export interface User {
  id: string;
  username: string;
  name: string;
  role: 'admin' | 'therapist';
  is_approved: boolean;
}

export interface Patient {
  id: string;
  patient_number: string;
  name: string;
  gender: 'M' | 'F';
  birth_date: string;
  height_cm: number;
  diagnosis?: string;
  created_at: string;
}

export interface Therapist {
  id: string;
  username: string;
  name: string;
  role: string;
  is_approved: boolean;
  created_at: string;
}

export interface PatientCreate {
  patient_number: string;
  name: string;
  gender: 'M' | 'F';
  birth_date: string;
  height_cm: number;
  diagnosis?: string;
}

// 검사 유형
export type TestType = '10MWT' | 'TUG' | 'BBS';

export interface WalkTest {
  id: string;
  patient_id: string;
  test_date: string;
  test_type: TestType;
  walk_time_seconds: number;
  walk_speed_mps: number;
  video_url?: string;
  analysis_data?: AnalysisData | TUGAnalysisData | BBSAnalysisData;
  notes?: string;
  created_at: string;
}

export interface GaitPattern {
  shoulder_tilt_avg: number;
  shoulder_tilt_max: number;
  shoulder_tilt_direction: string;
  hip_tilt_avg: number;
  hip_tilt_max: number;
  hip_tilt_direction: string;
  assessment: string;
}

export interface MeasurementZone {
  start_distance_m: number;
  end_distance_m: number;
  measured_distance_m: number;
}

export interface AngleDataPoint {
  time: number;
  shoulder_tilt: number;
  hip_tilt: number;
}

export interface SideAngleDataPoint {
  time: number;
  knee_angle: number;
  left_knee_angle: number;
  right_knee_angle: number;
  hip_angle: number;
  left_hip_angle: number;
  right_hip_angle: number;
}

// 10MWT 임상 보행 변수
export interface ClinicalCadence {
  value: number;
  unit: string;
  total_steps: number;
}

export interface ClinicalStepTime {
  mean: number;
  cv: number;
  unit: string;
  left_mean?: number;
  right_mean?: number;
}

export interface ClinicalStrideTime {
  mean: number;
  cv: number;
  unit: string;
}

export interface ClinicalStepTimeAsymmetry {
  value: number;
  unit: string;
  left_mean?: number;
  right_mean?: number;
}

export interface ClinicalArmSwing {
  left_amplitude: number;
  right_amplitude: number;
  asymmetry_index: number;
  unit: string;
}

export interface ClinicalFootClearance {
  mean_clearance: number;
  min_clearance: number;
  unit: string;
}

export interface ClinicalDoubleSupport {
  value: number;
  unit: string;
}

export interface ClinicalStrideRegularity {
  value: number;
  stride_period?: number;
  unit: string;
}

export interface ClinicalTrunkInclination {
  mean: number;
  std: number;
  unit: string;
}

export interface ClinicalSwingStanceRatio {
  swing_pct: number;
  stance_pct: number;
  unit: string;
}

export interface ClinicalStrideLength {
  value: number;
  unit: string;
}

export interface ClinicalVariables {
  cadence?: ClinicalCadence;
  step_time?: ClinicalStepTime;
  stride_time?: ClinicalStrideTime;
  stride_length?: ClinicalStrideLength;
  step_time_asymmetry?: ClinicalStepTimeAsymmetry;
  arm_swing?: ClinicalArmSwing;
  foot_clearance?: ClinicalFootClearance;
  double_support?: ClinicalDoubleSupport;
  stride_regularity?: ClinicalStrideRegularity;
  trunk_inclination?: ClinicalTrunkInclination;
  swing_stance_ratio?: ClinicalSwingStanceRatio;
}

// 3D 포즈 프레임 (월드 좌표계)
export interface Pose3DFrame {
  time: number;
  landmarks: [number, number, number][];  // [x, y, z] 배열 (body landmarks 11-32)
}

// TUG 3D 포즈 프레임 (단계 정보 포함)
export interface TUGPose3DFrame extends Pose3DFrame {
  phase: string;  // 'stand_up' | 'walk_out' | 'turn' | 'walk_back' | 'sit_down' | 'unknown'
}

