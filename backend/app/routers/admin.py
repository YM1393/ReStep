import io
import csv
from fastapi import APIRouter, HTTPException, Header, Request, Query, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

from app.models.db_factory import db, get_db_connection, DB_PATH
from app.services.audit_logger import log_action, get_audit_logs, get_audit_logs_count
from app.services.cache_service import cache
from app.services import site_manager

router = APIRouter()



class TherapistResponse(BaseModel):
    id: str
    username: str
    name: str
    role: str
    is_approved: bool
    created_at: str


def verify_admin(user_id: str = Header(None, alias="X-User-Id"),
                 user_role: str = Header(None, alias="X-User-Role")):
    """관리자 권한 확인"""
    if not user_id or user_role != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    return True


@router.get("/therapists", response_model=List[TherapistResponse])
async def get_all_therapists(
    user_id: str = Header(None, alias="X-User-Id"),
    user_role: str = Header(None, alias="X-User-Role")
):
    """모든 물리치료사 목록 조회"""
    verify_admin(user_id, user_role)

    therapists = db.get_all_therapists()
    return [
        {
            **t,
            "is_approved": bool(t["is_approved"])
        }
        for t in therapists
    ]


@router.get("/therapists/pending", response_model=List[TherapistResponse])
async def get_pending_therapists(
    user_id: str = Header(None, alias="X-User-Id"),
    user_role: str = Header(None, alias="X-User-Role")
):
    """승인 대기 물리치료사 목록 조회"""
    verify_admin(user_id, user_role)

    therapists = db.get_pending_therapists()
    return [
        {
            **t,
            "is_approved": bool(t["is_approved"])
        }
        for t in therapists
    ]


@router.post("/therapists/{user_id}/approve", response_model=TherapistResponse)
async def approve_therapist(
    user_id: str,
    req: Request,
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role")
):
    """물리치료사 승인"""
    verify_admin(admin_id, admin_role)

    result = db.approve_therapist(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="물리치료사를 찾을 수 없습니다.")

    log_action(
        user_id=admin_id,
        action="approve_therapist",
        resource_type="therapist",
        resource_id=user_id,
        details={"therapist_name": result.get("name")},
        ip_address=req.client.host if req.client else None,
    )

    # 승인 알림 전송
    try:
        from app.services.notification_service import notify_therapist_approved
        notify_therapist_approved(user_id, result.get("name", ""))
    except Exception:
        pass

    return {
        **result,
        "is_approved": bool(result["is_approved"])
    }


@router.delete("/therapists/{user_id}")
async def delete_therapist(
    user_id: str,
    req: Request,
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role")
):
    """물리치료사 삭제/거부"""
    verify_admin(admin_id, admin_role)

    if not db.delete_user(user_id):
        raise HTTPException(status_code=404, detail="물리치료사를 찾을 수 없습니다.")

    log_action(
        user_id=admin_id,
        action="delete_therapist",
        resource_type="therapist",
        resource_id=user_id,
        ip_address=req.client.host if req.client else None,
    )

    return {"message": "물리치료사가 삭제되었습니다."}


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role")
):
    """병원 관리자 대시보드 통계"""
    verify_admin(admin_id, admin_role)

    cached = cache.get_dashboard_stats()
    if cached is not None:
        return cached

    conn = get_db_connection()
    cursor = conn.cursor()

    # 기본 통계
    cursor.execute("SELECT COUNT(*) FROM patients")
    total_patients = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM walk_tests")
    total_tests = cursor.fetchone()[0]

    # 주간/월간 검사 수
    now = datetime.now()
    week_ago = (now - timedelta(days=7)).isoformat()
    month_ago = (now - timedelta(days=30)).isoformat()

    cursor.execute("SELECT COUNT(*) FROM walk_tests WHERE test_date >= ?", (week_ago,))
    tests_this_week = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM walk_tests WHERE test_date >= ?", (month_ago,))
    tests_this_month = cursor.fetchone()[0]

    # 낙상 고위험군 (최신 10MWT 속도 < 0.8 m/s)
    cursor.execute("""
        SELECT COUNT(DISTINCT patient_id) FROM (
            SELECT patient_id, walk_speed_mps,
                   ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY test_date DESC) as rn
            FROM walk_tests WHERE test_type = '10MWT'
        ) WHERE rn = 1 AND walk_speed_mps < 0.8
    """)
    high_fall_risk_count = cursor.fetchone()[0]

    # 기간별 검사 추이 (최근 12개월)
    tests_by_period = db.get_tests_by_period()

    # 개선율 분포 (2회 이상 검사한 환자)
    cursor.execute("""
        SELECT patient_id,
               MAX(CASE WHEN rn = 1 THEN walk_speed_mps END) as latest_speed,
               MAX(CASE WHEN rn = 2 THEN walk_speed_mps END) as prev_speed
        FROM (
            SELECT patient_id, walk_speed_mps,
                   ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY test_date DESC) as rn
            FROM walk_tests WHERE test_type = '10MWT'
        ) WHERE rn <= 2
        GROUP BY patient_id
        HAVING prev_speed IS NOT NULL
    """)
    improved = 0
    stable = 0
    worsened = 0
    for row in cursor.fetchall():
        diff = (row[1] or 0) - (row[2] or 0)
        if diff > 0.05:
            improved += 1
        elif diff < -0.05:
            worsened += 1
        else:
            stable += 1

    # 태그별 통계
    tag_stats = db.get_tag_stats()

    conn.close()

    result = {
        "total_patients": total_patients,
        "total_tests": total_tests,
        "tests_this_week": tests_this_week,
        "tests_this_month": tests_this_month,
        "high_fall_risk_count": high_fall_risk_count,
        "tests_by_period": tests_by_period,
        "improvement_distribution": {
            "improved": improved,
            "stable": stable,
            "worsened": worsened
        },
        "tag_stats": tag_stats
    }
    cache.set_dashboard_stats(result)
    return result


