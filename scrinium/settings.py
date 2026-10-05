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