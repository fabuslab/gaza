# core/ui/components/custom_graphics.py
import pyqtgraph as pg
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath
from PySide6.QtCore import QRectF, Qt, QPointF
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CandlestickItem(pg.GraphicsObject):
    """캔들스틱 차트 아이템"""
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        # data는 (timestamp, open, high, low, close, volume) 튜플의 리스트/배열
        self.data = np.array(data) if data else np.empty((0, 6))
        self.picture = None # QPicture 캐시
        self.generatePicture()

    def generatePicture(self):
        # QPainterPath 리스트 사용: 각 캔들(라인+몸통)을 별도 Path로 관리
        self.paths = [] 
        self.brushes = []
        self.pens = []
        
        if self.data.shape[0] == 0:
            self.prepareGeometryChange()
            return

        timestamps = self.data[:, 0]
        opens = self.data[:, 1]
        highs = self.data[:, 2]
        lows = self.data[:, 3]
        closes = self.data[:, 4]
        
        # 막대 너비 계산
        if len(timestamps) > 1:
            diffs = np.diff(timestamps)
            valid_diffs = diffs[diffs > 0]
            if len(valid_diffs) > 0:
                median_diff = np.median(valid_diffs)
                w = median_diff * 0.8
            else:
                w = 60 * 60 * 24 * 0.8 
        elif len(timestamps) == 1:
             w = 60 * 60 * 24 * 0.8
        else:
             w = 1
             
        if w <= 0: w = 1

        for i in range(len(timestamps)):
            t, o, h, l, c = timestamps[i], opens[i], highs[i], lows[i], closes[i]
            path = QPainterPath() # 각 캔들마다 새 Path
            
            # 라인 (High-Low)
            path.moveTo(QPointF(t, h))
            path.lineTo(QPointF(t, l))

            # 몸통
            if o == c:
                path.moveTo(QPointF(t - w / 2, c))
                path.lineTo(QPointF(t + w / 2, c))
            else:
                rect = QRectF(t - w / 2, min(o, c), w, abs(c - o))
                path.addRect(rect)
                
            self.paths.append(path)
            
            # 색상 결정
            pen = QPen()
            brush = QBrush()
            if o < c: # 양봉
                pen.setColor(QColor(Qt.red))
                brush.setColor(QColor(Qt.red))
            elif o > c: # 음봉
                pen.setColor(QColor(Qt.blue))
                brush.setColor(QColor(Qt.blue))
            else: # 도지 (시가=종가)
                 pen.setColor(QColor(Qt.black)) # 라인만 검정색
                 brush.setStyle(Qt.NoBrush) # 몸통 채우지 않음
                 
            pen.setWidthF(1.0)
            brush.setStyle(Qt.SolidPattern if o != c else Qt.NoBrush)
            self.pens.append(pen)
            self.brushes.append(brush)

        self.prepareGeometryChange() # boundingRect 변경 알림

    def paint(self, p, *args):
        # 각 Path를 저장된 Pen과 Brush로 그리기
        p.setRenderHint(QPainter.Antialiasing)
        for i, path in enumerate(self.paths):
            if i < len(self.pens) and i < len(self.brushes):
                p.setPen(self.pens[i])
                p.setBrush(self.brushes[i])
                p.drawPath(path)

    def boundingRect(self):
        # 데이터 기반으로 boundingRect 계산
        if self.data.shape[0] == 0:
            return QRectF()
            
        timestamps = self.data[:, 0]
        lows = self.data[:, 3]
        highs = self.data[:, 2]
        
        if len(timestamps) > 1:
             diffs = np.diff(timestamps)
             valid_diffs = diffs[diffs > 0]
             median_diff = np.median(valid_diffs) if len(valid_diffs) > 0 else (60 * 60 * 24)
             w = median_diff * 0.8
        else:
             w = 60 * 60 * 24 * 0.8
        if w <= 0: w = 1
        
        x_min = timestamps.min() - w / 2
        x_max = timestamps.max() + w / 2
        y_min = lows.min()
        y_max = highs.max()
        
        return QRectF(x_min, y_min, x_max - x_min, y_max - y_min)
        
    def set_data(self, data):
        """데이터 업데이트 및 다시 그리기"""
        self.data = np.array(data) if data else np.empty((0, 6))
        self.generatePicture() # Path 재생성
        self.update() # QGraphicsObject 업데이트 요청 

    def tickStrings(self, values, scale, spacing):
        """주어진 타임스탬프 값(values)을 주기에 맞는 문자열로 변환"""
        strings = []
        # logger.debug(f"tickStrings 호출: {len(values)}개 값, 주기={self.current_timeframe}")
        if not values:
            return []

        # 값 범위와 개수를 보고 포맷 결정 (분/틱 차트용)
        min_val, max_val = min(values), max(values)
        time_range_sec = max_val - min_val if max_val > min_val else 0

        # --- 수정 시작: 주기에 따른 포맷 명확화 ---
        try:
            fmt_str = '' # 포맷 초기화
            is_tick_or_minute = self.current_timeframe.isdigit() or self.current_timeframe.endswith('T')

            if is_tick_or_minute:
                if time_range_sec <= 60 * 60 * 2: # 2시간 이하: 시:분:초
                    fmt_str = '%H:%M:%S'
                elif time_range_sec <= 60 * 60 * 24 * 2: # 2일 이하: 월-일 시:분
                    fmt_str = '%m-%d %H:%M'
                else: # 그 이상: 연-월-일 (분/틱 차트에서 긴 범위)
                    fmt_str = '%Y-%m-%d'
            elif self.current_timeframe == 'D': # 일봉
                fmt_str = '%Y-%m-%d'
            elif self.current_timeframe == 'W': # 주봉
                fmt_str = '%Y-%m-%d' # 축에는 일단 해당 주의 대표 날짜(주로 월요일) 표시
            elif self.current_timeframe == 'M': # 월봉
                fmt_str = '%Y-%m'
            elif self.current_timeframe == 'Y': # 연봉
                fmt_str = '%Y'
            else: # 기타 또는 알 수 없는 주기
                fmt_str = '%Y-%m-%d %H:%M:%S' # 기본 상세 포맷

            for v in values:
                dt = datetime.fromtimestamp(v)
                strings.append(dt.strftime(fmt_str))
        # --- 수정 끝 ---
        except Exception as e:
            # logger.error(f"tickStrings 변환 오류: {e}, 값={values[:5]}...", exc_info=True) # 상세 오류 로깅
            strings = [str(v) for v in values] 

        # --- 추가: 너무 촘촘할 경우 레이블 생략 (연/월/주/일봉) --- 
        if self.current_timeframe in ['Y', 'M', 'W', 'D'] and len(strings) > 10: # 예시: 10개 초과 시
            visible_range = self.axis.linkedView().viewRect()
            if visible_range is not None:
                min_x, max_x = visible_range.left(), visible_range.right()
                tick_density = len(values) / (max_x - min_x) if (max_x - min_x) > 0 else 0
                # logger.debug(f"Tick density: {tick_density:.2f} ticks/unit")
                # 밀도에 따라 레이블 표시 간격 조절 (임계값 조정 필요)
                label_interval = 1
                if tick_density > 0.00001: # 밀도가 매우 높으면 (예: 일봉 확대)
                    label_interval = max(1, int(len(strings) / 10)) # 최대 10개 정도만 표시되도록
                
                for i in range(len(strings)):
                    if i % label_interval != 0:
                        strings[i] = "" # 간격에 따라 빈 문자열로 변경
        # --- 추가 끝 ---
        return strings 

    # 필요시 다른 메소드 오버라이드 (예: tickValues) 