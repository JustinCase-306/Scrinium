"""Der Downloads-Sortierer als Tool.

Zwei Dinge werden hier geprueft:

1.  **Der Vertrag** - gibt `check()`/`starte()` das zurueck, was der Kern
    braucht? Kennt der Test das Tool nur ueber `NAME`/`starte()`?
2.  **Das Verhalten** - sortiert er richtig, und laesst es sich undo
    machen? Das sind die Zusicherungen, auf die du dich verlassen kannst.
"""
from __future__ import annotations
import json
import os
import sys
import time
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, 'tools', '_downloadsorter')
if TOOL not in sys.path:
    sys.path.insert(0, TOOL)
from logik import regeln

@pytest.mark.parametrize('name,erwartet', [('a.pdf', 'Dokumente'), ('a.jpg', 'Bilder'), ('a.png', 'Bilder'), ('a.mp4', 'Videos'), ('a.mkv', 'Videos'), ('a.mp3', 'Musik'), ('a.flac', 'Musik'), ('a.zip', 'Archive'), ('a.exe', 'Programme'), ('a.py', 'Code'), ('a.woff2', 'Schriften')])
def test_extension_sorted_right(name, erwartet):
    kat = regeln.category_for(name)
    assert kat is not None and kat.name == erwartet

def test_extension_case_insensitive():
    assert regeln.category_for('BILD.JPG').name == 'Bilder'

def test_unknown_extension_stays():
    assert regeln.category_for('datei.qqq') is None

def test_no_extension_stays():
    assert regeln.category_for('README') is None

def test_screenshot_detected():
    assert regeln.category_for('Screenshot 2026-01-01').name == 'Bilder'

@pytest.mark.parametrize('name', ['Desktop.ini', 'thumbs.db'])
def test_system_files_not_sorted(name):
    assert regeln.category_for(name) is None

@pytest.mark.parametrize('name', ['video.mp4.crdownload', 'movie.part', 'x.partial', 'y.tmp', 'z.download', 'w.opdownload'])
def test_incomplete_detected(name):
    assert regeln.is_incomplete(name)

@pytest.mark.parametrize('name', ['a.pdf', 'b.mp4', 'Screenshot.png'])
def test_complete_not_incomplete(name):
    assert not regeln.is_incomplete(name)

def test_check_folder_ok(tmp_path):
    ok, grund = regeln.check_folder(str(tmp_path))
    assert ok and (not grund)

def test_check_folder_missing():
    ok, grund = regeln.check_folder('C:/gibt/es/nicht')
    assert not ok and 'nicht gefunden' in grund

def test_check_no_folder():
    ok, _ = regeln.check_folder('')
    assert not ok

def _datei(folder, name, size=100, alter_s=0, inhalt=None):
    p = os.path.join(str(folder), name)
    with open(p, 'wb') as fh:
        fh.write(inhalt if inhalt is not None else b'x' * size)
    if alter_s:
        t = time.time() - alter_s
        os.utime(p, (t, t))
    return p

def test_plan_sees_file(tmp_path):
    _datei(tmp_path, 'a.pdf', alter_s=300)
    plan = regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0))
    assert plan.anzahl == 1
    assert plan.dateien[0].kategorie == 'Dokumente'

def test_plan_moves_nothing(tmp_path):
    _datei(tmp_path, 'a.pdf', alter_s=300)
    regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0))
    assert sorted(os.listdir(tmp_path)) == ['a.pdf']
    assert not (tmp_path / 'Dokumente').exists()

def test_plan_respects_min_age(tmp_path):
    _datei(tmp_path, 'neu.pdf', alter_s=0)
    _datei(tmp_path, 'alt.pdf', alter_s=600)
    plan = regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=60))
    assert [d.quelle for d in plan.dateien] == [os.path.join(str(tmp_path), 'alt.pdf')]

def test_plan_skips_download(tmp_path):
    _datei(tmp_path, 'a.pdf', alter_s=300)
    _datei(tmp_path, 'film.mp4.crdownload', alter_s=300)
    plan = regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0))
    assert [os.path.basename(d.quelle) for d in plan.dateien] == ['a.pdf']
    assert any(('film' in name for name, _ in plan.skipped))

def test_plan_empty_folder(tmp_path):
    plan = regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0))
    assert plan.anzahl == 0

