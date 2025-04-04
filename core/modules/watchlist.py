"""
관심목록 모듈
"""

import logging
import json
import os
from typing import Dict, List, Optional
# from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, pyqtSlot # 이전
from PySide6.QtCore import QObject, Signal as pyqtSignal, QTimer, QThread, Slot as pyqtSlot # 변경

from core.database.watchlist_db import WatchlistDatabase
from core.api.kiwoom import KiwoomAPI
from core.ui.constants.colors import Colors
# 워커 임포트 경로 수정
from core.workers.watchlist_worker import WatchlistUpdateWorker

logger = logging.getLogger(__name__)

class WatchlistModule(QObject):
    """관심목록 모듈"""
    
    # 관심목록 업데이트 시그널
    watchlist_updated = pyqtSignal(int, list)  # group_id, stock_info_list
    watchlist_group_updated = pyqtSignal(list)  # [{"id": id, "name": name}, ...]
    # 오류 시그널
    error_occurred = pyqtSignal(str)
    
    def __init__(self, api: KiwoomAPI, db_path: str = "data/database/watchlist.db"):
        """
        Args:
            api: KiwoomAPI 인스턴스
            db_path: 데이터베이스 파일 경로
        """
        logger.info("관심목록 모듈 초기화 시작")
        super().__init__()
        self.api = api
        self.db = WatchlistDatabase(db_path)
        
        # 현재 활성화된 그룹 ID (기본값은 1)
        self.active_group_id = 1
        
        # 실시간 업데이트 타이머 (2초 간격)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.start_watchlist_update)
        self.update_timer.start(2000)
        logger.debug("실시간 업데이트 타이머 설정 완료")
        logger.info("관심목록 모듈 초기화 완료")
        
        self.current_worker: Optional[WatchlistUpdateWorker] = None # 현재 실행 중인 워커
        
    def create_watchlist(self, name: str) -> bool:
        """관심목록 생성
        
        Args:
            name: 관심목록 이름
            
        Returns:
            성공 여부
        """
        logger.debug(f"관심목록 생성 시도: {name}")
        try:
            # 빈 이름인 경우 생성 불가
            if not name.strip():
                logger.warning("관심목록 이름이 비어있습니다.")
                return False
            
            # 이미 동일한 이름의 그룹이 있는지 확인
            existing_watchlists = self.get_watchlists()
            for watchlist in existing_watchlists:
                if watchlist["name"].lower() == name.lower():
                    logger.warning(f"이미 존재하는 관심목록 이름: {name}")
                    return False
                
            # 데이터베이스에 관심목록 생성
            result = self.db.create_watchlist(name)
            if result:
                logger.info(f"관심목록 생성 완료: {name}")
                # 그룹 목록 업데이트 시그널 발생
                self.watchlist_group_updated.emit(self.get_watchlists())
            else:
                logger.warning(f"관심목록 생성 실패: {name}")
            return result
        except Exception as e:
            logger.error(f"관심목록 생성 중 오류 발생: {e}", exc_info=True)
            self.error_occurred.emit(f"관심목록 생성 실패: {str(e)}")
            return False
        
    def get_watchlists(self) -> List[Dict]:
        """관심목록 조회
        
        Returns:
            [{"id": id, "name": name, "created_at": created_at}, ...]
        """
        logger.debug("관심목록 조회 시작")
        try:
            watchlists = self.db.get_watchlists()
            logger.info(f"관심목록 조회 완료: {len(watchlists)}개")
            return watchlists
        except Exception as e:
            logger.error(f"관심목록 조회 실패: {e}", exc_info=True)
            self.error_occurred.emit(f"관심목록 조회 실패: {str(e)}")
            return []
        
    def delete_watchlist(self, watchlist_id: int) -> bool:
        """관심목록 삭제
        
        Args:
            watchlist_id: 관심목록 ID
            
        Returns:
            성공 여부
        """
        logger.debug(f"관심목록 삭제 시도: {watchlist_id}")
        try:
            result = self.db.delete_watchlist(watchlist_id)
            if result:
                logger.info(f"관심목록 삭제 완료: {watchlist_id}")
                # 그룹 목록 업데이트 시그널 발생
                self.watchlist_group_updated.emit(self.get_watchlists())
            else:
                logger.warning(f"관심목록 삭제 실패: {watchlist_id}")
            return result
        except Exception as e:
            logger.error(f"관심목록 삭제 중 오류 발생: {e}", exc_info=True)
            self.error_occurred.emit(f"관심목록 삭제 실패: {str(e)}")
            return False
        
    def add_stock(self, group_id: int, stock_code: str) -> bool:
        """종목 추가
        
        Args:
            group_id: 관심 그룹 ID
            stock_code: 종목 코드
            
        Returns:
            성공 여부
        """
        logger.debug(f"종목 추가 시도: 그룹 {group_id}, 종목 {stock_code}")
        try:
            # 종목코드가 숫자가 아닌 경우, 종목코드 형식이 아니므로 실패 처리
            if not stock_code or not any(c.isdigit() for c in stock_code):
                logger.warning(f"종목코드 형식 오류: {stock_code}")
                return False
                
            # 중복 입력 확인 (이미 해당 그룹에 있는지)
            if self.is_stock_exists(group_id, stock_code):
                logger.info(f"이미 존재하는 종목: 그룹 {group_id}, 종목 {stock_code}")
                return True
                
            # 종목 정보 조회
            stock_info = self.api.get_stock_info(stock_code)
            
            # 종목명 추출
            stock_name = None
            
            # API 응답 확인 및 처리
            if isinstance(stock_info, dict) and 'atn_stk_infr' in stock_info:
                stock_data = stock_info['atn_stk_infr'][0] if stock_info['atn_stk_infr'] else {}
                if stock_data and 'stk_nm' in stock_data and stock_data['stk_nm']:
                    stock_name = stock_data['stk_nm']
            
            # 종목명이 없는 경우 기본값 설정 (종목코드를 사용)
            if not stock_name:
                stock_name = stock_code
                logger.warning(f"종목 정보를 찾을 수 없어 기본 이름 사용: {stock_code}")
                
            # 데이터베이스에 추가
            result = self.db.add_stock(group_id, stock_code, stock_name)
            if result:
                logger.info(f"종목 추가 완료: 그룹 {group_id}, 종목 {stock_code} ({stock_name})")
                # 그룹 내 종목 업데이트 시그널 발생
                self.start_watchlist_update()
            else:
                logger.warning(f"종목 추가 실패: 그룹 {group_id}, 종목 {stock_code}")
            return result
            
        except Exception as e:
            logger.error(f"종목 추가 실패: {e}", exc_info=True)
            self.error_occurred.emit(f"종목 추가 실패: {str(e)}")
            return False
            
    def remove_stock(self, group_id: int, stock_code: str) -> bool:
        """종목 삭제
        
        Args:
            group_id: 관심 그룹 ID
            stock_code: 종목 코드
            
        Returns:
            성공 여부
        """
        logger.debug(f"종목 삭제 시도: 그룹 {group_id}, 종목 {stock_code}")
        try:
            result = self.db.remove_stock(group_id, stock_code)
            if result:
                logger.info(f"종목 삭제 완료: 그룹 {group_id}, 종목 {stock_code}")
                # 그룹 내 종목 업데이트 시그널 발생
                self.start_watchlist_update()
            else:
                logger.warning(f"종목 삭제 실패: 그룹 {group_id}, 종목 {stock_code}")
            return result
        except Exception as e:
            logger.error(f"종목 삭제 실패: {e}", exc_info=True)
            self.error_occurred.emit(f"종목 삭제 실패: {str(e)}")
            return False
            
    def start_watchlist_update(self):
        """활성 관심 그룹 업데이트 워커 스레드 시작"""
        # 이미 실행 중인 워커가 있으면 중복 실행 방지
        if self.current_worker and self.current_worker.isRunning():
            logger.debug(f"이미 업데이트 워커 실행 중: 그룹 {self.active_group_id}")
            return
            
        logger.debug(f"업데이트 워커 스레드 시작 요청: 그룹 {self.active_group_id}")
        # 이전 워커가 있다면 종료 요청 및 대기 (선택적)
        # if self.current_worker:
        #     self.current_worker.stop()
        #     self.current_worker.wait() 
            
        # 새 워커 생성 및 시작
        self.current_worker = WatchlistUpdateWorker(self.api, self.db, self.active_group_id)
        self.current_worker.update_finished.connect(self._on_update_finished)
        self.current_worker.error_occurred.connect(self.error_occurred.emit) # 오류 시그널 연결
        # 스레드 종료 시 self.current_worker 초기화
        self.current_worker.finished.connect(self._on_worker_finished)
        self.current_worker.start()

    @pyqtSlot(int, list)
    def _on_update_finished(self, group_id: int, stock_info_list: list):
        """워커 스레드 작업 완료 시 호출되는 슬롯"""
        logger.debug(f"워커 작업 완료 수신: 그룹 {group_id}, {len(stock_info_list)}개 종목")
        # 메인 스레드에서 UI 업데이트 시그널 발생
        self.watchlist_updated.emit(group_id, stock_info_list)
        
    @pyqtSlot()
    def _on_worker_finished(self):
        """워커 스레드 종료 시 호출되는 슬롯"""
        sender_worker = self.sender()
        worker_info = "알 수 없음"
        if isinstance(sender_worker, WatchlistUpdateWorker):
            worker_info = f"그룹 {sender_worker.group_id}"
            logger.info(f"워커 스레드 finished 시그널 수신: {worker_info}") # 시그널 수신 로그 추가
            
            logger.debug(f"워커({worker_info}) 객체 deleteLater() 호출 시도") # deleteLater 호출 전 로그
            sender_worker.deleteLater() # 종료된 워커 객체 정리 예약
            
            # 현재 모듈의 current_worker가 방금 종료된 워커와 동일한 경우에만 None으로 설정
            if self.current_worker is sender_worker:
                self.current_worker = None
                logger.debug(f"현재 워커 참조 제거 완료: {worker_info}")
            else:
                # self.current_worker가 다른 워커를 가리키고 있다면(그룹 변경 직후 등), 아무것도 하지 않음
                logger.debug(f"종료된 워커({worker_info})는 현재 활성 워커가 아니므로 참조 변경 없음")
        else:
            logger.warning(f"finished 시그널 발신자 확인 불가 또는 타입 불일치: {sender_worker}")
        
    def set_active_group(self, group_id: int):
        """활성 그룹 설정 (수정: 워커 중지 및 재시작 로직 추가)"""
        if self.active_group_id == group_id:
            return # 변경 없으면 아무것도 안 함
            
        logger.debug(f"활성 그룹 변경: {self.active_group_id} -> {group_id}")
        self.active_group_id = group_id
        
        # 현재 실행 중인 워커 중지
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.stop()
            # self.current_worker.wait() # 즉시 종료를 기다릴 필요는 없을 수 있음
            
        # 새 그룹으로 즉시 업데이트 시작
        self.start_watchlist_update()
        
    def get_trend_info(self, stock: Dict) -> Dict:
        """종목의 추세 정보를 반환합니다."""
        logger.debug(f"추세 정보 반환: {stock.get('stk_cd', '')}")
        try:
            # 등락률에 따른 추세 표시 - API 응답에서 flu_rt 필드를 우선 사용
            fluc_rt_value = stock.get('flu_rt', stock.get('fluc_rt', '0'))
            
            # 거래량 확인
            volume_str = stock.get('trde_qty', stock.get('trd_qty', '0'))
            
            # 문자열 처리
            if isinstance(fluc_rt_value, str):
                fluc_rt_value = fluc_rt_value.replace('%', '').replace('+', '').strip()
            
            # 거래량 문자열 처리
            if isinstance(volume_str, str):
                volume_str = volume_str.replace(',', '')
                
            # 숫자 변환
            try:
                fluc_rt = float(fluc_rt_value)
            except ValueError:
                fluc_rt = 0.0
                
            try:
                volume = float(volume_str)
            except ValueError:
                volume = 0
                
            # 추세 정보 생성 (요구사항에 맞게 수정)
            if fluc_rt >= 5 and volume >= 1000000:  # 등락률 5% 이상, 거래량 100만 이상
                return {
                    "arrow": "↑↑",
                    "text": "강한 상승",
                    "color": Colors.PRICE_UP
                }
            elif fluc_rt >= 1:  # 등락률 1% 이상
                return {
                    "arrow": "↑",
                    "text": "상승",
                    "color": Colors.PRICE_UP
                }
            elif fluc_rt <= -5 and volume >= 1000000:  # 등락률 -5% 이하, 거래량 100만 이상
                return {
                    "arrow": "↓↓",
                    "text": "강한 하락",
                    "color": Colors.PRICE_DOWN
                }
            elif fluc_rt <= -1:  # 등락률 -1% 이하
                return {
                    "arrow": "↓",
                    "text": "하락",
                    "color": Colors.PRICE_DOWN
                }
            else:  # 등락률 -1%~1% 사이
                return {
                    "arrow": "→",
                    "text": "중립",
                    "color": Colors.PRICE_UNCHANGED
                }
        except Exception as e:
            logger.error(f"추세 정보 반환 중 오류 발생: {e}", exc_info=True)
            # 오류 시 기본값 반환
            return {
                "arrow": "→",
                "text": "정보 없음",
                "color": Colors.TEXT
            }

    def get_all_stocks(self) -> List[Dict]:
        """모든 종목 조회"""
        logger.debug("모든 종목 조회 시작")
        try:
            stocks = self.db.get_all_stocks()
            logger.info(f"모든 종목 조회 완료: {len(stocks)}개")
            return stocks
        except Exception as e:
            logger.error(f"종목 조회 실패: {e}", exc_info=True)
            return []
            
    def is_stock_exists(self, group_id: int, stock_code: str) -> bool:
        """종목 존재 여부 확인
        
        Args:
            group_id: 관심 그룹 ID
            stock_code: 종목 코드
            
        Returns:
            존재 여부
        """
        logger.debug(f"종목 존재 여부 확인: 그룹 {group_id}, 종목 {stock_code}")
        try:
            exists = self.db.is_stock_exists(group_id, stock_code)
            logger.debug(f"종목 존재 여부 확인 완료: 그룹 {group_id}, 종목 {stock_code} - {'존재' if exists else '없음'}")
            return exists
        except Exception as e:
            logger.error(f"종목 확인 실패: {e}", exc_info=True)
            return False

    def rename_watchlist(self, watchlist_id: int, name: str) -> bool:
        """관심목록 이름 변경
        
        Args:
            watchlist_id: 관심목록 ID
            name: 새 이름
            
        Returns:
            성공 여부
        """
        logger.debug(f"관심목록 이름 변경 시도: {watchlist_id} -> {name}")
        try:
            result = self.db.rename_watchlist(watchlist_id, name)
            if result:
                logger.info(f"관심목록 이름 변경 완료: {watchlist_id} -> {name}")
                # 그룹 목록 업데이트 시그널 발생
                self.watchlist_group_updated.emit(self.get_watchlists())
            else:
                logger.warning(f"관심목록 이름 변경 실패: {watchlist_id} -> {name}")
            return result
        except Exception as e:
            logger.error(f"관심목록 이름 변경 중 오류 발생: {e}", exc_info=True)
            self.error_occurred.emit(f"관심목록 이름 변경 실패: {str(e)}")
            return False

    def get_stocks_basic_info(self, group_id: int) -> List[Dict]:
        """그룹 내 관심종목 기본 정보만 조회 (DB에서만 조회, API 호출 없음)
        
        Args:
            group_id: 관심 그룹 ID
            
        Returns:
            종목 기본 정보 목록 (코드, 이름만 포함)
        """
        logger.debug(f"관심종목 기본 정보 조회 시작: 그룹 {group_id}")
        try:
            # 데이터베이스에서 종목 목록 조회
            db_stocks = self.db.get_stocks(group_id)
            if not db_stocks:
                logger.info(f"등록된 관심종목 없음: 그룹 {group_id}")
                return []
            
            # 기본 정보만 포함하는 리스트 생성
            result_stocks = []
            for stock in db_stocks:
                result_stocks.append({
                    'stk_cd': stock["stock_code"],
                    'stk_nm': stock["stock_name"],
                    'cur_prc': '0',
                    'prc_diff': '0',
                    'prc_diff_sign': '0',
                    'fluc_rt': '0',
                    'trd_qty': '0',
                    'trde_prica': '0'
                })
            
            logger.info(f"관심종목 기본 정보 조회 완료: 그룹 {group_id}, {len(result_stocks)}개")
            return result_stocks
            
        except Exception as e:
            logger.error(f"관심종목 기본 정보 조회 실패: {e}", exc_info=True)
            self.error_occurred.emit(f"관심종목 기본 정보 조회 실패: {str(e)}")
            return []

    def remove_group(self, group_id: int) -> bool:
        """관심 그룹 삭제
        
        Args:
            group_id: 관심 그룹 ID
            
        Returns:
            성공 여부
        """
        logger.debug(f"관심 그룹 삭제 시도: {group_id}")
        try:
            # 기본 그룹(ID=1)은 삭제 불가
            if group_id == 1:
                logger.warning("기본 그룹은 삭제할 수 없습니다.")
                return False
                
            # 데이터베이스에서 그룹 삭제
            result = self.db.delete_watchlist(group_id)
            if result:
                logger.info(f"관심 그룹 삭제 완료: {group_id}")
                # 그룹 목록 업데이트 시그널 발생
                self.watchlist_group_updated.emit(self.get_watchlists())
            else:
                logger.warning(f"관심 그룹 삭제 실패: {group_id}")
            return result
            
        except Exception as e:
            logger.error(f"관심 그룹 삭제 중 오류 발생: {e}", exc_info=True)
            self.error_occurred.emit(f"관심 그룹 삭제 실패: {str(e)}")
            return False

    def stop_watchlist_update(self):
        """현재 실행 중인 워치리스트 업데이트 워커 스레드를 중지하고 종료될 때까지 기다립니다."""
        if self.current_worker and self.current_worker.isRunning():
            logger.info(f"워치리스트 워커 스레드 중지 요청: 그룹 {self.current_worker.group_id}")
            self.current_worker.stop()
            # 스레드가 완전히 종료될 때까지 대기 (타임아웃 제거)
            logger.info(f"워치리스트 워커 ({self.current_worker.group_id}) 종료 대기 시작...") # 상세 로그 추가
            wait_success = self.current_worker.wait() # Wait indefinitely, capture result
            logger.info(f"워치리스트 워커 ({self.current_worker.group_id}) 종료 대기 완료 (wait 성공: {wait_success}).") # wait 결과 로그 추가
            # if not self.current_worker.wait(5000): # 이전 타임아웃 로직 제거
            #     logger.warning("워치리스트 워커 스레드 종료 대기 시간 초과.")
            # else:
            #     logger.info("워치리스트 워커 스레드 정상 종료 확인.")
            logger.info("워치리스트 워커 스레드 종료 대기 완료.") # 로그 수정
        else:
            logger.debug("현재 실행 중인 워치리스트 워커 없음.")

    def cleanup(self):
        """모듈 정리 (수정: 워커 스레드 종료 추가)"""
        logger.info("관심목록 모듈 정리 시작")
        
        if hasattr(self, 'update_timer') and self.update_timer.isActive(): # 타이머 존재 확인
            self.update_timer.stop()
            logger.debug("관심목록 업데이트 타이머 중지")
            
        # 실행 중인 워커 스레드 종료
        self.stop_watchlist_update() # 추가된 중지 메소드 호출
        # if self.current_worker and self.current_worker.isRunning(): # 이전 로직 제거
        #     logger.debug("실행 중인 워커 스레드 중지 요청...")
        #     self.current_worker.stop()
        #     self.current_worker.wait() # 스레드가 완전히 종료될 때까지 대기 추가 -> stop_watchlist_update 에서 처리
        #     logger.debug("워커 스레드 중지 완료.")
        
        if hasattr(self, 'db') and self.db:
            try:
                self.db.close()
                logger.debug("관심목록 데이터베이스 연결 종료")
            except Exception as e:
                logger.error(f"데이터베이스 연결 종료 중 오류: {e}", exc_info=True)
                
        logger.info("관심목록 모듈 정리 완료")

    # _map_api_stock_to_db_format 함수는 현재 사용되지 않으므로 주석 처리 또는 삭제 가능
    # def _map_api_stock_to_db_format(self, api_stock, group_id): ... 