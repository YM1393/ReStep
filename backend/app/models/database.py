import os
import sqlite3
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import bcrypt

load_dotenv()

# SQLite 데이터베이스 경로
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "database.db")

def get_db_connection():
    """SQLite 연결 반환"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """비밀번호 검증"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def init_db():
    """데이터베이스 테이블 초기화"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # users 테이블 (관리자 + 물리치료사)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            is_approved INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 기본 관리자 계정 생성 (없으면)
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        import uuid
        admin_id = str(uuid.uuid4())
        admin_password_hash = hash_password("admin")
        cursor.execute("""
            INSERT INTO users (id, username, password_hash, name, role, is_approved)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (admin_id, "admin", admin_password_hash, "관리자", "admin", 1))

    # patients 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id TEXT PRIMARY KEY,
            patient_number TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            gender TEXT NOT NULL,
            birth_date TEXT NOT NULL,
            height_cm REAL NOT NULL,
            diagnosis TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # walk_tests 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS walk_tests (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            test_date TEXT DEFAULT CURRENT_TIMESTAMP,
            test_type TEXT DEFAULT '10MWT',
            walk_time_seconds REAL NOT NULL,
            walk_speed_mps REAL NOT NULL,
            video_url TEXT,
            analysis_data TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE
        )
    """)

    # 기존 테이블에 notes 컬럼이 없으면 추가 (마이그레이션)
    cursor.execute("PRAGMA table_info(walk_tests)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'notes' not in columns:
        cursor.execute("ALTER TABLE walk_tests ADD COLUMN notes TEXT")

    # 기존 테이블에 test_type 컬럼이 없으면 추가 (마이그레이션)
    if 'test_type' not in columns:
        cursor.execute("ALTER TABLE walk_tests ADD COLUMN test_type TEXT DEFAULT '10MWT'")

    # therapist_id 컬럼 추가 (관리자 대시보드 치료사별 통계용)
    if 'therapist_id' not in columns:
        cursor.execute("ALTER TABLE walk_tests ADD COLUMN therapist_id TEXT")

    # sites 테이블 (multi-site / multi-tenant)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sites (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            admin_user_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # site_id 컬럼 추가 (마이그레이션 - nullable for backward compat)
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [col[1] for col in cursor.fetchall()]
    if 'site_id' not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN site_id TEXT")

    cursor.execute("PRAGMA table_info(patients)")
    patient_columns = [col[1] for col in cursor.fetchall()]
    if 'site_id' not in patient_columns:
        cursor.execute("ALTER TABLE patients ADD COLUMN site_id TEXT")

    # Re-read walk_tests columns since we already read them above
    cursor.execute("PRAGMA table_info(walk_tests)")
    wt_cols = [col[1] for col in cursor.fetchall()]
    if 'site_id' not in wt_cols:
        cursor.execute("ALTER TABLE walk_tests ADD COLUMN site_id TEXT")

    # 환자 태그 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_tags (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            color TEXT DEFAULT '#6B7280',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 환자-태그 매핑 (N:N)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_tag_map (
            patient_id TEXT NOT NULL,
            tag_id TEXT NOT NULL,
            PRIMARY KEY (patient_id, tag_id),
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES patient_tags(id) ON DELETE CASCADE
        )
    """)

    # 환자 목표 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_goals (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            test_type TEXT NOT NULL DEFAULT '10MWT',
            target_speed_mps REAL,
            target_time_seconds REAL,
            target_score INTEGER,
            target_date TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            achieved_at TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
    """)

    # 보행 경로 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_walking_routes (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            origin_address TEXT NOT NULL,
            origin_lat REAL NOT NULL,
            origin_lng REAL NOT NULL,
            dest_address TEXT NOT NULL,
            dest_lat REAL NOT NULL,
            dest_lng REAL NOT NULL,
            distance_meters REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
    """)

    # 맞춤형 거리 목표 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_distance_goals (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            distance_meters REAL NOT NULL,
            label TEXT NOT NULL,
            emoji TEXT DEFAULT '📍',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
    """)

    # 알림 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            data TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # 감사 로그 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT,
            details TEXT,
            ip_address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# 앱 시작 시 DB 초기화
init_db()


class SimpleDB:
    """간단한 DB 헬퍼 클래스"""

    @staticmethod
    def generate_id():
        """UUID 생성"""
        import uuid
        return str(uuid.uuid4())

    # ===== Users =====
    @staticmethod
    def create_user(data: dict) -> dict:
        """사용자 생성"""
        conn = get_db_connection()
        cursor = conn.cursor()

        user_id = SimpleDB.generate_id()
        now = datetime.now().isoformat()
        password_hash = hash_password(data['password'])

        cursor.execute("""
            INSERT INTO users (id, username, password_hash, name, role, is_approved, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, data['username'], password_hash, data['name'],
              data.get('role', 'therapist'), data.get('is_approved', 0), now))

        conn.commit()

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        result = dict(cursor.fetchone())
        conn.close()
        # 비밀번호 해시 제거
        del result['password_hash']
        return result

    @staticmethod
    def get_user_by_username(username: str) -> Optional[dict]:
        """사용자명으로 사용자 조회 (로그인용)"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_user(user_id: str) -> Optional[dict]:
        """사용자 ID로 조회"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            result = dict(row)
            if 'password_hash' in result:
                del result['password_hash']
            return result
        return None

    @staticmethod
    def get_pending_therapists() -> list:
        """승인 대기 물리치료사 목록"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, name, role, is_approved, created_at
            FROM users WHERE role = 'therapist' AND is_approved = 0
            ORDER BY created_at DESC
        """)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def get_all_therapists() -> list:
        """모든 물리치료사 목록"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, name, role, is_approved, created_at
            FROM users WHERE role = 'therapist'
            ORDER BY created_at DESC
        """)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def approve_therapist(user_id: str) -> Optional[dict]:
        """물리치료사 승인"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_approved = 1 WHERE id = ? AND role = 'therapist'", (user_id,))
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return None

        cursor.execute("SELECT id, username, name, role, is_approved, created_at FROM users WHERE id = ?", (user_id,))
        result = dict(cursor.fetchone())
        conn.close()
        return result

    @staticmethod
    def delete_user(user_id: str) -> bool:
        """사용자 삭제"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ? AND role = 'therapist'", (user_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    # ===== Patients =====
    @staticmethod
    def create_patient(data: dict) -> dict:
        conn = get_db_connection()
        cursor = conn.cursor()

        patient_id = SimpleDB.generate_id()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO patients (id, patient_number, name, gender, birth_date, height_cm, diagnosis, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (patient_id, data['patient_number'], data['name'], data['gender'],
              data['birth_date'], data['height_cm'], data.get('diagnosis'), now))

        conn.commit()

        cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        result = dict(cursor.fetchone())
        conn.close()
        return result

    @staticmethod
    def get_patients(limit: int = 50) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients ORDER BY created_at DESC LIMIT ?", (limit,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def search_patients(query: str) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        search_term = f"%{query}%"
        cursor.execute("""
            SELECT * FROM patients
            WHERE name LIKE ? OR patient_number LIKE ?
            ORDER BY created_at DESC
        """, (search_term, search_term))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def get_patient(patient_id: str) -> Optional[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update_patient(patient_id: str, data: dict) -> Optional[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()

        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [patient_id]

        cursor.execute(f"UPDATE patients SET {set_clause} WHERE id = ?", values)
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return None

        cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        result = dict(cursor.fetchone())
        conn.close()
        return result

    @staticmethod
    def delete_patient(patient_id: str) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    # ===== Walk Tests =====
    @staticmethod
    def create_test(data: dict) -> dict:
        conn = get_db_connection()
        cursor = conn.cursor()

        test_id = SimpleDB.generate_id()
        now = datetime.now().isoformat()
        test_type = data.get('test_type', '10MWT')

        cursor.execute("""
            INSERT INTO walk_tests (id, patient_id, test_date, test_type, walk_time_seconds, walk_speed_mps, video_url, analysis_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (test_id, data['patient_id'], now, test_type, data['walk_time_seconds'],
              data['walk_speed_mps'], data.get('video_url'), data.get('analysis_data'), now))

        conn.commit()

        cursor.execute("SELECT * FROM walk_tests WHERE id = ?", (test_id,))
        result = dict(cursor.fetchone())
        conn.close()
        return result

    @staticmethod
    def get_patient_tests(patient_id: str, test_type: str = None) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        if test_type and test_type != 'ALL':
            cursor.execute("""
                SELECT * FROM walk_tests
                WHERE patient_id = ? AND test_type = ?
                ORDER BY test_date DESC
            """, (patient_id, test_type))
        else:
            cursor.execute("""
                SELECT * FROM walk_tests
                WHERE patient_id = ?
                ORDER BY test_date DESC
            """, (patient_id,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def get_test(test_id: str) -> Optional[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM walk_tests WHERE id = ?", (test_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update_test_date(test_id: str, test_date: str) -> Optional[dict]:
        """검사 날짜 수정"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE walk_tests SET test_date = ? WHERE id = ?",
            (test_date, test_id)
        )
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return None

        cursor.execute("SELECT * FROM walk_tests WHERE id = ?", (test_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update_test_notes(test_id: str, notes: str) -> Optional[dict]:
        """검사 메모 수정"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE walk_tests SET notes = ? WHERE id = ?",
            (notes, test_id)
        )
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return None

        cursor.execute("SELECT * FROM walk_tests WHERE id = ?", (test_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def delete_test(test_id: str) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM walk_tests WHERE id = ?", (test_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    # ===== Patient Tags =====
    @staticmethod
    def create_tag(name: str, color: str = '#6B7280') -> dict:
        conn = get_db_connection()
        cursor = conn.cursor()
        tag_id = SimpleDB.generate_id()
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO patient_tags (id, name, color, created_at) VALUES (?, ?, ?, ?)",
            (tag_id, name, color, now)
        )
        conn.commit()
        cursor.execute("SELECT * FROM patient_tags WHERE id = ?", (tag_id,))
        result = dict(cursor.fetchone())
        conn.close()
        return result

    @staticmethod
    def get_all_tags() -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patient_tags ORDER BY name")
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def delete_tag(tag_id: str) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM patient_tags WHERE id = ?", (tag_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    @staticmethod
    def add_patient_tag(patient_id: str, tag_id: str) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO patient_tag_map (patient_id, tag_id) VALUES (?, ?)",
                (patient_id, tag_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            conn.close()
            return False

    @staticmethod
    def remove_patient_tag(patient_id: str, tag_id: str) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM patient_tag_map WHERE patient_id = ? AND tag_id = ?",
            (patient_id, tag_id)
        )
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    @staticmethod
    def get_patient_tags(patient_id: str) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.* FROM patient_tags t
            JOIN patient_tag_map m ON t.id = m.tag_id
            WHERE m.patient_id = ?
            ORDER BY t.name
        """, (patient_id,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def get_patients_by_tag(tag_id: str) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.* FROM patients p
            JOIN patient_tag_map m ON p.id = m.patient_id
            WHERE m.tag_id = ?
            ORDER BY p.created_at DESC
        """, (tag_id,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    # ===== Patient Goals =====
    @staticmethod
    def create_goal(data: dict) -> dict:
        conn = get_db_connection()
        cursor = conn.cursor()
        goal_id = SimpleDB.generate_id()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO patient_goals (id, patient_id, test_type, target_speed_mps,
                target_time_seconds, target_score, target_date, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
        """, (goal_id, data['patient_id'], data.get('test_type', '10MWT'),
              data.get('target_speed_mps'), data.get('target_time_seconds'),
              data.get('target_score'), data.get('target_date'), now))
        conn.commit()
        cursor.execute("SELECT * FROM patient_goals WHERE id = ?", (goal_id,))
        result = dict(cursor.fetchone())
        conn.close()
        return result

    @staticmethod
    def get_patient_goals(patient_id: str, status: str = None) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        if status:
            cursor.execute(
                "SELECT * FROM patient_goals WHERE patient_id = ? AND status = ? ORDER BY created_at DESC",
                (patient_id, status)
            )
        else:
            cursor.execute(
                "SELECT * FROM patient_goals WHERE patient_id = ? ORDER BY created_at DESC",
                (patient_id,)
            )
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def get_goal(goal_id: str) -> Optional[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patient_goals WHERE id = ?", (goal_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def update_goal(goal_id: str, data: dict) -> Optional[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [goal_id]
        cursor.execute(f"UPDATE patient_goals SET {set_clause} WHERE id = ?", values)
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return None
        cursor.execute("SELECT * FROM patient_goals WHERE id = ?", (goal_id,))
        result = dict(cursor.fetchone())
        conn.close()
        return result

    @staticmethod
    def delete_goal(goal_id: str) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM patient_goals WHERE id = ?", (goal_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    # ===== Patient Walking Routes =====
    @staticmethod
    def create_walking_route(data: dict) -> dict:
        conn = get_db_connection()
        cursor = conn.cursor()
        route_id = SimpleDB.generate_id()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO patient_walking_routes
            (id, patient_id, origin_address, origin_lat, origin_lng, dest_address, dest_lat, dest_lng, distance_meters, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (route_id, data['patient_id'], data['origin_address'], data['origin_lat'], data['origin_lng'],
              data['dest_address'], data['dest_lat'], data['dest_lng'], data.get('distance_meters'), now))
        conn.commit()
        cursor.execute("SELECT * FROM patient_walking_routes WHERE id = ?", (route_id,))
        result = dict(cursor.fetchone())
        conn.close()
        return result

    @staticmethod
    def get_patient_walking_routes(patient_id: str) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM patient_walking_routes WHERE patient_id = ? ORDER BY created_at DESC",
            (patient_id,)
        )
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def delete_walking_route(route_id: str) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM patient_walking_routes WHERE id = ?", (route_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    # ===== Patient Distance Goals =====
    @staticmethod
    def create_distance_goal(data: dict) -> dict:
        conn = get_db_connection()
        cursor = conn.cursor()
        goal_id = SimpleDB.generate_id()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO patient_distance_goals (id, patient_id, distance_meters, label, emoji, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (goal_id, data['patient_id'], data['distance_meters'],
              data['label'], data.get('emoji', '📍'), now))
        conn.commit()
        cursor.execute("SELECT * FROM patient_distance_goals WHERE id = ?", (goal_id,))
        result = dict(cursor.fetchone())
        conn.close()
        return result

    @staticmethod
    def get_patient_distance_goals(patient_id: str) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM patient_distance_goals WHERE patient_id = ? ORDER BY distance_meters ASC",
            (patient_id,)
        )
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def delete_distance_goal(goal_id: str) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM patient_distance_goals WHERE id = ?", (goal_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    # ===== Notifications =====
    @staticmethod
    def create_notification(data: dict) -> dict:
        conn = get_db_connection()
        cursor = conn.cursor()
        noti_id = SimpleDB.generate_id()
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO notifications (id, user_id, type, title, message, data, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """, (noti_id, data['user_id'], data['type'], data['title'],
              data['message'], data.get('data'), now))
        conn.commit()
        cursor.execute("SELECT * FROM notifications WHERE id = ?", (noti_id,))
        result = dict(cursor.fetchone())
        conn.close()
        return result

    @staticmethod
    def get_notifications(user_id: str, limit: int = 20, offset: int = 0) -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM notifications WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, (user_id, limit, offset))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def get_unread_count(user_id: str) -> int:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count

    @staticmethod
    def mark_notification_read(noti_id: str) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (noti_id,))
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    @staticmethod
    def mark_all_read(user_id: str) -> int:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
            (user_id,)
        )
        conn.commit()
        count = cursor.rowcount
        conn.close()
        return count

    # ===== Admin Stats =====
    @staticmethod
    def get_all_tests_count() -> int:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM walk_tests")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    @staticmethod
    def get_tests_by_period() -> list:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT substr(test_date, 1, 7) as period, COUNT(*) as count
            FROM walk_tests GROUP BY period ORDER BY period DESC LIMIT 12
        """)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def get_all_latest_tests() -> list:
        """각 환자의 최신 2개 검사를 반환 (개선율 계산용)"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT w.* FROM walk_tests w
            INNER JOIN (
                SELECT patient_id, test_type, MAX(test_date) as max_date
                FROM walk_tests WHERE test_type IN ('10MWT', 'TUG')
                GROUP BY patient_id, test_type
            ) latest ON w.patient_id = latest.patient_id
                AND w.test_type = latest.test_type
                AND w.test_date = latest.max_date
            ORDER BY w.patient_id, w.test_type
        """)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def get_tag_stats() -> list:
        """태그별 환자 수와 평균 보행속도"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.name as tag_name, t.color,
                   COUNT(DISTINCT m.patient_id) as patient_count,
                   AVG(w.walk_speed_mps) as avg_speed
            FROM patient_tags t
            LEFT JOIN patient_tag_map m ON t.id = m.tag_id
            LEFT JOIN (
                SELECT patient_id, walk_speed_mps
                FROM walk_tests WHERE test_type = '10MWT'
                AND walk_speed_mps > 0
            ) w ON m.patient_id = w.patient_id
            GROUP BY t.id
            ORDER BY patient_count DESC
        """)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results


# 전역 DB 인스턴스
db = SimpleDB()
