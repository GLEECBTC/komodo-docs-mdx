#!/usr/bin/env python3
"""
Data Structures

Consolidated dataclass definitions for the Komodo DeFi Framework documentation tools.
Organized by domain to eliminate duplication and improve maintainability.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from .enums import FileType

# Import unified structures
from .unified_struct import (
    UnifiedMethodInfo,
    UnifiedParameterInfo,
    UnifiedErrorInfo,
    UnifiedExampleInfo
)


# =============================================================================
# RUST DOMAIN - Rust code analysis and KDF method extraction
# =============================================================================

@dataclass
class RustMethodDetails:
    """Detailed information about a KDF method extracted from Rust code."""
    method_name: str
    handler_file: Optional[str] = None
    parameters: List[UnifiedParameterInfo] = None
    response_type: Optional[str] = None
    description: Optional[str] = None
    examples: List[UnifiedExampleInfo] = None
    errors: List[UnifiedErrorInfo] = None
    request_type: Optional[str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.examples is None:
            self.examples = []
        if self.errors is None:
            self.errors = []


@dataclass
class RustRepositoryInfo:
    """Information about a Rust repository branch and its method extraction."""
    branch: str
    version: str
    url: str
    methods: List[str]
    last_updated: datetime
    commit_hash: Optional[str] = None
    extraction_patterns_used: List[str] = None


@dataclass
class CoinConfig:
    """Configuration for a specific coin from JSON config."""
    coin: str
    name: str
    protocol: Dict[str, Any]
    required_confirmations: int = 1
    requires_notarization: bool = False
    mature_confirmations: int = 0
    nodes: Optional[List[Dict[str, Any]]] = None
    electrum: Optional[List[Dict[str, Any]]] = None
    
    def __post_init__(self):
        if self.nodes is None:
            self.nodes = []
        if self.electrum is None:
            self.electrum = []
    
    @classmethod
    def from_config_dict(cls, coin_ticker: str, config: Dict[str, Any]) -> 'CoinConfig':
        """Create CoinConfig from configuration dictionary."""
        return cls(
            coin=coin_ticker,
            name=config.get('name', coin_ticker),
            protocol=config.get('protocol', {}),
            required_confirmations=config.get('required_confirmations', 1),
            requires_notarization=config.get('requires_notarization', False),
            mature_confirmations=config.get('mature_confirmations', 0),
            nodes=config.get('nodes', []),
            electrum=config.get('electrum', [])
        )
    
    @property
    def protocol_type(self) -> str:
        """Get the protocol type for this coin."""
        if 'type' in self.protocol:
            protocol_type = self.protocol['type']
            # Handle specific protocol mappings
            if protocol_type in ['ERC20', 'ETH', 'BCH', 'UTXO', 'QTUM', 'TENDERMINT', 'ZHTLC']:
                return protocol_type
            # Handle specific coin mappings
            elif protocol_type in ['Bitcoin', 'Litecoin', 'Dogecoin', 'Komodo']:
                return 'UTXO'
            elif protocol_type in ['Ethereum']:
                return 'ETH'
            elif protocol_type in ['BitcoinCash']:
                return 'BCH'
            else:
                return protocol_type
        
        # Fallback based on coin name for common cases
        if self.coin.upper().startswith('ERC20') or 'ERC20' in self.coin.upper():
            return 'ERC20'
        elif self.coin.upper() in ['ETH', 'ETHEREUM']:
            return 'ETH'
        elif self.coin.upper() in ['BCH', 'BITCOINCASH']:
            return 'BCH'
        elif self.coin.upper() in ['BTC', 'BITCOIN', 'LTC', 'LITECOIN', 'DOGE', 'DOGECOIN', 'KMD', 'KOMODO']:
            return 'UTXO'
        elif self.coin.upper() in ['QTUM']:
            return 'QTUM'
        else:
            return 'UNKNOWN'


# =============================================================================
# JSON DOMAIN - JSON processing and data extraction
# =============================================================================

@dataclass
class ExtractedExample:
    """Represents an extracted API example from JSON sources."""
    method_name: str
    version: str
    example_type: str
    content: Dict[str, Any]
    source_file: str
    line_number: Optional[int] = None
    description: Optional[str] = None



# =============================================================================
# FILE SYSTEM DOMAIN - File operations and path management
# =============================================================================

@dataclass
class FileInfo:
    """Information about a file."""
    path: Path
    size: int
    modified: datetime
    file_type: FileType
    exists: bool = True
    
    @classmethod
    def from_path(cls, path: Union[str, Path]) -> 'FileInfo':
        """Create FileInfo from a file path."""
        path = Path(path)
        if not path.exists():
            return cls(
                path=path,
                size=0,
                modified=datetime.min,
                file_type=FileType.UNKNOWN,
                exists=False
            )
        
        stat = path.stat()
        file_type = FileType.UNKNOWN
        
        if path.suffix.lower() == '.json':
            file_type = FileType.JSON
        elif path.suffix.lower() in ['.yaml']:
            file_type = FileType.YAML
        elif path.suffix.lower() == '.mdx':
            file_type = FileType.MDX
        elif path.suffix.lower() == '.txt':
            file_type = FileType.TXT
        
        return cls(
            path=path,
            size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime),
            file_type=file_type
        )


@dataclass
class PathInfo:
    """Information about a path and its components."""
    original_path: str
    normalized_path: str
    is_absolute: bool
    exists: bool
    is_file: bool
    is_directory: bool
    parts: List[str]
    parent: Optional[str] = None
    name: Optional[str] = None
    stem: Optional[str] = None
    suffix: Optional[str] = None


@dataclass
class PathMapping:
    """Complete path mapping for a method with enhanced metadata."""
    method_name: str
    version: str
    mdx_path: str
    category: str
    subcategory: Optional[str] = None
    openapi_path: str = ""
    postman_json_path: str = ""
    postman_collection_path: str = ""
    deprecated: bool = False
    migration_source: Optional[str] = None
    
    # Enhanced metadata
    version_status: Optional[str] = None  # Using str instead of VersionStatus to avoid circular import
    migration_target: Optional[str] = None


# =============================================================================
# SCANNING DOMAIN - File and repository scanning operations
# =============================================================================

@dataclass
class ScanResult:
    """Result from scanning a file or directory."""
    success: bool
    file_path: str
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ScanMetadata:
    """Standardized metadata for various scanning and report generation processes."""
    scanner_type: str
    scanner_version: str
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generated_during: Optional[str] = None # e.g. "mdx_scan", "json_scan", "openapi_scan", "postman_scan", "gap_analysis"
    method_source: Optional[str] = None # e.g. "mdx", "json", "openapi", "postman", "gap_analysis"
    is_primary_data_source: Optional[bool] = None 
    
    # Method counts - can be populated based on the scan type
    # e.g. {"all": 100, "v1": 50, "v2": 50}
    version_method_counts: Optional[Dict[str, int]] = None 
    total_known_methods: Optional[Dict[str, int]] = None
    total_methods_with_mdx_paths: Optional[Dict[str, int]] = None
    total_methods_with_postman_links: Optional[Dict[str, int]] = None
    total_methods_with_json_examples: Optional[Dict[str, int]] = None
    total_methods_with_openapi_paths: Optional[Dict[str, int]] = None
    
    def to_dict(self):
        """Converts the dataclass to a dictionary, excluding None values."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}

