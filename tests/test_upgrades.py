import json
import os

import numpy as np
import pytest

from loanlens import offer_cache
from loanlens.adjust import after_costs_growth, price_hurdle, verdict_adjusted
from loanlens.backtest import load_nifty
from loanlens.sanity import check_offer
from loanlens.verdict import verdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PRICES = load_nifty(os.path.join(ROOT, "data", "nifty50.csv"))


# ---- tax and dividends
def test_zero_adjustments_change_nothing():
    base = verdict(PRICES, 13.5, 5, penalty_pct=2.0, n_sims=500)
    same = verdict_adjusted(PRICES, 13.5, 5, penalty_pct=2.0, n_sims=500)
    for k in base:
        assert same[k] == base[k]
    assert same["price_hurdle_pct"] == base["hurdle_pct"]
    assert price_hurdle(0.12, 5) == 0.12


def test_hurdle_round_trip():
    # investing at exactly the needed price return must end level with prepaying
    for h in (0.06, 0.135, 0.21):
        for tax, div in ((12.5, 0), (0, 1.2), (12.5, 1.2)):
            need = price_hurdle(h, 5, tax, div)
            level = after_costs_growth((1 + need) ** 5, 5, tax, div)
            assert level == pytest.approx((1 + h) ** 5, rel=1e-9)


def test_tax_makes_investing_harder_and_dividends_easier():
    h = 0.12
    assert price_hurdle(h, 5, 12.5, 0) > h
    assert price_hurdle(h, 5, 0, 1.2) < h


def test_tax_only_on_gains():
    g = after_costs_growth(np.array([0.8, 1.5]), 5, tax_pct=20)
    assert g[0] == pytest.approx(0.8)          # a loss is not taxed
    assert g[1] == pytest.approx(1.4)          # 50% gain, 20% of it taxed


def test_adjusted_verdict_moves_the_right_way():
    base = verdict_adjusted(PRICES, 10, 5, n_sims=500)
    taxed = verdict_adjusted(PRICES, 10, 5, tax_pct=12.5, n_sims=500)
    paid = verdict_adjusted(PRICES, 10, 5, dividend_pct=1.2, n_sims=500)
    assert taxed["hist_invest_wins_pct"] <= base["hist_invest_wins_pct"]
    assert paid["hist_invest_wins_pct"] >= base["hist_invest_wins_pct"]
    assert taxed["hurdle_pct"] == base["hurdle_pct"]       # the guaranteed saving itself is untouched


def test_bad_inputs_rejected():
    with pytest.raises(ValueError):
        after_costs_growth(1.5, 5, tax_pct=100)
    with pytest.raises(ValueError):
        price_hurdle(0.1, 5, dividend_pct=-1)


# ---- saved AI readings
def test_cache_same_text_same_key():
    assert offer_cache.text_key("Loan of  Rs 1,000\n") == offer_cache.text_key("loan of rs 1,000")
    assert offer_cache.text_key("a") != offer_cache.text_key("b")


def test_cache_round_trip_and_miss(tmp_path):
    path = str(tmp_path / "sub" / "c.json")
    assert offer_cache.get(path, "x") is None
    offer_cache.put(path, "x", {"principal": 1000.0, "monthly_fee": None})
    assert offer_cache.get(path, "X ") == {"principal": 1000.0, "monthly_fee": None}
    offer_cache.put(path, "y", {"principal": 5.0})
    assert offer_cache.get(path, "x")["principal"] == 1000.0     # earlier entry kept


def test_cache_survives_corrupt_file(tmp_path):
    path = tmp_path / "c.json"
    path.write_text("{not json")
    assert offer_cache.get(str(path), "x") is None
    offer_cache.put(str(path), "x", {"a": 1})
    assert offer_cache.get(str(path), "x") == {"a": 1}


# ---- sanity checks
def test_normal_offer_has_no_warnings():
    assert check_offer(200000, 13.5, 24, penalty=4, upfront=11220) == []


def test_odd_values_are_flagged():
    assert any("unusually high" in n for n in check_offer(200000, 85, 24))
    assert any("monthly" in n for n in check_offer(200000, 1.2, 24))
    assert any("40 years" in n for n in check_offer(200000, 12, 600))
    assert any("multiply by 12" in n for n in check_offer(200000, 12, 2))
    assert any("quarter" in n for n in check_offer(100000, 12, 24, upfront=40000))
    assert any("very small" in n for n in check_offer(500, 12, 24))


def test_every_sample_offer_passes_sanity():
    cache = json.load(open(os.path.join(ROOT, "outputs", "extraction_cache.json")))
    for key, f in cache.items():
        up = sum((f.get(k) or 0) for k in ("processing_fee", "insurance_premium", "other_upfront_fees"))
        assert check_offer(f["principal"], f["annual_rate_pct"], f["tenure_months"],
                           f.get("prepayment_penalty_pct") or 0, up, f.get("monthly_fee") or 0) == [], key
