"""
재활 치료 추천 시스템

낙상 위험 수준 및 질환 프로파일 기반으로
맞춤형 재활 운동/치료 프로그램을 추천합니다.
"""

from typing import List, Dict, Optional


def get_recommendations(
    patient: dict,
    latest_tests: List[dict],
    disease_profile_name: str,
    risk_score: int,
) -> List[dict]:
    """환자 상태 기반 재활 추천 목록 생성

    Args:
        patient: 환자 정보 dict
        latest_tests: 최근 검사 목록
        disease_profile_name: 질환 프로파일 이름 (e.g. "parkinsons", "stroke")
        risk_score: 낙상 위험 점수 (0-100)

    Returns:
        추천 목록 [{category, title, description, priority, frequency, rationale}, ...]
    """
    recommendations = []

    # 1. 위험 수준별 기본 추천
    recommendations.extend(_risk_based_recommendations(risk_score))

    # 2. 질환별 추가 추천
    recommendations.extend(_disease_specific_recommendations(disease_profile_name))

    # 3. 검사 데이터 기반 추가 추천
    recommendations.extend(_test_data_recommendations(latest_tests))

    # 중복 제거 (title 기준)
    seen = set()
    unique = []
    for rec in recommendations:
        if rec["title"] not in seen:
            seen.add(rec["title"])
            unique.append(rec)

    # 우선순위 정렬: high > medium > low
    priority_order = {"high": 0, "medium": 1, "low": 2}
    unique.sort(key=lambda r: priority_order.get(r["priority"], 9))

    return unique


