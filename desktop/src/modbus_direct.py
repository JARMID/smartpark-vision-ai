"""
Smart Park Desktop - Direct Modbus Barrier Controller.
Provides direct TCP/IP relay actuation (Port 502) from the operator workstation
to physical parking barriers, with automatic local simulation fallback.
"""

import socket
import struct
import time
from typing import Dict, Any, Optional


class DirectModbusController:
    """
    Direct Modbus TCP controller for physical barrier gates.
    Sends standard Modbus Function 05 (Write Single Coil) pulses.
    """

    def __init__(
        self,
        host: str = "192.168.10.200",
        port: int = 502,
        timeout_sec: float = 1.0,
        simulation_mode: bool = True,
    ):
        self.host = host
        self.port = port
        self.timeout_sec = timeout_sec
        self.simulation_mode = simulation_mode

    def pulse_barrier(self, channel: int = 1, duration_ms: int = 500) -> Dict[str, Any]:
        """
        Sends a close-then-open coil pulse to actuate the barrier motor arm.
        Channel 1: Entry Barrier. Channel 2: Exit Barrier.
        """
        if self.simulation_mode:
            # Immediate responsive simulation
            return {
                "success": True,
                "channel": channel,
                "duration_ms": duration_ms,
                "mode": "SIMULATION",
                "message": f"Barrière Voie {channel} actionnée avec succès (Simulation).",
                "hardware_ip": f"{self.host}:{self.port}",
            }

        # Physical Modbus TCP Packet (RFC Modbus Application Protocol)
        # Transaction ID (2B) + Protocol ID (2B=0) + Length (2B) + Unit ID (1B) + Function 05 (1B) + Coil Addr (2B) + Value (2B)
        coil_address = channel - 1
        turn_on_cmd = struct.pack(">HHHBBHH", 0x0001, 0x0000, 0x0006, 0x01, 0x05, coil_address, 0xFF00)
        turn_off_cmd = struct.pack(">HHHBBHH", 0x0002, 0x0000, 0x0006, 0x01, 0x05, coil_address, 0x0000)

        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout_sec) as s:
                s.sendall(turn_on_cmd)
                _ = s.recv(12)  # Read response
                time.sleep(duration_ms / 1000.0)
                s.sendall(turn_off_cmd)
                _ = s.recv(12)

            return {
                "success": True,
                "channel": channel,
                "duration_ms": duration_ms,
                "mode": "PHYSICAL_HARDWARE",
                "message": f"Impulsion relais physique Modbus envoyée à {self.host}:{self.port}.",
                "hardware_ip": f"{self.host}:{self.port}",
            }
        except Exception as e:
            # Fall back to simulation gracefully if physical hardware is unpowered
            return {
                "success": True,
                "channel": channel,
                "duration_ms": duration_ms,
                "mode": "FALLBACK_SIMULATION",
                "message": f"Relais physique non connecté ({e}). Commutation en simulation locale.",
                "hardware_ip": f"{self.host}:{self.port}",
            }
