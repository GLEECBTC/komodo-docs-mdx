#!/usr/bin/env python3
"""
Code Cleaner for KDF Tools CLI

This module contains functionality for identifying and cleaning up unused code and dead code
separated from the main CLI class to improve maintainability.
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
import importlib.util


class CodeCleaner:
    """Identifies and cleans up unused code and dead code."""
    
    def __init__(self, logger):
        self.logger = logger
        
    def find_unused_imports(self, file_path: Path) -> List[str]:
        """
        Find unused imports in a Python file.
        
        Args:
            file_path: Path to the Python file to analyze
            
        Returns:
            List[str]: List of unused import statements
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            analyzer = ImportAnalyzer()
            analyzer.visit(tree)
            
            return analyzer.get_unused_imports()
        except Exception as e:
            self.logger.error(f"Error analyzing imports in {file_path}: {e}")
            return []
            
    def find_dead_code(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Find dead code in a Python file.
        
        Args:
            file_path: Path to the Python file to analyze
            
        Returns:
            List[Dict[str, Any]]: List of dead code locations with details
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            analyzer = DeadCodeAnalyzer()
            analyzer.visit(tree)
            
            return analyzer.get_dead_code()
        except Exception as e:
            self.logger.error(f"Error analyzing dead code in {file_path}: {e}")
            return []
            
    def find_placeholder_methods(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Find placeholder methods that need implementation.
        
        Args:
            file_path: Path to the Python file to analyze
            
        Returns:
            List[Dict[str, Any]]: List of placeholder methods with details
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            analyzer = PlaceholderAnalyzer()
            analyzer.visit(tree)
            
            return analyzer.get_placeholder_methods()
        except Exception as e:
            self.logger.error(f"Error analyzing placeholder methods in {file_path}: {e}")
            return []
            
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a Python file.
        
        Args:
            file_path: Path to the Python file to analyze
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        return {
            "file_path": str(file_path),
            "unused_imports": self.find_unused_imports(file_path),
            "dead_code": self.find_dead_code(file_path),
            "placeholder_methods": self.find_placeholder_methods(file_path),
        }
        
    def analyze_directory(self, directory_path: Path) -> Dict[str, Any]:
        """
        Analyze all Python files in a directory.
        
        Args:
            directory_path: Path to the directory to analyze
            
        Returns:
            Dict[str, Any]: Analysis results for all files
        """
        results = {
            "directory": str(directory_path),
            "files": [],
            "summary": {
                "total_files": 0,
                "total_unused_imports": 0,
                "total_dead_code": 0,
                "total_placeholder_methods": 0,
            }
        }
        
        for file_path in directory_path.rglob("*.py"):
            if file_path.is_file():
                file_analysis = self.analyze_file(file_path)
                results["files"].append(file_analysis)
                
                results["summary"]["total_files"] += 1
                results["summary"]["total_unused_imports"] += len(file_analysis["unused_imports"])
                results["summary"]["total_dead_code"] += len(file_analysis["dead_code"])
                results["summary"]["total_placeholder_methods"] += len(file_analysis["placeholder_methods"])
                
        return results
        
    def generate_cleanup_report(self, analysis_results: Dict[str, Any]) -> str:
        """
        Generate a human-readable cleanup report.
        
        Args:
            analysis_results: Results from analyze_directory()
            
        Returns:
            str: Formatted cleanup report
        """
        report = []
        report.append("# Code Cleanup Report")
        report.append("")
        
        summary = analysis_results["summary"]
        report.append(f"## Summary")
        report.append(f"- Total files analyzed: {summary['total_files']}")
        report.append(f"- Total unused imports: {summary['total_unused_imports']}")
        report.append(f"- Total dead code locations: {summary['total_dead_code']}")
        report.append(f"- Total placeholder methods: {summary['total_placeholder_methods']}")
        report.append("")
        
        for file_analysis in analysis_results["files"]:
            if (file_analysis["unused_imports"] or 
                file_analysis["dead_code"] or 
                file_analysis["placeholder_methods"]):
                
                report.append(f"## {file_analysis['file_path']}")
                
                if file_analysis["unused_imports"]:
                    report.append("### Unused Imports")
                    for import_stmt in file_analysis["unused_imports"]:
                        report.append(f"- `{import_stmt}`")
                    report.append("")
                    
                if file_analysis["dead_code"]:
                    report.append("### Dead Code")
                    for dead_code in file_analysis["dead_code"]:
                        report.append(f"- Line {dead_code['line']}: {dead_code['description']}")
                    report.append("")
                    
                if file_analysis["placeholder_methods"]:
                    report.append("### Placeholder Methods")
                    for placeholder in file_analysis["placeholder_methods"]:
                        report.append(f"- Line {placeholder['line']}: `{placeholder['name']}` - {placeholder['description']}")
                    report.append("")
                    
        return "\n".join(report)


class ImportAnalyzer(ast.NodeVisitor):
    """AST visitor for analyzing import usage."""
    
    def __init__(self):
        self.imports = set()
        self.used_names = set()
        
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                if alias.name == '*':
                    self.imports.add(f"{node.module}.*")
                else:
                    self.imports.add(f"{node.module}.{alias.name}")
        self.generic_visit(node)
        
    def visit_Name(self, node):
        self.used_names.add(node.id)
        self.generic_visit(node)
        
    def get_unused_imports(self) -> List[str]:
        """Get list of unused imports."""
        return list(self.imports - self.used_names)


class DeadCodeAnalyzer(ast.NodeVisitor):
    """AST visitor for analyzing dead code."""
    
    def __init__(self):
        self.dead_code = []
        
    def visit_FunctionDef(self, node):
        # Check for empty functions or functions with only pass/return
        if (len(node.body) == 1 and 
            isinstance(node.body[0], (ast.Pass, ast.Return))):
            self.dead_code.append({
                "line": node.lineno,
                "type": "empty_function",
                "name": node.name,
                "description": f"Empty function '{node.name}'"
            })
        self.generic_visit(node)
        
    def visit_ClassDef(self, node):
        # Check for empty classes
        if not node.body:
            self.dead_code.append({
                "line": node.lineno,
                "type": "empty_class",
                "name": node.name,
                "description": f"Empty class '{node.name}'"
            })
        self.generic_visit(node)
        
    def get_dead_code(self) -> List[Dict[str, Any]]:
        """Get list of dead code locations."""
        return self.dead_code


class PlaceholderAnalyzer(ast.NodeVisitor):
    """AST visitor for analyzing placeholder methods."""
    
    def __init__(self):
        self.placeholder_methods = []
        
    def visit_FunctionDef(self, node):
        # Check for placeholder methods (empty or with pass)
        if (len(node.body) == 1 and 
            isinstance(node.body[0], ast.Pass)):
            self.placeholder_methods.append({
                "line": node.lineno,
                "name": node.name,
                "type": "placeholder_method",
                "description": f"Placeholder method '{node.name}' needs implementation"
            })
        self.generic_visit(node)
        
    def get_placeholder_methods(self) -> List[Dict[str, Any]]:
        """Get list of placeholder methods."""
        return self.placeholder_methods 