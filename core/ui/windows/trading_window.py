from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QPushButton, QComboBox, QDialog
from PySide6.QtCore import Qt, QSize
from core.ui.stylesheets import StyleSheets
from core.ui.constants.colors import Colors
from core.ui.components.chart_component import ChartComponent
from core.modules.chart import ChartModule

class TradingWindow(QMainWindow):
    def __init__(self, kiwoom_api):
        super().__init__()
        self.kiwoom_api = kiwoom_api
        self.chart_modules = {}  # 차트 모듈 저장 {tab_index: ChartModule}
        self.chart_components = {}  # 차트 컴포넌트 저장 {tab_index: ChartComponent}
        self.stock_codes = ["005930", "035720", "000660", "207940"]  # 기본 종목 코드 (삼성전자, 카카오, SK하이닉스, 삼성바이오로직스)
        self.stock_names = ["삼성전자", "카카오", "SK하이닉스", "삼성바이오로직스"]  # 기본 종목 이름
        self.current_chart_type = "D"  # 기본 차트 타입 (일봉)
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("차트 분석")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(StyleSheets.WIDGET)
        
        # 중앙 위젯 생성
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 상단 컨트롤 영역
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(0, 0, 0, 10)
        
        # 종목 선택 콤보 박스
        self.stock_combo = QComboBox()
        self.stock_combo.setMinimumWidth(150)
        for i, name in enumerate(self.stock_names):
            self.stock_combo.addItem(f"{name} ({self.stock_codes[i]})")
        self.stock_combo.currentIndexChanged.connect(self.change_current_chart)
        
        # 차트 타입 선택 콤보 박스
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["일봉", "주봉", "월봉", "년봉", "분봉", "틱"])
        self.chart_type_combo.setCurrentIndex(0)
        self.chart_type_combo.currentIndexChanged.connect(self.change_chart_type)
        
        # 새 탭 추가 버튼
        add_tab_btn = QPushButton("+ 차트 추가")
        add_tab_btn.clicked.connect(self.add_chart_tab)
        
        # 컨트롤 레이아웃에 위젯 추가
        control_layout.addWidget(QLabel("종목 선택:"))
        control_layout.addWidget(self.stock_combo)
        control_layout.addWidget(QLabel("차트 타입:"))
        control_layout.addWidget(self.chart_type_combo)
        control_layout.addStretch()
        control_layout.addWidget(add_tab_btn)
        
        # 탭 위젯 생성
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_chart_tab)
        self.tab_widget.currentChanged.connect(self.tab_changed)
        
        # 메인 레이아웃에 위젯 추가
        main_layout.addWidget(control_widget)
        main_layout.addWidget(self.tab_widget)
        
        # 중앙 위젯 설정
        self.setCentralWidget(central_widget)
        
        # 초기 차트 탭 생성
        self.add_chart_tab()
    
    def add_chart_tab(self):
        """새 차트 탭 추가"""
        # 새 탭 위젯 생성
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        
        # 차트 모듈 및 컴포넌트 생성
        chart_module = ChartModule(self.kiwoom_api)
        chart_component = ChartComponent(chart_module=chart_module)
        
        # 탭 추가
        tab_index = self.tab_widget.addTab(tab, "새 차트")
        self.tab_widget.setCurrentIndex(tab_index)
        
        # 차트 모듈 및 컴포넌트 저장
        self.chart_modules[tab_index] = chart_module
        self.chart_components[tab_index] = chart_component
        
        # 차트 컴포넌트 추가
        tab_layout.addWidget(chart_component)
        
        # 현재 선택된 종목 로드
        selected_index = self.stock_combo.currentIndex()
        self.load_chart(tab_index, self.stock_codes[selected_index], self.stock_names[selected_index])
        
        # 탭 제목 업데이트
        self.tab_widget.setTabText(tab_index, self.stock_names[selected_index])
    
    def close_chart_tab(self, index):
        """차트 탭 닫기"""
        if self.tab_widget.count() > 1:  # 최소 1개의 탭은 유지
            # 차트 모듈 및 컴포넌트 정리
            if index in self.chart_modules:
                del self.chart_modules[index]
            if index in self.chart_components:
                del self.chart_components[index]
            
            # 탭 제거
            self.tab_widget.removeTab(index)
            
            # 인덱스 재정렬
            new_modules = {}
            new_components = {}
            for i in range(self.tab_widget.count()):
                if i in self.chart_modules:
                    new_modules[i] = self.chart_modules[i]
                if i in self.chart_components:
                    new_components[i] = self.chart_components[i]
            self.chart_modules = new_modules
            self.chart_components = new_components
    
    def tab_changed(self, index):
        """탭 변경시 호출되는 메서드"""
        # 현재 탭의 종목에 맞게 콤보박스 업데이트
        tab_text = self.tab_widget.tabText(index)
        for i, name in enumerate(self.stock_names):
            if name in tab_text:
                self.stock_combo.setCurrentIndex(i)
                break
    
    def change_current_chart(self, index):
        """선택된 종목 변경시 호출되는 메서드"""
        current_tab = self.tab_widget.currentIndex()
        if current_tab >= 0 and index >= 0:
            self.load_chart(current_tab, self.stock_codes[index], self.stock_names[index])
            self.tab_widget.setTabText(current_tab, self.stock_names[index])
    
    def change_chart_type(self, index):
        """차트 타입 변경시 호출되는 메서드"""
        # 차트 타입 매핑
        chart_types = {0: "D", 1: "W", 2: "M", 3: "Y", 4: "m", 5: "1T"}
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab >= 0 and current_tab in self.chart_components:
            chart_component = self.chart_components[current_tab]
            selected_stock_index = self.stock_combo.currentIndex()
            if selected_stock_index >= 0:
                stock_code = self.stock_codes[selected_stock_index]
                stock_name = self.stock_names[selected_stock_index]
                
                if index == 4:  # 분봉 선택 시
                    # 추가 분봉 타입 선택 대화상자
                    minutes = ["1", "3", "5", "10", "15", "30", "60"]
                    minutes_combo = QComboBox()
                    minutes_combo.addItems([f"{m}분봉" for m in minutes])
                    
                    dialog_layout = QVBoxLayout()
                    dialog_layout.addWidget(QLabel("분봉 타입 선택:"))
                    dialog_layout.addWidget(minutes_combo)
                    
                    dialog = QDialog(self)
                    dialog.setWindowTitle("분봉 선택")
                    dialog.setLayout(dialog_layout)
                    
                    buttons_layout = QHBoxLayout()
                    ok_button = QPushButton("확인")
                    ok_button.clicked.connect(dialog.accept)
                    cancel_button = QPushButton("취소")
                    cancel_button.clicked.connect(dialog.reject)
                    
                    buttons_layout.addWidget(ok_button)
                    buttons_layout.addWidget(cancel_button)
                    dialog_layout.addLayout(buttons_layout)
                    
                    if dialog.exec_() == QDialog.Accepted:
                        selected_minute = minutes[minutes_combo.currentIndex()]
                        chart_component.load_chart_data(stock_code, stock_name, selected_minute)
                    else:
                        # 취소하면 원래 선택으로 콤보박스 되돌림
                        if self.current_chart_type is not None:
                            for i, type_code in chart_types.items():
                                if type_code == self.current_chart_type:
                                    self.chart_type_combo.setCurrentIndex(i)
                                    break
                        return
                
                elif index == 5:  # 틱 선택 시
                    # 틱 선택 대화상자
                    ticks = ["1", "3", "5", "10"]
                    ticks_combo = QComboBox()
                    ticks_combo.addItems([f"{t}틱" for t in ticks])
                    
                    dialog_layout = QVBoxLayout()
                    dialog_layout.addWidget(QLabel("틱 타입 선택:"))
                    dialog_layout.addWidget(ticks_combo)
                    
                    dialog = QDialog(self)
                    dialog.setWindowTitle("틱 선택")
                    dialog.setLayout(dialog_layout)
                    
                    buttons_layout = QHBoxLayout()
                    ok_button = QPushButton("확인")
                    ok_button.clicked.connect(dialog.accept)
                    cancel_button = QPushButton("취소")
                    cancel_button.clicked.connect(dialog.reject)
                    
                    buttons_layout.addWidget(ok_button)
                    buttons_layout.addWidget(cancel_button)
                    dialog_layout.addLayout(buttons_layout)
                    
                    if dialog.exec_() == QDialog.Accepted:
                        selected_tick = ticks[ticks_combo.currentIndex()]
                        chart_component.load_chart_data(stock_code, stock_name, f"{selected_tick}T")
                    else:
                        # 취소하면 원래 선택으로 콤보박스 되돌림
                        if self.current_chart_type is not None:
                            for i, type_code in chart_types.items():
                                if type_code == self.current_chart_type:
                                    self.chart_type_combo.setCurrentIndex(i)
                                    break
                        return
                
                else:
                    # 일반 차트 타입 처리
                    chart_component.load_chart_data(stock_code, stock_name, chart_types[index])
                
                # 현재 차트 타입 저장
                self.current_chart_type = chart_types[index]
    
    def load_chart(self, tab_index, stock_code, stock_name):
        """특정 탭에 차트 데이터 로드"""
        try:
            if tab_index in self.chart_components:
                chart_component = self.chart_components[tab_index]
                chart_component.load_chart_data(stock_code, stock_name)
        except Exception as e:
            print(f"차트 로드 중 오류 발생: {e}") 