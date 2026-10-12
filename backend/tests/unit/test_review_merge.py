"""Unit tests for Review merge logic and severity evaluation (Decision 12)."""

from devpilot.agents.reviewer.agent import Finding, merge_findings


def test_merge_findings_deduplication() -> None:
    """Verifies that identical findings from multiple reviewers are deduplicated."""
    finding_1 = Finding(
        category="security",
        severity="high",
        file_path="src/calc.py",
        line_number=10,
        message="Potential injection vulnerability",
        suggestion="Sanitize input",
    )
    # Duplicate finding reported with identical location and message
    finding_duplicate = Finding(
        category="security",
        severity="high",
        file_path="src/calc.py",
        line_number=10,
        message="Potential injection vulnerability",
        suggestion="Sanitize input",
    )
    finding_distinct = Finding(
        category="code_quality",
        severity="low",
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
    """Verifies that a medium security finding forces fix_required and survives merge."""
    sec_finding = Finding(
        category="security",
        severity="medium",
        file_path="src/auth.py",
        line_number=5,
        message="Token logging detected",
        suggestion="Redact token",
    )
    low_req_finding = Finding(
        category="requirement",
        severity="low",
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

    assert any(f.category == "security" for f in result.findings)
    assert result.verdict == "fix_required"


def test_merge_findings_all_passed() -> None:
    """Verifies that info/low non-security findings result in a 'passed' verdict."""
    info_finding = Finding(
        category="code_quality",
        severity="info",
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
