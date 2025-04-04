"""
차트 표시를 위한 메인 창 위젯
"""

import sys
import logging
from typing import Dict, Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolBar, 
    QCheckBox, QPushButton, QMenu, QSizePolicy, QSpacerItem, QLabel, QComboBox, QSpinBox, QWidgetAction, QButtonGroup, QMessageBox
)
from PySide6.QtGui import QAction, QIcon, QActionGroup
from PySide6.QtCore import Qt, Slot as pyqtSlot, Signal as pyqtSignal, QSettings, QTimer, QSize
import pyqtgraph as pg

from core.api.kiwoom import KiwoomAPI
from core.modules.chart import ChartModule
from core.ui.components.chart_component import ChartComponent
from core.ui.stylesheets import StyleSheets
from core.ui.constants.colors import Colors
from core.ui.constants.chart_defs import INDICATOR_MAP

logger = logging.getLogger(__name__)

# 보조지표 키-이름 매핑 (chart_defs.py로 이동)
# INDICATOR_MAP = {
#     'MA': '이동평균선',
#     'BB': '볼린저밴드',
#     'RSI': 'RSI',
#     'MACD': 'MACD',
#     'Volume': '거래량',
#     'TradingValue': '거래대금'
# }

class ChartWindow(QWidget): # QMainWindow 대신 QWidget 사용 고려
    """개별 종목 차트를 표시하는 창"""
    
    chart_closed = pyqtSignal(str) # 창이 닫힐 때 종목 코드를 전달하는 시그널

    def __init__(self, kiwoom_api: KiwoomAPI, stock_code: str, stock_name: str, parent=None):
        super().__init__(parent)
        self.stock_code = stock_code
        self.stock_name = stock_name
        # self.settings_group = f"ChartWindow/{self.stock_code}" # settings 객체 생성 후 사용
        
        # QSettings 객체 초기화 추가
        self.settings = QSettings("GazuaTrading", "ChartWindow") 
        self.settings_group = f"ChartWindow/{self.stock_code}" # 그룹 키 정의
        
        # 모듈 및 컴포넌트 인스턴스 생성
        # KiwoomAPI는 MainWindow에서 관리하는 것을 사용하도록 수정 필요할 수 있음
        # 여기서는 일단 새로 생성하는 것으로 가정
        self.chart_module = ChartModule(kiwoom_api)
        # 수정: ChartComponent 생성 시 chart_module 전달
        self.chart_component = ChartComponent(self.chart_module)

        self._init_ui()
        self._connect_signals()
        # self._load_settings() # 삭제: restore_settings에서 통합 처리
        
        # 초기 데이터 로드 (예: 일봉)
        self.chart_component.current_stock_code = stock_code # 컴포넌트에도 정보 전달
        self.chart_component.current_stock_name = stock_name
        self.chart_module.load_chart_data(stock_code, 'D')
        
        # 창 크기 및 설정 복원
        self.restore_settings()

        logger.info(f"ChartWindow 초기화 완료: {stock_name} ({stock_code})")

    def _init_ui(self):
        """UI 초기화"""
        self.setWindowTitle(f"{self.stock_name} ({self.stock_code}) - 차트")
        self.setMinimumSize(800, 600) # 최소 크기 설정 (요구사항은 1024x768)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. 툴바 생성
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)

        # 2. 차트 컴포넌트 추가
        main_layout.addWidget(self.chart_component)

    def _create_toolbar(self) -> QToolBar:
        """기간 선택 및 보조지표 선택을 위한 툴바 생성"""
        toolbar = QToolBar("차트 도구")
        toolbar.setStyleSheet(StyleSheets.TOOLBAR)
        toolbar.setIconSize(QSize(16, 16))
        
        # --- 기간 선택 버튼 --- 
        periods = {'Y': '년', 'M': '월', 'W': '주', 'D': '일', '1': '분', '1T': '틱'}
        self.period_buttons: Dict[str, QPushButton] = {}
        period_button_group = QButtonGroup(self)
        period_button_group.setExclusive(True)
        
        for code, name in periods.items():
            button = QPushButton(name)
            button.setCheckable(True)
            # 기본 스타일 설정
            style_sheet = StyleSheets.TOOLBAR_BUTTON 
            button.setProperty('period_code', code)
            
            # 분/틱 버튼에 드롭다운 메뉴 연결 및 스타일 적용
            if code == '1' or code == '1T': 
                menu = self._create_period_detail_menu(code, button)
                button.setMenu(menu)
                style_sheet = StyleSheets.TOOLBAR_BUTTON_DROPDOWN
            else:
                 # 드롭다운 없는 버튼 클릭 시 바로 로드 요청
                 button.clicked.connect(self._handle_period_button_click)

            button.setStyleSheet(style_sheet) # 최종 스타일 적용
            self.period_buttons[code] = button
            period_button_group.addButton(button)
            toolbar.addWidget(button)

        # 기본 선택 (일봉)
        if 'D' in self.period_buttons:
             self.period_buttons['D'].setChecked(True)
             # 초기 스타일 업데이트 (선택됨)
             self._update_period_button_style('D')
             
        toolbar.addSeparator()

        # --- 보조지표 체크박스 --- 
        self.indicator_checkboxes: Dict[str, QCheckBox] = {}
        for code, name in INDICATOR_MAP.items():
            checkbox = QCheckBox(name)
            # 거래량/거래대금은 기본으로 체크 (ChartComponent에서 숨김 처리)
            checkbox.setChecked(code in ['Volume', 'TradingValue'])
            checkbox.toggled.connect(lambda checked, ic=code: self._on_indicator_toggled(ic, checked))
            toolbar.addWidget(checkbox)
            self.indicator_checkboxes[code] = checkbox
            
        # TODO: 툴바 우측 정렬 및 추가 기능 버튼 (설정, 저장 등)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)
        
        # --- 우측 정렬 버튼 (설정 등) ---
        # 설정 버튼 (아이콘 필요: resources/icons/settings.png)
        settings_action = QAction(QIcon("resources/icons/settings.png"), "차트 설정", self)
        settings_action.triggered.connect(self._open_chart_settings) # 슬롯 연결
        toolbar.addAction(settings_action)

        return toolbar
        
    def _create_period_detail_menu(self, base_period: str, parent_button: QPushButton) -> QMenu:
        """상세 주기 선택 메뉴 생성 (분/틱)"""
        menu = QMenu(parent_button) # 부모 버튼 전달
        menu.setStyleSheet(StyleSheets.MENU) # 메뉴 스타일 적용 (선택 사항)
        
        action_group = QActionGroup(self)
        action_group.setExclusive(True)
        
        if base_period == '1': # 분봉
            periods = ["1", "3", "5", "10", "15", "30", "60"]
            for p in periods:
                action = QAction(f"{p}분", self)
                action.setCheckable(True)
                # 수정: lambda 함수가 현재 p값을 캡처하도록 기본 인자 사용
                # triggered 시그널은 checked 상태(bool)를 전달하므로 lambda 인자에 포함
                action.triggered.connect(lambda checked=False, p_val=p, btn=parent_button: self._handle_detail_period_selected(btn, p_val, f"{p_val}분"))
                menu.addAction(action)
                action_group.addAction(action)
                # 현재 선택된 상세 주기에 체크 표시 (필요시)
                # if self.chart_module.current_period == p: action.setChecked(True)
        elif base_period == '1T': # 틱봉
             periods = ["1", "3", "5", "10"] # 예시 틱 주기
             for p in periods:
                 action = QAction(f"{p}틱", self)
                 action.setCheckable(True)
                 # 수정: lambda 함수가 현재 p값을 캡처하도록 기본 인자 사용
                 # triggered 시그널은 checked 상태(bool)를 전달하므로 lambda 인자에 포함
                 action.triggered.connect(lambda checked=False, p_val=p, btn=parent_button: self._handle_detail_period_selected(btn, f"{p_val}T", f"{p_val}틱"))
                 menu.addAction(action)
                 action_group.addAction(action)
                 # if self.chart_module.current_period == f"{p}T": action.setChecked(True)
                 
        return menu

    @pyqtSlot()
    def _handle_period_button_click(self):
        """기간 버튼 클릭 처리 (주로 드롭다운 없는 버튼)"""
        sender = self.sender()
        if not isinstance(sender, QPushButton): return
        
        selected_period = None
        for code, button in self.period_buttons.items():
            if button == sender:
                selected_period = code
                break
                
        if selected_period:
            # 분/틱 버튼 자체 클릭 시 기본값으로 로드 (선택적)
            if selected_period == '1': selected_period = '1' 
            elif selected_period == '1T': selected_period = '1T'
            # 다른 버튼이 눌리면 분/틱 버튼 텍스트 복원
            self._reset_detail_button_text('1', '분')
            self._reset_detail_button_text('1T', '틱')
            self._request_chart_load(selected_period)
            
    @pyqtSlot(QPushButton, str, str)
    def _handle_detail_period_selected(self, button: QPushButton, period: str, text: str):
        """상세 주기 메뉴 액션 선택 처리"""
        # --- 로깅 추가: 슬롯 실행 확인 ---
        logger.info(f"슬롯 _handle_detail_period_selected 호출됨: button={button.text()}, period={period}, text={text}")
        # --- 로깅 추가 끝 ---

        logger.info(f"상세 주기 선택: {text} ({period})")
        # 다른 버튼이 눌리면 분/틱 버튼 텍스트 복원 (다른 버튼 먼저 처리)
        self._reset_detail_button_text('1', '분', exclude_button=button)
        self._reset_detail_button_text('1T', '틱', exclude_button=button)
        
        button.setText(text) # 버튼 텍스트 변경 (예: "5분")
        # button.setChecked(True) # QButtonGroup이 Exclusive 모드이므로 불필요할 수 있음
        # self._request_chart_load 내부에서 스타일 업데이트 호출
        self._request_chart_load(period)
        # 스타일 업데이트를 여기서 명시적으로 호출할 수도 있음
        # self._update_period_button_style(period) 

    def _request_chart_load(self, period: str):
        """차트 데이터 로드 요청"""
        # 이미 로딩 중이거나 같은 주기를 요청하면 무시
        if self.chart_module.is_loading or (self.stock_code and period == self.chart_module.current_period):
            logger.debug(f"차트 로드 건너뛰기: 로딩 중({self.chart_module.is_loading}) 또는 동일 주기({period})")
            return
            
        if self.stock_code:
             logger.info(f"차트 로드 요청: {self.stock_code}, 주기={period}")
             self.chart_component.clear_chart() # 새 데이터 로드 전 클리어
             # 다른 버튼이 눌리면 분/틱 버튼 텍스트 복원 (주기가 변경될 때)
             current_base = '1' if self.chart_module.current_period.isdigit() else ('1T' if self.chart_module.current_period.endswith('T') else None)
             new_base = '1' if period.isdigit() else ('1T' if period.endswith('T') else None)
             if current_base and current_base != new_base:
                 self._reset_detail_button_text(current_base, '분' if current_base == '1' else '틱')
                 
             # 데이터 로드 시작
             self.chart_module.load_chart_data(self.stock_code, period)
             # 버튼 스타일 업데이트 (로드 완료 후에도 필요할 수 있음)
             self._update_period_button_style(period) 
         
    def _update_period_button_style(self, selected_period: str):
        """선택된 주기에 따라 버튼 스타일 업데이트"""
        base_period = '1' if selected_period.isdigit() else ('1T' if selected_period.endswith('T') else selected_period)
        for code, button in self.period_buttons.items():
            # 선택된 기본 주기 또는 상세 주기의 부모 버튼 활성화
            button.setChecked(code == base_period)
            # TODO: 선택/비선택 상태에 따라 다른 스타일 적용 (StyleSheets.BUTTON_SELECTED 등)
            # 현재는 setChecked 상태에 따라 스타일 자동 변경 기대 (스타일시트 정의 확인 필요)
            
    def _reset_detail_button_text(self, base_code: str, default_text: str, exclude_button: Optional[QPushButton] = None):
        """분/틱 버튼 텍스트를 기본값으로 되돌림 (다른 버튼 클릭 시)"""
        if base_code in self.period_buttons:
            btn = self.period_buttons[base_code]
            if btn != exclude_button and btn.text() != default_text:
                btn.setText(default_text)

    def _connect_signals(self):
        """시그널 연결"""
        # ChartModule -> ChartComponent
        self.chart_module.chart_updated.connect(self.chart_component.update_chart)
        self.chart_module.latest_data_updated.connect(self.chart_component.update_latest_data)
        self.chart_component.chart_loaded.connect(self._on_chart_loaded)

    @pyqtSlot(str, bool)
    def _on_indicator_toggled(self, indicator_code: str, checked: bool):
        """보조지표 체크박스 토글 시 슬롯"""
        logger.info(f"보조지표 토글: {indicator_code}, 상태: {checked}")
        self.chart_component.toggle_indicator(indicator_code, checked)

    @pyqtSlot(bool)
    def _on_chart_loaded(self, success: bool):
        """차트 데이터 로딩 완료/실패 시 슬롯"""
        if success:
            logger.info(f"{self.stock_code} 차트 데이터 로딩 완료.")
            # 필요시 로딩 인디케이터 숨김 등 처리
        else:
            logger.error(f"{self.stock_code} 차트 데이터 로딩 실패.")
            # 사용자에게 오류 메시지 표시 등
            # QMessageBox.critical(self, "오류", f"{self.stock_code} 차트 데이터 로딩에 실패했습니다.")

    def _load_settings(self):
        """창 설정(크기, 위치, 보조지표 상태) 로드"""
        settings = QSettings("GazuaTrading", "Trading")
        settings.beginGroup(self.settings_group)
        
        # 창 크기 및 위치
        size = settings.value("size", QSize(1024, 768)) # 요구사항 반영
        pos = settings.value("pos")
        self.resize(size)
        if pos: self.move(pos)
        
        # 보조지표 체크박스 상태
        for code, checkbox in self.indicator_checkboxes.items():
            is_checked = settings.value(f"indicator/{code}", False, type=bool)
            checkbox.setChecked(is_checked)
            # 초기 상태에 따라 토글 호출 (차트 데이터 로드 후에 하는 것이 안전할 수 있음)
            # self.chart_component.toggle_indicator(code, is_checked)
            
        settings.endGroup()
        logger.info(f"차트 창 설정 로드 완료: {self.stock_code}")

    def _save_settings(self):
        """창 설정 저장"""
        settings = QSettings("GazuaTrading", "Trading")
        settings.beginGroup(self.settings_group)
        
        settings.setValue("size", self.size())
        settings.setValue("pos", self.pos())
        
        for code, checkbox in self.indicator_checkboxes.items():
            settings.setValue(f"indicator/{code}", checkbox.isChecked())
            
        settings.endGroup()
        logger.info(f"차트 창 설정 저장 완료: {self.stock_code}")

    def closeEvent(self, event):
        """창 닫기 이벤트 처리"""
        logger.info(f"ChartWindow 닫기 시작: {self.stock_code}")
        # self._save_settings() # 이름 변경
        self.save_settings() # 수정된 메서드 호출
        self.chart_module.cleanup() # 모듈 정리
        self.chart_component.cleanup() # 컴포넌트 정리
        self.chart_closed.emit(self.stock_code) # 닫힘 시그널 발생
        super().closeEvent(event)

    def save_settings(self):
        """창 크기, 위치, 주기, 지표 상태 저장"""
        # 지오메트리 저장
        self.settings.setValue(f"chart/{self.stock_code}/geometry", self.saveGeometry())
        # 현재 주기 저장
        self.settings.setValue(f"chart/{self.stock_code}/period", self.chart_module.current_period)
        # 보조지표 상태 저장
        indicator_states = {}
        for code, checkbox in self.indicator_checkboxes.items():
            indicator_states[code] = checkbox.isChecked()
        self.settings.setValue(f"chart/{self.stock_code}/indicators", indicator_states)
        
        logger.info(f"차트 창 설정 저장 완료: {self.stock_code}")
        
    def restore_settings(self):
        """저장된 창 크기, 위치, 주기, 지표 상태 복원"""
        # 지오메트리 복원
        geometry = self.settings.value(f"chart/{self.stock_code}/geometry")
        if geometry:
             try: self.restoreGeometry(geometry)
             except Exception as e: logger.error(f"차트 창 지오메트리 복원 실패: {e}", exc_info=True)
        else:
             self.resize(1024, 768) # 기본 크기
             
        # 주기 복원
        saved_period = self.settings.value(f"chart/{self.stock_code}/period", 'D') # 기본값 'D'
        if saved_period in self.period_buttons:
             self.period_buttons[saved_period].setChecked(True)
             # 초기 로드 시 load_chart_data가 이미 호출되었으므로, 주기가 다를 때만 다시 로드
             # 또는 __init__에서 초기 로드를 제거하고 여기서 항상 로드?
             # 여기서는 __init__에서 'D'로 로드하고, 저장된 주기가 D가 아니면 변경 로드
             if saved_period != 'D':
                 self._request_chart_load(saved_period)
             else:
                  self._update_period_button_style(saved_period)
        else:
            logger.warning(f"저장된 주기 '{saved_period}' 버튼 없음. 기본값('D') 사용.")
            if 'D' in self.period_buttons: self.period_buttons['D'].setChecked(True)
            self._update_period_button_style('D')
            
        # 보조지표 상태 복원
        indicator_states = self.settings.value(f"chart/{self.stock_code}/indicators", {})
        if isinstance(indicator_states, dict):
            for code, checkbox in self.indicator_checkboxes.items():
                is_checked = indicator_states.get(code, code in ['Volume', 'TradingValue']) # 기본값: 거래량/대금만 체크
                # 현재 상태와 다를 경우에만 setChecked 호출 (불필요한 시그널 방지)
                if checkbox.isChecked() != is_checked:
                    checkbox.setChecked(is_checked)
        
        logger.info(f"차트 창 설정 복원 완료: {self.stock_code}") 

    @pyqtSlot()
    def _open_chart_settings(self):
        """차트 설정 버튼 클릭 시 (임시 메시지)"""
        QMessageBox.information(self, "알림", "차트 설정 기능은 아직 구현되지 않았습니다.") 