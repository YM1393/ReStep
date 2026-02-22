import os
import cv2
import numpy as np
import math
import base64
from typing import Dict, List, Tuple, Optional, Set

import mediapipe as mp
from analysis.stopwatch_overlay import add_tug_stopwatch


# 얼굴 랜드마크 제외한 몸체 연결선 정의 (상반신 + 하반신만)
# MediaPipe Pose 랜드마크: 0-10은 얼굴, 11-32는 몸체
BODY_CONNECTIONS: Set[Tuple[int, int]] = {
    # 상반신 (어깨, 팔꿈치, 손목, 손가락)
    (11, 12),  # 어깨-어깨
    (11, 13),  # 왼쪽 어깨-팔꿈치
    (13, 15),  # 왼쪽 팔꿈치-손목
    (15, 17),  # 왼쪽 손목-새끼손가락
    (15, 19),  # 왼쪽 손목-검지
    (15, 21),  # 왼쪽 손목-엄지
    (17, 19),  # 왼쪽 새끼-검지
    (12, 14),  # 오른쪽 어깨-팔꿈치
    (14, 16),  # 오른쪽 팔꿈치-손목
    (16, 18),  # 오른쪽 손목-새끼손가락
    (16, 20),  # 오른쪽 손목-검지
    (16, 22),  # 오른쪽 손목-엄지
    (18, 20),  # 오른쪽 새끼-검지
    # 몸통
    (11, 23),  # 왼쪽 어깨-엉덩이
    (12, 24),  # 오른쪽 어깨-엉덩이
    (23, 24),  # 엉덩이-엉덩이
    # 하반신 (엉덩이, 무릎, 발목, 발)
    (23, 25),  # 왼쪽 엉덩이-무릎
    (25, 27),  # 왼쪽 무릎-발목
    (27, 29),  # 왼쪽 발목-발뒤꿈치
    (27, 31),  # 왼쪽 발목-발가락
    (29, 31),  # 왼쪽 발뒤꿈치-발가락
    (24, 26),  # 오른쪽 엉덩이-무릎
    (26, 28),  # 오른쪽 무릎-발목
    (28, 30),  # 오른쪽 발목-발뒤꿈치
    (28, 32),  # 오른쪽 발목-발가락
    (30, 32),  # 오른쪽 발뒤꿈치-발가락
}

# 몸체 랜드마크 인덱스 (11-32, 얼굴 제외)
BODY_LANDMARKS: Set[int] = set(range(11, 33))


def draw_body_landmarks(
    image: np.ndarray,
    landmarks,
    thickness: int = 4,
    circle_radius: int = 8
) -> np.ndarray:
    """
    얼굴을 제외한 몸체 랜드마크만 그리기 (좌/우 색상 구분)

    색상 구분:
    - 왼쪽 (LEFT): 파란색 계열 (BGR: 255, 150, 0)
    - 오른쪽 (RIGHT): 주황색 계열 (BGR: 0, 128, 255)
    - 중앙 연결선: 흰색 (BGR: 255, 255, 255)

    Args:
        image: 그릴 이미지
        landmarks: MediaPipe pose landmarks
        thickness: 선 두께
        circle_radius: 랜드마크 점 반지름

    Returns:
        랜드마크가 그려진 이미지
    """
    if landmarks is None:
        return image

    # 색상 정의 (BGR 형식)
    LEFT_COLOR = (255, 150, 0)      # 파란색 계열 (시안)
    RIGHT_COLOR = (0, 128, 255)     # 주황색 계열
    CENTER_COLOR = (200, 200, 200)  # 밝은 회색 (중앙 연결선)

    # 왼쪽 랜드마크 인덱스 (홀수 번호)
    LEFT_LANDMARKS = {11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31}
    # 오른쪽 랜드마크 인덱스 (짝수 번호)
    RIGHT_LANDMARKS = {12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32}

    # 중앙 연결선 (좌-우 연결)
    CENTER_CONNECTIONS = {(11, 12), (23, 24)}

    h, w = image.shape[:2]

    # 랜드마크 좌표 계산
    landmark_points = {}
    for idx in BODY_LANDMARKS:
        if idx < len(landmarks.landmark):
            lm = landmarks.landmark[idx]
            if lm.visibility > 0.2:  # 가시성이 20% 이상인 경우만
                x = int(lm.x * w)
                y = int(lm.y * h)
                landmark_points[idx] = (x, y)

    # 연결선 그리기 (색상 구분)
    for connection in BODY_CONNECTIONS:
        start_idx, end_idx = connection
        if start_idx in landmark_points and end_idx in landmark_points:
            # 연결선 색상 결정
            if connection in CENTER_CONNECTIONS:
                color = CENTER_COLOR
            elif start_idx in LEFT_LANDMARKS and end_idx in LEFT_LANDMARKS:
                color = LEFT_COLOR
            elif start_idx in RIGHT_LANDMARKS and end_idx in RIGHT_LANDMARKS:
                color = RIGHT_COLOR
            elif start_idx in LEFT_LANDMARKS or end_idx in LEFT_LANDMARKS:
                color = LEFT_COLOR
            else:
                color = RIGHT_COLOR

            cv2.line(
                image,
                landmark_points[start_idx],
                landmark_points[end_idx],
                color,
                thickness
            )

    # 랜드마크 점 그리기 (색상 구분)
    for idx, point in landmark_points.items():
        if idx in LEFT_LANDMARKS:
            color = LEFT_COLOR
        elif idx in RIGHT_LANDMARKS:
            color = RIGHT_COLOR
        else:
            color = CENTER_COLOR

        cv2.circle(image, point, circle_radius, color, -1)
        cv2.circle(image, point, circle_radius, (255, 255, 255), 1)  # 흰색 테두리

    return image


