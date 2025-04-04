import pandas as pd
import pandas_ta as ta # pandas-ta 임포트
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    주어진 DataFrame에 주요 보조지표를 계산하여 추가합니다.

    Args:
        df (pd.DataFrame): 'Open', 'High', 'Low', 'Close', 'Volume' 컬럼과 
                           DatetimeIndex를 가진 데이터프레임.

    Returns:
        pd.DataFrame: 원본 DataFrame에 보조지표 컬럼들이 추가된 데이터프레임.
                      계산에 실패하거나 데이터가 부족하면 원본 DataFrame 반환 (오류 로깅).
    """
    if df.empty:
        logger.warning("보조지표 계산을 위한 데이터프레임이 비어 있습니다.")
        return df # 빈 DF 반환 대신 원본 반환

    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        logger.error(f"보조지표 계산에 필요한 컬럼 부족: {missing}. 반환: 원본 DataFrame")
        return df # 필요한 컬럼 없으면 원본 반환

    # 계산 편의를 위해 복사본 사용
    df_res = df.copy()

    # 필요한 경우 데이터 타입 변환 (pandas-ta는 보통 float 필요)
    for col in required_columns:
        if not pd.api.types.is_numeric_dtype(df_res[col]):
             try:
                 df_res[col] = pd.to_numeric(df_res[col], errors='coerce')
             except Exception as e:
                  logger.error(f"{col} 컬럼 숫자 변환 실패: {e}. 반환: 원본 DataFrame")
                  return df # 변환 실패 시 원본 반환
                  
    # NaN 값 처리 (ffill: 이전 값으로 채우기. 계산 오류 방지 목적)
    if df_res[required_columns].isnull().any().any():
        logger.warning("데이터에 NaN 값이 포함되어 ffill 수행.")
        df_res[required_columns] = df_res[required_columns].ffill()
        # ffill 후에도 NaN이 남으면 해당 행 제거 (맨 처음 데이터가 NaN인 경우)
        df_res.dropna(subset=required_columns, inplace=True)
        if df_res.empty:
            logger.warning("NaN 처리 후 데이터프레임이 비어 있습니다. 반환: 원본 DataFrame")
            return df

    try:
        # --- 이동 평균선 (SMA & EMA) --- 
        sma_periods = [5, 10, 20, 60, 120] 
        ema_periods = [5, 10, 20, 60, 120]
        
        for period in sma_periods:
            if len(df_res) >= period:
                df_res.ta.sma(length=period, append=True) 
            else:
                 df_res[f'SMA_{period}'] = pd.NA 
                 
        for period in ema_periods:
             if len(df_res) >= period:
                 df_res.ta.ema(length=period, append=True) 
             else:
                 df_res[f'EMA_{period}'] = pd.NA

        # --- 볼린저 밴드 --- 
        bb_length = 20
        bb_std = 2
        if len(df_res) >= bb_length:
            # pandas_ta v0.3.14b 기준, 컬럼 이름 직접 지정 가능 (명확성 위해)
            df_res.ta.bbands(length=bb_length, std=bb_std, 
                             col_names=(f'BBL_{bb_length}_{bb_std}', 
                                        f'BBM_{bb_length}_{bb_std}', 
                                        f'BBU_{bb_length}_{bb_std}', 
                                        f'BBB_{bb_length}_{bb_std}', 
                                        f'BBP_{bb_length}_{bb_std}'), 
                             append=True)
        else:
            for suffix in ['L', 'M', 'U', 'B', 'P']:
                 df_res[f'BBL_{bb_length}_{bb_std}'] = pd.NA
                 df_res[f'BBM_{bb_length}_{bb_std}'] = pd.NA
                 df_res[f'BBU_{bb_length}_{bb_std}'] = pd.NA
                 df_res[f'BBB_{bb_length}_{bb_std}'] = pd.NA
                 df_res[f'BBP_{bb_length}_{bb_std}'] = pd.NA

        # --- RSI --- 
        rsi_length = 14
        if len(df_res) > rsi_length: 
             df_res.ta.rsi(length=rsi_length, append=True) 
        else:
             df_res[f'RSI_{rsi_length}'] = pd.NA

        # --- MACD --- 
        macd_fast = 12
        macd_slow = 26
        macd_signal = 9
        if len(df_res) >= macd_slow + macd_signal:
            df_res.ta.macd(fast=macd_fast, slow=macd_slow, signal=macd_signal, append=True)
        else:
             for suffix in ['', 'h', 's']:
                 # pandas-ta에서 생성되는 실제 컬럼명 확인 필요 (예: MACD_12_26_9)
                 df_res[f'MACD_{macd_fast}_{macd_slow}_{macd_signal}'] = pd.NA
                 df_res[f'MACDh_{macd_fast}_{macd_slow}_{macd_signal}'] = pd.NA
                 df_res[f'MACDs_{macd_fast}_{macd_slow}_{macd_signal}'] = pd.NA

        # --- 거래대금 --- 
        df_res['TradingValue'] = df_res['Close'] * df_res['Volume']

        logger.info(f"보조지표 계산 완료. 최종 컬럼 수: {len(df_res.columns)}")
        return df_res

    except ImportError:
        logger.error("pandas-ta 라이브러리가 설치되지 않았습니다. pip install pandas-ta. 반환: 원본 DataFrame")
        return df
    except Exception as e:
        logger.error(f"보조지표 계산 중 오류 발생: {e}. 반환: 원본 DataFrame", exc_info=True)
        return df

# --- 사용 예시 (테스트용) ---
if __name__ == '__main__':
    # 샘플 데이터 생성
    data = {
        'Open': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 110, 112, 111, 113, 115, 114, 116, 118, 117, 119]*5,
        'High': [103, 104, 103, 105, 106, 106, 108, 109, 109, 111, 112, 114, 113, 115, 117, 116, 118, 120, 119, 121]*5,
        'Low': [99, 100, 100, 102, 103, 103, 105, 106, 106, 108, 109, 110, 110, 112, 113, 113, 115, 116, 116, 118]*5,
        'Close': [102, 101, 103, 105, 104, 106, 108, 107, 109, 110, 112, 111, 113, 115, 114, 116, 118, 117, 119, 120]*5,
        'Volume': [1000, 1200, 1100, 1300, 1500, 1400, 1600, 1800, 1700, 1900, 2000, 2200, 2100, 2300, 2500, 2400, 2600, 2800, 2700, 2900]*5
    }
    dates = pd.date_range(end=pd.Timestamp.today(), periods=100, freq='B')
    sample_df = pd.DataFrame(data, index=dates)
    
    print("--- 원본 데이터 (일부) ---")
    print(sample_df.tail())

    # 보조지표 계산
    df_with_indicators = calculate_indicators(sample_df.copy())

    print("\n--- 보조지표 추가 후 데이터 (일부) ---")
    if not df_with_indicators.empty:
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        print(df_with_indicators.tail())
        print(f"\n총 컬럼 수: {len(df_with_indicators.columns)}")
    else:
        print("보조지표 계산 실패 또는 데이터 부족") 