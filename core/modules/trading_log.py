import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import os

# 프로젝트 내 모듈 임포트
from core.database import db_manager
from core.database.models.trading_log_models import TradingLog, TradingLogDetail, StrategyLearning
from core.database.models.strategy_models import Strategy # 타입 힌팅용
from core.api.openai import OpenAIAPI # 실제 API 키 로딩 및 인스턴스 생성 필요
# from config import settings # API 키 로딩 예시

logger = logging.getLogger(__name__)

# --- 임시 데이터 및 Mock 함수 --- 
# TODO: 실제 매매 데이터 연동 모듈 구현 시 대체 필요
def get_mock_trade_data(log_date: date, strategy_id: int) -> List[Dict[str, Any]]:
    """지정된 날짜와 전략 ID에 대한 임시 매매 데이터 반환"""
    logger.info(f"{log_date} / 전략 {strategy_id} 에 대한 임시 매매 데이터 조회")
    # 예시 데이터: 실제로는 DB 조회 또는 API 호출 결과가 될 것
    if strategy_id == 1 and log_date == date(2024, 4, 1): # 특정 조건일 때만 데이터 반환
        return [
            {'stock_code': '005930', 'trade_time': datetime(2024, 4, 1, 9, 30, 0), 'trade_type': 'buy', 'price': 85000, 'quantity': 10},
            {'stock_code': '035720', 'trade_time': datetime(2024, 4, 1, 10, 15, 0), 'trade_type': 'buy', 'price': 510000, 'quantity': 2},
            {'stock_code': '005930', 'trade_time': datetime(2024, 4, 1, 14, 45, 0), 'trade_type': 'sell', 'price': 85500, 'quantity': 10},
        ]
    return []

# TODO: OpenAIAPI 클래스에 analyze_daily_trades 메서드 구현 필요
# 임시 OpenAI API 클라이언트 (실제로는 설정에서 키를 로드해야 함)
try:
    # 실제 API 키 로딩 로직 필요
    # 예: from config import settings; openai_api = OpenAIAPI(settings.OPENAI_API_KEY)
    openai_api = OpenAIAPI(api_key="YOUR_DUMMY_API_KEY") # 임시 키
except Exception as e:
    logger.error(f"OpenAI API 클라이언트 생성 실패: {e}")
    openai_api = None

def analyze_trading_log_with_ai_mock(trade_data: List[Dict[str, Any]], strategy_info: Dict) -> Dict[str, Any]:
    """AI 분석 Mock 함수. 실제로는 OpenAI API 호출 필요."""
    logger.info("AI 매매일지 분석 시뮬레이션 시작")
    if not openai_api:
        logger.warning("OpenAI API 클라이언트가 초기화되지 않아 Mock 분석을 수행합니다.")
        
    overall_review = f"전략 ID {strategy_info.get('id', 'N/A')} ({strategy_info.get('name', 'Unknown Strategy')})에 대한 {len(trade_data)}건의 매매 복기 결과입니다.\n- 전반적으로 안정적인 수익을 기록했습니다.\n- 다만, 005930 종목의 매도 타이밍이 약간 빨랐을 수 있습니다."
    
    detailed_analysis = []
    for trade in trade_data:
        analysis = {
            "stock_code": trade['stock_code'],
            "trade_time": trade['trade_time'],
            "ai_reason": f"({trade['trade_type']}) 시장 상황과 전략 규칙에 따른 표준적인 진입/청산으로 보입니다.",
            "ai_reflection": f"해당 거래는 무난했으나, {trade['stock_code']}의 변동성을 고려할 때 진입/청산 근거를 강화할 필요가 있습니다.",
            "ai_improvement": "다음 거래 시에는 변동성 지표(예: ATR)를 추가로 확인하세요."
        }
        detailed_analysis.append(analysis)
        
    learning_content = "손절 라인(-5%)이 일부 변동성 큰 장세에서 너무 타이트하게 작동하는 경향 발견. 백테스팅 결과 -7% 조정 시 수익률 개선 확인됨. 전략 파라미터 업데이트 고려 필요."
    
    logger.info("AI 매매일지 분석 시뮬레이션 완료")
    return {
        "overall_review": overall_review,
        "details": detailed_analysis,
        "learning": learning_content
    }

