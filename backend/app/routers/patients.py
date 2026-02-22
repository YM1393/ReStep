from fastapi import APIRouter, HTTPException, Query, Header, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import date

from app.models.database import db
from app.services.audit_logger import log_action
from app.services.cache_service import cache

router = APIRouter()


class PatientCreate(BaseModel):
    patient_number: str
    name: str
    gender: str  # 'M' or 'F'
    birth_date: date
    height_cm: float
    diagnosis: Optional[str] = None


class PatientResponse(BaseModel):
    id: str
    patient_number: str
    name: str
    gender: str
    birth_date: str
    height_cm: float
    diagnosis: Optional[str]
    created_at: str


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    height_cm: Optional[float] = None
    diagnosis: Optional[str] = None


def verify_approved_therapist(
    user_id: str = Header(None, alias="X-User-Id"),
    user_role: str = Header(None, alias="X-User-Role"),
    is_approved: str = Header(None, alias="X-User-Approved")
):
    """승인된 물리치료사 권한 확인"""
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    if user_role == "admin":
        raise HTTPException(status_code=403, detail="관리자는 환자를 등록/수정/삭제할 수 없습니다. 물리치료사만 가능합니다.")

    if user_role != "therapist":
        raise HTTPException(status_code=403, detail="물리치료사 권한이 필요합니다.")

    if is_approved != "true":
        raise HTTPException(status_code=403, detail="관리자 승인 후 이용 가능합니다.")

    return True


@router.post("/", response_model=PatientResponse)
async def create_patient(
    patient: PatientCreate,
    req: Request,
    user_id: str = Header(None, alias="X-User-Id"),
    user_role: str = Header(None, alias="X-User-Role"),
    is_approved: str = Header(None, alias="X-User-Approved")
):
    """새 환자 등록 - 승인된 물리치료사만"""
    verify_approved_therapist(user_id, user_role, is_approved)

    # 환자번호 중복 체크
    existing = db.search_patients(patient.patient_number)
    for p in existing:
        if p['patient_number'] == patient.patient_number:
            raise HTTPException(status_code=400, detail="이미 존재하는 환자번호입니다.")

    data = {
        "patient_number": patient.patient_number,
        "name": patient.name,
        "gender": patient.gender,
        "birth_date": patient.birth_date.isoformat(),
        "height_cm": patient.height_cm,
        "diagnosis": patient.diagnosis
    }

    result = db.create_patient(data)
    cache.invalidate_patients()
    cache.invalidate_dashboard()

    log_action(
        user_id=user_id,
        action="create_patient",
        resource_type="patient",
        resource_id=result["id"],
        details={"patient_number": patient.patient_number, "name": patient.name},
        ip_address=req.client.host if req.client else None,
    )

    return result


@router.get("/", response_model=List[PatientResponse])
async def get_patients(limit: int = Query(default=50, le=100)):
    """환자 목록 조회 - 모든 로그인 사용자"""
    cached = cache.get_patient_list(limit)
    if cached is not None:
        return cached
    result = db.get_patients(limit)
    cache.set_patient_list(limit, result)
    return result


@router.get("/with-latest-test")
async def get_patients_with_latest_test(limit: int = Query(default=50, le=100)):
    """환자 목록 + 최신 검사 정보 (단일 쿼리)"""
    return db.get_patients_with_latest_test(limit)


@router.get("/search", response_model=List[PatientResponse])
async def search_patients(q: str = Query(..., min_length=1)):
    """환자 검색 (이름 또는 환자번호) - 모든 로그인 사용자"""
    return db.search_patients(q)


# ===== 환자 태그 관리 (must be before /{patient_id} routes) =====

class TagCreate(BaseModel):
    name: str
    color: Optional[str] = '#6B7280'


@router.get("/tags/all")
async def get_all_tags():
    """전체 태그 목록"""
    return db.get_all_tags()


@router.post("/tags")
async def create_tag(tag: TagCreate):
    """새 태그 생성"""
    try:
        return db.create_tag(tag.name, tag.color or '#6B7280')
    except Exception:
        raise HTTPException(status_code=400, detail="이미 존재하는 태그입니다.")


@router.delete("/tags/{tag_id}")
async def delete_tag(tag_id: str):
    """태그 삭제"""
    if not db.delete_tag(tag_id):
        raise HTTPException(status_code=404, detail="태그를 찾을 수 없습니다.")
    return {"message": "태그가 삭제되었습니다."}


@router.get("/by-tag/{tag_id}")
async def get_patients_by_tag(tag_id: str):
    """태그별 환자 필터"""
    return db.get_patients_by_tag(tag_id)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str):
    """환자 상세 조회 - 모든 로그인 사용자"""
    result = db.get_patient(patient_id)
    if not result:
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")
    return result


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    patient: PatientUpdate,
    req: Request,
    user_id: str = Header(None, alias="X-User-Id"),
    user_role: str = Header(None, alias="X-User-Role"),
    is_approved: str = Header(None, alias="X-User-Approved")
):
    """환자 정보 수정 - 승인된 물리치료사만"""
    verify_approved_therapist(user_id, user_role, is_approved)

    update_data = {k: v.isoformat() if isinstance(v, date) else v
                   for k, v in patient.model_dump(exclude_none=True).items()}

    if not update_data:
        raise HTTPException(status_code=400, detail="수정할 데이터가 없습니다.")

    result = db.update_patient(patient_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")

    cache.invalidate_patients()

    log_action(
        user_id=user_id,
        action="update_patient",
        resource_type="patient",
        resource_id=patient_id,
        details={"fields_updated": list(update_data.keys())},
        ip_address=req.client.host if req.client else None,
    )

    return result


@router.delete("/{patient_id}")
async def delete_patient(
    patient_id: str,
    req: Request,
    user_id: str = Header(None, alias="X-User-Id"),
    user_role: str = Header(None, alias="X-User-Role"),
    is_approved: str = Header(None, alias="X-User-Approved")
):
    """환자 삭제 - 승인된 물리치료사만"""
    verify_approved_therapist(user_id, user_role, is_approved)

    if not db.delete_patient(patient_id):
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")

    cache.invalidate_patients()
    cache.invalidate_dashboard()
    cache.invalidate_tests(patient_id)

    log_action(
        user_id=user_id,
        action="delete_patient",
        resource_type="patient",
        resource_id=patient_id,
        ip_address=req.client.host if req.client else None,
    )

    return {"message": "환자가 삭제되었습니다."}


@router.get("/{patient_id}/tags")
async def get_patient_tags(patient_id: str):
    """환자 태그 조회"""
    return db.get_patient_tags(patient_id)


@router.post("/{patient_id}/tags/{tag_id}")
async def add_patient_tag(patient_id: str, tag_id: str):
    """환자에 태그 할당"""
    if not db.add_patient_tag(patient_id, tag_id):
        raise HTTPException(status_code=400, detail="이미 할당된 태그이거나 잘못된 요청입니다.")
    return {"message": "태그가 할당되었습니다."}


@router.delete("/{patient_id}/tags/{tag_id}")
async def remove_patient_tag(patient_id: str, tag_id: str):
    """환자에서 태그 제거"""
    if not db.remove_patient_tag(patient_id, tag_id):
        raise HTTPException(status_code=404, detail="태그를 찾을 수 없습니다.")
    return {"message": "태그가 제거되었습니다."}
