import numpy as np
from typing import Optional


def calculate_angle(point_a: dict, point_b: dict, point_c: dict) -> float:
    """
    Calculate angle at point_b between vectors BA and BC.

    Args:
        point_a, point_b, point_c: Dicts with 'x', 'y', 'z' keys

    Returns:
        Angle in degrees
    """
    a = np.array([point_a['x'], point_a['y'], point_a['z']])
    b = np.array([point_b['x'], point_b['y'], point_b['z']])
    c = np.array([point_c['x'], point_c['y'], point_c['z']])

    ba = a - b
    bc = c - b

    ba_norm = np.linalg.norm(ba)
    bc_norm = np.linalg.norm(bc)

    if ba_norm == 0 or bc_norm == 0:
        return 0.0

    cosine_angle = np.dot(ba, bc) / (ba_norm * bc_norm)
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    angle = np.degrees(np.arccos(cosine_angle))

    return float(angle)


def calculate_hip_angle(landmarks: dict, side: str = 'left') -> float:
    """Calculate hip flexion angle (shoulder-hip-knee)."""
    shoulder = landmarks[f'{side}_shoulder']
    hip = landmarks[f'{side}_hip']
    knee = landmarks[f'{side}_knee']
    return calculate_angle(shoulder, hip, knee)


def calculate_knee_angle(landmarks: dict, side: str = 'left') -> float:
    """Calculate knee flexion angle (hip-knee-ankle)."""
    hip = landmarks[f'{side}_hip']
    knee = landmarks[f'{side}_knee']
    ankle = landmarks[f'{side}_ankle']
    return calculate_angle(hip, knee, ankle)


def calculate_ankle_angle(landmarks: dict, side: str = 'left') -> float:
    """Calculate ankle angle (knee-ankle-foot)."""
    knee = landmarks[f'{side}_knee']
    ankle = landmarks[f'{side}_ankle']
    foot = landmarks[f'{side}_foot_index']
    return calculate_angle(knee, ankle, foot)


def calculate_trunk_angle(landmarks: dict) -> float:
    """Calculate trunk forward lean angle from vertical."""
    mid_shoulder = {
        'x': (landmarks['left_shoulder']['x'] + landmarks['right_shoulder']['x']) / 2,
        'y': (landmarks['left_shoulder']['y'] + landmarks['right_shoulder']['y']) / 2,
        'z': (landmarks['left_shoulder']['z'] + landmarks['right_shoulder']['z']) / 2
    }
    mid_hip = {
        'x': (landmarks['left_hip']['x'] + landmarks['right_hip']['x']) / 2,
        'y': (landmarks['left_hip']['y'] + landmarks['right_hip']['y']) / 2,
        'z': (landmarks['left_hip']['z'] + landmarks['right_hip']['z']) / 2
    }

    vertical_point = {
        'x': mid_hip['x'],
        'y': mid_hip['y'] - 1,
        'z': mid_hip['z']
    }

    return calculate_angle(mid_shoulder, mid_hip, vertical_point)


def calculate_spine_rotation(landmarks: dict) -> float:
    """Calculate spine rotation angle in horizontal plane."""
    left_shoulder = np.array([landmarks['left_shoulder']['x'], landmarks['left_shoulder']['z']])
    right_shoulder = np.array([landmarks['right_shoulder']['x'], landmarks['right_shoulder']['z']])
    left_hip = np.array([landmarks['left_hip']['x'], landmarks['left_hip']['z']])
    right_hip = np.array([landmarks['right_hip']['x'], landmarks['right_hip']['z']])

    shoulder_vector = right_shoulder - left_shoulder
    hip_vector = right_hip - left_hip

    shoulder_norm = np.linalg.norm(shoulder_vector)
    hip_norm = np.linalg.norm(hip_vector)

    if shoulder_norm == 0 or hip_norm == 0:
        return 0.0

    cosine = np.dot(shoulder_vector, hip_vector) / (shoulder_norm * hip_norm)
    cosine = np.clip(cosine, -1.0, 1.0)

    return float(np.degrees(np.arccos(cosine)))


def get_center_of_mass(landmarks: dict) -> dict:
    """Estimate center of mass position (simplified using hip midpoint)."""
    return {
        'x': (landmarks['left_hip']['x'] + landmarks['right_hip']['x']) / 2,
        'y': (landmarks['left_hip']['y'] + landmarks['right_hip']['y']) / 2,
        'z': (landmarks['left_hip']['z'] + landmarks['right_hip']['z']) / 2
    }


def calculate_base_of_support_width(landmarks: dict) -> float:
    """Calculate distance between feet (base of support width)."""
    left_ankle = np.array([
        landmarks['left_ankle']['x'],
        landmarks['left_ankle']['y'],
        landmarks['left_ankle']['z']
    ])
    right_ankle = np.array([
        landmarks['right_ankle']['x'],
        landmarks['right_ankle']['y'],
        landmarks['right_ankle']['z']
    ])
    return float(np.linalg.norm(right_ankle - left_ankle))
