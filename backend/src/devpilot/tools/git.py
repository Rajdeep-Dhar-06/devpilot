"""Git inspection tools for sandbox reviewers and agents.

Beginner Guide:
Reviewers need to see exactly what changed in the pull request. Instead of
running raw terminal commands, `git_diff` provides the formatted diff between
the feature branch and the base branch.
"""

import shlex

from langchain_core.tools import BaseTool, tool

from devpilot.sandbox import Sandbox


def git_diff_tool(sandbox: Sandbox) -> BaseTool:
    """Returns a dedicated git diff tool for reviewers to inspect PR changes."""

    @tool
    def git_diff(base_branch: str = "main") -> str:
        """Inspect the git diff of code changes on the current branch compared to base branch.

        Args:
            base_branch: The base branch to compare against (default: 'main').
        """
        clean_base = shlex.quote(base_branch)
        stat_res = sandbox.run(f"git diff --stat {clean_base}")
        diff_res = sandbox.run(f"git diff {clean_base}")

        if diff_res.exit_code != 0:
            return f"Error running git diff against '{base_branch}': {diff_res.stderr.strip()}"

        diff_text = diff_res.stdout.strip()
        stat_text = stat_res.stdout.strip()

        if not diff_text:
            return f"No differences detected between current branch and '{base_branch}'."

        lines = diff_text.splitlines()
        if len(lines) > 250:
            truncated = "\n".join(lines[:250])
            return (
                f"=== Git Diff Stat ===\n{stat_text}\n\n"
                f"=== Diff (showing first 250 of {len(lines)} lines) ===\n{truncated}\n"
                "... [diff truncated; use read_file to inspect specific files in detail]"
            )

        return f"=== Git Diff Stat ===\n{stat_text}\n\n=== Diff ===\n{diff_text}"

    return git_diff
