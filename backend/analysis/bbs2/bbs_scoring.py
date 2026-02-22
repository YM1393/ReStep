from typing import Any
from .angle_calculator import (
    calculate_hip_angle,
    calculate_knee_angle,
    calculate_trunk_angle,
    calculate_spine_rotation,
    calculate_base_of_support_width,
    get_center_of_mass
)
from .stability_analyzer import StabilityAnalyzer
import numpy as np


class BBSScoringService:
    """
    BBS (Berg Balance Scale) Scoring Service

    Scores 14 test items based on pose estimation data.
    Each test is scored 0-4 (total 56 points max).
    """

    BBS_TEST_NAMES = {
        1: "Sitting to Standing",
        2: "Standing Unsupported",
        3: "Sitting Unsupported",
        4: "Standing to Sitting",
        5: "Transfers",
        6: "Standing with Eyes Closed",
        7: "Standing with Feet Together",
        8: "Reaching Forward",
        9: "Retrieving Object from Floor",
        10: "Turning to Look Behind",
        11: "Turning 360 Degrees",
        12: "Placing Alternate Foot on Stool",
        13: "Standing with One Foot in Front",
        14: "Standing on One Foot"
    }

    def __init__(self, fps: float = 30.0):
        self.fps = fps

    def score_test(
        self,
        test_item_id: int,
        front_pose_data: list[dict],
        side_pose_data: list[dict],
        sync_offset_ms: float = 0.0
    ) -> dict[str, Any]:
        """
        Score a specific BBS test item.

        Returns:
            dict with score, confidence, reasoning, criteria_met
        """
        scorer_map = {
            1: self._score_sitting_to_standing,
            2: self._score_standing_unsupported,
            3: self._score_sitting_unsupported,
            4: self._score_standing_to_sitting,
            5: self._score_transfers,
            6: self._score_standing_eyes_closed,
            7: self._score_standing_feet_together,
            8: self._score_reaching_forward,
            9: self._score_retrieving_object,
            10: self._score_turning_look_behind,
            11: self._score_turning_360,
            12: self._score_alternate_foot_stool,
            13: self._score_one_foot_front,
            14: self._score_standing_one_foot
        }

        if test_item_id not in scorer_map:
            raise ValueError(f"Invalid test item ID: {test_item_id}")

        return scorer_map[test_item_id](front_pose_data, side_pose_data)

    def _get_valid_frames(self, pose_data: list[dict]) -> list[dict]:
        """Filter frames with valid pose data."""
        return [f for f in pose_data if f.get('has_pose') and f.get('landmarks')]

    def _score_sitting_to_standing(self, front_data: list, side_data: list) -> dict:
        """
        Test 1: Sitting to Standing
        4 = stand without using hands, stabilize independently
        3 = stand independently using hands
        2 = stand using hands after several tries
        1 = needs minimal aid to stand or stabilize
        0 = needs moderate or maximal assist
        """
        valid_frames = self._get_valid_frames(front_data)
        if not valid_frames:
            return self._no_pose_result("No valid pose data detected")

        sitting_frames = []
        standing_frames = []

        for frame in valid_frames:
            lm = frame['landmarks']
            knee_angle = (calculate_knee_angle(lm, 'left') + calculate_knee_angle(lm, 'right')) / 2

            if knee_angle < 120:
                sitting_frames.append(frame)
            elif knee_angle > 160:
                standing_frames.append(frame)

        if not sitting_frames or not standing_frames:
            return {
                'score': 2,
                'confidence': 0.5,
                'reasoning': "Could not clearly detect sitting and standing phases",
                'criteria_met': {'transition_detected': False}
            }

        stability = StabilityAnalyzer(standing_frames[-10:] if len(standing_frames) > 10 else standing_frames)
        sway = stability.calculate_sway_metrics()

        hands_used = self._detect_hand_support(valid_frames)
        stable = sway['max_excursion'] < 0.08

        if not hands_used and stable:
            score, reasoning = 4, "Able to stand without using hands and stabilize independently"
        elif not hands_used:
            score, reasoning = 3, "Able to stand without hands but with some instability"
        elif stable:
            score, reasoning = 3, "Able to stand independently using hands"
        else:
            score, reasoning = 2, "Able to stand using hands with some difficulty"

        return {
            'score': score,
            'confidence': 0.75,
            'reasoning': reasoning,
            'criteria_met': {
                'hands_used': hands_used,
                'stable_at_end': stable,
                'transition_detected': True
            }
        }

    def _score_standing_unsupported(self, front_data: list, side_data: list) -> dict:
        """
        Test 2: Standing Unsupported (2 minutes)
        4 = stand safely 2 minutes
        3 = stand 2 minutes with supervision
        2 = stand 30 seconds unsupported
        1 = needs several tries to stand 30 seconds
        0 = unable to stand 30 seconds unsupported
        """
        valid_frames = self._get_valid_frames(front_data)
        if not valid_frames:
            return self._no_pose_result("No valid pose data detected")

        stability = StabilityAnalyzer(valid_frames, self.fps)
        sway = stability.calculate_sway_metrics()
        duration_sec = len(valid_frames) / self.fps

        balance_events = stability.detect_loss_of_balance()
        is_stable = sway['max_excursion'] < 0.1 and len(balance_events) == 0

        if duration_sec >= 120 and is_stable:
            score, reasoning = 4, f"Able to stand safely for {duration_sec:.1f} seconds"
        elif duration_sec >= 120:
            score, reasoning = 3, f"Able to stand {duration_sec:.1f} seconds with minor instability"
        elif duration_sec >= 30 and is_stable:
            score, reasoning = 2, f"Able to stand {duration_sec:.1f} seconds unsupported"
        elif duration_sec >= 30:
            score, reasoning = 1, f"Stood {duration_sec:.1f} seconds with difficulty"
        else:
            score, reasoning = 0, f"Unable to stand for 30 seconds (stood {duration_sec:.1f}s)"

        return {
            'score': score,
            'confidence': 0.8,
            'reasoning': reasoning,
            'criteria_met': {
                'duration_2min': duration_sec >= 120,
                'duration_30sec': duration_sec >= 30,
                'stable': is_stable
            }
        }

    def _score_sitting_unsupported(self, front_data: list, side_data: list) -> dict:
        """
        Test 3: Sitting Unsupported (2 minutes)
        4 = sit safely and securely 2 minutes
        3 = sit 2 minutes under supervision
        2 = sit 30 seconds
        1 = sit 10 seconds
        0 = unable to sit without support 10 seconds
        """
        data_to_use = side_data if side_data else front_data
        valid_frames = self._get_valid_frames(data_to_use)
        if not valid_frames:
            return self._no_pose_result("No valid pose data detected")

        back_off_chair_frames = []
        for frame in valid_frames:
            lm = frame['landmarks']

            shoulder_x = (lm['left_shoulder']['x'] + lm['right_shoulder']['x']) / 2
            hip_x = (lm['left_hip']['x'] + lm['right_hip']['x']) / 2

            trunk_lean = shoulder_x - hip_x

            if trunk_lean >= -0.05:
                back_off_chair_frames.append(frame)

        back_off_duration_sec = len(back_off_chair_frames) / self.fps
        total_duration_sec = len(valid_frames) / self.fps

        if back_off_chair_frames:
            stability = StabilityAnalyzer(back_off_chair_frames, self.fps)
            sway = stability.calculate_sway_metrics()
            is_stable = sway['max_excursion'] < 0.08 and sway['ml_range'] < 0.06

            lateral_sway = sway['ml_range']
            ap_sway = sway['ap_range']
        else:
            is_stable = False
            lateral_sway = 0
            ap_sway = 0

        if back_off_duration_sec >= 120 and is_stable:
            score = 4
            reasoning = f"Sits safely and securely for {back_off_duration_sec:.0f} seconds"
        elif back_off_duration_sec >= 120:
            score = 3
            reasoning = f"Sits for {back_off_duration_sec:.0f} seconds with slight instability"
        elif back_off_duration_sec >= 30:
            score = 2
            reasoning = f"Sits unsupported for {back_off_duration_sec:.0f} seconds"
        elif back_off_duration_sec >= 10:
            score = 1
            reasoning = f"Sits unsupported for {back_off_duration_sec:.0f} seconds"
        else:
            score = 0
            if back_off_duration_sec > 0:
                reasoning = f"Unable to sit unsupported for 10 seconds ({back_off_duration_sec:.1f}s)"
            else:
                reasoning = "Unable to sit without back support"

        return {
            'score': score,
            'confidence': 0.8,
            'reasoning': reasoning,
            'criteria_met': {
                'back_off_chair': back_off_duration_sec >= 10,
                'duration_2min': back_off_duration_sec >= 120,
                'duration_30sec': back_off_duration_sec >= 30,
                'duration_10sec': back_off_duration_sec >= 10,
                'stable': is_stable,
                'lateral_sway_cm': round(lateral_sway * 100, 1),
                'ap_sway_cm': round(ap_sway * 100, 1)
            }
        }

    def _score_standing_to_sitting(self, front_data: list, side_data: list) -> dict:
        """
        Test 4: Standing to Sitting
        4 = sits safely with minimal use of hands
        3 = controls descent by using hands
        2 = uses back of legs against chair to control descent
        1 = sits independently but has uncontrolled descent
        0 = needs assistance to sit
        """
        valid_frames = self._get_valid_frames(side_data if side_data else front_data)
        if not valid_frames:
            return self._no_pose_result("No valid pose data detected")

        standing_phase = []
        sitting_phase = []

        for frame in valid_frames:
            lm = frame['landmarks']
            knee_angle = (calculate_knee_angle(lm, 'left') + calculate_knee_angle(lm, 'right')) / 2

            if knee_angle > 160:
                standing_phase.append(frame)
            elif knee_angle < 120:
                sitting_phase.append(frame)

        if not standing_phase or not sitting_phase:
            return {
                'score': 2,
                'confidence': 0.5,
                'reasoning': "Could not clearly detect transition phases",
                'criteria_met': {'transition_detected': False}
            }

        descent_controlled = self._analyze_descent_control(valid_frames)
        hands_used = self._detect_hand_support(valid_frames)

        if descent_controlled and not hands_used:
            score, reasoning = 4, "Sits safely with minimal use of hands"
        elif descent_controlled:
            score, reasoning = 3, "Controls descent by using hands"
        elif hands_used:
            score, reasoning = 2, "Uses support to control descent"
        else:
            score, reasoning = 1, "Sits independently but with uncontrolled descent"

        return {
            'score': score,
            'confidence': 0.7,
            'reasoning': reasoning,
            'criteria_met': {
                'controlled_descent': descent_controlled,
                'hands_used': hands_used,
                'transition_detected': True
            }
        }

    def _score_transfers(self, front_data: list, side_data: list) -> dict:
        """
        Test 5: Transfers
        4 = transfers safely with minor use of hands
        3 = transfers safely with definite need of hands
        2 = transfers with verbal cuing and/or supervision
        1 = needs one person to assist
        0 = needs two people to assist or supervise
        """
        valid_frames = self._get_valid_frames(front_data)
        if not valid_frames:
            return self._no_pose_result("No valid pose data detected")

        stability = StabilityAnalyzer(valid_frames, self.fps)
        sway = stability.calculate_sway_metrics()
        hands_used = self._detect_hand_support(valid_frames)

        if sway['max_excursion'] < 0.08 and not hands_used:
            score, reasoning = 4, "Transfers safely with minor use of hands"
        elif sway['max_excursion'] < 0.1:
            score, reasoning = 3, "Transfers safely with definite need of hands"
        else:
            score, reasoning = 2, "Transfers with some difficulty"

        return {
            'score': score,
            'confidence': 0.65,
            'reasoning': reasoning,
            'criteria_met': {
                'stable': sway['max_excursion'] < 0.1,
                'hands_used': hands_used
            }
        }

    def _score_standing_eyes_closed(self, front_data: list, side_data: list) -> dict:
        """
        Test 6: Standing with Eyes Closed (10 seconds)
        4 = stand 10 seconds safely
        3 = stand 10 seconds with supervision
        2 = stand 3 seconds
        1 = unable to keep eyes closed 3 seconds but stands safely
        0 = needs help to keep from falling
        """
        valid_frames = self._get_valid_frames(front_data)
        if not valid_frames:
            return self._no_pose_result("No valid pose data detected")

        stability = StabilityAnalyzer(valid_frames, self.fps)
        sway = stability.calculate_sway_metrics()
        duration_sec = len(valid_frames) / self.fps

        is_stable = sway['max_excursion'] < 0.12

        if duration_sec >= 10 and is_stable:
            score, reasoning = 4, "Able to stand 10 seconds safely"
        elif duration_sec >= 10:
            score, reasoning = 3, "Able to stand 10 seconds with supervision"
        elif duration_sec >= 3:
            score, reasoning = 2, f"Able to stand {duration_sec:.1f} seconds"
        else:
            score, reasoning = 1, "Unable to maintain position for 3 seconds"

        return {
            'score': score,
            'confidence': 0.75,
            'reasoning': reasoning,
            'criteria_met': {
                'duration_10sec': duration_sec >= 10,
                'duration_3sec': duration_sec >= 3,
                'stable': is_stable
            }
        }

    def _score_standing_feet_together(self, front_data: list, side_data: list) -> dict:
        """
        Test 7: Standing with Feet Together (1 minute)
        4 = place feet together independently and stand 1 minute safely
        3 = place feet together independently and stand 1 minute with supervision
        2 = place feet together independently and hold 30 seconds
        1 = needs help to attain position but able to stand 15 seconds
        0 = needs help to attain position and unable to hold 15 seconds
        """
        valid_frames = self._get_valid_frames(front_data)
        if not valid_frames:
            return self._no_pose_result("No valid pose data detected")

        feet_together_frames = []
        for frame in valid_frames:
            lm = frame['landmarks']
            bos_width = calculate_base_of_support_width(lm)
            if bos_width < 0.15:
                feet_together_frames.append(frame)

        if not feet_together_frames:
            return {
                'score': 1,
                'confidence': 0.6,
                'reasoning': "Feet not sufficiently together",
                'criteria_met': {'feet_together': False}
            }

        stability = StabilityAnalyzer(feet_together_frames, self.fps)
        sway = stability.calculate_sway_metrics()
        balance_events = stability.detect_loss_of_balance()
        duration_sec = len(feet_together_frames) / self.fps

        ml_sway = sway['ml_range']
        ap_sway = sway['ap_range']
        max_excursion = sway['max_excursion']

        ml_stable = ml_sway < 0.03
        ml_slightly_unstable = 0.03 <= ml_sway < 0.06
        ml_unstable = 0.06 <= ml_sway < 0.10
        ml_very_unstable = ml_sway >= 0.10

        ap_stable = ap_sway < 0.03
        ap_slightly_unstable = 0.03 <= ap_sway < 0.06
        ap_unstable = 0.06 <= ap_sway < 0.10
        ap_very_unstable = ap_sway >= 0.10

        is_stable = ml_stable and ap_stable and max_excursion < 0.05
        is_slightly_unstable = (ml_slightly_unstable or ap_slightly_unstable) and not (ml_unstable or ap_unstable or ml_very_unstable or ap_very_unstable)
        is_unstable = (ml_unstable or ap_unstable) and not (ml_very_unstable or ap_very_unstable)
        is_very_unstable = ml_very_unstable or ap_very_unstable or len(balance_events) > 3

        sway_description = []
        if ml_sway >= 0.03:
            sway_description.append(f"ML sway {ml_sway*100:.1f}cm")
        if ap_sway >= 0.03:
            sway_description.append(f"AP sway {ap_sway*100:.1f}cm")
        sway_text = ", ".join(sway_description) if sway_description else "stable"

        if duration_sec >= 60:
            if is_stable:
                score = 4
                reasoning = f"Stands with feet together safely for {duration_sec:.0f} seconds"
            elif is_slightly_unstable:
                score = 3
                reasoning = f"Stands with feet together {duration_sec:.0f}s (slightly unstable: {sway_text})"
            elif is_unstable:
                score = 3
                reasoning = f"Stands with feet together {duration_sec:.0f}s (unstable: {sway_text})"
            else:
                score = 2
                reasoning = f"Stands with feet together {duration_sec:.0f}s (very unstable: {sway_text})"
        elif duration_sec >= 30:
            if is_stable or is_slightly_unstable:
                score = 2
                reasoning = f"Holds feet together for {duration_sec:.0f} seconds ({sway_text})"
            else:
                score = 1
                reasoning = f"Holds feet together for {duration_sec:.0f} seconds (unstable: {sway_text})"
        elif duration_sec >= 15:
            score = 1
            reasoning = f"Holds feet together for {duration_sec:.0f} seconds (needs help, {sway_text})"
        else:
            score = 0
            reasoning = f"Unable to hold feet together for 15 seconds ({duration_sec:.1f}s)"

        return {
            'score': score,
            'confidence': 0.8,
            'reasoning': reasoning,
            'criteria_met': {
                'feet_together': True,
                'duration_1min': duration_sec >= 60,
                'duration_30sec': duration_sec >= 30,
                'duration_15sec': duration_sec >= 15,
                'stable': is_stable,
                'slightly_unstable': is_slightly_unstable,
                'unstable': is_unstable,
                'very_unstable': is_very_unstable,
                'lateral_sway_cm': round(ml_sway * 100, 1),
                'ap_sway_cm': round(ap_sway * 100, 1),
                'max_excursion_cm': round(max_excursion * 100, 1),
                'balance_loss_events': len(balance_events)
            }
        }

    def _score_reaching_forward(self, front_data: list, side_data: list) -> dict:
        """
        Test 8: Reaching Forward with Outstretched Arm
        4 = reaches forward confidently >25cm (10 inches)
        3 = reaches forward >12.5cm (5 inches)
        2 = reaches forward >5cm (2 inches)
        1 = reaches forward but needs supervision
        0 = loses balance while trying / requires external support
        """
        valid_frames = self._get_valid_frames(side_data if side_data else front_data)
        if not valid_frames:
            return self._no_pose_result("No valid pose data detected")

        max_reach = 0.0
        initial_wrist_x = None

        for frame in valid_frames:
            lm = frame['landmarks']
            wrist_x = lm['right_wrist']['x']

            if initial_wrist_x is None:
                initial_wrist_x = wrist_x

            reach = abs(wrist_x - initial_wrist_x)
            max_reach = max(max_reach, reach)

        shoulder_width = 0.0
        if valid_frames:
            lm = valid_frames[0]['landmarks']
            shoulder_width = abs(lm['left_shoulder']['x'] - lm['right_shoulder']['x'])

        scale_factor = 40.0 / shoulder_width if shoulder_width > 0 else 100.0
        reach_cm = max_reach * scale_factor

        stability = StabilityAnalyzer(valid_frames, self.fps)
        balance_events = stability.detect_loss_of_balance()

        if balance_events:
            score, reasoning = 0, "Lost balance while reaching"
        elif reach_cm >= 25:
            score, reasoning = 4, f"Reaches forward confidently {reach_cm:.1f}cm"
        elif reach_cm >= 12.5:
            score, reasoning = 3, f"Reaches forward {reach_cm:.1f}cm"
        elif reach_cm >= 5:
            score, reasoning = 2, f"Reaches forward {reach_cm:.1f}cm"
        else:
            score, reasoning = 1, "Reaches forward but limited range"

        return {
            'score': score,
            'confidence': 0.7,
            'reasoning': reasoning,
            'criteria_met': {
                'reach_25cm': reach_cm >= 25,
                'reach_12cm': reach_cm >= 12.5,
                'reach_5cm': reach_cm >= 5,
                'balance_maintained': len(balance_events) == 0
            }
        }

    def _score_retrieving_object(self, front_data: list, side_data: list) -> dict:
        """
        Test 9: Retrieving Object from Floor
        4 = pick up object safely and easily
        3 = pick up object but needs supervision
        2 = unable to pick up but reaches 2-5cm from object and keeps balance
        1 = unable to pick up and needs supervision while trying
        0 = unable to try / needs assist to keep from losing balance or falling
        """
        valid_frames = self._get_valid_frames(side_data if side_data else front_data)
        if not valid_frames:
            return self._no_pose_result("No valid pose data detected")

        min_wrist_y = 1.0
        max_trunk_angle = 0.0

        for frame in valid_frames:
            lm = frame['landmarks']
            wrist_y = min(lm['left_wrist']['y'], lm['right_wrist']['y'])
            trunk_angle = calculate_trunk_angle(lm)

            min_wrist_y = min(min_wrist_y, wrist_y)
            max_trunk_angle = max(max_trunk_angle, trunk_angle)

        ankle_y = valid_frames[0]['landmarks']['left_ankle']['y'] if valid_frames else 1.0
        reached_floor = min_wrist_y >= ankle_y - 0.1

        stability = StabilityAnalyzer(valid_frames, self.fps)
        balance_events = stability.detect_loss_of_balance()

        if len(balance_events) > 2:
            score, reasoning = 0, "Unable to maintain balance while attempting"
        elif reached_floor and len(balance_events) == 0:
            score, reasoning = 4, "Picks up object safely and easily"
        elif reached_floor:
            score, reasoning = 3, "Picks up object but needs supervision"
        elif max_trunk_angle > 45:
            score, reasoning = 2, "Unable to pick up but reaches close and keeps balance"
        else:
            score, reasoning = 1, "Unable to pick up, needs supervision"

        return {
            'score': score,
            'confidence': 0.7,
            'reasoning': reasoning,
            'criteria_met': {
                'reached_floor': reached_floor,
                'balance_maintained': len(balance_events) == 0,
                'significant_bend': max_trunk_angle > 45
            }
        }

    def _score_turning_look_behind(self, front_data: list, side_data: list) -> dict:
        """
        Test 10: Turning to Look Behind (Left and Right)
        4 = looks behind from both sides with good weight shift
        3 = looks behind one side only, other side shows less weight shift
        2 = turns sideways only but maintains balance
        1 = needs supervision when turning
        0 = needs assist to keep from losing balance or falling
        """
        valid_frames = self._get_valid_frames(front_data)
        if not valid_frames:
            return self._no_pose_result("No valid pose data detected")

        max_rotation_left = 0.0
        max_rotation_right = 0.0

        for frame in valid_frames:
            lm = frame['landmarks']
            rotation = calculate_spine_rotation(lm)

            nose_x = lm['nose']['x']
            mid_shoulder_x = (lm['left_shoulder']['x'] + lm['right_shoulder']['x']) / 2

            if nose_x < mid_shoulder_x:
                max_rotation_left = max(max_rotation_left, rotation)
            else:
                max_rotation_right = max(max_rotation_right, rotation)

        stability = StabilityAnalyzer(valid_frames, self.fps)
        balance_events = stability.detect_loss_of_balance()

        good_rotation = 30
        both_sides_good = max_rotation_left > good_rotation and max_rotation_right > good_rotation
        one_side_good = max_rotation_left > good_rotation or max_rotation_right > good_rotation

        if len(balance_events) > 2:
            score, reasoning = 0, "Unable to maintain balance while turning"
        elif both_sides_good and len(balance_events) == 0:
            score, reasoning = 4, "Looks behind from both sides with good weight shift"
        elif one_side_good:
            score, reasoning = 3, "Looks behind one side only with good rotation"
        elif max(max_rotation_left, max_rotation_right) > 15:
            score, reasoning = 2, "Turns sideways only but maintains balance"
        else:
            score, reasoning = 1, "Needs supervision when turning"

        return {
            'score': score,
            'confidence': 0.7,
            'reasoning': reasoning,
            'criteria_met': {
                'both_sides': both_sides_good,
                'one_side': one_side_good,
                'balance_maintained': len(balance_events) <= 1
            }
        }

    def _score_turning_360(self, front_data: list, side_data: list) -> dict:
        """
        Test 11: Turning 360 Degrees
        4 = turn 360 safely in 4 seconds or less
        3 = turn 360 safely one side only in 4 seconds or less
        2 = turn 360 safely but slowly
        1 = needs close supervision or verbal cuing
        0 = needs assistance while turning
        """
        valid_frames = self._get_valid_frames(front_data)
        if not valid_frames:
            return self._no_pose_result("No valid pose data detected")

        duration_sec = len(valid_frames) / self.fps

        stability = StabilityAnalyzer(valid_frames, self.fps)
        step_count = stability.count_steps()
        balance_events = stability.detect_loss_of_balance()

        if len(balance_events) > 3:
            score, reasoning = 0, "Needs assistance while turning"
        elif duration_sec <= 4 and len(balance_events) == 0:
            score, reasoning = 4, f"Turns 360 safely in {duration_sec:.1f} seconds"
        elif duration_sec <= 4:
            score, reasoning = 3, f"Turns 360 in {duration_sec:.1f} seconds with minor instability"
        elif len(balance_events) <= 1:
            score, reasoning = 2, f"Turns 360 safely but slowly ({duration_sec:.1f}s)"
        else:
            score, reasoning = 1, "Needs supervision while turning"

        return {
            'score': score,
            'confidence': 0.7,
            'reasoning': reasoning,
            'criteria_met': {
                'time_4sec': duration_sec <= 4,
                'balance_maintained': len(balance_events) <= 1,
                'steps_counted': step_count
            }
        }

    def _score_alternate_foot_stool(self, front_data: list, side_data: list) -> dict:
        """
        Test 12: Placing Alternate Foot on Stool (8 times in 20 seconds)
        4 = stand independently, complete 8 steps in 20 seconds
        3 = stand independently, complete 8 steps in >20 seconds
        2 = complete 4 steps without aid with supervision
        1 = complete >2 steps with minimal assist
        0 = needs assistance to keep from falling / unable to try
        """
        valid_frames = self._get_valid_frames(front_data)
        if not valid_frames:
            return self._no_pose_result("No valid pose data detected")

        duration_sec = len(valid_frames) / self.fps

        stability = StabilityAnalyzer(valid_frames, self.fps)
        step_count = stability.count_steps()
        balance_events = stability.detect_loss_of_balance()

        if len(balance_events) > 3:
            score, reasoning = 0, "Needs assistance to prevent falling"
        elif step_count >= 8 and duration_sec <= 20:
            score, reasoning = 4, f"Completed {step_count} steps in {duration_sec:.1f} seconds"
        elif step_count >= 8:
            score, reasoning = 3, f"Completed {step_count} steps in {duration_sec:.1f} seconds"
        elif step_count >= 4:
            score, reasoning = 2, f"Completed {step_count} steps with supervision"
        elif step_count >= 2:
            score, reasoning = 1, f"Completed {step_count} steps with minimal assist"
        else:
            score, reasoning = 0, "Unable to complete steps safely"

        return {
            'score': score,
            'confidence': 0.7,
            'reasoning': reasoning,
            'criteria_met': {
                'steps_8': step_count >= 8,
                'steps_4': step_count >= 4,
                'time_20sec': duration_sec <= 20,
                'balance_maintained': len(balance_events) <= 2
            }
        }

    def _score_one_foot_front(self, front_data: list, side_data: list) -> dict:
        """
        Test 13: Standing with One Foot in Front (Tandem) - 30 seconds
        4 = place foot tandem independently and hold 30 seconds
        3 = place foot ahead of other independently and hold 30 seconds
        2 = take small step independently and hold 30 seconds
        1 = needs help to step but can hold 15 seconds
        0 = loses balance while stepping or standing
        """
        valid_frames = self._get_valid_frames(front_data)
        if not valid_frames:
            return self._no_pose_result("No valid pose data detected")

        tandem_frames = []
        for frame in valid_frames:
            lm = frame['landmarks']
            left_ankle = lm['left_ankle']
            right_ankle = lm['right_ankle']

            foot_distance = abs(left_ankle['x'] - right_ankle['x'])
            foot_offset = abs(left_ankle['y'] - right_ankle['y'])

            if foot_distance < 0.1 and foot_offset > 0.05:
                tandem_frames.append(frame)

        duration_sec = len(tandem_frames) / self.fps if tandem_frames else 0

        stability = StabilityAnalyzer(tandem_frames if tandem_frames else valid_frames, self.fps)
        balance_events = stability.detect_loss_of_balance()

        if len(balance_events) > 2:
            score, reasoning = 0, "Loses balance while stepping or standing"
        elif duration_sec >= 30 and len(tandem_frames) > 0:
            score, reasoning = 4, "Places foot tandem and holds for 30 seconds"
        elif duration_sec >= 30:
            score, reasoning = 3, "Places foot ahead and holds for 30 seconds"
        elif duration_sec >= 15:
            score, reasoning = 2, f"Holds tandem position for {duration_sec:.1f} seconds"
        elif duration_sec >= 10:
            score, reasoning = 1, "Holds position with help for 15 seconds"
        else:
            score, reasoning = 0, "Unable to maintain position"

        return {
            'score': score,
            'confidence': 0.7,
            'reasoning': reasoning,
            'criteria_met': {
                'tandem_achieved': len(tandem_frames) > 0,
                'duration_30sec': duration_sec >= 30,
                'duration_15sec': duration_sec >= 15,
                'balance_maintained': len(balance_events) <= 1
            }
        }

    def _score_standing_one_foot(self, front_data: list, side_data: list) -> dict:
        """
        Test 14: Standing on One Foot - 10 seconds
        4 = lift leg independently and hold >10 seconds
        3 = lift leg independently and hold 5-10 seconds
        2 = lift leg independently and hold >= 3 seconds
        1 = tries to lift leg, unable to hold 3 seconds but remains standing
        0 = unable to try or needs assist to prevent fall
        """
        valid_frames = self._get_valid_frames(front_data)
        if not valid_frames:
            return self._no_pose_result("No valid pose data detected")

        one_leg_frames = []
        for frame in valid_frames:
            lm = frame['landmarks']
            left_ankle_y = lm['left_ankle']['y']
            right_ankle_y = lm['right_ankle']['y']

            if abs(left_ankle_y - right_ankle_y) > 0.08:
                one_leg_frames.append(frame)

        duration_sec = len(one_leg_frames) / self.fps if one_leg_frames else 0

        stability = StabilityAnalyzer(one_leg_frames if one_leg_frames else valid_frames, self.fps)
        balance_events = stability.detect_loss_of_balance()

        if len(balance_events) > 2 and duration_sec < 3:
            score, reasoning = 0, "Unable to try or needs assist"
        elif duration_sec >= 10:
            score, reasoning = 4, f"Lifts leg and holds for {duration_sec:.1f} seconds"
        elif duration_sec >= 5:
            score, reasoning = 3, f"Lifts leg and holds for {duration_sec:.1f} seconds"
        elif duration_sec >= 3:
            score, reasoning = 2, f"Lifts leg and holds for {duration_sec:.1f} seconds"
        elif duration_sec > 0:
            score, reasoning = 1, "Tries to lift leg but unable to hold 3 seconds"
        else:
            score, reasoning = 0, "Unable to lift leg"

        return {
            'score': score,
            'confidence': 0.75,
            'reasoning': reasoning,
            'criteria_met': {
                'duration_10sec': duration_sec >= 10,
                'duration_5sec': duration_sec >= 5,
                'duration_3sec': duration_sec >= 3,
                'leg_lifted': duration_sec > 0,
                'balance_maintained': len(balance_events) <= 1
            }
        }

    def _detect_hand_support(self, frames: list[dict]) -> bool:
        """Detect if hands are used for support (wrist below hip level)."""
        for frame in frames:
            lm = frame['landmarks']
            hip_y = (lm['left_hip']['y'] + lm['right_hip']['y']) / 2
            left_wrist_y = lm['left_wrist']['y']
            right_wrist_y = lm['right_wrist']['y']

            if left_wrist_y > hip_y + 0.1 or right_wrist_y > hip_y + 0.1:
                return True
        return False

    def _analyze_descent_control(self, frames: list[dict]) -> bool:
        """Analyze if descent from standing to sitting is controlled."""
        if len(frames) < 5:
            return True

        hip_velocities = []
        for i in range(1, len(frames)):
            prev_hip_y = (frames[i-1]['landmarks']['left_hip']['y'] +
                         frames[i-1]['landmarks']['right_hip']['y']) / 2
            curr_hip_y = (frames[i]['landmarks']['left_hip']['y'] +
                         frames[i]['landmarks']['right_hip']['y']) / 2
            velocity = abs(curr_hip_y - prev_hip_y) * self.fps
            hip_velocities.append(velocity)

        max_velocity = max(hip_velocities) if hip_velocities else 0
        return max_velocity < 0.5

    def _no_pose_result(self, message: str) -> dict:
        """Return result when no pose data is available."""
        return {
            'score': 0,
            'confidence': 0.0,
            'reasoning': message,
            'criteria_met': {}
        }
