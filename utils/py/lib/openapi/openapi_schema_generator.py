#!/usr/bin/env python3
"""
OpenAPI Common Schema Generator

This module contains the OpenApiSchemaGenerator class, which is responsible for
generating reusable schemas for enums and data structures. It scans the
documentation for definitions and creates OpenAPI components that can be
referenced throughout the API specification.
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
import json
from datetime import datetime

from ..constants.config import get_config
from .openapi_schema_factory import OpenApiSchemaFactory
from ..mdx.mdx_parser import MDXParser
from ..constants.config_struct import EnhancedKomodoConfig
from openapi_pydantic import Info, OpenAPI
from ..managers.path_mapping_manager import EnhancedPathMapper
from ..utils.file_utils import ensure_directory_exists
from ..utils.logging_utils import get_logger
from ..constants import UnifiedParameterInfo


class OpenApiSchemaGenerator:
    """
    Generates common OpenAPI schemas for enums and data structures.
    This class handles the discovery, parsing, and generation of reusable
    components from the MDX documentation.
    """
    # Regex to find structure definitions (### Heading) and their content (until the next ### or ##)
    _STRUCTURE_DEF_REGEX = re.compile(r'###\s+([\w_]+)\s*\n(.*?)(?=\n###|\n##|\Z)', re.DOTALL)
    # Regex to find enum definitions (### Heading ending with Enum) and their content
    _ENUM_DEF_REGEX = re.compile(r'###\s+([\w_]+Enum)\s*\n(.*?)(?=\n###|\n##|\Z)', re.DOTALL)
    _STRUCTURE_TABLE_ROW_REGEX = re.compile(r'\|\s*(.*?)\s*\|\s*(.*?)\s*\|')
    _ENUM_NAME_REGEX = re.compile(r'##\s+([\w_]+)')
    _ENUM_DESC_REGEX = re.compile(r'export const description = "(.*?)"')
    _ENUM_TABLE_REGEX = re.compile(r'\| Value \|.*?\n\|-.*\n(.*)', re.DOTALL)
    _ENUM_TABLE_ROW_REGEX = re.compile(r'\|\s*`([^`]+)`\s*\|')
    _COMMON_STRUCTURE_FILE_PATTERN = "src/pages/komodo-defi-framework/api/common_structures/**/index.mdx"
    _ENUM_FILE_PATTERN = "src/pages/komodo-defi-framework/api/common_structures/enums/index.mdx"
    _HEADING_REGEX = re.compile(r"^##\s+(.+)", re.MULTILINE)
    _TABLE_REGEX = re.compile(r"(\|(?:[^\r\n\|]+\|)+)", re.MULTILINE)
    _TABLE_HEADER_REGEX = re.compile(r"\|\s*Parameter\s*\|\s*Type\s*\|")

    def __init__(self, config: Optional[EnhancedKomodoConfig] = None, path_mapper=None, mdx_parser=None, logger=None):
        self.config = config or get_config()
        self.path_mapper = path_mapper or EnhancedPathMapper(config=self.config)
        self.mdx_parser = mdx_parser or MDXParser(config=self.config, path_mapper=self.path_mapper)
        self.logger = logger or get_logger(__name__)
        self.schema_factory = OpenApiSchemaFactory(
            config=self.config,
            path_mapper=self.path_mapper,
            mdx_parser=self.mdx_parser
        )
        self.common_schemas_path = self.config.directories.openapi_schemas
        ensure_directory_exists(self.common_schemas_path)
        self.logger.info(f"Common schemas will be written to: {self.common_schemas_path}")

    def generate_common_schemas(self):
        """
        Generates schemas for common data structures and enums.
        """
        self.logger.info("Generating common schemas for data structures and enums...")
        # Generate files for manually defined enums from the enums/index.mdx file
        manual_enums = self._extract_manual_enums_from_docs()
        for enum_name, schema in manual_enums.items():
            full_schema = {
                'components': {
                    'schemas': {
                        enum_name: {
                            **schema,
                            "title": f"Component: {enum_name}"
                        }
                    }
                }
            }
            with open(Path(self.common_schemas_path) / f"{enum_name}.yaml", 'w', encoding='utf-8') as f:
                yaml.dump(full_schema, f, sort_keys=False, allow_unicode=True)

        # Generate files for common data structures
        self.logger.info("Generating individual structure files...")
        self._generate_individual_structure_files()

    def generate_review_files(self, all_enums: Dict[str, Set[str]]):
        """
        Generates review files for undocumented enums.
        """
        # Log any enums that are documented but not in the manual list for review
        self._output_undocumented_enums_for_review(all_enums)

    def _output_undocumented_enums_for_review(self, all_enums: Dict[str, Set[str]]):
        """
        Creates a JSON file listing enums that are found in parameter descriptions
        but do not have a corresponding manual enum file.
        """
        review_file = self.path_mapper.config.directories.branched_reports_dir / "undocumented_enums_for_review.json"
        
        manual_enums_path = self.path_mapper.config.directories.mdx_common_structures / "enums"
        existing_enums = {p.stem for p in manual_enums_path.glob("*.mdx")}
        
        undocumented_enums_data = {}
        for enum_name, values in sorted(all_enums.items()):
            if enum_name not in existing_enums:
                sorted_values = sorted(list(values))
                undocumented_enums_data[enum_name] = {
                    "values": sorted_values,
                    "potential_schema": {
                        "type": "string",
                        "enum": sorted_values
                    }
                }
        
        if not undocumented_enums_data:
            # No undocumented enums, no need to create a report.
            return

        report = {
            "scan_metadata": {
                "scanner_type": "UNDOCUMENTED_ENUM_SCAN",
                "scanner_version": "1.0.0",
                "generated_at": datetime.now().isoformat(),
                "kdf_branch": self.path_mapper.config.kdf_branch,
                "mdx_branch": self.path_mapper.config.mdx_branch,
                "description": "Enums found in parameter descriptions that do not have a dedicated documentation file."
            },
            "undocumented_enums": undocumented_enums_data
        }

        with open(review_file, 'w') as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"Undocumented enums report created at: {review_file}")

    def _generate_individual_structure_files(self):
        """
        Scans for structure definition files and creates a YAML schema file for each.
        """
        structure_dir = self.path_mapper.config.directories.mdx_common_structures
        if not structure_dir.exists():
            return
            
        for structure_file in structure_dir.rglob("*.mdx"):
            if "enums" in structure_file.parts:
                continue
            self._create_structure_schema_file(structure_file)

    def _create_structure_schema_file(self, structure_file: Path):
        """
        Parses a single structure .mdx file and creates a corresponding OpenAPI schema file
        for each structure defined within it (marked by ###).
        """
        try:
            content = structure_file.read_text(encoding="utf-8")
            structures = self._parse_structure_definitions(content, str(structure_file))
            for name, schema in structures.items():
                full_schema = {
                    'components': {
                        'schemas': {
                            name: schema
                        }
                    }
                }
                self._write_schema_file(name, full_schema)
        except Exception as e:
            self.logger.error(f"Error processing structure file {structure_file}: {e}")

    def _parse_structure_definitions(self, content: str, file_path: str) -> Dict[str, Dict]:
        """
        Parses an MDX file for structure definitions. A single file can contain
        multiple structures, each denoted by a '###' heading.
        """
        structures = {}
        matches = self._STRUCTURE_DEF_REGEX.findall(content)
        
        for match in matches:
            structure_name, structure_content = match
            # Each match corresponds to one structure (e.g., ActivationMode)
            properties, required = self._parse_structure_table(structure_content, file_path)
            if properties: # Only add if properties were found
                schema = {
                    'type': 'object',
                    'properties': properties
                }
                if required:
                    schema['required'] = sorted(list(set(required)))
                structures[structure_name] = schema
            
        return structures

    def _parse_structure_table(self, structure_content: str, file_path: str) -> (Dict[str, Dict], List[str]):
        """
        Parses a markdown table within a structure's section to extract properties.
        """
        properties = {}
        required_params = []
        header = []
        table_lines = []
        in_table_body = False

        # First pass to find the header and table rows
        for line in structure_content.splitlines():
            line = line.strip()
            if not line.startswith('|'):
                continue
            
            if '---' in line:
                in_table_body = True
                continue
            
            if not in_table_body:
                if 'parameter' in line.lower() or 'property' in line.lower():
                    header = [h.strip().lower() for h in line.strip('|').split('|')]
            else:
                table_lines.append(line)
        
        if not header:
            self.logger.debug(f"No table header found in content for file: {file_path}")
            return {}, []

        # Process table rows
        for line in table_lines:
            cols = [c.strip() for c in line.strip('|').split('|')]
            
            if len(cols) < len(header):
                self.logger.warning(f"Skipping malformed row (cols < header): {line} in {file_path}")
                continue
            # In case of extra pipes in description, join the trailing columns
            if len(cols) > len(header):
                cols[len(header)-1] = '|'.join(cols[len(header)-1:])
                cols = cols[:len(header)]

            row_data = dict(zip(header, cols))

            param_name_raw = row_data.get('parameter', row_data.get('property', ''))
            if not param_name_raw or '---' in param_name_raw:
                continue
                
            param_name = param_name_raw.strip('`').replace('\\_', '_')

            param_type = row_data.get('type', 'string')
            description = row_data.get('description', '')
            default_val = row_data.get('default', '')
            required_str = row_data.get('required', '')
            is_required = '✓' in required_str

            # Create a UnifiedParameterInfo object to pass to the factory
            param_info = UnifiedParameterInfo(
                name=param_name,
                type=param_type,
                description=description,
                required=is_required,
                default_value=default_val if default_val and default_val != '-' else None
            )

            # Pass the file_path for context, but no method_info,
            # as we are generating a common component, not a method spec.
            param_schema = self.schema_factory.create_parameter_schema(
                [param_info],
                mdx_path=file_path
            )
            if param_name in param_schema.get('properties', {}):
                properties[param_name] = param_schema['properties'][param_name]
            
            if is_required:
                required_params.append(param_name)

        return properties, required_params

    def _write_schema_file(self, name: str, schema: Dict):
        """Writes a schema to a YAML file."""
        ensure_directory_exists(self.common_schemas_path)
        filename = f"{name}.yaml"
        output_file_path = Path(self.common_schemas_path) / filename
        # self.logger.info(f"Writing schema for {name} to {output_file_path}")
        with open(output_file_path, 'w', encoding='utf-8') as f_out:
            yaml.dump(schema, f_out, sort_keys=False, allow_unicode=True)

    def _extract_manual_enums_from_docs(self) -> Dict[str, Dict[str, Any]]:
        """
        Scans documentation for manually defined enum files. A single file can
        contain multiple enums, each denoted by a '###' heading ending in 'Enum'.
        """
        enums = {}
        enum_dir = self.path_mapper.config.directories.mdx_common_structures / "enums"
        if not enum_dir.exists():
            return enums
            
        for enum_file in enum_dir.glob("*.mdx"):
            with open(enum_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find all enum definitions in the file
            matches = self._ENUM_DEF_REGEX.findall(content)

            for match in matches:
                enum_name, enum_content = match
                
                # Simple description for now
                description_match = re.search(r'^(.*?)(?=\n\s*\|)', enum_content, re.DOTALL)
                description = description_match.group(1).strip() if description_match else f"Enum for {enum_name}"

                # The rest of the content is assumed to be the table
                values, descriptions = self._parse_enum_table(enum_content)

                if values:
                    # Append individual value descriptions to the main description
                    if descriptions:
                        description += "\n\n**Values:**\n"
                        for val, desc in descriptions.items():
                            if desc:
                                description += f"- `{val}`: {desc}\n"

                    enums[enum_name] = {
                        "type": "string",
                        "description": description,
                        "enum": values
                    }
        return enums

    def _parse_enum_table(self, table_content: str) -> (List[str], Dict[str, str]):
        """Parses a markdown table to extract enum values and their descriptions."""
        values = []
        descriptions = {}
        header = []
        table_lines = []
        in_table_body = False

        for line in table_content.splitlines():
            line = line.strip()
            if not line.startswith('|'):
                continue
            if '---' in line:
                in_table_body = True
                continue
            if not in_table_body:
                if 'value' in line.lower():
                    header = [h.strip().lower() for h in line.strip('|').split('|')]
            else:
                table_lines.append(line)

        if not header:
            return [], {}
            
        for line in table_lines:
            cols = [c.strip() for c in line.strip('|').split('|')]
            if len(cols) < len(header):
                continue
            
            row_data = dict(zip(header, cols))
            
            value_raw = row_data.get('value', '')
            if not value_raw or '---' in value_raw:
                continue
            
            value = value_raw.strip('`')
            description = row_data.get('description', '')

            values.append(value)
            descriptions[value] = description.strip()

        return values, descriptions

    def _parse_enum_values_from_table(self, table_content: str) -> List[str]:
        """Parses a markdown table to extract enum values."""
        values, _ = self._parse_enum_table(table_content)
        return values

    def resolve_nested_references(self):
        """
        Iterates through all generated common schemas and resolves internal $ref links.
        This is a post-processing step to handle nested common objects.
        """
        self.logger.info("Post-processing common schemas to resolve nested references...")
        schema_dir = Path(self.config.directories.openapi_schemas)
        if not schema_dir.exists() or not any(schema_dir.iterdir()):
            self.logger.warning("Common schemas directory is empty or not found. Skipping reference resolution.")
            return

        for schema_file in schema_dir.glob("*.yaml"):
            try:
                with open(schema_file, 'r+', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if not data:
                        continue

                    # updated tracks if a change was made
                    updated = self._traverse_and_update_refs(data)

                    if updated:
                        # If changes were made, write them back to the file
                        f.seek(0)
                        yaml.dump(data, f, sort_keys=False, allow_unicode=True)
                        f.truncate()
            except Exception as e:
                self.logger.error(f"Error processing schema file for nested refs {schema_file}: {e}")
        self.logger.info("Finished resolving nested references.")

    def _traverse_and_update_refs(self, node: Any) -> bool:
        """
        Recursively traverses a dictionary/list structure to find and update references.
        Returns True if an update was made, otherwise False.
        """
        updated = False
        if isinstance(node, dict):
            # Check if this node is a property that might contain a reference link
            if 'description' in node and isinstance(node['description'], str):
                ref_name = self.schema_factory._find_ref(node['description'])
                if ref_name:
                    # Found a reference. Replace the node content with a $ref,
                    # but keep the description for context.
                    description = node['description']
                    node.clear()
                    node['description'] = description
                    node['$ref'] = self.schema_factory._get_ref_path(ref_name)
                    return True  # A change was made

            # Recurse through dictionary values
            for key, value in list(node.items()):
                if self._traverse_and_update_refs(value):
                    updated = True

        elif isinstance(node, list):
            # Recurse through list items
            for item in node:
                if self._traverse_and_update_refs(item):
                    updated = True
        
        return updated 