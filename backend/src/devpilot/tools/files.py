"""File manipulation tools for agents running inside the sandbox.

Beginner Guide:
These tools allow the LLM to inspect and modify code in the repository:
- `read_file`: Inspect file contents with line numbers and optional line offset/limit.
- `write_file`: Create or overwrite files in the workspace.
- `replace_in_file`: Perform surgical search-and-replace edits on existing code.

When worker subagents are used, their write access is strictly limited to
their declared file scope.
"""

import base64
import os
from collections.abc import Sequence

from langchain_core.tools import BaseTool, tool

from devpilot.sandbox import Sandbox


def _normalize_path(path: str) -> str:
    """Normalizes path separators for reliable scope comparison."""
    return os.path.normpath(path).replace("\\", "/")


def is_path_in_scope(file_path: str, scope: Sequence[str] | set[str]) -> bool:
    """Checks if a file path matches any declared file or folder in scope."""
    norm = _normalize_path(file_path)
    for declared in scope:
        norm_declared = _normalize_path(declared)
        if norm == norm_declared or norm.startswith(f"{norm_declared}/"):
            return True
    return False


def _write_file_content(sandbox: Sandbox, file_path: str, content: str) -> str:
    """Encodes and writes content safely to sandbox filesystem via base64."""
    sandbox.run(f"mkdir -p $(dirname {file_path})")
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    res = sandbox.run(f"echo '{b64}' | base64 -d > {file_path}")
    if res.exit_code != 0:
        return f"Error writing '{file_path}': {res.stderr.strip()}"
    return f"Successfully wrote {file_path}."


def file_tools(
    sandbox: Sandbox,
    scope: set[str] | Sequence[str] | None = None,
) -> list[BaseTool]:
    """Builds file editing and inspection tools with optional scope boundaries."""

    @tool
    def read_file(file_path: str, offset: int = 1, limit: int = 200) -> str:
        """Read lines from a file with line numbers (default: first 200 lines).

        Args:
            file_path: Relative path to the file.
            offset: Starting 1-based line number (default: 1).
            limit: Maximum number of lines to display (default: 200).
        """
        res = sandbox.run(f"cat {file_path}")
        if res.exit_code != 0:
            return f"Error: Could not read '{file_path}': {res.stderr.strip()}"

        all_lines = res.stdout.splitlines()
        total_lines = len(all_lines)
        start_idx = max(1, offset) - 1
        end_idx = min(total_lines, start_idx + limit)

        selected = all_lines[start_idx:end_idx]
        formatted = [f"{start_idx + i + 1:4d} | {line}" for i, line in enumerate(selected)]

        header = f"[{file_path} (lines {start_idx + 1}-{end_idx} of {total_lines})]"
        return f"{header}\n" + "\n".join(formatted)

    @tool
    def write_file(file_path: str, content: str) -> str:
        """Write content to a file in the workspace (creates the file if missing)."""
        if scope and not is_path_in_scope(file_path, scope):
            return f"Error: '{file_path}' is outside your authorized file scope: {list(scope)}"

        return _write_file_content(sandbox, file_path, content)

    @tool
    def replace_in_file(file_path: str, old_string: str, new_string: str) -> str:
        """Replace a specific substring with new content in an existing workspace file."""
        if scope and not is_path_in_scope(file_path, scope):
            return f"Error: '{file_path}' is outside your authorized file scope: {list(scope)}"

        read_res = sandbox.run(f"cat {file_path}")
        if read_res.exit_code != 0:
            return f"Error: File '{file_path}' does not exist or cannot be read."

        current = read_res.stdout
        if old_string not in current:
            return f"Error: Target text to replace was not found in '{file_path}'."

        updated = current.replace(old_string, new_string, 1)
        _write_file_content(sandbox, file_path, updated)
        return f"Successfully updated content in {file_path}."

    return [read_file, write_file, replace_in_file]


def read_only_file_tools(sandbox: Sandbox) -> list[BaseTool]:
    """Returns only the read_file tool (for planners and reviewers)."""
    tools = file_tools(sandbox)
    return [t for t in tools if t.name == "read_file"]
