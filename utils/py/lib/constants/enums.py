"""
Shared Enums and Constants

Centralized location for enums and constants used across multiple modules.
This prevents circular imports by providing a single source of truth for
shared types and constants.
"""

from enum import Enum


class ValidationLevel(Enum):
    """Validation strictness levels."""
    BASIC = "basic"
    NORMAL = "normal"
    STRICT = "strict"
    COMPREHENSIVE = "comprehensive"


class VersionStatus(Enum):
    """Status of API versions."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    LEGACY = "legacy"
    DEVELOPMENT = "development"
    PLANNED = "planned"
    UNKNOWN = "unknown"


class PathType(Enum):
    """Types of paths we generate"""
    MDX = "mdx"
    OPENAPI = "openapi"
    POSTMAN_JSON = "postman_json"
    POSTMAN_COLLECTION = "postman_collection"


class FileType(Enum):
    """Supported file types."""
    JSON = "json"
    YAML = "yaml"
    MDX = "mdx"
    TXT = "txt"
    UNKNOWN = "unknown"


class DeploymentEnvironment(Enum):
    """Supported deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class EventType(Enum):
    """Types of events that can be published"""
    # General events
    OPERATION_STARTED = "operation_started"
    OPERATION_COMPLETED = "operation_completed"
    OPERATION_FAILED = "operation_failed"
    
    # Progress events
    PROGRESS_UPDATE = "progress_update"
    STAGE_CHANGED = "stage_changed"
    
    # File events
    FILE_PROCESSED = "file_processed"
    FILE_SKIPPED = "file_skipped"
    FILE_ERROR = "file_error"
    
    # Validation events
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    VALIDATION_WARNING = "validation_warning"
    
    # Cache events
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_INVALIDATED = "cache_invalidated"
    
    # Custom events
    CUSTOM_EVENT = "custom_event"


class ProcessingStatus(Enum):
    """Status of processing operations"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Common constants
DEFAULT_CACHE_TTL = 3600  # 1 hour
DEFAULT_BATCH_SIZE = 50
DEFAULT_TIMEOUT = 300  # 5 minutes
DEFAULT_MAX_RETRIES = 3

# File patterns
MDX_PATTERNS = ["*.mdx", "**/*.mdx"]
JSON_PATTERNS = ["*.json", "**/*.json"]
YAML_PATTERNS = ["*.yaml", "**/*.yaml"]
FILE_PATTERNS = {
    'mdx': MDX_PATTERNS,
    'json': JSON_PATTERNS,
    'yaml': YAML_PATTERNS
}

# API version configurations
API_VERSIONS = {
    "v1": {
        "status": VersionStatus.LEGACY,
        "base_path": "/api/v1",
        "doc_path": "v1"
    },
    "v2": {
        "status": VersionStatus.ACTIVE,
        "base_path": "/api/v2",
        "doc_path": "v20"
    },
    "v2-dev": {
        "status": VersionStatus.DEVELOPMENT,
        "base_path": "/api/v2-dev",
        "doc_path": "v20-dev"
    }
}

# Common file extensions
SUPPORTED_EXTENSIONS = {
    '.mdx': 'MDX Documentation',
    '.json': 'JSON Data',
    '.yaml': 'YAML Configuration',
    '.py': 'Python Script',
    '.md': 'Markdown Documentation'
}

# Batch sizes for different operations
BATCH_SIZES = {
    'file_processing': DEFAULT_BATCH_SIZE,
    'async_operations': 10,
    'concurrent_requests': 5
}

# Timeout settings for different operations
TIMEOUT_SETTINGS = {
    'file_read': 30,
    'network_request': DEFAULT_TIMEOUT,
    'async_operation': 60
}

# Validation rules
VALIDATION_RULES = {
    'method_name_min_length': 2,
    'method_name_max_length': 100,
    'file_size_limit': 10 * 1024 * 1024,  # 10MB
    'allowed_characters': r'^[a-zA-Z0-9_:.-]+$'
} 