"""
주식 종목 테이블 위젯
"""

import logging
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QPushButton, QWidget, QVBoxLayout, QApplication, QMenu, QAbstractItemView, QStyledItemDelegate, QStyleOptionViewItem
from PySide6.QtCore import Qt, QEvent, Signal as pyqtSignal, Slot as pyqtSlot, QSize
from PySide6.QtGui import QColor, QBrush, QFont, QCursor, QAction
from typing import Dict, List, Optional, Any
from core.ui.constants.colors import Colors
from core.ui.constants.fonts import FONT_SIZES
from core.ui.constants.rules import UI_RULES
from core.ui.stylesheets import StyleSheets

logger = logging.getLogger(__name__)

class StockTableWidget(QTableWidget):
    """주식 종목 테이블 위젯"""
    
    # 셀 진입 시그널 (마우스 호버를 위해 추가)
    cellEntered = pyqtSignal(int, int)
    # 종목 더블클릭 시그널 추가 (차트 연동용)
    stockDoubleClicked = pyqtSignal(str, str)  # 종목코드, 종목명
    
    def __init__(self, parent=None, watchlist_module=None, is_search_result=False, is_favorites=False):
        super().__init__(parent)
        self.watchlist_module = watchlist_module
        self.is_search_result = is_search_result
        self.is_favorites = is_favorites
        self.hover_row = -1
        self.init_ui()
        
        # 이벤트 필터 설치
        self.viewport().installEventFilter(self)
        
        # 마우스 이동 추적 설정
        self.setMouseTracking(True)
        
        # 더블클릭 이벤트 연결
        self.cellDoubleClicked.connect(self._on_cell_double_clicked)
        
    def init_ui(self):
        """UI 초기화"""
        # 기본 설정
        self.setColumnCount(9)  # 다시 9개 컬럼으로 복원
        self.setHorizontalHeaderLabels([
            "종목명", "종목코드", "현재가", "전일대비",
            "등락률", "거래량", "거래대금", "추세", "정보"
        ])
        
        # 스타일 설정
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.BACKGROUND};
                color: {Colors.TEXT};
                border: none;
                gridline-color: {Colors.BORDER};
            }}
            QTableWidget::item {{
                padding: {UI_RULES.PADDING_SMALL};
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
            QHeaderView::section {{
                background-color: {Colors.SECONDARY};
                color: white;
                padding: {UI_RULES.PADDING_SMALL};
                border: none;
                border-right: 1px solid {Colors.BORDER};
                border-bottom: 1px solid {Colors.BORDER};
            }}
        """)
        
        # 헤더 설정
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setDefaultAlignment(Qt.AlignCenter)
        
        # 컬럼 너비 조정
        self.setColumnWidth(0, 120)  # 종목명
        self.setColumnWidth(1, 80)   # 종목코드
        self.setColumnWidth(2, 80)   # 현재가
        self.setColumnWidth(3, 80)   # 전일대비
        self.setColumnWidth(4, 80)   # 등락률
        self.setColumnWidth(5, 100)  # 거래량
        self.setColumnWidth(6, 120)  # 거래대금
        self.setColumnWidth(7, 80)   # 추세
        self.setColumnWidth(8, 120)  # 정보
        
        # 선택 설정
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        
        # 읽기 전용 설정
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        
    def eventFilter(self, obj, event):
        """이벤트 필터"""
        if obj is self.viewport():
            if event.type() == QEvent.MouseMove:
                pos = event.pos()
                row = self.rowAt(pos.y())
                
                # 이전 호버 행이 달라졌다면 버튼 업데이트
                if row != self.hover_row:
                    old_row = self.hover_row
                    self.hover_row = row
                    
                    # 이전 행의 버튼 숨기기
                    if old_row >= 0 and old_row < self.rowCount():
                        self.update_row_buttons(old_row, False)
                    
                    # 현재 행의 버튼 표시
                    if row >= 0 and row < self.rowCount():
                        self.update_row_buttons(row, True)
            
            elif event.type() == QEvent.Leave:
                # 마우스가 테이블을 벗어나면 호버 상태 초기화
                old_row = self.hover_row
                self.hover_row = -1
                
                if old_row >= 0 and old_row < self.rowCount():
                    self.update_row_buttons(old_row, False)
                    
        return super().eventFilter(obj, event)
    
    def update_row_buttons(self, row, show_button):
        """행의 버튼 업데이트"""
        if row < 0 or row >= self.rowCount():
            return
            
        stock_code = self.item(row, 1).text()  # 종목코드 컬럼
        
        if show_button:
            if self.is_search_result:
                self._show_add_button(row, stock_code)
            elif self.is_favorites:
                self._show_delete_button(row, stock_code)
        else:
            # 버튼 제거 및 추세 데이터 복원
            self._restore_trend_info(row)
    
    def _show_add_button(self, row, stock_code):
        """추가 버튼 표시"""
        add_button = QPushButton("추가")
        add_button.setStyleSheet(StyleSheets.ADD_BUTTON)
        add_button.clicked.connect(lambda: self._on_add_stock(stock_code))
        # 정보 컬럼(9번째 컬럼)에 버튼 표시
        self.setCellWidget(row, 8, add_button)
    
    def _show_delete_button(self, row, stock_code):
        """삭제 버튼 표시"""
        del_button = QPushButton("삭제")
        del_button.setStyleSheet(StyleSheets.DELETE_BUTTON)
        del_button.clicked.connect(lambda: self._on_remove_stock(stock_code))
        # 정보 컬럼(9번째 컬럼)에 버튼 표시
        self.setCellWidget(row, 8, del_button)
    
    def _restore_trend_info(self, row):
        """추세 정보 복원 및 정보 컬럼 비움"""
        # 버튼 제거
        self.removeCellWidget(row, 8)
        
        # 추세 정보 복원
        if self.item(row, 0) is not None:  # 종목이 있는 경우에만
            stock_info = self._get_stock_info_from_row(row)
            if stock_info:
                # 추세 정보 다시 표시
                if self.watchlist_module:
                    trend_info = self.watchlist_module.get_trend_info(stock_info)
                    trend_str = f"{trend_info['arrow']} {trend_info['text']}"
                    trend_item = QTableWidgetItem(trend_str)
                    trend_item.setTextAlignment(Qt.AlignCenter)
                    trend_item.setForeground(QColor(trend_info['color']))
                    trend_item.setFont(QFont(self.font().family(), int(self.font().pointSize() * 1.1), QFont.Bold))
                    self.setItem(row, 7, trend_item)
                else:
                    trend_info = self._get_trend_indicator(stock_info)
                    trend_str = f"{trend_info['arrow']} {trend_info['text']}"
                    trend_item = QTableWidgetItem(trend_str)
                    trend_item.setTextAlignment(Qt.AlignCenter)
                    trend_item.setForeground(QColor(trend_info['color']))
                    trend_item.setFont(QFont(self.font().family(), int(self.font().pointSize() * 1.1), QFont.Bold))
                    self.setItem(row, 7, trend_item)
                
                # 정보 컬럼은 비워둠
                info_item = QTableWidgetItem("")
                info_item.setTextAlignment(Qt.AlignCenter)
                self.setItem(row, 8, info_item)
    
    def _on_add_stock(self, stock_code):
        """종목 추가 버튼 클릭 시"""
        if self.watchlist_module and stock_code:
            # 현재 선택된 관심목록에 종목 추가
            watchlist_id = 1  # 기본값
            # TODO: 실제 선택된 관심목록 ID 가져오기
            if hasattr(self.parent(), 'current_group_id'):
                watchlist_id = self.parent().current_group_id
                
            success = self.watchlist_module.add_stock(watchlist_id, stock_code)
            if success:
                # 추가 성공 메시지 표시
                logger.info(f"종목 {stock_code}가 관심목록에 추가되었습니다.")
    
    def _on_remove_stock(self, stock_code):
        """종목 삭제 버튼 클릭 시"""
        if self.watchlist_module and stock_code:
            # 현재 선택된 관심목록에서 종목 삭제
            watchlist_id = 1  # 기본값
            # TODO: 실제 선택된 관심목록 ID 가져오기
            if hasattr(self.parent(), 'current_group_id'):
                watchlist_id = self.parent().current_group_id
                
            success = self.watchlist_module.remove_stock(watchlist_id, stock_code)
            if success:
                # 삭제 성공 메시지 표시
                logger.info(f"종목 {stock_code}가 관심목록에서 삭제되었습니다.")

    def _get_stock_info_from_row(self, row):
        """테이블 행에서 종목 정보 가져오기"""
        if row < 0 or row >= self.rowCount():
            return None
            
        try:
            # 전일대비 값 추출 및 처리
            pred_pre_text = self.item(row, 3).text() if self.item(row, 3) else "0"
            # ▲, ▼, +, - 기호 제거 및 공백 제거
            pred_pre_value_str = pred_pre_text.replace('▲', '').replace('▼', '').replace('+', '').replace('-', '').strip()
            
            # 등락률 값 추출 및 처리
            fluc_rt_text = self.item(row, 4).text().replace('%', '').replace('+', '').strip() if self.item(row, 4) else "0"
            
            return {
                "stk_nm": self.item(row, 0).text(),
                "stk_cd": self.item(row, 1).text(),
                "cur_prc": int(self.item(row, 2).text().replace(',', '')),
                # pred_pre_value_str을 int로 변환하기 전에 빈 문자열인지 확인
                "prc_diff": int(pred_pre_value_str.replace(',', '')) if pred_pre_value_str else 0,
                "fluc_rt": float(fluc_rt_text) if fluc_rt_text else 0.0, # 빈 문자열 처리 추가
                "trd_qty": int(self.item(row, 5).text().replace(',', '')),
                "trd_amt": int(self.item(row, 6).text().replace(',', ''))
            }
        except (ValueError, AttributeError) as e:
            logger.error(f"행 데이터 변환 중 오류: {e}")
            return None
            
    def update_stock_data(self, stocks: List[Dict]):
        """종목 데이터 업데이트
        
        Args:
            stocks: 종목 정보 목록
        """
        logger.debug(f"테이블 데이터 업데이트: {len(stocks)}개 종목")
        try:
            self.clearContents()
            # 전체 행 설정
            self.setRowCount(len(stocks))
            
            # 데이터 채우기
            for row, stock in enumerate(stocks):
                try:
                    # 1. 종목명 (첫번째 컬럼)
                    name_item = QTableWidgetItem(stock.get('stk_nm', ''))
                    name_item.setTextAlignment(Qt.AlignCenter)
                    self.setItem(row, 0, name_item)
                    
                    # 2. 종목코드 (두번째 컬럼)
                    code_item = QTableWidgetItem(stock.get('stk_cd', ''))
                    code_item.setTextAlignment(Qt.AlignCenter)
                    self.setItem(row, 1, code_item)
                    
                    # 3. 현재가
                    price_str = self._format_number(stock.get('cur_prc', 0))
                    price_item = QTableWidgetItem(price_str)
                    price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    
                    # 등락에 따른 색상 설정
                    price_color = self._get_price_color(stock)
                    price_item.setForeground(price_color)
                    
                    self.setItem(row, 2, price_item)
                    
                    # 4. 전일대비
                    diff_str = self._format_price_diff(stock)
                    diff_item = QTableWidgetItem(diff_str)
                    diff_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    diff_item.setForeground(price_color)
                    self.setItem(row, 3, diff_item)
                    
                    # 5. 등락률
                    change_str = self._format_change_rate(stock)
                    change_item = QTableWidgetItem(change_str)
                    change_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    change_item.setForeground(price_color)
                    self.setItem(row, 4, change_item)
                    
                    # 6. 거래량
                    # 거래량은 'trde_qty' 또는 'trd_qty' 필드에서 가져옴
                    volume_str = self._format_number(stock.get('trde_qty', stock.get('trd_qty', 0)))
                    volume_item = QTableWidgetItem(volume_str)
                    volume_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.setItem(row, 5, volume_item)
                    
                    # 7. 거래대금
                    # 거래대금은 'trde_prica' 필드에서 가져옴
                    amount_str = self._format_number(stock.get('trde_prica', 0))
                    amount_item = QTableWidgetItem(amount_str)
                    amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.setItem(row, 6, amount_item)
                    
                    # 8. 추세
                    trend_info = stock.get('trend_info', self._get_trend_info(stock))
                    trend_str = f"{trend_info['arrow']} {trend_info['text']}"
                    trend_item = QTableWidgetItem(trend_str)
                    trend_item.setTextAlignment(Qt.AlignCenter)
                    trend_item.setForeground(QColor(trend_info['color']))
                    trend_item.setFont(QFont(self.font().family(), int(self.font().pointSize() * 1.1), QFont.Bold))
                    self.setItem(row, 7, trend_item)
                    
                    # 9. 정보 컬럼 - 빈 값으로 설정
                    info_item = QTableWidgetItem("")
                    info_item.setTextAlignment(Qt.AlignCenter)
                    self.setItem(row, 8, info_item)
                    
                    # 원본 데이터 저장 (호버 버튼 등에서 사용)
                    for col in range(self.columnCount()):
                        if self.item(row, col):
                            self.item(row, col).setData(Qt.UserRole, stock)
                    
                except Exception as e:
                    logger.error(f"{row}행 데이터 설정 중 오류: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"테이블 데이터 업데이트 중 오류 발생: {e}", exc_info=True)
            
    def _get_trend_info(self, stock: Dict) -> Dict:
        """종목의 추세 정보를 반환합니다."""
        try:
            # 등락률 - flu_rt 또는 fluc_rt 필드 사용
            fluc_rt_value = stock.get('flu_rt', stock.get('fluc_rt', '0'))
            
            # 문자열 처리
            if isinstance(fluc_rt_value, str):
                fluc_rt_value = fluc_rt_value.replace('%', '').replace('+', '').strip()
                
            # 숫자 변환
            try:
                fluc_rt = float(fluc_rt_value)
            except ValueError:
                fluc_rt = 0.0
                
            # 거래량 확인 - trde_qty 또는 trd_qty 필드 사용
            volume_str = stock.get('trde_qty', stock.get('trd_qty', '0'))
            if isinstance(volume_str, str):
                volume_str = volume_str.replace(',', '')
            
            try:
                volume = int(float(volume_str))
            except ValueError:
                volume = 0
                
            # 주어진 요구사항에 따라 추세 정보 생성
            if fluc_rt >= 5 and volume >= 1000000:
                return {
                    "arrow": "↑↑",
                    "text": "강한 상승",
                    "color": Colors.PRICE_UP
                }
            elif fluc_rt >= 1:
                return {
                    "arrow": "↑",
                    "text": "상승",
                    "color": Colors.PRICE_UP
                }
            elif fluc_rt <= -5 and volume >= 1000000:
                return {
                    "arrow": "↓↓",
                    "text": "강한 하락",
                    "color": Colors.PRICE_DOWN
                }
            elif fluc_rt <= -1:
                return {
                    "arrow": "↓",
                    "text": "하락",
                    "color": Colors.PRICE_DOWN
                }
            else:
                return {
                    "arrow": "→",
                    "text": "중립",
                    "color": Colors.PRICE_UNCHANGED
                }
        except Exception as e:
            logger.error(f"추세 정보 계산 실패: {e}", exc_info=True)
            return {
                "arrow": "→",
                "text": "정보 없음",
                "color": Colors.TEXT
            }
        
    def _get_price_color(self, stock: Dict) -> QColor:
        """가격 변동에 따른 색상 반환
        
        Args:
            stock: 종목 정보
            
        Returns:
            QColor 인스턴스
        """
        # 등락 부호 확인
        sign = stock.get('prc_diff_sign', stock.get('pred_pre_sig', '0'))
        
        # 등락률로 보합 여부 확인 (0%인 경우 보합)
        fluc_rt_value = stock.get('fluc_rt', stock.get('flu_rt', '0'))
        try:
            if isinstance(fluc_rt_value, str):
                fluc_rt_value = fluc_rt_value.replace('%', '').replace('+', '').strip()
            fluc_rt = float(fluc_rt_value)
            if fluc_rt == 0:
                return QColor(Colors.PRICE_UNCHANGED)
        except:
            pass
            
        # 가격 변동에 따른 색상 반환
        if sign in ('1', '2', '3', '+'):
            return QColor(Colors.PRICE_UP)
        elif sign in ('4', '5', '6', '-'):
            return QColor(Colors.PRICE_DOWN)
        else:
            return QColor(Colors.PRICE_UNCHANGED)
        
    def _format_number(self, value) -> str:
        """숫자 형식 변환 (천 단위 구분)
        
        Args:
            value: 숫자 값
            
        Returns:
            형식 변환된 문자열
        """
        try:
            # 문자열로 변환
            value_str = str(value).replace(',', '')
            
            # 숫자로 변환
            value_int = int(float(value_str))
            
            # 천 단위 구분
            return format(value_int, ',')
        except:
            return str(value)
        
    def _format_price_diff(self, stock: Dict) -> str:
        """전일대비 형식 변환 (요구사항 반영)
        
        Args:
            stock: 종목 정보
            
        Returns:
            형식 변환된 문자열
        """
        # 전일대비 값 (pred_pre 또는 prc_diff)
        diff = stock.get('pred_pre', stock.get('prc_diff', 0))
        
        # 등락 부호 확인 (pred_pre_sig 또는 prc_diff_sign)
        sign = stock.get('pred_pre_sig', stock.get('prc_diff_sign', '0')) # 기본값을 '0'으로
        
        # 숫자 형식 변환
        try:
            diff_value_str = str(diff).replace(',', '').replace('+', '')
            # '-' 부호는 유지해야 하므로 제거하지 않음
            diff_value = float(diff_value_str)
            formatted = self._format_number(abs(diff_value))
        except:
            formatted = str(diff)
            if formatted == '0': # 숫자로 변환 실패 시 0이면 보합 처리
                sign = '0' # 보합 기호 사용을 위해 sign 강제 변경
        
        # 부호(pred_pre_sig)에 따른 기호 매핑
        # 사용자 최종 요구사항 기준으로 기호 매핑 적용
        sign_symbol_map = {
            '1': '▲',  # 상한가 수준의 매우 강한 상승
            '2': '△',  # 강한 상승
            '3': '-',  # 보합 (등락률 0.00%)
            '0': '-',  # 보합
            '4': '▽',  # 강한 하락
            '5': '▼',  # 하한가 수준의 매우 강한 하락
            # '6': 사용 안 함
        }
        
        # API 응답의 4, 5를 요구사항의 -1, -2 등에 대응시키기 위한 처리
        # (실제 API 응답에서 pred_pre_sig가 음수로 오는지는 확인되지 않음)
        # 6은 사용하지 않으므로 관련 로직 제거
        if sign.startswith('-'):
             sign_adjusted = str(int(sign))
             if sign_adjusted == '-1': sign = '4' # 요구사항 -1(강한하락) -> API 4 -> 기호 ▽
             elif sign_adjusted == '-2': sign = '5' # 요구사항 -2(하한가수준) -> API 5 -> 기호 ▼
             # -3 및 그 외 음수값은 가장 강한 단계인 5로 처리 (▼)
             else: sign = '5' 
             
        # 숫자 0이면 무조건 보합 처리 ('0')
        if diff_value == 0:
            sign = '0'
        
        # 매핑된 기호 가져오기 (기본값: 보합 기호)
        # 정의되지 않은 6 등이 올 경우 보합(-)으로 처리
        sign_symbol = sign_symbol_map.get(sign, '-') 
        
        # 기호와 숫자 함께 반환
        return f"{sign_symbol} {formatted}"
        
    def _format_change_rate(self, stock: Dict) -> str:
        """등락률 형식 변환
        
        Args:
            stock: 종목 정보
            
        Returns:
            형식 변환된 문자열
        """
        # 등락률 값 (flu_rt 또는 fluc_rt)
        rate = stock.get('flu_rt', stock.get('fluc_rt', 0))
        
        # 문자열 처리
        if isinstance(rate, str):
            if rate.endswith('%'):
                rate = rate.replace('%', '')
            if rate.startswith('+'):
                rate = rate[1:]
        
        try:
            # 숫자로 변환
            rate_float = float(rate)
            
            # 값이 0이면 보합 (부호 없음)
            if rate_float == 0:
                return f"{rate_float:.2f}%"
            
            # 부호에 따른 접두사 추가
            prefix = ''
            if rate_float > 0:
                prefix = '+'
            elif rate_float < 0:
                prefix = '-'
                rate_float = abs(rate_float)  # 절대값 사용
            
            # 소수점 둘째 자리까지 표시
            return f"{prefix}{rate_float:.2f}%"
        except:
            return f"{rate}%"
    
    def add_stock(self, stock: Dict):
        """종목 추가
        
        Args:
            stock: 종목 정보
        """
        # None 체크 추가
        if stock is None:
            logger.error("추가할 종목 정보가 없습니다. (None)")
            return
        
        # 필수 필드 체크
        if not stock.get("stk_cd"):
            logger.error("추가할 종목 정보에 종목코드가 없습니다.")
            return
        
        logger.debug(f"종목 추가: {stock.get('stk_cd')} ({stock.get('stk_nm', '이름 없음')})")
        
        try:
            # 새 행 추가
            row = self.rowCount()
            self.setRowCount(row + 1)
            
            # 종목명 (첫번째 컬럼)
            name_item = QTableWidgetItem(str(stock.get("stk_nm", "")))
            name_item.setTextAlignment(Qt.AlignCenter)
            self.setItem(row, 0, name_item)
            
            # 종목코드 (두번째 컬럼)
            code_item = QTableWidgetItem(str(stock.get("stk_cd", "")))
            code_item.setTextAlignment(Qt.AlignCenter)
            self.setItem(row, 1, code_item)
            
            # 현재가
            try:
                cur_prc_val = stock.get('cur_prc', '0')
                # 문자열이 들어올 경우 숫자로 변환
                if isinstance(cur_prc_val, str):
                    cur_prc_val = cur_prc_val.replace(',', '')
                cur_prc_formatted = f"{float(cur_prc_val):,.0f}"
                price_item = QTableWidgetItem(cur_prc_formatted)
            except ValueError:
                # 변환 실패 시 그대로 표시
                price_item = QTableWidgetItem(str(stock.get('cur_prc', '0')))
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 2, price_item)
            
            # 전일대비
            prc_diff = stock.get('prc_diff', 0)
            sign = stock.get('prc_diff_sign', '')
            
            # 문자열이 들어올 경우 숫자로 변환
            try:
                if isinstance(prc_diff, str):
                    prc_diff = prc_diff.replace(',', '')
                prc_diff = float(prc_diff)
            except ValueError:
                prc_diff = 0
                
            # 등락 기호 처리
            sign_symbol = ""
            if sign == "1" or prc_diff > 0:  # 상승
                sign_symbol = "▲ "
                change_item = QTableWidgetItem(f"{sign_symbol}{abs(prc_diff):,.0f}")
                change_item.setForeground(QColor(Colors.PRICE_UP))
            elif sign == "2" or prc_diff < 0:  # 하락
                sign_symbol = "▼ "
                change_item = QTableWidgetItem(f"{sign_symbol}{abs(prc_diff):,.0f}")
                change_item.setForeground(QColor(Colors.PRICE_DOWN))
            else:  # 보합
                change_item = QTableWidgetItem(f"{prc_diff:,.0f}")
                change_item.setForeground(QColor(Colors.PRICE_UNCHANGED))
                
            change_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 3, change_item)
            
            # 등락률
            fluc_rt = stock.get('fluc_rt', 0)
            try:
                if isinstance(fluc_rt, str):
                    fluc_rt = fluc_rt.replace('%', '').strip()
                fluc_rt = float(fluc_rt)
            except ValueError:
                fluc_rt = 0
                
            if fluc_rt > 0:
                rate_item = QTableWidgetItem(f"+{fluc_rt:.2f}%")
                rate_item.setForeground(QColor(Colors.PRICE_UP))
            elif fluc_rt < 0:
                rate_item = QTableWidgetItem(f"{fluc_rt:.2f}%")
                rate_item.setForeground(QColor(Colors.PRICE_DOWN))
            else:
                rate_item = QTableWidgetItem(f"{fluc_rt:.2f}%")
                rate_item.setForeground(QColor(Colors.PRICE_UNCHANGED))
            
            rate_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 4, rate_item)
            
            # 거래량
            try:
                trd_qty = stock.get('trd_qty', 0)
                if isinstance(trd_qty, str):
                    trd_qty = trd_qty.replace(',', '')
                volume_item = QTableWidgetItem(f"{int(float(trd_qty)):,}")
            except ValueError:
                volume_item = QTableWidgetItem(str(stock.get('trd_qty', '0')))
            volume_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 5, volume_item)
            
            # 거래대금
            try:
                trde_prica = stock.get('trde_prica', 0)
                if isinstance(trde_prica, str):
                    trde_prica = trde_prica.replace(',', '')
                amount_item = QTableWidgetItem(f"{int(float(trde_prica)):,}")
            except ValueError:
                amount_item = QTableWidgetItem(str(stock.get('trde_prica', '0')))
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 6, amount_item)
            
            # 추세
            if self.watchlist_module:
                trend_info = self.watchlist_module.get_trend_info(stock)
                trend_item = QTableWidgetItem(f"{trend_info['arrow']} {trend_info['text']}")
                trend_item.setTextAlignment(Qt.AlignCenter)
                trend_item.setForeground(QColor(trend_info['color']))
                self.setItem(row, 7, trend_item)
                
                # 색상 설정
                self._set_row_color(row, stock, trend_info)
            else:
                trend_info = self._get_trend_indicator(stock)
                trend_item = QTableWidgetItem(f"{trend_info['arrow']} {trend_info['text']}")
                trend_item.setTextAlignment(Qt.AlignCenter)
                trend_item.setForeground(QColor(trend_info['color']))
                trend_item.setFont(QFont(self.font().family(), int(self.font().pointSize() * 1.1), QFont.Bold))
                self.setItem(row, 7, trend_item)
                
                # 색상 설정
                self._set_row_color(row, stock, trend_info)
            
            # 정보 컬럼 - 빈 셀로 설정
            info_item = QTableWidgetItem("")
            info_item.setTextAlignment(Qt.AlignCenter)
            self.setItem(row, 8, info_item)
            
        except Exception as e:
            logger.error(f"종목 추가 중 오류 발생: {e}", exc_info=True)
            
    def _get_trend_indicator(self, stock):
        """추세 지표 반환
        
        Args:
            stock: 종목 정보
            
        Returns:
            추세 지표 (dict)
        """
        # 등락률 가져오기
        change_rate = stock.get('flu_rt', stock.get('fluc_rt', 0))
        
        # 거래량 가져오기
        volume = stock.get('trde_qty', stock.get('trd_qty', 0))
        
        # 문자열을 숫자로 변환
        if isinstance(change_rate, str):
            try:
                # '%', '+' 문자 제거 및 공백 제거
                change_rate = change_rate.replace('%', '').replace('+', '').strip()
                change_rate = float(change_rate)
            except ValueError:
                change_rate = 0
                
        # 거래량을 숫자로 변환
        if isinstance(volume, str):
            try:
                volume = volume.replace(',', '')
                volume = float(volume)
            except ValueError:
                volume = 0
                
        # 추세 판단
        if change_rate >= 5 and volume >= 1000000:  # 등락률 5% 이상, 거래량 100만 이상
            return {
                "arrow": "↑↑",
                "text": "강한 상승",
                "color": Colors.PRICE_UP
            }
        elif change_rate >= 1:  # 등락률 1% 이상
            return {
                "arrow": "↑",
                "text": "상승",
                "color": Colors.PRICE_UP
            }
        elif change_rate <= -5 and volume >= 1000000:  # 등락률 -5% 이하, 거래량 100만 이상
            return {
                "arrow": "↓↓",
                "text": "강한 하락",
                "color": Colors.PRICE_DOWN
            }
        elif change_rate <= -1:  # 등락률 -1% 이하
            return {
                "arrow": "↓",
                "text": "하락",
                "color": Colors.PRICE_DOWN
            }
        else:  # 등락률 -1%~1% 사이
            return {
                "arrow": "→",
                "text": "중립",
                "color": Colors.PRICE_UNCHANGED
            }
            
    def _set_row_color(self, row, stock_or_change_rate, trend_info=None):
        """행 색상 설정
        
        Args:
            row: 행 번호
            stock_or_change_rate: 종목 정보 또는 등락률
            trend_info: 트렌드 정보 (있는 경우)
        """
        try:
            if trend_info is not None:
                # 트렌드 정보가 있는 경우 (watchlist_module 사용)
                color = trend_info.get("color", Colors.BACKGROUND)
                
                # 강한 상승/하락일 경우에만 약한 배경색 설정 (0.1 알파값)
                if color == Colors.PRICE_UP and "강한" in trend_info.get("text", ""):
                    bg_color = QColor(255, 200, 200, 30)  # 연한 빨간색 배경
                elif color == Colors.PRICE_DOWN and "강한" in trend_info.get("text", ""):
                    bg_color = QColor(200, 200, 255, 30)  # 연한 파란색 배경
                else:
                    bg_color = QColor(Colors.BACKGROUND)  # 기본 배경색
                    
                # 모든 셀에 배경색 설정
                for col in range(self.columnCount()):
                    item = self.item(row, col)
                    if item:
                        item.setBackground(bg_color)
            else:
                # 기존 방식 (등락률로 색상 설정)
                fluc_rt = stock_or_change_rate
                if isinstance(stock_or_change_rate, dict):
                    fluc_rt = stock_or_change_rate.get('fluc_rt', 0)
                    
                # 상승/하락에 따른 배경색 설정
                if fluc_rt > 5:
                    bg_color = QColor(255, 200, 200, 30)  # 연한 빨간색 (강한 상승)
                elif fluc_rt < -5:
                    bg_color = QColor(200, 200, 255, 30)  # 연한 파란색 (강한 하락)
                else:
                    bg_color = QColor(Colors.BACKGROUND)  # 기본 배경색
                    
                # 모든 셀에 배경색 설정
                for col in range(self.columnCount()):
                    item = self.item(row, col)
                    if item:
                        item.setBackground(bg_color)
        except Exception as e:
            logger.error(f"행 색상 설정 중 오류 발생: {e}", exc_info=True)
    
    def _get_atn_stk_infr_text(self, stock: Dict) -> str:
        """관심종목정보 텍스트 반환
        
        Args:
            stock: 종목 정보
            
        Returns:
            관심종목정보 텍스트 (빈 문자열 반환)
        """
        # 정보 컬럼에는 내용을 표시하지 않음
        return ""
                
    def clear_data(self):
        """테이블 데이터 초기화"""
        self.setRowCount(0)
        
    def contextMenuEvent(self, event):
        """컨텍스트 메뉴 이벤트"""
        menu = QMenu(self)
        
        # 행 선택 확인
        selected_rows = set(idx.row() for idx in self.selectedIndexes())
        if selected_rows:
            # 선택된 행이 있는 경우 액션 추가
            add_action = QAction("관심종목에 추가", self)
            delete_action = QAction("관심종목에서 삭제", self)
            
            menu.addAction(add_action)
            menu.addAction(delete_action)
            
        # 기본 액션 추가
        refresh_action = QAction("새로고침", self)
        menu.addAction(refresh_action)
        
        # 메뉴 표시
        menu.exec_(event.globalPos())

    def mouseMoveEvent(self, event):
        """마우스 이동 이벤트"""
        # 마우스 위치의 셀 좌표 계산
        pos = event.pos()
        row = self.rowAt(pos.y())
        column = self.columnAt(pos.x())
        
        # 유효한 셀 위에 있을 경우 신호 발생
        if row >= 0 and column >= 0:
            self.cellEntered.emit(row, column)
            
        super().mouseMoveEvent(event) 

    def _on_cell_double_clicked(self, row, column):
        """테이블 셀 더블 클릭 시 stockDoubleClicked 시그널 발생"""
        try:
            code_item = self.item(row, 1) # 종목코드 컬럼
            name_item = self.item(row, 0) # 종목명 컬럼
            # --- 디버깅 로그 추가 ---
            logger.debug(f"더블클릭 아이템 확인: code_item={code_item}, name_item={name_item}")
            if code_item: logger.debug(f"code_item text: '{code_item.text()}'")
            if name_item: logger.debug(f"name_item text: '{name_item.text()}'")
            # --- 로그 추가 끝 ---
            
            if code_item and name_item:
                stock_code = code_item.text()
                stock_name = name_item.text()
                logger.debug(f"종목 더블클릭: {stock_name}({stock_code})")
                self.stockDoubleClicked.emit(stock_code, stock_name) # str, str 시그널 발생
            else:
                logger.warning(f"더블클릭된 행({row})에서 종목코드/이름 가져오기 실패")
        except Exception as e:
             logger.error(f"셀 더블클릭 처리 중 오류: {e}", exc_info=True) 