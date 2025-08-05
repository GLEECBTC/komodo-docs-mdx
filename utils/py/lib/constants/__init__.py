#!/usr/bin/env python3
"""
Constants Package - Static Data and Configuration

This package contains all static data, enums, templates, configuration,
and exceptions used throughout the library. Organized for better maintainability.
"""

# Core enums and constants
from .enums import (
    ValidationLevel, VersionStatus, PathType, FileType, DeploymentEnvironment, EventType, ProcessingStatus,
    DEFAULT_CACHE_TTL, DEFAULT_BATCH_SIZE, DEFAULT_TIMEOUT, DEFAULT_MAX_RETRIES,
    MDX_PATTERNS, JSON_PATTERNS, YAML_PATTERNS, API_VERSIONS, SUPPORTED_EXTENSIONS,
    FILE_PATTERNS, BATCH_SIZES, TIMEOUT_SETTINGS, VALIDATION_RULES
)

# Template definitions
from .templates import ExampleTemplates

# Configuration management
from .config import get_config, reset_config
from .config_struct import (
    CoinConfig,
    DirectoryConfig,
    EnhancedKomodoConfig,
    LoggingConfig,
    OpenAPIConfig,
    ProcessingConfig,
    ValidationConfig,
    VersionConfig,
    VersionMappingConfig
)

# Data structures (consolidated dataclasses)
from .data_structures import (
    
    # Remaining structures in data_structures.py
    RustMethodDetails,
    RustRepositoryInfo,
    ExtractedExample,
    FileInfo,
    PathInfo,
    PathMapping,
    ScanResult,
    ParameterAnalysis,
    MethodAnalysis,
    AnalysisResult,
    AnalysisMetrics,
    ComparisonResult,
    ValidationRule,
    AsyncTask,
    ProcessingJob,
    FactoryConfig,
    CreationResult
)

# Import from unified structures
from .unified_struct import (
    UnifiedMethodInfo,
    UnifiedParameterInfo,
    UnifiedErrorInfo,
    UnifiedExampleInfo,
    UnifiedOperationResult,
    UnifiedBatchResult,
    UnifiedRepositoryInfo
)

# Import from domain-specific structures
from .postman_struct import (
    PostmanRequest,
    PostmanRequestInfo,
    PostmanMethodMapping,
    PostmanFolder
)

from .openapi_struct import (
    OpenAPIMethod,
    PathDetail
)

from .mdx_struct import (
    DocumentSection,
    DocumentationStatus,
    MethodMapping,
    ExistingDocInfo,
    MethodPattern
)

from .drafts_struct import (
    DraftInfo,
    DraftOperation,
    DocumentDifference,
    QualityReport
)

# Exception hierarchy
from .exceptions import (
    KomodoLibraryError, FileOperationError, ValidationError, ParseError,
    ConfigurationError, MethodNotFoundError, PostmanGenerationError,
    OpenAPIError, ExtractionError, DeduplicationError, MappingError,
    raise_file_not_found, raise_invalid_json, raise_method_not_mapped
)

# Configuration functions only (dataclasses are in data_structures)
from .config import get_config, reset_config

# Enums
from .enums import (
    FileType,
    ValidationLevel,
    VersionStatus,
    DeploymentEnvironment,
    PathType,
    EventType,
    ProcessingStatus
)

# Templates
from .templates import ExampleTemplates

__all__ = [
    # Configuration
    'DirectoryConfig',
    'VersionMappingConfig', 
    'VersionConfig',
    'ProcessingConfig',
    'LoggingConfig',
    'ValidationConfig',
    'EnhancedKomodoConfig',
    'get_config',
    'reset_config',
    
    # Enums
    'FileType',
    'ValidationLevel',
    'VersionStatus',
    'DeploymentEnvironment',
    'PathType',
    'EventType',
    'ProcessingStatus',
    
    # Exceptions
    'KomodoLibraryError',
    'FileOperationError', 
    'ValidationError',
    'ParseError',
    'ConfigurationError',
    'MethodNotFoundError',
    'PostmanGenerationError',
    'OpenAPIError',
    'ExtractionError',
    'DeduplicationError',
    'MappingError',
    'raise_file_not_found',
    'raise_invalid_json',
    'raise_method_not_mapped',
    
    # Templates
    'ExampleTemplates',
    
    # Unified structures
    'UnifiedMethodInfo',
    'UnifiedParameterInfo',
    'UnifiedErrorInfo',
    'UnifiedExampleInfo',
    'UnifiedOperationResult',
    'UnifiedBatchResult',
    'UnifiedRepositoryInfo',
    
    # Postman structures
    'PostmanRequest',
    'PostmanRequestInfo',
    'PostmanMethodMapping',
    'PostmanFolder',
    
    # OpenAPI structures and helpers
    'OpenAPIMethod',
    'PathDetail',
    
    # MDX/Documentation structures
    'DocumentSection',
    'DocumentationStatus',
    'MethodMapping',
    'ExistingDocInfo',
    'MethodPattern',
    
    # Drafts structures
    'DraftInfo',
    'DraftOperation',
    'DocumentDifference',
    'QualityReport',
    
    # Remaining data structures
    'RustMethodDetails',
    'RustRepositoryInfo',
    'ExtractedExample',
    'CoinConfig',
    'FileInfo',
    'PathInfo',
    'PathMapping',
    'ScanResult',
    'ParameterAnalysis',
    'MethodAnalysis',
    'AnalysisResult',
    'AnalysisMetrics',
    'ComparisonResult',
    'ValidationRule',
    'AsyncTask',
    'ProcessingJob',
    'FactoryConfig',
    'CreationResult'
] 