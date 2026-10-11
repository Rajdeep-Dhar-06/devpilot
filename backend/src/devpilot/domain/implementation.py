from pydantic import BaseModel, Field


class ImplementationReport(BaseModel):
    """Report returned by the Implementation Agent after modifying the repository."""

    changed_files: list[str] = Field(default_factory=list, description="Files modified or added")
    status: str = Field(..., description="Outcome status, e.g. 'completed' or 'blocked'")
    tests_run: list[str] = Field(default_factory=list, description="Checks run locally by agent")
    remaining_risks: str = Field(..., description="Risks identified during implementation")
    blockers: str | None = Field(default=None, description="Any blocking errors encountered")
