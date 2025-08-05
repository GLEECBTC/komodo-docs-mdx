#!/usr/bin/env python3
"""
Method Analyzer

Analyzes KDF method information to extract parameters, types, and generate documentation.
"""

import re
import json
from typing import Dict, List, Any, Optional

from ..constants import ParameterAnalysis, MethodAnalysis


class MethodAnalyzer:
    """Analyzes method implementations to extract parameter information."""
    
    def __init__(self):
        self.rust_type_mapping = {
            'String': 'string',
            'str': 'string', 
            '&str': 'string',
            'i32': 'integer',
            'i64': 'integer',
            'u32': 'integer',
            'u64': 'integer',
            'f32': 'float',
            'f64': 'float',
            'bool': 'boolean',
            'Vec': 'array',
            'Option': 'optional',
            'HashMap': 'object',
            'BTreeMap': 'object',
            'serde_json::Value': 'object',
            'Value': 'object',
        }
    
    def parse_rust_struct(self, struct_definition: str) -> List[ParameterAnalysis]:
        """Parse a Rust struct definition to extract parameters."""
        parameters = []
        
        # Extract struct body
        struct_body_match = re.search(r'\{([^}]*)\}', struct_definition, re.DOTALL)
        if not struct_body_match:
            return parameters
        
        struct_body = struct_body_match.group(1)
        
        # Parse individual fields
        field_pattern = r'(?:#\[[^\]]*\])?\s*(?:pub\s+)?(\w+):\s*([^,\n]+)(?:,|\n|$)'
        fields = re.findall(field_pattern, struct_body, re.MULTILINE)
        
        for field_name, field_type in fields:
            if field_name.startswith('//') or field_name.startswith('#'):
                continue
                
            param = self.parse_rust_type(field_name, field_type.strip())
            if param:
                parameters.append(param)
        
        return parameters
    
    def parse_rust_type(self, field_name: str, rust_type: str) -> Optional[ParameterAnalysis]:
        """Parse a Rust type definition into a Parameter."""
        # Clean up the type string
        rust_type = rust_type.strip().rstrip(',')
        
        # Determine if optional
        is_optional = rust_type.startswith('Option<')
        if is_optional:
            # Extract inner type from Option<T>
            inner_type_match = re.search(r'Option<(.+)>', rust_type)
            if inner_type_match:
                rust_type = inner_type_match.group(1)
        
        # Determine if array/vector
        is_array = rust_type.startswith('Vec<') or rust_type.startswith('Array<')
        if is_array:
            # Extract inner type from Vec<T>
            inner_type_match = re.search(r'Vec<(.+)>|Array<(.+)>', rust_type)
            if inner_type_match:
                rust_type = inner_type_match.group(1) or inner_type_match.group(2)
        
        # Map Rust type to documentation type
        doc_type = self.map_rust_type_to_doc_type(rust_type)
        
        # Generate description based on field name
        description = self.generate_field_description(field_name, doc_type, is_array)
        
        return ParameterAnalysis(
            name=field_name,
            param_type=doc_type,
            required=not is_optional,
            description=description,
            is_array=is_array,
            is_object=doc_type == 'object'
        )
    
    def map_rust_type_to_doc_type(self, rust_type: str) -> str:
        """Map Rust type to documentation type."""
        # Direct mapping
        if rust_type in self.rust_type_mapping:
            return self.rust_type_mapping[rust_type]
        
        # Pattern matching
        if 'String' in rust_type or 'str' in rust_type:
            return 'string'
        elif any(int_type in rust_type for int_type in ['i32', 'i64', 'u32', 'u64', 'usize']):
            return 'integer'
        elif any(float_type in rust_type for float_type in ['f32', 'f64']):
            return 'float'
        elif 'bool' in rust_type:
            return 'boolean'
        elif 'Vec<' in rust_type or 'Array<' in rust_type:
            return 'array'
        elif any(obj_type in rust_type for obj_type in ['HashMap', 'BTreeMap', 'Value']):
            return 'object'
        else:
            # Check if it's a custom struct/enum
            if rust_type[0].isupper():
                return 'object'
            else:
                return 'string'  # Default fallback
    
    def generate_field_description(self, field_name: str, field_type: str, is_array: bool) -> str:
        """Generate a description for a field based on its name and type."""
        # Convert snake_case to readable text
        readable_name = field_name.replace('_', ' ').title()
        
        # Common field name patterns
        if 'coin' in field_name.lower():
            return f"The {readable_name.lower()} identifier or symbol"
        elif 'address' in field_name.lower():
            return f"The {readable_name.lower()} for the operation"
        elif 'amount' in field_name.lower() or 'volume' in field_name.lower():
            return f"The {readable_name.lower()} for the transaction"
        elif 'price' in field_name.lower():
            return f"The {readable_name.lower()} for the order"
        elif 'id' in field_name.lower():
            return f"The unique identifier for {field_name.replace('_id', '').replace('id', '').replace('_', ' ').strip()}"
        elif 'uuid' in field_name.lower():
            return f"The UUID for {field_name.replace('_uuid', '').replace('uuid', '').replace('_', ' ').strip()}"
        elif 'timeout' in field_name.lower():
            return f"Timeout value in seconds for {field_name.replace('_timeout', '').replace('timeout', '').replace('_', ' ').strip()}"
        elif 'enabled' in field_name.lower() or field_type == 'boolean':
            return f"Whether {readable_name.lower().replace(' enabled', '')} is enabled"
        elif 'confirmations' in field_name.lower():
            return f"Number of {readable_name.lower()} required"
        elif 'password' in field_name.lower():
            return f"The {readable_name.lower()} for authentication"
        elif 'pubkey' in field_name.lower():
            return f"The {readable_name.lower()} in hexadecimal format"
        elif is_array:
            return f"Array of {readable_name.lower().rstrip('s')} objects"
        elif field_type == 'object':
            return f"Object containing {readable_name.lower()} information"
        else:
            return f"The {readable_name.lower()} parameter"
    
    def extract_error_types(self, method_info: Dict) -> List[str]:
        """Extract error types from method implementation."""
        error_types = []
        
        # Common KDF error patterns
        common_errors = [
            "NoSuchCoin",
            "InvalidParam",
            "InternalError",
            "Transport",
            "Timeout",
            "InvalidAddress",
            "InsufficientBalance",
            "CoinIsNotActive",
            "RpcError"
        ]
        
        # Scan implementation files for error patterns
        for impl in method_info.get('implementations', []):
            if 'signature' in impl:
                signature = impl['signature']['signature']
                # Look for error types in the signature
                for error in common_errors:
                    if error in signature:
                        error_types.append(error)
        
        # Add some default errors if none found
        if not error_types:
            error_types = ["InternalError", "InvalidParam", "Transport"]
        
        return list(set(error_types))  # Remove duplicates
    
    def generate_example_request(self, method_name: str, parameters: List[ParameterAnalysis]) -> Dict:
        """Generate an example request based on parameters."""
        params = {}
        
        for param in parameters:
            if param.name in ['userpass', 'mmrpc']:
                continue  # Skip standard fields
                
            example_value = self.generate_example_value(param)
            if example_value is not None:
                params[param.name] = example_value
        
        return {
            "userpass": "RPC_UserP@SSW0RD",
            "method": method_name,
            "mmrpc": "2.0",
            "params": params
        }
    
    def generate_example_value(self, param: ParameterAnalysis) -> Any:
        """Generate an example value for a parameter."""
        if param.param_type == 'string':
            if 'coin' in param.name.lower():
                return "BTC"
            elif 'address' in param.name.lower():
                return "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
            elif 'id' in param.name.lower() or 'uuid' in param.name.lower():
                return "12345678-1234-1234-1234-123456789012"
            else:
                return "example_value"
        elif param.param_type == 'integer':
            if 'timeout' in param.name.lower():
                return 60
            elif 'confirmations' in param.name.lower():
                return 1
            else:
                return 10
        elif param.param_type == 'float':
            if 'amount' in param.name.lower() or 'volume' in param.name.lower():
                return 1.5
            elif 'price' in param.name.lower():
                return 0.001
            else:
                return 1.0
        elif param.param_type == 'boolean':
            return False  # Default to false for optional booleans
        elif param.param_type == 'array':
            return ["example_item"]
        elif param.param_type == 'object':
            return {"key": "value"}
        else:
            return "example_value"
    
    def analyze_method(self, method_name: str, method_info: Dict) -> MethodAnalysis:
        """Perform complete analysis of a method."""
        print(f"Analyzing method: {method_name}")
        
        request_params = []
        response_params = []
        source_files = []
        
        # Analyze struct definitions
        for struct_info in method_info.get('structs', []):
            struct_def = struct_info['struct_definition']
            source_files.append(struct_def['file_path'] if 'file_path' in struct_def else struct_info['file_path'])
            
            struct_name = struct_def.get('struct_name', '')
            params = self.parse_rust_struct(struct_def.get('definition', ''))
            
            if 'request' in struct_name.lower() or 'params' in struct_name.lower():
                request_params.extend(params)
            elif 'response' in struct_name.lower() or 'result' in struct_name.lower():
                response_params.extend(params)
        
        # If no structs found, generate basic parameters based on method name
        if not request_params:
            request_params = self.generate_default_parameters(method_name)
        
        if not response_params:
            response_params = self.generate_default_response_parameters(method_name)
        
        # Extract error types
        error_types = self.extract_error_types(method_info)
        
        # Generate example
        example_request = self.generate_example_request(method_name, request_params)
        examples = [example_request]
        
        # Generate description
        description = f"The `{method_name}` method provides functionality for {method_name.replace('_', ' ').replace('::', ' ')} operations."
        
        return MethodAnalysis(
            method_name=method_name,
            description=description,
            request_params=request_params,
            response_params=response_params,
            error_types=error_types,
            examples=examples,
            source_files=list(set(source_files))
        )
    
    def generate_default_parameters(self, method_name: str) -> List[ParameterAnalysis]:
        """Generate default parameters based on method name patterns."""
        params = []
        
        # Common parameters based on method patterns
        if 'enable' in method_name:
            params.append(ParameterAnalysis("coin", "string", True, description="The coin to enable"))
            if 'task' in method_name:
                params.append(ParameterAnalysis("task_id", "integer", True, description="The task identifier"))
        elif 'cancel' in method_name and 'task' in method_name:
            params.append(ParameterAnalysis("task_id", "integer", True, description="The task identifier to cancel"))
        elif 'status' in method_name and 'task' in method_name:
            params.append(ParameterAnalysis("task_id", "integer", True, description="The task identifier to check"))
        elif 'withdraw' in method_name:
            params.extend([
                ParameterAnalysis("coin", "string", True, description="The coin to withdraw"),
                ParameterAnalysis("to", "string", True, description="The destination address"),
                ParameterAnalysis("amount", "string", True, description="The amount to withdraw")
            ])
        elif 'balance' in method_name:
            params.append(ParameterAnalysis("coin", "string", True, description="The coin to get balance for"))
        elif 'stream' in method_name:
            params.append(ParameterAnalysis("stream_id", "string", False, description="Optional stream identifier"))
        
        return params
    
    def generate_default_response_parameters(self, method_name: str) -> List[ParameterAnalysis]:
        """Generate default response parameters based on method name patterns."""
        params = []
        
        # Common response patterns
        if 'task' in method_name:
            if 'init' in method_name:
                params.append(ParameterAnalysis("task_id", "integer", True, description="The initialized task identifier"))
            elif 'status' in method_name:
                params.extend([
                    ParameterAnalysis("status", "string", True, description="Current task status"),
                    ParameterAnalysis("task_id", "integer", True, description="The task identifier")
                ])
            elif 'cancel' in method_name:
                params.append(ParameterAnalysis("result", "string", True, description="Cancellation result"))
        elif 'balance' in method_name:
            params.extend([
                ParameterAnalysis("coin", "string", True, description="The coin symbol"),
                ParameterAnalysis("balance", "string", True, description="The available balance"),
                ParameterAnalysis("unconfirmed_balance", "string", True, description="The unconfirmed balance")
            ])
        elif 'withdraw' in method_name:
            params.extend([
                ParameterAnalysis("tx_hex", "string", True, description="The transaction in hexadecimal format"),
                ParameterAnalysis("tx_hash", "string", True, description="The transaction hash")
            ])
        else:
            # Generic success response
            params.append(ParameterAnalysis("result", "string", True, description="Operation result"))
        
        return params 