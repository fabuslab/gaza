"""
차트 데이터 로딩, 처리, 실시간 업데이트 담당 모듈
"""

import logging
import time
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from PySide6.QtCore import QObject, Signal as pyqtSignal, QTimer, Slot as pyqtSlot
from datetime import datetime, timedelta

from core.api.kiwoom import KiwoomAPI
# pandas_ta 모듈 임포트 오류 방지를 위한 수정
try:
    from core.utils.indicators import calculate_indicators
    print("indicators 모듈 임포트 성공")
except ImportError as e:
    print(f"indicators 모듈 임포트 실패: {e}")
    # 임시 대체 기능 정의
    def calculate_indicators(df):
        print("기본 지표 계산 함수 사용 (indicators 모듈 로드 실패)")
        if 'Close' in df.columns and 'Volume' in df.columns:
            df['TradingValue'] = df['Close'] * df['Volume']
        return df

logger = logging.getLogger(__name__)

# API 호출 관련 설정 (필요시 조정)
DEFAULT_DATA_COUNT = 100 # 기본 로드 개수 변경 (3000 -> 100)
REALTIME_INTERVAL_MS = 1000 # 실시간 데이터 조회 간격 (ms)

class ChartModule(QObject):
    """차트 데이터 관리 및 제공 모듈 (pyqtgraph 기반)"""

    # 시그널 정의:
    # chart_updated: 전체 차트 데이터 업데이트 시 발생 (과거 데이터 로드, 주기 변경 등)
    #   - str: 종목 코드
    #   - str: 주기
    #   - pd.DataFrame: OHLCV 및 계산된 보조지표 포함 DataFrame (DatetimeIndex)
    chart_updated = pyqtSignal(str, str, pd.DataFrame)
    
    # latest_data_updated: 실시간 데이터(틱 또는 현재가) 업데이트 시 발생
    #   - str: 종목 코드
    #   - dict: 최신 데이터 딕셔너리 (예: {'time': timestamp, 'price': 10000, 'volume': 10})
    latest_data_updated = pyqtSignal(str, dict)

    def __init__(self, kiwoom_api: KiwoomAPI):
        super().__init__()
        self.kiwoom_api = kiwoom_api
        self.current_stock_code: Optional[str] = None
        self.current_period: str = 'D'
        self.chart_data: pd.DataFrame = pd.DataFrame() # 현재 로드된 전체 데이터
        
        self.realtime_timer = QTimer(self)
        self.realtime_timer.setInterval(REALTIME_INTERVAL_MS)
        self.realtime_timer.timeout.connect(self._request_realtime_data)
        
        self.is_loading = False # 데이터 로딩 중 플래그
        
        logger.info("새 ChartModule 초기화 완료.")

    @pyqtSlot(str, str, int)
    def load_chart_data(self, stock_code: str, period: str, count: Optional[int] = None):
        """지정된 종목과 주기의 차트 데이터를 로드하고 시그널을 발생시킵니다."""
        if self.is_loading:
            logger.warning(f"이미 데이터 로딩 중입니다 ({self.current_stock_code} {self.current_period}). 요청 무시: {stock_code} {period}")
            return

        logger.info(f"차트 데이터 로드 시작: {stock_code}, 주기={period}, 개수={count or '기본'}")
        self.is_loading = True
        self.current_stock_code = stock_code
        self.current_period = period
        if self.realtime_timer.isActive():
            self.realtime_timer.stop()

        try:
            data_count = count if count is not None else DEFAULT_DATA_COUNT
            ohlcv_data = None 
            column_map = {} # API 응답과 표준 컬럼명 매핑용

            # --- KiwoomAPI 호출 로직 --- 
            if not self.kiwoom_api or not hasattr(self.kiwoom_api, 'chart') or not self.kiwoom_api.chart:
                logger.error("KiwoomChartAPI가 초기화되지 않았습니다.")
                self.is_loading = False
                # 오류 시 빈 데이터프레임으로 시그널 발생
                self.chart_updated.emit(stock_code, period, pd.DataFrame())
                return
                
            # --- 현재 날짜 가져오기 (YYYYMMDD 형식) ---
            current_date_str = (datetime.now() + timedelta(days=1)).strftime('%Y%m%d')
            logger.debug(f"차트 기준일자(base_dt)를 내일({current_date_str})로 설정하여 조회합니다.")
            # ---

            # 주기에 따라 실제 API 메소드 호출
            if period in ['D', 'W', 'M', 'Y']:
                logger.debug(f"KiwoomChartAPI.get_stock_ohlcv_chart 호출 ({stock_code}, {period}, {current_date_str}, {data_count})") # 로깅 강화 (날짜 포함)
                # 수정: 하드코딩된 날짜 대신 current_date_str 사용
                ohlcv_data = self.kiwoom_api.chart.get_stock_ohlcv_chart(stock_code, period, current_date_str, data_count)
                column_map = {'time_col': 'dt', 'time_format': '%Y%m%d', 'open_col': 'open_pric', 'high_col': 'high_pric', 'low_col': 'low_pric', 'close_col': 'cur_prc', 'volume_col': 'trde_qty'}
            elif period.isdigit():
                logger.debug(f"KiwoomChartAPI.get_stock_minute_chart 호출 ({stock_code}, {period}, {data_count})") # 로깅 강화
                ohlcv_data = self.kiwoom_api.chart.get_stock_minute_chart(stock_code, period, data_count)
                column_map = {'time_col': 'cntr_tm', 'time_format': '%Y%m%d%H%M%S', 'open_col': 'open_pric', 'high_col': 'high_pric', 'low_col': 'low_pric', 'close_col': 'cur_prc', 'volume_col': 'trde_qty'}
            elif period.endswith('T'):
                tick_scope = period[:-1]
                logger.debug(f"KiwoomChartAPI.get_stock_tick_chart 호출 ({stock_code}, {tick_scope}, {data_count})") # 로깅 강화
                ohlcv_data = self.kiwoom_api.chart.get_stock_tick_chart(stock_code, tick_scope, data_count)
                # 틱 데이터에 맞는 컬럼 맵 - OHLC 제외
                column_map = {'time_col': 'cntr_tm', 'time_format': '%Y%m%d%H%M%S', 'close_col': 'cur_prc', 'volume_col': 'trde_qty'}

                # --- 로깅 추가: 틱 데이터 수신 확인 ---
                logger.debug(f"틱 API 호출 결과 수신 ({stock_code}, {period}): Type={type(ohlcv_data)}, Length={len(ohlcv_data) if isinstance(ohlcv_data, list) else 'N/A'}")
                if isinstance(ohlcv_data, list) and ohlcv_data:
                    logger.debug(f"수신된 첫 틱 데이터 항목 예시: {ohlcv_data[0]}")
                # --- 로깅 추가 끝 ---

            else:
                 logger.error(f"지원하지 않는 주기: {period}")
                 self.is_loading = False
                 self.chart_updated.emit(stock_code, period, pd.DataFrame())
                 return
            # --- API 호출 로직 끝 ---

            if ohlcv_data is None: # API 호출 실패
                 logger.error(f"API로부터 {stock_code} ({period}) 데이터 수신 실패 (None 반환)")
                 ohlcv_data = [] # 빈 리스트로 처리
                 
            if not ohlcv_data:
                logger.warning(f"API로부터 {stock_code} ({period}) 데이터 수신 결과 없음.")
                self.chart_data = pd.DataFrame()
                self.chart_updated.emit(stock_code, period, self.chart_data)
                if period.endswith('T') and REALTIME_INTERVAL_MS > 0:
                     self.realtime_timer.start()
                     logger.info(f"{stock_code} 틱 데이터 실시간 조회 시작 (빈 데이터, 주기: {REALTIME_INTERVAL_MS}ms)")
                self.is_loading = False
                return

            # --- DataFrame 변환 및 보조지표 계산 --- 
            try:
                df = pd.DataFrame(ohlcv_data)
                time_col = column_map.get('time_col')
                time_format = column_map.get('time_format')
                open_col = column_map.get('open_col')
                high_col = column_map.get('high_col')
                low_col = column_map.get('low_col')
                close_col = column_map.get('close_col')
                volume_col = column_map.get('volume_col')
                
                if not time_col or time_col not in df.columns: raise ValueError(f"필수 시간 컬럼 '{time_col}' ({time_col=}) 없음. 사용 가능 컬럼: {df.columns.tolist()}") # 오류 메시지 개선
                if not close_col or close_col not in df.columns: raise ValueError(f"필수 종가 컬럼 '{close_col}' 없음")
                if not volume_col or volume_col not in df.columns: raise ValueError(f"필수 거래량 컬럼 '{volume_col}' 없음")

                logger.debug(f"Raw DataFrame shape before datetime conversion: {df.shape}") # Log shape
                logger.debug(f"Raw DataFrame head:\n{df.head().to_string()}") # Log head
                logger.debug(f"Attempting to convert time column '{time_col}' using format '{time_format}'") # 변환 시도 로그

                df['Date'] = pd.to_datetime(df[time_col], format=time_format, errors='coerce')
                # --- 추가: 시간대 정보(KST) 설정 및 상세 로깅 ---
                try:
                    # NaT가 아닌 유효한 날짜에 대해서만 시간대 설정
                    valid_dates = df['Date'].notna()
                    df.loc[valid_dates, 'Date'] = df.loc[valid_dates, 'Date'].dt.tz_localize('Asia/Seoul') # ambiguous='infer' 제거 (에러 발생 시 명시적 처리 위해)
                    logger.debug("DataFrame 'Date' 컬럼에 KST 시간대 적용 완료")
                except AmbiguousTimeError as amb_err:
                    logger.error(f"모호한 시간대 오류(AmbiguousTimeError): {amb_err}", exc_info=True)
                    # 모호한 시간(예: DST 변경 시) 처리 - 여기서는 일단 NaT 처리
                    df.loc[amb_err.index, 'Date'] = pd.NaT
                except NonExistentTimeError as non_err:
                    logger.error(f"존재하지 않는 시간대 오류(NonExistentTimeError): {non_err}", exc_info=True)
                    # 존재하지 않는 시간(예: DST 변경 시) 처리 - 여기서는 일단 NaT 처리
                    df.loc[non_err.index, 'Date'] = pd.NaT
                except Exception as tz_err:
                    logger.error(f"시간대 설정 중 예상치 못한 오류 발생: {tz_err}", exc_info=True)
                    # 예상치 못한 오류 발생 시에도 일단 NaT 처리
                    df.loc[df['Date'].notna(), 'Date'] = pd.NaT 
                # --- 추가 끝 ---

                # --- Enhanced Logging ---
                logger.debug(f"DataFrame dtypes after creating 'Date' column:\n{df.dtypes}")
                nat_count = df['Date'].isna().sum()
                logger.debug(f"Number of NaT values in 'Date' column: {nat_count} / {len(df)}")
                # NaT가 발생한 행의 원본 시간 값 일부 로깅 (형식 확인용)
                if nat_count > 0:
                    original_time_samples = df.loc[df['Date'].isna(), time_col].head().tolist()
                    logger.warning(f"NaT 발생 시간 데이터 샘플 (원본 형식): {original_time_samples}")
                    # --- 추가: NaT 발생한 인덱스 로깅 ---
                    nat_indices = df.index[df['Date'].isna()].tolist()
                    logger.warning(f"Indices where NaT occurred: {nat_indices}")
                    # --- 추가 끝 ---
                logger.debug(f"DataFrame shape before dropna: {df.shape}")
                # --- End Enhanced Logging ---

                df.dropna(subset=['Date'], inplace=True) # 시간 변환 실패한 행 제거

                # --- Logging after dropna ---
                logger.debug(f"DataFrame shape after dropna: {df.shape}")
                if df.empty:
                    logger.warning("DataFrame became empty after dropping NaT dates.")
                # --- End Logging ---

                # If df is empty, set_index will fail, raise error earlier
                if df.empty:
                    raise ValueError("유효한 날짜 데이터가 없어 DataFrame이 비었습니다.")

                # --- 인덱스 설정 및 중복 처리 ---
                df = df.set_index('Date') # 이제 df가 비어있지 않을 때만 실행됨
                df = df.sort_index() # 시간순 정렬
                # 중복된 인덱스 중 마지막 값만 남김 (틱/분 데이터용)
                if not df.index.is_unique:
                    logger.warning(f"중복된 시간 인덱스 발견 ({stock_code}, {period}). 마지막 값만 유지합니다.")
                    df = df[~df.index.duplicated(keep='last')]
                # --- 중복 처리 끝 ---

                # --- 추가: 순서 번호 컬럼 생성 ---
                df['ordinal'] = np.arange(len(df))
                # --- 추가 끝 ---

                # --- 컬럼명 표준화 및 필수 컬럼 정의 (올바른 위치!) ---
                rename_map = {}
                if open_col and open_col in df.columns: rename_map[open_col] = 'Open'
                if high_col and high_col in df.columns: rename_map[high_col] = 'High'
                if low_col and low_col in df.columns: rename_map[low_col] = 'Low'
                if close_col and close_col in df.columns: rename_map[close_col] = 'Close'
                if volume_col and volume_col in df.columns: rename_map[volume_col] = 'Volume'
                df = df.rename(columns=rename_map)

                # required_cols 정의 수정 (틱 데이터 고려)
                if period.endswith('T'):
                    required_cols = ['Close', 'Volume'] # 틱은 OHLC 없음
                else:
                    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                    if not all(col in df.columns for col in ['Open', 'High', 'Low']): # OHLC 확인 강화
                         missing = [c for c in ['Open', 'High', 'Low'] if c not in df.columns]
                         logger.error(f"OHLC 표준 컬럼 부족 (rename 후): {missing}. 사용 가능 컬럼: {df.columns.tolist()}")
                         raise ValueError(f"OHLC 표준 컬럼 부족: {missing}")

                # 최종 컬럼 선택 전 확인
                missing_final = [c for c in required_cols if c not in df.columns]
                if missing_final:
                     logger.error(f"최종 필수 컬럼 부족 ({period}): {missing_final}. 사용 가능 컬럼: {df.columns.tolist()}")
                     raise ValueError(f"최종 필수 컬럼 부족: {missing_final}")
                # --- 표준화 및 정의 끝 ---

                # --- 최종 컬럼 선택 및 타입 변환 ---
                df = df[required_cols + ['ordinal']] # 필요한 컬럼과 ordinal 선택
                for col in df.columns:
                    if pd.api.types.is_object_dtype(df[col]):
                         df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[+-,]', '', regex=True), errors='coerce')
                    else:
                         df[col] = pd.to_numeric(df[col], errors='coerce')
                # df.dropna(inplace=True) # dropna 위치 변경 또는 재고려 -> 아래 계산 전에 개별 수행
                # --- 타입 변환 끝 ---

                # --- 로깅 추가 ---
                logger.debug(f"DataFrame 변환 및 컬럼 처리 후 ({stock_code}, {period}):\\n{df.head().to_string()}") # DataFrame 상위 5개 행 로깅
                # --- 로깅 추가 끝 ---

                if df.empty: raise ValueError("데이터 처리 후 유효한 데이터가 없습니다.")

            except Exception as e:
                 logger.error(f"DataFrame 변환 실패 ({stock_code}, {period}): {e}", exc_info=True) # 주기 정보 추가
                 self.chart_data = pd.DataFrame()
                 self.chart_updated.emit(stock_code, period, self.chart_data)
                 self.is_loading = False

            # --- 보조지표 계산 로직 수정 ---
            if not period.endswith('T') and not df.empty:
                # calculate_indicators가 'ordinal' 컬럼을 유지하도록 확인/수정 필요
                self.chart_data = calculate_indicators(df.drop(columns=['ordinal'])) # 계산 전 ordinal 제외
                self.chart_data['ordinal'] = df['ordinal'].values # 계산 후 다시 추가
            elif period.endswith('T') and not df.empty: # 틱 데이터 처리 (수정)
                 # TradingValue 계산 전 타입 확인 및 변환 추가
                 for col in ['Close', 'Volume']:
                     if not pd.api.types.is_numeric_dtype(df[col]):
                          df[col] = pd.to_numeric(df[col], errors='coerce')
                 df.dropna(subset=['Close', 'Volume'], inplace=True) # Close, Volume NaN 제거
                 df['TradingValue'] = df['Close'] * df['Volume']
                 # --- 추가: TradingValue 계산 후 NaN 값 제거 ---
                 df.dropna(subset=['TradingValue'], inplace=True)
                 # --- 추가 끝 ---
                 self.chart_data = df
                 # --- 추가: 틱 데이터 최종 로깅 ---
                 if period.endswith('T') and not self.chart_data.empty:
                     logger.debug(f"최종 처리된 틱 데이터 샘플:\n{self.chart_data.head().to_string()}")
                     logger.debug(f"틱 데이터 인덱스 (시간) 샘플: {self.chart_data.index[:5].tolist()}")
                     logger.debug(f"틱 데이터 종가 샘플: {self.chart_data['Close'].values[:5]}")
                 # --- 추가 끝 ---
            else: # df가 비어있는 경우
                self.chart_data = df # 빈 df 그대로 할당
            # --- 계산 끝 ---

            # --- 로깅 추가 ---
            logger.debug(f"최종 차트 데이터 생성 완료 ({stock_code}, {period}): {len(self.chart_data)} 행")
            if not self.chart_data.empty:
                logger.debug(f"최종 데이터 첫 행 예시:\\n{self.chart_data.iloc[0]}") # 최종 데이터 첫 행 로깅
            # --- 로깅 추가 끝 ---

            # --- 데이터 타입 최종 변환 (오류 방지) ---
            try:
                numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'TradingValue']
                indicator_cols = [col for col in self.chart_data.columns if col not in numeric_cols]
                all_cols_to_convert = numeric_cols + indicator_cols

                for col in all_cols_to_convert:
                    if col in self.chart_data.columns:
                        # 문자열 타입일 경우, 숫자 외 문자 제거 후 변환 시도
                        if pd.api.types.is_string_dtype(self.chart_data[col]):
                            # logger.debug(f"Converting string column '{col}' to numeric")
                            # +,- 기호 및 쉼표 제거 후 숫자 변환, 실패 시 NaN
                            self.chart_data[col] = pd.to_numeric(self.chart_data[col].astype(str).str.replace(r'[+-,]', '', regex=True), errors='coerce')
                        elif not pd.api.types.is_numeric_dtype(self.chart_data[col]): # 문자열 외 다른 non-numeric 타입
                             # logger.debug(f"Converting non-numeric column '{col}' to numeric")
                             self.chart_data[col] = pd.to_numeric(self.chart_data[col], errors='coerce')

                # NaN 처리 (선택적, 숫자 변환 실패 시 NaN 발생 가능)
                # self.chart_data.dropna(inplace=True) # 전체 행 제거는 위험할 수 있음

                logger.debug(f"최종 데이터 타입 변환 후 dtypes:\n{self.chart_data.dtypes}")

            except Exception as e:
                logger.error(f"최종 데이터 타입 변환 중 오류: {e}", exc_info=True)
                # 오류 발생 시 차트 업데이트 취소 또는 빈 데이터 전송 고려
                self.chart_updated.emit(stock_code, period, pd.DataFrame())
                self.is_loading = False
                return
            # --- 데이터 타입 변환 끝 ---

            logger.info(f"차트 데이터 로드 및 처리 완료: {stock_code}, {len(self.chart_data)}개")
            self.chart_updated.emit(stock_code, self.current_period, self.chart_data)
            
            if period.endswith('T') and REALTIME_INTERVAL_MS > 0:
                 logger.info(f"{stock_code} 틱 데이터 실시간 조회 시작 (주기: {REALTIME_INTERVAL_MS}ms)")
                 self.realtime_timer.start()

        except Exception as e:
            logger.error(f"차트 데이터 로드 중 오류 발생: {e}", exc_info=True)
            self.chart_data = pd.DataFrame()
            self.chart_updated.emit(stock_code, self.current_period, self.chart_data)
        finally:
            self.is_loading = False

    @pyqtSlot()
    def _request_realtime_data(self):
        """실시간 데이터(틱/현재가)를 주기적으로 요청합니다."""
        if not self.current_stock_code or not self.current_period.endswith('T'):
            self.realtime_timer.stop()
            return
            
        if self.is_loading: 
            logger.debug("과거 데이터 로딩 중... 실시간 요청 보류")
            return

        try:
            # KiwoomAPI의 get_stock_price 메소드 사용
            if not self.kiwoom_api:
                 logger.error("KiwoomAPI가 초기화되지 않았습니다.")
                 return
                 
            latest_data_raw = self.kiwoom_api.get_stock_price(self.current_stock_code)
            
            if latest_data_raw:
                # 필요한 정보 추출 및 형식 변환 (API 응답 키 확인 필요)
                try:
                    latest_data = {
                        'time': pd.Timestamp.now().timestamp(), # API 응답에 시간 없으면 현재 시간
                        'price': float(str(latest_data_raw.get('cur_prc', '0')).replace('+','').replace('-','').replace(',','')),
                        'volume': int(str(latest_data_raw.get('trde_qty', '0')).replace('+','').replace('-','').replace(',','')) # API가 실시간 체결량을 주는지 확인 필요
                    }
                    self.latest_data_updated.emit(self.current_stock_code, latest_data)
                except Exception as parse_err:
                    logger.error(f"실시간 데이터 파싱/변환 오류: {parse_err}, 원본: {latest_data_raw}")
            else:
                 logger.warning(f"실시간 데이터 조회 실패 또는 데이터 없음: {self.current_stock_code}")
                 
        except Exception as e:
            logger.error(f"실시간 데이터 요청 중 오류: {e}", exc_info=True)
            
    def stop_updates(self):
        """모든 업데이트 중지 (실시간 타이머 등)"""
        if self.realtime_timer.isActive():
            self.realtime_timer.stop()
            logger.info(f"실시간 업데이트 타이머 중지됨: {self.current_stock_code}")
            
    def cleanup(self):
        """모듈 정리"""
        logger.info(f"ChartModule 정리 시작: {self.current_stock_code}")
        self.stop_updates()
        # 필요한 경우 추가 리소스 정리
        logger.info(f"ChartModule 정리 완료: {self.current_stock_code}") 