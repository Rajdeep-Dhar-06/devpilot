"""File system manipulation tools inside the sandbox.

Enforces Decision 19: Delegated workers can only modify files within their declared scope.
"""

from typing import Any

from devpilot.core.exceptions import CommandPolicyViolationError
from devpilot.tools.subagent import WorkerManager


class FileOpsTools:
    """Provides file read and write operations inside the sandbox."""

    def __init__(self, sandbox_provider: Any, worker_manager: WorkerManager | None = None) -> None:
        self.sandbox = sandbox_provider
        self.worker_manager = worker_manager

    def _check_scope(self, file_path: str, worker_id: str | None) -> None:
        """Verifies worker file scope if called in the context of a delegated subagent."""
        if (
            worker_id
            and self.worker_manager
            and not self.worker_manager.is_file_in_scope(worker_id, file_path)
        ):
            raise CommandPolicyViolationError(
                f"Worker '{worker_id}' is not authorized to edit '{file_path}'. "
                "File is outside its declared task scope."
            )

    def read_file(self, sandbox_id: str, file_path: str) -> str:
        """Reads contents of a file inside the sandbox."""
        res = self.sandbox.exec(sandbox_id, f"cat {file_path}")
        if res.exit_code != 0:
            raise FileNotFoundError(f"Failed to read '{file_path}': {res.stderr}")
        return str(res.stdout)

    def write_file(
        self,
        sandbox_id: str,
        file_path: str,
        content: str,
        worker_id: str | None = None,
    ) -> None:
        """Writes content to a file, verifying worker scope permissions."""
        self._check_scope(file_path, worker_id)
        # Ensure parent directory exists
        self.sandbox.exec(sandbox_id, f"mkdir -p $(dirname {file_path})")
        # Write content safely using base64 decoding to avoid quoting problems
        import base64

        b64_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
        res = self.sandbox.exec(sandbox_id, f"echo '{b64_content}' | base64 -d > {file_path}")
        if res.exit_code != 0:
            raise RuntimeError(f"Failed to write '{file_path}': {res.stderr}")

    def replace_in_file(
        self,
        sandbox_id: str,
        file_path: str,
        old_string: str,
        new_string: str,
        worker_id: str | None = None,
    ) -> None:
        """Replaces text in a file inside the sandbox."""
        self._check_scope(file_path, worker_id)
        current = self.read_file(sandbox_id, file_path)
        if old_string not in current:
            raise ValueError(f"Target string not found in '{file_path}'")
        updated = current.replace(old_string, new_string, 1)
        self.write_file(sandbox_id, file_path, updated, worker_id=worker_id)

    def list_directory(self, sandbox_id: str, path: str = ".") -> list[str]:
        """Lists directory entries inside the sandbox."""
        res = self.sandbox.exec(sandbox_id, f"ls -1 {path}")
        if res.exit_code != 0:
            raise RuntimeError(f"Failed to list directory '{path}': {res.stderr}")
        return [line.strip() for line in res.stdout.splitlines() if line.strip()]
