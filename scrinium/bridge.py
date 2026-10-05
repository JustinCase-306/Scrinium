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
import threading
from . import core, texts
from .settings import Settings, config_path
ZUSTAND = {'tools': [], 'settings': {}, 'running': None, 'result': None}
_FENSTER = None
_ORDNER_WAHL: dict = {}

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

def choose_folder() -> str:
    """Oeffnet den Windows-Ordnerdialog. Gibt den Pfad zurueck oder ''.

    Muss im Hauptthread laufen, sonst blockiert Windows den Dialog.
    """
    import webview

    def zurueck(result):
        ZUSTAND['_folder_choice'] = result[0] if result else ''
    fenster = _window()
    if fenster is None:
        return ''
    window.create_file_dialog(webview.OPEN_DIALOG, directory_only=True, func=zurueck)
    for _ in range(600):
        if '_folder_choice' in ZUSTAND:
            path = ZUSTAND.pop('_folder_choice')
            if path:
                set_downloads_folder(path)
                return path
        threading.Event().wait(0.1)
    return ''

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
    """Oeffnet die Scrinium-Settings im Explorer.

    Bewusst kein zweites Fenster: fuer den Anfang reicht der Ordner, und
    ein Einstellungsfenster waere eine komplette Oberflaeche mehr.
    """
    folder = os.path.dirname(config_path())
    try:
        os.startfile(folder)
        return folder
    except OSError:
        return ''
