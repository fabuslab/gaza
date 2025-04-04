"""
관심종목 데이터베이스 모듈
"""

import sqlite3
import logging
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class WatchlistDatabase:
    """관심종목 데이터베이스 클래스"""
    
    def __init__(self, db_path: str = "data/database/watchlist.db"):
        """초기화"""
        logger.info(f"데이터베이스 초기화 시작: {db_path}")
        self.db_path = db_path
        self._ensure_db_exists()
        logger.info("데이터베이스 초기화 완료")
        
    def _ensure_db_exists(self):
        """데이터베이스 파일 존재 확인 및 생성"""
        try:
            db_file = Path(self.db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            
            # DB 파일이 존재하는지 확인
            if not db_file.exists():
                logger.debug(f"데이터베이스 파일 생성: {self.db_path}")
                # 빈 데이터베이스 파일 생성
                open(db_file, 'a').close()
            else:
                logger.debug(f"데이터베이스 파일 존재: {self.db_path}")
                
            # 테이블 생성 - 기존 파일이 있더라도 테이블이 없으면 생성
            self._create_tables()
            
        except Exception as e:
            logger.error(f"데이터베이스 파일 확인 중 오류 발생: {e}", exc_info=True)
            raise
            
    def _create_tables(self):
        """테이블 생성"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Foreign Key 제약 조건 활성화
                conn.execute("PRAGMA foreign_keys = ON")
                
                cursor = conn.cursor()
                
                # 테이블 존재 여부 확인
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='watchlist_groups'")
                group_table_exists = cursor.fetchone() is not None
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='watchlist'")
                stock_table_exists = cursor.fetchone() is not None
                
                # 그룹 테이블이 없으면 생성
                if not group_table_exists:
                    logger.debug("관심 그룹 테이블 생성")
                    cursor.execute("""
                        CREATE TABLE watchlist_groups (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL UNIQUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # 기본 관심 그룹 생성
                    cursor.execute(
                        "INSERT OR IGNORE INTO watchlist_groups (name) VALUES (?)",
                        ("기본 그룹",)
                    )
                
                # 종목 테이블이 없으면 생성
                if not stock_table_exists:
                    logger.debug("관심종목 테이블 생성")
                    cursor.execute("""
                        CREATE TABLE watchlist (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            group_id INTEGER NOT NULL,
                            stock_code TEXT NOT NULL,
                            stock_name TEXT NOT NULL,
                            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (group_id) REFERENCES watchlist_groups (id) ON DELETE CASCADE,
                            UNIQUE (group_id, stock_code)
                        )
                    """)
                
                conn.commit()
                logger.debug("테이블 생성 완료")
        except Exception as e:
            logger.error(f"테이블 생성 중 오류 발생: {e}", exc_info=True)
            raise
            
    # 관심 그룹 관련 메서드
    def create_watchlist(self, name: str) -> bool:
        """관심 그룹 생성
        
        Args:
            name: 관심 그룹 이름
            
        Returns:
            성공 여부
        """
        logger.debug(f"관심 그룹 생성 시도: {name}")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO watchlist_groups (name) VALUES (?)",
                    (name,)
                )
                conn.commit()
                logger.info(f"관심 그룹 생성 완료: {name}")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"관심 그룹 생성 실패 (중복): {name}")
            return False
        except Exception as e:
            logger.error(f"관심 그룹 생성 실패: {e}", exc_info=True)
            return False
            
    def get_watchlists(self) -> List[Dict]:
        """관심 그룹 조회
        
        Returns:
            [{"id": id, "name": name, "created_at": created_at}, ...]
        """
        logger.debug("관심 그룹 조회 시작")
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, name, created_at FROM watchlist_groups ORDER BY id"
                )
                watchlists = [dict(row) for row in cursor.fetchall()]
                logger.info(f"관심 그룹 조회 완료: {len(watchlists)}개")
                return watchlists
        except Exception as e:
            logger.error(f"관심 그룹 조회 실패: {e}", exc_info=True)
            return []
            
    def rename_watchlist(self, watchlist_id: int, name: str) -> bool:
        """관심 그룹 이름 변경
        
        Args:
            watchlist_id: 관심 그룹 ID
            name: 새 이름
            
        Returns:
            성공 여부
        """
        logger.debug(f"관심 그룹 이름 변경 시도: {watchlist_id} -> {name}")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE watchlist_groups SET name = ?, updated_at = ? WHERE id = ?",
                    (name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), watchlist_id)
                )
                conn.commit()
                if cursor.rowcount > 0:
                    logger.info(f"관심 그룹 이름 변경 완료: {watchlist_id} -> {name}")
                    return True
                else:
                    logger.warning(f"관심 그룹 이름 변경 실패 (ID 없음): {watchlist_id}")
                    return False
        except sqlite3.IntegrityError:
            logger.warning(f"관심 그룹 이름 변경 실패 (중복): {name}")
            return False
        except Exception as e:
            logger.error(f"관심 그룹 이름 변경 실패: {e}", exc_info=True)
            return False
            
    def delete_watchlist(self, watchlist_id: int) -> bool:
        """관심 그룹 삭제
        
        Args:
            watchlist_id: 관심 그룹 ID
            
        Returns:
            성공 여부
        """
        logger.debug(f"관심 그룹 삭제 시도: {watchlist_id}")
        try:
            # 기본 그룹(ID=1)은 삭제 불가
            if watchlist_id == 1:
                logger.warning("기본 그룹은 삭제할 수 없습니다.")
                return False
                
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM watchlist_groups WHERE id = ?", (watchlist_id,))
                conn.commit()
                if cursor.rowcount > 0:
                    logger.info(f"관심 그룹 삭제 완료: {watchlist_id}")
                    return True
                else:
                    logger.warning(f"관심 그룹 삭제 실패 (ID 없음): {watchlist_id}")
                    return False
        except Exception as e:
            logger.error(f"관심 그룹 삭제 실패: {e}", exc_info=True)
            return False
            
    # 관심종목 관련 메서드
    def add_stock(self, group_id: int, stock_code: str, stock_name: str) -> bool:
        """관심종목 추가
        
        Args:
            group_id: 관심 그룹 ID
            stock_code: 종목 코드
            stock_name: 종목 이름
            
        Returns:
            성공 여부
        """
        logger.debug(f"종목 추가 시도: 그룹 {group_id}, 종목 {stock_code} ({stock_name})")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO watchlist (group_id, stock_code, stock_name) VALUES (?, ?, ?)",
                    (group_id, stock_code, stock_name)
                )
                conn.commit()
                logger.info(f"종목 추가 완료: 그룹 {group_id}, 종목 {stock_code}")
                return True
        except Exception as e:
            logger.error(f"종목 추가 실패: {e}", exc_info=True)
            return False
            
    def remove_stock(self, group_id: int, stock_code: str) -> bool:
        """관심종목 삭제
        
        Args:
            group_id: 관심 그룹 ID
            stock_code: 종목 코드
            
        Returns:
            성공 여부
        """
        logger.debug(f"종목 삭제 시도: 그룹 {group_id}, 종목 {stock_code}")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM watchlist WHERE group_id = ? AND stock_code = ?", 
                    (group_id, stock_code)
                )
                conn.commit()
                if cursor.rowcount > 0:
                    logger.info(f"종목 삭제 완료: 그룹 {group_id}, 종목 {stock_code}")
                    return True
                else:
                    logger.warning(f"종목 삭제 실패 (없음): 그룹 {group_id}, 종목 {stock_code}")
                    return False
        except Exception as e:
            logger.error(f"종목 삭제 실패: {e}", exc_info=True)
            return False
            
    def get_stocks(self, group_id: int) -> List[Dict]:
        """그룹 내 관심종목 조회
        
        Args:
            group_id: 관심 그룹 ID
            
        Returns:
            [{"stock_code": code, "stock_name": name}, ...]
        """
        logger.debug(f"그룹 내 종목 조회 시작: 그룹 {group_id}")
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT stock_code, stock_name FROM watchlist WHERE group_id = ? ORDER BY added_at DESC",
                    (group_id,)
                )
                stocks = [dict(row) for row in cursor.fetchall()]
                logger.info(f"그룹 내 종목 조회 완료: 그룹 {group_id}, {len(stocks)}개")
                return stocks
        except Exception as e:
            logger.error(f"그룹 내 종목 조회 실패: {e}", exc_info=True)
            return []
            
    def get_all_stocks(self) -> List[Dict]:
        """모든 종목 조회 (기본 그룹)
        
        Returns:
            [{"stock_code": code, "stock_name": name}, ...]
        """
        logger.debug("모든 종목 조회 시작 (기본 그룹)")
        try:
            # 기본 그룹(ID=1)의 종목 조회
            return self.get_stocks(1)
        except Exception as e:
            logger.error(f"모든 종목 조회 실패: {e}", exc_info=True)
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
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM watchlist WHERE group_id = ? AND stock_code = ?", 
                    (group_id, stock_code)
                )
                exists = cursor.fetchone()[0] > 0
                logger.debug(f"종목 존재 여부 확인 완료: 그룹 {group_id}, 종목 {stock_code} - {'존재' if exists else '없음'}")
                return exists
        except Exception as e:
            logger.error(f"종목 확인 실패: {e}", exc_info=True)
            return False

    def close(self):
        """데이터베이스 연결 정리"""
        logger.info(f"데이터베이스 연결 정리: {self.db_path}")
        try:
            # SQLite는 connection 객체를 유지하지 않고 필요할 때 연결하므로
            # 명시적인 close 작업은 필요 없지만 로그를 위해 메서드 구현
            
            # 메모리 정리 및 GC 유도를 위한 조치
            if hasattr(self, 'db_path'):
                self.db_path = None
                
            logger.debug("데이터베이스 연결 정리 완료")
        except Exception as e:
            logger.error(f"데이터베이스 연결 정리 중 오류: {e}", exc_info=True) 