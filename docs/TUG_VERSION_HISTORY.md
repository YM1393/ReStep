# TUG (Timed Up and Go) Analyzer 버전별 변경 이력

## 개요

TUG 분석기는 **MediaPipe Pose Heavy**를 사용하여 의자 기립 → 3m 보행 → 180° 회전 → 복귀 보행 → 착석의 5단계를 자동 감지하고 소요 시간을 측정합니다. 초기 단일 카메라 + 단순 임계값 방식에서, 현재는 듀얼 카메라 + 다중 신호 융합(Multi-Signal Fusion) + 질환별 프로파일 + 8개 임상 변수까지 확장되었습니다.

---

## 통합 개선 결과 요약 


| 항목 | 초기 (v1) | 현재 (최종) |
|------|-----------|-------------|
| 카메라 | 단일 (측면) | **듀얼** (측면 + 정면) |
| Phase 감지 | 단순 임계값 | **다중 신호 융합 (5종 신호 가중합)** |
| 자세 판단 신호 | leg_angle만 | leg_angle + hip_height + torso_angle + head_y + shoulder_direction |
| 회전 감지 | 어깨 방향 변화 max | **융합 점수 피크 + 역방향 탐색** |
| 기울기 분석 | 없음 | **어깨/골반 기울기 + 체중이동 + 이상치 캡처** |
| 질환별 프로파일 | 없음 | **9개 질환 맞춤 파라미터** |
| 추가 임상 변수 | 없음 | **8개** (Arm Swing, Turn Velocity 등) |
| 반응시간/첫걸음 | 없음 | **multi-method 감지** |
| 3D 포즈 | 없음 | **매 3프레임 월드 좌표 + Phase 어노테이션** |
| 실시간 분석 | 없음 | **WebSocket + MediaPipe.js** |
| 신뢰도 점수 | 없음 | **Phase별 20~100점** |
| 대칭성 보정 | 없음 | **walk_out/walk_back 비율 자동 보정** |
| 검증 결과 | - | **4세트 100/100 신뢰도** |

---

## 버전별 변경 이력

### v1: 단일 카메라 + 단순 임계값

#### 구조
- 단일 측면 카메라만 사용
- `analyze()` 메서드로 단일 영상 분석

#### Phase 감지
- **leg_angle** (Hip-Knee-Ankle 3점 각도)만 사용
- 앉음 판단: `leg_angle ≤ 120°`
- 선 자세 판단: `leg_angle ≥ 160°`
- 누적 임계값 기반으로 시작/끝 탐색

#### 회전 감지
- 어깨 방향(`shoulder_direction`) 변화량 최대 지점
- 5프레임 윈도우 기반 before/after 차이

#### 한계
- leg_angle이 측면 시점에서 일시적으로 변동 (허리 숙이기 → 160°+ 오탐)
- 정면 기울기/체중이동 분석 불가
- 고정 임계값으로 다양한 환자 패턴 대응 불가

---

### v2: 상체 수직도 + 손 지지 감지 추가

#### 개선점
- **torso_angle** (상체 수직도) 추가: 90°에 가까울수록 직립
  - `UPRIGHT_TORSO_THRESHOLD = 75°` → 상체가 펴져야 기립 완료
- **wrist_knee_distance** 추가: 손으로 무릎을 짚고 일어나는지 감지
  - `HAND_SUPPORT_THRESHOLD = 0.15` (프레임 높이 대비 정규화 거리)
  - 해당 구간의 30% 이상 프레임에서 감지되면 "손 지지 사용"
- **hip_height_normalized** (정규화 엉덩이 높이) 추가: 0~1 (1=서있음)

#### 기립 완료 조건 강화
```
v1: leg_angle ≥ 160°
v2: leg_angle ≥ 160° AND torso_angle ≥ 75°
```

#### 한계
- 여전히 단일 신호 기반 임계값 판단
- 노이즈 스파이크에 취약

---

### v3: 다중 신호 융합 (Multi-Signal Fusion) 도입

#### 핵심 변경: 단일 임계값 → 가중 융합 점수

5종 신호를 추출하고 경계 유형별로 가중 합산:

