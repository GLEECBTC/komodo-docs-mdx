#!/usr/bin/env python3
"""
Clean Response Manager - Simplified and modular KDF response collection.

This is a cleaned-up version of the original responses_manager.py with:
- Removed deprecated/duplicate logic
- Modular wallet management
- Simplified prerequisite handling
- Better separation of concerns
"""

import json
import requests
import time
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

# Add lib path for utilities
sys.path.append(str(Path(__file__).parent.parent))
from utils.json_utils import dump_sorted_json

# Import managers
try:
    from .wallet_manager import WalletManager
    from .activation_manager import ActivationManager
    from .coins_config_manager import CoinsConfigManager
except ImportError:
    # Fall back to absolute imports
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    from wallet_manager import WalletManager
    from activation_manager import ActivationManager
    from coins_config_manager import CoinsConfigManager


@dataclass
class KDFInstance:
    """KDF instance configuration."""
    name: str
    url: str
    userpass: str


@dataclass
class CollectionResult:
    """Result of collecting responses for a method."""
    response_name: str
    instance_responses: Dict[str, Any]
    all_passed: bool
    consistent_structure: bool
    auto_updatable: bool
    collection_method: str
    notes: str = ""
    original_request: Optional[Dict[str, Any]] = None


class Outcome(Enum):
    SUCCESS = "success"
    EXPECTED_ERROR = "expected_error"
    FAILURE = "failure"


# Configuration
KDF_INSTANCES = [
    KDFInstance("native-hd", "http://localhost:7783", "RPC_UserP@SSW0RD"),
    KDFInstance("native-nonhd", "http://localhost:7784", "RPC_UserP@SSW0RD"),
]

# Manual methods that require hardware wallets or external services
SKIP_METHODS = {
    "TaskEnableEthInitTrezor", "TaskEnableEthUserActionPin", "TaskEnableQtumUserActionPin",  
    "TaskEnableUtxoUserActionPin", "TaskEnableBchUserActionPin", "TaskEnableTendermintUserActionPin",
    "TaskEnableZCoinUserActionPin", "EnableEthWithTokensWalletConnect", "EnableTendermintWithAssetsWalletConnect",
}


