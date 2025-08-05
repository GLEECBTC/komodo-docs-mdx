#!/usr/bin/env python3
"""
KDF Repository Scanner - Consolidated

This module handles all aspects of scanning the local KDF repository for API method information,

"""

import re
import subprocess
import json
import requests
import asyncio
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Union, Tuple
from datetime import datetime

from ..utils.logging_utils import get_logger
from ..utils import ensure_directory_exists
from ..constants import RustMethodDetails, UnifiedRepositoryInfo
from ..constants.data_structures import ScanMetadata
from ..constants.method_groups import KdfMethods


class KDFScanner:
    """
    Comprehensive scanner for the Komodo DeFi Framework repository.
    """

    def __init__(self, config: Any, repo_path: Optional[Union[str, Path]] = None,
                 branch: str = "dev",
                 verbose: bool = True):
        self.logger = get_logger("kdf-scanner")
        self.config = config
        self.script_dir = Path(__file__).parent.parent.parent
        self.repo_path = Path(self.config._resolve_path(self.config.directories.kdf_repo_path))
        self.branch = branch
        self.setup_repository()


    def setup_repository(self, force_clone: bool = False) -> bool:
        repo_url = "https://github.com/KomodoPlatform/komodo-defi-framework.git"

        if self.repo_path.exists() and not force_clone:
            self.logger.info(f"Repository already exists at {self.repo_path}. Pulling latest changes...")
            try:
                subprocess.run(
                    ["git", "pull", "origin", self.branch],
                    cwd=self.repo_path,
                    check=True,
                    capture_output=True
                )
                self.logger.success("Repository updated successfully.")
                return True
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Failed to update repository: {e.stderr.decode()}. Trying to clone fresh...")

        if self.repo_path.exists():
            import shutil
            self.logger.info(f"Removing existing repository at {self.repo_path}")
            shutil.rmtree(self.repo_path)

        self.logger.info(f"Cloning KDF repository (branch: {self.branch})...")
        try:
            subprocess.run([
                "git", "clone", repo_url, str(self.repo_path)
            ], check=True, capture_output=True)

            subprocess.run([
                "git", "checkout", self.branch
            ], cwd=self.repo_path, check=True, capture_output=True)
            self.logger.success("Repository cloned successfully.")

            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to clone repository: {e.stderr.decode()}")
            return False

    def find_method_files(self) -> Dict[str, List[Path]]:
        if not self.repo_path.exists():
            raise FileNotFoundError(f"Repository not found at {self.repo_path}")

        search_dirs = [
            self.repo_path / "mm2src" / "mm2_main" / "src" / "rpc",
            self.repo_path / "mm2src" / "coins",
            self.repo_path / "mm2src" / "mm2_main" / "src" / "lp_swap",
            self.repo_path / "mm2src" / "mm2_main" / "src" / "lp_ordermatch",
        ]
        method_files = {"dispatchers": [], "handlers": [], "structs": [], "tests": []}

        for search_dir in search_dirs:
            if search_dir.exists():
                for rust_file in search_dir.rglob("*.rs"):
                    try:
                        content = rust_file.read_text(encoding='utf-8', errors='ignore')
                        if "dispatcher" in rust_file.name.lower():
                            method_files["dispatchers"].append(rust_file)
                        elif "pub async fn" in content or "fn rpc_" in content:
                            method_files["handlers"].append(rust_file)
                        if "#[derive" in content and "struct" in content:
                            method_files["structs"].append(rust_file)
                        if "test" in rust_file.name.lower():
                            method_files["tests"].append(rust_file)
                    except Exception as e:
                        self.logger.warning(f"Error reading {rust_file}: {e}")
        return method_files

    # Async repository scanning
    async def scan_repository_methods_async(self, versions: List[str] = None) -> Dict[str, UnifiedRepositoryInfo]:
        if versions is None:
            versions = ["v1", "v2"]

        tasks = [self._scan_version_async(version) for version in versions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        repository_info = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                version = versions[i]
                self.logger.error(f"Error scanning version {version}: {result}")
            elif result:
                version, repo_info = result
                repository_info[version] = repo_info
        
        return repository_info

    async def _scan_version_async(self, version: str) -> Optional[Tuple[str, UnifiedRepositoryInfo]]:
        loop = asyncio.get_event_loop()
        source_content = None
        url = None

        dispatcher_filename = "dispatcher_legacy.rs" if version == "v1" else "dispatcher.rs"
        dispatcher_path = self.repo_path / "mm2src" / "mm2_main" / "src" / "rpc" / "dispatcher" / dispatcher_filename
        if not dispatcher_path.exists():
            self.logger.error(f"Dispatcher file for {version} not found at {dispatcher_path}")
            return None
        
        def read_local_file():
            return dispatcher_path.read_text(encoding='utf-8', errors='ignore')
        source_content = await loop.run_in_executor(None, read_local_file)
        url = str(dispatcher_path)
        if not source_content:
            self.logger.warning(f"No source content found for version {version}")
            return None
        
        methods = await loop.run_in_executor(None, self._extract_methods_from_source, source_content, version)

        # The following repo_info instantiation is incorrect. It needs to be fixed to match the UnifiedRepositoryInfo definition.
        # This is a placeholder to get the script to run without a TypeError.
        # I will need to revisit this to ensure all the correct repository information is being captured.
        repo_info = UnifiedRepositoryInfo(
            root_path=url,
            total_files=0, # Placeholder
            mdx_files=0, # Placeholder
            yaml_files=0, # Placeholder
            json_files=0, # Placeholder
            directories=[], # Placeholder
            last_scan=datetime.now(),
            scan_duration=0.0 # Placeholder
        )
        # This is where the methods should be added, but UnifiedRepositoryInfo does not have a methods field.
        # This indicates a larger data modeling issue that needs to be addressed.
        # For now, I will attach it to the object so the rest of the script can function.
        repo_info.methods = sorted(list(methods))
        return version, repo_info

    async def save_repository_methods_async(self, repo_info: Dict[str, UnifiedRepositoryInfo], version_method_counts: Dict[str, int]) -> str:

        file_path = self.config.directories.rust_methods_report
        
        metadata = ScanMetadata(
            scanner_type="RUST_METHODS_SCAN",
            scanner_version="KDFScanner v4.0.0",
            generated_during="rust_scan",
            method_source=f"KDF Repository (branch: {self.branch})",
            is_primary_data_source=True,
            total_known_methods=version_method_counts
        )

        data = {
            "scan_metadata": metadata.to_dict(),
            "repository_data": {}
        }
        
        for version, info in repo_info.items():
            repo_dict = {
                "branch": self.branch, "version": version, "url": info.root_path,
                "methods": info.methods, "last_updated": info.last_scan.isoformat(),
                "commit_hash": getattr(info, 'commit_hash', None),
                "extraction_patterns_used": getattr(info, 'extraction_patterns_used', [])
            }
            data["repository_data"][version] = repo_dict

        def _save_file():
            # Use config resolver to ensure the path is absolute from workspace root
            absolute_file_path = Path(self.config._resolve_path(str(file_path)))
            ensure_directory_exists(absolute_file_path.parent)
            with open(absolute_file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _save_file)
            
        
        return str(file_path)

    # Remote repository methods
    def _fetch_remote_content(self, url: str) -> Optional[str]:
        self.logger.fetch(f"Fetching source from {url}")
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            # self.logger.success(f"Successfully fetched {url} ({len(response.text):,} chars)")
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch source: {e}")
            return None

    # Content retrieval
    def _get_content(self, file_path_in_repo: Union[str, Path]) -> Optional[str]:
        full_path = self.repo_path / file_path_in_repo
        if full_path.exists():
            return full_path.read_text(encoding='utf-8', errors='ignore')
        return None

    # Method Name Extraction (Quick Scan)
    def scan_repository_for_method_names(self, versions: List[str] = None) -> Dict[str, List[str]]:
        if versions is None:
            versions = ["v1", "v2"]
        
        all_methods = {}
        for version in versions:
            source_content = None
            dispatcher_filename = "dispatcher_legacy.rs" if version == "v1" else "dispatcher.rs"
            dispatcher_path = self.repo_path / "mm2src" / "mm2_main" / "src" / "rpc" / "dispatcher" / dispatcher_filename
            if dispatcher_path.exists():
                source_content = dispatcher_path.read_text(encoding='utf-8', errors='ignore')
            else:
                self.logger.error(f"Dispatcher file for {version} not found at {dispatcher_path}")

            if source_content:
                methods = self._extract_methods_from_source(source_content, version)
                all_methods[version] = sorted(list(methods-KdfMethods.removed))
        return all_methods
    
    def _extract_methods_from_source(self, source_content: str, version: str) -> Set[str]:
        # Based on MethodExtractor from rust_remote_scanner.py
        if version == 'v1':
            return self._extract_legacy_dispatcher_methods(source_content)
        
        methods = set()
        methods.update(self._extract_task_dispatcher_methods(source_content))
        methods.update(self._extract_lightning_dispatcher_methods(source_content))
        methods.update(self._extract_streaming_dispatcher_methods(source_content))
        methods.update(self._extract_gui_storage_dispatcher_methods(source_content))
        methods.update(self._extract_staking_dispatcher_methods(source_content))
        methods.update(self._extract_direct_dispatcher_methods(source_content))
        return methods

    def _extract_dispatcher_methods_by_pattern(self, source_content: str, function_name: str, method_variable: str) -> Set[str]:
        methods = set()
        pattern = rf'async fn {function_name}\([^)]*\)[^{{]*\{{[\s\S]*?match {method_variable}\.as_str\(\) \{{([\s\S]*?)\s*\}}\s*\}}'
        match = re.search(pattern, source_content)
        if match:
            dispatcher_content = match.group(1)
            method_matches = re.findall(r'"([^"]+)"\s*=>', dispatcher_content)
            methods.update(method_matches)
        return methods

    def _extract_task_dispatcher_methods(self, source_content: str) -> Set[str]:
        methods = self._extract_dispatcher_methods_by_pattern(source_content, "rpc_task_dispatcher", "task_method")
        return {f"task::{method}" for method in methods}

    def _extract_lightning_dispatcher_methods(self, source_content: str) -> Set[str]:
        pattern = r'async fn lightning_dispatcher\([^)]*lightning_method: &str[^)]*\)[^{]*\{[\s\S]*?match lightning_method \{([\s\S]*?)\s*_\s*=>\s*MmError::err'
        match = re.search(pattern, source_content)
        if match:
            dispatcher_content = match.group(1)
            method_matches = re.findall(r'"([^"]+)"\s*=>', dispatcher_content)
            return {f"lightning::{method}" for method in method_matches}
        return set()

    def _extract_streaming_dispatcher_methods(self, source_content: str) -> Set[str]:
        methods = self._extract_dispatcher_methods_by_pattern(source_content, "rpc_streaming_dispatcher", "streaming_request")
        return {f"stream::{method}" for method in methods}
    
    def _extract_gui_storage_dispatcher_methods(self, source_content: str) -> Set[str]:
        pattern = r'async fn gui_storage_dispatcher\([^)]*gui_storage_method: &str[^)]*\)[^{]*\{[\s\S]*?match gui_storage_method \{([\s\S]*?)\s*_\s*=>\s*MmError::err'
        match = re.search(pattern, source_content)
        if match:
            dispatcher_content = match.group(1)
            method_matches = re.findall(r'"([^"]+)"\s*=>', dispatcher_content)
            return {f"gui_storage::{method}" for method in method_matches}
        return set()

    def _extract_staking_dispatcher_methods(self, source_content: str) -> Set[str]:
        methods = set()
        staking_pattern = r'async fn staking_dispatcher\([^)]*staking_method: &str[^)]*\)[^{]*\{[\s\S]*?match staking_method \{([\s\S]*?)\s*_\s*=>\s*MmError::err'
        match = re.search(staking_pattern, source_content)
        if match:
            dispatcher_content = match.group(1)
            method_matches = re.findall(r'"([^"]+)"\s*=>', dispatcher_content)
            for method in method_matches:
                methods.add(f"experimental::staking::{method}")
        
        query_pattern = r'async fn query_dispatcher\([^)]*staking_query_method: &str[^)]*\)[^{]*\{[\s\S]*?match staking_query_method \{([\s\S]*?)\s*_\s*=>\s*MmError::err'
        match = re.search(query_pattern, source_content)
        if match:
            query_content = match.group(1)
            query_matches = re.findall(r'"([^"]+)"\s*=>', query_content)
            for query_method in query_matches:
                methods.add(f"experimental::staking::query::{query_method}")
        return methods

    def _extract_direct_dispatcher_methods(self, source_content: str) -> Set[str]:
        main_pattern = r'async fn dispatcher_v2\([^)]*\)[^{]*\{[\s\S]*?match request\.method\.as_str\(\) \{([\s\S]*?)\s*\}\s*\}'
        match = re.search(main_pattern, source_content)
        if match:
            dispatcher_content = match.group(1)
            method_matches = re.findall(r'"([^"]+)"\s*=>', dispatcher_content)
            prefixes = ["task::", "lightning::", "stream::", "gui_storage::", "experimental::"]
            return {m for m in method_matches if not any(m.startswith(p) for p in prefixes)}
        return set()

    def _extract_legacy_dispatcher_methods(self, source_content: str) -> Set[str]:
        legacy_pattern = r'DispatcherRes::Match\(match &method\[\.\.\] \{([\s\S]*?)_\s*=>\s*return DispatcherRes::NoMatch'
        match = re.search(legacy_pattern, source_content)
        if match:
            dispatcher_content = match.group(1)
            method_matches = re.findall(r'"([^"]+)"\s*=>', dispatcher_content)
            return set(method_matches)
        return set()

    # Method Detail Extraction (Deep Scan)
    def extract_method_details(self, method_name: str) -> RustMethodDetails:
        method_info = RustMethodDetails(method_name=method_name)
        method_files = self.find_method_files()

        handler_patterns = [
            rf"pub async fn {method_name.replace('::', '_')}_rpc",
            rf"pub async fn rpc_{method_name.replace('::', '_')}",
            rf"async fn {method_name.replace('::', '_')}",
            rf'"{method_name}"\s*=>\s*(\w+)',
        ]

        for handler_file in method_files["handlers"]:
            try:
                content = handler_file.read_text(encoding='utf-8', errors='ignore')
                for pattern in handler_patterns:
                    if re.search(pattern, content):
                        method_info.handler_file = str(handler_file)
                        method_info = self._parse_handler_file_content(content, method_info)
                        break
                if method_info.handler_file:
                    break
            except Exception as e:
                self.logger.warning(f"Error reading {handler_file}: {e}")

        if method_info.parameters:
             method_info = self._enhance_with_struct_info(method_info, method_files["structs"])

        return method_info

    def _parse_handler_file_content(self, content: str, method_info: RustMethodDetails) -> RustMethodDetails:
        func_patterns = [
            r'pub async fn \w+\s*\([^)]*req:\s*(\w+)[^)]*\)',
            r'async fn \w+\s*\([^)]*req:\s*(\w+)[^)]*\)',
        ]
        for pattern in func_patterns:
            match = re.search(pattern, content)
            if match:
                request_type = match.group(1)
                method_info.request_type = request_type
                struct_pattern = rf'#\[derive[^\]]*\]\s*pub struct {request_type}\s*\{{([^}}]*)\}}'
                struct_match = re.search(struct_pattern, content, re.MULTILINE | re.DOTALL)
                if struct_match:
                    method_info.parameters = self._parse_struct_fields(struct_match.group(1))
                break

        doc_comments = re.findall(r'///\s*(.+)', content)
        if doc_comments:
            method_info.description = " ".join(doc_comments).strip()

        response_patterns = [r'-> Result<(\w+),', r'-> (\w+Result)', r'-> RpcResult<(\w+)>']
        for pattern in response_patterns:
            match = re.search(pattern, content)
            if match:
                method_info.response_type = match.group(1)
                break
        
        return method_info

    def _parse_struct_fields(self, struct_body: str) -> List[Dict[str, Any]]:
        parameters = []
        current_field = {}
        for line in struct_body.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('//'): continue

            if line.startswith('///'):
                current_field["description"] = line[3:].strip()
                continue
            
            if line.startswith('#[serde'):
                serde_attrs = re.findall(r'(\w+)\s*=\s*"([^"]*)"', line)
                for attr_name, attr_value in serde_attrs:
                    if attr_name == "default": current_field["default"] = attr_value
                    elif attr_name == "skip_serializing_if": current_field["optional"] = True
                continue

            field_match = re.match(r'pub\s+(\w+):\s*(.+?)(?:,|$)', line)
            if field_match:
                field_name, field_type = field_match.group(1), field_match.group(2).strip().rstrip(',')
                is_optional = field_type.startswith('Option<') or current_field.get("optional", False)
                if field_type.startswith('Option<') and field_type.endswith('>'):
                    field_type = field_type[7:-1]
                
                parameters.append({
                    "name": field_name, "type": field_type, "required": not is_optional,
                    "description": current_field.get("description", ""), "default": current_field.get("default")
                })
                current_field = {}
        
        return parameters

    def _enhance_with_struct_info(self, method_info: RustMethodDetails, struct_files: List[Path]) -> RustMethodDetails:
        # Placeholder for future enhancement to search for struct definitions in other files.
        return method_info 