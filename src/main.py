"""
SmartPark Vision AI - Core Edge Gate Orchestrator.
Coordinates the Algerian License Plate Parser, Anti-Spoofing Gate, In-Memory FAISS Vector Index,
Local SQLite Write-Ahead Queue, and Modbus Barrier Gate Relay.
"""

from enum import Enum
import json
import time
from typing import Dict, Optional, Any
import numpy as np

from src.alpr.algerian_plate_parser import AlgerianPlateParser, PlateType
from src.face.ram_vector_index import RamVectorIndex, MatchDecision
from src.sync.sqlite_buffer import SqliteBufferQueue
from src.barrier.modbus_controller import ModbusBarrierController


class GateDecisionResult(str, Enum):
    CLEARED_VIP = "cleared_vip"
    CLEARED_VISITOR = "cleared_visitor"
    DENIED_SPOOF = "denied_spoof"
    DENIED_BLACKLIST = "denied_blacklist"
    DENIED_ANTIPASSBACK = "denied_antipassback"
    ALERT_CLONE_PLATE = "alert_clone_plate"
    HOLD_GUARD_REVIEW = "hold_guard_review"
    INVALID_PLATE = "invalid_plate"


class GateOrchestrator:
    """
    Primary on-premise orchestrator for automated parking access control.
    Executes sub-250ms decisions completely offline.
    Includes Anti-Passback and Duplicate / Cloned License Plate detection.
    """

    def __init__(
        self,
        db_path: str = "edge_buffer.db",
        modbus_host: str = "192.168.10.200",
        modbus_port: int = 502,
        simulation_mode: bool = True,
        liveness_threshold: float = 0.60,
        enable_antipassback: bool = True,
    ):
        self.plate_parser = AlgerianPlateParser()
        self.vector_index = RamVectorIndex(dimension=512, match_threshold=0.52, resample_upper_bound=0.55)
        self.buffer_queue = SqliteBufferQueue(db_path=db_path)
        self.barrier_controller = ModbusBarrierController(
            host=modbus_host, port=modbus_port, simulation_mode=simulation_mode
        )
        self.liveness_threshold = liveness_threshold
        self.enable_antipassback = enable_antipassback
        # In-memory registry tracking vehicles currently inside the perimeter (key = cleaned plate digits)
        self.active_inside_vehicles: Dict[str, Dict[str, Any]] = {}

    def enroll_subscriber(
        self,
        person_id: str,
        full_name: str,
        plate_raw: str,
        plate_formatted: str,
        face_embedding: np.ndarray,
        is_blacklisted: bool = False,
    ):
        """Enroll an authorized tenant, employee, or VIP into the local in-memory caches."""
        self.vector_index.enroll(
            person_id=person_id,
            full_name=full_name,
            embedding=face_embedding,
            is_blacklisted=is_blacklisted,
        )
        self.buffer_queue.update_cached_whitelist(
            [
                {
                    "plate_raw": plate_raw,
                    "plate_formatted": plate_formatted,
                    "person_id": person_id,
                    "is_blacklisted": 1 if is_blacklisted else 0,
                }
            ]
        )

    def register_active_vehicle(
        self,
        plate_raw: str,
        slot_number: Optional[str] = None,
        driver_name: Optional[str] = None,
        is_vip: bool = False,
    ):
        """Seed or record an already parked vehicle into the in-memory anti-passback registry."""
        parsed = self.plate_parser.parse(plate_raw)
        digits = "".join(filter(str.isdigit, parsed.formatted if parsed.is_valid else plate_raw))
        self.active_inside_vehicles[digits] = {
            "plate": parsed.formatted if parsed.is_valid else plate_raw,
            "cleaned_digits": digits,
            "entry_timestamp": time.time(),
            "entry_camera": "initial_seed",
            "slot_number": slot_number or "Zone A",
            "driver_name": driver_name,
            "is_vip": is_vip,
        }

    def process_arrival(
        self,
        camera_id: str,
        raw_plate_text: str,
        plate_confidence: float,
        face_embedding: Optional[np.ndarray] = None,
        liveness_score: float = 1.0,
        snapshot_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a vehicle arrival event through the complete decision pipeline.
        Returns the operational action and enqueues telemetry for synchronization.
        """
        start_ts = time.time()

        # Step 1: Parse and validate the Algerian License Plate
        parsed_plate = self.plate_parser.parse(raw_plate_text)
        if not parsed_plate.is_valid:
            elapsed_ms = (time.time() - start_ts) * 1000.0
            self.buffer_queue.enqueue_event(
                camera_id=camera_id,
                plate_number=raw_plate_text,
                ocr_confidence=plate_confidence,
                action_taken="denied_invalid_plate",
                snapshot_path=snapshot_path,
            )
            return {
                "result": GateDecisionResult.INVALID_PLATE,
                "barrier_opened": False,
                "latency_ms": elapsed_ms,
                "error": parsed_plate.error_message,
            }

        # Step 2: Anti-Spoofing and Liveness Verification
        if liveness_score < self.liveness_threshold:
            elapsed_ms = (time.time() - start_ts) * 1000.0
            self.buffer_queue.enqueue_event(
                camera_id=camera_id,
                plate_number=parsed_plate.formatted,
                ocr_confidence=plate_confidence,
                driver_detected=True,
                action_taken="denied_spoof_detected",
                snapshot_path=snapshot_path,
            )
            return {
                "result": GateDecisionResult.DENIED_SPOOF,
                "barrier_opened": False,
                "latency_ms": elapsed_ms,
                "message": "Presentation attack detected by MiniFASNet anti-spoofing engine.",
            }

        # Step 3: Anti-Passback & Duplicate / Cloned Plate Detection Gate
        cleaned_digits = "".join(filter(str.isdigit, parsed_plate.formatted))
        if self.enable_antipassback and cleaned_digits in self.active_inside_vehicles:
            prior_entry = self.active_inside_vehicles[cleaned_digits]
            elapsed_ms = (time.time() - start_ts) * 1000.0
            duration_sec = time.time() - prior_entry.get("entry_timestamp", time.time())
            duration_min = max(0, int(duration_sec // 60))
            slot_info = prior_entry.get("slot_number", "Intérieur Parking")

            self.buffer_queue.enqueue_event(
                camera_id=camera_id,
                plate_number=parsed_plate.formatted,
                ocr_confidence=plate_confidence,
                driver_detected=True,
                action_taken="denied_antipassback_clone_plate",
                snapshot_path=snapshot_path,
            )

            return {
                "result": GateDecisionResult.DENIED_ANTIPASSBACK,
                "barrier_opened": False,
                "latency_ms": elapsed_ms,
                "plate": parsed_plate.formatted,
                "wilaya": parsed_plate.wilaya_name,
                "error_code": "CLONED_PLATE_OR_DOUBLE_ENTRY_VIOLATION",
                "message": (
                    f"ALERTE SÉCURITÉ: Le véhicule {parsed_plate.formatted} est déjà enregistré à l'intérieur "
                    f"du parking (Emplacement {slot_info}, présent depuis {duration_min} min). "
                    f"Refus pour suspicion de plaque clonée ou tentative de double passage (Anti-Passback)."
                ),
                "prior_entry": prior_entry,
            }

        # Step 4: Check Local Whitelist Cache
        cached_vehicle = self.buffer_queue.check_plate_in_cache(cleaned_digits)

        # Step 5: Facial Vector Search
        face_search_res = None
        if face_embedding is not None:
            face_search_res = self.vector_index.search(face_embedding)

        # Step 6: Watchlist / Blacklist Alert Priority
        if (cached_vehicle and cached_vehicle["is_blacklisted"]) or (
            face_search_res and face_search_res.decision == MatchDecision.BLACKLIST_HIT
        ):
            elapsed_ms = (time.time() - start_ts) * 1000.0
            self.buffer_queue.enqueue_event(
                camera_id=camera_id,
                plate_number=parsed_plate.formatted,
                ocr_confidence=plate_confidence,
                driver_detected=True,
                matched_person_id=face_search_res.person_id if face_search_res else None,
                face_cosine_distance=face_search_res.cosine_distance if face_search_res else None,
                action_taken="denied_blacklisted",
                snapshot_path=snapshot_path,
            )
            return {
                "result": GateDecisionResult.DENIED_BLACKLIST,
                "barrier_opened": False,
                "latency_ms": elapsed_ms,
                "message": "Access denied: Entity flagged on security watchlist.",
            }

        # Step 7: Whitelisted VIP / Subscriber Clearance
        if (
            cached_vehicle
            and not cached_vehicle["is_blacklisted"]
            and face_search_res
            and face_search_res.decision == MatchDecision.MATCH
        ):
            # Actuate barrier gate relay (<250ms target)
            trigger_res = self.barrier_controller.trigger_barrier_open(channel=1, duration_ms=500)
            elapsed_ms = (time.time() - start_ts) * 1000.0

            # Record in active inside registry for anti-passback tracking
            self.active_inside_vehicles[cleaned_digits] = {
                "plate": parsed_plate.formatted,
                "cleaned_digits": cleaned_digits,
                "entry_timestamp": time.time(),
                "entry_camera": camera_id,
                "person_id": face_search_res.person_id,
                "driver_name": face_search_res.full_name,
                "is_vip": True,
            }

            self.buffer_queue.enqueue_event(
                camera_id=camera_id,
                plate_number=parsed_plate.formatted,
                ocr_confidence=plate_confidence,
                driver_detected=True,
                matched_person_id=face_search_res.person_id,
                face_cosine_distance=face_search_res.cosine_distance,
                action_taken="auto_cleared",
                snapshot_path=snapshot_path,
            )

            return {
                "result": GateDecisionResult.CLEARED_VIP,
                "barrier_opened": trigger_res.success,
                "person_id": face_search_res.person_id,
                "full_name": face_search_res.full_name,
                "plate": parsed_plate.formatted,
                "wilaya": parsed_plate.wilaya_name,
                "face_distance": face_search_res.cosine_distance,
                "latency_ms": elapsed_ms,
            }

        # Step 8: Unregistered Public Visitor Entry
        # Standard or temporary 00 plate with live driver -> Issue entry QR ticket
        trigger_res = self.barrier_controller.trigger_barrier_open(channel=1, duration_ms=500)
        elapsed_ms = (time.time() - start_ts) * 1000.0
        ticket_code = f"QR-{int(time.time())}-{cleaned_digits[:6]}"

        # Record in active inside registry for anti-passback tracking
        self.active_inside_vehicles[cleaned_digits] = {
            "plate": parsed_plate.formatted,
            "cleaned_digits": cleaned_digits,
            "entry_timestamp": time.time(),
            "entry_camera": camera_id,
            "person_id": None,
            "driver_name": "Visiteur Public",
            "is_vip": False,
            "ticket_code": ticket_code,
        }

        self.buffer_queue.enqueue_event(
            camera_id=camera_id,
            plate_number=parsed_plate.formatted,
            ocr_confidence=plate_confidence,
            driver_detected=True,
            action_taken="cleared_visitor",
            snapshot_path=snapshot_path,
        )

        return {
            "result": GateDecisionResult.CLEARED_VISITOR,
            "barrier_opened": trigger_res.success,
            "plate": parsed_plate.formatted,
            "wilaya": parsed_plate.wilaya_name,
            "ticket_qr": ticket_code,
            "latency_ms": elapsed_ms,
        }

    def process_exit(
        self,
        camera_id: str,
        raw_plate_text: str,
        plate_confidence: float = 0.98,
        snapshot_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a vehicle exit event.
        Releases vehicle from the active inside registry and actuates the exit barrier.
        """
        start_ts = time.time()
        parsed_plate = self.plate_parser.parse(raw_plate_text)
        if not parsed_plate.is_valid:
            elapsed_ms = (time.time() - start_ts) * 1000.0
            return {
                "result": GateDecisionResult.INVALID_PLATE,
                "barrier_opened": False,
                "latency_ms": elapsed_ms,
                "error": parsed_plate.error_message,
            }

        cleaned_digits = "".join(filter(str.isdigit, parsed_plate.formatted))
        was_inside = cleaned_digits in self.active_inside_vehicles
        prior = self.active_inside_vehicles.pop(cleaned_digits, None)

        trigger_res = self.barrier_controller.trigger_barrier_open(channel=2, duration_ms=500)
        elapsed_ms = (time.time() - start_ts) * 1000.0

        entry_ts = prior.get("entry_timestamp", time.time() - 3600) if prior else (time.time() - 3600)
        duration_sec = time.time() - entry_ts
        duration_min = max(1, int(duration_sec // 60))

        is_vip = prior.get("is_vip", False) if prior else False
        fee_dzd = 0 if is_vip else max(100, int((duration_min / 60) * 100))

        self.buffer_queue.enqueue_event(
            camera_id=camera_id,
            plate_number=parsed_plate.formatted,
            ocr_confidence=plate_confidence,
            action_taken="cleared_exit",
            snapshot_path=snapshot_path,
        )

        return {
            "result": "cleared_exit",
            "barrier_opened": trigger_res.success,
            "plate": parsed_plate.formatted,
            "wilaya": parsed_plate.wilaya_name,
            "duration_minutes": duration_min,
            "fee_dzd": fee_dzd,
            "is_vip": is_vip,
            "was_registered_inside": was_inside,
            "latency_ms": elapsed_ms,
        }

    def close(self):
        """Release database connections."""
        self.buffer_queue.close()


if __name__ == "__main__":
    print("SmartPark Vision AI - Local Edge Orchestrator Initialized.")
    orchestrator = GateOrchestrator(simulation_mode=True)
    res = orchestrator.process_arrival(
        camera_id="cam-01",
        raw_plate_text="104822 119 16",
        plate_confidence=0.98,
        liveness_score=0.99,
    )
    print("Sample Execution Result:", res)
    orchestrator.close()
