"""
File Utilities

Consolidated file utility functions for the Komodo Documentation Library.
These utilities handle path operations, file I/O, and file management tasks.
"""

import json
import os
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Any, Union, List
from datetime import datetime

from ..constants.exceptions import FileOperationError


# =============================================================================
# PATH OPERATIONS
# =============================================================================

def normalize_file_path(path: Union[str, Path]) -> Path:
    """
    Normalize a file path to Path object with consistent handling.
    
    Args:
        path: File path as string or Path object
        
    Returns:
        Normalized Path object
    """
    if isinstance(path, str):
        return Path(path).resolve()
    return path.resolve()


def validate_file_exists(path: Union[str, Path], operation: str = "read") -> Path:
    """
    Validate that a file exists and is readable.
    
    Args:
        path: File path to validate
        operation: Operation being performed (for error messages)
        
    Returns:
        Validated Path object
        
    Raises:
        FileOperationError: If file doesn't exist or isn't accessible
    """
    normalized_path = normalize_file_path(path)
    
    if not normalized_path.exists():
        raise FileOperationError(f"File not found for {operation}: {normalized_path}")
    
    if not normalized_path.is_file():
        raise FileOperationError(f"Path is not a file: {normalized_path}")
    
    return normalized_path


def ensure_directory_exists(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Path object for the directory
    """
    normalized_path = normalize_file_path(path)
    normalized_path.mkdir(parents=True, exist_ok=True)
    return normalized_path


def find_files_by_pattern(directory: Union[str, Path], pattern: str, 
                         recursive: bool = True) -> List[Path]:
    """
    Find files matching a pattern in a directory.
    
    Args:
        directory: Directory to search
        pattern: Glob pattern to match
        recursive: Whether to search recursively
        
    Returns:
        List of matching file paths
    """
    dir_path = normalize_file_path(directory)
    
    if not dir_path.exists() or not dir_path.is_dir():
        return []
    
    if recursive:
        return list(dir_path.rglob(pattern))
    else:
        return list(dir_path.glob(pattern))


# =============================================================================
# JSON OPERATIONS
# =============================================================================

def safe_read_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Safely read a JSON file with proper error handling.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON data
        
    Raises:
        FileOperationError: If file cannot be read or parsed
    """
    validated_path = validate_file_exists(file_path, "read JSON")
    
    try:
        with open(validated_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise FileOperationError(f"Invalid JSON in {validated_path}: {e}")
    except Exception as e:
        raise FileOperationError(f"Error reading JSON file {validated_path}: {e}")


def safe_write_json(file_path: Union[str, Path], data: Dict[str, Any], 
                   indent: int = 2, ensure_ascii: bool = False) -> None:
    """
    Safely write data to a JSON file with proper error handling.
    
    Args:
        file_path: Path to write JSON file
        data: Data to write
        indent: JSON indentation
        ensure_ascii: Whether to ensure ASCII encoding
        
    Raises:
        FileOperationError: If file cannot be written
    """
    normalized_path = normalize_file_path(file_path)
    ensure_directory_exists(normalized_path.parent)
    
    try:
        with open(normalized_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
    except Exception as e:
        raise FileOperationError(f"Error writing JSON file {normalized_path}: {e}")


# =============================================================================
# FILE STATISTICS AND UTILITIES
# =============================================================================

def get_file_stats(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get comprehensive statistics about a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Dictionary with file statistics
    """
    validated_path = validate_file_exists(file_path, "get stats")
    stat = validated_path.stat()
    
    return {
        'size': stat.st_size,
        'modified': datetime.fromtimestamp(stat.st_mtime),
        'created': datetime.fromtimestamp(stat.st_ctime),
        'extension': validated_path.suffix,
        'name': validated_path.name,
        'stem': validated_path.stem,
        'is_readable': os.access(validated_path, os.R_OK),
        'is_writable': os.access(validated_path, os.W_OK)
    }


def extract_filename_parts(file_path: Union[str, Path]) -> Dict[str, str]:
    """
    Extract various parts of a filename.
    
    Args:
        file_path: Path to file
        
    Returns:
        Dictionary with filename parts
    """
    path = normalize_file_path(file_path)
    
    return {
        'full_name': path.name,
        'stem': path.stem,
        'extension': path.suffix,
        'parent': str(path.parent),
        'parts': list(path.parts)
    }


def calculate_file_hash(file_path: Union[str, Path], algorithm: str = "md5") -> str:
    """
    Calculate hash of a file's contents.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)
        
    Returns:
        Hex digest of file hash
    """
    validated_path = validate_file_exists(file_path, "calculate hash")
    hash_obj = hashlib.new(algorithm)
    
    with open(validated_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def calculate_content_hash(content: Union[str, Dict[str, Any]], algorithm: str = "md5") -> str:
    """
    Calculate hash of content (string or JSON-serializable data).
    
    Args:
        content: Content to hash
        algorithm: Hash algorithm
        
    Returns:
        Hex digest of content hash
    """
    if isinstance(content, dict):
        content_str = json.dumps(content, sort_keys=True, separators=(',', ':'))
    else:
        content_str = str(content)
    
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(content_str.encode('utf-8'))
    return hash_obj.hexdigest()


# =============================================================================
# FILE OPERATIONS
# =============================================================================

def safe_copy_file(src: Union[str, Path], dst: Union[str, Path], 
                   create_backup: bool = False) -> None:
    """
    Safely copy a file with optional backup.
    
    Args:
        src: Source file path
        dst: Destination file path
        create_backup: Whether to create backup of existing destination
        
    Raises:
        FileOperationError: If copy operation fails
    """
    src_path = validate_file_exists(src, "copy source")
    dst_path = normalize_file_path(dst)
    
    # Create destination directory if needed
    ensure_directory_exists(dst_path.parent)
    
    # Create backup if requested and destination exists
    if create_backup and dst_path.exists():
        backup_path = create_backup_path(dst_path)
        shutil.copy2(dst_path, backup_path)
    
    try:
        shutil.copy2(src_path, dst_path)
    except Exception as e:
        raise FileOperationError(f"Error copying {src_path} to {dst_path}: {e}")


def create_backup_path(file_path: Union[str, Path], suffix: str = ".backup") -> Path:
    """
    Create a backup path for a file.
    
    Args:
        file_path: Original file path
        suffix: Backup suffix
        
    Returns:
        Path for backup file
    """
    path = normalize_file_path(file_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{path.stem}{suffix}{path.suffix}"
    return path.parent / backup_name


# =============================================================================
# CLEANUP UTILITIES
# =============================================================================

def clean_empty_directories(directory: Union[str, Path], dry_run: bool = True) -> List[str]:
    """
    Remove empty directories recursively.
    
    Args:
        directory: Root directory to clean
        dry_run: If True, only report what would be deleted
        
    Returns:
        List of directories that were (or would be) removed
    """
    dir_path = normalize_file_path(directory)
    removed_dirs = []
    
    if not dir_path.exists():
        return removed_dirs
    
    # Walk directory tree bottom-up
    for root, dirs, files in os.walk(str(dir_path), topdown=False):
        for dir_name in dirs:
            dir_to_check = Path(root) / dir_name
            
            # Check if directory is empty
            try:
                if not any(dir_to_check.iterdir()):
                    if dry_run:
                        removed_dirs.append(str(dir_to_check))
                    else:
                        dir_to_check.rmdir()
                        removed_dirs.append(str(dir_to_check))
            except OSError:
                # Directory not empty or permission error
                pass
    
    return removed_dirs


# =============================================================================
# BATCH OPERATIONS
# =============================================================================

def quick_file_stats(file_paths: List[Union[str, Path]]) -> Dict[str, Any]:
    """
    Get quick statistics for multiple files.
    
    Args:
        file_paths: List of file paths
        
    Returns:
        Dictionary with aggregate statistics
    """
    stats = {
        'total_files': len(file_paths),
        'existing_files': 0,
        'total_size': 0,
        'extensions': {},
        'largest_file': None,
        'smallest_file': None
    }
    
    file_sizes = []
    
    for file_path in file_paths:
        try:
            file_stat = get_file_stats(file_path)
            stats['existing_files'] += 1
            stats['total_size'] += file_stat['size']
            
            ext = file_stat['extension'].lower()
            stats['extensions'][ext] = stats['extensions'].get(ext, 0) + 1
            
            file_sizes.append((file_path, file_stat['size']))
            
        except FileOperationError:
            # File doesn't exist, skip
            continue
    
    if file_sizes:
        file_sizes.sort(key=lambda x: x[1])
        stats['smallest_file'] = {'path': str(file_sizes[0][0]), 'size': file_sizes[0][1]}
        stats['largest_file'] = {'path': str(file_sizes[-1][0]), 'size': file_sizes[-1][1]}
        stats['average_size'] = stats['total_size'] / len(file_sizes)
    
    return stats


def cleanup_old_files(directory: str, pattern: str, keep_count: int = 3, verbose: bool = True) -> int:
    """
    Clean up old files matching a pattern, keeping only the most recent ones.
    
    Args:
        directory: Directory to search for files
        pattern: Glob pattern to match files (e.g., "kdf_rust_method*.json")
        keep_count: Number of most recent files to keep (default: 3)
        verbose: Whether to log cleanup actions
        
    Returns:
        Number of files removed
    """
    try:
        from .logging_utils import get_logger
        logger = get_logger("file-cleanup") if verbose else None
        
        directory_path = Path(directory)
        if not directory_path.exists():
            if verbose and logger:
                logger.info(f"Directory does not exist: {directory}")
            return 0
        
        # Find all matching files
        matching_files = list(directory_path.glob(pattern))
        
        if len(matching_files) <= keep_count:
            return 0
        
        # Sort by modification time (newest first)
        matching_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Files to remove (everything after keep_count)
        files_to_remove = matching_files[keep_count:]
        
        removed_count = 0
        for file_path in files_to_remove:
            try:
                file_path.unlink()
                removed_count += 1
                if verbose and logger:
                    logger.info(f"Removed old file: {file_path.name}")
            except Exception as e:
                if verbose and logger:
                    logger.warning(f"Failed to remove {file_path.name}: {e}")
        
        if verbose and logger and removed_count > 0:
            logger.success(f"Cleanup complete: removed {removed_count} old files, kept {keep_count} most recent")
        
        return removed_count
        
    except Exception as e:
        if verbose:
            try:
                from .logging_utils import get_logger
                logger = get_logger("file-cleanup")
                logger.error(f"Cleanup failed for pattern {pattern}: {e}")
            except:
                print(f"Cleanup failed for pattern {pattern}: {e}")
        return 0


    """
    Clean up KDF temporary files, keeping only the most recent ones.
    
    Args:
        data_dir: Directory containing the files
        keep_count: Number of files to keep for each type
        verbose: Whether to log cleanup actions
        
    Returns:
        Dictionary with cleanup results for each file type
    """
    cleanup_patterns = {
        "rust_methods": "kdf_rust_method*.json",
        "mdx_methods": "kdf_mdx_method*.json",
        "openapi_methods": "kdf_openapi_method*.json",
        "json_methods": "kdf_json_method*.json",
        "postman_methods": "kdf_postman_method*.json",
        "method_mapping": "kdf_method_mapping.json",
        "unified_method_mapping": "kdf_unified_method_mapping.json",
    }
    
    results = {}
    total_removed = 0
    
    if verbose:
        try:
            from .logging_utils import get_logger
            logger = get_logger("kdf-cleanup")
            logger.info(f"Starting KDF temp file cleanup (keeping {keep_count} most recent of each type)")
        except:
            print(f"Starting KDF temp file cleanup (keeping {keep_count} most recent of each type)")
    
    for file_type, pattern in cleanup_patterns.items():
        removed = cleanup_old_files(data_dir, pattern, keep_count, verbose)
        results[file_type] = removed
        total_removed += removed
    
    if verbose and total_removed > 0:
        try:
            from .logging_utils import get_logger
            logger = get_logger("kdf-cleanup")
            logger.success(f"Total cleanup: removed {total_removed} old files")
        except:
            print(f"Total cleanup: removed {total_removed} old files")
    
    return results 