# --- 실제 데이터 조회 및 API 연동 --- 
# TODO: 실제 매매 데이터 연동 모듈 구현 필요
def get_trade_data(log_date: date, strategy_id: int) -> List[Dict[str, Any]]:
    """지정된 날짜와 전략 ID에 대한 실제 매매 데이터 반환 (구현 필요)"""
    logger.info(f"{log_date} / 전략 {strategy_id} 에 대한 실제 매매 데이터 조회 시도...")
    # -------------------------------------------------------------
    # 여기에 실제 DB 조회 또는 거래 시스템 API 호출 로직 구현!
    # 예시: 
    # from core.trading import trade_manager 
    # try:
    #     trades = trade_manager.get_trades_for_date_strategy(log_date, strategy_id)
    #     logger.info(f"조회된 매매 내역: {len(trades)}건")
    #     return trades
    # except Exception as e:
    #     logger.error(f"매매 데이터 조회 실패: {e}")
    #     return []
    # -------------------------------------------------------------
    
    # 구현 전까지는 비어있는 리스트 반환 (Mock 데이터 반환 제거)
    logger.warning("get_trade_data: 실제 매매 데이터 조회 로직 구현 필요. 현재 빈 리스트 반환.")
    return [] 

# OpenAI API 클라이언트 초기화
try:
    # TODO: 실제 API 키 로딩 로직 구현 필요 (예: 설정 파일 또는 환경 변수)
    # from config import settings 
    # openai_api_key = settings.OPENAI_API_KEY
    openai_api_key = os.getenv("OPENAI_API_KEY", "YOUR_DUMMY_API_KEY_NEEDS_REPLACEMENT") # 환경 변수 예시
    if not openai_api_key or "DUMMY" in openai_api_key:
        logger.warning("OpenAI API 키가 설정되지 않았거나 유효하지 않습니다. AI 분석이 Mock으로 동작합니다.")
        openai_api = None
    else:
        openai_api = OpenAIAPI(api_key=openai_api_key)
        logger.info("OpenAI API 클라이언트 초기화 완료.")
except Exception as e:
    logger.error(f"OpenAI API 클라이언트 생성 실패: {e}", exc_info=True)
    openai_api = None

def analyze_trading_log_with_ai(trade_data: List[Dict[str, Any]], strategy_info: Strategy) -> Dict[str, Any]:
    """OpenAI API를 호출하여 매매일지 분석 (실제 연동)"""
    if not openai_api:
        logger.warning("OpenAI API 사용 불가. Mock 분석 결과 반환.")
        mock_info_dict = {"id": strategy_info.id, "name": strategy_info.name, "description": strategy_info.description}
        return analyze_trading_log_with_ai_mock(trade_data, mock_info_dict)
        
    logger.info(f"전략 '{strategy_info.name}' (ID: {strategy_info.id})에 대한 AI 분석 시작...")
    try:
        # OpenAIAPI 클래스에 analyze_daily_trades 메서드 호출
        analysis_result = openai_api.analyze_daily_trades(trade_data, strategy_info)
        
        logger.info(f"AI 분석 완료 (전략 ID: {strategy_info.id})")
        return analysis_result
        
    except Exception as e:
        logger.exception(f"AI 매매일지 분석 중 오류 발생 (전략 ID: {strategy_info.id}): {e}")
        mock_info_dict = {"id": strategy_info.id, "name": strategy_info.name, "description": strategy_info.description}
        return analyze_trading_log_with_ai_mock(trade_data, mock_info_dict) 

# --- 핵심 로직 함수 --- 

