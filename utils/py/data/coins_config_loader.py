#!/usr/bin/env python3
"""
Coins Configuration Loader

This module provides functionality to load and query the coins_config.json file
to provide contextually appropriate examples based on coin protocol types and
other configuration data.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .logging_utils import get_logger
from ..constants import CoinConfig




class CoinsConfigLoader:
    """Loader for coins configuration data."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the coins config loader."""
        self.logger = get_logger("coins-config-loader")
        
        # Default path to coins_config.json
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "data" / "coins" / "coins_config.json"
        
        self.config_path = config_path
        self._coins_data: Optional[Dict[str, Any]] = None
        self._coins_by_protocol: Optional[Dict[str, List[CoinConfig]]] = None
        
    def load_config(self) -> bool:
        """Load the coins configuration from file."""
        try:
            if not self.config_path.exists():
                self.logger.error(f"Coins config file not found: {self.config_path}")
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._coins_data = json.load(f)
            
            self.logger.info(f"✅ Loaded {len(self._coins_data)} coins from config")
            self._build_protocol_index()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load coins config: {e}")
            return False
    
    def _build_protocol_index(self):
        """Build an index of coins by protocol type."""
        if not self._coins_data:
            return
        
        self._coins_by_protocol = {}
        
        for coin_ticker, config in self._coins_data.items():
            try:
                coin_config = CoinConfig.from_config_dict(coin_ticker, config)
                protocol_type = coin_config.protocol_type
                
                if protocol_type not in self._coins_by_protocol:
                    self._coins_by_protocol[protocol_type] = []
                
                self._coins_by_protocol[protocol_type].append(coin_config)
                
            except Exception as e:
                self.logger.debug(f"Skipping coin {coin_ticker}: {e}")
        
        self.logger.info(f"📊 Indexed coins by protocol: {list(self._coins_by_protocol.keys())}")
    
    def get_coin_config(self, coin_ticker: str) -> Optional[CoinConfig]:
        """Get configuration for a specific coin."""
        if not self._coins_data:
            self.load_config()
        
        if not self._coins_data or coin_ticker not in self._coins_data:
            return None
        
        try:
            return CoinConfig.from_config_dict(coin_ticker, self._coins_data[coin_ticker])
        except Exception as e:
            self.logger.debug(f"Failed to parse config for {coin_ticker}: {e}")
            return None
    
    def get_coins_by_protocol(self, protocol_type: str) -> List[CoinConfig]:
        """Get all coins of a specific protocol type."""
        if not self._coins_by_protocol:
            self.load_config()
        
        if not self._coins_by_protocol:
            return []
        
        return self._coins_by_protocol.get(protocol_type, [])
    
    def get_example_coin_for_method(self, method_name: str) -> Optional[CoinConfig]:
        """Get an appropriate example coin based on the method name."""
        if not self._coins_by_protocol:
            self.load_config()
        
        if not self._coins_by_protocol:
            return None
        
        # Method-specific coin selection logic
        if "erc20" in method_name.lower():
            # For ERC20 methods, use ERC20 tokens
            erc20_coins = self.get_coins_by_protocol("ERC20")
            if erc20_coins:
                # Prefer well-known tokens like USDT
                for coin in erc20_coins:
                    if coin.coin in ["USDT-ERC20", "1INCH-ERC20", "USDC-ERC20"]:
                        return coin
                # Fall back to first available ERC20 token
                return erc20_coins[0]
        
        elif "bch" in method_name.lower():
            # For BCH methods, use BCH
            bch_coins = self.get_coins_by_protocol("BCH")
            if bch_coins:
                return bch_coins[0]
        
        elif "eth" in method_name.lower():
            # For ETH methods, use ETH
            eth_coins = self.get_coins_by_protocol("ETH")
            if eth_coins:
                return eth_coins[0]
        
        elif "lightning" in method_name.lower():
            # For Lightning methods, use Bitcoin
            btc_coins = self.get_coins_by_protocol("UTXO")
            for coin in btc_coins:
                if coin.coin in ["BTC", "tBTC"]:
                    return coin
        
        elif "utxo" in method_name.lower():
            # For UTXO methods, use KMD or other UTXO coins
            utxo_coins = self.get_coins_by_protocol("UTXO")
            if utxo_coins:
                # Prefer KMD for UTXO examples
                for coin in utxo_coins:
                    if coin.coin == "KMD":
                        return coin
                # Fall back to first UTXO coin
                return utxo_coins[0]
        
        elif "tendermint" in method_name.lower():
            # For Tendermint methods, use Cosmos-based coins
            tendermint_coins = self.get_coins_by_protocol("TENDERMINT")
            if tendermint_coins:
                return tendermint_coins[0]
        
        elif "qtum" in method_name.lower():
            # For QTUM methods, use QTUM
            qtum_coins = self.get_coins_by_protocol("QTUM")
            if qtum_coins:
                return qtum_coins[0]
        
        elif "z_coin" in method_name.lower() or "zcoin" in method_name.lower():
            # For Z-coin methods, use privacy coins
            zcoin_coins = self.get_coins_by_protocol("ZHTLC")
            if zcoin_coins:
                return zcoin_coins[0]
        
        # Default fallback - use KMD for general examples
        kmd_config = self.get_coin_config("KMD")
        if kmd_config:
            return kmd_config
        
        # Ultimate fallback - use first available coin
        if self._coins_by_protocol:
            for protocol_coins in self._coins_by_protocol.values():
                if protocol_coins:
                    return protocol_coins[0]
        
        return None
    
    def get_activation_params_example(self, coin_config: CoinConfig) -> Dict[str, Any]:
        """Generate appropriate activation parameters for a coin with multiple servers."""
        if coin_config.protocol_type == "ERC20":
            # ERC20 token activation - use multiple Ethereum RPC nodes
            rpc_nodes = self._get_preferred_rpc_nodes(coin_config.nodes, "Ethereum")
            return {
                "mode": {
                    "rpc": "Ethereum",
                    "rpc_data": {
                        "rpc_nodes": rpc_nodes
                    }
                }
            }
        
        elif coin_config.protocol_type == "UTXO":
            # UTXO coin activation - use multiple electrum servers
            electrum_servers = self._get_preferred_electrum_servers(coin_config.electrum)
            return {
                "mode": {
                    "rpc": "Electrum",
                    "rpc_data": {
                        "electrum_servers": electrum_servers
                    }
                }
            }
        
        elif coin_config.protocol_type == "ETH":
            # Ethereum activation - use multiple RPC nodes
            rpc_nodes = self._get_preferred_rpc_nodes(coin_config.nodes, "Ethereum")
            return {
                "mode": {
                    "rpc": "Ethereum",
                    "rpc_data": {
                        "rpc_nodes": rpc_nodes
                    }
                }
            }
        
        else:
            # Generic activation
            return {
                "mode": {
                    "rpc": "Native",
                    "rpc_data": {}
                }
            }
    
    def _get_preferred_rpc_nodes(self, nodes: Optional[List[Dict[str, Any]]], protocol_type: str) -> List[Dict[str, Any]]:
        """Get preferred RPC nodes with cipig/komodo preference and SSL/WSS over TCP."""
        if not nodes:
            # Fallback to default servers
            if protocol_type == "Ethereum":
                return [
                    {"url": "https://eth3.cipig.net:18555"},
                    {"url": "https://node.komodo.earth:8080/ethereum"},
                    {"url": "https://eth.drpc.org"}
                ]
            else:
                return [{"url": "https://node.komodo.earth:8080"}]
        
        # Sort nodes by preference: cipig/komodo first, SSL/WSS over TCP
        preferred_nodes = []
        other_nodes = []
        
        for node in nodes:
            url = node.get("url", "")
            ws_url = node.get("ws_url", "")
            
            # Check if it's a preferred domain
            is_preferred = any(domain in url.lower() for domain in ["cipig", "komodo"])
            
            # Prefer HTTPS/WSS over HTTP/TCP
            is_secure = url.startswith("https://") or url.startswith("wss://")
            
            node_entry = {"url": url}
            
            # Add WebSocket URL if available and secure
            if ws_url and ws_url.startswith("wss://"):
                node_entry["ws_url"] = ws_url
            
            if is_preferred:
                preferred_nodes.append((node_entry, is_secure))
            else:
                other_nodes.append((node_entry, is_secure))
        
        # Sort by security (secure first)
        preferred_nodes.sort(key=lambda x: x[1], reverse=True)
        other_nodes.sort(key=lambda x: x[1], reverse=True)
        
        # Combine and take up to 3 nodes
        final_nodes = []
        
        # Add preferred nodes first
        for node_entry, _ in preferred_nodes:
            if len(final_nodes) < 3:
                final_nodes.append(node_entry)
        
        # Add other nodes if we need more
        for node_entry, _ in other_nodes:
            if len(final_nodes) < 3:
                final_nodes.append(node_entry)
        
        # Ensure we have at least one node
        if not final_nodes and nodes:
            final_nodes = [{"url": nodes[0].get("url", "")}]
        
        return final_nodes
    
    def _get_preferred_electrum_servers(self, electrum_servers: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Get preferred electrum servers with cipig/komodo preference and SSL over TCP."""
        if not electrum_servers:
            # Fallback to default cipig electrum servers
            return [
                {"url": "electrum1.cipig.net:10001"},
                {"url": "electrum2.cipig.net:10001"},
                {"url": "electrum3.cipig.net:20001", "protocol": "SSL"}
            ]
        
        # Sort electrum servers by preference
        preferred_servers = []
        other_servers = []
        
        for server in electrum_servers:
            url = server.get("url", "")
            protocol = server.get("protocol", "TCP")
            
            # Check if it's a preferred domain
            is_preferred = any(domain in url.lower() for domain in ["cipig", "komodo"])
            
            # Prefer SSL over TCP
            is_secure = protocol.upper() == "SSL"
            
            server_entry = {"url": url}
            if protocol and protocol.upper() in ["SSL", "WSS"]:
                server_entry["protocol"] = protocol
            
            # Add WebSocket URL if available
            if "ws_url" in server:
                server_entry["ws_url"] = server["ws_url"]
            
            if is_preferred:
                preferred_servers.append((server_entry, is_secure))
            else:
                other_servers.append((server_entry, is_secure))
        
        # Sort by security (secure first)
        preferred_servers.sort(key=lambda x: x[1], reverse=True)
        other_servers.sort(key=lambda x: x[1], reverse=True)
        
        # Combine and take up to 3 servers
        final_servers = []
        
        # Add preferred servers first
        for server_entry, _ in preferred_servers:
            if len(final_servers) < 3:
                final_servers.append(server_entry)
        
        # Add other servers if we need more
        for server_entry, _ in other_servers:
            if len(final_servers) < 3:
                final_servers.append(server_entry)
        
        # Ensure we have at least one server
        if not final_servers and electrum_servers:
            final_servers = [{"url": electrum_servers[0].get("url", "")}]
        
        return final_servers
    
    def get_available_protocols(self) -> List[str]:
        """Get list of all available protocol types."""
        if not self._coins_by_protocol:
            self.load_config()
        
        return list(self._coins_by_protocol.keys()) if self._coins_by_protocol else [] 