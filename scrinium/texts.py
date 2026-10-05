"""Alle sichtbaren Texte an einem Ort.

Tool-Code schreibt KEINEN deutschen oder englischen Text. Er fragt nur:

    sag("downloadsorter.bereit", anzahl=14)

und bekommt den Text fuer die eingestellte Sprache. Eine neue Sprache
ist eine neue Datei in diesem Ordner - sonst wird nichts angefasst.

So funktioniert das:
- `language/de.py` ist ein Python-Ordner mit einem grossen Woerterbuch
- `sag()` schaut dort nach, ersetzt `{platzhalter}` und gibt den Text
- Fehlt ein Text, steht der Schluessel selbst da - man sieht den Fehler
"""

from __future__ import annotations

import importlib.util
import os

LANGUAGES = ("de", "en")           # was Scrinium anbietet
# Der Ordner mit den Sprachdateien - ein Unterordner dieses Pakets.
FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprache")

_aktuelle_sprache = "de"
_texte: dict = {}


def _lade(language: str) -> dict:
    """Laedt eine Sprachdatei. Fehlt sie, bleibt die alte aktiv."""
    global _texte
    path = os.path.join(FOLDER, f"{language}.py")
    if not os.path.isfile(path):
        return _texte                    # nicht da: alte behalten
    try:
        spec = importlib.util.spec_from_file_location(f"_scrinium_{language}", path)
        if spec is None or spec.loader is None:
            return _texte
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        # Wichtig: die Sprachdateien bieten ihre Texte unter "TEXTE" an.
        # Das ist Anzeigetext, kein Bezeichner - und bleibt deshalb deutsch.
        texte = getattr(modul, "TEXTE", None)
        if isinstance(texte, dict):
            _texte = texte
    except Exception:
        pass                                # kaputt: nicht crashen
    return _texte


def set_language(language: str) -> str:
    """Wechselt die Sprache. Gibt den echten Namen zurueck."""
    global _aktuelle_sprache
    if language in LANGUAGES:
        _aktuelle_sprache = language
        _lade(language)
    return _aktuelle_sprache


def language() -> str:
    return _aktuelle_sprache


def languages() -> tuple:
    """Welche Sprachen es gibt - aus den Dateien, nicht aus einer Liste."""
    gefunden = []
    try:
        for datei in sorted(os.listdir(FOLDER)):
            if datei.endswith(".py") and not datei.startswith("_"):
                gefunden.append(datei[:-3])
    except OSError:
        pass
    return tuple(gefunden) or LANGUAGES


def sag(key: str, **platzhalter) -> str:
    """Der Text zu einem Schluessel.

    Fehlt er, kommt der Schluessel selbst zurueck - das ist Absicht, damit
    man beim Testen sofort sieht "ah, der Text fehlt" und nicht "irgendwas
    Falsches".
    """
    if not _texte:
        _lade(_aktuelle_sprache)

    text = _texte.get(key)
    if text is None:
        # Vielleicht ist es in einer anderen Sprache da - dann zeigen wir
        # wenigstens, was der Schluessel bedeutet.
        for sprache_ in LANGUAGES:
            _lade(sprache_)
            if key in _texte:
                text = _texte[key]
                break
    if text is None:
        return key

    if platzhalter:
        try:
            return text.format(**platzhalter)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def all_keys() -> list:
    """Welche Texte es gibt - zum Pruefen, ob was fehlt."""
    return sorted(_texte)