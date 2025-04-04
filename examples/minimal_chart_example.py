#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
최소한의 코드로 구현된 깔끔한 캔들 차트 예시
"""

import sys
import pandas as pd
import numpy as np
from PySide6.QtWidgets import QApplication, QMainWindow
from core.ui.components.clean_candle_chart import CleanCandleChart

def create_sample_data():
    """샘플 OHLCV 데이터 생성"""
    # 날짜 범위 생성 (최근 100일)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='B')
    
    # 시작 가격
    base_price = 10000
    
    # 랜덤 가격 변동 생성
    np.random.seed(42)  # 재현 가능한 결과를 위한 시드 설정
    changes = np.random.normal(0, 100, 100)  # 평균 0, 표준편차 100의 정규분포
    
    # 종가 계산
    closes = base_price + np.cumsum(changes)
    
    # OHLC 생성
    highs = closes + np.random.uniform(0, 100, 100)
    lows = closes - np.random.uniform(0, 100, 100)
    opens = np.roll(closes, 1)
    opens[0] = base_price
    
    # 거래량 생성
    volumes = np.random.randint(100000, 1000000, 100)
    
    # 데이터프레임 생성
    df = pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes
    }, index=dates)
    
    return df

class SimpleChartWindow(QMainWindow):
    """최소한의 차트 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("간단한 캔들차트")
        self.resize(800, 600)
        
        # 차트 생성
        self.chart = CleanCandleChart(self)
        self.setCentralWidget(self.chart)
        
        # 샘플 데이터 로드
        data = create_sample_data()
        self.chart.set_data(data, "샘플", "D")
        
        # 이동평균선과 볼린저 밴드 표시
        self.chart.add_moving_average(5)  # 5일 이동평균선
        self.chart.add_moving_average(20)  # 20일 이동평균선
        self.chart.add_bollinger_bands()  # 볼린저 밴드 (기본값: 20일, 2시그마)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimpleChartWindow()
    window.show()
    sys.exit(app.exec()) 