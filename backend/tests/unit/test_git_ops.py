from unittest.mock import MagicMock

import pytest

from devpilot.core.exceptions import BranchVerificationError
from devpilot.sandbox.git_ops import GitOps


def test_verify_branch_success() -> None:
    sandbox = MagicMock()
    # Mock git rev-parse --abbrev-ref HEAD returning branch name
    sandbox.exec.side_effect = [
        MagicMock(stdout="devpilot/issue-42\n", exit_code=0),  # current branch
        MagicMock(stdout="3\n", exit_code=0),  # commit count diff
    ]
    git_ops = GitOps(sandbox=sandbox, repo_path="/workspace/repo")
    # Should succeed without error
    git_ops.verify_branch(expected_branch="devpilot/issue-42", base_branch="main")


def test_verify_branch_mismatch_raises() -> None:
    sandbox = MagicMock()
    sandbox.exec.return_value = MagicMock(stdout="main\n", exit_code=0)
    git_ops = GitOps(sandbox=sandbox, repo_path="/workspace/repo")

    with pytest.raises(BranchVerificationError, match="Branch mismatch"):
        git_ops.verify_branch(expected_branch="devpilot/issue-42", base_branch="main")


def test_verify_branch_no_changes_raises() -> None:
    sandbox = MagicMock()
    sandbox.exec.side_effect = [
        MagicMock(stdout="devpilot/issue-42\n", exit_code=0),
        MagicMock(stdout="0\n", exit_code=0),  # 0 commits ahead
        MagicMock(stdout="", exit_code=0),  # git status clean
    ]
    git_ops = GitOps(sandbox=sandbox, repo_path="/workspace/repo")

    with pytest.raises(BranchVerificationError, match="No modifications found"):
        git_ops.verify_branch(expected_branch="devpilot/issue-42", base_branch="main")


def test_push_branch_token_cleanup_on_failure() -> None:
    sandbox = MagicMock()
    # Mock push failing
    sandbox.exec.side_effect = [
        MagicMock(exit_code=0),  # set-url with token
        MagicMock(exit_code=1, stderr="Remote rejected"),  # git push fails
        MagicMock(exit_code=0),  # cleanup set-url without token
    ]
    git_ops = GitOps(sandbox=sandbox, repo_path="/workspace/repo")

    with pytest.raises(RuntimeError, match="Git push failed"):
        git_ops.push_branch(
            branch_name="devpilot/issue-42",
            repo_slug="org/repo",
            token="ghs_secret12345",
        )

    # Verify cleanup was called in the finally block
    calls = sandbox.exec.call_args_list
    assert len(calls) == 3
    # Check that final call strips the token
    last_cmd = calls[-1][0][0]
    assert "ghs_secret12345" not in last_cmd
