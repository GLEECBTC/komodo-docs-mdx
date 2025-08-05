#!/usr/bin/env python3
"""HD Multi-address Message Signing/Verification Test.

This test iterates over *HD_SIGNING_COINS* defined in ``utils/py/kdf_test_cases/test_params.json``
and performs the following steps for **three derived addresses** (`address_id` 0-2) of each coin:

1. Derive or fetch the wallet address for the given `coin` and `address_id`.
2. Call ``sign_message`` providing the same derivation path.
3. Call ``verify_message`` with the generated signature and the wallet address.
4. Ensure the verification result is **``true``**.

For coins in *HD_SIGNING_FAIL_COINS* the script confirms that ``sign_message`` returns an
error (usually ``PrefixNotFound``) because the coin lacks a ``sign_message_prefix`` in its
configuration.

Run the test directly with:

```bash
python utils/py/tests/test_hd_message_signing.py
```

The Dockerised KDF node must be available on ``127.0.0.1:8778`` (default). Use the helper
class to start/stop the compose stack automatically when required.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List

from kdf_test_helper import KDFTestHelper

helper = KDFTestHelper()

CONFIG_DIR = helper.compose_dir / "kdf-config"
MM2_FILE = CONFIG_DIR / "MM2.json"

# ---------------------------------------------------------------------------
# Load coin lists from parameters JSON
# ---------------------------------------------------------------------------

PARAMS_FILE = Path(__file__).resolve().parents[1] / "kdf_test_cases" / "test_params.json"
with open(PARAMS_FILE, "r", encoding="utf-8") as fh:
    _params = json.load(fh)

HD_SIGNING_COINS: List[str] = _params.get("HD_SIGNING_COINS", [])
HD_SIGNING_FAIL_COINS: List[str] = _params.get("HD_SIGNING_FAIL_COINS", [])

if not HD_SIGNING_COINS:
    raise SystemExit("HD_SIGNING_COINS list is empty – nothing to test.")

# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
CHECK = GREEN + "✅" + RESET
CROSS = RED + "❌" + RESET


# ---------------------------------------------------------------------------
# RPC wrappers using shared ``helper`` instance
# ---------------------------------------------------------------------------

def rpc(method: str, params: Dict[str, object] | None = None) -> Dict[str, object]:
    """Send *method* with *params* using version auto-detection."""
    return helper.send_method(method, params or {}, id=0)


# ---------------------------------------------------------------------------
# Task helpers (account_balance & get_new_address) using ApiRequestProcessor polling
# ---------------------------------------------------------------------------

def _fetch_existing_addresses(coin: str) -> List[Dict[str, object]]:
    """Return list of external addresses for *coin* using account_balance task."""

    init_resp = rpc("task::account_balance::init", {"coin": coin, "account_index": 0})
    if "error" in init_resp:
        raise RuntimeError(f"account_balance::init error for {coin}: {init_resp['error']}")

    task_id = init_resp.get("result", {}).get("task_id")
    if task_id is None:
        raise RuntimeError(f"account_balance::init did not return task_id for {coin}")

    status_result = helper.api_processor.poll_task_status(
        "task::account_balance::status", task_id
    )

    wallet_balance = status_result.get("wallet_balance", {})
    accounts = wallet_balance.get("accounts", [])

    addresses: List[Dict[str, object]] = []
    for acc in accounts:
        if acc.get("account_index") != 0:
            continue  # only account 0 for this test
        for addr in acc.get("addresses", []):
            if addr.get("chain") == "External":
                addresses.append(addr)
    return addresses


def _create_new_address(coin: str) -> Dict[str, object]:
    """Generate a new external address using the **non-task** `get_new_address` method.

    This avoids the current `HwContextNotInitialized` bug in
    `task::get_new_address::init` (see issue
    <https://github.com/KomodoPlatform/komodo-defi-framework/issues/2507>)."""

    resp = rpc(
        "get_new_address",
        {
            "coin": coin,
            "account_id": 0,
            "chain": "External",
        },
    )

    if "error" in resp:
        # Graceful handling when we've reached the address gap-limit. The
        # daemon returns a structured error object we can inspect.
        if resp.get("error_type") == "EmptyAddressesLimitReached":
            # Indicates we already generated the maximum unused addresses.
            # Return an empty dict so the caller can decide whether to proceed
            # with fewer addresses.
            return {}
        raise RuntimeError(f"get_new_address error for {coin}: {resp['error']}")

    result = resp.get("result", {})
    new_addr = result.get("new_address") or result  # fallback for legacy structure

    if not new_addr or "address" not in new_addr:
        # Empty dict from gap-limit case – propagate upwards.
        return {}

    # Return as-is (contains address, derivation_path, chain, balance)
    return new_addr


def derive_addresses(coin: str, count: int = 3) -> List[Dict[str, object]]:
    """Return *count* address info dicts for *coin*.

    Uses account_balance to fetch existing addresses and `get_new_address` to create
    additional ones if fewer than *count* are available.
    """

    addresses = _fetch_existing_addresses(coin)

    while len(addresses) < count:
        new_addr = _create_new_address(coin)
        if not new_addr:
            # Gap limit reached – cannot create more. Break to avoid infinite loop.
            break
        addresses.append(new_addr)

    return addresses[:count]


# ---------------------------------------------------------------------------
# Main test logic
# ---------------------------------------------------------------------------

def test_sign_and_verify() -> None:  # noqa: C901 – function is long but linear
    """Run signing/verification checks across all configured coin lists."""

    helper.ensure_node_ready()

    # Load userpass if available
    cfg = json.loads(MM2_FILE.read_text()) if MM2_FILE.exists() else {}

    print("HD multi-address message signing test – starting…\n")

    # ---------------------------------------------------------------------
    # Positive path – coins that should support signing
    # ---------------------------------------------------------------------

    for coin in HD_SIGNING_COINS:
        # Ensure coin is active
        if helper.api_processor and coin not in helper.api_processor.enabled_coins:
            print(f"Activating coin {coin} …")
            if not helper.api_processor.activate_coin(coin):
                print(CROSS, f"Failed to activate {coin}")
                raise SystemExit(1)

        print(f"Testing signing for coin: {coin}")

        try:
            addr_infos = derive_addresses(coin, 3)
        except Exception as exc:
            print(CROSS, f"Failed to prepare addresses for {coin}: {exc}")
            raise SystemExit(1)

        for idx, addr_info in enumerate(addr_infos):
            wallet_addr = addr_info.get("address")
            derivation_path = addr_info.get("derivation_path")
            if not wallet_addr or not derivation_path:
                print(CROSS, f"Incomplete address info for {coin}: {addr_info}")
                raise SystemExit(1)

            message = f"HD signing test {coin} addr {idx}"

            # 1. Sign
            sign_resp = rpc(
                "sign_message",
                {
                    "coin": coin,
                    "message": message,
                    "address": {"derivation_path": derivation_path},
                },
            )
            if "error" in sign_resp:
                print(CROSS, f"sign_message error for {coin}:", sign_resp["error"])
                raise SystemExit(1)
            signature = sign_resp.get("result", {}).get("signature")
            if not signature:
                print(CROSS, "Signature missing from response", sign_resp)
                raise SystemExit(1)

            # 2. Verify
            verify_resp = rpc(
                "verify_message",
                {
                    "coin": coin,
                    "message": message,
                    "signature": signature,
                    "address": wallet_addr,
                },
            )
            is_valid = verify_resp.get("result", {}).get("is_valid")
            if is_valid is not True:
                print(CROSS, f"verify_message failed for {coin} address {wallet_addr}")
                raise SystemExit(1)
            print(f"  index {idx}: sign/verify", CHECK)

        print(f"{coin} – all indices passed", CHECK, "\n")

    # ---------------------------------------------------------------------
    # Negative path – coins expected to fail due to missing prefix
    # ---------------------------------------------------------------------

    if HD_SIGNING_FAIL_COINS:
        print("\nTesting coins expected to fail (missing sign_message_prefix)…")
        for coin in HD_SIGNING_FAIL_COINS:
            # Ensure coin active to trigger prefix error instead of NoSuchCoin
            if helper.api_processor and coin not in helper.api_processor.enabled_coins:
                print(f"Activating coin {coin} for negative test …")
                helper.api_processor.activate_coin(coin)

            resp = rpc("sign_message", {"coin": coin, "message": "should fail"})
            if "error" not in resp:
                print(CROSS, f"sign_message unexpectedly succeeded for {coin}")
                raise SystemExit(1)
            print(f"{coin}: expected failure →", resp.get("error_type", resp.get("error")), CHECK)

    print("\nAll HD multi-address signing tests completed successfully", CHECK)


if __name__ == "__main__":
    test_sign_and_verify() 