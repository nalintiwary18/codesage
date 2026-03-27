"""
Quality scoring for validated issues.

Computes a composite 0.0–1.0 score based on structural resolution,
description length, snippet availability, and fix quality. Issues that
fall below the minimum quality threshold are excluded from the report.
"""

from src.issues.schema import Issue
from src.utils.logger import get_logger

logger = get_logger(__name__)


def calculate_quality_score(issue: Issue) -> float:
    """
    Compute a quality score in [0.0, 1.0] for one issue.

    Scoring breakdown (total weights sum to 1.0):
    - Structural validation passed   : 0.40
    - File path resolved             : 0.15
    - Code snippet available         : 0.15
    - Description length             : 0.15
    - Suggested fix quality          : 0.15
    """
    score = 0.0

    # Structural validation weight
    score += 0.40 if issue.is_validated else 0.05

    # Resolved file path
    if issue.is_resolved:
        score += 0.15

    # Snippet quality
    if issue.snippet and len(issue.snippet.strip()) > 5:
        score += 0.15

    # Description length bands
    desc_len = len(issue.description.strip())
    if desc_len >= 100:
        score += 0.15
    elif desc_len >= 50:
        score += 0.10
    elif desc_len >= 20:
        score += 0.05

    # Suggested fix length bands
    if issue.suggested_fix:
        fix_len = len(issue.suggested_fix.strip())
        if fix_len >= 50:
            score += 0.15
        elif fix_len >= 20:
            score += 0.10
        elif fix_len >= 5:
            score += 0.05

    return round(score, 2)


def apply_quality_scores(issues: list[Issue]) -> list[Issue]:
    """
    Compute and set validation_score on every issue in the list.
    Issues that fall below the minimum threshold are noted in validation_notes
    but not removed here — use filter_by_quality for that.
    """
    min_quality = 0.3

    for issue in issues:
        issue.validation_score = calculate_quality_score(issue)

        if issue.validation_score < min_quality:
            issue.validation_notes.append(
                f"WARN: quality score {issue.validation_score} below threshold {min_quality}"
            )

    return issues


def filter_by_quality(
    issues: list[Issue],
    min_quality: float = 0.3,
) -> list[Issue]:
    """
    Drop issues whose quality score is below min_quality.
    Logs a count of how many were removed for debuggability.
    """
    kept = [i for i in issues if i.validation_score >= min_quality]
    removed = len(issues) - len(kept)

    if removed:
        logger.info(f"Quality filter removed {removed} issues (threshold: {min_quality})")

    return kept
