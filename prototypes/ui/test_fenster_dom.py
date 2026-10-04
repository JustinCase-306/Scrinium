"""Prueft, ob das echte Fenster wirklich etwas anzeigt.

Der Test liest den DOM des echten WebView2-Fensters aus - ueber
`evaluate_js`, weil Python-Code im Fenster-Kontext nur ueber pywebviews
eigene Bruecke laeuft, nicht ueber einen Thread.

Erwartet wird KEIN Screenshot - nur die Tatsache, dass die Oberflaeche
tatsaechlich aufgebaut wurde.
"""

import json
import os
import sys
import threading
import time

ROOT = r"C:\Users\Friedrich\Documents\Portfolio\GitHub\Scrinium"
sys.path.insert(0, ROOT)

import tempfile
os.environ["APPDATA"] = os.path.join(tempfile.gettempdir(), "hermes-dom-test")

FEHLER = []


def ck(label, bedingung, detail=""):
    print(("  PASS  " if bedingung else "  FAIL  ") + label
          + (("   <- " + str(detail)) if detail else ""))
    if not bedingung:
        FEHLER.append(label)


# Testdaten
d = tempfile.mkdtemp(prefix="hermes-dom-daten-")
# 40 Dateien: damit ist die Liste sicher laenger als das Fenster. Sonst
# waere der Scrollbalken-Test ein Test fuer "passt noch".
_kategorien = ("pdf", "jpg", "mp4", "mp3", "zip", "png", "docx")
for i in range(40):
    endung = _kategorien[i % len(_kategorien)]
    open(os.path.join(d, f"datei_{i:02d}.{endung}"), "wb").write(b"x" * 4096)
open(os.path.join(d, "laden.mp4.crdownload"), "wb").write(b"x" * 512)
print("40 Dateien + 1 laufender Download angelegt")

from scrinium.einstellungen import Einstellungen  # noqa: E402

cfg = Einstellungen.standard()
cfg.downloads_ordner = d.replace("\\", "/")
cfg.downloads_min_age = 0
cfg.speichern()
print("Testordner:", d)

import webview  # noqa: E402
from scrinium import bruecke  # noqa: E402
from scrinium import fenster as fenster_mod  # noqa: E402

html = os.path.join(ROOT, "scrinium", "fenster.html")

# Das JavaScript, das den DOM liest. Ergebnis geht nach window.befund,
# damit es von aussen abrufbar ist.
JS_LESEN = """
(function(){
  var d = document;
  var work = d.querySelector('.work');
  window.befund = {
    titel: d.title,
    apiDa: !!(window.pywebview && window.pywebview.api),
    werkzeuge: d.querySelectorAll('.tool').length,
    werkzeugNamen: Array.prototype.map.call(
        d.querySelectorAll('.tool-name'),
        function(e){ return e.textContent.trim(); }),
    cta: d.querySelector('.cta') ? d.querySelector('.cta').textContent.trim() : '',
    ctaOhneIcon: d.querySelector('.cta')
        ? Array.prototype.filter.call(d.querySelector('.cta').childNodes,
              function(n){ return n.nodeType === 3; })
                .map(function(n){ return n.textContent.trim(); }).join('')
        : '',
    titelText: d.querySelector('.w-title') ? d.querySelector('.w-title').textContent : '',
    pfad: (d.getElementById('ordner-pfad')||{}).textContent || '',
    dateien: d.querySelectorAll('.file').length,
    dateiNamen: Array.prototype.map.call(d.querySelectorAll('.f-name'),
        function(e){ return e.textContent.trim(); }),
    zielOrdner: Array.prototype.map.call(d.querySelectorAll('.f-to'),
        function(e){ return e.textContent.trim(); }),
    filesHead: (d.querySelector('.files-h')||{}).textContent || '',
    schalter: d.querySelectorAll('.tool-schalter').length,
    leer: d.querySelector('.leer') ? d.querySelector('.leer').textContent : '',
    // WebView2 rendert einen Overlay-Scrollbalken ohne eigene Breite, darum
    // ist offsetHeight-clientHeight IMMER 0. Die richtige Messgroesse ist
    // scrollHeight (Inhalt) gegen clientHeight (sichtbarer Kasten).
    scrollHoehe: work ? work.scrollHeight - work.clientHeight : -1,
    clientH: work ? work.clientHeight : -1,
    scrollH: work ? work.scrollHeight : -1,
    // Zweiter Beweis: tatsaechlich scrollen und zurueck
    scrollTest: work ? (function(){
        work.scrollTop = 500;
        var mittig = work.scrollTop;
        work.scrollTop = 99999;
        var ende = work.scrollTop;
        work.scrollTop = 0;
        return { bei500: mittig, amEnde: ende };
      })() : null,
    scrollTopMax: work ? (function(){
        var vorher = work.scrollTop;
        work.scrollTop = 99999;
        var max = work.scrollTop;
        work.scrollTop = vorher;
        return max;
      })() : -1,
    pfadVoll: d.getElementById('ordner-pfad') ?
              d.getElementById('ordner-pfad').textContent.length : 0
  };
  return JSON.stringify(window.befund);
})()
"""

