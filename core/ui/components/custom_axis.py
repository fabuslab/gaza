# core/ui/components/custom_axis.py
import pyqtgraph as pg
# from PySide6.QtCore import QDateTime, Qt # QDateTime 대신 datetime 사용
from datetime import datetime # datetime 임포트
import numpy as np
import logging # 로깅 추가

logger = logging.getLogger(__name__)

class DateAxis(pg.AxisItem):
    """날짜/시간 표시를 위한 커스텀 X축 클래스"""
    def __init__(self, orientation='bottom', *args, **kwargs):
        super().__init__(orientation, *args, **kwargs)
        self.enableAutoSIPrefix(False)
        self.setLabel(text='시간', units=None) # 단위 없음
        self.current_timeframe = 'D' # 기본값: 일봉

    def set_current_timeframe(self, timeframe: str):
        """현재 차트 주기를 설정 (ChartComponent에서 호출)"""
        self.current_timeframe = timeframe
        # logger.debug(f"DateAxis timeframe set to: {timeframe}")

    def tickStrings(self, values, scale, spacing):
        """타임스탬프 값을 주기에 맞는 날짜/시간 문자열로 변환 (datetime 사용, 안정성 강화)"""
        strings = []
        if not values:
            return strings

        try:
            # 주기에 따른 포맷 결정 (고정 포맷 우선)
            if self.current_timeframe == 'Y': fmt = "%Y"
            elif self.current_timeframe == 'M': fmt = "%Y-%m"
            elif self.current_timeframe == 'W': fmt = "%m/%d"
            elif self.current_timeframe == 'D': fmt = "%m/%d"
            elif self.current_timeframe.isdigit(): fmt = "%H:%M" # 분봉 고정
            elif self.current_timeframe.endswith('T'): fmt = "%H:%M:%S" # 틱봉 고정
            else: fmt = "%Y-%m-%d"

            for v in values:
                try:
                    # 숫자형 값만 변환 시도
                    if isinstance(v, (int, float, np.number)):
                        # 타임스탬프 -> datetime 객체 -> strftime 포맷팅
                        # 매우 큰/작은 타임스탬프 값 처리
                        try:
                            dt_object = datetime.fromtimestamp(float(v))
                            strings.append(dt_object.strftime(fmt))
                        except (OSError, OverflowError):
                            strings.append('?') # 유효 범위 벗어나는 값 처리
                            # logger.warning(f"Timestamp {v} out of range for datetime conversion.")
                    else:
                        strings.append(str(v))
                except Exception as e_inner:
                    logger.error(f"Error processing tick value {v}: {e_inner}", exc_info=False)
                    strings.append('Err')

        except Exception as e:
            logger.error(f"General error in DateAxis.tickStrings: {e}", exc_info=True)
            strings = ['Err'] * len(values)

        return strings

    def setTickFormat(self, fmt: str):
        """tickStrings 내부에서 동적으로 포맷을 결정하므로 이 메소드는 사용하지 않음."""
        # Deprecated: 이 메소드를 사용하지 않도록 경고 또는 pass 처리
        logger.warning("DateAxis.setTickFormat is deprecated. Format is determined dynamically.")
        pass

class PriceAxis(pg.AxisItem):
    """가격 표시를 위한 커스텀 Y축 클래스"""
    def __init__(self, orientation, *args, **kwargs):
        super().__init__(orientation, *args, **kwargs)
        self.setLabel(text='가격', units='원')
        self.enableAutoSIPrefix(False) # SI 접두어 비활성화

    def tickStrings(self, values, scale, spacing):
        """가격 값을 문자열로 변환 (천 단위 구분자 추가)"""
        strings = []
        try:
            for v in values:
                strings.append(f"{v:,.0f}") # 천 단위 쉼표 포맷
        except Exception as e:
            logger.error(f"Error formatting price tick strings: {e}", exc_info=True)
            strings = [str(v) for v in values] # 오류 시 기본값 사용
        return strings 