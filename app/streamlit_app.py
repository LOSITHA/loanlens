import html
import json
import os
import sys
from datetime import date

import numpy as np
import plotly.graph_objects as go
import streamlit as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from loanlens.backtest import load_nifty, rolling_returns
from loanlens.emi import emi
from loanlens.explainer import build_facts, explain, explanation_points
from loanlens import offer_cache
from loanlens.adjust import after_costs_growth, price_hurdle, verdict_adjusted
from loanlens.montecarlo import bootstrap_growth
from loanlens.sanity import check_offer
from loanlens.verdict import effective_prepay_rate_pct
from loanlens.xirr import true_loan_rate

# Palette from the mood board
INK, SLATE, ROSE, PEACH = "#0F3040", "#404858", "#A56F63", "#D9987F"
CREAM, CARD, LINE, TINT, SIDE = "#F7EEE8", "#FFFAF6", "#E6CFC3", "#F3DDD0", "#F1E2D9"
FONT = "Times New Roman, Times, Liberation Serif, serif"

st.set_page_config(page_title="LoanLens", page_icon="🔍", layout="wide", initial_sidebar_state="expanded")

st.markdown(f"""
<style>
.stApp {{ background: {CREAM}; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ max-width: 1560px; padding: 1.2rem 2rem 3rem; }}

/* Times New Roman everywhere, icons keep their own font */
html, body, .stApp, .stApp * {{ font-family: 'Times New Roman', Times, 'Liberation Serif', serif; }}
.stApp [data-testid="stIconMaterial"], .stApp .material-icons {{
  font-family: 'Material Symbols Rounded', 'Material Icons' !important; }}
.stApp, .stApp p, .stApp label, .stApp li, .stApp span, .stApp div {{ color: {INK}; }}
.stApp [data-testid="stCaptionContainer"], .stApp small {{ color: {SLATE}; }}
.stApp p, .stApp label {{ font-size: 1.05rem; }}

/* sidebar = the loan panel */
[data-testid="stSidebar"] {{ background: {SIDE}; border-right: 1px solid {LINE};
  min-width: 390px !important; max-width: 390px !important; width: 390px !important; }}
[data-testid="stSidebar"] .block-container, [data-testid="stSidebarUserContent"] {{ padding-top: 1rem; }}
.sb-brand {{ font-size: 2.3rem; font-weight: 700; color: {INK}; line-height: 1.05; }}
.sb-tag {{ font-size: 1.05rem; color: {SLATE}; margin: 2px 0 14px; }}
.sb-h {{ font-size: 1.3rem; font-weight: 700; color: {INK}; margin: 8px 0 2px; }}
.sb-sub {{ font-size: 1rem; color: {SLATE}; margin-bottom: 8px; }}

/* top band */
.band {{ background: linear-gradient(135deg, {INK} 0%, {SLATE} 100%); border-radius: 20px; padding: 18px 28px;
  margin-bottom: 16px; box-shadow: 0 6px 18px rgba(15,48,64,.14); }}
.band .t {{ font-size: 1.9rem; font-weight: 700; color: {CREAM}; }}
.band .s {{ font-size: 1.1rem; color: #EFDFD6; }}
.band .s i {{ color: {PEACH}; }}

/* KPI cards */
.kpi {{ min-height: 138px; background: {CARD}; border: 1px solid {LINE}; border-radius: 18px; padding: 14px 20px;
  box-shadow: 0 3px 12px rgba(15,48,64,.06); height: 100%; }}
.kpi .l {{ font-size: .88rem; letter-spacing: .09em; text-transform: uppercase; color: {SLATE}; }}
.kpi .v {{ font-size: 2.2rem; font-weight: 700; color: {INK}; line-height: 1.15; }}
.kpi .d {{ font-size: 1rem; color: {SLATE}; }}
.kpi.hot {{ background: {INK}; border-color: {INK}; }}
.kpi.hot .l, .kpi.hot .d {{ color: #EFDFD6; }}
.kpi.hot .v {{ color: #FFFFFF; }}
.kpi .d i {{ color: {ROSE}; }}
.kpi.hot .d i {{ color: {PEACH}; }}

/* chart cards (containers with a key starting with card_) */
[class*="st-key-card_"] {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 18px;
  padding: 16px 20px 14px; margin-bottom: 14px; box-shadow: 0 3px 12px rgba(15,48,64,.06); }}
.ctitle {{ font-size: 1.4rem; font-weight: 700; color: {INK}; margin: 0; }}
.csub {{ font-size: 1rem; color: {SLATE}; margin: 0 0 6px; }}

.offer {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 12px; padding: 10px 14px;
  white-space: pre-wrap; font-size: .98rem; color: {INK}; line-height: 1.4; margin-bottom: 8px; }}
.answer {{ background: {TINT}; border-left: 7px solid {ROSE}; border-radius: 14px; padding: 12px 18px; margin: 4px 0 8px; }}
.answer .big {{ font-size: 1.9rem; font-weight: 700; color: {INK}; line-height: 1.15; }}
.answer .msg {{ font-size: 1.08rem; margin-top: 2px; }}
.pill {{ display: inline-block; border-radius: 999px; padding: 1px 14px; font-size: .92rem; font-weight: 700;
  background: {INK}; color: {CREAM} !important; margin-bottom: 4px; }}
.pill.soft {{ background: {PEACH}; color: {INK} !important; }}
.chip {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 12px; padding: 6px 12px; }}
.chip .v {{ font-size: 1.35rem; font-weight: 700; color: {INK}; line-height: 1.2; }}
.chip .l {{ font-size: .92rem; color: {SLATE}; }}
.pt {{ font-size: 1.1rem; line-height: 1.55; margin: 0 0 10px; }}
.pt .lead {{ font-weight: 700; }}
.explain {{ background: #FFFFFF; border: 1px solid {LINE}; border-left: 7px solid {PEACH}; border-radius: 12px;
  padding: 12px 16px; font-size: 1.08rem; line-height: 1.55; color: {INK}; margin-top: 8px; }}
.note {{ color: {SLATE}; font-size: .98rem; font-style: italic; }}

/* widgets */
.stButton > button {{ background: {INK}; color: {CREAM} !important; border: 0; border-radius: 12px;
  padding: .4rem 1.2rem; font-weight: 700; font-size: 1.02rem; }}
.stButton > button p, .stButton > button span {{ color: #F7EEE8 !important; font-weight: 700; }}
.stButton > button:hover {{ background: {ROSE}; color: #FFFFFF !important; }}
.stButton > button:hover p, .stButton > button:hover span {{ color: #FFFFFF !important; }}
.stApp [data-baseweb="input"], .stApp [data-baseweb="textarea"], .stApp [data-baseweb="select"] > div {{
  background: #FFFFFF !important; border-color: {LINE} !important; border-radius: 10px !important; }}
[data-testid="stSelectbox"] div[data-baseweb="select"] div {{ background-color: #FFFFFF !important; font-size: 1.02rem; }}
.stApp input, .stApp textarea {{ background: transparent !important; color: {INK} !important; }}
[data-testid="stExpander"] {{ background: #FFFFFF; border: 1px solid {LINE}; border-radius: 14px; }}
[data-testid="stExpander"] summary p {{ font-weight: 700; }}
/* smaller windows (for example half a screen): narrower sidebar, columns wrap instead of squeezing */
@media (max-width: 1250px) {{
  [data-testid="stSidebar"] {{ min-width: 330px !important; max-width: 330px !important; width: 330px !important; }}
  .block-container {{ padding: 1rem 1.1rem 3rem; }}
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap; }}
  [data-testid="stMain"] [data-testid="stColumn"] {{ min-width: 400px !important; flex: 1 1 400px !important; }}
  [data-testid="stMain"] [data-testid="stColumn"]:has(.kpi) {{ min-width: 200px !important; flex: 1 1 200px !important; }}
  .st-key-card_b [data-testid="stColumn"] {{ min-width: 150px !important; flex: 1 1 150px !important; }}
  .kpi .v {{ font-size: 1.8rem; }}
}}
</style>
""", unsafe_allow_html=True)


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


