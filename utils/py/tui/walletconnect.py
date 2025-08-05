"""
Prototype WalletConnect TUI
---------------------------------
Interact with the Komodo DeFi Framework WalletConnect helper
methods (`wc_new_connection`, `wc_get_sessions`, etc.) from the
terminal.  Relies on the existing ApiRequestProcessor so it obeys
your current .env / docker-compose setup.

Run this from the repo root (after activating the venv):

    python utils/py/tui/walletconnect_tui.py

Dependencies (install in the venv if missing):
    pip install rich qrcode-terminal
"""

# ------------------------------------------------------------
# Path boot-strapper so the script works regardless of the
# directory it is executed from (repo root or sub-folder).
# ------------------------------------------------------------

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ------------------------------------------------------------
# Standard library imports (after path fix).
# ------------------------------------------------------------

import json
import os
import argparse
import subprocess
import time

from typing import Any, Dict, Optional, List

# Third-party, optional imports. We handle absence gracefully.
try:
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
except ImportError:
    print("[!] rich not installed – install with `pip install rich` for a nicer UI.")
    Console = None  # type: ignore

try:
    import qrcode
except ImportError:
    qrcode = None  # type: ignore

# Internal library imports – the main reason we are here
from lib.constants.config_struct import EnhancedKomodoConfig
from lib.constants.method_groups import KdfMethods
from lib.utils.logging_utils import KomodoLogger
from lib.api_client.kdf_api_processor import ApiRequestProcessor
from utils.py.kdf_tools import KDFTools


# --------------------------------------------------------------------------------------
# Helper utilities
# --------------------------------------------------------------------------------------

def _get_console() -> Console:
    if Console is not None:
        return Console()
    # Fallback minimal console
    class _Dummy:
        def print(self, *a, **k):
            print(*a)
    return _Dummy()  # type: ignore

def _display_qr(uri: str):
    """Render the WalletConnect URI as an ASCII QR code (if `qrcode` is available).

    If the `qrcode` library is missing, fall back to printing the raw URI.
    """

    if qrcode is None:
        print("[QR code omitted – install `qrcode` to render]")
        print(uri)
        return

    qr = qrcode.QRCode(border=1)
    qr.add_data(uri)
    qr.make(fit=True)

    matrix = qr.get_matrix()
    # Use two characters wide blocks to get a roughly square aspect ratio in terminal
    black = "\u2588\u2588"  # Full block x2
    white = "  "

    for row in matrix:
        line = ''.join([black if cell else white for cell in row])
        print(line)


def _choose(names: List[str], console: Console) -> Optional[str]:
    """Prompt the user to choose one of the given names, returns the chosen element or None."""
    if not names:
        console.print("[bold red]No sessions found[/]")
        return None
    for idx, name in enumerate(names, 1):
        console.print(f"[{idx}] {name}")
    while True:
        choice = Prompt.ask("Select # (or Enter to cancel)")
        if not choice:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(names):
            return names[int(choice) - 1]
        console.print("Invalid selection – try again")


# --------------------------------------------------------------------------------------
# Local RPC helper – ensures correct URL and userpass for requests
# --------------------------------------------------------------------------------------

def _rpc(processor: ApiRequestProcessor, body: Dict[str, Any]) -> Dict[str, Any]:
    """Send *body* to the active node with userpass injected and echo JSON."""

    console = _get_console()

    node = ACTIVE_NODE  # defined in main scope below
    full_body = dict(body)  # shallow copy is enough here
    full_body.setdefault("userpass", node.userpass)

    method_name = full_body.get("method", "")

    # Remove empty params for most methods, BUT keep them for v2 RPCs that
    # explicitly require an empty object (see bug KomodoPlatform/kdf#2498).
    if full_body.get("params") == {} and method_name not in getattr(KdfMethods, "no_params_v2", []):
        full_body.pop("params")

    # --- Logging ---------------------------------------------------
    console.print("[cyan]→ {}[/]".format(full_body.get("method")))
    console.print("[yellow]Request:[/]")
    try:
        console.print_json(json.dumps(full_body, indent=2))
    except Exception:
        console.print(full_body)

    resp = processor._make_request(node.api_url, full_body)

    console.print("[yellow]Response:[/]")
    try:
        console.print_json(json.dumps(resp, indent=2))
    except Exception:
        console.print(resp)

    # Short convenience display of errors
    if isinstance(resp, dict) and resp.get("error"):
        console.print(f"[red]Error: {resp.get('error')}[/]")

    return resp


