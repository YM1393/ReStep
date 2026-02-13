"""AI 리포트 자동 생성 서비스

검사 데이터, 추세 분석, 정상 범위 비교, 재활 추천을 종합하여
구조화된 임상 리포트를 자동 생성합니다.
"""
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.models.database import db
from app.services.comparison_report import generate_comparison_report
from app.services.trend_analysis import analyze_trends
from app.services.rehab_recommendations import get_recommendations


def _format_date(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%Y년 %m월 %d일")
    except (ValueError, TypeError):
        return date_str[:10] if date_str else ""


def _calc_age(birth_date: str) -> int:
    try:
        birth = datetime.fromisoformat(birth_date)
        today = datetime.now()
        return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    except (ValueError, TypeError):
        return 0


def _risk_assessment(speed: float, time: float) -> Dict[str, Any]:
    """낙상 위험도 평가"""
    if speed >= 1.2:
        level, label = 'normal', '정상'
    elif speed >= 1.0:
        level, label = 'mild', '경도 위험'
    elif speed >= 0.8:
        level, label = 'moderate', '중등도 위험'
    else:
        level, label = 'high', '고위험'

    score = min(100, int(speed / 1.2 * 100))

    interpretations = []
    if speed >= 1.2:
        interpretations.append('지역사회 독립 보행 가능')
    elif speed >= 0.8:
        interpretations.append('제한적 지역사회 보행 가능')
    else:
        interpretations.append('가정 내 보행 수준')
        interpretations.append('낙상 위험 증가')

    if time > 12.5:
        interpretations.append('보행 시간 지연 - 보조 기기 필요성 평가 권장')

    return {
        'level': level,
        'label': label,
        'score': score,
        'interpretations': interpretations,
    }


def _assess_clinical_variables(cv: dict) -> List[Dict[str, str]]:
    """임상 변수 해석"""
    findings = []

    cadence = cv.get('cadence', {})
    if cadence.get('value'):
        val = cadence['value']
        if val < 80:
            findings.append({'variable': '분당 보수', 'value': f"{val:.0f} steps/min", 'assessment': '정상 범위 이하 - 보행 리듬 저하'})
        elif val > 140:
            findings.append({'variable': '분당 보수', 'value': f"{val:.0f} steps/min", 'assessment': '정상 범위 이상 - 짧은 보폭 보상 가능성'})
        else:
            findings.append({'variable': '분당 보수', 'value': f"{val:.0f} steps/min", 'assessment': '정상 범위'})

    step_time = cv.get('step_time', {})
    if step_time.get('cv'):
        cv_val = step_time['cv']
        if cv_val > 10:
            findings.append({'variable': '보행 주기 변동성', 'value': f"{cv_val:.1f}%", 'assessment': '불규칙한 보행 패턴 - 균형 장애 가능성'})
        else:
            findings.append({'variable': '보행 주기 변동성', 'value': f"{cv_val:.1f}%", 'assessment': '정상 범위의 보행 규칙성'})

    asym = cv.get('step_time_asymmetry', {})
    if asym.get('value') is not None:
        val = abs(asym['value'])
        if val > 10:
            findings.append({'variable': '좌우 대칭성', 'value': f"{val:.1f}%", 'assessment': '비대칭 보행 - 편측 약화 또는 통증 확인 필요'})

    trunk = cv.get('trunk_inclination', {})
    if trunk.get('std'):
        val = trunk['std']
        if val > 5:
            findings.append({'variable': '체간 안정성', 'value': f"SD {val:.1f}°", 'assessment': '체간 동요 증가 - 코어 안정성 강화 필요'})

    return findings


def generate_ai_report(patient_id: str, test_id: str) -> Dict[str, Any]:
    """AI 임상 리포트 자동 생성

    Returns:
        {
            patient_summary: {...},
            test_results: {...},
            gait_analysis: {...},
            progress: {...},
            risk_assessment: {...},
            recommendations: [...],
            generated_at: str,
        }
    """
    # 1. 환자 정보
    patient = db.get_patient(patient_id)
    if not patient:
        raise ValueError("환자를 찾을 수 없습니다.")

    # 2. 검사 데이터
    test = db.get_test(test_id)
    if not test:
        raise ValueError("검사를 찾을 수 없습니다.")

    analysis_data = {}
    if test.get('analysis_data'):
        if isinstance(test['analysis_data'], str):
            try:
                analysis_data = json.loads(test['analysis_data'])
            except (json.JSONDecodeError, TypeError):
                pass
        else:
            analysis_data = test['analysis_data']

    test_type = test.get('test_type', '10MWT')
    speed = test['walk_speed_mps']
    time_sec = test['walk_time_seconds']

    # 3. 환자 요약
    age = _calc_age(patient.get('birth_date', ''))
    patient_summary = {
        'name': patient['name'],
        'patient_number': patient.get('patient_number', ''),
        'gender': '남성' if patient.get('gender') == 'M' else '여성',
        'age': age,
        'height_cm': patient.get('height_cm', 0),
        'diagnosis': patient.get('diagnosis', ''),
        'test_date': _format_date(test.get('test_date', '')),
    }

    # 4. 검사 결과
    test_results = {
        'test_type': test_type,
        'test_type_label': {'10MWT': '10m 보행검사', 'TUG': 'TUG 검사', 'BBS': 'BBS 검사'}.get(test_type, test_type),
        'walk_speed_mps': round(speed, 3),
        'walk_time_seconds': round(time_sec, 2),
    }

    # 5. 보행 분석
    gait_analysis = {
        'gait_pattern': None,
        'clinical_findings': [],
        'confidence': None,
        'asymmetry_warnings': [],
    }

    gp = analysis_data.get('gait_pattern')
    if gp:
        gait_analysis['gait_pattern'] = {
            'shoulder_tilt': f"평균 {gp.get('shoulder_tilt_avg', 0):.1f}° ({gp.get('shoulder_tilt_direction', '')})",
            'hip_tilt': f"평균 {gp.get('hip_tilt_avg', 0):.1f}° ({gp.get('hip_tilt_direction', '')})",
            'assessment': gp.get('assessment', ''),
        }

    cv = analysis_data.get('clinical_variables', {})
    if cv:
        gait_analysis['clinical_findings'] = _assess_clinical_variables(cv)

    confidence = analysis_data.get('confidence_score')
    if confidence:
        gait_analysis['confidence'] = {
            'score': confidence.get('score', 0),
            'level': confidence.get('level', ''),
            'label': confidence.get('label', ''),
        }

    warnings = analysis_data.get('asymmetry_warnings', [])
    if warnings:
        gait_analysis['asymmetry_warnings'] = [
            {'type': w.get('label', ''), 'severity': w.get('severity', ''), 'description': w.get('description', '')}
            for w in warnings
        ]

    # 6. 경과 (비교 + 추세)
    progress = {
        'comparison': None,
        'trend': None,
        'goal_status': None,
    }

    tests = db.get_patient_tests(patient_id, test_type)
    if len(tests) >= 2:
        try:
            comp = generate_comparison_report(patient_id, test_id=test_id)
            progress['comparison'] = {
                'summary': comp.get('summary_text', ''),
                'improvement_pct': comp.get('improvement_pct', 0),
                'is_improved': comp.get('is_improved', False),
            }
        except Exception:
            pass

    if len(tests) >= 3:
        try:
            goals = db.get_patient_goals(patient_id, status='active')
            goal = next((g for g in goals if g.get('test_type') == test_type), None)
            trend = analyze_trends(tests, test_type, goal)
            if trend.get('sufficient_data'):
                progress['trend'] = {
                    'direction': trend.get('trend_direction', ''),
                    'direction_label': {'improving': '개선 추세', 'stable': '안정', 'declining': '하락 추세'}.get(
                        trend.get('trend_direction', ''), ''),
                    'slope_per_week': trend.get('slope_per_week'),
                    'r_squared': trend.get('r_squared'),
                    'goal_eta': trend.get('goal_eta'),
                }
        except Exception:
            pass

    # Goal progress
    try:
        goals = db.get_patient_goals(patient_id, status='active')
        for g in goals:
            if g.get('test_type') == test_type:
                target = g.get('target_speed_mps') or g.get('target_time_seconds')
                if target:
                    if g.get('target_speed_mps'):
                        pct = min(100, round(speed / target * 100, 1))
                    else:
                        pct = min(100, round(target / time_sec * 100, 1)) if time_sec > 0 else 0
                    progress['goal_status'] = {
                        'target': target,
                        'current': speed if g.get('target_speed_mps') else time_sec,
                        'achievement_pct': pct,
                        'status': g.get('status', 'active'),
                    }
                break
    except Exception:
        pass

    # 7. 위험도 평가
    risk = _risk_assessment(speed, time_sec)

    # 8. 재활 추천
    recommendations = []
    try:
        rec_result = get_recommendations(
            speed_mps=speed,
            time_seconds=time_sec,
            test_type=test_type,
            diagnosis=patient.get('diagnosis'),
            analysis_data=analysis_data,
        )
        recommendations = rec_result.get('recommendations', [])
    except Exception:
        pass

    return {
        'patient_summary': patient_summary,
        'test_results': test_results,
        'gait_analysis': gait_analysis,
        'progress': progress,
        'risk_assessment': risk,
        'recommendations': recommendations,
        'generated_at': datetime.now().isoformat(),
    }
