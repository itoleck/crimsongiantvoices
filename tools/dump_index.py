"""Dump every archive entry to a TSV so we can grep it."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pamt import iter_game  # noqa: E402

game = Path(sys.argv[1])
out = Path(sys.argv[2])
exts = Counter()
with out.open("w", encoding="utf-8") as f:
    for folder, e in iter_game(game):
        exts[Path(e.path).suffix.lower()] += 1
        f.write(f"{folder}\t{e.path}\t{e.paz_index}\t{e.offset}\t{e.comp_size}\t{e.orig_size}\t{e.flags:06x}\n")
for k, v in exts.most_common(40):
    print(f"{k or '<none>'}\t{v}")
