@echo off
chcp 65001 > nul
title 10m Walk Test - Stop Servers

echo ========================================
echo    10m 보행 검사 시스템 종료
echo ========================================
echo.

:: Python (uvicorn) 프로세스 종료
echo [1/2] 백엔드 서버 종료 중...
taskkill /F /IM python.exe /T 2>nul
if %errorlevel%==0 (
    echo       백엔드 서버가 종료되었습니다.
) else (
    echo       백엔드 서버가 실행 중이 아닙니다.
)

:: Node.js (Vite) 프로세스 종료
echo [2/2] 프론트엔드 서버 종료 중...
taskkill /F /IM node.exe /T 2>nul
if %errorlevel%==0 (
    echo       프론트엔드 서버가 종료되었습니다.
) else (
    echo       프론트엔드 서버가 실행 중이 아닙니다.
)

echo.
echo ========================================
echo    모든 서버가 종료되었습니다.
echo ========================================
echo.

pause
