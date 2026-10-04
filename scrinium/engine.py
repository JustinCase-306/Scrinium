"""The sorting engine: plan first, then move.

`plan()` is a pure dry-run - it never touches the filesystem. You inspect the
result, then hand it to `apply()` (or `apply_now()`) which performs the moves
and writes an undo journal entry.

Safety properties:
*   never moves a file that is still being downloaded
*   never overwrites an existing file
*   every applied move is recorded so it can be undone
*   cancelling mid-run leaves already-moved files in a recoverable journal
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field, asdict

from . import categories as cat_mod
from . import rules as rules_mod
from .util import human_size, is_inside, same_path, ts_iso

# collision policies
COLLIDE_SKIP = "skip"            # leave the source file where it is
COLLIDE_RENAME = "rename"        # name_01, name_02, ...  (default)
COLLIDE_REPLACE = "replace"      # overwrite the older existing file
COLLIDE_POLICIES = (COLLIDE_SKIP, COLLIDE_RENAME, COLLIDE_REPLACE)

# above this size we use shutil.move instead of os.replace (cross-volume safe)
LARGE_FILE_BYTES = 64_000_000


@dataclass
class MoveItem:
    src: str
    dst: str
    category: str          # category key
    label: str             # human label for GUI/log
    size: int = 0
    size_h: str = "0 B"
    reason: str = ""
    source: str = "builtin"
    renamed: bool = False

    @property
    def name(self) -> str:
        return os.path.basename(self.src)

    @property
    def new_name(self) -> str:
        return os.path.basename(self.dst)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "new_name": self.new_name,
            "src": self.src,
            "dst": self.dst,
            "category": self.category,
            "label": self.label,
            "size": self.size,
            "size_h": self.size_h,
            "reason": self.reason,
            "source": self.source,
            "renamed": self.renamed,
        }


@dataclass
class SkippedItem:
    name: str
    reason: str
    size: int = 0
    size_h: str = "0 B"
    category: str | None = None


@dataclass
class Plan:
    source_dir: str
    moves: list[MoveItem] = field(default_factory=list)
    skipped: list[SkippedItem] = field(default_factory=list)
    # (category_key, count, bytes)
    totals: dict[str, tuple[int, int]] = field(default_factory=dict)
    scanned: int = 0
    created_dirs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(i.size for i in self.moves)

    @property
    def total_bytes_h(self) -> str:
        return human_size(self.total_bytes)

    @property
    def count_by_category(self) -> list[tuple[str, int, int]]:
        return sorted(
            ((k, c, b) for k, (c, b) in self.totals.items()),
            key=lambda t: (-t[1], cat_mod.label(t[0])),
        )

    def summary(self, lang: str = "de") -> str:
        if not self.moves:
            return {
                "de": "Nichts zu sortieren – alle Dateien sind bereits einsortiert.",
                "en": "Nothing to sort - every file is already filed.",
            }[lang]
        return {
            "de": f"{len(self.moves)} Datei(en) einsortieren ({self.total_bytes_h}), "
                  f"{len(self.skipped)} übersprungen.",
            "en": f"File {len(self.moves)} to file ({self.total_bytes_h}), "
                  f"{len(self.skipped)} skipped.",
        }[lang]

    def to_dict(self) -> dict:
        """Serialisable snapshot - used by the CLI's --json output."""
        return {
            "source_dir": self.source_dir,
            "scanned": self.scanned,
            "total_bytes": self.total_bytes,
            "total_bytes_h": self.total_bytes_h,
            "moves": [m.to_dict() for m in self.moves],
            "skipped": [asdict(s) for s in self.skipped],
            "totals": {k: list(v) for k, v in self.totals.items()},
            "created_dirs": list(self.created_dirs),
            "errors": list(self.errors),
        }


# ---------------------------------------------------------------------------
# collision handling
# ---------------------------------------------------------------------------
def resolve_collision(dst: str, policy: str = COLLIDE_RENAME) -> tuple[str, bool]:
    """Return ``(final_dst, renamed)`` honouring the collision policy."""
    if not os.path.exists(dst):
        return dst, False
    if policy == COLLIDE_SKIP:
        return dst, False          # caller checks existence and skips
    if policy == COLLIDE_REPLACE:
        return dst, False
    stem, ext = os.path.splitext(dst)
    directory = os.path.dirname(dst)
    for i in range(1, 10000):
        cand = os.path.join(directory, f"{stem}_{i:02d}{ext}")
        if not os.path.exists(cand):
            return cand, True
    return dst, False


