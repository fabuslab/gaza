"""
Strategy Card Widget for displaying strategy summaries.
"""
import logging
# from PyQt5.QtWidgets import (
#     QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSpacerItem, QSizePolicy
# )
# from PyQt5.QtCore import Qt, pyqtSignal, QSize
# from PyQt5.QtGui import QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal as pyqtSignal, QSize, QEvent
from PySide6.QtGui import QIcon, QMouseEvent, QEnterEvent

from core.database.models.strategy_models import Strategy # 수정된 경로
from core.ui.stylesheets import StyleSheets
from core.ui.constants.colors import Colors
from core.ui.constants.fonts import Fonts, FONT_SIZES
from core.ui.constants.rules import UI_RULES

logger = logging.getLogger(__name__)

class StrategyCardWidget(QFrame): # QFrame을 상속받아 스타일링 용이하게 함
    """단일 매매 전략 정보를 표시하는 카드 위젯"""

    edit_requested = pyqtSignal(str) # 수정 요청 시그널 (strategy_name 전달)
    delete_requested = pyqtSignal(str) # 삭제 요청 시그널 (strategy_name 전달)

    def __init__(self, strategy: Strategy, parent=None):
        super().__init__(parent)
        self.strategy = strategy
        self.init_ui()
        self.setMouseTracking(True) # 마우스 추적 활성화 (호버 감지)
        self.setAutoFillBackground(True) # 배경색 적용 위함
        self.setFrameShape(QFrame.StyledPanel) # 프레임 모양 설정
        self.setFrameShadow(QFrame.Raised) # 그림자 효과
        self.setStyleSheet(StyleSheets.CARD_DEFAULT) # 기본 카드 스타일

    def init_ui(self):
        """카드 UI 초기화"""
        self.setFixedSize(400, 350)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(int(UI_RULES.PADDING_LARGE.replace('px', '')), 
                                         int(UI_RULES.PADDING_LARGE.replace('px', '')), 
                                         int(UI_RULES.PADDING_LARGE.replace('px', '')), 
                                         int(UI_RULES.PADDING_LARGE.replace('px', '')))
        main_layout.setSpacing(int(UI_RULES.MARGIN_NORMAL.replace('px', '')))

        # 1. 제목 영역
        title_layout = QHBoxLayout()
        self.title_label = QLabel(self.strategy.name)
        self.title_label.setStyleSheet(f"""
            font-size: {FONT_SIZES.H3};
            font-weight: bold;
            color: {Colors.TEXT_EMPHASIS};
        """)
        self.title_label.setWordWrap(True)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch(1)
        
        # 수정/삭제 버튼 영역 (초기에는 숨김)
        self.button_widget = QWidget()
        self.button_layout = QHBoxLayout(self.button_widget)
        self.button_layout.setContentsMargins(0,0,0,0)
        self.button_layout.setSpacing(int(UI_RULES.MARGIN_SMALL.replace('px','')))
        
        edit_button = QPushButton("수정")
        edit_button.setStyleSheet(StyleSheets.BUTTON_SECONDARY_SMALL)
        edit_button.clicked.connect(lambda: self.edit_requested.emit(self.strategy.name))
        self.button_layout.addWidget(edit_button)

        delete_button = QPushButton("삭제")
        delete_button.setStyleSheet(StyleSheets.BUTTON_DANGER_SMALL)
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self.strategy.name))
        self.button_layout.addWidget(delete_button)
        self.button_widget.setVisible(False) # 초기 숨김
        title_layout.addWidget(self.button_widget)

        main_layout.addLayout(title_layout)

        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet(f"border-top: 1px solid {Colors.BORDER};")
        main_layout.addWidget(line)

        # 2. 정보 영역 (Grid Layout 사용 고려)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(int(UI_RULES.MARGIN_SMALL.replace('px', '')))
        
        # AI 모델명
        ai_model = self.strategy.params.get('ai_model', '-')
        info_layout.addWidget(self._create_info_label("AI 모델", ai_model))
        
        # AI 모델 요청 주기
        ai_interval = self.strategy.params.get('ai_interval', '-')
        info_layout.addWidget(self._create_info_label("요청 주기", str(ai_interval))) # 문자열로 변환

        # 누적 수익률 (임시)
        profit = self.strategy.params.get('profit_rate', 0.0)
        profit_str = f"{profit:+.2f}%"
        profit_color = Colors.PRIMARY if profit > 0 else Colors.DANGER if profit < 0 else Colors.TEXT_SECONDARY
        info_layout.addWidget(self._create_info_label("누적 수익률", profit_str, value_color=profit_color))

        # 실전 트레이딩 횟수 (임시)
        real_trades = self.strategy.params.get('real_trades', 0)
        info_layout.addWidget(self._create_info_label("실전 트레이딩", str(real_trades)))

        # 모의 트레이딩 횟수 (임시)
        sim_trades = self.strategy.params.get('sim_trades', 0)
        info_layout.addWidget(self._create_info_label("모의 트레이딩", str(sim_trades)))

        # AI 학습 횟수 (임시)
        ai_trainings = self.strategy.params.get('ai_trainings', 0)
        info_layout.addWidget(self._create_info_label("AI 학습 횟수", str(ai_trainings)))
        
        main_layout.addLayout(info_layout)
        main_layout.addStretch(1) # 정보 영역 아래 공간 확보

        self.setLayout(main_layout)

    def _create_info_label(self, key: str, value: str, value_color: str = Colors.TEXT) -> QWidget:
        """정보 라벨 (키: 값 형태) 생성 헬퍼"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(int(UI_RULES.MARGIN_NORMAL.replace('px','')))
        
        key_label = QLabel(key + ":")
        key_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: {FONT_SIZES.SMALL};")
        key_label.setFixedWidth(100) # 키 라벨 너비 고정
        layout.addWidget(key_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {value_color}; font-size: {FONT_SIZES.NORMAL}; font-weight: bold;")
        layout.addWidget(value_label)
        layout.addStretch(1)
        return widget

    def enterEvent(self, event: QEnterEvent): # 이벤트 타입 수정
        """마우스 진입 시 (호버)"""
        logger.debug(f"Mouse enter on card: {self.strategy.name}")
        self.button_widget.setVisible(True)
        self.setStyleSheet(StyleSheets.CARD_HOVER) # 호버 스타일 적용
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent): # 이벤트 타입 수정
        """마우스 벗어날 시"""
        logger.debug(f"Mouse leave from card: {self.strategy.name}")
        self.button_widget.setVisible(False)
        self.setStyleSheet(StyleSheets.CARD_DEFAULT) # 기본 스타일 복원
        super().leaveEvent(event) 