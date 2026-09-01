"""Customer API routes."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request


customers_bp = Blueprint("customers", __name__)


def _store():
    return current_app.config["CUSTOMER_STORE"]


def _positive_int(name: str, default: int, maximum: int | None = None) -> int:
    raw = request.args.get(name)
    if raw is None or raw == "":
        value = default
    else:
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError(f"{name} must be an integer") from exc

    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be at most {maximum}")
    return value


@customers_bp.get("/customers")
def get_customers():
    try:
        page = _positive_int("page", 1)
        page_size = _positive_int("page_size", 20, maximum=100)
        result = _store().query_customers(
            page=page,
            page_size=page_size,
            risk_tier=request.args.get("risk_tier") or None,
            contract=request.args.get("contract") or None,
            outreach_status=request.args.get("outreach_status") or None,
            search=request.args.get("search") or None,
            sort=request.args.get("sort", "risk_desc"),
        )
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": "bad_request", "message": str(exc)}), 400


@customers_bp.get("/customers/<customer_id>")
def get_customer(customer_id: str):
    customer = _store().get_customer(customer_id)
    if customer is None:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": f"Customer '{customer_id}' was not found.",
                }
            ),
            404,
        )
    return jsonify(customer), 200


@customers_bp.patch("/customers/<customer_id>/outreach")
def update_outreach(customer_id: str):
    try:
        payload = request.get_json(silent=False)
    except Exception:
        return (
            jsonify({"error": "bad_request", "message": "Request body must contain valid JSON."}),
            400,
        )

    if not isinstance(payload, dict) or "status" not in payload:
        return (
            jsonify(
                {
                    "error": "bad_request",
                    "message": "Request body must be a JSON object with a 'status' field.",
                }
            ),
            400,
        )

    try:
        customer = _store().update_outreach(customer_id, payload["status"])
    except ValueError as exc:
        return jsonify({"error": "invalid_transition", "message": str(exc)}), 400

    if customer is None:
        return (
            jsonify(
                {
                    "error": "not_found",
                    "message": f"Customer '{customer_id}' was not found.",
                }
            ),
            404,
        )

    return jsonify(customer), 200