# ---------------------------------------------------------------------------
# planning
# ---------------------------------------------------------------------------
def plan(
    source_dir: str,
    targets: dict[str, str],
    resolver: rules_mod.Resolver | None = None,
    *,
    min_age_s: float = 30.0,
    collide: str = COLLIDE_RENAME,
    lang: str = "de",
    recursive: bool = False,
    max_files: int = 0,
    cancel=None,
    progress=None,
) -> Plan:
    """Dry-run: work out exactly what would happen. Never mutates anything."""
    resolver = resolver or rules_mod.Resolver()
    result = Plan(source_dir=source_dir)

    if not source_dir or not os.path.isdir(source_dir):
        result.errors.append(
            {"de": f"Ordner nicht gefunden: {source_dir}",
             "en": f"Folder not found: {source_dir}"}[lang]
        )
        return result

    import time as _time
    now_ts = _time.time()

    def target_for(key: str) -> str:
        return targets.get(key) or os.path.join(source_dir, cat_mod.folder_name(key, lang))

    needed_dirs: set[str] = set()

    # Never walk into our own target folders, otherwise a recursive run would
    # keep re-filing what it filed a moment ago.
    excluded: set[str] = set()
    for _key, _folder in targets.items():
        if _folder:
            excluded.add(os.path.normcase(os.path.abspath(_folder)))

    def is_excluded_dir(path: str) -> bool:
        return os.path.normcase(os.path.abspath(path)) in excluded

    def walk() -> list[str]:
        out: list[str] = []
        if recursive:
            for root, dirs, files in os.walk(source_dir):
                dirs[:] = [d for d in dirs if not is_excluded_dir(os.path.join(root, d))]
                for f in files:
                    full = os.path.join(root, f)
                    parent_abs = os.path.normcase(os.path.dirname(os.path.abspath(full)))
                    if parent_abs in excluded:
                        continue
                    out.append(full)
        else:
            try:
                for f in os.listdir(source_dir):
                    out.append(os.path.join(source_dir, f))
            except OSError as exc:
                result.errors.append(str(exc))
        return out

    entries = walk()
    result.scanned = len(entries)

    # Track names we are about to create so two same-named files in this run
    # cannot both claim the same destination.
    claimed: set[str] = set()
    ordered = sorted(entries, key=lambda p: os.path.basename(p).lower())

    for idx, path in enumerate(ordered):
        if cancel is not None and cancel():
            result.errors.append("Abgebrochen.")
            break
        if progress is not None:
            try:
                progress(idx, len(ordered))
            except Exception:
                pass

        name = os.path.basename(path)
        if not os.path.isfile(path):
            continue
        # Already inside one of our target folders -> leave it alone.
        parent_abs = os.path.normcase(os.path.dirname(os.path.abspath(path)))
        if parent_abs in excluded:
            continue

        cls = resolver.classify(name)

        stable, why = rules_mod.is_stable(path, now_ts, min_age_s)
        if not stable:
            result.skipped.append(
                SkippedItem(name, why, _safe_size(path), "", cls.category)
            )
            continue
        if cls.skip or cls.category is None:
            reason = cls.reason or "keine Kategorie"
            result.skipped.append(
                SkippedItem(name, reason, _safe_size(path), "", cls.category)
            )
            continue

        key = cls.category
        if not resolver.is_enabled(key):
            result.skipped.append(
                SkippedItem(name, f"{cat_mod.label(key)} deaktiviert",
                            _safe_size(path), "", key)
            )
            continue

        folder = target_for(key)
        if not folder:
            result.skipped.append(SkippedItem(name, "kein Zielordner", _safe_size(path), "", key))
            continue

        dst_dir = os.path.abspath(folder)
        src_abs = os.path.abspath(path)
        if same_path(dst_dir, os.path.dirname(src_abs)):
            continue                                   # already there
        if is_inside(dst_dir, src_abs):
            result.skipped.append(SkippedItem(name, "Ziel liegt in der Datei", _safe_size(path), "", key))
            continue

        dst = os.path.join(dst_dir, name)
        if collide == COLLIDE_SKIP and (os.path.exists(dst) or _norm(dst) in claimed):
            result.skipped.append(SkippedItem(name, "Ziel existiert bereits", _safe_size(path), "", key))
            continue
        dst, renamed = resolve_collision(dst, collide)
        nk = _norm(dst)
        if nk in claimed:
            dst, renamed = resolve_collision(dst, COLLIDE_RENAME)
            nk = _norm(dst)
        claimed.add(nk)

        size = _safe_size(path)
        needed_dirs.add(dst_dir)
        result.moves.append(
            MoveItem(
                src=src_abs,
                dst=dst,
                category=key,
                label=cat_mod.label(key, lang),
                size=size,
                size_h=human_size(size),
                reason=cls.reason,
                source=cls.source,
                renamed=renamed,
            )
        )
        prev = result.totals.get(key, (0, 0))
        result.totals[key] = (prev[0] + 1, prev[1] + size)

    for d in sorted(needed_dirs):
        if not os.path.isdir(d):
            result.created_dirs.append(d)
    return result


