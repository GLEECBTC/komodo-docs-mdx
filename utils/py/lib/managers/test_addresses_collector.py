"""
Test Addresses Collector
Collects addresses and balances from all KDF instances for testing purposes.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import logging

# Lazy import to avoid circular dependency issues
def _get_kdf_classes():
    """Lazy import of KDF classes to avoid circular imports."""
    try:
        from .responses_manager import KDFInstance, UnifiedResponseManager
        return KDFInstance, UnifiedResponseManager
    except ImportError:
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent))
        from responses_manager import KDFInstance, UnifiedResponseManager
        return KDFInstance, UnifiedResponseManager

# Import utilities
try:
    from ..utils.json_utils import dump_sorted_json
except ImportError:
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from utils.json_utils import dump_sorted_json


@dataclass
class AddressBalance:
    """Container for address and balance information."""
    address: str
    balance: str
    unspendable_balance: Optional[str] = None
    derivation_path: Optional[str] = None
    chain: Optional[str] = None


class TestAddressesCollector:
    """Collects addresses and balances from KDF instances for testing purposes."""
    
    def __init__(self, workspace_root: Optional[Path] = None):
        """Initialize the collector."""
        self.workspace_root = workspace_root or Path.cwd()
        self.logger = logging.getLogger(__name__)
        
        # Initialize response manager to get send_request capability (lazy import)
        KDFInstance, UnifiedResponseManager = _get_kdf_classes()
        self.response_manager = UnifiedResponseManager()
        self.KDFInstance = KDFInstance
        
    def send_request(self, instance, request_data: Dict[str, Any], timeout: int = 30) -> Tuple[bool, Dict[str, Any]]:
        """Send request using the response manager."""
        return self.response_manager.send_request(instance, request_data, timeout)
    
    def get_enabled_coins(self, instance) -> List[str]:
        """Get list of enabled coins for an instance."""
        try:
            # For HD wallets, use v2 API; for non-HD wallets, use v1 API
            if "hd" in instance.name.lower():
                # HD wallet - use v2 API
                request = {
                    "userpass": instance.userpass,
                    "mmrpc": "2.0",
                    "method": "get_enabled_coins"
                }
            else:
                # Non-HD wallet - use v1 API  
                request = {
                    "userpass": instance.userpass,
                    "method": "get_enabled_coins"
                }
            
            success, response = self.send_request(instance, request)
            
            if success and "result" in response:
                enabled_coins = []
                result = response["result"]
                
                # Handle v2 response format (HD wallets)
                if isinstance(result, dict) and "coins" in result:
                    for coin in result["coins"]:
                        if isinstance(coin, dict) and "ticker" in coin:
                            enabled_coins.append(coin["ticker"])
                        elif isinstance(coin, str):
                            enabled_coins.append(coin)
                # Handle v1 response format (non-HD wallets)  
                elif isinstance(result, list):
                    for coin in result:
                        if isinstance(coin, dict) and "ticker" in coin:
                            enabled_coins.append(coin["ticker"])
                        elif isinstance(coin, str):
                            enabled_coins.append(coin)
                
                self.logger.info(f"{instance.name}: Found {len(enabled_coins)} enabled coins: {enabled_coins}")
                return enabled_coins
            else:
                self.logger.warning(f"{instance.name}: Failed to get enabled coins: {response}")
                return []
                
        except Exception as e:
            self.logger.error(f"{instance.name}: Error getting enabled coins: {e}")
            return []
    
    def get_balance_legacy(self, instance, coin: str) -> Optional[AddressBalance]:
        """Get balance using legacy my_balance method."""
        try:
            request = {
                "userpass": instance.userpass,
                "method": "my_balance",
                "coin": coin
            }
            
            success, response = self.send_request(instance, request)
            
            if success and "address" in response:
                return AddressBalance(
                    address=response["address"],
                    balance=response.get("balance", "0"),
                    unspendable_balance=response.get("unspendable_balance", "0")
                )
            else:
                self.logger.debug(f"{instance.name}: my_balance failed for {coin}: {response}")
                return None
                
        except Exception as e:
            self.logger.debug(f"{instance.name}: Error getting legacy balance for {coin}: {e}")
            return None
    
    def get_balance_hd(self, instance, coin: str) -> List[AddressBalance]:
        """Get balance using HD task::account_balance methods."""
        try:
            # Initialize account balance task
            init_request = {
                "userpass": instance.userpass,
                "mmrpc": "2.0",
                "method": "task::account_balance::init",
                "params": {
                    "coin": coin,
                    "account_index": 0
                }
            }
            
            success, response = self.send_request(instance, init_request)
            
            if not success or "result" not in response:
                self.logger.debug(f"{instance.name}: account_balance init failed for {coin}: {response}")
                return []
            
            task_id = response["result"].get("task_id")
            if task_id is None:
                self.logger.debug(f"{instance.name}: No task_id returned for {coin} account balance")
                return []
            
            # Poll for status
            addresses = []
            max_attempts = 10
            for attempt in range(max_attempts):
                status_request = {
                    "userpass": instance.userpass,
                    "mmrpc": "2.0",
                    "method": "task::account_balance::status",
                    "params": {
                        "task_id": task_id,
                        "forget_if_finished": False
                    }
                }
                
                success, response = self.send_request(instance, status_request)
                
                if success and "result" in response:
                    result = response["result"]
                    status = result.get("status")
                    
                    if status == "Ok" and "details" in result:
                        details = result["details"]
                        if "addresses" in details:
                            for addr_info in details["addresses"]:
                                address = addr_info.get("address")
                                balance_info = addr_info.get("balance", {})
                                coin_balance = balance_info.get(coin, {})
                                
                                if address and coin_balance:
                                    addresses.append(AddressBalance(
                                        address=address,
                                        balance=coin_balance.get("spendable", "0"),
                                        unspendable_balance=coin_balance.get("unspendable", "0"),
                                        derivation_path=addr_info.get("derivation_path"),
                                        chain=addr_info.get("chain")
                                    ))
                        return addresses
                    elif status in ["InProgress", "UserActionRequired"]:
                        # Still processing, wait and retry
                        time.sleep(2)
                        continue
                    else:
                        # Failed or other status
                        self.logger.debug(f"{instance.name}: account_balance failed for {coin} with status: {status}")
                        return []
                else:
                    self.logger.debug(f"{instance.name}: account_balance status check failed for {coin}: {response}")
                    return []
            
            self.logger.debug(f"{instance.name}: account_balance timed out for {coin}")
            return []
            
        except Exception as e:
            self.logger.debug(f"{instance.name}: Error getting HD balance for {coin}: {e}")
            return []
    
    def get_coin_addresses_and_balances(self, instance, coin: str) -> List[AddressBalance]:
        """Get addresses and balances for a coin, trying both HD and legacy methods."""
        addresses = []
        
        # Choose method based on instance type
        if "hd" in instance.name.lower():
            # HD wallet - use HD method
            hd_addresses = self.get_balance_hd(instance, coin)
            if hd_addresses:
                addresses.extend(hd_addresses)
                self.logger.debug(f"{instance.name}: Got {len(hd_addresses)} HD addresses for {coin}")
            else:
                self.logger.debug(f"{instance.name}: No HD addresses found for {coin}")
        else:
            # Non-HD wallet - use legacy method
            legacy_balance = self.get_balance_legacy(instance, coin)
            if legacy_balance:
                addresses.append(legacy_balance)
                self.logger.debug(f"{instance.name}: Got legacy balance for {coin}")
            else:
                self.logger.debug(f"{instance.name}: No legacy balance found for {coin}")
        
        return addresses
    
    def collect_all_addresses(self, instances: List) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Collect addresses and balances from all instances.
        
        Returns:
            Dict in format: {
                "instance_name": {
                    "COIN_TICKER": {
                        "address_string": "balance_value",
                        ...
                    },
                    ...
                },
                ...
            }
        """
        self.logger.info("🏦 Starting test addresses collection...")
        
        all_addresses = {}
        
        for instance in instances:
            self.logger.info(f"📋 Processing instance: {instance.name}")
            instance_addresses = {}
            
            # Get enabled coins for this instance
            enabled_coins = self.get_enabled_coins(instance)
            
            if not enabled_coins:
                self.logger.info(f"{instance.name}: No enabled coins found")
                all_addresses[instance.name] = {}
                continue
            
            # Get addresses and balances for each coin
            for coin in enabled_coins:
                self.logger.debug(f"{instance.name}: Getting addresses for {coin}")
                addresses = self.get_coin_addresses_and_balances(instance, coin)
                
                if addresses:
                    coin_addresses = {}
                    for addr in addresses:
                        # Format balance (prefer spendable balance)
                        balance_str = addr.balance
                        if addr.unspendable_balance and addr.unspendable_balance != "0":
                            balance_str += f" (unspendable: {addr.unspendable_balance})"
                        
                        coin_addresses[addr.address] = balance_str
                    
                    if coin_addresses:
                        instance_addresses[coin] = coin_addresses
                        self.logger.info(f"{instance.name}: {coin} - {len(coin_addresses)} addresses")
                else:
                    self.logger.debug(f"{instance.name}: No addresses found for {coin}")
            
            all_addresses[instance.name] = instance_addresses
            self.logger.info(f"{instance.name}: Found addresses for {len(instance_addresses)} coins")
        
        return all_addresses
    
    def save_test_addresses_report(self, addresses_data: Dict[str, Any], output_file: Optional[Path] = None) -> Path:
        """Save the test addresses report to file."""
        if output_file is None:
            output_file = self.workspace_root / "postman/generated/reports/test_addresses.json"
        
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the report
        dump_sorted_json(addresses_data, output_file)
        
        self.logger.info(f"💾 Test addresses report saved to: {output_file}")
        return output_file