```
leg_angle, hip_height, torso_angle, head_y, shoulder_direction
→ 5-frame 스무딩 → np.gradient × fps → 정규화(0~1) → 가중 합산
```

#### 경계별 가중치

| 경계 | leg_angle | head_y | torso_angle | hip_height | shoulder_dir |
|------|-----------|--------|-------------|------------|--------------|
| **stand_start** | velocity 35% | velocity 30% | velocity 20% | velocity 15% | - |
| **stand_end** | level 30% | stability 15% | level 30% | stability 25% | - |
| **turn** | stability 30% | - | - | stability 20% | velocity **50%** |
| **sit_start** | velocity 35% | velocity 30% | velocity 20% | velocity 15% | - |
| **sit_end** | low_level 50% | - | - | stability 50% | - |

#### 개선 효과
- 단일 신호 오탐 방지 (여러 신호가 동시에 변해야 경계 판정)
- 노이즈에 강건한 감지

---

### v4: 엉덩이 높이 기반 검증 강화

#### 문제
- 측면 시점에서 허리를 숙이기만 해도 leg_angle이 160°+로 보이는 문제
- 실제로 엉덩이가 올라가지 않았는데 "기립 완료"로 오판

#### 해결: 엉덩이 높이 상승/하강 검증

**기립 시작 검증**:
```python
hip_baseline = 초반 안정 구간 평균
rise_threshold = hip_baseline + max(2.5σ, 0.02)
→ 3프레임 연속 rise_threshold 초과 시 기립 시작
```

**기립 완료 검증**:
```python
hip_standing_threshold = hip_baseline + (hip_max - hip_baseline) × 0.6
→ 엉덩이가 60% 이상 올라가야 실제 기립 완료
```

**착석 시작 검증**:
```python
standing_baseline = 서 있는 구간 평균
drop_threshold = standing_baseline - max(2.5σ, 0.03)
→ 뒤에서부터 탐색하여 처음 drop_threshold 이하로 떨어지는 지점
```

**착석 완료 검증**:
```python
hip_sitting_level = 초기 앉은 높이 (처음 20프레임)
settle_threshold = hip_sitting_level + max(2.0σ, 0.02)
→ 3프레임 연속 settle_threshold 이하면 착석 완료
```

#### 다중 신호 결합 전략
- 엉덩이 높이와 leg_angle 결과가 10프레임 이내면 보수적(더 늦은 시점) 선택
- 10프레임 이상 차이나면 엉덩이 높이 우선 (측면 leg_angle 오탐 방지)

---

### v5: 듀얼 카메라 + 정면 영상 분석

#### 핵심 변경: 단일 → 듀얼 카메라

```
analyze_dual_video(side_video, front_video)
├─ _analyze_side_video()  [45%] → 보행, 기립/착석, Phase
├─ _analyze_front_video() [35%] → 기울기, 체중이동
└─ _merge_results()       [20%] → 통합
```

#### 정면 영상 분석 추가

**어깨/골반 기울기**:
```python
tilt = atan2(-dy, abs(dx))   # abs(dx)로 카메라 방향 무관
→ ±25° 클램핑 (회전 왜곡 방지)
→ facing_camera 판정: shoulder_ratio > 3% 또는 hip_ratio > 3%
```

**체중이동 (Weight Shift)**:
- CoP (압력중심) 근사: 발 랜드마크 6개의 x좌표 평균
- `lateral_offset = (cop_x - body_midline_x) / frame_width × 100 (%)`
- `sway_amplitude`: lateral_offset의 표준편차
- `sway_frequency`: 영점 교차 횟수 기반 (Hz)
- `cop_trajectory`: 50포인트 샘플링

**기울기 이상치 캡처**:
- 일반 구간: `> 5.0°` 초과 시 캡처
- 회전 구간: `> 15.0°` 초과 시 캡처 (더 관대)
- `±24°` 근처 값 제외 (회전 왜곡)
- 1초 간격 샘플링, 최대 10프레임
- 심각도: severe(>15°), moderate(>10°), mild(≤10°)

---

### v6: 반응시간 + 첫걸음 시간 + Phase 신뢰도

#### 반응시간 (Reaction Time)

영상 시작 ~ 첫 의미있는 움직임까지의 시간

