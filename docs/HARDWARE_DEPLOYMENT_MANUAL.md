# Smart Park - Physical Hardware & Camera Deployment Manual

This manual provides the engineering specifications, physical wiring schematics, optical geometry, and software installation steps required to deploy **Smart Park** on physical access control gates and commercial IP cameras.

---

## 1. Physical Architecture: Camera vs Edge Compute Appliance

In commercial computer vision and automated parking access control, standard security cameras do not run complex neural networks, FAISS vector indexes, or national regulatory compliance layers directly on their onboard chips.

```
+---------------------------------------------------------------------------------------------------------+
|                                        FIELD INSTALLATION (LANE 1)                                      |
|                                                                                                         |
|   +--------------------------+                                                                          |
|   | CAM 1: Entry ALPR Camera |---[Cat6 PoE]---+                                                         |
|   | (Varifocal 8-32mm Lens)  |                |                                                         |
|   +--------------------------+                |                                                         |
|                                               v                                                         |
|   +--------------------------+      +--------------------+         +----------------------------------+ |
|   | CAM 2: Driver Biometric  |----->| Industrial 8-Port  |-------->| Edge AI Appliance                | |
|   | (Dual RGB + 850nm NIR)   |      | PoE+ Switch        |  Cat6   | (NVIDIA Jetson Orin / Advantech) | |
|   +--------------------------+      | (192.168.10.0/24)  | Gig-E   | - RTSP Stream Worker (Zero-Lag)  | |
|                                     +--------------------+         | - YOLOv11 Plate Detector         | |
|   +--------------------------+                ^                    | - Algerian Plate Parser (58 Wil) | |
|   | CAM 3: Exit Toll Gantry  |---[Cat6 PoE]---+                    | - ArcFace 512-D RAM Vector Index | |
|   +--------------------------+                |                    | - MiniFASNet Anti-Spoof Gate     | |
|                                               |                    | - SQLite Write-Ahead Buffer      | |
|   +--------------------------+                |                    +----------------------------------+ |
|   | CAM 4: Deck Fisheye      |---[Cat6 PoE]---+                                     |                   |
|   +--------------------------+                                                      | RS-485 (Modbus)   |
|                                                                                     v                   |
|   +--------------------------+     Dry Contact Pulse (COM / NO)    +----------------------------------+ |
|   | Physical Boom Barrier    |<------------------------------------| Modbus 4-Channel Relay Module    | |
|   | (FAAC / BFT / CAME)      |                                     | (Waveshare / Moxa / Advantech)   | |
|   +--------------------------+                                     +----------------------------------+ |
|                ^                                                                    ^                   |
|                |                                                                    |                   |
|                +---- Ground Loop Detector A (Presence) -----------------------------+                   |
|                +---- Ground Loop Detector B (Safety Close) -------------------------+                   |
+---------------------------------------------------------------------------------------------------------+
```

### Why Compute is Stationed at the Edge
1. **Camera SoC Constraints:** Commercial IP cameras (Axis, Hikvision, Dahua, Uniview, Hanwha) use low-power Ambarella, HiSilicon, or Novatek image signal processors designed strictly to compress sensor raw data into H.264/H.265 video streams. They do not have the RAM or tensor cores needed to run 512-dimensional vector math and anti-spoof classifiers at 30 frames per second.
2. **Sovereignty and Sub-250ms SLA:** Sending raw video streams over 4G/5G to cloud servers creates latency (500ms to 2500ms), requires massive bandwidth, and violates Algerian Law 18-07 and Law 25-11 regarding domestic biometric storage.
3. **The Industrial Edge Appliance:** The on-premise industrial gateway (an NVIDIA Jetson Orin Nano / NX or an Advantech fanless PC) resides inside the security booth or lane gate pedestal, processing RTSP streams locally with zero internet dependency.

---

## 2. Optical Geometry & Camera Placement Specifications

