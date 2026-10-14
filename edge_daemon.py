#!/usr/bin/env python3
"""
SmartPark Vision AI - Standalone Physical Edge Appliance Daemon.
Runs natively on on-premise industrial gateways (NVIDIA Jetson, Advantech IPC).
Manages physical RTSP streams, executes sub-250ms offline decisions,
and pulses physical barrier relays over RS-485 / Modbus.
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
from typing import Dict, Any

from src.main import GateOrchestrator
from src.camera.edge_stream_manager import EdgeStreamManager
from src.camera.rtsp_worker import CameraStreamStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("smartpark.edge.daemon")


class EdgeApplianceDaemon:
    """
    Main runtime daemon for on-site parking edge hardware.
    """

    def __init__(self, config_path: str, mode: str = "simulation", db_path: str = "edge_buffer.db"):
        self.config_path = config_path
        self.mode = mode.lower()
        self.db_path = db_path
        self.running = False

        self.config = self._load_config()
        self.orchestrator: GateOrchestrator = None
        self.stream_manager: EdgeStreamManager = None

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            logger.warning(f"Config {self.config_path} not found. Using default camera map.")
            return {"cameras": []}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def initialize(self):
        """Set up orchestrator and camera channels."""
        is_simulation = self.mode != "physical"
        logger.info(f"Initializing Edge Appliance Daemon (Mode: {self.mode.upper()})...")

        barrier_cfg = self.config.get("barrier_hardware", {})
        self.orchestrator = GateOrchestrator(
            db_path=self.db_path,
            modbus_host=barrier_cfg.get("fallback_tcp_host", "192.168.10.200"),
            modbus_port=barrier_cfg.get("fallback_tcp_port", 502),
            simulation_mode=is_simulation,
            liveness_threshold=0.60,
        )

        self.stream_manager = EdgeStreamManager(
            orchestrator=self.orchestrator,
            auto_start=False,
        )

        cameras = self.config.get("cameras", [])
        for cam in cameras:
            cam_id = cam.get("camera_id")
            rtsp_url = cam.get("rtsp_url")
            role = cam.get("role", "plate_entry")
            lane_id = cam.get("lane_id", "lane_1")
            roi = tuple(cam.get("roi_box")) if cam.get("roi_box") else None

            # If simulation mode, provide a synthetic generator if needed
            generator = None
            if is_simulation:
                import numpy as np
                generator = lambda: np.zeros((720, 1280, 3), dtype=np.uint8)

            self.stream_manager.register_camera(
                camera_id=cam_id,
                rtsp_url=rtsp_url,
                role=role,
                lane_id=lane_id,
                transport=cam.get("transport", "tcp"),
                roi_box=roi,
                synthetic_frame_generator=generator,
            )

        logger.info(f"Registered {len(cameras)} cameras from hardware manifest.")

    def run(self):
        """Main daemon loop."""
        self.running = True
        self.stream_manager.start_all()

        logger.info("=======================================================")
        logger.info(" SmartPark Vision AI - Edge Daemon Running 24/7        ")
        logger.info(" Sovereign Edge Node Active (Algerian Law 25-11 Ready) ")
        logger.info(" Sub-250ms Offline Verification Ready                  ")
        logger.info("=======================================================")

        last_status_report = time.time()

        try:
            while self.running:
                now = time.time()
                # Periodic health logging every 60 seconds
                if now - last_status_report >= 60.0:
                    last_status_report = now
                    statuses = self.stream_manager.get_camera_statuses()
                    for cam_id, stats in statuses.items():
                        logger.info(
                            f"Channel {cam_id} [{stats['role']}]: {stats['status'].upper()} | "
                            f"Ingested: {stats['frames_ingested']} | "
                            f"Dropped: {stats['frames_dropped']} | "
                            f"Reconnects: {stats['reconnects']}"
                        )
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Shutdown initiated by operator.")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean release of network sockets, camera streams, and database handles."""
        self.running = False
        logger.info("Releasing hardware handles and stopping camera threads...")
        if self.stream_manager:
            self.stream_manager.close()
        logger.info("Edge Appliance Daemon safely stopped.")


def main():
    parser = argparse.ArgumentParser(description="SmartPark Vision AI - Edge Camera Daemon")
    parser.add_argument(
        "--config",
        default="config/cameras.json",
        help="Path to cameras configuration file",
    )
    parser.add_argument(
        "--mode",
        choices=["physical", "simulation"],
        default="simulation",
        help="Operation mode: physical (real RTSP + RS485) or simulation",
    )
    parser.add_argument(
        "--db",
        default="edge_buffer.db",
        help="Path to local SQLite buffer database",
    )
    args = parser.parse_args()

    daemon = EdgeApplianceDaemon(
        config_path=args.config,
        mode=args.mode,
        db_path=args.db,
    )

    # Register POSIX / OS signals for clean exit
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}. Exiting gracefully...")
        daemon.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, signal_handler)

    daemon.initialize()
    daemon.run()


if __name__ == "__main__":
    main()
