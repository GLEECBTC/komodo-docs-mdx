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
class TaskInstance:
    """KDF task methods instance."""
    task_name: str
    init_request: Dict[str, Any]
    task_id: Optional[int] = None
    init_response: Optional[Dict[str, Any]] = None
    status_request: Optional[Dict[str, Any]] = None
    status_responses: Optional[List[Dict[str, Any]]] = None
    user_action_request: Optional[Dict[str, Any]]
    user_action_responses: Optional[Dict[str, Any]] = None
    status_request: Optional[Dict[str, Any]] = None
    status_responses: Optional[List[Dict[str, Any]]] = None
    user_action_request: Optional[Dict[str, Any]] = None
    user_action_responses: Optional[Dict[str, Any]] = None
    cancel_request: Optional[Dict[str, Any]] = None
    cancel_response: Optional[Dict[str, Any]] = None


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
        # Test data (addresses → known txids) for env-specific overrides
        self.test_data: Optional[Dict[str, Any]] = None
        
        # Task tracking: registry and report path
        self.task_registry: Dict[str, TaskInstance] = {}
        self.task_report_path: Path = self.workspace_root / "postman/generated/reports/method_tasks.json"
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
                workspace_root=self.workspace_root,
                instance_name=instance.name
            )
        return managers
    
    def _send_activation_request(self, instance: KDFInstance, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send activation request for ActivationManager.

        Uses v2 (mmrpc 2.0) for task:: methods; for legacy methods like 'electrum'/'enable',
        send v1-style payload by merging params at root.
        """
        # Determine if this is a v2 task method
        is_v2 = isinstance(method, str) and ("task::" in method or method.startswith("enable_"))
        if is_v2:
            request_data = {
                "userpass": instance.userpass,
                "mmrpc": "2.0",
                "method": method,
                "params": params,
                "id": 0
            }
        else:
            # Legacy v1 activation call: merge params into root
            request_data = {"userpass": instance.userpass, "method": method}
            # Merge only dict params at root level
            if isinstance(params, dict):
                request_data.update(params)
        _outcome, response = self.send_request(instance, request_data)
        return response  # ActivationManager expects just the response dict
    
    def send_request(self, instance: KDFInstance, request_data: Dict[str, Any], 
                    timeout: int = 30, allow_retry: bool = True) -> Tuple[Outcome, Dict[str, Any]]:
        """Send a request to a KDF instance with tri-state outcome."""
        start_time = time.time()
        status_code = None
        outcome: Outcome = Outcome.FAILURE
        
        try:
            headers = {"Content-Type": "application/json"}
            
            # Filter out metadata fields before sending to API
            filtered_request_data = self._filter_request_data(request_data)
            rpc_version = filtered_request_data.get("mmrpc", "1.0")
            method_name = filtered_request_data.get("method", "")
            # Ensure task status doesn't clear completed tasks
            try:
                if isinstance(method_name, str) and method_name.endswith("::status"):
                    params = filtered_request_data.setdefault("params", {})
                    if isinstance(params, dict) and "forget_if_finished" not in params:
                        params["forget_if_finished"] = False
            except Exception:
                pass
            
            # Pre-flight: ensure tasks exist for ::status/::cancel and override task_id from registry
            try:
                if isinstance(method_name, str) and method_name.endswith("::status"):
                    filtered_request_data = self._ensure_task_for_status(instance, filtered_request_data, timeout)
                    # Re-evaluate method_name in case of mutation
                    method_name = filtered_request_data.get("method", method_name)
            except Exception as e:
                self.logger.warning(f"Status preflight failed for {method_name} on {instance.name}: {e}")

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
                    # Task tracking: register/update task lifecycle on success
                    try:
                        self._maybe_track_task_success(instance, filtered_request_data, response_data)
                    except Exception:
                        pass
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
                # Prefer raw body for matching; fallback to stringified dict
                raw_body = data.get("raw_response") if isinstance(data, dict) else None
                text = raw_body if isinstance(raw_body, str) and raw_body else str(data)
                
                # Attach address hint when coin context is known
                try:
                    ticker_for_request = self._extract_ticker_from_request(filtered_request_data)
                    ticker_upper = str(ticker_for_request).upper() if ticker_for_request else None
                    if ticker_upper:
                        addr_hint = self.wallet_manager.get_address_hint(instance.name, ticker_upper)
                        if addr_hint:
                            data["address_hint"] = {"coin": ticker_upper, "address": addr_hint}
                except Exception:
                    pass

                # Auto-activation + retry wiring
                try:
                    # Extract ticker from original request
                    ticker_for_request = self._extract_ticker_from_request(filtered_request_data)
                    ticker_upper = str(ticker_for_request).upper() if ticker_for_request else None

                    # Helper to try activation then retry once
                    def _retry_after_activation(activate_ticker: Optional[str], *, force_platform: bool = False, force_reenable: bool = False) -> Tuple[Outcome, Dict[str, Any]]:
                        if not activate_ticker:
                            return outcome, data
                        act_result = self._ensure_coin_activated(
                            instance, activate_ticker,
                            force_enable_platform=force_platform,
                            force_reenable=force_reenable
                        )
                        if act_result.get("success"):
                            time.sleep(0.5)
                            return self.send_request(instance, request_data, timeout, allow_retry=False)
                        return Outcome.FAILURE, {"error": f"Activation failed for {activate_ticker}", "activation_error": act_result.get("error"), "activation_response": act_result.get("response")}

                    # Parent platform not activated: activate parent and retry
                    if allow_retry and "PlatformCoinIsNotActivated" in text:
                        parent_coin = None
                        if ticker_upper:
                            is_token, parent = self.coins_config.is_token(ticker_upper)
                            parent_coin = parent if is_token else None
                        if not parent_coin and isinstance(raw_body, str):
                            try:
                                body_json = json.loads(raw_body)
                                parent_coin = str(body_json.get("error_data") or body_json.get("error", {}).get("error_data")).upper()
                            except Exception:
                                parent_coin = None
                        if parent_coin:
                            outcome, data = _retry_after_activation(parent_coin, force_platform=True)
                            raw_body = data.get("raw_response") if isinstance(data, dict) else None
                            text = raw_body if isinstance(raw_body, str) and raw_body else str(data)

                    # NoSuchCoin for a known coin: activate coin and retry
                    if allow_retry and "NoSuchCoin" in text and ticker_upper and self.coins_config.get_coin_config(ticker_upper):
                        # Re-enable if already enabled but server reports 404
                        outcome, data = _retry_after_activation(ticker_upper, force_reenable=True)
                        raw_body = data.get("raw_response") if isinstance(data, dict) else None
                        text = raw_body if isinstance(raw_body, str) and raw_body else str(data)

                    # Handle cancel flows missing task id: run init -> sleep -> cancel
                    if allow_retry and "NoSuchTask" in text and isinstance(method_name, str) and method_name.endswith("::cancel"):
                        try:
                            init_method = method_name.replace("::cancel", "::init")
                            # Try to find example params for the init method
                            init_params = self._find_example_params_for_method(init_method) or {}
                            # If we can determine the ticker, disable it first to ensure a fresh task
                            ticker_for_init = None
                            if isinstance(init_params, dict):
                                ticker_for_init = init_params.get("ticker") or init_params.get("coin")
                                if isinstance(ticker_for_init, str) and ticker_for_init:
                                    try:
                                        self.disable_coin(instance, str(ticker_for_init).upper())
                                        time.sleep(0.5)
                                    except Exception:
                                        pass
                            # Proactively ensure coin is disabled before running ::init
                            if isinstance(ticker_for_init, str) and ticker_for_init:
                                try:
                                    ticker_upper_for_init = str(ticker_for_init).upper()
                                    # Attempt disable if enabled (up to 2 tries with short waits)
                                    for _ in range(2):
                                        if self._is_coin_enabled(instance, ticker_upper_for_init):
                                            self.disable_coin(instance, ticker_upper_for_init)
                                            time.sleep(0.5)
                                        else:
                                            break
                                except Exception:
                                    pass

                            init_request = {
                                "userpass": instance.userpass,
                                "mmrpc": "2.0",
                                "method": init_method,
                                "params": init_params,
                                "id": 0
                            }
                            # Fire init to get a fresh task id
                            init_outcome, init_resp = self.send_request(instance, init_request, timeout, allow_retry=False)
                            task_id = None
                            if isinstance(init_resp, dict):
                                result = init_resp.get("result")
                                if isinstance(result, dict):
                                    task_id = result.get("task_id")
                            if task_id is not None:
                                time.sleep(0.5)
                                cancel_request = {
                                    "userpass": instance.userpass,
                                    "mmrpc": "2.0",
                                    "method": method_name,
                                    "params": {"task_id": task_id},
                                    "id": 0
                                }
                                outcome, data = self.send_request(instance, cancel_request, timeout, allow_retry=False)
                                raw_body = data.get("raw_response") if isinstance(data, dict) else None
                                text = raw_body if isinstance(raw_body, str) and raw_body else str(data)
                        except Exception as e:
                            self.logger.warning(f"Cancel retry wiring failed for {method_name} on {instance.name}: {e}")
                except Exception as e:
                    self.logger.warning(f"Retry wiring failed for {method_name} on {instance.name}: {e}")

                expected_error = self._is_expected_error(text, instance, method_name)
                if expected_error:
                    outcome = Outcome.EXPECTED_ERROR
                    try:
                        self._record_expected_error(method_name, instance.name, status_code or 500, data, filtered_request_data)
                    except AttributeError:
                        # If a subclass doesn't have recorder yet (e.g., older Sequence manager), safely ignore
                        pass
                    self.logger.info(f"{instance.name}: [{method_name} {rpc_version}] EXPECTED_ERROR - [{data.get('error', '')}] {expected_error}")
                else:
                    self.logger.warning(f"{instance.name}: [{method_name} {rpc_version}] FAILED - [{status_code}] {data.get('error', '')}")
                    self.logger.warning(f"{instance.name}: [{method_name} {rpc_version}] Request - {request_data}")
                    self.logger.warning(f"{instance.name}: [{method_name} {rpc_version}] filtered_request_data - {filtered_request_data}")
                    self.logger.warning(f"{instance.name}: [{method_name} {rpc_version}] is params in filtered_request_data - {'params' in filtered_request_data}")
                    self.logger.warning(f"{instance.name}: [{method_name} {rpc_version}] Response - {data}")
            elif method_name != "get_enabled_coins":
                self.logger.info(f"{instance.name}: [{method_name} {rpc_version}] SUCCESS")
        return outcome, data

    # ----- Task tracking helpers -----
    def _base_task_name(self, method_name: str) -> str:
        try:
            if not isinstance(method_name, str):
                return ""
            if method_name.startswith("task::"):
                parts = method_name.split("::")
                if len(parts) >= 2:
                    return "::".join(parts[:2])
            return method_name
        except Exception:
            return ""

    def _make_task_key(self, instance_name: str, base_task_name: str, task_id: Any) -> str:
        return f"{instance_name}:{base_task_name}:{task_id}"

    def _find_active_task_for_base(self, instance_name: str, base_task_name: str) -> Optional[TaskInstance]:
        for key, ti in getattr(self, "task_registry", {}).items():
            try:
                if not isinstance(ti, TaskInstance):
                    continue
                if key.startswith(f"{instance_name}:{base_task_name}:"):
                    if not getattr(ti, "completed", False):
                        return ti
            except Exception:
                continue
        return None

    def _maybe_track_task_success(self, instance: KDFInstance, request: Dict[str, Any], response: Dict[str, Any]) -> None:
        try:
            method_name = request.get("method", "")
            if not isinstance(method_name, str):
                return
            # Register new task on ::init
            if method_name.endswith("::init"):
                result = response.get("result") if isinstance(response, dict) else None
                task_id = result.get("task_id") if isinstance(result, dict) else None
                if task_id is not None:
                    base_name = self._base_task_name(method_name)
                    key = self._make_task_key(instance.name, base_name, task_id)
                    ti = TaskInstance(task_name=base_name, init_request=request, task_id=task_id, init_response=response)
                    setattr(ti, "created_at", time.time())
                    setattr(ti, "completed", False)
                    if not hasattr(self, "task_registry"):
                        self.task_registry = {}
                    self.task_registry[key] = ti
            # Update task on ::status
            elif method_name.endswith("::status"):
                params = request.get("params", {}) if isinstance(request, dict) else {}
                task_id = params.get("task_id") if isinstance(params, dict) else None
                if task_id is not None:
                    base_name = self._base_task_name(method_name)
                    key = self._make_task_key(instance.name, base_name, task_id)
                    ti = getattr(self, "task_registry", {}).get(key)
                    if ti:
                        if getattr(ti, "status_responses", None) is None:
                            ti.status_responses = []
                        try:
                            ti.status_responses.append(response)
                        except Exception:
                            pass
                        result = response.get("result") if isinstance(response, dict) else None
                        status_val = result.get("status") if isinstance(result, dict) else None
                        if status_val == "Ok":
                            setattr(ti, "completed", True)
                            setattr(ti, "completed_at", time.time())
            # Update task on ::cancel
            elif method_name.endswith("::cancel"):
                params = request.get("params", {}) if isinstance(request, dict) else {}
                task_id = params.get("task_id") if isinstance(params, dict) else None
                if task_id is not None:
                    base_name = self._base_task_name(method_name)
                    key = self._make_task_key(instance.name, base_name, task_id)
                    ti = getattr(self, "task_registry", {}).get(key)
                    if ti:
                        ti.cancel_request = request
                        ti.cancel_response = response
        except Exception:
            pass

    def _ensure_task_for_status(self, instance: KDFInstance, request: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """Ensure there is a valid task before querying ::status.
        - If task_id missing or unknown, try to start one via matching ::init using example params.
        - Wait 0.3s after init before returning.
        - Override request.params.task_id with a known active id if found.
        """
        if not isinstance(request, dict):
            return request
        method_name = request.get("method", "")
        if not (isinstance(method_name, str) and method_name.endswith("::status")):
            return request
        params = request.setdefault("params", {}) if isinstance(request, dict) else {}
        task_id = params.get("task_id") if isinstance(params, dict) else None
        base_name = self._base_task_name(method_name)
        chosen = self._find_active_task_for_base(instance.name, base_name)
        # Use task from registry if available
        if chosen and isinstance(params, dict):
            params["task_id"] = chosen.task_id
            created_at = getattr(chosen, "created_at", None)
            if isinstance(created_at, (int, float)):
                elapsed = time.time() - created_at
                if elapsed < 0.3:
                    time.sleep(round(0.3 - elapsed, 3))
            return request
        # Otherwise, attempt to start a fresh task via ::init (based on examples)
        init_method = method_name.replace("::status", "::init")
        init_params = self._find_example_params_for_method(init_method) or {}
        # Best-effort: disable coin ahead of init if we can find ticker
        try:
            ticker_for_init = None
            if isinstance(init_params, dict):
                ticker_for_init = init_params.get("ticker") or init_params.get("coin")
            if isinstance(ticker_for_init, str) and ticker_for_init:
                ticker_upper = str(ticker_for_init).upper()
                for _ in range(2):
                    if self._is_coin_enabled(instance, ticker_upper):
                        self.disable_coin(instance, ticker_upper)
                        time.sleep(0.5)
                    else:
                        break
        except Exception:
            pass
        init_request = {
            "userpass": instance.userpass,
            "mmrpc": "2.0",
            "method": init_method,
            "params": init_params,
            "id": 0
        }
        _outcome, init_resp = self.send_request(instance, init_request, timeout, allow_retry=False)
        new_task_id = None
        if isinstance(init_resp, dict):
            result = init_resp.get("result")
            if isinstance(result, dict):
                new_task_id = result.get("task_id")
        if new_task_id is not None and isinstance(params, dict):
            time.sleep(0.3)
            params["task_id"] = new_task_id
        return request

    def _find_example_params_for_method(self, method_name: str) -> Optional[Dict[str, Any]]:
        """Find example params for a given method by scanning request definition files."""
        try:
            # Prefer v2 requests
            v2_requests_dir = self.workspace_root / "src/data/requests/kdf/v2"
            legacy_requests_dir = self.workspace_root / "src/data/requests/kdf/legacy"
            for req_dir in [v2_requests_dir, legacy_requests_dir]:
                if not req_dir.exists():
                    continue
                for request_file in req_dir.glob("*.json"):
                    try:
                        requests_data = self.load_json_file(request_file) or {}
                        if isinstance(requests_data, dict):
                            for _key, req in requests_data.items():
                                if not isinstance(req, dict):
                                    continue
                                if req.get("method") == method_name:
                                    params = req.get("params")
                                    return params if isinstance(params, dict) else {}
                    except Exception:
                        continue
        except Exception:
            return None
        return None

    def _is_expected_error(self, text: str, instance: KDFInstance, method_name: str) -> bool:
        """Check if the response is an expected error."""
        expected_error = None
        if instance.name.endswith("-nonhd"):
            if "not supported if the coin is initialized with an Iguana private key" in text:
                return "Iguana not supported"

        elif instance.name.endswith("-hd"):
            # TODO: Use example name to tag where HD/nonHD param set
            if method_name == "withdraw" and "Request should contain a 'from' address/account" in text:
                return "HD withdraw request without 'from' address/account"
            if "is deprecated for HD wallets" in text:
                return "HD wallet is deprecated"

        if "Error parsing the native wallet configuration" in text:
            return "Native wallet configuration error (no local blockchain data"
        for i in [
            "UnexpectedDerivationMethod",
            "SingleAddress",
            ]:
            if i in text:
                return i
        return None
        

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
    
    def _ensure_coin_activated(self, instance: KDFInstance, ticker: str,
                               force_enable_platform: bool = False,
                               force_reenable: bool = False):
        """Ensure a coin is activated using the ActivationManager.

        force_enable_platform: when True, allows enabling platform coins like ETH/IRIS
        force_reenable: when True and coin appears enabled, disable then activate again
        """
        if not ticker:
            return {"success": True, "already_enabled": True}
        
        ticker_upper = str(ticker).upper()
        
        # Skip platform coins unless forced from retry logic
        if not force_enable_platform and ticker_upper in ["ETH", "IRIS"]:
            return {"success": True, "already_enabled": True}
        
        # Get the activation manager for this instance
        activation_manager = self.activation_managers.get(instance.name)
        if not activation_manager:
            error_msg = f"No activation manager found for instance {instance.name}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        # Check if coin is already enabled
        if activation_manager.is_coin_enabled(ticker_upper):
            if force_reenable:
                self.logger.info(f"🔄 Re-enabling {ticker_upper} on {instance.name} due to prior error")
                self.disable_coin(instance, ticker_upper)
            else:
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
        # Load test data if available
        if self.test_data is None:
            try:
                with open(self.workspace_root / "postman/generated/reports/test_data.json", "r", encoding="utf-8") as f:
                    self.test_data = json.load(f)
            except Exception:
                self.test_data = {}
        
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
            # Apply test-data overrides for known examples (e.g., my_tx_history from_id)
            try:
                if isinstance(modified_request, dict):
                    # Deep copy to avoid mutating shared dict
                    import copy
                    modified_request = copy.deepcopy(modified_request)
                    method = modified_request.get("method", "")
                    if method == "my_tx_history":
                        # Override legacy from_id if available
                        inst_data = (self.test_data or {}).get(instance.name, {})
                        coin_key = (ticker or "").upper()
                        known = None
                        # Prefer address-mapped txid if present
                        addresses = inst_data.get(coin_key, {}).get("addresses", {}) if isinstance(inst_data, dict) else {}
                        if isinstance(addresses, dict) and addresses:
                            # pick first address in report for this coin
                            addr_key = sorted(addresses.keys())[0]
                            txids = addresses.get(addr_key, {}).get("known_txids", [])
                            if isinstance(txids, list) and len(txids) > 0:
                                known = txids[0]
                        if known:
                            if "from_id" in modified_request:
                                modified_request["from_id"] = known
                            # Also support v2-style paging_options.FromId if seen under legacy by mistake
                            if "paging_options" in modified_request and isinstance(modified_request["paging_options"], dict):
                                modified_request["paging_options"]["FromId"] = known
            except Exception:
                pass
            
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
        # Also persist method_tasks.json from registry
        try:
            tasks_serialized: Dict[str, Any] = {}
            for key, ti in getattr(self, "task_registry", {}).items():
                try:
                    entry = {
                        "task_name": ti.task_name,
                        "task_id": ti.task_id,
                        "created_at": getattr(ti, "created_at", None),
                        "completed": getattr(ti, "completed", False),
                        "completed_at": getattr(ti, "completed_at", None),
                        "init_request": ti.init_request,
                        "init_response": ti.init_response,
                        "status_responses": ti.status_responses,
                        "cancel_request": ti.cancel_request,
                        "cancel_response": ti.cancel_response,
                    }
                    tasks_serialized[key] = entry
                except Exception:
                    continue
            self.task_report_path.parent.mkdir(parents=True, exist_ok=True)
            dump_sorted_json(tasks_serialized, self.task_report_path)
            self.logger.info(f"Task report saved to: {self.task_report_path}")
        except Exception as e:
            self.logger.warning(f"Failed to save task report: {e}")
    
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
                    if self._is_expected_error(text, instance_name, method_name) is not None:
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
        """Regenerate missing responses split reports after response collection, validating actual response content."""
        self.logger.info("Regenerating missing responses (split) reports...")
        # Manual example patterns to skip (require external interaction)
        manual_patterns = ["WalletConnect", "Trezor", "Metamask", "UserAction"]
        
        # Load requests per version
        def load_requests(version: str) -> Dict[str, Dict[str, Any]]:
            reqs: Dict[str, Dict[str, Any]] = {}
            req_dir = self.workspace_root / "src/data/requests/kdf" / version
            for request_file in req_dir.glob("*.json"):
                reqs.update(self.load_json_file(request_file) or {})
            return reqs
        
        v2_requests = load_requests("v2")
        legacy_requests = load_requests("legacy")
        
        # Load responses per version into a single dict per version
        def load_responses(version: str) -> Dict[str, Any]:
            all_responses: Dict[str, Any] = {}
            resp_dir = self.workspace_root / "src/data/responses/kdf" / version
            for response_file in resp_dir.glob("*.json"):
                data = self.load_json_file(response_file) or {}
                if isinstance(data, dict):
                    all_responses.update(data)
            # Load common for references if present
            common_file = self.workspace_root / "src/data/responses/kdf/common.json"
            common = self.load_json_file(common_file) or {}
            return {"__all__": all_responses, "__common__": common}
        
        v2_responses = load_responses("v2")
        legacy_responses = load_responses("legacy")
        
        # Helper to resolve response reference and check if it has any content
        def has_response_content(request_key: str, responses_bundle: Dict[str, Any]) -> bool:
            all_responses = responses_bundle.get("__all__", {})
            common = responses_bundle.get("__common__", {})
            if request_key not in all_responses:
                return False
            value = all_responses[request_key]
            # Resolve if it's a string reference into common
            if isinstance(value, str):
                value = common.get(value)
            # If it's a list, resolve any string refs inside
            if isinstance(value, list):
                resolved_list: List[Any] = []
                for item in value:
                    if isinstance(item, str):
                        resolved_list.append(common.get(item))
                    else:
                        resolved_list.append(item)
                value = resolved_list
            # Now, determine content:
            if isinstance(value, dict):
                success = value.get("success", [])
                error = value.get("error", [])
                return (isinstance(success, list) and len(success) > 0) or (isinstance(error, list) and len(error) > 0)
            # If it's a list of blocks, consider non-empty list as content
            if isinstance(value, list):
                return len(value) > 0
            return False
        
        # Load method configs to skip deprecated
        data_dir = self.workspace_root / "src/data"
        kdf_methods = {}
        for fp in [data_dir / "kdf_methods_legacy.json", data_dir / "kdf_methods_v2.json"]:
            kdf_methods.update(self.load_json_file(fp) or {})
        
        def build_missing(requests: Dict[str, Dict[str, Any]], responses_bundle: Dict[str, Any]) -> Dict[str, List[str]]:
            missing: Dict[str, List[str]] = {}
            for request_key, request_data in requests.items():
                if not isinstance(request_data, dict):
                    continue
                # Skip manual/external examples
                if any(pat in request_key for pat in manual_patterns):
                    continue
                method_name = request_data.get("method", "unknown")
                # Skip deprecated methods
                method_cfg = kdf_methods.get(method_name, {})
                if method_cfg.get("deprecated", False):
                    continue
                # Check if response exists with content
                if not has_response_content(request_key, responses_bundle):
                    missing.setdefault(method_name, []).append(request_key)
            return missing
        
        missing_v2 = build_missing(v2_requests, v2_responses)
        missing_legacy = build_missing(legacy_requests, legacy_responses)
        
        dump_sorted_json(missing_v2, reports_dir / "missing_responses_v2.json")
        dump_sorted_json(missing_legacy, reports_dir / "missing_responses_legacy.json")
        self.logger.info("Missing responses split reports regenerated.")
    
    def update_response_files(self, auto_updatable_responses: Dict[str, Any]) -> int:
        """Update response files with successful responses."""
        self.logger.info("Updating response files")
        if not auto_updatable_responses:
            self.logger.info("No new successful responses to update.")
            return 0
        
        # Build lookup: request_key -> (version, response_file_path)
        mapping: Dict[str, Tuple[str, Path]] = {}
        base_requests = self.workspace_root / "src/data/requests/kdf"
        for version in ["v2", "legacy"]:
            req_dir = base_requests / version
            resp_dir = self.workspace_root / "src/data/responses/kdf" / version
            if not req_dir.exists():
                continue
            for req_file in req_dir.glob("*.json"):
                try:
                    data = self.load_json_file(req_file) or {}
                    for key in data.keys():
                        mapping[key] = (version, resp_dir / req_file.name)
                except Exception:
                    continue
        
        updated = 0
        for request_key, canonical_response in auto_updatable_responses.items():
            try:
                if request_key not in mapping:
                    self.logger.info(f"Skipping update for {request_key}: request key not found in mapping")
                    continue
                version, resp_path = mapping[request_key]
                # Load current response file (create if missing)
                if resp_path.exists():
                    responses_data = self.load_json_file(resp_path) or {}
                else:
                    responses_data = {}
                    resp_path.parent.mkdir(parents=True, exist_ok=True)
                # Ensure request_key entry exists
                entry = responses_data.get(request_key)
                if not isinstance(entry, dict):
                    entry = {"error": [], "success": []}
                    responses_data[request_key] = entry
                success_list = entry.setdefault("success", [])
                # Prepare success item
                item = {"title": "Success", "json": canonical_response}
                # Deduplicate by JSON content
                exists = any(isinstance(x, dict) and x.get("json") == canonical_response for x in success_list)
                if not exists:
                    success_list.append(item)
                    # Save back
                    dump_sorted_json(responses_data, resp_path)
                    updated += 1
                    self.logger.info(f"✅ Updated {resp_path.name} with {request_key}")
            except Exception as e:
                self.logger.warning(f"Failed to update response for {request_key}: {e}")
                continue
        
        self.logger.info(f"Updated response files for {updated} entries")
        return updated


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
