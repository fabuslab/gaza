from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# 다른 모델과 공유할 Base 클래스가 필요할 수 있음
# 예: from .base import Base
# 여기서는 독립 Base 가정, 필요시 수정
Base = declarative_base()

class Strategy(Base):
    """DB에 저장될 간단한 전략 정보 (선택 목록용)"""
    __tablename__ = 'strategies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True) # 전략 이름 (고유해야 함)
    description = Column(String) # 간단한 설명 (선택 사항)
    created_at = Column(DateTime, default=datetime.now)

    # 필요시 TradingLog 등 다른 모델과의 관계 설정
    # trading_logs = relationship("TradingLog", back_populates="strategy")
    # learnings = relationship("StrategyLearning", back_populates="strategy") 