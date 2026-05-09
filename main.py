"""Application entry point — delegates to the CLI dispatcher (run_cli)."""

import sys
from typing import NoReturn

from src import run_cli


def main() -> NoReturn:
    sys.exit(run_cli())


if __name__ == "__main__":
    main()
