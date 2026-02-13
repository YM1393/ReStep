import os
import cv2
import numpy as np
import math
from typing import Dict, List, Tuple, Optional, Set
import mediapipe as mp


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


class BBSAnalyzer:
    """
    MediaPipe Pose를 사용한 BBS (Berg Balance Scale) 자동 평가 분석기

    14개 항목 중 영상 분석으로 평가 가능한 항목들을 자동 채점합니다.
    """

    MODEL_COMPLEXITY = 2  # Heavy 모델

    # MediaPipe Pose 키포인트 인덱스
    NOSE = 0
    LEFT_EYE = 2
    RIGHT_EYE = 5
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
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
    SITTING_ANGLE_THRESHOLD = 120
    STANDING_ANGLE_THRESHOLD = 160
    HAND_SUPPORT_THRESHOLD = 0.15  # 손목-무릎 거리 임계값
    FEET_TOGETHER_THRESHOLD = 0.08  # 발 모음 임계값 (정규화)
    TANDEM_FEET_THRESHOLD = 0.12  # 일렬 서기 임계값

    def __init__(self):
        """MediaPipe Pose 모델 초기화"""
        print(f"Loading MediaPipe Pose for BBS (model_complexity={self.MODEL_COMPLEXITY})")
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            model_complexity=self.MODEL_COMPLEXITY,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            static_image_mode=False
        )

    def analyze_video(
        self,
        video_path: str,
        test_item: str,  # 어떤 항목을 테스트하는지
        progress_callback=None,
        frame_callback=None
    ) -> Dict:
        """
        영상을 분석하여 특정 BBS 항목 점수 반환

        Args:
            video_path: 영상 파일 경로
            test_item: BBS 항목 (item1_sitting_to_standing, item2_standing_unsupported, 등)
            progress_callback: 진행률 콜백
            frame_callback: 프레임 콜백

        Returns:
            점수 및 분석 데이터
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"영상을 열 수 없습니다: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = int(fps * 30) if fps > 0 else 900
            print(f"[BBS] Estimated total_frames={total_frames} (original was 0)")
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

        frame_data = []
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)

            # 프레임 콜백
            if frame_callback and frame_count % 3 == 0:
                try:
                    annotated_frame = frame.copy()
                    if results.pose_landmarks is not None:
                        draw_body_landmarks(annotated_frame, results.pose_landmarks)
                    frame_callback(annotated_frame)
                except Exception as e:
                    print(f"[BBS] Frame callback failed: {e}")

            # 포즈 데이터 추출
            if results.pose_landmarks is not None:
                keypoints = np.array([
                    [lm.x * frame_width, lm.y * frame_height]
                    for lm in results.pose_landmarks.landmark
                ])
                data = self._extract_frame_data(keypoints, frame_count, fps, frame_height, frame_width)
                if data:
                    frame_data.append(data)

            frame_count += 1

            if progress_callback and total_frames > 0:
                progress = int((frame_count / total_frames) * 100)
                progress_callback(progress)

        cap.release()

        if len(frame_data) < 10:
            return {
                "score": 0,
                "confidence": 0,
                "message": "분석할 수 있는 프레임이 부족합니다",
                "details": {}
            }

        # 항목별 분석 수행
        analysis_func = self._get_analysis_function(test_item)
        if analysis_func:
            return analysis_func(frame_data, fps)
        else:
            return {
                "score": None,
                "confidence": 0,
                "message": f"'{test_item}' 항목은 자동 분석을 지원하지 않습니다",
                "details": {}
            }

    def analyze_all_items(
        self,
        video_path: str,
        progress_callback=None,
        frame_callback=None,
        save_overlay_video: bool = False
    ) -> Dict:
        """
        영상을 분석하여 가능한 모든 BBS 항목 평가
        주로 앉았다 일어서기 관련 항목들을 분석
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"영상을 열 수 없습니다: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = int(fps * 30) if fps > 0 else 900
            print(f"[BBS] Estimated total_frames={total_frames} (overlay, original was 0)")
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

        # 오버레이 영상 저장 설정
        overlay_video_path = None
        video_writer = None
        if save_overlay_video:
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            overlay_video_path = os.path.join(
                os.path.dirname(video_path),
                f"{base_name}_overlay.mp4"
            )
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            video_writer = cv2.VideoWriter(
                overlay_video_path, fourcc, fps,
                (frame_width, frame_height)
            )
            if not video_writer.isOpened():
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(
                    overlay_video_path, fourcc, fps,
                    (frame_width, frame_height)
                )
            print(f"[BBS] Saving overlay video to: {overlay_video_path}")

        frame_data = []
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

            if frame_callback and frame_count % 3 == 0:
                try:
                    frame_callback(annotated_frame)
                except Exception as e:
                    print(f"[BBS] Frame callback failed: {e}")

            if results.pose_landmarks is not None:
                keypoints = np.array([
                    [lm.x * frame_width, lm.y * frame_height]
                    for lm in results.pose_landmarks.landmark
                ])
                data = self._extract_frame_data(keypoints, frame_count, fps, frame_height, frame_width)
                if data:
                    frame_data.append(data)

            frame_count += 1

            if progress_callback and total_frames > 0:
                progress = int((frame_count / total_frames) * 100)
                progress_callback(progress)

        cap.release()
        if video_writer is not None:
            video_writer.release()
            print(f"[BBS] Overlay video saved: {overlay_video_path}")

        if len(frame_data) < 10:
            return {
                "scores": {},
                "message": "분석할 수 있는 프레임이 부족합니다"
            }

        # 14개 항목 모두 분석
        scores = {}

        # 1. 앉은 자세에서 일어나기
        result = self._analyze_sitting_to_standing(frame_data, fps)
        if result["score"] is not None:
            scores["item1_sitting_to_standing"] = result

        # 2. 잡지 않고 서 있기
        result = self._analyze_standing_unsupported(frame_data, fps)
        if result["score"] is not None:
            scores["item2_standing_unsupported"] = result

        # 3. 등받이에 기대지 않고 앉기
        result = self._analyze_sitting_unsupported(frame_data, fps)
        if result["score"] is not None:
            scores["item3_sitting_unsupported"] = result

        # 4. 선자세에서 앉기
        result = self._analyze_standing_to_sitting(frame_data, fps)
        if result["score"] is not None:
            scores["item4_standing_to_sitting"] = result

        # 5. 의자에서 의자로 이동하기
        result = self._analyze_transfers(frame_data, fps)
        if result["score"] is not None:
            scores["item5_transfers"] = result

        # 6. 두눈을 감고 서 있기
        result = self._analyze_standing_eyes_closed(frame_data, fps)
        if result["score"] is not None:
            scores["item6_standing_eyes_closed"] = result

        # 7. 두발을 붙이고 서 있기
        result = self._analyze_feet_together_standing(frame_data, fps)
        if result["score"] is not None:
            scores["item7_standing_feet_together"] = result

        # 8. 선자세에서 앞으로 팔 뻗기
        result = self._analyze_reaching_forward(frame_data, fps)
        if result["score"] is not None:
            scores["item8_reaching_forward"] = result

        # 9. 바닥에서 물건 줍기
        result = self._analyze_pick_up_object(frame_data, fps)
        if result["score"] is not None:
            scores["item9_pick_up_object"] = result

        # 10. 뒤돌아보기
        result = self._analyze_turning_look_behind(frame_data, fps)
        if result["score"] is not None:
            scores["item10_turning_to_look_behind"] = result

        # 11. 360도 회전
        result = self._analyze_turn_360(frame_data, fps)
        if result["score"] is not None:
            scores["item11_turn_360_degrees"] = result

        # 12. 발판 위에 발 교대로 올리기
        result = self._analyze_stool_stepping(frame_data, fps)
        if result["score"] is not None:
            scores["item12_stool_stepping"] = result

        # 13. 일렬로 서기 (탄뎀)
        result = self._analyze_tandem_standing(frame_data, fps)
        if result["score"] is not None:
            scores["item13_standing_one_foot_front"] = result

        # 14. 한 다리로 서기
        result = self._analyze_one_leg_standing(frame_data, fps)
        if result["score"] is not None:
            scores["item14_standing_on_one_leg"] = result

        result = {
            "scores": scores,
            "total_frames": len(frame_data),
            "fps": fps,
            "duration": len(frame_data) / fps if fps > 0 else 0
        }
        if overlay_video_path and os.path.exists(overlay_video_path):
            result["overlay_video_path"] = overlay_video_path
        return result

    def _extract_frame_data(self, keypoints: np.ndarray, frame_num: int, fps: float,
                           frame_height: int, frame_width: int) -> Optional[Dict]:
        """프레임에서 BBS 분석에 필요한 데이터 추출"""
        if keypoints is None or len(keypoints) < 33:
            return None

        nose = keypoints[self.NOSE]
        left_hip = keypoints[self.LEFT_HIP]
        right_hip = keypoints[self.RIGHT_HIP]
        left_knee = keypoints[self.LEFT_KNEE]
        right_knee = keypoints[self.RIGHT_KNEE]
        left_ankle = keypoints[self.LEFT_ANKLE]
        right_ankle = keypoints[self.RIGHT_ANKLE]
        left_shoulder = keypoints[self.LEFT_SHOULDER]
        right_shoulder = keypoints[self.RIGHT_SHOULDER]
        left_elbow = keypoints[self.LEFT_ELBOW]
        right_elbow = keypoints[self.RIGHT_ELBOW]
        left_wrist = keypoints[self.LEFT_WRIST]
        right_wrist = keypoints[self.RIGHT_WRIST]
        left_heel = keypoints[self.LEFT_HEEL]
        right_heel = keypoints[self.RIGHT_HEEL]
        left_foot_index = keypoints[self.LEFT_FOOT_INDEX]
        right_foot_index = keypoints[self.RIGHT_FOOT_INDEX]

        # 다리 각도 계산
        left_leg_angle = self._calculate_angle(left_hip, left_knee, left_ankle)
        right_leg_angle = self._calculate_angle(right_hip, right_knee, right_ankle)
        avg_leg_angle = (left_leg_angle + right_leg_angle) / 2 if left_leg_angle > 0 and right_leg_angle > 0 else max(left_leg_angle, right_leg_angle)

        # 엉덩이 높이 (정규화)
        hip_y = (left_hip[1] + right_hip[1]) / 2
        hip_height_normalized = 1 - (hip_y / frame_height) if frame_height > 0 else 0

        # 어깨 중심점
        shoulder_center = np.array([(left_shoulder[0] + right_shoulder[0]) / 2,
                                    (left_shoulder[1] + right_shoulder[1]) / 2])

        # 어깨 방향 (회전 감지용)
        shoulder_direction = 0.0
        if left_shoulder[0] > 0 and right_shoulder[0] > 0:
            shoulder_direction = math.atan2(
                right_shoulder[1] - left_shoulder[1],
                right_shoulder[0] - left_shoulder[0]
            )

        # 손목-무릎 거리 (손으로 짚는지)
        wrist_knee_distance = float('inf')
        knee_center = np.array([(left_knee[0] + right_knee[0]) / 2, (left_knee[1] + right_knee[1]) / 2])

        if left_wrist[0] > 0 and left_wrist[1] > 0:
            left_dist = np.linalg.norm(left_wrist - knee_center)
            wrist_knee_distance = min(wrist_knee_distance, left_dist)
        if right_wrist[0] > 0 and right_wrist[1] > 0:
            right_dist = np.linalg.norm(right_wrist - knee_center)
            wrist_knee_distance = min(wrist_knee_distance, right_dist)

        wrist_knee_normalized = wrist_knee_distance / frame_height if frame_height > 0 and wrist_knee_distance != float('inf') else 1.0

        # 발 사이 거리 (정규화)
        feet_distance = 0.0
        if left_ankle[0] > 0 and right_ankle[0] > 0:
            feet_distance = np.linalg.norm(left_ankle - right_ankle) / frame_width

        # 발 높이 차이 (한발 들기 감지)
        left_foot_y = left_ankle[1] if left_ankle[1] > 0 else frame_height
        right_foot_y = right_ankle[1] if right_ankle[1] > 0 else frame_height
        foot_height_diff = abs(left_foot_y - right_foot_y) / frame_height

        # 어느 발이 더 높은지 (들려있는지)
        lifted_foot = None
        if foot_height_diff > 0.05:  # 5% 이상 차이
            lifted_foot = 'left' if left_foot_y < right_foot_y else 'right'

        # 손목 높이 (팔 뻗기 감지용) - 어깨 기준 상대 위치
        left_wrist_height = (shoulder_center[1] - left_wrist[1]) / frame_height if left_wrist[1] > 0 else 0
        right_wrist_height = (shoulder_center[1] - right_wrist[1]) / frame_height if right_wrist[1] > 0 else 0

        # 손목 전방 거리 (팔 뻗기 감지용)
        left_wrist_forward = (left_wrist[0] - shoulder_center[0]) / frame_width if left_wrist[0] > 0 else 0
        right_wrist_forward = (right_wrist[0] - shoulder_center[0]) / frame_width if right_wrist[0] > 0 else 0
        max_wrist_forward = max(abs(left_wrist_forward), abs(right_wrist_forward))

        # 손목 낮은 위치 (물건 줍기 감지용) - 발목 기준
        ankle_y = (left_ankle[1] + right_ankle[1]) / 2 if left_ankle[1] > 0 and right_ankle[1] > 0 else frame_height
        left_wrist_low = (left_wrist[1] - ankle_y) / frame_height if left_wrist[1] > 0 else 0
        right_wrist_low = (right_wrist[1] - ankle_y) / frame_height if right_wrist[1] > 0 else 0
        wrist_near_floor = max(left_wrist_low, right_wrist_low) > -0.1  # 손목이 발목 근처

        # 코 방향 (고개 돌리기 감지용)
        head_direction = 0.0
        if nose[0] > 0 and shoulder_center[0] > 0:
            head_direction = (nose[0] - shoulder_center[0]) / frame_width

        # 발 전후 위치 (일렬 서기 - 탄뎀)
        feet_front_back_diff = 0.0
        if left_ankle[1] > 0 and right_ankle[1] > 0:
            feet_front_back_diff = abs(left_ankle[1] - right_ankle[1]) / frame_height

        # 발 좌우 위치 (일렬 서기)
        feet_lateral_diff = 0.0
        if left_ankle[0] > 0 and right_ankle[0] > 0:
            feet_lateral_diff = abs(left_ankle[0] - right_ankle[0]) / frame_width

        # 일렬 서기 여부 (발이 앞뒤로 배치)
        is_tandem = feet_front_back_diff > 0.03 and feet_lateral_diff < self.TANDEM_FEET_THRESHOLD

        # 스텝 동작 감지 (발판 올리기)
        stepping_foot = None
        if foot_height_diff > 0.03 and foot_height_diff < 0.15:  # 적당한 높이 차이
            stepping_foot = 'left' if left_foot_y < right_foot_y else 'right'

        return {
            "frame": frame_num,
            "time": frame_num / fps if fps > 0 else 0,
            "leg_angle": avg_leg_angle,
            "hip_height": hip_height_normalized,
            "shoulder_direction": shoulder_direction,
            "wrist_knee_distance": wrist_knee_normalized,
            "feet_distance": feet_distance,
            "foot_height_diff": foot_height_diff,
            "lifted_foot": lifted_foot,
            "is_sitting": avg_leg_angle < self.SITTING_ANGLE_THRESHOLD,
            "is_standing": avg_leg_angle >= self.STANDING_ANGLE_THRESHOLD,
            "using_hands": wrist_knee_normalized < self.HAND_SUPPORT_THRESHOLD,
            # 추가 데이터
            "wrist_forward": max_wrist_forward,
            "wrist_near_floor": wrist_near_floor,
            "head_direction": head_direction,
            "is_tandem": is_tandem,
            "feet_front_back_diff": feet_front_back_diff,
            "feet_lateral_diff": feet_lateral_diff,
            "stepping_foot": stepping_foot,
            "left_wrist_height": left_wrist_height,
            "right_wrist_height": right_wrist_height
        }

    def _calculate_angle(self, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
        """세 점 사이의 각도 계산 (도)"""
        if any(p[0] <= 0 or p[1] <= 0 for p in [p1, p2, p3]):
            return 0.0

        v1 = p1 - p2
        v2 = p3 - p2

        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle = np.degrees(np.arccos(cos_angle))

        return angle

    def _get_analysis_function(self, test_item: str):
        """항목별 분석 함수 반환"""
        analysis_map = {
            "item1_sitting_to_standing": self._analyze_sitting_to_standing,
            "item2_standing_unsupported": self._analyze_standing_unsupported,
            "item3_sitting_unsupported": self._analyze_sitting_unsupported,
            "item4_standing_to_sitting": self._analyze_standing_to_sitting,
            "item5_transfers": self._analyze_transfers,
            "item6_standing_eyes_closed": self._analyze_standing_eyes_closed,
            "item7_standing_feet_together": self._analyze_feet_together_standing,
            "item8_reaching_forward": self._analyze_reaching_forward,
            "item9_pick_up_object": self._analyze_pick_up_object,
            "item10_turning_to_look_behind": self._analyze_turning_look_behind,
            "item11_turn_360_degrees": self._analyze_turn_360,
            "item12_stool_stepping": self._analyze_stool_stepping,
            "item13_standing_one_foot_front": self._analyze_tandem_standing,
            "item14_standing_on_one_leg": self._analyze_one_leg_standing,
        }
        return analysis_map.get(test_item)

    def _analyze_sitting_to_standing(self, frame_data: List[Dict], fps: float) -> Dict:
        """
        항목 1: 앉은 자세에서 일어나기 분석

        0점: 중간~최대 도움 필요
        1점: 도움 필요, 안정 유지에도 도움 필요
        2점: 여러 번 시도 후 손 사용하여 일어섬
        3점: 손 사용하여 스스로 일어섬
        4점: 손 사용 없이 일어서서 안정 유지
        """
        # 앉은 상태 → 선 상태 전환 찾기
        sitting_frames = [f for f in frame_data if f['is_sitting']]
        standing_frames = [f for f in frame_data if f['is_standing']]

        if len(sitting_frames) < 5 or len(standing_frames) < 5:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "앉았다 일어서는 동작이 감지되지 않았습니다",
                "details": {}
            }

        # 전환 구간 찾기 (앉은 상태에서 선 상태로)
        transition_start = None
        transition_end = None

        for i, f in enumerate(frame_data):
            if f['is_sitting'] and transition_start is None:
                transition_start = i
            if f['is_standing'] and transition_start is not None:
                transition_end = i
                break

        if transition_start is None or transition_end is None:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "기립 동작 전환점을 찾을 수 없습니다",
                "details": {}
            }

        # 전환 구간 데이터
        transition_frames = frame_data[transition_start:transition_end+1]

        # 손 사용 여부 확인
        hand_support_frames = sum(1 for f in transition_frames if f['using_hands'])
        hand_support_ratio = hand_support_frames / len(transition_frames) if transition_frames else 0
        used_hands = hand_support_ratio > 0.3

        # 시도 횟수 추정 (다리 각도 변화가 다시 감소했다 증가하면 재시도)
        attempt_count = 1
        was_increasing = True
        for i in range(1, len(transition_frames)):
            angle_change = transition_frames[i]['leg_angle'] - transition_frames[i-1]['leg_angle']
            if was_increasing and angle_change < -5:  # 각도가 다시 줄어듦
                attempt_count += 1
                was_increasing = False
            elif not was_increasing and angle_change > 5:
                was_increasing = True

        # 일어선 후 안정성 확인 (엉덩이 높이 변동)
        if transition_end + int(fps * 2) < len(frame_data):
            post_standing = frame_data[transition_end:transition_end + int(fps * 2)]
            height_variance = np.var([f['hip_height'] for f in post_standing])
            stable_standing = height_variance < 0.001
        else:
            stable_standing = True

        # 점수 결정
        if not used_hands and stable_standing and attempt_count == 1:
            score = 4
            message = "손 사용 없이 한 번에 안정적으로 일어섬"
        elif used_hands and attempt_count == 1:
            score = 3
            message = "손을 사용하여 스스로 일어섬"
        elif used_hands and attempt_count > 1:
            score = 2
            message = f"여러 번 시도({attempt_count}회) 후 손을 사용하여 일어섬"
        else:
            score = 2
            message = "일어서기 완료 (상세 분석 필요)"

        return {
            "score": score,
            "confidence": 0.7,
            "message": message,
            "details": {
                "used_hands": used_hands,
                "hand_support_ratio": round(hand_support_ratio, 2),
                "attempt_count": attempt_count,
                "stable_standing": stable_standing,
                "transition_duration": round((transition_end - transition_start) / fps, 2) if fps > 0 else 0
            }
        }

    def _analyze_standing_to_sitting(self, frame_data: List[Dict], fps: float) -> Dict:
        """
        항목 4: 선자세에서 앉기 분석

        0점: 앉을 때 도움 필요
        1점: 독립적이나 속도 조절 못함
        2점: 다리 뒤로 의자에 닿게 하여 속도 조절
        3점: 손 사용하여 독립적으로 앉음
        4점: 손 거의 사용 없이 안전하게 앉음
        """
        # 선 상태 → 앉은 상태 전환 찾기 (영상 후반부)
        standing_frames = [i for i, f in enumerate(frame_data) if f['is_standing']]
        sitting_frames = [i for i, f in enumerate(frame_data) if f['is_sitting']]

        if not standing_frames or not sitting_frames:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "앉는 동작이 감지되지 않았습니다",
                "details": {}
            }

        # 마지막 서있는 프레임에서 앉는 전환 찾기
        last_standing = max(standing_frames)
        sitting_after_standing = [i for i in sitting_frames if i > last_standing]

        if not sitting_after_standing:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "착석 동작 전환점을 찾을 수 없습니다",
                "details": {}
            }

        transition_start = last_standing
        transition_end = min(sitting_after_standing)
        transition_frames = frame_data[transition_start:transition_end+1]

        if len(transition_frames) < 3:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "착석 동작 분석에 충분한 데이터가 없습니다",
                "details": {}
            }

        # 손 사용 여부
        hand_support_frames = sum(1 for f in transition_frames if f['using_hands'])
        hand_support_ratio = hand_support_frames / len(transition_frames)
        used_hands = hand_support_ratio > 0.3

        # 앉는 속도 분석 (엉덩이 높이 변화율)
        height_changes = []
        for i in range(1, len(transition_frames)):
            change = transition_frames[i-1]['hip_height'] - transition_frames[i]['hip_height']
            height_changes.append(change)

        avg_descent_speed = np.mean(height_changes) if height_changes else 0
        max_descent_speed = max(height_changes) if height_changes else 0

        # 속도 조절 여부 (급격히 내려앉지 않음)
        controlled_descent = max_descent_speed < 0.05  # 급격한 하강 없음

        # 점수 결정
        if not used_hands and controlled_descent:
            score = 4
            message = "손 거의 사용 없이 안전하게 앉음"
        elif used_hands and controlled_descent:
            score = 3
            message = "손을 사용하여 안전하게 앉음"
        elif controlled_descent:
            score = 2
            message = "속도를 조절하며 앉음"
        else:
            score = 1
            message = "속도 조절이 어려움"

        return {
            "score": score,
            "confidence": 0.7,
            "message": message,
            "details": {
                "used_hands": used_hands,
                "hand_support_ratio": round(hand_support_ratio, 2),
                "controlled_descent": controlled_descent,
                "avg_descent_speed": round(avg_descent_speed, 4),
                "transition_duration": round((transition_end - transition_start) / fps, 2) if fps > 0 else 0
            }
        }

    def _analyze_standing_unsupported(self, frame_data: List[Dict], fps: float) -> Dict:
        """
        항목 2: 잡지 않고 서 있기 분석

        0점: 도움 없이 30초 서있지 못함
        1점: 여러 번 시도 후 30초
        2점: 30초 가능
        3점: 감독 하에 2분
        4점: 안전하게 2분
        """
        standing_frames = [f for f in frame_data if f['is_standing']]

        if len(standing_frames) < 10:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "서있는 구간이 감지되지 않았습니다",
                "details": {}
            }

        # 연속 서있는 시간 측정
        max_standing_duration = 0
        current_duration = 0

        for i, f in enumerate(frame_data):
            if f['is_standing']:
                current_duration += 1
            else:
                max_standing_duration = max(max_standing_duration, current_duration)
                current_duration = 0
        max_standing_duration = max(max_standing_duration, current_duration)

        standing_seconds = max_standing_duration / fps if fps > 0 else 0

        # 균형 안정성 (엉덩이 높이 변동)
        if standing_frames:
            height_variance = np.var([f['hip_height'] for f in standing_frames])
            stable = height_variance < 0.002
        else:
            stable = False

        # 점수 결정
        if standing_seconds >= 120 and stable:
            score = 4
            message = f"안전하게 {standing_seconds:.1f}초 동안 서있음"
        elif standing_seconds >= 120:
            score = 3
            message = f"{standing_seconds:.1f}초 동안 서있음 (약간의 균형 변동)"
        elif standing_seconds >= 30:
            score = 2
            message = f"{standing_seconds:.1f}초 동안 서있음"
        elif standing_seconds >= 10:
            score = 1
            message = f"{standing_seconds:.1f}초만 서있을 수 있음"
        else:
            score = 0
            message = f"30초 이상 서있지 못함 ({standing_seconds:.1f}초)"

        return {
            "score": score,
            "confidence": 0.6,
            "message": message,
            "details": {
                "standing_duration_seconds": round(standing_seconds, 1),
                "stable": stable,
                "height_variance": round(height_variance, 5) if standing_frames else 0
            }
        }

    def _analyze_feet_together_standing(self, frame_data: List[Dict], fps: float) -> Dict:
        """
        항목 7: 두발을 붙이고 서 있기 분석

        0점: 도움 필요, 15초 불가
        1점: 도움으로 15초
        2점: 30초 (지지 필요)
        3점: 독립적 1분
        4점: 혼자서 1분 안전하게
        """
        standing_frames = [f for f in frame_data if f['is_standing']]

        if len(standing_frames) < 10:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "서있는 구간이 감지되지 않았습니다",
                "details": {}
            }

        # 발을 모은 상태로 서있는 프레임
        feet_together_frames = [f for f in standing_frames if f['feet_distance'] < self.FEET_TOGETHER_THRESHOLD]

        if len(feet_together_frames) < 5:
            return {
                "score": None,
                "confidence": 0.4,
                "message": "발을 모은 자세가 감지되지 않았습니다",
                "details": {
                    "avg_feet_distance": round(np.mean([f['feet_distance'] for f in standing_frames]), 3)
                }
            }

        # 연속으로 발을 모은 시간
        max_duration = 0
        current_duration = 0

        for f in frame_data:
            if f['is_standing'] and f['feet_distance'] < self.FEET_TOGETHER_THRESHOLD:
                current_duration += 1
            else:
                max_duration = max(max_duration, current_duration)
                current_duration = 0
        max_duration = max(max_duration, current_duration)

        feet_together_seconds = max_duration / fps if fps > 0 else 0

        # 점수 결정
        if feet_together_seconds >= 60:
            score = 4
            message = f"발을 모으고 {feet_together_seconds:.1f}초 동안 안전하게 서있음"
        elif feet_together_seconds >= 30:
            score = 2
            message = f"발을 모으고 {feet_together_seconds:.1f}초 동안 서있음"
        elif feet_together_seconds >= 15:
            score = 1
            message = f"발을 모으고 {feet_together_seconds:.1f}초 동안 서있음"
        else:
            score = 0
            message = f"발을 모으고 15초 이상 서있지 못함 ({feet_together_seconds:.1f}초)"

        return {
            "score": score,
            "confidence": 0.6,
            "message": message,
            "details": {
                "feet_together_duration": round(feet_together_seconds, 1),
                "avg_feet_distance": round(np.mean([f['feet_distance'] for f in feet_together_frames]), 3)
            }
        }

    def _analyze_turn_360(self, frame_data: List[Dict], fps: float) -> Dict:
        """
        항목 11: 360도 회전 분석

        0점: 회전에 도움 필요
        1점: 감독/지시 필요
        2점: 안전하지만 느림
        3점: 한 방향 4초 이내
        4점: 양 방향 4초 이내
        """
        if len(frame_data) < 20:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "분석할 데이터가 부족합니다",
                "details": {}
            }

        # 어깨 방향 변화로 회전 감지
        directions = [f['shoulder_direction'] for f in frame_data]

        # 각도 변화 누적
        total_rotation = 0
        rotation_start = None
        rotation_end = None

        for i in range(1, len(directions)):
            diff = directions[i] - directions[i-1]
            # -π에서 π로 넘어가는 경우 처리
            if diff > math.pi:
                diff -= 2 * math.pi
            elif diff < -math.pi:
                diff += 2 * math.pi

            if abs(diff) > 0.05:  # 유의미한 회전
                if rotation_start is None:
                    rotation_start = i - 1
                total_rotation += diff
                rotation_end = i

        total_degrees = abs(math.degrees(total_rotation))

        if total_degrees < 180:
            return {
                "score": None,
                "confidence": 0.4,
                "message": f"360도 회전이 감지되지 않았습니다 ({total_degrees:.0f}도 회전)",
                "details": {"detected_rotation": round(total_degrees, 1)}
            }

        # 회전 시간 계산
        if rotation_start is not None and rotation_end is not None:
            rotation_duration = (rotation_end - rotation_start) / fps if fps > 0 else 0
        else:
            rotation_duration = 0

        # 점수 결정
        if total_degrees >= 360 and rotation_duration <= 4:
            score = 4 if total_degrees >= 360 else 3
            message = f"{total_degrees:.0f}도 회전, {rotation_duration:.1f}초 소요"
        elif total_degrees >= 360:
            score = 2
            message = f"360도 회전 완료, {rotation_duration:.1f}초 (느림)"
        else:
            score = 1
            message = f"부분 회전 ({total_degrees:.0f}도)"

        return {
            "score": score,
            "confidence": 0.5,
            "message": message,
            "details": {
                "total_rotation_degrees": round(total_degrees, 1),
                "rotation_duration": round(rotation_duration, 2)
            }
        }

    def _analyze_one_leg_standing(self, frame_data: List[Dict], fps: float) -> Dict:
        """
        항목 14: 한 다리로 서 있기 분석

        0점: 3초 유지 못함
        1점: 3초 이상
        2점: 5-10초
        3점: 10초
        4점: 10초 이상
        """
        # 한 발이 들린 프레임 찾기
        one_leg_frames = [f for f in frame_data if f['lifted_foot'] is not None]

        if len(one_leg_frames) < 5:
            return {
                "score": None,
                "confidence": 0.4,
                "message": "한 발 들기 자세가 감지되지 않았습니다",
                "details": {}
            }

        # 연속 한 발 서기 시간
        max_duration = 0
        current_duration = 0

        for f in frame_data:
            if f['lifted_foot'] is not None:
                current_duration += 1
            else:
                max_duration = max(max_duration, current_duration)
                current_duration = 0
        max_duration = max(max_duration, current_duration)

        one_leg_seconds = max_duration / fps if fps > 0 else 0

        # 점수 결정
        if one_leg_seconds >= 10:
            score = 4
            message = f"한 발로 {one_leg_seconds:.1f}초 동안 서있음"
        elif one_leg_seconds >= 5:
            score = 2
            message = f"한 발로 {one_leg_seconds:.1f}초 동안 서있음"
        elif one_leg_seconds >= 3:
            score = 1
            message = f"한 발로 {one_leg_seconds:.1f}초 동안 서있음"
        else:
            score = 0
            message = f"한 발로 3초 이상 서있지 못함 ({one_leg_seconds:.1f}초)"

        return {
            "score": score,
            "confidence": 0.6,
            "message": message,
            "details": {
                "one_leg_duration": round(one_leg_seconds, 1),
                "lifted_foot": one_leg_frames[0]['lifted_foot'] if one_leg_frames else None
            }
        }

    def _analyze_sitting_unsupported(self, frame_data: List[Dict], fps: float) -> Dict:
        """
        항목 3: 등받이에 기대지 않고 앉기 분석

        0점: 도움없이는 10초 동안 앉아 있을 수 없다
        1점: 10초 동안 앉아 있을 수 있다
        2점: 30초 동안 앉아 있을 수 있다
        3점: 감독 하에 2분 동안 앉을 수 있다
        4점: 2분 동안 안전하게 앉아있을 수 있다
        """
        sitting_frames = [f for f in frame_data if f['is_sitting']]

        if len(sitting_frames) < 5:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "앉은 자세가 감지되지 않았습니다",
                "details": {}
            }

        # 연속 앉은 시간 측정
        max_sitting_duration = 0
        current_duration = 0

        for f in frame_data:
            if f['is_sitting']:
                current_duration += 1
            else:
                max_sitting_duration = max(max_sitting_duration, current_duration)
                current_duration = 0
        max_sitting_duration = max(max_sitting_duration, current_duration)

        sitting_seconds = max_sitting_duration / fps if fps > 0 else 0

        # 안정성 확인 (엉덩이 높이 변동)
        if sitting_frames:
            height_variance = np.var([f['hip_height'] for f in sitting_frames])
            stable = height_variance < 0.002
        else:
            stable = False

        # 점수 결정
        if sitting_seconds >= 120 and stable:
            score = 4
            message = f"안전하게 {sitting_seconds:.1f}초 동안 앉아있음"
        elif sitting_seconds >= 120:
            score = 3
            message = f"{sitting_seconds:.1f}초 동안 앉아있음"
        elif sitting_seconds >= 30:
            score = 2
            message = f"{sitting_seconds:.1f}초 동안 앉아있음"
        elif sitting_seconds >= 10:
            score = 1
            message = f"{sitting_seconds:.1f}초 동안 앉아있음"
        else:
            score = 0
            message = f"10초 이상 앉아있지 못함 ({sitting_seconds:.1f}초)"

        return {
            "score": score,
            "confidence": 0.6,
            "message": message,
            "details": {
                "sitting_duration_seconds": round(sitting_seconds, 1),
                "stable": stable
            }
        }

    def _analyze_transfers(self, frame_data: List[Dict], fps: float) -> Dict:
        """
        항목 5: 의자에서 의자로 이동하기 분석

        0점: 두 사람의 도움이나 보조가 필요하다
        1점: 한 사람의 도움이 필요하다
        2점: 말로 지시하거나 감독이 필요하다
        3점: 완전히 손을 사용하여 안전하게 옮길 수 있다
        4점: 손을 거의 사용하지 않고 안전하게 이동할 수 있다
        """
        # 앉았다가 일어섰다가 다시 앉는 패턴 찾기
        sitting_frames = [i for i, f in enumerate(frame_data) if f['is_sitting']]
        standing_frames = [i for i, f in enumerate(frame_data) if f['is_standing']]

        if len(sitting_frames) < 10 or len(standing_frames) < 5:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "이동 동작이 감지되지 않았습니다",
                "details": {}
            }

        # 앉음 -> 서기 -> 앉음 패턴 확인
        transfer_detected = False
        first_sit = min(sitting_frames) if sitting_frames else -1
        first_stand_after_sit = None
        second_sit = None

        for i in standing_frames:
            if i > first_sit:
                first_stand_after_sit = i
                break

        if first_stand_after_sit:
            for i in sitting_frames:
                if i > first_stand_after_sit:
                    second_sit = i
                    transfer_detected = True
                    break

        if not transfer_detected:
            return {
                "score": None,
                "confidence": 0.4,
                "message": "의자 이동 패턴이 감지되지 않았습니다",
                "details": {}
            }

        # 이동 중 손 사용 여부
        transfer_frames = frame_data[first_sit:second_sit+1] if second_sit else frame_data[first_sit:]
        hand_support_frames = sum(1 for f in transfer_frames if f['using_hands'])
        hand_support_ratio = hand_support_frames / len(transfer_frames) if transfer_frames else 0
        used_hands = hand_support_ratio > 0.3

        # 안정성 (서있는 동안 높이 변동)
        standing_during_transfer = [f for f in transfer_frames if f['is_standing']]
        if standing_during_transfer:
            height_variance = np.var([f['hip_height'] for f in standing_during_transfer])
            stable = height_variance < 0.003
        else:
            stable = True

        # 점수 결정
        if not used_hands and stable:
            score = 4
            message = "손을 거의 사용하지 않고 안전하게 이동"
        elif used_hands and stable:
            score = 3
            message = "손을 사용하여 안전하게 이동"
        elif stable:
            score = 2
            message = "감독 하에 이동 완료"
        else:
            score = 2
            message = "이동 완료 (상세 분석 필요)"

        return {
            "score": score,
            "confidence": 0.5,
            "message": message,
            "details": {
                "used_hands": used_hands,
                "hand_support_ratio": round(hand_support_ratio, 2),
                "stable": stable
            }
        }

    def _analyze_standing_eyes_closed(self, frame_data: List[Dict], fps: float) -> Dict:
        """
        항목 6: 두눈을 감고 서 있기 분석
        (눈 감기는 영상으로 정확히 판단하기 어려우므로 서있기 안정성으로 대체 평가)

        0점: 넘어지는 것을 방지하기 위하여 도움이 필요하다
        1점: 안전하게 서 있으나 3초 동안 유지할 수는 없다
        2점: 3초 동안 서 있을 수 있다
        3점: 감독 하에 10초동안 서 있을 수 있다
        4점: 10초동안 안전하게 서 있을 수 있다
        """
        standing_frames = [f for f in frame_data if f['is_standing']]

        if len(standing_frames) < 5:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "서있는 구간이 감지되지 않았습니다",
                "details": {}
            }

        # 연속 서있는 시간
        max_standing_duration = 0
        current_duration = 0

        for f in frame_data:
            if f['is_standing']:
                current_duration += 1
            else:
                max_standing_duration = max(max_standing_duration, current_duration)
                current_duration = 0
        max_standing_duration = max(max_standing_duration, current_duration)

        standing_seconds = max_standing_duration / fps if fps > 0 else 0

        # 균형 안정성 (더 엄격하게 - 눈 감고 서기)
        if standing_frames:
            height_variance = np.var([f['hip_height'] for f in standing_frames])
            stable = height_variance < 0.001  # 더 엄격한 기준
        else:
            stable = False

        # 점수 결정
        if standing_seconds >= 10 and stable:
            score = 4
            message = f"안전하게 {standing_seconds:.1f}초 동안 서있음"
        elif standing_seconds >= 10:
            score = 3
            message = f"{standing_seconds:.1f}초 동안 서있음 (균형 변동 있음)"
        elif standing_seconds >= 3:
            score = 2
            message = f"{standing_seconds:.1f}초 동안 서있음"
        elif standing_seconds >= 1:
            score = 1
            message = f"{standing_seconds:.1f}초만 유지 가능"
        else:
            score = 0
            message = "서있기 유지 어려움"

        return {
            "score": score,
            "confidence": 0.5,
            "message": message + " (눈 감기 여부는 영상으로 확인 필요)",
            "details": {
                "standing_duration_seconds": round(standing_seconds, 1),
                "stable": stable,
                "height_variance": round(height_variance, 5) if standing_frames else 0
            }
        }

    def _analyze_reaching_forward(self, frame_data: List[Dict], fps: float) -> Dict:
        """
        항목 8: 선자세에서 앞으로 팔 뻗기 분석

        0점: 넘어지지 않기 위해 도움이 필요하다
        1점: 앞으로 뻗을 수 있으나 감독이 필요하다
        2점: 5cm 이상 안전하게 앞으로 뻗을 수 있다
        3점: 12.5cm 이상 안전하게 앞으로 뻗을 수 있다
        4점: 25cm 이상 앞으로 자신 있게 뻗을 수 있다
        """
        standing_frames = [f for f in frame_data if f['is_standing']]

        if len(standing_frames) < 5:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "서있는 구간이 감지되지 않았습니다",
                "details": {}
            }

        # 팔 뻗기 동작 감지 (손목이 앞으로 이동)
        max_forward_reach = max(f['wrist_forward'] for f in standing_frames)

        # 팔 뻗는 동안 균형 유지
        reaching_frames = [f for f in standing_frames if f['wrist_forward'] > 0.05]
        if reaching_frames:
            height_variance = np.var([f['hip_height'] for f in reaching_frames])
            stable_during_reach = height_variance < 0.002
        else:
            stable_during_reach = True

        if max_forward_reach < 0.03:
            return {
                "score": None,
                "confidence": 0.4,
                "message": "팔 뻗기 동작이 감지되지 않았습니다",
                "details": {"max_forward_reach": round(max_forward_reach, 3)}
            }

        # 점수 결정 (정규화된 값을 기준으로)
        # 대략 25cm = 0.15 정규화 값 (프레임 폭 기준)
        if max_forward_reach >= 0.15 and stable_during_reach:
            score = 4
            message = "충분히 앞으로 팔을 뻗음"
        elif max_forward_reach >= 0.08 and stable_during_reach:
            score = 3
            message = "적절히 앞으로 팔을 뻗음"
        elif max_forward_reach >= 0.05:
            score = 2
            message = "조금 앞으로 팔을 뻗음"
        else:
            score = 1
            message = "팔 뻗기 범위 제한적"

        return {
            "score": score,
            "confidence": 0.5,
            "message": message,
            "details": {
                "max_forward_reach": round(max_forward_reach, 3),
                "stable_during_reach": stable_during_reach
            }
        }

    def _analyze_pick_up_object(self, frame_data: List[Dict], fps: float) -> Dict:
        """
        항목 9: 바닥에서 물건 줍기 분석

        0점: 물건을 집으려고 시도해도 넘어지지 않게 하려면 도움이 필요하다
        1점: 물건을 집으려고 시도할 수 있으나 감독이 필요하다
        2점: 물건을 집을 수 없으나 2.5-5cm의 거리까지 손이 닿을 수 있다
        3점: 물건을 쉽게 집을 수 있으나 감독이 필요하다
        4점: 안전하고 쉽게 물건을 집을 수 있다
        """
        # 손목이 바닥 근처로 내려가는 프레임 찾기
        bending_frames = [f for f in frame_data if f['wrist_near_floor']]

        if len(bending_frames) < 3:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "물건 줍기 동작이 감지되지 않았습니다",
                "details": {}
            }

        # 허리 굽히기 동작 확인 (엉덩이 높이 감소)
        min_hip_height = min(f['hip_height'] for f in frame_data)
        max_hip_height = max(f['hip_height'] for f in frame_data)
        hip_height_change = max_hip_height - min_hip_height

        # 구부린 후 다시 일어나는지 확인
        recovered = False
        hip_heights = [f['hip_height'] for f in frame_data]
        min_idx = hip_heights.index(min_hip_height)
        if min_idx < len(hip_heights) - 5:
            post_bend_heights = hip_heights[min_idx:]
            if max(post_bend_heights) > min_hip_height + 0.1:
                recovered = True

        # 균형 유지
        if bending_frames:
            height_variance = np.var([f['hip_height'] for f in bending_frames])
            stable = height_variance < 0.003
        else:
            stable = True

        # 점수 결정
        if hip_height_change > 0.15 and recovered and stable:
            score = 4
            message = "안전하게 구부려서 물건을 집음"
        elif hip_height_change > 0.1 and recovered:
            score = 3
            message = "물건을 집을 수 있음"
        elif hip_height_change > 0.05:
            score = 2
            message = "구부리기는 하나 완전히 닿지 않음"
        else:
            score = 1
            message = "구부리기 범위 제한적"

        return {
            "score": score,
            "confidence": 0.5,
            "message": message,
            "details": {
                "hip_height_change": round(hip_height_change, 3),
                "recovered": recovered,
                "stable": stable
            }
        }

    def _analyze_turning_look_behind(self, frame_data: List[Dict], fps: float) -> Dict:
        """
        항목 10: 뒤돌아보기 분석

        0점: 넘어지지 않도록 하기 위해 도움이 필요하다
        1점: 돌아볼 때 감독이 필요하다
        2점: 옆으로만 돌아볼 수 있으나 균형을 유지한다
        3점: 한쪽으로만 돌아볼 수 있으나 다른 방향으로는 체중 이동이 감소한다
        4점: 좌우 양쪽으로 잘 돌아볼 수 있다
        """
        standing_frames = [f for f in frame_data if f['is_standing']]

        if len(standing_frames) < 10:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "서있는 구간이 감지되지 않았습니다",
                "details": {}
            }

        # 머리 방향 변화로 돌아보기 감지
        head_directions = [f['head_direction'] for f in standing_frames]
        max_left = min(head_directions)  # 왼쪽으로 돌아봄
        max_right = max(head_directions)  # 오른쪽으로 돌아봄

        total_range = max_right - max_left
        turned_left = abs(max_left) > 0.05
        turned_right = abs(max_right) > 0.05

        # 균형 유지
        height_variance = np.var([f['hip_height'] for f in standing_frames])
        stable = height_variance < 0.002

        if total_range < 0.05:
            return {
                "score": None,
                "confidence": 0.4,
                "message": "뒤돌아보기 동작이 감지되지 않았습니다",
                "details": {"head_turn_range": round(total_range, 3)}
            }

        # 점수 결정
        if turned_left and turned_right and stable:
            score = 4
            message = "좌우 양쪽으로 잘 돌아봄"
        elif (turned_left or turned_right) and stable:
            score = 3
            message = "한쪽으로 돌아볼 수 있음"
        elif stable:
            score = 2
            message = "옆으로 돌아보며 균형 유지"
        else:
            score = 1
            message = "돌아볼 때 균형 불안정"

        return {
            "score": score,
            "confidence": 0.5,
            "message": message,
            "details": {
                "turned_left": turned_left,
                "turned_right": turned_right,
                "head_turn_range": round(total_range, 3),
                "stable": stable
            }
        }

    def _analyze_stool_stepping(self, frame_data: List[Dict], fps: float) -> Dict:
        """
        항목 12: 발판 위에 발 교대로 올리기 분석

        0점: 넘어지지 않도록 하기 위해 도움이 필요하거나 과제를 수행할 수 없다
        1점: 도움을 받아 2회 이상 발판위에 올릴 수 있다
        2점: 보조없이 4회 이상 발판에 발을 올릴 수 있다
        3점: 혼자서 20초이내에 완전하게 교대로 8회 올릴 수 있다
        4점: 혼자 안전하게 서서 20초 이내에 완전하게 교대로 8회 올릴 수 있다
        """
        # 발 들기 동작 (스텝) 감지
        stepping_frames = [f for f in frame_data if f['stepping_foot'] is not None]

        if len(stepping_frames) < 3:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "발판 올리기 동작이 감지되지 않았습니다",
                "details": {}
            }

        # 스텝 횟수 계산 (발 교대)
        step_count = 0
        last_foot = None
        for f in frame_data:
            if f['stepping_foot'] is not None and f['stepping_foot'] != last_foot:
                step_count += 1
                last_foot = f['stepping_foot']

        # 스텝 시간
        first_step_frame = None
        last_step_frame = None
        for i, f in enumerate(frame_data):
            if f['stepping_foot'] is not None:
                if first_step_frame is None:
                    first_step_frame = i
                last_step_frame = i

        step_duration = (last_step_frame - first_step_frame) / fps if first_step_frame and last_step_frame and fps > 0 else 0

        # 균형 유지
        height_variance = np.var([f['hip_height'] for f in stepping_frames])
        stable = height_variance < 0.003

        # 점수 결정
        if step_count >= 8 and step_duration <= 20 and stable:
            score = 4
            message = f"안전하게 {step_count}회 교대로 올림 ({step_duration:.1f}초)"
        elif step_count >= 8 and step_duration <= 20:
            score = 3
            message = f"{step_count}회 교대로 올림 ({step_duration:.1f}초)"
        elif step_count >= 4:
            score = 2
            message = f"보조없이 {step_count}회 올림"
        elif step_count >= 2:
            score = 1
            message = f"{step_count}회 올림"
        else:
            score = 0
            message = "발판 올리기 어려움"

        return {
            "score": score,
            "confidence": 0.5,
            "message": message,
            "details": {
                "step_count": step_count,
                "step_duration": round(step_duration, 1),
                "stable": stable
            }
        }

    def _analyze_tandem_standing(self, frame_data: List[Dict], fps: float) -> Dict:
        """
        항목 13: 일렬로 서기 (탄뎀) 분석

        0점: 발을 내딛거나 서 있는 동안 균형을 잃는다
        1점: 발을 내딛는데 도움이 필요하나 15초 동안 유지할 수 있다
        2점: 혼자 발을 크게 내딛어 30초 동안 서 있을 수 있다
        3점: 혼자 발을 붙여서 30초 동안 유지할 수 있다
        4점: 혼자 일렬로 30초 동안 서 있을 수 있다
        """
        standing_frames = [f for f in frame_data if f['is_standing']]

        if len(standing_frames) < 10:
            return {
                "score": None,
                "confidence": 0.3,
                "message": "서있는 구간이 감지되지 않았습니다",
                "details": {}
            }

        # 일렬 서기 (탄뎀) 프레임 찾기
        tandem_frames = [f for f in standing_frames if f['is_tandem']]

        if len(tandem_frames) < 5:
            return {
                "score": None,
                "confidence": 0.4,
                "message": "일렬 서기 자세가 감지되지 않았습니다",
                "details": {
                    "avg_feet_lateral_diff": round(np.mean([f['feet_lateral_diff'] for f in standing_frames]), 3)
                }
            }

        # 연속 일렬 서기 시간
        max_duration = 0
        current_duration = 0

        for f in frame_data:
            if f['is_standing'] and f['is_tandem']:
                current_duration += 1
            else:
                max_duration = max(max_duration, current_duration)
                current_duration = 0
        max_duration = max(max_duration, current_duration)

        tandem_seconds = max_duration / fps if fps > 0 else 0

        # 균형 안정성
        if tandem_frames:
            height_variance = np.var([f['hip_height'] for f in tandem_frames])
            stable = height_variance < 0.002
        else:
            stable = False

        # 점수 결정
        if tandem_seconds >= 30 and stable:
            score = 4
            message = f"일렬로 {tandem_seconds:.1f}초 동안 안전하게 서있음"
        elif tandem_seconds >= 30:
            score = 3
            message = f"일렬로 {tandem_seconds:.1f}초 동안 서있음"
        elif tandem_seconds >= 15:
            score = 2
            message = f"일렬로 {tandem_seconds:.1f}초 동안 서있음"
        elif tandem_seconds >= 5:
            score = 1
            message = f"일렬로 {tandem_seconds:.1f}초 유지"
        else:
            score = 0
            message = "일렬 서기 유지 어려움"

        return {
            "score": score,
            "confidence": 0.5,
            "message": message,
            "details": {
                "tandem_duration": round(tandem_seconds, 1),
                "stable": stable
            }
        }
