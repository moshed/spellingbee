#!/usr/bin/env python3
"""Back-test the definition pipeline without anyone playing a board.

The pipeline, in order:
  1. is the word rare enough to be worth defining at all?   (wordfreq Zipf)
  2. does Apple's dictionary have it?                       -> use that, stop
  3. otherwise ask wow-define, which asks Grok              -> structured JSON
  4. mark our stored definition against Grok's, and only
     accept above a confidence threshold

Steps 1 and 2 run locally. Step 3 goes through the edge function so the key
stays a server-side secret.

    python3 scripts/backtest-definitions.py --board          # the last board played
    python3 scripts/backtest-definitions.py --gaps           # all 183 in definitions.json
    python3 scripts/backtest-definitions.py --gaps --limit 20
    python3 scripts/backtest-definitions.py --control        # planted wrong definitions

--control is the one that proves the grader works. Marking only correct
definitions tells you nothing: a grader that says "match" to everything scores
100%. It feeds Grok deliberately wrong definitions and fails the run if they
aren't caught.
"""
import argparse, ctypes, ctypes.util, json, os, pathlib, random, sys, urllib.request
from ctypes import c_void_p, c_char_p, c_long, Structure

ROOT = pathlib.Path(__file__).resolve().parent.parent
FN = "https://atqhfbaurrmivjarowco.supabase.co/functions/v1/wow-define"

# Rarity below which a word is worth offering a definition for. 2.5 puts it at
# roughly "most people would not use this word" -- on a real board it selected
# 3 words out of 26, which is the point: defining `then` and `enough` is noise.
RARE_BELOW = 2.5

# ---------- Apple's dictionary (same corpus the app reads on the phone) -------
cf = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
ds = ctypes.CDLL("/System/Library/Frameworks/CoreServices.framework/CoreServices")


class CFRange(Structure):
    _fields_ = [("location", c_long), ("length", c_long)]


cf.CFStringCreateWithCString.restype = c_void_p
cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, ctypes.c_uint32]
cf.CFRelease.argtypes = [c_void_p]
cf.CFStringGetLength.restype = c_long
cf.CFStringGetLength.argtypes = [c_void_p]
ds.DCSCopyTextDefinition.restype = c_void_p
ds.DCSCopyTextDefinition.argtypes = [c_void_p, c_void_p, CFRange]


def apple_defines(word):
    s = cf.CFStringCreateWithCString(None, word.encode(), 0x08000100)
    try:
        d = ds.DCSCopyTextDefinition(None, s, CFRange(0, cf.CFStringGetLength(s)))
        if d:
            cf.CFRelease(d)
            return True
        return False
    finally:
        cf.CFRelease(s)


# ---------- the edge function -------------------------------------------------
def ask(word, candidate, anon):
    payload = json.dumps({"word": word, "candidate": candidate}).encode()
    req = urllib.request.Request(FN, data=payload, headers={
        "Content-Type": "application/json",
        "apikey": anon,
        "Authorization": f"Bearer {anon}",
    })
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "detail": e.read().decode()[:300]}
    except Exception as e:
        return {"error": type(e).__name__, "detail": str(e)[:300]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", action="store_true", help="the last board played")
    ap.add_argument("--gaps", action="store_true", help="every word in definitions.json")
    ap.add_argument("--control", action="store_true", help="plant wrong definitions and check they're caught")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    anon = os.environ.get("SB_ANON_KEY", "")
    if not anon:
        sys.exit("set SB_ANON_KEY (the Misc project anon key) first")

    from wordfreq import zipf_frequency as z
    ours = json.loads((ROOT / "definitions.json").read_text())

    if args.board:
        words = json.loads(pathlib.Path("board_words.json").read_text())
    elif args.gaps or args.control:
        words = sorted(ours)
    else:
        sys.exit("pick --board, --gaps or --control")

    if args.limit:
        words = words[:args.limit]

    # ---- steps 1 and 2, local and free -------------------------------------
    triage = []
    for w in words:
        zipf = z(w, "en")
        triage.append({
            "word": w,
            "zipf": zipf,
            "rare": zipf < RARE_BELOW,
            "apple": apple_defines(w),
        })

    rare = [t for t in triage if t["rare"]]
    need_fallback = [t for t in rare if not t["apple"]]
    print(f"{len(words)} words")
    print(f"  rare enough to define (Zipf < {RARE_BELOW}): {len(rare)}")
    print(f"  ...of those, Apple already has:             {len(rare) - len(need_fallback)}")
    print(f"  ...needing the Grok fallback:               {len(need_fallback)}\n")

    # ---- step 3 and 4, through the edge function ---------------------------
    # In control mode every word is sent with a definition belonging to a
    # DIFFERENT word. Anything the grader calls a match is a false positive, and
    # a grader that can't fail is not a grader.
    rng = random.Random(7)
    checks = need_fallback if not args.control else triage
    if not checks:
        print("nothing to send")
        return

    stats = {"match": 0, "partial": 0, "mismatch": 0, "not_a_word": 0,
             "no_candidate": 0, "error": 0, "unusable": 0}
    misses = []
    for t in checks:
        w = t["word"]
        if args.control:
            other = rng.choice([x for x in ours if x != w])
            candidate = ours[other]
        else:
            candidate = ours.get(w, "")

        r = ask(w, candidate, anon)
        if "error" in r:
            stats["error"] += 1
            print(f"  {w:<14} ERROR {r['error']} {r.get('detail','')[:120]}")
            continue
        stats[r["verdict"]] = stats.get(r["verdict"], 0) + 1
        if not r.get("usable"):
            stats["unusable"] += 1
        flag = ""
        if args.control and r["verdict"] == "match":
            flag = "  <-- FALSE POSITIVE"
            misses.append(w)
        print(f"  {w:<14} conf={r['confidence']:.2f} agree={r['agreement']:.2f} "
              f"{r['verdict']:<11}{flag}")
        if r.get("note"):
            print(f"      note: {r['note']}")

    print("\n" + json.dumps(stats, indent=1))
    if args.control:
        if misses:
            print(f"\nFAIL: grader accepted {len(misses)} wrong definitions: {misses}")
            sys.exit(1)
        print("\nPASS: every planted wrong definition was caught")


if __name__ == "__main__":
    main()
