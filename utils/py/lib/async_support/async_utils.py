#!/usr/bin/env python3
"""
Async Utilities

Provides async/await support for I/O-bound operations in the Komodo Documentation Library.
Uses the unified file operations system for consistency and consolidated utilities.
"""

import asyncio
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Union, Tuple
from concurrent.futures import ThreadPoolExecutor
import json

from ..constants.config import get_config
from ..utils.logging_utils import get_logger, ProgressTracker
from ..utils.string_utils import (
    extract_method_name_from_mdx_content, 
    extract_method_name_from_yaml_filename,
    is_overview_page
)


class AsyncFileProcessor:
    """
    Async file processing utilities that delegate to the unified file operations system.
    
    Provides high-performance async operations while maintaining consistency
    with the unified file operations architecture.
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        self.config = get_config()
        self.logger = get_logger("async-processor")
        # Use default values since the new config doesn't have processing attributes
        self.max_workers = max_workers or 4
        
        # Thread pool for CPU-bound operations
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
    
    async def read_file_async(self, file_path: Union[str, Path]) -> str:
        """Read file content asynchronously."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            return content
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            raise
    
    async def read_json_async(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Read and parse JSON file asynchronously using direct implementation."""
        loop = asyncio.get_event_loop()
        
        def _read_json_sync(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return await loop.run_in_executor(
            self.thread_pool, 
            _read_json_sync, 
            file_path
        )
    
    async def write_file_async(self, file_path: Union[str, Path], content: str) -> None:
        """Write file content asynchronously."""
        try:
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
                
            self.logger.debug(f"Written file: {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to write file {file_path}: {e}")
            raise
    
    async def write_json_async(self, file_path: Union[str, Path], data: Dict[str, Any]) -> None:
        """Write JSON data to file asynchronously using direct implementation."""
        loop = asyncio.get_event_loop()
        
        def _write_json_sync(path, json_data):
            # Ensure directory exists
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2)
        
        await loop.run_in_executor(
            self.thread_pool,
            _write_json_sync,
            file_path, data
        )
    
    async def scan_directory_async(self, directory: Union[str, Path], 
                                  pattern: str = "*") -> List[Path]:
        """Scan directory for files matching pattern asynchronously."""
        loop = asyncio.get_event_loop()
        
        def _scan_files_sync(dir_path, file_pattern):
            from pathlib import Path
            dir_path = Path(dir_path)
            if not dir_path.exists():
                return []
            return list(dir_path.rglob(file_pattern))
        
        return await loop.run_in_executor(
            self.thread_pool,
            _scan_files_sync,
            directory, pattern
        )
    
    async def process_files_batch(self, file_paths: List[Path], 
                                 processor_func: Callable,
                                 batch_size: Optional[int] = None) -> List[Any]:
        """Process multiple files in batches asynchronously."""
        # Use default batch size since the new config doesn't have processing attributes
        batch_size = batch_size or 50
        results = []
        
        self.logger.info(f"Processing {len(file_paths)} files in batches of {batch_size}")
        
        # Create progress tracker
        progress = ProgressTracker(len(file_paths), "File Processing", self.logger)
        
        # Process in batches
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = []
            for file_path in batch:
                if asyncio.iscoroutinefunction(processor_func):
                    task = processor_func(file_path)
                else:
                    # Wrap sync function for async execution
                    loop = asyncio.get_event_loop()
                    task = loop.run_in_executor(self.thread_pool, processor_func, file_path)
                batch_tasks.append(task)
            
            # Wait for batch completion
            try:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Handle results and exceptions
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        # Use default continue_on_error behavior (True)
                        self.logger.warning(f"Error processing {batch[j]}: {result}")
                        results.append(None)
                    else:
                        results.append(result)
                    
                    progress.update()
                    
            except Exception as e:
                # Use default continue_on_error behavior (False for critical errors)
                self.logger.error(f"Batch processing failed: {e}")
                raise
        
        progress.finish()
        return results
    
    async def concurrent_map(self, func: Callable, items: List[Any], 
                           max_concurrent: Optional[int] = None) -> List[Any]:
        """Apply function to items concurrently with controlled concurrency."""
        max_concurrent = max_concurrent or self.max_workers
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def _process_item(item):
            async with semaphore:
                if asyncio.iscoroutinefunction(func):
                    return await func(item)
                else:
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(self.thread_pool, func, item)
        
        # Create all tasks
        tasks = [_process_item(item) for item in items]
        
        # Execute with progress tracking
        progress = ProgressTracker(len(tasks), f"Concurrent Processing {func.__name__}", self.logger)
        results = []
        
        for completed_task in asyncio.as_completed(tasks):
            try:
                result = await completed_task
                results.append(result)
                # progress.update()
            except Exception as e:
                # Use default continue_on_error behavior (True for individual tasks)
                self.logger.warning(f"Task failed: {e}")
                results.append(None)
            progress.update()
        
        progress.finish()
        return results
    
    def __del__(self):
        """Clean up thread pool."""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=False)


class AsyncMethodProcessor:
    """
    Async processing utilities specifically for API method operations.
    
    Handles concurrent scanning, mapping, and processing of method-related files.
    Uses consolidated extraction functions for consistency.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.file_processor = AsyncFileProcessor()
        self.logger = get_logger("method-processor")
    
    async def scan_mdx_files_async(self, directories: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """Scan MDX files asynchronously across multiple directories."""
        results = {}
        
        for version, directory in directories.items():
            self.logger.info(f"Scanning MDX files for {version}")
            
            # Get all MDX files in directory
            mdx_files = await self.file_processor.scan_directory_async(directory, "*.mdx")
            
            # Process files concurrently
            version_results = await self._process_mdx_files(mdx_files)
            results[version] = version_results
        
        return results
    
    async def _process_mdx_files(self, mdx_files: List[Path]) -> Dict[str, str]:
        """Process MDX files to extract method mappings."""
        async def extract_method_from_mdx(file_path: Path) -> Tuple[str, str]:
            try:
                content = await self.file_processor.read_file_async(file_path)
                
                # Skip overview pages - they don't represent actual API methods
                if is_overview_page(content):
                    return None, None
                
                # Use consolidated extraction function
                method_name = extract_method_name_from_mdx_content(content)
                return method_name, str(file_path) if method_name else None
            except Exception as e:
                self.logger.warning(f"Failed to process MDX file {file_path}: {e}")
                return None, None
        
        # Process all files concurrently
        results = await self.file_processor.concurrent_map(extract_method_from_mdx, mdx_files)
        
        # Filter and format results
        method_mappings = {}
        for method_name, file_path in results:
            if method_name and file_path:
                method_mappings[method_name] = file_path
        
        # Sort the method mappings by method name for consistent output
        return dict(sorted(method_mappings.items()))
    
    async def scan_yaml_files_async(self, directories: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """Scan YAML files asynchronously across multiple directories."""
        results = {}
        
        for version, directory in directories.items():
            self.logger.info(f"Scanning YAML files for {version}")
            
            # Get all YAML files
            yaml_files = await self.file_processor.scan_directory_async(
                directory, "*.yaml"
            ) + await self.file_processor.scan_directory_async(
                directory, "*.yaml"
            )
            
            # Process files concurrently
            version_results = await self._process_yaml_files(yaml_files, version)
            results[version] = version_results
        
        return results
    
    async def _process_yaml_files(self, yaml_files: List[Path], version: str) -> Dict[str, str]:
        """Process YAML files to extract method mappings."""
        async def extract_method_from_yaml(file_path: Path) -> Tuple[str, str]:
            try:
                # Use consolidated extraction function
                method_name = extract_method_name_from_yaml_filename(file_path.name, version)
                return method_name, str(file_path) if method_name else None
            except Exception as e:
                self.logger.warning(f"Failed to process YAML file {file_path}: {e}")
                return None, None
        
        # Process all files concurrently
        results = await self.file_processor.concurrent_map(extract_method_from_yaml, yaml_files)
        
        # Filter and format results
        method_mappings = {}
        for method_name, file_path in results:
            if method_name and file_path:
                method_mappings[method_name] = file_path
        
        # Sort the method mappings by method name for consistent output
        return dict(sorted(method_mappings.items()))
    
    async def scan_json_examples_async(self, directories: Dict[str, str]) -> Dict[str, Dict[str, Tuple[str, int]]]:
        """
        Asynchronously scan JSON examples.
        
        FIXED: Removed circular dependency by implementing direct scanning logic
        instead of creating another UnifiedScanner instance.
        
        Args:
            directories: Dictionary mapping versions to directories
            
        Returns:
            Dictionary mapping versions to method mappings
        """
        results = {}
        
        async def scan_version(version: str, directory: str) -> Dict[str, Tuple[str, int]]:
            """Scan a single version asynchronously."""
            try:
                # Scan directory for JSON files
                json_files = await self.file_processor.scan_directory_async(directory, "*.json")
                
                # Group files by method name (extracted from directory structure)
                method_groups = {}
                for json_file in json_files:
                    # Extract method name from file path structure
                    # Typical structure: /path/to/method-name/example.json
                    parts = json_file.parts
                    if len(parts) >= 2:
                        # Get the parent directory name as method name
                        method_dir = parts[-2]
                        # Convert from directory format (hyphen-separated) to canonical API format (:: separated).
                        # This assumes that the directory name uses hyphens as separators,
                        # which is the correct convention. e.g., 'task-enable_utxo-init' -> 'task::enable_utxo::init'.
                        method_name = method_dir.replace('-', '::')
                        
                        if method_name not in method_groups:
                            method_groups[method_name] = []
                        method_groups[method_name].append(json_file)
                
                # Convert to expected format
                converted = {}
                for method, files in method_groups.items():
                    if files:
                        # Use the parent directory of the first file as the path
                        first_file = files[0]
                        dir_path = str(first_file.parent.relative_to(Path(directory)))
                        converted[method] = (dir_path, len(files))
                
                # Sort the method mappings by method name for consistent output
                return dict(sorted(converted.items()))
                
            except Exception as e:
                self.logger.warning(f"Failed to scan {directory} for version {version}: {e}")
                return {}
        
        # Scan all versions concurrently
        tasks = []
        for version_key, directory in directories.items():
            # Extract version from directory key (e.g., 'postman_json_v1' -> 'v1')
            if version_key.startswith('json_'):
                version = version_key[5:]  # Remove 'json_' prefix
            else:
                version = version_key
            
            tasks.append((version, scan_version(version, directory)))
        
        # Wait for all tasks to complete
        for version, task in tasks:
            results[version] = await task
        
        return results


# Convenience functions
async def run_with_progress(coro, description: str = "Operation"):
    """Run coroutine with progress logging."""
    logger = get_logger()
    logger.progress(f"Starting {description}")
    
    try:
        result = await coro
        logger.success(f"Completed {description}")
        return result
    except Exception as e:
        logger.error(f"Failed {description}: {e}")
        raise


def run_async(coro):
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


def get_file_ops():
    """Get file operations for async support."""
    from ..utils.batch_processor import BatchFileProcessor
    return BatchFileProcessor() 