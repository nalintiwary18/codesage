"""
Issue block formatters for the Markdown report.

Each function converts an Issue object into a Markdown fragment.
format_issue_block() produces the full detailed block; 
format_issue_summary_row() produces a single table row for the overview table.
"""

from src.issues.schema import Issue, IssueSeverity

# Severity → inline Markdown badge (rendered in bold)
SEVERITY_BADGES: dict[IssueSeverity, str] = {
    IssueSeverity.CRITICAL: "🔴 **CRITICAL**",
    IssueSeverity.HIGH: "🟠 **HIGH**",
    IssueSeverity.MEDIUM: "🟡 **MEDIUM**",
    IssueSeverity.LOW: "🔵 **LOW**",
    IssueSeverity.INFO: "⚪ **INFO**",
}


def format_issue_block(issue: Issue, index: int = 1) -> str:
    """
    Render one issue as a full Markdown section including severity, location,
    description, code snippet, and suggested fix.
    Terminated with a horizontal rule for visual separation.
    """
    lines: list[str] = []

    badge = SEVERITY_BADGES.get(issue.severity, "⚪ **INFO**")
    lines.append(f"### {index}. {issue.title}\n")
    lines.append(f"**Severity:** {badge}  ")
    lines.append(f"**Category:** `{issue.category.value}`  ")
    lines.append(f"**Confidence:** `{issue.confidence:.0%}`  ")

    # Location — prefer resolved file:lines; fall back to chunk reference
    if issue.is_resolved:
        lines.append(
            f"**Location:** `{issue.file_path}` "
            f"(Lines {issue.absolute_start_line}–{issue.absolute_end_line})  "
        )
    else:
        lines.append(
            f"**Location:** Chunk `{issue.chunk_id[:12]}...` "
            f"(Relative lines {issue.relative_start_line}–{issue.relative_end_line})  "
        )

    lines.append("\n**Description:**\n")
    lines.append(issue.description)
    lines.append("")

    if issue.snippet:
        lang_hint = _guess_language(issue.file_path)
        lines.append("**Code:**\n")
        lines.append(f"```{lang_hint}")
        lines.append(issue.snippet)
        lines.append("```\n")

    if issue.suggested_fix:
        lines.append("**Suggested Fix:**\n")
        lines.append(issue.suggested_fix)
        lines.append("")

    lines.append("---\n")
    return "\n".join(lines)


def format_issue_summary_row(issue: Issue, index: int = 1) -> str:
    """
    Render one issue as a Markdown table row for the overview summary table.
    Columns: index, severity badge, title (truncated), location, confidence.
    """
    location = (
        f"`{issue.file_path}:{issue.absolute_start_line}`"
        if issue.is_resolved
        else "unresolved"
    )
    badge = SEVERITY_BADGES.get(issue.severity, "⚪")
    return f"| {index} | {badge} | {issue.title[:60]} | {location} | `{issue.confidence:.0%}` |"


def _guess_language(file_path: str | None) -> str:
    """
    Return a fenced-code-block language hint based on the file extension.
    Returns an empty string (no hint) if the extension is unknown.
    """
    if not file_path:
        return ""

    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".go": "go", ".rs": "rust", ".java": "java",
        ".rb": "ruby", ".php": "php", ".c": "c", ".cpp": "cpp",
    }
    for ext, lang in ext_map.items():
        if file_path.endswith(ext):
            return lang
    return ""
