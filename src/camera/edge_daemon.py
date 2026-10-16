"""
Smart Park - Edge Camera Daemon & Hardware Firmware Bridge.
Executes autonomous multi-camera RTSP ingestion, zero-latency circular buffer capture,
on-device ALPR & biometric liveness inference, Modbus PLC gate actuation,
and automated 30-day rolling log maintenance complying with Algerian Law 25-11.
"""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
import logging
import os
import signal
import sys
import threading
import time
from typing import Dict, List, Optional, Any
import numpy as np

try:
    import yaml
except ImportError:
    yaml = None

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from src.camera.edge_stream_manager import EdgeStreamManager
from src.camera.rtsp_worker import CameraStreamStatus
from src.main import GateOrchestrator, GateDecisionResult
from src.compliance.law_25_11_audit import Law2511ComplianceEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("smartpark.edge.daemon")


class ArrivalRequest(BaseModel):
    lane_id: str = Field(default="lane_1", description="Target entry lane identifier")
    raw_plate_text: str = Field(..., description="Raw license plate string or OCR candidate")
    plate_confidence: float = Field(default=0.98, ge=0.0, le=1.0)
    face_embedding: Optional[List[float]] = Field(default=None, description="512-D ArcFace float array")
    liveness_score: float = Field(default=0.95, ge=0.0, le=1.0)
    save_snapshot: bool = Field(default=True)


class BarrierOverrideRequest(BaseModel):
    gate_id: int = Field(default=1, ge=1, le=2, description="Target gate identifier (1: Entry, 2: Exit)")
    action: str = Field(default="open", description="'open' or 'close'")
    duration_seconds: float = Field(default=5.0, ge=1.0, le=30.0)
    operator_id: str = Field(default="op_guard_01", description="Audited operator tag")


