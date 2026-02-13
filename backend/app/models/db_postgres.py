"""
PostgreSQL database backend - drop-in replacement for database.py (SQLite).

Uses psycopg2 with the same function signatures as SimpleDB so the rest
of the application can swap backends transparently via db_factory.
"""

import os
import uuid
from datetime import datetime
from typing import Optional

import psycopg2
import psycopg2.extras
import bcrypt
from dotenv import load_dotenv

load_dotenv()


def _get_pg_dsn() -> str:
    """Build a PostgreSQL DSN from environment variables."""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "tenm_wt")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    sslmode = os.getenv("DB_SSLMODE", "require")
    return f"host={host} port={port} dbname={name} user={user} password={password} sslmode={sslmode}"


def get_db_connection():
    """Return a new PostgreSQL connection with RealDictCursor."""
    conn = psycopg2.connect(_get_pg_dsn())
    conn.autocommit = False
    return conn


def _dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db():
    """Create tables if they do not exist (PostgreSQL version)."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(36) PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            is_approved INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Default admin account
    cur.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        admin_id = str(uuid.uuid4())
        admin_pw = hash_password("admin")
        cur.execute(
            "INSERT INTO users (id, username, password_hash, name, role, is_approved) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (admin_id, "admin", admin_pw, "\uad00\ub9ac\uc790", "admin", 1),
        )

    cur.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id VARCHAR(36) PRIMARY KEY,
            patient_number VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            gender VARCHAR(10) NOT NULL,
            birth_date VARCHAR(20) NOT NULL,
            height_cm DOUBLE PRECISION NOT NULL,
            diagnosis TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
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
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS patient_tags (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            color VARCHAR(20) DEFAULT '#6B7280',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS patient_tag_map (
            patient_id VARCHAR(36) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
            tag_id VARCHAR(36) NOT NULL REFERENCES patient_tags(id) ON DELETE CASCADE,
            PRIMARY KEY (patient_id, tag_id)
        )
    """)

    cur.execute("""
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
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            type VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT,
            data TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36),
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(100) NOT NULL,
            resource_id VARCHAR(36),
            details TEXT,
            ip_address VARCHAR(45),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


# ---------------------------------------------------------------------------
# Helper to convert Row → dict with string timestamps
# ---------------------------------------------------------------------------

def _row_to_dict(row: Optional[dict]) -> Optional[dict]:
    """Convert a RealDictRow to a plain dict, stringifying datetimes."""
    if row is None:
        return None
    result = dict(row)
    for k, v in result.items():
        if isinstance(v, datetime):
            result[k] = v.isoformat()
    return result


def _rows_to_dicts(rows) -> list:
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# SimpleDB-compatible class
# ---------------------------------------------------------------------------

class SimpleDB:
    """PostgreSQL implementation matching the SQLite SimpleDB interface."""

    @staticmethod
    def generate_id() -> str:
        return str(uuid.uuid4())

    # ===== Users =====

    @staticmethod
    def create_user(data: dict) -> dict:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        user_id = SimpleDB.generate_id()
        now = datetime.now().isoformat()
        pw_hash = hash_password(data["password"])
        cur.execute(
            "INSERT INTO users (id, username, password_hash, name, role, is_approved, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (user_id, data["username"], pw_hash, data["name"],
             data.get("role", "therapist"), data.get("is_approved", 0), now),
        )
        conn.commit()
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        result = _row_to_dict(cur.fetchone())
        cur.close()
        conn.close()
        del result["password_hash"]
        return result

    @staticmethod
    def get_user_by_username(username: str) -> Optional[dict]:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return _row_to_dict(row)

    @staticmethod
    def get_user(user_id: str) -> Optional[dict]:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            result = _row_to_dict(row)
            result.pop("password_hash", None)
            return result
        return None

    @staticmethod
    def get_pending_therapists() -> list:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute(
            "SELECT id, username, name, role, is_approved, created_at "
            "FROM users WHERE role = 'therapist' AND is_approved = 0 "
            "ORDER BY created_at DESC"
        )
        results = _rows_to_dicts(cur.fetchall())
        cur.close()
        conn.close()
        return results

    @staticmethod
    def get_all_therapists() -> list:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute(
            "SELECT id, username, name, role, is_approved, created_at "
            "FROM users WHERE role = 'therapist' ORDER BY created_at DESC"
        )
        results = _rows_to_dicts(cur.fetchall())
        cur.close()
        conn.close()
        return results

    @staticmethod
    def approve_therapist(user_id: str) -> Optional[dict]:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute(
            "UPDATE users SET is_approved = 1 WHERE id = %s AND role = 'therapist'",
            (user_id,),
        )
        conn.commit()
        if cur.rowcount == 0:
            cur.close()
            conn.close()
            return None
        cur.execute(
            "SELECT id, username, name, role, is_approved, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        result = _row_to_dict(cur.fetchone())
        cur.close()
        conn.close()
        return result

    @staticmethod
    def delete_user(user_id: str) -> bool:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = %s AND role = 'therapist'", (user_id,))
        conn.commit()
        deleted = cur.rowcount > 0
        cur.close()
        conn.close()
        return deleted

    # ===== Patients =====

    @staticmethod
    def create_patient(data: dict) -> dict:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        patient_id = SimpleDB.generate_id()
        now = datetime.now().isoformat()
        cur.execute(
            "INSERT INTO patients (id, patient_number, name, gender, birth_date, height_cm, diagnosis, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (patient_id, data["patient_number"], data["name"], data["gender"],
             data["birth_date"], data["height_cm"], data.get("diagnosis"), now),
        )
        conn.commit()
        cur.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
        result = _row_to_dict(cur.fetchone())
        cur.close()
        conn.close()
        return result

    @staticmethod
    def get_patients(limit: int = 50) -> list:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute("SELECT * FROM patients ORDER BY created_at DESC LIMIT %s", (limit,))
        results = _rows_to_dicts(cur.fetchall())
        cur.close()
        conn.close()
        return results

    @staticmethod
    def search_patients(query: str) -> list:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        term = f"%{query}%"
        cur.execute(
            "SELECT * FROM patients WHERE name ILIKE %s OR patient_number ILIKE %s "
            "ORDER BY created_at DESC",
            (term, term),
        )
        results = _rows_to_dicts(cur.fetchall())
        cur.close()
        conn.close()
        return results

    @staticmethod
    def get_patient(patient_id: str) -> Optional[dict]:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return _row_to_dict(row)

    @staticmethod
    def update_patient(patient_id: str, data: dict) -> Optional[dict]:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        set_parts = [f"{k} = %s" for k in data.keys()]
        values = list(data.values()) + [patient_id]
        cur.execute(
            f"UPDATE patients SET {', '.join(set_parts)} WHERE id = %s",
            values,
        )
        conn.commit()
        if cur.rowcount == 0:
            cur.close()
            conn.close()
            return None
        cur.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
        result = _row_to_dict(cur.fetchone())
        cur.close()
        conn.close()
        return result

    @staticmethod
    def delete_patient(patient_id: str) -> bool:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM patients WHERE id = %s", (patient_id,))
        conn.commit()
        deleted = cur.rowcount > 0
        cur.close()
        conn.close()
        return deleted

    # ===== Walk Tests =====

    @staticmethod
    def create_test(data: dict) -> dict:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        test_id = SimpleDB.generate_id()
        now = datetime.now().isoformat()
        test_type = data.get("test_type", "10MWT")
        cur.execute(
            "INSERT INTO walk_tests "
            "(id, patient_id, test_date, test_type, walk_time_seconds, walk_speed_mps, video_url, analysis_data, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (test_id, data["patient_id"], now, test_type,
             data["walk_time_seconds"], data["walk_speed_mps"],
             data.get("video_url"), data.get("analysis_data"), now),
        )
        conn.commit()
        cur.execute("SELECT * FROM walk_tests WHERE id = %s", (test_id,))
        result = _row_to_dict(cur.fetchone())
        cur.close()
        conn.close()
        return result

    @staticmethod
    def get_patient_tests(patient_id: str, test_type: str = None) -> list:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        if test_type and test_type != "ALL":
            cur.execute(
                "SELECT * FROM walk_tests WHERE patient_id = %s AND test_type = %s ORDER BY test_date DESC",
                (patient_id, test_type),
            )
        else:
            cur.execute(
                "SELECT * FROM walk_tests WHERE patient_id = %s ORDER BY test_date DESC",
                (patient_id,),
            )
        results = _rows_to_dicts(cur.fetchall())
        cur.close()
        conn.close()
        return results

    @staticmethod
    def get_test(test_id: str) -> Optional[dict]:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute("SELECT * FROM walk_tests WHERE id = %s", (test_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return _row_to_dict(row)

    @staticmethod
    def update_test_date(test_id: str, test_date: str) -> Optional[dict]:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute("UPDATE walk_tests SET test_date = %s WHERE id = %s", (test_date, test_id))
        conn.commit()
        if cur.rowcount == 0:
            cur.close()
            conn.close()
            return None
        cur.execute("SELECT * FROM walk_tests WHERE id = %s", (test_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return _row_to_dict(row)

    @staticmethod
    def update_test_notes(test_id: str, notes: str) -> Optional[dict]:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute("UPDATE walk_tests SET notes = %s WHERE id = %s", (notes, test_id))
        conn.commit()
        if cur.rowcount == 0:
            cur.close()
            conn.close()
            return None
        cur.execute("SELECT * FROM walk_tests WHERE id = %s", (test_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return _row_to_dict(row)

    @staticmethod
    def delete_test(test_id: str) -> bool:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM walk_tests WHERE id = %s", (test_id,))
        conn.commit()
        deleted = cur.rowcount > 0
        cur.close()
        conn.close()
        return deleted

    # ===== Patient Tags =====

    @staticmethod
    def create_tag(name: str, color: str = "#6B7280") -> dict:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        tag_id = SimpleDB.generate_id()
        now = datetime.now().isoformat()
        cur.execute(
            "INSERT INTO patient_tags (id, name, color, created_at) VALUES (%s, %s, %s, %s)",
            (tag_id, name, color, now),
        )
        conn.commit()
        cur.execute("SELECT * FROM patient_tags WHERE id = %s", (tag_id,))
        result = _row_to_dict(cur.fetchone())
        cur.close()
        conn.close()
        return result

    @staticmethod
    def get_all_tags() -> list:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute("SELECT * FROM patient_tags ORDER BY name")
        results = _rows_to_dicts(cur.fetchall())
        cur.close()
        conn.close()
        return results

    @staticmethod
    def delete_tag(tag_id: str) -> bool:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM patient_tags WHERE id = %s", (tag_id,))
        conn.commit()
        deleted = cur.rowcount > 0
        cur.close()
        conn.close()
        return deleted

    @staticmethod
    def add_patient_tag(patient_id: str, tag_id: str) -> bool:
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO patient_tag_map (patient_id, tag_id) VALUES (%s, %s)",
                (patient_id, tag_id),
            )
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception:
            conn.rollback()
            cur.close()
            conn.close()
            return False

    @staticmethod
    def remove_patient_tag(patient_id: str, tag_id: str) -> bool:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM patient_tag_map WHERE patient_id = %s AND tag_id = %s",
            (patient_id, tag_id),
        )
        conn.commit()
        deleted = cur.rowcount > 0
        cur.close()
        conn.close()
        return deleted

    @staticmethod
    def get_patient_tags(patient_id: str) -> list:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute(
            "SELECT t.* FROM patient_tags t "
            "JOIN patient_tag_map m ON t.id = m.tag_id "
            "WHERE m.patient_id = %s ORDER BY t.name",
            (patient_id,),
        )
        results = _rows_to_dicts(cur.fetchall())
        cur.close()
        conn.close()
        return results

    @staticmethod
    def get_patients_by_tag(tag_id: str) -> list:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute(
            "SELECT p.* FROM patients p "
            "JOIN patient_tag_map m ON p.id = m.patient_id "
            "WHERE m.tag_id = %s ORDER BY p.created_at DESC",
            (tag_id,),
        )
        results = _rows_to_dicts(cur.fetchall())
        cur.close()
        conn.close()
        return results

    # ===== Patient Goals =====

    @staticmethod
    def create_goal(data: dict) -> dict:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        goal_id = SimpleDB.generate_id()
        now = datetime.now().isoformat()
        cur.execute(
            "INSERT INTO patient_goals "
            "(id, patient_id, test_type, target_speed_mps, target_time_seconds, target_score, target_date, status, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', %s)",
            (goal_id, data["patient_id"], data.get("test_type", "10MWT"),
             data.get("target_speed_mps"), data.get("target_time_seconds"),
             data.get("target_score"), data.get("target_date"), now),
        )
        conn.commit()
        cur.execute("SELECT * FROM patient_goals WHERE id = %s", (goal_id,))
        result = _row_to_dict(cur.fetchone())
        cur.close()
        conn.close()
        return result

    @staticmethod
    def get_patient_goals(patient_id: str, status: str = None) -> list:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        if status:
            cur.execute(
                "SELECT * FROM patient_goals WHERE patient_id = %s AND status = %s ORDER BY created_at DESC",
                (patient_id, status),
            )
        else:
            cur.execute(
                "SELECT * FROM patient_goals WHERE patient_id = %s ORDER BY created_at DESC",
                (patient_id,),
            )
        results = _rows_to_dicts(cur.fetchall())
        cur.close()
        conn.close()
        return results

    @staticmethod
    def get_goal(goal_id: str) -> Optional[dict]:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute("SELECT * FROM patient_goals WHERE id = %s", (goal_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return _row_to_dict(row)

    @staticmethod
    def update_goal(goal_id: str, data: dict) -> Optional[dict]:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        set_parts = [f"{k} = %s" for k in data.keys()]
        values = list(data.values()) + [goal_id]
        cur.execute(
            f"UPDATE patient_goals SET {', '.join(set_parts)} WHERE id = %s",
            values,
        )
        conn.commit()
        if cur.rowcount == 0:
            cur.close()
            conn.close()
            return None
        cur.execute("SELECT * FROM patient_goals WHERE id = %s", (goal_id,))
        result = _row_to_dict(cur.fetchone())
        cur.close()
        conn.close()
        return result

    @staticmethod
    def delete_goal(goal_id: str) -> bool:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM patient_goals WHERE id = %s", (goal_id,))
        conn.commit()
        deleted = cur.rowcount > 0
        cur.close()
        conn.close()
        return deleted

    # ===== Notifications =====

    @staticmethod
    def create_notification(data: dict) -> dict:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        noti_id = SimpleDB.generate_id()
        now = datetime.now().isoformat()
        cur.execute(
            "INSERT INTO notifications (id, user_id, type, title, message, data, is_read, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, 0, %s)",
            (noti_id, data['user_id'], data['type'], data['title'],
             data['message'], data.get('data'), now),
        )
        conn.commit()
        cur.execute("SELECT * FROM notifications WHERE id = %s", (noti_id,))
        result = _row_to_dict(cur.fetchone())
        cur.close()
        conn.close()
        return result

    @staticmethod
    def get_notifications(user_id: str, limit: int = 20, offset: int = 0) -> list:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute(
            "SELECT * FROM notifications WHERE user_id = %s "
            "ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (user_id, limit, offset),
        )
        results = _rows_to_dicts(cur.fetchall())
        cur.close()
        conn.close()
        return results

    @staticmethod
    def get_unread_count(user_id: str) -> int:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = %s AND is_read = 0",
            (user_id,),
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count

    @staticmethod
    def mark_notification_read(noti_id: str) -> bool:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE notifications SET is_read = 1 WHERE id = %s", (noti_id,))
        conn.commit()
        updated = cur.rowcount > 0
        cur.close()
        conn.close()
        return updated

    @staticmethod
    def mark_all_read(user_id: str) -> int:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE notifications SET is_read = 1 WHERE user_id = %s AND is_read = 0",
            (user_id,),
        )
        conn.commit()
        count = cur.rowcount
        cur.close()
        conn.close()
        return count

    # ===== Admin Stats =====

    @staticmethod
    def get_all_tests_count() -> int:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM walk_tests")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count

    @staticmethod
    def get_tests_by_period() -> list:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute(
            "SELECT TO_CHAR(test_date, 'YYYY-MM') AS period, COUNT(*) AS count "
            "FROM walk_tests GROUP BY period ORDER BY period DESC LIMIT 12"
        )
        results = _rows_to_dicts(cur.fetchall())
        cur.close()
        conn.close()
        return results

    @staticmethod
    def get_all_latest_tests() -> list:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute("""
            SELECT w.* FROM walk_tests w
            INNER JOIN (
                SELECT patient_id, test_type, MAX(test_date) AS max_date
                FROM walk_tests WHERE test_type IN ('10MWT', 'TUG')
                GROUP BY patient_id, test_type
            ) latest ON w.patient_id = latest.patient_id
                AND w.test_type = latest.test_type
                AND w.test_date = latest.max_date
            ORDER BY w.patient_id, w.test_type
        """)
        results = _rows_to_dicts(cur.fetchall())
        cur.close()
        conn.close()
        return results

    @staticmethod
    def get_tag_stats() -> list:
        conn = get_db_connection()
        cur = _dict_cursor(conn)
        cur.execute("""
            SELECT t.name AS tag_name, t.color,
                   COUNT(DISTINCT m.patient_id) AS patient_count,
                   AVG(w.walk_speed_mps) AS avg_speed
            FROM patient_tags t
            LEFT JOIN patient_tag_map m ON t.id = m.tag_id
            LEFT JOIN (
                SELECT patient_id, walk_speed_mps
                FROM walk_tests WHERE test_type = '10MWT'
                AND walk_speed_mps > 0
            ) w ON m.patient_id = w.patient_id
            GROUP BY t.id, t.name, t.color
            ORDER BY patient_count DESC
        """)
        results = _rows_to_dicts(cur.fetchall())
        cur.close()
        conn.close()
        return results


# Module-level convenience instance
db = SimpleDB()
