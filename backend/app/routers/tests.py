import os
import uuid
import json
import asyncio
import aiofiles
import base64
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Header, Request, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from dotenv import load_dotenv

from app.models.database import db
from app.routers.websocket import get_manager as get_ws_manager
from app.services.audit_logger import log_action
from app.services.cache_service import cache
# GaitAnalyzer를 함수 내에서 import하여 항상 최신 코드 사용
# from analysis.gait_analyzer import GaitAnalyzer

load_dotenv()

# 분석 작업을 위한 스레드 풀
analysis_executor = ThreadPoolExecutor(max_workers=2)

router = APIRouter()
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

# 분석 상태를 파일로 저장 (hot reload 문제 해결)
# 절대 경로 사용 (ThreadPoolExecutor에서 실행될 때도 동작하도록)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATUS_DIR = os.path.join(_BACKEND_DIR, "uploads", "status")
os.makedirs(STATUS_DIR, exist_ok=True)
print(f"[INIT] STATUS_DIR: {STATUS_DIR}")

def save_analysis_status(file_id: str, status_data: dict):
    """분석 상태를 파일에 저장"""
    try:
        status_path = os.path.join(STATUS_DIR, f"{file_id}.json")
        with open(status_path, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False)
        # 디버그 로그 파일에 기록
        log_path = os.path.join(STATUS_DIR, "debug.log")
        with open(log_path, 'a', encoding='utf-8') as log:
            has_frame = status_data.get("current_frame") is not None
            frame_len = len(status_data.get("current_frame") or "")
            log.write(f"[SAVE] file_id={file_id}, has_frame={has_frame}, frame_len={frame_len}\n")
    except Exception as e:
        # 에러도 로그 파일에 기록
        try:
            log_path = os.path.join(STATUS_DIR, "debug.log")
            with open(log_path, 'a', encoding='utf-8') as log:
                log.write(f"[ERROR] save_analysis_status failed: {e}\n")
        except:
            pass

    # WebSocket notification (fire-and-forget from any thread)
    _send_ws_notification(file_id, status_data)


# Store reference to main event loop for cross-thread WS notifications
_main_event_loop: Optional[asyncio.AbstractEventLoop] = None


def _set_main_loop():
    """Capture the main event loop reference. Called from async context."""
    global _main_event_loop
    try:
        _main_event_loop = asyncio.get_running_loop()
    except RuntimeError:
        pass


def _send_ws_notification(file_id: str, status_data: dict):
    """Send WebSocket notification for analysis status update.
    Safe to call from sync threads - schedules on the main event loop."""
    try:
        ws_manager = get_ws_manager()
        ws_status = status_data.get("status", "processing")
        if ws_status == "completed":
            msg_type = "completed"
        elif ws_status == "error":
            msg_type = "error"
        else:
            msg_type = "progress"

        msg = {
            "type": msg_type,
            "file_id": file_id,
            "progress": status_data.get("progress", 0),
            "message": status_data.get("message", ""),
        }
        if msg_type == "completed" and "result" in status_data:
            msg["result"] = status_data["result"]

        coro = ws_manager.notify_file_subscribers(file_id, msg)

        # Try running loop first (if called from async context)
        try:
            loop = asyncio.get_running_loop()
            asyncio.ensure_future(coro, loop=loop)
            return
        except RuntimeError:
            pass

        # Fall back to stored main loop (when called from thread pool)
        if _main_event_loop and _main_event_loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, _main_event_loop)
    except Exception:
        pass  # WS notification is best-effort, never break analysis

def load_analysis_status(file_id: str) -> Optional[dict]:
    """분석 상태를 파일에서 로드"""
    status_path = os.path.join(STATUS_DIR, f"{file_id}.json")
    if os.path.exists(status_path):
        with open(status_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def delete_analysis_status(file_id: str):
    """분석 상태 파일 삭제"""
    status_path = os.path.join(STATUS_DIR, f"{file_id}.json")
    if os.path.exists(status_path):
        os.remove(status_path)


def verify_approved_therapist(
    user_id: str = Header(None, alias="X-User-Id"),
    user_role: str = Header(None, alias="X-User-Role"),
    is_approved: str = Header(None, alias="X-User-Approved")
):
    """승인된 물리치료사 권한 확인"""
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    if user_role == "admin":
        raise HTTPException(status_code=403, detail="관리자는 검사를 수행할 수 없습니다. 물리치료사만 가능합니다.")

    if user_role != "therapist":
        raise HTTPException(status_code=403, detail="물리치료사 권한이 필요합니다.")

    if is_approved != "true":
        raise HTTPException(status_code=403, detail="관리자 승인 후 이용 가능합니다.")

    return True


class WalkTestResponse(BaseModel):
    id: str
    patient_id: str
    test_date: str
    test_type: str = "10MWT"
    walk_time_seconds: float
    walk_speed_mps: float
    video_url: Optional[str]
    analysis_data: Optional[dict]
    notes: Optional[str] = None
    created_at: str


class ComparisonResponse(BaseModel):
    current_test: WalkTestResponse
    previous_test: Optional[WalkTestResponse]
    comparison_message: str
    speed_difference: Optional[float]
    time_difference: Optional[float]


def parse_analysis_data(test: dict) -> dict:
    """분석 데이터를 파싱하여 반환"""
    result = dict(test)
    if result.get('analysis_data') and isinstance(result['analysis_data'], str):
        try:
            result['analysis_data'] = json.loads(result['analysis_data'])
        except:
            result['analysis_data'] = None
    # test_type이 없는 기존 데이터에 기본값 설정
    if 'test_type' not in result or result['test_type'] is None:
        result['test_type'] = '10MWT'
    return result


# ArUco 마커 PDF 다운로드
@router.get("/aruco/markers/pdf")
async def download_aruco_markers(marker_size_cm: float = 25.0):
    """10MWT용 ArUco 마커 PDF 생성 및 다운로드"""
    from analysis.aruco_marker_generator import generate_marker_pdf

    pdf_path = os.path.join(UPLOAD_DIR, "aruco_markers.pdf")
    generate_marker_pdf(pdf_path, marker_size_cm=marker_size_cm)

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="10MWT_ArUco_Markers.pdf"
    )


# 디버그 엔드포인트 (다른 라우트보다 먼저 정의해야 함)
@router.get("/debug/test-save")
async def debug_test_save():
    """디버그: save_analysis_status 테스트"""
    test_id = "debug-test-123"
    save_analysis_status(test_id, {
        "status": "testing",
        "progress": 50,
        "message": "테스트 중...",
        "current_frame": "TEST_FRAME_DATA"
    })
    # 바로 로드해서 확인
    loaded = load_analysis_status(test_id)
    return {
        "saved": True,
        "loaded": loaded is not None,
        "status_dir": STATUS_DIR,
        "data": loaded
    }


@router.post("/{patient_id}/upload")
async def upload_and_analyze(
    patient_id: str,
    background_tasks: BackgroundTasks,
    req: Request,
    file: UploadFile = File(...),
    walking_direction: str = Header(default="away", alias="X-Walking-Direction"),
    test_type: str = Header(default="10MWT", alias="X-Test-Type"),
    user_id: str = Header(None, alias="X-User-Id"),
    user_role: str = Header(None, alias="X-User-Role"),
    is_approved: str = Header(None, alias="X-User-Approved")
):
    """동영상 업로드 및 분석 시작 - 승인된 물리치료사만

    walking_direction: 보행 방향
        - "away": 카메라에서 멀어지는 방향 (기본값)
        - "toward": 카메라로 다가오는 방향

    test_type: 검사 유형
        - "10MWT": 10m 보행 검사 (기본값)
        - "TUG": Timed Up and Go 검사
    """
    verify_approved_therapist(user_id, user_role, is_approved)

    # 검사 유형 유효성 검사
    if test_type not in ["10MWT", "TUG"]:
        test_type = "10MWT"

    # 보행 방향 유효성 검사 (10MWT에만 해당)
    if walking_direction not in ["away", "toward"]:
        walking_direction = "away"

    # 환자 확인 및 키 정보 가져오기
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")

    patient_height_cm = patient["height_cm"]
    diagnosis = patient.get("diagnosis")

    # 파일 저장
    file_ext = os.path.splitext(file.filename)[1]
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    # 분석 상태 초기화 (파일 기반)
    test_type_label = "TUG 검사" if test_type == "TUG" else "10m 보행 검사"
    initial_status = {
        "status": "processing",
        "progress": 0,
        "message": f"{test_type_label} 분석 시작 중...",
        "current_frame": None
    }
    save_analysis_status(file_id, initial_status)
    print(f"[DEBUG] Initialized status for {file_id}, test_type={test_type}")

    log_action(
        user_id=user_id,
        action="upload_test",
        resource_type="test",
        resource_id=file_id,
        details={"patient_id": patient_id, "test_type": test_type, "filename": file.filename},
        ip_address=req.client.host if req.client else None,
    )

    # 백그라운드에서 분석 실행
    background_tasks.add_task(
        analyze_video_task,
        file_id,
        file_path,
        patient_id,
        patient_height_cm,
        walking_direction,
        test_type,
        diagnosis,
        user_id,
        patient.get("name", "")
    )

    return {
        "file_id": file_id,
        "message": "업로드 완료. 분석이 시작되었습니다.",
        "status_endpoint": f"/api/tests/status/{file_id}"
    }


