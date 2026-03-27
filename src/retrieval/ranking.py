"""
Chunk ranking utilities.

Provides a standalone rank_chunks() function and a RankedChunk type that
associates a chunk with its importance score and final rank.
The selector uses this for top-N selection; callers can also use it
independently for priority-sorted reporting.
"""

from dataclasses import dataclass

from src.core.chunk import CodeChunk
from src.analyzer.indexing.code_index import CodeIndex


@dataclass
class RankedChunk:
    """A chunk paired with its computed importance score and rank position."""
    chunk: CodeChunk
    score: float
    rank: int   # 1-indexed; rank 1 = highest score


def rank_chunks(
    chunks: list[CodeChunk],
    index: CodeIndex,
) -> list[RankedChunk]:
    """
    Sort chunks by computed importance and assign sequential rank values.
    Returns a list sorted highest-importance first (rank 1 = best).
    """
    ranked: list[RankedChunk] = [
        RankedChunk(chunk=chunk, score=_score(chunk, index), rank=0)
        for chunk in chunks
    ]

    ranked.sort(key=lambda r: r.score, reverse=True)

    for i, item in enumerate(ranked):
        item.rank = i + 1

    return ranked


def _score(chunk: CodeChunk, index: CodeIndex) -> float:
    """
    Multi-factor importance score for a single chunk.

    Factors and their rationale:
    - Complexity (weight 3.0): more branches → higher issue probability
    - File category (up to 5.0): core/api/auth files have higher stakes
    - Chunk type (up to 3.0): named functions/classes over anonymous code
    - Size (up to 3.0): more lines potentially means more issues
    - Named symbol (1.5): named code is more reusable and impactful
    - Test/config penalty: lower-priority noise for issue detection
    """
    score = 0.0

    # Complexity from the index metadata
    metadata = index.get_metadata(chunk.id)
    if metadata:
        score += metadata.complexity_score * 3.0

    # File category boosts
    file_path_lower = chunk.file_path.lower()
    category_boosts = [
        ("main", 5.0), ("app", 4.0), ("core", 4.0), ("server", 4.0),
        ("api", 3.5), ("auth", 3.5), ("handler", 3.0), ("service", 3.0),
        ("model", 2.5), ("controller", 2.5), ("router", 2.5),
    ]
    for pattern, boost in category_boosts:
        if pattern in file_path_lower:
            score += boost
            break

    # Chunk type contribution
    type_scores = {"class": 3.0, "function": 2.5, "method": 2.0, "module_level": 1.0}
    score += type_scores.get(chunk.chunk_type or "", 1.0)

    # Size contribution (capped)
    score += min(chunk.line_count * 0.05, 3.0)

    # Named symbol bonus
    if chunk.symbol_name:
        score += 1.5

    # Penalties for lower-signal file categories
    if "test" in file_path_lower or "spec" in file_path_lower:
        score *= 0.5
    if any(p in file_path_lower for p in ["setup", "config", "settings", "__init__"]):
        score *= 0.7

    return round(score, 2)
