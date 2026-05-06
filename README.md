# PyScripts

A desktop toolbox built with PySide6, providing utility tools through both a graphical interface and command-line interface.

## Tools

- **Regex Replacer** — Batch search and replace files in a folder using regular expressions, with dry-run preview and backup support.
- **Table Grapher** — Plot CSV data as line charts (direct, smooth spline, or linear regression) or histogram for single-column data.
- **Data Generator** — Generate random datasets with exact target statistics (mean, variance, range) via boundary-rejection sampling.

## Quick Start

```bash
# Launch GUI
uv run main.py -g

# Command-line usage
uv run main.py --help
```

Each tool can be used directly from the terminal — run `uv run main.py <tool> --help` for details.
