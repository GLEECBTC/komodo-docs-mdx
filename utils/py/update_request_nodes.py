#!/usr/bin/env python3
"""
Script to update node values in request JSON files with latest data from coins_config.json

This script addresses GitHub issue #360 by keeping electrum/node server values updated
in documentation request examples by syncing them with the latest values from the
coins repository.

Usage:
    python update_request_nodes.py <input_file> [output_file]
    
If output_file is not provided, the input file will be updated in-place.
"""

import json
import sys
import argparse
import logging
import urllib.request
import random
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URL to fetch the latest coins configuration
COINS_CONFIG_URL = "https://raw.githubusercontent.com/KomodoPlatform/coins/master/utils/coins_config.json"

def fetch_coins_config() -> Dict[str, Any]:
    """Fetch the latest coins configuration from the coins repository"""
    try:
        logger.info(f"Fetching coins configuration from {COINS_CONFIG_URL}")
        with urllib.request.urlopen(COINS_CONFIG_URL) as response:
            data = json.loads(response.read().decode('utf-8'))
        logger.info(f"Successfully fetched configuration for {len(data)} coins")
        return data
    except Exception as e:
        logger.error(f"Failed to fetch coins configuration: {e}")
        raise

def extract_method_from_request(request_data: Dict[str, Any]) -> Optional[str]:
    """Extract the method name from a request object"""
    if isinstance(request_data, dict) and 'method' in request_data:
        return request_data['method']
    return None

def extract_ticker_from_request(request_data: Dict[str, Any]) -> Optional[str]:
    """Extract the ticker symbol from a request object"""
    # Look for ticker in params
    if 'params' in request_data:
        params = request_data['params']
        if isinstance(params, dict) and 'ticker' in params:
            return params['ticker']
    
    # Look for ticker in other common locations
    if 'ticker' in request_data:
        return request_data['ticker']
    
    return None

def select_preferred_servers(servers: List[Dict[str, Any]], max_count: int = 3) -> List[Dict[str, Any]]:
    """Select up to max_count servers, preferring cipig/komodo domains"""
    if len(servers) <= max_count:
        return servers
    
    # Separate servers into priority and non-priority
    priority_servers = []
    regular_servers = []
    
    for server in servers:
        url = server.get('url', '')
        if 'cipig' in url.lower() or 'komodo' in url.lower():
            priority_servers.append(server)
        else:
            regular_servers.append(server)
    
    selected_servers = []
    
    # First, add priority servers (up to max_count)
    if priority_servers:
        if len(priority_servers) <= max_count:
            selected_servers.extend(priority_servers)
        else:
            # Randomly select from priority servers
            selected_servers.extend(random.sample(priority_servers, max_count))
    
    # If we need more servers and have regular ones available
    remaining_slots = max_count - len(selected_servers)
    if remaining_slots > 0 and regular_servers:
        if len(regular_servers) <= remaining_slots:
            selected_servers.extend(regular_servers)
        else:
            # Randomly select from regular servers
            selected_servers.extend(random.sample(regular_servers, remaining_slots))
    
    logger.debug(f"Selected {len(selected_servers)} servers from {len(servers)} available ({len(priority_servers)} priority, {len(regular_servers)} regular)")
    return selected_servers

def select_preferred_urls(urls: List[str], max_count: int = 3) -> List[str]:
    """Select up to max_count URLs, preferring cipig/komodo domains"""
    if len(urls) <= max_count:
        return urls
    
    # Separate URLs into priority and non-priority
    priority_urls = []
    regular_urls = []
    
    for url in urls:
        if 'cipig' in url.lower() or 'komodo' in url.lower():
            priority_urls.append(url)
        else:
            regular_urls.append(url)
    
    selected_urls = []
    
    # First, add priority URLs (up to max_count)
    if priority_urls:
        if len(priority_urls) <= max_count:
            selected_urls.extend(priority_urls)
        else:
            # Randomly select from priority URLs
            selected_urls.extend(random.sample(priority_urls, max_count))
    
    # If we need more URLs and have regular ones available
    remaining_slots = max_count - len(selected_urls)
    if remaining_slots > 0 and regular_urls:
        if len(regular_urls) <= remaining_slots:
            selected_urls.extend(regular_urls)
        else:
            # Randomly select from regular URLs
            selected_urls.extend(random.sample(regular_urls, remaining_slots))
    
    logger.debug(f"Selected {len(selected_urls)} URLs from {len(urls)} available ({len(priority_urls)} priority, {len(regular_urls)} regular)")
    return selected_urls

