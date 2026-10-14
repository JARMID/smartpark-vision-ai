"""
Unit tests for Chargily Pay V2 domestic payment client and HMAC signature verification.
"""

import hashlib
import hmac
import json
import unittest
from datetime import datetime, timedelta
from src.payment.chargily_v2_client import ChargilyV2PaymentClient


class TestChargilyV2PaymentClient(unittest.TestCase):

    def setUp(self):
        self.secret = "test_secret_hmac_chargily_satim"
        self.client = ChargilyV2PaymentClient(
            api_key="test_sk_smartpark_2026",
            secret_key=self.secret,
            tariff_per_hour_dzd=100.0,
        )

    def test_tariff_calculation_under_15_minutes_free(self):
        entry = datetime.now() - timedelta(minutes=12)
        calc = self.client.calculate_tariff(entry_time=entry)
        self.assertEqual(calc["amount_dzd"], 0.0)
        self.assertEqual(calc["billable_hours"], 0)

    def test_tariff_calculation_two_hours(self):
        entry = datetime.now() - timedelta(minutes=110)
        calc = self.client.calculate_tariff(entry_time=entry)
        self.assertEqual(calc["billable_hours"], 2)
        self.assertEqual(calc["amount_dzd"], 200.0)

    def test_checkout_session_creation(self):
        session = self.client.create_checkout_session(
            plate_number="08192 120 09",
            session_id="sess-test-4819",
            amount_dzd=200.0,
            payment_method="CIB",
        )
        self.assertTrue(session["success"])
        self.assertIn("ch_dz_", session["checkout_id"])
        self.assertEqual(session["amount_dzd"], 200.0)
        self.assertEqual(session["metadata"]["grace_period_minutes"], 15)

    def test_hmac_signature_verification_valid(self):
        payload = json.dumps({"event": "checkout.paid", "id": "ch_dz_99120"}).encode("utf-8")
        valid_sig = hmac.new(self.secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

        is_valid = self.client.verify_webhook_signature(payload_bytes=payload, signature_header=valid_sig)
        self.assertTrue(is_valid)

    def test_hmac_signature_verification_invalid(self):
        payload = json.dumps({"event": "checkout.paid", "id": "ch_dz_99120"}).encode("utf-8")
        is_valid = self.client.verify_webhook_signature(payload_bytes=payload, signature_header="invalid_tampered_sig")
        self.assertFalse(is_valid)

    def test_payment_confirmation_grants_15_minute_grace_window(self):
        conf = self.client.process_payment_confirmation(
            checkout_id="ch_dz_179192",
            plate_number="08192 120 09",
        )
        self.assertTrue(conf["success"])
        self.assertEqual(conf["exit_window_minutes"], 15)
        self.assertEqual(conf["payment_status"], "PAID")


if __name__ == "__main__":
    unittest.main()
