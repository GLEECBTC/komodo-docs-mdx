#!/usr/bin/env python3
"""
Postman Utilities

Stateless utility functions for Postman operations.
Extracted from postman pipeline modules to follow standard architecture.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

from ..constants import PostmanFolder


def template_json_body(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Template JSON body by replacing values with Postman variables.
    
    Args:
        json_data: Original JSON data
        
    Returns:
        Templated JSON with Postman variables
    """
    # Deep copy to avoid modifying original
    templated = json.loads(json.dumps(json_data))
    
    # Standard replacements
    templated["userpass"] = "{{userpass}}"
    
    # Common field replacements
    field_mappings = {
        "coin": "{{coin}}",
        "base": "{{base}}",
        "rel": "{{rel}}",
        "amount": "{{amount}}",
        "max_volume": "{{amount}}",
        "fee": "{{fee}}",
        "address": "{{address}}",
        "chain_id": "{{chain_id}}",
        "account_id": "{{account_id}}"
    }
    
    for field, template in field_mappings.items():
        if field in templated and templated[field] and not str(templated[field]).startswith("{{"):
            templated[field] = template
    
    # Handle task_id with context-specific templates
    if "task_id" in templated:
        method = templated.get("method", "")
        if "enable_utxo" in method:
            templated["task_id"] = "{{enable_utxo_taskid}}"
        elif "withdraw" in method:
            templated["task_id"] = "{{init_withdraw_taskid}}"
        elif "scan_for_new_addresses" in method:
            templated["task_id"] = "{{scan_new_addresses_taskid}}"
    
    # Handle nested params
    params = templated.get("params", {})
    if isinstance(params, dict):
        _template_nested_params(params)
    
    return templated


def _template_nested_params(params: Dict[str, Any]):
    """Template nested parameters within the params object."""
    nested_mappings = {
        "src_amount": "{{amount}}",
        "slippage": "{{slippage}}",
        "gas_price": "{{gas_price}}",
        "gas_limit": "{{gas_limit}}",
        "protocols": "{{protocols}}",
        "parts": "{{parts}}",
        "main_route_parts": "{{main_route_parts}}",
        "complexity_level": "{{complexity_level}}"
    }
    
    for field, template in nested_mappings.items():
        if field in params and params[field] is not None:
            params[field] = template


def _load_postman_categories_config() -> Dict:
    """Loads Postman categories configuration from JSON file."""
    config_path = Path(__file__).parent.parent.parent / 'data' / 'postman_categories.json'
    with open(config_path, 'r') as f:
        return json.load(f)


def _process_category(category: str, requests: List[Any], method_categories: Dict) -> PostmanFolder:
    """Processes a single category of requests and returns a PostmanFolder."""
    if not requests:
        return None

    category_config = method_categories.get(category, {
        'name': category.title(),
        'description': f'{category.title()} operations'
    })

    method_groups = _group_requests_by_method(requests)
    subfolders, folder_requests = _organize_method_groups(method_groups)

    return PostmanFolder(
        name=category_config['name'],
        description=category_config['description'],
        requests=sorted(folder_requests, key=lambda x: x.name),
        subfolders=sorted(subfolders, key=lambda x: x.name)
    )


def organize_requests_into_folders(categorized_requests: Dict[str, List[Any]]) -> List[PostmanFolder]:
    """
    Organize categorized requests into a folder structure.
    
    Args:
        categorized_requests: Dictionary mapping categories to request lists
        
    Returns:
        List of organized folders
    """
    method_categories = _load_postman_categories_config()
    
    folders = []
    for category, requests in categorized_requests.items():
        if not requests:
            continue
        
        folder = _process_category(category, requests, method_categories)
        if folder:
            folders.append(folder)
            
    return sorted(folders, key=lambda x: x.name)


def _group_requests_by_method(requests: List[Any]) -> Dict[str, List[Any]]:
    """Group requests by their base method name."""
    method_groups = {}
    
    for request in requests:
        base_method = _extract_base_method(request.method_name)
        if base_method not in method_groups:
            method_groups[base_method] = []
        method_groups[base_method].append(request)
    
    return method_groups


