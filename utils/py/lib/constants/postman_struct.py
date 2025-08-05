#!/usr/bin/env python3
"""
Postman Data Structures

Dataclass definitions for Postman collection and request handling
in the Komodo DeFi Framework documentation tools.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any


# =============================================================================
# POSTMAN DOMAIN - Postman collection and request handling
# =============================================================================

@dataclass
class PostmanRequest:
    """Represents a Postman request with all metadata."""
    name: str
    method: str
    url: str
    headers: List[Dict[str, str]]
    body: Dict[str, Any]
    description: str
    tests: str
    method_name: str
    operation: str
    example_description: str


@dataclass
class PostmanRequestInfo:
    """Represents a single request in a Postman collection."""
    name: str
    method_name: str
    folder_path: List[str]
    item_index: int
    description: str
    operation_type: str = "default"


@dataclass
class PostmanMethodMapping:
    """Maps a method name to its Postman collection entries."""
    method_name: str
    collection_file: str
    collection_version: str
    requests: List[PostmanRequestInfo]
    folder_hierarchy: List[str]


@dataclass
class PostmanFolder:
    """Represents a Postman folder containing related requests."""
    name: str
    description: str
    requests: List[PostmanRequest]
    subfolders: List['PostmanFolder'] = field(default_factory=list) 

