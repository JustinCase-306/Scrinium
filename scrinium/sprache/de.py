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

# --- Einstellungen ---
    "einstellungen.titel": "Einstellungen",
    "einstellungen.sprache": "Sprache",
    "einstellungen.downloads": "Download-Ordner",
    "einstellungen.ordner_waehlen": "Ordner wählen",
    "einstellungen.regeln": "Eigene Regeln",
    "einstellungen.regel_neu": "Neue Regel",
    "einstellungen.endung": "Dateiendung",
    "einstellungen.muster": "Dateiname",
    "einstellungen.ziel": "Zielordner",
    "einstellungen.werkzeuge": "Werkzeuge",
    "einstellungen.werkzeug_hinzu": "Werkzeug hinzufügen",
    "einstellungen.werkzeug_ordner": "Werkzeugordner wählen",
    "einstellungen.speichern": "Speichern und schließen",
    "einstellungen.zurueck": "Zurück",
    "einstellungen.min_age": "Wartezeit für neue Dateien (Sekunden)",
    "einstellungen.entfernen": "Entfernen",
    "einstellungen.leer": "Noch nichts eingestellt.",
    "einstellungen.ok": "OK",
    "einstellungen.abbruch": "Abbrechen",
    "einstellungen.neu": "Neu",
    "einstellungen.mitgeliefert": "Mitgeliefert",
    "einstellungen.eigen": "Von dir hinzugefügt",
    "einstellungen.regel_gueltig": "Regel gespeichert.",
    "einstellungen.regel_fehlt": "Bitte Endung, Dateiname und Zielordner angeben.",
    "einstellungen.werkzeug_ok": "Werkzeug hinzugefügt.",
    "einstellungen.fehler_ordner": "Dieser Ordner existiert nicht.",
    "einstellungen.hinweis_regeln": "Deine Regeln kommen vor den eingebauten.",
}
