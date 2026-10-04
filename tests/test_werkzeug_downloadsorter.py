"""Der Downloads-Sortierer als Werkzeug.

Zwei Dinge werden hier geprueft:

1.  **Der Vertrag** - gibt `pruefe()`/`starte()` das zurueck, was der Kern
    braucht? Kennt der Test das Werkzeug nur ueber `NAME`/`starte()`?
2.  **Das Verhalten** - sortiert er richtig, und laesst es sich rueckgaengig
    machen? Das sind die Zusicherungen, auf die du dich verlassen kannst.
"""

from __future__ import annotations

import json
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "_downloadsorter")
if TOOL not in sys.path:
    sys.path.insert(0, TOOL)

from logik import regeln                                     # noqa: E402


# ---------------------------------------------------------------------------
# Kategorien
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name,erwartet", [
    ("a.pdf", "Dokumente"),
    ("a.jpg", "Bilder"),
    ("a.png", "Bilder"),
    ("a.mp4", "Videos"),
    ("a.mkv", "Videos"),
    ("a.mp3", "Musik"),
    ("a.flac", "Musik"),
    ("a.zip", "Archive"),
    ("a.exe", "Programme"),
    ("a.py", "Code"),
    ("a.woff2", "Schriften"),
])
def test_endung_richtig_eingeordnet(name, erwartet):
    kat = regeln.kategorie_fuer(name)
    assert kat is not None and kat.name == erwartet


def test_endung_ist_nicht_case_sensitiv():
    assert regeln.kategorie_fuer("BILD.JPG").name == "Bilder"


def test_unbekannte_endung_liegt_bleiben():
    assert regeln.kategorie_fuer("datei.qqq") is None


def test_keine_endung_bleibt_liegen():
    assert regeln.kategorie_fuer("README") is None


def test_screenshot_wird_erkannt():
    assert regeln.kategorie_fuer("Screenshot 2026-01-01").name == "Bilder"


@pytest.mark.parametrize("name", ["Desktop.ini", "thumbs.db"])
def test_systemdateien_fehlen_fuer_die_einordnung(name):
    assert regeln.kategorie_fuer(name) is None


@pytest.mark.parametrize("name", [
    "video.mp4.crdownload", "movie.part", "x.partial",
    "y.tmp", "z.download", "w.opdownload",
])
def test_unvollstaendige_downloads_erkannt(name):
    assert regeln.ist_unvollstaendig(name)


@pytest.mark.parametrize("name", ["a.pdf", "b.mp4", "Screenshot.png"])
def test_fertige_dateien_nicht_als_unvollstaendig(name):
    assert not regeln.ist_unvollstaendig(name)


# ---------------------------------------------------------------------------
# Ordner-Zugriff
# ---------------------------------------------------------------------------
def test_pruefe_ortner_ok(tmp_path):
    ok, grund = regeln.pruefe_ordner(str(tmp_path))
    assert ok and not grund


def test_pruefe_ordner_fehlt():
    ok, grund = regeln.pruefe_ordner("C:/gibt/es/nicht")
    assert not ok and "nicht gefunden" in grund


def test_pruefe_kein_ordner():
    ok, _ = regeln.pruefe_ordner("")
    assert not ok


# ---------------------------------------------------------------------------
# Plan: sieht alles, bewegt nichts
# ---------------------------------------------------------------------------
def _datei(ordner, name, groesse=100, alter_s=0, inhalt=None):
    p = os.path.join(str(ordner), name)
    with open(p, "wb") as fh:
        fh.write(inhalt if inhalt is not None else b"x" * groesse)
    if alter_s:
        t = time.time() - alter_s
        os.utime(p, (t, t))
    return p


def test_plan_sieht_datei(tmp_path):
    _datei(tmp_path, "a.pdf", alter_s=300)
    plan = regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0))
    assert plan.anzahl == 1
    assert plan.dateien[0].kategorie == "Dokumente"


def test_plan_bewegt_nichts(tmp_path):
    _datei(tmp_path, "a.pdf", alter_s=300)
    regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0))
    assert sorted(os.listdir(tmp_path)) == ["a.pdf"]
    assert not (tmp_path / "Dokumente").exists()


def test_plan_respektiert_min_age(tmp_path):
    _datei(tmp_path, "neu.pdf", alter_s=0)
    _datei(tmp_path, "alt.pdf", alter_s=600)
    plan = regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=60))
    assert [d.quelle for d in plan.dateien] == [os.path.join(str(tmp_path), "alt.pdf")]


def test_plan_ueberspringt_download(tmp_path):
    _datei(tmp_path, "a.pdf", alter_s=300)
    _datei(tmp_path, "film.mp4.crdownload", alter_s=300)
    plan = regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0))
    assert [os.path.basename(d.quelle) for d in plan.dateien] == ["a.pdf"]
    assert any("film" in name for name, _ in plan.uebersprungen)


def test_plan_leerer_ordner(tmp_path):
    plan = regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0))
    assert plan.anzahl == 0


