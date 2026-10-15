"""
Smart Park Desktop Station - Local SQLite Ledger and Hardware Audit Database.
Provides 100% autonomous offline persistence for cashier shifts, cash drawer accounting,
local parking tickets, and barrier override audit trails.
"""

from datetime import datetime
import hashlib
import json
import os
import sqlite3
import time
from typing import Dict, List, Optional, Any, Tuple


class DesktopDatabase:
    """
    SQLite-backed local persistence engine for the desktop operator booth.
    Operates independently of cloud or backend network status.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "desktop_station.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        with self.conn:
            self.conn.execute("PRAGMA journal_mode=WAL;")
            self.conn.execute("PRAGMA synchronous=NORMAL;")

            # 1. Cashier Shift Ledger
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cashier_shifts (
                    shift_id TEXT PRIMARY KEY,
                    booth_id TEXT NOT NULL,
                    cashier_id TEXT NOT NULL,
                    cashier_name TEXT NOT NULL,
                    opened_at TEXT NOT NULL,
                    closed_at TEXT,
                    opening_float_dzd REAL NOT NULL DEFAULT 5000.0,
                    total_cash_in_dzd REAL NOT NULL DEFAULT 0.0,
                    total_card_in_dzd REAL NOT NULL DEFAULT 0.0,
                    total_change_dzd REAL NOT NULL DEFAULT 0.0,
                    transaction_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    z_report_hash TEXT,
                    created_at REAL NOT NULL
                );
                """
            )

            # 2. POS Financial Transactions
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pos_transactions (
                    id TEXT PRIMARY KEY,
                    shift_id TEXT NOT NULL,
                    ticket_id TEXT NOT NULL,
                    plate_number TEXT NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    amount_due_dzd REAL NOT NULL,
                    amount_tendered_dzd REAL NOT NULL,
                    change_dzd REAL NOT NULL,
                    payment_method TEXT NOT NULL,
                    receipt_number TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (shift_id) REFERENCES cashier_shifts(shift_id)
                );
                """
            )

            # 3. Local Offline Parking Tickets
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS local_tickets (
                    ticket_id TEXT PRIMARY KEY,
                    plate_number TEXT NOT NULL,
                    entry_time TEXT NOT NULL,
                    lane_id TEXT NOT NULL,
                    zone_name TEXT NOT NULL,
                    barcode_value TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    tariff_due_dzd REAL NOT NULL DEFAULT 100.0,
                    paid_at TEXT,
                    exit_at TEXT,
                    created_at REAL NOT NULL
                );
                """
            )

            # 4. Physical Barrier Override Audit Log
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS barrier_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    channel INTEGER NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    operator_name TEXT NOT NULL,
                    hardware_success INTEGER NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )

    # --- Cashier Shift Engine ---

    def get_or_open_shift(
        self,
        booth_id: str = "BOOTH-01",
        cashier_id: str = "AGENT-MEZIANE",
        cashier_name: str = "Amine Meziane",
        opening_float_dzd: float = 5000.0,
    ) -> Dict[str, Any]:
        """Fetch currently open shift for booth or initialize a new one."""
        cursor = self.conn.execute(
            """
            SELECT * FROM cashier_shifts
            WHERE booth_id = ? AND status = 'OPEN'
            ORDER BY created_at DESC LIMIT 1
            """,
            (booth_id,),
        )
        row = cursor.fetchone()
        if row:
            return dict(row)

        now = datetime.now()
        shift_id = f"SHIFT-{now.strftime('%Y%m%d')}-{int(now.timestamp()) % 10000:04d}"
        now_iso = now.strftime("%Y-%m-%d %H:%M:%S")

        with self.conn:
            self.conn.execute(
                """
                INSERT INTO cashier_shifts (
                    shift_id, booth_id, cashier_id, cashier_name,
                    opened_at, opening_float_dzd, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?)
                """,
                (shift_id, booth_id, cashier_id, cashier_name, now_iso, opening_float_dzd, time.time()),
            )

        return {
            "shift_id": shift_id,
            "booth_id": booth_id,
            "cashier_id": cashier_id,
            "cashier_name": cashier_name,
            "opened_at": now_iso,
            "opening_float_dzd": opening_float_dzd,
            "total_cash_in_dzd": 0.0,
            "total_card_in_dzd": 0.0,
            "total_change_dzd": 0.0,
            "transaction_count": 0,
            "status": "OPEN",
        }

    def record_transaction(
        self,
        shift_id: str,
        ticket_id: str,
        plate_number: str,
        entry_time: str,
        exit_time: str,
        duration_minutes: int,
        amount_due_dzd: float,
        amount_tendered_dzd: float,
        change_dzd: float,
        payment_method: str = "CASH",
    ) -> Dict[str, Any]:
        """Record financial settlement and update active shift running balances."""
        now = datetime.now()
        tx_id = f"TX-{now.strftime('%Y%m%d%H%M%S')}-{int(now.timestamp() * 1000) % 1000:03d}"
        receipt_num = f"REC-{now.strftime('%Y%m%d')}-{int(now.timestamp()) % 10000:04d}"
        now_iso = now.strftime("%Y-%m-%d %H:%M:%S")

        with self.conn:
            # 1. Insert transaction row
            self.conn.execute(
                """
                INSERT INTO pos_transactions (
                    id, shift_id, ticket_id, plate_number, entry_time, exit_time,
                    duration_minutes, amount_due_dzd, amount_tendered_dzd, change_dzd,
                    payment_method, receipt_number, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tx_id, shift_id, ticket_id, plate_number, entry_time, exit_time,
                    duration_minutes, amount_due_dzd, amount_tendered_dzd, change_dzd,
                    payment_method, receipt_num, time.time()
                ),
            )

            # 2. Update shift aggregates
            is_cash = payment_method.upper() == "CASH"
            cash_inc = amount_due_dzd if is_cash else 0.0
            card_inc = amount_due_dzd if not is_cash else 0.0

            self.conn.execute(
                """
                UPDATE cashier_shifts
                SET total_cash_in_dzd = total_cash_in_dzd + ?,
                    total_card_in_dzd = total_card_in_dzd + ?,
                    total_change_dzd = total_change_dzd + ?,
                    transaction_count = transaction_count + 1
                WHERE shift_id = ?
                """,
                (cash_inc, card_inc, change_dzd if is_cash else 0.0, shift_id),
            )

            # 3. Mark ticket paid if present locally
            self.conn.execute(
                """
                UPDATE local_tickets
                SET status = 'PAID', paid_at = ?
                WHERE ticket_id = ?
                """,
                (now_iso, ticket_id),
            )

        return {
            "transaction_id": tx_id,
            "receipt_number": receipt_num,
            "shift_id": shift_id,
            "ticket_id": ticket_id,
            "plate_number": plate_number,
            "amount_due_dzd": amount_due_dzd,
            "amount_tendered_dzd": amount_tendered_dzd,
            "change_dzd": change_dzd,
            "payment_method": payment_method,
            "timestamp": now_iso,
        }

    def close_shift(self, shift_id: str) -> Dict[str, Any]:
        """Close cashier shift, calculate drawer balance, and compute cryptographic Z-Report hash."""
        now = datetime.now()
        now_iso = now.strftime("%Y-%m-%d %H:%M:%S")

        cursor = self.conn.execute("SELECT * FROM cashier_shifts WHERE shift_id = ?", (shift_id,))
        shift = cursor.fetchone()
        if not shift:
            raise ValueError(f"Shift {shift_id} not found.")

        shift_dict = dict(shift)
        expected_cash_drawer = (
            shift_dict["opening_float_dzd"]
            + shift_dict["total_cash_in_dzd"]
        )

        # Audit hash across shift financial fields
        audit_raw = (
            f"{shift_id}|{shift_dict['booth_id']}|{shift_dict['cashier_id']}|"
            f"{shift_dict['opened_at']}|{now_iso}|{shift_dict['total_cash_in_dzd']}|"
            f"{shift_dict['total_card_in_dzd']}|{shift_dict['transaction_count']}"
        )
        z_hash = f"SHA256-{hashlib.sha256(audit_raw.encode('utf-8')).hexdigest().upper()}"

        with self.conn:
            self.conn.execute(
                """
                UPDATE cashier_shifts
                SET status = 'CLOSED',
                    closed_at = ?,
                    z_report_hash = ?
                WHERE shift_id = ?
                """,
                (now_iso, z_hash, shift_id),
            )

        return {
            "shift_id": shift_id,
            "booth_id": shift_dict["booth_id"],
            "cashier_id": shift_dict["cashier_id"],
            "cashier_name": shift_dict["cashier_name"],
            "opened_at": shift_dict["opened_at"],
            "closed_at": now_iso,
            "opening_float_dzd": shift_dict["opening_float_dzd"],
            "total_cash_in_dzd": shift_dict["total_cash_in_dzd"],
            "total_card_in_dzd": shift_dict["total_card_in_dzd"],
            "total_collected_dzd": shift_dict["total_cash_in_dzd"] + shift_dict["total_card_in_dzd"],
            "expected_drawer_cash_dzd": expected_cash_drawer,
            "transaction_count": shift_dict["transaction_count"],
            "audit_hash": z_hash,
            "status": "CLOSED",
        }

    # --- Local Offline Ticket Operations ---

    def create_local_ticket(
        self,
        plate_number: str,
        lane_id: str = "LANE-01",
        zone_name: str = "Zone B (Visiteur)",
        tariff_due_dzd: float = 100.0,
    ) -> Dict[str, Any]:
        """Issue an active parking ticket and persist to local SQLite store."""
        now = datetime.now()
        ticket_id = f"TKT-{now.strftime('%Y%m%d')}-{int(now.timestamp()) % 100000:05d}"
        now_iso = now.strftime("%Y-%m-%d %H:%M:%S")

        # Generate GS1 13-digit barcode with check digit
        clean_digits = "".join(filter(str.isdigit, plate_number)) or "16"
        padded_seq = f"{int(now.timestamp()) % 100000000:08d}"
        raw12 = f"99{padded_seq[:8]}{clean_digits[:2]:02s}"[:12]
        checksum = self._calculate_ean13_checksum(raw12)
        barcode_value = f"{raw12}{checksum}"

        with self.conn:
            self.conn.execute(
                """
                INSERT INTO local_tickets (
                    ticket_id, plate_number, entry_time, lane_id,
                    zone_name, barcode_value, status, tariff_due_dzd, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                """,
                (ticket_id, plate_number, now_iso, lane_id, zone_name, barcode_value, tariff_due_dzd, time.time()),
            )

        return {
            "ticket_id": ticket_id,
            "plate_number": plate_number,
            "entry_time": now_iso,
            "lane_id": lane_id,
            "zone_name": zone_name,
            "barcode_value": barcode_value,
            "status": "ACTIVE",
            "tariff_due_dzd": tariff_due_dzd,
        }

    def find_ticket_by_barcode(self, barcode_str: str) -> Optional[Dict[str, Any]]:
        """Look up ticket by 13-digit EAN barcode or ticket ID."""
        cursor = self.conn.execute(
            """
            SELECT * FROM local_tickets
            WHERE barcode_value = ? OR ticket_id = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (barcode_str.strip(), barcode_str.strip()),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    # --- Barrier Audit Logging ---

    def log_barrier_action(
        self,
        channel: int,
        duration_ms: int,
        reason: str,
        operator_name: str,
        success: bool = True,
    ):
        """Record barrier relay actuation into immutable local audit trail."""
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO barrier_audit_log (
                    timestamp, channel, duration_ms, reason,
                    operator_name, hardware_success, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (now_iso, channel, duration_ms, reason, operator_name, 1 if success else 0, time.time()),
            )

    def get_recent_transactions(self, limit: int = 15) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            """
            SELECT * FROM pos_transactions
            ORDER BY created_at DESC LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def _calculate_ean13_checksum(raw12: str) -> int:
        if len(raw12) != 12 or not raw12.isdigit():
            raw12 = (raw12 + "0" * 12)[:12]
        odds = sum(int(raw12[i]) for i in range(0, 12, 2))
        evens = sum(int(raw12[i]) * 3 for i in range(1, 12, 2))
        total = odds + evens
        remainder = total % 10
        return 0 if remainder == 0 else 10 - remainder

    def close(self):
        self.conn.close()
