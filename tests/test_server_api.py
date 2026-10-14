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


if __name__ == "__main__":
    unittest.main()
