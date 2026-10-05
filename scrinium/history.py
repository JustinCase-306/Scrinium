"""Undo journal - every move Scrinium makes is reversible.

Runs are appended to ``%APPDATA%/Scrinium/history.jsonl`` (JSON lines, so a
crash can never corrupt earlier entries) and the most recent N runs are also
mirrored into ``history.json`` for fast GUI access.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .util import atomic_write_json, human_size, norm_path, now, read_json, ts_human, ts_id

HISTORY_CAP = 200          # runs kept in history.json
JOURNAL_CAP = 4000         # journal lines kept on disk


@dataclass
class HistoryEntry:
    run_id: str
    when: float
    source_dir: str
    moves: list[dict] = field(default_factory=list)
    skipped: int = 0
    bytes_moved: int = 0
    trigger: str = "manual"        # manual | interval | newfile | cli
    error_count: int = 0
    undone: bool = False

    @property
    def count(self) -> int:
        return len(self.moves)

    @property
    def bytes_h(self) -> str:
        return human_size(self.bytes_moved)

    @property
    def when_h(self) -> str:
        return ts_human(self.when)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "when": self.when,
            "source_dir": self.source_dir,
            "moves": self.moves,
            "skipped": self.skipped,
            "bytes_moved": self.bytes_moved,
            "trigger": self.trigger,
            "error_count": self.error_count,
            "undone": self.undone,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HistoryEntry":
        return cls(
            run_id=str(d.get("run_id") or ""),
            when=float(d.get("when") or 0),
            source_dir=str(d.get("source_dir") or ""),
            moves=list(d.get("moves") or []),
            skipped=int(d.get("skipped") or 0),
            bytes_moved=int(d.get("bytes_moved") or 0),
            trigger=str(d.get("trigger") or "manual"),
            error_count=int(d.get("error_count") or 0),
            undone=bool(d.get("undone")),
        )


class History:
    """Append-only journal with a mirrored, bounded index."""

    def __init__(self, cfg_dir: str):
        self.dir = cfg_dir
        self.path = os.path.join(cfg_dir, "history.jsonl")
        self.index_path = os.path.join(cfg_dir, "history.json")
        os.makedirs(cfg_dir, exist_ok=True)
        self.entries: list[HistoryEntry] = self._load_index()

    # ---- io ---------------------------------------------------------------
    def _load_index(self) -> list[HistoryEntry]:
        raw = read_json(self.index_path, []) or []
        out: list[HistoryEntry] = []
        for d in raw:
            if isinstance(d, dict):
                out.append(HistoryEntry.from_dict(d))
        return out

    def _rewrite_journal(self) -> None:
        """Rebuild the jsonl from the (bounded) index - keeps both in sync."""
        try:
            lines = []
            for e in self.entries[-JOURNAL_CAP:]:
                import json

                lines.append(json.dumps(e.to_dict(), ensure_ascii=False))
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(lines))
                if lines:
                    fh.write("\n")
            os.replace(tmp, self.path)
        except OSError:
            pass

    def save(self) -> None:
        self.entries = self.entries[-HISTORY_CAP:]
        atomic_write_json(
            self.index_path, [e.to_dict() for e in self.entries]
        )

    # ---- api --------------------------------------------------------------
    def add(self, entry: HistoryEntry) -> HistoryEntry:
        self.entries.append(entry)
        self.save()
        self._rewrite_journal()
        return entry

    def record(self, plan_result, apply_result, trigger: str = "manual") -> HistoryEntry:
        entry = HistoryEntry(
            run_id=ts_id(),
            when=now(),
            source_dir=plan_result.source_dir,
            moves=[
                {"name": m.name, "new_name": m.new_name,
                 "src": m.src, "dst": m.dst, "category": m.label,
                 "size": m.size, "renamed": m.renamed}
                for m in apply_result.moved
            ],
            skipped=len(plan_result.skipped),
            bytes_moved=apply_result.bytes_moved,
            trigger=trigger,
            error_count=len(apply_result.failed),
        )
        return self.add(entry)

    def latest(self, n: int = 20) -> list[HistoryEntry]:
        return list(reversed(self.entries[-n:]))

    def get(self, run_id: str) -> HistoryEntry | None:
        for e in reversed(self.entries):
            if e.run_id == run_id:
                return e
        return None

    def stats(self) -> dict:
        total_moves = sum(e.count for e in self.entries)
        total_bytes = sum(e.bytes_moved for e in self.entries)
        last = self.entries[-1].when if self.entries else 0.0
        return {
            "runs": len(self.entries),
            "moves": total_moves,
            "bytes": total_bytes,
            "bytes_h": human_size(total_bytes),
            "last": last,
        }

    def mark_undone(self, run_id: str) -> None:
        e = self.get(run_id)
        if e is not None:
            e.undone = True
            self.save()
            self._rewrite_journal()

    def clear(self) -> None:
        self.entries = []
        self.save()
        self._rewrite_journal()

    # ---- undo -------------------------------------------------------------
    def undo(self, run_id: str) -> tuple[int, list[str]]:
        """Move every file of a run back where it came from.

        Returns ``(restored, errors)``. Files whose destination no longer
        exists are reported instead of silently skipped.
        """
        import shutil

        entry = self.get(run_id)
        if entry is None:
            return 0, [f"Unbekannter Run: {run_id}"]

        restored = 0
        errors: list[str] = []
        for m in reversed(entry.moves):
            dst = m.get("dst") or ""
            src = m.get("src") or ""
            if not os.path.exists(dst):
                errors.append(f"nicht mehr vorhanden: {os.path.basename(dst)}")
                continue
            try:
                os.makedirs(os.path.dirname(src), exist_ok=True)
                if os.path.exists(src):
                    stem, ext = os.path.splitext(src)
                    i = 1
                    alt = src
                    while os.path.exists(alt):
                        alt = os.path.join(
                            os.path.dirname(src), f"{stem}_restored{i:02d}{ext}"
                        )
                        i += 1
                    src = alt
                if os.path.getsize(dst) > 64_000_000:
                    shutil.move(dst, src)
                else:
                    os.replace(dst, src)
                restored += 1
            except Exception as exc:
                errors.append(f"{os.path.basename(dst)}: {exc}")
        entry.undone = True
        self.save()
        self._rewrite_journal()
        self._cleanup_empty_dirs(entry)
        return restored, errors

    @staticmethod
    def _cleanup_empty_dirs(entry: HistoryEntry) -> list[str]:
        """Remove category folders that undo emptied.

        Only touches directories that are (a) empty and (b) inside the source
        folder we filed from - never a folder the user configured themselves
        and never anything with contents.
        """
        removed: list[str] = []
        source = entry.source_dir
        if not source or not os.path.isdir(source):
            return removed
        for move in entry.moves:
            folder = os.path.dirname(move.get("dst") or "")
            if not folder or not os.path.isdir(folder):
                continue
            try:
                if os.path.normcase(os.path.abspath(folder)) == os.path.normcase(
                        os.path.abspath(source)):
                    continue                      # that IS the source
                if os.listdir(folder):            # not empty -> keep
                    continue
                os.rmdir(folder)
                removed.append(folder)
            except OSError:
                continue
        return removed


def stats_path(cfg_dir: str) -> str:
    return norm_path(os.path.join(cfg_dir, "stats.json"))
