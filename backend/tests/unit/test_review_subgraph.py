import pytest

from devpilot.domain.enums import ReviewCategory, ReviewSeverity
from devpilot.domain.issue import GitHubIssue
from devpilot.domain.plan import ImplementationPlan
from devpilot.domain.review import Finding
from devpilot.domain.workspace import WorkspaceInfo
from devpilot.workflows.review.graph import create_review_graph
from devpilot.workflows.review.state import ReviewState


@pytest.mark.asyncio
async def test_review_subgraph_execution() -> None:
    # Build review graph with mock node runners
    async def mock_security_node(state: ReviewState) -> dict[str, list[Finding]]:
        return {
            "security_findings": [
                Finding(
                    category=ReviewCategory.SECURITY,
                    severity=ReviewSeverity.INFO,
                    file_path="src/calc.py",
                    message="No security issues found",
                    suggestion="Looks good",
                )
            ]
        }

    async def mock_requirement_node(state: ReviewState) -> dict[str, list[Finding]]:
        return {"requirement_findings": []}

    async def mock_code_quality_node(state: ReviewState) -> dict[str, list[Finding]]:
        return {"code_quality_findings": []}

    async def mock_edge_case_node(state: ReviewState) -> dict[str, list[Finding]]:
        return {"edge_case_findings": []}

    graph = create_review_graph(
        security_node=mock_security_node,
        requirement_node=mock_requirement_node,
        code_quality_node=mock_code_quality_node,
        edge_case_node=mock_edge_case_node,
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
        "security_findings": [],
        "requirement_findings": [],
        "code_quality_findings": [],
        "edge_case_findings": [],
    }

    final_state = await graph.ainvoke(initial_state)

    assert "review_result" in final_state
    review_res = final_state["review_result"]
    assert review_res.verdict == "passed"
    assert len(review_res.findings) == 1
