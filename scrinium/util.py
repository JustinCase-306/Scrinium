"""Small shared helpers: sizes, timestamps, atomic file writes."""

from __future__ import annotations

import datetime as _dt
import json
import os
import tempfile
import time

_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


def human_size(num_bytes: float, precision: int = 1) -> str:
    """1234567 -> '1.2 MB'."""
    try:
        num_bytes = float(num_bytes)
    except (TypeError, ValueError):
        return "?"
    for unit in _UNITS:
        if abs(num_bytes) < 1024.0 or unit == _UNITS[-1]:
            if unit == "B":
                return f"{int(num_bytes)} B"
            return f"{num_bytes:.{precision}f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def now() -> float:
    return time.time()


def ts_iso(when: float | None = None) -> str:
    when = time.time() if when is None else when
    return _dt.datetime.fromtimestamp(when).isoformat(timespec="seconds")


def ts_human(when: float | None = None) -> str:
    when = time.time() if when is None else when
    return _dt.datetime.fromtimestamp(when).strftime("%d.%m.%Y %H:%M")


def ts_clock(when: float | None = None) -> str:
    when = time.time() if when is None else when
    return _dt.datetime.fromtimestamp(when).strftime("%H:%M:%S")


def ts_id(when: float | None = None) -> str:
    when = time.time() if when is None else when
    return _dt.datetime.fromtimestamp(when).strftime("%Y%m%d-%H%M%S")


def atomic_write(path: str, data: str, encoding: str = "utf-8") -> None:
    """Write `data` to `path` without ever leaving a half-written file behind.

    Writes to a temp file in the same directory, flushes + fsyncs, then
    replaces the target. On Windows os.replace() is atomic-ish and, crucially,
    fails if the target is open, which we want to surface.
    """
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(path: str, obj) -> None:
    atomic_write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def read_json(path: str, fallback=None):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return fallback


def norm_path(path: str) -> str:
    """Normalise for config storage: forward slashes, no trailing slash."""
    if not path:
        return ""
    p = str(path).replace("\\", "/").strip()
    if len(p) > 3 and p.endswith("/"):
        p = p.rstrip("/")
    return os.path.expandvars(os.path.expanduser(p)) if p.startswith("~") else p


def same_path(a: str, b: str) -> bool:
    try:
        return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
    except (TypeError, ValueError):
        return False


def is_inside(child: str, parent: str) -> bool:
    """True if `child` is `parent` or lives below it."""
    try:
        c = os.path.normcase(os.path.abspath(child))
        p = os.path.normcase(os.path.abspath(parent))
    except (TypeError, ValueError):
        return False
    if c == p:
        return True
    if not p.endswith(os.sep):
        p += os.sep
    return c.startswith(p)


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))
