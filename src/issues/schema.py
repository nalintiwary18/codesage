"""
Issue schema — the authoritative data structure for a detected code issue.

An Issue is born with chunk-relative references (chunk_id + relative_start_line,
relative_end_line) and is progressively enriched through the pipeline:
  1. Detection agent populates chunk_id + relative lines
  2. Structural validator resolves references → file_path + absolute lines
  3. Semantic validator adjusts confidence
  4. Quality scorer sets validation_score
  5. Report generator reads the final, enriched issue

Line numbers must never originate from LLM-generated absolute values.
All absolute references must be resolved through ChunkMapper.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class IssueSeverity(str, Enum):
    """Severity levels from most to least critical."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, Enum):
    """Functional category of the detected issue."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    BUG = "bug"
    CODE_SMELL = "code_smell"
    BEST_PRACTICE = "best_practice"
    ARCHITECTURE = "architecture"
    ERROR_HANDLING = "error_handling"
    MAINTAINABILITY = "maintainability"
    OTHER = "other"


@dataclass
class Issue:
    """
    Represents a single detected problem in the codebase.

    Phase 1 fields (populated by detection agent):
      chunk_id, relative_start_line, relative_end_line,
      title, description, severity, category,
      suggested_fix, snippet, confidence

    Phase 2 fields (populated by structural validator):
      file_path, absolute_start_line, absolute_end_line

    Phase 3 fields (populated by the validation pipeline):
      is_validated, validation_score, validation_notes
    """

    # --- Phase 1: populated by the detection agent ---

    # Chunk containing the problem — must match a known chunk ID in ChunkMapper
    chunk_id: str
    # 1-indexed line within the chunk where the issue starts
    relative_start_line: int
    # 1-indexed line within the chunk where the issue ends
    relative_end_line: int

    title: str
    description: str
    severity: IssueSeverity
    category: IssueCategory

    suggested_fix: Optional[str] = None
    snippet: Optional[str] = None
    # LLM confidence in this detection (0.0–1.0); adjusted by scorer
    confidence: float = 0.7

    # --- Phase 2: populated by structural validator ---

    # File path relative to project root — set only after ChunkMapper resolution
    file_path: Optional[str] = None
    absolute_start_line: Optional[int] = None
    absolute_end_line: Optional[int] = None

    # --- Phase 3: populated by validation pipeline ---

    is_validated: bool = False
    validation_score: float = 0.0
    validation_notes: list[str] = field(default_factory=list)

    @property
    def is_resolved(self) -> bool:
        """True once absolute file + line references have been resolved."""
        return self.file_path is not None and self.absolute_start_line is not None

    @property
    def location_string(self) -> str:
        """
        Human-readable location for display in reports and logs.
        Shows file:lines once resolved, chunk reference otherwise.
        """
        if self.is_resolved:
            return f"{self.file_path}:{self.absolute_start_line}-{self.absolute_end_line}"
        return f"chunk:{self.chunk_id[:12]}... (L{self.relative_start_line}-{self.relative_end_line})"

    def __repr__(self) -> str:
        return (
            f"<Issue [{self.severity.value}] {self.title[:50]} "
            f"at {self.location_string}>"
        )
