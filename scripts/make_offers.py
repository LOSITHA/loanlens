import json, os, random

random.seed(7)
OUT = "data/offers_labelled"
os.makedirs(OUT, exist_ok=True)


def inr(x):
    """Indian digit grouping: 200000 -> 2,00,000"""
    s = str(int(round(x)))
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


def fee_item(principal):
    """Returns (rupee_amount, description) for a processing-type fee."""
    gst = random.random() < 0.6
    if random.random() < 0.5:
        pct = random.choice([1, 1.5, 2, 2.5, 3])
        base = principal * pct / 100
        desc = f"{pct}% of loan amount"
    else:
        base = random.choice([499, 999, 1499, 1999, 2999, 4999])
        desc = f"Rs {inr(base)}"
    if gst:
        desc += " + 18% GST"
    return round(base * (1.18 if gst else 1), 2), desc


def make_loan(i):
    principal = random.choice(range(50000, 1000001, 25000))
    rate = round(random.uniform(9, 24) * 2) / 2
    tenure = random.choice([6, 12, 18, 24, 36, 48, 60])
    t = dict(principal=float(principal), annual_rate_pct=rate, tenure_months=tenure,
             processing_fee=None, insurance_premium=None, other_upfront_fees=None,
             monthly_fee=None, prepayment_penalty_pct=None)
    items = []
    if random.random() < 0.9:
        amt, d = fee_item(principal)
        t["processing_fee"] = amt
        items.append(("Processing fee", d))
    if random.random() < 0.5:
        v = random.choice([2500, 4000, 6500, 9000])
        t["insurance_premium"] = float(v)
        items.append(("Credit life insurance (mandatory)", f"Rs {inr(v)} one-time"))
    if random.random() < 0.4:
        v = random.choice([500, 750, 1200, 2000])
        t["other_upfront_fees"] = float(v)
        items.append(("Documentation charges", f"Rs {inr(v)}"))
    if random.random() < 0.25:
        v = random.choice([49, 99, 150])
        t["monthly_fee"] = float(v)
        items.append(("Account maintenance", f"Rs {v} per month"))
    if random.random() < 0.6:
        p = random.choice([2, 3, 4, 5])
        t["prepayment_penalty_pct"] = float(p)
        items.append(("Prepayment charges", f"{p}% of outstanding principal"))

    style = ["letter", "bullets", "table", "sms"][i % 4]
    if style == "letter":
        text = (f"Dear Customer, you are pre-approved for a personal loan of Rs {inr(principal)} "
                f"for {tenure} months at {rate}% p.a. (reducing balance).\n"
                + "\n".join(f"{a}: {b}." for a, b in items))
    elif style == "bullets":
        text = (f"LOAN OFFER\n- Amount: Rs {inr(principal)}\n- Tenure: {tenure} months\n"
                f"- Interest: {rate}% per annum\n" + "\n".join(f"- {a}: {b}" for a, b in items))
    elif style == "table":
        text = (f"Particulars | Details\nLoan amount | Rs {inr(principal)}\nTenure | {tenure} months\n"
                f"ROI | {rate}% p.a.\n" + "\n".join(f"{a} | {b}" for a, b in items))
    else:
        text = (f"Offer! Loan Rs {inr(principal)} @ {rate}% for {tenure}m. "
                + " ".join(f"{a}: {b}." for a, b in items) + " T&C apply.")
    return text, t


def make_nocost(i):
    price = random.choice([18000, 30000, 45000, 60000, 85000])
    tenure = random.choice([3, 6, 9, 12])
    fee = random.choice([199, 299, 499, 799, 999])
    gst = random.random() < 0.5
    t = dict(principal=float(price), annual_rate_pct=0.0, tenure_months=tenure,
             processing_fee=round(fee * (1.18 if gst else 1), 2), insurance_premium=None,
             other_upfront_fees=None, monthly_fee=None, prepayment_penalty_pct=None)
    text = (f"NO-COST EMI on your new purchase! Product price Rs {inr(price)}. "
            f"Pay in {tenure} easy monthly instalments. Interest: 0%. "
            f"One-time processing fee: Rs {fee}" + (" + 18% GST." if gst else "."))
    return text, t


for i in range(30):
    text, truth = make_nocost(i) if i >= 25 else make_loan(i)
    with open(f"{OUT}/syn_{i:02d}.txt", "w", encoding="utf-8") as f:
        f.write(text)
    with open(f"{OUT}/syn_{i:02d}.json", "w") as f:
        json.dump(truth, f, indent=2)
print("Wrote 30 offers to", OUT)