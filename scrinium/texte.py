"""Alle sichtbaren Texte an einem Ort.

Werkzeug-Code schreibt KEINEN deutschen oder englischen Text. Er fragt nur:

    sag("downloadsorter.bereit", anzahl=14)

und bekommt den Text fuer die eingestellte Sprache. Eine neue Sprache
ist eine neue Datei in diesem Ordner - sonst wird nichts angefasst.

So funktioniert das:
- `sprache/de.py` ist ein Python-Ordner mit einem grossen Woerterbuch
- `sag()` schaut dort nach, ersetzt `{platzhalter}` und gibt den Text
- Fehlt ein Text, steht der Schluessel selbst da - man sieht den Fehler
"""

from __future__ import annotations

import importlib.util
import os

SPRACHEN = ("de", "en")           # was Scrinium anbietet
# Der Ordner mit den Sprachdateien - ein Unterordner dieses Pakets.
ORDNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprache")

_aktuelle_sprache = "de"
_texte: dict = {}


def _lade(sprache: str) -> dict:
    """Laedt eine Sprachdatei. Fehlt sie, bleibt die alte aktiv."""
    global _texte
    pfad = os.path.join(ORDNER, f"{sprache}.py")
    if not os.path.isfile(pfad):
        return _texte                    # nicht da: alte behalten
    try:
        spec = importlib.util.spec_from_file_location(f"_scrinium_{sprache}", pfad)
        if spec is None or spec.loader is None:
            return _texte
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        texte = getattr(modul, "TEXTE", None)
        if isinstance(texte, dict):
            _texte = texte
    except Exception:
        pass                                # kaputt: nicht crashen
    return _texte


def sprache_setzen(sprache: str) -> str:
    """Wechselt die Sprache. Gibt den echten Namen zurueck."""
    global _aktuelle_sprache
    if sprache in SPRACHEN:
        _aktuelle_sprache = sprache
        _lade(sprache)
    return _aktuelle_sprache


def sprache() -> str:
    return _aktuelle_sprache


def sprachen() -> tuple:
    """Welche Sprachen es gibt - aus den Dateien, nicht aus einer Liste."""
    gefunden = []
    try:
        for datei in sorted(os.listdir(ORDNER)):
            if datei.endswith(".py") and not datei.startswith("_"):
                gefunden.append(datei[:-3])
    except OSError:
        pass
    return tuple(gefunden) or SPRACHEN


def sag(schluessel: str, **platzhalter) -> str:
    """Der Text zu einem Schluessel.

    Fehlt er, kommt der Schluessel selbst zurueck - das ist Absicht, damit
    man beim Testen sofort sieht "ah, der Text fehlt" und nicht "irgendwas
    Falsches".
    """
    if not _texte:
        _lade(_aktuelle_sprache)

    text = _texte.get(schluessel)
    if text is None:
        # Vielleicht ist es in einer anderen Sprache da - dann zeigen wir
        # wenigstens, was der Schluessel bedeutet.
        for sprache_ in SPRACHEN:
            _lade(sprache_)
            if schluessel in _texte:
                text = _texte[schluessel]
                break
    if text is None:
        return schluessel

    if platzhalter:
        try:
            return text.format(**platzhalter)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def alle_schluessel() -> list:
    """Welche Texte es gibt - zum Pruefen, ob was fehlt."""
    return sorted(_texte)