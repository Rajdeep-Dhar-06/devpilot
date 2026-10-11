from pydantic import BaseModel, Field


class ImplementationPlan(BaseModel):
    """Structured plan produced by the Planning Agent and reviewed by a human."""

    problem_summary: str = Field(..., description="Concise analysis of the problem")
    relevant_files: list[str] = Field(
        default_factory=list,
        description="Target files and modules",
    )
    proposed_changes: list[str] = Field(
        default_factory=list,
        description="High-level architectural changes",
    )
    implementation_steps: list[str] = Field(
        default_factory=list,
        description="Step-by-step implementation plan",
    )
    testing_expectations: str = Field(
        ...,
        description="Verification strategy and commands to execute",
    )
    potential_risks: str = Field(
        ...,
        description="Risks, regressions, or edge cases to watch for",
    )
