"""Codebase search and navigation tools for agents running inside the sandbox.

Beginner Guide:
These tools allow agents (Planner, Implementer, Reviewer) to quickly navigate
large repositories without guessing paths or flooding their context window:
- `find_files`: Locate files by glob/filename pattern (e.g., "*.py", "*test*").
- `search_code`: Search code text or identifiers across the codebase with line numbers.
"""

import shlex
from collections.abc import Sequence

from langchain_core.tools import BaseTool, tool

from devpilot.sandbox import Sandbox
from devpilot.tools.files import is_path_in_scope


def search_tools(
    sandbox: Sandbox,
    scope: Sequence[str] | set[str] | None = None,
) -> list[BaseTool]:
    """Builds search and discovery tools with optional scope restrictions."""

    @tool
    def find_files(pattern: str = "*", path: str = ".") -> str:
        """Find files matching a glob pattern (e.g. '*.py' or '*test*') in a directory.

        Args:
            pattern: Glob or file pattern to search for (default: '*').
            path: Directory to start searching from (default: '.').
        """
        clean_path = shlex.quote(path)
        clean_pat = shlex.quote(pattern)
        cmd = (
            f"find {clean_path} -name {clean_pat} "
            "-not -path '*/.*' -not -path '*__pycache__*' "
            "-not -path '*/node_modules/*' -not -path '*/venv/*' "
            "| head -n 100"
        )
        res = sandbox.run(cmd)
        if res.exit_code != 0:
            return f"Error finding files: {res.stderr.strip()}"

        lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        if scope:
            lines = [p for p in lines if is_path_in_scope(p, scope)]

        if not lines:
            return f"No files matching '{pattern}' found in '{path}'."

        return "\n".join(lines)

    @tool
    def search_code(query: str, path: str = ".") -> str:
        """Search for a specific string, function, or keyword in code files.

        Args:
            query: The text string or identifier to search for.
            path: Directory or file to search within (default: '.').
        """
        clean_path = shlex.quote(path)
        clean_query = shlex.quote(query)
        cmd = (
            f"grep -rnI --exclude-dir='.git' --exclude-dir='venv' "
            f"--exclude-dir='__pycache__' --exclude-dir='node_modules' "
            f"-F -- {clean_query} {clean_path} | head -n 50"
        )
        res = sandbox.run(cmd)
        if res.exit_code != 0:
            return f"No matches found for '{query}' in '{path}'."

        lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
        if scope:
            filtered = []
            for line in lines:
                file_part = line.split(":", 1)[0]
                if is_path_in_scope(file_part, scope):
                    filtered.append(line)
            lines = filtered

        if not lines:
            return f"No matches found for '{query}' in '{path}'."

        count_notice = f" (showing first {len(lines)} matches)" if len(lines) >= 50 else ""
        return f"Found matches{count_notice}:\n" + "\n".join(lines)

    return [find_files, search_code]
