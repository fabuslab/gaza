"""
매매 전략 실행 모듈
"""

import logging
import time
import re # 정규표현식 사용 위해 추가
from typing import Any
from PySide6.QtCore import QThread, QTimer, Signal, Slot
from PySide6.QtCore import QSettings
from core.utils.crypto import decrypt_data
from datetime import datetime

from core.strategy.base import AIStrategy
from core.api.openai import OpenAIAPI # AI 모델 호출을 위해 임포트 (가정)
from core.api.kiwoom import KiwoomAPI # 추가 또는 확인

logger = logging.getLogger(__name__)

# KiwoomAPI 매매구분 코드 (전체 목록 업데이트)
ORDER_TYPE_MAP = {
    "00": "지정가",
    "03": "시장가",
    "05": "조건부지정가",
    "06": "최유리지정가",
    "07": "최우선지정가",
    "10": "지정가IOC",
    "13": "시장가IOC",
    "16": "최유리IOC",
    "20": "지정가FOK",
    "23": "시장가FOK",
    "26": "최유리FOK",
    "61": "장전시간외", # 시간외종가
    "62": "시간외단일가",
    "81": "장후시간외", # 시간외종가
    # 스톱 관련은 별도 API 가능성 있음 (문서 확인 필요)
    "28": "스톱지정가",
    "29": "중간가",
    "30": "중간가IOC",
    "31": "중간가FOK",
}

# 가격이 필요한 주문 유형 코드 집합
PRICE_REQUIRED_TYPES = {"00", "05", "06", "07", "10", "16", "20", "26", "28", "29", "30", "31"}
# 가격이 0이어야 하는 (또는 무시되는) 주문 유형 코드 집합 (시장가 계열)
PRICE_ZERO_TYPES = {"03", "13", "23"}

