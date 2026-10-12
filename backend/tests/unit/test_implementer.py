"""Unit tests for Implementer Agent."""

from unittest.mock import AsyncMock, patch

import pytest

from devpilot.agents.implementer.agent import ImplementationReport, implement_node
from devpilot.agents.planner.agent import ImplementationPlan
from devpilot.models import GitHubIssue, WorkspaceInfo
from devpilot.workflow import DevPilotState


@pytest.mark.asyncio
async def test_implement_node() -> None:
    """Verifies that implement_node runs ReAct agent and returns branch and report."""
    sample_issue = GitHubIssue(
        issue_id=42,
        issue_url="https://github.com/org/repo/issues/42",
        title="ZeroDivisionError in calc.py",
        description="Division by zero crashes application",
        repository="org/repo",
    )
    sample_plan = ImplementationPlan(
        problem_summary="Fix ZeroDivisionError in divide function",
        relevant_files=["src/calc.py"],
        proposed_changes=["Add zero check"],
        implementation_steps=["Update divide function in calc.py"],
        testing_expectations="pytest passes",
        potential_risks="None",
    )
    workspace = WorkspaceInfo(
        sandbox_id="sbx-123",
        repo_path="/workspace/repo",
        base_branch="main",
    )

    expected_report = ImplementationReport(
        changed_files=["src/calc.py"],
        status="completed",
        summary="Updated calc.py and ran pytest.",
    )

    mock_agent = AsyncMock()
    mock_agent.ainvoke.return_value = {"structured_response": expected_report}

    state: DevPilotState = {
        "issue": sample_issue,
        "plan": sample_plan,
        "workspace": workspace,
    }

    with patch(
        "devpilot.agents.implementer.agent.create_react_agent", return_value=mock_agent
    ) as mock_create:
        res = await implement_node(state)

        assert "implementation_report" in res
        assert "branch_name" in res
        assert res["implementation_report"] == expected_report
        assert res["implementation_report"].status == "completed"
        assert "src/calc.py" in res["implementation_report"].changed_files
        mock_create.assert_called_once()
        mock_agent.ainvoke.assert_awaited_once()
