#!/usr/bin/env python3
"""Fetch the daily NYT Spelling Bee dataset (Adidev-Panday/nyt-games), rebuild
nyt-bee.json (per-day letters/center/answers), and union any new answer words
into words.json. Run daily by .github/workflows/update-nyt.yml."""
import json, os, urllib.request

UPSTREAM = 'https://raw.githubusercontent.com/Adidev-Panday/nyt-games/main/data.json'

def main():
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
    merged = sorted(words | {w for w in answers if w.isalpha() and len(w) >= 4})
    json.dump(merged, open('words.json', 'w'), separators=(',', ':'))
    print(f'nyt-bee.json: {len(bee)} days; words.json: {len(merged)} words')

if __name__ == '__main__':
    main()
