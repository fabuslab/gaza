"""
PyQtGraph 기반 차트 표시 위젯
"""

import logging
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel, QToolBar
from PySide6.QtCore import Qt, Slot as pyqtSlot, Signal as pyqtSignal, QPointF
from PySide6.QtGui import QMouseEvent
import pandas as pd
from typing import Dict, List, Optional, Tuple
import numpy as np
from pyqtgraph import BarGraphItem # BarGraphItem은 pyqtgraph에서 직접 임포트
from datetime import datetime, timedelta

from .custom_graphics import CandlestickItem # CandlestickItem만 custom_graphics에서 임포트
from .custom_axis import PriceAxis, OrdinalDateAxis # OrdinalDateAxis 추가
from core.ui.constants.colors import Colors  # 수정된 경로
from core.ui.stylesheets import StyleSheets # 수정된 경로
from core.modules.chart import ChartModule
from core.ui.constants.chart_defs import INDICATOR_MAP

logger = logging.getLogger(__name__)

# 보조지표 키-이름 매핑 (chart_window.py에서 이동)
# INDICATOR_MAP = {
#     'MA': '이동평균선',
#     'BB': '볼린저밴드',
#     'RSI': 'RSI',
#     'MACD': 'MACD',
#     'Volume': '거래량',
#     'TradingValue': '거래대금'
# }

# 표준 캔들 색상 정의 (한국 시장 관행에 맞춤)
# 한국 증시에서는 상승=빨간색, 하락=파란색이 표준
UP_COLOR = pg.mkColor(Colors.CANDLE_UP)     # 상승 캔들 색상 (빨강)
DOWN_COLOR = pg.mkColor(Colors.CANDLE_DOWN) # 하락 캔들 색상 (파랑)
NEUTRAL_COLOR = pg.mkColor('k')             # 보합 캔들 색상 (검정)

