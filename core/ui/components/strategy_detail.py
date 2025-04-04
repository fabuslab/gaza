"""
전략 상세 정보 위젯
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit,
    QPushButton, QFrame, QScrollArea,
    QMessageBox
)
from PySide6.QtCore import Qt, pyqtSignal

from core.strategy.base import AIStrategy
from core.ui.constants.colors import Colors
from core.ui.constants.fonts import Fonts, FONT_SIZES
from core.ui.constants.rules import UI_RULES
from core.ui.stylesheets import StyleSheets

logger = logging.getLogger(__name__)

class StrategyDetailWidget(QWidget):
    """전략 상세 정보 위젯"""
    
    strategy_updated = pyqtSignal(AIStrategy)
    
    def __init__(self, strategy: AIStrategy, parent=None):
        super().__init__(parent)
        self.strategy = strategy
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        layout.setSpacing(UI_RULES.MARGIN_NORMAL)
        
        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setStyleSheet(StyleSheets.SCROLLBAR)
        scroll.setWidgetResizable(True)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(UI_RULES.MARGIN_NORMAL)
        
        # 전략 이름
        name_layout = QHBoxLayout()
        name_label = QLabel("전략 이름:")
        name_label.setStyleSheet(StyleSheets.LABEL)
        name_layout.addWidget(name_label)
        
        self.name_input = QLineEdit(self.strategy.name)
        self.name_input.setStyleSheet(StyleSheets.INPUT)
        name_layout.addWidget(self.name_input)
        
        content_layout.addLayout(name_layout)
        
        # 전략 설명
        desc_layout = QVBoxLayout()
        desc_label = QLabel("전략 설명:")
        desc_label.setStyleSheet(StyleSheets.LABEL)
        desc_layout.addWidget(desc_label)
        
        self.desc_input = QTextEdit()
        self.desc_input.setStyleSheet(StyleSheets.INPUT)
        self.desc_input.setText(self.strategy.description)
        self.desc_input.setMinimumHeight(100)
        desc_layout.addWidget(self.desc_input)
        
        content_layout.addLayout(desc_layout)
        
        # 전략 규칙
        rules_layout = QVBoxLayout()
        rules_label = QLabel("전략 규칙:")
        rules_label.setStyleSheet(StyleSheets.LABEL)
        rules_layout.addWidget(rules_label)
        
        self.rules_input = QTextEdit()
        self.rules_input.setStyleSheet(StyleSheets.INPUT)
        self.rules_input.setText("\n".join(self.strategy.rules))
        self.rules_input.setMinimumHeight(200)
        rules_layout.addWidget(self.rules_input)
        
        content_layout.addLayout(rules_layout)
        
        # 전략 파라미터
        params_layout = QVBoxLayout()
        params_label = QLabel("전략 파라미터:")
        params_label.setStyleSheet(StyleSheets.LABEL)
        params_layout.addWidget(params_label)
        
        self.params_input = QTextEdit()
        self.params_input.setStyleSheet(StyleSheets.INPUT)
        self.params_input.setText(str(self.strategy.params))
        self.params_input.setMinimumHeight(100)
        params_layout.addWidget(self.params_input)
        
        content_layout.addLayout(params_layout)
        
        # 저장 버튼
        save_button = QPushButton("저장")
        save_button.setStyleSheet(StyleSheets.BUTTON)
        save_button.clicked.connect(self.save_strategy)
        content_layout.addWidget(save_button)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
        
    def save_strategy(self):
        """전략 저장"""
        try:
            # 이름 업데이트
            self.strategy.name = self.name_input.text()
            
            # 설명 업데이트
            self.strategy.description = self.desc_input.toPlainText()
            
            # 규칙 업데이트
            rules_text = self.rules_input.toPlainText()
            self.strategy.rules = [rule.strip() for rule in rules_text.split("\n") if rule.strip()]
            
            # 파라미터 업데이트
            params_text = self.params_input.toPlainText()
            self.strategy.params = eval(params_text)
            
            # 변경사항 저장
            self.strategy_updated.emit(self.strategy)
            
            QMessageBox.information(self, "성공", "전략이 저장되었습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"전략 저장 실패: {str(e)}") 