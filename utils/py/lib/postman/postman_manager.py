#!/usr/bin/env python3
"""
Postman Manager

Complete Postman operations manager following standard architecture.
Orchestrates collection generation, file management, and reporting.
Replaces the pipeline architecture from postman_consolidated.py.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Any, Tuple

from ..utils.file_types import UnifiedOperationResult
from ..utils.file_utils import safe_read_json, safe_write_json, ensure_directory_exists
from ..utils.logging_utils import get_logger
from ..constants.config import get_config
from .postman_scanner import PostmanJSONProcessor
from .postman_utils import (
    organize_requests_into_folders,
    generate_postman_collection as util_generate_postman_collection,
    generate_environment_file as util_generate_environment_file
)
from .postman_reporter import PostmanReportGenerator


class PostmanFileManager:
    """
    Manages file operations for Postman collections and environments.
    
    Provides validation, loading, saving, and management functionality with
    structured error handling using UnifiedOperationResult.
    """
    
    def __init__(self, collections_dir: str = "../../postman/collections",
                 environments_dir: str = "../../postman/environments", 
                 verbose: bool = True):
        self.collections_dir = Path(collections_dir)
        self.environments_dir = Path(environments_dir)
        self.verbose = verbose
        self.logger = get_logger("postman-file-manager")
        
        # Ensure directories exist
        ensure_directory_exists(self.collections_dir)
        ensure_directory_exists(self.environments_dir)
    
    def save_collection(self, collection: Dict[str, Any], version: str) -> UnifiedOperationResult:
        """Save Postman collection."""
        filename = f"KDF_API_{version.upper()}_Collection.postman_collection.json"
        filepath = self.collections_dir / filename
        
        # Validate collection structure
        is_valid, errors = self.validate_collection_structure(collection)
        if not is_valid:
            return UnifiedOperationResult(
                success=False,
                file_path=str(filepath),
                operation="save_collection",
                message="Collection validation failed",
                errors=errors
            )
        
        try:
            safe_write_json(filepath, collection)
            
            if self.verbose:
                self.logger.info(f"Saved collection: {filename}")
            
            return UnifiedOperationResult(
                success=True,
                file_path=str(filepath),
                operation="save_collection",
                message="Collection saved successfully",
                data=collection
            )
        except Exception as e:
            return UnifiedOperationResult(
                success=False,
                file_path=str(filepath),
                operation="save_collection",
                message=f"Save failed: {e}",
                errors=[str(e)]
            )
    
    def save_environment(self, environment: Dict[str, Any], version: str) -> UnifiedOperationResult:
        """Save Postman environment."""
        filename = f"KDF_API_{version.upper()}_Environment.postman_environment.json"
        filepath = self.environments_dir / filename
        
        # Validate environment structure
        is_valid, errors = self.validate_environment_structure(environment)
        if not is_valid:
            return UnifiedOperationResult(
                success=False,
                file_path=str(filepath),
                operation="save_environment",
                message="Environment validation failed",
                errors=errors
            )
        
        try:
            safe_write_json(filepath, environment)
            
            if self.verbose:
                self.logger.info(f"Saved environment: {filename}")
            
            return UnifiedOperationResult(
                success=True,
                file_path=str(filepath),
                operation="save_environment",
                message="Environment saved successfully",
                data=environment
            )
        except Exception as e:
            return UnifiedOperationResult(
                success=False,
                file_path=str(filepath),
                operation="save_environment",
                message=f"Save failed: {e}",
                errors=[str(e)]
            )
    
    def load_collection(self, version: str) -> Dict[str, Any]:
        """Load Postman collection."""
        filename = f"KDF_API_{version.upper()}_Collection.postman_collection.json"
        filepath = self.collections_dir / filename
        return safe_read_json(filepath)
    
    def load_environment(self, version: str) -> Dict[str, Any]:
        """Load Postman environment."""
        filename = f"KDF_API_{version.upper()}_Environment.postman_environment.json"
        filepath = self.environments_dir / filename
        return safe_read_json(filepath)
    
    def list_collections(self) -> Dict[str, str]:
        """List available collections."""
        collections = {}
        for file_path in self.collections_dir.glob("*.postman_collection.json"):
            # Extract version from filename
            name_parts = file_path.stem.split('_')
            if len(name_parts) >= 3:
                version = name_parts[2].lower()
                collections[version] = str(file_path)
        return collections
    
    def list_environments(self) -> Dict[str, str]:
        """List available environments."""
        environments = {}
        for file_path in self.environments_dir.glob("*.postman_environment.json"):
            # Extract version from filename
            name_parts = file_path.stem.split('_')
            if len(name_parts) >= 3:
                version = name_parts[2].lower()
                environments[version] = str(file_path)
        return environments
    
    def validate_collection_structure(self, collection: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate Postman collection structure."""
        errors = []
        
        # Check required fields
        required_fields = ['info', 'item']
        for field in required_fields:
            if field not in collection:
                errors.append(f"Missing required field: {field}")
        
        # Validate info section
        if 'info' in collection:
            info = collection['info']
            info_required = ['name', 'schema']
            for field in info_required:
                if field not in info:
                    errors.append(f"Missing required info field: {field}")
        
        # Validate items
        if 'item' in collection:
            if not isinstance(collection['item'], list):
                errors.append("Collection items must be a list")
        
        return len(errors) == 0, errors
    
    def validate_environment_structure(self, environment: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate Postman environment structure."""
        errors = []
        
        # Check required fields
        required_fields = ['id', 'name', 'values']
        for field in required_fields:
            if field not in environment:
                errors.append(f"Missing required field: {field}")
        
        # Validate values
        if 'values' in environment:
            values = environment['values']
            if not isinstance(values, list):
                errors.append("Environment values must be a list")
            else:
                for i, value in enumerate(values):
                    if not isinstance(value, dict):
                        errors.append(f"Environment value {i} must be a dictionary")
                    elif 'key' not in value:
                        errors.append(f"Environment value {i} is missing 'key'")
        
        return len(errors) == 0, errors
    
    def get_file_stats(self) -> Dict[str, Any]:
        """
        Get statistics for generated Postman files.
        """
        collections_path = self.collections_dir
        environments_path = self.environments_dir
        
        collection_files = list(collections_path.glob("*.postman_collection.json"))
        environment_files = list(environments_path.glob("*.postman_environment.json"))
        
        collection_stats = {
            'count': len(collection_files),
            'total_size': sum(p.stat().st_size for p in collection_files),
            'files': {p.name: p.stat().st_size for p in collection_files}
        }
        
        environment_stats = {
            'count': len(environment_files),
            'total_size': sum(p.stat().st_size for p in environment_files),
            'files': {p.name: p.stat().st_size for p in environment_files}
        }
        
        return {
            'collections': collection_stats,
            'environments': environment_stats,
            'total_files': len(collection_files) + len(environment_files)
        }


class PostmanManager:
    """
    Orchestrates Postman collection generation using standard components.
    
    - Scans for JSON examples using PostmanJSONProcessor.
    - Generates collections and environments using utility functions.
    - Manages files using PostmanFileManager.
    - Generates reports using PostmanReportGenerator.
    """
    
    def __init__(self, config=None, verbose: bool = True):
        self.config = config or get_config()
        self.verbose = verbose
        self.logger = get_logger("postman-manager")
        collections_dir = self.config._resolve_path(self.config.directories.postman_collections)
        environments_dir = self.config._resolve_path(self.config.directories.postman_environments)
        
        self.file_manager = PostmanFileManager(
            collections_dir=collections_dir,
            environments_dir=environments_dir,
            verbose=self.verbose
        )
        
        # Initialize the scanner with all supported JSON directories
        json_dirs = {
            'v1': self.config._resolve_path(self.config.directories.postman_json_v1),
            'v2': self.config._resolve_path(self.config.directories.postman_json_v2)
        }
        self.scanner = PostmanJSONProcessor(
            config=self.config,
            json_dirs=json_dirs,
            verbose=self.verbose
        )
        self._reporter = None # Lazy load to prevent circular imports
    
    @property
    def reporter(self):
        """Lazy-loaded PostmanReportGenerator."""
        if self._reporter is None:
            self._reporter = PostmanReportGenerator(verbose=self.verbose)
        return self._reporter
    
    def generate_collections(self, versions: List[str] = ['v1', 'v2']) -> Dict[str, Tuple[str, str]]:
        """
        Generate Postman collections and environments for specified API versions.
        
        Orchestrates scanning, generation, and file saving.
        
        Returns:
            Dictionary mapping versions to (collection_path, env_path) tuples.
        """
        results = {}
        
        if self.verbose:
            self.logger.info("Starting Postman collection generation...")
        
        for version in versions:
            if self.verbose:
                self.logger.info(f"Processing version: {version.upper()}")
            
            # Scan for requests for the current version
            categorized_requests = self.scanner.scan_json_examples(version)
            if not categorized_requests:
                if self.verbose:
                    self.logger.warning(f"No requests found for {version}")
                continue
            
            # Organize requests into folder structure
            organized_items = organize_requests_into_folders(categorized_requests)
            total_requests = sum(len(reqs) for reqs in categorized_requests.values())
            
            # Generate collection and environment
            collection = self.generate_postman_collection(version, organized_items, total_requests)
            environment = self.generate_environment_file(version)
            
            # Save files
            collection_result = self.file_manager.save_collection(collection, version)
            env_result = self.file_manager.save_environment(environment, version)
            
            if collection_result.success and env_result.success:
                results[version] = (collection_result.file_path, env_result.file_path)
            else:
                if self.verbose:
                    self.logger.error(f"Failed to generate for {version}")
                    if not collection_result.success:
                        self.logger.error(f"Collection errors: {collection_result.errors}")
                    if not env_result.success:
                        self.logger.error(f"Environment errors: {env_result.errors}")
        
        if self.verbose:
            self.logger.info("Postman generation complete.")
        
        return results
    
    def generate_postman_collection(self, version: str, organized_items: List[Dict], total_requests: int) -> Dict:
        """
        Generate a Postman collection dictionary for a given version.
        
        Uses the utility function and provides the necessary context.
        """
        userpass = self.config.openapi.userpass
        
        return util_generate_postman_collection(
            version=version,
            folders=organized_items,
            total_requests=total_requests
        )
    
    def generate_environment_file(self, version: str) -> Dict:
        """Generate a Postman environment dictionary."""
        return util_generate_environment_file(version)
    
    async def generate_collections_async(self, versions: List[str] = ['v1', 'v2']) -> Dict[str, Tuple[str, str]]:
        """
        Asynchronously generate Postman collections and environments.
        """
        async def generate_single_version(version: str) -> Tuple[str, Tuple[str, str]]:
            """
            Async task to generate collection and environment for one version.
            """
            if self.verbose:
                self.logger.info(f"Async processing version: {version.upper()}")
            
            try:
                # Scan for requests
                categorized_requests = await asyncio.to_thread(
                    self.scanner.scan_json_examples, version
                )
                
                if not categorized_requests:
                    if self.verbose:
                        self.logger.warning(f"No requests found for {version}")
                    return version, (None, None)
                
                # Organize requests
                organized_items = organize_requests_into_folders(categorized_requests)
                total_requests = sum(len(reqs) for reqs in categorized_requests.values())
                
                # Generate collection and environment
                collection = self.generate_postman_collection(version, organized_items, total_requests)
                environment = self.generate_environment_file(version)
                
                # Save files
                collection_result = await asyncio.to_thread(
                    self.file_manager.save_collection, collection, version
                )
                env_result = await asyncio.to_thread(
                    self.file_manager.save_environment, environment, version
                )
                
                if collection_result.success and env_result.success:
                    return version, (collection_result.file_path, env_result.file_path)
                else:
                    if self.verbose:
                        self.logger.error(f"Async generation failed for {version}")
                    return version, (None, None)
            
            except Exception as e:
                self.logger.error(f"Error during async generation for {version}: {e}")
                return version, (None, None)

        if self.verbose:
            self.logger.info("Starting async Postman generation...")

        tasks = [generate_single_version(version) for version in versions]
        results = await asyncio.gather(*tasks)

        if self.verbose:
            self.logger.info("Async Postman generation complete.")
        
        return {version: paths for version, paths in results if paths and all(paths)}

    def _generate_collections_async_wrapper(self, versions: List[str]) -> Dict[str, Tuple[str, str]]:
        """
        Wrapper to run the async generation method in a synchronous context.
        """
        return asyncio.run(self.generate_collections_async(versions))

    def generate_summary_report(self, results: Dict[str, Tuple[str, str]]) -> str:
        """Generate summary report using PostmanReportGenerator."""
        return self.reporter.generate_summary_report(results)
    
    def generate_scanning_report(self, versions: List[str] = ['v1', 'v2']) -> str:
        """Generate a report of the JSON scanning results."""
        scan_results = {}
        for version in versions:
            scan_results[version] = self.scanner.scan_json_examples(version)
        return self.reporter.generate_scanning_report(scan_results)
    
    def get_file_statistics(self) -> Dict:
        """Get statistics about the generated files."""
        return self.file_manager.get_file_stats()
    
    def get_file_statistics_report(self) -> str:
        """Generate a formatted report of file statistics."""
        stats = self.get_file_statistics()
        return self.reporter.generate_file_statistics_report(stats)


# --- Convenience Functions ---

def generate_postman_collections(versions: List[str] = ['v1', 'v2'], 
                                verbose: bool = True) -> Dict[str, Tuple[str, str]]:
    """
    High-level convenience function to generate Postman collections.
    """
    manager = get_postman_manager(verbose=verbose)
    results = manager.generate_collections(versions)
    
    # Print summary report
    if verbose:
        print(manager.generate_summary_report(results))
    
    return results

def get_postman_manager(config=None, verbose: bool = True) -> PostmanManager:
    """Factory function to get a PostmanManager instance."""
    return PostmanManager(config=config, verbose=verbose)

def get_postman_file_manager(collections_dir: str = "../../postman/collections",
                           environments_dir: str = "../../postman/environments") -> PostmanFileManager:
    """Factory function to get a PostmanFileManager instance."""
    return PostmanFileManager(collections_dir=collections_dir, environments_dir=environments_dir) 