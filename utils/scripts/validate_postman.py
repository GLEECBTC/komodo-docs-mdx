#!/usr/bin/env python3
"""
Postman collection validator script.
Validates that the generated Postman collections are properly formatted
and contain the expected structure for KDF API testing.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional


def validate_collection_structure(collection: Dict) -> List[str]:
    """Validate basic Postman collection structure."""
    errors = []
    
    # Check required top-level fields
    required_fields = ['info', 'item']
    for field in required_fields:
        if field not in collection:
            errors.append(f"Missing required field: {field}")
    
    # Validate info section
    if 'info' in collection:
        info = collection['info']
        if 'name' not in info:
            errors.append("Collection info missing 'name' field")
        if 'schema' not in info:
            errors.append("Collection info missing 'schema' field")
    
    # Validate items structure
    if 'item' in collection:
        if not isinstance(collection['item'], list):
            errors.append("Collection 'item' should be a list")
        elif len(collection['item']) == 0:
            errors.append("Collection has no items")
    
    return errors


def validate_environment_structure(environment: Dict) -> List[str]:
    """Validate Postman environment structure."""
    errors = []
    
    # Check required fields
    required_fields = ['info', 'variable']
    for field in required_fields:
        if field not in environment:
            errors.append(f"Missing required field: {field}")
    
    # Validate variables
    if 'variable' in environment:
        variables = environment['variable']
        if not isinstance(variables, list):
            errors.append("Environment 'variable' should be a list")
        else:
            # Check for required variables
            var_keys = [var.get('key') for var in variables]
            required_vars = ['base_url', 'userpass']
            for req_var in required_vars:
                if req_var not in var_keys:
                    errors.append(f"Missing required variable: {req_var}")
    
    return errors


def validate_kdf_methods(collection: Dict) -> List[str]:
    """Validate that collection contains expected KDF methods."""
    errors = []
    
    # Extract all method names from requests
    methods = set()
    
    def extract_methods_recursive(items):
        for item in items:
            if 'request' in item:
                # Try to extract method from request body
                request = item['request']
                if 'body' in request and 'raw' in request['body']:
                    try:
                        body = json.loads(request['body']['raw'])
                        if 'method' in body:
                            methods.add(body['method'])
                    except json.JSONDecodeError:
                        pass
            
            # Recursively check nested items
            if 'item' in item:
                extract_methods_recursive(item['item'])
    
    if 'item' in collection:
        extract_methods_recursive(collection['item'])
    
    # Check for some expected KDF methods
    expected_methods = [
        'task::enable_eth::init',
        'task::enable_eth::status',
        'task::enable_utxo::init'
    ]
    
    for method in expected_methods:
        if method not in methods:
            errors.append(f"Expected KDF method not found: {method}")
    
    if len(methods) == 0:
        errors.append("No KDF methods found in collection")
    
    return errors


def validate_file(file_path: Path) -> Dict[str, List[str]]:
    """Validate a single JSON file."""
    result = {
        'file': str(file_path),
        'errors': [],
        'warnings': []
    }
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        result['errors'].append(f"Invalid JSON: {e}")
        return result
    except Exception as e:
        result['errors'].append(f"Error reading file: {e}")
        return result
    
    # Determine file type and validate accordingly
    if file_path.name.endswith('_collection.json') or 'collection' in file_path.name:
        # Postman collection
        result['errors'].extend(validate_collection_structure(data))
        result['errors'].extend(validate_kdf_methods(data))
    elif file_path.name.endswith('_environment.json') or 'environment' in file_path.name:
        # Postman environment
        result['errors'].extend(validate_environment_structure(data))
    else:
        result['warnings'].append("Unknown file type, performing basic JSON validation only")
    
    return result


def main():
    """Main validation function."""
    if len(sys.argv) > 1:
        # Validate specific files
        files_to_check = [Path(arg) for arg in sys.argv[1:]]
    else:
        # Default: validate all generated Postman files
        postman_dir = Path(__file__).parent.parent.parent / 'postman' / 'generated'
        if not postman_dir.exists():
            print(f"Error: Postman generated directory not found: {postman_dir}")
            return 1
        
        files_to_check = list(postman_dir.glob('**/*.json'))
    
    if not files_to_check:
        print("No JSON files found to validate")
        return 1
    
    total_errors = 0
    total_warnings = 0
    
    print("🧪 Validating Postman Collections and Environments")
    print("=" * 50)
    
    for file_path in files_to_check:
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            total_errors += 1
            continue
        
        result = validate_file(file_path)
        
        # Display results
        status = "✅" if not result['errors'] else "❌"
        print(f"{status} {result['file']}")
        
        if result['errors']:
            total_errors += len(result['errors'])
            for error in result['errors']:
                print(f"   ❌ {error}")
        
        if result['warnings']:
            total_warnings += len(result['warnings'])
            for warning in result['warnings']:
                print(f"   ⚠️  {warning}")
        
        if not result['errors'] and not result['warnings']:
            print("   ✅ All validations passed")
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Validation Summary:")
    print(f"   Files checked: {len(files_to_check)}")
    print(f"   Total errors: {total_errors}")
    print(f"   Total warnings: {total_warnings}")
    
    if total_errors > 0:
        print("\n❌ Validation failed with errors")
        return 1
    else:
        print("\n✅ All validations passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
