#!/usr/bin/env python3
"""
Performance Manager for KDF Tools CLI

This module contains performance optimizations including caching, file operations,
and memory management separated from the main CLI class.
"""

import os
import time
import hashlib
import pickle
from pathlib import Path
from typing import Dict, Any, Optional, Union, Callable
from functools import wraps
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""
    data: Any
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl: Optional[int] = None  # Time to live in seconds
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl is None:
            return False
        return datetime.now() - self.created_at > timedelta(seconds=self.ttl)
    
    def update_access(self):
        """Update access metadata."""
        self.accessed_at = datetime.now()
        self.access_count += 1


class CacheManager:
    """Manages caching for improved performance."""
    
    def __init__(self, cache_dir: Optional[Path] = None, max_size: int = 1000):
        self.cache_dir = cache_dir or Path(".cache")
        self.max_size = max_size
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.lock = threading.RLock()
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_cache_key(self, key: str) -> str:
        """Generate a cache key from input."""
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"{key}.cache"
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from cache."""
        cache_key = self._get_cache_key(key)
        
        with self.lock:
            # Check memory cache first
            if cache_key in self.memory_cache:
                entry = self.memory_cache[cache_key]
                if entry.is_expired():
                    del self.memory_cache[cache_key]
                    return default
                entry.update_access()
                return entry.data
            
            # Check file cache
            cache_path = self._get_cache_path(cache_key)
            if cache_path.exists():
                try:
                    with open(cache_path, 'rb') as f:
                        entry = pickle.load(f)
                    if entry.is_expired():
                        cache_path.unlink()
                        return default
                    entry.update_access()
                    # Move to memory cache for faster access
                    self.memory_cache[cache_key] = entry
                    return entry.data
                except Exception:
                    cache_path.unlink(missing_ok=True)
        
        return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache."""
        cache_key = self._get_cache_key(key)
        entry = CacheEntry(data=value, ttl=ttl)
        
        with self.lock:
            # Store in memory cache
            self.memory_cache[cache_key] = entry
            
            # Store in file cache
            cache_path = self._get_cache_path(cache_key)
            try:
                with open(cache_path, 'wb') as f:
                    pickle.dump(entry, f)
            except Exception:
                pass  # File cache is optional
            
            # Cleanup if cache is too large
            if len(self.memory_cache) > self.max_size:
                self._cleanup_cache()
    
    def delete(self, key: str) -> None:
        """Delete a value from cache."""
        cache_key = self._get_cache_key(key)
        
        with self.lock:
            self.memory_cache.pop(cache_key, None)
            cache_path = self._get_cache_path(cache_key)
            cache_path.unlink(missing_ok=True)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            self.memory_cache.clear()
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink(missing_ok=True)
    
    def _cleanup_cache(self) -> None:
        """Remove least recently used entries."""
        if len(self.memory_cache) <= self.max_size:
            return
        
        # Sort by access time and remove oldest
        entries = sorted(
            self.memory_cache.items(),
            key=lambda x: x[1].accessed_at
        )
        
        # Remove oldest entries
        to_remove = len(entries) - self.max_size
        for key, _ in entries[:to_remove]:
            del self.memory_cache[key]


class FileOperationOptimizer:
    """Optimizes file operations for better performance."""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache_manager = cache_manager or CacheManager()
        self.file_stats_cache: Dict[str, Dict[str, Any]] = {}
        
    def read_file_with_cache(self, file_path: Path, ttl: int = 300) -> str:
        """Read a file with caching."""
        cache_key = f"file_content:{file_path}"
        content = self.cache_manager.get(cache_key)
        
        if content is None:
            content = file_path.read_text(encoding='utf-8')
            self.cache_manager.set(cache_key, content, ttl=ttl)
        
        return content
    
    def get_file_stats(self, file_path: Path) -> Dict[str, Any]:
        """Get file statistics with caching."""
        cache_key = f"file_stats:{file_path}"
        stats = self.cache_manager.get(cache_key)
        
        if stats is None:
            stat = file_path.stat()
            stats = {
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'ctime': stat.st_ctime,
                'exists': True
            }
            self.cache_manager.set(cache_key, stats, ttl=60)
        
        return stats
    
    def batch_read_files(self, file_paths: 'list[Path]', max_workers: int = 4) -> 'Dict[Path, str]':
        """Read multiple files in parallel."""
        results = {}
        
        def read_file(path: Path) -> 'tuple[Path, str]':
            try:
                return path, path.read_text(encoding='utf-8')
            except Exception as e:
                return path, f"ERROR: {e}"
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(read_file, path) for path in file_paths]
            for future in futures:
                path, content = future.result()
                results[path] = content
        
        return results
    
    def find_files_parallel(self, directory: Path, pattern: str = "*.py", max_workers: int = 4) -> 'list[Path]':
        """Find files in parallel using multiple threads."""
        def find_files_in_subdir(subdir: Path) -> 'list[Path]':
            try:
                return list(subdir.rglob(pattern))
            except Exception:
                return []
        
        subdirs = [d for d in directory.iterdir() if d.is_dir()]
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(find_files_in_subdir, subdir) for subdir in subdirs]
            all_files = []
            for future in futures:
                all_files.extend(future.result())
        
        return all_files


