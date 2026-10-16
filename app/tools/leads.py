import httpx
from pydantic import BaseModel, Field

from app.clients.los import los
from app.config import settings
from app.tools.registry import tool


def _pending(lead):
    return [d for d in lead["docs_required"] if d not in lead["docs_received"]]


class GetLeadsArgs(BaseModel):
    rm_id: str = Field(description="RM employee id, e.g. RM001")
    status: str | None = Field(default=None, description="Optional filter: new, docs_pending, ready_for_login")


@tool("get_leads", "List leads assigned to an RM, optionally filtered by status.", GetLeadsArgs)
def get_leads(rm_id, status):
    leads = los.list_leads(rm_id, status)
    return {"count": len(leads), "leads": [{"lead_id": l["lead_id"], "name": l["name"], "status": l["status"]} for l in leads]}


class FindCustomerArgs(BaseModel):
    rm_id: str = Field(description="RM employee id, e.g. RM001")
    query: str = Field(description="Customer name (or part of it) or lead id, e.g. 'Ramesh' or 'L1001'")


@tool("find_customer", "Look up a customer's profile, income, EMIs, property value, status and pending documents by name or lead id.", FindCustomerArgs)
def find_customer(rm_id, query):
    matches = los.search(rm_id, query)
    if not matches:
        return {"error": f"no customer matching '{query}' for {rm_id}"}
    if len(matches) > 1:
        return {"multiple_matches": [{"lead_id": l["lead_id"], "name": l["name"]} for l in matches]}
    l = matches[0]
    return {
        "lead_id": l["lead_id"], "name": l["name"], "employment": l["employment"], "city": l.get("city"),
        "monthly_income": l["monthly_income"], "existing_emi": l["existing_emi"],
        "property_value": l["property_value"], "loan_requested": l.get("loan_requested"),
        "cibil": l["cibil"], "status": l["status"], "last_contacted": l.get("last_contacted"),
        "pending_docs": _pending(l),
    }


class ScoreLeadArgs(BaseModel):
    lead_id: str = Field(description="Lead id, e.g. L1001")


def _mock_score(lead):
    docs_ratio = len(lead["docs_received"]) / max(len(lead["docs_required"]), 1)
    conv = 0.4 * docs_ratio + (0.3 if lead["employment"] == "salaried" else 0.15) + (0.2 if lead["cibil"] >= 750 else 0.05)
    return {"conversion": round(min(conv, 0.99), 2), "risk": "low" if lead["cibil"] >= 750 else "medium", "source": "mock"}


@tool("score_lead", "Get conversion and risk score for a lead.", ScoreLeadArgs)
def score_lead(lead_id):
    lead = los.get_lead(lead_id)
    if not lead:
        return {"error": f"lead {lead_id} not found"}
    if settings.ml_scoring_url:
        r = httpx.post(settings.ml_scoring_url, json=lead, timeout=10)
        r.raise_for_status()
        return r.json()
    return _mock_score(lead)


class TriageArgs(BaseModel):
    rm_id: str = Field(description="RM employee id, e.g. RM001")
    top_n: int = Field(default=3, ge=1, le=10)


@tool("triage_leads", "Rank an RM's leads by priority. Use for 'which leads should I work on first'.", TriageArgs)
def triage_leads(rm_id, top_n):
    ranked = []
    for l in los.list_leads(rm_id):
        s = _mock_score(l) if not settings.ml_scoring_url else score_lead(l["lead_id"])
        ranked.append({
            "lead_id": l["lead_id"], "name": l["name"], "status": l["status"],
            "conversion": s.get("conversion", 0), "risk": s.get("risk"), "pending_docs": _pending(l),
        })
    ranked.sort(key=lambda x: x["conversion"], reverse=True)
    return {"count": len(ranked), "top": ranked[:top_n]}