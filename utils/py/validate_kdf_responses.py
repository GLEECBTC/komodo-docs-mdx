#!/usr/bin/env python3
"""
KDF Responses Validation Script

Validates the structure and content of KDF response JSON files to ensure
they follow the expected format for the KdfResponses component.

Usage:
    python validate_kdf_responses.py [--fix-minor-issues]

Features:
- Validates JSON structure and syntax
- Checks required fields and data types  
- Validates response categories (success/error)
- Ensures consistent naming conventions
- Provides detailed error reporting
- Optional auto-fix for minor formatting issues
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import argparse
import re


class ValidationError:
    def __init__(self, file_path: str, error_type: str, message: str, location: str = ""):
        self.file_path = file_path
        self.error_type = error_type  
        self.message = message
        self.location = location

    def __str__(self):
        location_str = f" [{self.location}]" if self.location else ""
        return f"[{self.error_type}] {self.file_path}{location_str}: {self.message}"


class KdfResponseValidator:
    def __init__(self, fix_minor_issues: bool = False):
        self.fix_minor_issues = fix_minor_issues
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []
        self.fixes_applied: List[str] = []
        
        # Valid response types
        self.valid_response_types = {'success', 'error'}
        
        # Valid request key pattern (alphanumeric, camelCase/PascalCase)
        self.request_key_pattern = re.compile(r'^[A-Z][a-zA-Z0-9]*$')

    def validate_all(self) -> Tuple[bool, List[ValidationError], List[ValidationError]]:
        """Validate all KDF response files."""
        base_path = Path('src/data/kdf_responses')
        
        if not base_path.exists():
            self.errors.append(ValidationError(
                str(base_path), 
                "MISSING_DIRECTORY",
                "KDF responses directory does not exist"
            ))
            return False, self.errors, self.warnings
            
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
            self._validate_file_structure(file_path, data, version)
            
        except Exception as e:
            self.errors.append(ValidationError(
                str(file_path),
                "FILE_ERROR",
                f"Error reading file: {str(e)}"
            ))

    def _validate_file_structure(self, file_path: Path, data: Dict, version: str):
        """Validate the overall structure of a response file."""
        if not isinstance(data, dict):
            self.errors.append(ValidationError(
                str(file_path),
                "INVALID_STRUCTURE",
                "Root element must be an object/dictionary"
            ))
            return
            
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
            self._validate_response_structure(file_path, request_key, responses)

    def _validate_request_key(self, file_path: Path, request_key: str):
        """Validate request key naming convention."""
        if not isinstance(request_key, str):
            self.errors.append(ValidationError(
                str(file_path),
                "INVALID_KEY_TYPE",
                f"Request key must be string, got {type(request_key).__name__}",
                request_key
            ))
            return
            
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
        # Load request data
        requests_by_version = {}
        for version in ['legacy', 'v2']:
            requests_path = Path(f'src/data/requests/{version}')
            if requests_path.exists():
                requests_by_version[version] = self._load_request_keys(requests_path)

        # Load response data  
        responses_by_version = {}
        for version in ['legacy', 'v2']:
            responses_path = Path(f'src/data/kdf_responses/{version}')
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
                    f"src/data/kdf_responses/{version}/",
                    "MISSING_RESPONSE",
                    f"Request '{key}' exists but has no corresponding response data",
                    f"{version}/{key}"
                ))
            
            # Responses without requests
            missing_requests = response_keys - request_keys
            for key in missing_requests:
                self.warnings.append(ValidationError(
                    f"src/data/requests/{version}/",
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
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Validate KDF response JSON files')
    parser.add_argument('--fix-minor-issues', action='store_true', 
                       help='Automatically fix minor formatting issues')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed output including warnings')
    
    args = parser.parse_args()
    
    # Change to repo root directory
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    os.chdir(repo_root)
    
    print("🔍 Validating KDF response files...")
    print(f"📂 Working directory: {os.getcwd()}")
    
    validator = KdfResponseValidator(fix_minor_issues=args.fix_minor_issues)
    success, errors, warnings = validator.validate_all()
    
    # Report results
    if errors:
        print(f"\n❌ Validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"  {error}")
    
    if warnings and args.verbose:
        print(f"\n⚠️  {len(warnings)} warning(s):")
        for warning in warnings:
            print(f"  {warning}")
            
    if validator.fixes_applied:
        print(f"\n🔧 Applied {len(validator.fixes_applied)} fix(es):")
        for fix in validator.fixes_applied:
            print(f"  {fix}")
    
    if success:
        if warnings:
            print(f"\n✅ Validation passed with {len(warnings)} warning(s)")
        else:
            print("\n✅ All validations passed!")
        return 0
    else:
        print(f"\n❌ Validation failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())