# --------------------------------------------------------------------------------------
# Core TUI application
# --------------------------------------------------------------------------------------

def main():
    console = _get_console()

    console.print("[bold cyan]Initializing WalletConnect TUI …[/]")
    cfg = EnhancedKomodoConfig()  # auto-detects workspace root & branches
    active_branch = cfg.kdf_branch or "unknown"

    logger = KomodoLogger("walletconnect-tui")
    logger.logger.setLevel("ERROR")  # quiet internal logging

    # Tools helper (start/stop/build etc.)
    tools = KDFTools()
    processor = tools.processor  # reuse underlying ApiRequestProcessor

    # Active node for RPCs – starts with first in config
    global ACTIVE_NODE  # type: ignore
    ACTIVE_NODE = processor.config.nodes[0]

    console.print(f"[green]Ready. Using node: {ACTIVE_NODE.name} ({ACTIVE_NODE.api_url})[/]")

    def _menu_text() -> str:
        return (
            f"[0] Select node (current: {ACTIVE_NODE.name})\n"
            "[1] New connection\n"
            "[2] List sessions\n"
            "[3] Get session details\n"
            "[4] Ping session\n"
            "[5] Delete session\n"
            "[6] Start KDF container (no rebuild)\n"
            "[7] Stop KDF container\n"
            "[8] Switch KDF branch\n"
            "[9] Rebuild & restart container\n"
            "[10] Activate coin\n"
            "[11] Disable coin\n"
            "[12] List enabled coins\n"
            "[13] Withdraw coins\n"
            "[14] Make KMD sell order (setprice)\n"
            "[15] Buy KMD from orderbook\n"
            "[16] Legacy withdraw (direct)\n"
            "[17] Broadcast raw transaction\n"
            "[q] Quit"
        )

    while True:
        console.print(
            Panel(_menu_text(), title=f"WalletConnect TUI (Branch: {active_branch})", subtitle="Choose an action")
        )
        choice = Prompt.ask("Your choice").strip().lower()

        if choice == "0":
            ACTIVE_NODE = _select_node(processor, console, ACTIVE_NODE)
            console.print(f"[cyan]Switched to node {ACTIVE_NODE.name} ({ACTIVE_NODE.api_url})[/]")
        elif choice == "1":
            _handle_new_connection(processor, console)
        elif choice == "2":
            _handle_list_sessions(processor, console)
        elif choice == "3":
            _handle_get_session(processor, console)
        elif choice == "4":
            _handle_ping_session(processor, console)
        elif choice == "5":
            _handle_delete_session(processor, console)
        elif choice == "6":
            _start_container_no_build(cfg, tools, console, active_branch)
        elif choice == "7":
            tools.stop_container_command(argparse.Namespace())  # type: ignore  # simple namespace
        elif choice == "8":
            new_branch = Prompt.ask("Enter new branch name", default=active_branch).strip()
            if new_branch and new_branch != active_branch:
                _switch_branch_and_restart(tools, console, new_branch)
                active_branch = new_branch
        elif choice == "9":
            _rebuild_and_restart(tools, console, active_branch)
        elif choice == "10":
            _handle_activate_coin(processor, console)
        elif choice == "11":
            _handle_disable_coin(processor, console)
        elif choice == "12":
            _handle_list_enabled_coins(processor, console)
        elif choice == "13":
            _handle_withdraw(processor, console)
        elif choice == "14":
            _handle_make_order(processor, console)
        elif choice == "15":
            _handle_buy_order(processor, console)
        elif choice == "16":
            _handle_legacy_withdraw_ui(processor, console)
        elif choice == "17":
            _handle_send_raw_tx(processor, console)
        elif choice in {"q", "quit", "exit"}:
            console.print("Goodbye!")
            break
        else:
            console.print("[yellow]Unknown option – try again.[/]")


# --------------------------------------------------------------------------------------
# Action Handlers
# --------------------------------------------------------------------------------------

