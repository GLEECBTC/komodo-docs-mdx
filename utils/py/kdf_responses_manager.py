#!/usr/bin/env python3
"""
Unified Response Manager - A comprehensive tool to collect and validate KDF responses.

This script combines the functionality of:
- collect_missing_responses.py 
- collect_missing_responses_enhanced.py (platform dependencies)
- collect_task_lifecycle_responses.py (task lifecycle management)
- add_successful_responses.py (automated response file updates)
- validate_kdf_responses.py (response validation)

Features:
- Platform coin dependency management
- Task lifecycle handling (init -> status -> cancel)
- Automatic response file updates
- Response structure validation
- Comprehensive error reporting
- Single unified output file
"""

import json
import requests
import time
import sys
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

# Add lib path for utilities
sys.path.append(str(Path(__file__).parent / "lib"))
from utils.json_utils import dump_sorted_json


# Configuration Classes
@dataclass
class KDFInstance:
    name: str
    url: str
    userpass: str


@dataclass
class CollectionResult:
    response_name: str
    instance_responses: Dict[str, Any]
    all_successful: bool
    consistent_structure: bool
    auto_updatable: bool
    collection_method: str
    notes: str = ""


# CollectionMode enum removed - all functionality is always enabled


class ValidationError:
    """Represents a validation error or warning."""
    
    def __init__(self, file_path: str, error_type: str, message: str, location: str = ""):
        self.file_path = file_path
        self.error_type = error_type  
        self.message = message
        self.location = location

    def __str__(self):
        location_str = f" [{self.location}]" if self.location else ""
        return f"[{self.error_type}] {self.file_path}{location_str}: {self.message}"


# Configuration
KDF_INSTANCES = [
    KDFInstance("native-hd", "http://localhost:7783", "RPC_UserP@SSW0RD"),
    KDFInstance("native-nonhd", "http://localhost:7784", "RPC_UserP@SSW0RD"),
]

# Methods to skip (manual methods that require hardware wallets or external services)
SKIP_METHODS = {
    "TaskEnableEthInitTrezor",  # Trezor hardware wallet
    "TaskEnableEthUserActionPin",  # Trezor PIN entry
    "TaskEnableQtumUserActionPin",  # Trezor PIN entry  
    "TaskEnableUtxoUserActionPin",  # Trezor PIN entry
    "TaskEnableBchUserActionPin",  # Trezor PIN entry
    "TaskEnableTendermintUserActionPin",  # Trezor PIN entry
    "TaskEnableZCoinUserActionPin",  # Trezor PIN entry
    "EnableEthWithTokensWalletConnect",  # WalletConnect
    "EnableTendermintWithAssetsWalletConnect",  # WalletConnect
}

# Platform coin dependencies
PLATFORM_DEPENDENCIES = {
    "enable_erc20": "ETH",
    "enable_tendermint_token": "IRIS",
}

# Status values that indicate a task is still in progress
IN_PROGRESS_STATUSES = {
    "InProgress",
    "ActivatingCoin", 
    "RequestingWalletBalance",
    "Finishing",
    "WaitingForTrezorToConnect",
    "FollowHwDeviceInstructions"
}


