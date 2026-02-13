# TUG (Timed Up and Go) 분석 변수 보고서

## 1. 개요

TUG 검사는 의자에서 일어나 3m 걷고, 180도 회전 후 돌아와 다시 앉는 동작의 소요 시간을 측정하는 임상 기능 평가.

- **듀얼 카메라**: 측면(side) + 정면(front) 영상 동시 분석
- **측면 영상**: 기립/착석, 보행, 회전 등 5개 구간(phase) 감지
- **정면 영상**: 어깨/골반 기울기, 체중이동 분석

---

## 2. MediaPipe 설정 및 랜드마크

### 2.1 MediaPipe 설정

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| `model_complexity` | 2 | Pose Heavy (최고 정밀도) |
| `min_detection_confidence` | 0.5 | 최소 감지 신뢰도 |
| `min_tracking_confidence` | 0.5 | 최소 추적 신뢰도 |
| `smooth_landmarks` | True | 랜드마크 스무딩 |
| `enable_segmentation` | False | 세그멘테이션 비활성화 |

### 2.2 사용 랜드마크

| 부위 | 인덱스 | 용도 |
|------|--------|------|
| NOSE | 0 | head_y (기립/착석 속도) |
| LEFT/RIGHT_SHOULDER | 11, 12 | 어깨 기울기, 회전 방향 |
| LEFT/RIGHT_WRIST | 15, 16 | 손 지지 감지 |
| LEFT/RIGHT_HIP | 23, 24 | 골반 기울기, 엉덩이 높이 |
| LEFT/RIGHT_KNEE | 25, 26 | 다리 각도 |
| LEFT/RIGHT_ANKLE | 27, 28 | 다리 각도, 첫걸음 감지 |
| LEFT/RIGHT_HEEL | 29, 30 | 발 위치 (체중이동) |
| LEFT/RIGHT_FOOT_INDEX | 31, 32 | 발 위치 (체중이동) |

---

## 3. 임계값 및 파라미터

### 3.1 자세 판단 임계값 (측면 영상)

| 변수 | 값 | 설명 |
|------|-----|------|
| `SITTING_ANGLE_THRESHOLD` | 120도 | 다리 각도 <= 120도 → 앉은 자세 |
| `STANDING_ANGLE_THRESHOLD` | 160도 | 다리 각도 >= 160도 → 선 자세 |
| `UPRIGHT_TORSO_THRESHOLD` | 75도 | 상체 각도 >= 75도 → 직립 |
| `HAND_SUPPORT_THRESHOLD` | 0.15 | 손목-무릎 정규화 거리 < 0.15 → 손 지지 |
| 손 지지 판정 | 30% | 해당 구간 프레임 중 30% 이상이면 "손 지지 사용" |

### 3.2 기울기 분석 임계값 (정면 영상)

| 변수 | 값 | 설명 |
|------|-----|------|
| `TILT_ANGLE_CLAMP` | +-25도 | 회전 왜곡 방지 최대 기울기 |
| `DEVIATION_THRESHOLD` | 5.0도 | 일반 보행 구간 기울기 이상치 기준 |
| `TURN_DEVIATION_THRESHOLD` | 15.0도 | 회전 구간 기울기 이상치 기준 (더 관대) |
| `MIN_FACING_RATIO` | 0.03 | 어깨/골반 폭 >= 프레임 폭의 3% → 정면 |
| `CLAMP_LIMIT` | 24.0도 | +-25도 근처 값 무시 (회전 왜곡 판정) |

### 3.3 신호 처리

| 처리 | 파라미터 | 설명 |
|------|----------|------|
| 이동평균 | window = min(15, n/10), 최소 3 | leg_angle, head_y, torso_angle에 적용 |
| 속도 계산 | 5-frame 커널 스무딩 후 np.gradient × fps | 단위: degrees/sec 또는 normalized/sec |
| 정규화 | (x - min) / (max - min) | 융합 점수용 0~1 범위 변환 |

---

## 4. TUG 5단계 (Phase) 감지

### 4.1 단계 정의

```
1. stand_up  : 앉은 자세 → 선 자세 (다리각도 120도 → 160도)
2. walk_out  : 기립 완료 → 회전 지점 (전방 3m)
3. turn      : 180도 회전 (어깨 방향 최대 변화)
4. walk_back : 회전 완료 → 착석 시작 (복귀 3m)
5. sit_down  : 선 자세 → 앉은 자세 (다리각도 160도 → 120도)
```

