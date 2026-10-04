"""All English text in one place.

Keys match `de.py` exactly - a test checks that. If a key is missing in one
language, `sag()` falls back to the other and you see it immediately.
"""

TEXTE = {
    # ── Window / shell ──────────────────────────────────────────
    "fenster.titel": "Scrinium",
    "fenster.werkzeuge": "My tools",
    "fenster.keine_werkzeuge": "No tools yet.",
    "fenster.keine_werkzeuge_hinweis":
        "Put a folder with an __init__.py into the 'tools' folder.",
    "fenster.werkzeug_starten": "Start",
    "fenster.werkzeug_laeuft": "running",
    "fenster.schliessen": "Close",

    # ── Tool state ──────────────────────────────────────────────
    "werkzeug.bereit": "ready",
    "werkzeug.blockiert": "blocked: {grund}",
    "werkzeug.kaputt": "broken: {grund}",
    "werkzeug.beta": "work in progress",
    "werkzeug.ein": "on",
    "werkzeug.aus": "off",
    "werkzeug.einschalten": "enable",
    "werkzeug.ausschalten": "disable",

    # ── Downloads sorter ────────────────────────────────────────
    "downloadsorter.name": "Downloads sorter",
    "downloadsorter.prueft_ok": "ready",
    "downloadsorter.kein_ordner": "No download folder set.",
    "downloadsorter.ordner_fehlt": "Folder not found: {ordner}",
    "downloadsorter.keine_dateien": "Nothing to sort.",
    "downloadsorter.fertig": "Filed {anzahl} file(s)",
    "downloadsorter.uebersprungen": "{anzahl} file(s) skipped",
    "downloadsorter.kein_zugriff": "No access to: {ordner}",
    "downloadsorter.ordner_wahl": "Choose download folder",
    "downloadsorter.sortiert": "Sorted",
    "downloadsorter.rueckgaengig": "Undo",
    "downloadsorter.zurueck_fertig": "Moved {anzahl} file(s) back.",

    # ── Generic errors ──────────────────────────────────────────
    "fehler.allgemein": "Something went wrong: {grund}",
    "fehler.werkzeug_laeuft_nicht": "The tool is not running.",
    "aktion.verlassen": "Got it",
}