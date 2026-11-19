import numpy as np
import pandas as pd
import pytest
from loanlens.verdict import effective_prepay_rate_pct, verdict


def make_prices(n=2000, annual=0.10):
    idx = pd.bdate_range("2010-01-01", periods=n)
    return pd.Series(100 * (1 + annual) ** (np.arange(n) / 252), index=idx)


def test_no_penalty_equals_loan_rate():
    assert effective_prepay_rate_pct(12, 0, 3) == pytest.approx(12)


def test_penalty_lowers_effective_rate():
    assert effective_prepay_rate_pct(12, 4, 3) < 12


def test_penalty_hurts_less_over_longer_horizon():
    assert effective_prepay_rate_pct(12, 4, 5) > effective_prepay_rate_pct(12, 4, 1)


def test_clear_invest_when_loan_rate_low():
    v = verdict(make_prices(), 6, 3, n_sims=500)
    assert v["clear"] and v["leaning"] == "invest"


def test_clear_prepay_when_loan_rate_high():
    v = verdict(make_prices(), 16, 3, n_sims=500)
    assert v["clear"] and v["leaning"] == "prepay"


def test_methods_disagree_is_uncertain():
    v = verdict(make_prices(), 10.2, 3, n_sims=500)
    assert not v["clear"]


def test_penalty_can_flip_verdict():
    no_pen = verdict(make_prices(), 11, 3, penalty_pct=0, n_sims=500)
    big_pen = verdict(make_prices(), 11, 3, penalty_pct=10, n_sims=500)
    assert no_pen["leaning"] == "prepay"
    assert big_pen["leaning"] == "invest"