### 4.2 구간 경계 감지: 다중 신호 융합 (Multi-Signal Fusion)

각 구간 경계를 단일 임계값이 아닌 **여러 신호의 가중 합산 점수**로 감지:

#### stand_start (기립 시작)
| 신호 | 가중치 | 설명 |
|------|--------|------|
| leg_angle_velocity | 35% | 다리 각도 증가 속도 |
| head_y_velocity | 30% | 머리 상승 속도 |
| torso_angle_velocity | 20% | 상체 펴지는 속도 |
| hip_height_velocity | 15% | 엉덩이 상승 속도 |

#### stand_end (기립 완료)
| 신호 | 가중치 | 설명 |
|------|--------|------|
| leg_angle_level | 30% | 다리 각도 >= 160도 도달 |
| torso_angle_level | 30% | 상체 각도 >= 75도 도달 |
| hip_stability | 25% | 엉덩이 높이 안정화 (1/|속도|) |
| head_stability | 15% | 머리 높이 안정화 (1/|속도|) |

#### turn (회전 감지)
| 신호 | 가중치 | 설명 |
|------|--------|------|
| shoulder_direction_velocity | 50% | 어깨 방향 변화 최대 |
| hip_stability | 20% | 엉덩이 높이 안정 |
| leg_stability | 30% | 다리 각도 안정 |

#### sit_start (착석 시작)
| 신호 | 가중치 | 설명 |
|------|--------|------|
| leg_angle_velocity | 35% | 다리 각도 감소 속도 (음수) |
| head_y_velocity | 30% | 머리 하강 속도 |
| torso_angle_velocity | 20% | 상체 구부러지는 속도 |
| hip_height_velocity | 15% | 엉덩이 하강 속도 |

#### sit_end (착석 완료)
| 신호 | 가중치 | 설명 |
|------|--------|------|
| leg_angle_low | 50% | 다리 각도 <= 120도 |
| hip_stability | 50% | 엉덩이 높이 안정화 |

### 4.3 구간 경계 신뢰도 (Confidence)

```
peak_score = fusion_score[idx]
local_mean = mean(fusion_score[idx-5:idx+5])
sharpness = (peak_score - local_mean) / (local_mean + 1e-6)
confidence = clamp(50 + sharpness*30 + peak_score*20, 20, 100)
```

- 범위: 20~100
- 피크 돌출도(prominence)와 절대 점수 반영

### 4.4 회전 시간 추정

```
turn_duration = clamp(total_walk_time × 0.15, 0.8, 2.0)
```
- 전체 보행 시간의 15%로 추정, 0.8~2.0초 범위 제한

---

## 5. 분석 지표

### 5.1 측면 영상 지표

#### 기립 분석 (stand_up)
| 지표 | 계산 | 평가 기준 |
|------|------|-----------|
| duration | stand_end - stand_start (초) | - |
| speed | (end_hip - start_hip) / duration | > 0.3: 빠름, 0.15~0.3: 보통, < 0.15: 느림 |
| height_change | 엉덩이 높이 변화량 | - |
| used_hand_support | wrist_knee_dist < 0.15 비율 >= 30% | 손 지지 사용 여부 |

#### 착석 분석 (sit_down)
| 지표 | 계산 | 평가 기준 |
|------|------|-----------|
| duration | sit_end - sit_start (초) | - |
| speed | |end_hip - start_hip| / duration | > 0.4: 빠름(주의), 0.2~0.4: 보통, < 0.2: 느림(안정적) |
| height_change | 엉덩이 높이 변화량 | - |
| used_hand_support | wrist_knee_dist < 0.15 비율 >= 30% | 손 지지 사용 여부 |

#### 반응 시간 (reaction_time)
| 파라미터 | 값 | 설명 |
|----------|-----|------|
| 감지 구간 | 영상 첫 30% | 초기 움직임 탐색 범위 |
| 기준선 | 첫 10프레임의 std dev | 정지 상태의 변동성 |
| 임계값 | 기준선 × 2.5 | 의미있는 움직임 판단 |
| 연속 프레임 | 3프레임 이상 | 노이즈 방지 |
| 스무딩 | 5-frame 이동평균 | - |
| 방법 우선순위 | combined(85%) > hip_height(70%) > leg_angle(70%) > fallback(20%) | 신뢰도 |

