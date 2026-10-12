"""Review Subgraph definition (Section 5).

Runs 4 specialized code reviewers in parallel and aggregates their findings
into a consolidated ReviewResult via the Merge Node.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from devpilot.agents.reviewers.code_quality import run_code_quality_review
from devpilot.agents.reviewers.edge_case import run_edge_case_review
from devpilot.agents.reviewers.requirement import run_requirement_review
from devpilot.agents.reviewers.security import run_security_review
from devpilot.domain.review import ReviewResult
from devpilot.workflows.review.merge import merge_findings
from devpilot.workflows.review.state import ReviewState

ReviewNodeFunc = (
    Callable[[ReviewState], Awaitable[dict[str, Any]]] | Callable[[ReviewState], dict[str, Any]]
)


async def default_merge_node(state: ReviewState) -> dict[str, ReviewResult]:
    """Default merge node aggregating findings across all 4 specialists."""
    result = merge_findings(
        security_findings=state.get("security_findings", []),
        requirement_findings=state.get("requirement_findings", []),
        code_quality_findings=state.get("code_quality_findings", []),
        edge_case_findings=state.get("edge_case_findings", []),
    )
    return {"review_result": result}


def create_review_graph(
    security_node: ReviewNodeFunc | None = None,
    requirement_node: ReviewNodeFunc | None = None,
    code_quality_node: ReviewNodeFunc | None = None,
    edge_case_node: ReviewNodeFunc | None = None,
    merge_node: ReviewNodeFunc | None = None,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Builds and compiles the 4-reviewer parallel fan-out/fan-in subgraph."""
    builder = StateGraph(ReviewState)

    # Register nodes
    builder.add_node("security_review", security_node or run_security_review)  # type: ignore[arg-type]
    builder.add_node("requirement_review", requirement_node or run_requirement_review)  # type: ignore[arg-type]
    builder.add_node("code_quality_review", code_quality_node or run_code_quality_review)  # type: ignore[arg-type]
    builder.add_node("edge_case_review", edge_case_node or run_edge_case_review)  # type: ignore[arg-type]
    builder.add_node("merge", merge_node or default_merge_node)  # type: ignore[arg-type]

    # Parallel fan-out from START to all 4 reviewers
    builder.add_edge(START, "security_review")
    builder.add_edge(START, "requirement_review")
    builder.add_edge(START, "code_quality_review")
    builder.add_edge(START, "edge_case_review")

    # Fan-in convergence to the merge node
    builder.add_edge("security_review", "merge")
    builder.add_edge("requirement_review", "merge")
    builder.add_edge("code_quality_review", "merge")
    builder.add_edge("edge_case_review", "merge")

    # Terminal edge
    builder.add_edge("merge", END)

    return builder.compile()
