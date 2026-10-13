"""Reviewer Subgraph: 4 specialized reviewers run in parallel, merged by a merge node.

Beginner Guide:
Reading order of this file:
1. Types: Finding, ReviewerOutput, ReviewResult
2. Prompts: Specialist reviewer instructions (security, requirement, code_quality, edge_case)
3. State: ReviewState (with an operator.add reducer for findings)
4. Nodes: Four individual reviewer nodes
5. Merge: Merges findings, deduplicates, and evaluates verdict (Decision 12)
6. Graph: build_review_graph() compiles the parallel subgraph
"""

import operator
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from devpilot.llm import get_llm
from devpilot.models import GitHubIssue, WorkspaceInfo
from devpilot.sandbox import Sandbox
from devpilot.tools.files import read_only_file_tools
from devpilot.tools.git import git_diff_tool
from devpilot.tools.search import search_tools

# ---- 1. Types -------------------------------------------------------------

Severity = Literal["critical", "high", "medium", "low", "info"]
Category = Literal["security", "requirement", "code_quality", "edge_case"]


class Finding(BaseModel):
    """Specific observation produced by a review specialist."""

    category: Category = Field(..., description="Reviewer specialization category")
    severity: Severity = Field(..., description="Normalized severity level")
    file_path: str = Field(..., description="Target file path relative to repository root")
    line_number: int | None = Field(default=None, description="Line number if applicable")
    message: str = Field(..., description="Explanation of the issue")
    suggestion: str = Field(..., description="Actionable recommendation for resolving the issue")


class ReviewerOutput(BaseModel):
    """Structured response expected from each reviewer agent."""

    findings: list[Finding] = Field(default_factory=list, description="List of findings identified")


class ReviewResult(BaseModel):
    """Consolidated review result produced by the Merge Node."""

    findings: list[Finding] = Field(
        default_factory=list, description="Consolidated deduplicated findings"
    )
    summary: str = Field(..., description="Executive summary of the review")
    verdict: Literal["passed", "fix_required"] = Field(..., description="Review verdict")


# ---- 2. Prompts -----------------------------------------------------------

PROMPTS: dict[Category, str] = {
    "security": """You are the DevPilot Security Reviewer.
Inspect code changes between base branch and working branch for security issues:
1. Injection vulnerabilities (SQL, shell command, code injection, path traversal).
2. Secrets, API keys, passwords, or tokens hardcoded in code.
3. Unsafe input deserialization or unvalidated user input.
4. Broken authentication or authorization checks.
5. Insecure defaults or weak cryptography.
Return all issues as a list of findings with category='security'.""",
    "requirement": """You are the DevPilot Requirement Reviewer.
Validate that the code changes faithfully and completely address the GitHub issue
and follow the approved implementation plan.
Return any missing requirements or plan deviations with category='requirement'.""",
    "code_quality": """You are the DevPilot Code Quality Reviewer.
Inspect the changes for maintainability, readability, proper error handling,
clean architecture, and compliance with project coding standards.
Return issues with category='code_quality'.""",
    "edge_case": """You are the DevPilot Edge Case Reviewer.
Identify boundary conditions, null/empty values, exception handling gaps,
concurrency race conditions, and unexpected inputs.
Return issues with category='edge_case'.""",
}


# ---- 3. State -------------------------------------------------------------


class ReviewState(TypedDict, total=False):
    """State schema for the 4-reviewer parallel subgraph."""

    issue: GitHubIssue
    plan: Any
    branch_name: str
    workspace: WorkspaceInfo
    findings: Annotated[list[Finding], operator.add]
    review_result: ReviewResult


# ---- 4. Reviewer Nodes ----------------------------------------------------


def _reviewer_tools(sandbox: Sandbox) -> list[Any]:
    return [
        git_diff_tool(sandbox),
        *search_tools(sandbox),
        *read_only_file_tools(sandbox),
    ]