export interface AnalysisData {
  fps: number;
  total_frames: number;
  start_frame: number;
  end_frame: number;
  patient_height_cm: number;
  frames_analyzed: number;
  walking_direction?: string;
  measurement_zone?: MeasurementZone;
  gait_pattern?: GaitPattern;
  angle_data?: AngleDataPoint[];
  overlay_video_filename?: string;  // 포즈 오버레이 영상 파일명
  calibration_method?: 'proportional';
  disease_profile?: string;
  disease_profile_display?: string;
  clinical_variables?: ClinicalVariables;
  confidence_score?: ConfidenceScore;
  asymmetry_warnings?: AsymmetryWarning[];
  pose_3d_frames?: Pose3DFrame[];  // 3D 월드 랜드마크 데이터
  measurement_lines?: {
    start_y: number;
    finish_y: number;
    start_frame: number;
    finish_frame: number;
  };
}

// TUG 검사 관련 타입
export interface TUGPhase {
  duration: number;
  start_time: number;
  end_time: number;
}

export interface TUGPhases {
  stand_up: TUGPhase;
  walk_out: TUGPhase;
  turn: TUGPhase;
  walk_back: TUGPhase;
  sit_down: TUGPhase;
}

export type TUGAssessment = 'normal' | 'good' | 'caution' | 'risk';

// 기립/착석 분석 결과
export interface StandSitMetrics {
  duration: number;      // 소요 시간 (초)
  speed: number;         // 속도 (정규화된 높이/초)
  height_change?: number; // 높이 변화
  start_time: number;
  end_time: number;
  assessment: string;    // 평가 ("빠름", "보통", "느림" 등)
  used_hand_support?: boolean;  // 손으로 무릎을 짚고 일어났는지/앉았는지
}

// TUG 기울기 분석 (정면 영상)
export interface TiltAnalysis {
  shoulder_tilt_avg: number;
  shoulder_tilt_max: number;
  shoulder_tilt_direction: string;
  hip_tilt_avg: number;
  hip_tilt_max: number;
  hip_tilt_direction: string;
  assessment: string;
}

// TUG 단계별 캡처 프레임 정보
export interface PhaseFrameInfo {
  frame: string;           // base64 인코딩된 이미지
  time: number;            // 캡처 시점 (초)
  frame_number: number;    // 프레임 번호
  label: string;           // 단계 한글 레이블
  criteria: string;        // 감지 기준 요약
  description: string;     // 상세 설명
  key_points: string[];    // 주요 감지 포인트
  duration: number;        // 단계 지속 시간
}

// TUG 단계별 캡처 프레임 모음
export interface PhaseFrames {
  stand_up?: PhaseFrameInfo;
  walk_out?: PhaseFrameInfo;
  turn?: PhaseFrameInfo;
  walk_back?: PhaseFrameInfo;
  sit_down?: PhaseFrameInfo;
}

// 반응 시간 분석
export interface ReactionTimeData {
  reaction_time: number;        // 영상 시작~첫 움직임 (초)
  detection_method: string;     // 감지 방법
  confidence: number;           // 신뢰도 0-100
  first_movement_time: number;  // 첫 움직임 절대 시점
}

// 첫 걸음 시간 (파킨슨 지표)
export interface FirstStepData {
  time_to_first_step: number;   // 기립 완료~첫 걸음 (초)
  detection_method: string;
  hesitation_detected: boolean; // 2초 이상이면 보행 개시 지연
  confidence: number;
}

// 체중이동 분석 (정면 영상)
export interface WeightShiftData {
  lateral_sway_amplitude: number;  // 좌우 흔들림 폭
  lateral_sway_max: number;        // 최대 편향
  sway_frequency: number;          // 진동 주파수 (Hz)
  cop_trajectory: Array<{time: number; x: number}>;  // CoP 궤적
  standup_weight_shift: string;    // '균형' | '왼쪽 편향' | '오른쪽 편향'
  assessment: string;
}

// 자세 편향 캡처 (정면 영상)
export interface DeviationCapture {
  frame: string;               // base64 주석 이미지
  time: number;
  shoulder_angle: number;
  hip_angle: number;
  type: 'shoulder' | 'hip' | 'both';
  severity: 'mild' | 'moderate' | 'severe';
}

// 단계별 클립 정보
export interface PhaseClipInfo {
  clip_filename: string;
  start_time: number;
  end_time: number;
  duration: number;
  label: string;
  thumbnail?: string;          // base64 썸네일
}

export interface PhaseClips {
  stand_up?: PhaseClipInfo;
  walk_out?: PhaseClipInfo;
  turn?: PhaseClipInfo;
  walk_back?: PhaseClipInfo;
  sit_down?: PhaseClipInfo;
}

