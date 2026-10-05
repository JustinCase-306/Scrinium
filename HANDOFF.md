# Scrinium — Stand vom 4. Oktober 2026

Kurze Übersicht: was läuft, was nicht, und was als Nächstes ansteht.
Geschrieben für den Nutzer, nicht für ein Release-Dokument.

---

## Was heute passiert ist

### 1. Der Plan wurde festgelegt

Scrinium ist kein einzelnes Programm, sondern ein Rahmen plus Werkzeuge:

```
Scrinium/
  Scrinium.exe
  scrinium/                  <- was Scrinium selbst braucht
    kern.py                  <- findet die Werkzeuge, kennt keines davon
    texte.py                 <- alle sichtbaren Texte, ein Ort
    sprache/de.py, en.py     <- Sprachen als Dateien
    einstellungen.py          <- was der Nutzer einstellt
    bruecke.py               <- Verbindung zwischen Fenster und Kern
    fenster.py, fenster.html  <- das Fenster und seine Oberfläche
  tools/
    _downloadsorter/          <- ein Werkzeug, Ordner für Ordner
      __init__.py             <- NAME, pruefe(), starte(), vorschau()
      logik/regeln.py         <- die eigentliche Entscheidung
```

Ein Werkzeug ist ein Ordner mit drei Dingen:

```python
NAME  = "Downloads-Sortierer"
def pruefe(): ...            # darf ich starten?
def starte(): ...            # was ich tue, gibt immer dieselbe Form zurück
```

Neu ist ein Werkzeug? Ordner reinkopieren, fertig. Kein Code, keine
Konfigurationsdatei. Das war das Ziel, und es funktioniert.

### 2. Das Fenster ist ein echtes Programm

Ursprünglich war geplant: Browser. Jetzt ist es `pywebview` mit
WebView2 — ein echtes Fenster mit Rahmen, ohne URL-Leiste. Alt-F4
schließt, Ctrl+C nicht.

Warum pywebview und nicht Customtkinter: Material Design mit runden
Buttons, weichen Schatten und dunklen Farben geht in Tkinter nicht.
WebView2 ist auf Windows 11 Standard, auf dem Rechner in Version
154.0.4258 vorhanden.

### 3. Die Oberfläche

Drei Spalten: Werkzeuge links, Arbeit in der Mitte, Ordner und
Sicherheitshinweis rechts. Grundsätze:

- Schrift nie unter 13 px, meist 17 bis 34 px
- Keine Buttons ohne Text (außer die drei Fensterknöpfe oben)
- Klickflächen mindestens 48 px hoch
- Alle Aktions-Buttons sind rund
- Sprache: hell und dunkel, Standard folgt Windows

Gemessen in vier Fenstergrößen (1600, 1280, 1100, 960 px): kein
Überlauf, nichts abgeschnitten, nichts ragt heraus. Unter 1180 px
wandert die rechte Spalte nach unten, unter 1000 px wird die Leiste
zur schmalen Iconleiste.

### 4. Das Fenster kann echte Daten

Nicht nur bunt: es zeigt den Download-Ordner, die Liste der Dateien
mit ihrem Zielordner, und nach dem Klick das Ergebnis mit Undo-Knopf.

Unfertige Downloads sind sichtbar und bleiben liegen — mit dem Grund
„lädt noch". Das ist die wichtigste Sicherheitszusage, und sie steht
im Fenster, nicht nur im Code.

### 5. Fehler, die erst beim Prüfen auffielen

Das ist der ehrlichste Teil. Vier davon waren echte Fehler im Code:

| Fehler | Wirkung | Gefixt |
|---|---|---|
| `scrinium.ui.app` importiert | Fenster startete nicht | `main.pyw` zeigt jetzt auf `scrinium.launcher` |
| Window-Objekt im JSON-Zustand | `zustand()` verschluckte sich selbst | Fenster in eigenes Feld |
| `.work` ohne `min-height: 0` | Liste wurde unerreichbar, kein Scrollen | ergänzt |
| `--r-full` nie definiert | alle runden Elemente waren eckig | Token ergänzt |
| vier Zustandsklassen nie gesetzt | Kachel ohne Auswahl, Status ohne Farbe | werden jetzt gesetzt |
| `distutils` ausgeschlossen | Build brach ab | wieder raus, pythonnet braucht es |

Und zwei waren Fehler in **meinen Tests**, nicht im Produkt:

- Ich maß `MainWindowHandle` — bei pywebview immer 0. Richtig ist der
  WebView2-Kindprozess.
- Ich prüfte auf tote CSS-Regeln und übersah Klassen, die erst zur
  Laufzeit im JavaScript entstehen.

---

## Stand der Prüfungen

| Prüfung | Ergebnis |
|---|---|
| `pytest tests/` (kanonisch) | 288 passed |
| Fenster-DOM (echtes Fenster, 41 Dateien) | 22 von 22 |
| Brücke (Kern + Werkzeug, ohne Fenster) | 31 von 31 |
| Ad-hoc (main.pyw, Brücke, HTML, Spec, EXE) | 41 von 41 |
| Skalierung (4 Fenstergrößen) | 39 von 39 |

