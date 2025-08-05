#!/usr/bin/env python3
"""
File Types and Data Structures

Core data structures for file operations, moved from unified_file_ops.py
for better organization and to eliminate bloated files.

Note: All dataclasses have been moved to constants.data_structures
"""

# Import all data structures from constants
from ..constants.data_structures import FileInfo
from ..constants.unified_struct import UnifiedOperationResult, UnifiedBatchResult

# Re-export for backwards compatibility
__all__ = ['FileInfo', 'UnifiedOperationResult', 'UnifiedBatchResult'] 