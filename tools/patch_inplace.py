"""Write replacement WEMs into the game's .paz archives in place.

Nothing in the index (.pamt) or archive list (meta/0.papgt) is changed:
each new file is written over the original entry's bytes at the same
offset, padded to exactly the original size with a RIFF JUNK chunk.
Only uncompressed entries are supported (all voice WEMs are stored raw).

Before each write, the original bytes are saved under BACKUP_DIR so
`restore` can put them back byte for byte.

usage:
  patch_inplace.py patch   GAME_DIR REPLACEMENT_ROOT BACKUP_DIR [--dry-run]
  patch_inplace.py restore GAME_DIR BACKUP_DIR
REPLACEMENT_ROOT mirrors archive paths, e.g.
  REPLACEMENT_ROOT/sound/windows/english(us)/ntm_adult_1_..._50496.wem
"""
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pamt import iter_game  # noqa: E402

MANIFEST = "manifest.json"


def fit_riff(new: bytes, size: int) -> bytes:
    """Pad a RIFF/WAVE file to exactly `size` bytes with a JUNK chunk."""
    if len(new) == size:
        return new
    extra = size - len(new)
    if extra < 0:
        raise ValueError(f"replacement is {-extra} bytes too big")
    # Wwise (and vgmstream) expect the data chunk to be the last chunk, so the
    # padding goes in a JUNK chunk *before* data, the way Wwise itself aligns
    # data. Chunks are word aligned, so the JUNK body must be even.
    i = new.find(b"data", 12)
    if extra >= 8 and (extra - 8) % 2 == 0 and i > 0:
        junk = b"JUNK" + struct.pack("<I", extra - 8) + b"\0" * (extra - 8)
        out = new[:i] + junk + new[i:]
        return out[:4] + struct.pack("<I", len(out) - 8) + out[8:]
    # Otherwise leave the RIFF untouched and zero-fill past its end.
    return new + b"\0" * extra


def patch(game: Path, repl: Path, backup: Path, dry: bool):
    wanted = {p.relative_to(repl).as_posix(): p for p in repl.rglob("*.wem")}
    backup.mkdir(parents=True, exist_ok=True)
    mpath = backup / MANIFEST
    manifest = json.loads(mpath.read_text()) if mpath.exists() else {}
    done = failed = 0
    for _folder, e in iter_game(game):
        src = wanted.pop(e.path, None)
        if src is None:
            continue
        if e.comp_size != e.orig_size or e.compression:
            print(f"SKIP compressed {e.path}")
            failed += 1
            continue
        try:
            data = fit_riff(src.read_bytes(), e.orig_size)
        except ValueError as ex:
            print(f"SKIP {e.path}: {ex}")
            failed += 1
            continue
        if dry:
            done += 1
            continue
        key = f"{e.paz_file}|{e.offset}"
        with open(e.paz_file, "r+b") as f:
            f.seek(e.offset)
            orig = f.read(e.orig_size)
            if key not in manifest:  # never overwrite the first (vanilla) backup
                bfile = backup / f"{len(manifest):06d}.bin"
                bfile.write_bytes(orig)
                manifest[key] = {"path": e.path, "paz": str(e.paz_file), "offset": e.offset,
                                 "size": e.orig_size, "backup": bfile.name}
                mpath.write_text(json.dumps(manifest, indent=1))
            f.seek(e.offset)
            f.write(data)
        done += 1
    for p in wanted:
        print(f"NOT FOUND in archives: {p}")
    print(f"patched {done}, skipped {failed}, missing {len(wanted)}{' (dry run)' if dry else ''}")


def restore(backup: Path):
    manifest = json.loads((backup / MANIFEST).read_text())
    for m in manifest.values():
        with open(m["paz"], "r+b") as f:
            f.seek(m["offset"])
            f.write((backup / m["backup"]).read_bytes())
    print(f"restored {len(manifest)} entries")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "patch":
        patch(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), "--dry-run" in sys.argv)
    elif cmd == "restore":
        restore(Path(sys.argv[3]))
    else:
        sys.exit(__doc__)