```
1. 초반 30% 구간에서 탐색
2. hip_height, leg_angle → 5-frame 스무딩 → np.gradient
3. 기준선: 처음 10프레임 표준편차
4. 임계값: 기준선 × 2.5
5. 3프레임 연속 초과 → 움직임 감지
6. 실패 시 → 관대한 임계값(1.8배) + 2프레임으로 재시도
```

| 감지 방법 | 신뢰도 |
|----------|--------|
| combined (hip + angle) | 85% |
| hip_height만 | 70% |
| leg_angle만 | 70% |
| lenient (관대 임계값) | 50% |
| fallback | 20% |

#### 첫걸음 시간 (First Step Time)

기립 완료 ~ 첫 보행 발걸음 (파킨슨 동결보행 지표)

```
1. 기립 완료 후 3초 구간 탐색
2. ankle_x 변위 > 프레임 폭의 2% → 걸음 감지
3. ankle_x 없으면 head_y 변위 > 3%로 대체
4. 2프레임 연속 확인
5. > 2.0초면 "주저함(hesitation) 감지"
```

#### Phase 신뢰도 (Confidence)

각 Phase 경계의 감지 품질을 20~100점으로 수치화:

```python
peak_score = fusion_score[idx]
local_mean = mean(fusion_score[idx ± 5])
sharpness = (peak_score - local_mean) / (local_mean + 1e-6)
confidence = clamp(50 + sharpness × 30 + peak_score × 20, 20, 100)
```

---

### v7: 대칭성 보정 + 회전 시간 추정

#### TUG 대칭성 보정

walk_out과 walk_back은 같은 3m 거리이므로 비슷한 시간이어야 함.
회전 감지가 너무 늦으면 walk_back이 비정상적으로 짧아지는 문제 해결:

```python
if walk_back < walk_out × 0.25:  # 비정상적 비대칭
    total_moving = sit_down_start - stand_up_end
    estimated_turn = clamp(total_moving × 0.12, 0.8, 2.0)
    remaining = total_moving - estimated_turn
    walk_out = remaining × 0.55    # 나갈 때 약간 느림
    walk_back = remaining × 0.45   # 돌아올 때 약간 빠름
```

- 보정 적용 시 해당 Phase의 confidence를 60 이하로 제한

#### 회전 시간 추정
```python
turn_duration = clamp(total_walk_time × 0.15, 0.8, 2.0)
```
- 전체 보행 시간의 15%, 최소 0.8초 ~ 최대 2.0초

---

### v8: 질환별 프로파일 시스템

#### 9개 질환별 프로파일

| 프로파일 | 표시명 | 핵심 조정 사유 |
|---------|--------|---------------|
| default | 기본 | 표준 파라미터 |
| parkinsons | 파킨슨병 | 서동(bradykinesia), 전방 굴곡 자세 |
| stroke | 뇌졸중 | 편마비, 큰 기울기 |
| ms | 다발성 경화증 | 피로도, 균형 저하 |
| sci | 척수 손상 | 경직, 보조기구 사용 |
| cp | 뇌성마비 | 심한 전방 굴곡, 불완전 신전 |
| knee_oa | 슬관절 OA/TKA | 관절 가동범위 제한 |
| hip_oa | 고관절 OA/골절 | 관절 가동범위 제한 |
| fall_risk | 낙상 위험 | 균형 장애 |

#### 질환별 TUG 파라미터 오버라이드 (주요)

| 파라미터 | 기본 | 파킨슨 | 뇌졸중 | 뇌성마비 | 척수손상 |
|----------|------|--------|--------|---------|---------|
| sitting_angle | 120° | 110° | 115° | 110° | 125° |
| standing_angle | 160° | 155° | 150° | 140° | 145° |
| upright_torso | 75° | **60°** | 65° | **55°** | 65° |
| hand_support | 0.15 | 0.18 | 0.20 | 0.22 | **0.25** |
| deviation | 5.0° | **4.0°** | **8.0°** | 8.0° | 6.0° |

#### 진단명 자동 매칭
```python
resolve_profile(diagnosis="파킨슨병") → DiseaseProfile("parkinsons")
# 키워드: 파킨슨, parkinson, PD, 진전마비 등 (한글/영문)
```

---

### v9: 8개 추가 임상 변수

