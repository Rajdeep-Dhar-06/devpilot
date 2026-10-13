"""Main workflow state and lifecycle definitions for DevPilot.

Beginner Guide:
DevPilotState is the central 'clipboard' passed through the entire LangGraph workflow.
Every step reads some fields from this state and writes its own results back.

Workflow Architecture:
START -> ingest_issue -> planner -> (plan_decision router)
    - approve -> implementer -> [tester, reviewer] (parallel) -> qa -> (qa router)
        - passed -> publish_pr -> END
        - fix_required -> implementer (automated repair loop, max 3)
        - limit_reached -> END
    - revise -> planner (max 3 revisions)
    - reject -> END
"""

from typing import Any
from urllib.parse import urlparse

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from devpilot.agents.implementer.agent import implement_node
from devpilot.agents.planner.agent import plan_node
from devpilot.agents.reviewer.agent import Finding, ReviewResult, ReviewState, build_review_graph
from devpilot.github import create_pull_request, fetch_issue, get_github_mcp_client
from devpilot.models import (
    Decision,
    DevPilotState,
    GitHubIssue,
    QAStatus,
    TestResult,
)
from devpilot.observability import record_human_decision, record_qa_result
from devpilot.sandbox import Sandbox

__all__ = [
    "Decision",
    "DevPilotState",
    "QAStatus",
    "build_workflow_graph",
    "ingest_issue_node",
    "publish_pr_node",
    "qa_node",
    "record_human_decision",
    "route_plan_decision",
    "route_qa_verdict",
    "test_node",
]


# ============================================================================
# Workflow Nodes
# ============================================================================