def _extract_base_method(method_name: str) -> str:
    """Extract the base method name without operations."""
    if '::' in method_name:
        parts = method_name.split('::')
        if len(parts) > 1:
            return parts[0]
    elif '_' in method_name:
        parts = method_name.split('_')
        if len(parts) > 1:
            return parts[0]
    
    return method_name


def _organize_method_groups(method_groups: Dict[str, List[Any]]) -> tuple:
    """
    Organize method groups into subfolders and direct requests.
    
    Returns:
        Tuple of (subfolders, direct_requests)
    """
    subfolders = []
    folder_requests = []
    
    for method_name, method_requests in method_groups.items():
        # Create subfolder for methods with many requests
        if len(method_requests) > 3:
            subfolder = PostmanFolder(
                name=_format_method_name(method_name),
                description=f"Examples for the {method_name} method",
                requests=sorted(method_requests, key=lambda x: x.name),
                subfolders=[]
            )
            subfolders.append(subfolder)
        else:
            # Add to main folder if few requests
            folder_requests.extend(method_requests)
    
    return subfolders, folder_requests


def _format_method_name(method_name: str) -> str:
    """Format method name for display in folder names."""
    return method_name.replace('_', ' ').title()


def generate_postman_collection(version: str, folders: List[PostmanFolder], 
                               total_requests: int) -> Dict:
    """
    Generate a complete Postman collection.
    
    Args:
        version: API version
        folders: Organized folder structure
        total_requests: Total number of requests
        
    Returns:
        Complete Postman collection dictionary
    """
    collection = {
        "info": _generate_collection_info(version, total_requests),
        "item": [],
        "event": [
            {
                "listen": "prerequest",
                "script": {
                    "id": str(uuid.uuid4()),
                    "exec": _generate_pre_request_script(),
                    "type": "text/javascript"
                }
            }
        ],
        "variable": _generate_collection_variables(version)
    }
    
    # Add folders to collection
    for folder in folders:
        collection['item'].append(_folder_to_postman_item(folder, version))
        
    return collection


def generate_environment_file(version: str) -> Dict:
    """
    Generate a Postman environment file.
    
    Args:
        version: API version
        
    Returns:
        Postman environment dictionary
    """
    env_name = f"Komodo DeFi Framework - {version.upper()}"
    
    return {
        "id": str(uuid.uuid4()),
        "name": env_name,
        "values": _generate_environment_variables(version),
        "postman_variable_scope": "environment",
        "_postman_exported_at": datetime.utcnow().isoformat() + "Z",
        "_postman_exported_using": "Komodo-DeFi-Framework-Docs-Agent/1.0"
    }


def _generate_collection_info(version: str, total_requests: int) -> Dict:
    """
    Generate the 'info' block for a Postman collection.
    """
    return {
        "_postman_id": str(uuid.uuid4()),
        "name": f"Komodo DeFi Framework API - {version.upper()}",
        "description": _generate_collection_description(version, total_requests),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    }


def _generate_collection_description(version: str, total_requests: int) -> str:
    """
    Generate a formatted description for the Postman collection.
    """
    return {
        "content": f"""
# Komodo DeFi Framework API - {version.upper()}

This collection provides a comprehensive set of executable examples for the Komodo DeFi Framework API v{version}. It includes **{total_requests} requests** covering a wide range of functionalities, from coin activation and trading to wallet management and real-time streaming.

## Getting Started

1.  **Install the Environment**: Make sure to import and select the corresponding **Komodo DeFi Framework - {version.upper()}** environment. This contains essential variables like `userpass`, `address`, and `port`.
2.  **Run `mm2`**: Ensure an instance of the Komodo DeFi daemon (`mm2`) is running and accessible at the address specified in your environment variables.
3.  **Explore and Execute**: Navigate through the folders to find the methods you're interested in. Each request is pre-configured to work with the provided environment.

## Collection Structure

The collection is organized into folders based on functionality:
- **Coin & Token Activation**: Methods for enabling coins and tokens.
- **Trading & Orders**: Everything related to order placement, swaps, and market data.
- **Wallet Management**: Operations for checking balances, transaction history, etc.
- **And more...**

Each request includes a description that links back to the official documentation for more details.

---
*Generated by the Komodo Docs Team on {datetime.utcnow().strftime('%Y-%m-%d')}*
""",
        "type": "text/markdown"
    }


