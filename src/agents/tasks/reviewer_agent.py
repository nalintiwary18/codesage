"""
Reviewer agent — LLM-powered quality filter run after initial detection.

Each issue is evaluated for:
  - False positive likelihood
  - Description specificity
  - Appropriate severity assignment
  - Actionability of the fix

The LLM returns keep=true/false and an adjusted confidence per issue.
On parse failure, the original list is returned unchanged (fail-open).
"""

import json
from typing import Optional

from src.agents.llm.client import LLMProvider
from src.issues.schema import Issue
from src.utils.logger import get_logger

logger = get_logger(__name__)

REVIEWER_SYSTEM_PROMPT = """You are a senior code reviewer evaluating detected issues.
Your job is to filter and improve the quality of issues.

For each issue, evaluate:
1. Is it a REAL issue or a false positive?
2. Is the description specific enough?
3. Is the severity appropriate?
4. Is the suggested fix actionable?

Return a JSON array with the SAME issues, but:
- Remove duplicates (same file, same problem)
- Remove false positives
- Adjust confidence (0.0-1.0) based on your evaluation
- Set "keep" to true/false for each issue

Each item should have: "title", "keep" (boolean), "adjusted_confidence" (float)
Return ONLY valid JSON array."""


def run_reviewer_agent(llm: LLMProvider, issues: list[Issue]) -> list[Issue]:
    """
    Send detected issues to the LLM for quality review.
    Returns the subset of issues the LLM marks as worth keeping,
    with confidence scores adjusted to reflect the reviewer's assessment.
    Falls back to returning all issues if the response cannot be parsed.
    """
    if not issues:
        return []

    prompt = _build_review_prompt(issues)
    logger.info(f"Reviewing {len(issues)} issues...")
    raw = llm.generate(prompt, system_prompt=REVIEWER_SYSTEM_PROMPT)

    filtered = _apply_review(raw, issues)
    logger.info(f"Review kept {len(filtered)}/{len(issues)} issues")
    return filtered


def _build_review_prompt(issues: list[Issue]) -> str:
    parts = ["Here are the detected issues to review:\n"]
    for i, issue in enumerate(issues, 1):
        parts.append(f"--- ISSUE {i} ---")
        parts.append(f"Title: {issue.title}")
        parts.append(f"Severity: {issue.severity.value}")
        parts.append(f"Category: {issue.category.value}")
        parts.append(f"Confidence: {issue.confidence}")
        parts.append(f"Description: {issue.description}")
        if issue.suggested_fix:
            parts.append(f"Fix: {issue.suggested_fix}")
        if issue.snippet:
            parts.append(f"Code: {issue.snippet[:200]}")
        parts.append("")
    parts.append("---\nReview all issues above. Return JSON array with evaluation.")
    return "\n".join(parts)


def _apply_review(raw: str, issues: list[Issue]) -> list[Issue]:
    """
    Parse the review response and apply keep/confidence updates.
    Matching is done by title (lowercased). Falls back to returning all issues
    if the response is empty, malformed, or unparseable.
    """
    cleaned = _strip_markdown_fences(raw.strip())

    try:
        results = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Reviewer response unparseable — keeping all issues")
        return issues

    if not isinstance(results, list):
        return issues

    # Build title → adjusted_confidence map for issues the reviewer wants to keep
    keep_map: dict[str, float] = {
        r.get("title", "").lower().strip(): float(r.get("adjusted_confidence", 0.7))
        for r in results
        if isinstance(r, dict) and r.get("keep", True)
    }

    if not keep_map:
        return issues  # Fail-open — keep all if nothing was parseable

    filtered: list[Issue] = []
    for issue in issues:
        key = issue.title.lower().strip()
        if key in keep_map:
            issue.confidence = keep_map[key]
            filtered.append(issue)

    return filtered if filtered else issues


def _strip_markdown_fences(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.split("\n")
    body: list[str] = []
    inside = False
    for line in lines:
        if line.strip().startswith("```") and not inside:
            inside = True
            continue
        if line.strip() == "```" and inside:
            break
        if inside:
            body.append(line)
    return "\n".join(body)