def _handle_new_connection(processor: ApiRequestProcessor, console: Console):
    console.print("[bold]Create a new WalletConnect connection[/]")

    console.print("\n[bold]Select required namespaces configuration:[/]")
    console.print("[1] EIP155 only (Ethereum)")
    console.print("[2] Cosmos only")
    console.print("[3] Both (EIP155 + Cosmos) [default]")

    choice = Prompt.ask("Choose 1, 2, or 3", choices=["1", "2", "3"], default="3")

    if choice == "1":
        required_namespaces = {
            "eip155": {
                "chains": ["eip155:1"],
                "methods": [
                    "eth_sendTransaction",
                    "eth_signTransaction",
                    "personal_sign",
                ],
                "events": ["accountsChanged", "chainChanged"],
            }
        }
    elif choice == "2":
        required_namespaces = {
            "cosmos": {
                "chains": [
                    "cosmos:cosmoshub-4",
					"cosmos:irishub-1",
					"cosmos:osmosis-1"
                ],
                "methods": ["cosmos_signDirect", "cosmos_signAmino", "cosmos_getAccounts"],
                "events": [],
            }
        }
    else:  # "3" – both
        required_namespaces = {
            "eip155": {
                "chains": ["eip155:1"],
                "methods": [
                    "eth_sendTransaction",
                    "eth_signTransaction",
                    "personal_sign",
                ],
                "events": ["accountsChanged", "chainChanged"],
            },
            "cosmos": {
                "chains": ["cosmos:cosmoshub-4"],
                "methods": ["cosmos_signDirect", "cosmos_signAmino", "cosmos_getAccounts"],
                "events": [],
            },
        }

    req = {
        "method": "wc_new_connection",
        "mmrpc": "2.0",
        "params": {"required_namespaces": required_namespaces},
        "id": 0,
    }

    resp = _rpc(processor, req)
    if "error" in resp:
        console.print(f"[red]Error: {resp['error']}[/]")
        return

    uri = resp.get("result", {}).get("url")
    if not uri:
        console.print(f"[red]Unexpected response: {resp}[/]")
        return

    console.print("[green]Connection URI:[/]")
    console.print(uri)
    _display_qr(uri)


def _handle_list_sessions(processor: ApiRequestProcessor, console: Console):
    req = {"method": "wc_get_sessions", "mmrpc": "2.0", "params": {}, "id": 0}
    resp = _rpc(processor, req)
    if "error" in resp:
        console.print(f"[red]Error: {resp['error']}[/]")
        return

    sessions = resp.get("result", {}).get("sessions") or []
    if not sessions:
        console.print("[yellow]No active sessions.[/]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Topic", overflow="fold")
    table.add_column("Wallet", overflow="fold")
    table.add_column("Chains")
    table.add_column("Expiry")

    for sess in sessions:
        wallet_name = sess.get("metadata", {}).get("name", "N/A")
        chains = ", ".join(
            [
                chain
                for ns in sess.get("namespaces", {}).values()
                for chain in (ns.get("chains") or [])
            ]
        )
        table.add_row(sess.get("topic"), wallet_name, chains, str(sess.get("expiry")))

    console.print(table)


def _prompt_topic(processor: ApiRequestProcessor, console: Console) -> Optional[str]:
    """Prompt the user for a session topic, offering a list if available."""
    req = {"method": "wc_get_sessions", "mmrpc": "2.0", "params": {}, "id": 0}
    resp = _rpc(processor, req)
    sessions_raw = resp.get("result", {}).get("sessions") or []
    session_topics = [s.get("topic") for s in sessions_raw if s]
    if not session_topics:
        console.print("[yellow]No sessions found.[/]")
        return None

    # Offer a menu to pick one
    chosen = _choose(session_topics, console)
    return chosen


def _handle_get_session(processor: ApiRequestProcessor, console: Console):
    topic = _prompt_topic(processor, console)
    if not topic:
        return
    req = {
        "method": "wc_get_session",
        "mmrpc": "2.0",
        "params": {"topic": topic},
        "id": 0,
    }
    resp = _rpc(processor, req)
    console.print_json(json.dumps(resp, indent=2))


