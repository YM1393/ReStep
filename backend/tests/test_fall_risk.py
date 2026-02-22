"""Tests for fall_risk module - must match frontend fallRisk.ts thresholds exactly."""
import pytest
from app.services.fall_risk import (
    calculate_speed_score,
    calculate_time_score,
    calculate_fall_risk_score,
    get_risk_level,
    get_fall_risk_assessment,
)


class TestCalculateSpeedScore:
    def test_normal_speed(self):
        assert calculate_speed_score(1.2) == 50
        assert calculate_speed_score(1.5) == 50

    def test_mild_speed(self):
        assert calculate_speed_score(1.0) == 40
        assert calculate_speed_score(1.19) == 40

    def test_caution_speed(self):
        assert calculate_speed_score(0.8) == 25
        assert calculate_speed_score(0.99) == 25

    def test_danger_speed(self):
        assert calculate_speed_score(0.79) == 10
        assert calculate_speed_score(0.0) == 10

    def test_negative_speed(self):
        assert calculate_speed_score(-1.0) == 10


class TestCalculateTimeScore:
    def test_normal_time(self):
        assert calculate_time_score(8.3) == 50
        assert calculate_time_score(5.0) == 50

    def test_mild_time(self):
        assert calculate_time_score(8.31) == 40
        assert calculate_time_score(10.0) == 40

    def test_caution_time(self):
        assert calculate_time_score(10.01) == 25
        assert calculate_time_score(12.5) == 25

    def test_danger_time(self):
        assert calculate_time_score(12.51) == 10
        assert calculate_time_score(20.0) == 10


class TestCalculateFallRiskScore:
    def test_perfect_score(self):
        assert calculate_fall_risk_score(1.2, 8.3) == 100

    def test_worst_score(self):
        assert calculate_fall_risk_score(0.5, 15.0) == 20

    def test_mixed_score(self):
        assert calculate_fall_risk_score(1.0, 11.0) == 65


class TestGetRiskLevel:
    def test_normal(self):
        result = get_risk_level(90)
        assert result["level"] == "normal"
        assert result["label_en"] == "Normal"

    def test_mild(self):
        result = get_risk_level(70)
        assert result["level"] == "mild"

    def test_moderate(self):
        result = get_risk_level(50)
        assert result["level"] == "moderate"

    def test_high(self):
        result = get_risk_level(49)
        assert result["level"] == "high"

    def test_boundary_89(self):
        assert get_risk_level(89)["level"] == "mild"

    def test_boundary_69(self):
        assert get_risk_level(69)["level"] == "moderate"


class TestGetFallRiskAssessment:
    def test_complete_assessment(self):
        result = get_fall_risk_assessment(1.2, 8.0)
        assert result["score"] == 100
        assert result["speed_score"] == 50
        assert result["time_score"] == 50
        assert result["level"] == "normal"

    def test_high_risk_assessment(self):
        result = get_fall_risk_assessment(0.5, 15.0)
        assert result["score"] == 20
        assert result["level"] == "high"


class TestFrontendBackendParity:
    """Ensure Python thresholds match TypeScript thresholds exactly."""

    @pytest.mark.parametrize("speed,expected", [
        (0.79, 10), (0.8, 25), (0.99, 25), (1.0, 40), (1.19, 40), (1.2, 50),
    ])
    def test_speed_score_parity(self, speed, expected):
        assert calculate_speed_score(speed) == expected

    @pytest.mark.parametrize("time,expected", [
        (8.3, 50), (8.31, 40), (10.0, 40), (10.01, 25), (12.5, 25), (12.51, 10),
    ])
    def test_time_score_parity(self, time, expected):
        assert calculate_time_score(time) == expected
