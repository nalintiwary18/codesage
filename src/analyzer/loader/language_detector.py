"""
Language detection by file extension.
Maps file extensions to canonical language tags used throughout the pipeline.
Tags must match the keys expected by the parser selection logic in chunker.py.
"""

from pathlib import Path
from typing import Optional

from src.config.defaults import SUPPORTED_EXTENSIONS


def detect_language(file_path: str) -> Optional[str]:
    """
    Return the language tag for the file's extension, or None if unsupported.
    Detection is purely extension-based — no content sniffing.
    """
    extension = Path(file_path).suffix.lower()
    return SUPPORTED_EXTENSIONS.get(extension)


def is_supported_language(file_path: str) -> bool:
    """Return True if the file's extension maps to a known language."""
    return detect_language(file_path) is not None


def get_language_for_extension(extension: str) -> Optional[str]:
    """
    Look up a language tag directly from an extension string.
    The leading dot is optional — both ".py" and "py" are accepted.
    """
    if not extension.startswith("."):
        extension = f".{extension}"
    return SUPPORTED_EXTENSIONS.get(extension.lower())


def get_all_supported_extensions() -> list[str]:
    """Return the complete list of recognized file extensions."""
    return list(SUPPORTED_EXTENSIONS.keys())