def _handle_ping_session(processor: ApiRequestProcessor, console: Console):
    topic = _prompt_topic(processor, console)
    if not topic:
        return
    req = {
        "method": "wc_ping_session",
        "mmrpc": "2.0",
        "params": {"topic": topic},
        "id": 0,
    }
    resp = _rpc(processor, req)
    console.print(resp)


def _handle_delete_session(processor: ApiRequestProcessor, console: Console):
    topic = _prompt_topic(processor, console)
    if not topic:
        return
    if not Confirm.ask(f"Are you sure you want to delete session {topic}?"):
        return
    req = {
        "method": "wc_delete_session",
        "mmrpc": "2.0",
        "params": {"topic": topic},
        "id": 0,
    }
    resp = _rpc(processor, req)
    console.print(resp)


# --------------------------------------------------------------------------------------
# Container management helpers
# --------------------------------------------------------------------------------------


def _compose_file(cfg: EnhancedKomodoConfig):
    return cfg.directories.docker_dir / "docker-compose.yml"


def _start_container_no_build(cfg: EnhancedKomodoConfig, tools: KDFTools, console: Console, branch: str):
    compose = _compose_file(cfg)
    if not compose.exists():
        console.print(f"[red]docker-compose.yml not found at {compose} – cannot start container.[/]")
        return
    console.print(f"[cyan]Starting container for branch {branch} (no rebuild)…[/]")
    try:
        subprocess.run(
            [
                "docker",
                "compose",
                "--file",
                str(compose),
                "up",
                "-d",
            ],
            check=True,
            cwd=cfg.directories.docker_dir,
        )
        console.print("[green]Container started.[/]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to start container: {e}[/]")


def _rebuild_and_restart(tools: KDFTools, console: Console, branch: str):
    console.print(f"[cyan]Rebuilding and restarting container on branch {branch}…[/]")
    args = argparse.Namespace(kdf_branch=branch, commit=None, clean=False)
    tools.start_container_command(args)


def _switch_branch_and_restart(tools: KDFTools, console: Console, new_branch: str):
    console.print(f"[cyan]Switching to branch {new_branch} and restarting container…[/]")
    # Stop current container
    tools.stop_container_command(argparse.Namespace())  # type: ignore
    # Start with new branch (build may occur automatically)
    args = argparse.Namespace(kdf_branch=new_branch, commit=None, clean=False)
    tools.start_container_command(args)


# Node chooser helper ----------------------------------------------------

def _select_node(processor: ApiRequestProcessor, console: Console, current_node):
    """Prompt user to choose a node from processor.config.nodes.

    Returns the selected NodeConfig (or the current_node if cancelled)."""

    nodes = processor.config.nodes
    console.print("[bold]Select node to use:[/]")
    for idx, node in enumerate(nodes, 1):
        console.print(f"[{idx}] {node.name} – {node.api_url}")
    choice = Prompt.ask("Choice (Enter to cancel)")
    if not choice:
        return current_node
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(nodes):
            return nodes[idx-1]
    console.print("[yellow]Invalid selection – keeping previous node.[/]")
    return current_node


# --------------------------------------------------------------------------------------
# Activation helpers
# --------------------------------------------------------------------------------------

def _handle_activate_coin(processor: ApiRequestProcessor, console: Console):
    """Interactive coin activation using ApiRequestProcessor logic."""
    # --------------------------------------------------------------
    # 1. Ensure we have (or create) a WalletConnect session and get a
    #    `session_topic` that will be sent inside priv_key_policy.
    # --------------------------------------------------------------

    topic = _ensure_session_topic(processor, console)
    if topic is None:
        return  # user aborted

    # --------------------------------------------------------------
    # 2. Ask for the coin ticker to activate and perform activation.
    # --------------------------------------------------------------

    ticker = Prompt.ask("Enter coin ticker to activate (e.g., KMD, ETH, ATOM)").strip().upper()
    if not ticker:
        console.print("[yellow]No ticker provided.[/]")
        return

    console.print(f"[cyan]Activating {ticker} using session {topic}…[/]")

    priv_key_policy = {"type": "WalletConnect", "session_topic": topic}

    success = processor.activate_coin(
        ticker,
        node=ACTIVE_NODE,
        priv_key_policy=priv_key_policy,
    )

    # Always display last request/response pair when available for debugging
    if hasattr(processor, "last_request"):
        console.print("[yellow]Activation Request:[/]")
        console.print_json(json.dumps(processor.last_request, indent=2))
    if hasattr(processor, "last_response"):
        console.print("[yellow]Activation Response:[/]")
        console.print_json(json.dumps(processor.last_response, indent=2))

    if success:
        console.print(f"[green]{ticker} activated successfully.[/]")
    else:
        console.print(f"[red]Failed to activate {ticker}.[/]")