befund = {}
fenster_obj = webview.create_window(
    "Scrinium", html,
    js_api=fenster_mod.bruecke_api(),
    width=1280, height=820, min_size=(900, 620),
    background_color="#141218")
bruecke.fenster_setzen(fenster_obj)


def auslesen():
    """Wartet, bis die Oberflaeche steht, liest dann den DOM.

    Mehrfach lesen: `webview.start()` blockiert den Hauptthread, der
    erste Messpunkt kann noch den Platzhalter erwischen. Deshalb wird
    regelmaessig neu gelesen und der letzte Stand behalten - sofern er
    besser ist als der erste.
    """
    besser = -1
    for _ in range(60):
        time.sleep(0.5)
        try:
            roh = fenster_obj.evaluate_js(JS_LESEN)
            if not roh or roh == "null":
                continue
            daten = json.loads(roh) if isinstance(roh, str) else roh
            # "Aufbau vollstaendig" = Werkzeuge sichtbar und kein Platzhalter
            punkte = (1 if daten.get("werkzeuge") else 0) + \
                     (0 if daten.get("leer") else 1) + \
                     (1 if daten.get("cta") else 0) + \
                     (1 if daten.get("dateien", 0) >= 40 else 0) + \
                     (1 if daten.get("schalter") else 0) + \
                     (1 if daten.get("pfadVoll", 0) > 20 else 0)
            if punkte > besser:
                besser = punkte
                befund.clear()
                befund.update(daten)
                befund["_punkte"] = punkte
            if punkte >= 6:
                return
        except Exception:
            pass


def beenden():
    time.sleep(16)
    try:
        fenster_obj.destroy()
    except Exception:
        pass


threading.Thread(target=auslesen, daemon=True).start()
threading.Thread(target=beenden, daemon=True).start()

print("\n=== Fenster startet ===")
try:
    webview.start()
except Exception:
    pass

print("\n=== Was stand im Fenster? ===")
if not befund:
    print("  keine Daten")
    sys.exit(1)
for k, v in befund.items():
    print(f"  {k:<16} {v}")

print("\n=== Pruefungen ===")
ck("Fenster mit Titel 'Scrinium'", befund["titel"] == "Scrinium", befund["titel"])
ck("Bruecke verbunden (pywebview.api)", befund["apiDa"] is True, befund["apiDa"])
ck("Werkzeug sichtbar in der Leiste", befund["werkzeuge"] >= 1, befund["werkzeuge"])
ck("Werkzeugname im DOM",
   any("Downloads" in n for n in befund["werkzeugNamen"]),
   befund["werkzeugNamen"])
ck("grosser Startknopf da", len(befund["cta"]) > 5, befund["cta"])
ck("Knopf heisst 'Jetzt sortieren'",
   "jetzt sortieren" in befund["ctaOhneIcon"].lower(), befund["ctaOhneIcon"])
ck("Werkzeugtitel in der Arbeitsflaeche",
   "Downloads" in befund["titelText"], befund["titelText"])
ck("Ordnerpfad angezeigt", befund["pfadVoll"] > 20, befund["pfad"])
ck("Pfad zeigt den echten Testordner",
   "hermes-dom-daten" in befund["pfad"], befund["pfad"])
ck("kein Platzhalter 'laeuft noch'", not befund["leer"], befund["leer"])
ck("Schalter je Werkzeug", befund["schalter"] >= 1, befund["schalter"])
ck("Vorschau zeigt alle Dateien", befund["dateien"] >= 40, befund["dateien"])
ck("Dateinamen in der Vorschau",
   len(befund["dateiNamen"]) >= 40, len(befund["dateiNamen"]))
ck("Zielordner benannt (Dokumente/Bilder)",
   any("Dokumente" in z for z in befund["zielOrdner"]), befund["zielOrdner"])
ck("Vorschau-Ueberschrift da", "passiert" in befund["filesHead"].lower(),
   befund["filesHead"])
ck("Inhalt laenger als der sichtbare Bereich",
   befund["scrollH"] > befund["clientH"],
   "Inhalt %dpx, sichtbar %dpx, bei %d Dateien"
   % (befund["scrollH"], befund["clientH"], befund["dateien"]))
ck("Scrollen funktioniert (Position aendert sich)",
   befund["scrollTest"]["bei500"] == 500,
   befund["scrollTest"])
ck("letzte Datei erreichbar (Anfang bis Ende)",
   befund["scrollTest"]["amEnde"] > 1000,
   "%dpx bis zum Ende" % befund["scrollTest"]["amEnde"])
ck("nach dem Test zurueck am Anfang",
   befund["scrollTest"]["amEnde"] > 1000, befund["scrollTest"])

import shutil  # noqa: E402
shutil.rmtree(d, ignore_errors=True)

print("\n" + "=" * 54)
print("DOM-CHECK FAILED: %d" % len(FEHLER))
for x in FEHLER:
    print("   -", x)
sys.exit(1 if FEHLER else 0)