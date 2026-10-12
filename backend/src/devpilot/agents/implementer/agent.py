"""Implementation Agent: safely implements an approved plan inside an isolated workspace.

Beginner Guide:
Reading order of this file:
1. Types: ImplementationReport
2. Prompt: Rules given to the LLM
3. Node: implement_node (the LangGraph workflow step)
"""

from typing import Any, Literal

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from devpilot.llm import get_llm
from devpilot.models import DevPilotState
from devpilot.sandbox import Sandbox
from devpilot.tools.delegate import delegate_tool
from devpilot.tools.files import file_tools
from devpilot.tools.search import search_tools
from devpilot.tools.shell import bash_tool

# ---- 1. Types -------------------------------------------------------------


class ImplementationReport(BaseModel):
    """Report returned by the Implementer Agent after modifying the repository."""

    changed_files: list[str] = Field(default_factory=list, description="Files modified or added")
    status: Literal["completed", "blocked"] = Field(
        ..., description="Outcome status: 'completed' or 'blocked'"
    )
    summary: str = Field(default="", description="Summary of work completed and tests run")
    tests_run: list[str] = Field(default_factory=list, description="Checks run locally")
    remaining_risks: str = Field(default="", description="Risks identified during implementation")
    blockers: str | None = Field(default=None, description="Any blocking errors encountered")


# ---- 2. Prompt ------------------------------------------------------------

PROMPT = """You are the DevPilot Implementation Agent.

Your mission is to safely and precisely implement an approved plan inside an
isolated development workspace.

Mandatory Execution Rules:
1. Code Modification: Use `replace_in_file` for targeted edits or `write_file` for new files.
2. Local Verification: Run local project tests and linters using `bash` to verify your changes.
3. Delegation: You may invoke `delegate_work` to assign bounded subtasks to worker agents.
4. Final Report: Return a structured ImplementationReport summarizing changed files and status.
"""


# ---- 3. Node --------------------------------------------------------------


async def implement_node(
    state: DevPilotState, config: RunnableConfig | None = None
) -> dict[str, Any]:
    """Workflow node: implements approved plan on the working branch."""
    configurable = (config or {}).get("configurable", {})
    sandbox: Sandbox = configurable.get("sandbox") or Sandbox()

    branch_name = state.get("branch_name") or f"devpilot/issue-{state['issue'].issue_id}"

    # Build toolset for implementation
    tools = [
        *search_tools(sandbox),
        *file_tools(sandbox),
        bash_tool(sandbox),
        delegate_tool(sandbox),
    ]

    agent = create_react_agent(
        get_llm("implementer"),
        tools,
        prompt=PROMPT,
        response_format=ImplementationReport,
    )

    issue = state["issue"]
    plan = state["plan"]
    qa_feedback = state.get("qa_feedback") or "None"

    task = (
        f"Implement approved plan for Issue #{issue.issue_id}: {issue.title}\n\n"
        f"Branch: '{branch_name}'\n"
        f"Plan Summary: {getattr(plan, 'problem_summary', str(plan))}\n"
        f"Relevant Files: {getattr(plan, 'relevant_files', [])}\n"
        f"QA Repair Feedback (if fixing previous attempt): {qa_feedback}\n\n"
        f"Perform all necessary changes, test locally, and produce the ImplementationReport."
    )

    result = await agent.ainvoke({"messages": [HumanMessage(content=task)]})
    structured = result.get("structured_response")
    if isinstance(structured, ImplementationReport):
        report = structured
    elif isinstance(structured, dict):
        report = ImplementationReport.model_validate(structured)
    else:
        raise RuntimeError("Implementer failed to produce a valid ImplementationReport.")

    return {
        "branch_name": branch_name,
        "implementation_report": report,
    }


# Alias for standalone testing / direct execution
run_implementer = implement_node
