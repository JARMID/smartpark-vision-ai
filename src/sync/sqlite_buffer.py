"""
Local SQLite Offline Buffer and Write-Ahead Sync Queue.
Ensures zero data loss during network outages and provides local whitelist caching.
"""

from enum import Enum
import json
import sqlite3
import time
from typing import Dict, List, Optional, Any


class QueueEventStatus(str, Enum):
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"


class SqliteBufferQueue:
    """
    SQLite-backed local queue for storing access events and caching authorized vehicles.
    Uses Write-Ahead Logging (WAL) for high throughput.
    """

    def __init__(self, db_path: str = "edge_buffer.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("PRAGMA journal_mode=WAL;")
            self.conn.execute("PRAGMA synchronous=NORMAL;")

            # Table for event buffering
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS event_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    camera_id TEXT NOT NULL,
                    plate_number TEXT NOT NULL,
                    ocr_confidence REAL NOT NULL,
                    driver_detected INTEGER NOT NULL DEFAULT 0,
                    matched_person_id TEXT,
                    face_cosine_distance REAL,
                    action_taken TEXT NOT NULL,
                    snapshot_path TEXT,
                    created_at REAL NOT NULL,
                    sync_status TEXT NOT NULL DEFAULT 'pending',
                    synced_at REAL
                );
                """
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_event_queue_status ON event_queue(sync_status);"
            )

            # Table for cached authorized vehicles
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cached_whitelist (
                    plate_raw TEXT PRIMARY KEY,
                    plate_formatted TEXT NOT NULL,
                    person_id TEXT,
                    is_blacklisted INTEGER NOT NULL DEFAULT 0,
                    updated_at REAL NOT NULL
                );
                """
            )

    def enqueue_event(
        self,
        camera_id: str,
        plate_number: str,
        ocr_confidence: float,
        action_taken: str,
        driver_detected: bool = False,
        matched_person_id: Optional[str] = None,
        face_cosine_distance: Optional[float] = None,
        snapshot_path: Optional[str] = None,
    ) -> int:
        """Enqueue an access event into the local write-ahead log."""
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO event_queue (
                    camera_id, plate_number, ocr_confidence, driver_detected,
                    matched_person_id, face_cosine_distance, action_taken,
                    snapshot_path, created_at, sync_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    camera_id,
                    plate_number,
                    ocr_confidence,
                    1 if driver_detected else 0,
                    matched_person_id,
                    face_cosine_distance,
                    action_taken,
                    snapshot_path,
                    time.time(),
                    QueueEventStatus.PENDING.value,
                ),
            )
            return cursor.lastrowid

    def get_pending_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch un-synced events ordered chronologically."""
        cursor = self.conn.execute(
            """
            SELECT * FROM event_queue 
            WHERE sync_status = 'pending' 
            ORDER BY id ASC 
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def mark_synced(self, event_ids: List[int]):
        """Mark a batch of events as successfully transmitted to Supabase."""
        if not event_ids:
            return
        now = time.time()
        placeholders = ",".join("?" for _ in event_ids)
        with self.conn:
            self.conn.execute(
                f"""
                UPDATE event_queue 
                SET sync_status = 'synced', synced_at = ? 
                WHERE id IN ({placeholders})
                """,
                [now] + event_ids,
            )

    def update_cached_whitelist(self, items: List[Dict[str, Any]]):
        """Update or insert local whitelist plates synced from Supabase."""
        now = time.time()
        with self.conn:
            for item in items:
                self.conn.execute(
                    """
                    INSERT INTO cached_whitelist (
                        plate_raw, plate_formatted, person_id, is_blacklisted, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(plate_raw) DO UPDATE SET
                        plate_formatted=excluded.plate_formatted,
                        person_id=excluded.person_id,
                        is_blacklisted=excluded.is_blacklisted,
                        updated_at=excluded.updated_at
                    """,
                    (
                        item["plate_raw"],
                        item["plate_formatted"],
                        item.get("person_id"),
                        item.get("is_blacklisted", 0),
                        now,
                    ),
                )

    def check_plate_in_cache(self, plate_raw: str) -> Optional[Dict[str, Any]]:
        """Query local whitelist for instant offline barrier decision."""
        cursor = self.conn.execute(
            """
            SELECT * FROM cached_whitelist WHERE plate_raw = ?
            """,
            (plate_raw,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def close(self):
        """Close SQLite database connection."""
        self.conn.close()
