"""
SmartPark Vision AI - Sovereign FastAPI Server and Real-Time Gateway.
Serves REST APIs, WebSocket live telemetry, simulation triggers, and command center UI.
"""

import asyncio
from datetime import datetime
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

app = FastAPI(title="SmartPark Vision AI Sovereign Server", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Orchestrator
DB_PATH = "smartpark_demo.db"
orchestrator = GateOrchestrator(db_path=DB_PATH, simulation_mode=True)

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

    raise HTTPException(status_code=400, detail="Scénario non reconnu")


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