질환 프로파일의 `ClinicalFlags`에 따라 **조건부로 계산**되는 추가 변수:

#### 1. Peak Arm Swing Velocity (팔 흔들기 속도)
- **임상 의의**: 파킨슨 초기 최민감 변수 (★★★)
- **구간**: walk_out + walk_back
- **방법**: Wrist y좌표 → `np.gradient × fps` → 상위 10% 평균
- **출력**: left/right_peak_velocity (px/s), asymmetry_ratio (%)

#### 2. Peak Turn Velocity (회전 최대 각속도)
- **임상 의의**: 파킨슨/뇌졸중 핵심 (★★★)
- **구간**: turn phase
- **방법**: shoulder_direction → `np.gradient × fps × (180/π)`
- **출력**: peak_velocity_dps (°/s), mean_velocity_dps (°/s), turn_duration (s)

#### 3. Trunk Angular Velocity (체간 각속도)
- **임상 의의**: 낙상 예측 최강 변수 (★★★)
- **구간**: stand_up (SiSt), sit_down (StSi) 각각
- **방법**: torso_angle → `np.gradient × fps`
- **출력**: peak/mean_angular_vel (°/s) (SiSt/StSi 각각)

#### 4. Cadence (분당 걸음수)
- **임상 의의**: 파킨슨 보행 리듬 이상 (★★☆)
- **구간**: walk_out + walk_back
- **방법**: Ankle y좌표 → 5-frame 스무딩 → local maxima (heel strike)
  - prominence > 0.3 × std 필터
- **출력**: steps_per_minute, step_count, walk_duration_sec

#### 5. Foot Clearance (발 높이)
- **임상 의의**: 파킨슨 shuffling (★★☆)
- **구간**: walk_out + walk_back
- **방법**: Foot Index y좌표 → baseline(95 percentile) - y → swing phase 통계
- **출력**: mean/min/max_clearance_px (px)

#### 6. Step Asymmetry (좌우 보폭 비대칭)
- **임상 의의**: 뇌졸중 핵심 (★★★), 낙상 예측인자
- **구간**: walk_out + walk_back
- **방법**: L/R Ankle y좌표 → heel strike 카운트 → 비대칭 비율
- **출력**: asymmetry_pct (%), left/right_step_count

#### 7. SiSt/StSi Jerk (기립/착석 부드러움)
- **임상 의의**: 낙상 위험 (★★☆)
- **구간**: stand_up / sit_down 각각
- **방법**: Hip y → velocity → acceleration → jerk → RMS
  - `smoothness_score = max(0, 100 - jerk_rms / 100)`
- **출력**: jerk_rms (px/s³), smoothness_score (0~100)

#### 8. Joint ROM (관절 가동범위)
- **임상 의의**: 슬관절/고관절 OA (★★★)
- **구간**: walk_out + walk_back
- **방법**: Hip-Knee-Ankle / Shoulder-Hip-Knee 3점 각도 → max - min
- **출력**: knee_rom / hip_rom: { left, right, mean } (°)

---

### v10: 실시간 분석 + 3D 포즈 + 스톱워치 오버레이

#### 실시간 TUG 분석 (WebSocket)
- 브라우저에서 MediaPipe.js로 포즈 추출 → WebSocket → 서버 분석
- 실시간 Phase 전환 콜백 (`phase_callback`)
- 3프레임마다 포즈 오버레이 프레임 전송 (`frame_callback`)

#### 3D 포즈 데이터
- 매 3프레임마다 MediaPipe 월드 좌표 추출 (인덱스 11~32, 몸체만)
- Phase 어노테이션 추가: 각 3D 프레임에 현재 Phase 태깅
- React Three Fiber 기반 스켈레톤 애니메이션으로 시각화

#### 스톱워치 오버레이 (후처리)
- 오버레이 영상에 Phase별 타이머 UI 추가 (`add_tug_stopwatch`)
- Phase별 색상 구분 (보라/파랑/노랑/초록/분홍)
- 진행 바 + 총 시간 표시

#### Phase별 클립/캡처
- 각 Phase 전환 시점의 대표 프레임 캡처 (base64 JPEG, quality=85)
  - stand_up: 60% 지점, sit_down: 40% 지점, turn: 50% 지점
