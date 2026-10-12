from unittest.mock import AsyncMock, patch

import pytest

from devpilot.agents.implementer import run_implementer
from devpilot.domain.implementation import ImplementationReport
from devpilot.domain.issue import GitHubIssue
from devpilot.domain.plan import ImplementationPlan
from devpilot.domain.workspace import WorkspaceInfo


@pytest.mark.asyncio
async def test_run_implementer() -> None:
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
        tests_run=["pytest tests/test_calc.py"],
        remaining_risks="None",
        blockers=None,
    )

    mock_agent = AsyncMock()
    mock_agent.ainvoke.return_value = {"structured_response": expected_report}

    with patch("devpilot.agents.implementer.build_agent", return_value=mock_agent) as mock_build:
        report = await run_implementer(
            issue=sample_issue,
            plan=sample_plan,
            branch_name="devpilot/issue-42",
            workspace=workspace,
            tools=[],
        )

        assert report == expected_report
        assert report.status == "completed"
        assert "src/calc.py" in report.changed_files
        mock_build.assert_called_once()
        mock_agent.ainvoke.assert_awaited_once()
