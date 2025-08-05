"""
Cleanup utilities for generated files to prevent stale data issues.

This module provides functions to clean up generated files before regeneration,
ensuring that outdated YAML, Postman collections, and JSON examples don't
cause issues.
"""


import shutil
from pathlib import Path
from typing import Dict, List, Set, Union, Optional, Any
from datetime import datetime, timedelta

from ..utils.file_utils import normalize_file_path, ensure_directory_exists
from ..utils.logging_utils import get_logger
from ..constants.config import get_config


class GeneratedFilesCleaner:
    """Handles cleanup of generated files before regeneration."""
    
    def __init__(self, config: Optional[Any] = None, 
                 keep_count: int = 3, verbose: bool = True, dry_run: bool = False):
        """
        Initialize the cleaner.
        
        Args:
            config: Application configuration object
            keep_count: Number of recent files of each type to keep.
            verbose: Whether to log cleanup actions
            dry_run: If True, simulate cleanup without deleting files
        """
        self.config = config or get_config()
        self.workspace_root = Path(self.config.workspace_root).resolve()
        self.keep_count = keep_count
        self.verbose = verbose
        self.dry_run = dry_run
        self.logger = get_logger("FileCleaner") if verbose else None
        self.reports_dir = Path(self.config._resolve_path(self.config.directories.reports_dir))
        self.branched_reports_dir = Path(self.config._resolve_path(self.config.directories.branched_reports_dir))
        
        # Define categories of generated files that need cleanup
        self.FILE_CATEGORIES = {
            'openapi': {
                'patterns': [
                    'openapi/paths/v1/**/*.yaml',
                    'openapi/paths/v2/**/*.yaml',
                    'openapi/paths/v1/*.yaml',
                    'openapi/paths/v2/*.yaml',
                    'openapi/components/schemas/Generated.yaml',
                    'openapi/temp/**/*',
                ],
                'description': 'OpenAPI specification files',
                'preserve_dirs': ['openapi/components/schemas'],
                'preserve_files': [
                    'openapi/components/schemas/Common.yaml',
                    'openapi/components/schemas/Activation.yaml', 
                    'openapi/components/schemas/Orders.yaml',
                    'openapi/components/schemas/Wallet.yaml',
                    'openapi/components/schemas/Trading.yaml',
                    'openapi/components/schemas/Streaming.yaml',
                    'openapi/components/schemas/Lightning.yaml',
                    'openapi/components/schemas/NFT.yaml',
                ]
            },
            'postman_collections': {
                'patterns': [
                    'postman/collections/**/*.json',
                    'postman/environments/**/*.json',
                    'postman/temp/**/*',
                ],
                'description': 'Postman collection files',
                'preserve_dirs': [],
                'preserve_files': []
            },
            'json_examples': {
                'patterns': [
                    'postman/json/**/*.json',
                ],
                'description': 'Postman JSON example files',
                'preserve_dirs': [],
                'preserve_files': []
            },
            'data_files': {
                'patterns': [
                    'utils/py/data/kdf_rust_*_*.json',
                    'utils/py/data/unified_method_mapping.json',
                    'utils/py/data/kdf_postman_method_paths_*.json'
                ],
                'description': 'Timestamped data and mapping files in the main data directory',
                'preserve_dirs': [],
                'preserve_files': []
            },
            'report_files': {
                'patterns': [
                    f'{self.reports_dir}/**/*.json',
                    f'{self.branched_reports_dir}/**/*.json'
                ],
                'description': 'Timestamped report files in the reports subdirectory',
                'preserve_dirs': [],
                'preserve_files': []
            },
            'mdx_documentation': {
                'patterns': ['utils/py/data/generated_docs/**/*.mdx'],
                'description': 'Generated MDX documentation files'
            }
        }
    
    def clean_all_generated_files(self, 
                                 categories: Optional[List[str]] = None,
                                 dry_run: bool = False) -> Dict[str, Dict[str, int]]:
        """
        Clean all generated files or specific categories.
        
        Args:
            categories: List of categories to clean (default: all)
            dry_run: If True, only report what would be cleaned
            
        Returns:
            Dictionary with cleanup results for each category
        """
        if categories is None:
            categories = list(self.FILE_CATEGORIES.keys())
        
        results = {}
        total_files = 0
        total_dirs = 0
        
        self.logger.clean(f"Starting cleanup of generated files (dry_run={dry_run})")
        self.logger.clean(f"Categories to clean: {', '.join(categories)}")
        
        for category in categories:
            if category not in self.FILE_CATEGORIES:
                self._log(f"Warning: Unknown category '{category}', skipping", "warning")
                continue
                
            category_results = self._clean_category(category, dry_run)
            results[category] = category_results
            total_files += category_results["files_removed"]
            total_dirs += category_results["dirs_removed"]
        
        self._log(f"Cleanup complete: {total_files} files, {total_dirs} directories", "success")
        return results
    
    def _clean_category(self, category: str, dry_run: bool) -> Dict[str, int]:
        """Clean files for a specific category."""
        config = self.FILE_CATEGORIES[category]
        results = {"files_removed": 0, "dirs_removed": 0, "errors": 0}
        
        self._log(f"Cleaning category: {category}")
        
        # Convert preserve_files to absolute paths for easier comparison
        preserve_paths = set()
        for preserve_file in config["preserve_files"]:
            preserve_paths.add(str(self.workspace_root / preserve_file))
        
        # Clean each directory
        for directory in config["directories"]:
            dir_path = self.workspace_root / directory
            
            if not dir_path.exists():
                self._log(f"Directory not found: {dir_path}", "debug")
                continue
            
            dir_results = self._clean_directory(
                dir_path, 
                config["patterns"], 
                preserve_paths, 
                dry_run
            )
            
            results["files_removed"] += dir_results["files_removed"]
            results["dirs_removed"] += dir_results["dirs_removed"]
            results["errors"] += dir_results["errors"]
        
        return results
    
    def _clean_directory(self, 
                        directory: Path, 
                        patterns: List[str], 
                        preserve_paths: Set[str], 
                        dry_run: bool) -> Dict[str, int]:
        """Clean files in a specific directory matching patterns."""
        results = {"files_removed": 0, "dirs_removed": 0, "errors": 0}
        
        try:
            # Find all files matching patterns
            files_to_remove = []
            for pattern in patterns:
                files_to_remove.extend(directory.rglob(pattern))
            
            # Remove files that should be preserved
            files_to_remove = [
                f for f in files_to_remove 
                if str(f) not in preserve_paths and not self._should_preserve_file(f)
            ]
            
            # Remove files
            for file_path in files_to_remove:
                try:
                    if dry_run:
                        self._log(f"Would remove file: {file_path.relative_to(self.workspace_root)}", "debug")
                    else:
                        file_path.unlink()
                        self._log(f"Removed file: {file_path.relative_to(self.workspace_root)}", "debug")
                    results["files_removed"] += 1
                except Exception as e:
                    self._log(f"Error removing file {file_path}: {e}", "error")
                    results["errors"] += 1
            
            # Clean empty directories
            empty_dirs = self._find_empty_directories(directory)
            for empty_dir in empty_dirs:
                try:
                    if dry_run:
                        self._log(f"Would remove empty directory: {empty_dir.relative_to(self.workspace_root)}", "debug")
                    else:
                        empty_dir.rmdir()
                        self._log(f"Removed empty directory: {empty_dir.relative_to(self.workspace_root)}", "debug")
                    results["dirs_removed"] += 1
                except Exception as e:
                    self._log(f"Error removing directory {empty_dir}: {e}", "error")
                    results["errors"] += 1
        
        except Exception as e:
            self._log(f"Error cleaning directory {directory}: {e}", "error")
            results["errors"] += 1
        
        return results
    
    def _should_preserve_file(self, file_path: Path) -> bool:
        """Check if a file should be preserved based on additional criteria."""
        # Preserve README files
        if file_path.name.lower().startswith("readme"):
            return True
        
        # Preserve template files
        if "template" in file_path.name.lower():
            return True
        
        # Preserve source files that might be in the same directory
        if file_path.suffix in [".md", ".mdx"]:
            return True
        
        return False
    
    def _find_empty_directories(self, root_dir: Path) -> List[Path]:
        """Find empty directories within a root directory."""
        empty_dirs = []
        
        for dir_path in root_dir.rglob("*"):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                empty_dirs.append(dir_path)
        
        # Sort by depth (deepest first) to avoid removing parent of already removed child
        empty_dirs.sort(key=lambda p: len(p.parts), reverse=True)
        return empty_dirs
    
    def clean_stale_files(self, 
                          max_age_days: int = 7,
                          dry_run: bool = False) -> Dict[str, int]:
        """
        Clean stale generated files older than specified age.
        
        Args:
            max_age_days: Maximum age in days for files to be kept
            dry_run: If True, only report what would be cleaned
            
        Returns:
            Dictionary with cleanup results
        """
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        results = {"files_removed": 0, "errors": 0}
        
        self._log(f"Cleaning stale files older than {max_age_days} days (cutoff: {cutoff_date})")
        
        # Look for generated files in data directories
        data_dirs = [
            self.workspace_root / "utils" / "py" / "data",
            self.workspace_root / "utils" / "js" / "data"
        ]
        
        for data_dir in data_dirs:
            if not data_dir.exists():
                continue
            
            for file_path in data_dir.rglob("*.json"):
                try:
                    # Check if file is generated (based on naming patterns)
                    if not self._is_generated_file(file_path):
                        continue
                    
                    # Check file age
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime < cutoff_date:
                        if dry_run:
                            self._log(f"Would remove stale file: {file_path.relative_to(self.workspace_root)}", "debug")
                        else:
                            file_path.unlink()
                            self._log(f"Removed stale file: {file_path.relative_to(self.workspace_root)}", "debug")
                        results["files_removed"] += 1
                
                except Exception as e:
                    self._log(f"Error processing file {file_path}: {e}", "error")
                    results["errors"] += 1
        
        return results
    
    def _is_generated_file(self, file_path: Path) -> bool:
        """Check if a file is generated and safe to delete."""
        # Files with 'Generated' in the name are typically auto-generated
        if 'Generated' in file_path.name:
            return True
        
        # Check for generation markers in file content
        if file_path.suffix in ['.yaml', '.json']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(500)  # Just check first 500 chars
                    generation_markers = [
                        'Auto-generated',
                        'DO NOT EDIT',
                        'Generated from MDX',
                        'This file is automatically generated'
                    ]
                    return any(marker in content for marker in generation_markers)
            except Exception:
                pass
        
        return False
    
    def create_backup_before_cleanup(self, backup_dir: str = "backups") -> str:
        """
        Create a backup of generated files before cleanup.
        
        Args:
            backup_dir: Directory to store backups
            
        Returns:
            Path to the created backup directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.workspace_root / backup_dir / f"generated_files_backup_{timestamp}"
        
        self._log(f"Creating backup at: {backup_path}")
        
        # Create backup directory
        ensure_directory_exists(backup_path)
        
        # Copy files from each category
        for category, config in self.FILE_CATEGORIES.items():
            category_backup = backup_path / category
            ensure_directory_exists(category_backup)
            
            for directory in config["directories"]:
                source_dir = self.workspace_root / directory
                if source_dir.exists():
                    dest_dir = category_backup / directory
                    if source_dir.is_dir():
                        shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)
                    else:
                        shutil.copy2(source_dir, dest_dir)
        
        self._log(f"Backup created successfully at: {backup_path}", "success")
        return str(backup_path)
    
    def _log(self, message: str, level: str = "info"):
        """Log a message if verbose mode is enabled."""
        if self.verbose and self.logger:
            getattr(self.logger, level)(message)
        elif self.verbose:
            print(f"[{level.upper()}] {message}")

    def clean_files_by_category(self, categories: List[str], 
                               dry_run: bool = False, 
                               create_backup: bool = True,
                               max_age_days: Optional[int] = None) -> List[Path]:
        """
        Clean files by category with enhanced schema preservation.
        
        Args:
            categories: List of category names to clean
            dry_run: If True, only show what would be deleted
            create_backup: Whether to create backups before deletion
            max_age_days: Only delete files older than this many days
            
        Returns:
            List of files that were (or would be) deleted
        """
        if not categories:
            categories = list(self.FILE_CATEGORIES.keys())
        
        cleaned_files = []
        
        for category in categories:
            if category not in self.FILE_CATEGORIES:
                self.logger.warning(f"Unknown category: {category}")
                continue
            
            category_info = self.FILE_CATEGORIES[category]
            self.logger.info(f"Cleaning {category_info['description']}...")
            
            # Get files to clean for this category
            files_to_clean = self._get_files_for_category(category, max_age_days)
            
            # Filter out preserved files
            files_to_clean = self._filter_preserved_files(files_to_clean, category_info)
            
            if not files_to_clean:
                self.logger.info(f"No files to clean for category: {category}")
                continue
            
            # Show what will be cleaned
            self.logger.info(f"Found {len(files_to_clean)} files to clean for {category}")
            
            if dry_run:
                for file_path in files_to_clean:
                    self.logger.info(f"[DRY RUN] Would delete: {file_path}")
                cleaned_files.extend(files_to_clean)
            else:
                # Actually clean the files
                for file_path in files_to_clean:
                    try:
                        if create_backup and category not in ['temp_files']:
                            backup_path = self._create_backup(file_path)
                            if backup_path:
                                self.logger.debug(f"Created backup: {backup_path}")
                        
                        if file_path.is_file():
                            file_path.unlink()
                            self.logger.debug(f"Deleted file: {file_path}")
                        elif file_path.is_dir():
                            shutil.rmtree(file_path)
                            self.logger.debug(f"Deleted directory: {file_path}")
                        
                        cleaned_files.append(file_path)
                        
                    except Exception as e:
                        self.logger.error(f"Failed to delete {file_path}: {e}")
        
        return cleaned_files
    
    def _filter_preserved_files(self, files: List[Path], category_info: Dict[str, Any]) -> List[Path]:
        """Filter out files that should be preserved."""
        preserve_files = set(category_info.get('preserve_files', []))
        preserve_dirs = set(category_info.get('preserve_dirs', []))
        
        filtered_files = []
        
        for file_path in files:
            # Check if file is in preserve list
            relative_path = str(file_path.relative_to(self.workspace_root))
            
            # Skip preserved files
            if relative_path in preserve_files:
                self.logger.debug(f"Preserving file: {relative_path}")
                continue
            
            # Skip files in preserved directories
            should_preserve = False
            for preserve_dir in preserve_dirs:
                if relative_path.startswith(preserve_dir):
                    # Only preserve if it's a manually maintained file
                    if not self._is_generated_file(file_path):
                        self.logger.debug(f"Preserving file in protected directory: {relative_path}")
                        should_preserve = True
                        break
            
            if not should_preserve:
                filtered_files.append(file_path)
        
        return filtered_files
    
    def _get_files_for_category(self, category: str, max_age_days: Optional[int] = None) -> List[Path]:
        """Get all files for a specific category, optionally filtered by age."""
        category_info = self.FILE_CATEGORIES.get(category)
        if not category_info:
            self._log(f"Unknown category: {category}", "warning")
            return []

        files = []
        for pattern in category_info['patterns']:
            try:
                # Glob relative to workspace root
                files.extend(self.workspace_root.glob(pattern))
            except Exception as e:
                self._log(f"Error processing pattern {pattern} for {category}: {e}", "error")

        # Filter out directories
        files = [f for f in files if f.is_file()]

        # Filter by age if specified
        if max_age_days is not None:
            cutoff_time = datetime.now() - timedelta(days=max_age_days)
            files = [f for f in files if datetime.fromtimestamp(f.stat().st_mtime) < cutoff_time]

        # Sort files by modification time, newest first
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        # Return files to be deleted, respecting keep_count
        if self.keep_count > 0:
            return files[self.keep_count:]
        else:
            return files

    def _create_backup(self, file_path: Path) -> Optional[Path]:
        """Create a backup of a file or directory."""
        try:
            if file_path.is_file():
                backup_path = file_path.with_suffix(f"{file_path.suffix}.bak")
                shutil.copy2(file_path, backup_path)
                return backup_path
            elif file_path.is_dir():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = file_path.parent / f"{file_path.name}_backup_{timestamp}"
                shutil.copytree(file_path, backup_path)
                return backup_path
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to create backup for {file_path}: {e}")
        
        return None

    def clean_files_by_patterns(self, patterns: List[str], dry_run: bool = False) -> List[Path]:
        """Clean files matching specific patterns."""
        cleaned_files = []
        
        for pattern in patterns:
            try:
                matching_files = list(self.workspace_root.glob(pattern))
                for file_path in matching_files:
                    if file_path.exists():
                        if dry_run:
                            if self.logger:
                                self.logger.info(f"[DRY RUN] Would delete: {file_path}")
                        else:
                            if file_path.is_file():
                                file_path.unlink()
                            elif file_path.is_dir():
                                shutil.rmtree(file_path)
                            
                            if self.logger:
                                self.logger.debug(f"Deleted: {file_path}")
                        
                        cleaned_files.append(file_path)
                        
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error processing pattern {pattern}: {e}")
        
        return cleaned_files

    def cleanup_generated_files(self, category: str) -> int:
        """General purpose file cleanup based on category."""
        # This is a placeholder for a more robust category-based cleanup.
        # For now, it delegates to the new specific methods.
        if category == 'openapi':
            return self.clean_openapi_files()
        # Add other categories here as needed
        # elif category == 'postman':
        #     return self.clean_postman_files()
        else:
            self.logger.warning(f"Cleanup not implemented for category: {category}")
            return 0

    def clean_openapi_files(self):
        """Cleans all generated OpenAPI specification files."""
        self._log("Cleaning OpenAPI specification files...")
        openapi_paths = self.workspace_root / 'openapi' / 'paths'
        dirs_to_clean = [openapi_paths / 'v1', openapi_paths / 'v2']
        
        removed_count = 0
        for directory in dirs_to_clean:
            if directory.is_dir():
                for item in directory.iterdir():
                    if item.is_file() and item.suffix in ['.yaml']:
                        if self._remove_item(item):
                            removed_count += 1
                    elif item.is_dir():
                        # Recursively clean subdirectories
                        removed_count += self._clean_directory_recursively(item)
        
        self._log(f"Removed {removed_count} OpenAPI files.", "success")
        return removed_count

    def _clean_directory_recursively(self, directory: Path):
        """Helper to recursively clean files in a directory."""
        removed_count = 0
        for item in directory.iterdir():
            if item.is_file() and item.suffix in ['.yaml']:
                if self._remove_item(item):
                    removed_count += 1
            elif item.is_dir():
                removed_count += self._clean_directory_recursively(item)
        return removed_count

    def _remove_item(self, path: Path):
        """Removes a file or directory with logging and dry-run support."""
        try:
            if self.dry_run:
                self._log(f"[Dry Run] Would remove: {path.relative_to(self.workspace_root)}")
            else:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                self._log(f"Removed: {path.relative_to(self.workspace_root)}")
            return True
        except Exception as e:
            self._log(f"Error removing {path}: {e}", "error")
            return False

    def clean_reports(self, keep_count):
        """Cleans old report files."""
        self._log(f"Cleaning reports, keeping {keep_count} most recent...")
        
        # Group files by pattern
        patterns = [
            "kdf_rust_method*.json", "kdf_mdx_method*.json",
            "kdf_openapi_method*.json", "kdf_postman_json_method*.json",
            "kdf_gap_analysis.json"
        ]
        
        removed_count = 0
        for pattern in patterns:
            for dirpath in [self.reports_dir, self.branched_reports_dir]:
                files = sorted(dirpath.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True)
                if len(files) > keep_count:
                    for f in files[keep_count:]:
                        if self._remove_item(f):
                            removed_count += 1
        
        self._log(f"Removed {removed_count} old report files.", "success")
        return removed_count


def clean_generated_files(workspace_root: Union[str, Path], 
                         categories: Optional[List[str]] = None,
                         dry_run: bool = False,
                         create_backup: bool = True,
                         verbose: bool = True) -> Dict[str, Dict[str, int]]:
    """
    Convenience function to clean generated files.
    
    Args:
        workspace_root: Path to the workspace root directory
        categories: List of categories to clean (default: all)
        dry_run: If True, only report what would be cleaned
        create_backup: Whether to create a backup before cleaning
        verbose: Whether to log cleanup actions
        
    Returns:
        Dictionary with cleanup results for each category
    """
    cleaner = GeneratedFilesCleaner(verbose)
    
    if create_backup and not dry_run:
        cleaner.create_backup_before_cleanup()
    
    return cleaner.clean_all_generated_files(categories, dry_run)


def clean_stale_generated_files(workspace_root: Union[str, Path],
                               max_age_days: int = 7,
                               dry_run: bool = False,
                               verbose: bool = True) -> Dict[str, int]:
    """
    Convenience function to clean stale generated files.
    
    Args:
        workspace_root: Path to the workspace root directory
        max_age_days: Maximum age in days for files to be kept
        dry_run: If True, only report what would be cleaned
        verbose: Whether to log cleanup actions
        
    Returns:
        Dictionary with cleanup results
    """
    cleaner = GeneratedFilesCleaner(verbose)
    return cleaner.clean_stale_files(max_age_days, dry_run) 