"""Rule resolution: which category does a file belong to?

Three layers, highest priority first:

1.  **Filename patterns** - user rules like ``installer_* -> archive``
2.  **Custom extensions**  - user rules like ``*.ps1zip -> archive``
3.  **Built-in extension table** from :mod:`scrinium.categories`

The whole thing is data-driven from the config dict, so it stays testable
without touching the filesystem or Tk.
"""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass, field

from . import categories as cat_mod

# --- stability detection ---------------------------------------------------
# Downloads are often still being written. These patterns mark files as
# "not finished yet"; the engine skips them until they mature.
TEMP_SUFFIXES = (
    ".crdownload", ".part", ".partial", ".tmp", ".temp", ".download",
    ".!ut", ".opdownload", ".filepart", ".bkp", ".downloads",
)
TEMP_PREFIXES = (".~", "~$")
# lowercase - `looks_temporary()` compares against an already-lowered name
CHROME_TMP_PREFIX = ".com.google.chrome."
EDGE_TMP_RE = re.compile(r"^[A-Za-z0-9]{20,}(\s|$)")
INCOMPLETE_RE = re.compile(r"\.(crdownload|part|partial|download|tmp[a-z0-9]{0,4})$", re.I)

# Files that are never moved - they belong to the user's system / app.
NEVER_MOVE_STEMS = {
    "desktop", "start menu", "startmenu", "public desktop",
}
NEVER_MOVE_NAMES = {
    "desktop.ini", "thumbs.db", ".ds_store", "thumbs.db:encryptable",
    "$recycle.bin", "system volume information",
}
NEVER_MOVE_EXT = {
    "lnk", "url", "tmp", "log", "ini", "dat", "db", "lock", "sys", "dll",
}


@dataclass(frozen=True)
class Rule:
    """One user rule."""

    kind: str          # "ext" | "pattern" | "extglob"
    value: str
    target: str        # category key, or "!skip" to never touch
    case_sensitive: bool = False

    def describe(self, lang: str = "de") -> str:
        if self.kind == "ext":
            return f"*.{self.value} → {self.target}"
        if self.kind == "extglob":
            return f"{self.value} → {self.target}"
        return f"Name {_bold(self.value)} → {self.target}"

    def matches(self, filename: str) -> bool:
        name = filename if self.case_sensitive else filename.lower()
        val = self.value if self.case_sensitive else self.value.lower()
        if self.kind == "ext":
            return name.endswith("." + val)
        if self.kind == "extglob":
            return fnmatch.fnmatch(name, val.lower())
        return fnmatch.fnmatch(name, val.lower())


def _bold(text: str) -> str:
    return f"»{text}«"


@dataclass
class Classification:
    """Result of classifying one file."""

    category: str | None
    reason: str = ""            # human-readable, shown in preview
    source: str = "builtin"     # builtin | pattern | ext | extglob
    skip: bool = False          # matched a "!skip" rule
    stable: bool = True         # looks fully downloaded
    age_s: float = 0.0          # file age in seconds


# ---------------------------------------------------------------------------
# stability
# ---------------------------------------------------------------------------
def suffix_of(name: str) -> str:
    """Longest known temp suffix of `name` ('' if none)."""
    low = name.lower()
    for suf in TEMP_SUFFIXES:
        if low.endswith(suf) and len(low) > len(suf):
            return suf
    return ""


def looks_temporary(name: str) -> bool:
    low = name.lower()
    if suffix_of(low):
        return True
    for pre in TEMP_PREFIXES:
        if low.startswith(pre):
            return True
    if low.startswith(CHROME_TMP_PREFIX):
        return True
    if INCOMPLETE_RE.search(low):
        return True
    # browser temp names like "a1b2c3d4e5f6g7h8" (no extension, hex-ish)
    if not os.path.splitext(low)[1] and EDGE_TMP_RE.match(low):
        return True
    return False


def looks_locked(name: str) -> bool:
    low = name.lower()
    return low.startswith(("~$", ".~")) or low.endswith(".lock")


def is_protected(name: str) -> bool:
    """Files Scrinium must never move."""
    low = name.lower()
    if low in NEVER_MOVE_NAMES:
        return True
    stem = os.path.splitext(low)[0].strip()
    if stem in NEVER_MOVE_STEMS:
        return True
    ext = os.path.splitext(low)[1].lstrip(".")
    if ext in ("lnk", "url", "sys", "dll", "ini", "dat"):
        return True
    return False


