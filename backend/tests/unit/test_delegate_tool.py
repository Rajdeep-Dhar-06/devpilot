from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devpilot.core.exceptions import WorkerLimitExceededError, WorkerScopeConflictError
from devpilot.tools.registry import ToolRegistry
from devpilot.tools.subagent import WorkerManager


@pytest.mark.asyncio
async def test_delegate_work_lifecycle() -> None:
    mock_sandbox = MagicMock()
    worker_manager = WorkerManager(max_parallel_workers=2)

    registry = ToolRegistry(
        sandbox_provider=mock_sandbox,
        sandbox_id="sbx-123",
        worker_manager=worker_manager,
    )

    tools = registry.get_tools_for_role("implementer")
    delegate_tool = next((t for t in tools if t.name == "delegate_work"), None)
    assert delegate_tool is not None

    mock_worker_agent = AsyncMock()
    mock_msg = MagicMock()
    mock_msg.content = "Completed editing calc.py"
    mock_worker_agent.ainvoke.return_value = {"messages": [mock_msg]}

    with patch("devpilot.agents.base.build_agent", return_value=mock_worker_agent):
        result = await delegate_tool.ainvoke(
            {"task": "Add input validation", "declared_files": ["src/calc.py"]}
        )

        assert "Completed editing calc.py" in str(result)
        # Verify worker was completed and slot released
        assert worker_manager.active_worker_count == 0


@pytest.mark.asyncio
async def test_delegate_work_scope_conflict() -> None:
    mock_sandbox = MagicMock()
    worker_manager = WorkerManager(max_parallel_workers=5)
    worker_manager.register_worker(
        worker_id="existing-worker",
        task="Existing task",
        declared_files=["src/calc.py"],
    )

    registry = ToolRegistry(
        sandbox_provider=mock_sandbox,
        sandbox_id="sbx-123",
        worker_manager=worker_manager,
    )

    tools = registry.get_tools_for_role("implementer")
    delegate_tool = next((t for t in tools if t.name == "delegate_work"), None)
    assert delegate_tool is not None

    with pytest.raises(WorkerScopeConflictError):
        await delegate_tool.ainvoke({"task": "Conflicting task", "declared_files": ["src/calc.py"]})


@pytest.mark.asyncio
async def test_delegate_work_limit_exceeded() -> None:
    mock_sandbox = MagicMock()
    worker_manager = WorkerManager(max_parallel_workers=1)
    worker_manager.register_worker(
        worker_id="w-1",
        task="Task 1",
        declared_files=["src/a.py"],
    )

    registry = ToolRegistry(
        sandbox_provider=mock_sandbox,
        sandbox_id="sbx-123",
        worker_manager=worker_manager,
    )

    tools = registry.get_tools_for_role("implementer")
    delegate_tool = next((t for t in tools if t.name == "delegate_work"), None)
    assert delegate_tool is not None

    with pytest.raises(WorkerLimitExceededError):
        await delegate_tool.ainvoke({"task": "Overflow task", "declared_files": ["src/b.py"]})
