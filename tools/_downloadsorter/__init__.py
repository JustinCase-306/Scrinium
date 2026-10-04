"""Downloads-Sortierer - das erste Scrinium-Werkzeug.

Ein Werkzeug ist nicht mehr als diese Datei plus die Ordner daneben. Der
Kern (`scrinium/kern.py`) laedt diese Datei und ruft `pruefe()` und
`starte()`. Er weiss nicht, dass es hier um Dateien und Ordner geht.

Die eigentliche Sortier-Logik liegt nicht hier, sondern in
`logik/regeln.py` - genau wie ein echtes Programm. Diese Datei ist nur die
Schnittstelle zum Scrinium-Rahmen.

Was `starte()` zurueckgibt, hat immer dieselbe Form:

    {"text": "...", "aktionen": [...], "daten": {...}}
"""

from __future__ import annotations

import os
import sys

# Damit das Werkzeug seine eigene Dateien findet, egal von wo es gestartet
# wurde - der Rahmen setzt das, aber hier noch einmal als Absicherung.
_HIER = os.path.dirname(os.path.abspath(__file__))
if _HIER not in sys.path:
    sys.path.insert(0, _HIER)

from logik.regeln import (                    # noqa: E402
    ordner_planen,
    plan_anwenden,
    einstellungen,
    laeufe_liste,
    letzter_lauf,
    lauf_rueckgaengig,
    Lauf,
)

# Alles, was der Kern zum Finden braucht:
NAME = "Downloads-Sortierer"
BETA = False


# ---------------------------------------------------------------------------
# Der Vertrag
# ---------------------------------------------------------------------------
def pruefe() -> tuple:
    """Darf der Sortierer starten?

    Wird aufgerufen, BEVOR der Nutzer auf "Starten" klickt - auch beim
    Programmstart, um den Zustand anzuzeigen.
    """
    ordner = einstellungen().downloads_ordner
    if not ordner:
        return False, spr("downloadsorter.kein_ordner")
    if not os.path.isdir(ordner):
        return False, spr("downloadsorter.ordner_fehlt", ordner=ordner)
    return True, ""


def starte() -> dict:
    """Sortiert einmal.

    Keine Argumente - die Einstellungen kommen aus dem Werkzeug selbst. Das
    ist Absicht: der Rahmen soll nicht bestimmen, WIE ein Werkzeug arbeitet.
    """
    ok, grund = pruefe()
    if not ok:
        return {"text": grund, "aktionen": [], "daten": {}, "fehler": True}

    ordner = einstellungen().downloads_ordner
    plan = ordner_planen(ordner, einstellungen())
    if not plan or not plan.dateien:
        return {
            "text": spr("downloadsorter.keine_dateien"),
            "aktionen": [],
            "daten": {"uebersprungen": len(plan.uebersprungen) if plan else 0},
        }

    lauf = plan_anwenden(plan)
    if lauf.fehler:
        return {
            "text": spr("fehler.allgemein", grund=lauf.fehler),
            "aktionen": [], "daten": {}, "fehler": True,
        }

    # Was zurueckkommt, kann der Rahmen ohne Vorwissen anzeigen.
    text = spr("downloadsorter.fertig", anzahl=len(lauf.verschoben))

    aktionen = []
    if lauf.run_id:
        aktionen.append((spr("downloadsorter.rueckgaengig"), lauf.run_id))

    return {
        "text": text,
        "aktionen": aktionen,
        "daten": {
            "verschoben": len(lauf.verschoben),
            "uebersprungen": len(plan.uebersprungen),
            "ordner": ordner,
            "run_id": lauf.run_id,
        },
    }


