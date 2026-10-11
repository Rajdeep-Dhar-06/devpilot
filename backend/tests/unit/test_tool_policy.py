from devpilot.tools.policy import ToolPolicy


def test_reviewer_tool_policy() -> None:
    policy = ToolPolicy()
    allowed_tools = policy.get_allowed_tool_names(role="reviewer")
    assert "read_file" in allowed_tools
    assert "list_directory" in allowed_tools
    assert "write_file" not in allowed_tools
    assert "replace_in_file" not in allowed_tools
    assert "delegate_work" not in allowed_tools


def test_worker_tool_policy() -> None:
    policy = ToolPolicy()
    allowed_tools = policy.get_allowed_tool_names(role="worker")
    assert "read_file" in allowed_tools
    assert "write_file" in allowed_tools
    assert "replace_in_file" in allowed_tools
    assert "bash" in allowed_tools
    # Hard mandate: worker cannot invoke subagents (Decision 18)
    assert "delegate_work" not in allowed_tools


def test_implementer_tool_policy() -> None:
    policy = ToolPolicy()
    allowed_tools = policy.get_allowed_tool_names(role="implementer")
    assert "read_file" in allowed_tools
    assert "write_file" in allowed_tools
    assert "replace_in_file" in allowed_tools
    assert "bash" in allowed_tools
    assert "delegate_work" in allowed_tools


def test_planner_tool_policy() -> None:
    policy = ToolPolicy()
    allowed_tools = policy.get_allowed_tool_names(role="planner")
    assert "read_file" in allowed_tools
    assert "list_directory" in allowed_tools
    assert "web_search" in allowed_tools
    assert "retrieve_past_solutions" in allowed_tools
    assert "write_file" not in allowed_tools
    assert "delegate_work" not in allowed_tools
