"""Scrinium-Settings.

Zwei Sorten Dinge, die man trennen muss:

1.  **Was der Nutzer eingestellt hat** (welcher Download-Ordner, welche
    Sprache, welche Tools sind an) -> `config.json`
2.  **Wo Scrinium liegt** -> wird nie gespeichert, sondern jedes Mal neu
    aus dem Programmordner berechnet

Punkt 2 ist wichtig: Scrinium darf keinen festen Pfad speichern. Wenn du
den Ordner nach `D:\\Programme\\Scrinium` kopierst, muss alles weiter
funktionieren.

Die config.json liegt in `%APPDATA%\\Scrinium\\`, weil man in
`C:\\Programme\\` nicht schreiben darf. Das Programm ist umziehbar, die
Settings bleiben.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field, asdict

from .core import base_dir

CONFIG_NAME = "config.json"


def config_dir() -> str:
    """Wo die Settings liegen - nie im Programmordner."""
    basis = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(basis, "Scrinium")
    os.makedirs(folder, exist_ok=True)
    return folder


def config_path() -> str:
    return os.path.join(config_dir(), CONFIG_NAME)


# ---------------------------------------------------------------------------
# Standardwerte
# ---------------------------------------------------------------------------
@dataclass
class Settings:
    """Alles, was man einstellen kann."""

    language: str = "de"

    # Tools: welche sind an? Key ist die Tool-id (z.B. "downloadsorter")
    tools_enabled: dict = field(default_factory=dict)

    # Was der Downloadsorter braucht (darf er selbst fuehren)
    downloads_folder: str = ""
    downloads_interval: int = 30
    downloads_on_new_files: bool = True
    downloads_min_age: int = 30

    # Eigene Sortierregeln. Zwei Formen, beide benutzt der Sortierer:
    #   {"art": "endung", "wert": ".xyz", "ziel": "Dokumente"}
    #   {"art": "muster", "wert": "rechnung*", "ziel": "Dokumente"}
    # `ziel` ist ein Ordnername wie "Dokumente" - nie uebersetzt.
    sortier_regeln: list = field(default_factory=list)

    # Werkzeuge, die der Nutzer selbst hinzugefuegt hat. Das sind Pfade
    # auf Ordner mit einem __init__.py neben dem Programm - nicht auf
    # Dateien im Internet.
    eigene_werkzeuge: list = field(default_factory=list)

    @classmethod
    def standard(cls) -> "Settings":
        """Standardwerte inkl. Default-Download-Ordner."""
        e = cls()
        e.downloads_folder = _standard_downloads()
        return e

    def tool_is_enabled(self, wid: str) -> bool:
        """Standard: an. Man muss nur ausschalten, was man nicht will."""
        return bool(self.tools_enabled.get(wid, True))

    def toggle_tool(self, wid: str, an: bool) -> None:
        self.tools_enabled[wid] = an

    # -----------------------------------------------------------------
    # eigene Regeln
    # -----------------------------------------------------------------
    def regel_hinzufuegen(self, art: str, wert: str, ziel: str) -> dict | None:
        """Nimmt eine Regel auf. Gibt sie zurueck oder None bei Unsinn.

        `art` ist "endung" oder "muster". Beides wird auf Kleinbuchstaben
        und ohne fuehrenden Punkt gebracht - sonst findet der Sortierer
        seine eigene Regel nicht wieder.
        """
        art = str(art or "").strip().lower()
        wert = str(wert or "").strip().lower()
        ziel = str(ziel or "").strip()

        if art not in ("endung", "muster"):
            return None
        if not wert or not ziel:
            return None
        if art == "endung" and not wert.startswith("."):
            wert = "." + wert

        # Doppelte Regel nicht zweimal aufnehmen
        for r in self.sortier_regeln:
            if r.get("art") == art and r.get("wert") == wert:
                return r

        regel = {"art": art, "wert": wert, "ziel": ziel}
        self.sortier_regeln.append(regel)
        return regel

    def regel_entfernen(self, art: str, wert: str) -> bool:
        art = str(art or "").strip().lower()
        wert = str(wert or "").strip().lower()
        if art == "endung" and not wert.startswith("."):
            wert = "." + wert
        vorher = len(self.sortier_regeln)
        self.sortier_regeln = [r for r in self.sortier_regeln
                               if not (r.get("art") == art
                                       and r.get("wert") == wert)]
        return len(self.sortier_regeln) != vorher

    # -----------------------------------------------------------------
    # eigene Werkzeuge
    # -----------------------------------------------------------------
    def werkzeug_hinzufuegen(self, pfad: str) -> str:
        """Nimmt einen Werkzeugordner auf. Gibt eine Meldung zurueck.

        Geprueft wird, ob dort wirklich ein Werkzeug liegt: ein Ordner
        mit `__init__.py`, das eine Startfunktion hat. Die darf `starte`
        (der Name im Rahmenvertrag) oder `start` heissen - beides kam
        vor, und nur eines davon zu akzeptieren wuerde echte
        Werkzeuge abweisen.
        """
        pfad = str(pfad or "").strip()
        if not pfad:
            # os.path.abspath("") liefert das Arbeitsverzeichnis - ein
            # leerer Name wuerde also wie ein gueltiger Ordner aussehen.
            return "ORDNER FEHLT"
        pfad = os.path.abspath(pfad)
        if not os.path.isdir(pfad):
            return "ORDNER FEHLT"
        init = os.path.join(pfad, "__init__.py")
        if not os.path.isfile(init):
            return "KEIN WERKZEUG"

        try:
            with open(init, "r", encoding="utf-8") as fh:
                quelle = fh.read()
        except OSError:
            return "NICHT LESBAR"

        # "starte?" matcht start und starte in einem Muster. Nur ein
        # davon zu akzeptieren wuerde echte Werkzeuge abweisen.
        if not re.search(r"^\s*def\s+starte?\s*\(", quelle, re.M):
            return "KEIN WERKZEUG"
        if not re.search(r"^\s*NAME\s*=", quelle, re.M):
            return "KEIN WERKZEUG"

        # Schon drin? Dann nichts doppelt eintragen.
        for eintrag in self.eigene_werkzeuge:
            if os.path.normcase(os.path.abspath(eintrag["pfad"])) == \
               os.path.normcase(pfad):
                return "SCHON DABEI"

        name = os.path.basename(pfad.rstrip("\\/")).lstrip("_")
        self.eigene_werkzeuge.append({"pfad": pfad, "name": name,
                                      "quelle": "nutzer"})
        return "OK"

    def werkzeug_entfernen(self, pfad: str) -> bool:
        pfad = os.path.abspath(str(pfad or "").strip())
        vorher = len(self.eigene_werkzeuge)
        self.eigene_werkzeuge = [e for e in self.eigene_werkzeuge
                                 if os.path.normcase(
                                     os.path.abspath(e["pfad"]))
                                 != os.path.normcase(pfad)]
        return len(self.eigene_werkzeuge) != vorher

    # -----------------------------------------------------------------
    def speichern(self) -> str:
        """Schreibt die Settings - aber nie halb."""
        data = asdict(self)
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

        # Erst in eine Tempdatei, dann umbenennen. Sonst kann ein Stromausfall
        # mitten im Schreiben die ganze config.json zerstoeren.
        ziel = config_path()
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
    def laden(cls) -> "Settings":
        """Liest die Settings. Fehler sind nie fatal."""
        standard = cls.standard()
        try:
            with open(config_path(), "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return standard

        if not isinstance(data, dict):
            return standard

        for feld_name in standard.__dataclass_fields__:
            if feld_name in data:
                wert = data[feld_name]
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
                elif isinstance(aktuell, list):
                    # Ohne diesen Zweig wurden sortier_regeln und
                    # eigene_werkzeuge beim Neuladen kommentarlos
                    # verworfen.
                    if isinstance(wert, list):
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

        key = (r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion"
                      r"\\Explorer\\Shell Folders")
        downloads_id = "{374DE290-123F-4565-9164-39C4925E467B}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
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