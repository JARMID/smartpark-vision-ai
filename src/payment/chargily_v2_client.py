"""
Smart Park - Chargily Pay V2 Domestic Payment Rails Client.
Facilitates automated Pay-on-Foot / Pre-Exit QR settlements for Algerian CIB
and Algérie Poste EDAHABIA cards via SATIM gateway with HMAC SHA-256 signature verification.
"""

from datetime import datetime, timedelta
import hashlib
import hmac
import json
import time
from typing import Dict, Optional, Any


class ChargilyV2PaymentClient:
    """
    Domestic payment client interfacing with Chargily Pay V2 for sovereign Algerian parking tariffs.
    """

    def __init__(
        self,
        api_key: str = "test_sk_smartpark_chargily_v2_2026",
        secret_key: str = "test_secret_hmac_chargily_satim",
        simulation_mode: bool = True,
        tariff_per_hour_dzd: float = 100.0,
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.simulation_mode = simulation_mode
        self.tariff_per_hour_dzd = tariff_per_hour_dzd
        self.exit_grace_period_minutes = 15  # 15-minute departure grace window

    def calculate_tariff(self, entry_time: datetime, exit_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Calculates parking tariff based on parked duration and 15-minute initial grace period.
        """
        now = exit_time or datetime.now()
        duration_seconds = max(0, int((now - entry_time).total_seconds()))
        duration_minutes = duration_seconds // 60

        # First 15 minutes is completely free (drop-off grace)
        if duration_minutes <= 15:
            amount_dzd = 0.0
            billable_hours = 0
        else:
            # Hourly billing rounded up
            billable_hours = max(1, (duration_minutes + 59) // 60)
            amount_dzd = billable_hours * self.tariff_per_hour_dzd

        return {
            "duration_minutes": duration_minutes,
            "billable_hours": billable_hours,
            "amount_dzd": round(amount_dzd, 2),
            "tariff_rate_dzd": self.tariff_per_hour_dzd,
            "currency": "DZD",
        }

    def create_checkout_session(
        self,
        plate_number: str,
        session_id: str,
        amount_dzd: float,
        payment_method: str = "EDAHABIA",
    ) -> Dict[str, Any]:
        """
        Creates a Chargily Pay V2 checkout session for the visitor.
        """
        now = datetime.now()
        checkout_id = f"ch_dz_{int(now.timestamp())}_{plate_number.replace(' ', '')}"

        # Webhook payload metadata
        metadata = {
            "facility_code": "DZ-ALG-01",
            "session_id": session_id,
            "plate_number": plate_number,
            "grace_period_minutes": self.exit_grace_period_minutes,
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        }

        checkout_url = f"https://pay.chargily.net/test/checkouts/{checkout_id}"

        return {
            "success": True,
            "checkout_id": checkout_id,
            "checkout_url": checkout_url,
            "amount_dzd": amount_dzd,
            "currency": "DZD",
            "payment_method": payment_method,
            "metadata": metadata,
            "status": "pending",
        }

    def verify_webhook_signature(self, payload_bytes: bytes, signature_header: str) -> bool:
        """
        Verifies the HMAC SHA-256 cryptographic signature sent in the 'chargily-signature' header.
        Prevents double-spend and unauthorized barrier bypass attacks.
        """
        if not signature_header:
            return False

        computed_signature = hmac.new(
            self.secret_key.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(computed_signature, signature_header)

    def process_payment_confirmation(self, checkout_id: str, plate_number: str) -> Dict[str, Any]:
        """
        Processes successful SATIM payment confirmation and computes exit window.
        """
        now = datetime.now()
        exit_deadline = now + timedelta(minutes=self.exit_grace_period_minutes)

        return {
            "success": True,
            "checkout_id": checkout_id,
            "plate_number": plate_number,
            "payment_status": "PAID",
            "confirmed_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "exit_deadline": exit_deadline.strftime("%Y-%m-%d %H:%M:%S"),
            "exit_window_minutes": self.exit_grace_period_minutes,
            "instruction": "Barrière de sortie s'ouvrira automatiquement par lecture ALPR.",
        }
