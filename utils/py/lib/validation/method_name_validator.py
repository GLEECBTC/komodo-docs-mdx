#!/usr/bin/env python3
"""
Method Name Validator

Validates the format and structure of KDF API method names.
"""

import re
from functools import lru_cache
from typing import List

from ..constants.enums import ValidationLevel
from .results import ValidationResult


class MethodNameValidator:
    """Validates KDF method names against defined conventions."""
    
    # Regex for standard methods: lowercase, numbers, underscores, with '::' separators
    # e.g., 'task::enable_eth::init'
    STANDARD_METHOD_REGEX = re.compile(r"^[a-z0-9_]+(::[a-z0-9_]+)+$")
    
    # Regex for RPC v1 methods, which may not have '::'
    # e.g., 'buy', 'setprice'
    V1_METHOD_REGEX = re.compile(r"^[a-z0-9_]+$")
    
    # Common prefixes and segments
    KNOWN_PREFIXES = {"task::", "lightning::", "z_coin::", "stream::", "util::"}
    KNOWN_ACTIONS = {"::init", "::status", "::cancel", "::user_action", "::enable", "::disable"}
    
    def __init__(self, level: ValidationLevel = ValidationLevel.NORMAL):
        self.level = level

    def validate_method_name(self, method_name: str) -> ValidationResult:
        """
        Validate the format of a KDF method name.
        
        Args:
            method_name: The method name to validate.
            
        Returns:
            A ValidationResult object.
        """
        result = ValidationResult(is_valid=True)
        
        if not isinstance(method_name, str) or not method_name:
            result.add_error("Method name must be a non-empty string.")
            return result
        
        # Check against standard and v1 regex
        is_standard = self.STANDARD_METHOD_REGEX.match(method_name)
        is_v1_style = self.V1_METHOD_REGEX.match(method_name)
        
        if not is_standard and not is_v1_style:
            result.add_error(
                f"Method name '{method_name}' contains invalid characters or structure. "
                "Must be lowercase, with words separated by '_' and segments by '::'."
            )
        
        # Additional checks for strict validation level
        if self.level == ValidationLevel.STRICT:
            if "::" in method_name:
                segments = method_name.split('::')
                if len(segments) < 2:
                    result.add_warning(f"Method '{method_name}' looks like a namespace but has too few segments.")
                for segment in segments:
                    if not segment:
                        result.add_error(f"Method '{method_name}' contains an empty segment.")
                    if segment.startswith("_") or segment.endswith("_"):
                        result.add_warning(f"Segment '{segment}' in '{method_name}' starts or ends with an underscore.")
            
            if "__" in method_name:
                result.add_warning(f"Method name '{method_name}' contains double underscores.")
        
        if not result.errors:
            result.is_valid = True
            
        return result

    def is_valid_method_name(self, method_name: str) -> bool:
        """
        Quick check if a method name is valid.
        
        Args:
            method_name: The method name to check.
            
        Returns:
            True if the method name is valid, False otherwise.
        """
        return self.validate_method_name(method_name).is_valid

    @lru_cache(maxsize=128)
    def clean_method_name(self, method_name: str) -> str:
        """
        Clean and standardize a method name.
        
        - Converts to lowercase
        - Replaces spaces and hyphens with underscores
        - Removes leading/trailing whitespace and special characters
        
        Args:
            method_name: The method name to clean.
            
        Returns:
            A cleaned method name string.
        """
        if not isinstance(method_name, str):
            return ""
        
        # Lowercase and replace separators
        cleaned = method_name.lower().strip()
        cleaned = cleaned.replace(" ", "_").replace("-", "_")
        
        # Remove any characters not allowed in method names
        # This is a bit aggressive, but ensures a valid structure.
        # It allows a-z, 0-9, _, and the :: separator.
        cleaned = re.sub(r"[^a-z0-9_:]", "", cleaned)
        
        # Consolidate multiple underscores
        cleaned = re.sub(r"_{2,}", "_", cleaned)
        
        # Consolidate multiple colons (less common, but for safety)
        cleaned = re.sub(r":{3,}", "::", cleaned)
        
        # Remove leading/trailing underscores or colons from segments
        segments = cleaned.split('::')
        cleaned_segments = [s.strip('_') for s in segments]
        cleaned = "::".join(cleaned_segments)
        
        return cleaned

    def suggest_alternatives(self, invalid_method: str, known_methods: List[str]) -> List[str]:
        """
        Suggest alternative method names for a potentially invalid one.
        
        Args:
            invalid_method: The method name that failed validation.
            known_methods: A list of all known valid methods.
            
        Returns:
            A list of suggested valid method names.
        """
        from rapidfuzz import process, fuzz
        
        cleaned_method = self.clean_method_name(invalid_method)
        
        # Use a reasonably high score to avoid irrelevant matches
        results = process.extract(
            cleaned_method, 
            known_methods, 
            scorer=fuzz.token_sort_ratio, 
            limit=3, 
            score_cutoff=75
        )
        
        return [res[0] for res in results] 