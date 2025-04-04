"""
통합 종목 검색 및 관심 종목 화면
"""

import logging
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QFrame, QDialog,
    QMessageBox, QApplication, QLineEdit, QProgressBar, QMenu,
    QMainWindow, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QInputDialog, QListWidget, QListWidgetItem, QGroupBox, QAbstractScrollArea, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal as pyqtSignal, QPoint, QTimer, Slot as pyqtSlot, QEvent
from PySide6.QtGui import QCursor, QAction, QKeySequence

from core.api.kiwoom import KiwoomAPI
from core.ui.components.stock_search_component import StockSearchComponent
from core.ui.components.stock_table import StockTableWidget
from core.ui.components.watchlist_group_panel import WatchlistGroupPanel
from core.ui.dialogs.group_select_dialog import GroupSelectDialog
from core.modules.watchlist import WatchlistModule
from core.ui.constants.colors import Colors
from core.ui.constants.fonts import Fonts, FONT_SIZES
from core.ui.constants.rules import UI_RULES
from core.ui.stylesheets import StyleSheets

logger = logging.getLogger(__name__)

class HoverButton(QPushButton):
    """마우스 호버 시 표시되는 버튼"""
    
    def __init__(self, parent=None, text="", is_add=True):
        """
        Args:
            parent: 부모 위젯
            text: 버튼 텍스트
            is_add: 추가 버튼 여부 (True: 추가, False: 삭제)
        """
        super().__init__(text, parent)
        self.is_add = is_add
        self.setStyleSheet(StyleSheets.ADD_BUTTON if is_add else StyleSheets.DELETE_BUTTON)
        self.setFixedSize(60, 25)
        self.setCursor(Qt.PointingHandCursor)
        self.hide()  # 기본적으로 숨김 상태