def test_plan_missing_folder():
    plan = regeln.plan_folder('C:/gibt/es/nicht')
    assert plan is None or plan.anzahl == 0

def test_apply_sorts_one(tmp_path):
    _datei(tmp_path, 'a.pdf', alter_s=300)
    lauf = regeln.apply_plan(regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0)))
    assert not lauf.fehler and len(lauf.moved) == 1
    assert (tmp_path / 'Dokumente' / 'a.pdf').exists()
    assert not (tmp_path / 'a.pdf').exists()

def test_content_preserved(tmp_path):
    p = _datei(tmp_path, 'a.pdf', size=2000, alter_s=300)
    inhalt = open(p, 'rb').read()
    regeln.apply_plan(regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0)))
    assert (tmp_path / 'Dokumente' / 'a.pdf').read_bytes() == inhalt

def test_collision_never_overwrites(tmp_path):
    ziel = tmp_path / 'Dokumente'
    ziel.mkdir()
    (ziel / 'rep.pdf').write_bytes(b'ALT')
    _datei(tmp_path, 'rep.pdf', alter_s=300)
    regeln.apply_plan(regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0)))
    assert (ziel / 'rep.pdf').read_bytes() == b'ALT'
    assert (ziel / 'rep_01.pdf').exists()

def test_subfolders_untouched(tmp_path):
    """Der Sortierer arbeitet nur auf der obersten Ebene.

    Unterordner zu durchsuchen waere eine bewusste Entscheidung - und
    wuerde bedeuten, dass die Zielordner beim naechsten Run wieder
    durchsucht werden. Bis dahin bleiben sie in Ruhe.
    """
    os.makedirs(tmp_path / 'Reise')
    _datei(tmp_path / 'Reise', 'urlaub.pdf', alter_s=300)
    regeln.apply_plan(regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0)))
    assert (tmp_path / 'Reise' / 'urlaub.pdf').exists()

def test_same_name_gets_own_target(tmp_path):
    """Der wahrscheinlichste echte Fall: ein Run wird zweimal ausgefuehrt,
    weil dazwischen eine Datei zurueckkam. Dann darf nichts verloren gehen.
    """
    _datei(tmp_path, 'a.pdf', alter_s=300)
    lauf1 = regeln.apply_plan(regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0)))
    assert len(lauf1.moved) == 1
    _datei(tmp_path, 'a.pdf', alter_s=300, inhalt=b'ZWEITTE_FASSUNG')
    lauf2 = regeln.apply_plan(regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0)))
    assert len(lauf2.moved) == 1
    dokumente = sorted(os.listdir(tmp_path / 'Dokumente'))
    assert dokumente == ['a.pdf', 'a_01.pdf'], dokumente
    assert (tmp_path / 'Dokumente' / 'a.pdf').read_bytes() != b'ZWEITTE_FASSUNG'

def test_second_run_finds_nothing(tmp_path):
    _datei(tmp_path, 'a.pdf', alter_s=300)
    regeln.apply_plan(regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0)))
    plan2 = regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0))
    assert plan2.anzahl == 0, 'zweiter Run muss leer sein'

def test_undo_restores(tmp_path, monkeypatch):
    _isolierte_verlaufdatei(monkeypatch, tmp_path)
    _datei(tmp_path, 'a.pdf', alter_s=300)
    _datei(tmp_path, 'b.jpg', alter_s=300)
    lauf = regeln.apply_plan(regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0)))
    assert len(lauf.moved) == 2
    anzahl, fehler = regeln.undo_run(lauf.run_id)
    assert anzahl == 2 and (not fehler)
    assert (tmp_path / 'a.pdf').exists()
    assert (tmp_path / 'b.jpg').exists()

def test_undo_keeps_content(tmp_path, monkeypatch):
    _isolierte_verlaufdatei(monkeypatch, tmp_path)
    p = _datei(tmp_path, 'a.pdf', size=999, alter_s=300)
    inhalt = open(p, 'rb').read()
    lauf = regeln.apply_plan(regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0)))
    regeln.undo_run(lauf.run_id)
    assert (tmp_path / 'a.pdf').read_bytes() == inhalt

def test_undo_removes_empty_folders(tmp_path, monkeypatch):
    _isolierte_verlaufdatei(monkeypatch, tmp_path)
    _datei(tmp_path, 'a.pdf', alter_s=300)
    lauf = regeln.apply_plan(regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0)))
    regeln.undo_run(lauf.run_id)
    assert not (tmp_path / 'Dokumente').exists(), 'leerer Ordner blieb stehen'

