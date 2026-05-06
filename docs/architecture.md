# Architecture

## Directory Structure

```
main.py                  ← configures logging, then delegates to run_cli()
├── pyproject.toml       ← project metadata, deps, mypy/pytest config
├── src/
│   ├── __init__.py      ← exports run_cli() and launch_gui()
│   ├── cli.py           ← subcommand-based CLI: replace, graph, ...
│   ├── config.py        ← ConfigManager singleton (config/app.json, config/history.json)
│   ├── logger.py        ← structured JSON logging, rotation, trace IDs, @log_exceptions
│   ├── utils/
│   │   ├── data_generator.py    ← generate_data() with registered samplers
│   │   ├── regex_replacer.py    ← core logic (Qt-free)
│   │   └── table_grapher.py     ← core logic (Qt-free)
│   └── gui/
│       ├── __init__.py          ← launch_gui() (lazy Qt import)
│       ├── main_app.py          ← MainWindow (QMainWindow), theme/lang menus, tab mgmt
│       ├── home.py              ← HomePage, ToolCard (responsive grid)
│       ├── tabs.py              ← TabBar, TabItem (horizontal tab strip)
│       ├── tool_page.py         ← ToolPage wrapper per tool widget
│       ├── widgets.py           ← shared reusable widgets (InputEdit, etc.)
│       ├── theme.py             ← ThemeTokens, stylesheet(), ThemeManager
│       ├── i18n.py              ← tr(), set_language(), language_changed signal
│       └── app/
│           ├── __init__.py         ← GUI_TOOLS list (tool metadata)
│           ├── regex_replacer.py  ← ToolWidget for regex replace
│           ├── table_grapher.py   ← ToolWidget for function plotter
│           └── data_generator.py  ← ToolWidget for random data generation
├── assets/
│   ├── check.svg            ← checkmark for QCheckBox:checked
│   ├── chevron-down.svg     ← dropdown arrow for QComboBox
│   └── chevron-right.svg    ← arrow icon for ToolCard
├── .github/
│   └── workflows/
│       └── ci.yml           ← GitHub Actions: mypy + pytest on push/PR to main
├── lang/
│   ├── zh_CN.json           ← source of truth (simplified Chinese)
│   ├── en_US.json           ← English
│   └── ja_JP.json           ← Japanese
└── tests/
    ├── conftest.py
    ├── test_data_generator.py
    ├── test_regex_replacer.py
    └── test_table_grapher.py
```

## Control Flow

```
main.py → src.logger (init logging via LoggerConfig(...))
        → src.cli.run_cli()
           ├── replace  → src.utils.regex_replacer.replace_in_folder
           ├── graph    → src.utils.table_grapher.table2graph
           ├── generate → src.utils.data_generator.generate_data
           └── -g       → src.gui.launch_gui → MainWindow (PySide6 QMainWindow)
                                  ├── HomePage (ToolCard grid)              ← src.gui.home
                                  ├── TabBar / ToolPage (lazy-loaded)       ← src.gui.tabs / src.gui.tool_page
                                  │    ├── src.gui.app.regex_replacer       ← wraps src.utils.regex_replacer
                                  │    ├── src.gui.app.table_grapher        ← wraps src.utils.table_grapher
                                  │    └── src.gui.app.data_generator       ← wraps src.utils.data_generator
                                  ├── src.gui.theme       (light/dark/system stylesheet)
                                  ├── src.gui.i18n        (hot-swappable L10n via JSON, falls back to zh_CN)
                                  ├── src.gui.app         (GUI_TOOLS metadata list)
                                  └── src.gui.widgets     (shared form widgets)
```

## Key Design Decisions

- **Utils are Qt-free**: `src/utils/` modules have zero Qt imports; they can be used from CLI or GUI.
- **Tool widgets are lazy-loaded**: Each tool's GUI is `importlib.import_module()`-ed when opened. Adding a tool requires only a `GUI_TOOLS` entry and a widget module — no wiring in `main_app.py`.
- **Config is JSON-based**: `src.config.ConfigManager` singleton reads/writes `config/app.json` and `config/history.json` with dot-path nested access.
- **Theme applies via global stylesheet**: `theme.py` builds a single `QApplication.setStyleSheet()` string from `ThemeTokens`. Widgets use `#ObjectName` selectors — no inline styles, no per-widget stylesheets.
- **Translations react to signals**: `language_changed` signal is emitted on locale switch. Widgets connect in `__init__` and call `tr()` in the slot — no manual retranslation triggers needed.
- **SVG assets in stylesheet use relative paths**: `QComboBox::down-arrow` and `QCheckBox::indicator:checked` use `url(assets/xxx.svg)` (relative to CWD at runtime). `QSvgWidget` in code uses an absolute `Path(__file__).resolve()` resolved path.
