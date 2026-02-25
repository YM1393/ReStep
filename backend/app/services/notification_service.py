"""알림 서비스 - 알림 생성 및 WebSocket 전송"""
import json
import asyncio
from typing import Optional

from app.models.db_factory import db
from app.routers.websocket import get_manager


def create_notification(
    user_id: str,
    noti_type: str,
    title: str,
    message: str,
    data: Optional[dict] = None
) -> dict:
    """알림 생성 및 WebSocket으로 실시간 전송"""
    noti = db.create_notification({
        'user_id': user_id,
        'type': noti_type,
        'title': title,
        'message': message,
        'data': json.dumps(data, ensure_ascii=False) if data else None,
    })

    # WebSocket으로 실시간 알림 전송 (fire-and-forget)
    try:
        ws_manager = get_manager()
        ws_data = {
            'type': 'notification',
            'notification': {
                'id': noti['id'],
                'type': noti_type,
                'title': title,
                'message': message,
                'data': data,
                'created_at': noti['created_at'],
            }
        }
        # Try to broadcast (will reach all connected clients)
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(ws_manager.broadcast(json.dumps(ws_data, ensure_ascii=False)))
    except Exception:
        pass  # WebSocket failure should not block notification creation

    return noti


def notify_analysis_complete(user_id: str, patient_name: str, test_type: str, test_id: str, patient_id: str):
    """분석 완료 알림"""
    type_label = {'10MWT': '10m 보행검사', 'TUG': 'TUG 검사', 'BBS': 'BBS 검사'}.get(test_type, test_type)
    create_notification(
        user_id=user_id,
        noti_type='analysis_complete',
        title='분석 완료',
        message=f'{patient_name} 환자의 {type_label} 분석이 완료되었습니다.',
        data={'test_id': test_id, 'patient_id': patient_id, 'test_type': test_type},
    )


def notify_goal_achieved(user_id: str, patient_name: str, goal_type: str, patient_id: str):
    """목표 달성 알림"""
    type_label = {'10MWT': '10m 보행검사', 'TUG': 'TUG 검사', 'BBS': 'BBS 검사'}.get(goal_type, goal_type)
    create_notification(
        user_id=user_id,
        noti_type='goal_achieved',
        title='목표 달성',
        message=f'{patient_name} 환자가 {type_label} 목표를 달성했습니다!',
        data={'patient_id': patient_id, 'test_type': goal_type},
    )


def notify_therapist_approved(user_id: str, therapist_name: str):
    """치료사 승인 알림"""
    create_notification(
        user_id=user_id,
        noti_type='therapist_approved',
        title='계정 승인',
        message=f'{therapist_name}님의 계정이 승인되었습니다. 서비스를 이용하실 수 있습니다.',
        data={},
    )
