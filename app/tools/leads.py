import json
from pathlib import Path

import httpx
from pydantic import  BaseModel, Field

from app.config import settings
from app.tools.registry import tool


DATA = Path(__file__).resolve().parents[2]/"data"/"leads.json"

def _load():
    return json.loads(DATA.read_text(encoding="utf-8"))

class GetLeadsArgs(BaseModel):
    rm_id: str = Field(description="RM employee id, e.g. RM001")
    status: str | None = Field(default=None, description="Optional filter: new, docs_pending, ready_for_login")

@tool("get_leads", "List leads assigned to an RM, optionally filtered by status.", GetLeadsArgs)
def get_leads(rm_id, status):
    leads = [l for l in _load() if l["rm_id"] == rm_id and (status is None or l["status"] == status)]
    return {"count": len(leads), "leads": leads}


class ScoreLeadArgs(BaseModel):
    lead_id: str = Field(description="Lead id, e.g. L1001")


def _mock_score(lead):
    docs_ratio = len(lead["docs_received"]) / max(len(lead["docs_required"]), 1)
    conv = 0.4 * docs_ratio + (0.3 if lead["employment"] == "salaried" else 0.15) + (0.2 if lead["cibil"] >= 750 else 0.05)
    return {"conversion": round(min(conv, 0.99), 2), "risk": "low" if lead["cibil"] >= 750 else "medium", "source": "mock"}


@tool("score_lead", "Get conversion and risk score for a lead.", ScoreLeadArgs)
def score_lead(lead_id):
    lead = next((l for l in _load() if l["lead_id"] == lead_id), None)
    if not lead:
        return {"error": f"lead {lead_id} not found"}
    if settings.ml_scoring_url:
        r = httpx.post(settings.ml_scoring_url, json=lead, timeout=10)
        r.raise_for_status()
        return r.json()
    return _mock_score(lead)