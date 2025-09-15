#!/usr/bin/env python3
"""
Clean Slate - Disable all enabled coins to start fresh

This script:
1. Gets all enabled coins using get_enabled_coins 
2. Disables each coin to ensure a clean slate for testing
"""

import sys
import logging
from pathlib import Path
from typing import List

# Import from kdf_responses_manager to reuse existing functionality
sys.path.append(str(Path(__file__).parent))
from kdf_responses_manager import UnifiedResponseManager, KDFInstance, KDF_INSTANCES

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_enabled_coins_from_instance(manager: UnifiedResponseManager, instance: KDFInstance) -> List[str]:
    """Get list of enabled coins from a KDF instance."""
    request = {
        "userpass": instance.userpass,
        "method": "get_enabled_coins"
    }
    
    success, response = manager.send_request(instance, request)
    
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
        
        logger.info(f"{instance.name}: Found {len(tickers)} enabled coins: {tickers}")
        return tickers
    else:
        error_msg = response.get("error", "Unknown error") if isinstance(response, dict) else str(response)
        logger.warning(f"{instance.name}: Failed to get enabled coins: {error_msg}")
        return []


def clean_slate():
    """Clean slate - disable all enabled coins on all instances."""
    logger.info("🧹 Starting clean slate process...")
    
    # Create a manager instance to reuse existing functionality
    manager = UnifiedResponseManager()
    total_disabled = 0
    
    for instance in KDF_INSTANCES:
        logger.info(f"\n📋 Processing instance: {instance.name}")
        
        # Get enabled coins using the manager
        enabled_coins = get_enabled_coins_from_instance(manager, instance)
        
        if not enabled_coins:
            logger.info(f"{instance.name}: No coins to disable")
            continue
        
        # Disable each coin using the manager's disable_coin method
        instance_disabled = 0
        for ticker in enabled_coins:
            if manager.disable_coin(instance, ticker):
                instance_disabled += 1
        
        logger.info(f"{instance.name}: Disabled {instance_disabled}/{len(enabled_coins)} coins")
        total_disabled += instance_disabled
    
    logger.info(f"\n🎉 Clean slate complete! Disabled {total_disabled} coins total")
    
    # Verify clean state
    logger.info("\n🔍 Verifying clean state...")
    for instance in KDF_INSTANCES:
        enabled_coins = get_enabled_coins_from_instance(manager, instance)
        if enabled_coins:
            logger.warning(f"{instance.name}: Still has {len(enabled_coins)} coins enabled: {enabled_coins}")
        else:
            logger.info(f"{instance.name}: ✅ Clean slate confirmed")


if __name__ == "__main__":
    clean_slate()
