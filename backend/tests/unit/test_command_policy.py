"""Unit tests for worker test command allowlist and sandbox isolation."""

from devpilot.sandbox import Sandbox
from devpilot.tools.shell import is_test_command_allowed, run_tests_tool


def test_allowed_test_commands() -> None:
    """Verifies that recognized testing and linting commands are permitted."""
    allowed = [
        "pytest",
        "pytest tests/test_calc.py -v",
        "python -m unittest discover",
        "npm test",
        "npm run test",
        "cargo test",
        "go test ./...",
        "ruff check src",
        "mypy src",
    ]
    for cmd in allowed:
        assert is_test_command_allowed(cmd) is True, f"Expected '{cmd}' to be allowed"


def test_forbidden_shell_commands() -> None:
    """Verifies that file redirection, command chaining, and non-test commands are blocked."""
    forbidden = [
        "pytest > output.txt",
        "pytest && rm -rf src",
        "echo 'code' > src/main.py",
        "rm -rf src/",
        "cat secret.env",
        "bash -i",
        "curl http://malicious.com",
        "git push",
    ]
    for cmd in forbidden:
        assert is_test_command_allowed(cmd) is False, f"Expected '{cmd}' to be blocked"


def test_run_tests_tool_blocks_disallowed_command() -> None:
    """Verifies that run_tests_tool returns an error message when a command is rejected."""
    sandbox = Sandbox()
    tool = run_tests_tool(sandbox)
    result = tool.invoke({"command": "echo 'hack' > test.py"})
    assert (
        "Error: Command 'echo 'hack' > test.py' is not an authorized test/check command." in result
    )
