"""theme.py — unified theme / stylesheet configuration."""

__all__ = [
    "ThemeTokens",
    "DiffColors",
    "theme_manager",
    "stylesheet",
]

from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette


@dataclass(frozen=True)
class ThemeTokens:
    bg: str
    surface: str
    surface2: str
    border: str
    text: str
    text_sub: str
    accent: str
    tab_active: str
    tab_bg: str
    card_hover: str
    topbar: str
    is_dark: bool


@dataclass(frozen=True)
class DiffColors:
    file_accent: str
    del_bg: str
    del_fg: str
    add_bg: str
    add_fg: str
    line_no: str
    err_bg: str
    err_fg: str


_LIGHT_TOKENS = ThemeTokens(
    bg="#F4F6FB",
    surface="#FFFFFF",
    surface2="#EEF1F8",
    border="#DDE2EE",
    text="#1A1D2E",
    text_sub="#6B7280",
    accent="#4F8EF7",
    tab_active="#FFFFFF",
    tab_bg="#E8ECF5",
    card_hover="#F0F4FF",
    topbar="#FFFFFF",
    is_dark=False,
)

_DARK_TOKENS = ThemeTokens(
    bg="#0F1117",
    surface="#1A1D2E",
    surface2="#22263A",
    border="#2E3250",
    text="#E8EAF2",
    text_sub="#8892B0",
    accent="#4F8EF7",
    tab_active="#1A1D2E",
    tab_bg="#0F1117",
    card_hover="#1E2238",
    topbar="#1A1D2E",
    is_dark=True,
)

_LIGHT_DIFF = DiffColors(
    file_accent="#2563EB",
    del_bg="#FEE2E2",
    del_fg="#B91C1C",
    add_bg="#DCFCE7",
    add_fg="#15803D",
    line_no="#9CA3AF",
    err_bg="#FEE2E2",
    err_fg="#B91C1C",
)

_DARK_DIFF = DiffColors(
    file_accent="#4F8EF7",
    del_bg="#3D1515",
    del_fg="#FF7B7B",
    add_bg="#0D2E1A",
    add_fg="#57E89C",
    line_no="#6B7280",
    err_bg="#2E1515",
    err_fg="#FF7B7B",
)


