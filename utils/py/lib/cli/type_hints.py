#!/usr/bin/env python3
"""
Type Hints for KDF Tools CLI

This module contains comprehensive type hints and type checking utilities
separated from the main CLI class to improve maintainability.
"""

from typing import (
    Any, Dict, List, Optional, Union, Tuple, Callable, 
    TypeVar, Generic, Protocol, runtime_checkable
)
from pathlib import Path
from dataclasses import dataclass
from abc import ABC, abstractmethod


# Type variables for generic types
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

# Common type aliases
PathLike = Union[str, Path]
JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
ConfigDict = Dict[str, Any]
LoggerType = Any  # Type for logger objects


@dataclass
class CommandResult:
    """Result of a command execution."""
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None
    exit_code: int = 0


@dataclass
class ScanResult:
    """Result of a scan operation."""
    total_items: int
    processed_items: int
    failed_items: int
    results: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class FileInfo:
    """Information about a file."""
    path: Path
    size: int
    modified_time: float
    content_hash: Optional[str] = None


@dataclass
class MethodInfo:
    """Information about an API method."""
    name: str
    version: str
    description: str
    parameters: List[Dict[str, Any]]
    responses: List[Dict[str, Any]]
    examples: List[Dict[str, Any]]


class ConfigProvider(Protocol):
    """Protocol for configuration providers."""
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        ...
        
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        ...
        
    def has(self, key: str) -> bool:
        """Check if a configuration key exists."""
        ...


class LoggerProvider(Protocol):
    """Protocol for logger providers."""
    
    def info(self, message: str) -> None:
        """Log an info message."""
        ...
        
    def error(self, message: str) -> None:
        """Log an error message."""
        ...
        
    def warning(self, message: str) -> None:
        """Log a warning message."""
        ...
        
    def debug(self, message: str) -> None:
        """Log a debug message."""
        ...


class CommandHandler(Protocol):
    """Protocol for command handlers."""
    
    def __call__(self, args: Any) -> CommandResult:
        """Execute a command."""
        ...


class AsyncCommandHandler(Protocol):
    """Protocol for async command handlers."""
    
    async def __call__(self, args: Any) -> CommandResult:
        """Execute an async command."""
        ...


class FileProcessor(Protocol):
    """Protocol for file processors."""
    
    def process(self, file_path: Path) -> Dict[str, Any]:
        """Process a file."""
        ...


class AsyncFileProcessor(Protocol):
    """Protocol for async file processors."""
    
    async def process(self, file_path: Path) -> Dict[str, Any]:
        """Process a file asynchronously."""
        ...


class Validator(Protocol):
    """Protocol for validators."""
    
    def validate(self, data: Any) -> bool:
        """Validate data."""
        ...
        
    def get_errors(self) -> List[str]:
        """Get validation errors."""
        ...


class Transformer(Protocol):
    """Protocol for data transformers."""
    
    def transform(self, data: T) -> V:
        """Transform data from type T to type V."""
        ...


class CacheProvider(Protocol):
    """Protocol for cache providers."""
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        ...
        
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache."""
        ...
        
    def delete(self, key: str) -> None:
        """Delete a value from cache."""
        ...
        
    def clear(self) -> None:
        """Clear all cache entries."""
        ...


class BaseManager(ABC):
    """Base class for managers."""
    
    def __init__(self, config: ConfigProvider, logger: LoggerProvider):
        self.config = config
        self.logger = logger
        
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the manager."""
        pass
        
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources."""
        pass


class BaseCommand(ABC):
    """Base class for commands."""
    
    def __init__(self, config: ConfigProvider, logger: LoggerProvider):
        self.config = config
        self.logger = logger
        
    @abstractmethod
    def execute(self, args: Any) -> CommandResult:
        """Execute the command."""
        pass
        
    @abstractmethod
    def validate_args(self, args: Any) -> bool:
        """Validate command arguments."""
        pass


class BaseAsyncCommand(ABC):
    """Base class for async commands."""
    
    def __init__(self, config: ConfigProvider, logger: LoggerProvider):
        self.config = config
        self.logger = logger
        
    @abstractmethod
    async def execute(self, args: Any) -> CommandResult:
        """Execute the async command."""
        pass
        
    @abstractmethod
    def validate_args(self, args: Any) -> bool:
        """Validate command arguments."""
        pass


class TypeChecker:
    """Utility class for type checking."""
    
    @staticmethod
    def is_path_like(value: Any) -> bool:
        """Check if value is path-like."""
        return isinstance(value, (str, Path))
        
    @staticmethod
    def is_dict_like(value: Any) -> bool:
        """Check if value is dict-like."""
        return hasattr(value, '__getitem__') and hasattr(value, 'keys')
        
    @staticmethod
    def is_list_like(value: Any) -> bool:
        """Check if value is list-like."""
        return hasattr(value, '__getitem__') and hasattr(value, '__len__')
        
    @staticmethod
    def is_callable(value: Any) -> bool:
        """Check if value is callable."""
        return callable(value)
        
    @staticmethod
    def is_async_callable(value: Any) -> bool:
        """Check if value is an async callable."""
        return callable(value) and hasattr(value, '__await__')


class TypeConverter:
    """Utility class for type conversion."""
    
    @staticmethod
    def to_path(value: PathLike) -> Path:
        """Convert value to Path."""
        return Path(value)
        
    @staticmethod
    def to_dict(value: Any) -> Dict[str, Any]:
        """Convert value to dict."""
        if isinstance(value, dict):
            return value
        elif hasattr(value, '__dict__'):
            return value.__dict__
        else:
            raise ValueError(f"Cannot convert {type(value)} to dict")
            
    @staticmethod
    def to_list(value: Any) -> List[Any]:
        """Convert value to list."""
        if isinstance(value, list):
            return value
        elif hasattr(value, '__iter__'):
            return list(value)
        else:
            return [value]


# Type hints for common function signatures
CommandArgs = Any
CommandResult = CommandResult
ScanResult = ScanResult
FileInfo = FileInfo
MethodInfo = MethodInfo

# Type hints for collections
PathList = List[Path]
StringList = List[str]
DictList = List[Dict[str, Any]]
ConfigDict = Dict[str, Any]
ResultDict = Dict[str, Any]

# Type hints for callables
CommandHandler = Callable[[CommandArgs], CommandResult]
AsyncCommandHandler = Callable[[CommandArgs], CommandResult]
FileProcessor = Callable[[Path], Dict[str, Any]]
AsyncFileProcessor = Callable[[Path], Dict[str, Any]]
Validator = Callable[[Any], bool]
Transformer = Callable[[T], V]

# Type hints for optional values
OptionalPath = Optional[Path]
OptionalString = Optional[str]
OptionalDict = Optional[Dict[str, Any]]
OptionalList = Optional[List[Any]]
OptionalInt = Optional[int]
OptionalFloat = Optional[float]
OptionalBool = Optional[bool] 