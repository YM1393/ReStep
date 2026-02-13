"""한글 임상 비교 리포트 생성 서비스"""
from datetime import datetime
from typing import Optional


def _calc_fall_risk_score(speed: float, time: float) -> tuple:
    """낙상 위험도 점수 계산 (0-100)"""
    speed_score = 50 if speed >= 1.2 else 40 if speed >= 1.0 else 25 if speed >= 0.8 else 10
    time_score = 50 if time <= 8.3 else 40 if time <= 10 else 25 if time <= 12.5 else 10
    total = speed_score + time_score
    if total >= 90:
        label = "정상"
    elif total >= 70:
        label = "경도 위험"
    elif total >= 50:
        label = "중등도 위험"
    else:
        label = "고위험"
    return total, label


def _format_date(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%Y년 %m월 %d일")
    except (ValueError, TypeError):
        return date_str[:10] if date_str else "날짜 없음"


def _calc_age(birth_date: str) -> int:
    try:
        bd = datetime.fromisoformat(birth_date)
        today = datetime.now()
        return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
    except (ValueError, TypeError):
        return 0


def generate_comparison_report(
    current_test: dict,
    previous_test: Optional[dict],
    patient: dict,
    goal: Optional[dict] = None
) -> dict:
    """임상 비교 리포트 생성"""

    gender_str = "M" if patient.get('gender') == 'M' else "F"
    age = _calc_age(patient.get('birth_date', ''))
    test_type = current_test.get('test_type', '10MWT')

    lines = []
    lines.append(f"검사일: {_format_date(current_test.get('test_date', ''))}")
    lines.append(f"환자: {patient.get('name', '')} ({gender_str}/{age}세)")
    lines.append(f"검사유형: {test_type}")
    lines.append("")

    is_improved = False
    improvement_pct = 0.0

    if test_type == '10MWT':
        cur_speed = current_test.get('walk_speed_mps', 0)
        cur_time = current_test.get('walk_time_seconds', 0)

        lines.append("[보행 시간]")
        if previous_test:
            prev_time = previous_test.get('walk_time_seconds', 0)
            time_diff = cur_time - prev_time
            time_pct = abs(time_diff / prev_time * 100) if prev_time > 0 else 0
            # 시간이 줄어들면 향상
            improvement_pct = (-time_diff / prev_time * 100) if prev_time > 0 else 0
            is_improved = time_diff < 0
            sign = "+" if time_diff > 0 else ""
            change_word = "증가" if time_diff > 0 else "단축"
            lines.append(f"현재: {cur_time:.2f}초 | 이전({_format_date(previous_test.get('test_date', ''))}): {prev_time:.2f}초")
            lines.append(f"변화: {sign}{time_diff:.2f}초 ({time_pct:.1f}% {change_word})")
        else:
            lines.append(f"현재: {cur_time:.2f}초 (첫 검사)")
        lines.append("")

        lines.append("[보행 속도]")
        if previous_test:
            prev_speed = previous_test.get('walk_speed_mps', 0)
            speed_diff = cur_speed - prev_speed
            speed_pct = abs(speed_diff / prev_speed * 100) if prev_speed > 0 else 0
            sign = "+" if speed_diff > 0 else ""
            change_word = "향상" if speed_diff > 0 else "저하"
            lines.append(f"현재: {cur_speed:.2f} m/s | 이전: {prev_speed:.2f} m/s")
            lines.append(f"변화: {sign}{speed_diff:.2f} m/s ({speed_pct:.1f}% {change_word})")
        else:
            lines.append(f"현재: {cur_speed:.2f} m/s (첫 검사)")
        lines.append("")

        # 낙상 위험도
        cur_risk, cur_risk_label = _calc_fall_risk_score(cur_speed, cur_time)
        lines.append("[낙상 위험도]")
        if previous_test:
            prev_risk, prev_risk_label = _calc_fall_risk_score(
                previous_test.get('walk_speed_mps', 0),
                previous_test.get('walk_time_seconds', 0)
            )
            risk_diff = cur_risk - prev_risk
            sign = "+" if risk_diff > 0 else ""
            lines.append(f"현재: {cur_risk}점 ({cur_risk_label}) | 이전: {prev_risk}점 ({prev_risk_label})")
            lines.append(f"변화: {sign}{risk_diff}점")
        else:
            lines.append(f"현재: {cur_risk}점 ({cur_risk_label})")
        lines.append("")

    elif test_type == 'TUG':
        cur_time = current_test.get('walk_time_seconds', 0)
        lines.append("[TUG 총 시간]")
        if previous_test:
            prev_time = previous_test.get('walk_time_seconds', 0)
            time_diff = cur_time - prev_time
            time_pct = abs(time_diff / prev_time * 100) if prev_time > 0 else 0
            improvement_pct = -time_diff / prev_time * 100 if prev_time > 0 else 0
            is_improved = time_diff < 0
            sign = "+" if time_diff > 0 else ""
            change_word = "증가" if time_diff > 0 else "단축"
            lines.append(f"현재: {cur_time:.2f}초 | 이전({_format_date(previous_test.get('test_date', ''))}): {prev_time:.2f}초")
            lines.append(f"변화: {sign}{time_diff:.2f}초 ({time_pct:.1f}% {change_word})")
        else:
            lines.append(f"현재: {cur_time:.2f}초 (첫 검사)")
        lines.append("")

    elif test_type == 'BBS':
        cur_score = current_test.get('walk_time_seconds', 0)  # BBS total stored here
        lines.append("[BBS 총점]")
        if previous_test:
            prev_score = previous_test.get('walk_time_seconds', 0)
            score_diff = cur_score - prev_score
            improvement_pct = (score_diff / prev_score * 100) if prev_score > 0 else 0
            is_improved = score_diff > 0
            sign = "+" if score_diff > 0 else ""
            lines.append(f"현재: {int(cur_score)}점/56 | 이전: {int(prev_score)}점/56")
            lines.append(f"변화: {sign}{int(score_diff)}점")
        else:
            lines.append(f"현재: {int(cur_score)}점/56 (첫 검사)")
        lines.append("")

    # 목표 달성 현황
    if goal and goal.get('status') == 'active':
        lines.append("[목표 달성 현황]")
        if test_type == '10MWT':
            target_time = goal.get('target_time_seconds')
            if not target_time and goal.get('target_speed_mps'):
                target_time = round(10.0 / goal['target_speed_mps'], 1) if goal['target_speed_mps'] > 0 else 0
            if target_time:
                current = current_test.get('walk_time_seconds', 0)
                pct = min(100, (target_time / current * 100)) if current > 0 else 0
                lines.append(f"목표: {target_time:.1f}초 이내 | 달성률: {pct:.1f}%")
        elif test_type == 'TUG' and goal.get('target_time_seconds'):
            target = goal['target_time_seconds']
            current = current_test.get('walk_time_seconds', 0)
            pct = min(100, (target / current * 100)) if current > 0 else 0
            lines.append(f"목표: {target:.1f}초 이내 | 달성률: {pct:.1f}%")
        if goal.get('target_date'):
            lines.append(f"목표일: {_format_date(goal['target_date'])}")
        lines.append("")

    # 종합 소견
    lines.append("[종합 소견]")
    if previous_test:
        if is_improved:
            if test_type == '10MWT' or test_type == 'TUG':
                lines.append(f"지난 검사 대비 보행 시간이 {abs(improvement_pct):.1f}% 단축되었습니다.")
            else:
                lines.append(f"지난 검사 대비 {abs(improvement_pct):.1f}% 향상되었습니다.")
            lines.append("긍정적인 변화가 관찰되며, 현재 치료 방향을 유지하는 것이 권장됩니다.")
        elif improvement_pct == 0:
            lines.append("지난 검사와 유사한 수준을 유지하고 있습니다.")
        else:
            if test_type == '10MWT' or test_type == 'TUG':
                lines.append(f"지난 검사 대비 보행 시간이 {abs(improvement_pct):.1f}% 증가하였습니다.")
            else:
                lines.append(f"지난 검사 대비 {abs(improvement_pct):.1f}% 저하되었습니다.")
            lines.append("치료 계획 재검토가 필요할 수 있습니다.")
    else:
        lines.append("초기 평가 검사입니다. 추후 검사와 비교하여 변화를 추적합니다.")

    summary_text = "\n".join(lines)

    return {
        "summary_text": summary_text,
        "improvement_pct": round(improvement_pct, 1),
        "is_improved": is_improved,
        "test_type": test_type,
        "current_date": current_test.get('test_date', ''),
        "previous_date": previous_test.get('test_date', '') if previous_test else None
    }
