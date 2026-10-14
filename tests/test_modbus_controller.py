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


if __name__ == "__main__":
    unittest.main()
