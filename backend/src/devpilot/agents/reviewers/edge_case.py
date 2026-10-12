"""Edge case reviewer specialist node."""

from devpilot.agents.reviewers.base import run_reviewer_agent
from devpilot.domain.enums import ReviewCategory
from devpilot.domain.review import Finding
from devpilot.workflows.review.state import ReviewState


async def run_edge_case_review(state: ReviewState) -> dict[str, list[Finding]]:
    """Executes the edge case review specialist."""
    findings = await run_reviewer_agent(ReviewCategory.EDGE_CASE, state)
    return {"edge_case_findings": findings}
