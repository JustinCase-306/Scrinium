"""Generate Scrinium's .ico without any image assets in the repo.

Pure-stdlib PNG writer + a hand-rolled ICO container, so the build has no
Pillow dependency and the icon is reproducible from code.

    python -m scrinium.icons            # writes assets/scrinium.ico
"""

from __future__ import annotations

import os
import struct
import sys
import zlib

SIZES = (16, 24, 32, 48, 64, 128, 256)

# Accent blue on a dark slate rounded square, with a downward arrow (sorting).
BG_TOP = (59, 142, 208)
BG_BOTTOM = (31, 106, 165)
ARROW = (255, 255, 255)
GLYPH = (255, 255, 255)


def _rounded_alpha(size: int, radius_ratio: float = 0.22) -> list[list[float]]:
    """Anti-aliased coverage mask for a rounded square."""
    r = size * radius_ratio
    mask = [[0.0] * size for _ in range(size)]
    for y in range(size):
        for x in range(size):
            # distance to the rounded-rect boundary
            dx = max(r - x, x - (size - 1 - r), 0.0)
            dy = max(r - y, y - (size - 1 - r), 0.0)
            dist = (dx * dx + dy * dy) ** 0.5
            edge = r - dist if (dx or dy) else 0.0
            mask[y][x] = 0.0 if edge <= 0 else (1.0 if edge >= 1 else edge)
    return mask


def _arrow_mask(size: int) -> list[list[float]]:
    """A chunky down-arrow: shaft plus triangular head."""
    m = [[0.0] * size for _ in range(size)]
    shaft_w = max(1, int(size * 0.13))
    top = int(size * 0.22)
    head_top = int(size * 0.52)
    cx = (size - 1) / 2.0
    head_w = size * 0.32

    for y in range(top, int(size * 0.76)):
        half = shaft_w / 2.0
        for x in range(size):
            if abs(x - cx) <= half:
                m[y][x] = 1.0
    for y in range(head_top, int(size * 0.76)):
        t = (y - head_top) / max(1.0, size * 0.76 - head_top)
        half = head_w * (1.0 - t)
        for x in range(size):
            if abs(x - cx) <= half:
                m[y][x] = 1.0
    # baseline the arrow sits on
    for y in range(int(size * 0.78), int(size * 0.86)):
        for x in range(int(size * 0.22), int(size * 0.78)):
            m[y][x] = 1.0
    return m


def _compose(size: int) -> bytes:
    """Return raw RGBA rows for one size."""
    cov = _rounded_alpha(size)
    arrow = _arrow_mask(size)
    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            t = y / max(1, size - 1)
            bg = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
            a = cov[y][x]
            if a <= 0:
                row += bytes((0, 0, 0, 0))
                continue
            am = arrow[y][x]
            px = tuple(int(bg[i] + (ARROW[i] - bg[i]) * am) for i in range(3))
            row += bytes((px[0], px[1], px[2], int(round(a * 255))))
        rows.append(bytes(row))
    return b"".join(rows)


def _png(size: int) -> bytes:
    raw = _compose(size)
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)   # RGBA8
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def build_ico(path: str, sizes=SIZES) -> str:
    images = [(s, _png(s)) for s in sizes]
    out = bytearray(struct.pack("<HHH", 0, 1, len(images)))
    offset = 6 + 16 * len(images)
    header_size = offset
    for size, png in images:
        out += struct.pack("<BBBBHHII",
                           0 if size >= 256 else size,      # 0 == 256
                           0 if size >= 256 else size,
                           0, 0, 1, 32, len(png), offset)
        offset += len(png)
    for _size, png in images:
        out += png
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(bytes(out))
    assert len(out) == header_size + sum(len(p) for _s, p in images)
    return path


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "assets", "scrinium.ico")
    build_ico(out)
    print(f"wrote {out} ({os.path.getsize(out)} bytes, {len(SIZES)} sizes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())