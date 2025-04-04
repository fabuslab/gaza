import requests
import json
import datetime
import os

# 주식일봉차트조회요청
def fn_ka10081(token, data, cont_yn='N', next_key=''):
    # 1. 요청할 API URL
    #host = 'https://mockapi.kiwoom.com' # 모의투자
    host = 'https://api.kiwoom.com' # 실전투자
    endpoint = '/api/dostk/chart'
    url =  host + endpoint

    # 2. header 데이터
    headers = {
        'Content-Type': 'application/json;charset=UTF-8', # 컨텐츠타입
        'authorization': f'Bearer {token}', # 접근토큰
        'cont-yn': cont_yn, # 연속조회여부
        'next-key': next_key, # 연속조회키
        'api-id': 'ka10081', # TR명
    }

    print(f"\n전송할 헤더: {headers}")
    print(f"전송할 데이터: {data}")

    # 3. http POST 요청
    response = requests.post(url, headers=headers, json=data)

    # 4. 응답 상태 코드와 데이터 출력
    print('\nAPI 응답:')
    print('Code:', response.status_code)
    print('Header:', json.dumps({key: response.headers.get(key) for key in ['next-key', 'cont-yn', 'api-id']}, indent=4, ensure_ascii=False))
    
    # 응답 상태 코드가 200이 아닌 경우
    if response.status_code != 200:
        print(f"오류 응답: {response.text}")
        return None
    
    # JSON 응답 파싱 및 반환
    try:
        response_json = response.json()
        # 응답 데이터 출력 (간략화)
        items_count = len(response_json.get('stk_dt_pole_chart_qry', []))
        print(f"응답 데이터: 총 {items_count}개 항목")
        
        # 처음 3개 항목만 출력
        if items_count > 0:
            print("응답 데이터 샘플 (첫 3개 항목):")
            for item in response_json.get('stk_dt_pole_chart_qry', [])[:3]:
                print(json.dumps(item, indent=4, ensure_ascii=False))
                
        return response_json
    except json.JSONDecodeError:
        print(f"JSON 응답 파싱 오류: {response.text}")
        return None

# 응답 데이터를 처리하고 차트 데이터 추출하는 함수
def process_chart_data(response_data):
    if not response_data or 'return_code' not in response_data or response_data['return_code'] != 0:
        print(f"API 오류 응답 또는 유효하지 않은 응답: {response_data}")
        return []
    
    # 차트 데이터 목록 추출
    chart_data = response_data.get('stk_dt_pole_chart_qry', [])
    if not chart_data:
        print("차트 데이터가 없습니다.")
        return []
    
    # 데이터 처리 및 출력
    processed_data = []
    for item in chart_data:
        # 날짜 변환
        date_str = item.get('dt', '')
        
        # 가격 및 거래량
        open_price = item.get('open_pric', '0').replace(',', '')
        high_price = item.get('high_pric', '0').replace(',', '')
        low_price = item.get('low_pric', '0').replace(',', '')
        close_price = item.get('cur_prc', '0').replace(',', '')
        volume = item.get('trde_qty', '0').replace(',', '')
        
        processed_item = {
            'date': date_str,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        }
        processed_data.append(processed_item)
    
    return processed_data

# 실행 구간
if __name__ == '__main__':
    print("키움 API 일봉 차트 데이터 조회 테스트")
    print("-" * 50)
    
    # 액세스 토큰 입력 받기
    print("\n키움 API 액세스 토큰을 입력하세요:")
    MY_ACCESS_TOKEN = input("> ")
    
    if not MY_ACCESS_TOKEN:
        print("토큰이 없으면 API를 호출할 수 없습니다. 프로그램을 종료합니다.")
        exit(1)
    
    # 종목코드 입력 받기
    print("\n종목코드를 입력하세요 (기본값: 005930 - 삼성전자):")
    stock_code = input("> ").strip() or '005930'
    
    # 기준일자 설정 (오늘 날짜)
    base_dt = datetime.datetime.now().strftime("%Y%m%d")
    
    print(f"\n{stock_code} 종목의 일봉 데이터를 조회합니다...")
    print(f"기준일자: {base_dt}")
    
    # 요청 데이터
    params = {
        'stk_cd': stock_code,      # 종목코드
        'base_dt': base_dt,        # 기준일자 YYYYMMDD
        'upd_stkpc_tp': '1',       # 수정주가구분 0 or 1
    }
    
    # API 호출
    print("\nAPI 호출 중...")
    response_data = fn_ka10081(token=MY_ACCESS_TOKEN, data=params)
    
    if response_data:
        # 응답 처리
        chart_data = process_chart_data(response_data)
        
        # 결과 출력
        print("\n처리된 차트 데이터 (최근 5개):")
        for i, item in enumerate(chart_data[:5]):
            print(f"{i+1}. 날짜: {item['date']}, 시가: {item['open']}, 고가: {item['high']}, 저가: {item['low']}, 종가: {item['close']}, 거래량: {item['volume']}")
        
        # 데이터 개수 출력
        print(f"\n총 {len(chart_data)}개의 일봉 데이터를 받았습니다.")
    else:
        print("\nAPI 호출에 실패했습니다.")
    
    # 연속조회 처리
    if response_data:
        next_key = response_data.get('next-key', '')
        cont_yn = response_data.get('cont-yn', 'N')
        
        if cont_yn == 'Y' and next_key:
            print(f"\n연속조회가 가능합니다. 연속 조회를 하시겠습니까? (y/n)")
            choice = input("> ").strip().lower()
            
            if choice == 'y':
                print("\n연속 조회 중...")
                cont_response = fn_ka10081(token=MY_ACCESS_TOKEN, data=params, cont_yn='Y', next_key=next_key)
                if cont_response:
                    cont_chart_data = process_chart_data(cont_response)
                    print(f"\n연속 조회로 추가 {len(cont_chart_data)}개의 데이터를 받았습니다.")
    
    print("\n프로그램 종료") 