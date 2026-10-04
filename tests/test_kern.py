"""Der Scrinium-Kern: findet Werkzeuge, ohne sie zu kennen.

Der wichtigste Test hier ist `test_finzt_werkzeug_ohne_kenntnism`: der Kern
laedt ein Werkzeug, das er beim Schreiben nicht kannte. Wenn das klappt,
kann jedes zukuenftige Werkzeug einfach als Ordner dazukommen.
"""

from __future__ import annotations

import os
import sys

import pytest

from scrinium import kern


# ---------------------------------------------------------------------------
# Pfade: nichts ist fest eingetragen
# ---------------------------------------------------------------------------
def test_basis_verzeichnis_ist_der_programmordner():
    basis = kern.basis_verzeichnis()
    assert os.path.isdir(basis)
    assert os.path.isfile(os.path.join(basis, "scrinium", "kern.py"))


def test_tools_verzeichnis_ist_unter_der_basis():
    tools = kern.tools_verzeichnis()
    assert tools.startswith(kern.basis_verzeichnis())
    assert os.path.isdir(tools)


def test_tools_wird_angelegt_wenn_fehlend(tmp_path):
    ziel = tmp_path / "leer"
    # tools_verzeichnis() legt selbst an - genau das wird hier benutzt
    assert not ziel.exists()
    os.makedirs(ziel)
    assert kern.finde_werkzeuge(str(ziel)) == []


# ---------------------------------------------------------------------------
# Werkzeuge finden
# ---------------------------------------------------------------------------
def _werkzeug(ordner: str, inhalt: str, datei: str = "__init__.py") -> None:
    os.makedirs(ordner, exist_ok=True)
    with open(os.path.join(ordner, datei), "w", encoding="utf-8") as fh:
        fh.write(inhalt)


GUTES_WERKZEUG = '''
NAME = "Testwerkzeug"

def pruefe():
    return True, ""

def starte():
    return {"text": "fertig", "aktionen": [], "daten": {}}
'''


def test_ohne_werkzeuge_leer(tmp_path):
    assert kern.finde_werkzeuge(str(tmp_path)) == []


def test_ordner_ohne_init_py_ist_kein_werkzeug(tmp_path):
    (tmp_path / "notiz.txt").write_text("kein werkzeug", encoding="utf-8")
    (tmp_path / "bild.jpg").write_bytes(b"x")
    _werkzeug(str(tmp_path / "_leer"), "NAME = 'x'\n", datei="README.md")
    assert kern.finde_werkzeuge(str(tmp_path)) == []


def test_pycache_wird_ignoriert(tmp_path):
    _werkzeug(str(tmp_path / "__pycache__"), GUTES_WERKZEUG)
    _werkzeug(str(tmp_path / ".git"), GUTES_WERKZEUG)
    assert kern.finde_werkzeuge(str(tmp_path)) == []


def test_finzt_werkzeug_ohne_kenntnism(tmp_path):
    """Der Kern laedt etwas, von dem er beim Schreiben nichts wusste."""
    _werkzeug(str(tmp_path / "_erfunden"), GUTES_WERKZEUG)
    ws = kern.finde_werkzeuge(str(tmp_path))
    assert len(ws) == 1
    w = ws[0]
    assert w.name == "Testwerkzeug"
    assert not w.fehler
    assert w.id == "erfunden"


def test_nach_name_sortiert(tmp_path):
    _werkzeug(str(tmp_path / "_zebra"), 'NAME = "Zebra"\nBETA=False\ndef starte(): return {"text":"x"}\n')
    _werkzeug(str(tmp_path / "_anton"), 'NAME = "Anton"\nBETA=False\ndef starte(): return {"text":"x"}\n')
    assert [w.name for w in kern.finde_werkzeuge(str(tmp_path))] == ["Anton", "Zebra"]


# ---------------------------------------------------------------------------
# Fehler duerfen nicht stillschweigend passieren
# ---------------------------------------------------------------------------
def test_kaputtes_werkzeug_wird_gemeldet_nicht_ignoriert(tmp_path):
    _werkzeug(str(tmp_path / "_kaputt"), "das ist kein python(((")
    ws = kern.finde_werkzeuge(str(tmp_path))
    assert len(ws) == 1
    assert ws[0].fehler, "ein kaputtes Werkzeug muss einen Fehler melden"


def test_starte_ohne_text_ist_ein_fehler(tmp_path):
    _werkzeug(str(tmp_path / "_leertext"), 'NAME = "leer"\ndef starte(): return {}\n')
    w = kern.finde_werkzeuge(str(tmp_path))[0]
    assert w.starte()["fehler"] is True


