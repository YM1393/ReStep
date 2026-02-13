# 10m Walk Test - Clinical Gait Analysis System

물리치료사를 위한 10m 보행 검사 분석 시스템입니다. MediaPipe Pose를 사용하여 동영상에서 환자의 보행 속도를 자동으로 분석합니다.

## Features

- **환자 관리**: 환자 등록, 검색, 수정, 삭제
- **동영상 분석**: MediaPipe Pose 기반 자동 보행 분석
- **원근법 보정**: 환자 키를 이용한 정확한 거리 계산
- **자동 감지**: 걷기 시작/끝 자동 감지
- **히스토리**: 검사 기록 조회 및 속도 변화 그래프
- **비교 분석**: 최근/이전 검사 비교 및 낙상 위험도 변화 안내
- **리포트**: PDF/CSV 다운로드

## Tech Stack

- **Frontend**: React + TypeScript + Vite + TailwindCSS
- **Backend**: Python + FastAPI
- **AI/ML**: MediaPipe Pose Heavy (model_complexity=2)
- **Database**: Supabase (PostgreSQL)
- **Charts**: Recharts

## Setup

### 1. Supabase 설정

1. [Supabase](https://supabase.com)에서 새 프로젝트 생성
2. SQL Editor에서 `supabase_schema.sql` 실행
3. Project Settings > API에서 URL과 anon key 복사

### 2. Backend 설정

```bash
cd backend

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# .env 파일 설정
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_KEY=your-anon-key

# 서버 실행
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend 설정

```bash
cd frontend

# 패키지 설치
npm install

# 개발 서버 실행
npm run dev
```

### 4. 접속

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Usage

### 1. 환자 등록
- Dashboard에서 "New Patient" 클릭
- 환자 정보 입력 (키 입력 필수 - 원근법 보정에 사용)

### 2. 동영상 촬영 가이드
- 환자의 **측후면**에서 촬영
- 10m 보행 경로 전체가 화면에 보이도록
- 환자가 카메라에서 멀어지는 방향으로 걷기
- 밝은 조명 환경 권장

### 3. 검사 수행
- 환자 상세 페이지에서 "New Test" 클릭
- 동영상 업로드 (드래그앤드롭 지원)
- 자동 분석 대기 후 결과 확인

### 4. 결과 확인
- 보행 시간 (초)
- 보행 속도 (m/s)
- PDF/CSV 리포트 다운로드

### 5. 히스토리 비교
- History 페이지에서 전체 기록 확인
- 속도 변화 그래프 확인
- 이전 검사 대비 낙상 위험도 변화 확인

## Walking Speed Reference

| Speed | Assessment | Fall Risk |
|-------|------------|-----------|
| ≥ 1.2 m/s | Normal | Low |
| 1.0-1.2 m/s | Mildly reduced | Moderate |
| 0.8-1.0 m/s | Moderately reduced | High |
| < 0.8 m/s | Severely reduced | Very High |

## Project Structure

```
10M_WT/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI 앱
│   │   ├── models/           # DB 모델
│   │   ├── routers/          # API 라우터
│   │   └── services/         # 비즈니스 로직
│   ├── analysis/
│   │   └── gait_analyzer.py  # MediaPipe Pose 분석
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # UI 컴포넌트
│   │   ├── pages/           # 페이지
│   │   ├── services/        # API 호출
│   │   └── types/           # TypeScript 타입
│   └── package.json
├── uploads/                  # 업로드된 동영상
└── supabase_schema.sql      # DB 스키마
```

## API Endpoints

### Patients
- `POST /api/patients/` - 환자 등록
- `GET /api/patients/` - 환자 목록
- `GET /api/patients/search?q=` - 환자 검색
- `GET /api/patients/{id}` - 환자 상세
- `PUT /api/patients/{id}` - 환자 수정
- `DELETE /api/patients/{id}` - 환자 삭제

### Tests
- `POST /api/tests/{patient_id}/upload` - 동영상 업로드 및 분석
- `GET /api/tests/status/{file_id}` - 분석 상태 조회
- `GET /api/tests/patient/{patient_id}` - 환자 검사 기록
- `GET /api/tests/patient/{patient_id}/compare` - 비교 분석
- `GET /api/tests/{test_id}/report/pdf` - PDF 다운로드
- `GET /api/tests/{test_id}/report/csv` - CSV 다운로드

## License

MIT License
