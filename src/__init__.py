"""Package init — export public API."""

import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys.executable).parent
else:
    ROOT_DIR = Path(__file__).resolve().parent.parent

from .cli import run_cli
from .gui import launch_gui

__all__ = ["run_cli", "launch_gui"]

__version__ = "0.1.0"

__author__ = "ChenXu-Huang"
