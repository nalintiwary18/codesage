"""
Issue scorer — post-processes raw LLM-detected issues to enforce
severity floors and confidence calibration rules.

Security issues that the LLM marked as low/info are raised to at least HIGH.
Issues with vague descriptions or missing fixes have their confidence reduced.
Confidence is always clamped to [0.0, 1.0] after adjustment.
"""

from src.issues.schema import Issue, IssueSeverity, IssueCategory


def assign_severity(issue: Issue) -> IssueSeverity:
    """
    Override or validate the LLM-assigned severity using domain rules.

    Rules applied:
    - Security issues must be at least HIGH
    - Bug issues must be at least MEDIUM
    - All other severities are left unchanged
    """
    if issue.category == IssueCategory.SECURITY:
        if issue.severity in (IssueSeverity.LOW, IssueSeverity.INFO):
            return IssueSeverity.HIGH

    if issue.category == IssueCategory.BUG:
        if issue.severity == IssueSeverity.INFO:
            return IssueSeverity.MEDIUM

    return issue.severity


def adjust_confidence(issue: Issue) -> float:
    """
    Calibrate the confidence score based on the quality of the issue output.

    Penalties:
    - Title shorter than 10 chars: likely too generic → ×0.7
    - Description shorter than 30 chars: insufficient context → ×0.8

    Bonuses:
    - Suggested fix with substance (>20 chars): actionable → ×1.1
    - Non-trivial code snippet (>10 chars): grounded in code → ×1.1

    Final value is clamped to [0.0, 1.0].
    """
    confidence = issue.confidence

    if len(issue.title) < 10:
        confidence *= 0.7

    if len(issue.description) < 30:
        confidence *= 0.8

    if issue.suggested_fix and len(issue.suggested_fix) > 20:
        confidence *= 1.1

    if issue.snippet and len(issue.snippet) > 10:
        confidence *= 1.1

    return max(0.0, min(1.0, round(confidence, 2)))


def score_issue(issue: Issue) -> Issue:
    """Apply severity validation and confidence calibration to one issue."""
    issue.severity = assign_severity(issue)
    issue.confidence = adjust_confidence(issue)
    return issue


def score_all_issues(issues: list[Issue]) -> list[Issue]:
    """Apply score_issue to a batch of issues in place and return the list."""
    return [score_issue(issue) for issue in issues]