#### 첫걸음 시간 (first_step_time)
| 파라미터 | 값 | 설명 |
|----------|-----|------|
| 감지 구간 | 기립 완료 후 3초 | 탐색 범위 |
| ankle_x 임계 | 프레임 폭의 2% | 발목 X 이동 감지 |
| head_y 임계 | 프레임 높이의 3% | 머리 Y 이동 감지 (보조) |
| 주저함 판정 | > 2.0초 | 파킨슨 징후 가능성 |

### 5.2 정면 영상 지표

#### 어깨/골반 기울기
| 지표 | 계산 | 판정 |
|------|------|------|
| shoulder_tilt_avg | 전체 유효 프레임 어깨 기울기 평균 | > +2도: 오른쪽 높음, < -2도: 왼쪽 높음, else: 균형 |
| shoulder_tilt_max | 최대 어깨 기울기 | - |
| hip_tilt_avg | 전체 유효 프레임 골반 기울기 평균 | 동일 기준 |
| hip_tilt_max | 최대 골반 기울기 | - |

#### 체중이동 (Weight Shift)
| 지표 | 계산 | 설명 |
|------|------|------|
| lateral_sway_amplitude | std dev of lateral_offset (%) | 측방 흔들림 표준편차 |
| lateral_sway_max | max |lateral_offset| (%) | 최대 측방 편위 |
| sway_frequency | zero-crossings / sec (Hz) | 흔들림 주파수 |
| cop_trajectory | 50-point 샘플링 {time, x_offset} | 압력중심 궤적 |

**체중이동 평가 기준**:

| amplitude | max | 판정 |
|-----------|-----|------|
| < 1.0% | < 3.0% | 안정적 |
| < 2.5% | - | 약간의 불균형 |
| >= 2.5% | - | 불균형 주의 |

#### 기울기 이상치 캡처 (Deviation)
| 파라미터 | 값 | 설명 |
|----------|-----|------|
| 일반 구간 임계 | 5도 | DEVIATION_THRESHOLD |
| 회전 구간 임계 | 15도 | TURN_DEVIATION_THRESHOLD |
| 심각도 분류 | > 15도: severe, > 10도: moderate, <= 10도: mild | - |
| 샘플링 | 1초 간격 (구간 내 최악값) | 과도한 캡처 방지 |
| 최대 캡처 | 10 프레임 | - |

---

## 6. TUG 총점 평가

### 6.1 평가 척도

| 총 소요 시간 | 등급 | 판정 |
|-------------|------|------|
| < 10초 | normal | 정상 |
| 10~20초 | good | 양호 |
| 20~30초 | caution | 주의 |
| > 30초 | risk | 낙상 위험 |

**보행 속도**: walk_speed = 6.0m / total_time (m/s)

---

## 7. 시각화 및 프레임 캡처

### 7.1 구간별 색상

| 구간 | 색상 (BGR) | 용도 |
|------|-----------|------|
| stand_up | 보라 (128,0,128) | 기립 구간 |
| walk_out | 파랑 (255,0,0) | 전방 보행 |
| turn | 노랑 (0,255,255) | 회전 |
| walk_back | 초록 (0,255,0) | 복귀 보행 |
| sit_down | 분홍 (203,192,255) | 착석 구간 |

### 7.2 클립 및 캡처 설정

- 구간별 클립: 시작 1.5초 전 ~ 1.0초 후 패딩
- 코덱: avc1 (fallback: mp4v)
- 썸네일: 첫 프레임 base64 JPEG (quality=85)
- 기울기 이상치: 어깨/골반 연결선 + 호(arc) + 각도 텍스트 시각화

---

## 8. 질환별 분석 프로파일 시스템

iTUG_MediaPipe_Guide.docx 문서 기반으로, 환자 진단명에 따라 TUG 분석 파라미터와 추가 임상 변수를 자동 조정하는 시스템.

참고문헌:
- Ortega-Bastidas P et al. (2023) Sensors, 23(7):3426
- Zampieri C et al. (2010) J Neuroeng Rehabil, 7:32
- Abdollahi M et al. (2024) Bioengineering, 11(4):349

