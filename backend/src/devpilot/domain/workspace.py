from pydantic import BaseModel, Field


class WorkspaceInfo(BaseModel):
    """Metadata representing an active development workspace in the sandbox."""

    sandbox_id: str = Field(..., description="E2B Sandbox identifier")
    repo_path: str = Field(..., description="Root path of cloned repository in sandbox")
    base_branch: str = Field(default="main", description="Target base branch for PR")
