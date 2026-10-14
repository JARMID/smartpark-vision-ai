# SmartPark Vision AI - Sovereign Edge Parking Access Platform

SmartPark Vision AI is an edge-first automated parking and security access management platform built for Algerian municipal and enterprise parking facilities. The system combines real-time computer vision, dual-spectrum biometric liveness verification, automated license plate recognition (ALPR), 3D WebGL digital twin spatial monitoring, and domestic e-payments via Chargily Pay V2.

Live Production URL: https://smartpark-vision-ai.vercel.app

---

## Key Capabilities

1. **High-Accuracy Algerian ALPR Engine:**
   - Detects standard alphanumeric plates (e.g., `104822 119 16`, `08192 120 09`) and temporary transit plates (`00` series, e.g., `08412 00 16`).
   - YOLOv11 vehicle localization paired with PaddleOCR character extraction.
   - Wilaya code validation across all 58 Algerian wilayas.

2. **Dual-Spectrum Biometric Access Kiosk:**
   - 512-dimensional facial embeddings via ArcFace with sub-second vector comparison against FAISS indexed whitelists.
   - Dual-spectrum anti-spoofing via MiniFASNet and 850nm Near-Infrared (NIR) dermal reflectance analysis.
   - Remote photoplethysmography (rPPG) pulse signal detection to reject printed photo cards and video replay attacks.

3. **Multi-Camera CCTV Matrix (V3.2):**
   - **CAM-01 (Voie 1 Entry ALPR):** High-angle architectural perspective showing the entry lane, barrier pedestal, guard booth, portal canopy, and real-time detection bounding boxes.
   - **CAM-02 (Biometric Access Kiosk):** Close-up driver view through the vehicle window, maintaining 100% spatial continuity with CAM-01, with a live 850nm NIR thermal/luminescence picture-in-picture window.
   - **CAM-03 (Voie 2 Exit ALPR & Toll Barrier):** Exit lane perspective with dual inductive loops, flashing orange barrier pedestal, and articulated barrier arm.
   - **CAM-04 (Zone A & B Deck Overview):** Overhead tactical CCTV feed with ceiling-mounted ultrasonic guidance pucks synchronized with live stall data.
   - **Live 1080p Inspector Modal:** Expand any camera feed into an HD mirror view with hardware decoding telemetry.

4. **Day and Night Mode Parity:**
   - Full dual-theme palette across the dashboard shell, 3D WebGL Three.js digital twin, 2D tactical CAD blueprint, and all 4 camera canvas feeds.

5. **Trilingual Localization (FR / EN / AR RTL):**
   - Seamless one-click switching between French, English, and Arabic.
   - Authentic right-to-left (RTL) layout direction and Arabic typography.

6. **Domestic Algerian Fintech Integration:**
   - Direct checkout integration with Chargily Pay V2 for EDAHABIA and CIB debit cards.
   - Automated 15-minute exit grace window calculation upon payment validation.

7. **Regulatory Compliance (Algerian Law 18-07 & Law 25-11):**
   - Strict edge-isolated database partitioning under the `smartpark` schema.
   - 5-day ANPDP security breach triage protocol.
   - Automated 30-day rolling log purge to prevent unauthorized data accumulation.

---

## Architecture and Technology Stack

* **Backend:** FastAPI (Python 3.12), FAISS (Facebook AI Similarity Search), Uvicorn, WebSockets.
* **Computer Vision:** YOLOv11, PaddleOCR, ArcFace, MiniFASNet.
* **Frontend:** Vanilla HTML5 Canvas (CCTV rendering engine), Three.js (3D WebGL Digital Twin), Tailwind CSS, Lucide Icons.
* **Cloud & Edge:** Vercel Serverless (Production Cloud), Local Edge Daemon (`http://127.0.0.1:8080`).
* **Testing:** Python `unittest` (66 unit and integration test cases), Playwright (headless browser verification across themes and locales).

---

## Getting Started

### Prerequisites

* Python 3.10+
* Node.js 18+ (for Vercel deployment or testing tools)

### Installation

```bash
git clone https://github.com/JARMID/smartpark-vision-ai.git
cd smartpark-vision-ai
pip install -r requirements.txt
```

### Running Locally

```bash
python run_demo.py
```

The application will be available at `http://127.0.0.1:8080`.

### Running Tests

Execute the backend test suite:

```bash
python -m unittest discover -s tests
```

Execute the Playwright end-to-end browser test:

```bash
python tests/test_ui_playwright.py
```

---

## Repository Structure

```
smartpark-vision-ai/
├── api/                  # Vercel serverless entrypoints
├── public/               # Production frontend web assets
│   ├── index.html        # Main dashboard and user interface
│   └── cctv_engine.js    # Canvas-based CCTV simulation engine (V3.2)
├── src/                  # Core Python modules
│   ├── alpr_engine.py    # Plate detection, OCR, and Algerian wilaya parser
│   ├── biometric_engine.py # ArcFace embedding and anti-spoof verification
│   ├── compliance.py     # Law 18-07 and Law 25-11 compliance engine
│   ├── server.py         # FastAPI routes, WebSockets, and state store
│   └── chargily_client.py# Chargily Pay V2 integration
├── static/               # Local daemon static mirrors
├── tests/                # Automated test suite (66 unit tests + Playwright)
├── requirements.txt      # Python dependencies
├── vercel.json           # Vercel cloud deployment configuration
└── README.md             # Project documentation
```

---

## License

This project is licensed under the MIT License.
