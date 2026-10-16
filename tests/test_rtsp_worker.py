"""
Unit Tests for Smart Park - Camera RTSP Worker & Stream Manager.
Verifies thread safety, buffer flushing, ROI cropping, motion detection, and gate integration.
"""

import os
import time
import unittest
import numpy as np

from src.camera.rtsp_worker import RtspStreamWorker, CameraStreamStatus
from src.camera.edge_stream_manager import EdgeStreamManager
from src.camera.onvif_client import OnvifCameraClient
from src.main import GateOrchestrator, GateDecisionResult


class TestRtspStreamWorker(unittest.TestCase):
    """Test suite for RTSP worker ingestion and circular buffer mechanics."""

    def setUp(self):
        self.test_frame = np.ones((720, 1280, 3), dtype=np.uint8) * 128
        self.frame_counter = 0

    def synthetic_generator(self):
        """Simulate high-speed camera frame generation."""
        self.frame_counter += 1
        frame = self.test_frame.copy()
        # Watermark frame with counter
        frame[10:50, 10:50] = self.frame_counter % 255
        return frame

    def test_worker_lifecycle(self):
        worker = RtspStreamWorker(
            camera_id="test_cam_01",
            rtsp_url="synthetic://feed",
            synthetic_frame_generator=self.synthetic_generator,
        )
        self.assertEqual(worker.status, CameraStreamStatus.STOPPED)

        worker.start()
        time.sleep(0.1)
        self.assertEqual(worker.status, CameraStreamStatus.STREAMING)

        frame, ts, status = worker.get_latest_frame()
        self.assertIsNotNone(frame)
        self.assertEqual(frame.shape, (720, 1280, 3))
        self.assertEqual(status, CameraStreamStatus.STREAMING)
        self.assertGreater(ts, 0.0)

        worker.stop()
        self.assertEqual(worker.status, CameraStreamStatus.STOPPED)

    def test_buffer_zero_lag_drop(self):
        """Verify that older frames are dropped so inference never lags behind reality."""
        worker = RtspStreamWorker(
            camera_id="test_cam_drop",
            rtsp_url="synthetic://feed",
            synthetic_frame_generator=self.synthetic_generator,
        )
        worker.start()
        # Wait long enough for multiple frames to generate
        time.sleep(0.2)
        metrics = worker.metrics
        self.assertGreater(metrics["frames_ingested"], 2)
        self.assertGreaterEqual(metrics["frames_dropped"], 1)
        worker.stop()

    def test_roi_cropping(self):
        roi = (0.2, 0.3, 0.8, 0.7)  # ymin, xmin, ymax, xmax
        worker = RtspStreamWorker(
            camera_id="test_cam_roi",
            rtsp_url="synthetic://feed",
            roi_box=roi,
        )
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        cropped = worker.get_roi_crop(frame)
        # Expected height: (0.8 - 0.2) * 100 = 60
        # Expected width: (0.7 - 0.3) * 200 = 80
        self.assertEqual(cropped.shape, (60, 80, 3))

    def test_virtual_loop_motion(self):
        worker = RtspStreamWorker(
            camera_id="test_cam_motion",
            rtsp_url="synthetic://feed",
            roi_box=(0.1, 0.1, 0.9, 0.9),
        )
        frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
        # First call establishes background
        has_motion1 = worker.check_virtual_loop_motion(frame1)
        self.assertFalse(has_motion1)

        # Identical frame: no motion
        has_motion2 = worker.check_virtual_loop_motion(frame1)
        self.assertFalse(has_motion2)

        # Drastic vehicle arrival in ROI
        frame2 = frame1.copy()
        frame2[100:300, 100:300] = 255
        has_motion3 = worker.check_virtual_loop_motion(frame2)
        self.assertTrue(has_motion3)

    def test_snapshot_capture(self):
        test_snapshot_path = "test_snapshot_output.jpg"
        if os.path.exists(test_snapshot_path):
            os.remove(test_snapshot_path)

        worker = RtspStreamWorker(
            camera_id="test_cam_snap",
            rtsp_url="synthetic://feed",
            synthetic_frame_generator=self.synthetic_generator,
        )
        worker.start()
        time.sleep(0.08)

        success = worker.capture_snapshot(test_snapshot_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(test_snapshot_path))

        worker.stop()
        if os.path.exists(test_snapshot_path):
            os.remove(test_snapshot_path)


class TestEdgeStreamManager(unittest.TestCase):
    """Test multi-camera orchestration and integration with GateOrchestrator."""

    def setUp(self):
        self.orchestrator = GateOrchestrator(
            db_path="test_edge_stream_manager.db",
            simulation_mode=True,
        )
        self.manager = EdgeStreamManager(
            orchestrator=self.orchestrator,
            auto_start=False,
        )

    def tearDown(self):
        self.manager.close()
        for f in ["test_edge_stream_manager.db", "test_edge_stream_manager.db-shm", "test_edge_stream_manager.db-wal"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    def test_camera_registration_and_status(self):
        self.manager.register_camera(
            camera_id="cam_01_plate",
            rtsp_url="synthetic://01",
            role="plate_entry",
            lane_id="lane_1",
            synthetic_frame_generator=lambda: np.zeros((480, 640, 3), dtype=np.uint8),
        )
        self.manager.register_camera(
            camera_id="cam_02_face",
            rtsp_url="synthetic://02",
            role="face_entry",
            lane_id="lane_1",
            synthetic_frame_generator=lambda: np.zeros((480, 640, 3), dtype=np.uint8),
        )

        statuses = self.manager.get_camera_statuses()
        self.assertEqual(len(statuses), 2)
        self.assertIn("cam_01_plate", statuses)
        self.assertIn("cam_02_face", statuses)
        self.assertEqual(statuses["cam_01_plate"]["role"], "plate_entry")

    def test_trigger_lane_arrival_clears_visitor(self):
        self.manager.register_camera(
            camera_id="cam_entry",
            rtsp_url="synthetic://entry",
            role="plate_entry",
            lane_id="lane_1",
            synthetic_frame_generator=lambda: np.zeros((480, 640, 3), dtype=np.uint8),
        )
        self.manager.start_all()
        time.sleep(0.05)

        decision = self.manager.trigger_lane_arrival(
            lane_id="lane_1",
            raw_plate_text="104822 119 16",
            plate_confidence=0.98,
            save_snapshot=False,
        )
        self.assertEqual(decision["result"], GateDecisionResult.CLEARED_VISITOR)
        self.assertTrue(decision["barrier_opened"])
        self.assertEqual(decision["wilaya"], "Alger")


class TestOnvifClient(unittest.TestCase):
    """Test ONVIF client helpers."""

    def test_rtsp_uri_construction(self):
        client = OnvifCameraClient(
            ip="192.168.10.101",
            username="admin",
            password="securePassword",
        )
        uri = client.get_rtsp_stream_uri(channel=1, subtype=0)
        self.assertEqual(uri, "rtsp://admin:securePassword@192.168.10.101:554/cam/realmonitor?channel=1&subtype=0")

    def test_unreachable_camera_fails_gracefully(self):
        # Port 59999 should immediately fail without hanging or raising unhandled exceptions
        client = OnvifCameraClient(
            ip="127.0.0.1",
            port=59999,
            timeout=0.2,
        )
        self.assertFalse(client.test_reachability())
        self.assertIsNone(client.get_snapshot_jpeg())


if __name__ == "__main__":
    unittest.main()
