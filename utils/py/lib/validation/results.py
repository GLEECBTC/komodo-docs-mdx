#!/usr/bin/env python3
"""
Validation Result

Dataclass for storing the results of a validation operation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    data: Optional[Any] = None

    def add_error(self, message: str):
        """Add validation error."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        """Add validation warning."""
        self.warnings.append(message)

    def merge(self, other: 'ValidationResult'):
        """Merge with another validation result."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False 