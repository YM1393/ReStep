-- 10m Walk Test Database Schema for Supabase

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Admins table (관리자 계정)
CREATE TABLE IF NOT EXISTS admins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 기본 관리자 계정 (admin/admin)
-- 비밀번호는 bcrypt 해시: admin
INSERT INTO admins (username, password_hash, name)
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.G4rKQTWXmhJPjK', 'Administrator')
ON CONFLICT (username) DO NOTHING;

-- Patients table
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_number VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    gender VARCHAR(1) NOT NULL CHECK (gender IN ('M', 'F')),
    birth_date DATE NOT NULL,
    height_cm DECIMAL(5,2) NOT NULL CHECK (height_cm > 0 AND height_cm < 300),
    diagnosis TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Walk tests table
CREATE TABLE IF NOT EXISTS walk_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    test_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    walk_time_seconds DECIMAL(6,2) NOT NULL CHECK (walk_time_seconds > 0),
    walk_speed_mps DECIMAL(4,2) NOT NULL CHECK (walk_speed_mps > 0),
    video_url TEXT,
    analysis_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_patients_patient_number ON patients(patient_number);
CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(name);
CREATE INDEX IF NOT EXISTS idx_walk_tests_patient_id ON walk_tests(patient_id);
CREATE INDEX IF NOT EXISTS idx_walk_tests_test_date ON walk_tests(test_date DESC);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for patients table
DROP TRIGGER IF EXISTS update_patients_updated_at ON patients;
CREATE TRIGGER update_patients_updated_at
    BEFORE UPDATE ON patients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) policies
-- Enable RLS
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE walk_tests ENABLE ROW LEVEL SECURITY;

-- Allow all operations for authenticated users (adjust as needed)
CREATE POLICY "Allow all for authenticated users" ON patients
    FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow all for authenticated users" ON walk_tests
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Sample data (optional, for testing)
-- INSERT INTO patients (patient_number, name, gender, birth_date, height_cm, diagnosis)
-- VALUES
--     ('PT-001', 'John Doe', 'M', '1960-05-15', 175.5, 'Stroke rehabilitation'),
--     ('PT-002', 'Jane Smith', 'F', '1955-08-22', 162.0, 'Parkinson disease');
