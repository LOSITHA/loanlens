import os
import sys
import json
from datetime import date

import streamlit as st
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from loanlens.backtest import load_nifty, invest_beats_prepay
from loanlens.montecarlo import simulate_invest_vs_prepay
from loanlens.verdict import verdict, effective_prepay_rate_pct
from loanlens.xirr import true_loan_rate

DARK, MID, LIGHT = "#574964", "#9F8383", "#C8AAAA"

st.set_page_config(page_title="LoanLens", layout="centered")

st.markdown("""
<style>
.stApp { background: #C8AAAA; }
header[data-testid="stHeader"] { background: transparent; }
html, body, .stApp, .stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp input, .stApp textarea, .stApp button, .stApp select,
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stCaptionContainer"],
.stApp [data-baseweb="select"] div, .stApp [data-testid="stExpander"] summary p,
.stApp .hero, .stApp .hero div, .stApp .stat, .stApp .stat div {
  font-family: 'Times New Roman', Times, serif !important;
  color: #574964;
}
.stApp h2, .stApp h3 { font-weight: 700; font-style: italic; }
.title { font-size: 3.2rem; font-weight: 700; font-style: italic; color: #574964; line-height: 1.1; margin: 0; }
.tagline { font-size: 1.15rem; font-style: italic; color: #574964; margin: 4px 0 18px 0; }
.hero { background: rgba(255,255,255,0.40); border: 1px solid #9F8383; border-radius: 14px;
        padding: 16px 22px; margin: 8px 0 14px 0; }
.hero .label { font-size: 0.95rem; letter-spacing: 0.08em; text-transform: uppercase; }
.hero .big { font-size: 2.3rem; font-weight: 700; font-style: italic; line-height: 1.15; }
.hero .small { font-size: 1.1rem; margin-top: 4px; }
.stat { background: rgba(255,255,255,0.30); border: 1px solid #9F8383; border-radius: 12px;
        padding: 10px 14px; text-align: center; }
.stat .v { font-size: 1.6rem; font-weight: 700; }
.stat .l { font-size: 0.95rem; font-style: italic; }
.stButton > button { background: #574964; color: #C8AAAA !important; border: 1px solid #574964; border-radius: 10px; }
.stButton > button:hover { background: #9F8383; color: #FFFFFF !important; border-color: #9F8383; }
.stApp input, .stApp textarea { background: rgba(255,255,255,0.55) !important; color: #574964 !important; }
.stApp [data-baseweb="select"] > div { background: rgba(255,255,255,0.55) !important; }
[data-testid="stExpander"] { background: rgba(255,255,255,0.25); border: 1px solid #9F8383; border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "Times", "DejaVu Serif"]


@st.cache_data
def prices():
    return load_nifty(os.path.join(ROOT, "data", "nifty50.csv"))


@st.cache_data
def run_verdict(rate, years, penalty):
    return verdict(prices(), rate, years, penalty_pct=penalty, n_sims=5000)


@st.cache_data
def curve(years, penalty):
    p = prices()
    rates = list(range(6, 19))
    hist, mc = [], []
    for r in rates:
        h = effective_prepay_rate_pct(r, penalty, years)
        hist.append(invest_beats_prepay(p, h, years)["pct_invest_wins"])
        mc.append(simulate_invest_vs_prepay(p, h, years, n_sims=3000)["prob_invest_wins"])
    return rates, hist, mc


def load_cache():
    path = os.path.join(ROOT, "outputs", "extraction_cache.json")
    return json.load(open(path)) if os.path.exists(path) else {}


def sample_label(k):
    if k.startswith("syn_"):
        n = int(k[4:6])
        return f"No-cost EMI sample {n - 24}" if n >= 25 else f"Loan sample {n + 1}"
    return k


def stat(value, label):
    return f'<div class="stat"><div class="v">{value}</div><div class="l">{label}</div></div>'


st.markdown('<p class="title">LoanLens</p>', unsafe_allow_html=True)
st.markdown('<p class="tagline">See what a loan really costs, and whether to pay it off early or invest instead.</p>',
            unsafe_allow_html=True)

# ---------- Step 1 ----------
st.markdown("### 1. Start with a loan offer")
cache = load_cache()
source = st.radio("How would you like to begin?", ["Try a sample offer", "Paste my own offer"],
                  horizontal=True, label_visibility="collapsed")

fields, suffix = None, "x"
if source == "Try a sample offer":
    if not cache:
        st.warning("No samples found yet. Paste an offer instead.")
        st.stop()
    key = st.selectbox("Pick a sample", sorted(cache), format_func=sample_label)
    path = os.path.join(ROOT, "data", "offers_labelled", key)
    if os.path.exists(path):
        st.text_area("The offer text", open(path, encoding="utf-8").read(), height=130, disabled=True)
    fields, suffix = cache[key], key
else:
    text = st.text_area("Paste the text of your loan offer or EMI message", height=130)
    if st.button("Read my offer") and text.strip():
        try:
            from loanlens.extractor import extract_offer
            with st.spinner("Reading the offer..."):
                st.session_state["fields"] = extract_offer(text).model_dump()
            st.session_state["n"] = st.session_state.get("n", 0) + 1
        except Exception as e:
            st.error("Sorry, the AI could not read this offer right now. The free AI quota may be used up. "
                     "Please try a sample offer instead.")
            st.caption(f"Details: {str(e)[:160]}")
    fields = st.session_state.get("fields")
    suffix = f"paste{st.session_state.get('n', 0)}"

if not fields:
    st.info("Choose a sample or paste an offer, then press the button.")
    st.stop()

with st.expander("Check the details we read (you can change any of them)"):
    c = st.columns(4)
    principal = c[0].number_input("Loan amount (Rs)", value=float(fields["principal"] or 0), key="p" + suffix)
    rate = c[1].number_input("Advertised rate (% a year)", value=float(fields["annual_rate_pct"] or 0), key="r" + suffix)
    tenure = c[2].number_input("Months to repay", value=int(fields["tenure_months"] or 12), step=1, key="t" + suffix)
    penalty = c[3].number_input("Early-repayment charge (%)", value=float(fields["prepayment_penalty_pct"] or 0), key="pp" + suffix)
    c = st.columns(4)
    proc = c[0].number_input("Processing fee (Rs)", value=float(fields["processing_fee"] or 0), key="pf" + suffix)
    ins = c[1].number_input("Insurance (Rs)", value=float(fields["insurance_premium"] or 0), key="in" + suffix)
    other = c[2].number_input("Other upfront fees (Rs)", value=float(fields["other_upfront_fees"] or 0), key="ot" + suffix)
    monthly = c[3].number_input("Fee every month (Rs)", value=float(fields["monthly_fee"] or 0), key="mf" + suffix)

if principal <= 0 or tenure <= 0:
    st.warning("The loan amount and the number of months must be above zero.")
    st.stop()

# ---------- Step 2 ----------
st.markdown("### 2. What this loan really costs")
upfront = proc + ins + other
try:
    true_rate = true_loan_rate(principal, rate, int(tenure), date.today(),
                               upfront_fees=upfront, monthly_fees=monthly) * 100
except Exception:
    st.error("We could not work out the real cost for these numbers.")
    st.stop()

fee_total = upfront + monthly * tenure
if rate == 0:
    msg = f"Advertised as 0% interest, but the fees make it cost about {true_rate:.1f}% a year."
else:
    msg = (f"Fees of Rs {fee_total:,.0f} push the real yearly cost "
           f"{true_rate - rate:.1f} points above the advertised rate.")
st.markdown(f'<div class="hero"><div class="label">Real yearly cost</div>'
            f'<div class="big">{true_rate:.1f}% <span style="font-size:1.2rem">instead of {rate:.1f}%</span></div>'
            f'<div class="small">{msg}</div></div>', unsafe_allow_html=True)

# ---------- Step 3 ----------
st.markdown("### 3. Spare money: pay off the loan or invest it?")
if rate == 0:
    st.info("This loan charges no interest, so paying it off early saves nothing. "
            "The real cost is the fee shown above.")
    st.stop()

years = st.select_slider("How many years could you keep the money invested?", options=[3, 5], value=5)
v = run_verdict(rate, years, penalty)
avg = (v["hist_invest_wins_pct"] + v["mc_invest_wins_pct"]) / 2

if v["clear"] and v["leaning"] == "prepay":
    head = "Pay off the loan early."
    why = (f"Paying it off earns a guaranteed {v['hurdle_pct']:.1f}% a year. Investing in the Nifty 50 "
           f"beat that only about {avg:.0f}% of the time.")
elif v["clear"]:
    head = "Investing looks better."
    why = (f"Investing in the Nifty 50 beat the guaranteed {v['hurdle_pct']:.1f}% from paying off the loan "
           f"about {avg:.0f}% of the time.")
else:
    head = "Too close to call."
    why = (f"Past data and simulations do not agree, so no answer is safe here. "
           f"Slightly leaning towards {'paying off the loan' if v['leaning'] == 'prepay' else 'investing'}.")
st.markdown(f'<div class="hero"><div class="label">Our answer</div><div class="big">{head}</div>'
            f'<div class="small">{why}</div></div>', unsafe_allow_html=True)

left, right = st.columns([3, 2])
with left:
    rates, hist, mc = curve(years, penalty)
    fig, ax = plt.subplots(figsize=(4.4, 2.5))
    fig.patch.set_facecolor(LIGHT)
    ax.set_facecolor(LIGHT)
    ax.plot(rates, hist, color=DARK, marker="o", markersize=3, linewidth=1.4, label="Past periods")
    ax.plot(rates, mc, color=DARK, marker="s", markersize=3, linewidth=1.2, linestyle="--", label="Simulated futures")
    ax.axhline(50, color=MID, linewidth=0.8)
    ax.axvline(rate, color=DARK, linestyle=":", linewidth=1.2)
    ax.text(rate + 0.2, 4, "this loan", color=DARK, fontsize=8, style="italic")
    ax.set_xlabel("Loan interest rate (%)", color=DARK, fontsize=9)
    ax.set_ylabel("Chance investing wins (%)", color=DARK, fontsize=9)
    ax.tick_params(colors=DARK, labelsize=8)
    for s in ax.spines.values():
        s.set_color(MID)
    ax.legend(fontsize=7, frameon=False, labelcolor=DARK)
    fig.tight_layout()
    st.pyplot(fig, use_container_width=False)
with right:
    st.markdown(stat(f"{v['hurdle_pct']:.1f}%", "guaranteed from paying off the loan"), unsafe_allow_html=True)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown(stat(f"{v['hist_invest_wins_pct']:.0f}%", "of past periods, investing won"), unsafe_allow_html=True)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown(stat(f"{v['mc_invest_wins_pct']:.0f}%", "of simulated futures, investing won"), unsafe_allow_html=True)

with st.expander("How this works, and its limits"):
    st.write("The AI only reads the offer. All the maths is done by tested code. Investing is measured against "
             "the Nifty 50 index since 2007, both on real past periods and on 10,000 simulated futures built "
             "from reshuffled real market data.")
    st.write("Limits: the index excludes dividends, results are before tax, overlapping past periods are not "
             "independent trials, and past returns do not guarantee future ones. Fees you have already paid "
             "are not counted in the prepay-or-invest answer. This is not financial advice.")