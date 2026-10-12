"""Unit tests ensuring role toolsets only contain permitted tools."""

from devpilot.agents.reviewer.agent import _reviewer_tools
from devpilot.sandbox import Sandbox
from devpilot.tools.delegate import delegate_tool
from devpilot.tools.files import file_tools, read_only_file_tools
from devpilot.tools.search import search_tools
from devpilot.tools.shell import bash_tool, run_tests_tool


def test_reviewer_tools_are_strictly_read_only() -> None:
    """Verifies that reviewer tools only contain diff, search, and read tools."""
    sandbox = Sandbox()
    tools = _reviewer_tools(sandbox)
    names = {t.name for t in tools}

    assert names == {"git_diff", "find_files", "search_code", "read_file"}
    assert "write_file" not in names
    assert "replace_in_file" not in names
    assert "delegate_work" not in names
    assert "bash" not in names
    assert "readonly_bash" not in names


def test_planner_tools_are_strictly_read_only() -> None:
    """Verifies that planner tools only contain search and read tools."""
    sandbox = Sandbox()
    tools = [*search_tools(sandbox), *read_only_file_tools(sandbox)]
    names = {t.name for t in tools}

    assert names == {"find_files", "search_code", "read_file"}
    assert "write_file" not in names
    assert "delegate_work" not in names
    assert "bash" not in names


def test_implementer_tools_include_write_and_delegation() -> None:
    """Verifies that implementer tools include search, file editing, bash, and delegation."""
    sandbox = Sandbox()
    tools = [
        *search_tools(sandbox),
        *file_tools(sandbox),
        bash_tool(sandbox),
        delegate_tool(sandbox),
    ]
    names = {t.name for t in tools}

    assert "find_files" in names
    assert "search_code" in names
    assert "read_file" in names
    assert "write_file" in names
    assert "replace_in_file" in names
    assert "bash" in names
    assert "delegate_work" in names


def test_worker_tools_cannot_delegate_or_run_arbitrary_bash() -> None:
    """Verifies that worker tools exclude delegate_work and raw bash (Decisions 18 & 19)."""
    sandbox = Sandbox()
    tools = [
        *file_tools(sandbox, scope=["src/a.py"]),
        *search_tools(sandbox, scope=["src/a.py"]),
        run_tests_tool(sandbox),
    ]
    names = {t.name for t in tools}

    assert names == {
        "read_file",
        "write_file",
        "replace_in_file",
        "find_files",
        "search_code",
        "run_tests",
    }
    assert "delegate_work" not in names
    assert "bash" not in names