def create_trading_log(log_date: date, strategy_id: int, is_manual_trigger: bool = False) -> Optional[TradingLog]:
    """매매일지를 생성하고 AI 분석을 수행하여 DB에 저장"""
    logger.info(f"매매일지 생성 시작 - 날짜: {log_date}, 전략 ID: {strategy_id}, 수동실행: {is_manual_trigger}")

    # 1. 기존 자동 생성 로그 확인
    if db_manager.check_log_exists(log_date, strategy_id):
        logger.warning(f"{log_date} / 전략 {strategy_id} 에 대한 자동 생성된 매매일지가 이미 존재합니다. 생성을 건너뛰니다.")
        if is_manual_trigger:
            print("해당 날짜/전략의 자동 생성된 매매일지가 이미 존재하여 수동 생성이 불가능합니다.")
        return None

    # 2. 실제 매매 데이터 가져오기 (get_trade_data 호출)
    trade_data = get_trade_data(log_date, strategy_id)
    if not trade_data:
        logger.info(f"{log_date} / 전략 {strategy_id} 에 대한 매매 내역이 없습니다. 일지를 생성하지 않습니다.")
        return None
        
    # 3. 전략 정보 조회
    strategy_info = db_manager.get_strategy_by_id(strategy_id)
    if not strategy_info:
        logger.error(f"전략 정보 조회 실패 (ID: {strategy_id}). 매매일지를 생성할 수 없습니다.")
        return None

    # 4. AI 분석 수행 (analyze_trading_log_with_ai 호출)
    ai_analysis_result = analyze_trading_log_with_ai(trade_data, strategy_info)

    # 5. DB 저장 준비
    log_master_data = {
        'log_date': datetime.combine(log_date, datetime.min.time()), 
        'strategy_id': strategy_id,
        'ai_model': "gpt-4o" if openai_api else "gpt-4o (Mock)", # 실제 사용 모델 또는 Mock 표시
        'overall_review': ai_analysis_result['overall_review'],
        'is_auto_generated': not is_manual_trigger 
    }

    # 상세 분석 결과와 매매 데이터를 매핑 (trade_time 기준으로)
    log_details_data = []
    ai_details_map = {(d['stock_code'], d['trade_time']): d for d in ai_analysis_result['details']}
    
    for trade in trade_data:
        key = (trade['stock_code'], trade['trade_time'])
        ai_specifics = ai_details_map.get(key, {}) 
        
        log_details_data.append({
            **trade, 
            'ai_reason': ai_specifics.get('ai_reason'),
            'ai_reflection': ai_specifics.get('ai_reflection'),
            'ai_improvement': ai_specifics.get('ai_improvement')
        })

    learning_data = {
        'strategy_id': strategy_id,
        'learning_content': ai_analysis_result['learning'],
    }

    # 6. DB 저장
    try:
        log_master = db_manager.add_trading_log(log_master_data)
        if log_master:
            logger.info(f"매매일지 마스터 레코드 생성 완료 (ID: {log_master.id})")
            # 상세 내역 저장
            success_details = db_manager.add_trading_log_details(log_master.id, log_details_data)
            if not success_details:
                logger.error(f"매매일지 상세 내역 저장 실패 (Log ID: {log_master.id})")
                # TODO: 롤백 또는 에러 처리 로직 필요
                return None 
                
            # 학습 결과 저장
            learning_data['log_id'] = log_master.id # 생성된 log_id 설정
            learning_record = db_manager.add_strategy_learning(learning_data)
            if not learning_record:
                logger.error(f"전략 학습 결과 저장 실패 (Log ID: {log_master.id})")
                # TODO: 롤백 또는 에러 처리 로직 필요
                return None
                
            logger.info(f"매매일지 및 관련 데이터 저장 완료 (Log ID: {log_master.id})")
            return log_master
        else:
            logger.error("매매일지 마스터 레코드 생성 실패")
            return None
    except Exception as e:
        logger.exception(f"매매일지 저장 중 예외 발생: {e}")
        return None

# --- 향후 추가될 함수들 ---

