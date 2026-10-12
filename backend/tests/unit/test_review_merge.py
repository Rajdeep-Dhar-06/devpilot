from devpilot.domain.enums import ReviewCategory, ReviewSeverity
from devpilot.domain.review import Finding
from devpilot.workflows.review.merge import merge_findings


def test_merge_findings_deduplication() -> None:
    finding_1 = Finding(
        category=ReviewCategory.SECURITY,
        severity=ReviewSeverity.HIGH,
        file_path="src/calc.py",
        line_number=10,
        message="Potential injection vulnerability",
        suggestion="Sanitize input",
    )
    # Duplicate finding reported with identical location and message
    finding_duplicate = Finding(
        category=ReviewCategory.SECURITY,
        severity=ReviewSeverity.HIGH,
        file_path="src/calc.py",
        line_number=10,
        message="Potential injection vulnerability",
        suggestion="Sanitize input",
    )
    finding_distinct = Finding(
        category=ReviewCategory.CODE_QUALITY,
        severity=ReviewSeverity.LOW,
        file_path="src/calc.py",
        line_number=25,
        message="Variable name too short",
        suggestion="Rename x to total",
    )

    result = merge_findings(
        security_findings=[finding_1, finding_duplicate],
        requirement_findings=[],
        code_quality_findings=[finding_distinct],
        edge_case_findings=[],
    )

    # Duplicate should be filtered out
    assert len(result.findings) == 2
    assert result.verdict == "fix_required"  # Due to HIGH severity finding


def test_merge_findings_security_never_dropped() -> None:
    # A medium security finding must cause fix_required verdict (Decision 12)
    sec_finding = Finding(
        category=ReviewCategory.SECURITY,
        severity=ReviewSeverity.MEDIUM,
        file_path="src/auth.py",
        line_number=5,
        message="Token logging detected",
        suggestion="Redact token",
    )
    low_req_finding = Finding(
        category=ReviewCategory.REQUIREMENT,
        severity=ReviewSeverity.LOW,
        file_path="src/calc.py",
        line_number=1,
        message="Minor docstring typo",
        suggestion="Fix typo",
    )

    result = merge_findings(
        security_findings=[sec_finding],
        requirement_findings=[low_req_finding],
        code_quality_findings=[],
        edge_case_findings=[],
    )

    assert any(f.category == ReviewCategory.SECURITY for f in result.findings)
    assert result.verdict == "fix_required"


def test_merge_findings_all_passed() -> None:
    info_finding = Finding(
        category=ReviewCategory.CODE_QUALITY,
        severity=ReviewSeverity.INFO,
        file_path="src/calc.py",
        line_number=1,
        message="Code is clean and formatted",
        suggestion="Keep up the good work",
    )

    result = merge_findings(
        security_findings=[],
        requirement_findings=[],
        code_quality_findings=[info_finding],
        edge_case_findings=[],
    )

    assert result.verdict == "passed"
    assert len(result.findings) == 1
