# Development

## Prerequisites

- Python >= 3.13
- Package manager: `uv`

## Adding a New Tool

### GUI tool

Add an entry to `GUI_TOOLS` in `src/gui/app/__init__.py`:

```python
GUI_TOOLS = [
    {"id": "my_tool", "icon": "🔧", "color": "#xxx", "module": ".app.my_tool"},
    ...
]
```

Create `src/gui/app/my_tool.py` with a `ToolWidget` class (a `QWidget` subclass). Core logic belongs in `src/utils/my_tool.py`.

Required translation keys in `lang/*.json`:
- `tool.my_tool.name` — display name (tab, menu, card title)
- `tool.my_tool.desc` — card subtitle on home page

### CLI tool

Add an entry to `_CLI_TOOLS` in `src/cli.py`:

```python
_CLI_TOOLS: list[tuple[str, str, Callable, Callable]] = [
    ("replace", "Batch regex find/replace in a folder", _build_replace, _run_replace),
    ("graph",   "Plot CSV data to PNG images",          _build_graph,   _run_graph),
    ("my_tool", "Description",                            _build_my_tool, _run_my_tool),
]
```

Then define `_build_my_tool(sub)` to add argparse arguments, and `_run_my_tool(args) -> int` to import and call the function from `src/utils/my_tool.py`.

## Coding Conventions

- **PySide6 enums**: Always use fully-qualified forms (`Qt.CursorShape.PointingHandCursor`, `Qt.AlignmentFlag.AlignCenter`). Never use Qt5-style shorthand (`Qt.PointingHandCursor`, `Qt.AlignCenter`).
- **Logger formatting**: Use C-style `%` formatting (`logger.info("result: %s", var)`), never f-strings. This defers formatting until the log level is confirmed enabled.
- **`from __future__ import annotations`**: Only add when needed (forward references or `TYPE_CHECKING`-guarded imports). Python >= 3.13 supports PEP 604 union syntax and generic builtins natively.
- **Line endings**: LF only (`\n`), no CRLF.

## Testing

- Every module in `src/utils/` should have a corresponding `tests/test_<module>.py` file.
- GUI widgets are tested manually, not with unit tests.
- Always check if a test file already exists before creating one; add to it if it does.

## Configuration

Mypy is configured in `pyproject.toml` under `[tool.mypy]`. The `src.gui.*` override disables `attr-defined`, `union-attr`, `method-assign`, and `arg-type` error codes to work around PySide6 stub limitations.

Run checks:
```bash
uv run mypy src/ tests/
uv run pytest
```

CI (GitHub Actions) runs on push/PR to main: mypy first, then pytest.