def _handle_disable_coin(processor: ApiRequestProcessor, console: Console):
    """Disable a previously activated coin."""
    ticker = Prompt.ask("Enter coin ticker to disable").strip().upper()
    if not ticker:
        console.print("[yellow]No ticker provided.[/]")
        return

    console.print(f"[cyan]Disabling {ticker}…[/]")
    success = processor.disable_coin(ticker, node=ACTIVE_NODE)
    if success:
        console.print(f"[green]{ticker} disabled successfully.[/]")
    else:
        console.print(f"[red]Failed to disable {ticker}.[/]")


def _handle_list_enabled_coins(processor: ApiRequestProcessor, console: Console):
    """Refresh and display the list of enabled coins for the active node."""
    processor._update_enabled_coins(node=ACTIVE_NODE)
    coins = processor.enabled_coins.get(ACTIVE_NODE.name, set())
    if not coins:
        console.print("[yellow]No coins are currently enabled on this node.[/]")
    else:
        coin_list = ", ".join(sorted(coins))
        console.print(f"[green]Enabled coins ({len(coins)}):[/] {coin_list}")


# --------------------------------------------------------------------------------------
# Withdraw helpers
# --------------------------------------------------------------------------------------

def _handle_withdraw(processor: ApiRequestProcessor, console: Console):
    """Start a withdraw task using WalletConnect signing."""

    # Ensure we have a WC session
    topic = _ensure_session_topic(processor, console)
    if topic is None:
        return

    coin = Prompt.ask("Coin ticker to withdraw").strip().upper()
    if not coin:
        console.print("[yellow]No ticker entered.[/]")
        return

    to_addr = Prompt.ask("Destination address")
    if not to_addr:
        console.print("[yellow]No destination entered.[/]")
        return

    max_withdraw = Confirm.ask("Withdraw MAX amount?", default=False)
    amount = None
    if not max_withdraw:
        amount = Prompt.ask("Amount to withdraw (numeric)").strip()
        if not amount:
            console.print("[yellow]Amount required when not using MAX.[/]")
            return

    # Build params
    params: dict = {
        "coin": coin,
        "to": to_addr,
        "priv_key_policy": {"type": "WalletConnect", "session_topic": topic},
    }
    if max_withdraw:
        params["max"] = True
    else:
        params["amount"] = amount

    init_req = {
        "method": "task::withdraw::init",
        "mmrpc": "2.0",
        "params": params,
        "id": 0,
    }

    resp = _rpc(processor, init_req)
    if "error" in resp:
        # Try legacy withdraw if coin doesn't support task
        if "CoinDoesntSupportInitWithdraw" in str(resp.get("error_type", "")) or "doesn't support 'init_withdraw'" in str(resp.get("error", "")):
            console.print("[yellow]Falling back to legacy 'withdraw' method…[/]")
            _legacy_withdraw(processor, console, params)
        else:
            console.print(f"[red]Withdraw init failed: {resp['error']}[/]")
        return

    task_id = resp.get("result", {}).get("task_id")
    if task_id is None:
        console.print("[red]No task_id returned – aborting.[/]")
        return

    console.print(f"[green]Withdraw task started (ID {task_id}). polling status…[/]")

    status_method = "task::withdraw::status"
    while True:
        time.sleep(3)
        status_req = {
            "method": status_method,
            "mmrpc": "2.0",
            "params": {"task_id": task_id},
            "id": 0,
        }
        status_resp = _rpc(processor, status_req)

        if "error" in status_resp:
            console.print(f"[red]Status error: {status_resp['error']}[/]")
            break

        result = status_resp.get("result", {})
        status = result.get("status")
        details = result.get("details")

        if status == "Ok":
            console.print("[green]Withdraw completed successfully.[/]")
            tx_hex = result.get("tx_hex") or result.get("transaction_hex")
            if tx_hex:
                console.print("[cyan]Signed transaction hex (broadcast with send_raw_transaction):[/]")
                console.print(tx_hex)
            break
        elif status == "UserActionRequired":
            console.print("[yellow]Waiting for wallet confirmation… Details:", details)
        elif status in {"Failed", "Error", "Aborted"}:
            console.print(f"[red]Withdraw task ended with status {status}. Details: {details}[/]")
            break
        else:
            # InProgress or other
            console.print(f"[blue]In progress… Details: {details}[/]")


