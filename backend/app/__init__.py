"""Flask application factory."""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

from app.data_access.customer_store import CustomerStore
from app.routes.customers import customers_bp
from app.routes.model import model_bp


def _configure_logging(app: Flask) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    _configure_logging(app)

    project_root = Path(__file__).resolve().parents[2]
    default_dataset = project_root / "data" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"

    app.config.update(
        DATASET_PATH=os.environ.get("DATASET_PATH", str(default_dataset)),
        FRONTEND_ORIGIN=os.environ.get("FRONTEND_ORIGIN", "http://localhost:8000"),
        JSON_SORT_KEYS=False,
    )
    if config:
        app.config.update(config)

    # Load the dataset once during application startup, as requested by the assessment.
    app.config["CUSTOMER_STORE"] = CustomerStore(app.config["DATASET_PATH"])

    app.register_blueprint(customers_bp)
    app.register_blueprint(model_bp)

    @app.before_request
    def begin_request_log():
        g.request_started_at = time.perf_counter()

    @app.after_request
    def finish_request(response):
        duration_ms = round((time.perf_counter() - g.request_started_at) * 1000, 2)
        app.logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                }
            )
        )

        # The frontend is intentionally a separate HTTP client. Limit CORS to its local origin.
        response.headers["Access-Control-Allow-Origin"] = app.config["FRONTEND_ORIGIN"]
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, PATCH, OPTIONS"
        return response

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "customers_loaded": app.config["CUSTOMER_STORE"].count()})

    @app.errorhandler(HTTPException)
    def http_error(error):
        return (
            jsonify(
                {
                    "error": error.name.lower().replace(" ", "_"),
                    "message": error.description,
                }
            ),
            error.code,
        )

    @app.errorhandler(Exception)
    def internal_error(error):
        app.logger.error("Unexpected application failure", exc_info=True)
        return (
            jsonify(
                {
                    "error": "internal_server_error",
                    "message": "An unexpected error occurred. Please try again.",
                }
            ),
            500,
        )

    return app
