"""
Smart Park - Edge Multi-Channel Stream Manager.
Orchestrates multi-camera RTSP ingestion across entry lanes, biometric driver kiosks,
exit gates, and parking decks, interfacing directly with the local GateOrchestrator.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Callable
import numpy as np

from src.camera.rtsp_worker import RtspStreamWorker, CameraStreamStatus
from src.main import GateOrchestrator, GateDecisionResult

logger = logging.getLogger("smartpark.camera.manager")


class EdgeStreamManager:
    """
    Manages all physical or simulated RTSP camera channels on an edge gateway appliance.
    """

    def __init__(
        self,
        orchestrator: Optional[GateOrchestrator] = None,
        auto_start: bool = False,
    ):
        self.orchestrator = orchestrator or GateOrchestrator(simulation_mode=True)
        self.workers: Dict[str, RtspStreamWorker] = {}
        self._running = False
        self._auto_start = auto_start

    def register_camera(
        self,
        camera_id: str,
        rtsp_url: str,
        role: str,
        lane_id: str = "lane_1",
        transport: str = "tcp",
        roi_box: Optional[tuple] = None,
        synthetic_frame_generator: Optional[Callable[[], np.ndarray]] = None,
    ) -> RtspStreamWorker:
        """Register a camera channel and attach worker."""
        if camera_id in self.workers:
            logger.warning(f"Camera {camera_id} already registered. Replacing worker.")
            self.workers[camera_id].stop()

        worker = RtspStreamWorker(
            camera_id=camera_id,
            rtsp_url=rtsp_url,
            role=role,
            lane_id=lane_id,
            transport=transport,
            roi_box=roi_box,
            synthetic_frame_generator=synthetic_frame_generator,
        )
        self.workers[camera_id] = worker

        if self._running or self._auto_start:
            worker.start()

        return worker

    def start_all(self):
        """Start all registered camera workers."""
        self._running = True
        for cam_id, worker in self.workers.items():
            worker.start()
        logger.info(f"Started {len(self.workers)} camera ingestion streams.")

    def stop_all(self):
        """Stop all registered camera workers."""
        self._running = False
        for cam_id, worker in self.workers.items():
            worker.stop()
        logger.info("Stopped all camera ingestion streams.")

    def get_camera_statuses(self) -> Dict[str, Any]:
        """Return diagnostic metrics for every camera channel."""
        return {cam_id: worker.metrics for cam_id, worker in self.workers.items()}

    def trigger_lane_arrival(
        self,
        lane_id: str,
        raw_plate_text: str,
        plate_confidence: float = 0.98,
        face_embedding: Optional[np.ndarray] = None,
        liveness_score: float = 0.95,
        save_snapshot: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute an arrival verification for a given lane.
        Pulls latest optical frames from corresponding plate and driver cameras,
        passes data into GateOrchestrator, and actuates physical relays.
        """
        entry_cam = self._find_camera_by_role("plate_entry", lane_id)
        face_cam = self._find_camera_by_role("face_entry", lane_id)

        snapshot_path = None
        if save_snapshot and entry_cam:
            snapshot_path = f"snapshots/{lane_id}_{int(time.time())}.jpg"
            entry_cam.capture_snapshot(snapshot_path)

        decision = self.orchestrator.process_arrival(
            camera_id=entry_cam.camera_id if entry_cam else "sim_cam",
            raw_plate_text=raw_plate_text,
            plate_confidence=plate_confidence,
            face_embedding=face_embedding,
            liveness_score=liveness_score,
            snapshot_path=snapshot_path,
        )
        return decision

    def _find_camera_by_role(self, role: str, lane_id: str) -> Optional[RtspStreamWorker]:
        """Find registered worker matching role and lane."""
        for worker in self.workers.values():
            if worker.role == role and worker.lane_id == lane_id:
                return worker
        return None

    def close(self):
        """Clean teardown."""
        self.stop_all()
        if self.orchestrator:
            self.orchestrator.close()
