"""Die Bruecke zwischen Scrinium-Kern und der HTML-Oberflaeche.

Die Oberflaeche ist HTML/CSS (siehe `window.html`). Python und HTML
koennen nicht direkt miteinander reden, also running hier eine Bruecke:

    HTML ruft:   window.pywebview.api.start_tool('downloadsorter')
    Python erfuellt: def start_tool(wid): ...

Zwei Wege, je nachdem was schneller ist:

1. **API** (pywebview ruft Python) - fuer Aktionen: Knopf gedrueckt,
   Tool starten, Sprache wechseln.
2. **Ereignisse** (Python ruft HTML) - fuer Updates: Tool fertig,
   Liste neu laden, Sprache umstellen.

Warum das extra Datei ist: Das Fenster soll nie direkt den Kern kennen.
Es fragt hier an und bekommt fertige Daten. Damit bleibt der Kern
austauschbar, ohne dass sich das Fenster aendert - wichtig, weil
Tools spaeter dazukommen.
"""
from __future__ import annotations
import json
import os
import sys
from . import core, texts
from .settings import Settings, _standard_downloads
ZUSTAND = {'tools': [], 'settings': {}, 'running': None, 'result': None}
_FENSTER = None

def _window():
    """Das offene Fenster, oder None. Nie im JSON-Zustand."""
    return _FENSTER

def set_window(fenster_obj) -> None:
    """Merkt sich das Fenster. Aufruft `window.py`."""
    global _FENSTER
    _FENSTER = fenster_obj

def _read_state():
    """Baut den Zustand, den das Fenster braucht."""
    settings = Settings.laden()
    texts.set_language(settings.language)
    gefunden = core.find_tools()
    ZUSTAND['tools'] = [{'id': w.id, 'name': w.name, 'beta': w.beta, 'fehler': w.fehler, 'an': settings.tool_is_enabled(w.id), 'bereit': w.check()[0], 'grund': w.check()[1]} for w in gefunden]
    ZUSTAND['settings'] = {'language': settings.language, 'downloads_folder': settings.downloads_folder, 'tools_enabled': settings.tools_enabled}
    return ZUSTAND

def state() -> dict:
    """Alles, was das Fenster zum Aufbauen braucht."""
    return _read_state()

def start_tool(wid: str) -> dict:
    """Startet ein Tool und gibt das Ergebnis zurueck.

    Kommt direkt aus dem Button 'Jetzt sortieren'. Der Kern entscheidet
    alles selbst - das Fenster gibt nur die Id weiter und zeigt zurueck,
    was herauskam.
    """
    if ZUSTAND['running']:
        return {'text': texts.sag('fehler.werkzeug_laeuft_nicht'), 'actions': [], 'data': {}, 'fehler': True}
    for w in core.find_tools():
        if w.id != wid:
            continue
        ok, grund = w.check()
        if not ok:
            return {'text': grund, 'actions': [], 'data': {}, 'fehler': True}
        ZUSTAND['running'] = wid
        try:
            result = w.starte()
        finally:
            ZUSTAND['running'] = None
        ZUSTAND['result'] = result
        return result
    return {'text': f'Unbekanntes Tool: {wid}', 'actions': [], 'data': {}, 'fehler': True}

def toggle_tool(wid: str, an: bool) -> dict:
    """Ein Tool ein- oder ausschalten."""
    e = Settings.laden()
    e.toggle_tool(wid, an)
    e.speichern()
    return _read_state()

def set_language(language: str) -> dict:
    """Sprache umstellen - der Kern schickt danach alle Texte neu."""
    e = Settings.laden()
    e.language = language
    e.speichern()
    texts.set_language(language)
    return _read_state()

def set_downloads_folder(path: str) -> dict:
    """Neuer Download-Ordner."""
    e = Settings.laden()
    e.downloads_folder = path
    e.speichern()
    return _read_state()

