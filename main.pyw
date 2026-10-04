"""Scrinium launcher - double-click entry point.

Kept tiny on purpose: everything lives in the ``scrinium`` package, so this
file stays readable and the PyInstaller spec has one obvious entry point.

Run headless from a shortcut or Task Scheduler by passing CLI flags::

    main.pyw --dry-run          # preview only
    main.pyw --once --json      # sort now, machine readable
"""

import os
import sys

# Support running from a frozen one-file build (sys._MEIPASS) as well as from
# a plain source checkout next to this file.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    if len(sys.argv) > 1:
        from scrinium.cli import run_cli

        return run_cli(sys.argv[1:])

    # Ohne Argumente: das Fenster. Der Einstieg sitzt in scrinium.launcher,
    # damit main.pyw und die gepackte EXE denselben Weg nehmen.
    from scrinium.launcher import main as start

    return start()


if __name__ == "__main__":
    sys.exit(main())