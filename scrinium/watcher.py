"""Background watcher.

Replaces v1's naive `listdir` poll. Two jobs, one thread:

*   **interval** - run every `interval_min` minutes
*   **watch**    - run as soon as new files appear *and* have settled

The settled-check is the important part: a file only becomes eligible once it
has not grown for `settle_s` seconds and is at least `min_age_s` old. That is
what stops Scrinium from moving a file that the browser is still writing.

Thread safety: the watcher only reads plain data (a snapshot dict swapped in by
the GUI thread) and never touches Tk. Results travel back over a `queue.Queue`
that the GUI drains on its own `_pump` tick.
"""

from __future__ import annotations

import os
import queue
import threading
import time
from dataclasses import dataclass, field

from . import engine
from .util import human_size

# job kinds pushed onto the queue
JOB_PLAN = "plan"
JOB_APPLY = "apply"
JOB_UNDO = "undo"
JOB_PROGRESS = "progress"
JOB_LOG = "log"
JOB_ERROR = "error"
JOB_SNAPSHOT = "snapshot"


@dataclass
class WatchState:
    """Plain data the watcher thread reads. Never contains Tk objects."""

    dl: str = ""
    targets: dict = field(default_factory=dict)
    resolver: object = None
    interval_min: int = 30
    watch_enabled: bool = True
    interval_enabled: bool = True
    min_age_s: float = 30.0
    settle_s: float = 8.0
    collide: str = "rename"
    recursive: bool = False
    lang: str = "de"
    auto_apply: bool = True
    enabled: bool = True


@dataclass
class Snapshot:
    """Observed state of the download folder."""

    names: set = field(default_factory=set)
    sizes: dict = field(default_factory=dict)      # name -> (size, mtime)
    seen_at: float = 0.0

    def take(self, folder: str) -> "Snapshot":
        snap = Snapshot(seen_at=time.time())
        try:
            with os.scandir(folder) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            st = entry.stat(follow_symlinks=False)
                            snap.names.add(entry.name)
                            snap.sizes[entry.name] = (st.st_size, st.st_mtime)
                    except OSError:
                        continue
        except OSError:
            pass
        return snap


class Watcher:
    """One daemon thread. `snapshot()` swaps settings in from the GUI thread."""

    def __init__(self, out_queue: queue.Queue, state: WatchState | None = None):
        self.q = out_queue
        self._state = state or WatchState()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._prev = Snapshot()
        self._handled: set[str] = set()   # names already filed or dismissed
        self._busy_until = 0.0
        self._thread: threading.Thread | None = None
        self._running_run = False
        self._cancel = False

    # ---- lifecycle --------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="scrinium-watcher", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def snapshot(self, **changes) -> WatchState:
        """Replace settings (called from the GUI thread)."""
        with self._lock:
            for k, v in changes.items():
                if hasattr(self._state, k):
                    setattr(self._state, k, v)
            return self._state

    def poke(self) -> None:
        """Ask the loop to re-evaluate right now."""
        self._wake.set()

    def cancel_current(self) -> None:
        self._cancel = True

    def request_sort(self, trigger: str = "manual", auto: bool = False) -> None:
        self.q.put((JOB_APPLY, {"trigger": trigger, "auto": auto}))

    # ---- helpers ----------------------------------------------------------
    def _is_settled(self, state: WatchState, snap: Snapshot, now_ts: float) -> bool:
        """True when nothing on disk has changed for `settle_s` seconds.

        This is the guard that stops Scrinium from moving a file the browser
        is still writing. It deliberately looks at the *fresh* snapshot: a file
        that was just created (or just grew) has a recent mtime and must not
        count as settled yet.
        """
        for name, (_size, mtime) in snap.sizes.items():
            if now_ts - mtime < state.settle_s:
                return False
        return True

    def _new_files(self, state: WatchState, snap: Snapshot) -> set:
        return snap.names - self._prev.names

    def _pending(self, snap: Snapshot) -> set:
        """Files we have not filed yet.

        Deliberately *not* a "new since last look" check: if Scrinium starts
        while a download is already in flight, that file is in the very first
        snapshot and would never look new again. Pending = "seen but never
        handled", which also covers app restarts.
        """
        return snap.names - self._handled

    def _changed(self, snap: Snapshot) -> bool:
        """Did anything appear, disappear or change size since last look?"""
        if snap.names != self._prev.names:
            return True
        for name, size_info in snap.sizes.items():
            old = self._prev.sizes.get(name)
            if old is None or old[0] != size_info[0]:
                return True
        return False

    # ---- main loop --------------------------------------------------------
    def _run(self) -> None:
        last_change = time.time()
        last_interval = time.time()
        while not self._stop.is_set():
            with self._lock:
                state = WatchState(**vars(self._state))
            folder = state.dl
            if not state.enabled or not folder or not os.path.isdir(folder):
                self._wake.wait(2.0)
                self._wake.clear()
                continue

            now_ts = time.time()
            snap = Snapshot().take(folder)

            try:
                if self._changed(snap):
                    last_change = now_ts

                quiet_for = now_ts - last_change

                if state.watch_enabled and not self._running_run:
                    pending = self._pending(snap)
                    if pending and self._is_settled(state, snap, now_ts):
                        self._do_run(state, trigger="newfile", auto=True)

                if state.interval_enabled and not self._running_run:
                    if now_ts - last_interval >= state.interval_min * 60:
                        last_interval = now_ts
                        self._do_run(state, trigger="interval", auto=True)
            except Exception as exc:                     # never kill the thread
                self.q.put((JOB_ERROR, {"error": str(exc)}))

            self._prev = snap

            # Fast while things change, idle-friendly when nothing happens.
            if not state.watch_enabled:
                nap = 15.0
            elif quiet_for < state.settle_s:
                nap = 1.0
            else:
                nap = 3.0
            self._wake.wait(nap)
            self._wake.clear()

    # ---- one sort run -----------------------------------------------------
    def _do_run(self, state: WatchState, trigger: str, auto: bool) -> None:
        """Runs on the watcher thread: plan, then apply when allowed."""
        if self._running_run:
            return
        self._running_run = True
        self._cancel = False
        try:
            plan = engine.plan(
                state.dl,
                state.targets,
                state.resolver,
                min_age_s=state.min_age_s,
                collide=state.collide,
                lang=state.lang,
                recursive=state.recursive,
                cancel=lambda: self._cancel,
            )
            if not plan.moves:
                self.q.put((JOB_LOG, {
                    "msg": {"de": "Nichts zu sortieren.",
                            "en": "Nothing to sort."}[state.lang],
                    "level": "info",
                }))
                return

            self.q.put((JOB_PLAN, {
                "plan": plan, "trigger": trigger, "auto": auto,
                "total": len(plan.moves), "bytes": plan.total_bytes_h,
            }))

            # A preview-only request stops here: the GUI decides. Nothing is
            # marked handled yet, so a later run can pick the files up.
            if auto and not state.auto_apply:
                return

            result = engine.apply(
                plan,
                cancel=lambda: self._cancel,
                progress=lambda i, n: self.q.put(
                    (JOB_PROGRESS, {"phase": "apply", "done": i, "total": n})
                ),
            )
            # Remember what is now filed, so the watcher does not keep retrying.
            # Failures stay unhandled and are retried on the next pass.
            for item in result.moved:
                self._handled.add(item.name)
            self.q.put((JOB_APPLY, {
                "plan": plan, "result": result, "trigger": trigger,
            }))
        finally:
            self._running_run = False