"""Unit tests for DevPilotState structure and lifecycle fields."""

from devpilot.models import GitHubIssue, WorkspaceInfo
from devpilot.workflow import DevPilotState


def test_devpilot_state_structure() -> None:
    """Verifies that DevPilotState instantiates properly with partial and full fields."""
    initial_state: DevPilotState = {
        "issue_url": "https://github.com/org/repo/issues/1",
        "repair_attempts": 0,
        "plan_revisions": 0,
    }
    assert initial_state["repair_attempts"] == 0
    assert initial_state["plan_revisions"] == 0

    full_state: DevPilotState = {
        "issue_url": "https://github.com/org/repo/issues/1",
        "repair_attempts": 1,
        "plan_revisions": 2,
        "issue": GitHubIssue(
            issue_id=1,
            issue_url="https://github.com/org/repo/issues/1",
            title="Title",
            description="Desc",
            repository="org/repo",
        ),
        "workspace": WorkspaceInfo(
            sandbox_id="sbx-abc",
            repo_path="/path",
            base_branch="main",
        ),
        "branch_name": "devpilot/issue-1-fix",
        "plan_decision": "approve",
        "qa_status": "passed",
        "publication_decision": "approve",
    }
    assert full_state["branch_name"] == "devpilot/issue-1-fix"
    assert full_state["qa_status"] == "passed"
    assert full_state["publication_decision"] == "approve"
