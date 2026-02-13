"""
연령/성별 기준 10MWT 정상 보행 속도 및 임상 변수 데이터

참고문헌:
- Bohannon RW (2011) Comfortable and maximum walking speed of adults aged 20-79 years.
- Bohannon RW, Andrews AW (2011) Normal walking speed: a descriptive meta-analysis.
- Hollman JH et al. (2011) Normative spatiotemporal gait parameters in older adults.
  Gait Posture, 34(1):111-118.
- Oberg T et al. (1993) Basic gait parameters: reference data for normal subjects.
  J Rehabil Res Dev, 30(2):210-223.
"""

from typing import Dict, Optional, Tuple
from datetime import date


# 연령/성별 기준 정상 보행 속도 (m/s)
# Bohannon 2011 meta-analysis 기반
NORMATIVE_SPEED = {
    # (min_age, max_age): {"M": (mean, sd), "F": (mean, sd)}
    (20, 29): {"M": (1.36, 0.17), "F": (1.34, 0.17)},
    (30, 39): {"M": (1.43, 0.17), "F": (1.34, 0.17)},
    (40, 49): {"M": (1.43, 0.17), "F": (1.39, 0.18)},
    (50, 59): {"M": (1.31, 0.17), "F": (1.31, 0.17)},
    (60, 69): {"M": (1.24, 0.17), "F": (1.24, 0.17)},
    (70, 79): {"M": (1.13, 0.20), "F": (1.13, 0.18)},
    (80, 99): {"M": (0.94, 0.20), "F": (0.94, 0.18)},
}

# ============================================================
# 임상 변수별 연령/성별 정상 범위
# (min_age, max_age): {"M": (mean, sd), "F": (mean, sd)}
# ============================================================

# 보폭 (m) - Hollman 2011, Oberg 1993
NORMATIVE_STRIDE_LENGTH = {
    (20, 29): {"M": (1.46, 0.14), "F": (1.28, 0.14)},
    (30, 39): {"M": (1.46, 0.14), "F": (1.28, 0.14)},
    (40, 49): {"M": (1.44, 0.14), "F": (1.26, 0.14)},
    (50, 59): {"M": (1.38, 0.16), "F": (1.22, 0.14)},
    (60, 69): {"M": (1.32, 0.16), "F": (1.16, 0.16)},
    (70, 79): {"M": (1.22, 0.18), "F": (1.08, 0.16)},
    (80, 99): {"M": (1.06, 0.20), "F": (0.94, 0.18)},
}

# 분당 걸음수 (steps/min) - Hollman 2011, Bohannon 1997
NORMATIVE_CADENCE = {
    (20, 29): {"M": (113, 9), "F": (117, 9)},
    (30, 39): {"M": (112, 9), "F": (116, 9)},
    (40, 49): {"M": (112, 9), "F": (116, 9)},
    (50, 59): {"M": (110, 10), "F": (114, 10)},
    (60, 69): {"M": (108, 10), "F": (112, 10)},
    (70, 79): {"M": (104, 12), "F": (108, 12)},
    (80, 99): {"M": (98, 14), "F": (102, 14)},
}

# 스텝 시간 (s) - 60/cadence에서 파생
NORMATIVE_STEP_TIME = {
    (20, 29): {"M": (0.53, 0.04), "F": (0.51, 0.04)},
    (30, 39): {"M": (0.54, 0.04), "F": (0.52, 0.04)},
    (40, 49): {"M": (0.54, 0.04), "F": (0.52, 0.04)},
    (50, 59): {"M": (0.55, 0.05), "F": (0.53, 0.05)},
    (60, 69): {"M": (0.56, 0.05), "F": (0.54, 0.05)},
    (70, 79): {"M": (0.58, 0.06), "F": (0.56, 0.06)},
    (80, 99): {"M": (0.61, 0.08), "F": (0.59, 0.08)},
}

# 이중지지기 (%) - Hollman 2011
NORMATIVE_DOUBLE_SUPPORT = {
    (20, 29): {"M": (22, 4), "F": (23, 4)},
    (30, 39): {"M": (22, 4), "F": (23, 4)},
    (40, 49): {"M": (23, 4), "F": (24, 4)},
    (50, 59): {"M": (24, 4), "F": (25, 4)},
    (60, 69): {"M": (26, 5), "F": (27, 5)},
    (70, 79): {"M": (28, 5), "F": (29, 5)},
    (80, 99): {"M": (32, 6), "F": (33, 6)},
}

# 유각기 비율 (%) - 정상 ~38-42%
NORMATIVE_SWING_PCT = {
    (20, 29): {"M": (40, 2), "F": (40, 2)},
    (30, 39): {"M": (40, 2), "F": (40, 2)},
    (40, 49): {"M": (39, 2), "F": (39, 2)},
    (50, 59): {"M": (39, 3), "F": (38, 3)},
    (60, 69): {"M": (38, 3), "F": (38, 3)},
    (70, 79): {"M": (38, 3), "F": (37, 3)},
    (80, 99): {"M": (36, 4), "F": (35, 4)},
}

