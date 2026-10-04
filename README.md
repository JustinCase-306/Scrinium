# Scrinium v2.0

Sorts your **Downloads** folder into category subfolders — automatically, and
always reversibly.

> We do not want to know what you are downloading. Everything happens on your
> machine, nothing is uploaded, ever.

---

## What makes v2 different

v1.3 could move files. v2.0 is built around not losing them:

| | |
|---|---|
| **Dry-run first** | Every run is planned before a single byte moves. You see the exact list, then you confirm. |
| **Full undo** | Every move is written to a journal. `scrinium --undo <run_id>` puts everything back. |
| **Never grabs half-downloads** | `.crdownload`, `.part`, `.crx`, `~$` locks and files still being written are skipped — automatically. |
| **Never overwrites** | Name conflicts become `name_01`, `name_02`… The existing file is never touched. |
| **Idempotent** | Running it twice moves nothing the second time. Your category folders are never re-sorted. |
| **17 categories, 320 extensions** | Images, Video, Music, Audio, Documents, Sheets, Slides, Books, Archives, Disk Images, Applications, Code, Fonts, Design, 3D/CAD, Games, Other. |
| **Your own rules** | Map by filename pattern or by extension. Test a filename before you trust it. |
| **Windows integration** | Tray icon, autostart, single instance, desktop notifications. |
| **German & English** | Interface language never changes your folder names. |
| **Headless CLI** | Same engine without the GUI — for Task Scheduler, shortcuts or scripts. |

---

## Install

**No install needed** — grab `Scrinium.exe` and run it.

<details>
<summary>Run from source</summary>

```bash
git clone https://github.com/JustinAndBenjamin/Scrinium
cd Scrinium
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python main.pyw
```
</details>

---

## How it decides

1. **Protected files** are never touched (`Desktop.ini`, `Thumbs.db`, `.lnk`, `.url`, `.sys`, …).
2. **Incomplete downloads** are skipped: known temp suffixes, Office lock files, and — the important one — anything whose size or mtime changed in the last few seconds.
3. **Your rules** win: filename patterns first, then your custom extensions.
4. **Built-in extension table** decides the rest.
5. **Name hints** catch screenshots and similar extension-less files.
6. Otherwise the file is left alone and listed as *skipped*, with a reason.

Files younger than `min_age_s` (default 30 s) are never moved. That single
setting is what keeps a browser download safe.

---

## CLI

The GUI is optional — the whole engine is available headless:

```bash
scrinium --dry-run                 # preview only, moves nothing
scrinium --once                    # sort now
scrinium --once --json             # machine readable
scrinium --source D:\Other         # sort a different folder
scrinium --category video --once   # only one category
scrinium --lang en --dry-run       # English labels
scrinium --history                 # recent runs
scrinium --undo 20261004-101530    # undo a run
scrinium --stats                   # lifetime totals
scrinium --recursive --dry-run     # include subfolders
```

Every run prints its `run_id`; keep it if you might want to undo.

### As a scheduled task

```bat
scrinium.exe --once --min-age 120
```

No GUI, no tray, no window — just sorts quietly.

---

## Configuration

Stored in `%APPDATA%\Scrinium\`:

| File | Purpose |
|---|---|
| `config.json` | Settings. Written atomically. |
| `history.jsonl` | Append-only undo journal (crash-safe). |
| `history.json` | Bounded index for fast GUI access. |
| `accent.json` | Generated customtkinter theme. |

Your v1 `config.json` is imported automatically on first start.

---

## Development

```bash
.venv\Scripts\python -m pytest tests\ -q     # 162 tests
build.bat --test                             # test, then build the exe
python -m scrinium.icons                     # regenerate assets/scrinium.ico
```

Layout:

```
scrinium/
  categories.py    registry: 17 categories, 320 extensions
  rules.py         rule resolution + download-completeness detection
  engine.py        plan() dry-run, apply(), collision policies
  history.py       undo journal
  config.py        defaults, v1 migration, Windows known-folder lookup
  watcher.py       settle-guarded background worker
  platform_win.py  tray / autostart / single instance (pure ctypes)
  theme.py         customtkinter theming
  cli.py           headless interface
  ui/              customtkinter GUI
tests/             162 tests
```

---

## Credits

* **Logic & code:** [@JustinCase-306](https://github.com/JustinCase-306)
* **Original v1 GUI:** DeepSeek v4 — *"I have absolutely no idea of Python UI
  libraries"*
* **v2 GUI:** rebuilt on customtkinter with a dry-run-first design

## License

MIT