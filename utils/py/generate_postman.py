#!/usr/bin/env python3
"""
Unified Postman Collection Generator for KDF API

This script generates comprehensive Postman collections from KDF JSON files,
supporting both standard collections and environment-specific collections.

Features:
- Generates standard collections with full folder structure and validation
- Generates environment-specific collections (Native, WASM, Trezor variants)
- Parameter validation and reporting
- Protocol filtering for different environments
- Comprehensive CLI interface

Usage:
    python unified_postman_generator.py --help
"""

import json
import os
import sys
import uuid
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
from datetime import datetime
import logging

# Add the lib directory to the path
sys.path.append(str(Path(__file__).parent / "lib"))

from managers.environment_manager import EnvironmentManager
from managers.table_manager import TableManager
from utils.json_utils import dump_sorted_json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class UnifiedPostmanGenerator:
    """Unified generator for both standard and environment-specific Postman collections."""
    
    def __init__(self, workspace_root: Optional[str] = None):
        """Initialize the generator.
        
        Args:
            workspace_root: Path to the workspace root. If None, auto-detects.
        """
        if workspace_root is None:
            # Auto-detect workspace root from utils/py/ to workspace root
            workspace_root = Path(__file__).parent.parent.parent
        
        self.workspace_root = Path(workspace_root)
        self.requests_dir = self.workspace_root / "src" / "data" / "requests" / "kdf"
        self.responses_dir = self.workspace_root / "src" / "data" / "responses" / "kdf"
        self.tables_dir = self.workspace_root / "src" / "data" / "tables"
        
        # Initialize managers
        self.env_manager = EnvironmentManager()
        self.table_manager = TableManager(workspace_root=self.workspace_root, logger=logger)
        
        # Reports data
        self.unused_params = {}
        self.missing_responses = {}
        self.missing_requests = {}
        self.missing_methods = []
        self.untranslated_keys = []
        
        # Task ID variables for method groups
        self.task_variables = {}
        
        # Load configurations
        self.method_config = self.load_method_config()
        self.common_responses = self.load_common_responses()
    
    # ===== COMMON UTILITIES =====
    
    def load_json_file(self, file_path: Path) -> Optional[Dict]:
        """Load JSON file and return its content."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"File not found: {file_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            return None
    
    def load_method_config(self) -> Dict[str, Dict]:
        """Load method configuration from kdf_methods.json."""
        config_file = self.workspace_root / "src" / "data" / "kdf_methods.json"
        config = self.load_json_file(config_file)
        return config if config else {}
    
    def load_common_responses(self) -> Dict[str, Dict]:
        """Load common responses from common.json."""
        common_file = self.responses_dir / "common.json"
        common_responses = self.load_json_file(common_file)
        return common_responses if common_responses else {}
    
    def _is_manual_method(self, request_key: str) -> bool:
        """Check if a method requires manual intervention or external services."""
        manual_patterns = [
            "WalletConnect",  # Requires external wallet connection
            "Trezor",         # Requires hardware wallet
            "Metamask",       # Requires browser extension
            "Pin",            # Requires user PIN entry
            "UserAction"      # Requires user interaction
        ]
        
        return any(pattern in request_key for pattern in manual_patterns)
    
    def load_all_tables(self) -> Dict[str, Dict]:
        """Load all table files and combine them."""
        return self.table_manager.load_all_tables()
    
    def load_request_data(self, version: str = "v2") -> Dict[str, Any]:
        """Load ALL request data from JSON files in the specified version directory."""
        request_dir = self.requests_dir / version
        
        if not request_dir.exists():
            raise FileNotFoundError(f"Request directory not found: {request_dir}")
        
        all_requests = {}
        for request_file in request_dir.glob("*.json"):
            file_data = self.load_json_file(request_file)
            if file_data:
                all_requests.update(file_data)
        
        if not all_requests:
            raise FileNotFoundError(f"No valid request files found in: {request_dir}")
        
        return all_requests
    
    # ===== DATA PROCESSING UTILITIES =====
    
    def extract_method_name(self, method: str) -> str:
        """Extract method name from KDF method string."""
        return method.replace("::", "_")
    
    def get_method_path_components(self, method: str) -> List[str]:
        """Convert method name to folder path components."""
        if "::" in method:
            # For v2 methods like "task::enable_utxo::init"
            parts = method.split("::")
            return parts  # ["task", "enable_utxo", "init"]
        else:
            # For legacy methods like "enable"
            return [method]  # ["enable"]
    
    def get_method_group(self, request_key: str) -> str:
        """Extract method group from request key."""
        suffixes = ["Init", "Status", "UserAction", "Cancel"]
        group = request_key
        for suffix in suffixes:
            if group.endswith(suffix):
                group = group[:-len(suffix)]
                break
        return group
    
    def get_task_variable_name(self, method: str) -> str:
        """Generate task variable name from method."""
        if "::" in method:
            parts = method.split("::")
            if len(parts) >= 2:
                method_part = parts[1].replace("_", " ").title().replace(" ", "")
                return f"Task{method_part}_TaskId"
        return "DefaultTask_TaskId"
    
    def get_translated_name(self, request_key: str) -> str:
        """Get translated name for request key, fallback to original."""
        for method, config in self.method_config.items():
            # Skip deprecated methods
            if config.get('deprecated', False):
                continue
            examples = config.get("examples", {})
            if request_key in examples:
                return examples[request_key]
        
        if request_key not in self.untranslated_keys:
            self.untranslated_keys.append(request_key)
        return request_key
    
    # ===== DATA TRANSFORMATION =====
    
    def replace_userpass(self, data: Any) -> Any:
        """Replace userpass values with Postman variable."""
        if isinstance(data, dict):
            new_dict = {}
            for key, value in data.items():
                if key == "userpass" and value == "RPC_UserP@SSW0RD":
                    new_dict[key] = "{{ userpass }}"
                else:
                    new_dict[key] = self.replace_userpass(value)
            return new_dict
        elif isinstance(data, list):
            return [self.replace_userpass(item) for item in data]
        else:
            return data
    
    def replace_task_id(self, data: Any, task_var_name: str) -> Any:
        """Replace task_id values with Postman variable."""
        if isinstance(data, dict):
            new_dict = {}
            for key, value in data.items():
                if key == "task_id" and isinstance(value, int):
                    new_dict[key] = f"{{{{ {task_var_name} }}}}"
                else:
                    new_dict[key] = self.replace_task_id(value, task_var_name)
            return new_dict
        elif isinstance(data, list):
            return [self.replace_task_id(item, task_var_name) for item in data]
        else:
            return data
    
    # ===== ENVIRONMENT-SPECIFIC FILTERING =====
    
    def filter_protocols_for_environment(self, request_data: Dict[str, Any], 
                                       environment: str) -> Dict[str, Any]:
        """Filter and update protocol configurations for specific environment."""
        filtered_data = json.loads(json.dumps(request_data))  # Deep copy
        
        # Parse environment components
        env_parts = environment.split('_')
        base_env = env_parts[0]  # native, wasm
        wallet_type = env_parts[1] if len(env_parts) > 1 and env_parts[1] in ['hd', 'iguana'] else None
        
        for request_key, request_body in filtered_data.items():
            if not isinstance(request_body, dict):
                continue
            
            params = request_body.get('params', {})
            method = request_body.get('method', '')
            
            # Handle electrum servers
            self._update_electrum_servers(params, base_env)
            
            # Handle WebSocket URLs
            self._update_websocket_urls(params, base_env)
            
            # Handle nodes for ETH/Tendermint
            self._update_node_urls(params, base_env)
            
            # Handle wallet type specific parameters
            self._update_wallet_type_params(params, method, wallet_type)
        
        return filtered_data
    
    def _update_electrum_servers(self, params: Dict[str, Any], environment: str):
        """Update electrum server configurations for environment."""
        # Handle nested electrum servers (UTXO coins)
        if 'mode' in params and 'rpc_data' in params['mode']:
            rpc_data = params['mode']['rpc_data']
            if 'servers' in rpc_data:
                rpc_data['servers'] = self._filter_electrum_servers(
                    rpc_data['servers'], environment
                )
        
        # Handle direct electrum servers (Z-coins)
        if 'electrum_servers' in params:
            params['electrum_servers'] = self._filter_electrum_servers(
                params['electrum_servers'], environment
            )
    
    def _filter_electrum_servers(self, servers: List[Dict], environment: str) -> List[Dict]:
        """Filter electrum servers based on environment protocol preferences."""
        if environment == 'wasm':
            # WASM only supports WSS
            return [s for s in servers if s.get('protocol') == 'WSS']
        elif environment == 'native':
            # Native prefers TCP and SSL, but can use WSS
            preferred_order = ['TCP', 'SSL', 'WSS']
            sorted_servers = []
            for protocol in preferred_order:
                sorted_servers.extend([s for s in servers if s.get('protocol') == protocol])
            return sorted_servers[:3]  # Limit to 3 servers
        else:
            return servers
    
    def _update_websocket_urls(self, params: Dict[str, Any], environment: str):
        """Update WebSocket URLs for environment."""
        if environment == 'wasm':
            # Ensure all WebSocket URLs use WSS
            for key in ['nodes', 'ws_url']:
                if key in params:
                    if key == 'nodes' and isinstance(params[key], list):
                        for node in params[key]:
                            if 'ws_url' in node and node['ws_url'].startswith('ws://'):
                                node['ws_url'] = node['ws_url'].replace('ws://', 'wss://')
    
    def _update_node_urls(self, params: Dict[str, Any], environment: str):
        """Update node URLs for environment preferences."""
        if 'nodes' in params and isinstance(params['nodes'], list):
            for node in params['nodes']:
                if environment == 'wasm':
                    if 'ws_url' in node and not node['ws_url'].startswith('wss://'):
                        if node['ws_url'].startswith('ws://'):
                            node['ws_url'] = node['ws_url'].replace('ws://', 'wss://')
    
    def _update_wallet_type_params(self, params: Dict[str, Any], method: str, wallet_type: str):
        """Update parameters based on wallet type requirements."""
        if wallet_type is None:
            return
        
        if wallet_type == 'iguana':
            # Remove HD-only parameters for Iguana wallet
            hd_only_params = self.env_manager.get_conditional_params(method, 'hd')
            for param in hd_only_params:
                if param in params:
                    del params[param]
    
    # ===== VALIDATION =====
    
    def validate_request_params(self, request_data: Dict, method: str, tables: Dict[str, Dict]) -> Set[str]:
        """Validate request parameters against table definitions and return unused params."""
        if method not in self.method_config:
            logger.warning(f"No method config found for method: {method}")
            return set()
        
        validation_result = self.table_manager.validate_request_params(
            request_data, method, self.method_config[method]
        )
        
        if validation_result:
            if validation_result.unused_params:
                logger.warning(f"Unused parameters in {method}: {validation_result.unused_params}")
            return validation_result.unused_params
        
        return set()
    
    
    def check_response_exists(self, request_key: str, version: str) -> bool:
        """Check if response exists for the request in ANY response file and has actual content."""
        response_dir = self.responses_dir / version
        if not response_dir.exists():
            return False
        
        # Check all response files in the version directory
        for response_file in response_dir.glob("*.json"):
            response_data = self.load_json_file(response_file)
            if not response_data:
                continue
            
            if request_key not in response_data:
                continue
            
            # Resolve any common response references
            response_value = response_data[request_key]
            resolved_response = self.resolve_response_reference(response_value, self.common_responses)
            
            if resolved_response is None:
                continue
            
            # Check if response has actual content (not just empty templates)
            if isinstance(resolved_response, dict):
                # Check for success and error arrays
                success_responses = resolved_response.get("success", [])
                error_responses = resolved_response.get("error", [])
                
                # If both arrays are empty, consider this as missing response
                if (isinstance(success_responses, list) and len(success_responses) == 0 and 
                    isinstance(error_responses, list) and len(error_responses) == 0):
                    continue
            
            # Found a valid response
            return True
        
        return False
    
    def resolve_response_reference(self, response_value: Any, common_responses: Dict[str, Dict]) -> Any:
        """Resolve response references to common responses."""
        if isinstance(response_value, str) and response_value in common_responses:
            return common_responses[response_value]
        elif isinstance(response_value, list):
            resolved_list = []
            for item in response_value:
                if isinstance(item, str) and item in common_responses:
                    resolved_list.append(common_responses[item])
                else:
                    resolved_list.append(item)
            return resolved_list
        else:
            return response_value
    
    # ===== TABLE GENERATION =====
    
    def _track_missing_table(self, method: str, table_type: str) -> None:
        """Track a missing table by type."""
        self.table_manager.track_missing_table(method, table_type)

    def generate_table_markdown(self, method: str, tables: Dict[str, Dict]) -> str:
        """Generate markdown table from table data for method."""
        if method not in self.method_config:
            # Method not defined - will be tracked in missing_methods.json
            return ""
        
        return self.table_manager.generate_table_markdown(method, self.method_config[method])
    
    # ===== POSTMAN REQUEST CREATION =====
    
    def create_postman_request(self, request_key: str, request_data: Dict, 
                             version: str, tables: Dict[str, Dict], 
                             method_examples: List[tuple] = None,
                             environment: str = None) -> Dict:
        """Create a Postman request object."""
        method = request_data.get("method", "unknown")
        
        # Get translated name
        if method_examples and len(method_examples) > 1:
            translated_name = method
        else:
            translated_name = self.get_translated_name(request_key)
        
        # Add environment suffix for environment-specific collections
        if environment and environment != "standard":
            env_suffix = environment.replace('_', ' ').title()
            if env_suffix not in translated_name:
                translated_name += f" ({env_suffix})"
        
        # Handle task_id variables
        task_var_name = None
        if "task_id" in json.dumps(request_data):
            task_var_name = self.get_task_variable_name(method)
            self.task_variables[task_var_name] = "1"
        
        # Replace userpass and task_id
        processed_data = self.replace_userpass(request_data)
        if task_var_name:
            processed_data = self.replace_task_id(processed_data, task_var_name)
        
        # Generate description with table markdown
        description = self.generate_table_markdown(method, tables)
        
        # Add environment-specific description notes
        if environment:
            description += self._generate_environment_notes(environment, method)
        
        # Add examples if there are multiple variants
        examples = []
        if method_examples and len(method_examples) > 1:
            for example_key, example_data in method_examples:
                example_name = self.get_translated_name(example_key)
                processed_example = self.replace_userpass(example_data)
                if task_var_name:
                    processed_example = self.replace_task_id(processed_example, task_var_name)
                
                examples.append({
                    "name": example_name,
                    "originalRequest": {
                        "method": "POST",
                        "header": [{"key": "Content-Type", "value": "application/json"}],
                        "body": {
                            "mode": "raw",
                            "raw": json.dumps(processed_example, indent=2)
                        },
                        "url": {
                            "raw": "{{base_url}}",
                            "host": ["{{base_url}}"]
                        }
                    },
                    "status": "OK",
                    "code": 200,
                    "_postman_previewlanguage": "json"
                })
        
        request_obj = {
            "name": translated_name,
            "request": {
                "method": "POST",
                "header": [{"key": "Content-Type", "value": "application/json"}],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps(processed_data, indent=2)
                },
                "url": {
                    "raw": "{{base_url}}",
                    "host": ["{{base_url}}"]
                },
                "description": description
            },
            "response": examples,
            "event": []
        }
        
        # Add test for capturing task_id if this is an init request
        if method.endswith("::init") and "task_id" not in json.dumps(request_data):
            actual_task_var_name = self.get_task_variable_name(method)
            test_script = f"""
