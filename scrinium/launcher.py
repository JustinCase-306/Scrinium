"""Scrinium launcher.

Kept as a tiny shim so `main.pyw` (no console window on Windows) and the
packaged exe share one entry point. The real GUI lives in ``scrinium/ui``.
"""

from __future__ import annotations

import sys


def main() -> int:
    # `python main.pyw --dry-run` behaves like the CLI - handy for testing.
    if len(sys.argv) > 1:
        from scrinium.cli import run_cli

        return run_cli(sys.argv[1:])
    from scrinium.ui.app import run

    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())