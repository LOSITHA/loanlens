import pytest
from loanlens.regex_extractor import extract_offer_regex


def test_letter_with_percent_fee_and_gst():
    o = extract_offer_regex(
        "EASY-PAY LOAN OFFER\nCongratulations! You are pre-approved for a personal loan of Rs 2,00,000.\n"
        "Tenure: 24 months. Interest rate: 13.5% p.a. (reducing balance).\n"
        "Processing fee: 2% of loan amount + 18% GST.\n"
        "Credit life insurance (mandatory): Rs 6,500 one-time.\n"
        "Prepayment charges: 4% of outstanding principal.")
    assert o["principal"] == 200000
    assert o["annual_rate_pct"] == 13.5
    assert o["tenure_months"] == 24
    assert o["processing_fee"] == pytest.approx(4720)
    assert o["insurance_premium"] == 6500
    assert o["prepayment_penalty_pct"] == 4


def test_no_cost_emi():
    o = extract_offer_regex("NO-COST EMI! Product price Rs 30,000. Pay in 6 easy monthly instalments. "
                            "Interest: 0%. One-time processing fee: Rs 799 + 18% GST.")
    assert o["principal"] == 30000 and o["annual_rate_pct"] == 0 and o["tenure_months"] == 6
    assert o["processing_fee"] == pytest.approx(942.82)


def test_lakh_and_years():
    o = extract_offer_regex("Facility: Rs. 5 Lakh term loan\nTenure: 5 years\nROI: 10.5% p.a.")
    assert o["principal"] == 500000 and o["tenure_months"] == 60 and o["annual_rate_pct"] == 10.5


def test_gst_inclusive_not_added_twice():
    o = extract_offer_regex("Loan Rs 54,999 for 9 months. Interest 0%. Processing fee Rs 399 inclusive of GST.")
    assert o["processing_fee"] == 399


def test_missing_fields_are_none_not_guessed():
    o = extract_offer_regex("Loan of Rs 1,20,000 sanctioned. Interest rate 15% p.a. Tenure not yet decided.")
    assert o["tenure_months"] is None
    assert o["processing_fee"] is None and o["insurance_premium"] is None


def test_hinglish_lakh_without_rs():
    o = extract_offer_regex("aapka 3 lakh ka loan approved hai. 11.99% interest, 36 mahine. "
                            "Bima (insurance) Rs 8,000 compulsory hai.")
    assert o["principal"] == 300000 and o["tenure_months"] == 36 and o["insurance_premium"] == 8000


def test_words_are_not_understood():
    # known limit of rules: numbers written as words
    o = extract_offer_regex("Two lakh fifty thousand rupees, interest eleven percent per annum.")
    assert o["principal"] is None and o["annual_rate_pct"] is None