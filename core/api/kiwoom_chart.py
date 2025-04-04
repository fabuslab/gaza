"""
키움증권 REST API 차트 관련 기능 모듈
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta # timedelta 추가

# from .kiwoom import KiwoomAPI # 순환 참조 방지를 위해 타입 힌트만 사용

logger = logging.getLogger(__name__)

# API ID 상수 (차트 관련)
API_ID_DAILY_CHART = "ka10081"
API_ID_WEEKLY_CHART = "ka10082"
API_ID_MONTHLY_CHART = "ka10083"
API_ID_YEARLY_CHART = "ka10094"
API_ID_MINUTE_CHART = "ka10080"
API_ID_TICK_CHART = "ka10079"

# API 응답에서 실제 데이터 리스트를 담고 있는 키 (API ID별로 다를 수 있음 - 확인 필수!)
# 이전 로그 분석 및 일반적인 경우를 바탕으로 예상 키 추가
RESPONSE_DATA_KEYS = {
    API_ID_DAILY_CHART: ["stk_dt_pole_chart_qry", "output1", "output"],
    API_ID_WEEKLY_CHART: ["stk_wk_pole_chart_qry", "stk_stk_pole_chart_qry", "output1", "output"],
    API_ID_MONTHLY_CHART: ["stk_mth_pole_chart_qry", "output1", "output"],
    API_ID_YEARLY_CHART: ["stk_yr_pole_chart_qry", "output1", "output"],
    API_ID_MINUTE_CHART: ["stk_min_pole_chart_qry", "output1", "output"],
    API_ID_TICK_CHART: ["stk_tic_chart_qry", "output1", "output"],
    "fallback": ["output", "chart_data", "output1", "chart_output"]
}

class KiwoomChartAPI:
    """키움증권 차트 API 호출 담당 클래스"""

    def __init__(self, kiwoom_api: 'KiwoomAPI'): 
        self.api = kiwoom_api
        self.logger = logging.getLogger(__name__)

    def _extract_chart_data(self, api_id: str, response_data: Dict) -> Optional[List[Dict]]:
        """API 응답에서 실제 차트 데이터 리스트 추출"""
        if not isinstance(response_data, dict) or response_data.get("return_code") != 0:
            # return_code가 0이 아니어도 데이터가 있을 수 있는 API가 있는지 확인 필요 (일단 오류로 간주)
            self.logger.warning(f"API 응답 오류 또는 return_code != 0 ({api_id}): {response_data.get('return_msg', 'N/A')}")
            return None

        possible_keys = RESPONSE_DATA_KEYS.get(api_id, []) + RESPONSE_DATA_KEYS["fallback"]
        
        for key in possible_keys:
            data_list = response_data.get(key)
            if isinstance(data_list, list):
                self.logger.debug(f"데이터 리스트 찾음 (키: '{key}')")
                return data_list
                
        self.logger.warning(f"API 응답에서 차트 데이터 리스트를 찾을 수 없음 (API ID: {api_id}), 시도한 키: {possible_keys}")
        # 응답 자체를 로깅하여 구조 확인
        self.logger.debug(f"전체 API 응답 데이터 구조: {response_data}") 
        return None

    def _fetch_chart_data(self, api_id: str, request_data: Dict, count: Optional[int] = None) -> List[Dict]:
        """연속 조회를 포함하여 차트 데이터를 가져오는 공통 로जिक (개선)"""
        all_data = []
        cont_yn = 'N'
        next_key = ''
        request_count = 0
        MAX_REQUESTS = 10 # 연속 조회 최대 횟수
        MAX_TOTAL_DATA = 5000 # 최대 데이터 개수 제한 (메모리 관리)

        while request_count < MAX_REQUESTS:
            request_count += 1
            logger.debug(f"차트 데이터 요청 ({request_count}/{MAX_REQUESTS}): api_id={api_id}, cont={cont_yn}, next_key={next_key[:10]}...") # api_id 로깅 추가
            
            response_data, next_key_resp, cont_yn_resp = self.api._api_request(
                api_id=api_id,
                data=request_data,
                cont_yn=cont_yn,
                next_key=next_key
            )

            # --- 로깅 추가 ---
            # 응답 데이터 로깅 (너무 길 수 있으므로 일부만 또는 중요한 부분만 로깅 고려)
            # 예시: 처음 몇 개의 아이템 또는 키만 로깅
            response_log = str(response_data) # 전체를 문자열로
            if len(response_log) > 500: # 너무 길면 자르기
                response_log = response_log[:500] + "... (truncated)"
            logger.debug(f"API 응답 수신 ({api_id}): {response_log}")
            # --- 로깅 추가 끝 ---

            # 응답 유효성 검사 (오류 코드 등)
            if response_data.get("return_code") != 0:
                 logger.error(f"API 오류 수신 ({api_id}): code={response_data.get('return_code')}, msg={response_data.get('return_msg')}")
                 break # 오류 시 중단
                 
            data_list = self._extract_chart_data(api_id, response_data)
            
            # --- 로깅 추가 ---
            if data_list is not None:
                logger.debug(f"데이터 추출 결과 ({api_id}): {len(data_list)}개 항목 발견.")
                # 추출된 데이터의 첫 항목 예시 로깅 (구조 확인용)
                if data_list:
                     logger.debug(f"추출된 첫 데이터 항목 예시: {data_list[0]}")
            else:
                logger.warning(f"데이터 추출 실패 ({api_id}): data_list is None.")
            # --- 로깅 추가 끝 ---

            if data_list:
                 # 데이터 추가 (중복 제거는 하지 않음 - API가 알아서 할 것으로 기대)
                 all_data.extend(data_list)
                 logger.debug(f"데이터 {len(data_list)}개 추가 (누적: {len(all_data)}개), 연속: {cont_yn_resp}")
            else:
                 logger.warning(f"데이터 추출 실패 또는 없음. 연속 조회 중단 ({api_id})")
                 # 수정: 추출 실패 시에도 응답 자체를 다시 로깅하여 구조 확인
                 logger.debug(f"데이터 추출 실패 시 전체 API 응답: {response_log}")
                 break

            cont_yn = cont_yn_resp
            next_key = next_key_resp

            # 종료 조건 검사
            if cont_yn != 'Y':
                 logger.info("더 이상 받을 데이터 없음 (cont_yn != Y)")
                 break
            if count is not None and len(all_data) >= count:
                 logger.info(f"요청 개수({count}) 이상 데이터 수신 완료 ({len(all_data)}개)")
                 break
            if len(all_data) >= MAX_TOTAL_DATA:
                 logger.warning(f"최대 데이터 개수({MAX_TOTAL_DATA}) 도달. 조회 중단.")
                 break
                
        if request_count >= MAX_REQUESTS:
             logger.warning(f"최대 요청 횟수({MAX_REQUESTS}) 초과. 조회 중단.")

        # 데이터 시간순 정렬 (API가 역순으로 줄 경우 대비 - 실제 확인 필요)
        # 예: all_data.sort(key=lambda x: x.get('dt') or x.get('cntr_tm'))
        # 여기서는 일단 정렬하지 않음 (ChartModule에서 처리 가정)

        # 요청한 개수만큼 최신 데이터 반환 (count가 지정된 경우)
        if count is not None and len(all_data) > count:
             # API 응답은 최신 데이터가 앞에 오므로, 앞에서부터 count개 선택
             logger.debug(f"데이터 개수({len(all_data)})가 요청 개수({count})보다 많아 슬라이싱 수행 (최신 데이터 가정, 앞에서부터)")
             # return all_data[-count:]   # 기존 방식 (오래된 데이터 선택)
             return all_data[:count]    # 수정된 방식 (최신 데이터 선택)

        return all_data

    # --- 주기별 차트 조회 메소드 --- 
    
    def get_stock_ohlcv_chart(self, stock_code: str, period: str, base_dt: str, count: Optional[int]=None, adjusted_price: str = '1') -> List[Dict]:
        """일/주/월/년봉 데이터 조회"""
        api_id_map = { 'D': API_ID_DAILY_CHART, 'W': API_ID_WEEKLY_CHART, 'M': API_ID_MONTHLY_CHART, 'Y': API_ID_YEARLY_CHART }
        api_id = api_id_map.get(period)
        if not api_id: raise ValueError(f"지원하지 않는 OHLCV 주기: {period}")
            
        logger.info(f"{period}봉 차트 조회 시작: {stock_code}, 기준일={base_dt}, 요청개수={count or 'API기본'}")
        request_data = {
            "stk_cd": stock_code,
            "base_dt": base_dt,      # 기준일자
            "upd_stkpc_tp": adjusted_price # 수정주가 구분
            # "data_cnt": str(count) if count else "" # API가 지원하는지 확인 필요
        }
        return self._fetch_chart_data(api_id, request_data, count)

    def get_stock_minute_chart(self, stock_code: str, interval: str, count: Optional[int]=None, adjusted_price: str = '1') -> List[Dict]:
        """분봉 데이터 조회"""
        api_id = API_ID_MINUTE_CHART
        logger.info(f"{interval}분봉 차트 조회 시작: {stock_code}, 요청개수={count or 'API기본'}")
        request_data = {
            "stk_cd": stock_code,
            "tic_scope": interval,
            "upd_stkpc_tp": adjusted_price
        }
        logger.debug(f"분봉 요청 데이터: {request_data}")
        return self._fetch_chart_data(api_id, request_data, count)

    def get_stock_tick_chart(self, stock_code: str, tick_scope: str, count: Optional[int]=None, adjusted_price: str = '1') -> List[Dict]:
        """틱봉 데이터 조회"""
        api_id = API_ID_TICK_CHART
        logger.info(f"{tick_scope}틱 차트 조회 시작: {stock_code}, 요청개수={count or 'API기본'}")
        request_data = {
            "stk_cd": stock_code,
            "tic_scope": tick_scope,
            "upd_stkpc_tp": adjusted_price
        }
        logger.debug(f"틱봉 요청 데이터: {request_data}")
        return self._fetch_chart_data(api_id, request_data, count) 