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
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add lib path for utilities
sys.path.append(str(Path(__file__).parent / "lib"))
from utils.json_utils import dump_sorted_json
sys.path.append(str(Path(__file__).parent / "lib" / "managers"))
from coins_config_manager import CoinsConfigManager, CoinProtocolInfo
from activation_manager import ActivationRequestBuilder
sys.path.append(str(Path(__file__).parent / "lib" / "models"))
from kdf_method import extract_method_from_request, extract_ticker_from_request

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_coins_config() -> Dict[str, Any]:
    """Fetch coins configuration via CoinsConfigManager (with caching and normalization)."""
    try:
        workspace_root = Path(__file__).parent.parent.parent
        manager = CoinsConfigManager(workspace_root)
        data = manager.get_coins_config()
        logger.info(f"Successfully loaded configuration for {len(data)} coins (via CoinsConfigManager)")
        return data
    except Exception as e:
        logger.error(f"Failed to load coins configuration via CoinsConfigManager: {e}")
        raise



def detect_coin_protocol_info(manager: CoinsConfigManager, ticker: str) -> CoinProtocolInfo:
    """Use CoinsConfigManager to determine protocol info for a ticker."""
    return manager.get_protocol_info(ticker)

def update_tendermint_nodes(request_data: Dict[str, Any], arb: ActivationRequestBuilder, ticker: str) -> bool:
    protocol_info = arb.coins_config.get_protocol_info(ticker)
    return arb.update_tendermint_nodes_in_request(request_data, protocol_info, ticker)

def update_utxo_electrum_servers(request_data: Dict[str, Any], arb: ActivationRequestBuilder, ticker: str) -> bool:
    protocol_info = arb.coins_config.get_protocol_info(ticker)
    return arb.update_utxo_electrum_in_request(request_data, protocol_info, ticker)

def update_zhtlc_servers(request_data: Dict[str, Any], arb: ActivationRequestBuilder, ticker: str) -> bool:
    protocol_info = arb.coins_config.get_protocol_info(ticker)
    return arb.update_zhtlc_in_request(request_data, protocol_info, ticker)

def update_eth_nodes(request_data: Dict[str, Any], arb: ActivationRequestBuilder, ticker: str) -> bool:
    protocol_info = arb.coins_config.get_protocol_info(ticker)
    return arb.update_eth_nodes_in_request(request_data, protocol_info, ticker)

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
        logger.info(f"Scanning method '{method}' in request '{request_name}'")
    else:
        logger.info(f"Scanning request '{request_name}' (no method field)")
    
    if not ticker:
        logger.info(f"No ticker found in request '{request_name}'")
        return False
    
    if ticker not in coins_config:
        logger.warning(f"Ticker '{ticker}' not found in coins configuration")
        return False
    
    # Use ActivationRequestBuilder to detect and update
    workspace_root = Path(__file__).parent.parent.parent
    arb = ActivationRequestBuilder(CoinsConfigManager(workspace_root), "")
    protocol_info = arb.coins_config.get_protocol_info(ticker)
    protocol = protocol_info.protocol_type or 'UNKNOWN'
    logger.info(f"Detected protocol '{protocol}' for ticker '{ticker}' via CoinsConfigManager")
    if protocol == 'TENDERMINT':
        return update_tendermint_nodes(request_data, arb, ticker)
    elif protocol == 'UTXO':
        return update_utxo_electrum_servers(request_data, arb, ticker)
    elif protocol == 'ZHTLC':
        return update_zhtlc_servers(request_data, arb, ticker)
    elif protocol == 'ETH':
        return update_eth_nodes(request_data, arb, ticker)
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
                # Set transient __wasm flag based on request key naming
                if isinstance(key, str) and "wasm" in key.lower():
                    request_obj["__wasm"] = True
                    if isinstance(request_obj.get("params"), dict):
                        request_obj["params"]["__wasm"] = True
                if update_nodes_in_request(request_obj, coins_config, key):
                    updates_made += 1
                    method = extract_method_from_request(request_obj)
                    if method:
                        logger.info(f"Updated request object '{key}' (method: {method})")
                    else:
                        logger.info(f"Updated request object: {key}")
                # Remove transient __wasm flags before saving
                request_obj.pop("__wasm", None)
                if isinstance(request_obj.get("params"), dict):
                    request_obj["params"].pop("__wasm", None)
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
        dump_sorted_json(request_data, output_file, ensure_ascii=False)
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
        logging.getLogger().setLevel(logging.INFO)
    
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