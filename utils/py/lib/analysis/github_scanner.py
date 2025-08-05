"""
GitHub Scanner for Komodo DeFi Framework Methods

This module scans the KDF repository to find method implementations
and extract parameter information. It leverages the existing repository
scanner infrastructure for efficient access to known handler locations.
"""

import requests
import re
from typing import Dict, List, Optional, Any
import time
from ..rust.scanner import KDFScanner


class GitHubScanner:
    """Scans GitHub repository for method implementations."""
    
    def __init__(self):
        self.repo_owner = "KomodoPlatform"
        self.repo_name = "komodo-defi-framework"
        self.branch = "dev"
        self.base_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        self.search_url = "https://api.github.com/search/code"
        
        # Use existing repository fetcher for handler locations
        self.scanner = KDFScanner(branch=self.branch, verbose=False)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests
        
    def _rate_limit(self):
        """Simple rate limiting to avoid hitting GitHub API limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _github_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a request to GitHub API with rate limiting."""
        self._rate_limit()
        
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                print("GitHub API rate limit exceeded. Please wait or use a personal access token.")
                return None
            else:
                print(f"GitHub API request failed with status {response.status_code}")
                return None
        except requests.RequestException as e:
            print(f"Error making GitHub request: {e}")
            return None
    
    def search_method_in_code(self, method_name: str) -> List[Dict]:
        """Search for method implementation in repository code."""
        results = []
        
        # Try different search patterns
        search_patterns = [
            f'"{method_name}"',  # Exact string match
            f"fn {method_name}",  # Rust function definition
            f"async fn {method_name}",  # Async Rust function
            f"pub fn {method_name}",  # Public Rust function
            f"pub async fn {method_name}",  # Public async Rust function
            method_name.replace("::", "-"),  # Convert :: to _
        ]
        
        for pattern in search_patterns:
            params = {
                "q": f"{pattern} repo:{self.repo_owner}/{self.repo_name}",
                "type": "code"
            }
            
            response = self._github_request(self.search_url, params)
            if response and "items" in response:
                for item in response["items"]:
                    if item not in results:
                        results.append(item)
        
        return results
    
    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get the content of a specific file from the repository."""
        url = f"{self.base_url}/contents/{file_path}"
        params = {"ref": self.branch}
        
        response = self._github_request(url, params)
        if response and "content" in response:
            import base64
            return base64.b64decode(response["content"]).decode('utf-8')
        
        return None
    
    def get_dispatcher_content(self, version: str) -> Optional[str]:
        """Get dispatcher file content using the existing repository scanner."""
        urls = self.scanner.url_templates
        if version not in urls:
            return None
        
        return self.scanner._fetch_remote_content(urls[version])
    
    def extract_method_signature(self, file_content: str, method_name: str) -> Optional[Dict]:
        """Extract method signature from file content."""
        # Convert :: to _ for function name search
        rust_method_name = method_name.replace("::", "-")
        
        # Patterns to match Rust function signatures
        patterns = [
            rf"pub\s+async\s+fn\s+{re.escape(rust_method_name)}\s*\([^)]*\)\s*->[^{{]*\{{",
            rf"async\s+fn\s+{re.escape(rust_method_name)}\s*\([^)]*\)\s*->[^{{]*\{{",
            rf"pub\s+fn\s+{re.escape(rust_method_name)}\s*\([^)]*\)\s*->[^{{]*\{{",
            rf"fn\s+{re.escape(rust_method_name)}\s*\([^)]*\)\s*->[^{{]*\{{",
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, file_content, re.MULTILINE | re.DOTALL)
            for match in matches:
                return {
                    "signature": match.group(0),
                    "start_line": file_content[:match.start()].count('\n') + 1,
                    "method_name": rust_method_name,
                    "original_method_name": method_name
                }
        
        return None
    
    def extract_struct_definition(self, file_content: str, struct_name: str) -> Optional[Dict]:
        """Extract struct definition for request/response parameters."""
        patterns = [
            rf"#\[derive[^\]]*\]\s*pub\s+struct\s+{re.escape(struct_name)}\s*\{{[^}}]*\}}",
            rf"pub\s+struct\s+{re.escape(struct_name)}\s*\{{[^}}]*\}}",
            rf"struct\s+{re.escape(struct_name)}\s*\{{[^}}]*\}}",
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, file_content, re.MULTILINE | re.DOTALL)
            for match in matches:
                return {
                    "definition": match.group(0),
                    "start_line": file_content[:match.start()].count('\n') + 1,
                    "struct_name": struct_name
                }
        
        return None
    
    def find_rpc_handler_in_dispatcher(self, method_name: str, version: str) -> Optional[Dict]:
        """Find RPC handler registration in the dispatcher file."""
        dispatcher_content = self.get_dispatcher_content(version)
        if not dispatcher_content:
            return None
        
        # Look for method registration patterns
        method_patterns = [
            rf'"{re.escape(method_name)}"\s*=>',  # Direct string match in dispatcher
            rf'"{re.escape(method_name)}"',       # String occurrence
        ]
        
        for pattern in method_patterns:
            if re.search(pattern, dispatcher_content):
                return {
                    "file_path": f"mm2src/mm2_main/src/rpc/dispatcher/dispatcher{'_legacy' if version == 'v1' else ''}.rs",
                    "file_content": dispatcher_content,
                    "html_url": self.scanner.url_templates[version],
                    "found_pattern": pattern
                }
        
        return None
    
    def find_rpc_handler(self, method_name: str) -> Optional[Dict]:
        """Find RPC handler registration for the method."""
        # Try both v1 and v2 dispatchers
        for version in ["v1", "v2"]:
            handler_info = self.find_rpc_handler_in_dispatcher(method_name, version)
            if handler_info:
                handler_info["version"] = version
                return handler_info
        
        # Fallback to GitHub API search if not found in dispatchers
        search_patterns = [
            f'"{method_name}"',
            f"RpcHandler::{method_name.replace('::', '_')}",
            f"handle_{method_name.replace('::', '_')}",
        ]
        
        for pattern in search_patterns:
            results = self.search_method_in_code(pattern)
            for result in results:
                if "rpc" in result["path"].lower() or "handler" in result["path"].lower():
                    content = self.get_file_content(result["path"])
                    if content:
                        return {
                            "file_path": result["path"],
                            "file_content": content,
                            "html_url": result["html_url"],
                            "version": "unknown"
                        }
        
        return None
    
    def scan_method(self, method_name: str) -> Dict[str, Any]:
        """Comprehensive scan of a method in the repository."""
        print(f"Scanning GitHub repository for method: {method_name}")
        
        # First, try to find the method in dispatcher files
        handler_info = self.find_rpc_handler(method_name)
        
        # Search for method implementation via GitHub API
        search_results = self.search_method_in_code(method_name)
        
        method_info = {
            "method_name": method_name,
            "search_results": search_results,
            "implementations": [],
            "rpc_handler": handler_info,
            "structs": [],
            "examples": []
        }
        
        # Analyze each search result
        for result in search_results[:5]:  # Limit to first 5 results
            file_content = self.get_file_content(result["path"])
            if file_content:
                # Extract method signature
                signature = self.extract_method_signature(file_content, method_name)
                if signature:
                    method_info["implementations"].append({
                        "file_path": result["path"],
                        "signature": signature,
                        "html_url": result["html_url"]
                    })
                
                # Look for related structs (request/response parameters)
                struct_patterns = [
                    f"{method_name.replace('::', '_').title()}Request",
                    f"{method_name.replace('::', '_').title()}Response", 
                    f"{method_name.replace('::', '_').title()}Params",
                    f"{method_name.replace('::', '_').title()}Result",
                ]
                
                for struct_pattern in struct_patterns:
                    struct_def = self.extract_struct_definition(file_content, struct_pattern)
                    if struct_def:
                        method_info["structs"].append({
                            "file_path": result["path"],
                            "struct_definition": struct_def,
                            "html_url": result["html_url"]
                        })
        
        return method_info 