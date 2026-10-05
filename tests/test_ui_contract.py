"""Der Vertrag zwischen Oberflaeche, Python und der EXE.

Diese Fehlerklasse war der Grund fuer "von all diesen Buttons
funktioniert nur einer" - und KEIN Test hat sie gefangen:

1. ``window.html`` las ``settings.sprache``, Python liefert
   ``settings.language``. Der Sprachknopf konnte nie umschalten, weil
   der Wert immer undefined war.
2. ``bridge.choose_folder`` rief
   ``create_file_dialog(..., func=zurueck)``. Diesen Parameter gibt es
   in pywebview nicht -> TypeError. Da das JavaScript kein .catch()
   hatte, war der Fehler stumm: der Knopf tat einfach nichts.
3. ``Scrinium.spec`` bundelte ``settings.html`` und ``tools/`` nicht.
   In der EXE war die Datei nicht da, also gab ``open_settings()``
   still "" zurueck - und die Seitenleiste zeigte "noch nicht da".
4. ``tools_dir()`` benutzte ``base_dir()``, das bei einer onefile-EXE
   auf den Ordner neben der EXE zeigt statt auf ``_MEIPASS``.

Die Tests hier vergleichen die Schluessel und Dateien direkt
miteinander, damit derselbe Bruch nicht wieder unbemerkt bleibt.
"""

from __future__ import annotations

import inspect
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRINIUM = os.path.join(ROOT, "scrinium")


def lies(*teile: str) -> str:
    return open(os.path.join(ROOT, *teile), encoding="utf-8").read()


def js_teil(datei: str) -> str:
    """Nur der <script>-Block - Aussagen ueber das Verhalten der Seite."""
    s = lies("scrinium", datei)
    i = s.rfind("<script>")
    return s[i:] if i >= 0 else ""


# --------------------------------------------------------------------------
# 1. Schluessel: was Python liefert, muss das JS auch lesen
# --------------------------------------------------------------------------
def test_window_reads_the_keys_python_sends():
    """window.html darf keine Schluessel erfinden (sprache vs language)."""
    bridge = lies("scrinium", "bridge.py")
    m = re.search(r"ZUSTAND\[.settings.\] = \{(.*?)\}", bridge, re.S)
    assert m, "die settings-Struktur wurde nicht gefunden"
    geliefert = set(re.findall(r"'(\w+)':", m.group(1)))

    gelesen = set(re.findall(r"settings\.(\w+)", js_teil("window.html")))
    fehlend = gelesen - geliefert
    assert not fehlend, (
        f"window.html liest Schluessel, die Python nicht liefert: "
        f"{sorted(fehlend)}   (Python liefert: {sorted(geliefert)})")


def test_window_does_not_read_sprache():
    """Der konkrete Fehler, damit er nicht zurueckkommt."""
    assert "settings.sprache" not in js_teil("window.html")


def test_settings_window_reads_the_keys_python_sends():
    """Dasselbe fuer settings.html gegen settings_lesen()."""
    bridge = lies("scrinium", "bridge.py")
    # was settings_lesen() laut Rueckgabe enthaelt
    block = bridge[bridge.find("def settings_lesen"):]
    block = block[:block.find("\ndef ")]
    geliefert = set(re.findall(r'"(\w+)":', block))

    gelesen = set(re.findall(r"\b(?:d|dat|state)\.(\w+)",
                             js_teil("settings.html")))
    # nur die, die wirklich aus der Antwort kommen
    bekannt = {"language", "downloads_folder", "downloads_min_age",
               "regeln", "ordner", "eigene_werkzeuge",
               "tools_mitgeliefert", "texte"}
    fehlend = (gelesen & bekannt) - geliefert
    assert not fehlend, f"settings.html liest unbekannte Schluessel: {fehlend}"


# --------------------------------------------------------------------------
# 2. API-Aufrufe: jeder muss in Python existieren
# --------------------------------------------------------------------------
def test_every_api_call_exists_in_python():
    win = lies("scrinium", "window.py")
    # Die Api-Klasse: alles zwischen "class Api" und "return Api()"
    i = win.find("class Api")
    j = win.find("return Api()")
    assert i > 0 and j > i
    methoden = set(re.findall(r"def (\w+)\(", win[i:j]))

    for datei in ("window.html", "settings.html"):
        gerufen = set(re.findall(r"\b(?:API|api)\[?\.?(\w+)\(",
                                 js_teil(datei)))
        gerufen -= {"function", "then", "catch", "console", "sag", "el",
                    "document", "querySelector", "getElementById", "log",
                    "error"}
        fehlend = {g for g in gerufen if g not in methoden}
        assert not fehlend, f"{datei} ruft unbekannte API-Funktionen: {fehlend}"


def test_choose_folder_matches_the_pywebview_signature():
    """create_file_dialog hat KEINEN func-Parameter.

    Ein func=-Argument wirft TypeError. Ohne .catch() im JavaScript war
    der Knopf danach stumm - deshalb der Test hier.
    """
    webview = pytest.importorskip("webview")
    signatur = inspect.signature(webview.Window.create_file_dialog)
    assert "func" not in signatur.parameters, (
        "pywebview hat jetzt einen func-Parameter - bridge.py pruefen")

    quelle = lies("scrinium", "bridge.py")
    block = quelle[quelle.find("def choose_folder"):]
    block = block[:block.find("\ndef ")]
    assert "func=" not in block, (
        "choose_folder ruft create_file_dialog mit func= auf - das wirft "
        "TypeError und der Knopf bleibt stumm")