def _norm(p: str) -> str:
    return os.path.normcase(os.path.abspath(p))


def _safe_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# applying
# ---------------------------------------------------------------------------
@dataclass
class ApplyResult:
    moved: list[MoveItem] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)   # (src, error)
    cancelled: bool = False
    bytes_moved: int = 0

    @property
    def ok(self) -> bool:
        return not self.failed


def apply(
    p: Plan,
    *,
    replace: bool = False,
    cancel=None,
    progress=None,
    on_move=None,
) -> ApplyResult:
    """Execute a plan. Records nothing - the caller owns the journal."""
    res = ApplyResult()
    total = len(p.moves)
    for i, item in enumerate(p.moves):
        if cancel is not None and cancel():
            res.cancelled = True
            break
        if progress is not None:
            try:
                progress(i, total)
            except Exception:
                pass
        try:
            os.makedirs(os.path.dirname(item.dst), exist_ok=True)
            if os.path.exists(item.dst):
                if not replace:
                    item.dst, item.renamed = resolve_collision(item.dst, COLLIDE_RENAME)
                if os.path.exists(item.dst):
                    raise FileExistsError(item.dst)
                if replace:
                    os.unlink(item.dst)
            # os.replace() is atomic and cheap, but cannot cross volumes and
            # fails on some network shares - fall back to shutil for big files.
            if _safe_size(item.src) > LARGE_FILE_BYTES:
                shutil.move(item.src, item.dst)
            else:
                os.replace(item.src, item.dst)
            res.moved.append(item)
            res.bytes_moved += item.size
            if on_move is not None:
                on_move(item)
        except Exception as exc:      # keep going, report at the end
            res.failed.append((item.src, str(exc)))
    if progress is not None:
        try:
            progress(total, total)
        except Exception:
            pass
    return res


def apply_now(source_dir, targets, resolver=None, **kwargs) -> tuple[Plan, ApplyResult]:
    """plan() + apply() in one call - used by the CLI and the watcher."""
    p = plan(source_dir, targets, resolver, **{k: v for k, v in kwargs.items()
                                                if k not in ("replace", "on_move")})
    r = apply(p, **{k: v for k, v in kwargs.items() if k in ("replace", "cancel", "progress", "on_move")})
    return p, r


def scan_counts(source_dir: str, recursive: bool = False) -> dict[str, int]:
    """Top-level extension histogram for the overview card."""
    counts: dict[str, int] = {}
    if not source_dir or not os.path.isdir(source_dir):
        return counts
    try:
        names = os.listdir(source_dir)
    except OSError:
        return counts
    for n in names:
        ext = os.path.splitext(n)[1].lstrip(".").lower()
        if ext:
            counts[ext] = counts.get(ext, 0) + 1
    return counts


def undo_pairs(journal_entry: dict) -> list[tuple[str, str]]:
    """(dst, src) pairs - reverse order so renames unwind cleanly."""
    moves = journal_entry.get("moves", [])
    return [(m.get("dst", ""), m.get("src", "")) for m in reversed(moves) if m.get("dst") and m.get("src")]


__all__ = [
    "COLLIDE_POLICIES", "COLLIDE_RENAME", "COLLIDE_REPLACE", "COLLIDE_SKIP",
    "ApplyResult", "MoveItem", "Plan", "SkippedItem",
    "apply", "apply_now", "plan", "resolve_collision", "scan_counts",
    "undo_pairs", "ts_iso",
]
