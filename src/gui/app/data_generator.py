"""Random Data Generator tool — GUI widget."""

__all__ = ["ToolWidget"]

import threading
import numpy as np
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QFrame, QScrollArea, QProgressBar,
    QSplitter, QSizePolicy, QFileDialog, QLineEdit,
)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QCursor, QPixmap

from ..i18n import tr, language_changed
from ..widgets import SectionLabel, InputField
from ... import ROOT_DIR
from ...logger import get_logger
from ...config import config_manager
from ...utils.data_generator import generate_data
from ...utils.table_grapher import table2graph

logger = get_logger(__name__)

_DISTRIBUTIONS = [
    ("normal", "dg.dist_normal"),
    ("uniform", "dg.dist_uniform"),
]


class _WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)


class _DataWorker(threading.Thread):
    def __init__(
        self,
        mean: float,
        width: float,
        n: int,
        variance: float,
        distribution: str,
        decimals: int | None,
        seed: int | None,
        csv_path: str,
        dimension: int = 1,
        slope: float = 1.0,
        intercept: float = 0.0,
        r_squared: float = 0.95,
        decimals_y: int | None = None,
    ) -> None:
        super().__init__(daemon=True)
        self.mean = mean
        self.width = width
        self.n = n
        self.variance = variance
        self.distribution = distribution
        self.decimals = decimals
        self.seed = seed
        self.csv_path = csv_path
        self.dimension = dimension
        self.slope = slope
        self.intercept = intercept
        self.r_squared = r_squared
        self.decimals_y = decimals_y
        self.signals = _WorkerSignals()

    def run(self) -> None:
        try:
            rng = np.random.default_rng(self.seed)
            kwargs = {}
            if self.dimension == 2:
                kwargs = dict(
                    slope=self.slope,
                    intercept=self.intercept,
                    r_squared=self.r_squared,
                    decimals_y=self.decimals_y,
                )
            data = generate_data(
                n=self.n,
                mean=self.mean,
                width=self.width,
                variance=self.variance,
                distribution=self.distribution,
                decimals=self.decimals,
                rng=rng,
                csv_path=self.csv_path,
                dimension=self.dimension,
                **kwargs,
            )
            image_paths = table2graph(Path(self.csv_path), mode="linear", plot_together=True)
            self.signals.finished.emit((data, image_paths))
        except Exception as exc:
            logger.error("Data generation error: %s", exc)
            self.signals.error.emit(str(exc))


