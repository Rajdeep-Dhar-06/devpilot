"""Deterministic Git operations inside the sandbox workspace.

Implements:
- Decision 4: Inject short-lived token for push only, with guaranteed cleanup.
- Decision 16: Deterministic branch verification (code, not LLM).
"""

from typing import Any

from devpilot.core.exceptions import BranchVerificationError


class GitOps:
    """Performs git repository operations via sandbox shell commands."""

    def __init__(self, sandbox: Any, repo_path: str) -> None:
        self.sandbox = sandbox
        self.repo_path = repo_path

    def _exec(self, command: str) -> Any:
        return self.sandbox.exec(command, cwd=self.repo_path)

    def create_and_checkout_branch(self, branch_name: str) -> None:
        """Creates and switches to a dedicated working branch."""
        res = self._exec(f"git checkout -b {branch_name}")
        if res.exit_code != 0:
            raise RuntimeError(f"Failed to create branch {branch_name}: {res.stderr}")

    def verify_branch(self, expected_branch: str, base_branch: str = "main") -> None:
        """Deterministically verifies working branch state (Decision 16).

        Ensures:
        1. Current active branch exactly matches expected_branch.
        2. Expected branch has commits ahead of base_branch or unstaged modifications.

        Raises:
            BranchVerificationError: If verification checks fail.
        """
        # Check current active branch
        res_branch = self._exec("git rev-parse --abbrev-ref HEAD")
        if res_branch.exit_code != 0:
            raise BranchVerificationError(
                f"Failed to query current git branch: {res_branch.stderr}"
            )

        current_branch = res_branch.stdout.strip()
        if current_branch != expected_branch:
            raise BranchVerificationError(
                f"Branch mismatch: expected branch '{expected_branch}' "
                f"but currently on '{current_branch}'"
            )

        # Check commit difference against base branch
        res_commits = self._exec(f"git rev-list --count {base_branch}..{expected_branch}")
        commits_ahead = 0
        if res_commits.exit_code == 0:
            try:
                commits_ahead = int(res_commits.stdout.strip() or "0")
            except ValueError:
                commits_ahead = 0

        if commits_ahead > 0:
            return

        # Also check if there are uncommitted working tree changes
        res_status = self._exec("git status --porcelain")
        has_uncommitted_changes = bool(res_status.stdout.strip())

        if not has_uncommitted_changes:
            raise BranchVerificationError(
                f"No modifications found on branch '{expected_branch}' compared to '{base_branch}'."
            )

    def commit_changes(self, message: str) -> None:
        """Stages all working directory changes and creates a git commit."""
        self._exec("git add .")
        res = self._exec(f'git commit -m "{message}"')
        if res.exit_code != 0:
            raise RuntimeError(f"Git commit failed: {res.stderr}")

    def push_branch(
        self,
        branch_name: str,
        repo_slug: str,
        token: str,
    ) -> None:
        """Pushes working branch using short-lived token with guaranteed cleanup (Decision 4)."""
        authed_remote = f"https://x-access-token:{token}@github.com/{repo_slug}.git"
        clean_remote = f"https://github.com/{repo_slug}.git"

        # Inject temporary authenticated remote URL
        self._exec(f"git remote set-url origin {authed_remote}")
        try:
            res = self._exec(f"git push -u origin {branch_name}")
            if res.exit_code != 0:
                raise RuntimeError(f"Git push failed: {res.stderr}")
        finally:
            # Guaranteed cleanup: restore unauthenticated remote URL
            self._exec(f"git remote set-url origin {clean_remote}")
