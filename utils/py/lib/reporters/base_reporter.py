#!/usr/bin/env python3
"""
Base Reporter

Provides a base class for report generation with common utilities.
"""

class BaseReporter:
    """Base class for reporters providing common formatting utilities."""

    def format_percentage(self, numerator: int, denominator: int) -> str:
        """Formats a fraction as a percentage string."""
        if denominator == 0:
            return "0.0%"
        return f"{(numerator / denominator) * 100:.1f}%"

    def format_header(self, title: str, char: str = "=") -> str:
        """Formats a header section."""
        return f"\n{char * 60}\n{title.upper()}\n{char * 60}"

    def format_section_header(self, title: str, char: str = "-") -> str:
        """Formats a section header."""
        return f"\n{title}:\n{char * (len(title) + 1)}"
    
    def format_coverage_stats(self, count: int, total: int, label: str) -> str:
        """Formats a coverage statistics line."""
        percentage = self.format_percentage(count, total)
        return f"  - {label}: {count}/{total} ({percentage})" 