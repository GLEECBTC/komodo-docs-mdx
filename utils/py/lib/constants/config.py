#!/usr/bin/env python3
"""
Enhanced Configuration Management

Centralized configuration system for the Komodo Documentation Library.
Handles paths, settings, and environment-specific configurations.

REFACTORED: Dataclasses moved to data_structures.py. This module now provides
configuration utilities and the global configuration instance.
"""

from typing import Optional
from .enums import DeploymentEnvironment
from .config_struct import EnhancedKomodoConfig


# Global configuration instance
_config_instance: Optional[EnhancedKomodoConfig] = None


def get_config(config_file: Optional[str] = None, base_path: Optional[str] = None,
               environment: DeploymentEnvironment = DeploymentEnvironment.DEVELOPMENT) -> EnhancedKomodoConfig:
    """Get the global configuration instance."""
    global _config_instance
    
    if _config_instance is None:
        _config_instance = EnhancedKomodoConfig(
            environment=environment,
            workspace_root=base_path
        )
    
    return _config_instance


def reset_config() -> None:
    """Reset the global configuration instance."""
    global _config_instance
    _config_instance = None 