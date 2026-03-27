"""
Scoring utilities for aggregating, sorting, and filtering issues.
These helpers operate on lists of Issue objects and have no LLM dependencies.
"""

from src.issues.schema import Issue, IssueSeverity

# Numeric rank for each severity — used for consistent ordering
SEVERITY_ORDER: dict[IssueSeverity, int] = {
    IssueSeverity.CRITICAL: 5,
    IssueSeverity.HIGH: 4,
    IssueSeverity.MEDIUM: 3,
    IssueSeverity.LOW: 2,
    IssueSeverity.INFO: 1,
}


def severity_to_number(severity: IssueSeverity) -> int:
    """Return the numeric rank for a severity level (higher = more severe)."""
    return SEVERITY_ORDER.get(severity, 0)


def sort_by_severity(issues: list[Issue]) -> list[Issue]:
    """
    Sort issues so that CRITICAL appears first and INFO last.
    Within the same severity, higher confidence comes first.
    """
    return sorted(
        issues,
        key=lambda i: (severity_to_number(i.severity), i.confidence),
        reverse=True,
    )


def filter_by_confidence(
    issues: list[Issue],
    min_confidence: float = 0.5,
) -> list[Issue]:
    """Drop issues whose confidence is below min_confidence."""
    return [i for i in issues if i.confidence >= min_confidence]


def filter_by_severity(
    issues: list[Issue],
    min_severity: IssueSeverity = IssueSeverity.LOW,
) -> list[Issue]:
    """Drop issues whose severity is below the specified minimum."""
    min_level = severity_to_number(min_severity)
    return [i for i in issues if severity_to_number(i.severity) >= min_level]


def group_by_file(issues: list[Issue]) -> dict[str, list[Issue]]:
    """
    Group issues by their resolved file path.
    Unresolved issues (no file_path) are keyed by "chunk:<id_prefix>".
    Useful for generating per-file sections in the report.
    """
    groups: dict[str, list[Issue]] = {}
    for issue in issues:
        file_key = issue.file_path or f"chunk:{issue.chunk_id[:12]}"
        groups.setdefault(file_key, []).append(issue)
    return groups


def group_by_severity(issues: list[Issue]) -> dict[str, list[Issue]]:
    """Group issues by their severity string value."""
    groups: dict[str, list[Issue]] = {}
    for issue in issues:
        groups.setdefault(issue.severity.value, []).append(issue)
    return groups


def get_summary_stats(issues: list[Issue]) -> dict[str, int]:
    """
    Return a flat count dictionary for use in report headers.
    Keys: total, critical, high, medium, low, info, validated.
    """
    stats: dict[str, int] = {
        "total": len(issues),
        "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0,
        "validated": 0,
    }
    for issue in issues:
        stats[issue.severity.value] = stats.get(issue.severity.value, 0) + 1
        if issue.is_validated:
            stats["validated"] += 1
    return stats
