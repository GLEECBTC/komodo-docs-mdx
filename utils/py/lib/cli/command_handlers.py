#!/usr/bin/env python3
"""
Command Handlers for KDF Tools CLI

This module contains the command execution logic separated from the main CLI class
to improve maintainability and reduce the monolithic structure.
"""

import asyncio
import json
import time
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import glob

from lib.constants import get_config
from lib.utils import safe_write_json, ensure_directory_exists
from lib.constants.data_structures import ScanMetadata
from lib.utils.data_utils import sort_version_method_counts
from lib.rust.scanner import KDFScanner
from lib.rust.error_scanner import ErrorScanner
from lib.mdx.error_scanner import MdxErrorScanner
from lib.openapi.openapi_manager import OpenAPIManager
from lib.postman.postman_manager import PostmanManager
from lib.managers import MethodMappingManager
from lib.api_client.kdf_api_processor import ApiRequestProcessor
from lib.async_support import run_async


class CommandHandlers:
    """Handles command execution logic for KDF Tools CLI."""
    
    def __init__(self, config, logger, processor, git_manager, workspace_root):
        self.config = config
        self.logger = logger
        self.processor = processor
        self.git_manager = git_manager
        self.workspace_root = workspace_root
        self.verbose = True
        
    def _safe_path(self, path_value: Union[str, Path, None]) -> Path:
        """Safely convert to Path object, handling None values."""
        if path_value is None:
            return Path("")
        return Path(path_value)
        
    def _get_base_scan_metadata(self, kdf_branch: str) -> Dict[str, Any]:
        """Returns a base dictionary for scan_metadata."""
        kdf_commit = self.git_manager.get_commit_hash(self._safe_path(self.config.directories.kdf_repo_path))
        mdx_branch = self.git_manager.get_branch_name(self.workspace_root)
        mdx_commit = self.git_manager.get_commit_hash(self.workspace_root)
        
        return {
            "kdf_branch": kdf_branch,
            "mdx_branch": mdx_branch,
            "kdf_commit": kdf_commit,
            "mdx_commit": mdx_commit,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        
    def handle_openapi_command(self, args) -> bool:
        """Handle openapi subcommand - MDX to OpenAPI conversion."""
        command_title = "MDX to OpenAPI Conversion"
        self.logger.info(f"============== Starting: {command_title} ==============")
        
        success = False
        report_paths = []
        try:
            from lib.openapi.openapi_spec_generator import OpenApiSpecGenerator
            from lib.managers.path_mapping_manager import EnhancedPathMapper
            
            openapi_spec_generator = OpenApiSpecGenerator()
            path_mapper = EnhancedPathMapper(config=self.config)
            
            manager = OpenAPIManager(
                config=self.config,
                verbose=self.verbose,
                logger=self.logger,
                path_mapper=path_mapper
            )
            manager.openapi_command()
            
            v1_count = len([m for m in manager.all_methods.values() if m['version'] == 'v1'])
            v2_count = len([m for m in manager.all_methods.values() if m['version'] == 'v2'])
            total_count = v1_count + v2_count

            result = f"✅ All versions processed successfully!\n   📊 V1 methods: {v1_count}\n   📊 V2 methods: {v2_count}\n   📊 Total methods: {total_count}"
            
            self.logger.info(f"{result}")
            
            # Generate tracking files
            self.logger.info("📊 Generating OpenAPI tracking files...")
            enums_count = len(manager.mdx_parser.enum_patterns)
            structures_count = len(manager.mdx_parser.common_structures)
            
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
            self.logger.info("📊 Generating review files...")
            manager.common_schema_generator.generate_review_files(manager.mdx_parser.enum_patterns)
            
            # Show statistics about generated schemas
            stats = manager.get_stats()
            self.logger.info(f"📊 Generation Statistics:")
            self.logger.info(f"   • Total methods processed: {stats['files_processed']}")
            self.logger.info(f"   • Enums found: {stats['enums_found']}")
            self.logger.info(f"   • Structures found: {stats['structures_found']}")
            
            self.logger.info("🔚 Finished MDX to OpenAPI conversion.")

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
            self.logger.error(f"An error occurred during OpenAPI generation: {e}")
            self.logger.error(traceback.format_exc())
            success = False
        finally:
            self.logger.info(f"============== {'✅ Success' if success else '❌ Failed'}: {command_title} ==============")
            return success
            
    def handle_scan_rust_command(self, args) -> bool:
        """Handle scan-rust subcommand - KDF repository scanning with async processing."""
        command_title = "KDF Repository Scan"
        versions = ['v1', 'v2']
            
        config = [
            f"Branch: {args.kdf_branch}",
            f"Versions: {versions}",
        ]
        self.logger.info(f"============== Starting: {command_title} ==============")
        for line in config:
            self.logger.info(f"    - {line}")

        if args.kdf_branch:
            if not self.git_manager.switch_branch(Path(self.config.directories.kdf_repo_path), args.kdf_branch):
                self.logger.error(f"Could not switch to branch {args.kdf_branch}. Aborting rust-scan.")
                self.logger.info(f"============== ❌ Failed: {command_title} ==============")
                return False

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
            self.logger.info(f"Async KDF Repository scan completed:")
            self.logger.info(f"📊 Rust Repository Scan Statistics:")
            self.logger.info(f"   • V1 methods processed: {version_method_counts['v1']}")
            self.logger.info(f"   • V2 methods processed: {version_method_counts['v2']}")
            self.logger.info(f"   • Total methods processed: {version_method_counts['all']}")
            self.logger.info("🔚 Finished Rust repository scan.")
            success = True

        try:
            asyncio.run(main())
        except Exception as e:
            self.logger.error(f"❌ An error occurred during Rust repository scan: {e}")
            if self.verbose:
                traceback.print_exc()
            return False
            
        self.logger.info(f"============== {'✅ Success' if success else '❌ Failed'}: {command_title} ==============")
        return success
        
    def _calc_version_method_counts(self, repo_info: Dict[str, Any]) -> Dict[str, int]:
        version_method_counts = {version: len(info.methods) for version, info in repo_info.items()}
        return sort_version_method_counts(version_method_counts)
        
    def _generate_openapi_tracking_files(self, openapi_manager: OpenAPIManager, versions: List[str], version_method_counts: Dict[str, int]) -> str:
        """Generates all necessary tracking files for OpenAPI."""
        from lib.openapi.openapi_spec_generator import OpenApiSpecGenerator
        openapi_spec_generator = OpenApiSpecGenerator()
        
        return openapi_spec_generator._generate_openapi_method_paths_file(
            all_methods=openapi_manager.all_methods,
            path_mapper=openapi_manager.path_mapper,
            versions=versions,
            version_method_counts=version_method_counts
        ) 