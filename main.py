#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
가즈아! 트레이딩 - 메인 프로그램
"""

import sys
import os
import logging
import traceback
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from datetime import datetime

print(f"[{datetime.now()}] DEBUG: main.py 스크립트 시작")
sys.stdout.flush()

try:
    print(f"[{datetime.now()}] DEBUG: PySide6 임포트 시도...")
    sys.stdout.flush()
    print(f"[{datetime.now()}] DEBUG: PySide6 임포트 성공!")
    sys.stdout.flush()
except ImportError as e:
    print(f"[{datetime.now()}] CRITICAL: PySide6 임포트 실패! 오류: {e}")
    print(traceback.format_exc())
    sys.stdout.flush()
    sys.exit(1)

# pandas 임포트 테스트 (pandas_ta 없이)
try:
    print(f"[{datetime.now()}] DEBUG: pandas 임포트 시도...")
    sys.stdout.flush()
    import pandas as pd
    print(f"[{datetime.now()}] DEBUG: pandas 임포트 성공! 버전: {pd.__version__}")
    sys.stdout.flush()
    
    # pandas_ta 관련 오류 해결을 위한 환경 설정
    print(f"[{datetime.now()}] DEBUG: pandas_ta 오류 해결을 위한 설정 적용...")
    sys.path.append(os.path.join(os.path.dirname(__file__), 'venv311', 'Lib', 'site-packages'))
    os.environ['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), 'venv311', 'Lib', 'site-packages')
    print(f"[{datetime.now()}] DEBUG: sys.path: {sys.path}")
    sys.stdout.flush()
except Exception as e:
    print(f"[{datetime.now()}] CRITICAL: pandas 임포트 실패! 오류: {e}")
    print(traceback.format_exc())
    sys.stdout.flush()
    sys.exit(1)

# 추가: ChartModule 임포트 테스트
try:
    print(f"[{datetime.now()}] DEBUG: ChartModule 임포트 시도...")
    sys.stdout.flush()
    from core.modules.chart import ChartModule
    print(f"[{datetime.now()}] DEBUG: ChartModule 임포트 성공!")
    sys.stdout.flush()
except Exception as e:
    print(f"[{datetime.now()}] CRITICAL: ChartModule 임포트 실패! 오류: {e}")
    print(traceback.format_exc())
    sys.stdout.flush()
    sys.exit(1)

# 추가: ChartComponent 임포트 테스트
print(f"[{datetime.now()}] DEBUG: ChartComponent 임포트 시도...")
sys.stdout.flush()
try:
    from core.ui.components.chart_component import ChartComponent
    print(f"[{datetime.now()}] DEBUG: ChartComponent 임포트 성공!")
    sys.stdout.flush()
except Exception as e:
    print(f"[{datetime.now()}] CRITICAL: ChartComponent 임포트 중 오류 발생! 오류: {e}")
    print("-- Traceback --")
    print(traceback.format_exc())
    print("----")
    sys.stdout.flush()
    sys.exit(1) # Exit if import fails

# MainWindow 임포트 테스트 (수정: 상세 오류 출력)
try:
    print(f"[{datetime.now()}] DEBUG: MainWindow 임포트 시도...")
    sys.stdout.flush()
    from core.ui.main_window import MainWindow
    print(f"[{datetime.now()}] DEBUG: MainWindow 임포트 성공!")
    sys.stdout.flush()
except Exception as e:
    print(f"[{datetime.now()}] CRITICAL: MainWindow 임포트 중 치명적 오류 발생! 오류: {e}")
    print("-- Traceback --")
    print(traceback.format_exc())
    print("----")
    try:
        import core.ui.main_window
        print(f"core.ui.main_window 모듈 경로: {core.ui.main_window.__file__}")
    except Exception as import_err:
        print(f"core.ui.main_window 모듈 자체를 임포트하는 중 오류: {import_err}")
    sys.stdout.flush()
    sys.exit(1)

from core.ui.dialogs.api_key_dialog import APIKeyDialog # 원래대로 복구
from core.utils.crypto import decrypt_data

def setup_logging():
    """로깅 설정"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        datefmt=date_format,
        handlers= [
            logging.FileHandler('logs/app.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def check_api_keys() -> bool:
    """API 키 확인"""
    print(f"[{datetime.now()}] DEBUG: check_api_keys() 호출됨") # 로그 추가
    sys.stdout.flush()
    settings = QSettings("GazuaTrading", "Trading") # 원래대로 복구
    kiwoom_key = settings.value("api/kiwoom_key")
    kiwoom_secret = settings.value("api/kiwoom_secret")
    openai_key = settings.value("api/openai_key")
    print(f"Kiwoom Key Loaded: {'Exists' if kiwoom_key else 'None'}")
    print(f"Kiwoom Secret Loaded: {'Exists' if kiwoom_secret else 'None'}")
    print(f"OpenAI Key Loaded: {'Exists' if openai_key else 'None'}")
    sys.stdout.flush()
    if not all([kiwoom_key, kiwoom_secret, openai_key]):
        print(f"[{datetime.now()}] DEBUG: API 키 없음. False 반환.")
        sys.stdout.flush()
        return False
    try:
        print(f"[{datetime.now()}] DEBUG: API 키 복호화 시도...")
        sys.stdout.flush()
        os.environ["KIWOOM_API_KEY"] = decrypt_data(kiwoom_key)
        os.environ["KIWOOM_API_SECRET"] = decrypt_data(kiwoom_secret)
        os.environ["OPENAI_API_KEY"] = decrypt_data(openai_key)
        print(f"[{datetime.now()}] DEBUG: API 키 복호화 및 환경변수 설정 완료. True 반환.")
        sys.stdout.flush()
        return True
    except Exception as e:
        # 로깅 설정 전일 수 있으므로 print 사용
        print(f"[{datetime.now()}] ERROR: API 키 복호화 실패: {e}") 
        sys.stdout.flush()
        # logging.error(f"API 키 복호화 실패: {e}") # 로거 사용 시
        return False

def main():
    """메인 함수"""
    logger = None
    print(f"[{datetime.now()}] DEBUG: main() 함수 시작")
    sys.stdout.flush()
    try:
        print(f"[{datetime.now()}] DEBUG: setup_logging() 호출 전")
        sys.stdout.flush()
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info(f"[{datetime.now()}] 프로그램 시작 - main 함수 진입 (로깅 설정 완료)")
        print(f"[{datetime.now()}] DEBUG: 로깅 설정 완료")
        sys.stdout.flush()

        print(f"[{datetime.now()}] DEBUG: QApplication(sys.argv) 호출 전")
        sys.stdout.flush()
        app = QApplication(sys.argv)
        print(f"[{datetime.now()}] DEBUG: QApplication(sys.argv) 호출 완료")
        sys.stdout.flush()
        logger.info(f"[{datetime.now()}] 프로그램 시작 - QApplication 생성 완료")
        
        logger.info(f"[{datetime.now()}] API 키 확인 시작")
        api_keys_ok = check_api_keys()
        logger.info(f"[{datetime.now()}] check_api_keys() 호출 완료, 결과: {api_keys_ok}")
        if not api_keys_ok:
            logger.info(f"[{datetime.now()}] API 키 없음 또는 오류. API 키 입력 대화상자 표시 시도.")
            print(f"[{datetime.now()}] DEBUG: APIKeyDialog() 생성 전") # 추가 로그
            sys.stdout.flush()
            api_key_dialog = APIKeyDialog()
            print(f"[{datetime.now()}] DEBUG: APIKeyDialog() 생성 완료") # 추가 로그
            sys.stdout.flush()
            logger.info(f"[{datetime.now()}] APIKeyDialog.exec() 호출 전")
            dialog_result = api_key_dialog.exec()
            logger.info(f"[{datetime.now()}] APIKeyDialog 표시 완료, 결과: {dialog_result}")
            if dialog_result != APIKeyDialog.Accepted:
                logger.info(f"[{datetime.now()}] 프로그램 종료: API 키 입력 취소")
                sys.exit(0)
            logger.info(f"[{datetime.now()}] API 키 입력 완료 또는 확인됨.")
        else:
            logger.info(f"[{datetime.now()}] 저장된 API 키 확인 완료.")

        # 명령줄 인수 확인 (원본 유지)
        if len(sys.argv) > 1:
            arg = sys.argv[1].lower()
            if arg == "watchlist":
                logger.info("관심종목 화면 단독 실행 모드")
                from core.api.kiwoom import KiwoomAPI
                from core.ui.windows.integrated_search_watchlist_window import IntegratedSearchWatchlistWindow
                api = KiwoomAPI(os.environ["KIWOOM_API_KEY"], os.environ["KIWOOM_API_SECRET"])
                watchlist_window = IntegratedSearchWatchlistWindow(api)
                watchlist_window.show()
                logger.info("관심종목 화면 이벤트 루프 시작")
                sys.exit(app.exec())
        
        logger.info(f"[{datetime.now()}] 메인 윈도우 생성 시도")
        print(f"[{datetime.now()}] DEBUG: MainWindow() 생성 전") # 추가 로그
        sys.stdout.flush()
        main_window = MainWindow()
        print(f"[{datetime.now()}] DEBUG: MainWindow() 생성 완료") # 추가 로그
        sys.stdout.flush()
        logger.info(f"[{datetime.now()}] 메인 윈도우 생성 완료")

        logger.info(f"[{datetime.now()}] main_window.show() 호출 전")
        print(f"[{datetime.now()}] DEBUG: main_window.show() 호출 전") # 추가 로그
        sys.stdout.flush()
        main_window.show()
        print(f"[{datetime.now()}] DEBUG: main_window.show() 호출 완료") # 추가 로그
        sys.stdout.flush()
        logger.info(f"[{datetime.now()}] main_window.show() 호출 완료")

        logger.info(f"[{datetime.now()}] 메인 이벤트 루프 시작 (app.exec() 호출 전)")
        print(f"[{datetime.now()}] DEBUG: app.exec() 호출 전")
        sys.stdout.flush()
        exit_code = app.exec()
        logger.info(f"[{datetime.now()}] app.exec() 완료, 종료 코드: {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        error_message = f"예외 발생: {e}\n{traceback.format_exc()}"
        print(f"CRITICAL ERROR in main(): {error_message}")
        sys.stdout.flush()
        try:
            if 'logger' in locals() and logger:
                 logger.error(f"프로그램 실행 중 오류 발생: {e}")
                 logger.error(traceback.format_exc())
            else:
                with open('logs/critical_error.log', 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] CRITICAL ERROR: {error_message}\n")
        except Exception as log_err:
             print(f"로깅 중 추가 오류 발생: {log_err}")
             sys.stdout.flush()
        sys.exit(1)

print(f"[{datetime.now()}] DEBUG: 메인 실행 블록 (__name__ == '__main__') 진입 직전")
sys.stdout.flush()

if __name__ == "__main__":
    print(f"[{datetime.now()}] DEBUG: 스크립트 시작 (__name__ == '__main__')")
    sys.stdout.flush()
    main() 