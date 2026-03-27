"""
StructuralValidator — verifies that each issue's chunk reference is real and
that the reported line numbers fall within actual file bounds.

Performs six sequential checks for each issue:
  1. chunk_id exists in ChunkMapper
  2. Relative lines are within the chunk's line count
  3. Absolute line mapping succeeds
  4. The resolved file exists on disk
  5. Absolute line numbers are within the file's actual length
  6. Snippet is updated from the real file content

Issues that fail any check are flagged is_validated=False and excluded
from the final report by the filtering step.
"""

from pathlib import Path

from src.core.mapping import ChunkMapper
from src.issues.schema import Issue
from src.utils.helpers import read_file_lines
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StructuralValidator:
    """
    Validates and enriches issues by resolving their chunk references to
    absolute file positions. Must be run before the report is generated.
    """

    def __init__(self, chunk_mapper: ChunkMapper, project_root: str):
        """
        chunk_mapper holds the chunk ID → CodeChunk index.
        project_root is used to resolve relative file paths to disk locations.
        """
        self._mapper = chunk_mapper
        self._root = Path(project_root).resolve()

    def validate_issue(self, issue: Issue) -> Issue:
        """
        Run all six structural checks on one issue, mutating it in place.
        Sets is_validated, file_path, absolute lines, snippet, and validation_notes.
        Returns the mutated issue.
        """
        notes: list[str] = []
        is_valid = True

        # Check 1 — chunk must exist in mapper
        chunk = self._mapper.get_chunk(issue.chunk_id)
        if chunk is None:
            notes.append("FAIL: chunk_id not found in mapper — stale or hallucinated reference")
            issue.is_validated = False
            issue.validation_notes = notes
            return issue

        # Check 2 — relative line range must be within chunk bounds
        if issue.relative_start_line < 1 or issue.relative_end_line > chunk.line_count:
            notes.append(
                f"FAIL: relative lines {issue.relative_start_line}-{issue.relative_end_line} "
                f"are outside chunk range 1-{chunk.line_count}"
            )
            is_valid = False

        # Check 3 — absolute line resolution
        if is_valid:
            mapping_result = self._mapper.resolve_absolute_lines(
                issue.chunk_id,
                issue.relative_start_line,
                issue.relative_end_line,
            )

            if mapping_result is None:
                notes.append("FAIL: absolute line mapping returned None")
                is_valid = False
            else:
                file_path, abs_start, abs_end = mapping_result
                issue.file_path = file_path
                issue.absolute_start_line = abs_start
                issue.absolute_end_line = abs_end

                # Check 4 — file must exist on disk
                full_path = self._root / file_path
                if not full_path.is_file():
                    notes.append(f"FAIL: '{file_path}' not found on disk")
                    is_valid = False
                else:
                    # Check 5 — absolute lines within file length
                    file_lines = read_file_lines(str(full_path))
                    if file_lines is not None:
                        if abs_end > len(file_lines):
                            notes.append(
                                f"FAIL: line {abs_end} exceeds file length ({len(file_lines)})"
                            )
                            is_valid = False
                        else:
                            notes.append("PASS: file found, line range valid")

                            # Check 6 — replace snippet with actual disk content
                            actual_snippet = self._mapper.extract_snippet(
                                file_path, abs_start, abs_end,
                                project_root=str(self._root),
                            )
                            if actual_snippet:
                                issue.snippet = actual_snippet
                                notes.append("PASS: snippet updated from real file content")
                    else:
                        notes.append("WARN: file unreadable — encoding issue")

        issue.is_validated = is_valid
        issue.validation_notes = notes

        if not is_valid:
            logger.warning(f"Structural validation failed: {issue.title[:40]}")

        return issue

    def validate_all(self, issues: list[Issue]) -> list[Issue]:
        """
        Validate a list of issues, returning only those that pass all checks.
        Invalid issues are dropped from the result.
        """
        passed: list[Issue] = []
        failed = 0

        for issue in issues:
            self.validate_issue(issue)
            if issue.is_validated:
                passed.append(issue)
            else:
                failed += 1

        logger.info(f"Structural validation: {len(passed)} passed, {failed} failed")
        return passed
