import logging
import json
import requests
import os
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# 키움 API 토큰 파일 경로
TOKEN_FILE = os.path.join('data', 'kiwoom_token.json')

def load_token():
    """토큰 파일에서 액세스 토큰 로드"""
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                token_data = json.load(f)
                logger.info(f"토큰 로드 성공: 만료시간 {token_data.get('expires_at')}")
                return token_data.get('access_token')
        logger.error(f"토큰 파일이 존재하지 않음: {TOKEN_FILE}")
    except Exception as e:
        logger.error(f"토큰 로드 오류: {e}")
    return None

def test_chart_api():
    """일봉 차트 API 테스트"""
    # 1. 액세스 토큰 로드
    access_token = load_token()
    if not access_token:
        logger.error("액세스 토큰 없음. 테스트 불가")
        return
    
    # 2. API 요청 파라미터 설정
    params = {
        'stk_cd': '005930',      # 종목코드 (삼성전자)
        'base_dt': '20250403',   # 기준일자 YYYYMMDD
        'upd_stkpc_tp': '1'      # 수정주가구분 0 or 1
    }
    
    # 3. API 요청 헤더 설정
    host = 'https://api.kiwoom.com'  # 실전투자
    endpoint = '/api/dostk/chart'
    url = host + endpoint
    
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',  # 컨텐츠타입
        'authorization': f'Bearer {access_token}',         # 접근토큰
        'cont-yn': 'N',                                    # 연속조회여부
        'next-key': '',                                    # 연속조회키
        'api-id': 'ka10081',                              # TR명
    }
    
    # 4. API 요청 상세 로깅
    logger.info(f"일봉 API URL: {url}")
    logger.info(f"일봉 API Headers: {headers}")
    logger.info(f"일봉 API Params: {params}")
    
    # 5. HTTP POST 요청 직접 수행
    try:
        response = requests.post(url, headers=headers, json=params, timeout=10)
        
        # 6. 응답 헤더 및 상태 코드 로깅
        logger.info(f'API 응답 상태 코드: {response.status_code}')
        logger.info(f'API 응답 헤더: {dict(response.headers)}')
        
        # 7. 응답 데이터 파싱
        try:
            response_data = response.json()
            logger.info(f'API 응답 코드: {response_data.get("return_code")}, 메시지: {response_data.get("return_msg")}')
            
            # 8. 응답 내 stk_dt_pole_chart_qry 필드 확인
            if 'stk_dt_pole_chart_qry' in response_data:
                chart_data = response_data['stk_dt_pole_chart_qry']
                logger.info(f"일봉 데이터 필드 확인: {len(chart_data)}개 항목")
                
                if chart_data:
                    # 첫 번째와 마지막 데이터만 로깅
                    logger.info(f"첫 번째 데이터: {chart_data[0]}")
                    logger.info(f"마지막 데이터: {chart_data[-1]}")
            else:
                logger.warning(f"일봉 데이터 필드(stk_dt_pole_chart_qry) 없음. 응답 키: {list(response_data.keys())}")
                logger.info(f"전체 응답: {response_data}")
        except json.JSONDecodeError as e:
            logger.error(f'API 응답 JSON 파싱 실패: {str(e)}, 응답: {response.text}')
    except Exception as e:
        logger.error(f"API 호출 중 예외 발생: {e}", exc_info=True)

if __name__ == "__main__":
    logger.info("일봉 차트 API 테스트 시작")
    test_chart_api()
    logger.info("일봉 차트 API 테스트 종료") 