from unittest.mock import MagicMock

from langchain_core.tools import tool

from devpilot.agents.base import build_agent
from devpilot.integrations.llm.client import get_llm_client


def test_get_llm_client_role_tiering() -> None:
    # Planner & Implementer use strong tier (e.g. gpt-4o)
    planner_llm = get_llm_client("planner", api_key="dummy")
    implementer_llm = get_llm_client("implementer", api_key="dummy")
    assert planner_llm.model_name == "gpt-4o"
    assert implementer_llm.model_name == "gpt-4o"

    # Reviewers & QA use cost-efficient tier (e.g. gpt-4o-mini)
    reviewer_llm = get_llm_client("reviewer", api_key="dummy")
    qa_llm = get_llm_client("qa", api_key="dummy")
    assert reviewer_llm.model_name == "gpt-4o-mini"
    assert qa_llm.model_name == "gpt-4o-mini"


def test_build_agent_graph() -> None:
    @tool
    def sample_tool(arg: str) -> str:
        """A sample test tool."""
        return f"result: {arg}"

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm

    agent = build_agent(
        role="implementer",
        tools=[sample_tool],
        system_prompt="You are a helpful coding assistant.",
        model=mock_llm,
    )
    assert agent is not None
