"""Home page showing tool cards in a responsive grid."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QScrollArea,
    QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtSvgWidgets import QSvgWidget

from . import ASSETS_DIR
from .i18n import tr, language_changed
from .app import GUI_TOOLS


def _svg_widget(file: str, size: int) -> QSvgWidget:
    widget = QSvgWidget(file)
    widget.setFixedSize(size, size)
    return widget


class ToolCard(QFrame):
    """Clickable card representing a tool on the home page."""

    clicked = Signal(dict)

    def __init__(self, tool: dict, parent=None) -> None:
        super().__init__(parent)
        self.tool = tool
        self.setObjectName("ToolCard")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(90)
        self._build()
        language_changed.connect(self._retranslate)

    def _build(self) -> None:
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(14)

        icon_lbl = QLabel(self.tool["icon"])
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            f"background:{self.tool['color']}22; color:{self.tool['color']};"
            "border-radius:14px; font-size:24px;"
            "min-width:52px; max-width:52px; min-height:52px; max-height:52px;"
        )
        row.addWidget(icon_lbl)

        col = QVBoxLayout()
        col.setSpacing(3)
        self._title = QLabel()
        self._title.setObjectName("CardTitle")
        self._desc = QLabel()
        self._desc.setObjectName("CardDesc")
        self._desc.setWordWrap(True)
        col.addWidget(self._title)
        col.addWidget(self._desc)
        row.addLayout(col, 1)

        self._arrow = _svg_widget(str(ASSETS_DIR / "chevron-right.svg"), 18)
        row.addWidget(self._arrow)

        self._retranslate()

    def _retranslate(self) -> None:
        tid = self.tool["id"]
        self._title.setText(tr(f"tool.{tid}.name"))
        self._desc.setText(tr(f"tool.{tid}.desc"))

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tool)
        super().mousePressEvent(e)


class HomePage(QWidget):
    """Landing page with a grid of ToolCard widgets."""

    tool_opened = Signal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build()
        language_changed.connect(self._retranslate)

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(40, 36, 40, 36)
        outer.setSpacing(0)

        self._title = QLabel()
        self._title.setObjectName("HomeTitle")
        self._sub = QLabel()
        self._sub.setObjectName("HomeSubtitle")
        outer.addWidget(self._title)
        outer.addSpacing(6)
        outer.addWidget(self._sub)
        outer.addSpacing(28)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 8, 0)

        for i, tool in enumerate(GUI_TOOLS):
            card = ToolCard(tool)
            card.clicked.connect(self.tool_opened)
            grid.addWidget(card, i // 2, i % 2)

        grid.setRowStretch((len(GUI_TOOLS) + 1) // 2, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        scroll.setWidget(grid_w)
        outer.addWidget(scroll, 1)

        self._retranslate()

    def _retranslate(self) -> None:
        self._title.setText(tr("home.title"))
        self._sub.setText(tr("home.subtitle"))
