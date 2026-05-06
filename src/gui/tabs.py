"""Tab bar with closable tabs for tool navigation."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor

from .i18n import tr


class TabItem:
    """Data holder for a single tab."""

    def __init__(
        self,
        tool_id: str,
        name: str,
        widget: QWidget,
        btn: QPushButton,
        close_btn: QPushButton,
        wrapper: QWidget,
    ) -> None:
        self.tool_id = tool_id
        self.name = name
        self.widget = widget
        self.btn = btn
        self.close_btn = close_btn
        self.wrapper = wrapper


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

    def add_tab(self, tool_id: str, name: str, widget) -> TabItem:
        btn = QPushButton(name)
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

        item = TabItem(tool_id, name, widget, btn, close_btn, wrapper)
        self._tabs.append(item)
        self._row.insertWidget(self._row.count() - 1, wrapper)

        btn.clicked.connect(lambda: self._handle_tab_click(item))
        close_btn.clicked.connect(lambda: self._handle_tab_close(item))
        self.set_active(len(self._tabs) - 1)
        return item

    def _handle_tab_click(self, item: TabItem) -> None:
        try:
            self.tab_changed.emit(self._tabs.index(item))
        except ValueError:
            pass

    def _handle_tab_close(self, item: TabItem) -> None:
        try:
            self.tab_closed.emit(self._tabs.index(item))
        except ValueError:
            pass

    def set_active(self, idx: int) -> None:
        for i, t in enumerate(self._tabs):
            t.btn.setChecked(i == idx)

    def remove_tab(self, idx: int) -> None:
        if not (0 <= idx < len(self._tabs)):
            return
        item = self._tabs.pop(idx)
        self._row.removeWidget(item.wrapper)
        item.wrapper.deleteLater()

    def count(self) -> int:
        return len(self._tabs)

    def tab_at(self, idx: int) -> TabItem:
        return self._tabs[idx]
