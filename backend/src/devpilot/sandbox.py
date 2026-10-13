"""Sandbox management and workspace git operations inside E2B containers.

Beginner Guide:
The Sandbox is an isolated virtual computer where DevPilot clones the user's
codebase, edits files, and runs tests. All commands and git actions run
safely inside this environment without touching the host machine.
"""

import contextlib
import json
import logging
from dataclasses import dataclass
from typing import Any

import logfire

from devpilot.models import WorkspaceInfo

logger = logging.getLogger(__name__)


@dataclass
class ExecResult:
    """Output of a command executed inside the sandbox."""

    stdout: str
    stderr: str
    exit_code: int


class Sandbox:
    """Manages an active E2B sandbox environment and its workspace repository."""

    def __init__(
        self,
        instance: Any = None,
        sandbox_id: str = "local-sandbox",
        repo_path: str = "/workspace/repo",
    ) -> None:
        self.instance = instance
        self.sandbox_id = sandbox_id
        self.repo_path = repo_path

    @classmethod
    def create(cls, api_key: str = "", timeout_seconds: int = 3600) -> "Sandbox":
        """Spins up a new cloud E2B sandbox instance."""
        from e2b import Sandbox as E2BClient

        kwargs: dict[str, Any] = {"timeout": timeout_seconds}
        if api_key:
            kwargs["api_key"] = api_key

        instance = E2BClient.create(**kwargs)
        sandbox_id = getattr(instance, "sandbox_id", str(id(instance)))
        return cls(instance=instance, sandbox_id=sandbox_id)

    def run(self, command: str, cwd: str | None = None) -> ExecResult:
        """Executes a shell command inside the sandbox."""
        effective_cwd = cwd or self.repo_path
        if self.instance and hasattr(self.instance, "commands"):
            res = self.instance.commands.run(command, cwd=effective_cwd)
            return ExecResult(
                stdout=getattr(res, "stdout", "") or "",
                stderr=getattr(res, "stderr", "") or "",
                exit_code=getattr(res, "exit_code", 0),
            )
        # Mock / fallback runner for testing
        return ExecResult(stdout="", stderr="", exit_code=0)

    def kill(self) -> None:
        """Terminates the sandbox instance to stop billing."""
        if self.instance and hasattr(self.instance, "kill"):
            with contextlib.suppress(Exception):
                self.instance.kill()

    # --- Git & Workspace Operations ---

    def clone(self, repo_url: str, base_branch: str = "main") -> WorkspaceInfo:
        """Clones target repository and sets up initial git identity."""
        self.run("mkdir -p /workspace", cwd="/")
        self.run(f"git clone {repo_url} {self.repo_path}", cwd="/workspace")
        self.run(f"git checkout {base_branch}")
        self.run('git config user.name "DevPilot Agent"')
        self.run('git config user.email "devpilot-agent@devpilot.ai"')

        return WorkspaceInfo(
            sandbox_id=self.sandbox_id,
            repo_path=self.repo_path,
            base_branch=base_branch,
        )

    def create_branch(self, branch_name: str) -> None:
        """Creates and switches to a dedicated feature/fix branch."""
        res = self.run(f"git checkout -b {branch_name}")
        if res.exit_code != 0:
            raise RuntimeError(f"Failed to create branch '{branch_name}': {res.stderr}")

    def verify_branch(self, expected_branch: str, base_branch: str = "main") -> None:
        """Verifies that the branch exists and contains modifications (Decision 16)."""
        current_res = self.run("git rev-parse --abbrev-ref HEAD")
        current_name = current_res.stdout.strip()
        if current_name != expected_branch:
            raise RuntimeError(
                f"Branch mismatch: expected '{expected_branch}' but on '{current_name}'"
            )

        commits_res = self.run(f"git rev-list --count {base_branch}..{expected_branch}")
        try:
            commits_ahead = int(commits_res.stdout.strip() or "0")
        except ValueError:
            commits_ahead = 0

        if commits_ahead > 0:
            return

        status_res = self.run("git status --porcelain")
        has_uncommitted = bool(status_res.stdout.strip())

        if not has_uncommitted:
            raise RuntimeError(
                f"No changes or commits detected on branch '{expected_branch}' "
                f"compared to '{base_branch}'."
            )

    def commit(self, message: str) -> None:
        """Stages all changes and commits them."""
        self.run("git add .")
        res = self.run(f'git commit -m "{message}"')
        if res.exit_code != 0:
            raise RuntimeError(f"Git commit failed: {res.stderr}")

    def push(self, branch_name: str, repo_slug: str, token: str) -> None:
        """Pushes working branch with short-lived token and cleans up (Decision 4)."""
        authed_remote = f"https://x-access-token:{token}@github.com/{repo_slug}.git"
        clean_remote = f"https://github.com/{repo_slug}.git"

        self.run(f"git remote set-url origin {authed_remote}")
        try:
            res = self.run(f"git push -u origin {branch_name}")
            if res.exit_code != 0:
                raise RuntimeError(f"Git push failed: {res.stderr}")
        finally:
            self.run(f"git remote set-url origin {clean_remote}")

    # --- Test & Lint Command Auto-Discovery (Decision 6) ---

    def discover_tests(self) -> dict[str, str | None]:
        """Discovers project test, lint, and typecheck commands from repository manifest."""
        # Check for explicit devpilot.json config first
        cat_cfg = self.run("cat devpilot.json")
        if cat_cfg.exit_code == 0:
            try:
                cfg = json.loads(cat_cfg.stdout)
                return {
                    "test_command": cfg.get("test_command"),
                    "lint_command": cfg.get("lint_command"),
                    "typecheck_command": cfg.get("typecheck_command"),
                    "source": "config",
                }
            except Exception:
                logfire.warn("devpilot.json found but could not be parsed; falling back to auto-detection")
                logger.warning("Failed to parse devpilot.json", exc_info=True)

        # Auto-detect Python pyproject.toml
        cat_pyproject = self.run("cat pyproject.toml")
        if cat_pyproject.exit_code == 0:
            return {
                "test_command": "pytest",
                "lint_command": "ruff check",
                "typecheck_command": "mypy",
                "source": "auto_detected",
            }

        # Auto-detect Node.js package.json
        cat_package = self.run("cat package.json")
        if cat_package.exit_code == 0:
            return {
                "test_command": "npm test",
                "lint_command": "npm run lint",
                "typecheck_command": None,
                "source": "auto_detected",
            }

        return {
            "test_command": None,
            "lint_command": None,
            "typecheck_command": None,
            "source": "not_found",
        }
