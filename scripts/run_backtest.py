from loanlens.backtest import load_nifty, invest_beats_prepay

prices = load_nifty()
for years in (3, 5):
    for rate in (8, 10, 12, 14):
        r = invest_beats_prepay(prices, rate, years)
        print(f"{years}y window, loan {rate}%: invest wins {r['pct_invest_wins']:.0f}% "
              f"of {r['windows']} windows | median {r['median_return_pct']:.1f}% "
              f"| worst {r['worst_return_pct']:.1f}%")