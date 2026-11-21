"""Plain-language warnings for offer details that look unlikely, e.g. an AI misreading."""


def check_offer(principal, rate, tenure, penalty=0.0, upfront=0.0, monthly_fee=0.0):
    """Return a list of short warnings (empty list means nothing looks odd)."""
    notes = []
    if principal is not None and principal < 1000:
        notes.append(f"The loan amount (Rs {principal:,.0f}) is very small. Check it.")
    if principal is not None and principal > 500_000_000:
        notes.append("The loan amount is above Rs 50 crore. Check it.")
    if rate is not None and rate > 60:
        notes.append(f"A rate of {rate:g}% a year is unusually high. Check it is a yearly rate and not a monthly one.")
    if rate is not None and 0 < rate < 2:
        notes.append(f"A rate of {rate:g}% a year is unusually low. It may be a monthly rate.")
    if tenure is not None and tenure > 480:
        notes.append(f"{int(tenure)} months is over 40 years. Check the number of months.")
    if tenure is not None and 0 < tenure <= 2:
        notes.append(f"Only {int(tenure)} months to repay. If the offer says years, multiply by 12.")
    if penalty is not None and penalty > 10:
        notes.append(f"A prepay charge of {penalty:g}% is unusually high. Check it.")
    if principal and (upfront or 0) + (monthly_fee or 0) * (tenure or 0) > 0.25 * principal:
        notes.append("Fees add up to more than a quarter of the loan. Check the fee amounts.")
    return notes
