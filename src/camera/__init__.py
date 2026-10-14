"""
SmartPark Vision AI - Camera and Ingestion Module.
Contains RTSP stream ingestion workers, ONVIF discovery, and multi-channel edge management.
"""

from src.camera.rtsp_worker import RtspStreamWorker, CameraStreamStatus
from src.camera.edge_stream_manager import EdgeStreamManager

__all__ = ["RtspStreamWorker", "CameraStreamStatus", "EdgeStreamManager"]
