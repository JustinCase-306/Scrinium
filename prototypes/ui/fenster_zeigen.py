"""Startet Scriniums Fenster auf Monitor 2, damit du es ansehen kannst.

Nur von Hand starten, nie aus einem Test:

    .venv/Scripts/python.exe prototypes/ui/fenster_zeigen.py

Monitor 1 ist der Bildschirm, an dem du arbeitest - dort geht nichts
auf. Ohne zweiten Monitor startet das Skript gar nicht erst, damit
sich doch nichts auf deinem Hauptmonitor oeffnet.
"""

import os
import sys

_HIER = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(_HIER))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

for _key in ("PYTHONPATH", "PYTHONHOME"):
    os.environ.pop(_key, None)

BREITE, HOEHE = 1100, 880


def main():
    from scrinium import monitors as M
    from scrinium import window as W

    bildschirme = M.alle_monitore()
    for i, m in enumerate(bildschirme, 1):
        x, y, r, u = m["work"]
        print(f"Monitor {i} {'PRIMÄR' if m['primary'] else 'sekundär'}: "
              f"({x}, {y}) bis ({r}, {u}) = {r - x} x {u - y}")

    x, y = M.start_auf_zweiten_monitor(BREITE, HOEHE)
    if (x, y) == (0, 0):
        print()
        print("Kein zweiter Monitor (oder zu klein für das Fenster).")
        print("Es wird NICHTS geöffnet - damit auf deinem Hauptmonitor")
        print("nichts aufpoppt. Auf Monitor 2 laeuft es nur mit einem")
        print("Fenster dieser Größe.")
        return 1

    print()
    print(f"Fenster: ({x}, {y}), {BREITE} x {HOEHE} — auf Monitor 2")
    print("Schliessen zum Beenden.")
    print(f"Exitcode: {W.starten(x=x, y=y, breite=BREITE, hoehe=HOEHE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())