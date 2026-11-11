import numpy as np
import pandas as pd

TRADING_DAYS = 252


def bootstrap_growth(prices: pd.Series, years: int, n_sims: int = 10000,
                     block: int = 21, seed: int = 42) -> np.ndarray:
    """Simulated growth multiple (e.g. 1.5 = +50%) of Rs 1 invested for `years`."""
    rng = np.random.default_rng(seed)
    logret = np.log(prices).diff().dropna().values
    n_days = int(years * TRADING_DAYS)
    n_blocks = int(np.ceil(n_days / block))
    starts = rng.integers(0, len(logret) - block + 1, size=(n_sims, n_blocks))
    idx = starts[:, :, None] + np.arange(block)[None, None, :]
    sampled = logret[idx].reshape(n_sims, -1)[:, :n_days]
    return np.exp(sampled.sum(axis=1))


def simulate_invest_vs_prepay(prices: pd.Series, loan_rate_pct: float, years: int,
                              n_sims: int = 10000, block: int = 21, seed: int = 42) -> dict:
    growth = bootstrap_growth(prices, years, n_sims, block, seed)
    ann = growth ** (1 / years) - 1
    hurdle = loan_rate_pct / 100
    return {
        "prob_invest_wins": float((ann > hurdle).mean() * 100),
        "prob_loss": float((growth < 1).mean() * 100),
        "p5_pct": float(np.percentile(ann, 5) * 100),
        "p50_pct": float(np.percentile(ann, 50) * 100),
        "p95_pct": float(np.percentile(ann, 95) * 100),
    }