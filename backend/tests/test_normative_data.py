"""Tests for normative_data module."""
import pytest
from unittest.mock import patch
from datetime import date
from app.services.normative_data import (
    calculate_age,
    get_normative_range,
    get_speed_assessment,
)


class TestCalculateAge:
    @patch('app.services.normative_data.date')
    def test_birthday_passed(self, mock_date):
        mock_date.today.return_value = date(2025, 6, 15)
        mock_date.fromisoformat = date.fromisoformat
        assert calculate_age("1990-01-15") == 35

    @patch('app.services.normative_data.date')
    def test_birthday_not_passed(self, mock_date):
        mock_date.today.return_value = date(2025, 6, 15)
        mock_date.fromisoformat = date.fromisoformat
        assert calculate_age("1990-12-20") == 34

    def test_invalid_date_returns_zero(self):
        assert calculate_age("invalid") == 0
        assert calculate_age("") == 0

    def test_none_returns_zero(self):
        assert calculate_age(None) == 0


class TestGetNormativeRange:
    def test_male_20s(self):
        result = get_normative_range(25, "M")
        assert result is not None
        assert result["mean"] == 1.36
        assert result["sd"] == 0.17
        assert result["gender"] == "남성"

    def test_female_70s(self):
        result = get_normative_range(75, "F")
        assert result is not None
        assert result["mean"] == 1.13
        assert result["sd"] == 0.18
        assert result["gender"] == "여성"

    def test_korean_gender_male(self):
        assert get_normative_range(25, "남") is not None
        assert get_normative_range(25, "남성") is not None

    def test_korean_gender_female(self):
        assert get_normative_range(25, "여") is not None

    def test_age_too_young(self):
        assert get_normative_range(10, "M") is None

    def test_age_too_old(self):
        assert get_normative_range(100, "M") is None

    def test_all_age_groups_covered(self):
        for age in [25, 35, 45, 55, 65, 75, 85]:
            assert get_normative_range(age, "M") is not None
            assert get_normative_range(age, "F") is not None


class TestGetSpeedAssessment:
    def test_community_ambulation_met(self):
        result = get_speed_assessment(1.2, 50, "M")
        cats = {i["category"]: i for i in result["clinical_interpretation"]}
        assert cats["community_ambulation"]["met"] is True

    def test_community_ambulation_not_met(self):
        result = get_speed_assessment(0.9, 50, "M")
        cats = {i["category"]: i for i in result["clinical_interpretation"]}
        assert cats["community_ambulation"]["met"] is False

    def test_fall_risk_flagged(self):
        result = get_speed_assessment(0.7, 50, "M")
        cats = {i["category"]: i for i in result["clinical_interpretation"]}
        assert "fall_risk" in cats
        assert cats["fall_risk"]["met"] is True

    def test_no_fall_risk_above_cutoff(self):
        result = get_speed_assessment(0.9, 50, "M")
        cats = {i["category"]: i for i in result["clinical_interpretation"]}
        assert "fall_risk" not in cats

    def test_household_only(self):
        result = get_speed_assessment(0.3, 50, "M")
        cats = {i["category"]: i for i in result["clinical_interpretation"]}
        assert "household_only" in cats

    def test_z_score_present(self):
        result = get_speed_assessment(1.2, 50, "M")
        assert "z_score" in result
        assert "percent_of_normal" in result

    def test_normal_comparison(self):
        result = get_speed_assessment(1.3, 50, "M")
        assert result["comparison"] == "normal"

    def test_significantly_below(self):
        result = get_speed_assessment(0.5, 50, "M")
        assert result["comparison"] == "significantly_below"

    def test_no_normative_for_out_of_range_age(self):
        result = get_speed_assessment(1.2, 10, "M")
        assert result["normative"] is None
        assert "z_score" not in result
