"""Unit tests for workspace git branch verification and secure push."""

from unittest.mock import MagicMock

import pytest

from devpilot.sandbox import ExecResult, Sandbox


def test_verify_branch_success() -> None:
    """Verifies that branch verification succeeds when commits ahead exist."""
    mock_instance = MagicMock()
    sandbox = Sandbox(instance=mock_instance, repo_path="/workspace/repo")

    # Mock git commands via sandbox.run
    mock_instance.commands.run.side_effect = [
        ExecResult(stdout="devpilot/issue-42\n", stderr="", exit_code=0),  # current branch
        ExecResult(stdout="3\n", stderr="", exit_code=0),  # commits ahead
    ]

    sandbox.verify_branch(expected_branch="devpilot/issue-42", base_branch="main")


def test_verify_branch_mismatch_raises() -> None:
    """Verifies that being on the wrong branch raises an error."""
    mock_instance = MagicMock()
    sandbox = Sandbox(instance=mock_instance, repo_path="/workspace/repo")
    mock_instance.commands.run.return_value = ExecResult(stdout="main\n", stderr="", exit_code=0)

    with pytest.raises(RuntimeError, match="Branch mismatch"):
        sandbox.verify_branch(expected_branch="devpilot/issue-42", base_branch="main")


def test_verify_branch_no_changes_raises() -> None:
    """Verifies that a branch with zero commits and clean working tree is rejected."""
    mock_instance = MagicMock()
    sandbox = Sandbox(instance=mock_instance, repo_path="/workspace/repo")
    mock_instance.commands.run.side_effect = [
        ExecResult(stdout="devpilot/issue-42\n", stderr="", exit_code=0),
        ExecResult(stdout="0\n", stderr="", exit_code=0),  # 0 commits ahead
        ExecResult(stdout="", stderr="", exit_code=0),  # clean git status
    ]

    with pytest.raises(RuntimeError, match="No changes or commits detected"):
        sandbox.verify_branch(expected_branch="devpilot/issue-42", base_branch="main")


def test_push_branch_token_cleanup_on_failure() -> None:
    """Verifies that the push token is always cleaned up in finally block (Decision 4)."""
    mock_instance = MagicMock()
    sandbox = Sandbox(instance=mock_instance, repo_path="/workspace/repo")

    # Set URL, push fails, cleanup
    mock_instance.commands.run.side_effect = [
        ExecResult(stdout="", stderr="", exit_code=0),  # set-url with token
        ExecResult(stdout="", stderr="Remote rejected", exit_code=1),  # git push fails
        ExecResult(stdout="", stderr="", exit_code=0),  # cleanup set-url
    ]

    with pytest.raises(RuntimeError, match="Git push failed"):
        sandbox.push(
            branch_name="devpilot/issue-42",
            repo_slug="org/repo",
            token="ghs_secret12345",
        )

    # Verify cleanup was called
    calls = mock_instance.commands.run.call_args_list
    assert len(calls) == 3
    last_cmd = calls[-1][0][0]
    assert "ghs_secret12345" not in last_cmd


def test_git_diff_tool_output() -> None:
    """Verifies that git_diff_tool invokes git diff and formats output."""
    from devpilot.tools.git import git_diff_tool

    mock_instance = MagicMock()
    mock_instance.commands.run.side_effect = [
        ExecResult(stdout=" src/calc.py | 2 +-\n 1 file changed", stderr="", exit_code=0),
        ExecResult(
            stdout="diff --git a/src/calc.py b/src/calc.py\n+new line", stderr="", exit_code=0
        ),
    ]
    sandbox = Sandbox(instance=mock_instance)

    diff_tool = git_diff_tool(sandbox)
    res = diff_tool.invoke({"base_branch": "main"})
    assert "=== Git Diff Stat ===" in res
    assert "src/calc.py" in res
    assert "+new line" in res
