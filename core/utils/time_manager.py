"""
시간 관리 모듈
"""

import time
from datetime import datetime
from typing import Optional
# from PyQt5.QtCore import QObject, QTimer, pyqtSignal # 이전
from PySide6.QtCore import QObject, QTimer, Signal as pyqtSignal # 변경

class TimeManager(QObject):
    """시간 관리 클래스 (싱글톤)"""
    
    _instance: Optional['TimeManager'] = None
    time_updated = pyqtSignal(str)  # 시간 업데이트 시그널
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TimeManager, cls).__new__(cls)
            cls._instance.__initialized = False
        return cls._instance
    
    def __init__(self, interval_ms: int = 1000):
        if self.__initialized:
            return
            
        super().__init__()
        self.__initialized = True
        self._current_time = datetime.now()
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_time)
        self.timer.start(interval_ms)  # 1초마다 업데이트
    
    def start(self):
        """타이머 시작"""
        self._update_time()  # 초기 시간 표시
        self.timer.start(1000)  # 1초마다 업데이트
    
    def stop(self):
        """타이머 중지"""
        self.timer.stop()
    
    def _update_time(self):
        """시간 업데이트"""
        self._current_time = datetime.now()
        self.time_updated.emit(self._current_time.strftime("%Y-%m-%d %H:%M:%S"))
    
    @property
    def current_time(self) -> datetime:
        """현재 시간 반환"""
        return self._current_time
    
    def get_formatted_time(self, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """지정된 형식의 시간 문자열 반환"""
        return self._current_time.strftime(format_str)
    
    def get_date(self, format_str: str = "%Y-%m-%d") -> str:
        """날짜 문자열 반환"""
        return self._current_time.strftime(format_str)
    
    def get_time(self, format_str: str = "%H:%M:%S") -> str:
        """시간 문자열 반환"""
        return self._current_time.strftime(format_str) 