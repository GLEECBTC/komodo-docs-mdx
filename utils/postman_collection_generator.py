#!/usr/bin/env python3
"""
Postman Collection Generator for KDF API

This script generates a Postman collection from KDF JSON files,
validates parameters, and generates reports for missing data.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class PostmanCollectionGenerator:
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.requests_dir = self.workspace_root / "src/data/requests/kdf"
        self.responses_dir = self.workspace_root / "src/data/responses/kdf"
        self.tables_dir = self.workspace_root / "src/data/tables"
        
        # Reports data
        self.unused_params = {}
        self.missing_responses = {}
        self.untranslated_keys = []
        self.missing_tables = []
                
        # Task ID variables for method groups
        self.task_variables = {}
        
        # Load method configuration
        self.method_config = self.load_method_config()
        
    def load_json_file(self, file_path: Path) -> Optional[Dict]:
        """Load JSON file and return its content"""
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
        """Load method configuration from kdf_methods.json"""
        config_file = self.workspace_root / "src/data/kdf_methods.json"
        config = self.load_json_file(config_file)
        return config if config else {}

    def load_all_tables(self) -> Dict[str, Dict]:
        """Load all table files and combine them"""
        all_tables = {}
        
        # Load common structures
        common_dir = self.tables_dir / "common-structures"
        if common_dir.exists():
            for table_file in common_dir.glob("*.json"):
                tables = self.load_json_file(table_file)
                if tables:
                    all_tables.update(tables)
        
        # Load version-specific tables
        for version_dir in ["legacy", "v2"]:
            version_path = self.tables_dir / version_dir
            if version_path.exists():
                for table_file in version_path.glob("*.json"):
                    tables = self.load_json_file(table_file)
                    if tables:
                        all_tables.update(tables)
        
        return all_tables

    def extract_method_name(self, method: str) -> str:
        """Extract method name from KDF method string"""
        return method.replace("::", "_")

    def get_method_path_components(self, method: str) -> List[str]:
        """Convert method name to folder path components"""
        if "::" in method:
            # For v2 methods like "task::enable_utxo::init"
            parts = method.split("::")
            return parts  # ["task", "enable_utxo", "init"]
        else:
            # For legacy methods like "enable"
            return [method]  # ["enable"]

    def get_method_group(self, request_key: str) -> str:
        """Extract method group from request key (e.g., TaskEnableUtxo from TaskEnableUtxoInit)"""
        # Remove common suffixes to get the base group
        suffixes = ["Init", "Status", "UserAction", "Cancel"]
        group = request_key
        for suffix in suffixes:
            if group.endswith(suffix):
                group = group[:-len(suffix)]
                break
        return group

    def get_task_variable_name(self, method: str) -> str:
        """Generate task variable name from method"""
        if "::" in method:
            # For methods like "task::enable_utxo::init" -> "TaskEnableUtxo_TaskId"
            parts = method.split("::")
            if len(parts) >= 2:
                # Convert enable_utxo to EnableUtxo
                method_part = parts[1].replace("_", " ").title().replace(" ", "")
                return f"Task{method_part}_TaskId"
        return "DefaultTask_TaskId"

    def get_translated_name(self, request_key: str) -> str:
        """Get translated name for request key, fallback to original"""
        # Search through all method configs for this request key
        for method, config in self.method_config.items():
            examples = config.get("examples", {})
            if request_key in examples:
                return examples[request_key]
        
        # Track untranslated keys
        if request_key not in self.untranslated_keys:
            self.untranslated_keys.append(request_key)
        return request_key

    def generate_table_markdown(self, method: str, tables: Dict[str, Dict]) -> str:
        """Generate markdown table from table data for method"""
        if method not in self.method_config:
            if method not in self.missing_tables:
                self.missing_tables.append(method)
            return ""
        
        table_name = self.method_config[method].get("table")
        if not table_name or table_name not in tables:
            if method not in self.missing_tables:
                self.missing_tables.append(method)
            return ""
        
        table_data = tables[table_name].get("data", [])
        if not table_data:
            if method not in self.missing_tables:
                self.missing_tables.append(method)
            return ""
        
        # Generate markdown table with merged columns
        markdown = "## Request Parameters\n\n"
        markdown += "| Parameter | Type | Description |\n"
        markdown += "|-----------|------|-------------|\n"
        
        for param in table_data:
            parameter = param.get("parameter", "")
            param_type = param.get("type", "")
            required = param.get("required", False)
            default = param.get("default", "")
            description = param.get("description", "")
            
            # Build the type column with required/default info
            type_column = param_type
            if required and default:
                type_column += f" (required. Default: `{default}`)"
            elif required:
                type_column += " (required)"
            elif default:
                type_column += f" (Default: `{default}`)"
            
            # Escape markdown characters
            description = description.replace("|", "\\|").replace("\n", " ")
            
            markdown += f"| `{parameter}` | {type_column} | {description} |\n"
        
        return markdown



    def replace_userpass(self, data: Any) -> Any:
        """Replace userpass values with Postman variable"""
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
        """Replace task_id values with Postman variable"""
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

    def validate_request_params(self, request_data: Dict, method: str, tables: Dict[str, Dict]) -> Set[str]:
        """Validate request parameters against table definitions and return unused params"""
        if method not in self.method_config:
            logger.warning(f"No method config found for method: {method}")
            return set()
        
        table_name = self.method_config[method].get("table")
        if not table_name or table_name not in tables:
            logger.warning(f"Table {table_name} not found for method {method}")
            return set()
        
        table_params = set()
        for param_def in tables[table_name].get("data", []):
            table_params.add(param_def["parameter"])
        
        # Extract request parameters - look in params or activation_params
        request_params = set()
        params_data = request_data.get("params", {})
        
        # For task methods, parameters might be nested under activation_params
        if "activation_params" in params_data:
            # Add top-level params
            for key in params_data.keys():
                if key != "activation_params":
                    request_params.add(key)
            # Add activation_params as both the key and extract its nested parameters
            self._extract_param_names(params_data["activation_params"], request_params)
        else:
            # Extract all parameters from params
            self._extract_param_names(params_data, request_params)
        
        unused_params = table_params - request_params
        if unused_params:
            logger.warning(f"Unused parameters in {method}: {unused_params}")
        
        return unused_params

    def _extract_param_names(self, data: Any, param_names: Set[str], prefix: str = "") -> None:
        """Recursively extract parameter names from request data"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ["userpass", "mmrpc", "method"]:
                    continue
                    
                param_key = f"{prefix}.{key}" if prefix else key
                param_names.add(param_key)
                
                if isinstance(value, dict):
                    self._extract_param_names(value, param_names, param_key)
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    self._extract_param_names(value[0], param_names, param_key)

    def check_response_exists(self, request_key: str, version: str) -> bool:
        """Check if response file exists for the request"""
        response_file = self.responses_dir / version / "coin_activation.json"
        if not response_file.exists():
            return False
        
        response_data = self.load_json_file(response_file)
        if not response_data:
            return False
        
        return request_key in response_data

    def create_postman_request(self, request_key: str, request_data: Dict, version: str, tables: Dict[str, Dict], method_examples: List[tuple] = None) -> Dict:
        """Create a Postman request object"""
        method = request_data.get("method", "unknown")
        
        # Get translated name - if there are multiple examples, use the method name instead
        if method_examples and len(method_examples) > 1:
            # Use the method name directly for multiple examples
            translated_name = method
        else:
            # Use the translated name for single examples
            translated_name = self.get_translated_name(request_key)
        
        # Handle task_id variables
        task_var_name = None
        if "task_id" in json.dumps(request_data):
            task_var_name = self.get_task_variable_name(method)
            self.task_variables[task_var_name] = "1"  # Default value
        
        # Replace userpass and task_id
        processed_data = self.replace_userpass(request_data)
        if task_var_name:
            processed_data = self.replace_task_id(processed_data, task_var_name)
        
        # Generate description with table markdown
        description = self.generate_table_markdown(method, tables)
        
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
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
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
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
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

    def create_folder_structure(self, requests: Dict[str, Dict], version: str, filename: str, tables: Dict[str, Dict]) -> Dict:
        """Create folder structure for Postman collection organized by method paths"""
        # Create nested folder structure
        folder_tree = {}
        
        # Group requests by method
        method_groups = {}
        for request_key, request_data in requests.items():
            method = request_data.get("method")
            if not method:
                continue
            
            if method not in method_groups:
                method_groups[method] = []
            method_groups[method].append((request_key, request_data))
        
        # Process each method group
        for method, examples in method_groups.items():
            # Get method path components
            method_components = self.get_method_path_components(method)
            
            # Build the path: version/filename/method/components...
            # e.g., v2/coin_activation/task/enable_utxo/init
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
                    # Last component - create one request with multiple examples
                    # Use the first example as the main request
                    primary_key, primary_data = examples[0]
                    
                    request_obj = self.create_postman_request(
                        primary_key, 
                        primary_data, 
                        version, 
                        tables,
                        examples if len(examples) > 1 else None
                    )
                    current_level[part]["_items"].append(request_obj)
                else:
                    # Navigate deeper
                    current_level = current_level[part]["_folders"]
        
        return folder_tree

    def convert_tree_to_postman_folders(self, tree: Dict, name: str = "") -> List[Dict]:
        """Convert the folder tree to Postman folder structure"""
        items = []
        
        # Process each top-level key in the tree
        for key, value in tree.items():
            if key.startswith("_"):  # Skip internal keys
                continue
                
            folder_items = []
            
            # Add direct items from this level
            if "_items" in value:
                folder_items.extend(value["_items"])
            
            # Add subfolders
            if "_folders" in value:
                for subfolder_name, subfolder_data in value["_folders"].items():
                    subfolder_items = self.convert_tree_to_postman_folders({subfolder_name: subfolder_data}, subfolder_name)
                    folder_items.extend(subfolder_items)
            
            # Create folder if it has any items
            if folder_items:
                items.append({
                    "name": key,
                    "item": folder_items
                })
        
        return items

    def generate_collection(self) -> Dict:
        """Generate the complete Postman collection"""
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
                filename = json_file.stem  # filename without extension
                logger.info(f"Processing file: {filename}")
                
                requests_data = self.load_json_file(json_file)
                if not requests_data:
                    continue
                
                # Validate and collect unused parameters
                for request_key, request_data in requests_data.items():
                    method = request_data.get("method")
                    if method:
                        unused = self.validate_request_params(request_data, method, tables)
                        if unused:
                            self.unused_params[method] = list(unused)
                    
                    # Check for missing responses
                    if not self.check_response_exists(request_key, version):
                        if method not in self.missing_responses:
                            self.missing_responses[method] = []
                        self.missing_responses[method].append(request_key)
                
                # Add to folder tree
                file_tree = self.create_folder_structure(requests_data, version, filename, tables)
                
                # Merge into main tree
                for key, value in file_tree.items():
                    if key not in folder_tree:
                        folder_tree[key] = value
                    else:
                        # Merge folders
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
            {
                "key": "base_url",
                "value": "http://127.0.0.1:7783",
                "type": "string"
            },
            {
                "key": "userpass",
                "value": "RPC_UserP@SSW0RD",
                "type": "string"
            }
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
                "description": "Auto-generated Postman collection for KDF API",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                "_postman_id": str(uuid.uuid4())
            },
            "item": all_folders,
            "variable": variables
        }
        
        return collection

    def save_reports(self, reports_dir: Path) -> None:
        """Save validation reports"""
        # Create reports directory
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Save unused parameters report
        if self.unused_params:
            unused_file = reports_dir / "unused_params.json"
            with open(unused_file, 'w') as f:
                json.dump(self.unused_params, f, indent=2)
            logger.info(f"Unused parameters report saved to {unused_file}")
        
        # Save missing responses report
        if self.missing_responses:
            missing_file = reports_dir / "missing_responses.json"
            with open(missing_file, 'w') as f:
                json.dump(self.missing_responses, f, indent=2)
            logger.info(f"Missing responses report saved to {missing_file}")
        
        # Save untranslated keys report
        if self.untranslated_keys:
            untranslated_file = reports_dir / "untranslated_keys.json"
            with open(untranslated_file, 'w') as f:
                json.dump(self.untranslated_keys, f, indent=2)
            logger.info(f"Untranslated keys report saved to {untranslated_file}")
        
        # Save missing tables report
        if self.missing_tables:
            missing_tables_file = reports_dir / "missing_tables.json"
            with open(missing_tables_file, 'w') as f:
                json.dump(self.missing_tables, f, indent=2)
            logger.info(f"Missing tables report saved to {missing_tables_file}")

    def generate_and_save(self, base_dir: str) -> None:
        """Generate collection and save all outputs"""
        base_path = Path(base_dir)
        
        # Create directory structure
        generated_dir = base_path / "generated"
        reports_dir = base_path / "reports"
        
        generated_dir.mkdir(parents=True, exist_ok=True)
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Generating Postman collection...")
        collection = self.generate_collection()
        
        # Save collection to generated folder
        collection_file = generated_dir / "kdf_postman_collection.json"
        with open(collection_file, 'w') as f:
            json.dump(collection, f, indent=2)
        logger.info(f"Postman collection saved to {collection_file}")
        
        # Save reports to reports folder
        self.save_reports(reports_dir)
        
        # Log summary
        logger.info(f"Collection generated with {len(collection['item'])} version folders")
        if self.unused_params:
            logger.warning(f"Found unused parameters in {len(self.unused_params)} methods")
        if self.missing_responses:
            logger.warning(f"Found missing responses for {len(self.missing_responses)} methods")
        if self.untranslated_keys:
            logger.warning(f"Found {len(self.untranslated_keys)} untranslated keys")
        if self.missing_tables:
            logger.warning(f"Found {len(self.missing_tables)} methods with missing tables")


def main():
    """Main function"""
    # Get the workspace root (parent directory of utils)
    workspace_root = Path(__file__).parent.parent
    generator = PostmanCollectionGenerator(str(workspace_root))
    postman_dir = workspace_root / "postman"
    generator.generate_and_save(str(postman_dir))


if __name__ == "__main__":
    main()
