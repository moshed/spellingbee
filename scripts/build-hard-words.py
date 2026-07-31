#!/usr/bin/env python3
"""Generate hard-words.json — the words a player must define to score.

Rarity, not dictionary coverage, decides. Apple defines 88-95% of even the
rarest words, so "can we define it" says nothing about whether the player needs
to prove they know it.

Zipf frequency, from the `wordfreq` corpus: 7 is `the`, 4 is roughly one in ten
thousand, 0 is unattested. Under 2.5 reads as "most people would not use this
word". That takes 69% of the DICTIONARY, which sounds far too aggressive until
you notice the dictionary is mostly words nobody plays — on a real board
(HEGNOTU) it selected 3 of the 26 words actually found.

    pip3 install wordfreq && python3 scripts/build-hard-words.py
"""
import json, pathlib
from wordfreq import zipf_frequency as z

ROOT = pathlib.Path(__file__).resolve().parent.parent
THRESHOLD = 2.5

words = json.loads((ROOT / "words.json").read_text())
hard = sorted(w for w in words if z(w, "en") < THRESHOLD)
(ROOT / "hard-words.json").write_text(json.dumps(hard, separators=(",", ":")))

nyt = {w.lower() for d in json.loads((ROOT / "nyt-bee.json").read_text()).values()
       for w in (d.get("a") or [])}
print(f"Zipf < {THRESHOLD}")
print(f"  {len(hard)} of {len(words)} dictionary words")
print(f"  {sum(1 for w in nyt if z(w,'en') < THRESHOLD)} of {len(nyt)} reachable on a Hexicon board")
print(f"  wrote hard-words.json ({(ROOT/'hard-words.json').stat().st_size/1024:.0f} KB)")
print("\nCopy it into the app:")
print("  cp hard-words.json '/Users/moshe/Apps/World of Words/World of Words/Resources/'")
