#!/usr/bin/env python3
"""
Style Validator

Validates content against style guide rules.
"""

import re
from typing import Dict, List
from ..utils.logging_utils import get_logger


class StyleValidator:
    """Utility class for validating content against style guide rules."""
    
    def __init__(self):
        self.logger = get_logger("style-validator")
        self._load_style_rules()
    
    def _load_style_rules(self):
        """Load style guide rules for validation."""
        self.style_rules = {
            'title_format': r'^export const title = "Komodo DeFi Framework Method: .+";$',
            'description_format': r'^export const description = ".+";$',
            'main_heading': r'^# [A-Z][^#]*$',
            'method_heading': r'^## [a-zA-Z_:]+.*\{\{label\s*:\s*\'[^\']+\'\s*,\s*tag\s*:\s*\'[^\']+\'\}\}$',
            'parameter_table_headers': {
                'request_5col': r'\|\s*Parameter\s*\|\s*Type\s*\|\s*Required\s*\|\s*Default\s*\|\s*Description\s*\|',
                'request_4col': r'\|\s*Parameter\s*\|\s*Type\s*\|\s*Required\s*\|\s*Description\s*\|',
                'response_3col': r'\|\s*Parameter\s*\|\s*Type\s*\|\s*Description\s*\|'
            },
            'required_column': r'[✓✗]',
            'default_values': r'`[^`]+`',
            'userpass_value': 'RPC_UserP@SSW0RD',
            'kebab_case_anchors': r'^[a-z0-9-]+$',
            'bluebook_title_case': r'^[A-Z][a-zA-Z0-9]*(?:[A-Z][a-zA-Z0-9]*)*$'
        }
    
    def validate_title_format(self, line: str) -> bool:
        """Validate title export format."""
        return bool(re.match(self.style_rules['title_format'], line))
    
    def validate_description_format(self, line: str) -> bool:
        """Validate description export format."""
        return bool(re.match(self.style_rules['description_format'], line))
    
    def validate_method_heading(self, line: str) -> bool:
        """Validate method heading format."""
        return bool(re.match(self.style_rules['method_heading'], line))
    
    def validate_parameter_table_header(self, line: str) -> bool:
        """Validate parameter table header format."""
        return any(re.search(pattern, line) for pattern in self.style_rules['parameter_table_headers'].values())
    
    def check_userpass_value(self, content: str) -> bool:
        """Check if userpass uses the correct standard value."""
        if 'userpass' in content.lower():
            return self.style_rules['userpass_value'] in content
        return True  # No userpass found, so no violation
    
    def get_style_violations(self, content: str) -> List[Dict[str, str]]:
        """Get a list of style violations in the content."""
        violations = []
        lines = content.split('\n')
        
        # Check title format
        title_line = next((line for line in lines if line.startswith('export const title')), None)
        if title_line and not self.validate_title_format(title_line):
            violations.append({
                'section': 'metadata',
                'type': 'title_format',
                'line': title_line,
                'description': "Title format doesn't match style guide"
            })
        
        # Check description format
        desc_line = next((line for line in lines if line.startswith('export const description')), None)
        if desc_line and not self.validate_description_format(desc_line):
            violations.append({
                'section': 'metadata',
                'type': 'description_format',
                'line': desc_line,
                'description': "Description format doesn't match style guide"
            })
        
        # Check method heading format
        method_heading = next((line for line in lines if re.match(r'^## [a-zA-Z_:]', line)), None)
        if method_heading and not self.validate_method_heading(method_heading):
            violations.append({
                'section': 'headings',
                'type': 'method_heading',
                'line': method_heading,
                'description': "Method heading format doesn't match style guide"
            })
        
        # Check parameter table headers
        for line_num, line in enumerate(lines):
            if '| Parameter |' in line and not self.validate_parameter_table_header(line):
                violations.append({
                    'section': 'tables',
                    'type': 'table_header',
                    'line': line,
                    'line_number': line_num + 1,
                    'description': "Parameter table header format doesn't match style guide"
                })
        
        # Check userpass value
        if not self.check_userpass_value(content):
            violations.append({
                'section': 'examples',
                'type': 'userpass_value',
                'line': '',
                'description': f"Userpass value doesn't match style guide standard: {self.style_rules['userpass_value']}"
            })
        
        return violations 