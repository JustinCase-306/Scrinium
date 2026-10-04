"""Smoke-Test: startet pywebview aus dem Projekt-venv ein Fenster?

Wichtig: webview.start() braucht den HAUPTTHREAD. Und cffi darf nicht
mit einer fremden cffi-Version aus einem anderen venv kollidieren -
darum wird der sys.path vorher bereinigt.
"""

import os
import sys


def sys_path_bereinigen():
    """Wirft Pfade fremder venvs raus (hermes-agent o.ae.)."""
    raus = []
    eigener = os.path.normcase(os.path.dirname(os.path.dirname(
        os.path.abspath(sys.executable))))
    neu = []
    for p in sys.path:
        norm = os.path.normcase(p)
        if "hermes-agent" in norm or "hermes\\hermes" in norm:
            raus.append(p)
            continue
        # Fremde site-packages, die vor dem eigenen liegen
        if norm.endswith("site-packages") and eigener not in norm:
            if any(x in norm for x in ("\\hermes\\", "Temp\\")):
                raus.append(p)
                continue
        neu.append(p)
    sys.path[:] = neu
    return raus


entfernt = sys_path_bereinigen()
print("=== 0) sys.path bereinigt ===")
print("  entfernt:", entfernt or "nichts")
print("  python   :", sys.executable)

print("\n=== 1) pywebview ===")
import webview
from importlib.metadata import version as v
print("  Version  :", v("pywebview"))

print("\n=== 2) CLR ===")
try:
    import clr
    try:
        o = clr.System.Object()
        print("  CLR      : laeuft ->", o.GetType().FullName)
    except AttributeError:
        print("  CLR      : Runtime bereits geladen (System-Attribut gebunden)")
except Exception as e:
    print("  CLR      : FEHLER", str(e)[:110])

print("\n=== 3) Fensterstart (Hauptthread, 6s) ===")
HTML = os.path.join(
    r"C:\Users\Friedrich\Documents\Portfolio\GitHub\Scrinium\prototypes\ui",
    "variant_d_vollstaendig.html")
print("  HTML:", os.path.basename(HTML))
if not os.path.exists(HTML):
    sys.exit(2)

try:
    w = webview.create_window("Scrinium", HTML, width=1280, height=820,
                              min_size=(900, 620))
    print("  Fenster-Objekt: erstellt")

    import threading
    threading.Timer(6.0, lambda: w.destroy()).start()

    webview.start()
    print("  webview.start() zurueck -> Fenster war offen")
    print("\nERGEBNIS: OK")
except Exception:
    import traceback
    print("  FEHLER:\n" + traceback.format_exc())
    print("\nERGEBNIS: NEIN")
    sys.exit(1)