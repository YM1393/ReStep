# 분석 로직 상세 문서

## 목차
1. [10MWT 보행 분석](#1-10mwt-보행-분석)
2. [TUG 검사 분석](#2-tug-검사-분석)
3. [공통 기술 스택](#3-공통-기술-스택)

---

## 1. 10MWT 보행 분석

### 1.1 개요

10m Walk Test(10MWT)는 환자가 12m를 걸어가는 영상을 분석하여 보행 시간과 속도를 측정한다.
- 총 거리: 12m (가속 2m + 측정 10m)
- 카메라 위치: 출발점 뒤 약 14m (후방 촬영)
- 분석 파일: `backend/analysis/gait_analyzer.py`

### 1.2 핵심 원리: 1/h (역수 높이) 모델

#### 왜 pixel height가 아닌 1/h를 사용하는가?

핀홀 카메라 모델에서:
- 사람의 픽셀 높이 `h`는 실제 거리에 **반비례** → `h ∝ 1/d`
- 따라서 `1/h ∝ d` → **1/h는 실제 거리에 비례**
- `d(1/h)/dt`는 **실제 보행 속도에 비례** (거리에 무관하게 일정)

```
pixel velocity (dh/dt)  → 거리가 멀어질수록 감소 → 경계 감지에 부적합
real velocity (d(1/h)/dt) → 거리 무관하게 일정 → 정상 보행 구간 감지에 적합
```

### 1.3 분석 파이프라인

```
영상 입력
  ↓
[1단계] 프레임별 MediaPipe Pose 추론
  ├── 각 프레임에서 33개 키포인트 추출
  ├── 포즈 오버레이 영상 생성 (skeleton 그리기)
  ├── pixel_height = |nose_y - avg(ankle_y)| 계산
  └── 어깨/골반 기울기, 양측 관절 좌표 기록
  ↓
[2단계] 스무딩
  ├── 미디안 필터 (window=9) → 아웃라이어 제거
  └── 이동 평균 (window=15) → 노이즈 평활화
  ↓
[3단계] 1/h 및 실제 속도 계산
  ├── inv_h = 1 / max(smoothed_h, 1.0)
  └── real_vel = d(inv_h)/dt (인접 프레임 차분)
  ↓
[4단계] 보행 구간 감지 (_find_walk_region_real_velocity)
  ├── 양의 속도만 추출, 82번째 퍼센타일로 max_rv 산출
  ├── threshold_start = max_rv × 27%
  ├── threshold_end = threshold_start × 1.7 (종료 임계값 더 높게)
  ├── 임계값 이상 연속 구간 중 2초 이상인 것 선택
  └── 2-pass 반복 정제 (구간 내에서 임계값 재계산)
  ↓
[5단계] 2m/12m 지점 보간
  ├── inv_h_at_2m = inv_h_start + 0.60 × (inv_h_end - inv_h_start)
  ├── 선형 보간으로 정확한 time_2m 산출
  ├── time_12m = walk_end의 시간
  └── raw_walk_time = time_12m - time_2m
  ↓
[6단계] 보정 및 최종 결과
  ├── walk_time = raw_walk_time × CORRECTION_FACTOR_AWAY (2.4974)
  ├── walk_speed = 10.0 / walk_time (m/s)
  └── 임상 변수, 보행 패턴, 신뢰도 점수 산출
  ↓
[7단계] 오버레이 후처리
  └── START(2m) / FINISH(12m) 측정 라인 추가
```

### 1.4 주요 상수

| 상수 | 값 | 설명 |
|---|---|---|
| `INV_H_START_FRACTION` | 0.60 | 1/h 곡선의 60% 지점에서 측정 시작 (~7.2m) |
| `CORRECTION_FACTOR_AWAY` | 2.4974 | away 방향 보정 계수 |
| `VEL_THRESHOLD_PCT` | 27 | 최대 속도의 27%를 보행 임계값으로 사용 |
| `VEL_PERCENTILE` | 82 | 강건한 최대 속도 추정 (82번째 퍼센타일) |
| `VEL_END_FACTOR` | 1.7 | 보행 종료 임계값 = 시작 임계값 × 1.7 |
| `VEL_ITERATIVE` | True | 2-pass 반복 정제 활성화 |
| `SMOOTH_MEDIAN_WS` | 9 | 미디안 필터 윈도우 크기 |
| `SMOOTH_AVG_WS` | 15 | 이동 평균 윈도우 크기 |
| `CAMERA_DISTANCE_M` | 14.0 | 카메라~출발점 거리 |
| `MEASUREMENT_DISTANCE_M` | 10.0 | 실제 측정 거리 (2m~12m) |

### 1.5 보행 구간 감지 알고리즘 상세

```python
# 1. 양의 실제 속도만 추출하여 82번째 퍼센타일 계산
positive_vel = [v for v in real_vel if v > 0]
max_rv = np.percentile(positive_vel, 82)  # 노이즈 스파이크 방지

# 2. 비대칭 임계값 설정
threshold_start = max_rv * 0.27      # 보행 시작: 낮은 임계값
threshold_end = threshold_start * 1.7  # 보행 종료: 높은 임계값 (감속 구간 포함 방지)

# 3. 연속 구간 탐색 (최소 2초 이상)
# threshold_start 이상인 구간의 시작점 → walk_start
# threshold_end 이상인 구간의 끝점 → walk_end

# 4. 2-pass 정제: 감지된 구간 내에서 임계값 재계산
# → 더 정확한 경계 산출
```

### 1.6 2m/12m 보간 로직

카메라에서 멀어질수록 1/h가 증가한다 (1/h ∝ 거리). 보행 구간 내 1/h 변화량의 60% 지점을 2m 마크로 설정:

```
inv_h 곡선:
  ┌────────────────────────────────────┐
  │     /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾/     │
  │    /                        /      │
  │   /     60% 지점 = 2m      /       │
  │  /     ↑                  / ← 12m  │
  │ /      │                 /         │
  └────────────────────────────────────┘
    walk_start              walk_end
```

### 1.7 START/FINISH 라인 시각화

오버레이 영상에 2개의 수평선을 후처리로 추가:
- **START (2m)**: 초록색 선 - 사람의 발이 2m 지점에 있을 때의 Y 좌표
- **FINISH (12m)**: 빨간색 선 - 사람의 발이 12m 지점에 있을 때의 Y 좌표
- ankle_y를 전후 3프레임 median으로 스무딩하여 보행 바운스 제거
- 교차 시점 ±0.5초간 하이라이트 효과 (선 두께 증가)

### 1.8 신뢰도 점수 (0-100)

| 항목 | 배점 | 기준 |
|---|---|---|
| 포즈 감지율 | 30점 | ≥95%→30, ≥85%→25, ≥70%→18 |
| 보행 구간 길이 | 25점 | 5~18초→25, 3~25초→18 |
| 보행 시간 합리성 | 25점 | 4~20초→25, 2.5~30초→15 |
| 보행 속도 합리성 | 20점 | 0.5~2.0 m/s→20, 0.3~2.5→14 |

레벨: ≥90 높음 / 70~89 보통 / 50~69 낮음 / <50 매우 낮음

### 1.9 임상 변수

보행 구간 내 프레임 데이터에서 산출:
- **Cadence**: 분당 걸음수 (보행 이벤트 기반)
- **Step time**: 교대 발 접촉 간 시간
- **Stride time**: 완전한 보행 주기 시간 (좌→좌 or 우→우)
- **Step time asymmetry**: 좌/우 차이 %
- **Arm swing**: 팔 흔들림 범위 및 비대칭
- **Foot clearance**: 유각기 최소 발목 높이
- **Double support**: 양발 지지 시간
- **Stride regularity**: 보폭 간격 변동성
- **Trunk inclination**: 몸통 기울기 각도

---

## 2. TUG 검사 분석

### 2.1 개요

Timed Up and Go(TUG) 검사는 의자에서 일어나 3m 걸어간 뒤 돌아와 앉는 전체 과정을 분석한다.
- 5단계: 일어서기 → 걸어가기 → 회전 → 돌아오기 → 앉기
- 분석 파일: `backend/analysis/tug_analyzer.py`

### 2.2 분석 파이프라인

```
영상 입력
  ↓
[1단계] 프레임별 MediaPipe Pose 추론
  ├── 다리 각도 (무릎 굽힘/폄)
  ├── 머리 높이 (수직 위치)
  ├── 상체 수직도 (torso angle)
  ├── 어깨 방향 (회전 감지)
  └── 엉덩이 높이 (hip_height_normalized)
  ↓
[2단계] 신호 스무딩
  └── 이동 평균 필터 (window = min(15, n/10))
  ↓
[3단계] 다중신호 융합 점수 계산
  ├── 5개 경계 유형별 가중 융합 (stand_start, stand_end, turn, sit_start, sit_end)
  └── 각 신호를 0~1로 정규화 후 가중 합산
  ↓
[4단계] 단계 경계 감지 (엉덩이 높이 + 다리 각도 + 융합 점수)
  ├── 일어서기 시작 → 엉덩이 높이 상승 시작 + 다리 각도 증가
  ├── 일어서기 완료 → 다리 각도 ≥ 160° + 상체 ≥ 75° + 엉덩이 충분히 상승
  ├── 회전 시점 → 어깨 방향 변화 최대점
  ├── 앉기 시작 → 엉덩이 높이 하강 시작 (1차) + 다리 각도 감소 (보조)
  └── 앉기 완료 → 엉덩이가 초기 앉은 높이로 복귀 + 다리 각도 < 120°
  ↓
[5단계] 대칭성 보정
  ├── walk_out과 walk_back은 같은 3m → 비슷해야 함
  └── walk_back < walk_out × 25%이면 경계 재분배
  ↓
[6단계] 결과 산출
  ├── 단계별 시간, 신뢰도 점수
  ├── 단계 전환 대표 프레임 캡처 (단계 중간 지점)
  ├── 단계별 영상 클립 생성 (단계 전체 구간 + 앞뒤 0.5초)
  └── 평가: <10s 정상 / 10~20s 양호 / 20~30s 주의 / >30s 위험
```

### 2.3 다중신호 융합 (Fusion Score)

각 경계 유형별로 여러 신호를 가중 합산하여 하나의 점수로 만든다:

#### 일어서기 시작 (stand_start)
```
score = 0.35 × 다리각도속도 + 0.30 × 머리상승속도
      + 0.20 × 상체수직화속도 + 0.15 × 엉덩이상승속도
```

#### 일어서기 완료 (stand_end)
```
score = 0.30 × 다리각도수준 + 0.30 × 상체수직도수준
      + 0.25 × 엉덩이안정도 + 0.15 × 머리안정도
```
(안정도 = 1/|속도|, 움직임이 적을수록 높음)

#### 회전 (turn)
```
score = 0.50 × 어깨방향변화속도 + 0.20 × 엉덩이안정도
      + 0.30 × 다리안정도
```

#### 앉기 시작 (sit_start)
```
score = 0.35 × (-다리각도속도) + 0.30 × 머리하강속도
      + 0.20 × (-상체기울기속도) + 0.15 × (-엉덩이하강속도)
```

#### 앉기 완료 (sit_end)
```
score = 0.50 × (1 - 다리각도수준) + 0.50 × 엉덩이안정도
```

### 2.4 단계 경계 감지 기준

모든 경계 감지에서 **엉덩이 높이(hip_height)**를 보조/1차 신호로 활용하여,
측면 시점에서 다리 각도가 일시적으로 변동하는 오탐을 방지한다.

| 경계 | 주요 조건 | 보조 조건 | 탐색 범위 |
|---|---|---|---|
| **일어서기 시작** | fusion 피크 + 다리각도 < 145° | 엉덩이 높이 상승 시작 (기준선 + 2.5σ 초과, 3프레임 연속) | 영상 전반 40% |
| **일어서기 완료** | 다리각도 ≥ 160° + 상체 ≥ 75° | 엉덩이가 앉은→선 높이 변화량의 60% 이상 상승 | 시작점 이후 30% |
| **회전** | 어깨 방향 변화율 최대 | - | 일어서기 완료 ~ 앉기 시작 |
| **앉기 시작** | 엉덩이 높이 하강 시작 (1차) | 다리각도 < 160° (보조 검증) | 영상 후반 30% |
| **앉기 완료** | 엉덩이가 초기 앉은 높이로 복귀 (3프레임 안정) | 다리각도 < 120°, fusion 점수 | 앉기 시작 이후 |

#### 엉덩이 높이 기반 감지 상세

```python
# 일어서기 시작: 엉덩이 상승 시작점
baseline = mean(hip_heights[:30])  # 초반 안정 구간의 기준선
rise_threshold = baseline + max(std * 2.5, 0.02)
# 3프레임 연속 rise_threshold 초과 → hip_rise_start

# 일어서기 완료: 엉덩이가 충분히 올라갔는지 검증
hip_standing_threshold = hip_baseline + (hip_max - hip_baseline) * 0.6
# leg_angle ≥ 160° AND torso ≥ 75° AND hip >= threshold → 완료

# 앉기 시작: 엉덩이 하강 시작점
standing_baseline = mean(standing_region_hips)
drop_threshold = standing_baseline - max(std * 2.5, 0.03)
# 뒤에서 탐색 → drop_threshold 이하 첫 지점
# hip_drop과 angle_sit_start 중 신뢰도 높은 값 선택

# 앉기 완료: 엉덩이가 초기 앉은 높이로 복귀
settle_threshold = hip_sitting_level + max(std * 2.0, 0.02)
# 3프레임 연속 settle_threshold 이하 → 완료
# fusion/hip/angle 후보 중 중간값 선택 (극단적 오탐 방지)
```

### 2.5 주요 상수

| 상수 | 값 | 설명 |
|---|---|---|
| `SITTING_ANGLE_THRESHOLD` | 120° | 다리 각도 ≤120° = 앉은 자세 |
| `STANDING_ANGLE_THRESHOLD` | 160° | 다리 각도 ≥160° = 선 자세 |
| `UPRIGHT_TORSO_THRESHOLD` | 75° | 상체 수직도 ≥75° = 직립 (90°=완전 수직) |
| `WALK_DISTANCE_M` | 3.0 | TUG 보행 거리 (편도) |

### 2.6 대칭성 보정

TUG에서 walk_out(3m)과 walk_back(3m)은 같은 거리이므로 소요 시간이 비슷해야 한다:

```
조건: walk_out > 2초 AND walk_back < walk_out × 25%
→ 회전 시점(turn_start)이 너무 늦게 감지된 것으로 판단

보정:
  total_moving = sit_down_start - stand_up_end
  estimated_turn = min(2.0, max(0.8, total_moving × 12%))
  remaining = total_moving - estimated_turn
  walk_out = remaining × 55%
  walk_back = remaining × 45%

  → 보정된 단계의 신뢰도 ≤ 60으로 제한
```

### 2.7 단계 전환 프레임 캡처

각 단계의 **대표적 순간**을 캡처 (단순 시작 시점이 아님):

| 단계 | 캡처 시점 | 이유 |
|---|---|---|
| 일어서기 (stand_up) | 60% 지점 | 일어서는 동작이 가장 명확 |
| 걸어가기 (walk_out) | 40% 지점 | 안정적인 보행 자세 |
| 회전 (turn) | 50% 지점 | 최대 회전 각도 |
| 돌아오기 (walk_back) | 40% 지점 | 안정적인 보행 자세 |
| 앉기 (sit_down) | 40% 지점 | 앉는 동작 초반이 명확 |

### 2.8 단계별 영상 클립

각 단계의 **전체 구간**을 포함하는 MP4 클립을 생성:
- 클립 범위: `start_time - 0.5초` ~ `end_time + 0.5초` (앞뒤 0.5초 패딩)
- 포즈 오버레이(skeleton)와 함께 렌더링
- 첫 프레임을 썸네일로 저장

```
기존 방식 (폐기):
  transition_time(시작점) ± 패딩 → 단계 중간에서 클립 끊김

현재 방식:
  start_time ~ end_time 전체 + 앞뒤 0.5초 → 동작 전체 포함
```

### 2.9 기울기 계산

어깨/골반 기울기는 카메라 방향에 무관하게 수평 편차만 측정:

```python
angle = atan2(-dy, abs(dx))  # abs(dx)로 카메라 방향 무관
# 양수: 오른쪽이 높음, 음수: 왼쪽이 높음
# ±25° 범위로 제한 (이 이상은 회전에 의한 왜곡)
```

### 2.10 TUG 평가 기준

| 시간 | 등급 | 의미 |
|---|---|---|
| < 10초 | 정상 (Normal) | 독립적 이동 가능 |
| 10~20초 | 양호 (Good) | 대부분 독립적 |
| 20~30초 | 주의 (Caution) | 보조 기구 필요 가능 |
| > 30초 | 위험 (Risk) | 낙상 위험 높음 |

---

## 3. 공통 기술 스택

### 3.1 MediaPipe Pose Heavy

- `model_complexity=2` (Heavy 모델, 가장 정확)
- 33개 키포인트 감지 (얼굴 10 + 몸체 22)
- 오버레이에는 몸체(11~32)만 표시
- 좌측: 파란색 / 우측: 주황색 / 중앙: 회색

### 3.2 영상 처리

- OpenCV (`cv2`)로 프레임 읽기/쓰기
- 코덱: H.264 (`avc1`) 우선, 실패시 `mp4v` 폴백
- 오버레이 영상: `{원본명}_overlay.mp4`

### 3.3 ArUco 마커 (선택적)

- DICT_4X4_50, ID=0 (START, 2m), ID=1 (FINISH, 12m)
- 감지 성공시 절대 캘리브레이션 시도
- 현재 한계: 원거리에서 MediaPipe h가 부정확하여 항상 비례법으로 폴백
- 검증/로깅 용도로만 사용

### 3.4 프론트엔드 표시

- 오버레이 영상: HTML5 `<video>` 태그로 재생 (VideoModal.tsx)
- 원본/오버레이 토글 가능
- TUG: 측면/정면 오버레이 영상 각각 지원
- 3D 스켈레톤: Three.js + React Three Fiber
