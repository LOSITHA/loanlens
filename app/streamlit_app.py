import html
import io
import json
import os
import sys
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from loanlens.backtest import load_nifty, invest_beats_prepay
from loanlens.emi import emi
from loanlens.montecarlo import simulate_invest_vs_prepay
from loanlens.verdict import verdict, effective_prepay_rate_pct
from loanlens.xirr import true_loan_rate

# Palette from the mood board
INK, SLATE, ROSE, PEACH = "#0F3040", "#404858", "#A56F63", "#D9987F"
CREAM, CARD, LINE, TINT = "#F7EEE8", "#FFFAF6", "#E6CFC3", "#F3DDD0"

st.set_page_config(page_title="LoanLens", page_icon="🔍", layout="centered")

st.markdown(f"""
<style>
.stApp {{ background: {CREAM}; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ max-width: 980px; padding-top: 1.4rem; padding-bottom: 3rem; }}

/* Times New Roman everywhere, icons keep their own font */
html, body, .stApp, .stApp * {{ font-family: 'Times New Roman', Times, 'Liberation Serif', serif; }}
.stApp [data-testid="stIconMaterial"], .stApp .material-icons {{
  font-family: 'Material Symbols Rounded', 'Material Icons' !important; }}
.stApp, .stApp p, .stApp label, .stApp li, .stApp span, .stApp div {{ color: {INK}; }}
.stApp [data-testid="stCaptionContainer"], .stApp small {{ color: {SLATE}; }}
.stApp p, .stApp label {{ font-size: 1.05rem; }}

/* hero band */
.hero-band {{ background: linear-gradient(135deg, {INK} 0%, {SLATE} 100%); border-radius: 22px;
  padding: 26px 32px 24px; margin-bottom: 18px; box-shadow: 0 6px 18px rgba(15,48,64,.14); }}
.hero-band .brand {{ font-size: 3rem; font-weight: 700; color: {CREAM}; line-height: 1.05; }}
.hero-band .tag {{ font-size: 1.2rem; color: #EFDFD6; margin: 6px 0 16px; max-width: 640px; }}
.hero-band .tag i {{ color: {PEACH}; }}
.hero-band .chips span {{ display: inline-block; border: 1px solid {PEACH}; color: #F7EEE8;
  border-radius: 999px; padding: 4px 14px; margin: 0 8px 6px 0; font-size: 1rem; }}

/* white-ish cards (containers with a key starting with card_) */
[class*="st-key-card_"] {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 18px;
  padding: 20px 24px 18px; margin-bottom: 18px; box-shadow: 0 3px 12px rgba(15,48,64,.06); }}
.sec {{ display: flex; align-items: center; gap: 12px; margin-bottom: 2px; }}
.sec .num {{ background: {ROSE}; color: #FFFFFF; width: 32px; height: 32px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.1rem; }}
.sec .title {{ font-size: 1.55rem; font-weight: 700; color: {INK}; }}
.sec-sub {{ color: {SLATE}; font-size: 1.05rem; margin: 0 0 10px 44px; }}

.offer {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 12px; padding: 12px 16px;
  white-space: pre-wrap; font-size: 1.05rem; color: {INK}; line-height: 1.45; }}

/* highlight and stat blocks */
.answer {{ background: {TINT}; border-left: 7px solid {ROSE}; border-radius: 14px; padding: 16px 22px; margin: 6px 0 12px; }}
.answer .lbl {{ font-size: .9rem; letter-spacing: .09em; text-transform: uppercase; color: {SLATE}; }}
.answer .big {{ font-size: 2.5rem; font-weight: 700; color: {INK}; line-height: 1.15; }}
.answer .big .vs {{ font-size: 1.2rem; font-weight: 400; color: {SLATE}; }}
.answer .big .vs i {{ color: {ROSE}; }}
.answer .msg {{ font-size: 1.1rem; margin-top: 4px; }}
.pill {{ display: inline-block; border-radius: 999px; padding: 2px 14px; font-size: .95rem; font-weight: 700;
  background: {INK}; color: {CREAM} !important; margin-bottom: 6px; }}
.pill.soft {{ background: {PEACH}; color: {INK} !important; }}
.stat {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 14px; padding: 10px 14px; margin-bottom: 10px; }}
.stat .v {{ font-size: 1.55rem; font-weight: 700; color: {INK}; line-height: 1.2; }}
.stat .l {{ font-size: .98rem; color: {SLATE}; }}
.note {{ color: {SLATE}; font-size: .98rem; font-style: italic; }}

/* widgets */
.stButton > button {{ background: {INK}; color: {CREAM} !important; border: 0; border-radius: 12px;
  padding: .45rem 1.3rem; font-weight: 700; font-size: 1.05rem; }}
.stButton > button:hover {{ background: {ROSE}; color: #FFFFFF !important; }}
.stApp [data-baseweb="input"], .stApp [data-baseweb="textarea"], .stApp [data-baseweb="select"] > div {{
  background: #FFFFFF !important; border-color: {LINE} !important; border-radius: 10px !important; }}
[data-testid="stSelectbox"] div[data-baseweb="select"] div {{ background-color: #FFFFFF !important; font-size: 1.05rem; }}
.stApp input, .stApp textarea {{ background: transparent !important; color: {INK} !important; }}
[data-testid="stExpander"] {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 14px; }}
[data-testid="stExpander"] summary p {{ font-weight: 700; }}
</style>
""", unsafe_allow_html=True)

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "Times", "Liberation Serif", "DejaVu Serif"]


