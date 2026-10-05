"""Scrinium-Kern: findet Tools und startet sie.

Der Kern weiss NICHT, welche Tools es gibt. Er geht einfach durch
`tools/` und schaut, was er findet. Ein neuer Ordner mit den richtigen
Dateien reicht - es muss kein Code geaendert werden.

Ein Tool ist ein Ordner mit mindestens einer Datei `__init__.py`, die
diese drei Dinge anbietet:

    NAME  = "Downloads-Sortierer"     # Anzeigename
    def check() -> tuple[bool, str]  # Darf ich starten?
    def starte() -> dict              # Was ich tue

Was `starte()` zurueckgibt, ist immer gleich aufgebaut:

    {
        "text":     "14 Dateien einsortiert",        # eine Zeile fuer die Anzeige
        "actions": [("Rueckgaengig", run_id)],       # was der Nutzer tun kann
        "data":    {...},                           # Details, falls die UI sie will
    }

Der Kern muss das nicht verstehen - er zeigt `text` an und bietet `actions`
als Schaltflaechen an. Das ist der ganze Vertrag.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import traceback
from dataclasses import dataclass, field
from typing import Any

# Nur die drei Dateinamen, die ein Tool wirklich braucht.
# Alles andere in der Tools-Liste wird ignoriert, damit man keine
# .txt-Dateien oder __pycache__ als Tool sieht.
ERFORDERLICH = ("__init__.py",)


# ---------------------------------------------------------------------------
# Wo liegen die Programmeile?
# ---------------------------------------------------------------------------
def base_dir() -> str:
    """Der Ordner, in dem Scrinium liegt.

    Relativ zum Programm, nicht zum Arbeitsordner. Damit Scrinium aus
    `C:\\Programme\\Scrinium` genauso running wie aus `D:\\Dokumente\\Scrinium`.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # dev: .../Scrinium/scrinium/core.py  ->  .../Scrinium
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tools_dir() -> str:
    """Der Ordner mit den Werkzeugen."""
    path = os.path.join(base_dir(), "tools")
    os.makedirs(path, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Ein Tool
# ---------------------------------------------------------------------------
@dataclass
class Tool:
    """Ein geladenes Tool aus `tools/`."""

    folder: str            # vollstaendiger Pfad zum Ordner
    name: str              # der Name, den es selbst nennt
    modul: Any = None      # das geladene Python-Modul
    beta: bool = False     # True = noch nicht fertig
    fehler: str = ""       # wenn beim Laden etwas kaputt ging

    @property
    def path(self) -> str:
        """Eigener Codepfad - damit das Tool weitere Datei(en) laden kann."""
        if self.folder not in sys.path:
            sys.path.insert(0, self.folder)
        return self.folder

    @property
    def id(self) -> str:
        """Kurzer, stabiler Name fuer Settings."""
        return os.path.basename(self.folder).lstrip("_")

    def check(self) -> tuple[bool, str]:
        """Darf ich starten? Das Tool darf das selbst entscheiden."""
        if self.fehler:
            return False, self.fehler
        pruef = getattr(self.modul, "check", None)
        if not callable(pruef):
            return True, ""                       # kein Test = alles gut
        try:
            result = pruef()
        except Exception:
            return False, "check() ist abgestuerzt"
        if isinstance(result, tuple) and len(result) == 2:
            return bool(result[0]), str(result[1])
        return bool(result), ""

    def starte(self) -> dict:
        """Fuehrt das Tool aus und gibt das Standardergebnis zurueck.

        Ein Tool, das kaputt geht, wird NICHT stillschweigend zu
        `{}`. Es kommt ein sichtbarer Fehler zurueck.
        """
        if self.fehler:
            return _ergebnis("Kann nicht starten: " + self.fehler, fehler=True)

        starte = getattr(self.modul, "starte", None)
        if not callable(starte):
            return _ergebnis(
                f"'{self.name}' hat keine starte()-Funktion.", fehler=True)

        try:
            roh = starte()
        except Exception:
            # Tool ist defekt - sag es, statt still zu scheitern
            self.fehler = traceback.format_exc(limit=2).strip().splitlines()[-1]
            return _ergebnis(f"'{self.name}' ist abgestuerzt: {self.fehler}",
                             fehler=True)

        if not isinstance(roh, dict):
            return _ergebnis(
                f"'{self.name}' hat das falsche Format zurueckgegeben.", fehler=True)
        return _normalisiere(roh)


# ---------------------------------------------------------------------------
# Ergebnisse standardisieren
# ---------------------------------------------------------------------------
def _ergebnis(text: str, actions=None, data=None, fehler: bool = False) -> dict:
    return {"text": text, "actions": list(actions or []),
            "data": dict(data or {}), "fehler": fehler}


def _normalisiere(roh: dict) -> dict:
    """Macht aus allem, was ein Tool zurueckgibt, dieselbe Form.

    Ein Tool darf auch nur `{"text": "fertig"}` zurueckgeben - der Rest
    wird ergaenzt. Fehlt `text`, ist das ein Fehler: ohne Text kann die
    Oberflaeche nichts anzeigen.
    """
    text = roh.get("text")
    if not isinstance(text, str) or not text.strip():
        return _ergebnis("Tool hat keinen Text zurueckgegeben.", fehler=True)

    actions = roh.get("actions") or []
    if not isinstance(actions, (list, tuple)):
        actions = []

    # Jede Aktion: (Beschriftung, Kennung). Sonst nicht anzeigen.
    saubere_aktionen = []
    for a in actions:
        if isinstance(a, (str, bytes)):
            continue                      # "Text" ist keine Aktion
        try:
            beschriftung, kennung = a[0], a[1]
        except (TypeError, IndexError, KeyError):
            continue
        saubere_aktionen.append((str(beschriftung), kennung))

    data = roh.get("data")
    return _ergebnis(text, saubere_aktionen,
                     data if isinstance(data, dict) else {},
                     bool(roh.get("fehler")))


# ---------------------------------------------------------------------------
# Tools finden und laden
# ---------------------------------------------------------------------------
def _lade(folder: str) -> Tool:
    """Laedt ein Tool aus einem Ordner."""
    init = os.path.join(folder, "__init__.py")
    wc = Tool(folder=os.path.basename(folder), name=os.path.basename(folder))
    wc.folder = folder

    try:
        spec = importlib.util.spec_from_file_location(
            f"scrinium_tool_{wc.id}", init)
        if spec is None or spec.loader is None:
            wc.fehler = "kein Python-Modul"
            return wc
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
    except Exception:
        wc.fehler = traceback.format_exc(limit=1).strip().splitlines()[-1]
        return wc

    wc.modul = modul
    wc.name = str(getattr(modul, "NAME", wc.id))
    wc.beta = bool(getattr(modul, "BETA", False))
    return wc


def find_tools(folder: str | None = None) -> list[Tool]:
    """Alle Tools in `tools/` - ohne sie zu kennen.

    Regel: ein Ordner ist ein Tool, wenn er eine `__init__.py` hat.
    Alles andere wird ignoriert (auch __pycache__ und Textdateien).
    """
    basis = folder or tools_dir()
    gefunden: list[Tool] = []

    try:
        eintraege = sorted(os.listdir(basis))
    except OSError:
        return gefunden

    for eintrag in eintraege:
        path = os.path.join(basis, eintrag)
        if not os.path.isdir(path):
            continue
        if eintrag.startswith((".", "__")):
            continue                       # __pycache__, .git usw.
        if not os.path.isfile(os.path.join(path, ERFORDERLICH[0])):
            continue
        gefunden.append(_lade(path))

    gefunden.sort(key=lambda w: w.name.lower())
    return gefunden


def tool_names() -> list[str]:
    """Nur die Anzeigenamen - fuer Auswahlfelder usw."""
    return [w.name for w in find_tools()]


if __name__ == "__main__":
    # Kurztest: zeigt, was gefunden wurde
    print(f"Tools in {tools_dir()}:")
    for w in find_tools():
        state = "bereit" if w.check()[0] else f"blockiert: {w.check()[1]}"
        print(f"  {'[beta]' if w.beta else '      '} {w.name:<26} {state}")
    if not find_tools():
        print("  (keine)")