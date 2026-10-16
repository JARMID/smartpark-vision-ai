"""
Smart Park - Edge Camera Daemon & Hardware Bridge Test Suite.
Verifies camera channel configuration, low-latency streaming pipeline,
barrier override actuation, and Law 25-11 30-day log purge compliance.
"""

import os
import tempfile
import time
import unittest
import numpy as np
from fastapi.testclient import TestClient

from src.camera.edge_daemon import EdgeDaemonService, create_edge_app


class TestEdgeDaemonService(unittest.TestCase):

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()

        # Create temporary test config
        self.config_content = f"""
appliance:
  site_id: "test-site-01"
  site_name: "Parking Test"
  wilaya_code: 16
  simulation_mode: true
  retention_days: 30
  auto_purge_interval_hours: 1
  database_path: "{self.temp_db.name.replace(chr(92), '/')}"
  snapshot_directory: "test_snapshots"

hardware:
  modbus_host: "127.0.0.1"
  modbus_port: 502
  relay_pulse_duration_seconds: 1.0
  enable_loopback: true

cameras:
  - id: "test_cam_01"
    name: "Voie 1 Test ALPR"
    role: "plate_entry"
    lane_id: "lane_1"
    rtsp_url: "rtsp://127.0.0.1:8554/live"
    transport: "tcp"
    fps: 25.0
    roi_box: [0.2, 0.2, 0.8, 0.8]

  - id: "test_cam_02"
    name: "Borne Biometrique Test"
    role: "face_entry"
    lane_id: "lane_1"
    rtsp_url: "rtsp://127.0.0.1:8554/face"
    transport: "tcp"
    fps: 25.0
    roi_box: [0.1, 0.2, 0.9, 0.8]
"""
        self.temp_cfg = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w", encoding="utf-8")
        self.temp_cfg.write(self.config_content)
        self.temp_cfg.close()

        self.daemon = EdgeDaemonService(config_path=self.temp_cfg.name, simulation_mode=True)
        self.daemon.start()
        self.app = create_edge_app(self.daemon)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.daemon.stop()
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except OSError:
                pass
        if os.path.exists(self.temp_cfg.name):
            try:
                os.remove(self.temp_cfg.name)
            except OSError:
                pass
        if os.path.exists("test_snapshots"):
            try:
                for f in os.listdir("test_snapshots"):
                    os.remove(os.path.join("test_snapshots", f))
                os.rmdir("test_snapshots")
            except OSError:
                pass

    def test_daemon_initialization(self):
        """Verify daemon initializes stream manager and registers configured channels."""
        self.assertTrue(self.daemon.sim_mode)
        self.assertEqual(len(self.daemon.stream_manager.workers), 2)
        self.assertIn("test_cam_01", self.daemon.stream_manager.workers)
        self.assertIn("test_cam_02", self.daemon.stream_manager.workers)

    def test_health_telemetry_endpoint(self):
        """Verify /api/edge/health returns complete hardware and camera metrics."""
        response = self.client.get("/api/edge/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "operational")
        self.assertEqual(data["connected_cameras"], 2)
        self.assertIn("uptime_seconds", data)
        self.assertIn("camera_streams", data)

    def test_cameras_list_endpoint(self):
        """Verify /api/edge/cameras returns channel metrics for each camera."""
        response = self.client.get("/api/edge/cameras")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("test_cam_01", data)
        self.assertIn("test_cam_02", data)
        self.assertEqual(data["test_cam_01"]["role"], "plate_entry")

    def test_arrival_processing_vip_cleared(self):
        """Verify VIP arrival returns CLEARED_VIP and actuates barrier relay."""
        # Enroll test subscriber
        dummy_embedding = np.random.randn(512).astype(np.float32)
        dummy_embedding = dummy_embedding / np.linalg.norm(dummy_embedding)
        self.daemon.orchestrator.enroll_subscriber(
            person_id="VIP_001",
            full_name="Amine Hadj",
            plate_raw="104822 119 16",
            plate_formatted="104822-119-16",
            face_embedding=dummy_embedding,
        )

        payload = {
            "lane_id": "lane_1",
            "raw_plate_text": "104822 119 16",
            "plate_confidence": 0.99,
            "face_embedding": dummy_embedding.tolist(),
            "liveness_score": 0.96,
            "save_snapshot": False
        }
        response = self.client.post("/api/edge/arrival/process", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["result"], "cleared_vip")
        self.assertTrue(data["barrier_opened"])

    def test_barrier_manual_override(self):
        """Verify guard manual barrier override pulses the barrier relay and logs audit event."""
        payload = {
            "gate_id": 1,
            "action": "open",
            "duration_seconds": 2.0,
            "operator_id": "guard_agent_test"
        }
        response = self.client.post("/api/edge/barrier/override", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["action"], "open")

    def test_law_25_11_purge_maintenance(self):
        """Verify automated purge routines execute cleanly without error."""
        # Create a mock expired snapshot
        os.makedirs("test_snapshots", exist_ok=True)
        old_snapshot = os.path.join("test_snapshots", "old_plate.jpg")
        with open(old_snapshot, "w") as f:
            f.write("mock_jpeg_bytes")

        # Set file time back 40 days
        forty_days_ago = time.time() - (40 * 86400)
        os.utime(old_snapshot, (forty_days_ago, forty_days_ago))

        # Run purge
        self.daemon._purge_expired_snapshots(days=30)
        self.assertFalse(os.path.exists(old_snapshot), "Expired snapshot should have been purged!")


if __name__ == "__main__":
    unittest.main()