def detect_coin_protocol(coin_config: Dict[str, Any]) -> str:
    """Detect the coin protocol type from the coin configuration"""
    if 'protocol' in coin_config:
        protocol_type = coin_config['protocol'].get('type', '').upper()
        if protocol_type in ['TENDERMINT', 'COSMOS']:
            return 'TENDERMINT'
        elif protocol_type in ['UTXO', 'QTUM', 'BCH']:
            return 'UTXO'
        elif protocol_type in ['ZHTLC', 'ZEC']:
            return 'ZHTLC'
        elif protocol_type in ['ETH', 'ERC20', 'MATIC', 'BNB', 'AVAX', 'FTM', 'ONE']:
            return 'ETH'
    
    # Fallback: detect by available server types
    if 'rpc_urls' in coin_config:
        return 'TENDERMINT'
    elif 'light_wallet_d_servers' in coin_config:
        return 'ZHTLC'
    elif 'electrum' in coin_config:
        return 'UTXO'
    elif 'nodes' in coin_config:
        return 'ETH'
    
    return 'UNKNOWN'

def update_tendermint_nodes(request_data: Dict[str, Any], coin_config: Dict[str, Any], ticker: str) -> bool:
    """Update Tendermint coin nodes (rpc_urls → nodes)"""
    if 'rpc_urls' not in coin_config:
        logger.warning(f"No rpc_urls found for Tendermint ticker '{ticker}' in coins configuration")
        return False
    
    # Select up to 3 preferred RPC URLs and convert to nodes format
    selected_rpc_urls = select_preferred_servers(coin_config['rpc_urls'], max_count=3)
    
    # Convert selected rpc_urls to nodes format (preserve all fields)
    new_nodes = []
    for rpc_url in selected_rpc_urls:
        node = {"url": rpc_url["url"]}
        # Preserve additional fields like api_url, grpc_url, ws_url, komodo_proxy
        for field in ['api_url', 'grpc_url', 'ws_url', 'komodo_proxy']:
            if field in rpc_url:
                node[field] = rpc_url[field]
        new_nodes.append(node)
    
    # Update nodes in params
    if 'params' in request_data and isinstance(request_data['params'], dict):
        params = request_data['params']
        if 'nodes' in params:
            old_nodes = params['nodes']
            params['nodes'] = new_nodes
            logger.info(f"Updated Tendermint nodes for ticker '{ticker}': {len(old_nodes)} -> {len(new_nodes)} nodes")
            return True
    
    # Check root level for nodes
    if 'nodes' in request_data:
        old_nodes = request_data['nodes']
        request_data['nodes'] = new_nodes
        logger.info(f"Updated Tendermint nodes for ticker '{ticker}': {len(old_nodes)} -> {len(new_nodes)} nodes")
        return True
    
    return False

def update_utxo_electrum_servers(request_data: Dict[str, Any], coin_config: Dict[str, Any], ticker: str) -> bool:
    """Update UTXO coin electrum servers (electrum → servers)"""
    if 'electrum' not in coin_config:
        logger.warning(f"No electrum servers found for UTXO ticker '{ticker}' in coins configuration")
        return False
    
    # Select up to 3 preferred electrum servers and convert to servers format
    selected_electrum = select_preferred_servers(coin_config['electrum'], max_count=3)
    
    # Convert selected electrum to servers format
    new_servers = []
    for electrum in selected_electrum:
        server = {"url": electrum["url"]}
        # Preserve protocol if specified
        if 'protocol' in electrum:
            server['protocol'] = electrum['protocol']
        # Add other optional fields
        for field in ['ws_url', 'disable_cert_verification']:
            if field in electrum:
                server[field] = electrum[field]
        new_servers.append(server)
    
    # Look for electrum servers nested in mode.rpc_data.servers (common pattern)
    if 'params' in request_data and isinstance(request_data['params'], dict):
        params = request_data['params']
        
        # Handle nested activation_params.mode.rpc_data.servers
        if 'activation_params' in params and 'mode' in params['activation_params']:
            mode = params['activation_params']['mode']
            if 'rpc_data' in mode and 'servers' in mode['rpc_data']:
                old_servers = mode['rpc_data']['servers']
                mode['rpc_data']['servers'] = new_servers
                logger.info(f"Updated UTXO electrum servers for ticker '{ticker}': {len(old_servers)} -> {len(new_servers)} servers")
                return True
        
        # Handle direct mode.rpc_data.servers
        if 'mode' in params and 'rpc_data' in params['mode']:
            rpc_data = params['mode']['rpc_data']
            if 'servers' in rpc_data:
                old_servers = rpc_data['servers']
                rpc_data['servers'] = new_servers
                logger.info(f"Updated UTXO electrum servers for ticker '{ticker}': {len(old_servers)} -> {len(new_servers)} servers")
                return True
    
    return False

