"""Undo journal and config migration."""

from __future__ import annotations

import os

import pytest

from scrinium import config as cfg_mod
from scrinium import engine, history, rules


# --- undo ------------------------------------------------------------------
@pytest.fixture
def journal(tmp_path):
    return history.History(str(tmp_path / "cfg"))


def _run(tmp_path, files, targets, resolver):
    for name, data in files.items():
        (tmp_path / name).write_bytes(data)
    plan = engine.plan(str(tmp_path), targets, resolver, min_age_s=0)
    result = engine.apply(plan)
    return plan, result


def test_undo_restores_files_and_content(tmp_path, journal, resolver):
    _, result = _run(tmp_path, {"a.pdf": b"A", "b.jpg": b"B"}, {
        "doc": str(tmp_path / "D"), "image": str(tmp_path / "I")}, resolver)
    entry = journal.record(engine.Plan(str(tmp_path)), result)
    assert entry.count == 2
    assert not (tmp_path / "a.pdf").exists()

    n, errors = journal.undo(entry.run_id)
    assert n == 2 and errors == []
    assert (tmp_path / "a.pdf").read_bytes() == b"A"
    assert (tmp_path / "b.jpg").read_bytes() == b"B"


def test_undo_reports_missing_destination(tmp_path, journal, resolver):
    _, result = _run(tmp_path, {"a.pdf": b"A"}, {"doc": str(tmp_path / "D")}, resolver)
    entry = journal.record(engine.Plan(str(tmp_path)), result)
    os.remove(tmp_path / "D" / "a.pdf")
    n, errors = journal.undo(entry.run_id)
    assert n == 0 and errors


def test_undo_marks_entry(tmp_path, journal, resolver):
    _, result = _run(tmp_path, {"a.pdf": b"A"}, {"doc": str(tmp_path / "D")}, resolver)
    entry = journal.record(engine.Plan(str(tmp_path)), result)
    journal.undo(entry.run_id)
    assert journal.get(entry.run_id).undone


def test_undo_removes_emptied_folder(tmp_path, journal, resolver):
    _, result = _run(tmp_path, {"a.pdf": b"A"}, {"doc": str(tmp_path / "D")}, resolver)
    entry = journal.record(engine.Plan(str(tmp_path)), result)
    assert (tmp_path / "D").is_dir()
    journal.undo(entry.run_id)
    assert not (tmp_path / "D").exists(), "empty category folder left behind"


def test_cleanup_keeps_folder_with_other_files(tmp_path, journal, resolver):
    """An undo must never delete a folder that still holds unrelated files."""
    _, result = _run(tmp_path, {"a.pdf": b"A"}, {"doc": str(tmp_path / "D")}, resolver)
    keep = tmp_path / "D" / "unrelated.txt"
    keep.write_bytes(b"keep me")
    entry = journal.record(engine.Plan(str(tmp_path)), result)
    journal.undo(entry.run_id)
    assert (tmp_path / "D").exists()
    assert keep.read_bytes() == b"keep me"


def test_cleanup_never_removes_the_source_folder(tmp_path, journal, resolver):
    p = tmp_path / "inplace"
    p.mkdir()
    (p / "a.pdf").write_bytes(b"A")
    plan = engine.plan(str(p), {"doc": str(p)}, resolver, min_age_s=0)
    # target == source, so nothing is planned; exercise the guard directly
    entry = journal.record(plan, engine.ApplyResult())
    journal._cleanup_empty_dirs(entry)
    assert p.exists()


def test_undo_unknown_run_is_safe(journal):
    n, errors = journal.undo("does-not-exist")
    assert n == 0 and errors


def test_history_survives_reload(tmp_path, resolver):
    cfg = str(tmp_path / "cfg")
    h = history.History(cfg)
    _, result = _run(tmp_path, {"a.pdf": b"A"}, {"doc": str(tmp_path / "D")}, resolver)
    h.record(engine.Plan(str(tmp_path)), result)
    again = history.History(cfg)
    assert len(again.entries) == 1
    assert again.entries[0].count == 1
    # the jsonl mirror exists too
    assert os.path.exists(os.path.join(cfg, "history.jsonl"))


