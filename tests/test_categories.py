"""Category registry integrity.

These guard the bugs found while building v2: duplicated extensions and
ambiguous extensions that were silently resolved by declaration order.
"""

from __future__ import annotations

import pytest

from scrinium import categories as C


def test_no_extension_claimed_by_two_categories():
    assert C.CONFLICTING_EXTS == {}


def test_no_duplicate_within_a_category():
    for cat in C.CATEGORIES:
        assert len(cat.extensions) == len(set(cat.extensions)), cat.key


def test_extensions_are_lowercase_and_clean():
    for ext in C.EXT_MAP:
        assert ext == ext.lower()
        assert not ext.startswith(".")
        assert ext.strip() == ext


def test_registry_has_enough_coverage():
    assert len(C.CATEGORIES) >= 17
    assert len(C.EXT_MAP) >= 300


@pytest.mark.parametrize("ext,key", [
    ("pdf", "doc"), ("jpg", "image"), ("png", "image"), ("mp4", "video"),
    ("mkv", "video"), ("mp3", "music"), ("flac", "music"), ("epub", "book"),
    ("zip", "archive"), ("7z", "archive"), ("iso", "disk"), ("exe", "app"),
    ("msi", "app"), ("py", "code"), ("json", "code"), ("ttf", "font"),
    ("psd", "design"), ("obj", "model3d"), ("apk", "app"), ("xlsx", "sheet"),
])
def test_common_extensions_map_correctly(ext, key):
    assert C.EXT_MAP[ext] == key


@pytest.mark.parametrize("ext,key", [
    # regression: .ts used to be video, which misfiled every TypeScript file
    ("ts", "code"),
    ("tsx", "code"),
    # regression: .3ds used to be claimed by two categories
    ("3ds", "model3d"),
    ("mts", "video"),      # AVCHD video really is .mts
])
def test_ambiguous_extensions_resolved_intentionally(ext, key):
    assert C.EXT_MAP[ext] == key


def test_every_category_has_metadata():
    for cat in C.CATEGORIES:
        assert cat.name_de and cat.name_en
        assert cat.folder_de and cat.folder_en
        assert cat.color.startswith("#") and len(cat.color) == 7
        assert cat.label("de") and cat.label("en")


def test_folder_names_ignore_language():
    """Regression: switching the UI language must never rename the folders
    on disk, otherwise every file lands in a second, empty tree."""
    for cat in C.CATEGORIES:
        assert C.folder_name(cat.key, "de") == C.folder_name(cat.key, "en")
        assert C.folder_name(cat.key, "en") == cat.folder_de


def test_labels_do_follow_language():
    assert C.label("doc", "de") == "Dokumente"
    assert C.label("doc", "en") == "Documents"


def test_default_keys_exclude_other():
    assert "other" not in C.DEFAULT_KEYS
    assert C.get("other") is not None