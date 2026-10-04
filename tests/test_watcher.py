"""Watcher: the settle guard is the safety-critical behaviour."""

from __future__ import annotations

import os
import queue
import time

import pytest

from scrinium import categories as C
from scrinium import watcher as W


def _drain(q):
    out = []
    while True:
        try:
            out.append(q.get_nowait())
        except queue.Empty:
            return out


@pytest.fixture
def watch_cfg(tmp_path):
    q = queue.Queue()
    d = tmp_path / "Downloads"
    d.mkdir(exist_ok=True)
    state = W.WatchState(
        dl=str(d),
        targets={k: str(d / C.folder_name(k, "de")) for k in C.DEFAULT_KEYS},
        resolver=None,
        watch_enabled=True,
        interval_enabled=False,
        min_age_s=0.0,
        settle_s=1.0,
        auto_apply=True,
        lang="en",
    )
    return q, d, state


# --- settle detection ------------------------------------------------------
def test_new_file_is_not_settled_immediately(watch_cfg):
    q, d, state = watch_cfg
    (d / "a.pdf").write_bytes(b"x")
    snap = W.Snapshot().take(str(d))
    assert not W.Watcher(q, state)._is_settled(state, snap, time.time())


def test_file_is_settled_after_quiet_period(watch_cfg):
    q, d, state = watch_cfg
    (d / "a.pdf").write_bytes(b"x")
    time.sleep(state.settle_s + 0.4)
    snap = W.Snapshot().take(str(d))
    assert W.Watcher(q, state)._is_settled(state, snap, time.time())


def test_growing_file_is_never_settled(watch_cfg):
    q, d, state = watch_cfg
    w = W.Watcher(q, state)
    (d / "big.bin").write_bytes(b"x" * 100)
    results = []
    for _ in range(5):
        with open(d / "big.bin", "ab") as fh:
            fh.write(b"y" * 5000)
            fh.flush()
            os.fsync(fh.fileno())
        time.sleep(0.2)
        results.append(w._is_settled(state, W.Snapshot().take(str(d)), time.time()))
    assert not any(results)


# --- pending vs new --------------------------------------------------------
def test_pending_includes_files_seen_at_startup(watch_cfg):
    """Regression: a download already running when Scrinium starts used to
    never look 'new' again and was therefore never filed."""
    q, d, state = watch_cfg
    (d / "movie.mp4").write_bytes(b"x")          # exists before the watcher starts
    w = W.Watcher(q, state)
    snap = W.Snapshot().take(str(d))
    assert w._pending(snap) == {"movie.mp4"}


def test_pending_excludes_handled(watch_cfg):
    q, d, state = watch_cfg
    (d / "a.pdf").write_bytes(b"x")
    w = W.Watcher(q, state)
    snap = W.Snapshot().take(str(d))
    w._handled.add("a.pdf")
    assert w._pending(snap) == set()


def test_changed_detects_new_removed_and_resized(watch_cfg):
    q, d, state = watch_cfg
    w = W.Watcher(q, state)
    (d / "a.pdf").write_bytes(b"x")
    w._prev = W.Snapshot().take(str(d))
    assert not w._changed(W.Snapshot().take(str(d)))
    (d / "b.pdf").write_bytes(b"x")
    assert w._changed(W.Snapshot().take(str(d)))
    w._prev = W.Snapshot().take(str(d))
    with open(d / "a.pdf", "ab") as fh:
        fh.write(b"more")
    assert w._changed(W.Snapshot().take(str(d)))


# --- live behaviour --------------------------------------------------------
def test_inflight_download_is_never_moved_early(watch_cfg):
    q, d, state = watch_cfg
    from scrinium import rules

    state.resolver = rules.Resolver()
    w = W.Watcher(q, state)
    big = d / "movie.mp4"
    big.write_bytes(b"x" * 100)
    w.start()
    try:
        for _ in range(6):
            with open(big, "ab") as fh:
                fh.write(b"y" * 20000)
                fh.flush()
                os.fsync(fh.fileno())
            time.sleep(0.7)
            assert not (d / "Videos" / "movie.mp4").exists(), "moved while writing!"
    finally:
        w.stop()


def test_inflight_download_is_filed_once_quiet(watch_cfg):
    q, d, state = watch_cfg
    from scrinium import rules

    state.resolver = rules.Resolver()
    w = W.Watcher(q, state)
    big = d / "movie.mp4"
    big.write_bytes(b"x" * 100)
    w.start()
    try:
        for _ in range(4):
            with open(big, "ab") as fh:
                fh.write(b"y" * 20000)
                fh.flush()
                os.fsync(fh.fileno())
            time.sleep(0.7)
        deadline = time.time() + 20
        while time.time() < deadline and not (d / "Videos" / "movie.mp4").exists():
            time.sleep(0.5)
    finally:
        w.stop()
    assert (d / "Videos" / "movie.mp4").exists()
    assert not big.exists()


def test_multiple_files_filed_without_restart(watch_cfg):
    q, d, state = watch_cfg
    from scrinium import rules

    state.resolver = rules.Resolver()
    w = W.Watcher(q, state)
    w.start()
    try:
        for name, folder in (("doc.pdf", "Dokumente"), ("pic.jpg", "Bilder")):
            (d / name).write_bytes(b"z" * 500)
            deadline = time.time() + 20
            while time.time() < deadline and not (d / folder / name).exists():
                time.sleep(0.5)
            assert (d / folder / name).exists(), f"{name} never filed"
    finally:
        w.stop()


def test_idle_watcher_does_not_spin(watch_cfg):
    q, d, state = watch_cfg
    from scrinium import rules

    state.resolver = rules.Resolver()
    (d / "Dokumente").mkdir()
    (d / "Dokumente" / "old.pdf").write_bytes(b"x")
    w = W.Watcher(q, state)
    w.start()
    time.sleep(4)
    w.stop()
    assert _drain(q) == []


def test_stop_is_clean(watch_cfg):
    q, d, state = watch_cfg
    w = W.Watcher(q, state)
    w.start()
    w.stop()
    assert not (w._thread and w._thread.is_alive())


def test_snapshot_replaces_state(watch_cfg):
    q, d, state = watch_cfg
    w = W.Watcher(q, state)
    w.snapshot(min_age_s=99, watch_enabled=False)
    assert w._state.min_age_s == 99
    assert w._state.watch_enabled is False


def test_disabled_watcher_does_nothing(watch_cfg):
    q, d, state = watch_cfg
    from scrinium import rules

    state.resolver = rules.Resolver()
    state.enabled = False
    (d / "a.pdf").write_bytes(b"x")
    w = W.Watcher(q, state)
    w.start()
    time.sleep(3)
    w.stop()
    assert _drain(q) == []