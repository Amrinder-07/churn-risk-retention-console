import tempfile
import unittest
from pathlib import Path

import pandas as pd

from app import create_app


class CustomerApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        dataset = Path(self.temp_dir.name) / "customers.csv"
        pd.DataFrame(
            [
                {
                    "customerID": "A-001",
                    "gender": "Female",
                    "SeniorCitizen": 0,
                    "Partner": "No",
                    "Dependents": "No",
                    "tenure": 3,
                    "PhoneService": "Yes",
                    "MultipleLines": "No",
                    "InternetService": "Fiber optic",
                    "OnlineSecurity": "No",
                    "OnlineBackup": "No",
                    "DeviceProtection": "No",
                    "TechSupport": "No",
                    "StreamingTV": "No",
                    "StreamingMovies": "No",
                    "Contract": "Month-to-month",
                    "PaperlessBilling": "Yes",
                    "PaymentMethod": "Electronic check",
                    "MonthlyCharges": 95.0,
                    "TotalCharges": 285.0,
                    "Churn": "Yes",
                },
                {
                    "customerID": "B-002",
                    "gender": "Male",
                    "SeniorCitizen": 0,
                    "Partner": "Yes",
                    "Dependents": "Yes",
                    "tenure": 60,
                    "PhoneService": "Yes",
                    "MultipleLines": "No",
                    "InternetService": "DSL",
                    "OnlineSecurity": "Yes",
                    "OnlineBackup": "Yes",
                    "DeviceProtection": "Yes",
                    "TechSupport": "Yes",
                    "StreamingTV": "No",
                    "StreamingMovies": "No",
                    "Contract": "Two year",
                    "PaperlessBilling": "No",
                    "PaymentMethod": "Credit card (automatic)",
                    "MonthlyCharges": 55.0,
                    "TotalCharges": 3300.0,
                    "Churn": "No",
                },
            ]
        ).to_csv(dataset, index=False)

        app = create_app({"TESTING": True, "DATASET_PATH": str(dataset)})
        self.client = app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_customers_endpoint_is_paginated_and_filterable(self):
        response = self.client.get("/customers?page=1&page_size=1&risk_tier=HIGH")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["pagination"]["page_size"], 1)
        self.assertEqual(payload["pagination"]["total"], 1)
        self.assertEqual(payload["items"][0]["customerID"], "A-001")

    def test_outreach_endpoint_rejects_invalid_jump(self):
        response = self.client.patch(
            "/customers/A-001/outreach",
            json={"status": "RESOLVED"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "invalid_transition")


if __name__ == "__main__":
    unittest.main()
