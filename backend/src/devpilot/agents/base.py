"""Shared agent factory and execution helpers."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from devpilot.integrations.llm.client import get_llm_client

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(prompt_name: str) -> str:
    """Loads an agent system prompt from the markdown prompt directory."""
    prompt_path = PROMPTS_DIR / f"{prompt_name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


def build_agent(
    role: str,
    tools: Sequence[BaseTool],
    system_prompt: str,
    model: BaseChatModel | None = None,
    response_format: type[BaseModel] | None = None,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Builds a standardized ReAct agent with tools and prompt (Section 6)."""
    resolved_model = model or get_llm_client(role=role)
    return create_react_agent(
        model=resolved_model,
        tools=tools,
        prompt=system_prompt,
        response_format=response_format,
    )


async def invoke_agent(
    agent: CompiledStateGraph[Any, Any, Any, Any],
    prompt: str,
) -> dict[str, Any]:
    """Invokes a compiled agent graph with a user message prompt."""
    result = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
    return dict(result)
