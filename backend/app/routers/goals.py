from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.models.db_factory import db

router = APIRouter()


class GoalCreate(BaseModel):
    test_type: str = '10MWT'
    target_speed_mps: Optional[float] = None
    target_time_seconds: Optional[float] = None
    target_score: Optional[int] = None
    target_date: Optional[str] = None


class GoalUpdate(BaseModel):
    target_speed_mps: Optional[float] = None
    target_time_seconds: Optional[float] = None
    target_score: Optional[int] = None
    target_date: Optional[str] = None
    status: Optional[str] = None


@router.post("/{patient_id}")
async def create_goal(patient_id: str, goal: GoalCreate):
    """환자 목표 생성"""
    data = goal.model_dump(exclude_none=True)
    data['patient_id'] = patient_id
    return db.create_goal(data)


@router.get("/{patient_id}")
async def get_goals(patient_id: str, status: Optional[str] = Query(None)):
    """환자 목표 조회"""
    return db.get_patient_goals(patient_id, status)


@router.put("/{goal_id}/update")
async def update_goal(goal_id: str, goal: GoalUpdate):
    """목표 수정"""
    data = goal.model_dump(exclude_none=True)
    if data.get('status') == 'achieved':
        data['achieved_at'] = datetime.now().isoformat()
    result = db.update_goal(goal_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="목표를 찾을 수 없습니다.")
    return result


@router.delete("/{goal_id}/delete")
async def delete_goal(goal_id: str):
    """목표 삭제"""
    if not db.delete_goal(goal_id):
        raise HTTPException(status_code=404, detail="목표를 찾을 수 없습니다.")
    return {"message": "목표가 삭제되었습니다."}


@router.get("/{patient_id}/progress")
async def get_goal_progress(
    patient_id: str,
    x_user_id: Optional[str] = Header(None),
):
    """활성 목표의 달성률 계산"""
    goals = db.get_patient_goals(patient_id, status='active')
    if not goals:
        return []

    results = []
    for goal in goals:
        test_type = goal['test_type']
        tests = db.get_patient_tests(patient_id, test_type)

        if not tests:
            results.append({
                "goal": goal,
                "current_value": None,
                "achievement_pct": 0,
                "days_remaining": _days_remaining(goal.get('target_date'))
            })
            continue

        latest = tests[0]
        current_value = None
        achievement_pct = 0

        if test_type == '10MWT' and goal.get('target_time_seconds'):
            current_value = latest['walk_time_seconds']
            target = goal['target_time_seconds']
            # 10MWT: 시간이 짧을수록 좋음
            achievement_pct = min(100, round((target / current_value) * 100, 1)) if current_value > 0 else 0
        elif test_type == '10MWT' and goal.get('target_speed_mps'):
            # 하위 호환: 속도 목표를 시간 기준으로 변환 (10m / speed = seconds)
            current_value = latest['walk_time_seconds']
            target_time = round(10.0 / goal['target_speed_mps'], 1) if goal['target_speed_mps'] > 0 else 0
            achievement_pct = min(100, round((target_time / current_value) * 100, 1)) if current_value > 0 else 0
            # 목표를 시간 기준으로 변환하여 반환
            goal['target_time_seconds'] = target_time
            goal['target_speed_mps'] = None
        elif test_type == 'TUG' and goal.get('target_time_seconds'):
            current_value = latest['walk_time_seconds']
            target = goal['target_time_seconds']
            # TUG는 시간이 짧을수록 좋음
            achievement_pct = min(100, round((target / current_value) * 100, 1)) if current_value > 0 else 0
        elif test_type == 'BBS' and goal.get('target_score'):
            current_value = latest['walk_time_seconds']  # BBS total_score stored here
            target = goal['target_score']
            achievement_pct = min(100, round((current_value / target) * 100, 1)) if target > 0 else 0

        # 목표 달성 시 자동 업데이트
        if achievement_pct >= 100 and goal['status'] == 'active':
            db.update_goal(goal['id'], {
                'status': 'achieved',
                'achieved_at': datetime.now().isoformat()
            })
            goal['status'] = 'achieved'

            # 목표 달성 알림 전송
            if x_user_id:
                try:
                    from app.services.notification_service import notify_goal_achieved
                    patient = db.get_patient(patient_id)
                    patient_name = patient.get('name', '') if patient else ''
                    notify_goal_achieved(x_user_id, patient_name, test_type, patient_id)
                except Exception:
                    pass

        results.append({
            "goal": goal,
            "current_value": current_value,
            "achievement_pct": achievement_pct,
            "days_remaining": _days_remaining(goal.get('target_date'))
        })

    return results


def _days_remaining(target_date: Optional[str]) -> Optional[int]:
    if not target_date:
        return None
    try:
        target = datetime.fromisoformat(target_date)
        delta = (target - datetime.now()).days
        return max(0, delta)
    except (ValueError, TypeError):
        return None
