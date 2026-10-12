"""Unit tests for subagent delegation and worker scope isolation (Decisions 18 & 19)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devpilot.sandbox import Sandbox
from devpilot.tools.delegate import WorkerTracker, delegate_tool
from devpilot.tools.files import file_tools, is_path_in_scope


def test_worker_scope_conflict_detection() -> None:
    """Verifies that two parallel workers cannot claim overlapping file scopes."""
    tracker = WorkerTracker(max_parallel=5)
    tracker.register("w-1", ["src/calc.py"])

    # Overlapping file must be rejected
    with pytest.raises(RuntimeError, match="conflicts with active worker"):
        tracker.register("w-2", ["src/calc.py"])

    # Distinct file must be allowed
    tracker.register("w-3", ["src/other.py"])
    assert tracker.active_count == 2


def test_worker_concurrency_limit_exceeded() -> None:
    """Verifies that attempting to exceed the 5 parallel worker cap is rejected."""
    tracker = WorkerTracker(max_parallel=5)
    for i in range(5):
        tracker.register(f"w-{i}", [f"src/file_{i}.py"])

    with pytest.raises(RuntimeError, match="Concurrency limit of 5 workers reached"):
        tracker.register("w-overflow", ["src/extra.py"])

    # Releasing one worker allows another to run
    tracker.release("w-0")
    tracker.register("w-new", ["src/extra.py"])
    assert tracker.active_count == 5


def test_worker_file_write_scope_enforcement() -> None:
    """Verifies that file_tools with a scope reject writes outside that scope."""
    sandbox = Sandbox()
    tools = file_tools(sandbox, scope=["src/calc.py"])
    write_tool = next(t for t in tools if t.name == "write_file")

    # Outside scope must return error message
    err = write_tool.invoke({"file_path": "src/secret.py", "content": "bad"})
    assert "Error: 'src/secret.py' is outside your authorized file scope" in err

    assert is_path_in_scope("src/calc.py", ["src/calc.py"]) is True
    assert is_path_in_scope("src/secret.py", ["src/calc.py"]) is False


@pytest.mark.asyncio
async def test_delegate_tool_lifecycle() -> None:
    """Verifies that delegate_work tool executes worker agent and releases slot upon completion."""
    sandbox = Sandbox()
    tracker = WorkerTracker(max_parallel=2)
    tool = delegate_tool(sandbox, tracker=tracker)

    mock_agent = AsyncMock()
    mock_msg = MagicMock()
    mock_msg.content = "Finished editing calc.py"
    mock_agent.ainvoke.return_value = {"messages": [mock_msg]}

    with patch("devpilot.tools.delegate.create_react_agent", return_value=mock_agent):
        result = await tool.ainvoke({"task": "Update calc", "declared_files": ["src/calc.py"]})
        assert "Finished editing calc.py" in str(result)
        assert tracker.active_count == 0
