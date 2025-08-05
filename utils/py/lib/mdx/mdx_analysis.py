#!/usr/bin/env python3
"""
Document Analysis Utilities

Provides utilities for analyzing MDX documents, extracting sections,
calculating similarities, and validating content structure.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import re
from typing import Dict, List, Tuple
from difflib import SequenceMatcher
from lib.utils.logging_utils import get_logger


class DocumentAnalyzer:
    """Utility class for analyzing document content and structure."""
    
    def __init__(self):
        self.logger = get_logger("document-analyzer")
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize regex patterns for content extraction."""
        self.section_patterns = {
            'title_export': r'^export const title = .+$',
            'description_export': r'^export const description = .+$',
            'main_heading': r'^# .+$',
            'method_heading': r'^## .+\{\{.*\}\}$',
            'request_params': r'^### Request Parameters?$',
            'response_params': r'^### Response Parameters?$',
            'examples': r'^#### 📌 Examples?$',
            'error_responses': r'^#### ⚠️ Error Responses?$',
            'code_group': r'<CodeGroup>',
            'collapsible_section': r'<CollapsibleSection',
            'parameter_table': r'^\|.*\|.*\|.*\|',
            'error_types': r'^### Error Types$'
        }
        
        self.content_extractors = {
            'method_name': r'## ([a-zA-Z_:]+)',
            'api_version': r"tag\s*:\s*'([^']+)'",
            'human_title': r'# (.+)$',
            'request_params': r'### Request Parameters?\s*\n\n(.*?)(?=\n###|\n####|\n<|\Z)',
            'response_params': r'### Response Parameters?\s*\n\n(.*?)(?=\n###|\n####|\n<|\Z)',
            'examples': r'#### 📌 Examples?\s*\n\n(.*?)(?=\n###|\n####|\Z)',
        }
    
    def extract_document_sections(self, content: str) -> Dict[str, str]:
        """Extract key sections from MDX content."""
        sections = {}
        
        # Extract specific patterns
        for section_name, pattern in self.content_extractors.items():
            match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
            if match:
                sections[section_name] = match.group(1) if match.lastindex else match.group(0)
            else:
                sections[section_name] = ""
        
        # Extract full content sections by parsing line by line
        lines = content.split('\n')
        current_section = None
        section_content = []
        
        for line in lines:
            if line.startswith('# '):
                if current_section and section_content:
                    sections[f"full_{current_section}"] = '\n'.join(section_content)
                current_section = "main_content"
                section_content = [line]
            elif line.startswith('## '):
                if current_section and section_content:
                    sections[f"full_{current_section}"] = '\n'.join(section_content)
                current_section = "method_content"
                section_content = [line]
            elif line.startswith('### '):
                if current_section and section_content:
                    sections[f"full_{current_section}"] = '\n'.join(section_content)
                if "Request Parameter" in line:
                    current_section = "request_params"
                elif "Response Parameter" in line:
                    current_section = "response_params"
                elif "Error Types" in line:
                    current_section = "error_types"
                else:
                    current_section = "other_section"
                section_content = [line]
            else:
                if current_section:
                    section_content.append(line)
        
        # Don't forget the last section
        if current_section and section_content:
            sections[f"full_{current_section}"] = '\n'.join(section_content)
        
        return sections
    
    def calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings."""
        return SequenceMatcher(None, content1, content2).ratio()
    
    def classify_content_difference(self, generated: str, live: str, section: str) -> str:
        """Classify the type of content difference."""
        if "param" in section.lower():
            return "parameters"
        elif "example" in section.lower():
            return "examples"
        elif "error" in section.lower():
            return "error_handling"
        elif "title" in section.lower() or "description" in section.lower():
            return "metadata"
        elif "heading" in section.lower():
            return "structure"
        else:
            return "content"
    
    def assess_difference_severity(self, similarity: float, section: str) -> str:
        """Assess the severity of a difference based on similarity score."""
        if similarity < 0.3:
            return "critical"
        elif similarity < 0.6:
            return "major"
        else:
            return "minor"
    
    def find_section_differences(self, generated_sections: Dict[str, str], 
                               live_sections: Dict[str, str]) -> Tuple[List[str], List[str]]:
        """Find missing and extra sections between two documents."""
        gen_keys = set(generated_sections.keys())
        live_keys = set(live_sections.keys())
        
        missing_in_generated = list(live_keys - gen_keys)
        extra_in_generated = list(gen_keys - live_keys)
        
        return missing_in_generated, extra_in_generated 