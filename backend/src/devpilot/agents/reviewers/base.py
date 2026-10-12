"""Shared execution logic and schemas for review specialists."""

from collections.abc import Sequence
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from devpilot.agents.base import build_agent, load_prompt
from devpilot.domain.enums import ReviewCategory
from devpilot.domain.review import Finding
from devpilot.workflows.review.state import ReviewState


class ReviewerOutput(BaseModel):
    """Structured output expected from code review specialists."""

    findings: list[Finding] = Field(
        default_factory=list,
        description="List of code review findings identified",
    )


async def run_reviewer_agent(
    category: ReviewCategory,
    state: ReviewState,
    tools: Sequence[BaseTool] | None = None,
    model: BaseChatModel | None = None,
) -> list[Finding]:
    """Runs a specialized reviewer ReAct agent and extracts structured findings."""
    prompt = load_prompt(f"reviewers/{category.value}")

    active_tools: Sequence[BaseTool] = tools or state.get("tools") or []

    agent = build_agent(
        role="reviewer",
        tools=active_tools,
        system_prompt=prompt,
        model=model,
        response_format=ReviewerOutput,
    )

    review_prompt = (
        f"Review the code changes on branch '{state['branch_name']}' against base branch "
        f"'{state['workspace'].base_branch}'.\n\n"
        f"GitHub Issue:\nTitle: {state['issue'].title}\n"
        f"Description:\n{state['issue'].description}\n\n"
        f"Implementation Plan:\n{state['plan'].problem_summary}\n\n"
        f"Focus strictly on {category.value} issues. Inspect changes and return findings."
    )

    result: dict[str, Any] = await agent.ainvoke(
        {"messages": [HumanMessage(content=review_prompt)]}
    )

    structured: Any = result.get("structured_response")
    findings: list[Finding] = []

    if isinstance(structured, ReviewerOutput):
        findings = structured.findings
    elif isinstance(structured, dict) and "findings" in structured:
        findings = [
            f if isinstance(f, Finding) else Finding.model_validate(f)
            for f in structured["findings"]
        ]

    # Ensure findings are properly tagged with this reviewer's category
    for f in findings:
        f.category = category

    return findings
