import glob, json, os, sys, time
from datetime import date
from loanlens.extractor import extract_offer, offer_upfront_fees, LoanOffer
from loanlens.xirr import true_loan_rate

FIELDS = ["principal", "annual_rate_pct", "tenure_months", "processing_fee",
          "insurance_premium", "other_upfront_fees", "monthly_fee", "prepayment_penalty_pct"]
TOL = {"annual_rate_pct": 0.01, "prepayment_penalty_pct": 0.01, "tenure_months": 0}


def match(a, b, field):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= TOL.get(field, 1.0)   # money: within Rs 1


def true_rate(o):
    return true_loan_rate(o["principal"], o["annual_rate_pct"], o["tenure_months"], date(2026, 1, 1),
                          upfront_fees=sum(o[k] or 0 for k in ("processing_fee", "insurance_premium", "other_upfront_fees")),
                          monthly_fees=o["monthly_fee"] or 0)


os.makedirs("outputs", exist_ok=True)
cache_path = "outputs/extraction_cache.json"
cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}

correct = {f: 0 for f in FIELDS}
halluc = miss = n = 0
rate_errs, failures = [], []
files = sorted(glob.glob((sys.argv[1] if len(sys.argv) > 1 else "data/offers_labelled") + "/*.txt"))
for path in files:
    key = os.path.basename(path)
    truth = json.load(open(path.replace(".txt", ".json")))
    if key not in cache:
        try:
            cache[key] = extract_offer(open(path, encoding="utf-8").read()).model_dump()
        except Exception as e:
            print(f"Stopped at {key}: {type(e).__name__}: {str(e)[:300]}. {len(cache)} offers are cached. Rerun later.")
            raise SystemExit
        json.dump(cache, open(cache_path, "w"), indent=1)
        time.sleep(1.5)
        print(f"extracted {key} ({len(cache)}/30)")
    pred = cache[key]
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
        rate_errs.append(abs(true_rate(pred) - true_rate(truth)) * 100)
    except Exception:
        rate_errs.append(float("nan"))

total = n * len(FIELDS)
print(f"\nOffers: {n} | field-level accuracy: {100 * sum(correct.values()) / total:.1f}%")
for f in FIELDS:
    print(f"  {f:24s} {100 * correct[f] / n:5.1f}%")
print(f"Hallucinated values (invented a field): {halluc} | Missed fields: {miss}")
ok = [e for e in rate_errs if e == e]
print(f"True-rate error: mean {sum(ok) / len(ok):.2f} pct-points, max {max(ok):.2f} (over {len(ok)} offers)")
print("\nMistakes:")
for k, f, t, p in failures:
    print(f"  {k}: {f}  truth={t}  got={p}")
