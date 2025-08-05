#!/usr/bin/env python3
"""
Withdraw Chain Workflow

This utility orchestrates a round-robin withdraw chain across four local KDF
nodes (A → B → C → D → A). It alternates between the task-managed withdraw
flow and the legacy `withdraw` RPC, then broadcasts each unsigned transaction
with `send_raw_transaction`.

Coins covered (one chain each):
    • DOC     – UTXO protocol example
    • MATIC   – EVM protocol example
    • IRIS    – Tendermint protocol example
    • ZOMBIE  – Z-HTLC protocol example
    • SCZEN   – UTXO-Shielded protocol example

Usage (from repository root, after the Docker stack is running and the Python
virtual-env activated):

    source utils/py/.venv/bin/activate
    python -m utils.py.lib.workflows.withdraw_chain

The script expects the default local node configuration defined in
`EnhancedKomodoConfig` – namely the following services/ports:
    A) kdf_native_nonhd  – http://127.0.0.1:8778
    B) kdf_native_hd     – http://127.0.0.1:8779
    C) kdf_wasm_hd       – http://127.0.0.1:8780
    D) kdf_wasm_nonhd    – http://127.0.0.1:8781

If fewer than four nodes are available the script aborts early.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Any
import json
from pathlib import Path

import requests
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel

from constants.config_struct import EnhancedKomodoConfig, NodeConfig
from lib.utils.logging_utils import get_logger
from lib.api_client.kdf_api_processor import ApiRequestProcessor


class WithdrawChain:
    """High-level helper that builds and broadcasts withdraw transactions."""

    def __init__(self, coins: List[str], amount: str = "0.01") -> None:
        self.coins = coins
        self.amount = amount
        self.config = EnhancedKomodoConfig()
        # Treat the first four configured nodes as A, B, C, D
        self.nodes: List[NodeConfig] = self.config.nodes[:4]
        if len(self.nodes) < 4:
            raise RuntimeError("Configuration must define at least four nodes.")

        self.logger = get_logger("withdraw-chain")
        self.console = Console()
        # Load local coins_config to build explorer links
        self._coins_cfg_path = Path(__file__).resolve().parent.parent.parent / "data" / "coins" / "coins_config.json"
        try:
            with open(self._coins_cfg_path, "r", encoding="utf-8") as fp:
                self.coins_config = json.load(fp)
        except Exception:
            self.coins_config = {}
            self.logger.warning(f"Could not load coins config from {self._coins_cfg_path}")

        self.processor = ApiRequestProcessor(config=self.config, logger=self.logger)
        # Mapping coin -> node_name -> address
        self.address_book: Dict[str, Dict[str, str]] = {}

    # ------------------------------------------------------------------
    # Low-level RPC helpers
    # ------------------------------------------------------------------
    def _rpc(self, node: NodeConfig, method: str, **extra_fields) -> Dict:
        """Send an RPC request to *node* and return decoded JSON."""
        body: Dict = {
            "userpass": node.userpass,
            "mmrpc": "2.0",
            "id": int(time.time() * 1000) % 1_000_000,  # simple unique id
            "method": method,
        }
        body.update(extra_fields)

        self.logger.info(f"[{node.name}] → {method}")
        resp = requests.post(node.api_url, json=body, timeout=90)
        try:
            resp.raise_for_status()
            data: Dict = resp.json()
        except requests.exceptions.HTTPError:
            # Attempt to parse error JSON if provided
            try:
                data = resp.json()
            except ValueError:
                data = {"error": resp.text}
            error_type = data.get("error_type") or "Unknown"
            self.logger.warning(
                f"RPC call {method} on {node.name} failed – HTTP {resp.status_code} – errorType: {error_type}"
            )
            return {"error": data.get("error"), "error_type": error_type}
        # Normal success path
        if "error" in data:
            # Still an application-level error
            return data
        return data

    def _rpc_params(self, node: NodeConfig, method: str, params: Dict) -> Dict:
        """Helper that places *params* inside the `params` object."""
        return self._rpc(node, method, params=params)

    # ------------------------------------------------------------------
    # Wallet helpers
    # ------------------------------------------------------------------
    def _get_new_address(self, node: NodeConfig, coin: str) -> Optional[str]:
        """Return a fresh external address for *coin* on *node*."""
        params: Dict[str, Any] = {"coin": coin}
        if node.hd_mode:
            params["account_id"] = 0
        resp = self._rpc_params(node, "get_new_address", params)
        if resp.get("error"):
            err_type = resp.get("error_type", "Unknown")
            if not node.hd_mode:
                # Expected – coin might be HD-only
                self.logger.info(
                    f"Non-HD node '{node.name}' failed as expected with HD-only method 'get_new_address'. errorType: {err_type}"
                )
            else:
                self.logger.warning(
                    f"get_new_address failed on {node.name} for {coin}. errorType: {err_type}"
                )
            return None
        address: Optional[str] = (
            resp.get("new_address", {}).get("address")
            or resp.get("result", {}).get("address")
            or resp.get("address")
            or (resp.get("result", {}).get("new_address", {}).get("address") if isinstance(resp.get("result"), dict) else None)
        )
        if not address:
            self.logger.warning(f"No address returned for {coin} on {node.name}")
            return None
        return address

    def _get_balance(self, node: NodeConfig, coin: str) -> Optional[str]:
        """Return wallet balance string for *coin* on *node* (or None on error)."""
        try:
            # First attempt – v2 style (params object)
            resp = self._rpc_params(node, "my_balance", {"coin": coin})
            if resp.get("error_type") == "NoSuchMethod":
                # Fallback to v1 style (coin at top level, mmrpc omitted)
                resp = self._rpc(node, "my_balance", coin=coin)
        except Exception as exc:
            self.logger.warning(f"Balance fetch failed for {coin} on {node.name}: {exc}")
            return None
        if resp.get("error"):
            return None
        bal = resp.get("result", {}).get("balance") or resp.get("balance")
        if isinstance(bal, (int, float, str)):
            return str(bal)
        return None

    # ------------------------------------------------------------------
    # Task-managed withdraw flow
    # ------------------------------------------------------------------
    def _wait_task_completed(
        self,
        node: NodeConfig,
        task_id: int,
        poll_method: str,
        *,
        timeout: int = 180,
        sleep_s: int = 5,
    ) -> Dict:
        start = time.time()
        while time.time() - start < timeout:
            status_resp = self._rpc_params(node, poll_method, {"task_id": task_id})
            status = status_resp.get("status") or status_resp.get("result", {}).get("status")
            if status in {"Completed", "Success", "Finished"}:
                return status_resp
            if status in {"Failed", "Cancelled"}:
                raise RuntimeError(f"Task {task_id} ended with status {status}")
            time.sleep(sleep_s)
        raise TimeoutError(f"Task {task_id} on {node.name} did not finish within {timeout}s")

    def _task_withdraw(self, src: NodeConfig, coin: str, dest_addr: str) -> str:
        """Run the task-managed withdraw sequence and return *tx_hex*."""
        init_resp = self._rpc_params(
            src,
            "task::withdraw::init",
            {"coin": coin, "to": dest_addr, "amount": self.amount},
        )
        task_id = init_resp.get("task_id")
        if task_id is None:
            raise RuntimeError("task::withdraw::init did not return task_id")

        status_resp = self._wait_task_completed(src, task_id, "task::withdraw::status")
        tx_hex: Optional[str] = (
            status_resp.get("tx_hex")
            or status_resp.get("result", {}).get("tx_hex")
            or status_resp.get("result", {}).get("transaction", {}).get("tx_hex")
        )
        if not tx_hex:
            raise RuntimeError("Could not find tx_hex in task-withdraw status response")
        return tx_hex

    # ------------------------------------------------------------------
    # Legacy withdraw flow
    # ------------------------------------------------------------------
    def _legacy_withdraw(self, src: NodeConfig, coin: str, dest_addr: str) -> str:
        """Run the legacy `withdraw` RPC and return *tx_hex*."""
        resp = self._rpc_params(
            src,
            "withdraw",
            {"coin": coin, "to": dest_addr, "amount": self.amount},
        )
        tx_hex: Optional[str] = (
            resp.get("tx_hex")
            or resp.get("result", {}).get("tx_hex")
            or resp.get("result", {}).get("withdraw_tx")  # fallback key
        )
        if not tx_hex:
            raise RuntimeError("Could not find tx_hex in withdraw response")
        return tx_hex

    # ------------------------------------------------------------------
    # Broadcasting helper
    # ------------------------------------------------------------------
    def _build_tx_url(self, coin: str, tx_hash: str) -> Optional[str]:
        cfg = self.coins_config.get(coin)
        if not cfg:
            return None
        base = cfg.get("explorer_url", "")
        path = cfg.get("explorer_tx_url", "")
        if "{TXID}" in path:
            path = path.replace("{TXID}", tx_hash)
            return f"{base}{path}"
        return f"{base}{path}{tx_hash}"

    def _broadcast(self, src: NodeConfig, coin: str, tx_hex: str) -> str:
        """Broadcast *tx_hex* and return tx_hash (if any)."""
        resp = self._rpc(src, "send_raw_transaction", coin=coin, tx_hex=tx_hex)
        tx_hash = resp.get("tx_hash") or resp.get("result", {}).get("tx_hash")
        return tx_hash or ""

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------
    def run(self) -> None:
        self.logger.start("Starting withdraw-chain workflow")

        for coin in self.coins:
            self.logger.separator(f"=== Processing {coin} ===")

            # Pre-fetch destination addresses for all nodes
            addresses: Dict[str, str] = {}
            for node in self.nodes:
                addresses[node.name] = self._get_new_address(node, coin)
                self.logger.info(f"[{node.name}] {coin} address → {addresses[node.name]}")

            # Execute round-robin transfers (A→B→C→D→A)
            for idx, src_node in enumerate(self.nodes):
                dest_node = self.nodes[(idx + 1) % len(self.nodes)]
                dest_addr = self.address_book.get(coin, {}).get(dest_node.name)
                if not dest_addr:
                    self.logger.info(
                        f"Skipping hop {src_node.name} → {dest_node.name} for {coin} (destination node unsupported)."
                    )
                    continue
                use_task = idx % 2 == 0  # Alternate between task and legacy

                try:
                    if use_task:
                        tx_hex = self._task_withdraw(src_node, coin, dest_addr)
                    else:
                        tx_hex = self._legacy_withdraw(src_node, coin, dest_addr)

                    tx_hash = self._broadcast(src_node, coin, tx_hex)
                    tx_url = self._build_tx_url(coin, tx_hash) if tx_hash else None
                    self.logger.success(
                        f"[{coin}] {src_node.name} → {dest_node.name} broadcasted successfully (tx: {tx_hash})"
                    )
                    if tx_url:
                        self.console.print(f"[blue]Explorer:[/] {tx_url}")
                except Exception as exc:
                    self.logger.error(
                        f"Withdraw step failed for {coin} from {src_node.name} to {dest_node.name}: {exc}"
                    )
                    raise  # Abort entire workflow on first failure

            # Display balances after processing coin
            self._display_balances(coin)

        self.logger.finish("Withdraw-chain workflow completed successfully")

    def _display_balances(self, coin: str) -> None:
        """Show a table of balances for *coin* across all nodes."""
        table = Table(title=f"{coin} balances", show_lines=True)
        table.add_column("Node", style="cyan")
        table.add_column("Balance", justify="right")
        for node in self.nodes:
            bal = self._get_balance(node, coin) or "?"
            table.add_row(node.name, bal)
        self.console.print(table)

    def prepare_coin(self, coin: str) -> None:
        """Activate *coin* on all nodes and prefetch addresses/balances."""
        self.console.rule(f"[bold green]Preparing {coin}")
        # 1. Activation
        for node in self.nodes:
            if self.processor.activate_coin(coin, node=node):
                continue  # success first try

            self.logger.info(f"Attempting to disable '{coin}' on {node.name} and retry activation…")
            if self.processor.disable_coin(coin, node=node):
                if self.processor.activate_coin(coin, node=node):
                    continue  # success after disable

            # Still failed – log and mark unsupported
            self.logger.warning(
                f"Node {node.name} could not activate {coin}. It will be skipped for this coin."
            )
            # Mark address as None later

        # 2. Prefetch addresses
        book: Dict[str, str] = {}
        for node in self.nodes:
            addr = self._get_new_address(node, coin)
            book[node.name] = addr
        self.address_book[coin] = book
        # 3. Show addresses & balances
        addr_table = Table(title=f"{coin} destination addresses", show_lines=True)
        addr_table.add_column("Node", style="cyan")
        addr_table.add_column("Address")
        for node in self.nodes:
            addr_table.add_row(node.name, book[node.name] or "n/a")
        self.console.print(addr_table)
        self._display_balances(coin)

    def disable_all_coins(self):
        """Disable every currently enabled coin on all nodes for a clean slate."""
        self.console.rule("[bold red]Disabling all active coins on every node")
        for node in self.nodes:
            # Refresh enabled list first
            self.processor._update_enabled_coins(node=node)
            coins = sorted(self.processor.enabled_coins.get(node.name, []))
            if not coins:
                self.console.print(f"[green]No coins active on {node.name}.")
                continue
            for c in coins:
                if self.processor.disable_coin(c, node=node):
                    self.console.print(f"[cyan]{node.name}[/] → disabled {c}")
                else:
                    self.console.print(f"[yellow]{node.name}[/] → could not disable {c}")
        self.console.rule("[bold red]Disable-all pass complete")


# ----------------------------------------------------------------------
# Script entry-point
# ----------------------------------------------------------------------
if __name__ == "__main__":
    console = Console()
    console.print(Panel("[bold magenta]Withdraw Chain TUI[/]", subtitle="Komodo DeFi Framework"))

    default_coins = "DOC,MATIC,IRIS,ZOMBIE,SCZEN"
    coins_input = Prompt.ask("Enter comma-separated coin tickers", default=default_coins)
    coins_list = [c.strip() for c in coins_input.split(",") if c.strip()]

    chain = WithdrawChain(coins_list)

    # Clean slate – disable any previously active coins
    chain.disable_all_coins()

    # Activation, address & balance readout
    for coin in coins_list:
        chain.prepare_coin(coin)

    amount_input = Prompt.ask("Withdrawal amount per hop", default="0.01")
    chain.amount = amount_input

    if Confirm.ask("Start withdraw chain now?", default=True):
        chain.run()
    else:
        console.print("[yellow]Aborted by user.[/]") 