def update_zhtlc_servers(request_data: Dict[str, Any], coin_config: Dict[str, Any], ticker: str) -> bool:
    """Update ZHTLC coin servers (light_wallet_d_servers and electrum)"""
    updated = False
    
    # Update light_wallet_d_servers (select up to 3)
    if 'light_wallet_d_servers' in coin_config:
        new_lwd_servers = select_preferred_urls(coin_config['light_wallet_d_servers'], max_count=3)
        
        # Look for light_wallet_d_servers in nested structure
        if 'params' in request_data and isinstance(request_data['params'], dict):
            params = request_data['params']
            
            # Handle nested activation_params.mode.rpc_data.light_wallet_d_servers
            if 'activation_params' in params and 'mode' in params['activation_params']:
                mode = params['activation_params']['mode']
                if 'rpc_data' in mode and 'light_wallet_d_servers' in mode['rpc_data']:
                    old_lwd = mode['rpc_data']['light_wallet_d_servers']
                    mode['rpc_data']['light_wallet_d_servers'] = new_lwd_servers
                    logger.info(f"Updated ZHTLC light_wallet_d_servers for ticker '{ticker}': {len(old_lwd)} -> {len(new_lwd_servers)} servers")
                    updated = True
            
            # Handle direct mode.rpc_data.light_wallet_d_servers
            elif 'mode' in params and 'rpc_data' in params['mode']:
                rpc_data = params['mode']['rpc_data']
                if 'light_wallet_d_servers' in rpc_data:
                    old_lwd = rpc_data['light_wallet_d_servers']
                    rpc_data['light_wallet_d_servers'] = new_lwd_servers
                    logger.info(f"Updated ZHTLC light_wallet_d_servers for ticker '{ticker}': {len(old_lwd)} -> {len(new_lwd_servers)} servers")
                    updated = True
    
    # Update electrum_servers (from electrum field in coins_config, select up to 3)
    if 'electrum' in coin_config:
        # Select up to 3 preferred electrum servers
        selected_electrum = select_preferred_servers(coin_config['electrum'], max_count=3)
        
        # Convert selected electrum to electrum_servers format (simpler than UTXO)
        new_electrum_servers = []
        for electrum in selected_electrum:
            server = {"url": electrum["url"]}
            if 'protocol' in electrum:
                server['protocol'] = electrum['protocol']
            if 'ws_url' in electrum:
                server['ws_url'] = electrum['ws_url']
            new_electrum_servers.append(server)
        
        # Look for electrum_servers in nested structure
        if 'params' in request_data and isinstance(request_data['params'], dict):
            params = request_data['params']
            
            # Handle nested activation_params.mode.rpc_data.electrum_servers
            if 'activation_params' in params and 'mode' in params['activation_params']:
                mode = params['activation_params']['mode']
                if 'rpc_data' in mode and 'electrum_servers' in mode['rpc_data']:
                    old_electrum = mode['rpc_data']['electrum_servers']
                    mode['rpc_data']['electrum_servers'] = new_electrum_servers
                    logger.info(f"Updated ZHTLC electrum_servers for ticker '{ticker}': {len(old_electrum)} -> {len(new_electrum_servers)} servers")
                    updated = True
            
            # Handle direct mode.rpc_data.electrum_servers
            elif 'mode' in params and 'rpc_data' in params['mode']:
                rpc_data = params['mode']['rpc_data']
                if 'electrum_servers' in rpc_data:
                    old_electrum = rpc_data['electrum_servers']
                    rpc_data['electrum_servers'] = new_electrum_servers
                    logger.info(f"Updated ZHTLC electrum_servers for ticker '{ticker}': {len(old_electrum)} -> {len(new_electrum_servers)} servers")
                    updated = True
    
    return updated

def update_eth_nodes(request_data: Dict[str, Any], coin_config: Dict[str, Any], ticker: str) -> bool:
    """Update ETH-like coin nodes (nodes → nodes) - original functionality"""
    if 'nodes' not in coin_config:
        logger.warning(f"No nodes found for ETH ticker '{ticker}' in coins configuration")
        return False
    
    # Select up to 3 preferred nodes and convert coins_config node format to request format
    selected_nodes = select_preferred_servers(coin_config['nodes'], max_count=3)
    
    new_nodes = []
    for node in selected_nodes:
        request_node = {"url": node["url"]}
        # Preserve other fields that might be present
        for field in ['ws_url', 'komodo_proxy']:
            if field in node:
                request_node[field] = node[field]
        new_nodes.append(request_node)
    
    # Look for nodes in params first, then in the root of the request
    if 'params' in request_data and isinstance(request_data['params'], dict):
        params = request_data['params']
        if 'nodes' in params:
            old_nodes = params['nodes']
            params['nodes'] = new_nodes
            logger.info(f"Updated ETH nodes for ticker '{ticker}': {len(old_nodes)} -> {len(new_nodes)} nodes")
            return True
    
    # Check root level for nodes
    if 'nodes' in request_data:
        old_nodes = request_data['nodes']
        request_data['nodes'] = new_nodes
        logger.info(f"Updated ETH nodes for ticker '{ticker}': {len(old_nodes)} -> {len(new_nodes)} nodes")
        return True
    
    return False

