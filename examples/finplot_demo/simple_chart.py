#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FinPlot 기반 일봉차트 데모 (간소화 버전)
"""
import sys
import numpy as np
import pandas as pd
import finplot as fplt
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QApplication

# 테스트 데이터 생성
def generate_test_data(days=100):
    """테스트용 OHLCV 데이터 생성"""
    end_date = datetime.now()
    dates = pd.date_range(end=end_date, periods=days, freq='B')
    
    # 초기 가격
    price = 50000
    data = []
    
    for i in range(days):
        # 전일 종가 기준 변동폭 계산
        if i > 0:
            price = data[i-1]['close']
            
        # OHLC 생성
        open_price = price * (1 + np.random.uniform(-0.015, 0.015))
        high_price = open_price * (1 + np.random.uniform(0, 0.03))
        low_price = open_price * (1 - np.random.uniform(0, 0.03))
        close_price = np.random.uniform(low_price, high_price)
        
        # 거래량
        volume = np.random.uniform(1000000, 5000000)
        
        data.append({
            'date': dates[i],
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df = df.set_index('date')
    
    # 이동평균선 계산
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    return df

def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 데이터 생성
    df = generate_test_data(days=100)
    
    # 윈도우/뷰포트 생성
    fplt.foreground = '#333'
    fplt.background = '#f6f6f6'
    fplt.candle_bull_color = '#fa2d01'  # 상승봉 색상 (한국식: 빨강)
    fplt.candle_bear_color = '#0b0eff'  # 하락봉 색상 (한국식: 파랑)
    fplt.volume_bull_color = '#ffa5a5'  # 상승 거래량 색상 (연한 빨강)
    fplt.volume_bear_color = '#a5a5ff'  # 하락 거래량 색상 (연한 파랑)
    
    # 1. 캔들차트 영역 생성
    ax = fplt.create_plot('삼성전자 (005930)', rows=2)
    
    # 2. 캔들스틱 차트 그리기
    fplt.candlestick_ochl(df[['open', 'close', 'high', 'low']], ax=ax)
    
    # 3. 이동평균선 추가
    fplt.plot(df['ma5'], legend='MA5', ax=ax, color='#ff9900')
    fplt.plot(df['ma20'], legend='MA20', ax=ax, color='#0099ff')
    fplt.plot(df['ma60'], legend='MA60', ax=ax, color='#9900ff')
    
    # 4. 거래량 차트 영역 생성
    ax_vol = ax.overlay()
    
    # 5. 하단 20%에 거래량 표시
    # 거래량 최대값을 기준으로 캔들차트 영역의 20%를 차지하도록 스케일링
    df['scaled_volume'] = df['volume'] * df['close'].max() * 0.2 / df['volume'].max()
    
    # 색상 결정 (종가 >= 시가: 빨강, 아니면 파랑)
    colors = np.where(df['close'] >= df['open'], fplt.volume_bull_color, fplt.volume_bear_color)
    
    # 거래량 바 그리기
    for i in range(len(df)):
        fplt.bar(df.index[i], df['scaled_volume'].iloc[i], ax=ax, color=colors[i], width=0.6)
    
    # 6. 매매 신호 예시 추가 (무작위 5개 위치)
    for _ in range(5):
        idx = np.random.randint(10, len(df)-10)
        price = df['close'].iloc[idx]
        signal_type = np.random.choice(['BUY', 'SELL', 'HOLD'])
        
        if signal_type == 'BUY':
            marker = '▲'
            color = '#00cc00'
            offset = 0.99
        elif signal_type == 'SELL':
            marker = '▼'
            color = '#cc0000'
            offset = 1.01
        else:  # HOLD
            marker = '■'
            color = '#888888'
            offset = 1.0
            
        # 마커 추가
        fplt.plot_marker(
            df.index[idx], 
            price * offset,
            marker=marker,
            color=color,
            size=11,
            ax=ax
        )
    
    # 7. 크로스헤어 및 범례 표시
    fplt.show_legend(ax)
    fplt.add_crosshair_info()
    
    # 8. 표시
    fplt.show()

if __name__ == "__main__":
    main() 