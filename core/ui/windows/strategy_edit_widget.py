"""
매매 전략 생성/수정 위젯
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFrame, 
    QTextEdit, QComboBox, QLineEdit, 
    QSplitter, QFileDialog, QListWidget, QProgressBar, QMessageBox, QScrollArea # 추가
)
from PySide6.QtCore import Qt, Slot as pyqtSlot, Signal as pyqtSignal, QThread, QSettings # QThread 추가, QSettings 추가

from core.strategy.repository import StrategyRepository
from core.strategy.base import AIStrategy
from core.api.openai import OpenAIAPI
from core.ui.constants.colors import Colors
from core.ui.constants.fonts import Fonts, FONT_SIZES
from core.ui.constants.rules import UI_RULES
from core.ui.stylesheets import StyleSheets
from ..components.learning_result_item import LearningResultItemWidget
from core.trading.executor import ORDER_TYPE_MAP

import os
import base64 # 이미지 인코딩 위해 추가
import fitz # PyMuPDF
import difflib # 텍스트 비교 위해 추가
import logging

logger = logging.getLogger(__name__)

# --- AI 분석 백그라운드 워커 --- #
class AIAnalysisWorker(QThread):
    """ AI 분석을 백그라운드에서 처리하는 스레드 """
    analysis_complete = pyqtSignal(str) # 분석 완료 시 결과 텍스트 전달
    analysis_error = pyqtSignal(str) # 오류 발생 시 메시지 전달
    progress_update = pyqtSignal(str, int) # 진행 상황 업데이트 (메시지, 진행률%)

    def __init__(self, api: OpenAIAPI, text: str, files: list, parent=None):
        super().__init__(parent)
        self.api = api
        self.text_prompt = text
        self.file_paths = files
        self.max_pages_per_pdf = 200 # PDF 페이지 제한

    def run(self):
        """스레드 실행 로직"""
        try:
            self.progress_update.emit("이미지 데이터 준비 중...", 10)
            image_data_list = self._prepare_image_data()
            if not image_data_list and not self.text_prompt:
                self.analysis_error.emit("분석할 텍스트나 파일이 없습니다.")
                return
                
            self.progress_update.emit("AI 분석 요청 중...", 50)
            
            # --- 실제 OpenAI API 호출 --- #
            base_prompt = self.text_prompt
            image_data_list = self.file_paths
            
            # --- 주문 유형 정보 프롬프트 추가 --- 
            prompt_with_order_types = base_prompt + "\n\n--- 사용 가능한 주문 유형 ---\n"
            for code, name in ORDER_TYPE_MAP.items():
                 prompt_with_order_types += f"- {code}: {name}\n"
            prompt_with_order_types += "\n분석 결과나 매수/매도 조건 제안 시, 위에 제시된 주문 유형 코드(예: '00' 또는 '03')를 구체적으로 명시하여 답변해주세요."
            # --- 여기까지 추가 ---

            result = self.api.analyze_strategy_with_vision(
                prompt=prompt_with_order_types,
                image_data=image_data_list
            )
            # -------------------------- #

            self.progress_update.emit("분석 완료", 100)
            self.analysis_complete.emit(result)

        except Exception as e:
            import traceback
            error_msg = f"AI 분석 중 오류 발생: {e}\n{traceback.format_exc()}"
            self.analysis_error.emit(error_msg)
            
    def _prepare_image_data(self) -> list:
        """첨부 파일들을 base64 인코딩된 이미지 데이터 리스트로 변환"""
        image_data = []
        total_files = len(self.file_paths)
        if not total_files:
            return image_data
            
        for i, file_path in enumerate(self.file_paths):
            filename = os.path.basename(file_path)
            progress = 10 + int(40 * (i + 1) / total_files)
            self.progress_update.emit(f"파일 처리 중: {filename}", progress)
            
            _, ext = os.path.splitext(filename.lower())
            if ext == '.pdf':
                try:
                    doc = fitz.open(file_path)
                    page_count = 0
                    num_pages_in_doc = len(doc)
                    for page_num in range(min(num_pages_in_doc, self.max_pages_per_pdf)):
                        page_progress = progress + int( (1 / num_pages_in_doc) * (40 / total_files) * (page_num + 1) )
                        self.progress_update.emit(f"PDF 페이지 처리 중 ({page_num+1}/{num_pages_in_doc}): {filename}", page_progress)
                        
                        page = doc.load_page(page_num)
                        pix = page.get_pixmap()
                        img_bytes = pix.tobytes("png")
                        base64_image = base64.b64encode(img_bytes).decode('utf-8')
                        image_data.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}})
                        page_count += 1
                    doc.close()
                    if num_pages_in_doc > self.max_pages_per_pdf:
                         print(f"경고: PDF '{filename}'의 페이지 수가 {self.max_pages_per_pdf}개를 초과하여 일부만 처리합니다.")
                except Exception as e:
                     print(f"오류: PDF 파일 '{filename}' 처리 중 오류: {e}")
            elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
                try:
                    with open(file_path, "rb") as image_file:
                        img_bytes = image_file.read()
                        base64_image = base64.b64encode(img_bytes).decode('utf-8')
                        mime_type = f"image/{ext[1:]}" if ext != '.jpg' else 'image/jpeg'
                        image_data.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}})
                except Exception as e:
                    print(f"오류: 이미지 파일 '{filename}' 처리 중 오류: {e}")
            else:
                print(f"경고: 지원하지 않는 파일 형식입니다: {filename}")
                
        return image_data

# --- StrategyEditWidget 클래스 --- #
class StrategyEditWidget(QWidget):
    """전략 생성 및 수정을 위한 위젯"""

    view_list_requested = pyqtSignal()
    strategy_saved = pyqtSignal(str)

    def __init__(self, api: OpenAIAPI, parent=None):
        super().__init__(parent)
        self.api = api
        self.repository = StrategyRepository()
        self.current_strategy_name = None
        
        # 마지막 사용 디렉토리 설정에서 가져오기
        settings = QSettings("GazuaTrading", "Trading")
        self.last_dir = settings.value("attachments/last_dir", os.path.expanduser("~"))
        
        self.attached_files = []
        self.init_ui()

    def init_ui(self):
        """UI 초기화 - 상세 요소 배치"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(int(UI_RULES.MARGIN_LARGE.replace('px','')), 
                                         int(UI_RULES.MARGIN_LARGE.replace('px','')), 
                                         int(UI_RULES.MARGIN_LARGE.replace('px','')), 
                                         int(UI_RULES.MARGIN_LARGE.replace('px','')))
        main_layout.setSpacing(int(UI_RULES.MARGIN_NORMAL.replace('px','')))

        # 1. 상단 버튼 영역
        top_bar_layout = QHBoxLayout()
        self.back_button = QPushButton("← 뒤로가기") # 멤버 변수로 저장
        self.back_button.setStyleSheet(StyleSheets.BUTTON)
        self.back_button.clicked.connect(self.view_list_requested.emit)
        top_bar_layout.addWidget(self.back_button)
        top_bar_layout.addStretch(1)
        self.save_button = QPushButton("저장") # 멤버 변수로 저장
        self.save_button.setStyleSheet(StyleSheets.BUTTON_PRIMARY)
        self.save_button.clicked.connect(self.save_strategy)
        top_bar_layout.addWidget(self.save_button)
        main_layout.addLayout(top_bar_layout)

        # 2. 타이틀 및 AI 설정 영역
        title_ai_layout = QVBoxLayout()
        title_ai_layout.setSpacing(int(UI_RULES.MARGIN_SMALL.replace('px','')))
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("매매 전략 타이틀 입력...")
        self.title_input.setStyleSheet(StyleSheets.LINE_EDIT + f" font-size: {FONT_SIZES.LARGE};")
        title_ai_layout.addWidget(self.title_input)

        ai_config_layout = QHBoxLayout()
        self.ai_model_combo = QComboBox()
        self.ai_model_combo.addItem("GPT-4o")
        self.ai_model_combo.setEnabled(False)
        self.ai_model_combo.setStyleSheet(StyleSheets.COMBO_BOX)
        ai_config_layout.addWidget(QLabel("AI 모델:"))
        ai_config_layout.addWidget(self.ai_model_combo)
        
        self.ai_interval_combo = QComboBox()
        intervals = ["1초", "5초", "10초", "30초", "60초", "3분", "5분", "10분", "20분", "30분", "1시간", "2시간"]
        self.ai_interval_combo.addItems(intervals)
        self.ai_interval_combo.setStyleSheet(StyleSheets.COMBO_BOX)
        ai_config_layout.addWidget(QLabel("    AI 모델 요청 주기:"))
        ai_config_layout.addWidget(self.ai_interval_combo)
        ai_config_layout.addStretch(1)
        title_ai_layout.addLayout(ai_config_layout)
        main_layout.addLayout(title_ai_layout)

        # 3. 메인 영역 (스플리터 사용)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(StyleSheets.SPLITTER)

        # 3-1. 왼쪽: 투자 전략 섹션
        left_widget = QFrame()
        left_widget.setStyleSheet(StyleSheets.FRAME)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(int(UI_RULES.PADDING_NORMAL.replace('px','')),0,int(UI_RULES.PADDING_NORMAL.replace('px','')),0)
        left_layout.setSpacing(int(UI_RULES.MARGIN_NORMAL.replace('px','')))
        
        left_title = QLabel("투자 전략")
        left_title.setStyleSheet(StyleSheets.SUBTITLE)
        left_layout.addWidget(left_title)
        
        self.strategy_text_area = QTextEdit()
        self.strategy_text_area.setPlaceholderText("여기에 투자 전략을 입력하거나 AI 분석 결과를 붙여넣으세요...")
        self.strategy_text_area.setStyleSheet(StyleSheets.TEXT_EDIT)
        left_layout.addWidget(self.strategy_text_area, 3)

        # 파일 첨부 영역
        file_controls_layout = QHBoxLayout()
        self.file_attach_button = QPushButton("파일 첨부 (PDF, 이미지)") # 멤버 변수
        self.file_attach_button.setStyleSheet(StyleSheets.BUTTON)
        self.file_attach_button.clicked.connect(self.attach_file)
        file_controls_layout.addWidget(self.file_attach_button)
        
        self.file_delete_button = QPushButton("첨부 파일 삭제")
        self.file_delete_button.setStyleSheet(StyleSheets.BUTTON_DANGER_SMALL)
        self.file_delete_button.clicked.connect(self.delete_attached_file)
        self.file_delete_button.setEnabled(False)
        file_controls_layout.addWidget(self.file_delete_button)
        file_controls_layout.addStretch(1)
        left_layout.addLayout(file_controls_layout)

        self.attached_files_list = QListWidget()
        self.attached_files_list.setStyleSheet(StyleSheets.LIST_WIDGET + " min-height: 60px; max-height: 120px;")
        self.attached_files_list.itemSelectionChanged.connect(self.update_delete_button_state)
        left_layout.addWidget(self.attached_files_list, 1)

        # AI 학습 결과 영역
        ai_learning_title = QLabel("AI 학습 결과")
        ai_learning_title.setStyleSheet(StyleSheets.SUBTITLE)
        left_layout.addWidget(ai_learning_title)
        
        self.learning_scroll_area = QScrollArea()
        self.learning_scroll_area.setWidgetResizable(True)
        self.learning_scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        learning_content_widget = QWidget()
        self.learning_layout = QVBoxLayout(learning_content_widget)
        self.learning_layout.setContentsMargins(0,0,0,0)
        self.learning_layout.setSpacing(int(UI_RULES.MARGIN_XSMALL.replace('px','')))
        self.learning_layout.setAlignment(Qt.AlignTop)
        
        self.learning_scroll_area.setWidget(learning_content_widget)
        left_layout.addWidget(self.learning_scroll_area, 2)

        splitter.addWidget(left_widget)

        # 3-2. 중간: 버튼 열
        button_column = QFrame()
        button_column_layout = QVBoxLayout(button_column)
        button_column_layout.setContentsMargins(int(UI_RULES.MARGIN_SMALL.replace('px','')), 0, int(UI_RULES.MARGIN_SMALL.replace('px','')), 0)
        button_column_layout.setSpacing(int(UI_RULES.MARGIN_NORMAL.replace('px','')))
        button_column_layout.setAlignment(Qt.AlignCenter)
        
        self.ai_analyze_button = QPushButton("AI 분석 >") # 멤버 변수
        self.ai_analyze_button.setStyleSheet(StyleSheets.BUTTON)
        self.ai_analyze_button.clicked.connect(self.run_ai_analysis)
        button_column_layout.addWidget(self.ai_analyze_button)
        
        self.paste_button = QPushButton("< 붙여넣기") # 멤버 변수
        self.paste_button.setStyleSheet(StyleSheets.BUTTON)
        self.paste_button.clicked.connect(self.paste_ai_result)
        button_column_layout.addWidget(self.paste_button)
        
        self.overwrite_button = QPushButton("< 덮어쓰기") # 멤버 변수
        self.overwrite_button.setStyleSheet(StyleSheets.BUTTON)
        self.overwrite_button.clicked.connect(self.overwrite_with_ai_result)
        button_column_layout.addWidget(self.overwrite_button)
        button_column_layout.addStretch(1)

        splitter.addWidget(button_column)

        # 3-3. 오른쪽: AI 분석 결과 섹션
        right_widget = QFrame()
        right_widget.setStyleSheet(StyleSheets.FRAME)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(int(UI_RULES.PADDING_NORMAL.replace('px','')),0,int(UI_RULES.PADDING_NORMAL.replace('px','')),0)
        right_layout.setSpacing(int(UI_RULES.MARGIN_NORMAL.replace('px','')))

        right_title = QLabel("AI 분석 결과")
        right_title.setStyleSheet(StyleSheets.SUBTITLE)
        right_layout.addWidget(right_title)
        
        self.ai_result_text_area = QTextEdit()
        self.ai_result_text_area.setReadOnly(True)
        self.ai_result_text_area.setStyleSheet(StyleSheets.TEXT_EDIT_READONLY)
        right_layout.addWidget(self.ai_result_text_area)

        splitter.addWidget(right_widget)

        splitter.setSizes([550, 50, 400])
        main_layout.addWidget(splitter, 1)

        # 4. 프로그레스 바 (초기 숨김)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(StyleSheets.PROGRESSBAR)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 0)
        main_layout.addWidget(self.progress_bar)
        
        self.setLayout(main_layout)

    def attach_file(self):
        """파일 첨부 기능"""
        try:
            import fitz
        except ImportError:
            QMessageBox.warning(self, "오류", "PDF 처리를 위한 PyMuPDF 라이브러리가 설치되지 않았습니다.\n`pip install PyMuPDF` 명령어로 설치해주세요.")
            return

        # QSettings에서 마지막 사용 디렉토리 가져오기
        settings = QSettings("GazuaTrading", "Trading")
        last_dir = settings.value("attachments/last_dir", os.path.expanduser("~"))
        
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "파일 첨부",
            last_dir,
            "지원 파일 (*.pdf *.png *.jpg *.jpeg *.bmp *.gif)" 
        )

        if file_paths:
            # 마지막 사용 디렉토리 저장
            new_last_dir = os.path.dirname(file_paths[0])
            settings.setValue("attachments/last_dir", new_last_dir)
            self.last_dir = new_last_dir
            
            for file_path in file_paths:
                if file_path not in self.attached_files:
                    self.attached_files.append(file_path)
                    self.attached_files_list.addItem(os.path.basename(file_path))
            print(f"첨부된 파일: {self.attached_files}")

    def delete_attached_file(self):
        """선택된 첨부 파일 삭제"""
        selected_items = self.attached_files_list.selectedItems()
        if not selected_items:
            return

        item_to_delete = selected_items[0]
        file_basename = item_to_delete.text()
        
        file_path_to_delete = None
        for f_path in self.attached_files:
            if os.path.basename(f_path) == file_basename:
                file_path_to_delete = f_path
                break
                
        if file_path_to_delete:
            try:
                self.attached_files.remove(file_path_to_delete)
                row = self.attached_files_list.row(item_to_delete)
                self.attached_files_list.takeItem(row)
                print(f"첨부 파일 삭제: {file_path_to_delete}")
            except ValueError:
                print(f"오류: 리스트에서 파일을 찾을 수 없습니다 - {file_path_to_delete}")
        else:
            print(f"오류: 삭제할 파일 경로를 찾지 못했습니다 - {file_basename}")
            
        self.update_delete_button_state()

    def update_delete_button_state(self):
        """첨부 파일 목록 선택 상태에 따라 삭제 버튼 활성화/비활성화"""
        self.file_delete_button.setEnabled(len(self.attached_files_list.selectedItems()) > 0)

    def run_ai_analysis(self):
        """AI 분석 실행 (백그라운드 스레드 사용)"""
        strategy_text = self.strategy_text_area.toPlainText()
        attached_files = list(self.attached_files)

        if not strategy_text and not attached_files:
            QMessageBox.warning(self, "분석 불가", "분석할 투자 전략 텍스트나 첨부 파일이 없습니다.")
            return

        if hasattr(self, 'analysis_worker') and self.analysis_worker.isRunning():
            print("이전 AI 분석 작업이 실행 중입니다. 새 분석을 시작합니다.")

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("AI 분석 시작...")
        self.progress_bar.setVisible(True)
        self.set_buttons_enabled(False)

        self.analysis_worker = AIAnalysisWorker(self.api, strategy_text, attached_files)
        self.analysis_worker.analysis_complete.connect(self.on_analysis_complete)
        self.analysis_worker.analysis_error.connect(self.on_analysis_error)
        self.analysis_worker.progress_update.connect(self.update_progress)
        self.analysis_worker.finished.connect(self.on_analysis_finished)
        self.analysis_worker.start()

    def update_progress(self, message: str, value: int):
        """프로그레스 바 업데이트 슬롯"""
        self.progress_bar.setFormat(f"{message} ({value}%)")
        self.progress_bar.setValue(value)

    def on_analysis_complete(self, result: str):
        """AI 분석 완료 슬롯"""
        self.ai_result_text_area.setPlainText(result)
        QMessageBox.information(self, "분석 완료", "AI 분석이 완료되었습니다.")

    def on_analysis_error(self, error_message: str):
        """AI 분석 오류 슬롯"""
        print("AI 분석 오류: " + error_message)
        QMessageBox.critical(self, "분석 오류", f"AI 분석 중 오류가 발생했습니다.\n{error_message.splitlines()[0]}")

    def on_analysis_finished(self):
        """AI 분석 스레드 종료 슬롯"""
        self.progress_bar.setVisible(False)
        self.set_buttons_enabled(True)
        print("AI 분석 스레드 종료됨")
        
    def set_buttons_enabled(self, enabled: bool):
        """분석 중 버튼 활성화/비활성화"""
        # init_ui에서 버튼들을 self 멤버로 만들어서 접근 가능하게 함
        self.back_button.setEnabled(enabled)
        self.save_button.setEnabled(enabled)
        self.file_attach_button.setEnabled(enabled)
        self.file_delete_button.setEnabled(enabled and len(self.attached_files_list.selectedItems()) > 0) # 선택된 항목 있을때만 활성화
        self.ai_analyze_button.setEnabled(enabled)
        self.paste_button.setEnabled(enabled)
        self.overwrite_button.setEnabled(enabled)
        # TODO: 학습 결과 목록의 버튼들도 제어 필요

    def paste_ai_result(self):
        """AI 분석 결과 붙여넣기"""
        ai_result = self.ai_result_text_area.toPlainText()
        if ai_result:
            current_text = self.strategy_text_area.toPlainText()
            self.strategy_text_area.setPlainText(current_text + "\n\n--- AI 분석 결과 ---\n" + ai_result)
        else:
             QMessageBox.information(self, "알림", "붙여넣을 AI 분석 결과가 없습니다.")
             
    def overwrite_with_ai_result(self):
        """AI 분석 결과로 덮어쓰기"""
        ai_result = self.ai_result_text_area.toPlainText()
        if ai_result:
             reply = QMessageBox.question(self, "덮어쓰기 확인", 
                                        "기존 투자 전략 내용을 AI 분석 결과로 덮어쓰시겠습니까?",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
             if reply == QMessageBox.Yes:
                 self.strategy_text_area.setPlainText(ai_result)
        else:
             QMessageBox.information(self, "알림", "덮어쓸 AI 분석 결과가 없습니다.")

    def apply_learning_result(self, content: str):
        """학습 결과 내용을 현재 전략 텍스트에 반영 (추가된 라인 빨간색 강조 - difflib 사용)"""
        current_text = self.strategy_text_area.toPlainText()
        current_lines = current_text.splitlines()
        learned_lines = content.splitlines()
        
        diff = difflib.unified_diff(current_lines, learned_lines, lineterm='\n', n=0)
        
        merged_html = ""
        has_changes = False

        try:
            next(diff)
            next(diff)
        except StopIteration:
            pass
            
        for line in diff:
            has_changes = True
            if line.startswith('+'):
                escaped_line = line[1:].replace('<', '&lt;').replace('>', '&gt;')
                merged_html += f'<font color="{Colors.DANGER}">{escaped_line}</font><br>'
            elif line.startswith('-'):
                pass 
            elif line.startswith(' '):
                 escaped_line = line[1:].replace('<', '&lt;').replace('>', '&gt;')
                 merged_html += f'{escaped_line}<br>'
            
        if has_changes:
             reply = QMessageBox.question(self, "학습 결과 반영",
                                          "학습 결과를 반영하시겠습니까? (추가된 라인이 빨간색으로 표시됩니다. 기존 내용은 새 내용으로 대체됩니다.)",
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
             if reply == QMessageBox.Yes:
                 self.strategy_text_area.setHtml(merged_html) 
                 QMessageBox.information(self, "반영 완료", "학습 결과가 반영되었습니다.")
             else:
                 QMessageBox.information(self, "반영 취소", "학습 결과 반영이 취소되었습니다.")
                 
        else:
             QMessageBox.information(self, "변경 없음", "기존 전략과 학습 결과 내용이 동일합니다.")

    def delete_learning_result(self, result_id: str):
        """학습 결과 삭제 (데이터 및 UI)"""
        reply = QMessageBox.question(self, "학습 결과 삭제",
                                     f"'{result_id}' 학습 결과를 삭제하시겠습니까?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            print(f"TODO: 데이터에서 학습 결과 '{result_id}' 삭제")
            
            for i in range(self.learning_layout.count()):
                widget = self.learning_layout.itemAt(i).widget()
                if isinstance(widget, LearningResultItemWidget) and widget.result_id == result_id:
                    widget.deleteLater()
                    print(f"UI에서 학습 결과 '{result_id}' 위젯 제거")
                    break

    def load_strategy(self, strategy_name: str = None):
        """전략 데이터 로드 또는 UI 초기화"""
        self.current_strategy_name = strategy_name
        self.attached_files.clear()
        self.attached_files_list.clear()
        self.ai_result_text_area.clear()
        
        while self.learning_layout.count():
             item = self.learning_layout.takeAt(0)
             widget = item.widget()
             if widget: widget.deleteLater()

        if strategy_name:
            strategy = self.repository.load(strategy_name)
            if strategy:
                self.title_input.setText(strategy.name)
                self.strategy_text_area.setPlainText(strategy.description)
                self.attached_files = strategy.params.get('attached_files', [])
                for f_path in self.attached_files:
                     self.attached_files_list.addItem(os.path.basename(f_path))
                print(f"로드된 전략: {strategy_name}, 첨부파일: {len(self.attached_files)}개")
                
                learning_results = strategy.params.get('learning_results', [])
                print(f"로드된 학습 결과 수: {len(learning_results)}")
                for result_data in learning_results:
                    item_widget = LearningResultItemWidget(
                        result_id=result_data.get('id', 'N/A'),
                        title=result_data.get('title', '제목 없음'),
                        timestamp=result_data.get('timestamp', ''),
                        content=result_data.get('content', '')
                    )
                    item_widget.apply_requested.connect(self.apply_learning_result)
                    item_widget.delete_requested.connect(self.delete_learning_result)
                    self.learning_layout.addWidget(item_widget)
            else:
                 QMessageBox.critical(self, "오류", f"전략 '{strategy_name}'을(를) 로드하는 중 오류가 발생했습니다.")
                 self.view_list_requested.emit()
        else:
            self.title_input.clear()
            self.strategy_text_area.clear()
            self.ai_model_combo.setCurrentIndex(0)
            self.ai_interval_combo.setCurrentIndex(2)
            print("새 전략 생성 모드")
            
    def save_strategy(self):
        """현재 UI 내용을 기반으로 전략 저장"""
        new_name = self.title_input.text().strip()
        description = self.strategy_text_area.toPlainText()
        
        if not new_name:
            QMessageBox.warning(self, "입력 오류", "전략 타이틀을 입력해주세요.")
            self.title_input.setFocus()
            return

        if self.current_strategy_name and self.current_strategy_name != new_name:
            if not self.repository.delete(self.current_strategy_name):
                 print(f"경고: 이전 전략 파일 '{self.current_strategy_name}' 삭제 실패")
        
        params = {
            'ai_model': self.ai_model_combo.currentText(),
            'ai_interval': self.ai_interval_combo.currentText(),
            'attached_files': self.attached_files,
            # 'learning_results': self._collect_learning_results() # 저장 로직 필요
        }
        if self.current_strategy_name:
            old_strategy = self.repository.load(self.current_strategy_name)
            if old_strategy and old_strategy.params:
                 merged_params = old_strategy.params.copy()
                 # learning_results는 UI에서 수집해야 하므로 병합 시 주의
                 current_learning_results = self._collect_learning_results() 
                 merged_params.update(params)
                 merged_params['learning_results'] = current_learning_results # 수집한 결과로 덮어쓰기
                 params = merged_params
            else: # 이전 전략 로드 실패 시 learning_results만 추가
                 params['learning_results'] = self._collect_learning_results()
        else: # 새 전략 생성 시
            params['learning_results'] = self._collect_learning_results()

        strategy = AIStrategy(name=new_name, description=description, rules=[], params=params)
        
        if self.repository.save(strategy):
            QMessageBox.information(self, "저장 완료", f"전략 '{new_name}'이(가) 성공적으로 저장되었습니다.")
            self.strategy_saved.emit(new_name)
            self.view_list_requested.emit()
        else:
            QMessageBox.critical(self, "저장 실패", f"전략 '{new_name}'을(를) 저장하는 중 오류가 발생했습니다.")

    def _collect_learning_results(self):
        """현재 UI의 학습 결과 위젯에서 데이터를 수집"""
        results = []
        for i in range(self.learning_layout.count()):
            widget = self.learning_layout.itemAt(i).widget()
            if isinstance(widget, LearningResultItemWidget):
                results.append({
                    'id': widget.result_id,
                    'title': widget.title_text,
                    'timestamp': widget.timestamp_text,
                    'content': widget.content_text
                })
        return results