- Phase별 영상 클립 생성 (시작 1.5초 전 ~ 1.0초 후 패딩)
- 코덱: avc1 (fallback: mp4v)

---

## 감지 알고리즘 상세

### 다중 신호 융합 (Multi-Signal Fusion) 파이프라인

```
입력: 프레임별 포즈 데이터
  │
  ▼
[1단계] 신호 추출
  - leg_angle, hip_height, torso_angle, head_y, shoulder_direction
  │
  ▼
[2단계] 스무딩 + 미분
  - 5-frame 커널 이동평균
  - np.gradient × fps → 속도(velocity) 계산
  │
  ▼
[3단계] 정규화 (0~1)
  - normalize(arr) = (arr - min) / (max - min)
  │
  ▼
[4단계] 경계별 가중 합산
  - stand_start: 속도 기반 (다리+머리+상체+엉덩이 상승 속도)
  - stand_end: 수준 기반 (다리 펴짐+상체 수직+안정화)
  - turn: 어깨 방향 변화율 50% + 안정화 50%
  - sit_start: 하강 속도 기반
  - sit_end: 낮은 수준 + 안정화
  │
  ▼
[5단계] 피크 탐색 + 경계 결정
  - 융합 점수 > threshold(mean + kσ) 인 피크 탐색
  - 3프레임 연속 확인
  - 엉덩이 높이 보조 검증
  │
  ▼
[6단계] 후처리 보정
  - 대칭성 보정 (walk_out ≈ walk_back)
  - 회전 시간 추정 (전체의 15%, 0.8~2.0초)
  - Phase 순서 검증 (시간 순서 보장)
```

---

## 포즈 추정 (MediaPipe Pose Heavy)

### 모델 설정

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| model_complexity | 2 | Heavy (최고 정밀도, 33개 키포인트) |
| smooth_landmarks | True | 시간축 스무딩 |
| min_detection_confidence | 0.5 | 최소 감지 신뢰도 |
| min_tracking_confidence | 0.5 | 최소 추적 신뢰도 |

### 핵심 파생 데이터

| 데이터 | 계산 | 용도 |
|--------|------|------|
| leg_angle | Hip-Knee-Ankle 3점 각도 (좌우 평균) | 앉음/선 자세 판별 |
| hip_height_normalized | 1 - (hip_y / frame_height) | 기립/착석 속도 |
| torso_angle | hip-shoulder 벡터 수평 각도 (90°=직립) | 직립 판별 |
| shoulder_direction | atan2(R_shoulder - L_shoulder) | 회전 감지 |
| wrist_knee_distance | 손목-무릎 정규화 거리 | 손 지지 감지 |
| tilt_angle | atan2(-dy, abs(dx)) | 기울기 (카메라 방향 무관) |

### 랜드마크 가시성 최적화
- `optimize_threshold.py`로 가시성 임계값 최적화
- 현재 임계값: 0.2 (20%) - 몸체 랜드마크만 (인덱스 11~32)
- 얼굴 랜드마크(0~10) 제외, 좌/우 색상 구분 시각화
  - 왼쪽: 파란색 계열 (BGR: 255, 150, 0)
  - 오른쪽: 주황색 계열 (BGR: 0, 128, 255)
  - 중앙 연결선: 밝은 회색

---

## 지표 최적화

### 자세 판단 임계값

| 임계값 | 값 | 최적화 근거 |
|--------|-----|-------------|
| SITTING_ANGLE | 120° | Hip-Knee-Ankle 각도가 120° 이하면 충분히 앉은 자세 |
| STANDING_ANGLE | 160° | 완전 신전(180°)이 아닌 160°에서 판정 (노인/환자 고려) |
| UPRIGHT_TORSO | 75° | 90°(완전 수직) 대신 75°로 관대하게 (전방 굴곡 환자 고려) |
| HAND_SUPPORT | 0.15 | 프레임 높이 대비 15% 이내 → 손이 무릎 근처 |

### 기울기 분석 임계값

