import os
import io
import csv
import tempfile
from datetime import datetime
from typing import List, Dict, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.graphics import renderPDF

from app.services.fall_risk import get_fall_risk_assessment
from app.services.report_templates import ReportTemplate, get_template, STANDARD_TEMPLATE

# 한글 폰트 등록
import platform
_KR_FONT_REGISTERED = False
def _register_korean_font():
    global _KR_FONT_REGISTERED
    if _KR_FONT_REGISTERED:
        return
    if platform.system() == 'Windows':
        font_path = 'C:/Windows/Fonts/malgun.ttf'
        font_bold_path = 'C:/Windows/Fonts/malgunbd.ttf'
    else:
        font_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
        font_bold_path = font_path
    try:
        pdfmetrics.registerFont(TTFont('Korean', font_path))
        pdfmetrics.registerFont(TTFont('Korean-Bold', font_bold_path))
        _KR_FONT_REGISTERED = True
    except Exception:
        pass

FONT_NAME = 'Korean'
FONT_BOLD = 'Korean-Bold'


def generate_csv_report(test_data: Dict) -> str:
    """CSV 리포트 생성"""
    output = io.StringIO()
    writer = csv.writer(output)

    # 헤더
    writer.writerow(["10m Walk Test Report"])
    writer.writerow([])

    # 환자 정보
    patient = test_data.get("patients", {})
    writer.writerow(["Patient Information"])
    writer.writerow(["Name", patient.get("name", "N/A")])
    writer.writerow(["Patient Number", patient.get("patient_number", "N/A")])
    writer.writerow(["Gender", "Male" if patient.get("gender") == "M" else "Female"])
    writer.writerow(["Birth Date", patient.get("birth_date", "N/A")])
    writer.writerow(["Height (cm)", patient.get("height_cm", "N/A")])
    writer.writerow(["Diagnosis", patient.get("diagnosis", "N/A")])
    writer.writerow([])

    # 검사 결과
    writer.writerow(["Test Results"])
    writer.writerow(["Test Date", test_data.get("test_date", "N/A")])
    writer.writerow(["Walk Time (seconds)", test_data.get("walk_time_seconds", "N/A")])
    writer.writerow(["Walk Speed (m/s)", test_data.get("walk_speed_mps", "N/A")])
    writer.writerow(["Notes", test_data.get("notes", "")])
    writer.writerow([])

    # 분석 데이터
    analysis = test_data.get("analysis_data", {})
    if analysis:
        writer.writerow(["Analysis Details"])
        writer.writerow(["FPS", analysis.get("fps", "N/A")])
        writer.writerow(["Total Frames", analysis.get("total_frames", "N/A")])
        writer.writerow(["Start Frame", analysis.get("start_frame", "N/A")])
        writer.writerow(["End Frame", analysis.get("end_frame", "N/A")])

    return output.getvalue()


def create_speed_chart(all_tests: List[Dict], width: float = 170*mm, height: float = 80*mm) -> Drawing:
    """보행 속도 추이 차트 생성"""
    drawing = Drawing(width, height)

    if len(all_tests) < 2:
        return drawing

    # 데이터 준비 (최근 10개)
    tests = all_tests[-10:]
    speeds = [t.get("walk_speed_mps", 0) for t in tests]

    # 차트 영역
    chart = LinePlot()
    chart.x = 40
    chart.y = 25
    chart.width = width - 60
    chart.height = height - 45

    # 데이터 설정
    chart.data = [[(i, s) for i, s in enumerate(speeds)]]

    # 스타일
    chart.lines[0].strokeColor = colors.HexColor('#3b82f6')
    chart.lines[0].strokeWidth = 2
    chart.lines[0].symbol = makeMarker('Circle')
    chart.lines[0].symbol.fillColor = colors.HexColor('#3b82f6')
    chart.lines[0].symbol.strokeColor = colors.white
    chart.lines[0].symbol.size = 6

    # 축 설정
    chart.xValueAxis.valueMin = 0
    chart.xValueAxis.valueMax = len(speeds) - 1
    chart.xValueAxis.valueSteps = list(range(len(speeds)))
    chart.xValueAxis.labelTextFormat = lambda x: str(int(x) + 1)
    chart.xValueAxis.labels.fontSize = 8

    chart.yValueAxis.valueMin = 0
    chart.yValueAxis.valueMax = 2.0
    chart.yValueAxis.valueSteps = [0, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0]
    chart.yValueAxis.labels.fontSize = 8

    drawing.add(chart)

    # 기준선 (정상 1.2, 위험 0.8)
    chart_left = 40
    chart_bottom = 25
    chart_width = width - 60
    chart_height = height - 45

    # 정상 기준선 (1.2)
    y_normal = chart_bottom + (1.2 / 2.0) * chart_height
    drawing.add(Line(chart_left, y_normal, chart_left + chart_width, y_normal,
                    strokeColor=colors.HexColor('#22c55e'), strokeWidth=1, strokeDashArray=[4, 2]))

    # 위험 기준선 (0.8)
    y_danger = chart_bottom + (0.8 / 2.0) * chart_height
    drawing.add(Line(chart_left, y_danger, chart_left + chart_width, y_danger,
                    strokeColor=colors.HexColor('#ef4444'), strokeWidth=1, strokeDashArray=[4, 2]))

    # 제목
    drawing.add(String(width / 2, height - 8, "Walking Speed Trend (m/s)",
                      fontSize=10, textAnchor='middle', fillColor=colors.HexColor('#374151')))

    return drawing