# ------------------------------------------------------------------ data (cached)
@st.cache_data
def prices():
    return load_nifty(os.path.join(ROOT, "data", "nifty50.csv"))


@st.cache_data
def sim_data(years):
    """Past-period returns and 5000 simulated futures, computed once per horizon."""
    p = prices()
    rets = rolling_returns(p, years).values
    growth = bootstrap_growth(p, years, 5000)          # same settings the verdict uses
    return rets, growth ** (1 / years) - 1, growth


@st.cache_data
def run_verdict(rate, years, penalty, tax, dividend):
    return verdict_adjusted(prices(), rate, years, penalty_pct=penalty, tax_pct=tax,
                            dividend_pct=dividend, n_sims=5000)


def load_cache():
    path = os.path.join(ROOT, "outputs", "extraction_cache.json")
    return json.load(open(path)) if os.path.exists(path) else {}


def sample_label(k):
    if k.startswith("syn_"):
        n = int(k[4:6])
        return f"No-cost EMI sample {n - 24}" if n >= 25 else f"Loan sample {n + 1}"
    return k


LIVE_CACHE = os.path.join(ROOT, "outputs", "live_cache.json")


def read_offer(text):
    """Saved reading first (no AI call), then the AI reader, then the built-in rule-based reader."""
    saved = offer_cache.get(LIVE_CACHE, text)
    if saved:
        return saved, "saved"
    try:
        from loanlens.extractor import extract_offer
        fields = extract_offer(text, retries=2).model_dump()
        offer_cache.put(LIVE_CACHE, text, fields)
        return fields, "ai"
    except Exception:
        from loanlens.regex_extractor import extract_offer_regex
        return extract_offer_regex(text), "rules"


