import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, relationship
from contextlib import contextmanager
from typing import Generator, Optional, List, Dict, Any
from datetime import date, datetime

# 데이터베이스 파일 경로 설정 (프로젝트 루트의 data 폴더 아래)
# __file__은 현재 파일(db_manager.py)의 경로
# os.path.dirname()으로 디렉토리 경로 추출
# os.path.abspath()로 절대 경로화
# os.path.join()으로 상위 디렉토리(core) -> 프로젝트 루트 -> data 폴더 경로 조합
DATABASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data')
DATABASE_FILE = 'trading_gaza.db'
DATABASE_PATH = os.path.join(DATABASE_DIR, DATABASE_FILE)
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

# 디렉토리 존재 확인 및 생성
os.makedirs(DATABASE_DIR, exist_ok=True)

# SQLAlchemy 엔진 생성
# check_same_thread=False 는 SQLite 사용 시 여러 스레드에서 접근해야 할 경우 필요 (GUI 환경 고려)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# 세션 메이커 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모든 모델의 Base 가져오기 (개선 필요)
# 이상적으로는 모든 모델이 공유하는 단일 Base 객체를 가져와야 합니다.
# 여기서는 임시로 trading_log_models의 Base를 사용합니다.
# 향후 다른 모델 추가 시 `core.database.models.base` 같은 파일을 만들어 통합 Base를 관리하는 것이 좋습니다.
try:
    from .models.trading_log_models import Base as TradingLogBase
    # 여기에 다른 모델 Base도 임포트하여 합칠 수 있습니다. e.g., from .models.user_models import Base as UserBase
    # Strategy 모델 Base 추가
    from .models.strategy_models import Base as StrategyBase 
except ImportError as e:
    print(f"경고: 모델 임포트 실패 - {e}. DB 초기화가 불완전할 수 있습니다.")
    TradingLogBase = None # type: ignore
    StrategyBase = None # type: ignore

# 데이터베이스 초기화 함수
def init_db():
    """데이터베이스 테이블 생성"""
    if TradingLogBase:
        TradingLogBase.metadata.create_all(bind=engine)
        print(f"매매일지 관련 테이블이 '{DATABASE_PATH}'에 생성되었거나 이미 존재합니다.")
    # Strategy 테이블 생성 추가
    if StrategyBase:
        StrategyBase.metadata.create_all(bind=engine)
        print(f"전략 테이블이 '{DATABASE_PATH}'에 생성되었거나 이미 존재합니다.")
    # 다른 모델 Base에 대해서도 create_all 호출
    # 예: UserBase.metadata.create_all(bind=engine)