def choose_folder(auswahl: bool = False) -> str:
    """Ordnerdialog. Gibt den Pfad zurueck oder ''.

    Mit `auswahl=True` wird NICHTS gespeichert - das Fenster will den
    Pfad erst anzeigen, damit der Nutzer ihn bestaetigen kann. Ohne
    `auswahl` wird er direkt als Download-Ordner uebernommen.

    `create_file_dialog` gibt SYNCHRON ein Tupel zurueck. Es gibt keinen
    Callback-Parameter: ein solches Argument wirft TypeError, und weil
    das JavaScript kein .catch() hat, tat der Knopf danach einfach
    nichts. Deshalb hier der direkte Rueckgabewert.
    """
    import webview

    fenster = _window()
    if fenster is None:
        return ''

    try:
        gewaehlt = fenster.create_file_dialog(webview.FileDialog.FOLDER)
    except Exception:
        return ''

    path = (gewaehlt[0] if gewaehlt else '') or ''
    if path and not auswahl:
        set_downloads_folder(path)
    return path


def choose_tool_folder() -> str:
    """Ordnerdialog fuer ein neues Werkzeug. Speichert nichts.

    Gleiche pywebview-Falle wie in `choose_folder`: der Dialog gibt
    synchron ein Tupel zurueck, einen Callback-Parameter gibt es nicht.
    """
    import webview

    fenster = _window()
    if fenster is None:
        return ''

    try:
        gewaehlt = fenster.create_file_dialog(webview.FileDialog.FOLDER)
    except Exception:
        return ''

    return (gewaehlt[0] if gewaehlt else '') or ''


# ---------------------------------------------------------------------------
# Einstellungen - was der Knopf "Einstellungen" im Fenster aufruft
# ---------------------------------------------------------------------------
def settings_lesen() -> dict:
    """Alles, was das Einstellungsfenster zum Anzeigen braucht."""
    e = Settings.laden()

    # Alle Ordner, in die ein Werkzeug einsortieren kann. Die kommen aus
    # dem Werkzeug - der Rahmen darf sie nicht selbst erfinden.
    ordner = set()
    mitgeliefert = []
    for w in core.find_tools():
        ordner.update(_ordner_von_tool(w))
        mitgeliefert.append({"id": w.id, "name": w.name, "pfad": w.folder})

    regeln = []
    for r in e.sortier_regeln:
        if isinstance(r, dict) and r.get("wert"):
            regeln.append({"art": r.get("art", "endung"),
                           "wert": r.get("wert", ""),
                           "ziel": r.get("ziel", "")})

    return {
        "language": e.language,
        "downloads_folder": e.downloads_folder,
        "downloads_min_age": e.downloads_min_age,
        "downloads_interval": e.downloads_interval,
        "downloads_on_new_files": bool(e.downloads_on_new_files),
        "regeln": regeln,
        "ordner": sorted(ordner),
        "tools_mitgeliefert": mitgeliefert,
        "eigene_werkzeuge": [dict(w) for w in e.eigene_werkzeuge
                             if isinstance(w, dict)],
        "texte": settings_texts(e.language),
    }


def _ordner_von_tool(w) -> list:
    """Welche Zielordner kann ein Werkzeug? Der Rahmen fragt es nach."""
    ordner = []
    try:
        kategorien = getattr(w.modul, "categories", None)
        if callable(kategorien):
            for k in kategorien():
                name = getattr(k, "name", None) or getattr(k, "folder", None)
                if name:
                    ordner.append(str(name))
    except Exception:
        pass
    return ordner


