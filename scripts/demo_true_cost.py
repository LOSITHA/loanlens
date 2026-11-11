from datetime import date
from loanlens.xirr import true_loan_rate

r = true_loan_rate(30000, 0, 6, date.today(), upfront_fees=800)
print(f"'No-cost' EMI true yearly cost: {r:.1%}")