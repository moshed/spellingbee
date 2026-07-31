#!/usr/bin/env python3
"""Back-test the define-to-score marker, with nobody playing.

The mechanic: find a rare word, and the points are held until you say what it
means. This checks the marker would behave, using simulated player answers so it
can run before anyone types anything.

Four kinds of answer are sent for each word:

  good    a correct definition, loosely worded  -> must be AWARDED
  vague   right area, wrong sense               -> either way, but recorded
  wrong   a definition of a DIFFERENT word      -> must be REFUSED
  blank   nothing at all                        -> must be REFUSED

`wrong` and `blank` are the ones that matter. A marker that awards everything
scores 100% on correct answers alone, so a run that only sends good answers
proves nothing. The exit code fails on any false positive.

    export SB_ANON_KEY=...
    python3 scripts/backtest-definitions.py --board board_words.json
    python3 scripts/backtest-definitions.py --sample 12
"""
import argparse, json, os, pathlib, random, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
FN = "https://atqhfbaurrmivjarowco.supabase.co/functions/v1/wow-define"
RARE_BELOW = 2.5


def ask(word, answer, reference, anon):
    payload = {"word": word, "answer": answer}
    if reference:
        payload["reference"] = reference
    req = urllib.request.Request(FN, data=json.dumps(payload).encode(), headers={
        "Content-Type": "application/json", "apikey": anon,
        "Authorization": f"Bearer {anon}"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "detail": e.read().decode()[:200]}
    except Exception as e:
        return {"error": type(e).__name__, "detail": str(e)[:200]}


def loosen(definition):
    """Approximate how a player types: the gist, lowercase, no full stop."""
    d = definition.split(";")[0].split(",")[0].strip().rstrip(".")
    return d[0].lower() + d[1:] if d else d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", help="JSON array of words from a played board")
    ap.add_argument("--sample", type=int, default=0, help="N random words from definitions.json")
    args = ap.parse_args()

    anon = os.environ.get("SB_ANON_KEY", "")
    if not anon:
        sys.exit("set SB_ANON_KEY first")

    from wordfreq import zipf_frequency as z
    ours = json.loads((ROOT / "definitions.json").read_text())
    rng = random.Random(11)

    if args.board:
        words = json.loads(pathlib.Path(args.board).read_text())
        rare = [w for w in words if z(w, "en") < RARE_BELOW]
        print(f"{len(words)} words on the board, {len(rare)} rare enough to challenge:")
        print("  " + "  ".join(rare) + "\n")
        # the board's rare words mostly aren't in definitions.json (Apple has
        # them), so there's no stored reference -- the model supplies its own
        subjects = [(w, ours.get(w)) for w in rare]
    elif args.sample:
        picks = rng.sample(sorted(ours), min(args.sample, len(ours)))
        subjects = [(w, ours[w]) for w in picks]
    else:
        sys.exit("pick --board or --sample")

    if not subjects:
        print("nothing to test")
        return

    tally = {"good_awarded": 0, "good_refused": 0,
             "wrong_awarded": 0, "wrong_refused": 0,
             "blank_awarded": 0, "blank_refused": 0,
             "vague_awarded": 0, "vague_refused": 0, "errors": 0}
    false_positives = []

    for word, ref in subjects:
        # A correct answer needs SOME source of truth. Where we have no stored
        # definition, ask the marker for its own first and paraphrase that --
        # otherwise "good" would just be a guess and the test would be measuring
        # my guess, not the marker.
        seed = ref
        if not seed:
            probe = ask(word, "", None, anon)
            seed = probe.get("reference", "") if "error" not in probe else ""

        other = ours[rng.choice([k for k in ours if k != word])]
        cases = [("good", loosen(seed) if seed else None),
                 ("vague", "something to do with " + word[:4] if seed else None),
                 ("wrong", other),
                 ("blank", "")]

        print(f"{word}")
        for kind, answer in cases:
            if answer is None:
                print(f"    {kind:<6} skipped (no reference available)")
                continue
            r = ask(word, answer, ref, anon)
            if "error" in r:
                tally["errors"] += 1
                print(f"    {kind:<6} ERROR {r['error']} {r.get('detail','')[:100]}")
                continue
            awarded = bool(r.get("awarded"))
            tally[f"{kind}_{'awarded' if awarded else 'refused'}"] += 1
            flag = ""
            if kind in ("wrong", "blank") and awarded and r.get("verdict") != "unmarked":
                flag = "   <-- FALSE POSITIVE"
                false_positives.append((word, kind))
            if kind == "good" and not awarded:
                flag = "   <-- false negative"
            print(f"    {kind:<6} score={r.get('score', 0):.2f} "
                  f"{r.get('verdict','?'):<12}{'AWARDED' if awarded else 'refused':<8}{flag}")

    print("\n" + json.dumps(tally, indent=1))
    if false_positives:
        print(f"\nFAIL: {len(false_positives)} wrong/blank answers were awarded: {false_positives}")
        sys.exit(1)
    if tally["errors"]:
        print("\nINCONCLUSIVE: errors occurred; a clean run is needed before trusting this")
        sys.exit(2)
    print("\nPASS: no wrong or blank answer earned points")


if __name__ == "__main__":
    main()
