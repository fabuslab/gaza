"""
차트 관련 상수 정의
"""

# 보조지표 키-이름 매핑
INDICATOR_MAP = {
    'MA': '이동평균선',
    'BB': '볼린저밴드',
    'RSI': 'RSI',
    'MACD': 'MACD',
    'Volume': '거래량',
    'TradingValue': '거래대금'
}

# 이동평균선 기간 설정 (일봉 기준)
MA_PERIODS = {
    'D': [5, 10, 20, 60, 120, 240],  # 일봉: 5, 10, 20, 60, 120, 240일
    'W': [12, 26, 52],  # 주봉: 12, 26, 52주 (약 3개월, 6개월, 1년)
    'M': [3, 6, 12, 24, 60],  # 월봉: 3, 6, 12, 24, 60개월
    'T': [5, 10, 20, 60]   # 틱/분봉: 5, 10, 20, 60
}

# 볼린저밴드 설정
BOLLINGER_SETTINGS = {
    'length': 20,  # 기간
    'std_dev': 2.0  # 표준편차 배수
}

# RSI 설정
RSI_SETTINGS = {
    'length': 14,  # 기간
    'overbought': 70,  # 과매수 기준
    'oversold': 30    # 과매도 기준
}

# MACD 설정
MACD_SETTINGS = {
    'fast': 12,      # 단기 EMA
    'slow': 26,      # 장기 EMA
    'signal': 9      # 시그널 이동평균
}

# 주기별 캔들 기본 너비
CANDLE_WIDTH = {
    'D': 0.6,  # 일봉
    'W': 0.6,  # 주봉
    'M': 0.6,  # 월봉
    'T': 0.5   # 틱/분봉
}

# 기본 주기 코드
DEFAULT_PERIOD = 'D'  # 일봉

# 주기별 기본 데이터 개수
DEFAULT_DATA_COUNT = {
    'D': 100,  # 일봉
    'W': 52,   # 주봉
    'M': 36,   # 월봉
    'T': 100   # 틱/분봉
}

# 차트 그리드 스타일
GRID_STYLES = {
    'alpha': 0.3,    # 그리드 투명도
    'x_enabled': True,
    'y_enabled': True
}

# 보조지표 기본 위치 및 높이 설정
INDICATOR_AREAS = {
    'RSI': {
        'height': 100,   # 픽셀
        'position': 3    # 행 인덱스
    },
    'MACD': {
        'height': 100,   # 픽셀
        'position': 4    # 행 인덱스
    }
} 