### Camera 1: Entry ALPR Plate Camera
* **Recommended Hardware:** Dahua IPC-HFW5241E-Z12E, Hikvision DS-2CD7A26G0/P-IZS, or Axis P1455-LE-3.
* **Image Sensor:** 1/2.8" or 1/1.8" Progressive Scan CMOS, Minimum 0.001 Lux (Color).
* **Lens Selection:** 8mm to 32mm motorized varifocal lens.
* **Mounting Height:** 1.2 meters to 1.5 meters above road grade.
* **Horizontal Offset:** Mount within 15 degrees of the lane center to prevent acute perspective skew on license plates.
* **Vertical Pitch:** 15 to 20 degrees downward tilt.
* **Capture Distance:** 4.5 meters to 6.0 meters before the stop line.
* **Shutter Speed Configuration:** Set to fixed manual shutter at `1/1000s` to eliminate vehicle motion blur day and night.

### Camera 2: Driver Biometric & Anti-Spoof Kiosk Camera
* **Recommended Hardware:** Dual-lens biometric kiosk module (Integrated RGB sensor + 850nm Narrow-Band Infrared Sensor).
* **Mounting Position:** Integrated into the driver-side access pedestal or ticket terminal.
* **Mounting Height:** 1.15 meters from road grade (aligned with driver window head level).
* **Focal Length:** 3.6mm to 4.0mm wide angle.
* **Working Range:** 0.6 meters to 1.2 meters from the driver's face.
* **Illumination:** Pulsed 850nm NIR LED array synchronized with exposure to defeat nighttime glare and tinted windows.

### Camera 3: Exit Barrier & Gantry VMS Camera
* **Mounting Position:** Centered on the structural steel overhead gantry.
* **Mounting Height:** 2.4 meters above road grade.
* **Focal Length:** 6.0mm to 8.0mm.
* **Function:** Monitors exiting vehicle bumper, validates ticket settlement or VIP clearance, and verifies lane clearance before closing the arm.

### Camera 4: Deck Occupancy Fisheye Camera
* **Mounting Position:** Ceiling-mounted in the center of parking driving aisles.
* **Mounting Height:** 3.0 meters to 3.8 meters.
* **Lens:** 180-degree hemispheric fisheye (1.6mm to 2.8mm).
* **Coverage:** Up to 24 parking bays per camera unit.

---

## 3. Network Configuration & Stream URLs

Cameras must be connected to an isolated Layer 2 network switch on a dedicated CCTV VLAN. Default IP scheme:

| Camera Role | IP Address | Subnet Mask | RTSP Stream URL |
| :--- | :--- | :--- | :--- |
| **CAM 1: Entry Plate** | `192.168.10.101` | `255.255.255.0` | `rtsp://admin:smartpark2026@192.168.10.101:554/Streaming/Channels/101` |
| **CAM 2: Driver Biometric** | `192.168.10.102` | `255.255.255.0` | `rtsp://admin:smartpark2026@192.168.10.102:554/Streaming/Channels/101` |
| **CAM 3: Exit Plate** | `192.168.10.104` | `255.255.255.0` | `rtsp://admin:smartpark2026@192.168.10.104:554/Streaming/Channels/101` |
| **CAM 4: Deck Overhead** | `192.168.10.105` | `255.255.255.0` | `rtsp://admin:smartpark2026@192.168.10.105:554/Streaming/Channels/101` |
| **Modbus Relay Module** | `192.168.10.200` | `255.255.255.0` | Modbus TCP Port `502` / RS-485 via USB |
| **Edge Appliance (NIC 1)**| `192.168.10.10` | `255.255.255.0` | Gateway & Ingestion Node |

### Camera Firmware Configuration Requirements
1. **RTSP Transport:** Set protocol to **TCP** (enforced in `config/mediamtx.yml` and `src/camera/rtsp_worker.py`). UDP must be disabled to avoid packet tearing under network load.
2. **Video Encoding:** H.264 (Baseline or Main profile) or H.265.
3. **Bitrate Control:** CBR (Constant Bit Rate) set to `4096 kbps`.
4. **GOP (Group of Pictures):** Set I-Frame interval equal to framerate (e.g., 30 for 30fps) to ensure keyframes arrive every 1.0 second.

---

