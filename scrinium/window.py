"""Scriniums Fenster.

Startet ein echtes Fenster (kein Browser) mit der HTML-Oberflaeche aus
`window.html` und verbindet sie mit dem Python-Kern ueber `bridge.py`.

Ablauf beim Start:

    Fenster oeffnet
      -> bridge.state()   holt Tools + Settings
      -> HTML baut sich auf  (Werkzeugleiste, Kopfzeile, Inhalt)
      -> Knopf "Sortieren"   ruft bridge.start_tool()
      -> Ergebnis erscheint  mit Undo-Knopf

Der Kern kennt das Fenster nicht, und das Fenster kennt den Kern nicht -
sie treffen sich nur in der Bruecke.
"""

from __future__ import annotations

import os
import sys
import threading

from . import bridge

# pywebview braucht .NET; fehlt es, ist das ein klarer Fehler statt
# eines Absturzes mitten im Start.
ERROR_HTML = """<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">
<title>Scrinium</title>
<style>
  body { font-family: "Segoe UI", system-ui, sans-serif; background: #141218;
         color: #e6e1e5; display: grid; place-items: center; height: 100vh;
         margin: 0; padding: 2rem; box-sizing: border-box; }
  .karte { max-width: 620px; text-align: center; }
  h1 { font-size: 30px; margin: 0 0 1rem; }
  p { font-size: 18px; line-height: 1.6; color: #cac4d0; margin: 0 0 1rem; }
  code { background: #2b2930; padding: .3rem .6rem; border-radius: 6px;
         font-size: 16px; color: #a8c7fa; }
  .klein { font-size: 15px; color: #938f99; margin-top: 1.5rem; }
</style></head><body><div class="karte">
  <h1>Scrinium braucht eine Komponente</h1>
  <p>Scrinium nutzt die Windows-Webansicht, um seine Oberflaeche zu zeichnen.
     Auf diesem Rechner fehlt sie.</p>
  <p>Du kannst sie kostenlos nachinstallieren:<br>
     <code>Scrinium startet danach ohne Neustart</code></p>
  <p class="klein">Die Sortierfunktion running auch ohne Fenster:<br>
     <code>Scrinium.exe --sortieren</code></p>
</div></body></html>"""


def _html_path() -> str:
    """Wo liegt window.html?

    Im fertigen Programm neben den Modulen, im Quellcode eine Ebene
    hoeher - beides darf nicht hart verdrahtet sein.
    """
    kandidaten = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "window.html"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "scrinium", "window.html"),
    ]
    if getattr(sys, "frozen", False):
        kandidaten.insert(0, os.path.join(os.path.dirname(sys.executable),
                                          "scrinium", "window.html"))
    for path in kandidaten:
        if os.path.isfile(path):
            return path
    return kandidaten[0]


def webview2_present():
    """Ist die Windows-Webansicht installiert?"""
    import glob
    muster = [
        r"C:\Program Files (x86)\Microsoft\EdgeWebView\Application\*\msedgewebview2.exe",
        r"C:\Program Files\Microsoft\EdgeWebView\Application\*\msedgewebview2.exe",
    ]
    for m in muster:
        if glob.glob(m):
            return True
    return False


def starten() -> int:
    """Oeffnet das Fenster. Gibt einen Exitcode zurueck."""
    if not webview2_present():
        # Kein Fenster moeglich: die CLI funktioniert trotzdem.
        print("Scrinium: Windows-Webansicht fehlt.")
        print("  Oberflaeche: nicht verfuegbar.")
        print("  Sortieren:    'Scrinium.exe --sortieren' funktioniert trotzdem.")
        return 2

    try:
        import webview
    except ImportError as e:
        print(f"Scrinium: pywebview fehlt ({e}).")
        return 3

    html = _html_path()
    if not os.path.isfile(html):
        html_pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "_fehlt.html")
        with open(html_pfad, "w", encoding="utf-8") as fh:
            fh.write(ERROR_HTML)
        html = html_pfad

    api = bridge_api()
    fenster = webview.create_window(
        "Scrinium", html,
        js_api=api,
        width=1280, height=820,
        min_size=(900, 620),
        background_color="#141218",
        text_select=False,
    )
    bridge.set_window(fenster)

    try:
        webview.start()
    except Exception as e:
        print(f"Scrinium: Fenster konnte nicht starten ({e}).")
        return 4
    return 0


def bridge_api():
    """Macht die Bruecke fuer JavaScript aufrufbar.

    pywebview ruft alles auf, was hier oeffentlich ist (kein _ vor dem
    Namen) - deshalb die kurze Liste statt `__all__`.
    """
    class Api:
        def state(self):
            return bridge.state()

        def start_tool(self, wid):
            return bridge.start_tool(wid)

        def toggle_tool(self, wid, an):
            return bridge.toggle_tool(wid, bool(an))

        def set_language(self, language):
            return bridge.set_language(language)

        def set_downloads_folder(self, path):
            return bridge.set_downloads_folder(path)

        def choose_folder(self):
            return bridge.choose_folder()

        def open_folder(self):
            return bridge.open_folder()

        def open_settings(self):
            return bridge.open_settings()

        def preview(self, wid):
            return bridge.preview(wid)

        def _action(self, kennung):
            """Wird von der Oberflaeche ueber API['_action'] aufgerufen.

            Der fuehrende Unterstrich ist Absicht: pywebview blendet
            Attribute mit Unterstrich aus dem normalen Zugriff aus, damit
            nur die beabsichtigten Funktionen sichtbar sind. Die
            Oberflaeche umgeht das bewusst - es ist eine interne Route.
            """
            return bridge.action(kennung)

    return Api()


if __name__ == "__main__":
    sys.exit(starten())