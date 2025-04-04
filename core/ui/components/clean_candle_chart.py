"""
직관적이고 깔끔한 캔들스틱 차트 구현

# 활용 방법 예시
--------------------------------------------------------------------------------
기본 사용법:
    # 차트 생성
    chart = CleanCandleChart()
    layout.addWidget(chart)  # 적절한 레이아웃에 추가

    # 데이터 설정 - pandas DataFrame 사용 (OHLCV 형식)
    chart.set_data(df, symbol="삼성전자", timeframe="D")

    # 기본 지표 추가
    chart.add_moving_average(5)  # 5일 이동평균선
    chart.add_moving_average(20)  # 20일 이동평균선
    chart.add_bollinger_bands()  # 볼린저 밴드 추가

지표 토글 방식:
    # 이동평균선 토글
    chart.toggle_moving_average(5)  # 5일선 표시/숨김 전환
    chart.toggle_moving_average(20, True)  # 20일선 강제 표시
    
    # 볼린저 밴드 토글
    chart.toggle_bollinger_bands()  # 볼린저 밴드 표시/숨김 전환

이벤트 처리:
    # 크로스헤어 이동 시그널 연결
    chart.crosshair_moved.connect(self.on_crosshair_moved)
    
    # 차트 로딩 완료 시그널 연결
    chart.chart_loaded.connect(self.on_chart_loaded)

# 설계 철학과 구현 결정
--------------------------------------------------------------------------------
이 클래스는 다음과 같은 프로그래밍 원칙과 설계 철학을 따릅니다:

1. 책임 분리(SRP) 
   - 각 메서드는 단일 책임만 갖도록 설계
   - UI 생성, 데이터 처리, 이벤트 처리가 논리적으로 분리됨
   
   예: 차트 초기화와 데이터 설정이 분리되어 있어 단계적 초기화 가능
   ```
   def setup_ui(self):
       """기본 UI 설정"""
       # 레이아웃 설정만 담당
   
   def set_data(self, df, symbol=None, timeframe=None):
       """차트 데이터 설정"""
       # 데이터 설정과 검증만 담당
   ```

2. 컨테이너 기반 설계
   - 관련 객체들을 범주별로 딕셔너리에 저장하여 코드 가독성 향상
   - 확장성을 고려한 구조로 새로운 요소 추가가 용이
   
   ```
   self.plots = {}          # 플롯 영역 컨테이너
   self.items = {}          # 그래픽 아이템 컨테이너
   self.indicators = {}     # 지표 컨테이너
   ```

3. 성능 최적화 전략
   - 배치 처리: 유사한 그래픽 아이템은 그룹으로 처리하여 드로잉 호출 최소화
   - 데이터 크기 기반 자동 최적화: 데이터 양에 따라 캔들 너비 자동 조정
   
   ```
   # 데이터 양에 따라 캔들 너비 동적 조정
   width = min(0.8, max(0.2, 0.6 / np.log(len(self.data) + 1)))
   
   # 배치 처리로 모든 상승/하락 캔들을 각각 한번에 처리
   self.draw_candle_group(x[up_indices], self.data.iloc[up_indices], ...)
   ```

4. 메모리 관리 
   - 더 이상 사용하지 않는 차트 아이템을 명시적으로 제거하여 메모리 누수 방지
   - 대용량 데이터에서도 효율적으로 작동하도록 설계
   
   ```
   def clear_chart_items(self):
       """차트 아이템 제거 - 메모리 관리를 위해 중요"""
       for category, items in self.items.items():
           for item in items:
               if hasattr(item, 'scene') and item.scene():
                   item.scene().removeItem(item)
       self.items = {}  # 컨테이너 초기화
   ```

5. 유연한 API 설계
   - 간결한 공개 API와 복잡한 내부 구현 분리
   - 기본값과 옵션 파라미터로 다양한 사용 시나리오 지원
   
   ```
   # 간단한 공개 API:
   chart.set_data(df, symbol, timeframe)
   chart.add_moving_average(20)
   chart.toggle_bollinger_bands()
   
   # 복잡한 내부 구현은 private 메서드로 캡슐화
   def update_tooltip(self, x, y, mouse_point): ...
   ```

6. 이벤트 기반 상호작용
   - Qt 시그널/슬롯 메커니즘을 활용한 느슨한 결합
   - 사용자 정의 시그널로 외부 컴포넌트와 통합 용이
   
   ```
   # 시그널 정의
   crosshair_moved = Signal(float, float)  # (x, y) 좌표
   chart_loaded = Signal(bool)  # 로딩 성공/실패
   
   # 이벤트 연결
   main_plot.scene().sigMouseMoved.connect(self.on_mouse_moved)
   ```

7. 확장 가능한 지표 시스템
   - 일관된 패턴으로 다양한 기술적 지표 구현
   - 지표 추가/제거/토글이 편리한 인터페이스
   
   ```
   # 모든 지표는 동일한 패턴으로 추가 가능
   def add_moving_average(self, period, color=None): ...
   def add_bollinger_bands(self, period=20, std_dev=2.0): ...
   
   # 일관된 토글 메서드
   def toggle_moving_average(self, period, visible=None): ...
   def toggle_bollinger_bands(self, visible=None): ...
   ```

8. 시각적 일관성
   - 모든 시각적 스타일을 중앙화하여 일관된 UI 경험 제공
   - 기존 애플리케이션 색상 체계와 통합
   
   ```
   # 스타일 중앙화
   self.style = {
       'candle_up_color': Colors.CANDLE_UP,
       'candle_down_color': Colors.CANDLE_DOWN,
       # ... 다른 스타일 속성들
   }
   ```
--------------------------------------------------------------------------------
"""