def settings_texts(sprache: str) -> dict:
    """Alle Beschriftungen des Einstellungsfensters."""
    texts.set_language(sprache)
    keys = ("einstellungen.titel", "einstellungen.sprache",
            "einstellungen.downloads", "einstellungen.ordner_waehlen",
            "einstellungen.regeln", "einstellungen.regel_neu",
            "einstellungen.endung", "einstellungen.muster",
            "einstellungen.ziel", "einstellungen.werkzeuge",
            "einstellungen.werkzeug_hinzu", "einstellungen.speichern",
            "einstellungen.zurueck", "einstellungen.min_age",
            "einstellungen.entfernen", "einstellungen.leer",
            "einstellungen.ok", "einstellungen.abbruch",
            "einstellungen.neu", "einstellungen.werkzeug_ordner")
    return {k: texts.sag(k) for k in keys}


# --- Aenderungen -----------------------------------------------------------
def settings_sprache_setzen(sprache: str) -> dict:
    e = Settings.laden()
    e.language = sprache if sprache in ("de", "en") else "de"
    e.speichern()
    texts.set_language(e.language)
    return _read_state()


def settings_downloads_setzen(pfad: str) -> dict:
    e = Settings.laden()
    pfad = str(pfad or "").strip()
    if pfad and not os.path.isdir(pfad):
        return {"ok": False, "fehler": "ORDNER FEHLT"}
    e.downloads_folder = pfad or _standard_downloads()
    e.speichern()
    return {"ok": True, "downloads_folder": e.downloads_folder}


def settings_min_age_setzen(sekunden: int) -> dict:
    e = Settings.laden()
    try:
        sek = int(sekunden)
    except (TypeError, ValueError):
        sek = 30
    e.downloads_min_age = max(0, sek)
    e.speichern()
    return {"ok": True, "downloads_min_age": e.downloads_min_age}


def settings_regel_hinzufuegen(art: str, wert: str, ziel: str) -> dict:
    e = Settings.laden()
    regel = e.regel_hinzufuegen(art, wert, ziel)
    if regel is None:
        return {"ok": False, "fehler": "UNGUELTIG"}
    e.speichern()
    return {"ok": True, "regel": regel, "regeln": e.sortier_regeln}


def settings_regel_entfernen(art: str, wert: str) -> dict:
    e = Settings.laden()
    weg = e.regel_entfernen(art, wert)
    e.speichern()
    return {"ok": weg, "regeln": e.sortier_regeln}


def settings_werkzeug_hinzufuegen(pfad: str) -> dict:
    e = Settings.laden()
    meldung = e.werkzeug_hinzufuegen(pfad)
    if meldung != "OK":
        return {"ok": False, "fehler": meldung}
    e.speichern()
    core.reload_tools()
    return {"ok": True, "eigene_werkzeuge": e.eigene_werkzeuge,
            "tools": _read_state()["tools"]}


def settings_werkzeug_entfernen(pfad: str) -> dict:
    e = Settings.laden()
    weg = e.werkzeug_entfernen(pfad)
    e.speichern()
    core.reload_tools()
    return {"ok": weg, "eigene_werkzeuge": e.eigene_werkzeuge,
            "tools": _read_state()["tools"]}

def refresh() -> None:
    """Schickt den neuen Zustand an die Oberflaeche."""
    fenster = _window()
    if fenster is None:
        return
    try:
        window.evaluate_js('scrinium.state(' + json.dumps(_read_state()).replace('</', '<\\/') + ')')
    except Exception:
        pass
        pass

def preview(wid: str) -> dict:
    """Was wuerde passieren? Bewegt nichts - nur zum Anzeigen.

    Das Tool muss dafuer eine eigene Funktion anbieten. Hat es
    keine, bekommt die Oberflaeche eine leere Liste - sie soll nicht
    raten, was passieren wuerde.
    """
    for w in core.find_tools():
        if w.id != wid:
            continue
        vorschau_fn = getattr(w.modul, 'preview', None)
        if not callable(vorschau_fn):
            return {'dateien': [], 'geprueft': 0}
        try:
            roh = vorschau_fn()
        except Exception as exc:
            return {'dateien': [], 'geprueft': 0, 'fehler': str(exc)}
        if not isinstance(roh, dict):
            return {'dateien': [], 'geprueft': 0}
        dateien = []
        for d in roh.get('dateien', [])[:200]:
            if not isinstance(d, dict):
                continue
            dateien.append({'name': str(d.get('name', '')), 'ziel': d.get('ziel') or '', 'grund': d.get('grund') or '', 'size': d.get('size', 0)})
        return {'dateien': dateien, 'geprueft': int(roh.get('geprueft', len(dateien))), 'moved': int(roh.get('moved', 0)), 'skipped': int(roh.get('skipped', 0))}
    return {'dateien': [], 'geprueft': 0}