@router.get("/audit-logs")
async def get_audit_logs_endpoint(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    action: Optional[str] = Query(default=None),
    user_id_filter: Optional[str] = Query(default=None, alias="user_id"),
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role")
):
    """감사 로그 조회 - 관리자 전용 (페이지네이션 지원)"""
    verify_admin(admin_id, admin_role)

    logs = get_audit_logs(
        limit=limit,
        offset=offset,
        action=action,
        user_id=user_id_filter,
    )
    total = get_audit_logs_count(action=action, user_id=user_id_filter)

    return {
        "logs": logs,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ============= Data Export Endpoints =============

@router.get("/export/patients-csv")
async def export_patients_csv(
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role")
):
    """모든 환자 데이터 CSV 내보내기 - 관리자 전용"""
    verify_admin(admin_id, admin_role)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, patient_number, name, gender, birth_date, height_cm, diagnosis, created_at
        FROM patients ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Patient Number", "Name", "Gender", "Birth Date", "Height (cm)", "Diagnosis", "Created At"])
    for row in rows:
        writer.writerow([row["id"], row["patient_number"], row["name"],
                        "M" if row["gender"] == "M" else "F",
                        row["birth_date"], row["height_cm"],
                        row["diagnosis"] or "", row["created_at"]])

    csv_content = output.getvalue()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=patients_{timestamp}.csv"}
    )


