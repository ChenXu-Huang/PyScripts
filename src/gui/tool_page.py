"""Lazy-loaded tool page wrapper with placeholder fallback."""

import importlib
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt

from .i18n import tr, language_changed


class ToolPage(QWidget):
    """Wraps a tool widget loaded lazily via importlib.

    If the tool module is not found, displays a "coming soon" placeholder.
    """

    def __init__(self, tool: dict, parent=None) -> None:
        super().__init__(parent)
        self.tool = tool
        self.setObjectName("ToolPageWrapper")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)

        try:
            mod = importlib.import_module(tool["module"], __package__)
            widget = mod.ToolWidget(self)
            layout.addWidget(widget)
            self._has_placeholder = False
        except ModuleNotFoundError:
            ph = self._make_placeholder(tool)
            layout.addWidget(ph)
            self._has_placeholder = True
            language_changed.connect(self._retranslate_placeholder)

    def _make_placeholder(self, tool) -> QFrame:
        ph = QFrame()
        ph.setObjectName("Surface")
        vb = QVBoxLayout(ph)
        vb.setContentsMargins(40, 40, 40, 40)

        self._ph_icon = QLabel(tool["icon"])
        self._ph_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ph_icon.setStyleSheet(
            f"font-size:56px; color:{tool['color']}; background:transparent;"
        )
        self._ph_title = QLabel()
        self._ph_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ph_title.setStyleSheet("font-size:20px; font-weight:600;")
        self._ph_hint = QLabel()
        self._ph_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ph_hint.setTextFormat(Qt.TextFormat.RichText)
        self._ph_hint.setStyleSheet("font-size:13px;")

        vb.addStretch(1)
        vb.addWidget(self._ph_icon)
        vb.addSpacing(12)
        vb.addWidget(self._ph_title)
        vb.addSpacing(8)
        vb.addWidget(self._ph_hint)
        vb.addStretch(1)

        self._retranslate_placeholder()
        return ph

    def _retranslate_placeholder(self) -> None:
        tid = self.tool["id"]
        path = self.tool["module"].replace(".", "/")
        self._ph_title.setText(tr("tool.coming_soon", name=tr(f"tool.{tid}.name")))
        self._ph_hint.setText(tr("tool.hint", path=path))
