"""Planning Agent: explores repository and creates a structured ImplementationPlan.

Beginner Guide:
Reading order of this file:
1. Types: ImplementationPlan
2. Prompt: Instructions given to the LLM
3. Node: plan_node (the LangGraph workflow step)
"""

from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from devpilot.llm import get_llm
from devpilot.models import DevPilotState
from devpilot.sandbox import Sandbox
from devpilot.tools.files import read_only_file_tools
from devpilot.tools.search import search_tools

# ---- 1. Types -------------------------------------------------------------


class ImplementationPlan(BaseModel):
    """Structured plan produced by the Planning Agent for human approval."""

    problem_summary: str = Field(..., description="Concise analysis of the problem")
    relevant_files: list[str] = Field(default_factory=list, description="Target files and modules")
    proposed_changes: list[str] = Field(
        default_factory=list, description="High-level architectural changes"
    )
    implementation_steps: list[str] = Field(
        default_factory=list, description="Step-by-step implementation plan"
    )
    testing_expectations: str = Field(
        ..., description="Verification strategy and commands to execute"
    )
    potential_risks: str = Field(..., description="Risks, regressions, or edge cases to watch for")


# ---- 2. Prompt ------------------------------------------------------------

PROMPT = """You are the DevPilot Planning Agent.

Your mission is to understand a reported GitHub issue, explore the target codebase,
and produce a structured, high-quality Implementation Plan for human approval.

Guidelines:
1. Explore the repository using find_files, search_code, and read_file tools.
2. Identify relevant source files, existing tests, and architectural patterns.
3. Formulate a concrete, step-by-step implementation plan.
4. DO NOT make any code modifications or execute git commits at this stage.
5. Structure your final output strictly according to the ImplementationPlan schema.
"""


# ---- 3. Node --------------------------------------------------------------


async def plan_node(state: DevPilotState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Workflow node: explores codebase and produces state['plan']."""
    configurable = (config or {}).get("configurable", {})
    sandbox: Sandbox = configurable.get("sandbox") or Sandbox()

    planner_tools = [
        *search_tools(sandbox),
        *read_only_file_tools(sandbox),
    ]
    agent = create_react_agent(
        get_llm("planner"),
        planner_tools,
        prompt=PROMPT,
        response_format=ImplementationPlan,
    )

    issue = state["issue"]
    feedback = state.get("plan_feedback") or "None"
    task = (
        f"GitHub Issue #{issue.issue_id}: {issue.title}\n\n"
        f"Repository: {issue.repository}\n\n"
        f"Description:\n{issue.description}\n\n"
        f"Human feedback to address (if revising): {feedback}\n\n"
        f"Explore the codebase and output the structured ImplementationPlan."
    )

    # Pass Langfuse callbacks and agent role tags from config
    run_config: RunnableConfig = {
        "callbacks": (config or {}).get("callbacks", []),
        "tags": list((config or {}).get("tags", [])) + ["agent:planner"],
        "metadata": {**((config or {}).get("metadata", {})), "agent_role": "planner"},
    }

    result = await agent.ainvoke({"messages": [HumanMessage(content=task)]}, config=run_config)
    structured = result.get("structured_response")
    if isinstance(structured, ImplementationPlan):
        plan = structured
    elif isinstance(structured, dict):
        plan = ImplementationPlan.model_validate(structured)
    else:
        raise RuntimeError("Planner failed to produce a valid ImplementationPlan.")

    return {"plan": plan}


# Alias for standalone testing / direct execution
run_planner = plan_node