def _generate_pre_request_script() -> List[str]:
    """
    Generate the pre-request script for the collection.
    """
    return [
        "// Pre-request Script to set the request body",
        "// This script ensures that the raw JSON body is correctly formatted",
        "",
        "if (pm.request.body && pm.request.body.raw) {",
        "    try {",
        "        const body = JSON.parse(pm.request.body.raw);",
        "        pm.request.body.raw = JSON.stringify(body, null, 2);",
        "    } catch (e) {",
        "        console.error('Failed to parse and stringify request body: ', e);",
        "    }",
        "}"
    ]


def _generate_collection_variables(version: str) -> List[Dict[str, str]]:
    """
    Generate collection-level variables.
    """
    return [
        {
            "key": "base_url",
            "value": "{{address}}:{{port}}",
            "type": "string",
            "description": "Base URL for the Komodo DeFi Framework API"
        }
    ]


def _generate_environment_variables(version: str) -> List[Dict]:
    """
    Generate environment variables by loading from the JSON config.
    
    Args:
        version: API version (used to potentially filter variables)
        
    Returns:
        A list of environment variable dictionaries
    """
    # Load common variables from config file
    config_path = Path(__file__).parent.parent.parent / 'data' / 'postman_variables.json'
    with open(config_path, 'r') as f:
        common_vars = json.load(f)

    variables = []
    for var_group in common_vars.values():
        for details in var_group:
            variables.append({
                "key": details["key"],
                "value": details["value"],
                "type": details["type"],
                "description": details.get("description", "") 
            })

    # Add enabled flag
    for var in variables:
        var['enabled'] = True
        
    return variables


def generate_request_description(api_method: str, method_name: str, 
                               operation: str, version: str) -> str:
    """
    Generate a markdown description for a Postman request.
    
    Args:
        api_method: The full API method name
        method_name: Base name of the method
        operation: The specific operation (e.g., 'init', 'status')
        version: API version
        
    Returns:
        Formatted markdown string
    """
    base_url = "https://docs.komodoplatform.com/komodo-defi-framework/api"
    doc_path = f"{base_url}/{version}/{method_name}/{operation}/"
    
    return {
        "content": f"""
**Method**: `{api_method}`
**Operation**: `{operation}`

This request demonstrates the **{operation}** operation for the **{method_name}** method.

### Description
For detailed information about the parameters, response, and potential errors for this method, please refer to the official documentation.

[**View Full Documentation**]({doc_path})

---
*This is an auto-generated request. Manual modifications may be required for specific use cases.*
""",
        "type": "text/markdown"
    }


def generate_test_script(api_method: str) -> str:
    # Basic test to check for a 200 status and a 'result' in the response body.
    # More sophisticated, method-specific tests could be added in the future.
    return (
        f'pm.test("Status code is 200 for {api_method}", function () {{'
        '    pm.response.to.have.status(200);'
        '});'
        'pm.test("Response has a result for {api_method}", function () {{'
        '    var jsonData = pm.response.json();'
        '    pm.expect(jsonData.result).to.exist;'
        '});'
    )


