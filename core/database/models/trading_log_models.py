from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
# Base를 프로젝트의 다른 모델과 공유해야 할 수 있습니다.
# 현재는 독립적인 Base를 가정하며, 필요시 `from .base import Base` 등으로 수정해야 합니다.
Base = declarative_base() 

class TradingLog(Base):
    """매매일지 마스터 테이블"""
    __tablename__ = 'trading_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_date = Column(DateTime, nullable=False, index=True)  # 일지 작성 대상 날짜
    strategy_id = Column(Integer, nullable=False, index=True) # 어떤 전략에 대한 일지인지 (추후 Strategy 모델과 연결)
    ai_model = Column(String, nullable=False)                # 분석에 사용된 AI 모델 (예: "gpt-4o")
    overall_review = Column(Text)                            # AI가 생성한 해당 날짜의 전반적인 복기 내용
    created_at = Column(DateTime, default=datetime.now)
    is_auto_generated = Column(Boolean, default=True)       # 자동 생성 여부 (수동 실행과 구분)

    details = relationship("TradingLogDetail", back_populates="log", cascade="all, delete-orphan")
    learnings = relationship("StrategyLearning", back_populates="log", cascade="all, delete-orphan")

    # strategy = relationship("Strategy", back_populates="trading_logs") # 필요시 Strategy 모델과 연결

class TradingLogDetail(Base):
    """매매일지 상세 내역 테이블 (개별 매매 건)"""
    __tablename__ = 'trading_log_details'

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(Integer, ForeignKey('trading_logs.id'), nullable=False, index=True)
    stock_code = Column(String, nullable=False, index=True)    # 종목 코드
    trade_time = Column(DateTime, nullable=False)            # 매매 체결 시각
    trade_type = Column(String, nullable=False)              # 매매 구분 ('buy', 'sell')
    price = Column(Float, nullable=False)                    # 체결 가격
    quantity = Column(Integer, nullable=False)                 # 체결 수량
    # 홀드 기간 표시는 UI 레벨에서 매수/매도 시점을 이용해 구현
    
    ai_reason = Column(Text)       # AI가 분석한 해당 매매의 추정 실행 사유
    ai_reflection = Column(Text)   # AI가 분석한 반성/복기 내용
    ai_improvement = Column(Text)  # AI가 제시한 개선 방향

    log = relationship("TradingLog", back_populates="details")

class StrategyLearning(Base):
    """전략 학습 결과 테이블"""
    __tablename__ = 'strategy_learnings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(Integer, ForeignKey('trading_logs.id'), nullable=True, index=True) # 어떤 매매일지 분석에서 나왔는지 (Nullable=True는 독립적인 학습도 가능하게 할 경우)
    strategy_id = Column(Integer, nullable=False, index=True) # 학습 결과가 적용될 전략 ID
    learning_content = Column(Text, nullable=False)          # AI가 도출한 구체적인 학습 내용/규칙/인사이트
    created_at = Column(DateTime, default=datetime.now)

    log = relationship("TradingLog", back_populates="learnings")
    # strategy = relationship("Strategy", back_populates="learnings") # 필요시 Strategy 모델과 연결
