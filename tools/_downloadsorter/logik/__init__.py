"""Die Arbeits-Logik des Downloads-Sortierers.

Dieser Ordner gehoert zum Tool, nicht zum Scrinium-Kern. Hier liegen
die Entscheidungen ("welche Datei gehoert wohin", "ist die Datei fertig",
"was passiert bei Namenskonflikten").

Der Ordner ist absichtlich ein eigener Namensraum: wenn ein anderes
Tool auch eine Datei `regeln.py` hat, gibt das keine Kollision.
"""

from __future__ import annotations