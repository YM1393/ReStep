import os
import cv2
import numpy as np
import math
from typing import Dict, List, Tuple, Optional, Set
import mediapipe as mp

from analysis.bbs2 import BBSScoringService, ActionRecognitionService
from analysis.bbs2.landmark_converter import build_bbs2_frame


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
    """
    if landmarks is None:
        return image

    LEFT_COLOR = (255, 150, 0)
    RIGHT_COLOR = (0, 128, 255)
    CENTER_COLOR = (200, 200, 200)

    LEFT_LANDMARKS = {11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31}
    RIGHT_LANDMARKS = {12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32}
    CENTER_CONNECTIONS = {(11, 12), (23, 24)}

    h, w = image.shape[:2]

    landmark_points = {}
    for idx in BODY_LANDMARKS:
        if idx < len(landmarks.landmark):
            lm = landmarks.landmark[idx]
            if lm.visibility > 0.2:
                x = int(lm.x * w)
                y = int(lm.y * h)
                landmark_points[idx] = (x, y)

    for connection in BODY_CONNECTIONS:
        start_idx, end_idx = connection
        if start_idx in landmark_points and end_idx in landmark_points:
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

    for idx, point in landmark_points.items():
        if idx in LEFT_LANDMARKS:
            color = LEFT_COLOR
        elif idx in RIGHT_LANDMARKS:
            color = RIGHT_COLOR
        else:
            color = CENTER_COLOR

        cv2.circle(image, point, circle_radius, color, -1)
        cv2.circle(image, point, circle_radius, (255, 255, 255), 1)

    return image


# BBS2 test ID → frontend item key mapping
TEST_ID_TO_ITEM_KEY = {
    1: "item1_sitting_to_standing",
    2: "item2_standing_unsupported",
    3: "item3_sitting_unsupported",
    4: "item4_standing_to_sitting",
    5: "item5_transfers",
    6: "item6_standing_eyes_closed",
    7: "item7_standing_feet_together",
    8: "item8_reaching_forward",
    9: "item9_pick_up_object",
    10: "item10_turning_to_look_behind",
    11: "item11_turn_360_degrees",
    12: "item12_stool_stepping",
    13: "item13_standing_one_foot_front",
    14: "item14_standing_on_one_leg",
}

ITEM_KEY_TO_TEST_ID = {v: k for k, v in TEST_ID_TO_ITEM_KEY.items()}


class BBSAnalyzer:
    """
    MediaPipe Pose + BBS2 채점 엔진을 사용한 BBS (Berg Balance Scale) 자동 평가 분석기

    MediaPipe로 포즈를 추출하고, BBS2의 BBSScoringService로 14개 항목을 채점합니다.
    """

    MODEL_COMPLEXITY = 2  # Heavy 모델

    def __init__(self):
        """MediaPipe Pose 모델 + BBS2 채점 엔진 초기화"""
        print(f"Loading MediaPipe Pose for BBS (model_complexity={self.MODEL_COMPLEXITY})")
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            model_complexity=self.MODEL_COMPLEXITY,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            static_image_mode=False
        )

    def _extract_pose_frames(
        self,
        video_path: str,
        progress_callback=None,
        frame_callback=None,
        video_writer=None
    ) -> Tuple[List[dict], float, int]:
        """
        영상에서 MediaPipe 포즈를 추출하고 BBS2 형식 프레임 리스트로 변환

        Returns:
            (bbs2_frames, fps, total_frames_processed)
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"영상을 열 수 없습니다: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = int(fps * 30) if fps > 0 else 900

        bbs2_frames = []
        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(frame_rgb)

            # 포즈 오버레이 + 콜백
            if results.pose_landmarks is not None:
                annotated_frame = frame.copy()
                draw_body_landmarks(annotated_frame, results.pose_landmarks)

                if video_writer is not None:
                    video_writer.write(annotated_frame)

                if frame_callback and frame_count % 3 == 0:
                    try:
                        frame_callback(annotated_frame)
                    except Exception as e:
                        print(f"[BBS] Frame callback failed: {e}")
            else:
                if video_writer is not None:
                    video_writer.write(frame)

            # MediaPipe → BBS2 형식 변환
            timestamp_ms = (frame_count / fps * 1000) if fps > 0 else 0
            bbs2_frame = build_bbs2_frame(
                results.pose_landmarks,
                frame_number=frame_count,
                timestamp_ms=timestamp_ms
            )
            bbs2_frames.append(bbs2_frame)

            frame_count += 1

            if progress_callback and total_frames > 0:
                progress = int((frame_count / total_frames) * 100)
                progress_callback(progress)

        cap.release()
        return bbs2_frames, fps, frame_count

    def _bbs2_result_to_frontend(self, bbs2_result: dict) -> dict:
        """BBS2 채점 결과를 프론트엔드 형식으로 변환"""
        return {
            "score": bbs2_result.get("score"),
            "confidence": bbs2_result.get("confidence", 0),
            "message": bbs2_result.get("reasoning", ""),
            "details": bbs2_result.get("criteria_met", {})
        }

    def analyze_video(
        self,
        video_path: str,
        test_item: str,
        progress_callback=None,
        frame_callback=None
    ) -> Dict:
        """
        영상을 분석하여 특정 BBS 항목 점수 반환

        Args:
            video_path: 영상 파일 경로
            test_item: BBS 항목 (item1_sitting_to_standing 등)
            progress_callback: 진행률 콜백
            frame_callback: 프레임 콜백

        Returns:
            점수 및 분석 데이터
        """
        test_id = ITEM_KEY_TO_TEST_ID.get(test_item)
        if test_id is None:
            return {
                "score": None,
                "confidence": 0,
                "message": f"'{test_item}' 항목은 지원되지 않습니다",
                "details": {}
            }

        bbs2_frames, fps, total_processed = self._extract_pose_frames(
            video_path,
            progress_callback=progress_callback,
            frame_callback=frame_callback
        )

        valid_frames = [f for f in bbs2_frames if f.get('has_pose')]
        if len(valid_frames) < 10:
            return {
                "score": 0,
                "confidence": 0,
                "message": "분석할 수 있는 프레임이 부족합니다",
                "details": {}
            }

        scoring = BBSScoringService(fps=fps)
        # Single camera → same data for front and side
        bbs2_result = scoring.score_test(test_id, bbs2_frames, bbs2_frames)

        return self._bbs2_result_to_frontend(bbs2_result)

    def analyze_all_items(
        self,
        video_path: str,
        progress_callback=None,
        frame_callback=None,
        save_overlay_video: bool = False
    ) -> Dict:
        """
        영상을 분석하여 가능한 모든 BBS 항목 평가
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"영상을 열 수 없습니다: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        cap.release()

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

        # 포즈 추출
        bbs2_frames, fps, total_processed = self._extract_pose_frames(
            video_path,
            progress_callback=progress_callback,
            frame_callback=frame_callback,
            video_writer=video_writer
        )

        if video_writer is not None:
            video_writer.release()
            print(f"[BBS] Overlay video saved: {overlay_video_path}")

        valid_frames = [f for f in bbs2_frames if f.get('has_pose')]
        if len(valid_frames) < 10:
            return {
                "scores": {},
                "message": "분석할 수 있는 프레임이 부족합니다"
            }

        # BBS2 채점 엔진으로 14개 항목 모두 분석
        scoring = BBSScoringService(fps=fps)
        scores = {}

        for test_id in range(1, 15):
            try:
                bbs2_result = scoring.score_test(test_id, bbs2_frames, bbs2_frames)
                item_key = TEST_ID_TO_ITEM_KEY[test_id]
                frontend_result = self._bbs2_result_to_frontend(bbs2_result)
                if frontend_result["score"] is not None:
                    scores[item_key] = frontend_result
            except Exception as e:
                print(f"[BBS] Error scoring test {test_id}: {e}")

        result = {
            "scores": scores,
            "total_frames": len(valid_frames),
            "fps": fps,
            "duration": len(valid_frames) / fps if fps > 0 else 0
        }
        if overlay_video_path and os.path.exists(overlay_video_path):
            result["overlay_video_path"] = overlay_video_path
        return result
