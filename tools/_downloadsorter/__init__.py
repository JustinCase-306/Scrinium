"""Downloads-Sortierer - das erste Scrinium-Tool.

Ein Tool ist nicht mehr als diese Datei plus die Ordner daneben. Der
Kern (`scrinium/core.py`) laedt diese Datei und ruft `check()` und
`starte()`. Er weiss nicht, dass es hier um Dateien und Ordner geht.

Die eigentliche Sortier-Logik liegt nicht hier, sondern in
`logik/regeln.py` - genau wie ein echtes Programm. Diese Datei ist nur die
Schnittstelle zum Scrinium-Rahmen.

Was `starte()` zurueckgibt, hat immer dieselbe Form:

    {"text": "...", "actions": [...], "data": {...}}
"""

from __future__ import annotations

import os
import sys

# Damit das Tool seine eigene Dateien findet, egal von wo es gestartet
# wurde - der Rahmen setzt das, aber hier noch einmal als Absicherung.
_HIER = os.path.dirname(os.path.abspath(__file__))
if _HIER not in sys.path:
    sys.path.insert(0, _HIER)

from logik.regeln import (                    # noqa: E402
    plan_folder,
    apply_plan,
    settings,
    list_runs,
    last_run,
    undo_run,
    Run,
)

# Alles, was der Kern zum Finden braucht:
NAME = "Downloads-Sortierer"
BETA = False


# ---------------------------------------------------------------------------
# Der Vertrag
# ---------------------------------------------------------------------------
def check() -> tuple:
    """Darf der Sortierer starten?

    Wird aufgerufen, BEVOR der Nutzer auf "Starten" klickt - auch beim
    Programmstart, um den Zustand anzuzeigen.
    """
    folder = settings().downloads_folder
    if not folder:
        return False, spr("downloadsorter.kein_ordner")
    if not os.path.isdir(folder):
        return False, spr("downloadsorter.ordner_fehlt", folder=folder)
    return True, ""


def starte() -> dict:
    """Sortiert einmal.

    Keine Argumente - die Settings kommen aus dem Tool selbst. Das
    ist Absicht: der Rahmen soll nicht bestimmen, WIE ein Tool arbeitet.
    """
    ok, grund = check()
    if not ok:
        return {"text": grund, "actions": [], "data": {}, "fehler": True}

    folder = settings().downloads_folder
    plan = plan_folder(folder, settings())
    if not plan or not plan.dateien:
        return {
            "text": spr("downloadsorter.keine_dateien"),
            "actions": [],
            "data": {"skipped": len(plan.skipped) if plan else 0},
        }

    lauf = apply_plan(plan)
    if lauf.fehler:
        return {
            "text": spr("fehler.allgemein", grund=lauf.fehler),
            "actions": [], "data": {}, "fehler": True,
        }

    # Was zurueckkommt, kann der Rahmen ohne Vorwissen anzeigen.
    text = spr("downloadsorter.fertig", anzahl=len(lauf.moved))

    actions = []
    if lauf.run_id:
        actions.append((spr("downloadsorter.rueckgaengig"), lauf.run_id))

    return {
        "text": text,
        "actions": actions,
        "data": {
            "moved": len(lauf.moved),
            "skipped": len(plan.skipped),
            "folder": folder,
            "run_id": lauf.run_id,
        },
    }


def preview() -> dict:
    """Was wuerde passieren? Bewegt nichts.

    Die Oberflaeche zeigt das als Liste an, bevor der Nutzer auf
    "Jetzt sortieren" klickt. Das ist derselbe Plan wie in `starte()` -
    nur eben nicht ausgefuehrt.
    """
    ok, grund = check()
    if not ok:
        return {"dateien": [], "geprueft": 0, "fehler": grund}

    plan = plan_folder(settings().downloads_folder, settings())
    if not plan:
        return {"dateien": [], "geprueft": 0}

    dateien = []
    for path in plan.dateien:
        name = os.path.basename(path.quelle)
        ziel_ordner = ""
        try:
            ziel_ordner = os.path.basename(os.path.dirname(path.ziel))
        except OSError:
            pass
        dateien.append({
            "name": name,
            "ziel": ziel_ordner,
            "grund": "",
            "size": path.size,
        })

    # Was liegen bleibt, gehoert auch in die Vorschau - sonst denkt der
    # Nutzer, die Datei sei verschwunden.
    for name, grund in plan.skipped:
        if name.startswith("("):
            continue
        dateien.append({
            "name": name, "ziel": "", "grund": grund, "size": 0,
        })

    return {"dateien": dateien, "geprueft": len(dateien),
            "moved": len(plan.dateien),
            "skipped": len(plan.skipped)}


def run_action(kennung: str) -> dict:
    """Fuehrt eine zuvor angebotene Aktion aus.

    Der Rahmen schickt nur die Kennung zurueck, die das Tool selbst
    vergeben hat - er weiss nicht, was "Rueckgaengig" bedeutet. Eine
    unbekannte Kennung ist ein Fehler, kein stiller Erfolg.
    """
    lauf = last_run()
    if lauf is None or lauf.run_id != kennung:
        return {"text": "Dieser Run laesst sich nicht mehr rueckgaengig machen.",
                "actions": [], "data": {}, "fehler": True}

    anzahl, fehler = undo_run(kennung)
    return {
        "text": spr("downloadsorter.zurueck_fertig", anzahl=anzahl),
        "actions": [],
        "data": {"restored": anzahl, "errors": fehler},
    }


def spr(key: str, **platzhalter) -> str:
    """Ein Text in der eingestellten Sprache.

    Der Weg running ueber den Kern - aber nur, wenn es einer ist. Sonst
    nehmen wir Deutsch, damit das Tool auch einzeln lauffaehig ist.
    """
    try:
        from scrinium import texts
        return texts.sag(key, **platzhalter)
    except Exception:
        return f'<{key}>'   # ohne Rahmen: Schluessel zeigen


# ---------------------------------------------------------------------------
# Was das Tool sonst noch kann (der Rahmen ruft nichts davon automatisch)
# ---------------------------------------------------------------------------
def verlauf(anzahl: int = 20) -> list:
    """Die letzten Laeufe, fuer eine Verlaufs-Ansicht."""
    return list_runs(anzahl)


def last_action() -> Run | None:
    """Der letzte Run, fuer einen Undo-Knopf."""
    return last_run()


def undo(run_id: str) -> dict:
    """Macht einen Run undo - gleiches Format wie `starte()`."""
    anzahl, fehler = undo_run(run_id)
    return {
        "text": spr("downloadsorter.zurueck_fertig", anzahl=anzahl),
        "actions": [],
        "data": {"restored": anzahl, "errors": fehler},
    }


if __name__ == "__main__":
    # So laesst sich das Tool auch einzeln aufrufen:
    #     python tools\_downloadsorter\__init__.py
    import json

    ok, grund = check()
    result = starte() if ok else {"text": grund, "actions": [], "data": {}}
    print(json.dumps({"ok": ok, "grund": grund, "result": result},
                     indent=2, ensure_ascii=False))