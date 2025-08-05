#!/usr/bin/env python3
"""
Logging Utilities

Centralized logging system for the Komodo Documentation Library.
Provides structured logging with configurable output formats and levels.

FIXED: Circular import issue resolved with dependency injection pattern.
"""

import logging
import sys
from typing import Optional, Dict, Any, Callable
from datetime import datetime


# Global configuration provider - injected at runtime
_config_provider: Optional[Callable] = None


# Custom log levels
SAVE_LEVEL = 25  # Between INFO and WARNING
SUCCESS_LEVEL = 26 # Above SAVE
PROGRESS_LEVEL = 22 # Between INFO and SAVE
SCAN_LEVEL = 23 # Between PROGRESS and SAVE
FETCH_LEVEL = 24 # Between SCAN and SAVE
CLEAN_LEVEL = 21 # Below PROGRESS
DELETE_LEVEL = 29 # Below CLEAN
CONFIG_LEVEL = 19 # Below INFO
FOLDER_LEVEL = 18 # Below CONFIG
START_LEVEL = 27 # Above SUCCESS
FINISH_LEVEL = 28 # Above START

logging.addLevelName(SAVE_LEVEL, "SAVE")
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")
logging.addLevelName(PROGRESS_LEVEL, "PROGRESS")
logging.addLevelName(SCAN_LEVEL, "SCAN")
logging.addLevelName(FETCH_LEVEL, "FETCH")
logging.addLevelName(CLEAN_LEVEL, "CLEAN")
logging.addLevelName(DELETE_LEVEL, "DELETE")
logging.addLevelName(CONFIG_LEVEL, "CONFIG")
logging.addLevelName(FOLDER_LEVEL, "FOLDER")
logging.addLevelName(START_LEVEL, "START")
logging.addLevelName(FINISH_LEVEL, "FINISH")


def set_config_provider(provider: Callable):
    """
    Set the configuration provider function to avoid circular imports.
    
    This should be called during application initialization:
    from lib.constants.config import get_config
    set_config_provider(get_config)
    """
    global _config_provider
    _config_provider = provider


def _get_config():
    """Get configuration using injected provider, with sensible defaults."""
    if _config_provider is None:
        # Return sensible defaults if no config provider is set
        from types import SimpleNamespace
        default_logging = SimpleNamespace(
            emoji_output=True,
            log_file=None,
            quiet=False,
            verbose=True,
            progress_indicators=True
        )
        return SimpleNamespace(logging=default_logging)
    
    return _config_provider()


class EmojiFormatter(logging.Formatter):
    """Custom formatter that adds emoji indicators for different log levels."""
    
    EMOJI_MAP = {
        'DEBUG': '🐛 ',
        'INFO': '› ',
        'WARNING': '⚠️  ',
        'ERROR': '❌ ',
        'CRITICAL': '🚨 ',
        'SUCCESS': '✅ ',
        'START': '🚀 ',
        'FINISH': '🏁 ',
        'PROGRESS': '› ',
        'SAVE': '💾 ',
        'SCAN': '🔍 ',
        'FETCH': '📡 ',
        'CLEAN': '🧹 ',
        'CONFIG': '🔧 ',
        'FOLDER': '📁 ',
        'SKIP': '⏭️  ',
        'DELETE': '🗑️  ',
        'UPDATE': '🔄 '
    }
    
    def __init__(self, fmt=None, emoji_enabled: bool = True):
        super().__init__(fmt)
        self.emoji_enabled = emoji_enabled
    
    def format(self, record):
        # Add emoji if enabled and message is not empty
        if self.emoji_enabled and record.msg and record.msg.strip():
            # Use levelname for emoji mapping
            emoji = self.EMOJI_MAP.get(record.levelname, '')
            if emoji and not record.msg.startswith(emoji.strip()):
                record.msg = f"{emoji}{record.msg}"
        
        return super().format(record)


