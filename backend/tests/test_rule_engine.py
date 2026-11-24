from types import SimpleNamespace
from app.eligibility.extractor import TenderRequirements
from app.eligibility.rule_engine import evaluate_company

def test_turnover_failure_is_deterministic():
    profile = SimpleNamespace(annual_turnover_inr=1000000, years_in_business=2,
        udyam_number=None, dpiit_startup_number=None, gstin="22ABCDE1234F1Z5", pan_last_four="1234")
    req = TenderRequirements(minimum_annual_turnover_inr=5000000)
    result = evaluate_company(profile, [], [], req)
    assert result["recommendation"] == "NO_BID"
    assert result["checks"][0]["status"] == "FAIL"

def test_missing_turnover_evidence_is_not_a_pass():
    profile = SimpleNamespace(annual_turnover_inr=None, years_in_business=None,
        udyam_number=None, dpiit_startup_number=None, gstin=None, pan_last_four=None)
    req = TenderRequirements(minimum_annual_turnover_inr=5000000)
    result = evaluate_company(profile, [], [], req)
    assert result["checks"][0]["status"] == "MISSING_EVIDENCE"
    assert result["recommendation"] == "REVIEW_REQUIRED"


def test_tender_specific_msme_relaxation_requires_verification():
    profile = SimpleNamespace(annual_turnover_inr=1000000, years_in_business=1,
        udyam_number="UDYAM-UP-00-0000001", dpiit_startup_number=None, gstin=None, pan_last_four=None)
    req = TenderRequirements(minimum_annual_turnover_inr=5000000,
        turnover_relaxation_permitted=True, relaxation_beneficiaries=["msme"],
        emd_amount_inr=50000, emd_exemption_permitted=True)
    result = evaluate_company(profile, [], [], req)
    assert result["checks"][0]["status"] == "NEEDS_VERIFICATION"
    assert result["checks"][1]["status"] == "NEEDS_VERIFICATION"
    assert result["recommendation"] == "REVIEW_REQUIRED"
