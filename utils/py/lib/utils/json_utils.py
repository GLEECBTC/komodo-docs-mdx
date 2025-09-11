#!/usr/bin/env python3
"""
JSON utilities for consistent sorting and formatting.

This module provides utilities for deep sorting of JSON data structures,
ensuring consistent alphabetical ordering of all nested objects and lists.
"""

import json
from typing import Any, Dict, List, Union
from pathlib import Path


def deep_sort_data(data: Any) -> Any:
    """
    Recursively sort JSON data structures alphabetically.
    
    - Dictionaries are sorted by keys (case-insensitive)
    - Lists are sorted alphabetically (when possible)
    - Nested structures are recursively sorted
    
    Args:
        data: The data structure to sort
        
    Returns:
        The sorted data structure
    """
    if isinstance(data, dict):
        # Sort dictionary by keys (case-insensitive)
        sorted_dict = {}
        for key in sorted(data.keys(), key=str.lower):
            sorted_dict[key] = deep_sort_data(data[key])
        return sorted_dict
    
    elif isinstance(data, list):
        # Sort list elements recursively
        sorted_list = [deep_sort_data(item) for item in data]
        
        # Try to sort the list if all elements are comparable
        try:
            # If all elements are strings, sort case-insensitive
            if all(isinstance(item, str) for item in sorted_list):
                return sorted(sorted_list, key=str.lower)
            # If all elements are numbers, sort numerically
            elif all(isinstance(item, (int, float)) for item in sorted_list):
                return sorted(sorted_list)
            # If all elements are dicts with same structure, try to sort by a common key
            elif all(isinstance(item, dict) for item in sorted_list):
                # Try to find a common string key to sort by
                common_keys = None
                for item in sorted_list:
                    if common_keys is None:
                        common_keys = set(item.keys())
                    else:
                        common_keys &= set(item.keys())
                
                if common_keys:
                    # Try to sort by the first string key that exists in all items
                    for key in sorted(common_keys, key=str.lower):
                        try:
                            if all(isinstance(item.get(key), str) for item in sorted_list):
                                return sorted(sorted_list, key=lambda x: x[key].lower())
                            elif all(isinstance(item.get(key), (int, float)) for item in sorted_list):
                                return sorted(sorted_list, key=lambda x: x[key])
                        except (KeyError, AttributeError, TypeError):
                            continue
            
            # If we can't sort meaningfully, return as-is but with sorted elements
            return sorted_list
            
        except (TypeError, AttributeError):
            # If sorting fails, return the list with recursively sorted elements
            return sorted_list
    
    else:
        # For primitive types, return as-is
        return data


def dump_sorted_json(data: Any, file_path: Union[str, Path], **kwargs) -> None:
    """
    Dump JSON data to file with consistent deep sorting.
    
    Args:
        data: The data to dump
        file_path: Path to output file
        **kwargs: Additional arguments for json.dump (indent, ensure_ascii, etc.)
    """
    # Set default formatting options
    format_options = {
        'indent': 2,
        'ensure_ascii': False,
        'sort_keys': True,  # This is redundant since we deep sort, but kept for safety
    }
    format_options.update(kwargs)
    
    # Deep sort the data
    sorted_data = deep_sort_data(data)
    
    # Write to file
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_data, f, **format_options)


def dumps_sorted_json(data: Any, **kwargs) -> str:
    """
    Dump JSON data to string with consistent deep sorting.
    
    Args:
        data: The data to dump
        **kwargs: Additional arguments for json.dumps
        
    Returns:
        JSON string with sorted data
    """
    # Set default formatting options
    format_options = {
        'indent': 2,
        'ensure_ascii': False,
        'sort_keys': True,
    }
    format_options.update(kwargs)
    
    # Deep sort the data
    sorted_data = deep_sort_data(data)
    
    return json.dumps(sorted_data, **format_options)


def load_and_sort_json_file(file_path: Union[str, Path]) -> Any:
    """
    Load a JSON file and return its contents with deep sorting applied.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        The loaded and sorted data
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return deep_sort_data(data)


def sort_json_file_inplace(file_path: Union[str, Path]) -> bool:
    """
    Sort a JSON file in place.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        True if the file was modified, False if it was already sorted
    """
    file_path = Path(file_path)
    
    # Load original data
    with open(file_path, 'r', encoding='utf-8') as f:
        original_data = json.load(f)
    
    # Sort the data
    sorted_data = deep_sort_data(original_data)
    
    # Check if data changed
    if json.dumps(original_data, sort_keys=True) == json.dumps(sorted_data, sort_keys=True):
        return False
    
    # Save sorted data
    dump_sorted_json(sorted_data, file_path)
    return True