def main():
    """Main function for standalone execution."""
    import sys
    from pathlib import Path
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Get workspace root
    if len(sys.argv) > 1:
        workspace_root = Path(sys.argv[1])
    else:
        workspace_root = Path.cwd()
        while not (workspace_root / "docker-compose.yml").exists() and workspace_root != workspace_root.parent:
            workspace_root = workspace_root.parent
    
    logger = logging.getLogger(__name__)
    logger.info(f"🏦 Test Addresses Collector - Workspace: {workspace_root}")
    
    # Import KDF instances  
    sys.path.append(str(workspace_root / "utils/py/lib/managers"))
    KDFInstance, UnifiedResponseManager = _get_kdf_classes()
    from responses_manager import KDF_INSTANCES
    
    # Create collector and collect addresses
    collector = TestAddressesCollector(workspace_root)
    addresses = collector.collect_all_addresses(KDF_INSTANCES)
    
    # Save report
    output_file = collector.save_test_addresses_report(addresses)
    
    # Print summary
    total_instances = len(addresses)
    total_coins = sum(len(instance_data) for instance_data in addresses.values())
    total_addresses = sum(
        len(coin_data) for instance_data in addresses.values() 
        for coin_data in instance_data.values()
    )
    
    logger.info(f"📊 Collection Summary:")
    logger.info(f"   Instances: {total_instances}")
    logger.info(f"   Coins: {total_coins}")
    logger.info(f"   Addresses: {total_addresses}")
    logger.info(f"📁 Report: {output_file.relative_to(workspace_root)}")


if __name__ == "__main__":
    main()
