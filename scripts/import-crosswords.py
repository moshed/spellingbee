#!/usr/bin/env python3
"""Rebuild crosswords/ from doshea/nyt_crosswords, which publishes the grids.

Our archive was built the hard way: a clue-only dataset with the grids solved
back out of it. That capped us at 5,597 puzzles from 2000, left 114 with
unchecked squares unsolvable, and reduced rebus squares to guesswork. This
source has 14,547 puzzles from 1976 with the grids as published — a superset of
what we had, verified identical on every date we could compare.

Writes our own compact format, so the site and app need no changes:
    {date, rows, cols, grid:[str], across:[{n,c,a}], down:[{n,c,a}]}
A '#' is a block. Rebus squares hold their full string in the grid list, which
is why grid rows are lists of cells, not one string, when any cell is multi-char.
"""
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

RAW  = "https://raw.githubusercontent.com/doshea/nyt_crosswords/master/"
TREE = "https://api.github.com/repos/doshea/nyt_crosswords/git/trees/master?recursive=1"
OUT  = "crosswords"
UA   = {"User-Agent": "wordbox-import"}

def paths():
    req = urllib.request.Request(TREE, headers=UA)
    t = json.load(urllib.request.urlopen(req, timeout=120))
    import re
    return sorted(b["path"] for b in t["tree"]
                  if b["type"] == "blob" and re.fullmatch(r"\d{4}/\d{2}/\d{2}\.json", b["path"]))

def convert(d):
    size = d.get("size") or {}
    rows, cols = size.get("rows"), size.get("cols")
    cells = d.get("grid") or []
    if not rows or not cols or len(cells) != rows * cols:
        return None
    # A block is "."; everything else is the answer letter(s) for that square.
    grid = []
    for r in range(rows):
        row = [("#" if c == "." else c) for c in cells[r * cols:(r + 1) * cols]]
        # keep the compact string form when every square is a single character,
        # which is all but a handful of rebus puzzles
        grid.append("".join(row) if all(len(x) == 1 for x in row) else row)

    def side(which):
        clues = ((d.get("clues") or {}).get(which)) or []
        answers = ((d.get("answers") or {}).get(which)) or []
        out = []
        for i, raw in enumerate(clues):
            # "12. Clue text" — the number is part of the string in this format
            num, _, text = raw.partition(".")
            try: n = int(num.strip())
            except ValueError: continue
            out.append({"n": n, "c": text.strip(),
                        "a": answers[i] if i < len(answers) else ""})
        return out

    across, down = side("across"), side("down")
    if not across or not down:
        return None
    p = {"date": d.get("date", "").strip(), "rows": rows, "cols": cols,
         "grid": grid, "across": across, "down": down}
    # extras our own reconstruction could never recover
    if d.get("circles"):  p["circles"] = d["circles"]
    if d.get("notepad"):  p["notepad"] = d["notepad"]
    if d.get("title"):    p["title"] = d["title"]
    if d.get("author"):   p["author"] = d["author"]
    if d.get("dow"):      p["dow"] = d["dow"]
    return p

def iso(path):        # 1976/01/01.json -> 1976-01-01
    return f"{path[:4]}-{path[5:7]}-{path[8:10]}"

def fetch(path, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(RAW + path, headers=UA)
            return json.load(urllib.request.urlopen(req, timeout=45))
        except Exception:
            if attempt == tries - 1: return None
            time.sleep(1.5 * (attempt + 1))

def main():
    os.makedirs(OUT, exist_ok=True)
    todo = paths()
    print(f"{len(todo)} puzzles upstream")
    written = skipped = failed = 0
    lock_msgs = []

    def one(path):
        nonlocal written, skipped, failed
        date = iso(path)
        d = fetch(path)
        if d is None:
            failed += 1; lock_msgs.append(f"fetch failed {date}"); return
        p = convert(d)
        if p is None:
            failed += 1; lock_msgs.append(f"unusable {date}"); return
        p["date"] = date
        with open(os.path.join(OUT, f"{date}.json"), "w") as f:
            json.dump(p, f, separators=(",", ":"))
        written += 1

    with ThreadPoolExecutor(max_workers=12) as pool:
        for i, _ in enumerate(pool.map(one, todo), 1):
            if i % 1000 == 0:
                print(f"  {i}/{len(todo)}  written {written}  failed {failed}", flush=True)

    # index the lot
    puzzles = []
    for name in sorted(os.listdir(OUT)):
        if not name.endswith(".json") or name == "index.json": continue
        p = json.load(open(os.path.join(OUT, name)))
        puzzles.append({"d": p["date"], "r": p["rows"], "c": p["cols"],
                        "n": len(p["across"]) + len(p["down"])})
    json.dump({"count": len(puzzles), "puzzles": puzzles},
              open(os.path.join(OUT, "index.json"), "w"), separators=(",", ":"))
    print(f"done: {written} written, {failed} failed, index has {len(puzzles)}")
    for m in lock_msgs[:15]: print("   ", m)

if __name__ == "__main__":
    main()
