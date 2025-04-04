"""
API 키 입력 대화상자
"""

import logging
from typing import Dict, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, 
    QLineEdit, QPushButton, QLabel,
    QMessageBox, QHBoxLayout, QWidget,
    QProgressDialog, QApplication
)
from PySide6.QtCore import Qt, QTimer, QSize, QMargins, QSettings, Slot as pyqtSlot, Signal as pyqtSignal
from PySide6.QtGui import QFont, QIcon

from core.api.kiwoom import KiwoomAPI
from core.api.openai import OpenAIAPI
from core.utils.crypto import encrypt_data, decrypt_data
from core.ui.constants.colors import Colors
from core.ui.constants.fonts import Fonts, FONT_SIZES
from core.ui.constants.rules import UI_RULES
from core.ui.stylesheets import StyleSheets
import os

logger = logging.getLogger(__name__)

class APIKeyDialog(QDialog):
    """API 키 입력 대화상자"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API 키 설정")
        self.setWindowFlags((self.windowFlags() & ~Qt.WindowContextHelpButtonHint) | Qt.WindowStaysOnTopHint)
        self.setModal(True)
        self.setFixedSize(600, 350) # 요구사항: 사이즈 600x350
        self.setStyleSheet(StyleSheets.WIDGET)
        self.kiwoom_connected = False
        self.openai_connected = False
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)
        
        title_label = QLabel("API 키를 입력해주세요")
        title_label.setStyleSheet(f"""
            color: {Colors.TEXT};
            font-size: {FONT_SIZES.TITLE};
            font-weight: bold;
            padding: {UI_RULES.PADDING_NORMAL} 0;
        """)
        main_layout.addWidget(title_label)
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)
        
        # --- 입력 필드들 (시크릿, OpenAI 키 마스킹 제거) ---
        kiwoom_key_layout = QHBoxLayout()
        kiwoom_key_layout.setSpacing(5)
        kiwoom_key_label = QLabel("키움증권 API 키")
        kiwoom_key_label.setFixedWidth(150)
        kiwoom_key_label.setStyleSheet(StyleSheets.LABEL)
        kiwoom_key_layout.addWidget(kiwoom_key_label)
        self.kiwoom_key_edit = QLineEdit()
        self.kiwoom_key_edit.setPlaceholderText("키움증권 API 키를 입력하세요")
        self.kiwoom_key_edit.setStyleSheet(StyleSheets.INPUT)
        kiwoom_key_layout.addWidget(self.kiwoom_key_edit)
        container_layout.addLayout(kiwoom_key_layout)
        
        kiwoom_secret_layout = QHBoxLayout()
        kiwoom_secret_layout.setSpacing(5)
        kiwoom_secret_label = QLabel("키움증권 API 시크릿")
        kiwoom_secret_label.setFixedWidth(150)
        kiwoom_secret_label.setStyleSheet(StyleSheets.LABEL)
        kiwoom_secret_layout.addWidget(kiwoom_secret_label)
        self.kiwoom_secret_edit = QLineEdit()
        self.kiwoom_secret_edit.setPlaceholderText("키움증권 API 시크릿을 입력하세요")
        self.kiwoom_secret_edit.setStyleSheet(StyleSheets.INPUT)
        # self.kiwoom_secret_edit.setEchoMode(QLineEdit.Password) # 마스킹 제거
        kiwoom_secret_layout.addWidget(self.kiwoom_secret_edit)
        container_layout.addLayout(kiwoom_secret_layout)
        
        openai_key_layout = QHBoxLayout()
        openai_key_layout.setSpacing(5)
        openai_key_label = QLabel("OpenAI API 키")
        openai_key_label.setFixedWidth(150)
        openai_key_label.setStyleSheet(StyleSheets.LABEL)
        openai_key_layout.addWidget(openai_key_label)
        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setPlaceholderText("OpenAI API 키를 입력하세요")
        self.openai_key_edit.setStyleSheet(StyleSheets.INPUT)
        # self.openai_key_edit.setEchoMode(QLineEdit.Password) # 마스킹 제거
        openai_key_layout.addWidget(self.openai_key_edit)
        container_layout.addLayout(openai_key_layout)
        
        # 상태 메시지 영역
        self.status_label = QLabel("API 연결 상태: 미확인")
        self.status_label.setStyleSheet(f"color: {Colors.WARNING}; font-size: {FONT_SIZES.SMALL};")
        container_layout.addWidget(self.status_label)
        
        # 버튼 영역 (통신 테스트 버튼 제거)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_button = QPushButton("저장")
        self.save_button.setStyleSheet(StyleSheets.BUTTON)
        self.save_button.clicked.connect(self.save_and_validate_keys) # 연결 함수 변경
        button_layout.addWidget(self.save_button)
        
        cancel_button = QPushButton("닫기")
        cancel_button.setStyleSheet(StyleSheets.BUTTON)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        container_layout.addLayout(button_layout)
        main_layout.addWidget(container)
        self.setLayout(main_layout)
        
    def test_api_connection_internal(self) -> bool:
        """API 통신 테스트 (내부 호출용)"""
        kiwoom_key = self.kiwoom_key_edit.text().strip()
        kiwoom_secret = self.kiwoom_secret_edit.text().strip()
        openai_key = self.openai_key_edit.text().strip()
        
        if not all([kiwoom_key, kiwoom_secret, openai_key]):
            self.status_label.setText("오류: 모든 API 키를 입력해주세요.")
            self.status_label.setStyleSheet(f"color: {Colors.ERROR}; font-size: {FONT_SIZES.SMALL};")
            return False
            
        self.kiwoom_connected = False
        self.openai_connected = False
        
        # 진행 상태 표시 (옵션)
        # progress = QProgressDialog("API 통신 테스트 중...", None, 0, 0, self)
        # ... progress 설정 ...
        # progress.show()
        # QApplication.processEvents()
        
        kiwoom_error = None
        openai_error = None
        
        # 키움증권 API 테스트
        try:
            kiwoom_api = KiwoomAPI(kiwoom_key, kiwoom_secret, is_real=True)
            # KiwoomAPI 인스턴스 생성만으로 성공 간주 (토큰 발급 시도 포함)
            self.kiwoom_connected = True
            logger.info("키움증권 API 통신 성공 (인스턴스 생성 성공)")
        except Exception as e:
            kiwoom_error = str(e)
            logger.error(f"키움증권 API 통신 실패: {e}")
        
        # OpenAI API 테스트
        try:
            openai_api = OpenAIAPI(openai_key)
            # OpenAIAPI 인스턴스 생성만으로 성공 간주
            self.openai_connected = True
            logger.info("OpenAI API 통신 성공 (인스턴스 생성 성공)")
        except Exception as e:
            openai_error = str(e)
            logger.error(f"OpenAI API 통신 실패: {e}")
        
        # progress.close()
        
        # 상태 메시지 업데이트
        if self.kiwoom_connected and self.openai_connected:
            self.status_label.setText("API 연결 상태: 모두 성공")
            self.status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: {FONT_SIZES.SMALL};")
            return True
        else:
            error_msg = "API 연결 상태: "
            if not self.kiwoom_connected: error_msg += f"키움 실패({kiwoom_error or '오류'}) "
            if not self.openai_connected: error_msg += f"OpenAI 실패({openai_error or '오류'})"
            self.status_label.setText(error_msg.strip())
            self.status_label.setStyleSheet(f"color: {Colors.ERROR}; font-size: {FONT_SIZES.SMALL};")
            return False

    def save_and_validate_keys(self):
        """API 키 저장 및 유효성 검사 (통신 포함)"""
        # 1. 통신 테스트 수행
        if not self.test_api_connection_internal():
            QMessageBox.warning(self, "통신 실패", "API 서버와 통신할 수 없습니다. 키를 확인해주세요.")
            return # 저장하지 않고 종료
            
        # 2. 통신 성공 시 키 저장
        try:
            kiwoom_key = self.kiwoom_key_edit.text().strip()
            kiwoom_secret = self.kiwoom_secret_edit.text().strip()
            openai_key = self.openai_key_edit.text().strip()
            
            # 이미 위 test_api_connection_internal 에서 빈 값 체크됨
            
            # API 키 암호화하여 저장
            settings = QSettings("GazuaTrading", "Trading")
            settings.setValue("api/kiwoom_key", encrypt_data(kiwoom_key))
            settings.setValue("api/kiwoom_secret", encrypt_data(kiwoom_secret))
            settings.setValue("api/openai_key", encrypt_data(openai_key))
            settings.sync()
            logger.info("API 키 암호화 저장 완료")
            
            # 성공 메시지 표시 (QMessageBox 대신 상태 레이블 사용)
            self.status_label.setText("통신 성공! 1.5초 후 창이 닫힙니다.")
            self.status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: {FONT_SIZES.SMALL};")
            
            # 입력 필드 및 버튼 비활성화
            self.kiwoom_key_edit.setEnabled(False)
            self.kiwoom_secret_edit.setEnabled(False)
            self.openai_key_edit.setEnabled(False)
            self.save_button.setEnabled(False)
            
            # 1.5초 후 대화상자 닫기
            QTimer.singleShot(1500, self.accept)
            
        except Exception as e:
            logger.error(f"API 키 저장 중 오류 발생: {e}", exc_info=True)
            QMessageBox.critical(self, "오류", f"API 키 저장 중 오류가 발생했습니다: {str(e)}") 