import subprocess
from pathlib import Path
from typing import Optional


class GitManager:
    def __init__(self, logger):
        self.logger = logger

    def get_branch_name(self, repo_path: Path) -> str:
        """Gets the current git branch name of a repository."""
        if not repo_path.exists() or not (repo_path / ".git").exists():
            self.logger.warning(f"Git repository not found at '{repo_path}'. Cannot get branch name.")
            return "unknown"
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
            return "unknown"

    def get_commit_hash(self, repo_path: Path) -> Optional[str]:
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

    def switch_branch(self, repo_path: Path, branch_name: str) -> bool:
        """Switches the repository to a different branch."""
        self.logger.info(f"Attempting to switch repository at '{repo_path}' to branch '{branch_name}'...")

        if not repo_path.exists() or not (repo_path / ".git").exists():
            self.logger.error(f"Git repository not found at '{repo_path}'.")
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

            self.logger.success(f"Successfully switched repository at '{repo_path}' to branch '{branch_name}'.")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git command failed: {e.stderr.decode().strip() if e.stderr else e}")
            return False
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while switching branches: {e}")
            return False 