def stylesheet(t: ThemeTokens) -> str:
    return f"""
/* ── Global ── */
QWidget {{
    font-family: "PingFang SC", "Microsoft YaHei UI", "Segoe UI";
    font-size: 14px;
    color: {t.text};
    background: transparent;
}}
QMainWindow, #RootWidget {{
    background: {t.bg};
}}

/* ── Scrollbar ── */
QScrollBar:vertical {{
    background: transparent; width: 6px; margin: 0; border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {t.border}; border-radius: 3px; min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

/* ── TopBar ── */
#TopBar {{
    background: {t.topbar};
    border-bottom: 1px solid {t.border};
}}

/* ── TabBar ── */
#TabBar {{
    background: {t.tab_bg};
    border-radius: 10px;
    padding: 3px;
}}
#TabBtn {{
    background: transparent;
    border: none;
    border-radius: 8px;
    color: {t.text_sub};
    padding: 6px 18px;
    font-size: 13px;
    font-weight: 500;
}}
#TabBtn:checked {{
    background: {t.tab_active};
    color: {t.accent};
    font-weight: 600;
}}
#TabBtn:hover:!checked {{
    background: {t.surface2};
    color: {t.text};
}}

/* ── MenuBtn / IconBtn ── */
#MenuBtn::menu-indicator, #IconBtn::menu-indicator {{ image: none; width: 0; }}

/* ── MenuBtn ── */
#MenuBtn {{
    background: {t.surface2};
    border: 1px solid {t.border};
    border-radius: 10px;
    color: {t.text};
    padding: 0px 14px 0px 12px;
    font-size: 13px;
    font-weight: 500;
    min-height: 36px;
    max-height: 36px;
}}
#MenuBtn:hover {{
    background: {t.card_hover};
    border-color: {t.accent};
}}

/* ── IconBtn ── */
#IconBtn {{
    background: {t.surface2};
    border: 1px solid {t.border};
    border-radius: 10px;
    color: {t.text};
    font-size: 16px;
    min-width:  36px; max-width:  36px;
    min-height: 36px; max-height: 36px;
    padding: 0;
}}
#IconBtn:hover {{
    background: {t.card_hover};
    border-color: {t.accent};
}}

/* ── QMenu ── */
QMenu {{
    background: {t.surface};
    border: 1px solid {t.border};
    border-radius: 12px;
    padding: 6px;
}}
QMenu::item {{
    padding: 8px 20px;
    border-radius: 8px;
    color: {t.text};
    font-size: 13px;
}}
QMenu::item:selected {{
    background: {t.surface2};
    color: {t.accent};
}}
QMenu::separator {{
    height: 1px;
    background: {t.border};
    margin: 4px 10px;
}}

/* ── HomePage ── */
#HomeTitle  {{ font-size: 26px; font-weight: 700; color: {t.text}; }}
#HomeSubtitle {{ font-size: 14px; color: {t.text_sub}; }}

/* ── ToolCard ── */
#ToolCard {{
    background: {t.surface};
    border: 1px solid {t.border};
    border-radius: 18px;
}}
#ToolCard:hover {{
    background: {t.card_hover};
    border-color: {t.accent};
}}
#CardTitle  {{ font-size: 15px; font-weight: 600; color: {t.text}; }}
#CardDesc   {{ font-size: 12px; color: {t.text_sub}; }}
#CardArrow  {{ min-width: 18px; min-height: 18px; }}

/* ── ToolPage / Surface ── */
#ToolPageWrapper {{ background: {t.bg}; }}
#Surface {{
    background: {t.surface};
    border: 1px solid {t.border};
    border-radius: 14px;
}}

/* ── CloseTabBtn ── */
#CloseTabBtn {{
    background: transparent;
    border: none;
    border-radius: 6px;
    color: {t.text_sub};
    font-size: 11px;
    padding: 1px 3px;
    max-width: 18px;
    max-height: 18px;
}}
#CloseTabBtn:hover {{
    background: {t.surface2};
    color: {t.text};
}}

/* ── InputEdit ── */
#InputEdit {{
    background: transparent;
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 0 10px;
    font-size: 13px;
    color: {t.text};
}}
#InputEdit:focus {{ border-color: {t.accent}; }}
#InputEdit:read-only {{ color: {t.text_sub}; }}

/* ── QComboBox ── */
QComboBox {{
    background: transparent;
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 0 10px;
    font-size: 13px;
    color: {t.text};
    min-height: 36px;
}}
QComboBox:focus {{ border-color: {t.accent}; }}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox::down-arrow {{
    width: 12px; height: 12px;
    image: url(assets/chevron-down.svg);
}}
QComboBox QAbstractItemView {{
    background: {t.surface};
    border: 1px solid {t.border};
    border-radius: 8px;
    padding: 4px;
    outline: none;
    color: {t.text};
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 12px;
    border-radius: 6px;
    min-height: 28px;
}}
QComboBox QAbstractItemView::item:hover,
QComboBox QAbstractItemView::item:selected {{
    background: {t.surface2};
    color: {t.accent};
}}

/* ── QCheckBox ── */
QCheckBox {{ font-size: 13px; spacing: 6px; }}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {t.border};
    border-radius: 3px;
    background: {t.surface};
}}
QCheckBox::indicator:checked {{
    background: {t.accent};
    border-color: {t.accent};
    image: url(assets/check.svg);
}}

/* ── RunBtn ── */
#RunBtn {{
    background: {t.accent};
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    font-size: 14px;
}}
#RunBtn:hover  {{ background: {"#3A7DE8" if t.is_dark else "#2563EB"}; }}
#RunBtn:disabled {{ background: {t.border}; color: {t.text_sub}; }}

/* ── ProgressBar ── */
QProgressBar {{
    border: none;
    border-radius: 2px;
    background: {t.border};
}}
QProgressBar::chunk {{
    background: {t.accent};
    border-radius: 2px;
}}
"""


class _ThemeManager(QObject):
    changed = Signal(object)

    THEME_LIGHT = "light"
    THEME_DARK = "dark"
    THEME_SYSTEM = "system"

    def __init__(self) -> None:
        super().__init__()
        self._mode: str = self.THEME_SYSTEM
        self._sys_dark: bool = False
        self._tokens: ThemeTokens = _LIGHT_TOKENS
        self._diff: DiffColors = _LIGHT_DIFF

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def tokens(self) -> ThemeTokens:
        return self._tokens

    @property
    def diff(self) -> DiffColors:
        return self._diff

    @property
    def is_dark(self) -> bool:
        return self._tokens.is_dark

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self.apply()

    def update_system_dark(self, dark: bool) -> None:
        if dark != self._sys_dark:
            self._sys_dark = dark
            if self._mode == self.THEME_SYSTEM:
                self.apply()

    def apply(self) -> None:
        dark = self._resolve_dark()
        self._tokens = _DARK_TOKENS if dark else _LIGHT_TOKENS
        self._diff = _DARK_DIFF if dark else _LIGHT_DIFF
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setStyleSheet(stylesheet(self._tokens))
        self.changed.emit(self._tokens)

    def init_system_dark(self) -> None:
        self._sys_dark = QApplication.palette().color(QPalette.ColorRole.Window).lightness() < 128

    def _resolve_dark(self) -> bool:
        if self._mode == self.THEME_DARK:
            return True
        if self._mode == self.THEME_LIGHT:
            return False
        return self._sys_dark


theme_manager = _ThemeManager()
