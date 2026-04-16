@echo off
chcp 65001 > nul
echo Installing web dashboard libraries...
echo.

echo Installing backend Python libraries...
cd dashboard\backend
python -m pip install -r requirements.txt
cd ..\..

echo.
echo Checking npm installation...
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo Node.js not found. Installing automatically via winget...
    winget install --id OpenJS.NodeJS -e --source winget --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo ERROR: Automatic installation failed.
        echo Please install Node.js manually from https://nodejs.org/
        echo.
    ) else (
        echo Node.js installed successfully!
        echo Installing frontend Node.js libraries...
        cd dashboard\frontend
        npm install
        cd ..\..
    )
) else (
    echo Installing frontend Node.js libraries...
    cd dashboard\frontend
    npm install
    cd ..\..
)

echo.
echo All libraries installed successfully!
pause
