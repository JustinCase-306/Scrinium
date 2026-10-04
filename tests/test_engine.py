"""Engine: dry-run purity, collisions, idempotency, apply/undo."""

from __future__ import annotations

import os

import pytest

from scrinium import categories as C
from scrinium import engine, rules


def _tree(root):
    return sorted(
        os.path.relpath(os.path.join(rt, f), root).replace("\\", "/")
        for rt, _dirs, files in os.walk(root) for f in files
    )


# --- dry run ---------------------------------------------------------------
def test_plan_does_not_touch_the_filesystem(empty_dir, targets, make_file, resolver):
    make_file("a.pdf")
    make_file("b.jpg")
    before = _tree(empty_dir)
    engine.plan(str(empty_dir), targets, resolver, min_age_s=0)
    assert _tree(empty_dir) == before


def test_plan_reports_moves_without_creating_dirs(empty_dir, targets, make_file, resolver):
    make_file("a.pdf")
    plan = engine.plan(str(empty_dir), targets, resolver, min_age_s=0)
    assert len(plan.moves) == 1
    assert not (empty_dir / "Dokumente").exists()
    assert str(empty_dir / "Dokumente") in plan.created_dirs


def test_plan_skips_incomplete_downloads(empty_dir, targets, make_file, resolver):
    make_file("a.pdf")
    make_file("big.mp4.crdownload")
    plan = engine.plan(str(empty_dir), targets, resolver, min_age_s=0)
    assert [m.name for m in plan.moves] == ["a.pdf"]
    assert any("crdownload" in s.name for s in plan.skipped)


def test_plan_respects_min_age(empty_dir, targets, make_file, resolver):
    make_file("new.pdf", age_s=0)
    make_file("old.pdf", age_s=300)
    plan = engine.plan(str(empty_dir), targets, resolver, min_age_s=60)
    assert [m.name for m in plan.moves] == ["old.pdf"]
    assert any("neu" in s.reason for s in plan.skipped)


def test_plan_totals_and_summary(empty_dir, targets, make_file, resolver):
    make_file("a.pdf", size=2048)
    make_file("b.jpg", size=1024)
    plan = engine.plan(str(empty_dir), targets, resolver, min_age_s=0)
    assert plan.total_bytes == 3072
    assert "3.0 KB" in plan.total_bytes_h or "KB" in plan.total_bytes_h
    assert len(plan.moves) == 2
    keys = {k for k, _c, _b in plan.count_by_category}
    assert keys == {"doc", "image"}


def test_missing_source_directory_reports_error(tmp_path, resolver):
    plan = engine.plan(str(tmp_path / "nope"), {}, resolver)
    assert plan.errors
    assert plan.moves == []


# --- recursion -------------------------------------------------------------
def test_recursive_plan_includes_nested_files(empty_dir, targets, resolver):
    sub = empty_dir / "sub" / "deep"
    sub.mkdir(parents=True)
    (sub / "low.mp3").write_bytes(b"x")
    (empty_dir / "top.pdf").write_bytes(b"x")
    plan = engine.plan(str(empty_dir), targets, resolver, min_age_s=0, recursive=True)
    assert len(plan.moves) == 2


def test_non_recursive_ignores_subfolders(empty_dir, targets, resolver):
    sub = empty_dir / "sub"
    sub.mkdir()
    (sub / "low.mp3").write_bytes(b"x")
    plan = engine.plan(str(empty_dir), targets, resolver, min_age_s=0)
    assert plan.moves == []


# --- collisions ------------------------------------------------------------
def test_collision_renames_and_preserves_both(empty_dir, targets, make_file, resolver):
    docs = empty_dir / "Dokumente"
    docs.mkdir()
    (docs / "rep.pdf").write_bytes(b"OLD")
    make_file("rep.pdf", size=10)
    engine.apply(engine.plan(str(empty_dir), targets, resolver, min_age_s=0))
    assert (docs / "rep.pdf").read_bytes() == b"OLD"
    assert (docs / "rep_01.pdf").read_bytes() == b"x" * 10


def test_two_same_named_files_in_one_run_do_not_clobber(empty_dir, resolver):
    for sub in ("a", "b"):
        (empty_dir / sub).mkdir()
        (empty_dir / sub / "x.pdf").write_bytes(sub.encode())
    plan = engine.plan(
        str(empty_dir), {"doc": str(empty_dir / "Dokumente")},
        resolver, min_age_s=0, recursive=True,
    )
    engine.apply(plan)
    docs = empty_dir / "Dokumente"
    assert sorted(os.listdir(docs)) == ["x.pdf", "x_01.pdf"]
    assert (docs / "x.pdf").read_bytes() == b"a"
    assert (docs / "x_01.pdf").read_bytes() == b"b"


def test_skip_policy_leaves_source_alone(empty_dir, make_file, resolver):
    docs = empty_dir / "Dokumente"
    docs.mkdir()
    (docs / "rep.pdf").write_bytes(b"OLD")
    make_file("rep.pdf")
    plan = engine.plan(str(empty_dir), {"doc": str(docs)}, resolver,
                       min_age_s=0, collide=engine.COLLIDE_SKIP)
    assert plan.moves == []
    assert any(s.name == "rep.pdf" for s in plan.skipped)
    assert (empty_dir / "rep.pdf").exists()


def test_resolve_collision_generates_sequence(tmp_path):
    first = str(tmp_path / "a.txt")
    assert engine.resolve_collision(first, engine.COLLIDE_RENAME) == (first, False)
    (tmp_path / "a.txt").write_bytes(b"")
    second, renamed = engine.resolve_collision(first, engine.COLLIDE_RENAME)
    assert renamed and second.endswith("a_01.txt")


# --- apply -----------------------------------------------------------------
def test_apply_moves_and_creates_dirs(empty_dir, targets, make_file, resolver):
    make_file("a.pdf")
    result = engine.apply(engine.plan(str(empty_dir), targets, resolver, min_age_s=0))
    assert len(result.moved) == 1
    assert not result.failed
    assert (empty_dir / "Dokumente" / "a.pdf").exists()
    assert not (empty_dir / "a.pdf").exists()


def test_apply_reports_cancel(empty_dir, targets, make_file, resolver):
    for n in ("a.pdf", "b.pdf", "c.pdf"):
        make_file(n)
    plan = engine.plan(str(empty_dir), targets, resolver, min_age_s=0)
    result = engine.apply(plan, cancel=lambda: True)
    assert result.cancelled
    assert result.moved == []


def test_progress_callback_reaches_total(empty_dir, targets, make_file, resolver):
    make_file("a.pdf")
    seen = []
    engine.apply(engine.plan(str(empty_dir), targets, resolver, min_age_s=0),
                 progress=lambda i, n: seen.append((i, n)))
    assert seen[-1][0] == seen[-1][1]


# --- idempotency -----------------------------------------------------------
def test_second_pass_finds_nothing(empty_dir, targets, make_file, resolver):
    make_file("a.pdf")
    make_file("b.jpg")
    engine.apply(engine.plan(str(empty_dir), targets, resolver, min_age_s=0))
    second = engine.plan(str(empty_dir), targets, resolver, min_age_s=0, recursive=True)
    assert second.moves == []


def test_target_folders_are_not_resorted_recursively(empty_dir, targets, make_file, resolver):
    make_file("a.pdf")
    engine.apply(engine.plan(str(empty_dir), targets, resolver, min_age_s=0))
    again = engine.plan(str(empty_dir), targets, resolver, min_age_s=0, recursive=True)
    assert [m.name for m in again.moves] == []