#!/usr/bin/env python3
"""
Base Reporter

Provides common functionality and patterns for all reporter classes.
Includes shared utilities for formatting, statistics, and report generation.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging


class BaseReporter(ABC):
    """
    Abstract base class for all reporter implementations.
    Provides common reporting patterns and utilities.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def generate_summary_report(self, *args, **kwargs) -> str:
        """Generate a summary report. Must be implemented by subclasses."""
        pass
    
    def format_header(self, title: str, width: int = 60, char: str = "=") -> str:
        """Format a consistent header for reports."""
        return f"\n{char * width}\n{title}\n{char * width}"
    
    def format_section_header(self, title: str, width: int = 40, char: str = "-") -> str:
        """Format a section header."""
        return f"\n{title}\n{char * width}"
    
    def format_percentage(self, count: int, total: int, decimals: int = 1) -> str:
        """Format a percentage with consistent styling."""
        if total == 0:
            return "(0.0%)"
        pct = (count / total) * 100
        return f"({pct:.{decimals}f}%)"
    
    def format_timestamp(self, timestamp: Optional[datetime] = None) -> str:
        """Format a timestamp for reports."""
        if timestamp is None:
            timestamp = datetime.now()
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def calculate_statistics(self, items: List[Any], key_func=None) -> Dict[str, int]:
        """Calculate basic statistics for a list of items."""
        if not items:
            return {'total': 0, 'unique': 0}
        
        total = len(items)
        if key_func:
            unique = len(set(key_func(item) for item in items))
        else:
            unique = len(set(items))
        
        return {
            'total': total,
            'unique': unique,
            'duplicates': total - unique
        }
    
    def format_list_with_counts(self, items_dict: Dict[str, int], 
                               title: str = "Items", max_items: int = 10) -> List[str]:
        """Format a dictionary of items with counts as a report section."""
        lines = [f"{title}:"]
        
        sorted_items = sorted(items_dict.items(), key=lambda x: x[1], reverse=True)
        
        for i, (item, count) in enumerate(sorted_items):
            if i >= max_items:
                remaining = len(sorted_items) - max_items
                lines.append(f"  ... and {remaining} more items")
                break
            lines.append(f"  {item}: {count}")
        
        return lines
    
    def generate_error_summary(self, errors: List[str]) -> List[str]:
        """Generate a formatted error summary section."""
        if not errors:
            return ["✅ No errors reported"]
        
        lines = [f"❌ {len(errors)} error(s) encountered:"]
        for i, error in enumerate(errors[:10], 1):  # Limit to first 10 errors
            lines.append(f"  {i}. {error}")
        
        if len(errors) > 10:
            lines.append(f"  ... and {len(errors) - 10} more errors")
        
        return lines
    
    def format_coverage_stats(self, have: int, total: int, label: str = "Coverage") -> str:
        """Format coverage statistics with consistent styling."""
        if total == 0:
            return f"{label}: 0/0 (0.0%)"
        
        percentage = (have / total) * 100
        emoji = "✅" if percentage >= 90 else "⚠️" if percentage >= 70 else "❌"
        
        return f"{emoji} {label}: {have}/{total} ({percentage:.1f}%)"
    
    def generate_comparison_table(self, data: Dict[str, Dict[str, Any]], 
                                headers: List[str]) -> List[str]:
        """Generate a simple comparison table."""
        if not data or not headers:
            return ["No data to display"]
        
        lines = []
        
        # Calculate column widths
        widths = {header: len(header) for header in headers}
        for row_data in data.values():
            for header in headers:
                value = str(row_data.get(header, ""))
                widths[header] = max(widths[header], len(value))
        
        # Generate header
        header_line = " | ".join(header.ljust(widths[header]) for header in headers)
        separator = "-|-".join("-" * widths[header] for header in headers)
        
        lines.extend([header_line, separator])
        
        # Generate rows
        for row_name, row_data in data.items():
            row_line = " | ".join(
                str(row_data.get(header, "")).ljust(widths[header]) 
                for header in headers
            )
            lines.append(row_line)
        
        return lines
    
    def log_verbose(self, message: str):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            self.logger.info(message)
    
    def format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.1f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m" 