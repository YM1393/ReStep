"""대시보드 API 라우터 - 위젯 데이터"""
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Header, HTTPException, Query
from typing import Optional

from app.models.database import db, get_db_connection

router = APIRouter()


@router.get("/recent-tests")
async def get_recent_tests(
    limit: int = Query(default=5, ge=1, le=20),
    x_user_id: Optional[str] = Header(None),
):
    """최근 검사 목록 (환자명 포함)"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT w.id, w.patient_id, w.test_date, w.test_type, w.walk_time_seconds,
               w.walk_speed_mps, p.name as patient_name, p.patient_number
        FROM walk_tests w
        JOIN patients p ON w.patient_id = p.id
        ORDER BY w.test_date DESC
        LIMIT ?
    """, (limit,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


@router.get("/weekly-activity")
async def get_weekly_activity(
    x_user_id: Optional[str] = Header(None),
):
    """이번 주 일별 검사 수"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())  # Monday

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT substr(test_date, 1, 10) as day, COUNT(*) as count
        FROM walk_tests
        WHERE test_date >= ?
        GROUP BY day
        ORDER BY day
    """, (week_start.isoformat(),))
    rows = {row['day']: row['count'] for row in cursor.fetchall()}
    conn.close()

    # Fill in all 7 days
    days_kr = ['월', '화', '수', '목', '금', '토', '일']
    result = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        day_str = d.isoformat()
        result.append({
            'day': days_kr[i],
            'date': day_str,
            'count': rows.get(day_str, 0),
        })

    return result


@router.get("/speed-distribution")
async def get_speed_distribution(
    x_user_id: Optional[str] = Header(None),
):
    """보행 속도 분포 (정상/주의/위험)"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get latest 10MWT test for each patient
    cursor.execute("""
        SELECT w.walk_speed_mps FROM walk_tests w
        INNER JOIN (
            SELECT patient_id, MAX(test_date) as max_date
            FROM walk_tests WHERE test_type = '10MWT' AND walk_speed_mps > 0
            GROUP BY patient_id
        ) latest ON w.patient_id = latest.patient_id AND w.test_date = latest.max_date
        WHERE w.test_type = '10MWT' AND w.walk_speed_mps > 0
    """)
    speeds = [row['walk_speed_mps'] for row in cursor.fetchall()]
    conn.close()

    normal = sum(1 for s in speeds if s >= 1.2)
    caution = sum(1 for s in speeds if 0.8 <= s < 1.2)
    risk = sum(1 for s in speeds if s < 0.8)

    return [
        {'name': '정상', 'value': normal, 'color': '#22c55e'},
        {'name': '주의', 'value': caution, 'color': '#f97316'},
        {'name': '위험', 'value': risk, 'color': '#ef4444'},
    ]
