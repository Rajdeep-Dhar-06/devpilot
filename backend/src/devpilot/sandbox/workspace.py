"""Workspace preparation inside the sandbox."""

from devpilot.domain.workspace import WorkspaceInfo
from devpilot.sandbox.provider import E2BSandboxProvider


class WorkspaceManager:
    """Initializes and configures git repository workspaces in the sandbox."""

    def __init__(self, provider: E2BSandboxProvider) -> None:
        self.provider = provider

    def prepare_workspace(
        self,
        sandbox_id: str,
        repo_url: str,
        base_branch: str = "main",
        workspace_root: str = "/workspace/repo",
    ) -> WorkspaceInfo:
        """Clones target repository and prepares workspace directory."""
        self.provider.exec(sandbox_id, "mkdir -p /workspace")
        self.provider.exec(
            sandbox_id,
            f"git clone {repo_url} {workspace_root}",
        )
        self.provider.exec(
            sandbox_id,
            f"git checkout {base_branch}",
            cwd=workspace_root,
        )
        # Configure local git actor for automated commits
        self.provider.exec(
            sandbox_id,
            'git config user.name "DevPilot Agent"',
            cwd=workspace_root,
        )
        self.provider.exec(
            sandbox_id,
            'git config user.email "devpilot-agent@devpilot.ai"',
            cwd=workspace_root,
        )

        return WorkspaceInfo(
            sandbox_id=sandbox_id,
            repo_path=workspace_root,
            base_branch=base_branch,
        )
