"""Reader for Crimson Desert PAMT indexes (game 2.04+ layout).

Format notes from the CDUMM community (issue #458 on
faisalkindi/CrimsonDesert-UltimateModsManager).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Entry:
    path: str
    paz_file: Path
    offset: int
    comp_size: int
    orig_size: int
    flags: int  # flags & 0x00FFFFFF
    paz_index: int

    @property
    def compression(self) -> int:
        return (self.flags >> 16) & 0x0F


def _varint(d, o):
    r = s = 0
    while True:
        b = d[o]
        o += 1
        r |= (b & 0x7F) << s
        s += 7
        if b < 0x80:
            return r, o


def _names(d, o):
    size = struct.unpack_from("<I", d, o)[0]
    o += 4
    start, end, out = o, o + size, {}
    while o < end:
        rel = o - start
        delta, o = _varint(d, o)
        ln = d[o]
        o += 1
        out[rel] = (rel - delta if delta else None, d[o:o + ln].decode("utf-8", "replace"))
        o += ln
    assert o == end
    return out, o


def parse_pamt(pamt: Path) -> list[Entry]:
    pamt = Path(pamt)
    d = pamt.read_bytes()
    o = 4
    pc = struct.unpack_from("<I", d, o)[0]
    o += 12 + pc * 8 + (pc - 1) * 4
    folders, o = _names(d, o)
    nodes, o = _names(d, o)
    fc = struct.unpack_from("<I", d, o)[0]
    o += 4
    dirs = [struct.unpack_from("<IIII", d, o + 16 * i) for i in range(fc)]
    o += 16 * fc
    n = struct.unpack_from("<I", d, o)[0]
    o += 4
    recs = [struct.unpack_from("<IIIII", d, o + 20 * i) for i in range(n)]
    o += 20 * n
    es = struct.unpack_from("<I", d, o)[0]
    o += 4
    exts = d[o:o + es].decode("utf-8").split("\x00")
    assert o + es == len(d), "PAMT did not parse to EOF"

    def path(tree, ref):
        parts = []
        while ref in tree and len(parts) < 64:
            p, nm = tree[ref]
            parts.append(nm)
            ref = p
        return "".join(reversed(parts))

    dir_of = {}
    for _h, ref, first, cnt in dirs:
        dp = path(folders, ref)
        for i in range(first, first + cnt):
            dir_of[i] = dp
    stem = int(pamt.stem)
    paz_dir = pamt.parent
    out = []
    for i, (ref, off, comp, orig, flags) in enumerate(recs):
        idx = flags & 0xFFFF
        p = path(nodes, ref) + exts[flags >> 24]
        dp = dir_of.get(i, "")
        out.append(Entry(path=f"{dp}/{p}" if dp else p,
                         paz_file=paz_dir / f"{stem + idx}.paz",
                         offset=off, comp_size=comp, orig_size=orig,
                         flags=flags & 0x00FFFFFF, paz_index=idx))
    return out


def iter_game(game_dir: Path):
    for pamt in sorted(Path(game_dir).glob("*/0.pamt")):
        try:
            for e in parse_pamt(pamt):
                yield pamt.parent.name, e
        except Exception as ex:  # noqa: BLE001
            print(f"!! {pamt}: {ex}")
