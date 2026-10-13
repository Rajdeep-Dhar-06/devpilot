"""Shared data models used across multiple DevPilot components.

Beginner Guide:
These models are Pydantic objects and TypedDicts passed between major workflow nodes.
Single-purpose models (like ImplementationPlan or Finding) live directly
inside their respective agent files (agents/planner/agent.py, etc.).
"""

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field

# Human approval choices for both checkpoints (Plan approval and PR publication approval)
Decision = Literal["approve", "revise", "reject"]

# Verification outcomes produced by the QA evaluation step
QAStatus = Literal["passed", "fix_required", "retry_limit_reached"]


class GitHubIssue(BaseModel):
    """Normalized metadata for an ingested GitHub issue."""

    issue_id: int = Field(..., description="GitHub issue number, e.g. 42")
    issue_url: str = Field(..., description="Direct HTML URL to the issue")
    title: str = Field(..., description="Issue title")
    description: str = Field(default="", description="Issue description or body markdown")
    repository: str = Field(..., description="Repository slug, e.g. 'owner/repo'")
    labels: list[str] = Field(default_factory=list, description="Labels attached to the issue")


class WorkspaceInfo(BaseModel):
    """Metadata describing the isolated sandbox environment for this run."""

    sandbox_id: str = Field(..., description="Active E2B sandbox instance identifier")
    repo_path: str = Field(
        default="/workspace/repo", description="Filesystem path to cloned repository"
    )
    base_branch: str = Field(default="main", description="Target base branch, e.g. 'main'")


class TestResult(BaseModel):
    """Outcome of running test and validation commands inside the sandbox."""

    __test__ = False  # Prevents pytest from discovering this class as a test suite

    passed: bool = Field(..., description="True if test, linter, and type checks succeeded")
    command: str = Field(..., description="Exact shell command executed")
    output: str = Field(..., description="Captured standard output and error")
    exit_code: int = Field(..., description="Process exit code (0 indicates success)")


class DevPilotState(TypedDict, total=False):
    """Central state object tracking an issue-to-pull-request run.

    Fields are grouped by the workflow step that creates or modifies them.
    """

    # --- 1. Initial Inputs & Authentication ---
    issue_url: str  # Provided by API request or webhook
    github_token: str | None  # Per-user GitHub authentication token (isolated per run)

    # --- 2. Ingestion & Workspace Setup ---
    issue: GitHubIssue  # Ingested by Issue Node via GitHub MCP
    workspace: WorkspaceInfo  # Initialized by Issue Node (repository cloned in E2B sandbox)

    # --- 3. Planning Phase ---
    plan: Any  # Created by Planner Agent (ImplementationPlan)
    plan_feedback: str | None  # Optional human feedback if revised
    plan_decision: Decision  # Human decision (approve, revise, or reject)

    # --- 4. Implementation Phase ---
    branch_name: str  # Working branch created in workspace
    implementation_report: Any  # Produced by Implementer Agent (ImplementationReport)

    # --- 5. Verification Phase (Parallel checks) ---
    test_result: TestResult  # Produced by Testing Node (pytest/lint output)
    review_result: Any  # Produced by Reviewer Subgraph (ReviewResult)

    # --- 6. Quality Assurance (QA) Routing ---
    qa_status: QAStatus  # Verdict from QA Node ('passed', 'fix_required', etc.)
    qa_feedback: str | None  # Specific repair instructions if fixes are required

    # --- 7. Final Publication ---
    publication_decision: Decision  # Human decision to publish PR
    pull_request_url: str | None  # PR URL returned by GitHub MCP upon creation

    # --- 8. Bookkeeping & Counters ---
    repair_attempts: int  # Number of automated bug fix cycles attempted (capped at 3)
    plan_revisions: int  # Number of times human requested plan revisions
    trace_id: str | None  # Observability trace identifier
    run_id: str | None  # Unique workflow execution run identifier
    error: str | None  # High-level failure reason if workflow halts