### 8.1 프로파일 구조

```
DiseaseProfile
├── name: str                    # 프로파일 키 (예: "parkinsons")
├── display_name: str            # 표시명 (예: "파킨슨병")
├── keywords: List[str]          # 진단명 매칭 키워드 (한글/영문)
├── gait: GaitProfile            # 10MWT 파라미터 오버라이드
├── tug: TUGProfile              # TUG 파라미터 오버라이드
├── clinical_flags: ClinicalFlags # 추가 임상 변수 측정 플래그
└── description: str             # 프로파일 설명
```

### 8.2 지원 질환 (9개 프로파일)

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

### 8.3 질환별 TUG 파라미터 오버라이드

| 파라미터 | 기본 | 파킨슨 | 뇌졸중 | MS | 척수손상 | 뇌성마비 | 슬관절OA | 고관절OA | 낙상위험 |
|----------|------|--------|--------|-----|---------|---------|---------|---------|---------|
| sitting_angle | 120 | 110 | 115 | 118 | 125 | 110 | 115 | 118 | 118 |
| standing_angle | 160 | 155 | 150 | 155 | 145 | 140 | 150 | 155 | 158 |
| upright_torso | 75 | 60 | 65 | 70 | 65 | 55 | 70 | 68 | 72 |
| hand_support | 0.15 | 0.18 | 0.20 | 0.17 | 0.25 | 0.22 | 0.20 | 0.20 | 0.18 |
| deviation | 5.0 | 4.0 | 8.0 | 7.0 | 6.0 | 8.0 | 5.0 | 5.0 | 5.0 |
| turn_deviation | 15.0 | 12.0 | 18.0 | 18.0 | 16.0 | 18.0 | 15.0 | 15.0 | 15.0 |
| min_facing_ratio | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 |

**파라미터 조정 근거**:
- **파킨슨**: 서동(bradykinesia)으로 전방 굴곡 자세 → upright_torso=60, 경직으로 측방 흔들림 적음 → deviation=4.0
- **뇌졸중**: 편마비로 기울기 큼 → deviation=8.0, 불완전 신전 → standing_angle=150
- **척수손상**: 경직으로 깊이 못 앉음 → sitting_angle=125, 보조기구 사용 빈번 → hand_support=0.25
- **뇌성마비**: 심한 전방 굴곡 → upright_torso=55, 불완전 신전 → standing_angle=140

### 8.4 질환별 추가 임상 변수 플래그 (ClinicalFlags)

| 플래그 | 파킨슨 | 뇌졸중 | MS | 척수손상 | 뇌성마비 | 슬관절OA | 고관절OA | 낙상위험 |
|--------|--------|--------|-----|---------|---------|---------|---------|---------|
| arm_swing | ★★★ | ★★☆ | - | - | - | - | - | - |
| turn_velocity | ★★★ | ★★★ | - | - | - | ★★☆ | - | - |
| trunk_angular_vel | ★★★ | ★★☆ | ★★☆ | ★★☆ | ★★☆ | - | ★★☆ | ★★☆ |
| cadence | ★★☆ | - | ★★☆ | - | - | - | - | ★★☆ |
| joint_rom | - | - | ★★☆ | ★★☆ | ★★☆ | ★★★ | ★★★ | - |
| foot_clearance | ★★☆ | - | - | - | - | ★★☆ | - | - |
| step_asymmetry | - | ★★★ | - | ★★☆ | ★★☆ | - | - | ★★☆ |
| sist_jerk | ★★☆ | ★★☆ | - | - | - | - | ★★☆ | ★★☆ |

### 8.5 진단명 매칭 알고리즘

```python
def resolve_profile(diagnosis: str) -> DiseaseProfile:
    # 1. None 또는 빈 문자열 → default
    # 2. 각 프로파일의 keywords 순회
    # 3. keyword.lower() in diagnosis.lower() → 매칭
    # 4. 매칭 실패 → default
```

---

## 9. 질환별 추가 임상 변수 상세

질환 프로파일의 `ClinicalFlags`에 따라 조건부로 계산되는 추가 변수. 기존 `_extract_side_frame_data`에서 추출한 프레임 데이터를 활용.

### 9.1 추가 추출 데이터 (frame_data 확장)

