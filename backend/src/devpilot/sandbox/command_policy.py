"""Command policy enforcement for sandbox command execution.

Implements:
- Decision 3: Reviewers are restricted strictly to read-only commands.
- Decision 19: Bounded worker shell execution.
- Security protection: Blocks dangerous or destructive shell operations.
"""

import shlex

from devpilot.core.exceptions import CommandPolicyViolationError

# Commands permitted for read-only reviewer operations (Decision 3)
REVIEWER_ALLOWED_ROOT_COMMANDS: set[str] = {
    "cat",
    "grep",
    "find",
    "ls",
    "head",
    "tail",
    "wc",
    "git",
    "diff",
}

# Subcommands allowed under 'git' for reviewers (read-only only)
REVIEWER_ALLOWED_GIT_SUBCOMMANDS: set[str] = {
    "status",
    "diff",
    "log",
    "show",
    "rev-parse",
    "branch",
}

# Patterns strictly forbidden for all agents (destructive or credential exfiltration)
DANGEROUS_PATTERNS: tuple[str, ...] = (
    "rm -rf /",
    "mkfs",
    ":(){ :|:& };:",
    "> /dev/sda",
    "dd if=",
)


def is_command_allowed_for_reviewer(command: str) -> bool:
    """Checks whether a command string is permissible for a read-only reviewer."""
    cmd = command.strip()
    if not cmd:
        return False

    # Block any shell redirection that modifies files
    if ">" in cmd or ">>" in cmd:
        return False

    try:
        parts = shlex.split(cmd)
    except ValueError:
        # Malformed command string
        return False

    if not parts:
        return False

    root_cmd = parts[0]
    if root_cmd not in REVIEWER_ALLOWED_ROOT_COMMANDS:
        return False

    # If calling git, only read-only subcommands are permitted
    if root_cmd == "git":
        # Find first non-flag argument which is the git subcommand
        git_subcmd = None
        for part in parts[1:]:
            if not part.startswith("-"):
                git_subcmd = part
                break
        if not git_subcmd or git_subcmd not in REVIEWER_ALLOWED_GIT_SUBCOMMANDS:
            return False

    return True


def validate_command_for_reviewer(command: str) -> None:
    """Validates that a reviewer command is read-only, raising if forbidden."""
    if not is_command_allowed_for_reviewer(command):
        raise CommandPolicyViolationError(
            f"Reviewers are restricted to read-only inspection. Disallowed command: {command}"
        )


class CommandPolicy:
    """Central policy engine for evaluating sandbox shell command execution."""

    def validate_command(self, command: str, role: str) -> None:
        """Validates a command against the security policy for a given agent role.

        Raises:
            CommandPolicyViolationError: If the command violates policy rules.
        """
        cmd = command.strip()

        # Check for universally blocked destructive patterns
        for pattern in DANGEROUS_PATTERNS:
            if pattern in cmd:
                raise CommandPolicyViolationError(
                    f"Command contains prohibited dangerous pattern '{pattern}': {cmd}"
                )

        # Block suspicious network exfiltration attempts
        if "curl " in cmd and "@" in cmd:
            raise CommandPolicyViolationError(
                f"File uploading via curl is prohibited in sandbox: {cmd}"
            )

        if role == "reviewer":
            validate_command_for_reviewer(cmd)
