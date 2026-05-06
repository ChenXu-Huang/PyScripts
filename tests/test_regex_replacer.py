import pytest
import re
from pathlib import Path
from unittest.mock import patch

import src.utils.regex_replacer as rr


@pytest.fixture()
def tmp_folder(tmp_path: Path) -> Path:
    return tmp_path

@pytest.fixture()
def py_file(tmp_folder: Path) -> Path:
    f = tmp_folder / "sample.py"
    f.write_text("foo = 1\nbar = foo + 1\n", encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# FileResult
# ---------------------------------------------------------------------------
class TestFileResult:
    @pytest.mark.parametrize("replacements,error,expected", [
        (3, "",    True),
        (0, "err", False),
    ])
    def test_success(self, py_file: Path, replacements: int, error: str, expected: bool) -> None:
        assert rr.FileResult(py_file, replacements, [], error).success is expected

    @pytest.mark.parametrize("replacements,expected", [
        (1, True),
        (0, False),
    ])
    def test_changed(self, py_file: Path, replacements: int, expected: bool) -> None:
        assert rr.FileResult(py_file, replacements, []).changed is expected


# ---------------------------------------------------------------------------
# ReplaceResult
# ---------------------------------------------------------------------------
class TestReplaceResult:
    def _make(self, *fr, scanned=3) -> rr.ReplaceResult:
        rrt = rr.ReplaceResult(files_scanned=scanned)
        rrt.file_results.extend(fr)
        return rrt

    def test_files_modified(self, py_file: Path) -> None:
        rrt = self._make(rr.FileResult(py_file, 2, []), rr.FileResult(py_file, 0, []))
        assert rrt.files_modified == 1

    def test_total_replacements(self, py_file: Path) -> None:
        rrt = self._make(rr.FileResult(py_file, 3, []), rr.FileResult(py_file, 7, []))
        assert rrt.total_replacements == 10

    def test_errors(self, py_file: Path) -> None:
        ok = rr.FileResult(py_file, 1, [])
        err = rr.FileResult(py_file, 0, [], "boom")
        assert self._make(ok, err).errors == [err]

    def test_summary_stats(self, py_file: Path) -> None:
        rrt = self._make(rr.FileResult(py_file, 2, [(1, "o", "n")]), scanned=5)
        t = rrt.summary()
        assert "Files scanned:      5" in t
        assert "Files with changes: 1" in t
        assert "Total replacements: 2" in t

    def test_summary_dry_run(self, py_file: Path) -> None:
        rrt = self._make(rr.FileResult(py_file, 1, []))
        assert "[DRY RUN]" in rrt.summary(dry_run=True)
        assert "[DRY RUN]" not in rrt.summary()

    def test_summary_overflow(self, py_file: Path) -> None:
        many = [(i + 1, f"o{i}", f"n{i}") for i in range(10)]
        rrt_overflow    = self._make(rr.FileResult(py_file, 10, many))
        rrt_no_overflow = self._make(rr.FileResult(py_file, 3, [(1, "a", "b")] * 3))
        assert "and 7 more change(s)" in rrt_overflow.summary(max_changes_per_file=3)
        assert "more change" not in rrt_no_overflow.summary(max_changes_per_file=5)


# ---------------------------------------------------------------------------
# _normalize_extensions
# ---------------------------------------------------------------------------
class TestNormalizeExtensions:
    def test_normalization(self) -> None:
        result = rr._normalize_extensions(["py", ".txt", ".md"])
        assert ".py" in result
        assert ".txt" in result
        assert isinstance(result, frozenset)

    def test_dedup(self) -> None:
        assert rr._normalize_extensions(["py", ".py"]) == frozenset({".py"})


# ---------------------------------------------------------------------------
# _compile_pattern
# ---------------------------------------------------------------------------
class TestCompilePattern:
    def test_valid_and_flags(self) -> None:
        assert isinstance(rr._compile_pattern(r"\d+"), re.Pattern)
        assert rr._compile_pattern("foo", ignore_case=True).flags & re.IGNORECASE
        assert not (rr._compile_pattern("foo").flags & re.IGNORECASE)

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            rr._compile_pattern("[unclosed")


# ---------------------------------------------------------------------------
# _read_file
# ---------------------------------------------------------------------------
class TestReadFile:
    def test_reads_utf8_and_latin1(self, tmp_path: Path) -> None:
        utf8 = tmp_path / "a.txt"
        utf8.write_text("hello", encoding="utf-8")
        assert rr._read_file(utf8) == "hello"

        latin1 = tmp_path / "b.txt"
        latin1.write_bytes(b"\xe9\xe0")
        assert isinstance(rr._read_file(latin1), str)

    def test_oserror_propagates(self, tmp_path: Path) -> None:
        f = tmp_path / "x.txt"
        f.write_text("x", encoding="utf-8")
        with patch.object(Path, "read_text", side_effect=PermissionError("denied")):
            with pytest.raises(OSError):
                rr._read_file(f)

        with pytest.raises(OSError):
            rr._read_file(tmp_path / "ghost.txt")


# ---------------------------------------------------------------------------
# _write_file
# ---------------------------------------------------------------------------
class TestWriteFile:
    def test_writes_and_overwrites(self, tmp_path: Path) -> None:
        f = tmp_path / "out.txt"
        rr._write_file(f, "你好")
        assert f.read_text(encoding="utf-8") == "你好"

        rr._write_file(f, "new")
        assert f.read_text(encoding="utf-8") == "new"


# ---------------------------------------------------------------------------
# _backup
# ---------------------------------------------------------------------------
class TestBackup:
    def test_creates_bak_and_not_symlink(self, tmp_path: Path) -> None:
        f = tmp_path / "src.py"
        f.write_text("data", encoding="utf-8")
        rr._backup(f)
        bak = tmp_path / "src.py.bak"
        assert bak.exists()
        assert bak.read_text(encoding="utf-8") == "data"
        assert not bak.is_symlink()


# ---------------------------------------------------------------------------
# _changed_lines
# ---------------------------------------------------------------------------
class TestChangedLines:
    def test_diff_count_and_format(self) -> None:
        single = rr._changed_lines("foo\nbar\n", "foo\nbaz\n")
        assert len(single) == 1
        lineno, orig, new = single[0]
        assert lineno == 2
        assert orig.endswith("...")
        assert "bar" in orig

        assert len(rr._changed_lines("a\nb\nc\n", "x\nb\ny\n")) == 2

    def test_no_diff(self) -> None:
        assert rr._changed_lines("same\n", "same\n") == []

    def test_truncated(self) -> None:
        _, preview, _ = rr._changed_lines("x" * 200 + "\n", "y" * 200 + "\n")[0]
        assert preview.endswith("...")


# ---------------------------------------------------------------------------
# _find_files
# ---------------------------------------------------------------------------
class TestFindFiles:
    def test_by_ext_and_no_dot_normalised(self, tmp_folder: Path) -> None:
        (tmp_folder / "a.py").write_text("")
        (tmp_folder / "b.js").write_text("")
        (tmp_folder / "script.py").write_text("")
        files = rr._find_files(tmp_folder, [".py"])
        names = {f.name for f in files}
        assert "a.py" in names and "script.py" in names and "b.js" not in names
        assert len(files) == 2

        assert any(f.name == "script.py" for f in rr._find_files(tmp_folder, ["py"]))

    def test_default_ext(self, tmp_folder: Path) -> None:
        (tmp_folder / "note.md").write_text("")
        (tmp_folder / "img.png").write_text("")
        names = {f.name for f in rr._find_files(tmp_folder, None)}
        assert "note.md" in names and "img.png" not in names

    def test_recurses_and_sorted(self, tmp_folder: Path) -> None:
        sub = tmp_folder / "sub"
        sub.mkdir()
        (sub / "deep.py").write_text("")
        for n in ["c.py", "a.py", "b.py"]:
            (tmp_folder / n).write_text("")
        files = rr._find_files(tmp_folder, [".py"])
        assert any(f.name == "deep.py" for f in files)
        assert files == sorted(files)


# ---------------------------------------------------------------------------
# _replace_in_file
# ---------------------------------------------------------------------------
class TestReplaceInFile:
    C = staticmethod(re.compile)

    def test_replaces_writes_and_changed_lines(self, py_file: Path) -> None:
        r = rr._replace_in_file(py_file, self.C(r"foo"), "baz", dry_run=False, backup=False)
        assert r.changed and r.success
        assert "baz" in py_file.read_text(encoding="utf-8")
        assert len(r.changed_lines) >= 1

    def test_dry_run_no_change(self, py_file: Path) -> None:
        orig = py_file.read_text(encoding="utf-8")
        r = rr._replace_in_file(py_file, self.C(r"foo"), "baz", dry_run=True, backup=False)
        assert r.changed and py_file.read_text(encoding="utf-8") == orig

    def test_no_match(self, py_file: Path) -> None:
        r = rr._replace_in_file(py_file, self.C(r"NOMATCH"), "x", dry_run=False, backup=False)
        assert not r.changed and r.success

    def test_backup_created(self, py_file: Path) -> None:
        rr._replace_in_file(py_file, self.C(r"foo"), "baz", dry_run=False, backup=True)
        assert py_file.with_suffix(".py.bak").exists()

    def test_io_errors(self, py_file: Path, tmp_path: Path) -> None:
        r_read = rr._replace_in_file(tmp_path / "ghost.py", self.C(r"foo"), "x", dry_run=False, backup=False)
        assert not r_read.success and r_read.replacements == 0

        with patch.object(rr, "_write_file", side_effect=OSError("disk full")):
            r_write = rr._replace_in_file(py_file, self.C(r"foo"), "baz", dry_run=False, backup=False)
        assert not r_write.success

    def test_backup_failure_nonfatal(self, py_file: Path) -> None:
        with patch.object(rr, "_backup", side_effect=OSError("no space")):
            r = rr._replace_in_file(py_file, self.C(r"foo"), "baz", dry_run=False, backup=True)
        assert r.changed and r.success


# ---------------------------------------------------------------------------
# replace_in_folder (integration)
# ---------------------------------------------------------------------------
class TestReplaceInFolder:
    def test_basic_and_scanned_count(self, tmp_folder: Path) -> None:
        (tmp_folder / "a.py").write_text("hello world\n", encoding="utf-8")
        (tmp_folder / "b.py").write_text("x\n", encoding="utf-8")
        (tmp_folder / "c.txt").write_text("x\n", encoding="utf-8")
        rrt = rr.replace_in_folder(tmp_folder, r"hello", "hi")
        assert rrt.total_replacements == 1
        assert (tmp_folder / "a.py").read_text(encoding="utf-8") == "hi world\n"
        assert rrt.files_scanned == 3

    def test_dry_run(self, tmp_folder: Path) -> None:
        f = tmp_folder / "a.py"
        f.write_text("hello\n", encoding="utf-8")
        rr.replace_in_folder(tmp_folder, r"hello", "bye", dry_run=True)
        assert f.read_text(encoding="utf-8") == "hello\n"

    def test_ignore_case(self, tmp_folder: Path) -> None:
        (tmp_folder / "a.txt").write_text("Hello HELLO hello\n", encoding="utf-8")
        assert rr.replace_in_folder(tmp_folder, r"hello", "hi", ignore_case=True).total_replacements == 3

    def test_custom_extensions(self, tmp_folder: Path) -> None:
        (tmp_folder / "a.py").write_text("foo\n", encoding="utf-8")
        (tmp_folder / "b.log").write_text("foo\n", encoding="utf-8")
        rrt = rr.replace_in_folder(tmp_folder, r"foo", "bar", extensions=[".log"])
        assert rrt.total_replacements == 1
        assert (tmp_folder / "a.py").read_text(encoding="utf-8") == "foo\n"

    @pytest.mark.parametrize("make_path,match", [
        (lambda p: p / "ghost",  "Directory does not exist"),
        (lambda p: p / "a.txt",  "Path is not a directory"),
    ])
    def test_invalid_path_raises(self, tmp_folder: Path, make_path, match: str) -> None:
        (tmp_folder / "a.txt").write_text("x")
        with pytest.raises(ValueError, match=match):
            rr.replace_in_folder(make_path(tmp_folder), r"x", "y")

    def test_invalid_pattern(self, tmp_folder: Path) -> None:
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            rr.replace_in_folder(tmp_folder, r"[bad", "y")

    def test_no_match(self, tmp_folder: Path) -> None:
        (tmp_folder / "a.py").write_text("hello\n", encoding="utf-8")
        rrt = rr.replace_in_folder(tmp_folder, r"NOMATCH", "y")
        assert rrt.files_modified == 0 and rrt.file_results == []

    def test_backreference(self, tmp_folder: Path) -> None:
        (tmp_folder / "a.py").write_text("2024-01-15\n", encoding="utf-8")
        rr.replace_in_folder(tmp_folder, r"(\d{4})-(\d{2})-(\d{2})", r"\3/\2/\1")
        assert "15/01/2024" in (tmp_folder / "a.py").read_text(encoding="utf-8")

    def test_multiple_files(self, tmp_folder: Path) -> None:
        for i in range(5):
            (tmp_folder / f"f{i}.py").write_text(f"old_{i}\n", encoding="utf-8")
        rrt = rr.replace_in_folder(tmp_folder, r"old_\d", "new")
        assert rrt.files_modified == 5 and rrt.total_replacements == 5

    def test_summary_is_str(self, tmp_folder: Path) -> None:
        (tmp_folder / "a.py").write_text("foo\n", encoding="utf-8")
        assert isinstance(rr.replace_in_folder(tmp_folder, r"foo", "bar").summary(), str)