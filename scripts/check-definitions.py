#!/usr/bin/env python3
"""Which playable words Apple's dictionary can't define — i.e. what definitions.json owes.

The app looks a word up with UIReferenceLibraryViewController, which reads
Apple's bundled dictionaries. macOS exposes the same corpus through
DictionaryServices, so this script stands in for the phone. The two platforms
ship slightly different dictionary sets, so treat a word listed here as a
candidate, not a certainty.

    python3 scripts/check-definitions.py            # Hexicon's pool (NYT answers)
    python3 scripts/check-definitions.py --full     # the whole 115k dictionary

Anything printed under MISSING needs an entry writing in definitions.json.
Run it after the daily prune, since a prune can admit words as well as drop them.
"""
import ctypes, ctypes.util, json, pathlib, sys
from ctypes import c_void_p, c_char_p, c_long, Structure

ROOT = pathlib.Path(__file__).resolve().parent.parent

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

kUTF8 = 0x08000100


def apple_defines(word: str) -> bool:
    s = cf.CFStringCreateWithCString(None, word.encode(), kUTF8)
    try:
        d = ds.DCSCopyTextDefinition(None, s, CFRange(0, cf.CFStringGetLength(s)))
        if d:
            cf.CFRelease(d)
            return True
        return False
    finally:
        cf.CFRelease(s)


full = "--full" in sys.argv
if full:
    pool = set(json.loads((ROOT / "words.json").read_text()))
    label = "full dictionary"
else:
    pool = {w.lower()
            for day in json.loads((ROOT / "nyt-bee.json").read_text()).values()
            for w in (day.get("a") or [])}
    label = "NYT-accepted (what a Hexicon board can ask for)"

ours = json.loads((ROOT / "definitions.json").read_text())
gaps = sorted(w for w in pool if not apple_defines(w))
missing = [w for w in gaps if w not in ours]
unused = sorted(set(ours) - set(gaps))

print(f"{label}: {len(pool)} words")
print(f"  no Apple entry : {len(gaps)}")
print(f"  covered by ours: {len(gaps) - len(missing)}")
print(f"  MISSING        : {len(missing)}")
for i in range(0, len(missing), 6):
    print("     " + "  ".join(f"{w:<14}" for w in missing[i:i + 6]))
if unused and not full:
    # Apple added an entry, or the prune dropped the word -- either way ours is dead weight.
    print(f"  now redundant  : {len(unused)}")
    for i in range(0, len(unused), 6):
        print("     " + "  ".join(f"{w:<14}" for w in unused[i:i + 6]))
