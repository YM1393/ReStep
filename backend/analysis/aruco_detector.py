"""
ArUco 마커 감지 및 거리 캘리브레이션 모듈

영상에서 START/FINISH ArUco 마커를 감지하여 정확한 10m 구간을 측정한다.
마커 ID: 0=START(2m), 1=FINISH(12m) (DICT_4X4_50)

마커 크기(pixel size) 기반 캘리브레이션:
  - 마커 크기 ∝ 1/카메라거리 (핀홀 모델)
  - 두 마커 크기로 카메라~0m 거리(d_cam) 및 초점거리(f) 계산
  - f와 환자 키로 절대 1/h 타겟 계산 → 2m/12m 통과 시간 결정
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple


# 마커 ID → 실제 거리 (m) 매핑
MARKER_DISTANCE_MAP = {0: 2.0, 1: 12.0}  # START=2m, FINISH=12m
ARUCO_DICT_TYPE = cv2.aruco.DICT_4X4_50
MIN_DETECTIONS = 3  # 마커별 최소 감지 횟수
MARKER_REAL_SIZE_M = 0.25  # 생성된 마커의 실제 크기 (25cm)


class DistanceCalibration:
    """START/FINISH 마커 기반 거리 캘리브레이션 (크기 기반)

    두 마커의 pixel_size로 카메라 위치(d_cam)와 초점거리(f)를 계산하고,
    환자 키(patient_height_m)를 이용하여 절대 1/h 타겟을 산출한다.
    이렇게 하면 보행 시작 위치(x₀)에 무관하게 정확한 2m/12m 통과 시간을 결정할 수 있다.
    """

    def __init__(self, marker_pixel_y: Dict[int, float],
                 marker_pixel_sizes: Dict[int, float],
                 frame_height: int,
                 patient_height_m: float = 1.70):
        """
        Args:
            marker_pixel_y: {marker_id: pixel_y_position} (하위 호환)
            marker_pixel_sizes: {marker_id: pixel_size} (크기 기반 캘리브레이션)
            frame_height: 영상 프레임 높이 (px)
            patient_height_m: 환자 키 (m), 절대 1/h 타겟 계산에 필요
        """
        self.marker_pixel_y = marker_pixel_y
        self.marker_pixel_sizes = marker_pixel_sizes
        self.frame_height = frame_height
        self.patient_height_m = patient_height_m
        self.valid = False
        self.d_cam = None  # 카메라~0m 거리 (m)
        self.focal_length = None  # 추정 초점거리 (px)

        if 0 not in marker_pixel_sizes or 1 not in marker_pixel_sizes:
            print(f"[ARUCO CAL] Need both START(0) and FINISH(1) marker sizes")
            return

        size_start = marker_pixel_sizes[0]   # 2m 지점 마커 크기
        size_finish = marker_pixel_sizes[1]  # 12m 지점 마커 크기

        if size_start <= 0 or size_finish <= 0:
            print(f"[ARUCO CAL] Invalid marker sizes: start={size_start}, finish={size_finish}")
            return

        if size_start <= size_finish:
            print(f"[ARUCO CAL] Warning: START size({size_start:.0f}px) should be larger "
                  f"than FINISH size({size_finish:.0f}px)")
            return

        # d_cam 계산: 카메라에서 0m 시작선까지의 거리
        # size ∝ 1/(d + d_cam) → size_2m/size_12m = (12+d_cam)/(2+d_cam)
        # → d_cam = (12*size_finish - 2*size_start) / (size_start - size_finish)
        self.d_cam = (12.0 * size_finish - 2.0 * size_start) / (size_start - size_finish)

        if self.d_cam <= 0:
            print(f"[ARUCO CAL] Invalid d_cam={self.d_cam:.2f}m (must be positive)")
            return

        # 초점거리 계산: f = marker_pixel_size * distance_from_camera / marker_real_size
        # 2m 마커 사용: f = size_start * (2 + d_cam) / MARKER_REAL_SIZE_M
        self.focal_length = size_start * (2.0 + self.d_cam) / MARKER_REAL_SIZE_M

        self.valid = True

        # 절대 1/h 타겟 미리보기
        C = self.focal_length * self.patient_height_m
        inv_h_2m = (2.0 + self.d_cam) / C
        inv_h_12m = (12.0 + self.d_cam) / C
        h_2m = 1.0 / inv_h_2m if inv_h_2m > 0 else 0
        h_12m = 1.0 / inv_h_12m if inv_h_12m > 0 else 0

        print(f"[ARUCO CAL] Size-based: START={size_start:.0f}px, FINISH={size_finish:.0f}px, "
              f"d_cam={self.d_cam:.2f}m, f={self.focal_length:.0f}px")
        print(f"[ARUCO CAL] Absolute targets: h@2m={h_2m:.0f}px (1/h={inv_h_2m:.6f}), "
              f"h@12m={h_12m:.0f}px (1/h={inv_h_12m:.6f})")

    def find_time_at_marker(
        self,
        marker_id: int,
        inv_h: List[float],
        times: List[float],
        walk_start_idx: int,
        walk_end_idx: int,
        inv_h_walk_start: float,
        inv_h_walk_end: float,
        direction: str = 'away'
    ) -> Optional[float]:
        """마커 위치에 사람이 도달하는 시간을 찾는다.

        절대 1/h 타겟 방식: d_cam + focal_length + patient_height로
        2m/12m에서의 예상 1/h 값을 계산하고, 시계열에서 교차 시점을 찾는다.
        보행 시작 위치(x₀)에 무관하게 작동한다.

        Args:
            marker_id: 0(START, 2m) 또는 1(FINISH, 12m)
            inv_h: 사람의 1/pixel_height 시계열 (전체)
            times: 시간 시계열 (전체)
            walk_start_idx: 보행 시작 인덱스
            walk_end_idx: 보행 종료 인덱스
            inv_h_walk_start: 보행 시작 시 1/h
            inv_h_walk_end: 보행 종료 시 1/h
            direction: 'away' (카메라에서 멀어짐) 또는 'toward' (카메라로 접근)
        """
        if not self.valid or self.d_cam is None or self.focal_length is None:
            return None

        target_distance = MARKER_DISTANCE_MAP[marker_id]

        # 절대 1/h 타겟: 1/h(d) = (d + d_cam) / (f * H)
        C = self.focal_length * self.patient_height_m
        if C <= 0:
            return None
        target_inv_h = (target_distance + self.d_cam) / C

        # 탐색 범위: walk region + 앞뒤 여유
        margin = max(30, (walk_end_idx - walk_start_idx) // 4)
        search_start = max(0, walk_start_idx - margin)
        search_end = min(len(inv_h) - 1, walk_end_idx + margin)

        if direction == 'away':
            # away: 1/h 증가, walk_start부터 탐색
            for i in range(search_start, search_end):
                if inv_h[i] <= target_inv_h <= inv_h[i + 1]:
                    if abs(inv_h[i + 1] - inv_h[i]) < 1e-12:
                        continue
                    r = (target_inv_h - inv_h[i]) / (inv_h[i + 1] - inv_h[i])
                    return times[i] + r * (times[i + 1] - times[i])
        else:
            # toward: 1/h 감소, walk_start부터 하향 교차 탐색
            for i in range(search_start, search_end):
                if inv_h[i] >= target_inv_h >= inv_h[i + 1]:
                    if abs(inv_h[i + 1] - inv_h[i]) < 1e-12:
                        continue
                    r = (target_inv_h - inv_h[i]) / (inv_h[i + 1] - inv_h[i])
                    return times[i] + r * (times[i + 1] - times[i])

        return None


class ArucoCalibration:
    """영상에서 START/FINISH ArUco 마커를 감지하고 거리 캘리브레이션을 수행"""

    def __init__(self):
        self.dictionary = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_TYPE)
        self.parameters = cv2.aruco.DetectorParameters()

        # 원거리 감지를 위한 파라미터 튜닝
        self.parameters.adaptiveThreshWinSizeMin = 3
        self.parameters.adaptiveThreshWinSizeMax = 53
        self.parameters.adaptiveThreshWinSizeStep = 4
        self.parameters.minMarkerPerimeterRate = 0.005  # 작은 마커 허용
        self.parameters.maxMarkerPerimeterRate = 4.0
        self.parameters.polygonalApproxAccuracyRate = 0.05
        self.parameters.minCornerDistanceRate = 0.02

        self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.parameters)

    def detect_in_frame(self, frame: np.ndarray) -> Tuple[Dict[int, np.ndarray], Dict[int, float]]:
        """단일 프레임에서 ArUco 마커 감지

        Args:
            frame: BGR 이미지

        Returns:
            ({marker_id: center_point_array([x, y])}, {marker_id: pixel_size})
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        corners, ids, rejected = self.detector.detectMarkers(gray)

        positions = {}
        sizes = {}
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                marker_id = int(marker_id)
                if marker_id in MARKER_DISTANCE_MAP:
                    corner_points = corners[i][0]  # shape: (4, 2)
                    bottom_center_y = np.mean(corner_points[2:4, 1])
                    center_x = np.mean(corner_points[:, 0])
                    positions[marker_id] = np.array([center_x, bottom_center_y])
                    # 마커 크기: 코너 span의 최대값
                    size = max(np.ptp(corner_points[:, 0]), np.ptp(corner_points[:, 1]))
                    sizes[marker_id] = float(size)

        return positions, sizes

    def detect_in_video(
        self,
        video_path: str,
        sample_frames: int = 30
    ) -> Tuple[Dict[int, float], Dict[int, float]]:
        """영상에서 START/FINISH 마커를 감지하여 pixel_y 위치와 크기 반환

        "bookend" 전략: 영상 앞/뒤 프레임에서 샘플링
        (보행자가 마커를 가리지 않는 구간)

        Args:
            video_path: 영상 파일 경로
            sample_frames: 앞/뒤 각각 샘플링할 프레임 수

        Returns:
            ({marker_id: median_pixel_y}, {marker_id: median_pixel_size})
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[ARUCO] Cannot open video: {video_path}")
            return {}, {}

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames < 2:
            cap.release()
            return {}, {}

        # 샘플링할 프레임 인덱스 (앞 N + 뒤 N + 중간 일부)
        front_frames = list(range(0, min(sample_frames, total_frames)))
        back_start = max(total_frames - sample_frames, sample_frames)
        back_frames = list(range(back_start, total_frames))
        mid_frames = list(range(sample_frames, back_start, 30))

        all_sample_indices = sorted(set(front_frames + back_frames + mid_frames))

        # 마커별 감지된 Y좌표 및 크기 수집
        y_detections: Dict[int, List[float]] = {mid: [] for mid in MARKER_DISTANCE_MAP}
        size_detections: Dict[int, List[float]] = {mid: [] for mid in MARKER_DISTANCE_MAP}

        for frame_idx in all_sample_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                continue

            positions, sizes = self.detect_in_frame(frame)
            for mid, center in positions.items():
                y_detections[mid].append(center[1])
            for mid, size in sizes.items():
                size_detections[mid].append(size)

        cap.release()

        # 마커별 median Y좌표 및 크기
        label_map = {0: "START", 1: "FINISH"}
        result_y = {}
        result_sizes = {}
        for mid in MARKER_DISTANCE_MAP:
            label = label_map.get(mid, f"ID{mid}")
            y_values = y_detections[mid]
            s_values = size_detections[mid]
            if len(y_values) >= MIN_DETECTIONS:
                median_y = float(np.median(y_values))
                median_size = float(np.median(s_values))
                result_y[mid] = median_y
                result_sizes[mid] = median_size
                print(f"[ARUCO] {label} (ID={mid}, {MARKER_DISTANCE_MAP[mid]:.0f}m): "
                      f"y={median_y:.1f}, size={median_size:.0f}px "
                      f"(detected {len(y_values)} times)")
            elif len(y_values) > 0:
                print(f"[ARUCO] {label} (ID={mid}): only {len(y_values)} detections "
                      f"(need {MIN_DETECTIONS}), skipping")

        return result_y, result_sizes

    def compute_calibration(
        self,
        marker_positions: Dict[int, float],
        marker_sizes: Dict[int, float],
        frame_height: int,
        patient_height_m: float = 1.70
    ) -> Optional['DistanceCalibration']:
        """감지된 마커 위치+크기로 캘리브레이션 생성

        Args:
            marker_positions: {marker_id: pixel_y}
            marker_sizes: {marker_id: pixel_size}
            frame_height: 프레임 높이
            patient_height_m: 환자 키 (m)

        Returns:
            DistanceCalibration 또는 None
        """
        if 0 not in marker_sizes or 1 not in marker_sizes:
            return None

        cal = DistanceCalibration(marker_positions, marker_sizes, frame_height,
                                  patient_height_m=patient_height_m)
        return cal if cal.valid else None
