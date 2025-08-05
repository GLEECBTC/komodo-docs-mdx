#!/usr/bin/env python3
"""
Validation Manager

Centralized validation functionality for the Komodo Documentation Library.
Provides a simplified facade for accessing various validation tools.
"""

from pathlib import Path
from typing import Dict, List, Any, Union, Callable, Optional

from ..constants.enums import ValidationLevel
from ..validation import (
    ValidationResult,
    JSONValidator,
    MethodNameValidator,
    FileFormatValidator,
)


class ValidationManager:
    """
    Acts as a facade for the validation subsystem.
    
    Initializes and provides access to specialized validator classes.
    """
    
    def __init__(self, level: ValidationLevel = ValidationLevel.NORMAL):
        self.level = level
        self.json_validator = JSONValidator(level)
        self.method_name_validator = MethodNameValidator(level)
        self.file_format_validator = FileFormatValidator(level)

    def validate_json(self, data: Union[str, Path, Dict], schema: str = None) -> ValidationResult:
        """Validate JSON data using JSONValidator."""
        if isinstance(data, dict):
            # The validator expects a string, so we dump it.
            import json
            data = json.dumps(data)
        return self.json_validator.validate_json_string(data, schema)

    def validate_method_name(self, method_name: str) -> ValidationResult:
        """Validate a KDF method name."""
        return self.method_name_validator.validate_method_name(method_name)

    def validate_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """Validate a file based on its extension."""
        path = Path(file_path)
        if not path.exists():
            return ValidationResult(is_valid=False, errors=[f"File not found: {path}"], warnings=[])
            
        if path.suffix == ".mdx":
            return self.file_format_validator.validate_mdx_file(path)
        elif path.suffix in [".yaml"]:
            return self.file_format_validator.validate_yaml_file(path)
        else:
            return ValidationResult(is_valid=True, errors=[], warnings=[f"No validator for file type: {path.suffix}"])

    def validate_batch(self, items: List[Any], validator_func: Callable) -> Dict[str, ValidationResult]:
        """
        Run batch validation using a specified validator function.
        
        Example:
            validate_batch(list_of_methods, self.validate_method_name)
        """
        results = {}
        for item in items:
            results[str(item)] = validator_func(item)
        return results

    def get_validation_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Generate a summary from a dictionary of validation results."""
        summary = {
            'total_items': len(results),
            'valid_items': 0,
            'invalid_items': 0,
            'items_with_warnings': 0,
            'errors': [],
            'warnings': []
        }
        
        for item, result in results.items():
            if result.is_valid:
                summary['valid_items'] += 1
            else:
                summary['invalid_items'] += 1
                for error in result.errors:
                    summary['errors'].append(f"[{item}] {error}")
            
            if result.warnings:
                summary['items_with_warnings'] += 1
                for warning in result.warnings:
                    summary['warnings'].append(f"[{item}] {warning}")

        return summary
        
    def analyze_mdx_codegroup_status(self, root_dir: Union[str, Path] = None) -> ValidationResult:
        """
        Analyze MDX files for missing <CodeGroup> tags after a method heading.
        
        Args:
            root_dir: The directory to scan. Defaults to a configured path.
        """
        if root_dir is None:
            # Logic to get a default path, assuming a config system exists
            # For example: from ..constants import get_config; root_dir = get_config().get('docs_path')
            # As a fallback, using a relative path.
            root_dir = Path("./docs")

        return self.file_format_validator.find_mdx_files_missing_codegroup(root_dir)

    def print_codegroup_analysis(self, root_dir: Union[str, Path] = None):
        """
        Runs the CodeGroup analysis and prints a formatted report.
        """
        result = self.analyze_mdx_codegroup_status(root_dir)
        self.file_format_validator.print_codegroup_analysis_report(result)


# Optional: Helper functions for direct, simple access
def validate_json_safe(data: Any, schema: str = None, level: ValidationLevel = ValidationLevel.NORMAL) -> bool:
    """Quickly check if JSON is valid. Returns a boolean."""
    manager = ValidationManager(level)
    return manager.validate_json(data, schema).is_valid

def validate_method_name_safe(method_name: str, level: ValidationLevel = ValidationLevel.NORMAL) -> bool:
    """Quickly check if a method name is valid. Returns a boolean."""
    manager = ValidationManager(level)
    return manager.validate_method_name(method_name).is_valid

def get_validation_manager(level: ValidationLevel = ValidationLevel.NORMAL) -> 'ValidationManager':
    """Factory function to get an instance of the ValidationManager."""
    return ValidationManager(level) 