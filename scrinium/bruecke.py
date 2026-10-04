"""Die Bruecke zwischen Scrinium-Kern und der HTML-Oberflaeche.

Die Oberflaeche ist HTML/CSS (siehe `fenster.html`). Python und HTML
koennen nicht direkt miteinander reden, also laeuft hier eine Bruecke:

    HTML ruft:   window.pywebview.api.werkzeug_starten('downloadsorter')
    Python erfuellt: def werkzeug_starten(wid): ...

Zwei Wege, je nachdem was schneller ist:

1. **API** (pywebview ruft Python) - fuer Aktionen: Knopf gedrueckt,
   Werkzeug starten, Sprache wechseln.
2. **Ereignisse** (Python ruft HTML) - fuer Updates: Werkzeug fertig,
   Liste neu laden, Sprache umstellen.

Warum das extra Datei ist: Das Fenster soll nie direkt den Kern kennen.
Es fragt hier an und bekommt fertige Daten. Damit bleibt der Kern
austauschbar, ohne dass sich das Fenster aendert - wichtig, weil
Werkzeuge spaeter dazukommen.
"""

from __future__ import annotations

import json
import os
import threading

from . import kern, texte
from .einstellungen import Einstellungen, config_pfad

# Was die Oberflaeche anfragt. Ein dict, weil das Fenster den Zustand
# zwischen Klicks liest - eine Liste waere hier falsch.
#
# WICHTIG: das Fenster selbst steht hier NICHT drin. `zustand()` geht als
# JSON an die HTML, und ein Window-Objekt laesst sich nicht serialisieren -
# der Aufruf wuerde sich selbst verschlucken. Das Fenster gehoert darum
# in ein eigenes Modul-Feld.
ZUSTAND = {
    "werkzeuge": [],      # was gefundet wurde
    "einstellungen": {},  # derzeitige Einstellungen
    "laeuft": None,       # id des gerade laufenden Werkzeugs
    "ergebnis": None,     # letztes Ergebnis fuer die Anzeige
}

# Das offene Fenster. Getrennt, weil es nicht in den JSON-Zustand darf.
_FENSTER = None
_ORDNER_WAHL: dict = {}


def _fenster():
    """Das offene Fenster, oder None. Nie im JSON-Zustand."""
    return _FENSTER


def fenster_setzen(fenster_obj) -> None:
    """Merkt sich das Fenster. Aufruft `fenster.py`."""
    global _FENSTER
    _FENSTER = fenster_obj


def _zustand_lesen():
    """Baut den Zustand, den das Fenster braucht."""
    einstellungen = Einstellungen.laden()
    texte.sprache_setzen(einstellungen.sprache)

    gefunden = kern.finde_werkzeuge()
    ZUSTAND["werkzeuge"] = [
        {
            "id": w.id,
            "name": w.name,
            "beta": w.beta,
            "fehler": w.fehler,
            "an": einstellungen.werkzeug_ist_an(w.id),
            "bereit": w.pruefe()[0],
            "grund": w.pruefe()[1],
        }
        for w in gefunden
    ]
    ZUSTAND["einstellungen"] = {
        "sprache": einstellungen.sprache,
        "downloads_ordner": einstellungen.downloads_ordner,
        "werkzeuge_an": einstellungen.werkzeuge_an,
    }
    return ZUSTAND


# ---------------------------------------------------------------------------
# Was die Oberflaeche aufruft
# ---------------------------------------------------------------------------
def zustand() -> dict:
    """Alles, was das Fenster zum Aufbauen braucht."""
    return _zustand_lesen()


def werkzeug_starten(wid: str) -> dict:
    """Startet ein Werkzeug und gibt das Ergebnis zurueck.

    Kommt direkt aus dem Button 'Jetzt sortieren'. Der Kern entscheidet
    alles selbst - das Fenster gibt nur die Id weiter und zeigt zurueck,
    was herauskam.
    """
    if ZUSTAND["laeuft"]:
        return {"text": texte.sag("fehler.werkzeug_laeuft_nicht"),
                "aktionen": [], "daten": {}, "fehler": True}

    for w in kern.finde_werkzeuge():
        if w.id != wid:
            continue

        ok, grund = w.pruefe()
        if not ok:
            return {"text": grund, "aktionen": [], "daten": {}, "fehler": True}

        ZUSTAND["laeuft"] = wid
        try:
            # pruefe() und starte() koennen beide nicht lange dauern; fuer
            # laengere Laeufe wuerde hier ein Thread noetig.
            ergebnis = w.starte()
        finally:
            ZUSTAND["laeuft"] = None

        ZUSTAND["ergebnis"] = ergebnis
        return ergebnis

    return {"text": f"Unbekanntes Werkzeug: {wid}", "aktionen": [],
            "daten": {}, "fehler": True}


def werkzeug_schalten(wid: str, an: bool) -> dict:
    """Ein Werkzeug ein- oder ausschalten."""
    e = Einstellungen.laden()
    e.werkzeug_schalten(wid, an)
    e.speichern()
    return _zustand_lesen()