class KomodoLogger:
    """
    Centralized logger for the Komodo Documentation Library.
    
    IMPROVED: Fixed circular imports and added dependency injection.
    """
    
    _instances: Dict[str, 'KomodoLogger'] = {}
    
    def __new__(cls, name: str = "komodo-lib", **kwargs):
        """Singleton pattern per logger name."""
        if name not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[name] = instance
        return cls._instances[name]
    
    def __init__(self, name: str = "komodo-lib", config_provider: Optional[Callable] = None):
        # Avoid re-initialization of singleton
        if hasattr(self, '_initialized'):
            return
            
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False  # Prevent duplicate logging
        
        # Use injected config provider or global one
        if config_provider:
            self._config_provider = config_provider
        else:
            self._config_provider = _config_provider
        
        # Custom log levels are now defined globally
        
        # Setup handlers
        self._setup_handlers()
        self._initialized = True
    
    def _get_config_values(self):
        """Get config values with fallbacks."""
        try:
            config = self._config_provider() if self._config_provider else _get_config()
            return (
                getattr(config.logging, 'emoji_output', True),
                getattr(config.logging, 'log_file', None),
                getattr(config.logging, 'quiet', False),
                getattr(config.logging, 'verbose', True),
                getattr(config.logging, 'progress_indicators', True)
            )
        except Exception:
            # Fallback to defaults if config access fails
            return True, None, False, True, True
    
    def _setup_handlers(self):
        """Setup logging handlers based on configuration."""
        # Prevent duplicate handlers
        if self.logger.handlers:
            self.logger.handlers.clear()
            
        emoji_output, log_file, quiet, verbose, progress_indicators = self._get_config_values()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_level = self._get_console_level(quiet, verbose)
        console_handler.setLevel(console_level)
        
        # Format setup
        console_formatter = EmojiFormatter('%(message)s', emoji_enabled=emoji_output)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if configured)
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                self.logger.warning(f"Failed to setup file logging: {e}")
    
    def _get_console_level(self, quiet: bool, verbose: bool) -> int:
        """Determine console logging level based on configuration."""
        if quiet:
            return logging.WARNING
        elif verbose:
            return logging.DEBUG
        else:
            return logging.INFO
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(message, extra=kwargs)
    
    def success(self, message: str, **kwargs):
        """Log success message."""
        self.logger.log(SUCCESS_LEVEL, message, extra=kwargs)
    
    def save(self, message: str, **kwargs):
        """Log save message."""
        self.logger.log(SAVE_LEVEL, message, extra=kwargs)

    def scan(self, message: str, **kwargs):
        """Log scan message."""
        self.logger.log(SCAN_LEVEL, message, extra=kwargs)

    def fetch(self, message: str, **kwargs):
        """Log fetch message."""
        self.logger.log(FETCH_LEVEL, message, extra=kwargs)

    def clean(self, message: str, **kwargs):
        """Log clean message."""
        self.logger.log(CLEAN_LEVEL, message, extra=kwargs)

    def delete(self, message: str, **kwargs):
        """Log delete message."""
        self.logger.log(DELETE_LEVEL, message, extra=kwargs)

    def config(self, message: str, **kwargs):
        """Log config message."""
        self.logger.log(CONFIG_LEVEL, message, extra=kwargs)

    def folder(self, message: str, **kwargs):
        """Log folder message."""
        self.logger.log(FOLDER_LEVEL, message, extra=kwargs)

    def start(self, message: str, **kwargs):
        """Log start message."""
        self.logger.log(START_LEVEL, message, extra=kwargs)

    def finish(self, message: str, **kwargs):
        """Log finish message."""
        self.logger.log(FINISH_LEVEL, message, extra=kwargs)

    def progress(self, message: str, **kwargs):
        """Log progress message."""
        config = _get_config()
        if config.logging.progress_indicators:
            self.logger.log(PROGRESS_LEVEL, message, extra=kwargs)
    
    def file_operation(self, operation: str, file_path: str, success: bool = True, **kwargs):
        """Log file operation with standardized format."""
        action = "completed" if success else "failed"
        log_method = self.success if success else self.error
        
        message = f"File {operation} {action}: {file_path}"
        if operation.lower() == 'save' and success:
            self.save(message, **kwargs)
        elif operation.lower() == 'delete' and success:
            self.delete(message, **kwargs)
        else:
            log_method(message, **kwargs)

    def method_operation(self, method_name: str, operation: str, details: str = "", **kwargs):
        """Log method-specific operations."""
        message = f"Method '{method_name}': {operation}"
        if details:
            message += f" - {details}"
        self.info(message, **kwargs)
    
    def stats(self, title: str, stats: Dict[str, Any]):
        """Log statistics in a formatted way."""
        self.info(f"📊 {title}")
        for key, value in stats.items():
            self.info(f"   {key}: {value}")
    
    def separator(self, title: str = ""):
        """Log a visual separator."""
        if title:
            self.info(f"\n{'='*50}")
            self.info(title)
            self.info('='*50)
        else:
            self.info('-'*30)


