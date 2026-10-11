"""Sandbox lifecycle management and execution provider.

Implements Decision 13:
- Always-alive sandbox lifecycle per run.
- Timeout extension during paused human-in-the-loop steps.
- Clear error detection (SandboxLostError) if sandbox expires or disconnects.
"""

from dataclasses import dataclass
from typing import Any, Protocol

from devpilot.core.exceptions import SandboxError, SandboxLostError


@dataclass
class ExecResult:
    """Outcome of command execution inside the sandbox."""

    stdout: str
    stderr: str
    exit_code: int


class SandboxProtocol(Protocol):
    """Protocol for sandbox interactions, enabling simple mocking in tests."""

    def exec(self, command: str, cwd: str | None = None) -> ExecResult:
        """Executes a command inside the sandbox."""
        ...


class E2BSandboxProvider:
    """Manages E2B cloud sandbox instances and command execution."""

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key
        self._active_sandboxes: dict[str, Any] = {}

    def create_sandbox(self, timeout_seconds: int = 3600) -> str:
        """Spins up a new E2B sandbox instance.

        Returns:
            sandbox_id: Unique identifier for the created sandbox.
        """
        try:
            from e2b import Sandbox

            kwargs: dict[str, Any] = {"timeout": timeout_seconds}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            sbx = Sandbox.create(**kwargs)
            sandbox_id = getattr(sbx, "sandbox_id", str(id(sbx)))
            self._active_sandboxes[sandbox_id] = sbx
            return sandbox_id
        except Exception as err:
            raise SandboxError(f"Failed to create E2B sandbox: {err}") from err

    def extend_timeout(self, sandbox_id: str, extension_seconds: int = 3600) -> None:
        """Extends timeout for a running sandbox (Decision 13)."""
        sbx = self._active_sandboxes.get(sandbox_id)
        if not sbx:
            raise SandboxLostError(f"Sandbox '{sandbox_id}' not found or already terminated.")

        try:
            if hasattr(sbx, "set_timeout"):
                sbx.set_timeout(extension_seconds)
        except Exception as err:
            raise SandboxLostError(
                f"Failed extending timeout on sandbox '{sandbox_id}'. "
                f"Sandbox may have expired: {err}"
            ) from err

    def kill_sandbox(self, sandbox_id: str) -> None:
        """Kills and terminates an active sandbox instance to stop billing."""
        sbx = self._active_sandboxes.pop(sandbox_id, None)
        if sbx and hasattr(sbx, "kill"):
            import contextlib

            with contextlib.suppress(Exception):
                sbx.kill()

    def exec(self, sandbox_id: str, command: str, cwd: str | None = None) -> ExecResult:
        """Runs a command inside the specified sandbox."""
        sbx = self._active_sandboxes.get(sandbox_id)
        if not sbx:
            raise SandboxLostError(f"Sandbox '{sandbox_id}' is not available.")

        try:
            res = sbx.commands.run(command, cwd=cwd)
            return ExecResult(
                stdout=getattr(res, "stdout", "") or "",
                stderr=getattr(res, "stderr", "") or "",
                exit_code=getattr(res, "exit_code", 0),
            )
        except Exception as err:
            raise SandboxError(f"Sandbox command execution failed: {err}") from err
