"""Unit tests for the 4-reviewer parallel subgraph execution."""

import pytest

from devpilot.agents.planner.agent import ImplementationPlan
from devpilot.agents.reviewer.agent import (
    Finding,
    ReviewState,
    build_review_graph,
)
from devpilot.models import GitHubIssue, WorkspaceInfo


@pytest.mark.asyncio
async def test_review_subgraph_execution() -> None:
    """Verifies that the review graph runs parallel specialists and merges findings."""

    async def mock_security(state: ReviewState) -> dict[str, list[Finding]]:
        return {
            "findings": [
                Finding(
                    category="security",
                    severity="info",
                    file_path="src/calc.py",
                    message="No security issues found",
                    suggestion="Looks good",
                )
            ]
        }

    async def mock_requirement(state: ReviewState) -> dict[str, list[Finding]]:
        return {"findings": []}

    async def mock_code_quality(state: ReviewState) -> dict[str, list[Finding]]:
        return {"findings": []}

    async def mock_edge_case(state: ReviewState) -> dict[str, list[Finding]]:
        return {"findings": []}

    graph = build_review_graph(
        security_node=mock_security,
        requirement_node=mock_requirement,
        code_quality_node=mock_code_quality,
        edge_case_node=mock_edge_case,
    )

    initial_state: ReviewState = {
        "issue": GitHubIssue(
            issue_id=1,
            issue_url="https://github.com/org/repo/issues/1",
            title="Title",
            description="Description",
            repository="org/repo",
        ),
        "plan": ImplementationPlan(
            problem_summary="Summary",
            relevant_files=["src/calc.py"],
            proposed_changes=["Change"],
            implementation_steps=["Step 1"],
            testing_expectations="pytest",
            potential_risks="None",
        ),
        "branch_name": "devpilot/fix",
        "workspace": WorkspaceInfo(
            sandbox_id="sbx-123",
            repo_path="/workspace/repo",
            base_branch="main",
        ),
        "findings": [],
    }

    final_state = await graph.ainvoke(initial_state)

    assert "review_result" in final_state
    review_res = final_state["review_result"]
    assert review_res.verdict == "passed"
    assert len(review_res.findings) == 1
