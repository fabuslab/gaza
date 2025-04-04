"""
트레이딩 메인 화면 모듈 - 검색과 관심 그룹 통합 화면
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QLabel, QPushButton, QFrame, QDialog,
    QMessageBox
)
from PySide6.QtCore import Qt, pyqtSignal
from PySide6.QtGui import QIcon

from core.ui.components.stock_search_component import StockSearchComponent
from core.ui.windows.favorites_window import FavoritesWindow
from core.ui.dialogs.group_select_dialog import GroupSelectDialog
from core.api.kiwoom import KiwoomAPI
from core.modules.watchlist import WatchlistModule
from core.ui.constants.colors import Colors
from core.ui.constants.fonts import FONT_SIZES
from core.ui.constants.rules import UI_RULES
from core.ui.stylesheets import StyleSheets

logger = logging.getLogger(__name__)

class TradingMainWindow(QWidget):
    """트레이딩 메인 화면 - 검색과 관심 그룹 통합"""
    
    def __init__(self, kiwoom_api: KiwoomAPI, parent=None):
        super().__init__(parent)
        self.kiwoom_api = kiwoom_api
        self.watchlist_module = WatchlistModule(self.kiwoom_api)
        
        # 기본 설정
        self.setWindowTitle("가즈아! 트레이딩")
        self.setMinimumWidth(1200)
        self.setMinimumHeight(800)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 메인 스플리터 (좌우 분할)
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setHandleWidth(2)
        main_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {Colors.BORDER};
            }}
            QSplitter::handle:horizontal {{
                width: 2px;
            }}
            QSplitter::handle:hover {{
                background-color: {Colors.PRIMARY};
            }}
        """)
        
        # 왼쪽 영역 - 검색 컴포넌트
        left_panel = QFrame()
        left_panel.setStyleSheet(StyleSheets.FRAME)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        left_header = QLabel("종목 검색")
        left_header.setStyleSheet(f"""
            color: {Colors.TEXT};
            font-size: {FONT_SIZES.LARGE};
            font-weight: bold;
            padding-bottom: 5px;
        """)
        left_layout.addWidget(left_header)
        
        # 검색 컴포넌트 추가
        self.search_component = StockSearchComponent(self.kiwoom_api, self)
        self.search_component.stock_selected.connect(self.handle_stock_selected)
        left_layout.addWidget(self.search_component)
        
        # 오른쪽 영역 - 관심 그룹
        right_panel = QFrame()
        right_panel.setStyleSheet(StyleSheets.FRAME)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        right_header = QLabel("관심 그룹")
        right_header.setStyleSheet(f"""
            color: {Colors.TEXT};
            font-size: {FONT_SIZES.LARGE};
            font-weight: bold;
            padding-bottom: 5px;
        """)
        right_layout.addWidget(right_header)
        
        # 관심종목 창 임베드
        self.favorites_widget = FavoritesWindow(self.kiwoom_api)
        # 기존의 검색 영역 숨기기
        search_frame = self.favorites_widget.findChild(QFrame, "search_frame")
        if search_frame:
            search_frame.hide()
        right_layout.addWidget(self.favorites_widget)
        
        # 스플리터에 패널 추가
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        
        # 스플리터 비율 설정 (4:6 비율)
        total_width = self.width()
        main_splitter.setSizes([total_width * 0.4, total_width * 0.6])
        
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)
        
    def handle_stock_selected(self, stock_info):
        """검색에서 종목 선택 시 처리"""
        if not stock_info or 'stk_cd' not in stock_info:
            return
            
        stock_code = stock_info['stk_cd']
        stock_name = stock_info.get('stk_nm', f"종목 {stock_code}")
        
        logger.info(f"종목 선택됨: {stock_code} ({stock_name})")
        
        # 관심종목에 추가할지 묻기
        reply = QMessageBox.question(
            self,
            "관심종목 추가",
            f"{stock_name}({stock_code})을 관심종목에 추가하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 그룹 목록 조회
            groups = self.kiwoom_api.get_favorite_groups()
            if not groups:
                QMessageBox.warning(self, "오류", "관심종목 그룹이 없습니다.")
                return
                
            # 그룹 선택 다이얼로그 표시
            dialog = GroupSelectDialog(groups, self)
            if dialog.exec_() == QDialog.Accepted:
                group_name = dialog.get_selected_group()
                if self.kiwoom_api.add_favorite_stock(stock_code, group_name):
                    QMessageBox.information(self, "알림", "관심종목에 추가되었습니다.")
                    # 관심종목 목록 갱신
                    self.favorites_widget.load_favorites()
                else:
                    QMessageBox.warning(self, "오류", "관심종목 추가에 실패했습니다.")
    
    def closeEvent(self, event):
        """창 닫기 이벤트"""
        logger.info("트레이딩 메인 화면 닫기")
        # 연결된 위젯의 자원 해제
        self.favorites_widget.close()
        super().closeEvent(event) 