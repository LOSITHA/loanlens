from datetime import date
from dateutil.relativedelta import relativedelta
from scipy.optimize import brentq
from loanlens.emi import emi


def xirr(cashflows: list[tuple[date, float]]) -> float:
    """Annualised rate from dated cash flows (Excel XIRR convention, 365-day year)."""
    amounts = [a for _, a in cashflows]
    if not (any(a > 0 for a in amounts) and any(a < 0 for a in amounts)):
        raise ValueError("Need at least one inflow and one outflow")
    t0 = min(d for d, _ in cashflows)

    def npv(rate):
        return sum(a / (1 + rate) ** ((d - t0).days / 365) for d, a in cashflows)

    return brentq(npv, -0.99, 100)


def true_loan_rate(principal, annual_rate_pct, months, start: date,
                   upfront_fees: float = 0.0, monthly_fees: float = 0.0) -> float:
    """
    Effective yearly cost of a loan from the borrower's side.
    Borrower receives (principal - upfront_fees) on day 0,
    then pays EMI (+ any monthly fee) each month.
    """
    payment = emi(principal, annual_rate_pct, months) + monthly_fees
    flows = [(start, principal - upfront_fees)]
    for m in range(1, months + 1):
        flows.append((start + relativedelta(months=m), -payment))
    return xirr(flows)