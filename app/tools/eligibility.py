from pydantic import BaseModel, Field

from app.config import settings
from app.tools.registry import tool


class EligibilityArgs(BaseModel):
    monthly_income: float = Field(gt=0, description="Net monthly income in INR")
    existing_emi: float = Field(ge=0, default=0, description="Total existing monthly EMIs in INR")
    property_value: float = Field(gt=0, description="Property market value in INR")
    tenure_years: int = Field(ge=1, le=30, default=20)
    roi: float | None = Field(default=None, description="Annual interest rate %, optional")


def ltv_cap(property_value):
    if property_value <= 30_00_000:
        return 0.90
    if property_value <= 75_00_000:
        return 0.80
    return 0.75


def emi(principal, annual_rate, months):
    r = annual_rate / 1200
    return principal * r * (1 + r) ** months / ((1 + r) ** months - 1)

@tool("calc_eligibility", "Calculate indicative home loan eligibility, EMI, FOIR and LTV.", EligibilityArgs)
def calc_eligibility(monthly_income, existing_emi, property_value, tenure_years, roi):
    roi = roi or settings.default_roi
    n = tenure_years * 12
    r = roi / 1200
    flags = []

    max_emi = monthly_income * settings.foir_cap - existing_emi
    if max_emi <= 0:
        return {"eligible_amount": 0, "flags": ["Existing EMIs exceed FOIR cap"]}

    by_income = max_emi * ((1 + r) ** n - 1) / (r * (1 + r) ** n)
    cap = ltv_cap(property_value)
    by_ltv = property_value * cap
    amount = round(min(by_income, by_ltv), -3)

    if by_ltv < by_income:
        flags.append("Limited by LTV, not income")
    if existing_emi / monthly_income > 0.3:
        flags.append("High existing obligations")

    new_emi = emi(amount, roi, n)
    return {
        "eligible_amount": amount,
        "emi": round(new_emi),
        "foir": round((existing_emi + new_emi) / monthly_income, 3),
        "ltv": round(amount / property_value, 3),
        "ltv_cap": cap,
        "roi": roi,
        "tenure_years": tenure_years,
        "flags": flags,
    }