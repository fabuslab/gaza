"""
매매 전략 목록 표시 위젯 (카드 뷰)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFrame, QScrollArea, QGridLayout, 
    QMessageBox
)
from PySide6.QtCore import Qt, QSize, Slot as pyqtSlot, Signal as pyqtSignal
from PySide6.QtGui import QIcon

from core.strategy.repository import StrategyRepository
from core.strategy.base import AIStrategy
# OpenAIAPI 임포트 제거 (메인 창에서 관리)
# from core.api.openai import OpenAIAPI
from core.ui.constants.colors import Colors
from core.ui.constants.fonts import Fonts, FONT_SIZES
from core.ui.constants.rules import UI_RULES
from core.ui.stylesheets import StyleSheets
import logging
# 실제 카드 위젯 임포트
from ..components.strategy_card import StrategyCardWidget

logger = logging.getLogger(__name__)

class StrategyListWidget(QWidget):
    """전략 목록 카드 뷰를 표시하는 위젯"""

    # 화면 전환 요청 시그널
    create_strategy_requested = pyqtSignal()
    edit_strategy_requested = pyqtSignal(str) # strategy_name 전달

    def __init__(self, parent=None):
        super().__init__(parent)
        self.repository = StrategyRepository()
        self.init_ui()
        self.load_strategies()
        # 최소 사이즈 설정 제거 (메인 창에서 관리)
        # self.setMinimumSize(1024, 768)

    def init_ui(self):
        """UI 초기화 - 카드 리스트 뷰 구성"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(int(UI_RULES.MARGIN_LARGE.replace('px','')), 
                                         int(UI_RULES.MARGIN_LARGE.replace('px','')), 
                                         int(UI_RULES.MARGIN_LARGE.replace('px','')), 
                                         int(UI_RULES.MARGIN_LARGE.replace('px','')))
        main_layout.setSpacing(int(UI_RULES.MARGIN_LARGE.replace('px','')))

        # 상단 버튼 영역
        top_bar_layout = QHBoxLayout()
        
        title = QLabel("매매 전략 목록")
        title.setStyleSheet(f"""
            color: {Colors.TEXT_EMPHASIS};
            font-size: {FONT_SIZES.H2};
            font-weight: bold;
        """)
        top_bar_layout.addWidget(title)
        top_bar_layout.addStretch(1)

        new_strategy_button = QPushButton("매매전략 만들기")
        new_strategy_button.setStyleSheet(StyleSheets.BUTTON_PRIMARY)
        # 클릭 시 시그널 발생시키도록 변경
        new_strategy_button.clicked.connect(self.create_strategy_requested.emit)
        top_bar_layout.addWidget(new_strategy_button)

        main_layout.addLayout(top_bar_layout)

        # 스크롤 영역 설정
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {Colors.BACKGROUND_LIGHT};
            }}
        """)
        
        # 스크롤 영역 내부 위젯 및 레이아웃
        self.scroll_content = QWidget()
        self.card_layout = QGridLayout(self.scroll_content)
        self.card_layout.setSpacing(int(UI_RULES.MARGIN_NORMAL.replace('px',''))) 
        self.card_layout.setAlignment(Qt.AlignTop) # 카드를 위쪽부터 정렬

        scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(scroll_area)

        self.setLayout(main_layout) # 최종 레이아웃 설정

    def load_strategies(self):
        """전략 목록 로드 - 실제 카드 위젯 생성 및 연결"""
        # 기존 위젯 제거
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        strategies = self.repository.list_strategies()
        
        num_columns = max(1, self.width() // 450) # 카드 너비(400px) + 간격 고려
        
        for i, name in enumerate(strategies):
            strategy = self.repository.load(name)
            if strategy:
                # 실제 StrategyCardWidget 생성
                card = StrategyCardWidget(strategy)
                # 시그널 연결
                card.edit_requested.connect(self.edit_strategy_requested.emit) # 수정 요청 전달
                card.delete_requested.connect(self.delete_strategy) # 삭제는 이 위젯에서 처리
                
                row = i // num_columns
                col = i % num_columns
                self.card_layout.addWidget(card, row, col)

    def delete_strategy(self, strategy_name: str):
        """전략 삭제 요청 처리 (카드에서 요청)"""
        reply = QMessageBox.question(
            self,
            "전략 삭제",
            f"'{strategy_name}' 전략을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.repository.delete(strategy_name):
                self.load_strategies() # 카드 목록 새로고침

    def resizeEvent(self, event):
        """창 크기 변경 시 카드 재배치"""
        super().resizeEvent(event)
        
        # 카드 재배치만 수행하고 전략을 다시 로드하지 않음
        self._update_card_layout()
        
    def _update_card_layout(self):
        """카드 레이아웃 업데이트 - 현재 윈도우 크기에 맞게 그리드 재배치"""
        # 현재 그리드에 있는, 모든 카드 위젯 가져오기
        cards = []
        for i in range(self.card_layout.count()):
            item = self.card_layout.itemAt(i)
            if item and item.widget():
                cards.append(item.widget())
                
        # 기존 그리드에서 모든 위젯 제거 (삭제하지 않고 제거만)
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            
        # 새 배치에 맞게 재배치
        num_columns = max(1, self.width() // 450)  # 카드 너비(400px) + 간격 고려
        
        for i, card in enumerate(cards):
            row = i // num_columns
            col = i % num_columns
            self.card_layout.addWidget(card, row, col)

    # closeEvent 제거 (메인 창에서 관리) 