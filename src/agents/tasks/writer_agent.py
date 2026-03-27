"""
Writer agent — final polish pass before validation.

Improves issue text for clarity, specificity, and professionalism.
Only text fields (title, description, suggested_fix) are updated —
chunk_id, line references, severity, and category are never touched.
This preserves the referential integrity established by the detection agent.

Falls back to returning the original issues if the response cannot be applied.
"""

import json
from typing import Optional

from src.agents.llm.client import LLMProvider
from src.issues.schema import Issue
from src.utils.logger import get_logger

logger = get_logger(__name__)

WRITER_SYSTEM_PROMPT = """You are a technical writer polishing code review findings.
Your task is to improve the clarity and actionability of each issue.

For each issue:
1. Improve the description to be clear, specific, and professional
2. Enhance the suggested fix to be actionable with concrete steps
3. Keep the original meaning and technical accuracy intact

Return a JSON array where each item has:
- "title": Improved title (keep it concise)
- "description": Polished description
- "suggested_fix": Enhanced fix suggestion

Return ONLY valid JSON array, no markdown formatting."""


def run_writer_agent(llm: LLMProvider, issues: list[Issue]) -> list[Issue]:
    """
    Send issues to the LLM for final text polish.
    Updates title, description, and suggested_fix in place.
    Returns the original issues unchanged on any parse failure.
    """
    if not issues:
        return []

    prompt = _build_writer_prompt(issues)
    logger.info(f"Polishing {len(issues)} issues...")
    raw = llm.generate(prompt, system_prompt=WRITER_SYSTEM_PROMPT)

    return _apply_polish(raw, issues)


def _build_writer_prompt(issues: list[Issue]) -> str:
    parts = ["Here are the reviewed issues to polish:\n"]
    for i, issue in enumerate(issues, 1):
        parts.append(f"--- ISSUE {i} ---")
        parts.append(f"Title: {issue.title}")
        parts.append(f"Severity: {issue.severity.value}")
        parts.append(f"Category: {issue.category.value}")
        parts.append(f"Description: {issue.description}")
        if issue.suggested_fix:
            parts.append(f"Current Fix: {issue.suggested_fix}")
        if issue.snippet:
            parts.append(f"Code:\n{issue.snippet[:300]}")
        parts.append("")
    parts.append("---\nPolish all issues above. Return improved JSON array.")
    return "\n".join(parts)


def _apply_polish(raw: str, issues: list[Issue]) -> list[Issue]:
    """
    Apply polished text to issues by index.
    Only updates text fields — chunk references and metadata are unchanged.
    Returns the original list if the response is empty or malformed.
    """
    cleaned = _strip_markdown_fences(raw.strip())

    try:
        polished = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Writer response unparseable — returning original issues")
        return issues

    if not isinstance(polished, list):
        return issues

    for i, issue in enumerate(issues):
        if i >= len(polished):
            break
        item = polished[i]
        if not isinstance(item, dict):
            continue

        # Only overwrite when the LLM actually returned something non-empty
        if item.get("title"):
            issue.title = str(item["title"])
        if item.get("description"):
            issue.description = str(item["description"])
        if item.get("suggested_fix"):
            issue.suggested_fix = str(item["suggested_fix"])

    return issues


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
