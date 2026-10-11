from pydantic import BaseModel, Field


class GitHubIssue(BaseModel):
    """Normalized GitHub issue details ingested by the Issue Node."""

    issue_id: int = Field(..., description="GitHub Issue number")
    issue_url: str = Field(..., description="Full URL to the GitHub issue")
    title: str = Field(..., description="Issue title")
    description: str = Field(..., description="Full issue body/description")
    repository: str = Field(..., description="Owner/repo slug, e.g. 'org/repo'")
    labels: list[str] = Field(default_factory=list, description="Associated issue labels")
