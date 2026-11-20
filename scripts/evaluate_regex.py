import glob, json, os, sys
from datetime import date
from loanlens.regex_extractor import extract_offer_regex, FIELDS
from loanlens.xirr import true_loan_rate

TOL = {"annual_rate_pct": 0.01, "prepayment_penalty_pct": 0.01, "tenure_months": 0}


def match(a, b, field):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= TOL.get(field, 1.0)


def true_rate(o):
    return true_loan_rate(o["principal"], o["annual_rate_pct"], o["tenure_months"], date(2026, 1, 1),
                          upfront_fees=sum(o[k] or 0 for k in ("processing_fee", "insurance_premium", "other_upfront_fees")),
                          monthly_fees=o["monthly_fee"] or 0)


folder = sys.argv[1] if len(sys.argv) > 1 else "data/offers_labelled"
correct = {f: 0 for f in FIELDS}
halluc = miss = n = 0
errs, failures = [], []
for path in sorted(glob.glob(folder + "/*.txt")):
    key = os.path.basename(path)
    truth = json.load(open(path.replace(".txt", ".json")))
    pred = extract_offer_regex(open(path, encoding="utf-8").read())
    n += 1
    for f in FIELDS:
        if match(pred[f], truth[f], f):
            correct[f] += 1
        else:
            failures.append((key, f, truth[f], pred[f]))
            if truth[f] is None:
                halluc += 1
            elif pred[f] is None:
                miss += 1
    try:
        errs.append(abs(true_rate(pred) - true_rate(truth)) * 100)
    except Exception:
        errs.append(float("nan"))

total = n * len(FIELDS)
print(f"\nREGEX baseline | folder {folder} | offers: {n} | field-level accuracy: {100 * sum(correct.values()) / total:.1f}%")
for f in FIELDS:
    print(f"  {f:24s} {100 * correct[f] / n:5.1f}%")
print(f"Invented values: {halluc} | Missed fields: {miss}")
ok = [e for e in errs if e == e]
if ok:
    print(f"True-rate error: mean {sum(ok) / len(ok):.2f} pct-points, max {max(ok):.2f} (over {len(ok)} of {n} offers computable)")
print("\nMistakes:")
for k, f, t, p in failures:
    print(f"  {k}: {f}  truth={t}  got={p}")