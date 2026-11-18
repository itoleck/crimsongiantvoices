"""List the streamed WEM source IDs referenced by Wwise banks (bank v150).

usage: bank_sources.py BNK_ROOT INDEX_TSV NAMES_REGEX OUT_LIST
Banks in this game are named by the FNV-1 hash of their event name
(e.g. vce_effort_ntm_adult_2 -> 2530239014.bnk).
"""
import glob
import re
import struct
import sys
from pathlib import Path


def fnv1(s: str) -> int:
    h = 2166136261
    for c in s.lower().encode():
        h = (h * 16777619) & 0xFFFFFFFF
        h ^= c
    return h


def sources(bnk: bytes):
    o, out = 0, []
    while o < len(bnk):
        tag = bnk[o:o + 4]
        sz = struct.unpack_from("<I", bnk, o + 4)[0]
        if tag == b"HIRC":
            n = struct.unpack_from("<I", bnk, o + 8)[0]
            p = o + 12
            for _ in range(n):
                t = bnk[p]
                s = struct.unpack_from("<I", bnk, p + 1)[0]
                if t == 2:  # CAkSound
                    _oid, plugin, stype, sid, msize = struct.unpack_from("<IIBII", bnk, p + 5)
                    out.append((sid, stype, plugin))
                p += 5 + s
        o += 8 + sz
    return out


def main():
    root, index, rx, outp = sys.argv[1:5]
    names = set()
    # candidate event names come from the soundbanksinfo string table
    for f in glob.glob(f"{root}/../x/sound/bin__/windows/*.pasound"):
        data = open(f, "rb").read()
        # names are stored length-prefixed: <u8 len><name>
        for m in re.finditer(rb"([\x03-\x7f])([a-z0-9_]{3,})", data):
            n, s = m.group(1)[0], m.group(2)[:m.group(1)[0]]
            if len(s) == n:
                names.add(s.decode())
    names = sorted(n for n in names if re.search(rx, n))
    paths = [l.split("\t")[1] for l in open(index, encoding="utf-8").read().splitlines()]
    wem = {}
    for p in paths:
        m = re.match(r"^sound/windows/media/(?:([^/]+)/)?(\d+)\.wem$", p)
        if m:
            wem.setdefault(int(m.group(2)), []).append(p)
    picked = set()
    for n in names:
        h = fnv1(n)
        banks = glob.glob(f"{root}/**/{h}.bnk", recursive=True)
        if not banks:
            continue
        srcs = set()
        for b in banks:
            srcs |= {s for s, _t, _pl in sources(open(b, "rb").read())}
        found = [p for s in srcs for p in wem.get(s, [])]
        picked.update(found)
        print(f"{n:60s} banks={len(banks)} sources={len(srcs)} wems={len(found)}")
    Path(outp).write_text("\n".join(sorted(picked)) + "\n", encoding="utf-8")
    print("total wems", len(picked))


if __name__ == "__main__":
    main()
