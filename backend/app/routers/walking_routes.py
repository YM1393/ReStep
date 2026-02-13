"""보행 경로 API 라우터"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.models.database import db

router = APIRouter()


class WalkingRouteCreate(BaseModel):
    origin_address: str
    origin_lat: float
    origin_lng: float
    dest_address: str
    dest_lat: float
    dest_lng: float
    distance_meters: Optional[float] = None


@router.post("/{patient_id}")
async def create_walking_route(patient_id: str, route: WalkingRouteCreate):
    """보행 경로 저장"""
    data = route.model_dump()
    data['patient_id'] = patient_id
    return db.create_walking_route(data)


@router.get("/{patient_id}")
async def get_walking_routes(patient_id: str):
    """환자의 보행 경로 조회"""
    return db.get_patient_walking_routes(patient_id)


@router.delete("/{route_id}/delete")
async def delete_walking_route(route_id: str):
    """보행 경로 삭제"""
    if not db.delete_walking_route(route_id):
        raise HTTPException(status_code=404, detail="경로를 찾을 수 없습니다.")
    return {"message": "삭제되었습니다."}
