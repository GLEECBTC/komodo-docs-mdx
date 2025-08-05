#!/usr/bin/env python3
"""
Komodo DeFi Framework Tools - Unified CLI

A comprehensive command-line interface for managing KDF documentation, OpenAPI specs,
Postman collections, and repository analysis. This tool consolidates functionality
from multiple specialized scripts into a single, easy-to-use interface.

Available Commands:
- openapi: Convert MDX documentation to OpenAPI specs
- postman: Generate Postman collections
- scan-rust: Scan KDF Rust repository for RPC methods
- scan-mdx: Scan MDX documentation files for method names
- gap-analysis: Compare Rust methods with MDX documentation
- map_methods: Method mapping and OpenAPI management
- json-extract: Extract JSON examples from MDX files
- error-report: Generate a report of method requests that have error responses
- get-kdf-responses: Get KDF responses for a given method
- build-container: Build the KDF container
- start-container: Start the KDF container
- stop-container: Stop the KDF container
- switch-kdf-branch: Switch the KDF branch
- get-json-example-method-paths: Get the JSON example method paths
- generate-v2-no-param-methods-report: Generate a report of V2 methods that don't have parameters
- extract-errors: Extract error enums from the KDF Rust codebase
- balances: Get address and balance info for test coins on all nodes
- sync: Bidirectional sync between MDX docs and Postman collections

"""

import sys
import os
import time
import subprocess
import requests
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
import traceback
import argparse
import asyncio
import glob
import json
from datetime import datetime
from collections import defaultdict
import re

# To solve relative import issues, we add the project root to the python path.
_script_dir = Path(__file__).parent.absolute()
_workspace_root = _script_dir.parent.parent
if not (_workspace_root / "src" / "pages").exists():
    _current = Path.cwd()
    for _parent in [_current] + list(_current.parents):
        if (_parent / "src" / "pages").exists() and (_parent / "utils" / "py").exists():
            _workspace_root = _parent
            break
sys.path.insert(0, str(_workspace_root))

# Core library imports
from lib.mdx.mdx_generator import MdxGenerator
from lib.mdx.mdx_draft_generator import MethodDetails
from lib.postman.postman_scanner import MdxJsonExampleExtractor, ExtractedExample
from lib.managers import MethodMappingManager
from lib.utils import safe_write_json, ensure_directory_exists
from lib.managers.path_mapping_manager import EnhancedPathMapper
from lib import (
    UnifiedScanner,
    get_logger, DraftsManager,
    MdxGenerator, ExistingDocsScanner
)
from lib.constants import UnifiedRepositoryInfo
from lib.constants.config import get_config
from lib.constants.data_structures import ScanMetadata
from lib.rust.scanner import KDFScanner
from lib.rust.error_scanner import ErrorScanner
from lib.mdx.error_scanner import MdxErrorScanner
from lib.openapi.openapi_manager import OpenAPIManager
from lib.postman.postman_manager import PostmanManager
from lib.utils.data_utils import sort_version_method_counts
from lib.async_support import run_async
from lib.openapi.openapi_spec_generator import OpenApiSpecGenerator
from lib.api_client.kdf_api_processor import ApiRequestProcessor
from lib.api_client import kdf_api_processor as kdf_api_processor_module
from lib.managers.git_manager import GitManager
from lib.sync.cli import SyncCLI


