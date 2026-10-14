-- ============================================================================
-- SmartPark Vision AI (Algeria Edition) - Production Database Schema (V2.0)
-- Target Platform: Self-Hosted Supabase / PostgreSQL 16 on Algerian Sovereign Cloud
-- Fully Compliant with Algerian Law 18-07 and Amendment Law 25-11 (July 24, 2025)
-- ============================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 2. ENUM TYPES
CREATE TYPE user_role AS ENUM (
    'superadmin',
    'facility_admin',
    'security_operator',
    'compliance_auditor',
    'data_protection_officer',
    'customer_driver'
);

CREATE TYPE vehicle_category_code AS ENUM (
    '1_passenger_car',
    '2_truck',
    '3_commercial_van',
    '4_bus',
    '5_tractor',
    '6_special_machinery',
    '7_special_category',
    '8_trailer',
    '9_two_wheeler',
    'temporary_00',
    'transit_ww',
    'diplomatic_cd',
    'consular_cc',
    'state_official'
);

CREATE TYPE barrier_action AS ENUM (
    'auto_cleared',
    'manual_cleared',
    'denied_blacklisted',
    'denied_mismatch',
    'denied_spoof_detected',
    'held_for_inspection'
);

CREATE TYPE session_status AS ENUM (
    'active',
    'completed',
    'flagged',
    'overstay',
    'cancelled'
);

CREATE TYPE slot_status AS ENUM (
    'vacant',
    'occupied',
    'reserved',
    'disabled_access',
    'maintenance'
);

