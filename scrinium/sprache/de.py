"""Alle deutschen Texte an einem Ort.

Schluessel = "bereich.ereignis", in Kleingeschreibung, mit Punkt getrennt.
Werkzeug-Code benutzt NUR diese Schluessel, nie deutsche Texte direkt.
"""

TEXTE = {
    # ── Fenster / Rahmen ──────────────────────────────────────────
    "fenster.titel": "Scrinium",
    "fenster.werkzeuge": "Meine Werkzeuge",
    "fenster.keine_werkzeuge": "Noch keine Werkzeuge.",
    "fenster.keine_werkzeuge_hinweis":
        "Lege einen Ordner mit einer __init__.py in den Ordner 'tools'.",
    "fenster.werkzeug_starten": "Starten",
    "fenster.werkzeug_laeuft": "laeuft",
    "fenster.schliessen": "Schliessen",

    # ── Werkzeug-Zustand ─────────────────────────────────────────
    "werkzeug.bereit": "bereit",
    "werkzeug.blockiert": "blockiert: {grund}",
    "werkzeug.kaputt": "kaputt: {grund}",
    "werkzeug.beta": "in Arbeit",
    "werkzeug.ein": "an",
    "werkzeug.aus": "aus",
    "werkzeug.einschalten": "einschalten",
    "werkzeug.ausschalten": "ausschalten",

    # ── Downloads-Sortierer ──────────────────────────────────────
    "downloadsorter.name": "Downloads-Sortierer",
    "downloadsorter.prueft_ok": "bereit",
    "downloadsorter.kein_ordner": "Kein Download-Ordner eingestellt.",
    "downloadsorter.ordner_fehlt": "Ordner nicht gefunden: {ordner}",
    "downloadsorter.keine_dateien": "Nichts zu sortieren.",
    "downloadsorter.fertig": "{anzahl} Dateien einsortiert",
    "downloadsorter.uebersprungen": "{anzahl} Dateien uebersprungen",
    "downloadsorter.kein_zugriff": "Kein Zugriff auf: {ordner}",
    "downloadsorter.ordner_wahl": "Download-Ordner waehlen",
    "downloadsorter.sortiert": "Sortiert",
    "downloadsorter.rueckgaengig": "Rueckgaengig",
    "downloadsorter.zurueck_fertig": "{anzahl} Dateien zurueckverschoben.",

    # ── Allgemeine Fehler ────────────────────────────────────────
    "fehler.allgemein": "Etwas ist schiefgelaufen: {grund}",
    "fehler.werkzeug_laeuft_nicht": "Das Werkzeug laeuft gerade nicht.",
    "aktion.verlassen": "Verstanden",
}