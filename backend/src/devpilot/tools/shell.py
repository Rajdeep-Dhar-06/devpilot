"""Sandbox shell execution tool bounded by security and role policies."""

from typing import Any

from devpilot.sandbox.command_policy import CommandPolicy


class ShellTool:
    """Executes shell commands in the sandbox subject to command security policies."""

    def __init__(self, sandbox_provider: Any, policy: CommandPolicy | None = None) -> None:
        self.sandbox = sandbox_provider
        self.policy = policy or CommandPolicy()

    def execute(
        self,
        sandbox_id: str,
        command: str,
        role: str = "implementer",
        cwd: str | None = None,
    ) -> str:
        """Executes a command after validating it against the agent's role policy.

        Raises:
            CommandPolicyViolationError: If command violates role security policy.
            RuntimeError: If command returns a non-zero exit code.
        """
        self.policy.validate_command(command, role=role)
        res = self.sandbox.exec(sandbox_id, command, cwd=cwd)
        if res.exit_code != 0:
            raise RuntimeError(
                f"Command '{command}' failed with exit code {res.exit_code}:\n"
                f"{res.stderr}\n{res.stdout}"
            )
        return str(res.stdout)