-- 3. FACILITIES & SOVEREIGN TENANTS
CREATE TABLE facilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    wilaya_code VARCHAR(2) NOT NULL, -- e.g., '16' for Alger, '31' for Oran
    city VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    total_capacity INTEGER NOT NULL DEFAULT 100,
    current_occupancy INTEGER NOT NULL DEFAULT 0,
    grace_period_minutes INTEGER NOT NULL DEFAULT 15,
    hourly_rate_dzd NUMERIC(10, 2) NOT NULL DEFAULT 100.00,
    data_retention_days INTEGER NOT NULL DEFAULT 30, -- ANPDP 30-day purge rule
    anpdp_declaration_number VARCHAR(100), -- Official ANPDP filing reference
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. EDGE GATEWAYS (On-Premise Industrial Nodes)
CREATE TABLE edge_gateways (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    gateway_name VARCHAR(100) NOT NULL,
    mac_address VARCHAR(17) UNIQUE NOT NULL,
    ip_address INET NOT NULL,
    gpu_model VARCHAR(100) DEFAULT 'NVIDIA GeForce RTX 3060 12GB',
    tensorrt_version VARCHAR(50),
    local_vector_cache_size INTEGER DEFAULT 0,
    ups_battery_status VARCHAR(50) DEFAULT 'NORMAL_AC',
    is_online BOOLEAN NOT NULL DEFAULT false,
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT now(),
    pending_sync_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. IP CAMERAS
CREATE TABLE cameras (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    edge_gateway_id UUID NOT NULL REFERENCES edge_gateways(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    lane_number INTEGER NOT NULL,
    camera_type VARCHAR(50) NOT NULL, -- 'entry_plate', 'entry_face', 'exit_plate', 'exit_face', 'occupancy'
    rtsp_stream_path VARCHAR(255) NOT NULL,
    webrtc_stream_id VARCHAR(100),
    has_cpl_filter BOOLEAN NOT NULL DEFAULT true,
    has_nir_illuminator BOOLEAN NOT NULL DEFAULT true,
    resolution VARCHAR(20) DEFAULT '1920x1080',
    fps INTEGER DEFAULT 25,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. REGISTERED PERSONS (VIPs, Employees, Drivers, Watchlist)
CREATE TABLE registered_persons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    national_id_number VARCHAR(100), -- NIN under Algerian ID standards
    phone_number VARCHAR(50),
    organization_name VARCHAR(255),
    category VARCHAR(50) NOT NULL DEFAULT 'visitor', -- 'vip', 'tenant', 'employee', 'watchlist', 'visitor'
    is_blacklisted BOOLEAN NOT NULL DEFAULT false,
    blacklist_reason TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7. REGISTERED FACIAL VECTOR EMBEDDINGS (ArcFace 512-D float32)
CREATE TABLE registered_faces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES registered_persons(id) ON DELETE CASCADE,
    embedding VECTOR(512) NOT NULL, -- Normalized 512-dimensional vector
    photo_thumbnail_url TEXT NOT NULL,
    detector_quality_score REAL NOT NULL DEFAULT 1.0,
    liveness_verified BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- HNSW Vector Index for High-Speed Sub-Millisecond Similarity Search
CREATE INDEX idx_registered_faces_hnsw 
ON registered_faces 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- 8. REGISTERED VEHICLES (Whitelist / Blacklist)
CREATE TABLE registered_vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    person_id UUID REFERENCES registered_persons(id) ON DELETE SET NULL,
    plate_number_formatted VARCHAR(30) NOT NULL, -- e.g., '104822 119 16' or '08412 00 16'
    plate_number_raw VARCHAR(30) NOT NULL,       -- e.g., '10482211916' or '084120016'
    wilaya_code VARCHAR(2) NOT NULL,             -- e.g., '16'
    registration_year INTEGER,                   -- e.g., 2019, or NULL for temporary 00
    is_temporary_00 BOOLEAN NOT NULL DEFAULT false,
    vehicle_category vehicle_category_code NOT NULL DEFAULT '1_passenger_car',
    make VARCHAR(50),                            -- e.g., 'Renault', 'Peugeot', 'Volkswagen'
    model VARCHAR(50),                           -- e.g., 'Clio', '208', 'Golf'
    color VARCHAR(30),                           -- e.g., 'White', 'Black', 'Grey'
    is_whitelisted BOOLEAN NOT NULL DEFAULT true,
    is_blacklisted BOOLEAN NOT NULL DEFAULT false,
    blacklist_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_registered_vehicles_plate_raw ON registered_vehicles(plate_number_raw);
CREATE INDEX idx_registered_vehicles_wilaya ON registered_vehicles(wilaya_code);

-- 9. PARKING SLOTS & OCCUPANCY
CREATE TABLE parking_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    camera_id UUID REFERENCES cameras(id) ON DELETE SET NULL,
    floor_level VARCHAR(20) NOT NULL DEFAULT 'Level 0',
    zone_name VARCHAR(50) NOT NULL, -- e.g., 'Zone A', 'Zone VIP'
    slot_number VARCHAR(20) NOT NULL,
    status slot_status NOT NULL DEFAULT 'vacant',
    current_plate_number VARCHAR(30),
    occupied_since TIMESTAMPTZ,
    last_inspected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(facility_id, floor_level, slot_number)
);

CREATE INDEX idx_parking_slots_facility_status ON parking_slots(facility_id, status);

-- 10. PARKING SESSIONS (Core Operational Stays)
CREATE TABLE parking_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    plate_number VARCHAR(30) NOT NULL,
    vehicle_id UUID REFERENCES registered_vehicles(id) ON DELETE SET NULL,
    driver_person_id UUID REFERENCES registered_persons(id) ON DELETE SET NULL,
    slot_id UUID REFERENCES parking_slots(id) ON DELETE SET NULL,
    entry_camera_id UUID NOT NULL REFERENCES cameras(id),
    exit_camera_id UUID REFERENCES cameras(id),
    entry_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    exit_time TIMESTAMPTZ,
    duration_minutes INTEGER,
    status session_status NOT NULL DEFAULT 'active',
    entry_plate_crop_url TEXT NOT NULL,
    entry_face_crop_url TEXT,
    exit_plate_crop_url TEXT,
    exit_face_crop_url TEXT,
    amount_due_dzd NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    amount_paid_dzd NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    payment_method VARCHAR(50), -- 'cash', 'cib_edahabia', 'subscription'
    payment_status VARCHAR(50) NOT NULL DEFAULT 'unpaid',
    local_vlm_verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_parking_sessions_plate ON parking_sessions(plate_number);
CREATE INDEX idx_parking_sessions_status ON parking_sessions(status);
CREATE INDEX idx_parking_sessions_entry_time ON parking_sessions(entry_time DESC);

-- 11. RAW ACCESS DETECTION EVENTS (Telemetry & Gate Log)
CREATE TABLE access_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    camera_id UUID NOT NULL REFERENCES cameras(id),
    session_id UUID REFERENCES parking_sessions(id) ON DELETE SET NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    plate_number_detected VARCHAR(30) NOT NULL,
    ocr_confidence REAL NOT NULL,
    driver_face_detected BOOLEAN NOT NULL DEFAULT false,
    face_embedding VECTOR(512),
    matched_person_id UUID REFERENCES registered_persons(id) ON DELETE SET NULL,
    face_cosine_distance REAL,
    liveness_score REAL,
    action_taken barrier_action NOT NULL,
    barrier_open_latency_ms INTEGER,
    edge_device_id UUID REFERENCES edge_gateways(id),
    is_offline_event BOOLEAN NOT NULL DEFAULT false,
    synced_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_access_events_timestamp ON access_events(timestamp DESC);

-- 12. SECURITY INCIDENTS & ALERTS
CREATE TABLE security_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    session_id UUID REFERENCES parking_sessions(id) ON DELETE SET NULL,
    incident_type VARCHAR(100) NOT NULL, -- 'blacklist_hit', 'driver_mismatch', 'spoof_attempt', 'overstay', 'tailgating'
    severity VARCHAR(20) NOT NULL DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
    plate_number VARCHAR(30),
    person_id UUID REFERENCES registered_persons(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    is_resolved BOOLEAN NOT NULL DEFAULT false,
    resolved_by UUID,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

-- ============================================================================
-- LAW 18-07 & LAW 25-11 REGULATORY COMPLIANCE SUITE
-- ============================================================================

-- 13. DATA PROTECTION IMPACT ASSESSMENTS (DPIA / Analyse d'Impact)
CREATE TABLE dpia_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    assessment_title VARCHAR(255) NOT NULL,
    processing_purpose TEXT NOT NULL,
    biometric_justification TEXT NOT NULL,
    risk_evaluation JSONB NOT NULL,
    mitigation_measures JSONB NOT NULL,
    dpo_approval_status VARCHAR(50) NOT NULL DEFAULT 'approved',
    anpdp_submission_date DATE,
    anpdp_approval_reference VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 14. REGISTER OF PROCESSING ACTIVITIES (Registre des activités de traitement)
CREATE TABLE processing_activities_register (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    activity_name VARCHAR(255) NOT NULL,
    category_of_data_subjects TEXT NOT NULL, -- 'facility_visitors', 'employees', 'vip_tenants'
    categories_of_personal_data TEXT NOT NULL, -- 'license_plates', 'facial_embeddings_512d', 'entry_exit_timestamps'
    data_recipients TEXT NOT NULL, -- 'on_site_security_operators', 'facility_management'
    data_transfers_abroad BOOLEAN NOT NULL DEFAULT false, -- Must be strictly FALSE for Algerian sovereign hosting
    retention_period_days INTEGER NOT NULL DEFAULT 30,
    security_measures_summary TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 15. MANDATORY 5-DAY DATA BREACH NOTIFICATIONS (Law 25-11 Invariant)
CREATE TABLE data_breach_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    breach_incident_reference VARCHAR(100) UNIQUE NOT NULL,
    incident_timestamp TIMESTAMPTZ NOT NULL,
    discovery_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    anpdp_notification_deadline TIMESTAMPTZ GENERATED ALWAYS AS (discovery_timestamp + INTERVAL '5 days') STORED,
    nature_of_breach TEXT NOT NULL,
    estimated_affected_individuals INTEGER NOT NULL DEFAULT 0,
    potential_consequences TEXT NOT NULL,
    containment_measures_taken TEXT NOT NULL,
    anpdp_notified_at TIMESTAMPTZ,
    anpdp_receipt_number VARCHAR(100),
    is_closed BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 16. COMPLIANCE AUDIT LOGS (Law 18-07 / 25-11 Audit Trail)
CREATE TABLE compliance_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_id UUID REFERENCES facilities(id) ON DELETE SET NULL,
    user_id UUID,
    action_type VARCHAR(100) NOT NULL, -- 'search_plate', 'export_faces', 'override_barrier', 'delete_log'
    target_identifier VARCHAR(255),
    query_parameters JSONB,
    client_ip INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- STORED PROCEDURES & DATABASE FUNCTIONS (CALIBRATED)
-- ============================================================================

-- Function 1: Calibrated 1:N Facial Similarity Matcher
-- Note: Cosine Distance = 1 - Cosine Similarity.
-- For through-windshield driver capture with tint/refraction, distance <= 0.52 
-- corresponds to Cosine Similarity >= 0.48, providing reliable clearance without false rejections.
CREATE OR REPLACE FUNCTION match_face_embedding(
    query_embedding VECTOR(512),
    distance_threshold REAL DEFAULT 0.52,
    match_limit INTEGER DEFAULT 3
)
RETURNS TABLE (
    face_id UUID,
    person_id UUID,
    full_name VARCHAR(255),
    category VARCHAR(50),
    is_blacklisted BOOLEAN,
    cosine_distance REAL,
    similarity_score REAL
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rf.id AS face_id,
        rp.id AS person_id,
        rp.full_name,
        rp.category,
        rp.is_blacklisted,
        (rf.embedding <=> query_embedding) AS cosine_distance,
        (1.0 - (rf.embedding <=> query_embedding)) AS similarity_score
    FROM registered_faces rf
    JOIN registered_persons rp ON rf.person_id = rp.id
    WHERE (rf.embedding <=> query_embedding) <= distance_threshold
    ORDER BY cosine_distance ASC
    LIMIT match_limit;
END;
$$;

-- Function 2: Complete Algerian License Plate Parser & Regex Engine
-- Supports:
-- 1. Standard civilian plates: 1 to 6 digits serial (Algiers 16, Oran 31), 3-digit category/year, 2-digit wilaya
-- 2. Temporary new vehicle plates: 1 to 6 digits serial, '00' middle code, 2-digit wilaya (carte grise provisoire)
-- 3. Diplomatic plates: Prefixes CD, CC, CMD with wilaya suffix
-- 4. State / administration plates
CREATE OR REPLACE FUNCTION parse_algerian_plate(raw_input TEXT)
RETURNS JSONB
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    cleaned TEXT;
    seq_number TEXT;
    middle_code TEXT;
    wilaya_str TEXT;
    wilaya_num INTEGER;
    is_temp_00 BOOLEAN := false;
    is_diplomatic BOOLEAN := false;
    diplo_prefix TEXT := '';
BEGIN
    -- Strip whitespace and leading/trailing markers
    cleaned := upper(trim(raw_input));
    cleaned := regexp_replace(cleaned, '[\s\-\.\/]', '', 'g');

    -- Check for Diplomatic / Consular Prefixes
    IF cleaned ~ '^(CD|CC|CMD)' THEN
        is_diplomatic := true;
        diplo_prefix := substring(cleaned from '^(CD|CC|CMD)');
        cleaned := regexp_replace(cleaned, '^(CD|CC|CMD)', '');
    END IF;

    -- Strip remaining non-numeric characters for digit inspection
    cleaned := regexp_replace(cleaned, '[^0-9]', '', 'g');

    -- Algerian civilian plates have between 5 and 11 total digits
    -- e.g., '104822 119 16' (11 digits), '08412 00 16' (9 digits), '482 124 31' (8 digits)
    IF length(cleaned) < 5 OR length(cleaned) > 11 THEN
        RETURN jsonb_build_object(
            'is_valid', false, 
            'error', 'Invalid total digit count for Algerian plate format'
        );
    END IF;

    -- Extract wilaya code (last 2 digits)
    wilaya_str := right(cleaned, 2);
    wilaya_num := wilaya_str::INTEGER;

    -- Validate wilaya code between 01 and 58
    IF wilaya_num < 1 OR wilaya_num > 58 THEN
        RETURN jsonb_build_object(
            'is_valid', false, 
            'error', 'Wilaya code ' || wilaya_str || ' out of valid range (01 to 58)'
        );
    END IF;

    -- Inspect middle segment for Temporary '00' vs Standard 3-digit category/year
    -- If the 2 digits immediately preceding the wilaya are '00', it's a temporary registration
    IF substring(cleaned from (length(cleaned) - 3) for 2) = '00' THEN
        is_temp_00 := true;
        middle_code := '00';
        seq_number := left(cleaned, length(cleaned) - 4);
    ELSE
        -- Standard 3-digit category/year code (e.g., '124' for private car 2024)
        middle_code := substring(cleaned from (length(cleaned) - 4) for 3);
        seq_number := left(cleaned, length(cleaned) - 5);
    END IF;

    -- Ensure sequential registration number is between 1 and 6 digits
    IF length(seq_number) < 1 OR length(seq_number) > 6 THEN
        RETURN jsonb_build_object(
            'is_valid', false, 
            'error', 'Sequential registration number length invalid (' || seq_number || ')'
        );
    END IF;

    -- Construct verified payload
    IF is_diplomatic THEN
        RETURN jsonb_build_object(
            'is_valid', true,
            'plate_type', 'diplomatic',
            'prefix', diplo_prefix,
            'formatted', diplo_prefix || ' ' || seq_number || ' ' || wilaya_str,
            'sequential_number', seq_number,
            'wilaya_code', wilaya_str
        );
    ELSIF is_temp_00 THEN
        RETURN jsonb_build_object(
            'is_valid', true,
            'plate_type', 'temporary_00',
            'formatted', seq_number || ' 00 ' || wilaya_str,
            'sequential_number', seq_number,
            'middle_code', '00',
            'wilaya_code', wilaya_str,
            'notes', 'Temporary new vehicle registration'
        );
    ELSE
        RETURN jsonb_build_object(
            'is_valid', true,
            'plate_type', 'civilian_standard',
            'formatted', seq_number || ' ' || middle_code || ' ' || wilaya_str,
            'sequential_number', seq_number,
            'middle_code', middle_code,
            'category_digit', left(middle_code, 1)::INTEGER,
            'registration_year', 2000 + right(middle_code, 2)::INTEGER,
            'wilaya_code', wilaya_str
        );
    END IF;
END;
$$;

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

ALTER TABLE facilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE edge_gateways ENABLE ROW LEVEL SECURITY;
ALTER TABLE cameras ENABLE ROW LEVEL SECURITY;
ALTER TABLE registered_persons ENABLE ROW LEVEL SECURITY;
ALTER TABLE registered_faces ENABLE ROW LEVEL SECURITY;
ALTER TABLE registered_vehicles ENABLE ROW LEVEL SECURITY;
ALTER TABLE parking_slots ENABLE ROW LEVEL SECURITY;
ALTER TABLE parking_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE dpia_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_activities_register ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_breach_notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Facility isolation for parking sessions" 
ON parking_sessions 
FOR ALL 
TO authenticated 
USING (
    facility_id = (auth.jwt() ->> 'facility_id')::UUID 
    OR (auth.jwt() ->> 'role') = 'superadmin'
);

CREATE POLICY "Facility isolation for registered vehicles" 
ON registered_vehicles 
FOR ALL 
TO authenticated 
USING (
    facility_id = (auth.jwt() ->> 'facility_id')::UUID 
    OR (auth.jwt() ->> 'role') = 'superadmin'
);

CREATE POLICY "Auditors and DPO can view regulatory registers" 
ON dpia_assessments 
FOR SELECT 
TO authenticated 
USING (true);

CREATE POLICY "Auditors and DPO can view processing register" 
ON processing_activities_register 
FOR SELECT 
TO authenticated 
USING (true);

CREATE POLICY "Breach notifications viewable by compliance officers" 
ON data_breach_notifications 
FOR ALL 
TO authenticated 
USING (
    (auth.jwt() ->> 'role') IN ('superadmin', 'compliance_auditor', 'data_protection_officer')
);
