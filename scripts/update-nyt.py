#!/usr/bin/env python3
"""Fetch the daily NYT Spelling Bee dataset (Adidev-Panday/nyt-games), rebuild
nyt-bee.json (per-day letters/center/answers), and union any new answer words
into words.json. Run daily by .github/workflows/update-nyt.yml."""
import json, os, urllib.request
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
    TODAY = datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')
except Exception:
    TODAY = datetime.utcnow().strftime('%Y-%m-%d')

UPSTREAM = 'https://raw.githubusercontent.com/Adidev-Panday/nyt-games/main/data.json'

def main():
    # Cheap no-op: if today's puzzle is already in, don't download the 31MB source.
    if os.path.exists('nyt-bee.json'):
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
    # But never drop a common word (common-words.json) or any word NYT ever accepted,
    # so an occasional incomplete source day can't delete a good word. Only the recent
    # window is re-checked each run (older days handled on the day they first landed).
    common = set(json.load(open('common-words.json'))) if os.path.exists('common-words.json') else set()
    protected = common | {a for a in answers}
    recent = sorted(bee.keys())[-30:]
    remove = set()
    for date in recent:
        d = bee[date]
        letters, c, ans = set(d['l']), d['c'], set(d['a'])
        if len(letters) != 7 or c not in letters or len(ans) < 15:
            continue
        if not any(set(w) == letters for w in ans):   # sanity: must contain a pangram
            continue
        constructible = {w for w in words if len(w) >= 4 and c in w and all(ch in letters for ch in w)}
        remove |= (constructible - ans - protected)
    words -= remove

    json.dump(sorted(words), open('words.json', 'w'), separators=(',', ':'))
    print(f'nyt-bee.json: {len(bee)} days; words.json: {len(words)} words (pruned {len(remove)})')

if __name__ == '__main__':
    main()
