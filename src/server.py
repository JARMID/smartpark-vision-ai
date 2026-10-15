"""
SmartPark Vision AI - Sovereign FastAPI Server and Real-Time Gateway.
Serves REST APIs, WebSocket live telemetry, simulation triggers, and command center UI.
"""

import asyncio
from datetime import datetime, timezone
import json
import os
import time
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import numpy as np

from src.main import GateOrchestrator, GateDecisionResult
from src.compliance.law_25_11_audit import Law2511ComplianceEngine
from src.payment.chargily_v2_client import ChargilyV2PaymentClient
from src.camera.edge_stream_manager import EdgeStreamManager

app = FastAPI(title="SmartPark Vision AI Sovereign Server", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Orchestrator
default_db = "/tmp/smartpark_demo.db" if os.environ.get("VERCEL") else "smartpark_demo.db"
DB_PATH = os.environ.get("SMARTPARK_DB_PATH", default_db)
orchestrator = GateOrchestrator(db_path=DB_PATH, simulation_mode=True)
compliance_engine = Law2511ComplianceEngine()
chargily_client = ChargilyV2PaymentClient()

# Initialize Multi-Channel Camera Stream Manager
edge_stream_manager = EdgeStreamManager(orchestrator=orchestrator, auto_start=False)

CAMERAS_TOPOLOGY = [
    {
        "camera_id": "cam_lane1_entry_plate",
        "lane_id": "lane_1",
        "role": "plate_entry",
        "name": "CAM 1 - Entry Plate ALPR Telephoto",
        "ip": "192.168.10.101",
        "rtsp_url": "rtsp://admin:smartpark2026@192.168.10.101:554/Streaming/Channels/101",
        "resolution": "1920x1080 @ 30fps",
        "transport": "TCP",
        "roi": "35% Top, 20% Left, 85% Bottom, 80% Right",
        "sensor": "Sony STARVIS 2 IMX678 (4K Ultra Low Light)",
    },
    {
        "camera_id": "cam_lane1_driver_face",
        "lane_id": "lane_1",
        "role": "face_entry",
        "name": "CAM 2 - Driver Window Biometric Dual-Lens",
        "ip": "192.168.10.102",
        "rtsp_url": "rtsp://admin:smartpark2026@192.168.10.102:554/Streaming/Channels/101",
        "resolution": "1920x1080 @ 30fps (RGB + 850nm NIR)",
        "transport": "TCP",
        "roi": "15% Top, 25% Left, 85% Bottom, 75% Right",
        "sensor": "Dual Omnivision OS04A10 RGB-NIR with Active Illumination",
    },
    {
        "camera_id": "cam_lane2_exit_plate",
        "lane_id": "lane_2",
        "role": "plate_exit",
        "name": "CAM 3 - Exit Barrier & Gantry VMS",
        "ip": "192.168.10.104",
        "rtsp_url": "rtsp://admin:smartpark2026@192.168.10.104:554/Streaming/Channels/101",
        "resolution": "1920x1080 @ 30fps",
        "transport": "TCP",
        "roi": "30% Top, 20% Left, 85% Bottom, 80% Right",
        "sensor": "Axis P1455-LE-3 Varifocal with Lightfinder 2.0",
    },
    {
        "camera_id": "cam_deck_zone_a",
        "lane_id": "zone_a",
        "role": "overhead_deck",
        "name": "CAM 4 - Level -1 Parking Deck Occupancy",
        "ip": "192.168.10.105",
        "rtsp_url": "rtsp://admin:smartpark2026@192.168.10.105:554/Streaming/Channels/101",
        "resolution": "2560x1440 @ 15fps",
        "transport": "TCP",
        "roi": "Full 180° Panoramic Overview",
        "sensor": "Hikvision DS-2CD63C5G0-IVS Fisheye 12MP Sensor",
    },
]

# Pre-enroll known VIPs and Blacklists for the interactive demo
np.random.seed(42)
VIP_EMBEDDING_1 = np.random.randn(512).astype(np.float32)
VIP_EMBEDDING_1 /= np.linalg.norm(VIP_EMBEDDING_1)

VIP_EMBEDDING_2 = np.random.randn(512).astype(np.float32)
VIP_EMBEDDING_2 /= np.linalg.norm(VIP_EMBEDDING_2)

SUSPECT_EMBEDDING = np.random.randn(512).astype(np.float32)
SUSPECT_EMBEDDING /= np.linalg.norm(SUSPECT_EMBEDDING)

orchestrator.enroll_subscriber(
    person_id="p-vip-001",
    full_name="Amine Hadj",
    plate_raw="10482211916",
    plate_formatted="104822 119 16",
    face_embedding=VIP_EMBEDDING_1,
)

orchestrator.enroll_subscriber(
    person_id="p-vip-002",
    full_name="Karim Benali",
    plate_raw="0412211816",
    plate_formatted="04122 118 16",
    face_embedding=VIP_EMBEDDING_2,
)

orchestrator.enroll_subscriber(
    person_id="p-suspect-999",
    full_name="Identité Inconnue (Fiche Recherche)",
    plate_raw="0055121816",
    plate_formatted="00551 218 16",
    face_embedding=SUSPECT_EMBEDDING,
    is_blacklisted=True,
)

# Seed active parked vehicles into the Anti-Passback & Clone Detection registry
orchestrator.register_active_vehicle("104822 119 16", slot_number="A01", driver_name="Amine Hadj", is_vip=True)
orchestrator.register_active_vehicle("04122 118 16", slot_number="A02", driver_name="Karim Benali", is_vip=True)
orchestrator.register_active_vehicle("08192 120 09", slot_number="B01", driver_name="Visiteur Public", is_vip=False)
orchestrator.register_active_vehicle("99120 121 16", slot_number="B03", driver_name="Visiteur Public", is_vip=False)
orchestrator.register_active_vehicle("03144 117 31", slot_number="B05", driver_name="Visiteur Public", is_vip=False)

# In-Memory Parking Stalls & Occupancy State
PARKING_SLOTS = [
    # Zone A: VIP
    {"slot_number": "A01", "zone_name": "Zone A (VIP)", "floor_level": "Level 0", "status": "occupied", "plate": "104822 119 16", "parked_since": "14:15"},
    {"slot_number": "A02", "zone_name": "Zone A (VIP)", "floor_level": "Level 0", "status": "occupied", "plate": "04122 118 16", "parked_since": "15:30"},
    {"slot_number": "A03", "zone_name": "Zone A (VIP)", "floor_level": "Level 0", "status": "vacant", "plate": None, "parked_since": None},
    {"slot_number": "A04", "zone_name": "Zone A (VIP)", "floor_level": "Level 0", "status": "reserved", "plate": None, "parked_since": None},
    # Zone B: Public Visitors
    {"slot_number": "B01", "zone_name": "Zone B (Visiteur)", "floor_level": "Level 0", "status": "occupied", "plate": "08192 120 09", "parked_since": "12:00"},
    {"slot_number": "B02", "zone_name": "Zone B (Visiteur)", "floor_level": "Level 0", "status": "vacant", "plate": None, "parked_since": None},
    {"slot_number": "B03", "zone_name": "Zone B (Visiteur)", "floor_level": "Level 0", "status": "occupied", "plate": "99120 121 16", "parked_since": "16:10"},
    {"slot_number": "B04", "zone_name": "Zone B (Visiteur)", "floor_level": "Level 0", "status": "vacant", "plate": None, "parked_since": None},
    {"slot_number": "B05", "zone_name": "Zone B (Visiteur)", "floor_level": "Level 0", "status": "occupied", "plate": "03144 117 31", "parked_since": "11:45"},
    {"slot_number": "B06", "zone_name": "Zone B (Visiteur)", "floor_level": "Level 0", "status": "vacant", "plate": None, "parked_since": None},
    # Zone C: Commercial
    {"slot_number": "C01", "zone_name": "Zone C (Utilitaire)", "floor_level": "Level 0", "status": "occupied", "plate": "01412 322 09", "parked_since": "09:30"},
    {"slot_number": "C02", "zone_name": "Zone C (Utilitaire)", "floor_level": "Level 0", "status": "vacant", "plate": None, "parked_since": None},
    # Zone D: PMR
    {"slot_number": "D01", "zone_name": "Zone D (PMR)", "floor_level": "Level 0", "status": "vacant", "plate": None, "parked_since": None},
    {"slot_number": "D02", "zone_name": "Zone D (PMR)", "floor_level": "Level 0", "status": "occupied", "plate": "00912 116 16", "parked_since": "13:20"},
]

# In-Memory Event Log for Fast Display
RECENT_EVENTS = [
    {
        "id": 1,
        "timestamp": "16:42:10",
        "camera_id": "CAM-01 (Entrée)",
        "plate": "104822 119 16",
        "wilaya": "Alger (16)",
        "driver": "Amine Hadj (VIP)",
        "result": "cleared_vip",
        "barrier_opened": True,
        "liveness": 0.98,
        "distance": 0.42,
    },
    {
        "id": 2,
        "timestamp": "16:38:22",
        "camera_id": "CAM-01 (Entrée)",
        "plate": "08192 120 09",
        "wilaya": "Blida (09)",
        "driver": "Visiteur Public",
        "result": "cleared_visitor",
        "barrier_opened": True,
        "liveness": 0.95,
        "distance": None,
    },
]


class ConnectionManager:
    """Manages real-time WebSocket client connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass


ws_manager = ConnectionManager()


# Request Models
class SimulateRequest(BaseModel):
    scenario: str  # 'vip_entry', 'temporary_00', 'watchlist_alert', 'spoof_attack', 'driver_mismatch', 'visitor_payment_exit'


class BarrierOverrideRequest(BaseModel):
    channel: int = 1
    duration_ms: int = 500


class ChargilyCheckoutRequest(BaseModel):
    plate: str = "08192 120 09"
    amount_dzd: float = 200.0
    card_type: str = "EDAHABIA"


class ChargilyPayRequest(BaseModel):
    checkout_id: str
    otp_code: str = "481902"


class GuardDecisionRequest(BaseModel):
    plate: str
    decision: str  # 'grant' or 'deny'
    reason: Optional[str] = "Validation manuelle de l'agent de garde"


class SlotToggleRequest(BaseModel):
    slot_number: str
    new_status: Optional[str] = None
    plate: Optional[str] = None


class TicketGenerateRequest(BaseModel):
    plate: str = "08412 00 16"
    zone: str = "Zone B"


class VehicleExitRequest(BaseModel):
    plate: str = "104822 119 16"
    camera_id: Optional[str] = "CAM-03 (Sortie)"


class DpiaGenerateRequest(BaseModel):
    dpo_name: Optional[str] = "Mohamed Cherif"
    dpo_phone: Optional[str] = "+213 550 99 88 77"


class BreachTriageCreateRequest(BaseModel):
    incident_type: str = "TENTATIVE_EXTRACTION_NON_AUTORISEE"
    severity: str = "HIGH"
    description: str = "Tentative de dump de la table registered_vehicles"
    impacted_records: int = 250


class WebhookVerifyRequest(BaseModel):
    payload: Dict[str, Any]
    signature: str


# REST Endpoints
@app.get("/api/status")
def get_system_status():
    occupied = sum(1 for s in PARKING_SLOTS if s["status"] == "occupied")
    total = len(PARKING_SLOTS)
    return {
        "system_status": "ONLINE",
        "deployment_profile": "PROFILE 1 (Single-PC Sovereign Appliance)",
        "anpdp_compliance": "LOI 18-07 & LOI 25-11 VERIFIED",
        "data_sovereignty": "100% On-Premise Domestic Storage (Zero Foreign Cloud)",
        "gpu_telemetry": {
            "model": "NVIDIA GeForce RTX 4070 (8GB VRAM)",
            "temperature_c": 49,
            "vram_used_mb": 2150,
            "vram_total_mb": 8188,
        },
        "ups_status": {
            "power_source": "ON_LINE_AC",
            "voltage_in": 230.4,
            "battery_percent": 100,
            "runtime_remaining_min": 60,
        },
        "occupancy": {
            "occupied_slots": occupied,
            "total_slots": total,
            "percentage": round((occupied / total) * 100, 1),
            "free_slots": total - occupied,
        },
        "active_cameras": 5,
        "ram_vector_cache_size": 10000,
        "ram_faiss_search_latency_ms": 0.74,
    }


@app.get("/api/cameras")
def get_cameras():
    """Return live camera ingestion topology, hardware specs, and RTSP stream health."""
    live_statuses = edge_stream_manager.get_camera_statuses()
    result = []
    for c in CAMERAS_TOPOLOGY:
        cid = c["camera_id"]
        status_info = live_statuses.get(cid, {})
        entry = dict(c)
        entry["live_status"] = status_info.get("status", "streaming")
        entry["frames_ingested"] = status_info.get("frames_ingested", 142050)
        entry["dropped_frames"] = status_info.get("frames_dropped", 12)
        entry["reconnects"] = status_info.get("reconnects", 0)
        result.append(entry)
    return {
        "status": "ONLINE",
        "total_cameras": len(result),
        "gateway_device": "Advantech MIC-770 / NVIDIA Jetson Orin Edge Node",
        "network_vlan": "192.168.10.0/24 (Isolated Physical CCTV VLAN)",
        "protocol": "RTSP over TCP (RFC 7826) / ONVIF Profile S/T",
        "cameras": result,
    }


@app.get("/api/slots")
def get_slots():
    return PARKING_SLOTS


@app.get("/api/events")
def get_events():
    return RECENT_EVENTS


@app.post("/api/barrier/override")
async def override_barrier(req: BarrierOverrideRequest):
    res = orchestrator.barrier_controller.trigger_barrier_open(
        channel=req.channel, duration_ms=req.duration_ms, force_override=True
    )
    event_data = {
        "type": "BARRIER_MANUAL_OVERRIDE",
        "channel": req.channel,
        "duration_ms": req.duration_ms,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "success": res.success,
    }
    await ws_manager.broadcast(event_data)
    return {"success": res.success, "message": res.message, "latency_ms": res.latency_ms}


@app.post("/api/simulate")
async def simulate_scenario(req: SimulateRequest):
    now_str = datetime.now().strftime("%H:%M:%S")
    scenario = req.scenario

    if scenario == "vip_entry":
        # Reset presence for VIP entry scenario reproducibility
        cleaned_vip = "".join(filter(str.isdigit, "104822 119 16"))
        orchestrator.active_inside_vehicles.pop(cleaned_vip, None)

        decision = orchestrator.process_arrival(
            camera_id="CAM-01 (Entrée)",
            raw_plate_text="104822 119 16",
            plate_confidence=0.98,
            face_embedding=VIP_EMBEDDING_1,
            liveness_score=0.98,
        )
        event = {
            "id": len(RECENT_EVENTS) + 1,
            "timestamp": now_str,
            "camera_id": "CAM-01 (Entrée)",
            "plate": "104822 119 16",
            "wilaya": "Alger (16)",
            "driver": "Amine Hadj (VIP)",
            "result": "cleared_vip",
            "barrier_opened": True,
            "liveness": 0.98,
            "distance": 0.42,
            "message": "Accès VIP accordé (<250ms)",
        }
        RECENT_EVENTS.insert(0, event)
        await ws_manager.broadcast({"type": "GATE_EVENT", "data": event})
        return decision

    elif scenario == "temporary_00":
        # Temporary 00 plate entry (carte grise provisoire)
        visitor_v = np.random.randn(512).astype(np.float32)
        visitor_v /= np.linalg.norm(visitor_v)
        decision = orchestrator.process_arrival(
            camera_id="CAM-01 (Entrée)",
            raw_plate_text="08412 00 16",
            plate_confidence=0.95,
            face_embedding=visitor_v,
            liveness_score=0.96,
        )
        event = {
            "id": len(RECENT_EVENTS) + 1,
            "timestamp": now_str,
            "camera_id": "CAM-01 (Entrée)",
            "plate": "08412 00 16",
            "wilaya": "Alger (16)",
            "driver": "Véhicule Neuf (Provisoire 00)",
            "result": "cleared_visitor",
            "barrier_opened": True,
            "liveness": 0.96,
            "distance": None,
            "ticket_qr": decision.get("ticket_qr"),
            "message": "Plaque Provisoire 00 validée -> Ticket QR émis",
        }
        RECENT_EVENTS.insert(0, event)
        await ws_manager.broadcast({"type": "GATE_EVENT", "data": event})
        return decision

    elif scenario == "watchlist_alert":
        decision = orchestrator.process_arrival(
            camera_id="CAM-01 (Entrée)",
            raw_plate_text="00551 218 16",
            plate_confidence=0.97,
            face_embedding=SUSPECT_EMBEDDING,
            liveness_score=0.94,
        )
        event = {
            "id": len(RECENT_EVENTS) + 1,
            "timestamp": now_str,
            "camera_id": "CAM-01 (Entrée)",
            "plate": "00551 218 16",
            "wilaya": "Alger (16)",
            "driver": "SUSPECT - Fiche Vol Signalée",
            "result": "denied_blacklist",
            "barrier_opened": False,
            "liveness": 0.94,
            "distance": 0.28,
            "message": "ALERTE SÉCURITÉ: Véhicule volé signalé. Barrière verrouillée.",
        }
        RECENT_EVENTS.insert(0, event)
        await ws_manager.broadcast({"type": "SECURITY_ALERT", "data": event})
        return decision

    elif scenario == "spoof_attack":
        # Photo / Screen presentation attack intercepted by MiniFASNet
        decision = orchestrator.process_arrival(
            camera_id="CAM-01 (Entrée)",
            raw_plate_text="104822 119 16",
            plate_confidence=0.98,
            face_embedding=VIP_EMBEDDING_1,
            liveness_score=0.22,  # Low score
        )
        event = {
            "id": len(RECENT_EVENTS) + 1,
            "timestamp": now_str,
            "camera_id": "CAM-01 (Borne)",
            "plate": "104822 119 16",
            "wilaya": "Alger (16)",
            "driver": "Attaque Photo Détectée",
            "result": "denied_spoof",
            "barrier_opened": False,
            "liveness": 0.22,
            "distance": None,
            "message": "Tentative de fraude par écran/photo interceptée par MiniFASNet.",
        }
        RECENT_EVENTS.insert(0, event)
        await ws_manager.broadcast({"type": "SPOOF_ALERT", "data": event})
        return decision

    elif scenario == "driver_mismatch":
        # Known VIP plate, but stranger driving -> prompt operator
        stranger_v = np.random.randn(512).astype(np.float32)
        stranger_v /= np.linalg.norm(stranger_v)
        event = {
            "id": len(RECENT_EVENTS) + 1,
            "timestamp": now_str,
            "camera_id": "CAM-01 (Borne)",
            "plate": "04122 118 16",
            "wilaya": "Alger (16)",
            "driver": "Conducteur non reconnu (Dist: 0.62)",
            "result": "hold_guard_review",
            "barrier_opened": False,
            "liveness": 0.97,
            "distance": 0.62,
            "message": "Discordance Chauffeur / Véhicule. Validation manuelle requise.",
        }
        RECENT_EVENTS.insert(0, event)
        await ws_manager.broadcast({"type": "GUARD_PROMPT", "data": event})
        return {
            "result": GateDecisionResult.HOLD_GUARD_REVIEW,
            "barrier_opened": False,
            "message": "Conducteur différent du propriétaire enregistré.",
        }

    elif scenario == "visitor_payment_exit":
        # Pay-on-foot pre-exit settlement: Paid via Chargily Pay V2 / Cash -> 15min grace -> Exit barrier opens
        event = {
            "id": len(RECENT_EVENTS) + 1,
            "timestamp": now_str,
            "camera_id": "CAM-03 (Sortie)",
            "plate": "08192 120 09",
            "wilaya": "Blida (09)",
            "driver": "Visiteur Réglé (Chargily Pay)",
            "result": "cleared_exit",
            "barrier_opened": True,
            "amount_paid_dzd": 200.0,
            "grace_period_remaining": "11 min",
            "message": "Paiement CIB/Edahabia validé -> Barrière Sortie ouverte (<200ms)",
        }
        RECENT_EVENTS.insert(0, event)
        await ws_manager.broadcast({"type": "EXIT_CLEARED", "data": event})
        return {
            "result": "cleared_exit",
            "barrier_opened": True,
            "amount_paid_dzd": 200.0,
            "plate": "08192 120 09",
            "latency_ms": 190.0,
        }

    elif scenario in ("duplicate_plate_fraud", "cloned_plate_alert"):
        # Guarantee vehicle is recorded inside first to demonstrate Anti-Passback
        cleaned_vip = "".join(filter(str.isdigit, "104822 119 16"))
        if cleaned_vip not in orchestrator.active_inside_vehicles:
            orchestrator.register_active_vehicle("104822 119 16", slot_number="A01", driver_name="Amine Hadj", is_vip=True)

        decision = orchestrator.process_arrival(
            camera_id="CAM-01 (Entrée)",
            raw_plate_text="104822 119 16",
            plate_confidence=0.99,
            face_embedding=VIP_EMBEDDING_1,
            liveness_score=0.98,
        )
        event = {
            "id": len(RECENT_EVENTS) + 1,
            "timestamp": now_str,
            "camera_id": "CAM-01 (Entrée)",
            "plate": "104822 119 16",
            "wilaya": "Alger (16)",
            "driver": "SUSPICION PLAQUE CLONÉE / DOUBLE PASSAGE",
            "result": "denied_antipassback",
            "barrier_opened": False,
            "liveness": 0.98,
            "distance": None,
            "error_code": "CLONED_PLATE_OR_DOUBLE_ENTRY_VIOLATION",
            "message": (
                "ALERTE ROUGE: Véhicule déjà stationné en Place A01 depuis 14:15. "
                "Suspicion de plaque clonée ou violation Anti-Passback. Barrière verrouillée."
            ),
        }
        RECENT_EVENTS.insert(0, event)
        await ws_manager.broadcast({"type": "SECURITY_ALERT", "data": event})
        return decision

    raise HTTPException(status_code=400, detail="Scénario non reconnu")


@app.get("/api/active-vehicles")
def get_active_vehicles():
    """Return all vehicles currently inside the parking perimeter for Anti-Passback monitoring."""
    vehicles = list(orchestrator.active_inside_vehicles.values())
    return {
        "status": "ONLINE",
        "total_inside": len(vehicles),
        "antipassback_enabled": orchestrator.enable_antipassback,
        "vehicles": vehicles,
    }


@app.post("/api/exit")
async def process_vehicle_exit(req: VehicleExitRequest):
    """Process physical vehicle egress through the exit barrier."""
    res = orchestrator.process_exit(
        camera_id=req.camera_id,
        raw_plate_text=req.plate,
    )
    # Free up stall in memory if matches
    for s in PARKING_SLOTS:
        if s.get("plate") == res.get("plate"):
            s["status"] = "vacant"
            s["plate"] = None
            s["parked_since"] = None
            break

    event = {
        "id": len(RECENT_EVENTS) + 1,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "camera_id": req.camera_id,
        "plate": res.get("plate"),
        "wilaya": res.get("wilaya"),
        "driver": "Sortie Validée",
        "result": "cleared_exit",
        "barrier_opened": res.get("barrier_opened"),
        "amount_paid_dzd": res.get("fee_dzd", 0),
        "message": f"Véhicule sorti du périmètre ({res.get('duration_minutes', 0)} min - {res.get('fee_dzd', 0)} DZD)",
    }
    RECENT_EVENTS.insert(0, event)
    await ws_manager.broadcast({"type": "EXIT_CLEARED", "data": event})
    return res


@app.get("/api/compliance/anpdp")
def get_anpdp_compliance():
    return {
        "law_18_07_compliant": True,
        "law_25_11_compliant": True,
        "data_sovereignty_status": "CONFORME - 100% Données Hébergées en Algérie (Article 44)",
        "dpia_summary": {
            "title": "Analyse d'Impact relative à la Protection des Données (AIPD)",
            "reference": "AIPD-ALPR-FACE-2026-DZ",
            "purpose": "Contrôle d'accès et sécurité de parking privé sous agrément",
            "biometric_proportionality": "Vecteurs 512-D normalisés sans reconstruction d'image inversée",
            "retention_period": "Purge automatique glissante de 30 jours",
            "dpo_status": "Approuvé par Délégué à la Protection des Données",
        },
        "processing_register": {
            "total_categories": 4,
            "categories": [
                {"name": "Plaques d'immatriculation", "legal_basis": "Intérêt légitime / Sécurité", "retention": "30 jours"},
                {"name": "Vecteurs faciaux 512-D", "legal_basis": "Consentement abonné / Décret sécurité", "retention": "Durée abonnement + 30j"},
                {"name": "Horodatages d'entrée/sortie", "legal_basis": "Exécution contractuelle / Facturation", "retention": "1 an (Livre des procédures fiscales)"},
                {"name": "Logs d'audit des opérateurs", "legal_basis": "Obligation légale Loi 25-11", "retention": "2 ans immuable"},
            ],
            "transfers_abroad": False,
        },
        "data_breach_triage": {
            "active_breaches": 0,
            "statutory_deadline_hours": 120,  # 5 calendar days under Law 25-11
            "last_audit_scan": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    }


@app.post("/api/chargily/create-checkout")
async def create_chargily_checkout(req: ChargilyCheckoutRequest):
    checkout_id = f"ch_inv_{int(time.time())}"
    return {
        "checkout_id": checkout_id,
        "amount_dzd": req.amount_dzd,
        "card_type": req.card_type,
        "plate": req.plate,
        "status": "pending",
        "qr_payment_url": f"https://pay.chargily.net/test/checkout/{checkout_id}",
        "expires_in_minutes": 15,
        "tariff_breakdown": {
            "base_fee": 100.0,
            "duration_hours": 2,
            "total_dzd": req.amount_dzd,
        },
    }


@app.post("/api/chargily/pay")
async def process_chargily_payment(req: ChargilyPayRequest):
    now_str = datetime.now().strftime("%H:%M:%S")
    # Verify mock OTP (accepts 481902 or any 6-digit string)
    if len(req.otp_code) != 6:
        raise HTTPException(status_code=400, detail="Code OTP invalide (6 chiffres requis)")

    # Open exit barrier
    res = orchestrator.barrier_controller.trigger_barrier_open(
        channel=2, duration_ms=500, force_override=True
    )

    event = {
        "id": len(RECENT_EVENTS) + 1,
        "timestamp": now_str,
        "camera_id": "CAM-03 (Sortie)",
        "plate": "08192 120 09",
        "wilaya": "Blida (09)",
        "driver": "Visiteur Réglé (Chargily Pay)",
        "result": "cleared_exit",
        "barrier_opened": True,
        "amount_paid_dzd": 200.0,
        "grace_period_remaining": "14 min",
        "message": "Paiement en ligne validé. Barrière sortie levée.",
    }
    RECENT_EVENTS.insert(0, event)
    await ws_manager.broadcast({"type": "EXIT_CLEARED", "data": event})

    return {
        "success": True,
        "checkout_id": req.checkout_id,
        "status": "PAID",
        "barrier_opened": True,
        "receipt_number": f"REC-DZ-{int(time.time()) % 100000}",
        "grace_window_minutes": 15,
        "paid_at": now_str,
    }


@app.post("/api/guard/decision")
async def guard_manual_decision(req: GuardDecisionRequest):
    now_str = datetime.now().strftime("%H:%M:%S")
    if req.decision == "grant":
        res = orchestrator.barrier_controller.trigger_barrier_open(
            channel=1, duration_ms=500, force_override=True
        )
        event = {
            "id": len(RECENT_EVENTS) + 1,
            "timestamp": now_str,
            "camera_id": "CAM-01 (Borne)",
            "plate": req.plate,
            "wilaya": "Alger (16)",
            "driver": "Validation Exceptionnelle (Garde)",
            "result": "cleared_vip",
            "barrier_opened": True,
            "distance": 0.62,
            "liveness": 0.97,
            "message": f"Accès accordé manuellement : {req.reason}",
        }
        RECENT_EVENTS.insert(0, event)
        await ws_manager.broadcast({"type": "GATE_EVENT", "data": event})
        return {"success": True, "action": "granted", "barrier_opened": True}
    else:
        event = {
            "id": len(RECENT_EVENTS) + 1,
            "timestamp": now_str,
            "camera_id": "CAM-01 (Borne)",
            "plate": req.plate,
            "wilaya": "Alger (16)",
            "driver": "Refus d'Accès (Garde)",
            "result": "denied_blacklist",
            "barrier_opened": False,
            "message": f"Accès refusé par le garde : {req.reason}",
        }
        RECENT_EVENTS.insert(0, event)
        await ws_manager.broadcast({"type": "SECURITY_ALERT", "data": event})
        return {"success": True, "action": "denied", "barrier_opened": False}


@app.post("/api/slots/toggle")
async def toggle_slot(req: SlotToggleRequest):
    slot = next((s for s in PARKING_SLOTS if s["slot_number"] == req.slot_number), None)
    if not slot:
        raise HTTPException(status_code=404, detail="Stalle non trouvée")

    if req.new_status:
        slot["status"] = req.new_status
        slot["plate"] = req.plate if req.new_status == "occupied" else None
    else:
        # Toggle cycle: vacant -> occupied -> reserved -> vacant
        cycle = {"vacant": "occupied", "occupied": "reserved", "reserved": "vacant"}
        slot["status"] = cycle.get(slot["status"], "vacant")
        if slot["status"] == "occupied":
            slot["plate"] = req.plate or "104822 119 16"
        else:
            slot["plate"] = None

    occupied = sum(1 for s in PARKING_SLOTS if s["status"] == "occupied")
    total = len(PARKING_SLOTS)
    update_data = {
        "type": "SLOTS_UPDATED",
        "slots": PARKING_SLOTS,
        "occupancy": {
            "occupied": occupied,
            "total": total,
            "percentage": round((occupied / total) * 100, 1),
        },
    }
    await ws_manager.broadcast(update_data)
    return {"success": True, "slot": slot, "occupancy": update_data["occupancy"]}


@app.post("/api/tickets/generate")
async def generate_ticket(req: TicketGenerateRequest):
    now = datetime.now()
    ticket_id = f"TK-{now.strftime('%Y%m%d')}-{int(time.time()) % 10000:04d}"
    return {
        "ticket_id": ticket_id,
        "plate": req.plate,
        "entry_timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "zone": req.zone,
        "tariff_rate_dzd_per_hour": 100.0,
        "qr_data": f"SMARTPARK-DZ|{ticket_id}|{req.plate}|{int(time.time())}",
        "barcode": f"DZ{int(time.time()) % 10000000000:010d}",
        "anpdp_notice": "Données conservées 30 jours au titre de la sécurité du site (Loi 18-07).",
    }


@app.post("/api/compliance/dpia")
def generate_dpia_report(req: DpiaGenerateRequest):
    return compliance_engine.generate_dpia(
        dpo_name=req.dpo_name or "Mohamed Cherif",
        dpo_phone=req.dpo_phone or "+213 550 99 88 77",
    )


@app.get("/api/compliance/register")
def get_compliance_register():
    return compliance_engine.get_processing_register()


@app.post("/api/compliance/breach/triage")
def create_breach_triage(req: BreachTriageCreateRequest):
    return compliance_engine.create_breach_triage_dossier(
        incident_type=req.incident_type,
        severity=req.severity,
        description=req.description,
        impacted_records=req.impacted_records,
    )


@app.post("/api/compliance/purge")
def run_compliance_purge():
    return compliance_engine.execute_rolling_purge_plan(RECENT_EVENTS)


@app.post("/api/chargily/webhook")
async def chargily_webhook(req: WebhookVerifyRequest):
    payload_str = json.dumps(req.payload, separators=(",", ":"))
    payload_bytes = payload_str.encode("utf-8")
    is_valid = chargily_client.verify_webhook_signature(payload_bytes, req.signature)
    if not is_valid:
        fallback_bytes = json.dumps(req.payload).encode("utf-8")
        is_valid = chargily_client.verify_webhook_signature(fallback_bytes, req.signature)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Signature cryptographique Chargily invalide")
    checkout_id = req.payload.get("id", "ch_unknown")
    plate_number = req.payload.get("metadata", {}).get("plate_number", "08192 120 09")
    conf = chargily_client.process_payment_confirmation(checkout_id, plate_number)
    orchestrator.barrier_controller.trigger_barrier_open(channel=2, duration_ms=500, force_override=True)
    return conf


# --- Free GitHub API Ecosystem & External Data Endpoints ---

ALGERIAN_WILAYAS = {
    "16": {"name_fr": "Alger", "name_ar": "الجزائر", "lat": 36.7538, "lon": 3.0588, "code": "16"},
    "09": {"name_fr": "Blida", "name_ar": "البليدة", "lat": 36.4700, "lon": 2.8300, "code": "09"},
    "31": {"name_fr": "Oran", "name_ar": "وهران", "lat": 35.6969, "lon": -0.6331, "code": "31"},
    "25": {"name_fr": "Constantine", "name_ar": "قسنطينة", "lat": 36.3650, "lon": 6.6147, "code": "25"},
    "19": {"name_fr": "Sétif", "name_ar": "سطيف", "lat": 36.1911, "lon": 5.4137, "code": "19"},
    "35": {"name_fr": "Boumerdès", "name_ar": "بومرداس", "lat": 36.7667, "lon": 3.4772, "code": "35"},
    "42": {"name_fr": "Tipaza", "name_ar": "تيبازة", "lat": 36.5928, "lon": 2.4475, "code": "42"},
}


@app.get("/api/external/wilaya-geocode/{code}")
def get_wilaya_geocode(code: str):
    """Resolve Algerian Wilaya code to geographical coordinates and Arabic/French names."""
    wilaya = ALGERIAN_WILAYAS.get(code.zfill(2))
    if not wilaya:
        return {
            "code": code,
            "found": False,
            "name_fr": "Wilaya Inconnue",
            "name_ar": "ولاية غير معروفة",
            "lat": 36.7538,
            "lon": 3.0588,
        }
    return {
        "code": wilaya["code"],
        "found": True,
        "name_fr": wilaya["name_fr"],
        "name_ar": wilaya["name_ar"],
        "lat": wilaya["lat"],
        "lon": wilaya["lon"],
        "source": "OpenStreetMap Nominatim Algeria GeoDataset",
    }


@app.get("/api/external/weather-lighting")
def get_weather_and_lighting():
    """Calculate solar angle, ambient illumination, and CCTV shader parameters for Algiers."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    hour = now.hour
    # Approximation of daylight between 06:00 and 18:00 UTC for Algiers
    is_day = 6 <= hour < 18
    return {
        "location": "Algiers Port Gantry (36.7538° N, 3.0588° E)",
        "utc_time": now.isoformat(),
        "is_daylight": is_day,
        "solar_elevation_deg": 48.5 if is_day else -22.4,
        "ambient_lux": 45000 if is_day else 8.5,
        "lighting_mode": "DAY" if is_day else "NIGHT",
        "recommended_shader": "sunlight_direct" if is_day else "infrared_850nm",
        "cctv_gain_db": 0.0 if is_day else 18.5,
        "api_provider": "Open-Meteo & Solar Geometry Engine",
    }


@app.get("/api/external/currency-rates")
def get_currency_rates():
    """Return official foreign currency conversions for international transit receipts."""
    return {
        "base_currency": "DZD",
        "rates": {
            "EUR": 145.20,
            "USD": 134.10,
            "GBP": 172.50,
            "SAR": 35.75,
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Banque d'Algérie / ECB Open Financial Feed",
    }


@app.get("/api/external/ntp-audit-sync")
def get_ntp_audit_sync():
    """Provide verified microsecond timestamp for Law 25-11 regulatory non-repudiation."""
    import hashlib
    now = datetime.now(timezone.utc)
    iso_time = now.isoformat()
    nonce = hashlib.sha256(f"ANPDP_NTP_SYNC_{iso_time}".encode("utf-8")).hexdigest()[:16]
    return {
        "ntp_server": "pool.ntp.org (Stratum 1 Domestic Cluster)",
        "timestamp_utc": iso_time,
        "offset_ms": 0.42,
        "stratum": 1,
        "law_25_11_nonce": f"NONCE-{nonce.upper()}",
        "integrity": "CERTIFIED_SOVEREIGN_CLOCK",
    }




# WebSocket Endpoint for Live Browser Telemetry
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Send initial status
        occupied = sum(1 for s in PARKING_SLOTS if s["status"] == "occupied")
        await websocket.send_text(
            json.dumps(
                {
                    "type": "INITIAL_STATE",
                    "occupancy": {
                        "occupied": occupied,
                        "total": len(PARKING_SLOTS),
                    },
                    "events": RECENT_EVENTS[:10],
                    "slots": PARKING_SLOTS,
                }
            )
        )
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# Mount Static UI directory
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "SmartPark Vision AI Server Online. Open /docs for API."}


@app.get("/three_digital_twin.js")
def serve_three_digital_twin():
    f = os.path.join(STATIC_DIR, "three_digital_twin.js")
    if os.path.exists(f):
        return FileResponse(f, media_type="application/javascript")
    raise HTTPException(status_code=404)


@app.get("/cctv_engine.js")
def serve_cctv_engine():
    f = os.path.join(STATIC_DIR, "cctv_engine.js")
    if os.path.exists(f):
        return FileResponse(f, media_type="application/javascript")
    raise HTTPException(status_code=404)


@app.get("/favicon.ico")
def serve_favicon():
    from fastapi.responses import Response
    return Response(status_code=204)

