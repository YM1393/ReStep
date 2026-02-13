"""
낙상 위험도 점수 계산 모듈

점수 계산 기준:
- 보행 속도와 시간을 각각 50점씩 배점
- 총점 0-100점으로 종합 위험도 산출
"""

def calculate_speed_score(speed_mps: float) -> int:
    """보행 속도 기반 점수 (0-50점)"""
    if speed_mps >= 1.2:
        return 50  # 정상
    elif speed_mps >= 1.0:
        return 40  # 경도
    elif speed_mps >= 0.8:
        return 25  # 주의
    else:
        return 10  # 위험


def calculate_time_score(time_seconds: float) -> int:
    """보행 시간 기반 점수 (0-50점)"""
    if time_seconds <= 8.3:
        return 50  # 정상
    elif time_seconds <= 10.0:
        return 40  # 경도
    elif time_seconds <= 12.5:
        return 25  # 주의
    else:
        return 10  # 위험


def calculate_fall_risk_score(speed_mps: float, time_seconds: float) -> int:
    """종합 낙상 위험 점수 계산 (0-100점)"""
    speed_score = calculate_speed_score(speed_mps)
    time_score = calculate_time_score(time_seconds)
    return speed_score + time_score


def get_risk_level(score: int) -> dict:
    """점수에 따른 위험도 등급 반환"""
    if score >= 90:
        return {
            "level": "normal",
            "label": "정상",
            "label_en": "Normal",
            "color": "green",
            "description": "낙상 위험이 낮습니다."
        }
    elif score >= 70:
        return {
            "level": "mild",
            "label": "경도 위험",
            "label_en": "Mild Risk",
            "color": "blue",
            "description": "경미한 낙상 위험이 있습니다. 주의가 필요합니다."
        }
    elif score >= 50:
        return {
            "level": "moderate",
            "label": "중등도 위험",
            "label_en": "Moderate Risk",
            "color": "orange",
            "description": "낙상 위험이 있습니다. 예방 조치가 필요합니다."
        }
    else:
        return {
            "level": "high",
            "label": "고위험",
            "label_en": "High Risk",
            "color": "red",
            "description": "낙상 위험이 높습니다. 즉각적인 개입이 필요합니다."
        }


def get_fall_risk_assessment(speed_mps: float, time_seconds: float) -> dict:
    """종합 낙상 위험 평가 결과 반환"""
    score = calculate_fall_risk_score(speed_mps, time_seconds)
    risk_level = get_risk_level(score)

    return {
        "score": score,
        "speed_score": calculate_speed_score(speed_mps),
        "time_score": calculate_time_score(time_seconds),
        **risk_level
    }