class KDFTools:
    """Unified KDF Tools CLI."""
    
    def __init__(self):
        self.verbose = True
        self.config = get_config()
        # Handle None workspace_root
        workspace_root = self.config.workspace_root or str(Path.cwd())
        self.workspace_root = Path(workspace_root)
        self.mdx_docs_path = self.workspace_root / 'src' / 'pages'
        self.logger = get_logger("kdf-tools")
        self.git_manager = GitManager(self.logger)
        self.mdx_branch = self.git_manager.get_branch_name(self.workspace_root)
        self.mdx_commit = self.git_manager.get_commit_hash(self.workspace_root)
        
        if '-h' in sys.argv or '--help' in sys.argv:
            print()
        else:
            self.processor = ApiRequestProcessor(
                config=self.config,
                logger=self.logger
            )
            self.processor._load_dotenv()
            self.openapi_spec_generator = OpenApiSpecGenerator()
            self.path_mapper = EnhancedPathMapper(config=self.config)
            self.logger.folder(f"Workspace root: {self.config.workspace_root}")
            self.logger.folder(f"Data directory: {self.config.directories.data_dir}")
            self.logger.folder(f"KDF repository: {self.config.directories.kdf_repo_path}")
            self.logger.folder(f"Reports directory: {self.config.directories.reports_dir}")
            self.logger.folder(f"Branched reports directory: {self.config.directories.branched_reports_dir}")

    def log(self, message, level="info"):
        """Log a message with appropriate level."""
        
        # Map simple levels to logger methods
        log_method = getattr(self.logger, level, self.logger.info)
        log_method(message)
    
    def _print_header(self, title, config_lines=None):
        """Prints a standardized command header."""
        self.log(f"")
        self.logger.start(f"============== Starting: {title} ==============")
        if config_lines:
            self.logger.config("Config:")
            for line in config_lines:
                self.logger.config(f"    - {line}")
        self.log("")

    def _print_footer(self, title, success=True, output_paths=None, report_paths=None):
        """Prints a standardized command footer."""
        self.log("")
        if success:
            self.logger.finish(f"✅ Success: {title}")
        else:
            self.logger.finish(f"❌ Failed: {title}")

        if output_paths:
            self.log("  Output data paths:")
            for path in output_paths:
                self.log(f"    - {path}")
        if report_paths:
            self.log("  Output report paths:")
            for path in report_paths:
                self.log(f"    - {path}")
        self.log("")
        
    def _safe_path(self, path_value: Union[str, Path, None]) -> Path:
        """Safely convert to Path object, handling None values."""
        if path_value is None:
            return Path("")
        return Path(path_value)

    def _get_base_scan_metadata(self, kdf_branch: str) -> Dict[str, Any]:
        """Returns a base dictionary for scan_metadata."""
        kdf_commit = self.git_manager.get_commit_hash(self._safe_path(self.config.directories.kdf_repo_path))
        return {
            "kdf_branch": kdf_branch,
            "mdx_branch": self.mdx_branch,
            "kdf_commit": kdf_commit,
            "mdx_commit": self.mdx_commit,
            "generated_at": datetime.now().isoformat(),
        }

    def _generate_api_methods_table(self):
        self.logger.info("Generating API methods table for index.mdx...")
        paths_file = self.config.directories.mdx_method_paths_report
        template_file = self.workspace_root / 'templates' / 'methods_table.template'
        output_file = self.workspace_root / 'src' / 'pages' / 'komodo-defi-framework' / 'api' / 'index.mdx'

        if not Path(paths_file).exists():
            self.logger.error(f"Method paths file not found: {paths_file}")
            self.logger.error("Please run the 'scan-mdx' command first to generate the report.")
            return

        with open(paths_file, 'r') as f:
            paths_data = json.load(f)

        methods = defaultdict(lambda: {"legacy": "", "v20": "", "v20-dev": ""})
        
        for method_name, file_path_str in paths_data['method_paths']['v1'].items():
            link = self._create_link_for_api_table(method_name, file_path_str)
            methods[method_name]['legacy'] = link

        for method_name, file_path_str in paths_data['method_paths']['v2'].items():
            link = self._create_link_for_api_table(method_name, file_path_str)
            if '/api/v20-dev/' in file_path_str:
                methods[method_name]['v20-dev'] = link
            elif '/api/v20/' in file_path_str:
                methods[method_name]['v20'] = link
        
        sorted_methods = sorted(methods.keys())

        table_rows = []
        for method_name in sorted_methods:
            row = f"| {methods[method_name]['legacy']} | {methods[method_name]['v20']} | {methods[method_name]['v20-dev']} |"
            table_rows.append(row)

        with open(template_file, 'r') as f:
            template_content = f.read()

        final_content = template_content + "\n" + "\n".join(table_rows)

        with open(output_file, 'w') as f:
            f.write(final_content)
        
        self.logger.save(f"Successfully generated API methods table at: {output_file}")

    def _create_link_for_api_table(self, method_name, file_path_str):
        doc_path_obj = Path(file_path_str).relative_to(self.mdx_docs_path)
        doc_path = "/" + doc_path_obj.parent.as_posix()
        slug = self._slugify_for_api_table(method_name)
        escaped_name = method_name.replace('_', '\\_')
        return f"[{escaped_name}]({doc_path}/#{slug})"

    @staticmethod
    def _slugify_for_api_table(text):
        text = text.split("{{")[0].strip()
        text = re.sub(r'[:_\\s]+', '-', text)
        text = re.sub(r'[^a-zA-Z0-9\\-]', '', text)
        return text.lower()
        
    def report_error_responses(self, args):
        """Generates a report of method requests that have error responses."""
        command_title = "Generate Error Response Report"
        self._print_header(command_title)

        methods_with_errors = {
            "v1": {},
            "v2": {}
        }

        postman_dirs = {
            "v1": self.config.directories.postman_json_v1,
            "v2": self.config.directories.postman_json_v2
        }

        for version, version_dir in postman_dirs.items():
            self.logger.info(f"Scanning {version} directory: {version_dir}")
            for method_dir in Path(version_dir).iterdir():
                if not method_dir.is_dir():
                    continue

                method_name = method_dir.name
                error_files = sorted(list(method_dir.glob("error_*.json")))
                request_files = sorted(list(method_dir.glob("request_*.json")))

                if not error_files or not request_files:
                    continue

                self.logger.info(f"Found {len(error_files)} error responses for method: {method_name}")

                requests = []
                for req_file in request_files:
                    try:
                        with open(req_file, 'r') as f:
                            requests.append(json.load(f))
                    except json.JSONDecodeError:
                        self.logger.warning(f"Could not decode JSON from {req_file}")
                    except Exception as e:
                        self.logger.error(f"Error reading {req_file}: {e}")

                if not requests:
                    self.logger.warning(f"No valid request files found for {method_name}, skipping.")
                    continue

                for i, error_file in enumerate(error_files):
                    try:
                        with open(error_file, 'r') as f:
                            error_content_str = f.read()
                            error_response = json.loads(error_content_str)

                        # Skip connection errors
                        if error_response.get("error_type") == "ConnectionError":
                            self.logger.info(f"Skipping connection error for method: {method_name}")
                            continue
                            
                        request_body = requests[i % len(requests)]
                        report_method_name = f"{method_name}_{i+1}"

                        methods_with_errors[version][report_method_name] = {
                            "request": request_body,
                            "error_response": error_response
                        }

                    except json.JSONDecodeError:
                        self.logger.warning(f"Could not decode JSON from error file {error_file}")
                    except Exception as e:
                        self.logger.error(f"Error processing {error_file}: {e}")

        v1_count = len(methods_with_errors["v1"])
        v2_count = len(methods_with_errors["v2"])
        all_count = v1_count + v2_count

        scan_metadata = self._get_base_scan_metadata(args.kdf_branch)
        scan_metadata.update({
            "scanner_type": "ERROR_RESPONSE_SCAN",
            "scanner_version": "KDFTools v1.0.0",
            "generated_during": "error_report_scan",
            "method_source": "Postman JSON examples (dev branch)",
            "is_primary_data_source": False,
            "total_error_responses_found": {
                "all": all_count,
                "v1": v1_count,
                "v2": v2_count
            }
        })
        
        report = {
            "scan_metadata": scan_metadata,
            "methods": methods_with_errors
        }

        report_path = self.config.directories.kdf_error_responses_report
        safe_write_json(report_path, report)
        self.logger.save(f"Saved error responses report to: {report_path}")
        self._print_footer(command_title, success=True, report_paths=[str(report_path)])

    def openapi_command(self, args):
        """Handle openapi subcommand - MDX to OpenAPI conversion."""
        command_title = "MDX to OpenAPI Conversion"
        config = [
        ]
        self._print_header(command_title, config)
        
        success = False
        report_paths = []
        try:
            manager = OpenAPIManager(
                config=self.config,
                verbose=self.verbose,
                logger=self.logger,
                path_mapper=self.path_mapper
            )
            manager.openapi_command()
            
            v1_count = len([m for m in manager.all_methods.values() if m['version'] == 'v1'])
            v2_count = len([m for m in manager.all_methods.values() if m['version'] == 'v2'])
            total_count = v1_count + v2_count

            result = f"✅ All versions processed successfully!\n   📊 V1 methods: {v1_count}\n   📊 V2 methods: {v2_count}\n   📊 Total methods: {total_count}"
            
            self.log(f"{result}")
            
            # NEW: Call tracking file generat
            self.log("📊 Generating OpenAPI tracking files...")
            enums_count = len(manager.mdx_parser.enum_patterns)
            structures_count = len(manager.mdx_parser.common_structures)
            # The config directories are already Path objects after __post_init__
            if self.config.workspace_root:
                source_dirs = [str(Path(self.config.workspace_root) / self.config.directories.mdx_v1),
                                str(Path(self.config.workspace_root) / self.config.directories.mdx_v2)]
            else:
                source_dirs = []
            
            manager.spec_generator.generate_tracking_files(
                "all", manager.success_count, manager.error_count,
                manager.mdx_parser.enum_patterns, structures_count,
                enums_count, source_dirs, manager.all_methods
            )
            
            # Generate review files
            self.log("📊 Generating review files...")
            manager.common_schema_generator.generate_review_files(manager.mdx_parser.enum_patterns)
            
            # Show statistics about generated schemas
            stats = manager.get_stats()
            self.log(f"📊 Generation Statistics:")
            self.log(f"   • Total methods processed: {stats['files_processed']}")
            self.log(f"   • Enums found: {stats['enums_found']}")
            self.log(f"   • Structures found: {stats['structures_found']}")
            
            self.log("🔚 Finished MDX to OpenAPI conversion.")

            v1_methods = [m for m, d in manager.all_methods.items() if d['version'] == 'v1']
            v2_methods = [m for m, d in manager.all_methods.items() if d['version'] == 'v2']
            version_method_counts = {
                'v1': len(v1_methods),
                'v2': len(v2_methods),
                'all': len(v1_methods) + len(v2_methods)
            }
            version_method_counts = sort_version_method_counts(version_method_counts)

            # Generate tracking files
            processed_versions = ["v1", "v2"]
            openapi_report_path = self._generate_openapi_tracking_files(manager, processed_versions, version_method_counts)
            if openapi_report_path:
                report_paths.append(openapi_report_path)
            
            success = True
        except Exception as e:
            self.log(f"An error occurred during OpenAPI generation: {e}", "error")
            self.log(traceback.format_exc(), "error")
            success = False
        finally:
            self._print_footer(command_title, success=success, report_paths=report_paths)
            
    def scan_rust(self, args):
        """Handle scan-rust subcommand - KDF repository scanning with async processing."""
        command_title = "KDF Repository Scan"
        versions = ['v1', 'v2']
            
        config = [
            f"Branch: {args.kdf_branch}",
            f"Versions: {versions}",
        ]
        self._print_header(command_title, config)

        if args.kdf_branch:
            if not self.git_manager.switch_branch(Path(self.config.directories.kdf_repo_path), args.kdf_branch):
                self.logger.error(f"Could not switch to branch {args.kdf_branch}. Aborting rust-scan.")
                self._print_footer(command_title, success=False)
                return

        report_paths = []
        success = False

        async def main():
            nonlocal report_paths, success
            scanner = KDFScanner(
                config=self.config,
                repo_path=self.config.directories.kdf_repo_path,
                branch=args.kdf_branch,
                verbose=self.verbose
            )
            
            repo_info = await scanner.scan_repository_methods_async(versions)
            if repo_info:
                version_method_counts = self._calc_version_method_counts(repo_info)
                # Save results to file
                output_file = await scanner.save_repository_methods_async(repo_info, version_method_counts)
                report_paths.append(output_file)
            
            # Additional logic for processing/reporting on repo_info
            self.logger.finish(f"Async KDF Repository scan completed:")
            self.log(f"📊 Rust Repository Scan Statistics:")
            self.log(f"   • V1 methods processed: {version_method_counts['v1']}")
            self.log(f"   • V2 methods processed: {version_method_counts['v2']}")
            self.log(f"   • Total methods processed: {version_method_counts['all']}")
            self.log("🔚 Finished Rust repository scan.")
            success = True

        try:
            asyncio.run(main())
        except Exception as e:
            self.log(f"❌ An error occurred during Rust repository scan: {e}", "error")
            if self.verbose:
                traceback.print_exc()
            return 1
        self._print_footer(command_title, success=success, output_paths=report_paths)

        
    def _calc_version_method_counts(self, repo_info: Dict[str, UnifiedRepositoryInfo]) -> Dict[str, int]:
        version_method_counts = {version: len(info.methods) for version, info in repo_info.items()}
        return sort_version_method_counts(version_method_counts)
    
    def scan_mdx_command(self, args):
        """Scans MDX files for Komodo DeFi Framework methods."""
        branch = self.config.mdx_branch
        command_title = "Scan MDX Documentation"
        config_lines = [
        ]
        self._print_header(command_title, config_lines)
        
        versions = ['v1', 'v2']
        
        doc_scanner = UnifiedScanner(
            config=self.config,
            verbose=self.verbose 
        )
        doc_results = run_async(doc_scanner.scan_all_files_async(versions))
        self._generate_mdx_method_paths_data(doc_results, versions, args.kdf_branch)
        self._generate_mdx_methods_from_paths_file(self.config.directories.mdx_method_paths_report, versions, args.kdf_branch)
        
        self._generate_api_methods_table()
        self._print_footer(command_title, success=True, output_paths=[self.config.directories.mdx_method_paths_report, self.config.directories.mdx_methods_report])
    

    def _generate_mdx_method_paths_data(self, doc_results, versions, kdf_branch):
        """
        Generate the method paths data structure (primary data source).
        This version uses the ScanMetadata dataclass for standardized metadata.
        """
        method_paths = {}
        version_method_counts = {}

        for version in versions:
            if version not in doc_results:
                if self.verbose:
                    self.logger.warning(f"No documentation found for version {version}")
                version_method_counts[version] = 0
                method_paths[version] = {}
                continue

            version_data = doc_results[version]
            current_version_paths = {}
            if 'mdx_files' in version_data:
                for method_name, file_path in version_data['mdx_files'].items():
                    current_version_paths[method_name] = str(file_path)
            
            method_paths[version] = dict(sorted(current_version_paths.items()))
            version_method_counts[version] = len(current_version_paths)

            if self.verbose:
                self.logger.scan(f"Processing {version.upper()} documentation...")
                self.logger.folder(f"MDX files with paths: {len(current_version_paths)}")

        total_documented_methods = sum(version_method_counts.values())
        version_method_counts.update({"all": total_documented_methods})
        version_method_counts = sort_version_method_counts(version_method_counts)

        metadata = ScanMetadata(
            scanner_type="MDX_METHOD_PATH_MAPPING",
            scanner_version="KDFMethodPathMapper v2.0.0",
            generated_during="mdx_scan",
            method_source="mdx",
            is_primary_data_source=True,
            version_method_counts=version_method_counts
        )

        method_paths_data = {
            "scan_metadata": metadata.to_dict(),
            "method_paths": method_paths
        }
        
        # Add git info to scan_metadata
        base_metadata = self._get_base_scan_metadata(kdf_branch)
        method_paths_data["scan_metadata"].update(base_metadata)

        safe_write_json(self.config.directories.mdx_method_paths_report, method_paths_data)
        self.logger.save(f"Saved documentation paths to: {self.config.directories.mdx_method_paths_report}")
        return method_paths_data

    def _generate_mdx_methods_from_paths_file(self, paths_file_path, versions, kdf_branch):
        """Generates a JSON report of methods from a paths file."""
        # Read the paths file that was just generated
        with open(paths_file_path, 'r', encoding='utf-8') as f:
            paths_data = json.load(f)
        
        # Extract method names ONLY from the method_paths keys (methods with actual MDX documentation files)
        methods_by_version = {}
        method_paths = paths_data.get("method_paths", {})
        total_methods = 0
        
        for version in versions:
            if version in method_paths:
                # Only include methods that have actual MDX documentation files
                methods_with_mdx_files = list(method_paths[version].keys())
                method_list = sorted(methods_with_mdx_files)
                
                methods_by_version[version] = method_list
                total_methods += len(method_list)
                
                self.logger.info(f"{version.upper()}: {len(method_list)} methods with MDX documentation")
            else:
                methods_by_version[version] = []
        
        version_method_counts = {v: len(m) for v, m in methods_by_version.items()}
        version_method_counts = sort_version_method_counts(version_method_counts)

        # Create the methods data structure
        metadata = ScanMetadata(
            scanner_type="MDX_METHOD_PATH_MAPPING",
            scanner_version="KDFMethodPathMapper v2.0.0",
            generated_during="mdx_scan",
            method_source="mdx",
            is_primary_data_source=True,
            version_method_counts=version_method_counts
        )

        methods_data = {
            "scan_metadata": metadata.to_dict(),
            "repository_data": {}
        }
        
        # Add git info to scan_metadata
        base_metadata = self._get_base_scan_metadata(kdf_branch)
        methods_data["scan_metadata"].update(base_metadata)

        # Add version-specific data
        for version in versions:
            methods_data["repository_data"][version] = {
                "branch": self.config.mdx_branch,
                "version": version,
                "source_type": "MDX_DOCUMENTATION",
                "methods": methods_by_version.get(version, []),
                "last_updated": datetime.now().isoformat(),
                "extraction_patterns_used": [
                    "MDX file parsing with path verification",
                    "Derived from method paths file",
                    "Only includes methods with actual MDX files"
                ]
            }
        
        safe_write_json(self.config.directories.mdx_methods_report, methods_data)
        self.logger.save(f"Saved documentation paths to: {self.config.directories.mdx_methods_report}")
        return methods_data
    
    def methods_map_command(self, args):
        """Handle methods-map subcommand."""
        command_title = "Method Mapping and OpenAPI Management"
        config_lines = []
        self._print_header(command_title, config_lines)
        success = False
        try:
            # Initialize the MethodMappingManager
            manager = MethodMappingManager(
                config=self.config,
                verbose=self.verbose
            )
            run_async(manager.save_unified_mapping_async())
            success = True
        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            self.logger.error(traceback.format_exc())
        finally:
            self._print_footer(command_title, success=success)

    def postman_command(self, args):
        """Handle postman subcommand - Postman collection generation."""
        command_title = "Postman Collection Generation"
        versions = ["v1", "v2"]
        
        config_lines = [
            f"Versions: {versions}",
        ]
        self._print_header(command_title, config_lines)
        
        success = False
        try:
            # Step 1: Generate method paths file first (like other commands)
            self.logger.info("🗺️ Generating method mapping with Postman hotlinks...")
            mapper = MethodMappingManager(config=self.config, verbose=self.verbose)
            
            # Use async mapping for better performance and generate paths file
            run_async(mapper.save_unified_mapping_async())
            
            # Step 2: Generate Postman collections
            self.logger.info("📮 Generating Postman collections...")
            # Initialize manager
            manager = PostmanManager(config=self.config, verbose=self.verbose)
            
            # Generate collections
            results = manager.generate_collections(versions)
            summary = manager.generate_summary_report(results)
            
            # Step 3: Generate tracking file - read from the method paths file we just created
            self._generate_postman_tracking_file_from_latest_data(versions)
            
            self.logger.success("Postman collection generation completed!")
            print(summary)
            success = True
            
        except Exception as e:
            self.log(f"❌ Error in postman command: {e}", "error")
            if self.verbose:
                self.log(f"Full traceback: {traceback.format_exc()}", "error")
        
        self._print_footer(command_title, success=success)
        return 0 if success else 1
    
    def json_extract_command(self, args):
        """Handle json-extract subcommand - Extract JSON examples from MDX files."""
        self.log("Starting JSON example extraction from MDX files...")
        
        try:
            # Initialize components
            mapper = MethodMappingManager(verbose=self.verbose)
            extractor = MdxJsonExampleExtractor(verbose=self.verbose)
            
            # Get unified mapping using async for better performance (consistent with other commands)
            if self.verbose:
                self.logger.info("Using async processing for method mapping...")
            
            unified_mapping = mapper.create_unified_mapping(scan_yaml=False, scan_json=False)

            versions = ['v1', 'v2']
            
            # Initialize tracking data
            all_extracted_methods = {}
            extraction_stats = {
                'total_extracted': 0,
                'total_methods_processed': 0,
                'total_examples_found': 0,
                'methods_with_examples': 0,
                'methods_without_examples': 0,
                'versions_processed': versions,
                'v1': {'total_extracted': 0, 'total_examples_found': 0, 'methods_with_examples': 0},
                'v2': {'total_extracted': 0, 'total_examples_found': 0, 'methods_with_examples': 0}
            }
            
            for version in versions:
                if version not in unified_mapping:
                    self.log(f"No methods found for version {version}", "warning")
                    continue
                
                methods = unified_mapping[version]
                version_count = 0
                version_examples = 0
                version_methods_with_examples = 0
                
                self.log(f"Processing {len(methods)} methods for {version.upper()}")
                extraction_stats['total_methods_processed'] += len(methods)
                
                for method_name, mapping in methods.items():
                    if not mapping.has_mdx:
                        self.logger.warning(f"Skipping {method_name}: No MDX file found")
                        continue
                    
                    # Extract examples from MDX
                    examples = extractor.extract_from_mdx_file(method_name, mapping, version)
                    
                    if not examples:
                        self.logger.warning(f"{method_name}: No JSON examples found")
                        extraction_stats['methods_without_examples'] += 1
                        continue
                    
                    # Clean method names from examples (fix escaped underscores)
                    cleaned_examples = []
                    for example in examples:
                        # Clean the method name in the example
                        cleaned_method_name = example.method_name.replace('\\_', '_')
                        # Create a new example with cleaned method name
                        cleaned_example = ExtractedExample(
                            method_name=cleaned_method_name,
                            version=example.version,
                            example_type=example.example_type,
                            content=example.content,
                            source_file=example.source_file,
                            line_number=example.line_number,
                            description=example.description
                        )
                        cleaned_examples.append(cleaned_example)                    

                    self.logger.info(f"{method_name:64} Found {len(cleaned_examples)} examples")
                    
                    # Store method info for tracking
                    if method_name not in all_extracted_methods:
                        all_extracted_methods[method_name] = {
                            'method_name': method_name.replace('\\_', '_'),  # Clean method name
                            'version': version,
                            'mdx_path': mapping.mdx_path if hasattr(mapping, 'mdx_path') else '',
                            'examples_count': len(cleaned_examples),
                            'examples': []
                        }
                    # Save each example
                    for i, example in enumerate(cleaned_examples, 1):

                        # Clean method name for folder creation
                        # The canonical method name (e.g., 'task::enable_utxo::init') is converted to
                        # a directory-safe format by replacing '::' with hyphens.
                        # Underscores within method parts are preserved (e.g., 'task-enable_utxo-init').
                        folder_name = example.method_name.replace("::", "-")
                        
                        # Define output directory based on version
                        output_dir = self.config.directories.postman_json_v1 if version == 'v1' else self.config.directories.postman_json_v2
                        
                        # Create full path for the example file
                        example_dir = output_dir / folder_name
                        
                        ensure_directory_exists(example_dir)

                        # Generate filename
                        filename = f"{example.example_type}_{i}.json"
                        output_path = example_dir / filename
                        all_extracted_methods[method_name].update({
                            'json_examples_path': str(example_dir),
                        })
                        if self._save_json_example(output_path, example):
                            version_count += 1
                            # Track example info
                            all_extracted_methods[method_name]['examples'].append({
                                'example_num': i,
                                'description': example.description,
                                'example_type': example.example_type,
                                'line_number': example.line_number
                            })
                            # self.logger.save(f"{method_name}: Saved example {i} to {self.config.directories.get_relative_path(str(output_path))}")
                    
                    version_examples += len(cleaned_examples)
                    version_methods_with_examples += 1
                
                self.logger.finish(f"{version.upper()}: {version_count} examples extracted from {version_methods_with_examples} methods")
                
                # Update global stats
                extraction_stats['total_extracted'] += version_count
                extraction_stats['total_examples_found'] += version_examples
                extraction_stats['methods_with_examples'] += version_methods_with_examples

                # Update version-specific stats
                if version in extraction_stats:
                    extraction_stats[version]['total_extracted'] = version_count
                    extraction_stats[version]['total_examples_found'] = version_examples
                    extraction_stats[version]['methods_with_examples'] = version_methods_with_examples
            
            # Generate tracking files
            self._generate_json_tracking_files(all_extracted_methods, extraction_stats, args.kdf_branch)
            
            self.log(f"🎯 Total: {extraction_stats['total_extracted']} JSON examples extracted from {extraction_stats['methods_with_examples']} methods", "success")
            return 0
            
        except Exception as e:
            self.log(f"JSON extraction failed: {e}", "error")
            return 1
    
    def review_draft_quality_command(self, args):
        """Handle review-draft-quality subcommand - Compare generated docs with live versions."""
        self.log("Starting draft quality analysis...")
        
        # Validate arguments
        if bool(args.generated) != bool(args.live):
            self.log("❌ Error: Both --generated and --live must be specified together, or neither", "error")
            return 1
        
        if args.generated and args.live:
            if not args.generated.exists():
                self.log(f"❌ Generated file not found: {args.generated}", "error")
                return 1
            if not args.live.exists():
                self.log(f"❌ Live file not found: {args.live}", "error")
                return 1
        
        try:
            # Create analyzer with custom directories if provided
            analyzer = DraftsManager(
                generated_docs_dir=args.generated_dir,
                live_docs_dir=args.live_dir
            )
            
            # Run analysis
            self.log("🔍 Analyzing documentation quality...")
            
            if args.format == 'json':
                # TODO: Implement JSON output
                self.log("JSON format not yet implemented, using markdown", "warning")
            
            report = analyzer.review_draft_quality(
                generated_path=args.generated,
                live_path=args.live,
                output_file=args.output
            )
            
            # Print summary to console
            lines = report.split('\n')
            summary_end = next((i for i, line in enumerate(lines) if line.startswith('## Top Improvement')), len(lines))
            summary = '\n'.join(lines[:summary_end + 10])  # Include a bit of the improvements section
            
            self.logger.separator("DRAFT QUALITY ANALYSIS SUMMARY")
            self.logger.separator("="*60)
            self.logger.info(summary)
            self.logger.separator("="*60)
            
            if args.output:
                self.log(f"Full report saved to: {args.output}", "success")
            else:
                import glob
                if self.config.directories.branched_reports_dir:
                    latest_report_files = glob.glob(str(self.config.directories.branched_reports_dir / "draft_quality_report.md"))
                else:
                    latest_report_files = []
                if latest_report_files:
                    latest_report = max(latest_report_files, key=lambda p: Path(p).stat().st_mtime)
                    self.log(f"Full report saved to: {latest_report}", "success")
            
            self.log("Draft quality analysis completed successfully!", "success")
            return 0
            
        except Exception as e:
            self.log(f"❌ Draft quality analysis failed: {e}", "error")
            return 1
    
    def scan_existing_docs_command(self, args):
        """Handle scan-existing-docs subcommand - Scan existing KDF documentation to extract method patterns."""
        self.log("Starting existing documentation scan...")
        
        try:
            # Create scanner instance
            scanner = ExistingDocsScanner(
                docs_base_path=Path(args.docs_path) if args.docs_path else None,
                verbose=self.verbose
            )
            
            # Perform the scan
            if args.async_scan:
                # Use async scanning for better performance
                patterns = asyncio.run(scanner.scan_and_extract_patterns_async())
            else:
                patterns = scanner.scan_and_extract_patterns()
            
            if not patterns:
                self.log("⚠️  No documentation patterns found", "warning")
                return 1
            
            # Save patterns to file
            output_file = Path(args.output) if args.output else None
            saved_file = scanner.save_patterns(output_file)
            
            # Generate analysis report if requested
            if args.generate_report:
                report = scanner.generate_analysis_report()
                report_file = saved_file.parent / f"{saved_file.stem}_analysis_report.md"
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report)
                self.log(f"📊 Analysis report saved: {report_file}", "success")
            
            # Show summary
            if self.verbose:
                analysis = scanner.analyze_patterns()
                self.log(f"✅ Scan completed successfully:", "success")
                self.log(f"   📄 Patterns saved: {saved_file}")
                self.log(f"   📊 Total methods: {analysis['total_methods']}")
                self.log(f"   📂 Categories: {len(analysis['method_categories'])}")
                self.log(f"   🔧 Common parameters: {len(analysis['common_parameters'])}")
                
                if args.show_categories:
                    self.log("📂 Method categories:")
                    for category, methods in analysis['method_categories'].items():
                        self.log(f"   {category}: {len(methods)} methods")
            
            return 0
            
        except Exception as e:
            self.log(f"❌ Existing docs scan failed: {e}", "error")
            return 1
    
    def generate_docs_command(self, args):
        """Handle generate-docs subcommand - Generate documentation for missing KDF methods."""
        self.log("Starting comprehensive documentation generation...")
        
        try:
            # Create generator instance
            generator = MdxGenerator()
            
            # Determine which methods to generate
            selected_methods = []
            
            # Load all missing methods from unified mapping
            missing_methods = self._load_missing_methods()
            
            if not missing_methods:
                self.log("⚠️  No missing methods found in unified mapping", "warning")
                return 1
            
            # Convert to list of tuples
            for version, methods in missing_methods.items():
                for method in methods:
                    selected_methods.append((method, version))
            
            # Show options and let user select (if interactive)
            if args.interactive and selected_methods:
                selected_methods = self._select_methods_interactively(selected_methods)
            
            self.log(f"📋 Found {len(selected_methods) if selected_methods else 0} missing methods to generate")
        
            if not selected_methods:
                self.log("❌ No methods selected for generation", "error")
                return 1
            
            # Generate the documentation
            generated_files = self._generate_documentation_for_methods(generator, selected_methods)
            
            if generated_files:
                # Show results
                self.log(f"✅ Documentation generation completed!", "success")
                self.log(f"   📄 Generated: {len(generated_files)} method documentation files")
                
                if self.verbose:
                    for method, file_path in generated_files.items():
                        self.log(f"   📄 {method}: {file_path}")
                
                # Create summary report if requested
                if args.generate_summary:
                    summary_file = Path(args.output_dir or "data") / "generation_summary.md"
                    self._create_generation_summary(selected_methods, generated_files, summary_file)
                    self.log(f"📊 Generation summary saved: {summary_file}")
                
                return 0
            else:
                self.log("❌ No documentation was generated", "error")
                return 1
                
        except Exception as e:
            self.log(f"❌ Documentation generation failed: {e}", "error")
            if self.verbose:
                self.log(traceback.format_exc(), "error")
            return 1
    
    def _select_methods_interactively(self, methods_list):
        """Placeholder for interactive method selection."""
        pass

    def _create_generation_summary(self, selected_methods, generated_files, summary_file):
        with open(summary_file, "w") as f:
            f.write(f"Generated {len(generated_files)} files for {len(selected_methods)} methods.\n\n")
            f.write("Generated Files:\n" + "\n".join(f"- {Path(p).name}" for p in generated_files) + "\n\n")
            f.write("Selected Methods:\n" + "\n".join(f"- {m}" for m in selected_methods) + "\n")

    def _load_missing_methods(self):
        """Load missing methods from unified mapping."""
        try:
            # Load unified mapping
            mapper = MethodMappingManager(config=self.config, verbose=self.verbose)
            unified_mapping = mapper.create_unified_mapping()
            
            # Find missing methods by comparing with Rust methods
            missing_methods = {"v1": [], "v2": []}
            
            # Load Rust methods for comparison
            rust_methods = {}
            rust_scan_files = glob.glob(str(self.config.directories.rust_methods_report))
            if rust_scan_files:
                with open(rust_scan_files[0], 'r') as f:
                    rust_data = json.load(f)
                for version in ["v1", "v2"]:
                    if version in rust_data.get('repository_data', {}):
                        rust_methods[version] = set(rust_data['repository_data'][version].get('methods', []))
            
            # Find missing methods
            for version in ["v1", "v2"]:
                if version in unified_mapping:
                    documented_methods = set(unified_mapping[version].keys())
                    if version in rust_methods:
                        missing_methods[version] = list(rust_methods[version] - documented_methods)
            
            return missing_methods
        except Exception as e:
            self.log(f"Error loading missing methods: {e}", "error")
            return {"v1": [], "v2": []}

    def _generate_documentation_for_methods(self, generator, selected_methods):
        """Generate documentation for selected methods."""
        generated_files = {}
        
        for method, version in selected_methods:
            try:
                # Create basic method details for generation
                method_details = MethodDetails(
                    name=method,
                    human_title=method.replace("_", " ").title(),
                    description=f"Documentation for {method}",
                    api_tag="API-v2" if version == "v2" else "API-v1",
                    request_params=[],
                    response_params=[],
                    error_types=[],
                    source_files=[],
                    examples=[]
                )
                
                # Generate documentation
                content = generator.generate(method_details)
                
                # Save to file
                output_dir = Path("data/generated_docs")
                method_path = "/".join(method.split("::"))
                method_dir = output_dir / version / method_path
                method_dir.mkdir(parents=True, exist_ok=True)
                
                output_file = method_dir / "index.mdx"
                output_file.write_text(content, encoding="utf-8")
                
                generated_files[method] = str(output_file)
                
            except Exception as e:
                self.log(f"Error generating documentation for {method}: {e}", "error")
        
        return generated_files

    async def _save_json_example_async(self, output_path: Path, example: ExtractedExample) -> bool:
        """Asynchronously save a single JSON example to the correct file path."""
        safe_write_json(output_path, example.content, indent=2)
        return True

    def _save_json_example(self, output_path: Path, example: ExtractedExample) -> bool:
        return run_async(self._save_json_example_async(output_path, example))

    def _generate_json_tracking_files(self, all_extracted_methods: Dict[str, Any], extraction_stats: Dict[str, Any], kdf_branch: str) -> "tuple[Dict[str, Any], None]":
        """Top-level function to generate all JSON-related tracking files."""
        self.log("Generating JSON tracking files...", "info")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        method_paths_file = self._generate_json_method_paths_file(all_extracted_methods, kdf_branch)
        methods_file = self._generate_json_methods_file(method_paths_file, extraction_stats, kdf_branch)
        return method_paths_file, methods_file
    
    def _generate_openapi_tracking_files(self, openapi_manager: OpenAPIManager, versions: List[str], version_method_counts: Dict[str, int]) -> str:
        """Generates all necessary tracking files for OpenAPI."""

        return self.openapi_spec_generator._generate_openapi_method_paths_file(
            all_methods=openapi_manager.all_methods,
            path_mapper=openapi_manager.path_mapper,
            versions=versions,
            version_method_counts=version_method_counts
        )  

    def _generate_json_method_paths_file(self, all_extracted_methods: Dict[str, Any], kdf_branch: str) -> Dict[str, Any]:
        """Creates a JSON file mapping each method to its JSON examples path."""
        self.logger.info("Generating JSON method paths file...")
        v1_methods = {data["method_name"]: data["json_examples_path"] for data in all_extracted_methods.values() if data["version"] == "v1"}
        v2_methods = {data["method_name"]: data["json_examples_path"] for data in all_extracted_methods.values() if data["version"] == "v2"}
        
        scan_metadata = self._get_base_scan_metadata(kdf_branch)
        scan_metadata.update({
            "scanner_version": "KDF-MDX-JSON-Example-Extractor v1.0.0",
            "scanner_type": "MDX_JSON_EXAMPLE_EXTRACTOR",
            "total_methods": {
                "all": len(v1_methods) + len(v2_methods),
                "v1": len(v1_methods),
                "v2": len(v2_methods)
            },
            "versions_processed": ["v1", "v2"],
            "is_primary_data_source": False
        })
        paths_data = {
            "scan_metadata": scan_metadata,
            "method_paths": {
                "v1": v1_methods,
                "v2": v2_methods
            }
        }

        file_path = self.config.directories.mdx_json_example_method_paths_report
        safe_write_json(file_path, paths_data, indent=2)
        
        log_path = self.config.directories.get_relative_path(str(file_path))
        self.logger.save(f"Saved Postman method paths mapping to: {log_path}")
        self.log(f"📊 V1: {len(paths_data['method_paths']['v1'])} methods")
        self.log(f"📊 V2: {len(paths_data['method_paths']['v2'])} methods")
        return paths_data

    def _generate_json_methods_file(self, method_paths_data: Dict[str, Any], extraction_stats: Dict[str, Any], kdf_branch: str) -> None:
        """Generates a JSON file that maps each method to its extracted JSON examples."""
        self.log("Generating JSON methods file...")
        v1_methods = list(method_paths_data["method_paths"]["v1"].keys())
        v2_methods = list(method_paths_data["method_paths"]["v2"].keys())
        
        scan_metadata = self._get_base_scan_metadata(kdf_branch)
        scan_metadata.update({
            "scanner_version": "KDF-MDX-JSON-Example-Extractor v1.0.0",
            "scanner_type": "MDX_JSON_EXAMPLE_EXTRACTOR",
            "total_methods": {
                "all": len(v1_methods) + len(v2_methods),
                "v1": len(v1_methods),
                "v2": len(v2_methods)
            },
            "versions_processed": ["v1", "v2"],
            "is_primary_data_source": False
        })
        methods_data = {
            "scan_metadata": scan_metadata,
            "repository_data": {
                "v1": {
                    "methods": v1_methods,
                    "extraction_patterns_used": ["JSON extraction from MDX files"],
                    "total_extracted": extraction_stats['v1']['total_extracted'],
                    "total_methods_processed": len(v1_methods),
                    "total_examples_found": extraction_stats['v1']['total_examples_found']
                },
                "v2": {
                    "methods": v2_methods,
                    "extraction_patterns_used": ["JSON extraction from MDX files"],
                    "total_extracted": extraction_stats['v2']['total_extracted'],
                    "total_methods_processed": len(v2_methods),
                    "total_examples_found": extraction_stats['v2']['total_examples_found']
                }
            }
        }
        file_path = self.config.directories.mdx_json_example_methods_report
        safe_write_json(file_path, methods_data, indent=2)
        
        log_path = self.config.directories.get_relative_path(str(file_path))
        self.logger.save(f"Saved JSON extraction examples summary to: {log_path}")
        self.log(f"📊 V1: {extraction_stats['v1']['total_examples_found']} examples from {extraction_stats['v1']['methods_with_examples']} methods")
        self.log(f"📊 V2: {extraction_stats['v2']['total_examples_found']} examples from {extraction_stats['v2']['methods_with_examples']} methods")

    def _generate_postman_tracking_file_from_latest_data(self, versions: List[str]) -> None:
        """Placeholder for generating Postman tracking file."""
        pass

    def setup_postman_parser(self, subparsers):
        """Setup parser for the postman command."""
        parser = subparsers.add_parser(
            'postman',
            help='Generate Postman collections from OpenAPI specs.',
            description='Converts OpenAPI specifications into Postman collections for easier API testing and integration.'
        )
        parser.set_defaults(func=self.postman_command)

    def setup_openapi_parser(self, subparsers):
        """Setup parser for the openapi command."""
        parser = subparsers.add_parser(
            'openapi',
            help='Generate OpenAPI specs from MDX documentation.',
            description='Processes MDX documentation files to create OpenAPI specifications'
        )
        parser.set_defaults(func=self.openapi_command)

    def setup_scan_mdx_parser(self, subparsers):
        """Sets up argument parser for the mdx_scan command."""
        parser = subparsers.add_parser('scan-mdx', help='Scan MDX files for method info.')
        parser.set_defaults(func=self.scan_mdx_command)

    
    def setup_scan_rust_parser(self, subparsers):
        """Setup parser for the scan-rust command."""
        parser = subparsers.add_parser(
            'scan-rust', 
            help='Scan KDF Rust repository for RPC methods.',
            description='Scans the Komodo DeFi Framework Rust repository to find RPC methods.'
        )
        parser.set_defaults(func=self.scan_rust)


    def setup_map_methods_parser(self, subparsers):
        """Setup parser for the map-methods command."""
        parser = subparsers.add_parser(
            'map_methods',
            help='Generate a unified mapping of all method-related files.',
            description='Creates a comprehensive JSON file that maps each method to its corresponding MDX, OpenAPI, and Postman files.'
        )
        parser.add_argument(
            '--remove',
            type=str,
            help='Remove all files associated with a specific method.'
        )
        parser.add_argument(
            '--debug',
            type=str,
            help='Debug method matching for a specific method.'
        )
        parser.set_defaults(func=self.methods_map_command)

    def setup_json_extract_parser(self, subparsers):
        """Setup parser for the json-extract command."""
        parser = subparsers.add_parser(
            'json-extract',
            help='Extract JSON examples from MDX files.',
            description='Extracts JSON request/response examples from MDX documentation.'
        )
        parser.set_defaults(func=self.json_extract_command)

    def setup_review_draft_quality_parser(self, subparsers):
        """Setup parser for the review-draft-quality command."""
        parser = subparsers.add_parser(
            'review-draft-quality',
            help='Compare generated documentation with live versions.',
            description='Compares generated documentation with live versions to assess quality.'
        )
        parser.add_argument(
            '--generated', type=Path, required=True,
            help='Path to the generated documentation file.'
        )
        parser.add_argument(
            '--live', type=Path, required=True,
            help='Path to the live documentation file.'
        )
        parser.add_argument(
            '--generated-dir', type=Path,
            help='Directory containing generated documentation files.'
        )
        parser.add_argument(
            '--live-dir', type=Path,
            help='Directory containing live documentation files.'
        )
        parser.add_argument(
            '--output', type=Path,
            help='Path to save the review report.'
        )
        parser.add_argument(
            '--format', choices=['json', 'markdown'], default='markdown',
            help='Format of the review report.'
        )
        parser.add_argument(
            '--kdf-branch', type=str, default='dev',
            help='Specify the branch of the KDF repository to scan and check out.'
        )
        parser.set_defaults(func=self.review_draft_quality_command)

    def setup_scan_existing_docs_parser(self, subparsers):
        """Setup parser for the scan-existing-docs command."""
        parser = subparsers.add_parser(
            'scan-existing-docs',
            help='Scan existing KDF documentation to extract method patterns.',
            description='Scans existing KDF documentation to extract method patterns.'
        )
        parser.add_argument(
            '--docs-path', type=Path,
            help='Path to the directory containing existing documentation files.'
        )
        parser.add_argument(
            '--async-scan', action='store_true',
            help='Use asynchronous scanning for better performance.'
        )
        parser.add_argument(
            '--output', type=Path,
            help='Path to save the extracted method patterns.'
        )
        parser.add_argument(
            '--generate-report', action='store_true',
            help='Generate an analysis report of the extracted method patterns.'
        )
        parser.add_argument(
            '--show-categories', action='store_true',
            help='Show method categories in the analysis report.'
        )
        parser.add_argument(
            '--kdf-branch', type=str, default='dev',
            help='Specify the branch of the KDF repository to scan and check out.'
        )
        parser.set_defaults(func=self.scan_existing_docs_command)

    def setup_generate_docs_parser(self, subparsers):
        """Sets up the argument parser for the `generate-docs` command."""
        parser = subparsers.add_parser(
            "generate-docs",
            help="Generate MDX documentation from templates for specified methods.",
            description="This command automates the creation of MDX documentation files from pre-defined templates. It can use a list of methods from a file or allow interactive selection.",
            formatter_class=argparse.RawTextHelpFormatter
        )
        parser.add_argument(
            "-m", "--methods",
            nargs='+',
            help="A list of one or more method names to generate documentation for."
        )
        parser.add_argument(
            "-f", "--methods-file",
            type=str,
            help="Path to a file containing a list of method names (one per line)."
        )
        parser.add_argument(
            "-i", "--interactive",
            action="store_true",
            help="Use interactive mode to select methods from a list."
        )
        parser.add_argument(
            "-t", "--template",
            type=str,
            default="default",
            help="The template to use for generation (e.g., 'default', 'comprehensive')."
        )
        parser.add_argument(
            "-o", "--output-dir",
            type=str,
            default=str(Path(self.config.directories.data_dir) / "generated_docs") if self.config.directories.data_dir else "generated_docs",
            help="The directory to save the generated MDX files."
        )
        parser.add_argument(
            '--kdf-branch', type=str, default='dev',
            help='Specify the branch of the KDF repository to scan and check out.'
        )
        parser.set_defaults(func=self.generate_docs_command)

    def setup_gap_analysis_parser(self, subparsers):
        """Sets up the argument parser for the `gap-analysis` command."""
        parser = subparsers.add_parser(
            "gap-analysis",
            help="Perform gap analysis between Rust and MDX methods.",
            description="Compares methods found in the Rust repository against those documented in MDX files."
        )
        parser.set_defaults(func=self.gap_analysis_command)

    def setup_get_kdf_responses_parser(self, subparsers):
        """Sets up argument parser for the get_kdf_responses command."""
        parser = subparsers.add_parser(
            'get-kdf-responses',
            help='Get KDF responses for a given method.',
            description='Gets API responses for a given method and saves them to JSON files.'
        )
        parser.add_argument('--method', type=str, help='The method to get responses for.')
        parser.add_argument('--clean', action='store_true', help='Clean JSON files before running.')
        parser.add_argument('--substitute-defaults', action='store_true', help='Use test parameter substitution for coin/ticker fields.')
        parser.set_defaults(func=self.get_kdf_responses_command)
        
    def setup_v2_no_param_report_parser(self, subparsers):
        """Sets up argument parser for the generate_v2_no_param_methods_report command."""
        parser = subparsers.add_parser(
            "v2-no-param-methods-report",
            help="Generate a report of V2 methods that don't have parameters.",
            description="Generates a report of V2 methods that don't have parameters."
        )
        parser.set_defaults(func=self.generate_v2_no_param_methods_report)

    def setup_build_container_parser(self, subparsers):
        """Sets up argument parser for the build-container command."""
        parser = subparsers.add_parser('build-container', help='Build KDF container image.')
        parser.add_argument('--kdf-branch', type=str, default='dev', help='KDF branch to build.')
        parser.add_argument('--commit', type=str, help='Commit hash to build.')
        parser.set_defaults(func=self.build_container_command)

    def setup_start_container_parser(self, subparsers):
        """Sets up argument parser for the start-container command."""
        parser = subparsers.add_parser('start-container', help='Start KDF container.')
        parser.add_argument('--kdf-branch', type=str, default='dev', help='KDF branch to use.')
        parser.add_argument('--commit', type=str, help='Commit hash to use.')
        parser.set_defaults(func=self.start_container_command)
    
    def setup_stop_container_parser(self, subparsers):
        """Sets up argument parser for the stop-container command."""
        parser = subparsers.add_parser('stop-container', help='Stop KDF container.')
        parser.set_defaults(func=self.stop_container_command)

    def setup_switch_kdf_branch_parser(self, subparsers):
        """Sets up argument parser for the switch-kdf-branch command."""
        parser = subparsers.add_parser('switch-kdf-branch', help='Switch KDF branch.')
        parser.add_argument('branch', type=str, help='Branch to switch to.')
        parser.set_defaults(func=lambda args: self.git_manager.switch_branch(Path(self.config.directories.kdf_repo_path), args.branch) if self.config.directories.kdf_repo_path else None)

    def setup_get_json_example_method_paths_parser(self, subparsers):
        """Sets up argument parser for the get-json-example-method-paths command."""
        parser = subparsers.add_parser('get-json-example-method-paths', help='Get JSON example method paths.')
        parser.set_defaults(func=lambda args: self.get_json_example_method_paths())

    def setup_report_error_responses_parser(self, subparsers):
        """Sets up argument parser for the report-error-responses command."""
        parser = subparsers.add_parser('report-error-responses', help='Generate a report of method requests that have error responses.')
        parser.set_defaults(func=self.report_error_responses)

    def setup_extract_errors_parser(self, subparsers):
        """Setup parser for the extract-errors command."""
        parser = subparsers.add_parser('extract-errors', help='Extract error enums from KDF source')
        parser.add_argument(
            '--source', type=str, required=True,
            help="The source to scan (e.g., 'rust' or 'mdx')."
        )
        parser.add_argument(
            '--kdf-branch', type=str, default='dev',
            help='Specify the branch of the KDF repository to scan and check out.'
        )
        parser.set_defaults(func=self.extract_errors_command)

    def setup_balances_parser(self, subparsers):
        """Sets up argument parser for the balances command."""
        parser = subparsers.add_parser(
            "balances",
            help="Get address and balance info for test coins.",
            description="Checks balances for PRIMARY_COIN, SECONDARY_COIN and NODE_BALANCE_COINS on all nodes."
        )
        parser.add_argument('--clean', action='store_true', help='Clean JSON files before running.')
        parser.set_defaults(func=self.balances_command)

    def setup_sync_parser(self, subparsers):
        """Setup parser for the sync command."""
        parser = subparsers.add_parser(
            'sync',
            help='Bidirectional sync between MDX docs and Postman collections.',
            description='Sync requests and responses between MDX documentation and Postman collections.'
        )
        parser.add_argument(
            'direction',
            choices=['docs-to-postman', 'postman-to-docs', 'bidirectional'],
            help='Sync direction'
        )
        parser.add_argument(
            '--method-filter',
            type=str,
            help='Filter to specific method name'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.set_defaults(func=self.sync_command)

    def sync_command(self, args):
        """Handle sync subcommand."""
        command_title = f"Sync: {args.direction}"
        config_lines = [
            f"Direction: {args.direction}",
            f"Method filter: {args.method_filter or 'All methods'}",
            f"Dry run: {args.dry_run}",
        ]
        self._print_header(command_title, config_lines)
        try:
            # Create sync CLI with main config
            sync_cli = SyncCLI(self.config)
            # Run the appropriate sync operation
            if args.direction == 'docs-to-postman':
                result = asyncio.run(sync_cli.sync_docs_to_postman(args.method_filter, args.dry_run))
            elif args.direction == 'postman-to-docs':
                result = asyncio.run(sync_cli.sync_postman_to_docs(args.method_filter, args.dry_run))
            elif args.direction == 'bidirectional':
                result = asyncio.run(sync_cli.bidirectional_sync(args.method_filter, args.dry_run))
            else:
                self.logger.error(f"Unknown sync direction: {args.direction}")
                return 1
            success = result == 0
            self._print_footer(command_title, success=success)
            return result
        except Exception as e:
            self.logger.error(f"Sync command failed: {e}")
            self._print_footer(command_title, success=False)
            return 1

    def setup_workflow_parsers(self, subparsers):
        """Setup parsers for workflow commands."""
        
        # WalletConnect workflow
        wc_parser = subparsers.add_parser(
            'walletconnect-workflow',
            help='Launch interactive WalletConnect session management TUI.',
            description='Opens an interactive interface for managing WalletConnect sessions.'
        )
        wc_parser.add_argument(
            '--kdf-branch',
            type=str,
            default='dev',
            help='Specify the KDF branch to use'
        )
        wc_parser.set_defaults(func=self.walletconnect_workflow_command)
        
        # Trezor workflow
        trezor_parser = subparsers.add_parser(
            'trezor-workflow',
            help='Launch interactive Trezor device management TUI.',
            description='Opens an interactive interface for managing Trezor devices.'
        )
        trezor_parser.add_argument(
            '--kdf-branch',
            type=str,
            default='dev',
            help='Specify the KDF branch to use'
        )
        trezor_parser.set_defaults(func=self.trezor_workflow_command)

    def walletconnect_workflow_command(self, args):
        """Handle WalletConnect workflow command."""
        command_title = "WalletConnect Workflow"
        config_lines = [
            f"KDF Branch: {args.kdf_branch}",
        ]
        self._print_header(command_title, config_lines)
        
        try:
            import subprocess
            import sys
            from pathlib import Path
            
            # Get the path to the walletconnect.py script
            script_path = Path(__file__).parent / "tui" / "walletconnect.py"
            
            if not script_path.exists():
                self.logger.error(f"WalletConnect TUI not found at: {script_path}")
                self._print_footer(command_title, success=False)
                return 1
            
            # Launch the WalletConnect TUI
            result = subprocess.run([sys.executable, str(script_path)], 
                                 capture_output=False, text=True)
            
            success = result.returncode == 0
            self._print_footer(command_title, success=success)
            return result.returncode
            
        except Exception as e:
            self.logger.error(f"Error launching WalletConnect TUI: {e}")
            self._print_footer(command_title, success=False)
            return 1

    def trezor_workflow_command(self, args):
        """Handle Trezor workflow command."""
        command_title = "Trezor Workflow"
        config_lines = [
            f"KDF Branch: {args.kdf_branch}",
        ]
        self._print_header(command_title, config_lines)
        
        try:
            import subprocess
            import sys
            from pathlib import Path
            
            # Get the path to the trezor.py script
            script_path = Path(__file__).parent / "tui" / "trezor.py"
            
            if not script_path.exists():
                self.logger.error(f"Trezor TUI not found at: {script_path}")
                self._print_footer(command_title, success=False)
                return 1
            
            # Launch the Trezor TUI
            result = subprocess.run([sys.executable, str(script_path)], 
                                 capture_output=False, text=True)
            
            success = result.returncode == 0
            self._print_footer(command_title, success=success)
            return result.returncode
            
        except Exception as e:
            self.logger.error(f"Error launching Trezor TUI: {e}")
            self._print_footer(command_title, success=False)
            return 1

    def main(self):
        """Main entry point for the KDF Tools CLI."""
        
        parser = argparse.ArgumentParser(
            description='Komodo DeFi Framework Tools - Unified CLI',
            formatter_class=argparse.RawTextHelpFormatter
        )
        parser.add_argument(
            '--kdf-branch', type=str, default='dev',
            help='Specify the branch of the KDF repository to use for all commands.'
        )
        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        self.setup_openapi_parser(subparsers)
        self.setup_postman_parser(subparsers)
        self.setup_scan_rust_parser(subparsers)
        self.setup_scan_mdx_parser(subparsers)
        self.setup_map_methods_parser(subparsers)
        self.setup_json_extract_parser(subparsers)
        self.setup_review_draft_quality_parser(subparsers)
        self.setup_scan_existing_docs_parser(subparsers)
        self.setup_generate_docs_parser(subparsers)
        self.setup_gap_analysis_parser(subparsers)
        self.setup_get_kdf_responses_parser(subparsers)
        self.setup_v2_no_param_report_parser(subparsers)
        self.setup_build_container_parser(subparsers)
        self.setup_start_container_parser(subparsers)
        self.setup_stop_container_parser(subparsers)
        self.setup_switch_kdf_branch_parser(subparsers)
        self.setup_get_json_example_method_paths_parser(subparsers)
        self.setup_report_error_responses_parser(subparsers)
        self.setup_extract_errors_parser(subparsers)
        self.setup_balances_parser(subparsers)
        self.setup_sync_parser(subparsers)  # Add sync subcommand
        self.setup_workflow_parsers(subparsers)  # Add workflow subcommands
        
        args = parser.parse_args()

        if hasattr(args, 'func'):
            try:
                return args.func(args)
            except Exception as e:
                self.logger.error(f"An error occurred executing command '{args.command}': {e}")
                self.logger.error(traceback.format_exc())
                return 1
        else:
            parser.print_help()
            return 1

    def gap_analysis_command(self, args):
        """Compares Rust methods with MDX documentation and generates a report."""
        command_title = "Gap Analysis"
        config = [
        ]
        self._print_header(command_title, config)
        versions = ['v1', 'v2']
        # Load Rust methods
        rust_methods = {}
        rust_scan_files = glob.glob(str(self.config.directories.rust_methods_report))
        if rust_scan_files:
            with open(rust_scan_files[0], 'r') as f:
                rust_data = json.load(f)
            for version in versions:
                if version in rust_data['repository_data']:
                    rust_methods[version] = set(rust_data['repository_data'][version]['methods'])
        else:
            self.logger.warning(f"No '{os.path.basename(str(self.config.directories.rust_methods_report))}' file found.")
            self.logger.warning("Please run 'scan-rust' first.")
            return
        
        # Load MDX methods
        mdx_methods = {}
        mdx_scan_files = glob.glob(str(self.config.directories.mdx_methods_report))
        if mdx_scan_files:
            with open(mdx_scan_files[0], 'r') as f:
                mdx_data = json.load(f)
            for version in versions:
                if version in mdx_data['repository_data']:
                    mdx_methods[version] = set(mdx_data['repository_data'][version]['methods'])
        else:
            self.logger.warning(f"No '{os.path.basename(str(self.config.directories.mdx_methods_report))}' file found.")
            self.logger.warning("Please run 'scan-mdx' first.")
            return

        # Perform gap analysis
        gap_report = {}
        for v in versions:
            if v not in rust_methods or v not in mdx_methods:
                continue
            self.log(f"🔍 Processing {v.upper()}...")
            rust_method_set = rust_methods[v]
            doc_method_set = mdx_methods[v]

            missing_in_docs = sorted(list(rust_method_set - doc_method_set))
            extra_in_docs = sorted(list(doc_method_set - rust_method_set))

            gap_report[v] = {
                "missing_in_docs": missing_in_docs,
                "extra_in_docs": extra_in_docs,
                "total_rust_methods": len(rust_method_set),
                "total_doc_methods": len(doc_method_set),
                "undocumented_methods": len(missing_in_docs),
                "extra_methods_in_docs": len(extra_in_docs),
                "coverage": f"{len(doc_method_set) / len(rust_method_set) * 100:.2f}%"
            }

            self.log(f"   - Total methods in Rust: {len(rust_method_set)}")
            self.log(f"   - Total methods in MDX: {len(doc_method_set)}")
            self.log(f"   - Coverage: {gap_report[v]['coverage']}")
            if missing_in_docs:
                self.log(f"   - 🚨 Undocumented methods: {len(missing_in_docs)}")
            if extra_in_docs:
                self.log(f"   - ⚠️  Extra methods in docs: {len(extra_in_docs)}")

        # Save report
        report_path = self.config.directories.kdf_gap_analysis_report
        
        # Add metadata to the report
        final_report = {
            "scan_metadata": self._get_base_scan_metadata(args.kdf_branch),
            "gap_analysis": gap_report
        }
        
        safe_write_json(report_path, final_report, indent=2)
        self.logger.save(f"Gap analysis report saved to: {report_path}")

        success = True
        self._print_footer(command_title, success=success)

    def generate_common_schemas_command(self, args):
        """Generates OpenAPI schemas for common structures and enums."""
        command_title = "Generate Common Schemas"
        self._print_header(command_title)
        success = False
        try:
            manager = OpenAPIManager(config=self.config, verbose=self.verbose)
            manager.generate_common_schemas_only()
            success = True
        except Exception as e:
            self.log(f"An error occurred during common schema generation: {e}", "error")
            self.log(traceback.format_exc(), "error")
        finally:
            self._print_footer(command_title, success=success)

    def clean_json_files(self):
        """Removes all request, response, and error JSON files from Postman directories."""
        self.logger.info("Cleaning existing JSON files...")

        postman_dirs = [
            self.config.directories.postman_json_v1,
            self.config.directories.postman_json_v2
        ]

        patterns = ["request_*.json", "response_*.json", "error_*.json"]
        deleted_count = 0

        for p_dir in postman_dirs:
            if not p_dir or not Path(p_dir).exists():
                self.logger.warning(f"Directory not found, skipping clean: {p_dir}")
                continue

            p_dir_path = Path(p_dir)
            self.logger.info(f"Cleaning files in {p_dir_path}...")
            # Use rglob to recursively find files in subdirectories
            for pattern in patterns:
                for file_path in p_dir_path.rglob(pattern):
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except OSError as e:
                        self.logger.error(f"Error deleting file {file_path}: {e}")

        if deleted_count > 0:
            self.logger.success(f"Successfully deleted {deleted_count} JSON files.")
        else:
            self.logger.info("No JSON files found to clean.")

    def get_kdf_responses_command(self, args):
        try:
            """Gets API responses for a given method and version."""
            command_title = "Get KDF API Responses"
            config_lines = [
                f"Method: {args.method if args.method else None}",
                f"KDF Branch: {args.kdf_branch}",
            ]
            self._print_header(command_title, config_lines=config_lines)

            if args.kdf_branch:
                if not self.git_manager.switch_branch(self._safe_path(self.config.directories.kdf_repo_path), args.kdf_branch):
                    self.logger.error(f"Could not switch to branch {args.kdf_branch}. Aborting.")
                    self._print_footer(command_title, success=False)
                    return

            # Propagate substitute-defaults preference to the API processor
            self.processor.substitute_defaults = getattr(args, 'substitute_defaults', False)

            if args.clean:
                self.clean_json_files()
                self.json_extract_command(args)

            self.start_container_command(args)
            time.sleep(5)
            
            if args.method:
                # Process a single method if specified
                versions_to_process = ['v1', 'v2']
                for version in versions_to_process:
                    self.logger.info(f"Processing single method: {args.method}, version: {version}")
                    self.processor.process_method_request(
                        method=args.method,
                        version=version
                    )
            else:
                # Process all methods with sequencing
                self.logger.info("Processing all methods with sequencing...")
                examples = self.get_json_example_method_paths()
                
                for version, method_paths in examples.items():
                    self.logger.info(f"--- Processing version: {version.upper()} ---")
                    
                    all_methods_in_version = set(method_paths.keys())
                    
                    # Create an ordered execution plan
                    execution_plan = self._create_execution_plan(all_methods_in_version)
                    
                    self.logger.info(f"Execution plan for {version.upper()} created with {len(execution_plan)} methods.")

                    delayed_methods = []
                    for method in execution_plan:
                        validator = MethodValidator(method, version, self.processor, self.logger)
                        
                        if not validator.validate_method_for_testing():
                            self.logger.info(f"Skipping {method}, not valid for test case: [{version} HD: {self.processor.enable_hd}]")
                            continue

                        if not validator.is_method_ready():
                            # Delays methods which need a prior method to be completed
                            self.logger.info(f"Skipping not ready method: {method}")
                            delayed_methods.append(method)
                            continue
                            
                        if method == "stop":
                            self.logger.info(f"Skipping stop method: {method}")
                            continue

                        mdx_path = self.path_mapper.get_method_path("mdx", method, version)
                        json_path = self.path_mapper.get_method_path("json", method, version)
                        if mdx_path is None:
                            self.logger.error(f"Method path not found for method: {method}, version: {version}")
                            continue
                        self.logger.info(f"MDX method path: {mdx_path}")
                        self.logger.info(f"JSON method path: {json_path}")
                        self.logger.info(f"Processing method: {method}, version: {version}")
                        self.logger.info(f"--------------------------------")

                        try:
                            self.processor.process_method_request(
                                method=method,
                                version=version
                            )
                        except Exception as e:
                            self.logger.error(f"An error occurred while processing {method}: {e}")
                            self.logger.error(traceback.format_exc())
                            # Save the error to a file so it can be reported
                            error_content = {
                                "error": f"Failed to process method '{method}': {str(e)}",
                                "error_type": "PROCESSOR_EXECUTION_ERROR",
                                "traceback": traceback.format_exc()
                            }
                            error_filename = f"error_processor_failed.json"
                            folder_name = method.replace("::", "-")
                            output_dir = self._safe_path(self.config.directories.postman_json_v1 if version == 'v1' else self.config.directories.postman_json_v2)
                            example_dir = output_dir / folder_name
                            ensure_directory_exists(example_dir)
                            error_path = example_dir / error_filename
                            safe_write_json(error_path, error_content)
                        time.sleep(1)

        except KeyboardInterrupt:
            self.logger.error("Keyboard interrupt detected. Stopping container...")
        finally:
            self.report_error_responses(args)
            # Generate comparison report across docker nodes
            self.report_node_response_comparison(args)
            # Generate consolidated node balances report
            self.report_node_balances(args)
            # Clean up the temporary file created by import_swaps
            file_to_delete = self.workspace_root / 'utils' / 'docker' / 'kdf-db' / '7a4283ac93466ea1f0e4bb387e28055bbb38192e' / 'SWAPS' / 'MY' / '07ce08bf-3db9-4dd8-a671-854affc1b7a3.json'
            if file_to_delete.is_file():
                try:
                    file_to_delete.unlink()
                    self.logger.info(f"Deleted temporary file: {file_to_delete}")
                except Exception as e:
                    self.logger.error(f"Failed to delete temporary file {file_to_delete}: {e}")

            self._print_footer(command_title, success=False)

    def report_node_response_comparison(self, args):
        """Generates a report comparing responses returned by each docker node for every request example.

        The report structure mirrors other *_report helpers and is saved under
        <reports>/<branch>/kdf_node_response_comparison.json.
        """
        command_title = "Generate Node Response Comparison Report"
        self._print_header(command_title)

        # Prepare containers for aggregated data
        methods_summary: Dict[str, Dict[str, Any]] = {"v1": {}, "v2": {}}
        differing_methods: Dict[str, List[str]] = {"v1": [], "v2": []}

        postman_dirs = {
            "v1": self.config.directories.postman_json_v1,
            "v2": self.config.directories.postman_json_v2,
        }

        # Helper: map hd/wasm flags to a readable node key
        def _node_key(hd_flag: str, wasm_flag: str) -> str:
            return f"{hd_flag}-{wasm_flag}"  # e.g., hd-native, nonhd-wasm

        for version, version_dir in postman_dirs.items():
            if not version_dir:
                continue
            version_dir_path = Path(version_dir)
            self.logger.info(f"Scanning JSON example directory for {version}: {version_dir_path}")
            for method_dir in version_dir_path.iterdir():
                if not method_dir.is_dir():
                    continue

                # Collect response files (both success & error)
                json_files = list(method_dir.glob("*-*-*-*.json"))  # broad match matching at least 3 hyphens
                if not json_files:
                    continue

                # Organise by example number (may be absent)
                examples: Dict[str, Dict[str, Any]] = {}
                for jf in json_files:
                    stem = jf.stem  # e.g., my_method-1-hd-native-response
                    parts = stem.split("-")
                    if len(parts) < 4:
                        continue  # malformed name

                    suffix = parts[-1]  # response/error
                    wasm_flag = parts[-2]
                    hd_flag = parts[-3]

                    # Determine example number (optional)
                    example_part = parts[-4]
                    example_number = None
                    method_name_tokens: List[str]
                    if example_part.isdigit():
                        example_number = example_part
                        method_name_tokens = parts[:-4]
                    else:
                        method_name_tokens = parts[:-3]

                    method_name = "-".join(method_name_tokens)
                    report_key = f"{method_name}_{example_number}" if example_number else method_name

                    # Load JSON content to enable deep comparison later
                    try:
                        with open(jf, "r") as fp:
                            content_json = json.load(fp)
                    except Exception as e:
                        self.logger.error(f"Failed to load JSON from {jf}: {e}")
                        continue

                    node_label = _node_key(hd_flag, wasm_flag)
                    resp_type = "error" if suffix == "error" else "success"

                    if report_key not in examples:
                        examples[report_key] = {}
                    examples[report_key][node_label] = {
                        "type": resp_type,
                        "content": content_json,
                    }

                # Evaluate each example for this method
                for report_key, node_data in examples.items():
                    # Determine if all nodes returned identical responses (content equality)
                    baseline_json_str: Union[str, None] = None
                    all_same = True
                    for nd in node_data.values():
                        json_str = json.dumps(nd["content"], sort_keys=True)
                        if baseline_json_str is None:
                            baseline_json_str = json_str
                        elif json_str != baseline_json_str:
                            all_same = False
                    methods_summary[version][report_key] = {
                        "nodes": {n: d["type"] for n, d in node_data.items()},
                        "all_responses_same": all_same,
                    }
                    if not all_same:
                        differing_methods[version].append(report_key)

        # Sort methods alphabetically for deterministic output
        for ver in ["v1", "v2"]:
            # Sort differing methods lists
            differing_methods[ver] = sorted(set(differing_methods[ver]))
            # Sort keys of methods_summary dictionaries
            methods_summary[ver] = {
                k: methods_summary[ver][k] for k in sorted(methods_summary[ver].keys())
            }

        # Counts
        v1_diff_cnt = len(differing_methods["v1"])
        v2_diff_cnt = len(differing_methods["v2"])
        total_diff_cnt = v1_diff_cnt + v2_diff_cnt

        scan_metadata = self._get_base_scan_metadata(args.kdf_branch)
        scan_metadata.update({
            "scanner_type": "NODE_RESPONSE_COMPARISON",
            "scanner_version": "KDFTools v1.0.0",
            "generated_during": "node_response_comparison_scan",
            "method_source": "Postman JSON examples (dev branch)",
            "is_primary_data_source": False,
            "total_methods_differing": {
                "all": total_diff_cnt,
                "v1": v1_diff_cnt,
                "v2": v2_diff_cnt,
            },
        })

        final_report = {
            "scan_metadata": scan_metadata,
            "methods": methods_summary,
            "differing_methods": differing_methods,
        }

        # Save report
        report_path = self._safe_path(self.config.directories.branched_reports_dir) / "kdf_node_response_comparison.json"
        safe_write_json(report_path, final_report, indent=2)
        self.logger.save(f"Node response comparison report saved to: {report_path}")
        self._print_footer(command_title, success=True, report_paths=[str(report_path)])

    def _create_execution_plan(self, all_methods: set) -> List[str]:
        """Creates an ordered list of methods to execute, prioritizing sequences."""
        
        # Get activation methods from the processor
        activation_methods = self.processor.activation_methods

        # Define method sequences here. This could be moved to a config file later.
        method_sequences = [
            # Pubkey banning sequence
            ["ban_pubkey", "list_banned_pubkeys", "unban_pubkeys"],
            # Swap sequence
            ["buy", "my_swap_status"],
            ["sell", "my_swap_status"],
            # KMD rewards
            ["kmd_rewards_info"],
            # Non-task activation sequences
            ["enable_eth_with_tokens", "enable_erc20"],
            ["enable_tendermint_with_assets", "enable_tendermint_token"],
            # Generic task sequences
            *[
                [f"task::{group}::{suffix}" for suffix in ["init", "status", "cancel"]]
                for group in [
                    "withdraw",
                    "enable_utxo",
                    "enable_eth",
                    "enable_qtum",
                    "enable_sia",
                    "enable_z_coin",
                    "get_new_address",
                ]
            ],
            # Order management sequence
            ["setprice", "my_orders", "update_maker_order", "cancel_order", "cancel_all_orders"],
            # HD wallet sequences
            ["task::get_new_address::init", "task::get_new_address::status"],
            ["task::restore_hd_wallet::init", "task::restore_hd_wallet::status"],
            # Wallet Connect
            ["wc_new_connection", "wc_get_sessions", "wc_get_session", "wc_ping_session", "wc_delete_session"],
        ]
        fully_deprecated_methods = [
            "task::enable_bch::init",
            "task::enable_bch::status",
            "task::enable_bch::cancel",
            "task::enable_bch::user_action",
            "enable_bch_with_tokens",
            "enable_slp"
        ]
        interactive_methods = [
            "task::enable_eth::user_action",
            "task::enable_erc20::user_action",
            "task::enable_tendermint_with_assets::user_action",
            "task::enable_tendermint_token::user_action",
            "task::enable_utxo::user_action",
            "task::enable_qtum::user_action",
            "task::connect_metamask::cancel",
            "task::connect_metamask::init",
            "task::connect_metamask::status",
            "task::init_trezor::cancel",
            "task::init_trezor::init",
            "task::init_trezor::status",
            "task::init_trezor::user_action",
            "trezor_connection_status",
            "wc_new_connection",
            "wc_get_sessions",
            "wc_get_session",
            "wc_ping_session",
            "wc_delete_session",
        ]
        
        oneinch_methods = [
            "1inch_v6_0_classic_swap_contract",
            "1inch_v6_0_classic_swap_create",
            "1inch_v6_0_classic_swap_liquidity_sources",
            "1inch_v6_0_classic_swap_quote",
            "1inch_v6_0_classic_swap_tokens",
        ]

        lightning_methods = [
            "lightning::channels::close_channel",
            "lightning::channels::get_channel_details",
            "lightning::channels::get_claimable_balances",
            "lightning::channels::list_closed_channels_by_filter",
            "lightning::channels::list_open_channels_by_filter",
            "lightning::channels::open_channel",
            "lightning::channels::update_channel",
            "lightning::nodes::add_trusted_node",
            "lightning::nodes::connect_to_node",
            "lightning::nodes::list_trusted_nodes",
            "lightning::nodes::remove_trusted_node",
            "lightning::payments::generate_invoice",
            "lightning::payments::get_payment_details",
            "lightning::payments::list_payments_by_filter",
            "lightning::payments::send_payment",
        ]

        staking_methods = [
            "experimental::staking::claim_rewards",
            "experimental::staking::delegate",
            "experimental::staking::query::delegations",
            "experimental::staking::query::ongoing_undelegations",
            "experimental::staking::query::validators",
            "experimental::staking::undelegate",
        ]

        bot_methods = [
            "start_simple_market_maker_bot",
            "stop_simple_market_maker_bot",
        ]

        stats_methods = [
            "update_version_stat_collection",
            "add_node_to_version_stat",
            "remove_node_from_version_stat",
            "start_version_stat_collection",
            "stop_version_stat_collection",
        ]


        ordered_list = []
        processed = set()

        # Add activation methods first, respecting sequences if they are part of one
        for seq in method_sequences:
            # Check if the sequence contains any activation methods
            if any(method in activation_methods for method in seq):
                for method in seq:
                    if method in all_methods and method not in processed:
                        ordered_list.append(method)
                        processed.add(method)
        
        # Add any other activation methods not in a sequence
        for method in activation_methods:
            if method in all_methods and method not in processed:
                ordered_list.append(method)
                processed.add(method)

        # Add other sequences
        for seq in method_sequences:
            for method in seq:
                if method in all_methods and method not in processed:
                    ordered_list.append(method)
                    processed.add(method)
        
        # After sequences, add standalone activation methods
        for method in activation_methods:
            if (method not in processed 
                and method not in fully_deprecated_methods 
                and method not in interactive_methods
                and method not in oneinch_methods
                and method not in lightning_methods
                and method not in staking_methods
                and method not in bot_methods
                and method not in stats_methods
                ):
                ordered_list.append(method)
                processed.add(method)

        # Add remaining methods alphabetically
        remaining = sorted(list(all_methods - processed - set(fully_deprecated_methods)))
        ordered_list.extend(remaining)
        
        return ordered_list
    
    def build_container_command(self, args):
        """Builds the KDF container image."""
        self.logger.info(f"Building KDF container for branch: {args.kdf_branch}...")
        # Add implementation for building container
        self._print_footer("Build KDF Container", success=True)

    def _get_git_commit_hash(self, repo_path: Path) -> Union[str, None]:
        """Gets the current git commit hash of a repository."""
        if not repo_path.exists() or not (repo_path / ".git").exists():
            self.logger.warning(f"Git repository not found at '{repo_path}'. Cannot get commit hash.")
            return None
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Could not get git commit hash for {repo_path}: {e}")
            return None

    def start_container_command(self, args):
        """Starts the KDF container."""
        command_title = "Start KDF Container"
        config_lines = [
            f"KDF Branch: {args.kdf_branch or self.config.kdf_branch}",
        ]
        self._print_header(command_title, config_lines=config_lines)

        if args.kdf_branch:
            if not self.git_manager.switch_branch(self._safe_path(self.config.directories.kdf_repo_path), args.kdf_branch):
                self.logger.error(f"Could not switch to branch {args.kdf_branch}. Aborting.")
                self._print_footer(command_title, success=False)
                return

        # Stop any running containers first
        self.stop_container_command(args)

        build_commit_hash_file = self._safe_path(self.config.directories.docker_dir) / '.build_commit_hash'
        current_commit_hash = self.git_manager.get_commit_hash(self._safe_path(self.config.directories.kdf_repo_path))
        last_build_hash = None

        if build_commit_hash_file.exists():
            with open(build_commit_hash_file, 'r') as f:
                last_build_hash = f.read().strip()

        build_needed = True
        if current_commit_hash and last_build_hash and current_commit_hash == last_build_hash:
            self.logger.info("KDF commit hash unchanged. Skipping container rebuild.")
            build_needed = False

        try:
            # Generate the MM2.json config before starting
            self.processor.generate_mm2_config()

            docker_command = ["docker", "compose", "up", "-d"]
            if build_needed:
                self.logger.info("Change detected or first build, rebuilding container...")
                docker_command.append("--build")
            else:
                self.logger.info("No build needed, starting container...")

            subprocess.run(
                docker_command,
                cwd=self.config.directories.docker_dir,
                check=True
            )

            if build_needed and current_commit_hash:
                with open(build_commit_hash_file, 'w') as f:
                    f.write(current_commit_hash)
                self.logger.save(f"Saved current build commit hash: {current_commit_hash[:7]}")

            self.logger.success("Container started successfully.")
            self.logger.info("Waiting for container to be ready...")
            time.sleep(10)  # Give some time for the container to initialize
            self._print_footer(command_title, success=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to start container: {e}")
            self._print_footer(command_title, success=False)
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            self._print_footer(command_title, success=False)
            
    def stop_container_command(self, args):
        """Stops the KDF container."""
        self.logger.info("Stopping KDF container...")
        subprocess.run(["docker", "compose", "down"], cwd=self.config.directories.docker_dir)
        self.logger.success("Container stopped.")

    def _switch_kdf_branch(self, branch_name: str):
        """Switches the KDF repository to a different branch."""
        self.logger.info(f"Attempting to switch KDF repository to branch '{branch_name}'...")
        repo_path = self._safe_path(self.config.directories.kdf_repo_path)

        if not repo_path.exists() or not (repo_path / ".git").exists():
            self.logger.error(f"KDF repository not found at '{repo_path}'.")
            return False

        try:
            # Stash any local changes
            subprocess.run(["git", "stash"], cwd=repo_path, check=True, capture_output=True)

            # Fetch latest changes from origin
            subprocess.run(["git", "fetch", "origin"], cwd=repo_path, check=True, capture_output=True)

            # Check if branch exists locally or remotely
            local_branch_exists = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
                cwd=repo_path, capture_output=True
            ).returncode == 0
            
            remote_branch_exists = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/remotes/origin/{branch_name}"],
                cwd=repo_path, capture_output=True
            ).returncode == 0

            if not local_branch_exists and not remote_branch_exists:
                self.logger.error(f"Branch '{branch_name}' not found locally or on origin.")
                return False

            # Checkout branch (track remote if it doesn't exist locally)
            if not local_branch_exists and remote_branch_exists:
                subprocess.run(["git", "checkout", "--track", f"origin/{branch_name}"], cwd=repo_path, check=True, capture_output=True)
            else:
                subprocess.run(["git", "checkout", branch_name], cwd=repo_path, check=True, capture_output=True)

            # Pull latest changes from the branch
            subprocess.run(["git", "pull", "origin", branch_name], cwd=repo_path, check=True, capture_output=True)

            self.logger.success(f"Successfully switched KDF repository to branch '{branch_name}'.")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git command failed: {e.stderr.decode().strip() if e.stderr else e}")
            return False
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while switching branches: {e}")
            return False

    def get_json_example_method_paths(self):
        """Gets JSON example method paths."""
        file_path = self._safe_path(self.config.directories.mdx_json_example_method_paths_report)
        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            self.logger.error("Run 'json-extract' first to generate the file.")
            return {}

        with open(file_path, 'r') as f:
            data = json.load(f)
        return data.get("method_paths", {})

    def generate_v2_no_param_methods_report(self, args):
        """Generates a report of V2 methods that do not have any parameters."""
        command_title = "Generate V2 No-Parameter Methods Report"
        self._print_header(command_title)

        v2_methods_without_params = []
        
        unified_mapping = MethodMappingManager(config=self.config).create_unified_mapping()
        
        v2_methods = unified_mapping.get('v2', {})
        
        for method_name, method_data in v2_methods.items():
            if not method_data.has_mdx or not method_data.mdx_path:
                continue

            mdx_path = Path(method_data.mdx_path)
            if not mdx_path.exists():
                continue

            with open(mdx_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # A simple heuristic: check for the absence of a request parameters table
            if "Request Parameters" not in content and "### Request" not in content:
                 v2_methods_without_params.append(method_name)

        # Generate report
        report_path = self._safe_path(self.config.directories.branched_reports_dir) / "v2_no_param_methods.json"
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "total_v2_methods_scanned": len(v2_methods),
            "v2_methods_without_params_count": len(v2_methods_without_params),
            "v2_methods_without_params": sorted(v2_methods_without_params)
        }
        
        safe_write_json(report_path, report_data, indent=2)
        
        self.logger.save(f"Report saved to: {report_path}")
        self.logger.info(f"Found {len(v2_methods_without_params)} V2 methods without parameters.")

        self._print_footer(command_title, success=True, report_paths=[report_path])

    def extract_errors_command(self, args):
        """Extracts error enums from the KDF Rust codebase."""
        command_title = "Extract Error Enums"
        self._print_header(command_title)
        success = False

        try:
            if args.source == 'rust':
                self.logger.info("Scanning Rust source for error enums...")
                scanner = ErrorScanner(
                    repo_path=self.config.directories.kdf_repo_path,
                    logger=self.logger
                )
                errors = scanner.scan_for_errors()
                
                # Generate Markdown documentation from the extracted errors
                # Use a default path since docs_dir doesn't exist in DirectoryConfig
                md_output_path = Path("docs/komodo-defi-framework/api/errors.mdx")
                # Comment out the call since generate_error_docs doesn't exist
                # scanner.generate_error_docs(errors, md_output_path)
                
                # Save raw JSON data
                json_output_path = self._safe_path(self.config.directories.data_dir) / "kdf_error_enums.json"
                safe_write_json(json_output_path, errors)
                
                self.logger.save(f"Saved raw error data to: {json_output_path}")
                self.logger.save(f"Generated error documentation at: {md_output_path}")

            elif args.source == 'mdx':
                self.logger.info("Scanning MDX files for error responses...")
                scanner = MdxErrorScanner(
                    docs_path=self.config.directories.mdx_v2,
                    logger=self.logger
                )
                errors = scanner.scan_for_errors()
                
                # Save raw JSON data
                json_output_path = self._safe_path(self.config.directories.data_dir) / "mdx_error_responses.json"
                safe_write_json(json_output_path, errors)
                self.logger.save(f"Saved MDX error responses to: {json_output_path}")

                # Check for conflicts - comment out since find_conflicts doesn't exist
                conflict_report_path = self._safe_path(self.config.directories.reports_dir) / "dev" / "error_description_conflicts.json"
                # conflicts = scanner.find_conflicts(errors)
                # if conflicts:
                #     self.logger.warning(f"Found {len(conflicts)} error types with conflicting descriptions.")
                #     safe_write_json(conflict_report_path, conflicts)
                #     self.logger.save(f"Conflict report saved to: {conflict_report_path}")

            else:
                self.logger.error(f"Invalid source: {args.source}. Must be 'rust' or 'mdx'.")
                self._print_footer(command_title, success=False)
                return

            success = True

        except Exception as e:
            self.log(f"An error occurred during error extraction: {e}", "error")
            self.log(traceback.format_exc(), "error")
        finally:
            self._print_footer(command_title, success=success)

    def balances_command(self, args):
        """Gets address and balance info for test coins on all nodes."""
        command_title = "Get Coin Balances"
        self._print_header(command_title)

        try:
            self.start_container_command(args)
            time.sleep(5)

            # Use centralized path from DirectoryConfig for test parameters
            params_path = self.config.directories.test_params_json
            with open(params_path, 'r') as f:
                test_params = json.load(f)

            coins_to_check = list(set([test_params['PRIMARY_COIN'], test_params['SECONDARY_COIN']] + test_params['NODE_BALANCE_COINS']))
            hd_coins = set(test_params['HD_SIGNING_COINS'])

            self.logger.info("Activating coins on all nodes...")
            for node in self.config.nodes:
                self.logger.info(f"Checking node: {node.name}")
                for coin in coins_to_check:
                    self.processor.activate_coin(coin, node=node)
                    time.sleep(1)

            self.logger.info("Fetching balances...")
            for coin in coins_to_check:
                self.logger.info(f"--- Balances for {coin} ---")
                
                request_body = {
                    "method": "my_balance",
                    "coin": coin
                }

                output_dir = self._safe_path(self.config.directories.reports_dir) / "balances_check"
                output_dir.mkdir(exist_ok=True)
                
                node_responses = self.processor.send_request_to_all_nodes(
                    request_body=request_body,
                    method_name="my_balance",
                    output_dir=output_dir,
                    example_number=1
                )

                for node_name, resp in sorted(node_responses.items()):
                    if "result" in resp:
                        balance = resp["result"]["balance"]
                        address = resp["result"]["address"]
                        self.logger.info(f"  {node_name}:")
                        self.logger.info(f"    Address: {address}")
                        self.logger.info(f"    Balance: {balance}")

                        # Find the node's config to check if it's an HD node
                        node_cfg = next((n for n in self.config.nodes if n.name == node_name), None)
                        is_hd_node = node_cfg.hd_mode if node_cfg else False
                        
                        if is_hd_node and coin in hd_coins:
                            self._get_and_display_hd_addresses(coin, node_name)
                    else:
                        error = resp.get("error", "Unknown error")
                        self.logger.error(f"  {node_name}: Failed to get balance. Error: {error}")

            self._print_footer(command_title, success=True)
        except Exception as e:
            self.logger.error(f"An error occurred during balance check: {e}")
            self.logger.error(traceback.format_exc())
            self._print_footer(command_title, success=False)

    def _get_and_display_hd_addresses(self, coin, node_name):
        self.logger.info("    (HD Node) Getting more addresses...")
        
        # Find the port from the centralized config
        node_config = next((n for n in self.config.nodes if n.name == node_name), None)
        if not node_config:
            self.logger.error(f"Port for node {node_name} not found in config.")
            return
        
        port = node_config.port
        url = f"http://127.0.0.1:{port}"

        init_req = {
            "userpass": "RPC_UserP@SSW0RD",  # Use hardcoded value since rpc_password doesn't exist
            "method": "task::get_new_address::init",
            "mmrpc": "2.0",
            "params": {
                "coin": coin,
                "max": 2  # We need 2 more, the first one came from my_balance
            }
        }
        try:
            init_resp = requests.post(url, json=init_req, timeout=10).json()

            if "result" in init_resp and "task_id" in init_resp["result"]:
                task_id = init_resp["result"]["task_id"]
                
                status_method = "task::get_new_address::status"
                for _ in range(20):
                    status_req = {
                        "userpass": "RPC_UserP@SSW0RD",  # Use hardcoded value since rpc_password doesn't exist
                        "method": status_method,
                        "mmrpc": "2.0",
                        "params": {"task_id": task_id}
                    }
                    status_resp = requests.post(url, json=status_req, timeout=10).json()

                    if status_resp and "result" in status_resp:
                        status = status_resp["result"].get("status")
                        details = status_resp["result"].get("details")

                        if status == "Ok":
                            new_addresses = details.get("new_addresses", [])
                            for i, addr_info in enumerate(new_addresses):
                                self.logger.info(f"    Address {i+2}: {addr_info['address']}")
                            break
                        elif status == "InProgress":
                            time.sleep(5)
                            continue
                        else:
                            self.logger.error(f"      Address generation failed. Status: {status}")
                            break
                    else:
                        self.logger.error("      Failed to get status for address generation task.")
                        break
                else:
                    self.logger.error("      Polling for new addresses timed out.")
            else:
                self.logger.error(f"      Failed to init get_new_address task: {init_resp.get('error', init_resp)}")

        except requests.RequestException as e:
            self.logger.error(f"      Request to get new addresses failed: {e}")

    def _get_git_branch_name(self, repo_path: Path) -> Union[str, None]:
        """Gets the current git branch name of a repository."""
        if not repo_path.exists() or not (repo_path / ".git").exists():
            self.logger.warning(f"Git repository not found at '{repo_path}'. Cannot get branch name.")
            return None
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Could not get git branch for {repo_path}: {e}")
            return None

    def report_node_balances(self, args):
        """Generates a consolidated report of coin addresses and balances per test node.

        The report is saved to ``reports/kdf_node_balances.json`` and is intended to
        be consumed by funding scripts so that test wallets can be pre-funded.
        Structure::

            {
              "scan_metadata": {...},
              "balances": {
                  "node_a": {
                      "KMD": {
                          "RDux85r5X…": "0"
                      },
                      "LTC": {
                          "Labc123…": "12.34"
                      }
                  },
                  "node_b": {...}
              }
            }
        """

        command_title = "Generate Node Balances Report"
        self._print_header(command_title)

        try:
            # ------------------------------------------------------------------
            # Determine which coins we need to query. We reuse the same logic as
            # the dedicated `balances` command so that the behaviour is
            # consistent.
            # ------------------------------------------------------------------
            params_path = self.config.directories.test_params_json
            with open(params_path, "r", encoding="utf-8") as fp:
                test_params = json.load(fp)

            coins_to_check: list[str] = list(
                set(
                    [
                        test_params.get("PRIMARY_COIN"),
                        test_params.get("SECONDARY_COIN"),
                        *test_params.get("NODE_BALANCE_COINS", []),
                    ]
                )
            )
            coins_to_check = [c for c in coins_to_check if c]  # filter None

            # Container for aggregated balances
            balances: Dict[str, Dict[str, Dict[str, str]]] = {}

            # We will store the raw responses under a temp directory to avoid
            # clashing with the main get-kdf-responses outputs.
            output_dir = self._safe_path(self.config.directories.reports_dir) / "balances_scan"
            output_dir.mkdir(parents=True, exist_ok=True)

            for idx, coin in enumerate(coins_to_check, start=1):
                request_body = {
                    "method": "my_balance",
                    "coin": coin,
                }

                node_responses = self.processor.send_request_to_all_nodes(
                    request_body=request_body,
                    method_name="my_balance",
                    output_dir=output_dir,
                    example_number=idx,
                )

                for node_name, resp in node_responses.items():
                    # Normalise response structure – handle v1 plain vs v2 wrapped
                    data = resp.get("result", resp)
                    if not isinstance(data, dict):
                        continue

                    address = data.get("address")
                    balance = data.get("balance")
                    coin_ticker = data.get("coin", coin)

                    if address is None or balance is None:
                        # Record error or incomplete data instead of skipping
                        error_msg = resp.get("error") or "incomplete_response"
                        node_entry = balances.setdefault(node_name, {})
                        coin_entry = node_entry.setdefault(coin_ticker, {})
                        coin_entry["error"] = error_msg
                        continue

                    node_entry = balances.setdefault(node_name, {})
                    coin_entry = node_entry.setdefault(coin_ticker, {})
                    coin_entry[address] = balance

            # ------------------------------------------------------------------
            # Build scan metadata and persist report
            # ------------------------------------------------------------------
            scan_metadata = self._get_base_scan_metadata(args.kdf_branch)
            scan_metadata.update(
                {
                    "scanner_type": "NODE_BALANCES_SCAN",
                    "scanner_version": "KDFTools v1.0.0",
                    "generated_during": "get_kdf_responses_scan",
                    "method_source": "my_balance API calls",
                    "is_primary_data_source": True,
                    "coins_checked": sorted(coins_to_check),
                    "total_nodes": len(self.config.nodes),
                }
            )

            final_report = {
                "scan_metadata": scan_metadata,
                "balances": balances,
            }

            report_path = self._safe_path(self.config.directories.reports_dir) / "kdf_node_balances.json"
            safe_write_json(report_path, final_report, indent=2)
            self.logger.save(f"Node balances report saved to: {report_path}")

            self._print_footer(command_title, success=True, report_paths=[str(report_path)])
        except Exception as exc:
            self.logger.error(f"Failed to generate node balances report: {exc}")
            self.logger.error(traceback.format_exc())
            self._print_footer(command_title, success=False)


