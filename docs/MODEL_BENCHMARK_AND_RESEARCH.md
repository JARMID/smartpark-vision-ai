# AI Vision Model Benchmark and Architecture Research Report (V2.0)
## Sovereign Algerian Parking & Security Perception Architecture

## 1. Executive Summary

This report evaluates computer vision models, video streaming pipelines, optical filters, and inference topologies for an intelligent parking and surveillance management system operating in Algeria. The system handles two primary computer vision tasks:
1. Automatic Number Plate Recognition (ANPR/ALPR) calibrated for Algerian vehicle registration standards, supporting standard 6-digit serials, temporary `00` plates, and diplomatic series.
2. Facial detection, anti-spoofing liveness verification, facial feature extraction, and local sub-millisecond 1:N vector matching for drivers and pedestrians.

### Sovereign Compliance and Latency Invariants:
* **Zero Cross-Border Data Transfer (Law 18-07 Article 44):** Biometric vectors, driver faces, and license plate records remain strictly within Algerian sovereign borders. Cloud API roundtrips are replaced with an on-premise local Vision Language Model (VLM) running on the edge GPU alongside self-hosted Supabase instances in domestic data centers.
* **Sub-Millisecond Edge Vector Search:** 1:N facial similarity matching runs entirely in edge gateway RAM via FAISS or `sqlite-vec` (10,000 vectors of 512-D float32 require ~20 MB of RAM and search in <1 millisecond), completely decoupling barrier gate clearance from WAN latency.

---

## 2. Algerian License Plate Recognition (ALPR) Analysis

### 2.1 The Expanded Structure of Algerian License Plates
Algerian vehicle registration plates follow specific national decrees. While standardized, real-world deployment requires handling high-density wilayas and provisional registrations:

#### 1. Standard Civilian Plates:
Formatted as `XXXXXX YYY ZZ` (or `XXXXX YYY ZZ`)
* **Block 1 (`XXXXXX`):** Sequential registration number. In high-density wilayas (such as Algiers `16`, Oran `31`, Blida `09`, Constantine `25`, and Sétif `19`), this block routinely spans **6 digits** (e.g., `104822`), while smaller wilayas issue 1 to 5 digits.
* **Block 2 (`YYY`):** 3-digit category and year code.
  * Digit 1 designates vehicle category: `1` (Passenger car), `2` (Truck), `3` (Van), `4` (Bus), `5` (Tractor), `6` (Special machinery), `7` (Special category), `8` (Trailer), `9` (Motorcycle).
  * Digits 2 and 3 represent registration year (e.g., `24` for 2024, `16` for 2016).
* **Block 3 (`ZZ`):** 2-digit wilaya code from `01` to `58`.

#### 2. Temporary New Vehicle Registrations (`00` Series):
Brand new vehicles that have not yet received their permanent vehicle card (carte grise) circulate with the code `00` in the middle block:
`XXXXX 00 ZZ` or `XXXXXX 00 ZZ`
The parser must accept `00` locally without flagging the plate as invalid or routing it to fallback models.

#### 3. Special Series:
* **Diplomatic and Consular:** Prefixes `CD` (Corps Diplomatique), `CC` (Corps Consulaire), `CMD` (Chef de Mission Diplomatique) printed on light green backgrounds.
* **Temporary Transit:** `WW` series vehicles.

### 2.2 Plate Recognition Pipeline Architecture

```
[RTSP Camera Feed (1080p)]
       │
       ▼
[Motion & Vehicle Trigger (YOLOv11n)]
       │
       ▼
[Plate Bounding Box Crop & Bilinear Deskew]
       │
       ▼
[OCR Engine: PaddleOCR v4 / Fast-Plate-OCR]
       │
       ▼
[Deterministic Algerian Syntax Engine]
  ├── Validates 1 to 6 digit serials
  ├── Accepts both 3-digit category/year and '00' temporary codes
  └── Validates Wilaya codes 01 to 58
       │
       ├── Confidence >= 85%: Clean Text Matched Locally
       └── Confidence < 85%: Dispatched to Local Sovereign VLM (Qwen2.5-VL-3B)
                   │
                   ▼
       [Local Edge Decision Engine]
```

---

## 3. Facial Recognition, Liveness, and Optics

### 3.1 Optical Engineering: Windshield Glare and Harsh Sunlight
Capturing driver faces through windshields in Algerian sunlight presents severe optical challenges: reflection, solar glare, and tinted glass. Standard surveillance cameras produce high false rejections under these conditions.

The system incorporates three hardware-level optical countermeasures:
1. **Circular Polarizing Filter (CPL):** Mounted directly on the camera lens, the CPL cuts reflected light and glare from angled vehicle windshields.
2. **850nm Near-Infrared (NIR) Illumination:** Dedicated NIR floodlights illuminate the vehicle cabin through tinted glass without blinding the driver.
3. **Global Shutter Image Sensor:** Eliminates motion blur and rolling shutter distortion when vehicles approach the barrier.