def test_undo_keeps_used_folder(tmp_path, monkeypatch):
    _isolierte_verlaufdatei(monkeypatch, tmp_path)
    _datei(tmp_path, 'a.pdf', alter_s=300)
    lauf = regeln.apply_plan(regeln.plan_folder(str(tmp_path), _cfg(tmp_path, min_age=0)))
    (tmp_path / 'Dokumente' / 'wichtig.txt').write_bytes(b'bleibt')
    regeln.undo_run(lauf.run_id)
    assert (tmp_path / 'Dokumente' / 'wichtig.txt').exists()

def test_undo_unknown_run(tmp_path, monkeypatch):
    _isolierte_verlaufdatei(monkeypatch, tmp_path)
    anzahl, fehler = regeln.undo_run('gibt-es-nicht')
    assert anzahl == 0 and fehler

def test_tool_names_itself():
    from scrinium import core
    ws = {w.id: w for w in core.find_tools()}
    assert 'downloadsorter' in ws, f'gefunden: {list(ws)}'
    w = ws['downloadsorter']
    assert not w.fehler, w.fehler
    assert w.name == 'Downloads-Sortierer'

def test_tool_returns_standard_shape(tmp_path, monkeypatch):
    from scrinium import core
    _isolierte_verlaufdatei(monkeypatch, tmp_path)
    _datei(tmp_path, 'a.pdf', alter_s=300)
    _datei(tmp_path, 'b.jpg', alter_s=300)
    _cfg_schreiben(tmp_path)
    w = {x.id: x for x in core.find_tools()}['downloadsorter']
    assert w.check()[0] is True
    result = w.starte()
    assert set(result) == {'text', 'actions', 'data', 'fehler'}
    assert result['fehler'] is False
    assert '2' in result['text']
    assert len(result['actions']) == 1, 'nach dem Sortieren muss Undo da sein'
    assert result['actions'][0][0], 'die Aktion braucht einen sichtbaren Text'
    assert result['data']['moved'] == 2
    assert (tmp_path / 'Dokumente' / 'a.pdf').exists()

def test_tool_reports_missing_folder(tmp_path, monkeypatch):
    from scrinium import core
    import scrinium.settings as rahmen
    monkeypatch.setenv('APPDATA', str(tmp_path / 'appdata'))
    rahmen.config_dir()
    _cfg_schreiben(tmp_path, path='C:/gibt/es/nicht')
    w = {x.id: x for x in core.find_tools()}['downloadsorter']
    ok, grund = w.check()
    assert ok is False and grund

def test_tool_readable_in_both_languages(tmp_path, monkeypatch):
    from scrinium import core, texts
    import scrinium.settings as rahmen
    monkeypatch.setenv('APPDATA', str(tmp_path / 'appdata'))
    rahmen.config_dir()
    w = {x.id: x for x in core.find_tools()}['downloadsorter']
    for language, text, action in (('de', 'einsortiert', 'Rueckgaengig'), ('en', 'Filed', 'Undo')):
        d = tmp_path / language
        d.mkdir()
        _datei(d, 'a.pdf', alter_s=300)
        _datei(d, 'b.jpg', alter_s=300)
        texts.set_language(language)
        _cfg_schreiben(d, language=language)
        try:
            result = w.starte()
            assert text in result['text'], f"[{language}] {result['text']}"
            assert result['actions'][0][0] == action, result['actions']
        finally:
            texts.set_language('de')

def _cfg(tmp_path, min_age=0):

    class _C:
        downloads_min_age = min_age
    return _C()

def _cfg_schreiben(basis, language='de', path=None):
    import scrinium.settings as rahmen
    ziel = path or str(basis).replace('\\', '/')
    with open(rahmen.config_path(), 'w', encoding='utf-8') as fh:
        json.dump({'language': language, 'downloads_folder': ziel, 'downloads_min_age': 0}, fh)

def _isolierte_verlaufdatei(monkeypatch, tmp_path):
    """Verlauf in einen temp-Ordner legen, nicht in die echte Config."""
    import scrinium.settings as rahmen
    monkeypatch.setenv('APPDATA', str(tmp_path / 'appdata'))
    rahmen.config_dir()
    return True
