"""Audit logging service for tracking user actions."""

import json
from datetime import datetime
from typing import Optional
from app.models.database import get_db_connection, SimpleDB


def log_action(
    user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
):
    """Record an audit log entry.

    Args:
        user_id: ID of the user performing the action (None for anonymous).
        action: Action name (e.g. "login", "create_patient", "delete_test").
        resource_type: Type of resource (e.g. "auth", "patient", "test", "therapist").
        resource_id: Optional ID of the affected resource.
        details: Optional dict with extra context.
        ip_address: Client IP address.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        log_id = SimpleDB.generate_id()
        now = datetime.now().isoformat()
        details_json = json.dumps(details, ensure_ascii=False) if details else None

        cursor.execute(
            """INSERT INTO audit_logs
               (id, user_id, action, resource_type, resource_id, details, ip_address, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (log_id, user_id, action, resource_type, resource_id, details_json, ip_address, now),
        )
        conn.commit()
    except Exception as e:
        print(f"[AUDIT] Failed to log action: {e}")
    finally:
        conn.close()


def get_audit_logs(
    limit: int = 50,
    offset: int = 0,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
) -> list:
    """Retrieve audit logs with optional filtering and pagination."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []

    if action:
        query += " AND action = ?"
        params.append(action)
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    results = []
    for row in rows:
        entry = dict(row)
        if entry.get("details") and isinstance(entry["details"], str):
            try:
                entry["details"] = json.loads(entry["details"])
            except (json.JSONDecodeError, TypeError):
                pass
        results.append(entry)

    conn.close()
    return results


def get_audit_logs_count(
    action: Optional[str] = None,
    user_id: Optional[str] = None,
) -> int:
    """Return total count for pagination."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT COUNT(*) FROM audit_logs WHERE 1=1"
    params = []

    if action:
        query += " AND action = ?"
        params.append(action)
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)

    cursor.execute(query, params)
    count = cursor.fetchone()[0]
    conn.close()
    return count
