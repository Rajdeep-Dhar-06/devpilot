"""Worker subagent management, concurrency bounds, and file scope isolation.

Implements:
- Decision 2: Plain worker agent created with LangChain create_agent (invoked by delegate_work).
- Decision 18: Maximum 5 concurrent subagents, immediate error on overflow, no nesting.
- Decision 19: Declared file scope enforcement and overlap prevention.
"""

import os
from collections.abc import Sequence
from dataclasses import dataclass, field

from devpilot.core.exceptions import WorkerLimitExceededError, WorkerScopeConflictError


@dataclass
class ActiveWorker:
    """Tracks state and bounded file scope for a running subagent."""

    worker_id: str
    task: str
    declared_files: set[str] = field(default_factory=set)


class WorkerManager:
    """Manages active worker subagents, preventing scope collisions and concurrency overflow."""

    def __init__(self, max_parallel_workers: int = 5) -> None:
        self.max_parallel_workers = max_parallel_workers
        self._active_workers: dict[str, ActiveWorker] = {}

    @property
    def active_worker_count(self) -> int:
        """Returns the number of currently executing worker subagents."""
        return len(self._active_workers)

    def _normalize_path(self, path: str) -> str:
        """Normalizes file paths for reliable scope comparison."""
        return os.path.normpath(path).replace("\\", "/")

    def register_worker(
        self,
        worker_id: str,
        task: str,
        declared_files: Sequence[str],
    ) -> None:
        """Registers and validates a newly requested worker subagent.

        Raises:
            WorkerLimitExceededError: If the maximum parallel worker cap has been reached.
            WorkerScopeConflictError: If the declared files overlap with any active worker.
        """
        # Enforce concurrency cap (Decision 18)
        if len(self._active_workers) >= self.max_parallel_workers:
            raise WorkerLimitExceededError(
                f"Concurrency cap of {self.max_parallel_workers} reached. "
                f"Cannot spawn worker '{worker_id}'. Wait for active workers to complete."
            )

        # Normalize declared file paths
        normalized_new_files = {self._normalize_path(f) for f in declared_files}

        # Enforce file scope conflict rejection (Decision 19)
        for existing_id, worker in self._active_workers.items():
            overlap = normalized_new_files.intersection(worker.declared_files)
            if overlap:
                raise WorkerScopeConflictError(
                    f"Worker '{worker_id}' declared scope {list(overlap)} "
                    f"conflicts with active worker '{existing_id}'."
                )

        self._active_workers[worker_id] = ActiveWorker(
            worker_id=worker_id,
            task=task,
            declared_files=normalized_new_files,
        )

    def complete_worker(self, worker_id: str) -> None:
        """Marks a worker as completed and releases its concurrency slot and file scope."""
        self._active_workers.pop(worker_id, None)

    def is_file_in_scope(self, worker_id: str, file_path: str) -> bool:
        """Checks if a file path is within a worker's declared modification scope."""
        worker = self._active_workers.get(worker_id)
        if not worker:
            return False

        normalized_path = self._normalize_path(file_path)
        # Direct file match or parent directory prefix match
        for declared in worker.declared_files:
            if normalized_path == declared or normalized_path.startswith(f"{declared}/"):
                return True

        return False
