# TUG (Timed Up and Go) 분석 시스템 PRD

## 문서 정보

| 항목 | 내용 |
|------|------|
| 버전 | 2.0.0 |
| 최종 업데이트 | 2026-02-23 |
| 상태 | 구현 완료 (현재 코드 기준 문서화) |
| 대상 파일 | `backend/analysis/tug_analyzer.py`, `backend/analysis/disease_profiles.py`, `backend/app/routers/tug_realtime.py` |

---

## 목차

1. [개요](#1-개요)
2. [듀얼 카메라 아키텍처](#2-듀얼-카메라-아키텍처)
3. [MediaPipe 설정 및 랜드마크](#3-mediapipe-설정-및-랜드마크)
4. [임계값 및 파라미터](#4-임계값-및-파라미터)
5. [TUG 5단계 Phase 감지](#5-tug-5단계-phase-감지)
6. [측면 영상 분석 지표](#6-측면-영상-분석-지표)
7. [정면 영상 분석 지표](#7-정면-영상-분석-지표)
8. [질환별 프로파일 시스템](#8-질환별-프로파일-시스템)
9. [질환별 추가 임상 변수](#9-질환별-추가-임상-변수)
10. [TUG 총점 평가](#10-tug-총점-평가)
11. [시각화 및 프레임 캡처](#11-시각화-및-프레임-캡처)
12. [실시간 TUG 분석 (WebSocket)](#12-실시간-tug-분석-websocket)
13. [3D 포즈 뷰어](#13-3d-포즈-뷰어)
14. [API 명세](#14-api-명세)
15. [데이터베이스](#15-데이터베이스)
16. [프론트엔드 UI](#16-프론트엔드-ui)
17. [출력 데이터 구조](#17-출력-데이터-구조)
18. [검증 결과](#18-검증-결과)

---

## 1. 개요

### 1.1 검사 소개

TUG(Timed Up and Go) 검사는 의자에서 일어나 3m 걷고, 180도 회전 후 돌아와 다시 앉는 동작의 소요 시간을 측정하는 표준 임상 기능 평가입니다.

### 1.2 시스템 특징

- **듀얼 카메라**: 측면(side) + 정면(front) 영상 동시 분석
- **5단계 자동 감지**: 다중 신호 융합(Multi-Signal Fusion) 방식
- **질환별 프로파일**: 9개 질환 맞춤 파라미터 자동 조정
- **8개 추가 임상 변수**: 질환 플래그에 따라 조건부 계산
- **실시간 분석**: 브라우저 MediaPipe.js → WebSocket → 서버 분석
- **3D 시각화**: React Three Fiber 기반 스켈레톤 애니메이션

### 1.3 TUG 동작 흐름

```
   의자                    3m 지점
    ┃                        ┃
    ┃  ① 기립(stand_up)      ┃
    ┃  ② 전방보행(walk_out) →┃
    ┃                        ┃ ③ 회전(turn) 180°
    ┃← ④ 복귀보행(walk_back) ┃
    ┃  ⑤ 착석(sit_down)      ┃
    ┃                        ┃
```

---

## 2. 듀얼 카메라 아키텍처

### 2.1 카메라 배치

```
          정면 카메라 (Front)
              ↓
    ┌─────────────────┐
    │                 │
    │   3m 보행 구간   │
    │                 │
    └─────────────────┘
              │
         측면 카메라 (Side) →
```

### 2.2 카메라별 분석 역할

| 역할 | 측면 카메라 (Side) | 정면 카메라 (Front) |
|------|-------------------|-------------------|
| 기립/착석 | 다리 각도, 엉덩이 높이, 손 지지 | - |
| 보행 | 보행 속도, 팔 흔들기, 발 높이 | - |
| 회전 | 어깨 방향 변화 | - |
| 기울기 | - | 어깨/골반 기울기 |
| 체중이동 | - | 측방 흔들림, CoP 궤적 |
| 자세 이상치 | - | 기울기 이상치 프레임 캡처 |

### 2.3 분석 처리 흐름

```
듀얼 영상 업로드
├─ _analyze_side_video()   [진행률 45%]
│   ├─ 프레임별 포즈 추출
│   ├─ 5단계 Phase 감지
│   ├─ 기립/착석 분석
│   ├─ 반응시간/첫걸음 시간
│   ├─ 임상 변수 계산
│   ├─ 오버레이 영상 생성
│   └─ Phase 프레임/클립 캡처
│
├─ _analyze_front_video()  [진행률 35%]
│   ├─ 프레임별 기울기 추출
│   ├─ 어깨/골반 기울기 통계
│   ├─ 체중이동 분석
│   ├─ 기울기 이상치 캡처
│   └─ 오버레이 영상 생성
│
└─ _merge_results()        [진행률 20%]
    ├─ 측면 + 정면 결과 병합
    ├─ 총 시간/속도/평가 산출
    └─ DB 저장
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
| `enable_segmentation` | False | 세그멘테이션 비활성화 |

### 3.2 사용 랜드마크

| 부위 | 인덱스 | 용도 |
|------|--------|------|
| NOSE | 0 | head_y (기립/착석 속도) |
| LEFT/RIGHT_SHOULDER | 11, 12 | 어깨 기울기, 회전 방향 |
| LEFT/RIGHT_WRIST | 15, 16 | 손 지지 감지, 팔 흔들기 |
| LEFT/RIGHT_HIP | 23, 24 | 골반 기울기, 엉덩이 높이 |
| LEFT/RIGHT_KNEE | 25, 26 | 다리 각도 |
| LEFT/RIGHT_ANKLE | 27, 28 | 다리 각도, 첫걸음 감지 |
| LEFT/RIGHT_HEEL | 29, 30 | 발 위치 (체중이동) |
| LEFT/RIGHT_FOOT_INDEX | 31, 32 | 발 위치 (체중이동), Foot clearance |

### 3.3 프레임별 추출 데이터 (`_extract_side_frame_data`)

| 필드 | 계산 | 용도 |
|------|------|------|
| `leg_angle` | Hip-Knee-Ankle 3점 각도 (좌우 평균, °) | 앉음/선 자세 판별 |
| `hip_y` | avg(hip_y) 픽셀 좌표 | 기립/착석 속도 |
| `hip_height_normalized` | 0~1 (1=서있음, 0=앉음) | 융합 점수 |
| `shoulder_direction` | atan2(R_shoulder - L_shoulder) 라디안 | 회전 감지 |
| `head_y` | nose_y 픽셀 좌표 | 기립/착석 속도 |
| `torso_angle` | hip-shoulder 벡터 각도 (90°=직립) | 직립 판별 |
| `wrist_knee_distance` | 정규화 손목-무릎 거리 | 손 지지 감지 |
| `ankle_x` | avg(ankle_x) 정규화 | 첫걸음 감지 |
| `left/right_ankle_x/y` | 각 발목 좌표 | Cadence, Step asymmetry |
| `left/right_knee_angle` | Hip-Knee-Ankle 3점 각도 | Joint ROM |
| `left/right_hip_angle` | Shoulder-Hip-Knee 3점 각도 | Joint ROM |
| `left/right_wrist_y` | 손목 Y좌표 | Arm swing |
| `left/right_foot_y` | Foot Index Y좌표 | Foot clearance |

---

## 4. 임계값 및 파라미터

### 4.1 자세 판단 임계값 (측면 영상)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SITTING_ANGLE_THRESHOLD` | 120° | 다리 각도 ≤ 120° → 앉은 자세 |
| `STANDING_ANGLE_THRESHOLD` | 160° | 다리 각도 ≥ 160° → 선 자세 |
| `UPRIGHT_TORSO_THRESHOLD` | 75° | 상체 각도 ≥ 75° → 직립 |
| `HAND_SUPPORT_THRESHOLD` | 0.15 | 손목-무릎 정규화 거리 < 0.15 → 손 지지 |
| 손 지지 판정 비율 | 30% | 해당 구간 프레임 중 30% 이상이면 "손 지지 사용" |

### 4.2 기울기 분석 임계값 (정면 영상)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `TILT_ANGLE_CLAMP` | ±25° | 회전 왜곡 방지 최대 기울기 |
| `DEVIATION_THRESHOLD` | 5.0° | 일반 보행 구간 기울기 이상치 기준 |
| `TURN_DEVIATION_THRESHOLD` | 15.0° | 회전 구간 기울기 이상치 기준 (더 관대) |
| `MIN_FACING_RATIO` | 0.03 | 어깨/골반 폭 ≥ 프레임 폭의 3% → 정면 |
| `CLAMP_LIMIT` | 24.0° | ±25° 근처 값 무시 (회전 왜곡 판정) |

### 4.3 신호 처리

| 처리 | 파라미터 | 설명 |
|------|----------|------|
| 이동평균 | window = min(15, n/10), 최소 3 | leg_angle, head_y, torso_angle에 적용 |
| 속도 계산 | 5-frame 커널 스무딩 후 `np.gradient × fps` | 단위: °/sec 또는 normalized/sec |
| 정규화 | (x - min) / (max - min) | 융합 점수용 0~1 범위 변환 |

---

## 5. TUG 5단계 Phase 감지

### 5.1 단계 정의

```
1. stand_up  : 앉은 자세 → 선 자세 (다리각도 120° → 160°)
2. walk_out  : 기립 완료 → 회전 지점 (전방 3m)
3. turn      : 180° 회전 (어깨 방향 최대 변화)
4. walk_back : 회전 완료 → 착석 시작 (복귀 3m)
5. sit_down  : 선 자세 → 앉은 자세 (다리각도 160° → 120°)
```

### 5.2 구간 경계 감지: 다중 신호 융합 (Multi-Signal Fusion)

각 구간 경계를 단일 임계값이 아닌 **여러 신호의 가중 합산 점수**로 감지합니다.

#### stand_start (기립 시작)

| 신호 | 가중치 | 설명 |
|------|--------|------|
| `leg_angle_velocity` | 35% | 다리 각도 증가 속도 |
| `head_y_velocity` | 30% | 머리 상승 속도 |
| `torso_angle_velocity` | 20% | 상체 펴지는 속도 |
| `hip_height_velocity` | 15% | 엉덩이 상승 속도 |

#### stand_end (기립 완료)

| 신호 | 가중치 | 설명 |
|------|--------|------|
| `leg_angle_level` | 30% | 다리 각도 ≥ 160° 도달 |
| `torso_angle_level` | 30% | 상체 각도 ≥ 75° 도달 |
| `hip_stability` | 25% | 엉덩이 높이 안정화 (1/\|속도\|) |
| `head_stability` | 15% | 머리 높이 안정화 (1/\|속도\|) |

#### turn (회전 감지)

| 신호 | 가중치 | 설명 |
|------|--------|------|
| `shoulder_direction_velocity` | 50% | 어깨 방향 변화 최대 |
| `hip_stability` | 20% | 엉덩이 높이 안정 |
| `leg_stability` | 30% | 다리 각도 안정 |

#### sit_start (착석 시작)

| 신호 | 가중치 | 설명 |
|------|--------|------|
| `leg_angle_velocity` | 35% | 다리 각도 감소 속도 (음수) |
| `head_y_velocity` | 30% | 머리 하강 속도 |
| `torso_angle_velocity` | 20% | 상체 구부러지는 속도 |
| `hip_height_velocity` | 15% | 엉덩이 하강 속도 |

#### sit_end (착석 완료)

| 신호 | 가중치 | 설명 |
|------|--------|------|
| `leg_angle_low` | 50% | 다리 각도 ≤ 120° |
| `hip_stability` | 50% | 엉덩이 높이 안정화 |

### 5.3 Phase 감지 메서드 상세

#### `_find_stand_up_start()`
- 엉덩이 높이 상승 + 다리 각도 증가의 초기 지점 탐색
- 융합 점수 + 각도 속도 + 엉덩이 기준선으로 종합 판단
- 가장 이른 시점의 안정적인 상승 시작점 반환

#### `_find_stand_up_end()`
- 조건: `leg_angle ≥ 160°` AND `torso_angle ≥ 75°` AND 안정화
- 다중 신호 합의 (융합 + 각도 + 토르소)
- 후보 인덱스의 중앙값으로 이상치 방지

#### `_find_turn_point()`
- 어깨 방향 속도의 피크 탐색
- 피크의 30% 지점까지 역추적하여 회전 시작점 결정
- 방향 변화 = atan2(shoulder_y/x)

#### `_find_sit_down_start()` & `_find_sit_down_end()`
- 기립의 역과정 (각도 역전)
- 엉덩이 높이 안정화: baseline ± 2σ 임계값
- sit_down_end: 3-프레임 연속 안정성 확인

### 5.4 대칭 보정

```
walk_back이 walk_out의 25% 미만이면:
  → turn_start를 앞으로 조정 (walk_back ≈ walk_out 원칙)
  → 3m + 3m = 6m 총 보행 거리
```

### 5.5 구간 경계 신뢰도 (Confidence)

```python
peak_score = fusion_score[idx]
local_mean = mean(fusion_score[idx-5:idx+5])
sharpness = (peak_score - local_mean) / (local_mean + 1e-6)
confidence = clamp(50 + sharpness*30 + peak_score*20, 20, 100)
```

- 범위: 20~100
- 피크 돌출도(prominence)와 절대 점수 반영

### 5.6 회전 시간 추정

```python
turn_duration = clamp(total_walk_time × 0.15, 0.8, 2.0)
```

- 전체 보행 시간의 15%로 추정
- 0.8~2.0초 범위 제한

---

## 6. 측면 영상 분석 지표

### 6.1 기립 분석 (stand_up)

| 지표 | 계산 | 평가 기준 |
|------|------|-----------|
| `duration` | stand_end - stand_start (초) | - |
| `speed` | (end_hip - start_hip) / duration | > 0.3: 빠름, 0.15~0.3: 보통, < 0.15: 느림 |
| `height_change` | 엉덩이 높이 변화량 (정규화 0~1) | - |
| `used_hand_support` | wrist_knee_dist < 0.15 비율 ≥ 30% | 손 지지 사용 여부 |

### 6.2 착석 분석 (sit_down)

| 지표 | 계산 | 평가 기준 |
|------|------|-----------|
| `duration` | sit_end - sit_start (초) | - |
| `speed` | \|end_hip - start_hip\| / duration | > 0.4: 빠름(주의), 0.2~0.4: 보통, < 0.2: 느림(안정) |
| `height_change` | 엉덩이 높이 변화량 | - |
| `used_hand_support` | wrist_knee_dist < 0.15 비율 ≥ 30% | 손 지지 사용 여부 |

### 6.3 반응 시간 (reaction_time)

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| 감지 구간 | 영상 첫 30% | 초기 움직임 탐색 범위 |
| 기준선 | 첫 10프레임의 std dev | 정지 상태의 변동성 |
| 임계값 (기본) | 기준선 × 2.5 | 의미있는 움직임 판단 |
| 임계값 (완화) | 기준선 × 1.8 | 폴백 시 완화된 기준 |
| 연속 프레임 | 3프레임 이상 | 노이즈 방지 |
| 스무딩 | 5-frame 이동평균 | - |

**감지 방법 우선순위:**

| 순서 | 방법 | 신뢰도 |
|------|------|--------|
| 1 | combined (hip_height + leg_angle 동시 감지) | 85% |
| 2 | hip_height 단독 | 70% |
| 3 | leg_angle 단독 | 70% |
| 4 | lenient (완화 임계값 1.8σ, 2-프레임) | 50% |
| 5 | fallback (t=0 가정) | 20% |

### 6.4 첫걸음 시간 (first_step_time)

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| 감지 구간 | 기립 완료 후 3초 | 탐색 범위 |
| ankle_x 임계 | 프레임 폭의 2% (0.02) | 발목 X 이동 감지 |
| head_y 임계 | 프레임 높이의 3% (0.03) | 머리 Y 이동 감지 (보조) |
| 연속 프레임 | 3프레임 이상 | 확인 조건 |
| 주저함 판정 | > 2.0초 | 파킨슨 징후 가능성 |

**감지 방법:**

| 순서 | 방법 | 신뢰도 |
|------|------|--------|
| 1 | ankle_displacement (발목 X좌표 변위) | 75% |
| 2 | head_displacement (머리 Y좌표 변위) | 60% |
| 3 | no_data (데이터 부족) | 20% |

---

## 7. 정면 영상 분석 지표

### 7.1 기울기 데이터 추출 (`_extract_tilt_data`)

| 필드 | 계산 | 설명 |
|------|------|------|
| `shoulder_tilt` | atan2(-dy, \|dx\|) × (180/π), ±25° 클램핑 | 어깨 기울기 |
| `hip_tilt` | 동일 방식 (골반) | 골반 기울기 |
| `facing_camera` | 어깨 폭 / 프레임 폭 ≥ 0.03 | 정면 향함 여부 |
| `cop_x` | avg(left_foot_x, right_foot_x) | 압력중심 X좌표 |
| `lateral_offset` | (cop_x - frame_center) / frame_width × 100 | 측방 편위 (%) |

### 7.2 어깨/골반 기울기 통계

| 지표 | 계산 | 판정 기준 |
|------|------|-----------|
| `shoulder_tilt_avg` | 유효 프레임(facing=true) 평균 | > +2°: 오른쪽 높음, < -2°: 왼쪽 높음, else: 균형 |
| `shoulder_tilt_max` | 최대 절대값 | - |
| `hip_tilt_avg` | 동일 | 동일 기준 |
| `hip_tilt_max` | 최대 절대값 | - |

### 7.3 체중이동 분석 (Weight Shift)

| 지표 | 계산 | 설명 |
|------|------|------|
| `lateral_sway_amplitude` | std(lateral_offset) (%) | 측방 흔들림 표준편차 |
| `lateral_sway_max` | max(\|lateral_offset\|) (%) | 최대 측방 편위 |
| `sway_frequency` | zero-crossings / 2 / duration (Hz) | 흔들림 주파수 |
| `cop_trajectory` | 50-point 샘플링 {time, x_offset} | 압력중심 궤적 |
| `standup_weight_shift` | 첫 20% 프레임의 평균 편위 방향 | 기립 시 체중 쏠림 |

**체중이동 평가 기준:**

| amplitude | max | 판정 |
|-----------|-----|------|
| < 1.0% | < 3.0% | 안정적 (stable) |
| < 2.5% | - | 약간의 불균형 (mild imbalance) |
| ≥ 2.5% | - | 불균형 주의 (significant imbalance) |

### 7.4 기울기 이상치 캡처 (Deviation)

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| 일반 구간 임계 | 5° | DEVIATION_THRESHOLD |
| 회전 구간 임계 | 15° | TURN_DEVIATION_THRESHOLD (더 관대) |
| 심각도 분류 | > 15°: severe, > 10°: moderate, ≤ 10°: mild | 3단계 |
| 샘플링 | 1초 간격 (구간 내 최악값) | 과도한 캡처 방지 |
| 최대 캡처 | 10 프레임 | 저장 용량 제한 |
| 클램프 필터 | \|tilt\| ≥ 24° → 무시 | 회전 왜곡 판정 |

**캡처 시각화:**
- 어깨/골반 연결선 렌더링
- 호(arc) 표시로 기울기 각도 시각화
- 각도 텍스트 오버레이

---

## 8. 질환별 프로파일 시스템

### 8.1 프로파일 구조

```
DiseaseProfile
├── name: str                    # 프로파일 키
├── display_name: str            # 표시명
├── keywords: List[str]          # 진단명 매칭 키워드
├── gait: GaitProfile            # 10MWT 파라미터
├── tug: TUGProfile              # TUG 파라미터 오버라이드
├── clinical_flags: ClinicalFlags # 추가 임상 변수 플래그
└── description: str             # 설명
```

### 8.2 지원 질환 (9개)

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
| `sitting_angle` | 120° | 110° | 115° | 118° | 125° | 110° | 115° | 118° | 118° |
| `standing_angle` | 160° | 155° | 150° | 155° | 145° | 140° | 150° | 155° | 158° |
| `upright_torso` | 75° | 60° | 65° | 70° | 65° | 55° | 70° | 68° | 72° |
| `hand_support` | 0.15 | 0.18 | 0.20 | 0.17 | 0.25 | 0.22 | 0.20 | 0.20 | 0.18 |
| `deviation` | 5.0° | 4.0° | 8.0° | 7.0° | 6.0° | 8.0° | 5.0° | 5.0° | 5.0° |
| `turn_deviation` | 15.0° | 12.0° | 18.0° | 18.0° | 16.0° | 18.0° | 15.0° | 15.0° | 15.0° |
| `min_facing_ratio` | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 |

**파라미터 조정 근거:**
- **파킨슨**: 서동(bradykinesia)으로 전방 굴곡 자세 → `upright_torso=60°`, 경직으로 측방 흔들림 적음 → `deviation=4.0°`
- **뇌졸중**: 편마비로 기울기 큼 → `deviation=8.0°`, 불완전 신전 → `standing_angle=150°`
- **척수손상**: 경직으로 깊이 못 앉음 → `sitting_angle=125°`, 보조기구 빈번 → `hand_support=0.25`
- **뇌성마비**: 심한 전방 굴곡 → `upright_torso=55°`, 불완전 신전 → `standing_angle=140°`

### 8.4 진단명 매칭 알고리즘

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

## 9. 질환별 추가 임상 변수

### 9.1 질환별 활성화 플래그

| 플래그 | 파킨슨 | 뇌졸중 | MS | 척수손상 | 뇌성마비 | 슬관절OA | 고관절OA | 낙상위험 |
|--------|--------|--------|-----|---------|---------|---------|---------|---------|
| `arm_swing` | ★★★ | ★★☆ | - | - | - | - | - | - |
| `turn_velocity` | ★★★ | ★★★ | - | - | - | ★★☆ | - | - |
| `trunk_angular_vel` | ★★★ | ★★☆ | ★★☆ | ★★☆ | ★★☆ | - | ★★☆ | ★★☆ |
| `cadence` | ★★☆ | - | ★★☆ | - | - | - | - | ★★☆ |
| `joint_rom` | - | - | ★★☆ | ★★☆ | ★★☆ | ★★★ | ★★★ | - |
| `foot_clearance` | ★★☆ | - | - | - | - | ★★☆ | - | - |
| `step_asymmetry` | - | ★★★ | - | ★★☆ | ★★☆ | - | - | ★★☆ |
| `sist_jerk` | ★★☆ | ★★☆ | - | - | - | - | ★★☆ | ★★☆ |

### 9.2 Peak Arm Swing Velocity (팔 흔들기 속도)

```
임상 의의: 파킨슨 초기 최민감 변수 (★★★), 뇌졸중 좌우 비대칭
계산 구간: walk_out + walk_back
방법: Wrist y좌표 → np.gradient × fps → 상위 10% 평균

출력:
  left_peak_velocity (px/s)    : 왼쪽 팔 피크 속도
  right_peak_velocity (px/s)   : 오른쪽 팔 피크 속도
  asymmetry_ratio (%)          : |L-R| / max(L,R) × 100
```

### 9.3 Peak Turn Velocity (회전 최대 각속도)

```
임상 의의: 파킨슨/뇌졸중 핵심 (★★★), 뇌졸중 회전 시간 31% 지연
계산 구간: turn phase
방법: shoulder_direction → np.gradient × fps × (180/π)

출력:
  peak_velocity_dps (°/s)      : 최대 회전 각속도
  mean_velocity_dps (°/s)      : 평균 회전 각속도
  turn_duration (s)            : 회전 소요 시간
```

### 9.4 Trunk Angular Velocity (체간 각속도)

```
임상 의의: 낙상 예측 최강 변수 (★★★), SiSt amplitude
계산 구간: stand_up (SiSt), sit_down (StSi) 각각
방법: torso_angle → np.gradient × fps

출력 (sist / stsi 각각):
  peak_angular_vel (°/s)       : 최대 체간 각속도
  mean_angular_vel (°/s)       : 평균 체간 각속도
```

### 9.5 Cadence (분당 걸음수)

```
임상 의의: 파킨슨 보행 리듬 이상 (★★☆)
계산 구간: walk_out + walk_back
방법: Ankle y좌표 평균 → 5-frame 스무딩 → local maxima (heel strike) 카운트
  prominence > 0.3 × std 필터로 노이즈 제거

출력:
  steps_per_minute             : 분당 걸음수
  step_count                   : 총 걸음수
  walk_duration_sec            : 보행 시간

참고: 코드에 존재하나 TUG 분석에서는 현재 스킵됨 (10MWT용)
```

### 9.6 Foot Clearance (발 높이)

```
임상 의의: 파킨슨 shuffling 반영 (★★☆), 낮을수록 위험
계산 구간: walk_out + walk_back
방법: Foot Index y좌표 → baseline(95th percentile) - y = clearance → swing phase(>0) 통계

출력:
  mean_clearance_px (px)       : 평균 발 높이
  min_clearance_px (px)        : 최소 발 높이
  max_clearance_px (px)        : 최대 발 높이
```

### 9.7 Step Asymmetry (좌우 보폭 비대칭)

```
임상 의의: 뇌졸중 핵심 (★★★), ML pelvic displacement 낙상 예측인자 (IQR-OR=5.28~10.29)
계산 구간: walk_out + walk_back
방법: L/R Ankle y좌표 → 5-frame 스무딩 → 각각 heel strike 카운트

출력:
  asymmetry_pct (%)            : |L_count - R_count| / (L_count + R_count) × 100
  left_step_count              : 왼발 걸음수
  right_step_count             : 오른발 걸음수
```

### 9.8 SiSt/StSi Jerk (기립/착석 부드러움)

```
임상 의의: 낙상 위험 변수 (★★☆), 높은 jerk = 불안정 동작
계산 구간: stand_up (SiSt), sit_down (StSi) 각각
방법: Hip y좌표 → 1차 미분(velocity) → 2차 미분(acceleration) → 3차 미분(jerk) → RMS
  smoothness_score = max(0, 100 - jerk_rms / 100) (0~100)

출력 (sist / stsi 각각):
  jerk_rms (px/s³)             : Jerk RMS 값
  smoothness_score (0~100)     : 동작 부드러움 점수
```

### 9.9 Joint ROM (관절 가동범위)

```
임상 의의: 슬관절 OA (★★★), 고관절 OA (★★★)
계산 구간: walk_out + walk_back
방법:
  Knee ROM: Hip-Knee-Ankle 3점 각도 → max - min (보행 중 굴곡-신전 범위)
  Hip ROM: Shoulder-Hip-Knee 3점 각도 → max - min

출력:
  knee_rom: { left, right, mean } (°)
  hip_rom: { left, right, mean } (°)
```

---

## 10. TUG 총점 평가

### 10.1 평가 척도

| 총 소요 시간 | 등급 | 판정 | 색상 |
|-------------|------|------|------|
| < 10초 | normal | 정상 | 초록 |
| 10~20초 | good | 양호 | 파랑 |
| 20~30초 | caution | 주의 | 노랑 |
| > 30초 | risk | 낙상 위험 | 빨강 |

### 10.2 보행 속도

```
walk_speed = 6.0m / total_time (m/s)
  ※ TUG 총 보행 거리 = 3m + 3m = 6m
```

---

## 11. 시각화 및 프레임 캡처

### 11.1 구간별 색상

| 구간 | BGR (백엔드) | HEX (프론트엔드) | 용도 |
|------|-------------|-----------------|------|
| stand_up | (128,0,128) | #A855F7 보라 | 기립 구간 |
| walk_out | (255,0,0) | #3B82F6 파랑 | 전방 보행 |
| turn | (0,255,255) | #EAB308 노랑 | 회전 |
| walk_back | (0,255,0) | #22C55E 초록 | 복귀 보행 |
| sit_down | (203,192,255) | #EC4899 분홍 | 착석 구간 |

### 11.2 Phase 프레임 캡처

| 구간 | 캡처 시점 | 설명 |
|------|----------|------|
| stand_up | 구간 60% 지점 | 확실한 상승 순간 |
| walk_out | 구간 40% 지점 | 안정적 보행 |
| turn | 구간 50% 지점 | 최대 회전 |
| walk_back | 구간 40% 지점 | 안정적 보행 |
| sit_down | 구간 40% 지점 | 초기 하강 |

**캡처 데이터:**
```json
{
  "frame": "base64_jpg",
  "time": 3.5,
  "frame_number": 105,
  "label": "기립 (Stand Up)",
  "criteria": "다리 각도 120° → 160° 변화",
  "description": "의자에서 일어나는 동작",
  "key_points": ["다리 각도 증가", "엉덩이 높이 상승"],
  "duration": 2.17
}
```

### 11.3 Phase 클립

- **패딩**: 시작 0.5초 전 ~ 0.5초 후
- **코덱**: H.264 (avc1), 폴백 mp4v
- **파일명**: `{base}_phase_{phase_name}.mp4`
- **브라우저 호환**: 자동재생, 루프, 음소거

### 11.4 포즈 오버레이 영상

```
색상:
  좌측 (홀수): 시안 (255,150,0)
  우측 (짝수): 오렌지 (0,128,255)
  중앙: 회색 (200,200,200)

대상: 신체 랜드마크만 (11-32), 얼굴 제외
연결선: 22개 신체 스켈레톤
선 두께: 4px, 원 반지름: 8px
visibility 임계값: > 20%
```

### 11.5 기울기 이상치 시각화 (정면)

```
어깨/골반 연결선 렌더링
호(arc) 표시로 기울기 각도 시각화
각도 텍스트 오버레이 (°)
심각도별 색상: 경미=노랑, 보통=주황, 심함=빨강
```

---

## 12. 실시간 TUG 분석 (WebSocket)

### 12.1 시스템 아키텍처

```
브라우저                                     서버
┌─────────────────┐                ┌──────────────────────┐
│ MediaPipe.js    │                │ RealtimeTUGSession   │
│ (15fps 추출)    │                │                      │
│                 │   WebSocket    │ process_frame()      │
│ landmarks ──────┼───────────────►│ ├─ 랜드마크 → 관절각도 │
│ worldLandmarks  │                │ ├─ Phase 상태머신     │
│                 │◄───────────────┼─┤ phase_update 반환   │
│ 2D 스켈레톤     │  phase_update  │ └─ 3D 프레임 축적     │
│ 3D 스켈레톤     │                │                      │
│ 타이머/Phase    │                │ finalize()           │
└─────────────────┘                │ ├─ 전체 Phase 재분석  │
                                   │ ├─ DB 저장           │
                                   │ └─ 최종 결과 반환     │
                                   └──────────────────────┘
```

### 12.2 WebSocket 엔드포인트

**`/ws/tug-realtime/{client_id}`**

### 12.3 메시지 프로토콜

#### Client → Server

| 메시지 | 페이로드 | 설명 |
|--------|---------|------|
| `start_test` | `{patient_id, user_id}` | 검사 시작 |
| `frame_data` | `{landmarks, timestamp, world_landmarks}` | 프레임 전송 (20fps 제한) |
| `stop_test` | `{}` | 검사 종료 |
| `ping` | `{}` | 하트비트 (15초 간격) |

#### Server → Client

| 메시지 | 페이로드 | 설명 |
|--------|---------|------|
| `test_started` | `{}` | 검사 시작 확인 |
| `phase_update` | `{current_phase, phase_label, elapsed_time, leg_angle, hip_height}` | Phase 상태 업데이트 |
| `phase_transition` | `{from_phase, to_phase, transitions[]}` | Phase 전환 알림 |
| `test_completed` | `{test_id, total_time_seconds, walk_speed_mps, assessment, phases}` | 최종 결과 |

### 12.4 Phase 상태머신 (실시간)

```
stand_up → walk_out → turn → walk_back → sit_down

감지 조건:
  standing: leg_angle ≥ 160° AND torso_angle ≥ 75°
  turn: shoulder direction 변화 > 0.5 rad (15-프레임 윈도우)
  sitting: leg_angle < 120°
```

### 12.5 실시간 테스트 흐름

```
1. 환자 상세 페이지 → "실시간 TUG" 클릭
2. TUGRealtimePage 마운트
3. "카메라 시작" → MediaPipe.js 로드 + 카메라 스트리밍
4. 상태: idle → ready
5. "검사 시작" → WebSocket 연결 + start_test 전송
6. 상태: ready → testing
7. 프레임 전송 (50ms 간격, 20fps 제한)
8. phase_update/phase_transition 수신 → UI 실시간 반영
9. "검사 중지" → stop_test 전송
10. 서버: finalize() → TUGAnalyzer._detect_tug_phases() 정밀 분석
11. test_completed 수신
12. 상태: testing → completed
13. "결과 보기" → 환자 상세 페이지로 이동
```

### 12.6 3D 프레임 축적

```
world_landmarks: 매 3프레임마다 샘플링
인덱스: 11-32 (신체만, 얼굴 제외)
Phase 주석: finalize() 시 최종 Phase 타이밍으로 레이블링
```

---

## 13. 3D 포즈 뷰어

### 13.1 구현 기술

| 구성 | 기술 |
|------|------|
| 3D 렌더링 | React Three Fiber (Three.js) |
| 카메라 조작 | OrbitControls (마우스 드래그 회전, 스크롤 줌) |
| 스켈레톤 | AnimatedAnatomicalSkeleton 컴포넌트 |
| 바닥 | GridHelper (4×4, 셀 크기 0.2) |

### 13.2 기능

| 기능 | 설명 |
|------|------|
| 소스 전환 | 측면/정면 카메라 토글 |
| 재생 제어 | 재생/일시정지, 0.5x/1x/2x 속도 |
| Phase 탐색 | 이전/다음 Phase 건너뛰기 |
| 타임라인 | 색상별 Phase 바, 클릭으로 탐색 |
| Phase 범례 | 5개 Phase 색상 + 이름 |
| 프레임 정보 | 프레임 카운터 + 조작 안내 |

### 13.3 스켈레톤 렌더링

```
랜드마크: 11-32 (어깨, 팔꿈치, 손목, 엉덩이, 무릎, 발목)
관절: 구형 노드
연결선: 원통형 뼈대
색상: 현재 Phase에 따라 변경
프레임 보간: 재생 시 부드러운 전환
```

---

## 14. API 명세

### 14.1 듀얼 영상 업로드 (TUG)

**POST** `/api/tests/{patient_id}/upload-tug`

```
Body: multipart/form-data
  side_video: 측면 영상 (UploadFile)
  front_video: 정면 영상 (UploadFile)

Headers:
  X-User-Id: 치료사 ID
  X-User-Role: "therapist"
  X-User-Approved: "true"

Response: 202 Accepted
  {
    "file_id": "uuid",
    "message": "TUG 듀얼 영상 업로드 완료. 분석이 시작되었습니다.",
    "status_endpoint": "/api/tests/status/{file_id}"
  }

파일 저장: {file_id}_side.{ext}, {file_id}_front.{ext}
```

### 14.2 분석 상태 조회

**GET** `/api/tests/status/{file_id}`

```
Response:
  {
    "status": "processing" | "completed" | "error",
    "progress": 0-100,
    "message": "현재 처리 단계",
    "current_frame": "base64 이미지 (선택)",
    "result": { ... } (completed 시에만)
  }
```

### 14.3 Phase 클립 URL

**GET** `/api/tests/{test_id}/phase-clip/{phase_name}`

```
phase_name: "stand_up" | "walk_out" | "turn" | "walk_back" | "sit_down"
Response: 영상 파일 스트리밍
```

### 14.4 기타 엔드포인트 (10MWT 공용)

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/tests/{test_id}` | 검사 결과 조회 |
| `GET /api/tests/patient/{patient_id}?test_type=TUG` | TUG 검사 목록 |
| `GET /api/tests/patient/{patient_id}/compare` | 이전 비교 |
| `GET /api/tests/patient/{patient_id}/stats?test_type=TUG` | 통계 요약 |
| `GET /api/tests/patient/{patient_id}/trends?test_type=TUG` | 추세 분석 |
| `GET /api/tests/{test_id}/pdf` | PDF 리포트 |
| `POST /api/tests/{test_id}/email` | 이메일 전송 |
| `GET /api/tests/{test_id}/ai-report` | AI 리포트 |

---

## 15. 데이터베이스

### 15.1 walk_tests 테이블 (10MWT/TUG 공용)

```sql
CREATE TABLE walk_tests (
    id TEXT PRIMARY KEY,               -- UUID
    patient_id TEXT NOT NULL,           -- FK → patients
    test_date TEXT DEFAULT CURRENT_TIMESTAMP,
    test_type TEXT DEFAULT '10MWT',     -- "10MWT" | "TUG"
    walk_time_seconds REAL NOT NULL,    -- TUG 총 소요 시간 (초)
    walk_speed_mps REAL NOT NULL,       -- 6.0 / total_time (m/s)
    video_url TEXT,                     -- /uploads/filename (측면 영상)
    analysis_data TEXT,                 -- JSON (전체 분석 결과)
    notes TEXT,                         -- 치료사 메모
    therapist_id TEXT,
    site_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);
```

### 15.2 TUG 관련 저장 필드

```
analysis_data JSON 내 TUG 전용 필드:
  - phases: {stand_up, walk_out, turn, walk_back, sit_down}
  - stand_up / sit_down: 기립/착석 상세 메트릭
  - tilt_analysis: 어깨/골반 기울기
  - weight_shift: 체중이동 분석
  - phase_frames: 5개 Phase 대표 프레임 (base64)
  - phase_clips: 5개 Phase 영상 클립 (파일명)
  - deviation_captures: 기울기 이상치 캡처
  - clinical_variables: 질환별 추가 임상 변수
  - pose_3d_frames: 3D 포즈 데이터 (측면)
  - pose_3d_frames_front: 3D 포즈 데이터 (정면)
  - side_overlay_video_filename: 측면 오버레이 영상
  - front_overlay_video_filename: 정면 오버레이 영상
  - front_video_filename: 정면 원본 영상
```

---

## 16. 프론트엔드 UI

### 16.1 TUG 결과 페이지 (TUGResult 컴포넌트)

```
┌────────────────────────────────────────────────────────┐
│  ┌─ 총 시간 + 평가 ───────────────────────────────┐   │
│  │  12.05초                              [양호]    │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  ┌─ 평가 기준 참조 ──────────────────────────────┐    │
│  │ [정상<10s] [양호 10-20s] [주의 20-30s] [위험>30s]│   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  ┌─ Phase 타임라인 바 ────────────────────────────┐   │
│  │ ▓▓▓▓│▒▒▒▒▒▒▒│░░│▒▒▒▒▒▒│▓▓│                    │   │
│  │ 기립  전방보행  회전 복귀보행 착석                │   │
│  │ 2.17s  4.52s  1.12s  3.70s 0.54s               │   │
│  │ [호버→확대, 클릭→상세]                           │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  ┌─ 선택된 Phase 상세 ───────────────────────────┐    │
│  │ [프레임/클립 이미지]  기준: 다리각도 120→160°   │   │
│  │                       시간: 2.17초              │   │
│  │                       [상세 모달 열기]           │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  ┌─ 기립/착석 분석 카드 (2열) ────────────────────┐   │
│  │ 기립              │ 착석                       │   │
│  │ 시간: 2.17s       │ 시간: 0.54s               │   │
│  │ 평가: 보통        │ 평가: 빠름(주의)           │   │
│  │ 손지지: 미사용    │ 손지지: 미사용             │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  ┌─ 반응시간 + 첫걸음 (2열) ─────────────────────┐   │
│  │ 반응시간           │ 첫걸음 시간               │   │
│  │ 0.8초 (combined)   │ 0.5초                    │   │
│  │ 신뢰도: 85%        │ 주저함: 없음             │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  ┌─ 기울기 분석 (정면 카메라) ───────────────────┐    │
│  │ 어깨: 0.7° (균형)    골반: 0.3° (균형)        │   │
│  │ 평가: 정상                                     │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  ┌─ 체중이동 분석 (TUGWeightShift) ──────────────┐   │
│  │ 진폭: 0.8%  최대: 2.1%  주파수: 1.2Hz         │   │
│  │ 방향: 균형                                     │   │
│  │ [CoP 궤적 차트]                                │   │
│  │ 평가: 안정적                                   │   │
│  └────────────────────────────────────────────────┘   │
│                                                        │
│  ┌─ Phase 캡처 그리드 (TUGPhaseFrames) ──────────┐   │
│  │ [기립] [전방] [회전] [복귀] [착석]             │   │
│  │ (썸네일 + 클릭→상세 모달)                      │   │
│  └────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

### 16.2 VideoModal (영상 모달)

```
┌────────────────────────────────────────────┐
│ [X]                                        │
│                                            │
│  [측면] [정면] [순차재생]    ← TUG 전용    │
│                                            │
│  ┌──────────────────────────────┐          │
│  │                              │          │
│  │    영상 플레이어              │          │
│  │    포즈 오버레이 토글         │          │
│  │    실시간 각도 텍스트         │          │
│  │     측면: 무릎각°│엉덩이각°  │          │
│  │     정면: 어깨기울기°│골반°   │          │
│  │                              │          │
│  └──────────────────────────────┘          │
│                                            │
│  ┌─ 동기화 차트 ─────────────────┐         │
│  │  정면: TUGAngleSyncChart      │         │
│  │    어깨(파란)/골반(초록) ±15°  │         │
│  │    ±5° 경고선, 커서 연동       │         │
│  │                               │         │
│  │  측면: TUGSideAngleSyncChart  │         │
│  │    무릎(파란)/엉덩이(주황)     │         │
│  │    60°~180° 범위              │         │
│  └───────────────────────────────┘         │
│                                            │
│  ┌─ Phase 프레임 ────────────────┐         │
│  │  TUGPhaseFrames 컴포넌트      │         │
│  └───────────────────────────────┘         │
│                                            │
│  파일 크기: 25.3MB  [다운로드]              │
└────────────────────────────────────────────┘
```

### 16.3 실시간 TUG 페이지 (TUGRealtimePage)

```
┌─────────────────────────────────────────────────────────┐
│  환자명  [← 뒤로]           ● 연결됨   [카메라시작]     │
│                              [검사시작] [검사중지]       │
├──────────────────────────────┬──────────────────────────┤
│                              │                          │
│  ┌─ 카메라 뷰 ─────────┐   │  ┌─ 3D 모델 뷰 ──────┐  │
│  │                      │   │  │                     │  │
│  │  HTML 비디오 +       │   │  │  Three.js 캔버스    │  │
│  │  MediaPipe 캔버스    │   │  │  SkeletonBody       │  │
│  │  2D 스켈레톤 오버레이│   │  │  실시간 업데이트     │  │
│  │                      │   │  │  Phase 색상 변경     │  │
│  │  FPS: 15             │   │  │                     │  │
│  │         [walk_out] ──┼───┤  │  [walk_out]         │  │
│  │                      │   │  │                     │  │
│  └──────────────────────┘   │  └─────────────────────┘  │
│                              │                          │
├──────────────────────────────┴──────────────────────────┤
│                                                         │
│  ┌─ 타이머 + Phase ─────────────────────────────────┐  │
│  │   [walk_out]     05.2초                           │  │
│  │                                                   │  │
│  │  ▓▓▓▓│▒▒▒▒▒░░░░░░░░░░░░░░░░░░                   │  │
│  │  기립  전방  (진행중...)                           │  │
│  │                                                   │  │
│  │  기립  전방보행  회전  복귀보행  착석              │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  완료 시: 총 시간 12.05초  [양호]  [결과 보기]          │
└─────────────────────────────────────────────────────────┘
```

### 16.4 기울기 이상치 캡처 (TUGDeviationCaptures)

```
필터: [전체] [어깨] [골반] [복합]

┌─────┬─────┬─────┬─────┬─────┐
│ 캡1 │ 캡2 │ 캡3 │ 캡4 │ 캡5 │
│     │     │     │     │     │
│[경미]│[보통]│[심함]│     │     │
│ 2.1s│ 4.3s│ 8.7s│     │     │
└─────┴─────┴─────┴─────┴─────┘

상세 모달:
  전체 이미지
  어깨 기울기: X° (색상: 녹≤5°, 주황 5-10°, 빨강≥10°)
  골반 기울기: Y°
  이전/다음 네비게이션
```

### 16.5 체중이동 시각화 (TUGWeightShift)

```
┌─ 통계 카드 (3열) ──────────────────────┐
│ 진폭: 0.8%  │ 최대: 2.1%  │ 주파수: 1.2Hz │
├────────────────────────────────────────┤
│ 방향: [L ────|──── R]  균형              │
├────────────────────────────────────────┤
│ ┌─ CoP 궤적 (SVG) ──────────────────┐ │
│ │ L ─────────────────────────────── │ │
│ │      ╱╲    ╱╲                     │ │
│ │ 0 ──╱──╲──╱──╲──── (기준선)       │ │
│ │    ╱    ╲╱    ╲                   │ │
│ │ R ──────────────── t →            │ │
│ └────────────────────────────────────┘ │
│ 평가: 안정적                            │
└────────────────────────────────────────┘
```

---

## 17. 출력 데이터 구조

### 17.1 분석 결과 JSON (analyze_dual_video 반환)

```json
{
  "test_type": "TUG",
  "total_time_seconds": 12.05,
  "walk_speed_mps": 0.50,
  "assessment": "good",

  "fps": 30,
  "total_frames": 362,
  "frames_analyzed": 350,
  "patient_height_cm": 170,
  "model": "MediaPipe Pose Heavy (complexity=2)",

  "phases": {
    "stand_up": { "start_time": 0.0, "end_time": 2.17, "duration": 2.17 },
    "walk_out": { "start_time": 2.17, "end_time": 6.69, "duration": 4.52 },
    "turn": { "start_time": 6.69, "end_time": 7.81, "duration": 1.12 },
    "walk_back": { "start_time": 7.81, "end_time": 11.51, "duration": 3.70 },
    "sit_down": { "start_time": 11.51, "end_time": 12.05, "duration": 0.54 }
  },

  "stand_up": {
    "duration": 2.17,
    "speed": 0.25,
    "height_change": 0.54,
    "start_time": 0.0,
    "end_time": 2.17,
    "assessment": "보통",
    "used_hand_support": false
  },

  "sit_down": {
    "duration": 0.54,
    "speed": 0.45,
    "height_change": 0.24,
    "start_time": 11.51,
    "end_time": 12.05,
    "assessment": "빠름 (주의)",
    "used_hand_support": false
  },

  "reaction_time": {
    "reaction_time": 0.8,
    "detection_method": "combined",
    "confidence": 85,
    "first_movement_time": 0.8
  },

  "first_step_time": {
    "time_to_first_step": 0.5,
    "detection_method": "ankle_displacement",
    "hesitation_detected": false,
    "confidence": 75
  },

  "tilt_analysis": {
    "shoulder_tilt_avg": 0.7,
    "shoulder_tilt_max": 4.2,
    "shoulder_tilt_direction": "균형",
    "hip_tilt_avg": 0.3,
    "hip_tilt_max": 3.1,
    "hip_tilt_direction": "균형",
    "assessment": "정상"
  },

  "weight_shift": {
    "lateral_sway_amplitude": 0.8,
    "lateral_sway_max": 2.1,
    "sway_frequency": 1.2,
    "cop_trajectory": [{ "time": 0.0, "x_offset": 0.1 }, ...],
    "standup_weight_shift": "balanced",
    "assessment": "안정적"
  },

  "deviation_captures": [
    {
      "frame": "base64_jpg",
      "time": 4.3,
      "shoulder_angle": 6.5,
      "hip_angle": 3.2,
      "type": "shoulder",
      "severity": "moderate"
    }
  ],

  "phase_frames": {
    "stand_up": { "frame": "base64", "time": 1.3, ... },
    "walk_out": { ... },
    "turn": { ... },
    "walk_back": { ... },
    "sit_down": { ... }
  },

  "phase_clips": {
    "stand_up": { "clip_filename": "xxx_phase_stand_up.mp4", ... },
    ...
  },

  "angle_data": [
    { "time": 0.0, "shoulder_tilt": 0.5, "hip_tilt": 0.2 },
    ...
  ],

  "side_angle_data": [
    { "time": 0.0, "knee_angle": 95.0, "hip_angle": 85.0, ... },
    ...
  ],

  "side_overlay_video_filename": "xxx_side_overlay.mp4",
  "front_overlay_video_filename": "xxx_front_overlay.mp4",
  "front_video_filename": "xxx_front.mp4",

  "disease_profile": "default",
  "disease_profile_display": "기본",

  "clinical_variables": {
    "arm_swing": {
      "left_peak_velocity": 120.5,
      "right_peak_velocity": 115.3,
      "asymmetry_ratio": 4.3,
      "unit": "px/s"
    },
    "peak_turn_velocity": {
      "peak_velocity_dps": 180.5,
      "mean_velocity_dps": 95.2,
      "turn_duration": 1.12,
      "unit": "°/s"
    },
    "trunk_angular_velocity": {
      "sist": { "peak_angular_vel": 45.2, "mean_angular_vel": 22.1, "unit": "°/s" },
      "stsi": { "peak_angular_vel": 50.8, "mean_angular_vel": 25.3, "unit": "°/s" }
    },
    "foot_clearance": {
      "mean_clearance_px": 15.3,
      "min_clearance_px": 8.1,
      "max_clearance_px": 25.7,
      "unit": "px"
    },
    "step_asymmetry": {
      "asymmetry_pct": 5.2,
      "left_step_count": 10,
      "right_step_count": 9
    },
    "sist_jerk": {
      "sist": { "jerk_rms": 1250.5, "smoothness_score": 87.5, "unit": "px/s³" },
      "stsi": { "jerk_rms": 1450.2, "smoothness_score": 85.5, "unit": "px/s³" }
    },
    "joint_rom": {
      "knee_rom": { "left": 55.2, "right": 52.8, "mean": 54.0, "unit": "°" },
      "hip_rom": { "left": 35.1, "right": 33.8, "mean": 34.5, "unit": "°" }
    }
  },

  "pose_3d_frames": [
    { "time": 0.1, "phase": "stand_up", "landmarks": [[0.01, -0.15, 0.09], ...] },
    ...
  ],

  "pose_3d_frames_front": [
    { "time": 0.1, "phase": "stand_up", "landmarks": [[0.01, -0.15, 0.09], ...] },
    ...
  ]
}
```

---

## 18. 검증 결과

### 18.1 테스트 환경

| 항목 | 내용 |
|------|------|
| 영상 | 4세트 듀얼 영상 (Side + Front) |
| 촬영 장소 | 실내 복도 |
| 피험자 키 | 170cm (기본값) |
| 분석기 | TUGAnalyzer (MediaPipe Pose Heavy, complexity=2) |

### 18.2 측정 결과

| 세트 | TUG 시간 | 보행 속도 | 평가 | 신뢰도 |
|------|----------|-----------|------|--------|
| TUG_1 | **12.05s** | 0.50 m/s | good (양호) | **100/100** |
| TUG_2 | **12.71s** | 0.47 m/s | good (양호) | **100/100** |
| TUG_3 | **16.29s** | 0.37 m/s | good (양호) | **100/100** |
| TUG_4 | **19.01s** | 0.32 m/s | good (양호) | **100/100** |

### 18.3 5단계 Phase 시간 분석

| 세트 | stand_up | walk_out | turn | walk_back | sit_down |
|------|----------|----------|------|-----------|----------|
| TUG_1 | 2.17s | 4.52s | 1.12s | 3.70s | 0.54s |
| TUG_2 | 2.32s | 4.25s | 1.47s | 4.08s | 0.58s |
| TUG_3 | 5.22s | 4.37s | 1.60s | 4.72s | 0.38s |
| TUG_4 | 1.76s | 6.32s | 2.00s | 8.29s | 0.63s |

### 18.4 정면 영상 기울기 분석

| 세트 | 어깨 기울기 평균 | 골반 기울기 평균 | 판정 |
|------|-----------------|-----------------|------|
| TUG_1 | 0.7° | 0.3° | 균형 |
| TUG_2 | 0.1° | 0.5° | 균형 |
| TUG_3 | 2.0° | 3.7° | 약간의 골반 기울기 |
| TUG_4 | 3.5° | 4.5° | 어깨/골반 기울기 주의 |

### 18.5 검증 요약

- **4/4 세트 분석 성공** (Side + Front 듀얼 분석)
- 전체 세트 신뢰도 **100/100** 달성
- TUG 시간 범위: 12.05s ~ 19.01s (모두 10~20초 "양호" 범위)
- 5단계 구간 감지 정상 작동 (다중 신호 융합 방식)
- 정면 영상 기울기 분석 정상 작동

---

## 부록: 미구현 항목 (PRD v1 대비)

### A.1 백엔드

| 항목 | 상태 | 비고 |
|------|------|------|
| Cadence (TUG용) | ⚠️ 부분 | 코드 존재하나 TUG에서 스킵됨 |
| Phase 클립 패딩 | ⚠️ 차이 | PRD: 1.5초/1.0초, 구현: 0.5초/0.5초 |

### A.2 프론트엔드

| 항목 | 상태 | 비고 |
|------|------|------|
| Clinical Variables 표시 UI | ❌ 미구현 | 백엔드 계산값을 표시하는 컴포넌트 없음 |
| Disease Profile 표시 UI | ❌ 미구현 | 적용된 프로파일명 표시 없음 |
| TUGAnalysisData 타입 clinical_variables 필드 | ❌ 미정의 | types/index.ts에 누락 |

### A.3 참고문헌

- Ortega-Bastidas P et al. (2023) Sensors, 23(7):3426
- Zampieri C et al. (2010) J Neuroeng Rehabil, 7:32
- Abdollahi M et al. (2024) Bioengineering, 11(4):349