def _legacy_withdraw(processor: ApiRequestProcessor, console: Console, params: Dict[str, Any]):
    """Perform legacy withdraw flow when task variant unsupported."""

    legacy_params = dict(params)  # copy
    # Legacy withdraw doesn't take priv_key_policy at top-level; include as is for v2 Tendermint
    req = {
        "method": "withdraw",
        "mmrpc": "2.0",
        "params": legacy_params,
        "id": 0,
    }
    resp = _rpc(processor, req)
    if "error" in resp:
        console.print(f"[red]Legacy withdraw failed: {resp['error']}[/]")
        return
    result = resp.get("result", {})
    tx_hex = result.get("tx_hex")
    if tx_hex:
        console.print("[green]Withdraw successful. Signed transaction hex:[/]")
        console.print(tx_hex)
    else:
        console.print("[green]Withdraw successful. Response:[/]")
        console.print_json(json.dumps(resp, indent=2))


# --------------------------------------------------------------------------------------
# Session helpers
# --------------------------------------------------------------------------------------


def _ensure_session_topic(processor: ApiRequestProcessor, console: Console) -> Optional[str]:
    """Return a WalletConnect session topic, creating a new session if needed.

    1. Lists existing sessions via wc_get_sessions.
    2. If none exist, prompts the user to create a new one (calls _handle_new_connection)
       and waits for confirmation after scanning the QR code.
    3. Lets the user choose a session topic and returns it.
    """

    # Reuse existing helper to fetch topics
    def _list_topics() -> List[str]:
        req = {"method": "wc_get_sessions", "mmrpc": "2.0", "params": {}, "id": 0}
        resp = _rpc(processor, req)
        sessions_raw = resp.get("result", {}).get("sessions") or []
        return [s.get("topic") for s in sessions_raw if s]

    topics = _list_topics()

    if not topics:
        console.print("[yellow]No active WalletConnect sessions found.[/]")
        if not Confirm.ask("Create a new session now?", default=True):
            console.print("[red]Activation requires a WalletConnect session – aborting.[/]")
            return None

        # Create new connection (this will show the QR)
        _handle_new_connection(processor, console)

        console.print("[cyan]Scan the QR code with your wallet, approve the connection, then press Enter to continue…[/]")
        input()  # wait for user acknowledgement

        # Re-fetch topics after connection approval
        topics = _list_topics()

        if not topics:
            console.print("[red]Still no sessions detected – cannot continue.[/]")
            return None

    # Let user pick a topic
    chosen = _choose(topics, console)
    return chosen


# --------------------------------------------------------------------------------------
# Orderbook helpers
# --------------------------------------------------------------------------------------


def _get_orderbook(processor: ApiRequestProcessor, base: str, rel: str) -> Dict[str, Any]:
    """Return orderbook snapshot for base/rel pair using legacy v1 `orderbook` RPC."""
    req = {
        "method": "orderbook",
        "base": base,
        "rel": rel,
        "userpass": ACTIVE_NODE.userpass,
    }
    return _rpc(processor, req)


def _best_ask_price(orderbook_resp: Dict[str, Any]) -> Optional[float]:
    try:
        asks = orderbook_resp.get("result", {}).get("asks") or []
        if not asks:
            return None
        # asks list items may have "price" field
        prices = [float(a.get("price")) for a in asks if a.get("price") is not None]
        return min(prices) if prices else None
    except Exception:
        return None


