"""Die eigentliche Sortier-Logik.

Hier passiert die Arbeit. Das Werkzeug (`../__init__.py`) ist nur die
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
class Kategorie:
    name: str
    ordner: str
    endungen: tuple


KATEGORIEN: tuple = (
    Kategorie("Bilder", "Bilder",
              ("jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "tif", "tiff",
               "heic", "avif", "ico", "raw", "cr2", "nef", "arw", "dng")),
    Kategorie("Videos", "Videos",
              ("mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "mpeg", "mpg",
               "m4v", "3gp", "vob", "mts", "m2ts")),
    Kategorie("Musik", "Musik",
              ("mp3", "wav", "flac", "aac", "ogg", "m4a", "opus", "wma", "alac")),
    Kategorie("Dokumente", "Dokumente",
              ("pdf", "doc", "docx", "odt", "rtf", "txt", "md", "xls", "xlsx",
               "ppt", "pptx", "csv", "pages")),
    Kategorie("Archive", "Archive",
              ("zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso", "cab")),
    Kategorie("Programme", "Programme",
              ("exe", "msi", "bat", "cmd", "ps1", "apk", "deb", "rpm", "jar")),
    Kategorie("Code", "Code",
              ("py", "js", "ts", "html", "css", "json", "yaml", "yml", "toml",
               "c", "cpp", "h", "java", "go", "rs", "php", "rb", "sh")),
    Kategorie("Schriften", "Schriften",
              ("ttf", "otf", "woff", "woff2", "eot")),
)

ENDUNG_ZU_KATEGORIE: dict = {}
for _kat in KATEGORIEN:
    for _endung in _kat.endungen:
        ENDUNG_ZU_KATEGORIE.setdefault(_endung, _kat)

# Dateien, die nie angefasst werden: noch nicht fertig geladene oder
# gerade in Benutzung.
UNVOLLSTAENDIG = (".crdownload", ".part", ".partial", ".tmp", ".download", ".opdownload")
GESCHUETZT = ("desktop.ini", "thumbs.db", ".ds_store")


# ---------------------------------------------------------------------------
# Ein Plan: was wuerde passieren
# ---------------------------------------------------------------------------
@dataclass
class DateiPlan:
    quelle: str
    ziel: str
    kategorie: str
    groesse: int
    umbenannt: bool = False


@dataclass
class Plan:
    ordner: str
    dateien: list = field(default_factory=list)     # DateiPlan
    uebersprungen: list = field(default_factory=list)  # (name, grund)

    @property
    def anzahl(self) -> int:
        return len(self.dateien)

    @property
    def bytes(self) -> int:
        return sum(d.groesse for d in self.dateien)


@dataclass
class Lauf:
    run_id: str
    wann: float
    verschoben: list = field(default_factory=list)   # (quelle, ziel)
    fehler: str = ""


# ---------------------------------------------------------------------------
# Einstellungen (kommen vom Scrinium-Rahmen, sonst Standard)
# ---------------------------------------------------------------------------
def einstellungen():
    """Die aktuellen Einstellungen - aus dem Rahmen oder als Standard."""
    try:
        from scrinium import einstellungen as rahmen
        return rahmen.Einstellungen.laden()
    except Exception:
        @dataclass
        class _Standard:
            downloads_ordner: str = os.path.join(os.path.expanduser("~"), "Downloads")
            downloads_min_age: int = 30
            downloads_bei_neuen_dateien: bool = True
        return _Standard()


# ---------------------------------------------------------------------------
# Die Entscheidung: welche Datei kommt wohin
# ---------------------------------------------------------------------------
def kategorie_fuer(dateiname: str):
    """Gibt die Kategorie zurueck, oder None wenn unbekannt."""
    if dateiname.lower() in GESCHUETZT:
        return None
    endung = dateiname.rsplit(".", 1)[-1].lower() if "." in dateiname else ""
    if endung:
        return ENDUNG_ZU_KATEGORIE.get(endung)
    # Screenshot ohne brauchbare Endung?
    if "screenshot" in dateiname.lower() or "bildschirmfoto" in dateiname.lower():
        return KATEGORIEN[0]
    return None


def ist_unvollstaendig(dateiname: str) -> bool:
    niedrig = dateiname.lower()
    return any(niedrig.endswith(u) for u in UNVOLLSTAENDIG)


def ist_zu_alt(pfad: str, min_age: int) -> tuple:
    """Zu neu? Dann nicht anfassen - sonst verschiebt man halbe Dateien."""
    try:
        alter = time.time() - os.path.getmtime(pfad)
    except OSError:
        return False, "nicht lesbar"
    if alter < min_age:
        return False, f"zu neu ({int(alter)}s)"
    return True, ""


def pruefe_ordner(ordner: str) -> tuple:
    """Kann ueberhaupt gearbeitet werden?"""
    if not ordner:
        return False, "kein Ordner eingestellt"
    if not os.path.isdir(ordner):
        return False, f"Ordner nicht gefunden: {ordner}"
    if not os.access(ordner, os.W_OK):
        return False, f"Kein Schreibzugriff: {ordner}"
    return True, ""


# ---------------------------------------------------------------------------
# PLANEN - veraendert NICHTS
# ---------------------------------------------------------------------------
def ordner_planen(ordner: str, cfg=None) -> Plan | None:
    """Sagt voraus, was passieren wuerde. Bewegt keine Datei.

    Das ist der wichtigste Teil: erst nachsehen, dann tun. So kann nie
    etwas schiefgehen, ohne dass es vorher sichtbar war.
    """
    cfg = cfg or einstellungen()
    min_age = getattr(cfg, "downloads_min_age", 30)

    plan = Plan(ordner=ordner)
    if not ordner or not os.path.isdir(ordner):
        return plan

    try:
        namen = sorted(os.listdir(ordner))
    except OSError as exc:
        plan.uebersprungen.append(("(ordner)", str(exc)))
        return plan

    belegt: set = set()

    for name in namen:
        pfad = os.path.join(ordner, name)

        if not os.path.isfile(pfad):
            continue
        if ist_unvollstaendig(name):
            plan.uebersprungen.append((name, "Download laeuft noch"))
            continue

        alt, grund = ist_zu_alt(pfad, min_age)
        if not alt:
            plan.uebersprungen.append((name, grund))
            continue

        kategorie = kategorie_fuer(name)
        if kategorie is None:
            plan.uebersprungen.append((name, "keine Kategorie"))
            continue

        ziel = os.path.join(ordner, kategorie.ordner, name)
        umbenannt = False
        if os.path.exists(ziel):
            ziel, umbenannt = _freier_name(ziel)

        # Zwei Dateien mit gleichem Namen in einem Lauf: das zweite
        # bekommt einen anderen Zielnamen.
        schluessel = os.path.normcase(os.path.abspath(ziel))
        if schluessel in belegt:
            ziel, umbenannt = _freier_name(ziel, _zaehler=2)
        belegt.add(os.path.normcase(os.path.abspath(ziel)))

        try:
            groesse = os.path.getsize(pfad)
        except OSError:
            groesse = 0

        plan.dateien.append(DateiPlan(
            quelle=os.path.abspath(pfad),
            ziel=os.path.abspath(ziel),
            kategorie=kategorie.name,
            groesse=groesse,
            umbenannt=umbenannt,
        ))

    return plan


def _freier_name(pfad: str, _zaehler: int = 1) -> tuple:
    """Findet einen Namen, den es noch nicht gibt: foto_01.jpg, foto_02..."""
    stamm, endung = os.path.splitext(pfad)
    i = _zaehler
    while os.path.exists(f"{stamm}_{i:02d}{endung}"):
        i += 1
    return f"{stamm}_{i:02d}{endung}", True


# ---------------------------------------------------------------------------
# ANWENDEN - jetzt wird wirklich verschoben
# ---------------------------------------------------------------------------
def plan_anwenden(plan: Plan) -> Lauf:
    """Führt den Plan aus."""
    lauf = Lauf(run_id=_run_id(), wann=time.time())

    if plan is None or not plan.dateien:
        return lauf

    for datei in plan.dateien:
        try:
            os.makedirs(os.path.dirname(datei.ziel), exist_ok=True)
            os.replace(datei.quelle, datei.ziel)
            lauf.verschoben.append((datei.quelle, datei.ziel))
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
def _verlauf_datei() -> str:
    from scrinium import einstellungen as rahmen
    ordner = rahmen.config_ordner()
    return os.path.join(ordner, "laeufe.json")


def _lauf_speichern(lauf: Lauf) -> None:
    """Schreibt den Lauf in die Liste, damit man ihn rueckgaengig machen kann."""
    import json

    datei = _verlauf_datei()
    laeufe = laeufe_liste(500)

    laeufe.append({
        "run_id": lauf.run_id,
        "wann": lauf.wann,
        "verschoben": [[q, z] for q, z in lauf.verschoben],
        "fehler": lauf.fehler,
    })

    try:
        with open(datei, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(laeufe[-500:], fh, indent=1, ensure_ascii=False)
    except OSError:
        pass


def laeufe_liste(max_anzahl: int = 20) -> list:
    """Die letzten Laeufe, neueste zuerst."""
    import json

    try:
        with open(_verlauf_datei(), "r", encoding="utf-8") as fh:
            daten = json.load(fh)
        if isinstance(daten, list):
            return list(reversed(daten[-max_anzahl:]))
    except (OSError, ValueError):
        pass
    return []


def letzter_lauf() -> Lauf | None:
    """Der letzte Lauf, oder None."""
    alle = laeufe_liste(1)
    if not alle:
        return None
    d = alle[0]
    return Lauf(run_id=d.get("run_id", ""), wann=d.get("wann", 0),
                verschoben=[tuple(x) for x in d.get("verschoben", [])],
                fehler=d.get("fehler", ""))


def lauf_rueckgaengig(run_id: str) -> tuple:
    """Verschiebt alle Dateien eines Laufs zurueck.

    Gibt (anzahl, fehlerliste) zurueck. Die leeren Ordner, die dadurch
    entstehen, werden wieder entfernt - sonst sammeln sie sich mit der Zeit.
    """
    import shutil

    for eintrag in laeufe_liste(1000):
        if eintrag.get("run_id") != run_id:
            continue

        anzahl = 0
        fehler = []
        ordner_zum_aufraeumen = set()

        for quelle, ziel in reversed(eintrag.get("verschoben", [])):
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
        for ordner in ordner_zum_aufraeumen:
            try:
                if os.path.isdir(ordner) and not os.listdir(ordner):
                    os.rmdir(ordner)
            except OSError:
                pass

        _lauf_markieren(run_id)
        return anzahl, fehler

    return 0, [f"Unbekannter Lauf: {run_id}"]


def _lauf_markieren(run_id: str) -> None:
    import json

    datei = _verlauf_datei()
    try:
        with open(datei, "r", encoding="utf-8") as fh:
            laeufe = json.load(fh)
        for eintrag in laeufe:
            if eintrag.get("run_id") == run_id:
                eintrag["rueckgaengig"] = True
        with open(datei, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(laeufe, fh, indent=1, ensure_ascii=False)
    except (OSError, ValueError):
        pass