### 3.2 Anti-Spoofing and Liveness Verification
To prevent badge fraud (holding up a printed photo or smartphone screen displaying an authorized driver's face), the facial pipeline includes a lightweight anti-spoofing model:
* **Engine:** MiniFASNet (Silent-Face-Anti-Spoofing).
* **Latency:** 3 to 5 milliseconds on GPU.
* **Execution:** Evaluates texture, reflection, and depth gradients before embedding generation. If spoof score exceeds threshold, the system flags `denied_spoof_detected` and locks the barrier.

### 3.3 Face Feature Extraction and Calibrated Distance Thresholds
* **Detector:** SCRFD-10G isolates facial bounding boxes and 5 keypoints in 4ms.
* **Feature Extractor:** ArcFace (ResNet50 TensorRT FP16) extracts a normalized 512-dimensional vector.
* **Metric Definition:**
  $$\text{Cosine Distance} = 1 - \text{Cosine Similarity}$$
* **Threshold Calibration:**
  * In lab conditions, Cosine Distance `<= 0.38` (Similarity `>= 0.62`) is typical.
  * In real-world parking environments with windshield tint, glass refraction, and variable lighting, setting Distance `<= 0.38` causes excessive false rejections.
  * **Calibrated Gate Distance:** Set to **`<= 0.52`** (corresponding to Cosine Similarity **`>= 0.48`**) for driver verification at barrier gates.
  * **Pedestrian Access Distance:** Set to **`<= 0.40`** (Similarity **`>= 0.60`**) for unshielded pedestrian turnstiles.

---

## 4. Sub-Millisecond Local RAM Vector Matching

To guarantee gate clearance under 250 milliseconds, vector similarity search cannot query a cloud database over an external network link. 

### Local Edge FAISS / `sqlite-vec` Architecture:
1. **Memory Footprint:** 10,000 enrolled facial vectors of 512 float32 numbers consume:
   $$10{,}000 \times 512 \times 4 \text{ bytes} \approx 20.48 \text{ MB of RAM}$$
2. **Execution Latency:** FAISS flat inner-product search on 20 MB of RAM takes **less than 0.8 milliseconds** on an Intel i5 CPU or NVIDIA GPU.
3. **Synchronization Pattern:**
   * The edge node loads all active tenant and VIP vector embeddings into an in-memory index at startup.
   * Background WebSocket events from Supabase update the in-memory index whenever a new employee or tenant enrolls.
   * Gate decisions evaluate 100% locally in RAM in sub-millisecond time.

---

## 5. Local Sovereign VLM vs Cloud Services

To comply with Algerian Law 18-07 Article 44, video frames and biometric data must not cross international borders without explicit prior ANPDP authorization. Cloud API calls to foreign servers are replaced with an on-premise local VLM:

### Local VLM Selection: Qwen2.5-VL-3B-Instruct (INT4 Quantized)
* **Model:** Qwen2.5-VL-3B-Instruct or Llama-3.2-Vision-11B-INT4.
* **Execution:** Runs locally on the on-premise RTX 3060 via vLLM or Ollama.
* **Memory Footprint:** INT4/AWQ quantization requires ~2.8 GB of VRAM, running alongside YOLOv11 and ArcFace without saturating the 12GB VRAM buffer.
* **Inference Latency:** 350 to 480 milliseconds locally on the RTX 3060.
* **Capability:** Resolves damaged plate digits, identifies vehicle make, model, and color, and operates completely offline with zero recurring API costs.

---

## 6. Hardware Bill of Materials (BOM) with Power Protection

Power quality in industrial and commercial zones in Algeria exhibits occasional voltage fluctuations and micro-cuts. The hardware bill of materials includes power conditioning:

| Hardware Component | Specification | Purpose |
| :--- | :--- | :--- |
| **Edge Compute Node** | Intel Core i5 13th Gen, 32GB RAM, NVIDIA RTX 3060 12GB, 512GB NVMe + 2TB SSD | Local video decoding, YOLO, ArcFace, local VLM, SQLite queue. |
| **Power Protection (UPS)** | **Online Double-Conversion UPS (2kVA / 1800W)** with SNMP management | Pure sine wave output, zero transfer time (0ms switch), protects GPU from voltage spikes and sags. |
| **Driver Kiosk Camera** | 2MP Global Shutter IP Camera, CPL Circular Polarizer, 850nm NIR LED Array | Eliminates windshield reflection and penetrates window tint. |
| **Plate Recognition Camera** | 2MP/4MP ALPR Bullet Camera with motorized 5-50mm varifocal lens and optical WDR | High shutter speed (1/1000s) for moving vehicle plates. |
| **Barrier Relay Controller** | Waveshare 8-Channel Modbus TCP / Ethernet POE Relay Module | Dry contact triggers for barrier gate actuation. |
| **Loop Detector Interface** | Dual-channel inductive ground loop sensor | Physical vehicle presence verification before barrier actuation. |

---

## 7. Cost and Billing Reality in Algerian Dinars (DZD)

To avoid foreign currency card restrictions for Algerian corporate clients, all operational and infrastructure costs are quoted in Algerian Dinars (DZD) with domestic hosting:

| Component | Provider / Local Equivalent | Cost (DZD) |
| :--- | :--- | :--- |
| **Edge Hardware Bundle (One-Time)** | Local Industrial PC + RTX 3060 + 2kVA UPS + Cameras + Relay | ~380,000 DZD (one-time capex) |
| **Domestic Cloud Hosting** | Self-hosted Supabase on Algérie Télécom / Icosnet / Local VPS | ~6,500 DZD / month |
| **Local Vision & VLM Inference** | Local GPU Execution (YOLOv11 + ArcFace + Qwen2.5-VL) | 0.00 DZD (Zero API fees) |
| **On-Site Maintenance & Support** | SLA with 4-hour on-site hardware swap | ~15,000 DZD / month |
| **Total Monthly Operating Cost** | Sovereign Domestic Stack | **~21,500 DZD / month** |
