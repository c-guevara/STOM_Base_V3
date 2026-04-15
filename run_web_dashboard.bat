@echo off
chcp 65001 > nul
echo Starting web dashboard servers...
echo.

echo Checking npm installation...
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: npm is not installed or not in PATH.
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b
)

echo Starting backend server (separate window)...
start "Web Dashboard Backend" cmd /k "cd web_dashboard\backend && python main.py"

echo Starting frontend server (separate window)...
start "Web Dashboard Frontend" cmd /k "cd web_dashboard\frontend && npm run dev"

echo.
echo Both servers started.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
pause
