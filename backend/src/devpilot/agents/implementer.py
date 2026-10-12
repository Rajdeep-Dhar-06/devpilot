"""Implementation Agent implementation (Section 5).

Safely executes an approved plan inside an isolated workspace.
"""

from collections.abc import Sequence
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool

from devpilot.agents.base import build_agent, load_prompt
from devpilot.domain.implementation import ImplementationReport
from devpilot.domain.issue import GitHubIssue
from devpilot.domain.plan import ImplementationPlan
from devpilot.domain.workspace import WorkspaceInfo


async def run_implementer(
    issue: GitHubIssue,
    plan: ImplementationPlan,
    branch_name: str,
    workspace: WorkspaceInfo,
    tools: Sequence[BaseTool] | None = None,
    model: BaseChatModel | None = None,
) -> ImplementationReport:
    """Executes the implementation agent on the designated branch."""
    prompt = load_prompt("implementer")

    agent = build_agent(
        role="implementer",
        tools=tools or [],
        system_prompt=prompt,
        model=model,
        response_format=ImplementationReport,
    )

    user_prompt = (
        f"You are assigned to implement an approved plan on working branch '{branch_name}'.\n\n"
        f"GitHub Issue #{issue.issue_id}: {issue.title}\n"
        f"Description:\n{issue.description}\n\n"
        f"Approved Plan:\n"
        f"Summary: {plan.problem_summary}\n"
        f"Relevant Files: {', '.join(plan.relevant_files)}\n"
        f"Proposed Changes: {', '.join(plan.proposed_changes)}\n"
        f"Steps: {', '.join(plan.implementation_steps)}\n"
        f"Testing Expectations: {plan.testing_expectations}\n"
        f"Risks: {plan.potential_risks}\n\n"
        f"Mandatory First Action: Verify that you are on branch '{branch_name}'.\n"
        f"Perform all necessary code changes, run local tests, and output the ImplementationReport."
    )

    result: dict[str, Any] = await agent.ainvoke({"messages": [HumanMessage(content=user_prompt)]})

    structured = result.get("structured_response")
    if isinstance(structured, ImplementationReport):
        return structured
    if isinstance(structured, dict):
        return ImplementationReport.model_validate(structured)

    raise RuntimeError("Implementer agent failed to return a structured ImplementationReport.")
