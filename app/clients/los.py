import json
from pathlib import Path

import httpx

from app.config import settings

DATA = Path(__file__).resolve().parents[2] / "data" / "leads.json"


class LOSError(Exception):
    pass


class JsonLOS:
    def _all(self):
        return json.loads(DATA.read_text(encoding="utf-8"))

    def list_leads(self, rm_id, status=None):
        return [l for l in self._all() if l["rm_id"] == rm_id and (status is None or l["status"] == status)]

    def get_lead(self, lead_id):
        return next((l for l in self._all() if l["lead_id"].upper() == lead_id.upper()), None)

    def search(self, rm_id, query):
        q = query.lower()
        return [l for l in self.list_leads(rm_id) if q == l["lead_id"].lower() or q in l["name"].lower()]


class ApiLOS:
    def __init__(self):
        headers = {"X-API-Key": settings.los_api_key} if settings.los_api_key else {}
        self.http = httpx.Client(base_url=settings.los_api_url, timeout=settings.los_timeout, headers=headers)

    def _get(self, path, params=None):
        try:
            r = self.http.get(path, params=params)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise LOSError(f"LOS API returned {e.response.status_code}")
        except httpx.RequestError as e:
            raise LOSError(f"LOS API unreachable ({e.__class__.__name__})")

    def list_leads(self, rm_id, status=None):
        params = {"rm_id": rm_id}
        if status:
            params["status"] = status
        return self._get("/leads", params) or []

    def get_lead(self, lead_id):
        return self._get(f"/leads/{lead_id}")

    def search(self, rm_id, query):
        return self._get("/leads", {"rm_id": rm_id, "q": query}) or []


los = ApiLOS() if settings.leads_source == "api" else JsonLOS()