"""
추세 분석 및 예측 모듈

환자의 검사 히스토리를 기반으로 선형 회귀 분석,
추세 방향, 미래 예측, 목표 도달 예상일을 계산합니다.
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import numpy as np


def analyze_trends(
    tests: List[dict],
    test_type: str,
    goal: Optional[dict] = None,
) -> dict:
    """검사 데이터 추세 분석

    Args:
        tests: 검사 목록 (test_date 내림차순, newest first)
        test_type: 검사 유형 (10MWT, TUG, BBS)
        goal: 활성 목표 (optional)

    Returns:
        {
            sufficient_data: bool,
            trend_direction, slope_per_week, r_squared,
            predictions: [{date, value, lower, upper}],
            goal_eta, data_points, ...
        }
    """
    if len(tests) < 3:
        return {
            "sufficient_data": False,
            "message": "추세 분석에는 최소 3회의 검사 데이터가 필요합니다.",
            "data_points": len(tests),
        }

    # Date sort ascending (oldest first)
    sorted_tests = sorted(tests, key=lambda t: t["test_date"])

    # Extract values based on test type
    dates = []
    values = []
    for t in sorted_tests:
        try:
            dt = _parse_date(t["test_date"])
            dates.append(dt)
        except (ValueError, TypeError):
            continue

        if test_type == "BBS":
            # BBS: walk_time_seconds stores total_score
            values.append(float(t.get("walk_time_seconds", 0)))
        elif test_type == "TUG":
            values.append(float(t.get("walk_time_seconds", 0)))
        else:
            # 10MWT: use time (seconds)
            values.append(float(t.get("walk_time_seconds", 0)))

    if len(dates) < 3 or len(values) < 3:
        return {
            "sufficient_data": False,
            "message": "유효한 데이터가 3개 미만입니다.",
            "data_points": len(values),
        }

    # Convert dates to weeks from first measurement
    base_date = dates[0]
    weeks = np.array([(d - base_date).total_seconds() / (7 * 86400) for d in dates])
    vals = np.array(values)

    # Linear regression
    coeffs = np.polyfit(weeks, vals, 1)
    slope = float(coeffs[0])  # change per week
    intercept = float(coeffs[1])

    # R-squared
    predicted = np.polyval(coeffs, weeks)
    ss_res = np.sum((vals - predicted) ** 2)
    ss_tot = np.sum((vals - np.mean(vals)) ** 2)
    r_squared = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Standard error
    n = len(vals)
    if n > 2:
        std_error = float(np.sqrt(ss_res / (n - 2)))
    else:
        std_error = 0.0

    # Determine trend direction
    trend_direction = _determine_trend(slope, std_error, test_type)

    # Predictions at 1, 3, 6 months from latest
    latest_date = dates[-1]
    latest_week = weeks[-1]
    predictions = []
    for months, label in [(1, "1개월"), (3, "3개월"), (6, "6개월")]:
        future_date = latest_date + timedelta(days=months * 30)
        future_week = latest_week + (months * 30 / 7)
        pred_value = slope * future_week + intercept
        margin = 1.96 * std_error
        predictions.append({
            "label": label,
            "date": future_date.strftime("%Y-%m-%d"),
            "value": round(pred_value, 3),
            "lower": round(pred_value - margin, 3),
            "upper": round(pred_value + margin, 3),
        })

    # Data points for chart
    data_points = []
    for i, (d, v) in enumerate(zip(dates, values)):
        data_points.append({
            "date": d.strftime("%Y-%m-%d"),
            "value": round(v, 3),
            "trend_value": round(float(predicted[i]), 3),
        })

    # Goal ETA calculation
    goal_eta = None
    goal_info = None
    if goal:
        goal_eta, goal_info = _calculate_goal_eta(
            slope, intercept, latest_week, latest_date, test_type, goal
        )

    result = {
        "sufficient_data": True,
        "test_type": test_type,
        "trend_direction": trend_direction,
        "slope_per_week": round(slope, 4),
        "r_squared": round(r_squared, 3),
        "std_error": round(std_error, 4),
        "data_points": data_points,
        "predictions": predictions,
        "latest_value": round(float(vals[-1]), 3),
        "latest_date": latest_date.strftime("%Y-%m-%d"),
        "total_measurements": n,
    }

    if goal_eta:
        result["goal_eta"] = goal_eta
    if goal_info:
        result["goal_info"] = goal_info

    # Value label based on test type
    if test_type == "BBS":
        result["value_label"] = "BBS 총점"
        result["value_unit"] = "점"
    elif test_type == "TUG":
        result["value_label"] = "TUG 시간"
        result["value_unit"] = "초"
    else:
        result["value_label"] = "보행 시간"
        result["value_unit"] = "초"

    return result


def _parse_date(date_str: str) -> datetime:
    """Parse various date formats"""
    for fmt in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}")


def _determine_trend(slope: float, std_error: float, test_type: str) -> str:
    """추세 방향 결정

    For 10MWT time: negative slope = improving (shorter time)
    For TUG time: negative slope = improving
    For BBS score: positive slope = improving
    """
    # If slope magnitude is less than std_error, consider stable
    if abs(slope) < std_error * 0.5:
        return "stable"

    if test_type in ("TUG", "10MWT"):
        # Lower time = better
        if slope < -std_error * 0.3:
            return "improving"
        elif slope > std_error * 0.3:
            return "declining"
        return "stable"
    else:
        # Higher score = better (BBS score)
        if slope > std_error * 0.3:
            return "improving"
        elif slope < -std_error * 0.3:
            return "declining"
        return "stable"


def _calculate_goal_eta(
    slope: float,
    intercept: float,
    latest_week: float,
    latest_date: datetime,
    test_type: str,
    goal: dict,
) -> tuple:
    """목표 도달 예상일 계산"""
    # Determine target value
    target = None
    if test_type == "BBS":
        target = goal.get("target_score")
    elif test_type == "TUG":
        target = goal.get("target_time_seconds")
    else:
        # 10MWT: time-based target
        target = goal.get("target_time_seconds")
        if target is None and goal.get("target_speed_mps"):
            # Backward compat: convert speed target to time target
            target = round(10.0 / goal["target_speed_mps"], 1) if goal["target_speed_mps"] > 0 else None

    if target is None or slope == 0:
        return None, None

    target = float(target)

    # For TUG/10MWT time: need slope < 0 to reduce time
    # For BBS: need slope > 0 to increase score
    current_value = slope * latest_week + intercept

    if test_type in ("TUG", "10MWT"):
        if slope >= 0 and current_value > target:
            return None, {"message": "현재 추세로는 목표 도달이 어렵습니다."}
    else:
        if slope <= 0 and current_value < target:
            return None, {"message": "현재 추세로는 목표 도달이 어렵습니다."}

    # Solve: slope * week + intercept = target
    target_week = (target - intercept) / slope

    if target_week <= latest_week:
        # Already reached or passed
        return None, {"message": "이미 목표에 도달했거나 도달한 것으로 추정됩니다."}

    weeks_remaining = target_week - latest_week
    eta_date = latest_date + timedelta(weeks=weeks_remaining)

    goal_info = {
        "target_value": target,
        "weeks_remaining": round(weeks_remaining, 1),
    }

    return eta_date.strftime("%Y-%m-%d"), goal_info
