#!/usr/bin/env python3
"""
Documentation Helper for KDF Tools CLI

This module provides utilities for generating, validating, and enforcing docstring and usage documentation standards across CLI modules.
"""

import ast
from pathlib import Path
from typing import List, Dict, Any, Optional

class DocHelper:
    """Utilities for documentation generation and validation."""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def extract_docstrings(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract all docstrings from a Python file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        docstrings = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                doc = ast.get_docstring(node)
                if doc:
                    docstrings.append({
                        'name': getattr(node, 'name', '<module>'),
                        'type': type(node).__name__,
                        'docstring': doc
                    })
        return docstrings
    
    def validate_docstrings(self, file_path: Path) -> List[str]:
        """Validate that all public classes and functions have docstrings."""
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        missing = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not node.name.startswith('_') and not ast.get_docstring(node):
                    missing.append(f"Missing docstring: {type(node).__name__} '{node.name}' in {file_path}")
        return missing
    
    def generate_usage_example(self, class_or_func: Any) -> str:
        """Generate a usage example for a class or function."""
        name = class_or_func.__name__
        if callable(class_or_func):
            return f"# Usage example for {name}\n{name}()"
        return f"# Usage example for {name} (not callable)"
    
    def check_module_docstring(self, file_path: Path) -> Optional[str]:
        """Check if a module has a top-level docstring."""
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        if not ast.get_docstring(tree):
            return f"Missing module docstring in {file_path}"
        return None
    
    def enforce_docstring_standards(self, file_path: Path) -> List[str]:
        """Enforce docstring standards for a file (module, classes, functions)."""
        issues = []
        module_issue = self.check_module_docstring(file_path)
        if module_issue:
            issues.append(module_issue)
        issues.extend(self.validate_docstrings(file_path))
        return issues
    
    def auto_generate_missing_docstrings(self, file_path: Path) -> None:
        """Auto-generate placeholder docstrings for missing ones (in-place)."""
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        tree = ast.parse(''.join(lines))
        inserts = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not node.name.startswith('_') and not ast.get_docstring(node):
                    line_no = node.body[0].lineno - 1 if node.body else node.lineno
                    indent = ' ' * (node.col_offset + 4)
                    docstring = f'{indent}"""TODO: Add docstring for {type(node).__name__} {node.name}"""\n'
                    inserts.append((line_no, docstring))
        # Insert in reverse order to not mess up line numbers
        for line_no, docstring in sorted(inserts, reverse=True):
            lines.insert(line_no, docstring)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        if self.logger:
            self.logger.info(f"Auto-generated {len(inserts)} docstrings in {file_path}") 