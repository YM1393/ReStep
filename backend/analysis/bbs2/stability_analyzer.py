import numpy as np
from scipy import stats
from typing import Optional
from .angle_calculator import get_center_of_mass


class StabilityAnalyzer:
    def __init__(self, frames_data: list[dict], fps: float = 30.0):
        self.frames_data = [f for f in frames_data if f.get('has_pose') and f.get('landmarks')]
        self.fps = fps

    def calculate_com_trajectory(self) -> np.ndarray:
        """Calculate center of mass trajectory over time."""
        if not self.frames_data:
            return np.array([])

        com_positions = []
        for frame in self.frames_data:
            lm = frame['landmarks']
            com = get_center_of_mass(lm)
            com_positions.append([com['x'], com['y']])
        return np.array(com_positions)

    def calculate_sway_metrics(self) -> dict:
        """Calculate postural sway metrics."""
        com_trajectory = self.calculate_com_trajectory()

        if len(com_trajectory) < 2:
            return {
                'max_excursion': 0.0,
                'mean_velocity': 0.0,
                'path_length': 0.0,
                'sway_area': 0.0,
                'ml_range': 0.0,
                'ap_range': 0.0
            }

        com_centered = com_trajectory - com_trajectory.mean(axis=0)

        distances = np.linalg.norm(com_centered, axis=1)
        max_excursion = float(np.max(distances))

        displacements = np.diff(com_trajectory, axis=0)
        step_distances = np.linalg.norm(displacements, axis=1)
        path_length = float(np.sum(step_distances))

        duration_seconds = len(com_trajectory) / self.fps
        mean_velocity = path_length / duration_seconds if duration_seconds > 0 else 0.0

        ml_range = float(np.max(com_centered[:, 0]) - np.min(com_centered[:, 0]))
        ap_range = float(np.max(com_centered[:, 1]) - np.min(com_centered[:, 1]))

        sway_area = self._calculate_sway_area(com_centered)

        return {
            'max_excursion': max_excursion,
            'mean_velocity': mean_velocity,
            'path_length': path_length,
            'sway_area': sway_area,
            'ml_range': ml_range,
            'ap_range': ap_range
        }

    def _calculate_sway_area(self, com_centered: np.ndarray) -> float:
        """Calculate 95% confidence ellipse area."""
        if len(com_centered) < 3:
            return 0.0

        try:
            cov = np.cov(com_centered.T)
            eigenvalues = np.linalg.eigvalsh(cov)
            chi2_val = stats.chi2.ppf(0.95, 2)
            area = np.pi * chi2_val * np.sqrt(np.prod(np.maximum(eigenvalues, 0)))
            return float(area)
        except Exception:
            return 0.0

    def detect_loss_of_balance(self, threshold: float = 0.1) -> list[dict]:
        """Detect moments where balance may have been lost."""
        com_trajectory = self.calculate_com_trajectory()

        if len(com_trajectory) < 3:
            return []

        balance_loss_events = []
        displacements = np.diff(com_trajectory, axis=0)
        velocities = np.linalg.norm(displacements, axis=1) * self.fps

        accelerations = np.diff(velocities)

        for i, acc in enumerate(accelerations):
            if abs(acc) > threshold * self.fps:
                frame_idx = i + 1
                if frame_idx < len(self.frames_data):
                    balance_loss_events.append({
                        'frame_number': self.frames_data[frame_idx]['frame_number'],
                        'timestamp_ms': self.frames_data[frame_idx]['timestamp_ms'],
                        'acceleration': float(acc)
                    })

        return balance_loss_events

    def calculate_standing_duration(self, standing_threshold: float = 0.15) -> float:
        """Calculate total duration of stable standing in seconds."""
        if not self.frames_data:
            return 0.0

        stable_frames = 0
        com_trajectory = self.calculate_com_trajectory()

        if len(com_trajectory) < 2:
            return 0.0

        mean_com = com_trajectory.mean(axis=0)

        for i, com in enumerate(com_trajectory):
            distance_from_mean = np.linalg.norm(com - mean_com)
            if distance_from_mean < standing_threshold:
                stable_frames += 1

        return stable_frames / self.fps

    def is_single_leg_stance(self, frame_landmarks: dict, threshold: float = 0.05) -> bool:
        """Check if the person is in single leg stance."""
        left_ankle_y = frame_landmarks['left_ankle']['y']
        right_ankle_y = frame_landmarks['right_ankle']['y']

        return abs(left_ankle_y - right_ankle_y) > threshold

    def count_steps(self) -> int:
        """Count number of steps taken (for walking/turning tests)."""
        if len(self.frames_data) < 2:
            return 0

        steps = 0
        prev_left_higher = None

        for frame in self.frames_data:
            lm = frame['landmarks']
            left_ankle_y = lm['left_ankle']['y']
            right_ankle_y = lm['right_ankle']['y']

            left_higher = left_ankle_y < right_ankle_y

            if prev_left_higher is not None and left_higher != prev_left_higher:
                steps += 1

            prev_left_higher = left_higher

        return steps // 2
