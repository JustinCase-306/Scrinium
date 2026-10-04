"""CLI end-to-end via subprocess, plus i18n and util helpers."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import pytest

from scrinium import i18n, util

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SANDBOX = None


@pytest.fixture(autouse=True)
def isolated_config(tmp_path_factory):
    """Point the CLI's %APPDATA% at a throwaway dir.

    run_cli() copies os.environ per call, so the override has to live in the
    real process environment - monkeypatch.setenv would not reach the
    subprocess. Without this the tests read and write the *real* user config,
    which leaks state between runs.
    """
    global _SANDBOX
    sandbox = tmp_path_factory.mktemp("appdata") / "Roaming"
    sandbox.mkdir(parents=True, exist_ok=True)
    _SANDBOX = str(sandbox)
    return _SANDBOX


def run_cli(*args, cwd=None):
    env = dict(os.environ, PYTHONPATH=REPO)
    if _SANDBOX:
        env["APPDATA"] = _SANDBOX
    return subprocess.run(
        [sys.executable, "-m", "scrinium", *args],
        capture_output=True, text=True, cwd=cwd or REPO, env=env, timeout=120,
    )


@pytest.fixture
def dl(tmp_path):
    d = tmp_path / "Downloads"
    d.mkdir()
    for name in ("a.pdf", "b.jpg", "c.mp4", "d.crdownload"):
        (d / name).write_bytes(b"x" * 100)
    return d


def file_exists(path) -> bool:
    """os.path.exists on an abspath-resolved path.

    tmp_path under %TEMP% resolves to a short 8.3 name (FRIEDR~1) inside the
    CLI subprocess, while pytest keeps the long name - both hit the same file,
    but Path.exists() can miss if the two spellings disagree. Resolving both
    sides makes the comparison reliable.
    """
    return os.path.exists(os.path.abspath(str(path)))


# --- basic -----------------------------------------------------------------
def test_version():
    r = run_cli("--version")
    assert r.returncode == 0 and "Scrinium" in r.stdout


def test_help_lists_flags():
    r = run_cli("--help")
    assert r.returncode == 0
    for flag in ("--dry-run", "--once", "--json", "--undo", "--stats"):
        assert flag in r.stdout


def test_missing_source_returns_2():
    r = run_cli("--source", "C:/definitely/not/here", "--once")
    assert r.returncode == 2


def test_unknown_category_returns_2(dl):
    r = run_cli("--source", str(dl), "--category", "bogus")
    assert r.returncode == 2


# --- dry run ---------------------------------------------------------------
def test_dry_run_moves_nothing(dl):
    r = run_cli("--source", str(dl), "--dry-run", "--min-age", "0", "--lang", "en")
    assert r.returncode == 0
    assert "a.pdf" in r.stdout
    assert file_exists(dl / "a.pdf")
    assert not file_exists(dl / "Dokumente")


def test_dry_run_json(dl):
    r = run_cli("--source", str(dl), "--dry-run", "--json", "--min-age", "0")
    data = json.loads(r.stdout)
    assert isinstance(data["moves"], list)
    assert {m["name"] for m in data["moves"]} == {"a.pdf", "b.jpg", "c.mp4"}


# --- real run + undo -------------------------------------------------------
def test_source_flag_targets_the_given_folder(dl):
    """Regression: --source DIR must file into DIR, not the configured
    Downloads folder."""
    r = run_cli("--source", str(dl), "--min-age", "0", "--lang", "en")
    assert r.returncode == 0, r.stderr
    assert file_exists(dl / "Dokumente" / "a.pdf")
    assert file_exists(dl / "Bilder" / "b.jpg")
    assert not file_exists(dl / "Dokumente" / "a_01.pdf"), "unexpected rename"


def test_once_moves_files_and_prints_run_id(dl):
    r = run_cli("--source", str(dl), "--min-age", "0", "--lang", "en")
    assert r.returncode == 0, r.stderr
    assert file_exists(dl / "Dokumente" / "a.pdf")
    assert file_exists(dl / "Bilder" / "b.jpg")
    assert file_exists(dl / "Videos" / "c.mp4")
    assert file_exists(dl / "d.crdownload"), "incomplete download must stay"
    assert re.search(r"run_id:\s*(\S+)", r.stdout)


def test_undo_round_trip(dl):
    r = run_cli("--source", str(dl), "--min-age", "0", "--lang", "en")
    run_id = re.search(r"run_id:\s*(\S+)", r.stdout).group(1)
    u = run_cli("--undo", run_id)
    assert u.returncode == 0, u.stderr
    assert file_exists(dl / "a.pdf")
    assert file_exists(dl / "b.jpg")
    assert file_exists(dl / "c.mp4")
    with open(dl / "a.pdf", "rb") as fh:
        assert fh.read() == b"x" * 100


def test_undo_unknown_run_returns_1():
    r = run_cli("--undo", "no-such-run")
    assert r.returncode == 1


def test_once_json_output(dl):
    r = run_cli("--source", str(dl), "--min-age", "0", "--json")
    data = json.loads(r.stdout)
    assert data["moved"] == 3
    assert data["bytes"] == 300
    assert data["failed"] == []
    assert data["skipped"] == 1


# --- filtering / language --------------------------------------------------
def test_category_filter(dl):
    """`--category` restricts this run to one category.

    Uses --json: the human-readable dry-run also lists *skipped* files, so
    "a.pdf" would appear there even though it was not moved.
    """
    r = run_cli("--source", str(dl), "--category", "video",
                "--dry-run", "--json", "--min-age", "0", "--lang", "en")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert [m["name"] for m in data["moves"]] == ["c.mp4"]


def test_category_filter_does_not_persist(dl):
    """A one-off --category must not permanently disable other categories."""
    run_cli("--source", str(dl), "--category", "video", "--dry-run", "--min-age", "0")
    r = run_cli("--source", str(dl), "--dry-run", "--json", "--min-age", "0")
    data = json.loads(r.stdout)
    assert {m["name"] for m in data["moves"]} == {"a.pdf", "b.jpg", "c.mp4"}


def test_german_output(dl):
    r = run_cli("--source", str(dl), "--dry-run", "--min-age", "0", "--lang", "de")
    assert r.returncode == 0
    assert "Dokumente" in r.stdout or "Datei" in r.stdout


# --- reports ---------------------------------------------------------------
def test_stats_runs(dl):
    run_cli("--source", str(dl), "--min-age", "0")
    r = run_cli("--stats")
    assert r.returncode == 0 and "Scrinium" in r.stdout


def test_history_shows_run(dl):
    r0 = run_cli("--source", str(dl), "--min-age", "0")
    run_id = re.search(r"run_id:\s*(\S+)", r0.stdout).group(1)
    r = run_cli("--history")
    assert r.returncode == 0
    assert run_id in r.stdout


# --- i18n ------------------------------------------------------------------
def test_language_tables_have_same_keys():
    de, en = set(i18n.STRINGS["de"]), set(i18n.STRINGS["en"])
    assert de == en
    assert len(de) > 80


def test_translator_interpolates():
    t = i18n.T("en")
    assert t("status_done", count=3, size="1 MB") == "✓ Filed 3 file(s) (1 MB)"


def test_translator_falls_back_to_key():
    assert i18n.T("en")("no_such_key") == "no_such_key"


def test_translator_survives_bad_format_args():
    assert i18n.T("en")("status_done") == "✓ Filed {count} file(s) ({size})"


def test_set_lang_switches_global():
    i18n.set_lang("en")
    assert i18n.get_lang() == "en"
    i18n.set_lang("de")
    assert i18n.get_lang() == "de"


# --- util ------------------------------------------------------------------
@pytest.mark.parametrize("size,expected", [
    (0, "0 B"), (512, "512 B"), (1024, "1.0 KB"), (1536, "1.5 KB"),
    (1024 ** 2, "1.0 MB"), (1024 ** 3, "1.0 GB"), (1024 ** 4, "1.0 TB"),
])
def test_human_size(size, expected):
    assert util.human_size(size) == expected


def test_human_size_bad_input():
    assert util.human_size("nope") == "?"


def test_atomic_write_replaces(tmp_path):
    target = tmp_path / "x.json"
    util.atomic_write(str(target), '{"a": 1}')
    util.atomic_write(str(target), '{"a": 2}')
    assert target.read_text(encoding="utf-8") == '{"a": 2}'
    assert not list(tmp_path.glob(".tmp_*"))


def test_is_inside_and_same_path(tmp_path):
    child = tmp_path / "a" / "b"
    child.mkdir(parents=True)
    assert util.is_inside(str(child), str(tmp_path))
    assert util.is_inside(str(tmp_path), str(tmp_path))
    assert not util.is_inside(str(tmp_path), str(child))
    assert util.same_path(str(child), str(child))


def test_norm_path_strips_trailing_slash():
    assert util.norm_path("C:/Users/x/") == "C:/Users/x"
    assert util.norm_path("C:\\Users\\x") == "C:/Users/x"
    assert util.norm_path("") == ""