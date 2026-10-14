# UI/UX Design Brief and Interface Specifications (V2.0)
## SmartPark Vision AI Command Center (Sovereign Edition)

## 1. Design Philosophy and Visual Language

The SmartPark Vision AI interface serves security operators, parking attendants, and facility administrators who monitor high-throughput environments over extended shifts. The visual language emphasizes rapid information hierarchy, zero visual fatigue, high contrast status indicators, and keyboard-driven ergonomics.

### 1.1 Color Palette (Dark Mode Industrial Palette)
* **Background Primary:** `#090D16` (Deep Obsidian Canvas)
* **Surface Secondary:** `#111827` (Card and Panel Surface)
* **Surface Tertiary:** `#1F2937` (Active Rows, Hover States, Borders)
* **Border Default:** `#374151` (Subtle 1px Borders)
* **Text Primary:** `#F9FAFB` (High Contrast Headings and Plate Text)
* **Text Muted:** `#9CA3AF` (Timestamps, Labels, Secondary Metadata)

### Functional Semantic Accents:
* **Success / Clearance:** `#10B981` (Emerald Green: Barrier Open, Whitelist Match, Slot Vacant, Liveness Confirmed)
* **Danger / Security Alert:** `#EF4444` (Crimson Red: Blacklist Match, Barrier Lock, Stolen Plate, Spoof Attempt)
* **Warning / Review Needed:** `#F59E0B` (Amber: Mismatched Driver Face, Low OCR Confidence, Overstay, UPS Battery Mode)
* **Information / Telemetry:** `#06B6D4` (Cyan: Active RTSP Video Stream, Live Camera Online)
* **Plate Highlight:** `#FDE047` (Algerian Rear Plate Yellow: High-contrast character recognition box)

### 1.2 Native Algerian Dinar (DZD) Pricing and Typography
* All financial figures, parking fees, and daily totals render natively in Algerian Dinars: `100.00 DZD`, `500.00 DZD`.
* **Primary UI Font:** **Inter** for labels, navigation, buttons, and data tables.
* **Monospaced Data Font:** **JetBrains Mono** for license plate strings (`104822 119 16`, `08412 00 16`), timestamps, wilaya codes, and vector cosine distance scores.

---

## 2. Screen Architecture and Wireframes

### 2.1 Screen 1: Live Monitoring Command Center (Primary Screen)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ [LOGO] SmartPark Vision AI │ Site: Alger Centre (El-Biar) │ 🟢 UPS: ON-LINE (230V) │ 🟢 ALL ONLINE │
├──────────────────────────────────────────────────────┬───────────────────────────────────────┤
│ LIVE CAMERA MATRIX (WebRTC Streams)                  │ REAL-TIME EVENT STREAM (Ticker)       │
│ ┌─────────────────────────┬────────────────────────┐ │ ┌───────────────────────────────────┐ │
│ │ CAM-01: Lane 1 Entry    │ CAM-02: Lane 1 Driver  │ │ │ 16:42:10 🟢 ACCESS GRANTED        │ │
│ │ [LIVE RTSP 1080p 25FPS] │ [CPL + NIR FEED]       │ │ │ Plate: 104822 119 16 (Algiers)    │ │
│ │                         │                        │ │ │ Driver: Karim Benali (VIP)        │ │
│ │ Plate: 104822 119 16    │ Liveness: 🟢 LIVE (0.98│ │ │ Liveness: 🟢 Confirmed (0.98)     │ │
│ │                         │ Match: Karim B. (0.42) │ │ │ Barrier: Opened [Lane 1: 180ms]   │ │
│ ├─────────────────────────┼────────────────────────┤ │ ├───────────────────────────────────┤ │
│ │ CAM-03: Lane 2 Exit     │ CAM-04: Zone A Stalls  │ │ │ 16:41:48 🟡 REVIEW REQUIRED       │ │
│ │ [LIVE RTSP 1080p 25FPS] │ [OVERHEAD MATRIX]      │ │ │ Plate: 08412 00 16 (Temp Plate)   │ │
│ │                         │                        │ │ │ Driver: Unknown Face (Dist: 0.58) │ │
│ │ Plate: 00192 114 09     │ Slots: 184 / 220 Free  │ │ │ [APPROVE GUEST]  [INSPECT ID]     │ │
│ └─────────────────────────┴────────────────────────┘ │ ├───────────────────────────────────┤ │
│                                                      │ │ 16:40:02 🔴 SPOOF ATTEMPT BLOCKED │ │
│ QUICK BARRIER CONTROLS:                              │ │ Plate: 04112 118 16 (Algiers)     │ │
│ [OPEN LANE 1 (Space)] [OPEN LANE 2 (O)] [LOCK ALL]   │ │ MiniFASNet: 🔴 SCREEN REPLAY DETECT │ │
└──────────────────────────────────────────────────────┴───────────────────────────────────────┘
```

---

### 2.2 Screen 2: Law 25-11 Regulatory Compliance Portal

Dedicated dashboard for the Data Protection Officer (DPO) and compliance auditors:

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ ANPDP COMPLIANCE DASHBOARD (Loi 18-07 & Loi 25-11)          [GENERATE OFFICIAL ANPDP DOSSIER]│
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────┬─────────────────────────┬──────────────────────────────────────┐ │
│ │ DPIA STATUS: APPROVED   │ PROCESSING REGISTER     │ 5-DAY BREACH NOTIFICATIONS           │ │
│ │ Assessment Ref: DP-2026 │ Total Categories: 4     │ Active Incidents: 0                  │ │
│ │ Biometric Justification:│ Data Subjects: 1,480    │ Breach Clock: All Clear              │ │
│ │ High-Security Access    │ Cross-Border: 0 (FALSE) │ Statutory Compliance: 100%           │ │
│ └─────────────────────────┴─────────────────────────┴──────────────────────────────────────┘ │
│ DATA RETENTION & PURGE STATUS:                                                               │
│ Rolling 30-Day Purge Cycle: Active. Last automated scrub: 14/10/2026 02:00 AM (4,180 crops)  │
│ Sensitive Biometric Vectors Enrolled: 240 (All encrypted on domestic storage)                │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Keyboard Ergonomics for High-Stress Gate Operations

Operators can command the system entirely via keyboard shortcuts without touching a mouse:
* **`Spacebar`:** Momentary trigger to open Lane 1 barrier.
* **`Shift + Spacebar`:** Momentary trigger to open Lane 2 barrier.
* **`A`:** Quick-approve current flagged guest driver.
* **`B`:** Flag current vehicle plate or face to security blacklist.
* **`M`:** Switch to full-screen 4-camera grid.
* **`Escape`:** Dismiss active alert modal.
* **`F`:** Jump focus directly to search bar.
