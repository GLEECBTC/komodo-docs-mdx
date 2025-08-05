#!/usr/bin/env python3
"""
Error Handler for KDF Tools CLI

This module contains standardized error handling patterns separated from the main CLI class
to improve maintainability and reduce the monolithic structure.
"""

import traceback
from typing import Any, Callable, Optional, Union
from pathlib import Path
import json
import asyncio


class ErrorHandler:
    """Standardized error handling for KDF Tools CLI."""
    
    def __init__(self, logger):
        self.logger = logger
        
    def handle_command_execution(self, command_func: Callable, args: Any, command_name: str) -> int:
        """
        Standardized command execution with error handling.
        
        Args:
            command_func: The command function to execute
            args: Command arguments
            command_name: Name of the command for logging
            
        Returns:
            int: Exit code (0 for success, 1 for failure)
        """
        try:
            result = command_func(args)
            if isinstance(result, bool):
                return 0 if result else 1
            elif isinstance(result, int):
                return result
            else:
                return 0
        except KeyboardInterrupt:
            self.logger.error(f"Operation cancelled by user for command: {command_name}")
            return 1
        except Exception as e:
            self.logger.error(f"An error occurred executing command '{command_name}': {e}")
            self.logger.error(traceback.format_exc())
            return 1
            
    def safe_file_operation(self, operation: Callable, *args, **kwargs) -> Optional[Any]:
        """
        Safely execute file operations with standardized error handling.
        
        Args:
            operation: The file operation function to execute
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Optional[Any]: Result of the operation or None if failed
        """
        try:
            return operation(*args, **kwargs)
        except FileNotFoundError as e:
            self.logger.error(f"File not found: {e}")
            return None
        except PermissionError as e:
            self.logger.error(f"Permission denied: {e}")
            return None
        except Exception as e:
            self.logger.error(f"File operation failed: {e}")
            return None
            
    def safe_json_operation(self, operation: Callable, *args, **kwargs) -> Optional[Any]:
        """
        Safely execute JSON operations with standardized error handling.
        
        Args:
            operation: The JSON operation function to execute
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Optional[Any]: Result of the operation or None if failed
        """
        try:
            return operation(*args, **kwargs)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON format: {e}")
            return None
        except Exception as e:
            self.logger.error(f"JSON operation failed: {e}")
            return None
            
    def safe_network_operation(self, operation: Callable, *args, **kwargs) -> Optional[Any]:
        """
        Safely execute network operations with standardized error handling.
        
        Args:
            operation: The network operation function to execute
            *args: Arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Optional[Any]: Result of the operation or None if failed
        """
        try:
            return operation(*args, **kwargs)
        except ConnectionError as e:
            self.logger.error(f"Connection failed: {e}")
            return None
        except TimeoutError as e:
            self.logger.error(f"Operation timed out: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Network operation failed: {e}")
            return None
            
    def validate_path(self, path: Union[str, Path], must_exist: bool = True) -> Optional[Path]:
        """
        Validate a file path with standardized error handling.
        
        Args:
            path: The path to validate
            must_exist: Whether the path must exist
            
        Returns:
            Optional[Path]: Validated Path object or None if invalid
        """
        try:
            path_obj = Path(path)
            if must_exist and not path_obj.exists():
                self.logger.error(f"Path does not exist: {path}")
                return None
            return path_obj
        except Exception as e:
            self.logger.error(f"Invalid path '{path}': {e}")
            return None
            
    def log_error_with_context(self, error: Exception, context: str, command_name: str = ""):
        """
        Log an error with context information.
        
        Args:
            error: The exception that occurred
            context: Context information about what was being done
            command_name: Name of the command being executed
        """
        self.logger.error(f"Error in {command_name}: {context}")
        self.logger.error(f"Exception: {type(error).__name__}: {error}")
        if hasattr(error, '__traceback__'):
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
    def handle_async_error(self, error: Exception, operation_name: str) -> bool:
        """
        Handle errors in async operations.
        
        Args:
            error: The exception that occurred
            operation_name: Name of the async operation
            
        Returns:
            bool: True if error was handled gracefully, False otherwise
        """
        if isinstance(error, asyncio.CancelledError):
            self.logger.info(f"Async operation '{operation_name}' was cancelled")
            return True
        elif isinstance(error, TimeoutError):
            self.logger.error(f"Async operation '{operation_name}' timed out")
            return False
        else:
            self.logger.error(f"Async operation '{operation_name}' failed: {error}")
            return False 