def create_time_chart(all_tests: List[Dict], width: float = 170*mm, height: float = 80*mm) -> Drawing:
    """보행 시간 추이 차트 생성"""
    drawing = Drawing(width, height)

    if len(all_tests) < 2:
        return drawing

    # 데이터 준비 (최근 10개)
    tests = all_tests[-10:]
    times = [t.get("walk_time_seconds", 0) for t in tests]

    # 차트 영역
    chart = LinePlot()
    chart.x = 40
    chart.y = 25
    chart.width = width - 60
    chart.height = height - 45

    # 데이터 설정
    chart.data = [[(i, t) for i, t in enumerate(times)]]

    # 스타일
    chart.lines[0].strokeColor = colors.HexColor('#8b5cf6')
    chart.lines[0].strokeWidth = 2
    chart.lines[0].symbol = makeMarker('Circle')
    chart.lines[0].symbol.fillColor = colors.HexColor('#8b5cf6')
    chart.lines[0].symbol.strokeColor = colors.white
    chart.lines[0].symbol.size = 6

    # 축 설정
    chart.xValueAxis.valueMin = 0
    chart.xValueAxis.valueMax = len(times) - 1
    chart.xValueAxis.valueSteps = list(range(len(times)))
    chart.xValueAxis.labelTextFormat = lambda x: str(int(x) + 1)
    chart.xValueAxis.labels.fontSize = 8

    chart.yValueAxis.valueMin = 0
    chart.yValueAxis.valueMax = 20
    chart.yValueAxis.valueSteps = [0, 5, 8.3, 10, 12.5, 15, 20]
    chart.yValueAxis.labels.fontSize = 8

    drawing.add(chart)

    # 기준선
    chart_left = 40
    chart_bottom = 25
    chart_width = width - 60
    chart_height = height - 45

    # 정상 기준선 (8.3초)
    y_normal = chart_bottom + (8.3 / 20) * chart_height
    drawing.add(Line(chart_left, y_normal, chart_left + chart_width, y_normal,
                    strokeColor=colors.HexColor('#22c55e'), strokeWidth=1, strokeDashArray=[4, 2]))

    # 위험 기준선 (12.5초)
    y_danger = chart_bottom + (12.5 / 20) * chart_height
    drawing.add(Line(chart_left, y_danger, chart_left + chart_width, y_danger,
                    strokeColor=colors.HexColor('#ef4444'), strokeWidth=1, strokeDashArray=[4, 2]))

    # 제목
    drawing.add(String(width / 2, height - 8, "Walking Time Trend (seconds)",
                      fontSize=10, textAnchor='middle', fillColor=colors.HexColor('#374151')))

    return drawing


