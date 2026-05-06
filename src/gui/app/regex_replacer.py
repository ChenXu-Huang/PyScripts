"""Regex Replace tool — GUI widget."""

__all__ = ["ToolWidget"]

import threading
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QFrame, QSizePolicy, QScrollArea, QProgressBar,
    QSplitter
)
from PySide6.QtCore import Qt, Signal, QEvent, QObject
from PySide6.QtGui import QCursor, QFont

from ..i18n import tr, language_changed
from ..theme import theme_manager
from ..widgets import SectionLabel, InputField, FolderPicker
from ...logger import get_logger
from ...config import config_manager
from ...utils.regex_replacer import replace_in_folder, ReplaceResult, FileResult

logger = get_logger(__name__)


class _WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)


class _ReplaceWorker(threading.Thread):
    def __init__(
        self,
        folder: Path,
        pattern: str,
        replacement: str,
        extensions: list[str] | None,
        *,
        ignore_case: bool,
        dry_run: bool,
        backup: bool,
    ) -> None:
        super().__init__(daemon=True)
        self.folder = folder
        self.pattern = pattern
        self.replacement = replacement
        self.extensions = extensions
        self.ignore_case = ignore_case
        self.dry_run = dry_run
        self.backup = backup
        self.signals = _WorkerSignals()

    def run(self) -> None:
        try:
            result = replace_in_folder(
                self.folder,
                self.pattern,
                self.replacement,
                self.extensions or None,
                ignore_case=self.ignore_case,
                dry_run=self.dry_run,
                backup=self.backup,
            )
            self.signals.finished.emit(result)
        except Exception as exc:
            logger.error("Replacement error: %s", exc)
            self.signals.error.emit(str(exc))


