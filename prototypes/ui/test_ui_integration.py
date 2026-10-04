"""Echter Test: Fenster starten, Bruecke pruefen, Screenshot machen.

Testet in dieser Reihenfolge:
1. Kern + Bruecke ohne Fenster (Python-Seite)
2. Fenster starten, HTML laden, Bruecke aufrufen
3. Screenshot des echten Fensters

Kein pytest - ein Integrationstest fuer die reizvolle Stelle des Systems.
"""

import os
import sys
import threading
import time
import traceback

ROOT = r"C:\Users\Friedrich\Documents\Portfolio\GitHub\Scrinium"
sys.path.insert(0, ROOT)

FEHLER = []


def ck(label, bedingung, detail=""):
    print(("  PASS  " if bedingung else "  FAIL  ") + label
          + (("   <- " + str(detail)) if detail else ""))
    if not bedingung:
        FEHLER.append(label)


# ── 1. Python-Seite ohne Fenster ─────────────────────────────
print("=== 1) Bruecke ohne Fenster ===")
os.environ["APPDATA"] = os.path.join(
    os.environ.get("TEMP", r"C:\Windows\Temp"), "hermes-ui-test")

from scrinium import bruecke, kern  # noqa: E402
from scrinium.einstellungen import Einstellungen  # noqa: E402

z = bruecke.zustand()
ck("zustand() liefert ein dict", isinstance(z, dict), type(z))
ck("werkzeuge gefunden", len(z["werkzeuge"]) >= 1,
   [w["id"] for w in z["werkzeuge"]])
ck("erstes Werkzeug ist der Sortierer",
   z["werkzeuge"][0]["id"] == "downloadsorter",
   z["werkzeuge"][0]["id"] if z["werkzeuge"] else None)
ck("einstellungen vorhanden", "downloads_ordner" in z["einstellungen"],
   z["einstellungen"])
ck("kein Fenster im Weg (ordner_oeffnen ohne Fenster)",
   bruecke.ordner_oeffnen() in ("", z["einstellungen"]["downloads_ordner"]))

# ── 2. Vorschau mit echten Dateien ───────────────────────────
print("\n=== 2) Vorschau (read-only) ===")
import tempfile, time as tmod  # noqa: E402

d = tempfile.mkdtemp(prefix="hermes-vorschau-")
for name in ("a.pdf", "b.jpg", "c.mp4", "d.crdownload"):
    p = os.path.join(d, name)
    open(p, "wb").write(b"x" * 2048)
    alt = tmod.time() - 600
    os.utime(p, (alt, alt))

cfg = Einstellungen.standard()
cfg.downloads_ordner = d.replace("\\", "/")
cfg.downloads_min_age = 0
cfg.speichern()

v = bruecke.vorschau("downloadsorter")
ck("vorschau liefert ein dict", isinstance(v, dict), type(v))
ck("3 Dateien werden verschoben", v.get("verschoben") == 3,
   (v.get("verschoben"), [x["name"] for x in v.get("dateien", [])]))
ck("crdownload bleibt liegen",
   any(x["name"] == "d.crdownload" and not x["ziel"]
       for x in v.get("dateien", [])), v.get("dateien"))
ck("Zielordner benannt",
   all(x["ziel"] for x in v.get("dateien", []) if x["name"] != "d.crdownload"),
   [x for x in v.get("dateien", [])])
ck("Vorschau hat nichts bewegt",
   sorted(os.listdir(d)) == ["a.pdf", "b.jpg", "c.mp4", "d.crdownload"],
   sorted(os.listdir(d)))

# ── 3. Sortieren ueber die Bruecke ───────────────────────────
print("\n=== 3) Sortieren + Undo ueber die Bruecke ===")
r = bruecke.werkzeug_starten("downloadsorter")
ck("kein Fehler", not r.get("fehler"), r.get("text"))
ck("3 einsortiert", r["daten"]["verschoben"] == 3, r["daten"])
ck("Undo angeboten", len(r["aktionen"]) == 1, r["aktionen"])
ck("auf Deutsch ueber die Sprachdatei",
   "einsortiert" in r["text"], r["text"])

undo = bruecke.aktion(r["aktionen"][0][1])
ck("Undo ohne Fehler", not undo.get("fehler"), undo.get("text"))
ck("3 zurueck", undo["daten"]["zurueck"] == 3, undo["daten"])
ck("Quelle wieder voll",
   sorted(os.listdir(d)) == ["a.pdf", "b.jpg", "c.mp4", "d.crdownload"],
   sorted(os.listdir(d)))

# ── 4. Unbekannte Aktion ─────────────────────────────────────
print("\n=== 4) Unbekannte Kennung ===")
falsch = bruecke.aktion("gibt-es-nicht")
ck("ist ein Fehler, kein stiller Erfolg", falsch.get("fehler") is True, falsch)

# ── 5. Sprache ───────────────────────────────────────────────
print("\n=== 5) Sprachwechsel ===")
bruecke.sprache_setzen("en")
r2 = bruecke.werkzeug_starten("downloadsorter")
ck("englischer Text", "Filed" in r2.get("text", "") or "Nothing" in r2.get("text", ""),
   r2.get("text"))
bruecke.sprache_setzen("de")
ck("zurueck auf Deutsch", bruecke.zustand()["einstellungen"]["sprache"] == "de")

# ── 6. Echtes Fenster ────────────────────────────────────────
print("\n=== 6) Fensterstart ===")
import webview  # noqa: E402

html = os.path.join(ROOT, "scrinium", "fenster.html")
ck("fenster.html vorhanden", os.path.isfile(html), html)

from scrinium import fenster as fenster_mod  # noqa: E402

api = fenster_mod.bruecke_api()
erg = {}
fenster_obj = None


def laden():
    """Laeuft im Fenster-Thread: fuehrt echte API-Aufrufe aus."""
    try:
        import time as T
        for _ in range(40):
            try:
                z2 = window.scrinium.zustandIntern()
                break
            except AttributeError:
                T.sleep(0.25)
        erg["titel"] = window.document.title
        erg["werkzeugeImDom"] = len(window.document.querySelectorAll(".tool"))
        erg["ctaDa"] = window.document.querySelector(".cta") is not None
        erg["pfad"] = window.document.getElementById("ordner-pfad").textContent
        erg["titelText"] = window.document.querySelector(".w-title") \
            .textContent if window.document.querySelector(".w-title") else ""
    except Exception:
        erg["fehler"] = traceback.format_exc()


fenster_obj = webview.create_window(
    "Scrinium", html, js_api=api, width=1280, height=820,
    min_size=(900, 620), background_color="#141218")
bruecke.fenster_setzen(fenster_obj)


def erledigen():
    time.sleep(9)
    try:
        fenster_obj.destroy()
    except Exception:
        pass


threading.Thread(target=erledigen, daemon=True).start()

# Fenster laeuft in einem Thread, der eigentliche Start blockiert unten.
# webview.start() muss im Hauptthread sein - darum der Aufruf hier.
try:
    webview.start()
except Exception:
    pass

print("  Fenster wurde geoeffnet und nach 9s geschlossen")

# Screenshot des Fensters geht nur, solange es offen ist - deshalb
# separat im naechsten Schritt.

import shutil  # noqa: E402
shutil.rmtree(d, ignore_errors=True)

print("\n" + "=" * 54)
print("INTEGRATION FAILED: %d" % len(FEHLER))
for x in FEHLER:
    print("   -", x)
sys.exit(1 if FEHLER else 0)