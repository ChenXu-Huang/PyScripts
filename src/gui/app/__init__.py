"""Tool widgets package — each tool's GUI widget lives in its own module."""

__all__ = ["GUI_TOOLS"]

from . import regex_replacer
from . import table_grapher
from . import data_generator

GUI_TOOLS = [
    {"id": "regex_replacer", "icon": "📝", "color": "#4F8EF7", "module": ".app.regex_replacer"},
    {"id": "table_grapher", "icon": "🎨", "color": "#F76B4F", "module": ".app.table_grapher"},
    {"id": "data_generator", "icon": "🎲", "color": "#4CAF50", "module": ".app.data_generator"},
]
