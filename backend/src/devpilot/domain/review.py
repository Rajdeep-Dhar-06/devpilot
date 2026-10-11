from pydantic import BaseModel, Field

from devpilot.domain.enums import ReviewCategory, ReviewSeverity


class Finding(BaseModel):
    """Specific code review observation produced by a specialized reviewer."""

    category: ReviewCategory = Field(..., description="Reviewer specialization category")
    severity: ReviewSeverity = Field(..., description="Normalized severity level")
    file_path: str = Field(..., description="Target file path relative to repository root")
    line_number: int | None = Field(default=None, description="Line number if applicable")
    message: str = Field(..., description="Detailed explanation of the issue")
    suggestion: str = Field(..., description="Actionable recommendation for resolving the issue")


class ReviewResult(BaseModel):
    """Consolidated review output produced by the Merge Node (Review Subgraph)."""

    findings: list[Finding] = Field(default_factory=list, description="Consolidated findings list")
    summary: str = Field(..., description="Executive summary of the review")
    verdict: str = Field(..., description="Overall review verdict ('passed' or 'fix_required')")
