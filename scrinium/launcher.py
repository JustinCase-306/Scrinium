"""Scrinium-Einstieg.

Aufruf ohne Argumente oeffnet das Fenster. Mit Argumenten running die
Kommandozeile (`--sortieren`, `--undo`, `--pruefen` usw.) - so bleibt
alles auch ohne Fenster bedienbar.
"""

from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) > 1:
        from scrinium.cli import run_cli

        return run_cli(sys.argv[1:])

    # Ohne Argumente: das Fenster.
    #
    # Ein Protokoll in eine Datei, weil die fertige EXE keine Konsole hat:
    # ohne das ist jeder Fehler beim Start unsichtbar. Genau daran habe
    # ich lange gesucht, als im Fenster "API.state is not a function"
    # stand und nirgends eine Ursache zu sehen war.
    _protokoll_einrichten()

    from scrinium.window import starten

    return starten()


def _protokoll_einrichten() -> None:
    """Schreibt Warnungen und Fehler nach %APPDATA%/Scrinium/scrinium.log."""
    import logging
    import os

    try:
        basis = os.environ.get("APPDATA") or os.path.expanduser("~")
        ordner = os.path.join(basis, "Scrinium")
        os.makedirs(ordner, exist_ok=True)
        logging.basicConfig(
            filename=os.path.join(ordner, "scrinium.log"),
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            encoding="utf-8",
            force=True,
        )
    except Exception:
        # Kein Protokoll ist kein Grund, nicht zu starten.
        pass


if __name__ == "__main__":
    sys.exit(main())