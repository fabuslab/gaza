# -*- coding: utf-8 -*-
"""
메인 윈도우 모듈
"""

import sys
import os
import logging
from PySide6.QtWidgets import (
    QMainWindow, QMdiArea, QMenuBar, QStatusBar, QWidgetAction,
    QToolBar, QMessageBox, QWidget, QLabel,
    QMdiSubWindow, QMenu, QHBoxLayout, QPushButton, QVBoxLayout,
    QTabWidget, QApplication
)
from PySide6.QtGui import QAction, QScreen
from PySide6.QtCore import (
    Qt, QSize, QPoint, QSettings, Slot as pyqtSlot, QObject, Signal as pyqtSignal, QTimer, QEvent
)
from PySide6.QtGui import QIcon, QCloseEvent, QColor, QPixmap, QFont
from typing import Optional, Dict
import traceback

# --- 필요한 임포트 ---
from core.ui.constants.colors import Colors
from core.ui.constants.fonts import Fonts
from core.ui.stylesheets import StyleSheets
from core.utils.time_manager import TimeManager
from core.ui.windows.strategy_window import StrategyWindow
from core.ui.windows.integrated_search_watchlist_window import IntegratedSearchWatchlistWindow
from core.ui.dialogs.api_key_dialog import APIKeyDialog
from core.api.kiwoom import KiwoomAPI
from core.api.openai import OpenAIAPI
from core.ui.windows.trading_window import TradingWindow
from core.ui.windows.journal_window import JournalWindow
from core.ui.windows.settings_window import SettingsWindow
# --- 차트 관련 임포트 다시 추가 ---
from core.ui.windows.chart_window import ChartWindow
from core.modules.chart import ChartModule # ChartWindow에서 사용하므로 필요
# from core.ui.components.chart_component import ChartComponent # MainWindow에서 직접 사용 안 함

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """메인 윈도우 클래스"""
    
    def __init__(self):
        super().__init__()
        print("DEBUG: MainWindow.__init__() 시작")
        sys.stdout.flush()
        self.settings = QSettings("GazuaTrading", "Trading")
        self.time_manager = TimeManager()
        self.windows = {}  # 일반 서브윈도우 관리
        self.chart_subwindows: Dict[str, QMdiSubWindow] = {} # 차트 서브윈도우 관리 복원
        
        # 항상 위 플래그 추가
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        # API 키 초기화
        logger.info("API 키 초기화 시작...")
        print("DEBUG: _initialize_api_keys() 호출 전")
        sys.stdout.flush()
        api_keys_initialized = self._initialize_api_keys()
        print(f"DEBUG: _initialize_api_keys() 호출 완료, 결과: {api_keys_initialized}")
        sys.stdout.flush()
        if not api_keys_initialized:
            logger.critical("API 키 초기화 실패로 프로그램을 종료합니다.")
            # 메시지 박스 표시 전에 print 추가
            print("ERROR: API 키 초기화 실패, 메시지 박스 표시 시도...")
            sys.stdout.flush()
            QMessageBox.critical(None, "초기화 오류", "API 키 초기화에 실패하여 프로그램을 종료합니다.\n로그 파일을 확인해주세요.")
            print("ERROR: 메시지 박스 표시 완료. sys.exit() 호출")
            sys.stdout.flush()
            sys.exit("API 키 초기화 실패")

        logger.info("API 키 초기화 성공.")
        print("DEBUG: API 키 초기화 성공")
        sys.stdout.flush()

        print("DEBUG: init_ui() 호출 전")
        sys.stdout.flush()
        self.init_ui()
        print("DEBUG: init_ui() 호출 완료")
        sys.stdout.flush()
        print("DEBUG: MainWindow.__init__() 완료")
        sys.stdout.flush()
        
    def _initialize_api_keys(self) -> bool:
        """API 키 초기화"""
        print("DEBUG: _initialize_api_keys() 시작")
        sys.stdout.flush()
        try:
            # QSettings에서 API 키 가져오기
            settings = QSettings("GazuaTrading", "Trading")
            kiwoom_key_encrypted = settings.value("api/kiwoom_key")
            kiwoom_secret_encrypted = settings.value("api/kiwoom_secret")
            openai_key_encrypted = settings.value("api/openai_key")
            print("DEBUG: QSettings에서 키 로드 완료")
            sys.stdout.flush()

            # API 키가 없으면 API 키 설정 대화상자 표시
            if not all([kiwoom_key_encrypted, kiwoom_secret_encrypted, openai_key_encrypted]):
                logger.warning("저장된 API 키 없음. APIKeyDialog 표시.")
                print("DEBUG: 저장된 API 키 없음. APIKeyDialog 표시 전")
                sys.stdout.flush()
                dialog = APIKeyDialog(self)
                dialog_result = dialog.exec() # exec_() 대신 exec() 사용
                print(f"DEBUG: APIKeyDialog 표시 완료, 결과: {dialog_result}")
                sys.stdout.flush()
                # PyQt6/PySide6에서는 Accepted가 정수 값일 수 있음
                if dialog_result != QDialog.Accepted: 
                    logger.error("API 키 설정 취소됨.")
                    print("DEBUG: API 키 설정 취소됨. _initialize_api_keys() False 반환")
                    sys.stdout.flush()
                    return False

                # 대화상자에서 저장 후 다시 QSettings에서 로드
                print("DEBUG: APIKeyDialog 저장 후 QSettings 다시 로드")
                sys.stdout.flush()
                kiwoom_key_encrypted = settings.value("api/kiwoom_key")
                kiwoom_secret_encrypted = settings.value("api/kiwoom_secret")
                openai_key_encrypted = settings.value("api/openai_key")

                if not all([kiwoom_key_encrypted, kiwoom_secret_encrypted, openai_key_encrypted]):
                    print("ERROR: APIKeyDialog 저장 후에도 키 없음")
                    sys.stdout.flush()
                    raise ValueError("API 키가 설정되지 않았습니다.")

            # API 키 복호화
            print("DEBUG: API 키 복호화 시도")
            sys.stdout.flush()
            from core.utils.crypto import decrypt_data
            kiwoom_key = decrypt_data(kiwoom_key_encrypted)
            kiwoom_secret = decrypt_data(kiwoom_secret_encrypted)
            openai_key = decrypt_data(openai_key_encrypted)
            print("DEBUG: API 키 복호화 완료")
            sys.stdout.flush()

            # API 인스턴스 생성
            print("DEBUG: KiwoomAPI 인스턴스 생성 시도")
            sys.stdout.flush()
            # is_real 파라미터 제거 또는 설정 파일 통해 관리
            self.kiwoom_api = KiwoomAPI(kiwoom_key, kiwoom_secret)
            print("DEBUG: KiwoomAPI 인스턴스 생성 완료")
            sys.stdout.flush()
            print("DEBUG: OpenAIAPI 인스턴스 생성 시도")
            sys.stdout.flush()
            self.openai_api = OpenAIAPI(openai_key)
            print("DEBUG: OpenAIAPI 인스턴스 생성 완료")
            sys.stdout.flush()

            logger.info("API 키 초기화 성공")
            print("DEBUG: _initialize_api_keys() 성공, True 반환")
            sys.stdout.flush()
            return True

        except Exception as e:
            logger.error(f"API 키 초기화 실패: {e}", exc_info=True)
            error_msg = f"API 키 초기화 실패: {e}\n{traceback.format_exc()}"
            print(f"CRITICAL ERROR in _initialize_api_keys(): {error_msg}")
            sys.stdout.flush()
            print("DEBUG: _initialize_api_keys() 실패, False 반환")
            sys.stdout.flush()
            return False
        
    def init_ui(self):
        """UI 초기화"""
        # 기본 설정
        self.setWindowTitle("가즈아! 트레이딩")
        self.setMinimumSize(1024, 768)
        
        # --- 수정 시작: 창 크기/위치 복원 및 로깅 추가 ---
        logger.debug("메인 윈도우 크기/위치 복원 시작...")
        # 저장된 위치 복원
        pos = self.settings.value("window/position")
        if isinstance(pos, QPoint): # 타입 확인 추가
            logger.debug(f"저장된 위치 복원: {pos}")
            self.move(pos)
        else:
            logger.debug("저장된 위치 없음, 중앙 배치 시도.")
            self.center_window() # 저장된 위치 없으면 중앙 배치
            
        # 저장된 크기 복원
        size = self.settings.value("window/size")
        if isinstance(size, QSize): # 타입 확인 추가
            logger.debug(f"저장된 크기 복원: {size}")
            self.resize(size)
        else:
            default_size = QSize(1280, 1024)
            logger.debug(f"저장된 크기 없음, 기본 크기로 설정: {default_size}")
            self.resize(default_size)
        # self.center_window() # 위치 복원 후 중앙 배치는 불필요
        # --- 수정 끝 ---
        
        # MDI 영역 설정
        self.mdi_area = QMdiArea()
        self.mdi_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mdi_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setCentralWidget(self.mdi_area)
        
        # 상단 메뉴 생성
        self.create_menu_bar()
        
        # 상태바 생성
        self.create_status_bar()
        
        # 스타일 적용
        self.setStyleSheet(StyleSheets.WIDGET)
        
    def create_menu_bar(self):
        """메뉴바 생성"""
        menu_widget = QWidget()
        menu_layout = QHBoxLayout(menu_widget)
        menu_layout.setContentsMargins(10, 5, 10, 5)
        menu_layout.setSpacing(5)
        
        # 메뉴 버튼 생성 (차트 버튼 다시 추가)
        buttons = [
            ("관심그룹", self.show_integrated_window),
            ("트레이딩", self.show_trading_window),
            ("차트", self._show_empty_chart_window), # 빈 차트 열기 슬롯 연결
            ("투자전략", self.show_strategy_window),
            ("매매일지", self.show_journal_window),
            ("설정", self.show_settings_window)
        ]
        
        for text, callback in buttons:
            btn = QPushButton(text)
            btn.setStyleSheet(StyleSheets.MENU_BUTTON)
            btn.clicked.connect(callback)
            menu_layout.addWidget(btn)
        
        # 우측 정렬 및 로그아웃 레이어 관련 코드 유지
        menu_layout.addStretch()
        more_btn = QPushButton("···")
        more_btn.setStyleSheet(StyleSheets.MENU_BUTTON)
        more_btn.clicked.connect(self.show_logout_layer)
        menu_layout.addWidget(more_btn)
        self.setMenuWidget(menu_widget)
        self.logout_layer = QWidget(self)
        self.logout_layer.setStyleSheet(StyleSheets.LOGOUT_LAYER)
        self.logout_layer.setFixedSize(120, 40)
        self.logout_layer.hide()
        logout_layout = QVBoxLayout(self.logout_layer)
        logout_layout.setContentsMargins(5, 5, 5, 5)
        logout_btn = QPushButton("로그아웃")
        logout_btn.setStyleSheet(StyleSheets.LOGOUT_BUTTON)
        logout_btn.clicked.connect(self.close)
        logout_layout.addWidget(logout_btn)

    def create_status_bar(self):
        """상태바 생성"""
        statusbar = QStatusBar()
        statusbar.setStyleSheet(StyleSheets.STATUSBAR)
        self.setStatusBar(statusbar)
        
        # 시간 표시
        self.time_label = QLabel()
        self.time_label.setStyleSheet(StyleSheets.LABEL)
        statusbar.addPermanentWidget(self.time_label)
        
        # 시간 업데이트 시작
        self.time_manager.time_updated.connect(self.update_time)
        self.time_manager.start()
        
    def update_time(self, time_str: str):
        """시간 업데이트"""
        self.time_label.setText(time_str)
        
    def show_integrated_window(self):
        """통합 검색 및 관심종목 창 표시 (차트 시그널 연결 복원)"""
        window_key = "integrated"
        try:
            existing_subwindow = None
            if window_key in self.windows:
                subwindow_ref = self.windows.get(window_key)
                # --- 수정: 객체 유효성 검사 강화 ---
                if subwindow_ref:
                    try:
                        if subwindow_ref.widget():
                            existing_subwindow = subwindow_ref
                        else:
                            logger.warning(f"서브 윈도우({window_key}) 참조는 있으나 위젯이 없음. 제거합니다.")
                            del self.windows[window_key]
                    except RuntimeError:
                        logger.warning(f"서브 윈도우({window_key}) 객체가 이미 삭제됨. 새로 생성합니다.")
                        del self.windows[window_key]
                # --- 수정 끝 ---
                if existing_subwindow is None and window_key in self.windows:
                    del self.windows[window_key]
                    logger.debug(f"서브 윈도우의 위젯이 없어 참조 제거: {window_key}")
            
            if existing_subwindow:
                logger.debug(f"기존 창 활성화: {window_key}")
                if existing_subwindow.isMinimized(): existing_subwindow.showNormal()
                self.mdi_area.setActiveSubWindow(existing_subwindow)
            else:
                logger.debug(f"새 창 생성: {window_key}")
                content_window = IntegratedSearchWatchlistWindow(self.kiwoom_api)
                
                # <<< 시그널 연결 다시 추가 >>>
                content_window.chart_requested.connect(self._on_stock_chart_requested)

                sub_window = self.mdi_area.addSubWindow(content_window)
                self.windows[window_key] = sub_window
                sub_window.setWindowTitle(content_window.windowTitle())
                # --- 수정 시작: 저장된 geometry 복원 주석 처리 ---
                # saved_geometry = self.settings.value(f"window/{window_key}/geometry")
                # if saved_geometry:
                #     logger.debug(f"저장된 geometry 복원: {window_key}, {saved_geometry}")
                #     sub_window.setGeometry(saved_geometry)
                # else:
                #     logger.debug(f"저장된 geometry 없음, 기본 표시: {window_key}")
                
                # <<< 다시 추가: sub_window 표시 >>>
                sub_window.show()
                
                logger.debug(f"새 창 {window_key} 추가 및 표시 완료.")

        except Exception as e:
            logger.error(f"통합 창 표시 실패: {e}", exc_info=True)
            QMessageBox.critical(self, "오류", f"통합 창 표시 실패: {str(e)}")
            
    def show_strategy_window(self):
        """전략 창 표시 (수정: 활성화 로직 및 유효성 검사 강화)"""
        window_key = "strategy"
        try:
            existing_subwindow = None
            if window_key in self.windows:
                subwindow_ref = self.windows.get(window_key)
                # --- 수정: 객체 유효성 검사 강화 ---
                if subwindow_ref:
                    try:
                        if subwindow_ref.widget():
                            existing_subwindow = subwindow_ref
                        else:
                            logger.warning(f"서브 윈도우({window_key}) 참조는 있으나 위젯이 없음. 제거합니다.")
                            del self.windows[window_key]
                    except RuntimeError:
                        logger.warning(f"서브 윈도우({window_key}) 객체가 이미 삭제됨. 새로 생성합니다.")
                        del self.windows[window_key]
                # --- 수정 끝 ---
                if existing_subwindow is None and window_key in self.windows:
                    del self.windows[window_key]
                    logger.debug(f"서브 윈도우의 위젯이 없어 참조 제거: {window_key}")
            
            if existing_subwindow:
                logger.debug(f"기존 창 활성화: {window_key}")
                if existing_subwindow.isMinimized(): existing_subwindow.showNormal()
                self.mdi_area.setActiveSubWindow(existing_subwindow)
            else:
                logger.debug(f"새 창 생성: {window_key}")
                content_window = StrategyWindow(self.openai_api)
                sub_window = self.mdi_area.addSubWindow(content_window)
                self.windows[window_key] = sub_window
                sub_window.setWindowTitle(content_window.windowTitle())
                # --- 수정 시작: 저장된 geometry 복원 ---
                saved_geometry = self.settings.value(f"window/{window_key}/geometry")
                if saved_geometry:
                    logger.debug(f"저장된 geometry 복원: {window_key}, {saved_geometry}")
                    sub_window.setGeometry(saved_geometry)
                else:
                    logger.debug(f"저장된 geometry 없음, 기본 표시: {window_key}")
                    sub_window.show() # 저장된 값 없으면 기본 show
                # --- 수정 끝 ---
                logger.debug(f"새 창 {window_key} 추가 및 표시 완료.")
            
        except Exception as e:
            logger.error(f"전략 창 표시 실패: {e}", exc_info=True)
            QMessageBox.critical(self, "오류", f"전략 창 표시 실패: {str(e)}")
            
    def show_logout_layer(self):
        """로그아웃 레이어 표시"""
        sender = self.sender()
        if sender:
            # 버튼 위치 기준으로 레이어 위치 설정
            pos = sender.mapToGlobal(sender.rect().bottomLeft())
            self.logout_layer.move(self.mapFromGlobal(pos))
            self.logout_layer.show()
        
        # 레이어 외부 클릭 시 숨김 처리
        def hide_layer(watched, event):
            if event.type() == QEvent.MouseButtonPress and watched == self:
                if self.logout_layer.isVisible() and not self.logout_layer.geometry().contains(event.pos()):
                    self.logout_layer.hide()
                    self.removeEventFilter(self)
                    return True
            return False

        self._temp_event_filter_func = hide_layer
        self.installEventFilter(self)
        # self.eventFilter = self._temp_event_filter_func # PySide6에서는 직접 할당보다 installEventFilter 사용 권장

    def eventFilter(self, watched, event):
        """메인 윈도우의 이벤트 필터 (로그아웃 레이어 숨김 처리)"""
        if hasattr(self, '_temp_event_filter_func') and self._temp_event_filter_func(watched, event):
             return True # 이벤트 처리 완료
        return super().eventFilter(watched, event)

    def show_trading_window(self):
        """트레이딩 창 표시 (수정: 활성화 로직 및 유효성 검사 강화)"""
        window_key = "trading"
        try:
            existing_subwindow = None
            if window_key in self.windows:
                subwindow_ref = self.windows.get(window_key)
                # --- 수정: 객체 유효성 검사 강화 ---
                if subwindow_ref:
                    try:
                        if subwindow_ref.widget():
                            existing_subwindow = subwindow_ref
                        else:
                            logger.warning(f"서브 윈도우({window_key}) 참조는 있으나 위젯이 없음. 제거합니다.")
                            del self.windows[window_key]
                    except RuntimeError:
                        logger.warning(f"서브 윈도우({window_key}) 객체가 이미 삭제됨. 새로 생성합니다.")
                        del self.windows[window_key]
                # --- 수정 끝 ---
                if existing_subwindow is None and window_key in self.windows:
                    del self.windows[window_key]
                    logger.debug(f"서브 윈도우의 위젯이 없어 참조 제거: {window_key}")
            
            if existing_subwindow:
                logger.debug(f"기존 창 활성화: {window_key}")
                if existing_subwindow.isMinimized(): existing_subwindow.showNormal()
                self.mdi_area.setActiveSubWindow(existing_subwindow)
            else:
                logger.debug(f"새 창 생성: {window_key}")
                content_window = TradingWindow(self.kiwoom_api)
                sub_window = self.mdi_area.addSubWindow(content_window)
                self.windows[window_key] = sub_window
                sub_window.setWindowTitle(content_window.windowTitle())
                sub_window.show()
                logger.debug(f"새 창 {window_key} 추가 및 표시 완료.")
            
        except Exception as e:
            logger.error(f"트레이딩 창 표시 실패: {e}", exc_info=True)
            QMessageBox.critical(self, "오류", f"트레이딩 창 표시 실패: {str(e)}")

    def show_journal_window(self):
        """매매일지 창 표시 (수정: 활성화 로직 및 유효성 검사 강화)"""
        window_key = "journal"
        try:
            existing_subwindow = None
            if window_key in self.windows:
                subwindow_ref = self.windows[window_key]
                if subwindow_ref and subwindow_ref.widget(): 
                    existing_subwindow = subwindow_ref
                else:
                    del self.windows[window_key]
                    logger.debug(f"서브 윈도우의 위젯이 없어 참조 제거: {window_key}")
            
            if existing_subwindow:
                logger.debug(f"기존 창 활성화: {window_key}")
                if existing_subwindow.isMinimized(): existing_subwindow.showNormal()
                self.mdi_area.setActiveSubWindow(existing_subwindow)
            else:
                logger.debug(f"새 창 생성: {window_key}")
                content_window = JournalWindow(self.kiwoom_api)
                sub_window = self.mdi_area.addSubWindow(content_window)
                self.windows[window_key] = sub_window
                sub_window.setWindowTitle(content_window.windowTitle())
                # --- 수정 시작: 저장된 geometry 복원 ---
                saved_geometry = self.settings.value(f"window/{window_key}/geometry")
                if saved_geometry:
                    logger.debug(f"저장된 geometry 복원: {window_key}, {saved_geometry}")
                    sub_window.setGeometry(saved_geometry)
                else:
                    logger.debug(f"저장된 geometry 없음, 기본 표시: {window_key}")
                    sub_window.show() # 저장된 값 없으면 기본 show
                # --- 수정 끝 ---
                logger.debug(f"새 창 {window_key} 추가 및 표시 완료.")
            
        except Exception as e:
            logger.error(f"매매일지 창 표시 실패: {e}", exc_info=True)
            QMessageBox.critical(self, "오류", f"매매일지 창 표시 실패: {str(e)}")

    def show_settings_window(self):
        """설정 창 표시 (수정: 활성화 로직 및 유효성 검사 강화)"""
        window_key = "settings"
        try:
            existing_subwindow = None
            if window_key in self.windows:
                subwindow_ref = self.windows[window_key]
                if subwindow_ref and subwindow_ref.widget(): 
                    existing_subwindow = subwindow_ref
                else:
                    del self.windows[window_key]
                    logger.debug(f"서브 윈도우의 위젯이 없어 참조 제거: {window_key}")
            
            if existing_subwindow:
                logger.debug(f"기존 창 활성화: {window_key}")
                if existing_subwindow.isMinimized(): existing_subwindow.showNormal()
                self.mdi_area.setActiveSubWindow(existing_subwindow)
            else:
                logger.debug(f"새 창 생성: {window_key}")
                content_window = SettingsWindow()
                sub_window = self.mdi_area.addSubWindow(content_window)
                self.windows[window_key] = sub_window
                sub_window.setWindowTitle(content_window.windowTitle())
                # --- 수정 시작: 저장된 geometry 복원 ---
                saved_geometry = self.settings.value(f"window/{window_key}/geometry")
                if saved_geometry:
                    logger.debug(f"저장된 geometry 복원: {window_key}, {saved_geometry}")
                    sub_window.setGeometry(saved_geometry)
                else:
                    logger.debug(f"저장된 geometry 없음, 기본 표시: {window_key}")
                    sub_window.show() # 저장된 값 없으면 기본 show
                # --- 수정 끝 ---
                logger.debug(f"새 창 {window_key} 추가 및 표시 완료.")
            
        except Exception as e:
            logger.error(f"설정 창 표시 실패: {e}", exc_info=True)
            QMessageBox.critical(self, "오류", f"설정 창 표시 실패: {str(e)}")

    def center_window(self):
        """윈도우를 화면 중앙에 배치"""
        try:
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                center_point = screen_geometry.center()
                window_geometry = self.frameGeometry()
                window_geometry.moveCenter(center_point)
                self.move(window_geometry.topLeft())
        except Exception as e:
            logger.error(f"윈도우 중앙 배치 중 오류: {e}", exc_info=True)
            # 오류 발생 시 기본 위치 사용

    def closeEvent(self, event: QCloseEvent):
        """메인 윈도우 닫기 이벤트 처리 (서브 윈도우 상태 저장 포함)"""
        logger.info("앱 종료 요청")
        # --- 수정 시작: 메인 창 상태 저장 및 로깅 ---
        current_size = self.size()
        current_pos = self.pos()
        logger.debug(f"메인 윈도우 상태 저장: size={current_size}, position={current_pos}")
        self.settings.setValue("window/size", self.size())
        self.settings.setValue("window/position", self.pos())
        # --- 수정 끝 ---
        self.time_manager.stop()
        
        # --- 수정 시작: 서브 윈도우 상태 저장 및 닫기 --- 
        logger.debug("서브 윈도우 상태 저장 및 닫기 시작...")
        # 차트 윈도우
        chart_keys = list(self.chart_subwindows.keys())
        logger.debug(f"정리 대상 차트 창 키: {chart_keys}")
        for key in chart_keys:
            if key in self.chart_subwindows: # 키 존재 여부 다시 확인
                subwindow_ref = self.chart_subwindows.get(key) # get으로 안전하게 가져오기
                # --- 수정: widget() 호출 전 유효성 검사 강화 ---
                widget_instance = None
                try:
                    if subwindow_ref:
                        widget_instance = subwindow_ref.widget()
                except RuntimeError: # 이미 삭제된 경우
                    logger.warning(f"차트 서브윈도우({key}) 위젯 접근 시 RuntimeError 발생 (이미 삭제됨).")
                    widget_instance = None # 접근 불가 처리
                
                if widget_instance: # 위젯이 유효한 경우에만 처리
                    try:
                        # 닫기 전에 상태 저장
                        self.settings.setValue(f"window/{key}/geometry", subwindow_ref.geometry())
                        logger.debug(f"차트 창 상태 저장: {key}")
                        # 닫기
                        logger.debug(f"차트 서브윈도우 닫기 시도: {key}")
                        subwindow_ref.close()
                    except RuntimeError as e:
                         if "Internal C++ object" in str(e) and "already deleted" in str(e):
                             logger.warning(f"차트 서브 윈도우({key})는 닫기/저장 시도 전에 이미 삭제되었습니다.")
                         else:
                            logger.error(f"차트 서브윈도우({key}) 상태 저장/닫기 중 예외 발생: {e}", exc_info=True)
                    except Exception as e:
                         logger.error(f"차트 서브윈도우({key}) 상태 저장/닫기 중 예외 발생: {e}", exc_info=True)
                else:
                    # 참조는 있으나 위젯이 없는 경우 또는 이미 삭제된 경우
                    logger.warning(f"유효하지 않은 차트 창 참조 발견: {key}. 목록에서 제거합니다.")
                    if key in self.chart_subwindows: # 제거 전 다시 확인
                        del self.chart_subwindows[key]
            # --- 수정 끝 ---
        
        # 일반 서브 윈도우 (유사하게 수정)
        window_keys = list(self.windows.keys())
        logger.debug(f"정리 대상 일반 창 키: {window_keys}")
        for key in window_keys:
             if key in self.windows: # 키 존재 여부 다시 확인
                 subwindow_ref = self.windows.get(key)
                 # --- 수정: widget() 호출 전 유효성 검사 강화 ---
                 widget_instance = None
                 try:
                    if subwindow_ref:
                        widget_instance = subwindow_ref.widget()
                 except RuntimeError: # 이미 삭제된 경우
                    logger.warning(f"일반 서브 윈도우({key}) 위젯 접근 시 RuntimeError 발생 (이미 삭제됨).")
                    widget_instance = None
                 
                 if widget_instance:
                     try:
                         # 닫기 전에 상태 저장
                         self.settings.setValue(f"window/{key}/geometry", subwindow_ref.geometry())
                         logger.debug(f"일반 창 상태 저장: {key}")
                         # 닫기
                         logger.debug(f"일반 서브 윈도우 닫기 시도: {key}")
                         subwindow_ref.close()
                     except RuntimeError as e:
                         if "Internal C++ object" in str(e) and "already deleted" in str(e):
                             logger.warning(f"일반 서브 윈도우({key})는 닫기/저장 시도 전에 이미 삭제되었습니다.")
                         else:
                             logger.error(f"일반 서브윈도우({key}) 상태 저장/닫기 중 예외 발생: {e}", exc_info=True)
                     except Exception as e:
                          logger.error(f"일반 서브윈도우({key}) 상태 저장/닫기 중 예외 발생: {e}", exc_info=True)
                 else:
                     logger.warning(f"닫을 수 없는 서브 윈도우 참조 발견: {key}. 목록에서 제거합니다.")
                     if key in self.windows: del self.windows[key] 
             # --- 수정 끝 ---

        # 모든 창 닫기 시도 후, 혹시 콜백(_handle_subwindow_destroyed) 지연 등으로
        # 아직 딕셔너리에 남아있는 키가 있다면 안전하게 제거
        remaining_chart_keys = list(self.chart_subwindows.keys())
        if remaining_chart_keys:
            logger.warning(f"닫기 후에도 남아있는 차트 창 참조 발견: {remaining_chart_keys}. 강제 제거 시도.")
            for key in remaining_chart_keys:
                if key in self.chart_subwindows: del self.chart_subwindows[key]
        remaining_window_keys = list(self.windows.keys())
        if remaining_window_keys:
             logger.warning(f"닫기 후에도 남아있는 일반 창 참조 발견: {remaining_window_keys}. 강제 제거 시도.")
             for key in remaining_window_keys:
                 if key in self.windows: del self.windows[key]
                  
        logger.info("모든 서브 윈도우 닫기 완료 (시도). 메인 윈도우 닫기 수락.")
        event.accept()

    @pyqtSlot()
    def _show_empty_chart_window(self):
        """빈 차트 창을 엽니다 (메뉴 클릭 시)."""
        # TODO: 빈 차트 창을 어떻게 처리할지 결정 필요 (예: 종목 검색 유도)
        logger.info("빈 차트 창 열기 요청 (구현 필요)")
        # 임시로 메시지 표시
        QMessageBox.information(self, "알림", "종목을 선택하여 차트를 열어주세요.")
        # self._show_chart_window(None, "차트") # 또는 None으로 차트 열기 시도
        
    @pyqtSlot(str, str)
    def _on_stock_chart_requested(self, stock_code, stock_name):
        """차트 요청 시그널을 처리하는 슬롯"""
        logger.debug(f"MainWindow: 차트 요청 수신 - 코드: {stock_code}, 이름: {stock_name}") # 로그 추가
        self._show_chart_window(stock_code, stock_name)

    def _show_chart_window(self, stock_code: Optional[str], stock_name: Optional[str]):
        """특정 종목의 차트 창을 표시하거나 활성화합니다."""
        logger.debug(f"_show_chart_window 호출: code={stock_code}, name={stock_name}") # 진입 로그
        if not stock_code: 
            QMessageBox.warning(self, "오류", "차트를 표시할 종목 코드가 없습니다.")
            return

        logger.info(f"차트 창 표시/활성화 진행: {stock_code} ({stock_name})" )
        window_key = f"chart_{stock_code}" 

        logger.debug(f"현재 chart_subwindows 키: {list(self.chart_subwindows.keys())}")
        existing_subwindow = None
        if window_key in self.chart_subwindows:
            subwindow_ref = self.chart_subwindows[window_key]
            if subwindow_ref and subwindow_ref.widget():
                existing_subwindow = subwindow_ref
            else:
                 del self.chart_subwindows[window_key]
                 logger.debug(f"유효하지 않은 차트 창 참조 제거: {window_key}")

        if existing_subwindow:
            logger.debug(f"기존 차트 창 활성화 시도: {window_key}") # 활성화 시도 로그
            if existing_subwindow.isMinimized(): existing_subwindow.showNormal()
            self.mdi_area.setActiveSubWindow(existing_subwindow)
            # raise_(), activateWindow()는 일단 제거된 상태 유지
            logger.debug(f"기존 차트 창 활성화 완료: {window_key}") # 활성화 완료 로그
        else:
            logger.debug(f"새 차트 창 생성 함수 호출: {window_key}") # 생성 함수 호출 로그
            self._create_and_show_new_chart_window(stock_code, stock_name or stock_code)

    def _create_and_show_new_chart_window(self, stock_code: str, stock_name: str):
        """새로운 차트 창을 생성하고 표시합니다."""
        logger.debug(f"_create_and_show_new_chart_window 진입: {stock_code}") # 함수 진입 로그
        try:
            # KiwoomAPI 인스턴스가 유효한지 확인
            if not hasattr(self, 'kiwoom_api') or not self.kiwoom_api:
                 logger.error("KiwoomAPI가 초기화되지 않아 차트 창을 생성할 수 없습니다.")
                 QMessageBox.critical(self, "오류", "API 연결 오류로 차트 창을 열 수 없습니다.")
                 return None 
                 
            # ChartWindow 생성 전 로그
            logger.debug(f"ChartWindow({stock_code}) 생성 시도...")
            chart_window = ChartWindow(self.kiwoom_api, stock_code, stock_name)
            logger.debug(f"ChartWindow({stock_code}) 생성 완료: {chart_window}")

            # QMdiArea에 서브 윈도우로 추가 전 로그
            logger.debug(f"addSubWindow({stock_code}) 호출 시도...")
            sub_window = self.mdi_area.addSubWindow(chart_window)
            logger.debug(f"addSubWindow({stock_code}) 호출 완료: {sub_window}")
            
            sub_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True) 
            
            window_key = f"chart_{stock_code}"
            self.chart_subwindows[window_key] = sub_window # 추적
            logger.debug(f"차트 창 추적 목록에 추가: {window_key}") # 추적 추가 로그
            
            # chart_closed 시그널 연결 전 로그
            logger.debug(f"chart_closed 시그널 연결 시도: {window_key}")
            chart_window.chart_closed.connect(lambda code, key=window_key: self._handle_subwindow_destroyed(key, code))
            logger.debug(f"chart_closed 시그널 연결 완료: {window_key}")
            
            sub_window.setWindowTitle(chart_window.windowTitle()) # 제목 설정
            
            # sub_window.show() 호출 전 로그
            logger.debug(f"sub_window.show() 호출 시도: {window_key}")
            sub_window.show()
            logger.debug(f"sub_window.show() 호출 완료: {window_key}")
            
            logger.info(f"새 차트 창 생성 및 표시 완료: {stock_name} ({stock_code})")
            
            return sub_window

        except Exception as e:
            logger.error(f"새 차트 창 생성 실패 ({stock_code}): {e}", exc_info=True)
            QMessageBox.critical(self, "오류", f"차트 창 생성 실패 ({stock_code}): {str(e)}")
            return None

    def _handle_subwindow_destroyed(self, window_key: str, stock_code: Optional[str] = None):
        """서브 윈도우가 닫힐 때 (ChartWindow의 chart_closed 시그널 수신) 참조를 제거합니다."""
        logger.debug(f"_handle_subwindow_destroyed 호출됨: window_key={window_key}, stock_code={stock_code}")
        if window_key in self.chart_subwindows:
            del self.chart_subwindows[window_key]
            logger.info(f"차트 서브윈도우 참조 제거 완료: {window_key}")
        elif window_key in self.windows:
            del self.windows[window_key]
            logger.info(f"일반 서브윈도우 참조 제거 완료: {window_key}")
        else:
            logger.warning(f"제거할 서브윈도우 키를 찾지 못함: {window_key}")