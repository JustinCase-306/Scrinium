"""Rule resolution and download-completeness detection.

The stability checks are the safety-critical part: Scrinium must never move a
file a browser is still writing.
"""

from __future__ import annotations

import time

import pytest

from scrinium import rules as R


# --- temporary / incomplete downloads --------------------------------------
@pytest.mark.parametrize("name", [
    "video.mp4.crdownload",           # Chrome
    "video.mp4.part",                 # Firefox
    "file.partial",
    "temp.tmp",
    "thing.temp",
    "x.download",
    "y.opdownload",                   # Opera
    ".~lock.doc.pdf#",                # LibreOffice
    "~$budget.xlsx",                  # Office lock file
    ".com.google.Chrome.abcd1234",    # Chrome temp dir file
])
def test_temporary_files_detected(name):
    assert R.looks_temporary(name) or R.looks_locked(name)


@pytest.mark.parametrize("name", [
    "report.pdf", "holiday.jpg", "a.mp4", "archive.7z", "song.flac",
    "notes.md", "backup.2024.pdf", "my.tmp.file.pdf",
])
def test_real_files_not_flagged(name):
    assert not R.looks_temporary(name)


def test_extensionless_hash_name_is_temporary():
    assert R.looks_temporary("d41d8cd98f00b204e9800998ecf8427e")


@pytest.mark.parametrize("name", [
    "Desktop.ini", "desktop.ini", "Thumbs.db", "thumbs.db",
    "game.lnk", "site.url", "system.dll", "notes.dat",
])
def test_protected_files(name):
    assert R.is_protected(name)


@pytest.mark.parametrize("name", ["report.pdf", "a.jpg", "b.docx", "Thumbs2.db"])
def test_normal_files_not_protected(name):
    assert not R.is_protected(name)


# --- stability -------------------------------------------------------------
def test_file_must_reach_min_age(make_file):
    fresh = make_file("new.pdf", age_s=0)
    ok, why = R.is_stable(str(fresh), time.time(), 30)
    assert not ok
    assert "neu" in why


def test_old_enough_file_is_stable(make_file):
    old = make_file("old.pdf", age_s=120)
    ok, _ = R.is_stable(str(old), time.time(), 30)
    assert ok


def test_zero_min_age_accepts_anything_but_temp(make_file):
    p = make_file("brandnew.pdf", age_s=0)
    assert R.is_stable(str(p), time.time(), 0)[0]


def test_temp_file_never_stable_even_with_zero_age(make_file):
    p = make_file("mid.mp4.part", age_s=600)
    ok, why = R.is_stable(str(p), time.time(), 0)
    assert not ok
    assert "unvollständig" in why


# --- classification --------------------------------------------------------
@pytest.mark.parametrize("name,key", [
    ("report.pdf", "doc"),
    ("photo.jpg", "image"),
    ("clip.mp4", "video"),
    ("track.mp3", "music"),
    ("archive.zip", "archive"),
    ("setup.exe", "app"),
    ("script.py", "code"),
])
def test_builtin_extension_mapping(resolver, name, key):
    assert resolver.classify(name).category == key


def test_unknown_extension_has_no_category(resolver):
    c = resolver.classify("mystery.qqq")
    assert c.category is None
    assert not c.skip


def test_screenshot_name_hint(resolver):
    # no useful extension, but the name gives it away
    c = resolver.classify("Screenshot 2026-01-01 at 12.00.00")
    assert c.category == "image"


def test_custom_extension_rule(resolver):
    r = R.Resolver.from_config({"custom_ext": [{"ext": "qqq", "to": "doc"}]})
    assert r.classify("weird.qqq").category == "doc"


def test_pattern_rule_wins_over_extension():
    r = R.Resolver.from_config({"rules": [
        {"kind": "pattern", "value": "invoice_*", "target": "doc"},
    ]})
    assert r.classify("invoice_2026.pdf").category == "doc"
    # a non-matching name still uses the built-in table
    assert r.classify("holiday.jpg").category == "image"


def test_skip_rule_marks_as_skip():
    r = R.Resolver.from_config({"rules": [
        {"kind": "pattern", "value": "*secret*", "target": "!skip"},
    ]})
    c = r.classify("my_secret.pdf")
    assert c.skip and c.category is None


def test_disabled_category_is_skipped():
    r = R.Resolver.from_config({"disabled_categories": ["image"]})
    c = r.classify("photo.jpg")
    assert c.category is None


def test_protected_file_short_circuits(resolver):
    assert resolver.classify("Desktop.ini").skip