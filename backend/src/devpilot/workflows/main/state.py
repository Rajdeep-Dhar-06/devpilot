from typing import TypedDict

from devpilot.domain.enums import PlanDecision, PublicationDecision, QAStatus
from devpilot.domain.implementation import ImplementationReport
from devpilot.domain.issue import GitHubIssue
from devpilot.domain.plan import ImplementationPlan
from devpilot.domain.review import ReviewResult
from devpilot.domain.verification import TestResult
from devpilot.domain.workspace import WorkspaceInfo


class DevPilotState(TypedDict, total=False):
    """Main LangGraph workflow state representing the issue-to-PR lifecycle.

    Fields follow Decisions 7, 12, 16 and the architecture specification.
    """

    # Initial Input & Run Counters
    issue_url: str
    github_token: str | None  # Per-user GitHub authentication token (Decision 20)
    repair_attempts: int  # Defined once, starts at 0, incremented by QA routing
    plan_revisions: int  # Starts at 0, tracks HITL plan revisions

    # Ingested issue & sandbox workspace
    issue: GitHubIssue
    workspace: WorkspaceInfo

    # Planning & HITL Approval
    plan: ImplementationPlan
    plan_decision: PlanDecision
    plan_feedback: str | None

    # Implementation
    branch_name: str
    implementation_report: ImplementationReport

    # Verification (Parallel quality checks)
    test_result: TestResult
    review_result: ReviewResult

    # QA & Routing
    qa_status: QAStatus
    qa_feedback: str | None

    # Final Publication & Outcome
    publication_decision: PublicationDecision
    pull_request_url: str | None
    error: str | None
