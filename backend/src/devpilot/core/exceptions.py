"""Custom exception definitions for DevPilot."""


class DevPilotError(Exception):
    """Base exception for all DevPilot errors."""


class SandboxError(DevPilotError):
    """Raised when an operation within the sandbox fails."""


class SandboxLostError(SandboxError):
    """Raised when the sandbox connection or instance is lost (e.g. timeout expired)."""


class BranchVerificationError(DevPilotError):
    """Raised when deterministic branch verification fails."""


class CommandPolicyViolationError(DevPilotError):
    """Raised when a command violates the sandbox security policy."""


class WorkerLimitExceededError(DevPilotError):
    """Raised when attempting to spawn more workers than allowed by the concurrency cap."""


class WorkerScopeConflictError(DevPilotError):
    """Raised when a worker's declared file scope conflicts with an active worker."""


class GitHubIntegrationError(DevPilotError):
    """Raised when GitHub App operations (token minting, issue reading, PR opening) fail."""
