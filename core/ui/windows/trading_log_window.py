import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, 
    QDateEdit, QMdiSubWindow, QTextEdit, QTableWidget, QTableWidgetItem, 
    QAbstractItemView, QSplitter, QHeaderView, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, QDate
from datetime import date
from PySide6.QtGui import QColor
import traceback

# 프로젝트 모듈 임포트
from core.modules import trading_log # 매매일지 생성 함수
from core.database import db_manager # 매매일지 조회 함수
from core.database.models.trading_log_models import TradingLog # 타입 힌팅용
# 차트 관련 모듈 임포트 추가
from core.ui.components.chart_component import ChartComponent
from core.modules.chart import ChartModule 
# API 모듈 임포트 (ChartModule 생성 시 필요할 수 있음 - 현재는 Mock 사용 가정)
from core.api.kiwoom import KiwoomAPI 
# 스타일 모듈 임포트 추가
from core.ui.stylesheets import StyleSheets
from core.ui.constants.colors import Colors
from core.ui.constants.fonts import Fonts

logger = logging.getLogger(__name__)

class TradingLogWindow(QMdiSubWindow):
    """매매일지 MDI 자식 윈도우"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI 매매일지")
        self.setMinimumSize(800, 600)
        
        self.current_log_data: Optional[TradingLog] = None

        # 메인 위젯 및 레이아웃
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_widget.setStyleSheet(StyleSheets.WIDGET) # 메인 위젯 배경 등 기본 스타일 적용
        self.setWidget(main_widget)

        # --- 상단 컨트롤 영역 --- 
        top_controls_layout = QHBoxLayout()
        top_controls_layout.setContentsMargins(5, 5, 5, 5) # 여백 조정
        top_controls_layout.setSpacing(10) # 간격 조정
        
        # AI 모델 선택 콤보박스
        self.ai_model_combo = QComboBox()
        self.ai_model_combo.addItem("GPT-4o")
        self.ai_model_combo.setEnabled(False) # 요구사항: 읽기 전용 (비활성화)
        self.ai_model_combo.setStyleSheet(StyleSheets.COMBOBOX)
        top_controls_layout.addWidget(QLabel("분석 모델:"))
        top_controls_layout.addWidget(self.ai_model_combo)

        # 날짜 선택
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setStyleSheet(StyleSheets.INPUT) # QDateEdit도 입력 필드 스타일 적용
        self.date_edit.dateChanged.connect(self.load_log_data) # 날짜 변경 시 데이터 로드
        top_controls_layout.addWidget(QLabel("날짜:"))
        top_controls_layout.addWidget(self.date_edit)
        
        # 전략 선택 콤보박스 추가
        self.strategy_combo = QComboBox()
        self.strategy_combo.setStyleSheet(StyleSheets.COMBOBOX)
        self.strategy_combo.currentIndexChanged.connect(self.on_strategy_changed) # 인덱스 변경 시 호출
        top_controls_layout.addWidget(QLabel("전략:"))
        top_controls_layout.addWidget(self.strategy_combo)

        # ChartModule 인스턴스 생성 
        # TODO: 실제 API 클라이언트나 설정 주입 필요
        # 임시로 None 또는 기본값으로 생성
        # kiwoom_api_instance = None # 실제로는 KiwoomAPI 인스턴스 필요
        # self.chart_module = ChartModule(api_client=kiwoom_api_instance) 
        self.chart_module = ChartModule(api_client=None) # Mock API Client 가정
        
        top_controls_layout.addStretch(1) # 우측 정렬 위한 빈 공간

        # 수동 생성 버튼
        self.manual_create_button = QPushButton("수동 일지 생성")
        self.manual_create_button.setStyleSheet(StyleSheets.BUTTON) # 기본 버튼 스타일
        self.manual_create_button.clicked.connect(self.create_log_manually)
        top_controls_layout.addWidget(self.manual_create_button)
        
        main_layout.addLayout(top_controls_layout)

        # --- 콘텐츠 영역 (스플리터 사용) --- 
        content_splitter = QSplitter(Qt.Horizontal) # 좌우 분할
        content_splitter.setStyleSheet(StyleSheets.SPLITTER) # 스플리터 핸들 스타일
        main_layout.addWidget(content_splitter)

        # --- 좌측 영역 (전체 복기, 상세 매매 목록) --- 
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        content_splitter.addWidget(left_widget)

        # 전체 복기 내용
        left_layout.addWidget(QLabel("AI 종합 복기:"))
        self.overall_review_text = QTextEdit()
        self.overall_review_text.setReadOnly(True)
        self.overall_review_text.setStyleSheet(StyleSheets.TEXT_EDIT_READONLY) # 읽기전용 텍스트 에디트 스타일
        left_layout.addWidget(self.overall_review_text)

        # 상세 매매 목록 테이블
        left_layout.addWidget(QLabel("상세 매매 내역:"))
        self.trade_details_table = QTableWidget()
        self.trade_details_table.setStyleSheet(StyleSheets.TABLE_WIDGET) # 테이블 스타일 적용
        self.trade_details_table.setColumnCount(5)
        self.trade_details_table.setHorizontalHeaderLabels(["시간", "종목코드", "구분", "가격", "수량"])
        self.trade_details_table.setEditTriggers(QAbstractItemView.NoEditTriggers) # 편집 불가
        self.trade_details_table.setSelectionBehavior(QAbstractItemView.SelectRows) # 행 단위 선택
        self.trade_details_table.setSelectionMode(QAbstractItemView.SingleSelection) # 단일 선택
        self.trade_details_table.itemSelectionChanged.connect(self.display_selected_trade_analysis)
        # 컬럼 너비 자동 조절
        self.trade_details_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) 
        self.trade_details_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents) # 시간 컬럼은 내용에 맞게
        left_layout.addWidget(self.trade_details_table)

        # --- 우측 영역 (차트, 선택된 매매 분석, 학습 결과) --- 
        right_splitter = QSplitter(Qt.Vertical) # 상하 분할
        content_splitter.addWidget(right_splitter)

        # 차트 영역 (Placeholder 제거 및 ChartComponent 연동)
        self.chart_component = ChartComponent(chart_module=self.chart_module)
        # right_splitter.addWidget(chart_placeholder) # Placeholder 제거
        right_splitter.addWidget(self.chart_component) # ChartComponent 추가

        # 선택된 매매 분석 영역
        analysis_group = QGroupBox("선택된 매매 AI 분석") # 그룹박스로 감싸기
        analysis_group.setStyleSheet(StyleSheets.GROUPBOX) # 그룹박스 스타일 적용
        analysis_layout = QVBoxLayout(analysis_group) # 그룹박스 내 레이아웃
        self.ai_reason_text = QTextEdit() # 추정 사유
        self.ai_reason_text.setReadOnly(True)
        self.ai_reason_text.setPlaceholderText("AI 추정 매매 사유")
        self.ai_reason_text.setStyleSheet(StyleSheets.TEXT_EDIT_READONLY)
        self.ai_reflection_text = QTextEdit() # 복기/반성
        self.ai_reflection_text.setReadOnly(True)
        self.ai_reflection_text.setPlaceholderText("AI 복기 및 반성")
        self.ai_reflection_text.setStyleSheet(StyleSheets.TEXT_EDIT_READONLY)
        self.ai_improvement_text = QTextEdit() # 개선 방향
        self.ai_improvement_text.setReadOnly(True)
        self.ai_improvement_text.setPlaceholderText("AI 개선 방향 제시")
        self.ai_improvement_text.setStyleSheet(StyleSheets.TEXT_EDIT_READONLY)
        analysis_layout.addWidget(self.ai_reason_text)
        analysis_layout.addWidget(self.ai_reflection_text)
        analysis_layout.addWidget(self.ai_improvement_text)
        right_splitter.addWidget(analysis_group) # 위젯 대신 그룹박스 추가

        # 학습 결과 영역
        learning_group = QGroupBox("전략 학습 결과") # 그룹박스로 감싸기
        learning_group.setStyleSheet(StyleSheets.GROUPBOX)
        learning_layout = QVBoxLayout(learning_group)
        self.learning_text = QTextEdit()
        self.learning_text.setReadOnly(True)
        self.learning_text.setStyleSheet(StyleSheets.TEXT_EDIT_READONLY)
        learning_layout.addWidget(self.learning_text)
        right_splitter.addWidget(learning_group) # 위젯 대신 그룹박스 추가

        # 스플리터 초기 크기 조절
        content_splitter.setSizes([self.width() // 2, self.width() // 2]) # 좌우 50:50
        right_splitter.setSizes([self.height() // 2, self.height() // 4, self.height() // 4]) # 상중하 비율 조절

        # 초기 데이터 로드 전에 전략 목록 로드
        self.load_strategies()
        # 초기 데이터 로드 (load_strategies 후 자동으로 트리거될 수도 있음, 필요시 주석 처리)
        # self.load_log_data()

    def load_strategies(self):
        """DB에서 전략 목록을 불러와 콤보박스를 채웁니다."""
        logger.info("전략 목록 로드 중...")
        self.strategy_combo.blockSignals(True) # 데이터 로드 중 신호 발생 방지
        self.strategy_combo.clear()
        
        strategies = db_manager.get_strategies()
        if not strategies:
            logger.warning("데이터베이스에 등록된 전략이 없습니다.")
            # 필요하다면 기본 전략 추가 또는 사용자에게 알림
            self.strategy_combo.addItem("등록된 전략 없음", -1) # 사용자 데이터 -1
        else:
            for strategy in strategies:
                self.strategy_combo.addItem(strategy.name, strategy.id) # 표시 이름, 데이터(ID)
            logger.info(f"{len(strategies)}개의 전략 로드 완료.")
            
        self.strategy_combo.blockSignals(False) # 신호 발생 재개
        # 콤보박스 내용 변경 후 첫 데이터 로드 강제 실행 (선택 사항)
        # self.load_log_data() 
        # 또는 on_strategy_changed에서 처리
        if self.strategy_combo.count() > 0:
            self.on_strategy_changed(0) # 첫 번째 항목 기준으로 데이터 로드
            
    def on_strategy_changed(self, index):
        """전략 콤보박스 선택 변경 시 호출"""
        # 현재 선택된 전략 ID 업데이트 (필요한 경우)
        # strategy_id = self.strategy_combo.itemData(index)
        # logger.debug(f"선택된 전략 ID: {strategy_id}")
        self.load_log_data() # 선택된 전략 기준으로 데이터 다시 로드

    def load_log_data(self):
        """선택된 날짜와 전략에 해당하는 매매일지 데이터를 로드하여 표시"""
        selected_date = self.date_edit.date().toPyDate()
        # 현재 콤보박스에서 선택된 전략 ID 가져오기
        strategy_id = self.strategy_combo.currentData() 
        
        # 전략이 선택되지 않았거나 (예: "등록된 전략 없음") ID가 유효하지 않은 경우
        if strategy_id is None or strategy_id == -1:
            logger.warning("유효한 전략이 선택되지 않았습니다. 데이터 로드를 건너뛰었습니다.")
            self.clear_display()
            return

        logger.info(f"매매일지 데이터 로드 시도: {selected_date}, 전략 ID: {strategy_id}")
        
        logs = db_manager.get_trading_logs(log_date=selected_date, strategy_id=strategy_id)
        
        self.clear_display()
        
        if logs:
            self.current_log_data = logs[0] # 해당 날짜/전략 로그는 하나라고 가정
            logger.info(f"매매일지 로드 성공 (Log ID: {self.current_log_data.id}) - 상세 {len(self.current_log_data.details)}건, 학습 {len(self.current_log_data.learnings)}건")
            
            # 데이터 표시
            self.overall_review_text.setText(self.current_log_data.overall_review or "")
            
            # 테이블 아이템 스타일링 (선택 사항 - 매수/매도 구분 등)
            # 상세 매매 내역 테이블 채우기
            self.trade_details_table.setRowCount(len(self.current_log_data.details))
            for i, detail in enumerate(sorted(self.current_log_data.details, key=lambda x: x.trade_time)):
                self.trade_details_table.setItem(i, 0, QTableWidgetItem(detail.trade_time.strftime("%H:%M:%S")))
                self.trade_details_table.setItem(i, 1, QTableWidgetItem(detail.stock_code))
                trade_type_str = "매수" if detail.trade_type == 'buy' else "매도" if detail.trade_type == 'sell' else detail.trade_type
                item_trade_type = QTableWidgetItem(trade_type_str)
                # 매수/매도 색상 적용
                if detail.trade_type == 'buy':
                    item_trade_type.setForeground(QColor(Colors.PRICE_UP)) # styles.py의 색상 사용 (PRICE_UP이 빨강일 경우)
                elif detail.trade_type == 'sell':
                    item_trade_type.setForeground(QColor(Colors.PRICE_DOWN)) # styles.py의 색상 사용 (PRICE_DOWN이 파랑일 경우)
                self.trade_details_table.setItem(i, 2, item_trade_type)
                self.trade_details_table.setItem(i, 3, QTableWidgetItem(f"{detail.price:,.0f}")) # 가격 포맷
                self.trade_details_table.setItem(i, 4, QTableWidgetItem(f"{detail.quantity:,}")) # 수량 포맷
                # 각 행에 상세 데이터 저장 (선택 시 사용)
                self.trade_details_table.item(i, 0).setData(Qt.UserRole, detail) 
                
            # 학습 결과 표시 (여러 개일 수 있으므로 join)
            learning_texts = [l.learning_content for l in self.current_log_data.learnings]
            self.learning_text.setText("\n---\n".join(learning_texts) if learning_texts else "")
            
        else:
            self.current_log_data = None
            logger.info("해당 조건의 매매일지 데이터 없음")
            self.overall_review_text.setPlaceholderText("해당 날짜/전략의 매매일지가 없습니다.")

    def display_selected_trade_analysis(self):
        """테이블에서 선택된 매매 건의 AI 분석 내용 표시"""
        selected_items = self.trade_details_table.selectedItems()
        if not selected_items: 
            self.clear_analysis_display()
            return
            
        # 선택된 행의 첫 번째 아이템에서 상세 데이터 가져오기
        selected_detail = selected_items[0].data(Qt.UserRole)
        
        if selected_detail:
            # AI 분석 내용 표시
            self.ai_reason_text.setText(selected_detail.ai_reason or "")
            self.ai_reflection_text.setText(selected_detail.ai_reflection or "")
            self.ai_improvement_text.setText(selected_detail.ai_improvement or "")
            
            # 선택된 종목/시간 기준으로 차트 업데이트 로직 호출
            logger.debug(f"차트 로드 요청: {selected_detail.stock_code}")
            try:
                # 차트 컴포넌트 업데이트
                self.chart_component.load_chart(stock_code=selected_detail.stock_code, period='D') # 기본 일봉 로드
                
                # 현재 로그에 있는 모든 매매 내역 중 해당 종목 것 필터링하여 마커 데이터 생성
                trade_markers = []
                if self.current_log_data and self.current_log_data.details:
                    logger.debug(f"매매 마커 데이터 준비: {selected_detail.stock_code}에 대한 {len(self.current_log_data.details)}개 상세 내역 확인")
                    
                    for detail in self.current_log_data.details:
                        if detail.stock_code == selected_detail.stock_code:
                            # 차트 시간과 매매 시간 일치 여부 확인
                            try:
                                # 타임스탬프로 변환 (초 단위)
                                timestamp = int(detail.trade_time.timestamp())
                                
                                # 마커 데이터 추가
                                marker = {
                                    'timestamp': timestamp,
                                    'price': detail.price,
                                    'type': detail.trade_type, # 'buy' 또는 'sell'
                                    'text': f"{detail.trade_time.strftime('%H:%M')} {detail.trade_type.upper()}"
                                }
                                trade_markers.append(marker)
                                logger.debug(f"마커 추가: {marker}")
                            except Exception as e:
                                logger.warning(f"마커 데이터 생성 실패 ({detail.trade_time}): {e}")
                    
                    logger.debug(f"필터링된 마커 데이터: {len(trade_markers)}개")
                    
                # 마커가 있을 경우에만 설정 함수 호출
                if trade_markers:
                    self.chart_component.set_trade_markers(trade_markers)
                    logger.debug("차트에 매매 마커 설정 완료")
                else:
                    # 마커가 없으면 기존 마커 제거
                    self.chart_component.clear_trade_markers()
                    logger.debug("매매 마커 없음 - 클리어")
                    
            except Exception as e:
                logger.error(f"차트 업데이트 중 오류: {e}")
                logger.error(traceback.format_exc())
        else:
            self.chart_component.load_chart(stock_code=selected_detail.stock_code, period='D') # 기본 일봉 로드

            # 매매 마커 표시 로직 추가
            # 1. 현재 로그의 모든 매매 내역 중 해당 종목 것 필터링
            trade_markers = []
            if self.current_log_data:
                logger.debug(f"매매 마커 데이터 준비: {selected_detail.stock_code}에 대한 {len(self.current_log_data.details)}개 상세 내역 확인")
                for detail in self.current_log_data.details:
                    if detail.stock_code == selected_detail.stock_code:
                        # ChartComponent는 타임스탬프를 기대 (또는 x_index 직접 계산 필요)
                        # 우선 타임스탬프 전달 시도
                        try:
                            marker_time = detail.trade_time.timestamp()
                        except Exception as e:
                            logger.warning(f"타임스탬프 변환 실패 ({detail.trade_time}): {e}")
                            continue # 타임스탬프 변환 실패 시 마커 추가 불가
                            
                        trade_markers.append({
                            # 'x_index': 해당 시간의 x축 인덱스 (ChartComponent에서 찾아야 함)
                            'time': marker_time, 
                            'price': detail.price,
                            'type': detail.trade_type # 'buy' or 'sell'
                        })
                logger.debug(f"필터링된 마커 데이터: {len(trade_markers)}개")
                
            # 2. ChartComponent에 마커 설정 함수 호출
            self.chart_component.set_trade_markers(trade_markers)

        else:
             self.clear_analysis_display()
             
    def clear_display(self):
        """화면 내용 초기화"""
        self.overall_review_text.clear()
        self.overall_review_text.setPlaceholderText("AI 종합 복기 내용이 여기에 표시됩니다.")
        self.trade_details_table.setRowCount(0)
        self.learning_text.clear()
        self.clear_analysis_display()
        # 차트 클리어 로직 추가
        try:
            self.chart_component.load_chart(stock_code=None) # stock_code=None으로 차트 클리어 시도
            # TODO: 만약 set_trade_markers가 있다면 여기서 마커 클리어 호출
            # self.chart_component.set_trade_markers([]) 
        except Exception as e:
            logger.error(f"차트 클리어 중 오류: {e}")

    def clear_analysis_display(self):
        """선택된 매매 분석 영역 초기화"""
        self.ai_reason_text.clear()
        self.ai_reflection_text.clear()
        self.ai_improvement_text.clear()

    def create_log_manually(self):
        """수동으로 매매일지 생성을 시도"""
        selected_date = self.date_edit.date().toPyDate()
        # 현재 콤보박스에서 선택된 전략 ID 가져오기
        strategy_id = self.strategy_combo.currentData()
        
        # 전략 유효성 검사
        if strategy_id is None or strategy_id == -1:
            QMessageBox.warning(self, "오류", "매매일지를 생성할 유효한 전략이 선택되지 않았습니다.")
            return

        logger.info(f"수동 매매일지 생성 시도: {selected_date}, 전략 ID: {strategy_id}")

        # 확인 메시지 (선택 사항)
        reply = QMessageBox.question(self, '확인', 
                                     f"{selected_date} / 전략 {strategy_id} 에 대한 매매일지를 수동으로 생성하시겠습니까?\n(이미 자동 생성된 경우 생성되지 않습니다)",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                # core.modules.trading_log 의 함수 호출
                created_log = trading_log.create_trading_log(selected_date, strategy_id, is_manual_trigger=True)
                
                if created_log:
                    QMessageBox.information(self, "성공", "매매일지가 성공적으로 생성되었습니다.")
                    self.load_log_data() # 데이터 다시 로드
                else:
                    # 생성 실패 사유는 trading_log 모듈 내부 로그 또는 print로 확인됨
                    # check_log_exists 에서 걸렸을 가능성이 높음
                    QMessageBox.warning(self, "실패", "매매일지 생성에 실패했거나, 해당 날짜/전략의 자동 생성 일지가 이미 존재합니다.")
                    # 혹시 모르니 데이터 다시 로드 시도
                    self.load_log_data()
                    
            except Exception as e:
                logger.exception(f"수동 매매일지 생성 중 예외 발생: {e}")
                QMessageBox.critical(self, "오류", f"매매일지 생성 중 오류가 발생했습니다:\n{e}")

    # TODO:
    # def load_strategies(self):
    #     """DB 등에서 전략 목록을 불러와 콤보박스에 채우는 함수"""
    #     pass
    
    # def update_chart(self, stock_code: str, trade_time: datetime):
    #     """선택된 종목/시간 기준으로 차트 업데이트"""
    #     pass

# MDI 환경 테스트용 (임시)
if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QMdiArea
    
    # 로깅 설정 (간단하게)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # DB 초기화 (테스트 데이터 생성 목적)
    print("DB 초기화 및 테스트 데이터 확인...")
    db_manager.init_db() # init_db 호출 시 테스트 전략 데이터 추가 로직 실행됨
    
    # trading_log.py를 직접 실행하여 테스트 데이터가 생성되었는지 확인 필요
    # 또는 여기에 생성 코드 추가
    if not db_manager.get_trading_logs(log_date=date(2024, 4, 1), strategy_id=1):
        print("테스트 로그 생성 시도...")
        trading_log.create_trading_log(date(2024, 4, 1), 1, is_manual_trigger=False)
    else:
        print("테스트 로그 이미 존재")
    
    app = QApplication(sys.argv)
    mainWin = QMainWindow()
    mainWin.setWindowTitle('MDI 테스트')
    mdiArea = QMdiArea()
    mainWin.setCentralWidget(mdiArea)
    
    logWindow = TradingLogWindow()
    mdiArea.addSubWindow(logWindow)
    logWindow.show()
    
    mainWin.setGeometry(100, 100, 1200, 800)
    mainWin.show()
    sys.exit(app.exec_()) 