import pytest

from devpilot.core.exceptions import WorkerLimitExceededError, WorkerScopeConflictError
from devpilot.tools.subagent import WorkerManager


def test_worker_scope_conflict_detection() -> None:
    manager = WorkerManager(max_parallel_workers=5)

    # Worker 1 declared scope: src/calc.py
    manager.register_worker(
        worker_id="w-1",
        task="Fix division",
        declared_files=["src/calc.py"],
    )

    # Worker 2 trying to edit the same file -> conflict!
    with pytest.raises(WorkerScopeConflictError, match="conflicts with active worker"):
        manager.register_worker(
            worker_id="w-2",
            task="Add power",
            declared_files=["src/calc.py"],
        )

    # Worker 3 editing non-overlapping file -> allowed
    manager.register_worker(
        worker_id="w-3",
        task="Add power in other file",
        declared_files=["src/power.py"],
    )


def test_worker_concurrency_limit_exceeded() -> None:
    manager = WorkerManager(max_parallel_workers=5)

    # Spawn 5 workers with distinct scopes
    for i in range(5):
        manager.register_worker(
            worker_id=f"w-{i}",
            task=f"Task {i}",
            declared_files=[f"src/file_{i}.py"],
        )

    # 6th worker request -> immediate error (Decision 18)
    with pytest.raises(WorkerLimitExceededError, match="Concurrency cap of 5 reached"):
        manager.register_worker(
            worker_id="w-5",
            task="Task 5",
            declared_files=["src/file_5.py"],
        )

    # Completing a worker frees up a slot
    manager.complete_worker("w-0")
    manager.register_worker(
        worker_id="w-5",
        task="Task 5",
        declared_files=["src/file_5.py"],
    )


def test_worker_file_write_scope_enforcement() -> None:
    manager = WorkerManager(max_parallel_workers=5)
    manager.register_worker(
        worker_id="w-1",
        task="Edit only calc",
        declared_files=["src/calc.py"],
    )

    # Editing inside declared scope
    assert manager.is_file_in_scope("w-1", "src/calc.py") is True
    # Editing outside declared scope
    assert manager.is_file_in_scope("w-1", "src/secret.py") is False
