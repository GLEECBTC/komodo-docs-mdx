#!/usr/bin/env python3
"""
Utilities Package

Provides utility functions and classes for file operations, path management,
validation, and other common tasks.
"""

# Core utilities
from .logging_utils import get_logger, setup_logging, KomodoLogger, ProgressTracker

# File operations
from .file_utils import (
    normalize_file_path, ensure_directory_exists, find_files_by_pattern,
    safe_read_json, safe_write_json, get_file_stats, extract_filename_parts,
    calculate_file_hash, calculate_content_hash, safe_copy_file, create_backup_path,
    clean_empty_directories, quick_file_stats, cleanup_old_files, 
    validate_file_exists
)

# Import dataclasses from constants submodules
from ..constants.enums import FileType
from ..constants.data_structures import FileInfo, ParameterAnalysis, MethodAnalysis
from ..constants.unified_struct import UnifiedOperationResult, UnifiedBatchResult
from ..constants.exceptions import FileOperationError

# Batch processing
from .batch_processor import BatchFileProcessor, batch_read_json_files, batch_write_json_files

# Path utilities
from ..constants.data_structures import PathMapping

# String processing
from .string_utils import (
    normalize_method_name, format_method_name_for_display, extract_method_parts,
    convert_dir_to_method_name, convert_method_to_dir_name, join_method_parts,
    convert_canonical_to_slug, convert_slug_to_canonical, 
    convert_folder_to_slug, convert_slug_to_folder,
    generate_api_path, extract_category_from_method,
    extract_method_name_from_mdx_content, extract_method_name_from_yaml_filename,
    extract_methods_from_mdx_codeblocks, truncate_text, find_best_match,
    normalize_method_name_variations
)

# Templates from constants package
from ..constants.templates import ExampleTemplates

# Specialized analyzers and generators
from ..analysis.rust_analyzer import MethodAnalyzer

from ..mdx.mdx_generator import MdxGenerator
from ..mdx.mdx_analysis import DocumentAnalyzer
from ..validation.style_validator import StyleValidator
from .testing_utils import DocumentationTestSuite, RepositoryTestUtilities, run_quick_test

from ..constants.enums import ValidationLevel
from ..constants.exceptions import ConfigurationError

__all__ = [
    # Core utilities
    'get_logger',
    'setup_logging',
    'KomodoLogger',
    'ProgressTracker',
    
    # File operations
    'normalize_file_path',
    'ensure_directory_exists',
    'find_files_by_pattern',
    'safe_read_json',
    'safe_write_json',
    'get_file_stats',
    'extract_filename_parts',
    'calculate_file_hash',
    'calculate_content_hash',
    'safe_copy_file',
    'create_backup_path',
    'clean_empty_directories',
    'quick_file_stats',
    'cleanup_old_files',
    'validate_file_exists',
    'safe_read_json',
    'safe_write_json',
    
    # Data types
    'FileType',
    'FileInfo',
    'UnifiedOperationResult',
    'UnifiedBatchResult',
    'ParameterAnalysis',
    'MethodAnalysis',
    'FileOperationError',
    
    # Batch processing
    'BatchFileProcessor',
    'batch_read_json_files',
    'batch_write_json_files',
    
    # Path utilities
    'PathMapping',
    
    # String operations
    'normalize_method_name',
    'format_method_name_for_display',
    'extract_method_parts',
    'convert_dir_to_method_name',
    'convert_method_to_dir_name',
    'join_method_parts',
    'convert_canonical_to_slug',
    'convert_slug_to_canonical',
    'convert_folder_to_slug',
    'convert_slug_to_folder',
    'generate_api_path',
    'extract_category_from_method',
    'extract_method_name_from_mdx_content',
    'extract_method_name_from_yaml_filename',
    'extract_methods_from_mdx_codeblocks',
    'truncate_text',
    'find_best_match',
    'normalize_method_name_variations',
    
    # Templates
    'ExampleTemplates',
    
    # Specialized tools
    'MethodAnalyzer',
    'MdxGenerator',
    'DocumentAnalyzer',
    'StyleValidator',
    'DocumentationTestSuite',
    'RepositoryTestUtilities',
    'run_quick_test',
    'ValidationLevel',
    'ConfigurationError'
]

# Version info
__version__ = '1.0.0' 