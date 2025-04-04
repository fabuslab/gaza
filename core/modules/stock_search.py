"""
주식 검색 모듈
"""

import logging
from typing import Dict, Optional
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class StockSearchModule(QObject):
    """주식 검색 모듈"""
    
    # 검색 결과 시그널
    search_result = pyqtSignal(dict)
    # 오류 시그널
    error_occurred = pyqtSignal(str)
    
    def __init__(self, api):
        """
        Args:
            api: KiwoomAPI 인스턴스
        """
        super().__init__()
        self.api = api
        
    def search_stock(self, stock_code: str) -> Optional[Dict]:
        """종목 검색
        
        Args:
            stock_code: 종목코드
            
        Returns:
            {
                "stk_cd": 종목코드,
                "stk_nm": 종목명,
                "cur_prc": 현재가,
                "prc_diff": 전일대비,
                "prc_diff_sign": 등락부호,
                "fluc_rt": 등락률,
                "trd_qty": 거래량,
                "trd_amt": 거래대금
            }
        """
        try:
            # API를 통해 종목 정보 조회
            result = self.api.get_stock_info(stock_code)
            if result:
                # 필요한 정보만 추출하여 반환
                stock_info = {
                    "stk_cd": result["stk_cd"],
                    "stk_nm": result["stk_nm"],
                    "cur_prc": result["cur_prc"],
                    "prc_diff": result["prc_diff"],
                    "prc_diff_sign": result["prc_diff_sign"],
                    "fluc_rt": result["fluc_rt"],
                    "trd_qty": result["trd_qty"],
                    "trd_amt": result["trd_amt"]
                }
                self.search_result.emit(stock_info)
                return stock_info
            else:
                self.error_occurred.emit("종목을 찾을 수 없습니다.")
                return None
        except Exception as e:
            logger.error(f"종목 검색 실패: {e}")
            self.error_occurred.emit(f"종목 검색 중 오류 발생: {str(e)}")
            return None 