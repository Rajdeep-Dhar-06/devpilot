from unittest.mock import AsyncMock, patch

import pytest

from devpilot.agents.planner import run_planner
from devpilot.domain.issue import GitHubIssue
from devpilot.domain.plan import ImplementationPlan
from devpilot.domain.workspace import WorkspaceInfo


@pytest.mark.asyncio
async def test_run_planner() -> None:
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

    with patch("devpilot.agents.planner.build_agent", return_value=mock_agent) as mock_build:
        plan = await run_planner(
            issue=sample_issue,
            workspace=workspace,
            tools=[],
        )

        assert plan == expected_plan
        assert plan.problem_summary == "Fix ZeroDivisionError in divide function"
        mock_build.assert_called_once()
        mock_agent.ainvoke.assert_awaited_once()
