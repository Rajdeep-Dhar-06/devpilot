"""Unit tests for LLM client factory with tiered role mapping."""

from devpilot.llm import get_llm


def test_get_llm_role_tiering() -> None:
    """Verifies that planner/implementer get gpt-4o, while reviewers/qa/workers get gpt-4o-mini."""
    planner_llm = get_llm("planner", api_key="dummy-key")
    implementer_llm = get_llm("implementer", api_key="dummy-key")
    assert planner_llm.model_name == "gpt-4o"
    assert implementer_llm.model_name == "gpt-4o"

    reviewer_llm = get_llm("reviewer", api_key="dummy-key")
    qa_llm = get_llm("qa", api_key="dummy-key")
    worker_llm = get_llm("worker", api_key="dummy-key")
    assert reviewer_llm.model_name == "gpt-4o-mini"
    assert qa_llm.model_name == "gpt-4o-mini"
    assert worker_llm.model_name == "gpt-4o-mini"
