#!/usr/bin/env python3
"""Fetch the daily NYT Spelling Bee dataset (Adidev-Panday/nyt-games), rebuild
nyt-bee.json (per-day letters/center/answers), and union any new answer words
into words.json. Run daily by .github/workflows/update-nyt.yml."""
import json, os, sys, urllib.request
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
    TODAY = datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')
except Exception:
    TODAY = datetime.utcnow().strftime('%Y-%m-%d')

UPSTREAM = 'https://raw.githubusercontent.com/Adidev-Panday/nyt-games/main/data.json'

def main():
    # Cheap no-op: if today's puzzle is already in, don't download the 31MB source.
    # --force re-runs anyway, which is how a dictionary-rule change gets applied
    # to the whole archive instead of waiting for tomorrow's puzzle.
    if os.path.exists('nyt-bee.json') and '--force' not in sys.argv:
        try:
            if TODAY in json.load(open('nyt-bee.json')):
                print(f'Already have {TODAY}; nothing to do.')
                return
        except Exception:
            pass
    data = json.load(urllib.request.urlopen(UPSTREAM, timeout=180))
    bee = {}
    answers = set()
    for date, entry in data.items():
        sb = entry.get('spelling_bee') if isinstance(entry, dict) else None
        if not sb:
            continue
        c = (sb.get('center') or '').lower()
        outer = ''.join(sorted(l.lower() for l in (sb.get('letters') or [])))
        ans = [a.lower() for a in (sb.get('answers') or []) if a.isalpha()]
        if not c or len(outer) != 6 or not ans:
            continue
        bee[date] = {'c': c, 'l': ''.join(sorted(set(c + outer))), 'a': ans}
        answers.update(a for a in ans if len(a) >= 4)
    json.dump(bee, open('nyt-bee.json', 'w'), separators=(',', ':'), sort_keys=True)

    words = set(json.load(open('words.json'))) if os.path.exists('words.json') else set()
    # ADD: every real NYT answer word (authoritative)
    words |= {w for w in answers if w.isalpha() and len(w) >= 4}
    # PRUNE (safe): a NYT day publishes the COMPLETE valid list, so a word buildable
    # from that day's letters but absent from its answers is one NYT rejects — drop it.
    # Never drop a word NYT has EVER accepted, so an occasional incomplete source
    # day can't delete a good word. Only the recent window is re-checked each run
    # (older days are handled on the day they first landed).
    #
    # NB: this used to also protect everything in common-words.json. That list is
    # a 46k alphabetical word list, not a frequency ranking, and it shelters
    # proper nouns and obscure junk (amazonian, moai, noni, lido, dido, wank...),
    # which inflated a board's maximum and therefore its Genius target above NYT's.
    # Every word the protection was added for (yard, data, tidy, defund, unfound,
    # confound, dart, uncuffed) is in NYT's own answers, so it's fully covered.
    # Sweep EVERY day, not just a recent window. The window assumed each day is
    # checked while it's fresh, but words keep entering the dictionary from later
    # days' answers, so a word NYT rejected in 2023 could be re-added in 2026 and
    # never re-examined. A full sweep costs a few seconds and can't drift.
    protected = set(answers)

    def bases(w):
        """Plausible base forms of an inflected answer."""
        for suf, add in (('ing', ''), ('ing', 'e'), ('ed', ''), ('ed', 'e'),
                         ('s', ''), ('es', '')):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                stem = w[:-len(suf)]
                yield stem + add
                if len(stem) > 3 and stem[-1] == stem[-2]:   # filling -> fill, not fil
                    yield stem[:-1] + add

    def incomplete(letters, c, ans):
        """A day is only usable as evidence if its answer list is COMPLETE, and a
        list that accepts a word but not that word's base is missing entries --
        NYT's dictionary is closed under inflection, so the source is at fault,
        not NYT. Caught 2024-11-28, which accepts 'filching' but lists neither
        'filch' nor 'finch' nor 'flinch'; without this the prune ate all three.
        Eight days out of 1302 fail this, and skipping them costs almost nothing
        because a genuinely rejected word is nearly always rejected again."""
        for w in ans:
            for b in bases(w):
                if (len(b) >= 4 and b not in ans and b in words
                        and c in b and all(ch in letters for ch in b)):
                    return True
        return False

    remove = set()
    for date in sorted(bee.keys()):
        d = bee[date]
        letters, c, ans = set(d['l']), d['c'], set(d['a'])
        if len(letters) != 7 or c not in letters or len(ans) < 15:
            continue
        if not any(set(w) == letters for w in ans):   # sanity: must contain a pangram
            continue
        if incomplete(letters, c, ans):
            continue
        constructible = {w for w in words if len(w) >= 4 and c in w and all(ch in letters for ch in w)}
        remove |= (constructible - ans - protected)
    words -= remove

    json.dump(sorted(words), open('words.json', 'w'), separators=(',', ':'))
    print(f'nyt-bee.json: {len(bee)} days; words.json: {len(words)} words (pruned {len(remove)})')

if __name__ == '__main__':
    main()
