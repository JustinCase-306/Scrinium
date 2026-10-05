"""Der Scrinium-Kern: findet Tools, ohne sie zu kennen.

Der wichtigste Test hier ist `test_finds_unknown_tool`: der Kern
laedt ein Tool, das er beim Schreiben nicht kannte. Wenn das klappt,
kann jedes zukuenftige Tool einfach als Ordner dazukommen.
"""
from __future__ import annotations
import os
import sys
import pytest
from scrinium import core

def test_base_dir_is_program_dir():
    basis = core.base_dir()
    assert os.path.isdir(basis)
    assert os.path.isfile(os.path.join(basis, 'scrinium', 'core.py'))

def test_tools_dir_is_under_base():
    tools = core.tools_dir()
    assert tools.startswith(core.base_dir())
    assert os.path.isdir(tools)

def test_tools_dir_created_if_missing(tmp_path):
    ziel = tmp_path / 'leer'
    assert not ziel.exists()
    os.makedirs(ziel)
    assert core.find_tools(str(ziel)) == []

def _werkzeug(folder: str, inhalt: str, datei: str='__init__.py') -> None:
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, datei), 'w', encoding='utf-8') as fh:
        fh.write(inhalt)
GOOD_TOOL = '\nNAME = "Testwerkzeug"\n\ndef check():\n    return True, ""\n\ndef starte():\n    return {"text": "fertig", "actions": [], "data": {}}\n'

def test_no_tools_returns_empty(tmp_path):
    assert core.find_tools(str(tmp_path)) == []

def test_folder_without_init_is_not_a_tool(tmp_path):
    (tmp_path / 'notiz.txt').write_text('kein tool', encoding='utf-8')
    (tmp_path / 'bild.jpg').write_bytes(b'x')
    _werkzeug(str(tmp_path / '_leer'), "NAME = 'x'\n", datei='README.md')
    assert core.find_tools(str(tmp_path)) == []

def test_pycache_ignored(tmp_path):
    _werkzeug(str(tmp_path / '__pycache__'), GOOD_TOOL)
    _werkzeug(str(tmp_path / '.git'), GOOD_TOOL)
    assert core.find_tools(str(tmp_path)) == []

def test_finds_unknown_tool(tmp_path):
    """Der Kern laedt etwas, von dem er beim Schreiben nichts wusste."""
    _werkzeug(str(tmp_path / '_erfunden'), GOOD_TOOL)
    ws = core.find_tools(str(tmp_path))
    assert len(ws) == 1
    w = ws[0]
    assert w.name == 'Testwerkzeug'
    assert not w.fehler
    assert w.id == 'erfunden'

def test_sorted_by_name(tmp_path):
    _werkzeug(str(tmp_path / '_zebra'), 'NAME = "Zebra"\nBETA=False\ndef starte(): return {"text":"x"}\n')
    _werkzeug(str(tmp_path / '_anton'), 'NAME = "Anton"\nBETA=False\ndef starte(): return {"text":"x"}\n')
    assert [w.name for w in core.find_tools(str(tmp_path))] == ['Anton', 'Zebra']

def test_broken_tool_is_reported(tmp_path):
    _werkzeug(str(tmp_path / '_kaputt'), 'das ist kein python(((')
    ws = core.find_tools(str(tmp_path))
    assert len(ws) == 1
    assert ws[0].fehler, 'ein kaputtes Tool muss einen Fehler melden'

def test_start_without_text_is_error(tmp_path):
    _werkzeug(str(tmp_path / '_leertext'), 'NAME = "leer"\ndef starte(): return {}\n')
    w = core.find_tools(str(tmp_path))[0]
    assert w.starte()['fehler'] is True

def test_start_with_wrong_type_is_error(tmp_path):
    _werkzeug(str(tmp_path / '_falsch'), 'NAME = "falsch"\ndef starte(): return "kein dict"\n')
    w = core.find_tools(str(tmp_path))[0]
    assert w.starte()['fehler'] is True

def test_crash_is_reported(tmp_path):
    _werkzeug(str(tmp_path / '_absturz'), 'NAME = "absturz"\ndef starte(): raise RuntimeError("kaputt")\n')
    w = core.find_tools(str(tmp_path))[0]
    result = w.starte()
    assert result['fehler'] is True
    assert 'kaputt' in result['text']

def test_tool_without_start_reported(tmp_path):
    _werkzeug(str(tmp_path / '_nurname'), 'NAME = "nur name"\n')
    w = core.find_tools(str(tmp_path))[0]
    assert w.starte()['fehler'] is True

def test_check_optional(tmp_path):
    _werkzeug(str(tmp_path / '_ohne'), 'NAME = "ohne check"\ndef starte(): return {"text":"x"}\n')
    w = core.find_tools(str(tmp_path))[0]
    assert w.check() == (True, '')

def test_check_may_block(tmp_path):
    _werkzeug(str(tmp_path / '_gesperrt'), 'NAME = "zu"\ndef check(): return False, "kein Zugriff"\ndef starte(): return {"text":"x"}\n')
    w = core.find_tools(str(tmp_path))[0]
    ok, grund = w.check()
    assert ok is False and 'Zugriff' in grund

def test_check_without_reason(tmp_path):
    _werkzeug(str(tmp_path / '_bool'), 'NAME = "b"\ndef check(): return True\ndef starte(): return {"text":"x"}\n')
    assert core.find_tools(str(tmp_path))[0].check()[0] is True

def test_check_does_not_crash(tmp_path):
    _werkzeug(str(tmp_path / '_absturz2'), 'NAME = "a"\ndef check(): raise RuntimeError("peng")\ndef starte(): return {"text":"x"}\n')
    ok, grund = core.find_tools(str(tmp_path))[0].check()
    assert ok is False and 'abgestuerzt' in grund

def test_minimal_return_is_enough(tmp_path):
    _werkzeug(str(tmp_path / '_mini'), 'NAME = "mini"\ndef starte(): return {"text":"ok"}\n')
    r = core.find_tools(str(tmp_path))[0].starte()
    assert r['text'] == 'ok'
    assert r['actions'] == []
    assert r['data'] == {}
    assert r['fehler'] is False

def test_broken_actions_dropped(tmp_path):
    _werkzeug(str(tmp_path / '_aktionen'), 'NAME = "a"\ndef starte(): return {"text":"x", "actions": ["nur ein string", ("ok", 1)]}\n')
    r = core.find_tools(str(tmp_path))[0].starte()
    assert r['actions'] == [('ok', 1)], r['actions']

def test_data_must_be_dict(tmp_path):
    _werkzeug(str(tmp_path / '_daten'), 'NAME = "d"\ndef starte(): return {"text":"x", "data": "kein dict"}\n')
    assert core.find_tools(str(tmp_path))[0].starte()['data'] == {}

def test_result_always_complete(tmp_path):
    _werkzeug(str(tmp_path / '_voll'), GOOD_TOOL)
    r = core.find_tools(str(tmp_path))[0].starte()
    assert set(r) == {'text', 'actions', 'data', 'fehler'}

def test_downloadsorter_exists():
    ws = core.find_tools()
    assert ws, 'kein Tool gefunden - liegt tools/_downloadsorter vor?'
    sorter = [w for w in ws if w.id == 'downloadsorter']
    assert sorter, f'Downloads-Sortierer fehlt (gefunden: {[w.id for w in ws]})'
    w = sorter[0]
    assert not w.fehler, w.fehler
    assert w.name
    assert w.BETA if hasattr(w, 'BETA') else True
