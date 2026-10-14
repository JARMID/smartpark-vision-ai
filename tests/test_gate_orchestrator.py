"""
Integration tests for the Gate Orchestrator.
Verifies end-to-end pipeline: plate parsing -> anti-spoofing check -> RAM vector search -> barrier actuation -> local event queuing.
"""

import unittest
import numpy as np
import tempfile
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.main import GateOrchestrator, GateDecisionResult


class TestGateOrchestrator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_orchestrator.db")

        self.orchestrator = GateOrchestrator(
            db_path=self.db_path,
            simulation_mode=True,
        )

        # Enroll a registered VIP user with a known 512-D embedding and plate
        np.random.seed(100)
        base_v = np.random.randn(512).astype(np.float32)
        self.driver_embedding = base_v / np.linalg.norm(base_v)

        self.orchestrator.enroll_subscriber(
            person_id="p-vip-001",
            full_name="Amine Hadj",
            plate_raw="10482211916",
            plate_formatted="104822 119 16",
            face_embedding=self.driver_embedding,
        )

    def tearDown(self):
        self.orchestrator.close()
        self.temp_dir.cleanup()

    def test_vip_entry_clearance(self):
        # Whitelisted vehicle + matching driver face + live human -> instant clearance
        decision = self.orchestrator.process_arrival(
            camera_id="cam-01",
            raw_plate_text="104822 119 16",
            plate_confidence=0.97,
            face_embedding=self.driver_embedding,
            liveness_score=0.98,
        )

        self.assertEqual(decision["result"], GateDecisionResult.CLEARED_VIP)
        self.assertTrue(decision["barrier_opened"])
        self.assertEqual(decision["person_id"], "p-vip-001")
        self.assertLessEqual(decision["face_distance"], 0.52)

    def test_spoofed_face_blocked(self):
        # Liveness score low (<0.50) indicates printed photo or phone screen attack
        decision = self.orchestrator.process_arrival(
            camera_id="cam-01",
            raw_plate_text="104822 119 16",
            plate_confidence=0.97,
            face_embedding=self.driver_embedding,
            liveness_score=0.20,  # Spoof detected
        )

        self.assertEqual(decision["result"], GateDecisionResult.DENIED_SPOOF)
        self.assertFalse(decision["barrier_opened"])

    def test_unregistered_visitor_entry(self):
        # Valid Algerian plate but unregistered driver -> generates visitor ticket
        visitor_embedding = np.random.randn(512).astype(np.float32)
        visitor_embedding = visitor_embedding / np.linalg.norm(visitor_embedding)

        decision = self.orchestrator.process_arrival(
            camera_id="cam-01",
            raw_plate_text="08412 122 31",  # Oran plate
            plate_confidence=0.94,
            face_embedding=visitor_embedding,
            liveness_score=0.95,
        )

        self.assertEqual(decision["result"], GateDecisionResult.CLEARED_VISITOR)
        self.assertTrue(decision["barrier_opened"])
        self.assertTrue("ticket_qr" in decision)


if __name__ == "__main__":
    unittest.main()
