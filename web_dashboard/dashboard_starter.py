
import os
import threading
import subprocess
from PyQt5.QtCore import QObject, pyqtSignal


class DashboardStarter(QObject):
    log_received = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.backend_process = None
        self.frontend_process = None

    def _stream_output(self, pipe, prefix):
        """서브프로세스 출력을 스트리밍하여 로그로 전송합니다."""
        for line in iter(pipe.readline, b''):
            text = line.decode('utf-8', errors='replace').strip()
            if text:
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
        backend_dir = os.path.join("web_dashboard", "backend")
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
            args=(self.backend_process.stdout, "백엔드"),
            daemon=True
        ).start()
        threading.Thread(
            target=self._stream_output,
            args=(self.backend_process.stderr, "백엔드"),
            daemon=True
        ).start()

        frontend_dir = os.path.join("web_dashboard", "frontend")
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
            args=(self.frontend_process.stdout, "프론트엔드"),
            daemon=True
        ).start()
        threading.Thread(
            target=self._stream_output,
            args=(self.frontend_process.stderr, "프론트엔드"),
            daemon=True
        ).start()

    def stop(self):
        """백엔드와 프론트엔드 서버를 종료합니다."""
        if self.backend_process and self.backend_process.poll() is None:
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()

        if self.frontend_process and self.frontend_process.poll() is None:
            self.frontend_process.terminate()
            try:
                self.frontend_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
