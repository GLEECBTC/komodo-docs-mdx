"""Trezor Device TUI
====================
Minimal terminal UI to drive Komodo DeFi Framework Trezor helper
methods (task::init_trezor::* and trezor_connection_status).

Launch (from repo root, venv active):

    python -m utils.py.tui.trezor

Dependencies: same as other TUIs (rich).
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.panel import Panel
except ImportError:
    raise SystemExit("Please install 'rich' inside your venv: pip install rich")

# ---------------------------------------------------------------------------
# Path boot-strapper so the script works regardless of where it is executed
# (repo root or any sub-folder). Mirrors logic used in walletconnect TUI.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve()
_WORKSPACE_ROOT = next((p for p in _HERE.parents if (p / "utils").exists()), None)

if _WORKSPACE_ROOT and str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

# Internal imports (require workspace root on sys.path)
from utils.py.kdf_tools import KDFTools
from lib.constants.config_struct import EnhancedKomodoConfig, NodeConfig
from lib.api_client.kdf_api_processor import ApiRequestProcessor

class TrezorTUI:
    def __init__(self):
        self.console = Console()
        self.tools = KDFTools()
        self.processor: ApiRequestProcessor = self.tools.processor
        self.last_task_id: Optional[int] = None
        self.branch = EnhancedKomodoConfig().kdf_branch or "unknown"

        # Force localhost usage (port 8777) as requested
        self.api_url = "http://127.0.0.1:8777"
        self.userpass = "RPC_UserP@SSW0RD"

        # Dummy node object for backward-compatible display only
        class _LocalNode:
            name = "localhost"
            api_url = "http://127.0.0.1:8777"
        self.active_node = _LocalNode()

        # Build a minimal NodeConfig compatible instance for ApiRequestProcessor
        self.local_node_cfg = NodeConfig(
            name="localhost",
            port=8777,
            api_url="http://127.0.0.1:8777",
            userpass=self.userpass,
            passphrase="",
            hd_mode=False,
            wasm_mode=False,
        )

        # Replace processor's node list with the local-host node so *all* helper
        # logic (e.g. task polling, disable_coin, etc.) targets 127.0.0.1:8777.
        self.processor.config.nodes = [self.local_node_cfg]
        # Also reset any enabled_coins tracking to align with the new single-node setup
        self.processor.enabled_coins = {self.local_node_cfg.name: set()}

        self.last_activation_task: Optional[dict] = None  # {'prefix': str, 'task_id': int}
        self.last_wallet_task: Optional[dict] = None  # {'prefix': str, 'task_id': int}

    # --------------------------- RPC helpers ---------------------------
    def _rpc(self, method: str, params: dict | None = None):
        # Inject userpass and target the first configured node
        body = {
            "method": method,
            "mmrpc": "2.0",
            "params": params or {},
            "id": 0,
            "userpass": self.userpass,
        }

        # --- Logging ---
        self.console.print(f"[cyan]→ {method}[/]")
        self.console.print("[yellow]Request:[/]")
        self.console.print_json(json.dumps(body, indent=2))

        resp = self.processor._make_request(self.api_url, body)

        self.console.print("[yellow]Response:[/]")
        self.console.print_json(json.dumps(resp, indent=2))
        if "error" in resp:
            raise RuntimeError(resp["error"])
        return resp.get("result", {})

    # --------------------------- actions ------------------------------
    def init_device(self):
        dev_pk = Prompt.ask("Known device pubkey (optional)", default="").strip() or None
        params = {"device_pubkey": dev_pk} if dev_pk else {}
        try:
            res = self._rpc("task::init_trezor::init", params)
            self.last_task_id = res["task_id"]
            self.console.print(f"[green]Started init – Task ID {self.last_task_id}[/]")
        except Exception as e:
            self.console.print(f"[red]Init failed: {e}[/]")

    def status(self):
        task_id = self._ensure_task_id()
        if task_id is None:
            return
        try:
            res = self._rpc("task::init_trezor::status", {"task_id": task_id})
            self.console.print_json(json.dumps(res, indent=2))

            # Automatically guide the user based on status
            status = res.get("status")
            details = res.get("details")

            if status == "UserActionRequired":
                if details == "EnterTrezorPin":
                    self.console.print("[yellow]Device requests PIN entry.[/]")
                    if Confirm.ask("Enter PIN now?"):
                        self.send_user_action("TrezorPin")
                elif details == "EnterTrezorPassphrase":
                    self.console.print("[yellow]Device requests passphrase entry.[/]")
                    if Confirm.ask("Enter passphrase now?"):
                        self.send_user_action("TrezorPassphrase")

            if hasattr(self.processor, "last_status_responses"):
                self.console.print("[yellow]Status Polling Log:[/]")
                for resp in self.processor.last_status_responses:  # type: ignore[attr-defined]
                    self.console.print_json(json.dumps(resp, indent=2))
        except Exception as e:
            self.console.print(f"[red]Status error: {e}[/]")

    def send_user_action(self, action_type: str):
        task_id = self._ensure_task_id()
        if task_id is None:
            return
        # Build request according to docs: user_action must be an object containing
        # the actual action details (action_type, pin/passphrase, etc.)
        user_action: dict = {"action_type": action_type}

        if action_type == "TrezorPin":
            pin = Prompt.ask("Enter Trezor PIN (as mapped)")
            user_action["pin"] = pin
        elif action_type == "TrezorPassphrase":
            passwd = Prompt.ask("Enter Trezor passphrase", password=True)
            user_action["passphrase"] = passwd

        payload: dict = {"task_id": task_id, "user_action": user_action}

        try:
            res = self._rpc("task::init_trezor::user_action", payload)
            self.console.print(res)
        except Exception as e:
            self.console.print(f"[red]User action error: {e}[/]")

    def cancel(self):
        task_id = self._ensure_task_id()
        if task_id is None:
            return
        try:
            res = self._rpc("task::init_trezor::cancel", {"task_id": task_id})
            self.console.print(res)
        except Exception as e:
            self.console.print(f"[red]Cancel error: {e}[/]")

    def connection_status(self):
        pk = Prompt.ask("Expected device pubkey (optional)", default="").strip() or None
        params = {"device_pubkey": pk} if pk else {}
        try:
            res = self._rpc("trezor_connection_status", params)
            self.console.print_json(json.dumps(res, indent=2))
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/]")

    def activation_init(self):
        """Activate a coin using ApiRequestProcessor logic (task methods)."""
        ticker = Prompt.ask("Enter coin ticker (e.g., KMD, ETH, QTUM)").strip()
        if not ticker:
            self.console.print("[yellow]No ticker entered.[/]")
            return

        # Build activation request via internal helper from ApiRequestProcessor logic
        success = self.processor.activate_coin(
            ticker,
            node=self.local_node_cfg,
            priv_key_policy="Trezor",
        )

        # Always display the last request/response captured by ApiRequestProcessor
        if hasattr(self.processor, "last_request"):
            self.console.print("[yellow]Activation Request:[/]")
            self.console.print_json(json.dumps(self.processor.last_request, indent=2))
        if hasattr(self.processor, "last_response"):
            self.console.print("[yellow]Activation Response:[/]")
            self.console.print_json(json.dumps(self.processor.last_response, indent=2))

        if success:
            self.console.print(f"[green]{ticker} activated successfully.[/]")
        else:
            self.console.print(f"[red]Activation of {ticker} failed.[/]")

    def activation_status(self):
        if not self._ensure_activation_task():
            return
        method = f"{self.last_activation_task['prefix']}::status"
        try:
            res = self._rpc(method, {"task_id": self.last_activation_task['task_id']})
            self.console.print_json(json.dumps(res, indent=2))

            status = res.get("status") or res.get("result", {}).get("status")
            details = res.get("details") or res.get("result", {}).get("details")

            if status == "UserActionRequired":
                if details == "EnterTrezorPin":
                    self.console.print("[yellow]Activation requires Trezor PIN.[/]")
                    if Confirm.ask("Enter PIN now?"):
                        self.activation_send_user_action("TrezorPin")
                elif details == "EnterTrezorPassphrase":
                    self.console.print("[yellow]Activation requires Trezor Passphrase.[/]")
                    if Confirm.ask("Enter passphrase now?"):
                        self.activation_send_user_action("TrezorPassphrase")
        except Exception as e:
            self.console.print(f"[red]Activation status error: {e}[/]")

    def activation_send_user_action(self, action_type: str):
        if not self._ensure_activation_task():
            return
        user_action: dict = {"action_type": action_type}
        if action_type == "TrezorPin":
            pin = Prompt.ask("Enter Trezor PIN (as mapped)")
            user_action["pin"] = pin
        elif action_type == "TrezorPassphrase":
            passwd = Prompt.ask("Enter Trezor passphrase", password=True)
            user_action["passphrase"] = passwd
        payload = {"task_id": self.last_activation_task['task_id'], "user_action": user_action}
        method = f"{self.last_activation_task['prefix']}::user_action"
        try:
            res = self._rpc(method, payload)
            self.console.print(res)
        except Exception as e:
            self.console.print(f"[red]Activation user action error: {e}[/]")

    def activation_cancel(self):
        if not self._ensure_activation_task():
            return
        method = f"{self.last_activation_task['prefix']}::cancel"
        try:
            res = self._rpc(method, {"task_id": self.last_activation_task['task_id']})
            self.console.print(res)
        except Exception as e:
            self.console.print(f"[red]Activation cancel error: {e}[/]")

    # ====================== WALLET TASKS ============================
    # -- Account balance --
    def wallet_balance_init(self):
        coin = Prompt.ask("Coin ticker for account balance").strip()
        if not coin:
            return
        acct_idx = Prompt.ask("Account index", default="0")
        if not acct_idx.isdigit():
            self.console.print("[yellow]Invalid account index[/]")
            return
        params = {"coin": coin, "account_index": int(acct_idx)}
        try:
            res = self._rpc("task::account_balance::init", params)
            task_id = res.get("task_id")
            if task_id is None:
                self.console.print("[red]No task_id returned[/]")
                return
            self.last_wallet_task = {"prefix": "task::account_balance", "task_id": task_id}
            self.console.print(f"[green]Account balance task started – ID {task_id}[/]")
        except Exception as e:
            self.console.print(f"[red]Account balance init error: {e}[/]")

    def wallet_balance_status(self):
        if not self._ensure_wallet_task("task::account_balance"):
            return
        try:
            res = self._rpc("task::account_balance::status", {"task_id": self.last_wallet_task['task_id'], "forget_if_finished": False})
            self.console.print_json(json.dumps(res, indent=2))
        except Exception as e:
            self.console.print(f"[red]Account balance status error: {e}[/]")

    # -- Create new account --
    def create_account_init(self):
        coin = Prompt.ask("Coin ticker to create account for").strip()
        if not coin:
            return
        acct_id_str = Prompt.ask("Account ID (blank for next available)", default="")
        params = {"coin": coin}
        if acct_id_str.isdigit():
            params["account_id"] = int(acct_id_str)
        scan = Confirm.ask("Scan account for balances?", default=True)
        params["scan"] = scan
        try:
            res = self._rpc("task::create_new_account::init", params)
            task_id = res.get("task_id")
            if task_id is None:
                self.console.print("[red]No task_id returned[/]")
                return
            self.last_wallet_task = {"prefix": "task::create_new_account", "task_id": task_id}
            self.console.print(f"[green]Create account task started – ID {task_id}[/]")
        except Exception as e:
            self.console.print(f"[red]Create account init error: {e}[/]")

    def create_account_status(self):
        if not self._ensure_wallet_task("task::create_new_account"):
            return
        try:
            res = self._rpc("task::create_new_account::status", {"task_id": self.last_wallet_task['task_id'], "forget_if_finished": False})
            self.console.print_json(json.dumps(res, indent=2))
        except Exception as e:
            self.console.print(f"[red]Create account status error: {e}[/]")

    def create_account_user_action(self):
        if not self._ensure_wallet_task("task::create_new_account"):
            return
        pin = Prompt.ask("Enter Trezor PIN (as mapped)")
        payload = {"task_id": self.last_wallet_task['task_id'], "user_action": {"action_type": "TrezorPin", "pin": pin}}
        try:
            res = self._rpc("task::create_new_account::user_action", payload)
            self.console.print(res)
        except Exception as e:
            self.console.print(f"[red]Create account user_action error: {e}[/]")

    # -- Get new address --
    def new_address_init(self):
        coin = Prompt.ask("Coin ticker for new address").strip()
        if not coin:
            return

        account_id_str = Prompt.ask("Account ID", default="0")
        if not account_id_str.isdigit():
            self.console.print("[yellow]Invalid account ID.[/]")
            return

        chain = Prompt.ask("Chain (External/Internal)", default="External")

        params = {
            "coin": coin,
            "account_id": int(account_id_str),
            "chain": chain,
        }

        method = "task::get_new_address::init"
        self.console.print(f"[cyan]→ {method}[/]")

        try:
            res = self._rpc(method, params)
            task_id = res.get("task_id")
            if task_id is None:
                self.console.print("[red]No task_id returned[/]")
                return
            self.last_wallet_task = {"prefix": "task::get_new_address", "task_id": task_id}
            self.console.print(f"[green]New address task started – ID {task_id}[/]")
        except Exception as e:
            self.console.print(f"[red]New address init error: {e}[/]")

    def new_address_status(self):
        if not self._ensure_wallet_task("task::get_new_address"):
            return
        try:
            res = self._rpc("task::get_new_address::status", {"task_id": self.last_wallet_task['task_id'], "forget_if_finished": False})
            self.console.print_json(json.dumps(res, indent=2))
        except Exception as e:
            self.console.print(f"[red]New address status error: {e}[/]")

    def new_address_user_action(self):
        if not self._ensure_wallet_task("task::get_new_address"):
            return
        pin = Prompt.ask("Enter Trezor PIN (as mapped)")
        payload = {"task_id": self.last_wallet_task['task_id'], "user_action": {"action_type": "TrezorPin", "pin": pin}}
        try:
            res = self._rpc("task::get_new_address::user_action", payload)
            self.console.print(res)
        except Exception as e:
            self.console.print(f"[red]New address user_action error: {e}[/]")

    # -- Scan addresses --
    def scan_addresses_init(self):
        coin = Prompt.ask("Coin ticker for scan").strip()
        if not coin:
            return

        acct_idx_str = Prompt.ask("Account index", default="0")
        if not acct_idx_str.isdigit():
            self.console.print("[yellow]Invalid account index[/]")
            return

        params = {
            "coin": coin,
            "account_index": int(acct_idx_str),
        }

        method = "task::scan_for_new_addresses::init"
        self.console.print(f"[cyan]→ {method}[/]")

        try:
            res = self._rpc(method, params)
            task_id = res.get("task_id")
            if task_id is None:
                self.console.print("[red]No task_id returned[/]")
                return
            self.last_wallet_task = {"prefix": "task::scan_for_new_addresses", "task_id": task_id}
            self.console.print(f"[green]Scan addresses task started – ID {task_id}[/]")
        except Exception as e:
            self.console.print(f"[red]Scan addresses init error: {e}[/]")

    def scan_addresses_status(self):
        if not self._ensure_wallet_task("task::scan_for_new_addresses"):
            return
        try:
            res = self._rpc("task::scan_for_new_addresses::status", {"task_id": self.last_wallet_task['task_id'], "forget_if_finished": False})
            self.console.print_json(json.dumps(res, indent=2))
        except Exception as e:
            self.console.print(f"[red]Scan addresses status error: {e}[/]")

    # -- Withdraw --
    def withdraw_init(self):
        coin = Prompt.ask("Coin to withdraw").strip()
        if not coin:
            return

        # --------------------------------------------------------------
        # Select source address via account balance task
        # --------------------------------------------------------------
        acct_idx_str = Prompt.ask("Account index", default="0")
        if not acct_idx_str.isdigit():
            self.console.print("[yellow]Invalid account index.[/]")
            return
        acct_idx = int(acct_idx_str)

        bal_init_method = "task::account_balance::init"
        bal_status_method = "task::account_balance::status"

        self.console.print(f"[cyan]→ {bal_init_method}[/]")
        try:
            bal_res = self._rpc(bal_init_method, {"coin": coin, "account_index": acct_idx})
            bal_task_id = bal_res.get("task_id")
            if bal_task_id is None:
                self.console.print("[red]Failed to start account balance task.[/]")
                return

            # Poll status until completion (max 15s)
            for _ in range(15):
                status_res = self._rpc(bal_status_method, {"task_id": bal_task_id, "forget_if_finished": False})
                if status_res.get("status") == "Ok" or status_res.get("result", {}).get("status") == "Ok":
                    details = status_res.get("details") or status_res.get("result", {})
                    break
                time.sleep(1)
            else:
                self.console.print("[red]Timed out waiting for account balance.[/]")
                return

            addresses = details.get("addresses") or []
            if not addresses:
                self.console.print("[red]No addresses found for this account.[/]")
                return

            # Display addresses with spendable balances
            self.console.print("Available addresses (spendable balance):")
            addr_map = {}
            for idx, addr in enumerate(addresses):
                balance_map = addr.get("balance", {})
                # choose first balance entry for display
                bal_val = next(iter(balance_map.values())) if balance_map else {}
                spendable = bal_val.get("spendable", "0")
                self.console.print(f"  [{idx}] {addr['address']} – {spendable}")
                addr_map[str(idx)] = addr["address"]

            sel = Prompt.ask("Select from-address index", choices=list(addr_map.keys()))
            chosen_addr = addresses[int(sel)]
            from_selector = {
                "account_id": acct_idx,
                "chain": chosen_addr.get("chain", "External"),
                "address_id": int(chosen_addr["derivation_path"].split("/")[-1]),
            }
            from_addr = chosen_addr["address"]

        except Exception as e:
            self.console.print(f"[red]Failed to fetch account balance: {e}[/]")
            return

        to_addr = Prompt.ask("Destination address")
        max_withdraw = Confirm.ask("Withdraw MAX amount?", default=False)

        params = {
            "coin": coin,
            "to": to_addr,
            "from": from_selector,
        }

        if max_withdraw:
            params["max"] = True
        else:
            amt = Prompt.ask("Amount (numeric)")
            params["amount"] = amt

        method = "task::withdraw::init"
        request_body = {
            "userpass": self.userpass,
            "mmrpc": "2.0",
            "method": method,
            "params": params,
        }

        self.console.print(f"[cyan]→ {method}[/]")
        self.console.print("[yellow]Request:[/]")
        self.console.print_json(json.dumps(request_body, indent=2))

        try:
            res = self._rpc(method, params)
            task_id = res.get("task_id")
            if task_id is None:
                self.console.print("[red]No task_id returned[/]")
                return
            self.last_wallet_task = {"prefix": "task::withdraw", "task_id": task_id}
            self.console.print("[yellow]Response:[/]")
            self.console.print_json(json.dumps(res, indent=2))
            self.console.print(f"[green]Withdraw task started – ID {task_id}[/]")
        except Exception as e:
            self.console.print(f"[red]Withdraw init error: {e}[/]")

    def withdraw_status(self):
        if not self._ensure_wallet_task("task::withdraw"):
            return
        method = "task::withdraw::status"
        payload = {"task_id": self.last_wallet_task['task_id'], "forget_if_finished": False}
        self.console.print(f"[cyan]→ {method}[/]")
        self.console.print_json(json.dumps(payload, indent=2))
        try:
            res = self._rpc(method, payload)
            self.console.print_json(json.dumps(res, indent=2))
            status = res.get("status") or res.get("result", {}).get("status")
            details = res.get("details") or res.get("result", {}).get("details")
            if status == "UserActionRequired":
                self.console.print("[yellow]Withdraw needs PIN.[/]")
                if Confirm.ask("Enter PIN now?"):
                    self.withdraw_user_action()

            # Cache tx_hex for broadcasting
            if isinstance(details, dict) and details.get("tx_hex"):
                self.last_tx_hex = details["tx_hex"]
        except Exception as e:
            self.console.print(f"[red]Withdraw status error: {e}[/]")

    def withdraw_user_action(self):
        if not self._ensure_wallet_task("task::withdraw"):
            return
        pin = Prompt.ask("Enter Trezor PIN (as mapped)")
        payload = {"task_id": self.last_wallet_task['task_id'], "user_action": {"action_type": "TrezorPin", "pin": pin}}
        method = "task::withdraw::user_action"
        self.console.print(f"[cyan]→ {method}[/]")
        self.console.print_json(json.dumps(payload, indent=2))
        try:
            res = self._rpc(method, payload)
            self.console.print(res)
        except Exception as e:
            self.console.print(f"[red]Withdraw user action error: {e}[/]")

    def withdraw_cancel(self):
        if not self._ensure_wallet_task("task::withdraw"):
            return
        method = "task::withdraw::cancel"
        payload = {"task_id": self.last_wallet_task['task_id']}
        self.console.print(f"[cyan]→ {method}[/]")
        self.console.print_json(json.dumps(payload, indent=2))
        try:
            res = self._rpc(method, payload)
            self.console.print(res)
        except Exception as e:
            self.console.print(f"[red]Withdraw cancel error: {e}[/]")

    # --------------------------- broadcast raw tx ------------------------------
    def send_raw_transaction(self):
        tx_hex = Prompt.ask("Enter tx_hex (blank to use last cached)", default="").strip()
        if not tx_hex:
            tx_hex = getattr(self, "last_tx_hex", "")
            if not tx_hex:
                self.console.print("[yellow]No tx_hex available.[/]")
                return

        method = "send_raw_transaction"
        request_body = {
            "userpass": self.userpass,
            "method": method,
            "tx_hex": tx_hex,
        }

        self.console.print(f"[cyan]→ {method}[/]")
        self.console.print_json(json.dumps(request_body, indent=2))

        try:
            res = self._rpc(method, {"tx_hex": tx_hex})
            self.console.print_json(json.dumps(res, indent=2))
        except Exception as e:
            self.console.print(f"[red]Broadcast error: {e}[/]")

    # --------------------------- util ------------------------------
    def _ensure_task_id(self) -> Optional[int]:
        if self.last_task_id is None:
            inp = Prompt.ask("Enter task_id")
            if not inp.isdigit():
                self.console.print("[yellow]Invalid task_id.[/]")
                return None
            self.last_task_id = int(inp)
        return self.last_task_id

    def _ensure_activation_task(self) -> bool:
        if self.last_activation_task is None:
            self.console.print("[yellow]No activation task started yet.[/]")
            return False
        return True

    def _ensure_wallet_task(self, prefix: str) -> bool:
        if self.last_wallet_task is None or self.last_wallet_task.get("prefix") != prefix:
            self.console.print(f"[yellow]No active task for {prefix}. Start it first.[/]")
            return False
        return True

    # ------------------------------------------------------------------
    # Activation request builder (simplified subset of ApiRequestProcessor)
    # ------------------------------------------------------------------
    def _build_activation_request(self, ticker: str) -> dict | None:
        """Construct init request for *ticker* following ApiRequestProcessor logic."""
        coin_info = self.processor.coins_config.get(ticker)
        if coin_info is None:
            self.console.print(f"[red]{ticker} not found in coins_config.json.[/]")
            return None

        protocol = coin_info.get("protocol", {}).get("type")
        act_map = self.processor.protocol_to_activation.get(protocol, {})
        method = act_map.get("task")
        if not method:
            self.console.print(f"[red]No task-based activation method for protocol {protocol}.[/]")
            return None

        params: dict = {"ticker": ticker}

        # --- protocol-specific param helpers (subset) ---
        if protocol in {"UTXO", "BCH", "SLP"}:
            servers = coin_info.get("electrum", [])
            params["activation_params"] = {
                "mode": {
                    "rpc": "Electrum",
                    "rpc_data": {"servers": servers},
                },
                "utxo_merge_params": {"merge_at": 10},
                # Always add Trezor priv_key_policy for this TUI
                "priv_key_policy": "Trezor"
            }

        elif protocol in {"ETH", "ERC20"}:
            # Always add Trezor priv_key_policy for this TUI
            params.update({
                "nodes": coin_info.get("nodes", []),
                "priv_key_policy": {"type": "Trezor"}
            })
            if "swap_contract_address" in coin_info:
                params["swap_contract_address"] = coin_info["swap_contract_address"]


        return {
            "userpass": self.userpass,
            "method": method,
            "mmrpc": "2.0",
            "params": params,
        }

    # --------------------------- menu loop -------------------------
    def run(self):
        while True:
            self.console.print(
                Panel(
                    f"[1] Init Trezor\n[2] Status\n[3] Send PIN\n[4] Send Passphrase\n[5] Cancel Init\n[6] Connection status\n[7] Coin Activation Init\n[8] Coin Activation Status\n[9] Coin Activation Send PIN\n[10] Coin Activation Send Passphrase\n[11] Cancel Coin Activation\n[12] Account Balance Init\n[13] Account Balance Status\n[14] Create Account Init\n[15] Create Account Status\n[16] Create Account Send PIN\n[17] Get New Address Init\n[18] Get New Address Status\n[19] Get New Address Send PIN\n[20] Scan Addresses Init\n[21] Scan Addresses Status\n[22] Withdraw Init\n[23] Withdraw Status\n[24] Withdraw Send PIN\n[25] Withdraw Cancel\n[26] Broadcast Raw Transaction\n[q] Quit",
                    title=f"Trezor TUI (Branch: {self.branch})",
                    subtitle="Choose an action",
                )
            )
            choice = Prompt.ask("Your choice").strip().lower()
            if choice == "1":
                self.init_device()
            elif choice == "2":
                self.status()
            elif choice == "3":
                self.send_user_action("TrezorPin")
            elif choice == "4":
                self.send_user_action("TrezorPassphrase")
            elif choice == "5":
                self.cancel()
            elif choice == "6":
                self.connection_status()
            elif choice == "7":
                self.activation_init()
            elif choice == "8":
                self.activation_status()
            elif choice == "9":
                self.activation_send_user_action("TrezorPin")
            elif choice == "10":
                self.activation_send_user_action("TrezorPassphrase")
            elif choice == "11":
                self.activation_cancel()
            elif choice == "12":
                self.wallet_balance_init()
            elif choice == "13":
                self.wallet_balance_status()
            elif choice == "14":
                self.create_account_init()
            elif choice == "15":
                self.create_account_status()
            elif choice == "16":
                self.create_account_user_action()
            elif choice == "17":
                self.new_address_init()
            elif choice == "18":
                self.new_address_status()
            elif choice == "19":
                self.new_address_user_action()
            elif choice == "20":
                self.scan_addresses_init()
            elif choice == "21":
                self.scan_addresses_status()
            elif choice == "22":
                self.withdraw_init()
            elif choice == "23":
                self.withdraw_status()
            elif choice == "24":
                self.withdraw_user_action()
            elif choice == "25":
                self.withdraw_cancel()
            elif choice == "26":
                self.send_raw_transaction()
            elif choice in {"q", "quit", "exit"}:
                break
            else:
                self.console.print("[yellow]Unknown option – see menu for valid numbers.[/]")

    # --------------------------- node selection -------------------------
    def _select_node(self):
        self.console.print("[yellow]Node selection disabled – TrezorTUI always uses http://127.0.0.1:8777[/]")


if __name__ == "__main__":
    TrezorTUI().run() 