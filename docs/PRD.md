# Product Requirements Document (PRD)
## SmartPark Vision AI (Algeria Sovereign Commercial Edition)

## 1. Document Control and Overview

* **Project Name:** SmartPark Vision AI (Algeria)
* **Status:** Revised Planning Specification (V2.0)
* **Regulatory Baseline:** Algerian Law 18-07 and Amendment Law 25-11 (24 July 2025)
* **Target Release:** 60 to 90 Days Deployment Lifecycle
* **Primary Markets:** Commercial parking garages, corporate business parks, shopping centers, residential complexes, and transport hubs in Algeria (Algiers, Oran, Constantine, Sétif, Blida).

### 1.1 Executive Vision
SmartPark Vision AI is an enterprise-grade camera and parking facility management platform that automates vehicle access, parking occupancy tracking, driver verification, and facility security. The system operates on a sovereign, offline-first hybrid architecture designed specifically for the Algerian infrastructure and regulatory environment.

---

## 2. Regulatory Compliance: Algerian Law 18-07 and Law 25-11

Under Algerian legislation, automated camera surveillance and biometric processing are strictly regulated. The platform enforces compliance by design:

### 2.1 Law 18-07 and Amendment Law 25-11 (24 July 2025)
* **Mandatory Data Protection Impact Assessment (DPIA / Analyse d'Impact):** Under Law 25-11, any automated biometric processing requires a formal DPIA before deployment. The software includes an administrative module that pre-populates the standard ANPDP DPIA template detailing processing risks, biometric necessity, and encryption controls.
* **Formal Register of Processing Activities (Registre des activités de traitement):** The platform maintains an automated digital register categorizing data subjects (visitors, employees, subscribers), processed biometric vectors, retention periods, and internal recipients.
* **Mandatory 5-Day Data Breach Notification:** Law 25-11 establishes a strict 5-calendar-day deadline to notify the ANPDP upon discovering any data breach or unauthorized system access. The system features an incident triage module that generates the required ANPDP notification package within 24 hours of a security event.
* **Data Sovereignty (Article 44 Prohibition):** Personal data, license plate histories, and biometric vector embeddings remain strictly inside Algeria on sovereign infrastructure (on-premise edge storage and domestic sovereign cloud hosting). Cross-border transfers to foreign cloud APIs are eliminated.
* **Configurable Rolling Purge:** Image thumbnails and raw biometric vectors automatically purge after 30 days unless flagged by an active security incident.

---

## 3. User Personas

### Persona A: Security and Gate Operator (Amine)
* **Role:** Stationed at the primary guard kiosk or monitoring booth.
* **Needs:** Sub-250ms visual confirmation of arriving vehicles, side-by-side watchlist alerts, anti-spoofing notifications, one-click manual barrier overrides, and reliable operation during internet outages.

### Persona B: Facility Administrator (Nadia)
* **Role:** Manages parking rates in Algerian Dinars (DZD), tenant subscriptions, staff permissions, and security policies.
* **Needs:** Web dashboard displaying live occupancy, revenue breakdowns, whitelist management, and exportable financial reports.

### Persona C: Data Protection Officer / Compliance Lead (Samir)
* **Role:** Ensures institutional compliance with ANPDP guidelines and Law 25-11.
* **Needs:** One-click generation of the Register of Processing Activities, DPIA documentation, and immutable audit logs of all operator searches.

### Persona D: Corporate Tenant / VIP Driver (Karim)
* **Role:** Registered regular visitor or corporate fleet driver.
* **Needs:** Rapid hands-free gate access without badge scanning, accurate plate reading through tinted windows, and reserved slot guidance.

---

## 4. Functional Requirements

### 4.1 Automatic Number Plate Recognition (ALPR)
* **FR-1.1:** Detect vehicle presence and license plate coordinates within 100 milliseconds of camera frame arrival.
* **FR-1.2:** Recognize standard Algerian civilian plate formats (`XXXXXX YYY ZZ`), supporting 1 to 6 digits in the sequential registration block (covering high-density wilayas like Algiers 16 and Oran 31), valid vehicle category digits (`1` to `9`), registration years, and wilaya codes (`01` to `58`).
* **FR-1.3:** Recognize temporary new vehicle registration plates bearing the `00` middle block (`XXXXX 00 ZZ` and `XXXXXX 00 ZZ`), treating them as valid entries without routing to manual inspection.
* **FR-1.4:** Parse special Algerian plate series, including `WW` temporary transit plates, diplomatic series (`CD`, `CC`, `CMD`), and state vehicles.
* **FR-1.5:** When optical confidence drops below 85%, dispatch the plate crop to the local edge VLM (Qwen2.5-VL-3B-Instruct) for zero-shot character reading and vehicle color identification.

### 4.2 Driver and Pedestrian Facial Recognition & Anti-Spoofing
* **FR-2.1:** Detect driver and pedestrian faces using the SCRFD neural detector.
* **FR-2.2:** Execute anti-spoofing verification via MiniFASNet to detect printed photographs or digital screens, suppressing barrier opening on spoof attempts.
* **FR-2.3:** Generate a normalized 512-dimensional vector embedding per detected face using ArcFace.
* **FR-2.4:** Execute 1:N similarity searches across registered facial profiles locally in edge RAM using FAISS or `sqlite-vec` within 1 millisecond.
* **FR-2.5:** Enforce calibrated cosine distance thresholds: Distance `<= 0.52` (Similarity `>= 0.48`) for through-windshield driver capture; Distance `<= 0.40` (Similarity `>= 0.60`) for pedestrian access.
* **FR-2.6:** Correlate entry and exit driver faces to trigger an operator alert if a vehicle exits with a driver discordant from the entry profile.

### 4.3 Barrier Gate and Access Control Automation
* **FR-3.1:** Automated barrier triggers must execute via local Ethernet / Modbus TCP relays within 250 milliseconds of perception trigger.
* **FR-3.2:** Maintain a local SQLite cache and RAM vector index, enabling barrier automation to function continuously during internet outages.
* **FR-3.3:** Anti-tailgating logic must verify that the ground induction loop clears before allowing a subsequent barrier opening.

### 4.4 Parking Occupancy and Slot Guidance
* **FR-4.1:** Overhead cameras monitor parking stalls, classifying each stall as `vacant`, `occupied`, or `reserved`.
* **FR-4.2:** Total facility, zone-level, and floor-level occupancy counts update in real time on the web dashboard and roadside LED guidance signs.
* **FR-4.3:** Overstay detection notifies operators when a vehicle exceeds the permitted parking duration.

### 4.5 Tariff and Billing Management (DZD Native)
* **FR-5.1:** Support configurable rate structures in Algerian Dinars: flat fees, hourly rates, grace periods (e.g., 15 minutes free), and night tariffs.
* **FR-5.2:** Support monthly and annual tenant subscription passes tied to vehicle plates and driver facial credentials.
* **FR-5.3:** Integration-ready architecture for Algerian payment channels (cashier desk receipts, Chargily Pay V2 EDAHABIA/CIB cards, and mobile payments).

---

## 5. Non-Functional Requirements

### 5.1 Performance and Latency Invariants
* **NFR-1.1 (Gate Clearance Latency):** Maximum total elapsed time between vehicle arrival at the trigger zone and barrier opening signal must not exceed 250 milliseconds by executing vector matching locally in RAM.
* **NFR-1.2 (Search Speed):** Historical plate and face queries across a database of 1,000,000 records must complete in under 500 milliseconds.
* **NFR-1.3 (Live Video Latency):** WebRTC live video streams rendered on the web dashboard must exhibit glass-to-glass latency under 300 milliseconds.

### 5.2 Reliability, Availability, and Power Protection
* **NFR-2.1 (Offline Fault Tolerance):** If cloud network connectivity drops, edge gateways must continue processing entries, recording events in local SQLite, and operating barriers autonomously.
* **NFR-2.2 (Power Conditioning):** Edge hardware must connect to an Online Double-Conversion UPS (2kVA minimum) providing pure sine wave output and zero transfer time during commercial electrical sags or cuts.
* **NFR-2.3 (Data Resynchronization):** When network connectivity restores, all offline logs, images, and embeddings must synchronize automatically with Supabase without transaction duplication.

---

## 6. Success Metrics and KPIs

* **ALPR Recognition Accuracy:** Greater than 97.0% across standard civilian plates, 6-digit plates, and temporary `00` plates.
* **Facial Verification Precision:** False Acceptance Rate (FAR) under 0.01% and False Rejection Rate (FRR) under 2.0% through vehicle windshields with CPL filters.
* **Average Gate Clearance Time:** Under 2.0 seconds per authorized vehicle.
* **ANPDP Regulatory Approval:** 100% compliance with Law 18-07 and Law 25-11 requirements.