pm.test("Capture task_id", function () {{
    const responseJson = pm.response.json();
    if (responseJson.result && responseJson.result.task_id) {{
        pm.collectionVariables.set("{actual_task_var_name}", responseJson.result.task_id);
    }}
}});
"""
            request_obj["event"] = [{
                "listen": "test",
                "script": {
                    "exec": test_script.strip().split('\n'),
                    "type": "text/javascript"
                }
            }]
        
        return request_obj
    
    def _generate_environment_notes(self, environment: str, method: str) -> str:
        """Generate environment-specific notes for request description."""
        notes = "\n\n"
        
        if environment == 'wasm':
            notes += "**Environment Notes:**\n"
            notes += "- This request uses WebSocket Secure (WSS) protocols only\n"
            notes += "- Electrum servers are filtered to WSS-compatible endpoints\n"
        elif 'trezor' in environment:
            notes += "**Hardware Requirements:**\n"
            notes += "- This request requires Trezor hardware wallet\n"
        
        # Add protocol preferences
        base_env = environment.split('_')[0] if environment else 'native'
        protocol_prefs = self.env_manager.get_protocol_preferences(method, base_env)
        if protocol_prefs:
            notes += f"\n**Protocol Preferences:** {protocol_prefs}\n"
        
        return notes
    
    # ===== FOLDER STRUCTURE CREATION =====
    
    def create_folder_structure(self, requests: Dict[str, Dict], version: str, 
                              filename: str, tables: Dict[str, Dict],
                              environment: str = None) -> Dict:
        """Create folder structure for Postman collection organized by method paths."""
        folder_tree = {}
        
        # Group requests by method
        method_groups = {}
        for request_key, request_data in requests.items():
            method = request_data.get("method")
            if not method:
                continue
            
            # Check environment compatibility if specified
            if environment and environment != "standard":
                base_env = environment.split('_')[0]
                hardware = 'trezor' if 'trezor' in environment else None
                wallet_type = environment.split('_')[1] if '_' in environment and environment.split('_')[1] in ['hd', 'iguana'] else None
                
                if not self._is_request_compatible(request_key, method, base_env, hardware, wallet_type):
                    continue
            
            if method not in method_groups:
                method_groups[method] = []
            method_groups[method].append((request_key, request_data))
        
        # Process each method group
        for method, examples in method_groups.items():
            method_components = self.get_method_path_components(method)
            path_parts = [version.lower(), filename.lower()] + method_components
            
            # Navigate/create the nested structure
            current_level = folder_tree
            for i, part in enumerate(path_parts):
                if part not in current_level:
                    current_level[part] = {
                        "_folders": {},
                        "_items": []
                    }
                
                if i == len(path_parts) - 1:
                    # Last component - create request
                    primary_key, primary_data = examples[0]
                    
                    request_obj = self.create_postman_request(
                        primary_key, 
                        primary_data, 
                        version, 
                        tables,
                        examples if len(examples) > 1 else None,
                        environment
                    )
                    current_level[part]["_items"].append(request_obj)
                else:
                    current_level = current_level[part]["_folders"]
        
        return folder_tree
    
    def _is_request_compatible(self, request_key: str, method: str, 
                             environment: str, hardware: str = None, wallet_type: str = None) -> bool:
        """Check if a request is compatible with the target environment."""
        # Check method compatibility
        is_compatible, _ = self.env_manager.validate_method_compatibility(
            method, environment, hardware, wallet_type
        )
        
        if not is_compatible:
            return False
        
        # Check example-specific compatibility using pattern matching
        return self.env_manager._matches_pattern_requirements(
            request_key, environment, hardware, wallet_type
        )
    
    def convert_tree_to_postman_folders(self, tree: Dict, name: str = "") -> List[Dict]:
        """Convert the folder tree to Postman folder structure."""
        items = []
        
        for key, value in tree.items():
            if key.startswith("_"):
                continue
            
            folder_items = []
            
            if "_items" in value:
                folder_items.extend(value["_items"])
            
            if "_folders" in value:
                for subfolder_name, subfolder_data in value["_folders"].items():
                    subfolder_items = self.convert_tree_to_postman_folders({subfolder_name: subfolder_data}, subfolder_name)
                    folder_items.extend(subfolder_items)
            
            if folder_items:
                items.append({
                    "name": key,
                    "item": folder_items
                })
        
        return items
    
    # ===== COLLECTION GENERATION =====
    
    def generate_standard_collection(self) -> Dict:
        """Generate the standard comprehensive Postman collection."""
        tables = self.load_all_tables()
        folder_tree = {}
        
        # Process each version directory
        for version_dir in self.requests_dir.iterdir():
            if not version_dir.is_dir():
                continue
            
            version = version_dir.name
            logger.info(f"Processing version: {version}")
            
            # Process all JSON files in the version directory
            for json_file in version_dir.glob("*.json"):
                filename = json_file.stem
                logger.info(f"Processing file: {filename}")
                
                requests_data = self.load_json_file(json_file)
                if not requests_data:
                    continue
                
                # Filter out deprecated methods and validate
                filtered_requests_data = {}
                for request_key, request_data in requests_data.items():
                    method = request_data.get("method")
                    if method:
                        method_config = self.method_config.get(method, {})
                        if method_config.get('deprecated', False):
                            continue  # Skip deprecated methods
                    filtered_requests_data[request_key] = request_data
                
                # Validate and collect reports
                for request_key, request_data in filtered_requests_data.items():
                    method = request_data.get("method")
                    if method:
                        unused = self.validate_request_params(request_data, method, tables)
                        if unused:
                            self.unused_params[method] = list(unused)
                    
                    if not self.check_response_exists(request_key, version):
                        # Skip deprecated methods from missing responses report
                        method_config = self.method_config.get(method, {})
                        if not method_config.get('deprecated', False):
                            # Skip manual/external methods that can't be automated
                            if self._is_manual_method(request_key):
                                continue
                            if method not in self.missing_responses:
                                self.missing_responses[method] = []
                            self.missing_responses[method].append(request_key)
                
                # Add to folder tree (using filtered data)
                file_tree = self.create_folder_structure(filtered_requests_data, version, filename, tables, "standard")
                
                # Merge into main tree
                for key, value in file_tree.items():
                    if key not in folder_tree:
                        folder_tree[key] = value
                    else:
                        if "_folders" in value:
                            for subfolder_name, subfolder_data in value["_folders"].items():
                                if subfolder_name not in folder_tree[key]["_folders"]:
                                    folder_tree[key]["_folders"][subfolder_name] = subfolder_data
                        if "_items" in value:
                            folder_tree[key]["_items"].extend(value["_items"])
        
        # Convert tree to Postman folder structure
        all_folders = self.convert_tree_to_postman_folders(folder_tree)
        
        # Create collection variables
        variables = [
            {"key": "base_url", "value": "http://127.0.0.1:7783", "type": "string"},
            {"key": "userpass", "value": "RPC_UserP@SSW0RD", "type": "string"}
        ]
        
        # Add task ID variables
        for var_name, default_value in self.task_variables.items():
            variables.append({
                "key": var_name,
                "value": default_value,
                "type": "string"
            })
        
        # Create the collection
        collection = {
            "info": {
                "name": "Komodo DeFi Framework API",
                "description": "Comprehensive auto-generated Postman collection for KDF API",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                "_postman_id": str(uuid.uuid4())
            },
            "item": all_folders,
            "variable": variables
        }
        
        return collection
    
    def generate_environment_collection(self, environment: str) -> Dict[str, Any]:
        """Generate a Postman collection for a specific environment."""
        # Load and filter request data
        request_data = self.load_request_data('v2')
        
        # Filter out deprecated methods first
        filtered_request_data = {}
        for request_key, request_info in request_data.items():
            method = request_info.get('method')
            if method:
                method_config = self.method_config.get(method, {})
                if method_config.get('deprecated', False):
                    continue  # Skip deprecated methods
            filtered_request_data[request_key] = request_info
        
        filtered_data = self.filter_protocols_for_environment(filtered_request_data, environment)
        
        # Get environment configuration
        env_configs = self.env_manager.get_environment_specific_postman_configs()
        config = env_configs.get(environment, {})
        
        # Load tables for descriptions
        tables = self.load_all_tables()
        
        collection = {
            "info": {
                "name": config.get('name', f'KDF API ({environment.title()})'),
                "description": self._generate_collection_description(environment, config),
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                "_postman_id": f"kdf-{environment}-{datetime.now().strftime('%Y%m%d')}"
            },
            "variable": [
                {
                    "key": "base_url",
                    "value": config.get('base_url', 'http://127.0.0.1:7783'),
                    "type": "string"
                },
                {
                    "key": "userpass",
                    "value": "RPC_UserP@SSW0RD",
                    "type": "string"
                }
            ],
            "item": []
        }
        
        # Group requests by method family
        method_groups = self._group_requests_by_method(filtered_data)
        
        for method_family, requests in method_groups.items():
            folder_item = {
                "name": method_family,
                "item": []
            }
            
            for request_key, request_body in requests.items():
                method = request_body.get('method', '')
                hardware = 'trezor' if 'trezor' in environment else None
                wallet_type = config.get('wallet_type', None)
                base_env = environment.split('_')[0]
                
                if self._is_request_compatible(request_key, method, base_env, hardware, wallet_type):
                    postman_request = self.create_postman_request(
                        request_key, request_body, 'v2', tables, None, environment
                    )
                    folder_item["item"].append(postman_request)
            
            if folder_item["item"]:
                collection["item"].append(folder_item)
        
        return collection
    
    def _generate_collection_description(self, environment: str, config: Dict) -> str:
        """Generate description for the collection."""
        description = config.get('description', f'KDF API for {environment} environment')
        notes = config.get('notes', '')
        
        protocol_info = ""
        if 'preferred_protocols' in config:
            protocols = config['preferred_protocols']
            protocol_details = []
            for proto_type, proto_list in protocols.items():
                protocol_details.append(f"{proto_type}: {', '.join(proto_list)}")
            protocol_info = f"\n\nSupported Protocols:\n- " + "\n- ".join(protocol_details)
        
        hardware_info = ""
        if 'hardware' in config:
            hardware_info = f"\n\nHardware Support: {', '.join(config['hardware'])}"
        
        return f"{description}\n\n{notes}{protocol_info}{hardware_info}"
    
    def _group_requests_by_method(self, request_data: Dict[str, Any]) -> Dict[str, Dict]:
        """Group requests by method family for better organization."""
        groups = {}
        
        for request_key, request_body in request_data.items():
            if not isinstance(request_body, dict):
                continue
            
            method = request_body.get('method', '')
            
            # Determine method family
            if method.startswith('task::enable_'):
                coin_type = method.split('::')[1].replace('enable_', '')
                family = f"Task Enable {coin_type.upper()}"
            elif method.startswith('enable_'):
                family = "Legacy Enable"
            else:
                family = "Other Methods"
            
            if family not in groups:
                groups[family] = {}
            
            groups[family][request_key] = request_body
        
        return groups
    
    # ===== REPORTS =====
    
    def detect_missing_requests_and_methods(self) -> None:
        """Detect missing requests (responses without corresponding requests) and missing methods.
        
        Excludes deprecated methods from all missing reports.
        """
        # Get set of deprecated methods
        deprecated_methods = set()
        for method_name, method_config in self.method_config.items():
            if method_config.get('deprecated', False):
                deprecated_methods.add(method_name)
        
        # Load all request and response data from all files
        for version in ['v2', 'legacy']:
            version_responses_dir = self.responses_dir / version
            version_requests_dir = self.requests_dir / version
            
            if not version_responses_dir.exists() or not version_requests_dir.exists():
                continue
            
            # Collect all requests from all files in this version
            requests_data = {}
            for request_file in version_requests_dir.glob("*.json"):
                request_data = self.load_json_file(request_file) or {}
                requests_data.update(request_data)
            
            # Collect all responses from all files in this version    
            responses_data = {}
            for response_file in version_responses_dir.glob("*.json"):
                response_data = self.load_json_file(response_file) or {}
                responses_data.update(response_data)
            
            # Find missing requests (responses without corresponding requests)
            missing_requests_for_version = []
            for response_key in responses_data.keys():
                # Check if there's a corresponding request
                if response_key not in requests_data:
                    # Check if this response corresponds to a deprecated method
                    is_deprecated = False
                    for request_key, request_data in requests_data.items():
                        if isinstance(request_data, dict) and "method" in request_data:
                            method_name = request_data["method"]
                            if method_name in deprecated_methods:
                                # This is a deprecated method's response - skip it
                                is_deprecated = True
                                break
                    
                    # Also check if the response key itself suggests a deprecated method
                    # by looking for the method name in existing requests
                    for request_key, request_data in requests_data.items():
                        if isinstance(request_data, dict) and "method" in request_data:
                            method_name = request_data["method"]
                            if method_name in deprecated_methods and method_name in response_key.lower():
                                is_deprecated = True
                                break
                    
                    if not is_deprecated:
                        missing_requests_for_version.append(response_key)
            
            if missing_requests_for_version:
                self.missing_requests[version] = sorted(missing_requests_for_version)
            
            # Find missing methods (requests without method definitions in kdf_methods.json)
            for request_key, request_data in requests_data.items():
                if isinstance(request_data, dict) and "method" in request_data:
                    method_name = request_data["method"]
                    # Skip deprecated methods
                    if method_name not in deprecated_methods and method_name not in self.method_config:
                        if method_name not in self.missing_methods:
                            self.missing_methods.append(method_name)
        
        # Sort missing methods
        self.missing_methods = sorted(self.missing_methods)
    
    def detect_missing_response_and_error_tables(self) -> None:
        """Detect missing response and error tables for all methods."""
        for method_name, method_config in self.method_config.items():
            # Skip deprecated methods
            if method_config.get('deprecated', False):
                continue
            
            # Use TableManager to validate all table references
            self.table_manager.validate_method_tables(method_name, method_config)
    
    def save_reports(self, reports_dir: Path) -> None:
        """Save validation reports with consistent alphabetical sorting.
        
        Always writes all report files, even if empty, to indicate current state.
        """
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Save unused parameters report (always)
        sorted_unused = {}
        if self.unused_params:
            for method in sorted(self.unused_params.keys()):
                sorted_unused[method] = sorted(self.unused_params[method])
        
        unused_file = reports_dir / "unused_params.json"
        dump_sorted_json(sorted_unused, unused_file)
        logger.info(f"Unused parameters report saved to {unused_file}")
        
        # Save missing responses report (always)
        sorted_missing = {}
        if self.missing_responses:
            for method in sorted(self.missing_responses.keys()):
                sorted_missing[method] = sorted(self.missing_responses[method])
        
        missing_file = reports_dir / "missing_responses.json"
        dump_sorted_json(sorted_missing, missing_file)
        logger.info(f"Missing responses report saved to {missing_file}")
        
        # Save untranslated keys report (always)
        untranslated_list = sorted(self.untranslated_keys) if self.untranslated_keys else []
        untranslated_file = reports_dir / "untranslated_keys.json"
        dump_sorted_json(untranslated_list, untranslated_file)
        logger.info(f"Untranslated keys report saved to {untranslated_file}")
        
        # Save missing tables report (always) - now grouped by type
        missing_tables_file = reports_dir / "missing_tables.json"
        self.table_manager.save_missing_tables_report(missing_tables_file)
        
        # Save missing requests report (always)
        sorted_missing_requests = {}
        if self.missing_requests:
            for version in sorted(self.missing_requests.keys()):
                sorted_missing_requests[version] = sorted(self.missing_requests[version])
        
        missing_requests_file = reports_dir / "missing_requests.json"
        dump_sorted_json(sorted_missing_requests, missing_requests_file)
        logger.info(f"Missing requests report saved to {missing_requests_file}")
        
        # Save missing methods report (always)
        missing_methods_list = sorted(self.missing_methods) if self.missing_methods else []
        missing_methods_file = reports_dir / "missing_methods.json"
        dump_sorted_json(missing_methods_list, missing_methods_file)
        logger.info(f"Missing methods report saved to {missing_methods_file}")
    
    # ===== SELF-REPAIR FUNCTIONALITY =====
    
    def discover_missing_methods(self) -> Dict[str, Dict]:
        """Discover methods in request files that are missing from method config."""
        missing_methods = {}
        
        # Scan all request files to find methods
        for version_dir in self.requests_dir.iterdir():
            if not version_dir.is_dir():
                continue
            
            for json_file in version_dir.glob("*.json"):
                requests_data = self.load_json_file(json_file)
                if not requests_data:
                    continue
                
                for request_key, request_data in requests_data.items():
                    method = request_data.get("method")
                    if method and method not in self.method_config:
                        # Check if method exists in config but is deprecated
                        existing_config = self.method_config.get(method, {})
                        if existing_config.get('deprecated', False):
                            continue  # Skip deprecated methods
                            
                        if method not in missing_methods:
                            missing_methods[method] = {
                                "examples": {},
                                "version": version_dir.name,
                                "file": json_file.stem
                            }
                        
                        # Infer a human-readable name for this example
                        example_name = self._infer_example_name(request_key, method)
                        missing_methods[method]["examples"][request_key] = example_name
        
        return missing_methods
    
    def _infer_example_name(self, request_key: str, method: str) -> str:
        """Infer a human-readable name for a request example."""
        # Remove common prefixes
        name = request_key
        
        # Convert CamelCase to Title Case with spaces
        import re
        name = re.sub(r'([A-Z])', r' \1', name).strip()
        
        # Clean up specific patterns
        name = name.replace("Enable ", "Enable ")
        name = name.replace("Task ", "")
        name = name.replace("Legacy ", "")
        
        # Add context based on method type
        if "enable_" in method:
            if "Init" in request_key:
                name = name.replace(" Init", " Initialization")
            elif "Status" in request_key:
                name = name.replace(" Status", " Status Check")
            elif "Cancel" in request_key:
                name = name.replace(" Cancel", " Cancellation")
            elif "UserAction" in request_key:
                if "Pin" in request_key:
                    name = name.replace(" User Action Pin", " (Trezor PIN)")
                else:
                    name = name.replace(" User Action", " User Action")
        
        return name
    
    def _infer_method_requirements(self, method: str, examples: Dict[str, str]) -> Dict[str, Any]:
        """Infer method requirements based on method name and examples."""
        requirements = {
            "environments": ["native", "wasm"],
            "wallet_types": ["hd", "iguana"]
        }
        
        # Infer environment and wallet compatibility based on method patterns
        
        # Stream methods are wasm-only
        if method.startswith("stream::"):
            requirements["environments"] = ["wasm"]
        
        # Trezor methods require hardware
        if "trezor" in method.lower() or "::user_action" in method.lower():
            requirements["wallet_types"] = ["trezor"]
        
        # Infer from example patterns
        for example_key in examples.keys():
            if "Trezor" in example_key:
                # Trezor examples indicate hardware wallet requirement
                requirements["wallet_types"] = ["trezor"]
            
            if "WalletConnect" in example_key:
                if "wallet_types" in requirements:
                    # WalletConnect typically works with both HD and iguana
                    pass
        
        return requirements
    
    def _infer_table_name(self, method: str) -> str:
        """Infer a table name based on method name."""
        # Convert method name to a table name
        table_name = method.replace("::", "_").replace("_", " ").title().replace(" ", "")
        table_name += "Arguments"
        return table_name
    
    def auto_repair_missing_methods(self, dry_run: bool = True) -> Dict[str, Any]:
        """Automatically repair missing method configurations."""
        missing_methods = self.discover_missing_methods()
        repair_plan = {
            "discovered_methods": len(missing_methods),
            "methods": {},
            "would_add": [] if not dry_run else list(missing_methods.keys())
        }
        
        if not missing_methods:
            logger.info("No missing methods discovered - configuration is complete!")
            return repair_plan
        
        logger.info(f"Discovered {len(missing_methods)} missing methods")
        
        for method, method_info in missing_methods.items():
            table_name = self._infer_table_name(method)
            requirements = self._infer_method_requirements(method, method_info["examples"])
            
            method_config = {
                "request_table": table_name,
                "response_table": "",
                "errors_table": "",
                "examples": method_info["examples"],
                "requirements": requirements
            }
            
            repair_plan["methods"][method] = method_config
            
            if dry_run:
                logger.info(f"Would add method '{method}' with {len(method_info['examples'])} examples")
            else:
                self.method_config[method] = method_config
                logger.info(f"Added method '{method}' with {len(method_info['examples'])} examples")
        
        if not dry_run:
            self._save_method_config()
            logger.info(f"Saved updated method configuration with {len(missing_methods)} new methods")
        
        return repair_plan
    
    def _save_method_config(self):
        """Save the updated method configuration back to file."""
        config_file = self.workspace_root / "src" / "data" / "kdf_methods.json"
        
        # Sort the methods alphabetically for better organization
        sorted_config = dict(sorted(self.method_config.items()))
        
        dump_sorted_json(sorted_config, config_file)
    
    # ===== MAIN GENERATION METHODS =====
    
    def _count_collection_items(self, collection_data: Dict) -> int:
        """Count the total number of requests in a collection."""
        count = 0
        
        def count_items(items):
            nonlocal count
            for item in items:
                if "request" in item:
                    count += 1
                elif "item" in item:
                    count_items(item["item"])
        
        if "item" in collection_data:
            count_items(collection_data["item"])
        
        return count
    
    def _count_report_items(self, report_data: Any) -> int:
        """Count items in a report based on its structure."""
        if isinstance(report_data, dict):
            # For reports like missing_responses and unused_params
            total = 0
            for key, value in report_data.items():
                if isinstance(value, list):
                    total += len(value)
                else:
                    total += 1
            return total
        elif isinstance(report_data, list):
            # For reports like untranslated_keys and missing_tables
            return len(report_data)
        else:
            return 1
    
    def generate_all_collections(self, output_dir: Path, auto_repair: bool = False) -> Dict[str, Dict]:
        """Generate all collection types."""
        generated_files = {}
        
        # Auto-repair missing method configurations if requested
        if auto_repair:
            logger.info("🔧 Running self-repair for missing method configurations...")
            repair_plan = self.auto_repair_missing_methods(dry_run=False)
            if repair_plan["discovered_methods"] > 0:
                logger.info(f"✅ Auto-repaired {repair_plan['discovered_methods']} missing method configurations")
            else:
                logger.info("✅ No missing method configurations found")
        
        # Create output directories
        standard_dir = output_dir / "collections"
        environments_dir = output_dir / "environments" 
        reports_dir = output_dir / "reports"
        
        standard_dir.mkdir(parents=True, exist_ok=True)
        environments_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate standard collection
        logger.info("Generating standard comprehensive collection...")
        standard_collection = self.generate_standard_collection()
        
        standard_file = standard_dir / "kdf_comprehensive_collection.json"
        dump_sorted_json(standard_collection, standard_file)
        
        # Count items in standard collection
        standard_count = self._count_collection_items(standard_collection)
        generated_files["standard"] = {
            "file": str(standard_file.relative_to(self.workspace_root)),
            "count": standard_count
        }
        logger.info(f"Standard collection saved to {standard_file}")
        
        # Generate environment-specific collections
        env_configs = self.env_manager.get_environment_specific_postman_configs()
        
        for environment in env_configs.keys():
            logger.info(f"Generating collection for environment: {environment}")
            
            env_collection = self.generate_environment_collection(environment)
            
            env_file = environments_dir / f"kdf_{environment}_collection.json"
            dump_sorted_json(env_collection, env_file)
            
            # Count items in environment collection
            env_count = self._count_collection_items(env_collection)
            generated_files[environment] = {
                "file": str(env_file.relative_to(self.workspace_root)),
                "count": env_count
            }
            logger.info(f"Environment collection saved to {env_file}")
        
        # Detect missing requests and methods before saving reports
        self.detect_missing_requests_and_methods()
        
        # Detect missing response and error tables
        self.detect_missing_response_and_error_tables()
        
        # Save reports
        self.save_reports(reports_dir)
        
        # Prepare reports data with file paths and counts (always include all reports)
        reports_data = {}
        
        # Unused params (always)
        unused_params_file = reports_dir / "unused_params.json"
        reports_data["unused_params"] = {
            "file": str(unused_params_file.relative_to(self.workspace_root)),
            "count": self._count_report_items(self.unused_params) if self.unused_params else 0
        }
        
        # Missing responses (always)
        missing_responses_file = reports_dir / "missing_responses.json"
        reports_data["missing_responses"] = {
            "file": str(missing_responses_file.relative_to(self.workspace_root)),
            "count": self._count_report_items(self.missing_responses) if self.missing_responses else 0
        }
        
        # Untranslated keys (always)
        untranslated_keys_file = reports_dir / "untranslated_keys.json"
        reports_data["untranslated_keys"] = {
            "file": str(untranslated_keys_file.relative_to(self.workspace_root)),
            "count": len(self.untranslated_keys) if self.untranslated_keys else 0
        }
        
        # Missing tables (always) - with breakdown by type
        missing_tables_file = reports_dir / "missing_tables.json"
        missing_tables_report = self.table_manager.get_missing_tables_report()
        missing_tables_count = sum(len(methods) for methods in missing_tables_report.values())
        
        # Create detailed breakdown
        missing_tables_breakdown = {}
        for table_type, methods in missing_tables_report.items():
            # Convert missing_request_tables -> request_tables for cleaner naming
            clean_type = table_type.replace("missing_", "")
            missing_tables_breakdown[clean_type] = {
                "count": len(methods)
            }
        
        reports_data["missing_tables"] = {
            "file": str(missing_tables_file.relative_to(self.workspace_root)),
            "total_count": missing_tables_count,
            "breakdown": missing_tables_breakdown
        }
        
        # Missing requests (always)
        missing_requests_file = reports_dir / "missing_requests.json"
        missing_requests_count = sum(len(reqs) for reqs in self.missing_requests.values()) if self.missing_requests else 0
        reports_data["missing_requests"] = {
            "file": str(missing_requests_file.relative_to(self.workspace_root)),
            "count": missing_requests_count
        }
        
        # Missing methods (always)
        missing_methods_file = reports_dir / "missing_methods.json"
        reports_data["missing_methods"] = {
            "file": str(missing_methods_file.relative_to(self.workspace_root)),
            "count": len(self.missing_methods) if self.missing_methods else 0
        }
        
        # Generate summary
        summary = {
            "generation_timestamp": datetime.now().isoformat(),
            "generated_files": generated_files,
            "reports": reports_data
        }
        
        summary_file = output_dir / "generation_summary.json"
        dump_sorted_json(summary, summary_file)
        
        return generated_files


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Unified Postman Collection Generator for KDF API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all collections (standard + all environments)
  python unified_postman_generator.py --all
  
  # Generate with auto-repair of missing method configurations
  python unified_postman_generator.py --all --auto-repair
  
  # Check what would be repaired without making changes
  python unified_postman_generator.py --dry-run-repair
  
  # Generate only standard comprehensive collection
  python unified_postman_generator.py --standard
  
  # Generate specific environment collection
  python unified_postman_generator.py --environment native_hd
  
  # Generate with custom output directory
  python unified_postman_generator.py --all --output-dir ./custom_output
  
  # Enable verbose logging
  python unified_postman_generator.py --all --verbose
        """
    )
    
    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--all', '-a',
        action='store_true',
        help="Generate all collections (standard + all environments)"
    )
    mode_group.add_argument(
        '--standard', '-s',
        action='store_true',
        help="Generate only the standard comprehensive collection"
    )
    mode_group.add_argument(
        '--environment', '-e',
        choices=['native_hd', 'native_iguana', 'wasm_hd', 'wasm_iguana', 'trezor_native_hd', 'trezor_wasm_hd'],
        help="Generate specific environment collection"
    )
    mode_group.add_argument(
        '--dry-run-repair',
        action='store_true',
        help="Show what would be repaired without making changes"
    )
    
    # Optional arguments
    parser.add_argument(
        '--workspace', '-w',
        help="Path to workspace root (auto-detected if not provided)"
    )
    parser.add_argument(
        '--output-dir', '-o',
        help="Output directory (default: postman/generated)"
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Enable verbose output"
    )
    parser.add_argument(
        '--auto-repair',
        action='store_true',
        help="Automatically repair missing method configurations"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        generator = UnifiedPostmanGenerator(args.workspace)
        
        # Set output directory
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = generator.workspace_root / "postman" / "generated"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Handle dry-run repair mode
        if args.dry_run_repair:
            print("🔍 Checking for missing method configurations...")
            repair_plan = generator.auto_repair_missing_methods(dry_run=True)
            
            if repair_plan["discovered_methods"] == 0:
                print("✅ No missing method configurations found!")
            else:
                print(f"📋 Found {repair_plan['discovered_methods']} missing method configurations:")
                for method in repair_plan["would_add"]:
                    examples_count = len(repair_plan["methods"][method]["examples"])
                    print(f"  • {method} (with {examples_count} examples)")
                print(f"\nTo apply these fixes, run with --auto-repair")
            return
        
        if args.all:
            print("🚀 Generating all collections...")
            generated_files = generator.generate_all_collections(output_dir, auto_repair=args.auto_repair)
            
            print(f"\n✅ Generated {len(generated_files)} collections:")
            for collection_type, file_info in generated_files.items():
                file_path = file_info["file"]
                count = file_info["count"]
                print(f"  {collection_type}: {file_path} ({count} requests)")
            
            print(f"\n📊 Summary: {output_dir / 'generation_summary.json'}")
            
        elif args.standard:
            print("🚀 Generating standard comprehensive collection...")
            collection = generator.generate_standard_collection()
            
            collections_dir = output_dir / "collections"
            collections_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = collections_dir / "kdf_comprehensive_collection.json"
            dump_sorted_json(collection, output_file)
            
            # Detect missing requests and methods before saving reports
            generator.detect_missing_requests_and_methods()
            
            # Detect missing response and error tables
            generator.detect_missing_response_and_error_tables()
            
            # Save reports
            reports_dir = output_dir / "reports"
            generator.save_reports(reports_dir)
            
            print(f"✅ Standard collection generated: {output_file}")
            print(f"📊 Reports saved to: {reports_dir}")
            
        elif args.environment:
            print(f"🚀 Generating collection for environment: {args.environment}")
            collection = generator.generate_environment_collection(args.environment)
            
            environments_dir = output_dir / "environments"
            environments_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = environments_dir / f"kdf_{args.environment}_collection.json"
            dump_sorted_json(collection, output_file)
            
            print(f"✅ Environment collection generated: {output_file}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
