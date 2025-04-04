"""
OpenAI API 연동 모듈
"""

import logging
from typing import Dict, List, Optional, Any
from openai import OpenAI
from .base import BaseAPI, APIError
import json
from core.database.models.strategy_models import Strategy

logger = logging.getLogger(__name__)

class OpenAIAPI(BaseAPI):
    """OpenAI API 클래스"""
    
    def __init__(self, api_key: str):
        """
        Args:
            api_key: OpenAI API 키
        """
        super().__init__("https://api.openai.com/v1/", api_key)
        self.client = OpenAI(api_key=api_key)
        
    def analyze_stock(self, stock_code: str, stock_data: Dict) -> Dict:
        """주식 분석
        
        Args:
            stock_code: 종목코드
            stock_data: 종목 데이터
            
        Returns:
            분석 결과
        """
        try:
            # 프롬프트 생성
            prompt = self._create_analysis_prompt(stock_code, stock_data)
            
            # API 호출
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 전문 주식 분석가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # 응답 파싱
            return self._parse_analysis_response(response)
            
        except Exception as e:
            logger.error(f"주식 분석 실패: {e}")
            raise APIError(f"주식 분석 실패: {e}")
            
    def generate_strategy(self, stock_code: str, params: Dict) -> Dict:
        """투자 전략 생성
        
        Args:
            stock_code: 종목코드
            params: 전략 생성 파라미터
            
        Returns:
            생성된 전략
        """
        try:
            # 프롬프트 생성
            prompt = self._create_strategy_prompt(stock_code, params)
            
            # API 호출
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 전문 투자 전략가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            # 응답 파싱
            return self._parse_strategy_response(response)
            
        except Exception as e:
            logger.error(f"전략 생성 실패: {e}")
            raise APIError(f"전략 생성 실패: {e}")
            
    def analyze_strategy_with_vision(self, prompt: str, image_data: List = None) -> str:
        """이미지가 포함된 투자 전략 분석
        
        Args:
            prompt: 분석 요청 텍스트
            image_data: 이미지 데이터 리스트 (base64 인코딩)
            
        Returns:
            분석 결과 텍스트
        """
        try:
            if not image_data:
                image_data = []

            # 메시지 구성
            messages = [
                {"role": "system", "content": "당신은 전문 투자 전략가입니다. 사용자가 제공하는 투자 전략과 차트 이미지를 분석하여 구체적인 개선 방안을 제시하세요."},
                {"role": "user", "content": [{"type": "text", "text": prompt}] + image_data}
            ]
            
            # API 호출
            response = self.client.chat.completions.create(
                model="gpt-4o",  # GPT-4o 모델 사용
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            # 응답에서 텍스트 추출
            result = response.choices[0].message.content
            logger.info(f"전략 분석 완료: {len(result)} 글자")
            return result
            
        except Exception as e:
            logger.error(f"전략 분석 실패: {e}")
            raise APIError(f"전략 분석 실패: {e}")
            
    def get_trading_decision(self, prompt: str, model: str = "gpt-4o") -> str:
        """주어진 프롬프트를 기반으로 매매 결정을 반환합니다. (buy/sell/hold)"""
        logger.info(f"OpenAI API 호출 시작 (모델: {model})... 매매 결정 요청")
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "당신은 주어진 시장 데이터와 투자 전략을 분석하여 다음 행동(buy, sell, hold 중 하나)을 결정하는 AI입니다. 답변은 반드시 'buy', 'sell', 'hold' 중 하나여야 합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2, # 결정의 일관성을 위해 낮은 온도로 설정
                max_tokens=10 # 답변 길이를 짧게 제한
            )
            
            decision = response.choices[0].message.content.strip().lower()
            logger.info(f"OpenAI API 응답 수신 완료: {decision}")
            
            # 응답이 buy/sell/hold 중 하나인지 확인, 아니면 hold 반환
            if decision in ["buy", "sell", "hold"]:
                return decision
            else:
                logger.warning(f"예상치 못한 AI 결정 응답: '{decision}'. 기본값 'hold' 사용.")
                return "hold"
            
        except Exception as e:
            logger.error(f"매매 결정 요청 실패: {e}", exc_info=True)
            # 오류 발생 시 기본적으로 'hold' 반환
            return "hold"
            
    def analyze_daily_trades(self, trade_data: List[Dict[str, Any]], strategy_info: Strategy) -> Dict[str, Any]:
        """특정 전략의 일일 매매 내역을 분석하고 복기 결과를 생성합니다.
        
        Args:
            trade_data: 해당 날짜의 매매 내역 리스트 (각 딕셔너리는 stock_code, trade_time, trade_type, price, quantity 포함)
            strategy_info: 분석 대상 전략 정보 (Strategy 모델 객체)
            
        Returns:
            구조화된 분석 결과 딕셔너리:
            {
                "overall_review": "전반적인 복기 내용",
                "details": [
                    {"stock_code": ..., "trade_time": ..., "ai_reason": ..., "ai_reflection": ..., "ai_improvement": ...},
                    ...
                ],
                "learning": "전략 개선을 위한 학습 내용/인사이트"
            }
        """
        if not trade_data:
            logger.info("분석할 매매 내역이 없습니다.")
            return {"overall_review": "매매 내역이 없습니다.", "details": [], "learning": ""}
            
        try:
            # 1. 프롬프트 생성
            prompt = self._create_trade_analysis_prompt(trade_data, strategy_info)
            
            # 2. API 호출
            logger.info(f"OpenAI API 호출 시작 (모델: gpt-4o)... 전략 ID: {strategy_info.id}")
            response = self.client.chat.completions.create(
                model="gpt-4o", # 최신 모델 사용
                # response_format={"type": "json_object"}, # JSON 출력 강제 (gpt-4-turbo 이상 지원)
                messages=[
                    {"role": "system", "content": self._get_system_prompt_for_trade_analysis()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5, # 약간 더 일관된 결과 선호
                max_tokens=3000 # 충분한 토큰 할당 (매매 내역 길이에 따라 조절 필요)
            )
            raw_response_content = response.choices[0].message.content
            logger.info(f"OpenAI API 응답 수신 완료 (글자 수: {len(raw_response_content or '')})")
            
            # 3. 응답 파싱
            # 주의: JSON 포맷을 강제했더라도 파싱 오류 발생 가능
            return self._parse_trade_analysis_response(raw_response_content, trade_data)
            
        except Exception as e:
            logger.exception(f"일일 매매 분석 중 OpenAI API 오류 발생: {e}")
            raise APIError(f"일일 매매 분석 실패: {e}")

    def _get_system_prompt_for_trade_analysis(self) -> str:
        """매매 분석용 시스템 프롬프트 반환"""
        return """
You are a professional algorithmic trading analyst and strategist reviewing daily trades. Your task is to:
1. Analyze the provided trading strategy description and the list of trades executed today.
2. Provide an overall review of the day's trading performance based on the strategy.
3. For EACH trade, provide:
    - A plausible reason why the trade might have been executed based on the strategy and general market context (ai_reason).
    - A critical reflection on the trade (e.g., good entry/exit, missed opportunity, potential issues) (ai_reflection).
    - A concrete suggestion for improvement related to that trade or pattern (ai_improvement).
4. Derive a single, actionable learning or insight from the day's trades that can be used to improve the strategy itself (learning).

Output ONLY a valid JSON object with the following exact structure (do not add any explanation before or after the JSON):
{
  "overall_review": "<string: Your overall assessment of the day's trading performance.>",
  "details": [
    {
      "stock_code": "<string: Stock code>",
      "trade_time": "<string: ISO 8601 format timestamp>",
      "ai_reason": "<string: Plausible reason for the trade.>",
      "ai_reflection": "<string: Critical reflection.>",
      "ai_improvement": "<string: Suggestion for improvement.>"
    },
    ...
  ],
  "learning": "<string: Actionable insight for strategy improvement.>"
}

Ensure the 'details' array contains an entry for every trade provided in the input, matching the stock_code and trade_time.
"""

    def _create_trade_analysis_prompt(self, trade_data: List[Dict[str, Any]], strategy_info: Strategy) -> str:
        """매매 분석용 사용자 프롬프트 생성"""
        # 전략 정보 문자열화
        strategy_desc = f"Strategy Name: {strategy_info.name}\nStrategy Description: {strategy_info.description or 'Not provided'}\n"
        
        # 매매 내역 문자열화 (가독성 및 토큰 효율 고려)
        trades_str = "\n".join([
            f"- Stock: {t['stock_code']}, Time: {t['trade_time'].isoformat()}, Type: {t['trade_type']}, Price: {t['price']}, Qty: {t['quantity']}"
            for t in trade_data
        ])
        
        return f"""Analyze the following trades based on the provided strategy information.

Strategy Information:
{strategy_desc}
Today's Trades:
{trades_str}

Please provide the analysis in the JSON format specified in the system prompt.
"""

    def _parse_trade_analysis_response(self, raw_response: Optional[str], original_trade_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """AI 응답(JSON 문자열 예상)을 파싱하여 구조화된 딕셔너리로 변환"""
        default_result = {"overall_review": "AI 분석 실패 또는 응답 없음", "details": [], "learning": ""}
        
        if not raw_response:
            logger.error("AI 응답이 비어 있습니다.")
            return default_result

        try:
            # JSON 파싱 시도
            # 가끔 JSON 앞뒤로 불필요한 텍스트가 붙는 경우가 있어 ```json ... ``` 부분만 추출 시도
            json_match = re.search(r"```json\n(.*?)\n```", raw_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
                logger.debug("JSON 블록 추출 성공")
            else:
                json_str = raw_response.strip()
                logger.debug("JSON 블록을 찾지 못해 전체 응답을 사용")
                # 만약 { } 로 감싸여있지 않다면 추가 시도 (덜 일반적)
                if not json_str.startswith('{') or not json_str.endswith('}'):
                     start_index = json_str.find('{')
                     end_index = json_str.rfind('}')
                     if start_index != -1 and end_index != -1:
                         json_str = json_str[start_index:end_index+1]
            
            parsed_data = json.loads(json_str)
            logger.info("AI 응답 JSON 파싱 성공")

            # 필수 키 존재 여부 검증 (선택 사항이지만 권장)
            if not all(k in parsed_data for k in ["overall_review", "details", "learning"]):
                logger.error(f"AI 응답 JSON에 필수 키가 누락되었습니다: {parsed_data.keys()}")
                raise ValueError("Missing required keys in AI response JSON")
            if not isinstance(parsed_data["details"], list):
                 logger.error(f"AI 응답 JSON의 'details'가 리스트가 아닙니다: {type(parsed_data['details'])}")
                 raise ValueError("'details' key must contain a list")

            # 파싱된 데이터 반환
            # 세부 내역의 stock_code, trade_time이 원본 데이터와 일치하는지 검증 추가 가능
            return parsed_data

        except json.JSONDecodeError as e:
            logger.error(f"AI 응답 JSON 파싱 실패: {e}\nRaw Response:\n{raw_response}")
            # 파싱 실패 시 기본값 반환
            default_result["overall_review"] = f"AI 응답 파싱 실패: {e}"
            return default_result
        except ValueError as e:
             logger.error(f"AI 응답 JSON 구조 오류: {e}\nRaw Response:\n{raw_response}")
             default_result["overall_review"] = f"AI 응답 구조 오류: {e}"
             return default_result
        except Exception as e:
            logger.exception(f"AI 응답 처리 중 예상치 못한 오류 발생: {e}\nRaw Response:\n{raw_response}")
            default_result["overall_review"] = f"AI 응답 처리 중 오류 발생: {e}"
            return default_result

    def _create_analysis_prompt(self, stock_code: str, stock_data: Dict) -> str:
        """분석 프롬프트 생성"""
        return f"""
다음 주식에 대한 기술적/기본적 분석을 제공해주세요:

종목코드: {stock_code}
종목 데이터:
{stock_data}

다음 항목을 포함해주세요:
1. 기본적 분석 (재무제표, 시장 점유율 등)
2. 기술적 분석 (추세, 지지/저항선 등)
3. 시장 환경 분석
4. 투자 위험 요소
5. 종합 의견
"""

    def _create_strategy_prompt(self, stock_code: str, params: Dict) -> str:
        """전략 프롬프트 생성"""
        return f"""
다음 주식에 대한 투자 전략을 제시해주세요:

종목코드: {stock_code}
전략 파라미터:
{params}

다음 항목을 포함해주세요:
1. 투자 목표 및 기간
2. 매수/매도 조건
3. 포지션 크기
4. 손절/익절 기준
5. 리스크 관리 방안
"""

    def _parse_analysis_response(self, response: Dict) -> Dict:
        """분석 응답 파싱"""
        content = response.choices[0].message.content
        
        # TODO: 응답 파싱 로직 구현
        return {
            "content": content,
            "summary": self._extract_summary(content)
        }
        
    def _parse_strategy_response(self, response: Dict) -> Dict:
        """전략 응답 파싱"""
        content = response.choices[0].message.content
        
        # TODO: 응답 파싱 로직 구현
        return {
            "content": content,
            "rules": self._extract_rules(content)
        }
        
    def _extract_summary(self, content: str) -> str:
        """요약 추출"""
        # TODO: 요약 추출 로직 구현
        return content.split("\n\n")[0]
        
    def _extract_rules(self, content: str) -> List[str]:
        """규칙 추출"""
        # TODO: 규칙 추출 로직 구현
        return [line.strip() for line in content.split("\n") if line.strip().startswith("-")] 