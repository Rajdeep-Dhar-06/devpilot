"""Tool access policy by agent role.

Implements:
- Decision 3: Reviewers only have read-only tools.
- Decision 18: Delegated subagents cannot invoke other agents (no delegate_work).
"""

from collections.abc import Mapping


class ToolPolicy:
    """Defines which tools each agent role is allowed to invoke."""

    def __init__(self) -> None:
        self._role_permissions: Mapping[str, set[str]] = {
            "planner": {
                "read_file",
                "list_directory",
                "web_search",
                "retrieve_past_solutions",
            },
            "implementer": {
                "read_file",
                "list_directory",
                "write_file",
                "replace_in_file",
                "bash",
                "delegate_work",
            },
            "reviewer": {
                "read_file",
                "list_directory",
                "bash",  # Bounded strictly to read-only commands by CommandPolicy
            },
            "worker": {
                "read_file",
                "list_directory",
                "write_file",
                "replace_in_file",
                "bash",
                # NOTE: 'delegate_work' is explicitly excluded for workers (Decision 18)
            },
        }

    def get_allowed_tool_names(self, role: str) -> set[str]:
        """Returns the set of tool names allowed for the given role."""
        return self._role_permissions.get(role, set()).copy()

    def is_tool_allowed(self, role: str, tool_name: str) -> bool:
        """Checks if a role is allowed to call a specific tool."""
        return tool_name in self.get_allowed_tool_names(role)
