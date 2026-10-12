"""Security reviewer specialist node."""

from devpilot.agents.reviewers.base import run_reviewer_agent
from devpilot.domain.enums import ReviewCategory
from devpilot.domain.review import Finding
from devpilot.workflows.review.state import ReviewState


async def run_security_review(state: ReviewState) -> dict[str, list[Finding]]:
    """Executes the security review specialist."""
    findings = await run_reviewer_agent(ReviewCategory.SECURITY, state)
    return {"security_findings": findings}
