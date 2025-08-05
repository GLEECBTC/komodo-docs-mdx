import re
import os
from pathlib import Path
import logging

class MdxErrorScanner:
    def __init__(self, docs_path, logger=None):
        self.docs_path = Path(docs_path)
        self.logger = logger or logging.getLogger(__name__)
        self.error_section_pattern = re.compile(
            r'###\s+Error\s+Types\s*\n((?:.|\n)*?)(?:\n(?:###|##)\s|\Z)',
            re.IGNORECASE
        )
        self.table_row_pattern = re.compile(r'\|\s*([^\|\n]+)\s*\|[^\|\n]+\|([^\|\n]+)\|')
        self.list_item_pattern = re.compile(r'^\s*-\s*\*\*`?([^`*]+)`?\*\*:\s*(.*)')

    def scan_for_errors(self):
        mdx_error_descriptions = {}
        for mdx_file in self.docs_path.glob('**/index.mdx'):
            self.logger.debug(f"Scanning {mdx_file}")
            with open(mdx_file, 'r', encoding='utf-8') as f:
                content = f.read()

            error_section_match = self.error_section_pattern.search(content)
            if not error_section_match:
                continue

            self.logger.info(f"Found 'Error Types' section in {mdx_file}")
            error_content = error_section_match.group(1)
            
            # Extract from tables
            for row in error_content.split('\n'):
                table_match = self.table_row_pattern.match(row)
                if table_match:
                    error_name, description = table_match.groups()
                    error_name = error_name.strip().replace('`', '')
                    description = description.strip()
                    if error_name.lower() in ['parameter', 'errortype', 'error type'] or '---' in error_name:
                        continue
                    
                    if error_name not in mdx_error_descriptions:
                        mdx_error_descriptions[error_name] = []
                    if description and description not in mdx_error_descriptions[error_name]:
                        mdx_error_descriptions[error_name].append(description)

            # Extract from lists
            for list_match in self.list_item_pattern.finditer(error_content):
                error_name, description = list_match.groups()
                error_name = error_name.strip()
                description = description.strip()

                if error_name not in mdx_error_descriptions:
                    mdx_error_descriptions[error_name] = []
                if description and description not in mdx_error_descriptions[error_name]:
                    mdx_error_descriptions[error_name].append(description)

        return mdx_error_descriptions 