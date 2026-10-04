"""customtkinter theming.

Fixes the v1 bugs where a custom accent colour was silently replaced by the
preset on save and never applied at all. Here the accent is stored verbatim,
and :func:`apply` is always called after a save so the change is visible
immediately.
"""

from __future__ import annotations

import json
import os

import customtkinter as ctk

from .config import cfg_dir

APPEARANCES = ("dark", "light", "system")
APPEARANCE_LABELS = {"dark": "Dunkel", "light": "Hell", "system": "System"}

# the three colours customtkinter's blue theme uses for accent-ish widgets
BASE_THEME = "blue"
_SWAP = {
    "#3B8ED0": "primary",     # hover/pressed
    "#1F6AA5": "deep",
    "#36719F": "mid",
    "#145680": "dark",
}


def _hex_to_rgb(hexcol: str) -> tuple[int, int, int]:
    h = hexcol.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return (59, 142, 208)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return (59, 142, 208)


def lighten(hexcol: str, factor: float = 1.25) -> str:
    r, g, b = _hex_to_rgb(hexcol)
    return "#%02X%02X%02X" % (
        min(255, int(r * factor)), min(255, int(g * factor)), min(255, int(b * factor))
    )


def darken(hexcol: str, factor: float = 0.72) -> str:
    r, g, b = _hex_to_rgb(hexcol)
    return "#%02X%02X%02X" % (
        max(0, int(r * factor)), max(0, int(g * factor)), max(0, int(b * factor))
    )


def relative_luminance(hexcol: str) -> float:
    """WCAG contrast helper - used to pick readable foreground colours."""
    def chan(c: int) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _hex_to_rgb(hexcol)
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def on_color(hexcol: str) -> str:
    """Black or white - whichever reads better on `hexcol`."""
    return "#000000" if relative_luminance(hexcol) > 0.45 else "#FFFFFF"


def _theme_source() -> dict:
    base = os.path.join(os.path.dirname(ctk.__file__), "assets", "themes",
                        f"{BASE_THEME}.json")
    try:
        with open(base, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _swap(obj, mapping: dict):
    if isinstance(obj, dict):
        return {k: _swap(v, mapping) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_swap(v, mapping) for v in obj]
    if isinstance(obj, str) and obj.startswith("#") and obj.upper() in mapping:
        return mapping[obj.upper()]
    return obj


def custom_theme_path(accent: str) -> str:
    """Write a ctk theme json derived from the built-in one, recoloured."""
    mapping = {
        "#3B8ED0": accent,
        "#1F6AA5": darken(accent, 0.62),
        "#36719F": darken(accent, 0.80),
        "#145680": darken(accent, 0.45),
    }
    theme = _swap(_theme_source(), mapping)
    out = os.path.join(cfg_dir(), "accent.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(theme, fh)
    os.replace(tmp, out)
    return out


def apply(appearance: str = "dark", accent: str = "#3B8ED0") -> None:
    """Apply appearance + accent. Safe to call repeatedly (v1 called it once)."""
    if appearance not in APPEARANCES:
        appearance = "dark"
    try:
        ctk.set_appearance_mode(appearance)
    except Exception:
        pass
    accent = (accent or "#3B8ED0").strip()
    try:
        if accent.startswith("#"):
            ctk.set_default_color_theme(custom_theme_path(accent))
        else:
            ctk.set_default_color_theme(accent)
    except Exception:
        ctk.set_default_color_theme(BASE_THEME)


def apply_from_config(cfg: dict) -> None:
    apply(cfg.get("appearance", "dark"), cfg.get("accent", "#3B8ED0"))


def color_of(category_key: str, fallback: str = "#64748B") -> str:
    from . import categories as cat_mod

    return cat_mod.color(category_key) or fallback