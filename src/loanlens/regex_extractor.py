"""Rule-based loan offer reader. No API key, no quota. Baseline and offline fallback."""
import re

FIELDS = ["principal", "annual_rate_pct", "tenure_months", "processing_fee",
          "insurance_premium", "other_upfront_fees", "monthly_fee", "prepayment_penalty_pct"]

_UNIT = {"lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "crore": 1e7, "crores": 1e7}
_RS = re.compile(r"\bRs\s*(\d[\d,]*(?:\.\d+)?)\s*(lakhs?|lacs?|crores?)?", re.I)


def _num(s):
    return float(s.replace(",", ""))


def _rs_amount(text):
    m = _RS.search(text)
    if not m:
        return None
    return _num(m.group(1)) * _UNIT.get((m.group(2) or "").lower(), 1)


def _segments(text, keyword):
    pat = re.compile(keyword + r"([^\n]*?)(?:\.(?:\s|$)|\n|$)", re.I)
    return [m.group(1) for m in pat.finditer(text)]


def _gst_factor(seg):
    if not re.search(r"gst", seg, re.I) or re.search(r"inclusive|incl\.?\b", seg, re.I):
        return 1.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*gst|gst\s*@?\s*(\d+(?:\.\d+)?)\s*%", seg, re.I)
    rate = float(m.group(1) or m.group(2)) if m else 18.0
    return 1 + rate / 100


def _fee(text, keyword, principal, allow_percent=True):
    for seg in _segments(text, keyword):
        base = _rs_amount(seg)
        if base is None and allow_percent and principal:
            m = re.search(r"(\d+(?:\.\d+)?)\s*%", seg)
            if m:
                base = principal * float(m.group(1)) / 100
        if base is not None:
            return round(base * _gst_factor(seg), 2)
    return None


def extract_offer_regex(text: str) -> dict:
    t = re.sub(r"\bRs\.", "Rs", text)
    out = {f: None for f in FIELDS}

    # loan amount = whichever comes first: "Rs 2,00,000" or "3 lakh"
    cands = []
    m1 = _RS.search(t)
    if m1:
        cands.append((m1.start(), _num(m1.group(1)) * _UNIT.get((m1.group(2) or "").lower(), 1)))
    m2 = re.search(r"(\d+(?:\.\d+)?)\s*(lakhs?|lacs?|crores?)", t, re.I)
    if m2:
        cands.append((m2.start(), float(m2.group(1)) * _UNIT[m2.group(2).lower()]))
    if cands:
        out["principal"] = min(cands)[1]

    for pat in (r"(\d+(?:\.\d+)?)\s*%\s*(?:p\.?\s?a\.?|per\s*annum|interest)",
                r"(?:interest|ROI|rate)[^\n%\d]{0,25}(\d+(?:\.\d+)?)\s*%",
                r"@\s*(\d+(?:\.\d+)?)\s*%"):
        m = re.search(pat, t, re.I)
        if m:
            out["annual_rate_pct"] = float(m.group(1))
            break

    m = re.search(r"(\d+)\s*(?:months?|mahine|mths?)\b", t, re.I) or \
        re.search(r"for\s+(\d+)\s*m\b", t, re.I) or \
        re.search(r"(\d+)\s*(?:easy\s+)?(?:monthly\s+)?(?:instal+ments?|EMIs?)\b", t, re.I)
    if m:
        out["tenure_months"] = int(m.group(1))
    else:
        m = re.search(r"(\d+(?:\.\d+)?)\s*years?", t, re.I)
        if m:
            out["tenure_months"] = int(round(float(m.group(1)) * 12))

    out["processing_fee"] = _fee(t, r"(?:processing\s*(?:fee|charges)|\bPF\b)", out["principal"])

    for seg in _segments(t, r"(?:insurance|\bins\b|bima)"):
        a = _rs_amount(seg)
        if a is not None:
            out["insurance_premium"] = a
            break

    out["other_upfront_fees"] = _fee(t, r"(?:documentation\s*charges|stamp\s*duty)", out["principal"],
                                     allow_percent=False)

    m = re.search(r"\bRs\s*(\d[\d,]*(?:\.\d+)?)\s*(?:per|every|a|each)\s*month", t, re.I)
    if m:
        out["monthly_fee"] = _num(m.group(1))

    m = re.search(r"(?:prepayment|pre-payment|foreclosure|part[- ]payment)[^\n%]{0,80}?(\d+(?:\.\d+)?)\s*%", t, re.I)
    if m:
        out["prepayment_penalty_pct"] = float(m.group(1))
    return out