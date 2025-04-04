"""
관심종목 그룹 선택 다이얼로그
"""

import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton,
    QMessageBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Slot as pyqtSlot, Signal as pyqtSignal

from core.ui.constants.colors import Colors
from core.ui.constants.fonts import Fonts, FONT_SIZES
from core.ui.stylesheets import StyleSheets

class GroupSelectDialog(QDialog):
    """관심종목 그룹 선택 다이얼로그"""
    
    def __init__(self, groups: list, parent=None):
        super().__init__(parent)
        self.selected_group = None
        self.groups = groups
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("관심종목 그룹 선택")
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # 안내 메시지
        message = QLabel("추가할 그룹을 선택하세요")
        message.setStyleSheet(f"""
            color: {Colors.TEXT};
            font-size: {FONT_SIZES.NORMAL};
            font-weight: bold;
        """)
        message.setAlignment(Qt.AlignCenter)
        layout.addWidget(message)
        
        # 그룹 선택 콤보박스
        self.group_combo = QComboBox()
        self.group_combo.addItems(self.groups)
        self.group_combo.setStyleSheet(StyleSheets.COMBO_BOX)
        layout.addWidget(self.group_combo)
        
        # 버튼 영역
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 확인 버튼
        ok_button = QPushButton("확인")
        ok_button.setStyleSheet(StyleSheets.BUTTON)
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        # 취소 버튼
        cancel_button = QPushButton("취소")
        cancel_button.setStyleSheet(StyleSheets.BUTTON)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def get_selected_group(self) -> str:
        """선택된 그룹 반환"""
        return self.group_combo.currentText() 