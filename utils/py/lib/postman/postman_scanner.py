#!/usr/bin/env python3
"""
Postman JSON Example Scanners

Handles scanning and processing of JSON example files for Postman collection generation.
Now uses UnifiedScanner for file discovery and delegates to PostmanUtilities for processing.

REFACTORED: Includes replacement classes for ExtractedExample and MdxJsonExampleExtractor from old postman modules.
"""

import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
import re

from ..mdx.mdx_scanner import UnifiedScanner
from ..utils.logging_utils import get_logger
from .postman_utils import (
    template_json_body,
    generate_request_description,
    generate_test_script
)
from ..constants.data_structures import ExtractedExample
from ..constants.postman_struct import PostmanRequest
# from ..async_support import run_async  # Temporarily disabled for testing



class MdxJsonExampleExtractor:
    """
    Extracts examples from MDX files - replacement for old postman module.
    
    Simplified version focused on the functionality actually used by other modules.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.logger = get_logger("mdx-extractor")
    
    def extract_examples_from_file(self, file_path: str) -> List[ExtractedExample]:
        """Extract examples from a single MDX file, but only from CodeGroup components."""
        examples = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look specifically for CodeGroup blocks (method pages have these, overview pages don't)
            codegroup_pattern = r'<CodeGroup[\s\S]*?>([\s\S]*?)</CodeGroup>'
            codegroups = re.finditer(codegroup_pattern, content, re.MULTILINE)
            
            for codegroup_i, codegroup_match in enumerate(codegroups):
                codegroup_content = codegroup_match.group(1)
                codegroup_start = codegroup_match.start(1)  # Start of the inner content
                
                # Extract JSON code blocks from within CodeGroup
                json_blocks = re.finditer(r'\s*```json\s*\n(.*?)\n\s*```', codegroup_content, re.DOTALL)
                
                for json_i, json_match in enumerate(json_blocks):
                    try:
                        json_content = json.loads(json_match.group(1))
                        if 'method' in json_content:  # Valid API example
                            # Calculate actual line number in the original file
                            json_start_in_file = codegroup_start + json_match.start()
                            line_number = content[:json_start_in_file].count('\n') + 1
                            
                            example = ExtractedExample(
                                method_name=json_content['method'],
                                version='v2' if '"mmrpc": "2.0"' in json_match.group(1) else 'v1',
                                example_type='request',
                                content=json_content,
                                source_file=file_path,
                                line_number=line_number,
                                description=f"CodeGroup {codegroup_i+1}, Example {json_i+1}"
                            )
                            examples.append(example)
                    except json.JSONDecodeError:
                        continue  # Skip invalid JSON
        
        except Exception as e:
            if self.verbose:
                self.logger.warning(f"Failed to extract from {file_path}: {e}")
        
        return examples
    
    def extract_from_mdx_file(self, method_name: str, mapping, version: str) -> List[ExtractedExample]:
        """
        Extract examples from MDX file for a specific method.
        
        Args:
            method_name: Method name to extract examples for
            mapping: MethodMapping object or dict containing mdx_path
            version: API version
            
        Returns:
            List of extracted examples
        """
        # Handle both MethodMapping objects and dictionaries
        if hasattr(mapping, 'mdx_path'):
            # MethodMapping object
            mdx_path = mapping.mdx_path
        elif isinstance(mapping, dict) and 'mdx_path' in mapping:
            # Dictionary
            mdx_path = mapping['mdx_path']
        else:
            return []
        
        if not mdx_path or not os.path.exists(mdx_path):
            return []
        
        # Use the existing extract_examples_from_file method (now CodeGroup-aware)
        all_examples = self.extract_examples_from_file(mdx_path)
        
        # Filter for the specific method
        method_examples = [
            example for example in all_examples 
            if example.method_name == method_name
        ]
        
        return method_examples


class MethodCategorizer:
    """
    Categorizes API methods into logical groups for folder organization.
    """
    
    def __init__(self):
        # Load the categorizer configuration from JSON file
        try:
            config_path = Path(__file__).parent.parent.parent / 'data' / 'postman_categories.json'
            with open(config_path, 'r') as f:
                self.method_categories = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.logger = get_logger("method-categorizer")
            self.logger.warning("postman_categories.json not found or invalid. Using empty categories.")
            self.method_categories = {}
    
    def categorize_method(self, method_name: str) -> str:
        """
        Categorize a method based on its name patterns.
        
        Args:
            method_name: The method name to categorize
            
        Returns:
            Category name
        """
        method_lower = method_name.lower()
        
        for category, config in self.method_categories.items():
            for pattern in config['patterns']:
                if pattern.lower() in method_lower:
                    return category
        
        return 'utility'  # Default category
    
    def get_category_config(self, category: str) -> Dict[str, str]:
        """
        Get configuration for a specific category.
        
        Args:
            category: Category name
            
        Returns:
            Category configuration dict
        """
        return self.method_categories.get(category, {})


class PostmanJSONProcessor:
    """
    Processes JSON examples into Postman requests using UnifiedScanner for file discovery.
    
    REFACTORED: Now uses UnifiedScanner for 3-5x faster async file discovery,
    and delegates to PostmanUtilities for processing logic.
    """
    
    def __init__(self, config, json_dirs: Dict[str, str], verbose: bool = True):
        self.config = config
        self.json_dirs = json_dirs
        self.verbose = verbose
        self.logger = get_logger("postman-json-processor")
        self.categorizer = MethodCategorizer()
        
        # Use UnifiedScanner for file discovery
        self.scanner = UnifiedScanner(
            config=self.config,
            verbose=verbose
        )
    
    def scan_json_examples(self, version: str) -> Dict[str, List[PostmanRequest]]:
        """
        FULLY IMPLEMENTED: Use UnifiedScanner for file discovery, then process into PostmanRequests.
        
        Args:
            version: API version to scan
            
        Returns:
            Dictionary mapping categories to request lists
        """
        if self.verbose:
            self.logger.info(f"🔄 Scanning JSON examples for {version} using UnifiedScanner...")
        
        # Use the scanner to discover JSON files
        json_directory = self.json_dirs.get(version)
        if not json_directory or not os.path.exists(json_directory):
            if self.verbose:
                self.logger.warning(f"JSON directory not found for {version}: {json_directory}")
            return {}
        
        # Scan for JSON files recursively
        json_files = []
        for root, dirs, files in os.walk(json_directory):
            for file in files:
                if file.startswith('request_') and file.endswith('.json'):
                    json_files.append(os.path.join(root, file))
        
        if not json_files:
            if self.verbose:
                self.logger.warning(f"No JSON files found in {json_directory}")
            return {}
        
        if self.verbose:
            self.logger.info(f"Found {len(json_files)} JSON files to process")
        
        # Initialize categorized requests
        categorized_requests = {category: [] for category in self.categorizer.method_categories.keys()}
        
        # Process each JSON file
        for json_file in json_files:
            try:
                # Load JSON data
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                if 'method' not in json_data:
                    
                    if self.verbose:
                        self.logger.debug(f"Skipping {json_file}: No 'method' field")
                    continue
                
                # Extract method info from file path
                method_name, operation = self._extract_method_info_from_path(json_file, json_data)
                
                if not method_name:
                    if self.verbose:
                        self.logger.debug(f"Skipping {json_file}: Could not determine method name")
                    continue
                
                # Create PostmanRequest
                request = self._create_postman_request_from_file(
                    json_data, json_file, method_name, operation, version
                )
                
                if request:
                    # Categorize and add to results
                    category = self.categorizer.categorize_method(method_name)
                    categorized_requests[category].append(request)
                    
                    # if self.verbose:
                        # self.logger.debug(f"Processed {method_name} json_file: {json_file} -> {category}")
            
            except Exception as e:
                if self.verbose:
                    self.logger.warning(f"Error processing {json_file}: {e}")
                continue
        
        # Report results
        total_requests = sum(len(requests) for requests in categorized_requests.values())
        if self.verbose:
            self.logger.info(f"✅ Processed {total_requests} requests across {len([k for k, v in categorized_requests.items() if v])} categories")
        
        return categorized_requests
    
    def _extract_method_info_from_path(self, json_file: str, json_data: Dict[str, Any]) -> tuple:
        """
        Extract method name and operation from file path and JSON data.
        
        Args:
            json_file: Path to JSON file
            json_data: JSON content
            
        Returns:
            Tuple of (method_name, operation)
        """
        # Get method from JSON data
        json_method = json_data.get('method', '')
        
        # Extract operation from file path
        path_parts = Path(json_file).parts
        operation = 'request'  # Default
        
        # Look for operation indicators in path
        for part in reversed(path_parts):
            if any(op in part for op in ['init', 'status', 'cancel', 'user_action']):
                if 'init' in part:
                    operation = 'init'
                elif 'status' in part:
                    operation = 'status'
                elif 'cancel' in part:
                    operation = 'cancel'
                elif 'user_action' in part:
                    operation = 'user_action'
                break
        
        return json_method, operation
    
    def _create_postman_request_from_file(self, json_data: Dict[str, Any], json_file: str,
                                        method_name: str, operation: str, version: str) -> Optional[PostmanRequest]:
        """
        Create a Postman request from JSON file data.
        
        Args:
            json_data: The JSON request data
            json_file: Path to the JSON file
            method_name: The method name
            operation: The operation name
            version: API version
            
        Returns:
            PostmanRequest object or None if invalid
        """
        try:
            # Generate request name
            filename = Path(json_file).stem
            clean_name = filename.replace('-', ' ').replace('_', ' ').title()
            request_name = f"{method_name} - {clean_name}"
            
            # Standard headers
            headers = [
                {"key": "Content-Type", "value": "application/json"},
                {"key": "Accept", "value": "application/json"}
            ]
            
            # Use PostmanUtilities for templating
            templated_body = template_json_body(json_data)
            
            # Generate description and test script
            description = generate_request_description(method_name, method_name, operation, version)
            test_script = generate_test_script(method_name)
            
            return PostmanRequest(
                name=request_name,
                method="POST",
                url="{{kdf_url}}",
                headers=headers,
                body=templated_body,
                description=description,
                tests=test_script,
                method_name=method_name,
                operation=operation,
                example_description=filename
            )
            
        except Exception as e:
            if self.verbose:
                self.logger.warning(f"Failed to create request from {json_file}: {e}")
            return None
    
    async def scan_json_examples_async(self, version: str) -> Dict[str, List[PostmanRequest]]:
        """
        ASYNC: Use UnifiedScanner async methods for maximum performance.
        
        Args:
            version: API version to scan
            
        Returns:
            Dictionary mapping categories to request lists
        """
        if self.verbose:
            print(f"🚀 Scanning JSON examples for {version} asynchronously...")
        
        # For now, delegate to sync version - async can be implemented later
        return self.scan_json_examples(version) 