"""Scrinium-Einstieg.

Aufruf ohne Argumente oeffnet das Fenster. Mit Argumenten laeuft die
Kommandozeile (`--sortieren`, `--undo`, `--pruefen` usw.) - so bleibt
alles auch ohne Fenster bedienbar.
"""

from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) > 1:
        from scrinium.cli import run_cli

        return run_cli(sys.argv[1:])

    from scrinium.fenster import starten

    return starten()


if __name__ == "__main__":
    sys.exit(main())