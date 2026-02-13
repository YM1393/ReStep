import os
import cv2
import numpy as np
import math
from typing import Dict, List, Tuple, Optional, Set, FrozenSet

import mediapipe as mp
from scipy.signal import find_peaks


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


class GaitAnalyzer:
    """
    MediaPipe Pose Heavy를 사용한 10m 보행 분석기 (전면/후면 촬영 버전)

    모델: MediaPipe Pose Heavy (model_complexity=2)
    - model_complexity=0: Lite (가장 빠름, 정확도 낮음)
    - model_complexity=1: Full (균형잡힌 속도/정확도)
    - model_complexity=2: Heavy (가장 정확, 느림) ← 사용중

    33개의 키포인트를 감지하며 정밀한 포즈 추정 제공

    전면/후면에서 촬영된 영상을 분석하여:
    1. 환자가 카메라 방향으로 접근/이탈하는 것을 감지
    2. 실제 속도(1/h 미분) 기반 보행 구간 감지
    3. 핀홀 카메라 모델로 2m~12m 구간 매핑
    4. 보행 패턴 분석 (어깨 기울기 등)

    측정 구간:
    - 총 12m 보행 (2m 가속 + 10m 측정)
    - 1/h (pixel height 역수)는 실제 거리에 비례 → d(1/h)/dt는 실제 속도에 비례
    - 실제 속도 기반으로 보행 구간 감지 (pixel velocity보다 정확)
    - 보행 구간 내 1/h 선형 보간으로 2m 지점 결정
    """

    # MediaPipe Pose 모델 복잡도 (0: Lite, 1: Full, 2: Heavy)
    MODEL_COMPLEXITY = 2  # Heavy - 가장 정확한 모델

    # 측정 설정
    CAMERA_DISTANCE_M = 14.0      # 카메라와 시작점 사이 거리 (m)
    ACCEL_ZONE_M = 1.6            # 가속 구간 (1.6m) - walked_distance_m 기반 폴백용
    MEASUREMENT_DISTANCE_M = 10.0  # 실제 측정 거리 (10m)
    TOTAL_WALK_DISTANCE_M = 12.0   # 총 보행 거리 (2m 가속 + 10m 측정 = 12m)

    # v8 최적화: inv_h 곡선의 시작 분율 (LOO MAE=0.018s, v7: 0.069s)
    # 물리적 의미: inv_h 변화의 60% 지점(≈7.2m)부터 끝까지 측정 후 보정
    # 초반 가속/근거리 노이즈를 회피하여 정확도 대폭 향상
    INV_H_START_FRACTION = 0.60

    # 방향별 보정 계수 (v8: 새 캐시 기반 재최적화)
    CORRECTION_FACTOR_AWAY = 2.4974    # 멀어지는 방향 (v7: 2.4879)
    CORRECTION_FACTOR_TOWARD = 0.63    # 다가오는 방향 (toward는 별도 로직)

    # v8 최적화 파라미터 (실제 속도 기반 보행 감지)
    VEL_THRESHOLD_PCT = 27        # 실제 속도 임계값 (v7: 23%)
    SMOOTH_MEDIAN_WS = 9          # 미디안 필터 윈도우
    SMOOTH_AVG_WS = 15            # 이동평균 윈도우
    VEL_PERCENTILE = 82           # max_rv 계산시 82th percentile 사용 (v7: 86)
    VEL_END_FACTOR = 1.7          # walk_end threshold 배수 (v7: 1.9)
    VEL_ITERATIVE = True          # 2-pass 반복 정제

    # MediaPipe Pose 키포인트 인덱스 (33개 관절점)
    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22
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

    def __init__(self, model_path: str = None, camera_distance_m: float = None, disease_profile=None):
        """
        MediaPipe Pose Heavy 모델 초기화

        Args:
            model_path: 사용하지 않음 (MediaPipe는 내장 모델 사용)
            camera_distance_m: 카메라와 시작점 사이 거리 (기본값: 14m)
            disease_profile: 질환별 분석 프로파일 (DiseaseProfile)
        """
        if camera_distance_m is not None:
            self.CAMERA_DISTANCE_M = camera_distance_m

        # 질환별 프로파일 적용
        self._disease_profile = disease_profile
        if disease_profile is not None:
            gp = disease_profile.gait
            self.VEL_THRESHOLD_PCT = gp.vel_threshold_pct
            self.SMOOTH_MEDIAN_WS = gp.smooth_median_ws
            self.SMOOTH_AVG_WS = gp.smooth_avg_ws
            self.VEL_PERCENTILE = gp.vel_percentile
            self.VEL_END_FACTOR = gp.vel_end_factor
            self.VEL_ITERATIVE = gp.vel_iterative
            self.INV_H_START_FRACTION = gp.inv_h_start_fraction
            self.CORRECTION_FACTOR_AWAY = gp.correction_factor_away
            self.CORRECTION_FACTOR_TOWARD = gp.correction_factor_toward
            print(f"[GAIT] Disease profile applied: {disease_profile.display_name} ({disease_profile.name})")

        print(f"Loading MediaPipe Pose Heavy model (model_complexity={self.MODEL_COMPLEXITY})")
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=self.MODEL_COMPLEXITY,  # Heavy 모델
            smooth_landmarks=True,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.model_name = f"MediaPipe Pose Heavy (complexity={self.MODEL_COMPLEXITY})"

    def analyze(self, video_path: str, patient_height_cm: float, progress_callback=None, walking_direction: str = None, frame_callback=None, save_overlay_video: bool = True) -> Dict:
        """
        동영상 분석 메인 함수 (전면/후면 촬영용)

        Args:
            video_path: 동영상 파일 경로
            patient_height_cm: 환자의 실제 키 (cm)
            progress_callback: 진행률 콜백 함수 (0-100 사이의 정수를 인자로 받음)
            walking_direction: 보행 방향 (None=자동감지, "toward"=카메라로 접근, "away"=카메라에서 이탈)
            frame_callback: 프레임 콜백 함수 (포즈가 그려진 프레임을 인자로 받음)
            save_overlay_video: 포즈 오버레이 영상 저장 여부

        Returns:
            분석 결과 딕셔너리
        """
        # 진행률 직접 상태 파일에 기록 (tests.py의 update_progress 우회)
        import json as _json
        import glob as _glob

        _status_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads', 'status')
        _resolved_fid = [None]

        try:
            candidates = sorted(
                _glob.glob(os.path.join(_status_dir, '*.json')),
                key=lambda x: os.path.getmtime(x), reverse=True
            )
            for c in candidates[:5]:
                with open(c, 'r', encoding='utf-8') as f:
                    data = _json.load(f)
                if data.get('status') == 'processing' and data.get('progress', 0) <= 10:
                    _resolved_fid[0] = os.path.basename(c).replace('.json', '')
                    print(f"[GAIT] Auto-detected file_id: {_resolved_fid[0]}")
                    break
        except Exception as e:
            print(f"[GAIT] file_id auto-detect failed: {e}")

        _original_callback = progress_callback

        def progress_callback(progress):
            fid = _resolved_fid[0]
            if fid:
                if progress < 30:
                    msg = "동영상 프레임 분석 중..."
                elif progress < 70:
                    msg = "포즈 데이터 추출 중..."
                else:
                    msg = "보행 패턴 분석 중..."
                try:
                    with open(os.path.join(_status_dir, f'{fid}.json'), 'w', encoding='utf-8') as f:
                        _json.dump({"status": "processing", "progress": progress, "message": msg, "current_frame": None}, f, ensure_ascii=False)
                except:
                    pass
            if _original_callback:
                try:
                    _original_callback(progress)
                except:
                    pass

        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"동영상을 열 수 없습니다: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # 일부 동영상(iPhone MOV 등)은 total_frames가 0으로 반환됨 → fps 기반 추정
        if total_frames <= 0:
            total_frames = int(fps * 20) if fps > 0 else 600
            print(f"[GAIT] Estimated total_frames={total_frames} (original was 0)")
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
            print(f"[GAIT] Saving overlay video to: {overlay_video_path}")

        # ArUco 마커 감지 (별도 1차 패스)
        aruco_calibration = None
        aruco_markers_detected = 0
        try:
            from analysis.aruco_detector import ArucoCalibration
            aruco_cal = ArucoCalibration()
            marker_positions, marker_sizes = aruco_cal.detect_in_video(video_path)
            aruco_markers_detected = len(marker_positions)
            if aruco_markers_detected >= 2:
                aruco_calibration = aruco_cal.compute_calibration(
                    marker_positions, marker_sizes, frame_height,
                    patient_height_m=patient_height_cm / 100.0)
                if aruco_calibration:
                    print(f"[ARUCO] Calibration successful with {aruco_markers_detected} markers")
                else:
                    print(f"[ARUCO] Calibration fitting failed, falling back to proportional")
            else:
                print(f"[ARUCO] Insufficient markers ({aruco_markers_detected}), "
                      f"falling back to proportional correction")
        except Exception as e:
            print(f"[ARUCO] Detection failed: {e}, falling back to proportional correction")

        # 프레임별 데이터 수집
        frame_data = []
        pose_3d_frames = []  # 3D 월드 랜드마크 (매 5프레임)
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # MediaPipe Pose 추론 (RGB 변환 필요)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)

            # 포즈 오버레이 프레임 생성 (얼굴 제외, 몸체만)
            annotated_frame = frame.copy()
            if results.pose_landmarks is not None:
                draw_body_landmarks(annotated_frame, results.pose_landmarks)

            # 오버레이 영상 저장
            if video_writer is not None:
                video_writer.write(annotated_frame)

            # 프레임 콜백 호출 (매 3프레임마다 - 실시간 미리보기용)
            if frame_callback and frame_count % 3 == 0:
                try:
                    frame_callback(annotated_frame)
                    if frame_count % 30 == 0:
                        print(f"[GAIT] Frame callback called for frame {frame_count}")
                except Exception as e:
                    print(f"[GAIT ERROR] Frame callback failed: {e}")

            if results.pose_landmarks is not None:
                # 프레임 크기 가져오기
                h, w = frame.shape[:2]
                # 랜드마크를 픽셀 좌표로 변환
                keypoints = np.array([
                    [lm.x * w, lm.y * h] for lm in results.pose_landmarks.landmark
                ])
                data = self._extract_frame_data(keypoints, frame_count, fps)
                if data:
                    frame_data.append(data)

                # 3D 월드 랜드마크 추출 (매 5프레임마다, 몸체만)
                if results.pose_world_landmarks and frame_count % 5 == 0:
                    world_lms = results.pose_world_landmarks.landmark
                    pose_3d_frames.append({
                        "time": round(frame_count / fps, 3),
                        "landmarks": [
                            [round(world_lms[i].x, 4), round(world_lms[i].y, 4), round(world_lms[i].z, 4)]
                            for i in range(11, 33)
                        ]
                    })

            frame_count += 1

            # 진행률 콜백 호출 (10% ~ 80% 범위로 매핑)
            if progress_callback and total_frames > 0:
                progress = 10 + int((frame_count / total_frames) * 70)
                progress_callback(progress)

        cap.release()

        # 오버레이 비디오 저장 완료
        if video_writer is not None:
            video_writer.release()
            print(f"[GAIT] Overlay video saved: {overlay_video_path}")

        if len(frame_data) < 10:
            raise ValueError("충분한 포즈 데이터를 감지하지 못했습니다.")

        # 보행 방향: away 고정 (v8: toward 방향 미지원)
        direction = "away"
        print(f"[DEBUG] Walking direction: {direction}")

        # v5 최적화: 실제 속도(1/h 미분) 기반 보행 감지 + 핀홀 모델 거리 매핑
        heights = [f["pixel_height"] for f in frame_data]
        times = [f["time"] for f in frame_data]

        # 스무딩: 미디안 필터 + 이동 평균
        smoothed_heights = self._median_filter(heights, self.SMOOTH_MEDIAN_WS)
        smoothed_heights = self._moving_avg(smoothed_heights, self.SMOOTH_AVG_WS)

        # 1/h 계산 (실제 거리에 비례)
        inv_h = [1.0 / max(h, 1.0) for h in smoothed_heights]

        # 실제 속도 계산: d(1/h)/dt (거리에 무관하게 일정)
        real_vel = self._compute_real_velocity(inv_h, times)

        # 실제 속도 기반 보행 구간 감지
        walk_start_idx, walk_end_idx = self._find_walk_region_real_velocity(
            real_vel, times, self.VEL_THRESHOLD_PCT)

        print(f"[DEBUG] Walk region: [{times[walk_start_idx]:.2f}s - {times[walk_end_idx]:.2f}s] "
              f"= {times[walk_end_idx] - times[walk_start_idx]:.2f}s")

        # 1/h 기반 2m/12m 지점 찾기
        inv_h_start = inv_h[walk_start_idx]
        inv_h_end = inv_h[walk_end_idx]
        total_inv_h_change = inv_h_end - inv_h_start

        calibration_method = "proportional"
        time_2m = None
        time_12m = None
        idx_2m = walk_start_idx

        # ArUco 캘리브레이션이 있으면 사용 (START=2m, FINISH=12m)
        if aruco_calibration is not None:
            aruco_time_2m = aruco_calibration.find_time_at_marker(
                0, inv_h, times,  # marker_id=0 (START, 2m)
                walk_start_idx, walk_end_idx, inv_h_start, inv_h_end,
                direction=direction)
            aruco_time_12m = aruco_calibration.find_time_at_marker(
                1, inv_h, times,  # marker_id=1 (FINISH, 12m)
                walk_start_idx, walk_end_idx, inv_h_start, inv_h_end,
                direction=direction)

            if aruco_time_2m is not None and aruco_time_12m is not None:
                time_2m = aruco_time_2m
                time_12m = aruco_time_12m
                calibration_method = "aruco"
                # idx_2m 찾기 (캡처 프레임용)
                for i in range(walk_start_idx, walk_end_idx):
                    if times[i] >= time_2m:
                        idx_2m = i
                        break
                print(f"[ARUCO] Using ArUco calibration: t_2m={time_2m:.2f}s, t_12m={time_12m:.2f}s")
            else:
                print(f"[ARUCO] ArUco time interpolation failed, falling back to proportional")

        # ArUco 실패 시 기존 비례 보간 방식 사용
        if calibration_method == "proportional":
            if total_inv_h_change > 0:
                inv_h_at_2m = inv_h_start + self.INV_H_START_FRACTION * total_inv_h_change

                for i in range(walk_start_idx, walk_end_idx):
                    if inv_h[i] <= inv_h_at_2m and inv_h[i + 1] > inv_h_at_2m:
                        ratio = (inv_h_at_2m - inv_h[i]) / (inv_h[i + 1] - inv_h[i])
                        time_2m = times[i] + ratio * (times[i + 1] - times[i])
                        idx_2m = i
                        break
                    elif inv_h[i] >= inv_h_at_2m:
                        time_2m = times[i]
                        idx_2m = i
                        break

            if time_2m is None:
                time_2m = times[walk_start_idx]
                idx_2m = walk_start_idx

            time_12m = times[walk_end_idx]

        # raw 10m 보행 시간
        raw_walk_time = time_12m - time_2m

        # 보정 계수: ArUco는 1.0, 비례 방식은 방향별 보정
        if calibration_method == "aruco":
            correction_factor = 1.0
        else:
            correction_factor = self.CORRECTION_FACTOR_AWAY
        walk_time_seconds = raw_walk_time * correction_factor

        walk_speed_mps = self.MEASUREMENT_DISTANCE_M / walk_time_seconds if walk_time_seconds > 0 else 0
        print(f"[DEBUG] t_2m={time_2m:.2f}s, t_12m={time_12m:.2f}s, Raw 10m: {raw_walk_time:.2f}s, "
              f"Correction: {correction_factor}, Method: {calibration_method}, Final: {walk_time_seconds:.2f}s")

        # 프레임 인덱스를 frame_data 인덱스로 변환 (기존 호환성)
        start_frame_data = frame_data[idx_2m]
        end_frame_data = frame_data[walk_end_idx]

        # 측정 구간 내 보행 패턴 분석
        measurement_frames = frame_data[walk_start_idx:walk_end_idx + 1]
        gait_pattern = self._analyze_gait_pattern(measurement_frames)

        # 디버그 정보를 파일로 저장
        debug_info = {
            "total_frames": total_frames,
            "fps": fps,
            "video_duration": round(total_frames/fps, 2),
            "frames_with_pose": len(frame_data),
            "walk_start_frame": start_frame_data['frame'],
            "walk_start_time": round(start_frame_data['time'], 2),
            "walk_end_frame": end_frame_data['frame'],
            "walk_end_time": round(end_frame_data['time'], 2),
            "raw_walk_time": round(raw_walk_time, 2),
            "correction_factor": correction_factor,
            "walk_time_seconds": round(walk_time_seconds, 2),
            "walk_speed_mps": round(walk_speed_mps, 2),
            "walking_direction": direction
        }

        # 디버그 파일 저장
        import json as debug_json
        debug_path = os.path.join(os.path.dirname(video_path), "debug_analysis.json")
        with open(debug_path, 'w', encoding='utf-8') as f:
            debug_json.dump(debug_info, f, indent=2, ensure_ascii=False)

        print(f"[DEBUG] Analysis debug saved to: {debug_path}")

        # 프레임별 각도 데이터 추출 (그래프용)
        angle_data = []
        for f in measurement_frames:
            angle_data.append({
                "time": round(f["time"] - start_frame_data["time"], 2),  # 상대 시간
                "shoulder_tilt": round(f.get("shoulder_tilt_deg", 0), 1),
                "hip_tilt": round(f.get("hip_tilt_deg", 0), 1)
            })

        # 오버레이 영상 파일명
        overlay_video_filename = os.path.basename(overlay_video_path) if overlay_video_path else None

        result = {
            "walk_time_seconds": round(walk_time_seconds, 2),
            "walk_speed_mps": round(walk_speed_mps, 2),
            "fps": fps,
            "total_frames": total_frames,
            "start_frame": start_frame_data["frame"],
            "end_frame": end_frame_data["frame"],
            "patient_height_cm": patient_height_cm,
            "frames_analyzed": len(frame_data),
            "model": self.model_name,
            "video_duration": round(total_frames/fps, 2),
            "walking_direction": direction,
            "measurement_zone": {
                "start_distance_m": self.ACCEL_ZONE_M,
                "end_distance_m": self.TOTAL_WALK_DISTANCE_M,
                "measured_distance_m": self.MEASUREMENT_DISTANCE_M
            },
            "gait_pattern": gait_pattern,
            "angle_data": angle_data,
            "overlay_video_filename": overlay_video_filename,
            "calibration_method": calibration_method,
            "aruco_markers_detected": aruco_markers_detected,
            "disease_profile": self._disease_profile.name if self._disease_profile else "default",
            "disease_profile_display": self._disease_profile.display_name if self._disease_profile else "기본",
            "clinical_variables": self._calculate_clinical_variables(
                frame_data, walk_start_idx, walk_end_idx, fps
            ),
            "confidence_score": self._calculate_confidence_score(
                len(frame_data), total_frames, walk_time_seconds, walk_speed_mps,
                times[walk_end_idx] - times[walk_start_idx]
            ),
            "asymmetry_warnings": [],
            "pose_3d_frames": pose_3d_frames if pose_3d_frames else None,
        }

        # stride_length 계산 (walk_speed × stride_time)
        cv = result.get("clinical_variables", {})
        stride_time_data = cv.get("stride_time")
        if stride_time_data and stride_time_data.get("mean", 0) > 0:
            sl = walk_speed_mps * stride_time_data["mean"]
            cv["stride_length"] = {"value": round(sl, 3), "unit": "m"}

        # 비대칭 경고 계산
        result["asymmetry_warnings"] = self._calculate_asymmetry_warnings(cv)

        return result

    def _calculate_confidence_score(
        self,
        frames_analyzed: int,
        total_frames: int,
        walk_time: float,
        walk_speed: float,
        walk_duration: float
    ) -> Dict:
        """분석 결과 신뢰도 점수 산출 (0~100)"""
        details = {}

        # 1. 포즈 감지율 (30점)
        detection_rate = frames_analyzed / max(total_frames, 1)
        if detection_rate >= 0.95:
            pose_score = 30
        elif detection_rate >= 0.85:
            pose_score = 25
        elif detection_rate >= 0.70:
            pose_score = 18
        else:
            pose_score = max(0, int(detection_rate * 30))
        details["pose_detection"] = {"score": pose_score, "max": 30,
                                      "rate": round(detection_rate * 100, 1)}

        # 2. 보행 구간 길이 적정성 (25점)
        if 5.0 <= walk_duration <= 18.0:
            duration_score = 25
        elif 3.0 <= walk_duration <= 25.0:
            duration_score = 18
        else:
            duration_score = 8
        details["walk_duration"] = {"score": duration_score, "max": 25,
                                     "duration": round(walk_duration, 1)}

        # 3. 보행 시간 합리성 (25점)
        if 4.0 <= walk_time <= 20.0:
            time_score = 25
        elif 2.5 <= walk_time <= 30.0:
            time_score = 15
        else:
            time_score = 5
        details["walk_time"] = {"score": time_score, "max": 25,
                                 "time": round(walk_time, 2)}

        # 4. 보행 속도 합리성 (20점)
        if 0.5 <= walk_speed <= 2.0:
            speed_score = 20
        elif 0.3 <= walk_speed <= 2.5:
            speed_score = 14
        else:
            speed_score = 5
        details["walk_speed"] = {"score": speed_score, "max": 20,
                                  "speed": round(walk_speed, 2)}

        total = pose_score + duration_score + time_score + speed_score

        # 등급
        if total >= 90:
            level = "high"
            label = "높음"
        elif total >= 70:
            level = "medium"
            label = "보통"
        elif total >= 50:
            level = "low"
            label = "낮음"
        else:
            level = "very_low"
            label = "매우 낮음"

        return {
            "score": total,
            "level": level,
            "label": label,
            "details": details
        }

    def _calculate_asymmetry_warnings(self, clinical_variables: Dict) -> list:
        """보행 비대칭 경고 생성"""
        warnings = []

        # 1. 보폭 시간 비대칭
        step_asym = clinical_variables.get("step_time_asymmetry", {})
        asym_value = step_asym.get("value", 0)
        if asym_value is not None and asym_value > 10:
            if asym_value > 30:
                severity = "severe"
                label = "심한 비대칭"
            elif asym_value > 20:
                severity = "moderate"
                label = "중등도 비대칭"
            else:
                severity = "mild"
                label = "경미한 비대칭"

            left_mean = step_asym.get("left_mean", 0)
            right_mean = step_asym.get("right_mean", 0)
            slower_side = "좌측" if left_mean > right_mean else "우측"

            warnings.append({
                "type": "step_time_asymmetry",
                "severity": severity,
                "label": f"보폭 시간 {label}",
                "value": round(asym_value, 1),
                "unit": "%",
                "description": f"{slower_side} 보폭 시간이 더 깁니다 (비대칭 {round(asym_value, 1)}%)",
                "threshold": "정상 < 10%"
            })

        # 2. 팔 스윙 비대칭
        arm_swing = clinical_variables.get("arm_swing", {})
        arm_asym = arm_swing.get("asymmetry_index", 0)
        if arm_asym is not None and arm_asym > 15:
            if arm_asym > 40:
                severity = "severe"
                label = "심한 비대칭"
            elif arm_asym > 25:
                severity = "moderate"
                label = "중등도 비대칭"
            else:
                severity = "mild"
                label = "경미한 비대칭"

            left_amp = arm_swing.get("left_amplitude", 0)
            right_amp = arm_swing.get("right_amplitude", 0)
            reduced_side = "좌측" if left_amp < right_amp else "우측"

            warnings.append({
                "type": "arm_swing_asymmetry",
                "severity": severity,
                "label": f"팔 스윙 {label}",
                "value": round(arm_asym, 1),
                "unit": "%",
                "description": f"{reduced_side} 팔 스윙 감소 (비대칭 {round(arm_asym, 1)}%)",
                "threshold": "정상 < 15%"
            })

        return warnings

    def _extract_frame_data(
        self,
        keypoints: np.ndarray,
        frame_num: int,
        fps: float
    ) -> Optional[Dict]:
        """프레임에서 필요한 데이터 추출 (전면/후면 촬영용)"""

        # 키포인트 배열 유효성 검사 (MediaPipe는 33개 키포인트)
        if keypoints is None or keypoints.size == 0 or len(keypoints) < 33:
            return None

        # 주요 키포인트 추출
        nose = keypoints[self.NOSE]
        left_ankle = keypoints[self.LEFT_ANKLE]
        right_ankle = keypoints[self.RIGHT_ANKLE]
        left_hip = keypoints[self.LEFT_HIP]
        right_hip = keypoints[self.RIGHT_HIP]
        left_shoulder = keypoints[self.LEFT_SHOULDER]
        right_shoulder = keypoints[self.RIGHT_SHOULDER]

        # 유효성 검사 완화: 코, 어깨, 엉덩이, 발목 중 최소한의 포인트만 필요
        # 머리 위치: 코 또는 어깨 중점
        if nose[0] > 0 and nose[1] > 0:
            head_y = nose[1]
        elif left_shoulder[0] > 0 and right_shoulder[0] > 0:
            head_y = (left_shoulder[1] + right_shoulder[1]) / 2
        else:
            return None

        # 하체 위치: 발목 또는 엉덩이
        if left_ankle[0] > 0 or right_ankle[0] > 0:
            if left_ankle[0] > 0 and right_ankle[0] > 0:
                foot_y = (left_ankle[1] + right_ankle[1]) / 2
            elif left_ankle[0] > 0:
                foot_y = left_ankle[1]
            else:
                foot_y = right_ankle[1]
        elif left_hip[0] > 0 or right_hip[0] > 0:
            if left_hip[0] > 0 and right_hip[0] > 0:
                foot_y = (left_hip[1] + right_hip[1]) / 2
            elif left_hip[0] > 0:
                foot_y = left_hip[1]
            else:
                foot_y = right_hip[1]
        else:
            return None

        # 어깨가 감지되지 않으면 기울기 계산 불가
        shoulder_valid = not (
            (left_shoulder[0] == 0 and left_shoulder[1] == 0) or
            (right_shoulder[0] == 0 and right_shoulder[1] == 0)
        )

        # 화면상 키 추정 (머리부터 하체까지)
        pixel_height = abs(foot_y - head_y)

        if pixel_height < 30:  # 임계값 완화 (50 -> 30)
            return None

        # 중심점 계산 (기존 코드 호환성)
        ankle_center_y = foot_y

        # 어깨 기울기 계산 (도 단위)
        shoulder_tilt_deg = 0.0
        if shoulder_valid:
            shoulder_tilt_deg = self._calculate_shoulder_tilt(left_shoulder, right_shoulder)

        # 골반 기울기 계산 (도 단위)
        hip_valid = not (
            (left_hip[0] == 0 and left_hip[1] == 0) or
            (right_hip[0] == 0 and right_hip[1] == 0)
        )
        hip_tilt_deg = 0.0
        if hip_valid:
            hip_tilt_deg = self._calculate_shoulder_tilt(left_hip, right_hip)  # 같은 로직 사용

        # 추가 임상 랜드마크 추출 (보행 이벤트 감지 + 임상 변수용)
        left_wrist = keypoints[self.LEFT_WRIST]
        right_wrist = keypoints[self.RIGHT_WRIST]
        left_foot_index = keypoints[self.LEFT_FOOT_INDEX]
        right_foot_index = keypoints[self.RIGHT_FOOT_INDEX]

        return {
            "frame": frame_num,
            "time": frame_num / fps,
            "pixel_height": pixel_height,
            "shoulder_tilt_deg": shoulder_tilt_deg,
            "hip_tilt_deg": hip_tilt_deg,
            "nose_y": nose[1],
            "ankle_y": ankle_center_y,
            "left_shoulder": left_shoulder.tolist() if shoulder_valid else None,
            "right_shoulder": right_shoulder.tolist() if shoulder_valid else None,
            # 임상 변수용 양측 분리 데이터
            "left_ankle_y": left_ankle[1],
            "right_ankle_y": right_ankle[1],
            "left_foot_y": left_foot_index[1],
            "right_foot_y": right_foot_index[1],
            "left_wrist_y": left_wrist[1],
            "right_wrist_y": right_wrist[1],
            "left_hip_y": left_hip[1],
            "right_hip_y": right_hip[1],
            "left_shoulder_y": left_shoulder[1],
            "right_shoulder_y": right_shoulder[1],
        }

    def _calculate_shoulder_tilt(self, left_point: np.ndarray, right_point: np.ndarray) -> float:
        """
        어깨/골반 기울기 계산 (도 단위)

        Returns:
            양수: 오른쪽이 높음 (왼쪽으로 기울어짐)
            음수: 왼쪽이 높음 (오른쪽으로 기울어짐)
        """
        dx = right_point[0] - left_point[0]
        dy = right_point[1] - left_point[1]  # Y축은 아래가 양수

        if abs(dx) < 1:  # 거의 수직선인 경우
            return 0.0

        # atan2를 사용하여 각도 계산 (라디안 → 도)
        # Y축이 아래로 양수이므로, dy가 양수면 오른쪽이 낮음 → 음수 반환
        angle_rad = math.atan2(-dy, dx)  # -dy로 반전
        angle_deg = math.degrees(angle_rad)

        return round(angle_deg, 1)

    def _detect_walking_direction(self, frame_data: List[Dict]) -> str:
        """
        보행 방향 감지 (카메라로 접근 vs 이탈)

        픽셀 높이가 증가하면 카메라로 접근 (toward)
        픽셀 높이가 감소하면 카메라에서 이탈 (away)
        """
        if len(frame_data) < 10:
            return "unknown"

        # 처음 1/4와 마지막 1/4의 평균 픽셀 높이 비교
        quarter = len(frame_data) // 4

        first_quarter_heights = [f["pixel_height"] for f in frame_data[:quarter]]
        last_quarter_heights = [f["pixel_height"] for f in frame_data[-quarter:]]

        avg_first = sum(first_quarter_heights) / len(first_quarter_heights)
        avg_last = sum(last_quarter_heights) / len(last_quarter_heights)

        # 픽셀 높이가 증가하면 카메라로 접근
        if avg_last > avg_first * 1.1:  # 10% 이상 증가
            return "toward"  # 카메라 방향으로 접근
        elif avg_last < avg_first * 0.9:  # 10% 이상 감소
            return "away"  # 카메라에서 멀어짐
        else:
            return "toward"  # 기본값

    def _calculate_distances(
        self,
        frame_data: List[Dict],
        patient_height_cm: float,
        direction: str
    ) -> List[Dict]:
        """
        각 프레임의 이동 거리 계산 (핀홀 카메라 모델 기반)

        핀홀 카메라 모델: distance ∝ 1/pixel_height
        - 가까울 때: 큰 픽셀 높이
        - 멀 때: 작은 픽셀 높이

        이 관계를 사용하여 12m 보행 거리를 정확히 추정합니다.
        """
        if not frame_data or len(frame_data) < 20:
            return frame_data

        # 1단계: 픽셀 높이 데이터 스무딩 (이동 중앙값 필터)
        window_size = min(15, len(frame_data) // 10)
        if window_size < 3:
            window_size = 3
        if window_size % 2 == 0:
            window_size += 1

        heights = [f["pixel_height"] for f in frame_data]
        smoothed_heights = self._median_filter(heights, window_size)

        # 2단계: 보행 구간 감지
        walk_start_idx, walk_end_idx = self._detect_walk_boundaries(smoothed_heights, direction)

        print(f"[DEBUG] Walk boundary detection: start_idx={walk_start_idx}, end_idx={walk_end_idx}")

        # 3단계: 보행 구간의 시작/끝 픽셀 높이 (안정적인 값 사용)
        start_sample_count = max(5, (walk_end_idx - walk_start_idx) // 20)
        end_sample_count = max(5, (walk_end_idx - walk_start_idx) // 20)

        start_heights = smoothed_heights[walk_start_idx:walk_start_idx + start_sample_count]
        end_heights = smoothed_heights[walk_end_idx - end_sample_count:walk_end_idx]

        h_start = sum(start_heights) / len(start_heights)  # 시작점 픽셀 높이
        h_end = sum(end_heights) / len(end_heights)        # 끝점 픽셀 높이

        print(f"[DEBUG] Start pixel height: {h_start:.1f}, End pixel height: {h_end:.1f}")

        # 4단계: 핀홀 카메라 모델을 사용한 거리 계산
        # distance = k / pixel_height (k는 상수)
        # d_start = k / h_start
        # d_end = k / h_end
        # d_end - d_start = 12m (총 보행 거리)
        #
        # k/h_end - k/h_start = 12
        # k * (1/h_end - 1/h_start) = 12
        # k = 12 / (1/h_end - 1/h_start)

        inv_h_start = 1.0 / h_start
        inv_h_end = 1.0 / h_end

        if direction == "away":
            # 멀어지면 픽셀 높이 감소 → 1/h 증가
            inv_diff = inv_h_end - inv_h_start
        else:
            # 가까워지면 픽셀 높이 증가 → 1/h 감소
            inv_diff = inv_h_start - inv_h_end

        if abs(inv_diff) < 0.0001:
            print("[WARNING] Insufficient pixel height change. Using time-based estimation.")
            walk_duration_frames = walk_end_idx - walk_start_idx
            for i, frame in enumerate(frame_data):
                if i < walk_start_idx:
                    frame["walked_distance_m"] = 0.0
                elif i > walk_end_idx:
                    frame["walked_distance_m"] = self.TOTAL_WALK_DISTANCE_M
                else:
                    progress = (i - walk_start_idx) / walk_duration_frames
                    frame["walked_distance_m"] = round(progress * self.TOTAL_WALK_DISTANCE_M, 2)
            return frame_data

        # 캘리브레이션 상수 k 계산
        k = self.TOTAL_WALK_DISTANCE_M / inv_diff

        # 시작점의 카메라 거리
        d_start = k / h_start

        print(f"[DEBUG] Calibration constant k: {k:.1f}")
        print(f"[DEBUG] Initial camera distance: {d_start:.2f}m")

        # 5단계: 각 프레임의 이동 거리 계산
        for i, frame in enumerate(frame_data):
            smoothed_height = smoothed_heights[i]

            # 현재 카메라 거리
            d_current = k / smoothed_height

            # 이동 거리 계산
            if direction == "away":
                walked_distance = d_current - d_start
            else:
                walked_distance = d_start - d_current

            # 범위 제한
            walked_distance = max(0, min(self.TOTAL_WALK_DISTANCE_M, walked_distance))

            frame["walked_distance_m"] = round(walked_distance, 2)
            frame["camera_distance_m"] = round(d_current, 2)
            frame["smoothed_pixel_height"] = round(smoothed_height, 1)

        return frame_data

    def _median_filter(self, data: List[float], window_size: int) -> List[float]:
        """이동 중앙값 필터 적용"""
        result = []
        half_window = window_size // 2

        for i in range(len(data)):
            start = max(0, i - half_window)
            end = min(len(data), i + half_window + 1)
            window = sorted(data[start:end])
            median = window[len(window) // 2]
            result.append(median)

        return result

    def _moving_avg(self, data: List[float], window_size: int) -> List[float]:
        """이동 평균 필터 적용"""
        result = []
        half = window_size // 2
        for i in range(len(data)):
            s = max(0, i - half)
            e = min(len(data), i + half + 1)
            result.append(sum(data[s:e]) / (e - s))
        return result

    def _compute_real_velocity(self, inv_h: List[float], times: List[float]) -> List[float]:
        """
        1/h의 시간 미분 = 실제 보행 속도에 비례.
        pixel velocity와 달리, 거리에 무관하게 일정한 실제 속도를 반환.
        """
        vel = [0.0]
        for i in range(1, len(inv_h)):
            dt = times[i] - times[i - 1]
            if dt > 0:
                vel.append((inv_h[i] - inv_h[i - 1]) / dt)
            else:
                vel.append(0)
        return vel

    def _find_walk_region_real_velocity(
        self, real_vel: List[float], times: List[float],
        vel_threshold_pct: float, min_walk_duration: float = 2.0
    ) -> Tuple[int, int]:
        """
        실제 속도(d(1/h)/dt) 기반 보행 구간 감지.

        v5.1 개선사항:
        - percentile 기반 max_rv (노이즈 스파이크 방지)
        - 비대칭 threshold (walk_end에 더 높은 threshold)
        - 2-pass 반복 정제 (보행 구간 내에서 max_rv 재계산)
        """
        rv_smooth = self._moving_avg(real_vel, 31)
        n = len(rv_smooth)

        # max_rv: percentile 기반 (노이즈 스파이크 제거)
        positive_rv = [v for v in rv_smooth if v > 0]
        if not positive_rv:
            return 0, n - 1
        max_rv = float(np.percentile(positive_rv, self.VEL_PERCENTILE))

        if max_rv < 1e-8:
            return 0, n - 1

        threshold_start = max_rv * vel_threshold_pct / 100.0
        threshold_end = threshold_start * self.VEL_END_FACTOR

        def _find_regions(t_start, t_end):
            regions = []
            in_region = False
            start = 0
            for i in range(n):
                if rv_smooth[i] >= t_start and not in_region:
                    start = i
                    in_region = True
                elif rv_smooth[i] < t_end and in_region:
                    if times[i - 1] - times[start] >= min_walk_duration:
                        regions.append((start, i - 1))
                    in_region = False
            if in_region:
                if times[n - 1] - times[start] >= min_walk_duration:
                    regions.append((start, n - 1))
            return regions

        regions = _find_regions(threshold_start, threshold_end)

        if not regions:
            walk_start = 0
            walk_end = n - 1
            for i in range(n):
                if rv_smooth[i] >= threshold_start:
                    walk_start = i
                    break
            for i in range(n - 1, -1, -1):
                if rv_smooth[i] >= threshold_end:
                    walk_end = i
                    break
            return walk_start, walk_end

        best = max(regions, key=lambda r: times[r[1]] - times[r[0]])
        ws, we = best

        # 2-pass 반복 정제: 보행 구간 내에서 max_rv 재계산
        if self.VEL_ITERATIVE:
            walk_rv = [v for v in rv_smooth[ws:we + 1] if v > 0]
            if walk_rv:
                max_rv2 = float(np.percentile(walk_rv, self.VEL_PERCENTILE))
                threshold_start2 = max_rv2 * vel_threshold_pct / 100.0
                threshold_end2 = threshold_start2 * self.VEL_END_FACTOR

                regions2 = _find_regions(threshold_start2, threshold_end2)
                if regions2:
                    best2 = max(regions2, key=lambda r: times[r[1]] - times[r[0]])
                    ws, we = best2

        return ws, we

    def _detect_walk_boundaries(self, heights: List[float], direction: str) -> Tuple[int, int]:
        """
        보행 시작과 종료 지점 감지 (누적 높이 변화 기반)

        알고리즘:
        1. 총 높이 변화량 계산
        2. 누적 변화량이 5%~95% 사이인 구간을 보행 구간으로 설정
        """
        n = len(heights)
        if n < 30:
            return 0, n - 1

        # 1단계: 스무딩
        window = 11
        smoothed = []
        for i in range(n):
            start = max(0, i - window // 2)
            end = min(n, i + window // 2 + 1)
            smoothed.append(sum(heights[start:end]) / (end - start))

        # 2단계: 시작점과 끝점 높이
        h_start = smoothed[0]
        h_end = smoothed[-1]
        total_change = abs(h_end - h_start)

        if total_change < 50:
            print("[WARNING] Insufficient height change")
            return 0, n - 1

        print(f"[DEBUG] Height: start={h_start:.1f}, end={h_end:.1f}, change={total_change:.1f}")

        # 3단계: 누적 변화량 계산
        # 방향에 따라 부호 결정
        if direction == "away":
            # 멀어지면 높이 감소
            cumulative = [(h_start - smoothed[i]) / total_change * 100 for i in range(n)]
        else:
            # 가까워지면 높이 증가
            cumulative = [(smoothed[i] - h_start) / total_change * 100 for i in range(n)]

        # 4단계: 15% 지점 (보행 시작)과 85% 지점 (보행 종료) 찾기
        start_percent = 15   # 시작 후 15% 지점
        end_percent = 85     # 종료 전 85% 지점

        walk_start = 0
        walk_end = n - 1

        for i in range(n):
            if cumulative[i] >= start_percent:
                walk_start = i
                break

        for i in range(n - 1, -1, -1):
            if cumulative[i] <= end_percent:
                walk_end = i
                break

        print(f"[DEBUG] Cumulative at start frame: {cumulative[walk_start]:.1f}%")
        print(f"[DEBUG] Cumulative at end frame: {cumulative[walk_end]:.1f}%")
        print(f"[DEBUG] Walk boundaries: frames {walk_start}-{walk_end} ({walk_end - walk_start} frames)")

        return walk_start, walk_end

    def _find_measurement_zone(self, frame_data: List[Dict]) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        측정 구간 (0m ~ 10m) 찾기
        움직이기 시작한 순간부터 10m까지 측정

        Returns:
            (시작 프레임 데이터, 종료 프레임 데이터)
        """
        start_frame = None
        end_frame = None

        for frame in frame_data:
            walked = frame.get("walked_distance_m", 0)

            # 측정 시작 지점 (움직이기 시작한 순간)
            if start_frame is None and walked >= self.ACCEL_ZONE_M:
                start_frame = frame

            # 10m 지점 찾기 (측정 종료)
            if walked >= self.TOTAL_WALK_DISTANCE_M:
                end_frame = frame
                break

        # 10m에 도달하지 않았으면 마지막 프레임 사용
        if start_frame is not None and end_frame is None:
            last_frame = frame_data[-1]
            # 최소 6m 이상 걸었으면 마지막 프레임 사용
            if last_frame.get("walked_distance_m", 0) >= 6:
                end_frame = last_frame
                print(f"[WARNING] 10m 미도달. 최종 거리: {last_frame.get('walked_distance_m', 0):.1f}m")

        return start_frame, end_frame

    def _analyze_gait_pattern(self, measurement_frames: List[Dict]) -> Dict:
        """
        측정 구간 내 보행 패턴 분석

        분석 항목:
        - 어깨 기울기 (평균, 최대, 방향)
        - 골반 기울기 (평균, 최대, 방향)
        """
        if not measurement_frames:
            return {
                "shoulder_tilt_avg": 0.0,
                "shoulder_tilt_max": 0.0,
                "shoulder_tilt_direction": "정상",
                "hip_tilt_avg": 0.0,
                "hip_tilt_max": 0.0,
                "hip_tilt_direction": "정상",
                "assessment": "분석 데이터 부족"
            }

        # 어깨 기울기 분석
        shoulder_tilts = [f["shoulder_tilt_deg"] for f in measurement_frames if f.get("shoulder_tilt_deg") is not None]
        hip_tilts = [f["hip_tilt_deg"] for f in measurement_frames if f.get("hip_tilt_deg") is not None]

        # 어깨 통계
        shoulder_avg = sum(shoulder_tilts) / len(shoulder_tilts) if shoulder_tilts else 0
        shoulder_max = max(abs(t) for t in shoulder_tilts) if shoulder_tilts else 0

        # 골반 통계
        hip_avg = sum(hip_tilts) / len(hip_tilts) if hip_tilts else 0
        hip_max = max(abs(t) for t in hip_tilts) if hip_tilts else 0

        # 방향 판정
        def get_tilt_direction(avg_tilt: float, threshold: float = 2.0) -> str:
            if abs(avg_tilt) < threshold:
                return "정상"
            elif avg_tilt > 0:
                return f"우측 높음 ({abs(avg_tilt):.1f}°)"
            else:
                return f"좌측 높음 ({abs(avg_tilt):.1f}°)"

        shoulder_direction = get_tilt_direction(shoulder_avg)
        hip_direction = get_tilt_direction(hip_avg)

        # 종합 평가
        assessment_items = []

        if abs(shoulder_avg) >= 5.0:
            assessment_items.append(f"어깨 기울기 주의 ({shoulder_direction})")
        elif abs(shoulder_avg) >= 2.0:
            assessment_items.append(f"어깨 경미한 기울기 ({shoulder_direction})")

        if abs(hip_avg) >= 5.0:
            assessment_items.append(f"골반 기울기 주의 ({hip_direction})")
        elif abs(hip_avg) >= 2.0:
            assessment_items.append(f"골반 경미한 기울기 ({hip_direction})")

        if not assessment_items:
            assessment = "정상 보행 패턴"
        else:
            assessment = "; ".join(assessment_items)

        return {
            "shoulder_tilt_avg": round(shoulder_avg, 1),
            "shoulder_tilt_max": round(shoulder_max, 1),
            "shoulder_tilt_direction": shoulder_direction,
            "hip_tilt_avg": round(hip_avg, 1),
            "hip_tilt_max": round(hip_max, 1),
            "hip_tilt_direction": hip_direction,
            "assessment": assessment
        }

    def get_frame_preview(self, video_path: str, frame_num: int) -> np.ndarray:
        """특정 프레임의 포즈 오버레이 이미지 반환"""
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)

        ret, frame = cap.read()
        cap.release()

        if not ret:
            raise ValueError("프레임을 읽을 수 없습니다.")

        # MediaPipe Pose 추론
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)

        if results.pose_landmarks is not None:
            # 얼굴 제외, 몸체만 그리기
            annotated_frame = frame.copy()
            draw_body_landmarks(annotated_frame, results.pose_landmarks)
            return annotated_frame

        return frame

    # ============================================================
    # 10MWT 임상 변수 계산
    # ============================================================

    def _calculate_clinical_variables(
        self, frame_data: List[Dict], walk_start_idx: int, walk_end_idx: int, fps: float
    ) -> Dict:
        """질환별 추가 임상 변수 계산 (ClinicalFlags 기반)"""
        if not self._disease_profile:
            return {}

        flags = self._disease_profile.clinical_flags
        result = {}
        walk_duration = (walk_end_idx - walk_start_idx) / fps if fps > 0 else 0

        if walk_duration < 1.0:
            return {}

        # 보행 이벤트는 여러 변수의 기반 → 필요 시 한 번만 계산
        gait_events = None
        needs_events = any([
            flags.measure_cadence, flags.measure_step_time,
            flags.measure_stride_time, flags.measure_step_time_asymmetry,
            flags.measure_double_support, flags.measure_swing_stance_ratio
        ])
        if needs_events:
            gait_events = self._detect_gait_events(frame_data, walk_start_idx, walk_end_idx, fps)

        try:
            if flags.measure_cadence and gait_events:
                result["cadence"] = self._calc_cadence(gait_events, walk_duration)

            if flags.measure_step_time and gait_events:
                result["step_time"] = self._calc_step_time(gait_events)

            if flags.measure_stride_time and gait_events:
                result["stride_time"] = self._calc_stride_time(gait_events)

            if flags.measure_step_time_asymmetry and gait_events:
                result["step_time_asymmetry"] = self._calc_step_time_asymmetry(gait_events)

            if flags.measure_arm_swing:
                result["arm_swing"] = self._calc_arm_swing(
                    frame_data, walk_start_idx, walk_end_idx, fps)

            if flags.measure_foot_clearance:
                result["foot_clearance"] = self._calc_foot_clearance(
                    frame_data, walk_start_idx, walk_end_idx, fps)

            if flags.measure_double_support and gait_events:
                result["double_support"] = self._calc_double_support(gait_events, walk_duration)

            if flags.measure_stride_regularity:
                result["stride_regularity"] = self._calc_stride_regularity(
                    frame_data, walk_start_idx, walk_end_idx, fps)

            if flags.measure_trunk_inclination:
                result["trunk_inclination"] = self._calc_trunk_inclination(
                    frame_data, walk_start_idx, walk_end_idx)

            if flags.measure_swing_stance_ratio and gait_events:
                result["swing_stance_ratio"] = self._calc_swing_stance_ratio(
                    gait_events, walk_duration)
        except Exception as e:
            print(f"[GAIT] Clinical variable calculation error: {e}")

        return result

    def _detect_gait_events(
        self, frame_data: List[Dict], walk_start_idx: int, walk_end_idx: int, fps: float
    ) -> Optional[Dict]:
        """Walk 구간에서 좌/우 Heel Strike (HS) 시점을 감지

        알고리즘:
        1. ankle_y 시계열 추출 (walk 구간)
        2. 선형 트렌드 제거 (걸어가면서 y값 전체적으로 변화)
        3. Smoothing (median + moving average)
        4. Local minimum 감지 = Heel Strike (발이 가장 낮은 시점, y값 최대)
        """
        walk_frames = frame_data[walk_start_idx:walk_end_idx + 1]
        if len(walk_frames) < int(fps * 1.5):
            return None

        min_step_distance = max(int(0.3 * fps), 3)

        def detect_hs(ankle_key):
            y_vals = np.array([f[ankle_key] for f in walk_frames])

            # 선형 트렌드 제거
            x = np.arange(len(y_vals))
            coeffs = np.polyfit(x, y_vals, 1)
            trend = np.polyval(coeffs, x)
            detrended = y_vals - trend

            # Smoothing
            kernel_size = max(3, int(fps * 0.05))
            if kernel_size % 2 == 0:
                kernel_size += 1
            smoothed = np.convolve(detrended, np.ones(kernel_size) / kernel_size, mode='same')

            # HS = local maximum of y (foot lowest = y largest in image coords)
            peaks, properties = find_peaks(smoothed, distance=min_step_distance,
                                           prominence=np.std(smoothed) * 0.3)

            if len(peaks) < 2:
                return None, None

            # 프레임 인덱스 → 절대 프레임/시간
            hs_frames = [walk_start_idx + p for p in peaks]
            hs_times = [frame_data[idx]["time"] for idx in hs_frames]
            return hs_frames, hs_times

        left_hs_frames, left_hs_times = detect_hs("left_ankle_y")
        right_hs_frames, right_hs_times = detect_hs("right_ankle_y")

        if left_hs_frames is None and right_hs_frames is None:
            return None

        return {
            "left_hs_frames": left_hs_frames or [],
            "right_hs_frames": right_hs_frames or [],
            "left_hs_times": left_hs_times or [],
            "right_hs_times": right_hs_times or [],
        }

    def _calc_cadence(self, gait_events: Dict, walk_duration: float) -> Dict:
        """분당 걸음수 (steps/min)"""
        total_steps = len(gait_events["left_hs_times"]) + len(gait_events["right_hs_times"])
        cadence = (total_steps / walk_duration) * 60 if walk_duration > 0 else 0
        return {
            "value": round(cadence, 1),
            "unit": "steps/min",
            "total_steps": total_steps,
        }

    def _calc_step_time(self, gait_events: Dict) -> Dict:
        """Step time: 한 발 HS에서 반대 발 HS까지의 시간"""
        all_hs = []
        for t in gait_events["left_hs_times"]:
            all_hs.append(("L", t))
        for t in gait_events["right_hs_times"]:
            all_hs.append(("R", t))
        all_hs.sort(key=lambda x: x[1])

        step_times = []
        left_steps = []
        right_steps = []

        for i in range(1, len(all_hs)):
            side_prev, t_prev = all_hs[i - 1]
            side_curr, t_curr = all_hs[i]
            if side_prev != side_curr:
                dt = t_curr - t_prev
                step_times.append(dt)
                if side_curr == "L":
                    left_steps.append(dt)
                else:
                    right_steps.append(dt)

        if not step_times:
            return {"mean": 0, "cv": 0, "unit": "s"}

        mean_st = np.mean(step_times)
        cv_st = (np.std(step_times) / mean_st * 100) if mean_st > 0 else 0

        result = {
            "mean": round(float(mean_st), 3),
            "cv": round(float(cv_st), 1),
            "unit": "s",
        }
        if left_steps:
            result["left_mean"] = round(float(np.mean(left_steps)), 3)
        if right_steps:
            result["right_mean"] = round(float(np.mean(right_steps)), 3)
        return result

    def _calc_stride_time(self, gait_events: Dict) -> Dict:
        """Stride time: 같은 발 연속 HS 간격 (L→L, R→R)"""
        stride_times = []

        for times in [gait_events["left_hs_times"], gait_events["right_hs_times"]]:
            for i in range(1, len(times)):
                stride_times.append(times[i] - times[i - 1])

        if not stride_times:
            return {"mean": 0, "cv": 0, "unit": "s"}

        mean_st = np.mean(stride_times)
        cv_st = (np.std(stride_times) / mean_st * 100) if mean_st > 0 else 0

        return {
            "mean": round(float(mean_st), 3),
            "cv": round(float(cv_st), 1),
            "unit": "s",
        }

    def _calc_step_time_asymmetry(self, gait_events: Dict) -> Dict:
        """좌우 step time 비대칭: |L-R| / (L+R) * 200"""
        all_hs = []
        for t in gait_events["left_hs_times"]:
            all_hs.append(("L", t))
        for t in gait_events["right_hs_times"]:
            all_hs.append(("R", t))
        all_hs.sort(key=lambda x: x[1])

        left_steps = []
        right_steps = []
        for i in range(1, len(all_hs)):
            side_prev, t_prev = all_hs[i - 1]
            side_curr, t_curr = all_hs[i]
            if side_prev != side_curr:
                dt = t_curr - t_prev
                if side_curr == "L":
                    left_steps.append(dt)
                else:
                    right_steps.append(dt)

        if not left_steps or not right_steps:
            return {"value": 0, "unit": "%"}

        l_mean = np.mean(left_steps)
        r_mean = np.mean(right_steps)
        asymmetry = abs(l_mean - r_mean) / (l_mean + r_mean) * 200 if (l_mean + r_mean) > 0 else 0

        return {
            "value": round(float(asymmetry), 1),
            "unit": "%",
            "left_mean": round(float(l_mean), 3),
            "right_mean": round(float(r_mean), 3),
        }

    def _calc_arm_swing(
        self, frame_data: List[Dict], walk_start: int, walk_end: int, fps: float
    ) -> Dict:
        """Arm swing: Wrist Y 진동 amplitude (detrended)"""
        walk_frames = frame_data[walk_start:walk_end + 1]
        if len(walk_frames) < int(fps):
            return {"left_amplitude": 0, "right_amplitude": 0, "asymmetry_index": 0}

        def calc_amplitude(key):
            y_vals = np.array([f[key] for f in walk_frames])
            x = np.arange(len(y_vals))
            coeffs = np.polyfit(x, y_vals, 1)
            detrended = y_vals - np.polyval(coeffs, x)
            peaks_up, _ = find_peaks(detrended, distance=max(int(0.3 * fps), 3))
            peaks_dn, _ = find_peaks(-detrended, distance=max(int(0.3 * fps), 3))
            if len(peaks_up) > 0 and len(peaks_dn) > 0:
                return float(np.mean(detrended[peaks_up]) - np.mean(detrended[peaks_dn]))
            return float(np.std(detrended) * 2)

        left_amp = calc_amplitude("left_wrist_y")
        right_amp = calc_amplitude("right_wrist_y")
        total = left_amp + right_amp
        asymmetry = abs(left_amp - right_amp) / total * 100 if total > 0 else 0

        return {
            "left_amplitude": round(left_amp, 4),
            "right_amplitude": round(right_amp, 4),
            "asymmetry_index": round(float(asymmetry), 1),
            "unit": "normalized_y",
        }

    def _calc_foot_clearance(
        self, frame_data: List[Dict], walk_start: int, walk_end: int, fps: float
    ) -> Dict:
        """Foot clearance: swing phase에서 foot Y의 peak height (detrended)"""
        walk_frames = frame_data[walk_start:walk_end + 1]
        if len(walk_frames) < int(fps):
            return {"mean_clearance": 0, "min_clearance": 0}

        clearances = []
        for key in ["left_foot_y", "right_foot_y"]:
            y_vals = np.array([f[key] for f in walk_frames])
            x = np.arange(len(y_vals))
            coeffs = np.polyfit(x, y_vals, 1)
            detrended = y_vals - np.polyval(coeffs, x)

            # Swing phase = foot lifts = y decreases (in image coords, up = smaller y)
            # So foot clearance = negative peaks of detrended (foot going up)
            peaks, props = find_peaks(-detrended, distance=max(int(0.3 * fps), 3),
                                      prominence=np.std(detrended) * 0.2)
            if len(peaks) > 0:
                clearances.extend(-detrended[peaks])

        if not clearances:
            return {"mean_clearance": 0, "min_clearance": 0, "unit": "normalized_y"}

        return {
            "mean_clearance": round(float(np.mean(clearances)), 4),
            "min_clearance": round(float(np.min(clearances)), 4),
            "unit": "normalized_y",
        }

    def _calc_double_support(self, gait_events: Dict, walk_duration: float) -> Dict:
        """이중 지지기 비율 추정

        간이 계산: step_time 대비 stride_time으로 추정
        double_support ≈ 1 - (swing_time / stride_time) × 2
        정상: 20-30%
        """
        all_hs = []
        for t in gait_events["left_hs_times"]:
            all_hs.append(("L", t))
        for t in gait_events["right_hs_times"]:
            all_hs.append(("R", t))
        all_hs.sort(key=lambda x: x[1])

        step_times = []
        for i in range(1, len(all_hs)):
            if all_hs[i - 1][0] != all_hs[i][0]:
                step_times.append(all_hs[i][1] - all_hs[i - 1][1])

        stride_times = []
        for times in [gait_events["left_hs_times"], gait_events["right_hs_times"]]:
            for i in range(1, len(times)):
                stride_times.append(times[i] - times[i - 1])

        if not step_times or not stride_times:
            return {"value": 0, "unit": "%"}

        mean_step = np.mean(step_times)
        mean_stride = np.mean(stride_times)

        # double support ≈ (stride_time - 2 * swing_time) / stride_time
        # swing_time ≈ stride_time - 2 * step_time (approximation)
        # Simplified: ds_pct ≈ (2 * mean_step / mean_stride - 1) * 100
        ds_ratio = (2 * mean_step / mean_stride - 1) if mean_stride > 0 else 0
        ds_pct = max(0, ds_ratio * 100)

        return {
            "value": round(float(ds_pct), 1),
            "unit": "%",
        }

    def _calc_stride_regularity(
        self, frame_data: List[Dict], walk_start: int, walk_end: int, fps: float
    ) -> Dict:
        """Stride regularity: ankle Y 자기상관에서 stride frequency peak 높이"""
        walk_frames = frame_data[walk_start:walk_end + 1]
        if len(walk_frames) < int(fps * 2):
            return {"value": 0}

        # 양쪽 ankle_y 평균 사용
        y_vals = np.array([(f["left_ankle_y"] + f["right_ankle_y"]) / 2 for f in walk_frames])

        # Detrend
        x = np.arange(len(y_vals))
        coeffs = np.polyfit(x, y_vals, 1)
        detrended = y_vals - np.polyval(coeffs, x)

        # Normalize
        std = np.std(detrended)
        if std < 1e-8:
            return {"value": 0}
        normalized = detrended / std

        # Autocorrelation
        n = len(normalized)
        acf = np.correlate(normalized, normalized, mode='full')[n - 1:]
        acf = acf / acf[0]  # Normalize to 1 at lag=0

        # Stride period: ~0.8~2.0s → look for peak in lag range
        min_lag = max(int(0.6 * fps), 3)
        max_lag = min(int(2.5 * fps), n // 2)

        if max_lag <= min_lag:
            return {"value": 0}

        acf_segment = acf[min_lag:max_lag]
        if len(acf_segment) < 3:
            return {"value": 0}

        peak_idx = np.argmax(acf_segment)
        regularity = float(acf_segment[peak_idx])
        stride_period = (min_lag + peak_idx) / fps

        return {
            "value": round(regularity, 3),
            "stride_period": round(stride_period, 3),
            "unit": "ratio (0-1)",
        }

    def _calc_trunk_inclination(
        self, frame_data: List[Dict], walk_start: int, walk_end: int
    ) -> Dict:
        """체간 전방 경사: shoulder-hip Y 비율 (뒤에서 촬영이므로 상대적)"""
        walk_frames = frame_data[walk_start:walk_end + 1]
        if not walk_frames:
            return {"value": 0}

        ratios = []
        for f in walk_frames:
            shoulder_mid_y = (f["left_shoulder_y"] + f["right_shoulder_y"]) / 2
            hip_mid_y = (f["left_hip_y"] + f["right_hip_y"]) / 2
            # shoulder와 hip의 y 차이 (정상 시 shoulder < hip in image coords)
            trunk_length = hip_mid_y - shoulder_mid_y
            if trunk_length > 0.01:
                # 수직 기준 대비 shoulder-hip 비율
                ratios.append(trunk_length)

        if not ratios:
            return {"value": 0, "unit": "normalized_y"}

        return {
            "mean": round(float(np.mean(ratios)), 4),
            "std": round(float(np.std(ratios)), 4),
            "unit": "normalized_y",
        }

    def _calc_swing_stance_ratio(self, gait_events: Dict, walk_duration: float) -> Dict:
        """Swing/Stance 비율 추정 (HS 간격 기반)

        정상: ~40% swing / ~60% stance
        """
        stride_times = []
        for times in [gait_events["left_hs_times"], gait_events["right_hs_times"]]:
            for i in range(1, len(times)):
                stride_times.append(times[i] - times[i - 1])

        all_hs = []
        for t in gait_events["left_hs_times"]:
            all_hs.append(("L", t))
        for t in gait_events["right_hs_times"]:
            all_hs.append(("R", t))
        all_hs.sort(key=lambda x: x[1])

        step_times = []
        for i in range(1, len(all_hs)):
            if all_hs[i - 1][0] != all_hs[i][0]:
                step_times.append(all_hs[i][1] - all_hs[i - 1][1])

        if not stride_times or not step_times:
            return {"swing_pct": 0, "stance_pct": 0}

        mean_stride = np.mean(stride_times)
        mean_step = np.mean(step_times)

        # Swing time ≈ stride_time - step_time (single support of contralateral leg)
        swing_time = mean_stride - mean_step
        swing_pct = (swing_time / mean_stride * 100) if mean_stride > 0 else 0
        stance_pct = 100 - swing_pct

        # Clamp to reasonable range
        swing_pct = max(0, min(100, swing_pct))
        stance_pct = max(0, min(100, stance_pct))

        return {
            "swing_pct": round(float(swing_pct), 1),
            "stance_pct": round(float(stance_pct), 1),
            "unit": "%",
        }

    def __del__(self):
        """리소스 정리"""
        if hasattr(self, 'pose'):
            self.pose.close()
