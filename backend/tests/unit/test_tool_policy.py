from devpilot.tools.policy import ToolPolicy


def test_reviewer_tool_policy() -> None:
    policy = ToolPolicy()
    allowed = policy.get_allowed_tool_names(role="reviewer")
    assert "read_file" in allowed
    assert "list_directory" in allowed
    # Allowed MCP read tools
    assert "get_issue" in allowed
    # Forbidden write tools
    assert "write_file" not in allowed
    assert "replace_in_file" not in allowed
    assert "delegate_work" not in allowed


def test_worker_tool_policy() -> None:
    policy = ToolPolicy()
    allowed = policy.get_allowed_tool_names(role="worker")
    assert "read_file" in allowed
    assert "write_file" in allowed
    assert "replace_in_file" in allowed
    assert "bash" in allowed
    # Workers cannot invoke subagents (Decision 18)
    assert "delegate_work" not in allowed


def test_implementer_tool_policy() -> None:
    policy = ToolPolicy()
    allowed = policy.get_allowed_tool_names(role="implementer")
    assert "read_file" in allowed
    assert "write_file" in allowed
    assert "replace_in_file" in allowed
    assert "bash" in allowed
    assert "delegate_work" in allowed


def test_planner_tool_policy() -> None:
    policy = ToolPolicy()
    allowed = policy.get_allowed_tool_names(role="planner")
    assert "read_file" in allowed
    assert "list_directory" in allowed
    # MCP search & inspection tools
    assert "get_issue" in allowed
    assert "search_issues" in allowed
    assert "write_file" not in allowed
    assert "delegate_work" not in allowed
