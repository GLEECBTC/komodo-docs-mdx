import re
import os
from pathlib import Path
import logging

class ErrorScanner:
    def __init__(self, repo_path, logger=None):
        self.repo_path = Path(repo_path)
        self.logger = logger or logging.getLogger(__name__)

    def scan_for_errors(self):
        all_errors = {}
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith('.rs'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        found_errors = self._parse_rust_file(content)
                        if found_errors:
                            self.logger.info(f"Found errors in {file_path}: {list(found_errors.keys())}")
                            all_errors.update(found_errors)
                    except Exception as e:
                        self.logger.error(f"Error processing file {file_path}: {e}")
        return all_errors

    def _parse_rust_file(self, content):
        enums = {}
        
        enum_pattern = re.compile(
            r'pub enum\s+(\w*Error)\s*\{((?:.|\n)*?)\n\}',
            re.MULTILINE
        )

        for match in enum_pattern.finditer(content):
            enum_name = match.group(1)
            enum_body = match.group(2)
            
            variants = {}
            lines = enum_body.split('\n')
            
            last_doc_string = ""
            for line in lines:
                doc_match = re.match(r'\s*\/\/\/\s*(.*)', line)
                if doc_match:
                    last_doc_string = doc_match.group(1).strip()
                    continue

                variant_match = re.match(r'\s*([A-Z]\w*)', line)
                if variant_match:
                    variant_name = variant_match.group(1).strip()
                    self.logger.info(f"  - Found variant: {variant_name} with description: {last_doc_string}")
                    variants[variant_name] = last_doc_string
                    last_doc_string = "" # Reset for the next variant

            if variants:
                enums[enum_name] = variants
        return enums 