"""Subagent delegation tool for parallel worker tasks.

Beginner Guide:
When an implementation task has independent parts (like editing two different
files), the Implementer Agent can invoke `delegate_work` to launch a worker
subagent.

Rules (Decisions 18 & 19):
- Maximum 5 parallel workers at any time.
- Workers must declare their file scope upfront; overlapping files are rejected.
- Workers cannot delegate work to other agents (no nesting).
- Workers are restricted to scoped file/search tools and `run_tests` (no arbitrary bash).
"""

import uuid
from collections.abc import Sequence

from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, tool
from langgraph.prebuilt import create_react_agent

from devpilot.llm import get_llm
from devpilot.sandbox import Sandbox
from devpilot.tools.files import _normalize_path, file_tools
from devpilot.tools.search import search_tools
from devpilot.tools.shell import run_tests_tool

WORKER_PROMPT = """You are a DevPilot Worker Subagent.
Your mission is to perform a specific, bounded coding task within your declared file scope.

Rules:
1. Only inspect and modify files within your assigned file scope.
2. Run local tests or lint checks using the `run_tests` tool to verify your changes.
3. You cannot delegate work to other agents.
4. Provide a clear summary of what you did when done.
"""


class WorkerTracker:
    """Tracks active worker subagents, concurrency limits, and file scopes."""

    def __init__(self, max_parallel: int = 5) -> None:
        self.max_parallel = max_parallel
        self._active: dict[str, set[str]] = {}

    @property
    def active_count(self) -> int:
        return len(self._active)

    def register(self, worker_id: str, declared_files: Sequence[str]) -> None:
        """Validates concurrency and scope, then registers a new worker."""
        if len(self._active) >= self.max_parallel:
            raise RuntimeError(
                f"Concurrency limit of {self.max_parallel} workers reached. "
                f"Cannot spawn '{worker_id}'."
            )

        norm_new = {_normalize_path(f) for f in declared_files}
        for existing_id, existing_scope in self._active.items():
            overlap = norm_new.intersection(existing_scope)
            if overlap:
                raise RuntimeError(
                    f"Worker '{worker_id}' scope {list(overlap)} conflicts with "
                    f"active worker '{existing_id}'."
                )

        self._active[worker_id] = norm_new

    def release(self, worker_id: str) -> None:
        """Releases the worker's slot and scope upon completion."""
        self._active.pop(worker_id, None)


# Default global tracker instance
DEFAULT_TRACKER = WorkerTracker(max_parallel=5)


def delegate_tool(sandbox: Sandbox, tracker: WorkerTracker | None = None) -> BaseTool:
    """Builds the delegate_work tool for the Implementer Agent."""
    active_tracker = tracker or DEFAULT_TRACKER

    @tool
    async def delegate_work(task: str, declared_files: list[str]) -> str:
        """Delegate an isolated subtask to a worker agent.

        Args:
            task: Clear description of the task for the worker.
            declared_files: The exclusive list of files this worker is permitted to edit.
        """
        worker_id = f"worker-{uuid.uuid4().hex[:6]}"
        active_tracker.register(worker_id, declared_files)

        try:
            # Workers get scoped file/search tools + run_tests, but NO arbitrary bash or delegation
            worker_tools = [
                *file_tools(sandbox, scope=declared_files),
                *search_tools(sandbox, scope=declared_files),
                run_tests_tool(sandbox),
            ]
            agent = create_react_agent(
                get_llm("worker"),
                worker_tools,
                prompt=f"{WORKER_PROMPT}\nAssigned Files: {declared_files}",
            )
            res = await agent.ainvoke({"messages": [HumanMessage(task)]})
            messages = res.get("messages", [])
            if messages:
                return str(messages[-1].content)
            return "Worker finished task successfully."
        finally:
            active_tracker.release(worker_id)

    return delegate_work