export interface TUGAnalysisData {
  test_type: 'TUG';
  total_time_seconds: number;
  walk_time_seconds: number;
  walk_speed_mps: number;
  assessment: TUGAssessment;
  phases: TUGPhases;
  fps: number;
  total_frames: number;
  frames_analyzed: number;
  patient_height_cm: number;

  // 포즈 오버레이 영상 파일명
  overlay_video_filename?: string;  // 기존 호환성 (측면)
  side_overlay_video_filename?: string;  // 측면 영상 오버레이
  front_overlay_video_filename?: string; // 정면 영상 오버레이
  front_video_filename?: string; // 정면 원본 영상 파일명

  // 기립/착석 분석 (측면 영상)
  stand_up?: StandSitMetrics;
  sit_down?: StandSitMetrics;

  // 기울기 분석 (정면 영상)
  tilt_analysis?: TiltAnalysis;

  // 단계별 캡처 프레임 및 검증 정보
  phase_frames?: PhaseFrames;

  // 단계 감지 신뢰도 (0-100)
  phase_confidence?: Record<string, number>;

  // 반응 시간 (측면 영상)
  reaction_time?: ReactionTimeData;

  // 첫 걸음 시간 (파킨슨 지표)
  first_step_time?: FirstStepData;

  // 체중이동 분석 (정면 영상)
  weight_shift?: WeightShiftData;

  // 자세 편향 캡처 (정면 영상)
  deviation_captures?: DeviationCapture[];

  // 단계별 클립
  phase_clips?: PhaseClips;

  // 기존 필드 (호환성)
  gait_pattern?: GaitPattern;
  angle_data?: AngleDataPoint[];
  side_angle_data?: SideAngleDataPoint[];

  // 3D 포즈 데이터
  pose_3d_frames?: TUGPose3DFrame[];        // 측면 영상 (전체 TUG 시퀀스)
  pose_3d_frames_front?: TUGPose3DFrame[];  // 정면 영상 (보조)
}

// ─── 실시간 TUG 타입 ───
export interface RealtimeTUGPhaseUpdate {
  type: 'phase_update';
  current_phase: string;
  phase_label: string;
  elapsed_time: number;
  leg_angle?: number;
  hip_height?: number;
}

export interface RealtimeTUGPhaseTransition {
  type: 'phase_transition';
  from_phase: string;
  to_phase: string;
  transition_time: number;
  current_phase: string;
  phase_label: string;
  elapsed_time: number;
  transitions: Array<{ phase: string; start: number; end?: number }>;
}

export interface RealtimeTUGTestResult {
  type: 'test_completed';
  test_id?: string;
  test_type: string;
  total_time_seconds: number;
  walk_speed_mps: number;
  assessment: TUGAssessment;
  phases: TUGPhases;
  pose_3d_frames?: TUGPose3DFrame[];
}

// BBS (Berg Balance Scale) 검사 관련 타입
export type BBSAssessment = 'wheelchair_bound' | 'walking_with_assistance' | 'independent';

// BBS 14개 항목 점수 (각 0-4점)
export interface BBSItemScores {
  item1_sitting_to_standing: number;      // 앉은 자세에서 일어나기
  item2_standing_unsupported: number;     // 잡지 않고 서 있기
  item3_sitting_unsupported: number;      // 등받이에 기대지 않고 앉기
  item4_standing_to_sitting: number;      // 선자세에서 앉기
  item5_transfers: number;                // 의자에서 의자로 이동하기
  item6_standing_eyes_closed: number;     // 두눈을 감고 서 있기
  item7_standing_feet_together: number;   // 두발을 붙이고 서 있기
  item8_reaching_forward: number;         // 선자세에서 앞으로 팔 뻗기
  item9_pick_up_object: number;           // 바닥에서 물건 줍기
  item10_turning_to_look_behind: number;  // 뒤돌아보기
  item11_turn_360_degrees: number;        // 제자리에서 360도 회전
  item12_stool_stepping: number;          // 발판 위에 발 교대로 올리기
  item13_standing_one_foot_front: number; // 일렬로 서기 (탄뎀)
  item14_standing_on_one_leg: number;     // 한 다리로 서기
}

// BBS 항목 정보 (레이블, 설명, 채점 기준)
export interface BBSItemInfo {
  id: keyof BBSItemScores;
  label: string;
  description: string;
  criteria: string[];  // 0-4점 각각의 기준
}