def update_nodes_in_request(request_data: Dict[str, Any], coins_config: Dict[str, Any], request_name: str = "Unknown") -> bool:
    """
    Update server/node arrays in a request object based on coin protocol type
    
    Args:
        request_data: The request object to update
        coins_config: The coins configuration data
        request_name: Name/identifier of the request for logging
    
    Returns:
        bool: True if any servers/nodes were updated, False otherwise
    """
    method = extract_method_from_request(request_data)
    ticker = extract_ticker_from_request(request_data)
    
    if method:
        logger.debug(f"Scanning method '{method}' in request '{request_name}'")
    else:
        logger.debug(f"Scanning request '{request_name}' (no method field)")
    
    if not ticker:
        logger.debug(f"No ticker found in request '{request_name}'")
        return False
    
    if ticker not in coins_config:
        logger.warning(f"Ticker '{ticker}' not found in coins configuration")
        return False
    
    coin_config = coins_config[ticker]
    protocol = detect_coin_protocol(coin_config)
    
    logger.debug(f"Detected protocol '{protocol}' for ticker '{ticker}'")
    
    # Route to appropriate update function based on protocol
    if protocol == 'TENDERMINT':
        return update_tendermint_nodes(request_data, coin_config, ticker)
    elif protocol == 'UTXO':
        return update_utxo_electrum_servers(request_data, coin_config, ticker)
    elif protocol == 'ZHTLC':
        return update_zhtlc_servers(request_data, coin_config, ticker)
    elif protocol == 'ETH':
        return update_eth_nodes(request_data, coin_config, ticker)
    else:
        logger.warning(f"Unknown or unsupported protocol '{protocol}' for ticker '{ticker}'")
        return False

def process_request_file(input_file: Path, output_file: Optional[Path] = None) -> None:
    """Process a request JSON file and update node values"""
    
    # Read the input file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            request_data = json.load(f)
        logger.info(f"Loaded request file: {input_file}")
    except Exception as e:
        logger.error(f"Failed to read input file {input_file}: {e}")
        raise
    
    # Fetch the latest coins configuration
    coins_config = fetch_coins_config()
    
    # Process the request data
    updates_made = 0
    
    # Handle the case where the file contains multiple request objects
    if isinstance(request_data, dict):
        for key, request_obj in request_data.items():
            if isinstance(request_obj, dict):
                if update_nodes_in_request(request_obj, coins_config, key):
                    updates_made += 1
                    method = extract_method_from_request(request_obj)
                    if method:
                        logger.info(f"Updated request object '{key}' (method: {method})")
                    else:
                        logger.info(f"Updated request object: {key}")
    elif isinstance(request_data, list):
        # Handle array of requests
        for i, request_obj in enumerate(request_data):
            if isinstance(request_obj, dict):
                request_name = f"index_{i}"
                if update_nodes_in_request(request_obj, coins_config, request_name):
                    updates_made += 1
                    method = extract_method_from_request(request_obj)
                    if method:
                        logger.info(f"Updated request object at index {i} (method: {method})")
                    else:
                        logger.info(f"Updated request object at index {i}")
    else:
        # Single request object
        if update_nodes_in_request(request_data, coins_config, "single_request"):
            updates_made += 1
            method = extract_method_from_request(request_data)
            if method:
                logger.info(f"Updated single request object (method: {method})")
            else:
                logger.info("Updated single request object")
    
    # Determine output file
    if output_file is None:
        output_file = input_file
    
    # Write the updated data
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(request_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved updated file: {output_file}")
    except Exception as e:
        logger.error(f"Failed to write output file {output_file}: {e}")
        raise
    
    if updates_made > 0:
        logger.info(f"✅ Successfully updated {updates_made} request(s) with latest server/node values")
    else:
        logger.info("ℹ️ No updates were needed - no matching tickers with compatible server configurations found")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Update node values in request JSON files with latest data from coins_config.json"
    )
    parser.add_argument("input_file", help="Path to the input request JSON file")
    parser.add_argument("output_file", nargs="?", help="Path to the output file (optional, defaults to input_file)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    input_file = Path(args.input_file)
    output_file = Path(args.output_file) if args.output_file else None
    
    if not input_file.exists():
        logger.error(f"Input file does not exist: {input_file}")
        sys.exit(1)
    
    try:
        process_request_file(input_file, output_file)
        logger.info("🎉 Update completed successfully!")
    except Exception as e:
        logger.error(f"❌ Update failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()