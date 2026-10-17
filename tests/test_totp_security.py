"""
Unit and Integration Tests for Smart Park RFC 6238 TOTP Two-Factor Authentication.
Validates Google Authenticator compatibility, cryptographic test vectors,
provisioning URIs, SVG QR code generation, FastAPI endpoints, and Desktop Station gatekeeping.
"""

import base64
import time
import unittest
from fastapi.testclient import TestClient

from src.security.totp import (
    generate_totp_secret,
    format_secret_display,
    get_totp_provisioning_uri,
    generate_totp_code,
    verify_totp_code,
    generate_qr_svg,
    totp_service,
)
from src.server import app
from desktop.src.db import DesktopDatabase
from desktop.src.operator_window import DesktopBridgeApi


class TestTOTPSecurity(unittest.TestCase):
    """Test suite for TOTP cryptographic functions and Google Authenticator integration."""

    def setUp(self):
        self.client = TestClient(app)
        # Reset global service state for isolation
        totp_service.enforce_for_barrier_override = False
        totp_service.enforce_for_compliance_purge = False

    def test_rfc6238_standard_test_vectors(self):
        """Verify compliance with official RFC 6238 test vectors (Appendix B)."""
        secret_ascii = b"12345678901234567890"
        secret_b32 = base64.b32encode(secret_ascii).decode("ascii")

        vectors = [
            (59, "94287082"),
            (1111111109, "07081804"),
            (1111111111, "14050471"),
            (1234567890, "89005924"),
            (2000000000, "69279037"),
        ]
        for timestamp, expected_8digit in vectors:
            actual = generate_totp_code(secret=secret_b32, timestamp=timestamp, digits=8)
            self.assertEqual(actual, expected_8digit)

    def test_secret_generation_and_formatting(self):
        """Verify Base32 secret generation and human display formatting."""
        secret = generate_totp_secret(length=32)
        self.assertEqual(len(secret), 32)
        # Base32 characters: A-Z, 2-7
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")
        self.assertTrue(all(c in valid_chars for c in secret))

        formatted = format_secret_display(secret)
        self.assertEqual(len(formatted.split(" ")), 8)

    def test_provisioning_uri_and_qr_svg(self):
        """Verify Google Authenticator URI structure and SVG rendering."""
        secret = "JBSWY3DPEHPK3PXP"
        uri = get_totp_provisioning_uri(
            secret=secret,
            account_name="Amine Meziane",
            issuer="Smart Park Alger",
        )
        self.assertTrue(uri.startswith("otpauth://totp/"))
        self.assertIn("Smart%20Park%20Alger", uri)
        self.assertIn("secret=JBSWY3DPEHPK3PXP", uri)
        self.assertIn("digits=6", uri)
        self.assertIn("period=30", uri)

        svg = generate_qr_svg(uri)
        self.assertTrue(svg.startswith("<svg") or "<svg" in svg)
        self.assertIn("</svg>", svg)

    def test_verification_drift_and_replay_protection(self):
        """Verify code verification, drift window (+/- 30s), and replay prevention."""
        secret = generate_totp_secret(32)
        now = time.time()
        current_code = generate_totp_code(secret=secret, timestamp=now)

        # 1. Valid code verification
        ok, step = verify_totp_code(secret=secret, code=current_code, timestamp=now)
        self.assertTrue(ok)
        self.assertIsNotNone(step)

        # 2. Replay attack rejection within same time step
        ok_replay, _ = verify_totp_code(
            secret=secret,
            code=current_code,
            timestamp=now,
            last_verified_step=step,
        )
        self.assertFalse(ok_replay)

        # 3. Allow drift of -1 step (30 seconds in past)
        past_code = generate_totp_code(secret=secret, timestamp=now - 30)
        ok_drift, step_drift = verify_totp_code(secret=secret, code=past_code, timestamp=now, window=1)
        self.assertTrue(ok_drift)

        # 4. Reject drift outside window (65 seconds in past)
        ancient_code = generate_totp_code(secret=secret, timestamp=now - 65)
        ok_ancient, _ = verify_totp_code(secret=secret, code=ancient_code, timestamp=now, window=1)
        self.assertFalse(ok_ancient)

        # 5. Invalid digits rejection
        ok_bad, _ = verify_totp_code(secret=secret, code="abc123", timestamp=now)
        self.assertFalse(ok_bad)

    def test_totp_service_activation_lifecycle(self):
        """Verify operator enrollment, activation, and deactivation lifecycle."""
        op_id = "OP-TEST-AGENT"
        setup_data = totp_service.get_or_create_operator_secret(op_id, "Test Agent")
        self.assertEqual(setup_data["operator_id"], op_id)
        self.assertFalse(setup_data["is_enabled"])

        secret = setup_data["secret"]
        valid_code = generate_totp_code(secret)

        # Activation with correct code
        ok, msg = totp_service.verify_and_activate(op_id, valid_code)
        self.assertTrue(ok)
        self.assertTrue(totp_service._secrets[op_id]["is_enabled"])

        # Deactivation with wrong code fails
        ok_deact_bad, _ = totp_service.deactivate(op_id, "000000")
        self.assertFalse(ok_deact_bad)

        # Deactivation with valid code succeeds
        now = time.time() + 35  # Advance step to avoid replay collision
        fresh_code = generate_totp_code(secret, timestamp=now)
        ok_deact, _ = totp_service.deactivate(op_id, fresh_code)
        self.assertTrue(ok_deact)
        self.assertFalse(totp_service._secrets[op_id]["is_enabled"])

    def test_fastapi_totp_endpoints(self):
        """Verify REST API endpoints for Google Authenticator setup and policy toggle."""
        # 1. Setup endpoint
        res = self.client.get("/api/auth/totp/setup?operator_id=OP-API-TEST")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("secret", data)
        self.assertIn("provisioning_uri", data)
        self.assertIn("qr_svg", data)

        secret = data["secret"]
        code = generate_totp_code(secret)

        # 2. Verify and activate endpoint
        res_verify = self.client.post("/api/auth/totp/verify", json={
            "operator_id": "OP-API-TEST",
            "code": code,
        })
        self.assertEqual(res_verify.status_code, 200)
        self.assertTrue(res_verify.json()["success"])

        # 3. Status endpoint
        res_status = self.client.get("/api/auth/totp/status")
        self.assertEqual(res_status.status_code, 200)
        self.assertGreaterEqual(res_status.json()["active_2fa_operators"], 1)

        # 4. Toggle policy endpoint
        res_toggle = self.client.post("/api/auth/totp/toggle", json={
            "operator_id": "OP-API-TEST",
            "code": code,
            "enforce_barrier_override": True,
        })
        self.assertEqual(res_toggle.status_code, 200)
        self.assertTrue(totp_service.enforce_for_barrier_override)

    def test_barrier_override_with_totp_enforcement(self):
        """Verify that barrier override requires a TOTP code when policy is enforced."""
        op_id = "OP-ENFORCE-TEST"
        setup = totp_service.get_or_create_operator_secret(op_id, "Guard")
        secret = setup["secret"]
        valid_code = generate_totp_code(secret)
        totp_service.verify_and_activate(op_id, valid_code)

        # Enable barrier override 2FA policy
        totp_service.enforce_for_barrier_override = True

        # 1. Attempt override without code -> 403 Forbidden
        res_no_code = self.client.post("/api/barrier/override", json={
            "channel": 1,
            "operator_id": op_id,
            "reason": "Test non-autorise",
        })
        self.assertEqual(res_no_code.status_code, 403)

        # 2. Attempt override with wrong code -> 403 Forbidden
        res_wrong_code = self.client.post("/api/barrier/override", json={
            "channel": 1,
            "operator_id": op_id,
            "totp_code": "999999",
            "reason": "Test code erroné",
        })
        self.assertEqual(res_wrong_code.status_code, 403)

        # 3. Attempt override with correct code -> 200 OK
        now = time.time() + 35
        fresh_code = generate_totp_code(secret, timestamp=now)
        res_valid = self.client.post("/api/barrier/override", json={
            "channel": 1,
            "operator_id": op_id,
            "totp_code": fresh_code,
            "reason": "Test 2FA Valide",
        })
        self.assertEqual(res_valid.status_code, 200)
        self.assertTrue(res_valid.json()["totp_verified"])

    def test_desktop_database_totp_persistence(self):
        """Verify SQLite persistence of operator TOTP secret keys in desktop db."""
        import tempfile
        import os

        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_totp.db")
        db = DesktopDatabase(db_path=db_path)

        secret = generate_totp_secret()
        db.save_operator_totp(
            operator_id="AGENT-TEST",
            operator_name="Karim Test",
            secret_key=secret,
            is_enabled=False,
            enforce_on_barrier=True,
        )

        rec = db.get_operator_totp("AGENT-TEST")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["secret_key"], secret)
        self.assertEqual(rec["is_enabled"], 0)
        self.assertEqual(rec["enforce_on_barrier"], 1)

        # Update status
        db.update_operator_totp_status("AGENT-TEST", is_enabled=True, last_step=12345)
        rec2 = db.get_operator_totp("AGENT-TEST")
        self.assertEqual(rec2["is_enabled"], 1)
        self.assertEqual(rec2["last_verified_step"], 12345)

        db.close()

    def test_desktop_bridge_api_totp_methods(self):
        """Verify DesktopBridgeApi 2FA methods and barrier triggering gate."""
        import uuid
        test_cashier = f"AGENT-BRIDGE-{uuid.uuid4().hex[:6]}"
        bridge = DesktopBridgeApi(
            server_url="http://127.0.0.1:8080",
            booth_id="BOOTH-TEST",
            cashier_id=test_cashier,
        )
        info = bridge.get_totp_setup_info()
        self.assertIn("qr_svg", info)
        self.assertIn("secret", info)
        self.assertFalse(info["is_enabled"])

        # Activate 2FA on Desktop Bridge
        secret = info["secret"]
        code = generate_totp_code(secret)
        res_act = bridge.verify_and_enable_totp(code=code, enforce_on_barrier=True)
        self.assertTrue(res_act["success"])
        self.assertTrue(bridge.is_2fa_required_for_barrier())

        # Trigger barrier without TOTP code -> rejected
        res_block = bridge.trigger_barrier(channel=1)
        self.assertFalse(res_block["success"])
        self.assertTrue(res_block.get("requires_totp"))

        # Trigger barrier with valid TOTP code -> accepted
        now = time.time() + 35
        fresh_code = generate_totp_code(secret, timestamp=now)
        res_pass = bridge.trigger_barrier(channel=1, totp_code=fresh_code, timestamp=now)
        self.assertTrue(res_pass["success"])

        # Disable 2FA
        now2 = now + 35
        fresh_code2 = generate_totp_code(secret, timestamp=now2)
        res_dis = bridge.disable_totp(code=fresh_code2, timestamp=now2)
        self.assertTrue(res_dis["success"])
        self.assertFalse(bridge.is_2fa_required_for_barrier())

        bridge.pos_manager.db.close()


if __name__ == "__main__":
    unittest.main()