def _risk_based_recommendations(risk_score: int) -> List[dict]:
    """낙상 위험 점수 기반 추천"""
    recs = []

    if risk_score >= 90:
        # Low risk (90-100): maintenance
        recs.append({
            "category": "운동",
            "title": "유지 운동 프로그램",
            "description": "현재 기능 수준을 유지하기 위한 규칙적인 유산소 운동 및 근력 운동을 권장합니다.",
            "priority": "low",
            "frequency": "주 3회, 30분",
            "rationale": "낙상 위험이 낮은 수준이므로 현재 기능 유지에 초점을 맞춥니다.",
        })
        recs.append({
            "category": "평가",
            "title": "6개월 후 재평가",
            "description": "현재 상태가 양호하므로 6개월 간격으로 추적 평가를 시행합니다.",
            "priority": "low",
            "frequency": "6개월마다",
            "rationale": "정상 범위 내 기능을 보이는 환자의 정기 모니터링입니다.",
        })

    elif risk_score >= 70:
        # Mild risk (70-89): balance training
        recs.append({
            "category": "균형 훈련",
            "title": "균형 훈련 프로그램",
            "description": "정적/동적 균형 훈련을 포함한 체계적인 균형 훈련을 시작합니다. "
                           "탄뎀 자세, 한 발 서기, 체중 이동 훈련 등을 포함합니다.",
            "priority": "medium",
            "frequency": "주 2회, 30-45분",
            "rationale": "경도 낙상 위험이 있어 균형 능력 향상이 필요합니다.",
        })
        recs.append({
            "category": "보행 훈련",
            "title": "보행 개선 운동",
            "description": "보행 속도, 보폭, 보행 패턴 개선을 위한 보행 훈련을 시행합니다. "
                           "트레드밀 보행, 장애물 보행 등을 포함합니다.",
            "priority": "medium",
            "frequency": "주 2회, 20-30분",
            "rationale": "보행 속도가 다소 느려 보행 효율성 개선이 필요합니다.",
        })
        recs.append({
            "category": "평가",
            "title": "3개월 후 재평가",
            "description": "치료 효과를 확인하고 프로그램을 조정하기 위해 3개월 후 재평가합니다.",
            "priority": "medium",
            "frequency": "3개월마다",
            "rationale": "경도 위험군의 적극적 모니터링이 필요합니다.",
        })

    elif risk_score >= 50:
        # Moderate risk (50-69): intensive PT
        recs.append({
            "category": "물리치료",
            "title": "집중 물리치료 프로그램",
            "description": "전문 물리치료사의 지도 하에 근력 강화, 균형 훈련, 보행 훈련을 "
                           "포함한 집중 물리치료를 시행합니다.",
            "priority": "high",
            "frequency": "주 3회, 45-60분",
            "rationale": "중등도 낙상 위험으로 집중적인 재활 치료가 필요합니다.",
        })
        recs.append({
            "category": "보조기구",
            "title": "보조 기구 평가",
            "description": "보행 보조 기구(지팡이, 워커 등)의 필요성을 평가하고, "
                           "필요 시 적합한 보조 기구를 처방합니다.",
            "priority": "high",
            "frequency": "1회 (필요 시 추가)",
            "rationale": "보행 안정성이 저하되어 보조 기구 사용이 도움이 될 수 있습니다.",
        })
        recs.append({
            "category": "환경 평가",
            "title": "가정 환경 안전 점검",
            "description": "가정 내 낙상 위험 요소(미끄러운 바닥, 문턱, 조명 등)를 점검하고 "
                           "개선 방안을 제안합니다.",
            "priority": "high",
            "frequency": "1회 (6개월마다 재점검)",
            "rationale": "중등도 낙상 위험에서는 환경 요인이 낙상 발생에 큰 영향을 미칩니다.",
        })
        recs.append({
            "category": "평가",
            "title": "매월 재평가",
            "description": "치료 반응과 기능 변화를 매달 모니터링합니다.",
            "priority": "high",
            "frequency": "매월",
            "rationale": "중등도 위험군의 면밀한 추적 관찰이 필요합니다.",
        })

    else:
        # High risk (0-49): daily PT, fall prevention
        recs.append({
            "category": "물리치료",
            "title": "일일 물리치료",
            "description": "매일 전문 물리치료를 시행합니다. 근력 강화, 균형 훈련, "
                           "보행 훈련, 기능적 이동 훈련을 포함합니다.",
            "priority": "high",
            "frequency": "매일, 60분",
            "rationale": "고위험 낙상군으로 즉각적이고 집중적인 재활이 필요합니다.",
        })
        recs.append({
            "category": "낙상 예방",
            "title": "낙상 예방 프로그램",
            "description": "다학제 낙상 예방 프로그램에 참여합니다. 약물 검토, 시력 검사, "
                           "영양 평가, 보행 보조기구 처방 등을 포함합니다.",
            "priority": "high",
            "frequency": "프로그램 기간 동안 지속",
            "rationale": "고위험군은 포괄적인 낙상 예방 접근이 필수적입니다.",
        })
        recs.append({
            "category": "환경 평가",
            "title": "가정 환경 개조",
            "description": "안전 손잡이 설치, 미끄럼 방지 바닥재, 문턱 제거, "
                           "적절한 조명 설치 등 가정 환경을 개조합니다.",
            "priority": "high",
            "frequency": "즉시 시행",
            "rationale": "고위험 환자의 가정 환경 개조는 낙상 발생률을 크게 줄입니다.",
        })
        recs.append({
            "category": "보호자 교육",
            "title": "보호자/간병인 교육",
            "description": "안전한 이동 보조 방법, 낙상 시 대처법, 응급 상황 대응 등에 대해 "
                           "보호자를 교육합니다.",
            "priority": "high",
            "frequency": "초기 교육 + 월 1회 보충",
            "rationale": "보호자의 적절한 지원은 고위험 환자의 안전에 필수적입니다.",
        })
        recs.append({
            "category": "평가",
            "title": "주간 모니터링",
            "description": "매주 기능 상태와 치료 반응을 모니터링하고 프로그램을 조정합니다.",
            "priority": "high",
            "frequency": "매주",
            "rationale": "고위험군은 빈번한 모니터링을 통한 조기 개입이 중요합니다.",
        })

    return recs


