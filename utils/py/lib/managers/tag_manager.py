#!/usr/bin/env python3
"""
TagManager - Derive and apply common tags for KDF methods based on defining characteristics.

This module provides functionality to automatically tag KDF methods based on their properties
such as method names, request structure, wallet types, and environments.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


class TagManager:
    """
    Manages automatic tag derivation and application for KDF methods.
    
    Tags are derived based on:
    - Request structure (mmrpc version)
    - Method name patterns (task::, trezor, metamask)
    - Environment and wallet type singularity
    """
    
    def __init__(self, kdf_methods_path: Union[str, Path], requests_base_path: Union[str, Path]):
        """
        Initialize the TagManager.
        
        Args:
            kdf_methods_path: Path to the kdf_methods.json file
            requests_base_path: Path to the base directory containing request files
        """
        self.kdf_methods_path = Path(kdf_methods_path)
        self.requests_base_path = Path(requests_base_path)
        self.kdf_methods = {}
        # Track which file each method came from for saving
        self._method_source: Dict[str, Path] = {}
        self.request_data = {}
        
        self._load_data()
    
    def _load_data(self) -> None:
        """Load KDF methods and request data from files.
        
        Supports either a single file path or a directory containing
        kdf_methods_v2.json and kdf_methods_legacy.json. Methods are
        preserved from both files without merging on disk; in-memory we
        combine for analysis while tracking the source file for each method.
        """
        try:
            methods: Dict[str, Any] = {}
            if self.kdf_methods_path.is_dir():
                v2_file = self.kdf_methods_path / "kdf_methods_v2.json"
                legacy_file = self.kdf_methods_path / "kdf_methods_legacy.json"
                if legacy_file.exists():
                    with open(legacy_file, 'r') as f:
                        legacy_methods = json.load(f)
                        methods.update(legacy_methods)
                        for m in legacy_methods.keys():
                            self._method_source[m] = legacy_file
                if v2_file.exists():
                    with open(v2_file, 'r') as f:
                        v2_methods = json.load(f)
                        # v2 methods are distinct; if overlaps, track v2 as the source
                        methods.update(v2_methods)
                        for m in v2_methods.keys():
                            self._method_source[m] = v2_file
                if not methods:
                    raise FileNotFoundError(f"No methods files found in {self.kdf_methods_path}")
            else:
                with open(self.kdf_methods_path, 'r') as f:
                    methods = json.load(f)
                    for m in methods.keys():
                        self._method_source[m] = self.kdf_methods_path
            
            self.kdf_methods = methods
            logger.info(f"Loaded {len(self.kdf_methods)} KDF methods")
            
            # Load request data from all request files
            self._load_request_data()
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    
    def _load_request_data(self) -> None:
        """Load all request data from the requests directory structure."""
        self.request_data = {}
        
        # Find all JSON files in the requests directory
        request_files = list(self.requests_base_path.rglob("*.json"))
        
        for request_file in request_files:
            try:
                with open(request_file, 'r') as f:
                    file_data = json.load(f)
                    # Merge all request examples into a single dict
                    self.request_data.update(file_data)
                    logger.info(f"Loaded {len(file_data)} requests from {request_file}")
            except Exception as e:
                logger.warning(f"Error loading request file {request_file}: {e}")
        
        logger.info(f"Loaded {len(self.request_data)} total request examples")
    
    def derive_tags_for_method(self, method_name: str, method_data: Dict[str, Any]) -> Set[str]:
        """
        Derive tags for a single KDF method based on its characteristics.
        
        Args:
            method_name: The name of the KDF method
            method_data: The method's data from kdf_methods.json
            
        Returns:
            Set of derived tags
        """
        tags = set()
        
        # Rule 1: Check if method's request(s) contain "mmrpc": "2.0"
        if self._has_mmrpc_v2(method_data):
            tags.add("v2")
        
        # Rule 2: Check if method name starts with "task::"
        if method_name.startswith("task::"):
            tags.add("task-based")
        
        # Rule 3: Check if wallet_types has a single value
        wallet_type_tag = self._get_single_wallet_type_tag(method_data)
        if wallet_type_tag:
            tags.add(wallet_type_tag)
        
        # Rule 4: Check if environments has a single value
        environment_tag = self._get_single_environment_tag(method_data)
        if environment_tag:
            tags.add(environment_tag)
        
        # Rule 5: Check if method name or request examples include "trezor"
        if self._has_trezor_reference(method_name, method_data):
            tags.add("trezor")
        
        # Rule 6: Check if method name or request examples include "metamask"
        if self._has_metamask_reference(method_name, method_data):
            tags.add("metamask")
        
        return tags
    
    def _has_mmrpc_v2(self, method_data: Dict[str, Any]) -> bool:
        """
        Check if any of the method's request examples contain "mmrpc": "2.0".
        
        Args:
            method_data: The method's data from kdf_methods.json
            
        Returns:
            True if any request has mmrpc 2.0, False otherwise
        """
        examples = method_data.get("examples", {})
        
        for example_name in examples.keys():
            request_data = self.request_data.get(example_name, {})
            if request_data.get("mmrpc") == "2.0":
                return True
        
        return False
    
    def _get_single_wallet_type_tag(self, method_data: Dict[str, Any]) -> Optional[str]:
        """
        Get wallet type tag if there's only one wallet type.
        
        Args:
            method_data: The method's data from kdf_methods.json
            
        Returns:
            Wallet type tag if single, None otherwise
        """
        requirements = method_data.get("requirements", {})
        wallet_types = requirements.get("wallet_types", [])
        
        if len(wallet_types) == 1:
            return wallet_types[0]
        
        return None
    
    def _get_single_environment_tag(self, method_data: Dict[str, Any]) -> Optional[str]:
        """
        Get environment tag if there's only one environment.
        
        Args:
            method_data: The method's data from kdf_methods.json
            
        Returns:
            Environment tag if single, None otherwise
        """
        requirements = method_data.get("requirements", {})
        environments = requirements.get("environments", [])
        
        if len(environments) == 1:
            return environments[0]
        
        return None
    
    def _has_trezor_reference(self, method_name: str, method_data: Dict[str, Any]) -> bool:
        """
        Check if method name or request examples reference trezor.
        
        Args:
            method_name: The method name
            method_data: The method's data from kdf_methods.json
            
        Returns:
            True if trezor is referenced, False otherwise
        """
        # Check method name
        if "trezor" in method_name.lower():
            return True
        
        # Check example names and descriptions
        examples = method_data.get("examples", {})
        for example_name, description in examples.items():
            if "trezor" in example_name.lower() or "trezor" in description.lower():
                return True
        
        # Check request data for trezor references
        for example_name in examples.keys():
            request_data = self.request_data.get(example_name, {})
            if self._contains_trezor_in_request(request_data):
                return True
        
        return False
    
    def _has_metamask_reference(self, method_name: str, method_data: Dict[str, Any]) -> bool:
        """
        Check if method name or request examples reference metamask.
        
        Args:
            method_name: The method name
            method_data: The method's data from kdf_methods.json
            
        Returns:
            True if metamask is referenced, False otherwise
        """
        # Check method name
        if "metamask" in method_name.lower():
            return True
        
        # Check example names and descriptions
        examples = method_data.get("examples", {})
        for example_name, description in examples.items():
            if "metamask" in example_name.lower() or "metamask" in description.lower():
                return True
        
        # Check request data for metamask references
        for example_name in examples.keys():
            request_data = self.request_data.get(example_name, {})
            if self._contains_metamask_in_request(request_data):
                return True
        
        return False
    
    def _contains_trezor_in_request(self, request_data: Dict[str, Any]) -> bool:
        """
        Recursively search for trezor references in request data.
        
        Args:
            request_data: The request data dictionary
            
        Returns:
            True if trezor is found, False otherwise
        """
        return self._contains_string_in_data(request_data, "trezor")
    
    def _contains_metamask_in_request(self, request_data: Dict[str, Any]) -> bool:
        """
        Recursively search for metamask references in request data.
        
        Args:
            request_data: The request data dictionary
            
        Returns:
            True if metamask is found, False otherwise
        """
        return self._contains_string_in_data(request_data, "metamask")
    
    def _contains_string_in_data(self, data: Any, search_string: str) -> bool:
        """
        Recursively search for a string in any data structure.
        
        Args:
            data: The data to search (can be dict, list, str, etc.)
            search_string: The string to search for (case insensitive)
            
        Returns:
            True if string is found, False otherwise
        """
        if isinstance(data, str):
            return search_string.lower() in data.lower()
        elif isinstance(data, dict):
            for key, value in data.items():
                if search_string.lower() in key.lower():
                    return True
                if self._contains_string_in_data(value, search_string):
                    return True
        elif isinstance(data, list):
            for item in data:
                if self._contains_string_in_data(item, search_string):
                    return True
        
        return False
    
    def derive_tags_for_all_methods(self) -> Dict[str, Set[str]]:
        """
        Derive tags for all KDF methods.
        
        Returns:
            Dictionary mapping method names to their derived tags
        """
        all_derived_tags = {}
        
        for method_name, method_data in self.kdf_methods.items():
            derived_tags = self.derive_tags_for_method(method_name, method_data)
            all_derived_tags[method_name] = derived_tags
        
        return all_derived_tags
    
    def apply_derived_tags(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Apply derived tags to all methods in the KDF methods data.
        
        Args:
            dry_run: If True, don't modify files, just return what would be changed
            
        Returns:
            Dictionary with statistics about tag changes
        """
        derived_tags = self.derive_tags_for_all_methods()
        changes = {
            "methods_modified": 0,
            "tags_added": 0,
            "tags_removed": 0,
            "modifications": {}
        }
        
        # Create a working copy of the methods data
        updated_methods = json.loads(json.dumps(self.kdf_methods))
        
        for method_name, method_data in updated_methods.items():
            current_tags = set(method_data.get("tags", []))
            new_tags = derived_tags.get(method_name, set())
            
            # Combine existing tags with derived tags (derived tags take precedence for conflicts)
            combined_tags = current_tags.union(new_tags)
            combined_tags_list = sorted(list(combined_tags))
            
            # Track changes
            if set(combined_tags_list) != current_tags:
                changes["methods_modified"] += 1
                added = new_tags - current_tags
                removed = current_tags - new_tags  # In case we want to implement tag removal logic later
                
                changes["tags_added"] += len(added)
                changes["tags_removed"] += len(removed)
                
                changes["modifications"][method_name] = {
                    "old_tags": sorted(list(current_tags)),
                    "new_tags": combined_tags_list,
                    "added_tags": sorted(list(added)),
                    "removed_tags": sorted(list(removed))
                }
                
                # Update the method data
                method_data["tags"] = combined_tags_list
        
        # Save the changes if not a dry run
        if not dry_run:
            self._save_updated_methods(updated_methods)
            logger.info(f"Applied tags to {changes['methods_modified']} methods")
        else:
            logger.info(f"Dry run: Would modify {changes['methods_modified']} methods")
        
        return changes
    
    def _save_updated_methods(self, updated_methods: Dict[str, Any]) -> None:
        """
        Save the updated methods data back to the file.
        
        Args:
            updated_methods: The updated methods data
        """
        try:
            if self.kdf_methods_path.is_dir():
                v2_file = self.kdf_methods_path / "kdf_methods_v2.json"
                legacy_file = self.kdf_methods_path / "kdf_methods_legacy.json"
                # Split by original source; default to v2 if unknown
                v2_methods: Dict[str, Any] = {}
                legacy_methods: Dict[str, Any] = {}
                for name, data in updated_methods.items():
                    src = self._method_source.get(name)
                    if src and src == legacy_file:
                        legacy_methods[name] = data
                    else:
                        v2_methods[name] = data
                # Backups
                if legacy_file.exists():
                    with open(legacy_file.with_suffix('.json.backup'), 'w') as f:
                        json.dump(self._read_json_safe(legacy_file), f, indent=2)
                    logger.info(f"Created backup at {legacy_file.with_suffix('.json.backup')}")
                if v2_file.exists():
                    with open(v2_file.with_suffix('.json.backup'), 'w') as f:
                        json.dump(self._read_json_safe(v2_file), f, indent=2)
                    logger.info(f"Created backup at {v2_file.with_suffix('.json.backup')}")
                # Save
                with open(legacy_file, 'w') as f:
                    json.dump(legacy_methods, f, indent=2)
                logger.info(f"Updated KDF methods file: {legacy_file}")
                with open(v2_file, 'w') as f:
                    json.dump(v2_methods, f, indent=2)
                logger.info(f"Updated KDF methods file: {v2_file}")
                # Update internal data
                self.kdf_methods = {**legacy_methods, **v2_methods}
            else:
                # Single file mode (backward compatibility)
                backup_path = self.kdf_methods_path.with_suffix('.json.backup')
                with open(backup_path, 'w') as f:
                    json.dump(self.kdf_methods, f, indent=2)
                logger.info(f"Created backup at {backup_path}")
                with open(self.kdf_methods_path, 'w') as f:
                    json.dump(updated_methods, f, indent=2)
                logger.info(f"Updated KDF methods file: {self.kdf_methods_path}")
                self.kdf_methods = updated_methods
        except Exception as e:
            logger.error(f"Error saving updated methods: {e}")
            raise

    def _read_json_safe(self, file_path: Path) -> Dict[str, Any]:
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    
    def get_tag_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about current and derived tags.
        
        Returns:
            Dictionary with tag statistics
        """
        current_tags = {}
        derived_tags_stats = {}
        
        # Count current tags
        for method_name, method_data in self.kdf_methods.items():
            tags = method_data.get("tags", [])
            for tag in tags:
                current_tags[tag] = current_tags.get(tag, 0) + 1
        
        # Count derived tags
        derived_tags = self.derive_tags_for_all_methods()
        for method_name, tags in derived_tags.items():
            for tag in tags:
                derived_tags_stats[tag] = derived_tags_stats.get(tag, 0) + 1
        
        return {
            "total_methods": len(self.kdf_methods),
            "current_tags": dict(sorted(current_tags.items())),
            "derived_tags": dict(sorted(derived_tags_stats.items())),
            "total_current_tags": len(current_tags),
            "total_derived_tags": len(derived_tags_stats)
        }
    
    def preview_tag_changes(self, method_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Preview what tag changes would be made without applying them.
        
        Args:
            method_name: Optional specific method to preview, or None for all methods
            
        Returns:
            Dictionary with preview information
        """
        if method_name:
            if method_name not in self.kdf_methods:
                raise ValueError(f"Method '{method_name}' not found")
            
            method_data = self.kdf_methods[method_name]
            current_tags = set(method_data.get("tags", []))
            derived_tags = self.derive_tags_for_method(method_name, method_data)
            
            return {
                "method": method_name,
                "current_tags": sorted(list(current_tags)),
                "derived_tags": sorted(list(derived_tags)),
                "would_add": sorted(list(derived_tags - current_tags)),
                "final_tags": sorted(list(current_tags.union(derived_tags)))
            }
        else:
            # Preview all methods
            changes = self.apply_derived_tags(dry_run=True)
            return changes


def main():
    """Example usage of the TagManager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage KDF method tags")
    parser.add_argument("--kdf-methods", required=True, help="Path to kdf_methods.json")
    parser.add_argument("--requests-base", required=True, help="Path to requests base directory")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry run)")
    parser.add_argument("--method", help="Preview changes for specific method")
    parser.add_argument("--stats", action="store_true", help="Show tag statistics")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.INFO if args.verbose else logging.DEBUG
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    
    # Initialize TagManager
    tag_manager = TagManager(args.kdf_methods, args.requests_base)
    
    if args.stats:
        stats = tag_manager.get_tag_statistics()
        print(json.dumps(stats, indent=2))
    elif args.method:
        preview = tag_manager.preview_tag_changes(args.method)
        print(json.dumps(preview, indent=2))
    else:
        changes = tag_manager.apply_derived_tags(dry_run=not args.apply)
        print(json.dumps(changes, indent=2))


if __name__ == "__main__":
    main()