| 임계값 | 값 | 최적화 근거 |
|--------|-----|-------------|
| DEVIATION | 5.0° | 일반 보행 중 5° 초과 기울기는 이상치 |
| TURN_DEVIATION | 15.0° | 회전 중 15° 초과만 이상치 (회전 시 자연스러운 기울기 허용) |
| TILT_CLAMP | ±25° | 이 이상은 부분 회전에 의한 왜곡 |
| CLAMP_LIMIT | 24.0° | ±25° 근처 값은 왜곡으로 판단하여 제외 |
| MIN_FACING_RATIO | 0.03 | 어깨/골반 폭이 프레임 폭의 3% 미만이면 옆/뒤를 향한 것 |

### 체중이동 평가 기준 (프레임 폭 대비 %)

| amplitude | max | 판정 |
|-----------|-----|------|
| < 1.0% | < 3.0% | 안정적 |
| < 2.5% | - | 약간의 불균형 |
| ≥ 2.5% | - | 불균형 주의 |

### 신호 처리 파라미터

| 처리 | 파라미터 | 적용 대상 |
|------|----------|-----------|
| 이동평균 윈도우 | min(15, n/10), 최소 3 | leg_angle, head_y, torso_angle |
| 미분 스무딩 커널 | 5-frame | 모든 속도 계산 |
| heel strike prominence | > 0.3 × std | Cadence, Step Asymmetry |
| foot clearance baseline | 95th percentile | Foot Clearance |

---

## 결과 검증

### 테스트 환경
- **영상**: 4세트 듀얼 영상 (측면 + 정면)
- **촬영 장소**: 실내 복도
- **피험자 키**: 170cm (기본값)
- **분석기**: TUGAnalyzer (MediaPipe Pose Heavy, model_complexity=2)

### TUG 시간 및 평가

| 세트 | TUG 시간 | 보행 속도 | 평가 | 신뢰도 |
|------|----------|-----------|------|--------|
| TUG_1 | **12.05s** | 0.50 m/s | good (양호) | **100/100** |
| TUG_2 | **12.71s** | 0.47 m/s | good (양호) | **100/100** |
| TUG_3 | **16.29s** | 0.37 m/s | good (양호) | **100/100** |
| TUG_4 | **19.01s** | 0.32 m/s | good (양호) | **100/100** |

### 5단계(Phase) 시간 분석

| 세트 | stand_up | walk_out | turn | walk_back | sit_down |
|------|----------|----------|------|-----------|----------|
| TUG_1 | 2.17s | 4.52s | 1.12s | 3.70s | 0.54s |
| TUG_2 | 2.32s | 4.25s | 1.47s | 4.08s | 0.58s |
| TUG_3 | 5.22s | 4.37s | 1.60s | 4.72s | 0.38s |
| TUG_4 | 1.76s | 6.32s | 2.00s | 8.29s | 0.63s |

### 정면 영상 기울기 분석

| 세트 | 어깨 기울기 평균 | 골반 기울기 평균 | 판정 |
|------|-----------------|-----------------|------|
| TUG_1 | 0.7° | 0.3° | 균형 |
| TUG_2 | 0.1° | 0.5° | 균형 |
| TUG_3 | 2.0° | 3.7° | 약간의 골반 기울기 |
| TUG_4 | 3.5° | 4.5° | 어깨/골반 기울기 주의 |

### 검증 요약

- **4/4 세트 분석 성공** (Side + Front 듀얼 분석)
- 전체 세트 신뢰도 **100/100** 달성
- TUG 시간 범위: 12.05s ~ 19.01s (모두 10~20초 "양호" 범위)
- 5단계 구간 감지 정상 작동 (다중 신호 융합)
- 정면 영상 기울기 분석 정상 작동
- walk_out vs walk_back 비율이 합리적 (TUG_1: 4.52 vs 3.70, TUG_4: 6.32 vs 8.29)

### 평가 기준 (TUG 총 시간)

| 총 소요 시간 | 등급 | 판정 |
|-------------|------|------|
| < 10초 | normal | 정상 |
| 10~20초 | good | 양호 |
| 20~30초 | caution | 주의 |
| > 30초 | risk | 낙상 위험 |

---

## 참고문헌

- Ortega-Bastidas P et al. (2023) Sensors, 23(7):3426
- Zampieri C et al. (2010) J Neuroeng Rehabil, 7:32
- Abdollahi M et al. (2024) Bioengineering, 11(4):349
