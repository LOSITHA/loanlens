import json, os

OUT = "data/offers_hard"
os.makedirs(OUT, exist_ok=True)


def T(principal=None, rate=None, tenure=None, pf=None, ins=None, other=None, monthly=None, pen=None):
    return dict(principal=principal, annual_rate_pct=rate, tenure_months=tenure, processing_fee=pf,
                insurance_premium=ins, other_upfront_fees=other, monthly_fee=monthly,
                prepayment_penalty_pct=pen)


OFFERS = [
    # 1. Hinglish WhatsApp message, fee as % + GST
    ("Hi sir, aapka 3 lakh ka personal loan approved hai!! 11.99% interest, 36 mahine ke liye. "
     "Processing fee 1.5% + GST lagega. Bima (insurance) Rs 8,000 compulsory hai. "
     "Agar jaldi band karna ho to foreclosure charge 3% hai. Reply YES to proceed.",
     T(300000, 11.99, 36, pf=5310, ins=8000, pen=3)),

    # 2. Formal sanction letter, lakh notation, years, GST on fee
    ("SANCTION LETTER\nBorrower: R. Kumar\nFacility: Rs. 5 Lakh term loan\nTenure: 5 years\n"
     "ROI: 10.5% p.a. (floating)\nProcessing charges: Rs. 2,500 plus GST @18%\n"
     "Stamp duty & legal: Rs. 300\nThis sanction is valid for 30 days.",
     T(500000, 10.5, 60, pf=2950, other=300)),

    # 3. SMS shorthand
    ("Dear Customer, Pre-approved PL Rs 1,50,000 @ 14.25% pa for 24M. PF Rs 1,999+GST. "
     "Ins Rs 3,500. T&C apply.",
     T(150000, 14.25, 24, pf=2358.82, ins=3500)),

    # 4. Marketing noise, monthly fee, % fee without GST
    ("MEGA FESTIVE OFFER!!! Instant cash up to your limit. Your approved amount: Rs 75,000. "
     "Pay back in 12 months at just 16% p.a. Zero paperwork! Processing fee 2% of amount. "
     "Convenience fee Rs 149 every month. Offer valid till Diwali.",
     T(75000, 16, 12, pf=1500, monthly=149)),

    # 5. Everything in words; optional insurance must NOT be counted
    ("Two lakh fifty thousand rupees, tenure three years, interest eleven percent per annum. "
     "Processing fee is one percent of the loan amount. Insurance is optional and not included.",
     T(250000, 11, 36, pf=2500)),

    # 6. No-cost EMI, GST already included in the fee
    ("Buy the phone at Rs 54,999. No Cost EMI for 9 months (EMI Rs 6,111). Interest 0%. "
     "Processing fee Rs 399 inclusive of GST.",
     T(54999, 0, 9, pf=399)),

    # 7. GST applies to only one of two fees
    ("Home improvement loan - key terms: Amount Rs 4,00,000; Duration 48 months; Interest 13% p.a. "
     "Processing fee: 2.5% of loan amount. Documentation charges: Rs 1,000 plus 18% GST. "
     "Part-payment charges: 2% of amount prepaid.",
     T(400000, 13, 48, pf=10000, other=1180, pen=2)),

    # 8. Missing tenure: the extractor must return null, not guess
    ("Loan of Rs 1,20,000 sanctioned. Interest rate 15% p.a. Tenure not yet decided. "
     "Processing fee Rs 1,200.",
     T(120000, 15, None, pf=1200)),
]

for i, (text, truth) in enumerate(OFFERS, 1):
    with open(f"{OUT}/hard_{i:02d}.txt", "w", encoding="utf-8") as f:
        f.write(text)
    with open(f"{OUT}/hard_{i:02d}.json", "w") as f:
        json.dump(truth, f, indent=2)
print(f"Wrote {len(OFFERS)} offers to {OUT}")