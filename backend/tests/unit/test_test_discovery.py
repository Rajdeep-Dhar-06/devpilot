from devpilot.sandbox.test_discovery import TestCommandDiscovery


def test_discover_from_explicit_config() -> None:
    discovery = TestCommandDiscovery()
    files = {"devpilot.json": '{"test_command": "pytest -m unit", "lint_command": "ruff check"}'}
    result = discovery.discover(files=files)
    assert result.test_command == "pytest -m unit"
    assert result.lint_command == "ruff check"
    assert result.source == "config"


def test_discover_auto_detect_python_pytest() -> None:
    discovery = TestCommandDiscovery()
    files = {"pyproject.toml": "[tool.pytest.ini_options]\npythonpath = ['src']"}
    result = discovery.discover(files=files)
    assert result.test_command == "pytest"
    assert result.source == "auto_detected"


def test_discover_auto_detect_makefile() -> None:
    discovery = TestCommandDiscovery()
    files = {"Makefile": "test:\n\tpytest\nlint:\n\truff"}
    result = discovery.discover(files=files)
    assert result.test_command == "make test"
    assert result.source == "auto_detected"


def test_discover_no_command_found() -> None:
    discovery = TestCommandDiscovery()
    files = {"README.md": "# Project without tests"}
    result = discovery.discover(files=files)
    assert result.test_command is None
    assert result.source == "not_found"
    assert result.is_missing is True
