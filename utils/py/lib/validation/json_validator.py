#!/usr/bin/env python3
"""
JSON Validator

Provides comprehensive JSON validation with schema support.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Union

from ..constants.enums import ValidationLevel
from ..utils.logging_utils import get_logger
from .results import ValidationResult


class JSONValidator:
    """
    Comprehensive JSON validation with schema support.
    
    Validates JSON syntax, structure, and content against schemas.
    """
    
    def __init__(self, level: ValidationLevel = ValidationLevel.NORMAL):
        self.level = level
        self.logger = get_logger("json-validator")
        
        # Predefined schemas for common structures
        self._schemas = self._load_predefined_schemas()
    
    def _load_predefined_schemas(self) -> Dict[str, Dict]:
        """Load predefined JSON schemas."""
        return {
            'postman_request': {
                'type': 'object',
                'required': ['method', 'url'],
                'properties': {
                    'method': {'type': 'string'},
                    'url': {'type': 'string'},
                    'body': {'type': 'object'},
                    'headers': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'key': {'type': 'string'},
                                'value': {'type': 'string'}
                            }
                        }
                    }
                }
            },
            'kdf_request': {
                'type': 'object',
                'required': ['method'],
                'properties': {
                    'method': {'type': 'string'},
                    'mmrpc': {'type': 'string'},
                    'params': {'type': 'object'},
                    'id': {'type': ['integer', 'string']},
                    'userpass': {'type': 'string'}
                }
            },
            'kdf_response': {
                'type': 'object',
                'properties': {
                    'mmrpc': {'type': 'string'},
                    'result': {'type': 'object'},
                    'error': {'type': 'string'},
                    'id': {'type': ['integer', 'string']}
                }
            },
            'openapi_path': {
                'type': 'object',
                'properties': {
                    'operationId': {'type': 'string'},
                    'summary': {'type': 'string'},
                    'description': {'type': 'string'},
                    'parameters': {'type': 'array'},
                    'responses': {'type': 'object'}
                }
            }
        }
    
    def validate_json_string(self, json_string: str, schema_name: str = None) -> ValidationResult:
        """Validate JSON string with optional schema."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Parse JSON
        try:
            data = json.loads(json_string)
            result.data = data
        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON syntax: {e}")
            return result
        
        # Validate against schema if provided
        if schema_name:
            schema_result = self.validate_against_schema(data, schema_name)
            result.merge(schema_result)
        
        # General validation
        general_result = self._validate_general_structure(data)
        result.merge(general_result)
        
        return result
    
    def validate_json_file(self, file_path: Union[str, Path], schema_name: str = None) -> ValidationResult:
        """Validate JSON file with optional schema."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Validate content
            content_result = self.validate_json_string(content, schema_name)
            result.merge(content_result)
            result.data = content_result.data
            
        except FileNotFoundError:
            result.add_error(f"File not found: {file_path}")
        except PermissionError:
            result.add_error(f"Permission denied: {file_path}")
        except Exception as e:
            result.add_error(f"Error reading file {file_path}: {e}")
        
        return result
    
    def validate_against_schema(self, data: Any, schema_name: str) -> ValidationResult:
        """Validate data against a predefined schema."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if schema_name not in self._schemas:
            result.add_warning(f"Unknown schema: {schema_name}")
            return result
        
        schema = self._schemas[schema_name]
        validation_result = self._validate_schema(data, schema, "root")
        result.merge(validation_result)
        
        return result
    
    def _validate_schema(self, data: Any, schema: Dict, path: str) -> ValidationResult:
        """Recursively validate data against schema."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Check type
        if 'type' in schema:
            type_result = self._validate_type(data, schema['type'], path)
            result.merge(type_result)
        
        # Check required fields for objects
        if isinstance(data, dict) and 'required' in schema:
            for field in schema['required']:
                if field not in data:
                    result.add_error(f"Missing required field '{field}' at {path}")
        
        # Validate object properties
        if isinstance(data, dict) and 'properties' in schema:
            for key, value in data.items():
                if key in schema['properties']:
                    prop_result = self._validate_schema(
                        value, schema['properties'][key], f"{path}.{key}"
                    )
                    result.merge(prop_result)
                elif self.level == ValidationLevel.STRICT:
                    result.add_warning(f"Unknown property '{key}' at {path}")
        
        # Validate array items
        if isinstance(data, list) and 'items' in schema:
            for i, item in enumerate(data):
                item_result = self._validate_schema(
                    item, schema['items'], f"{path}[{i}]"
                )
                result.merge(item_result)
        
        return result
    
    def _validate_type(self, data: Any, expected_type: Union[str, List[str]], path: str) -> ValidationResult:
        """Validate data type."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Handle multiple allowed types
        if isinstance(expected_type, list):
            type_valid = any(
                self._check_type_match(data, t) for t in expected_type
            )
            if not type_valid:
                result.add_error(
                    f"Type mismatch at {path}: expected one of {expected_type}, "
                    f"got {self._get_json_type(data)}"
                )
        else:
            if not self._check_type_match(data, expected_type):
                result.add_error(
                    f"Type mismatch at {path}: expected {expected_type}, "
                    f"got {self._get_json_type(data)}"
                )
        
        return result
    
    def _check_type_match(self, data: Any, expected_type: str) -> bool:
        """Check if data matches expected JSON type."""
        json_type = self._get_json_type(data)
        return json_type == expected_type
    
    def _get_json_type(self, data: Any) -> str:
        """Get JSON type name for data."""
        if isinstance(data, bool):
            return "boolean"
        elif isinstance(data, int):
            return "integer"
        elif isinstance(data, float):
            return "number"
        elif isinstance(data, str):
            return "string"
        elif isinstance(data, list):
            return "array"
        elif isinstance(data, dict):
            return "object"
        elif data is None:
            return "null"
        return "unknown"
    
    def _validate_general_structure(self, data: Any) -> ValidationResult:
        """Perform general validation on JSON structure."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Example check: excessive depth
        max_depth = 20
        depth = self._calculate_depth(data)
        if depth > max_depth:
            result.add_warning(f"JSON depth ({depth}) exceeds threshold ({max_depth})")
            
        return result
    
    def _calculate_depth(self, data: Any, current_depth: int = 0) -> int:
        """Calculate nesting depth of a JSON object."""
        if isinstance(data, dict):
            if not data:
                return current_depth + 1
            return max(self._calculate_depth(v, current_depth + 1) for v in data.values())
        elif isinstance(data, list):
            if not data:
                return current_depth + 1
            return max(self._calculate_depth(i, current_depth + 1) for i in data)
        else:
            return current_depth
    
    def add_custom_schema(self, name: str, schema: Dict):
        """Add or update a custom schema."""
        self._schemas[name] = schema
    
    def get_available_schemas(self) -> List[str]:
        """Get a list of available schema names."""
        return list(self._schemas.keys()) 