"""CSV loading and in-memory customer store."""

from __future__ import annotations

import math
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from app.services.outreach import allowed_next_statuses, validate_transition
from app.services.risk_scoring import calculate_risk


SUMMARY_FIELDS = (
    "customerID",
    "tenure",
    "Contract",
    "InternetService",
    "MonthlyCharges",
    "outreach_status",
    "risk_score",
    "risk_tier",
)


class CustomerStore:
    """Thread-safe in-memory store for the life of the running server."""

    def __init__(self, dataset_path: str | Path):
        self.dataset_path = Path(dataset_path)
        self._customers: Dict[str, Dict[str, Any]] = {}
        self._ordered_ids: List[str] = []
        self._lock = threading.RLock()
        self._load()

    def _load(self) -> None:
        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset not found at {self.dataset_path}. "
                "Place the bundled WA_Fn-UseC_-Telco-Customer-Churn.csv in the root data/ folder."
            )

        try:
            frame = pd.read_csv(self.dataset_path)
        except (OSError, pd.errors.ParserError) as exc:
            raise RuntimeError(f"Unable to read dataset: {exc}") from exc

        required = {"customerID", "tenure", "Contract", "MonthlyCharges"}
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(f"Dataset is missing required column(s): {', '.join(missing)}")

        customers: Dict[str, Dict[str, Any]] = {}
        for row in frame.to_dict(orient="records"):
            customer = self._clean_record(row)
            customer_id = str(customer["customerID"]).strip()
            if not customer_id:
                continue

            risk = calculate_risk(customer)
            customer["risk_score"] = risk["score"]
            customer["risk_tier"] = risk["tier"]
            customer["risk_factors"] = risk["factors"]
            customer["outreach_status"] = "NOT_CONTACTED"
            customers[customer_id] = customer

        if not customers:
            raise ValueError("Dataset did not contain any usable customers")

        self._customers = customers
        # Default operational priority: highest risk first, then customer id for stable ordering.
        self._ordered_ids = sorted(
            customers,
            key=lambda cid: (-customers[cid]["risk_score"], cid),
        )

    @staticmethod
    def _clean_record(record: Dict[str, Any]) -> Dict[str, Any]:
        cleaned: Dict[str, Any] = {}
        for key, value in record.items():
            if pd.isna(value):
                cleaned[key] = None
            elif hasattr(value, "item"):
                cleaned[key] = value.item()
            else:
                cleaned[key] = value

        for int_field in ("SeniorCitizen", "tenure"):
            if int_field in cleaned and cleaned[int_field] is not None:
                cleaned[int_field] = int(cleaned[int_field])

        for float_field in ("MonthlyCharges", "TotalCharges"):
            if float_field in cleaned and cleaned[float_field] not in (None, ""):
                try:
                    cleaned[float_field] = float(cleaned[float_field])
                except (TypeError, ValueError):
                    cleaned[float_field] = None

        return cleaned

    def count(self) -> int:
        return len(self._customers)

    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            customer = self._customers.get(customer_id)
            if customer is None:
                return None
            result = deepcopy(customer)
            result["allowed_outreach_transitions"] = allowed_next_statuses(
                result["outreach_status"]
            )
            return result

    def update_outreach(self, customer_id: str, requested_status: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            customer = self._customers.get(customer_id)
            if customer is None:
                return None
            validated_status = validate_transition(customer["outreach_status"], requested_status)
            customer["outreach_status"] = validated_status
            result = deepcopy(customer)
            result["allowed_outreach_transitions"] = allowed_next_statuses(validated_status)
            return result

    def query_customers(
        self,
        *,
        page: int,
        page_size: int,
        risk_tier: Optional[str] = None,
        contract: Optional[str] = None,
        outreach_status: Optional[str] = None,
        search: Optional[str] = None,
        sort: str = "risk_desc",
    ) -> Dict[str, Any]:
        with self._lock:
            customers = [self._customers[cid] for cid in self._ordered_ids]
            filtered = self._apply_filters(
                customers,
                risk_tier=risk_tier,
                contract=contract,
                outreach_status=outreach_status,
                search=search,
            )
            filtered = self._sort(filtered, sort)

            total = len(filtered)
            total_pages = max(1, math.ceil(total / page_size)) if total else 0
            start = (page - 1) * page_size
            end = start + page_size
            page_records = filtered[start:end] if start < total else []

            summary = {
                "matching_customers": total,
                "high_risk": sum(1 for c in filtered if c["risk_tier"] == "HIGH"),
                "not_contacted": sum(
                    1 for c in filtered if c["outreach_status"] == "NOT_CONTACTED"
                ),
                "in_progress": sum(
                    1 for c in filtered if c["outreach_status"] == "IN_PROGRESS"
                ),
                "resolved": sum(1 for c in filtered if c["outreach_status"] == "RESOLVED"),
            }

            items = [
                {field: deepcopy(customer.get(field)) for field in SUMMARY_FIELDS}
                for customer in page_records
            ]

            return {
                "items": items,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                },
                "summary": summary,
                "filters": {
                    "risk_tier": risk_tier,
                    "contract": contract,
                    "outreach_status": outreach_status,
                    "search": search,
                    "sort": sort,
                },
            }

    @staticmethod
    def _apply_filters(
        customers: Iterable[Dict[str, Any]],
        *,
        risk_tier: Optional[str],
        contract: Optional[str],
        outreach_status: Optional[str],
        search: Optional[str],
    ) -> List[Dict[str, Any]]:
        result = list(customers)

        if risk_tier:
            normalized_tier = risk_tier.strip().upper()
            if normalized_tier not in {"LOW", "MEDIUM", "HIGH"}:
                raise ValueError("risk_tier must be LOW, MEDIUM, or HIGH")
            result = [c for c in result if c["risk_tier"] == normalized_tier]

        if contract:
            contract_value = contract.strip().lower()
            result = [
                c for c in result if str(c.get("Contract", "")).strip().lower() == contract_value
            ]

        if outreach_status:
            normalized_status = outreach_status.strip().upper()
            if normalized_status not in {"NOT_CONTACTED", "IN_PROGRESS", "RESOLVED"}:
                raise ValueError(
                    "outreach_status must be NOT_CONTACTED, IN_PROGRESS, or RESOLVED"
                )
            result = [c for c in result if c["outreach_status"] == normalized_status]

        if search:
            term = search.strip().lower()
            result = [
                c
                for c in result
                if term in str(c.get("customerID", "")).lower()
            ]

        return result

    @staticmethod
    def _sort(customers: List[Dict[str, Any]], sort: str) -> List[Dict[str, Any]]:
        if sort == "risk_desc":
            return sorted(customers, key=lambda c: (-c["risk_score"], c["customerID"]))
        if sort == "risk_asc":
            return sorted(customers, key=lambda c: (c["risk_score"], c["customerID"]))
        if sort == "monthly_desc":
            return sorted(
                customers,
                key=lambda c: (-(c.get("MonthlyCharges") or 0), c["customerID"]),
            )
        if sort == "tenure_asc":
            return sorted(customers, key=lambda c: (c.get("tenure") or 0, c["customerID"]))
        raise ValueError("sort must be risk_desc, risk_asc, monthly_desc, or tenure_asc")
