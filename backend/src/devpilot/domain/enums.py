from enum import StrEnum


class ReviewSeverity(StrEnum):
    """Normalized finding severity levels (Decision 12)."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ReviewCategory(StrEnum):
    """Specialized reviewer categories."""

    SECURITY = "security"
    REQUIREMENT = "requirement"
    CODE_QUALITY = "code_quality"
    EDGE_CASE = "edge_case"


class QAStatus(StrEnum):
    """Outcomes from the QA Node."""

    PASSED = "passed"
    FIX_REQUIRED = "fix_required"
    RETRY_LIMIT_REACHED = "retry_limit_reached"


class PlanDecision(StrEnum):
    """Human decision on the implementation plan (HITL)."""

    APPROVE = "approve"
    REVISE = "revise"
    REJECT = "reject"


class PublicationDecision(StrEnum):
    """Human decision on final PR publication (HITL)."""

    APPROVE = "approve"
    REVISE = "revise"
    REJECT = "reject"


PRDecision = PublicationDecision


class TaskStatus(StrEnum):
    """Overall workflow lifecycle status."""

    PENDING = "pending"
    PLANNING = "planning"
    AWAITING_PLAN_APPROVAL = "awaiting_plan_approval"
    IMPLEMENTING = "implementing"
    TESTING_AND_REVIEWING = "testing_and_reviewing"
    QA_EVALUATING = "qa_evaluating"
    AWAITING_PR_APPROVAL = "awaiting_publication_approval"
    PUBLISHED = "published"
    FAILED = "failed"
    REJECTED = "rejected"
