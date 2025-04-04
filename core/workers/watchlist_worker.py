import logging
from typing import List
# from PyQt5.QtCore import QThread, pyqtSignal # 이전
from PySide6.QtCore import QThread, Signal as pyqtSignal # 변경

# 순환 참조를 피하기 위해 타입 힌트만 사용 (실제 객체는 __init__에서 받음)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.api.kiwoom import KiwoomAPI
    from core.database.watchlist_db import WatchlistDatabase

logger = logging.getLogger(__name__)

class WatchlistUpdateWorker(QThread):
    """관심목록 업데이트 작업을 수행하는 워커 스레드"""
    # 작업 완료 시그널 (group_id, 결과 데이터)
    update_finished = pyqtSignal(int, list)
    # 오류 발생 시그널
    error_occurred = pyqtSignal(str)

    def __init__(self, api: 'KiwoomAPI', db: 'WatchlistDatabase', group_id: int, parent=None):
        super().__init__(parent)
        self.api = api
        self.db = db
        self.group_id = group_id
        self._is_running = True

    def run(self):
        """스레드 실행 로직"""
        logger.debug(f"워커 스레드 시작: 그룹 {self.group_id}")
        try:
            # DB에서 종목 목록 조회
            db_stocks = self.db.get_stocks(self.group_id)
            if not db_stocks:
                logger.info(f"워커: 등록된 관심종목 없음: 그룹 {self.group_id}")
                self.update_finished.emit(self.group_id, [])
                return

            result_stocks = []
            for i, stock in enumerate(db_stocks):
                # 스레드 중지 요청 확인 (API 호출 전)
                if not self._is_running:
                    logger.info(f"워커 스레드 중지됨 (API 호출 전): 그룹 {self.group_id}")
                    return

                stock_code = stock["stock_code"]
                stock_name = stock["stock_name"]
                logger.debug(f"워커 ({self.group_id}): 처리 중 {i+1}/{len(db_stocks)} - {stock_name} ({stock_code})") # 진행 로그 추가

                try:
                    # --- API 호출 및 데이터 처리 ---
                    logger.debug(f"워커 ({self.group_id}): API 호출 시작 - {stock_code}") # API 호출 전 로그
                    price_data = self.api.get_stock_price(stock_code)
                    logger.debug(f"워커 ({self.group_id}): API 호출 완료 - {stock_code}") # API 호출 후 로그

                    # 스레드 중지 요청 확인 (API 호출 후)
                    if not self._is_running:
                        logger.info(f"워커 스레드 중지됨 (API 호출 후): 그룹 {self.group_id}")
                        return

                    # API 호출 결과 확인 및 기본 정보 설정
                    result_stock = {
                        'stk_cd': stock_code,
                        'stk_nm': stock_name,
                        'cur_prc': '0', 'prc_diff': '0', 'prc_diff_sign': '0',
                        'fluc_rt': '0', 'trd_qty': '0', 'trde_prica': '0'
                    }

                    if price_data: # API 호출 성공 시 데이터 업데이트
                         result_stock.update(price_data) # get_stock_price 반환값으로 업데이트
                    else:
                         logger.warning(f"워커 ({self.group_id}): {stock_code} 가격 정보 조회 실패")

                    # 추세 정보 계산 로직은 WatchlistModule에 있으므로 여기서는 생략
                    # 필요하다면 결과 dict에 기본값 추가 또는 별도 처리 필요
                    # result_stock['trend_info'] = ...

                    result_stocks.append(result_stock)
                    # --- API 호출 및 데이터 처리 끝 ---
                except Exception as e:
                    logger.error(f"워커 ({self.group_id}): 종목 시세 조회 중 오류: {stock_code} - {e}")
                    # 오류 발생 시 기본 정보만 포함
                    result_stocks.append({
                        'stk_cd': stock_code, 'stk_nm': stock_name,
                        'cur_prc': '0', 'prc_diff': '0', 'prc_diff_sign': '0',
                        'fluc_rt': '0', 'trd_qty': '0', 'trde_prica': '0'
                    })

            # 작업 완료 시그널 발생
            if self._is_running:
                 self.update_finished.emit(self.group_id, result_stocks)
                 logger.debug(f"워커 스레드 정상 완료: 그룹 {self.group_id}, {len(result_stocks)}개 종목") # 로그 메시지 수정

        except Exception as e:
            logger.error(f"워커 스레드 실행 중 오류 발생: 그룹 {self.group_id} - {e}", exc_info=True)
            # 중지 요청이 아닌 실제 오류일 때만 시그널 발생
            if self._is_running: 
                self.error_occurred.emit(f"관심 그룹 업데이트 스레드 오류: {str(e)}")
        finally:
            logger.debug(f"워커 스레드 run 메소드 종료: 그룹 {self.group_id}") # finally 블록 추가 및 로그

    def stop(self):
        """스레드 중지 요청"""
        logger.info(f"워커 스레드 stop() 호출됨: 그룹 {self.group_id}") # stop 메소드 호출 로그 추가
        self._is_running = False
        logger.debug(f"워커 스레드 중지 요청됨: 그룹 {self.group_id}")

    def is_running(self):
        """스레드 실행 상태 확인"""
        return self._is_running 