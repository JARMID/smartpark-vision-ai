"""
API and Integration Tests for SmartPark Vision AI FastAPI Server.
Verifies REST endpoints, simulation scenarios, and ANPDP Law 25-11 compliance exports.
"""

import unittest
import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.server import app


class TestServerAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_status_endpoint(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["system_status"], "ONLINE")
        self.assertIn("occupancy", data)
        self.assertIn("ups_status", data)
        self.assertEqual(data["ups_status"]["power_source"], "ON_LINE_AC")

    def test_slots_endpoint(self):
        response = self.client.get("/api/slots")
        self.assertEqual(response.status_code, 200)
        slots = response.json()
        self.assertTrue(len(slots) > 0)
        self.assertIn("slot_number", slots[0])
        self.assertIn("zone_name", slots[0])
        self.assertIn("status", slots[0])

    def test_simulate_vip_entry(self):
        payload = {"scenario": "vip_entry"}
        response = self.client.post("/api/simulate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["result"], "cleared_vip")
        self.assertTrue(data["barrier_opened"])
        self.assertEqual(data["plate"], "104822 119 16")

    def test_simulate_temporary_00(self):
        payload = {"scenario": "temporary_00"}
        response = self.client.post("/api/simulate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["result"], "cleared_visitor")
        self.assertTrue(data["barrier_opened"])
        self.assertEqual(data["plate"], "08412 00 16")

    def test_simulate_watchlist_alert(self):
        payload = {"scenario": "watchlist_alert"}
        response = self.client.post("/api/simulate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["result"], "denied_blacklist")
        self.assertFalse(data["barrier_opened"])

    def test_simulate_spoof_attack(self):
        payload = {"scenario": "spoof_attack"}
        response = self.client.post("/api/simulate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["result"], "denied_spoof")
        self.assertFalse(data["barrier_opened"])

    def test_barrier_manual_override(self):
        payload = {"channel": 1, "duration_ms": 500}
        response = self.client.post("/api/barrier/override", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    def test_anpdp_compliance_endpoint(self):
        response = self.client.get("/api/compliance/anpdp")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["law_25_11_compliant"])
        self.assertIn("dpia_summary", data)
        self.assertIn("processing_register", data)

    def test_chargily_checkout_and_pay(self):
        # 1. Create checkout
        checkout_res = self.client.post("/api/chargily/create-checkout", json={
            "plate": "08192 120 09",
            "amount_dzd": 200.0,
            "card_type": "EDAHABIA"
        })
        self.assertEqual(checkout_res.status_code, 200)
        cdata = checkout_res.json()
        self.assertIn("checkout_id", cdata)
        self.assertEqual(cdata["amount_dzd"], 200.0)

        # 2. Pay checkout with valid 6-digit OTP
        pay_res = self.client.post("/api/chargily/pay", json={
            "checkout_id": cdata["checkout_id"],
            "otp_code": "481902"
        })
        self.assertEqual(pay_res.status_code, 200)
        pdata = pay_res.json()
        self.assertTrue(pdata["success"])
        self.assertEqual(pdata["status"], "PAID")
        self.assertTrue(pdata["barrier_opened"])

    def test_guard_manual_decision_grant_and_deny(self):
        grant_res = self.client.post("/api/guard/decision", json={
            "plate": "04122 118 16",
            "decision": "grant",
            "reason": "Épouse du titulaire vérifiée"
        })
        self.assertEqual(grant_res.status_code, 200)
        self.assertTrue(grant_res.json()["barrier_opened"])

        deny_res = self.client.post("/api/guard/decision", json={
            "plate": "04122 118 16",
            "decision": "deny",
            "reason": "Conducteur non autorisé"
        })
        self.assertEqual(deny_res.status_code, 200)
        self.assertFalse(deny_res.json()["barrier_opened"])

    def test_slot_toggle(self):
        res = self.client.post("/api/slots/toggle", json={
            "slot_number": "A03"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("occupancy", data)

    def test_ticket_generation(self):
        res = self.client.post("/api/tickets/generate", json={
            "plate": "08412 00 16",
            "zone": "Zone B"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("ticket_id", data)
        self.assertIn("qr_data", data)
        self.assertIn("barcode", data)
        self.assertEqual(data["plate"], "08412 00 16")


if __name__ == "__main__":
    unittest.main()