class UnifiedResponseManager:
    """Unified manager for collecting KDF API responses."""
    
    def __init__(self):
        """Initialize the response manager."""
        self.setup_logging("DEBUG")
        self.results: List[CollectionResult] = []
        self.platform_enabled: Dict[str, bool] = {}
        self.validator = KdfResponseValidator(self.logger)
        self.response_delays: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}
        self.inconsistent_responses: Dict[str, Dict[str, Any]] = {}
        
    def setup_logging(self, log_level: str):
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON file and return parsed content."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"File not found: {file_path}")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON file {file_path}: {e}")
            return {}
    
    def _filter_request_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out metadata fields from request data before sending to API."""
        # Remove documentation metadata fields that should not be sent to API
        metadata_fields = {'tags', 'prerequisites'}
        filtered_data = {k: v for k, v in request_data.items() if k not in metadata_fields}
        return filtered_data
    
    def send_request(self, instance: KDFInstance, request_data: Dict[str, Any], 
                    timeout: int = 30) -> Tuple[bool, Dict[str, Any]]:
        """Send a request to a KDF instance and track timing."""
        import time
        
        start_time = time.time()
        status_code = None
        
        try:
            headers = {"Content-Type": "application/json"}
            
            # Filter out metadata fields before sending to API
            filtered_request_data = self._filter_request_data(request_data)
            
            response = requests.post(
                instance.url,
                json=filtered_request_data,
                headers=headers,
                timeout=timeout
            )
            
            status_code = response.status_code
            
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
                
        except requests.exceptions.Timeout:
            status_code = 408  # Request Timeout
            return False, {"error": "Request timeout"}
        except requests.exceptions.ConnectionError:
            status_code = 503  # Service Unavailable
            return False, {"error": "Connection failed"}
        except Exception as e:
            status_code = 500  # Internal Server Error
            return False, {"error": f"Unexpected error: {str(e)}"}
        finally:
            # Calculate delay regardless of success/failure
            end_time = time.time()
            delay = round(end_time - start_time, 3)
            
            # Store timing information (will be used by calling methods)
            if hasattr(self, '_current_timing_context'):
                self._current_timing_context['delay'] = delay
                self._current_timing_context['status_code'] = status_code or 500
    
    def disable_coin(self, instance: KDFInstance, ticker: str) -> bool:
        """Disable a coin if it's already enabled."""
        disable_request = {
            "userpass": instance.userpass,
            "method": "disable_coin",
            "coin": ticker
        }
        
        success, response = self.send_request(instance, disable_request)
        
        if success:
            self.logger.info(f"Successfully disabled {ticker} on {instance.name}")
            return True
        else:
            # Safely handle response - ensure it's a dict before calling .get()
            if isinstance(response, dict):
                error_msg = str(response.get("error", "")).lower()
                error_display = response.get('error', 'Unknown error')
            else:
                # If response is not a dict, treat it as the error message
                error_msg = str(response).lower()
                error_display = str(response)
            
            if "not found" in error_msg or "not enabled" in error_msg:
                self.logger.debug(f"{ticker} was not enabled on {instance.name}")
                return True
            else:
                self.logger.warning(f"Failed to disable {ticker} on {instance.name}: {error_display}")
                return False
    
    def enable_platform_coin(self, instance: KDFInstance, ticker: str) -> bool:
        """Try to enable a platform coin using basic enable method."""
        # First disable if already enabled
        self.disable_coin(instance, ticker)
        
        # Platform coin enable requests
        enable_requests = {
            "ETH": {
                "userpass": instance.userpass,
                "method": "enable",
                "coin": "ETH",
                "urls": [
                    "https://eth3.cipig.net:18555",
                    "https://mainnet.gateway.tenderly.co",
                    "https://ethereum-rpc.publicnode.com"
                ],
                "swap_contract_address": "0x24ABE4c71FC658C91313b6552cd40cD808b3Ea80",
                "fallback_swap_contract": "0x8500AFc0bc5214728082163326C2FF0C73f4a871"
            },
            "IRIS": {
                "userpass": instance.userpass,
                "method": "enable_tendermint_with_assets", 
                "mmrpc": "2.0",
                "params": {
                    "ticker": "IRIS",
                    "tokens_params": [],
                    "nodes": [
                        {
                            "url": "https://iris-rpc.alpha.komodo.earth/",
                            "api_url": "https://iris-api.alpha.komodo.earth/",
                            "grpc_url": "https://iris-grpc.alpha.komodo.earth/",
                            "ws_url": "wss://iris-rpc.alpha.komodo.earth/websocket"
                        }
                    ],
                    "get_balances": False
                }
            }
        }
        
        if ticker not in enable_requests:
            return False
            
        request_data = enable_requests[ticker]
        success, response = self.send_request(instance, request_data, timeout=60)
        
        if success:
            self.logger.info(f"Successfully enabled platform coin {ticker} on {instance.name}")
            self.logger.debug(f"Platform coin {ticker} enable response: {json.dumps(response, indent=2)}")
            return True
        else:
            # Safely handle response - ensure it's a dict before calling .get()
            if isinstance(response, dict):
                error_msg = str(response.get("error", "")).lower()
                error_display = response.get('error', 'Unknown error')
            else:
                # If response is not a dict, treat it as the error message
                error_msg = str(response).lower()
                error_display = str(response)
            
            if "already activated" in error_msg or "already enabled" in error_msg:
                self.logger.info(f"Platform coin {ticker} already enabled on {instance.name}")
                return True
            else:
                self.logger.warning(f"Failed to enable platform coin {ticker} on {instance.name}: {error_display}")
                if isinstance(response, dict):
                    self.logger.debug(f"Platform coin {ticker} enable error: {json.dumps(response, indent=2)}")
                else:
                    self.logger.debug(f"Platform coin {ticker} enable error: {response}")
                return False
    
    def normalize_request_for_non_hd(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Modify request to work with non-HD wallets by removing HD-specific parameters."""
        request_copy = request_data.copy()
        
        # Remove HD-specific parameters from activation_params
        if "params" in request_copy and "activation_params" in request_copy["params"]:
            activation_params = request_copy["params"]["activation_params"]
            
            # Remove HD wallet specific fields
            hd_fields = ["path_to_address", "gap_limit", "scan_policy", "min_addresses_number"]
            for field in hd_fields:
                activation_params.pop(field, None)
                
            # Change priv_key_policy from Trezor to ContextPrivKey for non-hardware methods
            if "priv_key_policy" in activation_params:
                if activation_params["priv_key_policy"].get("type") == "Trezor":
                    activation_params["priv_key_policy"] = {"type": "ContextPrivKey"}
        
        return request_copy
    
    def _is_address_key(self, key: str) -> bool:
        """Check if a key looks like a cryptocurrency address."""
        if not isinstance(key, str):
            return False
        
        # Common address patterns
        address_patterns = [
            # Cosmos-based addresses (IRIS, ATOM, etc.)
            key.startswith(("iaa", "cosmos", "terra", "osmo", "juno")),
            # Ethereum addresses  
            key.startswith("0x") and len(key) == 42,
            # Bitcoin addresses
            key.startswith(("1", "3", "bc1")),
            # Other patterns
            len(key) > 25 and key.isalnum()  # Generic long alphanumeric strings
        ]
        
        return any(address_patterns)
    
    def _get_method_timeout(self, method_name: str) -> int:
        """Get appropriate timeout for a method based on its configuration in kdf_methods.json."""
        # Check if method has specific timeout configured
        workspace_root = Path(__file__).parent.parent.parent
        kdf_methods = self.load_json_file(workspace_root / "src/data/kdf_methods.json")
        
        if method_name in kdf_methods:
            method_config = kdf_methods[method_name]
            if isinstance(method_config, dict) and "timeout" in method_config:
                return method_config["timeout"]
        
        # Default timeout
        return 30
    
    def _record_response_delay(self, method_name: str, request_key: str, instance_name: str, 
                              status_code: int, delay: float) -> None:
        """Record response delay information for performance tracking."""
        if method_name not in self.response_delays:
            self.response_delays[method_name] = {}
        
        if request_key not in self.response_delays[method_name]:
            self.response_delays[method_name][request_key] = {}
        
        self.response_delays[method_name][request_key][instance_name] = {
            "status_code": status_code,
            "delay": delay
        }
    
    def _record_inconsistent_response(self, method_name: str, request_key: str, 
                                     instance_responses: Dict[str, Any]) -> None:
        """Record inconsistent response for analysis report."""
        if method_name not in self.inconsistent_responses:
            self.inconsistent_responses[method_name] = {}
        
        self.inconsistent_responses[method_name][request_key] = {
            "instances": instance_responses
        }
    
    def get_response_structure(self, response: Dict[str, Any]) -> str:
        """Get a simplified structure representation of the response for comparison."""
        if not isinstance(response, dict):
            return str(type(response).__name__)
            
        def simplify_structure(obj, parent_key=""):
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    # Normalize address-specific fields that vary between wallet types
                    if parent_key == "balances" and self._is_address_key(k):
                        # This is likely an address key, normalize it
                        result["<address>"] = simplify_structure(v, k)
                    elif k in ["address", "pubkey", "derivation_path", "account_index"]:
                        # These fields typically vary between instances, normalize them
                        result[k] = "<normalized>"
                    else:
                        result[k] = simplify_structure(v, k)
                return result
            elif isinstance(obj, list):
                if len(obj) > 0:
                    return [simplify_structure(obj[0], parent_key)]
                return []
            else:
                return type(obj).__name__
        
        return json.dumps(simplify_structure(response), sort_keys=True)
    
    def run_task_lifecycle(self, instance: KDFInstance, init_request: Dict[str, Any], 
                          method_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """Run a complete task lifecycle: init -> status (until completion/error) -> cancel."""
        lifecycle_responses = {
            "init": [],
            "status": [], 
            "cancel": []
        }
        
        # Step 1: Run init
        self.logger.info(f"Running {method_name}::init on {instance.name}")
        self._current_timing_context = {}
        success, init_response = self.send_request(instance, init_request)
        
        # Record init timing (assuming init_request has a method for naming)
        timing_info = getattr(self, '_current_timing_context', {})
        if timing_info:
            init_key = f"{method_name}_init"
            self._record_response_delay(
                method_name, 
                init_key, 
                instance.name,
                timing_info.get('status_code', 500),
                timing_info.get('delay', 0.0)
            )
        lifecycle_responses["init"].append(init_response)
        
        if not success:
            error_msg = init_response.get('error', 'Unknown error') if isinstance(init_response, dict) else str(init_response)
            self.logger.error(f"Init failed on {instance.name}: {error_msg}")
            return lifecycle_responses
        
        # Extract task_id
        task_id = None
        if "result" in init_response and "task_id" in init_response["result"]:
            task_id = init_response["result"]["task_id"]
            self.logger.info(f"Init successful on {instance.name}, task_id: {task_id}")
        else:
            self.logger.error(f"Init response missing task_id on {instance.name}: {init_response}")
            return lifecycle_responses
        
        # Step 2: Poll status until completion
        self.logger.info(f"Polling {method_name}::status on {instance.name}")
        status_request = {
            "userpass": instance.userpass,
            "mmrpc": "2.0", 
            "method": method_name.replace("::init", "::status"),
            "params": {
                "task_id": task_id,
                "forget_if_finished": False
            }
        }
        
        max_status_checks = 20
        status_check_count = 0
        
        while status_check_count < max_status_checks:
            time.sleep(2)  # Wait between status checks
            status_check_count += 1
            
            success, status_response = self.send_request(instance, status_request)
            lifecycle_responses["status"].append(status_response)
            
            if not success:
                error_msg = status_response.get('error', 'Unknown error') if isinstance(status_response, dict) else str(status_response)
                self.logger.warning(f"Status check {status_check_count} failed on {instance.name}: {error_msg}")
                break
            
            # Check status
            if "result" in status_response:
                result = status_response["result"]
                
                # Handle case where result is a dict with status info
                if isinstance(result, dict) and "status" in result:
                    status = result.get("status")
                    details = result.get("details", "")
                    
                    self.logger.debug(f"Status check {status_check_count} on {instance.name}: {status} - {details}")
                    
                    # Check if task is complete
                    if status == "Ok":
                        self.logger.info(f"Task completed successfully on {instance.name}")
                        break
                    elif status == "Error":
                        self.logger.warning(f"Task failed on {instance.name}: {details}")
                        break
                    elif status not in IN_PROGRESS_STATUSES and isinstance(details, str) and details not in IN_PROGRESS_STATUSES:
                        self.logger.info(f"Task in unknown status on {instance.name}: {status}")
                        break
                else:
                    # Handle case where result is the final response (task completed)
                    self.logger.debug(f"Status check {status_check_count} on {instance.name}: Ok - {result}")
                    self.logger.info(f"Task completed successfully on {instance.name}")
                    break
            else:
                self.logger.warning(f"Unexpected status response on {instance.name}: {status_response}")
                break
        
        # Step 3: Cancel the task (if still running)
        self.logger.info(f"Running {method_name}::cancel on {instance.name}")
        cancel_request = {
            "userpass": instance.userpass,
            "mmrpc": "2.0",
            "method": method_name.replace("::init", "::cancel"),
            "params": {
                "task_id": task_id
            }
        }
        
        success, cancel_response = self.send_request(instance, cancel_request)
        lifecycle_responses["cancel"].append(cancel_response)
        
        if success:
            self.logger.debug(f"Cancel successful on {instance.name}")
        else:
            error_msg = cancel_response.get('error', 'Unknown error') if isinstance(cancel_response, dict) else str(cancel_response)
            self.logger.debug(f"Cancel failed on {instance.name}: {error_msg}")
        
        return lifecycle_responses
    
    def _execute_prerequisite_method(self, prereq_method: str, all_requests: Dict[str, Any], 
                                   kdf_methods: Dict[str, Any]) -> None:
        """Execute a prerequisite method before running the main method."""
        # Find a suitable request example for the prerequisite method
        prereq_config = kdf_methods.get(prereq_method, {})
        prereq_examples = prereq_config.get('examples', {})
        
        if not prereq_examples:
            self.logger.warning(f"No examples found for prerequisite method: {prereq_method}")
            return
        
        # Use the first available example
        prereq_request_key = next(iter(prereq_examples.keys()))
        
        if prereq_request_key not in all_requests:
            self.logger.error(f"Request data not found for prerequisite: {prereq_request_key}")
            return
        
        prereq_request_data = all_requests[prereq_request_key]
        
        # Execute the prerequisite method on all instances
        for instance in KDF_INSTANCES:
            self.logger.info(f"Executing prerequisite {prereq_method} on {instance.name}")
            
            # Get the ticker for disabling if needed
            ticker = None
            if "params" in prereq_request_data and "ticker" in prereq_request_data["params"]:
                ticker = prereq_request_data["params"]["ticker"]
            elif "coin" in prereq_request_data:
                ticker = prereq_request_data["coin"]
            
            # Disable coin first if needed
            if ticker:
                self.disable_coin(instance, ticker)
            
            # Modify request for non-HD instances
            if "nonhd" in instance.name:
                modified_request = self.normalize_request_for_non_hd(prereq_request_data)
            else:
                modified_request = prereq_request_data
            
            # Set up timing context and send prerequisite request
            self._current_timing_context = {}
            timeout = self._get_method_timeout(prereq_method)
            success, response = self.send_request(instance, modified_request, timeout)
            
            # Record timing information for prerequisite
            timing_info = getattr(self, '_current_timing_context', {})
            if timing_info:
                self._record_response_delay(
                    prereq_method, 
                    prereq_request_key, 
                    instance.name,
                    timing_info.get('status_code', 500),
                    timing_info.get('delay', 0.0)
                )
            
            if success:
                self.logger.info(f"Prerequisite {prereq_method} succeeded on {instance.name}")
                self.logger.debug(f"Prerequisite response: {json.dumps(response, indent=2)}")
            else:
                error_msg = response.get('error', 'Unknown error') if isinstance(response, dict) else str(response)
                self.logger.warning(f"Prerequisite {prereq_method} failed on {instance.name}: {error_msg}")
                if isinstance(response, dict):
                    self.logger.debug(f"Prerequisite error: {json.dumps(response, indent=2)}")
                else:
                    self.logger.debug(f"Prerequisite error: {response}")
    
    def collect_regular_method(self, response_name: str, request_data: Dict[str, Any], 
                              method_name: str, platform_coin: Optional[str] = None) -> CollectionResult:
        """Collect responses for regular (non-task) methods."""
        instance_responses = {}
        all_successful = True
        consistent_structure = True
        first_response_structure = None
        
        # Get the ticker for disabling if needed
        ticker = None
        if "params" in request_data and "ticker" in request_data["params"]:
            ticker = request_data["params"]["ticker"]
        elif "coin" in request_data:
            ticker = request_data["coin"]
        
        for instance in KDF_INSTANCES:
            # Check if platform coin is required and enabled
            if platform_coin:
                key = f"{instance.name}:{platform_coin}"
                if not self.platform_enabled.get(key, False):
                    self.logger.info(f"Skipping {response_name} on {instance.name} - Platform coin {platform_coin} not available")
                    all_successful = False
                    continue
            
            # Disable coin first if needed
            if ticker:
                self.disable_coin(instance, ticker)
            
            # Modify request for non-HD instances
            if "nonhd" in instance.name:
                modified_request = self.normalize_request_for_non_hd(request_data)
            else:
                modified_request = request_data
            
            # Set up timing context and send request
            self._current_timing_context = {}
            timeout = self._get_method_timeout(method_name)
            success, response = self.send_request(instance, modified_request, timeout)
            
            # Record timing information
            timing_info = getattr(self, '_current_timing_context', {})
            if timing_info:
                self._record_response_delay(
                    method_name, 
                    response_name, 
                    instance.name,
                    timing_info.get('status_code', 500),
                    timing_info.get('delay', 0.0)
                )
            
            instance_responses[instance.name] = response
            
            if not success:
                all_successful = False
                error_msg = response.get('error', 'Unknown error') if isinstance(response, dict) else str(response)
                self.logger.warning(f"{instance.name}: FAILED - {error_msg}")
                if isinstance(response, dict):
                    self.logger.debug(f"{instance.name}: Error response: {json.dumps(response, indent=2)}")
                else:
                    self.logger.debug(f"{instance.name}: Error response: {response}")
            else:
                self.logger.info(f"{instance.name}: SUCCESS")
                self.logger.debug(f"{instance.name}: Success response: {json.dumps(response, indent=2)}")
                
                # Check response length
                response_str = json.dumps(response)
                if len(response_str) > 10000:
                    self.logger.warning(f"{instance.name}: Response too long ({len(response_str)} chars)")
                    all_successful = False
                
                # Check structure consistency
                if first_response_structure is None:
                    first_response_structure = self.get_response_structure(response)
                elif self.get_response_structure(response) != first_response_structure:
                    consistent_structure = False
        
        # Record inconsistent responses for analysis
        if not consistent_structure and len(instance_responses) > 0:
            successful_responses = {k: v for k, v in instance_responses.items() if "error" not in v}
            if successful_responses:
                self._record_inconsistent_response(method_name, response_name, instance_responses)
                self.logger.warning(f"Inconsistent structure detected for {method_name}::{response_name}")
        
        # Auto-updatable if we have successful responses (even if inconsistent structure)
        # This allows native-hd responses to be used for documentation
        successful_responses = {k: v for k, v in instance_responses.items() if "error" not in v}
        auto_updatable = len(successful_responses) > 0
        
        return CollectionResult(
            response_name=response_name,
            instance_responses=instance_responses,
            all_successful=all_successful,
            consistent_structure=consistent_structure,
            auto_updatable=auto_updatable,
            collection_method="regular",
            notes=f"Method: {method_name}"
        )
    
    def collect_task_lifecycle_method(self, method_name: str, request_keys: List[str], 
                                    all_requests: Dict[str, Any], platform_coin: Optional[str] = None) -> List[CollectionResult]:
        """Collect responses for task-based methods (init/status/cancel lifecycle)."""
        results = []
        
        # Find the init request
        init_response_name = None
        for response_name in request_keys:
            if "Init" in response_name and response_name not in SKIP_METHODS:
                init_response_name = response_name
                break
        
        if not init_response_name or init_response_name not in all_requests:
            self.logger.error(f"Could not find init request for task method: {method_name}")
            return results
        
        init_request = all_requests[init_response_name]
        
        # Get the ticker for disabling if needed
        ticker = None
        if "params" in init_request and "ticker" in init_request["params"]:
            ticker = init_request["params"]["ticker"]
        
        task_lifecycle_responses = {}
        
        for instance in KDF_INSTANCES:
            try:
                self.logger.info(f"Running task lifecycle for {method_name} on {instance.name}")
                
                # Check platform coin dependency
                if platform_coin:
                    key = f"{instance.name}:{platform_coin}"
                    if not self.platform_enabled.get(key, False):
                        self.logger.info(f"Skipping {method_name} on {instance.name} - Platform coin {platform_coin} not available")
                        continue
                
                # Disable coin first if needed
                if ticker:
                    try:
                        self.disable_coin(instance, ticker)
                    except Exception as e:
                        self.logger.error(f"Error disabling {ticker} on {instance.name}: {e}")
                        self.logger.error(f"Exception type: {type(e)}")
                        continue
                
                # Modify request for non-HD instances
                if "nonhd" in instance.name:
                    modified_request = self.normalize_request_for_non_hd(init_request)
                else:
                    modified_request = init_request
                
                # Run the complete task lifecycle
                lifecycle = self.run_task_lifecycle(instance, modified_request, method_name)
            except Exception as e:
                self.logger.error(f"Task lifecycle error for {method_name} on {instance.name}: {e}")
                self.logger.error(f"Exception type: {type(e)}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                continue
            
            # Store lifecycle responses for each phase
            for phase, responses in lifecycle.items():
                for i, response in enumerate(responses):
                    phase_response_name = f"{init_response_name.replace('Init', phase.title())}"
                    if i > 0:  # Multiple responses in same phase
                        phase_response_name += f"_{i+1}"
                    
                    if phase_response_name not in task_lifecycle_responses:
                        task_lifecycle_responses[phase_response_name] = {}
                    task_lifecycle_responses[phase_response_name][instance.name] = response
        
        # Convert lifecycle responses to CollectionResults
        for response_name, instances in task_lifecycle_responses.items():
            all_successful = True
            consistent_structure = True
            first_response_structure = None
            
            for instance_name, response in instances.items():
                if "error" in response:
                    all_successful = False
                    break
                
                response_str = json.dumps(response)
                if len(response_str) > 10000:
                    all_successful = False
                    break
                
                current_structure = self.get_response_structure(response)
                if first_response_structure is None:
                    first_response_structure = current_structure
                elif current_structure != first_response_structure:
                    consistent_structure = False
                    break
            
            # Record inconsistent responses for analysis
            if not consistent_structure and len(instances) > 0:
                successful_responses = {k: v for k, v in instances.items() if "error" not in v}
                if successful_responses:
                    self._record_inconsistent_response(method_name, response_name, instances)
                    self.logger.warning(f"Inconsistent structure detected for {method_name}::{response_name}")
            
            # Auto-updatable if we have successful responses (even if inconsistent structure)
            successful_responses = {k: v for k, v in instances.items() if "error" not in v}
            auto_updatable = len(successful_responses) > 0
            
            results.append(CollectionResult(
                response_name=response_name,
                instance_responses=instances,
                all_successful=all_successful,
                consistent_structure=consistent_structure,
                auto_updatable=auto_updatable,
                collection_method="task_lifecycle",
                notes=f"Task method: {method_name}, Phase: {response_name.split('_')[-1] if '_' in response_name else 'base'}"
            ))
        
        return results
    
    def collect_all_responses(self) -> Dict[str, Any]:
        """Main method to collect ALL responses, not just missing ones."""
        self.logger.info("Starting comprehensive response collection for ALL methods")
        
        # Load ALL request data files 
        workspace_root = Path(__file__).parent.parent.parent
        v2_requests_file = workspace_root / "src/data/requests/kdf/v2/coin_activation.json"
        legacy_requests_file = workspace_root / "src/data/requests/kdf/legacy/coin_activation.json"
        
        v2_requests = self.load_json_file(v2_requests_file)
        legacy_requests = self.load_json_file(legacy_requests_file)
        all_requests = {**v2_requests, **legacy_requests}
        
        # Load method config to check for deprecated methods
        kdf_methods_file = workspace_root / "src/data/kdf_methods.json"
        kdf_methods = self.load_json_file(kdf_methods_file) or {}
        
        # Group requests by method to process all examples for each method
        methods_with_requests = {}
        for request_key, request_data in all_requests.items():
            method_name = request_data.get("method", "unknown")
            method_config = kdf_methods.get(method_name, {})
            
            # Skip deprecated methods
            if method_config.get('deprecated', False):
                self.logger.debug(f"Skipping deprecated method: {method_name}")
                continue
                
            if method_name not in methods_with_requests:
                methods_with_requests[method_name] = []
            methods_with_requests[method_name].append(request_key)
        
        self.logger.info(f"Found {len(methods_with_requests)} methods to process")
        self.logger.info(f"Total request examples: {sum(len(requests) for requests in methods_with_requests.values())}")
        
        # Process each method (excluding deprecated)
        for method_name, request_keys in methods_with_requests.items():
            method_config = kdf_methods.get(method_name, {})
            
            self.logger.info(f"Processing method: {method_name} ({len(request_keys)} examples)")
            
            # Check for prerequisite methods
            prerequisite_methods = method_config.get('requirements', {}).get('prerequisite_methods', [])
            if prerequisite_methods:
                for prereq_method in prerequisite_methods:
                    self.logger.info(f"Executing prerequisite method: {prereq_method}")
                    self._execute_prerequisite_method(prereq_method, all_requests, kdf_methods)
            
            # Check if this method needs a platform coin
            platform_coin = PLATFORM_DEPENDENCIES.get(method_name)
            if platform_coin:
                self.logger.info(f"Method requires platform coin: {platform_coin}")
                
                # Try to enable platform coin on all instances
                for instance in KDF_INSTANCES:
                    key = f"{instance.name}:{platform_coin}"
                    if key not in self.platform_enabled:
                        self.platform_enabled[key] = self.enable_platform_coin(instance, platform_coin)
            
            # Handle task-based methods specially
            if "task::" in method_name and "::init" in method_name:
                self.logger.info(f"Task-based method detected: {method_name}")
                task_results = self.collect_task_lifecycle_method(
                    method_name, request_keys, all_requests, platform_coin
                )
                self.results.extend(task_results)
                continue
            
            # Regular method processing (non-task)
            # Process each request example for this method
            for request_key in request_keys:
                self.logger.info(f"Collecting response: {request_key}")
                
                # Skip manual methods
                if request_key in SKIP_METHODS:
                    self.logger.info(f"Skipping {request_key} (manual method)")
                    continue
                
                # Find the request data
                if request_key not in all_requests:
                    self.logger.error(f"Request data not found for {request_key}")
                    continue
                
                request_data = all_requests[request_key]
                
                # Collect responses based on method type
                if "::" in method_name and method_name.startswith("task::"):
                    # Task lifecycle method
                    task_results = self.collect_task_lifecycle_method(method_name, [request_key], all_requests, platform_coin)
                    self.results.extend(task_results)
                else:
                    # Regular method
                    result = self.collect_regular_method(
                        request_key, request_data, method_name, platform_coin
                    )
                    self.results.append(result)
        
        return self.compile_results()
    
    def compile_results(self) -> Dict[str, Any]:
        """Compile all results into a unified format."""
        unified_results = {
            "metadata": {
                "collection_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "total_responses_collected": len(self.results),
                "auto_updatable_count": sum(1 for r in self.results if r.auto_updatable),
                "collection_summary": {
                    "regular_methods": sum(1 for r in self.results if r.collection_method == "regular"),
                    "task_lifecycle_methods": sum(1 for r in self.results if r.collection_method == "task_lifecycle"),
                }
            },
            "responses": {},
            "auto_updatable": {},
            "manual_review_needed": {}
        }
        
        for result in self.results:
            # Add to main responses
            unified_results["responses"][result.response_name] = {
                "instances": result.instance_responses,
                "all_successful": result.all_successful,
                "consistent_structure": result.consistent_structure,
                "collection_method": result.collection_method,
                "notes": result.notes
            }
            
            # Categorize for update processing
            if result.auto_updatable:
                # Get canonical response (prefer native-hd, then first successful one)
                canonical_response = None
                
                # First, try to get native-hd response if it's successful
                if "native-hd" in result.instance_responses:
                    hd_response = result.instance_responses["native-hd"]
                    if "error" not in hd_response:
                        canonical_response = hd_response
                
                # If native-hd not available or failed, get first successful response
                if canonical_response is None:
                    canonical_response = next(
                        (resp for resp in result.instance_responses.values() if "error" not in resp),
                        None
                    )
                
                if canonical_response:
                    unified_results["auto_updatable"][result.response_name] = canonical_response
            else:
                # Analyze why it failed auto-update
                reasons = []
                
                has_errors = any("error" in resp for resp in result.instance_responses.values())
                if has_errors:
                    reasons.append("contains_errors")
                
                if not result.consistent_structure:
                    reasons.append("inconsistent_structure")
                
                # Check response length
                for resp in result.instance_responses.values():
                    if "error" not in resp and len(json.dumps(resp)) > 10000:
                        reasons.append("response_too_long")
                        break
                
                if not reasons:
                    reasons.append("unknown")
                
                unified_results["manual_review_needed"][result.response_name] = {
                    "reasons": reasons,
                    "instances": result.instance_responses,
                    "collection_method": result.collection_method,
                    "notes": result.notes
                }
        
        return unified_results
    
    def save_delay_report(self, output_dir: Path) -> None:
        """Save response delay report to separate file."""
        delay_file = output_dir / "kdf_response_delays.json"
        
        # Add metadata to the delay report
        delay_report = {
            "metadata": {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "total_methods": len(self.response_delays),
                "total_requests": sum(len(examples) for examples in self.response_delays.values()),
                "description": "Response timing data for KDF methods across different environments"
            },
            "delays": self.response_delays
        }
        
        dump_sorted_json(delay_report, delay_file)
        
        self.logger.info(f"Response delay report saved to: {delay_file}")
    
    def save_inconsistent_responses_report(self, output_dir: Path) -> None:
        """Save inconsistent responses report to separate file."""
        inconsistent_file = output_dir / "inconsistent_responses.json"
        
        # Add metadata to the inconsistent responses report
        inconsistent_report = {
            "metadata": {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "total_inconsistent_methods": len(self.inconsistent_responses),
                "total_inconsistent_examples": sum(len(examples) for examples in self.inconsistent_responses.values()),
                "description": "Methods with inconsistent responses across KDF environments - useful for identifying environment-specific behaviors"
            },
            "inconsistent_responses": self.inconsistent_responses
        }
        
        dump_sorted_json(inconsistent_report, inconsistent_file)
        
        self.logger.info(f"Inconsistent responses report saved to: {inconsistent_file}")
    
    def regenerate_missing_responses_report(self, reports_dir: Path) -> None:
        """Regenerate missing responses report after response collection."""
        workspace_root = Path(__file__).parent.parent.parent
        
        # Import the postman generator for its response checking logic
        sys.path.append(str(workspace_root / "utils/py"))
        from generate_postman import UnifiedPostmanGenerator
        
        # Create a generator instance to use its response checking logic
        generator = UnifiedPostmanGenerator(workspace_root)
        
        # Load all request data
        v2_requests_file = workspace_root / "src/data/requests/kdf/v2/coin_activation.json"
        legacy_requests_file = workspace_root / "src/data/requests/kdf/legacy/coin_activation.json"
        
        v2_requests = self.load_json_file(v2_requests_file) or {}
        legacy_requests = self.load_json_file(legacy_requests_file) or {}
        
        # Load method config to check for deprecated methods
        kdf_methods_file = workspace_root / "src/data/kdf_methods.json"
        kdf_methods = self.load_json_file(kdf_methods_file) or {}
        
        # Check for missing responses
        missing_responses = {}
        
        # Check v2 requests
        for request_key, request_data in v2_requests.items():
            method_name = request_data.get("method", "unknown")
            method_config = kdf_methods.get(method_name, {})
            
            # Skip deprecated methods
            if method_config.get('deprecated', False):
                continue
                
            # Skip manual methods (WalletConnect, Trezor, Metamask, PIN)
            if generator._is_manual_method(request_key):
                continue
                
            # Check if response exists and has content
            if not generator.check_response_exists(request_key, "v2"):
                if method_name not in missing_responses:
                    missing_responses[method_name] = []
                missing_responses[method_name].append(request_key)
        
        # Check legacy requests  
        for request_key, request_data in legacy_requests.items():
            method_name = request_data.get("method", "unknown")
            method_config = kdf_methods.get(method_name, {})
            
            # Skip deprecated methods
            if method_config.get('deprecated', False):
                continue
                
            # Skip manual methods
            if generator._is_manual_method(request_key):
                continue
                
            # Check if response exists and has content
            if not generator.check_response_exists(request_key, "legacy"):
                if method_name not in missing_responses:
                    missing_responses[method_name] = []
                missing_responses[method_name].append(request_key)
        
        # Sort the results
        sorted_missing = {}
        if missing_responses:
            for method in sorted(missing_responses.keys()):
                sorted_missing[method] = sorted(missing_responses[method])
        
        # Save regenerated missing responses report
        missing_file = reports_dir / "missing_responses.json"
        dump_sorted_json(sorted_missing, missing_file)
        
        self.logger.info(f"Missing responses report regenerated: {missing_file}")
        self.logger.info(f"Total missing methods: {len(sorted_missing)}")
        self.logger.info(f"Total missing examples: {sum(len(examples) for examples in sorted_missing.values())}")
    
    def update_response_files(self, auto_updatable_responses: Dict[str, Any]) -> int:
        """Update response files with successful responses."""
        if not auto_updatable_responses:
            self.logger.info("No new successful responses to update.")
            return 0
        
        self.logger.info("Updating response files")
        
        # Load existing response files (relative to workspace root)
        workspace_root = Path(__file__).parent.parent.parent
        v2_response_file = workspace_root / "src/data/responses/kdf/v2/coin_activation.json"
        
        if v2_response_file.exists():
            with open(v2_response_file, 'r') as f:
                v2_responses = json.load(f)
        else:
            v2_responses = {}
        
        # Add successful responses
        updated_count = 0
        for response_name, response_data in auto_updatable_responses.items():
            # Skip if already exists with actual content (not just empty templates)
            if response_name in v2_responses:
                existing_entry = v2_responses[response_name]
                # Check if it's just an empty template (both success and error arrays are empty)
                is_empty_template = (
                    isinstance(existing_entry, dict) and
                    existing_entry.get("success") == [] and
                    existing_entry.get("error") == []
                )
                
                if not is_empty_template:
                    self.logger.info(f"Skipping {response_name} (already has content)")
                    continue
                else:
                    self.logger.info(f"Updating {response_name} (was empty template)")
            else:
                self.logger.info(f"Adding new response: {response_name}")
                
            # Create the response entry
            response_entry = {
                "success": [
                    {
                        "title": "Success",
                        "generated": True,
                        "json": response_data
                    }
                ],
                "error": []
            }
            
            v2_responses[response_name] = response_entry
            updated_count += 1
            self.logger.info(f"Added: {response_name}")
        
        # Save updated file
        if updated_count > 0:
            dump_sorted_json(v2_responses, v2_response_file)
            self.logger.info(f"Updated {v2_response_file} with {updated_count} new responses")
        
        return updated_count
    
    def validate_responses(self, validate_collected_responses: bool = False) -> Dict[str, Any]:
        """Validate existing response files and optionally collected responses."""
        self.logger.info("Starting response validation")
        
        # Validate request metadata (tags and prerequisites)
        try:
            from validate_request_metadata import validate_request_metadata
            request_metadata_summary = validate_request_metadata(
                workspace_root=Path(__file__).parent.parent.parent,
                silent=True
            )
            if request_metadata_summary['files_modified'] > 0:
                self.logger.info(f"Fixed request metadata in {request_metadata_summary['files_modified']} files")
        except Exception as e:
            self.logger.warning(f"Request metadata validation failed: {e}")
            request_metadata_summary = {"error": str(e)}
        
        # Validate existing response files
        success, errors, warnings = self.validator.validate_all()
        
        # Sort JSON data files alphabetically by keys
        sorted_files = self._sort_json_files()
        
        # Add empty template entries for missing responses
        templated_files = self._add_missing_response_templates()
        
        validation_results = {
            "existing_files": {
                "success": success,
                "errors": [str(error) for error in errors],
                "warnings": [str(warning) for warning in warnings],
                "error_count": len(errors),
                "warning_count": len(warnings),
                "sorted_files": sorted_files,
                "templated_files": templated_files
            },
            "request_metadata": request_metadata_summary
        }
        
        # Optionally validate collected responses format
        if validate_collected_responses and self.results:
            collected_validation = self._validate_collected_responses()
            validation_results["collected_responses"] = collected_validation
        
        return validation_results
    
    def _sort_json_files(self) -> Dict[str, Any]:
        """Sort JSON data files alphabetically by keys and save them."""
        workspace_root = Path(__file__).parent.parent.parent
        sorted_files = {}
        
        # Define all JSON files to sort
        files_to_sort = [
            # Response files
            workspace_root / "src/data/responses/kdf/v2/coin_activation.json",
            workspace_root / "src/data/responses/kdf/legacy/coin_activation.json", 
            workspace_root / "src/data/responses/kdf/common.json",
            # Request files
            workspace_root / "src/data/requests/kdf/v2/coin_activation.json",
            workspace_root / "src/data/requests/kdf/legacy/coin_activation.json",
            # Table files (common structures)
            workspace_root / "src/data/tables/common-structures/activation.json",
            workspace_root / "src/data/tables/common-structures/common.json",
            workspace_root / "src/data/tables/common-structures/lightning.json",
            workspace_root / "src/data/tables/common-structures/maker-events.json",
            workspace_root / "src/data/tables/common-structures/nfts.json",
            workspace_root / "src/data/tables/common-structures/orders.json",
            workspace_root / "src/data/tables/common-structures/swaps.json",
            workspace_root / "src/data/tables/common-structures/taker-events.json",
            workspace_root / "src/data/tables/common-structures/wallet.json",
            # Table files (legacy and v2)
            workspace_root / "src/data/tables/legacy/coin_activation.json",
            workspace_root / "src/data/tables/v2/coin_activation.json",
            workspace_root / "src/data/tables/v2/streaming.json",
            workspace_root / "src/data/tables/v2/utils.json",
            workspace_root / "src/data/tables/v2/wallet.json",
            # KDF methods file
            workspace_root / "src/data/kdf_methods.json"
        ]
        
        for file_path in files_to_sort:
            if not file_path.exists():
                continue
                
            try:
                # Read the file
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if not isinstance(data, dict):
                    continue
                
                # Check if already sorted
                keys = list(data.keys())
                sorted_keys = sorted(keys, key=str.lower)  # Case-insensitive sort
                
                if keys != sorted_keys:
                    # File needs sorting
                    self.logger.info(f"Sorting JSON file: {file_path.name}")
                    
                    # Create sorted dictionary
                    sorted_data = {key: data[key] for key in sorted_keys}
                    
                    # Write sorted data back to file
                    dump_sorted_json(sorted_data, file_path)
                    
                    sorted_files[str(file_path.relative_to(workspace_root))] = {
                        "action": "sorted",
                        "keys_moved": [key for key in keys if keys.index(key) != sorted_keys.index(key)]
                    }
                else:
                    # File already sorted
                    sorted_files[str(file_path.relative_to(workspace_root))] = {
                        "action": "already_sorted",
                        "keys_moved": []
                    }
                    
            except (json.JSONDecodeError, Exception) as e:
                sorted_files[str(file_path.relative_to(workspace_root))] = {
                    "action": "error",
                    "error": str(e)
                }
        
        return sorted_files
    
    def _add_missing_response_templates(self) -> Dict[str, Any]:
        """Add empty template entries for requests missing any responses."""
        workspace_root = Path(__file__).parent.parent.parent
        templated_files = {}
        
        # Load request data to identify all available request methods
        request_files = [
            (workspace_root / "src/data/requests/kdf/v2/coin_activation.json", 
             workspace_root / "src/data/responses/kdf/v2/coin_activation.json"),
            (workspace_root / "src/data/requests/kdf/legacy/coin_activation.json", 
             workspace_root / "src/data/responses/kdf/legacy/coin_activation.json")
        ]
        
        for request_file, response_file in request_files:
            if not request_file.exists() or not response_file.exists():
                continue
                
            try:
                # Load request and response data
                with open(request_file, 'r', encoding='utf-8') as f:
                    request_data = json.load(f)
                    
                with open(response_file, 'r', encoding='utf-8') as f:
                    response_data = json.load(f)
                
                # Load KDF methods to check for deprecated entries
                kdf_methods_file = workspace_root / "src/data/kdf_methods.json"
                kdf_methods = {}
                if kdf_methods_file.exists():
                    with open(kdf_methods_file, 'r', encoding='utf-8') as f:
                        kdf_methods = json.load(f)
                
                # Find missing response entries (excluding deprecated methods)
                missing_entries = []
                updated = False
                
                for request_key in request_data.keys():
                    if request_key not in response_data:
                        # Check if the method for this request is deprecated
                        request_method = request_data[request_key].get('method')
                        if request_method and kdf_methods.get(request_method, {}).get('deprecated', False):
                            continue  # Skip deprecated methods
                        # Add empty template
                        response_data[request_key] = {
                            "success": [],
                            "error": []
                        }
                        missing_entries.append(request_key)
                        updated = True
                        self.logger.info(f"Added empty template for missing response: {request_key}")
                
                # Save updated response file if changes were made
                if updated:
                    # Sort the data before saving
                    sorted_keys = sorted(response_data.keys(), key=str.lower)
                    sorted_response_data = {key: response_data[key] for key in sorted_keys}
                    
                    dump_sorted_json(sorted_response_data, response_file)
                    
                    templated_files[str(response_file.relative_to(workspace_root))] = {
                        "action": "templated",
                        "added_entries": missing_entries,
                        "count": len(missing_entries)
                    }
                else:
                    templated_files[str(response_file.relative_to(workspace_root))] = {
                        "action": "complete",
                        "added_entries": [],
                        "count": 0
                    }
                    
            except (json.JSONDecodeError, Exception) as e:
                templated_files[str(response_file.relative_to(workspace_root))] = {
                    "action": "error",
                    "error": str(e)
                }
        
        return templated_files
    
    def _validate_collected_responses(self) -> Dict[str, Any]:
        """Validate the format of collected responses."""
        validation_errors = []
        validation_warnings = []
        
        for result in self.results:
            # Check if auto-updatable responses follow expected format
            if result.auto_updatable:
                for instance_name, response in result.instance_responses.items():
                    if "error" in response:
                        continue  # Skip error responses
                    
                    # Validate response structure
                    if not isinstance(response, dict):
                        validation_errors.append(f"Response {result.response_name} from {instance_name}: Expected object, got {type(response).__name__}")
                        continue
                    
                    # Check for v2 API format
                    if "mmrpc" in response:
                        if response.get("mmrpc") != "2.0":
                            validation_warnings.append(f"Response {result.response_name} from {instance_name}: Unexpected mmrpc version '{response.get('mmrpc')}'")
                        
                        if "result" not in response and "error" not in response:
                            validation_errors.append(f"Response {result.response_name} from {instance_name}: Missing 'result' or 'error' field in v2 API response")
        
        return {
            "errors": validation_errors,
            "warnings": validation_warnings,
            "error_count": len(validation_errors),
            "warning_count": len(validation_warnings)
        }
    
    def save_results(self, results: Dict[str, Any], output_file: Path):
        """Save results to output file."""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        dump_sorted_json(results, output_file)
        
        self.logger.info(f"Unified results saved to: {output_file}")


class KdfResponseValidator:
    """Validator for KDF response JSON files."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []
        self.fixes_applied: List[str] = []
        self.common_responses: Dict[str, Dict] = {}
        
        # Valid response types
        self.valid_response_types = {'success', 'error'}
        
        # Valid request key pattern (alphanumeric, PascalCase with optional leading numeric)
        self.request_key_pattern = re.compile(r'^[A-Z0-9][a-zA-Z0-9]*$')

    def validate_all(self) -> Tuple[bool, List[ValidationError], List[ValidationError]]:
        """Validate all KDF response files."""
        workspace_root = Path(__file__).parent.parent.parent
        base_path = workspace_root / 'src/data/responses/kdf'
        
        if not base_path.exists():
            self.errors.append(ValidationError(
                str(base_path), 
                "MISSING_DIRECTORY",
                "KDF responses directory does not exist"
            ))
            return False, self.errors, self.warnings
            
        # Load common responses first
        self._load_common_responses(base_path)
            
        # Validate legacy and v2 directories
        for version in ['legacy', 'v2']:
            version_path = base_path / version
            if version_path.exists():
                self._validate_directory(version_path, version)
            else:
                self.errors.append(ValidationError(
                    str(version_path),
                    "MISSING_DIRECTORY", 
                    f"Missing {version} directory"
                ))
        
        # Check request/response alignment
        self._validate_request_response_alignment()
        
        return len(self.errors) == 0, self.errors, self.warnings

    def _load_common_responses(self, base_path: Path):
        """Load common responses from common.json."""
        common_file = base_path / 'common.json'
        if common_file.exists():
            try:
                with open(common_file, 'r', encoding='utf-8') as f:
                    self.common_responses = json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                self.warnings.append(ValidationError(
                    str(common_file),
                    "COMMON_RESPONSES_LOAD_ERROR",
                    f"Failed to load common responses: {str(e)}"
                ))

    def resolve_response_reference(self, response_value: Any) -> Any:
        """Resolve response references to common responses."""
        if isinstance(response_value, str) and response_value in self.common_responses:
            return self.common_responses[response_value]
        elif isinstance(response_value, list):
            resolved_list = []
            for item in response_value:
                if isinstance(item, str) and item in self.common_responses:
                    resolved_list.append(self.common_responses[item])
                else:
                    resolved_list.append(item)
            return resolved_list
        elif isinstance(response_value, dict):
            # Recursively resolve references in dictionaries
            resolved_dict = {}
            for key, value in response_value.items():
                resolved_dict[key] = self.resolve_response_reference(value)
            return resolved_dict
        else:
            return response_value

    def _validate_directory(self, dir_path: Path, version: str):
        """Validate all JSON files in a directory."""
        json_files = list(dir_path.glob('*.json'))
        
        if not json_files:
            self.warnings.append(ValidationError(
                str(dir_path),
                "EMPTY_DIRECTORY",
                f"No JSON files found in {version} directory"
            ))
            return
            
        for json_file in json_files:
            self._validate_file(json_file, version)

    def _validate_file(self, file_path: Path, version: str):
        """Validate a single JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            if not content:
                self.errors.append(ValidationError(
                    str(file_path),
                    "EMPTY_FILE",
                    "File is empty"
                ))
                return
                
            # Parse JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                self.errors.append(ValidationError(
                    str(file_path),
                    "INVALID_JSON",
                    f"JSON syntax error: {e.msg} at line {e.lineno}, column {e.colno}"
                ))
                return
                
            # Validate structure
            self._validate_file_structure(file_path, data)
            
        except Exception as e:
            self.errors.append(ValidationError(
                str(file_path),
                "FILE_ERROR",
                f"Error reading file: {str(e)}"
            ))

    def _validate_file_structure(self, file_path: Path, data: Dict):
        """Validate the overall structure of a response file."""
        if not data:
            self.warnings.append(ValidationError(
                str(file_path),
                "EMPTY_DATA",
                "File contains no request definitions"
            ))
            return
            
        # Validate each request key and its responses
        for request_key, responses in data.items():
            self._validate_request_key(file_path, request_key)
            # Resolve common response references before validation
            resolved_responses = self.resolve_response_reference(responses)
            self._validate_response_structure(file_path, request_key, resolved_responses)

    def _validate_request_key(self, file_path: Path, request_key: str):
        """Validate request key naming convention."""
            
        if not self.request_key_pattern.match(request_key):
            self.errors.append(ValidationError(
                str(file_path),
                "INVALID_KEY_FORMAT",
                f"Request key '{request_key}' should follow PascalCase/camelCase pattern",
                request_key
            ))
            
        # Check for common issues
        if request_key.lower() != request_key and request_key.upper() != request_key:
            if '_' in request_key:
                self.warnings.append(ValidationError(
                    str(file_path),
                    "KEY_STYLE_WARNING",
                    f"Request key '{request_key}' contains underscores, consider camelCase",
                    request_key
                ))

    def _validate_response_structure(self, file_path: Path, request_key: str, responses: Any):
        """Validate the structure of responses for a request key."""
        if not isinstance(responses, dict):
            self.errors.append(ValidationError(
                str(file_path),
                "INVALID_RESPONSES_TYPE",
                f"Responses must be an object, got {type(responses).__name__}",
                request_key
            ))
            return
            
        # Check for required response types
        has_success = 'success' in responses
        has_error = 'error' in responses
        
        if not has_success and not has_error:
            self.errors.append(ValidationError(
                str(file_path),
                "MISSING_RESPONSE_TYPES",
                "Must have at least 'success' or 'error' responses",
                request_key
            ))
            return
            
        # Validate each response type
        for response_type, response_list in responses.items():
            if response_type not in self.valid_response_types:
                self.errors.append(ValidationError(
                    str(file_path),
                    "INVALID_RESPONSE_TYPE",
                    f"Invalid response type '{response_type}', must be 'success' or 'error'",
                    f"{request_key}.{response_type}"
                ))
                continue
                
            self._validate_response_list(file_path, request_key, response_type, response_list)

    def _validate_response_list(self, file_path: Path, request_key: str, response_type: str, response_list: Any):
        """Validate a list of responses."""
        if not isinstance(response_list, list):
            self.errors.append(ValidationError(
                str(file_path),
                "INVALID_RESPONSE_LIST",
                f"Response list must be an array, got {type(response_list).__name__}",
                f"{request_key}.{response_type}"
            ))
            return
            
        if not response_list:
            self.warnings.append(ValidationError(
                str(file_path),
                "EMPTY_RESPONSE_LIST",
                f"Empty {response_type} response list",
                f"{request_key}.{response_type}"
            ))
            return
            
        for idx, response in enumerate(response_list):
            self._validate_response_item(file_path, request_key, response_type, idx, response)

    def _validate_response_item(self, file_path: Path, request_key: str, response_type: str, idx: int, response: Any):
        """Validate a single response item."""
        location = f"{request_key}.{response_type}[{idx}]"
        
        if not isinstance(response, dict):
            self.errors.append(ValidationError(
                str(file_path),
                "INVALID_RESPONSE_ITEM",
                f"Response item must be an object, got {type(response).__name__}",
                location
            ))
            return
            
        # Check required fields
        required_fields = {'title', 'json'}
        missing_fields = required_fields - set(response.keys())
        
        if missing_fields:
            self.errors.append(ValidationError(
                str(file_path),
                "MISSING_REQUIRED_FIELDS",
                f"Missing required fields: {', '.join(missing_fields)}",
                location
            ))
            
        # Validate individual fields
        if 'title' in response:
            self._validate_title_field(file_path, location, response['title'])
            
        if 'notes' in response:
            self._validate_notes_field(file_path, location, response['notes'])
            
        if 'json' in response:
            self._validate_json_field(file_path, location, response['json'])

    def _validate_title_field(self, file_path: Path, location: str, title: Any):
        """Validate the title field."""
        if not isinstance(title, str):
            self.errors.append(ValidationError(
                str(file_path),
                "INVALID_TITLE_TYPE",
                f"Title must be a string, got {type(title).__name__}",
                f"{location}.title"
            ))
            return
            
        if not title.strip():
            self.errors.append(ValidationError(
                str(file_path),
                "EMPTY_TITLE",
                "Title cannot be empty",
                f"{location}.title"
            ))

    def _validate_notes_field(self, file_path: Path, location: str, notes: Any):
        """Validate the notes field."""
        if not isinstance(notes, str):
            self.errors.append(ValidationError(
                str(file_path),
                "INVALID_NOTES_TYPE",
                f"Notes must be a string, got {type(notes).__name__}",
                f"{location}.notes"
            ))

    def _validate_json_field(self, file_path: Path, location: str, json_data: Any):
        """Validate the json field."""
        if json_data is None:
            self.errors.append(ValidationError(
                str(file_path),
                "NULL_JSON_DATA",
                "JSON field cannot be null",
                f"{location}.json"
            ))
            return
            
        # JSON field should be a valid JSON structure (object, array, etc.)
        if not isinstance(json_data, (dict, list, str, int, float, bool)):
            self.errors.append(ValidationError(
                str(file_path),
                "INVALID_JSON_TYPE",
                f"JSON field contains invalid type: {type(json_data).__name__}",
                f"{location}.json"
            ))
            
        # For API responses, usually expect objects
        if isinstance(json_data, dict):
            # Common validation for API response format
            if 'mmrpc' in json_data:
                # V2 API format validation
                if json_data.get('mmrpc') != '2.0':
                    self.warnings.append(ValidationError(
                        str(file_path),
                        "UNEXPECTED_MMRPC_VERSION",
                        f"Expected mmrpc version '2.0', got '{json_data.get('mmrpc')}'",
                        f"{location}.json.mmrpc"
                    ))

    def _validate_request_response_alignment(self):
        """Validate that requests have corresponding responses and vice versa."""
        workspace_root = Path(__file__).parent.parent.parent
        
        # Load request data
        requests_by_version = {}
        for version in ['legacy', 'v2']:
            requests_path = workspace_root / f'src/data/requests/kdf/{version}'
            if requests_path.exists():
                requests_by_version[version] = self._load_request_keys(requests_path)

        # Load response data  
        responses_by_version = {}
        for version in ['legacy', 'v2']:
            responses_path = workspace_root / f'src/data/responses/kdf/{version}'
            if responses_path.exists():
                responses_by_version[version] = self._load_response_keys(responses_path)

        # Compare and report mismatches
        for version in ['legacy', 'v2']:
            request_keys = requests_by_version.get(version, set())
            response_keys = responses_by_version.get(version, set())
            
            # Requests without responses
            missing_responses = request_keys - response_keys
            for key in missing_responses:
                self.warnings.append(ValidationError(
                    f"src/data/responses/kdf/{version}/",
                    "MISSING_RESPONSE",
                    f"Request '{key}' exists but has no corresponding response data",
                    f"{version}/{key}"
                ))
            
            # Responses without requests
            missing_requests = response_keys - request_keys
            for key in missing_requests:
                self.warnings.append(ValidationError(
                    f"src/data/requests/kdf/{version}/",
                    "MISSING_REQUEST", 
                    f"Response '{key}' exists but has no corresponding request data",
                    f"{version}/{key}"
                ))

    def _load_request_keys(self, requests_path: Path) -> set:
        """Load all request keys from requests directory."""
        request_keys = set()
        try:
            for json_file in requests_path.glob('*.json'):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        request_keys.update(data.keys())
        except Exception as e:
            self.warnings.append(ValidationError(
                str(requests_path),
                "REQUEST_LOAD_ERROR",
                f"Error loading request keys: {str(e)}"
            ))
        return request_keys

    def _load_response_keys(self, responses_path: Path) -> set:
        """Load all response keys from responses directory."""
        response_keys = set()
        try:
            for json_file in responses_path.glob('*.json'):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        response_keys.update(data.keys())
        except Exception as e:
            self.warnings.append(ValidationError(
                str(responses_path),
                "RESPONSE_LOAD_ERROR",
                f"Error loading response keys: {str(e)}"
            ))
        return response_keys


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified KDF Response Manager and Validator")
# Mode argument removed - all functionality is always enabled
# Log level hardcoded to DEBUG for comprehensive output
# Output path hardcoded to postman/generated/reports/kdf_postman_responses.json  
# Validation always runs on both existing and collected responses
    parser.add_argument(
        "--update-files", 
        action="store_true",
        help="Automatically update response files with successful responses"
    )
# Verbose flag removed - warnings always shown
    
    args = parser.parse_args()
    
    try:
        # Initialize manager
        manager = UnifiedResponseManager()
        
        # Load missing responses data (relative to workspace root)
        workspace_root = Path(__file__).parent.parent.parent
        missing_responses_file = workspace_root / "postman/generated/reports/missing_responses.json"
        if not missing_responses_file.exists():
            print(f"Error: Missing responses file not found: {missing_responses_file}")
            print("Run the Postman collection generator first to create this file.")
            return
        
        # Load missing responses
        with open(missing_responses_file) as f:
            missing_responses = json.load(f)
        
        # Collect responses (all functionality enabled)
        results = manager.collect_all_responses()
        
        # Always validate both existing and collected responses
        validation_results = manager.validate_responses(validate_collected_responses=True)
        results["validation"] = validation_results
        
        # Save results (relative to workspace root)
        output_file = workspace_root / "postman/generated/reports/kdf_postman_responses.json"
        manager.save_results(results, output_file)
        
        # Save delay report
        reports_dir = workspace_root / "postman/generated/reports"
        manager.save_delay_report(reports_dir)
        
        # Save inconsistent responses report
        manager.save_inconsistent_responses_report(reports_dir)
        
        # Regenerate missing responses report after response collection
        manager.regenerate_missing_responses_report(reports_dir)
        
        # Print collection summary
        metadata = results.get("metadata", {})
        print(f"\n=== Collection Summary ===")
        print(f"Total responses collected: {metadata.get('total_responses_collected', 0)}")
        print(f"Auto-updatable responses: {metadata.get('auto_updatable_count', 0)}")
        print(f"Inconsistent responses: {len(manager.inconsistent_responses)}")
        print(f"Manual review needed: {len(results.get('manual_review_needed', {}))}")
        print(f"Results saved to: {output_file}")
        
        # Print validation summary if available
        if "validation" in results:
            validation = results["validation"]
            existing = validation["existing_files"]
            
            print(f"\n=== Validation Summary ===")
            print(f"Existing files validation: {'✅ PASS' if existing['success'] else '❌ FAIL'}")
            if existing["error_count"] > 0:
                print(f"Validation errors: {existing['error_count']}")
            if existing["warning_count"] > 0:
                print(f"Validation warnings: {existing['warning_count']}")
            
            # Show file sorting results
            if "sorted_files" in existing:
                sorted_files = existing["sorted_files"]
                sorted_count = sum(1 for info in sorted_files.values() if info.get("action") == "sorted")
                already_sorted_count = sum(1 for info in sorted_files.values() if info.get("action") == "already_sorted")
                
                if sorted_count > 0:
                    print(f"📄 Sorted {sorted_count} JSON file(s) alphabetically")
                    for file_path, info in sorted_files.items():
                        if info.get("action") == "sorted":
                            print(f"  ✅ {file_path}")
                else:
                    print(f"📄 All {already_sorted_count} JSON file(s) already sorted")
            
            # Show file templating results
            if "templated_files" in existing:
                templated_files = existing["templated_files"]
                templated_count = sum(1 for info in templated_files.values() if info.get("action") == "templated")
                complete_count = sum(1 for info in templated_files.values() if info.get("action") == "complete")
                total_added = sum(info.get("count", 0) for info in templated_files.values() if info.get("action") == "templated")
                
                if templated_count > 0:
                    print(f"📋 Added {total_added} empty template(s) to {templated_count} response file(s)")
                    for file_path, info in templated_files.items():
                        if info.get("action") == "templated":
                            entries = ", ".join(info.get("added_entries", [])[:3])  # Show first 3
                            if len(info.get("added_entries", [])) > 3:
                                entries += f" (+{len(info.get('added_entries', [])) - 3} more)"
                            print(f"  ✅ {file_path}: {entries}")
                else:
                    print(f"📋 All {complete_count} response file(s) already have templates for all requests")
            
            if "collected_responses" in validation:
                collected = validation["collected_responses"]
                print(f"Collected responses validation: {'✅ PASS' if collected['error_count'] == 0 else '❌ FAIL'}")
                if collected["error_count"] > 0:
                    print(f"Collected response errors: {collected['error_count']}")
                if collected["warning_count"] > 0:
                    print(f"Collected response warnings: {collected['warning_count']}")
            
            # Show validation details  
            if existing["errors"]:
                print(f"\nValidation Errors:")
                for error in existing["errors"]:
                    print(f"  {error}")
            if existing["warnings"]:
                print(f"\nValidation Warnings:")
                for warning in existing["warnings"]:
                    print(f"  {warning}")
        
        # Update response files if requested
        if args.update_files:
            updated_count = manager.update_response_files(results.get("auto_updatable", {}))
            print(f"Updated response files with {updated_count} new responses")
        
    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
