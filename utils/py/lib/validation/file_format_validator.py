#!/usr/bin/env python3
"""
File Format Validator

Validates the format and content of various documentation files.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
import yaml

from ..constants.enums import ValidationLevel
from ..constants.regexes import (
    CODE_BLOCK_REGEX,
    METHOD_HEADING_REGEX,
    MDX_SECTION_REGEX,
    USERPASS_REGEX,
)
from ..utils.logging_utils import get_logger
from .results import ValidationResult

class FileFormatValidator:
    """Validates the format and content of different file types."""

    def __init__(self, level: ValidationLevel = ValidationLevel.NORMAL):
        self.level = level
        self.logger = get_logger("file-format-validator")

    def validate_mdx_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """
        Validate MDX file for required elements.
        - Must contain a method heading: ## method_name {{...}}
        - Must contain at least one code block.
        - Code blocks must contain a userpass.
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        file_path = Path(file_path)

        if not file_path.exists():
            result.add_error(f"MDX file not found: {file_path}")
            return result
        
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            result.add_error(f"Could not read MDX file {file_path}: {e}")
            return result
        
        # Check for method heading
        if not METHOD_HEADING_REGEX.search(content):
            result.add_warning(f"No valid method heading '## method_name {{...}}' found in {file_path}")
            
        # Check for code blocks
        code_blocks = CODE_BLOCK_REGEX.findall(content)
        if not code_blocks:
            result.add_warning(f"No code blocks found in {file_path}")
        else:
            # Check for userpass in each JSON code block
            for lang, block_content in code_blocks:
                if lang.startswith("json"):
                    if not USERPASS_REGEX.search(block_content):
                        result.add_warning(f"JSON code block in {file_path} is missing 'userpass'.")

        if not result.errors and not result.warnings:
            result.is_valid = True
        else:
            # A file with only warnings is still considered "valid" for some purposes
            result.is_valid = not result.errors
            
        return result

    def validate_yaml_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """
        Validate YAML file for syntax and basic OpenAPI structure.
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        file_path = Path(file_path)

        if not file_path.exists():
            result.add_error(f"YAML file not found: {file_path}")
            return result

        try:
            with file_path.open('r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            if data is None:
                result.add_error(f"YAML file is empty or invalid: {file_path}")
                return result
        except yaml.YAMLError as e:
            result.add_error(f"YAML syntax error in {file_path}: {e}")
            return result
        except Exception as e:
            result.add_error(f"Could not read or parse YAML file {file_path}: {e}")
            return result

        # Basic OpenAPI structure check
        self._validate_openapi_yaml(data, result)
        
        result.is_valid = not result.errors
        return result

    def _validate_openapi_yaml(self, data: Dict, result: ValidationResult):
        """Validate basic OpenAPI fields."""
        if not isinstance(data, dict):
            result.add_error("YAML content is not a dictionary (object).")
            return
            
        if "operationId" not in data:
            result.add_warning("Missing 'operationId' in YAML.")
        if "summary" not in data:
            result.add_warning("Missing 'summary' in YAML.")
        if "responses" not in data or not isinstance(data.get("responses"), dict):
            result.add_error("Missing or invalid 'responses' section in YAML.")

    def extract_method_name_from_mdx_content(self, content: str) -> Optional[str]:
        """
        Extracts the method name from the ## heading in MDX content.
        
        Args:
            content: The MDX content as a string.
            
        Returns:
            The extracted method name or None if not found.
        """
        match = METHOD_HEADING_REGEX.search(content)
        if match:
            return match.group(1).strip()
        return None

    def extract_method_name_from_yaml_filename(self, filename: str, version: str) -> Optional[str]:
        """
        Extracts the method name from a YAML filename, assuming it follows a convention.
        e.g., v2_task_enable_eth_init.yaml -> task::enable_eth::init
        
        Args:
            filename: The name of the YAML file.
            version: The API version (e.g., 'v1', 'v2').
            
        Returns:
            The reconstructed method name or None.
        """
        name_part = Path(filename).stem
        
        # Remove version prefix like 'v2_'
        if name_part.startswith(f"{version}_"):
            name_part = name_part[len(version) + 1:]
            
        # Replace underscores with '::'
        # This is a strong assumption and may need refinement
        method_name = name_part.replace('_', '::')
        
        return method_name
        
    def extract_methods_from_mdx_codeblocks(self, content: str) -> Tuple[List[str], List[str]]:
        """
        Extracts method names from JSON code blocks within MDX content.
        Handles both single and batch requests.

        Args:
            content: The MDX content string.

        Returns:
            A tuple of (list of found methods, list of parsing errors).
        """
        methods = []
        errors = []
        
        code_blocks = CODE_BLOCK_REGEX.findall(content)

        for lang, block_content in code_blocks:
            if not lang.startswith("json"):
                continue

            try:
                # First, try to parse directly, assuming valid JSON
                data = json.loads(block_content)
            except json.JSONDecodeError:
                # If parsing fails, it might be JSON with comments (JSONC)
                # Try to strip comments and parse again
                try:
                    clean_content = "\n".join(
                        line for line in block_content.split('\n') 
                        if not line.strip().startswith("//")
                    )
                    data = json.loads(clean_content)
                except json.JSONDecodeError as e:
                    errors.append(f"JSON parsing error after stripping comments: {e} in block: {block_content[:100]}...")
                    continue
            
            # Extract method(s) from the parsed data
            try:
                if isinstance(data, dict):
                    # Handle single requests
                    if 'method' in data:
                        methods.append(data['method'])
                    # Handle batch requests
                    elif 'params' in data and isinstance(data['params'], list):
                        for req in data['params']:
                            if isinstance(req, dict) and 'method' in req:
                                methods.append(req['method'])
                elif isinstance(data, list):
                    # Handle batch requests that are a list of dicts
                    for req in data:
                        if isinstance(req, dict) and 'method' in req:
                            methods.append(req['method'])

            except Exception as e:
                errors.append(f"Unexpected error processing block: {e}")

        return list(set(methods)), errors

    def find_mdx_files_missing_codegroup(self, root_dir: Union[str, Path]) -> ValidationResult:
        """
        Analyzes all MDX files in a directory to find those missing <CodeGroup>.
        Specifically checks for ## method_name headings and ensures they are followed
        by a <CodeGroup> before the next heading.

        Args:
            root_dir: The root directory to scan for MDX files.

        Returns:
            A ValidationResult object with:
            - is_valid: False if any files are missing CodeGroup.
            - errors: List of files missing the CodeGroup tag.
            - data: A dictionary with detailed analysis.
        """
        root_path = Path(root_dir)
        result = ValidationResult(is_valid=True, errors=[], warnings=[], data={
            "total_files_scanned": 0,
            "files_with_method_heading": 0,
            "files_ok": [],
            "files_missing_codegroup": []
        })

        mdx_files = list(root_path.rglob("*.mdx"))
        if not mdx_files:
            result.add_warning("No MDX files found in the specified directory.")
            return result

        result.data["total_files_scanned"] = len(mdx_files)

        # Regex to find content between a method heading and the next heading or EOF
        for file_path in mdx_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                sections = MDX_SECTION_REGEX.finditer(content)
                
                has_method_heading = False
                file_is_problematic = False

                for match in sections:
                    has_method_heading = True
                    section_content = match.group(1)
                    
                    # Check if <CodeGroup> is present in this section
                    if "<CodeGroup>" not in section_content:
                        file_is_problematic = True
                        break # No need to check other sections in this file
                
                if has_method_heading:
                    result.data["files_with_method_heading"] += 1
                    if file_is_problematic:
                        error_message = f"File '{file_path}' has a method heading but is missing a subsequent <CodeGroup>."
                        result.add_error(error_message)
                        result.data["files_missing_codegroup"].append(str(file_path))
                    else:
                        result.data["files_ok"].append(str(file_path))

            except Exception as e:
                result.add_warning(f"Could not process file {file_path}: {e}")

        # Final validity is based on whether errors were found
        result.is_valid = not bool(result.errors)
        return result
        