async def ingest_issue_node(
    state: DevPilotState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Ingests the GitHub issue and clones the repository in the sandbox."""
    configurable = (config or {}).get("configurable", {})
    sandbox: Sandbox = configurable.get("sandbox") or Sandbox()

    issue_url = state.get("issue_url", "")
    token = state.get("github_token")
    parsed = urlparse(issue_url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) >= 4 and parts[2] == "issues":
        owner, repo, issue_num_str = parts[0], parts[1], parts[3]
        issue_number = int(issue_num_str)
    else:
        raise ValueError(f"Invalid GitHub issue URL: '{issue_url}'")

    # Ingest issue via remote GitHub MCP or fallback mock for local tests
    if token and token not in ("dummy-token", "dummy-key"):
        client = get_github_mcp_client(token)
        issue = await fetch_issue(client, owner, repo, issue_number)
    else:
        issue = GitHubIssue(
            issue_id=issue_number,
            issue_url=issue_url,
            title=f"Issue #{issue_number}",
            description=f"Auto-ingested issue for {owner}/{repo}",
            repository=f"{owner}/{repo}",
        )

    # Clone repository into sandbox
    repo_url = f"https://github.com/{owner}/{repo}.git"
    workspace = sandbox.clone(repo_url, base_branch="main")

    return {
        "issue": issue,
        "workspace": workspace,
        "repair_attempts": 0,
        "plan_revisions": 0,
    }


async def test_node(state: DevPilotState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Discovers and runs project tests inside the sandbox."""
    configurable = (config or {}).get("configurable", {})
    sandbox: Sandbox = configurable.get("sandbox") or Sandbox()

    discovered = sandbox.discover_tests()
    test_cmd = discovered.get("test_command")

    if test_cmd:
        res = sandbox.run(test_cmd)
        test_result = TestResult(
            passed=(res.exit_code == 0),
            command=test_cmd,
            output=f"{res.stdout}\n{res.stderr}".strip(),
            exit_code=res.exit_code,
        )
    else:
        test_result = TestResult(
            passed=True,
            command="none",
            output="No test suite configured.",
            exit_code=0,
        )

    return {"test_result": test_result}


async def review_node(state: DevPilotState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Runs the 4-way parallel review subgraph and records the merged ReviewResult."""
    review_graph = build_review_graph()
    subgraph_state: ReviewState = {
        "issue": state["issue"],
        "plan": state.get("plan"),
        "branch_name": state.get("branch_name", "main"),
        "workspace": state["workspace"],
        "findings": [],
    }
    result = await review_graph.ainvoke(subgraph_state, config)
    return {"review_result": result.get("review_result")}


def qa_node(
    state: DevPilotState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Evaluates test and review results to decide whether repairs are required."""
    test_res: TestResult | None = state.get("test_result")
    review_res: ReviewResult | None = state.get("review_result")
    current_repairs = state.get("repair_attempts", 0)

    # Extract trace id or run id if available in config metadata or state
    metadata = (config or {}).get("metadata", {})
    trace_id = state.get("trace_id") or state.get("run_id") or metadata.get("run_id") or metadata.get("trace_id")

    tests_ok = test_res.passed if test_res else True
    review_ok = (review_res.verdict == "passed") if review_res else True

    if tests_ok and review_ok:
        record_qa_result(trace_id, status="passed", attempt=current_repairs)
        return {
            "qa_status": "passed",
            "qa_feedback": None,
        }

    # If issues were detected, check repair budget
    new_repairs = current_repairs + 1
    if new_repairs > 3:
        record_qa_result(
            trace_id,
            status="retry_limit_reached",
            attempt=new_repairs,
            feedback="Maximum automated repair attempts (3) exceeded.",
        )
        return {
            "qa_status": "retry_limit_reached",
            "qa_feedback": "Maximum automated repair attempts (3) exceeded.",
            "repair_attempts": new_repairs,
        }

    # Format actionable feedback for the implementer
    feedback_parts: list[str] = []
    if test_res and not test_res.passed:
        feedback_parts.append(
            f"Automated tests failed (exit code {test_res.exit_code}):\n{test_res.output[:800]}"
        )
    if review_res and review_res.verdict == "fix_required":
        blocking_items: list[str] = []
        for finding in review_res.findings:
            if isinstance(finding, Finding) and (
                finding.severity in ("critical", "high")
                or (finding.category == "security" and finding.severity == "medium")
            ):
                loc = f"{finding.file_path}:{finding.line_number or '?'}"
                blocking_items.append(
                    f"- [{finding.severity.upper()}] {loc}: {finding.message} "
                    f"(Suggestion: {finding.suggestion})"
                )
        if blocking_items:
            feedback_parts.append("Reviewer blocking findings:\n" + "\n".join(blocking_items))

    qa_fb = "\n\n".join(feedback_parts)
    record_qa_result(trace_id, status="fix_required", attempt=new_repairs, feedback=qa_fb)
    return {
        "qa_status": "fix_required",
        "qa_feedback": qa_fb,
        "repair_attempts": new_repairs,
    }


async def publish_pr_node(
    state: DevPilotState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Verifies changes, pushes working branch, and opens a Pull Request on GitHub."""
    configurable = (config or {}).get("configurable", {})
    sandbox: Sandbox = configurable.get("sandbox") or Sandbox()

    branch = state.get("branch_name") or f"devpilot/issue-{state['issue'].issue_id}"
    workspace = state["workspace"]
    issue = state["issue"]
    token = state.get("github_token") or "dummy-token"

    # Verify branch has commits / modifications (Decision 16)
    sandbox.verify_branch(branch, base_branch=workspace.base_branch)

    # Push to GitHub (token cleaned up in finally block, Decision 4)
    sandbox.push(branch, issue.repository, token)

    # Build comprehensive PR summary
    report = state.get("implementation_report")
    report_summary = (
        getattr(report, "summary", "")
        or (report.get("summary") if isinstance(report, dict) else "")
        or "Automated implementation completed."
    )
    test_info = "Passed" if state.get("test_result") and state["test_result"].passed else "N/A"
    review_summary = (
        state["review_result"].summary if state.get("review_result") else "All checks passed"
    )

    pr_body = (
        f"Fixes #{issue.issue_id}\n\n"
        f"### Summary\n{report_summary}\n\n"
        f"### Verification\n- Tests: {test_info}\n- Reviews: {review_summary}\n"
    )

    if token not in ("dummy-token", "dummy-key"):
        client = get_github_mcp_client(token)
        owner, repo = issue.repository.split("/", 1)
        pr_url = await create_pull_request(
            client,
            owner=owner,
            repo=repo,
            title=f"Fix #{issue.issue_id}: {issue.title}",
            head_branch=branch,
            base_branch=workspace.base_branch,
            body=pr_body,
        )
    else:
        pr_url = f"https://github.com/{issue.repository}/pull/{issue.issue_id + 100}"

    return {"pull_request_url": pr_url}


# ============================================================================
# Conditional Edge Routers
# ============================================================================


def route_plan_decision(state: DevPilotState) -> str:
    """Decides next step after human plan checkpoint."""
    decision = state.get("plan_decision", None)
    trace_id = state.get("trace_id") or state.get("run_id")
    if decision:
        record_human_decision(
            trace_id=trace_id,
            checkpoint_name="plan_review",
            decision=decision,
            comment=state.get("plan_feedback"),
        )

    if decision == "approve":
        return "implementer"
    if decision == "revise":
        if state.get("plan_revisions", 0) >= 3:
            return "rejected"
        return "planner"
    return "rejected"


def route_qa_verdict(state: DevPilotState) -> str:
    """Decides next step after QA evaluation."""
    status = state.get("qa_status", None)
    if status == "passed":
        return "publish_pr"
    if status == "fix_required":
        return "implementer"
    return "limit_reached"


# ============================================================================
# Main Graph Builder
# ============================================================================


def build_workflow_graph() -> CompiledStateGraph[Any, Any, Any, Any]:
    """Builds and compiles the complete DevPilot main workflow graph.

    Graph execution flow:
    START -> ingest_issue -> planner -> (plan_decision router)
        - approve -> implementer -> [tester, reviewer] (parallel) -> qa -> (qa router)
            - passed -> publish_pr -> END
            - fix_required -> implementer (repair loop)
            - limit_reached -> END
        - revise -> planner
        - reject -> END
    """
    graph = StateGraph(DevPilotState)

    # 1. Register all nodes
    graph.add_node("ingest_issue", ingest_issue_node)
    graph.add_node("planner", plan_node)
    graph.add_node("implementer", implement_node)
    graph.add_node("tester", test_node)
    graph.add_node("reviewer", review_node)
    graph.add_node("qa", qa_node)
    graph.add_node("publish_pr", publish_pr_node)

    # 2. Sequential ingestion -> planning
    graph.add_edge(START, "ingest_issue")
    graph.add_edge("ingest_issue", "planner")

    # 3. Human checkpoint routing after planning
    graph.add_conditional_edges(
        "planner",
        route_plan_decision,
        {
            "implementer": "implementer",
            "planner": "planner",
            "rejected": END,
        },
    )

    # 4. Implementer triggers parallel testing and code review
    graph.add_edge("implementer", "tester")
    graph.add_edge("implementer", "reviewer")

    # 5. Parallel branches join at QA
    graph.add_edge("tester", "qa")
    graph.add_edge("reviewer", "qa")

    # 6. QA routing: automated repair loop or publication
    graph.add_conditional_edges(
        "qa",
        route_qa_verdict,
        {
            "publish_pr": "publish_pr",
            "implementer": "implementer",
            "limit_reached": END,
        },
    )

    # 7. Complete after PR publication
    graph.add_edge("publish_pr", END)

    return graph.compile()
