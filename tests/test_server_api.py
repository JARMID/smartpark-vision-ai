"""
API and Integration Tests for Smart Park FastAPI Server.
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

    def test_cameras_endpoint(self):
        response = self.client.get("/api/cameras")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ONLINE")
        self.assertEqual(data["total_cameras"], 4)
        self.assertIn("cameras", data)
        self.assertEqual(data["cameras"][0]["camera_id"], "cam_lane1_entry_plate")

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

    def test_simulate_duplicate_plate_fraud(self):
        payload = {"scenario": "duplicate_plate_fraud"}
        response = self.client.post("/api/simulate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["result"], "denied_antipassback")
        self.assertFalse(data["barrier_opened"])
        self.assertEqual(data["error_code"], "CLONED_PLATE_OR_DOUBLE_ENTRY_VIOLATION")
        self.assertIn("A01", data["message"])

    def test_active_vehicles_and_exit_endpoint(self):
        # 1. Inspect inside vehicles
        response = self.client.get("/api/active-vehicles")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ONLINE")
        self.assertTrue(data["antipassback_enabled"])
        self.assertGreaterEqual(data["total_inside"], 3)

        # 2. Process vehicle exit for 104822 119 16
        exit_res = self.client.post("/api/exit", json={"plate": "104822 119 16"})
        self.assertEqual(exit_res.status_code, 200)
        exit_data = exit_res.json()
        self.assertEqual(exit_data["result"], "cleared_exit")
        self.assertTrue(exit_data["barrier_opened"])
        self.assertTrue(exit_data["is_vip"])

    def test_barrier_manual_override(self):
        # Valid channel 1
        res1 = self.client.post("/api/barrier/override", json={"channel": 1, "duration_ms": 500})
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(res1.json()["success"])

        # Valid channel 2 with duration clamping
        res2 = self.client.post("/api/barrier/override", json={"channel": 2, "duration_ms": 3000})
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.json()["success"])

        # Invalid channel (e.g. 3) rejected with 400
        res_bad = self.client.post("/api/barrier/override", json={"channel": 3, "duration_ms": 500})
        self.assertEqual(res_bad.status_code, 400)

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

    def test_compliance_dpia_endpoint(self):
        res = self.client.post("/api/compliance/dpia", json={
            "dpo_name": "Karim Meziane",
            "dpo_phone": "+213 550 44 33 22"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["dossier_type"], "DPIA_ANPDP_ALGERIA")
        self.assertEqual(data["facility_metadata"]["dpo_officer"], "Karim Meziane")
        self.assertTrue(len(data["data_categories_processed"]) >= 3)

    def test_compliance_register_endpoint(self):
        res = self.client.get("/api/compliance/register")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(len(data) >= 4)
        self.assertTrue(any("ALPR" in item["activity_name"] for item in data))

    def test_compliance_breach_triage_endpoint(self):
        res = self.client.post("/api/compliance/breach/triage", json={
            "incident_type": "INTRUSION_RESEAU_SUSPECTE",
            "severity": "CRITICAL",
            "description": "Scan de ports anormaux sur VLAN 20",
            "impacted_records": 10
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["severity"], "CRITICAL")
        self.assertEqual(data["status"], "TRIAGE_OPEN")
        self.assertGreaterEqual(data["hours_remaining_until_statutory_breach"], 119)

    def test_compliance_purge_endpoint(self):
        res = self.client.post("/api/compliance/purge")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["anpdp_status"], "CONFORME_CYCLE_PURGE_AUTOMATIQUE")
        self.assertIn("records_purged", data)

    def test_chargily_webhook_endpoint(self):
        import hmac
        import hashlib
        import json
        payload = {"event": "checkout.paid", "id": "ch_inv_998811", "metadata": {"plate_number": "08192 120 09"}}
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        secret = "test_secret_hmac_chargily_satim"
        valid_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

        # Valid signature via JSON envelope
        res_ok = self.client.post("/api/chargily/webhook", json={
            "payload": payload,
            "signature": valid_sig
        })
        self.assertEqual(res_ok.status_code, 200)
        self.assertEqual(res_ok.json()["payment_status"], "PAID")

        # Valid signature via HTTP Signature header with raw JSON body
        raw_payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        raw_sig = hmac.new(secret.encode("utf-8"), raw_payload_bytes, hashlib.sha256).hexdigest()
        res_header = self.client.post(
            "/api/chargily/webhook",
            content=raw_payload_bytes,
            headers={"signature": raw_sig, "content-type": "application/json"}
        )
        self.assertEqual(res_header.status_code, 200)
        self.assertEqual(res_header.json()["payment_status"], "PAID")

        # Invalid signature
        res_bad = self.client.post("/api/chargily/webhook", json={
            "payload": payload,
            "signature": "tampered_signature_dz"
        })
        self.assertEqual(res_bad.status_code, 401)

    def test_wilaya_geocode_endpoint(self):
        # Known Wilaya 16 (Alger)
        res_alger = self.client.get("/api/external/wilaya-geocode/16")
        self.assertEqual(res_alger.status_code, 200)
        data = res_alger.json()
        self.assertTrue(data["found"])
        self.assertEqual(data["name_fr"], "Alger")
        self.assertEqual(data["name_ar"], "الجزائر")
        self.assertAlmostEqual(data["lat"], 36.7538, places=3)

        # Unknown Wilaya
        res_unknown = self.client.get("/api/external/wilaya-geocode/99")
        self.assertEqual(res_unknown.status_code, 200)
        self.assertFalse(res_unknown.json()["found"])

    def test_weather_lighting_endpoint(self):
        res = self.client.get("/api/external/weather-lighting")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("location", data)
        self.assertIn("lighting_mode", data)
        self.assertIn(data["lighting_mode"], ["DAY", "NIGHT"])
        self.assertIn("ambient_lux", data)

    def test_currency_rates_endpoint(self):
        res = self.client.get("/api/external/currency-rates")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["base_currency"], "DZD")
        self.assertIn("EUR", data["rates"])
        self.assertIn("USD", data["rates"])
        self.assertGreater(data["rates"]["EUR"], 100.0)

    def test_ntp_audit_sync_endpoint(self):
        res = self.client.get("/api/external/ntp-audit-sync")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["stratum"], 1)
        self.assertTrue(data["law_25_11_nonce"].startswith("NONCE-"))

    def test_daily_operational_report(self):
        res = self.client.get("/api/reports/daily")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["report_id"].startswith("RPT-"))
        self.assertEqual(data["wilaya_code"], "16")
        self.assertIn("operational_metrics", data)
        self.assertIn("anpdp_law_25_11_audit", data)
        self.assertEqual(data["anpdp_law_25_11_audit"]["compliance_status"], "CERTIFIED_SOVEREIGN")

    def test_export_audit_csv(self):
        res = self.client.get("/api/reports/export/csv")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("content-type"), "text/csv; charset=utf-8")
        text = res.text
        self.assertTrue(text.startswith("Timestamp,EventID,PlateNumber"))
        self.assertIn("Wilaya", text)
        self.assertIn("ANPDPNonce", text)

    def test_mobile_web_route(self):
        res = self.client.get("/mobile")
        # In testing environment, if static/mobile/index.html is compiled it returns 200
        self.assertIn(res.status_code, [200, 404])


if __name__ == "__main__":
    unittest.main()


