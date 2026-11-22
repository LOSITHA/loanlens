# LoanLens

![tests](https://github.com/LOSITHA/loanlens/actions/workflows/tests.yml/badge.svg)

**See what a loan really costs, and whether paying it off early beats investing the money.**

Demo video: _(add link here)_

LoanLens reads a loan offer (a message, a sanction letter, a "no-cost EMI" ad), works out the **real yearly cost** once fees are included, and then answers a question many borrowers ask: *"If I have spare money, should I pay this loan off early or invest it in the Nifty 50?"*

It answers with real market history and thousands of simulated futures, shows how confident it is, and explains the result in plain English.

![Dashboard](docs/dashboard.png)

## Why it matters

Loan offers hide their true price. A "no-cost EMI" with a small processing fee can really cost about **9.8% a year**. A loan advertised at 13.5% with fees and insurance can cost over 20%. Most people cannot work this out by hand, and they have no way to judge whether prepaying is smarter than investing. LoanLens does both, and is honest when the answer is a close call.

## What it does

1. **Reads the offer.** Paste text, or pick a sample. An AI reader (Google Gemini) pulls out the loan amount, interest rate, number of months, fees, insurance and prepayment charge. If the AI is busy or has no key, a built-in rule-based reader takes over.
2. **Finds the real yearly cost.** It uses XIRR (the same maths behind an APR) on the actual cash flows, including every fee.
3. **Compares prepaying with investing.** It checks how often investing in the Nifty 50 would have beaten the guaranteed saving from paying the loan down, in two ways:
   - **Past periods:** every real 3 or 5 year window since September 2007.
   - **Simulated futures:** 5,000 simulated futures built by reshuffling real market data in 21-day blocks (a block bootstrap).
4. **Gives a verdict.** "Pay off early" or "Investing looks better" only when both methods agree clearly. Otherwise it says **"Too close to call"** rather than guess.
5. **Explains it simply.** A live "A simple explanation" section, with a donut chart of principal, interest and fees, and a bar chart of paying off versus investing (bad, typical and good case). Every number comes from the maths, not from the AI.

Everything on screen updates when you change any detail. You can also add a simple tax rate and a dividend yield for investing (both start at 0).

![Explanation](docs/explanation.png)

## How the AI is used (and kept honest)

- The AI only **reads** the offer and, if you press the button, **rewords** the explanation.
- All maths is done by tested Python code. The AI never calculates anything.
- A **number guard** rejects any reworded text that contains a number that is not in the computed facts.
- Extracted values go through **sanity checks** (for example a 85% rate or a 600-month tenure triggers a warning).
- AI readings are **saved by text**, so the same text never costs a second AI call.
- If the AI is down or out of free quota, the app falls back to the rule-based reader and says so.

![Pasted offer](docs/paste.png)

## Run it yourself

Needs Python (built and tested on 3.14) and Git.

**Windows (PowerShell)**

```powershell
git clone https://github.com/LOSITHA/loanlens.git
cd loanlens
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app\streamlit_app.py
```

**Mac or Linux**

```bash
git clone https://github.com/LOSITHA/loanlens.git
cd loanlens
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

The app opens in your browser. It works **without any API key**: the sample offers are ready to use, and pasted offers are read by the rule-based reader.

### Optional: turn on the AI reader

1. Get a free key from Google AI Studio.
2. Copy `.env.example` to `.env` and fill it in:GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.8-flash

`.env` is git-ignored, so your key is never uploaded. The free tier has a small daily limit, and the model is sometimes busy; the app retries and then falls back by itself.

### Run the tests

```powershell
$env:PYTHONPATH="src"
pytest -v
```

44 tests cover the EMI and XIRR maths, the backtest, the verdict logic, tax and dividend adjustments, the readers, the explanation guard and the sanity checks. They run automatically on GitHub for every push.

## Results

### How well do the readers pull out the details?

Eight fields per offer (amount, rate, months, processing fee, insurance, other fees, monthly fee, prepayment charge). 95% ranges use the Wilson method, because the test sets are small.

| Test set | What it is | Rule-based reader (per field) | Gemini reader (per field) |
|---|---|---|---|
| Synthetic, 30 offers | Template-style messages made by our generator | 100% (240/240, range 98.4% to 100%) | _pending_ |
| Hard, 8 offers | Messy messages: Hinglish, numbers in words, SMS style | 93.8% (60/64, range 85.0% to 97.5%) | _pending_ |
| Bank-style, 8 offers | Layouts modelled on the RBI Key Facts Statement, sanction letters, card-EMI SMS, with the rupee symbol | 76.6% (49/64, range 64.9% to 85.3%) | _pending_ |

Read this honestly:

- The 100% on the synthetic set is optimistic: the rule-based reader was built while looking at those templates.
- The bank-style set is the fairest test. The rule-based reader struggles with the rupee symbol and with the Key Facts layout, which is the reason the AI reader exists.
- All offers are **invented**. Only the layout of the bank-style set follows public bank documents. Lender names and numbers are made up.

### Does the answer depend on the simulation settings?

I reran the simulation with 3 block lengths (10, 21 and 63 trading days) and 5 random seeds, for loan rates from 6% to 22% and both horizons (no prepayment charge):

- Changing the random seed moved results by at most 2.2 percentage points.
- For loans at **14% and above**, paying off early wins under both methods, in every setting.
- Below about 12%, the past-period and simulated answers disagree, so LoanLens reports a close call instead of guessing.
- 13 of 16 cases gave the same verdict everywhere. The other 3 sit right on the 40% or 60% line, which is exactly what the "close call" zone is for.

Run it yourself: `python scripts\check_robustness.py` (details in `outputs\robustness.csv`).

## Limits

- Investing is measured on the **Nifty 50 price index**, which leaves out dividends. A dividend yield and a simple tax rate can be added in the sidebar; tax there is taken on the whole gain and ignores the yearly exemption.
- Past windows **overlap**, so they are not independent trials. This is why the simulation is used as a second opinion.
- The history starts in September 2007 and includes some strong stretches. **Past returns do not predict future ones.**
- Fees you have already paid are not counted in the prepay-or-invest answer.
- The test offers are synthetic, and the sets are small, so accuracy figures have wide ranges.
- The free AI tier is limited and sometimes busy.
- LoanLens is a learning tool, **not financial advice**.

## Project layoutapp/streamlit_app.py the dashboard
src/loanlens/ maths (EMI, XIRR), backtest, Monte Carlo, verdict,
AI reader, rule-based reader, explainer, checks
scripts/ data pull, test-set builders, evaluations, robustness check
data/ Nifty 50 prices and the three labelled test sets
outputs/ saved readings, robustness results
tests/ 44 automated tests
docs/ screenshots

## Licence

See the `LICENSE` file.
