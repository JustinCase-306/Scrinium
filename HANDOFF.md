# Scrinium v2.0 — Stand (01.10.2026)

**Nichts committet, nichts gepusht.** `.gitignore` ist fertig, aber `origin`
zeigt weiterhin auf ein fremdes Repo (siehe unten) — das braucht deine Freigabe.

---

## ✅ Fertig und verifiziert

**162 Tests grün** (`.venv\Scripts\python -m pytest tests\ -q`), EXE gebaut und
funktional durchgetestet.

| Bereich | Datei | LOC |
|---|---|---|
| Kategorien-Registry, 17 Kategorien / 320 Endungen | `scrinium/categories.py` | ~300 |
| Regelauflösung + Download-Vollständigkeit | `scrinium/rules.py` | ~270 |
| Dry-Run-Engine, Kollisionen, `apply()` | `scrinium/engine.py` | ~420 |
| Undo-Journal (JSON-Lines, crash-sicher) | `scrinium/history.py` | ~218 |
| Config v2, v1-Migration, Registry-Downloads-Ordner | `scrinium/config.py` | ~240 |
| DE/EN i18n, 89 Keys | `scrinium/i18n.py` | ~252 |
| Watcher mit Settle-Guard | `scrinium/watcher.py` | ~260 |
| Tray/Autostart/Single-Instance (ctypes) | `scrinium/platform_win.py` | ~430 |
| Theme (fixt v1-Akzent-Bug) | `scrinium/theme.py` | ~130 |
| CLI (11 Modi) | `scrinium/cli.py` | ~280 |
| Icon-Generator (7 Größen, kein Pillow) | `scrinium/icons.py` | ~150 |

Tests: `tests/` mit 162 Tests über categories, rules, engine, history, config,
watcher, CLI (Subprozess), i18n, util.

Packaging: `Scrinium.spec`, `build.bat`, `requirements.txt`,
`requirements-dev.txt`, Icon in `assets/scrinium.ico`.

---

## 🐛 Gefundene und behobene Bugs

Die meisten davon waren **echte Produktfehler**, nicht Testprobleme:

| # | Bug | Wirkung |
|---|---|---|
| 1 | **`--lang en` änderte die Ordnernamen** (`Dokumente/` → `Documents/`) | Sprachwechsel → zweiter leerer Ordnerbaum, Dateien wirken verloren. **Datenverlust-Optik.** |
| 2 | **v1-Migration lief nie** (`iv`/`new` wurden ignoriert) | Alle v1-Nutzer verlieren ihre Einstellungen beim Update |
| 3 | **Chrome-Temp-Erkennung war case-sensitiv** | `.com.google.Chrome.*` nie erkannt |
| 4 | **`--source DIR` ignorierte den Ordner** | Dateien landeten im *konfigurierten* Downloads-Ordner, nicht in `DIR` |
| 5 | **`--category` war `set("video")`** | `{v,i,d,e,o}` → „unknown category: e, v, d, o, i" |
| 6 | **`--category` schrieb `disabled_categories` persistent** | Ein einmaliger Aufruf deaktiviert dauerhaft alle anderen Kategorien |
| 7 | **EXE crashte nach dem Sortieren** (`UnicodeEncodeError` am `✓`) | Dateien waren verschoben, aber **kein `run_id` → kein Undo** |
| 8 | **`plan()` übersprang bei `recursive=True` jede Datei** | Unterordner wurden nie sortiert |
| 9 | **Settle-Guard prüfte alte Snapshots** | Dateien wurden **während des Schreibens** verschoben |
| 10 | **`_new_files` = Mengendifferenz** | Start bei laufendem Download → Datei wird nie einsortiert |
| 11 | **`ctypes` ohne Prototypen** | HWND auf 64 Bit abgeschnitten → Tray-Icon erschien nie |
| 12 | **`self.tip` überschrieb die Methode** | `AttributeError`/`TypeError` bei jedem Tray-Update |
| 13 | `Plan.to_dict` gab die falsche Struktur zurück | `--json` war unbrauchbar |
| 14 | `.ts` (TypeScript) als Video, `.3ds` doppelt | Falsche Einordnung |

Alle 14 haben einen Regressionstest in `tests/`.

---

## ⚠️ Nicht verifizierbar in dieser Umgebung

**Der Tray-Icon-Build.** `CreateWindowExW` liefert hier `0` — die Session hat
keinen interaktiven Desktop. Der Code ist korrekt (Prototypen deklariert,
`WS_POPUP`, Rückgabewert geprüft, `build()` gibt sauber `False` zurück statt zu
raisen, und die App läuft ohne Tray weiter) — aber ich kann nicht *sehen*,
dass das Symbol wirklich erscheint. Das gehört am Rechner getestet.

---

## 📋 Offen / nächste Schritte

1. **GUI (`scrinium/ui/`)** — das ist der einzige große Brocken, der noch
   fehlt. `main.pyw` importiert `scrinium.ui.app.run`; die Logik ist fertig,
   es fehlen nur die Widgets (4 Tabs: Sortieren mit Preview-Tabelle,
   Regeln, Verlauf mit Undo, Einstellungen).
2. **`build/version_info.txt`** — `build.bat` erwähnt sie, PyInstaller läuft
   aber auch ohne (getestet, Build ok).
3. **README** ist geschrieben; Screenshot fehlt noch.
4. **`ScriniumReleases/`** aufräumen: `Scrinium_v1_0.exe` und `_v1_1.exe` sind
   die 32-MB-Ballast-Builds (pystray+Pillow). Neu ist **8,1 MB**.

---

## ⚡ Vor dem ersten Commit

```bash
cd "C:/Users/Friedrich/Documents/Portfolio/GitHub/Scrinium"
git remote -v
```

Aktuell:

```
origin  https://github.com/JustinCase-306/Scrinium.git
```

**Das ist ein anderes Projekt.** Pushes würden in Scrinium landen. Ich fasse
das nicht an, bis du es freigibst — vermutlich soll es
`JustinAndBenjamin/Scrinium.git` sein.

Danach:

```bash
git add -A
git status          # prüfen: .venv/, dist/, build/, *.exe dürfen NICHT drin sein
git commit -m "Scrinium v2.0: dry-run engine, undo journal, 17 categories, CLI"
```

---

## 💾 Größe

| | v1.0 | v1.2/1.3 | v2.0 |
|---|---|---|---|
| EXE | 31,97 MB | 13,41 MB | **8,11 MB** |

Der Unterschied zu v1.2: Tray ohne `pystray`+`Pillow` (reines ctypes),
`excludes` im Spec, `upx=False` bleibt (UPX wäre kleiner, aber es nervt
Virenscanner).

---

## 🧪 Selbst testen

```bash
# 1. Tests
.venv\Scripts\python -m pytest tests\ -q

# 2. CLI mit Vorschau
.venv\Scripts\python -m scrinium --dry-run --lang de

# 3. Bauen
build.bat --test

# 4. GUI starten (funktioniert noch nicht — ui/ fehlt)
.venv\Scripts\python main.pyw
```