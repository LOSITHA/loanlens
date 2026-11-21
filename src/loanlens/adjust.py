"""Optional tax and dividend adjustments for the invest side of the comparison.

With tax and dividends both 0 (the default) nothing changes: verdict_adjusted()
simply calls verdict(), so every existing number stays exactly the same.
"""
import numpy as np

from loanlens.backtest import invest_beats_prepay
from loanlens.montecarlo import simulate_invest_vs_prepay
from loanlens.verdict import _lean, effective_prepay_rate_pct, verdict


def _check(tax_pct, dividend_pct):
    if not 0 <= tax_pct < 100:
        raise ValueError("tax_pct must be at least 0 and below 100")
    if dividend_pct < 0:
        raise ValueError("dividend_pct cannot be negative")


def after_costs_growth(growth, years, tax_pct=0.0, dividend_pct=0.0):
    """Turn price-only growth multiples (1.5 = +50%) into after-dividend, after-tax multiples.
    Tax is taken on the whole gain, and only when there is a gain."""
    _check(tax_pct, dividend_pct)
    g = np.asarray(growth, dtype=float)
    if tax_pct == 0 and dividend_pct == 0:
        return g
    g = g * (1 + dividend_pct / 100) ** years
    return np.where(g > 1, 1 + (g - 1) * (1 - tax_pct / 100), g)


def price_hurdle(hurdle, years, tax_pct=0.0, dividend_pct=0.0):
    """Yearly price return (as a fraction) the index must beat so that investing, after dividends
    and tax, ends up level with the guaranteed saving from paying the loan down."""
    _check(tax_pct, dividend_pct)
    if tax_pct == 0 and dividend_pct == 0:
        return hurdle
    h = np.asarray(hurdle, dtype=float)
    prepay_growth = (1 + h) ** years
    needed = np.where(prepay_growth > 1, 1 + (prepay_growth - 1) / (1 - tax_pct / 100), prepay_growth)
    return (needed / (1 + dividend_pct / 100) ** years) ** (1 / years) - 1


def verdict_adjusted(prices, loan_rate_pct, years, penalty_pct=0.0, tax_pct=0.0,
                     dividend_pct=0.0, n_sims=10000):
    """Same output as verdict(), plus 'price_hurdle_pct' (the bar the index price must clear)."""
    _check(tax_pct, dividend_pct)
    if tax_pct == 0 and dividend_pct == 0:
        out = verdict(prices, loan_rate_pct, years, penalty_pct=penalty_pct, n_sims=n_sims)
        out["price_hurdle_pct"] = out["hurdle_pct"]
        return out
    hurdle = effective_prepay_rate_pct(loan_rate_pct, penalty_pct, years)
    needed = float(price_hurdle(hurdle / 100, years, tax_pct, dividend_pct)) * 100
    hist = invest_beats_prepay(prices, needed, years)["pct_invest_wins"]
    mc = simulate_invest_vs_prepay(prices, needed, years, n_sims=n_sims)["prob_invest_wins"]
    lean_h, lean_m = _lean(hist), _lean(mc)
    clear = lean_h == lean_m and lean_h != "close"
    leaning = "invest" if (hist + mc) / 2 > 50 else "prepay"
    return {"hurdle_pct": hurdle, "price_hurdle_pct": needed,
            "hist_invest_wins_pct": hist, "mc_invest_wins_pct": mc,
            "clear": clear, "leaning": leaning,
            "label": f"Clear: {leaning}" if clear else f"Uncertain: leaning {leaning}, methods disagree or too close"}
