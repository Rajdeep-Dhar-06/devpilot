"""Tool registry for constructing role-specific LangChain toolsets."""

from typing import Any

from langchain_core.tools import BaseTool, tool

from devpilot.tools.file_ops import FileOpsTools
from devpilot.tools.policy import ToolPolicy
from devpilot.tools.shell import ShellTool
from devpilot.tools.subagent import WorkerManager


class ToolRegistry:
    """Constructs permitted LangChain tools for agents based on their assigned role."""

    def __init__(
        self,
        sandbox_provider: Any,
        sandbox_id: str,
        workspace_cwd: str = "/workspace/repo",
        worker_manager: WorkerManager | None = None,
        policy: ToolPolicy | None = None,
    ) -> None:
        self.sandbox = sandbox_provider
        self.sandbox_id = sandbox_id
        self.workspace_cwd = workspace_cwd
        self.worker_manager = worker_manager or WorkerManager()
        self.policy = policy or ToolPolicy()

        self.file_ops = FileOpsTools(self.sandbox, self.worker_manager)
        self.shell = ShellTool(self.sandbox)

    def get_tools_for_role(self, role: str) -> list[BaseTool]:
        """Assembles a list of LangChain tools permissible for the requested agent role."""
        allowed_names = self.policy.get_allowed_tool_names(role)
        tools: list[BaseTool] = []

        if "read_file" in allowed_names:

            @tool
            def read_file(file_path: str) -> str:
                """Read the complete content of a file from the repository workspace."""
                return self.file_ops.read_file(self.sandbox_id, file_path)

            tools.append(read_file)

        if "list_directory" in allowed_names:

            @tool
            def list_directory(path: str = ".") -> list[str]:
                """List all files and folders in a workspace directory."""
                return self.file_ops.list_directory(self.sandbox_id, path)

            tools.append(list_directory)

        if "write_file" in allowed_names:

            @tool
            def write_file(file_path: str, content: str) -> str:
                """Write content to a file in the workspace (creates file if not present)."""
                self.file_ops.write_file(self.sandbox_id, file_path, content)
                return f"Successfully wrote {file_path}"

            tools.append(write_file)

        if "replace_in_file" in allowed_names:

            @tool
            def replace_in_file(file_path: str, old_string: str, new_string: str) -> str:
                """Replace a specific substring with new content in a workspace file."""
                self.file_ops.replace_in_file(self.sandbox_id, file_path, old_string, new_string)
                return f"Successfully replaced content in {file_path}"

            tools.append(replace_in_file)

        if "bash" in allowed_names:

            @tool
            def bash(command: str) -> str:
                """Execute a shell command inside the workspace sandbox."""
                return self.shell.execute(
                    self.sandbox_id,
                    command,
                    role=role,
                    cwd=self.workspace_cwd,
                )

            tools.append(bash)

        if "delegate_work" in allowed_names:

            @tool
            async def delegate_work(task: str, declared_files: list[str]) -> str:
                """Delegate an isolated, scoped task to a parallel worker subagent.

                Args:
                    task: Detailed description of the subtask for the worker to complete.
                    declared_files: Exclusive list of files this worker is permitted to modify.
                """
                import uuid

                from langchain_core.messages import HumanMessage

                from devpilot.agents.base import build_agent, load_prompt

                worker_id = f"worker-{uuid.uuid4().hex[:6]}"
                self.worker_manager.register_worker(
                    worker_id=worker_id,
                    task=task,
                    declared_files=declared_files,
                )
                try:
                    worker_tools = self.get_tools_for_role("worker")
                    worker_prompt = (
                        load_prompt("worker")
                        + f"\n\nAssigned Task: {task}\nDeclared File Scope: {declared_files}"
                    )
                    worker_agent = build_agent(
                        role="worker",
                        tools=worker_tools,
                        system_prompt=worker_prompt,
                    )
                    res = await worker_agent.ainvoke(
                        {"messages": [HumanMessage(content=f"Execute task: {task}")]}
                    )
                    messages = res.get("messages", [])
                    if messages:
                        return str(messages[-1].content)
                    return "Task completed successfully."
                finally:
                    self.worker_manager.complete_worker(worker_id)

            tools.append(delegate_work)

        return tools