export interface BBSAnalysisData {
  test_type: 'BBS';
  scores: BBSItemScores;
  total_score: number;           // 총점 (0-56)
  assessment: BBSAssessment;     // 평가 결과
  assessment_label: string;      // 한글 평가 레이블
  notes?: string;                // 추가 메모
  gait_pattern?: GaitPattern;    // 호환성 (사용되지 않음)
  angle_data?: AngleDataPoint[]; // 호환성 (사용되지 않음)
}

// BBS AI 분석 결과 항목
export interface BBSAIScoreItem {
  score: number;
  confidence: number;
  message: string;
  details: Record<string, any>;
}

export interface AnalysisStatus {
  status: 'processing' | 'completed' | 'error';
  progress: number;
  message: string;
  current_frame?: string;  // base64 encoded frame
  current_phase?: string;  // TUG 단계 코드 (stand_up, walk_out, turn, walk_back, sit_down)
  current_phase_label?: string;  // TUG 단계 한글 레이블 (일어서기, 걷기 등)
  result?: {
    test_id?: string;
    test_type?: TestType;
    walk_time_seconds?: number;
    walk_speed_mps?: number;
    // BBS AI 분석 결과
    ai_scores?: Partial<Record<keyof BBSItemScores, BBSAIScoreItem>>;
    video_duration?: number;
    total_frames?: number;
    video_path?: string;
    overlay_video_url?: string;
  };
}

// WebSocket message types
export interface WSProgressMessage {
  type: 'progress' | 'completed' | 'error';
  file_id: string;
  progress: number;
  message: string;
  result?: AnalysisStatus['result'];
}

// 신뢰도 점수
export interface ConfidenceScore {
  score: number;
  level: 'high' | 'medium' | 'low' | 'very_low';
  label: string;
  details: {
    pose_detection_rate: number;
    walk_duration_score: number;
    walk_time_score: number;
    walk_speed_score: number;
  };
}

// 보행 비대칭 경고
export interface AsymmetryWarning {
  type: string;
  severity: 'mild' | 'moderate' | 'severe';
  label: string;
  value: number;
  unit: string;
  description: string;
  threshold: number;
}

// 정상 범위 비교
export interface NormativeRange {
  mean: number;
  sd: number;
  range_low: number;
  range_high: number;
  age_group: string;
  gender: string;
  reference: string;
}

export interface ClinicalInterpretation {
  category: string;
  label: string;
  met: boolean;
}

export interface SpeedAssessment {
  speed_mps: number;
  normative?: NormativeRange;
  z_score?: number;
  comparison?: string;
  comparison_label?: string;
  percent_of_normal?: number;
  clinical_interpretation: ClinicalInterpretation[];
}

// 반복 측정 통계
export interface StatSummary {
  mean: number;
  std: number;
  min: number;
  max: number;
}

export interface TimeAssessment {
  time_seconds: number;
  normative?: NormativeRange;
  z_score?: number;
  comparison?: string;
  comparison_label?: string;
  percent_of_normal?: number;
  clinical_interpretation: ClinicalInterpretation[];
}

export interface PatientStats {
  test_count: number;
  test_type: string;
  walk_time: StatSummary;
  walk_speed: StatSummary;
  normative?: SpeedAssessment;
  normative_time?: TimeAssessment;
}

// 임상 변수 연령/성별 정상 범위 평가
export interface ClinicalVariableAssessment {
  value: number;
  normative?: {
    mean: number;
    sd: number;
    range_low: number;
    range_high: number;
    age_group: string;
    gender: string;
  };
  z_score?: number;
  comparison: string;
  comparison_label: string;
  percent_of_normal?: number;
  label: string;
  unit: string;
}

export interface ClinicalNormativeResponse {
  [variable: string]: ClinicalVariableAssessment;
}

// 임상 변수 추세
export interface ClinicalTrendDataPoint {
  test_id: string;
  date: string;
  walk_speed?: number;
  walk_time?: number;
  stride_length?: number;
  cadence?: number;
  step_time?: number;
  step_time_asymmetry?: number;
  double_support?: number;
  swing_pct?: number;
  arm_swing_asymmetry?: number;
  stride_regularity?: number;
  trunk_inclination?: number;
}

export interface ClinicalTrendsResponse {
  data_points: ClinicalTrendDataPoint[];
  variables: string[];
  total_tests: number;
  tests_with_clinical_data: number;
}

// 상관관계 분석
export interface CorrelationPair {
  var1: string;
  var2: string;
  r: number;
  p_value?: number;
  label: string;
}

export interface SpeedCorrelation {
  variable: string;
  r: number;
  label: string;
}

