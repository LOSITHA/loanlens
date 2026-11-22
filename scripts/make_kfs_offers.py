"""Build 8 test offers laid out like the RBI Key Facts Statement (KFS) that Indian lenders must give
borrowers, plus a few other real-world formats (sanction letter, card-EMI SMS, app screen).

The layout follows the public KFS template (numbered rows, fees split into lender / third party,
APR, contingent charges, the rupee symbol in some offers). All lender names, people and numbers are INVENTED. The EMI and APR
figures are computed, so each offer is internally consistent.

Run from the project folder:   python scripts\\make_kfs_offers.py
Writes data/offers_kfs/kfs_01.txt ... and the matching .json answer keys.
"""
import json
import os
import sys
from datetime import date

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from loanlens.emi import emi
from loanlens.xirr import true_loan_rate

OUT = os.path.join(ROOT, "data", "offers_kfs")


def inr(x):
    """Indian digit grouping: 1234567 -> 12,34,567."""
    s = f"{int(round(x)):d}"
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def T(principal, rate, tenure, pf=None, ins=None, other=None, monthly=None, pen=None):
    return dict(principal=principal, annual_rate_pct=rate, tenure_months=tenure, processing_fee=pf,
                insurance_premium=ins, other_upfront_fees=other, monthly_fee=monthly,
                prepayment_penalty_pct=pen)


def apr(t):
    """Yearly cost including fees, the way a KFS 'APR' row reports it."""
    r = true_loan_rate(t["principal"], t["annual_rate_pct"], t["tenure_months"], date(2026, 1, 1),
                       upfront_fees=sum(t[k] or 0 for k in ("processing_fee", "insurance_premium", "other_upfront_fees")),
                       monthly_fees=t["monthly_fee"] or 0)
    return round(r * 100, 2)


OFFERS = []

# 1. Fixed-rate personal loan, full KFS layout
t = T(300000, 12.5, 36, pf=5310, ins=4200, pen=4)
OFFERS.append((t, f"""KEY FACTS STATEMENT (KFS) - PERSONAL LOAN
Lender: Lakeview Bank Ltd. (example)    Date: 14-Jan-2026
Part 1: Interest rate and fees/charges
1. Loan proposal/account no.: LV/PL/2026/004417    Type of loan: Personal Loan
2. Sanctioned Loan amount (in Rs): Rs {inr(t['principal'])}
3. Disbursal schedule: (i) Disbursement in stages or 100% upfront: 100% upfront
4. Loan term (year/months/days): 36 months
5. Instalment details: Type of instalments: Equated Monthly Instalments   Number of EPIs: 36
   EPI (Rs): Rs {inr(emi(300000, 12.5, 36))}   Commencement of repayment, post sanction: 1 month
6. Interest rate (%) and type (fixed or floating or hybrid): 12.50% p.a., Fixed
8. Fee/Charges (in Rs or %):  (A) Payable to the RE
   (i) Processing fees (incl. GST): Rs 5,310 (1.5% of loan amount plus 18% GST), one-time
   (B) Payable to a third party through RE
   (ii) Insurance charges: Rs 4,200, one-time
   (iii) Valuation fees: Not applicable   (iv) Any other charges: Nil
9. Annual Percentage Rate (APR) (%): {apr(t)}%
10. Details of Contingent Charges (in Rs or %, as applicable)
   (i) Penal charges, if any, in case of delayed payment: 2% per month on overdue amount
   (iii) Foreclosure charges, if applicable: 4% of principal outstanding
   (iv) Charges for switching of loans from floating to fixed rate and vice versa: Not applicable
Part 2: Other qualitative information
1. Clause of Loan agreement relating to engagement of recovery agents: Clause 17
3. Nodal grievance redressal officer: Mr. A. Rao, Chief Manager, Mumbai
4. Whether the loan is, or in future may be, subject to transfer to other REs or securitisation: Yes
"""))

# 2. Floating rate (benchmark + spread), explicit nil foreclosure
t = T(500000, 11.75, 60, pf=4425, pen=0)
OFFERS.append((t, f"""KEY FACTS STATEMENT
Sundar Finance & Co. (example)   Loan type: Personal Loan - floating rate
Sr. 2  Sanctioned loan amount (Rs): {inr(t['principal'])}
Sr. 4  Loan term: 5 years
Sr. 5  Instalment details: EMI, 60 instalments, EPI Rs {inr(emi(500000, 11.75, 60))}
Sr. 6  Interest rate and type: Floating
Sr. 7  Floating rate details: Reference benchmark: External Benchmark Rate; Benchmark rate (B) 5.50%;
       Spread (S) 6.25%; Final rate (R = B + S) 11.75%; Reset periodicity: 3 months.
       Impact of 25 bps change in R: EPI changes by Rs {inr(emi(500000, 12.0, 60) - emi(500000, 11.75, 60))}
Sr. 8  Fee/charges: Processing fee (incl. GST) Rs 4,425 (0.75% + GST); insurance: not taken; other charges: Nil
Sr. 9  APR: {apr(T(500000, 11.75, 60, pf=4425))}%
Sr. 10 Contingent charges: Foreclosure / prepayment charges: Nil for individual borrowers on floating rate loans.
       Penal charges: 2% p.a. over the contracted rate.
"""))