def generate_pdf_report(
    test_data: Dict,
    patient_data: Dict,
    all_tests: List[Dict],
    template_name: str = "standard"
) -> str:
    """PDF 리포트 생성"""
    _register_korean_font()

    template = get_template(template_name)
    header_color = template.header_color

    # 임시 파일 생성
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_path = temp_file.name
    temp_file.close()

    doc = SimpleDocTemplate(
        temp_path,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    styles = getSampleStyleSheet()
    # 기본 스타일에 한글 폰트 적용 (모든 하위 스타일에 상속됨)
    for style_name in styles.byName:
        styles[style_name].fontName = FONT_NAME
    styles['Heading1'].fontName = FONT_BOLD
    styles['Heading2'].fontName = FONT_BOLD
    styles['Heading3'].fontName = FONT_BOLD

    # 커스텀 스타일 (한글 폰트 적용)
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=FONT_BOLD,
        fontSize=24,
        spaceAfter=20,
        alignment=1,  # Center
        textColor=colors.HexColor(header_color)
    )

    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=12,
        alignment=1,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=30
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=FONT_BOLD,
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor(header_color)
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=11,
        spaceAfter=6
    )

    elements = []

    # ========== 헤더 섹션 ==========
    elements.append(Paragraph("10m Walk Test Report", title_style))
    elements.append(Paragraph("10미터 보행 검사 결과 리포트", subtitle_style))

    # 생성 일시
    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ParagraphStyle('Date', parent=styles['Normal'], alignment=2, textColor=colors.grey, fontSize=9)
    ))
    elements.append(Spacer(1, 15))

    # ========== 환자 정보 ==========
    elements.append(Paragraph("Patient Information / 환자 정보", heading_style))

    patient_info = [
        ["Name / 이름", patient_data.get("name", "N/A")],
        ["Patient No. / 환자번호", patient_data.get("patient_number", "N/A")],
        ["Gender / 성별", "Male / 남" if patient_data.get("gender") == "M" else "Female / 여"],
        ["Birth Date / 생년월일", patient_data.get("birth_date", "N/A")],
        ["Height / 신장", f"{patient_data.get('height_cm', 'N/A')} cm"],
        ["Diagnosis / 진단명", patient_data.get("diagnosis", "N/A") or "-"],
    ]

    patient_table = Table(patient_info, colWidths=[70*mm, 100*mm])
    patient_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
        ('FONTNAME', (0, 0), (0, -1), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(patient_table)
    elements.append(Spacer(1, 20))

    # ========== 현재 검사 결과 ==========
    elements.append(Paragraph("Current Test Results / 검사 결과", heading_style))

    test_date = test_data.get("test_date", "N/A")
    if isinstance(test_date, str) and "T" in test_date:
        test_date = test_date.split("T")[0]

    walk_speed = test_data.get("walk_speed_mps", 0)
    walk_time = test_data.get("walk_time_seconds", 0)

    result_info = [
        ["Test Date / 검사일", test_date],
        ["Walk Time / 보행 시간", f"{walk_time:.2f} seconds"],
        ["Walk Speed / 보행 속도", f"{walk_speed:.2f} m/s"],
    ]

    result_table = Table(result_info, colWidths=[70*mm, 100*mm])
    result_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1e40af')),
        ('FONTNAME', (0, 0), (0, -1), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#93c5fd')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(result_table)
    elements.append(Spacer(1, 20))

    # ========== 낙상 위험 점수 ==========
    sections = template.sections_enabled

    elements.append(Paragraph("Fall Risk Assessment / 낙상 위험 평가", heading_style))

    risk_assessment = get_fall_risk_assessment(walk_speed, walk_time)
    score = risk_assessment["score"]
    risk_label = risk_assessment["label"]
    risk_desc = risk_assessment["description"]

    # 색상 결정
    if score >= 90:
        score_color = colors.HexColor('#22c55e')
        bg_color = colors.HexColor('#dcfce7')
    elif score >= 70:
        score_color = colors.HexColor('#3b82f6')
        bg_color = colors.HexColor('#dbeafe')
    elif score >= 50:
        score_color = colors.HexColor('#f97316')
        bg_color = colors.HexColor('#ffedd5')
    else:
        score_color = colors.HexColor('#ef4444')
        bg_color = colors.HexColor('#fee2e2')

    risk_info = [
        ["Total Score / 종합 점수", f"{score} / 100"],
        ["Speed Score / 속도 점수", f"{risk_assessment['speed_score']} / 50"],
        ["Time Score / 시간 점수", f"{risk_assessment['time_score']} / 50"],
        ["Risk Level / 위험 등급", risk_label],
        ["Assessment / 평가", risk_desc],
    ]

    risk_table = Table(risk_info, colWidths=[70*mm, 100*mm])
    risk_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('BACKGROUND', (0, 0), (0, -1), bg_color),
        ('TEXTCOLOR', (0, 0), (0, -1), score_color),
        ('FONTNAME', (0, 0), (0, -1), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTSIZE', (1, 0), (1, 0), 14),  # 점수 크게
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, score_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(risk_table)
    elements.append(Spacer(1, 15))

    # 점수 기준 안내
    score_guide = [
        ["90-100", "Normal / 정상", "70-89", "Mild / 경도 위험"],
        ["50-69", "Moderate / 중등도", "0-49", "High / 고위험"],
    ]
    guide_table = Table(score_guide, colWidths=[25*mm, 60*mm, 25*mm, 60*mm])
    guide_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor('#22c55e')),
        ('TEXTCOLOR', (2, 0), (2, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 1), (0, 1), colors.HexColor('#f97316')),
        ('TEXTCOLOR', (2, 1), (2, 1), colors.HexColor('#ef4444')),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    elements.append(guide_table)
    elements.append(Spacer(1, 20))

    # ========== 메모 섹션 ==========
    notes = test_data.get("notes", "")
    if notes:
        elements.append(Paragraph("Notes / 메모", heading_style))
        elements.append(Paragraph(notes, ParagraphStyle(
            'Notes',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4b5563'),
            backColor=colors.HexColor('#f9fafb'),
            borderPadding=10,
            borderColor=colors.HexColor('#e5e7eb'),
            borderWidth=1
        )))
        elements.append(Spacer(1, 20))

    # ========== 보행 패턴 분석 ==========
    analysis_data = test_data.get("analysis_data", {})
    gait_pattern = analysis_data.get("gait_pattern", {}) if analysis_data else {}

    if gait_pattern:
        elements.append(Paragraph("Gait Pattern Analysis / 보행 패턴 분석", heading_style))

        shoulder_avg = gait_pattern.get("shoulder_tilt_avg", 0)
        shoulder_max = gait_pattern.get("shoulder_tilt_max", 0)
        shoulder_dir = gait_pattern.get("shoulder_tilt_direction", "-")
        hip_avg = gait_pattern.get("hip_tilt_avg", 0)
        hip_max = gait_pattern.get("hip_tilt_max", 0)
        hip_dir = gait_pattern.get("hip_tilt_direction", "-")
        assessment = gait_pattern.get("assessment", "-")

        # 색상 결정
        if assessment == "정상 보행 패턴":
            pattern_color = colors.HexColor('#22c55e')
            pattern_bg = colors.HexColor('#dcfce7')
        else:
            pattern_color = colors.HexColor('#f97316')
            pattern_bg = colors.HexColor('#ffedd5')

        pattern_info = [
            ["Assessment / 종합 평가", assessment],
            ["Shoulder Tilt Avg / 어깨 기울기 (평균)", f"{shoulder_avg:+.1f}°"],
            ["Shoulder Tilt Max / 어깨 기울기 (최대)", f"{shoulder_max:.1f}°"],
            ["Shoulder Status / 어깨 상태", shoulder_dir],
            ["Hip Tilt Avg / 골반 기울기 (평균)", f"{hip_avg:+.1f}°"],
            ["Hip Tilt Max / 골반 기울기 (최대)", f"{hip_max:.1f}°"],
            ["Hip Status / 골반 상태", hip_dir],
        ]

        pattern_table = Table(pattern_info, colWidths=[85*mm, 85*mm])
        pattern_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('BACKGROUND', (0, 0), (0, -1), pattern_bg),
            ('BACKGROUND', (0, 0), (-1, 0), pattern_bg),
            ('TEXTCOLOR', (0, 0), (0, -1), pattern_color),
            ('TEXTCOLOR', (1, 0), (1, 0), pattern_color),
            ('FONTNAME', (0, 0), (0, -1), FONT_BOLD),
            ('FONTNAME', (1, 0), (1, 0), FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTSIZE', (1, 0), (1, 0), 11),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, pattern_color),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(pattern_table)
        elements.append(Spacer(1, 10))

        # 기준 안내
        elements.append(Paragraph(
            "Reference: ±2° or less = Normal / ±2~5° = Mild tilt / ±5° or more = Attention needed",
            ParagraphStyle('PatternGuide', parent=styles['Normal'],
                         fontSize=8, textColor=colors.grey)
        ))
        elements.append(Paragraph(
            "기준: ±2° 이내 = 정상 / ±2~5° = 경미한 기울기 / ±5° 이상 = 주의 필요",
            ParagraphStyle('PatternGuideKo', parent=styles['Normal'],
                         fontSize=8, textColor=colors.grey)
        ))
        elements.append(Spacer(1, 20))

    # ========== 보행 임상 변수 ==========
    clinical_variables = analysis_data.get("clinical_variables", {}) if analysis_data else {}
    if clinical_variables:
        elements.append(Paragraph("Clinical Gait Variables / 보행 임상 변수", heading_style))

        from app.services.normative_data import calculate_age, get_clinical_variable_assessment

        age = 0
        gender = patient_data.get("gender", "M") if patient_data else "M"
        if patient_data and patient_data.get("birth_date"):
            age = calculate_age(patient_data["birth_date"])

        cv_rows = [["Variable / 변수", "Value / 값", "Normal Range / 정상 범위", "Status / 평가"]]
        cv_status_colors = []  # row index -> color

        cv_items = [
            ("stride_length", "Stride Length / 보폭", lambda v: f"{v.get('value', '-')} m"),
            ("cadence", "Cadence / 분당 걸음수", lambda v: f"{v.get('value', '-')} steps/min"),
            ("step_time", "Step Time / 스텝 시간", lambda v: f"{v.get('mean', '-')} s"),
            ("step_time_asymmetry", "Asymmetry / 좌우 비대칭", lambda v: f"{v.get('value', '-')} %"),
            ("double_support", "Double Support / 이중지지기", lambda v: f"{v.get('value', '-')} %"),
            ("swing_stance_ratio", "Swing/Stance / 유각/입각", lambda v: f"{v.get('swing_pct', '-')}% / {v.get('stance_pct', '-')}%"),
            ("arm_swing", "Arm Swing Asym. / 팔 비대칭", lambda v: f"{v.get('asymmetry_index', '-')} %"),
            ("stride_regularity", "Regularity / 보행 규칙성", lambda v: f"{v.get('value', '-')}"),
            ("trunk_inclination", "Trunk Incl. / 체간 경사", lambda v: f"{v.get('angle', v.get('mean', '-'))}°"),
        ]

        norm_var_map = {
            "stride_length": ("stride_length", lambda v: v.get("value", 0)),
            "cadence": ("cadence", lambda v: v.get("value", 0)),
            "step_time": ("step_time", lambda v: v.get("mean", 0)),
            "double_support": ("double_support", lambda v: v.get("value", 0)),
            "swing_stance_ratio": ("swing_pct", lambda v: v.get("swing_pct", 0)),
        }

        for key, label, fmt_fn in cv_items:
            cv_val = clinical_variables.get(key)
            if not cv_val:
                continue

            value_str = fmt_fn(cv_val)
            range_str = "-"
            status_str = "-"
            status_color = colors.white

            if key in norm_var_map:
                norm_key, val_fn = norm_var_map[key]
                val = val_fn(cv_val)
                if val > 0 and age > 0:
                    assess = get_clinical_variable_assessment(norm_key, val, age, gender)
                    if assess and assess.get("normative"):
                        n = assess["normative"]
                        range_str = f"{n['range_low']} - {n['range_high']}"
                        status_str = assess.get("comparison_label", "-")
                        cmp = assess.get("comparison", "")
                        if cmp == "normal":
                            status_color = colors.Color(0.85, 0.95, 0.85)
                        elif cmp == "below_average":
                            status_color = colors.Color(1.0, 0.95, 0.8)
                        else:
                            status_color = colors.Color(1.0, 0.85, 0.85)
            elif key == "step_time_asymmetry":
                v = cv_val.get("value", 0)
                range_str = "< 10%"
                if v < 10:
                    status_str = "정상"
                    status_color = colors.Color(0.85, 0.95, 0.85)
                elif v < 20:
                    status_str = "경도 비대칭"
                    status_color = colors.Color(1.0, 0.95, 0.8)
                else:
                    status_str = "비대칭"
                    status_color = colors.Color(1.0, 0.85, 0.85)
            elif key == "stride_regularity":
                v = cv_val.get("value", 0)
                range_str = "> 0.7"
                if v >= 0.7:
                    status_str = "규칙적"
                    status_color = colors.Color(0.85, 0.95, 0.85)
                elif v >= 0.5:
                    status_str = "다소 불규칙"
                    status_color = colors.Color(1.0, 0.95, 0.8)
                else:
                    status_str = "불규칙"
                    status_color = colors.Color(1.0, 0.85, 0.85)

            cv_rows.append([label, value_str, range_str, status_str])
            cv_status_colors.append(status_color)

        if len(cv_rows) > 1:
            cv_table = Table(cv_rows, colWidths=[140, 90, 100, 80])
            style_cmds = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.2, 0.3, 0.5)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.Color(0.95, 0.95, 0.95), colors.white]),
            ]
            # 평가 열 색상
            for idx, sc in enumerate(cv_status_colors):
                style_cmds.append(('BACKGROUND', (3, idx + 1), (3, idx + 1), sc))
            cv_table.setStyle(TableStyle(style_cmds))
            elements.append(cv_table)
            elements.append(Spacer(1, 20))

    # ========== 추이 차트 ==========
    if len(all_tests) >= 2:
        elements.append(Paragraph("Trend Charts / 변화 추이", heading_style))

        # 보행 속도 차트
        speed_chart = create_speed_chart(all_tests)
        elements.append(speed_chart)
        elements.append(Spacer(1, 10))

        # 보행 시간 차트
        time_chart = create_time_chart(all_tests)
        elements.append(time_chart)
        elements.append(Spacer(1, 20))

    # ========== 이전 검사와 비교 ==========
    if len(all_tests) > 1:
        elements.append(Paragraph("Comparison / 이전 검사 비교", heading_style))

        current_idx = next((i for i, t in enumerate(all_tests) if t["id"] == test_data["id"]), -1)

        if current_idx > 0:
            previous_test = all_tests[current_idx - 1]
            prev_speed = previous_test.get("walk_speed_mps", 0)
            prev_time = previous_test.get("walk_time_seconds", 0)
            speed_diff = walk_speed - prev_speed
            time_diff = walk_time - prev_time

            if speed_diff > 0.05:
                comparison_msg = "Speed IMPROVED / 속도 향상 - Fall risk may have DECREASED / 낙상 위험 감소 추정"
                comparison_color = colors.HexColor('#059669')
            elif speed_diff < -0.05:
                comparison_msg = "Speed DECREASED / 속도 감소 - Fall risk may have INCREASED / 낙상 위험 증가 추정"
                comparison_color = colors.HexColor('#dc2626')
            else:
                comparison_msg = "Speed STABLE / 속도 유지 - No significant change / 큰 변화 없음"
                comparison_color = colors.HexColor('#d97706')

            comparison_info = [
                ["", "Previous / 이전", "Current / 현재", "Change / 변화"],
                ["Speed / 속도", f"{prev_speed:.2f} m/s", f"{walk_speed:.2f} m/s", f"{speed_diff:+.2f} m/s"],
                ["Time / 시간", f"{prev_time:.2f} s", f"{walk_time:.2f} s", f"{time_diff:+.2f} s"],
            ]

            comp_table = Table(comparison_info, colWidths=[40*mm, 45*mm, 45*mm, 40*mm])
            comp_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ]))
            elements.append(comp_table)
            elements.append(Spacer(1, 10))

            elements.append(Paragraph(
                comparison_msg,
                ParagraphStyle('Comparison', parent=styles['Normal'],
                             fontSize=11, textColor=comparison_color,
                             fontName=FONT_BOLD)
            ))
            elements.append(Spacer(1, 20))

    # ========== 히스토리 테이블 ==========
    if len(all_tests) > 1:
        elements.append(Paragraph("Test History / 검사 이력", heading_style))

        history_data = [["#", "Date / 날짜", "Time / 시간", "Speed / 속도", "Score / 점수"]]
        for i, t in enumerate(all_tests[-10:]):
            t_date = t.get("test_date", "N/A")
            if isinstance(t_date, str) and "T" in t_date:
                t_date = t_date.split("T")[0]
            t_speed = t.get("walk_speed_mps", 0)
            t_time = t.get("walk_time_seconds", 0)
            t_risk = get_fall_risk_assessment(t_speed, t_time)
            history_data.append([
                str(i + 1),
                t_date,
                f"{t_time:.2f}s",
                f"{t_speed:.2f}m/s",
                str(t_risk["score"])
            ])

        history_table = Table(history_data, colWidths=[15*mm, 45*mm, 35*mm, 40*mm, 35*mm])
        history_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(history_table)

    # ========== 푸터 ==========
    elements.append(Spacer(1, 40))
    if template.language in ("en", "bilingual"):
        elements.append(Paragraph(
            template.footer_text,
            ParagraphStyle('Footer', parent=styles['Normal'],
                          fontSize=8, textColor=colors.grey, alignment=1)
        ))
    if template.language in ("ko", "bilingual"):
        elements.append(Paragraph(
            template.footer_text_ko,
            ParagraphStyle('FooterKo', parent=styles['Normal'],
                          fontSize=8, textColor=colors.grey, alignment=1)
        ))

    doc.build(elements)
    return temp_path


