def emi(principal: float, annual_rate_pct: float, months: int) -> float:
    """Monthly EMI for a reducing-balance loan."""
    if principal <= 0 or months <= 0:
        raise ValueError("principal and months must be positive")
    r = annual_rate_pct / 12 / 100
    if r == 0:
        return principal / months
    f = (1 + r) ** months
    return principal * r * f / (f - 1)


def amortization_schedule(principal: float, annual_rate_pct: float, months: int):
    """List of dicts: month, emi, interest, principal_paid, balance."""
    r = annual_rate_pct / 12 / 100
    payment = emi(principal, annual_rate_pct, months)
    balance = principal
    rows = []
    for m in range(1, months + 1):
        interest = balance * r
        princ = payment - interest
        balance = max(balance - princ, 0.0)
        rows.append({"month": m, "emi": payment, "interest": interest,
                     "principal_paid": princ, "balance": balance})
    return rows