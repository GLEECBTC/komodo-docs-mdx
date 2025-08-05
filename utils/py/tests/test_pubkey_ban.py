#!/usr/bin/env python3
"""Pubkey ban / unban RPC test.

This script exercises
  • ban_pubkey
  • list_banned_pubkeys
  • unban_pubkeys

It uses the node running on localhost:8778.

Run:
    python utils/py/tests/test_pubkey_ban.py
"""

import json
import time
from pathlib import Path
from typing import Dict

import requests

from kdf_test_helper import KDFTestHelper

helper = KDFTestHelper()

RPC_URL = helper.rpc_url
CONFIG_DIR = helper.compose_dir / "kdf-config"
MM2_FILE = CONFIG_DIR / "MM2.json"

# ---------------------------------------------------------------------------
# Load test parameters (pubkeys) from utils/py/kdf_test_cases/test_params.json
# ---------------------------------------------------------------------------

PARAMS_FILE = Path(__file__).resolve().parents[1] / "kdf_test_cases" / "test_params.json"
with open(PARAMS_FILE, "r", encoding="utf-8") as f:
    _params_data = json.load(f)

PUBKEYS_LIST = _params_data.get("BAN_PUBKEYS", [])
if len(PUBKEYS_LIST) < 2:
    raise SystemExit("BAN_PUBKEYS list in test_params.json must contain at least two pubkeys for testing.")

TEST_PUBKEY_1 = PUBKEYS_LIST[0]
OTHER_PUBKEYS = PUBKEYS_LIST[1:]

REASON = "pytest-ban"

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
CHECK = GREEN + "✅" + RESET
CROSS = RED + "❌" + RESET


def rpc(userpass: str, method: str, params: Dict[str, object] | None = None) -> Dict[str, object]:
    return helper.send_method(method, params or {}, id=0)


def main() -> None:
    helper.ensure_node_ready()

    vers_resp = helper.call_version()
    print("Node version:", vers_resp.get("result"))

    cfg = json.loads(MM2_FILE.read_text()) if MM2_FILE.exists() else {}
    userpass = cfg.get("rpc_password", helper.rpc_password)

    # Ensure clean state: unban all first
    rpc(userpass, "unban_pubkeys", {"unban_by": {"type": "All"}})

    # -------------------------------------------------------------------
    # Case 1: Ban single pubkey and then unban few
    # -------------------------------------------------------------------

    print("Banning test pubkey…")
    res = rpc(
        userpass,
        "ban_pubkey",
        {"pubkey": TEST_PUBKEY_1, "reason": REASON, "duration_min": 1},
    )
    if res.get("result") != "success":
        print(CROSS, "ban_pubkey failed:", res)
        raise SystemExit(1)
    print("ban_pubkey", CHECK)

    # Verify listed
    lst = rpc(userpass, "list_banned_pubkeys")
    banned = lst.get("result", {})
    if TEST_PUBKEY_1 not in banned:
        print(CROSS, "Pubkey not present in list after ban")
        raise SystemExit(1)
    print("list_banned_pubkeys contains pubkey", CHECK)

    # Unban
    print("Unbanning pubkey…")
    unr = rpc(
        userpass,
        "unban_pubkeys",
        {"unban_by": {"type": "Few", "data": [TEST_PUBKEY_1]}},
    )
    if TEST_PUBKEY_1 not in unr.get("result", {}).get("unbanned", {}):
        print(CROSS, "unban_pubkeys did not report unbanned", unr)
        raise SystemExit(1)
    print("unban_pubkeys", CHECK)

    # Verify removal
    lst2 = rpc(userpass, "list_banned_pubkeys")
    still = lst2.get("result", {})
    if TEST_PUBKEY_1 in still:
        print(CROSS, "Pubkey still in list after unban")
        raise SystemExit(1)
    print("Pubkey successfully removed", CHECK)

    # -------------------------------------------------------------------
    # Case 2: Ban two pubkeys then unban all
    # -------------------------------------------------------------------

    print("Banning two pubkeys…")
    for pk in PUBKEYS_LIST:
        rpc(userpass, "ban_pubkey", {"pubkey": pk, "reason": REASON, "duration_min": 1})

    lst3 = rpc(userpass, "list_banned_pubkeys")
    banned_now = set(lst3.get("result", {}).keys())
    if not set(PUBKEYS_LIST).issubset(banned_now):
        print(CROSS, "Not all pubkeys present after banning all")
        raise SystemExit(1)
    print("Both pubkeys banned", CHECK)

    print("Unbanning all pubkeys…")
    rpc(userpass, "unban_pubkeys", {"unban_by": {"type": "All"}})

    lst4 = rpc(userpass, "list_banned_pubkeys")
    after_all = lst4.get("result", {})
    if after_all:
        print(CROSS, "unban_pubkeys All failed – list not empty", after_all)
        raise SystemExit(1)
    print("unban_pubkeys All", CHECK)

    print("Ban/unban tests completed successfully", CHECK)


if __name__ == "__main__":
    main() 