"""Shared reusable form widgets for tool pages."""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor


class SectionLabel(QLabel):
    """Section heading label (all-caps, small, bold)."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("SectionLabel")
        self.setStyleSheet(
            "#SectionLabel { font-size: 12px; font-weight: 600;"
            " letter-spacing: 0.5px; background: transparent; }"
        )


class InputField(QWidget):
    """A labeled text input field."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        vb = QVBoxLayout(self)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(4)
        self._label = SectionLabel(parent=self)
        self._edit = QLineEdit(self)
        self._edit.setObjectName("InputEdit")
        self._edit.setMinimumHeight(36)
        vb.addWidget(self._label)
        vb.addWidget(self._edit)

    @property
    def label(self) -> SectionLabel:
        return self._label

    def text(self) -> str:
        return self._edit.text()

    def set_placeholder(self, text: str) -> None:
        self._edit.setPlaceholderText(text)


class FolderPicker(QWidget):
    """Folder picker with read-only path display and browse button."""

    path_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        vb = QVBoxLayout(self)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(4)
        self._label = SectionLabel(parent=self)
        row = QHBoxLayout()
        row.setSpacing(8)
        self._edit = QLineEdit(self)
        self._edit.setObjectName("InputEdit")
        self._edit.setMinimumHeight(36)
        self._edit.setReadOnly(True)
        self._btn = QPushButton()
        self._btn.setObjectName("MenuBtn")
        self._btn.setFixedHeight(36)
        self._btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn.clicked.connect(self._browse)
        row.addWidget(self._edit, 1)
        row.addWidget(self._btn)
        vb.addWidget(self._label)
        vb.addLayout(row)

    def _browse(self) -> None:
        start = self._edit.text() or str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "", start)
        if folder:
            self._edit.setText(folder)
            self.path_changed.emit(folder)

    @property
    def label(self) -> SectionLabel:
        return self._label

    @property
    def browse_btn(self) -> QPushButton:
        return self._btn

    def path(self) -> Path | None:
        t = self._edit.text().strip()
        return Path(t) if t else None


class FilePicker(QWidget):
    """File picker with read-only path display and browse button."""

    path_changed = Signal(str)

    def __init__(self, parent=None, *, file_filter: str = "") -> None:
        super().__init__(parent)
        self._file_filter = file_filter
        vb = QVBoxLayout(self)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(4)
        self._label = SectionLabel(parent=self)
        row = QHBoxLayout()
        row.setSpacing(8)
        self._edit = QLineEdit(self)
        self._edit.setObjectName("InputEdit")
        self._edit.setMinimumHeight(36)
        self._edit.setReadOnly(True)
        self._btn = QPushButton()
        self._btn.setObjectName("MenuBtn")
        self._btn.setFixedHeight(36)
        self._btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn.clicked.connect(self._browse)
        row.addWidget(self._edit, 1)
        row.addWidget(self._btn)
        vb.addWidget(self._label)
        vb.addLayout(row)

    def _browse(self) -> None:
        start = self._edit.text() or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(self, "", start, self._file_filter)
        if path:
            self._edit.setText(path)
            self.path_changed.emit(path)

    @property
    def label(self) -> SectionLabel:
        return self._label

    @property
    def browse_btn(self) -> QPushButton:
        return self._btn

    def path(self) -> Path | None:
        t = self._edit.text().strip()
        return Path(t) if t else None
