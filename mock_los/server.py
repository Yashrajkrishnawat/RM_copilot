import json
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException

DATA = Path(__file__).resolve().parents[1] / "data" / "leads.json"
API_KEY = os.getenv("MOCK_LOS_KEY", "dev-key")

app = FastAPI(title="Mock LOS API")


def check_key(x_api_key: str = Header(default="")):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


def _all():
    return json.loads(DATA.read_text(encoding="utf-8"))


@app.get("/leads", dependencies=[Depends(check_key)])
def list_leads(rm_id: str, status: str | None = None, q: str | None = None):
    leads = [l for l in _all() if l["rm_id"] == rm_id]
    if status:
        leads = [l for l in leads if l["status"] == status]
    if q:
        ql = q.lower()
        leads = [l for l in leads if ql == l["lead_id"].lower() or ql in l["name"].lower()]
    return leads


@app.get("/leads/{lead_id}", dependencies=[Depends(check_key)])
def get_lead(lead_id: str):
    lead = next((l for l in _all() if l["lead_id"].upper() == lead_id.upper()), None)
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")
    return lead