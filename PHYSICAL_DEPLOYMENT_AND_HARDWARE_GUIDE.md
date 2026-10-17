# Smart Park: Physical Deployment, Hardware Procurement, and Field Commissioning Guide

This guide details the physical hardware, external services, computer specifications, wiring schematics, and field testing protocols required to deploy the Smart Park platform in an operational parking facility.

---

## 1. System Architecture and Workstation Topologies

Smart Park operates across two physical deployment profiles depending on facility scale and security booth staffing:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PROFILE A: SINGLE INDUSTRIAL APPLIANCE (Recommended for Single-Lane / Compact Sites)   │
│   A single heavy-duty machine performs all tasks:                                      │
│   • Runs Edge Gateway API and multi-camera RTSP ingestion                              │
│   • Executes on-device ONNX computer vision models (YOLOv11, OCR, ArcFace, MiniFASNet) │
│   • Actuates Modbus TCP barrier gate relays over industrial Ethernet                   │
│   • Hosts the Operator Workstation and Cashier POS window for the booth attendant      │
│   • Controls the ESC/POS thermal ticket printer, barcode scanner gun, and cash drawer  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ PROFILE B: DUAL-PC DISTRIBUTED SETUP (Recommended for High-Traffic Multi-Lane Sites)   │
│   Separates central vision processing from the cashier desktop interface:              │
│   • PC 1 (Machine Room Server / Edge Node): Dedicated PC with NVIDIA GPU. Ingests RTSP │
│     video, runs AI inference, executes barrier control, and maintains the database.    │
│   • PC 2 (Guard Booth Station / POS Terminal): Standard office mini-PC or desktop.     │
│     Runs the desktop operator window, handles ticket payments, ESC/POS printing,       │
│     and cash drawer kicks. Connects to PC 1 over the local Gigabit switch.            │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

> **Why choose Profile B?** In high-traffic facilities, separating the machines prevents cashier desktop actions (accidental restarts, peripheral disconnections, or operating system updates) from disrupting real-time entry and exit barrier automation.

---

## 2. Computer Hardware Specifications: What to Buy

### 2.1 The Edge Processing Server (PC 1 or Profile A Single Box)

Do not use a standard consumer laptop for 24/7 parking automation. Acquire an industrial edge box or a robust desktop tower with dedicated cooling:

| Component | Minimum Specification | Recommended Specification | Purpose in Smart Park |
| :--- | :--- | :--- | :--- |
| **Processor (CPU)** | Intel Core i5 (12th Gen+) or AMD Ryzen 5 5600 (6 cores) | Intel Core i7 (13th/14th Gen) or AMD Ryzen 7 7700 (8+ cores) | RTSP video demuxing, SQLite buffering, WebSocket broadcasts |
| **Graphics (GPU)** | NVIDIA GeForce RTX 3050 (6GB/8GB) | **NVIDIA GeForce RTX 3060 12GB or RTX 4060 8GB** | TensorRT/CUDA acceleration for ALPR OCR and ArcFace embeddings (<20ms latency) |
| **Memory (RAM)** | 16 GB DDR4/DDR5 | **32 GB DDR4/DDR5** | Local FAISS vector index, 4-camera circular frame buffers |
| **Primary Storage** | 256 GB M.2 NVMe SSD | **512 GB M.2 NVMe SSD** | Operating system, Python runtime, SQLite WAL database |
| **Evidence Storage**| 1 TB SATA SSD | **2 TB Enterprise SATA SSD / WD Purple** | 30-day encrypted snapshot retention mandated by Algerian Law 18-07 |
| **Network Interfaces**| 1x Gigabit Ethernet | **Dual Gigabit Ethernet (2x RJ45 NICs)** | Physical network isolation: NIC 1 on Camera VLAN, NIC 2 on WAN/Office |
| **Operating System**| Windows 10/11 Pro 64-bit | **Windows 11 Pro 64-bit or Ubuntu 24.04 LTS** | Native Edge WebView2 execution for operator station |

### 2.2 The Guard Booth Terminal (PC 2 in Profile B Only)

If you separate the cashier station, the booth computer does not require a dedicated GPU:
* **Form Factor:** Mini-PC (such as Intel N100, ASUS NUC, or HP EliteDesk Mini).
* **Processor:** Intel Core i3 (12th Gen+) or Intel N100 / N200.
* **Memory:** 8 GB or 16 GB RAM.
* **Storage:** 256 GB NVMe SSD.
* **Ports:** Minimum 4x USB-A ports (thermal printer, barcode scanner gun, keyboard, mouse), 1x Gigabit Ethernet, HDMI/DisplayPort.
* **Operating System:** Windows 11 Pro 64-bit.

