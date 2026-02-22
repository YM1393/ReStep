"""
MediaPipe → BBS2 Landmark Converter

Converts MediaPipe 33-landmark indexed array format to
BBS2 named-dict format for use with BBS2 scoring engine.

MediaPipe Pose provides 33 landmarks indexed 0-32.
BBS2 expects named dicts like {'left_shoulder': {'x','y','z','visibility'}, ...}
"""

# MediaPipe landmark index → BBS2 named key
MEDIAPIPE_TO_NAMED = {
    'nose': 0,
    'left_eye_inner': 1,
    'left_eye': 2,
    'left_eye_outer': 3,
    'right_eye_inner': 4,
    'right_eye': 5,
    'right_eye_outer': 6,
    'left_ear': 7,
    'right_ear': 8,
    'mouth_left': 9,
    'mouth_right': 10,
    'left_shoulder': 11,
    'right_shoulder': 12,
    'left_elbow': 13,
    'right_elbow': 14,
    'left_wrist': 15,
    'right_wrist': 16,
    'left_pinky': 17,
    'right_pinky': 18,
    'left_index': 19,
    'right_index': 20,
    'left_thumb': 21,
    'right_thumb': 22,
    'left_hip': 23,
    'right_hip': 24,
    'left_knee': 25,
    'right_knee': 26,
    'left_ankle': 27,
    'right_ankle': 28,
    'left_heel': 29,
    'right_heel': 30,
    'left_foot_index': 31,
    'right_foot_index': 32,
}


def mediapipe_to_named_landmarks(mp_landmarks) -> dict:
    """
    Convert MediaPipe pose landmarks to BBS2 named-dict format.

    Args:
        mp_landmarks: MediaPipe pose_landmarks object
                      (has .landmark attribute with indexed NormalizedLandmark objects)

    Returns:
        dict mapping name → {'x': float, 'y': float, 'z': float, 'visibility': float}
        Coordinates are normalized (0-1) as provided by MediaPipe.
    """
    named = {}
    for name, idx in MEDIAPIPE_TO_NAMED.items():
        if idx < len(mp_landmarks.landmark):
            lm = mp_landmarks.landmark[idx]
            named[name] = {
                'x': lm.x,
                'y': lm.y,
                'z': lm.z,
                'visibility': lm.visibility,
            }
    return named


def build_bbs2_frame(mp_landmarks, frame_number: int, timestamp_ms: float) -> dict:
    """
    Build a BBS2-compatible frame dict from MediaPipe landmarks.

    Args:
        mp_landmarks: MediaPipe pose_landmarks object
        frame_number: Frame index in the video
        timestamp_ms: Timestamp in milliseconds

    Returns:
        dict compatible with BBS2's StabilityAnalyzer, BBSScoringService, etc.
        {
            'frame_number': int,
            'timestamp_ms': float,
            'has_pose': True,
            'landmarks': {name: {'x','y','z','visibility'}, ...}
        }
    """
    if mp_landmarks is None:
        return {
            'frame_number': frame_number,
            'timestamp_ms': timestamp_ms,
            'has_pose': False,
            'landmarks': None,
        }

    return {
        'frame_number': frame_number,
        'timestamp_ms': timestamp_ms,
        'has_pose': True,
        'landmarks': mediapipe_to_named_landmarks(mp_landmarks),
    }