async def run_reviewer(
    category: Category, state: ReviewState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Runs a single specialized reviewer agent with read-only tools."""
    configurable = (config or {}).get("configurable", {})
    sandbox: Sandbox = configurable.get("sandbox") or Sandbox()

    agent = create_react_agent(
        get_llm("reviewer"),
        _reviewer_tools(sandbox),
        prompt=PROMPTS[category],
        response_format=ReviewerOutput,
    )

    base_branch = state["workspace"].base_branch
    task = (
        f"Review code changes on branch '{state['branch_name']}' against '{base_branch}'.\n"
        f"Issue: #{state['issue'].issue_id} {state['issue'].title}\n"
        f"Description: {state['issue'].description}\n\n"
        f"Focus strictly on {category} aspects and output findings."
    )

    # Pass Langfuse callbacks and agent role tags from config
    run_config: RunnableConfig = {
        "callbacks": (config or {}).get("callbacks", []),
        "tags": list((config or {}).get("tags", [])) + ["agent:reviewer", f"reviewer:{category}"],
        "metadata": {**((config or {}).get("metadata", {})), "agent_role": "reviewer", "reviewer_category": category},
    }

    result = await agent.ainvoke({"messages": [HumanMessage(content=task)]}, config=run_config)
    structured = result.get("structured_response")
    raw_findings: list[Finding] = []
    if isinstance(structured, ReviewerOutput):
        raw_findings = structured.findings
    elif isinstance(structured, dict) and "findings" in structured:
        raw_findings = [Finding.model_validate(f) for f in structured["findings"]]

    # Ensure correct category tag
    for f in raw_findings:
        f.category = category

    return {"findings": raw_findings}


async def review_security(
    state: ReviewState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    return await run_reviewer("security", state, config)


async def review_requirement(
    state: ReviewState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    return await run_reviewer("requirement", state, config)


async def review_code_quality(
    state: ReviewState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    return await run_reviewer("code_quality", state, config)


async def review_edge_case(
    state: ReviewState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    return await run_reviewer("edge_case", state, config)


# ---- 5. Merge Node --------------------------------------------------------


def is_blocking(finding: Finding) -> bool:
    """Checks if a finding requires fixes (Decision 12)."""
    if finding.severity in ("critical", "high"):
        return True
    return finding.category == "security" and finding.severity == "medium"


def merge_findings(
    security_findings: list[Finding] | None = None,
    requirement_findings: list[Finding] | None = None,
    code_quality_findings: list[Finding] | None = None,
    edge_case_findings: list[Finding] | None = None,
    findings: list[Finding] | None = None,
) -> ReviewResult:
    """Merges and deduplicates findings, ensuring security findings are never dropped."""
    all_findings = findings or [
        *(security_findings or []),
        *(requirement_findings or []),
        *(code_quality_findings or []),
        *(edge_case_findings or []),
    ]

    # Security findings first: if duplicates occur, the security finding wins
    ordered = sorted(all_findings, key=lambda f: f.category != "security")

    unique_findings: list[Finding] = []
    seen: set[tuple[str, int | None, str]] = set()

    for finding in ordered:
        key = (
            finding.file_path,
            finding.line_number,
            finding.message.strip().lower(),
        )
        if key not in seen:
            seen.add(key)
            unique_findings.append(finding)

    needs_fix = any(is_blocking(f) for f in unique_findings)
    verdict: Literal["passed", "fix_required"] = "fix_required" if needs_fix else "passed"
    summary = f"Review completed with {len(unique_findings)} finding(s). Verdict: {verdict}."

    return ReviewResult(
        findings=unique_findings,
        summary=summary,
        verdict=verdict,
    )


def merge_node(state: ReviewState) -> dict[str, ReviewResult]:
    """Workflow node: aggregates all findings in state['findings']."""
    result = merge_findings(findings=state.get("findings", []))
    return {"review_result": result}


# ---- 6. Graph -------------------------------------------------------------

REVIEWER_NODES = {
    "security": review_security,
    "requirement": review_requirement,
    "code_quality": review_code_quality,
    "edge_case": review_edge_case,
}


def build_review_graph(
    reviewers: dict[str, Any] | None = None,
    security_node: Any = None,
    requirement_node: Any = None,
    code_quality_node: Any = None,
    edge_case_node: Any = None,
    merge_node_fn: Any = None,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Builds and compiles the 4-reviewer parallel subgraph."""
    graph = StateGraph(ReviewState)

    node_map = dict(reviewers or REVIEWER_NODES)
    if security_node:
        node_map["security"] = security_node
    if requirement_node:
        node_map["requirement"] = requirement_node
    if code_quality_node:
        node_map["code_quality"] = code_quality_node
    if edge_case_node:
        node_map["edge_case"] = edge_case_node

    merge_fn = merge_node_fn or merge_node
    graph.add_node("merge", merge_fn)

    for name, node_fn in node_map.items():
        graph.add_node(name, node_fn)
        graph.add_edge(START, name)
        graph.add_edge(name, "merge")

    graph.add_edge("merge", END)
    return graph.compile()


# Compatibility alias
create_review_graph = build_review_graph
