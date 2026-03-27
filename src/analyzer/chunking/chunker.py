"""
Chunker — converts loaded source files into CodeChunk objects.

Decides which parser to use (AST for Python, regex for others), delegates
parsing to produce ParsedBlock objects, then maps those blocks to CodeChunk
instances with deterministic IDs.

Large blocks that exceed MAX_CHUNK_LINES are split into overlapping sub-chunks
so the LLM always receives manageable segments with predictable token counts.
"""

from typing import Optional

from src.analyzer.loader.file_loader import LoadedFile
from src.analyzer.parsing.ast_parser import parse_python_ast, ParsedBlock
from src.analyzer.parsing.regex_parser import parse_with_regex
from src.config.defaults import MAX_CHUNK_LINES
from src.core.chunk import CodeChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Lines of overlap between split sub-chunks — preserves context at boundaries
SPLIT_OVERLAP_LINES = 5


class Chunker:
    """
    Orchestrates file parsing and chunk creation for all loaded files.
    Each file is routed to the appropriate parser, then chunked independently.
    """

    def __init__(self, max_chunk_lines: Optional[int] = None):
        """
        max_chunk_lines — hard upper limit on lines per chunk.
        Falls back to the project default if not specified.
        """
        self._max_chunk_lines = max_chunk_lines or MAX_CHUNK_LINES

    def chunk_all_files(self, files: list[LoadedFile]) -> list[CodeChunk]:
        """
        Produce chunks for all files. Returns a flat list of CodeChunk objects
        ordered by file path and start line.
        """
        all_chunks: list[CodeChunk] = []

        for loaded_file in files:
            file_chunks = self._chunk_file(loaded_file)
            all_chunks.extend(file_chunks)

        logger.info(f"{len(all_chunks)} chunks created from {len(files)} files")
        return all_chunks

    def _chunk_file(self, file: LoadedFile) -> list[CodeChunk]:
        """
        Parse one file, produce ParsedBlocks, then convert to CodeChunks.
        Falls back to whole-file chunking if parsing returns nothing.
        """
        language = file.language or ""
        lines = file.content.splitlines()

        if not lines:
            return []

        # Select parser based on language
        blocks = self._parse_file(file)

        # If parsing produced no blocks, treat the whole file as one block
        if not blocks:
            blocks = [_make_whole_file_block(len(lines))]

        # Convert ParsedBlock → CodeChunk, splitting when necessary
        chunks: list[CodeChunk] = []
        for block in blocks:
            chunk_lines = lines[block.start_line - 1 : block.end_line]
            if not chunk_lines:
                continue

            block_content = "\n".join(chunk_lines)

            if block.end_line - block.start_line + 1 <= self._max_chunk_lines:
                # Block fits inside the limit — one chunk
                chunk = self._make_chunk(file, block, block_content, language)
                if chunk:
                    chunks.append(chunk)
            else:
                # Block is too large — split into overlapping sub-chunks
                split = self._split_large_block(file, block, chunk_lines, language)
                chunks.extend(split)

        return chunks

    def _parse_file(self, file: LoadedFile) -> list[ParsedBlock]:
        """
        Choose and invoke the correct parser for the file's language.
        Python → AST parser; everything else → regex parser.
        """
        language = (file.language or "").lower()

        if language == "python":
            return parse_python_ast(file.content, file.relative_path)
        else:
            return parse_with_regex(file.content, language, file.relative_path)

    def _make_chunk(
        self,
        file: LoadedFile,
        block: ParsedBlock,
        content: str,
        language: str,
    ) -> Optional[CodeChunk]:
        """
        Construct a CodeChunk from a ParsedBlock.
        Returns None if the content is whitespace-only.
        """
        if not content.strip():
            return None

        return CodeChunk(
            file_path=file.relative_path,
            start_line=block.start_line,
            end_line=block.end_line,
            content=content,
            language=language or None,
            chunk_type=block.block_type,
            symbol_name=block.name if block.name != "__module__" else None,
        )

    def _split_large_block(
        self,
        file: LoadedFile,
        block: ParsedBlock,
        block_lines: list[str],
        language: str,
    ) -> list[CodeChunk]:
        """
        Divide a block that exceeds max_chunk_lines into overlapping sub-chunks.
        Overlap ensures the LLM has context from the previous segment.
        Sub-chunks inherit the parent block's type and symbol_name.
        """
        chunks: list[CodeChunk] = []
        stride = self._max_chunk_lines - SPLIT_OVERLAP_LINES
        if stride < 1:
            stride = self._max_chunk_lines

        total_lines = len(block_lines)
        offset = 0

        while offset < total_lines:
            sub_line_count = min(self._max_chunk_lines, total_lines - offset)
            sub_lines = block_lines[offset : offset + sub_line_count]
            content = "\n".join(sub_lines)

            if content.strip():
                abs_start = block.start_line + offset
                abs_end = abs_start + sub_line_count - 1

                try:
                    chunk = CodeChunk(
                        file_path=file.relative_path,
                        start_line=abs_start,
                        end_line=abs_end,
                        content=content,
                        language=language or None,
                        chunk_type=block.block_type,
                        symbol_name=block.name if block.name != "__module__" else None,
                    )
                    chunks.append(chunk)
                except ValueError:
                    pass  # Silently skip invalid ranges

            offset += stride

        return chunks


# ------------------------------------------------------------------ helpers --

def _make_whole_file_block(total_lines: int) -> ParsedBlock:
    """Return a synthetic ParsedBlock that covers the entire file."""
    from src.analyzer.parsing.ast_parser import ParsedBlock
    return ParsedBlock(
        block_type="module_level",
        name="__module__",
        start_line=1,
        end_line=total_lines,
    )
