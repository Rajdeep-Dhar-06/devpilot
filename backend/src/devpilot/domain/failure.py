from pydantic import BaseModel, Field


class WorkflowFailure(BaseModel):
    """Structured capture of why a workflow path was terminated or failed."""

    reason: str = Field(..., description="Root cause of the failure")
    step: str = Field(..., description="Workflow node or stage where failure occurred")
    details: dict[str, str] = Field(
        default_factory=dict, description="Diagnostic contextual metadata"
    )