class EdgeDaemonService:
    """
    Core Edge Daemon coordinating physical camera ingestion, edge inference,
    PLC relay actuation, and automated data sovereignty lifecycle.
    """

    def __init__(self, config_path: str = "config/cameras.yaml", simulation_mode: Optional[bool] = None):
        self.config_path = config_path
        self.config = self._load_configuration(config_path)
        
        # Override simulation mode if explicitly provided
        if simulation_mode is not None:
            self.config["appliance"]["simulation_mode"] = simulation_mode

        self.sim_mode = self.config["appliance"].get("simulation_mode", True)
        self.retention_days = self.config["appliance"].get("retention_days", 30)
        self.db_path = self.config["appliance"].get("database_path", "edge_buffer.db")
        self.snapshot_dir = self.config["appliance"].get("snapshot_directory", "snapshots")

        os.makedirs(self.snapshot_dir, exist_ok=True)

        # 1. Initialize Gate Orchestrator
        hw = self.config.get("hardware", {})
        self.orchestrator = GateOrchestrator(
            db_path=self.db_path,
            modbus_host=hw.get("modbus_host", "192.168.10.200"),
            modbus_port=hw.get("modbus_port", 502),
            simulation_mode=self.sim_mode,
        )

        # 2. Initialize Stream Manager
        self.stream_manager = EdgeStreamManager(
            orchestrator=self.orchestrator,
            auto_start=False
        )

        # 3. Compliance & Purge Engine
        site_id = self.config.get("appliance", {}).get("site_id", "DZ-ALG-01")
        site_name = self.config.get("appliance", {}).get("site_name", "Parking Alger-Centre")
        self.compliance_engine = Law2511ComplianceEngine(facility_code=site_id, facility_name=site_name)
        self._purge_thread: Optional[threading.Thread] = None
        self._running = False
        self._start_time = time.time()

        # Register cameras from configuration
        self._setup_cameras()

    def _load_configuration(self, path: str) -> Dict[str, Any]:
        """Load configuration from YAML or JSON fallback."""
        if not os.path.exists(path):
            logger.warning(f"Configuration file {path} not found. Using defaults.")
            return {
                "appliance": {"simulation_mode": True, "retention_days": 30, "database_path": "edge_buffer.db"},
                "hardware": {"modbus_host": "127.0.0.1", "modbus_port": 502},
                "cameras": []
            }

        with open(path, "r", encoding="utf-8") as f:
            if path.endswith((".yaml", ".yml")) and yaml is not None:
                return yaml.safe_load(f)
            else:
                return json.load(f)

    def _setup_cameras(self):
        """Register all cameras defined in configuration."""
        cameras = self.config.get("cameras", [])
        for cam in cameras:
            cam_id = cam.get("id", "cam_default")
            rtsp_url = cam.get("rtsp_url", "")
            role = cam.get("role", "plate_entry")
            lane_id = cam.get("lane_id", "lane_1")
            transport = cam.get("transport", "tcp")
            roi = tuple(cam.get("roi_box", [0.0, 0.0, 1.0, 1.0]))

            # In simulation mode, provide a synthetic frame generator
            synth_gen = None
            if self.sim_mode:
                def make_synth_frame():
                    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                    # Simple color gradient representing active optical sensor
                    frame[:, :, 0] = 30
                    frame[:, :, 1] = 45
                    frame[:, :, 2] = 60
                    return frame
                synth_gen = make_synth_frame

            self.stream_manager.register_camera(
                camera_id=cam_id,
                rtsp_url=rtsp_url,
                role=role,
                lane_id=lane_id,
                transport=transport,
                roi_box=roi,
                synthetic_frame_generator=synth_gen,
            )
            logger.info(f"Registered camera channel [{cam_id}] for role [{role}] on lane [{lane_id}].")

    def start(self):
        """Start camera ingestion pipelines and background maintenance jobs."""
        self._running = True
        self.stream_manager.start_all()

        # Start 30-day automated rolling purge scheduler
        self._purge_thread = threading.Thread(
            target=self._run_purge_worker,
            name="SmartPark-PurgeWorker",
            daemon=True
        )
        self._purge_thread.start()
        logger.info(f"SmartPark Edge Daemon started successfully. Simulation mode: {self.sim_mode}")

    def stop(self):
        """Gracefully stop edge daemon services."""
        logger.info("Stopping SmartPark Edge Daemon services...")
        self._running = False
        self.stream_manager.stop_all()
        self.orchestrator.close()
        logger.info("SmartPark Edge Daemon stopped cleanly.")

    def _run_purge_worker(self):
        """
        Background maintenance worker enforcing Law 25-11 30-day rolling log purge.
        Executes an audit and vacuum routine every 6 hours.
        """
        interval = self.config["appliance"].get("auto_purge_interval_hours", 6) * 3600
        while self._running:
            try:
                purged_count = self.orchestrator.buffer_queue.purge_events_older_than(days=self.retention_days)
                self._purge_expired_snapshots(days=self.retention_days)
                if purged_count > 0:
                    logger.info(f"[Law 25-11 Maintenance] Automatically purged {purged_count} records older than {self.retention_days} days.")
            except Exception as e:
                logger.error(f"Error during rolling purge execution: {e}")

            # Sleep in short increments to allow rapid shutdown
            for _ in range(int(interval)):
                if not self._running:
                    break
                time.sleep(1.0)

    def _purge_expired_snapshots(self, days: int = 30):
        """Purge image snapshot files older than the retention threshold."""
        if not os.path.exists(self.snapshot_dir):
            return
        now = time.time()
        cutoff = now - (days * 86400)
        for fname in os.listdir(self.snapshot_dir):
            fpath = os.path.join(self.snapshot_dir, fname)
            if os.path.isfile(fpath):
                try:
                    if os.path.getmtime(fpath) < cutoff:
                        os.remove(fpath)
                except OSError:
                    pass

    def get_diagnostics(self) -> Dict[str, Any]:
        """Compile complete operational telemetry for desktop/cloud clients."""
        uptime = time.time() - self._start_time
        cam_statuses = self.stream_manager.get_camera_statuses()
        inside_vehicles = len(self.orchestrator.active_inside_vehicles)

        return {
            "status": "operational",
            "uptime_seconds": round(uptime, 2),
            "simulation_mode": self.sim_mode,
            "retention_days": self.retention_days,
            "connected_cameras": len(cam_statuses),
            "camera_streams": cam_statuses,
            "active_perimeter_vehicles": inside_vehicles,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# =============================================================================
# FASTAPI EDGE TELEMETRY AND CONTROL API
# =============================================================================
def create_edge_app(daemon: EdgeDaemonService) -> FastAPI:
    app = FastAPI(
        title="Smart Park - Edge Camera Daemon",
        description="Low-latency edge appliance API for camera streaming, ALPR trigger, and barrier actuation.",
        version="4.0.0"
    )

    @app.get("/api/edge/health")
    def health():
        return daemon.get_diagnostics()

    @app.get("/api/edge/cameras")
    def list_cameras():
        return daemon.stream_manager.get_camera_statuses()

    @app.post("/api/edge/arrival/process")
    def process_arrival(req: ArrivalRequest):
        face_emb = np.array(req.face_embedding, dtype=np.float32) if req.face_embedding else None
        decision = daemon.stream_manager.trigger_lane_arrival(
            lane_id=req.lane_id,
            raw_plate_text=req.raw_plate_text,
            plate_confidence=req.plate_confidence,
            face_embedding=face_emb,
            liveness_score=req.liveness_score,
            save_snapshot=req.save_snapshot,
        )
        return decision

    @app.post("/api/edge/barrier/override")
    def barrier_override(req: BarrierOverrideRequest):
        success = False
        duration_ms = int(req.duration_seconds * 1000)
        if req.action.lower() == "open":
            res = daemon.orchestrator.barrier_controller.trigger_barrier_open(
                channel=req.gate_id,
                duration_ms=duration_ms,
                force_override=True
            )
            success = res.success
        elif req.action.lower() == "close":
            res = daemon.orchestrator.barrier_controller.trigger_barrier_open(
                channel=req.gate_id + 1,
                duration_ms=duration_ms,
                force_override=True
            )
            success = res.success
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {req.action}")

        # Record manual security audit event
        daemon.orchestrator.buffer_queue.enqueue_event(
            camera_id=f"gate_{req.gate_id}",
            plate_number="MANUAL_OVERRIDE",
            ocr_confidence=1.0,
            action_taken=f"manual_override_{req.action}_{req.operator_id}",
            driver_detected=False
        )

        return {
            "status": "success" if success else "failed",
            "gate_id": req.gate_id,
            "action": req.action,
            "operator_id": req.operator_id
        }

    return app


def main():
    parser = argparse.ArgumentParser(description="Smart Park - Edge Camera Daemon")
    parser.add_argument("--config", default="config/cameras.yaml", help="Path to camera YAML configuration")
    parser.add_argument("--host", default="127.0.0.1", help="Edge API host")
    parser.add_argument("--port", type=int, default=8082, help="Edge API port")
    parser.add_argument("--simulation", action="store_true", help="Force simulation mode")
    parser.add_argument("--no-simulation", action="store_true", help="Force physical hardware mode")

    args = parser.parse_args()

    sim_mode = None
    if args.simulation:
        sim_mode = True
    elif args.no_simulation:
        sim_mode = False

    daemon = EdgeDaemonService(config_path=args.config, simulation_mode=sim_mode)
    daemon.start()

    app = create_edge_app(daemon)

    def signal_handler(sig, frame):
        logger.info("Termination signal received. Exiting...")
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info(f"Binding SmartPark Edge API to http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
