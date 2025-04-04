"""
주식 검색 컴포넌트 모듈
"""

import logging
from typing import List, Dict, Any, Optional
# from PyQt5.QtWidgets import (
#     QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton,
#     QCompleter, QTableWidget, QTableWidgetItem, QHeaderView
# )
# from PyQt5.QtCore import Qt, pyqtSignal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCompleter, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal as pyqtSignal

from core.api.kiwoom import KiwoomAPI
from core.ui.stylesheets import StyleSheets

logger = logging.getLogger(__name__)

class StockSearchComponent(QWidget):
    """주식 검색 컴포넌트"""
    
    # 신호 정의
    stock_selected = pyqtSignal(str, str)  # 종목 코드, 종목 이름
    search_completed = pyqtSignal(list)  # 검색 결과 리스트

    def __init__(self, kiwoom_api: KiwoomAPI, parent=None):
        """초기화"""
        super().__init__(parent)
        self.kiwoom_api = kiwoom_api
        self.search_results = []  # 검색 결과 저장
        
        # UI 초기화
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 검색어 레이블
        search_label = QLabel("종목검색:")
        search_label.setStyleSheet(StyleSheets.LABEL)
        layout.addWidget(search_label)
        
        # 검색 입력 필드
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("종목 코드 또는 이름 입력")
        self.search_input.setStyleSheet(StyleSheets.LINE_EDIT)
        self.search_input.returnPressed.connect(self.search_stock)
        layout.addWidget(self.search_input)
        
        # 검색 버튼
        search_button = QPushButton("검색")
        search_button.setStyleSheet(StyleSheets.BUTTON)
        search_button.clicked.connect(self.search_stock)
        layout.addWidget(search_button)
        
        # 검색 결과 테이블 초기화
        self.result_table = QTableWidget(0, 3)  # 행, 열 (코드, 이름, 현재가)
        self.result_table.setHorizontalHeaderLabels(["종목코드", "종목명", "현재가"])
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 편집 불가
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)  # 행 단위 선택
        self.result_table.setSelectionMode(QTableWidget.SingleSelection)  # 단일 선택
        self.result_table.verticalHeader().setVisible(False)  # 수직 헤더 숨김
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # 이름 열 늘림
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 코드 열 내용에 맞춤
        self.result_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 현재가 열 내용에 맞춤
        self.result_table.setStyleSheet(StyleSheets.TABLE)
        self.result_table.setVisible(False)  # 초기에는 숨김
        self.result_table.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        # 레이아웃 비율 조정
        layout.setStretch(0, 0)  # 레이블
        layout.setStretch(1, 1)  # 검색 필드
        layout.setStretch(2, 0)  # 검색 버튼
        
    def search_stock(self):
        """종목 검색 실행"""
        query = self.search_input.text().strip()
        if not query:
            return
            
        try:
            logger.info(f"종목 검색 시작: {query}")
            
            # API를 통해 종목 검색 (종목 코드 또는 이름)
            is_code = query.isdigit() and len(query) == 6
            
            if is_code:
                # 종목 코드로 검색
                stock_info = self.kiwoom_api.get_stock_price(query)
                if stock_info:
                    # 필드명 맞추기
                    stock_info['trd_qty'] = stock_info.get('trde_qty', '0')
                    stock_info['trde_prica'] = stock_info.get('trde_prica', '0')
                    self.search_results = [stock_info]
                else:
                    self.search_results = []
            else:
                # 종목 이름으로 검색
                search_results = self.kiwoom_api.search_stocks_by_name(query)
                # 각 결과에 필드명 맞추기
                for result in search_results:
                    result['trd_qty'] = result.get('trde_qty', '0')
                    result['trde_prica'] = result.get('trde_prica', '0')
                self.search_results = search_results
            
            logger.info(f"검색 결과: {len(self.search_results)}개 종목")
            
            # 검색 완료 신호 발생 - 검색 결과를 메인 윈도우로 전달
            self.search_completed.emit(self.search_results)
            
            # 검색 결과 테이블 숨김 (메인 테이블에 결과 표시)
            self.result_table.setVisible(False)
            
        except Exception as e:
            logger.error(f"종목 검색 중 오류: {e}", exc_info=True)
            self.search_results = []
            self.search_completed.emit([])  # 오류 발생 시 빈 리스트 전달
    
    def show_search_results(self):
        """검색 결과 테이블에 표시"""
        self.result_table.setRowCount(0)  # 테이블 초기화
        
        if not self.search_results:
            # 검색 결과가 없을 경우 테이블 숨김
            self.result_table.setVisible(False)
            return
            
        # 테이블 채우기
        for i, stock in enumerate(self.search_results):
            self.result_table.insertRow(i)
            
            # 종목 코드
            code_item = QTableWidgetItem(stock.get("stk_cd", ""))
            code_item.setTextAlignment(Qt.AlignCenter)
            self.result_table.setItem(i, 0, code_item)
            
            # 종목 이름
            name_item = QTableWidgetItem(stock.get("stk_nm", ""))
            name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.result_table.setItem(i, 1, name_item)
            
            # 현재가
            price = stock.get("cur_prc", "0")
            if isinstance(price, str):
                price = price.replace(',', '').replace('+', '').replace('-', '')
                try:
                    price = int(price)
                except ValueError:
                    price = 0
            price_item = QTableWidgetItem(f"{price:,}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.result_table.setItem(i, 2, price_item)
            
        # 테이블 표시
        self.result_table.setVisible(True)
        
        # 첫 번째 항목이 있으면 자동 선택
        if self.result_table.rowCount() > 0:
            self.result_table.selectRow(0)
            
    def on_item_double_clicked(self, item):
        """테이블 항목 더블 클릭 이벤트 처리"""
        row = item.row()
        if row >= 0 and row < len(self.search_results):
            stock_code = self.result_table.item(row, 0).text()
            stock_name = self.result_table.item(row, 1).text()
            
            # 선택 신호 발생
            self.stock_selected.emit(stock_code, stock_name)
            
            # 검색 필드 갱신
            self.search_input.setText(f"{stock_name} ({stock_code})")
            
            # 테이블 숨김
            self.result_table.setVisible(False) 