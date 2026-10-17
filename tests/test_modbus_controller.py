"""
Unit tests for the Modbus TCP Barrier Controller.
Verifies pulse duration, simulation mode, and vehicle presence loop interlock safety gates.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.barrier.modbus_controller import ModbusBarrierController, BarrierTriggerResult


class TestModbusBarrierController(unittest.TestCase):
    def setUp(self):
        # Simulation mode enabled for unit testing without physical relay hardware
        self.controller = ModbusBarrierController(
            host="192.168.10.200", port=502, simulation_mode=True
        )

    def test_open_with_vehicle_present(self):
        # When ground loop detects a vehicle (is_vehicle_present=True), pulse opens barrier
        self.controller.set_simulated_ground_loop(is_present=True)
        result = self.controller.trigger_barrier_open(channel=1, duration_ms=500)
        self.assertTrue(result.success)
        self.assertEqual(result.result_code, BarrierTriggerResult.PULSE_SENT)
        self.assertTrue(result.latency_ms >= 0)

    def test_open_blocked_without_vehicle_present(self):
        # When ground loop detects no vehicle (is_vehicle_present=False), pulse is blocked for safety
        self.controller.set_simulated_ground_loop(is_present=False)
        result = self.controller.trigger_barrier_open(channel=1, duration_ms=500)
        self.assertFalse(result.success)
        self.assertEqual(result.result_code, BarrierTriggerResult.LOOP_NOT_TRIGGERED)

    def test_manual_override_bypasses_loop(self):
        # Guard manual override can open barrier even if vehicle loop is inactive (e.g. high-chassis tractor)
        self.controller.set_simulated_ground_loop(is_present=False)
        result = self.controller.trigger_barrier_open(channel=1, duration_ms=500, force_override=True)
        self.assertTrue(result.success)
        self.assertEqual(result.result_code, BarrierTriggerResult.OVERRIDE_SENT)


import socket
import struct
import threading
import time

from desktop.src.modbus_direct import DirectModbusController


class TestModbusPhysicalSocket(unittest.TestCase):
    """
    Real TCP socket loopback verification.
    Spawns an industrial Modbus TCP server thread on localhost to verify
    exact binary packet structures (RFC Modbus Application Protocol) and
    hardware relay actuation behavior without physical PLC hardware.
    """

    def setUp(self):
        # Create server socket on localhost with ephemeral OS-assigned port
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(("127.0.0.1", 0))
        self.port = self.server_sock.getsockname()[1]
        self.server_sock.listen(1)
        self.received_packets = []
        self._stop_server = False

    def tearDown(self):
        self._stop_server = True
        try:
            self.server_sock.close()
        except Exception:
            pass

    def _run_mock_waveshare_server(self):
        """Thread worker acting as an industrial 8-channel Waveshare Modbus relay."""
        def server_thread():
            self.server_sock.settimeout(4.0)
            while not self._stop_server:
                try:
                    client, _ = self.server_sock.accept()
                except (socket.timeout, OSError):
                    break
                with client:
                    client.settimeout(2.0)
                    while not self._stop_server:
                        try:
                            data = client.recv(1024)
                            if not data:
                                break
                            self.received_packets.append(data)
                            func_code = data[7] if len(data) >= 8 else 0
                            if func_code == 0x02:
                                # Function 02 response: bit 0 = 1 (vehicle detected on loop)
                                resp = bytes([data[0], data[1], 0x00, 0x00, 0x00, 0x04, 0x01, 0x02, 0x01, 0x01])
                                client.sendall(resp)
                            else:
                                # Function 05 echo
                                client.sendall(data)
                        except (socket.timeout, OSError):
                            break
        t = threading.Thread(target=server_thread, daemon=True)
        t.start()
        return t

    def test_physical_modbus_packet_encoding_and_timing(self):
        """Verify byte-for-byte correctness of Modbus Function 05 ON/OFF frames."""
        srv_thread = self._run_mock_waveshare_server()

        controller = ModbusBarrierController(
            host="127.0.0.1",
            port=self.port,
            simulation_mode=False,
            timeout_seconds=2.0,
        )

        res = controller.trigger_barrier_open(channel=1, duration_ms=250)
        self._stop_server = True
        srv_thread.join(timeout=2.0)

        self.assertTrue(res.success)
        self.assertEqual(res.result_code, BarrierTriggerResult.PULSE_SENT)
        # Should receive: Packet 0 (Func 02 loop query), Packet 1 (Func 05 ON), Packet 2 (Func 05 OFF)
        self.assertGreaterEqual(len(self.received_packets), 3)

        # 1. Packet 0: Function 02 Read Discrete Inputs
        f02_pkt = self.received_packets[0]
        self.assertEqual(f02_pkt[7], 2)

        # 2. Packet 1: Turn ON Channel 1 (Coil Address 0x0000, Value 0xFF00)
        on_pkt = self.received_packets[1]
        self.assertEqual(len(on_pkt), 12)
        tx_id, proto, length, unit, func, coil, val = struct.unpack(">HHHBBHH", on_pkt)
        self.assertEqual(proto, 0x0000)
        self.assertEqual(length, 6)
        self.assertEqual(unit, 1)
        self.assertEqual(func, 5)  # Write Single Coil
        self.assertEqual(coil, 0)  # Channel 1 -> Coil 0
        self.assertEqual(val, 0xFF00)  # ON

        # 3. Packet 2: Turn OFF Channel 1 (Coil Address 0x0000, Value 0x0000)
        off_pkt = self.received_packets[2]
        self.assertEqual(len(off_pkt), 12)
        tx_id_off, proto_off, length_off, unit_off, func_off, coil_off, val_off = struct.unpack(">HHHBBHH", off_pkt)
        self.assertEqual(proto_off, 0x0000)
        self.assertEqual(length_off, 6)
        self.assertEqual(unit_off, 1)
        self.assertEqual(func_off, 5)
        self.assertEqual(coil_off, 0)
        self.assertEqual(val_off, 0x0000)  # OFF

    def test_direct_modbus_controller_physical_socket(self):
        """Verify DirectModbusController sends correct binary frames to relay."""
        srv_thread = self._run_mock_waveshare_server()

        direct_ctrl = DirectModbusController(
            host="127.0.0.1",
            port=self.port,
            simulation_mode=False,
            timeout_sec=2.0,
        )
        res = direct_ctrl.pulse_barrier(channel=2, duration_ms=250)
        self._stop_server = True
        srv_thread.join(timeout=2.0)

        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "PHYSICAL_HARDWARE")
        self.assertEqual(len(self.received_packets), 2)

        # Channel 2 -> Coil Address 1
        _, _, _, _, func, coil, val = struct.unpack(">HHHBBHH", self.received_packets[0])
        self.assertEqual(func, 5)
        self.assertEqual(coil, 1)
        self.assertEqual(val, 0xFF00)

        _, _, _, _, func_off, coil_off, val_off = struct.unpack(">HHHBBHH", self.received_packets[1])
        self.assertEqual(func_off, 5)
        self.assertEqual(coil_off, 1)
        self.assertEqual(val_off, 0x0000)

    def test_physical_connection_failure_handling(self):
        """Verify proper error handling when physical relay is unreachable."""
        unused_port = self.port
        self.server_sock.close()

        controller = ModbusBarrierController(
            host="127.0.0.1",
            port=unused_port,
            simulation_mode=False,
            timeout_seconds=0.5,
        )
        # Using force_override bypasses loop check and exercises physical socket failure
        res = controller.trigger_barrier_open(channel=1, duration_ms=250, force_override=True)
        self.assertFalse(res.success)
        self.assertEqual(res.result_code, BarrierTriggerResult.CONNECTION_ERROR)


if __name__ == "__main__":
    unittest.main()
