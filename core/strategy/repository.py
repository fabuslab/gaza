"""
전략 저장소 모듈
"""

import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime

from .base import Strategy, AIStrategy

logger = logging.getLogger(__name__)

class StrategyRepository:
    """전략 저장소 클래스"""
    
    def __init__(self, storage_path: str = "data/strategies"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    def save(self, strategy: Strategy) -> bool:
        """전략 저장
        
        Args:
            strategy: 저장할 전략
            
        Returns:
            성공 여부
        """
        try:
            if not strategy.validate():
                logger.error("유효하지 않은 전략")
                return False
                
            strategy.updated_at = datetime.now()
            data = strategy.to_dict()
            
            file_path = self.storage_path / f"{strategy.name}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"전략 저장 완료: {strategy.name}")
            return True
            
        except Exception as e:
            logger.error(f"전략 저장 실패: {e}")
            return False
            
    def load(self, name: str) -> Optional[Strategy]:
        """전략 로드
        
        Args:
            name: 전략 이름
            
        Returns:
            로드된 전략
        """
        try:
            file_path = self.storage_path / f"{name}.json"
            if not file_path.exists():
                logger.error(f"전략 파일 없음: {name}")
                return None
                
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # TODO: 전략 타입에 따른 분기 처리
            strategy = AIStrategy.from_dict(data)
            logger.info(f"전략 로드 완료: {name}")
            return strategy
            
        except Exception as e:
            logger.error(f"전략 로드 실패: {e}")
            return None
            
    def list_strategies(self) -> List[str]:
        """전략 목록 조회"""
        try:
            return [f.stem for f in self.storage_path.glob("*.json")]
        except Exception as e:
            logger.error(f"전략 목록 조회 실패: {e}")
            return []
            
    def delete(self, name: str) -> bool:
        """전략 삭제
        
        Args:
            name: 전략 이름
            
        Returns:
            성공 여부
        """
        try:
            file_path = self.storage_path / f"{name}.json"
            if not file_path.exists():
                logger.error(f"전략 파일 없음: {name}")
                return False
                
            file_path.unlink()
            logger.info(f"전략 삭제 완료: {name}")
            return True
            
        except Exception as e:
            logger.error(f"전략 삭제 실패: {e}")
            return False 