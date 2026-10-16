import app.tools
from app.tools.eligibility import calc_eligibility, ltv_cap
from app.tools.registry import REGISTRY


def test_ltv_slabs():
    assert ltv_cap(25_00_000) == 0.90
    assert ltv_cap(50_00_000) == 0.80
    assert ltv_cap(1_00_00_000) == 0.75


def test_eligibility_ltv_bound():
    r = calc_eligibility(monthly_income=65000, existing_emi=8000, property_value=2800000, tenure_years=20, roi=9.5)
    assert r["eligible_amount"] == 2520000
    assert "Limited by LTV, not income" in r["flags"]


def test_obligations_exceed_foir():
    r = calc_eligibility(monthly_income=40000, existing_emi=25000, property_value=2000000, tenure_years=20, roi=None)
    assert r["eligible_amount"] == 0


def test_invalid_args_return_error():
    out = REGISTRY["calc_eligibility"].run({"monthly_income": -5, "property_value": 100})
    assert out["error"] == "invalid_arguments"


def test_checklist_pending():
    out = REGISTRY["doc_checklist"].run({"profile": "self_employed", "docs_received": ["pan"]})
    assert "PAN" not in out["pending"]
    assert "Audited financials" in out["pending"]


def test_triage_sorted():
    out = REGISTRY["triage_leads"].run({"rm_id": "RM001"})
    scores = [l["conversion"] for l in out["top"]]
    assert scores == sorted(scores, reverse=True)