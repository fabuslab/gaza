"""
AI 학습 결과 항목 위젯 (아코디언 아이템)
"""
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTextEdit
)
from PySide6.QtCore import Qt, Signal as pyqtSignal, QEvent, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, Slot
from PySide6.QtGui import QIcon, QMouseEvent, QEnterEvent
from core.ui.constants.colors import Colors
from core.ui.constants.fonts import Fonts, FONT_SIZES
from core.ui.constants.rules import UI_RULES
from core.ui.stylesheets import StyleSheets

logger = logging.getLogger(__name__)

class LearningResultItemWidget(QFrame):
    """AI 학습 결과 하나를 표시하는 아코디언 스타일 위젯"""
    apply_requested = pyqtSignal(str) # 학습 결과 반영 요청 (결과 내용 전달)
    delete_requested = pyqtSignal(str) # 삭제 요청 (결과 ID 또는 제목 전달)

    def __init__(self, result_id: str, title: str, timestamp: str, content: str, parent=None):
        super().__init__(parent)
        self.result_id = result_id
        self.title_text = title
        self.timestamp_text = timestamp
        self.content_text = content
        self.is_expanded = False

        self.init_ui()
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(StyleSheets.ACCORDION_ITEM_DEFAULT) # 기본 스타일
        self.setMouseTracking(True)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. 헤더 영역 (클릭 시 확장/축소)
        self.header_widget = QWidget()
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(int(UI_RULES.PADDING_NORMAL.replace('px','')), 
                                         int(UI_RULES.PADDING_SMALL.replace('px','')), 
                                         int(UI_RULES.PADDING_NORMAL.replace('px','')), 
                                         int(UI_RULES.PADDING_SMALL.replace('px','')))
        
        self.title_label = QLabel(f"{self.title_text} ({self.timestamp_text})")
        self.title_label.setStyleSheet(f"font-size: {FONT_SIZES.NORMAL}; font-weight: bold;")
        header_layout.addWidget(self.title_label, 1)

        # 버튼 영역 (헤더 오른쪽에 배치, 호버 시 표시)
        self.button_widget = QWidget()
        self.button_layout = QHBoxLayout(self.button_widget)
        self.button_layout.setContentsMargins(0,0,0,0)
        self.button_layout.setSpacing(int(UI_RULES.MARGIN_SMALL.replace('px','')))
        
        apply_button = QPushButton("반영")
        apply_button.setStyleSheet(StyleSheets.BUTTON_SECONDARY_SMALL)
        apply_button.setToolTip("이 학습 결과를 현재 투자 전략에 반영합니다.")
        apply_button.clicked.connect(self._on_apply_clicked)
        self.button_layout.addWidget(apply_button)

        delete_button = QPushButton("삭제")
        delete_button.setStyleSheet(StyleSheets.BUTTON_DANGER_SMALL)
        delete_button.setToolTip("이 학습 결과를 삭제합니다.")
        delete_button.clicked.connect(self._on_delete_clicked)
        self.button_layout.addWidget(delete_button)
        self.button_widget.setVisible(False) # 초기 숨김
        header_layout.addWidget(self.button_widget)
        
        # 확장/축소 아이콘 (옵션)
        self.toggle_icon = QLabel("▶") # 초기 상태: 닫힘
        self.toggle_icon.setStyleSheet(f"font-size: {FONT_SIZES.SMALL}; color: {Colors.TEXT_SECONDARY};")
        header_layout.addWidget(self.toggle_icon)

        self.header_widget.mousePressEvent = self.toggle_expansion # 헤더 클릭 이벤트 연결
        self.header_widget.setCursor(Qt.PointingHandCursor)
        main_layout.addWidget(self.header_widget)

        # 2. 내용 영역 (숨겨진 상태로 시작)
        self.content_widget = QFrame()
        content_layout = QVBoxLayout(self.content_widget)
        self.content_text_edit = QTextEdit()
        self.content_text_edit.setPlainText(self.content_text)
        self.content_text_edit.setReadOnly(True)
        self.content_text_edit.setStyleSheet(StyleSheets.TEXT_EDIT_READONLY + " border: none; padding: 5px;")
        content_layout.addWidget(self.content_text_edit)
        self.content_widget.setVisible(False)
        self.content_widget.setMaximumHeight(0) # 애니메이션 위해 초기 높이 0
        self.content_widget.setStyleSheet(f"background-color: {Colors.BACKGROUND_DARKEST}; border-top: 1px solid {Colors.BORDER};")
        main_layout.addWidget(self.content_widget)
        
        # 애니메이션 설정
        self.animation = QPropertyAnimation(self.content_widget, b"maximumHeight")
        self.animation.setDuration(200) # 0.2초 애니메이션
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)

        self.setLayout(main_layout)

    def toggle_expansion(self, event: QMouseEvent = None):
        """내용 영역 확장/축소 토글"""
        target_height = 0
        if not self.is_expanded:
            # 펼칠 때: 내용의 실제 필요 높이 계산 (근사치)
            doc_height = self.content_text_edit.document().size().height()
            target_height = int(doc_height) + 10 # 여유 공간 추가
            self.toggle_icon.setText("▼") # 아이콘 변경
        else:
            target_height = 0 # 접을 때
            self.toggle_icon.setText("▶") # 아이콘 변경

        self.animation.stop()
        self.animation.setStartValue(self.content_widget.maximumHeight())
        self.animation.setEndValue(target_height)
        
        # 애니메이션 시작 전에 위젯을 보이게 설정 (펼칠 때)
        if not self.is_expanded:
             self.content_widget.setVisible(True)
             
        # 애니메이션 완료 후 위젯 숨기기 (접을 때)
        def on_animation_finished():
            if self.is_expanded:
                self.content_widget.setVisible(False)
                
        self.animation.finished.connect(on_animation_finished)
        self.animation.start()
        
        self.is_expanded = not self.is_expanded
        self.setStyleSheet(StyleSheets.ACCORDION_ITEM_EXPANDED if self.is_expanded else StyleSheets.ACCORDION_ITEM_DEFAULT)
        
        # 부모 위젯에게 크기 변경 알림 (필요시)
        # self.parentWidget().updateGeometry()

    def enterEvent(self, event: QEvent): # 타입 수정
        self.button_widget.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        # 마우스가 버튼 위에 있지 않을 때만 숨김
        if not self.button_widget.underMouse():
            self.button_widget.setVisible(False)
        super().leaveEvent(event)

    def _on_apply_clicked(self):
        self.apply_requested.emit(self.content_text)

    def _on_delete_clicked(self):
        self.delete_requested.emit(self.result_id) 