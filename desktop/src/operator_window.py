"""
SmartPark Vision AI - Desktop Operator Workstation Application.
Runs on Windows Edge WebView2 or cross-platform webview shell.
Provides 4-channel CCTV grid, emergency Spacebar barrier override,
threat HUD siren alerts, biometric triage modal, cashier POS,
ESC/POS thermal ticket printing, and trilingual Day/Night localization.
"""

from datetime import datetime
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


class DesktopBridgeApi:
    """
    Python backend exposed directly to JavaScript in the desktop window via pywebview.
    """

    def __init__(self, server_url: str = "http://127.0.0.1:8080"):
        self.server_url = server_url
        self.printer_engine = ThermalTicketEngine()
        self.scanner_decoder = BarcodeScannerDecoder()
        self.audio_synth = AudioThreatSynthesizer()
        self.pos_manager = CashierPosManager(booth_id="BOOTH-01")
        self.pos_manager.open_shift("AGENT-MEZIANE", 5000.0)

    def trigger_barrier(self, channel: int = 1, duration_ms: int = 500) -> Dict[str, Any]:
        """Trigger physical Modbus barrier relay via backend server or local simulation."""
        import urllib.request
        self.audio_synth.play_success_chime()
        url = f"{self.server_url}/api/barrier/override"
        payload = json.dumps({"channel": channel, "duration_ms": duration_ms}).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {"success": True, "message": f"Barriere voie {channel} declenchee avec succes", "data": data}
        except Exception:
            # Fallback to local simulation
            return {
                "success": True,
                "message": f"Barriere voie {channel} actionnee (Mode Secours Local)",
                "channel": channel,
                "duration_ms": duration_ms,
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

        return {
            "is_valid": result.is_valid,
            "barcode_raw": result.barcode_raw,
            "plate_snippet": result.plate_number_snippet,
            "entry_time": result.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
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
        # Open exit barrier
        self.trigger_barrier(channel=2, duration_ms=500)
        return {
            "success": True,
            "transaction_id": tx.transaction_id,
            "change_dzd": tx.change_dzd,
            "message": f"Paiement {payment_method} enregistre. Monnaie rendue: {tx.change_dzd:.0f} DZD. Barriere de sortie ouverte.",
        }

    def close_shift(self) -> Dict[str, Any]:
        """Compile shift report."""
        report = self.pos_manager.close_shift()
        self.audio_synth.play_success_chime()
        return report

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
  <title>SmartPark Vision AI - Poste Opérateur et Caisse</title>
  <style>
    :root {
      --bg-primary: #0B1120;
      --bg-surface: #1E293B;
      --bg-surface-elevated: #334155;
      --border-color: #334155;
      --text-main: #F8FAFC;
      --text-muted: #94A3B8;
      --accent-blue: #0284C7;
      --accent-blue-hover: #0369A1;
      --accent-green: #10B981;
      --accent-red: #EF4444;
      --accent-amber: #F59E0B;
      --font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }

    [data-theme="light"] {
      --bg-primary: #F1F5F9;
      --bg-surface: #FFFFFF;
      --bg-surface-elevated: #E2E8F0;
      --border-color: #CBD5E1;
      --text-main: #0F172A;
      --text-muted: #64748B;
      --accent-blue: #0284C7;
      --accent-blue-hover: #0369A1;
      --accent-green: #059669;
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
      animation: strobe 1s infinite alternate;
      flex-shrink: 0;
    }
    @keyframes strobe {
      from { background-color: #DC2626; }
      to { background-color: #7F1D1D; }
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
      <div class="brand-badge">SMARTPARK</div>
      <div class="brand-title" id="txtTitle">Poste Opérateur &amp; Caisse Dédié</div>
      <div class="hotkey-indicator">[BOOTH-01]</div>
    </div>
    <div class="header-pills">
      <div class="status-pill">
        <div class="status-dot"></div>
        <span id="txtStatus">MODBUS &amp; RTSP EN LIGNE</span>
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
          <span class="hotkey-indicator">1080p @ 30fps</span>
        </div>
        <div class="camera-feed-canvas">
          <svg width="100%" height="100%" viewBox="0 0 400 240">
            <rect width="400" height="240" fill="#0B132B"/>
            <path d="M 0 180 L 160 120 L 240 120 L 400 180 L 400 240 L 0 240 Z" fill="#1C2541"/>
            <line x1="200" y1="120" x2="200" y2="240" stroke="#F59E0B" stroke-dasharray="10,10" stroke-width="2"/>
            <!-- Car representation -->
            <rect x="130" y="130" width="140" height="70" rx="8" fill="#1E293B" stroke="#38BDF8" stroke-width="1.5"/>
            <rect x="150" y="165" width="100" height="25" rx="3" fill="#F8FAFC" stroke="#0F172A"/>
            <text x="200" y="182" font-family="monospace" font-size="12" font-weight="900" text-anchor="middle" fill="#0F172A">104822 119 16</text>
            <!-- ALPR Target Box -->
            <rect x="145" y="160" width="110" height="35" fill="none" stroke="#10B981" stroke-width="2" stroke-dasharray="6,3"/>
            <text x="145" y="155" font-family="monospace" font-size="9" font-weight="700" fill="#10B981">OCR: 98.4% [ALGER]</text>
          </svg>
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
          <span class="hotkey-indicator">RGB + NIR 850nm</span>
        </div>
        <div class="camera-feed-canvas">
          <svg width="100%" height="100%" viewBox="0 0 400 240">
            <rect width="400" height="240" fill="#030712"/>
            <circle cx="200" cy="110" r="50" fill="#1E293B" stroke="#38BDF8" stroke-width="1.5"/>
            <circle cx="185" cy="100" r="4" fill="#38BDF8"/>
            <circle cx="215" cy="100" r="4" fill="#38BDF8"/>
            <path d="M 190 130 Q 200 138 210 130" stroke="#38BDF8" stroke-width="2" fill="none"/>
            <rect x="140" y="50" width="120" height="120" fill="none" stroke="#38BDF8" stroke-width="1.5" stroke-dasharray="4,4"/>
            <text x="200" y="185" font-family="monospace" font-size="10" font-weight="700" text-anchor="middle" fill="#38BDF8">VIVACITE NIR: 0.985 [PASSED]</text>
          </svg>
        </div>
        <div class="camera-telemetry">
          <span>ARCFACE 512-D</span>
          <span>DISTANCE: 0.418</span>
        </div>
      </div>

      <!-- Cam 3: Exit Plate -->
      <div class="camera-tile" id="tileCam3">
        <div class="camera-header">
          <strong id="lblCam3">CAM 3: Sortie &amp; Barrière (Voie 2)</strong>
          <span class="hotkey-indicator">1080p @ 30fps</span>
        </div>
        <div class="camera-feed-canvas">
          <svg width="100%" height="100%" viewBox="0 0 400 240">
            <rect width="400" height="240" fill="#0B132B"/>
            <!-- Barrier Gate representation -->
            <rect x="50" y="80" width="16" height="120" fill="#E2E8F0"/>
            <rect x="66" y="90" width="220" height="10" fill="#EF4444" transform="rotate(-5 66 90)"/>
            <circle cx="58" cy="95" r="5" fill="#10B981"/>
            <text x="200" y="160" font-family="monospace" font-size="11" font-weight="700" text-anchor="middle" fill="#94A3B8">SAS DE SORTIE LIBRE</text>
          </svg>
        </div>
        <div class="camera-telemetry">
          <span>BOUCLE INDUCTIVE: ACTIVE</span>
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
          <svg width="100%" height="100%" viewBox="0 0 400 240">
            <rect width="400" height="240" fill="#0F172A"/>
            <!-- Parking slots representation -->
            <rect x="30" y="40" width="60" height="70" fill="rgba(239, 68, 68, 0.2)" stroke="#EF4444"/>
            <text x="60" y="80" font-size="10" font-weight="700" text-anchor="middle" fill="#EF4444">A01 (OCC)</text>
            <rect x="100" y="40" width="60" height="70" fill="rgba(239, 68, 68, 0.2)" stroke="#EF4444"/>
            <text x="130" y="80" font-size="10" font-weight="700" text-anchor="middle" fill="#EF4444">A02 (OCC)</text>
            <rect x="170" y="40" width="60" height="70" fill="rgba(16, 185, 129, 0.2)" stroke="#10B981"/>
            <text x="200" y="80" font-size="10" font-weight="700" text-anchor="middle" fill="#10B981">A03 (LIBRE)</text>
            <rect x="240" y="40" width="60" height="70" fill="rgba(245, 158, 11, 0.2)" stroke="#F59E0B"/>
            <text x="270" y="80" font-size="10" font-weight="700" text-anchor="middle" fill="#F59E0B">A04 (RES)</text>
          </svg>
        </div>
        <div class="camera-telemetry">
          <span>OCCUPATION: 8 / 14 PLACES</span>
          <span>DISPONIBLES: 6</span>
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

          <div style="margin-top: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
            <button class="btn-action" style="background:#10B981;" onclick="processPayment('CASH')" id="btnCash">Espèces (P)</button>
            <button class="btn-action" style="background:#0284C7;" onclick="processPayment('CIB_TERMINAL')" id="btnCard">Carte CIB</button>
          </div>
        </div>

        <div style="margin-top: 14px;">
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
    <div>SmartPark Vision AI v2.0 - Station d'Exploitation Souveraine</div>
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
        lblScan: "Scan Code-Barres / Entrée Manuelle (Touche S):",
        btnVerify: "Vérifier Ticket",
        lblPlate: "Immatriculation:",
        lblDuration: "Durée Stationnée:",
        lblRate: "Tarif Appliqué:",
        lblTotal: "Montant à Payer:",
        btnCash: "Espèces (P)",
        btnCard: "Carte CIB",
        btnZReport: "Clôture de Caisse (Rapport Z)",
        btnTheme: "Mode Jour / Nuit (D)",
        btnLang: "Langue: FR (L)",
        txtShortcuts: "Raccourcis: ",
        btnPrintTicket: "Imprimer Ticket Entrée (T)",
        threatText: "ALERTE SÉCURITÉ: VÉHICULE RECHERCHÉ OU TENTATIVE DE SPOOFING"
      },
      en: {
        title: "Guard Station & Dedicated POS",
        status: "MODBUS & RTSP ONLINE",
        cam1: "CAM 1: Entry ALPR (Lane 1)",
        cam2: "CAM 2: Biometric Kiosk (Lane 1)",
        cam3: "CAM 3: Exit & Barrier (Lane 2)",
        cam4: "CAM 4: Level 0 Overhead Deck",
        barrier: "EMERGENCY BARRIER OVERRIDE",
        barrierSub: "PRESS SPACEBAR",
        tabPos: "Cashier POS",
        tabScenarios: "Scenarios (1-7)",
        tabTicket: "Thermal Ticket",
        lblScan: "Scan Barcode / Manual Input (Key S):",
        btnVerify: "Verify Ticket",
        lblPlate: "License Plate:",
        lblDuration: "Elapsed Duration:",
        lblRate: "Applied Tariff:",
        lblTotal: "Amount Due:",
        btnCash: "Cash (P)",
        btnCard: "CIB Card",
        btnZReport: "End-of-Shift Z-Report",
        btnTheme: "Day / Night Mode (D)",
        btnLang: "Language: EN (L)",
        txtShortcuts: "Shortcuts: ",
        btnPrintTicket: "Print Entry Ticket (T)",
        threatText: "SECURITY ALERT: WATCHLIST MATCH OR SPOOF ATTEMPT"
      },
      ar: {
        title: "مركز الحراسة والصندوق المخصص",
        status: "مودبوس و RTSP متصل",
        cam1: "كاميرا 1: مدخل لوحات (المسلك 1)",
        cam2: "كاميرا 2: كشك التعرف على الوجه",
        cam3: "كاميرا 3: مخرج وحاجز (المسلك 2)",
        cam4: "كاميرا 4: مراقبة الطابق الأرضي",
        barrier: "فتح الحاجز في حالات الطوارئ",
        barrierSub: "اضغط على زر المسافة (Spacebar)",
        tabPos: "الصندوق POS",
        tabScenarios: "سيناريوهات (1-7)",
        tabTicket: "تذكرة حرارية",
        lblScan: "مسح الرمز الشريطي / إدخال يدوي (زر S):",
        btnVerify: "تحقق من التذكرة",
        lblPlate: "رقم اللوحة:",
        lblDuration: "مدة الركن:",
        lblRate: "التعريفة المطبقة:",
        lblTotal: "المبلغ المستحق:",
        btnCash: "نقداً (P)",
        btnCard: "بطاقة CIB",
        btnZReport: "إغلاق الصندوق (تقرير Z)",
        btnTheme: "وضع النهار / الليل (D)",
        btnLang: "اللغة: العربية (L)",
        txtShortcuts: "اختصارات: ",
        btnPrintTicket: "طباعة تذكرة الدخول (T)",
        threatText: "تنبيه أمني: سيارة مسروقة أو محاولة تزييف بيومتري"
      }
    };

    function applyTranslations() {
      const dict = I18N[currentLang];
      document.getElementById('txtTitle').innerText = dict.title;
      document.getElementById('txtStatus').innerText = dict.status;
      document.getElementById('lblCam1').innerText = dict.cam1;
      document.getElementById('lblCam2').innerText = dict.cam2;
      document.getElementById('lblCam3').innerText = dict.cam3;
      document.getElementById('lblCam4').innerText = dict.cam4;
      document.getElementById('btnBarrier').children[0].innerText = dict.barrier;
      document.getElementById('btnBarrier').children[1].innerText = dict.barrierSub;
      document.getElementById('tabPos').innerText = dict.tabPos;
      document.getElementById('tabScenarios').innerText = dict.tabScenarios;
      document.getElementById('tabTicket').innerText = dict.tabTicket;
      document.getElementById('lblScan').innerText = dict.lblScan;
      document.getElementById('btnVerify').innerText = dict.btnVerify;
      document.getElementById('lblPlate').innerText = dict.lblPlate;
      document.getElementById('lblDuration').innerText = dict.lblDuration;
      document.getElementById('lblRate').innerText = dict.lblRate;
      document.getElementById('lblTotal').innerText = dict.lblTotal;
      document.getElementById('btnCash').innerText = dict.btnCash;
      document.getElementById('btnCard').innerText = dict.btnCard;
      document.getElementById('btnZReport').innerText = dict.btnZReport;
      document.getElementById('btnTheme').innerText = dict.btnTheme;
      document.getElementById('btnLang').innerText = dict.btnLang;
      document.getElementById('txtShortcuts').innerText = dict.txtShortcuts;
      document.getElementById('btnPrintTicket').innerText = dict.btnPrintTicket;
      document.getElementById('threatText').innerText = dict.threatText;

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
      }
    }

    async function triggerManualBarrier() {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.trigger_barrier(1, 500);
      }
      const st = document.getElementById('gateStatus');
      st.innerText = "BARRIÈRE: OUVERTE (IMPULSION)";
      st.style.color = "#10B981";
      setTimeout(() => {
        st.innerText = "BARRIÈRE: FERMÉE";
        st.style.color = "#38BDF8";
      }, 3000);
    }

    async function triggerScenario(key) {
      if (key === 'watchlist_alert' || key === 'spoof_attack' || key === 'clone_dispute') {
        showThreat(key);
      } else if (key === 'driver_mismatch') {
        document.getElementById('triageModal').style.display = 'flex';
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
          total_due_dzd: 200.0
        };
      }
      currentScanData = res;
      document.getElementById('valPlate').innerText = res.plate_snippet || "104822 119 16";
      document.getElementById('valDuration').innerText = res.elapsed_minutes + " min";
      document.getElementById('valTotal').innerText = res.total_due_dzd.toFixed(0) + " DZD";
      document.getElementById('scanResultCard').style.display = 'block';
    }

    function handleBarcodeEnter(e) {
      if (e.key === 'Enter') {
        executeScan();
      }
    }

    async function processPayment(method) {
      if (!currentScanData) return;
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.settle_payment(
          "TKT-CURRENT",
          currentScanData.plate_snippet,
          currentScanData.total_due_dzd,
          method,
          currentScanData.total_due_dzd
        );
      }
      alert("Paiement enregistré avec succès. La barrière de sortie est ouverte.");
      document.getElementById('scanResultCard').style.display = 'none';
      document.getElementById('barcodeInput').value = '';
    }

    async function printManualTicket() {
      const plate = document.getElementById('manualPlateInput').value.trim() || "08412 00 16";
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

    async function closeShiftZReport() {
      let rep;
      if (window.pywebview && window.pywebview.api) {
        rep = await window.pywebview.api.close_shift();
        alert("RAPPORT Z GÉNÉRÉ AVEC SUCCÈS:\\n" +
              "Recettes Espèces: " + rep.total_cash_revenue_dzd + " DZD\\n" +
              "Recettes Carte: " + rep.total_card_revenue_dzd + " DZD\\n" +
              "Total Encaissé: " + rep.total_revenue_dzd + " DZD\\n" +
              "Hash d'audit: " + rep.audit_hash);
      } else {
        alert("Clôture de shift Z-Report effectuée.");
      }
    }

    async function resolveTriage(decision) {
      document.getElementById('triageModal').style.display = 'none';
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.guard_decision("104822 119 16", decision, "Avis opérateur poste");
      }
    }

    /* Global Physical Keyboard Shortcuts */
    window.addEventListener('keydown', (e) => {
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

    applyTranslations();
  </script>
</body>
</html>"""


def launch_desktop_station(server_url: str = "http://127.0.0.1:8080", headless: bool = False):
    """
    Launch the desktop operator station window using pywebview.
    If headless=True or pywebview cannot create a display, starts in interactive CLI mode.
    """
    bridge_api = DesktopBridgeApi(server_url=server_url)
    html_content = get_desktop_ui_html()

    if headless:
        print("[smartpark-desktop] Starting Desktop Operator Station in CLI Headless Mode...")
        return bridge_api

    try:
        import webview
        window = webview.create_window(
            title="SmartPark Vision AI - Operator Workstation & POS",
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
