"""
Report filesystem storage.

Writes Markdown reports to a configured output directory.
If the target filename already exists, a timestamp suffix is appended
to prevent overwriting previous reports.
"""

from datetime import datetime
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ReportStorage:
    """
    Handles creating the output directory and writing report files to disk.
    Collision avoidance uses a timestamp suffix: report.md → report_20240101_120000.md.
    """

    def __init__(self, output_dir: str = "./reports"):
        self._output_dir = Path(output_dir)

    def save_report(self, content: str, filename: str = "report.md") -> Path:
        """
        Write content to <output_dir>/<filename>.
        Creates the output directory if it does not exist.
        If the filename is already taken, a timestamped variant is used instead.
        Returns the path of the saved file.
        """
        self._output_dir.mkdir(parents=True, exist_ok=True)

        target = self._output_dir / filename
        if target.is_file():
            target = self._timestamped_path(target)

        target.write_text(content, encoding="utf-8")
        logger.info(f"Report saved: {target}")
        return target

    def _timestamped_path(self, original: Path) -> Path:
        """
        Append a timestamp to a path stem to avoid overwriting existing reports.
        Example: report.md → report_20240101_120000.md
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return original.parent / f"{original.stem}_{ts}{original.suffix}"

    def list_existing_reports(self) -> list[Path]:
        """
        Return all .md files in the output directory, newest first.
        Returns an empty list if the directory does not exist.
        """
        if not self._output_dir.is_dir():
            return []
        return sorted(
            self._output_dir.glob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    @property
    def output_dir(self) -> Path:
        return self._output_dir
