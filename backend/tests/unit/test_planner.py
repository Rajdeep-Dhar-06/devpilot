"""Unit tests for Planner Agent."""

from unittest.mock import AsyncMock, patch

import pytest

from devpilot.agents.planner.agent import ImplementationPlan, plan_node
from devpilot.models import GitHubIssue, WorkspaceInfo
from devpilot.workflow import DevPilotState


@pytest.mark.asyncio
async def test_plan_node() -> None:
    """Verifies that plan_node runs the ReAct agent and returns an ImplementationPlan."""
    sample_issue = GitHubIssue(
        issue_id=42,
        issue_url="https://github.com/org/repo/issues/42",
        title="ZeroDivisionError in calc.py",
        description="Division by zero crashes application",
        repository="org/repo",
        labels=["bug"],
    )
    workspace = WorkspaceInfo(
        sandbox_id="sbx-123",
        repo_path="/workspace/repo",
        base_branch="main",
    )

    expected_plan = ImplementationPlan(
        problem_summary="Fix ZeroDivisionError in divide function",
        relevant_files=["src/calc.py"],
        proposed_changes=["Add zero divisor check"],
        implementation_steps=["Check if b == 0, raise ValueError"],
        testing_expectations="pytest tests/test_calc.py passes",
        potential_risks="Existing callers might expect ZeroDivisionError",
    )

    mock_agent = AsyncMock()
    mock_agent.ainvoke.return_value = {"structured_response": expected_plan}

    state: DevPilotState = {
        "issue": sample_issue,
        "workspace": workspace,
    }

    with patch(
        "devpilot.agents.planner.agent.create_react_agent", return_value=mock_agent
    ) as mock_create:
        res = await plan_node(state)

        assert "plan" in res
        assert res["plan"] == expected_plan
        assert res["plan"].problem_summary == "Fix ZeroDivisionError in divide function"
        mock_create.assert_called_once()
        mock_agent.ainvoke.assert_awaited_once()