class StrategyExecutor(QThread):
    """
    선택된 AI 전략을 주기적으로 실행하는 클래스.
    QThread를 상속받아 백그라운드에서 동작합니다.
    """
    # 시그널 정의 (예: 상태 업데이트, 로그 메시지 등)
    log_message = Signal(str)
    error_occurred = Signal(str)
    status_changed = Signal(bool) # True: 실행 중, False: 중지됨
    trade_decision = Signal(str, datetime)
    order_result = Signal(dict) # 주문 결과 상세 정보 전달 (예: 성공여부, 시간, 타입, 가격, 수량, 메시지)

    def __init__(self, strategy: AIStrategy, stock_code: str, kiwoom_api: KiwoomAPI, parent=None):
        super().__init__(parent)
        self.strategy = strategy
        self.stock_code = stock_code
        self.kiwoom_api = kiwoom_api # KiwoomAPI 인스턴스 저장
        self._is_running = False
        self.timer = None
        self.openai_api = None
        
        # QSettings에서 OpenAI API 키 로드 및 복호화
        try:
            settings = QSettings("GazuaTrading", "Trading")
            openai_key_encrypted = settings.value("api/openai_key")
            if not openai_key_encrypted:
                raise ValueError("QSettings에 OpenAI API 키가 저장되어 있지 않습니다.")
            openai_api_key = decrypt_data(openai_key_encrypted)
            if not openai_api_key:
                 raise ValueError("OpenAI API 키 복호화에 실패했습니다.")
            self.openai_api = OpenAIAPI(api_key=openai_api_key)
            logger.info("OpenAI API 클라이언트 초기화 성공")
        except Exception as e:
             logger.error(f"OpenAI API 클라이언트 초기화 실패: {e}", exc_info=True)
             self.error_occurred.emit(f"OpenAI API 클라이언트 초기화 실패: {e}")
             self.openai_api = None

        # 호출 주기 파싱
        try:
            interval_str = self.strategy.params.get('ai_interval', '60초') # 기본값 60초
            # 숫자와 '초' 분리 (공백 제거 후)
            parts = interval_str.replace(' ', '').split('초')
            if len(parts) == 2 and parts[0].isdigit():
                value = int(parts[0])
                self.interval_ms = value * 1000
                if self.interval_ms <= 0:
                    raise ValueError("호출 주기는 0보다 커야 합니다.")
                logger.info(f"전략 '{self.strategy.name}' 실행 주기: {self.interval_ms}ms")
            else:
                raise ValueError(f"잘못된 주기 형식: {interval_str}")
        except Exception as e:
            logger.error(f"잘못된 호출 주기 형식 처리 실패: {interval_str} - 기본값 60초 사용. 오류: {e}")
            self.interval_ms = 60 * 1000

    def run(self):
        """스레드 실행 진입점"""
        # API 초기화 실패 시 스레드 실행 중단
        if not self.openai_api:
            logger.error("OpenAI API가 초기화되지 않아 StrategyExecutor 스레드를 시작할 수 없습니다.")
            # self.error_occurred 시그널은 __init__에서 이미 발생
            return # 스레드 실행 중단
            
        logger.info(f"StrategyExecutor 스레드 시작: {self.strategy.name} ({self.stock_code})")
        self._is_running = True
        self.status_changed.emit(True)

        # 스레드 내에서 타이머 생성 및 시작
        self.timer = QTimer()
        self.timer.timeout.connect(self._execute_trade_logic)
        self.timer.start(self.interval_ms)

        # QThread의 이벤트 루프 시작 (타이머 시그널 처리를 위해 필요)
        self.exec()

        # 스레드 종료 시 정리
        if self.timer:
            self.timer.stop()
        logger.info(f"StrategyExecutor 스레드 종료: {self.strategy.name} ({self.stock_code})")
        self._is_running = False
        self.status_changed.emit(False)


    def stop(self):
        """스레드 실행 중지 요청"""
        if self._is_running:
            logger.info(f"StrategyExecutor 스레드 중지 요청: {self.strategy.name} ({self.stock_code})")
            self.quit() # 스레드의 이벤트 루프 종료
            self.wait() # 스레드가 완전히 종료될 때까지 대기

    @Slot()
    def _execute_trade_logic(self):
        if not self._is_running or not self.openai_api:
            return

        current_time = datetime.now()
        self.log_message.emit(f"[{self.strategy.name}/{self.stock_code}] 매매 로직 실행...")

        try:
            market_data = f"현재 {self.stock_code} 시장 데이터 (구현 필요)" # 임시 데이터
            prompt = self._create_ai_prompt(market_data)
            ai_model_name = self.strategy.params.get('ai_model', 'gpt-3.5-turbo')
            
            # --- AI 결정 요청 및 파싱 --- 
            # TODO: get_trading_decision이 충분히 긴 응답(이유 포함)을 생성하도록 max_tokens 조정 필요
            decision_raw = self.openai_api.get_trading_decision(prompt, model=ai_model_name)
            self.log_message.emit(f"AI Raw 결정 ({ai_model_name}): {decision_raw}")
            decision_details = self._parse_ai_decision(decision_raw) # 상세 결정 파싱
            
            # 파싱 실패 시 처리
            if decision_details.get('action') == 'error':
                self.log_message.emit(f"AI 결정 파싱 실패: {decision_details.get('message')}")
                self.error_occurred.emit(f"AI 결정 파싱 실패: {decision_details.get('message')}")
                # 오류 발생 시에도 order_result 전달 (실패 상태)
                error_info = { 
                    'timestamp': current_time.isoformat(), 'decision': 'error', 'success': False, 
                    'message': f"AI 결정 파싱 실패: {decision_details.get('message')}",
                    'stock_code': self.stock_code, 'strategy_name': self.strategy.name,
                    'ai_reason': decision_details.get('reason', '파싱 오류로 이유 확인 불가')
                }
                self.order_result.emit(error_info)
                return # 로직 중단
            
            ai_reason = decision_details.get('reason', "")
            decision_details['reason'] = ai_reason # 상세 결과에 이유 추가
            self.trade_decision.emit(decision_details.get('action', 'error'), current_time)
            
            parent_window = self.parent()
            is_real_trading = False
            if parent_window and hasattr(parent_window, 'real_trade_radio') and parent_window.real_trade_radio.isChecked():
                is_real_trading = True
            # else: # 모의투자 모드는 로그만 남김 (이전과 동일)
            #     self.log_message.emit("투자 모드 확인 실패 또는 모의 투자 모드")

            # order_info 딕셔너리 업데이트
            order_info = { # 기본값 설정
                'timestamp': current_time.isoformat(),
                'stock_code': self.stock_code,
                'strategy_name': self.strategy.name,
                'decision': decision_details.get('action', 'error'),
                'order_type': decision_details.get('order_type_code', None),
                'order_qty': decision_details.get('qty', 0),
                'order_price': decision_details.get('price', 0),
                'trade_tp': decision_details.get('order_type_code', None),
                'ord_no': None,
                'success': None,
                'message': '-',
                'is_real_trade': is_real_trading,
                'ai_reason': ai_reason # AI 분석 이유 추가
            }

            action = decision_details.get('action')
            if is_real_trading and action in ['buy', 'sell']:
                if not self.kiwoom_api:
                    err_msg = "오류: KiwoomAPI가 초기화되지 않았습니다."
                    # ... (오류 처리 및 시그널 발생)
                    return
                
                # --- 주문 파라미터 설정 및 유효성 검사 --- 
                order_qty = decision_details.get('qty', 0)
                order_price = decision_details.get('price', 0)
                trade_type = decision_details.get('order_type_code')
                api_id = None
                order_type_code = None # 1: 매수, 2: 매도
                rq_name = None
                error_msg = None # 유효성 검사 오류 메시지

                # 1. 수량 검사
                if not isinstance(order_qty, int) or order_qty <= 0:
                    error_msg = f"오류: 주문 수량({order_qty})이 유효하지 않습니다."
                # 2. 주문 유형 코드 검사
                elif trade_type not in ORDER_TYPE_MAP:
                     error_msg = f"오류: 지원하지 않는 주문 유형 코드({trade_type})입니다."
                # 3. 가격 검사 (유형에 따라)
                elif trade_type in PRICE_REQUIRED_TYPES and (not isinstance(order_price, (int, float)) or order_price <= 0):
                     error_msg = f"오류: {ORDER_TYPE_MAP[trade_type]}({trade_type}) 주문 가격({order_price})이 유효하지 않습니다."
                elif trade_type in PRICE_ZERO_TYPES:
                     order_price = 0 # 시장가 등 가격 0으로 설정
                
                # 유효성 검사 실패 시 처리
                if error_msg:
                    logger.error(error_msg)
                    self.log_message.emit(error_msg)
                    self.error_occurred.emit(error_msg)
                    order_info['success'] = False
                    order_info['message'] = error_msg
                    self.order_result.emit(order_info)
                    return

                # 유효성 검사 통과 -> API ID 및 rqname 설정
                if action == 'buy':
                    api_id = 'kt10000'
                    order_type_code = 1
                    rq_name = f"StrategyBuy_{self.stock_code}_{trade_type}"
                    # TODO: 매수 가능 금액 확인 로직
                elif action == 'sell':
                    api_id = 'kt10001'
                    order_type_code = 2
                    rq_name = f"StrategySell_{self.stock_code}_{trade_type}"
                    # TODO: 실제 매도 가능 수량 확인 및 order_qty 조정 로직

                # order_info 업데이트 (주문 직전)
                order_info['order_type'] = order_type_code
                order_info['order_qty'] = order_qty
                order_info['order_price'] = order_price
                order_info['trade_tp'] = trade_type
                order_info['message'] = f"{action.upper()} ({ORDER_TYPE_MAP.get(trade_type, trade_type)}/{order_price}/{order_qty}) 주문 시도 중..."
                self.order_result.emit(order_info) # 주문 시도 상태 전달

                if api_id and order_type_code:
                    try:
                        # TODO: KiwoomAPI.send_order의 실제 파라미터 확인 및 조정 (accno 제거 확인)
                        response = self.kiwoom_api.send_order(
                            api_id=api_id, 
                            rqname=rq_name,
                            screen="0101", 
                            # accno=account_number, # 계좌번호 제거
                            order_type=order_type_code, 
                            code=self.stock_code,
                            qty=order_qty,
                            price=order_price,
                            trde_tp=trade_type, # 매매 구분 코드로 전달
                            orderno=""
                        )
                        log_msg = f"{action.upper()} 주문 결과: {response}"
                        logger.info(log_msg)
                        self.log_message.emit(log_msg)

                        # API 응답 파싱 (성공/실패, 주문번호 등)
                        if isinstance(response, dict):
                            order_info['success'] = (response.get('return_code') == 0)
                            order_info['message'] = response.get('return_msg', '응답 메시지 없음')
                            order_info['ord_no'] = response.get('ord_no') # 주문번호 저장
                        else:
                            order_info['success'] = False
                            order_info['message'] = f"예상치 못한 주문 응답 타입: {type(response)}"
                        
                    except Exception as order_e:
                        err_msg = f"{action.upper()} 주문 API 호출 오류: {order_e}"
                        logger.error(err_msg, exc_info=True)
                        self.log_message.emit(err_msg)
                        self.error_occurred.emit(err_msg)
                        order_info['success'] = False
                        order_info['message'] = err_msg
                    
                    # 최종 주문 결과 시그널 발생 (ai_reason 포함됨)
                    self.order_result.emit(order_info)
            
            elif action == 'hold':
                 order_info['message'] = "[홀드]"
                 order_info['success'] = None # 실행 안 함 상태
                 self.order_result.emit(order_info)
            else: # 모의 투자 모드 또는 알 수 없는 action
                 order_info['message'] = f"실제 주문 미실행 (모드: {'모의' if not is_real_trading else '실전'}, 결정: {action})"
                 order_info['success'] = None
                 self.order_result.emit(order_info)

        except Exception as e:
            error_msg = f"매매 로직 실행 중 오류: {e}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            # 오류 발생 시에도 정보 전달
            error_info = { 
                'timestamp': current_time.isoformat(), 
                'decision': 'error', 
                'success': False, 
                'message': f"로직 오류: {e}",
                'stock_code': self.stock_code,
                'strategy_name': self.strategy.name,
                'ai_reason': f"오류로 인해 분석 불가: {e}" # 오류 시 이유
            }
            self.order_result.emit(error_info)

    def _create_ai_prompt(self, market_data: str) -> str:
        """AI 모델에 전달할 프롬프트를 생성합니다."""
        # 전략 설명, 규칙, 현재 데이터 등을 조합하여 프롬프트 생성
        prompt = f"투자 전략: {self.strategy.name}\n"
        prompt += f"설명: {self.strategy.description}\n"
        if self.strategy.rules:
            prompt += "규칙:\n" + "\n".join([f"- {rule}" for rule in self.strategy.rules]) + "\n"
        prompt += f"현재 시장 데이터 ({self.stock_code}):\n{market_data}\n\n"
        prompt += "분석 결과 및 다음 행동(buy, sell, hold)을 결정하세요."
        # TODO: 첨부 파일 내용(이미지/PDF)을 프롬프트에 포함시키는 로직 추가 필요 (OpenAI Vision API 등 활용)
        return prompt

    # AI 상세 결정 파싱 메소드 (이유 파싱 TODO 추가)
    def _parse_ai_decision(self, decision_raw: Any) -> dict:
        # TODO: AI 응답에서 action, trade_type_code, price, qty, reason 추출 구현
        if isinstance(decision_raw, str) and decision_raw.lower() in ['buy', 'sell', 'hold']:
            return {'action': decision_raw.lower(), 'order_type_code': '03', 'price': 0, 'qty': 1, 'reason': 'AI 이유 파싱 필요 (임시)'}
        else:
            logger.warning(f"AI 결정 파싱 실패 또는 알 수 없는 형식: {decision_raw}. 홀드로 처리.")
            return {'action': 'hold', 'message': f'Invalid AI decision format: {decision_raw}', 'reason': '파싱 불가'}

    # --- Placeholder methods for actual implementation ---
    # def _get_current_chart_data(self):
    #     # ChartModule 또는 다른 데이터 소스에서 최신 데이터 가져오기
    #     pass
    #
    # def _place_buy_order(self):
    #     # KiwoomAPI 등을 사용하여 매수 주문 실행
    #     pass
    #
    # def _place_sell_order(self):
    #     # KiwoomAPI 등을 사용하여 매도 주문 실행
    #     pass 