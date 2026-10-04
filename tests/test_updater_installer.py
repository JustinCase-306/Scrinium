"""Updater and installer.

The repo's GitHub releases are all flagged as prereleases, which is why
`/releases/latest` 404s - the fallback to the list endpoint is load-bearing,
not defensive fluff.
"""

from __future__ import annotations

import json
import os

import pytest

from scrinium import installer as I
from scrinium import updater as U


# --- version ordering ------------------------------------------------------
@pytest.mark.parametrize("remote,local,expected", [
    ("2.0.10", "2.0.9", True),
    ("2.0.9", "2.0.10", False),
    ("v3.0.0", "2.9.9", True),
    ("2.0.0", "2.0.0", False),
    ("2.0.0-beta", "2.0.0", False),      # prerelease loses to the release
    ("2.0.0", "2.0.0-beta", True),
    ("", "1.0.0", False),
    ("garbage", "1.0.0", False),
])
def test_is_newer(remote, local, expected):
    assert U.is_newer(remote, local) is expected


def test_parse_version_is_numeric_not_lexicographic():
    assert U.parse_version("2.0.10") > U.parse_version("2.0.9")


def test_v_prefix_ignored():
    assert U.parse_version("v1.2.3") == U.parse_version("1.2.3")


# --- asset selection -------------------------------------------------------
def test_prefers_plain_exe_over_setup():
    rel = {"assets": [{"name": "Scrinium-Setup.exe"}, {"name": "Scrinium.exe"}]}
    assert U.pick_asset(rel)["name"] == "Scrinium.exe"


def test_setup_only():
    assert U.pick_asset({"assets": [{"name": "Scrinium-Setup.exe"}]})["name"] == \
        "Scrinium-Setup.exe"


def test_legacy_asset_names_still_match():
    """Releases before the rename shipped Downsort*.exe."""
    rel = {"assets": [{"name": "Downsort_v1_3.exe"}]}
    assert U.pick_asset(rel)["name"] == "Downsort_v1_3.exe"


def test_no_assets():
    assert U.pick_asset({}) is None
    assert U.pick_asset({"assets": []}) is None


def test_non_exe_fallback():
    assert U.pick_asset({"assets": [{"name": "a.zip"}]})["name"] == "a.zip"


# --- network ---------------------------------------------------------------
def test_check_for_update_never_raises(tmp_path):
    """A broken network must never crash the caller."""
    info = U.check_for_update(str(tmp_path), current="2.0.0", force=True)
    assert isinstance(info, dict)
    assert "available" in info and "current" in info


def test_cache_roundtrip(tmp_path):
    cfg = str(tmp_path)
    U.write_cache(cfg, {"checked_at": U.now(), "version": "v9.9.9", "url": "u"})
    assert U.read_cache(cfg)["version"] == "v9.9.9"
    U.clear_cache(cfg)
    assert U.read_cache(cfg) == {}


def test_cached_version_is_used_when_offline(tmp_path, monkeypatch):
    cfg = str(tmp_path)
    U.write_cache(cfg, {"checked_at": U.now(), "version": "v9.9.9", "url": "u"})

    def boom(*_a, **_k):
        raise OSError("offline")

    monkeypatch.setattr(U, "_fetch_latest", boom)
    info = U.check_for_update(cfg, current="2.0.0", force=True)
    assert info["cached"] is True
    assert info["version"] == "v9.9.9"
    assert info["available"] is True
    assert info["error"]


def test_offline_without_cache_reports_no_update(tmp_path, monkeypatch):
    def boom(*_a, **_k):
        raise OSError("offline")

    monkeypatch.setattr(U, "_fetch_latest", boom)
    info = U.check_for_update(str(tmp_path), current="2.0.0", force=True)
    assert info["available"] is False
    assert "error" in info


def test_download_rejects_empty_and_bad_urls(tmp_path):
    assert U.download_asset("", str(tmp_path)) is None
    # unroutable port -> must return None rather than raise
    assert U.download_asset("http://127.0.0.1:1/x.exe", str(tmp_path), timeout=2) is None
    assert not list(tmp_path.glob("*.part")), "partial file left behind"


def test_apply_update_without_url_fails_cleanly(tmp_path):
    res = U.apply_update({}, str(tmp_path))
    assert res["ok"] is False and res["error"]


# --- describe --------------------------------------------------------------
def test_describe_translations():
    assert "aktuell" in U.describe({"current": "2.0.0", "available": False}, "de")
    assert "up to date" in U.describe({"current": "2.0.0", "available": False}, "en")
    assert "verfügbar" in U.describe(
        {"current": "2.0.0", "available": True, "version": "2.1.0"}, "de")
    assert "fehlgeschlagen" in U.describe({"error": "boom"}, "de")


# --- installer -------------------------------------------------------------
@pytest.fixture
def payload(tmp_path):
    p = tmp_path / "Scrinium.exe"
    p.write_bytes(b"MZ" + b"\x00" * 500)
    return str(p)


def test_install_copies_exe(payload, tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    target = str(tmp_path / "Programs" / "Scrinium")
    assert I.install(payload, target, launch=False) == 0
    assert os.path.exists(os.path.join(target, "Scrinium.exe"))


def test_install_is_repeatable(payload, tmp_path, monkeypatch):
    """Regression: the payload used to be deleted, making a second install
    impossible."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    target = str(tmp_path / "Programs" / "Scrinium")
    for _ in range(3):
        assert I.install(payload, target, launch=False) == 0
    assert os.path.exists(payload), "installer deleted its own payload"


def test_install_missing_payload(tmp_path):
    assert I.install(str(tmp_path / "nope.exe"), str(tmp_path / "t")) == 1


def test_install_into_unwritable_dir(payload, tmp_path):
    # a file where a directory must go
    blocker = tmp_path / "blocked"
    blocker.write_text("x")
    rc = I.install(payload, str(blocker / "sub"), launch=False)
    assert rc in (0, 1)          # must not raise either way


def test_cleanup_payload_is_opt_in(payload, tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    target = str(tmp_path / "Programs" / "Scrinium")
    I.install(payload, target, launch=False, cleanup_payload=True)
    assert not os.path.exists(payload)


def test_reinstall_leaves_no_backup_behind(payload, tmp_path, monkeypatch):
    """Regression: the .old backup (9 MB) was never cleaned up, so repeated
    installs littered the install folder."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    target = str(tmp_path / "Programs" / "Scrinium")
    for _ in range(3):
        assert I.install(payload, target, launch=False, quiet=True) == 0
    assert os.listdir(target) == ["Scrinium.exe"], os.listdir(target)


def test_running_exes_returns_list():
    assert isinstance(I.running_exes(), list)


def test_install_cli_parses_and_reports_missing_payload(tmp_path, capsys):
    """--check on a folder without a payload must fail cleanly, not traceback."""
    empty = tmp_path / "empty"
    empty.mkdir()
    cwd = os.getcwd()
    try:
        os.chdir(empty)
        rc = I.main(["--dir", str(tmp_path / "target"), "--no-launch"])
    finally:
        os.chdir(cwd)
    assert rc == 1
    assert "payload" in capsys.readouterr().out.lower()