def action(kennung: str) -> dict:
    """Fuehrt eine Aktion aus, die ein Tool angeboten hat.

    `kennung` ist das, was in den 'actions' des Werkzeugs stand - beim
    Sortierer die run_id fuer "Rueckgaengig". Das Tool weiss, was
    damit gemeint ist; der Rahmen nicht.
    """
    for w in core.find_tools():
        ausfuehren = getattr(w.modul, 'run_action', None)
        if not callable(ausfuehren):
            continue
        try:
            result = ausfuehren(kennung)
        except Exception as exc:
            return {'text': str(exc), 'actions': [], 'data': {}, 'fehler': True}
        if isinstance(result, dict):
            return result
    return {'text': 'Diese Aktion ist zurueckgesetzt worden.', 'actions': [], 'data': {}, 'fehler': True}

def open_folder() -> str:
    """Oeffnet den Download-Ordner im Explorer."""
    e = Settings.laden()
    folder = e.downloads_folder
    if folder and os.path.isdir(folder):
        try:
            os.startfile(folder)
            return folder
        except OSError:
            pass
    return ''

def open_settings() -> str:
    """Oeffnet die Einstellungen als eigenes Fenster.

    Rueckgabewert ist '' (nichts) oder 'offen'.

    Der Titel kommt aus `texts.sag` - das nimmt EIN Argument. Ein
    zweites ("Einstellungen" als Notnagel) wirft TypeError:
    `sag() takes 1 positional argument but 2 were given`.

    Dieser TypeError war stumm verschluckt und hat den Knopf "Einstellungen"
    damit wirkungslos gemacht: hier kam '' heraus, und das JavaScript hat
    kein .catch(), also gab es keine Meldung. Der fehlende Text ist
    ohnehin abgedeckt - `sag` gibt den Schluessel selbst zurueck.
    """
    import webview

    from .window import bridge_api

    titel = texts.sag("einstellungen.titel") or "Einstellungen"

    html = _settings_html()
    if not html:
        # Kein stiller Ausstieg: so sieht man im Protokoll, was fehlt.
        print("Scrinium: settings.html nicht gefunden - "
              "Einstellungen nicht verfuegbar.")
        return ""
    if _window() is None:
        print("Scrinium: kein Hauptfenster - Einstellungen nicht moeglich.")
        return ""

    try:
        webview.create_window(
            titel, html, js_api=bridge_api(),
            width=900, height=820, min_size=(700, 600),
            background_color="#141218")
    except Exception as e:
        # Frueher stand hier ein blankes `return ""`. Damit sah ein
        # Fehler wie ein toter Knopf aus.
        print(f"Scrinium: Einstellungen konnten nicht oeffnen ({e}).")
        return ""
    return "offen"


def _settings_html() -> str:
    """Wo liegt settings.html - im Quellcode und in der gepackten EXE."""
    hier = os.path.dirname(os.path.abspath(__file__))
    pfad = os.path.join(hier, "settings.html")
    if os.path.isfile(pfad):
        return pfad
    if getattr(sys, "frozen", False):
        gepackt = os.path.join(os.path.dirname(sys.executable),
                               "scrinium", "settings.html")
        if os.path.isfile(gepackt):
            return gepackt
    return ""