@router.get("/export/tests-csv")
async def export_tests_csv(
    test_type: Optional[str] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role")
):
    """검사 데이터 CSV 내보내기 - 관리자 전용

    Filters:
        test_type: 10MWT, TUG, BBS (optional)
        date_from: ISO date string (optional)
        date_to: ISO date string (optional)
    """
    verify_admin(admin_id, admin_role)

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT w.id, w.patient_id, p.patient_number, p.name as patient_name,
               w.test_date, w.test_type, w.walk_time_seconds, w.walk_speed_mps,
               w.notes, w.created_at
        FROM walk_tests w
        LEFT JOIN patients p ON w.patient_id = p.id
        WHERE 1=1
    """
    params = []

    if test_type:
        query += " AND w.test_type = ?"
        params.append(test_type)
    if date_from:
        query += " AND w.test_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND w.test_date <= ?"
        params.append(date_to)

    query += " ORDER BY w.test_date DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Test ID", "Patient ID", "Patient Number", "Patient Name",
                     "Test Date", "Test Type", "Time (s)", "Speed (m/s)",
                     "Notes", "Created At"])
    for row in rows:
        writer.writerow([
            row["id"], row["patient_id"], row["patient_number"] or "",
            row["patient_name"] or "", row["test_date"], row["test_type"] or "10MWT",
            round(row["walk_time_seconds"], 2), round(row["walk_speed_mps"], 2),
            row["notes"] or "", row["created_at"]
        ])

    csv_content = output.getvalue()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    type_suffix = f"_{test_type}" if test_type else ""

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tests{type_suffix}_{timestamp}.csv"}
    )


@router.get("/export/backup")
async def export_database_backup(
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role")
):
    """SQLite 데이터베이스 백업 파일 다운로드 - 관리자 전용"""
    import os
    verify_admin(admin_id, admin_role)

    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="데이터베이스 파일을 찾을 수 없습니다.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    return FileResponse(
        DB_PATH,
        media_type="application/octet-stream",
        filename=f"database_backup_{timestamp}.db"
    )


@router.post("/import/backup")
async def import_database_backup(
    file: UploadFile = File(...),
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role")
):
    """SQLite 데이터베이스 백업 파일에서 복원 - 관리자 전용

    업로드된 .db 파일로 현재 데이터베이스를 교체합니다.
    기존 DB는 .bak 파일로 백업됩니다.
    """
    import os
    import shutil
    import sqlite3

    verify_admin(admin_id, admin_role)

    if not file.filename or not file.filename.endswith('.db'):
        raise HTTPException(status_code=400, detail="SQLite .db 파일만 업로드 가능합니다.")

    # 업로드된 파일을 임시 경로에 저장
    temp_path = DB_PATH + ".upload_tmp"
    try:
        content = await file.read()
        with open(temp_path, 'wb') as f:
            f.write(content)

        # 유효한 SQLite 파일인지 검증
        try:
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()

            required_tables = {'patients', 'walk_tests', 'users'}
            if not required_tables.issubset(set(tables)):
                missing = required_tables - set(tables)
                raise HTTPException(
                    status_code=400,
                    detail=f"유효하지 않은 백업 파일입니다. 필수 테이블 누락: {', '.join(missing)}"
                )
        except sqlite3.DatabaseError:
            raise HTTPException(status_code=400, detail="유효한 SQLite 데이터베이스 파일이 아닙니다.")

        # 기존 DB 백업
        backup_path = DB_PATH + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, backup_path)

        # 새 DB로 교체
        shutil.move(temp_path, DB_PATH)

        return {
            "message": "데이터베이스가 성공적으로 복원되었습니다.",
            "backup_created": os.path.basename(backup_path),
            "tables_found": tables
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"복원 중 오류 발생: {str(e)}")
    finally:
        # 임시 파일 정리
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


# ============= Multi-Site Management Endpoints =============


class SiteCreate(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None


class SiteUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None


@router.get("/sites")
async def list_sites(
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role"),
):
    """List all sites - admin only."""
    verify_admin(admin_id, admin_role)
    return site_manager.get_sites()


@router.post("/sites")
async def create_site(
    body: SiteCreate,
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role"),
):
    """Create a new site - admin only."""
    verify_admin(admin_id, admin_role)
    site = site_manager.create_site(
        name=body.name,
        address=body.address,
        phone=body.phone,
        admin_user_id=admin_id,
    )
    return site


@router.put("/sites/{site_id}")
async def update_site(
    site_id: str,
    body: SiteUpdate,
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role"),
):
    """Update a site - admin only."""
    verify_admin(admin_id, admin_role)
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = site_manager.update_site(site_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Site not found")
    return result


@router.get("/sites/{site_id}/stats")
async def get_site_stats(
    site_id: str,
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role"),
):
    """Get site-specific statistics - admin only."""
    verify_admin(admin_id, admin_role)
    site = site_manager.get_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    stats = site_manager.get_site_stats(site_id)
    stats["site_name"] = site["name"]
    return stats


# ============= Report Templates Endpoints =============


class ReportTemplateCreate(BaseModel):
    name: str
    config: dict


class ReportTemplateUpdate(BaseModel):
    config: dict


@router.get("/report-templates")
async def list_report_templates(
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role"),
):
    """List all report templates (built-in + custom) - admin only."""
    verify_admin(admin_id, admin_role)
    from app.services.report_templates import list_templates
    return list_templates()


@router.post("/report-templates")
async def create_report_template(
    body: ReportTemplateCreate,
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role"),
):
    """Create a custom report template - admin only."""
    verify_admin(admin_id, admin_role)
    from app.services.report_templates import create_template
    try:
        result = create_template(body.name, body.config, created_by=admin_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise HTTPException(status_code=409, detail=f"Template name '{body.name}' already exists.")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/report-templates/{template_id}")
async def update_report_template(
    template_id: str,
    body: ReportTemplateUpdate,
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role"),
):
    """Update a custom report template - admin only."""
    verify_admin(admin_id, admin_role)
    from app.services.report_templates import update_template
    result = update_template(template_id, body.config)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found.")
    return result


@router.delete("/report-templates/{template_id}")
async def delete_report_template(
    template_id: str,
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role"),
):
    """Delete a custom report template - admin only."""
    verify_admin(admin_id, admin_role)
    from app.services.report_templates import delete_template
    if not delete_template(template_id):
        raise HTTPException(status_code=404, detail="Template not found.")
    return {"message": "Template deleted."}


# ============= Email Configuration Status =============


@router.get("/email/status")
async def get_email_status(
    admin_id: str = Header(None, alias="X-User-Id"),
    admin_role: str = Header(None, alias="X-User-Role"),
):
    """Check if email sending is configured - admin only."""
    verify_admin(admin_id, admin_role)
    from app.services.email_service import email_service
    return {
        "configured": email_service.is_configured,
        "smtp_host": email_service.host if email_service.is_configured else None,
    }
