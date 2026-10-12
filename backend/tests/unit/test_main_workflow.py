"""Unit tests for DevPilot main workflow graph and lifecycle nodes."""

from unittest.mock import MagicMock

import pytest
from langchain_core.runnables import RunnableConfig

from devpilot.agents.reviewer.agent import Finding, ReviewResult
from devpilot.models import GitHubIssue, TestResult, WorkspaceInfo
from devpilot.sandbox import ExecResult, Sandbox
from devpilot.workflow import (
    DevPilotState,
    build_workflow_graph,
    ingest_issue_node,
    publish_pr_node,
    qa_node,
    route_plan_decision,
    route_qa_verdict,
)
from devpilot.workflow import (
    test_node as workflow_test_node,
)


@pytest.mark.asyncio
async def test_ingest_issue_node_success() -> None:
    """Verifies that ingest_issue_node parses the issue URL and clones repository."""
    mock_instance = MagicMock()
    mock_instance.commands.run.return_value = ExecResult(stdout="", stderr="", exit_code=0)
    sandbox = Sandbox(instance=mock_instance)

    state: DevPilotState = {
        "issue_url": "https://github.com/my-org/my-repo/issues/42",
        "github_token": "dummy-token",
    }
    config: RunnableConfig = {"configurable": {"sandbox": sandbox}}

    result = await ingest_issue_node(state, config=config)

    assert result["issue"].issue_id == 42
    assert result["issue"].repository == "my-org/my-repo"
    assert result["workspace"].base_branch == "main"
    assert result["repair_attempts"] == 0
    assert result["plan_revisions"] == 0


@pytest.mark.asyncio
async def test_ingest_issue_node_invalid_url_raises() -> None:
    """Verifies that an unparseable issue URL raises a ValueError."""
    sandbox = Sandbox()
    state: DevPilotState = {"issue_url": "https://not-github.com/invalid"}
    config: RunnableConfig = {"configurable": {"sandbox": sandbox}}

    with pytest.raises(ValueError, match="Invalid GitHub issue URL"):
        await ingest_issue_node(state, config=config)


@pytest.mark.asyncio
async def test_test_node_executes_discovered_command() -> None:
    """Verifies that test_node runs discovered tests and records TestResult."""
    mock_instance = MagicMock()
    mock_instance.commands.run.return_value = ExecResult(
        stdout="pytest: 10 passed\n", stderr="", exit_code=0
    )
    sandbox = Sandbox(instance=mock_instance)
    sandbox.discover_tests = MagicMock(  # type: ignore[method-assign]
        return_value={"test_command": "pytest", "source": "config"}
    )

    state: DevPilotState = {}
    config: RunnableConfig = {"configurable": {"sandbox": sandbox}}

    result = await workflow_test_node(state, config=config)
    test_res: TestResult = result["test_result"]

    assert test_res.passed is True
    assert test_res.command == "pytest"
    assert "10 passed" in test_res.output


def test_qa_node_passed_verdict() -> None:
    """Verifies that passing tests and approved review produce qa_status='passed'."""
    state: DevPilotState = {
        "test_result": TestResult(passed=True, command="pytest", output="OK", exit_code=0),
        "review_result": ReviewResult(findings=[], summary="All clear", verdict="passed"),
        "repair_attempts": 0,
    }

    result = qa_node(state)
    assert result["qa_status"] == "passed"
    assert result["qa_feedback"] is None


def test_qa_node_fix_required_formats_feedback() -> None:
    """Verifies that failures produce actionable feedback and increment repair_attempts."""
    state: DevPilotState = {
        "test_result": TestResult(
            passed=False, command="pytest", output="AssertionError in test_calc", exit_code=1
        ),
        "review_result": ReviewResult(
            findings=[
                Finding(
                    category="security",
                    severity="high",
                    file_path="src/calc.py",
                    line_number=12,
                    message="SQL injection risk",
                    suggestion="Use parameterized query",
                )
            ],
            summary="1 finding",
            verdict="fix_required",
        ),
        "repair_attempts": 0,
    }

    result = qa_node(state)
    assert result["qa_status"] == "fix_required"
    assert result["repair_attempts"] == 1
    assert "AssertionError in test_calc" in result["qa_feedback"]
    assert "SQL injection risk" in result["qa_feedback"]


def test_qa_node_repair_limit_reached() -> None:
    """Verifies that exceeding 3 repair attempts sets qa_status='retry_limit_reached'."""
    state: DevPilotState = {
        "test_result": TestResult(passed=False, command="pytest", output="Error", exit_code=1),
        "repair_attempts": 3,
    }

    result = qa_node(state)
    assert result["qa_status"] == "retry_limit_reached"
    assert "Maximum automated repair attempts" in result["qa_feedback"]


@pytest.mark.asyncio
async def test_publish_pr_node_flow() -> None:
    """Verifies that publish_pr_node verifies git changes and creates PR."""
    mock_instance = MagicMock()
    mock_instance.commands.run.side_effect = [
        ExecResult(stdout="devpilot/issue-1\n", stderr="", exit_code=0),  # rev-parse
        ExecResult(stdout="1\n", stderr="", exit_code=0),  # rev-list (commits ahead)
        ExecResult(stdout="", stderr="", exit_code=0),  # git remote set-url
        ExecResult(stdout="", stderr="", exit_code=0),  # git push
        ExecResult(stdout="", stderr="", exit_code=0),  # cleanup remote set-url
    ]
    sandbox = Sandbox(instance=mock_instance)

    state: DevPilotState = {
        "issue": GitHubIssue(
            issue_id=1,
            issue_url="https://github.com/org/repo/issues/1",
            title="Bug in math",
            description="Fix it",
            repository="org/repo",
        ),
        "workspace": WorkspaceInfo(sandbox_id="sbx-1", repo_path="/repo", base_branch="main"),
        "branch_name": "devpilot/issue-1",
        "github_token": "dummy-token",
    }
    config: RunnableConfig = {"configurable": {"sandbox": sandbox}}

    result = await publish_pr_node(state, config=config)
    assert "pull_request_url" in result
    assert "https://github.com/org/repo/pull/101" in result["pull_request_url"]


def test_routing_decisions() -> None:
    """Verifies conditional routing decisions for planning and QA."""
    # Plan routing
    assert route_plan_decision({"plan_decision": "approve"}) == "implementer"
    assert route_plan_decision({"plan_decision": "revise", "plan_revisions": 1}) == "planner"
    assert route_plan_decision({"plan_decision": "revise", "plan_revisions": 3}) == "rejected"
    assert route_plan_decision({"plan_decision": "reject"}) == "rejected"

    # QA routing
    assert route_qa_verdict({"qa_status": "passed"}) == "publish_pr"
    assert route_qa_verdict({"qa_status": "fix_required"}) == "implementer"
    assert route_qa_verdict({"qa_status": "retry_limit_reached"}) == "limit_reached"


def test_workflow_graph_compiles() -> None:
    """Verifies that the main workflow graph structure compiles cleanly."""
    graph = build_workflow_graph()
    assert graph is not None
    # Verify key nodes are registered
    node_names = set(graph.nodes.keys())
    assert "ingest_issue" in node_names
    assert "planner" in node_names
    assert "implementer" in node_names
    assert "tester" in node_names
    assert "reviewer" in node_names
    assert "qa" in node_names
    assert "publish_pr" in node_names
