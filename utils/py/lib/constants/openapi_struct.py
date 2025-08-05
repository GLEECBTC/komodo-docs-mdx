#!/usr/bin/env python3
"""
OpenAPI Data Structures

Dataclass definitions for OpenAPI specification management
in the Komodo DeFi Framework documentation tools.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class OpenAPIMethod:
    """Represents a method in the OpenAPI specification."""
    name: str
    summary: str
    mdx_path: str
    openapi_path: str


@dataclass
class PathDetail:
    """Represents a path in the OpenAPI specification."""
    path: str
    method_name: str 