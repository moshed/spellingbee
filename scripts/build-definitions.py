#!/usr/bin/env python3
"""Build definitions.json — the source of truth for the define-to-score marker.

The model must NOT invent the reference. It marks a player's answer against a
real dictionary; deciding what the word means is not its job. An earlier version
let it supply the definition and it said coatis were "of the weasel family"
about one call in four (they are raccoon family), with the text shown to the
player as fact.

Sources, in order of authority:
  1. hand-written  — the 183 checked by hand for words Apple's dictionary lacks
  2. WordNet       — Princeton, public domain, offline, ~75% of challenged words

Words with no entry from either are simply NOT challenged: no reference, no
gate, points given. That is better than gating on a definition nobody verified.

    pip3 install nltk wordfreq && python3 scripts/build-definitions.py
"""
import json, pathlib, sys
import nltk
nltk.download("wordnet", quiet=True)
from nltk.corpus import wordnet as wn

ROOT = pathlib.Path(__file__).resolve().parent.parent


def tidy(d):
    d = d.split(";")[0].strip()
    return (d[0].upper() + d[1:] + ".") if d else None


def wordnet_senses(w):
    """EVERY sense, not just the first.

    Marking against sense one alone refuses players who know a different real
    meaning. `suer` is WordNet's "a man who courts a woman" first and "someone
    who petitions a court" second, so "the person suing you" -- plainly correct
    -- scored zero. Same for `vitiating`, whose second sense is "make
    imperfect".

    Capped at four: past that they get obscure enough that accepting them would
    let a vague answer match something nobody meant.
    """
    ss = wn.synsets(w)
    if not ss:
        for pos in "nvar":
            b = wn.morphy(w, pos)
            if b and (ss := wn.synsets(b)):
                break
    out, seen = [], set()
    for syn in ss[:4]:
        d = tidy(syn.definition())
        if d and d.lower() not in seen:
            seen.add(d.lower())
            out.append(d)
    return out or None


hand = json.loads((ROOT / "hand-definitions.json").read_text())
hard = json.loads((ROOT / "hard-words.json").read_text())

out, stats = {}, {"hand-written": 0, "wordnet": 0, "none": 0}
for w in hard:
    if w in hand:
        out[w] = {"d": hand[w], "s": "h", "all": [hand[w]]}
        stats["hand-written"] += 1
    elif (ds := wordnet_senses(w)):
        # first sense is what the player is shown; all of them are what the
        # answer is marked against
        out[w] = {"d": ds[0], "s": "w", "all": ds}
        stats["wordnet"] += 1
    else:
        stats["none"] += 1

# hand-written entries that aren't in the hard list still belong -- they were
# built from the words Apple can't define, which is a different cut
for w, d in hand.items():
    out.setdefault(w, {"d": d, "s": "h", "all": [d]})

(ROOT / "definitions.json").write_text(json.dumps(out, separators=(",", ":"), sort_keys=True))
size = (ROOT / "definitions.json").stat().st_size / 1024 / 1024
print(f"{len(out)} definitions, {size:.1f} MB")
for k, v in stats.items():
    print(f"  {k}: {v}")
print(f"\n{stats['none']} hard words have no verified definition -- those are never challenged.")
