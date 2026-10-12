"""Planning Agent implementation (Section 4).

Explores codebase and formulates a structured ImplementationPlan for HITL approval.
"""

from collections.abc import Sequence
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool

from devpilot.agents.base import build_agent, load_prompt
from devpilot.domain.issue import GitHubIssue
from devpilot.domain.plan import ImplementationPlan
from devpilot.domain.workspace import WorkspaceInfo


async def run_planner(
    issue: GitHubIssue,
    workspace: WorkspaceInfo,
    tools: Sequence[BaseTool] | None = None,
    model: BaseChatModel | None = None,
) -> ImplementationPlan:
    """Executes the planning agent to produce a structured ImplementationPlan."""
    prompt = load_prompt("planner")

    agent = build_agent(
        role="planner",
        tools=tools or [],
        system_prompt=prompt,
        model=model,
        response_format=ImplementationPlan,
    )

    user_prompt = (
        f"Generate a structured Implementation Plan for the following GitHub issue:\n\n"
        f"Issue #{issue.issue_id}: {issue.title}\n"
        f"Repository: {issue.repository}\n"
        f"Base Branch: {workspace.base_branch}\n"
        f"Labels: {', '.join(issue.labels)}\n\n"
        f"Description:\n{issue.description}\n\n"
        f"Explore the codebase if tools are available and output the ImplementationPlan."
    )

    result: dict[str, Any] = await agent.ainvoke({"messages": [HumanMessage(content=user_prompt)]})

    structured = result.get("structured_response")
    if isinstance(structured, ImplementationPlan):
        return structured
    if isinstance(structured, dict):
        return ImplementationPlan.model_validate(structured)

    raise RuntimeError("Planner agent failed to return a structured ImplementationPlan.")
