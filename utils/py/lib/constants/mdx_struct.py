#!/usr/bin/env python3
"""
MDX/Documentation Data Structures

Dataclass definitions for MDX documentation and content management
in the Komodo DeFi Framework documentation tools.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from .unified_struct import UnifiedParameterInfo


# =============================================================================
# MDX/DOCUMENTATION DOMAIN - MDX documentation and content management
# =============================================================================

@dataclass
class DocumentSection:
    """Represents a section extracted from a document."""
    name: str
    content: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None


@dataclass
class DocumentationStatus:
    """Status information for documentation."""
    method_name: str
    has_mdx: bool
    has_yaml: bool
    has_examples: bool
    last_updated: Optional[datetime] = None
    completeness_score: float = 0.0


@dataclass
class MethodMapping:
    """Represents mapping information for a single method with enhanced metadata."""
    method: str
    mdx_path: Optional[str] = None
    yaml_path: Optional[str] = None
    examples_path: Optional[str] = None
    example_count: int = 0
    
    # Enhanced metadata
    version: Optional[str] = None
    category: Optional[str] = None
    deprecated: bool = False
    
    # Postman collection hotlinks
    postman_collection_info: Optional[Dict] = None
    
    @property
    def has_mdx(self) -> bool:
        return self.mdx_path is not None
    
    @property
    def has_yaml(self) -> bool:
        return self.yaml_path is not None
    
    @property
    def has_examples(self) -> bool:
        return self.examples_path is not None and self.example_count > 0
    
    @property
    def has_postman_links(self) -> bool:
        return self.postman_collection_info is not None
    
    @property
    def is_complete(self) -> bool:
        return self.has_mdx and self.has_yaml and self.has_examples
    
    @property
    def completeness_score(self) -> float:
        """Calculate completeness score (0.0 to 1.0)."""
        score = 0.0
        if self.has_mdx:
            score += 0.35
        if self.has_yaml:
            score += 0.35
        if self.has_examples:
            score += 0.2
        if self.has_postman_links:
            score += 0.1  # Small bonus for Postman integration
        return score


@dataclass
class ExistingDocInfo:
    """Information about existing documentation."""
    file_path: str
    method_name: str
    version: str
    last_modified: datetime
    content_hash: str
    has_examples: bool = False
    parameter_count: int = 0


@dataclass
class MethodPattern:
    """Represents a complete method pattern extracted from existing documentation."""
    method_name: str
    version: str
    parameters: List[UnifiedParameterInfo]
    response_parameters: List[UnifiedParameterInfo]
    error_types: List[str]
    file_path: str 