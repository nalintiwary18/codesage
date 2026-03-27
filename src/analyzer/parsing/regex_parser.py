"""
Regex-based fallback parser for non-Python source files.

Detects function and class boundaries using language-specific patterns.
End lines are estimated from the position of the next symbol or EOF —
not as precise as AST but sufficient for chunking non-Python code.

Supported languages: JavaScript, TypeScript, Go, Rust, Java, Ruby, PHP.
"""

import re
from typing import Optional

from src.analyzer.parsing.ast_parser import ParsedBlock
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Per-language regex patterns for function signatures
FUNCTION_PATTERNS: dict[str, re.Pattern] = {
    "javascript": re.compile(
        r"^(?:export\s+)?(?:async\s+)?(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\()",
        re.MULTILINE,
    ),
    "typescript": re.compile(
        r"^(?:export\s+)?(?:async\s+)?(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*(?::\s*\w+)?\s*=\s*(?:async\s+)?\()",
        re.MULTILINE,
    ),
    "go": re.compile(
        r"^func\s+(?:\(\s*\w+\s+\*?\w+\s*\)\s+)?(\w+)\s*\(",
        re.MULTILINE,
    ),
    "rust": re.compile(
        r"^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)",
        re.MULTILINE,
    ),
    "java": re.compile(
        r"^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:\w+\s+)+(\w+)\s*\(",
        re.MULTILINE,
    ),
    "ruby": re.compile(r"^\s*def\s+(\w+)", re.MULTILINE),
    "php": re.compile(
        r"^\s*(?:public|private|protected)?\s*(?:static\s+)?function\s+(\w+)",
        re.MULTILINE,
    ),
}

# Per-language regex patterns for class/type declarations
CLASS_PATTERNS: dict[str, re.Pattern] = {
    "javascript": re.compile(r"^(?:export\s+)?class\s+(\w+)", re.MULTILINE),
    "typescript": re.compile(r"^(?:export\s+)?(?:abstract\s+)?class\s+(\w+)", re.MULTILINE),
    "go": re.compile(r"^type\s+(\w+)\s+struct\s*\{", re.MULTILINE),
    "rust": re.compile(r"^(?:pub\s+)?(?:struct|enum|impl)\s+(\w+)", re.MULTILINE),
    "java": re.compile(r"^(?:public\s+)?(?:abstract\s+)?class\s+(\w+)", re.MULTILINE),
    "ruby": re.compile(r"^class\s+(\w+)", re.MULTILINE),
    "php": re.compile(r"^(?:abstract\s+)?class\s+(\w+)", re.MULTILINE),
}


def parse_with_regex(
    source_code: str,
    language: str,
    file_path: str = "<unknown>",
) -> list[ParsedBlock]:
    """
    Extract function and class blocks from source code using regex matching.

    End lines are estimated — each block is assumed to run until the line
    before the next block starts, or until EOF for the last block.
    Returns an empty list if no patterns are configured for the language.
    """
    lines = source_code.splitlines()
    total_lines = len(lines)

    if total_lines == 0:
        return []

    lang = language.lower()
    blocks: list[ParsedBlock] = []

    # Collect function matches
    func_pattern = FUNCTION_PATTERNS.get(lang)
    if func_pattern:
        for match in func_pattern.finditer(source_code):
            name = next((g for g in match.groups() if g), None)
            if name:
                line_num = source_code[: match.start()].count("\n") + 1
                blocks.append(ParsedBlock(
                    block_type="function",
                    name=name,
                    start_line=line_num,
                    end_line=line_num,  # Estimated below
                ))

    # Collect class/type matches
    class_pattern = CLASS_PATTERNS.get(lang)
    if class_pattern:
        for match in class_pattern.finditer(source_code):
            name = next((g for g in match.groups() if g), None)
            if name:
                line_num = source_code[: match.start()].count("\n") + 1
                blocks.append(ParsedBlock(
                    block_type="class",
                    name=name,
                    start_line=line_num,
                    end_line=line_num,  # Estimated below
                ))

    blocks.sort(key=lambda b: b.start_line)
    _estimate_end_lines(blocks, total_lines, lines)

    logger.debug(f"{len(blocks)} blocks extracted from {file_path} via regex")
    return blocks


def _estimate_end_lines(
    blocks: list[ParsedBlock],
    total_lines: int,
    lines: list[str],
) -> None:
    """
    Assign end_line to each block by looking at where the next block starts.
    Trailing empty lines are not counted — the end line is the last non-empty
    line within the estimated range.
    """
    for i, block in enumerate(blocks):
        estimated_end = blocks[i + 1].start_line - 1 if i + 1 < len(blocks) else total_lines

        # Walk back over trailing blank lines for a cleaner boundary
        while estimated_end > block.start_line and not lines[estimated_end - 1].strip():
            estimated_end -= 1

        block.end_line = max(estimated_end, block.start_line)
