"""
Smart Park - Desktop Operator Workstation Application.
Runs on Windows Edge WebView2 or cross-platform webview shell.
Provides 4-channel CCTV grid, emergency Spacebar barrier override,
threat HUD siren alerts, biometric triage modal, cashier POS,
ESC/POS thermal ticket printing, and trilingual Day/Night localization.
"""

from datetime import datetime, timedelta
import json
import os
import sys
import threading
import time
from typing import Optional, Dict, Any

from desktop.src.printer import ThermalTicketEngine, ParkingTicket
from desktop.src.scanner import BarcodeScannerDecoder, ScanResult
from desktop.src.audio_synthesizer import AudioThreatSynthesizer
from desktop.src.pos_manager import CashierPosManager
from desktop.src.modbus_direct import DirectModbusController


class DesktopBridgeApi:
    """
    Python backend exposed directly to JavaScript in the desktop window via pywebview.
    Operates with full offline resilience, local SQLite persistence, and direct Modbus control.
    """

    def __init__(
        self,
        server_url: str = "http://127.0.0.1:8080",
        booth_id: str = "BOOTH-01",
        cashier_id: str = "AGENT-MEZIANE",
        config: Optional[Dict[str, Any]] = None,
    ):
        self.server_url = server_url
        self.booth_id = booth_id
        self.cashier_id = cashier_id
        self.config = config or {}
        facility_name = self.config.get("facility_name", "Smart Park Alger-Centre")
        self.printer_engine = ThermalTicketEngine(facility_name=facility_name)
        self.scanner_decoder = BarcodeScannerDecoder()
        self.audio_synth = AudioThreatSynthesizer()
        self.pos_manager = CashierPosManager(booth_id=self.booth_id)
        modbus_cfg = self.config.get("direct_modbus", {})
        mb_host = modbus_cfg.get("host", "192.168.10.200")
        mb_port = modbus_cfg.get("port", 502)
        mb_sim = modbus_cfg.get("simulation_mode", True)
        self.modbus_direct = DirectModbusController(host=mb_host, port=mb_port, simulation_mode=mb_sim)

    def get_gateway_info(self) -> Dict[str, Any]:
        """Return gateway server connection metadata including derived WebSocket URL."""
        clean_url = self.server_url.rstrip("/")
        ws_url = clean_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"
        return {
            "server_url": clean_url,
            "ws_url": ws_url,
            "booth_id": self.booth_id,
            "cashier_id": self.cashier_id,
        }

    def trigger_barrier(self, channel: int = 1, duration_ms: int = 500) -> Dict[str, Any]:
        """Trigger physical Modbus barrier relay via backend server or direct local TCP socket."""
        import urllib.request
        self.audio_synth.play_success_chime()
        url = f"{self.server_url}/api/barrier/override"
        payload = json.dumps({"channel": channel, "duration_ms": duration_ms}).encode("utf-8")
        
        # Try backend server first, fallback to direct Modbus TCP
        server_ok = False
        server_data = None
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                server_data = json.loads(resp.read().decode("utf-8"))
                server_ok = True
        except Exception:
            pass

        # Trigger direct Modbus relay as well
        direct_res = self.modbus_direct.pulse_barrier(channel=channel, duration_ms=duration_ms)

        # Log into persistent SQLite barrier audit log
        try:
            cashier = self.pos_manager.active_shift.cashier_id if self.pos_manager.active_shift else "BOOTH-01"
            self.pos_manager.db.log_barrier_action(
                channel=channel,
                duration_ms=duration_ms,
                reason="Impulsion manuelle poste operateur",
                operator_name=cashier,
                success=True,
            )
        except Exception:
            pass

        if server_ok:
            return {"success": True, "message": f"Barriere voie {channel} actionnee (Synchronise)", "data": server_data}
        else:
            return {
                "success": True,
                "message": f"Barriere voie {channel} actionnee ({direct_res.get('message', 'Mode Autonome Direct')})",
                "channel": channel,
                "duration_ms": duration_ms,
                "mode": direct_res.get("mode", "LOCAL_AUTONOMOUS"),
            }

    def simulate_scenario(self, scenario_key: str) -> Dict[str, Any]:
        """Trigger edge event scenario."""
        import urllib.request
        url = f"{self.server_url}/api/simulate"
        payload = json.dumps({"scenario": scenario_key}).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                if scenario_key in ("watchlist_alert", "spoof_attack", "clone_plate"):
                    self.audio_synth.play_siren_threat(cycles=3)
                elif scenario_key in ("vip_entry", "temporary_00", "visitor_payment_exit"):
                    self.audio_synth.play_success_chime()
                return {"success": True, "result": res}
        except Exception as e:
            # Local simulation fallback
            if scenario_key in ("watchlist_alert", "spoof_attack"):
                self.audio_synth.play_siren_threat(cycles=2)
            else:
                self.audio_synth.play_success_chime()
            return {"success": True, "simulation_fallback": True, "scenario": scenario_key}

    def scan_ticket(self, barcode_str: str) -> Dict[str, Any]:
        """Decode barcode/QR payload and return ticket dues."""
        result = self.scanner_decoder.decode_input(barcode_str)
        if result.is_valid:
            self.audio_synth.play_success_chime()
        else:
            self.audio_synth.play_warning_beep(2)

        # Resolve actual ticket record from local SQLite if present
        db_ticket = self.pos_manager.db.find_ticket_by_barcode(barcode_str)
        ticket_id = db_ticket["ticket_id"] if db_ticket else (barcode_str if barcode_str.startswith("TKT-") else f"TKT-{barcode_str[:8]}")
        plate = db_ticket["plate_number"] if db_ticket else result.plate_number_snippet
        entry_time_str = db_ticket["entry_time"] if db_ticket else result.entry_time.strftime("%Y-%m-%d %H:%M:%S")

        return {
            "is_valid": result.is_valid,
            "ticket_id": ticket_id,
            "barcode_raw": result.barcode_raw,
            "plate_snippet": plate,
            "entry_time": entry_time_str,
            "exit_time": result.exit_time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_minutes": result.elapsed_minutes,
            "hourly_rate_dzd": result.hourly_rate_dzd,
            "total_due_dzd": result.total_due_dzd,
            "is_grace_period": result.is_grace_period,
            "status_message": result.status_message,
        }

    def print_ticket(self, plate_number: str, lane_id: str = "LANE-01") -> Dict[str, Any]:
        """Generate thermal parking ticket and send to spooler."""
        ticket = self.printer_engine.generate_ticket(plate_number, lane_id=lane_id)
        success, msg = self.printer_engine.dispatch_print_job(ticket, target="simulation")
        svg_preview = self.printer_engine.render_svg_ticket(ticket)
        text_preview = self.printer_engine.render_text_preview(ticket)

        # Persist to local SQLite store for offline tracking and settlement
        try:
            self.pos_manager.db.create_local_ticket(
                plate_number=ticket.plate_number,
                lane_id=ticket.lane_id,
                zone_name=ticket.zone_name,
                tariff_due_dzd=ticket.tariff_hourly_dzd,
                ticket_id=ticket.ticket_id,
                barcode_value=ticket.barcode_value,
            )
        except Exception:
            pass

        self.audio_synth.play_success_chime()
        return {
            "success": success,
            "message": msg,
            "ticket_id": ticket.ticket_id,
            "barcode_value": ticket.barcode_value,
            "svg_preview": svg_preview,
            "text_preview": text_preview,
        }

    def settle_payment(
        self,
        ticket_id: str,
        plate_number: str,
        amount_dzd: float,
        payment_method: str = "CASH",
        tendered_dzd: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Settle ticket fee, update cash drawer, and pulse exit barrier."""
        tx = self.pos_manager.process_settlement(
            ticket_id=ticket_id,
            plate_number=plate_number,
            amount_dzd=amount_dzd,
            payment_method=payment_method,
            tendered_dzd=tendered_dzd,
        )
        self.audio_synth.play_success_chime()
        # Pulse cash drawer on cash transactions
        if payment_method.upper() == "CASH":
            self.printer_engine.kick_cash_drawer()
        # Open exit barrier
        self.trigger_barrier(channel=2, duration_ms=500)
        return {
            "success": True,
            "transaction_id": tx.transaction_id,
            "change_dzd": tx.change_dzd,
            "amount_settled_dzd": tx.amount_dzd,
            "tendered_dzd": tx.tendered_dzd,
            "message": f"Paiement {payment_method} enregistre. Monnaie rendue: {tx.change_dzd:.0f} DZD. Barriere de sortie ouverte.",
        }

    def close_shift(self, denomination_counts: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """Compile shift report with physical cash denomination reconciliation."""
        report = self.pos_manager.close_shift(denomination_counts=denomination_counts)
        self.audio_synth.play_success_chime()
        return report

    def issue_lost_ticket(
        self,
        plate_number: str,
        flat_rate: bool = True,
        is_pmr: bool = False,
    ) -> Dict[str, Any]:
        """
        Process a lost ticket resolution for a vehicle plate.
        Calculates fee (flat 1500 DZD or accrued + 500 DZD surcharge),
        prints replacement thermal ticket, and creates local SQLite entry.
        """
        clean_plate = plate_number.strip().upper() if plate_number else "INCONNU"
        now = datetime.now()
        entry_time = None

        if not flat_rate:
            db_ticket = self.pos_manager.db.find_ticket_by_barcode(clean_plate)
            if db_ticket and "entry_time" in db_ticket:
                try:
                    entry_time = datetime.strptime(db_ticket["entry_time"], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass

        if entry_time:
            calc = self.scanner_decoder.tariff_engine.calculate_fee(
                entry_time=entry_time,
                exit_time=now,
                is_pmr=is_pmr,
                is_lost_ticket=True,
                flat_lost_ticket=False,
            )
        else:
            calc = self.scanner_decoder.tariff_engine.calculate_fee(
                entry_time=now - timedelta(hours=2),
                exit_time=now,
                is_pmr=is_pmr,
                is_lost_ticket=True,
                flat_lost_ticket=True,
            )

        due_dzd = calc["total_due_dzd"]
        ticket = self.printer_engine.generate_ticket(clean_plate, lane_id="CAISSE-01")
        ticket.zone_name = "REMPLACEMENT (TICKET PERDU)"
        ticket.tariff_hourly_dzd = due_dzd

        svg_preview = self.printer_engine.render_svg_ticket(ticket)
        text_preview = self.printer_engine.render_text_preview(ticket)

        try:
            self.pos_manager.db.create_local_ticket(
                plate_number=ticket.plate_number,
                lane_id=ticket.lane_id,
                zone_name=ticket.zone_name,
                tariff_due_dzd=due_dzd,
                ticket_id=ticket.ticket_id,
                barcode_value=ticket.barcode_value,
            )
        except Exception:
            pass

        self.audio_synth.play_warning_beep(1)

        return {
            "success": True,
            "ticket_id": ticket.ticket_id,
            "barcode_value": ticket.barcode_value,
            "plate_number": clean_plate,
            "total_due_dzd": due_dzd,
            "base_amount_dzd": calc.get("base_amount_dzd", due_dzd),
            "discount_dzd": calc.get("discount_dzd", 0.0),
            "breakdown": calc.get("breakdown", "Forfait Ticket Perdu"),
            "is_pmr": is_pmr,
            "svg_preview": svg_preview,
            "text_preview": text_preview,
            "message": f"Ticket de remplacement généré pour {clean_plate}. Montant: {due_dzd:.0f} DZD.",
        }

    def get_audit_data(self) -> Dict[str, Any]:
        """Fetch local SQLite transaction history, barrier logs, and active shift status."""
        try:
            txs = self.pos_manager.db.get_recent_transactions(limit=20)
            barrier_logs = self.pos_manager.db.get_recent_barrier_logs(limit=20)
            shift = self.pos_manager.active_shift
            shift_info = {
                "shift_id": shift.shift_id if shift else "AUCUN",
                "cashier_name": getattr(shift, "cashier_name", getattr(shift, "cashier_id", "Agent")) if shift else "Non assigné",
                "opening_float_dzd": shift.opening_float_dzd if shift else 0.0,
                "total_cash_dzd": shift.total_cash_collected_dzd if shift else 0.0,
                "total_card_dzd": shift.total_card_collected_dzd if shift else 0.0,
                "expected_drawer_dzd": ((shift.opening_float_dzd + shift.total_cash_collected_dzd) if shift else 0.0),
                "transaction_count": shift.tickets_settled_count if shift else 0,
                "status": "OUVERT" if shift else "FERMÉ",
            }
            return {
                "success": True,
                "transactions": txs,
                "barrier_logs": barrier_logs,
                "shift": shift_info,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "transactions": [], "barrier_logs": []}

    def sync_offline_buffer(self) -> Dict[str, Any]:
        """Synchronize unsynced local SQLite transactions and barrier logs to the gateway server."""
        import urllib.request
        unsynced_txs = self.pos_manager.db.get_unsynced_transactions(limit=100)
        recent_barrier = self.pos_manager.db.get_recent_barrier_logs(limit=20)
        if not unsynced_txs:
            return {
                "success": True,
                "synced_count": 0,
                "pending_count": 0,
                "message": "Toutes les transactions locales sont déjà synchronisées avec la passerelle.",
            }

        url = f"{self.server_url}/api/pos/sync"
        payload = json.dumps({
            "station_id": self.config.get("station_id", "DESKTOP-STATION-01"),
            "booth_id": self.booth_id,
            "cashier_id": self.cashier_id,
            "transactions": unsynced_txs,
            "barrier_logs": recent_barrier,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ack_ids = data.get("ack_ids", [])
                if ack_ids:
                    self.pos_manager.db.mark_transactions_synced(ack_ids)
                self.audio_synth.play_success_chime()
                rem = self.pos_manager.db.get_sync_status()
                return {
                    "success": True,
                    "synced_count": len(ack_ids),
                    "pending_count": rem.get("pending_transactions", 0),
                    "message": f"Synchronisation réussie: {len(ack_ids)} transactions transmises à la passerelle.",
                }
        except Exception as e:
            return {
                "success": False,
                "synced_count": 0,
                "pending_count": len(unsynced_txs),
                "error": str(e),
                "message": f"Passerelle inaccessible ({str(e)}). Transactions conservées dans le tampon SQLite local.",
            }

    def get_sync_status(self) -> Dict[str, Any]:
        """Fetch current sync statistics from local SQLite store."""
        try:
            return self.pos_manager.db.get_sync_status()
        except Exception as e:
            return {"total_transactions": 0, "pending_transactions": 0, "synced_transactions": 0, "error": str(e)}

    def export_shift_csv(self) -> Dict[str, Any]:
        """Export local SQLite transactions to a CSV file on disk in data/exports."""
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            export_dir = os.path.join(base_dir, "data", "exports")
            os.makedirs(export_dir, exist_ok=True)
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"shift_audit_{now_str}.csv"
            filepath = os.path.join(export_dir, filename)

            txs = self.pos_manager.db.get_recent_transactions(limit=1000)
            lines = [
                "id,receipt_number,ticket_id,plate_number,entry_time,exit_time,duration_minutes,amount_due_dzd,amount_tendered_dzd,change_dzd,payment_method,shift_id,created_at"
            ]
            for t in txs:
                lines.append(
                    f'"{t.get("id","")}","{t.get("receipt_number","")}","{t.get("ticket_id","")}","{t.get("plate_number","")}","{t.get("entry_time","")}","{t.get("exit_time","")}",{t.get("duration_minutes",0)},{t.get("amount_due_dzd",0)},{t.get("amount_tendered_dzd",0)},{t.get("change_dzd",0)},"{t.get("payment_method","")}","{t.get("shift_id","")}",{t.get("created_at",0)}'
                )

            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            return {
                "success": True,
                "filepath": filepath,
                "filename": filename,
                "total_rows": len(txs),
                "message": f"Export réussi: {filename} ({len(txs)} transactions)",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "message": f"Échec export: {str(e)}"}

    def reprint_receipt(self, tx_id: str) -> Dict[str, Any]:
        """Generate and spool duplicate thermal receipt for a past transaction."""
        tx = self.pos_manager.db.get_transaction_by_id(tx_id)
        if not tx:
            return {"success": False, "message": f"Transaction {tx_id} introuvable."}

        self.audio_synth.play_success_chime()
        receipt_lines = [
            "=" * 32,
            "         SMART PARK         ",
            "   --- DUPLICATA REÇU ---   ",
            "=" * 32,
            f"REÇU N°   : {tx.get('receipt_number', 'N/A')}",
            f"DATE/HEURE: {tx.get('exit_time', tx.get('entry_time', 'N/A'))}",
            f"VÉHICULE  : {tx.get('plate_number', 'N/A')}",
            f"TICKET ID : {tx.get('ticket_id', 'N/A')}",
            f"DURÉE     : {tx.get('duration_minutes', 0)} min",
            "-" * 32,
            f"MONTANT DÛ: {tx.get('amount_due_dzd', 0.0):.2f} DZD",
            f"MODE      : {tx.get('payment_method', 'CASH')}",
            f"REÇU      : {tx.get('amount_tendered_dzd', 0.0):.2f} DZD",
            f"RENDU     : {tx.get('change_dzd', 0.0):.2f} DZD",
            "=" * 32,
            "    MERCI DE VOTRE VISITE   ",
            "     SMART PARK - ALGER     ",
            "=" * 32,
        ]
        receipt_text = "\n".join(receipt_lines)
        return {
            "success": True,
            "receipt_number": tx.get("receipt_number"),
            "receipt_text": receipt_text,
            "message": f"Duplicata {tx.get('receipt_number')} généré avec succès.",
        }

    def play_sound(self, sound_type: str) -> bool:
        """Trigger sound effect."""
        if sound_type == "siren":
            self.audio_synth.play_siren_threat(cycles=3)
        elif sound_type == "warning":
            self.audio_synth.play_warning_beep(2)
        elif sound_type == "success":
            self.audio_synth.play_success_chime()
        return True

    def guard_decision(self, plate: str, decision: str, reason: str = "") -> Dict[str, Any]:
        """Manual guard decision from biometric triage modal."""
        import urllib.request
        url = f"{self.server_url}/api/guard/decision"
        payload = json.dumps({"plate": plate, "decision": decision, "reason": reason}).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                if decision == "grant":
                    self.audio_synth.play_success_chime()
                    self.trigger_barrier(channel=1)
                else:
                    self.audio_synth.play_warning_beep(3)
                return {"success": True, "result": res}
        except Exception:
            if decision == "grant":
                self.audio_synth.play_success_chime()
                self.trigger_barrier(channel=1)
            else:
                self.audio_synth.play_warning_beep(2)
            return {"success": True, "decision": decision, "plate": plate}


def get_desktop_ui_html() -> str:
    """Return self-contained HTML/CSS/JS for the Desktop Operator Station."""
    return """<!DOCTYPE html>
<html lang="fr" data-theme="dark" dir="ltr">
<head>
  <meta charset="UTF-8">
  <title>Smart Park - Poste Opérateur et Caisse</title>
  <style>
    :root {
      --bg-primary: #080C14;
      --bg-surface: #0D131F;
      --bg-surface-elevated: #161F30;
      --border-color: #1A2436;
      --text-main: #F8FAFC;
      --text-muted: #94A3B8;
      --accent-cyan: #00F2FE;
      --accent-blue: #38BDF8;
      --accent-blue-hover: #0284C7;
      --accent-green: #10B981;
      --accent-mint: #00F5A0;
      --accent-red: #F43F5E;
      --accent-amber: #FB923C;
      --font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }

    [data-theme="light"] {
      --bg-primary: #F1F5F9;
      --bg-surface: #FFFFFF;
      --bg-surface-elevated: #E2E8F0;
      --border-color: #CBD5E1;
      --text-main: #0F172A;
      --text-muted: #64748B;
      --accent-cyan: #0284C7;
      --accent-blue: #0284C7;
      --accent-blue-hover: #0369A1;
      --accent-green: #059669;
      --accent-mint: #10B981;
      --accent-red: #DC2626;
      --accent-amber: #D97706;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-primary);
      color: var(--text-main);
      font-family: var(--font-family);
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      user-select: none;
    }

    /* Top Command Header */
    header {
      background-color: var(--bg-surface);
      border-bottom: 1px solid var(--border-color);
      padding: 10px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
    }
    .brand-section {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-badge {
      background: linear-gradient(135deg, #0284C7, #2563EB);
      color: white;
      font-weight: 800;
      font-size: 13px;
      padding: 4px 10px;
      border-radius: 6px;
      letter-spacing: 0.5px;
    }
    .brand-title {
      font-size: 16px;
      font-weight: 700;
      letter-spacing: 0.5px;
    }
    .header-pills {
      display: flex;
      gap: 10px;
      align-items: center;
    }
    .status-pill {
      font-size: 12px;
      padding: 4px 10px;
      border-radius: 20px;
      background: rgba(16, 185, 129, 0.15);
      color: var(--accent-green);
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: var(--accent-green);
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(1.2); }
      100% { opacity: 1; transform: scale(1); }
    }
    .hotkey-indicator {
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 4px;
      background: var(--bg-surface-elevated);
      color: var(--text-muted);
      border: 1px solid var(--border-color);
      font-family: monospace;
    }

    /* Threat Alert Banner */
    #threatBanner {
      display: none;
      background-color: var(--accent-red);
      color: white;
      padding: 10px 20px;
      font-weight: 700;
      font-size: 14px;
      align-items: center;
      justify-content: space-between;
      will-change: opacity;
      animation: strobe-composited 1s infinite alternate ease-in-out;
      flex-shrink: 0;
    }
    @keyframes strobe-composited {
      from { opacity: 1.0; }
      to { opacity: 0.65; }
    }

    /* Main Grid Layout */
    .workspace {
      display: grid;
      grid-template-columns: 1fr 380px;
      flex: 1;
      overflow: hidden;
      gap: 12px;
      padding: 12px;
    }

    /* Left: 4-Channel CCTV Grid */
    .cctv-matrix {
      display: grid;
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr 1fr;
      gap: 10px;
      height: 100%;
    }
    .camera-tile {
      background-color: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      position: relative;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .camera-tile.active-threat {
      border: 2px solid var(--accent-red);
    }
    .camera-header {
      position: absolute;
      top: 8px;
      left: 10px;
      right: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 10;
      background: rgba(15, 23, 42, 0.75);
      backdrop-filter: blur(4px);
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
    }
    .camera-feed-canvas {
      flex: 1;
      width: 100%;
      height: 100%;
      background: #020617;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .camera-telemetry {
      position: absolute;
      bottom: 8px;
      left: 10px;
      right: 10px;
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      font-family: monospace;
      color: #38BDF8;
      background: rgba(15, 23, 42, 0.85);
      padding: 4px 8px;
      border-radius: 4px;
    }

    /* Right: Control Center & POS Panel */
    .controls-panel {
      background-color: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .tabs-header {
      display: flex;
      border-bottom: 1px solid var(--border-color);
      background-color: var(--bg-surface);
    }
    .tab-btn {
      flex: 1;
      padding: 10px;
      background: none;
      border: none;
      color: var(--text-muted);
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      text-align: center;
    }
    .tab-btn.active {
      color: var(--accent-blue);
      border-bottom: 2px solid var(--accent-blue);
      background-color: var(--bg-surface-elevated);
    }
    .tab-content {
      flex: 1;
      overflow-y: auto;
      padding: 14px;
      display: none;
    }
    .tab-content.active {
      display: block;
    }

    /* Emergency Override Spacebar Button */
    .emergency-pulse-btn {
      width: 100%;
      background: linear-gradient(135deg, #EF4444, #B91C1C);
      color: white;
      border: none;
      border-radius: 8px;
      padding: 16px;
      font-size: 15px;
      font-weight: 800;
      letter-spacing: 1px;
      cursor: pointer;
      box-shadow: 0 4px 14px rgba(239, 68, 68, 0.4);
      margin-bottom: 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
    }
    .emergency-pulse-btn:hover {
      background: linear-gradient(135deg, #DC2626, #991B1B);
    }
    .emergency-pulse-btn:active {
      transform: translateY(2px);
    }
    .pulse-sub {
      font-size: 11px;
      font-weight: 500;
      opacity: 0.85;
      font-family: monospace;
    }

    /* POS Input and Buttons */
    .form-group {
      margin-bottom: 12px;
    }
    .form-label {
      font-size: 12px;
      color: var(--text-muted);
      margin-bottom: 4px;
      display: block;
    }
    .form-input {
      width: 100%;
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 8px 12px;
      color: var(--text-main);
      font-family: monospace;
      font-size: 13px;
    }
    .form-input:focus {
      outline: 2px solid var(--accent-blue);
    }
    .btn-action {
      background-color: var(--accent-blue);
      color: white;
      border: none;
      padding: 10px 14px;
      border-radius: 6px;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      width: 100%;
      margin-top: 6px;
    }
    .btn-action:hover {
      background-color: var(--accent-blue-hover);
    }
    .btn-secondary {
      background-color: var(--bg-surface-elevated);
      color: var(--text-main);
      border: 1px solid var(--border-color);
      padding: 8px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
    }

    /* Tariff calculation summary card */
    .tariff-card {
      background: var(--bg-surface-elevated);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 12px;
      margin-top: 10px;
    }
    .tariff-row {
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      margin-bottom: 6px;
    }
    .tariff-total {
      font-size: 16px;
      font-weight: 800;
      color: var(--accent-green);
      border-top: 1px solid var(--border-color);
      padding-top: 8px;
      margin-top: 8px;
    }

    /* Modal */
    .modal-backdrop {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(4px);
      z-index: 100;
      align-items: center;
      justify-content: center;
    }
    .modal-box {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      width: 580px;
      max-width: 90vw;
      padding: 24px;
    }

    /* Quick Shortcuts Footer */
    footer {
      background-color: var(--bg-surface);
      border-top: 1px solid var(--border-color);
      padding: 6px 16px;
      font-size: 11px;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
    }
  </style>
</head>
<body>

  <!-- Top Header -->
  <header>
    <div class="brand-section">
      <div class="brand-badge" style="background: linear-gradient(135deg, #00F2FE, #0284C7); color: #080C14; font-weight: 800; display: flex; align-items: center; gap: 6px;">
        <svg width="18" height="18" viewBox="0 0 512 512" fill="none">
          <rect x="150" y="110" width="50" height="290" rx="25" fill="#080C14"/>
          <path d="M180 110 L310 110 C375 110, 410 145, 410 200 C410 255, 375 275, 310 275 L180 275" stroke="#080C14" stroke-width="36" stroke-linecap="round"/>
          <line x1="180" y1="270" x2="390" y2="120" stroke="#10B981" stroke-width="32" stroke-linecap="round"/>
        </svg>
        <span>SMART PARK</span>
      </div>
      <div class="brand-title" id="txtTitle">Smart Park &bull; Poste Opérateur et Caisse</div>
      <div class="hotkey-indicator">[BOOTH-01]</div>
    </div>
    <div class="header-pills">
      <div class="status-pill" id="syncStatusBadge" onclick="triggerManualSync()" style="cursor: pointer;" title="Cliquer pour forcer la synchronisation avec la passerelle">
        <div class="status-dot" id="syncDot" style="background-color: var(--accent-green);"></div>
        <span id="txtSyncStatus">SYNC: À JOUR</span>
      </div>
      <div class="status-pill" id="gatewayWsBadge" title="Flux télémétrie WebSocket passerelle">
        <div class="status-dot" id="wsDot" style="background-color: var(--accent-green);"></div>
        <span id="txtWsStatus">PASSERELLE EN LIGNE</span>
      </div>
      <div class="status-pill">
        <div class="status-dot"></div>
        <span id="txtStatus">MODBUS DIRECT EN LIGNE</span>
      </div>
      <button class="btn-secondary" onclick="toggleTheme()" id="btnTheme">Mode Jour / Nuit (D)</button>
      <button class="btn-secondary" onclick="cycleLanguage()" id="btnLang">Langue: FR (L)</button>
    </div>
  </header>

  <!-- Threat Warning Banner -->
  <div id="threatBanner">
    <span id="threatText">ALERTE SÉCURITÉ: VÉHICULE RECHERCHÉ OU TENTATIVE DE SPOOFING</span>
    <button class="btn-secondary" onclick="dismissThreat()" style="background: white; color: #DC2626;">Fermer (Esc)</button>
  </div>

  <!-- Main Workspace -->
  <div class="workspace">

    <!-- Left 4-Channel CCTV Grid -->
    <div class="cctv-matrix">
      <!-- Cam 1: Entry Plate -->
      <div class="camera-tile" id="tileCam1">
        <div class="camera-header">
          <strong id="lblCam1">CAM 1: Entrée ALPR (Voie 1)</strong>
          <span class="hotkey-indicator" id="cam1ArmPill">1080p @ 30fps</span>
        </div>
        <div class="camera-feed-canvas">
          <canvas id="cam1Canvas" width="400" height="240" style="width:100%;height:100%;display:block;object-fit:cover;"></canvas>
        </div>
        <div class="camera-telemetry">
          <span>RTSP: TCP // IMX678</span>
          <span id="fpsCam1">LATENCE: 18ms</span>
        </div>
      </div>

      <!-- Cam 2: Driver Face NIR -->
      <div class="camera-tile" id="tileCam2">
        <div class="camera-header">
          <strong id="lblCam2">CAM 2: Kiosque Biométrique (Voie 1)</strong>
          <span class="hotkey-indicator" id="cam2NirPill">RGB + NIR 850nm</span>
        </div>
        <div class="camera-feed-canvas">
          <canvas id="cam2Canvas" width="400" height="240" style="width:100%;height:100%;display:block;object-fit:cover;"></canvas>
        </div>
        <div class="camera-telemetry">
          <span>ARCFACE 512-D</span>
          <span id="cam2Dist">DISTANCE: 0.418</span>
        </div>
      </div>

      <!-- Cam 3: Exit Plate -->
      <div class="camera-tile" id="tileCam3">
        <div class="camera-header">
          <strong id="lblCam3">CAM 3: Sortie &amp; Barrière (Voie 2)</strong>
          <span class="hotkey-indicator" id="cam3ArmPill">BARRIÈRE: FERMÉE</span>
        </div>
        <div class="camera-feed-canvas">
          <canvas id="cam3Canvas" width="400" height="240" style="width:100%;height:100%;display:block;object-fit:cover;"></canvas>
        </div>
        <div class="camera-telemetry">
          <span id="cam3LoopStatus">BOUCLE INDUCTIVE: ACTIVE</span>
          <span id="gateStatus">BARRIÈRE: FERMÉE</span>
        </div>
      </div>

      <!-- Cam 4: Deck Overhead -->
      <div class="camera-tile" id="tileCam4">
        <div class="camera-header">
          <strong id="lblCam4">CAM 4: Vue Plafond Niveau 0</strong>
          <span class="hotkey-indicator">Fisheye 12MP</span>
        </div>
        <div class="camera-feed-canvas">
          <canvas id="cam4Canvas" width="400" height="240" style="width:100%;height:100%;display:block;object-fit:cover;"></canvas>
        </div>
        <div class="camera-telemetry">
          <span id="cam4Occ">OCCUPATION: 8 / 14 PLACES</span>
          <span id="cam4Disp">DISPONIBLES: 6</span>
        </div>
      </div>
    </div>

    <!-- Right Controls & POS Panel -->
    <div class="controls-panel">
      <!-- Emergency Override Pulse Button -->
      <div style="padding: 14px 14px 0 14px;">
        <button class="emergency-pulse-btn" onclick="triggerManualBarrier()" id="btnBarrier">
          <span>OUVERTURE BARRIÈRE D'URGENCE</span>
          <span class="pulse-sub">APPUYEZ SUR ESPACE (SPACEBAR)</span>
        </button>
      </div>

      <!-- Tab Selection -->
      <div class="tabs-header">
        <button class="tab-btn active" onclick="switchTab('pos')" id="tabPos">Caisse POS</button>
        <button class="tab-btn" onclick="switchTab('scenarios')" id="tabScenarios">Scénarios (1-7)</button>
        <button class="tab-btn" onclick="switchTab('ticket')" id="tabTicket">Ticket Thermique</button>
        <button class="tab-btn" onclick="switchTab('audit')" id="tabAudit">Journal &amp; Audit</button>
      </div>

      <!-- POS Tab Content -->
      <div id="panePos" class="tab-content active">
        <div class="form-group">
          <label class="form-label" id="lblScan">Scan Code-Barres / Entrée Manuelle (Touche S):</label>
          <input type="text" id="barcodeInput" class="form-input" placeholder="Scanner ticket ou saisir..." onkeydown="handleBarcodeEnter(event)">
          <button class="btn-action" onclick="executeScan()" style="margin-top:6px;" id="btnVerify">Vérifier Ticket</button>
        </div>

        <div id="scanResultCard" class="tariff-card" style="display:none;">
          <div class="tariff-row">
            <span id="lblPlate">Immatriculation:</span>
            <strong id="valPlate">--</strong>
          </div>
          <div class="tariff-row">
            <span id="lblDuration">Durée Stationnée:</span>
            <strong id="valDuration">-- min</strong>
          </div>
          <div class="tariff-row">
            <span id="lblRate">Tarif Appliqué:</span>
            <span id="valRate">100 DZD / heure</span>
          </div>
          <div class="tariff-row tariff-total">
            <span id="lblTotal">Montant à Payer:</span>
            <span id="valTotal">0 DZD</span>
          </div>

          <!-- Cash Tendered & Change Due Section -->
          <div style="margin-top: 10px; padding: 10px; background: var(--bg-surface-elevated); border: 1px solid var(--border-color); border-radius: 6px;">
            <label class="form-label" style="font-size:11px; margin-bottom:4px;" id="lblTendered">Montant Reçu Espèces (DZD) :</label>
            <div style="display:flex; gap:6px; align-items:center;">
              <input type="number" id="tenderedAmountInput" class="form-input" style="padding:6px 8px; font-size:13px; font-weight:700;" placeholder="ex: 500" oninput="calculateChangeDue()">
              <div style="display:flex; gap:4px;">
                <button type="button" class="btn-secondary" style="padding:4px 8px; font-size:11px;" onclick="setTenderedAmount(200)">200</button>
                <button type="button" class="btn-secondary" style="padding:4px 8px; font-size:11px;" onclick="setTenderedAmount(500)">500</button>
                <button type="button" class="btn-secondary" style="padding:4px 8px; font-size:11px;" onclick="setTenderedAmount(1000)">1000</button>
              </div>
            </div>
            <div class="tariff-row" style="margin-top:6px; font-weight:700; color:#10B981;">
              <span id="lblChangeDue">Monnaie à Rendre :</span>
              <strong id="valChangeDue">0 DZD</strong>
            </div>
          </div>

          <div style="margin-top: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
            <button class="btn-action" style="background:#10B981;" onclick="processPayment('CASH')" id="btnCash">Espèces (P)</button>
            <button class="btn-action" style="background:#0284C7;" onclick="processPayment('CIB_TERMINAL')" id="btnCard">Carte CIB</button>
          </div>
        </div>

        <div style="margin-top: 14px; display:flex; flex-direction:column; gap:8px;">
          <button class="btn-secondary" style="width:100%; border-color:#F59E0B; color:#F59E0B; font-weight:700;" onclick="showLostTicketModal()" id="btnLostTicket">⚠️ Régularisation Ticket Perdu</button>
          <button class="btn-secondary" style="width:100%;" onclick="closeShiftZReport()" id="btnZReport">Clôture de Caisse (Rapport Z)</button>
        </div>
      </div>

      <!-- Scenarios Tab Content -->
      <div id="paneScenarios" class="tab-content">
        <p style="font-size:12px; color:var(--text-muted); margin-bottom:10px;" id="lblQuickScenarios">Déclencheurs rapides de simulation :</p>
        <div style="display:flex; flex-direction:column; gap:8px;">
          <button class="btn-secondary" onclick="triggerScenario('vip_entry')" style="text-align:left;">[1] Accès VIP Reconnu (Amine Hadj)</button>
          <button class="btn-secondary" onclick="triggerScenario('temporary_00')" style="text-align:left;">[2] Plaque Provisoire 00 (Carte Grise)</button>
          <button class="btn-secondary" onclick="triggerScenario('watchlist_alert')" style="text-align:left; color:#EF4444; font-weight:700;">[3] Alerte Véhicule Recherché (Fiche Vol)</button>
          <button class="btn-secondary" onclick="triggerScenario('spoof_attack')" style="text-align:left; color:#EF4444; font-weight:700;">[4] Tentative Attaque Photo (Anti-Spoof)</button>
          <button class="btn-secondary" onclick="triggerScenario('driver_mismatch')" style="text-align:left;">[5] Discordance Chauffeur / Véhicule</button>
          <button class="btn-secondary" onclick="triggerScenario('visitor_payment_exit')" style="text-align:left;">[6] Règlement Sortie Visiteur</button>
          <button class="btn-secondary" onclick="triggerScenario('clone_dispute')" style="text-align:left; color:#F59E0B; font-weight:700;">[7] Conflit Plaque Clonée (Double Entrée)</button>
        </div>
      </div>

      <!-- Ticket Tab Content -->
      <div id="paneTicket" class="tab-content">
        <div class="form-group">
          <label class="form-label" id="lblManualPlate">Immatriculation Visiteur:</label>
          <input type="text" id="manualPlateInput" class="form-input" value="08412 00 16">
          <button class="btn-action" onclick="printManualTicket()" id="btnPrintTicket">Imprimer Ticket Entrée (T)</button>
        </div>
        <div id="ticketPreviewArea" style="margin-top:10px; overflow-x:auto;">
          <!-- Vector ticket preview will render here -->
        </div>
      </div>

      <!-- Audit & Ledger Tab Content -->
      <div id="paneAudit" class="tab-content">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <span style="font-weight:700; font-size:12px;" id="lblAuditTitle">Transactions Récentes (SQLite Local)</span>
          <div style="display:flex; gap:6px;">
            <button class="btn-secondary" style="width:auto; padding:3px 8px; font-size:11px;" onclick="exportAuditData()" id="btnExportAudit">Exporter CSV</button>
            <button class="btn-secondary" style="width:auto; padding:3px 8px; font-size:11px;" onclick="loadAuditData()">Actualiser</button>
          </div>
        </div>
        <div class="form-group" style="margin-bottom:8px;">
          <input type="text" id="auditSearchInput" class="form-input" placeholder="Rechercher par plaque ou reçu..." oninput="filterAuditTransactions()" style="font-size:11px; padding:6px 10px;">
        </div>
        <div id="auditShiftSummary" class="tariff-card" style="margin-bottom:10px; font-size:11px; padding:10px;">
          <div style="color:var(--text-muted);">Chargement du bilan de caisse...</div>
        </div>
        <div style="font-size:11px; font-weight:bold; margin-bottom:5px; color:var(--text-muted);">Derniers Règlements :</div>
        <div id="auditTxList" style="max-height:160px; overflow-y:auto; display:flex; flex-direction:column; gap:6px;">
          <div style="color:var(--text-muted); font-size:11px;">Aucune transaction enregistrée.</div>
        </div>
        <div style="font-size:11px; font-weight:bold; margin-top:10px; margin-bottom:5px; color:var(--text-muted);">Journal des Barrières (Modbus) :</div>
        <div id="auditBarrierList" style="max-height:110px; overflow-y:auto; display:flex; flex-direction:column; gap:4px; font-size:10.5px;">
          <div style="color:var(--text-muted); font-size:11px;">Aucun événement barrière récent.</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Biometric Triage Modal -->
  <div class="modal-backdrop" id="triageModal">
    <div class="modal-box">
      <h3 style="margin-bottom:12px; color:#EF4444;" id="txtModalTitle">Avis Manuel Agent: Discordance Biométrique</h3>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:16px;">
        <div style="background:var(--bg-surface-elevated); padding:10px; border-radius:6px; text-align:center;">
          <p style="font-size:11px; color:var(--text-muted); margin-bottom:6px;">Photo Caméra NIR (Direct)</p>
          <div style="height:120px; background:#0F172A; display:flex; align-items:center; justify-content:center; color:#38BDF8; font-weight:bold;">Conducteur Voie 1</div>
        </div>
        <div style="background:var(--bg-surface-elevated); padding:10px; border-radius:6px; text-align:center;">
          <p style="font-size:11px; color:var(--text-muted); margin-bottom:6px;">Fiche Référence Abonné</p>
          <div style="height:120px; background:#0F172A; display:flex; align-items:center; justify-content:center; color:#10B981; font-weight:bold;">Profil VIP Enrôlé</div>
        </div>
      </div>
      <p style="font-size:12px; margin-bottom:16px; color:var(--text-muted);">Distance euclidienne: 0.684 (Seuil: 0.55). Veuillez valider manuellement l'accès ou ordonner un contrôle physique.</p>
      <div style="display:flex; justify-content:flex-end; gap:10px;">
        <button class="btn-secondary" onclick="resolveTriage('deny')" style="color:#EF4444;">Refuser Accès (Backspace)</button>
        <button class="btn-action" onclick="resolveTriage('grant')" style="width:auto; padding:8px 16px;">Valider &amp; Ouvrir (Entrée)</button>
      </div>
    </div>
  </div>

  <!-- Lost Ticket Modal -->
  <div id="lostTicketModal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.8); z-index:200; align-items:center; justify-content:center;">
    <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px; width:460px; max-width:90%; padding:20px;">
      <h3 style="margin-top:0; color:#F59E0B; display:flex; align-items:center; gap:8px;">
        <span>⚠️ Régularisation Ticket Perdu</span>
      </h3>
      <p style="font-size:12px; color:var(--text-muted); margin-bottom:14px;">
        Calcul automatique du forfait municipal ou recherche horodatée en base de données locale.
      </p>
      <div class="form-group">
        <label class="form-label">Numéro d'immatriculation du véhicule :</label>
        <input type="text" id="lostPlateInput" class="form-input" placeholder="ex: 104822 119 16" value="104822 119 16">
      </div>
      <div style="margin-bottom:12px; display:flex; flex-direction:column; gap:8px; font-size:12px;">
        <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
          <input type="checkbox" id="lostFlatRateCheck" checked>
          <span>Appliquer forfait administratif standard (1 500 DZD)</span>
        </label>
        <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
          <input type="checkbox" id="lostPmrCheck">
          <span>Véhicule PMR / Carte d'invalidité (Remise 50%)</span>
        </label>
      </div>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
        <button class="btn-secondary" onclick="closeLostTicketModal()">Annuler</button>
        <button class="btn-action" style="background:#F59E0B; color:#0F172A; font-weight:700;" onclick="submitLostTicket()">Générer Ticket de Sortie</button>
      </div>
    </div>
  </div>

  <!-- Z-Report Denomination Reconciliation Modal -->
  <div id="zReportModal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.8); z-index:200; align-items:center; justify-content:center;">
    <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:12px; width:480px; max-width:95%; padding:20px;">
      <h3 style="margin-top:0; color:#38BDF8; display:flex; align-items:center; gap:8px;">
        <span>📊 Clôture de Caisse &amp; Décompte Physique</span>
      </h3>
      <p style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">
        Saisie des coupures physiques pour calcul automatique de l'écart de caisse avant certification Z.
      </p>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:12px;">
        <div>
          <label class="form-label" style="font-size:11px;">Billets 2000 DZD :</label>
          <input type="number" id="denom2000" class="form-input" placeholder="0" min="0" oninput="updatePhysicalCashCount()">
        </div>
        <div>
          <label class="form-label" style="font-size:11px;">Billets 1000 DZD :</label>
          <input type="number" id="denom1000" class="form-input" placeholder="0" min="0" oninput="updatePhysicalCashCount()">
        </div>
        <div>
          <label class="form-label" style="font-size:11px;">Billets 500 DZD :</label>
          <input type="number" id="denom500" class="form-input" placeholder="0" min="0" oninput="updatePhysicalCashCount()">
        </div>
        <div>
          <label class="form-label" style="font-size:11px;">Pièces 200 DZD :</label>
          <input type="number" id="denom200" class="form-input" placeholder="0" min="0" oninput="updatePhysicalCashCount()">
        </div>
        <div>
          <label class="form-label" style="font-size:11px;">Pièces 100 DZD :</label>
          <input type="number" id="denom100" class="form-input" placeholder="0" min="0" oninput="updatePhysicalCashCount()">
        </div>
        <div>
          <label class="form-label" style="font-size:11px;">Pièces 50 DZD :</label>
          <input type="number" id="denom50" class="form-input" placeholder="0" min="0" oninput="updatePhysicalCashCount()">
        </div>
      </div>
      <div style="padding:10px; background:var(--bg-surface-elevated); border:1px solid var(--border-color); border-radius:6px; margin-bottom:14px;">
        <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
          <span>Espèces Comptées :</span>
          <strong id="valPhysicalCashCounted">0 DZD</strong>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:12px; color:var(--text-muted); margin-bottom:4px;">
          <span>Solde Théorique Attendu :</span>
          <strong id="valExpectedDrawerCash">-- DZD</strong>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:700;">
          <span>Écart de Caisse :</span>
          <strong id="valCashVariance" style="color:#10B981;">0 DZD (Parfait)</strong>
        </div>
      </div>
      <div style="display:flex; justify-content:flex-end; gap:8px;">
        <button class="btn-secondary" onclick="closeZReportModal()">Annuler</button>
        <button class="btn-action" style="background:#10B981;" onclick="submitZReportFinal()">Valider &amp; Clôturer Shift</button>
      </div>
    </div>
  </div>

  <!-- Bottom Quick Hotkeys Reference Bar -->
  <footer>
    <div>
      <span id="txtShortcuts">Raccourcis Clavier: </span>
      <span class="hotkey-indicator">Espace = Barrière</span>
      <span class="hotkey-indicator">1-7 = Scénarios</span>
      <span class="hotkey-indicator">T = Ticket</span>
      <span class="hotkey-indicator">S = Scanner</span>
      <span class="hotkey-indicator">P = Encaisser</span>
      <span class="hotkey-indicator">Esc = Alerte</span>
    </div>
    <div>Smart Park v2.0 - Station Opérateur et Caisse</div>
  </footer>

  <script>
    let currentLang = 'fr';
    let currentTheme = 'dark';
    let currentScanData = null;

    const I18N = {
      fr: {
        title: "Poste Opérateur & Caisse Dédié",
        status: "MODBUS & RTSP EN LIGNE",
        cam1: "CAM 1: Entrée ALPR (Voie 1)",
        cam2: "CAM 2: Kiosque Biométrique (Voie 1)",
        cam3: "CAM 3: Sortie & Barrière (Voie 2)",
        cam4: "CAM 4: Vue Plafond Niveau 0",
        barrier: "OUVERTURE BARRIÈRE D'URGENCE",
        barrierSub: "APPUYEZ SUR ESPACE (SPACEBAR)",
        tabPos: "Caisse POS",
        tabScenarios: "Scénarios (1-7)",
        tabTicket: "Ticket Thermique",
        tabAudit: "Journal & Audit",
        lblAuditTitle: "Transactions Récentes (SQLite Local)",
        lblScan: "Scan Code-Barres / Entrée Manuelle (Touche S):",
        btnVerify: "Vérifier Ticket",
        lblPlate: "Immatriculation:",
        lblDuration: "Durée Stationnée:",
        lblRate: "Tarif Appliqué:",
        lblTotal: "Montant à Payer:",
        lblTendered: "Montant Reçu Espèces (DZD) :",
        lblChangeDue: "Monnaie à Rendre :",
        btnCash: "Espèces (P)",
        btnCard: "Carte CIB",
        btnLostTicket: "⚠️ Régularisation Ticket Perdu",
        btnZReport: "Clôture de Caisse (Rapport Z)",
        btnExportAudit: "Exporter CSV",
        auditSearchPlaceholder: "Rechercher par plaque ou reçu...",
        btnTheme: "Mode Jour / Nuit (D)",
        btnLang: "Langue: FR (L)",
        txtShortcuts: "Raccourcis: ",
        btnPrintTicket: "Imprimer Ticket Entrée (T)",
        threatText: "ALERTE SÉCURITÉ: VÉHICULE RECHERCHÉ OU TENTATIVE DE SPOOFING",
        syncOk: "SYNC: À JOUR",
        syncPending: "SYNC: {n} EN ATTENTE",
        syncRunning: "SYNC EN COURS...",
        wsOnline: "PASSERELLE EN LIGNE",
        wsReconnecting: "RECONNEXION...",
        wsOffline: "MODE AUTONOME"
      },
      en: {
        title: "Guard Station & Dedicated POS",
        status: "MODBUS DIRECT ONLINE",
        cam1: "CAM 1: Entry ALPR (Lane 1)",
        cam2: "CAM 2: Biometric Kiosk (Lane 1)",
        cam3: "CAM 3: Exit & Barrier (Lane 2)",
        cam4: "CAM 4: Level 0 Overhead Deck",
        barrier: "EMERGENCY BARRIER OVERRIDE",
        barrierSub: "PRESS SPACEBAR",
        tabPos: "Cashier POS",
        tabScenarios: "Scenarios (1-7)",
        tabTicket: "Thermal Ticket",
        tabAudit: "Logs & Audit",
        lblAuditTitle: "Recent Transactions (Local SQLite)",
        btnExportAudit: "Export CSV",
        auditSearchPlaceholder: "Search by plate or receipt...",
        lblScan: "Scan Barcode / Manual Input (Key S):",
        btnVerify: "Verify Ticket",
        lblPlate: "License Plate:",
        lblDuration: "Elapsed Duration:",
        lblRate: "Applied Tariff:",
        lblTotal: "Amount Due:",
        lblTendered: "Cash Tendered (DZD):",
        lblChangeDue: "Change Due:",
        btnCash: "Cash (P)",
        btnCard: "CIB Card",
        btnLostTicket: "⚠️ Lost Ticket Resolution",
        btnZReport: "End-of-Shift Z-Report",
        btnTheme: "Day / Night Mode (D)",
        btnLang: "Language: EN (L)",
        txtShortcuts: "Shortcuts: ",
        btnPrintTicket: "Print Entry Ticket (T)",
        threatText: "SECURITY ALERT: WATCHLIST MATCH OR SPOOF ATTEMPT",
        syncOk: "SYNC: UP TO DATE",
        syncPending: "SYNC: {n} PENDING",
        syncRunning: "SYNC IN PROGRESS...",
        wsOnline: "GATEWAY ONLINE",
        wsReconnecting: "RECONNECTING...",
        wsOffline: "STANDALONE MODE"
      },
      ar: {
        title: "مركز الحراسة والصندوق المخصص",
        status: "مودبوس مباشر متصل",
        cam1: "كاميرا 1: مدخل لوحات (المسلك 1)",
        cam2: "كاميرا 2: كشك التعرف على الوجه",
        cam3: "كاميرا 3: مخرج وحاجز (المسلك 2)",
        cam4: "كاميرا 4: مراقبة الطابق الأرضي",
        barrier: "فتح الحاجز في حالات الطوارئ",
        barrierSub: "اضغط على زر المسافة (Spacebar)",
        tabPos: "الصندوق POS",
        tabScenarios: "سيناريوهات (1-7)",
        tabTicket: "تذكرة حرارية",
        tabAudit: "السجل والتدقيق",
        lblAuditTitle: "المعاملات الأخيرة (SQLite محلي)",
        btnExportAudit: "تصدير CSV",
        auditSearchPlaceholder: "البحث باللوحة أو الإيصال...",
        lblScan: "مسح الرمز الشريطي / إدخال يدوي (زر S):",
        btnVerify: "تحقق من التذكرة",
        lblPlate: "رقم اللوحة:",
        lblDuration: "مدة الركن:",
        lblRate: "التعريفة المطبقة:",
        lblTotal: "المبلغ المستحق:",
        lblTendered: "المبلغ المستلم نقداً (د.ج):",
        lblChangeDue: "المبلغ المتبقي للإرجاع:",
        btnCash: "نقداً (P)",
        btnCard: "بطاقة CIB",
        btnLostTicket: "⚠️ تسوية تذكرة ضائعة",
        btnZReport: "إغلاق الصندوق (تقرير Z)",
        btnTheme: "وضع النهار / الليل (D)",
        btnLang: "اللغة: العربية (L)",
        txtShortcuts: "اختصارات: ",
        btnPrintTicket: "طباعة تذكرة الدخول (T)",
        threatText: "تنبيه أمني: سيارة مسروقة أو محاولة تزييف بيومتري",
        syncOk: "مزامنة: محدث",
        syncPending: "مزامنة: {n} معلق",
        syncRunning: "جاري المزامنة...",
        wsOnline: "البوابة متصلة",
        wsReconnecting: "جارٍ إعادة الاتصال...",
        wsOffline: "وضع مستقل"
      }
    };

    function applyTranslations() {
      const dict = I18N[currentLang];
      document.getElementById('txtTitle').innerText = dict.title;
      document.getElementById('txtStatus').innerText = dict.status;
      if (document.getElementById('txtWsStatus')) {
        const wsTxt = document.getElementById('txtWsStatus');
        if (typeof gatewayWs !== 'undefined' && gatewayWs && gatewayWs.readyState === WebSocket.OPEN) {
          wsTxt.innerText = dict.wsOnline;
        } else if (typeof gatewayWs !== 'undefined' && gatewayWs && gatewayWs.readyState === WebSocket.CONNECTING) {
          wsTxt.innerText = dict.wsReconnecting;
        } else {
          wsTxt.innerText = dict.wsOffline;
        }
      }
      document.getElementById('lblCam1').innerText = dict.cam1;
      document.getElementById('lblCam2').innerText = dict.cam2;
      document.getElementById('lblCam3').innerText = dict.cam3;
      document.getElementById('lblCam4').innerText = dict.cam4;
      document.getElementById('btnBarrier').children[0].innerText = dict.barrier;
      document.getElementById('btnBarrier').children[1].innerText = dict.barrierSub;
      document.getElementById('tabPos').innerText = dict.tabPos;
      document.getElementById('tabScenarios').innerText = dict.tabScenarios;
      document.getElementById('tabTicket').innerText = dict.tabTicket;
      if (document.getElementById('tabAudit')) document.getElementById('tabAudit').innerText = dict.tabAudit;
      if (document.getElementById('lblAuditTitle')) document.getElementById('lblAuditTitle').innerText = dict.lblAuditTitle;
      if (document.getElementById('btnExportAudit')) document.getElementById('btnExportAudit').innerText = dict.btnExportAudit;
      if (document.getElementById('auditSearchInput')) document.getElementById('auditSearchInput').placeholder = dict.auditSearchPlaceholder;
      document.getElementById('lblScan').innerText = dict.lblScan;
      document.getElementById('btnVerify').innerText = dict.btnVerify;
      document.getElementById('lblPlate').innerText = dict.lblPlate;
      document.getElementById('lblDuration').innerText = dict.lblDuration;
      document.getElementById('lblRate').innerText = dict.lblRate;
      document.getElementById('lblTotal').innerText = dict.lblTotal;
      if (document.getElementById('lblTendered')) document.getElementById('lblTendered').innerText = dict.lblTendered;
      if (document.getElementById('lblChangeDue')) document.getElementById('lblChangeDue').innerText = dict.lblChangeDue;
      document.getElementById('btnCash').innerText = dict.btnCash;
      document.getElementById('btnCard').innerText = dict.btnCard;
      if (document.getElementById('btnLostTicket')) document.getElementById('btnLostTicket').innerText = dict.btnLostTicket;
      document.getElementById('btnZReport').innerText = dict.btnZReport;
      document.getElementById('btnTheme').innerText = dict.btnTheme;
      document.getElementById('btnLang').innerText = dict.btnLang;
      document.getElementById('txtShortcuts').innerText = dict.txtShortcuts;
      document.getElementById('btnPrintTicket').innerText = dict.btnPrintTicket;
      document.getElementById('threatText').innerText = dict.threatText;
      updateSyncBadge();

      document.documentElement.dir = (currentLang === 'ar') ? 'rtl' : 'ltr';
    }

    function cycleLanguage() {
      if (currentLang === 'fr') currentLang = 'en';
      else if (currentLang === 'en') currentLang = 'ar';
      else currentLang = 'fr';
      applyTranslations();
    }

    function toggleTheme() {
      currentTheme = (currentTheme === 'dark') ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', currentTheme);
    }

    function switchTab(tab) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      if (tab === 'pos') {
        document.getElementById('tabPos').classList.add('active');
        document.getElementById('panePos').classList.add('active');
      } else if (tab === 'scenarios') {
        document.getElementById('tabScenarios').classList.add('active');
        document.getElementById('paneScenarios').classList.add('active');
      } else if (tab === 'ticket') {
        document.getElementById('tabTicket').classList.add('active');
        document.getElementById('paneTicket').classList.add('active');
      } else if (tab === 'audit') {
        document.getElementById('tabAudit').classList.add('active');
        document.getElementById('paneAudit').classList.add('active');
        loadAuditData();
      }
    }

    let cachedAuditData = null;

    async function loadAuditData() {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.get_audit_data) {
        try {
          const res = await window.pywebview.api.get_audit_data();
          if (res.success) {
            cachedAuditData = res;
            renderAuditData(res);
          }
        } catch (e) {
          console.error(e);
        }
      }
    }

    function filterAuditTransactions() {
      if (!cachedAuditData) return;
      const q = (document.getElementById('auditSearchInput').value || '').trim().toLowerCase();
      if (!q) {
        renderAuditTxList(cachedAuditData.transactions || []);
        return;
      }
      const filtered = (cachedAuditData.transactions || []).filter(t => {
        const plate = (t.plate_number || '').toLowerCase();
        const receipt = (t.receipt_number || t.id || '').toLowerCase();
        return plate.includes(q) || receipt.includes(q);
      });
      renderAuditTxList(filtered);
    }

    function renderAuditTxList(txs) {
      const txList = document.getElementById('auditTxList');
      if (!txList) return;
      if (!txs || txs.length === 0) {
        txList.innerHTML = '<div style="color:var(--text-muted); font-size:11px;">Aucune transaction correspondante.</div>';
        return;
      }
      txList.innerHTML = txs.map(t => `
        <div style="background:var(--bg-surface-elevated); padding:6px 8px; border-radius:6px; display:flex; justify-content:space-between; align-items:center; border:1px solid var(--border-color);">
          <div>
            <div style="font-weight:bold; font-size:11.5px;">${t.receipt_number || t.id} - ${t.plate_number}</div>
            <div style="font-size:10px; color:var(--text-muted);">${t.exit_time || ''} | ${t.payment_method} | Rendue: ${t.change_dzd || 0} DZD</div>
          </div>
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="font-weight:bold; color:#10B981; font-size:11.5px;">${t.amount_due_dzd} DZD</span>
            <button class="btn-secondary" style="width:auto; padding:2px 6px; font-size:10px;" onclick="reprintTx('${t.id}')">Reçu</button>
          </div>
        </div>
      `).join('');
    }

    function renderAuditData(data) {
      const summary = document.getElementById('auditShiftSummary');
      if (data.shift && summary) {
        summary.innerHTML = `
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px;">
            <div><strong>Agent:</strong> ${data.shift.cashier_name}</div>
            <div><strong>Statut:</strong> <span style="color:#10B981;">${data.shift.status}</span></div>
            <div><strong>Fond de caisse:</strong> ${data.shift.opening_float_dzd} DZD</div>
            <div><strong>Espèces perçues:</strong> ${data.shift.total_cash_dzd} DZD</div>
            <div><strong>Cartes CIB:</strong> ${data.shift.total_card_dzd} DZD</div>
            <div><strong>Total en caisse:</strong> <span style="color:#38BDF8; font-weight:bold;">${data.shift.expected_drawer_dzd} DZD</span></div>
          </div>
        `;
      }

      renderAuditTxList(data.transactions || []);

      const barrierList = document.getElementById('auditBarrierList');
      if (barrierList) {
        if (!data.barrier_logs || data.barrier_logs.length === 0) {
          barrierList.innerHTML = '<div style="color:var(--text-muted); font-size:11px;">Aucun événement barrière récent.</div>';
        } else {
          barrierList.innerHTML = data.barrier_logs.map(b => `
            <div style="background:var(--bg-surface-elevated); padding:3px 6px; border-radius:4px; display:flex; justify-content:space-between; align-items:center;">
              <span>${b.timestamp} | Voie ${b.channel} (${b.duration_ms}ms)</span>
              <span style="color:${b.hardware_success ? '#10B981' : '#EF4444'};">${b.reason} [${b.operator_name}]</span>
            </div>
          `).join('');
        }
      }
    }

    async function updateSyncBadge() {
      const dict = I18N[currentLang] || I18N['fr'];
      const dot = document.getElementById('syncDot');
      const txt = document.getElementById('txtSyncStatus');
      const badge = document.getElementById('syncStatusBadge');

      if (window.pywebview && window.pywebview.api && window.pywebview.api.get_sync_status) {
        try {
          const res = await window.pywebview.api.get_sync_status();
          if (res && res.pending_transactions > 0) {
            if (dot) dot.style.backgroundColor = '#F59E0B';
            if (txt) txt.innerText = dict.syncPending.replace('{n}', res.pending_transactions);
            if (badge) badge.style.color = '#F59E0B';
          } else {
            if (dot) dot.style.backgroundColor = '#10B981';
            if (txt) txt.innerText = dict.syncOk;
            if (badge) badge.style.color = '#10B981';
          }
        } catch (e) {
          console.error(e);
        }
      } else {
        if (dot) dot.style.backgroundColor = '#10B981';
        if (txt) txt.innerText = dict.syncOk;
      }
    }

    async function triggerManualSync() {
      const dict = I18N[currentLang] || I18N['fr'];
      const txt = document.getElementById('txtSyncStatus');
      if (txt) txt.innerText = dict.syncRunning;

      if (window.pywebview && window.pywebview.api && window.pywebview.api.sync_offline_buffer) {
        try {
          const res = await window.pywebview.api.sync_offline_buffer();
          alert(res.message);
          updateSyncBadge();
        } catch (e) {
          alert("Erreur lors de la synchronisation: " + e);
          updateSyncBadge();
        }
      } else {
        alert("Synchronisation simulée avec la passerelle locale.");
        updateSyncBadge();
      }
    }

    async function exportAuditData() {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.export_shift_csv) {
        const res = await window.pywebview.api.export_shift_csv();
        if (res.success) {
          alert(res.message);
        } else {
          alert("Erreur lors de l'export: " + (res.error || res.message));
        }
      } else {
        alert("Export CSV simulé (Fichier généré dans data/exports).");
      }
    }

    async function reprintTx(txId) {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.reprint_receipt) {
        const res = await window.pywebview.api.reprint_receipt(txId);
        if (res.success) {
          alert("Duplicata imprimé : " + res.receipt_number);
        } else {
          alert("Erreur : " + res.message);
        }
      }
    }

    async function triggerManualBarrier() {
      if (window.openExitBarrier) window.openExitBarrier();
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.trigger_barrier(1, 500);
      }
      const st = document.getElementById('gateStatus');
      if (st) {
        st.innerText = "BARRIÈRE: OUVERTE (IMPULSION)";
        st.style.color = "#10B981";
        setTimeout(() => {
          st.innerText = "BARRIÈRE: FERMÉE";
          st.style.color = "#38BDF8";
        }, 3000);
      }
    }

    async function triggerScenario(key) {
      if (key === 'watchlist_alert' || key === 'spoof_attack' || key === 'clone_dispute') {
        showThreat(key);
      } else if (key === 'driver_mismatch') {
        document.getElementById('triageModal').style.display = 'flex';
      }

      if (key === 'spoof_attack') {
        if (window.triggerFaceScan) window.triggerFaceScan(true);
      } else if (key === 'driver_mismatch') {
        if (window.triggerFaceScan) window.triggerFaceScan(false);
      } else if (key === 'vip_entry' || key === 'temporary_00') {
        if (window.triggerEntryCar) window.triggerEntryCar('104822 119 16');
      } else if (key === 'visitor_payment_exit') {
        if (window.openExitBarrier) window.openExitBarrier();
      }

      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.simulate_scenario(key);
      }
    }

    function showThreat(type) {
      const banner = document.getElementById('threatBanner');
      banner.style.display = 'flex';
      document.getElementById('tileCam1').classList.add('active-threat');
    }

    function dismissThreat() {
      document.getElementById('threatBanner').style.display = 'none';
      document.getElementById('tileCam1').classList.remove('active-threat');
    }

    async function executeScan() {
      const input = document.getElementById('barcodeInput');
      const val = input.value.trim() || "9910010482218";
      let res;
      if (window.pywebview && window.pywebview.api) {
        res = await window.pywebview.api.scan_ticket(val);
      } else {
        // Direct browser mock
        res = {
          is_valid: true,
          plate_snippet: "104822",
          elapsed_minutes: 115,
          total_due_dzd: 200.0,
          is_grace_period: false
        };
      }
      currentScanData = res;
      if (res.plate_snippet && window.setCam3Plate) {
        window.setCam3Plate(res.plate_snippet);
      }
      document.getElementById('valPlate').innerText = res.plate_snippet || "104822 119 16";
      document.getElementById('valDuration').innerText = res.elapsed_minutes + " min";
      if (res.is_grace_period) {
        document.getElementById('valTotal').innerText = "0 DZD (Franchise 15 min)";
      } else {
        document.getElementById('valTotal').innerText = res.total_due_dzd.toFixed(0) + " DZD";
      }
      if (document.getElementById('tenderedAmountInput')) {
        document.getElementById('tenderedAmountInput').value = res.total_due_dzd > 0 ? res.total_due_dzd.toFixed(0) : "200";
        calculateChangeDue();
      }
      document.getElementById('scanResultCard').style.display = 'block';
    }

    function calculateChangeDue() {
      const input = document.getElementById('tenderedAmountInput');
      const tendered = parseFloat(input ? input.value : 0) || 0;
      const total = (currentScanData && currentScanData.total_due_dzd) ? currentScanData.total_due_dzd : 0;
      const change = Math.max(0, tendered - total);
      const chgElem = document.getElementById('valChangeDue');
      if (chgElem) chgElem.innerText = change.toFixed(0) + " DZD";
      return { tendered, change };
    }

    function setTenderedAmount(val) {
      const input = document.getElementById('tenderedAmountInput');
      if (input) {
        input.value = val;
        calculateChangeDue();
      }
    }

    function handleBarcodeEnter(e) {
      if (e.key === 'Enter') {
        executeScan();
      }
    }

    async function processPayment(method) {
      if (!currentScanData) return;
      const ticketId = (currentScanData && currentScanData.ticket_id) ? currentScanData.ticket_id : "TKT-CURRENT";
      const totalDue = currentScanData.total_due_dzd || 0;
      let tendered = totalDue;
      if (method === 'CASH') {
        const inp = document.getElementById('tenderedAmountInput');
        if (inp && inp.value) {
          const val = parseFloat(inp.value);
          if (!isNaN(val) && val >= totalDue) {
            tendered = val;
          }
        }
      }
      if (window.openExitBarrier) window.openExitBarrier();
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.settle_payment(
          ticketId,
          currentScanData.plate_snippet,
          totalDue,
          method,
          tendered
        );
      }
      const chgMsg = (method === 'CASH' && tendered > totalDue) ? (" | Monnaie: " + (tendered - totalDue).toFixed(0) + " DZD") : "";
      alert("Paiement enregistré avec succès (" + method + chgMsg + "). La barrière de sortie est ouverte.");
      document.getElementById('scanResultCard').style.display = 'none';
      document.getElementById('barcodeInput').value = '';
      if (document.getElementById('tenderedAmountInput')) document.getElementById('tenderedAmountInput').value = '';
      updateSyncBadge();
    }

    async function printManualTicket() {
      const plate = document.getElementById('manualPlateInput').value.trim() || "08412 00 16";
      if (window.triggerEntryCar) window.triggerEntryCar(plate);
      let res;
      if (window.pywebview && window.pywebview.api) {
        res = await window.pywebview.api.print_ticket(plate, "LANE-01");
        if (res.svg_preview) {
          document.getElementById('ticketPreviewArea').innerHTML = res.svg_preview;
        }
      } else {
        alert("Impression ticket simulée pour plaque: " + plate);
      }
    }

    function showLostTicketModal() {
      document.getElementById('lostTicketModal').style.display = 'flex';
    }

    function closeLostTicketModal() {
      document.getElementById('lostTicketModal').style.display = 'none';
    }

    async function submitLostTicket() {
      const plate = document.getElementById('lostPlateInput').value.trim() || '104822 119 16';
      const flat = document.getElementById('lostFlatRateCheck').checked;
      const pmr = document.getElementById('lostPmrCheck').checked;
      closeLostTicketModal();

      let res;
      if (window.pywebview && window.pywebview.api) {
        res = await window.pywebview.api.issue_lost_ticket(plate, flat, pmr);
      } else {
        res = {
          success: true,
          ticket_id: "TKT-LOST-2026",
          barcode_value: "9910010482218",
          plate_number: plate,
          total_due_dzd: flat ? (pmr ? 750.0 : 1500.0) : (pmr ? 325.0 : 650.0),
          breakdown: "Forfait Ticket Perdu",
          message: "Ticket de remplacement généré.",
        };
      }

      if (res && res.success) {
        currentScanData = {
          is_valid: true,
          ticket_id: res.ticket_id,
          plate_snippet: res.plate_number,
          total_due_dzd: res.total_due_dzd,
          elapsed_minutes: 120,
        };
        switchTab('pos');
        document.getElementById('valPlate').innerText = res.plate_number;
        document.getElementById('valDuration').innerText = "RÉGULARISATION";
        document.getElementById('valRate').innerText = res.breakdown || "Forfait Ticket Perdu";
        document.getElementById('valTotal').innerText = res.total_due_dzd.toFixed(0) + " DZD";
        if (document.getElementById('tenderedAmountInput')) {
          document.getElementById('tenderedAmountInput').value = res.total_due_dzd;
          calculateChangeDue();
        }
        document.getElementById('scanResultCard').style.display = 'block';
        if (res.svg_preview && document.getElementById('ticketPreviewArea')) {
          document.getElementById('ticketPreviewArea').innerHTML = res.svg_preview;
        }
      }
    }

    let currentExpectedDrawer = 0;

    async function closeShiftZReport() {
      if (window.pywebview && window.pywebview.api) {
        try {
          const data = await window.pywebview.api.get_audit_data();
          if (data && data.shift) {
            currentExpectedDrawer = data.shift.expected_drawer_dzd || 0;
            document.getElementById('valExpectedDrawerCash').innerText = currentExpectedDrawer.toFixed(0) + " DZD";
          }
        } catch(e) {}
      }
      document.getElementById('zReportModal').style.display = 'flex';
      updatePhysicalCashCount();
    }

    function closeZReportModal() {
      document.getElementById('zReportModal').style.display = 'none';
    }

    function updatePhysicalCashCount() {
      const c2000 = parseInt(document.getElementById('denom2000').value) || 0;
      const c1000 = parseInt(document.getElementById('denom1000').value) || 0;
      const c500 = parseInt(document.getElementById('denom500').value) || 0;
      const c200 = parseInt(document.getElementById('denom200').value) || 0;
      const c100 = parseInt(document.getElementById('denom100').value) || 0;
      const c50 = parseInt(document.getElementById('denom50').value) || 0;

      const total = (c2000 * 2000) + (c1000 * 1000) + (c500 * 500) + (c200 * 200) + (c100 * 100) + (c50 * 50);
      document.getElementById('valPhysicalCashCounted').innerText = total.toFixed(0) + " DZD";

      const diff = total - currentExpectedDrawer;
      const diffElem = document.getElementById('valCashVariance');
      if (diff === 0) {
        diffElem.innerText = "0 DZD (Parfait)";
        diffElem.style.color = "#10B981";
      } else if (diff > 0) {
        diffElem.innerText = "+" + diff.toFixed(0) + " DZD (Excédent)";
        diffElem.style.color = "#38BDF8";
      } else {
        diffElem.innerText = diff.toFixed(0) + " DZD (Déficit)";
        diffElem.style.color = "#EF4444";
      }
    }

    async function submitZReportFinal() {
      closeZReportModal();
      const denominationCounts = {
        "2000": parseInt(document.getElementById('denom2000').value) || 0,
        "1000": parseInt(document.getElementById('denom1000').value) || 0,
        "500": parseInt(document.getElementById('denom500').value) || 0,
        "200": parseInt(document.getElementById('denom200').value) || 0,
        "100": parseInt(document.getElementById('denom100').value) || 0,
        "50": parseInt(document.getElementById('denom50').value) || 0,
      };

      let rep;
      if (window.pywebview && window.pywebview.api) {
        rep = await window.pywebview.api.close_shift(denominationCounts);
        const varMsg = rep.cash_variance_dzd !== undefined ? ("\\nÉcart de caisse: " + rep.cash_variance_dzd + " DZD (" + rep.variance_status + ")") : "";
        alert("RAPPORT Z GÉNÉRÉ AVEC SUCCÈS:\\n" +
              "Recettes Espèces: " + rep.total_cash_revenue_dzd + " DZD\\n" +
              "Recettes Carte: " + rep.total_card_revenue_dzd + " DZD\\n" +
              "Total Encaissé: " + rep.total_revenue_dzd + " DZD\\n" +
              "Espèces Physiques: " + rep.physical_cash_counted_dzd + " DZD" + varMsg + "\\n" +
              "Hash d'audit: " + rep.audit_hash);
      } else {
        alert("Clôture de shift Z-Report effectuée.");
      }
      updateSyncBadge();
      refreshAuditData();
    }

    async function resolveTriage(decision) {
      document.getElementById('triageModal').style.display = 'none';
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.guard_decision("104822 119 16", decision, "Avis opérateur poste");
      }
    }

    /* Global USB Barcode Gun Hardware Wedge Listener */
    let barcodeGunBuffer = "";
    let lastGunKeyTimestamp = 0;

    /* Global Physical Keyboard Shortcuts & Scanner Trap */
    window.addEventListener('keydown', (e) => {
      const now = Date.now();
      const timeDelta = now - lastGunKeyTimestamp;
      lastGunKeyTimestamp = now;

      // Handle barcode scanner burst finishing with Enter
      if (e.key === 'Enter') {
        if (barcodeGunBuffer.length >= 8) {
          e.preventDefault();
          const scannedCode = barcodeGunBuffer;
          barcodeGunBuffer = "";
          switchTab('pos');
          document.getElementById('barcodeInput').value = scannedCode;
          executeScan();
          return;
        }
        barcodeGunBuffer = "";
      } else if (e.key.length === 1 && !e.ctrlKey && !e.altKey && !e.metaKey) {
        // Hardware barcode guns type characters with <50ms inter-character interval
        if (timeDelta > 65) {
          barcodeGunBuffer = "";
        }
        barcodeGunBuffer += e.key;
      }

      // Spacebar: Instant Barrier Override
      if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
        e.preventDefault();
        triggerManualBarrier();
      }
      // Esc: Dismiss Threat Banner & Modals
      else if (e.key === 'Escape') {
        dismissThreat();
        document.getElementById('triageModal').style.display = 'none';
      }
      // Numbers 1-7: Trigger Scenarios
      else if (e.key >= '1' && e.key <= '7' && e.target.tagName !== 'INPUT') {
        const scenarios = [
          'vip_entry', 'temporary_00', 'watchlist_alert',
          'spoof_attack', 'driver_mismatch', 'visitor_payment_exit', 'clone_dispute'
        ];
        triggerScenario(scenarios[parseInt(e.key) - 1]);
      }
      // Key T: Print Manual Ticket
      else if ((e.key === 't' || e.key === 'T') && e.target.tagName !== 'INPUT') {
        switchTab('ticket');
        printManualTicket();
      }
      // Key S: Focus Barcode Scanner Input
      else if ((e.key === 's' || e.key === 'S') && e.target.tagName !== 'INPUT') {
        e.preventDefault();
        switchTab('pos');
        document.getElementById('barcodeInput').focus();
      }
      // Key P: Quick Cash Settlement
      else if ((e.key === 'p' || e.key === 'P') && e.target.tagName !== 'INPUT') {
        if (currentScanData) processPayment('CASH');
      }
      // Key D: Toggle Day / Night
      else if ((e.key === 'd' || e.key === 'D') && e.target.tagName !== 'INPUT') {
        toggleTheme();
      }
      // Key L: Cycle Language
      else if ((e.key === 'l' || e.key === 'L') && e.target.tagName !== 'INPUT') {
        cycleLanguage();
      }
    });

    /* =========================================================================
       HIGH-FIDELITY REAL-TIME 4-CHANNEL CCTV SIMULATION PIPELINE
       ========================================================================= */

    function drawCCTVLensOverlay(ctx, w, h, camCode, camTitle, fps, isRec) {
      if (isRec === undefined) isRec = true;
      // 1. Scanlines
      ctx.fillStyle = (currentTheme === 'light') ? 'rgba(15, 23, 42, 0.025)' : 'rgba(0, 0, 0, 0.16)';
      for (let y = 0; y < h; y += 3) {
        ctx.fillRect(0, y, w, 1);
      }
      // 2. Optical Security Lens Vignette
      const vig = ctx.createRadialGradient(w/2, h/2, h*0.4, w/2, h/2, w*0.75);
      vig.addColorStop(0, 'rgba(0,0,0,0)');
      vig.addColorStop(1, (currentTheme === 'light') ? 'rgba(15,23,42,0.12)' : 'rgba(2,6,18,0.65)');
      ctx.fillStyle = vig;
      ctx.fillRect(0, 0, w, h);

      // 3. Header OSD Bar
      ctx.fillStyle = (currentTheme === 'light') ? 'rgba(248, 250, 252, 0.92)' : 'rgba(4, 8, 20, 0.88)';
      ctx.fillRect(0, 0, w, 20);
      ctx.strokeStyle = (currentTheme === 'light') ? 'rgba(203, 213, 225, 0.8)' : 'rgba(30, 41, 59, 0.8)';
      ctx.beginPath(); ctx.moveTo(0, 20); ctx.lineTo(w, 20); ctx.stroke();

      // Blinking REC Indicator
      const blink = Math.floor(Date.now() / 600) % 2 === 0;
      if (isRec && blink) {
        ctx.fillStyle = '#EF4444';
        ctx.beginPath(); ctx.arc(10, 10, 3, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#EF4444';
        ctx.font = 'bold 8px monospace';
        ctx.fillText('REC', 17, 13);
      } else {
        ctx.fillStyle = '#94A3B8';
        ctx.font = 'bold 8px monospace';
        ctx.fillText('STBY', 10, 13);
      }

      ctx.fillStyle = (currentTheme === 'light') ? '#0F172A' : '#F1F5F9';
      ctx.font = 'bold 8.5px monospace';
      ctx.fillText(camCode + ' [' + camTitle + ']', 44, 13);

      // Real-time timecode
      ctx.fillStyle = '#38BDF8';
      ctx.textAlign = 'right';
      const nowStr = new Date().toLocaleTimeString('fr-FR');
      ctx.fillText(nowStr + ' UTC+1', w - 8, 13);
      ctx.textAlign = 'left';
    }

    // --- CAM 1 : ENTRÉE ALPR & KINÉMATIQUE VÉHICULE ---
    let cam1ArmAngle = 0.0;
    let cam1TargetArmAngle = 0.0;
    let cam1CarState = 'STOPPED';
    let cam1CarY = 120.0;
    let cam1Plate = '104822 119 16';

    window.triggerEntryCar = function(plate) {
      if (plate) cam1Plate = plate;
      cam1TargetArmAngle = 88.0;
      cam1CarState = 'DEPARTING';
      const pill = document.getElementById('cam1ArmPill');
      if (pill) { pill.innerText = 'ACCÈS AUTORISÉ'; pill.style.color = '#10B981'; }
    };

    function initCam1() {
      const cvs = document.getElementById('cam1Canvas');
      if (!cvs) return;
      const ctx = cvs.getContext('2d');
      const w = cvs.width, h = cvs.height;

      function render() {
        cam1ArmAngle += (cam1TargetArmAngle - cam1ArmAngle) * 0.12;

        if (cam1CarState === 'APPROACHING') {
          cam1CarY += 1.8;
          if (cam1CarY >= 120) {
            cam1CarY = 120;
            cam1CarState = 'STOPPED';
          }
        } else if (cam1CarState === 'DEPARTING') {
          cam1CarY += 2.6;
          if (cam1CarY > h + 80) {
            cam1CarState = 'APPROACHING';
            cam1CarY = -60;
            cam1TargetArmAngle = 0.0;
            const pill = document.getElementById('cam1ArmPill');
            if (pill) { pill.innerText = '1080p @ 30fps'; pill.style.color = 'var(--text-muted)'; }
          }
        }

        ctx.clearRect(0, 0, w, h);

        // Asphalt roadway
        ctx.fillStyle = '#0B132B';
        ctx.fillRect(0, 0, w, h);
        ctx.fillStyle = '#1C2541';
        ctx.beginPath();
        ctx.moveTo(0, 180); ctx.lineTo(160, 90); ctx.lineTo(240, 90); ctx.lineTo(400, 180); ctx.lineTo(400, h); ctx.lineTo(0, h);
        ctx.closePath(); ctx.fill();

        // Central dashed road marker
        ctx.strokeStyle = '#F59E0B';
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 8]);
        ctx.beginPath();
        ctx.moveTo(200, 90); ctx.lineTo(200, h);
        ctx.stroke();
        ctx.setLineDash([]);

        // Stop line
        ctx.fillStyle = '#F59E0B';
        ctx.fillRect(110, 175, 180, 4);

        // Entry Totem (Left)
        ctx.fillStyle = '#1E293B';
        ctx.fillRect(70, 130, 24, 60);
        ctx.strokeStyle = '#0284C7';
        ctx.lineWidth = 1;
        ctx.strokeRect(70, 130, 24, 60);
        ctx.fillStyle = '#10B981';
        ctx.fillRect(74, 140, 16, 8);

        // Barrier Cabinet (Right)
        ctx.fillStyle = '#EA580C';
        ctx.fillRect(295, 140, 20, 50);
        ctx.strokeStyle = '#9A3412';
        ctx.strokeRect(295, 140, 20, 50);

        // Car Body
        const cx = 130, cy = cam1CarY, cw = 140, ch = 70;
        ctx.fillStyle = '#1E293B';
        ctx.beginPath();
        ctx.roundRect(cx, cy, cw, ch, 8);
        ctx.fill();
        ctx.strokeStyle = '#38BDF8';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Windshield
        ctx.fillStyle = '#0F172A';
        ctx.beginPath();
        ctx.roundRect(cx + 15, cy + 10, cw - 30, 20, 4);
        ctx.fill();

        // Headlights
        ctx.fillStyle = '#FEF08A';
        ctx.beginPath(); ctx.arc(cx + 18, cy + ch - 8, 5, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.arc(cx + cw - 18, cy + ch - 8, 5, 0, Math.PI * 2); ctx.fill();

        // Front Plate
        const px = cx + 25, py = cy + 42, pw = 90, ph = 18;
        ctx.fillStyle = '#FDE047';
        ctx.fillRect(px, py, pw, ph);
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 1;
        ctx.strokeRect(px, py, pw, ph);
        ctx.fillStyle = '#000';
        ctx.font = 'bold 9px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(cam1Plate, px + pw/2, py + 12);
        ctx.textAlign = 'left';

        // ALPR OCR Reticle
        ctx.strokeStyle = '#10B981';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 2]);
        ctx.strokeRect(px - 3, py - 3, pw + 6, ph + 6);
        ctx.setLineDash([]);
        ctx.fillStyle = 'rgba(16, 185, 129, 0.9)';
        ctx.fillRect(px - 3, py - 12, 96, 9);
        ctx.fillStyle = '#000';
        ctx.font = 'bold 7px monospace';
        ctx.fillText('OCR: 98.4% [ALGER]', px, py - 5);

        // Barrier Boom Arm
        ctx.save();
        ctx.translate(295, 150);
        ctx.rotate((-cam1ArmAngle * Math.PI) / 180);
        ctx.fillStyle = '#F8FAFC';
        ctx.fillRect(-170, -3, 170, 6);
        ctx.fillStyle = '#EF4444';
        for (let s = -160; s < 0; s += 25) {
          ctx.fillRect(s, -3, 12, 6);
        }
        ctx.restore();

        drawCCTVLensOverlay(ctx, w, h, 'CAM-01', 'ENTRÉE ALPR VOIE 1', 25.0);
        requestAnimationFrame(render);
      }
      render();
    }

    // --- CAM 2 : KIOSQUE BIOMÉTRIQUE & CANAL NIR 850nm ---
    let cam2SpoofMode = false;
    let cam2Frame = 0;
    let cam2PulsePhase = 0.0;

    window.triggerFaceScan = function(isSpoof) {
      cam2SpoofMode = Boolean(isSpoof);
      const pill = document.getElementById('cam2NirPill');
      const dist = document.getElementById('cam2Dist');
      if (pill) {
        pill.innerText = cam2SpoofMode ? 'SPOOF DÉTECTÉ' : 'VIVACITÉ OK';
        pill.style.color = cam2SpoofMode ? '#EF4444' : '#10B981';
      }
      if (dist) {
        dist.innerText = cam2SpoofMode ? 'SCORE VIVACITÉ: 0.124' : 'SCORE MATCH: 0.985';
      }
      setTimeout(() => {
        cam2SpoofMode = false;
        if (pill) { pill.innerText = 'RGB + NIR 850nm'; pill.style.color = 'var(--text-muted)'; }
        if (dist) { dist.innerText = 'DISTANCE: 0.418'; }
      }, 7000);
    };

    function initCam2() {
      const cvs = document.getElementById('cam2Canvas');
      if (!cvs) return;
      const ctx = cvs.getContext('2d');
      const w = cvs.width, h = cvs.height;

      function render() {
        cam2Frame++;
        cam2PulsePhase += 0.08;

        ctx.clearRect(0, 0, w, h);

        // Vehicle Cabin Background
        ctx.fillStyle = '#090D16';
        ctx.fillRect(0, 0, w, h);

        // Driver Window Frame
        ctx.fillStyle = '#1E293B';
        ctx.beginPath();
        ctx.moveTo(0, 0); ctx.lineTo(50, 0); ctx.lineTo(70, h); ctx.lineTo(0, h);
        ctx.closePath(); ctx.fill();

        // Kiosk Column
        ctx.fillStyle = '#111827';
        ctx.fillRect(w - 60, 0, 60, h);
        ctx.strokeStyle = '#0284C7';
        ctx.lineWidth = 1;
        ctx.strokeRect(w - 60, 0, 60, h);

        // Driver Head Silhouette
        const headX = 180, headY = 110;
        const isBlinking = (cam2Frame % 180) < 6;
        const breathY = Math.sin(cam2Frame * 0.04) * 1.5;

        ctx.fillStyle = '#334155';
        ctx.beginPath();
        ctx.ellipse(headX, headY + breathY, 38, 48, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#38BDF8';
        ctx.lineWidth = 1.2;
        ctx.stroke();

        // Eyes
        ctx.fillStyle = '#38BDF8';
        if (isBlinking) {
          ctx.lineWidth = 1.5;
          ctx.beginPath(); ctx.moveTo(headX - 18, headY - 6 + breathY); ctx.lineTo(headX - 6, headY - 6 + breathY); ctx.stroke();
          ctx.beginPath(); ctx.moveTo(headX + 6, headY - 6 + breathY); ctx.lineTo(headX + 18, headY - 6 + breathY); ctx.stroke();
        } else {
          ctx.beginPath(); ctx.arc(headX - 12, headY - 6 + breathY, 3.5, 0, Math.PI * 2); ctx.fill();
          ctx.beginPath(); ctx.arc(headX + 12, headY - 6 + breathY, 3.5, 0, Math.PI * 2); ctx.fill();
        }

        // Nose Bridge
        ctx.strokeStyle = '#38BDF8';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(headX, headY - 4 + breathY); ctx.lineTo(headX, headY + 8 + breathY); ctx.lineTo(headX - 4, headY + 11 + breathY);
        ctx.stroke();

        // Mouth
        ctx.beginPath();
        ctx.arc(headX, headY + 20 + breathY, 8, 0.2, Math.PI - 0.2);
        ctx.stroke();

        // 68-Point Landmark Mesh Overlay
        ctx.fillStyle = '#00F2FE';
        const landmarks = [
          [-28, -20], [-18, -22], [-8, -20], [8, -20], [18, -22], [28, -20],
          [-22, -6], [-12, -8], [-2, -6], [2, -6], [12, -8], [22, -6],
          [0, 0], [0, 6], [-5, 12], [0, 13], [5, 12],
          [-12, 20], [0, 18], [12, 20], [0, 24],
          [-30, 0], [-26, 20], [-18, 36], [0, 44], [18, 36], [26, 20], [30, 0]
        ];
        landmarks.forEach(pt => {
          ctx.beginPath();
          ctx.arc(headX + pt[0], headY + pt[1] + breathY, 1.3, 0, Math.PI * 2);
          ctx.fill();
        });

        // Biometric Box
        const boxColor = cam2SpoofMode ? '#EF4444' : '#10B981';
        ctx.strokeStyle = boxColor;
        ctx.lineWidth = 1.5;
        ctx.strokeRect(headX - 50, headY - 60 + breathY, 100, 120);

        ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
        ctx.fillRect(headX - 50, headY - 76 + breathY, 100, 14);
        ctx.fillStyle = boxColor;
        ctx.font = 'bold 7.5px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(cam2SpoofMode ? 'SPOOF DÉTECTÉ (2D)' : 'ARCFACE: MATCH 0.985', headX, headY - 66 + breathY);
        ctx.textAlign = 'left';

        // PIP Viewport: 850nm NIR Infrared Channel
        const pipX = w - 110, pipY = 24, pipW = 95, pipH = 65;
        ctx.fillStyle = '#020617';
        ctx.fillRect(pipX, pipY, pipW, pipH);
        ctx.strokeStyle = cam2SpoofMode ? '#EF4444' : '#06B6D4';
        ctx.lineWidth = 1.2;
        ctx.strokeRect(pipX, pipY, pipW, pipH);

        ctx.fillStyle = cam2SpoofMode ? '#EF4444' : '#06B6D4';
        ctx.font = 'bold 7px monospace';
        ctx.fillText('NIR 850nm CANAL', pipX + 4, pipY + 10);

        if (!cam2SpoofMode) {
          const nirGrad = ctx.createRadialGradient(pipX + pipW/2, pipY + 38, 2, pipX + pipW/2, pipY + 38, 16);
          nirGrad.addColorStop(0, '#CBD5E1');
          nirGrad.addColorStop(0.7, '#64748B');
          nirGrad.addColorStop(1, '#1E293B');
          ctx.fillStyle = nirGrad;
          ctx.beginPath(); ctx.arc(pipX + pipW/2, pipY + 38, 16, 0, Math.PI * 2); ctx.fill();
          ctx.fillStyle = '#FFF';
          ctx.fillRect(pipX + pipW/2 - 6, pipY + 35, 2, 2);
          ctx.fillRect(pipX + pipW/2 + 4, pipY + 35, 2, 2);
          ctx.fillStyle = '#10B981';
          ctx.font = 'bold 6.5px monospace';
          ctx.fillText('DIFFUSION DERMIQUE OK', pipX + 4, pipY + pipH - 4);
        } else {
          ctx.fillStyle = '#F8FAFC';
          ctx.fillRect(pipX + 18, pipY + 18, 60, 32);
          ctx.fillStyle = '#EF4444';
          ctx.font = 'bold 6.5px monospace';
          ctx.fillText('REFLET VERRE COMPACT', pipX + 4, pipY + pipH - 4);
        }

        // Bottom rPPG Heart Waveform
        ctx.strokeStyle = '#10B981';
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        for (let x = 80; x < w - 80; x += 3) {
          const y = h - 26 + Math.sin((x * 0.08) - cam2PulsePhase) * 4 * (Math.sin(x * 0.02) > 0.3 ? 2 : 0.5);
          if (x === 80) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();

        drawCCTVLensOverlay(ctx, w, h, 'CAM-02', 'BORNE BIOMÉTRIQUE', 25.0);
        requestAnimationFrame(render);
      }
      render();
    }

    // --- CAM 3 : VOIE 2 SORTIE & BARRIÈRE MODBUS AVEC CINÉMATIQUE 5-PHASES ---
    let cam3ArmAngle = 0.0;
    let cam3TargetAngle = 0.0;
    let cam3CarState = 'APPROACHING';
    let cam3CarX = -120.0;
    let cam3CarSpeed = 2.8;
    let cam3WheelAngle = 0.0;
    let cam3StopFrames = 0;
    let cam3ClearFrames = 0;
    let cam3Plate = '08192 120 09';
    let cam3Frame = 0;

    window.setCam3Plate = function(plate) {
      if (plate) cam3Plate = plate;
    };

    window.openExitBarrier = function() {
      cam3TargetAngle = 88.0;
      const st = document.getElementById('gateStatus');
      const pill = document.getElementById('cam3ArmPill');
      const loop = document.getElementById('cam3LoopStatus');
      if (st) { st.innerText = 'BARRIÈRE: OUVERTE (88°)'; st.style.color = '#10B981'; }
      if (pill) { pill.innerText = 'LEVÉE (OUVERT)'; pill.style.color = '#10B981'; }
      if (loop) { loop.innerText = 'BOUCLE INDUCTIVE: PASSAGE (42 km/h)'; loop.style.color = '#10B981'; }

      if (cam3CarState === 'STOPPED' || cam3CarState === 'APPROACHING') {
        cam3CarState = 'OPENING';
      }
    };

    function initCam3() {
      const cvs = document.getElementById('cam3Canvas');
      if (!cvs) return;
      const ctx = cvs.getContext('2d');
      const w = cvs.width, h = cvs.height;

      function render() {
        cam3Frame++;
        cam3ArmAngle += (cam3TargetAngle - cam3ArmAngle) * 0.09;

        // Kinematic State Machine
        if (cam3CarState === 'APPROACHING') {
          cam3TargetAngle = 0.0;
          const dist = 60 - cam3CarX;
          if (dist > 0.6) {
            cam3CarSpeed = Math.min(2.8, Math.max(0.12, dist * 0.038));
            cam3CarX += cam3CarSpeed;
            cam3WheelAngle += cam3CarSpeed / 12.0;
          } else {
            cam3CarX = 60;
            cam3CarSpeed = 0.0;
            cam3CarState = 'STOPPED';
            cam3StopFrames = 0;
          }
        } else if (cam3CarState === 'STOPPED') {
          cam3CarSpeed = 0.0;
          cam3StopFrames++;
          if (cam3StopFrames > 350) {
            cam3TargetAngle = 88.0;
            cam3CarState = 'OPENING';
          }
        } else if (cam3CarState === 'OPENING') {
          cam3TargetAngle = 88.0;
          if (cam3ArmAngle > 45) {
            cam3CarState = 'DEPARTING';
            cam3CarSpeed = 0.5;
          }
        } else if (cam3CarState === 'DEPARTING') {
          cam3TargetAngle = 88.0;
          if (cam3CarSpeed < 3.8) cam3CarSpeed += 0.05;
          cam3CarX += cam3CarSpeed;
          cam3WheelAngle += cam3CarSpeed / 12.0;

          if (cam3CarX > w + 120) {
            cam3CarState = 'LANE_CLEAR';
            cam3ClearFrames = 0;
            cam3TargetAngle = 0.0;
            const st = document.getElementById('gateStatus');
            const pill = document.getElementById('cam3ArmPill');
            const loop = document.getElementById('cam3LoopStatus');
            if (st) { st.innerText = 'BARRIÈRE: FERMÉE'; st.style.color = '#38BDF8'; }
            if (pill) { pill.innerText = 'BARRIÈRE: FERMÉE'; pill.style.color = 'var(--text-muted)'; }
            if (loop) { loop.innerText = 'BOUCLE INDUCTIVE: ACTIVE'; loop.style.color = '#38BDF8'; }
          }
        } else if (cam3CarState === 'LANE_CLEAR') {
          cam3TargetAngle = 0.0;
          cam3ClearFrames++;
          if (cam3ClearFrames > 90) {
            cam3CarX = -130;
            cam3CarSpeed = 2.8;
            cam3CarState = 'APPROACHING';
            const plates = ['08192 120 09', '104822 119 16', '04122 118 16', '08412 00 16'];
            cam3Plate = plates[Math.floor(Math.random() * plates.length)];
          }
        }

        ctx.clearRect(0, 0, w, h);

        // Sky & Facade
        ctx.fillStyle = '#0B132B';
        ctx.fillRect(0, 0, w, 70);

        // Roadway
        const roadGrad = ctx.createLinearGradient(0, 70, 0, h);
        roadGrad.addColorStop(0, '#1E293B');
        roadGrad.addColorStop(1, '#0F172A');
        ctx.fillStyle = roadGrad;
        ctx.fillRect(0, 70, w, h - 70);

        // Curb Lines
        ctx.strokeStyle = '#F59E0B';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, 85); ctx.lineTo(w, 85);
        ctx.stroke();

        // Inductive loop markings
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([5, 5]);
        ctx.strokeRect(180, 115, 90, 60);
        ctx.setLineDash([]);
        ctx.fillStyle = 'rgba(56, 189, 248, 0.6)';
        ctx.font = 'bold 7px monospace';
        ctx.fillText('BOUCLE DÉTECTION SAS', 184, 110);

        // Car Body
        const cx = cam3CarX, cy = 100, cw = 110, ch = 52;
        ctx.fillStyle = '#1E293B';
        ctx.beginPath();
        ctx.roundRect(cx, cy, cw, ch, 6);
        ctx.fill();
        ctx.strokeStyle = '#38BDF8';
        ctx.lineWidth = 1.2;
        ctx.stroke();

        // Wheels
        function drawWheel(wx, wy) {
          ctx.fillStyle = '#020617';
          ctx.beginPath(); ctx.arc(wx, wy, 11, 0, Math.PI * 2); ctx.fill();
          ctx.strokeStyle = '#64748B'; ctx.lineWidth = 2; ctx.stroke();
          ctx.save();
          ctx.translate(wx, wy);
          ctx.rotate(cam3WheelAngle);
          ctx.strokeStyle = '#94A3B8'; ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(-9, 0); ctx.lineTo(9, 0);
          ctx.moveTo(0, -9); ctx.lineTo(0, 9);
          ctx.stroke();
          ctx.restore();
        }
        drawWheel(cx + 25, cy + ch);
        drawWheel(cx + cw - 25, cy + ch);

        // Tail Lights & Plate
        ctx.fillStyle = '#EF4444';
        ctx.fillRect(cx + cw - 4, cy + 12, 4, 10);
        const px = cx + cw - 8, py = cy + 28, pw = 8, ph = 16;
        ctx.fillStyle = '#FDE047';
        ctx.fillRect(px, py, pw, ph);

        // ALPR Detection Bounding Box
        ctx.strokeStyle = '#10B981';
        ctx.lineWidth = 1.2;
        ctx.setLineDash([3, 2]);
        ctx.strokeRect(cx - 4, cy - 4, cw + 8, ch + 12);
        ctx.setLineDash([]);
        ctx.fillStyle = 'rgba(16, 185, 129, 0.9)';
        ctx.fillRect(cx - 4, cy - 14, 110, 10);
        ctx.fillStyle = '#000';
        ctx.font = 'bold 7px monospace';
        ctx.fillText('OCR: ' + cam3Plate + ' (99%)', cx - 2, cy - 6);

        // Barrier Cabinet
        const bx = 160, by = 80, bw = 16, bh = 85;
        ctx.fillStyle = '#EA580C';
        ctx.fillRect(bx, by, bw, bh);
        ctx.strokeStyle = '#9A3412';
        ctx.lineWidth = 1;
        ctx.strokeRect(bx, by, bw, bh);

        // Strobe Dome
        const strobeColor = (Math.abs(cam3ArmAngle) > 5 && Math.abs(cam3ArmAngle) < 75)
          ? ((Math.floor(cam3Frame / 4) % 2 === 0) ? '#F59E0B' : '#EF4444')
          : (cam3ArmAngle > 45 ? '#10B981' : '#EF4444');
        ctx.fillStyle = strobeColor;
        ctx.beginPath(); ctx.arc(bx + bw/2, by - 2, 4, Math.PI, 0); ctx.fill();

        // Barrier Boom Arm
        ctx.save();
        ctx.translate(bx + bw/2, by + 16);
        ctx.rotate((-cam3ArmAngle * Math.PI) / 180);
        ctx.fillStyle = '#F8FAFC';
        ctx.fillRect(0, -3.5, 120, 7);
        ctx.fillStyle = '#EF4444';
        for (let s = 10; s < 115; s += 20) {
          ctx.beginPath();
          ctx.moveTo(s, -3.5); ctx.lineTo(s + 8, -3.5);
          ctx.lineTo(s + 4, 3.5); ctx.lineTo(s - 4, 3.5);
          ctx.closePath(); ctx.fill();
        }
        ctx.strokeStyle = cam3ArmAngle > 40 ? '#10B981' : '#EF4444';
        ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(0, -3.5); ctx.lineTo(120, -3.5); ctx.stroke();
        ctx.restore();

        drawCCTVLensOverlay(ctx, w, h, 'CAM-03', 'SORTIE & BARRIÈRE VOIE 2', 25.0);
        requestAnimationFrame(render);
      }
      render();
    }

    // --- CAM 4 : VUE PLAFOND NIVEAU 0 ---
    let cam4RadarAngle = 0.0;
    function initCam4() {
      const cvs = document.getElementById('cam4Canvas');
      if (!cvs) return;
      const ctx = cvs.getContext('2d');
      const w = cvs.width, h = cvs.height;

      const stalls = [
        { id: 'A01', status: 'OCC', x: 30, y: 35 },
        { id: 'A02', status: 'OCC', x: 80, y: 35 },
        { id: 'A03', status: 'LIBRE', x: 130, y: 35 },
        { id: 'A04', status: 'RES', x: 180, y: 35 },
        { id: 'A05', status: 'OCC', x: 230, y: 35 },
        { id: 'A06', status: 'LIBRE', x: 280, y: 35 },
        { id: 'A07', status: 'OCC', x: 330, y: 35 },
        { id: 'B01', status: 'OCC', x: 30, y: 145 },
        { id: 'B02', status: 'LIBRE', x: 80, y: 145 },
        { id: 'B03', status: 'OCC', x: 130, y: 145 },
        { id: 'B04', status: 'LIBRE', x: 180, y: 145 },
        { id: 'B05', status: 'OCC', x: 230, y: 145 },
        { id: 'B06', status: 'LIBRE', x: 280, y: 145 },
        { id: 'B07', status: 'OCC', x: 330, y: 145 }
      ];

      function render() {
        cam4RadarAngle += 0.025;

        ctx.clearRect(0, 0, w, h);

        // Deck Floor
        ctx.fillStyle = '#0B132B';
        ctx.fillRect(0, 0, w, h);

        // Central Driving Aisle
        ctx.fillStyle = '#080E1F';
        ctx.fillRect(0, 95, w, 45);
        ctx.strokeStyle = '#38BDF8';
        ctx.lineWidth = 1;
        ctx.setLineDash([8, 8]);
        ctx.beginPath(); ctx.moveTo(0, 117); ctx.lineTo(w, 117); ctx.stroke();
        ctx.setLineDash([]);

        // Stalls
        stalls.forEach(s => {
          const sw = 42, sh = 55;
          let color = '#10B981';
          let fill = 'rgba(16, 185, 129, 0.12)';
          if (s.status === 'OCC') {
            color = '#EF4444';
            fill = 'rgba(239, 68, 68, 0.15)';
          } else if (s.status === 'RES') {
            color = '#F59E0B';
            fill = 'rgba(245, 158, 11, 0.15)';
          }

          ctx.fillStyle = fill;
          ctx.fillRect(s.x, s.y, sw, sh);
          ctx.strokeStyle = color;
          ctx.lineWidth = 1;
          ctx.strokeRect(s.x, s.y, sw, sh);

          if (s.status === 'OCC') {
            ctx.fillStyle = '#1E293B';
            ctx.beginPath();
            ctx.roundRect(s.x + 4, s.y + 6, sw - 8, sh - 12, 4);
            ctx.fill();
            ctx.strokeStyle = '#475569';
            ctx.stroke();
          }

          ctx.fillStyle = color;
          ctx.font = 'bold 7px monospace';
          ctx.textAlign = 'center';
          ctx.fillText(s.id + ' ' + s.status, s.x + sw/2, s.y + (s.y < 100 ? sh - 4 : 12));
          ctx.textAlign = 'left';
        });

        // Radar sweep line from center
        ctx.save();
        ctx.translate(w/2, h/2);
        ctx.rotate(cam4RadarAngle);
        const sweepGrad = ctx.createLinearGradient(0, 0, 160, 0);
        sweepGrad.addColorStop(0, 'rgba(16, 185, 129, 0.4)');
        sweepGrad.addColorStop(1, 'rgba(16, 185, 129, 0)');
        ctx.fillStyle = sweepGrad;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.arc(0, 0, 180, -0.2, 0);
        ctx.closePath();
        ctx.fill();
        ctx.restore();

        drawCCTVLensOverlay(ctx, w, h, 'CAM-04', 'VUE PLAFOND NIVEAU 0', 30.0);
        requestAnimationFrame(render);
      }
      render();
    }

    /* Real-Time WebSocket Telemetry Connection to Edge Gateway with Exponential Backoff */
    let gatewayWs = null;
    let wsReconnectAttempts = 0;
    let wsHeartbeatTimer = null;

    async function initGatewayWebSocket() {
      let wsUrl = "ws://127.0.0.1:8080/ws";
      if (window.pywebview && window.pywebview.api && window.pywebview.api.get_gateway_info) {
        try {
          const info = await window.pywebview.api.get_gateway_info();
          if (info && info.ws_url) {
            wsUrl = info.ws_url;
          }
        } catch (e) {
          console.warn("[SmartPark WS] Failed to fetch gateway info:", e);
        }
      }

      const dot = document.getElementById('wsDot');
      const txt = document.getElementById('txtWsStatus');

      function updateWsIndicator(state) {
        if (!dot || !txt) return;
        const dict = I18N[currentLang] || I18N['fr'];
        if (state === 'connected') {
          dot.style.backgroundColor = 'var(--accent-green)';
          txt.textContent = dict.wsOnline || 'PASSERELLE EN LIGNE';
        } else if (state === 'reconnecting') {
          dot.style.backgroundColor = 'var(--accent-yellow)';
          txt.textContent = dict.wsReconnecting || 'RECONNEXION...';
        } else {
          dot.style.backgroundColor = '#64748B';
          txt.textContent = dict.wsOffline || 'MODE AUTONOME';
        }
      }

      try {
        updateWsIndicator('reconnecting');
        gatewayWs = new WebSocket(wsUrl);

        gatewayWs.onopen = function() {
          wsReconnectAttempts = 0;
          updateWsIndicator('connected');
          if (wsHeartbeatTimer) clearInterval(wsHeartbeatTimer);
          wsHeartbeatTimer = setInterval(() => {
            if (gatewayWs && gatewayWs.readyState === WebSocket.OPEN) {
              gatewayWs.send(JSON.stringify({ type: 'PING', timestamp: Date.now() }));
            }
          }, 25000);
        };

        gatewayWs.onmessage = function(event) {
          try {
            const msg = JSON.parse(event.data);
            handleGatewayBroadcast(msg);
          } catch (err) {
            console.error("[SmartPark WS] Message parse error:", err);
          }
        };

        gatewayWs.onerror = function() {
          if (gatewayWs) gatewayWs.close();
        };

        gatewayWs.onclose = function() {
          if (wsHeartbeatTimer) clearInterval(wsHeartbeatTimer);
          updateWsIndicator('disconnected');
          const delay = Math.min(15000, Math.pow(2, Math.min(wsReconnectAttempts, 4)) * 1000 + Math.random() * 500);
          wsReconnectAttempts++;
          setTimeout(initGatewayWebSocket, delay);
        };
      } catch (err) {
        updateWsIndicator('disconnected');
        setTimeout(initGatewayWebSocket, 5000);
      }
    }

    function handleGatewayBroadcast(msg) {
      if (!msg || !msg.type) return;
      if (msg.type === 'EXIT_CLEARED') {
        if (typeof cam3DepartureStartTime !== 'undefined') {
          cam3DepartureStartTime = performance.now();
        }
      } else if (msg.type === 'BARRIER_OVERRIDE') {
        if (msg.data && msg.data.channel === 2 && typeof cam3DepartureStartTime !== 'undefined') {
          cam3DepartureStartTime = performance.now();
        }
      } else if (msg.type === 'POS_SYNC_BATCH') {
        updateSyncBadge();
        refreshAuditData();
      }
    }

    applyTranslations();
    initCam1();
    initCam2();
    initCam3();
    initCam4();
    updateSyncBadge();
    initGatewayWebSocket();
    setInterval(updateSyncBadge, 10000);
  </script>
</body>
</html>"""


def launch_desktop_station(
    server_url: str = "http://127.0.0.1:8080",
    headless: bool = False,
    booth_id: str = "BOOTH-01",
    cashier_id: str = "AGENT-MEZIANE",
    config: Optional[Dict[str, Any]] = None,
):
    """
    Launch the desktop operator station window using pywebview.
    If headless=True or pywebview cannot create a display, starts in interactive CLI mode.
    """
    bridge_api = DesktopBridgeApi(
        server_url=server_url,
        booth_id=booth_id,
        cashier_id=cashier_id,
        config=config,
    )
    html_content = get_desktop_ui_html()

    if headless:
        print("[smartpark-desktop] Starting Desktop Operator Station in CLI Headless Mode...")
        return bridge_api

    try:
        import webview
        window = webview.create_window(
            title="Smart Park - Operator Workstation & POS",
            html=html_content,
            js_api=bridge_api,
            width=1380,
            height=860,
            min_size=(1024, 680),
        )
        print("[smartpark-desktop] Launching Desktop Window via Microsoft Edge WebView2...")
        webview.start(debug=False)
        return bridge_api
    except Exception as e:
        print(f"[smartpark-desktop] GUI window launch failed ({str(e)}). Running CLI fallback...")
        return bridge_api
