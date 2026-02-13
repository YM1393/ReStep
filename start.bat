@echo off
chcp 65001 > nul
title 10m Walk Test - Launcher

echo ========================================
echo    10m 보행 검사 시스템 시작
echo ========================================
echo.

:: 백엔드 서버 시작 (새 창에서)
echo [1/2] 백엔드 서버 시작 중...
start "Backend Server - FastAPI" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: 잠시 대기 (백엔드가 먼저 시작되도록)
timeout /t 3 /nobreak > nul

:: 프론트엔드 서버 시작 (새 창에서)
echo [2/2] 프론트엔드 서버 시작 중...
start "Frontend Server - Vite" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo    서버가 시작되었습니다!
echo ========================================
echo.
echo  - 백엔드:    http://localhost:8000
echo  - 프론트엔드: http://localhost:5173
echo  - API 문서:   http://localhost:8000/docs
echo.
echo  종료하려면 각 서버 창을 닫으세요.
echo ========================================
echo.

:: 브라우저 자동 열기 (5초 후)
timeout /t 5 /nobreak > nul
start http://localhost:5173

pause
