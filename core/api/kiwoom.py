"""
키움증권 API 연동 모듈
"""

import logging
import json
import os
import time
import requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .base import BaseAPI

logger = logging.getLogger(__name__)

# --- API ID 상수 정의 ---
STOCK_INFO_API_ID = "ka10095" # 원래 API ID (관심종목정보요청)
# 관심종목 API ID (필요시 별도 정의)
FAVORITE_STOCK_API_ID = "ka10095"

# KiwoomChartAPI 클래스 import (순환 참조 방지를 위해 함수 내에서 import 하거나, 의존성 주입 방식 고려)
# 여기서는 __init__ 에서 import 시도
# from .kiwoom_chart import KiwoomChartAPI # 파일 상단 임포트 제거

class KiwoomAPI(BaseAPI):
    """키움증권 REST API 클라이언트"""
    
    TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'kiwoom_token.json')
    
    def __init__(self, api_key: str = None, api_secret: str = None, is_real: bool = True):
        """
        Args:
            api_key: 키움증권 API 키
            api_secret: 키움증권 API 시크릿
            is_real: 실전/모의투자 모드 여부 (True: 실전, False: 모의투자)
        """
        base_url = "https://api.kiwoom.com" if is_real else "https://openapi.kiwoom.com"
        super().__init__(base_url=base_url, api_key=api_key)
        self.api_secret = api_secret
        self.is_real = is_real
        self.access_token = None
        self.token_expires_at = 0
        self.refresh_token = None
        self._last_api_calls = {}
        self.logger = logging.getLogger(__name__)
        
        # 차트 API 인스턴스 생성 (KiwoomChartAPI 임포트 후)
        try:
            from .kiwoom_chart import KiwoomChartAPI
            self.chart = KiwoomChartAPI(self)
        except ImportError as e:
             logger.error(f"KiwoomChartAPI 임포트 실패: {e}. 차트 기능을 사용할 수 없습니다.")
             self.chart = None # 임포트 실패 시 None 할당
        
        os.makedirs(os.path.dirname(self.TOKEN_FILE), exist_ok=True)
        if is_real: logger.info("실전투자 모드로 API 초기화")
        else: logger.info("모의투자 모드로 API 초기화")
        self._load_token()
        self.last_error_details = None
        self.last_request_info = None
        self._chart_data = None  # 차트 데이터 저장용 필드 추가
        self.verify_ssl = True  # SSL 인증서 검증 (기본값은 검증 활성화)

    def _load_token(self) -> bool:
        """저장된 토큰 로드
        
        Returns:
            로드 성공 여부
        """
        try:
            if os.path.exists(self.TOKEN_FILE):
                with open(self.TOKEN_FILE, 'r') as f:
                    token_data = json.load(f)
                
                # 저장된 토큰 정보 확인
                self.access_token = token_data.get('token')
                self.refresh_token = token_data.get('refresh_token')
                
                # 모드 확인 (실전/모의투자)
                saved_mode = token_data.get('is_real')
                if saved_mode != self.is_real:
                    logger.warning(f"저장된 토큰의 모드({saved_mode})와 현재 모드({self.is_real})가 다릅니다. 토큰을 재발급합니다.")
                    return False
                
                # API 키 변경 확인
                saved_api_key = token_data.get('api_key')
                if saved_api_key != self.api_key:
                    logger.warning("API 키가 변경되었습니다. 토큰을 재발급합니다.")
                    return False
                
                # 토큰 로드 성공
                logger.info(f"저장된 토큰을 로드했습니다. 토큰={self.access_token[:5]}... (길이: {len(self.access_token)}자)")
                
                # 토큰 만료 시간은 무한대로 설정
                self.token_expires_at = float('inf')
                return True
                    
            return False
        except Exception as e:
            logger.error(f"토큰 로드 중 오류 발생: {e}")
            return False
    
    def _save_token(self):
        """현재 토큰 저장"""
        try:
            token_data = {
                'token': self.access_token,
                'refresh_token': self.refresh_token,
                'is_real': self.is_real,
                'api_key': self.api_key
            }
            
            with open(self.TOKEN_FILE, 'w') as f:
                json.dump(token_data, f)
                
            logger.info(f"토큰을 파일에 저장했습니다: {self.TOKEN_FILE}")
        except Exception as e:
            logger.error(f"토큰 저장 중 오류 발생: {e}")
        
    def _ensure_token(self) -> str:
        """유효한 액세스 토큰 확보
        
        Returns:
            액세스 토큰
        """
        # 이미 토큰이 있으면 그대로 사용
        if self.access_token:
            return self.access_token
            
        # 토큰이 없을 경우에만 새로 발급받음
        self._get_access_token()
        return self.access_token
        
    def _get_access_token(self):
        """새로운 액세스 토큰 발급"""
        try:
            logger.info("액세스 토큰 발급 시작")
            
            # OAuth2 토큰 발급 엔드포인트
            token_url = f"{self.base_url}/oauth2/token"
            
            # 요청 헤더
            headers = {
                "Content-Type": "application/json;charset=UTF-8"
            }
            
            # 요청 데이터
            data = {
                "grant_type": "client_credentials",
                "appkey": self.api_key,
                "secretkey": self.api_secret
            }
            
            logger.info(f"토큰 요청 URL: {token_url}")
            logger.debug(f"토큰 요청 헤더: {headers}")
            logger.info(f"토큰 요청 파라미터: appkey={len(self.api_key) if self.api_key else 0}자리, secretkey={len(self.api_secret) if self.api_secret else 0}자리")
            
            # API 키와 시크릿이 유효한지 확인
            if not self.api_key or not self.api_secret:
                logger.error("API 키 또는 시크릿이 설정되지 않았습니다.")
                raise ValueError("API 키 또는 시크릿이 설정되지 않았습니다.")
            
            # 키움증권 API 서버에 토큰 요청
            response = requests.post(token_url, headers=headers, json=data, timeout=10)
            logger.info(f"토큰 응답 상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                # 응답 처리
                response_data = response.json()
                logger.debug(f"토큰 응답 데이터: {response_data}")
                
                # 응답에서 토큰 정보 추출
                self.access_token = response_data.get("token", "")
                self.refresh_token = response_data.get("refresh_token", "")
                
                # 토큰 만료 시간은 무한대로 설정 (만료 없음)
                self.token_expires_at = float('inf')
                
                logger.info(f"액세스 토큰 발급 성공: 토큰={self.access_token[:5]}... (길이: {len(self.access_token)}자)")
                
                # 토큰 파일에 저장
                self._save_token()
                
                return
            else:
                # 오류 처리
                try:
                    error_data = response.json()
                    error_message = f"토큰 발급 실패: 상태 코드={response.status_code}, 내용={json.dumps(error_data)}"
                except Exception:
                    error_message = f"토큰 발급 실패: 상태 코드={response.status_code}, 내용={response.text}"
                
                logger.error(error_message)
                raise ValueError(error_message)
                
        except Exception as e:
            logger.error(f"액세스 토큰 발급 중 오류 발생: {e}", exc_info=True)
            raise ValueError(f"액세스 토큰 발급 실패: {str(e)}")

    def _get_endpoint_by_api_id(self, api_id):
        """API ID에 해당하는 엔드포인트를 반환합니다."""
        # 차트 관련 엔드포인트 포함 (Chart API 클래스에서도 사용 가능)
        chart_endpoint = '/api/dostk/chart'
        info_endpoint = '/api/dostk/stkinfo' # stkinfo 엔드포인트
        endpoints = {
            STOCK_INFO_API_ID: info_endpoint, # ka10095
            # "ka10001": info_endpoint, # ka10001 관련 제거 또는 주석 처리
            "ka10079": chart_endpoint,
            "ka10080": chart_endpoint,
            "ka10081": chart_endpoint,
            "ka10082": chart_endpoint,
            "ka10083": chart_endpoint,
            "ka10094": chart_endpoint,
        }
        endpoint = endpoints.get(api_id)
        if not endpoint:
             logger.error(f"지원하지 않는 API ID 또는 엔드포인트 없음: {api_id}")
             return None
        return endpoint

    def _api_request(self, api_id, data, cont_yn='N', next_key='', retries=1):
        """API 요청을 보내고 응답을 처리합니다. (수정: 토큰 오류 시 재시도 로직 추가)"""
        self.last_error_details = None
        self.last_request_info = {"api_id": api_id, "time": datetime.now().isoformat()}
        
        endpoint = self._get_endpoint_by_api_id(api_id)
        if not endpoint:
            error_msg = f"지원하지 않는 API ID: {api_id}"
            logger.error(error_msg)
            return {"error": error_msg, "return_code": -1}, '', 'ERR' 

        host = 'https://api.kiwoom.com' 
        url = f'{host}{endpoint}'
        
        # 헤더 설정 시 유효한 토큰 확보
        access_token = self._ensure_token() # 여기서 토큰 가져오기
        if not access_token:
             error_msg = "API 요청 실패: 유효한 토큰 없음"
             logger.error(error_msg)
             return {"error": error_msg, "return_code": -1}, '', 'ERR'
             
        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'authorization': f'Bearer {access_token}',
            'cont-yn': cont_yn,
            'next-key': next_key,
            'api-id': api_id,
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            self.logger.info(f'API 요청: {api_id} | URL: {url}')
            self.logger.debug(f'API 요청 헤더: {headers}')
            self.logger.debug(f'API 요청 데이터: {data}')
            
            self.logger.info(f'API 응답 상태 코드: {response.status_code}')
            response_json = {}
            next_key_resp = ''
            cont_yn_resp = 'N'
            
            try:
                response_json = response.json()
                # 디버깅: 특정 API ID의 원본 응답 로깅 강화
                if api_id == 'ka10001':
                    self.logger.debug(f'KiwomAPI Raw Response ({api_id}): {json.dumps(response_json, indent=2, ensure_ascii=False)}')
                else:
                    self.logger.debug(f'API 원본 응답 ({api_id}): {response_json}')
                next_key_resp = response.headers.get('next-key', '')
                cont_yn_resp = response.headers.get('cont-yn', 'N')
            except json.JSONDecodeError as e:
                self.logger.error(f'API 응답 JSON 파싱 실패 ({api_id}): {str(e)}, 응답: {response.text}')
                # JSON 파싱 실패 시에도 오류 코드 확인 시도 (가끔 텍스트로 올 수 있음)
                if response.status_code != 200:
                     return {}, '', 'ERR' # 실패로 간주
                # 200 OK인데 파싱 실패면 빈 데이터로 처리할 수 있으나, 헤더는 반환
                next_key_resp = response.headers.get('next-key', '')
                cont_yn_resp = response.headers.get('cont-yn', 'N')
                return {}, next_key_resp, cont_yn_resp
            
            # 응답 코드 확인 및 토큰 오류 시 재시도
            return_code = response_json.get("return_code", 0 if response.status_code == 200 else -1)
            
            # 인증 실패(8005) 또는 유효하지 않은 토큰(3) 오류 코드 확인
            # API 문서상 8005, 실제 응답은 3으로 올 수 있음 (로그 기반)
            if response.status_code == 200 and return_code in [3, 8005] and retries > 0:
                logger.warning(f"토큰 인증 실패 감지(code: {return_code}). 새 토큰 발급 후 재시도합니다...")
                self.access_token = None # 현재 토큰 무효화
                self.token_expires_at = 0
                new_token = self._ensure_token() # 새 토큰 강제 발급 (_get_access_token 호출)
                if new_token:
                    logger.info("새 토큰으로 API 요청 재시도")
                    # 재귀 호출 대신 한 번만 재시도
                    return self._api_request(api_id, data, cont_yn, next_key, retries=0) 
                else:
                    logger.error("새 토큰 발급 실패. API 요청 최종 실패.")
                    return response_json, '', 'ERR' # 토큰 발급 실패 시 오류 반환
            
            # 정상 응답 또는 재시도 없는 오류
            if response.status_code == 200 and return_code == 0:
                return response_json, next_key_resp, cont_yn_resp
            else:
                 # 오류 응답 로깅 강화
                 self.logger.error(f'API 오류 응답 ({api_id}): status={response.status_code}, code={return_code}, msg={response_json.get("return_msg", "N/A")}')
                 return response_json, '', 'ERR'
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f'API 요청 실패 ({api_id}): {str(e)}')
            return {}, '', 'ERR'

    def search_stock(self, query: str) -> List[Dict[str, Any]]:
        """종목 검색"""
        api_id = 'ka10095'  # 관심종목정보요청
        
        data = {
            "stk_cd": query,
        }
        
        # API 요청 및 응답 받기
        response_data, _, _ = self._api_request(api_id=api_id, data=data)
        
        # 원본 응답 로깅
        self.logger.debug(f"API 원본 응답: {response_data}")
        
        # atn_stk_infr 필드가 있으면 그대로 반환
        if isinstance(response_data, dict) and 'atn_stk_infr' in response_data:
            return response_data['atn_stk_infr']
        
        # response_data가 이미 리스트면 그대로 반환
        if isinstance(response_data, list):
            return response_data
            
        # 그 외의 경우는 빈 리스트 반환
        self.logger.warning(f"검색 결과 없음: {query}")
        return []
        
    def _convert_stock_data(self, stock: Dict) -> Dict:
        """API 응답 데이터를 내부 형식으로 변환"""
        try:
            # 필수 필드 확인
            stk_cd = stock.get('stk_cd')
            stk_nm = stock.get('stk_nm')
            
            if not stk_cd or not stk_nm:
                self.logger.warning(f"필수 필드(stk_cd/stk_nm) 누락: {stock}")
                return {}
                
            # 숫자 필드 안전하게 변환
            try:
                cur_prc = self._safe_number_str(stock.get('cur_prc', '0'))
                pred_pre = self._safe_number_str(stock.get('pred_pre', '0'))
                flu_rt = self._safe_number_str(stock.get('flu_rt', '0.00'))
            except Exception as e:
                self.logger.error(f"숫자 변환 오류: {str(e)}, 원본: {stock}")
                # 에러 발생 시 기본값 사용
                cur_prc = '0'
                pred_pre = '0'
                flu_rt = '0.00'
            
            return {
                'stk_cd': stk_cd,
                'stk_nm': stk_nm,
                'cur_prc': cur_prc,
                'base_pric': self._safe_number_str(stock.get('base_pric', '0')),
                'prc_diff': pred_pre,
                'prc_diff_sign': stock.get('pred_pre_sig', '3'),
                'fluc_rt': flu_rt,
                'flu_rt': flu_rt,  # 양쪽 필드명 모두 지원
                'trd_qty': self._safe_number_str(stock.get('trde_qty', '0')),
                'trde_qty': self._safe_number_str(stock.get('trde_qty', '0')),  # 양쪽 필드명 모두 지원
                'trde_prica': self._safe_number_str(stock.get('trde_prica', '0')),
                'raw_data': stock  # 원본 데이터 유지
            }
        except Exception as e:
            self.logger.error(f"데이터 변환 중 예상치 못한 오류: {str(e)}", exc_info=True)
            return {}
        
    def _safe_number_str(self, value) -> str:
        """숫자 값을 안전하게 문자열로 변환 (수정: '- 0' 처리 추가)"""
        if value is None:
            return '0'
        
        try:
            # 문자열인 경우 정리
            if isinstance(value, str):
                value = value.replace('+', '').replace(',', '').strip()
                # "- 0" 또는 "-0" 같은 특수 케이스 처리 -> '0'으로 변환
                # float 변환 시 발생할 수 있는 ValueError 처리
                try:
                    if value.startswith('-') and float(value) == 0:
                        return '0'
                except ValueError:
                    pass # 변환 실패 시 아래 로직 계속 진행
                # 음수 표기 정리 (공백이 있는 경우)
                if '- ' in value:
                    value = value.replace('- ', '-')
                return value if value else '0'
            # 숫자인 경우 문자열로 변환
            elif isinstance(value, (int, float)):
                return str(value)
            # 다른 타입의 경우
            else:
                self.logger.warning(f"예상치 못한 값 타입: {type(value)}, 값: {value}")
                return str(value)
        except Exception as e:
            self.logger.error(f"숫자 변환 오류: {str(e)}, 값: {value}")
            return '0'

    def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """종목 정보 조회 (기존 가공 로직 사용)"""
        try:
            logger.info(f"종목 정보 조회 시작: {stock_code}")
            api_id = STOCK_INFO_API_ID
            request_data = {"stk_cd": stock_code}
            response_data, _, _ = self._api_request(api_id=api_id, data=request_data)
            
            if not response_data or "return_code" not in response_data or response_data["return_code"] != 0:
                error_msg = response_data.get("return_msg", "알 수 없는 오류") if response_data else "응답 없음"
                logger.error(f"종목 정보 조회 실패: {error_msg}")
                return None
            
            if "atn_stk_infr" in response_data and response_data["atn_stk_infr"]:
                stock_data_raw = response_data["atn_stk_infr"][0]
                # 필요한 정보 추출 및 가공 (기존 로직 재활용 또는 개선)
                result = {
                    "stock_code": stock_data_raw.get("stk_cd", ""),
                    "stock_name": stock_data_raw.get("stk_nm", ""),
                    "current_price": self._parse_price(stock_data_raw.get("cur_prc", "0")),
                    "change_rate": stock_data_raw.get("flu_rt", "0.00"),
                    "volume": int(self._safe_number_str(stock_data_raw.get("trde_qty", "0"))),
                    "ask_price": self._parse_price(stock_data_raw.get("sel_bid", "0")),
                    "bid_price": self._parse_price(stock_data_raw.get("buy_bid", "0")),
                    "high_price": self._parse_price(stock_data_raw.get("high_pric", "0")),
                    "low_price": self._parse_price(stock_data_raw.get("low_pric", "0")),
                    "open_price": self._parse_price(stock_data_raw.get("open_pric", "0")),
                    "market_cap": stock_data_raw.get("cap", "0"),
                    # 추가 정보 필요시 여기에 추가
                }
                return result
            return None
        except Exception as e:
            logger.error(f"종목 정보 조회 중 오류 발생: {e}", exc_info=True)
            return None
    
    def search_stocks_by_name(self, stock_name: str) -> List[Dict[str, Any]]:
        """종목 이름으로 주식 검색
        
        Args:
            stock_name: 종목 이름 키워드
            
        Returns:
            List[Dict]: 검색된 종목 목록
        """
        try:
            # 실제 구현은 API가 이름 검색을 지원한다면 그것을 활용하는 것이 좋음
            # 여기서는 간단히 구현 (더미 데이터 반환)
            
            # 종목 검색 API 호출 코드 필요
            # 실제 API가 없다면 종목 마스터에서 필터링하는 방식으로 구현 가능
            
            # 예시 구현 (실제 구현은 API에 따라 달라질 수 있음)
            # 간단한 예시를 위해 몇 가지 종목만 반환
            if "삼성" in stock_name:
                return [
                    {
                        "stock_code": "005930",
                        "stock_name": "삼성전자",
                        "current_price": 73400
                    },
                    {
                        "stock_code": "005935",
                        "stock_name": "삼성전자우",
                        "current_price": 67500
                    }
                ]
            elif "현대" in stock_name:
                return [
                    {
                        "stock_code": "005380",
                        "stock_name": "현대차",
                        "current_price": 243500
                    },
                    {
                        "stock_code": "005385",
                        "stock_name": "현대차우",
                        "current_price": 118500
                    }
                ]
            elif "sk" in stock_name.lower():
                return [
                    {
                        "stock_code": "017670",
                        "stock_name": "SK텔레콤",
                        "current_price": 54200
                    },
                    {
                        "stock_code": "034730",
                        "stock_name": "SK",
                        "current_price": 156000
                    }
                ]
            else:
                # 실제 구현에서는 전체 종목 마스터에서 검색
                # 이 예시에서는 간단히 빈 결과 반환
                return []
                
        except Exception as e:
            logger.error(f"종목 이름 검색 중 오류 발생: {e}", exc_info=True)
            return []
    
    def _parse_price(self, price_str: str) -> int:
        """가격 문자열을 정수로 변환
        
        Args:
            price_str: 가격 문자열 (예: '+123', '-123', '123')
            
        Returns:
            int: 변환된 가격
        """
        try:
            # 부호 제거 및 콤마 제거
            price_str = price_str.replace(",", "")
            
            # 부호 처리
            if price_str.startswith('+'):
                price_str = price_str[1:]
            elif price_str.startswith('-'):
                price_str = price_str[1:]
                
            # 숫자 변환
            return int(price_str)
        except (ValueError, TypeError):
            return 0

    def get_stock_price(self, stock_code: str) -> dict:
        """종목 가격 정보 조회 (수정: 원본 ka10095 API 사용 및 응답 키 수정)"""
        try:
            logger.info(f"종목 가격 정보 조회 시작 (get_stock_price, API: ka10095): {stock_code}")
            api_id = STOCK_INFO_API_ID # ka10095 사용
            request_data = {"stk_cd": stock_code}
            
            # _api_request를 직접 호출하여 원본 데이터 가져오기
            response_data, _, _ = self._api_request(api_id=api_id, data=request_data)
            
            if not response_data or "return_code" not in response_data or response_data["return_code"] != 0:
                error_msg = response_data.get("return_msg", "알 수 없는 오류") if response_data else "응답 없음"
                logger.error(f"종목 가격 정보 조회 실패(ka10095): {error_msg}")
                return {}

            # ka10095 응답 구조에 맞게 수정 ("atn_stk_infr" 키 확인 - 원래 코드 기준)
            if "atn_stk_infr" in response_data and response_data["atn_stk_infr"]:
                stock_data_raw = response_data["atn_stk_infr"][0] # 리스트의 첫 번째 요소 사용
                
                # 필요한 모든 필드를 포함하여 반환 (stock_table.py 에서 사용하는 키 기준)
                price_data = {
                    'stk_cd': stock_data_raw.get("stk_cd", ""),
                    'stk_nm': stock_data_raw.get("stk_nm", ""),
                    'cur_prc': self._safe_number_str(stock_data_raw.get("cur_prc", "0")),
                    'pred_pre': self._safe_number_str(stock_data_raw.get("pred_pre", "0")), # 전일대비 값
                    'pred_pre_sig': stock_data_raw.get("pred_pre_sig", "0"), # 전일대비 부호
                    'flu_rt': self._safe_number_str(stock_data_raw.get("flu_rt", "0.00")),
                    'trde_qty': self._safe_number_str(stock_data_raw.get("trde_qty", "0")), # 필드명 확인 필요 (tot_trde_qty?)
                    'trde_prica': self._safe_number_str(stock_data_raw.get("trde_prica", "0")), # 필드명 확인 필요 (tot_trde_prica?)
                    'sel_bid': self._safe_number_str(stock_data_raw.get("sel_bid", "0")),
                    'buy_bid': self._safe_number_str(stock_data_raw.get("buy_bid", "0")),
                    'high_pric': self._safe_number_str(stock_data_raw.get("high_pric", "0")),
                    'low_pric': self._safe_number_str(stock_data_raw.get("low_pric", "0")),
                    'open_pric': self._safe_number_str(stock_data_raw.get("open_pric", "0")),
                    'cap': stock_data_raw.get("cap", "0"),
                    'raw_data': stock_data_raw # 원본 데이터도 포함
                }
                # 내부 키 이름 통일
                price_data['prc_diff'] = price_data['pred_pre']
                price_data['prc_diff_sign'] = price_data['pred_pre_sig']
                price_data['fluc_rt'] = price_data['flu_rt']
                price_data['trd_qty'] = price_data['trde_qty']
                price_data['trd_amt'] = price_data['trde_prica']

                return price_data
            else:
                logger.warning(f"API 응답(ka10095)에 'atn_stk_infr' 데이터 없음: {stock_code}")
                return {}

        except Exception as e:
            logger.error(f"종목 가격 정보 조회(ka10095) 중 오류 발생: {e}", exc_info=True)
            return {}

    def get_favorite_groups(self) -> List[Dict[str, Any]]:
        """관심종목 그룹 목록을 조회합니다. (수정: 임시로 기본 그룹 반환)"""
        # 요청 (ka10095: 관심종목정보요청) - ka10095는 stk_cd가 필수이므로 그룹 조회용으로 부적합. 임시 비활성화.
        # response_data, _, _ = self._api_request(api_id=FAVORITE_STOCK_API_ID, data={}) # Use FAVORITE_STOCK_API_ID if defined
        
        # if response_data and "return_code" in response_data and response_data["return_code"] == 0:
        #     try:
        #         # 실제 응답 구조에 따라 그룹 정보 추출 (예시)
        #         groups_raw = response_data.get("group_info", []) # API 문서 확인 필요
        #         groups = []
        #         for idx, grp in enumerate(groups_raw):
        #             groups.append({
        #                 "id": grp.get("group_id", idx + 1), # 실제 ID 필드명 확인 필요
        #                 "name": grp.get("group_name", f"그룹 {idx + 1}")
        #             })
        #         if groups:
        #             return groups
        #         else:
        #              logger.warning("API 응답에 그룹 정보 없음")
        #     except Exception as e:
        #         logger.error(f"관심종목 그룹 목록 처리 중 오류: {e}", exc_info=True)
        # else:
        #     error_msg = response_data.get("return_msg", "알 수 없는 오류") if response_data else "API 호출 실패"
        #     logger.error(f"관심종목 그룹 목록 조회 실패: {error_msg}")
            
        # --- 임시 코드: 기본 그룹 목록 반환 --- 
        logger.warning("get_favorite_groups: 임시로 기본 그룹 목록을 반환합니다. (API 호출 비활성화됨)")
        return [
            {"id": 1, "name": "기본 그룹"},
            {"id": 2, "name": "테마주"},
            {"id": 3, "name": "배당주"}
        ]
    
    def add_favorite_stock(self, stock_code: str, group_name: str) -> bool:
        """관심종목 추가
        
        Args:
            stock_code: 종목코드
            group_name: 그룹명
            
        Returns:
            성공 여부
        """
        # 요청 파라미터
        data = {
            "stk_cd": stock_code,
            "group_name": group_name
        }
        
        # 요청 (실제 API ID와 엔드포인트는 API 문서 참조)
        response_data, _, _ = self._api_request(api_id='ka10095', data=data)
        
        if 'error' in response_data:
            logger.error(f"관심종목 추가 실패: {response_data['error']}")
            return False
            
        # 성공 여부 확인 (응답 구조에 따라 조정 필요)
        return response_data.get("result") == "success"

    def revoke_token(self) -> bool:
        """액세스 토큰 폐기
        
        Returns:
            폐기 성공 여부
        """
        try:
            logger.info("액세스 토큰 폐기 시작")
            
            # 토큰이 없으면 폐기 불필요
            if not self.access_token:
                logger.info("폐기할 토큰이 없습니다.")
                return True
                
            # OAuth2 토큰 폐기 엔드포인트
            revoke_url = f"{self.base_url}/oauth2/revoke"
            
            # 요청 헤더
            headers = {
                "Content-Type": "application/json;charset=UTF-8"
            }
            
            # 요청 데이터
            data = {
                "appkey": self.api_key,
                "secretkey": self.api_secret,
                "token": self.access_token
            }
            
            logger.info(f"토큰 폐기 요청 URL: {revoke_url}")
            logger.debug(f"토큰 폐기 요청 헤더: {headers}")
            logger.info(f"토큰 폐기 파라미터: appkey={len(self.api_key) if self.api_key else 0}자리, secretkey={len(self.api_secret) if self.api_secret else 0}자리, token={self.access_token[:5]}...")
            
            # API 키와 시크릿이 유효한지 확인
            if not self.api_key or not self.api_secret:
                logger.error("API 키 또는 시크릿이 설정되지 않았습니다.")
                return False
            
            # 키움증권 API 서버에 토큰 폐기 요청
            response = requests.post(revoke_url, headers=headers, json=data)
            logger.info(f"토큰 폐기 응답 상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                # 응답 처리
                response_data = response.json()
                logger.debug(f"토큰 폐기 응답 데이터: {response_data}")
                
                # 토큰 폐기 후 초기화
                self.access_token = None
                self.token_expires_at = 0
                self.refresh_token = None
                
                # 토큰 파일 삭제
                if os.path.exists(self.TOKEN_FILE):
                    try:
                        os.remove(self.TOKEN_FILE)
                        logger.info(f"토큰 파일 삭제 완료: {self.TOKEN_FILE}")
                    except Exception as e:
                        logger.error(f"토큰 파일 삭제 실패: {e}")
                
                logger.info("액세스 토큰 폐기 완료")
                return True
            else:
                # 오류 처리
                try:
                    error_data = response.json()
                    error_message = f"토큰 폐기 실패: 상태 코드={response.status_code}, 내용={json.dumps(error_data)}"
                except Exception:
                    error_message = f"토큰 폐기 실패: 상태 코드={response.status_code}, 내용={response.text}"
                
                logger.error(error_message)
                return False
                
        except Exception as e:
            logger.error(f"액세스 토큰 폐기 중 오류 발생: {e}", exc_info=True)
            return False 

    def _get_trend_signal(self, change_rate_str: str) -> str:
        # ...
        return '3'

    def request_chart_data(self, stock_code: str, period: str, count: int = None) -> bool:
        """차트 데이터 요청
        
        Args:
            stock_code: 종목 코드
            period: 주기 (D, W, M, Y, 1, 3, 5, 10, 15, 30, 45, 60, 1T)
            count: 요청 데이터 개수 (기본값: 기간별 정의)
            
        Returns:
            요청 성공 여부
        """
        try:
            logger.info(f"차트 데이터 요청: {stock_code}, 주기={period}")
            self._chart_data = None  # 이전 데이터 초기화
            
            if not hasattr(self, 'chart') or not self.chart:
                logger.error("차트 API 인스턴스가 초기화되지 않았습니다")
                return False
                
            now = datetime.now()
            base_dt = now.strftime("%Y%m%d")  # 오늘 날짜를 기준으로
            
            # API ID와 엔드포인트, 파라미터 설정
            api_id = None
            endpoint = "/api/dostk/chart"
            url = f"{self.base_url}{endpoint}"
            
            data = {
                "stk_cd": stock_code,
                "base_dt": base_dt,
                "upd_stkpc_tp": "1"  # 수정주가 적용 (1: 적용, 0: 미적용)
            }
            
            # 주기에 따른 API ID 및 추가 파라미터 설정
            if period in ['D', 'd', 'day', 'D1']:
                api_id = "ka10081"  # 일봉
            elif period in ['W', 'w', 'week']:
                api_id = "ka10082"  # 주봉
            elif period in ['M', 'm', 'month']:
                api_id = "ka10083"  # 월봉
            elif period in ['Y', 'y', 'year']:
                api_id = "ka10094"  # 년봉
            elif period.endswith('T') or period == '1T':
                api_id = "ka10079"  # 틱
                data["tic_scope"] = period.replace('T', '')  # 1T -> 1
            else:
                # 분봉 (1, 3, 5, 10, 15, 30, 45, 60)
                api_id = "ka10080"
                data["tic_scope"] = period  # 분 단위
            
            # 데이터 개수 설정 (기본값)
            if count is None:
                if period in ['D', 'd', 'day', 'D1']:
                    count = 200
                elif period in ['W', 'w', 'week']:
                    count = 100
                elif period in ['M', 'm', 'month', 'Y', 'y', 'year']:
                    count = 60
                else:
                    count = 500
            
            # API 요청 헤더 구성
            headers = {
                'Content-Type': 'application/json;charset=UTF-8',
                'authorization': f'Bearer {self.access_token}',
                'cont-yn': 'N',  # 연속조회 여부
                'next-key': '',  # 연속조회 키
                'api-id': api_id,  # TR 명
            }
            
            # API 호출
            logger.info(f"차트 API 요청: {api_id} | URL: {url}")
            logger.debug(f"차트 API 요청 데이터: {data}")
            
            response = requests.post(url, headers=headers, json=data, verify=self.verify_ssl)
            
            # 응답 처리
            if response.status_code != 200:
                logger.error(f"차트 데이터 API 오류: {response.status_code}, {response.text}")
                return False
                
            response_data = response.json()
            
            # 응답 데이터에서 차트 데이터 추출
            if response_data.get('return_code') != 0:
                logger.error(f"차트 데이터 API 응답 오류: {response_data.get('return_msg')} (코드: {response_data.get('return_code')})")
                return False
            
            # API ID에 따른 응답 키 추출
            from .kiwoom_chart import RESPONSE_KEYS
            response_keys = RESPONSE_KEYS.get(api_id, RESPONSE_KEYS["fallback"])
            
            # 실제 차트 데이터 추출
            chart_data = None
            for key in response_keys:
                if key in response_data:
                    chart_data = response_data[key]
                    break
            
            if not chart_data:
                logger.error(f"API 응답에 차트 데이터가 없습니다: {list(response_data.keys())}")
                return False
            
            self._chart_data = chart_data
            logger.info(f"차트 데이터 수신 완료: {len(chart_data)}개")
            return True
            
        except Exception as e:
            logger.error(f"차트 데이터 요청 중 오류: {e}", exc_info=True)
            return False

    def get_chart_data(self):
        """마지막으로 요청한 차트 데이터 반환"""
        return self._chart_data if self._chart_data else []

    def _get_headers(self, api_id=None, cont_yn=None, next_key=None):
        """인증 헤더 생성"""
        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'authorization': f'Bearer {self.access_token}'
        }
        
        # 연속 조회 관련 헤더 추가
        if cont_yn is not None:
            headers['cont-yn'] = cont_yn
        else:
            headers['cont-yn'] = 'N'
            
        if next_key is not None:
            headers['next-key'] = next_key
        else:
            headers['next-key'] = ''
            
        # API ID 추가 (필요시)
        if api_id is not None:
            headers['api-id'] = api_id
            
        return headers

    def _convert_period_to_api_code(self, period: str) -> str:
        """주기를 API 코드로 변환하는 함수"""
        # 기간 매핑 정의
        period_mapping = {
            'Y': 'Y',  # 년
            'M': 'M',  # 월
            'W': 'W',  # 주
            'D': 'D',  # 일
            '1': '1',  # 1분
            '3': '3',  # 3분
            '5': '5',  # 5분
            '10': '10',  # 10분
            '15': '15',  # 15분
            '30': '30',  # 30분
            '45': '45',  # 45분
            '60': '60',  # 60분
            '1T': 'T1',  # 1틱
        }
        
        # 매핑된 코드 반환 (없으면 그대로 반환)
        return period_mapping.get(period, period)

    def call_api(self, api_id: str, params: dict) -> dict:
        """API 요청 전송 및 응답 처리
        
        Args:
            api_id: API ID (예: 'ka10081' - 일봉 차트 조회)
            params: API 요청 파라미터
            
        Returns:
            API 응답 데이터
        """
        try:
            self.logger.info(f"API 호출 시작: {api_id}, 파라미터: {params}")
            
            # 키움 API 공식 가이드 방식으로 직접 HTTP 요청
            if self.is_real:
                host = 'https://api.kiwoom.com'  # 실전투자 URL
            else:
                host = 'https://openapi.kiwoom.com'  # 모의투자 URL
                
            # API ID에 따른 엔드포인트 선택
            if api_id in ['ka10081', 'ka10082', 'ka10083', 'ka10094', 'ka10079', 'ka10080']:  # 차트 관련 API
                endpoint = '/api/dostk/chart'
            elif api_id == 'ka10095':  # 관심종목정보요청
                endpoint = '/api/attnstkinfo'
            else:
                # 다른 API ID에 대한 엔드포인트는 필요에 따라 추가
                endpoint = self._get_endpoint_by_api_id(api_id)
                
            url = f'{host}{endpoint}'
            
            # 유효한 토큰 확보
            access_token = self._ensure_token()
            if not access_token:
                error_msg = "API 요청 실패: 유효한 토큰 없음"
                self.logger.error(error_msg)
                return {"return_code": -1, "return_msg": error_msg}
                
            # 키움 API 공식 헤더 설정
            headers = {
                'Content-Type': 'application/json;charset=UTF-8',  # 컨텐츠타입
                'authorization': f'Bearer {access_token}',  # 접근토큰
                'cont-yn': 'N',  # 연속조회여부
                'next-key': '',  # 연속조회키
                'api-id': api_id,  # TR명
            }
            
            # 상세 로깅
            self.logger.info(f"API URL: {url}")
            self.logger.info(f"API Headers: {headers}")
            
            # HTTP POST 요청 직접 수행
            response = requests.post(url, headers=headers, json=params, timeout=10)
            
            # 응답 헤더 및 상태 코드 로깅
            self.logger.info(f'API 응답 상태 코드: {response.status_code}')
            self.logger.info(f'API 응답 헤더: {dict(response.headers)}')
            
            # 응답 데이터 파싱
            response_data = {}
            try:
                response_data = response.json()
                self.logger.debug(f'API 원본 응답 ({api_id}): {response_data}')
            except json.JSONDecodeError as e:
                self.logger.error(f'API 응답 JSON 파싱 실패 ({api_id}): {str(e)}, 응답: {response.text}')
                return {"return_code": -1, "return_msg": f"JSON 파싱 실패: {str(e)}"}
            
            # 응답 코드 확인
            return_code = response_data.get("return_code")
            if return_code != 0:
                error_msg = response_data.get("return_msg", "알 수 없는 오류")
                self.logger.error(f"API 오류 응답: {api_id}, 코드={return_code}, 메시지={error_msg}")
            else:
                self.logger.info(f"API 요청 성공: {api_id}")
                
            return response_data
                
        except Exception as e:
            self.logger.error(f"API 호출 중 예외 발생: {e}", exc_info=True)
            return {"return_code": -999, "return_msg": f"예외 발생: {str(e)}"}