# 변수명 → 테이블 매핑
NORMATIVE_CLINICAL_TABLES = {
    "stride_length": NORMATIVE_STRIDE_LENGTH,
    "cadence": NORMATIVE_CADENCE,
    "step_time": NORMATIVE_STEP_TIME,
    "double_support": NORMATIVE_DOUBLE_SUPPORT,
    "swing_pct": NORMATIVE_SWING_PCT,
}

# 변수별 한글 레이블, 단위, 높을수록 나쁜지 여부
CLINICAL_VAR_META = {
    "stride_length": {"label": "보폭", "unit": "m", "higher_is_worse": False},
    "cadence": {"label": "분당 걸음수", "unit": "steps/min", "higher_is_worse": False},
    "step_time": {"label": "스텝 시간", "unit": "s", "higher_is_worse": True},
    "double_support": {"label": "이중지지기", "unit": "%", "higher_is_worse": True},
    "swing_pct": {"label": "유각기 비율", "unit": "%", "higher_is_worse": False},
}


def get_clinical_normative(variable_name: str, age: int, gender: str) -> Optional[Dict]:
    """임상 변수의 연령/성별 정상 범위 반환"""
    table = NORMATIVE_CLINICAL_TABLES.get(variable_name)
    if not table:
        return None

    gender_key = "M" if gender.upper() in ["M", "남", "남성", "MALE"] else "F"
    for (min_age, max_age), data in table.items():
        if min_age <= age <= max_age:
            mean, sd = data[gender_key]
            return {
                "mean": mean,
                "sd": sd,
                "range_low": round(mean - sd, 2),
                "range_high": round(mean + sd, 2),
                "age_group": f"{min_age}-{max_age}세",
                "gender": "남성" if gender_key == "M" else "여성",
            }
    return None


def get_clinical_variable_assessment(variable_name: str, value: float, age: int, gender: str) -> Optional[Dict]:
    """임상 변수 값에 대한 연령/성별 기반 평가"""
    normative = get_clinical_normative(variable_name, age, gender)
    if not normative:
        return None

    meta = CLINICAL_VAR_META.get(variable_name, {})
    mean = normative["mean"]
    sd = normative["sd"]
    z_score = (value - mean) / sd if sd > 0 else 0

    # 정상 범위: |z_score| 기반 양방향 평가
    abs_z = abs(z_score)

    if abs_z <= 1.0:
        comparison = "normal"
        comparison_label = "정상 범위"
    elif abs_z <= 1.5:
        if z_score > 0:
            comparison = "above_average"
            comparison_label = "평균 이상"
        else:
            comparison = "below_average"
            comparison_label = "평균 이하"
    elif abs_z <= 2.0:
        if z_score > 0:
            comparison = "above_normal"
            comparison_label = "정상 범위 초과"
        else:
            comparison = "below_normal"
            comparison_label = "정상 범위 미달"
    else:
        if z_score > 0:
            comparison = "significantly_above"
            comparison_label = "현저히 높음"
        else:
            comparison = "significantly_below"
            comparison_label = "현저히 낮음"

    return {
        "value": round(value, 3),
        "normative": normative,
        "z_score": round(z_score, 2),
        "comparison": comparison,
        "comparison_label": comparison_label,
        "percent_of_normal": round((value / mean) * 100, 1) if mean > 0 else 0,
        "label": meta.get("label", variable_name),
        "unit": meta.get("unit", ""),
    }


# 10MWT 시간 기준 임상 해석
CLINICAL_THRESHOLDS = {
    "community_ambulation": 1.0,     # 지역사회 보행 가능 기준 (m/s)
    "fall_risk_cutoff": 0.8,          # 낙상 위험 기준 (m/s)
    "household_ambulation": 0.4,      # 실내 보행만 가능 기준 (m/s)
}


def calculate_age(birth_date_str: str) -> int:
    """생년월일에서 나이 계산"""
    try:
        birth = date.fromisoformat(birth_date_str)
        today = date.today()
        return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    except (ValueError, TypeError):
        return 0


def get_normative_range(age: int, gender: str) -> Optional[Dict]:
    """연령/성별에 해당하는 정상 보행 속도 범위 반환"""
    gender_key = "M" if gender.upper() in ["M", "남", "남성", "MALE"] else "F"

    for (min_age, max_age), data in NORMATIVE_SPEED.items():
        if min_age <= age <= max_age:
            mean, sd = data[gender_key]
            return {
                "mean": mean,
                "sd": sd,
                "range_low": round(mean - sd, 2),
                "range_high": round(mean + sd, 2),
                "age_group": f"{min_age}-{max_age}세",
                "gender": "남성" if gender_key == "M" else "여성",
                "reference": "Bohannon 2011"
            }

    return None


