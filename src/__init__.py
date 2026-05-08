"""Package init — export public API."""

import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    _root_dir = Path(sys.executable).parent
else:
    _root_dir = Path(__file__).resolve().parent.parent

ROOT_DIR: Path = _root_dir

from .cli import run_cli
from .gui import launch_gui

__all__ = ["run_cli", "launch_gui"]

__version__ = "0.1.0"

__author__ = "ChenXu-Huang"
