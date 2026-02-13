-- PostgreSQL initial schema for 10MWT application
-- Run with: psql -d tenm_wt -f 001_initial_schema.sql

BEGIN;

-- Users table (admin + therapists)
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    is_approved INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Patients table
CREATE TABLE IF NOT EXISTS patients (
    id VARCHAR(36) PRIMARY KEY,
    patient_number VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    gender VARCHAR(10) NOT NULL,
    birth_date VARCHAR(20) NOT NULL,
    height_cm DOUBLE PRECISION NOT NULL,
    diagnosis TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Walk tests table
CREATE TABLE IF NOT EXISTS walk_tests (
    id VARCHAR(36) PRIMARY KEY,
    patient_id VARCHAR(36) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    test_date TIMESTAMP DEFAULT NOW(),
    test_type VARCHAR(20) DEFAULT '10MWT',
    walk_time_seconds DOUBLE PRECISION NOT NULL,
    walk_speed_mps DOUBLE PRECISION NOT NULL,
    video_url TEXT,
    analysis_data TEXT,
    notes TEXT,
    therapist_id VARCHAR(36),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_walk_tests_patient_id ON walk_tests(patient_id);
CREATE INDEX IF NOT EXISTS idx_walk_tests_test_date ON walk_tests(test_date);
CREATE INDEX IF NOT EXISTS idx_walk_tests_test_type ON walk_tests(test_type);

-- Patient tags
CREATE TABLE IF NOT EXISTS patient_tags (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    color VARCHAR(20) DEFAULT '#6B7280',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Patient-tag mapping (N:N)
CREATE TABLE IF NOT EXISTS patient_tag_map (
    patient_id VARCHAR(36) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    tag_id VARCHAR(36) NOT NULL REFERENCES patient_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (patient_id, tag_id)
);

-- Patient goals
CREATE TABLE IF NOT EXISTS patient_goals (
    id VARCHAR(36) PRIMARY KEY,
    patient_id VARCHAR(36) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    test_type VARCHAR(20) NOT NULL DEFAULT '10MWT',
    target_speed_mps DOUBLE PRECISION,
    target_time_seconds DOUBLE PRECISION,
    target_score INTEGER,
    target_date VARCHAR(30),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    achieved_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_patient_goals_patient_id ON patient_goals(patient_id);

-- Audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(36),
    details TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);

COMMIT;
