@echo off
echo 웹대시보드 라이브러리 설치 시작...
echo.

echo 백엔드 Python 라이브러리 설치 중...
cd web_dashboard\backend
python -m pip install -r requirements.txt
cd ..\..

echo.
echo 프론트엔드 Node.js 라이브러리 설치 중...
cd web_dashboard\frontend
npm install
cd ..\..

echo.
echo 모든 라이브러리 설치 완료!
pause
