"""Multi-site / multi-tenant management service.

Sites are optional.  When a user has no site_id, they see all data
(backward-compatible with the single-site default).
"""

from datetime import datetime
from typing import Optional

from app.models.database import get_db_connection, SimpleDB


def get_sites() -> list:
    """Return all sites ordered by name."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sites ORDER BY name")
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_site(site_id: str) -> Optional[dict]:
    """Return a single site by id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sites WHERE id = ?", (site_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_site(name: str, address: Optional[str] = None, phone: Optional[str] = None, admin_user_id: Optional[str] = None) -> dict:
    """Create a new site and return it."""
    conn = get_db_connection()
    cursor = conn.cursor()
    site_id = SimpleDB.generate_id()
    now = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO sites (id, name, address, phone, admin_user_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (site_id, name, address, phone, admin_user_id, now),
    )
    conn.commit()
    cursor.execute("SELECT * FROM sites WHERE id = ?", (site_id,))
    result = dict(cursor.fetchone())
    conn.close()
    return result


def update_site(site_id: str, data: dict) -> Optional[dict]:
    """Update site fields.  Returns updated site or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
    values = list(data.values()) + [site_id]
    cursor.execute(f"UPDATE sites SET {set_clause} WHERE id = ?", values)
    conn.commit()
    if cursor.rowcount == 0:
        conn.close()
        return None
    cursor.execute("SELECT * FROM sites WHERE id = ?", (site_id,))
    result = dict(cursor.fetchone())
    conn.close()
    return result


def delete_site(site_id: str) -> bool:
    """Delete a site.  Returns True if deleted."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sites WHERE id = ?", (site_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def get_user_site(user_id: str) -> Optional[dict]:
    """Return the site assigned to a user, or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT site_id FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    if not row or not row["site_id"]:
        conn.close()
        return None
    cursor.execute("SELECT * FROM sites WHERE id = ?", (row["site_id"],))
    site_row = cursor.fetchone()
    conn.close()
    return dict(site_row) if site_row else None


def assign_user_to_site(user_id: str, site_id: Optional[str]) -> bool:
    """Assign a user to a site (or clear with None)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET site_id = ? WHERE id = ?", (site_id, user_id))
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def get_site_stats(site_id: str) -> dict:
    """Return statistics for a specific site."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM patients WHERE site_id = ?", (site_id,))
    total_patients = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM walk_tests WHERE site_id = ?", (site_id,)
    )
    total_tests = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM users WHERE site_id = ? AND role = 'therapist'",
        (site_id,),
    )
    total_therapists = cursor.fetchone()[0]

    cursor.execute(
        """SELECT AVG(walk_speed_mps) FROM walk_tests
           WHERE site_id = ? AND test_type = '10MWT' AND walk_speed_mps > 0""",
        (site_id,),
    )
    row = cursor.fetchone()
    avg_speed = row[0] if row and row[0] else None

    conn.close()

    return {
        "site_id": site_id,
        "total_patients": total_patients,
        "total_tests": total_tests,
        "total_therapists": total_therapists,
        "avg_walk_speed_mps": round(avg_speed, 3) if avg_speed else None,
    }


def get_patients_for_site(site_id: Optional[str], limit: int = 50) -> list:
    """Return patients filtered by site_id.  If site_id is None, return all."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if site_id:
        cursor.execute(
            "SELECT * FROM patients WHERE site_id = ? ORDER BY created_at DESC LIMIT ?",
            (site_id, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM patients ORDER BY created_at DESC LIMIT ?", (limit,)
        )
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_tests_for_site(site_id: Optional[str], limit: int = 100) -> list:
    """Return walk tests filtered by site_id.  If site_id is None, return all."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if site_id:
        cursor.execute(
            "SELECT * FROM walk_tests WHERE site_id = ? ORDER BY test_date DESC LIMIT ?",
            (site_id, limit),
        )
    else:
        cursor.execute(
            "SELECT * FROM walk_tests ORDER BY test_date DESC LIMIT ?", (limit,)
        )
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results
