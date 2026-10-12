"""Unit tests for search and discovery tools (find_files and search_code)."""

from unittest.mock import MagicMock

from devpilot.sandbox import ExecResult, Sandbox
from devpilot.tools.search import search_tools


def test_find_files_success_and_scope() -> None:
    """Verifies that find_files discovers files and enforces scope boundaries."""
    mock_instance = MagicMock()
    mock_instance.commands.run.return_value = ExecResult(
        stdout="src/calc.py\nsrc/utils.py\ntests/test_calc.py\n",
        stderr="",
        exit_code=0,
    )
    sandbox = Sandbox(instance=mock_instance)

    # 1. Unscoped search
    tools = search_tools(sandbox)
    find_tool = next(t for t in tools if t.name == "find_files")
    res = find_tool.invoke({"pattern": "*.py"})
    assert "src/calc.py" in res
    assert "src/utils.py" in res
    assert "tests/test_calc.py" in res

    # 2. Scoped search
    scoped_tools = search_tools(sandbox, scope=["src/calc.py"])
    scoped_find = next(t for t in scoped_tools if t.name == "find_files")
    scoped_res = scoped_find.invoke({"pattern": "*.py"})
    assert "src/calc.py" in scoped_res
    assert "src/utils.py" not in scoped_res


def test_search_code_success_and_scope() -> None:
    """Verifies that search_code matches code text and respects scope."""
    mock_instance = MagicMock()
    mock_instance.commands.run.return_value = ExecResult(
        stdout=(
            "src/calc.py:10:def divide(a, b):\ntests/test_calc.py:5:    assert divide(10, 2) == 5\n"
        ),
        stderr="",
        exit_code=0,
    )
    sandbox = Sandbox(instance=mock_instance)

    # 1. Unscoped search
    tools = search_tools(sandbox)
    search_tool = next(t for t in tools if t.name == "search_code")
    res = search_tool.invoke({"query": "divide"})
    assert "src/calc.py:10:def divide(a, b):" in res
    assert "tests/test_calc.py:5:" in res

    # 2. Scoped search
    scoped_tools = search_tools(sandbox, scope=["src/calc.py"])
    scoped_search = next(t for t in scoped_tools if t.name == "search_code")
    scoped_res = scoped_search.invoke({"query": "divide"})
    assert "src/calc.py:10:def divide(a, b):" in scoped_res
    assert "tests/test_calc.py" not in scoped_res