export interface ClinicalCorrelationsResponse {
  variables: string[];
  variable_labels: Record<string, string>;
  correlation_matrix: number[][];
  significant_correlations: CorrelationPair[];
  scatter_data: Record<string, { x: number; y: number }[]>;
  speed_correlations: SpeedCorrelation[];
  n_tests: number;
  sufficient_data: boolean;
  message?: string;
}

export interface ComparisonResult {
  current_test: WalkTest;
  previous_test?: WalkTest;
  comparison_message: string;
  speed_difference?: number;
  time_difference?: number;
}

export interface VideoInfo {
  filename: string;
  size_bytes: number;
  size_mb: number;
  video_url: string;
}

// 환자 태그
export interface PatientTag {
  id: string;
  name: string;
  color: string;
  created_at: string;
}

// 구조화된 임상 메모
export interface StructuredNotes {
  text?: string;
  assistive_device?: string;
  pain_level?: number;
  condition?: string;
  tags?: string[];
}

// 환자 목표
export interface PatientGoal {
  id: string;
  patient_id: string;
  test_type: TestType;
  target_speed_mps?: number;
  target_time_seconds?: number;
  target_score?: number;
  target_date?: string;
  status: 'active' | 'achieved' | 'expired' | 'cancelled';
  created_at: string;
  achieved_at?: string;
}

export interface GoalProgress {
  goal: PatientGoal;
  current_value: number | null;
  achievement_pct: number;
  days_remaining?: number | null;
}

// 비교 리포트
export interface ComparisonReportData {
  summary_text: string;
  improvement_pct: number;
  is_improved: boolean;
  test_type: string;
  current_date: string;
  previous_date?: string | null;
}

// 관리자 대시보드 통계
export interface AdminDashboardStats {
  total_patients: number;
  total_tests: number;
  tests_this_week: number;
  tests_this_month: number;
  high_fall_risk_count: number;
  tests_by_period: { period: string; count: number }[];
  improvement_distribution: { improved: number; stable: number; worsened: number };
  tag_stats: { tag_name: string; color: string; patient_count: number; avg_speed: number | null }[];
}

// Multi-site
export interface Site {
  id: string;
  name: string;
  address?: string;
  phone?: string;
  admin_user_id?: string;
  created_at: string;
}

export interface SiteStats {
  site_id: string;
  site_name: string;
  total_patients: number;
  total_tests: number;
  total_therapists: number;
  avg_walk_speed_mps: number | null;
}

// EMR status
export interface EMRStatus {
  connected: boolean;
  message: string;
}

// 재활 추천
export interface RehabRecommendation {
  category: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  frequency: string;
  rationale: string;
}

export interface RecommendationsResponse {
  recommendations: RehabRecommendation[];
  disease_profile: string;
  disease_profile_display: string;
  risk_score: number;
  risk_level: 'normal' | 'mild' | 'moderate' | 'high';
}

// 추세 분석
export interface TrendDataPoint {
  date: string;
  value: number;
  trend_value: number;
}

export interface TrendPrediction {
  label: string;
  date: string;
  value: number;
  lower: number;
  upper: number;
}

export interface TrendAnalysisResponse {
  sufficient_data: boolean;
  message?: string;
  test_type?: string;
  trend_direction?: 'improving' | 'stable' | 'declining';
  slope_per_week?: number;
  r_squared?: number;
  std_error?: number;
  data_points?: TrendDataPoint[];
  predictions?: TrendPrediction[];
  latest_value?: number;
  latest_date?: string;
  total_measurements?: number;
  goal_eta?: string;
  goal_info?: { target_value?: number; weeks_remaining?: number; message?: string };
  value_label?: string;
  value_unit?: string;
}

// TUG 단계별 비교
export interface TUGPhaseComparisonTestSummary {
  id: string;
  test_date: string;
  total_time: number;
  assessment: string;
  phases: TUGPhases;
  stand_up_metrics?: { duration: number; assessment: string; used_hand_support?: boolean };
  sit_down_metrics?: { duration: number; assessment: string; used_hand_support?: boolean };
  reaction_time?: number;
  first_step_time?: number;
}

export interface TUGPhaseComparisonResponse {
  current_test: TUGPhaseComparisonTestSummary;
  previous_test: TUGPhaseComparisonTestSummary | null;
  phase_deltas: Record<string, { duration_diff: number | null; pct_change: number | null }> | null;
  total_time_diff: number | null;
  total_time_pct_change: number | null;
  available_tug_tests: Array<{ id: string; test_date: string; total_time: number }>;
}
