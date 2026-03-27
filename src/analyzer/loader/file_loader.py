"""
FileLoader — scans a project directory and returns readable source files.

Applies three layers of filtering:
  1. Directory exclusions — known noise dirs (node_modules, .git, etc.)
  2. .gitignore rules — parsed via pathspec if a .gitignore exists
  3. File-level checks — binary content, extension denylist, size limit

Callers receive a list of LoadedFile objects ready for the chunking stage.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pathspec

from src.config.defaults import (
    BINARY_EXTENSIONS,
    DEFAULT_IGNORE_DIRS,
    MAX_FILE_SIZE_BYTES,
)
from src.utils.helpers import is_binary_file, normalize_path_separator
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LoadedFile:
    """
    A successfully loaded source file.
    relative_path is relative to the project root and is used as the
    canonical identifier throughout the rest of the pipeline.
    """
    relative_path: str          # Relative to project root, always with / separators
    absolute_path: str          # Full path on disk
    content: str                # Raw text content of the file
    language: Optional[str] = None   # Set by language_detector after loading
    line_count: int = 0         # Total number of lines in the file


class FileLoader:
    """
    Walks a project directory and collects source files that are suitable
    for analysis. Respects .gitignore exclusion rules via pathspec.
    """

    def __init__(self, project_root: str):
        """
        Resolve the project root and load .gitignore rules if present.
        """
        self._root = Path(project_root).resolve()
        self._gitignore_spec = self._load_gitignore()

        logger.debug(f"Project root: {self._root}")

    def _load_gitignore(self) -> Optional[pathspec.PathSpec]:
        """
        Parse the .gitignore in the project root into a PathSpec object.
        Returns None if no .gitignore exists, so callers can skip that check.
        """
        gitignore_path = self._root / ".gitignore"

        if not gitignore_path.is_file():
            return None

        try:
            patterns = gitignore_path.read_text(encoding="utf-8").splitlines()
            return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        except (OSError, UnicodeDecodeError):
            logger.warning(".gitignore padh nahi paaya — bina rules ke chalunga")
            return None

    def load_all_files(self) -> list[LoadedFile]:
        """
        Recursively scan the project root and return all loadable source files.
        Modifies dirs in-place during os.walk to prune excluded directories early.
        """
        loaded_files: list[LoadedFile] = []

        for root, dirs, files in os.walk(self._root):
            # Prune excluded directories before recursing into them
            dirs[:] = [
                d for d in dirs
                if d not in DEFAULT_IGNORE_DIRS
                and not self._is_gitignored(os.path.join(root, d))
            ]

            for file_name in files:
                abs_path = os.path.join(root, file_name)
                loaded = self._try_load_file(abs_path)
                if loaded:
                    loaded_files.append(loaded)

        logger.info(f"{len(loaded_files)} files loaded")
        return loaded_files

    def _try_load_file(self, abs_path: str) -> Optional[LoadedFile]:
        """
        Attempt to load a single file, applying all filtering rules.
        Returns None (without raising) if the file should be skipped.
        """
        path = Path(abs_path)

        # Skip known binary extensions before touching the filesystem
        if path.suffix.lower() in BINARY_EXTENSIONS:
            return None

        # Skip gitignored files
        if self._is_gitignored(abs_path):
            return None

        # Skip oversized or empty files
        try:
            file_size = path.stat().st_size
            if file_size > MAX_FILE_SIZE_BYTES:
                logger.debug(f"Skip: {path.name} bahut badi file ({file_size} bytes)")
                return None
            if file_size == 0:
                return None
        except OSError:
            return None

        # Skip binary files even if extension wasn't in the denylist
        if is_binary_file(abs_path):
            return None

        # Read the file content
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            logger.debug(f"Skip: {path.name} — encoding issue")
            return None

        relative = normalize_path_separator(str(path.relative_to(self._root)))

        return LoadedFile(
            relative_path=relative,
            absolute_path=str(path),
            content=content,
            line_count=content.count("\n") + 1,
        )

    def _is_gitignored(self, path: str) -> bool:
        """
        Check whether a path matches any pattern in the loaded .gitignore spec.
        Returns False if no spec is loaded.
        """
        if self._gitignore_spec is None:
            return False

        try:
            relative = os.path.relpath(path, self._root)
            relative = normalize_path_separator(relative)
            return self._gitignore_spec.match_file(relative)
        except ValueError:
            return False

    @property
    def project_root(self) -> Path:
        return self._root
