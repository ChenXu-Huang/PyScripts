"""Tab bar with closable tabs for tool navigation."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from .i18n import tr


class TabItem:
    """Data holder for a single tab."""

    def __init__(self, tool_id: str, name: str, widget) -> None:
        self.tool_id = tool_id
        self.name = name
        self.widget = widget
        self.btn: QPushButton | None = None
        self.close_btn: QPushButton | None = None
        self.wrapper: QWidget | None = None


class TabBar(QWidget):
    """Horizontal tab bar with close buttons, similar to browser tabs."""

    tab_changed = Signal(int)
    tab_closed = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TabBar")
        self._tabs: list[TabItem] = []
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(4, 4, 4, 4)
        self._row.setSpacing(4)
        self._row.addStretch(1)

    def add_tab(self, item: TabItem) -> None:
        btn = QPushButton(item.name)
        btn.setObjectName("TabBtn")
        btn.setCheckable(True)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setMaximumWidth(160)

        close_btn = QPushButton(tr("tab.close"))
        close_btn.setObjectName("CloseTabBtn")
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setFlat(True)

        wrapper = QWidget()
        wl = QHBoxLayout(wrapper)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(2)
        wl.addWidget(btn)
        wl.addWidget(close_btn)

        idx = len(self._tabs)
        item.btn, item.close_btn, item.wrapper = btn, close_btn, wrapper
        self._tabs.append(item)
        self._row.insertWidget(self._row.count() - 1, wrapper)

        btn.clicked.connect(lambda _, i=idx: self.tab_changed.emit(i))
        close_btn.clicked.connect(lambda _, i=idx: self.tab_closed.emit(i))
        self.set_active(idx)

    def set_active(self, idx: int) -> None:
        for i, t in enumerate(self._tabs):
            if t.btn:
                t.btn.setChecked(i == idx)

    def remove_tab(self, idx: int) -> None:
        if not (0 <= idx < len(self._tabs)):
            return
        item = self._tabs.pop(idx)
        self._row.removeWidget(item.wrapper)
        item.wrapper.deleteLater()
        for i, t in enumerate(self._tabs):
            try:
                t.btn.clicked.disconnect()
                t.close_btn.clicked.disconnect()
            except Exception:
                pass
            t.btn.clicked.connect(lambda _, ii=i: self.tab_changed.emit(ii))
            t.close_btn.clicked.connect(lambda _, ii=i: self.tab_closed.emit(ii))

    def count(self) -> int:
        return len(self._tabs)

    def tab_at(self, idx: int) -> TabItem:
        return self._tabs[idx]
