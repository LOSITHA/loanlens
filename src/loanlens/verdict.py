from loanlens.backtest import invest_beats_prepay
from loanlens.montecarlo import simulate_invest_vs_prepay


def effective_prepay_rate_pct(loan_rate_pct: float, penalty_pct: float, years: int) -> float:
    """Yearly return from prepaying, after a prepayment penalty, over `years`."""
    growth = (1 + loan_rate_pct / 100) ** years / (1 + penalty_pct / 100)
    return (growth ** (1 / years) - 1) * 100


def _lean(p_invest_wins: float) -> str:
    if p_invest_wins >= 60:
        return "invest"
    if p_invest_wins <= 40:
        return "prepay"
    return "close"


def verdict(prices, loan_rate_pct: float, years: int,
            penalty_pct: float = 0.0, n_sims: int = 10000) -> dict:
    hurdle = effective_prepay_rate_pct(loan_rate_pct, penalty_pct, years)
    hist = invest_beats_prepay(prices, hurdle, years)["pct_invest_wins"]
    mc = simulate_invest_vs_prepay(prices, hurdle, years, n_sims=n_sims)["prob_invest_wins"]
    lean_h, lean_m = _lean(hist), _lean(mc)
    clear = lean_h == lean_m and lean_h != "close"
    leaning = "invest" if (hist + mc) / 2 > 50 else "prepay"
    return {
        "hurdle_pct": hurdle,
        "hist_invest_wins_pct": hist,
        "mc_invest_wins_pct": mc,
        "clear": clear,
        "leaning": leaning,
        "label": f"Clear: {leaning}" if clear else f"Uncertain: leaning {leaning}, methods disagree or too close",
    }
