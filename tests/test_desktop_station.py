"""
SmartPark Vision AI - Unit Tests for Desktop Operator Station.
Tests Thermal Ticket Printing, Barcode Scanning, Audio Synthesizer,
POS Ledger, and Desktop Bridge API.
"""

from datetime import datetime, timedelta
import os
import unittest

from desktop.src.printer import ThermalTicketEngine, ParkingTicket, EscPosCommands
from desktop.src.scanner import BarcodeScannerDecoder, ScanResult
from desktop.src.audio_synthesizer import AudioThreatSynthesizer
from desktop.src.pos_manager import CashierPosManager, TransactionRecord
from desktop.src.operator_window import DesktopBridgeApi, launch_desktop_station


class TestThermalTicketEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ThermalTicketEngine(facility_name="SMARTPARK TEST")

    def test_ticket_generation_and_ean13(self):
        ticket = self.engine.generate_ticket(plate_number="104822 119 16", lane_id="LANE-01")
        self.assertIsNotNone(ticket)
        self.assertTrue(ticket.ticket_id.startswith("TKT-"))
        self.assertEqual(len(ticket.barcode_value), 13)
        self.assertTrue(ticket.barcode_value.startswith("99"))

        # Verify checksum calculation
        base12 = ticket.barcode_value[:12]
        expected_chk = ThermalTicketEngine._calculate_ean13_checksum(base12)
        self.assertEqual(int(ticket.barcode_value[12]), expected_chk)

    def test_escpos_binary_rendering(self):
        ticket = self.engine.generate_ticket(plate_number="08412 00 16")
        raw = self.engine.render_escpos_binary(ticket)
        self.assertIsInstance(raw, bytes)
        self.assertTrue(raw.startswith(EscPosCommands.HW_INIT))
        self.assertIn(b"SMARTPARK TEST", raw)
        self.assertIn(b"08412 00 16", raw)
        self.assertTrue(raw.endswith(EscPosCommands.CUT_PAPER_FULL))

    def test_svg_and_text_preview(self):
        ticket = self.engine.generate_ticket(plate_number="04122 118 16")
        text = self.engine.render_text_preview(ticket)
        self.assertIn("TICKET D'ENTREE", text)
        self.assertIn("04122 118 16", text)

        svg = self.engine.render_svg_ticket(ticket)
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("04122 118 16", svg)
        self.assertIn(ticket.barcode_value, svg)

    def test_dispatch_simulation(self):
        ticket = self.engine.generate_ticket(plate_number="104822 119 16")
        success, msg = self.engine.dispatch_print_job(ticket, target="simulation")
        self.assertTrue(success)
        self.assertIn("simulation spooler", msg)


class TestBarcodeScannerDecoder(unittest.TestCase):
    def setUp(self):
        self.decoder = BarcodeScannerDecoder(hourly_rate_dzd=100.0, grace_period_min=15)

    def test_valid_ean13_decoding(self):
        # Generate valid 13-digit code: 991001048221 + checksum 8
        base12 = "991001048221"
        chk = BarcodeScannerDecoder._calc_checksum(base12)
        ean13 = f"{base12}{chk}"

        result = self.decoder.decode_input(ean13)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.plate_number_snippet, "048221")
        self.assertGreater(result.total_due_dzd, 0.0)

    def test_invalid_checksum_rejection(self):
        # 991001048221 has checksum 9. Using 5 makes it deliberately invalid.
        invalid_code = "9910010482215"
        result = self.decoder.decode_input(invalid_code)
        self.assertFalse(result.is_valid)
        self.assertIn("Somme de controle invalide", result.status_message)

    def test_grace_period_calculation(self):
        now = datetime.now()
        entry_time = now - timedelta(minutes=10)
        result = self.decoder._build_scan_result(
            is_valid=True,
            barcode_raw="TEST",
            plate_snippet="104822",
            entry_time=entry_time,
            exit_time=now,
            msg="Grace check",
        )
        self.assertTrue(result.is_grace_period)
        self.assertEqual(result.total_due_dzd, 0.0)

    def test_multi_hour_tariff_rounding(self):
        now = datetime.now()
        # 75 minutes = 2 chargeable hours (ceiling of 75/60 = 2 hours) -> 200 DZD
        entry_time = now - timedelta(minutes=75)
        result = self.decoder._build_scan_result(
            is_valid=True,
            barcode_raw="TEST",
            plate_snippet="104822",
            entry_time=entry_time,
            exit_time=now,
            msg="Multi-hour check",
        )
        self.assertFalse(result.is_grace_period)
        self.assertEqual(result.total_due_dzd, 200.0)

    def test_pipe_payload_qr_decoding(self):
        now = datetime.now()
        past = now - timedelta(minutes=90)
        qr_str = f"SPK|TKT-2026-001|{past.isoformat()}|104822 119 16"
        result = self.decoder.decode_input(qr_str, exit_time=now)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.plate_number_snippet, "104822 119 16")
        self.assertEqual(result.total_due_dzd, 200.0)