def trigger_automatic_log_creation(log_date: Optional[date] = None):
    """모든 활성 전략에 대해 지정된 날짜의 매매일지 자동 생성을 시도합니다.

    Args:
        log_date: 일지를 생성할 대상 날짜. None이면 어제 날짜를 사용합니다.
    """
    if log_date is None:
        log_date = date.today() - timedelta(days=1)
        # TODO: 실제로는 주말/공휴일 제외 마지막 거래일을 계산하는 로직 필요
        logger.info(f"대상 날짜가 지정되지 않아 어제 날짜({log_date})를 사용합니다.")
    else:
        logger.info(f"지정된 대상 날짜({log_date})에 대한 자동 일지 생성을 시작합니다.")

    strategies = db_manager.get_strategies()
    if not strategies:
        logger.warning("자동 생성할 전략이 없습니다.")
        return

    logger.info(f"총 {len(strategies)}개의 전략에 대해 자동 매매일지 생성을 시도합니다...")
    success_count = 0
    skipped_count = 0
    error_count = 0

    for strategy in strategies:
        logger.debug(f"전략 '{strategy.name}' (ID: {strategy.id}) 처리 중...")
        try:
            # is_manual_trigger=False로 자동 생성 시도
            created_log = create_trading_log(log_date, strategy.id, is_manual_trigger=False)
            
            if created_log is None:
                # create_trading_log 내부에서 이미 로그 존재 또는 데이터 없음 로그 기록됨
                skipped_count += 1
            elif created_log:
                 logger.info(f"전략 '{strategy.name}' (ID: {strategy.id}) 자동 일지 생성 성공 (Log ID: {created_log.id})")
                 success_count += 1
            else: # 명시적으로 False가 반환되는 경우는 없지만 방어적으로 처리
                logger.error(f"전략 '{strategy.name}' (ID: {strategy.id}) 자동 일지 생성 실패 (알 수 없는 오류)")
                error_count += 1
                
        except Exception as e:
            logger.exception(f"전략 '{strategy.name}' (ID: {strategy.id}) 처리 중 예외 발생: {e}")
            error_count += 1
            
    logger.info(f"자동 매매일지 생성 완료 - 성공: {success_count}, 건너뛴: {skipped_count}, 오류: {error_count}")

# def get_log_for_display(log_id: int):
#     """UI 표시에 필요한 형태로 로그 데이터 조회 및 가공"""
#     pass

# 스크립트 직접 실행 시 테스트
if __name__ == "__main__":
    print("매매일지 모듈 테스트 시작...")
    # DB 초기화 확인 (db_manager 실행 시 이미 수행되었을 수 있음)
    # db_manager.init_db()
    
    test_log_date = date(2024, 4, 1)
    test_strategy_id = 1
    
    print(f"\n{test_log_date} / 전략 {test_strategy_id} 수동 생성 테스트 (최초):")
    created_log = create_trading_log(test_log_date, test_strategy_id, is_manual_trigger=True)
    if created_log:
        print(f"수동 생성 성공: Log ID {created_log.id}")
    else:
        print("수동 생성 실패 또는 이미 존재")
        
    print(f"\n{test_log_date} / 전략 {test_strategy_id} 자동 생성 테스트 (중복 시도):")
    created_log_auto = create_trading_log(test_log_date, test_strategy_id, is_manual_trigger=False)
    if created_log_auto:
        print(f"자동 생성 성공: Log ID {created_log_auto.id}") # 이 경우는 거의 발생 안 함
    else:
        print("자동 생성 실패 또는 이미 존재")
        
    print(f"\n{test_log_date} / 전략 {test_strategy_id} 수동 생성 테스트 (중복 시도):")
    created_log_manual_again = create_trading_log(test_log_date, test_strategy_id, is_manual_trigger=True)
    if created_log_manual_again:
        print(f"수동 생성 성공: Log ID {created_log_manual_again.id}") # 이 경우는 거의 발생 안 함
    else:
        print("수동 생성 실패 또는 이미 존재")
        
    print("\n매매 내역 없는 경우 테스트:")
    no_trade_date = date(2024, 4, 2)
    created_log_no_trade = create_trading_log(no_trade_date, test_strategy_id)
    if not created_log_no_trade:
        print("매매 내역 없어 생성 안됨 (정상)")
        
    print("\nDB 조회 테스트:")
    logs = db_manager.get_trading_logs(log_date=test_log_date, strategy_id=test_strategy_id)
    if logs:
        print(f"조회된 로그 수: {len(logs)}")
        for log in logs:
            print(f"- Log ID: {log.id}, 자동생성: {log.is_auto_generated}")
            print(f"  Review: {log.overall_review[:50]}...")
            print(f"  Details: {len(log.details)} 건")
            print(f"  Learnings: {len(log.learnings)} 건")
    else:
        print("조회된 로그 없음")
        
    print("\n자동 생성 트리거 테스트 (어제 날짜):")
    trigger_automatic_log_creation()

    print("\n매매일지 모듈 테스트 완료.") 