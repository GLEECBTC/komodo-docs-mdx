#!/usr/bin/env python3
"""
Clean Slate - Disable all enabled coins to start fresh

This script:
1. Gets all enabled coins using get_enabled_coins 
2. Disables each coin to ensure a clean slate for testing
"""

import json
import requests
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any

# Add lib path for utilities
sys.path.append(str(Path(__file__).parent / "lib"))
from utils.json_utils import dump_sorted_json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# KDF instances
KDF_INSTANCES = [
    {"name": "native-hd", "url": "http://localhost:7783", "userpass": "RPC_UserP@SSW0RD"},
    {"name": "native-nonhd", "url": "http://localhost:7784", "userpass": "RPC_UserP@SSW0RD"},
]


def send_request(instance: Dict[str, str], request_data: Dict[str, Any]) -> tuple[bool, Any]:
    """Send a request to KDF instance."""
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            instance["url"],
            json=request_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                if "error" in response_data:
                    return False, response_data
                return True, response_data
            except json.JSONDecodeError:
                return False, {"error": "Invalid JSON response", "raw_response": response.text}
        else:
            return False, {"error": f"HTTP {response.status_code}", "raw_response": response.text}
            
    except Exception as e:
        return False, {"error": f"Request failed: {str(e)}"}


def get_enabled_coins(instance: Dict[str, str]) -> List[str]:
    """Get list of enabled coins."""
    request = {
        "userpass": instance["userpass"],
        "method": "get_enabled_coins"
    }
    
    success, response = send_request(instance, request)
    
    if success and "result" in response:
        tickers = []
        result = response["result"]
        
        # Handle different response formats
        if isinstance(result, list):
            # List of coin objects like [{"ticker": "ETH", "address": "..."}, ...]
            for coin in result:
                if isinstance(coin, dict) and "ticker" in coin:
                    tickers.append(coin["ticker"])
                elif isinstance(coin, str):
                    tickers.append(coin)
        elif isinstance(result, dict):
            # Sometimes result is {"enabled_coins": [...]}
            if "enabled_coins" in result:
                for coin in result["enabled_coins"]:
                    if isinstance(coin, dict) and "ticker" in coin:
                        tickers.append(coin["ticker"])
                    elif isinstance(coin, str):
                        tickers.append(coin)
            # Or result contains coin objects directly
            else:
                tickers = list(result.keys())
        
        logger.info(f"{instance['name']}: Found {len(tickers)} enabled coins: {tickers}")
        return tickers
    else:
        error_msg = response.get("error", "Unknown error") if isinstance(response, dict) else str(response)
        logger.warning(f"{instance['name']}: Failed to get enabled coins: {error_msg}")
        return []


def disable_coin(instance: Dict[str, str], ticker: str) -> bool:
    """Disable a specific coin."""
    request = {
        "userpass": instance["userpass"],
        "method": "disable_coin",
        "coin": ticker
    }
    
    success, response = send_request(instance, request)
    
    if success:
        logger.info(f"{instance['name']}: Successfully disabled {ticker}")
        return True
    else:
        error_msg = response.get("error", "Unknown error") if isinstance(response, dict) else str(response)
        logger.warning(f"{instance['name']}: Failed to disable {ticker}: {error_msg}")
        return False


def clean_slate():
    """Clean slate - disable all enabled coins on all instances."""
    logger.info("🧹 Starting clean slate process...")
    
    total_disabled = 0
    
    for instance in KDF_INSTANCES:
        logger.info(f"\n📋 Processing instance: {instance['name']}")
        
        # Get enabled coins
        enabled_coins = get_enabled_coins(instance)
        
        if not enabled_coins:
            logger.info(f"{instance['name']}: No coins to disable")
            continue
        
        # Disable each coin
        instance_disabled = 0
        for ticker in enabled_coins:
            if disable_coin(instance, ticker):
                instance_disabled += 1
        
        logger.info(f"{instance['name']}: Disabled {instance_disabled}/{len(enabled_coins)} coins")
        total_disabled += instance_disabled
    
    logger.info(f"\n🎉 Clean slate complete! Disabled {total_disabled} coins total")
    
    # Verify clean state
    logger.info("\n🔍 Verifying clean state...")
    for instance in KDF_INSTANCES:
        enabled_coins = get_enabled_coins(instance)
        if enabled_coins:
            logger.warning(f"{instance['name']}: Still has {len(enabled_coins)} coins enabled: {enabled_coins}")
        else:
            logger.info(f"{instance['name']}: ✅ Clean slate confirmed")


if __name__ == "__main__":
    clean_slate()
