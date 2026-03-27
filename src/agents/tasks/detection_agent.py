"""
Detection agent — the core analysis step that finds issues in source code.

Contract enforced by the system prompt:
  - chunk_id must be copied verbatim from the provided chunk header
  - relative_start_line / relative_end_line are 1-indexed positions WITHIN the chunk
  - Absolute file line numbers must never appear in the output
  - LLM must count lines from the numbered display, not guess from context

On response parse failure, returns an empty list — upstream retries or
continues with 0 issues rather than crashing the pipeline.
"""

import json
from typing import Any, Optional

from src.agents.llm.client import LLMProvider
from src.core.chunk import CodeChunk
from src.issues.schema import Issue, IssueSeverity, IssueCategory
from src.utils.logger import get_logger

logger = get_logger(__name__)

DETECTION_SYSTEM_PROMPT = """You are a senior code reviewer performing a thorough code analysis.
Your task is to detect real issues in the provided code chunks.

For EACH issue found, return a JSON object with:
1. "chunk_id": The exact chunk_id provided (COPY IT EXACTLY)
2. "relative_start_line": Line number WITHIN the chunk (1-indexed, first line of chunk = 1)
3. "relative_end_line": Line number WITHIN the chunk where issue ends
4. "title": Short, specific issue title
5. "description": Detailed explanation of why this is a problem
6. "severity": One of "critical", "high", "medium", "low", "info"
7. "category": One of "security", "performance", "bug", "code_smell", "best_practice", "architecture", "error_handling", "maintainability", "other"
8. "suggested_fix": Specific fix suggestion with code if possible
9. "snippet": The exact problematic code lines from the chunk
10. "confidence": Float 0.0 to 1.0 indicating how confident you are

CRITICAL RULES:
- relative_start_line and relative_end_line are WITHIN the chunk (1 = first line of chunk)
- Do NOT use absolute file line numbers
- Do NOT guess line numbers — count carefully from the numbered display
- Only report REAL issues, not style preferences
- Be specific — generic issues will be filtered out
- Reference actual code, not hypothetical problems

Return a JSON array of issue objects. If no issues found, return [].
Do NOT wrap in markdown code blocks."""


def build_detection_prompt(
    chunks: list[CodeChunk],
    understanding: Optional[dict[str, Any]] = None,
) -> str:
    """
    Format chunks into a detection prompt.
    Each chunk is displayed with explicit chunk_id and 1-indexed line numbers
    so the LLM can produce accurate relative references.
    """
    parts = []

    if understanding:
        parts.append("=== CODEBASE CONTEXT ===")
        parts.append(f"Architecture: {understanding.get('architecture', 'Unknown')}")
        patterns = understanding.get("patterns", [])
        if patterns:
            parts.append(f"Patterns: {', '.join(patterns)}")
        parts.append("")

    parts.append("=== CODE CHUNKS TO ANALYZE ===\n")

    for i, chunk in enumerate(chunks, 1):
        parts.append(f"--- CHUNK {i} ---")
        parts.append(f"chunk_id: {chunk.id}")
        parts.append(f"File: {chunk.file_path}")
        parts.append(f"Original lines: {chunk.start_line}-{chunk.end_line}")
        parts.append(f"Type: {chunk.chunk_type or 'unknown'}")
        parts.append(f"Total lines in chunk: {chunk.line_count}\n")

        # Display lines with 1-indexed relative numbers for accurate reference
        for line_num, line in enumerate(chunk.content.splitlines(), 1):
            parts.append(f"  {line_num:4d} | {line}")

        parts.append("")

    parts.append("---")
    parts.append("\nAnalyze ALL chunks above. Return issues as a JSON array.")
    return "\n".join(parts)


def run_detection_agent(
    llm: LLMProvider,
    chunks: list[CodeChunk],
    understanding: Optional[dict[str, Any]] = None,
) -> list[Issue]:
    """
    Send chunks to the LLM for issue detection and parse the JSON response.
    Returns a list of raw Issue objects (not yet structurally validated).
    """
    if not chunks:
        return []

    prompt = build_detection_prompt(chunks, understanding)
    logger.info(f"Detecting issues in {len(chunks)} chunks...")
    raw = llm.generate(prompt, system_prompt=DETECTION_SYSTEM_PROMPT)

    issues = _parse_detection_response(raw, chunks)
    logger.info(f"Detected {len(issues)} raw issues")
    return issues


def _parse_detection_response(raw: str, chunks: list[CodeChunk]) -> list[Issue]:
    """
    Parse LLM output into Issue objects.
    Invalid chunk_ids are rejected (hallucination guard).
    Malformed individual entries are skipped without failing the whole batch.
    """
    valid_ids = {chunk.id for chunk in chunks}
    cleaned = _strip_markdown_fences(raw.strip())

    try:
        raw_issues = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Detection response could not be parsed as JSON — returning 0 issues")
        return []

    if not isinstance(raw_issues, list):
        return []

    issues: list[Issue] = []
    for entry in raw_issues:
        try:
            issue = _to_issue(entry, valid_ids)
            if issue:
                issues.append(issue)
        except Exception as e:
            logger.debug(f"Skipping malformed issue entry: {e}")

    return issues


def _to_issue(raw: dict, valid_ids: set[str]) -> Optional[Issue]:
    """
    Convert a raw dict from the LLM response to an Issue object.
    Returns None if the chunk_id is not in the valid set (hallucination guard).
    """
    chunk_id = raw.get("chunk_id", "")

    if chunk_id not in valid_ids:
        logger.debug(f"Hallucinated chunk_id rejected: {chunk_id[:12]}...")
        return None

    try:
        severity = IssueSeverity(raw.get("severity", "medium").lower())
    except ValueError:
        severity = IssueSeverity.MEDIUM

    try:
        category = IssueCategory(raw.get("category", "other").lower())
    except ValueError:
        category = IssueCategory.OTHER

    return Issue(
        chunk_id=chunk_id,
        relative_start_line=int(raw.get("relative_start_line", 1)),
        relative_end_line=int(raw.get("relative_end_line", 1)),
        title=str(raw.get("title", "Unnamed Issue")),
        description=str(raw.get("description", "")),
        severity=severity,
        category=category,
        suggested_fix=raw.get("suggested_fix"),
        snippet=raw.get("snippet"),
        confidence=float(raw.get("confidence", 0.7)),
    )


def _strip_markdown_fences(text: str) -> str:
    """Remove triple-backtick fences from an LLM response."""
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
