"""
매매 전략 메인 컨테이너 창
QStackedWidget을 사용하여 목록 <-> 작성/수정 화면 전환 관리
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFrame, QScrollArea, QGridLayout, QStackedWidget
)
from PySide6.QtCore import Qt, QSize, Slot as pyqtSlot, Signal as pyqtSignal
from PySide6.QtGui import QIcon

from core.strategy.repository import StrategyRepository
from core.strategy.base import AIStrategy
from core.api.openai import OpenAIAPI
from core.ui.constants.colors import Colors
from core.ui.constants.fonts import Fonts, FONT_SIZES
from core.ui.constants.rules import UI_RULES
from core.ui.stylesheets import StyleSheets
# StrategyDetailWidget 임포트 제거
# from core.ui.components.strategy_detail import StrategyDetailWidget
# StrategyCardWidget 임포트 (추후 생성)
# from core.ui.components.strategy_card import StrategyCardWidget
# 실제 위젯 임포트
from .strategy_list_widget import StrategyListWidget 
from .strategy_edit_widget import StrategyEditWidget 

logger = logging.getLogger(__name__)

class StrategyWindow(QWidget):
    """매매 전략 화면의 메인 컨테이너"""

    # 화면 전환 시그널 정의 - 제거 (내부에서 처리)
    # edit_strategy_requested = pyqtSignal(str)
    # create_strategy_requested = pyqtSignal()
    # view_list_requested = pyqtSignal()

    def __init__(self, api: OpenAIAPI, parent=None):
        super().__init__(parent)
        self.api = api
        self.repository = StrategyRepository()
        self.init_ui()
        self.connect_signals()
        self.setMinimumSize(1024, 768) # 최소 사이즈 설정
        self.setWindowTitle("매매 전략 관리")

    def init_ui(self):
        """UI 초기화 - QStackedWidget 설정 및 위젯 추가"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0) # 컨테이너 자체의 마진은 0
        main_layout.setSpacing(0)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # 1. 목록 화면 위젯 생성 및 추가
        self.list_widget = StrategyListWidget()
        self.stack.addWidget(self.list_widget)

        # 2. 작성/수정 화면 위젯 생성 및 추가 (api 인스턴스 전달)
        self.edit_widget = StrategyEditWidget(self.api)
        self.stack.addWidget(self.edit_widget)

        # 초기 화면은 목록 화면으로 설정
        self.stack.setCurrentWidget(self.list_widget)

        self.setLayout(main_layout)

    def connect_signals(self):
        """화면 전환 시그널 연결"""
        # 목록 위젯 -> 편집 위젯 전환
        self.list_widget.create_strategy_requested.connect(self.show_create_widget)
        self.list_widget.edit_strategy_requested.connect(self.show_edit_widget)
        
        # 편집 위젯 -> 목록 위젯 전환
        self.edit_widget.view_list_requested.connect(self.show_list_widget)
        # 저장 후 목록 갱신 및 전환
        self.edit_widget.strategy_saved.connect(self.handle_strategy_saved)

    def show_list_widget(self):
        """목록 화면으로 전환 (목록 갱신 포함)"""
        self.list_widget.load_strategies() # 목록 화면 표시 전 항상 최신 목록 로드
        self.stack.setCurrentWidget(self.list_widget)

    def show_create_widget(self):
        """새 전략 생성 화면으로 전환"""
        self.edit_widget.load_strategy(None) # 새 전략 모드로 편집 위젯 초기화
        self.stack.setCurrentWidget(self.edit_widget)

    def show_edit_widget(self, strategy_name: str):
        """전략 수정 화면으로 전환"""
        self.edit_widget.load_strategy(strategy_name) # 선택된 전략 로드
        self.stack.setCurrentWidget(self.edit_widget)

    def handle_strategy_saved(self, strategy_name: str):
        """전략 저장 완료 후 처리"""
        # 저장 후 목록 화면으로 전환하고 최신 목록 표시
        self.show_list_widget()

    def closeEvent(self, event):
        """창 닫기 이벤트"""
        logger.info("전략 메인 창 닫기")
        
        # 자원 해제 작업 (필요시 추가)
        
        super().closeEvent(event) 