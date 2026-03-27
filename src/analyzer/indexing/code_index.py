"""
CodeIndex — primary lookup table mapping chunk IDs to metadata.

Stores chunks alongside computed metadata (complexity estimates, symbol
populations, file-level statistics). The retrieval layer queries this index
to rank chunks by importance before sending them to the LLM.
"""

from dataclasses import dataclass, field
from typing import Optional

from src.core.chunk import CodeChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ChunkMetadata:
    """
    Additional computed attributes for a chunk that are not stored on CodeChunk itself.
    Populated by analysis rather than parsing.
    """
    chunk_id: str

    # Heuristic complexity score — higher means more decision paths
    complexity_score: float = 0.0

    # Symbols (functions, classes) defined within this chunk
    symbol_count: int = 0

    # Number of distinct identifiers imported in this chunk
    import_count: int = 0

    # Density of comment lines relative to total lines (0.0–1.0)
    comment_density: float = 0.0

    # Whether this chunk appears to be in an entry-point file
    is_entry_point: bool = False

    # Whether this chunk belongs to a test file
    is_test_file: bool = False

    # Custom tags for retrieval filtering (e.g. "auth", "database")
    tags: list[str] = field(default_factory=list)


class CodeIndex:
    """
    Central index of all chunks and their associated metadata.
    Used by the retrieval layer to select and rank chunks for LLM analysis.
    """

    def __init__(self):
        # chunk_id → CodeChunk
        self._chunks: dict[str, CodeChunk] = {}
        # chunk_id → ChunkMetadata
        self._metadata: dict[str, ChunkMetadata] = {}
        # file_path → list of chunk_ids for that file
        self._file_index: dict[str, list[str]] = {}

    def add_chunk(self, chunk: CodeChunk) -> None:
        """
        Register a chunk and compute its metadata.
        Automatically invoked by add_chunks when indexing a batch.
        """
        self._chunks[chunk.id] = chunk
        self._metadata[chunk.id] = self._compute_metadata(chunk)
        self._file_index.setdefault(chunk.file_path, []).append(chunk.id)

    def add_chunks(self, chunks: list[CodeChunk]) -> None:
        """Index a list of chunks, computing metadata for each."""
        for chunk in chunks:
            self.add_chunk(chunk)
        logger.debug(f"{len(chunks)} chunks added to index")

    def get_chunk(self, chunk_id: str) -> Optional[CodeChunk]:
        """Return the chunk for a given ID, or None if not indexed."""
        return self._chunks.get(chunk_id)

    def get_metadata(self, chunk_id: str) -> Optional[ChunkMetadata]:
        """Return the metadata for a given chunk ID, or None if not found."""
        return self._metadata.get(chunk_id)

    def get_all_chunks(self) -> list[CodeChunk]:
        """Return all indexed chunks as a list (unordered)."""
        return list(self._chunks.values())

    def get_chunks_for_file(self, file_path: str) -> list[CodeChunk]:
        """Return all chunks belonging to a specific file, ordered by start line."""
        ids = self._file_index.get(file_path, [])
        chunks = [self._chunks[cid] for cid in ids if cid in self._chunks]
        return sorted(chunks, key=lambda c: c.start_line)

    def all_file_paths(self) -> list[str]:
        """Return a sorted list of all file paths represented in the index."""
        return sorted(self._file_index.keys())

    @property
    def total_chunks(self) -> int:
        return len(self._chunks)

    @property
    def total_files(self) -> int:
        return len(self._file_index)

    def _compute_metadata(self, chunk: CodeChunk) -> ChunkMetadata:
        """
        Derived metadata heuristics computed from chunk content.
        These estimates guide retrieval scoring without running any LLM calls.
        """
        lines = chunk.content.splitlines()

        # Estimate cyclomatic-like complexity by counting branching keywords
        branching_keywords = {"if", "elif", "else", "for", "while", "try",
                               "except", "finally", "with", "case", "match"}
        complexity = sum(
            1 for line in lines
            if any(f" {kw} " in f" {line.strip()} " for kw in branching_keywords)
        )

        # Count import lines for dependency density
        import_count = sum(
            1 for line in lines
            if line.lstrip().startswith(("import ", "from ", "require(", "use "))
        )

        # Estimate comment density
        comment_lines = sum(
            1 for line in lines
            if line.lstrip().startswith(("#", "//", "/*", "*", "'''", '"""'))
        )
        comment_density = comment_lines / len(lines) if lines else 0.0

        # Simple entry-point detection
        file_lower = chunk.file_path.lower()
        is_entry = any(ep in file_lower for ep in ["main", "__main__", "app", "index", "server", "cli"])

        # Test-file detection
        is_test = "test" in file_lower or "spec" in file_lower

        return ChunkMetadata(
            chunk_id=chunk.id,
            complexity_score=float(complexity),
            symbol_count=1 if chunk.symbol_name else 0,
            import_count=import_count,
            comment_density=round(comment_density, 2),
            is_entry_point=is_entry,
            is_test_file=is_test,
        )
