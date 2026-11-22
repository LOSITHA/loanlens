"""Score the Gemini reader on whatever offers it has already read (saved in outputs\\extraction_cache.json),
and score the rule-based reader on exactly the same offers, so the comparison is fair.
Makes NO Gemini calls, so it costs no quota.

Run from the project folder:
    $env:PYTHONPATH="src"
    python scripts\\score_partial.py
"""
import glob
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.dirname(__file__))

from confidence import wilson
from loanlens.regex_extractor import FIELDS, extract_offer_regex

TOL = {"annual_rate_pct": 0.01, "prepayment_penalty_pct": 0.01, "tenure_months": 0}
SETS = [("Synthetic", "data/offers_labelled"), ("Hard", "data/offers_hard"), ("Bank-style", "data/offers_kfs")]


def match(a, b, field):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= TOL.get(field, 1.0)


def score(pred, truth):
    return sum(match(pred.get(f), truth[f], f) for f in FIELDS)


def main():
    cache_path = os.path.join(ROOT, "outputs", "extraction_cache.json")
    cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}
    print(f"Saved Gemini readings found: {len(cache)}\n")
    rows = []
    for name, folder in SETS:
        paths = sorted(glob.glob(os.path.join(ROOT, folder, "*.txt")))
        done = [p for p in paths if os.path.basename(p) in cache]
        waiting = [os.path.basename(p) for p in paths if os.path.basename(p) not in cache]
        g = r = 0
        for p in done:
            truth = json.load(open(p.replace(".txt", ".json"), encoding="utf-8"))
            g += score(cache[os.path.basename(p)], truth)
            r += score(extract_offer_regex(open(p, encoding="utf-8").read()), truth)
        total = len(done) * len(FIELDS)
        print(f"{name}: Gemini has read {len(done)} of {len(paths)} offers")
        if done:
            _, glo, ghi = wilson(g, total)
            _, rlo, rhi = wilson(r, total)
            print(f"  Gemini      : {100 * g / total:.1f}% ({g}/{total} fields, range {glo * 100:.1f}% to {ghi * 100:.1f}%)")
            print(f"  Rules reader: {100 * r / total:.1f}% ({r}/{total} fields, range {rlo * 100:.1f}% to {rhi * 100:.1f}%)  <- same {len(done)} offers")
            rows.append((name, len(done), len(paths), g, r, total))
        if waiting:
            print(f"  Not read yet: {', '.join(waiting)}")
        print()
    print("Paste everything above into the chat.")


if __name__ == "__main__":
    main()
