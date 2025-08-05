#!/usr/bin/env python3
"""
Configuration Manager for KDF Tools CLI

This module contains consolidated configuration management separated from the main CLI class
to improve maintainability and reduce the monolithic structure.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from lib.constants import get_config


@dataclass
class CLIConfig:
    """Consolidated configuration for KDF Tools CLI."""
    
    # Core paths
    workspace_root: Path = field(default_factory=lambda: Path.cwd())
    mdx_docs_path: Path = field(default_factory=lambda: Path.cwd() / 'src' / 'pages')
    
    # Git information
    mdx_branch: Optional[str] = None
    mdx_commit: Optional[str] = None
    
    # Verbosity and logging
    verbose: bool = True
    
    # Default values
    default_kdf_branch: str = 'dev'
    default_rpc_password: str = 'RPC_UserP@SSW0RD'
    
    def __post_init__(self):
        """Initialize derived values after object creation."""
        if not self.mdx_branch:
            self.mdx_branch = self._get_git_branch(self.workspace_root)
        if not self.mdx_commit:
            self.mdx_commit = self._get_git_commit(self.workspace_root)
            
    def _get_git_branch(self, repo_path: Path) -> Optional[str]:
        """Get git branch name for a repository."""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
            
    def _get_git_commit(self, repo_path: Path) -> Optional[str]:
        """Get git commit hash for a repository."""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None


class ConfigManager:
    """Manages configuration for KDF Tools CLI."""
    
    def __init__(self):
        self.base_config = get_config()
        self.cli_config = CLIConfig()
        
    def get_workspace_root(self) -> Path:
        """Get the workspace root path."""
        workspace_root = self.base_config.workspace_root or str(Path.cwd())
        return Path(workspace_root)
        
    def get_mdx_docs_path(self) -> Path:
        """Get the MDX docs path."""
        workspace_root = self.get_workspace_root()
        return workspace_root / 'src' / 'pages'
        
    def get_kdf_repo_path(self) -> Path:
        """Get the KDF repository path."""
        return Path(self.base_config.directories.kdf_repo_path) if self.base_config.directories.kdf_repo_path else Path()
        
    def get_docker_dir(self) -> Path:
        """Get the Docker directory path."""
        return Path(self.base_config.directories.docker_dir) if self.base_config.directories.docker_dir else Path()
        
    def get_reports_dir(self) -> Path:
        """Get the reports directory path."""
        return Path(self.base_config.directories.reports_dir) if self.base_config.directories.reports_dir else Path()
        
    def get_data_dir(self) -> Path:
        """Get the data directory path."""
        return Path(self.base_config.directories.data_dir) if self.base_config.directories.data_dir else Path()
        
    def get_postman_json_v1_dir(self) -> Path:
        """Get the Postman JSON V1 directory path."""
        return Path(self.base_config.directories.postman_json_v1) if self.base_config.directories.postman_json_v1 else Path()
        
    def get_postman_json_v2_dir(self) -> Path:
        """Get the Postman JSON V2 directory path."""
        return Path(self.base_config.directories.postman_json_v2) if self.base_config.directories.postman_json_v2 else Path()
        
    def get_mdx_v1_dir(self) -> Path:
        """Get the MDX V1 directory path."""
        return Path(self.base_config.directories.mdx_v1) if self.base_config.directories.mdx_v1 else Path()
        
    def get_mdx_v2_dir(self) -> Path:
        """Get the MDX V2 directory path."""
        return Path(self.base_config.directories.mdx_v2) if self.base_config.directories.mdx_v2 else Path()
        
    def get_test_params_path(self) -> Path:
        """Get the test parameters JSON file path."""
        return Path(self.base_config.directories.test_params_json) if self.base_config.directories.test_params_json else Path()
        
    def get_rust_methods_report_path(self) -> Path:
        """Get the Rust methods report path."""
        return Path(self.base_config.directories.rust_methods_report) if self.base_config.directories.rust_methods_report else Path()
        
    def get_mdx_methods_report_path(self) -> Path:
        """Get the MDX methods report path."""
        return Path(self.base_config.directories.mdx_methods_report) if self.base_config.directories.mdx_methods_report else Path()
        
    def get_mdx_method_paths_report_path(self) -> Path:
        """Get the MDX method paths report path."""
        return Path(self.base_config.directories.mdx_method_paths_report) if self.base_config.directories.mdx_method_paths_report else Path()
        
    def get_mdx_json_example_method_paths_report_path(self) -> Path:
        """Get the MDX JSON example method paths report path."""
        return Path(self.base_config.directories.mdx_json_example_method_paths_report) if self.base_config.directories.mdx_json_example_method_paths_report else Path()
        
    def get_mdx_json_example_methods_report_path(self) -> Path:
        """Get the MDX JSON example methods report path."""
        return Path(self.base_config.directories.mdx_json_example_methods_report) if self.base_config.directories.mdx_json_example_methods_report else Path()
        
    def get_kdf_error_responses_report_path(self) -> Path:
        """Get the KDF error responses report path."""
        return Path(self.base_config.directories.kdf_error_responses_report) if self.base_config.directories.kdf_error_responses_report else Path()
        
    def get_kdf_gap_analysis_report_path(self) -> Path:
        """Get the KDF gap analysis report path."""
        return Path(self.base_config.directories.kdf_gap_analysis_report) if self.base_config.directories.kdf_gap_analysis_report else Path()
        
    def get_branched_reports_dir(self) -> Path:
        """Get the branched reports directory path."""
        return Path(self.base_config.directories.branched_reports_dir) if self.base_config.directories.branched_reports_dir else Path()
        
    def validate_paths(self, logger) -> bool:
        """Validate that all required paths exist."""
        required_paths = [
            ("Workspace root", self.get_workspace_root()),
            ("MDX docs path", self.get_mdx_docs_path()),
            ("Docker directory", self.get_docker_dir()),
            ("Reports directory", self.get_reports_dir()),
            ("Data directory", self.get_data_dir()),
        ]
        
        all_valid = True
        for name, path in required_paths:
            if not path.exists():
                logger.warning(f"Required path does not exist: {name} = {path}")
                all_valid = False
                
        return all_valid
        
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration."""
        return {
            "workspace_root": str(self.get_workspace_root()),
            "mdx_docs_path": str(self.get_mdx_docs_path()),
            "kdf_repo_path": str(self.get_kdf_repo_path()),
            "docker_dir": str(self.get_docker_dir()),
            "reports_dir": str(self.get_reports_dir()),
            "data_dir": str(self.get_data_dir()),
            "postman_json_v1": str(self.get_postman_json_v1_dir()),
            "postman_json_v2": str(self.get_postman_json_v2_dir()),
            "mdx_v1": str(self.get_mdx_v1_dir()),
            "mdx_v2": str(self.get_mdx_v2_dir()),
            "verbose": self.cli_config.verbose,
            "default_kdf_branch": self.cli_config.default_kdf_branch,
        } 