import os
import sys
import time
import httpx
from dotenv import load_dotenv
from pydantic import BaseModel
from google import genai
from google.genai import errors

load_dotenv()


class LoanOffer(BaseModel):
    principal: float | None = None            # loan amount in Rs
    annual_rate_pct: float | None = None      # stated interest rate, % per year
    tenure_months: int | None = None
    processing_fee: float | None = None       # Rs, upfront
    insurance_premium: float | None = None    # Rs, upfront add-on
    other_upfront_fees: float | None = None   # Rs, documentation, stamp duty etc.
    monthly_fee: float | None = None          # Rs per month, if any
    prepayment_penalty_pct: float | None = None


PROMPT = """You extract loan terms from an offer or sanction letter.
Rules:
- Use ONLY what the text states. If something is not stated, return null. Never guess.
- All money values in rupees. If a fee is given as a % of the loan, convert it to rupees.
- If GST is stated on a fee, include it in that fee's amount.
- annual_rate_pct is the stated interest rate (0 for a "0% / no-cost EMI").

Offer text:
"""


def extract_offer(text: str, retries: int = 4) -> LoanOffer:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    models = [os.getenv("GEMINI_MODEL") or "gemini-3.8-flash"]
    fallback = os.getenv("GEMINI_FALLBACK_MODEL")
    if fallback:
        models.append(fallback)

    last_error = None
    for model in models:
        for attempt in range(retries):
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=PROMPT + text,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": LoanOffer,
                        "temperature": 0,
                    },
                )
                return LoanOffer.model_validate_json(resp.text)
            except errors.APIError as e:
                last_error = e
                code = getattr(e, "code", None)
                print(f"[{model}] API error {code}: {str(e)[:200]}", file=sys.stderr)
                if code == 429:                  # quota used up: try next model
                    break
                if code in (500, 503):           # busy: wait, retry
                    time.sleep(min(2 ** attempt, 30))
                    continue
                raise                            # real bug: show it
            except httpx.TransportError as e:    # wifi dropped: wait, retry
                last_error = e
                print(f"[{model}] network error: {e}", file=sys.stderr)
                time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"Extraction failed. Last error: {last_error!r}")

def offer_upfront_fees(o: LoanOffer) -> float:
    return sum(x or 0 for x in (o.processing_fee, o.insurance_premium, o.other_upfront_fees))

