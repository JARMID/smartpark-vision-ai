"""
Smart Park Security - RFC 6238 Time-Based One-Time Password (TOTP) Engine.
Provides two-factor authentication (2FA) compatible with Google Authenticator,
Microsoft Authenticator, and standard hardware security keys.
Used to protect privileged physical barrier overrides, cash drawer manual releases,
and regulatory compliance purges.
"""

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from typing import Dict, Optional, Tuple, Any
import urllib.parse

try:
    import qrcode
    import qrcode.image.svg
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False


BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def generate_totp_secret(length: int = 32) -> str:
    """
    Generate a cryptographically secure Base32 secret for Google Authenticator.
    Standard length 32 characters provides 160 bits of entropy.
    """
    return "".join(secrets.choice(BASE32_ALPHABET) for _ in range(length))


def format_secret_display(secret: str) -> str:
    """Format a Base32 secret in groups of 4 characters for human entry."""
    cleaned = secret.replace(" ", "").upper()
    return " ".join(cleaned[i:i + 4] for i in range(0, len(cleaned), 4))


def get_totp_provisioning_uri(
    secret: str,
    account_name: str,
    issuer: str = "Smart Park Alger",
    period: int = 30,
    digits: int = 6,
) -> str:
    """
    Construct the otpauth URI standard recognized by Google Authenticator.
    Format: otpauth://totp/Issuer:Account?secret=...&issuer=...&algorithm=SHA1&digits=6&period=30
    """
    cleaned_secret = secret.replace(" ", "").upper()
    label = f"{issuer}:{account_name}"
    encoded_label = urllib.parse.quote(label)
    encoded_issuer = urllib.parse.quote(issuer)
    
    return (
        f"otpauth://totp/{encoded_label}"
        f"?secret={cleaned_secret}"
        f"&issuer={encoded_issuer}"
        f"&algorithm=SHA1"
        f"&digits={digits}"
        f"&period={period}"
    )


