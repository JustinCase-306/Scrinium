"""Werkzeuge und eigene Sortierregeln in den Settings.

Regression, die hier entstanden ist und nicht wieder passieren soll:

`werkzeug_hinzufuegen` suchte nach dem Text ``def start`` und lehnte
damit den mitgelieferten Sortierer ab - dessen Funktion heisst
``starte``. Ein Nutzer, der ein eigenes Werkzeug hinzufuegt, haette
"KEIN WERKZEUG" bekommen, obwohl es eines ist.

Hier steht beides: `start` und `starte` sind gueltig, alles ohne
Startfunktion nicht.
"""

from __future__ import annotations

import json

import pytest

from scrinium.settings import Settings


# --------------------------------------------------------------------------
# eigene Regeln
# --------------------------------------------------------------------------
def test_regel_bekommt_einen_punkt():
    e = Settings.standard()
    regel = e.regel_hinzufuegen("endung", "xyz", "Dokumente")
    assert regel == {"art": "endung", "wert": ".xyz", "ziel": "Dokumente"}


def test_regel_ignoriert_gross_klein():
    e = Settings.standard()
    regel = e.regel_hinzufuegen("ENDUNG", ".ABC", "Bilder")
    assert regel["wert"] == ".abc"
    assert regel["art"] == "endung"


def test_muster_bekommt_keinen_punkt():
    e = Settings.standard()
    regel = e.regel_hinzufuegen("muster", "rechnung*", "Dokumente")
    assert regel["wert"] == "rechnung*"
    assert regel["art"] == "muster"


@pytest.mark.parametrize("art,wert,ziel", [
    ("unsinn", "q", "Z"),
    ("endung", "", "Z"),
    ("muster", "", "Z"),
    ("endung", "q", ""),
])
def test_unsinnige_regeln_werden_abgelehnt(art, wert, ziel):
    e = Settings.standard()
    assert e.regel_hinzufuegen(art, wert, ziel) is None
    assert e.sortier_regeln == []


def test_doppelte_regel_nicht_zweimal():
    e = Settings.standard()
    e.regel_hinzufuegen("endung", "dup", "Z")
    e.regel_hinzufuegen("endung", ".dup", "Z")
    assert len(e.sortier_regeln) == 1


def test_regel_entfernen():
    e = Settings.standard()
    e.regel_hinzufuegen("endung", "xyz", "Dokumente")
    assert e.regel_entfernen("endung", ".xyz") is True
    assert e.sortier_regeln == []
    assert e.regel_entfernen("endung", ".xyz") is False


def test_regeln_ueberleben_neuladen(tmp_path, monkeypatch):
    """Regression: Settings.laden() verwarf list-Felder kommentarlos."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    e = Settings.standard()
    e.regel_hinzufuegen("endung", "qqq", "Dokumente")
    e.regel_hinzufuegen("muster", "rechnung*", "Bilder")
    e.speichern()

    neu = Settings.laden()
    assert len(neu.sortier_regeln) == 2
    wert = {r["wert"] for r in neu.sortier_regeln}
    assert wert == {".qqq", "rechnung*"}


def test_werkzeugliste_ueberlebt_neuladen(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    e = Settings.standard()
    e.eigene_werkzeuge.append({"pfad": "C:/x/mein", "name": "mein",
                               "quelle": "nutzer"})
    e.speichern()
    assert len(Settings.laden().eigene_werkzeuge) == 1


def test_kaputte_typen_werden_ignoriert(tmp_path, monkeypatch):
    """Aus der Datei darf keine kaputte Struktur werden."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    e = Settings.standard()
    pfad = e.speichern()

    with open(pfad, "w", encoding="utf-8") as fh:
        json.dump({"language": 42,                 # int statt str
                   "downloads_min_age": "viel",    # Text statt int
                   "sortier_regeln": "keine liste",  # str statt list
                   "eigene_werkzeuge": {"a": 1},  # dict statt list
                   "tools_enabled": ["x"]}, fh)   # list statt dict
    # dict statt list: lad() soll es verwerfen statt zu crashen
    neu = Settings.laden()
    assert neu.language == "de"               # Standard geblieben
    assert neu.downloads_min_age == 30
    assert neu.sortier_regeln == []
    assert isinstance(neu.eigene_werkzeuge, list)
    assert neu.tools_enabled == {}            # list verworfen


