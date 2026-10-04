"""Configuration: defaults, migration from v1, atomic saves.

Stored at ``%APPDATA%/Scrinium/config.json``. Everything is normalised on load
so the rest of the app never has to defend against a half-written config.
"""

from __future__ import annotations

import os

from . import categories as cat_mod
from .engine import COLLIDE_RENAME
from .util import atomic_write_json, norm_path, read_json, same_path

CFG_VERSION = 2


def cfg_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "Scrinium")
    os.makedirs(d, exist_ok=True)
    return d


def cfg_path() -> str:
    return os.path.join(cfg_dir(), "config.json")


def known_downloads_dir() -> str:
    """Ask Windows where Downloads really is (handles OneDrive redirection)."""
    # 1) the registry location shell uses for {374DE290-...} = Downloads
    try:
        import winreg

        key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            val, _ = winreg.QueryValueEx(k, "{374DE290-123F-4565-9164-39C4925E467B}")
            if val and os.path.isdir(val):
                return norm_path(val)
    except Exception:
        pass
    # 2) USERPROFILE\Downloads
    cand = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.isdir(cand):
        return norm_path(cand)
    # 3) OneDrive
    od = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer")
    if od:
        cand = os.path.join(od, "Downloads")
        if os.path.isdir(cand):
            return norm_path(cand)
    return norm_path(cand)


def default_config() -> dict:
    return {
        "version": CFG_VERSION,
        "dl": known_downloads_dir(),
        "paths": {},                       # category key -> absolute target dir
        "min_age_s": 30,                   # file must be this old to be moved
        "interval_min": 30,
        "watch_enabled": True,
        "interval_enabled": True,
        "start_with_windows": False,
        "minimize_to_tray": True,
        "close_to_tray": True,
        "notify": True,
        "appearance": "dark",
        "accent": "#3B8ED0",
        "lang": "de",
        "collide": COLLIDE_RENAME,
        "recursive": False,
        "disabled_categories": [],
        "custom_ext": [],
        "rules": [],
        "use_patterns": True,
        "first_run_done": False,
    }


def _migrate_v1(cfg: dict) -> dict:
    """v1 stored `iv` / `new` / `min` / `paths`.

    The guard below deliberately looks at the *legacy* keys only: the target
    keys (`interval_enabled`, `watch_enabled`) are already present in
    `default_config()`, so testing for them would always short-circuit and
    silently drop the user's settings.
    """
    if not any(k in cfg for k in ("iv", "new", "min")):
        return cfg
    if "iv" in cfg:
        cfg["interval_enabled"] = bool(cfg["iv"])
    if "new" in cfg:
        cfg["watch_enabled"] = bool(cfg["new"])
    if "min" in cfg:
        try:
            cfg["interval_min"] = max(1, min(10_080, int(cfg["min"])))
        except (TypeError, ValueError):
            pass
    cfg.pop("iv", None)
    cfg.pop("new", None)
    cfg.pop("min", None)
    # v1 `paths` keys are still category keys - they carry over unchanged
    cfg["version"] = CFG_VERSION
    return cfg


