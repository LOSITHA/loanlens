import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from loanlens.backtest import load_nifty, invest_beats_prepay
from loanlens.montecarlo import simulate_invest_vs_prepay

prices = load_nifty()
rates = list(range(6, 19))

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
for ax, years in zip(axes, (3, 5)):
    hist = [invest_beats_prepay(prices, r, years)["pct_invest_wins"] for r in rates]
    mc = [simulate_invest_vs_prepay(prices, r, years)["prob_invest_wins"] for r in rates]
    ax.plot(rates, hist, marker="o", label="Historical windows")
    ax.plot(rates, mc, marker="s", linestyle="--", label="Monte Carlo")
    ax.axhline(50, color="grey", linewidth=0.8)
    ax.set_title(f"{years}-year horizon")
    ax.set_xlabel("Loan interest rate (%)")
    ax.grid(alpha=0.3)
axes[0].set_ylabel("Chance investing beats prepaying (%)")
axes[0].legend()
fig.suptitle("Prepay or invest? Nifty 50 vs loan rate")
fig.tight_layout()

os.makedirs("outputs", exist_ok=True)
fig.savefig("outputs/sensitivity.png", dpi=150)
print("Saved outputs/sensitivity.png")