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
from .custom_axis import DateAxis, PriceAxis # 커스텀 축 임포트 (필요시 재생성)
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

class ChartComponent(QWidget):
    """pyqtgraph를 이용한 차트 표시 컴포넌트"""

    # 시그널 정의 (필요에 따라 추가)
    # crosshair_moved = pyqtSignal(float, float) # 마우스 위치 시그널 (x: timestamp, y: price)
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
        self._connect_internal_signals()

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
        self.date_axis = DateAxis(orientation='bottom')
        self.price_axis = PriceAxis(orientation='left')
        price_plot = self.win.addPlot(
            row=0, col=0, 
            axisItems={'bottom': self.date_axis, 'left': self.price_axis}
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
        # --- 수정 시작: 거래량 Y축에 PriceAxis 적용 ---
        volume_axis = PriceAxis(orientation='left')
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
        value_axis = PriceAxis(orientation='left') # 왼쪽 Y축 사용
        value_plot.setAxisItems({'left': value_axis})
        value_plot.getAxis('left').setWidth(self.price_axis.width()) # Y축 너비 맞춤
        value_plot.enableAutoRange(axis=pg.ViewBox.YAxis, enable=True)
        value_plot.setLabel('left', '거래대금') # Y축 라벨 설정
        self.plot_items['value'] = value_plot # PlotItem으로 저장
        # self.value_axis = value_axis # PriceAxis 참조 저장 (필요시)
        # value_plot.hide() # 기본 숨김 여부? -> 일단 보이도록

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

        # X Range 변경 시그널 연결
        price_plot.sigXRangeChanged.connect(self._on_xrange_changed)

        logger.info("차트 Plot Item 초기화 완료")

    def _setup_interactions(self):
        """차트 인터랙션 (크로스헤어, 줌/팬 등) 설정"""
        # 1. 크로스헤어 설정
        pen = pg.mkPen(color=Colors.CROSSHAIR, style=Qt.DashLine)
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pen)
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pen)
        self.plot_items['price'].addItem(self.v_line, ignoreBounds=True)
        self.plot_items['price'].addItem(self.h_line, ignoreBounds=True)
        # 가격 라벨 포맷 변경 (".0f" -> ",.0f" 로 천단위 구분자 추가)
        self.crosshair_labels['price'] = pg.InfLineLabel(self.h_line, text="{value:,.0f}", position=0.95, color=Colors.TOOLTIP_TEXT)
        self.crosshair_labels['time'] = pg.InfLineLabel(self.v_line, text="{value}", position=0.95, color=Colors.TOOLTIP_TEXT, angle=90)
        self.v_line.hide()
        self.h_line.hide()

        # 마우스 이동 시그널 프록시 설정
        self.proxy = pg.SignalProxy(self.plot_items['price'].scene().sigMouseMoved, rateLimit=60, slot=self._mouse_moved)
        
        logger.info("ChartComponent 인터랙션 설정 완료.")

    def _connect_internal_signals(self):
        """컴포넌트 내부 시그널 연결"""
        # 마우스 이동 시 크로스헤어/툴팁 업데이트
        self.proxy = pg.SignalProxy(self.plot_items['price'].scene().sigMouseMoved, rateLimit=60, slot=self._mouse_moved)

    @pyqtSlot(str, str, pd.DataFrame)
    def update_chart(self, stock_code: str, period: str, df: pd.DataFrame):
        """수신된 데이터와 주기로 차트 업데이트"""
        logger.info(f"차트 업데이트 수신: {stock_code}, 주기={period}, 데이터 {len(df)}개")
        self.clear_chart_items() # 기존 아이템 제거
        self.chart_data = df
        self.current_stock_code = stock_code # 필요시 업데이트
        # self.current_period = period # ChartComponent 내부에도 주기 저장 (선택 사항)

        # DateAxis에 현재 주기 정보 설정
        self.date_axis.set_current_timeframe(period)

        if df.empty:
            logger.warning("업데이트할 데이터 없음. 차트 클리어.")
            self.chart_loaded.emit(False)
            return

        try:
            # --- 1. 가격(캔들스틱) 그리기 --- 
            if 'Open' in df.columns and 'High' in df.columns and 'Low' in df.columns and 'Close' in df.columns:
                # DatetimeIndex를 timestamp (int64 초)로 변환 (오류 수정)
                timestamps = df.index.astype('int64') // 10**9 
                # 튜플 리스트로 변환 (CandlestickItem 요구사항)
                data_tuples = [
                    (ts, row['Open'], row['High'], row['Low'], row['Close'], row['Volume'])
                    for ts, (_, row) in zip(timestamps, df.iterrows()) # 인덱스와 행 동시 순회
                ]
                if data_tuples:
                    # CandlestickItem 생성 (core/ui/components/custom_graphics.py 필요)
                    try:
                        from .custom_graphics import CandlestickItem
                        candle_item = CandlestickItem(data_tuples)
                        self.plot_items['price'].addItem(candle_item)
                        self.data_items['candle'] = candle_item
                        logger.debug(f"캔들스틱 아이템 추가 완료: {len(data_tuples)}개")
                    except ImportError:
                        logger.error("CandlestickItem을 import할 수 없습니다. custom_graphics.py 파일을 확인하세요.")
                    except Exception as ce:
                        logger.error(f"CandlestickItem 생성 또는 추가 중 오류: {ce}", exc_info=True)
                else:
                    logger.warning("캔들 데이터 튜플 변환 결과 없음")
            elif 'Close' in df.columns: # OHLC 없고 Close 컬럼만 있을 경우 (틱 데이터 등)
                logger.info("OHLC 데이터 없어 Close 가격으로 라인 차트 생성")
                timestamps = df.index.astype('int64') // 10**9
                closes = df['Close'].values.astype(float)
                if timestamps.size > 0 and closes.size > 0:
                    try:
                        line_item = pg.PlotCurveItem(x=timestamps, y=closes, pen=pg.mkPen(Colors.CHART_FOREGROUND, width=1))
                        self.plot_items['price'].addItem(line_item)
                        self.data_items['price_line'] = line_item # 키 이름 변경 (candle과 구분)
                        logger.debug(f"가격 라인 아이템 추가 완료: {len(timestamps)}개")
                    except Exception as le:
                        logger.error(f"가격 라인 생성 또는 추가 중 오류: {le}", exc_info=True)
                else:
                    logger.warning("라인 차트 데이터 없음 (timestamps 또는 closes)")
            else:
                logger.warning("차트 가격 표시에 필요한 컬럼(OHLC 또는 Close) 없음")
            
            # --- 2. 거래량 그리기 --- 
            if 'Volume' in df.columns:
                volumes = df['Volume'].values.astype(float) # float 변환 추가
                timestamps = df.index.astype('int64') // 10**9
                bar_width = self._calculate_bar_width(timestamps)

                # 틱 데이터 여부 확인
                is_tick_data = period.endswith('T')

                if is_tick_data:
                    # 틱 데이터: 단색 브러시 사용 (OHLC 없으므로)
                    brushes = pg.mkBrush(Colors.VOLUME_TICK)
                elif 'Open' in df.columns and 'Close' in df.columns:
                    # OHLC 데이터: 기존 로직 (상승/하락 구분)
                    opens = df['Open'].values.astype(float)
                    closes = df['Close'].values.astype(float)
                    brushes = [pg.mkBrush(Colors.PRICE_UP if c >= o else Colors.PRICE_DOWN) for o, c in zip(opens, closes)]
                else:
                    # OHLC 없는 비-틱 데이터 (예: API 응답 이상): 기본 브러시
                    logger.warning(f"거래량 색상 구분을 위한 Open/Close 컬럼 부족 ({stock_code}, {period}). 기본 색상 사용.")
                    brushes = pg.mkBrush(Colors.VOLUME_DEFAULT)

                volume_item = BarGraphItem(x=timestamps, height=volumes, width=bar_width, brushes=brushes)
                self.plot_items['volume'].addItem(volume_item)
                self.data_items['volume'] = volume_item
                logger.debug("거래량 아이템 추가 완료")
            else:
                 logger.warning("거래량 차트 그리기에 필요한 Volume 컬럼 없음")
                 
            # --- 3. 거래대금 그리기 --- 
            if 'TradingValue' in df.columns:
                try:
                    timestamps = df.index.astype('int64') // 10**9
                    # values가 Series일 수 있으므로 .values로 numpy 배열 얻고, float 타입으로 변환
                    values = df['TradingValue'].values.astype(float)
                    # --- 수정 시작: NaN/inf 확인 및 데이터 정제 ---
                    # NaN 또는 Inf 값이 있는지 확인
                    valid_indices = np.isfinite(timestamps) & np.isfinite(values)
                    if not np.all(valid_indices):
                        logger.warning(f"거래대금 데이터에 NaN/inf 포함. 유효한 데이터만 사용합니다. Original size: {len(timestamps)}")
                        timestamps = timestamps[valid_indices]
                        values = values[valid_indices]
                    
                    logger.debug(f"거래대금 데이터 확인 (정제 후): timestamps shape={timestamps.shape}, values shape={values.shape}, values dtype={values.dtype}, values sample={values[:5] if values.size > 5 else values}")
                    # --- 수정 끝 ---
                    if timestamps.size != values.size:
                        logger.error(f"거래대금 데이터 오류: Timestamps({timestamps.size})와 Values({values.size}) 길이가 다릅니다.")
                    elif values.ndim == 1 and values.size > 0:
                        value_item = pg.PlotCurveItem(x=timestamps, y=values, pen=pg.mkPen(Colors.TRADING_VALUE, width=1))
                        self.plot_items['value'].addItem(value_item)
                        self.data_items['value'] = value_item
                        logger.debug("거래대금 아이템 추가 완료")
                    else:
                        logger.warning(f"유효한 거래대금 데이터가 없어 그리지 않음 (shape: {values.shape})")
                except Exception as e:
                    logger.error(f"거래대금 그리기 중 오류: {e}", exc_info=True)
                    # 오류 발생 시 아이템 제거 등 후속 처리 필요할 수 있음
            else:
                 logger.warning("거래대금 차트 그리기에 필요한 TradingValue 컬럼 없음")

            # --- 보조지표 그리기 --- 
            # 보이는 지표만 다시 그림 (toggle_indicator 호출)
            self._redraw_visible_indicators()

            # X축 범위 자동 설정 (초기 로드 시)
            self.plot_items['price'].autoRange()

            # Y축 범위 업데이트 호출 (초기 설정)
            self._on_xrange_changed()

            logger.info(f"{stock_code} 차트 그리기 완료.")
            self.chart_loaded.emit(True)

        except Exception as e:
            logger.error(f"차트 그리기 중 오류: {e}", exc_info=True)
            self.chart_loaded.emit(False)
            
    @pyqtSlot(str, dict)
    def update_latest_data(self, stock_code: str, data: dict):
        """실시간 데이터 수신 시 내부 변수 업데이트 (차트에 직접 그리지 않음)"""
        if stock_code != self.current_stock_code:
            return 
        
        # 주기 체크 제거: 틱 주기가 아니더라도 최신 정보는 받아둘 수 있음 (툴팁 등 활용 대비)
        # if not self.current_period.endswith('T'):
        #     return 
        
        try:
            timestamp = data.get('time') 
            price = data.get('price')
            volume = data.get('volume')

            if timestamp is None or price is None:
                logger.warning(f"실시간 데이터 필수 필드(time, price) 누락: {data}")
                return
                
            self.latest_tick_data = data # 최신 데이터 저장
            # logger.debug(f"Latest data updated: {self.latest_tick_data}")
            
            # 실시간 데이터 수신 시 크로스헤어/툴팁 강제 업데이트 (선택적)
            # 현재 마우스 위치 기준으로 툴팁을 다시 그림
            # last_pos = getattr(self.proxy, 'lastState', None)
            # if last_pos:
            #     self._mouse_moved([last_pos])

        except Exception as e:
            logger.error(f"실시간 데이터 업데이트 중 오류: {e}", exc_info=True)

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

    def _calculate_bar_width(self, timestamps: np.ndarray) -> float:
        """타임스탬프 배열을 기반으로 적절한 막대 너비 계산"""
        if len(timestamps) > 1:
            diffs = np.diff(timestamps)
            valid_diffs = diffs[diffs > 0]
            return max(np.median(valid_diffs) * 0.8, 0.1) if len(valid_diffs) > 0 else 1
        elif len(timestamps) == 1:
             return 60 * 60 * 24 * 0.8 
        else:
             return 1

    def _mouse_moved(self, event):
        """마우스 이동 시 크로스헤어 및 툴팁 업데이트"""
        pos = event[0] 
        vb = self.plot_items['price'].vb 
        
        if self.plot_items['price'].sceneBoundingRect().contains(pos):
            mouse_point = vb.mapSceneToView(pos)
            x_pos, y_pos = mouse_point.x(), mouse_point.y()
            
            self.v_line.setPos(x_pos)
            self.h_line.setPos(y_pos)
            self.v_line.show()
            self.h_line.show()
            
            # 시간 라벨 업데이트
            time_str = self.date_axis.tickStrings([x_pos], 0, 0)
            if time_str: self.crosshair_labels['time'].setText(time_str[0])
                
            # 가격 라벨 업데이트
            # price_str = self.price_axis.tickStrings([y_pos], 0, 0) # 기존 방식
            # self.crosshair_labels['price'].setText(price_str[0]) # 기존 방식
            # 직접 포맷팅하여 천 단위 구분자 적용
            self.crosshair_labels['price'].setText(f"{y_pos:,.0f}")

            # 툴팁 업데이트 (최신 실시간 데이터 포함)
            self._update_tooltip(x_pos, mouse_point)
            self.tooltip_text.show()
        else:
            self.v_line.hide()
            self.h_line.hide()
            self.tooltip_text.hide()
        
    def _update_tooltip(self, x_pos, mouse_point):
        """해당 x 위치(타임스탬프)의 데이터를 찾아 툴팁 업데이트 (실시간 데이터 포함)"""
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
            # 1. x_pos (타임스탬프)에 가장 가까운 과거 데이터 인덱스 찾기
            target_dt = pd.Timestamp(x_pos, unit='s', tz='UTC').tz_convert('Asia/Seoul')
            # 오류 수정: get_indexer 사용
            nearest_idx_loc = self.chart_data.index.get_indexer([target_dt], method='nearest')[0]
            # 인덱스 위치가 유효한지 확인
            if nearest_idx_loc == -1: 
                raise KeyError("가장 가까운 데이터 인덱스를 찾을 수 없습니다.")
            nearest_index = self.chart_data.index[nearest_idx_loc]
            data_row = self.chart_data.iloc[nearest_idx_loc]

            # 2. 툴팁 문자열 생성 (과거 데이터 기반)
            tooltip_parts = []
            # --- 수정 시작: 주기에 따른 날짜/시간 포맷 변경 ---
            dt_str = ''
            if self.current_period == 'Y': # 연봉
                dt_str = nearest_index.strftime('%Y')
            elif self.current_period == 'M': # 월봉
                dt_str = nearest_index.strftime('%Y-%m')
            elif self.current_period == 'W': # 주봉
                # 해당 날짜가 속한 주의 시작(월요일)과 끝(일요일) 계산
                start_of_week = nearest_index - timedelta(days=nearest_index.weekday())
                end_of_week = start_of_week + timedelta(days=6)
                dt_str = f"{start_of_week.strftime('%Y-%m-%d')} ~ {end_of_week.strftime('%Y-%m-%d')}"
            elif self.current_period == 'D': # 일봉
                dt_str = nearest_index.strftime('%Y-%m-%d')
            else: # 분봉/틱봉
                dt_str = nearest_index.strftime('%Y-%m-%d %H:%M:%S')
            # --- 수정 끝 ---
            tooltip_parts.append(f"<span style='font-size: 10pt;'>{dt_str}</span>")
            
            ohlc_map = {'Open': '시', 'High': '고', 'Low': '저', 'Close': '종'}
            for col, name in ohlc_map.items():
                if col in data_row:
                    val = data_row[col]
                    color = Colors.PRICE_UP if col == 'Close' and data_row['Close'] >= data_row.get('Open', data_row['Close']) else Colors.PRICE_DOWN if col == 'Close' else Colors.CHART_FOREGROUND
                    tooltip_parts.append(f"<span style='color:{color}'>{name}: {val:,.0f}</span>")
            
            if 'Volume' in data_row:
                vol = data_row['Volume']
                tooltip_parts.append(f"거래량: {vol:,.0f}")

            # 보조지표 데이터 추가
            for code, name in INDICATOR_MAP.items():
                # --- 수정: 거래량/거래대금은 루프에서 제외 ---
                if code in ['Volume', 'TradingValue']:
                    continue 
                # --- 수정 끝 ---
                # 수정 전: if code in self.indicator_checkboxes and self.indicator_checkboxes[code].isChecked():
                # 수정 후: 체크박스 상태 대신 컬럼 존재 여부만 확인
                indicator_cols = [c for c in self.chart_data.columns if c.startswith(code)]
                if indicator_cols: # 해당 코드로 시작하는 컬럼이 하나라도 있으면
                    for col in indicator_cols:
                        if col in data_row and pd.notna(data_row[col]): # NaN 값 제외
                            val = data_row[col]
                            # 공백이나 특수문자 제거 후 float 변환 시도, 실패 시 문자열로
                            try:
                                val_str = f"{float(str(val).replace(' ','').replace(',','').replace('+','')):,.2f}"
                            except ValueError:
                                val_str = str(val)
                            # label = col.replace('_', '(') + ')' if '_' in col else col # 기존 방식
                            # indicator_key를 사용하여 INDICATOR_MAP에서 원래 이름 찾기
                            base_name = name # INDICATOR_MAP의 기본 이름 사용
                            # 컬럼 이름에서 파라미터 부분 추출 (예: SMA_20 -> (20))
                            params = col.split('_')[1:]
                            param_str = f"({','.join(params)})" if params else ""
                            label = f"{base_name}{param_str}"

                            tooltip_parts.append(f"{label}: {val_str}")

            # 3. 실시간 데이터 추가 (틱 주기일 경우)
            if self.current_period.endswith('T') and self.latest_tick_data:
                 latest_time_str = pd.to_datetime(self.latest_tick_data['time'], unit='s').strftime('%H:%M:%S')
                 latest_price = self.latest_tick_data['price']
                 tooltip_parts.append(f"<hr>실시간: {latest_time_str} <span style='font-weight:bold;'>{latest_price:,.0f}</span>")

            # 4. TextItem 업데이트
            html_text = "<br>".join(tooltip_parts)
            self.tooltip_text.setHtml(f"<div style='background-color:{Colors.TOOLTIP_BACKGROUND}; color:{Colors.TOOLTIP_TEXT}; border: 1px solid {Colors.BORDER}; padding: 5px;'>{html_text}</div>")
            self.tooltip_text.setPos(mouse_point.x(), mouse_point.y())
            # self.tooltip_text.show() # _mouse_moved에서 호출

        except KeyError:
            logger.debug(f"툴팁 데이터 조회 실패 (KeyError): {x_pos}")
            self.tooltip_text.hide()
        except Exception as e:
            logger.error(f"툴팁 업데이트 중 오류: {e}", exc_info=True)
            self.tooltip_text.hide()

    @pyqtSlot(str, bool)
    def toggle_indicator(self, indicator_key: str, visible: bool):
        """보조지표 표시 상태 토글 (indicator_key는 'MA', 'BB', 'RSI', 'MACD' 등)"""
        logger.info(f"보조지표 토글 요청: {indicator_key}, 표시여부={visible}")
        
        plot_key = None
        target_cols = []
        colors = []
        plot_config = {}

        # 각 보조지표에 대한 설정 정의
        # TODO: styles.py에서 색상 가져오도록 수정
        if indicator_key == 'MA':
            plot_key = 'price'
            target_cols = ['SMA_5', 'SMA_10', 'SMA_20', 'SMA_60', 'SMA_120', 
                           'EMA_5', 'EMA_10', 'EMA_20', 'EMA_60', 'EMA_120']
            colors = [Colors.MA5, Colors.MA10, Colors.MA20, Colors.MA60, Colors.MA120, 
                      Colors.EMA5, Colors.EMA10, Colors.EMA20, Colors.EMA60, Colors.EMA120] 
        elif indicator_key == 'BB':
             plot_key = 'price'
             bb_length, bb_std = 20, 2.0
             target_cols = [f'BBL_{bb_length}_{bb_std}', f'BBM_{bb_length}_{bb_std}', f'BBU_{bb_length}_{bb_std}']
             colors = [Colors.BOLLINGER_BANDS, Colors.BOLLINGER_MID, Colors.BOLLINGER_BANDS]
             # 볼린저밴드 영역 채우기 정보
             plot_config['fill_between'] = (f'BBL_{bb_length}_{bb_std}', f'BBU_{bb_length}_{bb_std}')
             plot_config['fill_brush'] = pg.mkBrush(Colors.BOLLINGER_FILL)
        elif indicator_key == 'RSI':
             plot_key = 'RSI'
             rsi_length = 14
             target_cols = [f'RSI_{rsi_length}']
             colors = [Colors.RSI]
        elif indicator_key == 'MACD':
             plot_key = 'MACD'
             macd_fast, macd_slow, macd_signal = 12, 26, 9
             target_cols = [f'MACD_{macd_fast}_{macd_slow}_{macd_signal}', 
                            f'MACDs_{macd_fast}_{macd_slow}_{macd_signal}']
             colors = [Colors.MACD_LINE, Colors.MACD_SIGNAL]
             hist_col = f'MACDh_{macd_fast}_{macd_slow}_{macd_signal}'
             plot_config['macd_hist'] = hist_col
        elif indicator_key in ['Volume', 'TradingValue']:
             plot = self.plot_items.get(indicator_key.lower())
             if plot:
                 plot.setVisible(visible)
                 if visible: plot.autoRange()
             return
        else:
             logger.error(f"알 수 없는 보조지표 키: {indicator_key}")
             return

        target_plot = self.indicator_plots.get(plot_key) or self.plot_items.get(plot_key)
        if not target_plot:
            logger.error(f"{indicator_key}를 표시할 Plot 없음: {plot_key}")
            return
            
        # 해당 PlotItem 보이기/숨기기
        if plot_key in self.indicator_plots:
            target_plot.setVisible(visible)
            if visible and any(self.indicator_items.get(col) for col in target_cols): 
                 target_plot.autoRange()

        # 개별 커브 아이템 처리
        for i, col in enumerate(target_cols):
            item = self.indicator_items.get(col)
            if visible:
                if not item and not self.chart_data.empty and col in self.chart_data.columns:
                     color = colors[i % len(colors)]
                     fill_item_b = None
                     fill_brush = None
                     # 볼린저밴드 영역 채우기 처리
                     if indicator_key == 'BB' and 'fill_between' in plot_config and col == plot_config['fill_between'][0]: # BBL
                         upper_col = plot_config['fill_between'][1] # BBU
                         if upper_col in self.indicator_items:
                             fill_item_b = self.indicator_items[upper_col]
                             fill_brush = plot_config.get('fill_brush')
                         self._plot_indicator(col, plot_key, color, fillLevelItem=fill_item_b, fillBrush=fill_brush)
                     else:
                         self._plot_indicator(col, plot_key, color)
                elif item:
                    item.setVisible(True)
            elif item:
                 item.setVisible(False)
                 
        # MACD 히스토그램 처리
        if indicator_key == 'MACD' and 'macd_hist' in plot_config:
             hist_col = plot_config['macd_hist']
             hist_item = self.indicator_items.get(hist_col)
             if visible:
                 if not hist_item and not self.chart_data.empty and hist_col in self.chart_data.columns:
                      self._plot_macd_histogram(hist_col, plot_key)
                 elif hist_item:
                      hist_item.setVisible(True)
             elif hist_item:
                  hist_item.setVisible(False)
                  # 히스토그램은 제거하는 것이 더 깔끔할 수 있음
                  if hist_item.scene(): target_plot.removeItem(hist_item)
                  if hist_col in self.indicator_items: del self.indicator_items[hist_col]

    def _plot_macd_histogram(self, col_name: str, plot_key: str):
        """MACD 히스토그램을 BarGraphItem으로 그립니다."""
        if col_name not in self.chart_data.columns:
            logger.warning(f"MACD 히스토그램 데이터 컬럼 없음: {col_name}")
            return
            
        target_plot = self.indicator_plots.get(plot_key)
        if not target_plot:
             logger.error(f"MACD 히스토그램을 그릴 Plot 없음: {plot_key}")
             return
             
        hist_data = self.chart_data[col_name].dropna()
        if hist_data.empty:
             logger.warning(f"MACD 히스토그램 데이터 없음 (NaN 제거 후): {col_name}")
             return
             
        # 오류 수정: int64 사용
        timestamps = hist_data.index.astype('int64') // 10**9
        values = hist_data.values
        bar_width = self._calculate_bar_width(timestamps)
        brushes = [pg.mkColor(Colors.PRICE_UP if v >= 0 else Colors.PRICE_DOWN) for v in values]
        
        if col_name in self.indicator_items:
             item = self.indicator_items[col_name]
             if item.scene():
                 try: item.getViewBox().removeItem(item)
                 except Exception as e: logger.warning(f"기존 MACD 히스토그램({col_name}) 제거 오류: {e}")
             del self.indicator_items[col_name]
             
        hist_item = BarGraphItem(x=timestamps, height=values, width=bar_width, brushes=brushes)
        target_plot.addItem(hist_item)
        self.indicator_items[col_name] = hist_item
        logger.debug(f"MACD 히스토그램 '{col_name}'를 Plot '{plot_key}'에 추가 완료")

    def _plot_indicator(self, col_name: str, plot_key: str, color: str, fillLevelItem=None, fillBrush=None):
        """주어진 컬럼 데이터로 보조지표(라인)를 그립니다."""
        if col_name not in self.chart_data.columns:
            logger.warning(f"보조지표 데이터 컬럼 없음: {col_name}")
            return
            
        target_plot = self.indicator_plots.get(plot_key) or self.plot_items.get(plot_key)
        if not target_plot:
             logger.error(f"보조지표를 그릴 Plot 없음: {plot_key}")
             return
             
        indicator_data = self.chart_data[col_name].dropna()
        if indicator_data.empty:
             logger.warning(f"보조지표 데이터 없음 (NaN 제거 후): {col_name}")
             return
             
        timestamps = indicator_data.index.astype('int64') // 10**9
        values = indicator_data.values
        
        if col_name in self.indicator_items:
             item = self.indicator_items[col_name]
             if item.scene():
                 try: target_plot.removeItem(item) # target_plot에서 제거
                 except Exception as e: logger.warning(f"기존 보조지표({col_name}) 아이템 제거 오류: {e}")
             del self.indicator_items[col_name]
             
        # fillLevel 처리 수정: PlotDataItem 참조 또는 y 값 사용
        # fillLevelItem이 PlotCurveItem 인스턴스라고 가정
        fill_level_data = fillLevelItem.yData if fillLevelItem is not None else None
        
        # PlotCurveItem 생성 시 fillLevel과 brush 전달
        indicator_item = pg.PlotCurveItem(x=timestamps, y=values, pen=pg.mkPen(color, width=1), 
                                          fillLevel=fill_level_data, brush=fillBrush)
        target_plot.addItem(indicator_item)
        self.indicator_items[col_name] = indicator_item
        logger.debug(f"보조지표 '{col_name}'를 Plot '{plot_key}'에 추가 완료")

    def cleanup(self):
        """컴포넌트 정리"""
        logger.info(f"ChartComponent 정리 시작: {self.current_stock_code}")
        # 시그널 프록시 연결 해제
        if self.proxy:
             self.proxy.disconnect() # PyQtGraph 문서 확인 필요
             self.proxy = None
        # 추가적인 pyqtgraph 리소스 정리 (필요시)
        # 예: self.win.clear()
        logger.info(f"ChartComponent 정리 완료: {self.current_stock_code}") 

    @pyqtSlot()
    def _on_xrange_changed(self):
        """X축 범위 변경 시 Y축 범위 자동 조절"""
        if not hasattr(self, 'chart_data') or self.chart_data.empty:
            return

        try:
            price_plot = self.plot_items['price']
            visible_x_range = price_plot.vb.viewRange()[0]
            x_min_ts, x_max_ts = visible_x_range[0], visible_x_range[1]

            # 타임스탬프를 datetime으로 변환 (비교 위해)
            start_dt = pd.Timestamp(x_min_ts, unit='s', tz='UTC').tz_convert('Asia/Seoul')
            end_dt = pd.Timestamp(x_max_ts, unit='s', tz='UTC').tz_convert('Asia/Seoul')

            # 보이는 범위 내 데이터 필터링
            visible_data = self.chart_data[(self.chart_data.index >= start_dt) & (self.chart_data.index <= end_dt)]

            if visible_data.empty:
                # 보이는 데이터 없으면 자동 범위 (혹은 이전 범위 유지)
                # price_plot.enableAutoRange(axis=pg.ViewBox.YAxis)
                return

            # 보이는 데이터 내에서 Low 최소값, High 최대값 찾기
            if 'Low' in visible_data.columns and 'High' in visible_data.columns:
                min_low = visible_data['Low'].min()
                max_high = visible_data['High'].max()
            elif 'Close' in visible_data.columns: # 틱 데이터 등 OHLC 없을 경우
                min_low = visible_data['Close'].min()
                max_high = visible_data['Close'].max()
            else:
                # 가격 정보 없으면 범위 조절 불가
                return

            if pd.isna(min_low) or pd.isna(max_high):
                return # 유효한 가격 범위 없으면 조절 불가

            # Y축 범위 계산 (패딩 추가)
            padding = (max_high - min_low) * 0.05 # 5% 여백
            y_min = min_low - padding
            y_max = max_high + padding

            # Y축 범위 설정
            price_plot.setYRange(y_min, y_max, padding=0)

            # --- 수정 시작: 거래량/거래대금 축 범위 조절 --- 
            # 거래량 Y축 범위 조절
            if 'volume' in self.plot_items and 'Volume' in visible_data.columns:
                volume_plot = self.plot_items['volume']
                max_volume = visible_data['Volume'].max()
                if pd.notna(max_volume):
                    # 약간의 여백 추가 (최대값의 10%)
                    volume_plot.setYRange(0, max_volume * 1.1, padding=0)
            
            # 거래대금 Y축 범위 조절
            if 'value' in self.plot_items and 'TradingValue' in visible_data.columns:
                value_plot = self.plot_items['value']
                max_value = visible_data['TradingValue'].max()
                if pd.notna(max_value):
                    value_plot.setYRange(0, max_value * 1.1, padding=0)
            # --- 수정 끝 ---

        except Exception as e:
            logger.error(f"Error adjusting Y range: {e}", exc_info=True)

    def _redraw_visible_indicators(self):
        """현재 체크된 보조지표 다시 그리기"""
        if not hasattr(self, 'indicator_checkboxes'): return
        for code, checkbox in self.indicator_checkboxes.items():
            if checkbox.isChecked():
                 # 기존 toggle_indicator 로직 재활용 또는 분리된 그리기 함수 호출
                 self.toggle_indicator(code, True)

    # ... (기존 toggle_indicator, _plot_macd_histogram, _plot_indicator)
    # ... (cleanup) 