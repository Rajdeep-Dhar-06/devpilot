"""Shell execution tools for sandbox commands.

Beginner Guide:
- `bash_tool`: Full shell execution for the Implementer agent to run tests,
  linters, and build commands.
- `test_runner_tool`: Bounded test execution for Worker subagents. Workers are
  only permitted to run recognized test commands (e.g. pytest, npm test) and
  are strictly prohibited from arbitrary shell commands or file redirection.
"""

import shlex

from langchain_core.tools import BaseTool, tool

from devpilot.sandbox import Sandbox

ALLOWED_TEST_PREFIXES = (
    "pytest",
    "python -m pytest",
    "python -m unittest",
    "python3 -m unittest",
    "python3 -m pytest",
    "npm test",
    "npm run test",
    "yarn test",
    "pnpm test",
    "cargo test",
    "go test",
    "mvn test",
    "gradle test",
    "ruff check",
    "mypy",
    "flake8",
    "eslint",
)


def is_test_command_allowed(command: str) -> bool:
    """Checks whether a command is a safe test/linter verification command."""
    cmd = command.strip()
    if not cmd:
        return False

    # Block file redirection or command chaining/piping
    if any(char in cmd for char in (">", "<", "|", ";", "&")):
        return False

    try:
        parts = shlex.split(cmd)
    except ValueError:
        return False

    if not parts:
        return False

    # Check if the command starts with any allowed test or check prefix
    return any(cmd.startswith(prefix) for prefix in ALLOWED_TEST_PREFIXES)


def bash_tool(sandbox: Sandbox) -> BaseTool:
    """Returns a general-purpose shell tool for implementation and testing."""

    @tool
    def bash(command: str) -> str:
        """Execute a shell command inside the repository workspace."""
        res = sandbox.run(command)
        output = f"{res.stdout}\n{res.stderr}".strip()
        if res.exit_code != 0:
            return f"Command exited with code {res.exit_code}:\n{output}"
        return output or "Command completed with no output."

    return bash


def run_tests_tool(sandbox: Sandbox) -> BaseTool:
    """Returns a restricted test execution tool for worker subagents."""

    @tool
    def run_tests(command: str = "pytest") -> str:
        """Run project tests or linters (e.g., 'pytest', 'npm test', 'ruff check').

        Args:
            command: Safe test or lint command to execute (default: 'pytest').
        """
        if not is_test_command_allowed(command):
            return (
                f"Error: Command '{command}' is not an authorized test/check command. "
                "Workers may only execute recognized test runners (pytest, npm test, etc.)."
            )

        res = sandbox.run(command)
        output = f"{res.stdout}\n{res.stderr}".strip()
        if res.exit_code != 0:
            return f"Tests failed with exit code {res.exit_code}:\n{output}"
        return output or "Tests completed successfully with no output."

    return run_tests
