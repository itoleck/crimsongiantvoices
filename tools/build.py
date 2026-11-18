"""Build pitch-shifted Troll voice WEMs.

Pipeline per file:
  extract original WEM -> vgmstream-cli to WAV -> ffmpeg rubberband
  (pitch x0.25 = -24 semitones, duration kept) -> Wwise Vorbis encode
  -> must be no bigger than the original (in-place patching), so files
  that come out too big are re-encoded at lower Vorbis quality.

usage: build.py SELECTION_LIST WORK_DIR [--limit N]
Environment/paths are set in CONFIG below.
"""
import argparse
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract import read_entry  # noqa: E402
from pamt import iter_game  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG = {
    "game": Path(r"C:\Program Files (x86)\Steam\steamapps\common\Crimson Desert"),
    "ffmpeg": Path(r"ffmpeg.exe"),
    "vgmstream": ROOT / "bin" / "vgmstream" / "vgmstream-cli.exe",
    "wwise": Path(r"WwiseConsole.exe"),
    "wproj": ROOT / "wwise" / "CGV" / "CGV.wproj",
    # -4 semitones. Tried in game: -24 unintelligible, -12 too low and hard
    # to understand, -6 a little too deep.
    "pitch": 2 ** (-4 / 12),
}
# Tried in order until the result fits in the original's space.
QUALITIES = ["Vorbis Quality High", "Vorbis Quality Medium", "Vorbis Quality Low"]


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed: {r.stderr[-500:] or r.stdout[-500:]}")
    return r


def flat(path: str) -> str:
    return re.sub(r"[\\/()]", "_", path)


def encode(wavs: dict, quality: str, work: Path) -> Path:
    src_dir = work / "wav_pitched"
    out = work / f"enc_{quality.split()[-1].lower()}"
    lst = work / f"list_{quality.split()[-1].lower()}.wsources"
    rows = "\n".join(f'  <Source Path="{w.name}" Conversion="{quality}"/>' for w in wavs.values())
    lst.write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n'
                   f'<ExternalSourcesList SchemaVersion="1" Root="{src_dir}">\n{rows}\n'
                   f'</ExternalSourcesList>\n', encoding="utf-8")
    run([CONFIG["wwise"], "convert-external-source", CONFIG["wproj"], "--source-file", lst,
         "--output", out, "--platform", "Windows", "--quiet"])
    return out / "Windows"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("selection")
    ap.add_argument("work")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    work = Path(a.work).resolve()
    want = [l.strip() for l in open(a.selection, encoding="utf-8-sig") if l.strip()]
    if a.limit:
        want = want[:a.limit]
    want_set = set(want)
    for d in ("orig", "wav", "wav_pitched"):
        (work / d).mkdir(parents=True, exist_ok=True)

    entries = {e.path: e for _f, e in iter_game(CONFIG["game"]) if e.path in want_set}
    print(f"found {len(entries)}/{len(want)} in archives")

    def prep(path):
        e = entries[path]
        name = flat(path)
        o = work / "orig" / (name + ".wem")
        if not o.exists():
            o.write_bytes(read_entry(e))
        w = work / "wav" / (name + ".wav")
        if not w.exists():
            run([CONFIG["vgmstream"], "-o", w, o])
        pw = work / "wav_pitched" / (name + ".wav")
        if not pw.exists():
            run([CONFIG["ffmpeg"], "-hide_banner", "-loglevel", "error", "-y", "-i", w,
                 "-af", f"rubberband=pitch={CONFIG['pitch']}:formant=shifted:transients=smooth",
                 "-c:a", "pcm_s16le", pw])  # keep the source sample rate
        return path, pw

    with ThreadPoolExecutor(12) as ex:
        wavs = dict(ex.map(prep, entries))
    print(f"pitched {len(wavs)}")

    final = work / "replacements"
    remaining = dict(wavs)
    for q in QUALITIES:
        if not remaining:
            break
        outdir = encode(remaining, q, work)
        for path in list(remaining):
            wem = outdir / (flat(path) + ".wem")
            if wem.exists() and wem.stat().st_size + 8 <= entries[path].orig_size or \
                    wem.exists() and wem.stat().st_size == entries[path].orig_size:
                dst = final / path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(wem, dst)
                del remaining[path]
        print(f"{q}: {len(wavs) - len(remaining)} fit so far")
    for p in remaining:
        print(f"DOES NOT FIT: {p}")
    print(f"done: {len(wavs) - len(remaining)} replacements in {final}")


if __name__ == "__main__":
    main()
