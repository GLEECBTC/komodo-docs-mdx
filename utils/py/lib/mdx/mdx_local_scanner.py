#!/usr/bin/env python3
"""
Existing Documentation Scanner

Comprehensive scanner for existing KDF method documentation to build pattern awareness.
This analyzes all existing method docs to understand actual parameter patterns.
"""

import asyncio
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import asdict

from .mdx_scanner import UnifiedScanner
from ..utils.logging_utils import get_logger
from ..utils import safe_write_json, ensure_directory_exists
from ..constants import UnifiedParameterInfo, MethodPattern
from ..async_support import AsyncFileProcessor


class ExistingDocsScanner:
    """Scans existing KDF documentation to extract method patterns."""
    
    def __init__(self, docs_base_path: Optional[Path] = None, verbose: bool = True):
        self.logger = get_logger("existing-docs-scanner")
        self.verbose = verbose
        
        # Set up paths
        if docs_base_path:
            self.docs_base_path = Path(docs_base_path)
        else:
            # Default to workspace src/pages path
            script_dir = Path(__file__).parent.parent.parent
            workspace_root = script_dir.parent.parent
            self.docs_base_path = workspace_root / "src" / "pages" / "komodo-defi-framework" / "api"
        
        self.patterns: Dict[str, MethodPattern] = {}
        self.file_processor = AsyncFileProcessor()
        
        if self.verbose:
            self.logger.info(f"📁 Docs base path: {self.docs_base_path}")
    
    def scan_and_extract_patterns(self) -> Dict[str, MethodPattern]:
        """
        Synchronously scans for MDX files and extracts detailed patterns from them.
        """
        if self.verbose:
            self.logger.info("🔍 Synchronously scanning and extracting KDF method patterns...")
        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If we're already in an event loop, create a task
            task = loop.create_task(self.scan_and_extract_patterns_async())
            # This is a bit tricky in a general sync method.
            # For simplicity, we'll just run a new loop if needed.
            self.patterns = asyncio.run(self.scan_and_extract_patterns_async())
        else:
            self.patterns = asyncio.run(self.scan_and_extract_patterns_async())

        return self.patterns
    
    async def scan_and_extract_patterns_async(self) -> Dict[str, MethodPattern]:
        """
        Asynchronously scans for MDX files using UnifiedScanner and extracts detailed patterns from them.
        """
        if self.verbose:
            self.logger.info("🔍 Asynchronously scanning and extracting KDF method patterns...")

        # 1. Use UnifiedScanner to find all MDX files
        unified_scanner = UnifiedScanner(verbose=self.verbose)
        # We need to map file path to version. The current UnifiedScanner returns method -> path.
        scanned_files_by_version = await unified_scanner.scan_mdx_files_async(flatten_results=False)

        total_files = sum(len(files) for files in scanned_files_by_version.values())
        if self.verbose:
            self.logger.info(f"✅ Found {total_files} MDX files to analyze.")
            self.logger.info("📄 Extracting method patterns from files...")
        
        # 2. Process these files
        tasks = []
        for version, files_map in scanned_files_by_version.items():
            # The version from UnifiedScanner is like 'mdx_v1', 'mdx_v2', etc.
            # We want the 'v1', 'v2' part
            clean_version = version.replace('mdx_', '').replace('_dev', '-dev')
            for file_path_str in files_map.values():
                task = self._process_mdx_file(Path(file_path_str), clean_version)
                tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        for pattern in results:
            if pattern:
                self.patterns[pattern.method_name] = pattern

        if self.verbose:
            self.logger.info(f"✅ Extracted patterns for {len(self.patterns)} methods.")
        
        return self.patterns
    
    async def _process_mdx_file(self, mdx_file: Path, version: str) -> Optional[MethodPattern]:
        """Asynchronously reads and parses a single MDX file."""
        try:
            content = await self.file_processor.read_file_async(mdx_file)
            pattern = self._extract_method_pattern_from_content(content, mdx_file, version)
            if pattern and self.verbose:
                self.logger.debug(f"  📄 {pattern.method_name} ({version}) in {mdx_file.name}")
            return pattern
        except Exception as e:
            if self.verbose:
                self.logger.warning(f"  ⚠️  Error scanning {mdx_file}: {e}")
            return None
    
    def _extract_method_pattern_from_content(self, content: str, mdx_file: Path, version: str) -> Optional[MethodPattern]:
        """Extract method pattern from MDX file content."""
        try:
            # Extract method name from ## heading with label
            method_match = re.search(r'## ([a-zA-Z0-9_:]+).*\{\{.*label\s*:\s*[\'"]([^\'"]+)[\'"]', content)
            if not method_match:
                # Fallback to simple ## heading
                method_match = re.search(r'^## ([a-zA-Z0-9_:]+)', content, re.MULTILINE)
                if not method_match:
                    return None
            
            method_name = method_match.group(2) if len(method_match.groups()) > 1 else method_match.group(1)
            
            # Extract request parameters
            parameters = self._extract_parameters_table(content, "### Request Parameters")
            
            # Extract response parameters  
            response_parameters = self._extract_parameters_table(content, "### Response Parameters")
            
            # Extract error types
            error_types = self._extract_error_types(content)
            
            return MethodPattern(
                method_name=method_name,
                version=version,
                parameters=parameters,
                response_parameters=response_parameters,
                error_types=error_types,
                file_path=str(mdx_file)
            )
            
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Error extracting pattern from {mdx_file}: {e}")
            return None
    
    def _extract_parameters_table(self, content: str, section_header: str) -> List[UnifiedParameterInfo]:
        """Extract parameters from a table section."""
        parameters = []
        
        # Find the section
        section_match = re.search(rf'{re.escape(section_header)}.*?\n(.*?)(?=\n###|\n##|\nℹ️|\n<|\Z)', 
                                content, re.DOTALL)
        if not section_match:
            return parameters
        
        section_content = section_match.group(1)
        
        # Extract table rows - handle both 4 and 5 column formats
        table_rows = re.findall(r'\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]*)\|([^|]*)\|?', section_content)
        
        for row in table_rows:
            if len(row) >= 3 and not row[0].strip().startswith('-'):  # Skip header separator
                param_name = row[0].strip()
                param_type = row[1].strip()
                required_str = row[2].strip()
                
                # Skip header row
                if param_name.lower() == 'parameter':
                    continue
                
                required = '✓' in required_str or 'true' in required_str.lower()
                
                default = None
                description = ""
                
                if len(row) >= 4:
                    # Could be default or description depending on table format
                    col4 = row[3].strip()
                    if len(row) >= 5:
                        # 5-column format: Parameter | Type | Required | Default | Description
                        default_str = col4
                        if default_str and default_str != '-':
                            default = default_str.strip('`')
                        description = row[4].strip()
                    else:
                        # 4-column format: Parameter | Type | Required | Description
                        description = col4
                
                parameters.append(UnifiedParameterInfo(
                    name=param_name,
                    type=param_type,
                    required=required,
                    default_value=default,
                    description=description
                ))
        
        return parameters
    
    def _extract_error_types(self, content: str) -> List[str]:
        """Extract error types from the Error Types section."""
        error_types = []
        
        section_match = re.search(r'### Error Types.*?\n(.*?)(?=\n###|\n##|\n<|\Z)', 
                                content, re.DOTALL)
        if not section_match:
            return error_types
        
        section_content = section_match.group(1)
        
        # Extract error type names from table
        error_rows = re.findall(r'\|([^|]+)\|[^|]+\|[^|]+\|', section_content)
        
        for row in error_rows:
            error_name = row.strip()
            if error_name and error_name.lower() != 'parameter':
                error_types.append(error_name)
        
        return error_types
    
    def analyze_patterns(self) -> Dict[str, Any]:
        """Analyze the discovered patterns to identify commonalities."""
        analysis = {
            "total_methods": len(self.patterns),
            "method_categories": {},
            "common_parameters": {},
            "common_error_types": {},
            "parameter_patterns": {},
            "version_distribution": {}
        }
        
        # Categorize methods
        for method_name, pattern in self.patterns.items():
            category = self._categorize_method(method_name)
            if category not in analysis["method_categories"]:
                analysis["method_categories"][category] = []
            analysis["method_categories"][category].append(method_name)
        
        # Version distribution
        for pattern in self.patterns.values():
            version = pattern.version
            analysis["version_distribution"][version] = analysis["version_distribution"].get(version, 0) + 1
        
        # Find common parameters
        param_counts = {}
        for pattern in self.patterns.values():
            for param in pattern.parameters:
                key = f"{param.name}:{param.type}"
                param_counts[key] = param_counts.get(key, 0) + 1
        
        analysis["common_parameters"] = {
            k: v for k, v in param_counts.items() 
            if v >= 3  # Appears in 3+ methods
        }
        
        # Find common error types
        error_counts = {}
        for pattern in self.patterns.values():
            for error in pattern.error_types:
                error_counts[error] = error_counts.get(error, 0) + 1
        
        analysis["common_error_types"] = {
            k: v for k, v in error_counts.items()
            if v >= 3  # Appears in 3+ methods
        }
        
        return analysis
    
    def _categorize_method(self, method_name: str) -> str:
        """Categorize a method based on its name."""
        if method_name.startswith("task::"):
            parts = method_name.split("::")
            if len(parts) >= 3:
                return f"task::{parts[1]}"
            return "task"
        elif method_name.startswith("lightning::"):
            parts = method_name.split("::")
            if len(parts) >= 3:
                return f"lightning::{parts[1]}"
            return "lightning"
        elif method_name.startswith("stream::"):
            return "streaming"
        elif method_name.startswith("gui_storage::"):
            return "gui_storage"
        elif method_name.startswith("experimental::"):
            return "experimental"
        else:
            return "other"
    
    async def save_patterns_async(self, output_file: Optional[Path] = None) -> Path:
        """Asynchronously save the discovered patterns to a JSON file."""
        if output_file is None:
            # Default output path
            script_dir = Path(__file__).parent.parent.parent
            data_dir = script_dir / "data"
            output_file = data_dir / "existing_method_patterns.json"
        
        ensure_directory_exists(output_file.parent)
        
        # Convert to serializable format
        serializable_patterns = {}
        for method_name, pattern in self.patterns.items():
            serializable_patterns[method_name] = {
                "method_name": pattern.method_name,
                "version": pattern.version,
                "parameters": [asdict(p) for p in pattern.parameters],
                "response_parameters": [asdict(p) for p in pattern.response_parameters],
                "error_types": pattern.error_types,
                "file_path": pattern.file_path
            }
        
        file_processor = AsyncFileProcessor()
        await file_processor.write_json_async(output_file, serializable_patterns)
        
        if self.verbose:
            self.logger.save(f"Saved {len(self.patterns)} method patterns to {output_file}")
        
        return output_file
    
    def save_patterns(self, output_file: Optional[Path] = None) -> Path:
        """Synchronously save the discovered patterns to a JSON file."""
        if output_file is None:
            # Default output path
            script_dir = Path(__file__).parent.parent.parent
            data_dir = script_dir / "data"
            output_file = data_dir / "existing_method_patterns.json"
        
        ensure_directory_exists(output_file.parent)
        
        # Convert to serializable format
        serializable_patterns = {}
        for method_name, pattern in self.patterns.items():
            serializable_patterns[method_name] = {
                "method_name": pattern.method_name,
                "version": pattern.version,
                "parameters": [asdict(p) for p in pattern.parameters],
                "response_parameters": [asdict(p) for p in pattern.response_parameters],
                "error_types": pattern.error_types,
                "file_path": pattern.file_path
            }
        
        safe_write_json(output_file, serializable_patterns)
        
        if self.verbose:
            self.logger.save(f"Saved {len(self.patterns)} method patterns to {output_file}")
        
        return output_file
    
    def get_pattern_for_method(self, method_name: str) -> Optional[MethodPattern]:
        """Get the pattern for a specific method."""
        return self.patterns.get(method_name)
    
    def get_methods_by_category(self, category: str) -> List[str]:
        """Get all methods in a specific category."""
        return [name for name, pattern in self.patterns.items() 
                if self._categorize_method(name) == category]
    
    def generate_analysis_report(self) -> str:
        """Generate a comprehensive analysis report."""
        analysis = self.analyze_patterns()
        
        report_lines = [
            "# Existing Documentation Analysis Report",
            f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Methods:** {analysis['total_methods']}\n",
            "## Version Distribution\n"
        ]
        
        for version, count in analysis['version_distribution'].items():
            report_lines.append(f"- **{version}**: {count} methods")
        
        report_lines.extend([
            "\n## Method Categories\n",
            f"Found {len(analysis['method_categories'])} distinct categories:\n"
        ])
        
        for category, methods in analysis['method_categories'].items():
            report_lines.append(f"### {category} ({len(methods)} methods)")
            for method in sorted(methods)[:5]:  # Show first 5
                report_lines.append(f"- {method}")
            if len(methods) > 5:
                report_lines.append(f"- ... and {len(methods) - 5} more")
            report_lines.append("")
        
        report_lines.extend([
            "## Common Parameters\n",
            f"Parameters appearing in 3+ methods:\n"
        ])
        
        for param, count in sorted(analysis['common_parameters'].items(), 
                                  key=lambda x: x[1], reverse=True)[:10]:
            report_lines.append(f"- **{param}**: {count} methods")
        
        report_lines.extend([
            "\n## Common Error Types\n",
            f"Error types appearing in 3+ methods:\n"
        ])
        
        for error, count in sorted(analysis['common_error_types'].items(), 
                                  key=lambda x: x[1], reverse=True)[:10]:
            report_lines.append(f"- **{error}**: {count} methods")
        
        return '\n'.join(report_lines)


# Convenience functions for external use
async def scan_existing_documentation_async(docs_path: Optional[Path] = None, 
                                          output_file: Optional[Path] = None) -> Dict[str, MethodPattern]:
    """Convenience function to scan existing documentation asynchronously."""
    scanner = ExistingDocsScanner(docs_path)
    patterns = await scanner.scan_and_extract_patterns_async()
    
    if output_file:
        await scanner.save_patterns_async(output_file)
    
    return patterns


def scan_existing_documentation(docs_path: Optional[Path] = None, 
                               output_file: Optional[Path] = None) -> Dict[str, MethodPattern]:
    """Convenience function to scan existing documentation synchronously."""
    scanner = ExistingDocsScanner(docs_path)
    patterns = scanner.scan_and_extract_patterns()
    
    if output_file:
        scanner.save_patterns(output_file)
    
    return patterns 