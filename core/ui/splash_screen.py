"""
스플래시 화면 모듈
"""

from PySide6.QtWidgets import QApplication, QSplashScreen, QVBoxLayout, QLabel
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt, QTimer
from core.ui.constants.colors import Colors
from core.ui.constants.fonts import Fonts, FONT_SIZES
from core.ui.stylesheets import StyleSheets

class SplashScreen(QSplashScreen):
    """스플래시 화면"""
    
    def __init__(self):
        # 빈 픽스맵으로 초기화
        super().__init__(QPixmap(500, 300))
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        # 배경색 설정
        self.setStyleSheet(f"""
            QSplashScreen {{
                background-color: {Colors.PRIMARY};
                border-radius: 10px;
            }}
        """)
        
        # 중앙 위젯
        central_widget = QWidget(self)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignCenter)
        
        # 타이틀
        title = QLabel("가즈아! 트레이딩")
        title.setStyleSheet(f"""
            color: white;
            font-size: {FONT_SIZES.TITLE};
            font-weight: bold;
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 버전
        version = QLabel("v1.0.0")
        version.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.8);
            font-size: {FONT_SIZES.SMALL};
        """)
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        
        # 중앙 위젯 크기 설정
        central_widget.setFixedSize(self.size())
        
    def show_and_wait(self, duration_ms: int = 2000):
        """스플래시 화면 표시 및 대기
        
        Args:
            duration_ms: 표시 시간 (밀리초)
        """
        self.show()
        QTimer.singleShot(duration_ms, self.close) 