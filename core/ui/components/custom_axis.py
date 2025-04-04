# core/ui/components/custom_axis.py
import pyqtgraph as pg
# from PySide6.QtCore import QDateTime, Qt # QDateTime 대신 datetime 사용
from datetime import datetime, timedelta # timedelta 추가
import numpy as np
import pandas as pd # pandas 추가
import logging # 로깅 추가
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)

class OrdinalDateAxis(pg.AxisItem):
    """날짜/시간 표시를 위한 커스텀 X축 클래스 (순서축 기반)"""
    def __init__(self, orientation='bottom', *args, **kwargs):
        super().__init__(orientation, *args, **kwargs)
        self.enableAutoSIPrefix(False)
        # self.setLabel(text='시간', units=None) # 라벨은 동적으로 설정 가능
        self.current_period = 'D' # 기본값: 일봉
        self.chart_data_ref: Optional[pd.DataFrame] = None
        self.label_cache: Dict[int, str] = {}  # 레이블 캐시
        self.last_range: Tuple[float, float] = (0, 100)  # 마지막 표시 범위

    def setChartData(self, chart_data: pd.DataFrame, period: str):
        """ChartComponent로부터 차트 데이터 참조 및 주기 설정"""
        self.chart_data_ref = chart_data
        self.current_period = period # 주기 업데이트
        self.label_cache.clear()  # 데이터 변경 시 캐시 초기화
        # 축 레이블 설정
        if period == 'D':
            self.setLabel(text='날짜')
        elif period == 'W':
            self.setLabel(text='주')
        elif period == 'M':
            self.setLabel(text='월')
        elif period == 'Y':
            self.setLabel(text='년')
        elif period.endswith('T'):
            self.setLabel(text='시간')
        else:
            # 분봉
            self.setLabel(text='시간')
            
        # 데이터 변경 시 축 업데이트
        self.picture = None
        self.update()

    def tickStrings(self, values, scale, spacing):
        """순서 번호(values)를 주기에 맞는 날짜/시간 문자열로 변환"""
        if self.chart_data_ref is None or self.chart_data_ref.empty or len(values) == 0:
            return [''] * len(values)

        try:
            # 디버깅 정보 최소화
            if len(values) > 0:
                logger.debug(f"tickStrings 호출됨: values[0]={values[0]}, period={self.current_period}")
            
            # 현재 뷰의 범위 파악
            view_range = self.linkedView().viewRange()[0]
            view_min, view_max = view_range
            data_len = len(self.chart_data_ref)
            
            # 범위 검사
            if view_min > data_len or view_max < 0:
                return [''] * len(values)
                
            # 주기에 맞는 날짜 포맷 설정
            fmt = self._get_date_format(self.current_period)
            
            # 표시할 레이블 결정 (확대/축소 상태에 따라 자동 조절)
            visible_range = view_max - view_min
            
            # 레이블 간격 동적 계산
            if visible_range <= 10:  # 매우 확대된 상태 - 모든 날짜
                step = 1
            elif visible_range <= 30:  # 확대된 상태 - 격일
                step = 2
            elif visible_range <= 60:  # 중간 - 주 단위
                step = 5
            elif visible_range <= 180:  # 축소 - 2주 단위
                step = 10
            else:  # 매우 축소 - 월 단위
                step = int(visible_range / 20)
                
            # 레이블 생성
            strings = [''] * len(values)
            last_label_idx = -999  # 마지막 레이블 위치
            last_month = -1  # 마지막으로 표시한 월
            last_year = -1   # 마지막으로 표시한 연도
            
            # 주요 시간대 추출 (월초, 분기 등)
            major_dates = self._get_major_dates()
            
            for i, val in enumerate(values):
                idx = int(round(val))
                
                # 범위 내 레이블 생성
                if 0 <= idx < data_len:
                    # 항상 표시할 중요 날짜와 간격 기준 표시할 날짜 선택
                    is_major_date = idx in major_dates
                    is_step_position = (idx % step == 0)
                    
                    # 첫 날짜, 마지막 날짜는 항상 표시
                    is_boundary = (idx == 0 or idx == data_len - 1)
                    
                    # 충분한 간격이 있을 때만 표시 (레이블 겹침 방지)
                    has_gap = (idx - last_label_idx) >= step
                    
                    if (is_major_date or is_step_position or is_boundary) and has_gap:
                        date_obj = self.chart_data_ref.index[idx]
                        
                        # 주봉 차트 특수 처리
                        if self.current_period == 'W':
                            # 해당 주의 시작일 계산
                            weekday = date_obj.weekday()
                            start_of_week = date_obj - timedelta(days=weekday)
                            label = start_of_week.strftime(fmt)
                        
                        # 캐싱된 레이블 사용 (성능 최적화)
                        elif idx in self.label_cache:
                            label = self.label_cache[idx]
                            
                        else:
                            # 기본 레이블 생성
                            label = date_obj.strftime(fmt)
                            
                            # 월 변경 시 연도 표시 (월봉/일봉)
                            current_month = date_obj.month
                            current_year = date_obj.year
                            
                            if self.current_period in ['D', 'M']:
                                # 연도 표시 조건: 첫 레이블, 연도 변경, 1월
                                if (last_year != current_year) or (current_month == 1 and last_month != 1):
                                    if self.current_period == 'D' and current_month == 1:
                                        label = date_obj.strftime('%Y-%m-%d')
                                    elif self.current_period == 'M':
                                        label = date_obj.strftime('%Y-%m')
                                        
                            # 캐시에 저장
                            self.label_cache[idx] = label
                            
                        strings[i] = label
                        last_label_idx = idx
                        last_month = date_obj.month
                        last_year = date_obj.year
            
            # 디버깅: 생성된 레이블 샘플
            if len(strings) > 0:
                non_empty = [s for s in strings if s]
                logger.debug(f"생성된 레이블(처음 5개): {non_empty[:5]}")
                
            return strings
            
        except Exception as e:
            logger.error(f"날짜 축 레이블 생성 오류: {e}", exc_info=True)
            return ['Error'] * len(values)
    
    def _get_date_format(self, period):
        """주기에 맞는 날짜 포맷 반환"""
        if period == 'Y': 
            return "%Y"
        elif period == 'M': 
            return "%Y-%m"
        elif period == 'W' or period == 'D': 
            return "%m-%d"  # 월-일 형식으로 간결화
        elif period.endswith('T'): 
            return "%H:%M:%S"
        elif period.isdigit(): 
            return "%H:%M"
        return "%Y-%m-%d"  # 기본값
    
    def _get_major_dates(self):
        """중요 날짜(월초, 연초, 분기 등) 위치 반환"""
        if self.chart_data_ref is None or self.chart_data_ref.empty:
            return set()
            
        major_indices = set()
        
        try:
            dates = self.chart_data_ref.index
            
            for i, date in enumerate(dates):
                # 월초 표시
                if date.day == 1:
                    major_indices.add(i)
                
                # 연초 표시 (1월 1일)
                if date.month == 1 and date.day == 1:
                    major_indices.add(i)
                    
                # 분기 시작 표시 (1, 4, 7, 10월 1일)
                if date.day == 1 and date.month in [1, 4, 7, 10]:
                    major_indices.add(i)
        except:
            pass
            
        return major_indices
    
    def setTickFormat(self, fmt: str):
        """tickStrings 내부에서 동적으로 포맷을 결정하므로 이 메소드는 사용하지 않음."""
        # 사용하지 않음 (호환성 유지)
        pass
        
    def tickValues(self, minVal, maxVal, size):
        """틱 위치를 최적화하여 반환"""
        # 기본 구현 사용 (균등 간격)
        return super().tickValues(minVal, maxVal, size)

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