class MemoryManager:
    """Manages memory usage and garbage collection."""
    
    def __init__(self):
        import gc
        self.gc = gc
        
    def optimize_memory(self) -> Dict[str, Any]:
        """Run memory optimization and return statistics."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        before_memory = process.memory_info().rss
        
        # Force garbage collection
        collected = self.gc.collect()
        
        after_memory = process.memory_info().rss
        memory_freed = before_memory - after_memory
        
        return {
            'objects_collected': collected,
            'memory_freed_bytes': memory_freed,
            'memory_freed_mb': memory_freed / 1024 / 1024,
            'current_memory_mb': after_memory / 1024 / 1024
        }
    
    def monitor_memory_usage(self, threshold_mb: float = 1000.0) -> bool:
        """Monitor memory usage and return True if threshold exceeded."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > threshold_mb:
            self.optimize_memory()
            return True
        
        return False


class PerformanceProfiler:
    """Profiles performance of operations."""
    
    def __init__(self):
        self.profiles: Dict[str, Dict[str, Any]] = {}
        
    def profile(self, name: str):
        """Decorator to profile a function."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                start_memory = self._get_memory_usage()
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                except Exception as e:
                    success = False
                    raise e
                finally:
                    end_time = time.time()
                    end_memory = self._get_memory_usage()
                    
                    duration = end_time - start_time
                    memory_delta = end_memory - start_memory
                    
                    self.profiles[name] = {
                        'duration': duration,
                        'memory_delta': memory_delta,
                        'success': success,
                        'timestamp': datetime.now()
                    }
                
                return result
            return wrapper
        return decorator
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def get_profile_summary(self) -> Dict[str, Any]:
        """Get a summary of all profiles."""
        if not self.profiles:
            return {}
        
        total_duration = sum(p['duration'] for p in self.profiles.values())
        total_memory = sum(p['memory_delta'] for p in self.profiles.values())
        success_count = sum(1 for p in self.profiles.values() if p['success'])
        
        return {
            'total_operations': len(self.profiles),
            'total_duration': total_duration,
            'total_memory_delta_mb': total_memory,
            'success_rate': success_count / len(self.profiles),
            'operations': self.profiles
        }


class AsyncPerformanceOptimizer:
    """Optimizes async operations for better performance."""
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    async def run_with_semaphore(self, coro):
        """Run a coroutine with controlled concurrency."""
        async with self.semaphore:
            return await coro
    
    async def batch_process(self, items: list, processor: Callable, batch_size: int = 10) -> list:
        """Process items in batches with controlled concurrency."""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            tasks = [self.run_with_semaphore(processor(item)) for item in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)
        
        return results
    
    async def process_with_progress(self, items: list, processor: Callable, 
                                  progress_callback: Optional[Callable] = None) -> list:
        """Process items with progress tracking."""
        results = []
        total = len(items)
        
        for i, item in enumerate(items):
            result = await self.run_with_semaphore(processor(item))
            results.append(result)
            
            if progress_callback:
                progress = (i + 1) / total
                progress_callback(progress, i + 1, total)
        
        return results


def performance_monitor(operation_name: Optional[str] = None):
    """Decorator to monitor performance of operations."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = func.__name__ if operation_name is None else operation_name
            start_time = time.time()
            start_memory = _get_memory_usage()
            
            try:
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise e
            finally:
                end_time = time.time()
                end_memory = _get_memory_usage()
                
                duration = end_time - start_time
                memory_delta = end_memory - start_memory
                
                print(f"Performance: {name}")
                print(f"  Duration: {duration:.3f}s")
                print(f"  Memory Delta: {memory_delta:.2f}MB")
                print(f"  Success: {success}")
            
            return result
        return wrapper
    return decorator


def _get_memory_usage() -> float:
    """Get current memory usage in MB."""
    import psutil
    import os
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024 