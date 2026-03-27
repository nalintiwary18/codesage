"""
Analysis cache — skips re-analysis of chunks whose content has not changed.

Cache entries are keyed by content_hash (SHA-256 of the chunk content).
Stored as a single JSON file under .codesage_cache/analysis_cache.json.
Set enabled=False to run a fully cold analysis (useful when debugging the pipeline).
"""

import json
from pathlib import Path
from typing import Any, Optional

from src.config.defaults import CACHE_DIR_NAME
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisCache:
    """
    Persists analysis results between runs using content hashes as keys.
    On startup the existing JSON file is loaded; writes happen after every set().
    """

    def __init__(self, project_root: str, enabled: bool = True):
        self._enabled = enabled
        self._cache_dir = Path(project_root) / CACHE_DIR_NAME
        self._cache_file = self._cache_dir / "analysis_cache.json"
        self._cache: dict[str, Any] = {}

        if self._enabled:
            self._load()

    def _load(self) -> None:
        """
        Read the on-disk JSON cache into memory.
        Silently resets to an empty dict on any error.
        """
        if not self._cache_file.is_file():
            return

        try:
            with open(self._cache_file, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
            logger.debug(f"Loaded {len(self._cache)} cached entries")
        except (json.JSONDecodeError, OSError):
            logger.warning("Cache file unreadable — starting fresh")
            self._cache = {}

    def _save(self) -> None:
        """
        Persist the in-memory cache to disk.
        Creates the cache directory if it does not already exist.
        Silently ignores write errors so cache failures never break the pipeline.
        """
        if not self._enabled:
            return
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.warning(f"Cache write failed: {e}")

    def get(self, content_hash: str) -> Optional[Any]:
        """Return the cached result for a content hash, or None if not found."""
        if not self._enabled:
            return None
        return self._cache.get(content_hash)

    def set(self, content_hash: str, result: Any) -> None:
        """Store an analysis result and immediately persist to disk."""
        if not self._enabled:
            return
        self._cache[content_hash] = result
        self._save()

    def has(self, content_hash: str) -> bool:
        """Return True if a cached entry exists for the given hash."""
        if not self._enabled:
            return False
        return content_hash in self._cache

    def clear(self) -> None:
        """
        Delete all cached entries from memory and from disk.
        Next analysis run will be fully cold.
        """
        self._cache = {}
        if self._cache_file.is_file():
            try:
                self._cache_file.unlink()
                logger.info("Cache cleared")
            except OSError:
                logger.warning("Could not delete cache file")

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def is_enabled(self) -> bool:
        return self._enabled