Die Ad-hoc-Skripte liegen in `%TEMP%`, nicht im Projekt:
`hermes-verify-scrinium-ui.py`, `hermes-verify-scrinium-scale.py`.
Aufräumen:

```bash
rm "$TEMP/hermes-verify-scrinium-ui.py" "$TEMP/hermes-verify-scrinium-scale.py"
```

Die drei Testskripte liegen dauerhaft in `prototypes/ui/`:
`test_fenster_dom.py`, `test_ui_integration.py`, `test_pywebview_start.py`.

---

## Was NICHT geprüft ist

Ehrlich, weil davon viel abhängt:

- **WebView2 fehlt auf einem anderen Rechner.** Der Pfad ist gebaut
  (eigene Fehlerseite, Hinweis auf `Scrinium.exe --sortieren`), aber
  nie durchlaufen. Auf Windows 10 ohne WebView2 würde Scrinium nicht
  starten.
- **200 % Windows-Skalierung.** Nur Pixelbreiten gemessen. Die
  rem-Abstände sind vorbereitet, geprüft ist es nicht.
- **Tastaturbedienung.** Getestet wurde Maus und Klick. Ein alter
  Mensch ohne Maus kann Scrinium vermutlich nicht bedienen.
- **Wie es wirklich aussieht.** Alle Messungen prüfen Struktur, nicht
  Schönheit. Das Aussehen wurde nie beurteilt — weder von mir noch,
  seit dem letzten Entwurf, von dir.

---

## Was ansteht

### Zuerst: `build.bat` ist kaputt (wichtig)

`PYTHONPATH` zeigt global auf den Hermes-Agent. Beim normalen Build
zieht PyInstaller dessen `cffi 2.0.0` mit, und die fertige EXE
startet mit:

```
Version mismatch: cffi 2.0.0 ... 2.1.1
```

Der saubere Build braucht `env -u PYTHONPATH -u PYTHONHOME`. Alle
heutigen Builds liefen so. **Ein normaler `build.bat` erzeugt bei dir
eine kaputte EXE** — das ist die erste Aufgabe für morgen.

### Dann, in dieser Reihenfolge

1. **`build.bat` reparieren**, dann frisch bauen und prüfen.
2. **README aktualisieren.** Beschreibt noch den alten Stand ohne Fenster.
3. **Installer neu bauen.** `Scrinium-Setup.exe` enthält eine EXE von
   heute 10:16, nicht die von 20:49.
4. **Zwei Sortierer nebeneinander.** Der alte (`engine.py`, `rules.py`,
   `categories.py`, ~3.660 Zeilen) und der neue in `tools/`. Beide haben
   Tests. Welcher bleibt, entscheidet den weiteren Aufbau.
5. **Ordner aufräumen.** Die HTML-Entwürfe in `prototypes/ui/` gehören
   entweder ins Git oder raus.

### Was danach kommt, wenn die UI steht

Die Werkzeuge, in dieser Reihenfolge — jede für sich allein nutzbar:

- **Duplicate Finder** — überschneidet sich mit keinem Werkzeug, kann
  sofort 800 MB einparen
- **Glash-Benachrichtigungen** — „You notice it when you look for it";
  WebView2 macht sie trivial
- **Screenshot-Namen per OCR** — deterministisch, offline, kein Modell
- **Screenshots benennen mit KI** — SmolVLM, abwählbar, nachladbar
- **Automatisch sortieren im Hintergrund** (Watcher, steht im Code, ist
  nicht verdrahtet)

Der Watcher ist übrigens schon fertig programmiert (`watcher.py`, 264
Zeilen, mit Tests) — er wird nur nirgends aufgerufen.

---

## Was nicht mehr gebaut wird

Aus dem ursprünglichen Plan, bewusst gestrichen:

- **Storage Analyzer** — überschneidet sich mit Everything und WizTree.
  Die lesen das NTFS-Metadatenverzeichnis direkt; das kann Scrinium
  ohne Admin-Rechte nicht.
- **Optionales sicheres Vault** — Angriffsfläche für ein Programm, das
  unbeaufsichtigt läuft. Reicht nicht als Grund.
- **KI als fester Bestandteil** — wird ein nachladbares Modul. Ein
  Modell, das einen Dateinamen festschreibt, muss man abschalten können.

---

## Ein Hinweis zum Git-Stand

Ein Commit liegt auf `main` (`c86d2ea`, Scrinium v2.0). Alles danach —
die Modularisierung, der Kern, das Fenster, die Oberfläche — ist
**uncommitted**.

Bewusst nicht committet: `add`, `commit` oder `push` ohne ausdrückliche
Zustimmung.

Bevor committet wird, einmal `git status` ansehen. Zu erwarten sind
neue Dateien unter `scrinium/`, `tools/`, `tests/`, `prototypes/` und
geänderte Dateien `main.pyw`, `Scrinium.spec`, `build.bat`.