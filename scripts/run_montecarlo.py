from loanlens.backtest import load_nifty
from loanlens.montecarlo import simulate_invest_vs_prepay

prices = load_nifty()
for years in (3, 5):
    for rate in (8, 10, 12, 14):
        r = simulate_invest_vs_prepay(prices, rate, years)
        print(f"{years}y, loan {rate}%: invest wins {r['prob_invest_wins']:.0f}% | "
              f"loss chance {r['prob_loss']:.0f}% | "
              f"5th/50th/95th pct return: {r['p5_pct']:.1f}% / {r['p50_pct']:.1f}% / {r['p95_pct']:.1f}%")