| 필드 | 랜드마크 | 용도 |
|------|---------|------|
| `left_wrist_y` / `right_wrist_y` | Wrist #15, #16 y | Arm swing 속도 |
| `left_foot_y` / `right_foot_y` | Foot Index #31, #32 y | Foot clearance |
| `left_ankle_y` / `right_ankle_y` | Ankle #27, #28 y | Cadence, Step asymmetry |
| `left_knee_angle` / `right_knee_angle` | Hip-Knee-Ankle 3점 각도 | Knee ROM |
| `left_hip_angle` / `right_hip_angle` | Shoulder-Hip-Knee 3점 각도 | Hip ROM |

### 9.2 Peak Arm Swing Velocity (팔 흔들기 속도)

- **임상 의의**: 파킨슨 초기 최민감 변수 (★★★), 뇌졸중 좌우 비대칭
- **계산 구간**: walk_out + walk_back
- **방법**: Wrist y좌표 → `np.gradient` × fps → 상위 10% 평균
- **출력**:
  - `left_peak_velocity` (px/s): 왼쪽 팔 피크 속도
  - `right_peak_velocity` (px/s): 오른쪽 팔 피크 속도
  - `asymmetry_ratio` (%): |L-R| / max(L,R) × 100

### 9.3 Peak Turn Velocity (회전 최대 각속도)

- **임상 의의**: 파킨슨/뇌졸중 핵심 (★★★), 뇌졸중 회전 시간 31% 지연
- **계산 구간**: turn phase
- **방법**: shoulder_direction → `np.gradient` × fps × (180/π)
- **출력**:
  - `peak_velocity_dps` (°/s): 최대 회전 각속도
  - `mean_velocity_dps` (°/s): 평균 회전 각속도
  - `turn_duration` (s): 회전 소요 시간

### 9.4 Trunk Angular Velocity (체간 각속도)

- **임상 의의**: 낙상 예측 최강 변수 (★★★), SiSt amplitude
- **계산 구간**: stand_up (SiSt), sit_down (StSi) 각각
- **방법**: torso_angle → `np.gradient` × fps
- **출력** (sist / stsi 각각):
  - `peak_angular_vel` (°/s): 최대 체간 각속도
  - `mean_angular_vel` (°/s): 평균 체간 각속도

### 9.5 Cadence (분당 걸음수)

- **임상 의의**: 파킨슨 보행 리듬 이상 (★★☆)
- **계산 구간**: walk_out + walk_back
- **방법**: Ankle y좌표 평균 → 5-frame 스무딩 → local maxima (heel strike) 카운트
  - prominence > 0.3 × std 필터로 노이즈 제거
- **출력**:
  - `steps_per_minute`: 분당 걸음수
  - `step_count`: 총 걸음수
  - `walk_duration_sec`: 보행 시간

### 9.6 Foot Clearance (발 높이)

- **임상 의의**: 파킨슨 shuffling 반영 (★★☆), 발이 지면에 가까울수록 위험
- **계산 구간**: walk_out + walk_back
- **방법**: Foot Index y좌표 → baseline(95 percentile) - y = clearance → swing phase(>0) 통계
- **출력**:
  - `mean_clearance_px` (px): 평균 발 높이
  - `min_clearance_px` (px): 최소 발 높이
  - `max_clearance_px` (px): 최대 발 높이

### 9.7 Step Asymmetry (좌우 보폭 비대칭)

- **임상 의의**: 뇌졸중 핵심 (★★★), ML pelvic displacement 낙상 예측인자 (IQR-OR=5.28-10.29)
- **계산 구간**: walk_out + walk_back
- **방법**: L/R Ankle y좌표 → 5-frame 스무딩 → 각각 heel strike 카운트 → 비대칭 비율
  - `asymmetry = |L_count - R_count| / (L_count + R_count) × 100`
- **출력**:
  - `asymmetry_pct` (%): 비대칭 비율
  - `left_step_count`: 왼발 걸음수
  - `right_step_count`: 오른발 걸음수

### 9.8 SiSt/StSi Jerk (기립/착석 부드러움)

- **임상 의의**: 낙상 위험 변수 (★★☆), 높은 jerk = 불안정 동작
- **계산 구간**: stand_up (SiSt), sit_down (StSi) 각각
- **방법**: Hip y좌표 → 1차 미분(velocity) → 2차 미분(acceleration) → 3차 미분(jerk) → RMS
  - `smoothness_score = max(0, 100 - jerk_rms / 100)` (0~100)
