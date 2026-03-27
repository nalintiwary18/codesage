"""
ChunkMapper — resolves chunk references to absolute file locations.

Given a chunk_id and relative line positions (1-indexed within the chunk),
this module produces the corresponding absolute file path and line numbers.
All line number resolution in the system must go through here — never inferred
from LLM output directly.

Snippet extraction reads actual bytes from disk to guarantee accuracy.
"""

from pathlib import Path
from typing import Optional

from src.core.chunk import CodeChunk


class ChunkMapper:
    """
    Maintains a lookup table from chunk IDs to CodeChunk objects.
    All absolute-line resolution and snippet extraction happens here.
    """

    def __init__(self, chunks: list[CodeChunk]):
        """
        Build the ID → chunk index at construction time for O(1) lookups.
        """
        # Index chunks by their deterministic ID for fast resolution
        self._chunk_map: dict[str, CodeChunk] = {chunk.id: chunk for chunk in chunks}
        self._total_chunks = len(chunks)

    def get_chunk(self, chunk_id: str) -> Optional[CodeChunk]:
        """Return the CodeChunk for a given ID, or None if not found."""
        return self._chunk_map.get(chunk_id)

    def resolve_absolute_lines(
        self,
        chunk_id: str,
        relative_start: int,
        relative_end: int,
    ) -> Optional[tuple[str, int, int]]:
        """
        Convert a (chunk_id, relative_start, relative_end) reference into
        (file_path, absolute_start_line, absolute_end_line).

        This is the authoritative resolution path for all LLM-generated issue references.
        Returns None if the chunk is not found or the line range is invalid.
        """
        chunk = self._chunk_map.get(chunk_id)
        if chunk is None:
            return None

        # Validate relative line range before converting
        if relative_start < 1 or relative_end < relative_start:
            return None
        if relative_end > chunk.line_count:
            return None

        abs_start = chunk.get_absolute_line(relative_start)
        abs_end = chunk.get_absolute_line(relative_end)

        return (chunk.file_path, abs_start, abs_end)

    def extract_snippet(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        project_root: Optional[str] = None,
    ) -> Optional[str]:
        """
        Read the specified line range directly from disk and return it as a string.
        This guarantees snippets come from the actual source, not from LLM memory.
        Returns None if the file cannot be read or the line range is out of bounds.
        """
        full_path = Path(project_root) / file_path if project_root else Path(file_path)

        if not full_path.is_file():
            return None

        try:
            all_lines = full_path.read_text(encoding="utf-8").splitlines()

            # Convert from 1-indexed to 0-indexed for list slicing
            if start_line < 1 or end_line > len(all_lines):
                return None

            snippet_lines = all_lines[start_line - 1 : end_line]
            return "\n".join(snippet_lines)

        except (OSError, UnicodeDecodeError):
            return None

    @property
    def total_chunks(self) -> int:
        """Number of chunks loaded into this mapper."""
        return self._total_chunks

    def has_chunk(self, chunk_id: str) -> bool:
        """Check whether a chunk ID exists in this mapper's index."""
        return chunk_id in self._chunk_map

    def all_chunk_ids(self) -> list[str]:
        """Return all chunk IDs currently indexed."""
        return list(self._chunk_map.keys())