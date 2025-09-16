#!/usr/bin/env python3
"""
Response processor script for KDF Postman test results.
Processes Newman JSON reports and generates structured response reports
following the existing coin_activation.json format.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


def load_newman_report(file_path: str) -> Optional[Dict]:
    """Load Newman JSON report from file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading Newman report {file_path}: {e}")
        return None


def extract_method_from_request(request: Dict) -> str:
    """Extract the KDF method name from a request."""
    try:
        if 'body' in request and 'raw' in request['body']:
            body = json.loads(request['body']['raw'])
            return body.get('method', 'unknown_method')
    except (json.JSONDecodeError, KeyError):
        pass
    
    # Fallback to request name
    return request.get('name', 'unknown_method')


def format_response_entry(execution: Dict, environment: str, wallet_type: str, timestamp: str) -> Dict:
    """Format a single execution into the expected response format."""
    request = execution.get('request', {})
    response = execution.get('response', {})
    
    method = extract_method_from_request(request)
    
    # Determine success/error status
    is_success = response.get('code', 0) in [200, 201] and not execution.get('assertions', [])
    
    # Parse response body
    response_body = {}
    if 'body' in response:
        try:
            response_body = json.loads(response['body'])
        except json.JSONDecodeError:
            response_body = {"raw_response": response['body']}
    
    # Build the formatted entry
    entry = {
        "title": execution.get('item', {}).get('name', method),
        "notes": f"Environment: {environment}, Wallet: {wallet_type}",
        "json": response_body,
        "metadata": {
            "environment": environment,
            "wallet_type": wallet_type,
            "timestamp": timestamp,
            "method": method,
            "status_code": response.get('code', 0),
            "response_time": response.get('responseTime', 0),
            "request_url": response.get('originalRequest', {}).get('url', {}).get('raw', ''),
            "test_passed": is_success
        }
    }
    
    return entry


def process_newman_report(report_path: str, environment: str, wallet_type: str, timestamp: str) -> Dict[str, Dict]:
    """Process a Newman report and return structured response data."""
    report = load_newman_report(report_path)
    if not report:
        return {}
    
    responses = {}
    
    # Process each execution in the report
    for execution in report.get('run', {}).get('executions', []):
        method = extract_method_from_request(execution.get('request', {}))
        
        if method not in responses:
            responses[method] = {
                "success": [],
                "error": []
            }
        
        entry = format_response_entry(execution, environment, wallet_type, timestamp)
        
        # Categorize as success or error
        if entry["metadata"]["test_passed"]:
            responses[method]["success"].append(entry)
        else:
            responses[method]["error"].append(entry)
    
    return responses


def merge_responses(existing: Dict, new: Dict) -> Dict:
    """Merge new responses into existing response structure."""
    for method, data in new.items():
        if method not in existing:
            existing[method] = {"success": [], "error": []}
        
        existing[method]["success"].extend(data.get("success", []))
        existing[method]["error"].extend(data.get("error", []))
    
    return existing


def load_existing_responses(template_dir: str) -> Dict:
    """Load existing response templates."""
    responses = {}
    
    # Dynamically discover all template files
    template_paths = []
    
    # Add v2 templates
    v2_template_dir = os.path.join(template_dir, "kdf", "v2")
    if os.path.exists(v2_template_dir):
        template_paths.extend([
            os.path.join(v2_template_dir, f) for f in os.listdir(v2_template_dir) 
            if f.endswith('.json')
        ])
    
    # Add legacy templates
    legacy_template_dir = os.path.join(template_dir, "kdf", "legacy")
    if os.path.exists(legacy_template_dir):
        template_paths.extend([
            os.path.join(legacy_template_dir, f) for f in os.listdir(legacy_template_dir) 
            if f.endswith('.json')
        ])
    
    # Add common templates
    common_template_file = os.path.join(template_dir, "kdf", "common.json")
    if os.path.exists(common_template_file):
        template_paths.append(common_template_file)
    
    for path in template_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    template_data = json.load(f)
                    responses.update(template_data)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Warning: Could not load template {path}: {e}")
    
    return responses


def cleanup_old_reports(output_dir: Path) -> None:
    """Remove old report files, keeping only the 2 most recent of each type."""
    import glob
    import os
    
    if not output_dir.exists():
        return
    
    # Define the report patterns to clean up
    patterns = [
        'postman_test_results_*.json',
        'test_summary_*.json'
    ]
    
    for pattern in patterns:
        # Find all files matching this pattern
        files = list(output_dir.glob(pattern))
        
        if len(files) <= 2:
            continue  # Keep all if 2 or fewer
        
        # Sort by modification time (newest first)
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # Keep the 2 most recent, delete the rest
        files_to_keep = files[:2]
        files_to_delete = files[2:]
        
        for old_file in files_to_delete:
            try:
                old_file.unlink()
                print(f"Removed old report: {old_file.name}")
            except OSError as e:
                print(f"Warning: Could not remove {old_file.name}: {e}")


def main():
    parser = argparse.ArgumentParser(description='Process Newman test results into KDF response format')
    parser.add_argument('--input-dir', required=True, help='Directory containing Newman reports')
    parser.add_argument('--output-dir', required=True, help='Directory to write processed reports')
    parser.add_argument('--template-dir', required=True, help='Directory containing response templates')
    parser.add_argument('--timestamp', help='Timestamp for this test run (ISO format)')
    
    args = parser.parse_args()
    
    # Use provided timestamp or generate current one
    timestamp = args.timestamp or datetime.utcnow().isoformat() + 'Z'
    
    # Load existing response templates
    all_responses = load_existing_responses(args.template_dir)
    
    # Process each environment's results
    input_path = Path(args.input_dir)
    
    # Environment mappings based on directory structure
    env_configs = [
        ('native-hd', 'native_hd', 'hd'),
        ('native-nonhd', 'native_iguana', 'iguana'),
    ]
    
    for dir_name, environment, wallet_type in env_configs:
        results_file = input_path / dir_name / 'results.json'
        
        if results_file.exists():
            print(f"Processing {environment} results...")
            new_responses = process_newman_report(
                str(results_file), 
                environment, 
                wallet_type, 
                timestamp
            )
            all_responses = merge_responses(all_responses, new_responses)
        else:
            print(f"Warning: Results file not found: {results_file}")
    
    # Write the consolidated report
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Clean up old reports - keep only the 2 most recent of each type
    cleanup_old_reports(output_path)
    
    report_filename = f"postman_test_results_{timestamp.replace(':', '-').replace('T', '_')}.json"
    output_file = output_path / report_filename
    
    with open(output_file, 'w') as f:
        json.dump(all_responses, f, indent=2)
    
    print(f"Consolidated report written to: {output_file}")
    
    # Also write a summary
    summary = {
        "generated_at": timestamp,
        "environments_tested": len([env for env, _, _ in env_configs]),
        "total_methods": len(all_responses),
        "summary_by_method": {}
    }
    
    for method, data in all_responses.items():
        summary["summary_by_method"][method] = {
            "success_count": len(data.get("success", [])),
            "error_count": len(data.get("error", []))
        }
    
    summary_file = output_path / f"test_summary_{timestamp.replace(':', '-').replace('T', '_')}.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Test summary written to: {summary_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
