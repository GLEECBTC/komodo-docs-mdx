#!/usr/bin/env python3
"""
Utility Functions for KDF Tools CLI

This module contains utility functions separated from the main CLI class
to improve maintainability and reduce the monolithic structure.
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, List, Union, Optional
from collections import defaultdict

from lib.utils import safe_write_json, ensure_directory_exists
from lib.constants.data_structures import ScanMetadata
from lib.utils.data_utils import sort_version_method_counts


class CLIUtils:
    """Utility functions for KDF Tools CLI."""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        
    def _safe_path(self, path_value: Union[str, Path, None]) -> Path:
        """Safely convert to Path object, handling None values."""
        if path_value is None:
            return Path("")
        return Path(path_value)
        
    def _get_base_scan_metadata(self, kdf_branch: str, git_manager, workspace_root) -> Dict[str, Any]:
        """Returns a base dictionary for scan_metadata."""
        kdf_commit = git_manager.get_commit_hash(self._safe_path(self.config.directories.kdf_repo_path))
        mdx_branch = git_manager.get_branch_name(workspace_root)
        mdx_commit = git_manager.get_commit_hash(workspace_root)
        
        return {
            "kdf_branch": kdf_branch,
            "mdx_branch": mdx_branch,
            "kdf_commit": kdf_commit,
            "mdx_commit": mdx_commit,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        
    def _print_header(self, title: str, config_lines: Optional[List[str]] = None):
        """Prints a standardized command header."""
        self.logger.info("")
        self.logger.start(f"============== Starting: {title} ==============")
        if config_lines:
            self.logger.config("Config:")
            for line in config_lines:
                self.logger.config(f"    - {line}")
        self.logger.info("")

    def _print_footer(self, title: str, success: bool = True, output_paths: Optional[List[str]] = None, report_paths: Optional[List[str]] = None):
        """Prints a standardized command footer."""
        self.logger.info("")
        if success:
            self.logger.finish(f"✅ Success: {title}")
        else:
            self.logger.finish(f"❌ Failed: {title}")

        if output_paths:
            self.logger.info("  Output data paths:")
            for path in output_paths:
                self.logger.info(f"    - {path}")
        if report_paths:
            self.logger.info("  Output report paths:")
            for path in report_paths:
                self.logger.info(f"    - {path}")
        self.logger.info("")
        
    def _get_git_commit_hash(self, repo_path: Path) -> Union[str, None]:
        """Gets the current git commit hash of a repository."""
        if not repo_path.exists() or not (repo_path / ".git").exists():
            self.logger.warning(f"Git repository not found at '{repo_path}'. Cannot get commit hash.")
            return None
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Could not get git commit hash for {repo_path}: {e}")
            return None

    def _get_git_branch_name(self, repo_path: Path) -> Union[str, None]:
        """Gets the current git branch name of a repository."""
        if not repo_path.exists() or not (repo_path / ".git").exists():
            self.logger.warning(f"Git repository not found at '{repo_path}'. Cannot get branch name.")
            return None
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Could not get git branch for {repo_path}: {e}")
            return None
            
    def _switch_kdf_branch(self, branch_name: str, repo_path: Path) -> bool:
        """Switches the KDF repository to a different branch."""
        self.logger.info(f"Attempting to switch KDF repository to branch '{branch_name}'...")

        if not repo_path.exists() or not (repo_path / ".git").exists():
            self.logger.error(f"KDF repository not found at '{repo_path}'.")
            return False

        try:
            # Stash any local changes
            subprocess.run(["git", "stash"], cwd=repo_path, check=True, capture_output=True)

            # Fetch latest changes from origin
            subprocess.run(["git", "fetch", "origin"], cwd=repo_path, check=True, capture_output=True)

            # Check if branch exists locally or remotely
            local_branch_exists = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
                cwd=repo_path, capture_output=True
            ).returncode == 0
            
            remote_branch_exists = subprocess.run(
                ["git", "show-ref", "--verify", f"refs/remotes/origin/{branch_name}"],
                cwd=repo_path, capture_output=True
            ).returncode == 0

            if not local_branch_exists and not remote_branch_exists:
                self.logger.error(f"Branch '{branch_name}' not found locally or on origin.")
                return False

            # Checkout branch (track remote if it doesn't exist locally)
            if not local_branch_exists and remote_branch_exists:
                subprocess.run(["git", "checkout", "--track", f"origin/{branch_name}"], cwd=repo_path, check=True, capture_output=True)
            else:
                subprocess.run(["git", "checkout", branch_name], cwd=repo_path, check=True, capture_output=True)

            # Pull latest changes from the branch
            subprocess.run(["git", "pull", "origin", branch_name], cwd=repo_path, check=True, capture_output=True)

            self.logger.success(f"Successfully switched KDF repository to branch '{branch_name}'.")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git command failed: {e.stderr.decode().strip() if e.stderr else e}")
            return False
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while switching branches: {e}")
            return False
            
    def clean_json_files(self):
        """Removes all request, response, and error JSON files from Postman directories."""
        self.logger.info("Cleaning existing JSON files...")

        postman_dirs = [
            self.config.directories.postman_json_v1,
            self.config.directories.postman_json_v2
        ]

        patterns = ["request_*.json", "response_*.json", "error_*.json"]
        deleted_count = 0

        for p_dir in postman_dirs:
            if not p_dir or not Path(p_dir).exists():
                self.logger.warning(f"Directory not found, skipping clean: {p_dir}")
                continue

            p_dir_path = Path(p_dir)
            self.logger.info(f"Cleaning files in {p_dir_path}...")
            # Use rglob to recursively find files in subdirectories
            for pattern in patterns:
                for file_path in p_dir_path.rglob(pattern):
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except OSError as e:
                        self.logger.error(f"Error deleting file {file_path}: {e}")

        if deleted_count > 0:
            self.logger.success(f"Successfully deleted {deleted_count} JSON files.")
        else:
            self.logger.info("No JSON files found to clean.")
            
    def _create_link_for_api_table(self, method_name: str, file_path_str: str, mdx_docs_path: Path) -> str:
        """Creates a link for the API methods table."""
        doc_path_obj = Path(file_path_str).relative_to(mdx_docs_path)
        doc_path = "/" + doc_path_obj.parent.as_posix()
        slug = self._slugify_for_api_table(method_name)
        escaped_name = method_name.replace('_', '\\_')
        return f"[{escaped_name}]({doc_path}/#{slug})"

    @staticmethod
    def _slugify_for_api_table(text: str) -> str:
        """Converts text to a slug format for API table links."""
        import re
        text = text.split("{{")[0].strip()
        text = re.sub(r'[:_\\s]+', '-', text)
        text = re.sub(r'[^a-zA-Z0-9\\-]', '', text)
        return text.lower() 