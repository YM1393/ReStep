# 10MWT (10-Meter Walk Test) 분석 시스템 PRD

## 문서 정보

| 항목 | 내용 |
|------|------|
| 버전 | 2.0.0 |
| 최종 업데이트 | 2026-02-23 |
| 상태 | 구현 완료 (현재 코드 기준 문서화) |
| 대상 파일 | `backend/analysis/gait_analyzer.py`, `backend/analysis/disease_profiles.py`, `backend/analysis/stopwatch_overlay.py` |

---

## 목차

1. [개요](#1-개요)
2. [기술 스택 및 아키텍처](#2-기술-스택-및-아키텍처)
3. [MediaPipe 설정 및 랜드마크](#3-mediapipe-설정-및-랜드마크)
4. [핵심 알고리즘: 1/h 분석 파이프라인](#4-핵심-알고리즘-1h-분석-파이프라인)
5. [보행 구간 감지 알고리즘](#5-보행-구간-감지-알고리즘)
6. [보행 패턴 분석 (기울기)](#6-보행-패턴-분석-기울기)
7. [임상 변수 계산](#7-임상-변수-계산)
8. [질환별 프로파일 시스템](#8-질환별-프로파일-시스템)
9. [신뢰도 점수](#9-신뢰도-점수)
10. [비대칭 경고](#10-비대칭-경고)
11. [시각화 및 오버레이](#11-시각화-및-오버레이)
12. [API 명세](#12-api-명세)
13. [데이터베이스](#13-데이터베이스)
14. [프론트엔드 UI](#14-프론트엔드-ui)
15. [출력 데이터 구조](#15-출력-데이터-구조)
16. [검증 결과](#16-검증-결과)

---

## 1. 개요

### 1.1 제품 소개

10MWT(10-Meter Walk Test)는 환자가 10m 직선 보행로를 걸어가는 시간을 측정하여 보행 속도를 산출하는 표준 임상 검사입니다. 본 시스템은 **단일 카메라 영상**에서 MediaPipe 자세 추정을 활용하여 보행 시간, 속도, 그리고 다양한 임상 보행 변수를 자동으로 분석합니다.

### 1.2 핵심 기술 원리

```
핀홀 카메라 모델:
  실제 거리 ∝ 1 / 픽셀 높이 (1/h)
  실제 속도 ∝ d(1/h)/dt (거리와 무관하게 일정)

→ 픽셀 속도(dh/dt)는 거리가 멀어지면 감소하여 경계 감지 부적합
→ 역수 속도(d(1/h)/dt)는 거리와 무관하여 경계 감지에 최적
```

### 1.3 측정 구간

```
카메라 ─────────────────────────────────────────→ 보행 방향
  0m    2m(START)                    12m(FINISH)   14m
  │      │                              │           │
  │ 가속 │◄──── 측정 구간 10m ────────►│  감속     │
  │ 구간 │                              │  구간     │
```

- **가속 구간**: 0~2m (INV_H_START_FRACTION으로 제외)
- **측정 구간**: 2~12m (실제 10m 보행 시간 측정)
- **카메라 위치**: 보행로 끝에서 약 14m 거리

---

## 2. 기술 스택 및 아키텍처

### 2.1 백엔드

| 구성 | 기술 |
|------|------|
| 프레임워크 | FastAPI |
| 자세 추정 | MediaPipe Pose Heavy (model_complexity=2) |
| 데이터베이스 | SQLite |
| 영상 처리 | OpenCV (cv2) |
| 수치 계산 | NumPy, SciPy |
| 실행 | ThreadPoolExecutor (max_workers=2) |

### 2.2 프론트엔드

| 구성 | 기술 |
|------|------|
| 프레임워크 | React 18 + TypeScript |
| 빌드 | Vite |
| 스타일 | TailwindCSS |
| 차트 | Recharts |
| 3D | React Three Fiber |
| HTTP | Axios |

### 2.3 분석 처리 흐름

```
영상 업로드 → 비동기 분석 시작 (ThreadPool)
                    │
                    ├─ 1. MediaPipe 포즈 추출 (전체 프레임)
                    ├─ 2. 1/h 시계열 계산
                    ├─ 3. 보행 구간 감지 (속도 기반)
                    ├─ 4. 보행 시간 산출 (보정 계수 적용)
                    ├─ 5. 보행 이벤트 감지 (heel strike)
                    ├─ 6. 임상 변수 계산
                    ├─ 7. 오버레이 영상 생성
                    └─ 8. DB 저장 + 결과 반환
```

---

## 3. MediaPipe 설정 및 랜드마크

### 3.1 MediaPipe 설정

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| `model_complexity` | 2 | Pose Heavy (최고 정밀도) |
| `min_detection_confidence` | 0.5 | 최소 감지 신뢰도 |
| `min_tracking_confidence` | 0.5 | 최소 추적 신뢰도 |
| `smooth_landmarks` | True | 랜드마크 스무딩 |

### 3.2 사용 랜드마크

| 부위 | 인덱스 | 용도 |
|------|--------|------|
| NOSE | 0 | head_y (픽셀 높이 계산) |
| LEFT/RIGHT_SHOULDER | 11, 12 | 어깨 기울기, head_y 폴백 |
| LEFT/RIGHT_WRIST | 15, 16 | 팔 흔들기 분석 |
| LEFT/RIGHT_HIP | 23, 24 | 골반 기울기, 체간 경사 |
| LEFT/RIGHT_ANKLE | 27, 28 | 발목 위치 (픽셀 높이, 보행 이벤트) |
| LEFT/RIGHT_HEEL | 29, 30 | 발 위치 |
| LEFT/RIGHT_FOOT_INDEX | 31, 32 | 발 높이 (foot clearance) |

### 3.3 픽셀 높이 계산

```python
# 우선순위 기반 추출
head_y:
  1순위: nose_y (visibility > 0)
  2순위: avg(left_shoulder_y, right_shoulder_y)

foot_y:
  1순위: avg(left_ankle_y, right_ankle_y) (둘 다 visibility > 0)
  2순위: avg(left_hip_y, right_hip_y) (폴백)

pixel_height = |foot_y - head_y|
→ pixel_height < 30 이면 해당 프레임 스킵
```

---

## 4. 핵심 알고리즘: 1/h 분석 파이프라인

### 4.1 파라미터 (v8 최적화)

| 상수 | 값 | 설명 |
|------|-----|------|
| `INV_H_START_FRACTION` | 0.60 | inv_h 곡선의 60% 지점에서 측정 시작 (~7.2m) |
| `CORRECTION_FACTOR_AWAY` | 2.4974 | "멀어지는" 방향 보정 계수 |
| `CORRECTION_FACTOR_TOWARD` | 0.63 | "다가오는" 방향 보정 계수 |
| `VEL_THRESHOLD_PCT` | 27 | 최대 속도 대비 보행 시작 임계값 (%) |
| `SMOOTH_MEDIAN_WS` | 9 | 미디안 필터 윈도우 크기 |
| `SMOOTH_AVG_WS` | 15 | 이동평균 윈도우 크기 |
| `VEL_PERCENTILE` | 82 | 최대 속도 계산 시 백분위 |
| `VEL_END_FACTOR` | 1.7 | 보행 종료 임계값 배수 |
| `VEL_ITERATIVE` | True | 2-pass 반복 정제 활성화 |
| `MODEL_COMPLEXITY` | 2 | MediaPipe Pose Heavy |

### 4.2 처리 단계

```
Step 1: 프레임별 데이터 추출 (_extract_frame_data)
        → pixel_height, shoulder_tilt, hip_tilt, 각 관절 좌표

Step 2: 스무딩
        → median filter (window=9) → moving average (window=15)
        → smoothed_heights

Step 3: 역수 높이 계산
        → inv_h[i] = 1.0 / max(smoothed_heights[i], 1.0)

Step 4: 실제 속도 계산
        → real_vel[i] = (inv_h[i] - inv_h[i-1]) / (times[i] - times[i-1])

Step 5: 보행 구간 감지 (_find_walk_region_real_velocity)
        → (walk_start_idx, walk_end_idx) 반환

Step 6: 2m/12m 지점 결정 (비례 보간)
        inv_h의 60% 지점 = 측정 시작, walk_end = 측정 종료

Step 7: 보행 시간 계산
        raw_time = time_12m - time_2m
        walk_time = raw_time × CORRECTION_FACTOR_AWAY (2.4974)
        walk_speed = 10.0m / walk_time
```

### 4.3 1/h 원리 상세

```
핀홀 카메라 모델에서:
  h(d) = f × H / d
    h = 픽셀 높이, f = 초점거리, H = 실제 키, d = 카메라까지 거리

따라서:
  1/h = d / (f × H)    ← 실제 거리에 비례!
  d(1/h)/dt = v / (f × H)  ← 실제 속도에 비례! (거리 무관)

예시:
  5m 위치:  h=100px, 1/h=0.010
  10m 위치: h=50px,  1/h=0.020
  → 균일 보행 시 d(1/h)/dt는 일정
```

---

## 5. 보행 구간 감지 알고리즘

### 5.1 실제 속도 기반 감지

```python
def _find_walk_region_real_velocity():
    # 1. 실제 속도 스무딩 (31-포인트 이동평균)
    rv_smooth = moving_average(real_vel, window=31)

    # 2. 최대 속도 추정 (82번째 백분위)
    positive_rv = [v for v in rv_smooth if v > 0]
    max_rv = np.percentile(positive_rv, 82)

    # 3. 비대칭 임계값 설정
    threshold_start = max_rv × 0.27     # 시작 임계값
    threshold_end = threshold_start × 1.7  # 종료 임계값 (더 높음)

    # 4. 연속 구간 탐색 (최소 2초 이상)
    regions = find_continuous_regions(rv_smooth, threshold_start, threshold_end)
    walk_start, walk_end = longest_region(regions)

    # 5. 2-pass 반복 정제 (VEL_ITERATIVE=True)
    if VEL_ITERATIVE:
        local_max_rv = percentile(rv_smooth[walk_start:walk_end], 82)
        threshold_start2 = local_max_rv × 0.27
        threshold_end2 = threshold_start2 × 1.7
        walk_start, walk_end = longest_region(rv_smooth, threshold_start2, threshold_end2)

    return (walk_start, walk_end)
```

### 5.2 비대칭 임계값을 사용하는 이유

```
보행 시작: 가속이 완만 → 낮은 임계값(27%)으로 감지
보행 종료: 감속이 더 급격 → 높은 임계값(27% × 1.7 = 45.9%)으로 감지
→ 시작은 부드럽게, 종료는 확실하게 잡음
```

### 5.3 2-pass 반복 정제

```
Pass 1: 전체 영상에서 대략적 보행 구간 찾기
  → 영상 시작/끝의 노이즈가 max_rv를 왜곡할 수 있음

Pass 2: 1차 구간 내에서 max_rv 재계산
  → 실제 보행 속도에 맞는 정밀 임계값 사용
  → 경계 정확도 향상
```

---

## 6. 보행 패턴 분석 (기울기)

### 7.1 어깨/골반 기울기 계산

```python
# 프레임별 기울기 계산
shoulder_tilt_deg = atan2(-(right_shoulder_y - left_shoulder_y),
                          |right_shoulder_x - left_shoulder_x|) × (180/π)

hip_tilt_deg = atan2(-(right_hip_y - left_hip_y),
                      |right_hip_x - left_hip_x|) × (180/π)

# 양수 = 오른쪽 높음, 음수 = 왼쪽 높음
```

### 7.2 기울기 통계

| 지표 | 계산 | 설명 |
|------|------|------|
| `shoulder_tilt_avg` | 보행 구간 프레임 평균 | 전체 어깨 기울기 평균 |
| `shoulder_tilt_max` | 최대 절대값 | 최대 어깨 기울기 |
| `hip_tilt_avg` | 보행 구간 프레임 평균 | 전체 골반 기울기 평균 |
| `hip_tilt_max` | 최대 절대값 | 최대 골반 기울기 |

### 7.3 기울기 방향 판정

```
|avg| > 2°: "오른쪽 높음 (X°)" 또는 "왼쪽 높음 (X°)"
|avg| ≤ 2°: "정상"
```

### 7.4 전체 평가 (assessment)

```
어깨/골반 기울기 조합에 따라:
- 양쪽 모두 정상: "정상 보행 패턴"
- 어깨만 이상: "어깨 기울기 주의"
- 골반만 이상: "골반 기울기 주의"
- 양쪽 모두 이상: "어깨/골반 기울기 주의"
```

---

## 7. 임상 변수 계산

### 8.1 보행 이벤트 감지 (`_detect_gait_events`)

```python
# Heel Strike(HS) 감지 알고리즘
1. 보행 구간 내 좌/우 발목 Y좌표 추출
2. 선형 트렌드 제거 (polyfit degree=1)
3. 스무딩 (convolve)
4. 피크 탐색 (local maxima = HS)
   - distance: max(int(0.3 × fps), 3) 프레임
   - prominence: std(detrended) × 0.3
5. 좌/우 각각의 HS 프레임 인덱스 및 시간 반환
```

### 8.2 보행 변수 목록

#### Cadence (분당 걸음수)

| 항목 | 내용 |
|------|------|
| 계산 | `(total_steps / walk_duration) × 60` |
| 출력 | `value` (steps/min), `total_steps`, `unit` |
| 정상 범위 | 100~120 steps/min |
| 활성화 프로파일 | 파킨슨, MS, 낙상위험 |

#### Step Time (보폭 시간)

| 항목 | 내용 |
|------|------|
| 계산 | 좌→우 또는 우→좌 HS 간 시간 |
| 출력 | `mean`, `cv` (변동계수 %), `left_mean`, `right_mean`, `unit` |
| 정상 범위 | 0.5~0.6초 |
| 활성화 프로파일 | 기본 (전체) |

#### Stride Time (보행주기 시간)

| 항목 | 내용 |
|------|------|
| 계산 | 같은 발 연속 HS 간 시간 (L→L, R→R) |
| 출력 | `mean`, `cv` (%), `unit` |
| 정상 범위 | 1.0~1.2초 |
| 활성화 프로파일 | 기본 (전체) |

#### Step Time Asymmetry (보폭 시간 비대칭)

| 항목 | 내용 |
|------|------|
| 계산 | `\|L_mean - R_mean\| / (L_mean + R_mean) × 200` |
| 출력 | `value` (%), `left_mean`, `right_mean`, `threshold` |
| 정상 기준 | < 10% |
| 활성화 프로파일 | 기본 (전체) |

#### Arm Swing (팔 흔들기)

| 항목 | 내용 |
|------|------|
| 계산 | Wrist Y 디트렌드 → 피크-트러프 진폭 |
| 출력 | `left_amplitude`, `right_amplitude`, `asymmetry_index` (%) |
| 비대칭 기준 | < 15% |
| 활성화 프로파일 | 파킨슨(★★★), 뇌졸중 |

#### Foot Clearance (발 높이)

| 항목 | 내용 |
|------|------|
| 계산 | Foot Y 디트렌드 → 음의 피크 (발이 올라간 높이) |
| 출력 | `mean_clearance`, `min_clearance`, `unit` |
| 임상 의의 | 낮으면 shuffling 위험 (파킨슨) |
| 활성화 프로파일 | 파킨슨, 슬관절OA |

#### Double Support (양발 지지 비율)

| 항목 | 내용 |
|------|------|
| 계산 | `(2 × mean_step / mean_stride - 1) × 100` |
| 출력 | `value` (%), `unit` |
| 정상 범위 | 20~30% |
| 활성화 프로파일 | 기본 (전체) |

#### Stride Regularity (보행 규칙성)

| 항목 | 내용 |
|------|------|
| 계산 | Ankle Y 자기상관(autocorrelation) → stride 주파수 피크 |
| 출력 | `value` (0~1), `stride_period` (초), `unit` |
| 정상 범위 | > 0.8 |
| 활성화 프로파일 | 기본 (전체) |

#### Trunk Inclination (체간 경사)

| 항목 | 내용 |
|------|------|
| 계산 | `(hip_y_mid - shoulder_y_mid)` 프레임별 |
| 출력 | `mean`, `std`, `unit` |
| 임상 의의 | 전방/후방 기울어짐 정도 |
| 활성화 프로파일 | 기본 (전체) |

#### Swing/Stance Ratio (유각/입각 비율)

| 항목 | 내용 |
|------|------|
| 계산 | `swing_time ≈ stride_time - step_time` |
| 출력 | `swing_pct`, `stance_pct` (%) |
| 정상 범위 | ~40% 유각, ~60% 입각 |
| 활성화 프로파일 | 기본 (전체) |

#### Stride Length (보폭 거리)

| 항목 | 내용 |
|------|------|
| 계산 | `walk_speed_mps × stride_time_mean` |
| 출력 | `value` (m), `unit` |
| 정상 범위 | 1.0~1.5m |
| 활성화 프로파일 | 기본 (전체) |

---

## 8. 질환별 프로파일 시스템

### 9.1 프로파일 구조

```
DiseaseProfile
├── name: str                    # 프로파일 키 (예: "parkinsons")
├── display_name: str            # 표시명 (예: "파킨슨병")
├── keywords: List[str]          # 진단명 매칭 키워드 (한글/영문)
├── gait: GaitProfile            # 10MWT 파라미터 오버라이드
├── tug: TUGProfile              # TUG 파라미터 오버라이드
├── clinical_flags: ClinicalFlags # 임상 변수 활성화 플래그
└── description: str             # 프로파일 설명
```

### 9.2 지원 질환 (9개 프로파일)

| 프로파일 | 표시명 | 매칭 키워드 |
|---------|--------|------------|
| `default` | 기본 | (매칭 실패 시 기본값) |
| `parkinsons` | 파킨슨병 | 파킨슨, parkinson, PD, 진전마비 |
| `stroke` | 뇌졸중 | 뇌졸중, stroke, CVA, 뇌경색, 뇌출혈, 편마비, hemiplegia |
| `ms` | 다발성 경화증 | 다발성 경화증, multiple sclerosis, MS, 탈수초 |
| `sci` | 척수 손상 | 척수 손상, spinal cord, SCI, 척수염, 하반신마비 |
| `cp` | 뇌성마비 | 뇌성마비, cerebral palsy, CP |
| `knee_oa` | 슬관절 OA/TKA | 슬관절, TKA, TKR, knee OA, 퇴행성 무릎, 인공슬관절 |
| `hip_oa` | 고관절 OA/골절 | 고관절, THA, THR, hip OA, 대퇴골, 인공고관절 |
| `fall_risk` | 낙상 위험 | 낙상, fall risk, 균형 장애 |

### 9.3 질환별 보행 파라미터 오버라이드

| 파라미터 | 기본 | 파킨슨 | 뇌졸중 | MS | 척수손상 | 뇌성마비 | 슬관절OA | 고관절OA | 낙상위험 |
|----------|------|--------|--------|-----|---------|---------|---------|---------|---------|
| `vel_threshold_pct` | 27 | **15** | **18** | **20** | **15** | **15** | **20** | **20** | **20** |
| `smooth_median_ws` | 9 | **13** | **11** | **11** | **13** | **13** | 9 | 9 | **11** |
| `smooth_avg_ws` | 15 | **21** | **19** | **17** | **21** | **21** | 15 | 15 | **17** |
| `vel_percentile` | 82 | **84** | 82 | **84** | **80** | **80** | 82 | 82 | **84** |
| `vel_end_factor` | 1.7 | **1.5** | **2.2** | **2.0** | **2.5** | **2.2** | **1.9** | **1.9** | **2.0** |
| `correction_factor_away` | 2.4974 | 2.4974 | 2.4974 | 2.4974 | 2.4974 | 2.4974 | 2.4974 | 2.4974 | 2.4974 |

**파라미터 조정 근거:**
- **파킨슨**: 서동(bradykinesia) → 가속이 매우 느림(`vel_threshold=15%`), 진전 노이즈 → 높은 스무딩(`median=13`)
- **뇌졸중**: 편마비 → 불균형한 속도 프로파일, 감속 느림(`vel_end_factor=2.2`)
- **척수손상**: 경직 보행 → 매우 느린 가속/감속(`vel_threshold=15%`, `vel_end_factor=2.5`)

### 9.4 진단명 매칭 알고리즘

```python
def resolve_profile(diagnosis: Optional[str]) -> DiseaseProfile:
    if not diagnosis:
        return DEFAULT_PROFILE

    diagnosis_lower = diagnosis.lower()
    for profile in ALL_PROFILES:
        for keyword in profile.keywords:
            if keyword.lower() in diagnosis_lower:
                return profile

    return DEFAULT_PROFILE
```

---

## 9. 신뢰도 점수

### 10.1 신뢰도 구성 요소

| 항목 | 최대 점수 | 기준 |
|------|----------|------|
| 포즈 감지율 | 30점 | `(detected_frames / total_frames) × 30` |
| 보행 지속 시간 | 25점 | 3~15초 범위에서 스케일링 |
| 보행 시간 합리성 | 25점 | 3~30초 범위 → 25점, 범위 밖 → 감점 |
| 보행 속도 합리성 | 20점 | 0.3~2.5 m/s → 20점, 범위 밖 → 감점 |
| **총점** | **100점** | |

### 10.2 신뢰 등급

| 점수 범위 | 등급 | 레이블 |
|-----------|------|--------|
| 80~100 | high | 높음 |
| 60~79 | medium | 보통 |
| 40~59 | low | 낮음 |
| 0~39 | very_low | 매우 낮음 |

### 10.3 출력 구조

```json
{
  "score": 92,
  "level": "high",
  "label": "높음",
  "details": {
    "pose_detection_rate": 93.3,
    "walk_duration_score": 25,
    "walk_time_score": 25,
    "walk_speed_score": 20
  }
}
```

---

## 10. 비대칭 경고

### 11.1 경고 생성 기준

| 변수 | 경미(mild) | 보통(moderate) | 심함(severe) |
|------|-----------|---------------|-------------|
| Step Time Asymmetry | 10~20% | 20~30% | > 30% |
| Arm Swing Asymmetry | 15~30% | 30~50% | > 50% |
| 어깨 기울기 | 3~5° | 5~8° | > 8° |
| 골반 기울기 | 3~5° | 5~8° | > 8° |

### 11.2 경고 출력 형식

```json
{
  "type": "step_time_asymmetry",
  "severity": "mild",
  "label": "보폭 시간 경미한 비대칭",
  "value": 12.5,
  "unit": "%",
  "description": "좌측 보폭 시간이 더 깁니다 (비대칭 12.5%)",
  "threshold": "정상 < 10%"
}
```

---

## 11. 시각화 및 오버레이

### 12.1 포즈 스켈레톤 오버레이

```
색상 체계:
  좌측 (홀수 인덱스: 11,13,15,...): 시안 (255,150,0) BGR
  우측 (짝수 인덱스: 12,14,16,...): 오렌지 (0,128,255) BGR
  중앙 연결: 회색 (200,200,200) BGR

얼굴 랜드마크 (0~10): 제외 (개인정보 보호)
신체 연결선: 22개
선 두께: 4px, 원 반지름: 8px
visibility 임계값: > 20%
```

### 12.2 스톱워치 오버레이

```
위치: 영상 우하단
형식: "00.00s"
색상:
  - 측정 전: 비표시
  - 측정 중: 흰색 텍스트
  - 측정 완료: 녹색 텍스트

타이밍: 프레임 기반 (벽시계 아닌 영상 프레임 인덱스 사용)
진행률 = (current_frame - start_frame) / (end_frame - start_frame)
표시 시간 = 진행률 × measure_time
```

### 12.3 측정선 오버레이

```
START 2m 선: 녹색 수평선 (line_y_2m 위치)
FINISH 12m 선: 빨간색 수평선 (line_y_12m 위치)
라벨: "START 2m", "FINISH 12m"
통과 하이라이트: 전후 ±0.5초 동안 강조 효과
블렌딩: 60% 선 + 40% 원본 영상
```

### 12.4 오버레이 영상 코덱

```
1순위: H.264 (avc1) - 브라우저 호환
2순위: mp4v - 폴백
출력: {원본파일명}_overlay.mp4
```

---

## 12. API 명세

### 13.1 영상 업로드 및 분석

**POST** `/api/tests/{patient_id}/upload`

```
Headers:
  X-User-Id: string           # 치료사 ID
  X-User-Role: "therapist"    # 역할
  X-User-Approved: "true"     # 승인 여부
  X-Walking-Direction: "away" | "toward"  # 보행 방향 (기본: away)
  X-Test-Type: "10MWT"        # 검사 유형

Body: multipart/form-data
  file: 영상 파일 (MOV, MP4 등)

Response: 202 Accepted
  {
    "file_id": "uuid",
    "message": "업로드 완료. 분석이 시작되었습니다.",
    "status_endpoint": "/api/tests/status/{file_id}"
  }
```

### 13.2 분석 상태 조회

**GET** `/api/tests/status/{file_id}`

```
Response:
  {
    "status": "processing" | "completed" | "error",
    "progress": 0-100,
    "message": "현재 처리 단계 설명",
    "current_frame": "base64 이미지 (선택)",
    "result": { ... } (completed 시에만)
  }
```

### 13.3 검사 결과 조회

**GET** `/api/tests/{test_id}`

```
Response: WalkTestResponse
  {
    "id": "uuid",
    "patient_id": "uuid",
    "test_date": "ISO8601",
    "test_type": "10MWT",
    "walk_time_seconds": 7.45,
    "walk_speed_mps": 1.34,
    "video_url": "/uploads/...",
    "analysis_data": { ... 전체 분석 결과 ... },
    "notes": "치료사 메모",
    "created_at": "ISO8601"
  }
```

### 13.4 환자별 검사 목록

**GET** `/api/tests/patient/{patient_id}?test_type=10MWT`

```
Response: List[WalkTestResponse]  # 최신순 정렬
```

### 13.5 이전 검사 비교

**GET** `/api/tests/patient/{patient_id}/compare`

```
Response:
  {
    "current_test": WalkTestResponse,
    "previous_test": WalkTestResponse,
    "comparison_message": "보행 시간이 X초 단축되어...",
    "speed_difference": float,
    "time_difference": float
  }
```

### 13.6 통계 요약

**GET** `/api/tests/patient/{patient_id}/stats?test_type=10MWT`

```
Response:
  {
    "mean_walk_time": float,
    "std_walk_time": float,
    "mean_walk_speed": float,
    "std_walk_speed": float,
    "test_count": int,
    "fall_risk_percentage": int
  }
```

### 13.7 추세/트렌드 분석

**GET** `/api/tests/patient/{patient_id}/trends?test_type=10MWT`

```
Response:
  {
    "sufficient_data": bool,
    "trend_direction": "improving" | "stable" | "declining",
    "slope_per_week": float,
    "r_squared": float,
    "data_points": [{test_id, date, walk_speed, walk_time, ...}],
    "predictions": [{date, value, upper, lower}],
    "goal_eta": "YYYY-MM-DD" | null
  }
```

### 13.8 임상 정상 범위 비교

**GET** `/api/tests/patient/{patient_id}/clinical-normative?test_id={id}`

```
Response:
  {
    "speed": { normative, z_score, comparison, percent_of_normal, ... },
    "time": { normative, z_score, comparison, ... },
    "clinical_variables": { cadence, step_time, stride_length, ... }
  }
```

### 12.9 리포트/내보내기

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/tests/{id}/pdf?template=...` | PDF 리포트 다운로드 |
| `GET /api/tests/{id}/csv` | CSV 데이터 내보내기 |
| `POST /api/tests/{id}/email` | 이메일 리포트 전송 |
| `GET /api/tests/{id}/ai-report` | AI 분석 리포트 |
| `GET /api/tests/{id}/walking-clip` | 보행 하이라이트 클립 |

---

## 13. 데이터베이스

### 14.1 walk_tests 테이블

```sql
CREATE TABLE walk_tests (
    id TEXT PRIMARY KEY,               -- UUID
    patient_id TEXT NOT NULL,           -- FK → patients
    test_date TEXT DEFAULT CURRENT_TIMESTAMP,
    test_type TEXT DEFAULT '10MWT',     -- "10MWT" | "TUG"
    walk_time_seconds REAL NOT NULL,    -- 10m 보행 시간 (초)
    walk_speed_mps REAL NOT NULL,       -- 보행 속도 (m/s)
    video_url TEXT,                     -- /uploads/filename
    analysis_data TEXT,                 -- JSON (전체 분석 결과)
    notes TEXT,                         -- 치료사 메모
    therapist_id TEXT,                  -- 치료사 ID
    site_id TEXT,                       -- 기관 ID
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);
```

### 14.2 patients 테이블

```sql
CREATE TABLE patients (
    id TEXT PRIMARY KEY,               -- UUID
    patient_number TEXT UNIQUE,        -- 환자 번호
    name TEXT NOT NULL,                -- 이름
    gender TEXT,                       -- 성별
    birth_date TEXT,                   -- 생년월일
    height_cm REAL NOT NULL,           -- 키 (cm) ★ 1/h 보정에 필수
    diagnosis TEXT,                    -- 진단명 (질환 프로파일 매칭)
    site_id TEXT,                      -- 기관 ID
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

---

## 14. 프론트엔드 UI

### 15.1 환자 상세 페이지 (PatientDetail)

```
┌──────────────────────────────────────────────────────────┐
│ 환자명 / 환자번호 / 태그 / 진단명                            │
│ [PDF] [이메일] [업로드] [실시간 TUG]                        │
├──────────────────────────────┬───────────────────────────┤
│                              │                           │
│  ┌─ 검사 결과 카드 (3열) ──┐ │  ┌─ 신뢰도 점수 ────────┐ │
│  │ 보행시간 │ 보행속도 │ 분석  │ │  │ 원형 프로그레스 바    │ │
│  │ 7.45s   │ 1.34m/s │ 프레임│ │  │ 92점 (높음)          │ │
│  └─────────────────────────┘ │  └────────────────────────┘ │
│                              │                           │
│  ┌─ 낙상 위험 점수 ────────┐ │  ┌─ 이전 비교 ──────────┐ │
│  │ 그라데이션 카드          │ │  │ 시간 차이, 속도 차이   │ │
│  │ 총점: 82점              │ │  │ +0.5s, -0.07 m/s     │ │
│  └─────────────────────────┘ │  └────────────────────────┘ │
│                              │                           │
│  ┌─ 비대칭 경고 ───────────┐ │  ┌─ 반복 측정 통계 ─────┐ │
│  │ ⚠ 보폭 시간 비대칭 12.5%│ │  │ 평균, 표준편차, 범위   │ │
│  └─────────────────────────┘ │  └────────────────────────┘ │
│                              │                           │
│  ┌─ 보행 패턴 ─────────────┐ │  ┌─ 추세 차트 ──────────┐ │
│  │ 어깨 기울기: 2.3°       │ │  │ LineChart (속도/시간)  │ │
│  │ 골반 기울기: 1.1°       │ │  │ 예측선 포함            │ │
│  └─────────────────────────┘ │  └────────────────────────┘ │
│                              │                           │
│  ┌─ 임상 변수 (3열 그리드) ┐ │  ┌─ 임상 트렌드 ────────┐ │
│  │ Cadence  │ Steps  │ ...  │ │  │ 다변수 추세 차트      │ │
│  │ 108/min  │ 18개   │      │ │  └────────────────────────┘ │
│  │ 정상 범위 비교          │ │                           │
│  └─────────────────────────┘ │  ┌─ 상관분석 ──────────┐  │
│                              │  │ 변수간 상관 행렬      │ │
│  ┌─ 영상 플레이어 ─────────┐ │  └────────────────────────┘ │
│  │ 원본 / 오버레이 토글    │ │                           │
│  │ 실시간 각도 텍스트 표시  │ │  ┌─ AI 리포트 ─────────┐ │
│  └─────────────────────────┘ │  │ 자동 생성 분석 보고서  │ │
│                              │  └────────────────────────┘ │
│  ┌─ 기울기 차트 ───────────┐ │                           │
│  │ 어깨/골반 기울기 vs 시간 │ │  ┌─ 검사 정보 ─────────┐ │
│  │ ±5° 기준선, 평균선      │ │  │ 유형, AI모델, 프레임  │ │
│  └─────────────────────────┘ │  │ 키, 검사 횟수         │ │
│                              │  └────────────────────────┘ │
│  ┌─ 치료사 메모 ───────────┐ │                           │
│  │ 리치 텍스트 에디터       │ │  ┌─ 빠른 실행 ─────────┐ │
│  │ [저장]                  │ │  │ 이력 / 편집 / 삭제    │ │
│  └─────────────────────────┘ │  └────────────────────────┘ │
└──────────────────────────────┴───────────────────────────┘
```

### 15.2 VideoModal (영상 모달)

```
┌──────────────────────────────────────┐
│ [X]                                  │
│                                      │
│  ┌──────────────────────────────┐   │
│  │                              │   │
│  │    영상 플레이어              │   │
│  │    (원본/오버레이 토글)       │   │
│  │    실시간 각도 텍스트 오버레이 │   │
│  │                              │   │
│  └──────────────────────────────┘   │
│                                      │
│  ┌─ 기울기 동기화 차트 ──────────┐   │
│  │ 어깨(파란) / 골반(초록) vs 시간│   │
│  │ ±5° 기준선, 커서 연동         │   │
│  └──────────────────────────────┘   │
│                                      │
│  파일 크기: 12.5MB  [다운로드]       │
└──────────────────────────────────────┘
```

### 15.3 검사 이력 페이지 (History)

- 테이블: 검사일(편집가능), 유형, 시간, 속도, 메모, 액션
- 필터: 검사 유형별 (ALL, 10MWT, TUG, BBS)
- 확장 행: 상세 분석 데이터
- 차트: SpeedChart (속도/시간 추이), ComparisonReport

### 15.4 대시보드 (Dashboard)

- 환자 목록 (위험도/태그/검색 필터)
- 위젯: 최근 검사, 고위험 환자, 속도 분포, 주간 활동
- 위젯 커스터마이징 (드래그 정렬)

---

## 15. 출력 데이터 구조

### 16.1 분석 결과 JSON (analysis_data)

```json
{
  "walk_time_seconds": 7.45,
  "walk_speed_mps": 1.34,
  "fps": 60,
  "total_frames": 900,
  "video_duration": 15.0,
  "frames_analyzed": 850,
  "start_frame": 120,
  "end_frame": 610,
  "patient_height_cm": 170,
  "model": "MediaPipe Pose Heavy (complexity=2)",
  "walking_direction": "away",

  "measurement_zone": {
    "start_distance_m": 1.6,
    "end_distance_m": 12.0,
    "measured_distance_m": 10.0
  },

  "calibration_method": "proportional",

  "disease_profile": "default",
  "disease_profile_display": "기본",

  "overlay_video_filename": "video_overlay.mp4",

  "gait_pattern": {
    "shoulder_tilt_avg": 2.3,
    "shoulder_tilt_max": 8.5,
    "shoulder_tilt_direction": "우측 높음 (2.3°)",
    "hip_tilt_avg": 1.1,
    "hip_tilt_max": 6.2,
    "hip_tilt_direction": "정상",
    "assessment": "어깨 기울기 주의"
  },

  "angle_data": [
    { "time": 0.0, "shoulder_tilt": 2.1, "hip_tilt": 1.0 },
    ...
  ],

  "confidence_score": {
    "score": 92,
    "level": "high",
    "label": "높음",
    "details": {
      "pose_detection_rate": 93.3,
      "walk_duration_score": 25,
      "walk_time_score": 25,
      "walk_speed_score": 20
    }
  },

  "asymmetry_warnings": [
    {
      "type": "step_time_asymmetry",
      "severity": "mild",
      "label": "보폭 시간 경미한 비대칭",
      "value": 12.5,
      "unit": "%",
      "description": "좌측 보폭 시간이 더 깁니다",
      "threshold": "정상 < 10%"
    }
  ],

  "clinical_variables": {
    "cadence": { "value": 108.3, "unit": "steps/min", "total_steps": 18 },
    "step_time": { "mean": 0.556, "cv": 4.2, "unit": "s", "left_mean": 0.548, "right_mean": 0.564 },
    "stride_time": { "mean": 1.112, "cv": 3.8, "unit": "s" },
    "step_time_asymmetry": { "value": 2.9, "unit": "%", "left_mean": 0.548, "right_mean": 0.564 },
    "arm_swing": { "left_amplitude": 12.5, "right_amplitude": 13.2, "asymmetry_index": 2.7 },
    "foot_clearance": { "mean_clearance": 8.3, "min_clearance": 5.1 },
    "double_support": { "value": 24.5, "unit": "%" },
    "stride_regularity": { "value": 0.87, "stride_period": 1.11 },
    "trunk_inclination": { "mean": 145.2, "std": 3.5 },
    "swing_stance_ratio": { "swing_pct": 39.8, "stance_pct": 60.2 },
    "stride_length": { "value": 1.23, "unit": "m" }
  },

  "measurement_lines": {
    "start_y": 450,
    "finish_y": 520,
    "start_frame": 120,
    "finish_frame": 610
  },

  "pose_3d_frames": [
    { "time": 2.0, "landmarks": [[0.001, -0.152, 0.089], ...] }
  ]
}
```

---

## 16. 검증 결과

### 17.1 레퍼런스 영상 (v8)

| 영상 | 실측 시간 | 분석 결과 | 오차 | 오차율 |
|------|----------|----------|------|--------|
| 10MWT_7.33.MOV | 7.33s | 7.34s | +0.01s | 0.14% |
| 10MWT_7.58.MOV | 7.58s | 7.60s | +0.02s | 0.26% |
| 10MWT_9.33.MOV | 9.33s | 9.32s | -0.01s | 0.11% |
| 10MWT_10.43.MOV | 10.43s | 10.40s | -0.03s | 0.29% |

### 17.2 정확도 지표

| 지표 | v7 (이전) | v8 (현재) | 개선율 |
|------|----------|----------|-------|
| MAE (평균 절대 오차) | 0.052s | **0.015s** | 71% |
| Max Error (최대 오차) | 0.089s | **0.030s** | 66% |
| LOO MAE (Leave-One-Out) | 0.069s | **0.018s** | 74% |

### 17.3 v7 → v8 변경 요약

| 파라미터 | v7 | v8 |
|----------|----|----|
| VEL_THRESHOLD_PCT | 23% | 27% |
| VEL_PERCENTILE | 86 | 82 |
| VEL_END_FACTOR | 1.9 | 1.7 |
| CORRECTION_FACTOR_AWAY | 2.4879 | 2.4974 |

---

## 부록: 에러 처리 및 폴백

### A.1 프레임 데이터 폴백

```
head_y: nose → avg(shoulders) → 프레임 스킵
foot_y: avg(ankles) → avg(hips) → 프레임 스킵
pixel_height < 30: 프레임 스킵 (과소 감지)
```

### A.2 보행 이벤트 감지 폴백

```
피크 < 2개/발: → 임상 변수 계산 스킵
→ 기본 메트릭(시간/속도)만 보고, 임상 변수 없이 결과 반환
```