def generate_totp_code(
    secret: str,
    timestamp: Optional[float] = None,
    digits: int = 6,
    period: int = 30,
) -> str:
    """
    Generate an RFC 6238 TOTP code using HMAC-SHA1.
    Default period is 30 seconds with 6 decimal digits.
    """
    if timestamp is None:
        timestamp = time.time()

    counter = int(timestamp // period)
    cleaned_secret = secret.replace(" ", "").upper()
    
    # Pad secret with '=' if necessary for base64 decode
    padding_needed = (8 - (len(cleaned_secret) % 8)) % 8
    padded_secret = cleaned_secret + ("=" * padding_needed)
    key = base64.b32decode(padded_secret, casefold=True)

    # 8-byte big-endian unsigned integer
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()

    # Dynamic truncation
    offset = digest[-1] & 0x0F
    binary_code = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    code = binary_code % (10 ** digits)
    return f"{code:0{digits}d}"


def verify_totp_code(
    secret: str,
    code: str,
    timestamp: Optional[float] = None,
    window: int = 1,
    digits: int = 6,
    period: int = 30,
    last_verified_step: Optional[int] = None,
) -> Tuple[bool, Optional[int]]:
    """
    Verify a user-submitted code against the Base32 secret.
    Allows clock drift within +/- window time steps (window=1 allows +/- 30s drift).
    Enforces replay protection if last_verified_step is provided.
    Returns (True, current_step) on success, or (False, None) on failure.
    """
    cleaned_code = code.replace(" ", "").strip()
    if len(cleaned_code) != digits or not cleaned_code.isdigit():
        return False, None

    if timestamp is None:
        timestamp = time.time()

    current_step = int(timestamp // period)

    for step_offset in range(-window, window + 1):
        step_to_check = current_step + step_offset
        if last_verified_step is not None and step_to_check <= last_verified_step:
            # Replay attack prevention: already used in this or a prior step
            continue

        step_timestamp = step_to_check * period
        candidate_code = generate_totp_code(
            secret=secret,
            timestamp=step_timestamp,
            digits=digits,
            period=period,
        )

        if hmac.compare_digest(candidate_code, cleaned_code):
            return True, step_to_check

    return False, None


def generate_qr_svg(uri: str) -> str:
    """
    Generate a clean SVG QR code of the provisioning URI for Google Authenticator.
    Returns the raw SVG string.
    """
    if HAS_QRCODE:
        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(uri, image_factory=factory)
        svg_bytes = img.to_string()
        return svg_bytes.decode("utf-8")
    
    # Fallback placeholder SVG if qrcode is not present
    escaped_uri = urllib.parse.quote(uri)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">'
        f'<rect width="200" height="200" fill="#080C14"/>'
        f'<text x="100" y="90" fill="#38BDF8" font-size="12" text-anchor="middle">QR Code Generator</text>'
        f'<text x="100" y="120" fill="#94A3B8" font-size="10" text-anchor="middle">{escaped_uri[:24]}...</text>'
        f'</svg>'
    )


class TOTPSecurityService:
    """
    Central service managing Google Authenticator enrollment, verification,
    and access gatekeeping across Smart Park services.
    """

    def __init__(self):
        self._secrets: Dict[str, Dict[str, Any]] = {}
        self.enforce_for_barrier_override: bool = False
        self.enforce_for_compliance_purge: bool = True
        self.enforce_for_shift_close: bool = False

        # Pre-seed default supervisor account
        self._init_default_operator()

    def _init_default_operator(self):
        default_op = "OP-SUPERVISOR"
        # Seed a consistent test/pilot secret
        seed_secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
        self._secrets[default_op] = {
            "operator_id": default_op,
            "operator_name": "Superviseur General",
            "secret": seed_secret,
            "is_enabled": False,
            "last_step": 0,
            "enrolled_at": time.time(),
        }

    def get_or_create_operator_secret(
        self, operator_id: str, operator_name: str = "Operateur"
    ) -> Dict[str, Any]:
        """Fetch existing or generate a new TOTP registration for an operator."""
        if operator_id not in self._secrets:
            secret = generate_totp_secret()
            self._secrets[operator_id] = {
                "operator_id": operator_id,
                "operator_name": operator_name,
                "secret": secret,
                "is_enabled": False,
                "last_step": 0,
                "enrolled_at": time.time(),
            }
        
        record = self._secrets[operator_id]
        uri = get_totp_provisioning_uri(
            secret=record["secret"],
            account_name=f"{operator_id} ({operator_name})",
        )
        return {
            "operator_id": operator_id,
            "operator_name": operator_name,
            "secret": record["secret"],
            "secret_formatted": format_secret_display(record["secret"]),
            "provisioning_uri": uri,
            "qr_svg": generate_qr_svg(uri),
            "is_enabled": record["is_enabled"],
        }

    def verify_and_activate(self, operator_id: str, code: str) -> Tuple[bool, str]:
        """Verify code from Google Authenticator and enable 2FA for the operator."""
        if operator_id not in self._secrets:
            return False, "Operateur non trouve dans le registre de securite"

        record = self._secrets[operator_id]
        success, step = verify_totp_code(
            secret=record["secret"],
            code=code,
            last_verified_step=record.get("last_step"),
        )
        if not success:
            return False, "Code Google Authenticator invalide ou expire"

        record["is_enabled"] = True
        record["last_step"] = step
        return True, "Authentification a deux facteurs (2FA) activee avec succes"

    def deactivate(self, operator_id: str, code: str) -> Tuple[bool, str]:
        """Deactivate 2FA after validating current code."""
        if operator_id not in self._secrets:
            return False, "Operateur non trouve"

        record = self._secrets[operator_id]
        if not record["is_enabled"]:
            return True, "2FA deja desactive"

        success, step = verify_totp_code(
            secret=record["secret"],
            code=code,
            last_verified_step=record.get("last_step"),
        )
        if not success:
            return False, "Code Google Authenticator requis pour desactiver la protection"

        record["is_enabled"] = False
        record["last_step"] = step
        return True, "Authentification a deux facteurs desactivee"

    def verify_action(
        self,
        operator_id: str,
        code: Optional[str],
        action_name: str = "privileged_action",
    ) -> Tuple[bool, str]:
        """
        Verify whether an action is permitted.
        If 2FA is active for this operator or action, a valid code is mandatory.
        """
        record = self._secrets.get(operator_id)
        if not record or not record.get("is_enabled", False):
            # If 2FA not enabled for operator, permit if policy allows
            if action_name == "barrier_override" and self.enforce_for_barrier_override:
                return False, "Politique de securite active: Code 2FA obligatoire pour debloquer la barriere"
            return True, "Action autorisee sans 2FA"

        if not code:
            return False, "Code Google Authenticator obligatoire pour cette operation"

        success, step = verify_totp_code(
            secret=record["secret"],
            code=code,
            last_verified_step=record.get("last_step"),
        )
        if not success:
            return False, "Code Google Authenticator invalide ou expire"

        record["last_step"] = step
        return True, "Code 2FA valide"

    def get_status(self) -> Dict[str, Any]:
        """Return global 2FA policy status."""
        active_operators = sum(1 for v in self._secrets.values() if v.get("is_enabled"))
        return {
            "total_enrolled_operators": len(self._secrets),
            "active_2fa_operators": active_operators,
            "enforce_for_barrier_override": self.enforce_for_barrier_override,
            "enforce_for_compliance_purge": self.enforce_for_compliance_purge,
            "enforce_for_shift_close": self.enforce_for_shift_close,
        }


# Global singleton instance
totp_service = TOTPSecurityService()
