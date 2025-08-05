#!/usr/bin/env python3
"""
Postman Reporter - Report generation for Postman collections
"""

from pathlib import Path
from typing import Dict
from ..base.base_reporter import BaseReporter


class PostmanReportGenerator(BaseReporter):
    """
    Generates reports and summaries for Postman collection generation.
    """
    
    def generate_summary_report(self, results: Dict[str, tuple]) -> str:
        """
        Generate a summary report of collection generation results.
        
        Args:
            results: Dictionary mapping versions to (collection_path, env_path) tuples
            
        Returns:
            Formatted summary report
        """
        report_lines = [
            "🎯 Postman Collection Generation Summary",
            "=" * 50,
            ""
        ]
        
        total_collections = 0
        total_environments = 0
        
        for version, (collection_path, env_path) in results.items():
            if collection_path and env_path:
                total_collections += 1
                total_environments += 1
                report_lines.extend([
                    f"✅ {version.upper()} API:",
                    f"    📁 Collection: {Path(collection_path).name}",
                    f"    🌍 Environment: {Path(env_path).name}",
                    ""
                ])
            else:
                report_lines.extend([
                    f"❌ {version.upper()} API: Generation failed",
                    ""
                ])
        
        return "\n".join(report_lines)
    
    def generate_scanning_report(self, scan_results: Dict[str, Dict]) -> str:
        """
        Generate a report of JSON scanning results.
        
        Args:
            scan_results: Dictionary mapping versions to categorized requests
            
        Returns:
            Formatted scanning report
        """
        report_lines = [
            "🔍 JSON Scanning Report",
            "=" * 40,
            ""
        ]
        
        for version, categorized_requests in scan_results.items():
            if not categorized_requests:
                report_lines.extend([
                    f"❌ {version.upper()} API: No JSON examples found",
                    ""
                ])
                continue
            
            total_requests = sum(len(requests) for requests in categorized_requests.values())
            
            report_lines.extend([
                f"📋 {version.upper()} API: {total_requests} requests in {len(categorized_requests)} categories",
                ""
            ])
            
            for category, requests in categorized_requests.items():
                report_lines.append(f"  {category}: {len(requests)} requests")
            
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def generate_file_statistics_report(self, stats: Dict) -> str:
        """
        Generate a report of file statistics.
        
        Args:
            stats: File statistics dictionary
            
        Returns:
            Formatted statistics report
        """
        report_lines = [
            "📊 File Statistics Report",
            "=" * 35,
            ""
        ]
        
        if 'collections' in stats:
            coll_stats = stats['collections']
            report_lines.extend([
                f"📁 Collections:",
                f"   Count: {coll_stats.get('count', 0)}",
                f"   Total Size: {self.format_file_size(coll_stats.get('total_size', 0))}",
                ""
            ])
        
        if 'environments' in stats:
            env_stats = stats['environments']
            report_lines.extend([
                f"🌍 Environments:",
                f"   Count: {env_stats.get('count', 0)}",
                f"   Total Size: {self.format_file_size(env_stats.get('total_size', 0))}",
                ""
            ])
        
        return "\n".join(report_lines) 