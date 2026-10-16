"""
Smart Park - Thermal Ticket Printer Engine and Barcode Generator.
Supports ESC/POS binary command synthesis, EAN-13 / Code-128 barcode encoding,
ticket layout formatting, visual ticket rendering, and hardware printer dispatching.
"""

from dataclasses import dataclass
from datetime import datetime
import html
import io
import os
import re
from typing import Optional, Tuple


@dataclass
class ParkingTicket:
    ticket_id: str
    plate_number: str
    entry_time: datetime
    lane_id: str
    zone_name: str
    barcode_value: str
    tariff_hourly_dzd: float = 100.0
    grace_period_min: int = 15
    operator_id: str = "BOOTH-01"


class EscPosCommands:
    """Standard ESC/POS binary control codes for thermal receipt printers."""
    ESC = b"\x1b"
    GS = b"\x1d"

    # Hardware Control
    HW_INIT = b"\x1b@"
    CUT_PAPER_FULL = b"\x1dVA0"
    CUT_PAPER_PARTIAL = b"\x1dVA1"
    DRAWER_KICK = b"\x1bp\x00\x19\xfa"  # Standard pin 2 pulse to open cash drawer

    # Text Alignment
    ALIGN_LEFT = b"\x1ba\x00"
    ALIGN_CENTER = b"\x1ba\x01"
    ALIGN_RIGHT = b"\x1ba\x02"

    # Text Sizing and Emphasis
    TEXT_NORMAL = b"\x1b!\x00"
    TEXT_BOLD_ON = b"\x1bE\x01"
    TEXT_BOLD_OFF = b"\x1bE\x00"
    TEXT_DOUBLE_HEIGHT = b"\x1b!\x10"
    TEXT_DOUBLE_WIDTH = b"\x1b!\x20"
    TEXT_DOUBLE_SIZE = b"\x1b!\x30"

    # Line Spacing
    LINE_FEED = b"\n"
    FEED_3_LINES = b"\x1bd\x03"
    FEED_5_LINES = b"\x1bd\x05"

    # Barcode
    BARCODE_HEIGHT_60 = b"\x1dh<\x00"
    BARCODE_WIDTH_3 = b"\x1dw\x03"
    BARCODE_TEXT_BELOW = b"\x1dH\x02"


