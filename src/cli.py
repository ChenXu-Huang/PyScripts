"""CLI — subcommand-based entry point for all utils tools."""

__all__ = ["run_cli"]

import argparse
import logging
from typing import Callable
from pathlib import Path

from . import ROOT_DIR


def _build_replace(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("replace", help="Batch regex find/replace in a folder")
    p.add_argument("--folder", type=Path, default=ROOT_DIR / "data", help="Root folder to scan recursively (default: %(default)s)")
    p.add_argument("--pattern", required=True, help="Regex search pattern (Python syntax)")
    p.add_argument("--replacement", default="", help="Replacement string, supports backreferences \\1, \\2, ... (default: '%(default)s')")
    p.add_argument("--ext", action="append", default=None, help="Filter by file extension, repeatable (e.g. --ext py --ext txt). Skip to process all files")
    p.add_argument("--ignore-case", action="store_true", help="Case-insensitive pattern matching")
    p.add_argument("--dry-run", action="store_true", help="Preview matched files and changes without modifying anything")
    p.add_argument("--backup", action="store_true", help="Backup original file as .bak before applying changes")


def _run_replace(args: argparse.Namespace) -> int:
    from .utils import regex_replacer as rr

    result = rr.replace_in_folder(
        folder=args.folder,
        pattern=args.pattern,
        replacement=args.replacement,
        extensions=args.ext,
        ignore_case=args.ignore_case,
        dry_run=args.dry_run,
        backup=args.backup,
    )
    print(result.summary(dry_run=args.dry_run))
    return 1 if result.errors else 0


def _build_graph(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("graph", help="Plot CSV data to PNG images")
    p.add_argument("--data", type=Path, required=True, help="Path to input CSV file")
    p.add_argument("--mode", choices=["direct", "smooth", "linear"], default="smooth", help="Line fitting mode: direct (raw line), smooth (cubic spline), linear (regression fit). Ignored for single-column CSVs (auto histogram) (default: %(default)s)")
    p.add_argument("--combined", action="store_true", help="Plot all Y variables together in one figure instead of separate figures")


def _run_graph(args: argparse.Namespace) -> int:
    from .utils import table_grapher as tg

    paths = tg.table2graph(data_path=args.data, mode=args.mode, plot_together=args.combined)
    print(*paths, sep="\n")
    return 0


def _build_generate(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("generate", help="Generate random dataset with exact target statistics via boundary-rejection sampling")
    p.add_argument("--n", type=int, required=True, help="Number of data points to generate")
    p.add_argument("--mean", type=float, required=True, help="Target arithmetic mean of the generated data")
    p.add_argument("--width", type=float, required=True, help="Total range width (max - min) of the generated data")
    p.add_argument("--variance", type=float, required=True, help="Target population variance of the generated data")
    p.add_argument("--dist", choices=["normal", "uniform"], default="normal", help="Distribution shape (default: %(default)s)")
    p.add_argument("--decimals", type=int, default=0, help="Decimal places for rounding output values (default: %(default)s, meaning integers)")
    p.add_argument("--csv", type=Path, default=None, help="Output CSV file path (default: data/random_data.csv)")
    p.add_argument("--seed", type=int, default=None, help="Random seed for reproducible generation")
    p.add_argument("--2d", action="store_true", dest="dim2", help="Generate 2-D data (X, Y) with a specified linear relationship and exact R^2")
    p.add_argument("--slope", type=float, default=1.0, help="Slope for the Y = slope * X + intercept relationship (2-D only, default: %(default)s)")
    p.add_argument("--intercept", type=float, default=0.0, help="Intercept for the Y = slope * X + intercept relationship (2-D only, default: %(default)s)")
    p.add_argument("--r-squared", type=float, default=0.95, dest="r_squared", help="Target coefficient of determination R^2 between X and Y (2-D only, default: %(default)s)")
    p.add_argument("--decimals-y", type=int, default=None, dest="decimals_y", help="Decimal places for rounding Y values (2-D only, default: same as --decimals)")


def _run_generate(args: argparse.Namespace) -> int:
    import numpy as np
    from .utils import data_generator as dg

    rng = np.random.default_rng(args.seed)
    csv_path = args.csv or ROOT_DIR / "data/random_data.csv"
    data = dg.generate_data(
        n=args.n,
        mean=args.mean,
        width=args.width,
        variance=args.variance,
        distribution=args.dist,
        decimals=args.decimals,
        rng=rng,
        csv_path=csv_path,
        dimension=2 if args.dim2 else 1,
        slope=args.slope,
        intercept=args.intercept,
        r_squared=args.r_squared,
        decimals_y=args.decimals_y,
    )
    print(dg.summary(data))
    print(f"Exported to: {csv_path.resolve()}")
    return 0


_CLI_TOOLS: list[tuple[str, str, Callable[..., None], Callable[..., int]]] = [
    ("replace", "Batch regex find/replace in a folder", _build_replace, _run_replace),
    ("graph", "Plot CSV data to PNG images", _build_graph, _run_graph),
    ("generate", "Generate random dataset with exact statistics", _build_generate, _run_generate),
]


def _get_version() -> str:
    import tomllib

    pyproject = ROOT_DIR / "pyproject.toml"
    try:
        with open(pyproject, "rb") as f:
            return tomllib.load(f)["project"]["version"]
    except Exception:
        return "0.0.0"


_VERSION = _get_version()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PyScripts Toolbox")
    parser.add_argument("-g", "--gui", action="store_true", help="Launch GUI application")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable DEBUG-level logging")
    parser.add_argument("--version", "-V", action="version", version=f"pyscripts {_VERSION}")

    sub = parser.add_subparsers(dest="tool", title="available tools")
    sub.required = False
    for name, help_text, build_fn, _ in _CLI_TOOLS:
        build_fn(sub)
        sub.choices[name].description = help_text

    return parser


def run_cli(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and run the requested tool or GUI.

    Returns exit code (0 = success, 1 = error, 2 = usage error).
    """
    from .logger import LoggerConfig, LoggerManager

    LoggerManager.configure(LoggerConfig(
        name="pyscripts",
        level="INFO",
        log_dir=ROOT_DIR / "logs",
        console=False,
        console_color=False,
        json_file=False,
        text_file=True,
        error_file=True,
        max_bytes=10 * 1024 * 1024,
        backup_count=10,
        default_extra={"app_version": _VERSION, "env": "dev"},
        ignored_loggers=["matplotlib"],
    ))

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        LoggerManager.update_level(logging.DEBUG)

    if args.gui:
        from .gui import launch_gui

        launch_gui()
        return 0

    if args.tool is None:
        parser.print_help()
        return 2

    for name, _, _, run_fn in _CLI_TOOLS:
        if args.tool == name:
            try:
                return run_fn(args)
            except Exception:
                logging.getLogger(__name__).exception("Tool '%s' failed", name)
                return 1

    return 2
