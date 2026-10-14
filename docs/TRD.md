# Technical Requirements Document (TRD)
## SmartPark Vision AI: Architecture and Engineering Specification (V2.0)

## 1. System Architecture Overview

SmartPark Vision AI adopts a decentralized, sovereign hybrid edge-cloud architecture. High-frequency video decoding, neural inference, anti-spoofing, vector search, and barrier actuation execute locally on the on-premise edge gateway, while configuration management, reporting, long-term storage, and compliance registers operate on a self-hosted Supabase instance deployed on domestic Algerian sovereign infrastructure.

```
                    ON-PREMISE EDGE GATEWAY (Per Facility)
┌────────────────────────────────────────────────────────────────────────┐
│  [IP Cameras: RTSP / ONVIF over Camera VLAN]                           │
│    ├── Entry Gate (ALPR Bullet + CPL Driver Kiosk Camera + 850nm NIR)  │
│    ├── Exit Gate (ALPR Bullet + Driver Camera)                         │
│    └── Zone / Stalls (Wide Angle Occupancy Overhead Cameras)           │
│                  │                                                     │
│                  ▼                                                     │
│  [MediaMTX / go2rtc (RTSP Ingestion & WebRTC Re-streamer)]             │
│                  │                                                     │
│                  ▼                                                     │
│  [Edge Inference Engine (Python / TensorRT / CUDA 12.6)]               │
│    ├── Vehicle & Plate Detector (YOLOv11n-plate)                       │
│    ├── Bilinear Perspective Rectification (OpenCV)                     │
│    ├── Algerian OCR Parser (PaddleOCR / Fast-Plate-OCR)                │
│    │     └── Validates 1 to 6 digit serials, 00 & 3-digit codes, 01-58 │
│    ├── Local Sovereign VLM Fallback (Qwen2.5-VL-3B INT4 on GPU)        │
│    ├── Face Detector (SCRFD-10G)                                       │
│    ├── Liveness / Anti-Spoofing (MiniFASNet - 3ms on GPU)              │
│    ├── Feature Extractor (ArcFace 512-D float32)                       │
│    └── LOCAL RAM 1:N MATCHING (FAISS / sqlite-vec in RAM: <1ms)        │
│                  │                                                     │
│                  ├──────────────────────────────┐                      │
│                  ▼                              ▼                      │
│  [Barrier Controller Service]         [Local SQLite Buffer Queue]      │
│    └── Ethernet Relay / Modbus TCP              │                      │
│    └── Barrier Gate (BFT / CAME / FAAC)        │                      │
└─────────────────────────────────────────────────┼──────────────────────┘
                                                  │ (HTTPS / WSS Domestic Link)
                                                  ▼
             SOVEREIGN CLOUD MANAGEMENT PLANE (Self-Hosted Supabase)
                 (Algérie Télécom Data Center / Domestic Cloud)
┌────────────────────────────────────────────────────────────────────────┐
│  [Self-Hosted Supabase Services (Docker Compose on Linux)]             │
│    ├── PostgreSQL 16 + pgvector (HNSW Index for Central Sync)          │
│    ├── Supabase Realtime (WebSocket Dispatch to Control Room)          │
│    ├── MinIO / Supabase Storage (Encrypted Crops, 30-Day Purge)        │
│    └── Supabase Auth & Multi-Tenant Row Level Security (RLS)           │
│                                                                        │
│  [Law 18-07 & Law 25-11 Compliance Registers]                         │
│    ├── Data Protection Impact Assessment (DPIA) Engine                 │
│    ├── Register of Processing Activities (Automated Sync)              │
│    └── 5-Day Data Breach Notification Triage Module                    │
│                                                                        │
│  [Web Management Dashboard (React 19 / Vite / Tailwind)]              │
│    ├── Live WebRTC Video Matrix (Sub-300ms)                            │
│    ├── Real-Time Event Stream with Liveness Badges                     │
│    ├── Parking Slot Occupancy Heatmap & Overstay Alerts                │
│    └── Subscriber & Billing Manager (Native Algerian Dinars DZD)       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Edge Vision Processing Pipeline

### 2.1 Video Ingestion and Stream Demuxing
* **Stream Protocols:** IP cameras deliver H.264 or H.265 video over RTSP at 1080p resolution (1920x1080) at 25 or 30 frames per second.
* **Stream Multiplexer:** The edge gateway runs `MediaMTX` (an open-source RTSP/WebRTC media server written in Go) or `go2rtc`. This service ingests camera feeds directly from the local camera VLAN, decodes video frames via NVIDIA NVDEC hardware acceleration, and publishes sub-300ms WebRTC streams for browser consumption.
* **Inference Sampling:** Motion detection and background subtraction sample frames at 6 to 10 FPS during active vehicle motion, scaling down to 1 FPS when the detection zone is idle.

### 2.2 License Plate Detection and OCR (Algerian Syntax Calibration)
1. **Detection:** YOLOv11 Nano or Small (`yolov11n.pt` converted to TensorRT FP16 `.engine`) locates the vehicle bounding box and plate coordinates.
2. **Deskew and Crop:** OpenCV extracts the quadrilateral polygon and applies a perspective warp to normalize the plate crop to a standard 240x80 pixel rectangle.
3. **Character Recognition:** The rectified crop passes to PaddleOCR v4 or Fast-Plate-OCR.
4. **Algerian Regex and Wilaya Validation Engine:**
   * Accepts 1 to 6 digits for the sequential registration block (`\d{1,6}`).
   * Accepts either standard 3-digit category/year codes (`\d{3}`) or temporary new vehicle codes (`00`).
   * Validates Wilaya codes strictly between `01` and `58`.
   * Parses diplomatic prefixes (`CD`, `CC`, `CMD`).
5. **Local Sovereign VLM Fallback:** If optical confidence is below 85%, or if a plate is partially obscured by dirt or damage, the frame is processed locally on the edge GPU by `Qwen2.5-VL-3B-Instruct` (quantized in INT4/AWQ via vLLM). This resolves the characters and identifies vehicle make, model, and color in ~400ms without sending any image data over the public internet.

### 2.3 Facial Recognition, Liveness, and Optics
1. **Camera Optics:** The driver kiosk camera is fitted with a Circular Polarizing Filter (CPL) to cut windshield glare and an 850nm Near-Infrared (NIR) floodlight to penetrate tinted glass without distracting drivers.
2. **Face Detection:** SCRFD-10G locates driver face coordinates and 5 facial keypoints in 4 milliseconds.
3. **Anti-Spoofing Gate:** MiniFASNet evaluates facial texture, depth gradients, and reflection to detect printed photos or smartphone screens. Spoofed presentations are blocked instantly (`denied_spoof_detected`).
4. **Feature Extraction:** ArcFace (ResNet50 backbone, quantized to TensorRT FP16) extracts a 512-dimensional normalized vector:
   `E = [e_1, e_2, ..., e_{512}]` where `||E||_2 = 1.0`.

---

## 3. Sub-Millisecond Local RAM Vector Matching

To achieve gate opening latency under 250 milliseconds, vector similarity matching never traverses an external network.

### 3.1 Local Edge FAISS Index
* **Index Configuration:** In-memory flat inner product index (`IndexFlatIP`) or HNSW index on the edge gateway.
* **Vector Sizing:** 10,000 enrolled profiles consume only 20.48 MB of RAM.
* **Search Execution:** Search execution across 10,000 vectors takes under 0.8 milliseconds on the Intel Core i5 CPU or the RTX 3060 GPU.
* **Calibrated Distance Thresholds:**
  $$\text{Cosine Distance} = 1 - \text{Cosine Similarity}$$
  * Barrier Gate Driver Clearance: Distance `<= 0.52` (Similarity `>= 0.48`), calibrated to accommodate through-windshield refraction and window tint.
  * Pedestrian Gate Turnstile: Distance `<= 0.40` (Similarity `>= 0.60`).
* **Synchronization:** Enrolled vector updates sync from the self-hosted Supabase database to the edge RAM index in the background via WebSocket subscriptions.

---

## 4. Barrier Gate and Hardware Controller Integration

### 4.1 Industrial Controller Protocols
* **Hardware Interface:** Ethernet-based relay module (e.g., Waveshare 8-Channel Modbus POE Relay) connected to the isolated Camera VLAN.
* **Actuation Pulse:** Sends a momentary 500ms pulse closing the barrier gate dry contact input:
  ```json
  POST /api/relay/open
  { "relay_channel": 1, "duration_ms": 500 }
  ```
* **Inductive Ground Loop Interlock:** The controller hardware interlock requires vehicle presence loop activation before firing the open pulse. The barrier cannot be triggered unless a physical vehicle is positioned in the lane.

---

## 5. Power Infrastructure and Electrical Protection

Commercial electrical lines in Algeria experience frequent voltage drops and micro-interruptions. The hardware bill of materials incorporates dedicated power conditioning:
* **Online Double-Conversion UPS:** Rated at 2kVA / 1800W with zero millisecond transfer time (0ms switch). The inverter constantly supplies pure sine wave power to the industrial PC, cameras, and barrier relays, isolating sensitive GPU hardware from grid spikes and sags.
* **Runtime:** Provides 45 to 60 minutes of operational runtime during total grid power loss.

---

## 6. Security and Network Architecture

### 6.1 Network Isolation and VLAN Topology
The on-premise installation enforces three isolated network zones:
1. **VLAN 10 (Camera Surveillance LAN):** Unrouted private subnet (`192.168.10.0/24`) housing IP cameras, NVRs, and Modbus barrier relays. No direct gateway access to the internet.
2. **Edge Gateway (Dual-Homed Node):** The machine features two physical Ethernet NICs. NIC 1 connects to VLAN 10 to ingest camera streams; NIC 2 connects to VLAN 20.
3. **VLAN 20 (Facility Uplink LAN):** Connects to the local network router, synchronizing encrypted telemetry with the self-hosted Supabase instance located in a domestic data center over TLS 1.3.

### 6.2 Data Sovereignty and Cryptographic Protection
* **Domestic Hosting:** Supabase runs in a secure Docker environment on an Algerian sovereign cloud provider (such as Algérie Télécom, Icosnet, or on-premise local server).
* **Law 18-07 Article 44 Compliance:** Zero personal data or biometrics are transmitted outside Algerian national territory.
* **Immutable Audit Trail:** All operator queries and administrative actions write cryptographic hash records to `compliance_audit_logs`.
