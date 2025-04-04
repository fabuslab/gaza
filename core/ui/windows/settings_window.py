"""
설정 화면 모듈
"""

import logging
import sys
import os
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QMessageBox,
    QTabWidget, QGroupBox, QFormLayout, QCheckBox,
    QSpacerItem, QSizePolicy, QProgressDialog, QApplication
)
from PySide6.QtCore import Qt, QSettings, QProcess, Slot as pyqtSlot, Signal as pyqtSignal
from PySide6.QtGui import QIcon, QCloseEvent

from core.utils.crypto import encrypt_data, decrypt_data
from core.api.kiwoom import KiwoomAPI
from core.api.openai import OpenAIAPI
from core.ui.dialogs.api_key_dialog import APIKeyDialog
from core.ui.constants.colors import Colors
from core.ui.constants.fonts import Fonts, FONT_SIZES
from core.ui.constants.rules import UI_RULES
from core.ui.stylesheets import StyleSheets

logger = logging.getLogger(__name__)

class SettingsWindow(QMainWindow):
    """설정 화면 클래스"""
    
    def __init__(self, parent=None, kiwoom_api=None, openai_api=None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setMinimumSize(600, 500)
        
        self.settings = QSettings("GazuaTrading", "Trading")
        self.kiwoom_api = kiwoom_api
        self.openai_api = openai_api
        
        self.init_ui()
        
    def init_ui(self):
        """UI 초기화"""
        central_widget = QWidget()
        central_widget.setStyleSheet(StyleSheets.WIDGET)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(StyleSheets.TAB)
        
        # API 설정 탭
        self.api_tab = QWidget()
        self.create_api_tab()
        self.tab_widget.addTab(self.api_tab, "API 설정")
        
        # 화면 설정 탭
        self.display_tab = QWidget()
        self.create_display_tab()
        self.tab_widget.addTab(self.display_tab, "화면 설정")
        
        # 기타 설정 탭
        self.etc_tab = QWidget()
        self.create_etc_tab()
        self.tab_widget.addTab(self.etc_tab, "기타 설정")
        
        main_layout.addWidget(self.tab_widget)
        
        # 버튼 레이아웃
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.reset_button = QPushButton("API 키 초기화")
        self.reset_button.setStyleSheet(StyleSheets.BUTTON_WARNING)
        self.reset_button.clicked.connect(self.confirm_reset_api_keys)
        button_layout.addWidget(self.reset_button)
        
        self.save_button = QPushButton("저장")
        self.save_button.setStyleSheet(StyleSheets.BUTTON)
        self.save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_button)
        
        self.cancel_button = QPushButton("닫기")
        self.cancel_button.setStyleSheet(StyleSheets.BUTTON_SECONDARY)
        self.cancel_button.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)
        
        self.setCentralWidget(central_widget)
        
    def create_api_tab(self):
        """API 설정 탭 생성"""
        layout = QVBoxLayout(self.api_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 키움증권 API 설정 그룹
        kiwoom_group = QGroupBox("키움증권 API 설정")
        kiwoom_group.setStyleSheet(StyleSheets.GROUP_BOX)
        kiwoom_layout = QFormLayout(kiwoom_group)
        kiwoom_layout.setContentsMargins(15, 20, 15, 15)
        kiwoom_layout.setSpacing(10)
        
        # API 키 입력
        self.kiwoom_key_edit = QLineEdit()
        self.kiwoom_key_edit.setStyleSheet(StyleSheets.INPUT)
        self.kiwoom_key_edit.setPlaceholderText("키움증권 API 키를 입력하세요")
        self.kiwoom_key_edit.setEchoMode(QLineEdit.Password)
        kiwoom_layout.addRow("API 키:", self.kiwoom_key_edit)
        
        # API 시크릿 입력
        self.kiwoom_secret_edit = QLineEdit()
        self.kiwoom_secret_edit.setStyleSheet(StyleSheets.INPUT)
        self.kiwoom_secret_edit.setPlaceholderText("키움증권 API 시크릿을 입력하세요")
        self.kiwoom_secret_edit.setEchoMode(QLineEdit.Password)
        kiwoom_layout.addRow("API 시크릿:", self.kiwoom_secret_edit)
        
        # 키움증권 API 상태
        self.kiwoom_status_label = QLabel("연결 상태: 확인 필요")
        self.kiwoom_status_label.setStyleSheet(f"color: {Colors.WARNING};")
        kiwoom_layout.addRow("상태:", self.kiwoom_status_label)
        
        # 버튼 레이아웃
        kiwoom_button_layout = QHBoxLayout()
        
        # 키움증권 API 테스트 버튼
        kiwoom_test_button = QPushButton("연결 테스트")
        kiwoom_test_button.setStyleSheet(StyleSheets.BUTTON_SECONDARY)
        kiwoom_test_button.clicked.connect(self.test_kiwoom_api)
        kiwoom_button_layout.addWidget(kiwoom_test_button)
        
        # 키움증권 토큰 재발급 버튼
        kiwoom_token_refresh_button = QPushButton("토큰 재발급")
        kiwoom_token_refresh_button.setStyleSheet(StyleSheets.BUTTON_SECONDARY)
        kiwoom_token_refresh_button.clicked.connect(self.refresh_kiwoom_token)
        kiwoom_button_layout.addWidget(kiwoom_token_refresh_button)
        
        kiwoom_layout.addRow("", kiwoom_button_layout)
        
        layout.addWidget(kiwoom_group)
        
        # OpenAI API 설정 그룹
        openai_group = QGroupBox("OpenAI API 설정")
        openai_group.setStyleSheet(StyleSheets.GROUP_BOX)
        openai_layout = QFormLayout(openai_group)
        openai_layout.setContentsMargins(15, 20, 15, 15)
        openai_layout.setSpacing(10)
        
        # API 키 입력
        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setStyleSheet(StyleSheets.INPUT)
        self.openai_key_edit.setPlaceholderText("OpenAI API 키를 입력하세요")
        self.openai_key_edit.setEchoMode(QLineEdit.Password)
        openai_layout.addRow("API 키:", self.openai_key_edit)
        
        # OpenAI API 상태
        self.openai_status_label = QLabel("연결 상태: 확인 필요")
        self.openai_status_label.setStyleSheet(f"color: {Colors.WARNING};")
        openai_layout.addRow("상태:", self.openai_status_label)
        
        # OpenAI API 테스트 버튼
        openai_test_button = QPushButton("연결 테스트")
        openai_test_button.setStyleSheet(StyleSheets.BUTTON_SECONDARY)
        openai_test_button.clicked.connect(self.test_openai_api)
        openai_layout.addRow("", openai_test_button)
        
        layout.addWidget(openai_group)
        layout.addStretch()
        
        # 현재 저장된 키 값 로드
        self.load_api_keys()
        
    def create_display_tab(self):
        """화면 설정 탭 생성"""
        layout = QVBoxLayout(self.display_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 일반 화면 설정 그룹
        display_group = QGroupBox("화면 설정")
        display_group.setStyleSheet(StyleSheets.GROUP_BOX)
        display_layout = QFormLayout(display_group)
        display_layout.setContentsMargins(15, 20, 15, 15)
        display_layout.setSpacing(10)
        
        # 항상 위에 표시 옵션
        self.always_on_top_check = QCheckBox()
        self.always_on_top_check.setChecked(
            self.settings.value("window/always_on_top", True, type=bool)
        )
        display_layout.addRow("항상 위에 표시:", self.always_on_top_check)
        
        # 시작 시 전체화면 옵션
        self.fullscreen_on_start_check = QCheckBox()
        self.fullscreen_on_start_check.setChecked(
            self.settings.value("window/fullscreen_on_start", False, type=bool)
        )
        display_layout.addRow("시작 시 전체화면:", self.fullscreen_on_start_check)
        
        layout.addWidget(display_group)
        layout.addStretch()
        
    def create_etc_tab(self):
        """기타 설정 탭 생성"""
        layout = QVBoxLayout(self.etc_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 시스템 설정 그룹
        system_group = QGroupBox("시스템 설정")
        system_group.setStyleSheet(StyleSheets.GROUP_BOX)
        system_layout = QFormLayout(system_group)
        system_layout.setContentsMargins(15, 20, 15, 15)
        system_layout.setSpacing(10)
        
        # 자동 업데이트 확인 옵션
        self.auto_update_check = QCheckBox()
        self.auto_update_check.setChecked(
            self.settings.value("system/auto_update", True, type=bool)
        )
        system_layout.addRow("자동 업데이트 확인:", self.auto_update_check)
        
        # 로그 보존 기간 옵션
        self.log_retention_edit = QLineEdit()
        self.log_retention_edit.setStyleSheet(StyleSheets.INPUT)
        self.log_retention_edit.setText(
            str(self.settings.value("system/log_retention_days", "30"))
        )
        system_layout.addRow("로그 보존 기간(일):", self.log_retention_edit)
        
        layout.addWidget(system_group)
        layout.addStretch()
        
    def load_api_keys(self):
        """저장된 API 키 로드"""
        try:
            # 키움증권 API 키 로드
            kiwoom_key = self.settings.value("api/kiwoom_key", "")
            kiwoom_secret = self.settings.value("api/kiwoom_secret", "")
            
            # OpenAI API 키 로드
            openai_key = self.settings.value("api/openai_key", "")
            
            # 키가 저장되어 있으면 마스킹 표시로 보여줌
            if kiwoom_key:
                self.kiwoom_key_edit.setText("●●●●●●●●●●●●")
                self.kiwoom_status_label.setText("연결 상태: 키 저장됨")
            
            if kiwoom_secret:
                self.kiwoom_secret_edit.setText("●●●●●●●●●●●●")
            
            if openai_key:
                self.openai_key_edit.setText("●●●●●●●●●●●●")
                self.openai_status_label.setText("연결 상태: 키 저장됨")
            
            # API 인스턴스가 있으면 상태 업데이트
            if self.kiwoom_api:
                self.kiwoom_status_label.setText("연결 상태: 연결됨")
                self.kiwoom_status_label.setStyleSheet(f"color: {Colors.SUCCESS};")
            
            if self.openai_api:
                self.openai_status_label.setText("연결 상태: 연결됨")
                self.openai_status_label.setStyleSheet(f"color: {Colors.SUCCESS};")
                
        except Exception as e:
            logger.error(f"API 키 로드 실패: {e}")
            QMessageBox.warning(self, "로드 오류", f"설정 로드 중 오류가 발생했습니다: {str(e)}")
    
    def test_kiwoom_api(self):
        """키움증권 API 연결 테스트"""
        key = self.kiwoom_key_edit.text().strip()
        secret = self.kiwoom_secret_edit.text().strip()
        
        # 마스킹된 값이면 저장된 값 사용
        if key == "●●●●●●●●●●●●":
            key = decrypt_data(self.settings.value("api/kiwoom_key", ""))
        
        if secret == "●●●●●●●●●●●●":
            secret = decrypt_data(self.settings.value("api/kiwoom_secret", ""))
        
        if not key or not secret:
            QMessageBox.warning(self, "입력 오류", "API 키와 시크릿을 모두 입력해주세요.")
            return
        
        # 테스트 진행 중 메시지
        progress = QProgressDialog("API 연결 테스트 중...", None, 0, 0, self)
        progress.setWindowTitle("연결 테스트")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        QApplication.processEvents()
        
        try:
            # API 연결 테스트
            test_api = KiwoomAPI(key, secret, is_real=True)
            
            # 성공 메시지
            self.kiwoom_status_label.setText("연결 상태: 연결 성공")
            self.kiwoom_status_label.setStyleSheet(f"color: {Colors.SUCCESS};")
            progress.close()
            QMessageBox.information(self, "테스트 성공", "키움증권 API 연결에 성공했습니다.")
            
        except Exception as e:
            # 실패 메시지
            logger.error(f"키움증권 API 테스트 실패: {e}")
            self.kiwoom_status_label.setText("연결 상태: 연결 실패")
            self.kiwoom_status_label.setStyleSheet(f"color: {Colors.ERROR};")
            progress.close()
            QMessageBox.critical(self, "테스트 실패", f"키움증권 API 연결에 실패했습니다: {str(e)}")
    
    def test_openai_api(self):
        """OpenAI API 연결 테스트"""
        key = self.openai_key_edit.text().strip()
        
        # 마스킹된 값이면 저장된 값 사용
        if key == "●●●●●●●●●●●●":
            key = decrypt_data(self.settings.value("api/openai_key", ""))
        
        if not key:
            QMessageBox.warning(self, "입력 오류", "API 키를 입력해주세요.")
            return
        
        # 테스트 진행 중 메시지
        progress = QProgressDialog("API 연결 테스트 중...", None, 0, 0, self)
        progress.setWindowTitle("연결 테스트")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        QApplication.processEvents()
        
        try:
            # API 연결 테스트
            test_api = OpenAIAPI(key)
            
            # 성공 메시지
            self.openai_status_label.setText("연결 상태: 연결 성공")
            self.openai_status_label.setStyleSheet(f"color: {Colors.SUCCESS};")
            progress.close()
            QMessageBox.information(self, "테스트 성공", "OpenAI API 연결에 성공했습니다.")
            
        except Exception as e:
            # 실패 메시지
            logger.error(f"OpenAI API 테스트 실패: {e}")
            self.openai_status_label.setText("연결 상태: 연결 실패")
            self.openai_status_label.setStyleSheet(f"color: {Colors.ERROR};")
            progress.close()
            QMessageBox.critical(self, "테스트 실패", f"OpenAI API 연결에 실패했습니다: {str(e)}")
    
    def save_settings(self):
        """설정 저장"""
        try:
            # API 설정 저장
            kiwoom_key = self.kiwoom_key_edit.text().strip()
            kiwoom_secret = self.kiwoom_secret_edit.text().strip()
            openai_key = self.openai_key_edit.text().strip()
            
            # 마스킹된 값이 아닌 경우에만 저장
            if kiwoom_key and kiwoom_key != "●●●●●●●●●●●●":
                self.settings.setValue("api/kiwoom_key", encrypt_data(kiwoom_key))
            
            if kiwoom_secret and kiwoom_secret != "●●●●●●●●●●●●":
                self.settings.setValue("api/kiwoom_secret", encrypt_data(kiwoom_secret))
            
            if openai_key and openai_key != "●●●●●●●●●●●●":
                self.settings.setValue("api/openai_key", encrypt_data(openai_key))
            
            # 화면 설정 저장
            self.settings.setValue("window/always_on_top", self.always_on_top_check.isChecked())
            self.settings.setValue("window/fullscreen_on_start", self.fullscreen_on_start_check.isChecked())
            
            # 기타 설정 저장
            self.settings.setValue("system/auto_update", self.auto_update_check.isChecked())
            self.settings.setValue("system/log_retention_days", self.log_retention_edit.text())
            
            self.settings.sync()
            
            QMessageBox.information(self, "저장 완료", "설정이 저장되었습니다.")
            
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")
            QMessageBox.critical(self, "저장 실패", f"설정 저장 중 오류가 발생했습니다: {str(e)}")
    
    def confirm_reset_api_keys(self):
        """API 키 초기화 확인"""
        result = QMessageBox.question(
            self,
            "API 키 초기화",
            "초기화를 하면 등록된 키값이 모두 삭제되고 프로그램이 종료됩니다. 정말 초기화 하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            self.reset_api_keys()
    
    def reset_api_keys(self):
        """API 키 초기화 및 프로그램 재시작"""
        try:
            # API 키 설정 삭제
            self.settings.remove("api/kiwoom_key")
            self.settings.remove("api/kiwoom_secret")
            self.settings.remove("api/openai_key")
            self.settings.sync()
            
            QMessageBox.information(
                self,
                "초기화 완료",
                "API 키가 초기화되었습니다. 프로그램이 재시작됩니다."
            )
            
            # 프로그램 재시작
            QProcess.startDetached(sys.executable, sys.argv)
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"API 키 초기화 실패: {e}")
            QMessageBox.critical(
                self,
                "초기화 실패",
                f"API 키 초기화 중 오류가 발생했습니다: {str(e)}"
            )
    
    def refresh_kiwoom_token(self):
        """키움증권 토큰 재발급"""
        result = QMessageBox.question(
            self,
            "토큰 재발급",
            "키움증권 API 토큰을 재발급하시겠습니까?\n이전 토큰은 폐기됩니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result != QMessageBox.Yes:
            return
            
        key = self.kiwoom_key_edit.text().strip()
        secret = self.kiwoom_secret_edit.text().strip()
        
        # 마스킹된 값이면 저장된 값 사용
        if key == "●●●●●●●●●●●●":
            key = decrypt_data(self.settings.value("api/kiwoom_key", ""))
        
        if secret == "●●●●●●●●●●●●":
            secret = decrypt_data(self.settings.value("api/kiwoom_secret", ""))
        
        if not key or not secret:
            QMessageBox.warning(self, "입력 오류", "API 키와 시크릿을 모두 입력해주세요.")
            return
        
        # 테스트 진행 중 메시지
        progress = QProgressDialog("API 토큰 처리 중...", None, 0, 0, self)
        progress.setWindowTitle("토큰 재발급")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        QApplication.processEvents()
        
        try:
            # 1. 기존 토큰 폐기
            is_real = self.settings.value("api/is_real", True, type=bool)
            
            # 현재 API 인스턴스가 있으면 기존 토큰 폐기
            if self.kiwoom_api and self.kiwoom_api.access_token:
                logger.info("기존 토큰 폐기 시작")
                progress.setLabelText("기존 토큰 폐기 중...")
                QApplication.processEvents()
                
                revoke_result = self.kiwoom_api.revoke_token()
                if revoke_result:
                    logger.info("기존 토큰 폐기 성공")
                else:
                    logger.warning("기존 토큰 폐기 실패, 새 토큰 발급 계속 진행")
            
            # 2. 새 API 인스턴스 생성
            progress.setLabelText("새 토큰 발급 중...")
            QApplication.processEvents()
            
            new_api = KiwoomAPI(key, secret, is_real=is_real)
            
            # 3. 새 토큰 발급 강제 시도
            new_api._get_access_token()
            
            # 4. 성공 메시지
            self.kiwoom_status_label.setText("연결 상태: 토큰 재발급 성공")
            self.kiwoom_status_label.setStyleSheet(f"color: {Colors.SUCCESS};")
            progress.close()
            QMessageBox.information(self, "토큰 재발급 성공", "키움증권 API 토큰이 재발급되었습니다.")
            
            # 5. API 인스턴스 갱신
            if hasattr(self.parent(), "kiwoom_api"):
                self.parent().kiwoom_api = new_api
                self.kiwoom_api = new_api
            
        except Exception as e:
            # 실패 메시지
            logger.error(f"키움증권 API 토큰 재발급 실패: {e}")
            self.kiwoom_status_label.setText("연결 상태: 토큰 재발급 실패")
            self.kiwoom_status_label.setStyleSheet(f"color: {Colors.ERROR};")
            progress.close()
            QMessageBox.critical(self, "토큰 재발급 실패", f"키움증권 API 토큰 재발급에 실패했습니다: {str(e)}")
    
    def closeEvent(self, event: QCloseEvent):
        """창 닫기 이벤트 처리"""
        event.accept() 