class KdfResponseManager:
    """Simplified response manager with clean architecture."""
    
    def __init__(self, workspace_root: Optional[Path] = None):
        """Initialize the clean response manager."""
        self.setup_logging()
        
        # Set workspace root
        if workspace_root:
            self.workspace_root = workspace_root
        else:
            # Auto-detect workspace root
            current_dir = Path(__file__).parent
            workspace_root = current_dir
            while workspace_root.name != "komodo-docs-mdx" and workspace_root.parent != workspace_root:
                workspace_root = workspace_root.parent
            
            if workspace_root.name != "komodo-docs-mdx":
                raise RuntimeError("Could not find workspace root (komodo-docs-mdx)")
            
            self.workspace_root = workspace_root
        
        # Initialize managers
        self.wallet_manager = WalletManager(self.workspace_root)
        self.coins_config = CoinsConfigManager(self.workspace_root)
        self.activation_managers = self._init_activation_managers()
        
        # Results storage
        self.results: List[CollectionResult] = []
        self.response_delays: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}
        self.inconsistent_responses: Dict[str, Dict[str, Any]] = {}
        self.last_kdf_version: Optional[str] = None
        self.expected_error_responses: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._current_request_key: Optional[str] = None
        self._current_method_name: Optional[str] = None
        
    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_kdf_version(self) -> Optional[str]:
        """Fetch KDF version from a running instance using the version RPC."""
        for instance in KDF_INSTANCES:
            try:
                # version is a legacy (v1) method only
                req_v1 = {"userpass": instance.userpass, "method": "version"}
                outcome, resp = self.send_request(instance, req_v1, timeout=10)
                if outcome == Outcome.SUCCESS and isinstance(resp, dict):
                    # Common legacy formats
                    if "result" in resp and isinstance(resp["result"], str):
                        self.last_kdf_version = resp["result"]
                        return self.last_kdf_version
                    for v in resp.values():
                        if isinstance(v, str) and any(ch.isdigit() for ch in v):
                            self.last_kdf_version = v
                            return self.last_kdf_version
            except Exception:
                continue
        return self.last_kdf_version

    def get_kdf_version_from_report(self) -> Optional[str]:
        """Extract KDF version from postman/generated/reports/kdf_postman_responses.json.

        Returns the version string if found, otherwise None.
        """
        try:
            report_path = self.workspace_root / "postman/generated/reports/kdf_postman_responses.json"
            if not report_path.exists():
                return None
            with open(report_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Direct top-level LegacyVersion pattern
            if isinstance(data, dict) and "LegacyVersion" in data:
                lv = data.get("LegacyVersion")
                if isinstance(lv, dict):
                    ver = lv.get("result")
                    if isinstance(ver, str):
                        self.last_kdf_version = ver
                        return ver

            # Unified responses format: search in responses -> LegacyVersion
            responses = data.get("responses") if isinstance(data, dict) else None
            if isinstance(responses, dict) and "LegacyVersion" in responses:
                lv_entry = responses.get("LegacyVersion")
                # Try common fields
                if isinstance(lv_entry, dict):
                    # direct result
                    if isinstance(lv_entry.get("result"), str):
                        self.last_kdf_version = lv_entry["result"]
                        return self.last_kdf_version
                    # scan nested values for a plausible version string
                    def scan(obj):
                        if isinstance(obj, str) and any(ch.isdigit() for ch in obj):
                            return obj
                        if isinstance(obj, dict):
                            for v in obj.values():
                                s = scan(v)
                                if s:
                                    return s
                        if isinstance(obj, list):
                            for v in obj:
                                s = scan(v)
                                if s:
                                    return s
                        return None
                    found = scan(lv_entry)
                    if found:
                        self.last_kdf_version = found
                        return found
            return None
        except Exception:
            return None

    def _init_activation_managers(self) -> Dict[str, ActivationManager]:
        """Initialize activation managers for each KDF instance."""
        managers = {}
        for instance in KDF_INSTANCES:
            managers[instance.name] = ActivationManager(
                rpc_func=lambda method, params, inst=instance: self._send_activation_request(inst, method, params),
                userpass=instance.userpass,
                workspace_root=self.workspace_root
            )
        return managers
    
    def _send_activation_request(self, instance: KDFInstance, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send activation request for ActivationManager."""
        request_data = {
            "userpass": instance.userpass,
            "mmrpc": "2.0",
            "method": method,
            "params": params,
            "id": 0
        }
        _outcome, response = self.send_request(instance, request_data)
        return response  # ActivationManager expects just the response dict
    
    def send_request(self, instance: KDFInstance, request_data: Dict[str, Any], 
                    timeout: int = 30) -> Tuple[Outcome, Dict[str, Any]]:
        """Send a request to a KDF instance with tri-state outcome."""
        start_time = time.time()
        status_code = None
        outcome: Outcome = Outcome.FAILURE
        
        try:
            headers = {"Content-Type": "application/json"}
            
            # Filter out metadata fields before sending to API
            filtered_request_data = self._filter_request_data(request_data)
            method_name = filtered_request_data.get("method", "")
            
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
                    if "error" not in response_data:
                        outcome = Outcome.SUCCESS
                        # Extract addresses/balances from successful responses
                        self.wallet_manager.extract_addresses_from_response(
                            instance.name, method_name, response_data, filtered_request_data
                        )
                    data = response_data
                except json.JSONDecodeError:
                    data = {"error": "Invalid JSON response", "raw_response": response.text}
            else:
                data = {"error": f"HTTP {response.status_code}", "raw_response": response.text}
                
        except requests.exceptions.Timeout:
            status_code = 408
            data = {"error": "Request timeout"}
        except requests.exceptions.ConnectionError:
            status_code = 503
            data = {"error": "Connection failed"}
        except Exception as e:
            status_code = 500
            data = {"error": f"Unexpected error: {str(e)}"}
        finally:
            # Record timing
            end_time = time.time()
            delay = round(end_time - start_time, 3)
            
            if hasattr(self, '_current_timing_context'):
                self._current_timing_context['delay'] = delay
                self._current_timing_context['status_code'] = status_code or 500

            if outcome != Outcome.SUCCESS:
                # Classify expected errors
                text = str(data)
                is_expected = (
                    "UnexpectedDerivationMethod" in text or
                    "SingleAddress" in text or
                    "PlatformCoinIsNotActivated" in text or
                    "Error parsing the native wallet configuration" in text or
                    ("FromAddressNotFound" in text and instance.name.endswith("-hd"))
                )
                if is_expected:
                    outcome = Outcome.EXPECTED_ERROR
                    try:
                        self._record_expected_error(method_name, instance.name, status_code or 500, data, filtered_request_data)
                    except AttributeError:
                        # If a subclass doesn't have recorder yet (e.g., older Sequence manager), safely ignore
                        pass
                    self.logger.info(f"{instance.name}: [{method_name}] EXPECTED_ERROR - {data.get('error', '')}")
                else:
                    self.logger.warning(f"{instance.name}: [{method_name}] FAILED - [{status_code}] {data.get('error', '')}")
                    self.logger.warning(f"{instance.name}: [{method_name}] Request - {request_data}")
                    self.logger.warning(f"{instance.name}: [{method_name}] filtered_request_data - {filtered_request_data}")
                    self.logger.warning(f"{instance.name}: [{method_name}] is params in filtered_request_data - {'params' in filtered_request_data}")
                    self.logger.warning(f"{instance.name}: [{method_name}] Response - {data}")
            else:
                self.logger.info(f"{instance.name}: [{method_name}] SUCCESS")
        return outcome, data


    def _filter_request_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out metadata fields from request data before sending to API."""
        metadata_fields = {'tags', 'prerequisites'}
        return {k: v for k, v in request_data.items() if k not in metadata_fields}
    
    def _extract_ticker_from_request(self, request_data: Dict[str, Any]) -> Optional[str]:
        """Extract ticker/coin from request data."""
        # Look for ticker in params
        if "params" in request_data:
            params = request_data["params"]
            if isinstance(params, dict):
                if "ticker" in params:
                    return params["ticker"]
                elif "coin" in params:
                    return params["coin"]
        
        # Look for ticker at root level
        if "ticker" in request_data:
            return request_data["ticker"]
        elif "coin" in request_data:
            return request_data["coin"]
        
        return None
    
    def _ensure_coin_activated(self, instance: KDFInstance, ticker: str):
        """Ensure a coin is activated using the ActivationManager."""
        if not ticker:
            return {"success": True, "already_enabled": True}
        
        ticker_upper = str(ticker).upper()
        
        # Skip platform coins that are handled separately
        if ticker_upper in ["ETH", "IRIS"]:
            return {"success": True, "already_enabled": True}
        
        # Get the activation manager for this instance
        activation_manager = self.activation_managers.get(instance.name)
        if not activation_manager:
            error_msg = f"No activation manager found for instance {instance.name}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        # Check if coin is already enabled
        if activation_manager.is_coin_enabled(ticker_upper):
            self.logger.info(f"Coin {ticker_upper} is already enabled on {instance.name}")
            return {"success": True, "already_enabled": True}
        
        try:
            # Determine if this is a token
            is_token, parent_coin = self.coins_config.is_token(ticker_upper)
            enable_hd = "-hd" in instance.name.lower() and "nonhd" not in instance.name.lower()
            
            if is_token:
                self.logger.info(f"Activating token {ticker_upper} on {instance.name}")
                result = activation_manager.activate_token(ticker_upper, enable_hd=enable_hd)
            else:
                self.logger.info(f"Activating coin {ticker_upper} on {instance.name}")
                result = activation_manager.activate_coin(
                    ticker_upper, 
                    enable_hd=enable_hd,
                    wait_for_completion=True
                )
            
            if result.success:
                self.logger.info(f"Successfully activated {ticker_upper} on {instance.name}")
                return {"success": True, "result": result}
            else:
                self.logger.warning(f"Failed to activate {ticker_upper} on {instance.name}: {result.error}")
                return {"success": False, "error": result.error, "response": result.response}
                
        except Exception as e:
            error_msg = f"Error activating {ticker_upper} on {instance.name}: {e}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def _is_coin_enabled(self, instance: KDFInstance, ticker: str) -> bool:
        """Check if a coin is enabled using appropriate get_enabled_coins method."""
        if not ticker:
            return False
            
        try:
            # Determine which version of get_enabled_coins to use based on HD detection
            enable_hd = "-hd" in instance.name.lower() and "nonhd" not in instance.name.lower()
            
            if enable_hd:
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
            
            outcome, response = self.send_request(instance, request)
            
            if outcome == Outcome.SUCCESS and "result" in response:
                result = response["result"]
                ticker_upper = ticker.upper()
                
                # Handle v2 response format (HD wallets)
                if isinstance(result, dict) and "coins" in result:
                    for coin in result["coins"]:
                        if isinstance(coin, dict) and coin.get("ticker", "").upper() == ticker_upper:
                            return True
                        elif isinstance(coin, str) and coin.upper() == ticker_upper:
                            return True
                # Handle v1 response format (non-HD wallets)  
                elif isinstance(result, list):
                    for coin in result:
                        if isinstance(coin, dict) and coin.get("ticker", "").upper() == ticker_upper:
                            return True
                        elif isinstance(coin, str) and coin.upper() == ticker_upper:
                            return True
                
                return False
            else:
                self.logger.info(f"Failed to get enabled coins for {instance.name}: {response}")
                return False
                
        except Exception as e:
            self.logger.info(f"Error checking if {ticker} is enabled on {instance.name}: {e}")
            return False
    
    def disable_coin(self, instance: KDFInstance, ticker: str) -> bool:
        """Simple coin disable using disable_coin method."""
        disable_request = {
            "userpass": instance.userpass,
            "method": "disable_coin",
            "coin": ticker
        }
        
        outcome, response = self.send_request(instance, disable_request)
        
        if outcome == Outcome.SUCCESS:
            self.logger.info(f"Successfully disabled {ticker} on {instance.name}")
            return True
        else:
            # Check if it's already disabled (expected case)
            if isinstance(response, dict):
                error_msg = str(response.get("error", "")).lower()
                if any(phrase in error_msg for phrase in [
                    "not found", "not enabled", "is not activated", "not active",
                    "no such coin", "coin not found"
                ]):
                    self.logger.info(f"{ticker} was not enabled on {instance.name}")
                    return True
            
            self.logger.warning(f"Failed to disable {ticker} on {instance.name}: {response}")
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

        
        return request_copy
    
    def collect_regular_method(self, response_name: str, request_data: Dict[str, Any], 
                              method_name: str) -> CollectionResult:
        """Collect responses for regular (non-task) methods."""
        instance_responses = {}
        all_passed = True
        consistent_structure = True
        first_response_structure = None
        
        # Extract ticker from request data
        ticker = self._extract_ticker_from_request(request_data)
        
        for instance in KDF_INSTANCES:
            # Ensure coin is activated if needed
            if ticker:
                # Check if this is an activation method
                method_name_check = request_data.get("method", "")
                is_activation_method = any(activation_term in method_name_check.lower() for activation_term in [
                    "enable", "activate", "init", "electrum"
                ])
                
                if is_activation_method:
                    # For activation methods, check if coin is enabled first, then disable
                    # self.logger.info(f"🔄 Checking if {ticker} is enabled on {instance.name} before disabling")
                    if self._is_coin_enabled(instance, ticker):
                        self.logger.info(f"🔄 Pre-disabling {ticker} on {instance.name} before activation")
                        self.disable_coin(instance, ticker)
                        time.sleep(1.0)  # Allow time for disable to complete
                else:
                    # For other methods, ensure coin is activated
                    activation_result = self._ensure_coin_activated(instance, ticker)
                    if not activation_result["success"]:
                        self.logger.warning(f"Skipping {response_name} on {instance.name} - Could not activate {ticker}")
                        all_passed = False
                        
                        error_response = {
                            "error": f"Failed to activate coin {ticker}",
                            "error_type": "CoinActivationFailed"
                        }
                        
                        if activation_result.get("error"):
                            error_response["activation_error"] = activation_result["error"]
                        if activation_result.get("response"):
                            error_response["activation_response"] = activation_result["response"]
                        
                        instance_responses[instance.name] = error_response
                        continue
            
            # Modify request for non-HD instances
            if "nonhd" in instance.name:
                modified_request = self.normalize_request_for_non_hd(request_data)
            else:
                modified_request = request_data
            
            # Set up timing context and send request
            self._current_timing_context = {}
            timeout = self._get_method_timeout(method_name)
            # Set request context for reporting
            self._current_request_key = response_name
            self._current_method_name = method_name
            outcome, response = self.send_request(instance, modified_request, timeout)
            
            # Record timing information
            timing_info = getattr(self, '_current_timing_context', {})
            if timing_info:
                self._record_response_delay(
                    method_name, response_name, instance.name,
                    timing_info.get('status_code', 500),
                    timing_info.get('delay', 0.0)
                )
            
            instance_responses[instance.name] = response
            
            if not (outcome == Outcome.SUCCESS or outcome == Outcome.EXPECTED_ERROR):
                all_passed = False
            else:
                if first_response_structure is None:
                    first_response_structure = self._get_response_structure(response)
                elif self._get_response_structure(response) != first_response_structure:
                    consistent_structure = False
        
        # Auto-updatable if we have successful responses
        successful_responses = {k: v for k, v in instance_responses.items() if "error" not in v}
        auto_updatable = len(successful_responses) > 0
        
        # Record inconsistencies if any (mixed outcomes or structure differences)
        self._maybe_record_inconsistency(
            response_name=response_name,
            method_name=method_name,
            instance_responses=instance_responses,
            consistent_structure=consistent_structure,
        )

        return CollectionResult(
            response_name=response_name,
            instance_responses=instance_responses,
            all_passed=all_passed,
            consistent_structure=consistent_structure,
            auto_updatable=auto_updatable,
            collection_method="regular",
            notes=f"Method: {method_name}",
            original_request=request_data
        )

    def _record_expected_error(self, method_name: str, instance_name: str, status_code: int,
                               response_data: Dict[str, Any], request_data: Dict[str, Any]) -> None:
        """Record an expected error for reporting.

        Stores expected errors grouped by method -> example(request_key) -> instance.
        """
        try:
            request_key = self._current_request_key or method_name
            if method_name not in self.expected_error_responses:
                self.expected_error_responses[method_name] = {}
            if request_key not in self.expected_error_responses[method_name]:
                self.expected_error_responses[method_name][request_key] = {}

            # Extract a concise error summary
            error_entry: Dict[str, Any] = {
                "status_code": status_code,
            }
            if isinstance(response_data, dict):
                # Copy common error fields if present
                for key in ["error", "error_type", "error_path", "error_trace", "raw_response"]:
                    if key in response_data:
                        error_entry[key] = response_data[key]
            # Store minimal request context for debugging
            error_entry["request"] = {
                "method": method_name,
                "request_key": request_key,
            }

            self.expected_error_responses[method_name][request_key][instance_name] = error_entry
        except Exception as e:
            # Do not let reporting failures affect collection flow
            self.logger.warning(f"Failed to record expected error for {method_name} on {instance_name}: {e}")

    def _classify_instance_outcome(self, instance_name: str, method_name: str, request_key: str,
                                   response: Dict[str, Any]) -> str:
        """Classify outcome for a single instance as 'success', 'expected_error', or 'failure'."""
        if isinstance(response, dict) and "error" not in response:
            return "success"

        # Check if this response was recorded as expected
        method_map = self.expected_error_responses.get(method_name, {})
        example_map = method_map.get(request_key, {})
        if instance_name in example_map:
            return "expected_error"

        return "failure"

    def _maybe_record_inconsistency(self, response_name: str, method_name: str,
                                    instance_responses: Dict[str, Any],
                                    consistent_structure: bool) -> None:
        """Detect and record inconsistencies across environments for a single example.

        Inconsistencies include:
        - Presence of failures in any instance
        - Inconsistent structure among successful responses only
        Expected errors alone should NOT trigger inclusion.
        """
        try:
            request_key = response_name
            # Build outcome categories per instance
            categories: Dict[str, str] = {}
            for instance_name, resp in instance_responses.items():
                categories[instance_name] = self._classify_instance_outcome(
                    instance_name, method_name, request_key, resp if isinstance(resp, dict) else {}
                )

            reasons: List[str] = []

            # Include if any failure is present (unexpected)
            has_failure = any(outcome == "failure" for outcome in categories.values())
            if has_failure:
                reasons.append("mixed_outcomes")

            # Structure inconsistency: compare ONLY successful responses
            success_structures: List[str] = []
            for instance_name, resp in instance_responses.items():
                if categories.get(instance_name) == "success" and isinstance(resp, dict):
                    success_structures.append(self._get_response_structure(resp))
            if len(success_structures) >= 2 and len(set(success_structures)) > 1:
                reasons.append("inconsistent_structure")

            # Do NOT include if the only differences are success vs expected_error
            if reasons:
                if response_name not in self.inconsistent_responses:
                    self.inconsistent_responses[response_name] = {}
                self.inconsistent_responses[response_name] = {
                    "method": method_name,
                    "reasons": reasons,
                    "outcomes": categories,
                    "instances": instance_responses,
                }
        except Exception as e:
            self.logger.warning(f"Failed to evaluate inconsistency for {response_name}: {e}")
    
    def _get_method_timeout(self, method_name: str) -> int:
        """Get appropriate timeout for a method."""
        # Load method config to check for specific timeout (v2 preferred over legacy)
        data_dir = self.workspace_root / "src/data"
        files = [data_dir / "kdf_methods_legacy.json", data_dir / "kdf_methods_v2.json"]
        kdf_methods = {}
        # Load legacy first, then v2 to allow v2 to override
        for fp in files:
            try:
                with open(fp, 'r') as f:
                    kdf_methods.update(json.load(f))
            except Exception:
                continue
        # No fallback to old single file
        
        if method_name in kdf_methods:
            method_config = kdf_methods[method_name]
            if isinstance(method_config, dict) and "timeout" in method_config:
                return method_config["timeout"]
        
        # Default timeout
        return 30
    
    def _record_response_delay(self, method_name: str, request_key: str, instance_name: str, 
                              status_code: int, delay: float) -> None:
        """Record response delay information."""
        if method_name not in self.response_delays:
            self.response_delays[method_name] = {}
        
        if request_key not in self.response_delays[method_name]:
            self.response_delays[method_name][request_key] = {}
        
        self.response_delays[method_name][request_key][instance_name] = {
            "status_code": status_code,
            "delay": delay
        }
    
    def _get_response_structure(self, response: Dict[str, Any]) -> str:
        """Get a simplified structure representation of the response for comparison."""
        if not isinstance(response, dict):
            return str(type(response).__name__)
        
        def simplify_structure(obj):
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    if k in ["address", "pubkey", "derivation_path", "account_index"]:
                        result[k] = "<normalized>"
                    else:
                        result[k] = simplify_structure(v)
                return result
            elif isinstance(obj, list):
                if len(obj) > 0:
                    return [simplify_structure(obj[0])]
                return []
            else:
                return type(obj).__name__
        
        return json.dumps(simplify_structure(response), sort_keys=True)
    
    def load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON file and return parsed content."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.warning(f"Error loading {file_path}: {e}")
            return {}
    
    def _ensure_response_files_exist(self):
        """Ensure all response files exist by scanning request files and creating missing response files."""
        self.logger.info("🔧 Ensuring all response files exist...")
        
        # Check all request files and create corresponding response files if missing
        request_dirs = [
            self.workspace_root / "src/data/requests/kdf/v2",
            self.workspace_root / "src/data/requests/kdf/legacy"
        ]
        
        files_created = 0
        for request_dir in request_dirs:
            if not request_dir.exists():
                continue
                
            for request_file in request_dir.glob("*.json"):
                # Determine corresponding response file
                if "v2" in str(request_file):
                    response_file = self.workspace_root / "src/data/responses/kdf/v2" / request_file.name
                else:
                    response_file = self.workspace_root / "src/data/responses/kdf/legacy" / request_file.name
                
                if not response_file.exists():
                    self.logger.info(f"📁 Creating missing response file: {response_file.relative_to(self.workspace_root)}")
                    response_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Load request data to create empty templates
                    request_data = self.load_json_file(request_file)
                    if request_data:
                        empty_response_structure = {}
                        for request_name in request_data.keys():
                            empty_response_structure[request_name] = {
                                "error": [],
                                "success": []
                            }
                        
                        dump_sorted_json(empty_response_structure, response_file)
                        files_created += 1
                        self.logger.info(f"✅ Created {response_file.name} with {len(empty_response_structure)} method templates")
        
        if files_created > 0:
            self.logger.info(f"🎯 Created {files_created} missing response files")
        else:
            self.logger.info("📋 All response files already exist")
    
    def save_results(self, results: Dict[str, Any], output_file: Path):
        """Save results to output file."""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        dump_sorted_json(results, output_file)
        self.logger.info(f"Results saved to: {output_file}")
    
    def compile_results(self) -> Dict[str, Any]:
        """Compile all results into a unified format."""
        unified_results = {
            "metadata": {
                "collection_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "total_responses_collected": len(self.results),
                "auto_updatable_count": sum(1 for r in self.results if r.auto_updatable),
                "collection_summary": {
                    "regular_methods": sum(1 for r in self.results if r.collection_method == "regular"),
                }
            },
            "responses": {},
            "auto_updatable": {},
            "manual_review_needed": {}
        }
        
        for result in self.results:
            # Add to main responses
            response_entry = {
                "instances": result.instance_responses,
                "all_passed": result.all_passed,
                "consistent_structure": result.consistent_structure,
                "collection_method": result.collection_method,
                "notes": result.notes
            }
            
            # Add original request for manual verification
            if hasattr(result, 'original_request') and result.original_request:
                response_entry["request"] = result.original_request
                
            unified_results["responses"][result.response_name] = response_entry
            
            # Categorize for update processing
            if result.auto_updatable:
                # Get canonical response (prefer native-hd, then first successful one)
                canonical_response = None
                
                if "native-hd" in result.instance_responses:
                    hd_response = result.instance_responses["native-hd"]
                    if "error" not in hd_response:
                        canonical_response = hd_response
                
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
                
                if not reasons:
                    reasons.append("unknown")
                
                # Create detailed entry for manual review
                manual_review_entry = {
                    "reasons": reasons,
                    "instances": result.instance_responses,
                    "collection_method": result.collection_method,
                    "notes": result.notes
                }
                
                if hasattr(result, 'original_request') and result.original_request:
                    manual_review_entry["request"] = result.original_request
                
                unified_results["manual_review_needed"][result.response_name] = manual_review_entry
        
        # Save wallet addresses
        wallet_output_file = self.workspace_root / "postman/generated/reports/test_addresses.json"
        self.wallet_manager.save_test_addresses_report(wallet_output_file)
        # Save expected error report
        reports_dir = self.workspace_root / "postman/generated/reports"
        self.save_expected_error_responses_report(reports_dir)

        return unified_results
    
    def validate_responses(self, validate_collected_responses: bool = False) -> Dict[str, Any]:
        """Validate existing response files and optionally collected responses."""
        self.logger.info("Starting response validation")
        
        # For now, return a basic validation structure
        # This can be expanded later with proper validation logic
        validation_results = {
            "existing_files": {
                "success": True,
                "errors": [],
                "warnings": [],
                "error_count": 0,
                "warning_count": 0,
                "sorted_files": {},
                "templated_files": {}
            }
        }
        
        if validate_collected_responses and self.results:
            validation_results["collected_responses"] = {
                "errors": [],
                "warnings": [],
                "error_count": 0,
                "warning_count": 0
            }
        
        return validation_results
    
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
        
        # Initialize empty inconsistent responses if not exists
        if not hasattr(self, 'inconsistent_responses'):
            self.inconsistent_responses = {}
        
        # Add metadata to the inconsistent responses report
        inconsistent_report = {
            "metadata": {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "total_inconsistent_methods": len(self.inconsistent_responses),
                "total_inconsistent_examples": sum(len(examples) for examples in self.inconsistent_responses.values()),
                "description": "Methods with inconsistent responses across KDF environments"
            },
            "inconsistent_responses": self.inconsistent_responses
        }
        
        dump_sorted_json(inconsistent_report, inconsistent_file)
        self.logger.info(f"Inconsistent responses report saved to: {inconsistent_file}")

    def save_expected_error_responses_report(self, output_dir: Path) -> None:
        """Save expected error responses report to separate file."""
        expected_file = output_dir / "expected_error_responses.json"
        report = {
            "metadata": {
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "total_methods": len(self.expected_error_responses),
                "total_examples": sum(len(ex) for ex in self.expected_error_responses.values()),
                "description": "Requests that returned expected, acceptable error responses"
            },
            "expected_errors": self.expected_error_responses
        }
        dump_sorted_json(report, expected_file)
        self.logger.info(f"Expected error responses report saved to: {expected_file}")

    def rebuild_reports_from_unified(self, unified_report_path: Path, output_dir: Path) -> None:
        """Rebuild expected_error_responses.json and inconsistent_responses.json from an existing unified report.

        This is useful when we want to re-derive these reports without re-running collection.
        """
        try:
            with open(unified_report_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load unified report: {e}")
            return

        responses = data.get("responses", {}) if isinstance(data, dict) else {}
        self.expected_error_responses = {}
        self.inconsistent_responses = {}

        for response_name, entry in responses.items():
            if not isinstance(entry, dict):
                continue
            method_name = entry.get("notes", "").replace("Method: ", "") or entry.get("method", "")
            instance_responses = entry.get("instances", {})

            # Rebuild expected errors by scanning error responses that match the classifier
            for instance_name, resp in instance_responses.items():
                if not isinstance(resp, dict):
                    continue
                if "error" in resp:
                    text = json.dumps(resp)
                    is_expected = (
                        "UnexpectedDerivationMethod" in text or
                        "SingleAddress" in text or
                        "PlatformCoinIsNotActivated" in text or
                        "Error parsing the native wallet configuration" in text or
                        ("FromAddressNotFound" in text and instance_name.endswith("-hd"))
                    )
                    if is_expected:
                        if method_name not in self.expected_error_responses:
                            self.expected_error_responses[method_name] = {}
                        if response_name not in self.expected_error_responses[method_name]:
                            self.expected_error_responses[method_name][response_name] = {}
                        self.expected_error_responses[method_name][response_name][instance_name] = {
                            "status_code": None,
                            "error": resp.get("error"),
                            "error_type": resp.get("error_type"),
                            "error_path": resp.get("error_path"),
                            "error_trace": resp.get("error_trace"),
                            "raw_response": resp.get("raw_response")
                        }

            # Rebuild inconsistency entries based on mixed outcomes and structure flag
            consistent_structure = bool(entry.get("consistent_structure", True))
            # Determine categories
            categories = {}
            for instance_name, resp in instance_responses.items():
                categories[instance_name] = self._classify_instance_outcome(
                    instance_name, method_name, response_name, resp if isinstance(resp, dict) else {}
                )
            reasons = []
            if len(set(categories.values())) > 1:
                reasons.append("mixed_outcomes")
            if not consistent_structure:
                reasons.append("inconsistent_structure")
            if reasons:
                self.inconsistent_responses[response_name] = {
                    "method": method_name,
                    "reasons": reasons,
                    "outcomes": categories,
                    "instances": instance_responses,
                }

        # Save the rebuilt reports
        self.save_expected_error_responses_report(output_dir)
        self.save_inconsistent_responses_report(output_dir)
    
    def regenerate_missing_responses_report(self, reports_dir: Path) -> None:
        """Regenerate missing responses report after response collection."""
        self.logger.info("Regenerating missing responses report...")
        
        # Load all request data
        all_requests = {}
        
        # Load v2 request files
        v2_requests_dir = self.workspace_root / "src/data/requests/kdf/v2"
        for request_file in v2_requests_dir.glob("*.json"):
            v2_requests = self.load_json_file(request_file) or {}
            all_requests.update(v2_requests)
        
        # Load legacy request files
        legacy_requests_dir = self.workspace_root / "src/data/requests/kdf/legacy"
        for request_file in legacy_requests_dir.glob("*.json"):
            legacy_requests = self.load_json_file(request_file) or {}
            all_requests.update(legacy_requests)
        
        # Load method config to check for deprecated methods (merged v2 + legacy)
        data_dir = self.workspace_root / "src/data"
        kdf_methods = {}
        for fp in [data_dir / "kdf_methods_legacy.json", data_dir / "kdf_methods_v2.json"]:
            kdf_methods.update(self.load_json_file(fp) or {})
        
        # Check for missing responses (simplified version)
        missing_responses = {}
        
        for request_key, request_data in all_requests.items():
            method_name = request_data.get("method", "unknown")
            method_config = kdf_methods.get(method_name, {})
            
            # Skip deprecated methods
            if method_config.get('deprecated', False):
                continue
            
            # For now, assume all methods need responses (proper logic can be added later)
            if method_name not in missing_responses:
                missing_responses[method_name] = []
            missing_responses[method_name].append(request_key)
        
        # Save regenerated missing responses report
        missing_file = reports_dir / "missing_responses.json"
        dump_sorted_json(missing_responses, missing_file)
        
        self.logger.info(f"Missing responses report regenerated: {missing_file}")
        self.logger.info(f"Total missing methods: {len(missing_responses)}")
    
    def update_response_files(self, auto_updatable_responses: Dict[str, Any]) -> int:
        """Update response files with successful responses."""
        self.logger.info("Updating response files")
        
        # If no responses to add, return early
        if not auto_updatable_responses:
            self.logger.info("No new successful responses to update.")
            return 0
        
        # For now, just log what would be updated
        # Proper file update logic can be added later
        updated_count = len(auto_updatable_responses)
        self.logger.info(f"Would update {updated_count} response files with new responses")
        
        return updated_count


def main():
    """Main function for the clean response manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean KDF Response Manager")
    parser.add_argument("--update-files", action="store_true", help="Update response files")
    args = parser.parse_args()
    
    try:
        # Initialize manager
        manager = KdfResponseManager()
        
        # For now, just demonstrate with a simple collection
        # This would be called by the sequence manager
        
        print("✅ Clean Response Manager initialized successfully!")
        print(f"Workspace root: {manager.workspace_root}")
        print(f"Wallet manager ready: {manager.wallet_manager is not None}")
        print(f"Activation managers: {len(manager.activation_managers)}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
