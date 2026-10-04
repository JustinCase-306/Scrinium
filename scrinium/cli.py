"""Command line interface.

Lets Scrinium run headless (Task Scheduler, shortcut, cron-like), which is the
most robust form of "automatic sorting" - no GUI, no tray, no dependencies
beyond the stdlib.

    scrinium --once                 # sort now, print a summary
    scrinium --dry-run              # show what would happen, move nothing
    scrinium --source D:\\Downloads --lang en --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def _force_utf8_stdio() -> None:
    """Ask the interpreter to use UTF-8 for stdout/stderr where supported."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


_FOLD = {
    "✓": "OK", "✖": "X", "⚡": "*", "⚙": "", "✅": "OK",
    "📥": "", "🤖": "", "📁": "", "🎨": "", "📋": "", "📂": "",
    "⏭": "-", "↩": "<-", "ⓘ": "i", "🔍": "", "🔁": "",
    "→": "->", "–": "-", "—": "-", "…": "...", "·": "-",
    "•": "*", "»": '"', "«": '"',
}


def _ascii_safe(text: str) -> str:
    """Fold text to cp1252-printable characters.

    The GUI can render emoji, but a console build (or a redirect into a
    cp1252 pipe) cannot. Replacing rather than raising keeps the CLI usable
    when stdout is not a real UTF-8 terminal.
    """
    for src, dst in _FOLD.items():
        text = text.replace(src, dst)
    # anything still outside cp1252 becomes a question mark
    return text.encode("cp1252", "replace").decode("cp1252")


def out(text: str = "") -> None:
    """print() that can never raise UnicodeEncodeError."""
    line = _ascii_safe(str(text)) + "\n"
    try:
        sys.stdout.write(line)
        sys.stdout.flush()
    except (UnicodeEncodeError, ValueError, OSError):
        try:
            sys.stdout.write(line.encode("ascii", "replace").decode("ascii"))
            sys.stdout.flush()
        except Exception:
            pass


def err_out(text: str = "") -> None:
    try:
        sys.stderr.write(_ascii_safe(str(text)) + "\n")
        sys.stderr.flush()
    except Exception:
        pass


_force_utf8_stdio()

from . import categories as cat_mod
from . import config as cfg_mod
from . import engine, history
from . import rules as rules_mod
from . import i18n
from .util import human_size, ts_iso

