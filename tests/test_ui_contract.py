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

    # Die datas=-Zeile muss die Werkzeuge wirklich enthalten - sonst
    # werden sie gesammelt und dann weggeworfen.
    datas_zeilen = [z.strip() for z in spec.splitlines()
                    if z.strip().startswith("datas=")]
    assert datas_zeilen, "keine datas=-Zeile in der Spec"
    assert any("tools_datas" in z for z in datas_zeilen), (
        f"tools_datas fehlt in der datas=-Zeile: {datas_zeilen}")
    assert any("html_datas" in z for z in datas_zeilen), datas_zeilen

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


# --------------------------------------------------------------------------
# 4. Der Einstellungen-Knopf
# --------------------------------------------------------------------------
def test_texts_sag_takes_only_one_argument():
    """sag(key, **platzhalter) - nur EIN positionales Argument.

    ``texts.sag("einstellungen.titel", "Einstellungen")`` wirft
    TypeError. In open_settings stand das im try-Block, der Fehler wurde
    verschluckt, und der Knopf "Einstellungen" tat nichts.
    """
    import inspect

    from scrinium import texts

    parameter = inspect.signature(texts.sag).parameters
    positional = [p for p in parameter.values()
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    assert len(positional) == 1, (
        f"sag() hat jetzt {len(positional)} positionale Parameter - "
        f"die Aufrufe im Projekt pruefen")


def test_no_sag_call_uses_two_positional_arguments():
    """Kein Aufruf im Projekt darf zwei positionale Argumente geben."""
    treffer = []
    for dp, dn, fn in os.walk(SCRINIUM):
        dn[:] = [d for d in dn if d != "__pycache__"]
        for f in fn:
            if not f.endswith(".py") or f == "texts.py":
                continue
            p = os.path.join(dp, f)
            for i, z in enumerate(open(p, encoding="utf-8"), 1):
                for m in re.finditer(r"\bsag\((.*?)\)", z):
                    teile = [t for t in m.group(1).split(",") if t.strip()]
                    if len(teile) > 1 and "=" not in teile[1]:
                        treffer.append(f"{os.path.basename(p)}:{i}  {z.strip()[:60]}")
    assert not treffer, (
        "sag() wird mit zwei positionalen Argumenten gerufen - das wirft "
        f"TypeError:\n  " + "\n  ".join(treffer))


def test_open_settings_opens_a_window(monkeypatch):
    """Der Knopf muss wirklich ein Fenster erzeugen.

    Ohne echtes Fenster: ``create_window`` wird ersetzt und muss mit dem
    richtigen Titel und der settings.html gerufen werden. Vorher kam
    hier '' heraus, ohne dass etwas passierte.
    """
    import sys as _sys
    import types

    from scrinium import bridge

    gerufen = {}

    def create_window(titel, *args, **kwargs):
        gerufen["titel"] = titel
        gerufen["args"] = args
        return types.SimpleNamespace()

    fake = types.ModuleType("webview")
    fake.create_window = create_window
    fake.start = lambda *a, **k: None
    fake.FileDialog = type("FileDialog", (), {"FOLDER": 20, "OPEN": 10})
    monkeypatch.setitem(_sys.modules, "webview", fake)
    monkeypatch.setattr(bridge, "_window", lambda: object())
    monkeypatch.setattr(bridge, "_settings_html", lambda: os.path.join(
        SCRINIUM, "settings.html"))

    ergebnis = bridge.open_settings()
    assert ergebnis == "offen", (
        f"open_settings() gab {ergebnis!r} zurueck - der Knopf bleibt stumm")
    assert gerufen.get("titel") == "Einstellungen", (
        f"falscher Fenstertitel: {gerufen.get('titel')!r}")


def test_open_settings_says_so_when_the_file_is_missing(monkeypatch, capsys):
    """Fehlt settings.html, muss das im Protokoll stehen - nicht stumm."""
    import sys as _sys
    import types

    from scrinium import bridge

    fake = types.ModuleType("webview")
    fake.create_window = lambda *a, **k: None
    monkeypatch.setitem(_sys.modules, "webview", fake)
    monkeypatch.setattr(bridge, "_window", lambda: object())
    monkeypatch.setattr(bridge, "_settings_html", lambda: "")

    assert bridge.open_settings() == ""
    assert "settings.html" in capsys.readouterr().out


# --------------------------------------------------------------------------
# 5. Der Start-Wettlauf mit pywebview
# --------------------------------------------------------------------------
def test_bereit_waits_for_a_method_not_just_the_object():
    """Regression: "API.state is not a function" in der gepackten EXE.

    pywebview setzt `window.pywebview.api` in ZWEI Schritten: erst ein
    leeres Objekt, dann - in einem eigenen Thread - die Methoden. Wer
    nur auf das Objekt wartet, erwischt den leeren Zwischenstand.

    Aus der Quelle gewann man den Wettlauf zufaellig, in der EXE nie.
    Deshalb muss auf eine bekannte Methode geprueft werden.
    """
    js = js_teil("window.html")
    i = js.find("function bereit()")
    assert i > 0, "bereit() nicht gefunden"
    block = js[i:i + 900]

    assert "typeof window.pywebview.api.state === 'function'" in block, (
        "bereit() prueft nicht, ob eine Methode schon da ist - dann kann "
        "es den leeren Zwischenstand erwischen")
    assert "function fertig()" in block, "die Pruefung fehlt"


def test_no_pseudo_element_uses_the_icon_font():
    """Ein Icon-Zeichen in ::after wird als TEXT sichtbar.

    `content: 'expand_more'` mit der Icon-Schrift zeigte im Fenster das
    Wort "more" ueber "Deutsch" - die Schrift greift in einem
    Pseudo-Element nicht.
    """
    html = lies("scrinium", "window.html")
    css = html[html.find("<style>"):html.find("</style>")]
    for m in re.finditer(r"::(?:after|before)\s*\{([^}]*)\}", css):
        rumpf = m.group(1)
        assert "Material Symbols" not in rumpf, (
            "Icon-Schrift in einem Pseudo-Element - das wird als Text "
            f"sichtbar: {rumpf.strip()[:80]}")


def test_language_field_has_a_visible_arrow():
    """Das Auswahlfeld muss einen Pfeil haben, sonst sieht es wie Text aus."""
    html = lies("scrinium", "window.html")
    css = html[html.find("<style>"):html.find("</style>")]
    assert ".wahl-wrap::after" in css
    block = css[css.find(".wahl-wrap::after"):]
    block = block[:block.find("}")]
    assert "border-top" in block, (
        "der Pfeil ist kein Dreieck - dann braucht er eine Schrift")


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
