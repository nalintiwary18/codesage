"""
SymbolTable — global symbol registry across all analyzed files.

Records every named symbol (function, class, method) seen in the codebase
and the chunk IDs that reference each one.
Used during analysis to enrich context and identify cross-file dependencies.
"""

from dataclasses import dataclass, field
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SymbolEntry:
    """
    A single named symbol encountered in the codebase.
    """
    name: str                             # Symbol identifier
    symbol_type: str                      # "function", "class", or "method"
    file_path: str                        # Source file (relative to project root)
    start_line: int                       # First line of the symbol's definition
    end_line: int                         # Last line of the symbol's definition
    chunk_id: str                         # ID of the chunk that contains this symbol
    parent_class: Optional[str] = None   # Enclosing class name, if this is a method


class SymbolTable:
    """
    Maintains a name → list[SymbolEntry] index for all parsed symbols.
    Lookup is O(1) by name; cross-file symbol detection is O(k) in match count.
    """

    def __init__(self):
        # Primary index: symbol name → all entries with that name
        self._by_name: dict[str, list[SymbolEntry]] = {}
        # Secondary index: file path → all entries in that file
        self._by_file: dict[str, list[SymbolEntry]] = {}

    def register(self, entry: SymbolEntry) -> None:
        """
        Add a symbol to both indexes.
        Duplicate registrations are allowed — the same symbol may appear
        in multiple chunks if a large block was split.
        """
        self._by_name.setdefault(entry.name, []).append(entry)
        self._by_file.setdefault(entry.file_path, []).append(entry)

    def lookup(self, name: str) -> list[SymbolEntry]:
        """
        Return all entries with the given symbol name.
        Returns an empty list if the name has not been registered.
        """
        return self._by_name.get(name, [])

    def get_file_symbols(self, file_path: str) -> list[SymbolEntry]:
        """Return all symbols registered for a given file path."""
        return self._by_file.get(file_path, [])

    def all_symbol_names(self) -> list[str]:
        """Sorted list of every registered symbol name."""
        return sorted(self._by_name.keys())

    @property
    def total_symbols(self) -> int:
        """Total number of registered symbol entries."""
        return sum(len(entries) for entries in self._by_name.values())

    @property
    def total_files(self) -> int:
        """Number of distinct files that have contributed symbols."""
        return len(self._by_file)