class IntegratedSearchWatchlistWindow(QMainWindow):
    """통합 검색 및 관심 종목 화면"""
    
    chart_requested = pyqtSignal(str, str)  # 종목 코드, 종목명 전달 시그널 복원

    def __init__(self, kiwoom_api: KiwoomAPI, parent=None):
        super().__init__(parent)
        logger.info("통합 검색 및 관심 종목 화면 초기화 시작")
        self.kiwoom_api = kiwoom_api
        
        # 관심목록 모듈 초기화
        self.watchlist_module = WatchlistModule(self.kiwoom_api)
        
        # 현재 선택된 관심그룹
        self.current_group_id = 1  # 기본 그룹 ID
        self.current_group_name = "기본 그룹"
        
        # 로딩 상태
        self.is_loading = False
        
        # 마우스 호버 위치 저장 (테이블 행 인덱스)
        self.search_hover_row = -1
        self.watchlist_hover_row = -1
        
        # 마우스 호버 버튼
        self.search_hover_button = None
        self.watchlist_hover_button = None
        
        # 현재 검색 결과 저장용 변수
        self.current_search_results = []
        
        # 기본 설정
        self.setWindowTitle("종목 검색 및 관심그룹")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(StyleSheets.WIDGET)
        
        self.init_ui()
        
        # WatchlistModule의 시그널 연결
        self.watchlist_module.watchlist_updated.connect(self._on_watchlist_updated)
        self.watchlist_module.watchlist_group_updated.connect(self._on_watchlist_groups_updated)
        self.watchlist_module.error_occurred.connect(self._on_error_occurred)
        
        # --- 수정 시작: 초기 데이터 로드 및 타이머 시작 주석 해제 ---
        # logger.debug("초기 데이터 로드 및 타이머 시작 임시 주석 처리됨") # 로그는 제거
        self.load_watchlist_groups() # 그룹 목록 먼저 로드
        self.watchlist_module.set_active_group(self.current_group_id) # 모듈에 활성 그룹 알림 (업데이트 시작 트리거)
        
        # 검색 결과 업데이트 타이머
        self.search_result_timer = QTimer()
        self.search_result_timer.timeout.connect(self.update_search_results)
        self.search_result_timer.start(2000)  # 2초마다 업데이트
        # --- 수정 끝 ---

        logger.info("통합 검색 및 관심 종목 화면 초기화 완료")
    
    def init_ui(self):
        """UI 초기화"""
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 1. 검색 영역
        search_container = QFrame()
        search_container.setFixedHeight(44) # 최소 높이 대신 고정 높이 설정
        search_container.setStyleSheet(StyleSheets.SEARCH_CONTAINER)
        search_layout = QVBoxLayout(search_container)
        search_layout.setContentsMargins(0, 5, 0, 5)  # 상하 여백 추가
        search_layout.setSpacing(0)  # 간격 제거
        
        # 검색 컴포넌트
        self.search_component = StockSearchComponent(self.kiwoom_api)
        self.search_component.search_completed.connect(self.on_search_result)
        search_layout.addWidget(self.search_component)
        
        main_layout.addWidget(search_container)
        
        # 2. 검색 결과 영역
        result_container = QFrame()
        result_container.setStyleSheet(StyleSheets.RESULT_CONTAINER)
        result_layout = QVBoxLayout(result_container)
        result_layout.setContentsMargins(10, 10, 10, 10)
        
        # 검색 결과 레이블
        result_label = QLabel("검색 결과")
        result_label.setStyleSheet(StyleSheets.RESULT_TITLE)
        result_layout.addWidget(result_label)
        
        # 검색 결과 테이블
        self.result_table = StockTableWidget()
        self.result_table.setMouseTracking(True)  # 마우스 이동 추적
        self.result_table.cellEntered.connect(self.on_result_table_hover)
        self.result_table.leaveEvent = self.on_result_table_leave
        self.result_table.viewport().installEventFilter(self)  # 이벤트 필터 설치
        self.result_table.setContextMenuPolicy(Qt.CustomContextMenu)  # 컨텍스트 메뉴 정책 설정
        self.result_table.customContextMenuRequested.connect(self.show_result_context_menu)  # 컨텍스트 메뉴 이벤트 연결
        # 검색 결과 테이블 더블클릭 시그널 연결
        self.result_table.stockDoubleClicked.connect(self._on_search_table_double_clicked)
        result_layout.addWidget(self.result_table)
        
        main_layout.addWidget(result_container, 1)  # 검색 결과에 비율 1 할당
        
        # 3. 관심 그룹 영역 (수평 분할)
        watchlist_frame = QFrame()
        watchlist_frame.setStyleSheet("""
            QFrame {
                background-color: """ + Colors.BACKGROUND + """;
                border: 1px solid """ + Colors.BORDER + """;
                border-radius: """ + UI_RULES.BORDER_RADIUS + """;
                padding: 0px;
            }
        """)
        
        # 관심 그룹 영역 내부 수평 스플리터
        watchlist_splitter = QSplitter(Qt.Horizontal)
        watchlist_splitter.setChildrenCollapsible(False)
        
        # 3-1. 왼쪽: 관심 그룹 리스트
        left_panel = QFrame()
        left_panel.setStyleSheet("""
            QFrame {
                background-color: """ + Colors.BACKGROUND + """;
                border: none;
                padding: 0px;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)
        
        # 관심 그룹 타이틀과 추가 버튼
        group_title = QLabel("관심 그룹")
        group_title.setStyleSheet(StyleSheets.RESULT_TITLE)
        
        add_group_button = QPushButton("+")
        add_group_button.setStyleSheet(StyleSheets.BUTTON)
        add_group_button.setFixedSize(30, 30)
        add_group_button.setToolTip("관심 그룹 추가")
        add_group_button.clicked.connect(self.on_add_group)
        
        title_layout = QHBoxLayout()
        title_layout.addWidget(group_title)
        title_layout.addStretch()
        title_layout.addWidget(add_group_button)
        left_layout.addLayout(title_layout)
        
        # 관심 그룹 리스트
        self.group_list = QListWidget()
        self.group_list.setEnabled(True)  # 명시적으로 활성화
        self.group_list.setFocusPolicy(Qt.StrongFocus)  # 포커스 정책 강화
        self.group_list.setSelectionMode(QAbstractItemView.SingleSelection)  # 단일 선택 모드 명시적 설정
        self.group_list.itemClicked.connect(self.on_group_item_clicked)
        self.group_list.currentItemChanged.connect(self.on_group_item_changed)
        # self.group_list.itemEntered.connect(self.on_group_item_hover)  # <<< 임시 주석 처리
        left_layout.addWidget(self.group_list)
        
        # 관심그룹 삭제 버튼 초기화
        self.group_delete_button = QPushButton("×")
        self.group_delete_button.setStyleSheet(StyleSheets.GROUP_DELETE_BUTTON)
        # self.group_delete_button.clicked.connect(self.on_delete_group) # <<< 슬롯이 없으므로 주석 처리
        self.group_delete_button.hide()  # 초기에는 숨김 상태
        self.group_delete_button.setParent(self.group_list.viewport())  # 뷰포트를 부모로 설정
        
        # 현재 호버 중인 그룹 아이템 인덱스
        self.group_hover_index = -1
        
        # 3-2. 오른쪽: 관심 그룹 종목 목록
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame {
                background-color: """ + Colors.BACKGROUND + """;
                border: none;
                padding: 0px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)
        
        # 관심 그룹 레이블 (선택된 그룹명 표시)과 전체 삭제 버튼
        watchlist_header = QHBoxLayout()
        
        self.watchlist_label = QLabel("관심 그룹: 기본 그룹")
        self.watchlist_label.setStyleSheet(StyleSheets.RESULT_TITLE)
        watchlist_header.addWidget(self.watchlist_label)
        
        watchlist_header.addStretch()
        
        # 전체 삭제 버튼 추가
        clear_all_button = QPushButton("전체 삭제")
        clear_all_button.setStyleSheet(StyleSheets.DELETE_BUTTON)
        clear_all_button.setFixedSize(80, 30)
        clear_all_button.clicked.connect(self.on_clear_all_stocks)
        watchlist_header.addWidget(clear_all_button)
        
        right_layout.addLayout(watchlist_header)
        
        # 관심 그룹 테이블
        self.watchlist_table = StockTableWidget()
        self.watchlist_table.setMouseTracking(True)  # 마우스 이동 추적
        self.watchlist_table.cellEntered.connect(self.on_watchlist_table_hover)
        self.watchlist_table.leaveEvent = self.on_watchlist_table_leave
        self.watchlist_table.viewport().installEventFilter(self)  # 이벤트 필터 설치
        self.watchlist_table.setContextMenuPolicy(Qt.CustomContextMenu)  # 컨텍스트 메뉴 정책 설정
        self.watchlist_table.customContextMenuRequested.connect(self.show_watchlist_context_menu)  # 컨텍스트 메뉴 이벤트 연결
        # 관심 그룹 테이블 더블클릭 시그널 연결
        self.watchlist_table.stockDoubleClicked.connect(self._on_stock_table_double_clicked)
        right_layout.addWidget(self.watchlist_table)
        
        # 왼쪽 패널 최소/최대 너비 설정
        left_panel.setMinimumWidth(100)
        left_panel.setMaximumWidth(300)
        
        # 스플리터에 패널 추가
        watchlist_splitter.addWidget(left_panel)
        watchlist_splitter.addWidget(right_panel)
        
        # 스플리터 크기를 비율로 설정 (setStretchFactor)
        watchlist_splitter.setStretchFactor(0, 1) # 왼쪽 패널(group_list) 비율 1
        watchlist_splitter.setStretchFactor(1, 3) # 오른쪽 패널(watchlist_table) 비율 3
        logger.debug(f"스플리터 크기 비율 설정: 1:3")
        
        # 관심 그룹 프레임 레이아웃 설정
        watchlist_frame_layout = QVBoxLayout(watchlist_frame)
        watchlist_frame_layout.setContentsMargins(0, 0, 0, 0)
        watchlist_frame_layout.addWidget(watchlist_splitter)
        
        # 메인 레이아웃에 관심 그룹 프레임 추가
        main_layout.addWidget(watchlist_frame, 2)  # 관심 그룹 영역에 비율 2 할당
        
        # 마우스 호버 버튼 생성
        self.search_hover_button = HoverButton(self.result_table, "추가", True)
        self.search_hover_button.clicked.connect(self.on_add_to_watchlist)
        
        self.watchlist_hover_button = HoverButton(self.watchlist_table, "삭제", False)
        self.watchlist_hover_button.clicked.connect(self.on_remove_from_watchlist)
        
        # 관심 그룹 데이터 로드
        self.load_watchlist_groups()
        self.load_watchlist_data()
    
    def eventFilter(self, obj, event):
        """이벤트 필터 - 테이블 내부 마우스 이동 추적"""
        if event.type() == QEvent.Type.MouseMove:
            if obj == self.result_table.viewport():
                pos = event.pos()
                row = self.result_table.rowAt(pos.y())
                if row >= 0 and row != self.search_hover_row:
                    if self.search_hover_row >= 0:
                        self.search_hover_button.hide()
                    self.search_hover_row = row
                    # 검색 결과 테이블은 직접 표시 유지 (또는 타이머 적용 가능)
                    self.on_result_table_hover(row, 0)
                    
            elif obj == self.watchlist_table.viewport(): 
                pos = event.pos()
                row = self.watchlist_table.rowAt(pos.y())
                if row >= 0 and row != self.watchlist_hover_row:
                    if self.watchlist_hover_row >= 0:
                        self.watchlist_hover_button.hide()
                    self.watchlist_hover_row = row
                    # <<< 수정: 타이머로 지연 호출 >>>
                    # self.on_watchlist_table_hover(row, 0) # 직접 호출 제거
                    QTimer.singleShot(100, lambda r=row: self.show_watchlist_hover_button_if_needed(r)) # 100ms 지연
                    
        elif event.type() == QEvent.Type.Leave:
            if obj == self.result_table.viewport():
                if self.search_hover_row >= 0:
                    self.search_hover_button.hide()
                self.search_hover_row = -1
            elif obj == self.watchlist_table.viewport(): 
                if self.watchlist_hover_row >= 0:
                    self.watchlist_hover_button.hide()
                self.watchlist_hover_row = -1

        return super().eventFilter(obj, event)
    
    # <<< 추가: 타이머 콜백 함수 >>>
    def show_watchlist_hover_button_if_needed(self, row):
        """타이머 콜백: 현재 호버 행이 맞으면 버튼 표시"""
        if row == self.watchlist_hover_row:
             self.on_watchlist_table_hover(row, 0) # 실제 버튼 표시 함수 호출
    
    def on_result_table_hover(self, row, column):
        """검색 결과 테이블 마우스 호버 이벤트"""
        if row < 0 or row >= self.result_table.rowCount():
            return
            
        try:
            self.search_hover_row = row
            
            # 마지막 열의 아이템이 없을 수 있으므로 존재하는 열의 아이템을 찾아서 위치 계산
            last_item = None
            for col in range(self.result_table.columnCount()-1, -1, -1):
                if self.result_table.item(row, col):
                    last_item = self.result_table.item(row, col)
                    break
                    
            if not last_item and self.result_table.rowCount() > 0:
                # 아이템이 없지만 행은 존재하는 경우 행 전체 위치 사용
                rect = self.result_table.visualItemRect(self.result_table.item(row, 0) or self.result_table.cellWidget(row, 0))
            elif last_item:
                rect = self.result_table.visualItemRect(last_item)
            else:
                # 행 자체가 없는 경우 리턴
                return
            
            # 버튼 위치 계산 (테이블 우측에 배치)
            table_width = self.result_table.viewport().width()
            button_x = table_width - self.search_hover_button.width() - 20
            button_y = rect.top() + (rect.height() - self.search_hover_button.height()) // 2
            
            # 버튼 위치 설정 및 표시
            self.search_hover_button.setParent(self.result_table.viewport())  # 부모를 뷰포트로 설정
            self.search_hover_button.move(button_x, button_y)
            self.search_hover_button.raise_()  # 버튼을 최상위로 올림
            self.search_hover_button.show()
            
            # 로그로 버튼 위치 디버깅
            logger.debug(f"검색 결과 호버 버튼 위치: ({button_x}, {button_y})")
        except Exception as e:
            logger.error(f"검색 결과 호버 버튼 표시 오류: {e}", exc_info=True)
    
    def on_result_table_leave(self, event):
        """검색 결과 테이블 마우스 이탈 이벤트"""
        self.search_hover_row = -1
        self.search_hover_button.hide()
        super(StockTableWidget, self.result_table).leaveEvent(event)
    
    def on_watchlist_table_hover(self, row, column):
        """관심 그룹 테이블 마우스 호버 이벤트"""
        if row < 0 or row >= self.watchlist_table.rowCount():
            return
            
        try:
            self.watchlist_hover_row = row
            
            # 마지막 열의 아이템이 없을 수 있으므로 존재하는 열의 아이템을 찾아서 위치 계산
            last_item = None
            for col in range(self.watchlist_table.columnCount()-1, -1, -1):
                if self.watchlist_table.item(row, col):
                    last_item = self.watchlist_table.item(row, col)
                    break
                    
            if not last_item and self.watchlist_table.rowCount() > 0:
                rect = self.watchlist_table.visualItemRect(self.watchlist_table.item(row, 0) or self.watchlist_table.cellWidget(row, 0))
            elif last_item:
                rect = self.watchlist_table.visualItemRect(last_item)
            else:
                return
            
            table_width = self.watchlist_table.viewport().width()
            button_x = table_width - self.watchlist_hover_button.width() - 20
            button_y = rect.top() + (rect.height() - self.watchlist_hover_button.height()) // 2
            
            self.watchlist_hover_button.setParent(self.watchlist_table.viewport())
            self.watchlist_hover_button.move(button_x, button_y)
            self.watchlist_hover_button.raise_()
            self.watchlist_hover_button.show()
            
            logger.debug(f"관심 그룹 호버 버튼 위치: ({button_x}, {button_y})")
        except Exception as e:
            logger.error(f"관심 그룹 호버 버튼 표시 오류: {e}", exc_info=True)
    
    def on_watchlist_table_leave(self, event):
        """관심 그룹 테이블 마우스 이탈 이벤트"""
        self.watchlist_hover_row = -1
        self.watchlist_hover_button.hide()
        super(StockTableWidget, self.watchlist_table).leaveEvent(event)
    
    def on_add_to_watchlist(self):
        """검색 결과 종목을 관심 그룹에 추가"""
        if self.search_hover_row < 0:
            return
            
        try:
            # 첫번째 컬럼은 종목명, 두번째 컬럼은 종목코드로 수정
            name_item = self.result_table.item(self.search_hover_row, 0)  # 첫번째 컬럼 = 종목명
            code_item = self.result_table.item(self.search_hover_row, 1)  # 두번째 컬럼 = 종목코드
            
            if not code_item or not name_item:
                logger.warning("종목코드 또는 종목명을 찾을 수 없습니다.")
                QMessageBox.warning(
                    self,
                    "추가 실패",
                    "종목코드를 찾을 수 없습니다."
                )
                return
                
            stock_code = code_item.text()
            stock_name = name_item.text()
            
            # 디버그 로그 추가
            logger.debug(f"관심그룹에 종목 추가 시도: {stock_name} ({stock_code})")
                
            # 이미 그룹에 있는지 확인
            if self.watchlist_module.is_stock_exists(self.current_group_id, stock_code):
                QMessageBox.information(
                    self,
                    "알림",
                    f"이미 '{self.current_group_name}' 그룹에 추가된 종목입니다."
                )
                return
                
            # 그룹에 종목 추가 - 코드를 명확하게 전달
            result = self.watchlist_module.add_stock(self.current_group_id, stock_code)
            if result:
                QMessageBox.information(
                    self,
                    "추가 성공",
                    f"종목 '{stock_name}'이(가) '{self.current_group_name}' 그룹에 추가되었습니다."
                )
                # 관심 그룹 테이블 새로고침
                self.load_watchlist_data()
            else:
                QMessageBox.warning(
                    self,
                    "추가 실패",
                    f"종목을 '{self.current_group_name}' 그룹에 추가하지 못했습니다."
                )
                
        except Exception as e:
            logger.error(f"관심 그룹에 종목 추가 실패: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "오류",
                f"관심 그룹에 종목 추가 중 오류가 발생했습니다: {str(e)}"
            )
    
    def on_remove_from_watchlist(self):
        """관심 그룹에서 종목 삭제"""
        if self.watchlist_hover_row < 0:
            return
            
        try:
            # 종목 코드와 이름 가져오기
            code_item = self.watchlist_table.item(self.watchlist_hover_row, 1)  # 두 번째 열은 종목 코드
            name_item = self.watchlist_table.item(self.watchlist_hover_row, 0)  # 첫 번째 열은 종목명
            
            if not code_item:
                logger.warning("삭제할 종목코드를 찾을 수 없습니다.")
                return
                
            stock_code = code_item.text()
            stock_name = name_item.text() if name_item else "알 수 없는 종목"
            
            # 디버그 로그 추가
            logger.debug(f"삭제 시도: 그룹 {self.current_group_id}, 종목코드: '{stock_code}', 종목명: '{stock_name}'")
            
            # 종목코드가 종목명과 동일한 경우 로그 표시 (테이블 데이터 이상)
            if stock_code == stock_name:
                logger.warning(f"종목코드와 종목명이 동일합니다. 올바르지 않은 데이터 가능성 있음: {stock_code}")
            
            # 삭제 확인 메시지
            reply = QMessageBox.question(
                self,
                "삭제 확인",
                f"'{stock_name}' 종목을 '{self.current_group_name}' 그룹에서 삭제하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # 호버 버튼 숨기기
            self.watchlist_hover_button.hide()
            self.watchlist_hover_row = -1
            
            # 그룹에서 종목 삭제
            result = self.watchlist_module.remove_stock(self.current_group_id, stock_code)
            if result:
                # 성공 메시지 표시
                QMessageBox.information(
                    self,
                    "삭제 성공",
                    f"종목 '{stock_name}'이(가) '{self.current_group_name}' 그룹에서 삭제되었습니다."
                )
                
                # 관심 그룹 테이블 새로고침
                self.load_watchlist_data()
            else:
                QMessageBox.warning(
                    self,
                    "삭제 실패",
                    f"종목을 '{self.current_group_name}' 그룹에서 삭제하지 못했습니다."
                )
                
        except Exception as e:
            logger.error(f"관심 그룹에서 종목 삭제 실패: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "오류",
                f"관심 그룹에서 종목 삭제 중 오류가 발생했습니다: {str(e)}"
            )
    
    def on_group_selected(self, group_id, group_name):
        """관심 그룹 선택 시 호출되는 함수 (수정: 모듈에 알리고 데이터 로드 트리거)"""
        logger.debug(f"관심 그룹 선택: {group_id} ({group_name})")
        self.current_group_id = group_id
        self.current_group_name = group_name
        
        # WatchlistModule에 활성 그룹 변경 알림 (내부적으로 워커 중지/재시작)
        self.watchlist_module.set_active_group(group_id)
        
        # 레이블 업데이트
        self.watchlist_label.setText(f"관심 그룹: {group_name}")
        
        # 테이블 데이터 로드 요청 (비동기)
        self.load_watchlist_data()
    
    def on_search_result(self, stocks):
        """검색 결과 수신 시 호출되는 함수"""
        self.current_search_results = stocks  # 검색 결과 저장
        self._update_result_table(stocks)
    
    def _update_result_table(self, stocks):
        """검색 결과 테이블 업데이트"""
        if not stocks:
            self.result_table.clearContents()
            self.result_table.setRowCount(0)
            return
            
        # 검색 결과 표시 전 데이터 업데이트
        try:
            # 파라미터 불러와 정보 업데이트 (API 호출로 최신 데이터 조회)
            updated_stocks = []
            # --- 수정: 동기 API 호출 임시 주석 처리 (UI 멈춤 방지) ---
            ''' 
            for stock in stocks:
                stock_code = stock.get('stk_cd', '')
                if stock_code:
                    # API로 최신 정보 조회
                    stock_info = self.kiwoom_api.get_stock_price(stock_code)
                    if stock_info:
                        # 기존 정보와 병합
                        stock_info.update({
                            'stk_cd': stock_code,
                            'stk_nm': stock.get('stk_nm', '알 수 없음')
                        })
                        # 거래량과 거래대금 필드 확인 및 추가
                        stock_info['trd_qty'] = stock_info.get('trde_qty', stock_info.get('trd_qty', '0'))
                        stock_info['trde_prica'] = stock_info.get('trde_prica', '0')
                        updated_stocks.append(stock_info)
                    else:
                        # 기존 데이터에 필드 추가
                        stock['trd_qty'] = stock.get('trde_qty', stock.get('trd_qty', '0'))
                        stock['trde_prica'] = stock.get('trde_prica', '0')
                        updated_stocks.append(stock)
                else:
                    # 기존 데이터에 필드 추가
                    stock['trd_qty'] = stock.get('trde_qty', stock.get('trd_qty', '0'))
                    stock['trde_prica'] = stock.get('trde_prica', '0')
                    updated_stocks.append(stock)
                    
            '''
            # 업데이트된 데이터로 테이블 갱신
            self.result_table.update_stock_data(updated_stocks)
            
        except Exception as e:
            logger.error(f"검색 결과 업데이트 실패: {e}", exc_info=True)
            # 오류 발생 시 원본 데이터에 필드 추가 후 테이블 갱신
            for stock in stocks:
                stock['trd_qty'] = stock.get('trde_qty', stock.get('trd_qty', '0'))
                stock['trde_prica'] = stock.get('trde_prica', '0')
            self.result_table.update_stock_data(stocks)
    
    def load_watchlist_data(self):
        """관심 그룹 종목 목록 로드 (수정: 비동기 로드 및 커서 변경)"""
        try:
            # 로딩 표시
            self.is_loading = True
            # QApplication.setOverrideCursor(Qt.WaitCursor) # <<< 임시 주석 처리
            
            # 호버 버튼 초기화
            self.watchlist_hover_button.hide()
            self.watchlist_hover_row = -1
            
            # 테이블 초기화
            self.watchlist_table.clearContents()
            self.watchlist_table.setRowCount(0)
            logger.debug(f"관심 그룹 ({self.current_group_id}) 데이터 로드 요청 (워커 실행 트리거)")
            # WatchlistModule에 업데이트 요청 (비동기 실행됨)
            self.watchlist_module.start_watchlist_update() 
            
            # 데이터 로딩은 워커가 완료하고 시그널을 보내면 _on_watchlist_updated 슬롯에서 처리됨
            # 여기서 더 이상 동기적으로 API 호출하거나 테이블 업데이트 하지 않음

        except Exception as e:
            logger.error(f"관심 그룹 데이터 로드 시작 중 오류: {e}", exc_info=True)
            QMessageBox.critical(self, "오류", f"관심 그룹 데이터 로드 중 오류 발생: {str(e)}")
            self.is_loading = False
            # QApplication.restoreOverrideCursor() # <<< 임시 주석 처리
        # finally 블록에서 커서 복원 및 is_loading 해제는 _on_watchlist_updated 슬롯으로 이동
            
    @pyqtSlot(int, list)
    def _on_watchlist_updated(self, group_id: int, stocks: list):
        """WatchlistModule로부터 업데이트된 종목 정보 수신 슬롯 (커서 복원 추가)"""
        try:
            # 현재 보고 있는 그룹의 업데이트만 처리
            if group_id == self.current_group_id:
                logger.debug(f"수신된 관심 그룹 업데이트: 그룹 {group_id}, {len(stocks)}개 종목")
                self.watchlist_table.update_stock_data(stocks)
            else:
                logger.debug(f"현재 그룹({self.current_group_id})과 다른 그룹({group_id}) 업데이트 수신 무시")
        except Exception as e:
             logger.error(f"관심 그룹 테이블 업데이트 중 오류: {e}", exc_info=True)
        finally:
             # 로딩 완료 처리 및 커서 복원
             if self.is_loading:
                 self.is_loading = False
                 # QApplication.restoreOverrideCursor() # <<< 임시 주석 처리

    @pyqtSlot(list)
    def _on_watchlist_groups_updated(self, groups: list):
        """WatchlistModule로부터 업데이트된 그룹 목록 수신 슬롯"""
        logger.debug("수신된 관심 그룹 목록 업데이트")
        self.group_list.clear()
        for group in groups:
            item = QListWidgetItem(group["name"])
            item.setData(Qt.UserRole, group["id"]) # ID 저장
            self.group_list.addItem(item)
            if group["id"] == self.current_group_id:
                item.setSelected(True) # 현재 활성 그룹 선택 표시

    @pyqtSlot(str)
    def _on_error_occurred(self, error_message: str):
        """WatchlistModule로부터 오류 메시지 수신 슬롯 (커서 복원 추가)"""
        QMessageBox.warning(self, "오류 발생", error_message)
        # 오류 발생 시에도 커서 복원
        if self.is_loading:
            self.is_loading = False
            # QApplication.restoreOverrideCursor() # <<< 임시 주석 처리

    def load_watchlist_groups(self):
        """관심 그룹 목록 로드"""
        try:
            # 그룹 목록 가져오기
            groups = self.watchlist_module.get_watchlists()
            
            # 리스트 위젯 초기화
            self.group_list.clear()
            
            # 그룹 목록 추가
            for group in groups:
                item = QListWidgetItem(group["name"])
                item.setData(Qt.UserRole, group["id"])
                self.group_list.addItem(item)
                
            # 현재 선택된 그룹 표시
            for i in range(self.group_list.count()):
                item = self.group_list.item(i)
                if item.data(Qt.UserRole) == self.current_group_id:
                    self.group_list.setCurrentItem(item)
                    break
            
        except Exception as e:
            logger.error(f"관심 그룹 목록 로드 실패: {e}", exc_info=True)
    
    def on_group_item_clicked(self, item):
        """관심 그룹 클릭 이벤트"""
        logger.debug(f"그룹 클릭됨: {item.text()}")
        group_id = item.data(Qt.UserRole)
        group_name = item.text()
        self.on_group_selected(group_id, group_name)
    
    def on_add_group(self):
        """관심 그룹 추가"""
        name, ok = QInputDialog.getText(self, "관심 그룹 추가", "그룹 이름을 입력하세요:")
        if ok and name:
            result = self.watchlist_module.create_watchlist(name)
            if result:
                self.load_watchlist_groups()
            else:
                QMessageBox.warning(self, "추가 실패", f"'{name}' 그룹 추가에 실패했습니다.") 

    def on_clear_all_stocks(self):
        """관심 그룹에서 모든 종목 삭제"""
        try:
            # 관심그룹에 종목이 없는 경우
            if self.watchlist_table.rowCount() == 0:
                QMessageBox.information(
                    self,
                    "알림",
                    f"{self.current_group_name} 그룹에 삭제할 종목이 없습니다."
                )
                return
                
            # 삭제 확인 메시지
            reply = QMessageBox.question(
                self,
                "전체 삭제 확인",
                f"{self.current_group_name} 그룹에서 모든 종목을 삭제하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # 그룹에서 모든 종목 삭제
            success_count = 0
            for row in range(self.watchlist_table.rowCount()):
                code_item = self.watchlist_table.item(row, 1)  # 종목코드
                if code_item and code_item.text():
                    stock_code = code_item.text()
                    if self.watchlist_module.remove_stock(self.current_group_id, stock_code):
                        success_count += 1
            
            # 성공 여부에 따른 메시지 표시
            if success_count > 0:
                QMessageBox.information(
                    self,
                    "삭제 성공",
                    f"{self.current_group_name} 그룹에서 {success_count}개 종목이 삭제되었습니다."
                )
                
                # 관심 그룹 테이블 새로고침
                self.load_watchlist_data()
            else:
                QMessageBox.warning(
                    self,
                    "삭제 실패",
                    f"{self.current_group_name} 그룹에서 종목 삭제에 실패했습니다."
                )
                
        except Exception as e:
            logger.error(f"관심 그룹에서 모든 종목 삭제 실패: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "오류",
                f"{self.current_group_name} 그룹에서 모든 종목 삭제 중 오류가 발생했습니다: {str(e)}"
            )
    
    def on_group_item_changed(self, current, previous):
        """관심 그룹 변경 이벤트"""
        if current is None:
            return
        
        logger.debug(f"그룹 변경됨: {current.text()}")
        group_id = current.data(Qt.UserRole)
        group_name = current.text()
        self.on_group_selected(group_id, group_name)

    def show_result_context_menu(self, position):
        """검색 결과 테이블 컨텍스트 메뉴"""
        try:
            # 마우스 위치의 행 구하기
            row = self.result_table.rowAt(position.y())
            if row < 0:
                return
                
            # 종목 코드와 이름 가져오기
            code_item = self.result_table.item(row, 1)  # 종목코드는 두번째 열
            name_item = self.result_table.item(row, 0)  # 종목명은 첫번째 열
            
            if not code_item or not name_item:
                return
                
            stock_code = code_item.text()
            stock_name = name_item.text()
            
            # 컨텍스트 메뉴 생성
            context_menu = QMenu(self)
            context_menu.setStyleSheet(StyleSheets.CONTEXT_MENU)
            
            # 차트보기 액션 추가
            chart_action = QAction("관심그룹에 추가", self)
            chart_action.triggered.connect(lambda: self._add_item_to_watchlist(stock_code, stock_name))
            context_menu.addAction(chart_action)
            
            # 메뉴 표시
            context_menu.exec_(self.result_table.viewport().mapToGlobal(position))
            
        except Exception as e:
            logger.error(f"컨텍스트 메뉴 생성 오류: {e}", exc_info=True)
    
    def show_watchlist_context_menu(self, position):
        """관심 그룹 테이블 컨텍스트 메뉴"""
        try:
            # 마우스 위치의 행 구하기
            row = self.watchlist_table.rowAt(position.y())
            if row < 0:
                return
                
            # 종목 코드와 이름 가져오기
            code_item = self.watchlist_table.item(row, 1)  # 종목코드는 두번째 열
            name_item = self.watchlist_table.item(row, 0)  # 종목명은 첫번째 열
            
            if not code_item or not name_item:
                return
                
            stock_code = code_item.text()
            stock_name = name_item.text()
            
            # 컨텍스트 메뉴 생성
            context_menu = QMenu(self)
            context_menu.setStyleSheet(StyleSheets.CONTEXT_MENU)
            
            # 차트보기 액션 추가
            chart_action = QAction("관심그룹에 추가", self)
            chart_action.triggered.connect(lambda: self._add_item_to_watchlist(stock_code, stock_name))
            context_menu.addAction(chart_action)
            
            # 메뉴 표시
            context_menu.exec_(self.watchlist_table.viewport().mapToGlobal(position))
            
        except Exception as e:
            logger.error(f"컨텍스트 메뉴 생성 오류: {e}", exc_info=True)
    
    def show_chart(self, stock_code, stock_name):
        """종목 차트 보기"""
        try:
            # 여기에 차트 보기 관련 코드 구현
            logger.debug(f"차트 보기: {stock_name} ({stock_code})")
            QMessageBox.information(
                self,
                "차트 보기",
                f"{stock_name} ({stock_code}) 종목의 차트 기능은 아직 구현 중입니다."
            )
        except Exception as e:
            logger.error(f"차트 표시 오류: {e}", exc_info=True)
    
    def update_search_results(self):
        """검색 결과 실시간 업데이트"""
        if not self.current_search_results:
            return
            
        try:
            updated_results = []
            for stock in self.current_search_results:
                stock_code = stock.get('stk_cd', '')
                if not stock_code:
                    continue
                    
                # API로 최신 정보 가져오기
                updated_info = self.kiwoom_api.get_stock_price(stock_code)
                if updated_info:
                    # 기존 데이터에 최신 정보 병합
                    updated_stock = stock.copy()
                    updated_stock.update(updated_info)
                    updated_results.append(updated_stock)
                else:
                    # 정보를 가져오지 못하면 원래 데이터 사용
                    updated_results.append(stock)
                    
            # 테이블 업데이트
            if updated_results:
                self._update_result_table(updated_results)
                self.current_search_results = updated_results
                logger.debug(f"검색 결과 실시간 업데이트 완료: {len(updated_results)}개 종목")
                
        except Exception as e:
            logger.error(f"검색 결과 업데이트 중 오류: {e}", exc_info=True)

    def closeEvent(self, event):
        """창 종료 시 호출 - 리소스 정리"""
        try:
            logger.info("관심그룹 창 닫기 이벤트 수신")
            
            # 검색 결과 업데이트 타이머 중지
            if hasattr(self, 'search_result_timer') and self.search_result_timer.isActive():
                self.search_result_timer.stop()
                logger.debug("검색 결과 업데이트 타이머 중지 완료")
            
            # 관심그룹 워커 스레드 종료 처리
            logger.info("관심그룹 워커 스레드 종료 요청...")
            
            if self.watchlist_module:
                self.watchlist_module.cleanup()
                logger.info("관심그룹 워커 스레드 종료 완료.")
        except Exception as e:
            logger.error(f"창 종료 처리 중 오류: {e}")
        
        super().closeEvent(event)

    def _on_search_table_double_clicked(self, index):
        if not index.isValid(): return
        stock_info = self.result_table.get_stock_info_at_row(index.row())
        if stock_info:
             self._add_item_to_watchlist(stock_info['종목코드'], stock_info['종목명'])

    @pyqtSlot(str, str)
    def _on_stock_table_double_clicked(self, stock_code, stock_name):
        """관심목록 테이블 더블 클릭 시 차트 요청 시그널 발생"""
        logger.debug(f"관심목록 테이블 더블 클릭됨: {stock_code} ({stock_name}). 차트 요청 시그널 발생 시도.")
        self.chart_requested.emit(stock_code, stock_name)