"""Main application window — the top-level QMainWindow."""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QStackedWidget, QMenu,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor

from .home import HomePage
from .tabs import TabBar, TabItem
from .tool_page import ToolPage
from .app import GUI_TOOLS
from .i18n import tr, set_language, language_changed, available_languages
from .theme import theme_manager
from ..config import config_manager
from ..logger import get_logger

logger = get_logger(__name__)

THEME_LIGHT = "light"
THEME_DARK = "dark"
THEME_SYSTEM = "system"

_THEME_ICONS = {
    THEME_SYSTEM: "🌓",
    THEME_LIGHT: "☀️",
    THEME_DARK: "🌙",
}


class MainWindow(QMainWindow):
    """Top-level window with top bar, home page, and lazy-loaded tool tabs."""

    def __init__(self) -> None:
        super().__init__()
        self.resize(1100, 720)
        self.setMinimumSize(780, 560)

        theme_manager.set_mode(config_manager.get_app("theme", theme_manager.THEME_SYSTEM))
        theme_manager.init_system_dark()
        theme_manager.apply()

        self._open_tools: dict[str, int] = {}
        self._build_ui()

        language_changed.connect(self._retranslate)

    # ── Theme ────────────────────────────────────────────────────────

    def _set_theme(self, mode: str) -> None:
        theme_manager.set_mode(mode)
        self._theme_btn.setText(_THEME_ICONS[mode])
        config_manager.set_app("theme", mode)

    # ── Build UI ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("RootWidget")
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # Top bar
        topbar = QWidget()
        topbar.setObjectName("TopBar")
        topbar.setFixedHeight(56)
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(16, 10, 16, 10)
        tb.setSpacing(8)

        self._menu_btn = QPushButton()
        self._menu_btn.setObjectName("MenuBtn")
        self._menu_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._build_tool_menu()
        tb.addWidget(self._menu_btn)

        self._tab_bar = TabBar()
        tb.addWidget(self._tab_bar, 1)

        self._lang_btn = QPushButton()
        self._lang_btn.setObjectName("MenuBtn")
        self._lang_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._build_lang_menu()
        tb.addWidget(self._lang_btn)

        self._theme_btn = QPushButton()
        self._theme_btn.setObjectName("IconBtn")
        self._theme_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._build_theme_menu()
        tb.addWidget(self._theme_btn)

        vbox.addWidget(topbar)

        # Stacked content
        self._stack = QStackedWidget()
        self._stack.setObjectName("MainStack")
        self._home = HomePage()
        self._home.tool_opened.connect(self._open_tool)
        self._stack.addWidget(self._home)
        vbox.addWidget(self._stack, 1)

        self._tab_bar.tab_changed.connect(self._on_tab_changed)
        self._tab_bar.tab_closed.connect(self._on_tab_closed)

        self._retranslate()

    # ── Menu builders ────────────────────────────────────────────────

    def _build_tool_menu(self) -> None:
        menu = QMenu(self)
        home_act = menu.addAction("")
        home_act.triggered.connect(lambda: self._stack.setCurrentIndex(0))
        menu.addSeparator()
        for tool in GUI_TOOLS:
            a = menu.addAction(f"{tool['icon']}  ...")
            a._tool = tool
            a.triggered.connect(lambda _, t=tool: self._open_tool(t))
        self._tool_menu = menu
        self._menu_btn.setMenu(menu)

    def _build_theme_menu(self) -> None:
        menu = QMenu(self)
        for mode in (THEME_SYSTEM, THEME_LIGHT, THEME_DARK):
            a = menu.addAction("")
            a._theme_mode = mode
            a.triggered.connect(lambda _, m=mode: self._set_theme(m))
        self._theme_menu = menu
        self._theme_btn.setMenu(menu)
        self._theme_btn.setText(_THEME_ICONS[theme_manager.mode])

    def _build_lang_menu(self) -> None:
        menu = QMenu(self)
        for locale, _ in available_languages():
            a = menu.addAction("")
            a._locale = locale
            a.triggered.connect(lambda _, lc=locale: set_language(lc))
        self._lang_menu = menu
        self._lang_btn.setMenu(menu)

    # ── Retranslate ──────────────────────────────────────────────────

    def _retranslate(self) -> None:
        self.setWindowTitle(tr("app.title"))
        self._menu_btn.setText(tr("topbar.tools_menu"))
        self._lang_btn.setText(tr("lang.btn"))

        tool_actions = [a for a in self._tool_menu.actions() if not a.isSeparator()]
        if tool_actions:
            tool_actions[0].setText(tr("topbar.home"))
        for a in self._tool_menu.actions():
            if not a.isSeparator() and hasattr(a, "_tool"):
                tid = a._tool["id"]
                a.setText(f"{a._tool['icon']}  {tr(f'tool.{tid}.name')}")

        theme_labels = {
            THEME_SYSTEM: f"{_THEME_ICONS[THEME_SYSTEM]}  {tr('theme.system')}",
            THEME_LIGHT: f"{_THEME_ICONS[THEME_LIGHT]}  {tr('theme.light')}",
            THEME_DARK: f"{_THEME_ICONS[THEME_DARK]}  {tr('theme.dark')}",
        }
        for a in self._theme_menu.actions():
            if hasattr(a, "_theme_mode"):
                a.setText(theme_labels[a._theme_mode])

        lang_map = dict(available_languages())
        for a in self._lang_menu.actions():
            if hasattr(a, "_locale"):
                a.setText(lang_map.get(a._locale, a._locale))

        tool_map = {t["id"]: t for t in GUI_TOOLS}
        for i in range(self._tab_bar.count()):
            item = self._tab_bar.tab_at(i)
            tool = tool_map.get(item.tool_id)
            if tool and item.btn:
                item.btn.setText(f"{tool['icon']} {tr(f'tool.{item.tool_id}.name')}")

    # ── Tool opening ─────────────────────────────────────────────────

    def _open_tool(self, tool: dict) -> None:
        tid = tool["id"]
        if tid in self._open_tools:
            idx = self._open_tools[tid]
            self._stack.setCurrentIndex(idx)
            self._sync_tab_for_stack(idx)
            return
        page = ToolPage(tool)
        stack_idx = self._stack.addWidget(page)
        self._open_tools[tid] = stack_idx
        tab_item = TabItem(tid, f"{tool['icon']} {tr(f'tool.{tid}.name')}", page)
        self._tab_bar.add_tab(tab_item)
        self._stack.setCurrentIndex(stack_idx)
        self._sync_tab_for_stack(stack_idx)

    def _sync_tab_for_stack(self, stack_idx: int) -> None:
        for i in range(self._tab_bar.count()):
            if self._tab_bar.tab_at(i).widget is self._stack.widget(stack_idx):
                self._tab_bar.set_active(i)
                return

    # ── Tab signals ──────────────────────────────────────────────────

    def _on_tab_changed(self, tab_idx: int) -> None:
        item = self._tab_bar.tab_at(tab_idx)
        for si in range(self._stack.count()):
            if self._stack.widget(si) is item.widget:
                self._stack.setCurrentIndex(si)
                self._tab_bar.set_active(tab_idx)
                return

    def _on_tab_closed(self, tab_idx: int) -> None:
        item = self._tab_bar.tab_at(tab_idx)
        for si in range(self._stack.count()):
            if self._stack.widget(si) is item.widget:
                w = self._stack.widget(si)
                self._stack.removeWidget(w)
                w.deleteLater()
                break
        self._open_tools.pop(item.tool_id, None)
        self._tab_bar.remove_tab(tab_idx)
        if self._tab_bar.count() == 0:
            self._stack.setCurrentIndex(0)
        else:
            new_idx = min(tab_idx, self._tab_bar.count() - 1)
            self._on_tab_changed(new_idx)
            self._tab_bar.set_active(new_idx)

    # ── Close event ──────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        logger.info("Window close triggered, saving configuration...")
        config_manager.save_all()
        logger.info("Configuration saved")
        event.accept()