class ChartComponent(QWidget):
    """pyqtgraph를 이용한 차트 표시 컴포넌트"""

    # 시그널 정의 (필요에 따라 추가)
    crosshair_moved = pyqtSignal(float, float) # 마우스 위치 시그널 (x: ordinal, y: price) 활성화
    chart_loaded = pyqtSignal(bool) # 데이터 로딩 완료/실패 시그널

    def __init__(self, chart_module, parent=None):
        super().__init__(parent)
        self.chart_module = chart_module # ChartModule 참조 저장
        self.current_stock_code: Optional[str] = None
        self.current_period: str = 'D'
        self.chart_data: pd.DataFrame = pd.DataFrame()

        # Plot 아이템 저장용 딕셔너리
        self.plot_items: Dict[str, pg.PlotItem] = {}
        self.data_items: Dict[str, pg.GraphicsObject] = {}
        # 보조지표 PlotItem 저장
        self.indicator_plots: Dict[str, pg.PlotItem] = {}
        self.indicator_items: Dict[str, pg.PlotCurveItem] = {}

        # 크로스헤어용 라인
        self.v_line: Optional[pg.InfiniteLine] = None
        self.h_line: Optional[pg.InfiniteLine] = None
        self.proxy: Optional[pg.SignalProxy] = None
        self.tooltip_label: Optional[pg.TextItem] = None # 툴팁용 TextItem (개선 필요)
        self.crosshair_labels: Dict[str, pg.InfLineLabel] = {} # 크로스헤어 라벨 저장

        # 툴팁용 TextItem 추가
        self.tooltip_text = pg.TextItem(anchor=(0, 1))
        
        self.latest_tick_data: Optional[Dict] = None # 실시간 데이터 저장용
        
        self._init_ui()
        self._setup_interactions()
        self.connectAxisSignals() # --- 추가: 축 시그널 연결 호출 --- 

        logger.info("새 ChartComponent 초기화 완료.")

    def _init_ui(self):
        """차트 UI 구성"""
        pg.setConfigOptions(antialias=True) # 안티앨리어싱 활성화
        pg.setConfigOption('background', Colors.CHART_BACKGROUND)
        pg.setConfigOption('foreground', Colors.CHART_FOREGROUND)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Graphics Layout Widget 생성
        self.win = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.win)

        # 1. 가격 차트 PlotItem 생성
        self.price_axis = PriceAxis(orientation='left')
        self.ordinal_axis = OrdinalDateAxis(orientation='bottom')
        price_plot = self.win.addPlot(
            row=0, col=0,
            axisItems={'bottom': self.ordinal_axis, 'left': self.price_axis}
        )
        price_plot.setDownsampling(mode='peak')
        price_plot.setClipToView(True)
        price_plot.showGrid(x=True, y=True, alpha=0.3)
        price_plot.setLimits(xMin=-1e9, xMax=2e9, yMin=-1e9, yMax=1e9) # 예시 한계 설정
        price_plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
        self.plot_items['price'] = price_plot

        # 가격 차트 생성 후 툴팁 아이템 추가
        price_plot.addItem(self.tooltip_text, ignoreBounds=True)
        self.tooltip_text.setZValue(100) # 다른 아이템 위에 보이도록
        self.tooltip_text.hide() # 초기 숨김

        # 2. 거래량 차트 PlotItem 생성
        # 가격 차트와 X축 공유
        volume_plot = self.win.addPlot(row=1, col=0)
        volume_plot.setMaximumHeight(150) # 높이 제한
        volume_plot.setXLink(price_plot) # X축 연결
        volume_plot.setDownsampling(mode='peak')
        volume_plot.setClipToView(True)
        volume_plot.showGrid(x=True, y=True, alpha=0.1)
        # --- 수정 시작: 거래량 Y축에 PriceAxis 적용 및 SI Prefix 비활성화 제거 ---
        volume_axis = PriceAxis(orientation='left')
        # volume_axis.enableSIprefix(False) # 지수 표기 비활성화 (제거)
        volume_plot.setAxisItems({'left': volume_axis})
        # --- 수정 끝 ---
        volume_plot.getAxis('left').setWidth(self.price_axis.width()) # Y축 너비 맞춤
        # --- 수정 시작: 거래량 Y축 라벨 추가 ---
        volume_plot.setLabel('left', '거래량')
        # --- 수정 끝 ---
        volume_plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
        self.plot_items['volume'] = volume_plot
        
        # 3. 거래대금 차트 PlotItem 생성 (필요시)
        value_plot = self.win.addPlot(row=2, col=0) # 거래량 아래(row=2)에 추가
        value_plot.setMaximumHeight(150) # 거래량과 동일한 높이 제한
        value_plot.setXLink(price_plot) # 가격 차트와 X축 공유
        value_plot.setDownsampling(mode='peak')
        value_plot.setClipToView(True)
        value_plot.showGrid(x=True, y=True, alpha=0.1)
        # --- 수정 시작: 거래대금 Y축에 PriceAxis 적용 및 SI Prefix 비활성화 제거 ---
        value_axis = PriceAxis(orientation='left') # 왼쪽 Y축 사용
        # value_axis.enableSIprefix(False) # 지수 표기 비활성화 (제거)
        value_plot.setAxisItems({'left': value_axis})
        # --- 수정 끝 ---
        value_plot.getAxis('left').setWidth(self.price_axis.width()) # Y축 너비 맞춤
        value_plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
        value_plot.setLabel('left', '거래대금') # Y축 라벨 설정
        self.plot_items['value'] = value_plot # PlotItem으로 저장
        # --- 수정: 거래대금 차트 명시적으로 보이도록 설정 ---
        value_plot.show() 
        # --- 수정 끝 ---

        # --- 보조지표 PlotItem 추가 (행 번호 조정) --- 
        # RSI Plot
        rsi_plot = self.win.addPlot(row=3, col=0) # 거래대금 아래(row=3)로 이동
        rsi_plot.setMaximumHeight(100)
        rsi_plot.showGrid(x=True, y=True, alpha=0.1)
        rsi_plot.setXLink(price_plot)
        rsi_plot.getAxis('left').setWidth(self.price_axis.width())
        rsi_plot.setYRange(0, 100) # RSI 범위는 고정
        self.indicator_plots['RSI'] = rsi_plot
        rsi_plot.hide() # 기본 숨김

        # MACD Plot
        macd_plot = self.win.addPlot(row=4, col=0) # RSI 아래(row=4)로 이동
        macd_plot.setMaximumHeight(100)
        macd_plot.showGrid(x=True, y=True, alpha=0.1)
        macd_plot.setXLink(price_plot)
        macd_plot.getAxis('left').setWidth(self.price_axis.width())
        self.indicator_plots['MACD'] = macd_plot
        macd_plot.hide() # 기본 숨김
        # ------------------------------

        # X축 범위 변경 시그널 연결
        # price_plot.sigXRangeChanged.connect(self._on_xrange_changed)

        logger.info("차트 Plot Item 초기화 완료 (OrdinalDateAxis 사용)")

    def _setup_interactions(self):
        """차트 인터랙션 (크로스헤어, 줌/팬 등) 설정"""
        # 1. 크로스헤어 설정
        pen = pg.mkPen(color=Colors.CROSSHAIR, style=Qt.DashLine, width=0.8)
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pen)
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pen)
        self.plot_items['price'].addItem(self.v_line, ignoreBounds=True)
        self.plot_items['price'].addItem(self.h_line, ignoreBounds=True)
        
        # 가격/시간 라벨 추가 (천단위 구분자 포맷)
        self.crosshair_labels['price'] = pg.InfLineLabel(
            self.h_line, 
            text="{value:,.0f}", 
            position=0.95, 
            color=Colors.TOOLTIP_TEXT,
            fill=pg.mkBrush(Colors.TOOLTIP_BACKGROUND),
            border=pg.mkPen(Colors.BORDER)
        )
        self.crosshair_labels['time'] = pg.InfLineLabel(
            self.v_line, 
            text="{value}", 
            position=0.95, 
            color=Colors.TOOLTIP_TEXT, 
            angle=90,
            fill=pg.mkBrush(Colors.TOOLTIP_BACKGROUND),
            border=pg.mkPen(Colors.BORDER)
        )
        
        # 크로스헤어 초기 숨김
        self.v_line.hide()
        self.h_line.hide()

        # 마우스 이동 시그널 연결
        price_plot = self.plot_items.get('price')
        if price_plot:
            # 직접 이벤트 연결 (SignalProxy 대신 사용)
            price_plot.scene().sigMouseMoved.connect(self._on_mouse_moved)
            
            # 스크린샷 오류 디버깅 용: 추가 SignalProxy 연결
            self.proxy = pg.SignalProxy(
                price_plot.scene().sigMouseMoved, 
                rateLimit=60,  # 초당 최대 60회 호출 제한
                slot=self._mouse_moved
            )
            
            logger.debug("크로스헤어 이벤트 연결 완료 (직접 연결 + SignalProxy 백업)")
        else:
            logger.error("Price PlotItem이 없어 마우스 시그널 연결 불가")
        
        logger.info("ChartComponent 인터랙션 설정 완료.")
        
    def _on_mouse_moved(self, pos):
        """마우스 이동 직접 이벤트 처리 (SignalProxy 없이)"""
        self._update_crosshair(pos)
        
    def _mouse_moved(self, event):
        """마우스 이동 이벤트 처리 (SignalProxy 사용 시)"""
        pos = event[0]
        self._update_crosshair(pos)
        
    def _update_crosshair(self, pos):
        """크로스헤어 및 툴팁 위치 업데이트 (통합 함수)"""
        plot = self.plot_items.get('price')
        if not plot or not plot.sceneBoundingRect().contains(pos):
            self.v_line.hide()
            self.h_line.hide()
            self.tooltip_text.hide()
            return
            
        # 마우스 위치를 데이터 좌표계로 변환
        vb = plot.vb
        mouse_point = vb.mapSceneToView(pos)
        x_pos, y_pos = mouse_point.x(), mouse_point.y()
        
        # 크로스헤어 위치 업데이트 및 표시
        self.v_line.setPos(x_pos)
        self.h_line.setPos(y_pos)
        self.v_line.show()
        self.h_line.show()
        
        # 가격 라벨 업데이트 (천단위 구분자 포맷)
        self.crosshair_labels['price'].setText(f"{y_pos:,.0f}")
        
        # x 위치의 ordinal 값으로 날짜/시간 표시
        self._update_time_label(x_pos)
        
        # 툴팁 업데이트 및 표시
        self._update_tooltip(x_pos, mouse_point)
        self.tooltip_text.show()
        
        # 시그널 발생 (외부 연결용)
        self.crosshair_moved.emit(x_pos, y_pos)
        
    def _update_time_label(self, x_pos):
        """ordinal 값에 해당하는 시간 라벨 업데이트"""
        if self.chart_data.empty:
            return
            
        try:
            # 인덱스 범위 체크
            idx = int(round(x_pos))
            if 0 <= idx < len(self.chart_data):
                # 날짜 가져오기
                date_obj = self.chart_data.index[idx]
                
                # 주기별 포맷 적용
                if self.current_period == 'Y':
                    date_str = date_obj.strftime("%Y")
                elif self.current_period == 'M':
                    date_str = date_obj.strftime("%Y-%m")
                elif self.current_period == 'W':
                    weekday = date_obj.weekday()
                    start_of_week = date_obj - timedelta(days=weekday)
                    date_str = start_of_week.strftime("%Y-%m-%d")
                elif self.current_period == 'D':
                    date_str = date_obj.strftime("%Y-%m-%d")
                elif self.current_period.endswith('T'):
                    date_str = date_obj.strftime("%H:%M:%S")
                else:
                    date_str = date_obj.strftime("%H:%M")
                    
                self.crosshair_labels['time'].setText(date_str)
        except Exception as e:
            logger.error(f"시간 라벨 업데이트 오류: {e}")

    def _update_tooltip(self, x_pos, mouse_point):
        """해당 x 위치(순서번호)의 데이터를 찾아 툴팁 업데이트"""
        if self.chart_data.empty:
            # 차트 데이터가 없어도 최신 틱 정보는 표시 시도
            if self.current_period.endswith('T') and self.latest_tick_data:
                try:
                    latest_time = pd.to_datetime(self.latest_tick_data['time'], unit='s').strftime('%H:%M:%S')
                    latest_price = self.latest_tick_data['price']
                    html_text = f"<div style='background-color:{Colors.TOOLTIP_BACKGROUND}; color:{Colors.TOOLTIP_TEXT}; border: 1px solid {Colors.BORDER}; padding: 5px;'>실시간: {latest_time} {latest_price:,.0f}</div>"
                    self.tooltip_text.setHtml(html_text)
                    self.tooltip_text.setPos(mouse_point.x(), mouse_point.y())
                    self.tooltip_text.show()
                except Exception as e:
                    logger.error(f"최신 틱 툴팁 표시 오류: {e}")
                    self.tooltip_text.hide()
            else:
                self.tooltip_text.hide()
            return

        try:
            # --- 수정: ordinal 값으로 데이터 접근 및 경계 검사 강화 ---
            nearest_idx = int(round(x_pos))
            # 경계 검사 추가
            if not (0 <= nearest_idx < len(self.chart_data)):
                self.tooltip_text.hide()
                return
                
            # .iloc 사용 시 정수 인덱스 필요
            data_row = self.chart_data.iloc[nearest_idx]
            actual_index_datetime = self.chart_data.index[nearest_idx]

            # 2. 툴팁 문자열 생성 (과거 데이터 기반)
            tooltip_parts = []
            
            # 날짜 포맷팅 - 앞에서 이미 계산한 date_str 재사용 가능
            dt_str_formatted = ''
            if self.current_period == 'Y': fmt = "%Y"
            elif self.current_period == 'M': fmt = "%Y-%m"
            elif self.current_period == 'W':
                 start_of_week = actual_index_datetime - timedelta(days=actual_index_datetime.weekday())
                 end_of_week = start_of_week + timedelta(days=6)
                 dt_str_formatted = f"{start_of_week.strftime('%Y-%m-%d')} ~ {end_of_week.strftime('%Y-%m-%d')}"
                 fmt = None # 이미 포맷 완료
            elif self.current_period == 'D': fmt = '%Y-%m-%d'
            else: fmt = '%Y-%m-%d %H:%M:%S'
            
            if fmt: # 주봉 외
                dt_str_formatted = actual_index_datetime.strftime(fmt)
                
            tooltip_parts.append(f"<span style='font-size: 10pt; font-weight: bold;'>{dt_str_formatted}</span>")
            
            # OHLC 정보
            ohlc_map = {'Open': '시가', 'High': '고가', 'Low': '저가', 'Close': '종가'}
            for col, name in ohlc_map.items():
                if col in data_row:
                    val = data_row[col]
                    # 색상 적용 (종가만 색상 구분)
                    if col == 'Close':
                        if data_row['Close'] > data_row.get('Open', 0):
                            color = Colors.CANDLE_UP  # 상승
                        elif data_row['Close'] < data_row.get('Open', 0):
                            color = Colors.CANDLE_DOWN  # 하락
                        else:
                            color = Colors.CHART_FOREGROUND  # 보합
                    else:
                        color = Colors.CHART_FOREGROUND
                        
                    tooltip_parts.append(f"<span style='color:{color}'>{name}: {val:,.0f}</span>")
            
            # 거래량 정보
            if 'Volume' in data_row:
                vol = data_row['Volume']
                tooltip_parts.append(f"거래량: {vol:,.0f}")
                
            # 거래대금 정보
            if 'TradingValue' in data_row:
                value = data_row['TradingValue']
                tooltip_parts.append(f"거래대금: {value:,.0f}")

            # 보조지표 데이터 추가 (활성화된 지표만)
            for code, name in INDICATOR_MAP.items():
                # 거래량/거래대금은 이미 처리함
                if code in ['Volume', 'TradingValue']:
                    continue
                    
                # 보조지표 표시 여부 확인 - 해당 코드로 시작하는 컬럼이 있고, 아이템이 있으면 표시
                indicator_cols = [c for c in self.chart_data.columns if c.startswith(code)]
                active_items = [c for c in indicator_cols if c in self.indicator_items and self.indicator_items[c].isVisible()]
                
                if active_items:
                    for col in active_items:
                        if col in data_row and pd.notna(data_row[col]):
                            val = data_row[col]
                            # 숫자 포맷팅
                            try:
                                val_str = f"{float(val):,.2f}"
                            except (ValueError, TypeError):
                                val_str = str(val)
                                
                            # 지표 이름 가공
                            base_name = name
                            params = col.split('_')[1:]
                            param_str = f"({','.join(params)})" if params else ""
                            label = f"{base_name}{param_str}"

                            tooltip_parts.append(f"{label}: {val_str}")

            # 실시간 데이터 추가 (틱 주기일 경우)
            if self.current_period.endswith('T') and self.latest_tick_data:
                 latest_time_str = pd.to_datetime(self.latest_tick_data['time'], unit='s').strftime('%H:%M:%S')
                 latest_price = self.latest_tick_data['price']
                 tooltip_parts.append(f"<hr><span style='font-weight:bold;'>실시간:</span> {latest_time_str} <span style='font-weight:bold;color:{Colors.TOOLTIP_TEXT};'>{latest_price:,.0f}</span>")

            # TextItem 위치 및 내용 업데이트
            html_text = "<br>".join(tooltip_parts)
            
            # 테두리와 배경이 있는 스타일 적용
            styled_html = f"""
            <div style='
                background-color:{Colors.TOOLTIP_BACKGROUND}; 
                color:{Colors.TOOLTIP_TEXT}; 
                border: 1px solid {Colors.BORDER}; 
                border-radius: 3px;
                padding: 8px;
                font-size: 9pt;
                '>
                {html_text}
            </div>
            """
            
            self.tooltip_text.setHtml(styled_html)
            
            # 툴팁 위치 조정 (화면 밖으로 나가지 않도록)
            view_rect = self.plot_items['price'].viewRect()
            tooltip_width = 150  # 대략적인 툴팁 너비
            tooltip_height = 20 * len(tooltip_parts)  # 대략적인 높이
            
            # 마우스 위치 기준 적절한 위치 선택
            x_pos = min(mouse_point.x() + 10, view_rect.right() - tooltip_width)
            y_pos = min(mouse_point.y() - 10, view_rect.bottom() - tooltip_height)
            
            self.tooltip_text.setPos(x_pos, y_pos)

        except Exception as e:
            logger.error(f"툴팁 업데이트 중 오류: {e}", exc_info=True)
            self.tooltip_text.hide()

    @pyqtSlot(str, str, pd.DataFrame)
    def update_chart(self, stock_code: str, period: str, df: pd.DataFrame):
        """수신된 데이터와 주기로 차트 업데이트 (순서축 기반)"""
        logger.info(f"차트 업데이트 수신: {stock_code}, 주기={period}, 데이터 {len(df)}개")
        
        # 기존 차트 아이템 정리
        self.clear_chart_items() 
        
        # 데이터 저장
        self.chart_data = df # 'ordinal' 컬럼 포함 가정
        self.current_stock_code = stock_code 
        self.current_period = period # 주기 정보 저장

        # 차트 제목 업데이트 (부모 윈도우가 있을 경우)
        if self.parent() and hasattr(self.parent(), 'setWindowTitle'):
            # 종목명이 있으면 추가 (시그널에 추가하면 좋을 듯)
            self.parent().setWindowTitle(f'{stock_code} - {period}봉')

        # OrdinalDateAxis에 데이터와 주기 전달
        if 'price' in self.plot_items:
            axis = self.plot_items['price'].getAxis('bottom')
            if isinstance(axis, OrdinalDateAxis):
                axis.setChartData(df, period) # 주기 정보 전달

        # 빈 데이터 체크
        if df.empty:
            logger.warning("업데이트할 데이터 없음. 차트 클리어.")
            self.chart_loaded.emit(False)
            return

        try:
            # --- 1. 가격 데이터 확인 ---
            if 'ordinal' not in df.columns:
                logger.error("'ordinal' 컬럼이 없어 차트를 그릴 수 없습니다.")
                self.chart_loaded.emit(False)
                return
                
            # --- 2. 캔들스틱 또는 라인 차트 그리기 ---
            if ('Open' in df.columns and 'High' in df.columns and 
                'Low' in df.columns and 'Close' in df.columns):
                # 캔들스틱 차트 그리기
                try:
                    # CandlestickItem 생성에 직접 전달할 데이터 준비
                    data_tuples = df[['ordinal', 'Open', 'High', 'Low', 'Close']].values
                    
                    # 캔들스틱 아이템 생성 또는 업데이트
                    from .custom_graphics import CandlestickItem
                    
                    # 기존 아이템 확인
                    if 'candle' in self.data_items and isinstance(self.data_items['candle'], CandlestickItem):
                        # 기존 아이템 데이터 업데이트
                        self.data_items['candle'].setData(data_tuples)
                        # 색상 명시적 설정
                        self.data_items['candle'].setColors(
                            upColor=UP_COLOR,
                            downColor=DOWN_COLOR,
                            neutralColor=NEUTRAL_COLOR,
                            wickColor=pg.mkColor('w')
                        )
                        # 꼬리 별도 그리기 모드 설정
                        self.data_items['candle'].setSeparateWicks(True)
                        logger.debug("기존 캔들스틱 아이템 업데이트 완료")
                    else:
                        # 새 캔들스틱 아이템 생성
                        candle_item = CandlestickItem(
                            data_tuples,
                            upColor=UP_COLOR,
                            downColor=DOWN_COLOR,
                            neutralColor=NEUTRAL_COLOR,
                            wickColor=pg.mkColor('w')
                        )
                        # 꼬리 별도 그리기 모드 설정
                        candle_item.setSeparateWicks(True)
                        self.plot_items['price'].addItem(candle_item)
                        self.data_items['candle'] = candle_item
                        logger.debug(f"새 캔들스틱 아이템 생성 완료: {len(data_tuples)}개")
                        
                except Exception as e:
                    logger.error(f"캔들스틱 차트 생성 오류: {e}", exc_info=True)
                    # 오류 시 라인 차트로 대체 (종가만 표시)
                    if 'Close' in df.columns:
                        self._create_line_chart(df)
                        
            elif 'Close' in df.columns:
                # 종가만 있는 경우 라인 차트 생성
                self._create_line_chart(df)
            else:
                logger.warning("차트 그리기에 필요한 가격 데이터 컬럼이 없습니다.")
                
            # --- 3. 거래량 차트 그리기 ---
            if 'Volume' in df.columns:
                self._create_volume_chart(df)
                
            # --- 4. 거래대금 차트 그리기 ---
            if 'TradingValue' in df.columns:
                self._create_trading_value_chart(df)
                
            # --- 5. 보조지표 그리기 (필요시) ---
            self._redraw_visible_indicators()
            
            # --- 6. 초기 범위 조정 ---
            # 전체 데이터 표시
            self.plot_items['price'].autoRange()
            
            # Y축 범위 동적 조절 적용
            self._adjust_yrange_for_visible_data()
            
            # --- 7. 상호작용 설정 활성화 ---
            # 크로스헤어 및 툴팁 활성화는 이미 _setup_interactions에서 되어 있음
            
            logger.info(f"{stock_code} 차트 그리기 완료")
            self.chart_loaded.emit(True)

        except Exception as e:
            logger.error(f"차트 그리기 중 오류: {e}", exc_info=True)
            self.chart_loaded.emit(False)
            
    def _create_line_chart(self, df):
        """종가 기반 라인 차트 생성"""
        try:
            closes = df['Close'].values
            ordinals = df['ordinal'].values
            
            # 유효성 검사
            if len(ordinals) == 0 or len(closes) == 0:
                logger.warning("라인 차트를 그릴 데이터가 없습니다.")
                return
                
            # 라인 차트 생성
            pen = pg.mkPen(Colors.CHART_FOREGROUND, width=1.5)
            line_item = pg.PlotCurveItem(
                x=ordinals,
                y=closes,
                pen=pen,
                connect='finite'  # NaN 값 연결하지 않음
            )
            
            self.plot_items['price'].addItem(line_item)
            self.data_items['price_line'] = line_item
            logger.debug(f"라인 차트 생성 완료: {len(ordinals)}개 데이터")
            
        except Exception as e:
            logger.error(f"라인 차트 생성 오류: {e}", exc_info=True)
            
    def _create_volume_chart(self, df):
        """거래량 차트 생성"""
        try:
            volumes = df['Volume'].values
            ordinals = df['ordinal'].values
            
            # 거래량 색상 설정 (캔들 색상 기준)
            if 'Open' in df.columns and 'Close' in df.columns:
                # 상승/하락 구분
                opens = df['Open'].values
                closes = df['Close'].values
                brushes = [pg.mkBrush(UP_COLOR if c >= o else DOWN_COLOR) 
                          for o, c in zip(opens, closes)]
            else:
                # 기본 색상 사용
                brushes = pg.mkBrush(Colors.VOLUME_DEFAULT)
                
            # 거래량 막대 생성
            bar_width = 0.6  # 캔들과 동일 너비
            volume_item = BarGraphItem(
                x=ordinals,
                height=volumes,
                width=bar_width,
                brushes=brushes
            )
            
            self.plot_items['volume'].addItem(volume_item)
            self.data_items['volume'] = volume_item
            
            # 거래량 차트 Y축 레이블 설정
            self.plot_items['volume'].setLabel('left', '거래량')
            logger.debug("거래량 차트 생성 완료")
            
        except Exception as e:
            logger.error(f"거래량 차트 생성 오류: {e}", exc_info=True)
            
    def _create_trading_value_chart(self, df):
        """거래대금 차트 생성"""
        try:
            # 문자열 가능성 고려하여 숫자 변환
            numeric_values = pd.to_numeric(df['TradingValue'], errors='coerce')
            values = np.array(numeric_values)
            ordinals = df['ordinal'].values
            
            # 유효한 데이터 필터링
            valid_indices = np.isfinite(values)
            valid_values = values[valid_indices]
            valid_ordinals = ordinals[valid_indices]
            
            if len(valid_ordinals) == 0:
                logger.warning("유효한 거래대금 데이터가 없습니다.")
                return
                
            # 거래대금 라인 생성
            pen = pg.mkPen(Colors.TRADING_VALUE, width=1.5)
            value_item = pg.PlotCurveItem(
                x=valid_ordinals,
                y=valid_values,
                pen=pen
            )
            
            self.plot_items['value'].addItem(value_item)
            self.data_items['value'] = value_item
            
            # 거래대금 차트 Y축 레이블 설정
            self.plot_items['value'].setLabel('left', '거래대금')
            logger.debug("거래대금 차트 생성 완료")
            
        except Exception as e:
            logger.error(f"거래대금 차트 생성 오류: {e}", exc_info=True)

    def clear_chart(self):
        """차트의 모든 아이템 제거"""
        self.clear_chart_items()
        self.chart_data = pd.DataFrame()
        logger.debug("차트 클리어 완료")
        
    def clear_chart_items(self):
        """차트에서 데이터 아이템만 제거"""
        # self.plot_items 딕셔너리의 값들을 순회
        for plot in self.plot_items.values():
            # --- 수정 시작 ---
            # plot 객체가 PlotItem 인스턴스인지 확인
            if isinstance(plot, pg.PlotItem):
                items_to_remove = [item for item in plot.items if isinstance(item, (CandlestickItem, BarGraphItem, pg.PlotCurveItem))]
                for item in items_to_remove:
                    plot.removeItem(item)
            # --- 수정 끝 ---
        self.data_items.clear()

        # self.indicator_plots 딕셔너리의 값들을 순회
        for plot in self.indicator_plots.values():
             # 여기서도 plot이 PlotItem이 아닌 ViewBox 객체일 수 있음 (이 부분은 이미 PlotItem만 저장되므로 안전할 수 있으나, 일관성을 위해 추가 고려 가능)
             # --- 수정 시작 (일관성 및 안정성 강화) ---
             if isinstance(plot, pg.PlotItem):
                 items_to_remove = list(plot.items)
                 for item in items_to_remove:
                     if isinstance(item, pg.PlotCurveItem): # 추가된 보조지표 커브만 제거
                          plot.removeItem(item)
             # --- 수정 끝 ---
        self.indicator_items.clear()

    def cleanup(self):
        """컴포넌트 정리"""
        logger.info(f"ChartComponent 정리 시작: {self.current_stock_code}")
        
        # 크로스헤어 연결 해제
        try:
            # 직접 연결 해제
            if 'price' in self.plot_items:
                scene = self.plot_items['price'].scene()
                if scene:
                    scene.sigMouseMoved.disconnect(self._on_mouse_moved)
        except Exception as e:
            logger.warning(f"직접 연결 해제 오류: {e}")
            
        # 시그널 프록시 연결 해제
        if self.proxy:
            try:
                self.proxy.disconnect()
            except Exception as e:
                logger.warning(f"프록시 연결 해제 오류: {e}")
            self.proxy = None
            
        # 플롯 아이템 정리
        for key in list(self.plot_items.keys()):
            plot = self.plot_items.get(key)
            if plot:
                try:
                    # 캔들스틱 등 아이템 제거
                    for item in list(plot.items):
                        plot.removeItem(item)
                except Exception as e:
                    logger.warning(f"플롯 아이템 제거 오류: {e}")
                    
        logger.info(f"ChartComponent 정리 완료: {self.current_stock_code}")

    @pyqtSlot(str, dict)
    def update_latest_data(self, stock_code: str, data: dict):
        """실시간 데이터 수신 시 내부 변수 업데이트 (차트에 직접 그리지 않음)"""
        # 종목코드 확인
        if stock_code != self.current_stock_code:
            return
            
        try:
            # 데이터 유효성 확인
            timestamp = data.get('time')
            price = data.get('price')
            
            if timestamp is None or price is None:
                logger.warning(f"실시간 데이터 필수 필드(time, price) 누락: {data}")
                return
                
            # 최신 데이터 저장
            self.latest_tick_data = data
            logger.debug(f"실시간 데이터 업데이트: {stock_code}, 가격={price:,.0f}")
            
            # 현재 마우스 위치 기준으로 툴팁 강제 업데이트 (선택적)
            if self.proxy and hasattr(self.proxy, 'lastState'):
                last_pos = self.proxy.lastState
                if last_pos:
                    # 현재 마우스 위치에서 툴팁 업데이트 재실행
                    self._mouse_moved([last_pos])
                    
        except Exception as e:
            logger.error(f"실시간 데이터 업데이트 중 오류: {e}", exc_info=True)

    def connectAxisSignals(self):
        """축 신호 연결 설정"""
        # X축 변경 시 Y축 자동 조절 연결
        try:
            if 'price' in self.plot_items:
                vb = self.plot_items['price'].getViewBox()
                # SignalProxy를 활용하여 이벤트 제한 (성능 향상)
                self.range_change_proxy = pg.SignalProxy(
                    vb.sigXRangeChanged, 
                    rateLimit=30,  # 30Hz 제한
                    slot=self._on_xrange_changed
                )
                logger.debug("X축 범위 변경 신호 연결 완료")
        except Exception as e:
            logger.error(f"축 신호 연결 오류: {e}")

    def _on_xrange_changed(self, event):
        """X축 범위 변경 시 호출 (SignalProxy 사용)"""
        # SignalProxy를 통해 호출됨
        self._adjust_yrange_for_visible_data()

    def _adjust_yrange_for_visible_data(self):
        """X축 범위 변경 시 Y축 범위 자동 조절"""
        if not hasattr(self, 'chart_data') or self.chart_data.empty:
            return

        try:
            # 현재 보이는 영역 계산
            price_plot = self.plot_items['price']
            visible_x_range = price_plot.vb.viewRange()[0]
            x_min, x_max = visible_x_range[0], visible_x_range[1]

            # 보이는 데이터 인덱스 범위 계산
            start_idx = max(0, int(np.floor(x_min)))
            end_idx = min(len(self.chart_data) - 1, int(np.ceil(x_max)))

            if start_idx > end_idx or end_idx < 0:
                return  # 유효한 범위 없음

            # 보이는 영역의 데이터 추출
            visible_data = self.chart_data.iloc[start_idx:end_idx + 1]
            
            if visible_data.empty:
                return  # 데이터 없음

            # 1. 가격 차트 Y축 조절
            min_price = None
            max_price = None
            
            # 캔들 차트일 경우 고가/저가 사용
            if 'Low' in visible_data.columns and 'High' in visible_data.columns:
                min_price = visible_data['Low'].min(skipna=True)
                max_price = visible_data['High'].max(skipna=True)
            # 선 차트일 경우 종가만 사용
            elif 'Close' in visible_data.columns:
                min_price = visible_data['Close'].min(skipna=True)
                max_price = visible_data['Close'].max(skipna=True)
            
            # 범위 유효성 검사
            if pd.notna(min_price) and pd.notna(max_price) and max_price > min_price:
                # 데이터 범위에 여백 추가 (가독성 향상)
                price_range = max_price - min_price
                if price_range <= 0:  # 모든 값이 같은 경우
                    price_range = max_price * 0.1
                    
                # 패딩 비율 (데이터 범위의 %)
                padding_ratio = 0.05
                
                # 최소 패딩 값 (고정 여백)
                min_padding = 1.0
                
                # 패딩 계산 (상대적 여백과 최소 여백 중 큰 값 사용)
                padding = max(price_range * padding_ratio, min_padding)
                
                y_min = min_price - padding
                y_max = max_price + padding
                
                # 0 미만으로 내려가지 않도록 조정 (선택적)
                # if y_min < 0:
                #     y_min = 0
                
                # Y축 범위 설정 (부드러운 애니메이션 적용)
                price_plot.setYRange(y_min, y_max, padding=0)
                logger.debug(f"가격 차트 Y축 조절: {y_min:.1f} ~ {y_max:.1f}")

            # 2. 거래량 차트 Y축 조절
            if 'volume' in self.plot_items and 'Volume' in visible_data.columns:
                volume_plot = self.plot_items['volume']
                max_volume = visible_data['Volume'].max(skipna=True)
                
                if pd.notna(max_volume):
                    if max_volume > 0:
                        # 여백 추가 (위쪽만)
                        volume_plot.setYRange(0, max_volume * 1.1, padding=0)
                        logger.debug(f"거래량 차트 Y축 조절: 0 ~ {max_volume * 1.1:.0f}")
                    else:
                        # 거래량이 0인 경우
                        volume_plot.setYRange(0, 1, padding=0)

            # 3. 거래대금 차트 Y축 조절
            if 'value' in self.plot_items and 'TradingValue' in visible_data.columns:
                value_plot = self.plot_items['value']
                # 문자열일 수 있으므로 숫자로 변환
                numeric_values = pd.to_numeric(visible_data['TradingValue'], errors='coerce')
                max_value = numeric_values.max(skipna=True)
                
                if pd.notna(max_value):
                    if max_value > 0:
                        # 여백 추가 (위쪽만)
                        value_plot.setYRange(0, max_value * 1.1, padding=0)
                        logger.debug(f"거래대금 차트 Y축 조절: 0 ~ {max_value * 1.1:.0f}")
                    else:
                        # 거래대금이 0인 경우
                        value_plot.setYRange(0, 1, padding=0)
                        
            # 4. 보조지표 차트 Y축 조절 (선택적)
            for key, plot in self.indicator_plots.items():
                if plot.isVisible():
                    self._adjust_indicator_yrange(key, visible_data)

        except Exception as e:
            logger.error(f"Y축 범위 조절 오류: {e}", exc_info=True)
            
    def _adjust_indicator_yrange(self, indicator_key, visible_data):
        """특정 보조지표의 Y축 범위 자동 조절"""
        try:
            if indicator_key not in self.indicator_plots:
                return
                
            plot = self.indicator_plots[indicator_key]
            
            # 보조지표별 컬럼 패턴 및 처리
            if indicator_key == 'RSI':
                # RSI는 0-100 고정 범위
                plot.setYRange(0, 100, padding=0)
                # 기준선 추가 (30, 70)
                self._ensure_reference_lines(plot, [30, 70])
                
            elif indicator_key == 'MACD':
                # MACD 관련 컬럼 찾기
                macd_cols = [c for c in visible_data.columns if c.startswith('MACD')]
                if not macd_cols:
                    return
                    
                # MACD 값 범위 계산
                macd_min, macd_max = float('inf'), float('-inf')
                for col in macd_cols:
                    if col in visible_data:
                        col_min = visible_data[col].min(skipna=True)
                        col_max = visible_data[col].max(skipna=True)
                        if pd.notna(col_min) and pd.notna(col_max):
                            macd_min = min(macd_min, col_min)
                            macd_max = max(macd_max, col_max)
                
                if macd_min != float('inf') and macd_max != float('-inf'):
                    # 범위가 너무 작은 경우 확장
                    if abs(macd_max - macd_min) < 0.1:
                        center = (macd_max + macd_min) / 2
                        macd_min = center - 0.5
                        macd_max = center + 0.5
                    
                    # 여백 추가
                    range_size = macd_max - macd_min
                    padding = range_size * 0.1
                    plot.setYRange(macd_min - padding, macd_max + padding, padding=0)
                    
                    # 기준선 추가 (0)
                    self._ensure_reference_lines(plot, [0])
        
        except Exception as e:
            logger.error(f"{indicator_key} Y축 범위 조절 오류: {e}")
            
    def _ensure_reference_lines(self, plot, values, style=None):
        """보조지표 차트에 기준선 추가 (없으면 생성, 있으면 위치만 업데이트)"""
        if not hasattr(plot, 'reference_lines'):
            plot.reference_lines = {}
            
        # 기본 스타일 정의
        if style is None:
            style = {'color': '#888888', 'width': 1, 'style': Qt.DashLine}
            
        # 각 기준값에 대해 선 추가/업데이트
        for value in values:
            if value not in plot.reference_lines:
                # 새 기준선 생성
                pen = pg.mkPen(color=style['color'], width=style['width'], style=style['style'])
                line = pg.InfiniteLine(pos=value, angle=0, pen=pen, movable=False)
                plot.addItem(line)
                plot.reference_lines[value] = line

    def _add_candle_item(self, data: pd.DataFrame):
        """캔들스틱 아이템 생성 및 추가"""
        try:
            # 데이터 셋업
            data_array = np.array([
                data['ordinal'].values,  # 순서 (x축)
                data['Open'].values,     # 시가
                data['High'].values,     # 고가
                data['Low'].values,      # 저가
                data['Close'].values,    # 종가
            ]).T  # 행렬 전치
            
            # 이미 존재하는 캔들 아이템이 있는지 확인
            if 'candle' in self.data_items and self.data_items['candle'] is not None:
                candle_item = self.data_items['candle']
                # 기존 아이템에 데이터 업데이트
                candle_item.setData(data_array)
                # 색상 업데이트 메서드 호출
                candle_item.setColors(upColor=UP_COLOR, downColor=DOWN_COLOR, neutralColor=NEUTRAL_COLOR)
                logger.debug("기존 CandlestickItem 데이터 및 색상 업데이트 완료")
            else:
                from .custom_graphics import CandlestickItem
                # 생성 시 색상 전달 
                candle_item = CandlestickItem(
                    data_array,
                    upColor=UP_COLOR,
                    downColor=DOWN_COLOR,
                    neutralColor=NEUTRAL_COLOR,
                    wickColor=pg.mkColor('w')  # 캔들 꼬리 색상은 흰색
                )
                self.plot_items['price'].addItem(candle_item)
                self.data_items['candle'] = candle_item
                logger.debug(f"새 CandlestickItem 추가 완료 (색상 적용): {len(data)}개")
                
            return candle_item
            
        except Exception as e:
            logger.exception(f"캔들스틱 차트 생성 오류: {e}")
            return None

    def _redraw_visible_indicators(self):
         """체크된 보조지표 다시 그리기 (순서축 기반)"""
         if self.chart_data.empty or 'ordinal' not in self.chart_data.columns:
              return
         
         # 기존 아이템 제거 (개선 필요 - 부분 업데이트 방식 고려)
         for plot in self.indicator_plots.values():
             items_to_remove = [item for item in plot.items if isinstance(item, (pg.PlotCurveItem, BarGraphItem))]
             for item in items_to_remove:
                 plot.removeItem(item)
         self.indicator_items.clear()
                 
         # 보이는 지표 다시 그리기
         # if hasattr(self, 'indicator_checkboxes'): # 체크박스 참조 방식 유지 시
         #     for code, checkbox in self.indicator_checkboxes.items():
         #         if checkbox.isChecked():
         #             self.toggle_indicator(code, True) # 토글 함수 내부에서 ordinal 사용 필요
         # 또는
         # 저장된 설정 등을 기반으로 직접 그리기 함수 호출
         self._plot_visible_indicators_from_config() # 예시 함수명

    def _plot_visible_indicators_from_config(self):
        """저장된 설정이나 체크박스 상태에 따라 보조지표 그리기 (순서축 사용)"""
        # 상위 윈도우의 체크박스 상태 확인
        parent = self.parent()
        if hasattr(parent, 'indicator_checkboxes'):
            checkboxes = parent.indicator_checkboxes
            for key, checkbox in checkboxes.items():
                if checkbox.isChecked():
                    self._plot_indicator_group(key)
        
    def is_indicator_visible(self, key):
        """지표 표시 여부 확인"""
        parent = self.parent()
        if hasattr(parent, 'indicator_checkboxes') and key in parent.indicator_checkboxes:
            return parent.indicator_checkboxes[key].isChecked()
        return False

    def _plot_indicator_group(self, indicator_key):
        """주어진 키에 해당하는 보조지표 그룹 그리기"""
        if self.chart_data.empty:
            return
            
        plot_key = 'price'  # 기본값 (가격 차트에 표시)
        target_cols = []
        colors = []
        plot_config = {}
        
        # 지표별 설정
        if indicator_key == 'MA':
            plot_key = 'price'
            # 이동평균선 관련 컬럼 찾기 (SMA, EMA)
            sma_cols = [c for c in self.chart_data.columns if c.startswith('SMA_')]
            ema_cols = [c for c in self.chart_data.columns if c.startswith('EMA_')]
            
            # 일봉 이동평균선 컬럼 필터링 및 정렬 (주기별)
            target_cols = []
            
            # SMA 추가 (주기별 색상 구분)
            if sma_cols:
                periods = sorted([int(c.split('_')[1]) for c in sma_cols])
                sma_colors = {
                    5: Colors.SMA_5,     # 5일선: 파란색
                    10: Colors.SMA_10,   # 10일선: 녹색
                    20: Colors.SMA_20,   # 20일선: 빨간색
                    60: Colors.SMA_60,   # 60일선: 보라색
                    120: Colors.SMA_120, # 120일선: 갈색
                    240: Colors.SMA_240  # 240일선: 검정색
                }
                
                for period in periods:
                    col = f'SMA_{period}'
                    if col in self.chart_data.columns:
                        target_cols.append(col)
                        # 해당 주기 색상 사용 또는 기본 색상
                        colors.append(sma_colors.get(period, Colors.CHART_FOREGROUND))
                    
            # EMA 추가 (점선으로 표시)
            if ema_cols:
                periods = sorted([int(c.split('_')[1]) for c in ema_cols])
                ema_colors = {
                    5: Colors.EMA_5,    # 5일선: 파란색
                    10: Colors.EMA_10,  # 10일선: 녹색
                    20: Colors.EMA_20,  # 20일선: 빨간색
                    60: Colors.EMA_60,  # 60일선: 보라색
                    120: Colors.EMA_120 # 120일선: 갈색
                }
                
                for period in periods:
                    col = f'EMA_{period}'
                    if col in self.chart_data.columns:
                        target_cols.append(col)
                        # 해당 주기 색상 사용 또는 기본 색상
                        colors.append(ema_colors.get(period, Colors.CHART_FOREGROUND))
                
                # EMA 경우 점선 사용을 위한 추가 설정
                plot_config['dash_pattern'] = {
                    col: [4, 4] for col in ema_cols if col in self.chart_data.columns
                }
                        
        elif indicator_key == 'BB':
            plot_key = 'price'
            # 볼린저밴드 기본 설정 (20, 2)
            bb_length, bb_std = 20, 2.0
            
            # 볼린저밴드 상하단 및 중심선
            lower_band = f'BBL_{bb_length}_{bb_std}'
            middle_band = f'BBM_{bb_length}_{bb_std}'
            upper_band = f'BBU_{bb_length}_{bb_std}'
            
            # 모든 필요 컬럼이 있는지 확인
            if all(col in self.chart_data.columns for col in [lower_band, middle_band, upper_band]):
                target_cols = [lower_band, middle_band, upper_band]
                colors = [
                    Colors.BOLLINGER_LOWER,  # 하단밴드: 파란색
                    Colors.BOLLINGER_MID,    # 중심선: 검정색
                    Colors.BOLLINGER_UPPER   # 상단밴드: 빨간색
                ]
                
                # 볼린저밴드 채우기 설정
                plot_config['fill_between'] = (lower_band, upper_band)
                plot_config['fill_brush'] = pg.mkBrush(Colors.BOLLINGER_FILL)
                
                # 볼린저밴드 상하단 스타일 (점선)
                plot_config['dash_pattern'] = {
                    lower_band: [4, 4],
                    upper_band: [4, 4]
                }
            
        elif indicator_key == 'RSI':
            plot_key = 'RSI'
            # RSI 표시 및 설정
            rsi_cols = [c for c in self.chart_data.columns if c.startswith('RSI_')]
            if rsi_cols:
                target_cols = rsi_cols
                colors = [Colors.RSI for _ in rsi_cols]  # RSI: 파란색
                
                # RSI 플롯 보이기
                self.indicator_plots['RSI'].show()
                
                # RSI 참조선 추가 (30, 70)
                self._ensure_reference_lines(self.indicator_plots['RSI'], [30, 70], {
                    'color': Colors.REFERENCE_LINE,
                    'width': 1,
                    'style': Qt.DashLine
                })
                
                # RSI 플롯에 Y축 범위 고정 (0-100)
                self.indicator_plots['RSI'].setYRange(0, 100, padding=0)
                
                # RSI 플롯에 레이블 추가
                self.indicator_plots['RSI'].setLabel('left', 'RSI')
                
                # RSI 주요 눈금 추가
                rsi_axis = self.indicator_plots['RSI'].getAxis('left')
                rsi_axis.setTicks([[(0, '0'), (30, '30'), (50, '50'), (70, '70'), (100, '100')]])
            
        elif indicator_key == 'MACD':
            plot_key = 'MACD'
            # MACD 표시 및 설정
            macd_base_cols = [c for c in self.chart_data.columns if c.startswith('MACD_') and not c.startswith(('MACDh_', 'MACDs_'))]
            macd_signal_cols = [c for c in self.chart_data.columns if c.startswith('MACDs_')]
            macd_hist_cols = [c for c in self.chart_data.columns if c.startswith('MACDh_')]
            
            # MACD 선과 시그널 라인 표시
            if macd_base_cols and macd_signal_cols:
                target_cols = macd_base_cols + macd_signal_cols
                colors = [Colors.MACD_LINE for _ in macd_base_cols] + [Colors.MACD_SIGNAL for _ in macd_signal_cols]
                
                # MACD 플롯 보이기
                self.indicator_plots['MACD'].show()
                
                # MACD 플롯에 레이블 추가
                self.indicator_plots['MACD'].setLabel('left', 'MACD')
                
                # MACD 플롯에 참조선 추가 (0)
                self._ensure_reference_lines(self.indicator_plots['MACD'], [0], {
                    'color': Colors.REFERENCE_LINE,
                    'width': 1,
                    'style': Qt.SolidLine
                })
                
                # MACD 히스토그램 추가 (별도 처리)
                if macd_hist_cols:
                    plot_config['macd_hist'] = macd_hist_cols[0]
            
        # 개별 커브 그리기
        for i, col in enumerate(target_cols):
            if col in self.chart_data.columns:
                # 색상 사용
                color = colors[i % len(colors)]
                
                # 대시 패턴 적용
                dash_pattern = None
                if 'dash_pattern' in plot_config and col in plot_config['dash_pattern']:
                    dash_pattern = plot_config['dash_pattern'][col]
                
                # 채우기 설정 확인
                fill_item_b = None
                fill_brush = None
                if 'fill_between' in plot_config and col == plot_config['fill_between'][0]:
                    upper_col = plot_config['fill_between'][1]
                    if upper_col in self.chart_data.columns:
                        # 채우기 라인은 나중에 그려질 upper_col을 참조함
                        # 먼저 upper_col을 그리고 나서 로직 수정 필요
                        fill_item_b = self._plot_indicator(upper_col, plot_key, colors[target_cols.index(upper_col)])
                        fill_brush = plot_config.get('fill_brush')
                
                # 지표선 그리기
                self._plot_indicator(col, plot_key, color, 
                                   dash_pattern=dash_pattern,
                                   fillLevelItem=fill_item_b, 
                                   fillBrush=fill_brush)
        
        # MACD 히스토그램 별도 처리
        if 'macd_hist' in plot_config:
            hist_col = plot_config['macd_hist']
            if hist_col in self.chart_data.columns:
                self._plot_macd_histogram(hist_col, 'MACD')

    def _plot_indicator(self, column_name, plot_key, color, 
                      dash_pattern=None, fillLevelItem=None, fillBrush=None, width=1.5):
        """지표선 그리기"""
        try:
            # 데이터 확인
            if column_name not in self.chart_data.columns or self.chart_data.empty:
                logger.warning(f"컬럼 '{column_name}'이 차트 데이터에 없거나 데이터가 비어 있습니다.")
                return None
                
            # 플롯 아이템 확인
            if plot_key not in self.plot_items and plot_key not in self.indicator_plots:
                logger.warning(f"플롯 키 '{plot_key}'가 유효하지 않습니다.")
                return None
                
            # 대상 플롯 아이템 가져오기
            plot_item = self.plot_items.get(plot_key) or self.indicator_plots.get(plot_key)
            if not plot_item:
                return None
                
            # 데이터 준비 (유효한 값만)
            y_values = self.chart_data[column_name].values
            x_values = self.chart_data['ordinal'].values
            
            # 펜 설정
            pen = pg.mkPen(color=color, width=width)
            if dash_pattern:
                pen.setDashPattern(dash_pattern)
                
            # 커브 아이템 생성
            curve_item = pg.PlotCurveItem(
                x=x_values,
                y=y_values,
                pen=pen,
                name=column_name
            )
            
            # 채우기 설정
            if fillLevelItem is not None and fillBrush is not None:
                # 여기서 fillLevelItem은 이미 그려진 curve_item이어야 함
                # 채우기 영역 추가
                fill_item = pg.FillBetweenItem(
                    curve1=curve_item,
                    curve2=fillLevelItem,
                    brush=fillBrush
                )
                plot_item.addItem(fill_item)
                self.indicator_items[f'fill_{column_name}'] = fill_item
            
            # 커브 추가
            plot_item.addItem(curve_item)
            self.indicator_items[column_name] = curve_item
            
            return curve_item
            
        except Exception as e:
            logger.error(f"지표선 '{column_name}' 그리기 오류: {e}", exc_info=True)
            return None
            
    def _plot_macd_histogram(self, hist_column, plot_key='MACD'):
        """MACD 히스토그램 그리기"""
        try:
            # 데이터 확인
            if hist_column not in self.chart_data.columns or self.chart_data.empty:
                return
                
            # 플롯 확인
            if plot_key not in self.indicator_plots:
                return
                
            plot_item = self.indicator_plots[plot_key]
            
            # 데이터 준비
            y_values = self.chart_data[hist_column].values
            x_values = self.chart_data['ordinal'].values
            
            # 양/음수 구분
            positive_mask = y_values >= 0
            negative_mask = y_values < 0
            
            # 양수 히스토그램 (빨간색)
            if np.any(positive_mask):
                # 양수 부분만 추출
                pos_x = x_values[positive_mask]
                pos_y = y_values[positive_mask]
                
                # 막대 폭 계산 (0.6이 적절)
                width = 0.6
                
                # 히스토그램용 막대 아이템 생성
                pos_bar = pg.BarGraphItem(
                    x=pos_x,
                    height=pos_y,
                    width=width,
                    brush=pg.mkBrush(Colors.MACD_HIST_POS)
                )
                plot_item.addItem(pos_bar)
                self.indicator_items[f'{hist_column}_pos'] = pos_bar
            
            # 음수 히스토그램 (파란색)
            if np.any(negative_mask):
                # 음수 부분만 추출
                neg_x = x_values[negative_mask]
                neg_y = y_values[negative_mask]
                
                # 막대 폭 계산
                width = 0.6
                
                # 히스토그램용 막대 아이템 생성
                neg_bar = pg.BarGraphItem(
                    x=neg_x,
                    height=neg_y,
                    width=width,
                    brush=pg.mkBrush(Colors.MACD_HIST_NEG)
                )
                plot_item.addItem(neg_bar)
                self.indicator_items[f'{hist_column}_neg'] = neg_bar
                
        except Exception as e:
            logger.error(f"MACD 히스토그램 그리기 오류: {e}", exc_info=True)
            
    def toggle_indicator(self, key, state):
        """보조지표 표시/숨김 토글"""
        if key in INDICATOR_MAP:
            # 상태에 따라 지표 표시/숨김
            if state:
                # 보조지표 그리기
                self._plot_indicator_group(key)
                
                # 특수 지표는 플롯도 표시 전환
                if key in ['RSI', 'MACD']:
                    if key in self.indicator_plots:
                        self.indicator_plots[key].show()
            else:
                # 지표 숨기기
                items_to_remove = []
                
                # 지표 유형별 처리
                if key == 'MA':
                    # 이동평균선 관련 항목 찾기
                    patterns = ['SMA_', 'EMA_']
                    items_to_remove = [k for k in self.indicator_items.keys() 
                                     if any(k.startswith(p) for p in patterns)]
                elif key == 'BB':
                    # 볼린저밴드 관련 항목 찾기
                    patterns = ['BBL_', 'BBM_', 'BBU_', 'fill_BBL_']
                    items_to_remove = [k for k in self.indicator_items.keys() 
                                     if any(k.startswith(p) for p in patterns)]
                elif key == 'RSI':
                    # RSI 관련 항목 찾기
                    patterns = ['RSI_']
                    items_to_remove = [k for k in self.indicator_items.keys() 
                                     if any(k.startswith(p) for p in patterns)]
                    # RSI 플롯 숨기기
                    if 'RSI' in self.indicator_plots:
                        self.indicator_plots['RSI'].hide()
                elif key == 'MACD':
                    # MACD 관련 항목 찾기
                    patterns = ['MACD_', 'MACDs_', 'MACDh_']
                    items_to_remove = [k for k in self.indicator_items.keys() 
                                     if any(k.startswith(p) for p in patterns)]
                    # MACD 플롯 숨기기
                    if 'MACD' in self.indicator_plots:
                        self.indicator_plots['MACD'].hide()
                elif key == 'Volume':
                    # 거래량 차트 표시/숨김
                    if 'volume' in self.plot_items:
                        self.plot_items['volume'].setVisible(state)
                elif key == 'TradingValue':
                    # 거래대금 차트 표시/숨김
                    if 'value' in self.plot_items:
                        self.plot_items['value'].setVisible(state)
                
                # 지표 아이템 제거
                for k in items_to_remove:
                    if k in self.indicator_items:
                        item = self.indicator_items[k]
                        
                        # 어느 플롯에 속해있는지 확인 후 제거
                        for plot in list(self.plot_items.values()) + list(self.indicator_plots.values()):
                            if item in plot.items:
                                plot.removeItem(item)
                                break
                                
                        # 아이템 목록에서도 제거
                        del self.indicator_items[k]
            
            # Y축 범위 재조정
            self._adjust_yrange_for_visible_data()

    # ... (cleanup, _on_xrange_changed) ...
    # ... (toggle_indicator) ...
    # ... (_plot_macd_histogram) ...
    # ... (_plot_indicator) ...
    # ... (_plot_visible_indicators_from_config) ...
    # ... (is_indicator_visible) ...
    # ... (_plot_indicator_group) ...
    # ... (cleanup) ... 