"""
General-purpose helper utilities.
These functions have no dependencies on other project modules and are
safe to import from anywhere in the codebase.
"""

from pathlib import Path
from typing import Optional


def read_file_lines(file_path: str | Path) -> Optional[list[str]]:
    """
    Read a file and return its lines as a list.
    Returns None if the file cannot be read due to an IO or encoding error.
    Does not raise — callers should handle the None case explicitly.
    """
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        return content.splitlines()
    except (OSError, UnicodeDecodeError):
        return None


def count_lines(file_path: str | Path) -> int:
    """
    Return the number of lines in a file, or 0 if unreadable.
    """
    lines = read_file_lines(file_path)
    return len(lines) if lines else 0


def truncate_string(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    Truncate a string to max_length characters, appending suffix if cut.
    Returns the original string unchanged if it is already within the limit.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def safe_path(path: str | Path) -> Path:
    """Resolve a path to an absolute, canonical Path object."""
    return Path(path).resolve()


def is_binary_file(file_path: str | Path) -> bool:
    """
    Detect whether a file is binary by scanning the first 8 KB for null bytes.
    Returns True (treat as binary) if the file cannot be opened.
    """
    try:
        chunk = Path(file_path).read_bytes()[:8192]
        return b"\x00" in chunk
    except OSError:
        return True


def format_file_size(size_bytes: int) -> str:
    """Format a byte count as a human-readable string: "1.0 KB", "2.4 MB", etc."""
    units = ["B", "KB", "MB", "GB"]
    size = float(size_bytes)
    for unit in units[:-1]:
        if abs(size) < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} {units[-1]}"


def normalize_path_separator(path: str) -> str:
    """
    Replace backslashes with forward slashes for cross-platform consistency.
    Useful when comparing or storing paths on Windows vs Unix.
    """
    return path.replace("\\", "/")
