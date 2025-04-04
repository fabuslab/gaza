#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
깔끔한 캔들 차트 활용 예시
"""

import sys
import pandas as pd
import numpy as np
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QComboBox, QLabel
from PySide6.QtCore import Qt

# 직접 구현한 깔끔한 캔들 차트 임포트
from core.ui.components.clean_candle_chart import CleanCandleChart

class ChartExampleWindow(QMainWindow):
    """캔들 차트 예시 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("깔끔한 캔들 차트 예시")
        self.resize(1000, 600)
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 컨트롤 패널 생성
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        
        # 심볼 선택 콤보박스
        symbol_label = QLabel("종목:")
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["005930", "035720", "000660", "035420", "051910"])  # 예시 종목코드
        self.symbol_combo.currentTextChanged.connect(self.load_chart_data)
        
        # 기간 선택 콤보박스
        timeframe_label = QLabel("기간:")
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["D", "W", "M", "60min", "30min", "10min"])
        self.timeframe_combo.currentTextChanged.connect(self.load_chart_data)
        
        # 지표 버튼
        self.ma_button = QPushButton("이동평균선")
        self.ma_button.setCheckable(True)
        self.ma_button.clicked.connect(self.toggle_ma)
        
        self.bb_button = QPushButton("볼린저밴드")
        self.bb_button.setCheckable(True)
        self.bb_button.clicked.connect(self.toggle_bollinger)
        
        # 컨트롤 패널에 위젯 추가
        control_layout.addWidget(symbol_label)
        control_layout.addWidget(self.symbol_combo)
        control_layout.addWidget(timeframe_label)
        control_layout.addWidget(self.timeframe_combo)
        control_layout.addWidget(self.ma_button)
        control_layout.addWidget(self.bb_button)
        control_layout.addStretch()
        
        # 메인 레이아웃에 컨트롤 패널 추가
        main_layout.addWidget(control_panel)
        
        # 차트 생성
        self.chart = CleanCandleChart()
        main_layout.addWidget(self.chart)
        
        # 초기 데이터 로드
        self.load_chart_data()
    
    def load_chart_data(self):
        """차트 데이터 로드"""
        symbol = self.symbol_combo.currentText()
        timeframe = self.timeframe_combo.currentText()
        
        # 실제 애플리케이션에서는 API 또는 DB에서 데이터를 로드
        # 여기서는 예시 데이터 생성
        df = self.generate_sample_data(symbol, timeframe)
        
        # 차트 데이터 설정
        self.chart.set_data(df, symbol, timeframe)
        
        # 이전에 표시했던 지표 적용
        if self.ma_button.isChecked():
            self.toggle_ma(True)
        
        if self.bb_button.isChecked():
            self.toggle_bollinger(True)
    
    def generate_sample_data(self, symbol, timeframe):
        """샘플 차트 데이터 생성"""
        # 종목 코드에 따라 다른 시작 가격 설정
        base_price = int(symbol[1:4]) * 100 + 5000
        
        # 기간에 따라 다른 데이터 포인트 수 설정
        if timeframe == 'M':
            periods = 60
        elif timeframe == 'W':
            periods = 120
        elif timeframe == 'D':
            periods = 250
        else:
            periods = 300
        
        # 시작 날짜 설정
        if timeframe == 'D':
            start_date = pd.Timestamp.now() - pd.Timedelta(days=periods)
            date_range = pd.date_range(start=start_date, periods=periods, freq='B')
        elif timeframe == 'W':
            start_date = pd.Timestamp.now() - pd.Timedelta(weeks=periods)
            date_range = pd.date_range(start=start_date, periods=periods, freq='W')
        elif timeframe == 'M':
            start_date = pd.Timestamp.now() - pd.Timedelta(days=30*periods)
            date_range = pd.date_range(start=start_date, periods=periods, freq='M')
        else:
            # 분 단위 데이터
            minutes = int(timeframe.replace('min', ''))
            start_date = pd.Timestamp.now() - pd.Timedelta(minutes=minutes*periods)
            date_range = pd.date_range(start=start_date, periods=periods, freq=f'{minutes}min')
        
        # 가격 데이터 생성
        np.random.seed(int(symbol[-2:]))
        
        # 기본 추세와 랜덤 요소 결합
        trend = np.linspace(0, 20, periods) * (1 if np.random.random() > 0.5 else -1)
        noise = np.random.normal(0, 1, periods)
        price_changes = trend + noise * 5
        
        # 시작 가격으로부터 변동 계산
        closes = base_price + np.cumsum(price_changes)
        
        # OHLC 데이터 생성
        highs = closes + np.random.uniform(10, 50, periods)
        lows = closes - np.random.uniform(10, 50, periods)
        opens = np.roll(closes, 1)
        opens[0] = base_price
        
        # 거래량 생성
        volumes = np.random.uniform(50000, 500000, periods)
        volumes = volumes * (1 + 0.5 * np.sin(np.linspace(0, 10, periods)))
        volumes = volumes.astype(int)
        
        # 데이터프레임 생성
        df = pd.DataFrame({
            'Open': opens,
            'High': highs,
            'Low': lows,
            'Close': closes,
            'Volume': volumes
        }, index=date_range)
        
        return df
    
    def toggle_ma(self, checked=None):
        """이동평균선 표시/숨김 전환"""
        if checked is None:
            checked = self.ma_button.isChecked()
        
        # 다양한 기간의 이동평균선 추가/제거
        self.chart.toggle_moving_average(5, checked)
        self.chart.toggle_moving_average(20, checked)
        self.chart.toggle_moving_average(60, checked)
    
    def toggle_bollinger(self, checked=None):
        """볼린저 밴드 표시/숨김 전환"""
        if checked is None:
            checked = self.bb_button.isChecked()
        
        self.chart.toggle_bollinger_bands(checked)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChartExampleWindow()
    window.show()
    sys.exit(app.exec()) 