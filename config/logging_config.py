"""
로깅 설정 모듈
"""

import os
import logging
import logging.handlers
from datetime import datetime

def setup_logging():
    """로깅 설정"""
    # 로그 디렉토리 생성
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # 오늘 날짜 로그 파일
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"app_{today}.log")
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 파일 핸들러 설정 (날짜별 로그 파일)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 포맷 설정
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 디버깅 로그 파일 (항상 덮어쓰기)
    debug_log_file = os.path.join(log_dir, "debug.log")
    debug_handler = logging.FileHandler(debug_log_file, mode="w", encoding="utf-8")
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(formatter)
    root_logger.addHandler(debug_handler)
    
    # 에러 로그 파일 (추가 모드)
    error_log_file = os.path.join(log_dir, "error.log")
    error_handler = logging.FileHandler(error_log_file, mode="a", encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    logging.info("로깅 설정 완료") 