#!/usr/bin/env python3
"""
KDF Methods Metadata Validator - Ensures kdf_methods.json has proper tags and prerequisites.

This script validates and automatically fixes kdf_methods.json to ensure all methods have:
- 'tags' list field with correct version-specific tags (v2/legacy) and deprecation status
- 'prerequisites' list field (initially empty)

Request files should contain only the request body data.
This can be run standalone or integrated into other validation workflows.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add lib path for utilities
sys.path.append(str(Path(__file__).parent / "lib"))
from utils.json_utils import dump_sorted_json


class KdfMethodsMetadataValidator:
    """Validator for kdf_methods.json metadata fields (tags and prerequisites)."""
    
    def __init__(self, workspace_root: Path = None):
        """Initialize the validator."""
        self.workspace_root = workspace_root or Path(__file__).parent.parent.parent
        self.kdf_methods_file = self.workspace_root / "src/data/kdf_methods.json"
        self.kdf_methods = self._load_kdf_methods()
        self.fixes_applied = []
        self.errors = []
        self.warnings = []
    
    def _load_kdf_methods(self) -> Dict[str, Any]:
        """Load KDF methods configuration."""
        try:
            if self.kdf_methods_file.exists():
                with open(self.kdf_methods_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                self.warnings.append(f"KDF methods file not found: {self.kdf_methods_file}")
                return {}
        except Exception as e:
            self.errors.append(f"Error loading KDF methods: {e}")
            return {}
    
    def _determine_version_from_examples(self, examples: Dict[str, str]) -> str:
        """Determine version based on example naming patterns."""
        if not examples:
            return "v2"  # Default to v2
        
        # Check if method has v2 or legacy examples by looking at example names
        has_v2_examples = any(not key.startswith("Legacy") for key in examples.keys())
        has_legacy_examples = any(key.startswith("Legacy") for key in examples.keys())
        
        # Prefer v2 if both exist
        if has_v2_examples:
            return "v2"
        elif has_legacy_examples:
            return "legacy"
        else:
            return "v2"  # Default

    def _determine_tags(self, method_name: str, method_config: Dict[str, Any]) -> List[str]:
        """Determine the correct tags for a method."""
        tags = []
        
        # Determine version from examples
        examples = method_config.get("examples", {})
        version = self._determine_version_from_examples(examples)
        tags.append(version)
        
        # Check if method is deprecated
        if method_config.get("deprecated", False):
            tags.append("deprecated")
        
        return sorted(tags)  # Sort alphabetically
    
    def validate_and_fix_kdf_methods(self) -> bool:
        """Validate and fix kdf_methods.json metadata. Returns True if modified."""
        if not self.kdf_methods:
            self.errors.append("No KDF methods loaded")
            return False
        
        methods_modified = False
        
        for method_name, method_config in self.kdf_methods.items():
            if not isinstance(method_config, dict):
                self.errors.append(f"Method '{method_name}' configuration must be a JSON object")
                continue
            
            method_modified = False
            
            # Validate tags field
            expected_tags = self._determine_tags(method_name, method_config)
            
            if "tags" not in method_config:
                method_config["tags"] = expected_tags
                method_modified = True
                self.fixes_applied.append(f"Added tags {expected_tags} to method {method_name}")
            elif not isinstance(method_config["tags"], list):
                self.errors.append(f"Method '{method_name}' tags field must be a list")
            else:
                current_tags = sorted(method_config["tags"])
                if current_tags != expected_tags:
                    method_config["tags"] = expected_tags
                    method_modified = True
                    self.fixes_applied.append(f"Updated tags from {current_tags} to {expected_tags} for method {method_name}")
            
            # Validate prerequisites field
            if "prerequisites" not in method_config:
                method_config["prerequisites"] = []
                method_modified = True
                self.fixes_applied.append(f"Added empty prerequisites to method {method_name}")
            elif not isinstance(method_config["prerequisites"], list):
                self.errors.append(f"Method '{method_name}' prerequisites field must be a list")
            
            if method_modified:
                methods_modified = True
        
        # Save the file if it was modified
        if methods_modified:
            dump_sorted_json(self.kdf_methods, self.kdf_methods_file)
            print(f"✅ Fixed {self.kdf_methods_file}")
        
        return methods_modified
    
    def validate_kdf_methods_metadata(self) -> Dict[str, Any]:
        """Validate kdf_methods.json metadata and return summary."""
        methods_modified = self.validate_and_fix_kdf_methods()
        return self._create_summary(methods_modified)
    
    def _create_summary(self, methods_modified: bool = False) -> Dict[str, Any]:
        """Create validation summary."""
        return {
            "methods_count": len(self.kdf_methods),
            "methods_modified": methods_modified,
            "fixes_applied": self.fixes_applied,
            "fix_count": len(self.fixes_applied),
            "errors": self.errors,
            "error_count": len(self.errors),
            "warnings": self.warnings,
            "warning_count": len(self.warnings),
            "success": len(self.errors) == 0
        }


def validate_kdf_methods_metadata(workspace_root: Path = None, silent: bool = False) -> Dict[str, Any]:
    """
    Validate KDF methods metadata (for integration with other scripts).
    
    Args:
        workspace_root: Path to workspace root (defaults to auto-detect)
        silent: If True, don't print progress messages
        
    Returns:
        Dictionary with validation summary
    """
    validator = KdfMethodsMetadataValidator(workspace_root)
    summary = validator.validate_kdf_methods_metadata()
    
    if not silent and summary['methods_modified']:
        print(f"✅ KDF methods metadata validation: applied {summary['fix_count']} fixes")
    
    return summary

# Keep old function name for backwards compatibility
def validate_request_metadata(workspace_root: Path = None, silent: bool = False) -> Dict[str, Any]:
    """Backwards compatibility wrapper."""
    return validate_kdf_methods_metadata(workspace_root, silent)


def main():
    """Main function for standalone execution."""
    print("🔍 Validating KDF methods metadata (tags and prerequisites)...")
    
    validator = KdfMethodsMetadataValidator()
    summary = validator.validate_kdf_methods_metadata()
    
    print(f"\n📊 Validation Summary:")
    print(f"   Methods processed: {summary['methods_count']}")
    print(f"   Methods modified: {summary['methods_modified']}")
    print(f"   Fixes applied: {summary['fix_count']}")
    print(f"   Errors: {summary['error_count']}")
    print(f"   Warnings: {summary['warning_count']}")
    
    if summary['fixes_applied']:
        print(f"\n✅ Applied fixes:")
        for fix in summary['fixes_applied']:
            print(f"   - {fix}")
    
    if summary['errors']:
        print(f"\n❌ Errors:")
        for error in summary['errors']:
            print(f"   - {error}")
    
    if summary['warnings']:
        print(f"\n⚠️  Warnings:")
        for warning in summary['warnings']:
            print(f"   - {warning}")
    
    if summary['success']:
        if summary['methods_modified']:
            print(f"\n🎉 Successfully validated and fixed KDF methods metadata!")
        else:
            print(f"\n✨ All KDF methods metadata is already properly validated!")
    else:
        print(f"\n💥 Validation completed with {summary['error_count']} errors.")
        sys.exit(1)


if __name__ == "__main__":
    main()
