"""Minimal i18n. German and English, no external dependency.

`_()` is bound to the active language on the app instance; the module-level
`t()` helper is available for pure-logic code and tests.
"""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "de": {
        # tabs
        "tab.sort": "Sortieren",
        "tab.rules": "Regeln",
        "tab.history": "Verlauf",
        "tab.settings": "Settings",
        # sort tab
        "source": "📥 Download-Ordner",
        "browse": "Durchsuchen…",
        "auto": "🤖 Automatisch sortieren",
        "watch": "Bei neuen Dateien sortieren",
        "interval": "Intervall aktivieren",
        "minutes": "Minuten",
        "sort_now": "⚡ Jetzt sortieren",
        "preview": "🔍 Vorschau",
        "apply": "✅ Ausführen",
        "cancel": "✖ Abbrechen",
        "undo": "↩ Rückgängig",
        "open_folder": "📂 Ordner öffnen",
        "status_idle": "Bereit.",
        "status_planning": "Analysiere {count} Dateien …",
        "status_sorting": "Verschiebe {done}/{total} …",
        "status_done": "✓ {count} Datei(en) einsortiert ({size})",
        "status_nothing": "Nichts zu sortieren – alles bereits einsortiert.",
        "status_cancelled": "Abgebrochen nach {count} Datei(en).",
        "status_error": "Fehler: {err}",
        "col.file": "Datei",
        "col.category": "Category",
        "col.size": "Größe",
        "col.reason": "Warum",
        "col.new_name": "Neuer Name",
        "skipped": "⏭ Übersprungen",
        "log": "📋 Protokoll",
        "clear_log": "Leeren",
        # rules tab
        "rules_intro": "Eigene Regeln – geprüft vor der eingebauten Zuordnung.",
        "rule_add": "Regel hinzufügen",
        "rule_pattern": "Dateiname enthält",
        "rule_extglob": "Name entspricht",
        "rule_ext": "Endung",
        "rule_target": "Gehört zu",
        "rule_skip": "Nie verschieben",
        "rule_case": "Groß-/Kleinschreibung",
        "no_rules": "Noch keine eigenen Regeln.",
        "ext_add": "Eigene Endung",
        "ext_to": "Gehört zu",
        "no_ext": "Noch keine eigenen Endungen.",
        "disabled": "Deaktivierte Kategorien",
        "categories": "Kategorien",
        "test_input": "Testdatei",
        "test_run": "Testen",
        "test_result": "Ergebnis",
        # history tab
        "history_empty": "Noch keine Sortierläufe.",
        "history_runs": "Läufe",
        "history_files": "Dateien",
        "history_volume": "Volumen",
        "history_undo": "Rückgängig machen",
        "history_undo_done": "✓ {count} Datei(en) zurückverschoben.",
        "history_cleared": "Verlauf gelöscht.",
        "history_clear": "Verlauf löschen",
        # settings tab
        "targets": "📁 Zielordner pro Category",
        "targets_hint": "leer lassen = Standardordner im Download-Ordner",
        "reset": "Standard",
        "appearance": "🎨 Aussehen",
        "mode": "Modus",
        "accent": "Akzentfarbe",
        "accent_custom": "Eigene Farbe…",
        "language": "Sprache",
        "behaviour": "⚙️ Verhalten",
        "min_age": "Datei muss mindestens so alt sein (Sek.)",
        "collide": "Bei Namenskonflikt",
        "collide_skip": "Überspringen",
        "collide_rename": "Umbenennen (name_01)",
        "collide_replace": "Ersetzen",
        "recursive": "Unterordner einbeziehen",
        "tray": "In den Infobereich minimieren",
        "close_tray": "Schließen legt in den Infobereich",
        "autostart": "Mit Windows starten",
        "notify": "Desktop-Benachrichtigungen",
        "save": "💾 Settings speichern",
        "saved": "✓ Settings gespeichert.",
        "open_cfg": "📁 Konfigurationsordner",
        "about": "ⓘ Über",
        # tray menu
        "tray.open": "Scrinium öffnen",
        "tray.sort": "Jetzt sortieren",
        "tray.quit": "Beenden",
        "tray.autostart": "Mit Windows starten",
        # dialogs
        "confirm_title": "Scrinium",
        "quit_confirm": "Scrinium läuft weiter im Infobereich. Trotzdem beenden?",
        "first_run": (
            "Willkommen bei Scrinium!\n\n"
            "Scrinium verschiebt fertige Dateien aus deinem Download-Ordner in "
            "passende Unterordner.\n\n"
            "• Vorschau zeigt erst, was passieren würde\n"
            "• Jeder Run lässt sich rückgängig machen\n"
            "• Halbe Downloads (.crdownload/.part) werden ignoriert"
        ),
        "first_run_ok": "Verstanden",
        "dl_missing": "Der Download-Ordner {dir} existiert nicht.\nBitte wähle einen anderen Ordner.",
        "thousands_sep": ".",
    },
    "en": {
        "tab.sort": "Sort",
        "tab.rules": "Rules",
        "tab.history": "History",
        "tab.settings": "Settings",
        "source": "📥 Download folder",
        "browse": "Browse…",
        "auto": "🤖 Automatic sorting",
        "watch": "Sort on new files",
        "interval": "Enable interval",
        "minutes": "minutes",
        "sort_now": "⚡ Sort now",
        "preview": "🔍 Preview",
        "apply": "✅ Apply",
        "cancel": "✖ Cancel",
        "undo": "↩ Undo",
        "open_folder": "📂 Open folder",
        "status_idle": "Ready.",
        "status_planning": "Scanning {count} files…",
        "status_sorting": "Moving {done}/{total}…",
        "status_done": "✓ Filed {count} file(s) ({size})",
        "status_nothing": "Nothing to sort - everything is already filed.",
        "status_cancelled": "Cancelled after {count} file(s).",
        "status_error": "Error: {err}",
        "col.file": "File",
        "col.category": "Category",
        "col.size": "Size",
        "col.reason": "Why",
        "col.new_name": "New name",
        "skipped": "⏭ Skipped",
        "log": "📋 Log",
        "clear_log": "Clear",
        "rules_intro": "Your own rules - checked before the built-in mapping.",
        "rule_add": "Add rule",
        "rule_pattern": "Filename contains",
        "rule_extglob": "Name matches",
        "rule_ext": "Extension",
        "rule_target": "Belongs to",
        "rule_skip": "Never move",
        "rule_case": "Case sensitive",
        "no_rules": "No custom rules yet.",
        "ext_add": "Custom extension",
        "ext_to": "Belongs to",
        "no_ext": "No custom extensions yet.",
        "disabled": "Disabled categories",
        "categories": "Categories",
        "test_input": "Test file",
        "test_run": "Test",
        "test_result": "Result",
        "history_empty": "No sort runs yet.",
        "history_runs": "Runs",
        "history_files": "Files",
        "history_volume": "Volume",
        "history_undo": "Undo run",
        "history_undo_done": "✓ Moved {count} file(s) back.",
        "history_cleared": "History cleared.",
        "history_clear": "Clear history",
        "targets": "📁 Target folder per category",
        "targets_hint": "leave empty = default folder inside Downloads",
        "reset": "Default",
        "appearance": "🎨 Appearance",
        "mode": "Mode",
        "accent": "Accent colour",
        "accent_custom": "Custom colour…",
        "language": "Language",
        "behaviour": "⚙️ Behaviour",
        "min_age": "File must be at least this old (seconds)",
        "collide": "On name conflict",
        "collide_skip": "Skip",
        "collide_rename": "Rename (name_01)",
        "collide_replace": "Replace",
        "recursive": "Include subfolders",
        "tray": "Minimise to tray",
        "close_tray": "Closing goes to tray",
        "autostart": "Start with Windows",
        "notify": "Desktop notifications",
        "save": "💾 Save settings",
        "saved": "✓ Settings saved.",
        "open_cfg": "📁 Config folder",
        "about": "ⓘ About",
        "tray.open": "Open Scrinium",
        "tray.sort": "Sort now",
        "tray.quit": "Quit",
        "tray.autostart": "Start with Windows",
        "confirm_title": "Scrinium",
        "quit_confirm": "Scrinium keeps running in the tray. Quit anyway?",
        "first_run": (
            "Welcome to Scrinium!\n\n"
            "Scrinium moves finished files from your download folder into "
            "matching subfolders.\n\n"
            "• Preview shows what would happen first\n"
            "• Every run can be undone\n"
            "• Half-finished downloads (.crdownload/.part) are ignored"
        ),
        "first_run_ok": "Got it",
        "dl_missing": "The download folder {dir} does not exist.\nPlease choose another folder.",
        "thousands_sep": ",",
    },
}


class T:
    """Tiny translator bound to one language."""

    def __init__(self, lang: str = "de"):
        self.lang = lang if lang in STRINGS else "de"

    def __call__(self, key: str, **kw) -> str:
        table = STRINGS[self.lang]
        text = table.get(key) or STRINGS["de"].get(key) or key
        if kw:
            try:
                return text.format(**kw)
            except (KeyError, IndexError, ValueError):
                return text
        return text

    def set(self, lang: str) -> None:
        if lang in STRINGS:
            self.lang = lang

    def num(self, value: int) -> str:
        return f"{int(value):,}".replace(",", STRINGS[self.lang]["thousands_sep"])


_TR = T("de")


def t(key: str, **kw) -> str:
    return _TR(key, **kw)


def set_lang(lang: str) -> None:
    _TR.set(lang)


def get_lang() -> str:
    return _TR.lang