def test_html_reacts_to_rejected_promises():
    """Kein stummer Fehler mehr: beide Seiten haben einen Handler."""
    for datei in ("window.html", "settings.html"):
        assert "unhandledrejection" in js_teil(datei), (
            f"{datei} hat keinen unhandledrejection-Handler - ein "
            f"abgelehntes Promise bleibt dort unsichtbar")


# --------------------------------------------------------------------------
# 3. Die EXE: alles Noetige muss in der Spec stehen
# --------------------------------------------------------------------------
def test_spec_collects_settings_html_and_tools(monkeypatch):
    """Die Spec muss die Dateien wirklich EINSAMMELN, nicht nur nennen.

    Ein blosser ``assert "settings.html" in spec`` wuerde auch bei
    ``if False: html_datas.append(...)`` bestehen - genau das hat ein
    Mutationstest gezeigt. Deshalb wird der Spec-Kopf hier ausgefuehrt
    und das erzeugte Datenverzeichnis geprueft.
    """
    monkeypatch.setenv("SCRINIUM_SRC", ROOT)
    spec = lies("Scrinium.spec")
    kopf = spec[:spec.find("a = Analysis(")]
    assert kopf, "Analysis() nicht in der Spec gefunden"

    ns: dict = {}
    exec(compile(kopf, "Scrinium.spec", "exec"), ns)  # noqa: S102

    daten = (ns["asset_datas"] + ns["html_datas"] + ns["sprache_datas"]
             + ns["tools_datas"] + ns["webview_datas"])
    assert daten, "die Spec sammelt gar nichts ein"

    quellen = {os.path.normcase(str(q)) for q, _ in daten}
    erwartet = os.path.normcase(os.path.join(SCRINIUM, "settings.html"))
    assert erwartet in quellen, (
        "settings.html landet nicht in den Daten - open_settings() gibt "
        "in der EXE still '' zurueck")

    assert "tools_datas in datas" in spec or "tools_datas" in \
        spec.split("datas=")[1].split("),")[0], \
        "tools_datas wird gesammelt, aber nicht an datas uebergeben"

    ziele = [ziel for _, ziel in daten]
    assert any(z.startswith("tools") for z in ziele), (
        f"kein Werkzeugordner in den Daten: {ziele}")


def test_tools_dir_finds_bundled_tools_in_meipass(tmp_path, monkeypatch):
    """Onefile-EXE: PyInstaller entpackt nach _MEIPASS.

    ``base_dir()`` zeigt bei einer onefile-EXE auf den Ordner NEBEN der
    EXE und traf _MEIPASS nicht - deshalb war die Seitenleiste im
    fertigen Programm leer ("noch nicht da").

    Geprueft wird das Verhalten: mit gesetztem _MEIPASS muss dort
    gesucht werden. Ein blosser Stringvergleich auf "_MEIPASS" wuerde
    auch bei ``meipass = None`` bestehen.
    """
    from scrinium import core

    meipass = tmp_path / "_MEI123456"
    werkzeug = meipass / "tools" / "meinsortierer"
    werkzeug.mkdir(parents=True)
    (werkzeug / "__init__.py").write_text(
        'NAME = "Meinsortierer"\ndef starte():\n    pass\n', encoding="utf-8")

    monkeypatch.setattr(core.sys, "frozen", True, raising=False)
    monkeypatch.setattr(core.sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(core.sys, "executable",
                        str(tmp_path / "Scrinium.exe"), raising=False)

    gefunden = core.tools_dir()
    assert os.path.normcase(gefunden) == os.path.normcase(str(meipass / "tools")), (
        f"tools_dir() sucht nicht in _MEIPASS: {gefunden}")

    namen = [w.name.lower() for w in core.find_tools()]
    assert any("meinsortierer" in n for n in namen), namen


def test_tools_dir_prefers_meipass_over_the_exe_folder(tmp_path, monkeypatch):
    """Beide Ordner da: der gebundelte gewinnt."""
    from scrinium import core

    meipass = tmp_path / "mei"
    (meipass / "tools" / "gebunden").mkdir(parents=True)
    neben_exe = tmp_path / "neben"
    (neben_exe / "tools" / "dazugelegt").mkdir(parents=True)

    monkeypatch.setattr(core.sys, "frozen", True, raising=False)
    monkeypatch.setattr(core.sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(core.sys, "executable",
                        str(neben_exe / "Scrinium.exe"), raising=False)

    assert os.path.normcase(core.tools_dir()) == \
        os.path.normcase(str(meipass / "tools"))


def test_tools_dir_finds_the_bundled_sorter():
    """Im Quellcode muss das mitgelieferte Werkzeug gefunden werden."""
    from scrinium import core

    gefunden = core.find_tools()
    namen = [w.name.lower() for w in gefunden]
    assert gefunden, f"keine Werkzeuge in {core.tools_dir()}"
    assert any("sort" in n or "download" in n for n in namen), namen


def test_tools_dir_does_not_create_folders_in_meipass():
    """_MEIPASS ist ein Temp-Ordner - dort darf nichts angelegt werden."""
    quelle = lies("scrinium", "core.py")
    block = quelle[quelle.find("def tools_dir"):]
    block = block[:block.find("\ndef ")]
    # makedirs darf nur im letzten Zweig stehen, nach der Suche
    i_mkdir = block.find("makedirs")
    i_such = block.find("for pfad in kandidaten")
    assert i_such > 0 and i_mkdir > i_such, (
        "makedirs laeuft vor der Suche - das legt Ordner in _MEIPASS an")