def vorschau() -> dict:
    """Was wuerde passieren? Bewegt nichts.

    Die Oberflaeche zeigt das als Liste an, bevor der Nutzer auf
    "Jetzt sortieren" klickt. Das ist derselbe Plan wie in `starte()` -
    nur eben nicht ausgefuehrt.
    """
    ok, grund = pruefe()
    if not ok:
        return {"dateien": [], "geprueft": 0, "fehler": grund}

    plan = ordner_planen(einstellungen().downloads_ordner, einstellungen())
    if not plan:
        return {"dateien": [], "geprueft": 0}

    dateien = []
    for pfad in plan.dateien:
        name = os.path.basename(pfad.quelle)
        ziel_ordner = ""
        try:
            ziel_ordner = os.path.basename(os.path.dirname(pfad.ziel))
        except OSError:
            pass
        dateien.append({
            "name": name,
            "ziel": ziel_ordner,
            "grund": "",
            "groesse": pfad.groesse,
        })

    # Was liegen bleibt, gehoert auch in die Vorschau - sonst denkt der
    # Nutzer, die Datei sei verschwunden.
    for name, grund in plan.uebersprungen:
        if name.startswith("("):
            continue
        dateien.append({
            "name": name, "ziel": "", "grund": grund, "groesse": 0,
        })

    return {"dateien": dateien, "geprueft": len(dateien),
            "verschoben": len(plan.dateien),
            "uebersprungen": len(plan.uebersprungen)}


def aktion_ausfuehren(kennung: str) -> dict:
    """Fuehrt eine zuvor angebotene Aktion aus.

    Der Rahmen schickt nur die Kennung zurueck, die das Werkzeug selbst
    vergeben hat - er weiss nicht, was "Rueckgaengig" bedeutet. Eine
    unbekannte Kennung ist ein Fehler, kein stiller Erfolg.
    """
    lauf = letzter_lauf()
    if lauf is None or lauf.run_id != kennung:
        return {"text": "Dieser Lauf laesst sich nicht mehr rueckgaengig machen.",
                "aktionen": [], "daten": {}, "fehler": True}

    anzahl, fehler = lauf_rueckgaengig(kennung)
    return {
        "text": spr("downloadsorter.zurueck_fertig", anzahl=anzahl),
        "aktionen": [],
        "daten": {"zurueck": anzahl, "fehler": fehler},
    }


def spr(schluessel: str, **platzhalter) -> str:
    """Ein Text in der eingestellten Sprache.

    Der Weg laeuft ueber den Kern - aber nur, wenn es einer ist. Sonst
    nehmen wir Deutsch, damit das Werkzeug auch einzeln lauffaehig ist.
    """
    try:
        from scrinium import texte
        return texte.sag(schluessel, **platzhalter)
    except Exception:
        return f'<{schluessel}>'   # ohne Rahmen: Schluessel zeigen


# ---------------------------------------------------------------------------
# Was das Werkzeug sonst noch kann (der Rahmen ruft nichts davon automatisch)
# ---------------------------------------------------------------------------
def verlauf(anzahl: int = 20) -> list:
    """Die letzten Laeufe, fuer eine Verlaufs-Ansicht."""
    return laeufe_liste(anzahl)


def letzte_aktion() -> Lauf | None:
    """Der letzte Lauf, fuer einen Undo-Knopf."""
    return letzter_lauf()


def rueckgaengig(run_id: str) -> dict:
    """Macht einen Lauf rueckgaengig - gleiches Format wie `starte()`."""
    anzahl, fehler = lauf_rueckgaengig(run_id)
    return {
        "text": spr("downloadsorter.zurueck_fertig", anzahl=anzahl),
        "aktionen": [],
        "daten": {"zurueck": anzahl, "fehler": fehler},
    }


if __name__ == "__main__":
    # So laesst sich das Werkzeug auch einzeln aufrufen:
    #     python tools\_downloadsorter\__init__.py
    import json

    ok, grund = pruefe()
    ergebnis = starte() if ok else {"text": grund, "aktionen": [], "daten": {}}
    print(json.dumps({"ok": ok, "grund": grund, "ergebnis": ergebnis},
                     indent=2, ensure_ascii=False))