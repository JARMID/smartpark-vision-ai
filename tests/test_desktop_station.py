"""
Smart Park - Unit Tests for Desktop Operator Station.
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
from desktop.src.db import DesktopDatabase
from desktop.src.modbus_direct import DirectModbusController


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

    def test_cash_drawer_kick(self):
        success, msg = self.engine.kick_cash_drawer(target="simulation")
        self.assertTrue(success)
        self.assertIn("tiroir-caisse", msg)



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

    def test_progressive_tariff_calculation(self):
        progressive_decoder = BarcodeScannerDecoder(hourly_rate_dzd=100.0, grace_period_min=15, progressive=True)
        now = datetime.now()
        entry_time = now - timedelta(minutes=75)
        res = progressive_decoder._build_scan_result(
            is_valid=True,
            barcode_raw="TEST",
            plate_snippet="104822",
            entry_time=entry_time,
            exit_time=now,
            msg="Progressive check",
        )
        self.assertEqual(res.total_due_dzd, 150.0)
        self.assertEqual(res.base_amount_dzd, 150.0)
        self.assertIn("tarif progressif", res.breakdown)

    def test_pmr_and_lost_ticket_calculation(self):
        progressive_decoder = BarcodeScannerDecoder(hourly_rate_dzd=100.0, grace_period_min=15, progressive=True)
        now = datetime.now()
        entry_time = now - timedelta(minutes=75)
        res_pmr = progressive_decoder._build_scan_result(
            is_valid=True,
            barcode_raw="TEST",
            plate_snippet="104822",
            entry_time=entry_time,
            exit_time=now,
            msg="PMR check",
            is_pmr=True,
        )
        self.assertEqual(res_pmr.total_due_dzd, 75.0)
        self.assertEqual(res_pmr.discount_dzd, 75.0)
        self.assertTrue(res_pmr.is_pmr)

        res_lost = progressive_decoder._build_scan_result(
            is_valid=True,
            barcode_raw="TEST",
            plate_snippet="104822",
            entry_time=entry_time,
            exit_time=now,
            msg="Lost check",
            is_lost_ticket=True,
        )
        self.assertEqual(res_lost.total_due_dzd, 650.0)  # 150 stay + 500 penalty = 650 DZD
        self.assertTrue(res_lost.is_lost_ticket)


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

    def tearDown(self):
        if hasattr(self, "pos") and self.pos.db:
            self.pos.db.close()

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

    def tearDown(self):
        if hasattr(self, "bridge") and self.bridge.pos_manager and self.bridge.pos_manager.db:
            self.bridge.pos_manager.db.close()

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
        if inst.pos_manager and inst.pos_manager.db:
            inst.pos_manager.db.close()

    def test_audit_data_and_reprint(self):
        # Open shift first
        self.bridge.pos_manager.open_shift("AGENT-TEST", 5000.0)

        # Get initial audit data
        audit_initial = self.bridge.get_audit_data()
        self.assertTrue(audit_initial["success"])
        self.assertIn("shift", audit_initial)

        # Process a payment
        settle_res = self.bridge.settle_payment(
            ticket_id="TKT-AUDIT-01",
            plate_number="104822 119 16",
            amount_dzd=150.0,
            payment_method="CASH",
            tendered_dzd=200.0,
        )
        self.assertTrue(settle_res["success"])

        # Check updated audit data
        audit_updated = self.bridge.get_audit_data()
        self.assertTrue(audit_updated["success"])
        self.assertGreaterEqual(len(audit_updated["transactions"]), 1)
        latest_tx = audit_updated["transactions"][0]

        # Test duplicate receipt reprint
        reprint_res = self.bridge.reprint_receipt(latest_tx["id"])
        self.assertTrue(reprint_res["success"])
        self.assertIn("DUPLICATA REÇU", reprint_res["receipt_text"])
        self.assertIn("104822 119 16", reprint_res["receipt_text"])

    def test_cctv_canvas_and_animation_pipeline_in_html(self):
        from desktop.src.operator_window import get_desktop_ui_html
        html = get_desktop_ui_html()
        self.assertIn('id="cam1Canvas"', html)
        self.assertIn('id="cam2Canvas"', html)
        self.assertIn('id="cam3Canvas"', html)
        self.assertIn('id="cam4Canvas"', html)
        self.assertIn('id="syncStatusBadge"', html)
        self.assertIn('id="txtSyncStatus"', html)
        self.assertIn('triggerManualSync', html)
        self.assertIn('updateSyncBadge', html)
        self.assertIn('window.openExitBarrier', html)
        self.assertIn('window.triggerEntryCar', html)
        self.assertIn('window.triggerFaceScan', html)
        self.assertIn('initCam1()', html)
        self.assertIn('initCam2()', html)
        self.assertIn('initCam3()', html)
        self.assertIn('initCam4()', html)

    def test_pos_tendered_amount_and_change_due_in_html_and_api(self):
        from desktop.src.operator_window import get_desktop_ui_html
        html = get_desktop_ui_html()
        self.assertIn('id="tenderedAmountInput"', html)
        self.assertIn('id="valChangeDue"', html)
        self.assertIn('calculateChangeDue', html)
        self.assertIn('setTenderedAmount', html)

        # Test settlement change calculation
        tkt = self.bridge.print_ticket("104822 119 16")
        settle_res = self.bridge.settle_payment(
            ticket_id=tkt["ticket_id"],
            plate_number="104822 119 16",
            amount_dzd=200.0,
            payment_method="CASH",
            tendered_dzd=500.0,
        )
        self.assertTrue(settle_res["success"])
        self.assertEqual(settle_res["change_dzd"], 300.0)
        self.assertEqual(settle_res["tendered_dzd"], 500.0)
        self.assertEqual(settle_res["amount_settled_dzd"], 200.0)

    def test_audit_csv_export_and_filtering_in_html(self):
        from desktop.src.operator_window import get_desktop_ui_html
        html = get_desktop_ui_html()
        self.assertIn('id="auditSearchInput"', html)
        self.assertIn('id="btnExportAudit"', html)
        self.assertIn('filterAuditTransactions', html)
        self.assertIn('exportAuditData', html)

        # Test bridge export_shift_csv
        self.bridge.pos_manager.open_shift("AGENT-TEST", 5000.0)
        self.bridge.settle_payment(
            ticket_id="TKT-CSV-01",
            plate_number="08192 120 09",
            amount_dzd=200.0,
            payment_method="CASH",
            tendered_dzd=500.0,
        )
        export_res = self.bridge.export_shift_csv()
        self.assertTrue(export_res["success"])
        self.assertIn("filepath", export_res)
        with open(export_res["filepath"], "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("08192 120 09", content)
            self.assertIn("TKT-CSV-01", content)

    def test_offline_buffer_sync_and_status(self):
        # 1. Initial status
        status = self.bridge.get_sync_status()
        self.assertIn("total_transactions", status)
        self.assertIn("pending_transactions", status)

        # 2. Settle a transaction and verify pending status
        tkt = self.bridge.print_ticket("104822 119 16")
        self.bridge.settle_payment(
            ticket_id=tkt["ticket_id"],
            plate_number="104822 119 16",
            amount_dzd=150.0,
            payment_method="CASH",
            tendered_dzd=200.0,
        )
        status_after = self.bridge.get_sync_status()
        self.assertGreater(status_after["pending_transactions"], 0)

        # 3. Test sync_offline_buffer execution
        sync_res = self.bridge.sync_offline_buffer()
        self.assertIn("pending_count", sync_res)


class TestDesktopDatabaseAndHardware(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.test_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.test_dir.name, "test_station.db")
        self.db = DesktopDatabase(self.db_path)

    def tearDown(self):
        self.db.close()
        self.test_dir.cleanup()

    def test_database_shift_and_transactions(self):
        # Open shift
        shift = self.db.get_or_open_shift(
            booth_id="BOOTH-TEST",
            cashier_id="CASHIER-01",
            cashier_name="Amine Test",
            opening_float_dzd=5000.0,
        )
        self.assertEqual(shift["booth_id"], "BOOTH-TEST")
        self.assertEqual(shift["status"], "OPEN")

        # Create local ticket
        tkt = self.db.create_local_ticket(
            plate_number="104822 119 16",
            lane_id="LANE-01",
            zone_name="Zone B",
            tariff_due_dzd=150.0,
        )
        self.assertTrue(tkt["ticket_id"].startswith("TKT-"))
        self.assertEqual(len(tkt["barcode_value"]), 13)

        # Lookup ticket
        found = self.db.find_ticket_by_barcode(tkt["barcode_value"])
        self.assertIsNotNone(found)
        self.assertEqual(found["plate_number"], "104822 119 16")

        # Record cash transaction
        tx = self.db.record_transaction(
            shift_id=shift["shift_id"],
            ticket_id=tkt["ticket_id"],
            plate_number="104822 119 16",
            entry_time=tkt["entry_time"],
            exit_time="2026-10-15 15:00:00",
            duration_minutes=45,
            amount_due_dzd=150.0,
            amount_tendered_dzd=200.0,
            change_dzd=50.0,
            payment_method="CASH",
        )
        self.assertTrue(tx["transaction_id"].startswith("TX-"))
        self.assertEqual(tx["change_dzd"], 50.0)

        # Verify recent transactions
        recent = self.db.get_recent_transactions(limit=5)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["ticket_id"], tkt["ticket_id"])

        # Log barrier override action
        self.db.log_barrier_action(
            channel=1,
            duration_ms=500,
            reason="PAYMENT_AUTHORIZED",
            operator_name="Amine Test",
            success=True,
        )

        # Close shift and check Z-Report
        z_report = self.db.close_shift(shift["shift_id"])
        self.assertEqual(z_report["status"], "CLOSED")
        self.assertEqual(z_report["total_cash_in_dzd"], 150.0)
        self.assertEqual(z_report["expected_drawer_cash_dzd"], 5150.0)
        self.assertTrue(z_report["audit_hash"].startswith("SHA256-"))

    def test_direct_modbus_controller(self):
        controller = DirectModbusController(simulation_mode=True)
        res = controller.pulse_barrier(channel=1, duration_ms=250)
        self.assertTrue(res["success"])
        self.assertEqual(res["mode"], "SIMULATION")

        # Test fallback on unreachable physical address
        hw_controller = DirectModbusController(
            host="127.0.0.1",
            port=55502,
            timeout_sec=0.1,
            simulation_mode=False,
        )
        fallback_res = hw_controller.pulse_barrier(channel=2, duration_ms=100)
        self.assertTrue(fallback_res["success"])
        self.assertEqual(fallback_res["mode"], "FALLBACK_SIMULATION")

    def test_database_sync_ledger(self):
        shift = self.db.get_or_open_shift("BOOTH-SYNC", "CASHIER-SYNC", "Amine Sync", 5000.0)
        tkt = self.db.create_local_ticket("104822 119 16", "LANE-01", "Zone A", 100.0)
        tx = self.db.record_transaction(
            shift_id=shift["shift_id"],
            ticket_id=tkt["ticket_id"],
            plate_number="104822 119 16",
            entry_time=tkt["entry_time"],
            exit_time="2026-10-17 15:00:00",
            duration_minutes=30,
            amount_due_dzd=100.0,
            amount_tendered_dzd=100.0,
            change_dzd=0.0,
            payment_method="CASH",
        )
        # Check unsynced
        unsynced = self.db.get_unsynced_transactions()
        self.assertEqual(len(unsynced), 1)
        self.assertEqual(unsynced[0]["id"], tx["transaction_id"])
        self.assertEqual(unsynced[0]["is_synced"], 0)

        # Mark synced
        self.db.mark_transactions_synced([tx["transaction_id"]])
        unsynced_after = self.db.get_unsynced_transactions()
        self.assertEqual(len(unsynced_after), 0)

        # Check sync stats
        stats = self.db.get_sync_status()
        self.assertEqual(stats["total_transactions"], 1)
        self.assertEqual(stats["pending_transactions"], 0)
        self.assertEqual(stats["synced_transactions"], 1)
        self.assertTrue(stats["is_fully_synced"])

    def test_issue_lost_ticket(self):
        bridge = DesktopBridgeApi(server_url="http://127.0.0.1:8080")
        try:
            # 1. Standard flat fee lost ticket
            res_flat = bridge.issue_lost_ticket("104822 119 16", flat_rate=True, is_pmr=False)
            self.assertTrue(res_flat["success"])
            self.assertEqual(res_flat["total_due_dzd"], 1500.0)
            self.assertTrue(res_flat["ticket_id"].startswith("TKT-"))
            self.assertEqual(len(res_flat["barcode_value"]), 13)

            # 2. PMR discounted lost ticket (50% of 1500 = 750 DZD)
            res_pmr = bridge.issue_lost_ticket("08412 00 16", flat_rate=True, is_pmr=True)
            self.assertTrue(res_pmr["success"])
            self.assertEqual(res_pmr["total_due_dzd"], 750.0)
            self.assertEqual(res_pmr["discount_dzd"], 750.0)
            self.assertTrue(res_pmr["is_pmr"])
        finally:
            bridge.pos_manager.db.close()

    def test_close_shift_with_denomination_breakdown(self):
        bridge = DesktopBridgeApi(server_url="http://127.0.0.1:8080")
        try:
            bridge.pos_manager.open_shift("CASHIER-DENOM", opening_float_dzd=5000.0)
            # Settle 500 DZD payment
            tkt = bridge.print_ticket("104822 119 16")
            bridge.settle_payment(tkt["ticket_id"], "104822 119 16", 500.0, payment_method="CASH", tendered_dzd=500.0)

            # Expected in drawer: 5000 + 500 = 5500 DZD
            denoms = {
                "2000": 2,  # 4000
                "1000": 1,  # 1000
                "500": 1,   # 500
            }  # Total 5500 DZD
            report = bridge.close_shift(denomination_counts=denoms)
            self.assertEqual(report["expected_drawer_cash_dzd"], 5500.0)
            self.assertEqual(report["physical_cash_counted_dzd"], 5500.0)
            self.assertEqual(report["cash_variance_dzd"], 0.0)
            self.assertIn("PARFAIT", report["variance_status"])
        finally:
            bridge.pos_manager.db.close()


if __name__ == "__main__":
    unittest.main()
