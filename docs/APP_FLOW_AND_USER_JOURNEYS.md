# Application Flows and User Journeys (V2.0)
## Smart Park (Algeria Sovereign Edition)

## 1. Primary Operational Workflows

This document specifies the step-by-step user journeys and system state machines for gate entry, liveness verification, parking slot guidance, payment processing, and Law 25-11 regulatory breach handling.

---

## 2. Journey 1: Registered VIP and Subscriber Entry (Sub-250ms Clearance)

```mermaid
flowchart TD
    A["Vehicle approaches Entry Gate"] --> B["Inductive Loop detects vehicle presence"]
    B --> C["CPL Camera captures Plate & Driver Face with NIR"]
    C --> D["YOLOv11 detects plate and SCRFD detects face"]
    D --> E["Algerian Regex validates 1-6 digits & wilaya"]
    D --> F["MiniFASNet verifies Face Liveness"]
    F -- "Liveness Passed" --> G["ArcFace generates 512-D vector"]
    F -- "Photo / Screen Spoof" --> H["Lock Barrier & Flag Spoof Alert"]
    G --> I["Query Local Edge RAM Index (FAISS: <1ms)"]
    I --> J{"Plate & Face on Active Whitelist?"}
    J -- "Yes (Distance <= 0.52)" --> K["Trigger Modbus Relay (Pulse 500ms)"]
    K --> L["Barrier opens, Green LED lights up"]
    L --> M["Vehicle enters facility (<250ms total latency)"]
    M --> N["Induction loop clears, Barrier closes"]
    N --> O["Background sync to Supabase: Log Entry Session"]
    J -- "No: Mismatch or Unknown" --> P["Route to Visitor Flow (Journey 2)"]
```

### Step-by-Step Description:
1. **Trigger:** The vehicle drives onto the entry lane induction loop. The hardware controller notifies the edge engine.
2. **Perception:** The CPL-filtered camera takes a frame burst. YOLOv11 extracts the plate; SCRFD extracts the driver face.
3. **Liveness Verification:** MiniFASNet confirms a live human subject, blocking printed photographs and smartphone screen replays.
4. **Validation:** The plate matches the Algerian format, accepting 1 to 6 digits in the sequential registration block and valid wilaya codes (`01` to `58`).
5. **Local RAM Match:** The edge node executes a FAISS vector search across enrolled profiles in RAM, returning a match in under 0.8ms (Cosine Distance `<= 0.52`).
6. **Clearance:** The edge relay activates. The gate lifts. Clearance completes within 250 milliseconds.
7. **Telemetry:** The event logs locally and syncs to the domestic Supabase instance in the background.

---

## 3. Journey 2: Unregistered Visitor & Temporary `00` Plate Entry

```mermaid
flowchart TD
    A["Unregistered or New Vehicle arrives at Gate"] --> B["Camera reads Algerian Plate"]
    B --> C{"Is Plate Format Valid?"}
    C -- "Standard (XXXXXX YYY ZZ) or Temp (XXXXXX 00 ZZ)" --> D["Validate Wilaya Code (01-58)"]
    C -- "Damaged / Ambiguous (<85% conf)" --> E["Send crop to Local Sovereign VLM (Qwen2.5-VL-3B)"]
    E --> D
    D --> F["Face embedding generated for driver"]
    F --> G["Create new Parking Session in Database"]
    G --> H["Print QR Code Ticket / Display Entry Time on Kiosk"]
    H --> I["Trigger Barrier Gate Relay"]
    I --> J["Vehicle enters, Session marked ACTIVE"]
```

### Step-by-Step Description:
1. **Arrival:** An unregistered vehicle or a brand-new vehicle on temporary `00` plates arrives at the kiosk.
2. **Capture:** The camera reads the plate digits. If the plate contains `00` in the middle block, the engine identifies it as a valid temporary registration.
3. **Local VLM Disambiguation:** If the plate is partially obscured by dust or mud, the local GPU VLM (`Qwen2.5-VL-3B-Instruct`) reads the plate and identifies vehicle make and color in 400ms without internet access.
4. **Session Creation:** A new session record initializes with `status = 'ACTIVE'`, linking the plate number, entry timestamp, vehicle thumbnail, and driver face embedding.
5. **Barrier Clearance:** The barrier opens, and the digital display welcomes the driver with the current time and available slot count.

---

## 4. Journey 3: Blacklisted Vehicle or Watchlist Person Incident

```mermaid
flowchart TD
    A["Vehicle arrives at Gate"] --> B["System processes Plate and Face"]
    B --> C{"Matches Security Blacklist?"}
    C -- "Yes: Stolen Vehicle / Barred Person" --> D["Hold Barrier Gate CLOSED"]
    D --> E["Play audible kiosk prompt: Please wait for security"]
    D --> F["Push critical alarm to Operator Web Dashboard"]
    F --> G["Operator screen spotlights Live Camera + Blacklist File"]
    G --> H["System dispatches SMS/Push alert to Security Patrol"]
    H --> I["Security Officer arrives at lane for inspection"]
    I --> J["Operator records incident notes & manual resolution"]
```

---

## 5. Journey 4: Driver-Vehicle Mismatch (Anti-Theft Protocol)

```mermaid
flowchart TD
    A["Whitelisted Vehicle arrives at Gate"] --> B["Plate confirmed on Whitelist"]
    B --> C["Face recognition processes driver"]
    C --> D{"Does Face match Registered Owner?"}
    D -- "Match (Distance <= 0.52)" --> E["Direct Barrier Open (Journey 1)"]
    D -- "Mismatch (Distance > 0.55)" --> F["Display Prompt on Guard Kiosk"]
    F --> G["Operator reviews: Authorized Family Member or Valet?"]
    G -- "Approved by Guard" --> H["Guard clicks One-Click Override Open"]
    H --> I["Session logs: Plate White, Driver Guest (Logged)"]
    G -- "Suspicious" --> J["Guard requests physical ID verification"]
```

---

## 6. Journey 5: Law 25-11 Mandatory 5-Day Data Breach Notification Triage

```mermaid
flowchart TD
    A["Security Incident / Data Anomaly Detected"] --> B["System logs Incident to data_breach_notifications"]
    B --> C["5-Day ANPDP Notification Countdown Timer starts"]
    C --> D["Data Protection Officer (DPO) alerted via High-Priority SMS/Email"]
    D --> E["DPO opens Incident Triage Portal"]
    E --> F["System pre-populates official ANPDP Breach Notification Form"]
    F --> G["Review affected records, containment measures, and root cause"]
    G --> H["DPO transmits dossier to ANPDP within 5-day statutory window"]
    H --> I["System records ANPDP submission receipt reference in audit log"]
```

### Step-by-Step Description:
1. **Trigger:** A security anomaly or unauthorized export attempt occurs.
2. **Statutory Timer:** Under Law 25-11, a mandatory 5-calendar-day countdown begins from the discovery timestamp.
3. **DPO Workflow:** The designated Data Protection Officer opens the compliance portal, which pre-populates the nature of the breach, affected data categories, and containment actions taken.
4. **Resolution:** The notification dossier is transmitted to the ANPDP, and the official submission receipt number is archived in the immutable compliance ledger.