def _disease_specific_recommendations(disease_profile_name: str) -> List[dict]:
    """질환별 추가 추천"""
    recs = []

    if disease_profile_name == "parkinsons":
        recs.extend([
            {
                "category": "특수 치료",
                "title": "리듬 청각 자극 (RAS) 훈련",
                "description": "메트로놈이나 음악의 리듬에 맞춰 보행하는 리듬 청각 자극 훈련을 시행합니다. "
                               "보행 속도, 보폭, 케이던스 개선에 효과적입니다.",
                "priority": "high",
                "frequency": "주 3회, 20-30분",
                "rationale": "파킨슨병의 서동(bradykinesia)과 소보행(festination) 개선에 "
                             "리듬 청각 자극이 강력한 근거를 가지고 있습니다.",
            },
            {
                "category": "인지-운동",
                "title": "이중과제 훈련 (Dual-task Training)",
                "description": "보행 중 인지 과제(계산, 단어 나열 등)를 동시에 수행하는 훈련입니다. "
                               "실제 일상생활 상황에서의 보행 안전성을 향상시킵니다.",
                "priority": "high",
                "frequency": "주 2-3회, 15-20분",
                "rationale": "파킨슨병 환자는 이중과제 시 보행 능력이 크게 저하되며, "
                             "이 훈련이 일상 낙상 예방에 효과적입니다.",
            },
            {
                "category": "특수 치료",
                "title": "동결보행 관리 전략",
                "description": "동결보행(freezing of gait) 대처 전략을 교육합니다. "
                               "시각적 단서(레이저 지팡이), 청각적 단서, 주의 전환 전략 등을 포함합니다.",
                "priority": "medium",
                "frequency": "교육 후 일상 적용",
                "rationale": "동결보행은 파킨슨병의 주요 낙상 원인이며, "
                             "적절한 전략 교육으로 발생 빈도와 영향을 줄일 수 있습니다.",
            },
        ])

    elif disease_profile_name == "stroke":
        recs.extend([
            {
                "category": "특수 치료",
                "title": "체중 이동 훈련",
                "description": "마비측과 비마비측 간의 균형 잡힌 체중 이동을 훈련합니다. "
                               "시각적 바이오피드백을 활용한 기립/보행 훈련을 포함합니다.",
                "priority": "high",
                "frequency": "주 3-5회, 20-30분",
                "rationale": "뇌졸중 후 편마비로 인한 비대칭적 체중 분배를 교정하여 "
                             "균형과 보행 안정성을 향상시킵니다.",
            },
            {
                "category": "근력 훈련",
                "title": "마비측 근력 강화",
                "description": "마비측 하지의 근력을 집중적으로 강화합니다. "
                               "점진적 저항 운동, 기능적 전기 자극(FES) 등을 활용합니다.",
                "priority": "high",
                "frequency": "주 3-5회, 30분",
                "rationale": "마비측 근력 회복은 보행 대칭성과 속도 개선의 핵심입니다.",
            },
            {
                "category": "특수 치료",
                "title": "강제 유도 운동 치료 (CIMT)",
                "description": "비마비측 사용을 제한하고 마비측을 집중 사용하도록 유도하는 "
                               "강제 유도 운동 치료를 시행합니다.",
                "priority": "medium",
                "frequency": "주 5회, 2-3시간 (집중 프로그램)",
                "rationale": "뇌졸중 후 학습된 비사용(learned non-use)을 극복하고 "
                             "마비측 기능 회복을 촉진합니다.",
            },
        ])

    elif disease_profile_name == "knee_oa":
        recs.extend([
            {
                "category": "관절 운동",
                "title": "슬관절 관절 가동 범위(ROM) 운동",
                "description": "슬관절의 굴곡/신전 관절 가동 범위를 유지하고 개선하기 위한 "
                               "능동적/수동적 ROM 운동을 시행합니다.",
                "priority": "high",
                "frequency": "매일, 15-20분",
                "rationale": "슬관절 OA/TKA 후 ROM 감소가 보행 패턴 이상의 주요 원인입니다.",
            },
            {
                "category": "수중 치료",
                "title": "수중 운동 치료",
                "description": "수중에서의 보행 훈련 및 관절 운동을 시행합니다. "
                               "부력으로 관절 부하를 줄이면서 운동 효과를 얻을 수 있습니다.",
                "priority": "medium",
                "frequency": "주 2-3회, 30-45분",
                "rationale": "수중 치료는 관절 부하를 줄이면서 근력과 ROM을 개선할 수 있어 "
                             "OA 환자에게 효과적입니다.",
            },
            {
                "category": "통증 관리",
                "title": "통증 관리 프로그램",
                "description": "온열/냉각 치료, 경피 전기 신경 자극(TENS), 관절 보호 교육 등을 "
                               "통해 통증을 관리합니다.",
                "priority": "medium",
                "frequency": "통증 수준에 따라 조절",
                "rationale": "통증 감소는 운동 참여도와 보행 기능 개선의 전제 조건입니다.",
            },
        ])

    elif disease_profile_name == "hip_oa":
        recs.extend([
            {
                "category": "관절 운동",
                "title": "고관절 ROM 운동",
                "description": "고관절의 굴곡, 신전, 외전 관절 가동 범위를 개선하기 위한 운동을 시행합니다.",
                "priority": "high",
                "frequency": "매일, 15-20분",
                "rationale": "고관절 ROM 감소는 보행 패턴 이상과 낙상 위험 증가의 주요 원인입니다.",
            },
            {
                "category": "수중 치료",
                "title": "수중 운동 치료",
                "description": "수중에서의 보행 훈련 및 고관절 가동 운동을 시행합니다.",
                "priority": "medium",
                "frequency": "주 2-3회, 30-45분",
                "rationale": "부력으로 고관절 부하를 줄이면서 기능을 개선합니다.",
            },
            {
                "category": "통증 관리",
                "title": "통증 관리 프로그램",
                "description": "물리적 치료와 약물 요법을 병행하여 통증을 관리합니다.",
                "priority": "medium",
                "frequency": "통증 수준에 따라 조절",
                "rationale": "통증 경감이 기능적 활동 참여의 전제 조건입니다.",
            },
        ])

    elif disease_profile_name == "fall_risk":
        recs.extend([
            {
                "category": "균형 훈련",
                "title": "태극권 (Tai Chi) 프로그램",
                "description": "느리고 유연한 동작을 통해 균형, 유연성, 하지 근력을 향상시키는 "
                               "태극권 프로그램에 참여합니다.",
                "priority": "high",
                "frequency": "주 2-3회, 45-60분",
                "rationale": "태극권은 노인의 낙상 예방에 가장 강력한 근거를 가진 운동 프로그램 중 하나입니다.",
            },
            {
                "category": "심리",
                "title": "균형 자신감 훈련",
                "description": "낙상 공포를 줄이고 활동 참여를 촉진하기 위한 인지행동 접근 "
                               "프로그램(ABC: Activities-specific Balance Confidence)에 참여합니다.",
                "priority": "medium",
                "frequency": "주 1회, 60분 (8-12주 프로그램)",
                "rationale": "낙상 공포는 활동 회피를 초래하여 오히려 기능 저하와 낙상 위험 증가로 이어집니다.",
            },
        ])

    return recs


