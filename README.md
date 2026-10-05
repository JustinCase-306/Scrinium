# Scrinium

Sorts your **Downloads** folder into category subfolders — automatically,
visibly, and always reversibly.

> We do not want to know what you are downloading. Everything happens on your
> machine, nothing is uploaded, ever.

---

## What it is

Scrinium is a **frame plus tools**. The frame is the program; the tools are
folders you can add, remove or switch off.

```
Scrinium/
  Scrinium.exe          <- the frame: one window, nothing else
  scrinium/             <- what Scrinium itself needs
    core.py             <- finds the tools, knows none of them
    bridge.py           <- connection between window and tools
    window.py           <- starts the real window
    window.html         <- the interface
    texts.py            <- all visible text, in one place
    sprache/de.py, en.py
    settings.py         <- what the user configured
    cli.py              <- headless interface
    engine.py, rules.py, categories.py, history.py, watcher.py
  tools/
    _downloadsorter/    <- a tool
      __init__.py       <- NAME, check(), start(), preview()
      logik/regeln.py   <- the actual decision
```

A tool is a folder with three things:

```python
NAME  = "Downloads-Sortierer"

def check() -> tuple[bool, str]:   # may I start?
def start() -> dict:               # what I do - always the same shape
```

`start()` always returns:

```python
{"text": "...", "actions": [...], "data": {...}}
```

**That is the whole contract.** The frame displays `text` and offers
`actions` as buttons — it does not know what a duplicate finder does. So a
new tool is a new folder. No code change anywhere else.

---

## What makes it different

| | |
|---|---|
| **Preview before every move** | The window shows exactly which file goes where, *then* you click. Nothing moves until then. |
| **Full undo** | Every move is written to a journal. `scrinium --undo <run_id>` puts everything back. |
| **Never grabs half-downloads** | `.crdownload`, `.part`, `~$` locks and files younger than 30 s are skipped — automatically. |
| **Never overwrites** | Name conflicts become `name_01`, `name_02`. The existing file is never touched. |
| **Idempotent** | Running it twice moves nothing the second time. |
| **Your folders stay German** | Switching the interface to English never renames `Dokumente` or `Bilder`. |
| **Headless CLI** | The whole engine works without a window — for Task Scheduler or scripts. |
| **A real window** | Not a browser. No URL bar, no tabs. Alt+F4 closes it, Ctrl+C does not. |

---

## Install

**No install needed** — grab `Scrinium.exe` and run it.

Requires the Windows web view (WebView2), which ships with Windows 11. If it
is missing, Scrinium says so and the CLI still works.

<details>
<summary>Run from source</summary>

```bash
git clone https://github.com/JustinCase-306/Scrinium
cd Scrinium
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python main.pyw
```
</details>

---

## The window

Three columns: tools on the left, work in the middle, folder and safety
notes on the right.

Designed for someone who is 80 and has never seen this program:

- Type never below 13 px, mostly 17–34 px
- No button without a label (except the three window controls)
- Click areas at least 48 px high
- Material Design, dark or light, follows Windows by default
- Measured at four window sizes: nothing overflows, nothing gets cut off

Colour and light/dark are meant to follow the system, not be chosen.

---

## CLI

The window is optional:

```bash
scrinium --dry-run                 # preview only, moves nothing
scrinium --once                    # sort now
scrinium --once --json             # machine readable
scrinium --source D:\Other         # sort a different folder
scrinium --lang en --dry-run       # English labels
scrinium --history                 # recent runs
scrinium --undo 20261004-101530    # undo a run
scrinium --stats                   # lifetime totals
```

Every run prints its `run_id`; keep it if you might want to undo.

---

## Configuration

Stored in `%APPDATA%\Scrinium\`:

| File | Purpose |
|---|---|
| `config.json` | Settings. Written atomically. |
| `laeufe.json` | The sort runs, with everything needed for undo. |
| `update-check.json` | When the update check last ran. |

Settings are never written into the program folder — that way you can put
Scrinium anywhere, including a USB stick.

> **Known problem:** the old core (`engine.py`) also keeps a journal in
> `history.jsonl` / `history.json`. The tool in `tools/_downloadsorter/`
> uses `laeufe.json` instead. Two journals, one program — that needs
> cleaning up before the next release.

---

## Development

```bash
.venv\Scripts\python -m pytest tests\ -q     # 288 tests
build.bat --test                             # test, then build the exe
build.bat installer                          # also build Scrinium-Setup.exe
```

**Important for building:** `PYTHONPATH` and `PYTHONHOME` must be empty.
If something global points at another Python, PyInstaller bundles its `cffi`
and the finished exe dies with a version mismatch. `build.bat` clears both
itself.

### Tests that exist

| Test | What it checks |
|---|---|
| `tests/` | 288 tests: categories, rules, engine, undo, config, CLI, watcher, core, texts, tool |
| `prototypes/ui/test_fenster_dom.py` | reads the real window's DOM (22 checks) |
| `prototypes/ui/test_ui_integration.py` | core + bridge without a window (19 checks) |

**Never open a window visibly while testing.** The user works on this
machine. Start minimised (`SW_MINIMIZE` + `CREATE_NO_WINDOW`) and read the
DOM through `evaluate_js`. Proof that a window was created: the WebView2
child process appears in `tasklist`. `MainWindowHandle` is always 0 with
pywebview and proves nothing.

Project-specific rules live in `.hermes.md`.

---

## Credits

* **Logic & code:** [@JustinCase-306](https://github.com/JustinCase-306)
* **Original v1 GUI:** DeepSeek v4
* **v2 interface:** pywebview + WebView2, HTML/CSS, Material Design

## License

MIT