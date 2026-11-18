# Crimson Desert Troll Voices

A Crimson Desert mod that drops every Troll voice 4 semitones (pitch
x0.794) while keeping each line's length, so lip-sync and subtitles still
match. English voice-over only. Change `pitch` in `tools/build.py` to adjust.

Covers 3,960 English files:

- 3,306 dialogue lines: generic trolls (`ntm_*` voice types), the named
  trolls Brollam, Darkmazzul, Grimrick, Grundir, Karzul, Octavius,
  Raging Tempest, Ravok and Vargus, and the troll trader, provost and
  contribution shopkeepers.
- 654 grunts and combat efforts (Wwise banks `vce_effort_ntm_adult_1..7`).

Shared shopkeeper voices (`unique_shop_smithy`, `unique_shop_bank`) are left
alone: they are also used by human NPCs such as the blacksmith Rhett.

## How it installs

Since game 2.04 the archive list (`meta/0.papgt`) is signed and the game will
not start if it is rewritten, so mod managers cannot install mods. This mod
writes each new WEM over the original inside the `.paz` archive, at the same
offset and exactly the same size (padded with a RIFF `JUNK` chunk before
`data`). No index or archive list is touched. Tested working on game build
26636972 (exe 1.0.0.3663).

## Requirements

- Python 3.12 with a venv: `python -m venv .venv` then
  `.venv\Scripts\pip install lz4 cryptography`
- ffmpeg with rubberband (gyan.dev full build)
- vgmstream-cli in `bin\vgmstream\`
- Wwise 2026.1 (WwiseConsole) and the conversion project in `wwise\CGV`

Paths are set in `CONFIG` in `tools/build.py`.

## Rebuild and install

```powershell
# 1. index the archives and pick the Troll voices
.venv\Scripts\python tools\dump_index.py "<game>" .claude\scratch\index.tsv
.venv\Scripts\python tools\select_troll.py .claude\scratch\index.tsv .claude\scratch\troll_dialogue.txt --langs "english(us)"
#    effort sounds: tools\bank_sources.py (see selection\troll_voices_english.txt)

# 2. decode, pitch shift, re-encode
.venv\Scripts\python tools\build.py selection\troll_voices_english.txt work\full_m4

# 3. patch the game (saves vanilla bytes to backups\full first)
.venv\Scripts\python tools\patch_inplace.py patch "<game>" work\full_m4\replacements backups\full
```

## Uninstall

```powershell
.venv\Scripts\python tools\patch_inplace.py restore "<game>" backups\full
```

Or use Steam's "Verify integrity of game files". A game update may also
overwrite the patched archives; re-run steps 1 to 3 afterwards.

## Credits

PAZ crypto from lazorr410/crimson-desert-unpacker (MIT). 2.04+ PAMT layout
from the CDUMM community (faisalkindi/CrimsonDesert-UltimateModsManager #458).
