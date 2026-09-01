"""Rule-based churn risk scoring.

The assessment treats this heuristic as a stand-in for a production ML model.
The score is intentionally transparent so a retention agent can understand why
someone is considered at risk.
"""

from __future__ import annotations

from typing import Any, Dict, List


RISK_TIERS = [
    {"tier": "HIGH", "min_score": 65, "max_score": 100},
    {"tier": "MEDIUM", "min_score": 35, "max_score": 64},
    {"tier": "LOW", "min_score": 0, "max_score": 34},
]

SCORING_RULES = [
    {
        "id": "month_to_month_contract",
        "label": "Month-to-month contract",
        "points": 30,
        "reason": "Shorter commitments make cancellation easier and deserve closer retention attention.",
    },
    {
        "id": "new_customer",
        "label": "Tenure under 12 months",
        "points": 20,
        "reason": "Customers early in the relationship may not yet be strongly retained.",
    },
    {
        "id": "developing_customer",
        "label": "Tenure from 12 to 23 months",
        "points": 10,
        "reason": "Customers with limited tenure still receive a smaller early-lifecycle risk contribution.",
    },
    {
        "id": "no_tech_support",
        "label": "No Tech Support",
        "points": 15,
        "reason": "Internet customers without support may have fewer resources to resolve service issues.",
    },
    {
        "id": "no_online_security",
        "label": "No Online Security",
        "points": 10,
        "reason": "Missing value-added services can indicate a less embedded customer relationship.",
    },
    {
        "id": "very_high_monthly_charge",
        "label": "Monthly charges at or above $90",
        "points": 15,
        "reason": "Higher monthly cost can increase price sensitivity.",
    },
    {
        "id": "high_monthly_charge",
        "label": "Monthly charges from $70 to $89.99",
        "points": 8,
        "reason": "Elevated monthly cost contributes a smaller pricing-pressure signal.",
    },
    {
        "id": "electronic_check",
        "label": "Electronic check payment method",
        "points": 10,
        "reason": "This payment method is treated as a small operational friction signal in the heuristic.",
    },
]


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _add_factor(factors: List[Dict[str, Any]], rule_id: str) -> None:
    rule = next(rule for rule in SCORING_RULES if rule["id"] == rule_id)
    factors.append(
        {
            "id": rule["id"],
            "label": rule["label"],
            "points": rule["points"],
            "reason": rule["reason"],
        }
    )


def tier_for_score(score: int) -> str:
    if score >= 65:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


def calculate_risk(customer: Dict[str, Any]) -> Dict[str, Any]:
    """Return transparent heuristic risk score, tier, and applied factors."""
    factors: List[Dict[str, Any]] = []

    if str(customer.get("Contract", "")).strip() == "Month-to-month":
        _add_factor(factors, "month_to_month_contract")

    tenure = _number(customer.get("tenure"))
    if tenure < 12:
        _add_factor(factors, "new_customer")
    elif tenure < 24:
        _add_factor(factors, "developing_customer")

    internet_service = str(customer.get("InternetService", "")).strip()
    if internet_service != "No":
        if str(customer.get("TechSupport", "")).strip() == "No":
            _add_factor(factors, "no_tech_support")
        if str(customer.get("OnlineSecurity", "")).strip() == "No":
            _add_factor(factors, "no_online_security")

    monthly_charges = _number(customer.get("MonthlyCharges"))
    if monthly_charges >= 90:
        _add_factor(factors, "very_high_monthly_charge")
    elif monthly_charges >= 70:
        _add_factor(factors, "high_monthly_charge")

    if str(customer.get("PaymentMethod", "")).strip() == "Electronic check":
        _add_factor(factors, "electronic_check")

    score = min(sum(factor["points"] for factor in factors), 100)
    return {
        "score": int(score),
        "tier": tier_for_score(int(score)),
        "factors": factors,
    }


def get_model_info() -> Dict[str, Any]:
    """Describe the current heuristic so the UI can explain the model."""
    return {
        "model_name": "Churn Risk Heuristic v1",
        "model_type": "rule_based_heuristic",
        "score_range": {"min": 0, "max": 100},
        "note": (
            "The score is an explainable prioritization heuristic, not a calibrated churn probability. "
            "In production, the same console could consume scores from a versioned ML service."
        ),
        "risk_tiers": RISK_TIERS,
        "rules": SCORING_RULES,
    }
