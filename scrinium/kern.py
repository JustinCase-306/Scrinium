"""Scrinium-Kern: findet Werkzeuge und startet sie.

Der Kern weiss NICHT, welche Werkzeuge es gibt. Er geht einfach durch
`tools/` und schaut, was er findet. Ein neuer Ordner mit den richtigen
Dateien reicht - es muss kein Code geaendert werden.

Ein Werkzeug ist ein Ordner mit mindestens einer Datei `__init__.py`, die
diese drei Dinge anbietet:

    NAME  = "Downloads-Sortierer"     # Anzeigename
    def pruefe() -> tuple[bool, str]  # Darf ich starten?
    def starte() -> dict              # Was ich tue

Was `starte()` zurueckgibt, ist immer gleich aufgebaut:

    {
        "text":     "14 Dateien einsortiert",        # eine Zeile fuer die Anzeige
        "aktionen": [("Rueckgaengig", run_id)],       # was der Nutzer tun kann
        "daten":    {...},                           # Details, falls die UI sie will
    }

Der Kern muss das nicht verstehen - er zeigt `text` an und bietet `aktionen`
als Schaltflaechen an. Das ist der ganze Vertrag.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import traceback
from dataclasses import dataclass, field
from typing import Any

# Nur die drei Dateinamen, die ein Werkzeug wirklich braucht.
# Alles andere in der Tools-Liste wird ignoriert, damit man keine
# .txt-Dateien oder __pycache__ als Werkzeug sieht.
ERFORDERLICH = ("__init__.py",)


# ---------------------------------------------------------------------------
# Wo liegen die Programmeile?
# ---------------------------------------------------------------------------
def basis_verzeichnis() -> str:
    """Der Ordner, in dem Scrinium liegt.

    Relativ zum Programm, nicht zum Arbeitsordner. Damit Scrinium aus
    `C:\\Programme\\Scrinium` genauso laeuft wie aus `D:\\Dokumente\\Scrinium`.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # dev: .../Scrinium/scrinium/kern.py  ->  .../Scrinium
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tools_verzeichnis() -> str:
    """Der Ordner mit den Werkzeugen."""
    pfad = os.path.join(basis_verzeichnis(), "tools")
    os.makedirs(pfad, exist_ok=True)
    return pfad


# ---------------------------------------------------------------------------
# Ein Werkzeug
# ---------------------------------------------------------------------------
@dataclass
class Werkzeug:
    """Ein geladenes Werkzeug aus `tools/`."""

    ordner: str            # vollstaendiger Pfad zum Ordner
    name: str              # der Name, den es selbst nennt
    modul: Any = None      # das geladene Python-Modul
    beta: bool = False     # True = noch nicht fertig
    fehler: str = ""       # wenn beim Laden etwas kaputt ging

    @property
    def pfad(self) -> str:
        """Eigener Codepfad - damit das Werkzeug weitere Datei(en) laden kann."""
        if self.ordner not in sys.path:
            sys.path.insert(0, self.ordner)
        return self.ordner

    @property
    def id(self) -> str:
        """Kurzer, stabiler Name fuer Einstellungen."""
        return os.path.basename(self.ordner).lstrip("_")

    def pruefe(self) -> tuple[bool, str]:
        """Darf ich starten? Das Werkzeug darf das selbst entscheiden."""
        if self.fehler:
            return False, self.fehler
        pruef = getattr(self.modul, "pruefe", None)
        if not callable(pruef):
            return True, ""                       # kein Test = alles gut
        try:
            ergebnis = pruef()
        except Exception:
            return False, "pruefe() ist abgestuerzt"
        if isinstance(ergebnis, tuple) and len(ergebnis) == 2:
            return bool(ergebnis[0]), str(ergebnis[1])
        return bool(ergebnis), ""

    def starte(self) -> dict:
        """Fuehrt das Werkzeug aus und gibt das Standardergebnis zurueck.

        Ein Werkzeug, das kaputt geht, wird NICHT stillschweigend zu
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
            # Werkzeug ist defekt - sag es, statt still zu scheitern
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
def _ergebnis(text: str, aktionen=None, daten=None, fehler: bool = False) -> dict:
    return {"text": text, "aktionen": list(aktionen or []),
            "daten": dict(daten or {}), "fehler": fehler}


def _normalisiere(roh: dict) -> dict:
    """Macht aus allem, was ein Werkzeug zurueckgibt, dieselbe Form.

    Ein Werkzeug darf auch nur `{"text": "fertig"}` zurueckgeben - der Rest
    wird ergaenzt. Fehlt `text`, ist das ein Fehler: ohne Text kann die
    Oberflaeche nichts anzeigen.
    """
    text = roh.get("text")
    if not isinstance(text, str) or not text.strip():
        return _ergebnis("Werkzeug hat keinen Text zurueckgegeben.", fehler=True)

    aktionen = roh.get("aktionen") or []
    if not isinstance(aktionen, (list, tuple)):
        aktionen = []

    # Jede Aktion: (Beschriftung, Kennung). Sonst nicht anzeigen.
    saubere_aktionen = []
    for a in aktionen:
        if isinstance(a, (str, bytes)):
            continue                      # "Text" ist keine Aktion
        try:
            beschriftung, kennung = a[0], a[1]
        except (TypeError, IndexError, KeyError):
            continue
        saubere_aktionen.append((str(beschriftung), kennung))

    daten = roh.get("daten")
    return _ergebnis(text, saubere_aktionen,
                     daten if isinstance(daten, dict) else {},
                     bool(roh.get("fehler")))


# ---------------------------------------------------------------------------
# Werkzeuge finden und laden
# ---------------------------------------------------------------------------
def _lade(ordner: str) -> Werkzeug:
    """Laedt ein Werkzeug aus einem Ordner."""
    init = os.path.join(ordner, "__init__.py")
    wc = Werkzeug(ordner=os.path.basename(ordner), name=os.path.basename(ordner))
    wc.ordner = ordner

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


def finde_werkzeuge(ordner: str | None = None) -> list[Werkzeug]:
    """Alle Werkzeuge in `tools/` - ohne sie zu kennen.

    Regel: ein Ordner ist ein Werkzeug, wenn er eine `__init__.py` hat.
    Alles andere wird ignoriert (auch __pycache__ und Textdateien).
    """
    basis = ordner or tools_verzeichnis()
    gefunden: list[Werkzeug] = []

    try:
        eintraege = sorted(os.listdir(basis))
    except OSError:
        return gefunden

    for eintrag in eintraege:
        pfad = os.path.join(basis, eintrag)
        if not os.path.isdir(pfad):
            continue
        if eintrag.startswith((".", "__")):
            continue                       # __pycache__, .git usw.
        if not os.path.isfile(os.path.join(pfad, ERFORDERLICH[0])):
            continue
        gefunden.append(_lade(pfad))

    gefunden.sort(key=lambda w: w.name.lower())
    return gefunden


def werkzeug_namen() -> list[str]:
    """Nur die Anzeigenamen - fuer Auswahlfelder usw."""
    return [w.name for w in finde_werkzeuge()]


if __name__ == "__main__":
    # Kurztest: zeigt, was gefunden wurde
    print(f"Werkzeuge in {tools_verzeichnis()}:")
    for w in finde_werkzeuge():
        zustand = "bereit" if w.pruefe()[0] else f"blockiert: {w.pruefe()[1]}"
        print(f"  {'[beta]' if w.beta else '      '} {w.name:<26} {zustand}")
    if not finde_werkzeuge():
        print("  (keine)")