def test_stats_reflect_runs(tmp_path, resolver):
    h = history.History(str(tmp_path / "cfg"))
    _, r1 = _run(tmp_path, {"a.pdf": b"A" * 10}, {"doc": str(tmp_path / "D1")}, resolver)
    h.record(engine.Plan(str(tmp_path)), r1)
    s = h.stats()
    assert s["runs"] == 1 and s["moves"] == 1 and s["bytes"] == 10


def test_clear_history(journal):
    journal.entries.clear()
    journal.save()
    journal.clear()
    assert journal.entries == []


# --- config migration ------------------------------------------------------
def test_v1_keys_are_migrated():
    c = cfg_mod.default_config()
    c.update({"iv": 1, "new": 0, "min": 5})
    c = cfg_mod._sanitize(cfg_mod._migrate_v1(c))
    assert c["interval_enabled"] is True
    assert c["watch_enabled"] is False
    assert c["interval_min"] == 5
    assert "iv" not in c and "new" not in c and "min" not in c


def test_v1_reverse_values():
    c = cfg_mod.default_config()
    c.update({"iv": 0, "new": 1, "min": 45})
    c = cfg_mod._sanitize(cfg_mod._migrate_v1(c))
    assert c["interval_enabled"] is False
    assert c["watch_enabled"] is True
    assert c["interval_min"] == 45


def test_v2_config_survives_migration():
    c = cfg_mod.default_config()
    c.update({"interval_enabled": False, "watch_enabled": True, "interval_min": 99})
    out = cfg_mod._sanitize(cfg_mod._migrate_v1(c))
    assert out["interval_enabled"] is False
    assert out["watch_enabled"] is True
    assert out["interval_min"] == 99


def test_garbage_legacy_values_do_not_crash():
    c = cfg_mod.default_config()
    c.update({"iv": "x", "new": None, "min": "abc"})
    out = cfg_mod._sanitize(cfg_mod._migrate_v1(c))
    assert out["interval_min"] == 30


def test_unknown_category_paths_dropped():
    c = cfg_mod.default_config()
    c["paths"] = {"bogus": "C:/x", "image": "C:/Temp/Bilder"}
    out = cfg_mod._sanitize(c)
    assert "bogus" not in out["paths"]
    assert out["paths"]["image"] == "C:/Temp/Bilder"


@pytest.mark.parametrize("bad,key,fallback", [
    ("abc", "interval_min", 30),
    (-5, "min_age_s", 0),
    (999999999, "interval_min", 10080),
])
def test_out_of_range_values_clamped(bad, key, fallback):
    out = cfg_mod._sanitize({key: bad})
    assert out[key] == fallback


def test_invalid_enums_fall_back():
    out = cfg_mod._sanitize({"appearance": "neon", "lang": "klingon",
                             "collide": "explode", "accent": "not-a-colour"})
    assert out["appearance"] == "dark"
    assert out["lang"] == "de"
    assert out["collide"] == "rename"
    assert out["accent"] == "#3B8ED0"


def test_target_dirs_fill_defaults(empty_dir):
    c = cfg_mod.default_config()
    c["dl"] = str(empty_dir)
    c["paths"] = {"image": "C:/Elsewhere"}
    t = cfg_mod.target_dirs(c, "de")
    assert t["image"] == "C:/Elsewhere"
    assert t["doc"] == os.path.join(str(empty_dir), "Dokumente")
    assert len(t) == 17


def test_target_dirs_honour_source_override(empty_dir, tmp_path):
    """Regression: `--source DIR` used to file into the *configured*
    Downloads folder instead of the folder actually being sorted."""
    c = cfg_mod.default_config()
    c["dl"] = str(empty_dir)
    other = tmp_path / "OtherDownloads"
    other.mkdir()
    t = cfg_mod.target_dirs(c, "de", source_dir=str(other))
    # compare normalised: os.path.join uses "\" on Windows, norm_path "/"
    assert t["doc"].replace("\\", "/") == f"{other}/Dokumente".replace("\\", "/")


def test_target_dirs_explicit_paths_beat_source_override(empty_dir, tmp_path):
    c = cfg_mod.default_config()
    c["dl"] = str(empty_dir)
    c["paths"] = {"doc": "C:/Chosen"}
    other = tmp_path / "OtherDownloads"
    other.mkdir()
    t = cfg_mod.target_dirs(c, "de", source_dir=str(other))
    assert t["doc"] == "C:/Chosen"