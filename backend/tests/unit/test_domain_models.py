from devpilot.domain.enums import (
    PlanDecision,
    PublicationDecision,
    QAStatus,
    ReviewCategory,
    ReviewSeverity,
)
from devpilot.domain.failure import WorkflowFailure
from devpilot.domain.implementation import ImplementationReport
from devpilot.domain.issue import GitHubIssue
from devpilot.domain.plan import ImplementationPlan
from devpilot.domain.review import Finding, ReviewResult
from devpilot.domain.verification import QAResult, TestResult
from devpilot.domain.workspace import WorkspaceInfo


def test_domain_enums() -> None:
    assert ReviewSeverity.CRITICAL.value == "critical"
    assert ReviewSeverity.HIGH.value == "high"
    assert ReviewSeverity.MEDIUM.value == "medium"
    assert ReviewSeverity.LOW.value == "low"
    assert ReviewSeverity.INFO.value == "info"

    assert QAStatus.PASSED.value == "passed"
    assert QAStatus.FIX_REQUIRED.value == "fix_required"
    assert QAStatus.RETRY_LIMIT_REACHED.value == "retry_limit_reached"

    assert PlanDecision.APPROVE.value == "approve"
    assert PlanDecision.REVISE.value == "revise"
    assert PlanDecision.REJECT.value == "reject"

    assert PublicationDecision.APPROVE.value == "approve"
    assert PublicationDecision.REJECT.value == "reject"


def test_domain_models_creation() -> None:
    issue = GitHubIssue(
        issue_id=42,
        issue_url="https://github.com/org/repo/issues/42",
        title="Fix divide by zero",
        description="Calculation crashes when denom is 0",
        repository="org/repo",
    )
    assert issue.issue_id == 42

    workspace = WorkspaceInfo(
        sandbox_id="sbx-12345",
        repo_path="/workspace/repo",
        base_branch="main",
    )
    assert workspace.sandbox_id == "sbx-12345"

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
        tests_run=["pytest"],
        remaining_risks="None",
        blockers=None,
    )
    assert report.changed_files == ["src/calc.py"]

    finding = Finding(
        category=ReviewCategory.SECURITY,
        severity=ReviewSeverity.HIGH,
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
    assert review_res.findings[0].severity == ReviewSeverity.HIGH

    test_res = TestResult(
        passed=False,
        command="pytest",
        output="1 failed, 2 passed",
        exit_code=1,
    )
    assert test_res.passed is False

    qa_res = QAResult(
        status=QAStatus.FIX_REQUIRED,
        feedback="Fix failing tests and high security finding",
        guardrail_override=True,
    )
    assert qa_res.guardrail_override is True

    failure = WorkflowFailure(
        reason="Exceeded maximum repair attempts",
        step="qa_evaluation",
    )
    assert failure.step == "qa_evaluation"
