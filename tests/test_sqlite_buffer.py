"""
Unit tests for the Local SQLite Offline Buffer and Write-Ahead Sync Queue.
Verifies event queuing, offline survival, and batch synchronization state transitions.
"""

import unittest
import os
import tempfile
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.sync.sqlite_buffer import SqliteBufferQueue, QueueEventStatus


class TestSqliteBufferQueue(unittest.TestCase):
    def setUp(self):
        # Create temporary database file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_buffer.db")
        self.queue = SqliteBufferQueue(db_path=self.db_path)

    def tearDown(self):
        self.queue.close()
        self.temp_dir.cleanup()

    def test_enqueue_and_retrieve_pending(self):
        event_id = self.queue.enqueue_event(
            camera_id="cam-01",
            plate_number="104822 119 16",
            ocr_confidence=0.96,
            driver_detected=True,
            matched_person_id="p-001",
            face_cosine_distance=0.42,
            action_taken="auto_cleared",
            snapshot_path="/tmp/crops/001.jpg",
        )
        self.assertTrue(event_id > 0)

        pending = self.queue.get_pending_events(limit=10)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], event_id)
        self.assertEqual(pending[0]["plate_number"], "104822 119 16")
        self.assertEqual(pending[0]["sync_status"], QueueEventStatus.PENDING)

    def test_mark_synced(self):
        e1 = self.queue.enqueue_event(
            camera_id="cam-01", plate_number="08412 119 16", ocr_confidence=0.98, action_taken="auto_cleared"
        )
        e2 = self.queue.enqueue_event(
            camera_id="cam-02", plate_number="04112 00 16", ocr_confidence=0.91, action_taken="manual_cleared"
        )

        pending_before = self.queue.get_pending_events()
        self.assertEqual(len(pending_before), 2)

        self.queue.mark_synced([e1])

        pending_after = self.queue.get_pending_events()
        self.assertEqual(len(pending_after), 1)
        self.assertEqual(pending_after[0]["id"], e2)

    def test_whitelist_cache_sync(self):
        whitelist_items = [
            {"plate_raw": "10482211916", "plate_formatted": "104822 119 16", "person_id": "p-001", "is_blacklisted": 0},
            {"plate_raw": "0055121816", "plate_formatted": "00551 218 16", "person_id": "p-002", "is_blacklisted": 1},
        ]
        self.queue.update_cached_whitelist(whitelist_items)

        item = self.queue.check_plate_in_cache("10482211916")
        self.assertIsNotNone(item)
        self.assertEqual(item["person_id"], "p-001")
        self.assertEqual(item["is_blacklisted"], 0)

        blacklisted = self.queue.check_plate_in_cache("0055121816")
        self.assertIsNotNone(blacklisted)
        self.assertEqual(blacklisted["is_blacklisted"], 1)

        missing = self.queue.check_plate_in_cache("9999999999")
        self.assertIsNone(missing)


if __name__ == "__main__":
    unittest.main()
