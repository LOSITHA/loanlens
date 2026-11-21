"""Does the answer depend on the simulation settings? Rerun the Monte Carlo with different block
lengths and random seeds and see whether the verdict (invest / prepay / close call) ever changes.

Run from the project folder:   python scripts\\check_robustness.py
Writes outputs\\robustness.csv and prints a short summary.
"""
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from loanlens.backtest import invest_beats_prepay, load_nifty
from loanlens.montecarlo import simulate_invest_vs_prepay
from loanlens.verdict import _lean, effective_prepay_rate_pct

BLOCKS = [10, 21, 63]          # trading days kept together: about 2 weeks, 1 month, 3 months
SEEDS = [1, 2, 3, 4, 5]
RATES = [6, 8, 10, 12, 14, 16, 18, 22]
YEARS = [3, 5]
PENALTY = 0.0
N_SIMS = 5000


def main():
    prices = load_nifty(os.path.join(ROOT, "data", "nifty50.csv"))
    rows, header = [], "years  loan%  past%  " + "  ".join(f"blk{b:>2}" for b in BLOCKS) + "   seed-spread  verdict-stable"
    print(header)
    unstable = 0
    for years in YEARS:
        for rate in RATES:
            hurdle = effective_prepay_rate_pct(rate, PENALTY, years)
            past = invest_beats_prepay(prices, hurdle, years)["pct_invest_wins"]
            by_block = [simulate_invest_vs_prepay(prices, hurdle, years, N_SIMS, block=b, seed=42)["prob_invest_wins"]
                        for b in BLOCKS]
            by_seed = [simulate_invest_vs_prepay(prices, hurdle, years, N_SIMS, block=21, seed=s)["prob_invest_wins"]
                       for s in SEEDS]
            spread = max(by_seed) - min(by_seed)
            leans = {_lean(p) for p in by_block + by_seed}
            stable = len(leans) == 1
            unstable += not stable
            rows.append((years, rate, past, *by_block, spread, stable))
            print(f"{years:>5}  {rate:>5}  {past:>5.0f}  " + "  ".join(f"{p:>5.0f}" for p in by_block)
                  + f"   {spread:>10.1f}  {'yes' if stable else 'NO: ' + '/'.join(sorted(leans))}")
    os.makedirs(os.path.join(ROOT, "outputs"), exist_ok=True)
    out = os.path.join(ROOT, "outputs", "robustness.csv")
    with open(out, "w", encoding="utf-8") as f:
        f.write("years,loan_rate_pct,past_pct," + ",".join(f"mc_block_{b}" for b in BLOCKS) + ",seed_spread,verdict_stable\n")
        for r in rows:
            f.write(",".join(str(round(x, 2)) if isinstance(x, float) else str(x) for x in r) + "\n")
    worst = max(r[-2] for r in rows)
    print(f"\n{len(rows) - unstable} of {len(rows)} loan cases give the same verdict for every block length and seed.")
    print(f"Biggest change from reshuffling the random seed: {worst:.1f} percentage points.")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