MAX_PRINT = 500


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scrinium",
        description="Sort your downloads into category folders.",
    )
    p.add_argument("--once", action="store_true",
                   help="run one sort pass (default when no mode is given)")
    p.add_argument("--dry-run", action="store_true",
                   help="only show what would happen, move nothing")
    p.add_argument("--source", "-s", metavar="DIR",
                   help="download folder (default: from config)")
    p.add_argument("--lang", choices=("de", "en"),
                   help="language for rule names and messages")
    p.add_argument("--min-age", type=int, metavar="SEC",
                   help="only move files older than this many seconds")
    p.add_argument("--recursive", action="store_true",
                   help="also sort files in subfolders")
    p.add_argument("--collide", choices=engine.COLLIDE_POLICIES,
                   help="what to do when the target name is taken")
    p.add_argument("--category", "-c", metavar="KEY", action="append",
                   help="restrict to one category (repeatable)")
    p.add_argument("--json", action="store_true", dest="as_json",
                   help="machine readable output")
    p.add_argument("--history", action="store_true",
                   help="list recent runs and exit")
    p.add_argument("--undo", metavar="RUN_ID",
                   help="undo a run by id and exit")
    p.add_argument("--stats", action="store_true",
                   help="print lifetime statistics and exit")
    p.add_argument("--check-update", action="store_true", dest="check_update",
                   help="check GitHub for a newer Scrinium release and exit")
    p.add_argument("--version", "-V", action="store_true",
                   help="print version and exit")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from . import VERSION

    if args.version:
        out(f"Scrinium {VERSION}")
        return 0

    cfg = cfg_mod.load_config()
    lang = args.lang or cfg.get("lang", "de")
    i18n.set_lang(lang)
    T = i18n.T(lang)
    hist = history.History(cfg_mod.cfg_dir())

    # ---- non-sorting modes ------------------------------------------------
    if args.history:
        entries = hist.latest(20)
        if args.as_json:
            out(json.dumps([e.to_dict() for e in entries], indent=2,
                             ensure_ascii=False))
            return 0
        if not entries:
            out(T("history_empty"))
            return 0
        out(f"{T('history_runs')}: {len(entries)}")
        for e in entries:
            flag = " (undo)" if e.undone else ""
            out(f"  {e.run_id}  {e.when_h}  {e.count:>5} Dateien  "
                  f"{e.bytes_h:>9}  {e.trigger}{flag}")
        return 0

    if args.undo:
        n, errs = hist.undo(args.undo)
        if args.as_json:
            out(json.dumps({"restored": n, "errors": errs}, indent=2,
                             ensure_ascii=False))
            return 0 if n else 1
        out(T("history_undo_done", count=n))
        for e in errs:
            err_out(f"  ! {e}")
        return 0 if n else 1

    if args.check_update:
        from . import updater

        info = updater.check_for_update(cfg_mod.cfg_dir(), force=True)
        if args.as_json:
            out(json.dumps(info, indent=2, ensure_ascii=False))
        else:
            out(updater.describe(info, lang))
            if info.get("available") and info.get("url"):
                out(f"  {info['url']}")
        return 0 if not info.get("available") else 2

    if args.stats:
        s = hist.stats()
        if args.as_json:
            out(json.dumps(s, indent=2, ensure_ascii=False))
            return 0
        out(f"Scrinium {VERSION} - {ts_iso()}")
        out(f"  {T('history_runs')}:    {s['runs']}")
        out(f"  {T('history_files')}:   {s['moves']}")
        out(f"  {T('history_volume')}:  {s['bytes_h']}")
        return 0

    # ---- sort modes --------------------------------------------------------
    source = args.source or cfg.get("dl")
    if not source or not os.path.isdir(source):
        err_out(T("dl_missing", dir=source or "?"))
        return 2

    # Targets default *inside* the folder we are about to sort, so `--source`
    # never scatters files into the configured Downloads folder.
    targets = cfg_mod.target_dirs(cfg, lang, source_dir=source)
    only = set(args.category or []) or None
    if only:
        unknown = [k for k in only if not cat_mod.get(k)]
        if unknown:
            err_out(f"unknown category: {', '.join(sorted(unknown))}")
            return 2

    resolver = rules_mod.Resolver.from_config(cfg)
    if only:
        # Restrict this run only. Never write it back to the config - a one-off
        # `--category video` must not permanently disable every other category.
        resolver.disabled = set(resolver.disabled) | {
            k for k in cat_mod.BY_KEY if k not in only
        }

    min_age = args.min_age if args.min_age is not None else int(cfg.get("min_age_s", 30))
    collide = args.collide or cfg.get("collide", engine.COLLIDE_RENAME)

    plan = engine.plan(
        source, targets, resolver,
        min_age_s=min_age,
        collide=collide,
        lang=lang,
        recursive=args.recursive or bool(cfg.get("recursive")),
    )

    if plan.errors and not plan.moves:
        for e in plan.errors:
            err_out(f"! {e}")
        return 2

    if args.dry_run:
        if args.as_json:
            out(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False))
            return 0
        out(f"[{ts_iso()}] {plan.summary(lang)}")
        _print_plan(plan, lang)
        return 0

    result = engine.apply(plan)
    entry = hist.record(plan, result, "cli")

    if args.as_json:
        # Keep stdout pure JSON - nothing may precede the object.
        out(json.dumps({
            "run_id": entry.run_id,
            "moved": len(result.moved),
            "bytes": result.bytes_moved,
            "failed": [{"file": os.path.basename(s), "error": e}
                       for s, e in result.failed],
            "skipped": len(plan.skipped),
        }, indent=2, ensure_ascii=False))
        return 0 if not result.failed else 1

    # run_id first: it is the only handle on this run, and everything after
    # this point may still fail to print.
    out(f"run_id: {entry.run_id}")
    out(T("status_done", count=len(result.moved), size=human_size(result.bytes_moved)))
    for item in result.moved[:MAX_PRINT]:
        arrow = f" -> {item.new_name}" if item.renamed else ""
        out(f"  {item.label:<18} {item.name}{arrow}  ({item.size_h})")
    if len(result.moved) > MAX_PRINT:
        out(f"  ... +{len(result.moved) - MAX_PRINT} more")
    for src, err in result.failed:
        err_out(f"  ! {os.path.basename(src)}: {err}")
    out(f"  (undo: scrinium --undo {entry.run_id})")
    return 0 if not result.failed else 1


def _print_plan(plan: engine.Plan, lang: str) -> None:
    for key, count, size in plan.count_by_category:
        out(f"  {cat_mod.label(key, lang):<18} {count:>5}  {human_size(size):>9}")
    out()
    for item in plan.moves[:MAX_PRINT]:
        arrow = f" -> {item.new_name}" if item.renamed else ""
        out(f"  {item.label:<18} {item.name}{arrow}  ({item.size_h})")
    if len(plan.moves) > MAX_PRINT:
        out(f"  ... +{len(plan.moves) - MAX_PRINT} more")
    if plan.skipped:
        out(f"\n  skipped ({len(plan.skipped)}):")
        for s in plan.skipped[:MAX_PRINT]:
            out(f"    {s.name:<45} {s.reason}")
        if len(plan.skipped) > MAX_PRINT:
            out(f"    ... +{len(plan.skipped) - MAX_PRINT} more")


def run_cli(argv: list[str] | None = None) -> int:
    try:
        return main(argv)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(run_cli())