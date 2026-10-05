"""Die eigentliche Sortier-Logik.

Hier passiert die Arbeit. Das Tool (`../__init__.py`) ist nur die
Schnittstelle zum Scrinium-Rahmen; die Entscheidungen fallen hier.

Wichtig: Das ist ein *eigenstaendiges* Modul. Es kennt Scrinium nicht und
braucht es nicht - dadurch kann man es ohne den Rahmen testen.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field

# Der Kern darf von hier aus importiert werden, muss aber nicht: dieses
# Modul laesst sich auch ohne Scrinium aufrufen.
_HIER = os.path.dirname(os.path.abspath(__file__))
_WURZEL = os.path.dirname(os.path.dirname(_HIER))
if _WURZEL not in sys.path:
    sys.path.insert(0, _WURZEL)


# ---------------------------------------------------------------------------
# Kategorien: welche Endung gehoert wohin
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Category:
    name: str
    folder: str
    endungen: tuple


CATEGORIES: tuple = (
    Category("Bilder", "Bilder",
              ("jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "tif", "tiff",
               "heic", "avif", "ico", "raw", "cr2", "nef", "arw", "dng")),
    Category("Videos", "Videos",
              ("mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "mpeg", "mpg",
               "m4v", "3gp", "vob", "mts", "m2ts")),
    Category("Musik", "Musik",
              ("mp3", "wav", "flac", "aac", "ogg", "m4a", "opus", "wma", "alac")),
    Category("Dokumente", "Dokumente",
              ("pdf", "doc", "docx", "odt", "rtf", "txt", "md", "xls", "xlsx",
               "ppt", "pptx", "csv", "pages")),
    Category("Archive", "Archive",
              ("zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso", "cab")),
    Category("Programme", "Programme",
              ("exe", "msi", "bat", "cmd", "ps1", "apk", "deb", "rpm", "jar")),
    Category("Code", "Code",
              ("py", "js", "ts", "html", "css", "json", "yaml", "yml", "toml",
               "c", "cpp", "h", "java", "go", "rs", "php", "rb", "sh")),
    Category("Schriften", "Schriften",
              ("ttf", "otf", "woff", "woff2", "eot")),
)

EXT_TO_CATEGORY: dict = {}
for _kat in CATEGORIES:
    for _endung in _kat.endungen:
        EXT_TO_CATEGORY.setdefault(_endung, _kat)

# Dateien, die nie angefasst werden: noch nicht fertig geladene oder
# gerade in Benutzung.
INCOMPLETE = (".crdownload", ".part", ".partial", ".tmp", ".download", ".opdownload")
PROTECTED = ("desktop.ini", "thumbs.db", ".ds_store")


# ---------------------------------------------------------------------------
# Ein Plan: was wuerde passieren
# ---------------------------------------------------------------------------
@dataclass
class FilePlan:
    quelle: str
    ziel: str
    kategorie: str
    size: int
    renamed: bool = False


@dataclass
class Plan:
    folder: str
    dateien: list = field(default_factory=list)     # FilePlan
    skipped: list = field(default_factory=list)  # (name, grund)

    @property
    def anzahl(self) -> int:
        return len(self.dateien)

    @property
    def bytes(self) -> int:
        return sum(d.size for d in self.dateien)


@dataclass
class Run:
    run_id: str
    wann: float
    moved: list = field(default_factory=list)   # (quelle, ziel)
    fehler: str = ""


# ---------------------------------------------------------------------------
# Settings (kommen vom Scrinium-Rahmen, sonst Standard)
# ---------------------------------------------------------------------------
def settings():
    """Die aktuellen Settings - aus dem Rahmen oder als Standard."""
    try:
        from scrinium import settings as rahmen
        return rahmen.Settings.laden()
    except Exception:
        @dataclass
        class _Standard:
            downloads_folder: str = os.path.join(os.path.expanduser("~"), "Downloads")
            downloads_min_age: int = 30
            downloads_on_new_files: bool = True
        return _Standard()


# ---------------------------------------------------------------------------
# Die Entscheidung: welche Datei kommt wohin
# ---------------------------------------------------------------------------
def category_for(filename: str):
    """Gibt die Kategorie zurueck, oder None wenn unbekannt."""
    if filename.lower() in PROTECTED:
        return None
    endung = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if endung:
        return EXT_TO_CATEGORY.get(endung)
    # Screenshot ohne brauchbare Endung?
    if "screenshot" in filename.lower() or "bildschirmfoto" in filename.lower():
        return CATEGORIES[0]
    return None


def is_incomplete(filename: str) -> bool:
    niedrig = filename.lower()
    return any(niedrig.endswith(u) for u in INCOMPLETE)


def is_too_new(path: str, min_age: int) -> tuple:
    """Zu neu? Dann nicht anfassen - sonst verschiebt man halbe Dateien."""
    try:
        alter = time.time() - os.path.getmtime(path)
    except OSError:
        return False, "nicht lesbar"
    if alter < min_age:
        return False, f"zu neu ({int(alter)}s)"
    return True, ""


def check_folder(folder: str) -> tuple:
    """Kann ueberhaupt gearbeitet werden?"""
    if not folder:
        return False, "kein Ordner eingestellt"
    if not os.path.isdir(folder):
        return False, f"Ordner nicht gefunden: {folder}"
    if not os.access(folder, os.W_OK):
        return False, f"Kein Schreibzugriff: {folder}"
    return True, ""


# ---------------------------------------------------------------------------
# PLANEN - veraendert NICHTS
# ---------------------------------------------------------------------------
def plan_folder(folder: str, cfg=None) -> Plan | None:
    """Sagt voraus, was passieren wuerde. Bewegt keine Datei.

    Das ist der wichtigste Teil: erst nachsehen, dann tun. So kann nie
    etwas schiefgehen, ohne dass es vorher sichtbar war.
    """
    cfg = cfg or settings()
    min_age = getattr(cfg, "downloads_min_age", 30)

    plan = Plan(folder=folder)
    if not folder or not os.path.isdir(folder):
        return plan

    try:
        namen = sorted(os.listdir(folder))
    except OSError as exc:
        plan.skipped.append(("(folder)", str(exc)))
        return plan

    belegt: set = set()

    for name in namen:
        path = os.path.join(folder, name)

        if not os.path.isfile(path):
            continue
        if is_incomplete(name):
            plan.skipped.append((name, "Download laeuft noch"))
            continue

        alt, grund = is_too_new(path, min_age)
        if not alt:
            plan.skipped.append((name, grund))
            continue

        kategorie = category_for(name)
        if kategorie is None:
            plan.skipped.append((name, "keine Kategorie"))
            continue

        ziel = os.path.join(folder, kategorie.folder, name)
        renamed = False
        if os.path.exists(ziel):
            ziel, renamed = _free_name(ziel)

        # Zwei Dateien mit gleichem Namen in einem Run: das zweite
        # bekommt einen anderen Zielnamen.
        key = os.path.normcase(os.path.abspath(ziel))
        if key in belegt:
            ziel, renamed = _free_name(ziel, _zaehler=2)
        belegt.add(os.path.normcase(os.path.abspath(ziel)))

        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0

        plan.dateien.append(FilePlan(
            quelle=os.path.abspath(path),
            ziel=os.path.abspath(ziel),
            kategorie=kategorie.name,
            size=size,
            renamed=renamed,
        ))

    return plan


def _free_name(path: str, _zaehler: int = 1) -> tuple:
    """Findet einen Namen, den es noch nicht gibt: foto_01.jpg, foto_02..."""
    stamm, endung = os.path.splitext(path)
    i = _zaehler
    while os.path.exists(f"{stamm}_{i:02d}{endung}"):
        i += 1
    return f"{stamm}_{i:02d}{endung}", True


# ---------------------------------------------------------------------------
# ANWENDEN - jetzt wird wirklich moved
# ---------------------------------------------------------------------------
def apply_plan(plan: Plan) -> Run:
    """Führt den Plan aus."""
    lauf = Run(run_id=_run_id(), wann=time.time())

    if plan is None or not plan.dateien:
        return lauf

    for datei in plan.dateien:
        try:
            os.makedirs(os.path.dirname(datei.ziel), exist_ok=True)
            os.replace(datei.quelle, datei.ziel)
            lauf.moved.append((datei.quelle, datei.ziel))
        except Exception as exc:
            # Ein Fehler stoppt nichts - die anderen Dateien gehen weiter.
            lauf.fehler = str(exc)

    _lauf_speichern(lauf)
    return lauf


def _run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


# ---------------------------------------------------------------------------
# Verlauf / Rueckgaengig
# ---------------------------------------------------------------------------
def _history_file() -> str:
    from scrinium import settings as rahmen
    folder = rahmen.config_dir()
    return os.path.join(folder, "laeufe.json")


def _lauf_speichern(lauf: Run) -> None:
    """Schreibt den Run in die Liste, damit man ihn undo machen kann."""
    import json

    datei = _history_file()
    laeufe = list_runs(500)

    laeufe.append({
        "run_id": lauf.run_id,
        "wann": lauf.wann,
        "moved": [[q, z] for q, z in lauf.moved],
        "fehler": lauf.fehler,
    })

    try:
        with open(datei, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(laeufe[-500:], fh, indent=1, ensure_ascii=False)
    except OSError:
        pass


def list_runs(max_anzahl: int = 20) -> list:
    """Die letzten Laeufe, neueste zuerst."""
    import json

    try:
        with open(_history_file(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            return list(reversed(data[-max_anzahl:]))
    except (OSError, ValueError):
        pass
    return []


def last_run() -> Run | None:
    """Der letzte Run, oder None."""
    alle = list_runs(1)
    if not alle:
        return None
    d = alle[0]
    return Run(run_id=d.get("run_id", ""), wann=d.get("wann", 0),
                moved=[tuple(x) for x in d.get("moved", [])],
                fehler=d.get("fehler", ""))


def undo_run(run_id: str) -> tuple:
    """Verschiebt alle Dateien eines Laufs zurueck.

    Gibt (anzahl, fehlerliste) zurueck. Die leeren Ordner, die dadurch
    entstehen, werden wieder entfernt - sonst sammeln sie sich mit der Zeit.
    """
    import shutil

    for eintrag in list_runs(1000):
        if eintrag.get("run_id") != run_id:
            continue

        anzahl = 0
        fehler = []
        ordner_zum_aufraeumen = set()

        for quelle, ziel in reversed(eintrag.get("moved", [])):
            if not os.path.exists(ziel):
                fehler.append(f"nicht mehr da: {os.path.basename(ziel)}")
                continue
            try:
                os.makedirs(os.path.dirname(quelle), exist_ok=True)
                ziel_quelle = quelle
                if os.path.exists(quelle):
                    stamm, endung = os.path.splitext(quelle)
                    i = 1
                    while os.path.exists(ziel_quelle):
                        ziel_quelle = f"{stamm}_zurueck{i:02d}{endung}"
                        i += 1
                shutil.move(ziel, ziel_quelle)
                ordner_zum_aufraeumen.add(os.path.dirname(ziel))
                anzahl += 1
            except Exception as exc:
                fehler.append(f"{os.path.basename(ziel)}: {exc}")

        # Leere Ordner wegraeumen, aber nur die, die wir selbst angelegt haben
        for folder in ordner_zum_aufraeumen:
            try:
                if os.path.isdir(folder) and not os.listdir(folder):
                    os.rmdir(folder)
            except OSError:
                pass

        _lauf_markieren(run_id)
        return anzahl, fehler

    return 0, [f"Unbekannter Run: {run_id}"]


def _lauf_markieren(run_id: str) -> None:
    import json

    datei = _history_file()
    try:
        with open(datei, "r", encoding="utf-8") as fh:
            laeufe = json.load(fh)
        for eintrag in laeufe:
            if eintrag.get("run_id") == run_id:
                eintrag["undo"] = True
        with open(datei, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(laeufe, fh, indent=1, ensure_ascii=False)
    except (OSError, ValueError):
        pass