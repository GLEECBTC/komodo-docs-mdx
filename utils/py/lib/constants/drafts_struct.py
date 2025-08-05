#!/usr/bin/env python3
"""
Drafts Data Structures

Dataclass definitions for draft document management and quality assurance
in the Komodo DeFi Framework documentation tools.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


# =============================================================================
# DRAFTS DOMAIN - Draft document management and quality assurance
# =============================================================================

@dataclass
class DraftInfo:
    """Information about a draft document."""
    method_name: str
    file_path: str
    created_at: datetime
    last_modified: datetime
    status: str  # 'draft', 'review', 'approved'
    author: Optional[str] = None
    version: str = "v2"


@dataclass
class DraftOperation:
    """Result of a draft operation."""
    operation: str  # 'create', 'update', 'delete', 'publish'
    draft_info: DraftInfo
    success: bool
    message: str
    errors: List[str] = field(default_factory=list)


@dataclass
class DocumentDifference:
    """Represents a difference between generated and live documentation."""
    section: str
    type: str  # 'structure', 'content', 'formatting', 'style'
    severity: str  # 'critical', 'major', 'minor'
    generated_content: str
    live_content: str
    description: str
    line_numbers: Optional[tuple] = None
    suggestions: List[str] = field(default_factory=list)


@dataclass
class QualityReport:
    """Comprehensive quality report comparing generated vs live docs."""
    method_name: str
    generated_file: Path
    live_file: Path
    overall_similarity: float
    differences: List[DocumentDifference] = field(default_factory=list)
    template_issues: List[str] = field(default_factory=list)
    style_violations: List[str] = field(default_factory=list)
    improvement_opportunities: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat()) 