class TestAudioThreatSynthesizer(unittest.TestCase):
    def test_wav_buffer_synthesis(self):
        synth = AudioThreatSynthesizer(enabled=True)
        buf = synth.synthesize_wav_buffer([880, 1175], duration_s=0.1, sample_rate=44100)
        self.assertTrue(buf.startswith(b"RIFF"))
        self.assertIn(b"WAVEfmt ", buf)
        self.assertGreater(len(buf), 1000)

    def test_non_blocking_calls(self):
        synth = AudioThreatSynthesizer(enabled=False)  # Disabled to keep CI silent
        # Verify method calls execute without exceptions
        synth.play_siren_threat(cycles=1)
        synth.play_warning_beep(count=1)
        synth.play_success_chime()


class TestCashierPosManager(unittest.TestCase):
    def setUp(self):
        self.pos = CashierPosManager(booth_id="BOOTH-01")
        self.pos.open_shift("AGENT-SALAH", 5000.0)

    def test_shift_lifecycle_and_transactions(self):
        # Process cash transaction
        tx1 = self.pos.process_settlement(
            ticket_id="TKT-001",
            plate_number="104822 119 16",
            amount_dzd=200.0,
            payment_method="CASH",
            tendered_dzd=500.0,
        )
        self.assertEqual(tx1.change_dzd, 300.0)
        self.assertEqual(tx1.amount_dzd, 200.0)

        # Process CIB terminal transaction
        tx2 = self.pos.process_settlement(
            ticket_id="TKT-002",
            plate_number="04122 118 16",
            amount_dzd=100.0,
            payment_method="CIB_TERMINAL",
        )
        self.assertEqual(tx2.change_dzd, 0.0)

        # Verify shift totals
        shift = self.pos.active_shift
        self.assertEqual(shift.tickets_settled_count, 2)
        self.assertEqual(shift.total_cash_collected_dzd, 200.0)
        self.assertEqual(shift.total_card_collected_dzd, 100.0)

        # Close shift and verify Z-Report
        z_rep = self.pos.close_shift()
        self.assertEqual(z_rep["tickets_processed"], 2)
        self.assertEqual(z_rep["total_revenue_dzd"], 300.0)
        self.assertEqual(z_rep["expected_drawer_cash_dzd"], 5200.0)
        self.assertTrue(z_rep["audit_hash"].startswith("SHA256-"))


class TestDesktopBridgeApi(unittest.TestCase):
    def setUp(self):
        self.bridge = DesktopBridgeApi(server_url="http://127.0.0.1:8080")

    def test_barrier_and_simulation(self):
        # Trigger barrier in local simulation mode
        res = self.bridge.trigger_barrier(channel=1, duration_ms=250)
        self.assertTrue(res["success"])

        # Test scenario simulation
        res_scen = self.bridge.simulate_scenario("vip_entry")
        self.assertTrue(res_scen["success"])

    def test_ticket_print_and_scan_flow(self):
        print_res = self.bridge.print_ticket("104822 119 16", "LANE-01")
        self.assertTrue(print_res["success"])
        self.assertIn("svg_preview", print_res)

        # Scan the generated barcode
        scan_res = self.bridge.scan_ticket(print_res["barcode_value"])
        self.assertTrue(scan_res["is_valid"])

        # Settle payment
        pay_res = self.bridge.settle_payment(
            ticket_id=print_res["ticket_id"],
            plate_number="104822 119 16",
            amount_dzd=scan_res["total_due_dzd"],
            payment_method="CASH",
            tendered_dzd=scan_res["total_due_dzd"] + 100.0,
        )
        self.assertTrue(pay_res["success"])
        self.assertEqual(pay_res["change_dzd"], 100.0)

    def test_headless_launcher(self):
        inst = launch_desktop_station(server_url="http://127.0.0.1:8080", headless=True)
        self.assertIsNotNone(inst)


if __name__ == "__main__":
    unittest.main()