def test_starte_mit_falschem_typ_ist_ein_fehler(tmp_path):
    _werkzeug(str(tmp_path / "_falsch"),
              'NAME = "falsch"\ndef starte(): return "kein dict"\n')
    w = kern.finde_werkzeuge(str(tmp_path))[0]
    assert w.starte()["fehler"] is True


def test_absturz_wird_zurueckgemeldet(tmp_path):
    _werkzeug(str(tmp_path / "_absturz"),
              'NAME = "absturz"\ndef starte(): raise RuntimeError("kaputt")\n')
    w = kern.finde_werkzeuge(str(tmp_path))[0]
    ergebnis = w.starte()
    assert ergebnis["fehler"] is True
    assert "kaputt" in ergebnis["text"]


def test_werkzeug_ohne_starte_wird_gemeldet(tmp_path):
    _werkzeug(str(tmp_path / "_nurname"), 'NAME = "nur name"\n')
    w = kern.finde_werkzeuge(str(tmp_path))[0]
    assert w.starte()["fehler"] is True


# ---------------------------------------------------------------------------
# pruefe(): das Werkzeug darf selbst entscheiden
# ---------------------------------------------------------------------------
def test_pruefe_ohne_funktion_ist_erlaubt(tmp_path):
    _werkzeug(str(tmp_path / "_ohne"), 'NAME = "ohne pruefe"\ndef starte(): return {"text":"x"}\n')
    w = kern.finde_werkzeuge(str(tmp_path))[0]
    assert w.pruefe() == (True, "")


def test_pruefe_darf_sperren(tmp_path):
    _werkzeug(str(tmp_path / "_gesperrt"),
              'NAME = "zu"\ndef pruefe(): return False, "kein Zugriff"\n'
              'def starte(): return {"text":"x"}\n')
    w = kern.finde_werkzeuge(str(tmp_path))[0]
    ok, grund = w.pruefe()
    assert ok is False and "Zugriff" in grund


def test_pruefe_ohne_zweiten_wert(tmp_path):
    _werkzeug(str(tmp_path / "_bool"),
              'NAME = "b"\ndef pruefe(): return True\ndef starte(): return {"text":"x"}\n')
    assert kern.finde_werkzeuge(str(tmp_path))[0].pruefe()[0] is True


def test_pruefe_stuerzt_nicht_ab(tmp_path):
    _werkzeug(str(tmp_path / "_absturz2"),
              'NAME = "a"\ndef pruefe(): raise RuntimeError("peng")\n'
              'def starte(): return {"text":"x"}\n')
    ok, grund = kern.finde_werkzeuge(str(tmp_path))[0].pruefe()
    assert ok is False and "abgestuerzt" in grund


# ---------------------------------------------------------------------------
# Ergebnisse werden vereinheitlicht
# ---------------------------------------------------------------------------
def test_minimaler_rueckgabewert_reicht(tmp_path):
    _werkzeug(str(tmp_path / "_mini"), 'NAME = "mini"\ndef starte(): return {"text":"ok"}\n')
    r = kern.finde_werkzeuge(str(tmp_path))[0].starte()
    assert r["text"] == "ok"
    assert r["aktionen"] == []
    assert r["daten"] == {}
    assert r["fehler"] is False


def test_kaputte_aktionen_werden_verworfen(tmp_path):
    _werkzeug(str(tmp_path / "_aktionen"),
              'NAME = "a"\ndef starte(): return '
              '{"text":"x", "aktionen": ["nur ein string", ("ok", 1)]}\n')
    r = kern.finde_werkzeuge(str(tmp_path))[0].starte()
    assert r["aktionen"] == [("ok", 1)], r["aktionen"]


def test_daten_muss_dict_sein(tmp_path):
    _werkzeug(str(tmp_path / "_daten"),
              'NAME = "d"\ndef starte(): return {"text":"x", "daten": "kein dict"}\n')
    assert kern.finde_werkzeuge(str(tmp_path))[0].starte()["daten"] == {}


def test_ergebnis_ist_immer_vollstaendig(tmp_path):
    _werkzeug(str(tmp_path / "_voll"), GUTES_WERKZEUG)
    r = kern.finde_werkzeuge(str(tmp_path))[0].starte()
    assert set(r) == {"text", "aktionen", "daten", "fehler"}


# ---------------------------------------------------------------------------
# Das echte Werkzeug im Repo
# ---------------------------------------------------------------------------
def test_downloadsorter_ist_vorhanden():
    ws = kern.finde_werkzeuge()
    assert ws, "kein Werkzeug gefunden - liegt tools/_downloadsorter vor?"
    sorter = [w for w in ws if w.id == "downloadsorter"]
    assert sorter, f"Downloads-Sortierer fehlt (gefunden: {[w.id for w in ws]})"
    w = sorter[0]
    assert not w.fehler, w.fehler
    assert w.name
    assert w.BETA if hasattr(w, "BETA") else True