def _sanitize(cfg: dict) -> dict:
    out = default_config()
    out.update(cfg)

    out["dl"] = norm_path(out.get("dl") or "") or known_downloads_dir()

    paths = out.get("paths")
    if not isinstance(paths, dict):
        paths = {}
    clean_paths = {}
    for k, v in paths.items():
        if cat_mod.get(k):
            p = norm_path(v)
            if p:
                clean_paths[k] = p
    out["paths"] = clean_paths

    def _int(key, lo, hi, fallback):
        try:
            return max(lo, min(hi, int(out.get(key))))
        except (TypeError, ValueError):
            return fallback

    out["min_age_s"] = _int("min_age_s", 0, 86_400, 30)
    out["interval_min"] = _int("interval_min", 1, 10_080, 30)
    for key in ("watch_enabled", "interval_enabled", "start_with_windows",
                "minimize_to_tray", "close_to_tray", "notify", "recursive",
                "use_patterns", "first_run_done"):
        out[key] = bool(out.get(key))

    if out.get("appearance") not in ("dark", "light", "system"):
        out["appearance"] = "dark"
    if out.get("lang") not in cat_mod.LANGS:
        out["lang"] = "de"
    if out.get("collide") not in ("skip", "rename", "replace"):
        out["collide"] = COLLIDE_RENAME
    accent = str(out.get("accent") or "#3B8ED0")
    if not accent.startswith("#"):
        accent = "#3B8ED0"
    out["accent"] = accent

    out["disabled_categories"] = [
        k for k in (out.get("disabled_categories") or []) if cat_mod.get(k)
    ]

    custom = []
    for e in out.get("custom_ext") or []:
        if isinstance(e, dict) and e.get("ext"):
            custom.append({"ext": str(e["ext"]).lstrip("*.").lower(),
                           "to": str(e.get("to") or "")})
    out["custom_ext"] = [c for c in custom if cat_mod.get(c["to"])]

    rules = []
    for r in out.get("rules") or []:
        if isinstance(r, dict) and r.get("value") and r.get("target"):
            t = str(r["target"])
            if t == "!skip" or cat_mod.get(t):
                rules.append({
                    "kind": str(r.get("kind") or "pattern"),
                    "value": str(r["value"]),
                    "target": t,
                })
    out["rules"] = rules

    out["version"] = CFG_VERSION
    return out


def _migrate_legacy_file(cfg: dict) -> dict:
    """Import the v1 repo-adjacent config.json once, so settings survive."""
    try:
        import scrinium

        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(scrinium.__file__)))
    except Exception:
        app_dir = os.getcwd()
    legacy = os.path.join(app_dir, "config.json")
    here = cfg_path()
    if os.path.isfile(legacy) and not os.path.isfile(here):
        data = read_json(legacy)
        if isinstance(data, dict):
            for k in ("dl", "min", "paths", "colors", "iv", "new"):
                if k in data and k not in cfg:
                    cfg[k] = data[k]
            cfg["_migrated_from"] = norm_path(legacy)
    return cfg


def load_config() -> dict:
    cfg = default_config()
    data = read_json(cfg_path())
    if isinstance(data, dict):
        cfg.update(data)
    cfg = _migrate_v1(cfg)
    cfg = _migrate_legacy_file(cfg)
    cfg.pop("_migrated_from", None)
    return _sanitize(cfg)


def save_config(cfg: dict) -> str:
    path = cfg_path()
    atomic_write_json(path, _sanitize(cfg))
    return path


def target_dirs(cfg: dict, lang: str | None = None,
                 source_dir: str | None = None) -> dict[str, str]:
    """Full category -> destination mapping, filling in defaults.

    `source_dir` overrides the configured download folder for the *default*
    targets. This matters for `--source DIR` and for a temporary source: a
    relative default must land inside the folder actually being sorted, never
    in the configured one. Explicit `paths` entries always win.
    """
    lang = lang or cfg.get("lang", "de")
    dl = norm_path(source_dir) if source_dir else cfg["dl"]
    out = {}
    for c in cat_mod.CATEGORIES:
        custom = (cfg.get("paths") or {}).get(c.key)
        # folder_name() - never c.folder(lang): the language must not rename
        # the physical folders.
        out[c.key] = (norm_path(custom) if custom
                      else os.path.join(dl, cat_mod.folder_name(c.key, lang)))
    return out


def is_default_target(cfg: dict, key: str) -> bool:
    return not (cfg.get("paths") or {}).get(key)


def reset_paths(cfg: dict) -> dict:
    cfg["paths"] = {}
    return cfg


def source_ok(cfg: dict) -> bool:
    dl = cfg.get("dl") or ""
    return bool(dl) and os.path.isdir(dl) and not same_path(dl, os.path.expanduser("~"))