class _StatsBar(QWidget):
    """Statistics bar showing data info."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Surface")
        self.setVisible(False)
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(16, 10, 16, 10)
        self._row.setSpacing(24)

    @staticmethod
    def _make_stat(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setStyleSheet("font-size: 13px; background: transparent;")
        return lbl

    def _clear(self) -> None:
        while self._row.count():
            item = self._row.takeAt(0)
            if item and (w := item.widget()):
                w.deleteLater()

    def update_stats(self, data: np.ndarray) -> None:
        self._clear()
        labels = [self._make_stat(f"📊 {tr('dg.stat_n')}: <b>{len(data)}</b>")]
        if data.ndim == 2:
            labels.append(self._make_stat(f"X μ: <b>{data[:, 0].mean():.4f}</b>  σ: <b>{data[:, 0].std(ddof=0):.4f}</b>"))
            labels.append(self._make_stat(f"Y μ: <b>{data[:, 1].mean():.4f}</b>  σ: <b>{data[:, 1].std(ddof=0):.4f}</b>"))
        else:
            labels.append(self._make_stat(f"μ {tr('dg.stat_mean')}: <b>{data.mean():.4f}</b>"))
            labels.append(self._make_stat(f"σ {tr('dg.stat_std')}: <b>{data.std(ddof=0):.4f}</b>"))
            labels.append(self._make_stat(f"▼ {tr('dg.stat_min')}: <b>{data.min():.4f}</b>"))
            labels.append(self._make_stat(f"▲ {tr('dg.stat_max')}: <b>{data.max():.4f}</b>"))
        for w in labels:
            self._row.addWidget(w)
        self._row.addStretch(1)
        self.setVisible(True)

    def hide_stats(self) -> None:
        self._clear()
        self.setVisible(False)


class ToolWidget(QWidget):
    """Main widget for the random data generator tool."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._worker: _DataWorker | None = None
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

        self._n_field = InputField()
        self._mean_field = InputField()
        self._width_field = InputField()
        self._std_field = InputField()
        self._decimals_field = InputField()

        lv.addWidget(self._n_field)
        lv.addWidget(self._mean_field)
        lv.addWidget(self._width_field)
        lv.addWidget(self._std_field)
        lv.addWidget(self._decimals_field)
        lv.addWidget(self._make_divider())

        self._dist_label = SectionLabel()
        self._dist_combo = QComboBox()
        self._dist_combo.setMinimumHeight(36)
        for _key, label_key in _DISTRIBUTIONS:
            self._dist_combo.addItem(tr(label_key), _key)
        lv.addWidget(self._dist_label)
        lv.addWidget(self._dist_combo)

        self._dim2_checkbox = QCheckBox()
        self._dim2_checkbox.setMinimumHeight(36)
        self._dim2_checkbox.toggled.connect(self._on_dim2_toggled)
        lv.addWidget(self._dim2_checkbox)

        self._slope_field = InputField()
        self._slope_field.setVisible(False)
        self._intercept_field = InputField()
        self._intercept_field.setVisible(False)
        self._r_squared_field = InputField()
        self._r_squared_field.setVisible(False)
        self._decimals_y_field = InputField()
        self._decimals_y_field.setVisible(False)
        lv.addWidget(self._slope_field)
        lv.addWidget(self._intercept_field)
        lv.addWidget(self._r_squared_field)
        lv.addWidget(self._decimals_y_field)

        self._seed_field = InputField()
        lv.addWidget(self._seed_field)

        self._export_label = SectionLabel()
        self._export_row = QHBoxLayout()
        self._export_row.setSpacing(8)
        self._export_edit = QLineEdit()
        self._export_edit.setObjectName("InputEdit")
        self._export_edit.setMinimumHeight(36)
        self._export_edit.setReadOnly(True)
        self._export_btn = QPushButton()
        self._export_btn.setObjectName("MenuBtn")
        self._export_btn.setFixedHeight(36)
        self._export_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._export_btn.clicked.connect(self._browse_export)
        self._export_row.addWidget(self._export_edit, 1)
        self._export_row.addWidget(self._export_btn)
        lv.addWidget(self._export_label)
        lv.addLayout(self._export_row)

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

        self._image_scroll = QScrollArea()
        self._image_scroll.setWidgetResizable(True)
        self._image_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._image_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("background: transparent;")
        self._image_scroll.setWidget(self._image_label)
        result_v.addWidget(self._image_scroll, 1)

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

    def _browse_export(self) -> None:
        start = self._export_edit.text() or str(Path.home())
        path, _ = QFileDialog.getSaveFileName(self, "", start, "CSV (*.csv)")
        if path:
            self._export_edit.setText(path)

    def _make_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: palette(mid);")
        line.setFixedHeight(1)
        return line

    def _load_config(self) -> None:
        dist = config_manager.get_app("data_generator.distribution", "normal")
        idx = self._dist_combo.findData(dist)
        if idx >= 0:
            self._dist_combo.setCurrentIndex(idx)

    def _save_config(self) -> None:
        config_manager.set_app("data_generator.distribution", self._dist_combo.currentData())
        config_manager.save_app()

    def _retranslate(self) -> None:
        self._n_field.label.setText(tr("dg.n_label"))
        self._mean_field.label.setText(tr("dg.mean_label"))
        self._width_field.label.setText(tr("dg.width_label"))
        self._std_field.label.setText(tr("dg.std_label"))
        self._decimals_field.label.setText(tr("dg.decimals_label"))
        self._dist_label.setText(tr("dg.dist_label"))
        for i in range(self._dist_combo.count()):
            key = self._dist_combo.itemData(i)
            label_key = next(lk for k, lk in _DISTRIBUTIONS if k == key)
            self._dist_combo.setItemText(i, tr(label_key))
        self._dim2_checkbox.setText(tr("dg.dim2_label"))
        self._slope_field.label.setText(tr("dg.slope_label"))
        self._intercept_field.label.setText(tr("dg.intercept_label"))
        self._r_squared_field.label.setText(tr("dg.r_squared_label"))
        self._decimals_y_field.label.setText(tr("dg.decimals_y_label"))
        self._seed_field.label.setText(tr("dg.seed_label"))
        self._seed_field.set_placeholder(tr("dg.seed_placeholder"))
        self._export_label.setText(tr("dg.export_label"))
        self._export_btn.setText(tr("dg.export_browse"))
        self._run_btn.setText(tr("dg.run_btn"))
        self._clear_btn.setText(tr("dg.clear_btn"))
        self._result_label.setText(tr("dg.stat_title"))

    def _start_worker(self) -> None:
        try:
            n = int(self._n_field.text().strip())
            mean = float(self._mean_field.text().strip())
            width = float(self._width_field.text().strip())
            std = float(self._std_field.text().strip())
            decimals_text = self._decimals_field.text().strip()
            decimals = int(decimals_text) if decimals_text else 0
        except (ValueError, TypeError):
            return

        seed_text = self._seed_field.text().strip()
        seed = int(seed_text) if seed_text else None

        csv_path = self._export_edit.text().strip() or str(ROOT_DIR / "data/random_data.csv")
        variance = std * std
        distribution = self._dist_combo.currentData()

        dim2 = self._dim2_checkbox.isChecked()
        try:
            slope = float(self._slope_field.text().strip()) if self._slope_field.text().strip() else 1.0
            intercept = float(self._intercept_field.text().strip()) if self._intercept_field.text().strip() else 0.0
            r_squared = float(self._r_squared_field.text().strip()) if self._r_squared_field.text().strip() else 0.95
        except (ValueError, TypeError):
            return
        decimals_y_text = self._decimals_y_field.text().strip()
        decimals_y = int(decimals_y_text) if decimals_y_text else None

        self._save_config()

        self._run_btn.setEnabled(False)
        self._clear_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._stats_bar.hide_stats()
        self._image_label.clear()

        self._worker = _DataWorker(
            mean=mean,
            width=width,
            n=n,
            variance=variance,
            distribution=distribution,
            decimals=decimals,
            seed=seed,
            csv_path=csv_path,
            dimension=2 if dim2 else 1,
            slope=slope,
            intercept=intercept,
            r_squared=r_squared,
            decimals_y=decimals_y,
        )
        self._worker.signals.finished.connect(self._on_finished)
        self._worker.signals.error.connect(self._on_error)
        self._worker.start()

    def _on_dim2_toggled(self, checked: bool) -> None:
        self._slope_field.setVisible(checked)
        self._intercept_field.setVisible(checked)
        self._r_squared_field.setVisible(checked)
        self._decimals_y_field.setVisible(checked)

    def _on_run(self) -> None:
        self._start_worker()

    def _on_clear(self) -> None:
        self._image_label.clear()
        self._stats_bar.hide_stats()

    def _on_finished(self, payload: tuple[np.ndarray, list[Path]]) -> None:
        data, image_paths = payload
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._clear_btn.setEnabled(True)
        self._stats_bar.update_stats(data)

        if image_paths:
            pixmap = QPixmap(str(image_paths[0]))
            if not pixmap.isNull():
                max_w = min(pixmap.width(), 700)
                max_h = min(pixmap.height(), 500)
                self._image_label.setPixmap(
                    pixmap.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )

    def _on_error(self, message: str) -> None:
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._clear_btn.setEnabled(True)
        logger.error("Tool error: %s", message)