# 3. NBFC style with fees split in A and B, documentation charge
t = T(150000, 18, 24, pf=2360, ins=6500, other=590, pen=5)
OFFERS.append((t, f"""Loan Key Facts - Greenfield Capital (example NBFC)
Amount sanctioned: ₹{inr(t['principal'])}/-
Tenure: 24 months | EMI: ₹{inr(emi(150000, 18, 24))} | Rate of interest: 18% per annum (fixed, reducing balance)
One-time charges deducted from disbursal:
  Payable to lender: Processing fee ₹2,360 (inclusive of GST)
                     Documentation charges ₹590 (inclusive of GST)
  Payable to third party via lender: Credit life insurance ₹6,500
APR (including all charges): {apr(t)}%
If you close the loan early: 5% of the principal outstanding at the time of closure.
Late payment: Rs 500 per missed instalment.
"""))

# 4. Digital loan with a cooling-off period (a distractor) and a monthly fee
t = T(50000, 24, 6, pf=1770, monthly=99, pen=2)
OFFERS.append((t, f"""QuickRupee Digital Loan - Key Facts (example app)
Loan amount: Rs {inr(t['principal'])}      Repayment period: 6 months
Interest: 24% p.a.      EMI: Rs {inr(emi(50000, 24, 6) + 99)} (includes the account fee)
Processing fee: Rs 1,770 (incl. GST), deducted at disbursal
Account maintenance fee: Rs 99 every month
Cooling-off period: you may exit within 3 days of disbursal by repaying the principal and interest for those days,
with no penalty.
Prepayment after the cooling-off period: 2% of the amount prepaid.
APR: {apr(t)}%
"""))

# 5. Bank sanction letter, fee given as a percentage with min/max, tenure in years, no prepayment mention
t = T(750000, 9.85, 84, pf=3097.5)
OFFERS.append((t, f"""SANCTION ADVICE
Ref: HB/RT/2026/1182     Date: 02/02/2026
Dear Mr. S. Menon,
We are pleased to sanction a Term Loan of Rs. 7.50 lakh to you on the following terms:
  Rate of interest: 9.85% p.a., linked to the bank's lending rate, reset yearly
  Repayment: 7 years in equated monthly instalments
  Processing charges: 0.35% of the loan amount (minimum Rs 2,000, maximum Rs 10,000) plus GST at 18%
  Security: hypothecation of the vehicle financed
  Sanction valid for 45 days from the date of this letter.
"""))

# 6. Credit card purchase converted to EMI (SMS style)
t = T(42000, 15, 12, pf=234.82, pen=3)
OFFERS.append((t, f"""HDFC-style SMS (example): Your purchase of Rs {inr(t['principal'])} on card XX4821 is converted to EMI.
Tenure 12 months @ 15% p.a. EMI Rs {inr(emi(42000, 15, 12))}. Processing fee Rs 199 + GST. Foreclosure charge 3% of outstanding
principal. Total interest payable Rs {inr(emi(42000, 15, 12) * 12 - 42000)}. T&C apply."""))

# 7. App screen copy-paste with a late fee distractor
t = T(200000, 14.99, 18, pf=7080, pen=2)
OFFERS.append((t, f"""Your offer is ready!
Loan amount   Rs {inr(t['principal'])}
Tenure   18 months
Interest rate   14.99% p.a.
Processing fee   3% + GST
Late payment fee   Rs 500 per instalment
Part-prepayment   allowed after 6 EMIs, charge 2%
Monthly instalment   Rs {inr(emi(200000, 14.99, 18))}
Tap CONTINUE to accept."""))

# 8. Vehicle loan KFS with several small fees
t = T(650000, 9.25, 60, pf=5310, other=2500, pen=3)
OFFERS.append((t, f"""KEY FACTS STATEMENT - VEHICLE LOAN
Hillcrest Bank (example)
2. Sanctioned loan amount: ₹ {inr(t['principal'])}
3. Disbursal: single payment to the dealer
4. Loan term: 60 months
5. Instalments: 60 EPIs of ₹ {inr(emi(650000, 9.25, 60))}
6. Interest rate: 9.25% per annum, fixed for the full term
8. Fees: (A) Lender: Processing fee ₹4,500 + GST @18% (₹5,310 in total); Valuation fee ₹1,000;
   Documentation charges ₹1,500 (both one-time).
   (B) Third party: Insurance - to be bought by the borrower directly from the insurer, not through the lender.
9. APR: {apr(T(650000, 9.25, 60, pf=5310, other=2500))}%
10. Contingent charges: Foreclosure charges 3% of principal outstanding; delayed payment 24% p.a. on overdue amount.
"""))


def main():
    os.makedirs(OUT, exist_ok=True)
    for i, (truth, text) in enumerate(OFFERS, 1):
        with open(os.path.join(OUT, f"kfs_{i:02d}.txt"), "w", encoding="utf-8") as f:
            f.write(text)
        with open(os.path.join(OUT, f"kfs_{i:02d}.json"), "w") as f:
            json.dump(truth, f, indent=2)
    print(f"Wrote {len(OFFERS)} offers to {OUT}")


if __name__ == "__main__":
    main()
