"""Merge node logic for the Review Subgraph (Section 5)."""

from devpilot.domain.enums import ReviewCategory, ReviewSeverity
from devpilot.domain.review import Finding, ReviewResult


def merge_findings(
    security_findings: list[Finding],
    requirement_findings: list[Finding],
    code_quality_findings: list[Finding],
    edge_case_findings: list[Finding],
) -> ReviewResult:
    """Merges, deduplicates, and evaluates findings from all 4 review specialists.

    Rules:
    1. Deduplicate identical findings across reviewers.
    2. Security findings are never dropped or superseded.
    3. Any security finding >= MEDIUM triggers 'fix_required'.
    4. Any finding of any category >= HIGH triggers 'fix_required'.
    5. Otherwise verdict is 'passed'.
    """
    all_raw_findings = [
        *security_findings,  # primary
        *requirement_findings,  # primary
        *code_quality_findings,  # secondary
        *edge_case_findings,  # secondary
    ]

    deduped_findings: list[Finding] = []
    seen: set[tuple[str, int | None, str]] = set()

    for finding in all_raw_findings:
        key = (
            finding.file_path,
            finding.line_number,
            finding.message.strip().lower(),
        )
        if key not in seen:
            seen.add(key)
            deduped_findings.append(finding)

    # Evaluate verdict
    fix_required = False
    for finding in deduped_findings:
        if finding.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH):
            fix_required = True
            break
        if (
            finding.category == ReviewCategory.SECURITY
            and finding.severity == ReviewSeverity.MEDIUM
        ):
            fix_required = True
            break

    verdict = "fix_required" if fix_required else "passed"
    summary = (
        f"Review completed with {len(deduped_findings)} finding(s). Verdict: {verdict}."
        if verdict == "fix_required"
        else f"Review passed with {len(deduped_findings)} finding(s)."
    )

    return ReviewResult(
        findings=deduped_findings,
        summary=summary,
        verdict=verdict,
    )
