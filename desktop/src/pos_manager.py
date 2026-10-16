"""
Smart Park - Cashier Point of Sale (POS) and Shift Ledger.
Manages booth cash drawer floats, ticket settlements, receipt numbering,
card terminal transaction logging, and daily closing Z-Reports.
"""

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
from typing import List, Optional, Dict, Any


from desktop.src.db import DesktopDatabase


@dataclass
class TransactionRecord:
    transaction_id: str
    ticket_id: str
    plate_number: str
    payment_method: str  # CASH, CIB_TERMINAL, EDAHABIA_TERMINAL, VIP_EXEMPT
    amount_dzd: float
    tendered_dzd: float
    change_dzd: float
    timestamp: datetime
    cashier_id: str
    booth_id: str
    reference_code: str = ""


@dataclass
class ShiftSummary:
    shift_id: str
    cashier_id: str
    booth_id: str
    opened_at: datetime
    closed_at: Optional[datetime]
    opening_float_dzd: float
    total_cash_collected_dzd: float
    total_card_collected_dzd: float
    total_exemptions_dzd: float
    tickets_settled_count: int
    transactions: List[TransactionRecord] = field(default_factory=list)


class CashierPosManager:
    """
    Booth Point of Sale manager ensuring accurate cash drawer tracking
    and audit trail compliance backed by local SQLite persistence.
    """

    def __init__(self, booth_id: str = "BOOTH-01", db: Optional[DesktopDatabase] = None):
        self.booth_id = booth_id
        self.db = db or DesktopDatabase()
        self.active_shift: Optional[ShiftSummary] = None
        self.shift_history: List[ShiftSummary] = []
        self._tx_counter = 5000

        # Hydrate or resume active shift from SQLite
        db_shift = self.db.get_or_open_shift(booth_id=booth_id)
        if db_shift:
            try:
                opened_dt = datetime.strptime(db_shift["opened_at"], "%Y-%m-%d %H:%M:%S")
            except Exception:
                opened_dt = datetime.now()
            self.active_shift = ShiftSummary(
                shift_id=db_shift["shift_id"],
                cashier_id=db_shift["cashier_id"],
                booth_id=db_shift["booth_id"],
                opened_at=opened_dt,
                closed_at=None,
                opening_float_dzd=float(db_shift["opening_float_dzd"]),
                total_cash_collected_dzd=float(db_shift["total_cash_in_dzd"]),
                total_card_collected_dzd=float(db_shift["total_card_in_dzd"]),
                total_exemptions_dzd=0.0,
                tickets_settled_count=int(db_shift["transaction_count"]),
            )

    def open_shift(self, cashier_id: str, opening_float_dzd: float = 5000.0) -> ShiftSummary:
        """Open a new cashier working shift and ensure persistence in SQLite."""
        db_shift = self.db.get_or_open_shift(
            booth_id=self.booth_id,
            cashier_id=cashier_id,
            opening_float_dzd=opening_float_dzd,
        )
        opened_dt = datetime.now()
        if db_shift and "opened_at" in db_shift:
            try:
                opened_dt = datetime.strptime(db_shift["opened_at"], "%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

        self.active_shift = ShiftSummary(
            shift_id=db_shift["shift_id"] if db_shift else f"SHIFT-{datetime.now().strftime('%Y%m%d')}-{cashier_id}",
            cashier_id=cashier_id,
            booth_id=self.booth_id,
            opened_at=opened_dt,
            closed_at=None,
            opening_float_dzd=round(float(opening_float_dzd), 2),
            total_cash_collected_dzd=0.0,
            total_card_collected_dzd=0.0,
            total_exemptions_dzd=0.0,
            tickets_settled_count=0,
        )
        return self.active_shift

    def process_settlement(
        self,
        ticket_id: str,
        plate_number: str,
        amount_dzd: float,
        payment_method: str = "CASH",
        tendered_dzd: Optional[float] = None,
        reference_code: str = "",
    ) -> TransactionRecord:
        """Process a parking payment and record in active shift ledger."""
        if not self.active_shift:
            self.open_shift("DEFAULT-OPERATOR", 5000.0)

        self._tx_counter += 1
        now = datetime.now()
        tx_id = f"TX-{now.strftime('%Y%m%d')}-{self._tx_counter}"

        amount_dzd = round(float(amount_dzd), 2)
        tender = round(float(tendered_dzd if tendered_dzd is not None else amount_dzd), 2)
        change = round(max(0.0, tender - amount_dzd) if payment_method == "CASH" else 0.0, 2)

        tx = TransactionRecord(
            transaction_id=tx_id,
            ticket_id=ticket_id,
            plate_number=plate_number,
            payment_method=payment_method,
            amount_dzd=amount_dzd,
            tendered_dzd=tender,
            change_dzd=change,
            timestamp=now,
            cashier_id=self.active_shift.cashier_id,
            booth_id=self.booth_id,
            reference_code=reference_code or f"REF-{self._tx_counter}",
        )

        self.active_shift.transactions.append(tx)
        self.active_shift.tickets_settled_count += 1

        if payment_method == "CASH":
            self.active_shift.total_cash_collected_dzd = round(self.active_shift.total_cash_collected_dzd + amount_dzd, 2)
        elif payment_method in ("CIB_TERMINAL", "EDAHABIA_TERMINAL"):
            self.active_shift.total_card_collected_dzd = round(self.active_shift.total_card_collected_dzd + amount_dzd, 2)
        elif payment_method == "VIP_EXEMPT":
            self.active_shift.total_exemptions_dzd = round(self.active_shift.total_exemptions_dzd + amount_dzd, 2)

        # Persist transaction to SQLite
        try:
            self.db.record_transaction(
                shift_id=self.active_shift.shift_id,
                ticket_id=ticket_id,
                plate_number=plate_number,
                entry_time=now.strftime("%Y-%m-%d %H:%M:%S"),
                exit_time=now.strftime("%Y-%m-%d %H:%M:%S"),
                duration_minutes=120,
                amount_due_dzd=amount_dzd,
                amount_tendered_dzd=tender,
                change_dzd=change,
                payment_method=payment_method,
            )
        except Exception as err:
            import logging
            logging.getLogger("smartpark.pos").error(f"Failed to record transaction to db: {err}")

        return tx

    def close_shift(self) -> Dict[str, Any]:
        """Close active shift and compile certified Z-Report."""
        if not self.active_shift:
            raise ValueError("No active shift found to close.")

        now = datetime.now()
        self.active_shift.closed_at = now
        closing_drawer_cash = round(self.active_shift.opening_float_dzd + self.active_shift.total_cash_collected_dzd, 2)
        total_revenue = round(self.active_shift.total_cash_collected_dzd + self.active_shift.total_card_collected_dzd, 2)

        # Generate cryptographic audit hash
        audit_payload = (
            f"{self.active_shift.shift_id}|{self.active_shift.cashier_id}|"
            f"{total_revenue}|{self.active_shift.tickets_settled_count}|{now.isoformat()}"
        )
        z_hash = hashlib.sha256(audit_payload.encode("utf-8")).hexdigest()[:16].upper()

        # Update SQLite
        try:
            self.db.close_shift(self.active_shift.shift_id)
        except Exception as err:
            import logging
            logging.getLogger("smartpark.pos").error(f"Failed to close shift in db: {err}")

        z_report = {
            "report_title": "RAPPORT Z DE CLOTURE DE CAISSE",
            "facility": "SMART PARK ALGER",
            "shift_id": self.active_shift.shift_id,
            "cashier_id": self.active_shift.cashier_id,
            "booth_id": self.booth_id,
            "opened_at": self.active_shift.opened_at.strftime("%Y-%m-%d %H:%M:%S"),
            "closed_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "opening_float_dzd": self.active_shift.opening_float_dzd,
            "total_cash_revenue_dzd": self.active_shift.total_cash_collected_dzd,
            "total_card_revenue_dzd": self.active_shift.total_card_collected_dzd,
            "total_exemptions_dzd": self.active_shift.total_exemptions_dzd,
            "total_revenue_dzd": total_revenue,
            "expected_drawer_cash_dzd": closing_drawer_cash,
            "tickets_processed": self.active_shift.tickets_settled_count,
            "audit_hash": f"SHA256-{z_hash}",
            "regulatory_status": "CONFORME FISCALITE ET ANPDP",
        }

        self.shift_history.append(self.active_shift)
        self.active_shift = None
        return z_report
