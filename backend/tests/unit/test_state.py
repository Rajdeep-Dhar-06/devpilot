from devpilot.domain.enums import PlanDecision, PublicationDecision, QAStatus
from devpilot.domain.issue import GitHubIssue
from devpilot.domain.workspace import WorkspaceInfo
from devpilot.workflows.main.state import DevPilotState


def test_devpilot_state_structure() -> None:
    # Verify minimal initial state
    initial_state: DevPilotState = {
        "issue_url": "https://github.com/org/repo/issues/1",
        "repair_attempts": 0,
        "plan_revisions": 0,
    }
    assert initial_state["repair_attempts"] == 0
    assert initial_state["plan_revisions"] == 0

    # Verify extended populated state
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
        "plan_decision": PlanDecision.APPROVE,
        "qa_status": QAStatus.PASSED,
        "publication_decision": PublicationDecision.APPROVE,
    }
    assert full_state["branch_name"] == "devpilot/issue-1-fix"
    assert full_state["qa_status"] == QAStatus.PASSED