class MethodValidator:
    def __init__(self, method: str, version: str, processor: Optional[ApiRequestProcessor] = None, logger=None):
        self.method = method
        self.version = version
        self.processor = processor
        self.logger = logger
        
    def _safe_path(self, path_value: Union[str, Path, None]) -> Path:
        """Safely convert to Path object, handling None values."""
        if path_value is None:
            return Path("")
        return Path(path_value)

    def validate_method_for_testing(self) -> bool:
        if self.processor is None:
            return False
        if self.is_hd_only_method() and not self.processor.enable_hd:
            return False
        if self.is_legacy_only_method() and self.processor.enable_hd:
            return False
        if self.is_method_interactive():
            return False
        if self.is_method_too_complex_for_now():
            return False
        if self.is_method_deprecated():
            return False
        return True

    def is_hd_only_method(self) -> bool:
        """Checks if a method is only available for HD wallets."""
        # Add methods that are only available for HD wallets here.
        # This is used to skip tests for non-HD wallets.
        hd_only_methods = [
            "task::get_new_address::init",
            "task::get_new_address::status",
            "task::get_new_address::cancel",
            "task::restore_hd_wallet::init",
            "task::restore_hd_wallet::status",
            "task::restore_hd_wallet::user_action",
            "task::restore_hd_wallet::cancel",
            "get_public_key_at_hd_account"
        ]
        return self.method in hd_only_methods

    def is_legacy_only_method(self) -> bool:
        """Checks if a method is only available for legacy wallets."""
        # Add methods that are only available for legacy wallets here.
        # This is used to skip tests for HD wallets.
        legacy_only_methods = [
            "show_priv_key"
        ]
        return self.method in legacy_only_methods

    def is_method_interactive(self) -> bool:
        """Checks if a method is interactive."""
        # Add methods that are interactive here.
        # This is used to skip tests for interactive methods.
        interactive_methods = [
            "task::enable_bch::user_action",
            "task::enable_eth::user_action",
            "task::enable_qtum::user_action",
            "task::enable_utxo::user_action",
            "task::restore_hd_wallet::user_action",
        ]
        return self.method in interactive_methods

    def is_method_too_complex_for_now(self) -> bool:
        """
        Methods that are too complex to test for now.
        This is a temporary solution to skip tests for methods that require more complex setup.
        """
        complex_methods = [
            "task::withdraw::cancel",
            "task::withdraw::init",
            "task.withdraw.status"
            "get_trade_preimage",
            "trade_preimage",
        ]
        return self.method in complex_methods

    def is_method_deprecated(self) -> bool:
        """
        Methods that are deprecated.
        This is a temporary solution to skip tests for methods that require more complex setup.
        """
        deprecated_methods = [
            "kmd_rewards_info",
        ]
        if self.method in deprecated_methods:
            if self.processor is None:
                return False
            kdf_branch = self.processor.git_manager.get_branch_name(
                self._safe_path(self.processor.config.directories.kdf_repo_path)
            )
            # This method is only deprecated on dev.
            if kdf_branch and "dev" in kdf_branch:
                return True
        return False

    def is_method_ready(self) -> bool:
        """
        Checks if a method is ready to be tested.
        This is used to skip tests for methods that require other methods to be completed first.
        """
        # Add methods that require other methods to be completed first here.
        # This is used to skip tests for methods that require other methods to be completed first.
        # For example, my_swap_status requires a swap to be started first.
        methods_that_need_prior_completion = {
            "my_swap_status": ["buy", "sell"],
            "list_banned_pubkeys": ["ban_pubkey"],
            "unban_pubkeys": ["ban_pubkey", "list_banned_pubkeys"],
            "enable_erc20": ["enable_eth_with_tokens"],
            "enable_tendermint_token": ["enable_tendermint_with_assets"],
            "verify_message": ["sign_message"],
            "send_raw_transaction": ["get_unsigned_transaction"],
        }

        # Handle task-based methods
        if self.processor is None:
            return True
            
        if "::" in self.method and not self.method.endswith("::init"):
            task_group = "::".join(self.method.split("::")[:-1])
            init_method = f"{task_group}::init"
            if hasattr(self.processor, 'completed_methods') and init_method not in self.processor.completed_methods:
                if self.logger:
                    self.logger.info(f"Skipping {self.method} because {init_method} has not been completed.")
                return False

        if self.method in methods_that_need_prior_completion:
            required_methods = methods_that_need_prior_completion[self.method]
            if hasattr(self.processor, 'completed_methods') and not any(req in self.processor.completed_methods for req in required_methods):
                if self.logger:
                    self.logger.info(f"Skipping {self.method} because none of {required_methods} have been completed.")
                return False
        
        return True

    def _get_current_git_branch(self, repo_path):
        """Gets the current git branch of a repository."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if self.logger:
                self.logger.error(f"Could not get current git branch for {repo_path}: {e}")
            return None


def main():
    """Main entry point for the script."""
    try:
        cli = KDFTools()
        cli.main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()