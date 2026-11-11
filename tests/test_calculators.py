from datetime import date
import pytest
from loanlens.emi import emi, amortization_schedule
from loanlens.xirr import xirr, true_loan_rate


def test_emi_known_value():
    # 1 lakh, 12% p.a., 12 months -> about 8884.88
    assert emi(100000, 12, 12) == pytest.approx(8884.88, abs=0.01)


def test_emi_zero_rate():
    assert emi(12000, 0, 12) == pytest.approx(1000)


def test_schedule_ends_at_zero_balance():
    rows = amortization_schedule(500000, 9.5, 60)
    assert rows[-1]["balance"] == pytest.approx(0, abs=1e-6)
    assert len(rows) == 60


def test_xirr_simple_ten_percent():
    flows = [(date(2021, 1, 1), -1000), (date(2022, 1, 1), 1100)]
    assert xirr(flows) == pytest.approx(0.10, abs=1e-6)


def test_xirr_needs_both_signs():
    with pytest.raises(ValueError):
        xirr([(date(2021, 1, 1), -1000), (date(2022, 1, 1), -50)])


def test_true_rate_no_fees_matches_effective_rate():
    # 12% nominal monthly compounding -> about 12.68% effective
    rate = true_loan_rate(100000, 12, 12, date(2025, 1, 1))
    assert rate == pytest.approx(0.1268, abs=0.003)


def test_fees_raise_true_rate():
    base = true_loan_rate(100000, 12, 12, date(2025, 1, 1))
    with_fee = true_loan_rate(100000, 12, 12, date(2025, 1, 1), upfront_fees=2000)
    assert with_fee > base


def test_no_cost_emi_is_not_free():
    # "0% no-cost EMI": EMI is price/6, but you pay Rs 800 processing fee upfront
    rate = true_loan_rate(30000, 0, 6, date(2025, 1, 1), upfront_fees=800)
    assert 0.09 < rate < 0.11   # about 9.9% a year, not 0%