class TUGAnalyzer:
    """
    MediaPipe Pose Heavy를 사용한 TUG (Timed Up and Go) 검사 분석기

    TUG 검사:
    1. 의자에서 일어나기
    2. 3m 걷기
    3. 돌아서기
    4. 3m 걸어 돌아오기
    5. 의자에 앉기

    평가 기준:
    - < 10초: 정상 (normal)
    - 10-20초: 양호 (good)
    - 20-30초: 주의 필요 (caution)
    - > 30초: 낙상 위험 (risk)
    """

    MODEL_COMPLEXITY = 2  # Heavy 모델
    WALK_DISTANCE_M = 3.0  # TUG는 3m 왕복

    # MediaPipe Pose 키포인트 인덱스
    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32

    # 자세 판단 임계값
    SITTING_ANGLE_THRESHOLD = 120  # 이 각도 이하면 앉은 자세
    STANDING_ANGLE_THRESHOLD = 160  # 이 각도 이상이면 선 자세
    UPRIGHT_TORSO_THRESHOLD = 75   # 상체가 이 각도 이상이면 직립 (90도가 완전 수직)

    def __init__(self, disease_profile=None):
        """MediaPipe Pose Heavy 모델 초기화"""
        print(f"Loading MediaPipe Pose Heavy model for TUG (model_complexity={self.MODEL_COMPLEXITY})")
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=self.MODEL_COMPLEXITY,
            smooth_landmarks=True,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.model_name = f"MediaPipe Pose Heavy (complexity={self.MODEL_COMPLEXITY})"

        # 질환별 프로파일 적용
        self._disease_profile = disease_profile
        if disease_profile is not None:
            tp = disease_profile.tug
            self.SITTING_ANGLE_THRESHOLD = tp.sitting_angle_threshold
            self.STANDING_ANGLE_THRESHOLD = tp.standing_angle_threshold
            self.UPRIGHT_TORSO_THRESHOLD = tp.upright_torso_threshold
            self.HAND_SUPPORT_THRESHOLD = tp.hand_support_threshold
            self.DEVIATION_THRESHOLD = tp.deviation_threshold
            self.TURN_DEVIATION_THRESHOLD = tp.turn_deviation_threshold
            self.MIN_FACING_RATIO = tp.min_facing_ratio
            print(f"[TUG] Disease profile applied: {disease_profile.display_name} ({disease_profile.name})")

    def analyze_dual_video(
        self,
        side_video_path: str,
        front_video_path: str,
        patient_height_cm: float,
        progress_callback=None,
        frame_callback=None,
        phase_callback=None,
        save_overlay_video: bool = True,
        file_id: str = None
    ) -> Dict:
        """
        두 영상으로 TUG 검사 분석 (측면 + 정면)

        Args:
            side_video_path: 측면 영상 경로 (보행 분석, 기립/착석 속도)
            front_video_path: 정면 영상 경로 (어깨/골반 기울기)
            patient_height_cm: 환자의 실제 키 (cm)
            progress_callback: 진행률 콜백 함수
            frame_callback: 프레임 콜백 함수
            phase_callback: 단계 콜백 함수 (현재 단계 정보 전달)
            save_overlay_video: 포즈 오버레이 영상 저장 여부

        Returns:
            분석 결과 딕셔너리
        """
        # 진행률 직접 상태 파일에 기록 (tests.py의 update_progress가 동작하지 않는 문제 우회)
        import json as _json
        import os as _os
        import glob as _glob

        _status_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'uploads', 'status')
        _resolved_fid = [file_id]  # file_id가 전달되면 사용, 아니면 자동 탐색

        # file_id가 없으면 상태 디렉토리에서 현재 processing 중인 파일을 찾음
        if not _resolved_fid[0]:
            try:
                candidates = sorted(
                    _glob.glob(_os.path.join(_status_dir, '*.json')),
                    key=lambda x: _os.path.getmtime(x), reverse=True
                )
                for c in candidates[:5]:
                    with open(c, 'r', encoding='utf-8') as f:
                        data = _json.load(f)
                    if data.get('status') == 'processing' and data.get('progress', 0) <= 10:
                        _resolved_fid[0] = _os.path.basename(c).replace('.json', '')
                        print(f"[TUG] Auto-detected file_id: {_resolved_fid[0]}")
                        break
            except Exception as e:
                print(f"[TUG] file_id auto-detect failed: {e}")

        def _direct_progress(progress):
            fid = _resolved_fid[0]
            if fid:
                msg = "측면 영상 분석 중..." if progress < 50 else ("정면 영상 분석 중..." if progress < 90 else "결과 통합 중...")
                try:
                    with open(_os.path.join(_status_dir, f'{fid}.json'), 'w', encoding='utf-8') as f:
                        _json.dump({"status": "processing", "progress": progress, "message": msg, "current_frame": None}, f, ensure_ascii=False)
                except:
                    pass
            if progress_callback:
                try:
                    progress_callback(progress)
                except:
                    pass

        # 1. 측면 영상 분석 (보행 + 기립/착석)
        _direct_progress(5)
        side_result = self._analyze_side_video(
            side_video_path,
            patient_height_cm,
            progress_callback=lambda p: _direct_progress(5 + int(p * 0.45)),
            frame_callback=frame_callback,
            phase_callback=phase_callback,
            save_overlay_video=save_overlay_video
        )

        # 2. 정면 영상 분석 (기울기)
        _direct_progress(55)
        front_result = self._analyze_front_video(
            front_video_path,
            patient_height_cm,
            progress_callback=lambda p: _direct_progress(55 + int(p * 0.35)),
            frame_callback=frame_callback,
            save_overlay_video=save_overlay_video,
            phases=side_result.get('phases')
        )

        # 3. 결과 통합
        _direct_progress(90)
        return self._merge_results(side_result, front_result, patient_height_cm)

    def _analyze_side_video(
        self,
        video_path: str,
        patient_height_cm: float,
        progress_callback=None,
        frame_callback=None,
        phase_callback=None,
        save_overlay_video: bool = True
    ) -> Dict:
        """측면 영상 분석 - 보행 및 기립/착석 속도 측정"""
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"측면 영상을 열 수 없습니다: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = int(fps * 20) if fps > 0 else 600
            print(f"[TUG] Estimated total_frames={total_frames} (side, original was 0)")
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 오버레이 영상 저장 설정
        overlay_video_path = None
        video_writer = None
        if save_overlay_video:
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            overlay_video_path = os.path.join(
                os.path.dirname(video_path),
                f"{base_name}_overlay.mp4"
            )
            # H.264 코덱 사용 (브라우저 호환성)
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            video_writer = cv2.VideoWriter(
                overlay_video_path, fourcc, fps,
                (frame_width, frame_height)
            )
            if not video_writer.isOpened():
                # avc1 실패시 mp4v로 폴백
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(
                    overlay_video_path, fourcc, fps,
                    (frame_width, frame_height)
                )
            print(f"[TUG SIDE] Saving overlay video to: {overlay_video_path}")

        frame_data = []
        pose_3d_frames = []  # 3D 월드 랜드마크 (매 3프레임)
        frame_count = 0

        # 실시간 단계 감지용 상태
        current_phase = "stand_up"
        standing_detected = False
        turn_detected = False
        sitting_started = False

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)
            current_time = frame_count / fps

            # 포즈 오버레이 프레임 생성 (얼굴 제외, 몸체만)
            annotated_frame = frame.copy()
            if results.pose_landmarks is not None:
                draw_body_landmarks(annotated_frame, results.pose_landmarks)

            # 오버레이 영상 저장
            if video_writer is not None:
                video_writer.write(annotated_frame)

            # 실시간 미리보기 콜백 (3프레임마다)
            if frame_callback and frame_count % 3 == 0:
                try:
                    frame_callback(annotated_frame)
                except Exception as e:
                    print(f"[TUG SIDE] Frame callback failed: {e}")

            if results.pose_landmarks is not None:
                h, w = frame.shape[:2]
                keypoints = np.array([
                    [lm.x * w, lm.y * h] for lm in results.pose_landmarks.landmark
                ])
                data = self._extract_side_frame_data(keypoints, frame_count, fps, h)
                if data:
                    frame_data.append(data)

                # 3D 월드 랜드마크 추출 (매 3프레임, 몸체만)
                if results.pose_world_landmarks and frame_count % 3 == 0:
                    world_lms = results.pose_world_landmarks.landmark
                    pose_3d_frames.append({
                        "time": round(frame_count / fps, 3),
                        "landmarks": [
                            [round(world_lms[i].x, 4), round(world_lms[i].y, 4), round(world_lms[i].z, 4)]
                            for i in range(11, 33)
                        ]
                    })

                    # 실시간 단계 감지
                    leg_angle = data.get('leg_angle', 0)
                    shoulder_direction = data.get('shoulder_direction', 0)

                    new_phase = self._detect_current_phase_realtime(
                        leg_angle, shoulder_direction, current_time,
                        standing_detected, turn_detected, sitting_started,
                        len(frame_data)
                    )

                    # 상태 업데이트
                    if leg_angle >= self.STANDING_ANGLE_THRESHOLD:
                        standing_detected = True

                    if standing_detected and not turn_detected:
                        if len(frame_data) > 10:
                            recent_directions = [f['shoulder_direction'] for f in frame_data[-10:]]
                            if len(recent_directions) >= 10:
                                direction_change = abs(recent_directions[-1] - recent_directions[0])
                                if direction_change > 0.5:
                                    turn_detected = True

                    if turn_detected and leg_angle < self.STANDING_ANGLE_THRESHOLD:
                        sitting_started = True

                    if new_phase != current_phase:
                        current_phase = new_phase
                        if phase_callback:
                            phase_callback({
                                "phase": current_phase,
                                "phase_label": self._get_phase_label(current_phase),
                                "time": current_time
                            })

            frame_count += 1

            if progress_callback and total_frames > 0:
                progress = int((frame_count / total_frames) * 100)
                progress_callback(progress)

        cap.release()

        # 오버레이 비디오 저장 완료
        if video_writer is not None:
            video_writer.release()
            print(f"[TUG SIDE] Overlay video saved: {overlay_video_path}")

        if len(frame_data) < 10:
            raise ValueError("측면 영상에서 충분한 포즈 데이터를 감지하지 못했습니다.")

        # TUG 단계 감지
        phases = self._detect_tug_phases(frame_data, fps)

        # 오버레이 영상에 스톱워치 UI 추가 (후처리)
        if overlay_video_path and os.path.exists(overlay_video_path):
            print(f"[TUG SIDE] Adding stopwatch overlay...")
            add_tug_stopwatch(overlay_video_path, phases, fps, frame_width, frame_height)

        # 기립/착석 분석
        stand_up_metrics = self._calculate_stand_up_metrics(frame_data, phases, fps)
        sit_down_metrics = self._calculate_sit_down_metrics(frame_data, phases, fps)

        total_time = phases['total_duration']
        assessment = self._get_assessment(total_time)

        # 단계 전환 시점 프레임 캡처
        print(f"[TUG SIDE] Capturing phase transition frames...")
        phase_frames = self._capture_phase_frames(video_path, phases, fps)
        print(f"[TUG SIDE] Captured {len(phase_frames)} phase frames")

        # 단계별 클립 생성
        print(f"[TUG SIDE] Capturing phase clips...")
        phase_clips = self._capture_phase_clips(video_path, phases, fps)
        print(f"[TUG SIDE] Captured {len(phase_clips)} phase clips")

        # 반응 시간 측정
        reaction_time = self._calculate_reaction_time(frame_data, fps)
        print(f"[TUG SIDE] Reaction time: {reaction_time.get('reaction_time', 0):.3f}s")

        # 첫 걸음 시간 측정
        first_step_time = self._calculate_first_step_time(frame_data, phases, fps)
        print(f"[TUG SIDE] First step time: {first_step_time.get('time_to_first_step', 0):.3f}s")

        # 질환별 추가 임상 변수 계산
        clinical_variables = {}
        if self._disease_profile is not None:
            clinical_variables = self._calculate_clinical_variables(frame_data, phases, fps)
            print(f"[TUG SIDE] Clinical variables calculated: {list(clinical_variables.keys())}")

        return {
            "fps": fps,
            "total_frames": total_frames,
            "frames_analyzed": len(frame_data),
            "total_time_seconds": total_time,
            "assessment": assessment,
            "phases": phases,
            "stand_up": stand_up_metrics,
            "sit_down": sit_down_metrics,
            "reaction_time": reaction_time,
            "first_step_time": first_step_time,
            "frame_data": frame_data,
            "phase_frames": phase_frames,
            "phase_clips": phase_clips,
            "overlay_video_path": overlay_video_path,
            "clinical_variables": clinical_variables,
            "pose_3d_frames": pose_3d_frames if pose_3d_frames else None
        }

    def _extract_side_frame_data(self, keypoints: np.ndarray, frame_num: int, fps: float, frame_height: int) -> Optional[Dict]:
        """측면 영상에서 프레임 데이터 추출 (기립/착석 분석용)"""
        if keypoints is None or keypoints.size == 0 or len(keypoints) < 33:
            return None

        left_hip = keypoints[self.LEFT_HIP]
        right_hip = keypoints[self.RIGHT_HIP]
        left_knee = keypoints[self.LEFT_KNEE]
        right_knee = keypoints[self.RIGHT_KNEE]
        left_ankle = keypoints[self.LEFT_ANKLE]
        right_ankle = keypoints[self.RIGHT_ANKLE]
        left_shoulder = keypoints[self.LEFT_SHOULDER]
        right_shoulder = keypoints[self.RIGHT_SHOULDER]
        left_wrist = keypoints[self.LEFT_WRIST]
        right_wrist = keypoints[self.RIGHT_WRIST]
        nose = keypoints[self.NOSE]

        # 다리 각도 계산
        left_leg_angle = self._calculate_angle(left_hip, left_knee, left_ankle)
        right_leg_angle = self._calculate_angle(right_hip, right_knee, right_ankle)
        avg_leg_angle = (left_leg_angle + right_leg_angle) / 2 if left_leg_angle > 0 and right_leg_angle > 0 else max(left_leg_angle, right_leg_angle)

        # 엉덩이 높이 (프레임 하단 기준, 높을수록 선 자세)
        hip_y = (left_hip[1] + right_hip[1]) / 2 if left_hip[1] > 0 and right_hip[1] > 0 else max(left_hip[1], right_hip[1])
        # 정규화된 엉덩이 높이 (0~1, 1이 위쪽)
        hip_height_normalized = 1 - (hip_y / frame_height) if frame_height > 0 else 0

        # 어깨 방향 (회전 감지용)
        shoulder_direction = 0.0
        if left_shoulder[0] > 0 and right_shoulder[0] > 0:
            shoulder_direction = math.atan2(
                right_shoulder[1] - left_shoulder[1],
                right_shoulder[0] - left_shoulder[0]
            )

        # 상체(몸통) 수직도 계산 - 엉덩이와 어깨 사이의 각도
        # 수직일 때 90도에 가까움 (측면에서 볼 때 어깨가 엉덩이 바로 위에 있음)
        torso_angle = 0.0
        hip_center = np.array([(left_hip[0] + right_hip[0]) / 2, (left_hip[1] + right_hip[1]) / 2])
        shoulder_center = np.array([(left_shoulder[0] + right_shoulder[0]) / 2, (left_shoulder[1] + right_shoulder[1]) / 2])
        if hip_center[0] > 0 and shoulder_center[0] > 0:
            # 수평 기준으로 몸통 각도 계산 (수직이면 약 90도)
            dx = shoulder_center[0] - hip_center[0]
            dy = hip_center[1] - shoulder_center[1]  # y는 아래가 양수이므로 반전
            torso_angle = abs(math.degrees(math.atan2(dy, dx)))  # 0~180도

        # 손목-무릎 거리 계산 (손으로 무릎을 짚는지 감지)
        # 프레임 높이로 정규화하여 상대적 거리 계산
        wrist_knee_distance = float('inf')
        knee_center = np.array([(left_knee[0] + right_knee[0]) / 2, (left_knee[1] + right_knee[1]) / 2])

        # 왼쪽 손목-무릎 거리
        if left_wrist[0] > 0 and left_wrist[1] > 0:
            left_dist = np.linalg.norm(left_wrist - knee_center)
            wrist_knee_distance = min(wrist_knee_distance, left_dist)

        # 오른쪽 손목-무릎 거리
        if right_wrist[0] > 0 and right_wrist[1] > 0:
            right_dist = np.linalg.norm(right_wrist - knee_center)
            wrist_knee_distance = min(wrist_knee_distance, right_dist)

        # 정규화 (프레임 높이 기준)
        wrist_knee_normalized = wrist_knee_distance / frame_height if frame_height > 0 and wrist_knee_distance != float('inf') else 1.0

        # 발목 x좌표 (첫 걸음 시간 감지용)
        ankle_x_avg = 0.0
        if left_ankle[0] > 0 and right_ankle[0] > 0:
            ankle_x_avg = (left_ankle[0] + right_ankle[0]) / 2
        elif left_ankle[0] > 0:
            ankle_x_avg = left_ankle[0]
        elif right_ankle[0] > 0:
            ankle_x_avg = right_ankle[0]

        # 프레임 너비로 정규화
        frame_width = keypoints.max(axis=0)[0] + 1e-6
        ankle_x_normalized = ankle_x_avg / frame_width if ankle_x_avg > 0 else 0

        # === 추가 임상 변수용 데이터 ===
        # 손목 y좌표 (arm swing 측정용)
        left_wrist_y = left_wrist[1] if left_wrist[1] > 0 else 0
        right_wrist_y = right_wrist[1] if right_wrist[1] > 0 else 0

        # 발 y좌표 (foot clearance 측정용)
        left_foot = keypoints[self.LEFT_FOOT_INDEX]
        right_foot = keypoints[self.RIGHT_FOOT_INDEX]
        left_foot_y = left_foot[1] if left_foot[1] > 0 else 0
        right_foot_y = right_foot[1] if right_foot[1] > 0 else 0

        # 발목 y좌표 (cadence, step asymmetry 측정용)
        left_ankle_y = left_ankle[1] if left_ankle[1] > 0 else 0
        right_ankle_y = right_ankle[1] if right_ankle[1] > 0 else 0

        # 관절 ROM용 각도: Knee ROM (Hip-Knee-Ankle), Hip ROM (Shoulder-Hip-Knee)
        left_knee_angle = self._calculate_angle(left_hip, left_knee, left_ankle)
        right_knee_angle = self._calculate_angle(right_hip, right_knee, right_ankle)
        left_hip_angle = self._calculate_angle(left_shoulder, left_hip, left_knee)
        right_hip_angle = self._calculate_angle(right_shoulder, right_hip, right_knee)

        return {
            "frame": frame_num,
            "time": frame_num / fps,
            "leg_angle": avg_leg_angle,
            "hip_y": hip_y,
            "hip_height_normalized": hip_height_normalized,
            "shoulder_direction": shoulder_direction,
            "head_y": nose[1] if nose[1] > 0 else (left_shoulder[1] + right_shoulder[1]) / 2,
            "torso_angle": torso_angle,  # 상체 수직도 (90도에 가까울수록 직립)
            "wrist_knee_distance": wrist_knee_normalized,  # 손목-무릎 거리 (0에 가까울수록 손으로 짚음)
            "ankle_x": ankle_x_normalized,  # 발목 x좌표 (첫 걸음 감지용)
            "left_ankle_x": left_ankle[0],
            "right_ankle_x": right_ankle[0],
            # 임상 변수용 추가 데이터
            "left_wrist_y": left_wrist_y,
            "right_wrist_y": right_wrist_y,
            "left_foot_y": left_foot_y,
            "right_foot_y": right_foot_y,
            "left_ankle_y": left_ankle_y,
            "right_ankle_y": right_ankle_y,
            "left_knee_angle": left_knee_angle,
            "right_knee_angle": right_knee_angle,
            "left_hip_angle": left_hip_angle,
            "right_hip_angle": right_hip_angle,
        }

    # 손목-무릎 거리 임계값 (정규화된 값, 이 값 이하면 손으로 짚는 것으로 판단)
    HAND_SUPPORT_THRESHOLD = 0.15

    def _calculate_stand_up_metrics(self, frame_data: List[Dict], phases: Dict, fps: float) -> Dict:
        """기립 분석 - 엉덩이 높이 변화로 속도 계산"""
        stand_up_phase = phases['stand_up']
        start_time = stand_up_phase['start_time']
        end_time = stand_up_phase['end_time']

        # 해당 구간의 프레임 추출
        phase_frames = [f for f in frame_data if start_time <= f['time'] <= end_time]

        if len(phase_frames) < 2:
            return {
                "duration": stand_up_phase['duration'],
                "speed": 0,
                "start_time": start_time,
                "end_time": end_time,
                "assessment": "분석 불가",
                "used_hand_support": False
            }

        # 엉덩이 높이 변화 계산
        start_height = phase_frames[0]['hip_height_normalized']
        end_height = phase_frames[-1]['hip_height_normalized']
        height_change = end_height - start_height  # 양수면 올라감

        duration = stand_up_phase['duration']
        speed = height_change / duration if duration > 0 else 0

        # 손으로 무릎을 짚고 일어났는지 감지
        # 기립 구간에서 손목-무릎 거리가 임계값 이하인 프레임이 일정 비율 이상이면 손 짚음
        wrist_knee_distances = [f.get('wrist_knee_distance', 1.0) for f in phase_frames]
        hand_support_frames = sum(1 for d in wrist_knee_distances if d < self.HAND_SUPPORT_THRESHOLD)
        hand_support_ratio = hand_support_frames / len(phase_frames) if phase_frames else 0
        used_hand_support = hand_support_ratio > 0.3  # 30% 이상의 프레임에서 손이 무릎 근처

        # 속도 평가 (상대 속도 기준)
        if speed > 0.3:
            assessment = "빠름"
        elif speed > 0.15:
            assessment = "보통"
        else:
            assessment = "느림"

        return {
            "duration": round(duration, 2),
            "speed": round(speed, 3),
            "height_change": round(height_change, 3),
            "start_time": round(start_time, 2),
            "end_time": round(end_time, 2),
            "assessment": assessment,
            "used_hand_support": used_hand_support
        }

    def _calculate_sit_down_metrics(self, frame_data: List[Dict], phases: Dict, fps: float) -> Dict:
        """착석 분석 - 엉덩이 높이 변화로 속도 계산"""
        sit_down_phase = phases['sit_down']
        start_time = sit_down_phase['start_time']
        end_time = sit_down_phase['end_time']

        phase_frames = [f for f in frame_data if start_time <= f['time'] <= end_time]

        if len(phase_frames) < 2:
            return {
                "duration": sit_down_phase['duration'],
                "speed": 0,
                "start_time": start_time,
                "end_time": end_time,
                "assessment": "분석 불가",
                "used_hand_support": False
            }

        start_height = phase_frames[0]['hip_height_normalized']
        end_height = phase_frames[-1]['hip_height_normalized']
        height_change = abs(start_height - end_height)  # 절대값 (내려감)

        duration = sit_down_phase['duration']
        speed = height_change / duration if duration > 0 else 0

        # 손으로 무릎을 짚고 앉았는지 감지
        wrist_knee_distances = [f.get('wrist_knee_distance', 1.0) for f in phase_frames]
        hand_support_frames = sum(1 for d in wrist_knee_distances if d < self.HAND_SUPPORT_THRESHOLD)
        hand_support_ratio = hand_support_frames / len(phase_frames) if phase_frames else 0
        used_hand_support = hand_support_ratio > 0.3  # 30% 이상의 프레임에서 손이 무릎 근처

        # 착석 속도 평가 (너무 빠르면 낙상 위험)
        if speed > 0.4:
            assessment = "빠름 (주의)"
        elif speed > 0.2:
            assessment = "보통"
        else:
            assessment = "느림 (안정적)"

        return {
            "duration": round(duration, 2),
            "speed": round(speed, 3),
            "height_change": round(height_change, 3),
            "start_time": round(start_time, 2),
            "end_time": round(end_time, 2),
            "assessment": assessment,
            "used_hand_support": used_hand_support
        }

    def _calculate_reaction_time(self, frame_data: List[Dict], fps: float) -> Dict:
        """반응 시간 계산: 영상 시작~첫 움직임 감지"""
        if len(frame_data) < 10:
            return {"reaction_time": 0, "detection_method": "insufficient_data",
                    "confidence": 0, "first_movement_time": 0}

        # 처음 30% 구간에서 탐색
        search_range = min(len(frame_data), max(20, int(len(frame_data) * 0.3)))

        hip_heights = np.array([f['hip_height_normalized'] for f in frame_data[:search_range]])
        leg_angles = np.array([f['leg_angle'] for f in frame_data[:search_range]])

        # 스무딩 후 미분
        kernel = np.ones(5) / 5
        hip_smooth = np.convolve(hip_heights, kernel, mode='same')
        angle_smooth = np.convolve(leg_angles, kernel, mode='same')
        hip_velocity = np.gradient(hip_smooth)
        angle_velocity = np.gradient(angle_smooth)

        # 처음 10프레임의 기준선 표준편차
        baseline_n = min(10, len(hip_velocity) // 2)
        if baseline_n < 3:
            return {"reaction_time": 0, "detection_method": "insufficient_baseline",
                    "confidence": 0, "first_movement_time": 0}

        hip_baseline_std = np.std(hip_velocity[:baseline_n]) + 1e-6
        angle_baseline_std = np.std(angle_velocity[:baseline_n]) + 1e-6

        hip_threshold = 2.5 * hip_baseline_std
        angle_threshold = 2.5 * angle_baseline_std

        # 3프레임 연속 임계값 초과 확인
        def find_first_sustained(velocity, threshold, min_consecutive=3):
            for i in range(baseline_n, len(velocity) - min_consecutive):
                if all(abs(velocity[i + j]) > threshold for j in range(min_consecutive)):
                    return i
            return None

        first_move_hip = find_first_sustained(hip_velocity, hip_threshold)
        first_move_angle = find_first_sustained(angle_velocity, angle_threshold)

        candidates = [c for c in [first_move_hip, first_move_angle] if c is not None]
        if not candidates:
            # 2차 시도: 더 관대한 임계값 (1.8배)과 2프레임 연속
            lenient_hip_th = 1.8 * hip_baseline_std
            lenient_angle_th = 1.8 * angle_baseline_std
            lenient_hip = find_first_sustained(hip_velocity, lenient_hip_th, min_consecutive=2)
            lenient_angle = find_first_sustained(angle_velocity, lenient_angle_th, min_consecutive=2)
            lenient_candidates = [c for c in [lenient_hip, lenient_angle] if c is not None]

            if lenient_candidates:
                first_move_idx = min(lenient_candidates)
                method = "lenient"
                confidence = 50
            else:
                first_move_idx = 0
                method = "fallback"
                confidence = 20
        else:
            first_move_idx = min(candidates)
            if first_move_hip is not None and first_move_angle is not None:
                method = "combined"
                confidence = 85
            else:
                method = "hip_height" if first_move_hip is not None else "leg_angle"
                confidence = 70

        reaction_time = frame_data[first_move_idx]['time'] - frame_data[0]['time']

        return {
            "reaction_time": round(max(0, reaction_time), 3),
            "detection_method": method,
            "confidence": confidence,
            "first_movement_time": round(frame_data[first_move_idx]['time'], 3)
        }

    def _calculate_first_step_time(self, frame_data: List[Dict], phases: Dict, fps: float) -> Dict:
        """첫 걸음 시간: 기립 완료~첫 보행 발걸음 (파킨슨 지표)"""
        stand_up_end_time = phases['stand_up']['end_time']

        # 기립 완료 후 3초 구간의 프레임
        post_stand_frames = [f for f in frame_data
                             if stand_up_end_time <= f['time'] <= stand_up_end_time + 3.0]

        if len(post_stand_frames) < 5:
            return {"time_to_first_step": 0, "detection_method": "insufficient_data",
                    "hesitation_detected": False, "confidence": 0}

        # 발목 x좌표 변위 감시
        ankle_positions = [f.get('ankle_x', 0) for f in post_stand_frames]
        if not any(p != 0 for p in ankle_positions):
            # ankle_x가 없는 경우 (기존 데이터), head_y 변위로 대체
            head_positions = [f.get('head_y', 0) for f in post_stand_frames]
            if not any(p != 0 for p in head_positions):
                return {"time_to_first_step": 0, "detection_method": "no_data",
                        "hesitation_detected": False, "confidence": 20}
            positions = np.array(head_positions)
            initial_pos = np.mean(positions[:3])
            displacement = np.abs(positions - initial_pos)
            # 머리 위치 기반 임계값 (더 큼)
            disp_threshold = 0.03
            method = "head_displacement"
        else:
            positions = np.array(ankle_positions)
            initial_pos = np.mean(positions[:3])
            displacement = np.abs(positions - initial_pos)
            disp_threshold = 0.02
            method = "ankle_displacement"

        # 첫 번째로 임계값을 초과하는 프레임 찾기
        first_step_idx = None
        for i in range(len(displacement)):
            if displacement[i] > disp_threshold:
                # 3프레임 연속 확인
                if i + 2 < len(displacement) and displacement[i + 1] > disp_threshold:
                    first_step_idx = i
                    break

        if first_step_idx is None:
            time_to_first_step = post_stand_frames[-1]['time'] - stand_up_end_time
            confidence = 30
        else:
            time_to_first_step = post_stand_frames[first_step_idx]['time'] - stand_up_end_time
            confidence = 75

        hesitation_detected = time_to_first_step > 2.0

        return {
            "time_to_first_step": round(max(0, time_to_first_step), 3),
            "detection_method": method,
            "hesitation_detected": hesitation_detected,
            "confidence": confidence
        }

    def _analyze_front_video(
        self,
        video_path: str,
        patient_height_cm: float,
        progress_callback=None,
        frame_callback=None,
        save_overlay_video: bool = True,
        phases: Dict = None
    ) -> Dict:
        """정면 영상 분석 - 어깨/골반 기울기"""
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"정면 영상을 열 수 없습니다: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = int(fps * 20) if fps > 0 else 600
            print(f"[TUG] Estimated total_frames={total_frames} (front, original was 0)")
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 오버레이 영상 저장 설정
        overlay_video_path = None
        video_writer = None
        if save_overlay_video:
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            overlay_video_path = os.path.join(
                os.path.dirname(video_path),
                f"{base_name}_overlay.mp4"
            )
            # H.264 코덱 사용 (브라우저 호환성)
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            video_writer = cv2.VideoWriter(
                overlay_video_path, fourcc, fps,
                (frame_width, frame_height)
            )
            if not video_writer.isOpened():
                # avc1 실패시 mp4v로 폴백
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(
                    overlay_video_path, fourcc, fps,
                    (frame_width, frame_height)
                )
            print(f"[TUG FRONT] Saving overlay video to: {overlay_video_path}")

        tilt_data = []
        pose_3d_frames_front = []  # 3D 월드 랜드마크 (매 5프레임)
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)

            # 포즈 오버레이 프레임 생성
            annotated_frame = frame.copy()
            if results.pose_landmarks is not None:
                draw_body_landmarks(annotated_frame, results.pose_landmarks)

            # 오버레이 영상 저장
            if video_writer is not None:
                video_writer.write(annotated_frame)

            # 실시간 미리보기 콜백
            if frame_callback and frame_count % 3 == 0:
                try:
                    frame_callback(annotated_frame)
                except Exception as e:
                    print(f"[TUG FRONT] Frame callback failed: {e}")

            if results.pose_landmarks is not None:
                h, w = frame.shape[:2]
                keypoints = np.array([
                    [lm.x * w, lm.y * h] for lm in results.pose_landmarks.landmark
                ])
                data = self._extract_tilt_data(keypoints, frame_count, fps, frame_width=w)
                if data:
                    tilt_data.append(data)

                # 3D 월드 랜드마크 추출 (매 5프레임, 몸체만)
                if results.pose_world_landmarks and frame_count % 5 == 0:
                    world_lms = results.pose_world_landmarks.landmark
                    pose_3d_frames_front.append({
                        "time": round(frame_count / fps, 3),
                        "landmarks": [
                            [round(world_lms[i].x, 4), round(world_lms[i].y, 4), round(world_lms[i].z, 4)]
                            for i in range(11, 33)
                        ]
                    })

            frame_count += 1

            if progress_callback and total_frames > 0:
                progress = int((frame_count / total_frames) * 100)
                progress_callback(progress)

        cap.release()

        # 오버레이 비디오 저장 완료
        if video_writer is not None:
            video_writer.release()
            print(f"[TUG FRONT] Overlay video saved: {overlay_video_path}")

        if len(tilt_data) < 5:
            return {
                "shoulder_tilt_avg": 0,
                "shoulder_tilt_max": 0,
                "shoulder_tilt_direction": "분석 불가",
                "hip_tilt_avg": 0,
                "hip_tilt_max": 0,
                "hip_tilt_direction": "분석 불가",
                "angle_data": [],
                "overlay_video_path": overlay_video_path
            }

        # 기울기 통계 계산 (카메라 향한 프레임만, 클램핑 근처 제외)
        CLAMP_LIMIT = 24.0
        facing_data = [d for d in tilt_data if d.get('facing_camera', True)]
        shoulder_tilts = [d['shoulder_tilt'] for d in facing_data
                         if d['shoulder_tilt'] != 0 and abs(d['shoulder_tilt']) < CLAMP_LIMIT]
        hip_tilts = [d['hip_tilt'] for d in facing_data
                     if d['hip_tilt'] != 0 and abs(d['hip_tilt']) < CLAMP_LIMIT]

        shoulder_tilt_avg = sum(shoulder_tilts) / len(shoulder_tilts) if shoulder_tilts else 0
        shoulder_tilt_max = max(abs(t) for t in shoulder_tilts) if shoulder_tilts else 0
        hip_tilt_avg = sum(hip_tilts) / len(hip_tilts) if hip_tilts else 0
        hip_tilt_max = max(abs(t) for t in hip_tilts) if hip_tilts else 0

        # 방향 판단
        if shoulder_tilt_avg > 2:
            shoulder_direction = "오른쪽 높음"
        elif shoulder_tilt_avg < -2:
            shoulder_direction = "왼쪽 높음"
        else:
            shoulder_direction = "균형"

        if hip_tilt_avg > 2:
            hip_direction = "오른쪽 높음"
        elif hip_tilt_avg < -2:
            hip_direction = "왼쪽 높음"
        else:
            hip_direction = "균형"

        # 체중이동 분석
        weight_shift = self._calculate_weight_shift(tilt_data, fps)
        print(f"[TUG FRONT] Weight shift - sway: {weight_shift.get('lateral_sway_amplitude', 0):.1f}, standup: {weight_shift.get('standup_weight_shift', 'N/A')}")

        # 편향 프레임 캡처 (각도 시각화 포함)
        deviation_captures = self._capture_deviation_frames(video_path, tilt_data, fps, phases=phases)

        return {
            "shoulder_tilt_avg": round(shoulder_tilt_avg, 1),
            "shoulder_tilt_max": round(shoulder_tilt_max, 1),
            "shoulder_tilt_direction": shoulder_direction,
            "hip_tilt_avg": round(hip_tilt_avg, 1),
            "hip_tilt_max": round(hip_tilt_max, 1),
            "hip_tilt_direction": hip_direction,
            "angle_data": tilt_data,
            "weight_shift": weight_shift,
            "deviation_captures": deviation_captures,
            "overlay_video_path": overlay_video_path,
            "pose_3d_frames": pose_3d_frames_front if pose_3d_frames_front else None
        }

    # 발 랜드마크 인덱스
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32

    # 정면 카메라에서 어깨/골반 폭이 이 비율 이상이어야 기울기를 신뢰
    MIN_FACING_RATIO = 0.03  # 프레임 폭의 3% 이상 (원거리 촬영 고려)

    def _extract_tilt_data(self, keypoints: np.ndarray, frame_num: int, fps: float,
                           frame_width: float = 0) -> Optional[Dict]:
        """정면 영상에서 기울기 + 체중이동 데이터 추출"""
        if keypoints is None or keypoints.size == 0 or len(keypoints) < 33:
            return None

        left_shoulder = keypoints[self.LEFT_SHOULDER]
        right_shoulder = keypoints[self.RIGHT_SHOULDER]
        left_hip = keypoints[self.LEFT_HIP]
        right_hip = keypoints[self.RIGHT_HIP]

        # 어깨/골반 폭 (사람이 카메라를 향하고 있는지 판단)
        shoulder_width = abs(right_shoulder[0] - left_shoulder[0]) if left_shoulder[0] > 0 and right_shoulder[0] > 0 else 0
        hip_width = abs(right_hip[0] - left_hip[0]) if left_hip[0] > 0 and right_hip[0] > 0 else 0

        facing_camera = True
        if frame_width > 0:
            shoulder_ratio = shoulder_width / frame_width
            hip_ratio = hip_width / frame_width
            # 어깨와 골반 모두 폭이 좁으면 옆/뒤를 향한 것
            facing_camera = bool(shoulder_ratio > self.MIN_FACING_RATIO or hip_ratio > self.MIN_FACING_RATIO)

        shoulder_tilt = 0.0
        if facing_camera and left_shoulder[0] > 0 and right_shoulder[0] > 0 and shoulder_width > 5:
            shoulder_tilt = self._calculate_tilt(left_shoulder, right_shoulder)

        hip_tilt = 0.0
        if facing_camera and left_hip[0] > 0 and right_hip[0] > 0 and hip_width > 5:
            hip_tilt = self._calculate_tilt(left_hip, right_hip)

        # 체중이동 분석용 발 좌표
        left_ankle = keypoints[self.LEFT_ANKLE]
        right_ankle = keypoints[self.RIGHT_ANKLE]
        left_heel = keypoints[self.LEFT_HEEL]
        right_heel = keypoints[self.RIGHT_HEEL]
        left_foot = keypoints[self.LEFT_FOOT_INDEX]
        right_foot = keypoints[self.RIGHT_FOOT_INDEX]

        # 압력중심(CoP) 근사: 모든 발 랜드마크의 x좌표 평균
        foot_x_points = []
        for pt in [left_ankle, right_ankle, left_heel, right_heel, left_foot, right_foot]:
            if pt[0] > 0 and pt[1] > 0:
                foot_x_points.append(pt[0])

        cop_x = float(np.mean(foot_x_points)) if foot_x_points else 0

        # 좌우 발 중심 x좌표
        left_pts = [p[0] for p in [left_ankle, left_heel, left_foot] if p[0] > 0]
        right_pts = [p[0] for p in [right_ankle, right_heel, right_foot] if p[0] > 0]
        left_foot_x = float(np.mean(left_pts)) if left_pts else 0
        right_foot_x = float(np.mean(right_pts)) if right_pts else 0

        # 몸 중심선 (엉덩이 중앙 x좌표)
        body_midline_x = 0.0
        if left_hip[0] > 0 and right_hip[0] > 0:
            body_midline_x = (left_hip[0] + right_hip[0]) / 2

        # CoP 좌우 편향 - 프레임 폭으로 정규화 (백분율)
        lateral_offset_raw = (cop_x - body_midline_x) if body_midline_x > 0 and cop_x > 0 else 0
        lateral_offset = (lateral_offset_raw / frame_width * 100) if frame_width > 0 else lateral_offset_raw

        return {
            "time": round(frame_num / fps, 2),
            "shoulder_tilt": round(shoulder_tilt, 1),
            "hip_tilt": round(hip_tilt, 1),
            "facing_camera": facing_camera,
            "cop_x": round(cop_x, 1),
            "lateral_offset": round(lateral_offset, 2),
            "left_foot_x": round(left_foot_x, 1),
            "right_foot_x": round(right_foot_x, 1)
        }

    def _calculate_weight_shift(self, tilt_data: List[Dict], fps: float) -> Dict:
        """정면 영상 체중이동 분석"""
        if len(tilt_data) < 10:
            return {"lateral_sway_amplitude": 0, "lateral_sway_max": 0,
                    "sway_frequency": 0, "cop_trajectory": [],
                    "standup_weight_shift": "분석 불가", "assessment": "분석 불가"}

        lateral_offsets = np.array([d.get('lateral_offset', 0) for d in tilt_data])
        times = np.array([d['time'] for d in tilt_data])

        # 유효 데이터 필터링 (0이 아닌 값)
        valid_mask = lateral_offsets != 0
        if valid_mask.sum() < 5:
            return {"lateral_sway_amplitude": 0, "lateral_sway_max": 0,
                    "sway_frequency": 0, "cop_trajectory": [],
                    "standup_weight_shift": "분석 불가", "assessment": "데이터 부족"}

        valid_offsets = lateral_offsets[valid_mask]
        valid_times = times[valid_mask]

        # 흔들림 폭 (표준편차)
        sway_amplitude = float(np.std(valid_offsets))
        sway_max = float(np.max(np.abs(valid_offsets)))

        # 진동 주파수: 영점 교차 횟수 기반
        mean_offset = np.mean(valid_offsets)
        centered = valid_offsets - mean_offset
        zero_crossings = int(np.sum(np.diff(np.sign(centered)) != 0))
        duration = valid_times[-1] - valid_times[0]
        sway_frequency = (zero_crossings / 2) / duration if duration > 0 else 0

        # CoP 궤적 (50포인트 샘플링)
        sample_rate = max(1, len(valid_times) // 50)
        cop_trajectory = [
            {"time": round(float(valid_times[i]), 2), "x": round(float(valid_offsets[i]), 1)}
            for i in range(0, len(valid_times), sample_rate)
        ]

        # 기립 시 체중이동 (처음 20% 구간) - 백분율 기준
        standup_range = valid_offsets[:max(1, len(valid_offsets) // 5)]
        standup_mean = float(np.mean(standup_range))
        if standup_mean > 1.5:
            standup_shift = "오른쪽 편향"
        elif standup_mean < -1.5:
            standup_shift = "왼쪽 편향"
        else:
            standup_shift = "균형"

        # 종합 평가 - 백분율 기준 (프레임 폭 대비)
        if sway_amplitude < 1.0 and sway_max < 3.0:
            assessment = "체중이동이 안정적입니다."
        elif sway_amplitude < 2.5:
            assessment = "약간의 체중이동 불균형이 관찰됩니다."
        else:
            assessment = "체중이동 불균형에 주의가 필요합니다."

        return {
            "lateral_sway_amplitude": round(sway_amplitude, 1),
            "lateral_sway_max": round(sway_max, 1),
            "sway_frequency": round(sway_frequency, 2),
            "cop_trajectory": cop_trajectory,
            "standup_weight_shift": standup_shift,
            "assessment": assessment
        }

    # 편향 감지 임계값 (도)
    DEVIATION_THRESHOLD = 5.0
    # 돌아서기 단계 편향 감지 임계값 (도) - 회전 중이므로 높은 임계값 적용
    TURN_DEVIATION_THRESHOLD = 15.0

    def _capture_deviation_frames(
        self,
        video_path: str,
        tilt_data: List[Dict],
        fps: float,
        max_captures: int = 10,
        phases: Dict = None
    ) -> List[Dict]:
        """어깨/골반 기울기 임계값 초과 프레임을 포즈 오버레이와 각도 시각화로 캡처"""
        deviations = []

        # 돌아서기 단계 시간 범위 추출
        turn_start = None
        turn_end = None
        if phases and 'turn' in phases:
            turn_phase = phases['turn']
            if isinstance(turn_phase, dict):
                turn_start = turn_phase.get('start_time')
                turn_end = turn_phase.get('end_time')
                print(f"[TUG FRONT] Turn phase: {turn_start:.2f}s ~ {turn_end:.2f}s (threshold={self.TURN_DEVIATION_THRESHOLD}°)")

        # 임계값 초과 프레임 필터링 (카메라를 향한 프레임만, 클램핑 값 제외)
        CLAMP_LIMIT = 24.0  # ±25° 클램핑 근처 값은 회전 왜곡
        for d in tilt_data:
            if not d.get('facing_camera', True):
                continue
            s_tilt = abs(d.get('shoulder_tilt', 0))
            h_tilt = abs(d.get('hip_tilt', 0))
            # 클램핑 한계에 가까운 값은 부분 회전에 의한 왜곡이므로 제외
            if s_tilt >= CLAMP_LIMIT or h_tilt >= CLAMP_LIMIT:
                continue

            # 돌아서기 단계에서는 더 높은 임계값 적용
            t = d.get('time', 0)
            is_turn_phase = (turn_start is not None and turn_end is not None
                            and turn_start <= t <= turn_end)
            threshold = self.TURN_DEVIATION_THRESHOLD if is_turn_phase else self.DEVIATION_THRESHOLD

            shoulder_dev = s_tilt > threshold
            hip_dev = h_tilt > threshold
            if shoulder_dev or hip_dev:
                dev_type = 'both' if shoulder_dev and hip_dev else ('shoulder' if shoulder_dev else 'hip')
                severity_val = max(abs(d.get('shoulder_tilt', 0)), abs(d.get('hip_tilt', 0)))
                severity = 'severe' if severity_val > 15 else ('moderate' if severity_val > 10 else 'mild')
                deviations.append({**d, 'type': dev_type, 'severity': severity})

        if not deviations:
            return []

        # 1초 간격 샘플링: 같은 1초 구간 내에서 가장 심한 편향만 캡처
        time_buckets = {}
        for dev in deviations:
            bucket_key = int(dev['time'])  # 1초 단위 버킷
            severity_val = max(abs(dev.get('shoulder_tilt', 0)), abs(dev.get('hip_tilt', 0)))
            if bucket_key not in time_buckets or severity_val > time_buckets[bucket_key][1]:
                time_buckets[bucket_key] = (dev, severity_val)
        deviations = [v[1][0] for v in sorted(time_buckets.items())]

        # 최대 캡처 수로 균일 샘플링
        if len(deviations) > max_captures:
            indices = np.linspace(0, len(deviations) - 1, max_captures, dtype=int)
            deviations = [deviations[i] for i in indices]

        print(f"[TUG FRONT] Capturing {len(deviations)} deviation frames (1s interval)...")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        result_captures = []
        for dev in deviations:
            frame_num = int(dev['time'] * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if not ret:
                continue

            # 포즈 감지
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)

            annotated = frame.copy()
            if results.pose_landmarks:
                draw_body_landmarks(annotated, results.pose_landmarks)
                h, w = annotated.shape[:2]
                lm = results.pose_landmarks.landmark

                # 어깨 시각화
                ls = (int(lm[11].x * w), int(lm[11].y * h))
                rs = (int(lm[12].x * w), int(lm[12].y * h))
                mid_s = ((ls[0] + rs[0]) // 2, (ls[1] + rs[1]) // 2)
                shoulder_tilt = dev.get('shoulder_tilt', 0)

                s_color = (0, 0, 255) if abs(shoulder_tilt) > 10 else (0, 165, 255)
                # 어깨 연결선
                cv2.line(annotated, ls, rs, s_color, 3)
                # 수평 기준선
                cv2.line(annotated, (ls[0], mid_s[1]), (rs[0], mid_s[1]), (200, 200, 200), 1, cv2.LINE_AA)
                # 각도 아크
                radius = min(40, abs(rs[0] - ls[0]) // 4)
                if radius > 5:
                    angle = int(shoulder_tilt)
                    cv2.ellipse(annotated, mid_s, (radius, radius), 0, 0, -angle, s_color, 2)

                # 골반 시각화
                lh = (int(lm[23].x * w), int(lm[23].y * h))
                rh = (int(lm[24].x * w), int(lm[24].y * h))
                mid_h = ((lh[0] + rh[0]) // 2, (lh[1] + rh[1]) // 2)
                hip_tilt = dev.get('hip_tilt', 0)

                h_color = (0, 0, 255) if abs(hip_tilt) > 10 else (0, 165, 255)
                cv2.line(annotated, lh, rh, h_color, 3)
                cv2.line(annotated, (lh[0], mid_h[1]), (rh[0], mid_h[1]), (200, 200, 200), 1, cv2.LINE_AA)
                if radius > 5:
                    cv2.ellipse(annotated, mid_h, (radius, radius), 0, 0, -int(hip_tilt), h_color, 2)

                # 각도 텍스트 표시 (하단)
                overlay = annotated.copy()
                cv2.rectangle(overlay, (0, h - 70), (w, h), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.6, annotated, 0.4, 0, annotated)

                cv2.putText(annotated, f"Shoulder: {shoulder_tilt:+.1f} deg",
                           (10, h - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, s_color, 2)
                cv2.putText(annotated, f"Hip: {hip_tilt:+.1f} deg",
                           (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, h_color, 2)

                # 시간 표시
                cv2.putText(annotated, f"t={dev['time']:.2f}s",
                           (w - 120, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            # base64 인코딩
            _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_b64 = base64.b64encode(buffer).decode('utf-8')

            result_captures.append({
                "frame": frame_b64,
                "time": dev['time'],
                "shoulder_angle": dev.get('shoulder_tilt', 0),
                "hip_angle": dev.get('hip_tilt', 0),
                "type": dev['type'],
                "severity": dev['severity']
            })

        cap.release()
        print(f"[TUG FRONT] Captured {len(result_captures)} deviation frames")
        return result_captures

    def _annotate_3d_frames_with_phases(self, pose_3d_frames, phases: Dict) -> list:
        """3D 프레임에 TUG 단계 정보 부여"""
        if not pose_3d_frames:
            return []

        phase_order = ['stand_up', 'walk_out', 'turn', 'walk_back', 'sit_down']
        annotated = []
        for frame in pose_3d_frames:
            t = frame['time']
            phase_name = 'unknown'
            for pname in phase_order:
                p = phases.get(pname, {})
                st = p.get('start_time', 0)
                et = p.get('end_time', 0)
                if st <= t <= et:
                    phase_name = pname
                    break
            # stand_up 이전 → stand_up, sit_down 이후 → sit_down
            if phase_name == 'unknown':
                su = phases.get('stand_up', {})
                sd = phases.get('sit_down', {})
                if t < su.get('start_time', 0):
                    phase_name = 'stand_up'
                elif t > sd.get('end_time', 0):
                    phase_name = 'sit_down'
            annotated.append({**frame, "phase": phase_name})
        return annotated

    def _merge_results(self, side_result: Dict, front_result: Dict, patient_height_cm: float) -> Dict:
        """측면 분석 결과와 정면 분석 결과 통합"""
        total_time = side_result['total_time_seconds']

        # 보행 패턴 평가
        tilt_assessment = self._get_tilt_assessment(front_result)

        # 오버레이 영상 경로 (파일명만 추출)
        side_overlay_path = side_result.get('overlay_video_path')
        side_overlay_filename = os.path.basename(side_overlay_path) if side_overlay_path else None

        front_overlay_path = front_result.get('overlay_video_path')
        front_overlay_filename = os.path.basename(front_overlay_path) if front_overlay_path else None

        return {
            "test_type": "TUG",
            "total_time_seconds": round(total_time, 2),
            "walk_time_seconds": round(total_time, 2),
            "walk_speed_mps": 0,
            "assessment": side_result['assessment'],

            # 포즈 오버레이 영상 경로 (측면/정면)
            "overlay_video_filename": side_overlay_filename,  # 기존 호환성
            "side_overlay_video_filename": side_overlay_filename,
            "front_overlay_video_filename": front_overlay_filename,

            # 기립/착석 분석 (측면 영상)
            "stand_up": side_result['stand_up'],
            "sit_down": side_result['sit_down'],

            # 반응 시간 (측면 영상)
            "reaction_time": side_result.get('reaction_time', {}),

            # 첫 걸음 시간 (파킨슨 지표)
            "first_step_time": side_result.get('first_step_time', {}),

            # 기울기 분석 (정면 영상)
            "tilt_analysis": {
                "shoulder_tilt_avg": front_result['shoulder_tilt_avg'],
                "shoulder_tilt_max": front_result['shoulder_tilt_max'],
                "shoulder_tilt_direction": front_result['shoulder_tilt_direction'],
                "hip_tilt_avg": front_result['hip_tilt_avg'],
                "hip_tilt_max": front_result['hip_tilt_max'],
                "hip_tilt_direction": front_result['hip_tilt_direction'],
                "assessment": tilt_assessment
            },

            # 체중이동 분석 (정면 영상)
            "weight_shift": front_result.get('weight_shift', {}),

            # 자세 편향 캡처 (정면 영상)
            "deviation_captures": front_result.get('deviation_captures', []),

            # 단계별 시간
            "phases": {
                "stand_up": {
                    "duration": round(side_result['phases']['stand_up']['duration'], 2),
                    "start_time": round(side_result['phases']['stand_up']['start_time'], 2),
                    "end_time": round(side_result['phases']['stand_up']['end_time'], 2)
                },
                "walk_out": {
                    "duration": round(side_result['phases']['walk_out']['duration'], 2),
                    "start_time": round(side_result['phases']['walk_out']['start_time'], 2),
                    "end_time": round(side_result['phases']['walk_out']['end_time'], 2)
                },
                "turn": {
                    "duration": round(side_result['phases']['turn']['duration'], 2),
                    "start_time": round(side_result['phases']['turn']['start_time'], 2),
                    "end_time": round(side_result['phases']['turn']['end_time'], 2)
                },
                "walk_back": {
                    "duration": round(side_result['phases']['walk_back']['duration'], 2),
                    "start_time": round(side_result['phases']['walk_back']['start_time'], 2),
                    "end_time": round(side_result['phases']['walk_back']['end_time'], 2)
                },
                "sit_down": {
                    "duration": round(side_result['phases']['sit_down']['duration'], 2),
                    "start_time": round(side_result['phases']['sit_down']['start_time'], 2),
                    "end_time": round(side_result['phases']['sit_down']['end_time'], 2)
                }
            },

            # 단계별 캡처 이미지 및 검증 정보 (측면 영상)
            "phase_frames": side_result.get('phase_frames', {}),

            "fps": side_result['fps'],
            "total_frames": side_result['total_frames'],
            "frames_analyzed": side_result['frames_analyzed'],
            "patient_height_cm": patient_height_cm,
            "model": self.model_name,

            # 기울기 그래프 데이터 (정면 영상)
            "angle_data": front_result.get('angle_data', []),

            # 단계 감지 신뢰도
            "phase_confidence": side_result['phases'].get('phase_confidence', {}),

            # 단계별 클립
            "phase_clips": side_result.get('phase_clips', {}),

            # 기존 gait_pattern 필드 유지 (호환성)
            "gait_pattern": {
                "shoulder_tilt_avg": front_result['shoulder_tilt_avg'],
                "shoulder_tilt_max": front_result['shoulder_tilt_max'],
                "shoulder_tilt_direction": front_result['shoulder_tilt_direction'],
                "hip_tilt_avg": front_result['hip_tilt_avg'],
                "hip_tilt_max": front_result['hip_tilt_max'],
                "hip_tilt_direction": front_result['hip_tilt_direction'],
                "assessment": tilt_assessment
            },

            # 질환별 프로파일 정보
            "disease_profile": self._disease_profile.name if self._disease_profile else "default",
            "disease_profile_display": self._disease_profile.display_name if self._disease_profile else "기본",

            # 질환별 추가 임상 변수
            "clinical_variables": side_result.get('clinical_variables', {}),

            # 3D 포즈 데이터 (측면 영상 - 전체 TUG 시퀀스)
            "pose_3d_frames": self._annotate_3d_frames_with_phases(
                side_result.get('pose_3d_frames', []),
                side_result.get('phases', {})
            ) or None,

            # 3D 포즈 데이터 (정면 영상 - 보조)
            "pose_3d_frames_front": self._annotate_3d_frames_with_phases(
                front_result.get('pose_3d_frames', []),
                side_result.get('phases', {})
            ) or None,
        }

    def _get_tilt_assessment(self, front_result: Dict) -> str:
        """기울기 분석 종합 평가"""
        shoulder_max = front_result.get('shoulder_tilt_max', 0)
        hip_max = front_result.get('hip_tilt_max', 0)

        if shoulder_max < 5 and hip_max < 5:
            return "보행 자세가 안정적입니다."
        elif shoulder_max < 10 and hip_max < 10:
            return "약간의 자세 불균형이 관찰됩니다."
        else:
            return "자세 불균형에 주의가 필요합니다."

    def analyze(self, video_path: str, patient_height_cm: float, progress_callback=None, frame_callback=None, phase_callback=None) -> Dict:
        """
        TUG 검사 동영상 분석

        Args:
            video_path: 동영상 파일 경로
            patient_height_cm: 환자의 실제 키 (cm)
            progress_callback: 진행률 콜백 함수
            frame_callback: 프레임 콜백 함수 (실시간 미리보기용)
            phase_callback: 단계 콜백 함수 (현재 단계 정보 전달)

        Returns:
            분석 결과 딕셔너리
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"동영상을 열 수 없습니다: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = int(fps * 20) if fps > 0 else 600
            print(f"[TUG] Estimated total_frames={total_frames} (single, original was 0)")

        # 프레임별 데이터 수집
        frame_data = []
        pose_3d_frames = []  # 3D 월드 랜드마크 (매 3프레임)
        frame_count = 0

        # 실시간 단계 감지용 상태
        current_phase = "stand_up"  # 시작은 일어서기
        phase_start_time = 0.0
        standing_detected = False
        turn_detected = False
        sitting_started = False

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # MediaPipe Pose 추론
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)

            current_time = frame_count / fps

            # 프레임 콜백 호출 (실시간 미리보기용)
            if frame_callback and frame_count % 3 == 0:
                try:
                    annotated_frame = frame.copy()
                    if results.pose_landmarks is not None:
                        draw_body_landmarks(annotated_frame, results.pose_landmarks)
                    frame_callback(annotated_frame)
                except Exception as e:
                    print(f"[TUG ERROR] Frame callback failed: {e}")

            if results.pose_landmarks is not None:
                h, w = frame.shape[:2]
                keypoints = np.array([
                    [lm.x * w, lm.y * h] for lm in results.pose_landmarks.landmark
                ])
                data = self._extract_frame_data(keypoints, frame_count, fps)
                if data:
                    frame_data.append(data)

                # 3D 월드 랜드마크 추출 (매 3프레임, 몸체만)
                if results.pose_world_landmarks and frame_count % 3 == 0:
                    world_lms = results.pose_world_landmarks.landmark
                    pose_3d_frames.append({
                        "time": round(frame_count / fps, 3),
                        "landmarks": [
                            [round(world_lms[i].x, 4), round(world_lms[i].y, 4), round(world_lms[i].z, 4)]
                            for i in range(11, 33)
                        ]
                    })

                if data:
                    # 실시간 단계 감지
                    leg_angle = data.get('leg_angle', 0)
                    shoulder_direction = data.get('shoulder_direction', 0)

                    new_phase = self._detect_current_phase_realtime(
                        leg_angle, shoulder_direction, current_time,
                        standing_detected, turn_detected, sitting_started,
                        len(frame_data)
                    )

                    # 상태 업데이트
                    if leg_angle >= self.STANDING_ANGLE_THRESHOLD:
                        standing_detected = True

                    if standing_detected and not turn_detected:
                        # 회전 감지 (어깨 방향 급격한 변화)
                        if len(frame_data) > 10:
                            recent_directions = [f['shoulder_direction'] for f in frame_data[-10:]]
                            if len(recent_directions) >= 10:
                                direction_change = abs(recent_directions[-1] - recent_directions[0])
                                if direction_change > 0.5:  # 라디안 기준
                                    turn_detected = True

                    if turn_detected and leg_angle < self.STANDING_ANGLE_THRESHOLD:
                        sitting_started = True

                    # 단계가 변경되었으면 콜백 호출
                    if new_phase != current_phase:
                        current_phase = new_phase
                        if phase_callback:
                            phase_callback({
                                "phase": current_phase,
                                "phase_label": self._get_phase_label(current_phase),
                                "time": current_time
                            })

            frame_count += 1

            # 진행률 콜백
            if progress_callback and total_frames > 0:
                progress = 10 + int((frame_count / total_frames) * 70)
                progress_callback(progress)

        cap.release()

        if len(frame_data) < 10:
            raise ValueError("충분한 포즈 데이터를 감지하지 못했습니다.")

        # TUG 단계 감지
        phases = self._detect_tug_phases(frame_data, fps)

        # 총 시간 계산
        total_time_seconds = phases['total_duration']

        # 평가 결정
        assessment = self._get_assessment(total_time_seconds)

        # 보행 패턴 분석 (걷기 구간)
        walking_frames = self._get_walking_frames(frame_data, phases)
        gait_pattern = self._analyze_gait_pattern(walking_frames)

        # 각도 데이터 (그래프용)
        angle_data = []
        start_time = phases['stand_up']['start_time']
        for f in frame_data:
            if f['time'] >= start_time:
                angle_data.append({
                    "time": round(f["time"] - start_time, 2),
                    "shoulder_tilt": round(f.get("shoulder_tilt_deg", 0), 1),
                    "hip_tilt": round(f.get("hip_tilt_deg", 0), 1)
                })

        # 단계 전환 시점 프레임 캡처
        print(f"[TUG] Capturing phase transition frames...")
        phase_frames = self._capture_phase_frames(video_path, phases, fps)
        print(f"[TUG] Captured {len(phase_frames)} phase frames")

        return {
            "test_type": "TUG",
            "total_time_seconds": round(total_time_seconds, 2),
            "walk_time_seconds": round(total_time_seconds, 2),  # 호환성용
            "walk_speed_mps": 0,
            "assessment": assessment,
            "phases": {
                "stand_up": {
                    "duration": round(phases['stand_up']['duration'], 2),
                    "start_time": round(phases['stand_up']['start_time'], 2),
                    "end_time": round(phases['stand_up']['end_time'], 2)
                },
                "walk_out": {
                    "duration": round(phases['walk_out']['duration'], 2),
                    "start_time": round(phases['walk_out']['start_time'], 2),
                    "end_time": round(phases['walk_out']['end_time'], 2)
                },
                "turn": {
                    "duration": round(phases['turn']['duration'], 2),
                    "start_time": round(phases['turn']['start_time'], 2),
                    "end_time": round(phases['turn']['end_time'], 2)
                },
                "walk_back": {
                    "duration": round(phases['walk_back']['duration'], 2),
                    "start_time": round(phases['walk_back']['start_time'], 2),
                    "end_time": round(phases['walk_back']['end_time'], 2)
                },
                "sit_down": {
                    "duration": round(phases['sit_down']['duration'], 2),
                    "start_time": round(phases['sit_down']['start_time'], 2),
                    "end_time": round(phases['sit_down']['end_time'], 2)
                }
            },
            "phase_frames": phase_frames,  # 단계별 캡처 이미지 및 검증 정보
            "fps": fps,
            "total_frames": total_frames,
            "frames_analyzed": len(frame_data),
            "patient_height_cm": patient_height_cm,
            "model": self.model_name,
            "gait_pattern": gait_pattern,
            "angle_data": angle_data,

            # 질환별 프로파일 정보
            "disease_profile": self._disease_profile.name if self._disease_profile else "default",
            "disease_profile_display": self._disease_profile.display_name if self._disease_profile else "기본",

            # 3D 포즈 데이터 (단계 어노테이션 포함)
            "pose_3d_frames": self._annotate_3d_frames_with_phases(
                pose_3d_frames, phases
            ) if pose_3d_frames else None,
        }

    def _extract_frame_data(self, keypoints: np.ndarray, frame_num: int, fps: float) -> Optional[Dict]:
        """프레임에서 필요한 데이터 추출"""
        if keypoints is None or keypoints.size == 0 or len(keypoints) < 33:
            return None

        # 주요 키포인트 추출
        nose = keypoints[self.NOSE]
        left_hip = keypoints[self.LEFT_HIP]
        right_hip = keypoints[self.RIGHT_HIP]
        left_knee = keypoints[self.LEFT_KNEE]
        right_knee = keypoints[self.RIGHT_KNEE]
        left_ankle = keypoints[self.LEFT_ANKLE]
        right_ankle = keypoints[self.RIGHT_ANKLE]
        left_shoulder = keypoints[self.LEFT_SHOULDER]
        right_shoulder = keypoints[self.RIGHT_SHOULDER]

        # 엉덩이-무릎-발목 각도 계산 (자세 판단용)
        left_leg_angle = self._calculate_angle(left_hip, left_knee, left_ankle)
        right_leg_angle = self._calculate_angle(right_hip, right_knee, right_ankle)
        avg_leg_angle = (left_leg_angle + right_leg_angle) / 2 if left_leg_angle > 0 and right_leg_angle > 0 else max(left_leg_angle, right_leg_angle)

        # 머리 높이 (자세 변화 감지용)
        head_y = nose[1] if nose[1] > 0 else (left_shoulder[1] + right_shoulder[1]) / 2

        # 엉덩이 높이
        hip_y = (left_hip[1] + right_hip[1]) / 2 if left_hip[1] > 0 and right_hip[1] > 0 else max(left_hip[1], right_hip[1])

        # 어깨 기울기
        shoulder_tilt_deg = 0.0
        if left_shoulder[0] > 0 and right_shoulder[0] > 0:
            shoulder_tilt_deg = self._calculate_tilt(left_shoulder, right_shoulder)

        # 골반 기울기
        hip_tilt_deg = 0.0
        if left_hip[0] > 0 and right_hip[0] > 0:
            hip_tilt_deg = self._calculate_tilt(left_hip, right_hip)

        # 어깨 방향 (회전 감지용)
        shoulder_direction = 0.0
        if left_shoulder[0] > 0 and right_shoulder[0] > 0:
            shoulder_direction = math.atan2(
                right_shoulder[1] - left_shoulder[1],
                right_shoulder[0] - left_shoulder[0]
            )

        return {
            "frame": frame_num,
            "time": frame_num / fps,
            "leg_angle": avg_leg_angle,
            "head_y": head_y,
            "hip_y": hip_y,
            "shoulder_tilt_deg": shoulder_tilt_deg,
            "hip_tilt_deg": hip_tilt_deg,
            "shoulder_direction": shoulder_direction,
            "left_shoulder": left_shoulder.tolist(),
            "right_shoulder": right_shoulder.tolist()
        }

    def _calculate_angle(self, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
        """세 점으로 각도 계산 (p2가 꼭지점)"""
        if p1[0] <= 0 or p2[0] <= 0 or p3[0] <= 0:
            return 0

        v1 = p1 - p2
        v2 = p3 - p2

        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
        return math.degrees(angle)

    def _calculate_tilt(self, left_point: np.ndarray, right_point: np.ndarray) -> float:
        """어깨/골반 기울기 계산 (수평으로부터의 편차)

        abs(dx)를 사용하여 카메라 방향(dx 부호)에 무관하게 수평 편차만 계산.
        양수: 오른쪽이 높음, 음수: 왼쪽이 높음
        """
        dx = right_point[0] - left_point[0]
        dy = right_point[1] - left_point[1]

        if abs(dx) < 1:
            return 0.0

        # abs(dx)로 카메라 방향 무관하게 수평 편차만 측정
        angle_rad = math.atan2(-dy, abs(dx))
        angle_deg = math.degrees(angle_rad)

        # ±25° 범위로 제한 (이 이상은 회전에 의한 왜곡)
        angle_deg = max(-25.0, min(25.0, angle_deg))
        return round(angle_deg, 1)

    def _detect_tug_phases(self, frame_data: List[Dict], fps: float) -> Dict:
        """TUG 검사의 각 단계 감지 (다중신호 융합)"""
        n = len(frame_data)
        if n < 30:
            # 데이터 부족시 기본값
            total_time = frame_data[-1]['time'] - frame_data[0]['time']
            phase_time = total_time / 5
            return self._create_default_phases(frame_data[0]['time'], phase_time)

        # 스무딩된 다리 각도와 머리 높이, 상체 수직도
        leg_angles = [f['leg_angle'] for f in frame_data]
        head_heights = [f['head_y'] for f in frame_data]
        torso_angles = [f.get('torso_angle', 90) for f in frame_data]  # 상체 수직도

        # 이동 평균 필터
        window = min(15, n // 10)
        if window < 3:
            window = 3
        smoothed_angles = self._moving_average(leg_angles, window)
        smoothed_heights = self._moving_average(head_heights, window)
        smoothed_torso = self._moving_average(torso_angles, window)

        # 다중신호 미분 및 융합 점수 계산
        derivatives = self._compute_signal_derivatives(frame_data, fps)
        fusion_scores = {}
        if derivatives:
            for btype in ['stand_start', 'stand_end', 'sit_start', 'sit_end', 'turn']:
                fusion_scores[btype] = self._compute_fusion_score(derivatives, btype)

        # 엉덩이 높이 (모든 단계에서 공통 사용)
        hip_heights = [f['hip_height_normalized'] for f in frame_data]
        smoothed_hip_heights = self._moving_average(hip_heights, window)

        # 1. 일어서기 시작점 감지 (앉은 자세에서 엉덩이가 올라가기 시작)
        stand_up_start_idx = self._find_stand_up_start(smoothed_angles, smoothed_heights,
                                                        fusion_scores.get('stand_start'),
                                                        smoothed_hip_heights)

        # 2. 일어서기 완료점 감지 (선 자세에 도달 + 상체가 수직 + 엉덩이 높이 상승)
        stand_up_end_idx = self._find_stand_up_end(smoothed_angles, smoothed_torso, stand_up_start_idx,
                                                    fusion_scores.get('stand_end'),
                                                    smoothed_hip_heights)

        # 3. 앉기 시작점 감지 (엉덩이가 내려가기 시작)
        sit_down_start_idx = self._find_sit_down_start(smoothed_angles, stand_up_end_idx,
                                                        fusion_scores.get('sit_start'),
                                                        smoothed_hip_heights)

        # 4. 앉기 완료점 감지 (엉덩이가 앉은 높이로 복귀)
        sit_down_end_idx = self._find_sit_down_end(smoothed_angles, sit_down_start_idx,
                                                    fusion_scores.get('sit_end'),
                                                    smoothed_hip_heights)

        # 5. 회전 감지 (어깨 방향 변화)
        turn_idx = self._find_turn_point(frame_data, stand_up_end_idx, sit_down_start_idx,
                                          fusion_scores.get('turn'))

        # 시간 계산
        stand_up_start = frame_data[stand_up_start_idx]['time']
        stand_up_end = frame_data[stand_up_end_idx]['time']
        turn_start_time = frame_data[turn_idx]['time']  # 회전 시작 시점
        sit_down_start = frame_data[sit_down_start_idx]['time']
        sit_down_end = frame_data[sit_down_end_idx]['time']

        # 회전 시간 추정 (일반적으로 1~2초)
        total_walk_time = sit_down_start - stand_up_end
        turn_duration = min(2.0, max(0.8, total_walk_time * 0.15))

        # 회전 종료 시점 계산
        turn_end_time = turn_start_time + turn_duration

        walk_out_duration = turn_start_time - stand_up_end
        walk_back_duration = sit_down_start - turn_end_time

        # TUG 대칭성 보정: walk_out과 walk_back은 같은 3m 거리이므로 비슷해야 함
        # walk_back이 walk_out의 25% 미만이면 turn_start가 너무 늦게 잡힌 것
        symmetry_corrected = False
        if walk_out_duration > 2.0 and walk_back_duration < walk_out_duration * 0.25:
            symmetry_corrected = True
            # 회전 전후 시간을 대칭적으로 재분배
            # 총 이동시간(walk_out + turn + walk_back)을 유지하면서 재분배
            total_moving = sit_down_start - stand_up_end
            # 회전 시간은 전체의 10~15% (일반적으로 1~2초)
            estimated_turn = min(2.0, max(0.8, total_moving * 0.12))
            remaining = total_moving - estimated_turn
            # walk_out과 walk_back을 비슷하게 분배 (보행 속도가 일정하다고 가정)
            # 보통 돌아올 때 약간 빠르므로 walk_back을 약간 짧게 (45:55)
            walk_back_ratio = 0.45
            new_walk_back = remaining * walk_back_ratio
            new_walk_out = remaining * (1 - walk_back_ratio)

            # 새로운 경계 시간 재계산
            turn_start_time = stand_up_end + new_walk_out
            turn_duration = estimated_turn
            turn_end_time = turn_start_time + turn_duration
            walk_out_duration = new_walk_out
            walk_back_duration = new_walk_back

        total_duration = sit_down_end - stand_up_start

        # 신뢰도 점수 계산
        phase_confidence = self._calculate_phase_confidence(
            frame_data, fusion_scores,
            stand_up_start_idx, stand_up_end_idx,
            turn_idx, sit_down_start_idx, sit_down_end_idx
        )

        # 대칭성 보정 적용 시 보정된 단계의 confidence 조정
        if symmetry_corrected:
            for phase_name in ['walk_out', 'turn', 'walk_back']:
                original = phase_confidence.get(phase_name, 50)
                phase_confidence[phase_name] = min(original, 60)

        return {
            'total_duration': total_duration,
            'stand_up': {
                'start_time': stand_up_start,
                'end_time': stand_up_end,
                'duration': stand_up_end - stand_up_start
            },
            'walk_out': {
                'start_time': stand_up_end,
                'end_time': turn_start_time,
                'duration': walk_out_duration
            },
            'turn': {
                'start_time': turn_start_time,
                'end_time': turn_end_time,
                'duration': turn_duration
            },
            'walk_back': {
                'start_time': turn_end_time,
                'end_time': sit_down_start,
                'duration': walk_back_duration
            },
            'sit_down': {
                'start_time': sit_down_start,
                'end_time': sit_down_end,
                'duration': sit_down_end - sit_down_start
            },
            'phase_confidence': phase_confidence
        }

    def _calculate_phase_confidence(self, frame_data, fusion_scores,
                                     stand_start_idx, stand_end_idx,
                                     turn_idx, sit_start_idx, sit_end_idx) -> Dict[str, int]:
        """각 단계 경계의 신뢰도 점수 계산 (0-100)"""
        confidence = {}

        for name, btype, idx in [
            ('stand_up', 'stand_start', stand_start_idx),
            ('walk_out', 'stand_end', stand_end_idx),
            ('turn', 'turn', turn_idx),
            ('walk_back', 'sit_start', sit_start_idx),
            ('sit_down', 'sit_end', sit_end_idx),
        ]:
            score_arr = fusion_scores.get(btype)
            if score_arr is not None and len(score_arr) > 0 and idx < len(score_arr):
                # 해당 인덱스의 융합 점수를 신뢰도로 변환
                window = 5
                start = max(0, idx - window)
                end = min(len(score_arr), idx + window + 1)
                local_scores = score_arr[start:end]
                peak_score = float(score_arr[idx])
                local_mean = float(np.mean(local_scores))
                # 피크가 주변 대비 얼마나 뚜렷한지
                sharpness = (peak_score - local_mean) / (local_mean + 1e-6)
                conf = min(100, max(20, int(50 + sharpness * 30 + peak_score * 20)))
                confidence[name] = conf
            else:
                confidence[name] = 50  # 기본값

        return confidence

    def _find_stand_up_start(self, angles: List[float], heights: List[float],
                              fusion_score: Optional[np.ndarray] = None,
                              hip_heights: Optional[List[float]] = None) -> int:
        """일어서기 시작점 찾기 (다중신호 융합 + 엉덩이 높이 상승 시작 검증)

        앉은 상태에서 단순히 허리를 숙이는 동작(leg_angle 변동)과
        실제 기립 시작(엉덩이가 올라가기 시작)을 구분한다.
        """
        n = len(angles)

        # 엉덩이 높이의 상승 시작점을 보조 신호로 활용
        hip_rise_start = None
        if hip_heights and len(hip_heights) > 10:
            # 초반 안정 구간의 엉덩이 높이 기준선
            baseline_len = min(30, n // 5)
            hip_baseline = sum(hip_heights[:baseline_len]) / baseline_len
            hip_std = (sum((h - hip_baseline) ** 2 for h in hip_heights[:baseline_len]) / baseline_len) ** 0.5
            rise_threshold = hip_baseline + max(hip_std * 2.5, 0.02)
            # 엉덩이가 기준선 위로 올라가기 시작하는 첫 지점
            for i in range(baseline_len, min(n, int(n * 0.5))):
                if hip_heights[i] > rise_threshold:
                    # 3프레임 연속 상승 확인
                    if i + 3 < n and all(hip_heights[i + j] >= rise_threshold for j in range(3)):
                        hip_rise_start = i
                        break

        # 융합 점수 기반 탐색: 처음 40% 내에서 융합 점수 피크 탐색
        if fusion_score is not None and len(fusion_score) > 0:
            search_end = min(n, int(n * 0.4))
            if search_end > 10:
                search_region = fusion_score[:search_end]
                threshold = np.mean(search_region) + 1.5 * np.std(search_region)
                for i in range(search_end):
                    if search_region[i] > threshold and angles[i] < 145:
                        # 3프레임 연속 확인
                        if i + 3 < search_end and all(search_region[i+j] > threshold * 0.7 for j in range(3)):
                            # 엉덩이 상승 시작점과 비교하여 더 이른 시점 선택
                            if hip_rise_start is not None:
                                return min(i, hip_rise_start)
                            return i

        # 기존 임계값 기반 (fallback)
        for i in range(n - 10):
            if angles[i] < self.SITTING_ANGLE_THRESHOLD:
                increasing = all(angles[i + j] <= angles[i + j + 1] for j in range(5))
                if increasing:
                    # 엉덩이 상승 시작점과 비교
                    if hip_rise_start is not None:
                        return min(i, hip_rise_start)
                    return i

        # leg_angle 기반 감지 실패 시 엉덩이 높이 상승만으로 판단
        if hip_rise_start is not None:
            return hip_rise_start

        return 0

    def _find_stand_up_end(self, angles: List[float], torso_angles: List[float], start_idx: int,
                            fusion_score: Optional[np.ndarray] = None,
                            hip_heights: Optional[List[float]] = None) -> int:
        """일어서기 완료점 찾기 (다중신호 융합 지원 + 엉덩이 높이 검증)

        허리를 숙이기만 해도 leg_angle이 측면 시점에서 일시적으로 160°+로 보이는
        문제를 방지하기 위해, 엉덩이가 실제로 충분히 올라갔는지 확인한다.
        """
        n = len(angles)

        # 앉은 자세의 엉덩이 높이 기준선 (start_idx 부근)
        hip_baseline = 0.0
        hip_standing_threshold = 0.0
        if hip_heights and len(hip_heights) > start_idx:
            baseline_end = min(start_idx + 10, n)
            hip_baseline = sum(hip_heights[start_idx:baseline_end]) / max(1, baseline_end - start_idx)
            # 서 있을 때의 최대 엉덩이 높이 추정
            hip_max = max(hip_heights[start_idx:])
            # 앉은 높이에서 선 높이까지 변화량의 60% 이상 올라가야 실제 기립
            hip_standing_threshold = hip_baseline + (hip_max - hip_baseline) * 0.6

        def _hip_risen(idx: int) -> bool:
            """엉덩이가 충분히 올라갔는지 확인"""
            if not hip_heights or idx >= len(hip_heights):
                return True  # hip 데이터 없으면 기존 로직으로 fallback
            return hip_heights[idx] >= hip_standing_threshold

        # 융합 점수 기반: start_idx 이후 융합 점수 최대점 탐색
        if fusion_score is not None and len(fusion_score) > start_idx:
            search_end = min(n, start_idx + int(n * 0.3))
            if search_end > start_idx + 5:
                search_region = fusion_score[start_idx:search_end]
                threshold = np.mean(search_region) + 1.0 * np.std(search_region)
                for i in range(len(search_region)):
                    idx = start_idx + i
                    if search_region[i] > threshold and angles[idx] >= 145 and _hip_risen(idx):
                        return idx

        # 기존 로직 (fallback) + 엉덩이 높이 조건 추가
        for i in range(start_idx, n):
            leg_standing = angles[i] >= self.STANDING_ANGLE_THRESHOLD
            torso_upright = torso_angles[i] >= self.UPRIGHT_TORSO_THRESHOLD if i < len(torso_angles) else True
            if leg_standing and torso_upright and _hip_risen(i):
                return i

        # 엉덩이 높이 조건 없이 다리+상체만으로 재시도
        for i in range(start_idx, n):
            leg_standing = angles[i] >= self.STANDING_ANGLE_THRESHOLD
            torso_upright = torso_angles[i] >= self.UPRIGHT_TORSO_THRESHOLD if i < len(torso_angles) else True
            if leg_standing and torso_upright:
                return i

        for i in range(start_idx, n):
            if angles[i] >= self.STANDING_ANGLE_THRESHOLD:
                return i

        return min(start_idx + int(n * 0.15), n - 1)

    def _find_sit_down_start(self, angles: List[float], stand_end_idx: int,
                              fusion_score: Optional[np.ndarray] = None,
                              hip_heights: Optional[List[float]] = None) -> int:
        """앉기 시작점 찾기 - 엉덩이 높이가 내려가기 시작하는 지점

        기존 문제: leg_angle만으로 판단하면 측면 시점에서 각도가 일시적으로
        변동하여 앉기 시작을 너무 일찍/늦게 잡는 문제.

        개선: 엉덩이 높이 하강 시작점을 1차 기준으로 사용하고,
        leg_angle은 보조 검증으로 활용.
        """
        n = len(angles)
        standing_threshold = getattr(self, 'STANDING_ANGLE_THRESHOLD', 145)

        # 엉덩이 높이 기반: 영상 후반부에서 엉덩이가 내려가기 시작하는 지점
        hip_drop_idx = None
        if hip_heights and len(hip_heights) > stand_end_idx:
            # 서 있는 구간의 엉덩이 높이 기준선 (stand_end 이후 ~ 70% 구간)
            standing_region_end = min(n, int(n * 0.7))
            standing_hips = hip_heights[stand_end_idx:standing_region_end]
            if len(standing_hips) > 5:
                standing_baseline = sum(standing_hips) / len(standing_hips)
                standing_std = (sum((h - standing_baseline) ** 2 for h in standing_hips) / len(standing_hips)) ** 0.5
                # 서 있는 높이에서 유의미하게 떨어지는 지점 (기준선 - 2.5σ 또는 최소 0.03)
                drop_threshold = standing_baseline - max(standing_std * 2.5, 0.03)

                # 뒤에서부터 탐색: 엉덩이가 drop_threshold 이하로 내려간 구간의 시작점
                for i in range(n - 1, stand_end_idx, -1):
                    if hip_heights[i] >= drop_threshold:
                        # 여기서부터 앞으로 가면서 처음 떨어지는 지점이 앉기 시작
                        for j in range(i, n):
                            if hip_heights[j] < drop_threshold:
                                hip_drop_idx = j
                                break
                        break

        # leg_angle 기반 (기존 로직)
        # 뒤에서 앞으로 탐색하여 선 자세 구간의 끝 찾기
        sitting_threshold = 130
        last_sitting_idx = n - 1
        for i in range(n - 1, stand_end_idx, -1):
            if angles[i] >= sitting_threshold:
                last_sitting_idx = i
                break

        angle_sit_start = last_sitting_idx
        for i in range(last_sitting_idx, n):
            if angles[i] < standing_threshold:
                angle_sit_start = i
                break

        # 융합 점수 기반 보정 (있는 경우)
        if fusion_score is not None and len(fusion_score) > 0:
            search_start = max(stand_end_idx, int(n * 0.6))
            if search_start < n - 5:
                search_region = fusion_score[search_start:]
                threshold = np.mean(search_region) + 1.0 * np.std(search_region)
                for i in range(len(search_region) - 1, -1, -1):
                    idx = search_start + i
                    if search_region[i] > threshold and angles[idx] >= standing_threshold:
                        for j in range(idx, min(n, idx + 30)):
                            if angles[j] < standing_threshold:
                                angle_sit_start = j
                                break
                        else:
                            angle_sit_start = min(idx + 5, n - 1)
                        break

        # 결과 결합: 엉덩이 하강과 leg_angle 전환 중 더 신뢰할 수 있는 값 선택
        if hip_drop_idx is not None and hip_drop_idx > stand_end_idx:
            # 두 신호가 가까우면 (10프레임 이내) 더 늦은 시점 채택 (보수적)
            if abs(hip_drop_idx - angle_sit_start) < 10:
                sit_start = max(hip_drop_idx, angle_sit_start)
            else:
                # 멀면 엉덩이 높이 우선 (측면 leg_angle 오탐 방지)
                sit_start = hip_drop_idx
        else:
            sit_start = angle_sit_start

        # 검증: stand_end 이후여야 함
        if sit_start <= stand_end_idx:
            sit_start = max(stand_end_idx + 1, int(n * 0.85))

        return sit_start

    def _find_sit_down_end(self, angles: List[float], start_idx: int,
                            fusion_score: Optional[np.ndarray] = None,
                            hip_heights: Optional[List[float]] = None) -> int:
        """앉기 완료점 찾기 (다중신호 융합 + 엉덩이 높이 안정화 검증)

        엉덩이가 초기 앉은 높이 수준으로 돌아오고 안정되면 앉기 완료.
        """
        n = len(angles)

        # 엉덩이 높이 기반: 초기 앉은 높이 수준으로 복귀한 지점
        hip_settled_idx = None
        if hip_heights and len(hip_heights) > start_idx:
            # 초기 앉은 높이 기준 (영상 처음 ~20프레임)
            baseline_len = min(20, start_idx)
            if baseline_len > 3:
                hip_sitting_level = sum(hip_heights[:baseline_len]) / baseline_len
                hip_std = (sum((h - hip_sitting_level) ** 2 for h in hip_heights[:baseline_len]) / baseline_len) ** 0.5
                # 앉은 높이 + 여유값 이하로 안정되면 완료
                settle_threshold = hip_sitting_level + max(hip_std * 2.0, 0.02)

                for i in range(start_idx, n):
                    if hip_heights[i] <= settle_threshold:
                        # 3프레임 연속 안정 확인
                        if i + 3 < n and all(hip_heights[i + j] <= settle_threshold for j in range(3)):
                            hip_settled_idx = i
                            break

        # 융합 점수 기반: start_idx 이후에서 안정된 낮은 각도 탐색
        fusion_idx = None
        if fusion_score is not None and len(fusion_score) > start_idx:
            search_region = fusion_score[start_idx:]
            threshold = np.mean(search_region) + 0.8 * np.std(search_region)
            for i in range(len(search_region)):
                idx = start_idx + i
                if search_region[i] > threshold and angles[idx] < 135:
                    fusion_idx = idx
                    break

        # leg_angle 기반 (fallback)
        angle_idx = n - 1
        for i in range(start_idx, n):
            if angles[i] < self.SITTING_ANGLE_THRESHOLD:
                angle_idx = i
                break

        # 결과 결합: 사용 가능한 신호 중 가장 신뢰할 수 있는 값
        candidates = []
        if fusion_idx is not None:
            candidates.append(fusion_idx)
        if hip_settled_idx is not None:
            candidates.append(hip_settled_idx)
        candidates.append(angle_idx)

        # 여러 신호가 있으면 중간값 선택 (극단적 오탐 방지)
        if len(candidates) >= 2:
            candidates.sort()
            return candidates[len(candidates) // 2]
        return candidates[0]

    def _find_turn_point(self, frame_data: List[Dict], start_idx: int, end_idx: int,
                          fusion_score: Optional[np.ndarray] = None) -> int:
        """회전 시작 지점 찾기 (다중신호 융합 지원)"""
        if end_idx <= start_idx:
            return (start_idx + end_idx) // 2

        # 융합 점수 기반 탐색
        if fusion_score is not None and len(fusion_score) > end_idx:
            region = fusion_score[start_idx:end_idx]
            if len(region) > 10:
                peak_idx = int(np.argmax(region))
                peak_val = region[peak_idx]
                mean_val = np.mean(region)
                if peak_val > mean_val + 1.5 * np.std(region):
                    # 피크에서 역방향 탐색하여 시작점 찾기
                    threshold = peak_val * 0.3
                    turn_start = peak_idx
                    for i in range(peak_idx, 0, -1):
                        if region[i] < threshold:
                            turn_start = i + 1
                            break
                    return start_idx + turn_start

        directions = [f['shoulder_direction'] for f in frame_data[start_idx:end_idx]]
        if len(directions) < 10:
            return (start_idx + end_idx) // 2

        # 방향 변화량 계산
        changes = []
        window = 5
        for i in range(window, len(directions) - window):
            before = sum(directions[i - window:i]) / window
            after = sum(directions[i:i + window]) / window
            change = abs(after - before)
            changes.append((i + start_idx, change))

        if not changes:
            return (start_idx + end_idx) // 2

        # 최대 변화 지점 찾기
        max_change = max(c[1] for c in changes)
        max_change_idx = max(changes, key=lambda x: x[1])[0]

        # 최대 변화 지점에서 역방향으로 탐색하여 회전 시작점 찾기
        # 변화량이 최대값의 30% 이상인 지점까지 역추적
        threshold = max_change * 0.3
        turn_start_idx = max_change_idx

        # changes를 인덱스로 변환하여 역방향 탐색
        changes_dict = {idx: change for idx, change in changes}
        for idx in range(max_change_idx, start_idx, -1):
            if idx in changes_dict and changes_dict[idx] < threshold:
                turn_start_idx = idx + 1
                break

        return turn_start_idx

    def _moving_average(self, data: List[float], window: int) -> List[float]:
        """이동 평균 필터"""
        result = []
        half = window // 2
        for i in range(len(data)):
            start = max(0, i - half)
            end = min(len(data), i + half + 1)
            result.append(sum(data[start:end]) / (end - start))
        return result

    def _compute_signal_derivatives(self, frame_data: List[Dict], fps: float) -> Dict[str, np.ndarray]:
        """프레임 데이터에서 각 신호의 1차 미분(속도)을 계산"""
        n = len(frame_data)
        if n < 5:
            return {}

        signals = {
            'leg_angle': np.array([f['leg_angle'] for f in frame_data]),
            'hip_height': np.array([f['hip_height_normalized'] for f in frame_data]),
            'torso_angle': np.array([f.get('torso_angle', 90) for f in frame_data]),
            'head_y': np.array([f['head_y'] for f in frame_data]),
            'shoulder_dir': np.array([f['shoulder_direction'] for f in frame_data]),
        }

        derivatives = {}
        kernel = np.ones(5) / 5
        for name, signal in signals.items():
            smoothed = np.convolve(signal, kernel, mode='same')
            derivatives[name] = smoothed
            derivatives[f'{name}_velocity'] = np.gradient(smoothed) * fps

        return derivatives

    def _compute_fusion_score(self, derivatives: Dict[str, np.ndarray], boundary_type: str) -> np.ndarray:
        """단계 경계 유형별 가중 융합 점수 계산

        boundary_type:
            'stand_start' - 일어서기 시작 감지 (속도 기반)
            'stand_end' - 일어서기 완료 감지 (수준 기반)
            'sit_start' - 앉기 시작 감지 (속도 기반, 역방향)
            'sit_end' - 앉기 완료 감지 (수준 기반)
            'turn' - 회전 감지 (어깨 방향 변화율 기반)
        """
        if not derivatives:
            return np.array([])

        n = len(derivatives.get('leg_angle', []))
        if n == 0:
            return np.array([])

        def normalize(arr):
            """0~1로 정규화"""
            mn, mx = arr.min(), arr.max()
            if mx - mn < 1e-6:
                return np.zeros_like(arr)
            return (arr - mn) / (mx - mn)

        if boundary_type == 'stand_start':
            # 일어서기 시작: 다리 각도 증가 속도 + 엉덩이 상승 속도
            score = (
                0.35 * normalize(np.clip(derivatives.get('leg_angle_velocity', np.zeros(n)), 0, None)) +
                0.30 * normalize(np.clip(-derivatives.get('head_y_velocity', np.zeros(n)), 0, None)) +
                0.20 * normalize(np.clip(derivatives.get('torso_angle_velocity', np.zeros(n)), 0, None)) +
                0.15 * normalize(np.clip(derivatives.get('hip_height_velocity', np.zeros(n)), 0, None))
            )
        elif boundary_type == 'stand_end':
            # 일어서기 완료: 다리 각도 높음 + 몸통 수직 + 안정
            leg_level = normalize(derivatives.get('leg_angle', np.zeros(n)))
            torso_level = normalize(derivatives.get('torso_angle', np.zeros(n)))
            # 안정성: 속도의 절대값이 작을수록 높음
            hip_stability = normalize(1.0 / (np.abs(derivatives.get('hip_height_velocity', np.ones(n))) + 0.01))
            head_stability = normalize(1.0 / (np.abs(derivatives.get('head_y_velocity', np.ones(n))) + 0.01))
            score = 0.30 * leg_level + 0.30 * torso_level + 0.25 * hip_stability + 0.15 * head_stability
        elif boundary_type == 'turn':
            # 회전: 어깨 방향 변화율
            shoulder_vel = np.abs(derivatives.get('shoulder_dir_velocity', np.zeros(n)))
            hip_stability = normalize(1.0 / (np.abs(derivatives.get('hip_height_velocity', np.ones(n))) + 0.01))
            leg_stability = normalize(1.0 / (np.abs(derivatives.get('leg_angle_velocity', np.ones(n))) + 0.01))
            score = 0.50 * normalize(shoulder_vel) + 0.20 * hip_stability + 0.30 * leg_stability
        elif boundary_type == 'sit_start':
            # 앉기 시작: 다리 각도 감소 속도 + 엉덩이 하강 속도
            score = (
                0.35 * normalize(np.clip(-derivatives.get('leg_angle_velocity', np.zeros(n)), 0, None)) +
                0.30 * normalize(np.clip(derivatives.get('head_y_velocity', np.zeros(n)), 0, None)) +
                0.20 * normalize(np.clip(-derivatives.get('torso_angle_velocity', np.zeros(n)), 0, None)) +
                0.15 * normalize(np.clip(-derivatives.get('hip_height_velocity', np.zeros(n)), 0, None))
            )
        elif boundary_type == 'sit_end':
            # 앉기 완료: 다리 각도 낮음 + 안정
            leg_low = normalize(1.0 - normalize(derivatives.get('leg_angle', np.zeros(n))))
            hip_stability = normalize(1.0 / (np.abs(derivatives.get('hip_height_velocity', np.ones(n))) + 0.01))
            score = 0.50 * leg_low + 0.50 * hip_stability
        else:
            score = np.zeros(n)

        return score

    def _create_default_phases(self, start_time: float, phase_time: float) -> Dict:
        """기본 단계 정보 생성 (감지 실패 시)"""
        return {
            'total_duration': phase_time * 5,
            'stand_up': {'start_time': start_time, 'end_time': start_time + phase_time, 'duration': phase_time},
            'walk_out': {'start_time': start_time + phase_time, 'end_time': start_time + phase_time * 2, 'duration': phase_time},
            'turn': {'start_time': start_time + phase_time * 2, 'end_time': start_time + phase_time * 3, 'duration': phase_time},
            'walk_back': {'start_time': start_time + phase_time * 3, 'end_time': start_time + phase_time * 4, 'duration': phase_time},
            'sit_down': {'start_time': start_time + phase_time * 4, 'end_time': start_time + phase_time * 5, 'duration': phase_time}
        }

    def _get_assessment(self, total_time: float) -> str:
        """TUG 시간에 따른 평가"""
        if total_time < 10:
            return "normal"  # 정상
        elif total_time < 20:
            return "good"  # 양호
        elif total_time < 30:
            return "caution"  # 주의
        else:
            return "risk"  # 낙상 위험

    def _get_walking_frames(self, frame_data: List[Dict], phases: Dict) -> List[Dict]:
        """걷기 구간의 프레임 데이터 추출"""
        walk_start = phases['walk_out']['start_time']
        walk_end = phases['walk_back']['end_time']
        return [f for f in frame_data if walk_start <= f['time'] <= walk_end]

    def _detect_current_phase_realtime(
        self,
        leg_angle: float,
        shoulder_direction: float,
        current_time: float,
        standing_detected: bool,
        turn_detected: bool,
        sitting_started: bool,
        frame_count: int
    ) -> str:
        """실시간으로 현재 TUG 단계 감지"""
        # 아직 서지 않았으면 일어서기 단계
        if not standing_detected:
            if leg_angle < self.STANDING_ANGLE_THRESHOLD:
                return "stand_up"
            else:
                return "walk_out"  # 선 자세가 되면 걷기 시작

        # 선 이후, 회전 전이면 나가는 걷기
        if standing_detected and not turn_detected:
            return "walk_out"

        # 회전 중 (회전 직후)
        if turn_detected and not sitting_started:
            # 회전 감지 직후 몇 프레임은 turn으로 표시
            return "walk_back"

        # 앉기 시작
        if sitting_started:
            if leg_angle > self.SITTING_ANGLE_THRESHOLD:
                return "sit_down"
            else:
                return "sit_down"

        return "walk_out"

    def _get_phase_label(self, phase: str) -> str:
        """단계 코드를 한글 레이블로 변환"""
        labels = {
            "stand_up": "일어서기",
            "walk_out": "걷기 (나감)",
            "turn": "돌아서기",
            "walk_back": "걷기 (돌아옴)",
            "sit_down": "앉기"
        }
        return labels.get(phase, phase)

    def _get_detection_criteria(self) -> Dict[str, Dict]:
        """각 단계의 감지 기준 설명 반환"""
        return {
            "stand_up": {
                "label": "일어서기",
                "criteria": "다리 각도 160° 이상 + 상체 수직도 75° 이상",
                "description": "앉은 자세에서 무릎이 펴지며 일어서는 동작을 감지합니다. 다리 각도가 160° 이상이고, 상체가 거의 수직(75° 이상)이 되어야 일어서기 완료로 판단합니다.",
                "key_points": ["엉덩이 높이 상승", "무릎 각도 증가 (160° 이상)", "상체 수직화 (75° 이상)"]
            },
            "walk_out": {
                "label": "걷기 (나감)",
                "criteria": "기립 완료 (다리+상체 수직) 후 전방 이동",
                "description": "완전히 일어선 후 (다리 각도 160° 이상, 상체 75° 이상) 첫 걸음을 내딛는 시점부터 회전 전까지의 보행 구간입니다.",
                "key_points": ["선 자세 유지", "상체 직립 상태", "전방 이동", "보행 패턴"]
            },
            "turn": {
                "label": "돌아서기",
                "criteria": "어깨 방향 변화가 최대인 지점 감지",
                "description": "3m 지점에서 180° 회전하는 동작입니다. 어깨의 방향 변화율이 가장 큰 구간을 감지합니다.",
                "key_points": ["어깨 회전", "방향 전환", "균형 유지"]
            },
            "walk_back": {
                "label": "걷기 (돌아옴)",
                "criteria": "회전 완료 후 반대 방향 이동 시작",
                "description": "회전 완료 후 의자 방향으로 돌아오는 보행 구간입니다.",
                "key_points": ["선 자세 유지", "후방 이동", "의자 접근"]
            },
            "sit_down": {
                "label": "앉기",
                "criteria": "다리 각도가 160° 이상에서 120° 이하로 변화",
                "description": "선 자세에서 의자에 앉는 동작입니다. 다리 각도가 선 상태에서 앉은 상태로 변화하는 구간입니다.",
                "key_points": ["엉덩이 높이 하강", "무릎 각도 감소", "착석 완료"]
            }
        }

    def _capture_phase_frames(
        self,
        video_path: str,
        phases: Dict,
        fps: float
    ) -> Dict[str, Dict]:
        """각 단계 전환 시점의 프레임을 캡처하여 반환"""
        phase_frames = {}
        detection_criteria = self._get_detection_criteria()
        phase_order = ['stand_up', 'walk_out', 'turn', 'walk_back', 'sit_down']

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[WARNING] Cannot open video for phase frame capture: {video_path}")
            return phase_frames

        for phase_name in phase_order:
            if phase_name not in phases:
                continue

            phase_info = phases[phase_name]
            # 각 단계의 대표 시점 프레임 캡처 (단계 중간 지점)
            start_time = phase_info['start_time']
            end_time = phase_info['end_time']
            duration = phase_info['duration']

            # 단계별 최적 캡처 시점: 각 단계의 가장 대표적인 순간
            if phase_name == 'stand_up':
                # 일어서기: 60% 지점 (일어서는 동작이 명확히 보이는 순간)
                capture_time = start_time + duration * 0.6
            elif phase_name == 'sit_down':
                # 앉기: 40% 지점 (앉는 동작 초반이 더 명확)
                capture_time = start_time + duration * 0.4
            elif phase_name == 'turn':
                # 회전: 50% 지점 (최대 회전 각도)
                capture_time = start_time + duration * 0.5
            else:
                # walk_out, walk_back: 40% 지점 (안정적 보행 자세)
                capture_time = start_time + duration * 0.4

            start_frame_num = int(capture_time * fps)

            # 프레임으로 이동
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame_num)
            ret, frame = cap.read()

            if ret and frame is not None:
                # 프레임에 포즈 그리기
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.pose.process(frame_rgb)

                annotated_frame = frame.copy()
                if results.pose_landmarks is not None:
                    draw_body_landmarks(annotated_frame, results.pose_landmarks)

                # 단계 정보 오버레이 추가
                h, w = annotated_frame.shape[:2]
                criteria = detection_criteria.get(phase_name, {})

                # 단계별 색상 정의
                phase_colors_bgr = {
                    'stand_up': (128, 0, 128),    # 보라색 (BGR)
                    'walk_out': (255, 0, 0),      # 파란색
                    'turn': (0, 255, 255),        # 노란색
                    'walk_back': (0, 255, 0),     # 초록색
                    'sit_down': (203, 192, 255)   # 분홍색
                }
                label_color = phase_colors_bgr.get(phase_name, (255, 255, 255))

                # 상단 반투명 배경 추가
                overlay = annotated_frame.copy()
                cv2.rectangle(overlay, (0, 0), (w, 70), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.6, annotated_frame, 0.4, 0, annotated_frame)

                # 단계 레이블 (단계 색상으로 표시)
                label = criteria.get('label', phase_name)
                cv2.putText(annotated_frame, f"[{label}]", (10, 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, label_color, 2)

                # 시간 정보
                time_text = f"Time: {capture_time:.2f}s | Frame: {start_frame_num}"
                cv2.putText(annotated_frame, time_text, (10, 55),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

                # 프레임을 base64로 인코딩
                _, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_base64 = base64.b64encode(buffer).decode('utf-8')

                phase_frames[phase_name] = {
                    "frame": frame_base64,
                    "time": round(capture_time, 2),
                    "frame_number": start_frame_num,
                    "label": criteria.get('label', phase_name),
                    "criteria": criteria.get('criteria', ''),
                    "description": criteria.get('description', ''),
                    "key_points": criteria.get('key_points', []),
                    "duration": round(phase_info['duration'], 2)
                }

        cap.release()
        return phase_frames

    def _capture_phase_clips(
        self,
        video_path: str,
        phases: Dict,
        fps: float,
        clip_padding: float = 0.5,
        output_dir: str = None
    ) -> Dict[str, Dict]:
        """각 단계 전체 구간 + 앞뒤 패딩의 MP4 클립 생성"""
        phase_clips = {}
        phase_order = ['stand_up', 'walk_out', 'turn', 'walk_back', 'sit_down']

        if output_dir is None:
            output_dir = os.path.dirname(video_path)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return phase_clips

        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = int(fps * 20) if fps > 0 else 600
        total_duration = total_frames / fps if fps > 0 else 0

        base_name = os.path.splitext(os.path.basename(video_path))[0]

        for phase_name in phase_order:
            if phase_name not in phases:
                continue

            phase_info = phases[phase_name]
            if not isinstance(phase_info, dict):
                continue

            # 단계 전체 구간 + 앞뒤 패딩
            phase_start = phase_info.get('start_time', 0)
            phase_end = phase_info.get('end_time', phase_start)
            clip_start = max(0, phase_start - clip_padding)
            clip_end = min(total_duration, phase_end + clip_padding)

            start_frame = int(clip_start * fps)
            end_frame = min(int(clip_end * fps), total_frames)

            if end_frame <= start_frame:
                continue

            # MP4 클립 파일 생성
            clip_filename = f"{base_name}_phase_{phase_name}.mp4"
            clip_path = os.path.join(output_dir, clip_filename)

            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            writer = cv2.VideoWriter(clip_path, fourcc, fps, (frame_width, frame_height))
            if not writer.isOpened():
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                writer = cv2.VideoWriter(clip_path, fourcc, fps, (frame_width, frame_height))

            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

            # 포즈 오버레이와 함께 프레임 쓰기
            thumbnail_b64 = ""
            for frame_idx in range(start_frame, end_frame):
                ret, frame = cap.read()
                if not ret:
                    break

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.pose.process(frame_rgb)

                annotated = frame.copy()
                if results.pose_landmarks:
                    draw_body_landmarks(annotated, results.pose_landmarks)

                writer.write(annotated)

                # 첫 프레임을 썸네일로 저장
                if frame_idx == start_frame:
                    _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    thumbnail_b64 = base64.b64encode(buffer).decode('utf-8')

            writer.release()

            # 단계 클립에 스톱워치 UI 추가
            add_tug_stopwatch(clip_path, phases, fps, frame_width, frame_height,
                              time_offset=clip_start)

            phase_clips[phase_name] = {
                "clip_filename": clip_filename,
                "start_time": round(clip_start, 2),
                "end_time": round(clip_end, 2),
                "duration": round(clip_end - clip_start, 2),
                "label": self._get_phase_label(phase_name),
                "thumbnail": thumbnail_b64
            }
            print(f"[TUG SIDE] Phase clip saved: {clip_filename} ({clip_end - clip_start:.1f}s)")

        cap.release()
        return phase_clips

    def _analyze_gait_pattern(self, frames: List[Dict]) -> Dict:
        """보행 패턴 분석"""
        if not frames:
            return {
                "shoulder_tilt_avg": 0,
                "shoulder_tilt_max": 0,
                "shoulder_tilt_direction": "균형",
                "hip_tilt_avg": 0,
                "hip_tilt_max": 0,
                "hip_tilt_direction": "균형",
                "assessment": "분석 불가"
            }

        # 어깨 기울기 분석
        shoulder_tilts = [f.get("shoulder_tilt_deg", 0) for f in frames]
        shoulder_tilt_avg = sum(shoulder_tilts) / len(shoulder_tilts)
        shoulder_tilt_max = max(abs(t) for t in shoulder_tilts)

        if shoulder_tilt_avg > 2:
            shoulder_direction = "오른쪽 높음"
        elif shoulder_tilt_avg < -2:
            shoulder_direction = "왼쪽 높음"
        else:
            shoulder_direction = "균형"

        # 골반 기울기 분석
        hip_tilts = [f.get("hip_tilt_deg", 0) for f in frames]
        hip_tilt_avg = sum(hip_tilts) / len(hip_tilts)
        hip_tilt_max = max(abs(t) for t in hip_tilts)

        if hip_tilt_avg > 2:
            hip_direction = "오른쪽 높음"
        elif hip_tilt_avg < -2:
            hip_direction = "왼쪽 높음"
        else:
            hip_direction = "균형"

        # 종합 평가
        if shoulder_tilt_max < 5 and hip_tilt_max < 5:
            assessment = "보행 자세가 안정적입니다."
        elif shoulder_tilt_max < 10 and hip_tilt_max < 10:
            assessment = "약간의 자세 불균형이 관찰됩니다."
        else:
            assessment = "자세 불균형에 주의가 필요합니다."

        return {
            "shoulder_tilt_avg": round(shoulder_tilt_avg, 1),
            "shoulder_tilt_max": round(shoulder_tilt_max, 1),
            "shoulder_tilt_direction": shoulder_direction,
            "hip_tilt_avg": round(hip_tilt_avg, 1),
            "hip_tilt_max": round(hip_tilt_max, 1),
            "hip_tilt_direction": hip_direction,
            "assessment": assessment
        }

    # ================================================================
    # 질환별 추가 임상 변수 계산 메서드
    # ================================================================

    def _calculate_clinical_variables(self, frame_data: List[Dict], phases: Dict, fps: float) -> Dict:
        """질환별 추가 임상 변수 계산 (ClinicalFlags 기반)"""
        if self._disease_profile is None:
            return {}

        flags = self._disease_profile.clinical_flags
        result = {}

        try:
            if flags.measure_arm_swing:
                result["arm_swing"] = self._calc_arm_swing(frame_data, phases, fps)

            if flags.measure_turn_velocity:
                result["peak_turn_velocity"] = self._calc_peak_turn_velocity(frame_data, phases, fps)

            if flags.measure_trunk_angular_vel:
                result["trunk_angular_velocity"] = self._calc_trunk_angular_vel(frame_data, phases, fps)

            # cadence는 10MWT 전용 - TUG에서는 계산하지 않음

            if flags.measure_foot_clearance:
                result["foot_clearance"] = self._calc_foot_clearance(frame_data, phases, fps)

            if flags.measure_step_asymmetry:
                result["step_asymmetry"] = self._calc_step_asymmetry(frame_data, phases)

            if flags.measure_sist_jerk:
                result["sist_jerk"] = self._calc_sist_jerk(frame_data, phases, fps)

            if flags.measure_joint_rom:
                result["joint_rom"] = self._calc_joint_rom(frame_data, phases)
        except Exception as e:
            print(f"[TUG] Clinical variable calculation error: {e}")

        return result

    def _get_phase_frames(self, frame_data: List[Dict], phases: Dict, phase_name: str) -> List[Dict]:
        """특정 구간의 프레임 데이터 추출"""
        if phase_name not in phases:
            return []
        phase = phases[phase_name]
        start_t = phase.get('start_time', 0)
        end_t = phase.get('end_time', 0)
        return [f for f in frame_data if start_t <= f['time'] <= end_t]

    def _get_walk_frames(self, frame_data: List[Dict], phases: Dict) -> List[Dict]:
        """walk_out + walk_back 구간 프레임"""
        walk_out = self._get_phase_frames(frame_data, phases, 'walk_out')
        walk_back = self._get_phase_frames(frame_data, phases, 'walk_back')
        return walk_out + walk_back

    def _calc_arm_swing(self, frame_data: List[Dict], phases: Dict, fps: float) -> Dict:
        """팔 흔들기 속도 및 비대칭 분석 (Wrist y좌표 변화율)

        파킨슨병 최민감 변수 (★★★). 초기 PD에서 팔 흔들기 속도 감소.
        뇌졸중에서 좌우 비대칭이 특징.
        """
        walk_frames = self._get_walk_frames(frame_data, phases)
        if len(walk_frames) < 5:
            return {"left_peak_velocity": 0, "right_peak_velocity": 0, "asymmetry_ratio": 0}

        left_wrist_y = np.array([f.get('left_wrist_y', 0) for f in walk_frames])
        right_wrist_y = np.array([f.get('right_wrist_y', 0) for f in walk_frames])

        # 속도 계산 (pixel/frame → pixel/sec)
        left_vel = np.abs(np.gradient(left_wrist_y)) * fps
        right_vel = np.abs(np.gradient(right_wrist_y)) * fps

        # 피크 속도 (상위 10% 평균)
        n_top = max(1, len(left_vel) // 10)
        left_peak = float(np.mean(np.sort(left_vel)[-n_top:]))
        right_peak = float(np.mean(np.sort(right_vel)[-n_top:]))

        # 비대칭 비율: |L-R| / max(L,R) × 100
        max_peak = max(left_peak, right_peak)
        asymmetry = abs(left_peak - right_peak) / max_peak * 100 if max_peak > 0 else 0

        return {
            "left_peak_velocity": round(left_peak, 1),
            "right_peak_velocity": round(right_peak, 1),
            "asymmetry_ratio": round(asymmetry, 1),
            "unit": "px/s"
        }

    def _calc_peak_turn_velocity(self, frame_data: List[Dict], phases: Dict, fps: float) -> Dict:
        """회전 구간 최대 각속도 (Shoulder yaw 미분)

        파킨슨/뇌졸중 핵심 변수 (★★★). 뇌졸중 회전 시간 31% 지연.
        """
        turn_frames = self._get_phase_frames(frame_data, phases, 'turn')
        if len(turn_frames) < 3:
            return {"peak_velocity_dps": 0, "turn_duration": 0}

        directions = np.array([f.get('shoulder_direction', 0) for f in turn_frames])

        # 각속도 (rad/frame → deg/sec)
        angular_vel = np.abs(np.gradient(directions)) * fps * (180.0 / math.pi)

        peak_vel = float(np.max(angular_vel))
        mean_vel = float(np.mean(angular_vel))
        turn_dur = turn_frames[-1]['time'] - turn_frames[0]['time']

        return {
            "peak_velocity_dps": round(peak_vel, 1),
            "mean_velocity_dps": round(mean_vel, 1),
            "turn_duration": round(turn_dur, 2),
            "unit": "°/s"
        }

    def _calc_trunk_angular_vel(self, frame_data: List[Dict], phases: Dict, fps: float) -> Dict:
        """체간 각속도 (기립/착석 시 Shoulder-Hip 벡터 변화율)

        낙상 예측 ★★★. SiSt amplitude가 낙상 예측 핵심.
        """
        result = {}

        for phase_name, label in [('stand_up', 'sist'), ('sit_down', 'stsi')]:
            pframes = self._get_phase_frames(frame_data, phases, phase_name)
            if len(pframes) < 3:
                result[label] = {"peak_angular_vel": 0, "mean_angular_vel": 0}
                continue

            torso_angles = np.array([f.get('torso_angle', 0) for f in pframes])

            # 각속도 (deg/frame → deg/sec)
            angular_vel = np.abs(np.gradient(torso_angles)) * fps
            peak_vel = float(np.max(angular_vel))
            mean_vel = float(np.mean(angular_vel))

            result[label] = {
                "peak_angular_vel": round(peak_vel, 1),
                "mean_angular_vel": round(mean_vel, 1),
                "unit": "°/s"
            }

        return result

    def _calc_cadence(self, frame_data: List[Dict], phases: Dict, fps: float) -> Dict:
        """분당 걸음수 (Ankle y좌표 peak counting)

        Walk 구간에서 발목 y좌표의 local minimum (heel strike) 카운트.
        """
        walk_frames = self._get_walk_frames(frame_data, phases)
        if len(walk_frames) < 10:
            return {"steps_per_minute": 0, "step_count": 0}

        # 양 발목 y좌표 평균
        ankle_y = np.array([(f.get('left_ankle_y', 0) + f.get('right_ankle_y', 0)) / 2
                            for f in walk_frames])

        if np.std(ankle_y) < 1:
            return {"steps_per_minute": 0, "step_count": 0}

        # 스무딩
        kernel = min(5, len(ankle_y) // 3)
        if kernel >= 3:
            ankle_y_smooth = np.convolve(ankle_y, np.ones(kernel) / kernel, mode='same')
        else:
            ankle_y_smooth = ankle_y

        # Local maxima 감지 (y좌표가 아래가 양수이므로, max = heel strike)
        step_count = 0
        for i in range(1, len(ankle_y_smooth) - 1):
            if ankle_y_smooth[i] > ankle_y_smooth[i-1] and ankle_y_smooth[i] > ankle_y_smooth[i+1]:
                # prominence 체크
                prominence = ankle_y_smooth[i] - min(ankle_y_smooth[max(0,i-5):i+6])
                if prominence > np.std(ankle_y_smooth) * 0.3:
                    step_count += 1

        # 보행 시간
        walk_duration = walk_frames[-1]['time'] - walk_frames[0]['time']
        steps_per_min = step_count / walk_duration * 60 if walk_duration > 0 else 0

        return {
            "steps_per_minute": round(steps_per_min, 1),
            "step_count": step_count,
            "walk_duration_sec": round(walk_duration, 2)
        }

    def _calc_foot_clearance(self, frame_data: List[Dict], phases: Dict, fps: float) -> Dict:
        """발 높이 측정 (swing phase에서 Foot y좌표 peak)

        파킨슨 shuffling 반영 (★★☆). 발이 지면에 가까울수록 위험.
        """
        walk_frames = self._get_walk_frames(frame_data, phases)
        if len(walk_frames) < 10:
            return {"mean_clearance_px": 0, "min_clearance_px": 0}

        left_foot_y = np.array([f.get('left_foot_y', 0) for f in walk_frames])
        right_foot_y = np.array([f.get('right_foot_y', 0) for f in walk_frames])

        # y가 아래가 양수이므로, 발이 올라갈 때 y가 작아짐
        # baseline (지면) = 가장 큰 y값
        left_baseline = np.percentile(left_foot_y[left_foot_y > 0], 95) if np.any(left_foot_y > 0) else 0
        right_baseline = np.percentile(right_foot_y[right_foot_y > 0], 95) if np.any(right_foot_y > 0) else 0

        # clearance = baseline - y (높이)
        left_clearance = left_baseline - left_foot_y
        right_clearance = right_baseline - right_foot_y

        # swing phase만 (clearance > 0인 구간)
        left_swings = left_clearance[left_clearance > 0]
        right_swings = right_clearance[right_clearance > 0]

        all_swings = np.concatenate([left_swings, right_swings]) if len(left_swings) > 0 or len(right_swings) > 0 else np.array([0])

        mean_clearance = float(np.mean(all_swings)) if len(all_swings) > 0 else 0
        min_clearance = float(np.min(all_swings)) if len(all_swings) > 0 else 0
        max_clearance = float(np.max(all_swings)) if len(all_swings) > 0 else 0

        return {
            "mean_clearance_px": round(mean_clearance, 1),
            "min_clearance_px": round(min_clearance, 1),
            "max_clearance_px": round(max_clearance, 1),
            "unit": "px"
        }

    def _calc_step_asymmetry(self, frame_data: List[Dict], phases: Dict) -> Dict:
        """좌우 보폭 비대칭 측정

        뇌졸중 핵심 변수 (★★★). ML pelvic displacement 낙상 예측인자.
        |L_step - R_step| / (L_step + R_step) × 100
        """
        walk_frames = self._get_walk_frames(frame_data, phases)
        if len(walk_frames) < 10:
            return {"asymmetry_pct": 0, "left_step_count": 0, "right_step_count": 0}

        left_ankle_y = np.array([f.get('left_ankle_y', 0) for f in walk_frames])
        right_ankle_y = np.array([f.get('right_ankle_y', 0) for f in walk_frames])

        # 스무딩
        kernel = min(5, len(left_ankle_y) // 3)
        if kernel >= 3:
            left_smooth = np.convolve(left_ankle_y, np.ones(kernel) / kernel, mode='same')
            right_smooth = np.convolve(right_ankle_y, np.ones(kernel) / kernel, mode='same')
        else:
            left_smooth = left_ankle_y
            right_smooth = right_ankle_y

        # 각 발의 heel strike (local max of y) 간격
        def count_peaks(arr):
            peaks = []
            for i in range(1, len(arr) - 1):
                if arr[i] > arr[i-1] and arr[i] > arr[i+1]:
                    prominence = arr[i] - min(arr[max(0,i-5):i+6])
                    if prominence > np.std(arr) * 0.3:
                        peaks.append(i)
            return peaks

        left_peaks = count_peaks(left_smooth)
        right_peaks = count_peaks(right_smooth)

        left_count = len(left_peaks)
        right_count = len(right_peaks)
        total = left_count + right_count

        asymmetry = abs(left_count - right_count) / total * 100 if total > 0 else 0

        return {
            "asymmetry_pct": round(asymmetry, 1),
            "left_step_count": left_count,
            "right_step_count": right_count
        }

    def _calc_sist_jerk(self, frame_data: List[Dict], phases: Dict, fps: float) -> Dict:
        """기립/착석 동작 부드러움 (Hip y좌표 3차 미분 RMS)

        낙상 위험 변수 (★★☆). Jerk가 높을수록 동작이 불안정.
        """
        result = {}

        for phase_name, label in [('stand_up', 'sist'), ('sit_down', 'stsi')]:
            pframes = self._get_phase_frames(frame_data, phases, phase_name)
            if len(pframes) < 5:
                result[label] = {"jerk_rms": 0, "smoothness_score": 0}
                continue

            hip_y = np.array([f.get('hip_y', 0) for f in pframes])

            # 1차 미분: velocity
            vel = np.gradient(hip_y) * fps
            # 2차 미분: acceleration
            acc = np.gradient(vel) * fps
            # 3차 미분: jerk
            jerk = np.gradient(acc) * fps

            jerk_rms = float(np.sqrt(np.mean(jerk ** 2)))

            # smoothness score: 0~100 (낮은 jerk = 높은 점수)
            # 경험적으로 jerk_rms < 1000이면 매우 부드러움
            smoothness = max(0, min(100, 100 - jerk_rms / 100))

            result[label] = {
                "jerk_rms": round(jerk_rms, 1),
                "smoothness_score": round(smoothness, 1),
                "unit": "px/s³"
            }

        return result

    def _calc_joint_rom(self, frame_data: List[Dict], phases: Dict) -> Dict:
        """관절 가동범위 (ROM) 측정

        슬관절 OA: Knee ROM (Hip-Knee-Ankle) 핵심 (★★☆)
        고관절 OA: Hip ROM (Shoulder-Hip-Knee) 핵심 (★★☆)
        """
        walk_frames = self._get_walk_frames(frame_data, phases)
        if len(walk_frames) < 5:
            return {"knee_rom": {}, "hip_rom": {}}

        # 슬관절 ROM (Knee: Hip-Knee-Ankle angle)
        left_knee_angles = [f.get('left_knee_angle', 0) for f in walk_frames if f.get('left_knee_angle', 0) > 0]
        right_knee_angles = [f.get('right_knee_angle', 0) for f in walk_frames if f.get('right_knee_angle', 0) > 0]

        left_knee_rom = max(left_knee_angles) - min(left_knee_angles) if left_knee_angles else 0
        right_knee_rom = max(right_knee_angles) - min(right_knee_angles) if right_knee_angles else 0

        # 고관절 ROM (Hip: Shoulder-Hip-Knee angle)
        left_hip_angles = [f.get('left_hip_angle', 0) for f in walk_frames if f.get('left_hip_angle', 0) > 0]
        right_hip_angles = [f.get('right_hip_angle', 0) for f in walk_frames if f.get('right_hip_angle', 0) > 0]

        left_hip_rom = max(left_hip_angles) - min(left_hip_angles) if left_hip_angles else 0
        right_hip_rom = max(right_hip_angles) - min(right_hip_angles) if right_hip_angles else 0

        return {
            "knee_rom": {
                "left": round(left_knee_rom, 1),
                "right": round(right_knee_rom, 1),
                "mean": round((left_knee_rom + right_knee_rom) / 2, 1),
                "unit": "°"
            },
            "hip_rom": {
                "left": round(left_hip_rom, 1),
                "right": round(right_hip_rom, 1),
                "mean": round((left_hip_rom + right_hip_rom) / 2, 1),
                "unit": "°"
            }
        }
