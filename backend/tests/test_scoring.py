import unittest

from app.services.risk_scoring import calculate_risk


class RiskScoringTests(unittest.TestCase):
    def test_high_risk_customer_accumulates_explainable_factors(self):
        customer = {
            "Contract": "Month-to-month",
            "tenure": 3,
            "InternetService": "Fiber optic",
            "TechSupport": "No",
            "OnlineSecurity": "No",
            "MonthlyCharges": 95.0,
            "PaymentMethod": "Electronic check",
        }

        result = calculate_risk(customer)

        self.assertEqual(result["score"], 100)
        self.assertEqual(result["tier"], "HIGH")
        self.assertIn("Month-to-month contract", [f["label"] for f in result["factors"]])

    def test_low_risk_customer_has_zero_score_when_no_rule_applies(self):
        customer = {
            "Contract": "Two year",
            "tenure": 60,
            "InternetService": "DSL",
            "TechSupport": "Yes",
            "OnlineSecurity": "Yes",
            "MonthlyCharges": 55.0,
            "PaymentMethod": "Credit card (automatic)",
        }

        result = calculate_risk(customer)

        self.assertEqual(result["score"], 0)
        self.assertEqual(result["tier"], "LOW")
        self.assertEqual(result["factors"], [])


if __name__ == "__main__":
    unittest.main()