class ThermalTicketEngine:
    """
    Synthesizes thermal ticket payloads, prints through ESC/POS or Windows spoolers,
    and produces visual previews for on-screen inspection.
    """

    def __init__(self, facility_name: str = "SMARTPARK VISION AI ALGIERS", rc_nif: str = "NIF: 001616098234190 | RC: 16/00-098214B"):
        self.facility_name = facility_name
        self.rc_nif = rc_nif
        self.sequence_counter = 1000

    def generate_ticket(self, plate_number: str, lane_id: str = "LANE-01", zone_name: str = "Zone B (Visiteur)", operator_id: str = "BOOTH-01") -> ParkingTicket:
        """Create a new ticket instance with verified EAN-13 or Code-128 identifier."""
        self.sequence_counter += 1
        now = datetime.now()
        cleaned_plate = re.sub(r"[^0-9]", "", plate_number)
        if not cleaned_plate:
            cleaned_plate = "0000000000"
        
        # Build 12-digit base for EAN-13: 2-digit facility prefix (99) + 4-digit sequence + 6-digit plate snippet
        base_12 = f"99{self.sequence_counter % 10000:04d}{cleaned_plate[-6:]:0>6}"
        checksum = self._calculate_ean13_checksum(base_12)
        barcode_13 = f"{base_12}{checksum}"
        ticket_id = f"TKT-{now.strftime('%Y%m%d')}-{self.sequence_counter:05d}"

        return ParkingTicket(
            ticket_id=ticket_id,
            plate_number=plate_number,
            entry_time=now,
            lane_id=lane_id,
            zone_name=zone_name,
            barcode_value=barcode_13,
            tariff_hourly_dzd=100.0,
            grace_period_min=15,
            operator_id=operator_id,
        )

    @staticmethod
    def _calculate_ean13_checksum(digits12: str) -> int:
        """Calculate standard modulo 10 checksum for 12 numeric digits."""
        total = 0
        for i, ch in enumerate(digits12):
            val = int(ch)
            total += val * 1 if (i % 2 == 0) else val * 3
        remainder = total % 10
        return 0 if remainder == 0 else (10 - remainder)

    def render_escpos_binary(self, ticket: ParkingTicket) -> bytes:
        """Compile complete ESC/POS binary byte stream for thermal receipt printers."""
        buf = bytearray()
        buf.extend(EscPosCommands.HW_INIT)
        buf.extend(EscPosCommands.ALIGN_CENTER)

        # Facility Header
        buf.extend(EscPosCommands.TEXT_BOLD_ON)
        buf.extend(EscPosCommands.TEXT_DOUBLE_HEIGHT)
        buf.extend(self.facility_name.encode("utf-8") + b"\n")
        buf.extend(EscPosCommands.TEXT_NORMAL)
        buf.extend(b"STATIONNEMENT AUTOMATISE SOVERAIN\n")
        buf.extend(self.rc_nif.encode("utf-8") + b"\n")
        buf.extend(b"------------------------------------------\n")

        # Ticket Info
        buf.extend(EscPosCommands.TEXT_BOLD_ON)
        buf.extend(b"TICKET D'ENTREE / PARKING PASS\n")
        buf.extend(EscPosCommands.TEXT_NORMAL)
        buf.extend(f"Ticket ID: {ticket.ticket_id}\n".encode("utf-8"))
        buf.extend(f"Date/Heure: {ticket.entry_time.strftime('%Y-%m-%d %H:%M:%S')}\n".encode("utf-8"))
        buf.extend(f"Voie: {ticket.lane_id} | Operateur: {ticket.operator_id}\n".encode("utf-8"))
        buf.extend(f"Zone Allouee: {ticket.zone_name}\n".encode("utf-8"))
        buf.extend(b"------------------------------------------\n")

        # Plate Highlighting
        buf.extend(EscPosCommands.ALIGN_CENTER)
        buf.extend(b"IMMATRICULATION VEHICULE:\n")
        buf.extend(EscPosCommands.TEXT_BOLD_ON)
        buf.extend(EscPosCommands.TEXT_DOUBLE_SIZE)
        buf.extend(ticket.plate_number.encode("utf-8") + b"\n")
        buf.extend(EscPosCommands.TEXT_NORMAL)
        buf.extend(b"------------------------------------------\n")

        # Barcode (Code-128 / EAN-13)
        buf.extend(EscPosCommands.BARCODE_HEIGHT_60)
        buf.extend(EscPosCommands.BARCODE_WIDTH_3)
        buf.extend(EscPosCommands.BARCODE_TEXT_BELOW)
        # ESC/POS Code-128 format: GS k 73 [len] [data]
        barcode_bytes = ticket.barcode_value.encode("ascii")
        buf.extend(EscPosCommands.GS + b"k" + bytes([73, len(barcode_bytes)]) + barcode_bytes)
        buf.extend(b"\n")

        # Tariff and Legal Notice
        buf.extend(EscPosCommands.ALIGN_LEFT)
        buf.extend(f"Tarif Standard: {ticket.tariff_hourly_dzd:.0f} DZD / Heure\n".encode("utf-8"))
        buf.extend(f"Franchise Gratuite: {ticket.grace_period_min} Minutes\n".encode("utf-8"))
        buf.extend(b"Paiement: Borne automatique ou Caisse sortie\n")
        buf.extend(b"En cas de perte du ticket: Forfait 1500 DZD applique\n")
        buf.extend(b"------------------------------------------\n")
        buf.extend(EscPosCommands.ALIGN_CENTER)
        buf.extend(b"Conforme Loi 18-07 & Loi 25-11 (ANPDP)\n")
        buf.extend(b"Conservation images limitee a 30 jours\n")
        buf.extend(b"MERCI DE VOTRE VISITE - BONNE ROUTE\n")
        buf.extend(EscPosCommands.FEED_5_LINES)
        buf.extend(EscPosCommands.CUT_PAPER_FULL)

        return bytes(buf)

    def render_text_preview(self, ticket: ParkingTicket) -> str:
        """Generate high-contrast textual slip preview for terminal and GUI displays."""
        lines = [
            "==========================================",
            f"       {self.facility_name}",
            "     STATIONNEMENT AUTOMATISE SOVERAIN    ",
            f"   {self.rc_nif}",
            "==========================================",
            "         TICKET D'ENTREE / PASS           ",
            f" Ticket ID:    {ticket.ticket_id}",
            f" Date/Heure:   {ticket.entry_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f" Voie Acces:   {ticket.lane_id}",
            f" Operateur:    {ticket.operator_id}",
            f" Zone:         {ticket.zone_name}",
            "------------------------------------------",
            " IMMATRICULATION VEHICULE:",
            f"       >>> [ {ticket.plate_number} ] <<<",
            "------------------------------------------",
            f" Code-Barres:  {ticket.barcode_value}",
            " [ ||||| ||||||| |||| |||||| ||||| |||| ] ",
            "------------------------------------------",
            f" Tarif:        {ticket.tariff_hourly_dzd:.0f} DZD / heure",
            f" Franchise:    {ticket.grace_period_min} min gratuites",
            " Perte ticket: Forfait 1,500 DZD",
            " Conformite:   Loi 18-07 & Loi 25-11 (ANPDP)",
            "==========================================",
            "   MERCI DE VOTRE VISITE - BONNE ROUTE    ",
            "==========================================",
        ]
        return "\n".join(lines)

    def render_svg_ticket(self, ticket: ParkingTicket) -> str:
        """Render vector SVG thermal ticket preview for crisp desktop screen rendering with XSS sanitization."""
        safe_ticket_id = html.escape(str(ticket.ticket_id))
        safe_entry_time = html.escape(ticket.entry_time.strftime('%Y-%m-%d %H:%M:%S'))
        safe_lane_id = html.escape(str(ticket.lane_id))
        safe_zone_name = html.escape(str(ticket.zone_name))
        safe_plate_number = html.escape(str(ticket.plate_number))
        safe_barcode_value = html.escape(str(ticket.barcode_value))

        return f"""<svg width="340" height="490" viewBox="0 0 340 490" xmlns="http://www.w3.org/2000/svg">
  <rect width="340" height="490" fill="#FFFDF8" rx="8" stroke="#E2E8F0" stroke-width="2"/>
  <rect x="15" y="15" width="310" height="460" fill="none" stroke="#CBD5E1" stroke-dasharray="4,4"/>
  <text x="170" y="45" font-family="'Segoe UI', Roboto, sans-serif" font-size="14" font-weight="800" text-anchor="middle" fill="#080C14">SMART PARK</text>
  <text x="170" y="62" font-family="'Segoe UI', Roboto, sans-serif" font-size="10" font-weight="600" text-anchor="middle" fill="#64748B">ALGER CENTRE</text>
  <line x1="25" y1="75" x2="315" y2="75" stroke="#E2E8F0" stroke-width="1.5"/>
  <text x="170" y="96" font-family="'Segoe UI', Roboto, sans-serif" font-size="12" font-weight="700" text-anchor="middle" fill="#10B981">TICKET DE STATIONNEMENT</text>
  <text x="35" y="125" font-family="monospace" font-size="11" fill="#475569">Ticket: <tspan font-weight="700" fill="#0F172A">{safe_ticket_id}</tspan></text>
  <text x="35" y="145" font-family="monospace" font-size="11" fill="#475569">Entrée: <tspan font-weight="700" fill="#0F172A">{safe_entry_time}</tspan></text>
  <text x="35" y="165" font-family="monospace" font-size="11" fill="#475569">Voie:   <tspan font-weight="700" fill="#0F172A">{safe_lane_id}</tspan> | Zone: <tspan font-weight="700" fill="#0F172A">{safe_zone_name}</tspan></text>
  <rect x="30" y="185" width="280" height="55" fill="#F8FAFC" rx="6" stroke="#94A3B8"/>
  <text x="170" y="203" font-family="'Segoe UI', sans-serif" font-size="10" font-weight="600" text-anchor="middle" fill="#64748B">PLAQUE DETECTEE PAR CAMERA ALPR</text>
  <text x="170" y="228" font-family="monospace" font-size="18" font-weight="900" text-anchor="middle" fill="#0F172A" letter-spacing="2">{safe_plate_number}</text>
  <g transform="translate(45, 255)">
    <rect x="0" y="0" width="250" height="50" fill="#FFFFFF" stroke="#E2E8F0"/>
    <text x="125" y="32" font-family="monospace" font-size="16" letter-spacing="4" text-anchor="middle" fill="#0F172A">||| ||||| || ||||||</text>
  </g>
  <text x="170" y="322" font-family="monospace" font-size="11" font-weight="700" text-anchor="middle" fill="#334155">{safe_barcode_value}</text>
  <line x1="25" y1="335" x2="315" y2="335" stroke="#E2E8F0" stroke-width="1.5"/>
  <text x="35" y="358" font-family="'Segoe UI', sans-serif" font-size="10.5" fill="#475569">Tarif standard: <tspan font-weight="700">100 DZD / heure</tspan></text>
  <text x="35" y="375" font-family="'Segoe UI', sans-serif" font-size="10.5" fill="#475569">Franchise de grace: <tspan font-weight="700">15 minutes</tspan></text>
  <text x="35" y="392" font-family="'Segoe UI', sans-serif" font-size="10" fill="#94A3B8">Paiement especes, Carte CIB ou EDAHABIA</text>
  <rect x="25" y="410" width="290" height="30" fill="#F0FDF4" rx="4" stroke="#BBF7D0"/>
  <text x="170" y="428" font-family="'Segoe UI', sans-serif" font-size="9.5" font-weight="600" text-anchor="middle" fill="#15803D">Stationnement Securise par Vision IA</text>
  <text x="170" y="460" font-family="'Segoe UI', sans-serif" font-size="9" text-anchor="middle" fill="#64748B">Conservez ce ticket pour la validation de sortie</text>
</svg>"""

    def dispatch_print_job(self, ticket: ParkingTicket, target: str = "simulation") -> Tuple[bool, str]:
        """
        Dispatch the ticket to a physical printer or simulation spooler.
        Target options: 'simulation', 'file://path', 'tcp://host:port', or Windows printer name.
        """
        raw_bytes = self.render_escpos_binary(ticket)

        if target == "simulation":
            # Save to temporary spool preview
            spool_dir = os.path.join(os.getcwd(), "desktop", "spool")
            os.makedirs(spool_dir, exist_ok=True)
            spool_file = os.path.join(spool_dir, f"{ticket.ticket_id}.bin")
            with open(spool_file, "wb") as f:
                f.write(raw_bytes)
            return True, f"Ticket printed to simulation spooler: {spool_file}"

        elif target.startswith("file://"):
            filepath = target.replace("file://", "")
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(raw_bytes)
            return True, f"Ticket written to file: {filepath}"

        elif target.startswith("tcp://"):
            # Network ESC/POS printer over raw socket port 9100
            import socket
            host_port = target.replace("tcp://", "").split(":")
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else 9100
            try:
                with socket.create_connection((host, port), timeout=3.0) as s:
                    s.sendall(raw_bytes)
                return True, f"ESC/POS ticket dispatched to {host}:{port}"
            except Exception as e:
                return False, f"Failed network print to {target}: {str(e)}"

        else:
            # Attempt Windows print spooler via win32print
            try:
                import win32print
                printer_name = target if target != "default" else win32print.GetDefaultPrinter()
                handle = win32print.OpenPrinter(printer_name)
                try:
                    job = win32print.StartDocPrinter(handle, 1, (f"SmartPark {ticket.ticket_id}", None, "RAW"))
                    win32print.StartPagePrinter(handle)
                    win32print.WritePrinter(handle, raw_bytes)
                    win32print.EndPagePrinter(handle)
                    win32print.EndDocPrinter(handle)
                finally:
                    win32print.ClosePrinter(handle)
                return True, f"Ticket spooled to Windows printer: {printer_name}"
            except ImportError:
                return False, "win32print not available on this platform"
            except Exception as e:
                return False, f"Windows print error: {str(e)}"

    def kick_cash_drawer(self, target: str = "simulation") -> Tuple[bool, str]:
        """Pulse pin 2 of printer cash drawer port to pop open physical cash register."""
        pulse_bytes = EscPosCommands.DRAWER_KICK
        if target == "simulation":
            return True, "Signal d'ouverture tiroir-caisse émis (Simulation)."
        try:
            import win32print
            printer_name = target if target != "default" else win32print.GetDefaultPrinter()
            handle = win32print.OpenPrinter(printer_name)
            try:
                win32print.StartDocPrinter(handle, 1, ("SmartPark Drawer Kick", None, "RAW"))
                win32print.StartPagePrinter(handle)
                win32print.WritePrinter(handle, pulse_bytes)
                win32print.EndPagePrinter(handle)
                win32print.EndDocPrinter(handle)
            finally:
                win32print.ClosePrinter(handle)
            return True, f"Impulsion tiroir-caisse envoyée à l'imprimante: {printer_name}"
        except Exception as e:
            return False, f"Erreur déclenchement tiroir: {str(e)}"

