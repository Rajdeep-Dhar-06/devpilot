"""State definitions for the Review Subgraph."""

from typing import Any, NotRequired, TypedDict

from devpilot.domain.issue import GitHubIssue
from devpilot.domain.plan import ImplementationPlan
from devpilot.domain.review import Finding, ReviewResult
from devpilot.domain.workspace import WorkspaceInfo


class ReviewState(TypedDict):
    """Execution state for the 4-reviewer parallel subgraph (Section 5)."""

    issue: GitHubIssue
    plan: ImplementationPlan
    branch_name: str
    workspace: WorkspaceInfo
    security_findings: list[Finding]
    requirement_findings: list[Finding]
    code_quality_findings: list[Finding]
    edge_case_findings: list[Finding]
    review_result: NotRequired[ReviewResult]
    tools: NotRequired[list[Any]]
