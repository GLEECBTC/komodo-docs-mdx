#!/usr/bin/env python3
"""
Table Manager - Centralized table operations for KDF API documentation

This module provides a unified interface for:
- Loading and managing table definitions
- Validating parameter structures against tables
- Tracking missing table references
- Generating table-based documentation
"""

import json
import logging
from pathlib import Path
from typing import Dict, Set, List, Optional, Any, Tuple
from dataclasses import dataclass

# Add lib path for utilities
import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.json_utils import dump_sorted_json


@dataclass
class TableReference:
    """Represents a table reference with type and status."""
    table_name: str
    table_type: str  # 'request', 'response', 'error'
    method_name: str
    exists: bool = False
    is_na: bool = False  # True if table_name is "N/A"
    is_empty: bool = False  # True if table_name is ""


@dataclass  
class ValidationResult:
    """Result of parameter validation against a table."""
    method: str
    table_name: str
    unused_params: Set[str]
    missing_params: Set[str]
    valid_params: Set[str]


class TableManager:
    """Centralized manager for all table-related operations."""
    
    def __init__(self, workspace_root: Optional[Path] = None, logger: Optional[logging.Logger] = None):
        """Initialize the table manager.
        
        Args:
            workspace_root: Path to the workspace root. If None, auto-detects.
            logger: Logger instance. If None, creates a new one.
        """
        if workspace_root is None:
            workspace_root = Path(__file__).parent.parent.parent.parent
        
        self.workspace_root = Path(workspace_root)
        self.tables_dir = self.workspace_root / "src" / "data" / "tables"
        self.logger = logger or logging.getLogger(__name__)
        
        # Cache for loaded tables
        self._tables_cache: Optional[Dict[str, Dict]] = None
        
        # Missing table tracking
        self.missing_tables = {
            "missing_request_tables": [],
            "missing_response_tables": [],
            "missing_error_tables": []
        }
    
    def load_json_file(self, file_path: Path) -> Optional[Dict]:
        """Load JSON file and return its content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"Table file not found: {file_path}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in table file {file_path}: {e}")
            return None
    
    def load_all_tables(self, force_reload: bool = False) -> Dict[str, Dict]:
        """Load all table files and combine them.
        
        Args:
            force_reload: If True, bypass cache and reload from disk.
            
        Returns:
            Dictionary mapping table names to table definitions.
        """
        if not force_reload and self._tables_cache is not None:
            return self._tables_cache
        
        all_tables = {}
        
        # Load common structures
        common_dir = self.tables_dir / "common-structures"
        if common_dir.exists():
            for table_file in common_dir.glob("*.json"):
                tables = self.load_json_file(table_file)
                if tables:
                    all_tables.update(tables)
                    self.logger.info(f"Loaded {len(tables)} tables from {table_file}")
        
        # Load version-specific tables
        for version_dir in ["legacy", "v2"]:
            version_path = self.tables_dir / version_dir
            if version_path.exists():
                for table_file in version_path.glob("*.json"):
                    tables = self.load_json_file(table_file)
                    if tables:
                        all_tables.update(tables)
                        self.logger.info(f"Loaded {len(tables)} tables from {table_file}")
        
        self._tables_cache = all_tables
        self.logger.info(f"Loaded {len(all_tables)} total table definitions")
        
        return all_tables
    
    def get_table_reference(self, method_config: Dict[str, Any], table_type: str) -> TableReference:
        """Get a table reference for a specific method and table type.
        
        Args:
            method_config: Method configuration from kdf_methods.json
            table_type: Type of table ('request', 'response', 'error')
            
        Returns:
            TableReference object with metadata about the table reference.
        """
        # Map table types to field names
        field_mapping = {
            'request': 'request_table',
            'response': 'response_table', 
            'error': 'errors_table'
        }
        
        field_name = field_mapping.get(table_type)
        if not field_name:
            raise ValueError(f"Invalid table type: {table_type}")
        
        # Get table name from method config (with fallback for old 'table' field)
        table_name = method_config.get(field_name)
        if not table_name and table_type == 'request':
            # Fallback to old 'table' field for backward compatibility
            table_name = method_config.get('table', '')
        
        if not table_name:
            table_name = ''
        
        method_name = method_config.get('method_name', 'unknown')
        
        return TableReference(
            table_name=table_name,
            table_type=table_type,
            method_name=method_name,
            exists=False,  # Will be set by check_table_exists
            is_na=(table_name == "N/A"),
            is_empty=(table_name == "")
        )
    
    def check_table_exists(self, table_ref: TableReference) -> TableReference:
        """Check if a table reference exists in the loaded tables.
        
        Args:
            table_ref: TableReference to check
            
        Returns:
            Updated TableReference with exists field set correctly.
        """
        if table_ref.is_na or table_ref.is_empty:
            table_ref.exists = False
            return table_ref
        
        tables = self.load_all_tables()
        table_ref.exists = table_ref.table_name in tables
        
        return table_ref
    
    def track_missing_table(self, method_name: str, table_type: str) -> None:
        """Track a missing table by type.
        
        Args:
            method_name: Name of the method missing the table
            table_type: Type of table missing ('request', 'response', 'error')
        """
        category_key = f"missing_{table_type}_tables"
        if category_key in self.missing_tables:
            if method_name not in self.missing_tables[category_key]:
                self.missing_tables[category_key].append(method_name)
                self.logger.info(f"Tracked missing {table_type} table for {method_name}")
    
    def validate_method_tables(self, method_name: str, method_config: Dict[str, Any]) -> List[TableReference]:
        """Validate all table references for a method.
        
        Args:
            method_name: Name of the method
            method_config: Method configuration from kdf_methods.json
            
        Returns:
            List of TableReference objects for all table types.
        """
        results = []
        
        # Add method name to config for reference tracking
        method_config = method_config.copy()
        method_config['method_name'] = method_name
        
        # Check all table types
        for table_type in ['request', 'response', 'error']:
            table_ref = self.get_table_reference(method_config, table_type)
            table_ref = self.check_table_exists(table_ref)
            
            # Track missing tables (excluding N/A and deprecated methods)
            if not table_ref.exists and not table_ref.is_na:
                is_deprecated = method_config.get('deprecated', False)
                if not is_deprecated:
                    if table_ref.is_empty:
                        self.track_missing_table(method_name, table_type)
                    elif table_ref.table_name:  # Non-empty, non-N/A but doesn't exist
                        self.track_missing_table(method_name, table_type)
                        self.logger.warning(f"Table {table_ref.table_name} not found for method {method_name}")
            
            results.append(table_ref)
        
        return results
    
    def validate_request_params(self, request_data: Dict, method_name: str, method_config: Dict[str, Any]) -> Optional[ValidationResult]:
        """Validate request parameters against table definitions.
        
        Args:
            request_data: Request data to validate
            method_name: Name of the method
            method_config: Method configuration from kdf_methods.json
            
        Returns:
            ValidationResult object or None if validation cannot be performed.
        """
        # Get request table reference
        table_ref = self.get_table_reference(method_config, 'request')
        table_ref = self.check_table_exists(table_ref)
        
        if not table_ref.exists or table_ref.is_na:
            return None
        
        tables = self.load_all_tables()
        table_data = tables[table_ref.table_name]
        
        # Extract table parameters
        table_params = set()
        for param_def in table_data.get("data", []):
            table_params.add(param_def["parameter"])
        
        # Extract request parameters
        request_params = set()
        params_data = request_data.get("params")
        
        # If explicit params object exists, use it (v2 structure)
        if isinstance(params_data, dict):
            if "activation_params" in params_data:
                # Add top-level params
                for key in params_data.keys():
                    if key != "activation_params":
                        request_params.add(key)
                # Extract nested parameters
                self._extract_param_names(params_data["activation_params"], request_params)
            else:
                self._extract_param_names(params_data, request_params)
        else:
            # Legacy structure: parameters are at the top level of request_data
            # Exclude non-parameter control fields
            excluded_keys = {"method", "userpass"}
            legacy_params: Dict[str, Any] = {}
            for k, v in request_data.items():
                if k not in excluded_keys:
                    legacy_params[k] = v
            self._extract_param_names(legacy_params, request_params)
        
        # Calculate validation results
        unused_params = table_params - request_params
        missing_params = request_params - table_params
        valid_params = table_params & request_params
        
        return ValidationResult(
            method=method_name,
            table_name=table_ref.table_name,
            unused_params=unused_params,
            missing_params=missing_params,
            valid_params=valid_params
        )
    
    def _extract_param_names(self, data: Any, param_names: Set[str], prefix: str = "") -> None:
        """Recursively extract parameter names from nested data structure.
        
        Args:
            data: Data structure to extract from
            param_names: Set to add parameter names to
            prefix: Current parameter path prefix
        """
        if isinstance(data, dict):
            for key, value in data.items():
                param_path = f"{prefix}.{key}" if prefix else key
                param_names.add(param_path)
                
                if isinstance(value, (dict, list)):
                    self._extract_param_names(value, param_names, param_path)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    self._extract_param_names(item, param_names, prefix)
    
    def generate_table_markdown(self, method_name: str, method_config: Dict[str, Any]) -> str:
        """Generate markdown table documentation for a method.
        
        Args:
            method_name: Name of the method
            method_config: Method configuration from kdf_methods.json
            
        Returns:
            Markdown string for the table or empty string if no table available.
        """
        # Skip deprecated methods
        if method_config.get('deprecated', False):
            return ""
        
        # Get request table reference
        table_ref = self.get_table_reference(method_config, 'request')
        table_ref = self.check_table_exists(table_ref)
        
        # Handle cases where no table is needed or available
        if table_ref.is_na:
            return ""  # N/A means no table needed
        
        if table_ref.is_empty:
            self.track_missing_table(method_name, 'request')
            return ""
        
        if not table_ref.exists:
            self.track_missing_table(method_name, 'request')
            return ""
        
        tables = self.load_all_tables()
        table_data = tables[table_ref.table_name].get("data", [])
        
        if not table_data:
            self.track_missing_table(method_name, 'request')
            return ""
        
        # Generate markdown table
        markdown = "## Request Parameters\n\n"
        markdown += "| Parameter | Type | Description |\n"
        markdown += "|-----------|------|-------------|\n"
        
        for param in table_data:
            parameter = param.get("parameter", "")
            param_type = param.get("type", "")
            required = param.get("required", False)
            default = param.get("default", "")
            description = param.get("description", "")
            
            # Build the type column with required/default info
            type_column = param_type
            if required and default:
                type_column += f" (required. Default: `{default}`)"
            elif required:
                type_column += " (required)"
            elif default:
                type_column += f" (Default: `{default}`)"
            
            # Escape markdown characters
            description = description.replace("|", "\\|").replace("\n", " ")
            
            markdown += f"| `{parameter}` | {type_column} | {description} |\n"
        
        return markdown
    
    def get_missing_tables_report(self) -> Dict[str, List[str]]:
        """Get the current missing tables report.
        
        Returns:
            Dictionary with missing table categories and methods.
        """
        # Sort all missing table lists
        sorted_missing_tables = {}
        for table_type, methods in self.missing_tables.items():
            sorted_missing_tables[table_type] = sorted(methods) if methods else []
        
        return sorted_missing_tables
    
    def save_missing_tables_report(self, output_file: Path) -> None:
        """Save the missing tables report to a file.
        
        Args:
            output_file: Path to save the report to
        """
        report = self.get_missing_tables_report()
        dump_sorted_json(report, output_file)
        self.logger.info(f"Missing tables report saved to {output_file}")
    
    def clear_missing_tables(self) -> None:
        """Clear the missing tables tracking."""
        for table_type in self.missing_tables:
            self.missing_tables[table_type].clear()
    
    def get_table_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded tables.
        
        Returns:
            Dictionary with table statistics.
        """
        tables = self.load_all_tables()
        
        stats = {
            "total_tables": len(tables),
            "tables_by_category": {},
            "tables_with_data": 0,
            "empty_tables": 0,
            "total_parameters": 0
        }
        
        # Categorize tables and count parameters
        for table_name, table_data in tables.items():
            # Categorize by naming pattern
            if "Arguments" in table_name:
                category = "arguments"
            elif "Response" in table_name:
                category = "responses"
            elif "Error" in table_name:
                category = "errors"
            else:
                category = "other"
            
            stats["tables_by_category"][category] = stats["tables_by_category"].get(category, 0) + 1
            
            # Count parameters
            data = table_data.get("data", [])
            if data:
                stats["tables_with_data"] += 1
                stats["total_parameters"] += len(data)
            else:
                stats["empty_tables"] += 1
        
        return stats