def inr(x):
    """Rs amount with Indian digit grouping: 200000 -> 2,00,000"""
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


@st.cache_data
def prices():
    return load_nifty(os.path.join(ROOT, "data", "nifty50.csv"))


@st.cache_data
def run_verdict(rate, years, penalty):
    return verdict(prices(), rate, years, penalty_pct=penalty, n_sims=5000)


@st.cache_data
def curve(years, penalty, hi):
    p = prices()
    rates = list(range(6, hi + 1))
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


def read_offer(text):
    """Try the AI reader first; fall back to the built-in rule-based reader."""
    try:
        from loanlens.extractor import extract_offer
        return extract_offer(text, retries=2).model_dump(), "ai"
    except Exception:
        from loanlens.regex_extractor import extract_offer_regex
        return extract_offer_regex(text), "rules"


def section(num, title, sub):
    st.markdown(f'<div class="sec"><span class="num">{num}</span><span class="title">{title}</span></div>'
                f'<div class="sec-sub">{sub}</div>', unsafe_allow_html=True)


def stat(value, label):
    return f'<div class="stat"><div class="v">{value}</div><div class="l">{label}</div></div>'


# ------------------------------------------------------------------ header
st.markdown("""
<div class="hero-band">
  <div class="brand">LoanLens</div>
  <div class="tag"><i>See what a loan really costs</i>, and whether to pay it off early or invest the money instead.</div>
  <div class="chips"><span>1 &nbsp;Read the offer</span><span>2 &nbsp;Find the real cost</span><span>3 &nbsp;Prepay or invest?</span></div>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ step 1
fields, suffix, via = None, "x", "sample"
with st.container(key="card_1"):
    section(1, "Start with a loan offer", "Try one of our samples, or paste the text of your own offer.")
    cache = load_cache()
    source = st.radio("How would you like to begin?", ["Try a sample offer", "Paste my own offer"],
                      horizontal=True, label_visibility="collapsed")
    if source == "Try a sample offer":
        names = sorted(k for k in cache if k.startswith("syn_"))
        if not names:
            st.warning("No samples found yet. Paste an offer instead.")
        else:
            key = st.selectbox("Pick a sample", names, format_func=sample_label)
            path = os.path.join(ROOT, "data", "offers_labelled", key)
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    st.markdown(f'<div class="offer">{html.escape(f.read())}</div>', unsafe_allow_html=True)
            fields, suffix = cache[key], key
    else:
        text = st.text_area("Paste the text of your loan offer or EMI message", height=140,
                            placeholder="Example: Loan of Rs 2,00,000 for 24 months at 13.5% p.a. "
                                        "Processing fee 2% + GST. Insurance Rs 6,500.")
        if st.button("Read my offer") and text.strip():
            with st.spinner("Reading the offer..."):
                st.session_state["fields"], st.session_state["via"] = read_offer(text)
            st.session_state["n"] = st.session_state.get("n", 0) + 1
        fields = st.session_state.get("fields")
        via = st.session_state.get("via", "ai")
        suffix = f"paste{st.session_state.get('n', 0)}"

    if fields and via == "rules":
        st.warning("The AI reader is busy or unavailable, so we used the simpler built-in reader. "
                   "It can miss things, so please check the details below.")

if not fields:
    st.info("Choose a sample or paste an offer to see what it really costs.")
    st.stop()

missing = [n for k, n in (("principal", "loan amount"), ("annual_rate_pct", "interest rate"),
                          ("tenure_months", "number of months")) if fields.get(k) is None]

with st.expander("Check the details we read (you can change any of them)", expanded=bool(missing)):
    if missing:
        st.warning("We could not find the " + ", ".join(missing) + " in this offer. Please fill it in.")
    c = st.columns(4)
    principal = c[0].number_input("Loan amount (Rs)", min_value=0.0, step=1000.0,
                                  value=fields["principal"], placeholder="not found", key="p" + suffix)
    rate = c[1].number_input("Advertised rate (% a year)", min_value=0.0, step=0.1, format="%.2f",
                             value=fields["annual_rate_pct"], placeholder="not found", key="r" + suffix)
    tenure = c[2].number_input("Months to repay", min_value=1, step=1,
                               value=fields["tenure_months"], placeholder="not found", key="t" + suffix)
    penalty = c[3].number_input("Early-repayment charge (%)", min_value=0.0, step=0.5,
                                value=float(fields["prepayment_penalty_pct"] or 0), key="pp" + suffix)
    c = st.columns(4)
    proc = c[0].number_input("Processing fee (Rs)", min_value=0.0, step=100.0,
                             value=float(fields["processing_fee"] or 0), key="pf" + suffix)
    ins = c[1].number_input("Insurance (Rs)", min_value=0.0, step=100.0,
                            value=float(fields["insurance_premium"] or 0), key="in" + suffix)
    other = c[2].number_input("Other upfront fees (Rs)", min_value=0.0, step=100.0,
                              value=float(fields["other_upfront_fees"] or 0), key="ot" + suffix)
    monthly = c[3].number_input("Fee every month (Rs)", min_value=0.0, step=10.0,
                                value=float(fields["monthly_fee"] or 0), key="mf" + suffix)

if not principal or rate is None or not tenure:
    st.info("Fill in the loan amount, interest rate and number of months above to continue.")
    st.stop()

# ------------------------------------------------------------------ step 2
upfront = proc + ins + other
try:
    true_rate = true_loan_rate(principal, rate, int(tenure), date.today(),
                               upfront_fees=upfront, monthly_fees=monthly) * 100
    payment = emi(principal, rate, int(tenure)) + monthly
except Exception:
    st.error("We could not work out the real cost for these numbers. Please check the details above.")
    st.stop()

fee_total = upfront + monthly * tenure
with st.container(key="card_2"):
    section(2, "What this loan really costs", "Fees count too. This is the yearly rate once they are included.")
    if rate == 0:
        msg = f"Advertised as 0% interest, but the fees make it cost about {true_rate:.1f}% a year."
    else:
        msg = (f"Fees of Rs {inr(fee_total)} push the real yearly cost "
               f"{true_rate - rate:.1f} points above the advertised rate.")
    st.markdown(f'<div class="answer"><div class="lbl">Real yearly cost</div>'
                f'<div class="big">{true_rate:.1f}% <span class="vs">instead of <i>{rate:.1f}%</i> advertised</span></div>'
                f'<div class="msg">{msg}</div></div>', unsafe_allow_html=True)
    s = st.columns(3)
    s[0].markdown(stat(f"Rs {inr(principal)}", "loan amount"), unsafe_allow_html=True)
    s[1].markdown(stat(f"Rs {inr(payment)}", f"monthly payment for {int(tenure)} months"), unsafe_allow_html=True)
    s[2].markdown(stat(f"Rs {inr(fee_total)}", "fees you pay on top"), unsafe_allow_html=True)

# ------------------------------------------------------------------ step 3
with st.container(key="card_3"):
    section(3, "Spare money: pay off the loan or invest it?",
            "We compare paying the loan down with investing in the Nifty 50, using real market history.")
    if rate == 0:
        st.info("This loan charges no interest, so paying it off early saves nothing. "
                "The real cost is the fee shown above.")
    else:
        years = st.select_slider("How long could you keep the money invested?", options=[3, 5], value=5,
                                 format_func=lambda y: f"{y} years")
        v = run_verdict(rate, years, penalty)
        avg = (v["hist_invest_wins_pct"] + v["mc_invest_wins_pct"]) / 2
        if v["clear"] and v["leaning"] == "prepay":
            pill, head = "Clear answer", "Pay off the loan early."
            why = (f"Paying it off earns a guaranteed {v['hurdle_pct']:.1f}% a year. Investing in the Nifty 50 "
                   f"beat that only about {avg:.0f}% of the time.")
        elif v["clear"]:
            pill, head = "Clear answer", "Investing looks better."
            why = (f"Investing in the Nifty 50 beat the guaranteed {v['hurdle_pct']:.1f}% from paying off the loan "
                   f"about {avg:.0f}% of the time.")
        else:
            pill, head = "Close call", "Too close to call."
            why = ("Past data and simulations do not agree, so no answer is safe here. Slightly leaning towards "
                   + ("paying off the loan." if v["leaning"] == "prepay" else "investing."))
        st.markdown(f'<div class="answer"><span class="pill{" soft" if pill == "Close call" else ""}">{pill}</span>'
                    f'<div class="big">{head}</div><div class="msg">{why}</div></div>', unsafe_allow_html=True)

        left, right = st.columns([3, 2])
        with left:
            rates, hist, mc = curve(years, penalty, max(18, int(rate) + 2))
            fig, ax = plt.subplots(figsize=(4.6, 2.7))
            fig.patch.set_facecolor(CARD)
            ax.set_facecolor(CARD)
            ax.plot(rates, hist, color=INK, marker="o", markersize=3.5, linewidth=1.6, label="Past periods")
            ax.plot(rates, mc, color=ROSE, marker="s", markersize=3.5, linewidth=1.6, linestyle="--",
                    label="Simulated futures")
            ax.axhline(50, color=LINE, linewidth=1)
            ax.axvline(rate, color=SLATE, linestyle=":", linewidth=1.3)
            ax.set_ylim(0, 100)
            ax.text(rate - 0.25, 96, "this loan", color=SLATE, fontsize=8.5, style="italic", ha="right", va="top")
            ax.set_xlabel("Loan interest rate (%)", color=INK, fontsize=9)
            ax.set_ylabel("Chance investing wins (%)", color=INK, fontsize=9)
            ax.tick_params(colors=SLATE, labelsize=8)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color(LINE)
            ax.legend(fontsize=8, frameon=False, labelcolor=INK)
            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=220, facecolor=CARD)
            plt.close(fig)
            st.image(buf.getvalue(), width=470)
        with right:
            st.markdown(stat(f"{v['hurdle_pct']:.1f}%", "guaranteed a year from paying off the loan"),
                        unsafe_allow_html=True)
            st.markdown(stat(f"{v['hist_invest_wins_pct']:.0f}%", "of past periods, investing won"),
                        unsafe_allow_html=True)
            st.markdown(stat(f"{v['mc_invest_wins_pct']:.0f}%", "of simulated futures, investing won"),
                        unsafe_allow_html=True)

with st.expander("How this works, and its limits"):
    st.write("The AI only reads the offer. All the maths is done by tested code. Investing is measured against "
             "the Nifty 50 index since 2007, both on real past periods and on thousands of simulated futures "
             "built from reshuffled real market data.")
    st.write("Limits: the index excludes dividends, results are before tax, overlapping past periods are not "
             "independent trials, and past returns do not guarantee future ones. Fees you have already paid "
             "are not counted in the prepay-or-invest answer.")
st.markdown('<p class="note">LoanLens is a learning tool and not financial advice.</p>', unsafe_allow_html=True)