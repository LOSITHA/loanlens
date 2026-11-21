"""Plain-language explanation. The numbers come from code; the AI only puts them into words."""
import hashlib
import json
import os
import re
import time

CACHE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "outputs", "explanations.json"))
LANGS = {"English": "English", "Hindi": "Hindi (Devanagari script)", "Tamil": "Tamil (Tamil script)"}


def inr(x):
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


def build_facts(principal, rate, tenure, penalty, upfront, monthly, true_rate, payment,
                years=None, v=None, outcomes=None):
    """Collect every number the explanation may mention.
    v = dict from verdict(); outcomes = dict(spare, prepay_value, invest_typical, invest_bad)."""
    interest = max((payment - monthly) * tenure - principal, 0)
    f = {"principal": round(principal), "stated_rate": round(rate, 2), "true_rate": round(true_rate, 1),
         "fees": round(upfront + monthly * tenure), "monthly_payment": round(payment),
         "tenure_months": int(tenure), "penalty_pct": round(penalty, 1),
         "total_interest": round(interest), "total_paid": round(payment * tenure + upfront), "answer": None}
    if v is not None and rate > 0:
        f.update(years=years, hurdle=round(v["hurdle_pct"], 1), past_pct=round(v["hist_invest_wins_pct"]),
                 simulated_pct=round(v["mc_invest_wins_pct"]),
                 answer=(v["leaning"] if v["clear"] else "close"))
        if outcomes:
            f.update({k: round(x) for k, x in outcomes.items()})
    return f


def explanation_points(f):
    """List of (lead, sentence) pairs in plain English. No AI needed, so it updates instantly."""
    pts = []
    if f["stated_rate"] == 0:
        pts.append(("The real price.", f"This offer says 0% interest, but its fees of Rs {inr(f['fees'])} make it "
                    f"cost about {f['true_rate']:.1f}% a year."))
    else:
        pts.append(("The real price.", f"The advertised rate is {f['stated_rate']:.1f}%, but with fees of "
                    f"Rs {inr(f['fees'])} the real yearly cost is {f['true_rate']:.1f}%."))
    if f.get("total_paid") is not None:
        pts.append(("What you pay back.", f"You borrow Rs {inr(f['principal'])} and pay back about "
                    f"Rs {inr(f['total_paid'])} over {f['tenure_months']} months: Rs {inr(f['total_interest'])} "
                    f"of interest and Rs {inr(f['fees'])} of fees. That is about Rs {inr(f['monthly_payment'])} a month."))
    else:
        pts.append(("What you pay.", f"You would pay about Rs {inr(f['monthly_payment'])} a month for "
                    f"{f['tenure_months']} months."))
    a = f.get("answer")
    avg = (f["past_pct"] + f["simulated_pct"]) / 2 if a else None
    if a == "prepay":
        txt = (f"Paying the loan off early earns a guaranteed {f['hurdle']:.1f}% a year. Investing in the Nifty 50 "
               f"beat that only about {avg:.0f}% of the time, so paying it off looks safer.")
    elif a == "invest":
        txt = (f"Investing in the Nifty 50 beat the {f['hurdle']:.1f}% a year saved by paying off the loan "
               f"about {avg:.0f}% of the time.")
    elif a == "close":
        txt = "Paying the loan off early and investing are too close to call, because past data and simulations disagree."
    else:
        txt = None
    if txt:
        if f.get("spare") and f.get("prepay_value"):
            txt += (f" With Rs {inr(f['spare'])} of spare money for {f['years']} years, paying the loan down grows to "
                    f"Rs {inr(f['prepay_value'])} for sure. Investing grew to Rs {inr(f['invest_typical'])} in a typical "
                    f"case, but only Rs {inr(f['invest_bad'])} in a bad case.")
        pts.append(("Spare money.", txt))
    if f.get("penalty_pct"):
        pts.append(("Early-repayment charge.", f"The charge of {f['penalty_pct']:.1f}% is already counted above."))
    pts.append(("Reminder.", "This is a learning tool, not financial advice."))
    return pts


def template_explanation(f):
    """Plain English with no AI. Used as the fallback."""
    return " ".join(t for _, t in explanation_points(f))


def _numbers(text):
    text = re.sub(r"Nifty\s*50", "Nifty", text, flags=re.I)   # the index name is not a figure
    return [n.rstrip(".,") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)]


def _allowed(f):
    ok = set()
    for val in f.values():
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            ok.update({str(int(round(val))), f"{val:.0f}", f"{val:.1f}", f"{val:.2f}", inr(val), f"{val:,.0f}"})
    if f.get("past_pct") is not None:
        avg = (f["past_pct"] + f["simulated_pct"]) / 2
        ok.update({f"{avg:.0f}", f"{avg:.1f}"})
    if f.get("true_rate") is not None:
        ok.add(f"{f['true_rate'] - f['stated_rate']:.1f}")
    return ok


def numbers_are_safe(text, f):
    """True only if every number in the text is one of the facts (so the AI cannot invent figures)."""
    ok = _allowed(f)
    return all(n in ok or n.replace(",", "") in ok for n in _numbers(text))


PROMPT = """You explain loan facts to an ordinary person in simple, friendly words.
Write 4 to 6 short sentences in {lang}. Rules:
- Use ONLY the facts below. Do not invent, change or add any number. Write numbers with ordinary digits 0-9.
- Say the real yearly cost versus the advertised rate. If an answer is given, explain what it means for paying
  the loan off early versus investing in the Nifty 50 (the "answer" field says prepay, invest or close).
- No jargon. Do not promise any returns. End with one short reminder that this is not financial advice.
Facts (JSON):
{facts}
"""


def _call_gemini(prompt):
    from dotenv import load_dotenv
    from google import genai
    from google.genai import errors
    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    model = (os.getenv("GEMINI_MODEL") or "gemini-3.8-flash").strip().lower().replace(" ", "-")
    last = None
    for attempt in range(2):
        try:
            return client.models.generate_content(model=model, contents=prompt,
                                                  config={"temperature": 0.3}).text.strip()
        except errors.APIError as e:
            last = e
            if getattr(e, "code", None) == 429:
                break
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Gemini unavailable: {last!r}")


def _key(f, language):
    return hashlib.sha1((json.dumps(f, sort_keys=True) + "|" + language).encode()).hexdigest()[:16]


def _load():
    try:
        return json.load(open(CACHE_PATH, encoding="utf-8"))
    except Exception:
        return {}


def explain(f, language="English"):
    """Returns (text, source). source: 'saved', 'ai', 'template' or 'template-fallback'."""
    cache = _load()
    k = _key(f, language)
    if k in cache:
        return cache[k], "saved"
    if language == "English" and os.getenv("LOANLENS_NO_AI_ENGLISH"):
        return template_explanation(f), "template"
    try:
        text = _call_gemini(PROMPT.format(lang=LANGS[language], facts=json.dumps(f, indent=1)))
        if not text or not numbers_are_safe(text, f):
            raise ValueError("explanation contained a number that is not in the facts")
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        cache[k] = text
        json.dump(cache, open(CACHE_PATH, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        return text, "ai"
    except Exception:
        return template_explanation(f), "template-fallback"
