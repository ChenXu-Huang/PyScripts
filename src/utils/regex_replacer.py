__all__ = ["replace_in_folder", "FileResult", "ReplaceResult"]

import re
import shutil
from dataclasses import dataclass, field
from itertools import zip_longest
from pathlib import Path

from ..logger import get_logger, log_exceptions

logger = get_logger(__name__)

_DEFAULT_EXTENSIONS = frozenset({".txt", ".py", ".js", ".html", ".css", ".json", ".xml", ".md", ".yaml", ".yml"})

_ENCODINGS = ("utf-8", "latin-1")
_CONTEXT_LEN = 500


@dataclass
class FileResult:
    """Result of replacing within a single file.

    Attributes:
        path: Path to the file
        replacements: Number of replacements made; 0 means no changes
        changed_lines: Preview of changed lines as (line_no, old, new) tuples
        error: Non-empty if processing failed
    """

    path: Path
    replacements: int
    changed_lines: list[tuple[int, str, str]]
    error: str = ""

    @property
    def success(self) -> bool:
        return not bool(self.error)

    @property
    def changed(self) -> bool:
        return self.replacements > 0


@dataclass
class ReplaceResult:
    """Aggregated result for a batch replacement.

    Attributes:
        files_scanned: Total number of files scanned
        file_results: Results per file (only includes changed or errored entries)
    """

    files_scanned: int = 0
    file_results: list[FileResult] = field(default_factory=list)

    @property
    def files_modified(self) -> int:
        return sum(r.changed for r in self.file_results)

    @property
    def total_replacements(self) -> int:
        return sum(r.replacements for r in self.file_results)

    @property
    def errors(self) -> list[FileResult]:
        return [r for r in self.file_results if not r.success]

    def __str__(self) -> str:
        return self.summary()

    def summary(self, *, dry_run: bool = False, max_changes_per_file: int = 500) -> str:
        prefix = "[DRY RUN] " if dry_run else ""
        lines = [
            "=" * 50,
            f"{prefix}Summary:",
            f"  Files scanned:      {self.files_scanned}",
            f"  Files with changes: {self.files_modified}",
            f"  Total replacements: {self.total_replacements}",
        ]

        if self.errors:
            lines.append(f"  Errors:             {len(self.errors)}")

        for result in self.file_results:
            if not (result.changed and result.changed_lines):
                continue
            lines.append(f"\n  {result.path}  ({result.replacements} replacement(s))")
            for _, orig, new in result.changed_lines[:max_changes_per_file]:
                lines += [orig, new]
            overflow = len(result.changed_lines) - max_changes_per_file
            if overflow > 0:
                lines.append(f"  ... and {overflow} more change(s)")

        if dry_run:
            lines += [
                "",
                "[INFO] Dry run — no files were modified.",
                "       Remove dry_run=True to apply changes.",
            ]

        lines.append("=" * 50)
        return "\n".join(lines)


def _normalize_extensions(extensions: list[str]) -> frozenset[str]:
    return frozenset(ext if ext.startswith(".") else f".{ext}" for ext in extensions)


def _compile_pattern(pattern: str, *, ignore_case: bool = False) -> re.Pattern:
    flags = re.MULTILINE | (re.IGNORECASE if ignore_case else 0)
    try:
        return re.compile(pattern, flags)
    except re.error as exc:
        raise ValueError(f"Invalid regex pattern: {exc}") from exc


def _read_file(path: Path) -> str:
    for encoding in _ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise OSError(f"Could not decode file {path} with {' or '.join(_ENCODINGS)}")


def _write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _backup(path: Path) -> None:
    shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))


def _changed_lines(original: str, modified: str) -> list[tuple[int, str, str]]:
    return [
        (i, f"{orig[:_CONTEXT_LEN]}...", f"{new[:_CONTEXT_LEN]}...")
        for i, (orig, new) in enumerate(zip_longest(
            original.splitlines(), modified.splitlines(), fillvalue=""
        ), start=1)
        if orig != new
    ]


def _find_files(folder: Path, extensions: list[str] | None) -> list[Path]:
    exts = _normalize_extensions(extensions) if extensions else _DEFAULT_EXTENSIONS
    return sorted(path for ext in exts for path in folder.rglob(f"*{ext}"))


def _replace_in_file(
    path: Path,
    compiled: re.Pattern,
    replacement: str,
    *,
    dry_run: bool,
    backup: bool,
) -> FileResult:
    try:
        content = _read_file(path)
    except OSError as exc:
        logger.error("Failed to read %s: %s", path, exc)
        return FileResult(path, 0, [], str(exc))

    new_content, count = compiled.subn(replacement, content)
    if count == 0:
        return FileResult(path, 0, [])

    diff = _changed_lines(content, new_content)

    if dry_run:
        return FileResult(path, count, diff)

    if backup:
        try:
            _backup(path)
        except OSError as exc:
            logger.warning("Failed to create backup for %s: %s", path, exc)

    try:
        _write_file(path, new_content)
    except OSError as exc:
        logger.error("Failed to write %s: %s", path, exc)
        return FileResult(path, 0, [], str(exc))

    logger.info("Replaced %d occurrence(s) in %s", count, path)
    return FileResult(path, count, diff)


@log_exceptions()
def replace_in_folder(
    folder: Path,
    pattern: str,
    replacement: str,
    extensions: list[str] | None = None,
    *,
    ignore_case: bool = False,
    dry_run: bool = False,
    backup: bool = False,
) -> ReplaceResult:
    """Batch regex-replace across all matching files in a folder.

    Parameters:
        folder: Root directory to process.
        pattern: Regex pattern string.
        replacement: Replacement string; may contain back-references (\\1, \\2, etc.).
        extensions: List of extensions to process; ``None`` uses the default text-file set.
        ignore_case: Whether to ignore case.
        dry_run: Preview only; do not modify files.
        backup: Create a ``.bak`` backup before modifying.

    Returns:
        :class:`ReplaceResult` summary object.

    Raises:
        ValueError: *folder* does not exist or is not a directory, or *pattern* is invalid.
    """

    if not folder.exists():
        raise ValueError(f"Directory does not exist: {folder}")
    if not folder.is_dir():
        raise ValueError(f"Path is not a directory: {folder}")

    compiled = _compile_pattern(pattern, ignore_case=ignore_case)
    files = _find_files(folder, extensions)
    logger.info("Scanned %s, found %d file(s)", folder.resolve(), len(files))

    result = ReplaceResult(files_scanned=len(files))
    for path in files:
        file_result = _replace_in_file(path, compiled, replacement, dry_run=dry_run, backup=backup)
        if file_result.changed or not file_result.success:
            result.file_results.append(file_result)

    logger.info(result)
    return result
