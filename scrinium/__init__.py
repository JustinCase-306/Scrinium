"""Scrinium - keep your Downloads folder tidy.

A GUI + CLI download sorter with a safety-first design engine:

*   dry-run planning (preview every move before anything happens)
*   download-completeness detection (never move a half-written file)
*   full undo journal for every run
*   17 categories, user-defined extension rules and filename patterns
*   Windows tray icon, autostart, DE/EN interface

Public entry points::

    from scrinium import App, run_cli, load_config
"""

from __future__ import annotations

APP_NAME = "Scrinium"
APP_ID = "Scrinium"
VERSION = "2.0.0"
TAGLINE = "Download-Auto-Sorter"

__all__ = [
    "APP_NAME",
    "APP_ID",
    "TAGLINE",
    "VERSION",
    "__version__",
]

__version__ = VERSION


def __getattr__(name):  # lazy, so `import scrinium` stays cheap
    if name == "App":
        from .ui.app import App

        return App
    if name == "run_cli":
        from .cli import run_cli

        return run_cli
    if name == "load_config":
        from .config import load_config

        return load_config
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
