"""
SmartPark Vision AI - ONVIF Camera Client & Device Discovery.
Interacts with ONVIF Profile S/T compliant IP cameras for RTSP URI resolution,
snapshot extraction, digital I/O alarm input monitoring, and network discovery.
"""

import logging
import socket
import time
from typing import Dict, List, Optional, Tuple, Any
import xml.etree.ElementTree as ET
import requests

logger = logging.getLogger("smartpark.camera.onvif")


class OnvifCameraClient:
    """
    Lightweight, dependency-free ONVIF SOAP/REST client for camera configuration and snapshots.
    """

    def __init__(
        self,
        ip: str,
        port: int = 80,
        username: str = "admin",
        password: str = "admin",
        timeout: float = 3.0,
    ):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.base_url = f"http://{ip}:{port}/onvif/device_service"

    def test_reachability(self) -> bool:
        """Check if TCP port is reachable on the camera."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            res = sock.connect_ex((self.ip, self.port))
            sock.close()
            return res == 0
        except Exception:
            return False

    def get_snapshot_jpeg(self, custom_path: Optional[str] = None) -> Optional[bytes]:
        """
        Pull a still JPEG directly from the camera HTTP snapshot endpoint.
        Standard for Dahua, Hikvision, Axis, and Uniview.
        """
        candidate_paths = [
            custom_path,
            f"http://{self.ip}:{self.port}/cgi-bin/snapshot.cgi",  # Dahua
            f"http://{self.ip}:{self.port}/ISAPI/Streaming/channels/101/picture",  # Hikvision
            f"http://{self.ip}:{self.port}/axis-cgi/jpg/image.cgi",  # Axis
            f"http://{self.ip}:{self.port}/onvif/snapshot",  # Standard ONVIF
        ]

        auth = requests.auth.HTTPDigestAuth(self.username, self.password)
        basic_auth = requests.auth.HTTPBasicAuth(self.username, self.password)

        for url in candidate_paths:
            if not url:
                continue
            try:
                # Try Digest Auth first (standard ONVIF requirement)
                resp = requests.get(url, auth=auth, timeout=self.timeout)
                if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
                    return resp.content
                # Fallback to Basic Auth
                resp = requests.get(url, auth=basic_auth, timeout=self.timeout)
                if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image"):
                    return resp.content
            except Exception:
                continue

        return None

    def get_rtsp_stream_uri(self, channel: int = 1, subtype: int = 0) -> str:
        """
        Generate standard RTSP endpoint for typical camera brands.
        """
        # Primary channel stream
        return f"rtsp://{self.username}:{self.password}@{self.ip}:554/cam/realmonitor?channel={channel}&subtype={subtype}"


def discover_onvif_cameras(timeout_sec: float = 2.0) -> List[Dict[str, Any]]:
    """
    Perform WS-Discovery broadcast to locate all ONVIF cameras on the local subnet.
    """
    ws_probe = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<Envelope xmlns="http://www.w3.org/2003/05/soap-envelope" '
        'xmlns:dn="http://www.onvif.org/ver10/network/wsdl">'
        "<Header>"
        '<wsa:MessageID xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">'
        f"uuid:{int(time.time())}"
        "</wsa:MessageID>"
        '<wsa:To xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">'
        "urn:schemas-xmlsoap-org:ws:2005:04:discovery"
        "</wsa:To>"
        '<wsa:Action xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">'
        "http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe"
        "</wsa:Action>"
        "</Header>"
        "<Body>"
        '<Probe xmlns="http://schemas.xmlsoap.org/ws/2005/04/discovery">'
        '<Types xmlns:dn="http://www.onvif.org/ver10/network/wsdl">dn:NetworkVideoTransmitter</Types>'
        "</Probe>"
        "</Body>"
        "</Envelope>"
    )

    discovered = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(timeout_sec)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        sock.sendto(ws_probe.encode("utf-8"), ("239.255.255.250", 3702))
        while True:
            try:
                data, addr = sock.recvfrom(4096)
                discovered.append({"ip": addr[0], "port": addr[1], "payload_len": len(data)})
            except socket.timeout:
                break
    except Exception as exc:
        logger.debug(f"WS-Discovery completed or restricted by local firewall: {exc}")
    finally:
        sock.close()

    return discovered
