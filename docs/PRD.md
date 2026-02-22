# 10m 보행검사 시스템 - 제품 요구사항 명세서 (PRD)

## 문서 정보
| 항목 | 내용 |
|------|------|
| 버전 | 3.2.0 |
| 최종 업데이트 | 2026년 2월 13일 |
| 상태 | 운영 준비 완료 (Phase 3 엔터프라이즈 + 보행 경로 분석) |

---

## 목차
1. [제품 개요](#1-제품-개요)
2. [기술 스택](#2-기술-스택)
3. [프로젝트 구조](#3-프로젝트-구조)
4. [데이터베이스 스키마](#4-데이터베이스-스키마)
5. [API 명세](#5-api-명세)
6. [프론트엔드 기능](#6-프론트엔드-기능)
7. [인증 및 권한 관리](#7-인증-및-권한-관리)
8. [보행 분석 알고리즘](#8-보행-분석-알고리즘)
9. [낙상 위험 점수 시스템](#9-낙상-위험-점수-시스템)
10. [정상 보행 기준 데이터](#10-정상-보행-기준-데이터)
11. [리포트 생성](#11-리포트-생성)
12. [UI/UX 디자인](#12-uiux-디자인)
13. [성능 최적화](#13-성능-최적화)
14. [보안 고려사항](#14-보안-고려사항)
15. [배포 가이드](#15-배포-가이드)
16. [테스트 현황](#16-테스트-현황)
17. [향후 개선 계획](#17-향후-개선-계획)
18. [실시간 알림 시스템](#18-실시간-알림-시스템-신규)
19. [리포트 강화 및 데이터 내보내기](#19-리포트-강화-및-데이터-내보내기-신규)
20. [재활 권장 시스템](#20-재활-권장-시스템-신규)
21. [추세 예측/트렌드 분석](#21-추세-예측트렌드-분석-신규)
22. [신뢰도 점수 시각화 및 WCAG AA](#22-신뢰도-점수-시각화-및-wcag-aa-phase-3)
23. [맞춤형 리포트 템플릿](#23-맞춤형-리포트-템플릿-phase-3)
24. [이메일 전송 서비스](#24-이메일-전송-서비스-phase-3)
25. [PostgreSQL 및 Redis](#25-postgresql-및-redis-phase-3)
26. [EMR/FHIR 연동](#26-emrfhir-연동-phase-3)
27. [다기관 지원](#27-다기관-지원-phase-3)
28. [Kubernetes 배포](#28-kubernetes-배포-phase-3)

---

## 1. 제품 개요

### 1.1 제품 소개
**10m 보행검사 시스템**은 물리치료사가 환자의 보행 및 균형 능력을 AI 기반 영상 분석으로 자동 측정하는 임상 분석 시스템입니다. MediaPipe 자세 추정 모델을 사용하여 **10MWT(10m 보행검사)**, **TUG(Timed Up and Go)**, **BBS(Berg Balance Scale)** 3가지 표준 임상 검사를 지원합니다.

### 1.2 핵심 기능
| 기능 | 설명 |
|------|------|
| **AI 영상 분석** | MediaPipe Pose 모델을 사용한 자동 자세 분석 (33개 랜드마크) |
| **3가지 검사 지원** | 10MWT, TUG, BBS 표준 임상 검사 |
| **10MWT 분석** | 10m 보행 속도/시간 측정, 어깨/골반 기울기 분석 |
| **TUG 분석** | 5단계 자동 감지 (일어서기→걷기→돌기→걷기→앉기) |
| **TUG 단계별 캡처** | 각 단계 전환 시점 프레임 자동 캡처 및 표시 |
| **TUG 체중이동 분석** | 정면 영상 기반 측방 흔들림, 압력중심(CoP) 궤적 분석 |
| **TUG 자세 편향 캡처** | 어깨/골반 기울기 이상치 자동 감지 및 프레임 캡처 |
| **BBS 평가** | 14개 항목 균형 평가 (총 56점), AI 자동 채점 (6/14항목) |
| **질환별 분석 프로파일** | 9개 질환 (파킨슨, 뇌졸중 등)에 따른 분석 파라미터 자동 조정 |
| **원근 보정** | 환자 키 데이터와 픽셀 높이 비율로 거리 추정 |
| **보행 패턴 분석** | 어깨/골반 기울기 측정 및 비대칭 패턴 감지 |
| **낙상 위험 점수** | 속도/시간 기반 0-100점 종합 위험도 평가 |
| **정상 보행 기준 데이터** | 연령/성별별 정상 보행 속도 비교 (Bohannon 2011) |
| **리포트 생성** | PDF/CSV 형식의 상세 분석 리포트, 한국어 비교 리포트 |
| **다중 사용자** | 역할 기반 접근 제어 (관리자/치료사) |
| **치료사 승인** | 관리자의 치료사 계정 승인 워크플로우 |
| **관리자 대시보드** | 전체 환자/검사 통계, 월별 추세 차트, 개선율 분포 |
| **환자 태그 관리** | 환자 분류용 태그 생성/삭제, 환자별 태그 부여, 태그 기반 필터링 |
| **환자 목표 관리** | 속도/시간/BBS 점수 목표 설정, 진척도 추적 및 달성 관리 |
| **임상 메모 에디터** | 구조화된 메모 (보조기구, 상태, 통증 수준 0-10, 퀵 태그) |
| **포즈 오버레이 영상** | 분석 시 MediaPipe 스켈레톤이 그려진 영상 자동 저장 |
| **좌/우 구분 색상** | 신체 좌측(파란색)/우측(주황색) 색상 구분 표시 |
| **TUG 정면/측면 선택** | TUG 검사 시 정면(어깨/골반 각도) 또는 측면(기립/착석) 영상 선택 |
| **보행 구간 클립 추출** | 보행 구간만 별도 영상 클립으로 추출 |
| **비교 영상 생성** | 두 검사의 영상을 좌우 나란히 배치한 비교 영상 |
| **ArUco 마커 지원** | 마커 PDF 생성/다운로드, 거리 보정 참고값 제공 |
| **랜딩 페이지** | 시스템 소개, 기능 안내, 기술 설명 마케팅 페이지 |
| **다크 모드** | 눈 피로 감소를 위한 다크 테마 지원 |
| **JWT 인증** | Access Token (30분) + Refresh Token (7일) 기반 보안 인증 |
| **Rate Limiting** | 로그인 5회/분, 회원가입 3회/분, 일반 100회/분 속도 제한 |
| **감사 로그** | 모든 주요 작업(로그인, CRUD, 승인 등) 감사 추적 |
| **실시간 알림** | WebSocket 기반 분석 진행률 + 브라우저 알림 + Toast |
| **TUG/BBS PDF 리포트** | TUG 5단계 분석 + BBS 14항목 점수표 PDF 리포트 |
| **일괄 리포트** | 환자의 모든 검사(10MWT+TUG+BBS)를 하나의 PDF로 생성 |
| **데이터 내보내기/백업** | 환자 CSV, 검사 CSV, DB 백업/복원 |
| **재활 권장 시스템** | 낙상 위험 등급 + 질환별 맞춤 재활 프로그램 자동 권장 |
| **추세 예측/트렌드** | 선형회귀 기반 보행 속도 추세 분석, 목표 달성 예측일 |
| **Docker 컨테이너화** | docker-compose로 원클릭 배포 (백엔드+프론트엔드+nginx) |
| **신뢰도 점수 시각화** | 분석 신뢰도를 원형 프로그레스 링 + 색상 그라데이션으로 시각화 |
| **확장 기록 차트** | 10회 제한 없이 전체 검사 이력, 날짜 필터, 페이지네이션 |
| **WCAG AA 색상 대비** | 다크 모드 8개 컴포넌트 대비 비율 검증 및 수정 |
| **맞춤형 리포트 템플릿** | 3개 기본 템플릿 (표준/임상/요약) + DB 기반 커스텀 템플릿 |
| **이메일 전송** | aiosmtplib 기반 PDF 첨부 이메일 전송 |
| **PostgreSQL 지원** | SQLite/PostgreSQL 이중 지원 (db_factory 패턴) |
| **Redis 캐싱** | 대시보드/환자 목록 캐싱, graceful fallback |
| **Kubernetes 배포** | 10개 K8s 매니페스트 (Deployment, Service, Ingress, PVC 등) |
| **CI/CD 파이프라인** | GitHub Actions (ci.yml 테스트 + deploy.yml 배포) |
| **EMR/FHIR 연동** | HL7 FHIR Patient/Observation 리소스 매핑 |
| **다기관 지원** | site_id 기반 데이터 격리, 사이트 관리 |
| **커스텀 거리 목표** | 치료사가 환자별 목적지(편의점, 공원 등) + 거리 + 이모지 입력, 예상 시간 계산 |
| **횡단보도 신호 비교** | 목표에 "횡단보도" 포함 시 일반(1m/1초)/보호구역(1m/1.5초) 신호시간 비교 |
| **보행 능력 등급** | Perry et al. (1995) 기준 4단계 자동 분류 (정상/지역사회/제한적/실내 보행) |
| **보행 경로 분석** | 카카오맵 연동 출발지/도착지 검색, 지도 마커/경로 표시, 예상 소요시간 |
| **카카오맵 통합** | Kakao Maps SDK + Places API 키워드 검색, Haversine 거리 × 1.3 도보 보정 |
| **E2E 테스트** | Playwright 17개 테스트 (인증, 환자, 검사, 관리자 플로우) |

### 1.3 사용 대상
- **물리치료사**: 환자 등록, 보행 검사 수행, 결과 분석
- **관리자**: 치료사 계정 승인 및 관리

### 1.4 임상적 의의

#### 10MWT (10m Walk Test)
노인 및 재활 환자의 기능적 이동성을 평가하는 표준화된 임상 도구입니다:
- 보행 속도 < 0.8 m/s: 낙상 위험 증가
- 보행 시간 > 12.5초: 고위험군 분류
- 정상 보행 속도: ≥ 1.2 m/s

#### TUG (Timed Up and Go)
기능적 이동성과 낙상 위험을 평가하는 검사입니다:
- < 10초: 정상 (독립적 이동 가능)
- 10-20초: 양호 (대부분 독립적)
- 20-30초: 주의 (보조 기구 필요 가능)
- ≥ 30초: 낙상 위험 높음

#### BBS (Berg Balance Scale)
14개 항목으로 균형 능력을 평가합니다 (총 56점):
- 41-56점: 독립적 (낙상 위험 낮음)
- 21-40점: 보조 보행 필요
- 0-20점: 휠체어 의존

---

## 2. 기술 스택

### 2.1 프론트엔드
| 기술 | 버전 | 용도 |
|------|------|------|
| React | 18.2.0 | UI 프레임워크 |
| TypeScript | 5.3.3 | 타입 안전성 |
| Vite | 5.0.12 | 빌드 도구 |
| React Router DOM | 6.21.2 | 라우팅 |
| TailwindCSS | 3.4.1 | CSS 유틸리티 |
| Axios | 1.6.5 | HTTP 클라이언트 |
| Recharts | 2.10.4 | 차트 라이브러리 |
| Kakao Maps SDK | - | 지도 표시, Places 키워드 검색 |

### 2.2 백엔드
| 기술 | 버전 | 용도 |
|------|------|------|
| FastAPI | 0.109.0 | 웹 프레임워크 |
| Uvicorn | 0.27.0 | ASGI 서버 |
| SQLite | - | 데이터베이스 |
| **MediaPipe** | 0.10.14 | AI 자세 추정 (33개 랜드마크) |
| OpenCV | 4.9.0.80 | 영상 처리 |
| NumPy | 1.26.3 | 수치 연산 |
| bcrypt | 4.1.2 | 비밀번호 해싱 |
| ReportLab | 4.0.8 | PDF 생성 |
| aiofiles | 23.2.1 | 비동기 파일 처리 |

### 2.3 AI 모델
- **모델**: MediaPipe Pose
- **키포인트**: 인체 33개 랜드마크 감지
- **특징**: 실시간 처리, 높은 정확도, 3D 좌표 지원

#### MediaPipe Pose 랜드마크
| 부위 | 포인트 | 인덱스 |
|------|--------|--------|
| 얼굴 | 코, 눈, 귀, 입 | 0-10 (분석에서 제외) |
| 상체 | 어깨, 팔꿈치, 손목, 손가락 | 11-22 |
| 몸통 | 골반(힙) | 23-24 |
| 하체 | 무릎, 발목, 발뒤꿈치, 발끝 | 25-32 |

**참고**: 포즈 오버레이 영상에서는 얼굴 랜드마크(0-10)를 제외하고 신체 랜드마크(11-32)만 표시합니다.

#### 좌/우 구분 색상 코딩
| 부위 | 색상 | BGR 값 | 랜드마크 인덱스 |
|------|------|--------|----------------|
| 좌측 (왼쪽) | 파란색/청록색 | (255, 150, 0) | 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31 |
| 우측 (오른쪽) | 주황색 | (0, 128, 255) | 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32 |
| 중앙 (어깨-어깨, 골반-골반) | 회색 | (200, 200, 200) | 연결선 (11-12), (23-24) |

#### 검사별 사용 랜드마크
| 검사 | 주요 랜드마크 | 분석 내용 |
|------|--------------|----------|
| 10MWT | 어깨, 골반, 발목 | 보행 속도, 기울기 |
| TUG | 골반, 무릎, 발목, 어깨 | 5단계 전환 감지 |
| BBS | 전신 33개 포인트 | 균형 자세 평가 |

---

## 3. 프로젝트 구조

```
10M_WT/
├── backend/                          # 백엔드 서버
│   ├── app/
│   │   ├── main.py                   # FastAPI 애플리케이션 진입점
│   │   ├── models/
│   │   │   └── database.py           # SQLite ORM 및 데이터베이스 작업
│   │   ├── routers/
│   │   │   ├── auth.py               # 인증 엔드포인트
│   │   │   ├── patients.py           # 환자 CRUD + 태그 관리
│   │   │   ├── tests.py              # 검사 분석/영상/리포트 엔드포인트
│   │   │   ├── admin.py              # 관리자 치료사 관리 + 대시보드 통계
│   │   │   └── goals.py              # 환자 목표 관리
│   │   ├── services/
│   │   │   ├── fall_risk.py          # 낙상 위험 점수 알고리즘
│   │   │   ├── normative_data.py     # 연령/성별별 정상 보행 기준 데이터
│   │   │   ├── report_generator.py   # PDF/CSV 리포트 생성
│   │   │   ├── comparison_report.py  # 한국어 임상 비교 리포트
│   │   │   └── video_clip_generator.py # 보행 클립 추출 및 비교 영상 생성
│   │   └── utils/
│   ├── analysis/
│   │   ├── gait_analyzer.py          # 10MWT MediaPipe 분석 엔진
│   │   ├── tug_analyzer.py           # TUG 5단계 분석 엔진
│   │   ├── bbs_analyzer.py           # BBS 균형 평가 엔진
│   │   ├── disease_profiles.py       # 질환별 분석 프로파일 (9개 질환)
│   │   ├── aruco_detector.py         # ArUco 마커 감지 및 거리 보정
│   │   └── aruco_marker_generator.py # ArUco 마커 PDF 생성
│   ├── requirements.txt              # Python 의존성
│   └── database.db                   # SQLite 데이터베이스 (런타임)
│
├── frontend/                         # 프론트엔드 클라이언트
│   ├── src/
│   │   ├── App.tsx                   # 메인 React 컴포넌트 (라우팅)
│   │   ├── main.tsx                  # React 진입점
│   │   ├── components/               # 재사용 컴포넌트
│   │   │   ├── Layout.tsx            # 메인 레이아웃, 네비게이션, 검색, 모바일 하단 탭
│   │   │   ├── PatientCard.tsx       # 환자 목록 카드
│   │   │   ├── FallRiskScore.tsx     # 위험 점수 표시
│   │   │   ├── SpeedChart.tsx        # 속도 추이 차트
│   │   │   ├── AngleChart.tsx        # 어깨/골반 기울기 차트
│   │   │   ├── UploadProgress.tsx    # 업로드/분석 3단계 진행률
│   │   │   ├── VideoModal.tsx        # 영상 재생 모달 (포즈 오버레이, TUG 정면/측면)
│   │   │   ├── TUGResult.tsx         # TUG 검사 종합 결과
│   │   │   ├── TUGPhaseTimeline.tsx  # TUG 단계별 타임라인
│   │   │   ├── TUGPhaseFrames.tsx    # TUG 단계별 캡처 이미지
│   │   │   ├── TUGWeightShift.tsx    # TUG 체중이동 분석 (정면 영상)
│   │   │   ├── TUGDeviationCaptures.tsx # TUG 자세 편향 캡처
│   │   │   ├── BBSResult.tsx         # BBS 검사 결과 표시
│   │   │   ├── BBSForm.tsx           # BBS 14항목 수동 채점 폼 (AI 추천 포함)
│   │   │   ├── GoalProgress.tsx      # 목표 진척도 추적
│   │   │   ├── GoalSetting.tsx       # 목표 설정 모달
│   │   │   ├── TagManager.tsx        # 환자 태그 관리
│   │   │   ├── TagBadge.tsx          # 태그 배지 표시
│   │   │   ├── ComparisonReport.tsx  # 이전/현재 검사 비교 리포트
│   │   │   ├── ClinicalNotesEditor.tsx # 구조화된 임상 메모 에디터
│   │   │   ├── NotesAnalysis.tsx     # 메모 분석 표시
│   │   │   ├── VideoComparison.tsx   # 좌우 비교 영상
│   │   │   └── WalkingHighlight.tsx  # 보행 구간 클립 하이라이트
│   │   ├── pages/                    # 페이지 컴포넌트
│   │   │   ├── Landing.tsx           # 랜딩/마케팅 페이지
│   │   │   ├── Dashboard.tsx         # 메인 환자 목록 (검색, 태그 필터, 위험도 필터)
│   │   │   ├── Login.tsx             # 로그인
│   │   │   ├── Register.tsx          # 회원가입
│   │   │   ├── PatientForm.tsx       # 환자 생성/수정
│   │   │   ├── PatientDetail.tsx     # 환자 상세 (태그, 목표, 비교 리포트)
│   │   │   ├── VideoUpload.tsx       # 영상 업로드 (10MWT/TUG/BBS 탭)
│   │   │   ├── History.tsx           # 검사 기록 (유형별 필터, 인라인 편집)
│   │   │   ├── TherapistManagement.tsx # 관리자 치료사 관리
│   │   │   └── AdminDashboard.tsx    # 관리자 통계 대시보드
│   │   ├── services/
│   │   │   └── api.ts                # Axios API 클라이언트 (auth/admin/patient/test/goal/dashboard)
│   │   ├── types/
│   │   │   └── index.ts              # TypeScript 인터페이스
│   │   ├── utils/
│   │   │   ├── index.ts              # 날짜 포맷, 나이 계산, 속도 평가
│   │   │   └── fallRisk.ts           # 클라이언트 측 위험 계산
│   │   ├── contexts/
│   │   │   └── ThemeContext.tsx       # 다크 모드 테마 관리
│   │   └── index.css                 # 전역 스타일 (커스텀 TailwindCSS 유틸리티)
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── vite.config.ts
│
├── uploads/                          # 영상 저장 디렉토리
│   └── status/                       # 분석 상태 JSON 파일
├── database.db                       # SQLite 데이터베이스
├── start.bat                         # Windows 시작 스크립트
├── stop.bat                          # Windows 종료 스크립트
├── PRD.md                            # 본 문서
├── PRD_10MWT.md                      # 10MWT 분석 변수/정확도 검증 보고서
└── PRD_TUG.md                        # TUG 분석 변수/임상 프로파일 보고서
```

---

## 4. 데이터베이스 스키마

### 4.1 Users 테이블 (사용자)
| 컬럼 | 타입 | 설명 | 제약조건 |
|------|------|------|----------|
| id | TEXT | 고유 식별자 | PRIMARY KEY |
| username | TEXT | 로그인 아이디 | UNIQUE, NOT NULL |
| password_hash | TEXT | bcrypt 해시된 비밀번호 | NOT NULL |
| name | TEXT | 사용자 이름 | NOT NULL |
| role | TEXT | 역할 ('admin' 또는 'therapist') | - |
| is_approved | INTEGER | 승인 상태 (0 또는 1) | DEFAULT 0 |
| created_at | TEXT | 생성 일시 | DEFAULT CURRENT_TIMESTAMP |

### 4.2 Patients 테이블 (환자)
| 컬럼 | 타입 | 설명 | 제약조건 |
|------|------|------|----------|
| id | TEXT | 고유 식별자 | PRIMARY KEY |
| patient_number | TEXT | 환자 번호 | UNIQUE, NOT NULL |
| name | TEXT | 환자 이름 | NOT NULL |
| gender | TEXT | 성별 ('M' 또는 'F') | - |
| birth_date | TEXT | 생년월일 | NOT NULL |
| height_cm | REAL | 키 (cm) - 원근 보정용 | NOT NULL |
| diagnosis | TEXT | 진단명 | OPTIONAL |
| created_at | TEXT | 생성 일시 | DEFAULT CURRENT_TIMESTAMP |

### 4.3 Walk_Tests 테이블 (검사 기록)
| 컬럼 | 타입 | 설명 | 제약조건 |
|------|------|------|----------|
| id | TEXT | 고유 식별자 | PRIMARY KEY |
| patient_id | TEXT | 환자 ID | FOREIGN KEY |
| **test_type** | TEXT | 검사 유형 ('10MWT', 'TUG', 'BBS') | DEFAULT '10MWT' |
| test_date | TEXT | 검사 일시 | DEFAULT CURRENT_TIMESTAMP |
| walk_time_seconds | REAL | 시간/점수 (TUG:초, BBS:총점) | NOT NULL |
| walk_speed_mps | REAL | 보행 속도 (m/s), BBS는 0 | NOT NULL |
| video_url | TEXT | 업로드된 영상 경로 | OPTIONAL |
| analysis_data | TEXT | JSON 형식의 상세 분석 데이터 | - |
| notes | TEXT | 치료사 메모 | OPTIONAL |
| therapist_id | TEXT | 검사 수행 치료사 ID | OPTIONAL |
| created_at | TEXT | 생성 일시 | DEFAULT CURRENT_TIMESTAMP |

#### analysis_data JSON 구조 (검사 유형별)

**10MWT:**
```json
{
  "test_type": "10MWT",
  "walk_time_seconds": 8.5,
  "walk_speed_mps": 1.18,
  "overlay_video_filename": "overlay_abc123.mp4",
  "gait_pattern": {
    "shoulder_tilt_avg": 2.3,
    "hip_tilt_avg": 1.1,
    "assessment": "정상 보행 패턴"
  }
}
```

**TUG:**
```json
{
  "test_type": "TUG",
  "total_time_seconds": 12.5,
  "assessment": "normal",
  "side_overlay_video_filename": "tug_side_overlay_abc123.mp4",
  "front_overlay_video_filename": "tug_front_overlay_abc123.mp4",
  "phases": {
    "stand_up": { "duration": 1.5, "start_time": 0, "end_time": 1.5 },
    "walk_out": { "duration": 3.2, "start_time": 1.5, "end_time": 4.7 },
    "turn": { "duration": 2.1, "start_time": 4.7, "end_time": 6.8 },
    "walk_back": { "duration": 3.5, "start_time": 6.8, "end_time": 10.3 },
    "sit_down": { "duration": 2.2, "start_time": 10.3, "end_time": 12.5 }
  },
  "phase_frames": {
    "stand_up": { "frame": "base64...", "time": 0.5, "label": "일어서기" },
    "walk_out": { "frame": "base64...", "time": 1.5, "label": "걷기(나감)" },
    "turn": { "frame": "base64...", "time": 4.7, "label": "돌아서기" },
    "walk_back": { "frame": "base64...", "time": 6.8, "label": "걷기(돌아옴)" },
    "sit_down": { "frame": "base64...", "time": 10.3, "label": "앉기" }
  }
}
```

**BBS:**
```json
{
  "test_type": "BBS",
  "total_score": 45,
  "assessment": "independent",
  "item_scores": {
    "item1_sitting_to_standing": 4,
    "item2_standing_unsupported": 4,
    ...
  }
}
```

### 4.4 Patient_Tags 테이블 (환자 태그)
| 컬럼 | 타입 | 설명 | 제약조건 |
|------|------|------|----------|
| id | TEXT | 고유 식별자 | PRIMARY KEY |
| name | TEXT | 태그 이름 | UNIQUE, NOT NULL |
| color | TEXT | 태그 색상 (헥스 코드) | DEFAULT '#6B7280' |
| created_at | TEXT | 생성 일시 | DEFAULT CURRENT_TIMESTAMP |

### 4.5 Patient_Tag_Map 테이블 (환자-태그 매핑, N:N)
| 컬럼 | 타입 | 설명 | 제약조건 |
|------|------|------|----------|
| patient_id | TEXT | 환자 ID | FOREIGN KEY, PK |
| tag_id | TEXT | 태그 ID | FOREIGN KEY, PK |

### 4.6 Patient_Goals 테이블 (환자 목표)
| 컬럼 | 타입 | 설명 | 제약조건 |
|------|------|------|----------|
| id | TEXT | 고유 식별자 | PRIMARY KEY |
| patient_id | TEXT | 환자 ID | FOREIGN KEY |
| test_type | TEXT | 검사 유형 ('10MWT', 'TUG', 'BBS') | DEFAULT '10MWT' |
| target_speed_mps | REAL | 목표 보행 속도 (m/s) | OPTIONAL |
| target_time_seconds | REAL | 목표 보행 시간 (초) | OPTIONAL |
| target_score | INTEGER | 목표 BBS 점수 | OPTIONAL |
| target_date | TEXT | 목표 달성 기한 | OPTIONAL |
| status | TEXT | 목표 상태 ('active', 'achieved') | DEFAULT 'active' |
| achieved_at | TEXT | 달성 일시 | OPTIONAL |
| created_at | TEXT | 생성 일시 | DEFAULT CURRENT_TIMESTAMP |

### 4.7 Patient_Distance_Goals 테이블 (커스텀 거리 목표)
| 컬럼 | 타입 | 설명 | 제약조건 |
|------|------|------|----------|
| id | TEXT | 고유 식별자 | PRIMARY KEY |
| patient_id | TEXT | 환자 ID | FOREIGN KEY |
| distance_meters | REAL | 목표 거리 (m) | NOT NULL |
| label | TEXT | 목적지 라벨 (예: 편의점, 횡단보도) | NOT NULL |
| emoji | TEXT | 이모지 아이콘 | DEFAULT '🚶' |
| created_at | TEXT | 생성 일시 | DEFAULT CURRENT_TIMESTAMP |

### 4.8 Patient_Walking_Routes 테이블 (보행 경로)
| 컬럼 | 타입 | 설명 | 제약조건 |
|------|------|------|----------|
| id | TEXT | 고유 식별자 | PRIMARY KEY |
| patient_id | TEXT | 환자 ID | FOREIGN KEY |
| origin_address | TEXT | 출발지 주소 | NOT NULL |
| origin_lat | REAL | 출발지 위도 | NOT NULL |
| origin_lng | REAL | 출발지 경도 | NOT NULL |
| dest_address | TEXT | 도착지 주소 | NOT NULL |
| dest_lat | REAL | 도착지 위도 | NOT NULL |
| dest_lng | REAL | 도착지 경도 | NOT NULL |
| distance_meters | REAL | 도보 거리 (m) | OPTIONAL |
| created_at | TEXT | 생성 일시 | DEFAULT CURRENT_TIMESTAMP |

### 4.9 ERD (Entity Relationship Diagram)
```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Users     │       │  Patients   │       │ Walk_Tests  │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │◄──────│ patient_id  │
│ username    │       │ patient_num │       │ id (PK)     │
│ password    │       │ name        │       │ test_type   │
│ name        │       │ gender      │       │ test_date   │
│ role        │       │ birth_date  │       │ walk_time   │
│ is_approved │       │ height_cm   │       │ walk_speed  │
│ created_at  │       │ diagnosis   │       │ video_url   │
└─────────────┘       │ created_at  │       │ analysis    │
                      └──────┬──────┘       │ notes       │
                             │              │ therapist_id│
                      ┌──────┼──────┐       │ created_at  │
                      │      │      │       └─────────────┘
                      ▼      ▼      ▼
              ┌────────┐ ┌────────┐ ┌──────────────┐
              │Tag_Map │ │ Goals  │ │ Patient_Tags │
              ├────────┤ ├────────┤ ├──────────────┤
              │pat_id  │ │ id(PK) │ │ id (PK)      │
              │tag_id  │ │ pat_id │ │ name         │
              └────────┘ │test_typ│ │ color        │
                         │tgt_spd │ └──────────────┘
                         │tgt_time│
                         │tgt_scor│
                         │status  │
                         └────────┘
```

---

## 5. API 명세

### 5.1 인증 API

#### POST /api/auth/register
새로운 치료사 계정 등록

**요청 본문:**
```json
{
  "username": "string",
  "password": "string",
  "name": "string"
}
```

**응답:**
```json
{
  "id": "uuid",
  "username": "string",
  "name": "string",
  "role": "therapist",
  "is_approved": false,
  "created_at": "ISO8601"
}
```

**참고:** 치료사는 관리자 승인 전까지 기능 사용 불가

---

#### POST /api/auth/login
사용자 로그인

**요청 본문:**
```json
{
  "username": "string",
  "password": "string"
}
```

**응답:**
```json
{
  "id": "uuid",
  "username": "string",
  "name": "string",
  "role": "admin|therapist",
  "is_approved": true|false
}
```

**오류 응답:**
- `400`: 잘못된 사용자명 또는 비밀번호
- `403`: 승인 대기 중인 치료사

---

### 5.2 환자 API

#### POST /api/patients/
새 환자 등록

**권한:** 승인된 치료사만

**요청 본문:**
```json
{
  "patient_number": "string",
  "name": "string",
  "gender": "M|F",
  "birth_date": "YYYY-MM-DD",
  "height_cm": 170.5,
  "diagnosis": "string (optional)"
}
```

**응답:** 생성된 환자 객체 (ID 포함)

---

#### GET /api/patients/
환자 목록 조회

**권한:** 로그인한 모든 사용자

**쿼리 파라미터:**
- `limit`: 최대 반환 개수 (기본: 50, 최대: 100)

**응답:** 환자 객체 배열

---

#### GET /api/patients/search
환자 검색

**권한:** 로그인한 모든 사용자

**쿼리 파라미터:**
- `q`: 검색어 (이름 또는 환자번호)

**응답:** 일치하는 환자 객체 배열

---

#### GET /api/patients/{patient_id}
환자 상세 조회

**권한:** 로그인한 모든 사용자

**응답:** 환자 객체

---

#### PUT /api/patients/{patient_id}
환자 정보 수정

**권한:** 승인된 치료사만

**요청 본문:** 수정할 필드만 포함

**응답:** 수정된 환자 객체

---

#### DELETE /api/patients/{patient_id}
환자 삭제 (관련 검사 포함)

**권한:** 승인된 치료사만

**응답:** `{ "message": "환자가 삭제되었습니다" }`

---

#### 환자 태그 API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/patients/tags/all` | 전체 태그 목록 조회 |
| POST | `/api/patients/tags` | 태그 생성 (`{ "name": "string", "color": "#hex" }`) |
| DELETE | `/api/patients/tags/{tag_id}` | 태그 삭제 |
| GET | `/api/patients/by-tag/{tag_id}` | 태그별 환자 조회 |
| GET | `/api/patients/{patient_id}/tags` | 환자의 태그 목록 |
| POST | `/api/patients/{patient_id}/tags/{tag_id}` | 환자에 태그 부여 |
| DELETE | `/api/patients/{patient_id}/tags/{tag_id}` | 환자에서 태그 제거 |

---

### 5.3 검사/분석 API

#### POST /api/tests/{patient_id}/upload
영상 업로드 및 분석 시작

**권한:** 승인된 치료사만

**요청:** `multipart/form-data`로 영상 파일

**응답:**
```json
{
  "file_id": "uuid",
  "message": "분석이 시작되었습니다",
  "status_endpoint": "/api/tests/status/{file_id}"
}
```

**처리 과정:**
1. 환자 존재 여부 확인
2. 영상을 uploads 디렉토리에 저장
3. 백그라운드 분석 작업 시작
4. 상태 확인용 file_id 반환

---

#### GET /api/tests/status/{file_id}
분석 진행 상태 확인

**응답:**
```json
{
  "status": "processing|completed|error",
  "progress": 0-100,
  "message": "현재 상태 메시지",
  "result": { /* 분석 결과 (완료 시) */ }
}
```

---

#### GET /api/tests/patient/{patient_id}
환자의 모든 검사 조회

**권한:** 로그인한 모든 사용자

**응답:** 검사 객체 배열 (최신순 정렬)

---

#### GET /api/tests/{test_id}
단일 검사 상세 조회

**권한:** 로그인한 모든 사용자

**응답:** 분석 데이터가 파싱된 검사 객체

---

#### GET /api/tests/patient/{patient_id}/compare
최근 검사와 이전 검사 비교

**권한:** 로그인한 모든 사용자

**응답:**
```json
{
  "current_test": { /* 현재 검사 */ },
  "previous_test": { /* 이전 검사 (있을 경우) */ },
  "comparison_message": "개선됨|악화됨|유지",
  "speed_difference": 0.15,
  "time_difference": -1.2
}
```

---

#### PUT /api/tests/{test_id}/date
검사 날짜 수정

**요청 본문:**
```json
{
  "test_date": "ISO8601 날짜"
}
```

---

#### PUT /api/tests/{test_id}/notes
검사 메모 추가/수정

**요청 본문:**
```json
{
  "notes": "치료사 메모 내용 (null이면 삭제)"
}
```

---

#### DELETE /api/tests/{test_id}
검사 삭제 (영상 포함)

**응답:** `{ "message": "검사 기록이 삭제되었습니다" }`

---

#### GET /api/tests/{test_id}/report/pdf
PDF 리포트 다운로드

**응답:** PDF 파일

---

#### GET /api/tests/{test_id}/report/csv
CSV 리포트 다운로드

**응답:** CSV 파일

---

#### GET /api/tests/{test_id}/video/info
영상 정보 조회

**응답:**
```json
{
  "filename": "video.mp4",
  "size_bytes": 1024000,
  "size_mb": 1.0,
  "video_url": "/uploads/video.mp4"
}
```

---

#### GET /api/tests/{test_id}/video/download
영상 파일 다운로드

---

#### POST /api/tests/{patient_id}/upload-tug
TUG 듀얼 영상 업로드 (측면 + 정면)

**권한:** 승인된 치료사만

**요청:** `multipart/form-data`로 `side_video`, `front_video` 2개 파일

**응답:** `{ "file_id": "uuid", "status_endpoint": "..." }`

---

#### POST /api/tests/{patient_id}/upload-bbs
BBS 영상 업로드 (AI 분석)

**권한:** 승인된 치료사만

**요청:** `multipart/form-data`로 영상 파일

**응답:** `{ "file_id": "uuid", "status_endpoint": "..." }`

---

#### POST /api/tests/{patient_id}/bbs
BBS 수동 채점 결과 저장

**권한:** 승인된 치료사만

**요청 본문:**
```json
{
  "scores": { "item1_sitting_to_standing": 4, ... },
  "notes": "string (optional)"
}
```

**응답:** `{ "test_id": "uuid", "total_score": 45, "assessment": "independent" }`

---

#### GET /api/tests/patient/{patient_id}/stats
환자 통계 조회

**쿼리 파라미터:** `test_type` (기본: '10MWT')

**응답:** 평균/최고/최저 속도·시간, 총 검사 횟수, 개선율

---

#### GET /api/tests/patient/{patient_id}/comparison-report
임상 비교 리포트 생성 (한국어)

**쿼리 파라미터:** `test_id`, `prev_test_id` (선택)

**응답:** 개선/악화 분석, 속도·시간 변화율, 낙상 위험 점수 변화, 목표 진척도

---

#### GET /api/tests/{test_id}/video/overlay
포즈 오버레이 영상 스트리밍

**응답:** `multipart/x-mixed-replace` MJPEG 스트림 (MediaPipe 스켈레톤 오버레이)

---

#### GET /api/tests/{test_id}/video/overlay/frame
단일 프레임 포즈 오버레이

**쿼리 파라미터:** `frame` (프레임 번호)

**응답:** JPEG 이미지 + 메타데이터 헤더 (`X-Total-Frames`, `X-FPS`, `X-Current-Frame`)

---

#### GET /api/tests/{test_id}/video/walking-clip
보행 구간 클립 추출

**응답:** 보행 시작~종료 구간만 추출된 MP4 영상

---

#### GET /api/tests/patient/{patient_id}/video/comparison
비교 영상 생성 (좌우 배치)

**쿼리 파라미터:** `test1_id`, `test2_id`

**응답:** 두 영상을 좌우로 나란히 합친 MP4 영상

---

#### GET /api/tests/{test_id}/phase-clip/{phase_name}
TUG 단계별 클립 추출

**파라미터:** `phase_name` (stand_up, walk_out, turn, walk_back, sit_down)

**응답:** 해당 단계의 영상 클립

---

#### GET /api/tests/aruco/markers/pdf
ArUco 마커 PDF 다운로드

**응답:** START(ID=0) + FINISH(ID=1) 마커가 포함된 PDF 파일

---

### 5.4 관리자 API

#### GET /api/admin/therapists
모든 치료사 목록

**권한:** 관리자만

**응답:** 치료사 객체 배열

---

#### GET /api/admin/therapists/pending
승인 대기 중인 치료사 목록

**권한:** 관리자만

**응답:** 미승인 치료사 객체 배열

---

#### POST /api/admin/therapists/{user_id}/approve
치료사 승인

**권한:** 관리자만

**응답:** `is_approved: true`가 된 치료사 객체

---

#### DELETE /api/admin/therapists/{user_id}
치료사 삭제/거부

**권한:** 관리자만

---

#### GET /api/admin/dashboard/stats
관리자 대시보드 통계

**권한:** 관리자만

**응답:**
```json
{
  "total_patients": 25,
  "total_tests": 120,
  "total_therapists": 5,
  "monthly_tests": [{ "month": "2026-01", "count": 15 }, ...],
  "improvement_distribution": { "improved": 60, "maintained": 25, "declined": 15 },
  "test_type_distribution": { "10MWT": 80, "TUG": 30, "BBS": 10 }
}
```

---

### 5.5 목표 API

#### POST /api/goals/{patient_id}
환자 목표 생성

**요청 본문:**
```json
{
  "test_type": "10MWT|TUG|BBS",
  "target_speed_mps": 1.2,
  "target_time_seconds": 8.3,
  "target_score": null,
  "target_date": "2026-06-01"
}
```

---

#### GET /api/goals/{patient_id}
환자 목표 조회

**쿼리 파라미터:** `status` (active, achieved, 선택)

**응답:** 목표 객체 배열

---

#### PUT /api/goals/{goal_id}/update
목표 수정

**요청 본문:** 수정할 필드만 포함

---

#### DELETE /api/goals/{goal_id}/delete
목표 삭제

---

#### GET /api/goals/{patient_id}/progress
목표 진척도 조회

**응답:** 각 목표별 현재 달성률 (%), 최근 검사 대비 진척 상태

---

### 5.6 커스텀 거리 목표 API

#### POST /api/distance-goals/{patient_id}
커스텀 거리 목표 생성 (치료사가 환자별 목적지 + 거리 + 이모지 입력)

**요청 본문:**
```json
{
  "distance_meters": 150,
  "label": "편의점",
  "emoji": "🏪"
}
```

#### GET /api/distance-goals/{patient_id}
환자의 거리 목표 목록 조회

#### DELETE /api/distance-goals/{goal_id}/delete
거리 목표 삭제

---

### 5.7 보행 경로 API

#### POST /api/walking-routes/{patient_id}
보행 경로 저장 (카카오맵 검색 결과 기반)

**요청 본문:**
```json
{
  "origin_address": "서울역",
  "origin_lat": 37.5547,
  "origin_lng": 126.9707,
  "dest_address": "남산타워",
  "dest_lat": 37.5512,
  "dest_lng": 126.9882,
  "distance_meters": 2340
}
```

#### GET /api/walking-routes/{patient_id}
환자의 보행 경로 목록 조회

#### DELETE /api/walking-routes/{route_id}/delete
보행 경로 삭제

---

## 6. 프론트엔드 기능

### 6.1 페이지 구성

#### 랜딩 페이지 (`Landing.tsx`)
| 기능 | 설명 |
|------|------|
| 히어로 섹션 | 시스템 소개 및 주요 가치 |
| 기능 소개 | 10MWT, TUG, BBS 검사 기능 안내 |
| 기술 설명 | MediaPipe AI 기반 분석 기술 |
| 검사 유형 설명 | 각 검사의 임상적 의의 |
| 혜택 안내 | 치료사/환자를 위한 시스템 장점 |
| 로그인/가입 링크 | 인증 페이지 이동 |

#### 로그인 페이지 (`Login.tsx`)
| 기능 | 설명 |
|------|------|
| 사용자명/비밀번호 입력 | 폼 유효성 검사 |
| 오류 메시지 표시 | 잘못된 자격 증명 안내 |
| 승인 상태 확인 | 미승인 치료사 접근 차단 |
| 회원가입 링크 | 등록 페이지로 이동 |
| 다크 모드 지원 | 테마 적용 |

#### 회원가입 페이지 (`Register.tsx`)
| 기능 | 설명 |
|------|------|
| 신규 치료사 등록 | 사용자명/비밀번호/이름 입력 |
| 중복 검사 | 사용자명 중복 확인 |
| 승인 안내 | 관리자 승인 필요 메시지 표시 |

#### 대시보드 (`Dashboard.tsx`)
| 기능 | 설명 |
|------|------|
| 환자 통계 | 총 환자 수 표시 |
| 환자 검색 | 디바운스 적용 (300ms) |
| 환자 목록 | PatientCard 컴포넌트로 표시 |
| **태그 기반 필터링** | 태그별 환자 분류 및 필터 |
| **위험도 필터링** | 낙상 위험 등급별 필터 (정상/경도/중등도/고위험) |
| **정렬** | 이름순, 최근 검사순 등 정렬 기능 |
| 빠른 액션 | 신규 환자, 치료사 관리 버튼 |
| 역할별 표시 | 관리자/치료사에 따른 UI 차별화 |

#### 환자 상세 (`PatientDetail.tsx`)
| 기능 | 설명 |
|------|------|
| 환자 정보 | 이름, 나이, 키, 진단명 |
| **환자 태그** | 태그 표시 및 TagManager로 관리 |
| 검사 통계 | 총 검사 횟수 |
| 최근 검사 결과 | 시간, 속도, 상태 표시 |
| 이전 검사 비교 | 속도/시간 변화량 표시 |
| **임상 비교 리포트** | ComparisonReport 컴포넌트로 한국어 비교 분석 |
| **목표 진척도** | GoalProgress/GoalSetting으로 목표 관리 |
| **임상 메모** | ClinicalNotesEditor로 구조화된 메모 |
| 최근 검사 목록 | 최근 5회 검사 |
| PDF 다운로드 | 리포트 다운로드 버튼 |
| 영상 재생 | VideoModal로 영상 확인 |
| 액션 버튼 | 새 검사, 기록, 수정, 삭제 |

#### 환자 등록/수정 (`PatientForm.tsx`)
| 기능 | 설명 |
|------|------|
| 신규 등록 모드 | 모든 필드 입력 |
| 수정 모드 | 기존 데이터 불러오기 |
| 필드 | 환자번호, 이름, 성별, 생년월일, 키, 진단명 |
| 환자번호 | 생성 후 수정 불가 |
| 폼 유효성 | 필수 필드 검사 |

#### 영상 업로드 (`VideoUpload.tsx`)
| 기능 | 설명 |
|------|------|
| **검사 유형 탭** | 10MWT / TUG / BBS 탭으로 구분 |
| 드래그 앤 드롭 | 영상 파일 드롭 영역 |
| 파일 선택 | 파일 입력을 통한 선택 |
| **10MWT 업로드** | 단일 영상 + 보행 방향(away/toward) 선택 |
| **TUG 듀얼 업로드** | 측면 영상 + 정면 영상 별도 드래그 영역 |
| **BBS 업로드** | AI 자동 분석 영상 업로드 + 수동 채점 폼(BBSForm) |
| 포맷 검증 | 영상 파일 형식 확인 |
| 업로드 진행률 | 실시간 진행 상황 표시 (3단계: 업로드→분석→완료) |
| 분석 진행률 | 분석 상태 폴링 및 표시 |
| 결과 표시 | 성공 시 측정값 및 오버레이 영상 표시 |
| 오류 처리 | "다시 시도" 버튼으로 재시도 옵션 제공 |
| 촬영 가이드 | 검사 유형별 올바른 촬영 방법 안내 (10MWT/TUG) |

#### 검사 기록 (`History.tsx`)
| 기능 | 설명 |
|------|------|
| 전체 검사 목록 | 모든 검사 기록 표시 |
| 검사 비교 | 이전/현재 검사 비교 |
| 변화 지표 | 속도/시간 변화량 색상 표시 |
| 낙상 위험 점수 | FallRiskScore 컴포넌트 |
| 추이 차트 | SpeedChart로 속도/시간 변화 |
| 검사별 액션 | 날짜 수정, 메모, 영상, PDF/CSV, 삭제 |
| 기준값 안내 | 정상/위험 기준 설명 |

#### 치료사 관리 (`TherapistManagement.tsx`)
| 기능 | 설명 |
|------|------|
| 관리자 전용 | 관리자만 접근 가능 |
| 대기 목록 | 승인 대기 치료사 (주황색) |
| 승인 목록 | 승인된 치료사 (녹색) |
| 승인/거부 | 대기 치료사 처리 버튼 |
| 삭제 | 승인된 치료사 제거 |
| 사용자 정보 | 이름, 사용자명, 가입일 |

#### 관리자 대시보드 (`AdminDashboard.tsx`)
| 기능 | 설명 |
|------|------|
| 관리자 전용 | 관리자만 접근 가능 |
| 전체 통계 | 총 환자 수, 총 검사 수, 치료사 수 |
| 월별 추세 차트 | 월별 검사 건수 Recharts 차트 |
| 개선율 분포 | 개선/유지/악화 비율 파이 차트 |
| 검사 유형 분포 | 10MWT/TUG/BBS 비율 표시 |

### 6.2 컴포넌트 구성

#### Layout (`Layout.tsx`)
- 고정 헤더 (sticky)
- 로고 및 애플리케이션 제목
- 네비게이션 링크
- 환자 검색 드롭다운
- **다크 모드 토글 버튼**
- 사용자 정보 및 역할 배지
- 로그아웃 버튼
- 모바일 하단 네비게이션
- 반응형 레이아웃
- 푸터

#### PatientCard (`PatientCard.tsx`)
- 환자 요약 정보 카드
- 이름, 환자번호, 인구통계
- 최근 검사 속도/시간
- 상태 배지 (색상 구분)
- 클릭 시 상세 페이지 이동

#### FallRiskScore (`FallRiskScore.tsx`)
- 낙상 위험 평가 표시
- 점수 (0-100) 색상 구분
- 위험 등급 (정상/경도/중등도/고위험)
- 점수 구성 (속도 + 시간)
- 위험 설명 텍스트

#### SpeedChart (`SpeedChart.tsx`)
- 보행 속도 추이 라인 차트
- 보행 시간 추이 라인 차트
- X축: 검사 회차 (최근 10회)
- Y축: 속도 (m/s), 시간 (초)
- 기준선: 정상 (1.2), 위험 (0.8)
- Recharts 인터랙티브 차트

#### UploadProgress (`UploadProgress.tsx`)
- 업로드 진행률 바
- 분석 진행률 바
- 실시간 상태 메시지
- 단계별 상태 표시

#### VideoModal (`VideoModal.tsx`)
- 영상 재생 모달 오버레이
- HTML5 비디오 플레이어
- **포즈 오버레이 영상 재생**: MediaPipe 스켈레톤이 그려진 영상 표시
- **TUG 정면/측면 영상 선택**: 정면(어깨/골반 각도) 또는 측면(기립/착석) 영상 선택 버튼
- **TUG 검사 시 단계별 전환 시점 캡처 표시**
- 포즈 ON/OFF 토글 버튼
- 닫기 버튼, 다운로드 버튼
- 반응형 크기, 스크롤 지원

#### TUGResult (`TUGResult.tsx`)
- TUG 검사 종합 결과 표시
- 총 소요 시간 및 평가
- 단계별 시간 타임라인
- 기립/착석 분석 메트릭
- 기울기 분석 (정면 영상)

#### TUGPhaseFrames (`TUGPhaseFrames.tsx`)
- 5단계 전환 시점 캡처 이미지 그리드
- 각 단계별 색상 구분
- 클릭 시 상세 모달 (감지 기준, 설명, 주요 포인트)
- 이미지 다운로드 기능

#### BBSResult (`BBSResult.tsx`)
- BBS 14개 항목 점수 표시
- 총점 및 균형 평가
- 카테고리별 점수 시각화

#### BBSForm (`BBSForm.tsx`)
- BBS 14개 항목 수동 채점 폼
- AI 추천 점수 표시 (자동 분석 완료 시)
- 각 항목별 0-4점 선택
- 합계 자동 계산

#### TUGWeightShift (`TUGWeightShift.tsx`)
- 정면 영상 기반 체중이동 분석
- 측방 흔들림 (lateral sway) 표시
- 압력중심(CoP) 궤적 시각화
- 안정성 평가 (안정적/약간의 불균형/불균형 주의)

#### TUGDeviationCaptures (`TUGDeviationCaptures.tsx`)
- 어깨/골반 기울기 이상치 캡처 프레임
- 심각도 배지 (mild/moderate/severe)
- 주석 이미지 표시

#### GoalProgress (`GoalProgress.tsx`)
- 커스텀 거리 목표 관리 (DB 저장)
- 치료사가 목적지 라벨 + 거리(m) + 이모지 입력
- 환자 보행 속도 기반 예상 소요시간 계산
- 이모지 프리셋 12종 (🏪🏫🌳🏥🛒🚌🏠⛪🏢🚶🚗☕)
- **횡단보도 신호시간 비교**: 라벨에 "횡단보도" 포함 시 자동 표시
  - 일반: 보행진입 7초 + 거리 × 1초/m
  - 보호구역: 보행진입 7초 + 거리 × 1.5초/m
- 목표 추가/삭제 기능

#### GoalSetting (`GoalSetting.tsx`)
- 새 목표 설정 모달 폼
- 검사 유형별 목표 입력 (속도, 시간, BBS 점수)
- 달성 기한 설정

#### TagManager (`TagManager.tsx`)
- 환자에 태그 부여/제거
- 기존 태그 목록에서 선택
- 새 태그 생성 (이름 + 색상)

#### TagBadge (`TagBadge.tsx`)
- 색상 코딩된 태그 배지 표시

#### ComparisonReport (`ComparisonReport.tsx`)
- 이전/현재 검사 비교 메시지 (한국어)
- 개선/악화/유지 분석

#### ClinicalNotesEditor (`ClinicalNotesEditor.tsx`)
- 구조화된 임상 메모 작성
- 보조기구 선택
- 상태/컨디션 입력
- 통증 수준 슬라이더 (0-10)
- 퀵 태그 선택

#### NotesAnalysis (`NotesAnalysis.tsx`)
- 저장된 메모의 구조화된 표시
- 태그, 통증 수준, 텍스트 파싱

#### VideoComparison (`VideoComparison.tsx`)
- 두 검사 영상 좌우 나란히 비교
- 영상 동기화 재생

#### WalkingHighlight (`WalkingHighlight.tsx`)
- 보행 구간만 추출한 클립 재생
- 보행 시작/종료 표시

#### AngleChart (`AngleChart.tsx`)
- Recharts 라인 차트
- 어깨/골반 기울기 시간축 변화
- X축: 시간, Y축: 각도(°)
- **평균 각도 표시**: 제목 옆에 평균값 (±5° 이내 녹색, 초과 주황색)

#### WalkingRouteCard (`WalkingRouteCard.tsx`)
- **보행 능력 등급 표시**: Perry et al. (1995) 기준 4단계
  - Lv.1 정상 보행 (≥1.2 m/s, 녹색)
  - Lv.2 지역사회 보행 (0.8-1.2 m/s, 파란색)
  - Lv.3 제한적 보행 (0.4-0.8 m/s, 주황색)
  - Lv.4 실내 보행 (<0.4 m/s, 빨간색)
- **카카오맵 통합**: Kakao Maps SDK + Places API
  - 출발지/도착지 키워드 검색 (300ms 디바운스)
  - 지도 마커 (파란색=출발, 빨간색=도착) + 점선 경로
- **예상 소요시간**: Haversine 직선거리 × 1.3 도보보정 ÷ 환자 속도
- **일반인 기준 비교**: 1.0 m/s 기준 소요시간 함께 표시
- **경로 CRUD**: DB 저장/조회/삭제, 재방문 시 복원
- PatientDetail 우측 사이드바 + History 우측 사이드바 (평균 속도 기반)

---

## 7. 인증 및 권한 관리

### 7.1 인증 흐름
```
1. 사용자 회원가입 → is_approved = false로 계정 생성
2. 관리자가 대기 치료사 검토
3. 관리자 승인 클릭 → is_approved = true
4. 치료사 로그인 및 기능 사용 가능
```

### 7.2 권한 모델

| 역할 | 접근 가능 | 가능한 작업 | 제한사항 |
|------|----------|------------|----------|
| **비로그인** | 로그인, 회원가입 | 없음 | 보호된 경로 접근 불가 |
| **관리자** | 대시보드(조회만), 치료사 관리 | 치료사 승인/거부/삭제 | 환자/검사 생성/수정/삭제 불가 |
| **치료사 (미승인)** | 대시보드(조회만) | 없음 | 모든 쓰기 작업 차단 |
| **치료사 (승인됨)** | 전체 애플리케이션 | 환자/검사 CRUD, 영상 업로드, 리포트 다운로드 | 치료사 관리 불가 |

### 7.3 클라이언트 측 인증 저장
- 사용자 객체: localStorage에 저장
- API 요청 시 헤더로 전송:
  - `X-User-Id`: 사용자 ID
  - `X-User-Role`: 역할 (admin/therapist)
  - `X-User-Approved`: 승인 상태 (true/false)
- Axios 인터셉터가 자동으로 헤더 추가

---

## 8. 검사 분석 알고리즘

### 8.1 GaitAnalyzer 클래스 (`gait_analyzer.py`) - 10MWT

#### 사용 모델
- **MediaPipe Pose**
- 인체 33개 랜드마크 감지
- 실시간 처리, 높은 정확도
- 3D 좌표 지원

#### 촬영 방식
- **전면/후면 촬영**: 카메라가 환자의 정면 또는 후면에 위치
- **환자 이동 방향**: 카메라 방향으로 접근 또는 이탈

#### 측정 구간
```
[시작] ----2m---- [측정 시작] ----10m---- [측정 종료]
  0m              2m                      12m
       가속구간          실제 측정 구간
```
| 구간 | 거리 | 설명 |
|------|------|------|
| 0m ~ 2m | 2m | 가속 구간 (측정 제외) |
| 2m ~ 12m | 10m | 실제 측정 구간 |
| 총 보행 거리 | 12m | - |

#### 분석 과정

**1. 프레임 처리**
```
- 네이티브 FPS로 영상 읽기
- 각 프레임: MediaPipe 추론 → 33개 랜드마크 추출
- 픽셀 높이 계산 (코에서 발목까지 거리)
- 어깨/골반 기울기 각도 계산
```

**2. 보행 방향 감지 (`_detect_walking_direction`)**
```
- 처음 1/4 프레임과 마지막 1/4 프레임의 평균 픽셀 높이 비교
- 픽셀 높이 증가: 카메라로 접근 (toward)
- 픽셀 높이 감소: 카메라에서 이탈 (away)
```

**3. 거리 계산 (`_calculate_distances`)**
```
- 핀홀 카메라 모델: 거리 비율 = 픽셀 높이 역비례
- 초기 픽셀 높이와 카메라 거리 기준으로 보정
- 각 프레임별 이동 거리 추정
```

**4. 측정 구간 찾기 (`_find_measurement_zone`)**
```
- 2m 지점 통과 프레임 감지 (측정 시작)
- 12m 지점 도달 프레임 감지 (측정 종료)
- 시간 = (종료 프레임 - 시작 프레임) / FPS
- 속도 = 10m / 시간(초)
```

**5. 보행 패턴 분석 (`_analyze_gait_pattern`)**
```
- 어깨 기울기: 좌/우 어깨 Y좌표 차이로 각도 계산
- 골반 기울기: 좌/우 골반 Y좌표 차이로 각도 계산
- 양수: 오른쪽 높음 (왼쪽으로 기울어짐)
- 음수: 왼쪽 높음 (오른쪽으로 기울어짐)
```

#### 분석 결과 데이터
```json
{
  "walk_time_seconds": 8.5,
  "walk_speed_mps": 1.18,
  "fps": 30.0,
  "total_frames": 450,
  "start_frame": 75,
  "end_frame": 330,
  "patient_height_cm": 170.0,
  "frames_analyzed": 450,
  "model": "MediaPipe Pose",
  "video_duration": 15.0,
  "walking_direction": "toward",
  "overlay_video_filename": "overlay_abc123.mp4",
  "measurement_zone": {
    "start_distance_m": 2.0,
    "end_distance_m": 12.0,
    "measured_distance_m": 10.0
  },
  "gait_pattern": {
    "shoulder_tilt_avg": 2.3,
    "shoulder_tilt_max": 5.1,
    "shoulder_tilt_direction": "우측 높음 (2.3°)",
    "hip_tilt_avg": 1.1,
    "hip_tilt_max": 3.2,
    "hip_tilt_direction": "정상",
    "assessment": "어깨 경미한 기울기 (우측 높음 (2.3°))"
  }
}
```

#### 포즈 오버레이 영상 생성
- 분석 중 각 프레임에 MediaPipe 스켈레톤 그리기
- 신체 랜드마크(11-32)만 표시 (얼굴 제외)
- 좌측(파란색)/우측(주황색)/중앙(회색) 색상 구분
- 선 굵기: 4px, 원 반경: 8px
- 가시성 임계값: 50% (visibility > 0.5인 랜드마크만 표시)
- MP4 형식으로 저장 (mp4v 코덱)

#### 보행 패턴 기준
| 기울기 | 판정 | 설명 |
|--------|------|------|
| ±2° 이내 | 정상 | 정상 범위 |
| ±2° ~ 5° | 경미한 기울기 | 모니터링 권장 |
| ±5° 이상 | 주의 필요 | 전문가 상담 권장 |

#### 측정 설정 파라미터
| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| CAMERA_DISTANCE_M | 14.0 | 카메라와 시작점 사이 거리 (m) |
| ACCEL_ZONE_M | 2.0 | 가속 구간 (측정 제외) |
| MEASUREMENT_DISTANCE_M | 10.0 | 실제 측정 거리 |
| TOTAL_WALK_DISTANCE_M | 12.0 | 총 보행 거리 |

---

### 8.2 TUGAnalyzer 클래스 (`tug_analyzer.py`)

#### 검사 개요
TUG(Timed Up and Go) 검사는 의자에서 일어나 3m 걷고, 돌아서 다시 3m 걸어 돌아와 앉는 동작을 측정합니다.

#### 5단계 자동 감지
| 단계 | 한글명 | 감지 기준 |
|------|--------|----------|
| stand_up | 일어서기 | 엉덩이-무릎-발목 각도가 120° 이하 → 160° 이상 변화 |
| walk_out | 걷기(나감) | 기립 완료 후 발이 전방으로 이동 시작 |
| turn | 돌아서기 | 어깨 방향 변화가 최대인 지점 감지 |
| walk_back | 걷기(돌아옴) | 회전 완료 후 반대 방향 이동 시작 |
| sit_down | 앉기 | 다리 각도가 160° 이상 → 120° 이하 변화 |

#### 각도 임계값
| 파라미터 | 값 | 설명 |
|----------|-----|------|
| SITTING_ANGLE_THRESHOLD | 120° | 앉은 자세 기준 |
| STANDING_ANGLE_THRESHOLD | 160° | 선 자세 기준 |

#### 단계별 전환 시점 캡처
- 각 단계 시작 시점에서 1개 프레임 자동 캡처
- MediaPipe 포즈 스켈레톤 오버레이
- Base64 인코딩으로 저장 (JPEG 품질 85%)
- 캡처 정보: 시간, 프레임 번호, 감지 기준, 설명, 주요 포인트

#### 추가 분석 (측면/정면 영상)
**측면 영상:**
- 기립 속도 (stand_up_speed)
- 착석 속도 (sit_down_speed)
- 손 지지 여부 감지 (손목-무릎 거리 < 15% 프레임 높이)
- **포즈 오버레이 영상 저장** (side_overlay_video_filename)

**정면 영상:**
- 어깨 기울기 (평균, 최대, 방향)
- 골반 기울기 (평균, 최대, 방향)
- **포즈 오버레이 영상 저장** (front_overlay_video_filename)

#### 포즈 오버레이 영상 선택 (프론트엔드)
| 영상 타입 | 용도 | 기본 선택 |
|----------|------|----------|
| 정면 영상 | 어깨/골반 기울기, 좌/우 균형 분석 | ✓ (TUG 기본값) |
| 측면 영상 | 기립/착석 동작, 보행 패턴 분석 | - |

#### TUG 평가 기준
| 시간 | 평가 | 설명 |
|------|------|------|
| < 10초 | 정상 (normal) | 독립적 이동 가능 |
| 10-20초 | 양호 (good) | 대부분 독립적 |
| 20-30초 | 주의 (caution) | 보조 기구 필요 가능 |
| ≥ 30초 | 위험 (risk) | 낙상 위험 높음 |

---

### 8.3 BBSAnalyzer 클래스 (`bbs_analyzer.py`)

#### 검사 개요
BBS(Berg Balance Scale)는 14개 항목으로 균형 능력을 평가하는 검사입니다. 총 56점 만점.

#### 14개 평가 항목
| 번호 | 항목 | 설명 |
|------|------|------|
| 1 | 앉은 자세에서 일어나기 | sitting_to_standing |
| 2 | 잡지 않고 서 있기 | standing_unsupported |
| 3 | 등받이 없이 앉기 | sitting_unsupported |
| 4 | 선 자세에서 앉기 | standing_to_sitting |
| 5 | 이동하기 | transfers |
| 6 | 눈 감고 서 있기 | standing_eyes_closed |
| 7 | 발 모으고 서 있기 | standing_feet_together |
| 8 | 팔 뻗어 앞으로 내밀기 | reaching_forward |
| 9 | 바닥에서 물건 집기 | pick_up_object |
| 10 | 뒤 돌아보기 | turning_to_look |
| 11 | 360도 회전 | turning_360 |
| 12 | 발판 위에 발 교대로 올리기 | alternate_foot |
| 13 | 일렬로 서기 | standing_tandem |
| 14 | 한 발로 서기 | standing_one_leg |

#### 각 항목 점수 (0-4점)
| 점수 | 의미 |
|------|------|
| 0 | 수행 불가 |
| 1 | 심한 도움 필요 |
| 2 | 중등도 도움 필요 |
| 3 | 경미한 도움/감독 필요 |
| 4 | 독립적 수행 |

#### BBS 총점 평가
| 점수 범위 | 평가 | 설명 |
|-----------|------|------|
| 41-56점 | 독립적 (independent) | 낙상 위험 낮음 |
| 21-40점 | 보조 보행 (walking_with_assistance) | 보조 기구 필요 |
| 0-20점 | 휠체어 의존 (wheelchair_bound) | 이동 시 휠체어 필요 |

---

## 9. 낙상 위험 점수 시스템

### 9.1 점수 체계

**총점: 0-100점**

#### 속도 점수 (0-50점)
| 속도 (m/s) | 점수 | 상태 |
|------------|------|------|
| ≥ 1.2 | 50점 | 정상 |
| ≥ 1.0 | 40점 | 경도 저하 |
| ≥ 0.8 | 25점 | 주의 |
| < 0.8 | 10점 | 위험 |

#### 시간 점수 (0-50점) - 10m 거리 기준
| 시간 (초) | 점수 | 상태 |
|-----------|------|------|
| ≤ 8.3 | 50점 | 정상 |
| ≤ 10.0 | 40점 | 경도 저하 |
| ≤ 12.5 | 25점 | 주의 |
| > 12.5 | 10점 | 위험 |

### 9.2 위험 등급
| 점수 범위 | 등급 | 색상 | 설명 |
|-----------|------|------|------|
| 90-100 | 정상 | 녹색 | 낙상 위험 낮음 |
| 70-89 | 경도 위험 | 파란색 | 경미한 우려, 모니터링 권장 |
| 50-69 | 중등도 위험 | 주황색 | 적극적 개입 필요 |
| 0-49 | 고위험 | 빨간색 | 즉각적 개입 필요 |

### 9.3 임상 근거
- 10m 보행검사 임상 표준 기반
- 속도 < 0.8 m/s: 낙상 위험 증가와 연관
- 시간 > 12.5초 (0.8 m/s): 고위험군 분류

---

## 10. 정상 보행 기준 데이터

### 10.1 연령/성별별 정상 보행 속도 (`normative_data.py`)

Bohannon (2011) 연구 기반 정상 보행 속도 참조 데이터:

| 연령대 | 남성 평균 (m/s) | 여성 평균 (m/s) | 남성 범위 | 여성 범위 |
|--------|----------------|----------------|----------|----------|
| 20-29세 | 1.36 | 1.34 | 1.10-1.62 | 1.08-1.60 |
| 30-39세 | 1.43 | 1.34 | 1.17-1.69 | 1.08-1.60 |
| 40-49세 | 1.43 | 1.39 | 1.17-1.69 | 1.13-1.65 |
| 50-59세 | 1.43 | 1.31 | 1.17-1.69 | 1.05-1.57 |
| 60-69세 | 1.34 | 1.24 | 1.08-1.60 | 0.98-1.50 |
| 70-79세 | 1.26 | 1.13 | 1.00-1.52 | 0.87-1.39 |
| 80-89세 | 0.97 | 0.94 | 0.71-1.23 | 0.68-1.20 |

### 10.2 속도 평가 (`get_speed_assessment`)

환자의 보행 속도를 연령/성별 기준과 비교하여 Z-점수 기반 임상 해석을 제공:

| Z-점수 | 평가 | 설명 |
|--------|------|------|
| ≥ -0.5 | 정상 범위 | 동일 연령/성별 평균 내 |
| ≥ -1.0 | 경미한 저하 | 평균 이하, 모니터링 권장 |
| ≥ -2.0 | 중등도 저하 | 재활 개입 필요 |
| < -2.0 | 심한 저하 | 집중 재활 필요 |

### 10.3 프론트엔드 평가 (`utils/index.ts`)

| 속도 (m/s) | 평가 | 색상 |
|------------|------|------|
| ≥ 1.2 | Normal | 녹색 |
| ≥ 1.0 | Mildly reduced | - |
| ≥ 0.8 | Moderately reduced | 노란색 |
| < 0.8 | Severely reduced | 빨간색 |

---

## 11. 리포트 생성

### 11.1 PDF 리포트 (`report_generator.py`)

#### 섹션 구성

**1. 헤더**
- 제목: "10m Walk Test Report"
- 부제: 한글 설명
- 생성 일시

**2. 환자 정보**
- 이름, 환자번호
- 성별, 생년월일
- 키 (cm), 진단명

**3. 현재 검사 결과**
- 검사 일자
- 보행 시간 (초)
- 보행 속도 (m/s)

**4. 낙상 위험 평가**
- 총점 (0-100)
- 속도 점수 (0-50)
- 시간 점수 (0-50)
- 위험 등급 및 설명
- 점수 해석 가이드

**5. 메모 섹션** (있을 경우)
- 치료사 메모 표시 박스

**6. 추이 차트** (다수 검사 시)
- 속도 추이 라인 차트 (최근 10회)
- 시간 추이 라인 차트 (최근 10회)
- 기준선: 정상/위험 임계값

**7. 이전 검사 비교** (있을 경우)
- 속도 비교 (이전 vs 현재)
- 시간 비교
- 방향 지표 (↑ ↓)
- 평가 메시지 (개선/악화/유지)
- 색상별 해석

**8. 검사 기록 테이블** (다수 검사 시)
- 최근 10회 검사
- 컬럼: 회차, 날짜, 시간(초), 속도(m/s), 위험점수

**9. 푸터**
- 면책 조항: "임상 참고용"
- 이중 언어 면책 조항

### 11.2 CSV 리포트

**형식:** 표준 CSV (섹션 구분)

**내용:**
- 환자 인구통계
- 검사 결과 (시간, 속도)
- 분석 세부 정보 (FPS, 프레임, 시작/종료)
- 메모 (있을 경우)

### 11.3 임상 비교 리포트 (`comparison_report.py`)

이전 검사와 현재 검사를 비교하는 한국어 임상 요약 리포트:

**포함 내용:**
- 속도 변화량 및 변화율 (%)
- 시간 변화량 및 변화율 (%)
- 낙상 위험 점수 변화
- 개선/악화/유지 평가 메시지
- 목표 대비 진척도 (목표 설정 시)

---

## 12. UI/UX 디자인

### 12.1 디자인 시스템

#### 색상 체계
| 용도 | 색상 | 헥스 코드 |
|------|------|-----------|
| 주요 색상 | 파란색 | #3b82f6 |
| 성공 | 녹색 | #22c55e |
| 경고 | 주황색 | #f97316 |
| 오류 | 빨간색 | #ef4444 |
| 중립 | 회색 | #f9fafb ~ #111827 |

#### 타이포그래피
- 폰트: 시스템 폰트 스택
- 크기: 8px (캡션) → 24px (제목)

#### 간격
- 4px 기본 단위 (TailwindCSS)

#### 테두리 및 반경
- 둥근 모서리 (8-16px)

### 12.2 테마

#### 라이트 모드 (기본)
- 배경: 흰색/연회색
- 텍스트: 진회색/검정

#### 다크 모드
- 배경: 진회색 (#1f2937 기반)
- 텍스트: 연회색/흰색
- 대비 조정

#### 테마 컨텍스트
- React Context로 전역 상태 관리
- localStorage에 설정 저장
- 시스템 설정 감지 (prefers-color-scheme)

### 12.3 반응형 디자인
| 화면 | 레이아웃 |
|------|----------|
| 데스크톱 | 3-4열, 전체 네비게이션 |
| 태블릿 | 2열, 햄버거 메뉴 |
| 모바일 | 1열, 하단 네비게이션 |

#### 중단점 (TailwindCSS 표준)
- sm: 640px
- md: 768px
- lg: 1024px
- xl: 1280px

### 12.4 접근성

> **구현 상태: 구현 완료** - ARIA 레이블, 키보드 접근성, 스크린 리더 지원 추가 (2026.02.10)

| 항목 | 상태 | 비고 |
|------|------|------|
| 시맨틱 HTML 구조 | ✅ 구현 | `<button>`, `<form>`, `<label>` 등 적절히 사용 |
| 폼 입력 레이블 | ✅ 구현 | `htmlFor`/`id` 연결, 필수 표시(`*`) |
| ARIA 레이블 | ✅ **구현** | `aria-label`, `aria-pressed`, `aria-expanded`, `aria-current="page"` 적용 |
| 키보드 네비게이션 | ✅ **구현** | BBSForm 항목 Enter/Space 키 지원, `tabIndex`, `role="button"` |
| 스크린 리더 최적화 | ✅ **구현** | `aria-live="polite"` (업로드 진행, 검색 결과), `role="alert"` (오류 메시지) |
| 색상 대비 (WCAG AA) | ⚠️ 미검증 | TailwindCSS 기본 색상 사용, 공식 검증 미실시 |

#### 접근성 적용 컴포넌트
| 컴포넌트 | 적용 내용 |
|----------|-----------|
| `Layout.tsx` | `aria-current="page"` 네비게이션 활성 링크 |
| `VideoModal.tsx` | `role="alert"` 오류, `aria-pressed` 토글 버튼 |
| `UploadProgress.tsx` | `aria-live="polite"` 상태 변경 알림 |
| `BBSForm.tsx` | `aria-expanded`, `role="button"`, `tabIndex={0}`, `aria-pressed` 점수 버튼 |
| `Dashboard.tsx` | `aria-live="polite"` 검색 결과, `role="alert"` 오류 |
| `VideoUpload.tsx` | `role="alert"` 오류 카드 |

---

## 13. 성능 최적화

### 13.1 백엔드 최적화
| 영역 | 방법 |
|------|------|
| 비동기 처리 | FastAPI 백그라운드 태스크로 영상 분석 |
| 스레드 풀 | 별도 스레드 풀에서 분석 실행 (최대 2 워커) |
| 데이터베이스 | 단순 쿼리로 SQLite 최적화 |
| 영상 스트리밍 | 업로드된 영상에 정적 파일 마운팅 |
| 진행 콜백 | 분석 중 실시간 진행 상황 업데이트 |

### 13.2 프론트엔드 최적화
| 영역 | 방법 |
|------|------|
| 상태 관리 | 로컬 React 상태 + localStorage |
| 검색 디바운싱 | 환자 검색에 300ms 디바운스 |
| 차트 렌더링 | 최적화된 데이터셋 (최대 10개 검사) |
| SVG 아이콘 | 최소한의 이미지 사용 |

### 13.3 병목 지점
| 작업 | 예상 시간 |
|------|-----------|
| 영상 분석 | 영상 길이/FPS에 따라 30-120초 |
| 모델 로딩 | 백엔드 시작 시 일회성 비용 |
| PDF 생성 | 복잡한 리포트 시 2-5초 |

---

## 14. 보안 고려사항

### 14.1 비밀번호 보안
- **해싱**: bcrypt + 솔트 (비용 인자 12)
- **권장**: 최소 길이 검증 추가

### 14.2 인증

> **구현 상태: JWT 인증 구현 완료** (2026.02.10)

- **JWT 토큰**: Access Token (30분 만료) + Refresh Token (7일 만료)
- **알고리즘**: HS256, 비밀키는 `JWT_SECRET` 환경변수
- **토큰 구조**: user_id, username, role, is_approved 포함
- **하위 호환**: JWT 없으면 기존 X-User-* 헤더 방식으로 폴백
- **프론트엔드**: `Authorization: Bearer` 헤더 자동 추가, 401 시 자동 refresh

#### JWT 관련 파일
| 파일 | 용도 |
|------|------|
| `backend/app/utils/jwt_handler.py` | 토큰 생성/검증 (create_access_token, create_refresh_token, verify_token) |
| `backend/.env` | JWT_SECRET 설정 |

#### JWT API 엔드포인트
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/auth/login` | 로그인 시 access_token + refresh_token 반환 |
| POST | `/api/auth/refresh` | refresh_token으로 새 access_token 발급 |
| GET | `/api/auth/me` | Bearer 토큰으로 현재 사용자 조회 |

### 14.3 속도 제한 (Rate Limiting)

> **구현 상태: 구현 완료** (2026.02.10)

- **라이브러리**: slowapi
- **전역 제한**: 100 요청/분 (IP당)
- **로그인**: 5 요청/분 (IP당)
- **회원가입**: 3 요청/분 (IP당)
- **테스트 환경**: `TESTING=true` 환경변수로 자동 비활성화
- **응답**: 429 Too Many Requests + Retry-After 헤더

### 14.4 감사 로그 (Audit Logging)

> **구현 상태: 구현 완료** (2026.02.10)

#### audit_logs 테이블
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT | 고유 식별자 (UUID) |
| user_id | TEXT | 작업 수행 사용자 |
| action | TEXT | 작업 유형 (login, create_patient, etc.) |
| resource_type | TEXT | 자원 유형 (user, patient, test, therapist) |
| resource_id | TEXT | 자원 ID |
| details | TEXT | 상세 정보 JSON |
| ip_address | TEXT | 클라이언트 IP |
| created_at | TEXT | 타임스탬프 |

#### 감사 대상 작업
| 작업 | 설명 |
|------|------|
| login / login_failed | 로그인 성공/실패 |
| register | 회원가입 |
| create_patient / update_patient / delete_patient | 환자 CRUD |
| upload_test / delete_test | 검사 업로드/삭제 |
| approve_therapist / delete_therapist | 치료사 승인/삭제 |

#### 감사 로그 API
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/admin/audit-logs?limit=50&offset=0&action=&user_id=` | 관리자 전용, 페이징 및 필터 |

#### 감사 로그 파일
| 파일 | 용도 |
|------|------|
| `backend/app/services/audit_logger.py` | log_action(), get_audit_logs(), get_audit_logs_count() |

### 14.5 권한
- **JWT 검증**: Authorization Bearer 토큰 서버 측 검증 (폴백: X-User-* 헤더)
- **DB 쿼리**: 행 수준 보안 없음 (다중 테넌시 불필요)
- **관리자 확인**: 관리자 엔드포인트 역할 검사

### 14.6 데이터 보호
- **영상 저장**: 서버 `/uploads` 디렉토리
- **데이터베이스**: 애플리케이션 루트의 SQLite 파일
- **암호화**: 저장 데이터 미암호화

### 14.7 남은 개선 권장사항
1. ~~localStorage 헤더 대신 JWT 토큰 구현~~ → ✅ 구현 완료
2. 프로덕션에 HTTPS 추가
3. 민감 데이터 저장 시 암호화
4. CSRF 보호 추가
5. ~~속도 제한 구현~~ → ✅ 구현 완료
6. ~~관리자 작업 감사 로깅~~ → ✅ 구현 완료
7. 의존성 정기 보안 패치

---

## 15. 배포 가이드

### 15.1 필수 조건
- Python 3.9+
- Node.js 16+
- Windows/Linux/macOS

### 15.2 백엔드 설정
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 15.3 프론트엔드 설정
```bash
cd frontend
npm install
npm run dev  # 개발 서버: http://localhost:5173
```

### 15.4 프로덕션 빌드
```bash
# 프론트엔드
npm run build  # dist/ 디렉토리 생성

# 백엔드
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 15.5 환경 변수
```
# Backend .env
UPLOAD_DIR=./uploads
```

### 15.6 정적 파일
- 영상: `uploads/` 디렉토리 저장
- 데이터베이스: 프로젝트 루트 `database.db`
- 프론트엔드: `frontend/dist/` 빌드

### 15.7 Windows 스크립트
- `start.bat`: 백엔드/프론트엔드 서버 시작
- `stop.bat`: 서버 종료

### 15.8 Docker 배포 (신규)

> **구현 상태: 구현 완료** (2026.02.10)

#### Docker 파일 구성
| 파일 | 설명 |
|------|------|
| `docker-compose.yml` | 백엔드 + 프론트엔드 오케스트레이션 |
| `backend/Dockerfile` | Python 3.11-slim, OpenCV/MediaPipe 시스템 의존성 |
| `frontend/Dockerfile` | 멀티스테이지 빌드 (node:20-alpine → nginx:alpine) |
| `frontend/nginx.conf` | API 리버스 프록시, SPA 라우팅, 업로드 500MB 제한 |
| `backend/.dockerignore` | venv/, __pycache__ 제외 |
| `frontend/.dockerignore` | node_modules/, dist/ 제외 |

#### 서비스 구성
| 서비스 | 포트 | 설명 |
|--------|------|------|
| `backend` | 8000:8000 | FastAPI + MediaPipe |
| `frontend` | 3000:80 | nginx (정적 파일 + API 프록시) |

#### 실행 명령
```bash
# 빌드 및 시작
docker compose up --build

# 종료
docker compose down
```

#### 데이터 영속성
- `uploads/` 디렉토리: 볼륨 마운트로 영상 파일 유지
- `database.db`: 볼륨 마운트로 DB 데이터 유지

#### nginx 설정
- `/api/` → `http://backend:8000/api/` (프록시)
- `/uploads/` → `http://backend:8000/uploads/` (프록시)
- `proxy_read_timeout`: 300초 (영상 분석 대기)
- `client_max_body_size`: 500MB (대용량 영상 업로드)

---

## 16. 테스트 현황

> **구현 상태: 구현 완료** - 백엔드 pytest + 프론트엔드 Vitest + Playwright E2E + 성능 테스트 총 248개+ 자동화 테스트 (2026.02.10)

### 16.1 현재 상태

| 항목 | 상태 |
|------|------|
| 백엔드 단위 테스트 (pytest) | ✅ **130개 테스트** (32초) |
| 프론트엔드 단위 테스트 (Vitest) | ✅ **84개 테스트** (2초) |
| 테스트 프레임워크 | ✅ pytest (백엔드), Vitest (프론트엔드) |
| 테스트 스크립트 (package.json) | ✅ `npm test` |
| E2E 테스트 (Playwright) | ✅ **17개 테스트** (Chromium) |
| CI/CD 테스트 파이프라인 | ✅ GitHub Actions (`ci.yml` + `deploy.yml`) |
| 분석 정확도 검증 | ✅ 4개 레퍼런스 영상 수동 검증 (PRD_10MWT.md 참고) |

### 16.2 백엔드 테스트 (130개)

**실행**: `cd backend && venv\Scripts\python.exe -m pytest tests/ -v`

| 파일 | 테스트 수 | 검증 내용 |
|------|-----------|-----------|
| `tests/test_fall_risk.py` | 23개 | 속도/시간 점수, 위험 등급, 프론트엔드 동등성 |
| `tests/test_normative_data.py` | 13개 | 연령 계산, 정상 범위, Z-점수, 임상 해석 |
| `tests/test_database.py` | 47개 | 사용자/환자/검사/태그/목표 CRUD, 비밀번호 해싱 |
| `tests/test_api_auth.py` | 9개 | 회원가입, 로그인, 중복/누락 필드 |
| `tests/test_api_patients.py` | 21개 | 환자 CRUD, 권한 검증, 태그, 헬스체크 |

**테스트 인프라**:
- `tests/conftest.py`: 격리된 테스트 DB (`test_database.db`), `clean_db` autouse fixture
- `httpx.AsyncClient` + `ASGITransport`: 서버 없이 인프로세스 API 테스트
- `TESTING=true` 환경변수: Rate limiting 자동 비활성화

### 16.3 프론트엔드 테스트 (84개)

**실행**: `cd frontend && npm test`

| 파일 | 테스트 수 | 검증 내용 |
|------|-----------|-----------|
| `src/utils/fallRisk.test.ts` | 30개 | 낙상 위험 점수 계산, 등급 판정 |
| `src/utils/index.test.ts` | 10개 | 날짜 포맷, 나이 계산, 속도 평가 |
| `src/services/api.test.ts` | 44개 | auth/patient/admin/test/goal/dashboard API 모킹 |

**테스트 인프라**:
- Vitest (vite.config.ts에 설정)
- `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`
- jsdom 환경

### 16.4 E2E 테스트 (17개)

> ✅ **구현 완료** (2026.02.10) - Playwright

**실행**: `cd frontend && npx playwright test`

| 파일 | 테스트 수 | 검증 내용 |
|------|-----------|-----------|
| `e2e/auth.spec.ts` | 5개 | 로그인, 회원가입, 잘못된 자격증명, 로그아웃, 보호된 경로 |
| `e2e/patient-flow.spec.ts` | 5개 | 환자 생성, 목록, 상세, 수정, 삭제 |
| `e2e/test-flow.spec.ts` | 3개 | 검사 업로드 페이지, 이력 페이지, 검사 결과 표시 |
| `e2e/admin.spec.ts` | 4개 | 관리자 대시보드, 사용자 관리, 통계, 데이터 내보내기 |

**E2E 인프라**:
- `playwright.config.ts`: Chromium 브라우저, 자동 서버 시작 (백엔드 8000 + 프론트엔드 5173)
- `e2e/helpers/auth.ts`: `loginAsAdmin`, `registerTherapist` 헬퍼
- 재시도: 최대 2회 (CI 환경)

### 16.5 CI/CD 파이프라인

> ✅ **구현 완료** (2026.02.10) - GitHub Actions

| 파일 | 트리거 | 내용 |
|------|--------|------|
| `.github/workflows/ci.yml` | push, PR | 백엔드 pytest + 프론트엔드 Vitest + 빌드 검증 |
| `.github/workflows/deploy.yml` | 태그 릴리스 | Docker 이미지 빌드/푸시 + K8s 배포 |

### 16.6 성능 테스트 (6개 카테고리)

> ✅ **검증 완료** (2026.02.10)

**실행**: `cd backend && venv\Scripts\python.exe tests/test_performance.py`

#### 16.6.1 대용량 영상 업로드

| 파일 크기 | 업로드 시간 | 처리량 | 결과 |
|----------|-----------|--------|------|
| 10MB | 0.06s | 168.7 MB/s | ✅ PASS |
| 50MB | 0.32s | 155.1 MB/s | ✅ PASS |
| 100MB | 0.70s | 142.6 MB/s | ✅ PASS |
| 500MB | 2.86s | 174.6 MB/s | ✅ PASS |

#### 16.6.2 동시 접속 (API 요청)

| 동시 요청 | 평균 응답 | P95 | 에러 | 처리량 |
|----------|---------|-----|------|-------|
| 1 | 266ms | 266ms | 0 | 3.8 req/s |
| 10 | 273ms | 276ms | 0 | 36.2 req/s |
| 25 | 280ms | 284ms | 0 | 87.7 req/s |
| 50 | 294ms | 308ms | 0 | 161.1 req/s |
| 100 | 387ms | 422ms | 0 | 233.2 req/s |

#### 16.6.3 동시 업로드 (2-Worker 포화 테스트)

| 동시 업로드 | 총 시간 | 최대 시간 | 성공률 |
|-----------|--------|---------|-------|
| 1 | 0.27s | 0.27s | 100% |
| 2 | 0.29s | 0.29s | 100% |
| 3 | 0.42s | 0.42s | 100% |
| 4 | 0.42s | 0.42s | 100% |
| 5 | 0.32s | 0.32s | 100% |

#### 16.6.4 DB 대량 데이터 (1,600+ 레코드)

| 작업 | 결과 |
|------|------|
| 100명 환자 일괄 생성 | 1.52s (66건/s) |
| 500명 환자 일괄 생성 | 4.80s (104건/s) |
| 1,000명 환자 일괄 생성 | 10.97s (91건/s) |
| 환자 목록 쿼리 (page_size=20~500) | 평균 2.9~3.1ms |
| 환자 검색 (1,600+ 레코드) | 평균 2.8~3.3ms |

#### 16.6.5 API 엔드포인트 응답 시간 (10회 평균)

| 엔드포인트 | 평균 | 최소 | 최대 |
|-----------|------|------|------|
| Health check | 0.9ms | 0.7ms | 1.0ms |
| Patient list | 2.7ms | 2.6ms | 2.9ms |
| Patient detail | 1.5ms | 1.4ms | 1.7ms |
| Patient tests | 1.6ms | 1.5ms | 2.0ms |
| Recommendations | 1.0ms | 0.8ms | 1.3ms |
| Trend analysis | 1.0ms | 0.8ms | 1.3ms |

#### 16.6.6 WebSocket 동시 연결

| 동시 연결 | 성공률 | 총 시간 |
|----------|-------|--------|
| 1 | 100% | 2.07s |
| 5 | 100% | 2.03s |
| 10 | 100% | 2.05s |
| 25 | 100% | 2.06s |
| 50 | 100% | 2.07s |

#### 16.6.7 성능 테스트 결론

- **대용량 업로드**: 500MB 영상도 3초 이내 업로드 완료, 파일 크기 제한 없음
- **동시 접속**: 100명 동시 요청에도 에러 0건, 평균 387ms 응답
- **Worker 포화**: 5개 동시 업로드도 전부 성공 (ThreadPoolExecutor 큐잉 정상)
- **DB 쿼리**: 1,600+ 레코드에서도 3ms 이내 응답, 페이지 크기 무관
- **WebSocket**: 50개 동시 연결 100% 성공

---

## 17. 향후 개선 계획

### 17.1 접근성 개선

> ✅ **전체 구현 완료** (2026.02.10)

| 항목 | 상태 |
|------|------|
| ~~ARIA 레이블 추가~~ | ✅ 구현 완료 |
| ~~키보드 네비게이션~~ | ✅ 구현 완료 |
| ~~스크린 리더 지원~~ | ✅ 구현 완료 |
| ~~WCAG AA 검증~~ | ✅ 구현 완료 - 다크 모드 8개 컴포넌트 색상 대비 수정 (섹션 22 참고) |

### 17.2 테스트 인프라 구축

> ✅ **전체 구현 완료** (2026.02.10) - 섹션 16 참고

| 항목 | 상태 |
|------|------|
| ~~Vitest 설정~~ | ✅ 84개 프론트엔드 테스트 |
| ~~pytest 설정~~ | ✅ 130개 백엔드 테스트 |
| ~~Playwright E2E~~ | ✅ 17개 E2E 테스트 (섹션 16.4 참고) |
| ~~CI/CD 연동~~ | ✅ GitHub Actions 파이프라인 (섹션 16.5 참고) |

### 17.3 2단계 기능

> ✅ **전체 구현 완료** (2026.02.10)

| 영역 | 기능 | 상태 |
|------|------|------|
| **영상 분석** | ~~신뢰도 점수 시각화~~ | ✅ 구현 완료 (`ConfidenceScore.tsx`, 섹션 22 참고) |
| **리포트** | ~~TUG/BBS PDF 리포트~~ | ✅ 구현 완료 |
| | ~~일괄 리포트 생성~~ | ✅ 구현 완료 (`/report/batch-pdf`) |
| | ~~맞춤형 템플릿~~ | ✅ 구현 완료 (3개 기본 + 커스텀, 섹션 23 참고) |
| | ~~이메일 전송~~ | ✅ 구현 완료 (`email_service.py`, 섹션 24 참고) |
| | ~~확장 기록 차트~~ | ✅ 구현 완료 (무제한 + 날짜 필터 + 페이지네이션) |
| **임상** | ~~위험 등급 기반 권장 시스템~~ | ✅ 구현 완료 (`rehab_recommendations.py`) |
| | ~~추세 예측/트렌드 분석~~ | ✅ 구현 완료 (`trend_analysis.py`) |
| | ~~전자의무기록(EMR) 연동~~ | ✅ 구현 완료 (FHIR R4, 섹션 26 참고) |
| | ~~자동 치료 프로그램 제안~~ | ✅ 구현 완료 (질환별 맞춤 권장) |
| **관리** | ~~사용자 감사 로그~~ | ✅ 구현 완료 (`audit_logger.py`) |
| | ~~내보내기/백업 기능~~ | ✅ 구현 완료 (CSV + DB 백업/복원) |
| | ~~다기관 지원~~ | ✅ 구현 완료 (`site_manager.py`, 섹션 27 참고) |
| **실시간** | ~~WebSocket 진행률~~ | ✅ 구현 완료 (`websocket.py`) |
| | ~~브라우저 알림~~ | ✅ 구현 완료 (Notification API + Toast) |

> **참고:** 아래 항목은 이전에 구현 완료:
> - ~~연령/성별별 정상치 비교~~ → `normative_data.py` (섹션 10)
> - ~~데이터 분석 대시보드~~ → `AdminDashboard.tsx` (섹션 6.1)
> - ~~보폭/케이던스/대칭성 측정~~ → TUG 질환 프로파일 임상 변수 (PRD_TUG.md 섹션 9)

### 17.4 기술 개선

> ✅ **전체 구현 완료** (2026.02.10)

| 영역 | 개선사항 | 상태 |
|------|----------|------|
| **데이터베이스** | ~~SQLite → PostgreSQL 마이그레이션~~ | ✅ 구현 완료 (`db_factory.py`, 섹션 25 참고) |
| **인증** | ~~JWT 인증 구현~~ | ✅ 구현 완료 (섹션 14.2) |
| **캐싱** | ~~Redis 캐싱~~ | ✅ 구현 완료 (`cache_service.py`, 섹션 25 참고) |
| **배포** | ~~Docker 컨테이너화~~ | ✅ 구현 완료 (섹션 15.8) |
| | ~~Kubernetes 배포~~ | ✅ 구현 완료 (10개 K8s 매니페스트, 섹션 28 참고) |
| | ~~CI/CD 파이프라인~~ | ✅ 구현 완료 (GitHub Actions, 섹션 16.5 참고) |

### 17.5 모바일 애플리케이션
- 네이티브 iOS/Android 앱
- 모바일 직접 영상 촬영
- 오프라인 분석 기능
- 생체 인증

---

## 18. 실시간 알림 시스템 (신규)

> **구현 상태: 구현 완료** (2026.02.10)

### 18.1 WebSocket 서버

| 항목 | 설명 |
|------|------|
| 엔드포인트 | `/ws/{client_id}` |
| 라이브러리 | FastAPI WebSocket (내장) |
| 파일 | `backend/app/routers/websocket.py` |

#### ConnectionManager
- `connect(client_id, websocket)`: 클라이언트 연결 등록
- `disconnect(client_id)`: 연결 해제
- `subscribe(client_id, file_id)`: 특정 분석 작업 구독
- `notify_file_subscribers(file_id, message)`: 구독자에게 알림 전송
- `send_personal_message(client_id, message)`: 개인 메시지 전송

#### 메시지 형식
```json
{
  "type": "progress|completed|error",
  "file_id": "uuid",
  "progress": 0-100,
  "message": "현재 상태 메시지",
  "result": { /* 완료 시 분석 결과 */ }
}
```

#### 스레드 안전성
- `asyncio.run_coroutine_threadsafe()`로 동기 분석 스레드에서 비동기 WebSocket 전송
- `_set_main_loop()`으로 메인 이벤트 루프 참조 저장

### 18.2 WebSocket 클라이언트

| 항목 | 설명 |
|------|------|
| 파일 | `frontend/src/services/websocket.ts` |
| 패턴 | 싱글톤 + 이벤트 에미터 |
| 재연결 | 지수 백오프 (1s → 2s → 4s → ... 최대 30s) |
| 킵얼라이브 | 30초 간격 ping |

### 18.3 브라우저 알림
- `Notification API`: 분석 완료 시 탭이 비활성 상태이면 브라우저 알림
- `Toast 컴포넌트`: 인앱 알림 (success/error/info, 5초 자동 닫힘)
- 기존 polling 방식 폴백 유지

---

## 19. 리포트 강화 및 데이터 내보내기 (신규)

> **구현 상태: 구현 완료** (2026.02.10)

### 19.1 TUG PDF 리포트

`generate_tug_pdf()` in `report_generator.py`

| 섹션 | 내용 |
|------|------|
| 환자 정보 | 이름, 번호, 성별, 생년월일, 키 |
| TUG 총 시간 | 시간 + 평가 배지 (정상/양호/주의/위험) |
| 5단계 분석 | stand_up, walk_out, turn, walk_back, sit_down 소요 시간 |
| 기립/착석 분석 | 속도, 손 지지 여부, 부드러움 점수 |
| 기울기 분석 | 어깨/골반 기울기 (정면 영상) |
| 질환 프로파일 | 적용된 질환 프로파일 정보 |
| TUG 이력 | 과거 검사 기록 테이블 |

### 19.2 BBS PDF 리포트

`generate_bbs_pdf()` in `report_generator.py`

| 섹션 | 내용 |
|------|------|
| 환자 정보 | 이름, 번호, 성별, 생년월일, 키 |
| 총점 | /56점 + 평가 배지 (독립적/보조보행/휠체어) |
| 14항목 점수표 | 항목별 점수 (색상: 0-1 빨강, 2 노랑, 3-4 초록) |
| 해석 가이드 | 점수 범위별 의미 |
| BBS 이력 | 과거 검사 기록 테이블 |

### 19.3 일괄 리포트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/tests/patient/{patient_id}/report/batch-pdf` | 10MWT+TUG+BBS 최신 결과 통합 PDF |

- PyPDF2로 개별 PDF 병합

### 19.4 데이터 내보내기/백업

| 메서드 | 경로 | 설명 | 권한 |
|--------|------|------|------|
| GET | `/api/admin/export/patients-csv` | 전체 환자 CSV | 관리자 |
| GET | `/api/admin/export/tests-csv?test_type=&date_from=&date_to=` | 검사 CSV (필터 지원) | 관리자 |
| GET | `/api/admin/export/backup` | SQLite DB 파일 다운로드 | 관리자 |
| POST | `/api/admin/import/backup` | DB 복원 (업로드, 기존 DB .bak 백업 후 교체) | 관리자 |

---

## 20. 재활 권장 시스템 (신규)

> **구현 상태: 구현 완료** (2026.02.10)

### 20.1 위험 등급별 권장사항

파일: `backend/app/services/rehab_recommendations.py`

| 위험 등급 | 점수 | 권장 프로그램 |
|-----------|------|--------------|
| 정상 (Low) | 90-100 | 유지 운동, 6개월 재평가 |
| 경도 (Mild) | 70-89 | 균형 훈련 2회/주, 보행 운동, 3개월 재평가 |
| 중등도 (Moderate) | 50-69 | 집중 PT 3회/주, 보조기구 평가, 가정 안전 점검, 월별 재평가 |
| 고위험 (High) | 0-49 | 일일 PT, 낙상 예방 프로그램, 가정 환경 수정, 보호자 교육, 주별 모니터링 |

### 20.2 질환별 추가 권장사항

| 질환 | 추가 권장 |
|------|----------|
| 파킨슨병 | 리듬 청각 자극(RAS), 이중과제 훈련, 동결 관리 |
| 뇌졸중 | 체중이동 훈련, 마비측 강화, 구속유도운동치료(CIMT) |
| 슬관절/고관절 OA | 관절 ROM 운동, 수중 치료, 통증 관리 |
| 낙상 위험 | 태극권, 균형 자신감 훈련 |

### 20.3 API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/tests/patient/{patient_id}/recommendations` | 맞춤 재활 권장 + 질환 프로파일 + 위험 등급 |

### 20.4 프론트엔드

| 컴포넌트 | 설명 |
|----------|------|
| `RehabRecommendations.tsx` | 우선순위별 그룹핑, 색상 배지, 접이식 상세, 질환 프로파일 배지 |

---

## 21. 추세 예측/트렌드 분석 (신규)

> **구현 상태: 구현 완료** (2026.02.10)

### 21.1 분석 방법

파일: `backend/app/services/trend_analysis.py`

- **회귀 모델**: numpy polyfit (1차 선형회귀)
- **최소 데이터**: 3개 이상의 검사 결과 필요
- **지원 검사**: 10MWT (속도), TUG (시간), BBS (점수)
- **방향 판정**: slope 기반 improving / stable / declining

### 21.2 출력 데이터

| 항목 | 설명 |
|------|------|
| `trend_direction` | "improving" / "stable" / "declining" |
| `slope_per_week` | 주당 변화량 |
| `r_squared` | 결정계수 (모델 적합도) |
| `predictions` | 1개월, 3개월, 6개월 후 예측값 (상한/하한 신뢰구간) |
| `goal_eta` | 목표 달성 예상일 (목표 설정 시) |

### 21.3 신뢰 구간

```
예측값 ± 1.96 × 표준오차
```

### 21.4 API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/tests/patient/{patient_id}/trends?test_type=10MWT` | 추세 분석 + 예측 + 목표 ETA |

### 21.5 프론트엔드

| 컴포넌트 | 설명 |
|----------|------|
| `TrendChart.tsx` | Recharts 차트: 실제 데이터 + 추세선(점선) + 예측 포인트 + 신뢰구간(음영) + 목표선 + ETA |

---

## 22. 신뢰도 점수 시각화 및 WCAG AA (Phase 3)

> **구현 상태: 구현 완료** (2026.02.10)

### 22.1 ConfidenceScore 컴포넌트

파일: `frontend/src/components/ConfidenceScore.tsx`

| 항목 | 설명 |
|------|------|
| 시각화 | SVG 원형 프로그레스 링 (stroke-dasharray 애니메이션) |
| 색상 | 점수 기반 그라데이션 (0-39: 빨강, 40-69: 노랑, 70-89: 초록, 90-100: 파랑) |
| 크기 | sm (48px) / md (64px) / lg (80px) 3단계 |
| 표시 위치 | PatientDetail, History 페이지의 검사 결과 |

### 22.2 확장 기록 차트 (SpeedChart)

파일: `frontend/src/components/SpeedChart.tsx`

| 개선사항 | 설명 |
|----------|------|
| 데이터 제한 해제 | 10회 제한 → 전체 기록 표시 |
| 날짜 범위 필터 | 시작일/종료일 선택으로 기간 필터링 |
| 페이지네이션 | 한 페이지당 20개씩, 이전/다음 네비게이션 |

### 22.3 WCAG AA 색상 대비

| 수정 파일 | 변경 내용 |
|-----------|-----------|
| `Layout.tsx` | `text-gray-500` → `text-gray-400` (다크 모드) |
| `Dashboard.tsx` | 통계 카드 대비 강화 |
| `PatientDetail.tsx` | 라벨/값 대비 수정 |
| `History.tsx` | 검사 목록 텍스트 대비 |
| `VideoUpload.tsx` | 안내 텍스트 대비 |
| `AdminDashboard.tsx` | 차트/테이블 대비 |
| `BBSForm.tsx` | 점수 입력 대비 |
| `index.css` | WCAG AA 준수 주석 추가 |

---

## 23. 맞춤형 리포트 템플릿 (Phase 3)

> **구현 상태: 구현 완료** (2026.02.10)

파일: `backend/app/services/report_templates.py`

### 23.1 기본 템플릿 (3개)

| 템플릿 | 설명 | 포함 섹션 |
|--------|------|-----------|
| `standard` | 표준 리포트 | 환자 정보, 결과 요약, 상세 분석, 이력 |
| `clinical` | 임상 리포트 | 표준 + 낙상 위험, 질환 프로파일, 재활 권장 |
| `summary` | 요약 리포트 | 환자 정보, 결과 요약만 (간결) |

### 23.2 커스텀 템플릿 CRUD

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/report-templates` | 전체 템플릿 목록 |
| GET | `/api/report-templates/{id}` | 템플릿 상세 |
| POST | `/api/report-templates` | 커스텀 템플릿 생성 |
| PUT | `/api/report-templates/{id}` | 커스텀 템플릿 수정 |
| DELETE | `/api/report-templates/{id}` | 커스텀 템플릿 삭제 |

---

## 24. 이메일 전송 서비스 (Phase 3)

> **구현 상태: 구현 완료** (2026.02.10)

파일: `backend/app/services/email_service.py`

### 24.1 설정

| 환경변수 | 설명 | 기본값 |
|----------|------|--------|
| `SMTP_HOST` | SMTP 서버 주소 | - |
| `SMTP_PORT` | SMTP 포트 | 587 |
| `SMTP_USER` | SMTP 사용자 | - |
| `SMTP_PASSWORD` | SMTP 비밀번호 | - |
| `SMTP_FROM` | 발신자 이메일 | - |

### 24.2 기능

| 기능 | 설명 |
|------|------|
| PDF 첨부 | 검사 리포트 PDF 자동 첨부 |
| 비동기 전송 | aiosmtplib 기반 async/await |
| 프론트엔드 | PatientDetail, History 페이지에 이메일 전송 버튼 + 모달 |

---

## 25. PostgreSQL 및 Redis (Phase 3)

> **구현 상태: 구현 완료** (2026.02.10)

### 25.1 PostgreSQL 지원

| 파일 | 설명 |
|------|------|
| `backend/app/models/db_postgres.py` | PostgreSQL 구현 (36개 메서드) |
| `backend/app/models/db_factory.py` | SQLite/PostgreSQL 팩토리 패턴 |
| `backend/migrations/001_initial_schema.sql` | PostgreSQL 스키마 |

| 환경변수 | 설명 |
|----------|------|
| `DB_TYPE` | `sqlite` (기본) 또는 `postgresql` |
| `DATABASE_URL` | PostgreSQL 연결 문자열 |

### 25.2 Redis 캐싱

파일: `backend/app/services/cache_service.py`

| 항목 | 설명 |
|------|------|
| 캐시 대상 | 대시보드 통계, 환자 목록, 검사 결과 |
| TTL | 5분 (기본), API별 설정 가능 |
| Fallback | Redis 미연결 시 graceful fallback (캐싱 없이 동작) |
| 환경변수 | `REDIS_URL` (기본: `redis://localhost:6379`) |

---

## 26. EMR/FHIR 연동 (Phase 3)

> **구현 상태: 구현 완료** (2026.02.10)

### 26.1 FHIR 클라이언트

파일: `backend/app/services/emr_integration.py`

| 항목 | 설명 |
|------|------|
| 표준 | HL7 FHIR R4 |
| 리소스 | Patient, Observation |
| 인증 | OAuth2 Bearer Token |

### 26.2 API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/emr/status` | EMR 연결 상태 확인 |
| POST | `/api/emr/sync-patient/{patient_id}` | 환자 → FHIR Patient 동기화 |
| POST | `/api/emr/sync-test/{test_id}` | 검사 결과 → FHIR Observation 동기화 |
| GET | `/api/emr/patient/{fhir_id}` | FHIR에서 환자 조회 |

### 26.3 데이터 매핑

| 로컬 필드 | FHIR 필드 |
|-----------|-----------|
| patient.name | Patient.name[0].text |
| patient.birth_date | Patient.birthDate |
| patient.gender | Patient.gender |
| test.walk_speed | Observation.valueQuantity (m/s) |
| test.walk_time | Observation.component (s) |

---

## 27. 다기관 지원 (Phase 3)

> **구현 상태: 구현 완료** (2026.02.10)

파일: `backend/app/services/site_manager.py`

### 27.1 데이터 구조

| 테이블 | 추가 컬럼 |
|--------|-----------|
| `sites` | 새 테이블 (id, name, code, address, phone, created_at) |
| `users` | `site_id` (FK → sites) |
| `patients` | `site_id` (FK → sites) |
| `walk_tests` | `site_id` (FK → sites) |

### 27.2 API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/sites` | 사이트 목록 |
| POST | `/api/sites` | 사이트 생성 (관리자) |
| PUT | `/api/sites/{id}` | 사이트 수정 |
| DELETE | `/api/sites/{id}` | 사이트 삭제 |

### 27.3 데이터 격리

- 일반 사용자: 자신의 `site_id`에 속한 데이터만 조회/수정
- 관리자: 전체 사이트 데이터 접근 가능
- 프론트엔드: `AdminDashboard.tsx`에 사이트 선택 드롭다운

---

## 28. Kubernetes 배포 (Phase 3)

> **구현 상태: 구현 완료** (2026.02.10)

### 28.1 매니페스트 파일

| 파일 | 설명 |
|------|------|
| `k8s/namespace.yaml` | `gait-analyzer` 네임스페이스 |
| `k8s/configmap.yaml` | 환경 설정 (DB_TYPE, REDIS_URL 등) |
| `k8s/secret.yaml` | 민감 정보 (JWT_SECRET, DB 비밀번호) |
| `k8s/pvc.yaml` | 업로드 데이터 영구 볼륨 (10Gi) |
| `k8s/backend-deployment.yaml` | 백엔드 Deployment (2 replicas) |
| `k8s/backend-service.yaml` | 백엔드 ClusterIP Service |
| `k8s/frontend-deployment.yaml` | 프론트엔드 Deployment (2 replicas) |
| `k8s/frontend-service.yaml` | 프론트엔드 ClusterIP Service |
| `k8s/ingress.yaml` | Nginx Ingress (TLS, 경로 라우팅) |
| `k8s/README.md` | 배포 가이드 |

### 28.2 배포 명령

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/
```

---

## 용어집

| 용어 | 설명 |
|------|------|
| 10MWT | 10m Walk Test - 10미터 거리에서 보행 속도를 측정하는 임상 평가 |
| TUG | Timed Up and Go - 의자에서 일어나 3m 걷고 돌아와 앉는 검사 |
| BBS | Berg Balance Scale - 14개 항목으로 균형 능력을 평가하는 검사 |
| 보행 (Gait) | 걷기 동작의 패턴 |
| 랜드마크 | MediaPipe가 감지한 인체 관절 위치 (33개 포인트) |
| 자세 추정 | 영상에서 인체 관절 위치를 감지하는 AI 기술 |
| MediaPipe | Google의 실시간 자세 추정 프레임워크 |
| 낙상 위험 | 환자가 낙상할 가능성 평가 |
| 원근 보정 | 카메라 각도와 환자 크기 기반 측정 조정 |
| 단계 전환 캡처 | TUG 검사의 각 단계 시작 시점 프레임 이미지 |
| 포즈 오버레이 | MediaPipe 스켈레톤이 그려진 분석 영상 |
| 신체 랜드마크 | 얼굴을 제외한 신체 관절 포인트 (인덱스 11-32) |
| 가시성 임계값 | 랜드마크 표시 여부를 결정하는 신뢰도 기준 (50%) |

---

## 29. 보행 경로 분석 및 보행 등급 시스템 (Phase 3.2)

> **구현 상태: 구현 완료** (2026.02.13)

### 29.1 보행 능력 등급 분류 (Perry et al., 1995)

| 등급 | 속도 범위 | 라벨 | 설명 | 색상 |
|------|-----------|------|------|------|
| Lv.1 | ≥ 1.2 m/s | 정상 보행 | 독립적 지역사회 활동 가능 | 녹색 |
| Lv.2 | 0.8–1.2 m/s | 지역사회 보행 | 지역사회 보행 가능, 일부 제한 | 파란색 |
| Lv.3 | 0.4–0.8 m/s | 제한적 보행 | 보조 기구 또는 동반자 필요 | 주황색 |
| Lv.4 | < 0.4 m/s | 실내 보행 | 실내 보행만 가능, 외출 시 휠체어 권장 | 빨간색 |

### 29.2 카카오맵 연동

| 항목 | 설명 |
|------|------|
| SDK | `//dapi.kakao.com/v2/maps/sdk.js` (libraries=services, autoload=false) |
| 검색 | `kakao.maps.services.Places.keywordSearch()` |
| 지도 | `kakao.maps.Map`, `Marker`, `CustomOverlay`, `Polyline` |
| 거리 | Haversine 공식 × 1.3 도보 보정계수 |
| 마커 | 출발지 (파란색) + 도착지 (빨간색) + 점선 경로 |

### 29.3 예상 소요시간 계산

```
도보 거리 = Haversine(출발지, 도착지) × 1.3
환자 예상 시간 = 도보 거리 ÷ 환자 보행속도
일반인 기준 시간 = 도보 거리 ÷ 1.0 m/s
```

### 29.4 커스텀 거리 목표

- 치료사가 환자 주변 목적지 (편의점, 공원, 횡단보도 등) 직접 입력
- 거리(m) + 라벨 + 이모지 선택 (12종 프리셋)
- 환자 보행 속도 기반 예상 소요시간 자동 계산
- **횡단보도 감지**: 라벨에 "횡단보도" 포함 시 신호시간 비교 표시
  - 일반: 보행진입 7초 + 거리 × 1초/m
  - 보호구역: 보행진입 7초 + 거리 × 1.5초/m

### 29.5 UI 위치

| 페이지 | 위치 | 속도 기준 |
|--------|------|-----------|
| PatientDetail | 우측 사이드바 (GoalProgress 아래) | 최근 검사 보행 속도 |
| History | 우측 사이드바 (FallRiskScore 아래) | 10MWT 평균 보행 속도 |

### 29.6 관련 파일

| 파일 | 설명 |
|------|------|
| `frontend/src/components/WalkingRouteCard.tsx` | 보행 경로 + 등급 메인 컴포넌트 |
| `frontend/src/components/GoalProgress.tsx` | 커스텀 거리 목표 컴포넌트 |
| `frontend/index.html` | 카카오맵 SDK 스크립트 |
| `frontend/src/services/api.ts` | walkingRouteApi, distanceGoalApi |
| `backend/app/routers/walking_routes.py` | 보행 경로 REST API |
| `backend/app/routers/distance_goals.py` | 거리 목표 REST API |
| `backend/app/models/database.py` | patient_walking_routes, patient_distance_goals 테이블 |

---

## 30. UI 변경사항 (v3.2.0, 2026.02.13)

| 변경 | 내용 |
|------|------|
| **임상 변수 제거** | Step Time, Swing/Stance 비율, 보행 규칙성 (Stride Regularity) UI에서 삭제 |
| **Stride Length 조건부 표시** | 10MWT(후면 촬영)에서는 숨김, TUG(측면 촬영)에서만 표시 |
| **"정상 범위" → "평균 범위"** | Cadence, Stride Length, Double Support, 어깨/골반 기울기 라벨 변경 |
| **정상 범위 비교 박스 삭제** | PatientDetail의 시간/속도 기반 정상 범위 비교 카드 전체 삭제 |
| **3D 스켈레톤 모델 숨김** | TUG/10MWT 모든 검사에서 TUGPoseViewer3D 숨김 |
| **보행 기울기 평균값** | AngleChart 제목에 평균 각도 표시 (±5° 기준 색상 구분) |
| **치료사 메모 위치 이동** | 보행 기울기 추이 차트 아래로 이동 |
| **History 한국어 라벨** | Cadence → 분당 걸음수, Double Support → 이중 지지기 |
| **대시보드 검사 유형 배지** | 환자 카드 Footer + 최근 검사 위젯에 10MWT/TUG 배지 표시 |

---

## 관련 기술 문서

| 문서 | 설명 |
|------|------|
| [PRD_10MWT.md](./PRD_10MWT.md) | 10MWT 분석 변수, 최적화 과정, 정확도 검증 (v7 알고리즘, 13가지 접근법 비교) |
| [PRD_TUG.md](./PRD_TUG.md) | TUG 분석 변수, 5단계 감지 로직, 다중 신호 융합, 측면/정면 지표 |

---

## 참고 문헌

1. 10미터 보행검사 임상 가이드라인
2. YOLOv8 공식 문서 (Ultralytics)
3. 노인 낙상 위험 평가 연구 자료

---

**문서 끝**