## 4. Barrier Gate Physical Interfacing (Modbus & Dry Contacts)

The physical barrier gate (e.g. FAAC 620, BFT Giotto, CAME Gard 4, Magnetic Autocontrol) is controlled via relay dry contacts.

### Wiring Diagram: Edge Relay to Barrier Motherboard
```
+------------------------------------+           +----------------------------------+
| Waveshare / Moxa Modbus Relay Unit |           | Barrier Gate Control Motherboard |
|                                    |           | (e.g. BFT Thalia / FAAC 624MPS)  |
|   [ CH1 Relay Output ]             |           |                                  |
|   Pin: Normally Open (NO) ---------|---------->| Terminal: OPEN Command Input     |
|   Pin: Common (COM) ---------------|---------->| Terminal: 24Vdc Common Ground    |
+------------------------------------+           +----------------------------------+
```

### Relay Command Sequence
1. Upon vehicle arrival, `src/main.py` validates the plate and driver credentials in less than 250ms.
2. If access is granted, `src/barrier/modbus_controller.py` executes:
   - Modbus Function Code `0x05` (Write Single Coil) setting Coil `0x00` to `ON`.
   - The relay contacts close for a calibrated 500ms duration.
   - The barrier motherboard detects the dry contact closure and drives the motor to raise the arm.
   - After 500ms, the relay automatically resets to `OFF` (normally open state).
3. The inductive safety loop detector beneath the gate keeps the barrier open until the rear bumper clears, then pulses the close terminal to lower the arm.

---

## 5. Software Installation on On-Premise Edge Appliance

### Option A: Running Containerized with Docker Compose
```bash
# 1. Clone repository to edge gateway
cd /opt/smartpark

# 2. Verify camera connectivity
ping 192.168.10.101
ping 192.168.10.102

# 3. Launch edge daemon and local stream proxy
docker compose -f docker-compose.edge.yml up -d

# 4. View real-time ingestion logs
docker logs -f smartpark_edge_daemon
```

### Option B: Running Natively via Systemd (Jetson Linux / Ubuntu)
```bash
# 1. Install prerequisites
sudo apt update && sudo apt install -y python3-venv python3-pip ffmpeg

# 2. Set up virtual environment
cd /opt/smartpark
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Test edge daemon in physical mode
python3 edge_daemon.py --mode physical --config config/cameras.json

# 4. Install and enable systemd auto-start
sudo cp smartpark-edge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable smartpark-edge
sudo systemctl start smartpark-edge

# 5. Check service health
sudo systemctl status smartpark-edge
```

---

## 6. Commissioning & Optical Alignment Checklist

Before handing the installation over to operations, field technicians must verify:
- [ ] License plate covers at least **150 horizontal pixels** in CAM 1 view at the stop line.
- [ ] License plate tilt is within ±5 degrees of horizontal.
- [ ] No direct headlight flare blinds CAM 1 (verify exposure compensation and WDR).
- [ ] Driver face covers at least **120x120 pixels** in CAM 2 view with clear pupil visibility.
- [ ] Infrared active illuminator activates automatically when ambient light drops below 10 Lux.
- [ ] RS-485 Modbus relay opens the barrier arm within 250ms of a whitelisted VIP arrival.
- [ ] Loop detector B safely locks the barrier arm up while a vehicle is positioned underneath.

---

## 7. Automated Site Commissioning Script

A dedicated verification utility is provided to run full automated diagnostics on-site:

```bash
python verify_edge_deployment.py
```

This utility automatically audits:
1. Camera RTSP manifest parsing and channel reachability in `config/cameras.json`.
2. SQLite Write-Ahead Logging (WAL) state and database integrity (`PRAGMA integrity_check`).
3. Algerian plate syntax and wilaya registry parsing (Wilayas 01 to 58).
4. Anti-Passback (APB) and cloned plate fraud intercept:
   - Validates sub-250ms barrier opening for whitelisted VIP vehicles.
   - Confirms immediate gate lockdown when a vehicle attempts duplicate entry while already recorded inside.
   - Validates exit gantry clearance through CAM 3 and subsequent legal re-entry.