import logging
import pyqtgraph as pg
import pandas as pd
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, Signal, Slot, QPointF
from PySide6.QtGui import QPen, QBrush, QColor, QFont

from core.ui.constants.colors import Colors

logger = logging.getLogger(__name__)

class CleanCandleChart(QWidget):
    """
    깔끔하고 직관적인 캔들스틱 차트 구현
    
    특징:
    - 명확한 모듈화와 책임 분리
    - 직관적인 API
    - 성능 최적화
    - 확장 가능한 구조
    """
    
    # 시그널 정의
    crosshair_moved = Signal(float, float)  # 마우스 위치 시그널 (x, y)
    chart_loaded = Signal(bool)  # 데이터 로딩 완료/실패 시그널
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = None
        self.current_symbol = None
        self.current_timeframe = 'D'  # 기본값: 일봉
        
        # 차트 요소 컨테이너
        self.plots = {}          # 플롯 영역 (메인, 거래량, 지표 등)
        self.items = {}          # 그래픽 아이템 (캔들, 선, 바 등)
        self.indicators = {}     # 활성화된 지표
        
        # 크로스헤어 요소
        self.crosshair = {
            'visible': True,
            'v_line': None,
            'h_line': None,
            'tooltip': None
        }
        
        # 시각적 스타일 설정
        self.style = {
            'candle_up_color': Colors.CANDLE_UP,
            'candle_down_color': Colors.CANDLE_DOWN,
            'volume_up_color': QColor(Colors.CANDLE_UP).lighter(150),
            'volume_down_color': QColor(Colors.CANDLE_DOWN).lighter(150),
            'grid_color': Colors.CHART_GRID,
            'crosshair_color': Colors.CROSSHAIR,
            'background_color': Colors.CHART_BACKGROUND,
            'foreground_color': Colors.CHART_FOREGROUND,
            'tooltip_bg': Colors.TOOLTIP_BACKGROUND,
            'tooltip_text': Colors.TOOLTIP_TEXT
        }
        
        self.setup_ui()
        self.setup_interactions()
    
    def setup_ui(self):
        """기본 UI 설정"""
        # 레이아웃 설정
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # PyQtGraph 기본 설정
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', self.style['background_color'])
        pg.setConfigOption('foreground', self.style['foreground_color'])
        
        # 차트 위젯 생성
        self.chart_widget = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.chart_widget)
        
        # 1. 메인 차트 영역 (캔들스틱)
        self.create_main_plot()
        
        # 2. 거래량 차트 영역
        self.create_volume_plot()
    
    def create_main_plot(self):
        """메인 캔들스틱 차트 영역 생성"""
        # 메인 플롯 생성
        main_plot = self.chart_widget.addPlot(row=0, col=0)
        main_plot.setDownsampling(mode='peak')
        main_plot.setClipToView(True)
        main_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # 그리드 스타일 설정
        grid_pen = pg.mkPen(color=self.style['grid_color'], width=1, style=Qt.DashLine)
        main_plot.getAxis('bottom').setGrid(True)
        main_plot.getAxis('left').setGrid(True)
        
        # 축 스타일 설정
        axis_pen = pg.mkPen(color=self.style['foreground_color'], width=1)
        main_plot.getAxis('bottom').setPen(axis_pen)
        main_plot.getAxis('left').setPen(axis_pen)
        
        # 틱 폰트 설정
        axis_font = QFont("Arial", 8)
        main_plot.getAxis('bottom').setTickFont(axis_font)
        main_plot.getAxis('left').setTickFont(axis_font)
        
        # 축 라벨 설정
        main_plot.setLabel('left', '가격')
        
        # 메인 플롯 저장
        self.plots['main'] = main_plot
        
        # 툴팁 텍스트 아이템 추가
        self.tooltip = pg.TextItem(anchor=(0, 0))
        self.tooltip.setZValue(100)  # 다른 요소 위에 표시
        main_plot.addItem(self.tooltip, ignoreBounds=True)
        self.tooltip.hide()  # 초기에는 숨김
        self.crosshair['tooltip'] = self.tooltip
    
    def create_volume_plot(self):
        """거래량 차트 영역 생성"""
        # 거래량 플롯 생성
        volume_plot = self.chart_widget.addPlot(row=1, col=0)
        volume_plot.setMaximumHeight(100)  # 높이 제한
        volume_plot.setXLink(self.plots['main'])  # X축 연결
        
        # 그리드 및 축 설정
        volume_plot.showGrid(x=True, y=True, alpha=0.3)
        volume_plot.setLabel('left', '거래량')
        
        # 축 스타일 설정
        axis_pen = pg.mkPen(color=self.style['foreground_color'], width=1)
        volume_plot.getAxis('bottom').setPen(axis_pen)
        volume_plot.getAxis('left').setPen(axis_pen)
        
        # 틱 폰트 설정
        axis_font = QFont("Arial", 8)
        volume_plot.getAxis('bottom').setTickFont(axis_font)
        volume_plot.getAxis('left').setTickFont(axis_font)
        
        # 거래량 플롯 저장
        self.plots['volume'] = volume_plot
    
    def setup_interactions(self):
        """사용자 상호작용 설정"""
        # 크로스헤어 설정
        self.setup_crosshair()
        
        # 마우스 이벤트 연결
        main_plot = self.plots.get('main')
        if main_plot:
            # 마우스 이동 이벤트 연결
            main_plot.scene().sigMouseMoved.connect(self.on_mouse_moved)
            
            # 확대/축소 이벤트 연결
            main_plot.sigRangeChanged.connect(self.on_range_changed)
            
            # 마우스 클릭 이벤트 (향후 확장)
            # main_plot.scene().sigMouseClicked.connect(self.on_mouse_clicked)
    
    def setup_crosshair(self):
        """크로스헤어 설정"""
        main_plot = self.plots.get('main')
        if not main_plot:
            return
        
        # 크로스헤어 라인 생성
        pen = pg.mkPen(color=self.style['crosshair_color'], style=Qt.DashLine, width=1)
        v_line = pg.InfiniteLine(angle=90, movable=False, pen=pen)
        h_line = pg.InfiniteLine(angle=0, movable=False, pen=pen)
        
        # 메인 플롯에 추가
        main_plot.addItem(v_line, ignoreBounds=True)
        main_plot.addItem(h_line, ignoreBounds=True)
        
        # 초기에는 숨김
        v_line.hide()
        h_line.hide()
        
        # 크로스헤어 저장
        self.crosshair['v_line'] = v_line
        self.crosshair['h_line'] = h_line
    
    def on_mouse_moved(self, pos):
        """마우스 이동 이벤트 처리"""
        main_plot = self.plots.get('main')
        if not main_plot or not main_plot.sceneBoundingRect().contains(pos):
            # 플롯 영역 밖이면 크로스헤어 숨김
            self.hide_crosshair()
            return
        
        # 크로스헤어 표시
        self.show_crosshair()
        
        # 마우스 위치를 데이터 좌표로 변환
        mouse_point = main_plot.vb.mapSceneToView(pos)
        x, y = mouse_point.x(), mouse_point.y()
        
        # 크로스헤어 위치 업데이트
        self.update_crosshair_position(x, y)
        
        # 툴팁 업데이트
        self.update_tooltip(x, y, mouse_point)
        
        # 시그널 발생
        self.crosshair_moved.emit(x, y)
    
    def show_crosshair(self):
        """크로스헤어 표시"""
        if self.crosshair['visible']:
            self.crosshair['v_line'].show()
            self.crosshair['h_line'].show()
    
    def hide_crosshair(self):
        """크로스헤어 숨김"""
        self.crosshair['v_line'].hide()
        self.crosshair['h_line'].hide()
        self.crosshair['tooltip'].hide()
    
    def update_crosshair_position(self, x, y):
        """크로스헤어 위치 업데이트"""
        self.crosshair['v_line'].setPos(x)
        self.crosshair['h_line'].setPos(y)
    
    def update_tooltip(self, x, y, mouse_point):
        """툴팁 내용 및 위치 업데이트"""
        if not self.data or self.data.empty:
            return
        
        # 가장 가까운 데이터 포인트 찾기
        idx = int(round(x))
        if not (0 <= idx < len(self.data)):
            self.crosshair['tooltip'].hide()
            return
        
        # 해당 인덱스의 데이터 가져오기
        row = self.data.iloc[idx]
        
        # HTML 형식의 툴팁 내용 생성
        html = f"""
        <div style='background-color:{self.style["tooltip_bg"]}; color:{self.style["tooltip_text"]}; padding:5px; border-radius:3px;'>
            <div style='font-weight:bold; margin-bottom:3px;'>{self.format_date(idx)}</div>
            <table style='border-spacing:5px 0; margin-top:5px;'>
                <tr><td>시가:</td><td align='right'>{row['Open']:,.0f}</td></tr>
                <tr><td>고가:</td><td align='right'>{row['High']:,.0f}</td></tr>
                <tr><td>저가:</td><td align='right'>{row['Low']:,.0f}</td></tr>
                <tr><td>종가:</td><td align='right' style='color:{self.get_price_color(row)};'>{row['Close']:,.0f}</td></tr>
                <tr><td>거래량:</td><td align='right'>{row['Volume']:,.0f}</td></tr>
            </table>
        </div>
        """
        
        # 툴팁 설정 및 표시
        self.crosshair['tooltip'].setHtml(html)
        self.crosshair['tooltip'].setPos(mouse_point.x() + 10, mouse_point.y() - 10)  # 마우스 근처에 배치
        self.crosshair['tooltip'].show()
    
    def format_date(self, idx):
        """인덱스에 해당하는 날짜 포맷팅"""
        if not self.data or self.data.empty or not (0 <= idx < len(self.data)):
            return ""
        
        # 인덱스가 datetime인 경우
        if isinstance(self.data.index, pd.DatetimeIndex):
            date = self.data.index[idx]
            
            # 시간프레임에 따라 다른 포맷 적용
            if self.current_timeframe == 'M':
                return date.strftime("%Y-%m")
            elif self.current_timeframe == 'W':
                return date.strftime("%Y-%m-%d (주)")
            elif self.current_timeframe == 'D':
                return date.strftime("%Y-%m-%d")
            elif self.current_timeframe.endswith('min'):
                return date.strftime("%Y-%m-%d %H:%M")
            else:
                return date.strftime("%Y-%m-%d %H:%M:%S")
        
        # 'Date' 컬럼이 있는 경우
        elif 'Date' in self.data.columns:
            date_val = self.data.iloc[idx]['Date']
            if isinstance(date_val, str):
                return date_val
            elif isinstance(date_val, (int, float)):
                # 타임스탬프를 날짜로 변환
                date = pd.to_datetime(date_val, unit='s')
                return date.strftime("%Y-%m-%d %H:%M:%S")
        
        # 인덱스가 숫자인 경우
        return f"인덱스 {idx}"
    
    def get_price_color(self, row):
        """가격 변화에 따른 색상 반환"""
        if row['Close'] > row['Open']:
            return self.style['candle_up_color']  # 상승
        elif row['Close'] < row['Open']:
            return self.style['candle_down_color']  # 하락
        else:
            return self.style['foreground_color']  # 보합
    
    def set_data(self, df, symbol=None, timeframe=None):
        """차트 데이터 설정"""
        if df is None or df.empty:
            logger.warning("빈 데이터프레임이 전달되었습니다.")
            self.clear_chart()
            self.chart_loaded.emit(False)
            return
        
        # 필수 칼럼 확인
        required_columns = ['Open', 'High', 'Low', 'Close']
        if not all(col in df.columns for col in required_columns):
            logger.error(f"필수 칼럼({required_columns})이 데이터프레임에 없습니다.")
            self.chart_loaded.emit(False)
            return
        
        # 데이터 저장
        self.data = df.copy()
        
        # 심볼 및 시간프레임 업데이트
        if symbol:
            self.current_symbol = symbol
        if timeframe:
            self.current_timeframe = timeframe
        
        # 차트 그리기
        self.draw_chart()
        
        # 로딩 완료 시그널 발생
        self.chart_loaded.emit(True)
    
    def draw_chart(self):
        """차트 그리기"""
        # 기존 아이템 제거
        self.clear_chart_items()
        
        # 캔들스틱 그리기
        self.draw_candles()
        
        # 거래량 그리기
        if 'Volume' in self.data.columns:
            self.draw_volume()
        
        # X축 포맷 설정
        self.format_time_axis()
        
        # 자동 범위 설정
        self.auto_range()
    
    def draw_candles(self):
        """캔들스틱 그리기"""
        if self.data is None or self.data.empty:
            return
        
        main_plot = self.plots.get('main')
        if not main_plot:
            return
        
        # 데이터 인덱스 생성 (x 좌표)
        x = np.arange(len(self.data))
        
        # 상승/하락 구분
        up_indices = self.data['Close'] >= self.data['Open']
        down_indices = self.data['Close'] < self.data['Open']
        
        # 상승 캔들 그리기
        self.draw_candle_group(
            x[up_indices], 
            self.data.iloc[up_indices], 
            self.style['candle_up_color'],
            QColor(self.style['candle_up_color']).darker(120)
        )
        
        # 하락 캔들 그리기
        self.draw_candle_group(
            x[down_indices],
            self.data.iloc[down_indices],
            self.style['candle_down_color'],
            QColor(self.style['candle_down_color']).darker(120)
        )
    
    def draw_candle_group(self, x_values, data, fill_color, border_color):
        """캔들 그룹 그리기"""
        main_plot = self.plots.get('main')
        if not main_plot or len(x_values) == 0:
            return
        
        # 캔들 너비 (최대 0.8, 최소 0.2)
        width = min(0.8, max(0.2, 0.6 / np.log(len(self.data) + 1)))
        
        # 캔들 브러시 및 펜 생성
        brush = pg.mkBrush(fill_color)
        pen = pg.mkPen(color=border_color, width=1)
        
        # 1. 캔들 본체 그리기 (상자)
        candle_body = pg.BarGraphItem(
            x=x_values,
            height=abs(data['Close'].values - data['Open'].values),
            width=width,
            brush=brush,
            pen=pen
        )
        candle_body.setY(np.minimum(data['Open'].values, data['Close'].values))
        main_plot.addItem(candle_body)
        self.items.setdefault('candles', []).append(candle_body)
        
        # 2. 심지 그리기 (선)
        wick_pen = pg.mkPen(color=border_color, width=1)
        
        # 각 캔들에 대해 심지 그리기
        for i, x_val in enumerate(x_values):
            # 인덱스로 해당 행 가져오기
            row_idx = data.index[i]
            row = data.loc[row_idx]
            
            # 상단 심지
            high_line = pg.PlotCurveItem(
                [x_val, x_val],
                [max(row['Open'], row['Close']), row['High']],
                pen=wick_pen
            )
            main_plot.addItem(high_line)
            self.items.setdefault('wicks', []).append(high_line)
            
            # 하단 심지
            low_line = pg.PlotCurveItem(
                [x_val, x_val],
                [min(row['Open'], row['Close']), row['Low']],
                pen=wick_pen
            )
            main_plot.addItem(low_line)
            self.items.setdefault('wicks', []).append(low_line)
    
    def draw_volume(self):
        """거래량 차트 그리기"""
        if self.data is None or self.data.empty or 'Volume' not in self.data.columns:
            return
        
        volume_plot = self.plots.get('volume')
        if not volume_plot:
            return
        
        # 데이터 인덱스 생성 (x 좌표)
        x = np.arange(len(self.data))
        
        # 상승/하락 구분
        up_indices = self.data['Close'] >= self.data['Open']
        down_indices = self.data['Close'] < self.data['Open']
        
        # 캔들 너비 (최대 0.8, 최소 0.2)
        width = min(0.8, max(0.2, 0.6 / np.log(len(self.data) + 1)))
        
        # 상승 거래량 그리기
        if any(up_indices):
            up_volume = pg.BarGraphItem(
                x=x[up_indices],
                height=self.data.iloc[up_indices]['Volume'].values,
                width=width,
                brush=self.style['volume_up_color'],
                pen=None
            )
            volume_plot.addItem(up_volume)
            self.items.setdefault('volume', []).append(up_volume)
        
        # 하락 거래량 그리기
        if any(down_indices):
            down_volume = pg.BarGraphItem(
                x=x[down_indices],
                height=self.data.iloc[down_indices]['Volume'].values,
                width=width,
                brush=self.style['volume_down_color'],
                pen=None
            )
            volume_plot.addItem(down_volume)
            self.items.setdefault('volume', []).append(down_volume)
    
    def format_time_axis(self):
        """X축 시간 포맷 설정"""
        main_plot = self.plots.get('main')
        if not main_plot or self.data is None or self.data.empty:
            return
        
        # 데이터 길이에 따라 표시할 틱 개수 결정
        data_len = len(self.data)
        if data_len <= 10:
            step = 1
        elif data_len <= 50:
            step = 5
        elif data_len <= 100:
            step = 10
        elif data_len <= 200:
            step = 20
        else:
            step = data_len // 10
        
        # 틱 위치 및 라벨 생성
        ticks = []
        for i in range(0, data_len, step):
            if i < data_len:
                date_str = self.format_date(i)
                ticks.append((i, date_str))
        
        # 마지막 포인트 추가
        if data_len > 0 and (data_len - 1) % step != 0:
            date_str = self.format_date(data_len - 1)
            ticks.append((data_len - 1, date_str))
        
        # X축 틱 설정
        main_plot.getAxis('bottom').setTicks([ticks])
        
        # 볼륨 차트도 같은 틱 설정 적용
        volume_plot = self.plots.get('volume')
        if volume_plot:
            volume_plot.getAxis('bottom').setTicks([ticks])
    
    def auto_range(self):
        """자동 범위 설정"""
        if self.data is None or self.data.empty:
            return
        
        # 메인 차트 Y축 범위 설정
        main_plot = self.plots.get('main')
        if main_plot:
            min_price = self.data['Low'].min()
            max_price = self.data['High'].max()
            
            # 여유 공간 추가 (10%)
            price_range = max_price - min_price
            padding = price_range * 0.1
            main_plot.setYRange(min_price - padding, max_price + padding)
            
            # X축 범위는 전체 데이터 표시
            main_plot.setXRange(-0.5, len(self.data) - 0.5)
        
        # 거래량 차트 Y축 범위 설정
        volume_plot = self.plots.get('volume')
        if volume_plot and 'Volume' in self.data.columns:
            max_volume = self.data['Volume'].max()
            
            # 여유 공간 추가 (10%)
            volume_plot.setYRange(0, max_volume * 1.1)
    
    def clear_chart(self):
        """차트 초기화"""
        self.clear_chart_items()
        self.data = None
    
    def clear_chart_items(self):
        """차트 아이템 제거"""
        # 모든 아이템 제거
        for category, items in self.items.items():
            for item in items:
                if category == 'candles' or category == 'volume':
                    # BarGraphItem은 부모 플롯에서 직접 제거
                    plot = self.plots.get('main' if category == 'candles' else 'volume')
                    if plot:
                        plot.removeItem(item)
                else:
                    # 기타 아이템
                    if hasattr(item, 'scene') and item.scene():
                        item.scene().removeItem(item)
        
        # 아이템 컨테이너 초기화
        self.items = {}
    
    def add_moving_average(self, period, color=None):
        """이동평균선 추가"""
        if self.data is None or self.data.empty or 'Close' not in self.data.columns:
            return
        
        # 이동평균 계산
        ma_column = f'MA{period}'
        self.data[ma_column] = self.data['Close'].rolling(window=period).mean()
        
        # 색상 설정
        if color is None:
            # 기본 색상 설정
            colors = ['#FFDE03', '#FF9A00', '#8A2BE2', '#00C853']
            color = colors[period % len(colors)]
        
        # 이동평균선 그리기
        main_plot = self.plots.get('main')
        if main_plot:
            # NaN 제거
            valid_data = self.data.dropna(subset=[ma_column])
            
            # 데이터가 충분하면 그리기
            if not valid_data.empty:
                x = np.arange(len(self.data))[len(self.data) - len(valid_data):]
                y = valid_data[ma_column].values
                
                pen = pg.mkPen(color=color, width=1.5)
                ma_line = pg.PlotCurveItem(x=x, y=y, pen=pen, name=f"MA{period}")
                main_plot.addItem(ma_line)
                
                # 아이템 저장
                self.items.setdefault('indicators', []).append(ma_line)
                self.indicators[ma_column] = ma_line
    
    def toggle_moving_average(self, period, visible=None):
        """이동평균선 표시/숨김 전환"""
        ma_column = f'MA{period}'
        
        if ma_column in self.indicators:
            ma_line = self.indicators[ma_column]
            
            # visible이 None이면 현재 상태 반전
            if visible is None:
                visible = not ma_line.isVisible()
            
            # 표시 상태 설정
            ma_line.setVisible(visible)
        else:
            # 이동평균선이 없으면 추가
            self.add_moving_average(period)
    
    def add_bollinger_bands(self, period=20, std_dev=2.0):
        """볼린저 밴드 추가"""
        if self.data is None or self.data.empty or 'Close' not in self.data.columns:
            return
        
        # 중심선 (단순 이동평균)
        middle = self.data['Close'].rolling(window=period).mean()
        
        # 표준편차
        std = self.data['Close'].rolling(window=period).std()
        
        # 상단 및 하단 밴드
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        # 데이터프레임에 추가
        self.data['BB_Middle'] = middle
        self.data['BB_Upper'] = upper
        self.data['BB_Lower'] = lower
        
        # 볼린저 밴드 그리기
        main_plot = self.plots.get('main')
        if main_plot:
            # NaN 제거
            valid_data = self.data.dropna(subset=['BB_Middle', 'BB_Upper', 'BB_Lower'])
            
            # 데이터가 충분하면 그리기
            if not valid_data.empty:
                x = np.arange(len(self.data))[len(self.data) - len(valid_data):]
                
                # 중심선
                middle_pen = pg.mkPen(color='#FFDE03', width=1.5)
                middle_line = pg.PlotCurveItem(
                    x=x, 
                    y=valid_data['BB_Middle'].values, 
                    pen=middle_pen, 
                    name="BB Middle"
                )
                main_plot.addItem(middle_line)
                
                # 상단 밴드
                upper_pen = pg.mkPen(color='#FF416C', width=1.5)
                upper_line = pg.PlotCurveItem(
                    x=x, 
                    y=valid_data['BB_Upper'].values, 
                    pen=upper_pen, 
                    name="BB Upper"
                )
                main_plot.addItem(upper_line)
                
                # 하단 밴드
                lower_pen = pg.mkPen(color='#00C853', width=1.5)
                lower_line = pg.PlotCurveItem(
                    x=x, 
                    y=valid_data['BB_Lower'].values, 
                    pen=lower_pen, 
                    name="BB Lower"
                )
                main_plot.addItem(lower_line)
                
                # 밴드 채우기
                fill = pg.FillBetweenItem(
                    upper_line, 
                    lower_line, 
                    brush=pg.mkBrush(QColor(138, 43, 226, 30))  # 반투명 보라색
                )
                main_plot.addItem(fill)
                
                # 아이템 저장
                self.items.setdefault('indicators', []).extend([middle_line, upper_line, lower_line, fill])
                self.indicators['BB_Middle'] = middle_line
                self.indicators['BB_Upper'] = upper_line
                self.indicators['BB_Lower'] = lower_line
                self.indicators['BB_Fill'] = fill
    
    def toggle_bollinger_bands(self, visible=None):
        """볼린저 밴드 표시/숨김 전환"""
        bb_items = ['BB_Middle', 'BB_Upper', 'BB_Lower', 'BB_Fill']
        
        # 모든 볼린저 밴드 구성요소가 있는지 확인
        if all(item in self.indicators for item in bb_items):
            # visible이 None이면 현재 상태 반전
            if visible is None:
                visible = not self.indicators['BB_Middle'].isVisible()
            
            # 모든 구성요소의 표시 상태 설정
            for key in bb_items:
                self.indicators[key].setVisible(visible)
        else:
            # 볼린저 밴드가 없으면 추가
            self.add_bollinger_bands()
    
    def resize_event(self, event):
        """위젯 크기 조정 이벤트 처리"""
        super().resizeEvent(event)
        
        # 거래량 차트 높이 조정
        total_height = self.height()
        volume_plot = self.plots.get('volume')
        
        if volume_plot:
            # 전체 높이의 20%를 거래량 차트에 할당
            volume_height = int(total_height * 0.2)
            volume_plot.setMaximumHeight(volume_height)
            
        # LOD 알고리즘 적용
        self.apply_level_of_detail()
    
    # LOD 알고리즘 관련 메서드 추가
    def apply_level_of_detail(self):
        """현재 줌 레벨에 따라 Level of Detail 적용"""
        if not self.data or self.data.empty:
            return
            
        # 현재 표시 영역 계산
        main_plot = self.plots.get('main')
        if not main_plot:
            return
            
        # 현재 X축 범위 가져오기
        x_range = main_plot.getViewBox().viewRange()[0]
        visible_range = x_range[1] - x_range[0]
        
        # 화면 너비 (픽셀) 가져오기
        screen_width = main_plot.width()
        
        # 최적 해상도 결정
        timeframe, sampling_ratio = self._get_optimal_resolution(visible_range, screen_width)
        
        # 현재 타임프레임과 다르면 타임프레임 전환
        if timeframe != self.current_timeframe:
            # 실제 구현에서는 여기서 새 타임프레임 데이터를 로드
            self.current_timeframe = timeframe
            # TODO: 새 타임프레임 데이터 로드 로직 구현
            
        # 데이터 샘플링 적용
        if sampling_ratio < 1.0:
            sampled_data = self._apply_sampling(self.data, sampling_ratio)
            # 샘플링된 데이터로 차트 갱신
            self.clear_chart_items()
            self._plot_sampled_data(sampled_data)
    
    def _get_optimal_resolution(self, view_range, screen_width):
        """화면 너비와 보는 시간범위에 따른 최적 해상도 결정"""
        
        # 1. 타임프레임 선택 (큰 범위일수록 큰 타임프레임)
        timeframe = self._select_timeframe(view_range)
        
        # 2. 해당 타임프레임 내에서 샘플링 비율 계산
        # 화면 픽셀:데이터 비율이 1:1에 가깝게 유지
        data_points = len(self.data)
        sampling_ratio = min(1.0, screen_width * 1.5 / data_points)
        
        return timeframe, sampling_ratio
    
    def _select_timeframe(self, visible_range):
        """줌 레벨에 따른 최적 타임프레임 선택"""
        # 현재 구현에서는 단순화를 위해 현재 타임프레임 유지
        # 실제 구현에서는 시간 범위에 따라 타임프레임 변경
        
        # 예시 구현 (실제 시간 값으로 변환 필요)
        ONE_MINUTE = 1
        ONE_HOUR = 60 * ONE_MINUTE
        ONE_DAY = 24 * ONE_HOUR
        ONE_WEEK = 7 * ONE_DAY
        ONE_MONTH = 30 * ONE_DAY
        ONE_YEAR = 365 * ONE_DAY
        
        # 보이는 범위에 따른 최적 타임프레임 결정
        # 참고: visible_range는 캔들 수 기준
        if visible_range > 500:
            return "M"  # 월봉
        elif visible_range > 200:
            return "W"  # 주봉
        elif visible_range > 60:
            return "D"  # 일봉
        elif visible_range > 24:
            return "4h"  # 4시간봉
        elif visible_range > 8:
            return "1h"  # 1시간봉
        elif visible_range > 2:
            return "15min"  # 15분봉
        else:
            return "1min"  # 1분봉
            
    def _apply_sampling(self, data, ratio):
        """데이터 샘플링 적용 (LTTB 알고리즘)"""
        if ratio >= 1.0:
            return data  # 샘플링 필요 없음
            
        # 목표 데이터 포인트 수 계산
        target_points = max(10, int(len(data) * ratio))
        
        # LTTB 알고리즘 적용
        return self._lttb_downsample(data, target_points)
    
    def _lttb_downsample(self, data, target_points):
        """
        Largest-Triangle-Three-Buckets 알고리즘으로 시각적 중요도 기반 다운샘플링
        """
        # 원본 데이터 포인트가 타겟보다 적으면 그대로 반환
        if len(data) <= target_points:
            return data
        
        # 다운샘플링 결과를 저장할 DataFrame
        sampled = pd.DataFrame(columns=data.columns)
        
        # 첫 점과 마지막 점은 항상 유지
        sampled = pd.concat([sampled, pd.DataFrame([data.iloc[0]])], ignore_index=True)
        
        # 각 버킷 크기 계산
        bucket_size = (len(data) - 2) / (target_points - 2)
        
        # 중간 포인트 선택
        for i in range(1, target_points - 1):
            # 세 버킷의 범위 계산
            a = int((i - 1) * bucket_size) + 1
            b = int(i * bucket_size) + 1
            c = int((i + 1) * bucket_size) + 1 if i < target_points - 2 else len(data) - 1
            
            # 현재 버킷의 데이터 포인트
            curr_bucket = data.iloc[a:b]
            
            # 이전 버킷의 대표점
            prev_point = sampled.iloc[-1]
            
            # 다음 버킷의 대표점
            next_point = data.iloc[c]
            
            # 삼각형 면적 최대화 포인트 찾기
            max_area = -1
            max_idx = a
            
            for j in range(a, b):
                # 삼각형 면적 계산 (시각적 중요도)
                area = abs(
                    (prev_point.name - next_point.name) * (data.iloc[j]['Close'] - prev_point['Close']) -
                    (prev_point.name - data.iloc[j].name) * (next_point['Close'] - prev_point['Close'])
                ) * 0.5
                
                if area > max_area:
                    max_area = area
                    max_idx = j
            
            # 최대 면적 포인트 추가
            sampled = pd.concat([sampled, pd.DataFrame([data.iloc[max_idx]])], ignore_index=True)
        
        # 마지막 점 추가
        sampled = pd.concat([sampled, pd.DataFrame([data.iloc[-1]])], ignore_index=True)
        
        return sampled
    
    def _plot_sampled_data(self, data):
        """샘플링된 데이터 플로팅 (최적화 버전)"""
        # 기존 draw_chart()와 유사하지만 최적화된 방식으로 구현
        
        # 간소화된 캔들 표현 (줌아웃 시)
        if len(data) > 100:
            self._draw_simplified_candles(data)
        else:
            # 상세한 캔들 표현 (줌인 시)
            self.draw_candles()
        
        # 거래량 그리기
        if 'Volume' in data.columns:
            self._draw_simplified_volume(data) if len(data) > 100 else self.draw_volume()
    
    def _draw_simplified_candles(self, data):
        """대량의 데이터를 위한 단순화된 캔들 그리기"""
        main_plot = self.plots.get('main')
        if not main_plot:
            return
            
        # 상승/하락 구분
        up_indices = data['Close'] >= data['Open']
        down_indices = data['Close'] < data['Open']
        
        # 데이터 인덱스 생성
        x = np.arange(len(data))
        
        # 더 얇은 캔들 너비 사용
        width = min(0.8, max(0.1, 0.3 / np.log(len(data) + 1)))
        
        # 상승 캔들 (심지 생략)
        if any(up_indices):
            up_body = pg.BarGraphItem(
                x=x[up_indices],
                height=data.iloc[up_indices]['Close'].values - data.iloc[up_indices]['Open'].values,
                width=width,
                brush=pg.mkBrush(self.style['candle_up_color']),
                pen=None
            )
            up_body.setY(data.iloc[up_indices]['Open'].values)
            main_plot.addItem(up_body)
            self.items.setdefault('candles', []).append(up_body)
        
        # 하락 캔들 (심지 생략)
        if any(down_indices):
            down_body = pg.BarGraphItem(
                x=x[down_indices],
                height=data.iloc[down_indices]['Open'].values - data.iloc[down_indices]['Close'].values,
                width=width,
                brush=pg.mkBrush(self.style['candle_down_color']),
                pen=None
            )
            down_body.setY(data.iloc[down_indices]['Close'].values)
            main_plot.addItem(down_body)
            self.items.setdefault('candles', []).append(down_body)
    
    def _draw_simplified_volume(self, data):
        """대량의 데이터를 위한 단순화된 거래량 그리기"""
        volume_plot = self.plots.get('volume')
        if not volume_plot or 'Volume' not in data.columns:
            return
            
        # 데이터 인덱스 생성
        x = np.arange(len(data))
        
        # 얇은 바 사용
        width = min(0.8, max(0.1, 0.3 / np.log(len(data) + 1)))
        
        # 모든 거래량을 단일 색상으로 그리기 (구분 없이)
        volume_bar = pg.BarGraphItem(
            x=x,
            height=data['Volume'].values,
            width=width,
            brush=pg.mkBrush(QColor(self.style['volume_up_color']).lighter(130)),
            pen=None
        )
        volume_plot.addItem(volume_bar)
        self.items.setdefault('volume', []).append(volume_bar)
    
    def on_range_changed(self, view_box):
        """X축 또는 Y축 범위 변경 이벤트 처리"""
        # LOD 알고리즘 적용
        self.apply_level_of_detail() 