- **출력** (sist / stsi 각각):
  - `jerk_rms` (px/s³): Jerk RMS 값
  - `smoothness_score` (0~100): 동작 부드러움 점수

### 9.9 Joint ROM (관절 가동범위)

- **임상 의의**: 슬관절 OA (★★★), 고관절 OA (★★★)
- **계산 구간**: walk_out + walk_back
- **방법**:
  - Knee ROM: Hip-Knee-Ankle 3점 각도 → max - min (보행 중 굴곡-신전 범위)
  - Hip ROM: Shoulder-Hip-Knee 3점 각도 → max - min
- **출력**:
  - `knee_rom`: { left, right, mean } (°)
  - `hip_rom`: { left, right, mean } (°)

---

## 10. 데이터 흐름

```
환자 DB (diagnosis)
  ↓
tests.py: patient.get("diagnosis")
  ↓
resolve_profile(diagnosis) → DiseaseProfile
  ↓
TUGAnalyzer(disease_profile=profile)
  ├── __init__: TUGProfile 파라미터 오버라이드
  ├── _extract_side_frame_data: 추가 데이터 추출
  ├── _analyze_side_video: _calculate_clinical_variables 호출
  │     ├── _calc_arm_swing
  │     ├── _calc_peak_turn_velocity
  │     ├── _calc_trunk_angular_vel
  │     ├── _calc_cadence
  │     ├── _calc_foot_clearance
  │     ├── _calc_step_asymmetry
  │     ├── _calc_sist_jerk
  │     └── _calc_joint_rom
  └── 결과 dict에 포함:
        ├── disease_profile: "parkinsons"
        ├── disease_profile_display: "파킨슨병"
        └── clinical_variables: { arm_swing: {...}, ... }
```

---

## 11. 분석 검증 결과

### 11.1 테스트 환경

- **영상**: 4세트 듀얼 영상 (측면 Side + 정면 Front)
- **촬영 장소**: 실내 복도
- **피험자 키**: 170cm (기본값)
- **분석기**: TUGAnalyzer (MediaPipe Pose Heavy, model_complexity=2)

### 11.2 측정 결과

| 세트 | TUG 시간 | 보행 속도 | 평가 | 신뢰도 |
|------|----------|-----------|------|--------|
| TUG_1 | **12.05s** | 0.50 m/s | good (양호) | **100/100** |
| TUG_2 | **12.71s** | 0.47 m/s | good (양호) | **100/100** |
| TUG_3 | **16.29s** | 0.37 m/s | good (양호) | **100/100** |
| TUG_4 | **19.01s** | 0.32 m/s | good (양호) | **100/100** |

### 11.3 5단계(Phase) 시간 분석

| 세트 | stand_up | walk_out | turn | walk_back | sit_down |
|------|----------|----------|------|-----------|----------|
| TUG_1 | 2.17s | 4.52s | 1.12s | 3.70s | 0.54s |
| TUG_2 | 2.32s | 4.25s | 1.47s | 4.08s | 0.58s |
| TUG_3 | 5.22s | 4.37s | 1.60s | 4.72s | 0.38s |
| TUG_4 | 1.76s | 6.32s | 2.00s | 8.29s | 0.63s |

### 11.4 정면 영상 기울기 분석

| 세트 | 어깨 기울기 평균 | 골반 기울기 평균 | 판정 |
|------|-----------------|-----------------|------|
| TUG_1 | 0.7° | 0.3° | 균형 |
| TUG_2 | 0.1° | 0.5° | 균형 |
| TUG_3 | 2.0° | 3.7° | 약간의 골반 기울기 |
| TUG_4 | 3.5° | 4.5° | 어깨/골반 기울기 주의 |

### 11.5 검증 요약

- **4/4 세트 분석 성공** (Side + Front 듀얼 분석)
- 전체 세트 신뢰도 **100/100** 달성
- TUG 시간 범위: 12.05s ~ 19.01s (모두 10~20초 "양호" 범위)
- 5단계 구간 감지 정상 작동 (다중 신호 융합 방식)
- 정면 영상 기울기 분석 정상 작동 (어깨/골반 기울기 측정)