---

## 3. Peripheral Hardware & Facility Equipment Bill of Materials

### 3.1 Field Devices and Hardware Parts

All pricing estimates reflect Algiers commercial equipment and distributor rates:

| Item | Equipment Name | Exact Model / Specification Reference | Estimated Cost (DZD) |
| :--- | :--- | :--- | :--- |
| **1** | **Industrial Modbus Relay** | Waveshare 8-Channel Modbus TCP Ethernet POE Relay (Port 502) | ~14,000 DZD (~$100) |
| **2** | **ALPR Bullet Cameras (x2)** | 4MP Motorized Varifocal Bullet (5-50mm or 2.8-12mm), 1/1000s shutter, Optical WDR, ONVIF RTSP (Dahua IPC-HFW5442E or Hikvision DS-2CD7A46G0) | ~75,000 DZD (pair) |
| **3** | **Kiosk Face Camera (x1)** | 2MP Global Shutter Camera with 850nm NIR ring illuminator and CPL circular polarizing filter (eliminates windshield reflections) | ~40,000 DZD |
| **4** | **Deck Overview Camera (x1)** | 4MP Wide-Angle Dome Camera (2.8mm, IP67, IK10 vandal-proof) | ~14,000 DZD |
| **5** | **Managed PoE+ Switch** | 8-Port Gigabit Managed PoE+ Switch (802.3at, 120W power budget, VLAN support, e.g. Dahua or TP-Link Omada) | ~22,000 DZD |
| **6** | **Online Double-Conversion UPS**| 2kVA / 1800W Online UPS with pure sine wave inverter and USB telemetry (APC Smart-UPS or Riello Vision) | ~125,000 DZD |
| **7** | **Thermal Receipt Printer** | 80mm ESC/POS Thermal Printer with auto-cutter, USB + Ethernet, 260mm/s (Epson TM-T20III or Xprinter XP-N160II) | ~20,000 DZD |
| **8** | **2D Barcode Scanner Gun** | Handheld USB HID Barcode Reader with stand, auto-sensing trigger, reads QR and Code-128 off phone screens (Honeywell or Netum) | ~9,000 DZD |
| **9** | **Heavy-Duty Cash Drawer** | 4-Bill / 8-Coin Metal Cash Drawer with RJ11/RJ12 24V solenoid pulse cable | ~10,000 DZD |
| **10** | **Vehicle Presence Sensors** | Dual-channel inductive ground loop detector module (12V/24V DIN-rail mounted) | ~16,000 DZD |
| **Total**| **Hardware & Peripherals** | **Turnkey Hardware Field Package** | **~345,000 DZD** |

---

## 4. Cloud Services, Accounts, and AI Stack Requirements

### 4.1 Do You Need a Recurring Cloud AI Subscription (OpenAI / Claude)?

**No.** Smart Park does not require any recurring cloud AI subscriptions to operate:
* **ALPR License Plate Detection & OCR:** Runs locally on ONNX Runtime using YOLOv11 and PaddleOCR.
* **Driver Facial Landmark & Recognition:** Runs locally on ONNX Runtime using SCRFD and ArcFace ResNet50.
* **Biometric Liveness Verification:** Runs locally using MiniFASNet anti-spoofing classification.
* **Subscriber Matching:** Runs locally in system memory using the FAISS vector search library (<1ms latency).
* **Zero Cloud Dependency:** If the facility loses internet connectivity, the edge node continues to read plates, verify VIP faces, actuate barriers, issue thermal tickets, and process cashier cash payments without degradation.

### 4.2 Cloud Databases: Do You Need Supabase Pro?

* **Pilot Testing & Single Site:** You can run Smart Park completely free using either:
  1. The built-in local SQLite persistence (`desktop/data/desktop_station.db` and `edge_buffer.db`), or
  2. The local self-hosted Supabase Docker stack (`PostgreSQL 16` + `pgvector` + `Realtime` + `MinIO`) on the server itself.
* **When Supabase Pro ($25 / month) is Required:**
  - If you manage a commercial facility with remote mobile driver access, multi-operator shifts, and cloud backups:
    - **Continuous Point-in-Time Recovery (PITR):** Safeguards financial ledgers against disk failure.
    - **High-Concurrency Realtime Engine:** Pushes live parking occupancy updates to thousands of mobile app drivers simultaneously.
    - **Encrypted S3 Storage:** Securely retains vehicle entry photos and biometric crops with automatic 30-day lifecycle expiration rules complying with Algerian Law 18-07.

