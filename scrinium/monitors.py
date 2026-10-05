"""Testfenster auf den zweiten Monitor schieben.

Der Nutzer arbeitet auf Monitor 1. Wenn ein Test ein Fenster braucht,
soll das auf Monitor 2 aufgehen - nicht auf dem, vor dem er sitzt.

Deshalb ist die Regel im Gedaechtnis ("keine Fenster aufpoppen lassen")
so umsetzbar, ohne dass man sie umgehen muss.

Wichtig: MonitorFromPoint + GetMonitorInfo, NICHT EnumDisplayMonitors.
EnumDisplayMonitors mit selbstgebauten ctypes-Strukturen hat hier
dreimal Muell geliefert (-217182272 als Koordinate) - die Struktur
schneidet Windows ab. GetMonitorInfoW mit gesetztem cbSize
funktioniert und braucht keinen Callback.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes


class _MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


def _metrics(index: int) -> int:
    user32 = ctypes.windll.user32
    user32.GetSystemMetrics.restype = ctypes.c_int
    return user32.GetSystemMetrics(index)


SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CMONITORS = 80

MONITOR_DEFAULTTONEAREST = 2
MONITORINFOF_PRIMARY = 1


def monitor_anzahl() -> int:
    try:
        return int(_metrics(SM_CMONITORS))
    except Exception:
        return 1


def alle_monitore() -> list[dict]:
    """Jeden Monitor mit Arbeitsflaeche. Leer, wenn etwas nicht klappt."""
    if not hasattr(ctypes, "windll"):
        return []
    user32 = ctypes.windll.user32
    try:
        user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
        user32.MonitorFromPoint.restype = wintypes.HMONITOR
        user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.c_void_p]
        user32.GetMonitorInfoW.restype = wintypes.BOOL
    except Exception:
        return []

    try:
        vx, vy = _metrics(SM_XVIRTUALSCREEN), _metrics(SM_YVIRTUALSCREEN)
        vb, vh = _metrics(SM_CXVIRTUALSCREEN), _metrics(SM_CYVIRTUALSCREEN)
    except Exception:
        return []
    if vb <= 0 or vh <= 0:
        return []

    # Den virtuellen Bildschirm abtasten. Alle 40 Pixel reichen, um
    # jeden Monitor zu treffen - auch einen schmalen Streifen.
    gefunden: dict[int, dict] = {}
    schritt = 40
    y = vy
    while y < vy + vh:
        x = vx
        while x < vx + vb:
            try:
                hmon = user32.MonitorFromPoint(
                    wintypes.POINT(x, y), MONITOR_DEFAULTTONEAREST)
            except Exception:
                x += schritt
                continue
            if hmon:
                schluessel = int(hmon)
                if schluessel not in gefunden:
                    info = _MonitorInfo()
                    info.cbSize = ctypes.sizeof(_MonitorInfo)
                    if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
                        gefunden[schluessel] = {
                            "work": (info.rcWork.left, info.rcWork.top,
                                     info.rcWork.right, info.rcWork.bottom),
                            "monitor": (info.rcMonitor.left,
                                        info.rcMonitor.top,
                                        info.rcMonitor.right,
                                        info.rcMonitor.bottom),
                            "primary": bool(info.dwFlags & MONITORINFOF_PRIMARY),
                        }
            x += schritt
        y += schritt

    return list(gefunden.values())


def zweiter_monitor_platz() -> tuple[int, int]:
    """Wo ein Testfenster hingeht. (0, 0) heisst: kein zweiter Monitor.

    Dann darf der Aufrufer KEIN Fenster sichtbar machen - er muss
    minimiert starten oder ganz auf ein Fenster verzichten.
    """
    bildschirme = alle_monitore()
    sekundaer = [m for m in bildschirme if not m["primary"]]
    if not sekundaer:
        return (0, 0)

    bester = max(sekundaer,
                 key=lambda m: (m["work"][2] - m["work"][0])
                               * (m["work"][3] - m["work"][1]))
    x, y, r, u = bester["work"]
    return (x + 60, y + 60)


def passt_auf_zweiten(b_breite: int, b_hoehe: int) -> bool:
    """Passt ein Fenster dieser Groesse auf Monitor 2?"""
    bildschirme = alle_monitore()
    sekundaer = [m for m in bildschirme if not m["primary"]]
    if not sekundaer:
        return False
    bester = max(sekundaer,
                 key=lambda m: (m["work"][2] - m["work"][0])
                               * (m["work"][3] - m["work"][1]))
    x, y, r, u = bester["work"]
    return (x + 60 + b_breite <= r) and (y + 60 + b_hoehe <= u)


def start_auf_zweiten_monitor(b_breite: int, b_hoehe: int) -> tuple[int, int]:
    """STARTUPINFO fuer einen Prozess, der auf Monitor 2 erscheint.

    Gibt (x, y) zurueck fuer subprocess. Ohne zweiten Monitor (0, 0)
    und der Aufrufer muss selbst minimieren.
    """
    platz = zweiter_monitor_platz()
    if platz == (0, 0):
        return (0, 0)
    x, y = platz
    # Fenstergroesse noch einmal pruefen - ein Monitor, der zu klein
    # ist, ist schlimmer als gar keiner.
    if not passt_auf_zweiten(b_breite, b_hoehe):
        return (0, 0)
    return (x, y)


if __name__ == "__main__":          # manuell pruefen: python monitors.py
    bildschirme = alle_monitore()
    print(f"{len(bildschirme)} Monitor(e)")
    for i, m in enumerate(bildschirme, 1):
        x, y, r, u = m["work"]
        print(f"  {i} {'PRIMÄR' if m['primary'] else 'sekundär'}: "
              f"({x}, {y}) bis ({r}, {u}) = {r - x} x {u - y}")
    print(f"Testfenster 1280x820 -> {start_auf_zweiten_monitor(1280, 820)}")
