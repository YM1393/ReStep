"""
질환별 분석 변수 프로파일 시스템

iTUG_MediaPipe_Guide.docx 문서 기반으로 질환별 최적 파라미터와
추가 임상 변수를 정의합니다.

참고문헌:
- Ortega-Bastidas P et al. (2023) Sensors, 23(7):3426
- Zampieri C et al. (2010) J Neuroeng Rehabil, 7:32
- Abdollahi M et al. (2024) Bioengineering, 11(4):349
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict


@dataclass
class GaitProfile:
    """10MWT GaitAnalyzer 파라미터"""
    vel_threshold_pct: float = 27        # v8 최적화
    smooth_median_ws: int = 9
    smooth_avg_ws: int = 15
    vel_percentile: float = 82           # v8 최적화 (v7: 86)
    vel_end_factor: float = 1.7          # v8 최적화 (v7: 1.9)
    vel_iterative: bool = True
    inv_h_start_fraction: float = 0.60
    correction_factor_away: float = 2.4974   # v8 최적화 (v7: 2.4879)
    correction_factor_toward: float = 0.63


@dataclass
class TUGProfile:
    """TUG Analyzer 파라미터"""
    sitting_angle_threshold: float = 120
    standing_angle_threshold: float = 160
    upright_torso_threshold: float = 75
    hand_support_threshold: float = 0.15
    deviation_threshold: float = 5.0
    turn_deviation_threshold: float = 15.0
    min_facing_ratio: float = 0.03


@dataclass
class ClinicalFlags:
    """질환별 추가 측정 변수 플래그"""
    # TUG 변수
    measure_arm_swing: bool = False
    measure_turn_velocity: bool = False
    measure_trunk_angular_vel: bool = False
    measure_cadence: bool = False
    measure_joint_rom: bool = False
    measure_foot_clearance: bool = False
    measure_step_asymmetry: bool = False
    measure_sist_jerk: bool = False
    # 10MWT 보행 변수
    measure_step_time: bool = False
    measure_stride_time: bool = False
    measure_step_time_asymmetry: bool = False
    measure_double_support: bool = False
    measure_stride_regularity: bool = False
    measure_trunk_inclination: bool = False
    measure_swing_stance_ratio: bool = False


@dataclass
class DiseaseProfile:
    """질환별 분석 프로파일"""
    name: str
    display_name: str
    keywords: List[str] = field(default_factory=list)
    gait: GaitProfile = field(default_factory=GaitProfile)
    tug: TUGProfile = field(default_factory=TUGProfile)
    clinical_flags: ClinicalFlags = field(default_factory=ClinicalFlags)
    description: str = ""


# ============================================================
# 질환별 프로파일 정의
# ============================================================

DISEASE_PROFILES: Dict[str, DiseaseProfile] = {

    # 기본 (진단명 없음 또는 매칭 안 됨)
    "default": DiseaseProfile(
        name="default",
        display_name="기본",
        keywords=[],
        gait=GaitProfile(),
        tug=TUGProfile(),
        clinical_flags=ClinicalFlags(
            measure_cadence=True,
            measure_step_time=True,
            measure_stride_time=True,
            measure_step_time_asymmetry=True,
            measure_arm_swing=True,
            measure_foot_clearance=True,
            measure_double_support=True,
            measure_stride_regularity=True,
            measure_trunk_inclination=True,
            measure_swing_stance_ratio=True,
        ),
        description="기본 프로파일 (모든 보행 파라미터 측정)",
    ),

    # 파킨슨병: 서동, 소보행, 동결보행, 전방 굴곡, 진전
    # iTUG 연구의 32.5% 차지 (Ortega-Bastidas 2023)
    "parkinsons": DiseaseProfile(
        name="parkinsons",
        display_name="파킨슨병",
        keywords=["파킨슨", "parkinson", "PD", "진전마비"],
        gait=GaitProfile(
            vel_threshold_pct=15,     # 서동(bradykinesia)으로 느린 가속
            smooth_median_ws=13,      # 진전 노이즈 제거
            smooth_avg_ws=21,
            vel_percentile=84,
            vel_end_factor=1.5,       # 급격한 정지 패턴
        ),
        tug=TUGProfile(
            sitting_angle_threshold=110,   # 굴곡 자세로 앉음
            standing_angle_threshold=155,  # 불완전 신전
            upright_torso_threshold=60,    # 전방 굴곡 자세
            hand_support_threshold=0.18,
            deviation_threshold=4.0,       # 경직으로 측방 흔들림 적음 → 낮은 임계
            turn_deviation_threshold=12.0,
        ),
        clinical_flags=ClinicalFlags(
            measure_arm_swing=True,         # ★★★ 초기 PD 최민감 변수
            measure_turn_velocity=True,     # ★★★ H&Y 단계 상관
            measure_trunk_angular_vel=True, # ★★★ 낙상 예측
            measure_cadence=True,           # ★★☆ 보행 리듬 이상
            measure_foot_clearance=True,    # ★★☆ shuffling 반영
            measure_sist_jerk=True,         # ★★☆ 동작 부드러움
            # 10MWT
            measure_step_time=True,
            measure_stride_time=True,
            measure_step_time_asymmetry=True,
            measure_double_support=True,
            measure_stride_regularity=True,
            measure_trunk_inclination=True,
            measure_swing_stance_ratio=True,
        ),
        description="서동, 소보행, 동결보행, 전방 굴곡 자세. Arm swing velocity가 초기 PD 최민감 변수.",
    ),

    # 뇌졸중 / 편마비: 비대칭성이 핵심 특징
    "stroke": DiseaseProfile(
        name="stroke",
        display_name="뇌졸중",
        keywords=["뇌졸중", "stroke", "CVA", "뇌경색", "뇌출혈", "반신마비", "편마비", "hemiplegia"],
        gait=GaitProfile(
            vel_threshold_pct=18,     # 느린 가속
            smooth_median_ws=11,      # 보행 변동성
            smooth_avg_ws=19,
            vel_percentile=82,        # 불안정한 최대 속도
            vel_end_factor=2.2,       # 느린 감속
        ),
        tug=TUGProfile(
            sitting_angle_threshold=115,
            standing_angle_threshold=150,  # 마비측 불완전 신전
            upright_torso_threshold=65,    # 보상적 체간 기울임
            hand_support_threshold=0.20,   # 손 지지 빈도 높음
            deviation_threshold=8.0,       # 편마비로 기울기 큼
            turn_deviation_threshold=18.0,
        ),
        clinical_flags=ClinicalFlags(
            measure_arm_swing=True,         # 비대칭 분석
            measure_turn_velocity=True,     # ★★★ 회전 31% 지연
            measure_trunk_angular_vel=True, # ★★☆ 기립 시 20% 저하
            measure_step_asymmetry=True,    # ★★★ ML pelvic displacement
            measure_sist_jerk=True,
            # 10MWT
            measure_step_time=True,
            measure_stride_time=True,
            measure_step_time_asymmetry=True,
            measure_double_support=True,
            measure_stride_regularity=True,
            measure_swing_stance_ratio=True,
        ),
        description="편마비 비대칭성이 핵심. ML pelvic displacement가 낙상 최강 예측인자 (IQR-OR=5.28-10.29).",
    ),

    # 다발성 경화증: 실조 보행, 피로 의존적, 균형 장애
    "ms": DiseaseProfile(
        name="ms",
        display_name="다발성 경화증",
        keywords=["다발성 경화증", "다발성경화증", "multiple sclerosis", "MS", "탈수초"],
        gait=GaitProfile(
            vel_threshold_pct=20,
            smooth_median_ws=11,
            smooth_avg_ws=17,
            vel_percentile=84,
            vel_end_factor=2.0,
        ),
        tug=TUGProfile(
            sitting_angle_threshold=118,
            standing_angle_threshold=155,
            upright_torso_threshold=70,
            hand_support_threshold=0.17,
            deviation_threshold=7.0,       # 실조로 체간 흔들림 큼
            turn_deviation_threshold=18.0,  # 회전 시 불안정
        ),
        clinical_flags=ClinicalFlags(
            measure_trunk_angular_vel=True,
            measure_cadence=True,
            measure_joint_rom=True,
            # 10MWT
            measure_step_time=True,
            measure_stride_time=True,
            measure_stride_regularity=True,
        ),
        description="실조 보행, 피로 의존적 변화. 회전 구간에서 특히 불안정.",
    ),

    # 척수 손상: 경직 보행, 보조기구 사용, 매우 느린 속도
    "sci": DiseaseProfile(
        name="sci",
        display_name="척수 손상",
        keywords=["척수 손상", "척수손상", "spinal cord", "SCI", "척수염", "하반신마비"],
        gait=GaitProfile(
            vel_threshold_pct=15,
            smooth_median_ws=13,
            smooth_avg_ws=21,
            vel_percentile=80,
            vel_end_factor=2.5,       # 매우 느린 감속
        ),
        tug=TUGProfile(
            sitting_angle_threshold=125,   # 경직으로 깊이 못 앉음
            standing_angle_threshold=145,  # 불완전 신전
            upright_torso_threshold=65,
            hand_support_threshold=0.25,   # 보조기구 사용 빈번
            deviation_threshold=6.0,
            turn_deviation_threshold=16.0,
        ),
        clinical_flags=ClinicalFlags(
            measure_joint_rom=True,
            measure_trunk_angular_vel=True,
            measure_step_asymmetry=True,
            # 10MWT
            measure_step_time=True,
            measure_stride_time=True,
            measure_step_time_asymmetry=True,
            measure_double_support=True,
            measure_trunk_inclination=True,
            measure_swing_stance_ratio=True,
        ),
        description="경직 보행, 보조기구 사용 빈번. 관절 ROM 제한이 특징.",
    ),

    # 뇌성마비: 구부정 자세, 경직, 다양한 패턴
    "cp": DiseaseProfile(
        name="cp",
        display_name="뇌성마비",
        keywords=["뇌성마비", "뇌성 마비", "cerebral palsy", "CP"],
        gait=GaitProfile(
            vel_threshold_pct=15,
            smooth_median_ws=13,
            smooth_avg_ws=21,
            vel_percentile=80,
            vel_end_factor=2.2,
        ),
        tug=TUGProfile(
            sitting_angle_threshold=110,   # 구부정 자세
            standing_angle_threshold=140,  # 경직으로 불완전 신전
            upright_torso_threshold=55,    # 심한 전방 굴곡
            hand_support_threshold=0.22,
            deviation_threshold=8.0,       # 높은 변동성
            turn_deviation_threshold=18.0,
        ),
        clinical_flags=ClinicalFlags(
            measure_joint_rom=True,
            measure_step_asymmetry=True,
            measure_trunk_angular_vel=True,
            # 10MWT
            measure_step_time=True,
            measure_stride_time=True,
            measure_step_time_asymmetry=True,
            measure_trunk_inclination=True,
            measure_swing_stance_ratio=True,
        ),
        description="구부정 자세(crouch gait), 경직, 불완전 신전. 과제 전환 예측 어려움.",
    ),

    # 슬관절 OA / TKA 후: 통증 회피 보행, 슬관절 ROM 감소
    "knee_oa": DiseaseProfile(
        name="knee_oa",
        display_name="슬관절 OA/TKA",
        keywords=["슬관절", "무릎 관절", "TKA", "TKR", "knee OA", "퇴행성 무릎", "인공슬관절",
                  "무릎 퇴행", "슬관절염"],
        gait=GaitProfile(
            vel_threshold_pct=20,
            vel_end_factor=1.9,
        ),
        tug=TUGProfile(
            sitting_angle_threshold=115,   # 슬관절 굴곡 제한
            standing_angle_threshold=150,  # 신전 부족
            upright_torso_threshold=70,
            hand_support_threshold=0.20,
        ),
        clinical_flags=ClinicalFlags(
            measure_joint_rom=True,         # ★★☆ 슬관절 ROM 핵심
            measure_turn_velocity=True,     # TKA 후 장기 추적
            measure_foot_clearance=True,
            # 10MWT
            measure_step_time=True,
            measure_double_support=True,
            measure_swing_stance_ratio=True,
        ),
        description="통증 회피 보상 보행. Knee ROM 감소와 heel strike 시 신전 부족이 특징.",
    ),

    # 고관절 OA / 골절 후: 고관절 ROM 감소, 기립 시간 증가
    "hip_oa": DiseaseProfile(
        name="hip_oa",
        display_name="고관절 OA/골절",
        keywords=["고관절", "THA", "THR", "hip OA", "대퇴골", "퇴행성 고관절", "인공고관절",
                  "고관절 골절", "대퇴경부"],
        gait=GaitProfile(
            vel_threshold_pct=20,
            vel_end_factor=1.9,
        ),
        tug=TUGProfile(
            sitting_angle_threshold=118,
            standing_angle_threshold=155,
            upright_torso_threshold=68,
            hand_support_threshold=0.20,
        ),
        clinical_flags=ClinicalFlags(
            measure_joint_rom=True,         # ★★☆ 고관절 ROM 핵심
            measure_trunk_angular_vel=True,
            measure_sist_jerk=True,
            # 10MWT
            measure_step_time=True,
            measure_double_support=True,
            measure_trunk_inclination=True,
        ),
        description="고관절 ROM 감소. THA 전 TUG<9.7s이면 조기 퇴원 4배 가능. MDC: 2.49s.",
    ),

    # 노인 낙상 위험군: 표준 TUG 정상이어도 iTUG로 감별 가능
    "fall_risk": DiseaseProfile(
        name="fall_risk",
        display_name="낙상 위험",
        keywords=["낙상", "fall risk", "낙상 위험", "균형 장애", "낙상위험"],
        gait=GaitProfile(
            vel_threshold_pct=20,
            smooth_median_ws=11,
            smooth_avg_ws=17,
            vel_percentile=84,
            vel_end_factor=2.0,
        ),
        tug=TUGProfile(
            sitting_angle_threshold=118,
            standing_angle_threshold=158,
            upright_torso_threshold=72,
            hand_support_threshold=0.18,
        ),
        clinical_flags=ClinicalFlags(
            measure_sist_jerk=True,         # ★★☆ 낙상군 jerk 증가
            measure_cadence=True,           # 평균 걸음 시간 증가
            measure_trunk_angular_vel=True, # SiSt amplitude
            measure_step_asymmetry=True,    # 대칭성 감소
            # 10MWT
            measure_step_time=True,
            measure_stride_time=True,
            measure_step_time_asymmetry=True,
            measure_double_support=True,
            measure_stride_regularity=True,
            measure_swing_stance_ratio=True,
        ),
        description="표준 TUG 정상인 노인에서도 iTUG로 낙상 위험 감별 가능. Cut-off: TUG>=12s.",
    ),
}


def resolve_profile(diagnosis: Optional[str]) -> DiseaseProfile:
    """환자 진단명에서 질환 프로파일을 매칭합니다.

    Args:
        diagnosis: 환자 진단명 텍스트 (한글/영문 혼합 가능)

    Returns:
        매칭된 DiseaseProfile. 매칭 실패 시 default 프로파일.
    """
    if not diagnosis:
        return DISEASE_PROFILES["default"]

    diagnosis_lower = diagnosis.lower().strip()

    for profile_key, profile in DISEASE_PROFILES.items():
        if profile_key == "default":
            continue
        for keyword in profile.keywords:
            if keyword.lower() in diagnosis_lower:
                return profile

    return DISEASE_PROFILES["default"]