# ------------------------------------------------------------------ chart helpers
PCONF = {"displayModeBar": False}


def show(fig):
    try:
        st.plotly_chart(fig, width="stretch", config=PCONF)
    except TypeError:                                   # older Streamlit
        st.plotly_chart(fig, use_container_width=True, config=PCONF)


def style(fig, height):
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=36, b=8), paper_bgcolor=CARD, plot_bgcolor=CARD,
                      font=dict(family=FONT, color=INK, size=14),
                      hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=LINE, font=dict(family=FONT, color=INK, size=14)),
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(size=13)))
    return fig


def card_head(title, sub):
    st.markdown(f'<p class="ctitle">{title}</p><p class="csub">{sub}</p>', unsafe_allow_html=True)


def short_inr(x):
    """Rs 2,58,703 -> Rs 2.59L (full amount stays in the hover text)"""
    return f"Rs {x / 1e5:.2f}L" if x >= 1e5 else f"Rs {inr(x)}"


def chip(value, label):
    return f'<div class="chip"><div class="v">{value}</div><div class="l">{label}</div></div>'


def kpi(label, value, detail, hot=False):
    return (f'<div class="kpi{" hot" if hot else ""}"><div class="l">{label}</div>'
            f'<div class="v">{value}</div><div class="d">{detail}</div></div>')


