import numpy as np
import pandas as pd
from loanlens.montecarlo import simulate_invest_vs_prepay


def test_deterministic_series():
    # prices grow exactly 10%/yr, so every simulation returns 10%
    prices = pd.Series(100 * 1.10 ** (np.arange(1500) / 252))
    assert simulate_invest_vs_prepay(prices, 8, 3, n_sims=500)["prob_invest_wins"] == 100
    assert simulate_invest_vs_prepay(prices, 12, 3, n_sims=500)["prob_invest_wins"] == 0