class _StatsBar(QWidget):
    """Statistics bar showing scan / modify / replace / error counts."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Surface")
        self.setVisible(False)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 10, 16, 10)
        row.setSpacing(24)
        self._scanned = self._make_stat()
        self._modified = self._make_stat()
        self._replacements = self._make_stat()
        self._errors = self._make_stat()
        for w in (self._scanned, self._modified, self._replacements, self._errors):
            row.addWidget(w)
        row.addStretch(1)

    def _make_stat(self) -> QLabel:
        lbl = QLabel()
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setStyleSheet("font-size: 13px; background: transparent;")
        return lbl

    def update_stats(self, result: ReplaceResult, *, dry_run: bool) -> None:
        self._scanned.setText(f"📂 {tr('rr.stat_scanned')}: <b>{result.files_scanned}</b>")
        self._modified.setText(f"✏️ {tr('rr.stat_modified')}: <b>{result.files_modified}</b>")
        self._replacements.setText(f"🔄 {tr('rr.stat_replacements')}: <b>{result.total_replacements}</b>")
        d = theme_manager.diff
        err_color = d.err_fg if result.errors else "inherit"
        self._errors.setText(f"<span style='color:{err_color}'>⚠️ {tr('rr.stat_errors')}: <b>{len(result.errors)}</b></span>")
        self.setVisible(True)

    def hide_stats(self) -> None:
        self.setVisible(False)


_MONO_FONT = QFont()
_MONO_FONT.setFamilies(["Menlo", "Consolas", "Courier New", "monospace"])
_MONO_FONT.setPointSize(11)


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class _DiffHunk(QFrame):
    """One changed line rendered as a −old / +new pair."""

    def __init__(self, lineno: int, old: str, new: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("DiffHunk")
        self.setStyleSheet("QFrame#DiffHunk { border: none; }")
        self._lineno = lineno
        self._old = old
        self._new = new
        vb = QVBoxLayout(self)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(0)
        self._lbl_del = self._make_line(lineno, old, removed=True)
        self._lbl_add = self._make_line(lineno, new, removed=False)
        vb.addWidget(self._lbl_del)
        vb.addWidget(self._lbl_add)
        theme_manager.changed.connect(self._on_theme_changed)

    def _make_line(self, lineno: int, text: str, *, removed: bool) -> QLabel:
        d = theme_manager.diff
        bg = d.del_bg if removed else d.add_bg
        fg = d.del_fg if removed else d.add_fg
        sym = "−" if removed else "+"
        lbl = QLabel()
        lbl.setFont(_MONO_FONT)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setWordWrap(False)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lbl.setStyleSheet(f"background: {bg}; padding: 1px 0px; border-radius: 0px;")
        lbl.setText(
            f"<span style='color:{d.line_no}; font-size:10px;'>{lineno:>5} </span>"
            f"<span style='color:{fg}; font-weight:700; padding:0 6px;'>{sym}</span>"
            f"<span style='color:{fg};'>{_esc(text)}</span>"
        )
        return lbl

    def _on_theme_changed(self, _tokens) -> None:
        d = theme_manager.diff
        for lbl, removed in ((self._lbl_del, True), (self._lbl_add, False)):
            bg = d.del_bg if removed else d.add_bg
            fg = d.del_fg if removed else d.add_fg
            sym = "−" if removed else "+"
            text = self._old if removed else self._new
            lbl.setStyleSheet(f"background: {bg}; padding: 1px 0px; border-radius: 0px;")
            lbl.setText(
                f"<span style='color:{d.line_no}; font-size:10px;'>"
                f"{self._lineno:>5} </span>"
                f"<span style='color:{fg}; font-weight:700; padding:0 6px;'>{sym}</span>"
                f"<span style='color:{fg};'>{_esc(text)}</span>"
            )


class _FileBlock(QFrame):
    """Collapsible block for one FileResult with diff hunks."""

    def __init__(self, file_result: FileResult, root_folder: Path, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Surface")
        self._is_error = bool(file_result.error)
        d = theme_manager.diff

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._header = QFrame()
        self._header.setObjectName("FileBlockHeader")
        self._header.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        hrow = QHBoxLayout(self._header)
        hrow.setContentsMargins(12, 8, 14, 8)
        hrow.setSpacing(8)

        self._chevron = QLabel("▾")
        try:
            display_path = str(file_result.path.relative_to(root_folder))
        except ValueError:
            display_path = str(file_result.path)

        path_color = d.err_fg if self._is_error else d.file_accent
        self._path_lbl = QLabel(f"<b style='color:{path_color};'>{_esc(display_path)}</b>")
        self._path_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._path_lbl.setFont(_MONO_FONT)
        self._path_lbl.setStyleSheet("background: transparent;")

        badge_text = tr("rr.diff_error") if self._is_error else tr("rr.diff_replacements", count=file_result.replacements)
        self._badge = QLabel(badge_text)

        hrow.addWidget(self._chevron)
        hrow.addWidget(self._path_lbl, 1)
        hrow.addWidget(self._badge)
        outer.addWidget(self._header)

        self._body = QWidget()
        self._body.setStyleSheet("background: transparent;")
        body_v = QVBoxLayout(self._body)
        body_v.setContentsMargins(0, 0, 0, 0)
        body_v.setSpacing(0)

        self._err_lbl: QLabel | None
        if self._is_error:
            self._err_lbl = QLabel(f"  {_esc(file_result.error)}")
            self._err_lbl.setFont(_MONO_FONT)
            self._err_lbl.setTextFormat(Qt.TextFormat.RichText)
            self._err_lbl.setWordWrap(True)
            body_v.addWidget(self._err_lbl)
        else:
            self._err_lbl = None
            for lineno, old, new in file_result.changed_lines:
                body_v.addWidget(_DiffHunk(lineno, old, new))

        outer.addWidget(self._body)
        self._header.installEventFilter(self)
        self._apply_theme()
        theme_manager.changed.connect(self._apply_theme)

    def _apply_theme(self, _tokens=None) -> None:
        d = theme_manager.diff
        path_color = d.err_fg if self._is_error else d.file_accent
        self._header.setStyleSheet(
            f"QFrame#FileBlockHeader {{  background: {path_color}22;  border-radius: 14px 14px 0 0;  border-bottom: 1px solid {path_color}44;}}"
        )
        self._chevron.setStyleSheet(f"color: {path_color}; font-size: 13px; background: transparent;")
        self._badge.setStyleSheet(f"color: {path_color}; font-size: 11px; font-weight: 600; background: transparent;")
        if self._err_lbl is not None:
            self._err_lbl.setStyleSheet(f"color: {d.err_fg}; background: {d.err_bg}; padding: 6px 14px;")

    def eventFilter(self, obj, event) -> bool:
        if obj is self._header and event.type() == QEvent.Type.MouseButtonPress:
            self._toggle()
            return True
        return super().eventFilter(obj, event)

    def _toggle(self) -> None:
        visible = not self._body.isVisible()
        self._body.setVisible(visible)
        self._chevron.setText("▾" if visible else "▸")


class _DiffView(QScrollArea):
    """Scrollable pane of _FileBlock items."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._root_folder: Path | None = None
        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._vb = QVBoxLayout(self._container)
        self._vb.setContentsMargins(0, 0, 0, 0)
        self._vb.setSpacing(8)

        self._empty = QLabel()
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("color: palette(mid); font-size: 13px;")
        self._vb.addWidget(self._empty)

        self._vb.addStretch(1)
        self.setWidget(self._container)

    def set_root(self, folder: Path) -> None:
        self._root_folder = folder

    def populate(self, result: ReplaceResult) -> None:
        self.clear()
        relevant = [r for r in result.file_results if r.changed or not r.success]
        if not relevant:
            self._empty.setVisible(True)
            return
        self._empty.setVisible(False)
        root = self._root_folder or Path(".")
        insert_at = self._vb.count() - 1
        for fr in relevant:
            self._vb.insertWidget(insert_at, _FileBlock(fr, root))
            insert_at += 1

    def clear(self) -> None:
        while self._vb.count() > 2:
            item = self._vb.takeAt(1)
            if item and (w := item.widget()):
                w.deleteLater()
        self._empty.setVisible(True)

    def retranslate(self) -> None:
        self._empty.setText(tr("rr.diff_empty"))


