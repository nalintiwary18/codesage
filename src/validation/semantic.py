"""
Semantic validation — checks whether issue content is specific and actionable.

Complements structural validation by detecting vague, generic, or copy-paste
output from the LLM. Issues that fail semantic checks have their confidence
reduced rather than being outright rejected; the final quality filter applies
the hard cutoff.

Includes fuzzy snippet matching for minor whitespace differences.
"""

from difflib import SequenceMatcher

from src.issues.schema import Issue

# Phrases that indicate a generic, non-actionable issue description
GENERIC_PHRASES: list[str] = [
    "could be improved",
    "should be better",
    "consider using",
    "this is not ideal",
    "may cause issues",
    "potential problem",
    "generally speaking",
    "in most cases",
    "it depends",
]


def fuzzy_match_snippet(
    expected_snippet: str,
    actual_snippet: str,
    threshold: float = 0.7,
) -> tuple[bool, float]:
    """
    Compare two code snippets with whitespace normalization.
    Returns (matched, similarity_score).
    A score above threshold is considered a match.
    """
    if not expected_snippet or not actual_snippet:
        return False, 0.0

    a = _normalize_whitespace(expected_snippet)
    b = _normalize_whitespace(actual_snippet)
    similarity = SequenceMatcher(None, a, b).ratio()

    return similarity >= threshold, round(similarity, 3)


def check_issue_specificity(issue: Issue) -> tuple[bool, list[str]]:
    """
    Apply heuristics to determine whether an issue is specific and actionable.

    Checks:
    - Title length >= 10 chars
    - Description length >= 30 chars
    - No generic filler phrases in description
    - Suggested fix present and non-trivial
    - Title and description not nearly identical

    Returns (is_specific, list_of_notes).
    Failing checks reduce confidence but do not block the issue by themselves.
    """
    notes: list[str] = []
    is_specific = True

    if len(issue.title.strip()) < 10:
        notes.append("WARN: title too short — likely too generic")
        is_specific = False

    desc = issue.description.strip()
    if len(desc) < 30:
        notes.append("WARN: description too short — insufficient detail")
        is_specific = False

    desc_lower = desc.lower()
    for phrase in GENERIC_PHRASES:
        if phrase in desc_lower:
            notes.append(f"WARN: generic phrase detected: '{phrase}'")
            is_specific = False
            break

    if not issue.suggested_fix or len(issue.suggested_fix.strip()) < 10:
        notes.append("WARN: suggested_fix missing or too short")
        # Non-blocking — noted but does not fail the check

    if _are_too_similar(issue.title, issue.description):
        notes.append("WARN: title and description are nearly identical — low-effort output")
        is_specific = False

    if is_specific:
        notes.append("PASS: issue content appears specific and actionable")

    return is_specific, notes


def validate_semantic(issue: Issue) -> Issue:
    """
    Apply semantic specificity check to one issue.
    Confidence is reduced by 30% if the issue fails the specificity check.
    """
    is_specific, notes = check_issue_specificity(issue)

    if not is_specific:
        issue.confidence = max(0.0, min(1.0, round(issue.confidence * 0.7, 2)))

    issue.validation_notes.extend(notes)
    return issue


def validate_all_semantic(issues: list[Issue]) -> list[Issue]:
    """Apply semantic validation to all issues in place and return the list."""
    for issue in issues:
        validate_semantic(issue)
    return issues


def _normalize_whitespace(text: str) -> str:
    """Collapse all whitespace runs into single spaces."""
    return " ".join(text.split())


def _are_too_similar(text1: str, text2: str, threshold: float = 0.85) -> bool:
    """Return True if the two strings are more similar than the given threshold."""
    if not text1 or not text2:
        return False
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio() >= threshold
