#!/usr/bin/env python3
"""
Configuration for synchronization functionality.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import logging

from ..utils.logging_utils import get_logger
from ..constants.config_struct import DirectoryConfig

@dataclass
class SyncConfig:
    """Configuration for bidirectional sync operations, always using DirectoryConfig."""
    directories: DirectoryConfig
    kdf_endpoint: str = "http://localhost:8080"
    kdf_timeout: int = 30
    dry_run: bool = False
    backup_files: bool = True
    validate_requests: bool = True
    verbose: bool = True
    logger: Optional[logging.Logger] = None
    max_concurrent_requests: int = 10
    retry_attempts: int = 3
    retry_delay: float = 1.0

    def __post_init__(self):
        if self.logger is None:
            self.logger = get_logger("sync-config")
        if not isinstance(self.directories, DirectoryConfig):
            raise ValueError("SyncConfig requires a DirectoryConfig instance for 'directories'.")
        self._validate_paths()

    def _validate_paths(self):
        # Example: check that main directories exist
        if not self.directories.mdx_v2.exists():
            self.logger.warning(f"MDX v2 docs path does not exist: {self.directories.mdx_v2}")
        if not self.directories.postman_collections.exists():
            self.logger.warning(f"Postman collections path does not exist: {self.directories.postman_collections}")

    def ensure_directories(self):
        self.directories.mdx_v2.mkdir(parents=True, exist_ok=True)
        self.directories.postman_collections.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'directories': {k: str(v) for k, v in self.directories.__dict__.items()},
            'kdf_endpoint': self.kdf_endpoint,
            'kdf_timeout': self.kdf_timeout,
            'dry_run': self.dry_run,
            'backup_files': self.backup_files,
            'validate_requests': self.validate_requests,
            'verbose': self.verbose,
            'max_concurrent_requests': self.max_concurrent_requests,
            'retry_attempts': self.retry_attempts,
            'retry_delay': self.retry_delay
        }

    @classmethod
    def from_main_config(cls, main_config, **kwargs):
        """Create SyncConfig from the main EnhancedKomodoConfig or similar config object."""
        return cls(directories=main_config.directories, **kwargs)

class ConfigValidator:
    """Validator for sync configuration."""
    @staticmethod
    def validate_config(config: SyncConfig) -> bool:
        errors = []
        if not config.directories.mdx_v2.exists():
            errors.append(f"MDX v2 docs path does not exist: {config.directories.mdx_v2}")
        if not config.directories.postman_collections.exists():
            errors.append(f"Postman collections path does not exist: {config.directories.postman_collections}")
        if not config.kdf_endpoint:
            errors.append("KDF endpoint is required")
        if config.kdf_timeout <= 0:
            errors.append("KDF timeout must be positive")
        if config.max_concurrent_requests <= 0:
            errors.append("Max concurrent requests must be positive")
        if config.retry_attempts < 0:
            errors.append("Retry attempts must be non-negative")
        if config.retry_delay < 0:
            errors.append("Retry delay must be non-negative")
        if errors:
            config.logger.error(f"Configuration validation failed: {errors}")
            return False
        return True 