def generate_tug_pdf(
    test_data: Dict,
    patient_data: Dict,
    all_tests: List[Dict]
) -> str:
    """TUG 검사 PDF 리포트 생성"""
    _register_korean_font()
    import json

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_path = temp_file.name
    temp_file.close()

    doc = SimpleDocTemplate(
        temp_path,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    styles = getSampleStyleSheet()
    for sn in styles.byName:
        styles[sn].fontName = FONT_NAME
    styles['Heading1'].fontName = FONT_BOLD
    styles['Heading2'].fontName = FONT_BOLD

    title_style = ParagraphStyle(
        'TUGTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=20,
        alignment=1,
        textColor=colors.HexColor('#065f46')
    )

    subtitle_style = ParagraphStyle(
        'TUGSubTitle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=1,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=30
    )

    heading_style = ParagraphStyle(
        'TUGHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#059669')
    )

    elements = []

    # ========== Header ==========
    elements.append(Paragraph("Timed Up and Go Test Report", title_style))
    elements.append(Paragraph("TUG 검사 결과 리포트", subtitle_style))

    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ParagraphStyle('Date', parent=styles['Normal'], alignment=2, textColor=colors.grey, fontSize=9)
    ))
    elements.append(Spacer(1, 15))

    # ========== Patient Info ==========
    elements.append(Paragraph("Patient Information / 환자 정보", heading_style))

    patient_info = [
        ["Name / 이름", patient_data.get("name", "N/A")],
        ["Patient No. / 환자번호", patient_data.get("patient_number", "N/A")],
        ["Gender / 성별", "Male / 남" if patient_data.get("gender") == "M" else "Female / 여"],
        ["Birth Date / 생년월일", patient_data.get("birth_date", "N/A")],
        ["Height / 신장", f"{patient_data.get('height_cm', 'N/A')} cm"],
        ["Diagnosis / 진단명", patient_data.get("diagnosis", "N/A") or "-"],
    ]

    patient_table = Table(patient_info, colWidths=[70*mm, 100*mm])
    patient_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
        ('FONTNAME', (0, 0), (0, -1), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(patient_table)
    elements.append(Spacer(1, 20))

    # Parse analysis data
    analysis = test_data.get("analysis_data", {})
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except:
            analysis = {}

    # ========== TUG Total Time & Assessment ==========
    elements.append(Paragraph("TUG Test Results / TUG 검사 결과", heading_style))

    total_time = test_data.get("walk_time_seconds", 0)
    assessment = analysis.get("assessment", "")

    assessment_labels = {
        "normal": ("Normal / 정상", colors.HexColor('#22c55e'), colors.HexColor('#dcfce7')),
        "good": ("Good / 양호", colors.HexColor('#3b82f6'), colors.HexColor('#dbeafe')),
        "caution": ("Caution / 주의", colors.HexColor('#f97316'), colors.HexColor('#ffedd5')),
        "risk": ("Fall Risk / 낙상 위험", colors.HexColor('#ef4444'), colors.HexColor('#fee2e2')),
    }
    label, score_color, bg_color = assessment_labels.get(assessment, ("N/A", colors.grey, colors.HexColor('#f3f4f6')))

    test_date = test_data.get("test_date", "N/A")
    if isinstance(test_date, str) and "T" in test_date:
        test_date = test_date.split("T")[0]

    result_info = [
        ["Test Date / 검사일", test_date],
        ["Total Time / 총 소요 시간", f"{total_time:.2f} seconds"],
        ["Assessment / 평가", label],
    ]

    result_table = Table(result_info, colWidths=[70*mm, 100*mm])
    result_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('BACKGROUND', (0, 0), (0, -1), bg_color),
        ('TEXTCOLOR', (0, 0), (0, -1), score_color),
        ('FONTNAME', (0, 0), (0, -1), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTSIZE', (1, 2), (1, 2), 12),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, score_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(result_table)
    elements.append(Spacer(1, 20))

    # ========== 5-Phase Durations Table ==========
    phases = analysis.get("phases", {})
    if phases:
        elements.append(Paragraph("Phase Durations / 단계별 소요 시간", heading_style))

        phase_labels = {
            "stand_up": "Stand Up / 일어서기",
            "walk_out": "Walk Out / 걷기(나감)",
            "turn": "Turn / 돌아서기",
            "walk_back": "Walk Back / 걷기(돌아옴)",
            "sit_down": "Sit Down / 앉기",
        }

        phase_data = [["Phase / 단계", "Duration / 소요 시간 (s)", "Start / 시작 (s)", "End / 종료 (s)"]]
        for phase_key in ["stand_up", "walk_out", "turn", "walk_back", "sit_down"]:
            p = phases.get(phase_key, {})
            if isinstance(p, dict):
                duration = p.get("duration", 0)
                start = p.get("start_time", 0)
                end = p.get("end_time", 0)
                phase_data.append([
                    phase_labels.get(phase_key, phase_key),
                    f"{duration:.2f}",
                    f"{start:.2f}",
                    f"{end:.2f}"
                ])

        if len(phase_data) > 1:
            phase_table = Table(phase_data, colWidths=[55*mm, 40*mm, 35*mm, 35*mm])
            phase_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#064e3b')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ]))
            elements.append(phase_table)
            elements.append(Spacer(1, 20))

    # ========== Stand Up / Sit Down Analysis ==========
    stand_up = analysis.get("stand_up", {})
    sit_down = analysis.get("sit_down", {})

    if stand_up or sit_down:
        elements.append(Paragraph("Stand Up & Sit Down Analysis / 기립 및 착석 분석", heading_style))

        transfer_data = [["Metric / 항목", "Stand Up / 기립", "Sit Down / 착석"]]

        su_duration = stand_up.get("duration", 0) if stand_up else 0
        sd_duration = sit_down.get("duration", 0) if sit_down else 0
        transfer_data.append(["Duration / 소요 시간", f"{su_duration:.2f}s", f"{sd_duration:.2f}s"])

        su_used_hands = stand_up.get("used_hands", False) if stand_up else False
        sd_used_hands = sit_down.get("used_hands", False) if sit_down else False
        transfer_data.append([
            "Hand Support / 손 사용",
            "Yes / 사용" if su_used_hands else "No / 미사용",
            "Yes / 사용" if sd_used_hands else "No / 미사용"
        ])

        su_smoothness = stand_up.get("smoothness", "-") if stand_up else "-"
        sd_smoothness = sit_down.get("smoothness", "-") if sit_down else "-"
        transfer_data.append(["Smoothness / 부드러움", str(su_smoothness), str(sd_smoothness)])

        transfer_table = Table(transfer_data, colWidths=[60*mm, 55*mm, 55*mm])
        transfer_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(transfer_table)
        elements.append(Spacer(1, 20))

    # ========== Gait Pattern / Tilt Analysis ==========
    gait_pattern = analysis.get("gait_pattern", {})
    if gait_pattern:
        elements.append(Paragraph("Gait Pattern Analysis / 보행 패턴 분석", heading_style))

        shoulder_avg = gait_pattern.get("shoulder_tilt_avg", 0)
        shoulder_max = gait_pattern.get("shoulder_tilt_max", 0)
        shoulder_dir = gait_pattern.get("shoulder_tilt_direction", "-")
        hip_avg = gait_pattern.get("hip_tilt_avg", 0)
        hip_max = gait_pattern.get("hip_tilt_max", 0)
        hip_dir = gait_pattern.get("hip_tilt_direction", "-")
        gait_assessment = gait_pattern.get("assessment", "-")

        if gait_assessment == "정상 보행 패턴":
            pattern_color = colors.HexColor('#22c55e')
            pattern_bg = colors.HexColor('#dcfce7')
        else:
            pattern_color = colors.HexColor('#f97316')
            pattern_bg = colors.HexColor('#ffedd5')

        pattern_info = [
            ["Assessment / 종합 평가", gait_assessment],
            ["Shoulder Tilt Avg / 어깨 기울기 (평균)", f"{shoulder_avg:+.1f}"],
            ["Shoulder Tilt Max / 어깨 기울기 (최대)", f"{shoulder_max:.1f}"],
            ["Shoulder Status / 어깨 상태", shoulder_dir],
            ["Hip Tilt Avg / 골반 기울기 (평균)", f"{hip_avg:+.1f}"],
            ["Hip Tilt Max / 골반 기울기 (최대)", f"{hip_max:.1f}"],
            ["Hip Status / 골반 상태", hip_dir],
        ]

        pattern_table = Table(pattern_info, colWidths=[85*mm, 85*mm])
        pattern_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('BACKGROUND', (0, 0), (0, -1), pattern_bg),
            ('BACKGROUND', (0, 0), (-1, 0), pattern_bg),
            ('TEXTCOLOR', (0, 0), (0, -1), pattern_color),
            ('TEXTCOLOR', (1, 0), (1, 0), pattern_color),
            ('FONTNAME', (0, 0), (0, -1), FONT_BOLD),
            ('FONTNAME', (1, 0), (1, 0), FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, pattern_color),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(pattern_table)
        elements.append(Spacer(1, 20))

    # ========== Disease Profile ==========
    disease_profile = analysis.get("disease_profile_display", "")
    if disease_profile and disease_profile != "기본":
        elements.append(Paragraph("Disease Profile / 질환 프로파일", heading_style))
        elements.append(Paragraph(
            f"Applied Profile: {disease_profile}",
            ParagraphStyle('Profile', parent=styles['Normal'], fontSize=11,
                         textColor=colors.HexColor('#374151'))
        ))
        elements.append(Spacer(1, 20))

    # ========== Notes ==========
    notes = test_data.get("notes", "")
    if notes:
        elements.append(Paragraph("Notes / 메모", heading_style))
        elements.append(Paragraph(notes, ParagraphStyle(
            'Notes',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4b5563'),
            backColor=colors.HexColor('#f9fafb'),
            borderPadding=10,
            borderColor=colors.HexColor('#e5e7eb'),
            borderWidth=1
        )))
        elements.append(Spacer(1, 20))

    # ========== TUG History ==========
    tug_tests = [t for t in all_tests if t.get("test_type") == "TUG"]
    if len(tug_tests) > 1:
        elements.append(Paragraph("TUG Test History / TUG 검사 이력", heading_style))

        history_data = [["#", "Date / 날짜", "Time / 시간 (s)", "Assessment / 평가"]]
        for i, t in enumerate(tug_tests[-10:]):
            t_date = t.get("test_date", "N/A")
            if isinstance(t_date, str) and "T" in t_date:
                t_date = t_date.split("T")[0]
            t_time = t.get("walk_time_seconds", 0)
            t_analysis = t.get("analysis_data", {})
            if isinstance(t_analysis, str):
                try:
                    t_analysis = json.loads(t_analysis)
                except:
                    t_analysis = {}
            t_assess = t_analysis.get("assessment", "")
            t_label = assessment_labels.get(t_assess, ("N/A",))[0]
            history_data.append([
                str(i + 1),
                t_date,
                f"{t_time:.2f}",
                t_label
            ])

        history_table = Table(history_data, colWidths=[15*mm, 50*mm, 45*mm, 60*mm])
        history_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#064e3b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(history_table)

    # ========== TUG Reference Guide ==========
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("TUG Assessment Guide / TUG 검사 기준", heading_style))

    guide_data = [
        ["< 10s", "Normal / 정상", "10-20s", "Good / 양호"],
        ["20-30s", "Caution / 주의", "> 30s", "Fall Risk / 낙상 위험"],
    ]
    guide_table = Table(guide_data, colWidths=[25*mm, 60*mm, 25*mm, 60*mm])
    guide_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor('#22c55e')),
        ('TEXTCOLOR', (2, 0), (2, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 1), (0, 1), colors.HexColor('#f97316')),
        ('TEXTCOLOR', (2, 1), (2, 1), colors.HexColor('#ef4444')),
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    elements.append(guide_table)

    # ========== Footer ==========
    elements.append(Spacer(1, 40))
    elements.append(Paragraph(
        "This report is generated automatically for clinical reference only. "
        "Please consult with a healthcare professional for diagnosis and treatment.",
        ParagraphStyle('Footer', parent=styles['Normal'],
                      fontSize=8, textColor=colors.grey, alignment=1)
    ))
    elements.append(Paragraph(
        "본 리포트는 임상 참고용으로 자동 생성되었습니다. 진단 및 치료는 의료 전문가와 상담하세요.",
        ParagraphStyle('FooterKo', parent=styles['Normal'],
                      fontSize=8, textColor=colors.grey, alignment=1)
    ))

    doc.build(elements)
    return temp_path


