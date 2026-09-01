"""Model metadata route."""

from flask import Blueprint, jsonify

from app.services.outreach import get_state_machine_info
from app.services.risk_scoring import get_model_info


model_bp = Blueprint("model", __name__)


@model_bp.get("/model/info")
def model_info():
    response = get_model_info()
    response["outreach_state_machine"] = get_state_machine_info()
    return jsonify(response), 200
