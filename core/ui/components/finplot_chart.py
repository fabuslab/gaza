#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
finplot 기반 고성능 차트 컴포넌트
"""

import logging
import finplot as fplt
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFrame
from PySide6.QtCore import Qt, Slot as pyqtSlot, Signal as pyqtSignal

logger = logging.getLogger(__name__)

# 표준 캔들 색상 정의 (한국 시장 관행에 맞춤)
CANDLE_UP_COLOR = '#ff0000'     # 상승 캔들 색상 (빨강)
CANDLE_DOWN_COLOR = '#0000ff'   # 하락 캔들 색상 (파랑)
VOLUME_UP_COLOR = '#ff8888'     # 상승 거래량 색상 (연한 빨강)
VOLUME_DOWN_COLOR = '#8888ff'   # 하락 거래량 색상 (연한 파랑)

# 이동평균선 색상
MA_COLORS = {
    5: '#ff9900',   # 5일 이평선 (주황)
    20: '#0099ff',  # 20일 이평선 (파랑)
    60: '#9900ff'   # 60일 이평선 (보라)
}

class FinPlotChartComponent(QWidget):
    """finplot 라이브러리를 이용한 고성능 차트 컴포넌트"""

    # 시그널 정의
    chart_loaded = pyqtSignal(bool)  # 데이터 로딩 완료/실패 시그널
    
    def __init__(self, chart_module, parent=None):
        super().__init__(parent)
        self.chart_module = chart_module  # ChartModule 참조 저장
        self.current_stock_code: Optional[str] = None
        self.current_period: str = 'D'
        self.chart_data: pd.DataFrame = pd.DataFrame()
        
        # finplot 관련 객체 저장
        self.ax_candle = None      # 캔들차트 축
        self.ax_volume = None      # 거래량 축
        self.plots = {}            # 플롯 객체 저장
        self.ma_plots = {}         # 이동평균선 플롯 저장
        
        # 최신 데이터 저장
        self.latest_tick_data: Optional[Dict] = None

        self._init_ui()
        logger.info("새 FinPlotChartComponent 초기화 완료.")

    def _init_ui(self):
        """UI 초기화"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # finplot 위젯을 담을 프레임 생성
        self.chart_frame = QFrame(self)
        self.chart_frame.setFrameShape(QFrame.StyledPanel)
        self.layout.addWidget(self.chart_frame)
        
        # 기본 스타일 설정
        fplt.background = '#f0f0f0'          # 배경색
        fplt.foreground = '#333333'          # 전경색
        fplt.cross_hair_color = '#777777aa'  # 크로스헤어 색상
        fplt.volume_bull_color = VOLUME_UP_COLOR   # 상승 거래량 색상
        fplt.volume_bear_color = VOLUME_DOWN_COLOR # 하락 거래량 색상
        fplt.candle_bull_body_color = CANDLE_UP_COLOR  # 상승 캔들 바디 색상
        fplt.candle_bear_body_color = CANDLE_DOWN_COLOR  # 하락 캔들 바디 색상
        
        logger.info("FinPlotChartComponent UI 초기화 완료")

    def _create_plot(self):
        """finplot 차트 생성"""
        # 기존 차트 정리
        if hasattr(self, 'win'):
            fplt.close()
        
        # 새 차트 생성
        self.win = fplt.create_plot_widget(self.chart_frame)
        self.layout.addWidget(self.win)
        
        # 차트 분할 (캔들차트 70%, 거래량 30%)
        self.ax_candle = fplt.create_plot(init_zoom_periods=100)  # 초기 100봉 표시
        self.ax_volume = fplt.create_plot(init_zoom_periods=100, rows=1)
        
        # Y축 및 그리드 설정
        self.ax_candle.set_visible(xaxis=True, yaxis=True, xgrid=True, ygrid=True)
        self.ax_volume.set_visible(xaxis=False, yaxis=True, xgrid=True, ygrid=True)
        
        # X축 연결
        self.ax_volume.link_x_axis(self.ax_candle)
        
        # 레이아웃 설정 (거래량은 캔들의 30% 크기)
        fplt.set_row_heights(30)
        
        logger.info("finplot 차트 생성 완료")

    @pyqtSlot(str, str, pd.DataFrame)
    def update_chart(self, stock_code: str, period: str, df: pd.DataFrame):
        """수신된 데이터와 주기로 차트 업데이트"""
        logger.info(f"차트 업데이트 수신: {stock_code}, 주기={period}, 데이터 {len(df)}개")
        
        # 데이터 저장
        self.chart_data = df
        self.current_stock_code = stock_code
        self.current_period = period

        # 빈 데이터 체크
        if df.empty:
            logger.warning("업데이트할 데이터 없음. 차트 클리어.")
            self.chart_loaded.emit(False)
            return

        try:
            # 차트 생성
            self._create_plot()
            
            # 데이터 준비
            # 이미 정렬되어 있는지 확인
            if 'ordinal' in df.columns:
                df = df.sort_values('ordinal')
            elif not df.index.is_monotonic_increasing:
                df = df.sort_index()
            
            # OHLC 데이터 체크
            has_ohlc = all(col in df.columns for col in ['Open', 'High', 'Low', 'Close'])
            
            # X축 데이터 설정 - ordinal 값 또는 인덱스 
            if 'ordinal' in df.columns:
                x_data = df['ordinal'].values
            else:
                # 날짜/시간 인덱스를 숫자로 변환
                x_data = np.arange(len(df))
            
            # 날짜 인덱스 포맷 설정
            if pd.api.types.is_datetime64_any_dtype(df.index):
                if period == 'D':
                    fplt.set_time_inspector(lambda x, _: df.index[int(x)].strftime('%Y-%m-%d') if 0 <= int(x) < len(df) else '')
                elif period == 'W':
                    fplt.set_time_inspector(lambda x, _: df.index[int(x)].strftime('%Y-%m-%d (주)') if 0 <= int(x) < len(df) else '')
                elif period == 'M':
                    fplt.set_time_inspector(lambda x, _: df.index[int(x)].strftime('%Y-%m') if 0 <= int(x) < len(df) else '')
                elif period == 'Y':
                    fplt.set_time_inspector(lambda x, _: df.index[int(x)].strftime('%Y') if 0 <= int(x) < len(df) else '')
                elif period.isdigit(): # 분봉
                    fplt.set_time_inspector(lambda x, _: df.index[int(x)].strftime('%Y-%m-%d %H:%M') if 0 <= int(x) < len(df) else '')
                elif period.endswith('T'): # 틱
                    fplt.set_time_inspector(lambda x, _: df.index[int(x)].strftime('%Y-%m-%d %H:%M:%S') if 0 <= int(x) < len(df) else '')
            
            # 캔들스틱 또는 라인 차트 그리기
            if has_ohlc:
                # 데이터 타입 변환 확인
                for col in ['Open', 'High', 'Low', 'Close']:
                    if not pd.api.types.is_numeric_dtype(df[col]):
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # 캔들스틱 차트 데이터 준비
                candle_data = np.array([
                    x_data,                     # X 값 (ordinal)
                    df['Open'].values,          # 시가
                    df['Close'].values,         # 종가
                    df['High'].values,          # 고가
                    df['Low'].values            # 저가
                ])
                
                # 캔들스틱 차트 그리기
                fplt.candlestick_ochl(
                    candle_data, 
                    ax=self.ax_candle,
                    bull_color=CANDLE_UP_COLOR,
                    bear_color=CANDLE_DOWN_COLOR
                )
                
                # 이동평균선 추가
                for period, color in MA_COLORS.items():
                    if len(df) > period:
                        ma = df['Close'].rolling(period).mean()
                        if not ma.isna().all():  # 모든 값이 NaN이 아닌 경우에만 그리기
                            self.ma_plots[period] = fplt.plot(
                                x_data, ma.values,
                                ax=self.ax_candle, 
                                legend=f'MA{period}',
                                color=color, 
                                width=1.5
                            )
            else:
                # 종가만 있는 경우 라인 차트 그리기
                if 'Close' in df.columns:
                    if not pd.api.types.is_numeric_dtype(df['Close']):
                        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
                    
                    fplt.plot(
                        x_data, df['Close'].values,
                        ax=self.ax_candle, 
                        legend='종가', 
                        color='#333333'
                    )
            
            # 거래량 차트 그리기
            if 'Volume' in df.columns:
                # 데이터 타입 확인
                if not pd.api.types.is_numeric_dtype(df['Volume']):
                    df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')
                
                if df['Volume'].sum() > 0:  # 거래량이 있는 경우에만 그리기
                    # 상승/하락 색상 구분
                    volume_colors = np.where(
                        df['Close'].values >= df['Open'].values if has_ohlc else np.zeros(len(df)),
                        VOLUME_UP_COLOR,
                        VOLUME_DOWN_COLOR
                    )
                    
                    fplt.volume_ocv(
                        candle_data if has_ohlc else np.array([x_data, np.zeros(len(df)), df['Volume'].values]),
                        ax=self.ax_volume,
                        colorfunc=lambda i: volume_colors[int(i)]
                    )
            
            # 차트 제목 설정
            self.ax_candle.set_title(f"{stock_code} - {period}봉")
            
            # 크로스헤어 및 범례 설정
            fplt.add_crosshair_info()
            fplt.show_legend(self.ax_candle)
            
            # Y축 범위 조정 및 새로고침
            fplt.refresh()
            
            logger.info(f"{stock_code} 차트 그리기 완료")
            self.chart_loaded.emit(True)
            
        except Exception as e:
            logger.error(f"차트 그리기 중 오류: {e}", exc_info=True)
            self.chart_loaded.emit(False)

    def clear_chart(self):
        """차트의 모든 아이템 제거"""
        try:
            # finplot 차트 초기화
            fplt.close()
            self.chart_data = pd.DataFrame()
            logger.debug("차트 클리어 완료")
        except Exception as e:
            logger.error(f"차트 클리어 중 오류: {e}")

    @pyqtSlot(str, dict)
    def update_latest_data(self, stock_code: str, data: dict):
        """실시간 데이터 수신 시 내부 변수 업데이트"""
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
            
            # 필요시 여기에 실시간 차트 업데이트 로직 추가 가능
            
            logger.debug(f"실시간 데이터 업데이트: {stock_code}, 가격={price:,.0f}")
        except Exception as e:
            logger.error(f"실시간 데이터 업데이트 중 오류: {e}")

    def add_trade_signal(self, timestamp, signal_type, price, additional_info=None):
        """매매 신호 표시 추가
        
        Args:
            timestamp: 신호 시간 (datetime 객체 또는 x축 위치)
            signal_type: 'BUY', 'SELL', 'HOLD' 중 하나
            price: 매매 가격
            additional_info: 추가 정보 (툴팁에 표시될 내용)
        """
        if self.ax_candle is None or self.chart_data.empty:
            logger.warning("차트가 준비되지 않아 매매 신호를 표시할 수 없습니다.")
            return
            
        try:
            # 날짜/시간 타입이라면 해당 x 위치 찾기
            if isinstance(timestamp, (datetime, pd.Timestamp)):
                if pd.api.types.is_datetime64_any_dtype(self.chart_data.index):
                    # 가장 가까운 인덱스 찾기
                    nearest_idx = self.chart_data.index.get_indexer([timestamp], method='nearest')[0]
                    if nearest_idx >= 0 and nearest_idx < len(self.chart_data):
                        if 'ordinal' in self.chart_data.columns:
                            x_pos = self.chart_data['ordinal'].iloc[nearest_idx]
                        else:
                            x_pos = nearest_idx
                    else:
                        logger.warning(f"매매 신호 시간({timestamp})에 해당하는 데이터를 찾을 수 없습니다.")
                        return
                else:
                    logger.warning("차트 데이터의 인덱스가 날짜/시간 타입이 아닙니다.")
                    return
            else:
                # 직접 x 위치 지정된 경우
                x_pos = timestamp
            
            # 신호 유형별 마커 및 색상 설정
            if signal_type.upper() == 'BUY':
                marker = '▲'  # 상향 화살표
                color = '#00cc00'  # 녹색
                offset_factor = 0.995  # 가격보다 살짝 아래에 표시
                size = 12
                text = 'BUY'
            elif signal_type.upper() == 'SELL':
                marker = '▼'  # 하향 화살표
                color = '#cc0000'  # 적색
                offset_factor = 1.005  # 가격보다 살짝 위에 표시
                size = 12
                text = 'SELL'
            elif signal_type.upper() == 'HOLD':
                marker = '■'  # 사각형
                color = '#888888'  # 회색
                offset_factor = 1.0  # 가격과 같은 위치
                size = 8
                text = 'HOLD'
            else:
                logger.warning(f"알 수 없는 신호 유형: {signal_type}")
                return
            
            # 매매 신호 마커 추가
            marker_plot = fplt.plot_marker(
                x_pos, price * offset_factor,
                ax=self.ax_candle,
                marker=marker,
                color=color,
                size=size,
                text=text
            )
            
            # 추가 정보가 있으면 툴팁으로 표시
            if additional_info:
                # 근처에 마우스가 가면 추가 정보 표시하는 기능은
                # 현재 finplot에서 직접 지원하지 않음
                # 대신 라벨을 추가할 수 있음
                fplt.add_text(
                    (x_pos, price * offset_factor),
                    additional_info,
                    ax=self.ax_candle,
                    color=color,
                    size=8
                )
                
            # 변경사항 적용
            fplt.refresh()
            logger.info(f"매매 신호 추가: {signal_type}, 위치={x_pos}, 가격={price}")
            
            return marker_plot  # 나중에 제거할 때 사용할 수 있도록 반환
            
        except Exception as e:
            logger.error(f"매매 신호 표시 중 오류: {e}", exc_info=True)
            return None
            
    def add_ai_analysis_marker(self, timestamp, text, icon='ℹ', color='#0088ff'):
        """AI 분석 마커 추가 (정보 아이콘 표시)
        
        Args:
            timestamp: 마커 시간 (datetime 객체 또는 x축 위치)
            text: 표시할 분석 내용
            icon: 표시할 아이콘 문자
            color: 아이콘 색상
        """
        if self.ax_candle is None or self.chart_data.empty:
            logger.warning("차트가 준비되지 않아 AI 분석 마커를 표시할 수 없습니다.")
            return
            
        try:
            # 날짜/시간 타입이라면 해당 x 위치 찾기
            if isinstance(timestamp, (datetime, pd.Timestamp)):
                if pd.api.types.is_datetime64_any_dtype(self.chart_data.index):
                    # 가장 가까운 인덱스 찾기
                    nearest_idx = self.chart_data.index.get_indexer([timestamp], method='nearest')[0]
                    if nearest_idx >= 0 and nearest_idx < len(self.chart_data):
                        if 'ordinal' in self.chart_data.columns:
                            x_pos = self.chart_data['ordinal'].iloc[nearest_idx]
                        else:
                            x_pos = nearest_idx
                            
                        # Y 위치 계산 (해당 지점의 고가보다 약간 위에)
                        if 'High' in self.chart_data.columns:
                            y_pos = self.chart_data['High'].iloc[nearest_idx] * 1.01
                        elif 'Close' in self.chart_data.columns:
                            y_pos = self.chart_data['Close'].iloc[nearest_idx] * 1.01
                        else:
                            # Y 위치 정보가 없는 경우, 현재 보이는 Y축 범위의 상단 근처
                            view_rect = self.ax_candle.viewRect()
                            y_pos = view_rect.bottom() + (view_rect.height() * 0.9)
                    else:
                        logger.warning(f"AI 분석 마커 시간({timestamp})에 해당하는 데이터를 찾을 수 없습니다.")
                        return
                else:
                    logger.warning("차트 데이터의 인덱스가 날짜/시간 타입이 아닙니다.")
                    return
            else:
                # 직접 x 위치 지정된 경우
                x_pos = timestamp
                
                # Y 위치는 현재 보이는 Y축 범위의 상단 근처로 설정
                view_rect = self.ax_candle.viewRect()
                y_pos = view_rect.bottom() + (view_rect.height() * 0.9)
            
            # 정보 아이콘 마커 추가
            info_marker = fplt.plot_marker(
                x_pos, y_pos,
                ax=self.ax_candle,
                marker=icon,  # 정보 아이콘
                color=color,  # 파란색
                size=10,
                text=text
            )
            
            # 변경사항 적용
            fplt.refresh()
            logger.info(f"AI 분석 마커 추가: {text[:20]}... 위치={x_pos}")
            
            return info_marker  # 나중에 제거할 때 사용할 수 있도록 반환
            
        except Exception as e:
            logger.error(f"AI 분석 마커 표시 중 오류: {e}", exc_info=True)
            return None

    def toggle_indicator(self, indicator_code: str, checked: bool):
        """보조지표 표시/숨김 토글"""
        logger.info(f"보조지표 토글: {indicator_code}={checked}")
        
        # 차트가 준비되지 않았으면 나중에 처리하도록 상태만 저장
        if self.chart_data.empty or self.ax_candle is None:
            logger.warning(f"차트가 준비되지 않아 보조지표 토글을 적용할 수 없습니다: {indicator_code}")
            return
            
        try:
            # 거래량 차트 처리
            if indicator_code == 'Volume':
                if hasattr(self, 'ax_volume') and self.ax_volume is not None:
                    # 거래량 차트 표시/숨김
                    self.ax_volume.show() if checked else self.ax_volume.hide()
                    # 레이아웃 업데이트
                    fplt.refresh()
                return
                
            # 이동평균선 처리
            if indicator_code == 'MA':
                # 각 이동평균선 표시/숨김 처리
                for period, plot in self.ma_plots.items():
                    if plot is not None:
                        plot.show() if checked else plot.hide()
                # 레이아웃 업데이트
                fplt.refresh()
                return
                
            # 필요에 따라 다른 지표(RSI, MACD 등) 추가 가능
            # 예: RSI 지표
            if indicator_code == 'RSI':
                # RSI 지표가 없으면 계산해서 추가
                if 'RSI' not in self.plots and checked:
                    if 'Close' in self.chart_data.columns and len(self.chart_data) > 14:
                        # RSI 계산 (pandas-ta 라이브러리 필요)
                        try:
                            import pandas_ta as ta
                            rsi = ta.rsi(self.chart_data['Close'], length=14)
                            
                            # RSI용 서브플롯 생성
                            ax_rsi = fplt.create_plot(init_zoom_periods=100, rows=1)
                            ax_rsi.set_visible(xaxis=False, yaxis=True, xgrid=True, ygrid=True)
                            ax_rsi.link_x_axis(self.ax_candle)
                            ax_rsi.setMaximumHeight(150)  # 높이 설정
                            
                            # RSI 플롯 추가
                            self.plots['RSI'] = fplt.plot(
                                rsi, 
                                ax=ax_rsi, 
                                legend='RSI(14)',
                                color='#ff5900'
                            )
                            
                            # 50 기준선 추가
                            fplt.add_band(30, 70, ax=ax_rsi, color='#6335')
                            fplt.hline(50, ax=ax_rsi, color='#6399')
                            
                            # RSI 축 설정
                            ax_rsi.set_label('RSI')
                            ax_rsi.set_range(0, 100)
                            
                            fplt.refresh()
                        except ImportError:
                            logger.error("pandas_ta 라이브러리가 설치되지 않아 RSI를 계산할 수 없습니다.")
                        except Exception as e:
                            logger.error(f"RSI 계산 중 오류: {e}", exc_info=True)
                # 기존 RSI 표시/숨김
                elif 'RSI' in self.plots:
                    self.plots['RSI'].show() if checked else self.plots['RSI'].hide()
                    fplt.refresh()
                    
                return
                
            # MACD 지표
            if indicator_code == 'MACD':
                # MACD 지표가 없으면 계산해서 추가
                if 'MACD' not in self.plots and checked:
                    if 'Close' in self.chart_data.columns and len(self.chart_data) > 26:
                        # MACD 계산 (pandas-ta 라이브러리 필요)
                        try:
                            import pandas_ta as ta
                            macd = ta.macd(self.chart_data['Close'])
                            
                            # MACD용 서브플롯 생성
                            ax_macd = fplt.create_plot(init_zoom_periods=100, rows=1)
                            ax_macd.set_visible(xaxis=False, yaxis=True, xgrid=True, ygrid=True)
                            ax_macd.link_x_axis(self.ax_candle)
                            ax_macd.setMaximumHeight(150)  # 높이 설정
                            
                            # MACD 선 플롯
                            self.plots['MACD'] = fplt.plot(
                                macd['MACD_12_26_9'], 
                                ax=ax_macd, 
                                legend='MACD',
                                color='#0077ff'
                            )
                            
                            # 시그널 선 플롯
                            self.plots['MACD_signal'] = fplt.plot(
                                macd['MACDs_12_26_9'], 
                                ax=ax_macd, 
                                legend='Signal',
                                color='#ff0000'
                            )
                            
                            # 히스토그램 플롯
                            hist = macd['MACDh_12_26_9']
                            colors = np.where(hist >= 0, '#00aa00', '#cc0000')
                            fplt.bar(hist, ax=ax_macd, width=0.8, color=colors)
                            
                            # MACD 축 설정
                            ax_macd.set_label('MACD')
                            
                            fplt.refresh()
                        except ImportError:
                            logger.error("pandas_ta 라이브러리가 설치되지 않아 MACD를 계산할 수 없습니다.")
                        except Exception as e:
                            logger.error(f"MACD 계산 중 오류: {e}", exc_info=True)
                # 기존 MACD 표시/숨김
                elif 'MACD' in self.plots:
                    self.plots['MACD'].show() if checked else self.plots['MACD'].hide()
                    if 'MACD_signal' in self.plots:
                        self.plots['MACD_signal'].show() if checked else self.plots['MACD_signal'].hide()
                    fplt.refresh()
                    
                return
                
            # 나머지 지표들에 대한 처리 (필요에 따라 추가)
            logger.warning(f"아직 구현되지 않은 보조지표: {indicator_code}")
            
        except Exception as e:
            logger.error(f"보조지표 토글 중 오류: {e}", exc_info=True)

    def cleanup(self):
        """컴포넌트 정리"""
        try:
            # finplot 차트 정리
            fplt.close()
            logger.info(f"FinPlotChartComponent 정리 완료: {self.current_stock_code}")
        except Exception as e:
            logger.error(f"FinPlotChartComponent 정리 중 오류: {e}") 