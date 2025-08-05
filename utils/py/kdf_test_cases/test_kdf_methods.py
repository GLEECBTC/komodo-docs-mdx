#!/usr/bin/env python3
"""Integration tests for Komodo DeFi Framework (KDF).

This module refactors the following standalone scripts into a single test class:

* `test_hd_wallet_msg_signing.py`
* `test_unified_rpc_interface.py`
* `test_zcoin_locked_notes.py`

The tests assume a KDF node is available.  If the environment variable
`START_KDF_CONTAINER` is set to `1` (default), the tests will automatically
build and start the Docker compose stack defined in
`utils/docker/docker-compose.yml` before running.  Set the variable to `0`
if you prefer to manage the node lifecycle yourself.

Configuration is controlled by environment variables to avoid command-line
arguments:

* `RPC_URL` Base URL of the RPC endpoint (default: `http://127.0.0.1`)
* `RPC_PORT` Port of the RPC service (default: `8778`)
* `RPC_PASSWORD` RPC authentication token (default:
  `RPC_UserP@SSW0RD`)
* `WALLET_DIR` Path that contains the Z-coin wallet DB (required for the
  locked notes test).
* `ZCOIN_TICKER` Ticker symbol for the Z-coin test (default: `ARRR`).
* `ZCOIN_WITHDRAW_AMOUNT` Amount to withdraw in the locked notes test
  (default: `0.0001`).

These variables align with the ones used in the Docker image so you can simply
source `utils/docker/kdf-config/.env` before executing the tests.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
import requests

# Third-party helpers ---------------------------------------------------------------------------
# Load sensitive values (e.g. RPC_PASSWORD) from the same .env file that is mounted into the
# container (see utils/docker/docker-compose.yml).
from dotenv import load_dotenv  # type: ignore

# The .env file lives in utils/docker/kdf-config/.env relative to the repository root.
_ENV_PATH = Path(__file__).resolve().parents[3] / "utils/docker/kdf-config/.env"
load_dotenv(_ENV_PATH, override=False)

# Load test-specific parameters (non-sensitive) from JSON so they are version-controlled but easily
# customisable without touching the code. A companion ``test_params.example.json`` file is provided
# with sane defaults; copy it to ``test_params.json`` and adjust as needed.
_PARAMS_PATH = Path(__file__).with_name("test_params.json")
try:
    with _PARAMS_PATH.open("r", encoding="utf-8") as fp:
        _TEST_PARAMS: Dict[str, str] = json.load(fp)
except FileNotFoundError:
    _TEST_PARAMS = {}

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

# Existing tooling ------------------------------------------------------------------------------
from utils.py.kdf_tools import KDFTools

# ---------------------------------------------------------------------------
# Utility wrapper around the ApiRequestProcessor inside KDFTools
# ---------------------------------------------------------------------------


def _call_rpc(processor, method: str, params: Dict[str, Any] | None = None, *, _id: int = 0) -> Dict[str, Any]:
    """Thin wrapper that delegates the RPC call to ApiRequestProcessor._make_request."""

    request_body: Dict[str, Any] = {
        "method": method,
        "mmrpc": "2.0",
        "params": params or {},
        "id": _id,
    }

    response = processor._make_request(request_body)
    if "error" in response:
        raise RuntimeError(f"RPC {method} error: {response}")

    return response.get("result", {})

# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestKDFMethods:
    """High-level integration tests leveraging the production helper classes."""

    _tools: Optional[KDFTools] = None
    _processor: Optional[Any] = None  # ApiRequestProcessor instance
    wallet_dir: str = 'utils/docker/kdf-db/7a4283ac93466ea1f0e4bb387e28055bbb38192e'

    # Constants for the HD message-signing test
    _DOC = "DOC"
    _ELECTRUM_SERVERS = [
        {"url": "electrum1.cipig.net:10020"},
        {"url": "electrum2.cipig.net:10020"},
        {"url": "electrum3.cipig.net:10020"},
    ]
    _TEST_MESSAGE = "HD message"

    # ---------------------------------------------------------------------
    # PyTest hooks
    # ---------------------------------------------------------------------

    @classmethod
    def setup_class(cls):  # noqa: D401 – imperative mood in pytest hook
        """Start a KDF node (Docker) unless disabled via environment var."""
        # Initialise KDFTools which in turn sets up ApiRequestProcessor (incl. .env loading).
        cls._tools = KDFTools()

        # Optionally (default) start the container using the proven implementation.
        if os.getenv("START_KDF_CONTAINER", "1") == "1":
            args = argparse.Namespace(kdf_branch=os.getenv("KDF_BRANCH", "dev"), commit=None, clean=False)
            cls._tools.start_container_command(args)
            # Allow the daemon a moment to become responsive.
            time.sleep(5)

        cls._processor = cls._tools.processor

    @classmethod
    def teardown_class(cls):  # noqa: D401 – imperative mood in pytest hook
        """Tear down the Docker container started in `setup_class`."""
        if cls._tools is None:
            return

        if os.getenv("START_KDF_CONTAINER", "1") == "1":
            # Use the dedicated stop logic.
            args = argparse.Namespace()
            cls._tools.stop_container_command(args)

    # ---------------------------------------------------------------------
    # Helper methods
    # ---------------------------------------------------------------------

    @classmethod
    def rpc(cls, method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        assert cls._processor is not None, "ApiRequestProcessor not initialized"
        return _call_rpc(cls._processor, method, params)

    @staticmethod
    def _locked_notes_db_path(wallet_dir: str, address: str) -> Path:
        return Path(wallet_dir) / f"{address}_locked_notes_cache.db"

    # ---------------------------------------------------------------------
    # Tests
    # ---------------------------------------------------------------------

    def test_hd_wallet_message_signing(self):
        """Enable DOC coin in HD mode and verify signatures from two addresses."""

        params = {
            "ticker": self._DOC,
            "activation_params": {
                "mode": {"rpc": "Electrum", "rpc_data": {"servers": self._ELECTRUM_SERVERS}},
                "path_to_address": {"account_id": 0, "chain": "External", "address_id": 0},
            },
        }
        init = self.rpc("task::enable_utxo::init", params)
        task_id = init["task_id"]
        print(f"Message Signing Task ID: {task_id}")

        # Poll status until activation is completed
        while True:
            time.sleep(1)
            status = self.rpc("task::enable_utxo::status", {"task_id": task_id})
            print(f"Message Signing Task ID: {task_id} Status: {status}")
            if status["status"] == "Ok":
                details = status["details"]
                break
            if status["status"] == "Error":
                pytest.fail(f"DOC enable error: {status}")

        addr0 = details["wallet_balance"]["accounts"][0]["addresses"][0]["address"]
        addr1 = details["wallet_balance"]["accounts"][0]["addresses"][1]["address"]

        # Address 0 – derivation path selector
        sig0 = self.rpc(
            "sign_message",
            {"coin": self._DOC, "message": self._TEST_MESSAGE, "address": {"derivation_path": "m/44'/141'/0'/0/0"}},
        )["signature"]
        assert self.rpc(
            "verify_message",
            {"coin": self._DOC, "message": self._TEST_MESSAGE, "signature": sig0, "address": addr0},
        )["is_valid"]

        # Address 1 – account/chain selector
        sig1 = self.rpc(
            "sign_message",
            {
                "coin": self._DOC,
                "message": self._TEST_MESSAGE,
                "address": {"account_id": 0, "chain": "External", "address_id": 1},
            },
        )["signature"]
        assert self.rpc(
            "verify_message",
            {"coin": self._DOC, "message": self._TEST_MESSAGE, "signature": sig1, "address": addr1},
        )["is_valid"]

    def test_unified_rpc_interface(self):
        """Ensure legacy and v2 RPC dispatchers return the same result."""

        legacy_req = {
            "userpass": os.getenv("RPC_PASSWORD", "RPC_UserP@SSW0RD"),
            "method": "get_public_key",
            "id": 2,
        }
        v2_req = legacy_req | {"mmrpc": "2.0", "id": 1}

        # Call directly with requests to exercise raw interface
        base_url = self._processor.api_url  # type: ignore[attr-defined]
        r_legacy = requests.post(base_url, json=legacy_req, timeout=60)
        r_legacy.raise_for_status()
        legacy_resp = r_legacy.json()

        r_v2 = requests.post(base_url, json=v2_req, timeout=60)
        r_v2.raise_for_status()
        v2_resp = r_v2.json()

        assert legacy_resp == v2_resp, f"Mismatch between new and legacy RPC results: {v2_resp} vs {legacy_resp}"

    def test_zcoin_locked_notes(self):
        """Withdraw Z-coin and ensure locked notes are tracked and cleared."""

        if not self.wallet_dir:
            pytest.skip("WALLET_DIR environment variable not set – skipping locked notes test.")
        coin = _TEST_PARAMS.get("ZCOIN_TICKER", os.getenv("ZCOIN_TICKER", "ARRR"))
        amount = _TEST_PARAMS.get("ZCOIN_WITHDRAW_AMOUNT", os.getenv("ZCOIN_WITHDRAW_AMOUNT", "0.0001"))

        bal = self.rpc("my_balance", {"coin": coin})
        my_addr = bal["address"]

        tx = self.rpc("withdraw", {"coin": coin, "to": my_addr, "amount": amount})
        txid = tx["tx_hash"]

        db_file = self._locked_notes_db_path(self.wallet_dir, my_addr)

        def fetch_locked_notes(db_path: Path, txid_: str) -> int:
            if not db_path.exists():
                return 0
            with sqlite3.connect(db_path) as conn:
                cur = conn.execute("SELECT COUNT(*) FROM locked_notes_cache WHERE txid=?", (txid_,))
                row = cur.fetchone()
                return row[0] if row else 0

        assert fetch_locked_notes(db_file, txid) > 0, "No locked notes found after withdraw"

        # Wait until notes disappear indicating confirmation
        while fetch_locked_notes(db_file, txid) > 0:
            time.sleep(10)

        final_bal = self.rpc("my_balance", {"coin": coin})
        assert float(final_bal["spendable"]) <= float(bal["spendable"]) - float(amount) 