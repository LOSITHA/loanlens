from loanlens.backtest import load_nifty
from loanlens.verdict import verdict

prices = load_nifty()
for penalty in (0, 4):
    print(f"\n5-year horizon, prepayment penalty {penalty}%")
    for rate in (8, 10, 11, 12, 13, 14, 16):
        v = verdict(prices, rate, 5, penalty_pct=penalty)
        print(f"  loan {rate:>2}% -> hurdle {v['hurdle_pct']:.1f}% | "
              f"hist {v['hist_invest_wins_pct']:.0f}% | MC {v['mc_invest_wins_pct']:.0f}% | {v['label']}")