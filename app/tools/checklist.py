from typing import Literal

from pydantic import BaseModel, Field

from app.tools.registry import tool

BASE =["PAN", "Aadhaar", "Photograph", "Property documents"]
BY_PROFILE = {
    "salaried": ["Last 3 salary slips", "6 months bank statement", "Form 16 / ITR (2 yrs)"],
    "self_employed": ["ITR with computation (3 yrs)", "12 months bank statement", "Business proof (GST/Udyam)",
                      "Audited financials"],
    "nri": ["Passport & visa", "Overseas salary slips", "NRE/NRO statement", "PoA document"],
}

class ChecklistArgs(BaseModel):
    profile: Literal["salaried", "self_employed", "nri"]
    docs_received: list[str] = Field(default_factory=list)


@tool("doc_checklist", "Build the document checklist for a customer profile and show what is pending.", ChecklistArgs)
def doc_checklist(profile, docs_received):
    required = BASE + BY_PROFILE[profile]
    got = {d.lower() for d in docs_received}
    pending = [d for d in required if d.lower() not in got]
    return {"required": required, "pending": pending, "complete": not pending}