# =============================================================================
# ANALYSIS DOMAIN - Analysis and comparison operations
# =============================================================================

@dataclass
class ParameterAnalysis:
    """Analysis of a method parameter."""
    name: str
    type_name: str
    required: bool
    description: Optional[str] = None
    default_value: Optional[Any] = None
    constraints: Optional[Dict[str, Any]] = None


@dataclass
class MethodAnalysis:
    """Complete analysis of a method."""
    method_name: str
    description: Optional[str] = None
    parameters: List[ParameterAnalysis] = field(default_factory=list)
    response_parameters: List[ParameterAnalysis] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """Result of method analysis operation."""
    method_name: str
    success: bool
    info: Optional[UnifiedMethodInfo] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisMetrics:
    """Metrics from analysis operations."""
    total_methods: int
    analyzed_methods: int
    failed_methods: int
    warnings_count: int
    errors_count: int
    analysis_duration: float


@dataclass
class ComparisonResult:
    """Result of comparing two methods or files."""
    item1: str
    item2: str
    similarity_score: float
    differences: List[str]
    is_identical: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# VALIDATION DOMAIN - Validation rules and results
# =============================================================================

@dataclass
class ValidationRule:
    """Represents a validation rule."""
    name: str
    description: str
    severity: str  # 'error', 'warning', 'info'
    pattern: Optional[str] = None
    validator_function: Optional[str] = None
    enabled: bool = True


# =============================================================================
# ASYNC DOMAIN - Asynchronous processing and task management
# =============================================================================

@dataclass
class AsyncTask:
    """Represents an asynchronous task."""
    task_id: str
    task_type: str
    status: str  # 'pending', 'running', 'completed', 'failed'
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: float = 0.0


@dataclass
class ProcessingJob:
    """Represents a processing job with multiple tasks."""
    job_id: str
    job_type: str
    tasks: List[AsyncTask]
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    status: str
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# FACTORY DOMAIN - Factory pattern and creation utilities
# =============================================================================

@dataclass
class FactoryConfig:
    """Configuration for factory methods."""
    enable_caching: bool = True
    cache_size: int = 1000
    validate_inputs: bool = True
    default_encoding: str = "utf-8"
    strict_mode: bool = False


@dataclass
class CreationResult:
    """Result of a factory creation operation."""
    success: bool
    instance: Optional[Any] = None
    error_message: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict) 