### 4.3 Algerian Domestic Payments: Chargily Pay V2

To accept payments from EDAHABIA (Algérie Poste) and CIB (SATIM interbank) cards, register an official merchant account:
* **Portal:** https://chargily.com/pay
* **Requirements:**
  1. Valid Algerian Commercial Register (Registre de Commerce) or National Auto-Entrepreneur Card.
  2. Corporate or Professional Bank / CCP account statement (Attestation de compte / RIP).
  3. National Identity Card of the legal representative.
* **Integration Keys:** Obtain the live API Secret Key (`live_sk_...`) and Webhook Secret for HMAC-SHA256 signature verification.

### 4.4 Remote Networking & Sovereign Internet Access

Avoid opening insecure inbound ports (port forwarding on port 80/443/8080) on commercial routers. Use secure zero-trust tunneling:
* **Cloudflare Tunnel (cloudflared):** Free. Creates an outbound-only encrypted tunnel from the edge server to your domain (e.g., `api.smartpark-alger.dz`), routing mobile app requests without requiring a static public IP from Algérie Télécom.
* **Tailscale:** Free mesh VPN connecting remote maintenance laptops and mobile patrol devices directly into the edge gateway.

---

## 5. Physical Wiring and Electrical Interconnects

### 5.1 Isolated Local Area Network (VLAN Architecture)

```
                         INTERNET WAN
                              │
                    ┌─────────▼─────────┐
                    │ Fiber/4G Router   │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────────────────┐
                    │ Managed PoE+ Switch           │
                    │                               │
                    │ ┌───────────────────────────┐ │
                    │ │ VLAN 10: CAMERA & MODBUS  │ │
                    │ │ 192.168.10.0/24 (ISOLATED)│ │
                    │ └──────┬─────────────┬──────┘ │
                    │        │             │        │
                    │ ┌──────▼──────────┐ ┌▼──────┐ │
                    │ │ Cameras 1 to 4  │ │Modbus │ │
                    │ │ (PoE Powered)   │ │Relay  │ │
                    │ └─────────────────┘ └───────┘ │
                    │                               │
                    │ ┌───────────────────────────┐ │
                    │ │ VLAN 20: OFFICE & SERVER  │ │
                    │ │ 192.168.20.0/24           │ │
                    │ └──────────────┬────────────┘ │
                    └────────────────┼──────────────┘
                                     │
                    ┌────────────────▼──────────────┐
                    │ Smart Park Edge Server (PC 1) │
                    │ Port 1 (NIC 1) -> 192.168.10.2│
                    │ Port 2 (NIC 2) -> 192.168.20.2│
                    └────────────────┬──────────────┘
                                     │ USB / Ethernet
                    ┌────────────────▼──────────────┐
                    │ Booth Station Peripherals     │
                    │ • 80mm ESC/POS Printer        │
                    │ • 2D Barcode Scanner Gun      │
                    │ • Cash Drawer (via RJ11 port) │
                    └───────────────────────────────┘
```

### 5.2 Modbus Relay to Barrier Motor Control Board

Industrial parking barriers (BFT, CAME, FAAC, Beninca) actuate via clean, volt-free dry contacts. Never send 220V or 24V into the barrier command input:

```
Waveshare Modbus Relay Terminal          Barrier Motor Control Board
┌─────────────────────────────┐          ┌──────────────────────────┐
│ Channel 1 (Entry Gate)      │          │ Command Terminals        │
│   • NO (Normally Open)  ────┼──────────► START / OPEN Input       │
│   • COM (Common)        ────┼──────────► GND / Common             │
├─────────────────────────────┤          ├──────────────────────────┤
│ Channel 2 (Exit Gate)       │          │                          │
│   • NO (Normally Open)  ────┼──────────► START / OPEN Input       │
│   • COM (Common)        ────┼──────────► GND / Common             │
└─────────────────────────────┘          └──────────────────────────┘
```

> **Hardware Safety Rule:** The inductive ground loop detector module must be wired in series with the barrier safety interlock terminal. If no vehicle is physically positioned on the ground loop coils, the barrier will not actuate even if a software command is dispatched.

### 5.3 ESC/POS Printer and Cash Drawer Wiring

Connect the cash drawer RJ11/RJ12 cable directly into the DK (Drawer Kick) port located at the back of the thermal printer. When `DesktopBridgeApi.settle_payment()` executes a cash transaction, the printer firmware issues an electrical pulse on pin 2 (`ESC p 0 25 250`), popping the cash drawer open automatically.

