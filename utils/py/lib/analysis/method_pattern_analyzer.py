#!/usr/bin/env python3
"""
Method Pattern Analyzer

Analyzes KDF method patterns from Rust source code and existing documentation.
"""

from pathlib import Path
from typing import Dict, List, Any
import re

from .enhanced_analyzer import EnhancedRepositoryAnalyzer, ParameterInfo
from ..mdx.mdx_local_scanner import ExistingDocsScanner
from ..constants import EnhancedKomodoConfig


class MethodPatternAnalyzer:
    """
    Analyzes KDF method patterns from the actual Rust source code and existing documentation.
    Uses the LocalKDFScanner as the authoritative source for parameter structures.
    """
    
    def __init__(self, enhanced_analyzer=None, repo_path=None, existing_docs_scanner=None):
        self.enhanced_analyzer = enhanced_analyzer
        self.repo_path = repo_path
        self.existing_docs_scanner = existing_docs_scanner
        self.local_scanner = None
        self.method_patterns = self._build_fallback_patterns()
        
        # Initialize local scanner for Rust code analysis
        try:
            from ..rust.scanner import KDFScanner
            
            if repo_path:
                actual_repo_path = Path(repo_path)
            else:
                config = EnhancedKomodoConfig()
                actual_repo_path = config.directories.kdf_repo_path
            
            self.local_scanner = KDFScanner(repo_path=actual_repo_path)
            
            # Verify repository is available
            if self.local_scanner.repo_path.exists():
                print(f"✅ Local KDF repository found at: {self.local_scanner.repo_path}")
            else:
                print(f"⚠️  Local KDF repository not found at: {self.local_scanner.repo_path}")
                print("   Rust code analysis will be unavailable - falling back to pattern matching")
                self.local_scanner = None
                
        except ImportError as e:
            print(f"Warning: Could not import KDFScanner: {e}")
            self.local_scanner = None
        except Exception as e:
            print(f"Warning: Failed to initialize KDFScanner: {e}")
            self.local_scanner = None
    
    def _build_fallback_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Build fallback patterns for when Rust analysis isn't available."""
        return {
            # Generic task init patterns (fallback only)
            "task::*::init": {
                "parameters": [
                    {"name": "userpass", "type": "string", "required": True, "description": "Password for authentication"}
                ],
                "response": [
                    {"name": "task_id", "type": "integer", "description": "The identifier of the initialized task"}
                ],
                "errors": ["InvalidUserpass", "InternalError", "InvalidRequest"]
            },
            
            # Generic task cancel patterns
            "task::*::cancel": {
                "parameters": [
                    {"name": "task_id", "type": "integer", "required": True, "description": "The identifier of the task to cancel"},
                    {"name": "userpass", "type": "string", "required": True, "description": "Password for authentication"}
                ],
                "response": [
                    {"name": "result", "type": "string", "description": "Result of the cancellation operation"}
                ],
                "errors": ["InvalidUserpass", "InternalError", "NoSuchTask", "InvalidRequest"]
            },
            
            # Generic task status patterns
            "task::*::status": {
                "parameters": [
                    {"name": "task_id", "type": "integer", "required": True, "description": "The identifier of the task to query"},
                    {"name": "userpass", "type": "string", "required": True, "description": "Password for authentication"}
                ],
                "response": [
                    {"name": "status", "type": "string", "description": "Current status of the task"},
                    {"name": "details", "type": "object", "description": "Detailed information about the task"}
                ],
                "errors": ["InvalidUserpass", "InternalError", "NoSuchTask", "InvalidRequest"]
            },
            
            # Generic task user_action patterns
            "task::*::user_action": {
                "parameters": [
                    {"name": "task_id", "type": "integer", "required": True, "description": "The identifier of the task"},
                    {"name": "action", "type": "object", "required": True, "description": "The user action to perform"},
                    {"name": "userpass", "type": "string", "required": True, "description": "Password for authentication"}
                ],
                "response": [
                    {"name": "result", "type": "string", "description": "Result of the user action"}
                ],
                "errors": ["InvalidUserpass", "InternalError", "NoSuchTask", "InvalidRequest", "InvalidAction"]
            }
        }
    
    def infer_parameters_from_pattern(self, method_name: str) -> List[Dict[str, Any]]:
        """
        Infer parameters using multiple sources in priority order:
        1. Existing documentation patterns (highest priority)
        2. Rust code analysis 
        3. Enhanced analyzer patterns
        4. Basic fallback patterns
        """
        # First priority: Check existing documentation patterns
        if self.existing_docs_scanner:
            pattern = self.existing_docs_scanner.get_pattern_for_method(method_name)
            if pattern and pattern.parameters:
                return self._convert_existing_docs_parameters(pattern.parameters)
        
        # Second priority: Extract parameters from actual Rust code
        if self.local_scanner:
            try:
                method_details = self.local_scanner.extract_method_details(method_name)
                if method_details.parameters:
                    return self._convert_rust_parameters(method_details.parameters)
            except Exception as e:
                # If Rust analysis fails, continue to fallbacks
                pass
        
        # Third priority: Use enhanced analyzer's pattern analysis
        if self.enhanced_analyzer:
            try:
                category = self.enhanced_analyzer._classify_method_category(method_name)
                parameters = self.enhanced_analyzer._extract_method_parameters(method_name, category, "v2")
                if parameters:
                    return self._convert_enhanced_parameters(parameters)
            except Exception as e:
                # If enhanced analysis fails, continue to fallbacks
                pass
        
        # Fourth priority: Use fallback pattern matching
        return self._infer_from_fallback_patterns(method_name)
    
    def infer_response_from_pattern(self, method_name: str) -> List[Dict[str, Any]]:
        """
        Infer response parameters using multiple sources in priority order.
        """
        # First priority: Check existing documentation patterns
        if self.existing_docs_scanner:
            pattern = self.existing_docs_scanner.get_pattern_for_method(method_name)
            if pattern and pattern.response_parameters:
                return self._convert_existing_docs_parameters(pattern.response_parameters)
        
        # Second priority: Extract response from actual Rust code
        if self.local_scanner:
            try:
                method_details = self.local_scanner.extract_method_details(method_name)
                if method_details.response_type:
                    return [{"name": "result", "type": method_details.response_type, "description": "The method result"}]
            except Exception as e:
                # If Rust analysis fails, continue to fallbacks
                pass
        
        # Third priority: Use enhanced analyzer's response generation
        if self.enhanced_analyzer:
            try:
                response_data = self.enhanced_analyzer._generate_method_response(method_name, "v2")
                if response_data and "result" in response_data:
                    return self._convert_response_to_parameters(response_data["result"])
            except Exception as e:
                # If enhanced analysis fails, continue to fallbacks
                pass
        
        # Fourth priority: Use fallback pattern matching
        return self._infer_response_from_fallback_patterns(method_name)
    
    def _convert_existing_docs_parameters(self, existing_params) -> List[Dict[str, Any]]:
        """Convert parameters from existing documentation patterns."""
        converted = []
        for param in existing_params:
            converted.append({
                "name": param.name,
                "type": param.type,
                "required": param.required,
                "default": param.default,
                "description": param.description
            })
        return converted
    
    def _convert_rust_parameters(self, rust_params: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert parameters extracted from Rust code to generator format."""
        converted = []
        for param in rust_params:
            converted.append({
                "name": param.get("name", ""),
                "type": self._rust_type_to_api_type(param.get("type", "String")),
                "required": param.get("required", True),
                "default": param.get("default"),
                "description": param.get("description", f"Parameter {param.get('name', 'unknown')}")
            })
        return converted
    
    def _rust_type_to_api_type(self, rust_type: str) -> str:
        """Convert Rust types to API documentation types."""
        type_mapping = {
            "String": "string",
            "str": "string", 
            "bool": "boolean",
            "u64": "integer",
            "i64": "integer",
            "u32": "integer",
            "i32": "integer",
            "f64": "number",
            "f32": "number",
            "Vec<String>": "array of strings",
            "Vec<u64>": "array of integers",
            "Option<String>": "string (optional)",
            "Option<bool>": "boolean (optional)",
            "Option<u64>": "integer (optional)",
            "serde_json::Value": "object",
            "Value": "object"
        }
        
        # Handle generic types
        if rust_type.startswith("Vec<"):
            inner_type = rust_type[4:-1]  # Extract inner type from Vec<T>
            mapped_inner = type_mapping.get(inner_type, inner_type.lower())
            return f"array of {mapped_inner}"
        
        if rust_type.startswith("Option<"):
            inner_type = rust_type[7:-1]
            mapped_inner = type_mapping.get(inner_type, inner_type.lower())
            return f"{mapped_inner} (optional)"
            
        return type_mapping.get(rust_type, rust_type.lower())
    
    def _convert_enhanced_parameters(self, enhanced_params: List) -> List[Dict[str, Any]]:
        """Convert parameters from enhanced analyzer to a standardized dict format."""
        converted = []
        for param in enhanced_params:
            if isinstance(param, ParameterInfo):
                converted.append({
                    "name": param.name,
                    "type": param.type,
                    "required": param.required,
                    "default": param.default,
                    "description": param.description
                })
            elif isinstance(param, dict):
                 converted.append(param)
        return converted
    
    def _infer_from_fallback_patterns(self, method_name: str) -> List[Dict[str, Any]]:
        """Infer parameters using basic wildcard pattern matching."""
        for pattern, data in self.method_patterns.items():
            if self._matches_wildcard_pattern(method_name, pattern):
                return self._add_method_specific_params(method_name, data.get("parameters", []))
        return []
    
    def _infer_response_from_fallback_patterns(self, method_name: str) -> List[Dict[str, Any]]:
        """Infer response fields using basic wildcard pattern matching."""
        for pattern, data in self.method_patterns.items():
            if self._matches_wildcard_pattern(method_name, pattern):
                return data.get("response", [])
        return []
    
    def _convert_response_to_parameters(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recursively convert a response object into a list of parameters."""
        def extract_fields(data, prefix=""):
            params = []
            if isinstance(data, dict):
                for key, value in data.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, (dict, list)):
                        params.extend(extract_fields(value, full_key))
                    else:
                        params.append({
                            "name": full_key,
                            "type": self._infer_type_from_value(value),
                            "description": f"The {key.replace('_', ' ')} of the result."
                        })
            elif isinstance(data, list) and data:
                # Handle array of objects
                if isinstance(data[0], dict):
                     params.extend(extract_fields(data[0], f"{prefix}[]"))
                else: # Handle array of simple types
                    params.append({
                        "name": f"{prefix}[]",
                        "type": f"array of {self._infer_type_from_value(data[0])}s",
                        "description": f"An array of results."
                    })
            return params
            
        return extract_fields(response_data)
        
    def _infer_type_from_value(self, value: Any) -> str:
        """Infer API type from a Python value."""
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        return "any"
        
    def _matches_wildcard_pattern(self, method_name: str, pattern: str) -> bool:
        """Check if a method name matches a simple wildcard pattern."""
        parts = pattern.split('*')
        regex_pattern = '.*'.join(map(re.escape, parts))
        return re.fullmatch(regex_pattern, method_name) is not None
        
    def _add_method_specific_params(self, method_name: str, base_params: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add method-specific parameters based on its name."""
        params = list(base_params) # Make a copy
        
        # Example: Add 'coin' parameter for coin-specific methods
        if "::enable_" in method_name or "::disable_" in method_name:
             if not any(p['name'] == 'coin' for p in params):
                params.insert(0, {
                    "name": "coin", 
                    "type": "string", 
                    "required": True,
                    "description": "The ticker of the coin to target."
                })

        return params
        
    def _get_protocol(self, method_name: str) -> str:
        """Determine the protocol type from the method name."""
        if "::enable_eth" in method_name:
            return "eth"
        if "::enable_bch" in method_name:
            return "bch"
        if "::enable_utxo" in method_name:
            return "utxo"
        if "::enable_tendermint" in method_name:
            return "tendermint"
        if "lightning::" in method_name:
            return "lightning"
        return "utxo" # Default
        
    def _get_example_coin(self, method_name: str) -> str:
        """Get an example coin based on the method's protocol."""
        protocol = self._get_protocol(method_name)
        return {
            "eth": "ETH",
            "bch": "BCH",
            "utxo": "KMD",
            "tendermint": "TKL",
            "lightning": "BTC"
        }.get(protocol, "KMD")
        
    def _convert_parameters(self, params: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert parameter info objects or dicts into a consistent dict format."""
        converted_params = []
        for p in params:
            if isinstance(p, ParameterInfo):
                converted_params.append({
                    "name": p.name, "type": p.type, "required": p.required, 
                    "default": p.default, "description": p.description
                })
            else:
                converted_params.append(p)
        return converted_params 