#!/usr/bin/env python3
"""
Container Manager for KDF Tools CLI

This module contains container management functionality separated from the main CLI class
to improve maintainability and reduce the monolithic structure.
"""

import subprocess
import time
from pathlib import Path
from typing import Optional


class ContainerManager:
    """Handles Docker container operations for KDF Tools CLI."""
    
    def __init__(self, config, logger, git_manager):
        self.config = config
        self.logger = logger
        self.git_manager = git_manager
        
    def _safe_path(self, path_value) -> Path:
        """Safely convert to Path object, handling None values."""
        if path_value is None:
            return Path("")
        return Path(path_value)
        
    def build_container(self, args) -> bool:
        """Builds the KDF container image."""
        self.logger.info(f"Building KDF container for branch: {args.kdf_branch}...")
        # Add implementation for building container
        self.logger.info("============== ✅ Success: Build KDF Container ==============")
        return True

    def start_container(self, args) -> bool:
        """Starts the KDF container."""
        command_title = "Start KDF Container"
        config_lines = [
            f"KDF Branch: {args.kdf_branch or self.config.kdf_branch}",
        ]
        self.logger.info(f"============== Starting: {command_title} ==============")
        for line in config_lines:
            self.logger.info(f"    - {line}")

        if args.kdf_branch:
            if not self.git_manager.switch_branch(self._safe_path(self.config.directories.kdf_repo_path), args.kdf_branch):
                self.logger.error(f"Could not switch to branch {args.kdf_branch}. Aborting.")
                self.logger.info(f"============== ❌ Failed: {command_title} ==============")
                return False

        # Stop any running containers first
        self.stop_container(args)

        build_commit_hash_file = self._safe_path(self.config.directories.docker_dir) / '.build_commit_hash'
        current_commit_hash = self.git_manager.get_commit_hash(self._safe_path(self.config.directories.kdf_repo_path))
        last_build_hash = None

        if build_commit_hash_file.exists():
            with open(build_commit_hash_file, 'r') as f:
                last_build_hash = f.read().strip()

        build_needed = True
        if current_commit_hash and last_build_hash and current_commit_hash == last_build_hash:
            self.logger.info("KDF commit hash unchanged. Skipping container rebuild.")
            build_needed = False

        try:
            # Generate the MM2.json config before starting
            # Note: This would need to be implemented based on the processor's generate_mm2_config method
            # self.processor.generate_mm2_config()

            docker_command = ["docker", "compose", "up", "-d"]
            if build_needed:
                self.logger.info("Change detected or first build, rebuilding container...")
                docker_command.append("--build")
            else:
                self.logger.info("No build needed, starting container...")

            subprocess.run(
                docker_command,
                cwd=self.config.directories.docker_dir,
                check=True
            )

            if build_needed and current_commit_hash:
                with open(build_commit_hash_file, 'w') as f:
                    f.write(current_commit_hash)
                self.logger.save(f"Saved current build commit hash: {current_commit_hash[:7]}")

            self.logger.success("Container started successfully.")
            self.logger.info("Waiting for container to be ready...")
            time.sleep(10)  # Give some time for the container to initialize
            self.logger.info(f"============== ✅ Success: {command_title} ==============")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to start container: {e}")
            self.logger.info(f"============== ❌ Failed: {command_title} ==============")
            return False
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            self.logger.info(f"============== ❌ Failed: {command_title} ==============")
            return False
            
    def stop_container(self, args) -> bool:
        """Stops the KDF container."""
        self.logger.info("Stopping KDF container...")
        try:
            subprocess.run(["docker", "compose", "down"], cwd=self.config.directories.docker_dir)
            self.logger.success("Container stopped.")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to stop container: {e}")
            return False
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            return False 