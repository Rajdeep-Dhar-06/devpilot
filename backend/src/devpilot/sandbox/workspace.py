"""Workspace preparation and git repository operations inside the sandbox.

Combines workspace setup with deterministic git operations (branch creation,
deterministic verification, and push with short-lived token cleanup).
"""

from typing import Any

from devpilot.core.exceptions import BranchVerificationError
from devpilot.domain.workspace import WorkspaceInfo


class Workspace:
    """Manages the cloned repository and git operations inside the sandbox."""

    def __init__(self, sandbox: Any, repo_path: str = "/workspace/repo") -> None:
        self.sandbox = sandbox
        self.repo_path = repo_path

    def _exec(self, command: str, cwd: str | None = None) -> Any:
        return self.sandbox.exec(command, cwd=cwd or self.repo_path)

    def setup(
        self,
        repo_url: str,
        base_branch: str = "main",
    ) -> WorkspaceInfo:
        """Clones the repository and configures git identity."""
        self.sandbox.exec("mkdir -p /workspace")
        self.sandbox.exec(f"git clone {repo_url} {self.repo_path}")
        self._exec(f"git checkout {base_branch}")
        self._exec('git config user.name "DevPilot Agent"')
        self._exec('git config user.email "devpilot-agent@devpilot.ai"')
        return WorkspaceInfo(
            sandbox_id=getattr(self.sandbox, "sandbox_id", ""),
            repo_path=self.repo_path,
            base_branch=base_branch,
        )

    def create_and_checkout_branch(self, branch_name: str) -> None:
        """Creates and switches to a dedicated working branch."""
        res = self._exec(f"git checkout -b {branch_name}")
        if res.exit_code != 0:
            raise RuntimeError(f"Failed to create branch {branch_name}: {res.stderr}")

    def verify_branch(self, expected_branch: str, base_branch: str = "main") -> None:
        """Deterministically verifies branch status and commit/change presence (Decision 16)."""
        res_branch = self._exec("git rev-parse --abbrev-ref HEAD")
        if res_branch.exit_code != 0:
            raise BranchVerificationError(f"Failed to query branch: {res_branch.stderr}")

        current_branch = res_branch.stdout.strip()
        if current_branch != expected_branch:
            raise BranchVerificationError(
                f"Branch mismatch: expected '{expected_branch}' but on '{current_branch}'"
            )

        res_commits = self._exec(f"git rev-list --count {base_branch}..{expected_branch}")
        commits_ahead = 0
        if res_commits.exit_code == 0:
            try:
                commits_ahead = int(res_commits.stdout.strip() or "0")
            except ValueError:
                commits_ahead = 0

        if commits_ahead > 0:
            return

        res_status = self._exec("git status --porcelain")
        if not bool(res_status.stdout.strip()):
            raise BranchVerificationError(
                f"No modifications found on branch '{expected_branch}' compared to '{base_branch}'."
            )

    def commit_changes(self, message: str) -> None:
        """Stages all working directory changes and creates a git commit."""
        self._exec("git add .")
        res = self._exec(f'git commit -m "{message}"')
        if res.exit_code != 0:
            raise RuntimeError(f"Git commit failed: {res.stderr}")

    def push_branch(self, branch_name: str, repo_slug: str, token: str) -> None:
        """Pushes working branch using short-lived token with guaranteed cleanup (Decision 4)."""
        authed_remote = f"https://x-access-token:{token}@github.com/{repo_slug}.git"
        clean_remote = f"https://github.com/{repo_slug}.git"

        self._exec(f"git remote set-url origin {authed_remote}")
        try:
            res = self._exec(f"git push -u origin {branch_name}")
            if res.exit_code != 0:
                raise RuntimeError(f"Git push failed: {res.stderr}")
        finally:
            self._exec(f"git remote set-url origin {clean_remote}")


# Aliases for compatibility
WorkspaceManager = Workspace
GitOps = Workspace
