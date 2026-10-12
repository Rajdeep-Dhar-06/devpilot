"""Code quality reviewer specialist node."""

from devpilot.agents.reviewers.base import run_reviewer_agent
from devpilot.domain.enums import ReviewCategory
from devpilot.domain.review import Finding
from devpilot.workflows.review.state import ReviewState


async def run_code_quality_review(state: ReviewState) -> dict[str, list[Finding]]:
    """Executes the code quality review specialist."""
    findings = await run_reviewer_agent(ReviewCategory.CODE_QUALITY, state)
    return {"code_quality_findings": findings}
