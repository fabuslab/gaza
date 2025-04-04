"""
전략 기본 모듈
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime

class Strategy(ABC):
    """투자 전략 기본 클래스"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
    @abstractmethod
    def analyze(self, data: Dict) -> Dict:
        """전략 분석 실행
        
        Args:
            data: 분석 데이터
            
        Returns:
            분석 결과
        """
        pass
        
    @abstractmethod
    def validate(self) -> bool:
        """전략 유효성 검사"""
        pass
        
    @abstractmethod
    def to_dict(self) -> Dict:
        """전략을 딕셔너리로 변환"""
        pass
        
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict) -> 'Strategy':
        """딕셔너리에서 전략 생성"""
        pass
        
class AIStrategy(Strategy):
    """AI 기반 투자 전략 클래스"""
    
    def __init__(
        self,
        name: str,
        description: str,
        rules: List[str],
        params: Dict,
        model_type: str = "gpt-4"
    ):
        super().__init__(name, description)
        self.rules = rules
        self.params = params
        self.model_type = model_type
        
    def analyze(self, data: Dict) -> Dict:
        """전략 분석 실행"""
        # TODO: OpenAI API를 사용한 분석 구현
        return {
            "result": "분석 결과",
            "confidence": 0.0,
            "recommendations": []
        }
        
    def validate(self) -> bool:
        """전략 유효성 검사"""
        return (
            bool(self.name) and
            bool(self.description) and
            self.rules is not None and
            isinstance(self.params, dict)
        )
        
    def to_dict(self) -> Dict:
        """전략을 딕셔너리로 변환"""
        return {
            "name": self.name,
            "description": self.description,
            "rules": self.rules,
            "params": self.params,
            "model_type": self.model_type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'AIStrategy':
        """딕셔너리에서 전략 생성"""
        strategy = cls(
            name=data["name"],
            description=data["description"],
            rules=data["rules"],
            params=data["params"],
            model_type=data.get("model_type", "gpt-4")
        )
        strategy.created_at = datetime.fromisoformat(data["created_at"])
        strategy.updated_at = datetime.fromisoformat(data["updated_at"])
        return strategy 