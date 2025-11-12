#!/usr/bin/env python3
"""
Wallet Manager - Handles address and balance tracking for KDF instances.

This module provides a clean interface for collecting and managing wallet addresses
and balances from various KDF method responses.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path

try:
    from ..utils.json_utils import dump_sorted_json
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from utils.json_utils import dump_sorted_json


@dataclass
class WalletAddress:
    """Represents a single wallet address with its balance information."""
    address: str
    coin: str
    balance_spendable: str = "0"
    balance_unspendable: str = "0"
    instance_name: str = ""
    source_method: str = ""
    
    @property
    def balance_display(self) -> str:
        """Get formatted balance string for display."""
        if self.balance_unspendable and self.balance_unspendable != "0":
            return f"{self.balance_spendable} (unspendable: {self.balance_unspendable})"
        return self.balance_spendable
    
    @property
    def total_balance(self) -> float:
        """Calculate total balance as float."""
        try:
            spendable = float(self.balance_spendable) if self.balance_spendable else 0.0
            unspendable = float(self.balance_unspendable) if self.balance_unspendable else 0.0
            return spendable + unspendable
        except (ValueError, TypeError):
            return 0.0
    
    def update_balance(self, spendable: str, unspendable: str = "0"):
        """Update balance information."""
        self.balance_spendable = spendable
        self.balance_unspendable = unspendable
    
    def __str__(self):
        return f"{self.coin}:{self.address} = {self.balance_display}"


class WalletManager:
    """Manages wallet addresses and balances across KDF instances."""
    
    def __init__(self, workspace_root: Path):
        """Initialize the wallet manager."""
        self.workspace_root = workspace_root
        self.logger = logging.getLogger(__name__)
        
        # Storage: instance_name -> coin -> address -> WalletAddress
        self.addresses: Dict[str, Dict[str, Dict[str, WalletAddress]]] = {}
    
    def add_address(self, instance_name: str, coin: str, address: str, 
                   spendable: str = "0", unspendable: str = "0", 
                   source_method: str = "") -> WalletAddress:
        """Add or update a wallet address."""
        # Initialize nested dictionaries if needed
        if instance_name not in self.addresses:
            self.addresses[instance_name] = {}
        if coin not in self.addresses[instance_name]:
            self.addresses[instance_name][coin] = {}
        
        # Create or update the address
        if address in self.addresses[instance_name][coin]:
            # Update existing address
            wallet_address = self.addresses[instance_name][coin][address]
            wallet_address.update_balance(spendable, unspendable)
            if source_method:
                wallet_address.source_method = source_method
        else:
            # Create new address
            wallet_address = WalletAddress(
                address=address,
                coin=coin,
                balance_spendable=spendable,
                balance_unspendable=unspendable,
                instance_name=instance_name,
                source_method=source_method
            )
            self.addresses[instance_name][coin][address] = wallet_address
        
        self.logger.info(f"Added address: {instance_name}/{coin}/{address} = {wallet_address.balance_display}")
        return wallet_address
    
    def get_addresses_for_coin(self, instance_name: str, coin: str) -> List[WalletAddress]:
        """Get all addresses for a specific coin on an instance."""
        if instance_name in self.addresses and coin in self.addresses[instance_name]:
            return list(self.addresses[instance_name][coin].values())
        return []
    
    def get_all_addresses_for_instance(self, instance_name: str) -> List[WalletAddress]:
        """Get all addresses for a specific instance."""
        all_addresses = []
        if instance_name in self.addresses:
            for coin_addresses in self.addresses[instance_name].values():
                all_addresses.extend(coin_addresses.values())
        return all_addresses
    
    def get_instance_summary(self, instance_name: str) -> Dict[str, int]:
        """Get summary statistics for an instance."""
        addresses = self.get_all_addresses_for_instance(instance_name)
        coins = set(addr.coin for addr in addresses)
        
        return {
            "total_addresses": len(addresses),
            "total_coins": len(coins),
            "coins": sorted(coins)
        }
    
    def extract_addresses_from_response(self, instance_name: str, method_name: str, 
                                      response_data: Dict[str, Any], 
                                      request_data: Optional[Dict[str, Any]] = None):
        """Extract address and balance information from method responses."""
        if not isinstance(response_data, dict):
            return
        
        try:
            # Handle legacy electrum/enable responses with direct address/balance fields
            if "address" in response_data and "coin" in response_data:
                coin = response_data["coin"]
                address = response_data["address"]
                balance = response_data.get("balance", "0")
                unspendable = response_data.get("unspendable_balance", "0")
                
                self.add_address(instance_name, coin, address, balance, unspendable, method_name)
                
            # Handle account_balance responses (HD wallets)
            elif "task::account_balance::status" in method_name and "result" in response_data:
                self._extract_from_account_balance(instance_name, response_data["result"], method_name)
                
            # Handle get_enabled_coins responses (legacy - includes addresses)
            elif method_name == "get_enabled_coins" and isinstance(response_data, list):
                self._extract_from_enabled_coins(instance_name, response_data, method_name)
                
            # Handle coin activation responses with address info
            elif "result" in response_data and isinstance(response_data["result"], dict):
                self._extract_from_activation_response(instance_name, method_name, 
                                                     response_data["result"], request_data)
                
        except Exception as e:
            self.logger.info(f"Error extracting addresses from {method_name} response: {e}")
    
    def _extract_from_account_balance(self, instance_name: str, result: Dict[str, Any], method_name: str):
        """Extract addresses from account_balance responses."""
        if isinstance(result, dict) and result.get("status") == "Ok" and "details" in result:
            details = result["details"]
            if "addresses" in details:
                for addr_info in details["addresses"]:
                    address = addr_info.get("address")
                    balance_info = addr_info.get("balance", {})
                    
                    if address and balance_info:
                        for coin, coin_balance in balance_info.items():
                            spendable = coin_balance.get("spendable", "0")
                            unspendable = coin_balance.get("unspendable", "0")
                            self.add_address(instance_name, coin, address, spendable, unspendable, method_name)
    
    def _extract_from_enabled_coins(self, instance_name: str, response_data: List, method_name: str):
        """Extract addresses from get_enabled_coins responses."""
        for coin_info in response_data:
            if isinstance(coin_info, dict) and "ticker" in coin_info and "address" in coin_info:
                coin = coin_info["ticker"]
                address = coin_info["address"]
                # For get_enabled_coins, we don't have balance info, so mark as "enabled"
                self.add_address(instance_name, coin, address, "enabled", "0", method_name)
    
    def _extract_from_activation_response(self, instance_name: str, method_name: str, 
                                        result: Dict[str, Any], request_data: Optional[Dict[str, Any]] = None):
        """Extract addresses from various coin activation response formats."""
        try:
            # Handle task completion responses
            if isinstance(result, dict) and result.get("status") == "Ok" and "details" in result:
                self._extract_from_task_details(instance_name, result["details"], method_name)
            
            # Handle direct activation responses
            if isinstance(result, dict) and "address" in result and "ticker" in result:
                self._extract_from_direct_activation(instance_name, result, method_name)
            
            # Handle HD wallet responses
            if isinstance(result, dict) and "wallet_balance" in result:
                self._extract_from_wallet_balance(instance_name, result["wallet_balance"], method_name)
            
            # Handle ETH/Polygon non-HD responses (erc20_addresses_infos, eth_addresses_infos)
            self._extract_from_addresses_infos(instance_name, result, method_name)
            
            # Handle token activation responses
            if isinstance(result, dict) and "balances" in result and isinstance(result["balances"], dict):
                self._extract_from_token_balances(instance_name, result, method_name, request_data)
                
        except Exception as e:
            self.logger.info(f"Error extracting from activation response: {e}")
    
    def _extract_from_task_details(self, instance_name: str, details: Dict[str, Any], method_name: str):
        """Extract addresses from task completion details."""
        # HD wallet format with wallet_balance
        if "wallet_balance" in details and "ticker" in details:
            ticker = details["ticker"]
            self._extract_from_wallet_balance(instance_name, details["wallet_balance"], method_name, ticker)
        
        # Tendermint format (single address with balance and tokens)
        elif "address" in details and "ticker" in details:
            ticker = details["ticker"]
            address = details["address"]
            
            # Main coin balance
            if "balance" in details:
                balance = details["balance"]
                spendable = balance.get("spendable", "0")
                unspendable = balance.get("unspendable", "0")
                self.add_address(instance_name, ticker, address, spendable, unspendable, method_name)
            
            # Token balances
            if "tokens_balances" in details:
                for token_name, token_balance in details["tokens_balances"].items():
                    spendable = token_balance.get("spendable", "0")
                    unspendable = token_balance.get("unspendable", "0")
                    self.add_address(instance_name, token_name, address, spendable, unspendable, method_name)
    
    def _extract_from_direct_activation(self, instance_name: str, result: Dict[str, Any], method_name: str):
        """Extract addresses from direct activation responses."""
        ticker = result["ticker"]
        address = result["address"]
        
        # Main coin balance
        if "balance" in result:
            balance = result["balance"]
            spendable = balance.get("spendable", "0")
            unspendable = balance.get("unspendable", "0")
            self.add_address(instance_name, ticker, address, spendable, unspendable, method_name)
        
        # Token balances
        if "tokens_balances" in result:
            for token_name, token_balance in result["tokens_balances"].items():
                spendable = token_balance.get("spendable", "0")
                unspendable = token_balance.get("unspendable", "0")
                self.add_address(instance_name, token_name, address, spendable, unspendable, method_name)
    
    def _extract_from_wallet_balance(self, instance_name: str, wallet_balance: Dict[str, Any], 
                                   method_name: str, default_ticker: str = None):
        """Extract addresses from wallet_balance structures."""
        if isinstance(wallet_balance, dict):
            # HD wallet with accounts
            if "accounts" in wallet_balance:
                for account in wallet_balance["accounts"]:
                    if "addresses" in account:
                        for addr_info in account["addresses"]:
                            address = addr_info.get("address")
                            balance_info = addr_info.get("balance", {})
                            
                            if address and balance_info:
                                for coin, coin_balance in balance_info.items():
                                    spendable = coin_balance.get("spendable", "0")
                                    unspendable = coin_balance.get("unspendable", "0")
                                    self.add_address(instance_name, coin, address, spendable, unspendable, method_name)
            
            # Iguana wallet format
            elif "address" in wallet_balance and "balance" in wallet_balance:
                address = wallet_balance["address"]
                balance_info = wallet_balance["balance"]
                
                if address and balance_info:
                    for coin, coin_balance in balance_info.items():
                        spendable = coin_balance.get("spendable", "0")
                        unspendable = coin_balance.get("unspendable", "0")
                        self.add_address(instance_name, coin, address, spendable, unspendable, method_name)
    
    def _extract_from_addresses_infos(self, instance_name: str, result: Dict[str, Any], method_name: str):
        """Extract addresses from various addresses_infos structures."""
        if not isinstance(result, dict):
            return
        
        for key in result:
            if key.endswith("_addresses_infos"):
                addresses_info = result[key]
                if isinstance(addresses_info, dict):
                    for address, addr_data in addresses_info.items():
                        if "balances" in addr_data:
                            balances = addr_data["balances"]
                            
                            if isinstance(balances, dict):
                                # Platform coin format: {"spendable": "0", "unspendable": "0"}
                                if "spendable" in balances:
                                    coin = key.replace("_addresses_infos", "").upper()
                                    if coin != "ERC20":  # Skip ERC20, handled in token section
                                        spendable = balances.get("spendable", "0")
                                        unspendable = balances.get("unspendable", "0")
                                        self.add_address(instance_name, coin, address, spendable, unspendable, method_name)
                                
                                # Token format: {"TOKEN-NAME": {"spendable": "0", "unspendable": "0"}}
                                else:
                                    for token_name, token_balance in balances.items():
                                        if isinstance(token_balance, dict) and "spendable" in token_balance:
                                            spendable = token_balance.get("spendable", "0")
                                            unspendable = token_balance.get("unspendable", "0")
                                            self.add_address(instance_name, token_name, address, spendable, unspendable, method_name)
    
    def _extract_from_token_balances(self, instance_name: str, result: Dict[str, Any], 
                                   method_name: str, request_data: Optional[Dict[str, Any]] = None):
        """Extract addresses from token activation balances."""
        for address, balance_info in result["balances"].items():
            if "spendable" in balance_info:
                # Extract token name from request data
                token_name = self._extract_ticker_from_request_data(request_data) if request_data else "TOKEN"
                spendable = balance_info.get("spendable", "0")
                unspendable = balance_info.get("unspendable", "0")
                self.add_address(instance_name, token_name, address, spendable, unspendable, method_name)
    
    def _extract_ticker_from_request_data(self, request_data: Dict[str, Any]) -> Optional[str]:
        """Extract ticker from request data for token activation methods."""
        if not request_data:
            return None
        
        # Check common ticker locations in request
        if "ticker" in request_data:
            return request_data["ticker"]
        
        # Check in params
        params = request_data.get("params", {})
        if isinstance(params, dict):
            if "ticker" in params:
                return params["ticker"]
            if "coin" in params:
                return params["coin"]
        
        # Check direct coin field
        if "coin" in request_data:
            return request_data["coin"]
        
        return None
    
    def reprocess_responses_for_addresses(self, results: List[Any]):
        """Reprocess all collected responses to extract any addresses we may have missed."""
        self.logger.info("🔄 Reprocessing collected responses to extract any missed addresses...")
        
        addresses_found = 0
        initial_count = self.get_total_addresses_count()
        
        for result in results:
            if hasattr(result, 'instance_responses') and result.instance_responses:
                for instance_name, response_data in result.instance_responses.items():
                    # Skip error responses
                    if isinstance(response_data, dict) and "error" not in response_data:
                        self.extract_addresses_from_response(instance_name, "reprocess", response_data, None)
        
        final_count = self.get_total_addresses_count()
        addresses_found = final_count - initial_count
        
        if addresses_found > 0:
            self.logger.info(f"🎯 Reprocessing found {addresses_found} additional addresses")
        else:
            self.logger.info("📋 No additional addresses found during reprocessing")
    
    def get_total_addresses_count(self) -> int:
        """Get total number of addresses across all instances."""
        return sum(
            len(coin_addresses) 
            for instance_addresses in self.addresses.values()
            for coin_addresses in instance_addresses.values()
        )
    
    def get_address_hint(self, instance_name: str, coin: str) -> Optional[str]:
        """Return a representative address for a given instance/coin.
        
        Prefers in-memory addresses extracted during this run; falls back to the
        latest saved test_addresses.json report if needed.
        """
        try:
            coin = str(coin).upper()
            # Prefer in-memory
            addrs = self.get_addresses_for_coin(instance_name, coin)
            if addrs:
                # Return the first address deterministically by sorting
                first = sorted(a.address for a in addrs if a and a.address)[0]
                return first
            # Fallback to saved report
            report_path = self.workspace_root / "postman/generated/reports/test_addresses.json"
            if report_path.exists():
                import json
                with open(report_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                inst = data.get(instance_name, {})
                coin_map = inst.get(coin) if isinstance(inst, dict) else None
                if isinstance(coin_map, dict) and coin_map:
                    return sorted(coin_map.keys())[0]
        except Exception:
            pass
        return None
    
    def save_test_addresses_report(self, output_file: Path):
        """Save addresses in the test_addresses.json format."""
        # Convert to the expected format: instance -> coin -> {address: balance}
        report_data = {}
        
        for instance_name, instance_addresses in self.addresses.items():
            report_data[instance_name] = {}
            for coin, coin_addresses in instance_addresses.items():
                report_data[instance_name][coin] = {
                    addr.address: addr.balance_display
                    for addr in coin_addresses.values()
                }
        
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save with sorted keys
        dump_sorted_json(report_data, output_file)
        
        # Log summary
        total_instances = len(report_data)
        total_coins = sum(len(instance_data) for instance_data in report_data.values())
        total_addresses = sum(
            len(coin_data) for instance_data in report_data.values()
            for coin_data in instance_data.values()
        )
        
        self.logger.info(f"🏦 Test addresses saved to: {output_file.name}")
        self.logger.info(f"   Instances: {total_instances}, Coins: {total_coins}, Addresses: {total_addresses}")
        
        return {
            "total_instances": total_instances,
            "total_coins": total_coins,
            "total_addresses": total_addresses,
            "report_file": str(output_file),
            "addresses_data": report_data
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of collected addresses."""
        summary = {
            "total_instances": len(self.addresses),
            "instances": {}
        }
        
        for instance_name in self.addresses:
            summary["instances"][instance_name] = self.get_instance_summary(instance_name)
        
        summary["total_addresses"] = self.get_total_addresses_count()
        summary["total_coins"] = len(set(
            coin for instance_addresses in self.addresses.values()
            for coin in instance_addresses.keys()
        ))
        
        return summary
