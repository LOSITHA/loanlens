import json
import pytest
from loanlens import explainer as ex

FACTS = dict(principal=200000, stated_rate=13.5, true_rate=21.3, fees=11220, monthly_payment=9548,
             tenure_months=24, penalty_pct=4.0, total_interest=29000, total_paid=240220, answer="prepay", years=5, hurdle=12.5, past_pct=30, simulated_pct=34)


def test_template_mentions_key_numbers():
    t = ex.template_explanation(FACTS)
    assert "21.3%" in t and "13.5%" in t and "11,220" in t and "not financial advice" in t


def test_template_no_cost():
    f = dict(FACTS, stated_rate=0.0, answer=None)
    assert "0% interest" in ex.template_explanation(f)


def test_guard_accepts_facts_and_rejects_invented_numbers():
    assert ex.numbers_are_safe("The real cost is 21.3% not 13.5%. Fees are Rs 11,220 over 24 months.", FACTS)
    assert not ex.numbers_are_safe("The real cost is 25% a year.", FACTS)


def test_ai_text_with_invented_number_falls_back(monkeypatch, tmp_path):
    monkeypatch.setattr(ex, "CACHE_PATH", str(tmp_path / "c.json"))
    monkeypatch.setattr(ex, "_call_gemini", lambda p: "Real cost is 99% a year.")
    text, src = ex.explain(FACTS, "Hindi")
    assert src == "template-fallback" and "21.3%" in text


def test_good_ai_text_is_used_then_cached(monkeypatch, tmp_path):
    monkeypatch.setattr(ex, "CACHE_PATH", str(tmp_path / "c.json"))
    monkeypatch.setattr(ex, "_call_gemini", lambda p: "Asli kharcha 21.3% hai, 13.5% nahi.")
    assert ex.explain(FACTS, "Hindi")[1] == "ai"

    def boom(p):
        raise RuntimeError("no network")
    monkeypatch.setattr(ex, "_call_gemini", boom)
    text, src = ex.explain(FACTS, "Hindi")      # second time: served from the saved file
    assert src == "saved" and "21.3%" in text


def test_api_failure_falls_back_to_template(monkeypatch, tmp_path):
    monkeypatch.setattr(ex, "CACHE_PATH", str(tmp_path / "c.json"))

    def boom(p):
        raise RuntimeError("503")
    monkeypatch.setattr(ex, "_call_gemini", boom)
    assert ex.explain(FACTS, "Tamil")[1] == "template-fallback"


def test_points_include_total_paid_and_spare_money():
    f = dict(FACTS, spare=100000, prepay_value=180000, invest_typical=170000, invest_bad=120000)
    t = ex.template_explanation(f)
    assert "2,40,220" in t and "1,00,000" in t and "1,20,000" in t
    assert ex.numbers_are_safe(t, f)


def test_old_facts_without_new_keys_still_work():
    f = {k: v for k, v in FACTS.items() if k not in ("total_interest", "total_paid")}
    assert "11,220" in ex.template_explanation(f)


def test_index_name_is_not_treated_as_a_number():
    assert ex.numbers_are_safe("Investing in the Nifty 50 beat 12.5% only 32% of the time.", FACTS)
