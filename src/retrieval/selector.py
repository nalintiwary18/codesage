"""
ChunkSelector — picks the most analysis-worthy chunks from the full index.

When a project has more chunks than max_chunks allows, a scoring heuristic
ranks all available chunks and takes the top N. Entry-point files, complex
code, and named functions/classes are scored higher.

If the total chunk count is within the limit, all chunks are returned unchanged.
"""

from typing import Optional

from src.core.chunk import CodeChunk
from src.analyzer.indexing.code_index import CodeIndex
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ChunkSelector:
    """
    Filters and ranks all indexed chunks to stay within the per-run token budget.
    Scoring is deterministic — given the same index, the same chunks are selected.
    """

    def __init__(self, max_chunks: int = 50):
        """max_chunks is the hard upper limit on chunks returned by select()."""
        self._max_chunks = max_chunks

    def select(
        self,
        index: CodeIndex,
        priority_files: Optional[list[str]] = None,
    ) -> list[CodeChunk]:
        """
        Return the most important chunks from the index, up to max_chunks.
        priority_files allows callers to bias selection toward specific paths.
        """
        all_chunks = index.get_all_chunks()

        if len(all_chunks) <= self._max_chunks:
            logger.info(f"Selecting all {len(all_chunks)} chunks — within limit")
            return all_chunks

        # Score every chunk and take the top N
        scored: list[tuple[float, CodeChunk]] = [
            (self._score(chunk, index, priority_files), chunk)
            for chunk in all_chunks
        ]
        scored.sort(key=lambda x: x[0], reverse=True)

        selected = [chunk for _, chunk in scored[: self._max_chunks]]
        logger.info(
            f"Selected {len(selected)}/{len(all_chunks)} chunks (max: {self._max_chunks})"
        )
        return selected

    def _score(
        self,
        chunk: CodeChunk,
        index: CodeIndex,
        priority_files: Optional[list[str]],
    ) -> float:
        """
        Compute a priority score for one chunk.
        Higher score → more likely to be selected when chunks must be trimmed.
        """
        score = 0.0

        # Explicit priority files get a large boost
        if priority_files:
            if any(pf in chunk.file_path for pf in priority_files):
                score += 10.0

        # Entry-point patterns get a boost
        entry_indicators = ["main", "__main__", "app", "index", "server", "cli"]
        if any(ind in chunk.file_path.lower() for ind in entry_indicators):
            score += 5.0

        # Named symbols (functions, classes, methods) are preferred over module-level code
        if chunk.chunk_type in ("function", "method", "class"):
            score += 3.0

        # Complexity score from the code index
        metadata = index.get_metadata(chunk.id)
        if metadata:
            score += metadata.complexity_score * 2.0

        # Larger chunks may contain more issues — small bonus, capped to avoid bias
        score += min(chunk.line_count / 50.0, 2.0)

        # Test files are given lower priority in issue detection
        if "test" in chunk.file_path.lower():
            score -= 2.0

        return score
