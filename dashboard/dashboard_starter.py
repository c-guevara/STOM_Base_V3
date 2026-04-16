
import os
import threading
import subprocess
from PyQt5.QtCore import QObject, pyqtSignal
from utility.static_method.static import qtest_qwait


class DashboardStarter(QObject):
    log_received = pyqtSignal(str)

    def __init__(self, market=1, frontend_port=3000):
        super().__init__()
        self.market = market
        self.frontend_port = frontend_port
        self.backend_port  = frontend_port + 5000
        self.backend_process = None
        self.frontend_process = None

    def _stream_output(self, pipe, prefix, is_stderr=False):
        """서브프로세스 출력을 스트리밍하여 오류만 로그로 전송합니다."""
        error_keywords = ['error', 'Error', 'ERROR', 'exception', 'Exception', 'EXCEPTION', 'failed', 'Failed', 'FAILED']
        info_keywords = ['INFO', 'info']

        for line in iter(pipe.readline, b''):
            text = line.decode('utf-8', errors='replace').strip()
            if text:
                # INFO 로그는 무시
                if any(keyword in text for keyword in info_keywords):
                    continue
                # stderr는 무조건 오류로 간주, stdout은 오류 키워드가 있는 경우만 오류로 간주
                is_error = is_stderr or any(keyword in text for keyword in error_keywords)
                if is_error:
                    self.log_received.emit(f"웹대시보드 {prefix} - {text}")
        pipe.close()

    def _get_startupinfo(self):
        """Windows에서 콘솔 창을 숨기기 위한 startupinfo를 반환합니다."""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        return startupinfo

    def start(self):
        """백엔드와 프론트엔드 서버를 subprocess로 시작합니다."""
        backend_dir = os.path.join("dashboard", "backend")
        self.backend_process = subprocess.Popen(
            ["python", "main.py"],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=self._get_startupinfo(),
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        threading.Thread(
            target=self._stream_output,
            args=(self.backend_process.stdout, "백엔드", False),
            daemon=True
        ).start()
        threading.Thread(
            target=self._stream_output,
            args=(self.backend_process.stderr, "백엔드", True),
            daemon=True
        ).start()

        qtest_qwait(2)
        frontend_dir = os.path.join("dashboard", "frontend")
        self.frontend_process = subprocess.Popen(
            ["node", "node_modules/vite/bin/vite.js", "--host", "0.0.0.0"],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=self._get_startupinfo(),
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        threading.Thread(
            target=self._stream_output,
            args=(self.frontend_process.stdout, "프론트엔드", False),
            daemon=True
        ).start()
        threading.Thread(
            target=self._stream_output,
            args=(self.frontend_process.stderr, "프론트엔드", True),
            daemon=True
        ).start()

    def stop(self):
        """백엔드와 프론트엔드 서버를 종료합니다."""
        if self.backend_process and self.backend_process.poll() is None:
            self.backend_process.kill()

        if self.frontend_process and self.frontend_process.poll() is None:
            self.frontend_process.kill()
