"""Unit tests for test command discovery in Sandbox (Decision 6)."""

from unittest.mock import MagicMock

from devpilot.sandbox import ExecResult, Sandbox


def test_discover_from_explicit_config() -> None:
    """Verifies that devpilot.json explicit configuration takes precedence."""
    mock_instance = MagicMock()
    sandbox = Sandbox(instance=mock_instance)
    mock_instance.commands.run.return_value = ExecResult(
        stdout='{"test_command": "pytest -m unit", "lint_command": "ruff check"}',
        stderr="",
        exit_code=0,
    )

    result = sandbox.discover_tests()
    assert result["test_command"] == "pytest -m unit"
    assert result["lint_command"] == "ruff check"
    assert result["source"] == "config"


def test_discover_auto_detect_pyproject() -> None:
    """Verifies that pyproject.toml triggers auto-detection of pytest, ruff, and mypy."""
    mock_instance = MagicMock()
    sandbox = Sandbox(instance=mock_instance)
    mock_instance.commands.run.side_effect = [
        ExecResult(stdout="", stderr="File not found", exit_code=1),  # no devpilot.json
        ExecResult(stdout="[tool.pytest]", stderr="", exit_code=0),  # pyproject.toml exists
    ]

    result = sandbox.discover_tests()
    assert result["test_command"] == "pytest"
    assert result["lint_command"] == "ruff check"
    assert result["typecheck_command"] == "mypy"
    assert result["source"] == "auto_detected"


def test_discover_no_command_found() -> None:
    """Verifies that absence of test files returns not_found status."""
    mock_instance = MagicMock()
    sandbox = Sandbox(instance=mock_instance)
    mock_instance.commands.run.return_value = ExecResult(
        stdout="",
        stderr="File not found",
        exit_code=1,
    )

    result = sandbox.discover_tests()
    assert result["test_command"] is None
    assert result["source"] == "not_found"
