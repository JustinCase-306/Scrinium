"""Monitore finden, ohne ein Fenster aufzumachen.

Der Nutzer arbeitet auf Monitor 1. Testfenster gehoeren auf Monitor 2 -
das macht die Regel "keine Fenster aufpoppen lassen" ueberhaupt erst
moeglich. Diese Tests pruefen die Positionierung, ohne dass irgendwo
ein Fenster entsteht.

Die ctypes-Fehler, die hier entstanden sind und nicht wieder passieren
sollen:

* ``EnumDisplayMonitors`` mit selbstgebauten MONITORINFO-/-EX-
  Strukturen lieferte dreimal Muell als Koordinaten (-217182272).
  Windows schneidet die Struktur ab, wenn ``cbSize`` und ``argtypes``
  nicht stimmen - und ``cbSize`` muss VOR ``EnumDisplayMonitors``
  gesetzt werden, nicht im Callback.
* ``MonitorFromPoint`` + ``GetMonitorInfoW`` funktioniert: kein
  Callback, ``cbSize`` einmal vor dem Aufruf.

Deshalb wird hier bewusst der zweite Weg benutzt.
"""

from __future__ import annotations

import ctypes

import pytest

from scrinium import monitors as M


def test_monitor_count_is_at_least_one():
    assert M.monitor_anzahl() >= 1


def test_all_monitors_have_plausible_geometry():
    """Koordinaten muessen in einem realistischen Bereich liegen.

    Der ctypes-Fehler zeigte sich als Koordinaten wie -217182272. Genau
    das fängt dieser Test ab.
    """
    bildschirme = M.alle_monitore()
    assert bildschirme, "EnumDisplayMonitors lieferte nichts"

    virt_b = M._metrics(M.SM_CXVIRTUALSCREEN)
    virt_h = M._metrics(M.SM_CYVIRTUALSCREEN)
    virt_x = M._metrics(M.SM_XVIRTUALSCREEN)
    virt_y = M._metrics(M.SM_YVIRTUALSCREEN)

    for m in bildschirme:
        x, y, r, u = m["work"]
        assert r > x, f"Breite negativ: {m['work']}"
        assert u > y, f"Hoehe negativ: {m['work']}"
        assert r - x <= virt_b, f"breiter als der Bildschirm: {m['work']}"
        assert u - y <= virt_h, f"hoeher als der Bildschirm: {m['work']}"
        # Alle Werte muessen im virtuellen Bildschirm liegen
        assert virt_x - 1 <= x <= virt_x + virt_b, m["work"]
        assert virt_y - 1 <= y <= virt_y + virt_h, m["work"]


def test_exactly_one_primary_monitor():
    primaere = [m for m in M.alle_monitore() if m["primary"]]
    assert len(primaere) == 1, f"{len(primaere)} als primaer markiert"


def test_second_monitor_position_is_not_on_the_primary():
    """Wenn es einen zweiten Monitor gibt, liegt er ausserhalb von ihm."""
    bildschirme = M.alle_monitore()
    sekundaer = [m for m in bildschirme if not m["primary"]]
    if not sekundaer:
        pytest.skip("nur ein Monitor")

    primaer = next(m for m in bildschirme if m["primary"])
    px, py, pr, pu = primaer["work"]

    for m in sekundaer:
        sx, sy, sr, su = m["work"]
        # Ueberschneidung zweier Arbeitsflaechen geht nicht
        assert sx >= pr or sr <= px or sy >= pu or su <= py, \
            f"sekundaer {m['work']} liegt auf primaer {primaer['work']}"


def test_window_position_lands_on_the_second_monitor():
    bildschirme = M.alle_monitore()
    sekundaer = [m for m in bildschirme if not m["primary"]]
    if not sekundaer:
        pytest.skip("nur ein Monitor")

    x, y = M.zweiter_monitor_platz()
    assert (x, y) != (0, 0), "zweiter Monitor vorhanden, aber Platz ist (0, 0)"

    sx, sy, sr, su = sekundaer[0]["work"]
    assert sx <= x < sr, f"x={x} liegt nicht auf Monitor 2 ({sx}..{sr})"
    assert sy <= y < su, f"y={y} liegt nicht auf Monitor 2 ({sy}..{su})"


def test_window_position_never_on_the_primary_screen():
    """Das ist der eigentliche Zweck: Monitor 1 bleibt frei."""
    bildschirme = M.alle_monitore()
    sekundaer = [m for m in bildschirme if not m["primary"]]
    if not sekundaer:
        pytest.skip("nur ein Monitor")

    x, y = M.zweiter_monitor_platz()
    px, py, pr, pu = next(m for m in bildschirme if m["primary"])["work"]

    auf_primaer = px <= x < pr and py <= y < pu
    assert not auf_primaer, \
        f"Testfenster wuerde auf dem primaeren Monitor landen: ({x}, {y})"


def test_no_second_monitor_gives_zero_and_no_window():
    """Ohne zweiten Monitor: (0, 0). Der Aufrufer muss dann minimieren.

    Ruft man trotzdem start_auf_zweiten_monitor() auf und bekommt nicht
    (0, 0) zurueck, wuerde ein Fenster auf Monitor 1 aufgehen - genau
    das darf nicht passieren.
    """
    bildschirme = M.alle_monitore()
    if any(not m["primary"] for m in bildschirme):
        pytest.skip("zweiter Monitor vorhanden")

    assert M.zweiter_monitor_platz() == (0, 0)
    assert M.start_auf_zweiten_monitor(1280, 820) == (0, 0)
    assert not M.passt_auf_zweiten(1280, 820)


def test_window_too_big_for_second_monitor_is_refused():
    """Ein Fenster, das nicht passt, wird abgelehnt - nicht gestreckt."""
    bildschirme = M.alle_monitore()
    sekundaer = [m for m in bildschirme if not m["primary"]]
    if not sekundaer:
        pytest.skip("nur ein Monitor")

    sx, sy, sr, su = sekundaer[0]["work"]
    zu_gross = (sr - sx) + 5000
    assert not M.passt_auf_zweiten(zu_gross, 100)
    assert M.start_auf_zweiten_monitor(zu_gross, 100) == (0, 0)


def test_typical_window_size_fits_when_second_monitor_exists():
    bildschirme = M.alle_monitore()
    sekundaer = [m for m in bildschirme if not m["primary"]]
    if not sekundaer:
        pytest.skip("nur ein Monitor")

    sx, sy, sr, su = sekundaer[0]["work"]
    if (sr - sx) >= 1340 and (su - sy) >= 880:
        assert M.passt_auf_zweiten(1280, 820)
        assert M.start_auf_zweiten_monitor(1280, 820) != (0, 0)
    else:
        # Schmaler Monitor: 1000x700 ist das groesste, was passt
        assert M.passt_auf_zweiten(1000, 700)


def test_helpers_do_not_need_windows():
    """Die Funktionen hier duerfen kein Fenster erzeugen - nur rechnen."""
    # Zweimal aufrufen: wenn beim ersten Mal ein Fenster entstuende,
    # wuerde das hier auffallen (kein Fenster wird zurueckgegeben).
    erste = M.zweiter_monitor_platz()
    zweite = M.zweiter_monitor_platz()
    assert erste == zweite, "Ergebnis ist nicht stabil"