def run_analysis_sync(file_id: str, file_path: str, patient_height_cm: float, walking_direction: str = "away", test_type: str = "10MWT", diagnosis: str = None):
    """동기식 분석 실행 (스레드에서 실행됨)"""
    # 캐시를 완전히 무시하고 새로 로드
    import sys

    # analysis 관련 모듈 모두 제거
    modules_to_remove = [key for key in sys.modules.keys() if 'analysis' in key or 'gait' in key or 'tug' in key]
    for mod in modules_to_remove:
        del sys.modules[mod]

    # 검사 유형에 따라 분석기 선택
    if test_type == "TUG":
        from analysis.tug_analyzer import TUGAnalyzer
        test_type_label = "TUG 검사"
    else:
        from analysis.gait_analyzer import GaitAnalyzer
        test_type_label = "10m 보행 검사"

    # 질환별 프로파일 매칭
    from analysis.disease_profiles import resolve_profile
    disease_profile = resolve_profile(diagnosis)
    print(f"[DEBUG] Disease profile: {disease_profile.display_name} ({disease_profile.name}) for diagnosis='{diagnosis}'")

    save_analysis_status(file_id, {
        "status": "processing",
        "progress": 5,
        "message": f"MediaPipe 모델 로딩 중... ({test_type_label})",
        "current_frame": None
    })

    if test_type == "TUG":
        analyzer = TUGAnalyzer(disease_profile=disease_profile)
    else:
        analyzer = GaitAnalyzer(disease_profile=disease_profile)

    direction_text = "카메라 방향으로" if walking_direction == "toward" else "카메라 반대 방향으로"
    analysis_msg = f"{test_type_label} 분석 중..." if test_type == "TUG" else f"동영상 프레임 분석 중... ({direction_text})"
    save_analysis_status(file_id, {
        "status": "processing",
        "progress": 10,
        "message": analysis_msg,
        "current_frame": None
    })

    # 현재 상태를 캐시 (매번 파일 읽기 방지)
    current_status = {
        "progress": 10,
        "message": "동영상 프레임 분석 중...",
        "current_phase": None,
        "current_phase_label": None
    }

    # 진행률 콜백 함수
    last_saved_progress = [10]  # 마지막 저장된 진행률 (파일 쓰기 빈도 제한용)

    def update_progress(progress: int):
        current_status["progress"] = progress
        # 진행률에 따라 메시지 업데이트
        if progress < 30:
            current_status["message"] = "동영상 프레임 분석 중..."
        elif progress < 70:
            current_status["message"] = "포즈 데이터 추출 중..."
        else:
            current_status["message"] = "보행 패턴 분석 중..."
        # 진행률이 2% 이상 변했을 때만 파일에 저장 (I/O 부하 방지)
        if progress - last_saved_progress[0] >= 2:
            last_saved_progress[0] = progress
            save_analysis_status(file_id, {
                "status": "processing",
                "progress": progress,
                "message": current_status["message"],
                "current_frame": None
            })

    # TUG 단계 콜백 함수 (실시간 단계 감지)
    def update_phase(phase_info: dict):
        current_status["current_phase"] = phase_info.get("phase")
        current_status["current_phase_label"] = phase_info.get("phase_label")
        print(f"[TUG PHASE] {phase_info.get('phase_label')} at {phase_info.get('time', 0):.2f}s")

    print(f"[DEBUG] Starting {test_type} analysis")

    # 분석 실행 (진행률 콜백 전달)
    if test_type == "TUG":
        result = analyzer.analyze(
            file_path,
            patient_height_cm,
            progress_callback=update_progress,
            phase_callback=update_phase
        )
    else:
        result = analyzer.analyze(
            file_path,
            patient_height_cm,
            progress_callback=update_progress,
            walking_direction=walking_direction
        )

    print(f"[DEBUG] {test_type} analysis complete.")

    return result


async def analyze_video_task(
    file_id: str,
    file_path: str,
    patient_id: str,
    patient_height_cm: float,
    walking_direction: str = "away",
    test_type: str = "10MWT",
    diagnosis: str = None,
    uploader_user_id: str = None,
    patient_name: str = ""
):
    """백그라운드 동영상 분석 작업"""
    _set_main_loop()
    try:
        # 분석을 별도 스레드에서 실행 (이벤트 루프 블록 방지)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            analysis_executor,
            run_analysis_sync,
            file_id,
            file_path,
            patient_height_cm,
            walking_direction,
            test_type,
            diagnosis
        )

        test_type_label = "TUG 검사" if test_type == "TUG" else "10m 보행 검사"
        save_analysis_status(file_id, {
            "status": "processing",
            "progress": 90,
            "message": f"{test_type_label} 결과 저장 중...",
            "current_frame": None
        })

        # 결과를 DB에 저장
        test_data = {
            "patient_id": patient_id,
            "test_type": test_type,
            "walk_time_seconds": result["walk_time_seconds"],
            "walk_speed_mps": result["walk_speed_mps"],
            "video_url": f"/uploads/{os.path.basename(file_path)}",
            "analysis_data": json.dumps(result)
        }

        db_result = db.create_test(test_data)
        cache.invalidate_tests(patient_id)
        cache.invalidate_dashboard()

        save_analysis_status(file_id, {
            "status": "completed",
            "progress": 100,
            "message": f"{test_type_label} 분석 완료!",
            "result": {
                "test_id": db_result["id"],
                "test_type": test_type,
                "walk_time_seconds": result["walk_time_seconds"],
                "walk_speed_mps": result["walk_speed_mps"]
            }
        })

        # 분석 완료 알림 전송
        if uploader_user_id:
            try:
                from app.services.notification_service import notify_analysis_complete
                notify_analysis_complete(uploader_user_id, patient_name, test_type, db_result["id"], patient_id)
            except Exception:
                pass

    except Exception as e:
        save_analysis_status(file_id, {
            "status": "error",
            "progress": 0,
            "message": f"분석 중 오류 발생: {str(e)}"
        })


@router.get("/status/{file_id}")
async def get_analysis_status(file_id: str):
    """분석 진행 상태 조회"""
    status = load_analysis_status(file_id)
    if status is None:
        raise HTTPException(status_code=404, detail="분석 상태를 찾을 수 없습니다.")

    has_frame = status.get("current_frame") is not None
    frame_len = len(status.get("current_frame") or "")
    print(f"[STATUS API] file_id={file_id}, progress={status.get('progress')}, has_frame={has_frame}, frame_len={frame_len}")

    return status