def _test_data_recommendations(latest_tests: List[dict]) -> List[dict]:
    """검사 데이터 기반 추가 추천"""
    recs = []

    if not latest_tests:
        return recs

    latest = latest_tests[0]
    speed = latest.get("walk_speed_mps", 0)

    # Very slow speed - community ambulation concern
    if speed > 0 and speed < 0.4:
        recs.append({
            "category": "보행 훈련",
            "title": "실내 보행 안전 훈련",
            "description": "현재 보행 속도가 실내 보행 수준에 해당합니다. "
                           "안전한 실내 이동을 위한 맞춤 훈련을 시행합니다.",
            "priority": "high",
            "frequency": "매일, 짧은 시간 반복",
            "rationale": f"현재 보행 속도({speed:.2f} m/s)가 실내 보행 기준(0.4 m/s) 미만입니다.",
        })
    elif speed > 0 and speed < 0.8:
        recs.append({
            "category": "보행 훈련",
            "title": "지역사회 보행 준비 훈련",
            "description": "지역사회 독립 보행을 목표로 보행 속도와 지구력을 향상시키는 "
                           "체계적 보행 훈련을 시행합니다.",
            "priority": "high",
            "frequency": "주 3-5회, 20-30분",
            "rationale": f"현재 보행 속도({speed:.2f} m/s)가 지역사회 보행 기준(1.0 m/s)에 미달합니다.",
        })

    return recs