def test_plan_fehlender_ordner():
    plan = regeln.ordner_planen("C:/gibt/es/nicht")
    assert plan is None or plan.anzahl == 0


# ---------------------------------------------------------------------------
# Anwenden
# ---------------------------------------------------------------------------
def test_anwenden_sortiert_ein(tmp_path):
    _datei(tmp_path, "a.pdf", alter_s=300)
    lauf = regeln.plan_anwenden(
        regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0)))
    assert not lauf.fehler and len(lauf.verschoben) == 1
    assert (tmp_path / "Dokumente" / "a.pdf").exists()
    assert not (tmp_path / "a.pdf").exists()


def test_inhalt_bleibt_erhalten(tmp_path):
    p = _datei(tmp_path, "a.pdf", groesse=2000, alter_s=300)
    inhalt = open(p, "rb").read()
    regeln.plan_anwenden(regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0)))
    assert (tmp_path / "Dokumente" / "a.pdf").read_bytes() == inhalt


def test_namenskonflikt_ueberschreibt_nie(tmp_path):
    ziel = tmp_path / "Dokumente"
    ziel.mkdir()
    (ziel / "rep.pdf").write_bytes(b"ALT")
    _datei(tmp_path, "rep.pdf", alter_s=300)
    regeln.plan_anwenden(regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0)))
    assert (ziel / "rep.pdf").read_bytes() == b"ALT"
    assert (ziel / "rep_01.pdf").exists()


def test_unterordner_werden_nicht_angefasst(tmp_path):
    """Der Sortierer arbeitet nur auf der obersten Ebene.

    Unterordner zu durchsuchen waere eine bewusste Entscheidung - und
    wuerde bedeuten, dass die Zielordner beim naechsten Lauf wieder
    durchsucht werden. Bis dahin bleiben sie in Ruhe.
    """
    os.makedirs(tmp_path / "Reise")
    _datei(tmp_path / "Reise", "urlaub.pdf", alter_s=300)
    regeln.plan_anwenden(
        regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0)))
    assert (tmp_path / "Reise" / "urlaub.pdf").exists()


def test_gleichnamige_aus_dem_verlauf_bekommen_eigenes_ziel(tmp_path):
    """Der wahrscheinlichste echte Fall: ein Lauf wird zweimal ausgefuehrt,
    weil dazwischen eine Datei zurueckkam. Dann darf nichts verloren gehen.
    """
    _datei(tmp_path, "a.pdf", alter_s=300)
    lauf1 = regeln.plan_anwenden(
        regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0)))
    assert len(lauf1.verschoben) == 1

    # gleiche Datei kommt zurueck, zweiter Lauf
    _datei(tmp_path, "a.pdf", alter_s=300, inhalt=b"ZWEITTE_FASSUNG")
    lauf2 = regeln.plan_anwenden(
        regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0)))
    assert len(lauf2.verschoben) == 1

    dokumente = sorted(os.listdir(tmp_path / "Dokumente"))
    assert dokumente == ["a.pdf", "a_01.pdf"], dokumente
    assert (tmp_path / "Dokumente" / "a.pdf").read_bytes() != b"ZWEITTE_FASSUNG"


def test_zweiter_lauf_findet_nichts(tmp_path):
    _datei(tmp_path, "a.pdf", alter_s=300)
    regeln.plan_anwenden(regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0)))
    plan2 = regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0))
    assert plan2.anzahl == 0, "zweiter Lauf muss leer sein"


# ---------------------------------------------------------------------------
# Rueckgaengig
# ---------------------------------------------------------------------------
def test_rueckgaengig_stellt_wieder_her(tmp_path, monkeypatch):
    _isolierte_verlaufdatei(monkeypatch, tmp_path)
    _datei(tmp_path, "a.pdf", alter_s=300)
    _datei(tmp_path, "b.jpg", alter_s=300)
    lauf = regeln.plan_anwenden(
        regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0)))
    assert len(lauf.verschoben) == 2

    anzahl, fehler = regeln.lauf_rueckgaengig(lauf.run_id)
    assert anzahl == 2 and not fehler
    assert (tmp_path / "a.pdf").exists()
    assert (tmp_path / "b.jpg").exists()


def test_rueckgaengig_behaelt_inhalt(tmp_path, monkeypatch):
    _isolierte_verlaufdatei(monkeypatch, tmp_path)
    p = _datei(tmp_path, "a.pdf", groesse=999, alter_s=300)
    inhalt = open(p, "rb").read()
    lauf = regeln.plan_anwenden(
        regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0)))
    regeln.lauf_rueckgaengig(lauf.run_id)
    assert (tmp_path / "a.pdf").read_bytes() == inhalt


