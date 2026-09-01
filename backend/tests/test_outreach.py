import unittest

from app.services.outreach import validate_transition


class OutreachTransitionTests(unittest.TestCase):
    def test_valid_forward_transition(self):
        self.assertEqual(validate_transition("NOT_CONTACTED", "IN_PROGRESS"), "IN_PROGRESS")
        self.assertEqual(validate_transition("IN_PROGRESS", "RESOLVED"), "RESOLVED")

    def test_cannot_skip_directly_to_resolved(self):
        with self.assertRaisesRegex(ValueError, "Invalid outreach transition"):
            validate_transition("NOT_CONTACTED", "RESOLVED")

    def test_same_status_is_idempotent(self):
        self.assertEqual(validate_transition("IN_PROGRESS", "IN_PROGRESS"), "IN_PROGRESS")


if __name__ == "__main__":
    unittest.main()
