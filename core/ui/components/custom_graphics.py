# core/ui/components/custom_graphics.py
import pyqtgraph as pg
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QPicture
from PySide6.QtCore import QRectF, Qt, QPointF
import numpy as np
import logging
from datetime import datetime
from core.ui.constants.colors import Colors  # Colors 클래스 임포트 추가

logger = logging.getLogger(__name__)

# --- 수정: 기본 캔들 색상 정의 (한국 시장 표준에 맞게) ---
# 기존 정의
# DEFAULT_UP_COLOR = pg.mkColor('r') # 상승 (빨강)
# DEFAULT_DOWN_COLOR = pg.mkColor('b') # 하락 (파랑)

# 한국 시장 표준에 맞게 수정 
DEFAULT_UP_COLOR = pg.mkColor(Colors.CANDLE_UP) # 상승 (빨강) - Colors 클래스 상수 활용
DEFAULT_DOWN_COLOR = pg.mkColor(Colors.CANDLE_DOWN) # 하락 (파랑) - Colors 클래스 상수 활용
NEUTRAL_COLOR = pg.mkColor('k') # 중립/꼬리 (검정)
# --- 수정 끝 ---

class CandlestickItem(pg.GraphicsObject):
    """커스텀 캔들스틱 아이템 클래스"""
    
    def __init__(self, data, upColor=None, downColor=None, neutralColor=None, wickColor=None):
        """캔들스틱 아이템 초기화 (data는 순서축 기반 튜플)"""
        # data: [(ordinal, open, high, low, close), ...]
        pg.GraphicsObject.__init__(self)
        
        # 데이터 설정
        self.data = np.array(data)  # numpy 배열로 변환
        
        # 색상 설정 (상승=빨간색, 하락=파란색, 보합=검정색)
        self.up_color = pg.mkColor('r') if upColor is None else upColor
        self.down_color = pg.mkColor('b') if downColor is None else downColor
        self.neutral_color = pg.mkColor('k') if neutralColor is None else neutralColor
        
        # 꼬리 색상 설정
        if wickColor is None:
            # 기본 꼬리 색상은 흰색
            self.wick_color = pg.mkColor('w')
        else:
            self.wick_color = wickColor
            
        # 꼬리 그리기 모드 (별도/일체)
        self.separate_wicks = True
        
        # 캔들 너비 (기본값)
        self.candle_width = 0.8
        
        # 캐시 및 경계 계산
        self.picture = None
        self.generatePicture()  # 최초 그림 생성
    
    def generatePicture(self):
        """캔들스틱 그림을 캐시에 생성"""
        if self.data.shape[0] == 0:
            self.picture = QPicture()
            return
        
        # 새 QPicture 생성
        self.picture = QPicture()
        p = QPainter(self.picture)
        
        # 안티앨리어싱 활성화
        p.setRenderHint(QPainter.Antialiasing)
        
        # paint 메서드 호출하여 그림 생성
        self.paint(p, None, None)
        p.end()
        
    def setData(self, data):
        """데이터 설정 및 업데이트 요청"""
        try:
            if data is None or len(data) == 0:
                self.data = np.empty((0, 5))
                logger.warning("캔들스틱에 설정할 데이터가 없습니다.")
            else:
                # 데이터 형식 체크
                if isinstance(data, list) and len(data) > 0 and len(data[0]) == 5:
                    # 리스트 형태로 전달된 경우
                    self.data = np.array(data, dtype=float)
                elif isinstance(data, np.ndarray) and data.shape[1] == 5:
                    # NumPy 배열로 전달된 경우
                    self.data = data
                else:
                    raise ValueError("데이터는 (ordinal, open, high, low, close) 형식의 리스트나 배열이어야 합니다.")
                logger.debug(f"캔들스틱 데이터 설정 완료: {len(data)}개")
        except Exception as e:
            logger.error(f"캔들스틱 데이터 설정 오류: {e}")
            self.data = np.empty((0, 5))
            
        # 업데이트 준비
        self.prepareGeometryChange()
        self.generatePicture()  # 그림 재생성
        self.update()
        
    def setWidth(self, width):
        """캔들 너비 설정 (0.0 ~ 1.0)"""
        if 0.0 < width <= 1.0:
            self.candle_width = width
            self.generatePicture()
            self.update()
        
    def setColors(self, upColor=None, downColor=None, neutralColor=None, wickColor=None):
        """캔들스틱 색상 업데이트"""
        changed = False
        
        if upColor is not None and self.up_color != upColor:
            self.up_color = upColor
            changed = True
            
        if downColor is not None and self.down_color != downColor:
            self.down_color = downColor
            changed = True
            
        if neutralColor is not None and self.neutral_color != neutralColor:
            self.neutral_color = neutralColor
            changed = True
            
        if wickColor is not None and self.wick_color != wickColor:
            self.wick_color = wickColor
            changed = True
        
        # 색상 변경 시에만 다시 그리기
        if changed:
            logger.debug(f"캔들스틱 색상 변경: up={self.up_color.name()}, down={self.down_color.name()}, wick={self.wick_color.name()}")
            self.generatePicture()
            self.update()

    def paint(self, p: QPainter, *args):
        """캔들스틱 직접 그리기 (QPainter 사용, 순서축 기반)"""
        if self.data.shape[0] == 0:
            return
            
        p.setRenderHint(QPainter.Antialiasing)
        
        # 데이터 추출
        ordinals = self.data[:, 0]  # X 좌표 (순서)
        opens = self.data[:, 1]     # 시가
        highs = self.data[:, 2]     # 고가
        lows = self.data[:, 3]      # 저가
        closes = self.data[:, 4]    # 종가
        
        # 캔들 너비 (고정)
        w = self.candle_width  # 순서 간격(1)의 기본 80% 너비 사용
            
        # 꼬리 색상 펜 설정 (모든 캔들에 동일하게 적용)
        wick_pen = QPen(self.wick_color)
        wick_pen.setWidthF(1.0)  # 꼬리 굵기 1.0
        
        # 각 캔들 그리기 전 펜/브러시 초기화
        body_pen = QPen()
        body_pen.setWidth(1)
        body_brush = QBrush()
        
        # 별도 꼬리 모드일 경우, 꼬리를 먼저 그리기
        if self.separate_wicks:
            p.setPen(wick_pen)
            for i in range(len(ordinals)):
                t, o, h, l, c = ordinals[i], opens[i], highs[i], lows[i], closes[i]
                # 모든 캔들의 꼬리를 흰색(wick_color)으로 그리기
                p.drawLine(QPointF(t, h), QPointF(t, l))
        
        # 각 캔들 본체 그리기
        for i in range(len(ordinals)):
            t, o, h, l, c = ordinals[i], opens[i], highs[i], lows[i], closes[i]
            
            # 상승(종가 > 시가), 하락(종가 < 시가), 보합(종가 = 시가) 구분
            if c > o:  # 상승 캔들 (양봉)
                # 한국 시장 관행: 상승=빨간색
                body_pen.setColor(self.up_color)
                body_brush.setColor(self.up_color)
                body_brush.setStyle(Qt.SolidPattern)
            elif c < o:  # 하락 캔들 (음봉)
                # 한국 시장 관행: 하락=파란색
                body_pen.setColor(self.down_color)
                body_brush.setColor(self.down_color)
                body_brush.setStyle(Qt.SolidPattern)
            else:  # 보합 캔들 (시가=종가)
                body_pen.setColor(self.neutral_color)
                body_brush.setStyle(Qt.NoBrush)
                 
            # 본체 펜 설정
            p.setPen(body_pen)
            p.setBrush(body_brush)
            
            # 꼬리 별도 그리기 모드가 아닐 경우, 각 캔들마다 꼬리 그리기
            if not self.separate_wicks:
                # 캔들 꼬리 그리기 (상하좌우 값으로 계산)
                p.drawLine(QPointF(t, h), QPointF(t, max(o, c)))
                p.drawLine(QPointF(t, min(o, c)), QPointF(t, l))
            
            # 본체 그리기
            if o == c:  # 보합: 가로선으로 표시
                p.drawLine(QPointF(t - w / 2, c), QPointF(t + w / 2, c))
            else:  # 상승/하락: 직사각형으로 표시
                rect = QRectF(t - w / 2, min(o, c), w, abs(c - o))
                p.drawRect(rect)

    def boundingRect(self):
        """아이템의 경계 사각형 반환"""
        if self.data.shape[0] == 0:
            return QRectF()
            
        # 유효한 데이터 확인
        ordinals = self.data[:, 0]
        lows = self.data[:, 3]
        highs = self.data[:, 2]
        
        # NaN 값 검사 및 필터링
        valid_indices = ~np.isnan(ordinals) & ~np.isnan(lows) & ~np.isnan(highs)
        if not np.any(valid_indices):
            return QRectF()
        
        valid_ordinals = ordinals[valid_indices]
        valid_lows = lows[valid_indices]
        valid_highs = highs[valid_indices]
        
        # 데이터 범위 계산
        w = self.candle_width
        x_min = valid_ordinals.min() - w
        x_max = valid_ordinals.max() + w
        y_min = valid_lows.min()
        y_max = valid_highs.max()
        
        # 유효한 결과 확인
        if not np.isfinite(x_min) or not np.isfinite(x_max) or \
           not np.isfinite(y_min) or not np.isfinite(y_max):
            logger.warning("경계 계산 결과가 유효하지 않습니다.")
            return QRectF()

        return QRectF(x_min, y_min, x_max - x_min, y_max - y_min)

    def setSeparateWicks(self, separate=True):
        """꼬리 그리기 모드 설정 (True: 별도 그리기, False: 본체와 같은 색상)"""
        if self.separate_wicks != separate:
            self.separate_wicks = separate
            self.generatePicture()
            self.update()

    # set_data 메소드 제거 (setData로 대체)
    # def set_data(self, data):
    #     ...

    # tickStrings 제거 (CandlestickItem은 축이 아님)
    # def tickStrings(self, values, scale, spacing):
    #     ...

    # 필요시 다른 메소드 오버라이드 (예: tickValues) 