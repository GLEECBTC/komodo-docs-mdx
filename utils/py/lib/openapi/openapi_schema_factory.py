#!/usr/bin/env python3
"""
OpenAPI Schema Creator

This module contains the OpenApiSchemaFactory class, which is responsible for building
various components of the OpenAPI specification, such as request bodies,
response schemas, and parameter definitions. It helps to decouple the schema
generation logic from the main converter class.
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from ..utils.data_utils import is_confirmed_empty_params_method

from ..constants import (
    EnhancedKomodoConfig,
    UnifiedMethodInfo,
    UnifiedParameterInfo,
)
from ..utils import get_logger
from ..constants.config import get_config
from ..managers.path_mapping_manager import EnhancedPathMapper
from ..mdx.mdx_parser import MDXParser
from .openapi_helpers import (
    openapi_property,
    openapi_schema
)


class OpenApiSchemaFactory:
    """
    Factory for creating OpenAPI schemas from parsed MDX data.
    """
    _REF_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(\/komodo-defi-framework\/api\/common_structures")

    def __init__(self, config: Optional[EnhancedKomodoConfig] = None,
                 path_mapper: Optional[EnhancedPathMapper] = None,
                 mdx_parser: Optional[MDXParser] = None):
        self.config = config or get_config()
        self.base_path = Path(self.config.workspace_root)
        self.path_mapper = path_mapper or EnhancedPathMapper(config=self.config)
        self.logger = get_logger(__name__)
        self.mdx_parser = mdx_parser
        
        if self.path_mapper is None:
            self.logger.warning("EnhancedPathMapper not provided to OpenApiSchemaFactory. Reference generation will be disabled.")
            
    def _get_ref_path(self, schema_name: str) -> Optional[str]:
        """
        Constructs an absolute reference path for a schema component,
        suitable for the final bundled OpenAPI specification.
        """
        return f"#/components/schemas/{schema_name}"

    def _find_ref(self, description: str) -> Optional[str]:
        """
        Parses a description to find a markdown link to a common structure or enum.
        Returns the name of the component if found, otherwise None.
        """
        if not description:
            return None
        
        match = self._REF_LINK_PATTERN.search(description)
        if match:
            # The schema name is the text within the square brackets.
            # We'll remove spaces and ensure it's a valid component name.
            return match.group(1).replace(" ", "")
        
        return None

    def create_parameter_schema(self, params: List[UnifiedParameterInfo], mdx_path: str, method_info: Optional[UnifiedMethodInfo] = None) -> Dict[str, Any]:
        """
        Creates a schema for a list of parameters for use in requestBody or response properties.
        """
        properties = {}
        required_fields = []

        for param in params:
            ref_name = self._find_ref(param.description)
            if ref_name:
                # If it's a reference, we create a $ref property.
                # The description is kept at the same level as the $ref.
                properties[param.name] = {
                    "description": param.description,
                    "$ref": self._get_relative_ref_path(ref_name, mdx_path, method_info)
                }
            else:
                # It's a primitive type.
                properties[param.name] = openapi_property(
                    type=self._map_type(param.type),
                    description=param.description,
                    default=param.default_value,
                    enum=param.enum_values
                )
            
            if param.required:
                required_fields.append(param.name)

        return openapi_schema(properties, required_fields)

    def create_response_schema(self, params: List[UnifiedParameterInfo], mdx_path: str, method_info: UnifiedMethodInfo) -> Dict[str, Any]:
        """
        Creates a schema for a successful (200) response.
        """
        schema = self.create_parameter_schema(params, mdx_path, method_info)
        # Add an example if needed, for now an empty object.
        return {
            'description': 'Successful response',
            'content': {
                'application/json': {
                    'schema': schema,
                    'example': {}
                }
            }
        }

    def create_request_body_schema(self, method_info: UnifiedMethodInfo, mdx_path: str) -> Optional[Dict[str, Any]]:
        """
        Creates the complete requestBody object for an OpenAPI operation,
        differentiating between V1 and V2 method structures.
        """
        params_schema = self.create_parameter_schema(method_info.parameters, mdx_path, method_info)
        is_v2 = 'legacy' not in mdx_path

        if is_v2:
            # V2 structure: userpass, method, mmrpc, and an optional 'params' object.
            top_level_properties = {
                'userpass': openapi_property(
                    type="string",
                    description="User password for authentication.",
                    example="RPC_UserP@SSW0RD"
                ),
                'method': openapi_property(
                    type="string",
                    description="Name of the method to be called.",
                    enum=[method_info.name]
                ),
                'mmrpc': openapi_property(
                    type="string",
                    description="The version of the Komodo DeFi SDK RPC protocol. Must be exactly '2.0'",
                    example="2.0"
                )
            }
            required_top_level = ['userpass', 'method', 'mmrpc']
            
            if 'properties' in params_schema:
                if len(params_schema['properties']) == 0:
                    if not is_confirmed_empty_params_method(method_info.name, method_info.version):
                        self.logger.debug(f"{method_info.name} {method_info.version} has empty params_schema.properties: {mdx_path}")
            
            # The 'params' object is optional and only included if the method has parameters.
            if params_schema.get('properties'):
                top_level_properties['params'] = params_schema

        else:
            # V1 structure: userpass, method, and all other params at the top level.
            top_level_properties = {
                'userpass': openapi_property(
                    type="string",
                    description="User password for authentication.",
                    example="RPC_UserP@SSW0RD"
                ),
                'method': openapi_property(
                    type="string",
                    description="Name of the method to be called.",
                    enum=[method_info.name]
                )
            }
            required_top_level = ['userpass', 'method']
            # Add parameters from the 'params' schema directly to the top level.
            
            if 'properties' in params_schema:
                top_level_properties.update(params_schema['properties'])
                if len(params_schema['properties']) == 0:
                    if not is_confirmed_empty_params_method(method_info.name, method_info.version):
                        self.logger.debug(f"{method_info.name} {method_info.version} has empty params_schema.properties: {mdx_path}")

            # Add required fields from the params schema to the top level required list.
            if 'required' in params_schema:
                required_top_level.extend(params_schema['required'])

        final_schema = openapi_schema(top_level_properties, required_top_level)

        return {
            'content': {
                'application/json': {
                    'schema': final_schema
                }
            }
        }

    def _get_relative_ref_path(self, schema_name: str, mdx_path: str, method_info: Optional[UnifiedMethodInfo] = None) -> Optional[str]:
        """
        Constructs a relative file path reference for a schema component.
        Links method files to an enum or common structure schema file 
        in the openapi/paths/components/schemas directory.
        """
        try:
            # All paths in config are relative to the workspace root already.
            schema_file_path = self.config.directories.openapi_schemas / f"{schema_name}.yaml"
            start_dir = None
            # self.logger.info(f"---------------------------------------------------------")
            # self.logger.info(f"Getting relative ref path for {schema_name} from {mdx_path}")
            # self.logger.info(f"schema_file_path: {schema_file_path}")
            if method_info and self.path_mapper:
                path_mapping = self.path_mapper.get_method_path_mapping(
                    method_name=method_info.name, mdx_path=mdx_path, version=method_info.version
                )
                method_yaml_path = Path(path_mapping.openapi_path)
                # self.logger.info(f"method_yaml_path: {method_yaml_path}")
                start_dir = method_yaml_path.parent
                # The starting point for the relative path is the directory containing the method's OpenAPI file.
            else:
                # For a common schema referencing another, or if no method info,
                # the start dir is the schemas dir itself.
                start_dir = self.config.directories.openapi_schemas
            #self.logger.info(f"start_dir: {start_dir}")

            # os.path.relpath calculates the relative path from start_dir to schema_file_path.
            relative_path = os.path.relpath(str(schema_file_path), str(start_dir))
            # self.logger.info(f"relative_path: {relative_path}")
            # Normalize path separators for URL format.
            return relative_path.replace("\\", "/")

        except Exception as e:
            self.logger.error(f"Error creating relative path for '{schema_name}' from '{mdx_path}': {e}", exc_info=True)
            # Fallback to an absolute reference if relative path generation fails.
            return f"#/components/schemas/{schema_name}"

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

    @staticmethod
    def generate_success_example(method_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generates a sample success response for documentation purposes."""
        response_params = method_info.get('response_parameters', [])
        result = {}
        for param in response_params:
            name = param.get('name')
            ptype = param.get('type', 'string').lower()
            if 'string' in ptype:
                result[name] = "string_value"
            elif 'integer' in ptype:
                result[name] = 123
            elif 'boolean' in ptype:
                result[name] = True
            else:
                result[name] = {}
        return {
            "mmrpc": "2.0",
            "result": result,
            "id": 0
        }

    @staticmethod
    def _create_params_schema(parameters: List[UnifiedParameterInfo]) -> Dict[str, Any]:
        """
        Creates the JSON schema for the 'params' object within the request body.
        """
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        # Sort parameters alphabetically for consistent order
        parameters.sort(key=lambda p: p.name)

        for param in parameters:
            param_schema = {
                "description": param.description
            }

            # Use reference for enums or define type
            if param.type and param.type.startswith("#/"):
                param_schema["$ref"] = param.type
            else:
                param_schema["type"] = OpenApiSchemaFactory._map_type(param.type)

            # Add default value if present
            if param.default_value is not None:
                param_schema["default"] = param.default_value

            # Add inline enum values if present
            if param.enum_values:
                param_schema["enum"] = param.enum_values

            schema["properties"][param.name] = param_schema

            if param.required:
                schema["required"].append(param.name)

        # Remove 'required' field if it's empty
        if not schema["required"]:
            del schema["required"]

        return schema

    @staticmethod
    def _extract_enum_references_from_description(description: str) -> Optional[str]:
        """
        Extracts references to common enums from the description.
        """
        match = re.search(r'\[([^\]]+)\]\((.*?)\)', description)
        if match:
            link_url = match.group(2)
            if '#-enum' in link_url.lower() or 'enums' in link_url.lower():
                anchor_match = re.search(r'#([\w-]+enum)$', link_url)
                if anchor_match:
                    return anchor_match.group(1)
        return None 