def sprache_setzen(sprache: str) -> dict:
    """Sprache umstellen - der Kern schickt danach alle Texte neu."""
    e = Einstellungen.laden()
    e.sprache = sprache
    e.speichern()
    texte.sprache_setzen(sprache)
    return _zustand_lesen()


def downloads_ordner_setzen(pfad: str) -> dict:
    """Neuer Download-Ordner."""
    e = Einstellungen.laden()
    e.downloads_ordner = pfad
    e.speichern()
    return _zustand_lesen()


def ordner_waehlen() -> str:
    """Oeffnet den Windows-Ordnerdialog. Gibt den Pfad zurueck oder ''.

    Muss im Hauptthread laufen, sonst blockiert Windows den Dialog.
    """
    import webview

    def zurueck(ergebnis):
        ZUSTAND["_ordner_wahl"] = ergebnis[0] if ergebnis else ""

    fenster = _fenster()
    if fenster is None:
        return ""
    fenster.create_file_dialog(webview.OPEN_DIALOG, directory_only=True,
                               func=zurueck)
    # create_file_dialog blockiert nicht - deshalb pollen wir kurz.
    for _ in range(600):
        if "_ordner_wahl" in ZUSTAND:
            pfad = ZUSTAND.pop("_ordner_wahl")
            if pfad:
                downloads_ordner_setzen(pfad)
                return pfad
        threading.Event().wait(0.1)
    return ""


def aktualisieren() -> None:
    """Schickt den neuen Zustand an die Oberflaeche."""
    fenster = _fenster()
    if fenster is None:
        return
    try:
        fenster.evaluate_js("scrinium.zustand(" +
                            json.dumps(_zustand_lesen()).replace("</", "<\\/") + ")")
    except Exception:
        pass
        pass


def vorschau(wid: str) -> dict:
    """Was wuerde passieren? Bewegt nichts - nur zum Anzeigen.

    Das Werkzeug muss dafuer eine eigene Funktion anbieten. Hat es
    keine, bekommt die Oberflaeche eine leere Liste - sie soll nicht
    raten, was passieren wuerde.
    """
    for w in kern.finde_werkzeuge():
        if w.id != wid:
            continue
        vorschau_fn = getattr(w.modul, "vorschau", None)
        if not callable(vorschau_fn):
            return {"dateien": [], "geprueft": 0}
        try:
            roh = vorschau_fn()
        except Exception as exc:
            return {"dateien": [], "geprueft": 0, "fehler": str(exc)}
        if not isinstance(roh, dict):
            return {"dateien": [], "geprueft": 0}
        dateien = []
        for d in roh.get("dateien", [])[:200]:
            if not isinstance(d, dict):
                continue
            dateien.append({
                "name": str(d.get("name", "")),
                "ziel": d.get("ziel") or "",
                "grund": d.get("grund") or "",
                "groesse": d.get("groesse", 0),
            })
        return {
            "dateien": dateien,
            "geprueft": int(roh.get("geprueft", len(dateien))),
            "verschoben": int(roh.get("verschoben", 0)),
            "uebersprungen": int(roh.get("uebersprungen", 0)),
        }

    return {"dateien": [], "geprueft": 0}


def aktion(kennung: str) -> dict:
    """Fuehrt eine Aktion aus, die ein Werkzeug angeboten hat.

    `kennung` ist das, was in den 'aktionen' des Werkzeugs stand - beim
    Sortierer die run_id fuer "Rueckgaengig". Das Werkzeug weiss, was
    damit gemeint ist; der Rahmen nicht.
    """
    for w in kern.finde_werkzeuge():
        ausfuehren = getattr(w.modul, "aktion_ausfuehren", None)
        if not callable(ausfuehren):
            continue
        try:
            ergebnis = ausfuehren(kennung)
        except Exception as exc:
            return {"text": str(exc), "aktionen": [], "daten": {}, "fehler": True}
        if isinstance(ergebnis, dict):
            return ergebnis
    return {"text": "Diese Aktion ist zurueckgesetzt worden.",
            "aktionen": [], "daten": {}, "fehler": True}


def ordner_oeffnen() -> str:
    """Oeffnet den Download-Ordner im Explorer."""
    e = Einstellungen.laden()
    ordner = e.downloads_ordner
    if ordner and os.path.isdir(ordner):
        try:
            os.startfile(ordner)
            return ordner
        except OSError:
            pass
    return ""


def einstellungen_oeffnen() -> str:
    """Oeffnet die Scrinium-Einstellungen im Explorer.

    Bewusst kein zweites Fenster: fuer den Anfang reicht der Ordner, und
    ein Einstellungsfenster waere eine komplette Oberflaeche mehr.
    """
    ordner = os.path.dirname(config_pfad())
    try:
        os.startfile(ordner)
        return ordner
    except OSError:
        return ""