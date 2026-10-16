# Implementation Plan and Execution Roadmap (V2.0)
## Smart Park (Algeria Commercial Production Edition)

## 1. Project Phasing and Realistic Timeline

Deploying an automated biometric and ALPR parking installation in Algeria requires accounting for physical barrier safety loops, electrical conditioning, and official ANPDP prior-authorization review cycles under Law 18-07 and Law 25-11.

While a single-lane software prototype can run in 30 days, commercial enterprise production readiness operates on a **60 to 90 day deployment lifecycle**:

```
[Phase 1: Days 1-14]   Edge Vision Engine, 6-Digit & '00' Plates, Anti-Spoofing
         │
[Phase 2: Days 15-30]  Hardware Controller, 2kVA UPS & Sovereign Supabase
         │
[Phase 3: Days 31-45]  Command Center Dashboard & Law 25-11 Compliance Modules
         │
[Phase 4: Days 46-75]  ANPDP Prior-Authorization Review & Optical Field Calibration
         │
[Phase 5: Days 76-90]  End-to-End Commissioning, Staff Training & Full Go-Live
```

---

## 2. Detailed Phase Breakdown

### Phase 1: Edge Vision Engine, Syntax Expansion & Anti-Spoofing (Days 1 to 14)
* **Objective:** Establish real-time video stream ingestion and achieve greater than 97% recognition accuracy across standard 6-digit Algerian plates, temporary `00` plates, and live faces.
* **Key Tasks:**
  1. Set up the local edge Python environment with PyTorch, CUDA 12.6, TensorRT, and OpenCV on the RTX 3060 PC.
  2. Configure `MediaMTX` to ingest test RTSP camera feeds and expose low-latency WebRTC endpoints.
  3. Deploy YOLOv11 plate detector (`yolov11n.pt`) and export to TensorRT FP16 engine.
  4. Integrate PaddleOCR v4 with the expanded Algerian regex engine accepting 1 to 6 digit serials, `00` temporary middle codes, and Wilaya codes `01` to `58`.
  5. Deploy MiniFASNet anti-spoofing model to detect printed photos and phone screen presentations.
  6. Deploy SCRFD-10G face detector and ArcFace ResNet50 feature extractor.
  7. Implement local in-memory FAISS flat inner-product vector index in RAM, verifying sub-millisecond search across 10,000 vectors.
* **Deliverable:** Working Python edge worker processing 30 FPS video streams with plate, face, and liveness extraction logged locally in sub-200ms.

---

### Phase 2: Hardware Controller, Power Conditioning & Sovereign Database (Days 15 to 30)
* **Objective:** Connect physical barrier gate relays, install power protection, and deploy self-hosted Supabase on domestic Algerian infrastructure.
* **Key Tasks:**
  1. Provision self-hosted Supabase (Docker Compose) on an Algerian sovereign cloud provider (Algérie Télécom, Icosnet, or on-premise local server) and apply `BACKEND_SCHEMA.sql`.
  2. Build the local SQLite write-ahead queue on the edge node for offline event buffering.
  3. Deploy the local sovereign VLM (`Qwen2.5-VL-3B-Instruct` INT4 quantized via vLLM) on the RTX 3060 for offline, zero-API-cost plate disambiguation.
  4. Install the **Online Double-Conversion UPS (2kVA / 1800W)** to protect the compute node, cameras, and relays from electrical grid spikes and cuts.
  5. Connect the Ethernet / Modbus TCP relay controller and wire the inductive vehicle presence loop interlock.
  6. Test the physical barrier actuation loop: ensure the barrier only opens when a vehicle is physically over the inductive loop.
* **Deliverable:** Verified end-to-end hardware loop with local power protection and domestic database synchronization.

---

### Phase 3: Operator Web Dashboard and Law 25-11 Modules (Days 31 to 45)
* **Objective:** Build the web management interface, mobile patrol views, and regulatory compliance tools.
* **Key Tasks:**
  1. Initialize the React 19 application using Vite, Tailwind CSS, and Lucide icons.
  2. Implement the live camera quad-view using WebRTC streams delivered by `MediaMTX`.
  3. Build the real-time event stream panel with liveness badges (`LIVE HUMAN` vs `SPOOF DETECTED`).
  4. Construct the interactive 2D parking stall occupancy map with overstay timers.
  5. Build the Law 25-11 compliance views: DPIA assessment viewer, Register of Processing Activities exporter, and the 5-day breach notification triage screen.
  6. Configure native billing displays in Algerian Dinars (DZD).
  7. Implement operator keyboard shortcuts (`Spacebar` to open, `B` to blacklist, `A` to approve).
* **Deliverable:** Fully functional web application accessible to security operators, facility managers, and the Data Protection Officer (DPO).

---

### Phase 4: Optical Field Calibration and ANPDP Regulatory Review (Days 46 to 75)
* **Objective:** On-site optical tuning and official regulatory prior-authorization processing.
* **Key Tasks:**
  1. Mount and align driver kiosk cameras with Circular Polarizing Filters (CPL) to cut windshield glare.
  2. Align 850nm Near-Infrared (NIR) illuminators to penetrate tinted windows without blinding drivers.
  3. Calibrate camera shutter speeds (1/500s to 1/1000s) for plate cameras.
  4. Compile and submit the formal ANPDP prior-authorization dossier under Law 18-07 and Law 25-11, including the DPIA report and security architecture documentation.
  5. Run 200 consecutive automated gate entries across varied lighting (direct sunlight, dusk, night headlights).
  6. Simulate WAN disconnects: verify 100% of whitelisted vehicles clear the barrier autonomously via edge RAM FAISS index.
* **Deliverable:** Validated optical installation and submitted ANPDP compliance file.

---

### Phase 5: Commercial Commissioning, Training and Go-Live (Days 76 to 90)
* **Objective:** Transition to full commercial production.
* **Key Tasks:**
  1. Conduct security operator and guard training on keyboard shortcuts and incident handling.
  2. Train facility management on DZD financial reconciliation and subscription pass creation.
  3. Train the Data Protection Officer (DPO) on the 5-day breach notification workflow and audit ledger reviews.
  4. Execute final security and penetration tests on the isolated Camera VLAN.
  5. Formal project sign-off and commercial go-live.
* **Deliverable:** Fully operational, legally compliant smart parking installation in production.

---

## 3. Risk Register and Mitigation Strategies

| Risk Description | Severity | Likelihood | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **ANPDP Regulatory Rejection (Cross-Border Transfer)** | Critical | Low | Zero foreign cloud transfers: self-hosted Supabase on domestic Algerian cloud + local Qwen2.5-VL on the edge GPU. |
| **Severe Windshield Glare / Tinted Glass** | High | High | Circular Polarizing Filters (CPL) + 850nm NIR illumination + calibrated ArcFace distance (`<= 0.52`). |
| **Grid Power Micro-Cuts and Voltage Drops** | High | High | Online Double-Conversion UPS (2kVA / 1800W) providing zero transfer time and 45-60 min runtime. |
| **Presentation Attacks / Photo Spoofing** | High | Medium | MiniFASNet anti-spoofing model intercepts printed photos and phone screen replays before embedding generation. |
| **Temporary 00 Plates Rejected at Gate** | Medium | High | Expanded regex engine accepts `00` middle codes and 6-digit serials natively without triggering manual review. |
| **Sub-250ms Latency Failure over WAN** | Critical | High | Vector matching executes 100% locally in edge RAM via FAISS (<0.8ms), decoupled from internet availability. |
