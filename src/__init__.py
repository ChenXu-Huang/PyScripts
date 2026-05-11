"""Package init — export public API."""

import sys
from pathlib import Path


def _resolve_root() -> Path:
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        root_dir = Path(sys.executable).parent
        if root_dir.name.lower() == "bin":
            root_dir = root_dir.parent
        return root_dir
    return Path(__file__).resolve().parent.parent


ROOT_DIR: Path = _resolve_root()

from .cli import run_cli
from .gui import launch_gui

__all__ = ["run_cli", "launch_gui"]

__version__ = "0.2.0"

__author__ = "ChenXu-Huang"
