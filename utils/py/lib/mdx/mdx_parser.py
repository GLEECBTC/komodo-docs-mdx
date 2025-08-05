#!/usr/bin/env python3
"""
MDX Parser

This module contains the MDXParser class, responsible for parsing MDX files
to extract API method information, including parameters, descriptions, and titles.
It is designed to handle the specific structure of Komodo DeFi Framework documentation.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass

# Import path utilities
from ..constants.config import get_config
from ..managers.path_mapping_manager import EnhancedPathMapper
from ..constants import UnifiedParameterInfo


# Create a simple Response class for backward compatibility
@dataclass
class Response:
    """Simple response class for OpenAPI generation."""
    status_code: str
    description: str


class MDXParser:
    """Parser for MDX files to extract API method information."""
    def __init__(self, config=None, path_mapper=None):
        self.config = config or get_config()
        self.path_mapper = path_mapper or EnhancedPathMapper()
        self.base_path = Path(self.config.workspace_root)
        # Track common structures across all parsed methods
        self.common_structures = defaultdict(int)
        self.enum_patterns = defaultdict(set)
        self.common_structure_files = self._get_common_structure_files()
        self._load_enums()
        self._load_common_structures()

    def parse_mdx_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        # TEST COMMENT
        """Parse an MDX file and extract method information."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if 'common_structures/enums' in str(file_path):
                return self._parse_enum_file(content, file_path)
            elif 'common_structures' in str(file_path):
                return self._parse_structure_file(content, file_path)
            else:
                return self._parse_method_file(content, file_path)

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def _parse_enum_file(self, content: str, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parses an MDX file containing an enum definition."""
        enum_name_match = re.search(r'#\s+([a-zA-Z0-9_]+)', content)
        if enum_name_match:
            enum_name = enum_name_match.group(1)
            self.enum_patterns[enum_name] = set() # Placeholder for actual enum values
            return {"type": "enum", "name": enum_name, "file_path": str(file_path)}
        return None

    def _parse_structure_file(self, content: str, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parses an MDX file containing a common structure definition."""
        structure_name_match = re.search(r'#\s+([a-zA-Z0-9_]+)', content)
        if structure_name_match:
            structure_name = structure_name_match.group(1)
            self.common_structures[structure_name] += 1
            return {"type": "structure", "name": structure_name, "file_path": str(file_path)}
        return None

    def _parse_method_file(self, content: str, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse an MDX file for method information."""
        # If the file is tagged as an overview, skip it.
        if "tag : 'overview'" in content:
            return None

        method_match = re.search(r'^##\s+([^\s{]+)', content, re.MULTILINE)
        if not method_match:
            return None

        if 'legacy' in str(file_path):
            version = 'v1'
        else:
            version = 'v2'

        method_name = method_match.group(1).replace('\\_', '_')

        title_match = re.search(r'export const title = ["\']([^"\']+)["\']', content)
        desc_match = re.search(r'export const description = ["\']([^"\']+)["\']', content)

        title = title_match.group(1) if title_match else f"Komodo DeFi Framework Method: {method_name}"
        description = desc_match.group(1) if desc_match else f"Method description for {method_name}"

        request_params = self._extract_parameters_from_mdx(content, "Request")
        response_params = self._extract_parameters_from_mdx(content, "Response")

        return {
            'type': 'method',
            'version': version,
            'method_name': method_name,
            'title': title,
            'description': description,
            'parameters': request_params,
            'response_parameters': response_params,
            'file_path': str(file_path)
        }

    def _extract_parameters_from_mdx(self, content: str, table_type: str) -> List[UnifiedParameterInfo]:
        """Extract parameters from MDX tables (Request or Response)."""
        params = []
        # More robust regex to find tables for either "Request" or "Response"
        pattern = re.compile(
            rf'### {table_type} Parameter[s]?.*?\n\n(.*?)(?=\n###|\n##|\Z)',
            re.DOTALL | re.IGNORECASE
        )
        
        matches = pattern.findall(content)
        for table_content in matches:
            params.extend(self._parse_parameter_table(table_content, table_type))

        return params

    def _parse_parameter_table(self, table_content: str, table_type: str) -> List[UnifiedParameterInfo]:
        """General purpose parameter table parser for request and response tables."""
        parameters = []
        lines = table_content.strip().split('\n')
        if len(lines) < 2:  # Needs at least a header and a separator
            return parameters

        header_line = lines[0]
        header = [h.strip().lower() for h in header_line.strip('|').split('|')]
        
        if not any(header): return []

        has_default = 'default' in header
        has_required = 'required' in header

        for line in lines[2:]:  # Skip header and separator
            if not line.strip().startswith('|'):
                continue
            
            cols = [c.strip() for c in line.strip('|').split('|')]
            
            if len(cols) < len(header):
                continue
            if len(cols) > len(header):
                cols[len(header)-1] = '|'.join(cols[len(header)-1:])
                cols = cols[:len(header)]
            
            row_data = dict(zip(header, cols))

            param_name_raw = row_data.get('parameter', '')
            if not param_name_raw or '---' in param_name_raw:
                continue

            param_name = param_name_raw.strip('`').replace('\\_', '_')
            param_type = row_data.get('type', 'string')
            description = row_data.get('description', '')

            required = False
            default_value = None
            enum_values = None

            if table_type == "Request":
                required_str = row_data.get('required', '') if has_required else ''
                default_val_str = row_data.get('default', '') if has_default else ''
                
                required = self._is_parameter_required(required_str, description, default_val_str)
                
                if default_val_str and default_val_str != '-':
                    default_value = self._clean_and_cast_default(default_val_str, param_type)
                
                # Enum extraction
                found_enum_values, cleaned_type = self._extract_enum_from_type(param_type)
                if not found_enum_values:
                    found_enum_values = self._extract_enum_from_description(description)
                
                param_type = cleaned_type
                enum_values = found_enum_values

                if not default_value:
                     extracted_default = self._extract_default_from_description(description)
                     if extracted_default:
                        default_value = self._clean_and_cast_default(extracted_default, param_type)
            
            # For response tables, all we need is name, type, and description.
            # For request tables, we need all fields.
            parameters.append(UnifiedParameterInfo(
                name=param_name,
                type=param_type,
                description=description,
                required=required,
                default_value=default_value,
                enum_values=enum_values
            ))
            
        return parameters

    def _clean_and_cast_default(self, default_val: str, param_type: str) -> Any:
        """Cleans and casts a default value string to its appropriate type."""
        cleaned_val = default_val.strip('`')
        lower_param_type = param_type.lower()

        if 'int' in lower_param_type:
            try:
                return int(cleaned_val)
            except (ValueError, TypeError):
                return cleaned_val
        elif 'bool' in lower_param_type:
            if cleaned_val.lower() == 'true':
                return True
            elif cleaned_val.lower() == 'false':
                return False
            return cleaned_val
        elif 'number' in lower_param_type or 'float' in lower_param_type:
            try:
                return float(cleaned_val)
            except (ValueError, TypeError):
                return cleaned_val
        
        return cleaned_val

    def _is_parameter_required(self, required_indicator: str, description: str, default_value: Optional[str]) -> bool:
        """Determines if a parameter is required based on table indicators and description."""
        if '✓' in required_indicator:
            return True
        if '✗' in required_indicator:
            return False
        # Fallback logic if symbols are not used
        if default_value is not None and default_value.strip() != '-':
            return False
        if 'optional' in description.lower():
            return False
        return True

    def _extract_enum_from_type(self, param_type: str) -> Tuple[Optional[List[str]], str]:
        # Simple enum extraction from type field, e.g., "string (Enum: A, B)"
        match = re.search(r'\((?:Enum|Values):\s*(.*?)\)', param_type, re.IGNORECASE)
        if match:
            values = [v.strip().strip('`') for v in match.group(1).split(',')]
            # Return the cleaned type without the enum part
            cleaned_type = re.sub(r'\s*\((?:Enum|Values):.*?\)', '', param_type).strip()
            return values, cleaned_type
        return None, param_type

    def _extract_default_from_description(self, description: str) -> Optional[str]:
        match = re.search(r'defaults to `([^`]+)`', description, re.IGNORECASE)
        return match.group(1) if match else None

    def _parse_responses_table(self, content: str) -> List[Response]:
        return [Response(status_code="200", description="Success")]

    def _extract_request_body_schema(self, content: str, method_name: str) -> Optional[Dict[str, Any]]:
        """Extracts the request body schema from JSON example in MDX."""
        code_group_match = re.search(
            r'```json\s*\n({.*?})\n```',
            content, re.DOTALL | re.IGNORECASE
        )
        
        if code_group_match:
            # Find the first JSON block within the CodeGroup
            json_match = re.search(r'```json\s*\n({.*?})\n```', code_group_match.group(1), re.DOTALL)
            if json_match:
                try:
                    example_json = json.loads(json_match.group(1))
                    
                    # Basic schema inference from the example
                    properties = {
                        key: {"type": self._infer_type_from_value(value)}
                        for key, value in example_json.items()
                    }
                    
                    return {
                        "type": "object",
                        "properties": properties,
                        "required": list(example_json.keys()) # Assume all keys in example are required
                    }
                except json.JSONDecodeError:
                    pass  # Ignore if JSON is malformed

        return None

    def _map_type(self, mdx_type: str) -> str:
        """Maps an MDX type to an OpenAPI type."""
        mdx_type = mdx_type.lower()
        if 'string' in mdx_type:
            return 'string'
        if 'integer' in mdx_type or 'int' in mdx_type:
            return 'integer'
        if 'number' in mdx_type or 'float' in mdx_type:
            return 'number'
        if 'boolean' in mdx_type or 'bool' in mdx_type:
            return 'boolean'
        if 'array' in mdx_type:
            return 'array'
        if 'object' in mdx_type:
            return 'object'
        return 'string'  # Default to string

    def _infer_type_from_value(self, value: Any) -> str:
        """Infers the JSON schema type from a Python value."""
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        return "string"

    def _extract_enum_from_description(self, description: str) -> Optional[List[str]]:
        """Extracts enum values from a description string."""
        # This regex looks for patterns like "one of `VALUE1`, `VALUE2`"
        match = re.search(r'one of (.+?)(?:\.|$)', description, re.IGNORECASE)
        if match:
            # Extracting values and cleaning them up
            values_str = match.group(1)
            return [v.strip().strip('`') for v in values_str.split(',')]
        return None

    def _extract_enum_references_from_description(self, description: str) -> Optional[str]:
        # Simple regex to find a link to an enum, e.g. [MyEnum](#myenum)
        match = re.search(r'\[([\w\s]+Enum)\]\((#[\w-]+)\)', description)
        if match:
            # We can return the name of the enum. The generator can then create a $ref
            return match.group(1).replace(' ', '')
        return None

    def preload_common_structures(self):
        """Public method to explicitly load or reload common structures and enums."""
        self._load_enums()
        self._load_common_structures()

    def _get_common_structure_files(self) -> Dict[str, Path]:
        """
        Scans for common structure and enum files in the documentation directory.
        """
        # Implementation of _get_common_structure_files method
        pass

    def _load_enums(self):
        """Implementation of _load_enums method"""
        pass

    def _load_common_structures(self):
        """Implementation of _load_common_structures method"""
        pass 