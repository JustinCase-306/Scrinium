"""Update check against the GitHub Releases API.

Uses only the stdlib (``urllib``) so it works in the frozen exe without extra
dependencies. The check is anonymous and rate-limited, so it is cached and
never blocks the UI for long.

Source of truth is the releases feed of the repository:

    https://api.github.com/repos/JustinCase-306/Scrinium/releases/latest

Version comparison is numeric-segment based, so ``2.0.10`` correctly beats
``2.0.9`` (a plain string compare would get this wrong).
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from . import APP_NAME
from .util import atomic_write_json, human_size, now, read_json, ts_human

REPO = "JustinCase-306/Scrinium"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
API_LIST = f"https://api.github.com/repos/{REPO}/releases?per_page=30"
CACHE_FILE = "update-check.json"
CACHE_TTL = 3 * 3600          # re-check at most every 3 hours
TIMEOUT = 8

UA = f"{APP_NAME}-updater"


# --- version comparison ----------------------------------------------------
def parse_version(text: str) -> tuple:
    """'v2.0.10-beta' -> (2, 0, 10, 'beta'). Sortable, and pre-release loses
    to the final release of the same number."""
    raw = str(text or "").strip().lstrip("vV")
    m = re.match(r"^(\d+(?:\.\d+)*)", raw)
    nums = tuple(int(p) for p in m.group(1).split(".")) if m else (0,)
    tag = raw[m.end():].strip("-_+") if m else raw
    # a pre-release sorts *below* the same version without a suffix
    return nums + ((0,) if not tag else (-1,) + tuple(ord(c) for c in tag[:8]))


def is_newer(remote: str, local: str) -> bool:
    return parse_version(remote) > parse_version(local)


# --- network ---------------------------------------------------------------
def _get_json(url: str, timeout: int = TIMEOUT):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def _fetch_latest() -> dict:
    """Newest release, drafts excluded.

    `/releases/latest` 404s when *every* release is flagged as a prerelease -
    which is exactly the case for this repo. So we fall back to the list
    endpoint and pick the highest version ourselves.
    """
    try:
        return _get_json(API_LATEST)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    except (urllib.error.URLError, OSError, ValueError):
        return {}

    try:
        releases = _get_json(API_LIST)
    except (urllib.error.URLError, OSError, ValueError):
        return {}
    if not isinstance(releases, list):
        return {}

    usable = [r for r in releases if not r.get("draft") and r.get("tag_name")]
    if not usable:
        return {}
    return max(usable, key=lambda r: parse_version(r["tag_name"]))


def cache_path(cfg_dir: str) -> str:
    return os.path.join(cfg_dir, CACHE_FILE)


def read_cache(cfg_dir: str) -> dict:
    return read_json(cache_path(cfg_dir), {}) or {}


def write_cache(cfg_dir: str, data: dict) -> None:
    try:
        atomic_write_json(cache_path(cfg_dir), data)
    except OSError:
        pass


def clear_cache(cfg_dir: str) -> None:
    try:
        os.unlink(cache_path(cfg_dir))
    except OSError:
        pass


def pick_asset(release: dict) -> dict | None:
    """Prefer a plain windows exe, then the installer.

    Older releases shipped the binaries under the previous product name, so
    match on the extension and role rather than on a hard-coded name.
    """
    assets = release.get("assets") or []
    if not assets:
        return None

    def rank(a: dict) -> int:
        name = (a.get("name") or "").lower()
        if not name.endswith(".exe"):
            return 3
        return 1 if ("setup" in name or "install" in name) else 0

    exes = [a for a in assets if rank(a) < 3]
    if not exes:
        return assets[0]
    return sorted(exes, key=lambda a: (rank(a), a.get("name", "")))[0]


def check_for_update(cfg_dir: str, current: str | None = None,
                    force: bool = False, lang: str = "de") -> dict:
    """Returns ``{available, current, version, url, notes, size_h, checked_at}``.

    Never raises: on any failure it reports ``available: False`` and an
    ``error`` key, so a flaky network can never break the app.
    """
    from . import VERSION

    current = current or VERSION
    cache = read_cache(cfg_dir)
    checked = float(cache.get("checked_at") or 0)

    if not force and checked and (now() - checked) < CACHE_TTL:
        remote = cache.get("version")
        if remote:
            return {
                "available": is_newer(remote, current),
                "current": current,
                "version": remote,
                "url": cache.get("url", ""),
                "notes": cache.get("notes", ""),
                "size_h": cache.get("size_h", ""),
                "checked_at": checked,
                "cached": True,
            }

    try:
        release = _fetch_latest()
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
        return {
            "available": bool(cache.get("version")) and
                         is_newer(cache["version"], current),
            "current": current,
            "version": cache.get("version", ""),
            "url": cache.get("url", ""),
            "notes": cache.get("notes", ""),
            "size_h": cache.get("size_h", ""),
            "checked_at": checked,
            "error": str(exc),
            "cached": bool(cache.get("version")),
        }

    tag = release.get("tag_name") or release.get("name") or ""
    asset = pick_asset(release)
    info = {
        "available": is_newer(tag, current) if tag else False,
        "current": current,
        "version": tag,
        "url": release.get("html_url", ""),
        "notes": (release.get("body") or "")[:4000],
        "size_h": human_size(int(asset.get("size") or 0)) if asset else "",
        "asset_url": asset.get("browser_download_url", "") if asset else "",
        "published": release.get("published_at", ""),
        "checked_at": now(),
    }
    write_cache(cfg_dir, {
        "checked_at": info["checked_at"],
        "version": tag,
        "url": info["url"],
        "notes": info["notes"],
        "size_h": info["size_h"],
    })
    return info


def describe(info: dict, lang: str = "de") -> str:
    """One-line human summary for the log / notification."""
    if info.get("error"):
        return {"de": f"Update-Prüfung fehlgeschlagen: {info['error']}",
                "en": f"Update check failed: {info['error']}"}[lang]
    if info.get("available"):
        return {"de": f"Scrinium {info['version']} ist verfügbar (installiert: {info['current']}).",
                "en": f"Scrinium {info['version']} is available (installed: {info['current']})."}[lang]
    return {"de": f"Scrinium {info['current']} ist aktuell.",
            "en": f"Scrinium {info['current']} is up to date."}[lang]


# --- applying an update ----------------------------------------------------
def download_asset(url: str, dest_dir: str, timeout: int = 60,
                   progress=None) -> str | None:
    """Stream an asset to `dest_dir`. Returns the file path or None."""
    if not url:
        return None
    os.makedirs(dest_dir, exist_ok=True)
    target = os.path.join(dest_dir, os.path.basename(url.split("?")[0]) or "Scrinium.exe")
    tmp = target + ".part"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as fh:
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = resp.read(64 * 512)
                if not chunk:
                    break
                fh.write(chunk)
                done += len(chunk)
                if progress is not None and total:
                    progress(done, total)
        os.replace(tmp, target)
        return target
    except (urllib.error.URLError, OSError, ValueError) as exc:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return None if exc is None else None


def apply_update(info: dict, install_dir: str, launch: bool = True) -> dict:
    """Download the newest asset and install it over the current copy.

    Never raises. Returns ``{ok, path, error}``.
    """
    url = info.get("asset_url") or ""
    if not url:
        return {"ok": False, "path": "", "error": "no asset url"}

    payload = download_asset(url, os.path.join(install_dir, "_update"))
    if not payload:
        return {"ok": False, "path": "", "error": "download failed"}

    try:
        from .installer import install
    except Exception as exc:                        # pragma: no cover
        return {"ok": False, "path": payload, "error": str(exc)}

    # install() names the target Scrinium.exe and handles a locked binary by
    # renaming it aside, so a running instance does not block the update.
    rc = install(payload, install_dir, launch=launch, quiet=True)
    try:
        os.unlink(payload)
    except OSError:
        pass
    return {"ok": rc == 0, "path": os.path.join(install_dir, "Scrinium.exe"),
            "error": "" if rc == 0 else f"installer rc {rc}"}