---

## 6. Camera Placement and Optical Alignment Guidelines

Optical calibration is critical to achieving 99%+ ALPR reading accuracy:

1. **Horizontal and Vertical Angle:**
   * Keep the camera angle between **15 and 30 degrees** relative to the vehicle trajectory. An angle exceeding 35 degrees causes perspective distortion on Algerian embossed Arabic and European characters.
2. **Mounting Height:**
   * Mount bullet ALPR cameras at a height between **1.2 meters and 1.6 meters** above the road surface.
3. **Electronic Shutter Speed:**
   * Set camera shutter speed to manual mode at **1/1000 second** or faster. Default automatic shutters (1/25s to 1/100s) create motion blur on moving vehicle plates.
4. **Day/Night Glare Suppression:**
   * Enable Optical Wide Dynamic Range (WDR >= 120 dB) and Headlight Compensation (HLC) to prevent vehicle headlights from blinding the image sensor at night.
5. **Driver Kiosk Biometric Camera:**
   * Position the camera inside or beside the driver ticket terminal at an angle facing the driver window (height 1.1 meters).
   * Install a Circular Polarizing Lens (CPL) to eliminate sun glare reflecting off windshield and side window glass.

---

## 7. Step-by-Step Bench Testing & Field Commissioning Checklist

Execute these verification phases in order before opening the lanes to public traffic:

### Phase 1: Tabletop Bench Test (Before Field Installation)
1. Place the Edge PC, PoE switch, Modbus relay, 80mm printer, barcode scanner, and one test camera on a workbench.
2. Assign static IP addresses:
   * Edge Server NIC 1: `192.168.10.2` (Subnet: `255.255.255.0`)
   * Modbus Relay: `192.168.10.200` (Port: `502`)
   * Test Camera: `192.168.10.101` (RTSP: `rtsp://admin:pass@192.168.10.101:554/live`)
3. Launch the Edge Gateway server: `python src/server.py`.
4. Launch the Desktop Station in diagnostic mode: `python desktop/app.py --headless`.
5. Verify automated ticket printing, barcode scanning, payment settlement, and shift closure.

### Phase 2: Modbus Relay Actuation Test
1. Connect a digital multimeter (set to Continuity / Beep mode) across Channel 1 NO and COM terminals.
2. In the desktop operator station, press the `Spacebar` key or click `OUVERTURE BARRIÈRE D'URGENCE`.
3. Verify that the multimeter beeps for exactly 500 milliseconds and silences immediately.
4. Ensure the relay coil does not remain energized when the network cable is unplugged.

### Phase 3: Live Camera Optical Tuning
1. Mount the bullet cameras at the entry and exit gates.
2. Drive a test vehicle through the lane at 15 km/h during broad daylight. Verify the plate bounding box and OCR score in the CCTV dashboard.
3. Repeat the test at night with full headlights on to verify optical headlight compensation.
4. Test with clean plates, dusty plates, and temporary commercial paper plates (`00` series) to confirm parser disambiguation.

### Phase 4: Financial and Regulatory Audit
1. Perform three test transactions: one cash payment, one card payment via Chargily Pay V2, and one 10-minute free stay (franchise grace).
2. Verify that the cash drawer kicks open only on cash payment.
3. Close the shift in the desktop window and inspect the generated Z-Report:
   * Verify cash variance reconciliation.
   * Verify the SHA-256 cryptographic audit hash.
4. Trigger the ANPDP automated purge routine (`POST /api/compliance/purge`) and verify log retention limits.

---

## 8. Summary of Physical Deliverables

| Category | Deliverable | Status |
| :--- | :--- | :--- |
| **Software Core** | Edge Gateway API, Desktop Station, Flutter Mobile App | 100% Tested & Verified (163 tests passing) |
| **Edge Hardware** | 1x Edge PC (NVIDIA GPU) or Dual-PC setup, 1x Online UPS (2kVA) | Procure locally |
| **Surveillance** | 2x ALPR Cameras, 1x Driver Kiosk Camera, 1x Overview Camera | Procure locally |
| **Gate Automation** | 1x Waveshare Modbus TCP Relay, 2x Ground Loops, Dry Contact Wiring | Procure locally |
| **Booth Station** | 1x 80mm ESC/POS Thermal Printer, 1x 2D Barcode Gun, 1x Metal Cash Drawer | Procure locally |
| **Services & SaaS** | Supabase Pro (Optional/Cloud), Chargily Pay V2 Live Account | Register online |
