"""Unit tests for shared and agent-specific Pydantic data models."""

import pytest
from pydantic import ValidationError

from devpilot.agents.implementer.agent import ImplementationReport
from devpilot.agents.planner.agent import ImplementationPlan
from devpilot.agents.reviewer.agent import Finding, ReviewResult
from devpilot.models import GitHubIssue, TestResult, WorkspaceInfo


def test_shared_models_instantiation() -> None:
    """Verifies that shared models construct correctly with expected fields."""
    issue = GitHubIssue(
        issue_id=42,
        issue_url="https://github.com/org/repo/issues/42",
        title="Fix divide by zero",
        description="Calculation crashes when denom is 0",
        repository="org/repo",
    )
    assert issue.issue_id == 42
    assert issue.repository == "org/repo"

    workspace = WorkspaceInfo(
        sandbox_id="sbx-12345",
        repo_path="/workspace/repo",
        base_branch="main",
    )
    assert workspace.sandbox_id == "sbx-12345"

    test_res = TestResult(
        passed=False,
        command="pytest",
        output="1 failed, 2 passed",
        exit_code=1,
    )
    assert test_res.passed is False


def test_agent_specific_models() -> None:
    """Verifies agent-specific output models: plan, report, and review result."""
    plan = ImplementationPlan(
        problem_summary="Fix divide by zero in calc.py",
        relevant_files=["src/calc.py"],
        proposed_changes=["Add zero check before division"],
        implementation_steps=["1. Open calc.py", "2. Raise ValueError on zero"],
        testing_expectations="Run pytest tests/test_calc.py",
        potential_risks="Existing callers expecting 0 or float inf",
    )
    assert len(plan.relevant_files) == 1

    report = ImplementationReport(
        changed_files=["src/calc.py"],
        status="completed",
        summary="Updated calc.py and ran pytest.",
    )
    assert report.changed_files == ["src/calc.py"]
    assert report.status == "completed"

    finding = Finding(
        category="security",
        severity="high",
        file_path="src/calc.py",
        line_number=10,
        message="Potential denial of service",
        suggestion="Add input bounds validation",
    )
    review_res = ReviewResult(
        findings=[finding],
        summary="Found 1 high severity finding",
        verdict="fix_required",
    )
    assert len(review_res.findings) == 1
    assert review_res.verdict == "fix_required"


def test_literal_field_validation() -> None:
    """Verifies that invalid literal values trigger Pydantic validation errors."""
    with pytest.raises(ValidationError):
        # 'urgent' is not an allowed severity
        Finding(
            category="security",
            severity="urgent",  # type: ignore[arg-type]
            file_path="src/calc.py",
            message="Bug",
            suggestion="Fix",
        )

    with pytest.raises(ValidationError):
        # 'in_progress' is not an allowed report status
        ImplementationReport(
            changed_files=[],
            status="in_progress",  # type: ignore[arg-type]
            summary="Working on it",
        )
