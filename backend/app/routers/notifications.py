"""알림 API 라우터"""
from fastapi import APIRouter, Header, HTTPException
from typing import Optional

from app.models.database import db

router = APIRouter()


@router.get("")
async def get_notifications(
    limit: int = 20,
    offset: int = 0,
    x_user_id: Optional[str] = Header(None),
):
    """사용자 알림 목록 조회"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    notifications = db.get_notifications(x_user_id, limit=limit, offset=offset)
    # Parse JSON data field
    import json
    for n in notifications:
        if n.get('data') and isinstance(n['data'], str):
            try:
                n['data'] = json.loads(n['data'])
            except (json.JSONDecodeError, TypeError):
                pass
    return notifications


@router.get("/unread-count")
async def get_unread_count(
    x_user_id: Optional[str] = Header(None),
):
    """읽지 않은 알림 수 조회"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    count = db.get_unread_count(x_user_id)
    return {"count": count}


@router.put("/read-all")
async def mark_all_read(
    x_user_id: Optional[str] = Header(None),
):
    """모든 알림 읽음 처리"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    count = db.mark_all_read(x_user_id)
    return {"success": True, "count": count}


@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    x_user_id: Optional[str] = Header(None),
):
    """알림 읽음 처리"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
    success = db.mark_notification_read(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")
    return {"success": True}
