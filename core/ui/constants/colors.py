"""
UI Color Constants
"""

from PySide6.QtGui import QColor

class Colors:
    """색상 정의"""
    # 기본 색상
    PRIMARY = "#1e88e5" # 파란색 계열
    PRIMARY_HOVER = "#1976d2"
    PRIMARY_PRESSED = "#1565c0"
    PRIMARY_DISABLED = "#a4c9f4"
    
    SECONDARY = "#424242" # 회색 계열
    SECONDARY_HOVER = "#616161"
    SECONDARY_PRESSED = "#757575"
    SECONDARY_DISABLED = "#bdbdbd"
    
    SUCCESS = "#4caf50" # 녹색 계열
    SUCCESS_HOVER = "#43a047"
    SUCCESS_PRESSED = "#388e3c"
    SUCCESS_DISABLED = "#a5d6a7"
    
    WARNING = "#ff9800" # 주황색 계열
    WARNING_HOVER = "#fb8c00"
    WARNING_PRESSED = "#f57c00"
    WARNING_DISABLED = "#ffcc80"

    DANGER = "#f44336" # 빨간색 계열
    DANGER_HOVER = "#e53935"
    DANGER_PRESSED = "#d32f2f"
    DANGER_DISABLED = "#ef9a9a"

    INFO = "#2196f3" # 밝은 파란색 계열
    INFO_HOVER = "#1e88e5"
    INFO_PRESSED = "#1976d2"
    INFO_DISABLED = "#90caf9"

    # 활성/강조 색상 (Accent Color) - INFO 기반
    ACCENT = INFO # 기본 활성 색상
    ACCENT_HOVER = INFO_HOVER
    ACCENT_PRESSED = INFO_PRESSED

    LIGHT = "#f5f5f5" # 매우 밝은 회색
    DARK = "#212121" # 매우 어두운 회색 (거의 검정)
    WHITE = "#ffffff"
    BLACK = "#000000"

    # 배경색 (Light/Dark 모드 고려)
    BACKGROUND = "#ffffff" # 기본 배경 (밝음)
    BACKGROUND_LIGHT = "#f5f5f5" # 약간 어두운 배경
    BACKGROUND_DARKER = "#eeeeee" # 더 어두운 배경
    BACKGROUND_DARKEST = "#e0e0e0" # 가장 어두운 배경 (밝은 모드 기준)
    # TODO: 다크 모드 색상 정의 추가 필요
    
    # 텍스트 색상
    TEXT = "#333333" # 기본 텍스트
    TEXT_EMPHASIS = "#111111" # 강조 텍스트
    TEXT_SECONDARY = "#757575" # 보조 텍스트 (회색)
    TEXT_DISABLED = "#bdbdbd" # 비활성 텍스트
    TEXT_ON_PRIMARY = WHITE # Primary 배경 위의 텍스트
    TEXT_ON_SECONDARY = WHITE # Secondary 배경 위의 텍스트
    TEXT_ON_DANGER = WHITE # Danger 배경 위의 텍스트

    # 추가: stylesheets.py에서 사용하는 누락된 상수
    FOREGROUND = "#333333" # TEXT와 동일한 색상 값 사용

    # 테두리 색상
    BORDER = "#aaaaaa"
    BORDER_LIGHT = "#eeeeee"
    BORDER_DARK = "#bdbdbd"
    BORDER_DISABLED = "#eeeeee"
    
    # 기타 상태 색상
    DISABLED = "#e0e0e0" # 비활성화된 요소 배경/테두리 (BORDER와 동일하게 시작)
    HOVER = "#eeeeee" # 기본 호버 배경 (임시) -> 실제로는 각 컴포넌트 스타일에 정의됨

    # 주가 관련 색상
    PRICE_UP = "#d32f2f"     # 상승 (빨간색)
    PRICE_DOWN = "#1976d2"   # 하락 (파란색)
    PRICE_UNCHANGED = "#555555"  # 보합 (회색)
    
    # 추세 표시 색상 (요구사항에 맞게 추가)
    TREND_STRONG_UP = "#FF4500"    # 강한 상승 색상 (진한 빨간색)
    TREND_UP = "#FF6B6B"           # 상승 색상 (연한 빨간색)
    TREND_NEUTRAL = "#808080"      # 중립 색상 (회색)
    TREND_DOWN = "#6B9BFF"         # 하락 색상 (연한 파란색)
    TREND_STRONG_DOWN = "#1261C4"  # 강한 하락 색상 (진한 파란색)

    # --- 차트 관련 색상 추가 ---
    CANDLE_UP = "#d32f2f"         # 양봉 캔들 (빨강 - PRICE_UP과 동일하게)
    CANDLE_DOWN = "#1976d2"       # 음봉 캔들 (파랑 - PRICE_DOWN과 동일하게)
    CANDLE_DOJI = "#555555"       # 도지 캔들 (회색 - PRICE_UNCHANGED와 동일하게)

    VOLUME_UP = (211, 47, 47, 150)   # 상승 거래량 (빨강, 반투명) - QColor(Colors.PRICE_UP)에 알파값 추가 방식 고려
    VOLUME_DOWN = (25, 118, 210, 150) # 하락 거래량 (파랑, 반투명) - QColor(Colors.PRICE_DOWN)에 알파값 추가 방식 고려
    TRADING_VALUE = "#ff9800"      # 거래대금 라인 (주황)

    MA5 = "#ff7f0e"                # 5일 이평선 (주황)
    MA10 = "#1f77b4"               # 10일 이평선 (파랑)
    MA20 = "#2ca02c"               # 20일 이평선 (녹색)
    MA60 = "#9467bd"               # 60일 이평선 (보라)
    MA120 = "#8c564b"              # 120일 이평선 (갈색)
    # EMA 색상 (MA와 다르게 또는 동일하게)
    EMA5 = MA5 
    EMA10 = MA10
    EMA20 = MA20
    EMA60 = MA60
    EMA120 = MA120

    BOLLINGER_BANDS = "#bdbdbd"       # 볼린저 밴드 상/하단 선 (연회색)
    BOLLINGER_MID = "#ff7f0e"        # 볼린저 밴드 중간 선 (주황 - MA20과 겹치지 않게)
    BOLLINGER_FILL = (224, 224, 224, 50) # 볼린저 밴드 내부 채우기 (연회색, 반투명)

    MACD_LINE = "#1f77b4"          # MACD 선 (파랑)
    MACD_SIGNAL = "#ff7f0e"        # MACD 시그널 선 (주황)
    MACD_HIST_UP = "#d32f2f"       # MACD 히스토그램 양수 (빨강)
    MACD_HIST_DOWN = "#1976d2"     # MACD 히스토그램 음수 (파랑)
    ZERO_LINE = "#808080"            # 0 기준선 (회색)

    RSI_LINE = "#9467bd"           # RSI 선 (보라)
    RSI_OVER = "#d32f2f"           # RSI 과매수/과매도 기준선 (빨강)

    MARKER_BUY = "#4caf50"         # 매수 마커 (녹색)
    MARKER_SELL = "#f44336"        # 매도 마커 (빨강)
    MARKER_HOLD = "#bdbdbd"        # 홀드 마커 (회색)
    # --- 차트 관련 색상 추가 끝 ---

    # --- 차트 관련 색상 추가 (기존 정의 확인 및 통합) ---
    CHART_BACKGROUND = "#f0f0f0"
    CHART_FOREGROUND = "#333333"
    CROSSHAIR = "#808080"         # 크로스헤어 라인 색상 (회색)
    TOOLTIP_BACKGROUND = "#ffffdc"
    TOOLTIP_TEXT = "#000000"

    DEFAULT_LINE = (0, 0, 0)         # 기본 선 색상 (검정)

    BB_LINE = (100, 100, 100)        # 볼린저 밴드 상/하단 선 (회색)
    BB_MIDDLE = (50, 50, 50)         # 볼린저 밴드 중간 선 (진회색)
    BB_FILL = (200, 200, 200, 50)    # 볼린저 밴드 내부 채우기 (반투명 회색)

    MACD_HIST_UP = (0, 200, 0)       # MACD 히스토그램 양수 (초록)
    MACD_HIST_DOWN = (200, 0, 0)     # MACD 히스토그램 음수 (빨강)

    VOLUME_TICK = '#888888'      # 틱 거래량 기본 색상 (회색 계열)
    VOLUME_DEFAULT = '#0000aa'   # OHLC 없을 때 기본 거래량 색상 (파란색 계열)

    # ----- 작은 버튼 스타일 끝 ----- 

    # 차트 애플리케이션에서 사용하는 색상 상수 정의
    CHART_GRID = "#EEEEEE"
    REFERENCE_LINE = "#999999"  # 회색
    TOOLTIP_BACKGROUND = QColor(0, 0, 0, 220)  # 검정색 (알파값 220)
    TOOLTIP_TEXT = "#FFFFFF"  # 흰색

    # 차트 애플리케이션에서 사용하는 색상 상수 정의
    BOLLINGER_UPPER = "#DB4437"  # 상단밴드: 빨간색
    BOLLINGER_LOWER = "#4285F4"  # 하단밴드: 파란색
    BOLLINGER_FILL = QColor(200, 200, 255, 30)  # 밴드 채우기: 연한 파란색 (알파값 30)
    RSI = "#4285F4"  # 파란색
    RSI_OVERBOUGHT = "#DB4437"  # 과매수 영역: 빨간색
    RSI_OVERSOLD = "#0F9D58"  # 과매도 영역: 녹색
    MACD_HIST_POS = "#FF5252"  # 양수 히스토그램: 빨간색
    MACD_HIST_NEG = "#1E88E5"  # 음수 히스토그램: 파란색
    SMA_5 = "#4285F4"  # 파란색 (5일선)
    SMA_10 = "#0F9D58"  # 녹색 (10일선)
    SMA_20 = "#DB4437"  # 빨간색 (20일선)
    SMA_60 = "#673AB7"  # 보라색 (60일선)
    SMA_120 = "#795548"  # 갈색 (120일선)
    SMA_240 = "#000000"  # 검정색 (240일선)
    EMA_5 = "#4285F4"  # 파란색 (5일선)
    EMA_10 = "#0F9D58"  # 녹색 (10일선)
    EMA_20 = "#DB4437"  # 빨간색 (20일선)
    EMA_60 = "#673AB7"  # 보라색 (60일선)
    EMA_120 = "#795548"  # 갈색 (120일선)
    BOLLINGER_MID = "#000000"  # 중간선: 검정색
    MACD_SIGNAL = "#DB4437"  # 시그널선: 빨간색
    MACD_LINE = "#4285F4"  # MACD선: 파란색
    MACD_HIST_UP = "#FF5252"  # 양수 히스토그램: 빨간색
    MACD_HIST_DOWN = "#1E88E5"  # 음수 히스토그램: 파란색
    MACD_HIST_POS = "#FF5252"  # 양수 히스토그램: 빨간색
    MACD_HIST_NEG = "#1E88E5"  # 음수 히스토그램: 파란색
    RSI_OVER = "#DB4437"  # 과매수/과매도 기준선: 빨간색
    RSI_OVERBOUGHT = "#DB4437"  # 과매수 영역: 빨간색
    RSI_OVERSOLD = "#0F9D58"  # 과매도 영역: 녹색
    MACD_LINE = "#4285F4"  # MACD선: 파란색
    MACD_SIGNAL = "#DB4437"  # 시그널선: 빨간색
    MACD_HIST_POS = "#FF5252"  # 양수 히스토그램: 빨간색
    MACD_HIST_NEG = "#1E88E5"  # 음수 히스토그램: 파란색
    REFERENCE_LINE = "#999999"  # 회색
    TOOLTIP_BACKGROUND = QColor(0, 0, 0, 220)  # 검정색 (알파값 220)
    TOOLTIP_TEXT = "#FFFFFF"  # 흰색
    BOLLINGER_UPPER = "#DB4437"  # 상단밴드: 빨간색
    BOLLINGER_LOWER = "#4285F4"  # 하단밴드: 파란색
    BOLLINGER_FILL = QColor(200, 200, 255, 30)  # 밴드 채우기: 연한 파란색 (알파값 30)
    RSI = "#4285F4"  # 파란색
    RSI_OVERBOUGHT = "#DB4437"  # 과매수 영역: 빨간색
    RSI_OVERSOLD = "#0F9D58"  # 과매도 영역: 녹색
    MACD_LINE = "#4285F4"  # MACD선: 파란색
    MACD_SIGNAL = "#DB4437"  # 시그널선: 빨간색
    MACD_HIST_POS = "#FF5252"  # 양수 히스토그램: 빨간색
    MACD_HIST_NEG = "#1E88E5"  # 음수 히스토그램: 파란색
    REFERENCE_LINE = "#999999"  # 회색
    TOOLTIP_BACKGROUND = QColor(0, 0, 0, 220)  # 검정색 (알파값 220)
    TOOLTIP_TEXT = "#FFFFFF"  # 흰색
    BOLLINGER_UPPER = "#DB4437"  # 상단밴드: 빨간색
    BOLLINGER_LOWER = "#4285F4"  # 하단밴드: 파란색
    BOLLINGER_FILL = QColor(200, 200, 255, 30)  # 밴드 채우기: 연한 파란색 (알파값 30)
    RSI = "#4285F4"  # 파란색
    RSI_OVERBOUGHT = "#DB4437"  # 과매수 영역: 빨간색
    RSI_OVERSOLD = "#0F9D58"  # 과매도 영역: 녹색
    MACD_LINE = "#4285F4"  # MACD선: 파란색
    MACD_SIGNAL = "#DB4437"  # 시그널선: 빨간색
    MACD_HIST_POS = "#FF5252"  # 양수 히스토그램: 빨간색
    MACD_HIST_NEG = "#1E88E5"  # 음수 히스토그램: 파란색
    REFERENCE_LINE = "#999999"  # 회색
    TOOLTIP_BACKGROUND = QColor(0, 0, 0, 220)  # 검정색 (알파값 220)
    TOOLTIP_TEXT = "#FFFFFF"  # 흰색
    BOLLINGER_UPPER = "#DB4437"  # 상단밴드: 빨간색
    BOLLINGER_LOWER = "#4285F4"  # 하단밴드: 파란색
    BOLLINGER_FILL = QColor(200, 200, 255, 30)  # 밴드 채우기: 연한 파란색 (알파값 30)
    RSI = "#4285F4"  # 파란색
    RSI_OVERBOUGHT = "#DB4437"  # 과매수 영역: 빨간색
    RSI_OVERSOLD = "#0F9D58"  # 과매도 영역: 녹색
    MACD_LINE = "#4285F4"  # MACD선: 파란색
    MACD_SIGNAL = "#DB4437"  # 시그널선: 빨간색
    MACD_HIST_POS = "#FF5252"  # 양수 히스토그램: 빨간색
    MACD_HIST_NEG = "#1E88E5"  # 음수 히스토그램: 파란색
    REFERENCE_LINE = "#999999"  # 회색
    TOOLTIP_BACKGROUND = QColor(0, 0, 0, 220)  # 검정색 (알파값 220)
    TOOLTIP_TEXT = "#FFFFFF"  # 흰색
    BOLLINGER_UPPER = "#DB4437"  # 상단밴드: 빨간색
    BOLLINGER_LOWER = "#4285F4"  # 하단밴드: 파란색
    BOLLINGER_FILL = QColor(200, 200, 255, 30)  # 밴드 채우기: 연한 파란색 (알파값 30)
    RSI = "#4285F4"  # 파란색
    RSI_OVERBOUGHT = "#DB4437"  # 과매수 영역: 빨간색
    RSI_OVERSOLD = "#0F9D58"  # 과매도 영역: 녹색
    MACD_LINE = "#4285F4"  # MACD선: 파란색
    MACD_SIGNAL = "#DB4437"  # 시그널선: 빨간색
    MACD_HIST_POS = "#FF5252"  # 양수 히스토그램: 빨간색
    MACD_HIST_NEG = "#1E88E5"  # 음수 히스토그램: 파란색
    REFERENCE_LINE = "#999999"  # 회색
    TOOLTIP_BACKGROUND = QColor(0, 0, 0, 220)  # 검정색 (알파값 220)
    TOOLTIP_TEXT = "#FFFFFF"  # 흰색
    BOLLINGER_UPPER = "#DB4437"  # 상단밴드: 빨간색
    BOLLINGER_LOWER = "#4285F4"  # 하단밴드: 파란색
    BOLLINGER_FILL = QColor(200, 200, 255, 30)  # 밴드 채우기: 연한 파란색 (알파값 30)
    RSI = "#4285F4"  # 파란색
    RSI_OVERBOUGHT = "#DB4437"  # 과매수 영역: 빨간색
    RSI_OVERSOLD = "#0F9D58"  # 과매도 영역: 녹색
    MACD_LINE = "#4285F4"  # MACD선: 파란색
    MACD_SIGNAL = "#DB4437"  # 시그널선: 빨간색
    MACD_HIST_POS = "#FF5252"  # 양수 히스토그램: 빨간색
    MACD_HIST_NEG = "#1E88E5"  # 음수 히스토그램: 파란색
    REFERENCE_LINE = "#999999"  # 회색
    TOOLTIP_BACKGROUND = QColor(0, 0, 0, 220)  # 검정색 (알파값 220)
    TOOLTIP_TEXT = "#FFFFFF"  # 흰색
    BOLLINGER_UPPER = "#DB4437"  # 상단밴드: 빨간색
    BOLLINGER_LOWER = "#4285F4"  # 하단밴드: 파란색
    BOLLINGER_FILL = QColor(200, 200, 255, 30)  # 밴드 채우기: 연한 파란색 (알파값 30)