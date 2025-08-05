#!/usr/bin/env python3
"""
OpenAPI Manager

This module contains the OpenAPIManager class, which orchestrates the entire
OpenAPI specification generation process. It discovers MDX files, uses the
MDXParser to extract information, and the OpenApiSpecGenerator to generate
the final specification files.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Set
import os

# Import local modules
from ..utils import get_logger
from .openapi_spec_generator import OpenApiSpecGenerator
from .openapi_schema_generator import OpenApiSchemaGenerator
from ..mdx.mdx_parser import MDXParser
from ..managers.path_mapping_manager import EnhancedPathMapper
from ..constants import get_config
from .openapi_schema_factory import OpenApiSchemaFactory


class OpenAPIManager:
    """
    Manages the end-to-end process of generating OpenAPI specifications
    from MDX documentation files. It acts as a high-level orchestrator,
    coordinating the parser and converter to produce individual and
    categorized OpenAPI specs.
    """

    def __init__(self, config=None, verbose: bool = True, logger=None, mdx_parser=None, path_mapper=None):
        self.config = config if config else get_config()
        self.logger = logger if logger else get_logger("openapi-manager")
        self.verbose = verbose
        
        # Initialize components with correct dependency injection
        self.path_mapper = EnhancedPathMapper(self.config)
        self.mdx_parser = MDXParser(
            config=self.config,
            path_mapper=self.path_mapper
        )
        
        self.schema_factory = OpenApiSchemaFactory(
            config=self.config,
            path_mapper=self.path_mapper,
            mdx_parser=self.mdx_parser
        )
        self.spec_generator = OpenApiSpecGenerator(
            config=self.config,
            path_mapper=self.path_mapper,
            mdx_parser=self.mdx_parser,
            schema_creator=self.schema_factory
        )
        self.common_schema_generator = OpenApiSchemaGenerator(
            config=self.config,
            path_mapper=self.path_mapper,
            mdx_parser=self.mdx_parser
        )
        self.is_initialized = False

        # Tracking state
        self.all_methods = {}
        self.success_count = 0
        self.error_count = 0
        self.enum_count = 0
        self.structure_count = 0
        self.mdx_source_dirs = [
            self.config.directories.mdx_v1,
            self.config.directories.mdx_v2,
            self.config.directories.mdx_v2_dev
        ]

    def _initialize(self):
        """
        Initializes the manager by loading common structures.
        This is to ensure that common structures are available for all other operations.
        """
        if not self.is_initialized:
            self.logger.info("Initializing OpenAPI manager and preloading common structures...")
            self.mdx_parser.preload_common_structures()
            self.is_initialized = True
            self.logger.info("Initialization complete.")

    def openapi_command(self, **kwargs):
        """
        Main command to orchestrate the entire OpenAPI generation process.
        """
        self._initialize()
        self.logger.info("Starting OpenAPI generation process...")

        # Step 1: Generate all common component schemas from MDX files.
        self.common_schema_generator.generate_common_schemas()
        
        # Step 2: Post-process the generated schemas to resolve nested references.
        self.common_schema_generator.resolve_nested_references()

        # Step 3: Process method files.
        self._process_and_generate_specs()

        # Step 4: Generate the main openapi.yaml file that bundles everything.
        self.generate_main_openapi_file()

        self.logger.info("OpenAPI generation process finished.")
        self.logger.info(f"Total successful methods processed: {self.success_count}")

    def _process_and_generate_specs(self):
        versions = ["v1", "v2"]
        self.logger.info(f"Processing versions: {versions}")
        for version in versions:
            if not self.mdx_source_dirs:
                self.logger.warning(f"No source directories found for version {version}. Skipping.")
                return

            files_to_process = []
            for dir_path in self.mdx_source_dirs:
                if dir_path.exists():
                    files_to_process.extend(sorted(dir_path.rglob("*.mdx")))
            
            version_methods = {}
            for file_path in files_to_process:
                try:
                    parsed_info = self.mdx_parser.parse_mdx_file(file_path)
                    if parsed_info and parsed_info.get('type') == 'method':
                        method_name = parsed_info['method_name']
                        parsed_info['version'] = version
                        version_methods[method_name] = parsed_info
                        
                        spec = self.spec_generator.build_openapi_spec(parsed_info)
                        self.spec_generator.write_openapi_file(
                            spec, method_name, mdx_path=str(file_path)
                        )
                        self.success_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to process {file_path}: {e}")
                    self.error_count += 1
            
            self.all_methods.update(version_methods)


    def generate_main_openapi_file(self):
        """
        Generates the root openapi.yaml file by discovering all generated
        path and component files and creating relative references to them.
        """
        self.logger.info("Generating main openapi.yaml file...")
        
        main_spec = {
            "openapi": "3.0.3",
            "info": {
                "title": "Komodo DeFi Framework API",
                "version": "2.0",
                "description": (
                    "This specification provides a comprehensive overview of the Komodo DeFi Framework API, "
                    "covering all available methods and data structures."
                )
            },
            "servers": [
                {
                    "url": "http://127.0.0.1:7783",
                    "description": "Local MM2 instance"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {}
            }
        }   
        
        paths_root = self.config.directories.openapi_paths
        components_root = self.config.directories.openapi_schemas
        output_file = self.config.directories.openapi_main

        # Reference all path files
        for file_path in sorted(paths_root.rglob("*.yaml")):
            # Skip any files inside a 'components' subdirectory within 'paths'
            if 'components' in file_path.parts:
                continue

            if file_path.parent != paths_root: # Exclude files in the root of 'paths'
                content = yaml.safe_load(file_path.read_text())
                # The file content is a dict where the key is the path string
                for path_item in content:
                    relative_path = os.path.relpath(file_path, start=output_file.parent)
                    main_spec["paths"][path_item] = {
                        "$ref": relative_path.replace("\\", "/")
                    }

        # Reference all component schema files
        for schema_file in sorted(components_root.rglob("*.yaml")):
            schema_name = schema_file.stem
            # The ref path should be relative from the main openapi.yaml
            relative_path = os.path.relpath(schema_file, start=output_file.parent)
            main_spec["components"]["schemas"][schema_name] = {
                "$ref": relative_path.replace("\\", "/")
            }

        try:
            with open(output_file, 'w') as f:
                yaml.dump(main_spec, f, sort_keys=False, width=120)
            self.logger.info(f"Successfully generated main spec at {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to write main openapi.yaml file: {e}", exc_info=True)

    def vlog(self, message: str):
        """Verbose logging utility."""
        if self.verbose:
            print(message)

    def get_stats(self) -> Dict[str, Any]:
        """
        Retrieves and consolidates statistics from the manager and spec_generator.
        """
        spec_stats = self.spec_generator.get_stats()
        return {
            'files_processed': spec_stats.get('files_processed', 0),
            'enums_found': self.enum_count,
            'structures_found': self.structure_count,
        }

    def generate_common_schemas_only(self):
        """
        Discovers and processes only common component files (enums, structures)
        and generates their corresponding OpenAPI schemas.
        """
        self.logger.info("Starting common schema generation...")
        
        common_structures_dir = self.path_mapper.config.directories.mdx_common_structures
        if not common_structures_dir.exists():
            self.logger.warning(f"Common structures directory not found at: {common_structures_dir}")
            return

        for mdx_file in sorted(common_structures_dir.rglob("*.mdx")):
            parsed_info = self.mdx_parser.parse_mdx_file(mdx_file)
            if parsed_info:
                doc_type = parsed_info.get('type')
                name = parsed_info.get('name')

                if doc_type in ['enum', 'structure']:
                    spec = self.spec_generator.build_component_spec(parsed_info)
                    self.spec_generator.write_openapi_file(
                        spec, name, mdx_path=str(mdx_file)
                    )
                    self.logger.save(f"Schema created for [{name}]")
                    if doc_type == 'enum':
                        self.enum_count += 1
                    else:
                        self.structure_count += 1
        
        self.logger.info(f"Common schema generation complete. Processed {self.enum_count} enums and {self.structure_count} structures.")

    def _merge_specs(self, paths: List[str], version: str) -> Dict:
        """
        Merges multiple OpenAPI specification files into a single dictionary.
        This is useful for creating aggregated or master specifications.

        Args:
            paths: A list of file paths to the OpenAPI YAML files.
            version: The API version string.

        Returns:
            A dictionary representing the merged OpenAPI specification.
        """
        main_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": f"Komodo DeFi Framework API - {version.upper()}",
                "version": version,
                "description": "The comprehensive OpenAPI specification for Komodo DeFi Framework API."
            },
            "paths": {},
            "components": {
                "schemas": {}
            }
        }
        
        for path in paths:
            try:
                with open(path, 'r') as f:
                    spec = yaml.safe_load(f)
                
                # Merge paths
                if "paths" in spec:
                    main_spec["paths"].update(spec.get("paths", {}))
                
                # Merge components
                if "components" in spec and "schemas" in spec["components"]:
                    main_spec["components"]["schemas"].update(spec["components"]["schemas"])
            
            except FileNotFoundError:
                self.logger.info(f"Warning: File not found - {path}")
            except yaml.YAMLError as e:
                self.logger.info(f"Error parsing YAML file {path}: {e}")
                
        return main_spec

    def _get_yaml_files(self, directory: str) -> List[str]:
        """
        Recursively finds all YAML files in a given directory.
        """
        yaml_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith((".yaml", ".yaml")):
                    yaml_files.append(os.path.join(root, file))
        return yaml_files

    def _write_main_openapi_file(self, spec: Dict, version: str):
        """
        Writes the main, aggregated OpenAPI specification to a file.
        The output path is determined by the EnhancedPathMapper.
        """
        output_path = self.path_mapper.openapi_path / f"main_openapi_spec_{version}.yaml"
        
        with open(output_path, 'w') as f:
            yaml.dump(spec, f, sort_keys=False, allow_unicode=True)
            
        self.logger.info(f"Main OpenAPI spec file written to: {output_path}")

    def update_main_spec(self, version: str):
        """
        Updates the main OpenAPI specification by discovering all individual
        and categorized spec files and merging them. This ensures the main
        spec is always up-to-date.
        """
        self.logger.info("Updating main OpenAPI specification...")
        
        # Define directories to scan for spec files
        spec_dirs = [
            Path(self.config.workspace_root) / self.path_mapper.config.directories.yaml_v1,
            Path(self.config.workspace_root) / self.path_mapper.config.directories.yaml_v2,
            Path(self.config.workspace_root) / self.path_mapper.config.directories.openapi_main
        ]
        
        all_spec_files = []
        for directory in spec_dirs:
            if directory.exists():
                all_spec_files.extend(self._get_yaml_files(str(directory)))
                
        # Remove duplicates
        all_spec_files = sorted(list(set(all_spec_files)))
        
        # Merge all found specs
        merged_spec = self._merge_specs(all_spec_files, version)
        
        # Write the final main spec file
        self._write_main_openapi_file(merged_spec, version)
        
        self.logger.info("Main OpenAPI specification updated successfully.") 