"""
Modbus TCP Barrier Gate Controller and Safety Interlock Driver.
Interfaces with industrial Ethernet relays (e.g., Waveshare 8-Channel Modbus POE Relay).
Enforces physical ground presence loop verification before barrier actuation.
"""

from dataclasses import dataclass
from enum import Enum
import socket
import time
from typing import Optional


class BarrierTriggerResult(str, Enum):
    PULSE_SENT = "pulse_sent"
    OVERRIDE_SENT = "override_sent"
    LOOP_NOT_TRIGGERED = "loop_not_triggered"
    CONNECTION_ERROR = "connection_error"


@dataclass
class TriggerResponse:
    success: bool
    result_code: BarrierTriggerResult
    latency_ms: float
    message: str


class ModbusBarrierController:
    """
    Commands industrial barrier gate relays over Modbus TCP.
    Includes a safety interlock verifying that a vehicle is physically positioned
    on the inductive ground loop before actuation.
    """

    def __init__(
        self,
        host: str = "192.168.10.200",
        port: int = 502,
        simulation_mode: bool = False,
        timeout_seconds: float = 2.0,
    ):
        self.host = host
        self.port = port
        self.simulation_mode = simulation_mode
        self.timeout = timeout_seconds
        self._simulated_loop_present = True

    def set_simulated_ground_loop(self, is_present: bool):
        """Toggle simulated inductive vehicle presence loop state for testing."""
        self._simulated_loop_present = is_present

    def is_vehicle_on_loop(self, loop_input_channel: int = 1) -> bool:
        """
        Read digital input channel corresponding to the inductive ground loop.
        Returns True if a physical vehicle is detected.
        """
        if self.simulation_mode:
            return self._simulated_loop_present

        try:
            # Modbus TCP Function 02: Read Discrete Inputs
            # Transaction ID (2B) + Protocol ID (2B) + Length (2B) + Unit ID (1B) + Func (1B) + Start (2B) + Count (2B)
            req = bytes([0x00, 0x01, 0x00, 0x00, 0x00, 0x06, 0x01, 0x02, 0x00, loop_input_channel - 1, 0x00, 0x01])
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.sendall(req)
                resp = sock.recv(32)
                if len(resp) >= 10:
                    byte_val = resp[9]
                    return (byte_val & 0x01) == 1
                return False
        except Exception:
            return False

    def trigger_barrier_open(
        self,
        channel: int = 1,
        duration_ms: int = 500,
        force_override: bool = False,
    ) -> TriggerResponse:
        """
        Send a momentary dry contact pulse to the barrier gate controller.
        Requires active vehicle presence on the ground loop unless force_override is set.
        """
        start_time = time.time()

        # Safety Interlock: Verify vehicle presence
        if not force_override:
            if not self.is_vehicle_on_loop():
                elapsed = (time.time() - start_time) * 1000.0
                return TriggerResponse(
                    success=False,
                    result_code=BarrierTriggerResult.LOOP_NOT_TRIGGERED,
                    latency_ms=elapsed,
                    message="Actuation blocked: No vehicle detected on induction ground loop.",
                )

        # Clamp channel and duration safely
        clamped_channel = max(1, min(channel, 8))
        clamped_duration_ms = min(max(duration_ms, 250), 1500)

        if self.simulation_mode:
            time.sleep(clamped_duration_ms / 1000.0)
            elapsed = (time.time() - start_time) * 1000.0
            return TriggerResponse(
                success=True,
                result_code=(
                    BarrierTriggerResult.OVERRIDE_SENT
                    if force_override
                    else BarrierTriggerResult.PULSE_SENT
                ),
                latency_ms=elapsed,
                message=f"Simulated {clamped_duration_ms}ms pulse sent on relay channel {clamped_channel}.",
            )

        try:
            # Modbus TCP Function 05: Write Single Coil (Turn ON)
            coil_addr = clamped_channel - 1
            on_cmd = bytes([0x00, 0x02, 0x00, 0x00, 0x00, 0x06, 0x01, 0x05, 0x00, coil_addr, 0xFF, 0x00])
            off_cmd = bytes([0x00, 0x03, 0x00, 0x00, 0x00, 0x06, 0x01, 0x05, 0x00, coil_addr, 0x00, 0x00])

            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                # Turn ON relay
                sock.sendall(on_cmd)
                sock.recv(32)

                try:
                    # Hold pulse duration
                    time.sleep(clamped_duration_ms / 1000.0)
                finally:
                    # Guarantee coil shutoff
                    sock.sendall(off_cmd)
                    sock.recv(32)

            elapsed = (time.time() - start_time) * 1000.0
            return TriggerResponse(
                success=True,
                result_code=(
                    BarrierTriggerResult.OVERRIDE_SENT
                    if force_override
                    else BarrierTriggerResult.PULSE_SENT
                ),
                latency_ms=elapsed,
                message=f"Relay pulse executed on channel {clamped_channel} ({clamped_duration_ms}ms).",
            )
        except Exception as ex:
            elapsed = (time.time() - start_time) * 1000.0
            return TriggerResponse(
                success=False,
                result_code=BarrierTriggerResult.CONNECTION_ERROR,
                latency_ms=elapsed,
                message=f"Modbus communication error: {str(ex)}",
            )