@router.post("/{patient_id}/upload-tug")
async def upload_tug_dual_video(
    patient_id: str,
    background_tasks: BackgroundTasks,
    side_video: UploadFile = File(..., description="측면 영상 (보행 분석, 기립/착석 속도)"),
    front_video: UploadFile = File(..., description="정면 영상 (어깨/골반 기울기)"),
    user_id: str = Header(None, alias="X-User-Id"),
    user_role: str = Header(None, alias="X-User-Role"),
    is_approved: str = Header(None, alias="X-User-Approved")
):
    """TUG 검사 두 영상 업로드 및 분석 시작

    - side_video: 측면 영상 (보행 분석, 기립/착석 속도 측정용)
    - front_video: 정면 영상 (어깨/골반 기울기 분석용)
    """
    verify_approved_therapist(user_id, user_role, is_approved)

    # 환자 확인 및 키 정보 가져오기
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")

    patient_height_cm = patient["height_cm"]
    diagnosis = patient.get("diagnosis")

    # 파일 저장
    file_id = str(uuid.uuid4())

    # 측면 영상 저장
    side_ext = os.path.splitext(side_video.filename)[1]
    side_filename = f"{file_id}_side{side_ext}"
    side_path = os.path.join(UPLOAD_DIR, side_filename)

    async with aiofiles.open(side_path, 'wb') as out_file:
        content = await side_video.read()
        await out_file.write(content)

    # 정면 영상 저장
    front_ext = os.path.splitext(front_video.filename)[1]
    front_filename = f"{file_id}_front{front_ext}"
    front_path = os.path.join(UPLOAD_DIR, front_filename)

    async with aiofiles.open(front_path, 'wb') as out_file:
        content = await front_video.read()
        await out_file.write(content)

    # 분석 상태 초기화
    initial_status = {
        "status": "processing",
        "progress": 0,
        "message": "TUG 검사 분석 준비 중...",
        "current_frame": None
    }
    save_analysis_status(file_id, initial_status)
    print(f"[DEBUG] Initialized TUG dual video status for {file_id}")

    # 백그라운드에서 분석 실행
    background_tasks.add_task(
        analyze_tug_dual_video_task,
        file_id,
        side_path,
        front_path,
        patient_id,
        patient_height_cm,
        diagnosis
    )

    return {
        "file_id": file_id,
        "message": "업로드 완료. TUG 분석이 시작되었습니다.",
        "status_endpoint": f"/api/tests/status/{file_id}"
    }


def run_tug_dual_analysis_sync(
    file_id: str,
    side_video_path: str,
    front_video_path: str,
    patient_height_cm: float,
    diagnosis: str = None
):
    """TUG 두 영상 동기식 분석 (스레드에서 실행됨)"""
    import sys

    # 캐시 무시하고 새로 로드
    modules_to_remove = [key for key in sys.modules.keys() if 'analysis' in key or 'tug' in key]
    for mod in modules_to_remove:
        del sys.modules[mod]

    from analysis.tug_analyzer import TUGAnalyzer
    from analysis.disease_profiles import resolve_profile

    # 질환별 프로파일 매칭
    disease_profile = resolve_profile(diagnosis)
    print(f"[DEBUG] TUG Dual - Disease profile: {disease_profile.display_name} ({disease_profile.name}) for diagnosis='{diagnosis}'")

    save_analysis_status(file_id, {
        "status": "processing",
        "progress": 5,
        "message": "MediaPipe 모델 로딩 중...",
        "current_frame": None
    })

    analyzer = TUGAnalyzer(disease_profile=disease_profile)

    save_analysis_status(file_id, {
        "status": "processing",
        "progress": 10,
        "message": "측면 영상 분석 중 (보행 + 기립/착석)...",
        "current_frame": None,
        "current_phase": None,
        "current_phase_label": None
    })

    current_status = {
        "progress": 10,
        "message": "측면 영상 분석 중...",
        "current_phase": None,
        "current_phase_label": None
    }

    def update_progress(progress: int):
        current_status["progress"] = progress
        if progress < 50:
            current_status["message"] = "측면 영상 분석 중 (보행 + 기립/착석)..."
        elif progress < 90:
            current_status["message"] = "정면 영상 분석 중 (기울기)..."
        else:
            current_status["message"] = "분석 결과 통합 중..."
        # 매번 파일에 저장 (디버깅용)
        save_analysis_status(file_id, {
            "status": "processing",
            "progress": progress,
            "message": current_status["message"],
            "current_frame": None,
            "current_phase": current_status.get("current_phase"),
            "current_phase_label": current_status.get("current_phase_label")
        })

    def update_phase(phase_info: dict):
        current_status["current_phase"] = phase_info.get("phase")
        current_status["current_phase_label"] = phase_info.get("phase_label")
        print(f"[TUG DUAL PHASE] {phase_info.get('phase_label')} at {phase_info.get('time', 0):.2f}s")

    result = analyzer.analyze_dual_video(
        side_video_path,
        front_video_path,
        patient_height_cm,
        progress_callback=update_progress,
        phase_callback=update_phase,
        file_id=file_id
    )

    print(f"[DEBUG] TUG dual video analysis complete.")
    return result


async def analyze_tug_dual_video_task(
    file_id: str,
    side_video_path: str,
    front_video_path: str,
    patient_id: str,
    patient_height_cm: float,
    diagnosis: str = None
):
    """백그라운드 TUG 두 영상 분석 작업"""
    _set_main_loop()
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            analysis_executor,
            run_tug_dual_analysis_sync,
            file_id,
            side_video_path,
            front_video_path,
            patient_height_cm,
            diagnosis
        )

        save_analysis_status(file_id, {
            "status": "processing",
            "progress": 95,
            "message": "TUG 검사 결과 저장 중...",
            "current_frame": None
        })

        # 결과를 DB에 저장
        test_data = {
            "patient_id": patient_id,
            "test_type": "TUG",
            "walk_time_seconds": result["walk_time_seconds"],
            "walk_speed_mps": result["walk_speed_mps"],
            "video_url": f"/uploads/{os.path.basename(side_video_path)}",  # 측면 영상 URL
            "analysis_data": json.dumps(result)
        }

        db_result = db.create_test(test_data)
        cache.invalidate_tests(patient_id)
        cache.invalidate_dashboard()

        save_analysis_status(file_id, {
            "status": "completed",
            "progress": 100,
            "message": "TUG 검사 분석 완료!",
            "result": {
                "test_id": db_result["id"],
                "test_type": "TUG",
                "walk_time_seconds": result["walk_time_seconds"],
                "walk_speed_mps": result["walk_speed_mps"]
            }
        })

    except Exception as e:
        save_analysis_status(file_id, {
            "status": "error",
            "progress": 0,
            "message": f"TUG 분석 중 오류 발생: {str(e)}"
        })
        print(f"[ERROR] TUG dual video analysis failed: {e}")


@router.get("/patient/{patient_id}", response_model=List[WalkTestResponse])
async def get_patient_tests(patient_id: str, test_type: Optional[str] = None):
    """환자의 검사 히스토리 조회

    test_type: 검사 유형 필터 (선택사항)
        - None 또는 "ALL": 모든 검사
        - "10MWT": 10m 보행 검사만
        - "TUG": TUG 검사만
    """
    cached = cache.get_patient_tests(patient_id, test_type)
    if cached is not None:
        return cached
    tests = db.get_patient_tests(patient_id, test_type=test_type)
    result = [parse_analysis_data(t) for t in tests]
    cache.set_patient_tests(patient_id, result, test_type)
    return result


@router.get("/{test_id}", response_model=WalkTestResponse)
async def get_test(test_id: str):
    """검사 상세 조회"""
    result = db.get_test(test_id)
    if not result:
        raise HTTPException(status_code=404, detail="검사 결과를 찾을 수 없습니다.")
    return parse_analysis_data(result)


@router.get("/patient/{patient_id}/compare", response_model=ComparisonResponse)
async def compare_tests(patient_id: str):
    """최근 검사와 이전 검사 비교"""
    tests = db.get_patient_tests(patient_id)

    if not tests:
        raise HTTPException(status_code=404, detail="검사 기록이 없습니다.")

    current_test = parse_analysis_data(tests[0])
    previous_test = parse_analysis_data(tests[1]) if len(tests) > 1 else None

    # 비교 메시지 생성
    if previous_test:
        speed_diff = current_test["walk_speed_mps"] - previous_test["walk_speed_mps"]
        time_diff = current_test["walk_time_seconds"] - previous_test["walk_time_seconds"]

        # 시간 감소 = 개선 (음수)
        if time_diff < -0.3:
            comparison_message = f"보행 시간이 {abs(time_diff):.2f}초 단축되어 낙상 위험 가능성이 감소된 것으로 추정됩니다."
        elif time_diff > 0.3:
            comparison_message = f"보행 시간이 {abs(time_diff):.2f}초 증가하여 낙상 위험 가능성이 증가된 것으로 추정됩니다."
        else:
            comparison_message = "보행 시간 변화가 미미하여 낙상 위험도에 큰 변화가 없는 것으로 추정됩니다."
    else:
        speed_diff = None
        time_diff = None
        comparison_message = "이전 검사 기록이 없어 비교할 수 없습니다."

    return {
        "current_test": current_test,
        "previous_test": previous_test,
        "comparison_message": comparison_message,
        "speed_difference": speed_diff,
        "time_difference": time_diff
    }


@router.get("/patient/{patient_id}/stats")
async def get_patient_stats(patient_id: str, test_type: Optional[str] = "10MWT"):
    """환자의 검사 통계 (반복 측정 평균)

    test_type: 검사 유형 필터 (기본: 10MWT)
    """
    tests = db.get_patient_tests(patient_id, test_type=test_type)

    if not tests:
        raise HTTPException(status_code=404, detail="검사 기록이 없습니다.")

    parsed = [parse_analysis_data(t) for t in tests]

    times = [t["walk_time_seconds"] for t in parsed]
    speeds = [t["walk_speed_mps"] for t in parsed]

    import numpy as np
    stats = {
        "test_count": len(parsed),
        "test_type": test_type,
        "walk_time": {
            "mean": round(float(np.mean(times)), 2),
            "std": round(float(np.std(times)), 2),
            "min": round(float(np.min(times)), 2),
            "max": round(float(np.max(times)), 2),
        },
        "walk_speed": {
            "mean": round(float(np.mean(speeds)), 2),
            "std": round(float(np.std(speeds)), 2),
            "min": round(float(np.min(speeds)), 2),
            "max": round(float(np.max(speeds)), 2),
        },
    }

    # 정상 범위 비교 (환자 정보 필요)
    patient = db.get_patient(patient_id)
    if patient and patient.get("birth_date") and patient.get("gender"):
        from app.services.normative_data import calculate_age, get_speed_assessment, get_time_assessment
        age = calculate_age(patient["birth_date"])
        if age > 0:
            stats["normative"] = get_speed_assessment(
                float(np.mean(speeds)), age, patient["gender"]
            )
            stats["normative_time"] = get_time_assessment(
                float(np.mean(times)), age, patient["gender"]
            )

    return stats


@router.get("/patient/{patient_id}/clinical-normative")
async def get_clinical_normative(patient_id: str, test_id: Optional[str] = Query(None)):
    """환자의 임상 변수에 대한 연령/성별 기반 정상 범위 평가"""
    from app.services.normative_data import calculate_age, get_clinical_variable_assessment

    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")

    age = calculate_age(patient.get("birth_date", "")) if patient.get("birth_date") else 0
    gender = patient.get("gender", "M")

    # 특정 검사 또는 최신 검사의 임상 변수 가져오기
    if test_id:
        test = db.get_test(test_id)
    else:
        tests = db.get_patient_tests(patient_id, test_type="10MWT")
        test = tests[0] if tests else None

    if not test:
        return {}

    analysis_data = test.get("analysis_data")
    if isinstance(analysis_data, str):
        import json as _json
        try:
            analysis_data = _json.loads(analysis_data)
        except Exception:
            analysis_data = {}

    cv = (analysis_data or {}).get("clinical_variables", {})
    if not cv:
        return {}

    result = {}
    # stride_length
    sl = cv.get("stride_length")
    if sl:
        val = sl.get("value", 0)
        if val > 0:
            assess = get_clinical_variable_assessment("stride_length", val, age, gender)
            if assess:
                result["stride_length"] = assess

    # cadence
    cad = cv.get("cadence")
    if cad:
        val = cad.get("value", 0)
        if val > 0:
            assess = get_clinical_variable_assessment("cadence", val, age, gender)
            if assess:
                result["cadence"] = assess

    # step_time
    st = cv.get("step_time")
    if st:
        val = st.get("mean", 0)
        if val > 0:
            assess = get_clinical_variable_assessment("step_time", val, age, gender)
            if assess:
                result["step_time"] = assess

    # double_support
    ds = cv.get("double_support")
    if ds:
        val = ds.get("value", 0)
        if val > 0:
            assess = get_clinical_variable_assessment("double_support", val, age, gender)
            if assess:
                result["double_support"] = assess

    # swing_pct
    ss = cv.get("swing_stance_ratio")
    if ss:
        val = ss.get("swing_pct", 0)
        if val > 0:
            assess = get_clinical_variable_assessment("swing_pct", val, age, gender)
            if assess:
                result["swing_pct"] = assess

    # 정상 범위만 (정규화 평가 없는 변수)
    asym = cv.get("step_time_asymmetry")
    if asym:
        val = asym.get("value", 0)
        result["step_time_asymmetry"] = {
            "value": val,
            "comparison": "normal" if val < 10 else ("below_average" if val < 20 else "below_normal"),
            "comparison_label": "정상" if val < 10 else ("경도 비대칭" if val < 20 else "비대칭"),
            "label": "좌우 비대칭",
            "unit": "%",
            "normative": {"range_low": 0, "range_high": 10, "age_group": "전 연령", "gender": gender},
        }

    sr = cv.get("stride_regularity")
    if sr:
        val = sr.get("value", 0)
        result["stride_regularity"] = {
            "value": val,
            "comparison": "normal" if val >= 0.7 else ("below_average" if val >= 0.5 else "below_normal"),
            "comparison_label": "정상" if val >= 0.7 else ("다소 불규칙" if val >= 0.5 else "불규칙"),
            "label": "보행 규칙성",
            "unit": "",
            "normative": {"range_low": 0.7, "range_high": 1.0, "age_group": "전 연령", "gender": gender},
        }

    return result


@router.get("/patient/{patient_id}/clinical-trends")
async def get_clinical_trends(patient_id: str, test_type: Optional[str] = Query("10MWT")):
    """환자의 임상 변수 추이 데이터"""
    tests = db.get_patient_tests(patient_id, test_type=test_type)
    if not tests:
        return {"data_points": [], "variables": [], "total_tests": 0, "tests_with_clinical_data": 0}

    import json as _json
    data_points = []
    all_vars = set()

    for t in reversed(tests):  # 오래된 것부터
        ad = t.get("analysis_data")
        if isinstance(ad, str):
            try:
                ad = _json.loads(ad)
            except Exception:
                continue
        cv = (ad or {}).get("clinical_variables", {})
        if not cv:
            continue

        point = {"test_id": t["id"], "date": t.get("created_at", "")[:10]}
        # 속도/시간도 포함
        point["walk_speed"] = t.get("walk_speed_mps")
        point["walk_time"] = t.get("walk_time_seconds")

        if cv.get("stride_length"):
            point["stride_length"] = cv["stride_length"].get("value")
            all_vars.add("stride_length")
        if cv.get("cadence"):
            point["cadence"] = cv["cadence"].get("value")
            all_vars.add("cadence")
        if cv.get("step_time"):
            point["step_time"] = cv["step_time"].get("mean")
            all_vars.add("step_time")
        if cv.get("step_time_asymmetry"):
            point["step_time_asymmetry"] = cv["step_time_asymmetry"].get("value")
            all_vars.add("step_time_asymmetry")
        if cv.get("double_support"):
            point["double_support"] = cv["double_support"].get("value")
            all_vars.add("double_support")
        if cv.get("swing_stance_ratio"):
            point["swing_pct"] = cv["swing_stance_ratio"].get("swing_pct")
            all_vars.add("swing_pct")
        if cv.get("arm_swing"):
            point["arm_swing_asymmetry"] = cv["arm_swing"].get("asymmetry_index")
            all_vars.add("arm_swing_asymmetry")
        if cv.get("stride_regularity"):
            point["stride_regularity"] = cv["stride_regularity"].get("value")
            all_vars.add("stride_regularity")
        if cv.get("trunk_inclination"):
            point["trunk_inclination"] = cv["trunk_inclination"].get("angle") or cv["trunk_inclination"].get("mean")
            all_vars.add("trunk_inclination")

        data_points.append(point)

    return {
        "data_points": data_points,
        "variables": sorted(all_vars),
        "total_tests": len(tests),
        "tests_with_clinical_data": len(data_points),
    }


@router.get("/patient/{patient_id}/clinical-correlations")
async def get_clinical_correlations(patient_id: str, test_type: Optional[str] = Query("10MWT")):
    """환자의 임상 변수 간 상관관계 분석"""
    import json as _json

    tests = db.get_patient_tests(patient_id, test_type=test_type)
    if not tests:
        return {"sufficient_data": False, "message": "검사 데이터가 없습니다.", "n_tests": 0}

    # 데이터 수집
    records = []
    for t in tests:
        ad = t.get("analysis_data")
        if isinstance(ad, str):
            try:
                ad = _json.loads(ad)
            except Exception:
                continue
        cv = (ad or {}).get("clinical_variables", {})
        if not cv:
            continue

        rec = {"walk_speed": t.get("walk_speed_mps"), "walk_time": t.get("walk_time_seconds")}
        if cv.get("stride_length"):
            rec["stride_length"] = cv["stride_length"].get("value")
        if cv.get("cadence"):
            rec["cadence"] = cv["cadence"].get("value")
        if cv.get("step_time_asymmetry"):
            rec["step_time_asymmetry"] = cv["step_time_asymmetry"].get("value")
        if cv.get("double_support"):
            rec["double_support"] = cv["double_support"].get("value")
        if cv.get("stride_regularity"):
            rec["stride_regularity"] = cv["stride_regularity"].get("value")
        if cv.get("arm_swing"):
            rec["arm_swing_asymmetry"] = cv["arm_swing"].get("asymmetry_index")
        records.append(rec)

    if len(records) < 3:
        return {"sufficient_data": False, "message": "상관관계 분석에는 최소 3개의 검사가 필요합니다.", "n_tests": len(records)}

    # 공통 변수 추출
    all_keys = set()
    for r in records:
        all_keys.update(r.keys())

    # 최소 3개 데이터가 있는 변수만
    valid_vars = []
    for k in sorted(all_keys):
        count = sum(1 for r in records if r.get(k) is not None)
        if count >= 3:
            valid_vars.append(k)

    if len(valid_vars) < 2:
        return {"sufficient_data": False, "message": "분석 가능한 변수가 부족합니다.", "n_tests": len(records)}

    var_labels = {
        "walk_speed": "보행 속도",
        "walk_time": "보행 시간",
        "stride_length": "보폭",
        "cadence": "분당 걸음수",
        "step_time_asymmetry": "좌우 비대칭",
        "double_support": "이중지지기",
        "stride_regularity": "보행 규칙성",
        "arm_swing_asymmetry": "팔 흔들림 비대칭",
    }

    # 상관행렬 계산
    from scipy import stats as sp_stats
    n = len(valid_vars)
    corr_matrix = [[0.0] * n for _ in range(n)]
    significant_correlations = []

    for i in range(n):
        corr_matrix[i][i] = 1.0
        for j in range(i + 1, n):
            pairs = [(r[valid_vars[i]], r[valid_vars[j]])
                     for r in records
                     if r.get(valid_vars[i]) is not None and r.get(valid_vars[j]) is not None]
            if len(pairs) >= 3:
                x_vals = [p[0] for p in pairs]
                y_vals = [p[1] for p in pairs]
                import math
                r_val, p_val = sp_stats.pearsonr(x_vals, y_vals)
                if math.isnan(r_val) or math.isnan(p_val):
                    r_val, p_val = 0.0, 1.0
                corr_matrix[i][j] = round(r_val, 3)
                corr_matrix[j][i] = round(r_val, 3)

                if abs(r_val) >= 0.3:
                    significant_correlations.append({
                        "var1": valid_vars[i],
                        "var2": valid_vars[j],
                        "r": round(r_val, 3),
                        "p_value": round(p_val, 4),
                        "label": f"{var_labels.get(valid_vars[i], valid_vars[i])} vs {var_labels.get(valid_vars[j], valid_vars[j])}",
                    })

    significant_correlations.sort(key=lambda x: abs(x["r"]), reverse=True)

    # 보행속도와 각 변수의 상관
    speed_correlations = []
    if "walk_speed" in valid_vars:
        si = valid_vars.index("walk_speed")
        for j, v in enumerate(valid_vars):
            if v != "walk_speed":
                speed_correlations.append({
                    "variable": v,
                    "r": corr_matrix[si][j],
                    "label": var_labels.get(v, v),
                })
        speed_correlations.sort(key=lambda x: abs(x["r"]), reverse=True)

    # 산점도 데이터 (상위 5개 상관)
    scatter_data = {}
    for sc in significant_correlations[:5]:
        key = f"{sc['var1']}_vs_{sc['var2']}"
        pairs = [{"x": r[sc["var1"]], "y": r[sc["var2"]]}
                 for r in records
                 if r.get(sc["var1"]) is not None and r.get(sc["var2"]) is not None]
        scatter_data[key] = pairs

    return {
        "variables": valid_vars,
        "variable_labels": {v: var_labels.get(v, v) for v in valid_vars},
        "correlation_matrix": corr_matrix,
        "significant_correlations": significant_correlations,
        "scatter_data": scatter_data,
        "speed_correlations": speed_correlations,
        "n_tests": len(records),
        "sufficient_data": True,
    }


@router.get("/{test_id}/ai-report")
async def get_ai_report(test_id: str):
    """AI 임상 리포트 자동 생성"""
    from app.services.ai_report_generator import generate_ai_report

    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="검사를 찾을 수 없습니다.")

    try:
        report = generate_ai_report(test["patient_id"], test_id)
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"리포트 생성 실패: {str(e)}")


@router.get("/{test_id}/report/csv")
async def download_csv(test_id: str):
    """CSV 리포트 다운로드"""
    from app.services.report_generator import generate_csv_report

    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="검사 결과를 찾을 수 없습니다.")

    patient = db.get_patient(test["patient_id"])
    test_with_patient = {**parse_analysis_data(test), "patients": patient}

    csv_content = generate_csv_report(test_with_patient)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=walk_test_{test_id}.csv"}
    )


@router.get("/{test_id}/report/pdf")
async def download_pdf(test_id: str, template: str = "standard"):
    """PDF 리포트 다운로드 (검사 유형 자동 감지)

    template: 리포트 템플릿 이름 (standard, clinical, summary, 또는 커스텀)
    """
    from app.services.report_generator import generate_pdf_report, generate_tug_pdf, generate_bbs_pdf

    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="검사 결과를 찾을 수 없습니다.")

    test_data = parse_analysis_data(test)
    patient = db.get_patient(test_data["patient_id"])

    # 환자의 모든 검사 기록 조회 (그래프용)
    all_tests = db.get_patient_tests(test_data["patient_id"])
    all_tests_parsed = [parse_analysis_data(t) for t in all_tests]
    # 날짜순 정렬 (오래된 것부터)
    all_tests_parsed.reverse()

    # 검사 유형에 따라 적절한 PDF 생성기 선택
    test_type = test_data.get("test_type", "10MWT")
    if test_type == "TUG":
        pdf_path = generate_tug_pdf(test_data, patient, all_tests_parsed)
        filename = f"tug_report_{test_id}.pdf"
    elif test_type == "BBS":
        pdf_path = generate_bbs_pdf(test_data, patient, all_tests_parsed)
        filename = f"bbs_report_{test_id}.pdf"
    else:
        pdf_path = generate_pdf_report(test_data, patient, all_tests_parsed, template_name=template)
        filename = f"walk_test_report_{test_id}.pdf"

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename
    )


class EmailReportRequest(BaseModel):
    to_email: str
    message: Optional[str] = None
    template: Optional[str] = "standard"


@router.post("/{test_id}/report/email")
async def email_report(test_id: str, body: EmailReportRequest):
    """Send PDF report to specified email address."""
    from app.services.report_generator import generate_pdf_report, generate_tug_pdf, generate_bbs_pdf
    from app.services.email_service import email_service

    if not email_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Email service is not configured. Set SMTP_HOST in environment variables."
        )

    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="검사 결과를 찾을 수 없습니다.")

    test_data = parse_analysis_data(test)
    patient = db.get_patient(test_data["patient_id"])
    if not patient:
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")

    all_tests = db.get_patient_tests(test_data["patient_id"])
    all_tests_parsed = [parse_analysis_data(t) for t in all_tests]
    all_tests_parsed.reverse()

    test_type = test_data.get("test_type", "10MWT")
    template_name = body.template or "standard"

    if test_type == "TUG":
        pdf_path = generate_tug_pdf(test_data, patient, all_tests_parsed)
    elif test_type == "BBS":
        pdf_path = generate_bbs_pdf(test_data, patient, all_tests_parsed)
    else:
        pdf_path = generate_pdf_report(test_data, patient, all_tests_parsed, template_name=template_name)

    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
    finally:
        try:
            os.remove(pdf_path)
        except Exception:
            pass

    result = await email_service.send_report_email(
        to_email=body.to_email,
        patient_name=patient.get("name", "Unknown"),
        test_type=test_type,
        pdf_bytes=pdf_bytes,
        message=body.message,
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])

    return result


@router.get("/patient/{patient_id}/report/batch-pdf")
async def download_batch_pdf(patient_id: str):
    """환자의 최근 검사를 유형별로 묶어 종합 PDF 생성"""
    from app.services.report_generator import generate_pdf_report, generate_tug_pdf, generate_bbs_pdf

    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")

    all_tests = db.get_patient_tests(patient_id)
    if not all_tests:
        raise HTTPException(status_code=404, detail="검사 기록이 없습니다.")

    all_tests_parsed = [parse_analysis_data(t) for t in all_tests]
    all_tests_parsed.reverse()

    # 각 유형별 최신 검사 1개씩 가져오기
    latest_by_type = {}
    for t in reversed(all_tests_parsed):
        tt = t.get("test_type", "10MWT")
        latest_by_type[tt] = t

    pdf_paths = []
    for tt, td in latest_by_type.items():
        if tt == "TUG":
            pdf_paths.append(generate_tug_pdf(td, patient, all_tests_parsed))
        elif tt == "BBS":
            pdf_paths.append(generate_bbs_pdf(td, patient, all_tests_parsed))
        else:
            pdf_paths.append(generate_pdf_report(td, patient, all_tests_parsed))

    if len(pdf_paths) == 1:
        return FileResponse(
            pdf_paths[0],
            media_type="application/pdf",
            filename=f"batch_report_{patient_id[:8]}.pdf"
        )

    # Merge PDFs
    import tempfile
    from PyPDF2 import PdfMerger

    merger = PdfMerger()
    for p in pdf_paths:
        merger.append(p)

    merged_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    merged_path = merged_file.name
    merged_file.close()
    merger.write(merged_path)
    merger.close()

    # Clean up individual PDFs
    for p in pdf_paths:
        try:
            os.remove(p)
        except:
            pass

    return FileResponse(
        merged_path,
        media_type="application/pdf",
        filename=f"batch_report_{patient_id[:8]}.pdf"
    )


@router.get("/{test_id}/video/info")
async def get_video_info(test_id: str):
    """영상 파일 정보 조회"""
    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="검사 결과를 찾을 수 없습니다.")

    if not test.get("video_url"):
        raise HTTPException(status_code=404, detail="이 검사에 연결된 영상이 없습니다.")

    video_filename = os.path.basename(test["video_url"])
    video_path = os.path.join(UPLOAD_DIR, video_filename)

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="영상 파일을 찾을 수 없습니다.")

    file_stat = os.stat(video_path)

    return {
        "filename": video_filename,
        "size_bytes": file_stat.st_size,
        "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
        "video_url": test["video_url"]
    }


@router.get("/{test_id}/video/download")
async def download_video(test_id: str):
    """영상 파일 다운로드"""
    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="검사 결과를 찾을 수 없습니다.")

    if not test.get("video_url"):
        raise HTTPException(status_code=404, detail="이 검사에 연결된 영상이 없습니다.")

    video_filename = os.path.basename(test["video_url"])
    video_path = os.path.join(UPLOAD_DIR, video_filename)

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="영상 파일을 찾을 수 없습니다.")

    # 파일 확장자 추출
    _, ext = os.path.splitext(video_filename)
    download_filename = f"walk_test_{test_id}{ext}"

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=download_filename
    )


# 포즈 오버레이 상태 관리 (테스트별 프레임 위치)
pose_overlay_states: dict = {}


@router.get("/{test_id}/video/overlay/frame")
async def get_single_pose_frame(test_id: str, frame_num: int = 0, reset: bool = False):
    """단일 포즈 오버레이 프레임 반환 (프레임 번호 지정)

    브라우저 호환성을 위해 단일 JPEG 프레임을 반환합니다.
    """
    import cv2
    import mediapipe as mp
    from fastapi.responses import Response

    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="검사 결과를 찾을 수 없습니다.")

    if not test.get("video_url"):
        raise HTTPException(status_code=404, detail="이 검사에 연결된 영상이 없습니다.")

    video_filename = os.path.basename(test["video_url"])
    video_path = os.path.join(UPLOAD_DIR, video_filename)

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="영상 파일을 찾을 수 없습니다.")

    # MediaPipe 초기화
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles

    pose = mp_pose.Pose(
        static_image_mode=True,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5
    )

    cap = cv2.VideoCapture(video_path)

    try:
        # 프레임 위치로 이동
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = cap.read()

        if not ret:
            # 영상 끝에 도달하면 처음 프레임 반환
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                raise HTTPException(status_code=500, detail="프레임을 읽을 수 없습니다.")

        # BGR -> RGB 변환
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # MediaPipe 포즈 감지
        results = pose.process(rgb_frame)

        # 포즈 랜드마크 그리기
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
            )

        # JPEG로 인코딩
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frame_bytes = buffer.tobytes()

        # 총 프레임 수 반환
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30

        return Response(
            content=frame_bytes,
            media_type="image/jpeg",
            headers={
                "X-Total-Frames": str(total_frames),
                "X-FPS": str(fps),
                "X-Current-Frame": str(frame_num),
                "Cache-Control": "no-cache, no-store, must-revalidate"
            }
        )

    finally:
        cap.release()
        pose.close()


@router.get("/{test_id}/phase-clip/{phase_name}")
async def get_phase_clip(test_id: str, phase_name: str):
    """TUG 단계별 전환 클립 서빙"""
    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="검사 결과를 찾을 수 없습니다.")

    analysis = test.get("analysis_data")
    if isinstance(analysis, str):
        analysis = json.loads(analysis)

    if not analysis:
        raise HTTPException(status_code=404, detail="분석 데이터가 없습니다.")

    clips = analysis.get('phase_clips', {})
    clip_info = clips.get(phase_name)

    if not clip_info or not clip_info.get('clip_filename'):
        raise HTTPException(status_code=404, detail="해당 단계 클립을 찾을 수 없습니다.")

    clip_path = os.path.join(UPLOAD_DIR, clip_info['clip_filename'])
    if not os.path.exists(clip_path):
        raise HTTPException(status_code=404, detail="클립 파일을 찾을 수 없습니다.")

    return FileResponse(clip_path, media_type="video/mp4",
                        filename=clip_info['clip_filename'])


@router.get("/{test_id}/video/overlay")
async def stream_video_with_pose_overlay(test_id: str):
    """MediaPipe 포즈 오버레이가 적용된 영상 스트리밍

    원본 영상에 실시간으로 MediaPipe 포즈 랜드마크와 스켈레톤을 그려서 스트리밍합니다.
    """
    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="검사 결과를 찾을 수 없습니다.")

    if not test.get("video_url"):
        raise HTTPException(status_code=404, detail="이 검사에 연결된 영상이 없습니다.")

    video_filename = os.path.basename(test["video_url"])
    video_path = os.path.join(UPLOAD_DIR, video_filename)

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="영상 파일을 찾을 수 없습니다.")

    def generate_overlay_frames():
        """MediaPipe 포즈 오버레이 프레임 생성기"""
        import cv2
        import mediapipe as mp

        # MediaPipe 초기화
        mp_pose = mp.solutions.pose
        mp_drawing = mp.solutions.drawing_utils
        mp_drawing_styles = mp.solutions.drawing_styles

        pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        cap = cv2.VideoCapture(video_path)

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # BGR -> RGB 변환
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # MediaPipe 포즈 감지
                results = pose.process(rgb_frame)

                # 포즈 랜드마크 그리기
                if results.pose_landmarks:
                    mp_drawing.draw_landmarks(
                        frame,
                        results.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS,
                        landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
                    )

                # JPEG로 인코딩
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_bytes = buffer.tobytes()

                # multipart/x-mixed-replace 형식으로 전송
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        finally:
            cap.release()
            pose.close()

    return StreamingResponse(
        generate_overlay_frames(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )


class TestDateUpdate(BaseModel):
    test_date: str


class TestNotesUpdate(BaseModel):
    notes: Optional[str] = None


@router.put("/{test_id}/date")
async def update_test_date(test_id: str, data: TestDateUpdate):
    """검사 날짜 수정"""
    result = db.update_test_date(test_id, data.test_date)
    if not result:
        raise HTTPException(status_code=404, detail="검사 결과를 찾을 수 없습니다.")
    return {"message": "검사 날짜가 수정되었습니다.", "test": parse_analysis_data(result)}


@router.put("/{test_id}/notes")
async def update_test_notes(test_id: str, data: TestNotesUpdate):
    """검사 메모 수정"""
    result = db.update_test_notes(test_id, data.notes or "")
    if not result:
        raise HTTPException(status_code=404, detail="검사 결과를 찾을 수 없습니다.")
    return {"message": "메모가 수정되었습니다.", "test": parse_analysis_data(result)}


@router.delete("/{test_id}")
async def delete_test(
    test_id: str,
    req: Request,
    user_id: str = Header(None, alias="X-User-Id"),
):
    """검사 삭제"""
    # 동영상 파일도 삭제
    test = db.get_test(test_id)
    if test and test.get("video_url"):
        video_path = os.path.join(UPLOAD_DIR, os.path.basename(test["video_url"]))
        if os.path.exists(video_path):
            os.remove(video_path)

    if not db.delete_test(test_id):
        raise HTTPException(status_code=404, detail="검사 결과를 찾을 수 없습니다.")

    if test:
        cache.invalidate_tests(test["patient_id"])
    cache.invalidate_dashboard()

    log_action(
        user_id=user_id,
        action="delete_test",
        resource_type="test",
        resource_id=test_id,
        details={"patient_id": test["patient_id"]} if test else None,
        ip_address=req.client.host if req.client else None,
    )

    return {"message": "검사 기록이 삭제되었습니다."}


# ============= BBS (Berg Balance Scale) 검사 =============

class BBSItemScores(BaseModel):
    """BBS 14개 항목 점수 (각 0-4점)"""
    item1_sitting_to_standing: int       # 앉은 자세에서 일어나기
    item2_standing_unsupported: int      # 잡지 않고 서 있기
    item3_sitting_unsupported: int       # 등받이에 기대지 않고 앉기
    item4_standing_to_sitting: int       # 선자세에서 앉기
    item5_transfers: int                 # 의자에서 의자로 이동하기
    item6_standing_eyes_closed: int      # 두눈을 감고 서 있기
    item7_standing_feet_together: int    # 두발을 붙이고 서 있기
    item8_reaching_forward: int          # 선자세에서 앞으로 팔 뻗기
    item9_pick_up_object: int            # 바닥에서 물건 줍기
    item10_turning_to_look_behind: int   # 뒤돌아보기
    item11_turn_360_degrees: int         # 제자리에서 360도 회전
    item12_stool_stepping: int           # 발판 위에 발 교대로 올리기
    item13_standing_one_foot_front: int  # 일렬로 서기 (탄뎀)
    item14_standing_on_one_leg: int      # 한 다리로 서기


class BBSTestCreate(BaseModel):
    """BBS 검사 생성 요청"""
    scores: BBSItemScores
    notes: Optional[str] = None


def calculate_bbs_assessment(total_score: int) -> tuple:
    """BBS 총점에 따른 평가 결과 반환"""
    if total_score <= 20:
        return "wheelchair_bound", "휠체어 의존"
    elif total_score <= 40:
        return "walking_with_assistance", "보조 보행"
    else:
        return "independent", "독립적"


@router.post("/{patient_id}/upload-bbs")
async def upload_bbs_video(
    patient_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Header(None, alias="X-User-Id"),
    user_role: str = Header(None, alias="X-User-Role"),
    is_approved: str = Header(None, alias="X-User-Approved")
):
    """BBS 검사 영상 업로드 및 AI 분석 시작

    영상을 분석하여 BBS 항목별 AI 추천 점수를 반환합니다.
    자동 분석 가능 항목: 1, 2, 4, 7, 11, 14
    """
    verify_approved_therapist(user_id, user_role, is_approved)

    # 환자 확인
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")

    # 파일 저장
    file_ext = os.path.splitext(file.filename)[1]
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    # 분석 상태 초기화
    initial_status = {
        "status": "processing",
        "progress": 0,
        "message": "BBS 검사 AI 분석 준비 중...",
        "current_frame": None
    }
    save_analysis_status(file_id, initial_status)
    print(f"[DEBUG] Initialized BBS analysis status for {file_id}")

    # 백그라운드에서 분석 실행
    background_tasks.add_task(
        analyze_bbs_video_task,
        file_id,
        file_path,
        patient_id
    )

    return {
        "file_id": file_id,
        "message": "업로드 완료. BBS AI 분석이 시작되었습니다.",
        "status_endpoint": f"/api/tests/status/{file_id}"
    }


def run_bbs_analysis_sync(file_id: str, file_path: str):
    """BBS 동기식 분석 (스레드에서 실행됨)"""
    import sys

    # 캐시 무시하고 새로 로드
    modules_to_remove = [key for key in sys.modules.keys() if 'analysis' in key or 'bbs' in key]
    for mod in modules_to_remove:
        del sys.modules[mod]

    from analysis.bbs_analyzer import BBSAnalyzer

    save_analysis_status(file_id, {
        "status": "processing",
        "progress": 5,
        "message": "MediaPipe 모델 로딩 중...",
        "current_frame": None
    })

    analyzer = BBSAnalyzer()

    save_analysis_status(file_id, {
        "status": "processing",
        "progress": 10,
        "message": "BBS 항목 분석 중...",
        "current_frame": None
    })

    current_status = {"progress": 10, "message": "BBS 항목 분석 중..."}

    def update_progress(progress: int):
        # 10-90% 범위로 조정
        adjusted_progress = 10 + int(progress * 0.8)
        current_status["progress"] = adjusted_progress
        if progress < 30:
            current_status["message"] = "포즈 데이터 추출 중..."
        elif progress < 70:
            current_status["message"] = "BBS 항목 분석 중..."
        else:
            current_status["message"] = "점수 계산 중..."

    result = analyzer.analyze_all_items(
        file_path,
        progress_callback=update_progress,
        save_overlay_video=True
    )

    print(f"[DEBUG] BBS analysis complete.")
    return result


async def analyze_bbs_video_task(
    file_id: str,
    file_path: str,
    patient_id: str
):
    """백그라운드 BBS 영상 분석 작업"""
    _set_main_loop()
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            analysis_executor,
            run_bbs_analysis_sync,
            file_id,
            file_path
        )

        save_analysis_status(file_id, {
            "status": "processing",
            "progress": 95,
            "message": "분석 결과 정리 중...",
            "current_frame": None
        })

        # AI 추천 점수 추출
        ai_scores = {}
        for item_key, item_result in result.get("scores", {}).items():
            if item_result.get("score") is not None:
                ai_scores[item_key] = {
                    "score": item_result["score"],
                    "confidence": item_result.get("confidence", 0),
                    "message": item_result.get("message", ""),
                    "details": item_result.get("details", {})
                }

        # 오버레이 영상 경로
        overlay_path = result.get("overlay_video_path")
        overlay_url = None
        if overlay_path and os.path.exists(overlay_path):
            overlay_url = f"/uploads/{os.path.basename(overlay_path)}"

        save_analysis_status(file_id, {
            "status": "completed",
            "progress": 100,
            "message": "BBS AI 분석 완료!",
            "result": {
                "ai_scores": ai_scores,
                "video_duration": result.get("duration", 0),
                "total_frames": result.get("total_frames", 0),
                "video_path": f"/uploads/{os.path.basename(file_path)}",
                "overlay_video_url": overlay_url
            }
        })

    except Exception as e:
        save_analysis_status(file_id, {
            "status": "error",
            "progress": 0,
            "message": f"BBS 분석 중 오류 발생: {str(e)}"
        })
        print(f"[ERROR] BBS video analysis failed: {e}")


@router.post("/{patient_id}/bbs")
async def create_bbs_test(
    patient_id: str,
    data: BBSTestCreate,
    user_id: str = Header(None, alias="X-User-Id"),
    user_role: str = Header(None, alias="X-User-Role"),
    is_approved: str = Header(None, alias="X-User-Approved")
):
    """BBS 검사 결과 저장"""
    verify_approved_therapist(user_id, user_role, is_approved)

    # 환자 확인
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")

    # 점수 검증 (각 항목 0-4점)
    scores_dict = data.scores.dict()
    for key, value in scores_dict.items():
        if not (0 <= value <= 4):
            raise HTTPException(status_code=400, detail=f"{key} 점수는 0-4 사이여야 합니다.")

    # 총점 계산
    total_score = sum(scores_dict.values())

    # 평가 결과
    assessment, assessment_label = calculate_bbs_assessment(total_score)

    # 분석 데이터 구성
    analysis_data = {
        "test_type": "BBS",
        "scores": scores_dict,
        "total_score": total_score,
        "assessment": assessment,
        "assessment_label": assessment_label,
        "notes": data.notes
    }

    # DB에 저장
    test_data = {
        "patient_id": patient_id,
        "test_type": "BBS",
        "walk_time_seconds": total_score,  # BBS는 총점을 여기에 저장
        "walk_speed_mps": 0,  # BBS는 속도 없음
        "analysis_data": json.dumps(analysis_data, ensure_ascii=False)
    }

    result = db.create_test(test_data)
    cache.invalidate_tests(patient_id)
    cache.invalidate_dashboard()

    return {
        "message": "BBS 검사 결과가 저장되었습니다.",
        "test_id": result["id"],
        "total_score": total_score,
        "assessment": assessment,
        "assessment_label": assessment_label
    }


# ===== 재활 추천 및 추세 분석 =====

@router.get("/patient/{patient_id}/recommendations")
async def get_patient_recommendations(patient_id: str):
    """환자 맞춤 재활 추천"""
    from app.services.rehab_recommendations import get_recommendations
    from app.services.fall_risk import calculate_fall_risk_score
    from analysis.disease_profiles import resolve_profile

    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")

    tests = db.get_patient_tests(patient_id)
    if not tests:
        raise HTTPException(status_code=404, detail="검사 기록이 없습니다.")

    latest = parse_analysis_data(tests[0])
    speed = latest.get("walk_speed_mps", 0)
    time_sec = latest.get("walk_time_seconds", 0)

    risk_score = calculate_fall_risk_score(speed, time_sec) if speed > 0 else 50

    disease_profile = resolve_profile(patient.get("diagnosis"))
    profile_name = disease_profile.name

    recommendations = get_recommendations(
        patient=patient,
        latest_tests=[parse_analysis_data(t) for t in tests[:5]],
        disease_profile_name=profile_name,
        risk_score=risk_score,
    )

    return {
        "recommendations": recommendations,
        "disease_profile": profile_name,
        "disease_profile_display": disease_profile.display_name,
        "risk_score": risk_score,
        "risk_level": (
            "normal" if risk_score >= 90 else
            "mild" if risk_score >= 70 else
            "moderate" if risk_score >= 50 else
            "high"
        ),
    }


@router.get("/patient/{patient_id}/trends")
async def get_patient_trends(patient_id: str, test_type: Optional[str] = "10MWT"):
    """환자 검사 추세 분석"""
    from app.services.trend_analysis import analyze_trends

    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")

    tests = db.get_patient_tests(patient_id, test_type=test_type)
    if not tests:
        raise HTTPException(status_code=404, detail="검사 기록이 없습니다.")

    parsed_tests = [parse_analysis_data(t) for t in tests]

    # Get active goal
    goal = None
    goals = db.get_patient_goals(patient_id, status='active')
    if goals:
        for g in goals:
            if g.get('test_type') == test_type:
                goal = g
                break

    result = analyze_trends(parsed_tests, test_type, goal=goal)
    return result


# ===== 자동 비교 리포트 =====

@router.get("/patient/{patient_id}/comparison-report")
async def get_comparison_report(
    patient_id: str,
    test_id: Optional[str] = None,
    prev_id: Optional[str] = None
):
    """검사 간 자동 비교 리포트 생성 (한글 임상 요약문)"""
    from app.services.comparison_report import generate_comparison_report

    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")

    if test_id:
        current_test = db.get_test(test_id)
    else:
        tests = db.get_patient_tests(patient_id)
        if not tests:
            raise HTTPException(status_code=404, detail="검사 기록이 없습니다.")
        current_test = tests[0]

    previous_test = None
    if prev_id:
        previous_test = db.get_test(prev_id)
    else:
        test_type = current_test.get('test_type', '10MWT')
        tests = db.get_patient_tests(patient_id, test_type)
        if len(tests) >= 2:
            # 현재 검사 다음으로 최신인 것
            for t in tests:
                if t['id'] != current_test['id']:
                    previous_test = t
                    break

    # 활성 목표 가져오기
    goals = db.get_patient_goals(patient_id, status='active')
    goal = None
    if goals:
        test_type = current_test.get('test_type', '10MWT')
        for g in goals:
            if g['test_type'] == test_type:
                goal = g
                break

    return generate_comparison_report(current_test, previous_test, patient, goal)


# ===== 보행 영상 하이라이트 클립 =====

@router.get("/{test_id}/video/walking-clip")
async def get_walking_clip(test_id: str):
    """10MWT 보행 구간 클립 추출"""
    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="검사를 찾을 수 없습니다.")
    if not test.get('video_url'):
        raise HTTPException(status_code=404, detail="영상이 없습니다.")

    # analysis_data에서 보행 시작/끝 시간 추출
    analysis = parse_analysis_data(test.get('analysis_data'))
    start_time = analysis.get('walk_start_time')
    end_time = analysis.get('walk_end_time')

    if start_time is None or end_time is None:
        raise HTTPException(status_code=400, detail="보행 구간 정보가 없습니다.")

    video_path = os.path.join(UPLOAD_DIR, os.path.basename(test['video_url']))
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="영상 파일을 찾을 수 없습니다.")

    # 캐싱: 이미 생성된 클립이 있으면 반환
    clip_filename = f"{os.path.splitext(os.path.basename(video_path))[0]}_walking_clip.mp4"
    clip_path = os.path.join(UPLOAD_DIR, clip_filename)

    if not os.path.exists(clip_path):
        from app.services.video_clip_generator import extract_walking_clip
        extract_walking_clip(video_path, start_time, end_time, clip_path)

    return FileResponse(clip_path, media_type="video/mp4", filename=clip_filename)


@router.get("/patient/{patient_id}/video/comparison")
async def get_comparison_video(
    patient_id: str,
    test1_id: str = None,
    test2_id: str = None
):
    """두 검사의 보행 구간 좌우 비교 영상 생성"""
    if not test1_id or not test2_id:
        raise HTTPException(status_code=400, detail="test1_id와 test2_id가 필요합니다.")

    test1 = db.get_test(test1_id)
    test2 = db.get_test(test2_id)
    if not test1 or not test2:
        raise HTTPException(status_code=404, detail="검사를 찾을 수 없습니다.")

    def _get_video_times(test):
        analysis = parse_analysis_data(test.get('analysis_data'))
        video_path = os.path.join(UPLOAD_DIR, os.path.basename(test['video_url']))
        start = analysis.get('walk_start_time', 0)
        end = analysis.get('walk_end_time', 10)
        return video_path, start, end

    v1_path, s1, e1 = _get_video_times(test1)
    v2_path, s2, e2 = _get_video_times(test2)

    if not os.path.exists(v1_path) or not os.path.exists(v2_path):
        raise HTTPException(status_code=404, detail="영상 파일을 찾을 수 없습니다.")

    # 캐싱
    comp_filename = f"comparison_{test1_id[:8]}_{test2_id[:8]}.mp4"
    comp_path = os.path.join(UPLOAD_DIR, comp_filename)

    if not os.path.exists(comp_path):
        from app.services.video_clip_generator import generate_side_by_side_clip
        generate_side_by_side_clip(v1_path, s1, e1, v2_path, s2, e2, comp_path)

    return FileResponse(comp_path, media_type="video/mp4", filename=comp_filename)