def is_stable(path: str, now_ts: float, min_age_s: float) -> tuple[bool, str]:
    """Decide whether a file is safe to move.

    Returns ``(stable, reason)``. A file is stable when it is not a known
    temporary artefact *and* has not been modified for `min_age_s` seconds.
    """
    name = os.path.basename(path)
    if looks_temporary(name):
        return False, "unvollständig (.crdownload/.part/…)"
    if looks_locked(name):
        return False, "gesperrt (~$/.lock)"
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return False, "nicht lesbar"
    age = max(0.0, now_ts - mtime)
    if age < min_age_s:
        return False, f"zu neu ({int(age)}s < {int(min_age_s)}s)"
    return True, f"stabil ({int(age)}s alt)"


# ---------------------------------------------------------------------------
# extension + pattern resolution
# ---------------------------------------------------------------------------
def normalize_ext(value: str) -> str:
    v = str(value or "").strip().lower().lstrip("*").lstrip(".").strip()
    return v


@dataclass
class Resolver:
    """Compiled rule set. Cheap to build, safe to reuse."""

    rules: list[Rule] = field(default_factory=list)
    custom_ext: dict[str, str] = field(default_factory=dict)   # ext -> key
    disabled: set[str] = field(default_factory=set)            # category keys
    use_patterns: bool = True
    _glob: list[Rule] = field(default_factory=list, repr=False)
    _plain: list[Rule] = field(default_factory=list, repr=False)

    @classmethod
    def from_config(cls, cfg: dict) -> "Resolver":
        rules: list[Rule] = []
        for entry in cfg.get("rules", []) or []:
            try:
                kind = entry.get("kind") or "pattern"
                value = str(entry.get("value") or "").strip()
                target = str(entry.get("target") or "").strip()
            except AttributeError:
                continue
            if not value or not target:
                continue
            if kind == "ext":
                value = normalize_ext(value)
                if not value:
                    continue
            rules.append(Rule(kind, value, target, bool(entry.get("case"))))

        custom_ext: dict[str, str] = {}
        for entry in cfg.get("custom_ext", []) or []:
            try:
                ext = normalize_ext(entry.get("ext"))
                target = str(entry.get("to") or "").strip()
            except AttributeError:
                continue
            if ext and target:
                custom_ext[ext] = target

        disabled = {str(k) for k in (cfg.get("disabled_categories") or [])}
        return cls(
            rules=rules,
            custom_ext=custom_ext,
            disabled=disabled,
            use_patterns=bool(cfg.get("use_patterns", True)),
        )

    def __post_init__(self) -> None:
        # patterns first so they win over plain extensions
        self._glob = [r for r in self.rules if r.kind == "pattern"]
        self._plain = [r for r in self.rules if r.kind == "extglob"]
        for r in self.rules:
            if r.kind == "ext":
                self._plain.insert(0, r)

    def is_enabled(self, key: str) -> bool:
        return key not in self.disabled

    def category_of(self, filename: str) -> tuple[str | None, str, str, bool]:
        """Return ``(category_key, source, reason, is_skip)``.

        ``is_skip`` is True when a rule explicitly said "never touch this".
        """
        if self.use_patterns:
            for rule in self._glob:
                if rule.matches(filename):
                    if rule.target == "!skip":
                        return None, "pattern", f"Regel »{rule.value}«", True
                    return rule.target, "pattern", f"Name passt zu »{rule.value}«", False
        for rule in self._plain:
            if rule.matches(filename):
                if rule.target == "!skip":
                    return None, "ext", f"Regel *.{rule.value}", True
                return rule.target, "ext", f"Eigene Erweiterung *.{rule.value}", False

        ext = os.path.splitext(filename)[1].lstrip(".").lower()
        if ext and ext in self.custom_ext:
            target = self.custom_ext[ext]
            if target == "!skip":
                return None, "custom_ext", f"Eigene Endung *.{ext}", True
            return target, "custom_ext", f"Eigene Endung *.{ext}", False

        if ext:
            key = cat_mod.EXT_MAP.get(ext)
            if key:
                if not self.is_enabled(key):
                    return None, "builtin", f"{cat_mod.label(key)} deaktiviert", False
                return key, "builtin", f"Endung *.{ext}", False

        # unknown extension - try the image name hints (Screenshots!)
        low = filename.lower()
        for cat in cat_mod.CATEGORIES:
            for hint in cat.name_hints:
                if hint in low and self.is_enabled(cat.key):
                    return cat.key, "hint", f"Name enthält »{hint}«", False
        return None, "none", "keine Regel", False

    def classify(self, filename: str) -> Classification:
        if is_protected(filename):
            return Classification(None, "System-/Shortcut-Datei", "protected", skip=True)
        key, source, reason, skip = self.category_of(filename)
        if skip:
            return Classification(None, reason, source, skip=True)
        if key and not self.is_enabled(key):
            return Classification(None, reason, source, skip=True)
        return Classification(key, reason, source)