def validate_method_operation_match(json_method: str, method_name: str, operation: str) -> bool:
    """
    Validate that the method from the JSON file matches the expected
    method name and operation, accommodating various naming conventions.

    Args:
        json_method: Method name from the JSON file's 'method' field.
        method_name: Expected base method name (from directory structure).
        operation: Expected operation (from file name).

    Returns:
        True if it's a match, False otherwise.
    """
    # Case 1: Exact match for default operations.
    # e.g., json_method='version', method_name='version', operation='default'
    if json_method == method_name and operation == "default":
        return True

    # Case 2: For single-word methods with non-default operations where the operation
    # is not part of the method name itself. The context is given by the filename.
    # e.g., json_method='setprice', method_name='setprice', operation='buy'
    if json_method == method_name and operation != "default":
        return True

    # Case 3: Namespaced methods (e.g., 'task::enable_bch::init').
    # Checks if the JSON method is composed of the base method name and operation.
    # e.g., method_name='task::enable_bch', operation='init'
    if '::' in json_method and json_method == f"{method_name}::{operation}":
        return True

    # Case 4: Suffixed methods (e.g., 'orders_history_by_filter').
    # Checks if the method starts with the base name and ends with the operation.
    # e.g., method_name='orders_history', operation='by_filter'
    if '_' in json_method and json_method.startswith(method_name) and json_method.endswith(operation):
        return True

    # Case 5: Broader fallback for namespaced methods where simple concatenation doesn't match.
    # This preserves the original logic's flexibility.
    # e.g., json_method='streaming::enable_something', method_name='streaming', operation='enable_something'
    if '::' in json_method and json_method.startswith(method_name) and operation in json_method:
        return True

    # Case 6: A general, broad fallback for other potential matches.
    # This can be risky and match unintended combinations, but preserves original behavior.
    if method_name in json_method and operation in json_method and operation != 'default':
        return True

    return False


def validate_content_for_operation(json_data: Dict[str, Any], operation: str) -> bool:
    """
    Validate if the JSON content is appropriate for the given operation.
    
    For example, 'status' operations should not contain a large 'params' block.
    """
    method = json_data.get("method", "")
    params = json_data.get("params", {})
    
    # 'status' and 'cancel' requests typically only require a task_id
    is_status_or_cancel = 'status' in operation or 'cancel' in operation
    if is_status_or_cancel:
        # Should have 'task_id' but not other complex params
        if 'task_id' in json_data and len(params) <= 1:
            return True
        # Allow empty params for some status checks
        if not params and 'task_id' not in json_data:
            return True
        return False # Contains unexpected params
        
    # 'init' requests should generally have more than just a task_id
    if 'init' in operation:
        # It's okay for some init methods to have no params
        return True
        
    return True


def _folder_to_postman_item(folder: PostmanFolder, version: str) -> Dict:
    """Converts a PostmanFolder to a Postman item dictionary."""
    items = []
    
    # Add requests in the current folder
    for request in folder.requests:
        items.append(_request_to_postman_item(request, version))
    
    # Add subfolders
    for subfolder in folder.subfolders:
        items.append(_folder_to_postman_item(subfolder, version))
    
    return {
        "name": folder.name,
        "item": items,
        "description": folder.description
    }


def _request_to_postman_item(request: Any, version: str) -> Dict:
    """Converts a request object to a Postman item dictionary."""
    
    # Generate request description
    description = generate_request_description(
        api_method=request.method_name,
        method_name=request.method_name,
        operation=request.operation,
        version=version
    )
    
    # Generate test script
    test_script = generate_test_script(request.method_name)
    
    return {
        "name": request.name,
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
                "raw": _format_json_body(request.body),
                "options": {
                    "raw": {
                        "language": "json"
                    }
                }
            },
            "url": {
                "raw": "{{base_url}}",
                "host": ["{{base_url}}"]
            },
            "description": description
        },
        "response": [],
        "event": [
            {
                "listen": "test",
                "script": {
                    "exec": test_script,
                    "type": "text/javascript"
                }
            }
        ]
    }


def _format_json_body(body: Dict) -> str:
    """
    Format the JSON body for display in Postman.
    """
    try:
        # Use a simple dumps for the raw body to keep it compact
        return json.dumps(body)
    except (TypeError, ValueError):
        return "{}" 