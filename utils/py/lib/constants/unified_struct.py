#!/usr/bin/env python3
"""
Unified Data Structures

Cross-cutting dataclass definitions used across multiple domains in the 
Komodo DeFi Framework documentation tools. These structures provide 
consistent interfaces for common patterns throughout the codebase.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any


# =============================================================================
# UNIFIED DOMAIN - Cross-cutting data structures used across multiple domains
# =============================================================================

@dataclass
class UnifiedMethodInfo:
    """Unified method information structure used across all domains."""
    name: str
    version: str
    description: Optional[str] = None
    category: Optional[str] = None
    parameters: List['UnifiedParameterInfo'] = field(default_factory=list)
    response_parameters: List['UnifiedParameterInfo'] = field(default_factory=list)
    error_types: List['UnifiedErrorInfo'] = field(default_factory=list)
    examples: List['UnifiedExampleInfo'] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Source tracking
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    handler_file: Optional[str] = None
    
    # Metadata
    return_type: Optional[str] = None
    request_type: Optional[str] = None
    related_methods: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class UnifiedParameterInfo:
    """Unified parameter information structure."""
    name: str
    type: str
    required: bool
    description: str = ""
    default_value: Optional[str] = None
    example: Optional[str] = None
    
    # Advanced parameter properties
    location: str = "body"  # body, query, path, header
    enum_values: Optional[List[str]] = None
    enum_reference: Optional[str] = None
    is_object: bool = False
    is_array: bool = False
    nested_params: Optional[List['UnifiedParameterInfo']] = None


@dataclass
class UnifiedErrorInfo:
    """Unified error information structure."""
    name: str
    type: str
    description: str


@dataclass
class UnifiedExampleInfo:
    """Unified example information structure."""
    title: str
    request: Dict[str, Any]
    response: Dict[str, Any]
    description: Optional[str] = None
    example_type: str = "default"
    source_file: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class UnifiedOperationResult:
    """Unified result structure for all operations."""
    success: bool
    operation: str
    message: str = ""
    data: Optional[Any] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: Optional[float] = None
    
    # Context information
    file_path: Optional[str] = None
    method_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)



@dataclass
class UnifiedBatchResult:
    """Unified batch operation result structure."""
    total: int
    successful: int
    failed: int
    results: List[UnifiedOperationResult]
    duration_seconds: float
    operation_type: str
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        return (self.successful / self.total * 100) if self.total > 0 else 0 


@dataclass
class UnifiedRepositoryInfo:
    """Information about a repository structure."""
    root_path: str
    total_files: int
    mdx_files: int
    yaml_files: int
    json_files: int
    directories: List[str]
    last_scan: datetime
    scan_duration: float
    methods: List[str] = field(default_factory=list)