class ToolWidget(QWidget):
    """Main widget for the regex replace tool."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._worker: _ReplaceWorker | None = None
        self._build_ui()
        self._load_config()
        language_changed.connect(self._retranslate)
        self._retranslate()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background: palette(mid); }")

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        left_w = QWidget()
        left_w.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        lv = QVBoxLayout(left_w)
        lv.setContentsMargins(0, 0, 12, 0)
        lv.setSpacing(14)

        self._folder_picker = FolderPicker()
        self._pattern_field = InputField()
        self._replacement_field = InputField()
        self._ext_field = InputField()

        lv.addWidget(self._folder_picker)
        lv.addWidget(self._make_divider())
        lv.addWidget(self._pattern_field)
        lv.addWidget(self._replacement_field)
        lv.addWidget(self._ext_field)
        lv.addWidget(self._make_divider())

        opts_frame = QFrame()
        opts_frame.setObjectName("Surface")
        opts_v = QVBoxLayout(opts_frame)
        opts_v.setContentsMargins(14, 12, 14, 12)
        opts_v.setSpacing(10)
        self._opt_label = SectionLabel()
        self._chk_ignore_case = QCheckBox()
        self._chk_backup = QCheckBox()
        opts_v.addWidget(self._opt_label)
        for chk in (self._chk_ignore_case, self._chk_backup):
            chk.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            opts_v.addWidget(chk)
        lv.addWidget(opts_frame)
        lv.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._preview_btn = QPushButton()
        self._preview_btn.setObjectName("MenuBtn")
        self._preview_btn.setMinimumHeight(40)
        self._preview_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._preview_btn.clicked.connect(self._on_preview)
        self._run_btn = QPushButton()
        self._run_btn.setObjectName("RunBtn")
        self._run_btn.setMinimumHeight(40)
        self._run_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._run_btn.clicked.connect(self._on_run)
        self._clear_btn = QPushButton()
        self._clear_btn.setObjectName("MenuBtn")
        self._clear_btn.setMinimumHeight(40)
        self._clear_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._clear_btn.clicked.connect(self._on_clear)
        btn_row.addWidget(self._preview_btn, 1)
        btn_row.addWidget(self._run_btn, 2)
        btn_row.addWidget(self._clear_btn, 1)
        lv.addLayout(btn_row)

        left_scroll.setWidget(left_w)

        right_w = QWidget()
        rv = QVBoxLayout(right_w)
        rv.setContentsMargins(12, 0, 0, 0)
        rv.setSpacing(10)

        self._stats_bar = _StatsBar()
        rv.addWidget(self._stats_bar)

        diff_frame = QFrame()
        diff_frame.setObjectName("Surface")
        diff_frame_v = QVBoxLayout(diff_frame)
        diff_frame_v.setContentsMargins(14, 12, 14, 12)
        diff_frame_v.setSpacing(6)

        self._diff_section_label = SectionLabel()
        diff_frame_v.addWidget(self._diff_section_label)

        self._diff_view = _DiffView()
        diff_frame_v.addWidget(self._diff_view, 1)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedHeight(4)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        diff_frame_v.addWidget(self._progress)

        rv.addWidget(diff_frame, 1)

        splitter.addWidget(left_scroll)
        splitter.addWidget(right_w)
        splitter.setSizes([360, 640])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, 1)

    def _load_config(self) -> None:
        self._chk_ignore_case.setChecked(config_manager.get_app("regex_replacer.ignore_case", False))
        self._chk_backup.setChecked(config_manager.get_app("regex_replacer.backup", False))

    def _save_config(self) -> None:
        config_manager.set_app("regex_replacer.ignore_case", self._chk_ignore_case.isChecked())
        config_manager.set_app("regex_replacer.backup", self._chk_backup.isChecked())
        config_manager.save_app()

    def _make_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: palette(mid);")
        line.setFixedHeight(1)
        return line

    def _retranslate(self) -> None:
        self._folder_picker.label.setText(tr("rr.folder_label").upper())
        self._folder_picker.browse_btn.setText(tr("rr.browse_btn"))
        self._pattern_field.label.setText(tr("rr.pattern_label").upper())
        self._pattern_field.set_placeholder(tr("rr.pattern_placeholder"))
        self._replacement_field.label.setText(tr("rr.replacement_label").upper())
        self._replacement_field.set_placeholder(tr("rr.replacement_placeholder"))
        self._ext_field.label.setText(tr("rr.ext_label").upper())
        self._ext_field.set_placeholder(tr("rr.ext_placeholder"))
        self._opt_label.setText(tr("rr.options_label").upper())
        self._chk_ignore_case.setText(tr("rr.opt_ignore_case"))
        self._chk_backup.setText(tr("rr.opt_backup"))
        self._preview_btn.setText(tr("rr.preview_btn"))
        self._run_btn.setText(tr("rr.run_btn"))
        self._clear_btn.setText(tr("rr.clear_btn"))
        self._diff_section_label.setText(tr("rr.diff_label").upper())
        self._diff_view.retranslate()

    def _start_worker(self, *, dry_run: bool) -> None:
        folder = self._folder_picker.path()
        pattern = self._pattern_field.text().strip()
        replacement = self._replacement_field.text()
        ext_raw = self._ext_field.text().strip()
        extensions = [e.strip() for e in ext_raw.split(",") if e.strip()] or None

        if not folder or not pattern:
            return

        self._save_config()

        self._run_btn.setEnabled(False)
        self._preview_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._stats_bar.hide_stats()
        self._diff_view.clear()
        self._diff_view.set_root(folder)

        self._worker = _ReplaceWorker(
            folder,
            pattern,
            replacement,
            extensions,
            ignore_case=self._chk_ignore_case.isChecked(),
            dry_run=dry_run,
            backup=self._chk_backup.isChecked(),
        )
        self._worker.signals.finished.connect(self._on_finished)
        self._worker.signals.error.connect(self._on_error)
        self._worker.start()

    def _on_run(self) -> None:
        self._start_worker(dry_run=False)

    def _on_preview(self) -> None:
        self._start_worker(dry_run=True)

    def _on_clear(self) -> None:
        self._diff_view.clear()
        self._stats_bar.hide_stats()

    def _on_finished(self, result: ReplaceResult) -> None:
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._preview_btn.setEnabled(True)
        self._stats_bar.update_stats(result, dry_run=self._worker.dry_run if self._worker else False)
        self._diff_view.populate(result)

    def _on_error(self, message: str) -> None:
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._preview_btn.setEnabled(True)
        logger.error("Tool error: %s", message)
