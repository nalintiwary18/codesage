"""
CodeChunk — immutable, deterministic schema for a single code segment.
All line references across the system trace back to this structure.

A chunk captures a contiguous range of source lines from a file, along with
enough metadata to uniquely identify it, cache analysis results, and convert
between relative (within-chunk) and absolute (file-level) line positions.

Constraints enforced at construction time:
- start_line must be >= 1
- end_line must be >= start_line
- content must be non-empty
"""
from dataclasses import dataclass, field
import hashlib
from typing import Optional


@dataclass(frozen=True)
class CodeChunk:
    """
    Represents a contiguous block of source code from a file.
    Frozen so that chunk data cannot be mutated after creation.
    IDs are deterministic: same file + same lines + same content => same ID.
    """

    # Relative path to the source file from project root
    file_path: str

    # Line number where this chunk starts (1-indexed, inclusive)
    start_line: int

    # Line number where this chunk ends (1-indexed, inclusive)
    end_line: int

    # Raw source code content for these lines
    content: str

    # Programming language — None if detection was skipped or failed
    language: Optional[str] = None

    # Structural classification: "function", "class", "method", "module_level"
    chunk_type: Optional[str] = None

    # Name of the symbol if this chunk corresponds to a named definition
    symbol_name: Optional[str] = None

    # SHA-256 hash of content — used for cache lookups
    content_hash: str = field(init=False)

    # Globally unique chunk identifier — derived from path + lines + hash
    id: str = field(init=False)

    def __post_init__(self):
        """
        Validate inputs and compute derived fields.
        Called automatically by the dataclass machinery after __init__.
        Raises ValueError for invalid line ranges or empty content.
        """
        # Enforce valid line range before computing derived fields
        if self.start_line < 1:
            raise ValueError(
                f"start_line {self.start_line} galat hai — 1 ya usse zyada hona chahiye"
            )
        if self.end_line < self.start_line:
            raise ValueError(
                f"end_line ({self.end_line}) start_line ({self.start_line}) se chhota nahi ho sakta"
            )

        if not self.content.strip():
            raise ValueError("content khali nahi ho sakta — actual code chahiye")

        # Compute content hash for cache keying
        computed_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        object.__setattr__(self, "content_hash", computed_hash)

        # Compute deterministic ID — file path + line range + content hash
        raw_id_string = f"{self.file_path}:{self.start_line}:{self.end_line}:{computed_hash}"
        chunk_id = hashlib.sha256(raw_id_string.encode("utf-8")).hexdigest()
        object.__setattr__(self, "id", chunk_id)

    @property
    def line_count(self) -> int:
        """Total number of lines covered by this chunk."""
        return self.end_line - self.start_line + 1

    def get_relative_line(self, absolute_line: int) -> int:
        """
        Convert an absolute file line number to a 1-indexed position within this chunk.
        Raises ValueError if the line is outside this chunk's range.
        """
        if absolute_line < self.start_line or absolute_line > self.end_line:
            raise ValueError(
                f"Line {absolute_line} is chunk ki range ke bahar hai "
                f"({self.start_line}-{self.end_line})"
            )
        return absolute_line - self.start_line + 1

    def get_absolute_line(self, relative_line: int) -> int:
        """
        Convert a 1-indexed relative line position to the corresponding file line number.
        This is the core conversion used by the mapping layer before report generation.
        Raises ValueError if relative_line is out of range.
        """
        if relative_line < 1 or relative_line > self.line_count:
            raise ValueError(
                f"Relative line {relative_line} out of range — "
                f"chunk mein sirf {self.line_count} lines hai"
            )
        return self.start_line + relative_line - 1

    def __repr__(self) -> str:
        type_info = f" [{self.chunk_type}]" if self.chunk_type else ""
        name_info = f" {self.symbol_name}" if self.symbol_name else ""
        return f"<CodeChunk{type_info}{name_info} {self.file_path}:{self.start_line}-{self.end_line}>"

    def __str__(self) -> str:
        return f"{self.file_path}:{self.start_line}-{self.end_line}"
