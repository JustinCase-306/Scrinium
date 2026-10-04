"""Scrinium-Einstellungen.

Zwei Sorten Dinge, die man trennen muss:

1.  **Was der Nutzer eingestellt hat** (welcher Download-Ordner, welche
    Sprache, welche Werkzeuge sind an) -> `config.json`
2.  **Wo Scrinium liegt** -> wird nie gespeichert, sondern jedes Mal neu
    aus dem Programmordner berechnet

Punkt 2 ist wichtig: Scrinium darf keinen festen Pfad speichern. Wenn du
den Ordner nach `D:\\Programme\\Scrinium` kopierst, muss alles weiter
funktionieren.

Die config.json liegt in `%APPDATA%\\Scrinium\\`, weil man in
`C:\\Programme\\` nicht schreiben darf. Das Programm ist umziehbar, die
Einstellungen bleiben.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field, asdict

from .kern import basis_verzeichnis

CONFIG_NAME = "config.json"


def config_ordner() -> str:
    """Wo die Einstellungen liegen - nie im Programmordner."""
    basis = os.environ.get("APPDATA") or os.path.expanduser("~")
    ordner = os.path.join(basis, "Scrinium")
    os.makedirs(ordner, exist_ok=True)
    return ordner


def config_pfad() -> str:
    return os.path.join(config_ordner(), CONFIG_NAME)


# ---------------------------------------------------------------------------
# Standardwerte
# ---------------------------------------------------------------------------
@dataclass
class Einstellungen:
    """Alles, was man einstellen kann."""

    sprache: str = "de"

    # Werkzeuge: welche sind an? Key ist die Werkzeug-id (z.B. "downloadsorter")
    werkzeuge_an: dict = field(default_factory=dict)

    # Was der Downloadsorter braucht (darf er selbst fuehren)
    downloads_ordner: str = ""
    downloads_minute: int = 30
    downloads_bei_neuen_dateien: bool = True
    downloads_min_age: int = 30

    @classmethod
    def standard(cls) -> "Einstellungen":
        """Standardwerte inkl. Default-Download-Ordner."""
        e = cls()
        e.downloads_ordner = _standard_downloads()
        return e

    def werkzeug_ist_an(self, wid: str) -> bool:
        """Standard: an. Man muss nur ausschalten, was man nicht will."""
        return bool(self.werkzeuge_an.get(wid, True))

    def werkzeug_schalten(self, wid: str, an: bool) -> None:
        self.werkzeuge_an[wid] = an

    # -----------------------------------------------------------------
    def speichern(self) -> str:
        """Schreibt die Einstellungen - aber nie halb."""
        daten = asdict(self)
        text = json.dumps(daten, indent=2, ensure_ascii=False) + "\n"

        # Erst in eine Tempdatei, dann umbenennen. Sonst kann ein Stromausfall
        # mitten im Schreiben die ganze config.json zerstoeren.
        ziel = config_pfad()
        fd, tmp = tempfile.mkstemp(prefix=".scrinium_", dir=os.path.dirname(ziel))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            os.replace(tmp, ziel)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        return ziel

    @classmethod
    def laden(cls) -> "Einstellungen":
        """Liest die Einstellungen. Fehler sind nie fatal."""
        standard = cls.standard()
        try:
            with open(config_pfad(), "r", encoding="utf-8") as fh:
                daten = json.load(fh)
        except (OSError, ValueError):
            return standard

        if not isinstance(daten, dict):
            return standard

        for feld_name in standard.__dataclass_fields__:
            if feld_name in daten:
                wert = daten[feld_name]
                aktuell = getattr(standard, feld_name)
                # Typ pruefen: bool ist ein specialer int in Python
                if isinstance(aktuell, bool):
                    if isinstance(wert, bool):
                        setattr(standard, feld_name, wert)
                elif isinstance(aktuell, int):
                    try:
                        setattr(standard, feld_name, int(wert))
                    except (TypeError, ValueError):
                        pass
                elif isinstance(aktuell, dict):
                    if isinstance(wert, dict):
                        setattr(standard, feld_name, wert)
                elif isinstance(aktuell, str):
                    if isinstance(wert, str):
                        setattr(standard, feld_name, wert)
        return standard


def _standard_downloads() -> str:
    """Wo ist der Download-Ordner?

    Gefragt wird Windows, weil der Ordner bei OneDrive-CONTACTS woanders
    liegen kann als unter C:\\Users\\...\\Downloads.
    """
    # 1) Windows fragen (funktioniert auch mit OneDrive-Umleitung)
    try:
        import winreg

        schluessel = (r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion"
                      r"\\Explorer\\Shell Folders")
        downloads_id = "{374DE290-123F-4565-9164-39C4925E467B}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, schluessel) as k:
            wert, _ = winreg.QueryValueEx(k, downloads_id)
            if wert and os.path.isdir(wert):
                return wert.replace("\\", "/")
    except Exception:
        pass

    # 2) Der normale Weg
    kandidat = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.isdir(kandidat):
        return kandidat.replace("\\", "/")

    # 3) OneDrive
    for var in ("OneDrive", "OneDriveConsumer"):
        basis = os.environ.get(var)
        if basis:
            kandidat = os.path.join(basis, "Downloads")
            if os.path.isdir(kandidat):
                return kandidat.replace("\\", "/")

    return kandidat.replace("\\", "/")