@echo off
echo 웹대시보드 서버 시작...
echo.

echo 백엔드 서버 시작 (별도 창)...
start "Web Dashboard Backend" cmd /k "cd web_dashboard\backend && python main.py"

echo 프론트엔드 서버 시작 (별도 창)...
start "Web Dashboard Frontend" cmd /k "cd web_dashboard\frontend && npm run dev"

echo.
echo 두 서버가 시작되었습니다.
echo 백엔드: http://localhost:8000
echo 프론트엔드: http://localhost:5173
pause
