import sys
from datetime import date
from loanlens.extractor import extract_offer, offer_upfront_fees
from loanlens.xirr import true_loan_rate

text = open(sys.argv[1], encoding="utf-8").read()
o = extract_offer(text)
print(o.model_dump())

fees = offer_upfront_fees(o)
rate = true_loan_rate(o.principal, o.annual_rate_pct, o.tenure_months,
                      date.today(), upfront_fees=fees, monthly_fees=o.monthly_fee or 0)
print(f"Stated rate: {o.annual_rate_pct}%  ->  TRUE yearly cost: {rate:.1%}  (upfront fees Rs {fees:,.0f})")