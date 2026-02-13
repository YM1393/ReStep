"""맞춤형 거리 목표 API 라우터"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.models.database import db

router = APIRouter()


class DistanceGoalCreate(BaseModel):
    distance_meters: float
    label: str
    emoji: Optional[str] = "📍"


@router.post("/{patient_id}")
async def create_distance_goal(patient_id: str, goal: DistanceGoalCreate):
    """환자 맞춤형 거리 목표 생성"""
    data = goal.model_dump()
    data['patient_id'] = patient_id
    return db.create_distance_goal(data)


@router.get("/{patient_id}")
async def get_distance_goals(patient_id: str):
    """환자의 거리 목표 조회"""
    return db.get_patient_distance_goals(patient_id)


@router.delete("/{goal_id}/delete")
async def delete_distance_goal(goal_id: str):
    """거리 목표 삭제"""
    if not db.delete_distance_goal(goal_id):
        raise HTTPException(status_code=404, detail="목표를 찾을 수 없습니다.")
    return {"message": "삭제되었습니다."}