def _handle_make_order(processor: ApiRequestProcessor, console: Console):
    """Docker node posts a KMD sell order (setprice)."""

    rel = Prompt.ask("Quote coin ticker (rel)").strip().upper()
    if not rel:
        console.print("[yellow]No ticker given.[/]")
        return

    base = "KMD"

    ob = _get_orderbook(processor, base, rel)
    best_ask = _best_ask_price(ob)
    if best_ask is None:
        price = 1.0
    else:
        price = best_ask * 0.99  # beat best ask

    volume = 0.1

    req = {
        "method": "setprice",
        "base": base,
        "rel": rel,
        "price": str(price),
        "volume": str(volume),
        "cancel_previous": True,
        "userpass": ACTIVE_NODE.userpass,
    }

    resp = _rpc(processor, req)
    if "error" in resp:
        console.print(f"[red]setprice error: {resp['error']}[/]")
    else:
        console.print(f"[green]Order placed: Sell {volume} {base} at {price} {rel}/{base}.[/]")


def _handle_buy_order(processor: ApiRequestProcessor, console: Console):
    """Host node buys from orderbook using `buy`."""

    rel = Prompt.ask("Quote coin ticker (rel)").strip().upper()
    if not rel:
        console.print("[yellow]No ticker given.[/]")
        return

    base = "KMD"

    ob = _get_orderbook(processor, base, rel)
    best_ask = _best_ask_price(ob)
    if best_ask is None:
        console.print("[red]No asks on the book to buy.[/]")
        return

    volume = 0.1

    req = {
        "method": "buy",
        "base": base,
        "rel": rel,
        "price": str(best_ask),
        "volume": str(volume),
        "userpass": ACTIVE_NODE.userpass,
    }

    resp = _rpc(processor, req)
    if "error" in resp:
        console.print(f"[red]buy error: {resp['error']}[/]")
    else:
        console.print(f"[green]Buy order submitted: {volume} {base} at {best_ask} {rel}/{base}.[/]")


# --------------------------------------------------------------------------------------
# Legacy withdraw UI wrapper
# --------------------------------------------------------------------------------------

def _handle_legacy_withdraw_ui(processor: ApiRequestProcessor, console: Console):
    """Prompt user and execute legacy `withdraw` RPC (non-task)."""

    topic = _ensure_session_topic(processor, console)
    if topic is None:
        return

    coin = Prompt.ask("Coin ticker to withdraw (legacy)").strip().upper()
    if not coin:
        console.print("[yellow]No ticker provided.[/]")
        return

    to_addr = Prompt.ask("Destination address")
    if not to_addr:
        console.print("[yellow]No destination entered.[/]")
        return

    max_withdraw = Confirm.ask("Withdraw MAX amount?", default=False)
    amount = None
    if not max_withdraw:
        amount = Prompt.ask("Amount to withdraw (numeric)").strip()
        if not amount:
            console.print("[yellow]Amount required when not using MAX.[/]")
            return

    params: Dict[str, Any] = {
        "coin": coin,
        "to": to_addr,
        "priv_key_policy": {"type": "WalletConnect", "session_topic": topic},
    }
    if max_withdraw:
        params["max"] = True
    else:
        params["amount"] = amount

    _legacy_withdraw(processor, console, params)


# --------------------------------------------------------------------------------------
# Broadcast raw transaction
# --------------------------------------------------------------------------------------

def _handle_send_raw_tx(processor: ApiRequestProcessor, console: Console):
    """Broadcast a signed transaction hex via `send_raw_transaction`."""

    coin = Prompt.ask("Coin ticker (leave blank if not required)").strip().upper()
    tx_hex = Prompt.ask("Enter signed transaction hex").strip()
    if not tx_hex:
        console.print("[yellow]Transaction hex is required.[/]")
        return

    req = {
        "method": "send_raw_transaction",
        "mmrpc": "2.0",
        "params": {
            "tx_hex": tx_hex,
        },
        "id": 0,
        "userpass": ACTIVE_NODE.userpass,
    }
    if coin:
        req["params"]["coin"] = coin

    resp = _rpc(processor, req)
    if "error" in resp:
        console.print(f"[red]Broadcast failed: {resp['error']}[/]")
    else:
        console.print("[green]Broadcast result:[/]")
        console.print_json(json.dumps(resp, indent=2))


# --------------------------------------------------------------------------------------
# Entrypoint
# --------------------------------------------------------------------------------------


if __name__ == "__main__":
    main()