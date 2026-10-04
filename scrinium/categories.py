"""Category registry.

Every category knows its extensions, its default folder name per language and
an accent colour used by the GUI. The registry is the single source of truth -
the engine, the rules layer and the UI all read from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

LANGS = ("de", "en")


@dataclass(frozen=True)
class Category:
    key: str
    name_de: str
    name_en: str
    folder_de: str
    folder_en: str
    color: str
    extensions: tuple[str, ...]
    enabled_by_default: bool = True
    # categories that also match on file *name* patterns (e.g. screenshots)
    name_hints: tuple[str, ...] = field(default=())

    def label(self, lang: str) -> str:
        return self.name_en if lang == "en" else self.name_de

    def folder(self, lang: str) -> str:
        return self.folder_en if lang == "en" else self.folder_de


CATEGORIES: tuple[Category, ...] = (
    Category(
        key="image",
        name_de="Bilder",
        name_en="Images",
        folder_de="Bilder",
        folder_en="Images",
        color="#F59E0B",
        extensions=(
            "jpg", "jpeg", "jpe", "jfif", "png", "gif", "bmp", "tif", "tiff",
            "webp", "svg", "heic", "heif", "avif", "ico", "raw", "cr2", "cr3",
            "nef", "arw", "dng", "orf", "rw2", "raf", "srw", "pef",
        ),
        name_hints=(
            "screenshot", "screen shot", "bildschirmfoto", "snip", "snippingtool",
            "schnellfoto", "capture", "grab", "shot_",
        ),
    ),
    Category(
        key="video",
        name_de="Videos",
        name_en="Videos",
        folder_de="Videos",
        folder_en="Videos",
        color="#EF4444",
        extensions=(
            "mp4", "m4v", "mkv", "avi", "mov", "wmv", "flv", "mpeg", "mpg",
            "webm", "vob", "3gp", "3g2", "divx", "mts", "m2ts", "ogv",
            "rmvb", "asf", "f4v", "mpv", "roq",
            # NOTE: no plain "ts" - it is far more often TypeScript than an
            # MPEG transport stream. Users can re-map it via a custom rule.
        ),
    ),
    Category(
        key="music",
        name_de="Musik",
        name_en="Music",
        folder_de="Musik",
        folder_en="Music",
        color="#A855F7",
        extensions=(
            "mp3", "wav", "aac", "flac", "ogg", "oga", "m4a", "opus", "wma",
            "alac", "aiff", "aif", "ape", "wv", "dsf", "dff", "mka",
        ),
    ),
    Category(
        key="audio",
        name_de="Audio & Podcast",
        name_en="Audio & Podcasts",
        folder_de="Audio",
        folder_en="Audio",
        color="#C084FC",
        extensions=(
            "m4b", "aax", "amr", "mid", "midi", "caf", "au", "snd", "ra",
            "rm", "m3u", "m3u8", "pls", "cue", "srt", "vtt", "ass", "ssa",
            "lrc", "sbv",
        ),
    ),
    Category(
        key="doc",
        name_de="Dokumente",
        name_en="Documents",
        folder_de="Dokumente",
        folder_en="Documents",
        color="#3B82F6",
        extensions=(
            "pdf", "doc", "docx", "docm", "odt", "ott", "rtf", "txt", "md",
            "markdown", "tex", "pages", "wpd", "wps", "abw", "sdw", "log",
        ),
    ),
    Category(
        key="sheet",
        name_de="Tabellen",
        name_en="Spreadsheets",
        folder_de="Tabellen",
        folder_en="Spreadsheets",
        color="#10B981",
        extensions=(
            "xls", "xlsx", "xlsm", "xlsb", "xltx", "ods", "ots", "csv", "tsv",
            "dif", "numbers", "gnumeric",
        ),
    ),
    Category(
        key="slides",
        name_de="Präsentationen",
        name_en="Presentations",
        folder_de="Praesentationen",
        folder_en="Presentations",
        color="#F97316",
        extensions=("ppt", "pptx", "pptm", "pps", "ppsx", "odp", "otp", "key"),
    ),
    Category(
        key="book",
        name_de="Bücher & E-Books",
        name_en="Books & E-Books",
        folder_de="Buecher",
        folder_en="Books",
        color="#D97706",
        extensions=("epub", "mobi", "azw", "azw3", "fb2", "djvu", "lit", "chm", "cbz", "cbr"),
    ),
    Category(
        key="archive",
        name_de="Archive",
        name_en="Archives",
        folder_de="Archive",
        folder_en="Archives",
        color="#78716C",
        extensions=(
            "zip", "rar", "7z", "tar", "gz", "tgz", "bz2", "tbz", "tbz2",
            "xz", "txz", "lz", "lzma", "zst", "z", "cab", "arj", "ace",
            "zipx", "sit", "sea", "war", "nupkg", "whl", "gem", "crate",
        ),
    ),
    Category(
        key="disk",
        name_de="Images & Abbilder",
        name_en="Disk Images",
        folder_de="Disk-Images",
        folder_en="Disk Images",
        color="#0EA5E9",
        extensions=("iso", "img", "vhd", "vhdx", "vmdk", "wim", "esd", "dmg", "toast"),
    ),
    Category(
        key="app",
        name_de="Anwendungen",
        name_en="Applications",
        folder_de="Anwendungen",
        folder_en="Applications",
        color="#22C55E",
        extensions=(
            "exe", "msi", "msu", "msix", "appx", "appimage", "snap", "flatpak",
            "app", "deb", "rpm", "pkg", "ipa", "apk", "apks", "aab", "xapk",
            "bat", "cmd", "ps1", "psm1", "vbs", "wsf", "reg", "inf",
            "lnk", "url",
        ),
    ),
    Category(
        key="code",
        name_de="Code & Projekte",
        name_en="Code & Projects",
        folder_de="Code",
        folder_en="Code",
        color="#8B5CF6",
        extensions=(
            "py", "pyc", "pyw", "ipynb", "js", "mjs", "cjs",
            # "ts" is claimed here, not by video: a bare .ts in a download folder
            # is TypeScript far more often than an MPEG transport stream.
            "ts", "tsx",
            "jsx", "html", "htm", "css", "scss", "sass", "less", "vue", "svelte",
            "c", "h", "cpp", "hpp", "cc", "cs", "java", "kt", "kts", "go",
            "rs", "rb", "php", "pl", "pm", "lua", "r", "jl", "swift", "scala",
            "dart", "ex", "exs", "erl", "hs", "clj", "sql", "db", "sqlite",
            "json", "jsonl", "yaml", "yml", "toml", "ini", "cfg", "conf",
            "env", "gradle", "cmake", "make", "mk", "dockerfile", "lock", "patch", "diff",
        ),
    ),
    Category(
        key="font",
        name_de="Schriften",
        name_en="Fonts",
        folder_de="Schriften",
        folder_en="Fonts",
        color="#EC4899",
        extensions=("ttf", "otf", "woff", "woff2", "eot", "ttc", "pfb", "pfm"),
    ),
    Category(
        key="design",
        name_de="Design-Dateien",
        name_en="Design Files",
        folder_de="Design",
        folder_en="Design",
        color="#14B8A6",
        extensions=("psd", "psb", "ai", "eps", "sketch", "fig", "xd", "afdesign", "afphoto"),
    ),
    Category(
        key="model3d",
        name_de="3D & CAD",
        name_en="3D & CAD",
        folder_de="3D",
        folder_en="3D",
        color="#F43F5E",
        extensions=(
            "obj", "fbx", "stl", "ply", "dae", "blend", "glb", "gltf", "3ds",
            "max", "mb", "ma", "step", "stp", "iges", "igs", "dxf", "dwg",
            "skp", "3mf", "amf", "usd", "usdz",
        ),
    ),
    Category(
        key="game",
        name_de="Spiele & Mods",
        name_en="Games & Mods",
        folder_de="Spiele",
        folder_en="Games",
        color="#EAB308",
        extensions=(
            # NOTE: no "3ds" here - it is the 3D Studio mesh format and is
            # claimed by the model3d category. Game content uses "pk3"/"vpk"/…
            "unity", "unity3d", "pak", "wad", "vpk", "gcf", "gcf2", "ncf",
            "pk3", "bnk", "esm", "esp", "espfm", "sav", "rom", "gbs",
            "nes", "sfc", "smc", "gb", "gba", "nds", "cia", "3dsx", "xci",
        ),
    ),
    Category(
        key="other",
        name_de="Sonstiges",
        name_en="Other",
        folder_de="Sonstiges",
        folder_en="Other",
        color="#64748B",
        extensions=(),
        enabled_by_default=False,
    ),
)

BY_KEY: dict[str, Category] = {c.key: c for c in CATEGORIES}
DEFAULT_KEYS: tuple[str, ...] = tuple(c.key for c in CATEGORIES if c.enabled_by_default)

# ext -> category key (first category wins for duplicates)
EXT_MAP: dict[str, str] = {}
CONFLICTING_EXTS: dict[str, tuple[str, ...]] = {}
for _cat in CATEGORIES:
    for _ext in _cat.extensions:
        prior = EXT_MAP.get(_ext)
        if prior is None:
            EXT_MAP[_ext] = _cat.key
        elif prior != _cat.key:
            CONFLICTING_EXTS[_ext] = (prior, _cat.key)

# legacy 5-category names, kept so old configs keep working
LEGACY_FOLDERS = {
    "image": "Bilder",
    "doc": "Dokumente",
    "music": "Musik",
    "video": "Videos",
    "app": "Anwendungen",
}


def get(key: str) -> Category | None:
    return BY_KEY.get(str(key or "").strip())


def label(key: str, lang: str = "de") -> str:
    cat = get(key)
    return cat.label(lang) if cat else str(key)


def folder_name(key: str, lang: str = "de") -> str:
    """The physical folder name for a category.

    IMPORTANT: `lang` is accepted for call-site compatibility but IGNORED.
    The folder on disk must never change when the user switches the interface
    language - otherwise flipping to English would scatter every file into a
    second, empty tree (Dokumente/ -> Documents/) and look like data loss.
    Only the *labels* in the UI are translated; folders keep their German v1
    names so existing installs stay intact.
    """
    cat = get(key)
    return cat.folder_de if cat else str(key)


def color(key: str) -> str:
    cat = get(key)
    return cat.color if cat else "#64748B"


def ext_count(key: str) -> int:
    cat = get(key)
    return len(cat.extensions) if cat else 0


def all_extensions() -> list[str]:
    return sorted(EXT_MAP, key=lambda e: (EXT_MAP[e], e))
