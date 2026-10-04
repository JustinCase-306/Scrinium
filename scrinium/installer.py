"""Self-updating installer for Scrinium.

No Inno Setup / NSIS required: this ships as a tiny PyInstaller exe that

1. finds its own install directory,
2. copies Scrinium.exe next to itself (overwriting a running copy by first
   renaming it - Windows keeps a lock on the running image),
3. optionally registers an autostart entry,
4. optionally launches Scrinium.

The update check lives in :mod:`scrinium.updater`; ``--check`` only reports,
``--silent`` runs without a window. Exit codes: 0 ok, 1 failed, 2 update
available, 3 already current.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False)
                                        else __file__))
DEFAULT_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                           "Programs", "Scrinium")


def log(msg: str) -> None:
    try:
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()
    except Exception:
        pass


def running_exes() -> list[str]:
    """PIDs of Scrinium processes currently holding the exe open."""
    if os.name != "nt":
        return []
    found = []
    try:
        import subprocess

        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Scrinium.exe", "/FO", "CSV", "/NH"],
            capture_output=True, timeout=15,
        ).stdout.decode("cp1252", "replace")     # tasklist is not UTF-8
        for line in out.splitlines():
            if "Scrinium.exe" not in line:
                continue
            parts = [p.strip().strip('"') for p in line.split(",")]
            if len(parts) > 1 and parts[1].isdigit():
                found.append(parts[1])
    except Exception:
        pass
    return found


def install(source_exe: str, target_dir: str = DEFAULT_DIR,
            launch: bool = True, quiet: bool = False,
            cleanup_payload: bool = False) -> int:
    """Copy `source_exe` to `target_dir` as Scrinium.exe.

    `cleanup_payload` deletes the source after a successful copy. It defaults
    to False on purpose: an installer must stay re-runnable (repair, update,
    second install), and a self-deleting payload cannot be.
    """
    source_exe = os.path.abspath(source_exe)
    if not os.path.isfile(source_exe):
        log(f"ERROR: installer payload missing: {source_exe}")
        return 1

    target_dir = os.path.abspath(target_dir)
    try:
        os.makedirs(target_dir, exist_ok=True)
    except OSError as exc:
        log(f"ERROR: cannot create {target_dir}: {exc}")
        return 1

    dest = os.path.join(target_dir, "Scrinium.exe")
    same = os.path.normcase(source_exe) == os.path.normcase(dest)

    if same:
        if not quiet:
            log(f"Already installed: {dest}")
    else:
        # A running exe cannot be overwritten - rename it aside first, then let
        # Windows clean it up once the process exits.
        backup = dest + ".old"
        if os.path.exists(dest):
            for p in running_exes():
                log(f"  close Scrinium (PID {p}) to finish updating")
            try:
                if os.path.exists(backup):
                    os.unlink(backup)          # never stack backups
                os.replace(dest, backup)
            except OSError as exc:
                log(f"ERROR: cannot replace {dest}: {exc}")
                return 1
        try:
            shutil.copy2(source_exe, dest)
        except OSError as exc:
            log(f"ERROR: copy failed: {exc}")
            return 1
        # The backup only matters while the old process is still running;
        # otherwise it is 9 MB of dead weight in the install folder.
        if not os.path.exists(backup) or not running_exes():
            try:
                os.unlink(backup)
            except OSError:
                pass
        if not quiet:
            log(f"Installed: {dest}")

    try:
        from scrinium import platform_win as P

        P.set_autostart(True)
        if not quiet:
            log("Autostart registered.")
    except Exception as exc:
        log(f"note: autostart not set ({exc})")

    # A first-run config write proves the install actually runs.
    try:
        from scrinium import config as C

        cfg = C.load_config()
        C.save_config(cfg)
        if not quiet:
            log(f"Config ready: {C.cfg_path()}")
    except Exception as exc:
        log(f"ERROR: config init failed: {exc}")
        return 1

    if launch:
        try:
            os.startfile(dest)
            if not quiet:
                log("Launched Scrinium.")
        except Exception as exc:
            log(f"note: could not launch ({exc})")

    # Only remove the payload when explicitly asked - e.g. after installing
    # from a temp extraction. Never during a normal run: the installer has to
    # stay usable for a repair or a second install.
    if cleanup_payload and not same and not getattr(sys, "frozen", False):
        try:
            os.unlink(source_exe)
        except OSError:
            pass
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="Scrinium-Setup",
                                description="Install or update Scrinium.")
    p.add_argument("--dir", default=DEFAULT_DIR, help="install directory")
    p.add_argument("--no-launch", action="store_true", help="do not start Scrinium")
    p.add_argument("--silent", action="store_true", help="no output")
    p.add_argument("--check", action="store_true", help="only check for updates")
    p.add_argument("--version", action="store_true", help="print version")
    args = p.parse_args(argv)

    if args.version:
        from scrinium import VERSION

        log(f"Scrinium-Setup {VERSION}")
        return 0

    quiet = args.silent

    if args.check:
        try:
            from scrinium.updater import check_for_update

            info = check_for_update()
        except Exception as exc:
            log(f"ERROR: update check failed: {exc}")
            return 1
        if info.get("available"):
            log(f"Update available: {info['version']} (current {info['current']})")
            log(info.get("url", ""))
            return 2
        log(f"Scrinium {info['current']} is up to date.")
        return 3

    # The payload sits next to the installer, or in its own temp dir.
    candidates = [HERE, os.path.dirname(HERE), tempfile.gettempdir()]
    payload = None
    for base in candidates:
        for name in ("Scrinium.exe", "Scrinium_*.exe"):
            cand = os.path.join(base, name)
            if os.path.isfile(cand) and "Setup" not in os.path.basename(cand):
                payload = cand
                break
        if payload:
            break
    if payload is None:
        log("ERROR: Scrinium.exe payload not found next to the installer.")
        return 1

    return install(payload, args.dir, launch=not args.no_launch, quiet=quiet)


if __name__ == "__main__":
    sys.exit(main())