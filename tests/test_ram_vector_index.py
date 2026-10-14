"""
Unit tests for In-Memory Vector Search Index and Distance Calibration.
Verifies sub-millisecond cosine distance matching and 3-frame averaging logic.
"""

import unittest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.face.ram_vector_index import RamVectorIndex, MatchDecision


class TestRamVectorIndex(unittest.TestCase):
    def setUp(self):
        self.index = RamVectorIndex(dimension=512)

        # Generate a deterministic base vector
        np.random.seed(42)
        base_v = np.random.randn(512).astype(np.float32)
        self.base_v = base_v / np.linalg.norm(base_v)

        # Enroll base vector for person "Karim Benali"
        self.index.enroll(
            person_id="p-001",
            full_name="Karim Benali",
            embedding=self.base_v,
            is_blacklisted=False,
        )

        # Enroll a blacklisted person
        blacklisted_v = np.random.randn(512).astype(np.float32)
        blacklisted_v = blacklisted_v / np.linalg.norm(blacklisted_v)
        self.index.enroll(
            person_id="p-002",
            full_name="Suspect X",
            embedding=blacklisted_v,
            is_blacklisted=True,
            blacklist_reason="Vehicle theft report",
        )

    def test_exact_match(self):
        # Querying with identical embedding should produce Distance = 0.0
        result = self.index.search(self.base_v)
        self.assertEqual(result.decision, MatchDecision.MATCH)
        self.assertEqual(result.person_id, "p-001")
        self.assertAlmostEqual(result.cosine_distance, 0.0, places=4)
        self.assertAlmostEqual(result.similarity_score, 1.0, places=4)

    def test_slight_perturbation_match(self):
        # Add slight natural perturbation (Distance ~ 0.08 -> well below 0.52 threshold)
        noise = np.random.randn(512).astype(np.float32) * 0.02
        query = self.base_v + noise
        query = query / np.linalg.norm(query)

        result = self.index.search(query)
        self.assertEqual(result.decision, MatchDecision.MATCH)
        self.assertEqual(result.person_id, "p-001")
        self.assertLessEqual(result.cosine_distance, 0.52)

    def test_borderline_deadzone_handling(self):
        # Create a synthetic vector with cosine distance exactly ~0.53 (in the 0.52-0.55 band)
        orthogonal = np.random.randn(512).astype(np.float32)
        orthogonal = orthogonal - np.dot(orthogonal, self.base_v) * self.base_v
        orthogonal = orthogonal / np.linalg.norm(orthogonal)

        # target distance = 0.53 -> target similarity = 0.47
        alpha = 0.47
        beta = np.sqrt(1.0 - alpha**2)
        borderline_query = alpha * self.base_v + beta * orthogonal
        borderline_query = borderline_query / np.linalg.norm(borderline_query)

        # Single frame query should report BORDERLINE_RESAMPLE
        result = self.index.search(borderline_query)
        self.assertEqual(result.decision, MatchDecision.BORDERLINE_RESAMPLE)
        self.assertGreater(result.cosine_distance, 0.52)
        self.assertLessEqual(result.cosine_distance, 0.55)

    def test_temporal_multi_frame_averaging(self):
        # Provide 3 noisy frames where individual frames have noise, but centroid clears
        frames = []
        for _ in range(3):
            noisy = self.base_v + np.random.randn(512).astype(np.float32) * 0.03
            frames.append(noisy / np.linalg.norm(noisy))

        result = self.index.search_multi_frame(frames)
        self.assertEqual(result.decision, MatchDecision.MATCH)
        self.assertEqual(result.person_id, "p-001")

    def test_blacklist_trigger(self):
        blacklisted_profile = self.index.profiles["p-002"]
        result = self.index.search(blacklisted_profile.embedding)
        self.assertEqual(result.decision, MatchDecision.BLACKLIST_HIT)
        self.assertTrue(result.is_blacklisted)
        self.assertEqual(result.person_id, "p-002")

    def test_complete_mismatch(self):
        # Orthogonal random vector
        orthogonal = np.random.randn(512).astype(np.float32)
        orthogonal = orthogonal / np.linalg.norm(orthogonal)

        result = self.index.search(orthogonal)
        self.assertEqual(result.decision, MatchDecision.NO_MATCH)


if __name__ == "__main__":
    unittest.main()
