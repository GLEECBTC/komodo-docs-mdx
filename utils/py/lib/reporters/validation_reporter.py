#!/usr/bin/env python3
"""
This module contains functions for reporting validation results.
"""

from ..validation.results import ValidationResult


def print_codegroup_analysis_report(analysis_result: ValidationResult):
    """
    Prints a formatted report from the result of find_mdx_files_missing_codegroup.
    """
    print("\n--- MDX CodeGroup Analysis Report ---")

    if not analysis_result.data:
        print("No analysis data available.")
        if analysis_result.warnings:
            for warning in analysis_result.warnings:
                print(f"⚠️  Warning: {warning}")
        return
        
    data = analysis_result.data
    total_files = data.get("total_files_scanned", 0)
    files_with_heading = data.get("files_with_method_heading", 0)
    missing_codegroup_files = data.get("files_missing_codegroup", [])
    
    print(f"Total MDX files scanned: {total_files}")
    print(f"Files with a method heading (## method_name): {files_with_heading}")
    
    if analysis_result.is_valid:
        print("\n✅ All applicable files have the required <CodeGroup> tag.")
    else:
        print(f"\n❌ Found {len(missing_codegroup_files)} files missing the <CodeGroup> tag:")
        for file_path in missing_codegroup_files:
            print(f"  - {file_path}")

    if analysis_result.warnings:
        print("\n⚠️ Warnings:")
        for warning in analysis_result.warnings:
            print(f"  - {warning}")
    
    print("\n--- End of Report ---") 