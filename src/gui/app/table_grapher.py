"""Table Grapher tool — GUI widget."""

__all__ = ["ToolWidget"]

import threading
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QFrame, QScrollArea, QProgressBar,
    QSplitter, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QEvent, QObject
from PySide6.QtGui import QCursor, QPixmap, QFont

from ..i18n import tr, language_changed
from ..theme import theme_manager
from ..widgets import SectionLabel, FilePicker
from ...logger import get_logger
from ...config import config_manager
from ...utils.table_grapher import table2graph

logger = get_logger(__name__)

_MODES = [
    ("direct", "tg.mode_direct"),
    ("smooth", "tg.mode_smooth"),
    ("linear", "tg.mode_linear"),
]


class _WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)


class _TableWorker(threading.Thread):
    def __init__(
        self,
        data_path: Path,
        *,
        mode: str,
        plot_together: bool,
    ) -> None:
        super().__init__(daemon=True)
        self.data_path = data_path
        self.mode = mode
        self.plot_together = plot_together
        self.signals = _WorkerSignals()

    def run(self) -> None:
        try:
            paths = table2graph(
                self.data_path,
                mode=self.mode,
                plot_together=self.plot_together,
            )
            self.signals.finished.emit(paths)
        except Exception as exc:
            logger.error("Plotting error: %s", exc)
            self.signals.error.emit(str(exc))


_MONO_FONT = QFont()
_MONO_FONT.setFamilies(["Menlo", "Consolas", "Courier New", "monospace"])
_MONO_FONT.setPointSize(11)


class _ImageBlock(QFrame):
    """Collapsible block showing one generated PNG with a thumbnail."""

    def __init__(self, image_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Surface")
        self._path = image_path
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
        self._name_lbl = QLabel(f"<b style='color:{d.file_accent};'>{image_path.name}</b>")
        self._name_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._name_lbl.setFont(_MONO_FONT)
        self._name_lbl.setStyleSheet("background: transparent;")

        hrow.addWidget(self._chevron)
        hrow.addWidget(self._name_lbl, 1)
        outer.addWidget(self._header)

        self._body = QWidget()
        self._body.setStyleSheet("background: transparent;")
        body_v = QVBoxLayout(self._body)
        body_v.setContentsMargins(12, 8, 12, 12)
        body_v.setSpacing(0)

        self._image_lbl = QLabel()
        self._image_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._load_thumbnail()
        body_v.addWidget(self._image_lbl)

        outer.addWidget(self._body)
        self._header.installEventFilter(self)
        self._apply_theme()
        theme_manager.changed.connect(self._apply_theme)

    def _load_thumbnail(self) -> None:
        pixmap = QPixmap(str(self._path))
        if not pixmap.isNull():
            max_w = min(pixmap.width(), 600)
            max_h = min(pixmap.height(), 400)
            self._image_lbl.setPixmap(pixmap.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _apply_theme(self, _tokens=None) -> None:
        d = theme_manager.diff
        self._header.setStyleSheet(
            f"QFrame#FileBlockHeader {{  background: {d.file_accent}22;"
            f"  border-radius: 14px 14px 0 0;"
            f"  border-bottom: 1px solid {d.file_accent}44;}}"
        )
        self._chevron.setStyleSheet(f"color: {d.file_accent}; font-size: 13px; background: transparent;")

    def eventFilter(self, obj, event) -> bool:
        if obj is self._header and event.type() == QEvent.Type.MouseButtonPress:
            self._toggle()
            return True
        return super().eventFilter(obj, event)

    def _toggle(self) -> None:
        visible = not self._body.isVisible()
        self._body.setVisible(visible)
        self._chevron.setText("▾" if visible else "▸")


class _ResultView(QScrollArea):
    """Scrollable pane of _ImageBlock items."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

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

    def populate(self, paths: list[Path]) -> None:
        self.clear()
        if not paths:
            self._empty.setVisible(True)
            return
        self._empty.setVisible(False)
        insert_at = self._vb.count() - 1
        for p in paths:
            self._vb.insertWidget(insert_at, _ImageBlock(p))
            insert_at += 1

    def clear(self) -> None:
        while self._vb.count() > 2:
            item = self._vb.takeAt(1)
            if item and (w := item.widget()):
                w.deleteLater()
        self._empty.setVisible(True)

    def retranslate(self) -> None:
        self._empty.setText(tr("tg.result_empty"))


class _StatsBar(QWidget):
    """Statistics bar showing data info and image count."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Surface")
        self.setVisible(False)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 10, 16, 10)
        row.setSpacing(24)
        self._data_file = self._make_stat()
        self._variables = self._make_stat()
        self._images = self._make_stat()
        for w in (self._data_file, self._variables, self._images):
            row.addWidget(w)
        row.addStretch(1)

    def _make_stat(self) -> QLabel:
        lbl = QLabel()
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setStyleSheet("font-size: 13px; background: transparent;")
        return lbl

    def update_stats(self, data_name: str, var_count: int, image_count: int) -> None:
        self._data_file.setText(f"📂 {tr('tg.stat_file')}: <b>{data_name}</b>")
        self._variables.setText(f"📊 {tr('tg.stat_vars')}: <b>{var_count}</b>")
        self._images.setText(f"🖼️ {tr('tg.stat_images')}: <b>{image_count}</b>")
        self.setVisible(True)

    def hide_stats(self) -> None:
        self.setVisible(False)


