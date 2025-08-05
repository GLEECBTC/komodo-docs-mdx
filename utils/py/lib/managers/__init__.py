#!/usr/bin/env python3
"""
Managers Package - Centralized Management Classes

This package consolidates all manager classes that coordinate complex operations:
- OpenAPIManager: OpenAPI specification management
- PostmanManager: Postman collection and file operations
- ValidationManager: Validation operations
- MethodMappingManager: API method mapping operations
- SimpleComparator: Simple JSON-based method comparison
- MdxGenerator: Generate comprehensive MDX documentation
- DraftsManager: Draft quality analysis and comparison management

Note: MethodMapping data structure moved to constants package.
"""

from ..openapi.openapi_manager import OpenAPIManager
from .validation_manager import ValidationManager
from .method_mapping_manager import MethodMappingManager
from ..mdx.mdx_manager import review_draft_quality, DraftsManager
from ..postman.postman_manager import PostmanManager, PostmanFileManager

from ..mdx.mdx_generator import MdxGenerator

# Import MethodMapping from constants (moved there to avoid circular imports)
from ..constants import MethodMapping

__all__ = [
    # Core managers
    'OpenAPIManager',
    'PostmanManager',
    'PostmanFileManager',
    'ValidationManager',
    'MethodMappingManager',
    
    # Data structures (re-exported for convenience)
    'MethodMapping',
    
    # Documentation generation
    'MdxGenerator',

    # Quality analysis
    'DraftsManager',
    'review_draft_quality',
] 