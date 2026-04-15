@echo off
chcp 65001 > nul
echo Installing web dashboard libraries...
echo.

echo Installing backend Python libraries...
cd web_dashboard\backend
python -m pip install -r requirements.txt
cd ..\..

echo.
echo Checking npm installation...
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: npm is not installed or not in PATH.
    echo Please install Node.js from https://nodejs.org/
    echo.
) else (
    echo Installing frontend Node.js libraries...
    cd web_dashboard\frontend
    npm install
    cd ..\..
)

echo.
echo All libraries installed successfully!
pause