# Global logger instances - use weak references to avoid memory leaks
_loggers: Dict[str, KomodoLogger] = {}


def get_logger(name: str = "komodo-lib") -> KomodoLogger:
    """Get a logger instance by name."""
    if name not in _loggers:
        _loggers[name] = KomodoLogger(name)
    return _loggers[name]


def setup_logging(log_file: Optional[str] = None, verbose: bool = None, 
                 quiet: bool = None, emoji: bool = None) -> KomodoLogger:
    """
    Setup logging with custom configuration.
    
    Args:
        log_file: Path to log file (optional)
        verbose: Enable verbose logging
        quiet: Enable quiet mode (warnings and errors only)
        emoji: Enable emoji output
        
    Returns:
        Configured logger instance
    """
    config = _get_config()
    
    # Override config if parameters provided
    if log_file is not None:
        config.logging.log_file = log_file
    if verbose is not None:
        config.logging.verbose = verbose
    if quiet is not None:
        config.logging.quiet = quiet
    if emoji is not None:
        config.logging.emoji_output = emoji
    
    # Clear existing loggers to apply new config
    _loggers.clear()
    
    return get_logger()


class ProgressTracker:
    """Helper class for tracking and logging progress of long operations."""
    
    def __init__(self, total: int, operation: str = "Processing", logger: KomodoLogger = None):
        self.total = total
        self.current = 0
        self.operation = operation
        self.logger = logger or get_logger()
        self.start_time = datetime.now()
        
        # Calculate update frequency for performance
        self.update_frequency = max(1, self.total // 3)
        
        self.logger.progress(f"{operation}: Starting ({total} items)")
    
    def update(self, increment: int = 1, message: str = ""):
        """Update progress counter."""
        self.current += increment
        
        # Only log at intervals to avoid spam
        if (self.current % self.update_frequency == 0 or 
            self.current == self.total):
            
            percentage = (self.current / self.total) * 100
            elapsed = datetime.now() - self.start_time
            
            progress_msg = f"{self.operation}: {self.current}/{self.total} ({percentage:.1f}%)"
            if message:
                progress_msg += f" - {message}"
            
            if self.current == self.total:
                progress_msg += f" [Completed in {elapsed.total_seconds():.1f}s]"
            
            self.logger.progress(progress_msg)
    
    def finish(self, message: str = ""):
        """Mark operation as finished."""
        elapsed = datetime.now() - self.start_time
        final_msg = f"{self.operation}: Completed {self.current}/{self.total} in {elapsed.total_seconds():.1f}s"
        if message:
            final_msg += f" - {message}"
        self.logger.success(final_msg)


# Convenience functions for common logging scenarios
def log_file_operation(operation: str, file_path: str, success: bool = True):
    """Quick file operation logging."""
    logger = get_logger()
    logger.file_operation(operation, file_path, success)


def log_method_processing(method_name: str, operation: str, details: str = ""):
    """Quick method processing logging."""
    logger = get_logger()
    logger.method_operation(method_name, operation, details)


def log_stats(title: str, stats: Dict[str, Any]):
    """Quick statistics logging."""
    logger = get_logger()
    logger.stats(title, stats) 