def test_rueckgaengig_raeumt_leere_ordner(tmp_path, monkeypatch):
    _isolierte_verlaufdatei(monkeypatch, tmp_path)
    _datei(tmp_path, "a.pdf", alter_s=300)
    lauf = regeln.plan_anwenden(
        regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0)))
    regeln.lauf_rueckgaengig(lauf.run_id)
    assert not (tmp_path / "Dokumente").exists(), "leerer Ordner blieb stehen"


def test_rueckgaengig_behaelt_ordner_mit_anderen_dateien(tmp_path, monkeypatch):
    _isolierte_verlaufdatei(monkeypatch, tmp_path)
    _datei(tmp_path, "a.pdf", alter_s=300)
    lauf = regeln.plan_anwenden(
        regeln.ordner_planen(str(tmp_path), _cfg(tmp_path, min_age=0)))
    (tmp_path / "Dokumente" / "wichtig.txt").write_bytes(b"bleibt")
    regeln.lauf_rueckgaengig(lauf.run_id)
    assert (tmp_path / "Dokumente" / "wichtig.txt").exists()


def test_rueckgaengig_unbekannter_lauf(tmp_path, monkeypatch):
    _isolierte_verlaufdatei(monkeypatch, tmp_path)
    anzahl, fehler = regeln.lauf_rueckgaengig("gibt-es-nicht")
    assert anzahl == 0 and fehler


# ---------------------------------------------------------------------------
# Das Werkzeug als Werkzeug
# ---------------------------------------------------------------------------
def test_werkzeug_nennt_sich_beim_namen():
    from scrinium import kern

    ws = {w.id: w for w in kern.finde_werkzeuge()}
    assert "downloadsorter" in ws, f"gefunden: {list(ws)}"
    w = ws["downloadsorter"]
    assert not w.fehler, w.fehler
    assert w.name == "Downloads-Sortierer"


def test_werkzeug_laeuft_und_gibt_das_standardformat(tmp_path, monkeypatch):
    from scrinium import kern

    _isolierte_verlaufdatei(monkeypatch, tmp_path)
    _datei(tmp_path, "a.pdf", alter_s=300)
    _datei(tmp_path, "b.jpg", alter_s=300)
    _cfg_schreiben(tmp_path)

    w = {x.id: x for x in kern.finde_werkzeuge()}["downloadsorter"]
    assert w.pruefe()[0] is True

    ergebnis = w.starte()
    assert set(ergebnis) == {"text", "aktionen", "daten", "fehler"}
    assert ergebnis["fehler"] is False
    assert "2" in ergebnis["text"]
    assert len(ergebnis["aktionen"]) == 1, "nach dem Sortieren muss Undo da sein"
    assert ergebnis["aktionen"][0][0], "die Aktion braucht einen sichtbaren Text"
    assert ergebnis["daten"]["verschoben"] == 2
    assert (tmp_path / "Dokumente" / "a.pdf").exists()


def test_werkzeug_meldet_fehlenden_ordner(tmp_path, monkeypatch):
    from scrinium import kern
    import scrinium.einstellungen as rahmen

    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    rahmen.config_ordner()
    _cfg_schreiben(tmp_path, pfad="C:/gibt/es/nicht")

    w = {x.id: x for x in kern.finde_werkzeuge()}["downloadsorter"]
    ok, grund = w.pruefe()
    assert ok is False and grund


def test_werkzeug_ist_in_beiden_sprachen_lesbar(tmp_path, monkeypatch):
    from scrinium import kern, texte
    import scrinium.einstellungen as rahmen

    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    rahmen.config_ordner()

    w = {x.id: x for x in kern.finde_werkzeuge()}["downloadsorter"]

    for sprache, text, aktion in (("de", "einsortiert", "Rueckgaengig"),
                                  ("en", "Filed", "Undo")):
        d = tmp_path / sprache
        d.mkdir()
        _datei(d, "a.pdf", alter_s=300)
        _datei(d, "b.jpg", alter_s=300)
        texte.sprache_setzen(sprache)
        _cfg_schreiben(d, sprache=sprache)
        try:
            ergebnis = w.starte()
            assert text in ergebnis["text"], f"[{sprache}] {ergebnis['text']}"
            assert ergebnis["aktionen"][0][0] == aktion, ergebnis["aktionen"]
        finally:
            texte.sprache_setzen("de")


# ---------------------------------------------------------------------------
# Helfer
# ---------------------------------------------------------------------------
def _cfg(tmp_path, min_age=0):
    class _C:
        downloads_min_age = min_age
    return _C()


def _cfg_schreiben(basis, sprache="de", pfad=None):
    import scrinium.einstellungen as rahmen

    ziel = pfad or str(basis).replace("\\", "/")
    with open(rahmen.config_pfad(), "w", encoding="utf-8") as fh:
        json.dump({"sprache": sprache, "downloads_ordner": ziel,
                   "downloads_min_age": 0}, fh)


def _isolierte_verlaufdatei(monkeypatch, tmp_path):
    """Verlauf in einen temp-Ordner legen, nicht in die echte Config."""
    import scrinium.einstellungen as rahmen

    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    rahmen.config_ordner()
    return True