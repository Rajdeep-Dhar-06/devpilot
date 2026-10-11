from pydantic import BaseModel, Field

from devpilot.domain.enums import QAStatus


class TestResult(BaseModel):
    """Execution results from the Testing Node."""

    __test__ = False

    passed: bool = Field(..., description="Whether tests, linter, and type checks succeeded")
    command: str = Field(..., description="Command that was executed")
    output: str = Field(..., description="Captured stdout and stderr")
    exit_code: int = Field(..., description="Process exit code")


class QAResult(BaseModel):
    """Evaluation verdict produced by the QA Node combining tests and reviews."""

    status: QAStatus = Field(..., description="QA status decision")
    feedback: str = Field(..., description="Actionable repair instructions for Implementer")
    guardrail_override: bool = Field(
        default=False,
        description="True if a hard rule guardrail overrode the LLM's assessment",
    )
