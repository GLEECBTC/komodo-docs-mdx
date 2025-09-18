#!/usr/bin/env python3
"""
CoinsConfigManager - Efficient management of coins configuration data.

This module provides centralized access to coins configuration with intelligent
caching and single-fetch optimization.
"""

import json
import time
import urllib.request
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# URL to fetch the latest coins configuration
COINS_CONFIG_URL = "https://raw.githubusercontent.com/KomodoPlatform/coins/master/utils/coins_config.json"

@dataclass
class CoinProtocolInfo:
    """Information about a coin's protocol and configuration."""
    protocol_type: str
    nodes: Optional[List[Dict[str, Any]]] = None
    electrum: Optional[List[Dict[str, Any]]] = None
    rpc_urls: Optional[List[Dict[str, Any]]] = None
    swap_contract_address: Optional[str] = None
    fallback_swap_contract: Optional[str] = None
    chain_id: Optional[str] = None
    denom: Optional[str] = None
    contract_address: Optional[str] = None
    required_confirmations: Optional[int] = None


class CoinsConfigManager:
    """Manages coins configuration with efficient caching and fetching."""
    
    def __init__(self, workspace_root: Optional[Path] = None):
        """Initialize the coins config manager.
        
        Args:
            workspace_root: Path to the workspace root. If None, auto-detects.
        """
        if workspace_root is None:
            workspace_root = Path(__file__).parent.parent.parent.parent.parent
        
        self.workspace_root = Path(workspace_root)
        self.logger = logger or logging.getLogger(__name__)
        
        # Cache for coins configuration
        self._coins_config: Optional[Dict[str, Any]] = None
        self._last_fetch_time: float = 0
        self._cache_duration: float = 3600  # 1 hour cache
        
        # Try to load from cache first
        self._load_from_cache()
    
    def _load_from_cache(self) -> None:
        """Try to load coins config from local cache file."""
        cache_file = self.workspace_root / "tmp" / "coins_config_cache.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # Check if cache is still valid (within cache duration)
                cache_time = cache_data.get('timestamp', 0)
                if time.time() - cache_time < self._cache_duration:
                    self._coins_config = cache_data.get('data', {})
                    self._last_fetch_time = cache_time
                    self.logger.debug(f"Loaded coins config from cache ({len(self._coins_config)} coins)")
                    return
                    
            except Exception as e:
                self.logger.warning(f"Failed to load coins config from cache: {e}")
    
    def _save_to_cache(self) -> None:
        """Save coins config to local cache file."""
        if not self._coins_config:
            return
            
        cache_file = self.workspace_root / "tmp" / "coins_config_cache.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            cache_data = {
                'timestamp': self._last_fetch_time,
                'data': self._coins_config
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
                
            self.logger.debug(f"Saved coins config to cache")
            
        except Exception as e:
            self.logger.warning(f"Failed to save coins config to cache: {e}")
    
    def _fetch_coins_config(self) -> Dict[str, Any]:
        """Fetch the latest coins configuration from the remote repository."""
        try:
            self.logger.info(f"Fetching coins configuration from {COINS_CONFIG_URL}")
            with urllib.request.urlopen(COINS_CONFIG_URL, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            # Normalize the data structure
            normalized_data = {}
            if isinstance(data, list):
                for entry in data:
                    if isinstance(entry, dict):
                        ticker = (
                            entry.get("ticker") or 
                            entry.get("symbol") or 
                            entry.get("coin")
                        )
                        if ticker:
                            normalized_data[str(ticker).upper()] = entry
            elif isinstance(data, dict):
                normalized_data = data
            
            self.logger.info(f"Successfully fetched configuration for {len(normalized_data)} coins")
            return normalized_data
            
        except Exception as e:
            self.logger.error(f"Failed to fetch coins configuration: {e}")
            raise
    
    def get_coins_config(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get the coins configuration, fetching if needed.
        
        Args:
            force_refresh: If True, forces a fresh fetch from remote.
            
        Returns:
            Dictionary of coin configurations keyed by ticker.
        """
        # Check if we need to refresh
        current_time = time.time()
        needs_refresh = (
            force_refresh or 
            self._coins_config is None or 
            (current_time - self._last_fetch_time) > self._cache_duration
        )
        
        if needs_refresh:
            try:
                self._coins_config = self._fetch_coins_config()
                self._last_fetch_time = current_time
                self._save_to_cache()
            except Exception as e:
                # If fetch fails and we have cached data, use it
                if self._coins_config is not None:
                    self.logger.warning(f"Failed to refresh coins config, using cached data: {e}")
                else:
                    # If no cached data available, re-raise the exception
                    raise
        
        return self._coins_config or {}
    
    def get_coin_config(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific coin.
        
        Args:
            ticker: The coin ticker symbol.
            
        Returns:
            Coin configuration dictionary or None if not found.
        """
        coins_config = self.get_coins_config()
        ticker_upper = str(ticker).upper()
        
        # Direct lookup first
        if ticker_upper in coins_config:
            return coins_config[ticker_upper]
        
        # Search by various ticker fields
        for coin_ticker, config in coins_config.items():
            if isinstance(config, dict):
                coin_identifiers = [
                    config.get("ticker"),
                    config.get("symbol"), 
                    config.get("coin")
                ]
                
                if ticker_upper in [str(x).upper() for x in coin_identifiers if x]:
                    return config
        
        return None
    
    def get_protocol_info(self, ticker: str) -> CoinProtocolInfo:
        """Get protocol information for a coin.
        
        Args:
            ticker: The coin ticker symbol.
            
        Returns:
            CoinProtocolInfo object with protocol details.
        """
        config = self.get_coin_config(ticker)
        if not config:
            return CoinProtocolInfo(protocol_type="UNKNOWN")
        
        # Extract protocol information
        protocol = config.get("protocol", {})
        protocol_type = protocol.get("type", "").upper() if isinstance(protocol, dict) else ""
        
        # Detect protocol type if not explicitly set
        if not protocol_type:
            if config.get("rpc_urls"):
                protocol_type = "TENDERMINT"
            elif config.get("light_wallet_d_servers"):
                protocol_type = "ZHTLC"
            elif config.get("electrum"):
                protocol_type = "UTXO"
            elif config.get("nodes"):
                protocol_type = "ETH"
            else:
                protocol_type = "UNKNOWN"
        
        # Normalize protocol type
        if protocol_type in ['COSMOS']:
            protocol_type = 'TENDERMINT'
        elif protocol_type in ['QTUM', 'BCH']:
            protocol_type = 'UTXO'
        elif protocol_type in ['ZEC']:
            protocol_type = 'ZHTLC'
        elif protocol_type in ['ERC20', 'MATIC', 'BNB', 'AVAX', 'FTM', 'ONE']:
            protocol_type = 'ETH'
        
        # Extract protocol data
        protocol_data = protocol.get("protocol_data", {}) if isinstance(protocol, dict) else {}
        
        return CoinProtocolInfo(
            protocol_type=protocol_type,
            nodes=config.get("nodes") or protocol_data.get("nodes"),
            electrum=config.get("electrum") or protocol_data.get("electrum"),
            rpc_urls=config.get("rpc_urls") or protocol_data.get("rpc_urls"),
            swap_contract_address=(
                config.get("swap_contract_address") or 
                protocol_data.get("swap_contract_address")
            ),
            fallback_swap_contract=(
                config.get("fallback_swap_contract") or 
                protocol_data.get("fallback_swap_contract")
            ),
            chain_id=(
                config.get("chain_id") or 
                config.get("chainId") or 
                config.get("chain_registry_name") or
                protocol_data.get("chain_id")
            ),
            denom=config.get("denom") or protocol_data.get("denom"),
            contract_address=(
                config.get("contract_address") or
                config.get("token_contract_address") or
                protocol_data.get("contract_address")
            ),
            required_confirmations=config.get("required_confirmations")
        )
    
    def is_token(self, ticker: str) -> Tuple[bool, Optional[str]]:
        """Check if a ticker is a token and determine its parent coin.
        
        Args:
            ticker: The coin ticker symbol.
            
        Returns:
            Tuple of (is_token, parent_coin).
        """
        config = self.get_coin_config(ticker)
        if not config:
            return False, None
        
        protocol_info = self.get_protocol_info(ticker)
        
        # Check for various parent coin indicators
        parent_candidates = [
            config.get("platform"),
            config.get("parent_coin"),
            config.get("parent"),
            config.get("base"),
            config.get("platform_coin"),
        ]
        
        for candidate in parent_candidates:
            if isinstance(candidate, str) and candidate.strip():
                return True, str(candidate).upper()
        
        # Check if it has a contract address (token indicator)
        if protocol_info.contract_address:
            # Detect parent from ticker pattern
            ticker_upper = str(ticker).upper()
            if ticker_upper.endswith("-ERC20"):
                return True, "ETH"
            if "-IBC_" in ticker_upper:
                try:
                    parent = ticker_upper.split("-IBC_")[1].split("-")[0].upper()
                    return True, parent
                except Exception:
                    pass
        
        return False, None
    
    def get_all_coins(self) -> List[str]:
        """Get list of all available coin tickers.
        
        Returns:
            Sorted list of coin ticker symbols.
        """
        coins_config = self.get_coins_config()
        return sorted(coins_config.keys())