def get_speed_assessment(speed_mps: float, age: int, gender: str) -> Dict:
    """보행 속도에 대한 종합 평가"""
    from app.services.cache_service import cache

    # Round speed to 2 decimals for stable cache key
    cache_key = f"{cache.PREFIX_NORMATIVE}:assess:{round(speed_mps, 2)}:{age}:{gender}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    normative = get_normative_range(age, gender)

    result = {
        "speed_mps": round(speed_mps, 2),
        "normative": normative,
        "clinical_interpretation": [],
    }

    # 정상 범위 대비 평가
    if normative:
        mean = normative["mean"]
        sd = normative["sd"]
        z_score = (speed_mps - mean) / sd if sd > 0 else 0
        result["z_score"] = round(z_score, 2)

        if z_score >= -0.5:
            result["comparison"] = "normal"
            result["comparison_label"] = "정상 범위"
        elif z_score >= -1.0:
            result["comparison"] = "below_average"
            result["comparison_label"] = "평균 이하"
        elif z_score >= -2.0:
            result["comparison"] = "below_normal"
            result["comparison_label"] = "정상 범위 미달"
        else:
            result["comparison"] = "significantly_below"
            result["comparison_label"] = "현저히 낮음"

        pct_of_normal = (speed_mps / mean) * 100 if mean > 0 else 0
        result["percent_of_normal"] = round(pct_of_normal, 1)

    # 임상 해석
    if speed_mps >= CLINICAL_THRESHOLDS["community_ambulation"]:
        result["clinical_interpretation"].append({
            "category": "community_ambulation",
            "label": "지역사회 보행 가능",
            "met": True
        })
    else:
        result["clinical_interpretation"].append({
            "category": "community_ambulation",
            "label": "지역사회 보행 제한",
            "met": False
        })

    if speed_mps < CLINICAL_THRESHOLDS["fall_risk_cutoff"]:
        result["clinical_interpretation"].append({
            "category": "fall_risk",
            "label": "낙상 위험 증가",
            "met": True
        })

    if speed_mps < CLINICAL_THRESHOLDS["household_ambulation"]:
        result["clinical_interpretation"].append({
            "category": "household_only",
            "label": "실내 보행만 가능",
            "met": True
        })

    cache.set(cache_key, result, ttl=3600)
    return result


def get_time_assessment(time_seconds: float, age: int, gender: str) -> Dict:
    """보행 시간에 대한 종합 평가 (10m 기준)"""
    normative_speed = get_normative_range(age, gender)

    result = {
        "time_seconds": round(time_seconds, 2),
        "normative": None,
        "clinical_interpretation": [],
    }

    if normative_speed:
        mean_speed = normative_speed["mean"]
        sd_speed = normative_speed["sd"]
        # 속도→시간 변환: time = 10 / speed
        mean_time = round(10.0 / mean_speed, 2) if mean_speed > 0 else 0
        range_low_time = round(10.0 / (mean_speed + sd_speed), 2) if (mean_speed + sd_speed) > 0 else 0
        range_high_time = round(10.0 / max(0.01, mean_speed - sd_speed), 2)

        result["normative"] = {
            "mean": mean_time,
            "range_low": range_low_time,
            "range_high": range_high_time,
            "age_group": normative_speed["age_group"],
            "gender": normative_speed["gender"],
            "reference": "Bohannon 2011",
        }

        # z-score는 시간 기준 (시간이 길수록 나쁨, 부호 반전)
        sd_time = abs(mean_time - range_low_time) if range_low_time > 0 else 1
        z_score = (time_seconds - mean_time) / sd_time if sd_time > 0 else 0
        result["z_score"] = round(z_score, 2)

        if z_score <= 0.5:
            result["comparison"] = "normal"
            result["comparison_label"] = "정상 범위"
        elif z_score <= 1.0:
            result["comparison"] = "above_average"
            result["comparison_label"] = "평균보다 느림"
        elif z_score <= 2.0:
            result["comparison"] = "above_normal"
            result["comparison_label"] = "정상 범위 초과 (느림)"
        else:
            result["comparison"] = "significantly_above"
            result["comparison_label"] = "현저히 느림"

        pct = (mean_time / time_seconds) * 100 if time_seconds > 0 else 0
        result["percent_of_normal"] = round(pct, 1)

    # 시간 기준 임상 해석
    speed_equiv = 10.0 / time_seconds if time_seconds > 0 else 0
    if speed_equiv >= CLINICAL_THRESHOLDS["community_ambulation"]:
        result["clinical_interpretation"].append({
            "category": "community_ambulation",
            "label": "지역사회 보행 가능 (≤10.0초)",
            "met": True
        })
    else:
        result["clinical_interpretation"].append({
            "category": "community_ambulation",
            "label": "지역사회 보행 제한 (>10.0초)",
            "met": False
        })

    if speed_equiv < CLINICAL_THRESHOLDS["fall_risk_cutoff"]:
        result["clinical_interpretation"].append({
            "category": "fall_risk",
            "label": "낙상 위험 증가 (>12.5초)",
            "met": True
        })

    if speed_equiv < CLINICAL_THRESHOLDS["household_ambulation"]:
        result["clinical_interpretation"].append({
            "category": "household_only",
            "label": "실내 보행만 가능 (>25.0초)",
            "met": True
        })

    return result
