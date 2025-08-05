#!/usr/bin/env python3
"""Delete Wallet RPC test script.

This script exercises the `delete_wallet` RPC to ensure
wallets can be deleted only when inactive and with the
correct password.

Usage:
    python test_delete_wallet_rpc.py

The Komodo DeFi Framework must be running on http://127.0.0.1:7783
and contain the specified wallets.
"""

import json
import time
from pathlib import Path

from kdf_test_helper import KDFTestHelper
import requests

helper = KDFTestHelper()

RPC_URL = helper.rpc_url

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
CHECK = GREEN + "✅" + RESET
CROSS = RED + "❌" + RESET

# ---------------------------------------------------------------------------
# Test pre-setup: ensure the node runs with a wallet that can be deleted.
# ---------------------------------------------------------------------------

CONFIG_DIR = helper.compose_dir / "kdf-config"
MM2_FILE = CONFIG_DIR / "MM2.json"

DELETE_WALLET_NAME = "delete_me"
DELETE_WALLET_PW = "1WillRis3@gain"

# Wallet that will remain active during testing
ACTIVE_WALLET_NAME = "active_wallet"
ACTIVE_WALLET_PW = "1c@N-n0t-Di3"


def _write_mm2(wallet_name: str, wallet_pw: str):
    # Base MM2.json template required for tests
    data = {
        "gui": "kdf_mdx_docs",
        "rpcip": "0.0.0.0",
        "rpc_local_only": False,
        "enable_hd": True,
        "netid": 8762,
        "rpcport": 8778,
        "1inch_api": "https://api.1inch.dev",
        "seednodes": [
            "seed01.kmdefi.net",
            "seed02.kmdefi.net",
        ],
        "passphrase": "movie near museum glare gossip clerk adapt chair inch child erupt verify",
        "rpc_password": "RPC_UserP@SSW0RD",
        "use_watchers": False,
        "i_am_seed": False,
        "is_bootstrap_node": False,
        "disable_p2p": False,
        "use_trading_proto_v2": False,
        "allow_weak_password": True,
        "event_streaming_configuration": {"access_control_allow_origin": "*"},
        # Wallet specific
        "wallet_name": wallet_name,
        "wallet_password": wallet_pw,
    }
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MM2_FILE.write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Helper functions that rely on the shared ``helper`` instance
# ---------------------------------------------------------------------------


def _cycle_wallets():
    """Start with delete_me wallet, then restart with active wallet."""

    # 2. Stop container so files are flushed
    helper.docker_compose(["stop"])
    time.sleep(3)

    # 1. Write config with deletable wallet and start container
    _write_mm2(DELETE_WALLET_NAME, DELETE_WALLET_PW)
    helper.docker_compose(["up", "-d"])
    time.sleep(6)

    # 2. Stop container so files are flushed
    helper.docker_compose(["stop"])
    time.sleep(3)

    # 3. Write config with active wallet and start container again
    _write_mm2(ACTIVE_WALLET_NAME, ACTIVE_WALLET_PW)
    helper.docker_compose(["up", "-d"])
    time.sleep(6)


# ---------------------------------------------------------------------------
# RPC helper using shared ``helper``
# ---------------------------------------------------------------------------


def rpc(userpass: str, method: str, params: dict) -> dict:
    return helper.send_method(method, params, id=1)


def main() -> None:
    cfg = json.loads(MM2_FILE.read_text())
    userpass = cfg.get("rpc_password", "RPC_UserP@SSW0RD")
    active_pass = ACTIVE_WALLET_PW
    wallet_to_delete = DELETE_WALLET_NAME
    delete_pass = DELETE_WALLET_PW

    helper.ensure_node_ready()
    _cycle_wallets()

    info = rpc(userpass, "get_wallet_names", {})
    result = info.get("result", {})
    active = result.get("activated_wallet")
    wallets = result.get("wallet_names", [])
    print("Wallets:", wallets, "Active:", active)

    # 1. Attempt to delete the active wallet (should fail)
    print("Deleting active wallet (expect failure)...")
    resp = rpc(userpass, "delete_wallet", {"wallet_name": active, "password": active_pass})
    if "error" not in resp:
        print(CROSS, "Active wallet deletion should have failed but succeeded")
        raise SystemExit(1)
    print("Delete active wallet error:", resp["error"], CHECK)

    # 2. Attempt to delete with wrong password (should fail)
    print("Deleting", wallet_to_delete, "with wrong password (expect failure)...")
    wrong = rpc(userpass, "delete_wallet", {"wallet_name": wallet_to_delete, "password": "wrong_pass"})
    if "error" not in wrong:
        print(CROSS, "Deletion with wrong password unexpectedly succeeded")
        raise SystemExit(1)
    print("Wrong password error:", wrong["error"], CHECK)

    # 3. Delete with correct password (should succeed)
    print("Deleting", wallet_to_delete, "with correct password...")
    success = rpc(userpass, "delete_wallet", {"wallet_name": wallet_to_delete, "password": delete_pass})
    if "error" in success:
        print(CROSS, "Deletion failed:", success["error"])
        raise SystemExit(1)
    print("Deleted", wallet_to_delete, CHECK)

    # 4. Verify the wallet is gone
    check = rpc(userpass, "get_wallet_names", {})
    wallets_after = check.get("result", {}).get("wallet_names", [])
    print("Wallets after deletion:", wallets_after)
    if wallet_to_delete in wallets_after:
        print(CROSS, "Wallet still present after deletion")
        raise SystemExit(1)
    print("Wallet successfully removed", CHECK)

    helper.docker_compose(["down"])

if __name__ == "__main__":
    main()
