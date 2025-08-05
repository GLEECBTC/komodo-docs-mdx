#!/usr/bin/env python3
"""
Base classes and data structures for synchronization functionality.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import json
import logging
from dataclasses import dataclass


@dataclass
class RequestData:
    """Standardized request data structure."""
    method: str
    request: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    source_file: Optional[str] = None
    example_index: int = 0
    source: str = 'unknown'
    version: str = 'v2'
    description: Optional[str] = None


@dataclass
class SyncResult:
    """Result of a synchronization operation."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.data is None:
            self.data = {}
    
    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)


class BaseExtractor(ABC):
    """Base class for extracting requests from different sources."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    @abstractmethod
    def extract_requests(self, source_path: Union[str, Path]) -> List[RequestData]:
        """
        Extract requests from the given source.
        
        Args:
            source_path: Path to the source file or directory
            
        Returns:
            List of RequestData objects with standardized format
        """
        pass
    
    def validate_request(self, request: Dict[str, Any]) -> bool:
        """
        Validate a request dictionary.
        
        Args:
            request: Request dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(request, dict):
            return False
        
        # Basic validation - must have method
        if 'method' not in request:
            return False
        
        # Must have request data
        if 'request' not in request:
            return False
        
        return True
    
    def standardize_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize request format for consistent processing.
        
        Args:
            request_data: Raw request data
            
        Returns:
            Standardized request data
        """
        standardized = request_data.copy()
        
        # Ensure userpass is present for v1 methods
        if standardized.get('version') == 'v1':
            if 'userpass' not in standardized['request']:
                standardized['request']['userpass'] = "RPC_UserP@SSW0RD"
        
        # Ensure mmrpc version is present for v2 methods
        if standardized.get('version') == 'v2':
            if 'mmrpc' not in standardized['request']:
                standardized['request']['mmrpc'] = "2.0"
        
        return standardized


class BaseUpdater(ABC):
    """Base class for updating target files with extracted data."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    @abstractmethod
    def update_target(self, target_path: Union[str, Path], data: List[RequestData]) -> bool:
        """
        Update target file with extracted data.
        
        Args:
            target_path: Path to the target file
            data: List of RequestData objects to apply
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    def backup_target(self, target_path: Union[str, Path]) -> Optional[Path]:
        """
        Create a backup of the target file before updating.
        
        Args:
            target_path: Path to the target file
            
        Returns:
            Path to backup file, or None if backup failed
        """
        target_path = Path(target_path)
        if not target_path.exists():
            return None
        
        backup_path = target_path.with_suffix(f"{target_path.suffix}.backup")
        try:
            import shutil
            shutil.copy2(target_path, backup_path)
            self.logger.info(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None 