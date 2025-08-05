#!/usr/bin/env python3
"""
Async Manager for KDF Tools CLI

This module contains standardized async/await patterns separated from the main CLI class
to improve maintainability and reduce the monolithic structure.
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, Union
from functools import wraps


class AsyncManager:
    """Manages async operations and patterns for KDF Tools CLI."""
    
    def __init__(self, logger):
        self.logger = logger
        
    def run_async_safely(self, coro, timeout: Optional[float] = None) -> Any:
        """
        Safely run an async coroutine with error handling.
        
        Args:
            coro: The coroutine to run
            timeout: Optional timeout in seconds
            
        Returns:
            Any: Result of the coroutine or None if failed
        """
        try:
            if timeout:
                return asyncio.run(asyncio.wait_for(coro, timeout=timeout))
            else:
                return asyncio.run(coro)
        except asyncio.TimeoutError:
            self.logger.error(f"Async operation timed out after {timeout} seconds")
            return None
        except Exception as e:
            self.logger.error(f"Async operation failed: {e}")
            return None
            
    def run_async_with_retry(self, coro, max_retries: int = 3, delay: float = 1.0) -> Any:
        """
        Run an async coroutine with retry logic.
        
        Args:
            coro: The coroutine to run
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            Any: Result of the coroutine or None if all retries failed
        """
        for attempt in range(max_retries + 1):
            try:
                return asyncio.run(coro)
            except Exception as e:
                if attempt < max_retries:
                    self.logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"All {max_retries + 1} attempts failed: {e}")
                    return None
                    
    def run_concurrent_tasks(self, tasks: List[Callable], max_concurrent: int = 5) -> List[Any]:
        """
        Run multiple async tasks concurrently with controlled concurrency.
        
        Args:
            tasks: List of async task functions
            max_concurrent: Maximum number of concurrent tasks
            
        Returns:
            List[Any]: Results from all tasks
        """
        async def run_with_semaphore(semaphore, task):
            async with semaphore:
                return await task()
                
        async def main():
            semaphore = asyncio.Semaphore(max_concurrent)
            coros = [run_with_semaphore(semaphore, task) for task in tasks]
            return await asyncio.gather(*coros, return_exceptions=True)
            
        return self.run_async_safely(main())
        
    def run_async_with_progress(self, coro, description: str = "Processing") -> Any:
        """
        Run an async coroutine with progress indication.
        
        Args:
            coro: The coroutine to run
            description: Description for progress logging
            
        Returns:
            Any: Result of the coroutine
        """
        self.logger.info(f"Starting: {description}")
        start_time = time.time()
        
        result = self.run_async_safely(coro)
        
        elapsed_time = time.time() - start_time
        if result is not None:
            self.logger.info(f"Completed: {description} (took {elapsed_time:.2f}s)")
        else:
            self.logger.error(f"Failed: {description} (took {elapsed_time:.2f}s)")
            
        return result
        
    def create_async_context(self, timeout: Optional[float] = None):
        """
        Create an async context manager for consistent async operations.
        
        Args:
            timeout: Optional timeout for all operations in this context
            
        Returns:
            AsyncContext: Context manager for async operations
        """
        return AsyncContext(self.logger, timeout)


class AsyncContext:
    """Context manager for async operations."""
    
    def __init__(self, logger, timeout: Optional[float] = None):
        self.logger = logger
        self.timeout = timeout
        self.start_time = None
        
    async def __aenter__(self):
        self.start_time = time.time()
        self.logger.info("Starting async context")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        elapsed_time = time.time() - self.start_time
        if exc_type is None:
            self.logger.info(f"Async context completed successfully (took {elapsed_time:.2f}s)")
        else:
            self.logger.error(f"Async context failed: {exc_val} (took {elapsed_time:.2f}s)")
            
    async def run_task(self, coro) -> Any:
        """
        Run a task within this async context.
        
        Args:
            coro: The coroutine to run
            
        Returns:
            Any: Result of the coroutine
        """
        if self.timeout:
            return await asyncio.wait_for(coro, timeout=self.timeout)
        else:
            return await coro


def async_operation(description: str = "Async operation", timeout: Optional[float] = None):
    """
    Decorator for standardizing async operations.
    
    Args:
        description: Description for logging
        timeout: Optional timeout for the operation
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger = None
            # Try to find logger in args or kwargs
            for arg in args:
                if hasattr(arg, 'logger'):
                    logger = arg.logger
                    break
            if logger is None:
                for value in kwargs.values():
                    if hasattr(value, 'logger'):
                        logger = value.logger
                        break
                        
            if logger:
                logger.info(f"Starting: {description}")
                start_time = time.time()
                
                try:
                    if timeout:
                        result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                    else:
                        result = await func(*args, **kwargs)
                        
                    elapsed_time = time.time() - start_time
                    logger.info(f"Completed: {description} (took {elapsed_time:.2f}s)")
                    return result
                except asyncio.TimeoutError:
                    elapsed_time = time.time() - start_time
                    logger.error(f"Timeout: {description} (took {elapsed_time:.2f}s)")
                    raise
                except Exception as e:
                    elapsed_time = time.time() - start_time
                    logger.error(f"Failed: {description} - {e} (took {elapsed_time:.2f}s)")
                    raise
            else:
                # No logger found, run without logging
                if timeout:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                else:
                    return await func(*args, **kwargs)
                    
        return wrapper
    return decorator


def sync_to_async(func):
    """
    Decorator to convert a sync function to async.
    
    Args:
        func: The sync function to convert
        
    Returns:
        Callable: Async version of the function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    return wrapper


def async_to_sync(func):
    """
    Decorator to convert an async function to sync.
    
    Args:
        func: The async function to convert
        
    Returns:
        Callable: Sync version of the function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper 