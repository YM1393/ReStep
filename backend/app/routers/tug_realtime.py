"""
실시간 TUG 검사 WebSocket 엔드포인트
- 브라우저에서 MediaPipe JS로 추출한 랜드마크를 수신
- 실시간 단계 감지 (기립→보행→회전→복귀→착석)
- 검사 완료 시 전체 분석 및 DB 저장
"""
import json
import math
import time
import uuid
import numpy as np
from typing import List, Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# ─── MediaPipe 랜드마크 인덱스 (33점 전체 기준) ───
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_FOOT_INDEX = 31
RIGHT_FOOT_INDEX = 32

# ─── 임계값 (tug_analyzer.py와 동일) ───
SITTING_ANGLE_THRESHOLD = 120
STANDING_ANGLE_THRESHOLD = 160
UPRIGHT_TORSO_THRESHOLD = 75

PHASE_LABELS = {
    "stand_up": "기립",
    "walk_out": "보행",
    "turn": "회전",
    "walk_back": "복귀",
    "sit_down": "착석",
}


def _calculate_angle(p1: List[float], p2: List[float], p3: List[float]) -> float:
    """세 점으로 각도 계산 (p2가 꼭지점). 정규화 좌표에서도 동일 작동."""
    v1 = np.array(p1[:2]) - np.array(p2[:2])
    v2 = np.array(p3[:2]) - np.array(p2[:2])
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 < 1e-6 or norm2 < 1e-6:
        return 0
    cos_angle = np.dot(v1, v2) / (norm1 * norm2 + 1e-6)
    return math.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))


def _extract_frame_data_from_landmarks(landmarks: List[List[float]], timestamp: float) -> Optional[Dict]:
    """정규화 좌표(0-1) 랜드마크에서 프레임 데이터 추출.
    tug_analyzer.py _extract_side_frame_data() 로직의 정규화 좌표 버전."""
    if len(landmarks) < 33:
        return None

    lh = landmarks[LEFT_HIP]
    rh = landmarks[RIGHT_HIP]
    lk = landmarks[LEFT_KNEE]
    rk = landmarks[RIGHT_KNEE]
    la = landmarks[LEFT_ANKLE]
    ra = landmarks[RIGHT_ANKLE]
    ls = landmarks[LEFT_SHOULDER]
    rs = landmarks[RIGHT_SHOULDER]
    lw = landmarks[LEFT_WRIST]
    rw = landmarks[RIGHT_WRIST]

    # 다리 각도
    left_leg = _calculate_angle(lh, lk, la)
    right_leg = _calculate_angle(rh, rk, ra)
    if left_leg > 0 and right_leg > 0:
        avg_leg = (left_leg + right_leg) / 2
    else:
        avg_leg = max(left_leg, right_leg)

    # 엉덩이 높이 (정규화: y가 0=상단, 1=하단이므로 1-y)
    hip_y_avg = (lh[1] + rh[1]) / 2
    hip_height = 1 - hip_y_avg

    # 어깨 방향 (회전 감지)
    shoulder_direction = math.atan2(
        rs[1] - ls[1],
        rs[0] - ls[0]
    )

    # 상체 수직도
    hip_center = [(lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2]
    shoulder_center = [(ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2]
    dx = shoulder_center[0] - hip_center[0]
    dy = hip_center[1] - shoulder_center[1]  # y 반전
    torso_angle = abs(math.degrees(math.atan2(dy, dx))) if abs(dx) + abs(dy) > 0.01 else 90

    # 손목-무릎 거리
    knee_center = np.array([(lk[0] + rk[0]) / 2, (lk[1] + rk[1]) / 2])
    wrist_knee = 1.0
    for w in [lw, rw]:
        d = np.linalg.norm(np.array(w[:2]) - knee_center)
        wrist_knee = min(wrist_knee, d)

    # 발목 x좌표
    ankle_x = (la[0] + ra[0]) / 2

    # 머리 높이
    head_y = (ls[1] + rs[1]) / 2  # 어깨 y 사용

    return {
        "time": timestamp,
        "leg_angle": avg_leg,
        "hip_y": hip_y_avg,
        "hip_height_normalized": hip_height,
        "shoulder_direction": shoulder_direction,
        "head_y": head_y,
        "torso_angle": torso_angle,
        "wrist_knee_distance": wrist_knee,
        "ankle_x": ankle_x,
        "left_ankle_y": la[1],
        "right_ankle_y": ra[1],
        "left_knee_angle": _calculate_angle(lh, lk, la),
        "right_knee_angle": _calculate_angle(rh, rk, ra),
        "left_hip_angle": _calculate_angle(ls, lh, lk),
        "right_hip_angle": _calculate_angle(rs, rh, rk),
    }


class RealtimeTUGSession:
    """실시간 TUG 검사 세션 상태 관리"""

    def __init__(self, patient_id: str, user_id: str):
        self.patient_id = patient_id
        self.user_id = user_id
        self.frame_data: List[Dict] = []
        self.pose_3d_frames: List[Dict] = []
        self.start_time: Optional[float] = None

        # 단계 상태머신
        self.current_phase = "stand_up"
        self.standing_detected = False
        self.turn_detected = False
        self.sitting_started = False
        self.phase_transitions: List[Dict] = [
            {"phase": "stand_up", "start": 0.0}
        ]

        # 회전 감지용
        self._shoulder_history: List[float] = []
        self._shoulder_window = 15  # 15프레임 윈도우

    def process_frame(self, landmarks: List[List[float]], timestamp: float,
                      world_landmarks: Optional[List[List[float]]] = None) -> Dict:
        """프레임 처리 후 현재 상태 반환"""
        if self.start_time is None:
            self.start_time = timestamp

        elapsed = timestamp - self.start_time

        # 프레임 데이터 추출
        fd = _extract_frame_data_from_landmarks(landmarks, elapsed)
        if fd is None:
            return {
                "type": "phase_update",
                "current_phase": self.current_phase,
                "phase_label": PHASE_LABELS.get(self.current_phase, "-"),
                "elapsed_time": round(elapsed, 1),
            }

        self.frame_data.append(fd)

        # 3D 월드 랜드마크 저장 (매 3프레임)
        if world_landmarks and len(self.frame_data) % 3 == 0:
            self.pose_3d_frames.append({
                "time": round(elapsed, 3),
                "phase": self.current_phase,
                "landmarks": [
                    [round(world_landmarks[i][0], 4),
                     round(world_landmarks[i][1], 4),
                     round(world_landmarks[i][2], 4)]
                    for i in range(11, min(33, len(world_landmarks)))
                ]
            })

        # 단계 감지
        prev_phase = self.current_phase
        self._update_phase(fd)

        result = {
            "type": "phase_update",
            "current_phase": self.current_phase,
            "phase_label": PHASE_LABELS.get(self.current_phase, "-"),
            "elapsed_time": round(elapsed, 1),
            "leg_angle": round(fd["leg_angle"], 1),
            "hip_height": round(fd["hip_height_normalized"], 2),
        }

        # 단계 전환 이벤트
        if prev_phase != self.current_phase:
            # 이전 단계 종료
            if self.phase_transitions:
                self.phase_transitions[-1]["end"] = round(elapsed, 2)
            # 새 단계 시작
            self.phase_transitions.append({
                "phase": self.current_phase,
                "start": round(elapsed, 2),
            })

            result = {
                "type": "phase_transition",
                "from_phase": prev_phase,
                "to_phase": self.current_phase,
                "transition_time": round(elapsed, 2),
                "current_phase": self.current_phase,
                "phase_label": PHASE_LABELS.get(self.current_phase, "-"),
                "elapsed_time": round(elapsed, 1),
                "transitions": self.phase_transitions,
            }

        return result

    def _update_phase(self, fd: Dict):
        """단계 상태머신 업데이트 (tug_analyzer._detect_current_phase_realtime 기반)"""
        leg_angle = fd["leg_angle"]
        torso_angle = fd.get("torso_angle", 90)
        shoulder_dir = fd["shoulder_direction"]

        # 어깨 방향 히스토리 (회전 감지용)
        self._shoulder_history.append(shoulder_dir)
        if len(self._shoulder_history) > self._shoulder_window:
            self._shoulder_history.pop(0)

        # 1. 기립 감지
        if not self.standing_detected:
            if leg_angle >= STANDING_ANGLE_THRESHOLD and torso_angle >= UPRIGHT_TORSO_THRESHOLD:
                self.standing_detected = True
                self.current_phase = "walk_out"
            else:
                self.current_phase = "stand_up"
            return

        # 2. 회전 감지 (어깨 방향 변화)
        if self.standing_detected and not self.turn_detected:
            if len(self._shoulder_history) >= self._shoulder_window:
                dir_change = abs(self._shoulder_history[-1] - self._shoulder_history[0])
                if dir_change > 0.5:  # ~28도 이상 변화
                    self.turn_detected = True
                    self.current_phase = "turn"
                    return
            self.current_phase = "walk_out"
            return

        # 3. 회전 후 → 복귀 또는 착석
        if self.turn_detected and not self.sitting_started:
            # 착석 시작 감지
            if leg_angle < STANDING_ANGLE_THRESHOLD:
                self.sitting_started = True
                self.current_phase = "sit_down"
                return
            self.current_phase = "walk_back"
            return

        # 4. 착석 중
        if self.sitting_started:
            self.current_phase = "sit_down"

    def finalize(self) -> Dict:
        """검사 완료 - 전체 분석 및 결과 반환"""
        if not self.frame_data:
            return {"error": "프레임 데이터 없음"}

        # 마지막 전환 종료
        if self.phase_transitions:
            self.phase_transitions[-1]["end"] = self.frame_data[-1]["time"]

        total_time = self.frame_data[-1]["time"] - self.frame_data[0]["time"]

        # 전체 단계 감지 (TUGAnalyzer 사용)
        try:
            from analysis.tug_analyzer import TUGAnalyzer
            analyzer = TUGAnalyzer()
            phases = analyzer._detect_tug_phases(self.frame_data, 30.0)
        except Exception as e:
            print(f"[TUG Realtime] Full phase detection failed: {e}, using realtime transitions")
            phases = self._build_phases_from_transitions(total_time)

        # 평가
        if total_time < 10:
            assessment = "normal"
        elif total_time < 20:
            assessment = "good"
        elif total_time < 30:
            assessment = "caution"
        else:
            assessment = "risk"

        walk_speed = 6.0 / total_time if total_time > 0 else 0

        # 3D 프레임에 최종 단계 어노테이션
        self._annotate_3d_frames(phases)

        result = {
            "test_type": "TUG",
            "total_time_seconds": round(total_time, 2),
            "walk_speed_mps": round(walk_speed, 2),
            "assessment": assessment,
            "phases": phases,
            "pose_3d_frames": self.pose_3d_frames if self.pose_3d_frames else None,
            "realtime": True,
        }

        # DB 저장
        try:
            from app.models.db_factory import db
            test_record = db.create_test({
                "patient_id": self.patient_id,
                "test_type": "TUG",
                "walk_time_seconds": round(total_time, 2),
                "walk_speed_mps": round(walk_speed, 2),
                "analysis_data": json.dumps(result, ensure_ascii=False),
            })
            result["test_id"] = test_record.get("id")
        except Exception as e:
            print(f"[TUG Realtime] DB save failed: {e}")
            result["test_id"] = str(uuid.uuid4())

        return result

    def _build_phases_from_transitions(self, total_time: float) -> Dict:
        """실시간 전환 기록에서 단계 딕셔너리 생성 (fallback)"""
        phases = {}
        for t in self.phase_transitions:
            name = t["phase"]
            start = t.get("start", 0)
            end = t.get("end", total_time)
            phases[name] = {
                "start_time": round(start, 2),
                "end_time": round(end, 2),
                "duration": round(end - start, 2),
            }

        # 누락 단계 기본값
        phase_order = ["stand_up", "walk_out", "turn", "walk_back", "sit_down"]
        for p in phase_order:
            if p not in phases:
                phases[p] = {"start_time": 0, "end_time": 0, "duration": 0}

        return phases

    def _annotate_3d_frames(self, phases: Dict):
        """3D 프레임에 최종 단계 어노테이션 적용"""
        phase_order = ["stand_up", "walk_out", "turn", "walk_back", "sit_down"]
        for frame in self.pose_3d_frames:
            t = frame["time"]
            frame["phase"] = "unknown"
            for pname in phase_order:
                p = phases.get(pname, {})
                st = p.get("start_time", 0)
                et = p.get("end_time", 0)
                if st <= t <= et:
                    frame["phase"] = pname
                    break


# ─── 세션 관리 ───
_sessions: Dict[str, RealtimeTUGSession] = {}


@router.websocket("/ws/tug-realtime/{client_id}")
async def tug_realtime_websocket(websocket: WebSocket, client_id: str):
    await websocket.accept()
    session: Optional[RealtimeTUGSession] = None
    print(f"[TUG Realtime] Client connected: {client_id}")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "start_test":
                patient_id = msg.get("patient_id", "")
                user_id = msg.get("user_id", "")
                session = RealtimeTUGSession(patient_id, user_id)
                _sessions[client_id] = session
                await websocket.send_json({
                    "type": "test_started",
                    "message": "실시간 TUG 검사가 시작되었습니다.",
                })
                print(f"[TUG Realtime] Test started for patient {patient_id}")

            elif msg_type == "frame_data":
                if session is None:
                    await websocket.send_json({"type": "error", "message": "검사가 시작되지 않았습니다."})
                    continue

                landmarks = msg.get("landmarks", [])
                timestamp = msg.get("timestamp", 0)
                world_landmarks = msg.get("world_landmarks")

                result = session.process_frame(landmarks, timestamp, world_landmarks)
                await websocket.send_json(result)

            elif msg_type == "stop_test":
                if session is None:
                    await websocket.send_json({"type": "error", "message": "검사가 시작되지 않았습니다."})
                    continue

                result = session.finalize()
                await websocket.send_json({
                    "type": "test_completed",
                    **result,
                })
                print(f"[TUG Realtime] Test completed: {result.get('total_time_seconds', 0)}s")
                _sessions.pop(client_id, None)
                session = None

    except WebSocketDisconnect:
        print(f"[TUG Realtime] Client disconnected: {client_id}")
    except Exception as e:
        print(f"[TUG Realtime] Error for {client_id}: {e}")
    finally:
        _sessions.pop(client_id, None)