# ================================================================== SIDEBAR: the loan offer
fields, suffix, via = None, "x", "sample"
tax = dividend = 0.0
with st.sidebar:
    st.markdown('<div class="sb-brand">LoanLens</div>'
                '<div class="sb-tag"><i>See what a loan really costs.</i></div>', unsafe_allow_html=True)
    st.markdown('<div class="sb-h">Your loan offer</div>'
                '<div class="sb-sub">Try a sample or paste your own. Change any detail and the whole page updates.</div>',
                unsafe_allow_html=True)
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
        text = st.text_area("Paste the text of your loan offer or EMI message", height=130,
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
            st.warning("The AI reader is busy or unavailable, so the simpler built-in reader was used. "
                       "Please check the details below.")
        if fields and via == "saved":
            st.caption("Reused a saved reading of this exact text, so no AI call was needed.")

    principal = rate = tenure = None
    penalty = proc = ins = other = monthly = 0.0
    if fields:
        missing = [n for k, n in (("principal", "loan amount"), ("annual_rate_pct", "interest rate"),
                                  ("tenure_months", "number of months")) if fields.get(k) is None]
        st.markdown('<div class="sb-h">Details we read</div>', unsafe_allow_html=True)
        if missing:
            st.warning("We could not find the " + ", ".join(missing) + ". Please fill it in.")
        c = st.columns(2)
        principal = c[0].number_input("Loan amount (Rs)", min_value=0.0, step=1000.0, format="%.0f",
                                      value=fields["principal"], placeholder="not found", key="p" + suffix)
        rate = c[1].number_input("Rate (% a year)", min_value=0.0, step=0.1, format="%.2f",
                                 value=fields["annual_rate_pct"], placeholder="not found", key="r" + suffix)
        c = st.columns(2)
        tenure = c[0].number_input("Months to repay", min_value=1, step=1,
                                   value=fields["tenure_months"], placeholder="not found", key="t" + suffix)
        penalty = c[1].number_input("Prepay charge (%)", min_value=0.0, step=0.5,
                                    value=float(fields["prepayment_penalty_pct"] or 0), key="pp" + suffix)
        c = st.columns(2)
        proc = c[0].number_input("Processing fee (Rs)", min_value=0.0, step=100.0,
                                 value=float(fields["processing_fee"] or 0), key="pf" + suffix)
        ins = c[1].number_input("Insurance (Rs)", min_value=0.0, step=100.0,
                                value=float(fields["insurance_premium"] or 0), key="in" + suffix)
        c = st.columns(2)
        other = c[0].number_input("Other upfront fees (Rs)", min_value=0.0, step=100.0,
                                  value=float(fields["other_upfront_fees"] or 0), key="ot" + suffix)
        monthly = c[1].number_input("Fee every month (Rs)", min_value=0.0, step=10.0,
                                    value=float(fields["monthly_fee"] or 0), key="mf" + suffix)

        st.markdown('<div class="sb-h">Investing assumptions (optional)</div>'
                    '<div class="sb-sub">Both start at 0, which compares against the plain index price. '
                    'Change them for a closer-to-real answer.</div>', unsafe_allow_html=True)
        c = st.columns(2)
        tax = c[0].number_input("Tax on gains (%)", min_value=0.0, max_value=40.0, step=0.5, value=0.0, key="tax",
                                help="India taxes long-term gains on listed equity at 12.5%, with the first "
                                     "Rs 1.25 lakh a year exempt. Here the tax is taken on the whole gain, "
                                     "so it is slightly harsh. Please check current rules.")
        dividend = c[1].number_input("Dividends (%)", min_value=0.0, max_value=5.0, step=0.1, value=0.0,
                                     key="div", help="The Nifty 50 has recently paid about 1.2% a year in "
                                                     "dividends. The price index in this app leaves them out.")

# ================================================================== MAIN: the dashboard
st.markdown('<div class="band"><div class="t">Your loan at a glance</div>'
            '<div class="s"><i>Every number and chart below updates</i> when you change the details on the left.</div></div>',
            unsafe_allow_html=True)

if not fields:
    st.info("Choose a sample or paste an offer in the panel on the left to see what it really costs.")
    st.stop()
if not principal or rate is None or not tenure:
    st.info("Fill in the loan amount, interest rate and number of months on the left to continue.")
    st.stop()

upfront = proc + ins + other
for note in check_offer(principal, rate, tenure, penalty, upfront, monthly):
    st.warning(note)
try:
    true_rate = true_loan_rate(principal, rate, int(tenure), date.today(),
                               upfront_fees=upfront, monthly_fees=monthly) * 100
    payment = emi(principal, rate, int(tenure)) + monthly
except Exception:
    st.error("We could not work out the real cost for these numbers. Please check the details on the left.")
    st.stop()
fee_total = upfront + monthly * tenure

# ---- KPI row
k = st.columns(4, gap="medium")
k[0].markdown(kpi("Real yearly cost", f"{true_rate:.1f}%",
                  f"<i>{true_rate - rate:+.1f} points</i> vs advertised", hot=True),
              unsafe_allow_html=True)
k[1].markdown(kpi("Advertised rate", f"{rate:.1f}%", "what the offer says, before fees"), unsafe_allow_html=True)
k[2].markdown(kpi("Monthly payment", f"Rs {inr(payment)}", f"for {int(tenure)} months"), unsafe_allow_html=True)
k[3].markdown(kpi("Fees on top", f"Rs {inr(fee_total)}", f"{fee_total / principal * 100:.1f}% of the loan"),
              unsafe_allow_html=True)
st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# ---- prepay or invest
years, v, outcomes = None, None, None
if rate == 0:
    st.info("This loan charges no interest, so paying it off early saves nothing. "
            "The real cost is the fees shown above.")
else:
    left, right = st.columns([7, 5], gap="medium")

    with right:                                          # controls first, so the left card can use them
        with st.container(key="card_b"):
            card_head("What your spare money could become", "Type how much you could spare, and for how long.")
            c = st.columns(2)
            spare = c[0].number_input("Spare money (Rs)", min_value=1000.0, value=100000.0, step=10000.0, format="%.0f", key="spare")
            years = c[1].select_slider("Keep it for", options=[3, 5], value=5, format_func=lambda y: f"{y} years")
            rets, ann, growth = sim_data(years)
            hurdle = effective_prepay_rate_pct(rate, penalty, years)
            prepay_value = spare * (1 + hurdle / 100) ** years
            grown = after_costs_growth(growth, years, tax, dividend)
            low, mid, high = (spare * np.percentile(grown, q) for q in (5, 50, 95))
            outcomes = dict(spare=spare, prepay_value=prepay_value, invest_typical=mid, invest_bad=low)
            labels = ["Pay off<br>the loan", "Invest:<br>bad case", "Invest:<br>typical", "Invest:<br>good case"]
            vals = [prepay_value, low, mid, high]
            fig = go.Figure(go.Bar(x=labels, y=vals, marker_color=[INK, PEACH, ROSE, SLATE],
                                   text=[short_inr(x) for x in vals], textposition="inside", insidetextanchor="end", textangle=0,
                                   textfont=dict(color=["#FFFFFF", INK, "#FFFFFF", "#FFFFFF"], size=14),
                                   hovertext=[f"Rs {inr(x)} after {years} years" for x in vals], hoverinfo="text",
                                   cliponaxis=False))
            fig.add_hline(y=prepay_value, line_dash="dot", line_color=INK, line_width=1.2)
            fig.update_yaxes(visible=False, range=[0, max(vals) * 1.08])
            fig.update_xaxes(showgrid=False, linecolor=LINE)
            show(style(fig, 330))
            st.caption("Bad case = 1 in 20 simulated futures did worse. Good case = 1 in 20 did better. "
                       "The dotted line is what paying off the loan gives for sure."
                       + (" Investing figures are after the tax and dividends you set on the left."
                          if tax or dividend else ""))

    with left:
        with st.container(key="card_a"):
            card_head("Pay off the loan early, or invest the money?",
                      "Chance that investing in the Nifty 50 beats the guaranteed saving from paying the loan down.")
            v = run_verdict(rate, years, penalty, tax, dividend)
            avg = (v["hist_invest_wins_pct"] + v["mc_invest_wins_pct"]) / 2
            if v["clear"] and v["leaning"] == "prepay":
                pill, head = "Clear answer", "Pay off the loan early."
                why = (f"It earns a guaranteed {v['hurdle_pct']:.1f}% a year. Investing beat that only about {avg:.0f}% of the time.")
            elif v["clear"]:
                pill, head = "Clear answer", "Investing looks better."
                why = (f"Investing beat the guaranteed {v['hurdle_pct']:.1f}% from paying off the loan about {avg:.0f}% of the time.")
            else:
                pill, head = "Close call", "Too close to call."
                why = ("Past data and simulations do not agree, so no answer is safe here. Slightly leaning towards "
                       + ("paying off the loan." if v["leaning"] == "prepay" else "investing."))
            st.markdown(f'<div class="answer"><span class="pill{" soft" if pill == "Close call" else ""}">{pill}</span>'
                        f'<div class="big">{head}</div><div class="msg">{why}</div></div>', unsafe_allow_html=True)

            # curve: exact for any loan rate, because every point comes from the same stored simulations
            xs = np.round(np.arange(4, max(18, int(rate) + 3) + 0.001, 0.25), 2)
            hurdles = ((((1 + xs / 100) ** years) / (1 + penalty / 100)) ** (1 / years) - 1)
            hurdles = price_hurdle(hurdles, years, tax, dividend)
            hist = [(rets > h).mean() * 100 for h in hurdles]
            mc = [(ann > h).mean() * 100 for h in hurdles]
            fig = go.Figure()
            fig.add_hrect(y0=0, y1=40, fillcolor=ROSE, opacity=0.09, line_width=0)
            fig.add_hrect(y0=60, y1=100, fillcolor=INK, opacity=0.06, line_width=0)
            fig.add_hline(y=50, line_color=LINE, line_width=1)
            fig.add_trace(go.Scatter(x=xs, y=hist, name="Past periods", mode="lines", line=dict(color=INK, width=3),
                                     hovertemplate="Loan at %{x:.2f}%: investing won %{y:.0f}% of past periods<extra></extra>"))
            fig.add_trace(go.Scatter(x=xs, y=mc, name="Simulated futures", mode="lines",
                                     line=dict(color=ROSE, width=3, dash="dash"),
                                     hovertemplate="Loan at %{x:.2f}%: investing won %{y:.0f}% of simulated futures<extra></extra>"))
            fig.add_trace(go.Scatter(x=[rate, rate], y=[v["hist_invest_wins_pct"], v["mc_invest_wins_pct"]],
                                     name="This loan", mode="markers",
                                     marker=dict(size=13, color=[INK, ROSE], line=dict(color="#FFFFFF", width=2)),
                                     hovertemplate="This loan (%{x:.2f}%): %{y:.0f}%<extra></extra>"))
            fig.add_vline(x=rate, line_dash="dot", line_color=SLATE, line_width=1.3)
            fig.add_annotation(x=rate, y=100, text="this loan", showarrow=False, xanchor="left", yanchor="top",
                               xshift=6, font=dict(size=13, color=SLATE))
            fig.add_annotation(x=4.1, y=96, text="Investing wins here", showarrow=False, xanchor="left",
                               font=dict(size=12, color=SLATE))
            fig.add_annotation(x=4.1, y=4, text="Paying off wins here", showarrow=False, xanchor="left",
                               font=dict(size=12, color=ROSE))
            fig.update_xaxes(title="Loan interest rate (% a year)", showgrid=False, linecolor=LINE, ticksuffix="%")
            fig.update_yaxes(title="Chance investing wins", range=[0, 100], gridcolor="#F0E3DA", zeroline=False,
                             ticksuffix="%")
            show(style(fig, 330))

# ---- a simple explanation
facts = build_facts(principal, rate, tenure, penalty, upfront, monthly, true_rate, payment, years, v, outcomes)
with st.container(key="card_d"):
    card_head("A simple explanation", "Written from the numbers above, so it changes when you change the loan.")
    a, b = st.columns([6, 5], gap="large")
    with a:
        for lead, txt in explanation_points(facts):
            st.markdown(f'<p class="pt"><span class="lead">{lead}</span> {html.escape(txt)}</p>', unsafe_allow_html=True)
        fid = f"{suffix}|{sorted(facts.items())}"
        if st.button("Say it in friendlier words (uses AI)"):
            with st.spinner("Asking the AI..."):
                st.session_state["friendly"] = (fid,) + explain(facts, "English")
        done = st.session_state.get("friendly")
        if done and done[0] == fid:
            if done[2] == "template-fallback":
                st.caption("The AI is busy or out of free quota right now, so the explanation above is the built-in one.")
            else:
                st.markdown(f'<div class="explain">{html.escape(done[1])}</div>', unsafe_allow_html=True)
                st.caption("Reworded by AI. Every number in it is checked against the maths first.")
    with b:
        interest = max((payment - monthly) * tenure - principal, 0)
        parts = [("What you borrow", principal, INK), ("Interest", interest, ROSE), ("Fees", fee_total, PEACH)]
        total_paid = sum(p[1] for p in parts)
        fig = go.Figure(go.Pie(labels=[f"{p[0]} ({p[1] / total_paid * 100:.1f}%)" for p in parts],
                               values=[p[1] for p in parts], hole=0.62,
                               marker=dict(colors=[p[2] for p in parts], line=dict(color=CARD, width=3)),
                               textinfo="none", sort=False, direction="clockwise",
                               hovertemplate="%{label}<br>Rs %{customdata}<extra></extra>",
                               customdata=[inr(p[1]) for p in parts]))
        fig.add_annotation(text=f"You pay back<br><b>Rs {inr(principal + interest + fee_total)}</b>",
                           showarrow=False, font=dict(size=15, color=INK))
        fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center"))
        show(style(fig, 330))

with st.expander("How this works, and its limits"):
    st.write("The AI only reads the offer and, if you ask, rewords the explanation. All the maths is done by tested code. "
             "Investing is measured against the Nifty 50 index since 2007, both on real past periods and on thousands "
             "of simulated futures built from reshuffled real market data.")
    st.write("Limits: unless you add them in the left panel, the index excludes dividends and results are before tax "
             "(tax there is a simple estimate on the whole gain). Overlapping past periods are not "
             "independent trials, and past returns do not guarantee future ones. Fees you have already paid "
             "are not counted in the prepay-or-invest answer.")
st.markdown('<p class="note">LoanLens is a learning tool and not financial advice.</p>', unsafe_allow_html=True)
