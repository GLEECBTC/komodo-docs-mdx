#!/usr/bin/env python3
"""
Method Mapping Manager

Centralized manager for mapping API methods to their corresponding MDX and YAML files.
Uses enhanced configuration system and specialized components for scanning, 
normalization, and reporting.

Moved from mapping/mapping.py to managers/ for better organization.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import glob
import asyncio

# Import enhanced components
from ..constants import MethodMapping
from ..mdx.mdx_scanner import UnifiedScanner
from ..utils import (
    convert_dir_to_method_name,
    find_best_match, get_logger,
    extract_category_from_method
)
from ..managers.path_mapping_manager import EnhancedPathMapper
from ..postman.parser import PostmanCollectionParser
from ..utils.logging_utils import get_logger
from ..constants.config import EnhancedKomodoConfig, get_config



class MethodMappingManager:
    """
    Centralized manager for API method mapping operations.
    
    Coordinates scanning, normalization, and reporting of API method mappings
    across different file types (MDX, YAML, JSON examples).
    """
    
    def __init__(self, config: Optional[EnhancedKomodoConfig] = None, verbose: bool = True):
        self.config = config or get_config()
        self.verbose = verbose
        self.logger = get_logger("method-mapping-manager")
        
        # Initialize enhanced components
        self.path_mapper = EnhancedPathMapper()
        self.postman_parser = PostmanCollectionParser(verbose)
        self._reporter = None  # Lazy loading to avoid circular imports
        
        # Configure directories for UnifiedScanner using enhanced config
        self.unified_scanner = UnifiedScanner(verbose=verbose, config=self.config)
        self.branched_reports_dir = Path(self.config._resolve_path(self.config.directories.branched_reports_dir))
        
        # Add async processor for performance improvements
        self.async_processor = None
        
        if self.verbose:
            self.logger.info("🔧 MethodMappingManager initialized with flexible configuration")
            self.logger.info("🔗 Postman collection parser enabled for hotlink generation")
    
    @property
    def reporter(self):
        """Lazy loading property for MappingReporter to avoid circular imports."""
        if self._reporter is None:
            from ..reporters.mapping_reporter import MappingReporter
            self._reporter = MappingReporter(self.verbose)
        return self._reporter
    
    def _get_async_processor(self):
        """Lazy initialization of async processor."""
        if self.async_processor is None:
            from ..async_support import AsyncMethodProcessor
            self.async_processor = AsyncMethodProcessor()
        return self.async_processor

    def create_unified_mapping(self, scan_mdx=True, scan_yaml=True, scan_json=True):
        """
        Create a unified mapping of methods synchronously.

        Args:
            scan_mdx (bool): Whether to scan MDX files.
            scan_yaml (bool): Whether to scan YAML files.
            scan_json (bool): Whether to scan JSON example files.

        Returns:
            Dict[str, Dict[str, MethodMapping]]: The unified mapping.
        """
        return asyncio.run(self.create_unified_mapping_async(
            scan_mdx=scan_mdx,
            scan_yaml=scan_yaml,
            scan_json=scan_json
        ))

    def _is_overview_method(self, method_name: str, mdx_path: str) -> bool:
        """
        Check if a method corresponds to an overview page by examining the MDX content.
        
        Args:
            method_name: The method name to check
            mdx_path: Path to the MDX file
            
        Returns:
            True if this is an overview page, False otherwise
        """
        if not mdx_path or not os.path.exists(mdx_path):
            return False
            
        try:
            with open(mdx_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use the existing is_overview_page function
            from ..utils.string_utils import is_overview_page
            return is_overview_page(content)
            
        except Exception as e:
            if self.verbose:
                self.logger.warning(f"Could not check overview status for {method_name}: {e}")
            return False

    async def create_unified_mapping_async(self, scan_mdx=True, scan_yaml=True, scan_json=True) -> Dict[str, Dict[str, MethodMapping]]:
        
        processor = self._get_async_processor()
        # Build directory configurations
        mdx_dirs = {}
        yaml_dirs = {}  
        json_dirs = {}
        
        supported_versions = self.path_mapper.get_supported_versions(include_deprecated=True)
        
        for version in supported_versions:
            try:
                if version == "v1":
                    mdx_dirs[version] = self.config._resolve_path(self.config.directories.mdx_v1)
                    yaml_dirs[version] = self.config._resolve_path(self.config.directories.yaml_v1)
                    json_dirs[version] = self.config._resolve_path(self.config.directories.postman_json_v1)
                elif version == "v2":
                    mdx_dirs[version] = self.config._resolve_path(self.config.directories.mdx_v2)
                    yaml_dirs[version] = self.config._resolve_path(self.config.directories.yaml_v2)
                    json_dirs[version] = self.config._resolve_path(self.config.directories.postman_json_v2)
                elif version == "v2-dev":
                    mdx_dirs[version] = self.config._resolve_path(self.config.directories.mdx_v2_dev)
                    yaml_dirs[version] = self.config._resolve_path(self.config.directories.yaml_v2)  # v2-dev uses v2 yaml
                    json_dirs[version] = self.config._resolve_path(self.config.directories.postman_json_v2)  # v2-dev uses v2 json

            except Exception as e:
                self.logger.warning(f"Could not configure directories for version {version}: {e}")
        
        # Load canonical method names
        canonical_methods = self._load_canonical_methods()
        
        # Scan all file types concurrently using AsyncMethodProcessor
        tasks = []
        if scan_mdx:
            tasks.append(processor.scan_mdx_files_async(mdx_dirs))
        if scan_yaml:
            tasks.append(processor.scan_yaml_files_async(yaml_dirs))
        if scan_json:
            tasks.append(processor.scan_json_examples_async(json_dirs))

        if not tasks:
            self.logger.warning("No scan tasks were specified. Returning empty mapping.")
            return {}

        results = await asyncio.gather(*tasks)

        result_map = {}
        task_names = []
        if scan_mdx:
            task_names.append("mdx")
        if scan_yaml:
            task_names.append("yaml")
        if scan_json:
            task_names.append("json")

        for i, name in enumerate(task_names):
            result_map[name] = results[i]

        mdx_mappings = result_map.get("mdx", {})
        yaml_mappings = result_map.get("yaml", {})
        example_mappings = result_map.get("json", {})
        
        # Merge v2-dev into v2 right after scanning to ensure consistent path handling
        if 'v2' in mdx_mappings and 'v2-dev' in mdx_mappings:
            mdx_mappings['v2'].update(mdx_mappings.pop('v2-dev', {}))
        if 'v2' in yaml_mappings and 'v2-dev' in yaml_mappings:
            yaml_mappings['v2'].update(yaml_mappings.pop('v2-dev', {}))
        if 'v2' in example_mappings and 'v2-dev' in example_mappings:
            example_mappings['v2'].update(example_mappings.pop('v2-dev', {}))

        # Also merge canonical methods
        if 'v2' in canonical_methods and 'v2-dev' in canonical_methods:
            v2_set = set(canonical_methods['v2'])
            v2_dev_set = set(canonical_methods.pop('v2-dev', []))
            v2_set.update(v2_dev_set)
            canonical_methods['v2'] = sorted(list(v2_set))
        
        # Rest of the mapping logic remains the same
        unified = {}
        
        # Get all canonical versions to process
        canonical_versions_to_process = self.config.version_mapping.get_all_canonical_versions()

        # Remove v2-dev since it's merged into v2
        if 'v2-dev' in canonical_versions_to_process:
            canonical_versions_to_process.remove('v2-dev')

        for version in canonical_versions_to_process:
            if version not in mdx_mappings and version not in yaml_mappings and version not in example_mappings:
                if self.verbose:
                    self.logger.debug(f"Skipping version {version} as no data was found.")
                continue

            unified[version] = {}
            
            # Use canonical methods as the authoritative source
            canonical_method_list = canonical_methods.get(version, [])
            
            # Convert discovered methods from filesystem format to canonical format
            canonical_discovered_methods = set()
            for method in mdx_mappings.get(version, {}).keys():
                canonical_discovered_methods.add(convert_dir_to_method_name(method))
            for method in yaml_mappings.get(version, {}).keys():
                canonical_discovered_methods.add(convert_dir_to_method_name(method))
            for method in example_mappings.get(version, {}).keys():
                canonical_discovered_methods.add(convert_dir_to_method_name(method))
            
            # Combine canonical methods with canonical discovered methods
            all_methods = set(canonical_method_list) | canonical_discovered_methods
            
            if self.verbose:
                print(f"📋 Processing {len(all_methods)} {version.upper()} methods asynchronously...")
                print(f"   📋 {len(canonical_method_list)} from canonical source")
                print(f"   📋 {len(canonical_discovered_methods)} discovered and normalized")
            
            # Create enhanced mapping for each method
            overview_methods_filtered = 0
            for method in sorted(list(all_methods)):
                # Find matching method name and get the file path
                mdx_method_key = find_best_match(method, mdx_mappings.get(version, {}))
                mdx_path = mdx_mappings.get(version, {}).get(mdx_method_key) if mdx_method_key else None
                
                # Filter out overview pages
                if mdx_path and self._is_overview_method(method, mdx_path):
                    overview_methods_filtered += 1
                    if self.verbose:
                        self.logger.debug(f"Filtering out overview page: {method} ({mdx_path})")
                    continue
                
                yaml_method_key = find_best_match(method, yaml_mappings.get(version, {}))
                yaml_path = yaml_mappings.get(version, {}).get(yaml_method_key) if yaml_method_key else None
                
                # Handle example mappings
                examples_path = None
                example_count = 0
                example_method_key = find_best_match(method, example_mappings.get(version, {}))
                if example_method_key and example_method_key in example_mappings.get(version, {}):
                    example_data = example_mappings[version][example_method_key]
                    if isinstance(example_data, tuple) and len(example_data) == 2:
                        examples_path, example_count = example_data
                    elif isinstance(example_data, str):
                        examples_path = example_data
                        example_count = 1
                
                # Get enhanced metadata
                version_status = self.config.get_version_status(version)
                is_deprecated = self.config.is_version_deprecated(version)
                
                # Extract category from method name or path
                category, _ = extract_category_from_method(method)
                
                unified[version][method] = MethodMapping(
                    method=method,
                    mdx_path=mdx_path,
                    yaml_path=yaml_path,
                    examples_path=examples_path,
                    example_count=example_count,
                    version=version,
                    category=category,
                    deprecated=is_deprecated
                )
                
            if self.verbose and overview_methods_filtered > 0:
                print(f"   ✅ Filtered out {overview_methods_filtered} overview pages from {version.upper()}")
        
        # Integrate Postman collection hotlinks
        unified = self._integrate_postman_hotlinks(unified)
        
        # Merge v2-dev into v2 to treat them as a single version downstream
        if 'v2' in unified and 'v2-dev' in unified:
            v2_methods = unified.get('v2', {})
            v2_dev_methods = unified.pop('v2-dev', {})  # Use pop to get and remove
            
            merged_count = 0
            for method, mapping in v2_dev_methods.items():
                if method not in v2_methods:
                    # Re-assign version and merge
                    mapping.version = 'v2'
                    v2_methods[method] = mapping
                    merged_count += 1
            
            unified['v2'] = v2_methods
            
            if self.verbose and merged_count > 0:
                print(f"   ✅ Merged {merged_count} v2-dev methods into v2, treating as a single version.")
        
        # Final check for unified mapping content before saving
        if self.verbose:
            self._print_enhanced_mapping_stats(unified)
        
        return unified
    
    def _extract_category_from_method(self, method_name: str) -> Optional[str]:
        pass
    
    def _load_canonical_methods(self) -> Dict[str, List[str]]:
        """Load canonical method names from the MDX method paths report."""
        canonical_methods = {"v1": [], "v2": []}
        
        try:
            paths_file = self.config.directories.mdx_method_paths_report
            if paths_file.exists():
                with open(paths_file, 'r') as f:
                    data = json.load(f)
                
                v1_methods = data.get("method_paths", {}).get("v1", {})
                v2_methods = data.get("method_paths", {}).get("v2", {})
                
                canonical_methods["v1"] = sorted(list(v1_methods.keys()))
                canonical_methods["v2"] = sorted(list(v2_methods.keys()))
                
                if self.verbose:
                    self.logger.info(f"Loaded {len(canonical_methods['v1'])} V1 and {len(canonical_methods['v2'])} V2 canonical methods.")
            else:
                self.logger.warning(f"Canonical methods file not found: {paths_file}")

        except Exception as e:
            if self.verbose:
                self.logger.warning(f"Could not load canonical methods: {e}")
        
        return canonical_methods
    
    def _print_enhanced_mapping_stats(self, unified: Dict[str, Dict[str, MethodMapping]]) -> None:
        """Print enhanced mapping statistics."""
        print("\n📊 Enhanced Mapping Statistics:")
        
        # Consolidate v2-dev with v2 for statistics (v2-dev is just an alias of v2)
        consolidated_unified = {}
        
        for version, methods in unified.items():
            if version == "v2-dev":
                # Merge v2-dev methods with v2
                if "v2" not in consolidated_unified:
                    consolidated_unified["v2"] = {}
                consolidated_unified["v2"].update(methods)
            else:
                consolidated_unified[version] = methods
        
        for version, methods in consolidated_unified.items():
            total = len(methods)
            complete = sum(1 for m in methods.values() if m.is_complete)
            has_mdx = sum(1 for m in methods.values() if m.has_mdx)
            has_yaml = sum(1 for m in methods.values() if m.has_yaml)
            has_examples = sum(1 for m in methods.values() if m.has_examples)
            has_postman = sum(1 for m in methods.values() if m.has_postman_links)
            deprecated = sum(1 for m in methods.values() if m.deprecated)
            
            avg_completeness = sum(m.completeness_score for m in methods.values()) / total if total > 0 else 0
            
            print(f"\n🏷️  {version.upper()}:")
            print(f"   📄 Total methods: {total}")
            print(f"   ✅ Complete: {complete} ({complete/total*100:.1f}%)")
            print(f"   📝 With MDX: {has_mdx} ({has_mdx/total*100:.1f}%)")
            print(f"   📋 With YAML: {has_yaml} ({has_yaml/total*100:.1f}%)")
            print(f"   📊 With Examples: {has_examples} ({has_examples/total*100:.1f}%)")
            print(f"   🔗 With Postman Links: {has_postman} ({has_postman/total*100:.1f}%)")
            print(f"   ⚠️  Deprecated: {deprecated} ({deprecated/total*100:.1f}%)")
            print(f"   📈 Avg Completeness: {avg_completeness:.2f}")
    
    def save_unified_mapping(self, unified_mapping, filename="unified_method_mapping.json"):
        """Saves the unified mapping to a file in the data directory."""

        output_path = self.branched_reports_dir / filename
        
        try:
            with open(output_path, 'w') as f:
                json.dump(unified_mapping, f, indent=4)
            self.logger.success(f"✅ Saved unified mapping to {output_path} [347]")
            return str(output_path)
        except IOError as e:
            self.logger.error(f"❌ Error saving unified mapping to {output_path}: {e}")
            return None

    def load_unified_mapping(self, filename="unified_method_mapping.json"):
        """Loads the unified mapping from a file in the data directory."""
        file_path = self.branched_reports_dir / filename
        if not file_path.exists():
            self.logger.warning(f"⚠️  Could not find unified mapping file: {file_path}")
            return None
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            self.logger.error(f"❌ Error loading unified mapping from {file_path}: {e}")
            return None

    def save_method_paths(self, method_paths, filename="kdf_postman_method_paths.json"):
        """Saves the method paths with Postman hotlinks."""
        
        # separate filename from extension
        parts = filename.split('.')
        base_name = parts[0]
        extension = parts[1] if len(parts) > 1 else 'json'
        output_path = self.branched_reports_dir / f"{base_name}.{extension}"
        
        try:
            with open(output_path, 'w') as f:
                json.dump(method_paths, f, indent=4)
            self.logger.info(f"✅  📝 Saved method paths with 0 Postman hotlinks to {output_path}")
            return str(output_path)
        except IOError as e:
            self.logger.error(f"❌ Error saving method paths to {output_path}: {e}")
            return None
    
    def _save_method_paths_with_hotlinks(self, unified: Dict[str, Dict[str, MethodMapping]]) -> None:
        """Save method paths with Postman collection hotlinks to dedicated file (synchronous version)."""
        from datetime import datetime
        
        # Create method paths structure with hotlinks
        method_paths_data = {
            "scan_metadata": {
                "generated_at": datetime.now().isoformat(),
                "scanner_version": "KDF Method Path Mapper with Postman Hotlinks v1.0.0",
                "scanner_type": "METHOD_PATH_MAPPING_WITH_POSTMAN_HOTLINKS",
                "total_methods_with_mdx_paths": sum(
                    len([m for m in methods.values() if m.has_mdx])
                    for methods in unified.values()
                ),
                "total_methods_with_postman_links": sum(
                    len([m for m in methods.values() if m.has_postman_links])
                    for methods in unified.values()
                ),
                "versions_processed": [v for v in unified.keys() if v in ['v1', 'v2']],
                "includes_postman_hotlinks": True,
                "generated_during_unified_mapping": True
            },
            "method_paths": {}
        }
        
        # Build method paths with hotlinks
        for version in ['v1', 'v2']:
            if version in unified:
                version_methods = {}
                
                for method_name, mapping in unified[version].items():
                    method_info = {
                        "mdx_path": mapping.mdx_path
                    }
                    
                    # Add Postman collection hotlinks if available
                    if mapping.has_postman_links:
                        method_info["postman_collection"] = mapping.postman_collection_info
                    
                    version_methods[method_name] = method_info
                
                # Sort methods alphabetically within this version
                method_paths_data["method_paths"][version] = dict(sorted(version_methods.items()))
        
        # Save to dedicated method paths file
        output_filename = f"kdf_postman_method_paths.json"
        output_file = self.branched_reports_dir / output_filename

        def write_method_paths_file():
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(method_paths_data, f, indent=2, ensure_ascii=False)

        write_method_paths_file()
        
        if self.verbose:
            total_with_hotlinks = method_paths_data["scan_metadata"]["total_methods_with_postman_links"]
            self.logger.success(f"📝 Saved method paths with {total_with_hotlinks} Postman hotlinks to {output_file}")

    async def save_unified_mapping_async(self, output_file: Optional[str] = None) -> None:
        """Save unified mapping to JSON file with metadata asynchronously."""
        unified = await self.create_unified_mapping_async()
        
        # Convert to JSON-serializable format with proper structure
        json_data = await self._convert_mapping_to_enhanced_json(unified)

        if output_file is None:
            output_file_path = self.branched_reports_dir / "unified_method_mapping.json"
        else:
            # If an output file is provided, make sure it's inside the reports dir
            output_file_path = self.branched_reports_dir / Path(output_file).name
        
        def write_json_file():
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
                self.logger.info(f"✅ Saved unified mapping to {output_file_path}")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_json_file)
        
        # Also save method paths with hotlinks to separate file
        await self._save_method_paths_with_hotlinks_async(unified)
        
        if self.verbose:
            print(f"✅ Saved unified mapping to {output_file_path}")
            self._print_enhanced_mapping_stats(unified)

    async def _convert_mapping_to_enhanced_json(self, unified: Dict[str, Dict[str, MethodMapping]]) -> Dict[str, Any]:
        """Convert mapping objects to enhanced JSON format with missing methods analysis."""
        # Build the core structure
        json_data = {
            "method_paths": {},
            "summary_statistics": {},
            "missing": {}
        }
        
        # Build method_paths section (restructured format)
        for version in unified:
            if version in ['v1', 'v2']:  # Only include main versions
                json_data["method_paths"][version] = {}
                for method in sorted(unified[version].keys()):
                    mapping = unified[version][method]
                    method_data = {
                        'method': mapping.method,
                        'mdx_path': mapping.mdx_path,
                        'yaml_path': mapping.yaml_path,
                        'examples_path': mapping.examples_path,
                        'postman_path': self._extract_postman_path(mapping),
                        'has_mdx': mapping.has_mdx,
                        'has_yaml': mapping.has_yaml,
                        'has_examples': mapping.has_examples,
                        'has_postman': mapping.has_postman_links,
                        'is_complete': mapping.is_complete
                    }
                    json_data["method_paths"][version][method] = method_data
        
        # Generate summary statistics
        json_data["summary_statistics"] = await self._generate_summary_statistics(unified)
        
        # Generate missing methods analysis
        json_data["missing"] = await self._generate_missing_methods_analysis(unified)
        
        # Update summary with missing methods info if analysis was successful
        if "statistics" in json_data["missing"] and "overall" in json_data["missing"]["statistics"]:
            missing_stats = json_data["missing"]["statistics"]["overall"]
            if "analysis_status" not in missing_stats:  # Only if analysis was successful
                json_data["summary_statistics"]["includes_missing_methods_analysis"] = True
                json_data["summary_statistics"]["total_missing_methods"] = missing_stats["total_missing_methods"]
                json_data["summary_statistics"]["overall_documentation_coverage_percentage"] = missing_stats["overall_coverage_percentage"]
                json_data["summary_statistics"]["documentation_completeness_status"] = missing_stats["documentation_completeness_status"]
        
        return json_data
    
    def _extract_postman_path(self, mapping: MethodMapping) -> Optional[str]:
        """Extract the postman collection file path from mapping."""
        if mapping.has_postman_links and mapping.postman_collection_info:
            collection_info = mapping.postman_collection_info.get("collection_info", {})
            return collection_info.get("file")
        return None
    
    async def _generate_summary_statistics(self, unified: Dict[str, Dict[str, MethodMapping]]) -> Dict[str, Any]:
        """Generate comprehensive summary statistics."""
        # Calculate coverage statistics
        total_methods = sum(len(methods) for version, methods in unified.items() if version in ['v1', 'v2'])
        
        mdx_count = sum(len([m for m in methods.values() if m.has_mdx]) 
                       for version, methods in unified.items() if version in ['v1', 'v2'])
        yaml_count = sum(len([m for m in methods.values() if m.has_yaml]) 
                        for version, methods in unified.items() if version in ['v1', 'v2'])
        examples_count = sum(len([m for m in methods.values() if m.has_examples]) 
                            for version, methods in unified.items() if version in ['v1', 'v2'])
        postman_count = sum(len([m for m in methods.values() if m.has_postman_links]) 
                           for version, methods in unified.items() if version in ['v1', 'v2'])
        complete_count = sum(len([m for m in methods.values() if m.is_complete]) 
                            for version, methods in unified.items() if version in ['v1', 'v2'])
        
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_methods": total_methods,
            "coverage_overview": {
                "mdx_coverage": {
                    "count": mdx_count,
                    "percentage": round(mdx_count / total_methods * 100, 1) if total_methods > 0 else 0
                },
                "yaml_coverage": {
                    "count": yaml_count,
                    "percentage": round(yaml_count / total_methods * 100, 1) if total_methods > 0 else 0
                },
                "examples_coverage": {
                    "count": examples_count,
                    "percentage": round(examples_count / total_methods * 100, 1) if total_methods > 0 else 0
                },
                "postman_coverage": {
                    "count": postman_count,
                    "percentage": round(postman_count / total_methods * 100, 1) if total_methods > 0 else 0
                },
                "complete_coverage": {
                    "count": complete_count,
                    "percentage": round(complete_count / total_methods * 100, 1) if total_methods > 0 else 0
                }
            },
            "version_breakdown": {}
        }
        
        # Version-specific statistics
        for version in ['v1', 'v2']:
            if version in unified:
                methods = unified[version]
                version_total = len(methods)
                
                version_mdx = len([m for m in methods.values() if m.has_mdx])
                version_yaml = len([m for m in methods.values() if m.has_yaml])
                version_examples = len([m for m in methods.values() if m.has_examples])
                version_postman = len([m for m in methods.values() if m.has_postman_links])
                version_complete = len([m for m in methods.values() if m.is_complete])
                
                summary["version_breakdown"][version] = {
                    "total_methods": version_total,
                    "mdx_coverage": {
                        "count": version_mdx,
                        "percentage": round(version_mdx / version_total * 100, 1) if version_total > 0 else 0
                    },
                    "yaml_coverage": {
                        "count": version_yaml,
                        "percentage": round(version_yaml / version_total * 100, 1) if version_total > 0 else 0
                    },
                    "examples_coverage": {
                        "count": version_examples,
                        "percentage": round(version_examples / version_total * 100, 1) if version_total > 0 else 0
                    },
                    "postman_coverage": {
                        "count": version_postman,
                        "percentage": round(version_postman / version_total * 100, 1) if version_total > 0 else 0
                    },
                    "complete_coverage": {
                        "count": version_complete,
                        "percentage": round(version_complete / version_total * 100, 1) if version_total > 0 else 0
                    }
                }
        
        return summary
    
    async def _generate_missing_methods_analysis(self, unified: Dict[str, Dict[str, MethodMapping]]) -> Dict[str, Any]:
        """Generate missing methods analysis by comparing against canonical Rust methods."""
        try:
            # Find the latest Rust methods file
            rust_methods = await self._load_canonical_rust_methods()
            documented_methods = self._extract_documented_methods_from_unified(unified)
            
            # Calculate missing methods
            missing_methods = self._calculate_missing_methods(rust_methods, documented_methods)
            missing_stats = self._generate_missing_statistics(rust_methods, documented_methods, missing_methods)
            
            # Get the source file reference
            branched_reports_dir = self.config._resolve_path(self.config.directories.branched_reports_dir)
            rust_files = glob.glob(os.path.join(branched_reports_dir, "kdf_rust_methods.json"))
            rust_file_name = Path(max(rust_files, key=lambda x: Path(x).stat().st_mtime)).name if rust_files else "unknown"
            
            return {
                "description": "Methods that exist in the Komodo DeFi Framework repository but lack documentation coverage",
                "data_source": {
                    "canonical_methods_source": rust_file_name,
                    "comparison_date": datetime.now().isoformat(),
                    "missing_criteria": "Methods present in Rust repository but not in method_paths"
                },
                "statistics": missing_stats,
                "methods_lacking_coverage": missing_methods
            }
            
        except Exception as e:
            if self.verbose:
                self.logger.warning(f"Could not generate missing methods analysis: {e}")
            
            # Return empty structure if analysis fails
            return {
                "description": "Missing methods analysis unavailable - canonical Rust methods file not found",
                "data_source": {
                    "canonical_methods_source": "not_available",
                    "comparison_date": datetime.now().isoformat(),
                    "missing_criteria": "Analysis skipped due to missing data"
                },
                "statistics": {
                    "overall": {"analysis_status": "unavailable"},
                    "v1": {"analysis_status": "unavailable"},
                    "v2": {"analysis_status": "unavailable"}
                },
                "methods_lacking_coverage": {"v1": [], "v2": []}
            }
    
    async def _load_canonical_rust_methods(self) -> Dict[str, Set[str]]:
        """
        Asynchronously loads canonical Rust methods from the latest 'kdf_rust_methods.json' report.
        """
        rust_methods = {}
        
        # Find the latest rust methods report
        rust_files = glob.glob(str(self.config.directories.rust_methods_report))
        if not rust_files:
            if self.verbose:
                self.logger.warning("No Rust method report found. Cannot perform gap analysis.")
            return rust_methods
        
        # Get the most recent file
        latest_file = max(rust_files, key=lambda x: Path(x).stat().st_mtime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            rust_data = json.load(f)
        
        rust_methods = {"v1": set(), "v2": set()}
        
        if "repository_data" in rust_data:
            for version in ["v1", "v2"]:
                if version in rust_data["repository_data"]:
                    methods_list = rust_data["repository_data"][version].get("methods", [])
                    rust_methods[version] = set(methods_list)
        
        return rust_methods
    
    def _extract_documented_methods_from_unified(self, unified: Dict[str, Dict[str, MethodMapping]]) -> Dict[str, Set[str]]:
        """Extract documented method names from unified mapping."""
        documented_methods = {"v1": set(), "v2": set()}
        
        for version in ["v1", "v2"]:
            if version in unified:
                documented_methods[version] = set(unified[version].keys())
        
        return documented_methods
    
    def _calculate_missing_methods(self, rust_methods: Dict[str, Set[str]], 
                                  documented_methods: Dict[str, Set[str]]) -> Dict[str, List[str]]:
        """Calculate which methods are missing documentation coverage."""
        missing_methods = {"v1": [], "v2": []}
        
        for version in ["v1", "v2"]:
            rust_set = rust_methods.get(version, set())
            documented_set = documented_methods.get(version, set())
            
            # Methods that exist in Rust but don't have documentation
            missing_set = rust_set - documented_set
            missing_methods[version] = sorted(list(missing_set))
        
        return missing_methods
    
    def _generate_missing_statistics(self, rust_methods: Dict[str, Set[str]], 
                                   documented_methods: Dict[str, Set[str]], 
                                   missing_methods: Dict[str, List[str]]) -> Dict[str, Any]:
        """Generate comprehensive statistics about missing methods."""
        stats = {}
        
        total_rust = sum(len(methods) for methods in rust_methods.values())
        total_documented = sum(len(methods) for methods in documented_methods.values())
        total_missing = sum(len(methods) for methods in missing_methods.values())
        
        overall_coverage = (total_documented / total_rust * 100) if total_rust > 0 else 0
        
        stats["overall"] = {
            "total_canonical_methods": total_rust,
            "total_documented_methods": total_documented,
            "total_missing_methods": total_missing,
            "overall_coverage_percentage": round(overall_coverage, 1),
            "documentation_completeness_status": "complete" if total_missing == 0 else "incomplete"
        }
        
        # Version-specific statistics
        for version in ["v1", "v2"]:
            rust_count = len(rust_methods.get(version, set()))
            documented_count = len(documented_methods.get(version, set()))
            missing_count = len(missing_methods.get(version, []))
            
            coverage = (documented_count / rust_count * 100) if rust_count > 0 else 0
            
            stats[version] = {
                "canonical_methods": rust_count,
                "documented_methods": documented_count,
                "missing_methods": missing_count,
                "coverage_percentage": round(coverage, 1),
                "completeness_status": "complete" if missing_count == 0 else "incomplete"
            }
        
        return stats
    
    def _integrate_postman_hotlinks(self, unified: Dict[str, Dict[str, MethodMapping]]) -> Dict[str, Dict[str, MethodMapping]]:
        """
        Integrate Postman collection hotlinks into the unified mapping.
        
        Args:
            unified: The unified mapping dictionary
            
        Returns:
            Enhanced unified mapping with Postman hotlinks
        """
        if self.verbose:
            self.logger.info("🔗 Integrating Postman collection hotlinks...")
        
        # Parse Postman collections for hotlinks
        version_hotlinks = self._parse_postman_collections_for_hotlinks()
        
        # Integrate hotlinks into existing mappings
        enhanced_unified = {}
        total_hotlinks_added = 0
        
        for version, methods in unified.items():
            enhanced_unified[version] = {}
            
            # Use centralized version mapping configuration
            postman_version = self.config.get_postman_version(version)
            version_hotlinks_data = version_hotlinks.get(postman_version, {})
            
            if self.verbose and version != postman_version:
                self.logger.info(f"📋 Mapping {version} methods to {postman_version} Postman collection ({len(version_hotlinks_data)} hotlinks available)")
            
            for method_name, mapping in methods.items():
                # Get Postman collection info for this method
                postman_info = version_hotlinks_data.get(method_name)
                
                # Create enhanced mapping with postman info
                enhanced_mapping = MethodMapping(
                    method=mapping.method,
                    mdx_path=mapping.mdx_path,
                    yaml_path=mapping.yaml_path,
                    examples_path=mapping.examples_path,
                    example_count=mapping.example_count,
                    version=mapping.version,
                    category=mapping.category,
                    deprecated=mapping.deprecated,
                    postman_collection_info=postman_info
                )
                
                if enhanced_mapping.has_postman_links:
                    total_hotlinks_added += 1
                
                enhanced_unified[version][method_name] = enhanced_mapping
        
        if self.verbose:
            self.logger.success(f"✅ Integrated {total_hotlinks_added} Postman hotlinks into unified mapping")
        
        return enhanced_unified

    def _parse_postman_collections_for_hotlinks(self) -> Dict[str, Dict[str, Dict]]:
        """
        Parse Postman collections to extract hotlink information.
        
        Returns:
            Dictionary mapping versions to method hotlinks
        """
        try:
            # Use PostmanCollectionParser to parse all collections
            collections_dir = self.config._resolve_path("postman/collections")
            version_hotlinks = self.postman_parser.parse_all_collections(collections_dir)
            
            # Convert to hotlink format
            hotlinks_by_version = {}
            for version, method_mappings in version_hotlinks.items():
                hotlinks_by_version[version] = self.postman_parser.generate_postman_hotlinks(method_mappings)
            
            if self.verbose:
                total_hotlinks = sum(len(methods) for methods in hotlinks_by_version.values())
                self.logger.info(f"📋 Parsed {total_hotlinks} Postman hotlinks across {len(hotlinks_by_version)} versions")
            
            return hotlinks_by_version
            
        except Exception as e:
            if self.verbose:
                self.logger.warning(f"⚠️ Could not parse Postman collections: {e}")
            return {}

    async def _save_method_paths_with_hotlinks_async(self, unified: Dict[str, Dict[str, MethodMapping]]) -> None:
        """
        Asynchronously extracts method paths with Postman hotlinks and saves to a timestamped file.
        """
        if self.verbose:
            self.logger.save("Saving method paths with Postman hotlinks...")
            
        method_paths = {}
        for version, methods in unified.items():
            method_paths[version] = {
                method: self._extract_postman_path(mapping)
                for method, mapping in methods.items()
                if self._extract_postman_path(mapping)
            }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"kdf_postman_collection_method_paths.json"
        
        output_path = self.branched_reports_dir / filename

        def write_method_paths_file():
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(method_paths, f, indent=2, ensure_ascii=False)
                if self.verbose:
                    self.logger.info(f"✅ Saved method paths to {output_path}")
            except IOError as e:
                self.logger.error(f"❌ Error saving method paths to {output_path}: {e}")

        await asyncio.to_thread(write_method_paths_file) 