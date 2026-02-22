"""
BBS Test Action Recognition Service

Automatically detects which BBS test is being performed based on motion patterns.
"""

import numpy as np
from typing import Optional, List, Tuple
from .angle_calculator import (
    calculate_knee_angle,
    calculate_hip_angle,
    calculate_trunk_angle,
    calculate_spine_rotation,
    calculate_base_of_support_width
)


class ActionRecognitionService:
    """
    Automatically recognizes which BBS test is being performed
    by analyzing pose motion patterns.
    """

    TEST_PATTERNS = {
        1: {
            'name': 'Sitting to Standing',
            'name_ko': '앉아서 일어서기',
            'key_features': ['knee_extension', 'hip_extension', 'vertical_rise']
        },
        2: {
            'name': 'Standing Unsupported',
            'name_ko': '지지없이 서기',
            'key_features': ['standing_still', 'minimal_sway', 'long_duration']
        },
        3: {
            'name': 'Sitting Unsupported',
            'name_ko': '지지없이 앉기',
            'key_features': ['sitting_posture', 'minimal_movement']
        },
        4: {
            'name': 'Standing to Sitting',
            'name_ko': '서서 앉기',
            'key_features': ['knee_flexion', 'hip_flexion', 'vertical_descent']
        },
        5: {
            'name': 'Transfers',
            'name_ko': '이동하기',
            'key_features': ['lateral_movement', 'sit_stand_sit']
        },
        6: {
            'name': 'Standing Eyes Closed',
            'name_ko': '눈감고 서기',
            'key_features': ['standing_still', 'increased_sway']
        },
        7: {
            'name': 'Standing Feet Together',
            'name_ko': '두발 모으고 서기',
            'key_features': ['narrow_base', 'standing_still']
        },
        8: {
            'name': 'Reaching Forward',
            'name_ko': '팔 뻗기',
            'key_features': ['arm_forward_reach', 'trunk_lean']
        },
        9: {
            'name': 'Retrieving Object',
            'name_ko': '바닥 물건 집기',
            'key_features': ['deep_trunk_flexion', 'arm_down_reach']
        },
        10: {
            'name': 'Turning Look Behind',
            'name_ko': '뒤돌아보기',
            'key_features': ['trunk_rotation', 'head_turn']
        },
        11: {
            'name': 'Turning 360',
            'name_ko': '360도 회전',
            'key_features': ['full_rotation', 'stepping']
        },
        12: {
            'name': 'Alternate Foot on Stool',
            'name_ko': '발판 발 교대',
            'key_features': ['alternating_leg_lift', 'stepping_pattern']
        },
        13: {
            'name': 'One Foot in Front',
            'name_ko': '일렬로 서기',
            'key_features': ['tandem_stance', 'narrow_base']
        },
        14: {
            'name': 'Standing One Foot',
            'name_ko': '한발 서기',
            'key_features': ['single_leg_stance', 'leg_lifted']
        }
    }

    def __init__(self, fps: float = 30.0):
        self.fps = fps

    def recognize_test(self, pose_data: List[dict]) -> Tuple[int, float, dict]:
        """
        Analyze pose data and recognize which BBS test is being performed.

        Args:
            pose_data: List of frame data with landmarks

        Returns:
            Tuple of (test_id, confidence, analysis_details)
        """
        valid_frames = [f for f in pose_data if f.get('has_pose') and f.get('landmarks')]

        if len(valid_frames) < 10:
            return 0, 0.0, {'error': 'Not enough valid frames'}

        scores = {}

        scores[1] = self._detect_sit_to_stand(valid_frames)
        scores[2] = self._detect_standing_unsupported(valid_frames)
        scores[3] = self._detect_sitting_unsupported(valid_frames)
        scores[4] = self._detect_stand_to_sit(valid_frames)
        scores[6] = self._detect_standing_eyes_closed(valid_frames)
        scores[7] = self._detect_feet_together(valid_frames)
        scores[8] = self._detect_reaching_forward(valid_frames)
        scores[9] = self._detect_retrieving_object(valid_frames)
        scores[10] = self._detect_turning_look_behind(valid_frames)
        scores[11] = self._detect_turning_360(valid_frames)
        scores[12] = self._detect_alternate_foot(valid_frames)
        scores[13] = self._detect_tandem_stance(valid_frames)
        scores[14] = self._detect_single_leg_stance(valid_frames)
        scores[5] = self._detect_transfers(valid_frames)

        best_test = max(scores, key=scores.get)
        best_score = scores[best_test]

        total_score = sum(scores.values())
        confidence = best_score / total_score if total_score > 0 else 0.0

        analysis = {
            'all_scores': scores,
            'detected_test': best_test,
            'test_name': self.TEST_PATTERNS[best_test]['name'],
            'test_name_ko': self.TEST_PATTERNS[best_test]['name_ko'],
            'confidence': confidence
        }

        return best_test, confidence, analysis

    def _get_knee_angles(self, frames: List[dict]) -> List[float]:
        """Get knee angles for all frames."""
        angles = []
        for frame in frames:
            lm = frame['landmarks']
            try:
                angle = (calculate_knee_angle(lm, 'left') + calculate_knee_angle(lm, 'right')) / 2
                angles.append(angle)
            except:
                pass
        return angles

    def _get_hip_heights(self, frames: List[dict]) -> List[float]:
        """Get hip Y positions for all frames."""
        heights = []
        for frame in frames:
            lm = frame['landmarks']
            try:
                hip_y = (lm['left_hip']['y'] + lm['right_hip']['y']) / 2
                heights.append(hip_y)
            except:
                pass
        return heights

    def _detect_sit_to_stand(self, frames: List[dict]) -> float:
        """Detect sitting to standing motion."""
        knee_angles = self._get_knee_angles(frames)
        hip_heights = self._get_hip_heights(frames)

        if len(knee_angles) < 5:
            return 0.0

        score = 0.0

        min_angle = min(knee_angles[:len(knee_angles)//3])
        max_angle = max(knee_angles[-len(knee_angles)//3:])

        if min_angle < 120 and max_angle > 150:
            angle_change = max_angle - min_angle
            score += min(angle_change / 60, 1.0) * 50

        if hip_heights:
            initial_height = np.mean(hip_heights[:5])
            final_height = np.mean(hip_heights[-5:])
            if final_height < initial_height:
                height_change = initial_height - final_height
                score += min(height_change * 100, 50)

        return score

    def _detect_stand_to_sit(self, frames: List[dict]) -> float:
        """Detect standing to sitting motion."""
        knee_angles = self._get_knee_angles(frames)
        hip_heights = self._get_hip_heights(frames)

        if len(knee_angles) < 5:
            return 0.0

        score = 0.0

        max_angle = max(knee_angles[:len(knee_angles)//3])
        min_angle = min(knee_angles[-len(knee_angles)//3:])

        if max_angle > 150 and min_angle < 120:
            angle_change = max_angle - min_angle
            score += min(angle_change / 60, 1.0) * 50

        if hip_heights:
            initial_height = np.mean(hip_heights[:5])
            final_height = np.mean(hip_heights[-5:])
            if final_height > initial_height:
                height_change = final_height - initial_height
                score += min(height_change * 100, 50)

        return score

    def _detect_standing_unsupported(self, frames: List[dict]) -> float:
        """Detect standing unsupported (minimal movement)."""
        knee_angles = self._get_knee_angles(frames)

        if len(knee_angles) < 10:
            return 0.0

        score = 0.0

        standing_frames = sum(1 for a in knee_angles if a > 155)
        standing_ratio = standing_frames / len(knee_angles)

        if standing_ratio > 0.8:
            score += 40

        angle_std = np.std(knee_angles)
        if angle_std < 10:
            score += 30

        duration = len(frames) / self.fps
        if duration > 10:
            score += 30

        return score

    def _detect_sitting_unsupported(self, frames: List[dict]) -> float:
        """Detect sitting unsupported."""
        knee_angles = self._get_knee_angles(frames)

        if len(knee_angles) < 10:
            return 0.0

        score = 0.0

        sitting_frames = sum(1 for a in knee_angles if a < 125)
        sitting_ratio = sitting_frames / len(knee_angles)

        if sitting_ratio > 0.8:
            score += 50

        angle_std = np.std(knee_angles)
        if angle_std < 10:
            score += 30

        duration = len(frames) / self.fps
        if duration > 10:
            score += 20

        return score

    def _detect_standing_eyes_closed(self, frames: List[dict]) -> float:
        """Detect standing with eyes closed (more sway than normal standing)."""
        knee_angles = self._get_knee_angles(frames)

        if len(knee_angles) < 10:
            return 0.0

        score = 0.0

        standing_frames = sum(1 for a in knee_angles if a > 155)
        standing_ratio = standing_frames / len(knee_angles)

        if standing_ratio > 0.8:
            score += 30

        angle_std = np.std(knee_angles)
        if 5 < angle_std < 20:
            score += 40

        duration = len(frames) / self.fps
        if 8 < duration < 15:
            score += 30

        return score

    def _detect_feet_together(self, frames: List[dict]) -> float:
        """Detect standing with feet together."""
        score = 0.0
        narrow_count = 0

        for frame in frames:
            lm = frame['landmarks']
            try:
                base_width = calculate_base_of_support_width(lm)
                if base_width < 0.15:
                    narrow_count += 1
            except:
                pass

        if frames:
            narrow_ratio = narrow_count / len(frames)
            if narrow_ratio > 0.7:
                score += 60

        knee_angles = self._get_knee_angles(frames)
        if knee_angles:
            standing_frames = sum(1 for a in knee_angles if a > 155)
            if standing_frames / len(knee_angles) > 0.8:
                score += 40

        return score

    def _detect_reaching_forward(self, frames: List[dict]) -> float:
        """Detect reaching forward with arm."""
        score = 0.0

        wrist_x_positions = []
        for frame in frames:
            lm = frame['landmarks']
            try:
                wrist_x = (lm['left_wrist']['x'] + lm['right_wrist']['x']) / 2
                wrist_x_positions.append(wrist_x)
            except:
                pass

        if len(wrist_x_positions) < 5:
            return 0.0

        initial_x = np.mean(wrist_x_positions[:5])
        max_x = max(wrist_x_positions)
        reach_distance = abs(max_x - initial_x)

        if reach_distance > 0.1:
            score += min(reach_distance * 300, 60)

        knee_angles = self._get_knee_angles(frames)
        if knee_angles:
            standing_frames = sum(1 for a in knee_angles if a > 150)
            if standing_frames / len(knee_angles) > 0.7:
                score += 40

        return score

    def _detect_retrieving_object(self, frames: List[dict]) -> float:
        """Detect picking up object from floor."""
        score = 0.0

        wrist_y_positions = []
        trunk_angles = []

        for frame in frames:
            lm = frame['landmarks']
            try:
                wrist_y = min(lm['left_wrist']['y'], lm['right_wrist']['y'])
                wrist_y_positions.append(wrist_y)
                trunk_angle = calculate_trunk_angle(lm)
                trunk_angles.append(trunk_angle)
            except:
                pass

        if len(wrist_y_positions) < 5:
            return 0.0

        max_wrist_y = max(wrist_y_positions)
        if max_wrist_y > 0.8:
            score += 50

        if trunk_angles:
            max_trunk = max(trunk_angles)
            if max_trunk > 45:
                score += 50

        return score

    def _detect_turning_look_behind(self, frames: List[dict]) -> float:
        """Detect turning to look behind."""
        score = 0.0
        rotations = []

        for frame in frames:
            lm = frame['landmarks']
            try:
                rotation = calculate_spine_rotation(lm)
                rotations.append(rotation)
            except:
                pass

        if len(rotations) < 5:
            return 0.0

        max_rotation = max(rotations)

        if max_rotation > 20:
            score += min(max_rotation * 2, 60)

        knee_angles = self._get_knee_angles(frames)
        if knee_angles:
            standing_ratio = sum(1 for a in knee_angles if a > 150) / len(knee_angles)
            if standing_ratio > 0.7:
                score += 40

        return score

    def _detect_turning_360(self, frames: List[dict]) -> float:
        """Detect 360 degree turn."""
        score = 0.0

        shoulder_angles = []
        for frame in frames:
            lm = frame['landmarks']
            try:
                dx = lm['right_shoulder']['x'] - lm['left_shoulder']['x']
                dy = lm['right_shoulder']['y'] - lm['left_shoulder']['y']
                angle = np.arctan2(dy, dx)
                shoulder_angles.append(angle)
            except:
                pass

        if len(shoulder_angles) < 10:
            return 0.0

        total_rotation = 0
        for i in range(1, len(shoulder_angles)):
            diff = shoulder_angles[i] - shoulder_angles[i-1]
            if diff > np.pi:
                diff -= 2 * np.pi
            elif diff < -np.pi:
                diff += 2 * np.pi
            total_rotation += abs(diff)

        if total_rotation > np.pi:
            score += min(total_rotation / (2 * np.pi) * 100, 100)

        return score

    def _detect_alternate_foot(self, frames: List[dict]) -> float:
        """Detect alternating foot on stool."""
        score = 0.0

        left_ankle_y = []
        right_ankle_y = []

        for frame in frames:
            lm = frame['landmarks']
            try:
                left_ankle_y.append(lm['left_ankle']['y'])
                right_ankle_y.append(lm['right_ankle']['y'])
            except:
                pass

        if len(left_ankle_y) < 10:
            return 0.0

        left_lifts = 0
        right_lifts = 0

        for i in range(1, len(left_ankle_y)):
            if left_ankle_y[i] < left_ankle_y[i-1] - 0.02:
                left_lifts += 1
            if right_ankle_y[i] < right_ankle_y[i-1] - 0.02:
                right_lifts += 1

        total_lifts = left_lifts + right_lifts
        if total_lifts >= 4:
            score += min(total_lifts * 10, 100)

        return score

    def _detect_tandem_stance(self, frames: List[dict]) -> float:
        """Detect tandem stance (one foot in front of other)."""
        score = 0.0
        tandem_count = 0

        for frame in frames:
            lm = frame['landmarks']
            try:
                left_ankle = lm['left_ankle']
                right_ankle = lm['right_ankle']

                x_diff = abs(left_ankle['x'] - right_ankle['x'])
                y_diff = abs(left_ankle['y'] - right_ankle['y'])

                if x_diff < 0.1 and y_diff > 0.05:
                    tandem_count += 1
            except:
                pass

        if frames:
            tandem_ratio = tandem_count / len(frames)
            if tandem_ratio > 0.5:
                score += tandem_ratio * 100

        return score

    def _detect_single_leg_stance(self, frames: List[dict]) -> float:
        """Detect standing on one leg."""
        score = 0.0
        single_leg_count = 0

        for frame in frames:
            lm = frame['landmarks']
            try:
                left_ankle_y = lm['left_ankle']['y']
                right_ankle_y = lm['right_ankle']['y']

                height_diff = abs(left_ankle_y - right_ankle_y)
                if height_diff > 0.1:
                    single_leg_count += 1
            except:
                pass

        if frames:
            single_leg_ratio = single_leg_count / len(frames)
            if single_leg_ratio > 0.5:
                score += single_leg_ratio * 100

        return score

    def _detect_transfers(self, frames: List[dict]) -> float:
        """Detect transfer movement (sit-stand-sit with lateral movement)."""
        sit_stand = self._detect_sit_to_stand(frames)
        stand_sit = self._detect_stand_to_sit(frames)

        if sit_stand > 30 and stand_sit > 30:
            return (sit_stand + stand_sit) / 2
        return 0.0
