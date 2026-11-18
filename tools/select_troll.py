"""Select Troll dialogue voice files from the index TSV.

A line is a Troll line when:
  * its voice type is ntm_/ntw_ (NPC troll male/female), or
  * it belongs to a speaker whose facial-animation clips are authored on a
    troll rig (character/motion/1_pc/{14_ptm,15_ptw,17_pttm}/99_*facial/).
    Every speaker group in the game uses exactly one rig, so the whole
    speaker group is taken.

usage: select_troll.py INDEX_TSV OUT_LIST [--langs english(us),korean,...]
"""
import re
import sys
from collections import Counter
from pathlib import Path

TROLL_RIGS = {"14_ptm", "15_ptw", "17_pttm"}
SHARED_SHOP_VOICES = {"unique_shop_smithy", "unique_shop_bank"}
FACE = re.compile(r"^character/motion/1_pc/(\d+_p[a-z]+)/99_(?:auto|ar)facial/[^/]+/(.+)\.paa$")
WEM = re.compile(r"^sound/windows/([^/]+)/([a-z][^/]*)\.wem$")


def speaker(name: str) -> str:
    """Speaker group of a line name: unique_<who>_... or unique_shop_<type>_..."""
    m = re.match(r"^(unique_shop_[a-z_]+?)_(?:aidialog|questdialog|funcnpc|memory|[a-z]+_\d{4})", name)
    if m:
        return m.group(1)
    m = re.match(r"^(unique_[a-z]+)_", name)
    if m:
        return m.group(1)
    return ""


def main():
    index, out = Path(sys.argv[1]), Path(sys.argv[2])
    langs = None
    if "--langs" in sys.argv:
        langs = set(sys.argv[sys.argv.index("--langs") + 1].split(","))
    paths = [l.split("\t")[1] for l in index.read_text(encoding="utf-8").splitlines()]

    face_rig = {}
    for p in paths:
        m = FACE.match(p)
        if m:
            face_rig.setdefault(m.group(2), set()).add(m.group(1))
    troll_names = {n for n, rigs in face_rig.items() if rigs & TROLL_RIGS}
    troll_speakers = {speaker(n) for n in troll_names} - {""}
    human_speakers = {speaker(n) for n, rigs in face_rig.items() if rigs - TROLL_RIGS} - {""}
    clash = troll_speakers & human_speakers
    if clash:
        print("WARNING speakers on both troll and non-troll rigs:", sorted(clash))
    troll_speakers -= clash
    # Generic shop voices shared by every shopkeeper of that type, whatever
    # their race (verified in game: human blacksmith Rhett uses "smithy").
    troll_speakers -= SHARED_SHOP_VOICES
    print("troll speakers:", sorted(troll_speakers))

    picked, why = [], Counter()
    for p in paths:
        m = WEM.match(p)
        if not m:
            continue
        lang, name = m.groups()
        if langs and lang not in langs:
            continue
        if speaker(name) in SHARED_SHOP_VOICES:
            continue
        if name.startswith(("ntm_", "ntw_")):
            why["ntm/ntw"] += 1
        elif speaker(name) in troll_speakers:
            why[speaker(name)] += 1
        elif name in troll_names:
            why["facial-match"] += 1
        else:
            continue
        picked.append(p)
    picked = sorted(set(picked))
    out.write_text("\n".join(picked) + "\n", encoding="utf-8")
    for k, v in why.most_common():
        print(f"{v:6d}  {k}")
    print(f"total {len(picked)}")


if __name__ == "__main__":
    main()