# --------------------------------------------------------------------------
# eigene Werkzeuge
# --------------------------------------------------------------------------
def _werkzeug(ordner, inhalt):
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "__init__.py").write_text(inhalt, encoding="utf-8")
    return str(ordner)


@pytest.mark.parametrize("start_funktion", [
    'NAME = "A"\ndef starte():\n    pass\n',
    'NAME = "B"\ndef start():\n    pass\n',
    'NAME = "C"\n\ndef starte():\n    return {}\n',
])
def test_start_und_starte_gueltig(tmp_path, start_funktion):
    """Regression: es wurde nur nach "def start" gesucht.

    Der mitgelieferte Sortierer nennt seine Funktion `starte`. Nach dem
    Bug wurde jedes echte Werkzeug als "KEIN WERKZEUG" abgewiesen.
    """
    ordner = _werkzeug(tmp_path / "w" / "mein", start_funktion)
    e = Settings.standard()
    assert e.werkzeug_hinzufuegen(ordner) == "OK"
    assert len(e.eigene_werkzeuge) == 1


@pytest.mark.parametrize("inhalt", [
    "",                                              # leere Datei
    'X = 1\ndef hilfe():\n    pass\n',              # keine Startfunktion
    'def starte():\n    pass\n',                     # kein NAME
    "nur Text, kein Code",                          # Freitext
])
def test_kein_werkzeug_wird_abgewiesen(tmp_path, inhalt):
    ordner = _werkzeug(tmp_path / "w" / "quatsch", inhalt)
    e = Settings.standard()
    assert e.werkzeug_hinzufuegen(ordner) == "KEIN WERKZEUG"
    assert e.eigene_werkzeuge == []


def test_fehlender_ordner(tmp_path):
    e = Settings.standard()
    assert e.werkzeug_hinzufuegen(str(tmp_path / "gibtsnicht")) == "ORDNER FEHLT"
    assert e.werkzeug_hinzufuegen("") == "ORDNER FEHLT"


def test_ordner_ohne_init_py(tmp_path):
    ordner = tmp_path / "leer"
    ordner.mkdir()
    e = Settings.standard()
    assert e.werkzeug_hinzufuegen(str(ordner)) == "KEIN WERKZEUG"


def test_gleiches_werkzeug_nicht_zweimal(tmp_path):
    ordner = _werkzeug(tmp_path / "w" / "mein", 'NAME = "A"\ndef starte():\n    pass\n')
    e = Settings.standard()
    assert e.werkzeug_hinzufuegen(ordner) == "OK"
    assert e.werkzeug_hinzufuegen(ordner) == "SCHON DABEI"
    assert len(e.eigene_werkzeuge) == 1


def test_werkzeug_entfernen(tmp_path):
    ordner = _werkzeug(tmp_path / "w" / "mein", 'NAME = "A"\ndef starte():\n    pass\n')
    e = Settings.standard()
    e.werkzeug_hinzufuegen(ordner)
    assert e.werkzeug_entfernen(ordner) is True
    assert e.eigene_werkzeuge == []
    assert e.werkzeug_entfernen(ordner) is False


def test_zielordner_wird_nie_uebersetzt(tmp_path, monkeypatch):
    """Die physischen Ordnernamen bleiben deutsch, immer."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    e = Settings.standard()
    e.regel_hinzufuegen("endung", "xyz", "Präsentationen")
    e.speichern()
    neu = Settings.laden()
    assert neu.sortier_regeln[0]["ziel"] == "Präsentationen"


def test_tool_schalter_ueberlebt_neuladen(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    e = Settings.standard()
    e.toggle_tool("downloadsorter", False)
    e.speichern()
    assert Settings.laden().tool_is_enabled("downloadsorter") is False

    # Standard ist an
    assert Settings.standard().tool_is_enabled("neuwerkzeug") is True