def generate_bbs_pdf(
    test_data: Dict,
    patient_data: Dict,
    all_tests: List[Dict]
) -> str:
    """BBS (Berg Balance Scale) 검사 PDF 리포트 생성"""
    _register_korean_font()
    import json

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_path = temp_file.name
    temp_file.close()

    doc = SimpleDocTemplate(
        temp_path,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    styles = getSampleStyleSheet()
    for sn in styles.byName:
        styles[sn].fontName = FONT_NAME
    styles['Heading1'].fontName = FONT_BOLD
    styles['Heading2'].fontName = FONT_BOLD

    title_style = ParagraphStyle(
        'BBSTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=20,
        alignment=1,
        textColor=colors.HexColor('#6b21a8')
    )

    subtitle_style = ParagraphStyle(
        'BBSSubTitle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=1,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=30
    )

    heading_style = ParagraphStyle(
        'BBSHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#7c3aed')
    )

    elements = []

    # ========== Header ==========
    elements.append(Paragraph("Berg Balance Scale Report", title_style))
    elements.append(Paragraph("BBS 균형 검사 결과 리포트", subtitle_style))

    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ParagraphStyle('Date', parent=styles['Normal'], alignment=2, textColor=colors.grey, fontSize=9)
    ))
    elements.append(Spacer(1, 15))

    # ========== Patient Info ==========
    elements.append(Paragraph("Patient Information / 환자 정보", heading_style))

    patient_info = [
        ["Name / 이름", patient_data.get("name", "N/A")],
        ["Patient No. / 환자번호", patient_data.get("patient_number", "N/A")],
        ["Gender / 성별", "Male / 남" if patient_data.get("gender") == "M" else "Female / 여"],
        ["Birth Date / 생년월일", patient_data.get("birth_date", "N/A")],
        ["Height / 신장", f"{patient_data.get('height_cm', 'N/A')} cm"],
        ["Diagnosis / 진단명", patient_data.get("diagnosis", "N/A") or "-"],
    ]

    patient_table = Table(patient_info, colWidths=[70*mm, 100*mm])
    patient_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
        ('FONTNAME', (0, 0), (0, -1), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(patient_table)
    elements.append(Spacer(1, 20))

    # Parse analysis data
    analysis = test_data.get("analysis_data", {})
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except:
            analysis = {}

    # ========== Total Score & Assessment ==========
    elements.append(Paragraph("BBS Test Results / BBS 검사 결과", heading_style))

    total_score = analysis.get("total_score", test_data.get("walk_time_seconds", 0))
    total_score = int(total_score) if total_score else 0
    bbs_assessment = analysis.get("assessment", "")
    bbs_label = analysis.get("assessment_label", "")

    if total_score >= 41:
        score_color = colors.HexColor('#22c55e')
        bg_color = colors.HexColor('#dcfce7')
        badge = "Independent / 독립적"
    elif total_score >= 21:
        score_color = colors.HexColor('#eab308')
        bg_color = colors.HexColor('#fefce8')
        badge = "Walking with Assistance / 보조 보행"
    else:
        score_color = colors.HexColor('#ef4444')
        bg_color = colors.HexColor('#fee2e2')
        badge = "Wheelchair Bound / 휠체어 의존"

    test_date = test_data.get("test_date", "N/A")
    if isinstance(test_date, str) and "T" in test_date:
        test_date = test_date.split("T")[0]

    result_info = [
        ["Test Date / 검사일", test_date],
        ["Total Score / 총점", f"{total_score} / 56"],
        ["Assessment / 평가", badge],
    ]

    result_table = Table(result_info, colWidths=[70*mm, 100*mm])
    result_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('BACKGROUND', (0, 0), (0, -1), bg_color),
        ('TEXTCOLOR', (0, 0), (0, -1), score_color),
        ('FONTNAME', (0, 0), (0, -1), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTSIZE', (1, 1), (1, 1), 14),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, score_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(result_table)
    elements.append(Spacer(1, 20))

    # ========== 14-Item Score Table ==========
    scores = analysis.get("scores", {})
    if scores:
        elements.append(Paragraph("Item Scores / 항목별 점수", heading_style))

        item_labels = {
            "item1_sitting_to_standing": "1. Sitting to Standing / 앉은 자세에서 일어나기",
            "item2_standing_unsupported": "2. Standing Unsupported / 잡지 않고 서 있기",
            "item3_sitting_unsupported": "3. Sitting Unsupported / 등받이 없이 앉기",
            "item4_standing_to_sitting": "4. Standing to Sitting / 선자세에서 앉기",
            "item5_transfers": "5. Transfers / 의자 이동",
            "item6_standing_eyes_closed": "6. Standing Eyes Closed / 눈감고 서 있기",
            "item7_standing_feet_together": "7. Standing Feet Together / 발 붙이고 서 있기",
            "item8_reaching_forward": "8. Reaching Forward / 앞으로 팔 뻗기",
            "item9_pick_up_object": "9. Pick Up Object / 바닥 물건 줍기",
            "item10_turning_to_look_behind": "10. Turning to Look Behind / 뒤돌아보기",
            "item11_turn_360_degrees": "11. Turn 360 Degrees / 360도 회전",
            "item12_stool_stepping": "12. Stool Stepping / 발판 교대 올리기",
            "item13_standing_one_foot_front": "13. Tandem Standing / 일렬로 서기",
            "item14_standing_on_one_leg": "14. Standing on One Leg / 한 다리로 서기",
        }

        score_data = [["Item / 항목", "Score / 점수"]]
        for item_key in item_labels:
            score_val = scores.get(item_key, "N/A")
            if isinstance(score_val, dict):
                score_val = score_val.get("score", "N/A")
            score_data.append([item_labels[item_key], str(score_val) if score_val is not None else "N/A"])

        score_table = Table(score_data, colWidths=[140*mm, 30*mm])

        table_styles = [
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#581c87')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ]

        # Color-code individual scores
        for row_idx in range(1, len(score_data)):
            try:
                val = int(score_data[row_idx][1])
                if val <= 1:
                    table_styles.append(('BACKGROUND', (1, row_idx), (1, row_idx), colors.HexColor('#fee2e2')))
                    table_styles.append(('TEXTCOLOR', (1, row_idx), (1, row_idx), colors.HexColor('#dc2626')))
                elif val == 2:
                    table_styles.append(('BACKGROUND', (1, row_idx), (1, row_idx), colors.HexColor('#fef9c3')))
                    table_styles.append(('TEXTCOLOR', (1, row_idx), (1, row_idx), colors.HexColor('#ca8a04')))
                else:
                    table_styles.append(('BACKGROUND', (1, row_idx), (1, row_idx), colors.HexColor('#dcfce7')))
                    table_styles.append(('TEXTCOLOR', (1, row_idx), (1, row_idx), colors.HexColor('#16a34a')))
            except (ValueError, TypeError):
                pass

        score_table.setStyle(TableStyle(table_styles))
        elements.append(score_table)
        elements.append(Spacer(1, 15))

    # ========== Score Interpretation Guide ==========
    elements.append(Paragraph("Score Interpretation / 점수 해석", heading_style))

    interp_data = [
        ["Score Range / 점수 범위", "Level / 수준", "Description / 설명"],
        ["41-56", "Independent / 독립적", "Safe, independent ambulation / 안전한 독립 보행"],
        ["21-40", "Assisted / 보조 보행", "Needs assistance for mobility / 이동 시 도움 필요"],
        ["0-20", "Wheelchair / 휠체어 의존", "Wheelchair-bound / 휠체어 사용 필요"],
    ]
    interp_table = Table(interp_data, colWidths=[40*mm, 55*mm, 75*mm])
    interp_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ('TEXTCOLOR', (0, 1), (0, 1), colors.HexColor('#22c55e')),
        ('TEXTCOLOR', (0, 2), (0, 2), colors.HexColor('#eab308')),
        ('TEXTCOLOR', (0, 3), (0, 3), colors.HexColor('#ef4444')),
    ]))
    elements.append(interp_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(
        "Individual item scores: 0-1 = Poor (red), 2 = Fair (yellow), 3-4 = Good (green)",
        ParagraphStyle('ScoreGuide', parent=styles['Normal'],
                     fontSize=8, textColor=colors.grey)
    ))
    elements.append(Paragraph(
        "개별 항목 점수: 0-1 = 불량 (적색), 2 = 보통 (황색), 3-4 = 양호 (녹색)",
        ParagraphStyle('ScoreGuideKo', parent=styles['Normal'],
                     fontSize=8, textColor=colors.grey)
    ))

    # ========== Notes ==========
    bbs_notes = analysis.get("notes", "") or test_data.get("notes", "")
    if bbs_notes:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Notes / 메모", heading_style))
        elements.append(Paragraph(bbs_notes, ParagraphStyle(
            'Notes',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4b5563'),
            backColor=colors.HexColor('#f9fafb'),
            borderPadding=10,
            borderColor=colors.HexColor('#e5e7eb'),
            borderWidth=1
        )))

    # ========== BBS History ==========
    bbs_tests = [t for t in all_tests if t.get("test_type") == "BBS"]
    if len(bbs_tests) > 1:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("BBS Test History / BBS 검사 이력", heading_style))

        history_data = [["#", "Date / 날짜", "Score / 총점", "Assessment / 평가"]]
        for i, t in enumerate(bbs_tests[-10:]):
            t_date = t.get("test_date", "N/A")
            if isinstance(t_date, str) and "T" in t_date:
                t_date = t_date.split("T")[0]
            t_score = int(t.get("walk_time_seconds", 0))
            if t_score >= 41:
                t_assess = "Independent / 독립적"
            elif t_score >= 21:
                t_assess = "Assisted / 보조 보행"
            else:
                t_assess = "Wheelchair / 휠체어 의존"
            history_data.append([str(i + 1), t_date, f"{t_score}/56", t_assess])

        history_table = Table(history_data, colWidths=[15*mm, 50*mm, 40*mm, 65*mm])
        history_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#581c87')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(history_table)

    # ========== Footer ==========
    elements.append(Spacer(1, 40))
    elements.append(Paragraph(
        "This report is generated automatically for clinical reference only. "
        "Please consult with a healthcare professional for diagnosis and treatment.",
        ParagraphStyle('Footer', parent=styles['Normal'],
                      fontSize=8, textColor=colors.grey, alignment=1)
    ))
    elements.append(Paragraph(
        "본 리포트는 임상 참고용으로 자동 생성되었습니다. 진단 및 치료는 의료 전문가와 상담하세요.",
        ParagraphStyle('FooterKo', parent=styles['Normal'],
                      fontSize=8, textColor=colors.grey, alignment=1)
    ))

    doc.build(elements)
    return temp_path