# 데이터베이스 세션 제공 컨텍스트 매니저
@contextmanager
def get_db() -> Generator[Session, None, None]:
    """DB 세션을 안전하게 사용하고 닫는 컨텍스트 매니저"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 매매일지 관련 CRUD 함수 ---

from .models.trading_log_models import TradingLog, TradingLogDetail, StrategyLearning # 모델 임포트
# Strategy 모델 임포트 추가
from .models.strategy_models import Strategy

def add_trading_log(log_data: Dict[str, Any]) -> Optional[TradingLog]:
    """새 매매일지 마스터 레코드 추가"""
    try:
        with get_db() as db:
            # TradingLog 객체 생성 시 details, learnings 제외
            log = TradingLog(
                log_date=log_data['log_date'],
                strategy_id=log_data['strategy_id'],
                ai_model=log_data['ai_model'],
                overall_review=log_data.get('overall_review'),
                is_auto_generated=log_data.get('is_auto_generated', True)
            )
            db.add(log)
            db.commit()
            db.refresh(log) # 생성된 ID 등을 포함하여 객체 업데이트
            return log
    except Exception as e:
        print(f"매매일지 추가 중 오류 발생: {e}")
        # 필요시 로그 기록
        return None

def add_trading_log_details(log_id: int, details_data: List[Dict[str, Any]]) -> bool:
    """매매일지에 상세 내역 일괄 추가"""
    try:
        with get_db() as db:
            details = [
                TradingLogDetail(
                    log_id=log_id,
                    stock_code=d['stock_code'],
                    trade_time=d['trade_time'],
                    trade_type=d['trade_type'],
                    price=d['price'],
                    quantity=d['quantity'],
                    ai_reason=d.get('ai_reason'),
                    ai_reflection=d.get('ai_reflection'),
                    ai_improvement=d.get('ai_improvement')
                ) for d in details_data
            ]
            db.add_all(details)
            db.commit()
            return True
    except Exception as e:
        print(f"매매일지 상세 내역 추가 중 오류 발생: {e}")
        return False

def add_strategy_learning(learning_data: Dict[str, Any]) -> Optional[StrategyLearning]:
    """새 전략 학습 결과 추가"""
    try:
        with get_db() as db:
            learning = StrategyLearning(
                log_id=learning_data.get('log_id'), # 매매일지와 연관될 수도, 아닐 수도 있음
                strategy_id=learning_data['strategy_id'],
                learning_content=learning_data['learning_content']
            )
            db.add(learning)
            db.commit()
            db.refresh(learning)
            return learning
    except Exception as e:
        print(f"전략 학습 결과 추가 중 오류 발생: {e}")
        return None

def check_log_exists(log_date: date, strategy_id: int) -> bool:
    """특정 날짜와 전략 ID에 해당하는 자동 생성된 매매일지가 있는지 확인"""
    try:
        with get_db() as db:
            # 날짜 비교 시 시간 부분 제거 필요 (date 객체 사용)
            start_of_day = datetime.combine(log_date, datetime.min.time())
            end_of_day = datetime.combine(log_date, datetime.max.time())
            
            log = db.query(TradingLog).filter(
                TradingLog.log_date >= start_of_day,
                TradingLog.log_date <= end_of_day,
                TradingLog.strategy_id == strategy_id,
                TradingLog.is_auto_generated == True
            ).first()
            return log is not None
    except Exception as e:
        print(f"매매일지 존재 확인 중 오류 발생: {e}")
        return False # 오류 시 존재하지 않는 것으로 간주 (안전 측면)

def get_trading_logs(log_date: Optional[date] = None, strategy_id: Optional[int] = None) -> List[TradingLog]:
    """조건에 맞는 매매일지 목록 조회 (상세내역, 학습결과 포함)"""
    try:
        with get_db() as db:
            query = db.query(TradingLog)
            # 앞서 정의한 relationship 대신 직접 join 사용
            
            if log_date:
                start_of_day = datetime.combine(log_date, datetime.min.time())
                end_of_day = datetime.combine(log_date, datetime.max.time())
                query = query.filter(TradingLog.log_date >= start_of_day, TradingLog.log_date <= end_of_day)
            
            if strategy_id is not None:
                query = query.filter(TradingLog.strategy_id == strategy_id)
                
            logs = query.order_by(TradingLog.log_date.desc()).all()
            
            # details와 learnings 직접 로드
            for log in logs:
                _ = log.details  # 관계 로드
                _ = log.learnings  # 관계 로드
                
            return logs
    except Exception as e:
        print(f"매매일지 조회 중 오류 발생: {e}")
        return []

def get_trading_log(log_id: int) -> Optional[TradingLog]:
    """특정 ID로 매매일지 조회 (상세내역, 학습결과 포함)"""
    try:
        with get_db() as db:
            log = db.query(TradingLog).filter(TradingLog.id == log_id).first()
            if log:
                # details와 learnings 관계 로드
                _ = log.details
                _ = log.learnings
            return log
    except Exception as e:
        print(f"ID로 매매일지 조회 중 오류 발생: {e}")
        return None

# --- 전략 관련 CRUD 함수 ---

def add_strategy(strategy_data: Dict[str, Any]) -> Optional[Strategy]:
    """새 전략 추가"""
    try:
        with get_db() as db:
            # 이름 중복 체크
            existing_strategy = db.query(Strategy).filter(Strategy.name == strategy_data['name']).first()
            if existing_strategy:
                print(f"오류: 전략 이름 '{strategy_data['name']}'이(가) 이미 존재합니다.")
                return None
                
            strategy = Strategy(
                name=strategy_data['name'],
                description=strategy_data.get('description')
            )
            db.add(strategy)
            db.commit()
            db.refresh(strategy)
            return strategy
    except Exception as e:
        print(f"전략 추가 중 오류 발생: {e}")
        return None

def get_strategies() -> List[Strategy]:
    """모든 전략 목록 조회"""
    try:
        with get_db() as db:
            return db.query(Strategy).order_by(Strategy.name).all()
    except Exception as e:
        print(f"전략 목록 조회 중 오류 발생: {e}")
        return []
        
def get_strategy_by_id(strategy_id: int) -> Optional[Strategy]:
    """ID로 전략 조회"""
    try:
        with get_db() as db:
            return db.query(Strategy).filter(Strategy.id == strategy_id).first()
    except Exception as e:
        print(f"ID로 전략 조회 중 오류 발생: {e}")
        return None

# --- 기타 필요한 CRUD 함수 추가 예정 ---

# 스크립트 직접 실행 시 DB 초기화 (테스트용)
if __name__ == "__main__":
    print("데이터베이스 초기화를 시도합니다...")
    init_db()
    print("DB 초기화 완료 (또는 이미 존재).")

    # 간단한 테스트 코드 (선택 사항)
    # 전략 테스트 데이터 추가 (최초 실행 시)
    if not get_strategies():
        print("테스트 전략 데이터 추가 시도...")
        add_strategy({'name': '테스트 전략 1', 'description': '기본 테스트용 전략'})
        add_strategy({'name': '돌파매매 전략', 'description': '저항선 돌파 시 매수'})
        print("테스트 전략 데이터 추가 완료.")
    else:
        print("테스트 전략 데이터가 이미 존재합니다.")
        
    # test_date = date(2024, 1, 1)
    # if not check_log_exists(test_date, 1):
    #     print("테스트 데이터 추가 시도...")
    #     log = add_trading_log({
    #         'log_date': datetime.combine(test_date, datetime.min.time()),
    #         'strategy_id': 1,
    #         'ai_model': 'gpt-4o',
    #         'overall_review': '테스트 복기 내용입니다.'
    #     })
    #     if log:
    #         add_trading_log_details(log.id, [
    #             {'stock_code': '005930', 'trade_time': datetime(2024, 1, 1, 10, 0, 0), 'trade_type': 'buy', 'price': 70000, 'quantity': 10, 'ai_reason': '테스트 매수 이유'},
    #             {'stock_code': '005930', 'trade_time': datetime(2024, 1, 1, 14, 0, 0), 'trade_type': 'sell', 'price': 71000, 'quantity': 10, 'ai_reflection': '테스트 매도 반성'}
    #         ])
    #         add_strategy_learning({'strategy_id': 1, 'learning_content': '테스트 학습 결과입니다.', 'log_id': log.id})
    #         print("테스트 데이터 추가 완료.")
    # else:
    #     print("테스트 데이터가 이미 존재합니다.")
        
    # print("조회 테스트:")
    # logs = get_trading_logs(log_date=test_date)
    # for log_item in logs:
    #     print(f"Log ID: {log_item.id}, Date: {log_item.log_date}, Review: {log_item.overall_review}")
    #     for detail in log_item.details:
    #         print(f"  Detail: {detail.stock_code} {detail.trade_type} at {detail.price}")
    #     for learning in log_item.learnings:
    #         print(f"  Learning: {learning.learning_content}") 