class ToolWidget(QWidget):
    """Main widget for the table grapher tool."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._worker: _TableWorker | None = None
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

        self._file_picker = FilePicker(file_filter="CSV (*.csv)")

        lv.addWidget(self._file_picker)
        lv.addWidget(self._make_divider())

        self._mode_label = SectionLabel()
        self._mode_combo = QComboBox()
        self._mode_combo.setMinimumHeight(36)
        for _key, label_key in _MODES:
            self._mode_combo.addItem(tr(label_key), _key)
        lv.addWidget(self._mode_label)
        lv.addWidget(self._mode_combo)

        opts_frame = QFrame()
        opts_frame.setObjectName("Surface")
        opts_v = QVBoxLayout(opts_frame)
        opts_v.setContentsMargins(14, 12, 14, 12)
        opts_v.setSpacing(10)
        self._opt_label = SectionLabel()
        self._chk_plot_together = QCheckBox()
        self._chk_plot_together.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        opts_v.addWidget(self._opt_label)
        opts_v.addWidget(self._chk_plot_together)
        lv.addWidget(opts_frame)
        lv.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
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

        result_frame = QFrame()
        result_frame.setObjectName("Surface")
        result_v = QVBoxLayout(result_frame)
        result_v.setContentsMargins(14, 12, 14, 12)
        result_v.setSpacing(6)

        self._result_label = SectionLabel()
        result_v.addWidget(self._result_label)

        self._result_view = _ResultView()
        result_v.addWidget(self._result_view, 1)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedHeight(4)
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        result_v.addWidget(self._progress)

        rv.addWidget(result_frame, 1)

        splitter.addWidget(left_scroll)
        splitter.addWidget(right_w)
        splitter.setSizes([360, 640])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, 1)

    def _load_config(self) -> None:
        mode = config_manager.get_app("table_grapher.mode", "smooth")
        idx = self._mode_combo.findData(mode)
        if idx >= 0:
            self._mode_combo.setCurrentIndex(idx)
        self._chk_plot_together.setChecked(config_manager.get_app("table_grapher.plot_together", False))

    def _save_config(self) -> None:
        config_manager.set_app("table_grapher.mode", self._mode_combo.currentData())
        config_manager.set_app("table_grapher.plot_together", self._chk_plot_together.isChecked())
        config_manager.save_app()

    def _make_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: palette(mid);")
        line.setFixedHeight(1)
        return line

    def _retranslate(self) -> None:
        self._file_picker.label.setText(tr("tg.file_label").upper())
        self._file_picker.browse_btn.setText(tr("tg.browse_btn"))
        self._mode_label.setText(tr("tg.mode_label").upper())
        for i in range(self._mode_combo.count()):
            key = self._mode_combo.itemData(i)
            label_key = next(lk for k, lk in _MODES if k == key)
            self._mode_combo.setItemText(i, tr(label_key))
        self._opt_label.setText(tr("tg.options_label").upper())
        self._chk_plot_together.setText(tr("tg.opt_plot_together"))
        self._run_btn.setText(tr("tg.run_btn"))
        self._clear_btn.setText(tr("tg.clear_btn"))
        self._result_label.setText(tr("tg.result_label").upper())
        self._result_view.retranslate()

    def _start_worker(self) -> None:
        data_path = self._file_picker.path()
        if not data_path or not data_path.exists():
            return

        self._save_config()

        self._run_btn.setEnabled(False)
        self._clear_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._stats_bar.hide_stats()
        self._result_view.clear()

        self._worker = _TableWorker(
            data_path,
            mode=self._mode_combo.currentData(),
            plot_together=self._chk_plot_together.isChecked(),
        )
        self._worker.signals.finished.connect(self._on_finished)
        self._worker.signals.error.connect(self._on_error)
        self._worker.start()

    def _on_run(self) -> None:
        self._start_worker()

    def _on_clear(self) -> None:
        self._result_view.clear()
        self._stats_bar.hide_stats()

    def _on_finished(self, paths: list[Path]) -> None:
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._clear_btn.setEnabled(True)
        data_path = self._file_picker.path()
        self._stats_bar.update_stats(
            data_path.name if data_path else "?",
            max(len(paths), 1),
            len(paths),
        )
        self._result_view.populate(paths)

    def _on_error(self, message: str) -> None:
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._clear_btn.setEnabled(True)
        logger.error("Tool error: %s", message)
