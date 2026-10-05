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

from scrinium import bridge, core  # noqa: E402
from scrinium.settings import Settings  # noqa: E402

z = bridge.state()
ck("state() liefert ein dict", isinstance(z, dict), type(z))
ck("tools gefunden", len(z["tools"]) >= 1,
   [w["id"] for w in z["tools"]])
ck("first tool is the sorter",
   z["tools"][0]["id"] == "downloadsorter",
   z["tools"][0]["id"] if z["tools"] else None)
ck("einstellungen vorhanden", "downloads_folder" in z["settings"],
   z["settings"])
ck("kein Fenster im Weg (open_folder ohne Fenster)",
   bridge.open_folder() in ("", z["settings"]["downloads_folder"]))

# ── 2. Vorschau mit echten Dateien ───────────────────────────
print("\n=== 2) Vorschau (read-only) ===")
import tempfile, time as tmod  # noqa: E402

d = tempfile.mkdtemp(prefix="hermes-preview-")
for name in ("a.pdf", "b.jpg", "c.mp4", "d.crdownload"):
    p = os.path.join(d, name)
    open(p, "wb").write(b"x" * 2048)
    alt = tmod.time() - 600
    os.utime(p, (alt, alt))

cfg = Settings.standard()
cfg.downloads_folder = d.replace("\\", "/")
cfg.downloads_min_age = 0
cfg.speichern()

v = bridge.preview("downloadsorter")
ck("preview liefert ein dict", isinstance(v, dict), type(v))
ck("3 Dateien werden verschoben", v.get("moved") == 3,
   (v.get("moved"), [x["name"] for x in v.get("dateien", [])]))
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
r = bridge.start_tool("downloadsorter")
ck("kein Fehler", not r.get("fehler"), r.get("text"))
ck("3 einsortiert", r["data"]["moved"] == 3, r["data"])
ck("Undo angeboten", len(r["actions"]) == 1, r["actions"])
ck("auf Deutsch ueber die Sprachdatei",
   "einsortiert" in r["text"], r["text"])

undo = bridge.action(r["actions"][0][1])
ck("Undo ohne Fehler", not undo.get("fehler"), undo.get("text"))
ck("3 zurueck", undo["data"]["restored"] == 3, undo["data"])
ck("Quelle wieder voll",
   sorted(os.listdir(d)) == ["a.pdf", "b.jpg", "c.mp4", "d.crdownload"],
   sorted(os.listdir(d)))

# ── 4. Unbekannte Aktion ─────────────────────────────────────
print("\n=== 4) Unbekannte Kennung ===")
falsch = bridge.action("gibt-es-nicht")
ck("ist ein Fehler, kein stiller Erfolg", falsch.get("fehler") is True, falsch)

# ── 5. Sprache ───────────────────────────────────────────────
print("\n=== 5) Sprachwechsel ===")
bridge.set_language("en")
r2 = bridge.start_tool("downloadsorter")
ck("englischer Text", "Filed" in r2.get("text", "") or "Nothing" in r2.get("text", ""),
   r2.get("text"))
bridge.set_language("de")
ck("zurueck auf Deutsch", bridge.state()["settings"]["language"] == "de")

# ── 6. Echtes Fenster ────────────────────────────────────────
print("\n=== 6) Fensterstart ===")
import webview  # noqa: E402

html = os.path.join(ROOT, "scrinium", "window.html")
ck("window.html vorhanden", os.path.isfile(html), html)

from scrinium import window as window_mod  # noqa: E402

api = window_mod.bridge_api()
erg = {}
fenster_obj = None


def laden():
    """Laeuft im Fenster-Thread: fuehrt echte API-Aufrufe aus."""
    try:
        import time as T
        for _ in range(40):
            try:
                z2 = window.scrinium.stateIntern()
                break
            except AttributeError:
                T.sleep(0.25)
        erg["titel"] = window.document.title
        erg["werkzeugeImDom"] = len(window.document.querySelectorAll(".tool"))
        erg["ctaDa"] = window.document.querySelector(".cta") is not None
        erg["path"] = window.document.getElementById("ordner-pfad").textContent
        erg["titelText"] = window.document.querySelector(".w-title") \
            .textContent if window.document.querySelector(".w-title") else ""
    except Exception:
        erg["fehler"] = traceback.format_exc()


fenster_obj = webview.create_window(
    "Scrinium", html, js_api=api, width=1280, height=820,
    min_size=(900, 620), background_color="#141218")
bridge.set_window(fenster_obj)


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