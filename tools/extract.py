"""Extract entries from Crimson Desert PAZ archives.

usage: extract.py GAME_DIR OUT_DIR (--list FILE | --glob PATTERN ...)
LIST FILE: one archive path per line (as shown in the index TSV).
"""
import argparse
import fnmatch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pamt import iter_game, Entry  # noqa: E402
from paz_crypto import decrypt, lz4_decompress  # noqa: E402


def read_entry(e: Entry) -> bytes:
    with open(e.paz_file, "rb") as f:
        f.seek(e.offset)
        raw = f.read(e.comp_size)
    name = Path(e.path).name
    comp = e.compression
    if e.comp_size != e.orig_size and comp == 2:
        try:
            return lz4_decompress(raw, e.orig_size)
        except Exception:  # noqa: BLE001 - probably encrypted first
            return lz4_decompress(decrypt(raw, name), e.orig_size)
    if e.path.endswith(".xml") and not raw.lstrip()[:1] in (b"<", b"\xef"):
        dec = decrypt(raw, name)
        if dec.lstrip()[:1] in (b"<", b"\xef"):
            return dec
    return raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("game")
    ap.add_argument("out")
    ap.add_argument("--list")
    ap.add_argument("--glob", action="append", default=[])
    a = ap.parse_args()
    want = set()
    if a.list:
        want = {l.strip() for l in open(a.list, encoding="utf-8") if l.strip()}
    out = Path(a.out)
    n = 0
    for folder, e in iter_game(Path(a.game)):
        if e.path in want or any(fnmatch.fnmatch(e.path, g) for g in a.glob):
            dst = out / e.path
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(read_entry(e))
            n += 1
    print(f"extracted {n}")


if __name__ == "__main__":
    main()
