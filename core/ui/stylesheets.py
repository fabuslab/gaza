"""
UI Stylesheet Definitions
"""

# Import constants
from .constants.colors import Colors
from .constants.fonts import Fonts, FONT_SIZES
from .constants.rules import UI_RULES

class StyleSheets:
    """스타일시트 정의"""

    # --- 스타일 변수 정의 시작 ---
    GROUP_ADD_BUTTON = f"""
        QPushButton {{
            background-color: {Colors.SUCCESS};
            color: white;
            border: none;
            border-radius: 3px;
            padding: 4px 8px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.DARK};
        }}
    """

    CARD_DEFAULT = f"""
        QFrame {{
            background-color: {Colors.BACKGROUND_DARKER};
            border: 1px solid {Colors.BORDER};
            border-radius: {UI_RULES.BORDER_RADIUS_LARGE};
            color: {Colors.TEXT};
        }}
    """

    CARD_HOVER = f"""
        QFrame {{
            background-color: {Colors.BACKGROUND_DARKER};
            border: 1px solid {Colors.PRIMARY};
            border-radius: {UI_RULES.BORDER_RADIUS_LARGE};
            color: {Colors.TEXT};
        }}
    """

    ACCORDION_ITEM_DEFAULT = f"""
        QFrame {{
            border: 1px solid {Colors.BORDER};
            background-color: {Colors.BACKGROUND_DARKER};
            border-radius: {UI_RULES.BORDER_RADIUS_SMALL};
            margin-bottom: {UI_RULES.MARGIN_XSMALL};
        }}
        QWidget#header_widget {{
            background-color: transparent;
        }}
        QLabel {{
            color: {Colors.TEXT};
        }}
    """
    
    ACCORDION_ITEM_EXPANDED = f"""
        QFrame {{
            border: 1px solid {Colors.PRIMARY};
            background-color: {Colors.BACKGROUND_DARKER};
            border-radius: {UI_RULES.BORDER_RADIUS_SMALL};
            margin-bottom: {UI_RULES.MARGIN_XSMALL};
        }}
         QWidget#header_widget {{
            background-color: transparent; 
        }}
        QLabel {{
            color: {Colors.TEXT};
        }}
    """
    
    CHART_PERIOD_BUTTON_ACTIVE = f"""
        QPushButton {{
            background-color: {Colors.ACCENT}; /* 활성 색상 */
            color: {Colors.BACKGROUND};
            border: 1px solid {Colors.PRIMARY}; /* 테두리 추가 */
            padding: 8px 16px;
            border-radius: {UI_RULES.BORDER_RADIUS};
            font-size: {FONT_SIZES.NORMAL};
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.ACCENT_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.ACCENT_PRESSED};
        }}
    """
    
    MENU_BUTTON = f"""
        QPushButton {{
            background-color: transparent;
            border: none;
            color: {Colors.TEXT};
            padding: 8px 16px;
            font-family: {Fonts.FAMILY};
            font-size: {FONT_SIZES.NORMAL}px;
            min-width: 80px;
        }}
        QPushButton:hover {{
            background-color: {Colors.INFO};
        }}
        QPushButton:pressed {{
            background-color: {Colors.PRIMARY};
            color: white;
        }}
    """
    
    WATCHLIST_ITEM = f"""
        QListWidget {{
            background-color: {Colors.BACKGROUND};
            border: 1px solid {Colors.BORDER};
            border-radius: {UI_RULES.BORDER_RADIUS};
            padding: 1px;
        }}
        QListWidget::item {{
            padding: {UI_RULES.PADDING_NORMAL};
            border-radius: {UI_RULES.BORDER_RADIUS};
            color: {Colors.TEXT};
        }}
        QListWidget::item:selected {{
            background-color: {Colors.PRIMARY};
            color: white;
            font-weight: bold;
        }}
        QListWidget::item:hover:!selected {{
            background-color: #E3F2FD;
            border: 1px solid {Colors.INFO};
        }}
    """
    
    CONTEXT_MENU = f"""
        QMenu {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
            border-radius: {UI_RULES.BORDER_RADIUS};
        }}
        QMenu::item {{
            padding: 8px 30px;
        }}
        QMenu::item:selected {{
            background-color: {Colors.PRIMARY};
            color: white;
        }}
    """
    
    GROUP_DELETE_BUTTON = f"""
        QPushButton {{
            background-color: {Colors.DANGER};
            color: white;
            border: none;
            border-radius: {UI_RULES.BORDER_RADIUS};
            padding: 4px 8px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.DARK};
        }}
    """
    
    BUTTON_PRIMARY = f"""
        QPushButton {{
            background-color: {Colors.PRIMARY};
            color: white;
            border: none;
            border-radius: 3px;
            padding: 8px 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.DARK};
        }}
        QPushButton:disabled {{
            background-color: {Colors.DISABLED};
            color: gray;
        }}
    """
    
    BUTTON_SECONDARY_SMALL = f""" 
        QPushButton {{
            background-color: {Colors.SECONDARY};
            color: {Colors.WHITE};
            border: 1px solid {Colors.SECONDARY};
            padding: {UI_RULES.PADDING_XSMALL} {UI_RULES.PADDING_SMALL};
            border-radius: {UI_RULES.BORDER_RADIUS_SMALL};
            font-size: {FONT_SIZES.SMALL};
        }}
        QPushButton:hover {{
            background-color: {Colors.SECONDARY_HOVER};
            border-color: {Colors.SECONDARY_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.SECONDARY_PRESSED};
            border-color: {Colors.SECONDARY_PRESSED};
        }}
        QPushButton:disabled {{
            background-color: {Colors.SECONDARY_DISABLED};
            color: {Colors.TEXT_DISABLED};
            border-color: {Colors.SECONDARY_DISABLED};
        }}
    """

    BUTTON_DANGER_SMALL = f""" 
        QPushButton {{
            background-color: {Colors.DANGER};
            color: {Colors.WHITE};
            border: 1px solid {Colors.DANGER};
            padding: {UI_RULES.PADDING_XSMALL} {UI_RULES.PADDING_SMALL};
            border-radius: {UI_RULES.BORDER_RADIUS_SMALL};
            font-size: {FONT_SIZES.SMALL};
        }}
        QPushButton:hover {{
            background-color: {Colors.DANGER_HOVER};
            border-color: {Colors.DANGER_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.DANGER_PRESSED};
            border-color: {Colors.DANGER_PRESSED};
        }}
        QPushButton:disabled {{
            background-color: {Colors.DANGER_DISABLED};
            color: {Colors.TEXT_DISABLED};
            border-color: {Colors.DANGER_DISABLED};
        }}
    """

    BUTTON_SECONDARY = f"""
        QPushButton {{
            background-color: {Colors.SECONDARY};
            color: white;
            border: none;
            border-radius: 3px;
            padding: 8px 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.DARK};
        }}
        QPushButton:disabled {{
            background-color: {Colors.DISABLED};
            color: gray;
        }}
    """
    # --- 스타일 변수 정의 끝 ---

    # 기본 위젯 스타일
    WIDGET = f"""
        QWidget {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
            font-family: {Fonts.FAMILY};
            font-size: {FONT_SIZES.NORMAL};
        }}
    """
    
    # 버튼 스타일
    BUTTON = f"""
        QPushButton {{
            background-color: {Colors.PRIMARY};
            color: {Colors.BACKGROUND};
            border: none;
            padding: 8px 16px;
            border-radius: {UI_RULES.BORDER_RADIUS};
            font-size: {FONT_SIZES.SMALL};
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.PRIMARY_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.PRIMARY_PRESSED};
        }}
        QPushButton:disabled {{
            background-color: {Colors.DISABLED};
            color: {Colors.TEXT_DISABLED};
        }}
    """
    
    # 선택된 버튼 스타일 (추가)
    BUTTON_SELECTED = f"""
        QPushButton {{
            background-color: {Colors.INFO};  # 선택 시 배경색 변경
            color: white;
            border: 1px solid {Colors.PRIMARY}; # 선택 표시를 위한 테두리 추가 (선택사항)
            border-radius: {UI_RULES.BORDER_RADIUS};
            padding: {UI_RULES.PADDING_SMALL} {UI_RULES.PADDING_NORMAL};
            font-weight: {Fonts.WEIGHT_BOLD};
            min-width: 80px;
        }}
        /* 선택된 상태에서는 호버/눌림 효과를 다르게 주거나 없앨 수 있음 */
        QPushButton:hover {{
            background-color: {Colors.PRIMARY}; /* 호버 시 약간 더 진하게 */
        }}
        QPushButton:pressed {{
            background-color: {Colors.SECONDARY};
        }}
        QPushButton:disabled {{
            background-color: {Colors.DISABLED};
        }}
    """
    
    # 보조 버튼 스타일
    # BUTTON_SECONDARY = f""" ... """ # 이미 위에서 정의됨
    
    # 입력 필드 스타일
    INPUT = f"""
        QLineEdit {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
            border-radius: {UI_RULES.BORDER_RADIUS};
            padding: {UI_RULES.PADDING_SMALL};
            selection-background-color: {Colors.PRIMARY};
        }}
        QLineEdit:focus {{
            border: 2px solid {Colors.PRIMARY};
        }}
        QLineEdit:disabled {{
            background-color: {Colors.DISABLED};
        }}
    """
    
    # LINE_EDIT 속성 (INPUT과 동일)
    LINE_EDIT = INPUT
    
    # 텍스트 에디트 스타일 (추가)
    TEXT_EDIT = f"""
        QTextEdit {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
            border-radius: {UI_RULES.BORDER_RADIUS};
            padding: {UI_RULES.PADDING_SMALL};
            selection-background-color: {Colors.PRIMARY};
        }}
        QTextEdit:focus {{
            border: 2px solid {Colors.PRIMARY};
        }}
        QTextEdit:disabled {{
            background-color: {Colors.DISABLED};
        }}
    """
    
    # 읽기 전용 텍스트 에디트 스타일 (추가)
    TEXT_EDIT_READONLY = f"""
        QTextEdit {{
            background-color: {Colors.BACKGROUND_LIGHT}; /* 약간 다른 배경 */
            color: {Colors.TEXT_SECONDARY};
            border: 1px solid {Colors.BORDER};
            border-radius: {UI_RULES.BORDER_RADIUS};
            padding: {UI_RULES.PADDING_SMALL};
        }}
    """

    # 레이블 스타일
    LABEL = f"""
        QLabel {{
            color: {Colors.TEXT};
            font-size: {FONT_SIZES.NORMAL};
        }}
    """
    
    # 콤보박스 스타일
    COMBOBOX = f"""
        QComboBox {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
            border-radius: {UI_RULES.BORDER_RADIUS};
            padding: {UI_RULES.PADDING_SMALL};
            min-width: 100px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: url(resources/icons/down_arrow.png);
            width: 12px;
            height: 12px;
        }}
        QComboBox:disabled {{
            background-color: {Colors.DISABLED};
        }}
    """
    
    # 콤보박스 스타일 (COMBOBOX와 동일)
    COMBO_BOX = COMBOBOX
    
    # 추가 버튼 스타일 (수정)
    ADD_BUTTON = f"""
        QPushButton {{
            background-color: {Colors.SUCCESS};
            color: white;
            border: none;
            border-radius: 3px;
            padding: 4px 8px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.DARK};
        }}
    """
    
    # 삭제 버튼 스타일 (수정)
    DELETE_BUTTON = f"""
        QPushButton {{
            background-color: {Colors.DANGER};
            color: white;
            border: none;
            border-radius: 3px;
            padding: 4px 8px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.DARK};
        }}
    """
    
    # 경고 버튼 스타일
    BUTTON_WARNING = f"""
        QPushButton {{
            background-color: {Colors.WARNING};
            color: {Colors.TEXT};
            border: none;
            border-radius: {UI_RULES.BORDER_RADIUS};
            padding: {UI_RULES.PADDING_SMALL} {UI_RULES.PADDING_NORMAL};
            font-weight: {Fonts.WEIGHT_BOLD};
            min-width: 80px;
        }}
        QPushButton:hover {{
            background-color: #FFA000;
        }}
        QPushButton:pressed {{
            background-color: #FF8F00;
        }}
        QPushButton:disabled {{
            background-color: {Colors.DISABLED};
        }}
    """
    
    # 체크박스 스타일
    CHECKBOX = f"""
        QCheckBox {{
            color: {Colors.TEXT};
            spacing: 5px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
        }}
        QCheckBox::indicator:unchecked {{
            border: 2px solid {Colors.BORDER};
            background-color: {Colors.BACKGROUND};
            border-radius: 3px;
        }}
        QCheckBox::indicator:checked {{
            border: 2px solid {Colors.PRIMARY};
            background-color: {Colors.PRIMARY};
            border-radius: 3px;
            image: url(resources/icons/check.png);
        }}
        QCheckBox:disabled {{
            color: {Colors.DISABLED};
        }}
    """
    
    # 라디오버튼 스타일
    RADIO = f"""
        QRadioButton {{
            color: {Colors.TEXT};
            spacing: 5px;
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
        }}
        QRadioButton::indicator:unchecked {{
            border: 2px solid {Colors.BORDER};
            background-color: {Colors.BACKGROUND};
            border-radius: 9px;
        }}
        QRadioButton::indicator:checked {{
            border: 2px solid {Colors.PRIMARY};
            background-color: {Colors.PRIMARY};
            border-radius: 9px;
        }}
        QRadioButton:disabled {{
            color: {Colors.DISABLED};
        }}
    """
    
    # 프로그레스바 스타일
    PROGRESSBAR = f"""
        QProgressBar {{
            border: 1px solid {Colors.BORDER};
            border-radius: {UI_RULES.BORDER_RADIUS};
            text-align: center;
            background-color: {Colors.BACKGROUND};
        }}
        QProgressBar::chunk {{
            background-color: {Colors.PRIMARY};
            border-radius: {UI_RULES.BORDER_RADIUS};
        }}
    """
    
    # 스크롤바 스타일
    SCROLLBAR = f"""
        QScrollBar:vertical {{
            border: none;
            background-color: {Colors.BACKGROUND};
            width: 12px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {Colors.SECONDARY};
            border-radius: 6px;
            min-height: 20px;
        }}
        QScrollBar::add-line:vertical {{
            height: 0px;
        }}
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            border: none;
            background-color: {Colors.BACKGROUND};
            height: 12px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {Colors.SECONDARY};
            border-radius: 6px;
            min-width: 20px;
        }}
        QScrollBar::add-line:horizontal {{
            width: 0px;
        }}
        QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
    """
    
    # 메뉴바 스타일
    MENUBAR = f"""
        QMenuBar {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
            border-bottom: 1px solid {Colors.BORDER};
        }}
        QMenuBar::item {{
            background-color: transparent;
            padding: {UI_RULES.PADDING_SMALL} {UI_RULES.PADDING_NORMAL};
        }}
        QMenuBar::item:selected {{
            background-color: {Colors.PRIMARY};
            color: white;
        }}
    """
    
    # 메뉴 스타일
    MENU = f"""
        QMenu {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
        }}
        QMenu::item {{
            padding: {UI_RULES.PADDING_SMALL} {UI_RULES.PADDING_LARGE};
        }}
        QMenu::item:selected {{
            background-color: {Colors.PRIMARY};
            color: white;
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {Colors.BORDER};
            margin: {UI_RULES.MARGIN_SMALL} 0px;
        }}
    """
    
    # 상태바 스타일
    STATUSBAR = f"""
        QStatusBar {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
            border-top: 1px solid {Colors.BORDER};
        }}
        QStatusBar::item {{
            border: none;
        }}
    """
    
    # 탭 위젯 스타일
    TAB = f"""
        QTabWidget::pane {{
            border: 1px solid {Colors.BORDER};
            border-radius: {UI_RULES.BORDER_RADIUS};
            background-color: {Colors.BACKGROUND};
        }}
        QTabBar::tab {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
            border-bottom: none;
            border-top-left-radius: {UI_RULES.BORDER_RADIUS};
            border-top-right-radius: {UI_RULES.BORDER_RADIUS};
            padding: {UI_RULES.PADDING_SMALL} {UI_RULES.PADDING_NORMAL};
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background-color: {Colors.PRIMARY};
            color: white;
        }}
        QTabBar::tab:!selected {{
            margin-top: 2px;
        }}
    """
    
    # 테이블 위젯 스타일
    TABLE = f"""
        QTableWidget {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
            gridline-color: {Colors.BORDER};
        }}
        QTableWidget::item {{
            padding: {UI_RULES.PADDING_SMALL};
        }}
        QTableWidget::item:selected {{
            background-color: {Colors.PRIMARY};
            color: white;
        }}
        QHeaderView::section {{
            background-color: {Colors.SECONDARY};
            color: white;
            padding: {UI_RULES.PADDING_SMALL};
            border: none;
            border-right: 1px solid {Colors.BORDER};
            border-bottom: 1px solid {Colors.BORDER};
        }}
    """
    
    # 트리 위젯 스타일
    TREE = f"""
        QTreeWidget {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
        }}
        QTreeWidget::item {{
            padding: {UI_RULES.PADDING_SMALL};
        }}
        QTreeWidget::item:selected {{
            background-color: {Colors.PRIMARY};
            color: white;
        }}
        QTreeWidget::branch {{
            background-color: {Colors.BACKGROUND};
        }}
    """
    
    # 리스트 위젯 스타일 (추가/수정)
    LIST_WIDGET = f"""
        QListWidget {{
            background-color: {Colors.BACKGROUND};
            border: 1px solid {Colors.BORDER};
            border-radius: {UI_RULES.BORDER_RADIUS};
            padding: 1px;
        }}
        QListWidget::item {{
            padding: {UI_RULES.PADDING_SMALL};
            border-radius: {UI_RULES.BORDER_RADIUS};
        }}
        QListWidget::item:selected {{
            background-color: {Colors.PRIMARY};
            color: white;
        }}
        QListWidget::item:hover {{
            background-color: #E3F2FD;
        }}
    """
    
    # 프레임 스타일 (추가/수정)
    FRAME = f"""
        QFrame {{
            background-color: {Colors.BACKGROUND};
            border: 1px solid {Colors.BORDER};
            border-radius: {UI_RULES.BORDER_RADIUS};
        }}
    """
    
    # 테이블 위젯 스타일
    TABLE_WIDGET = f"""
        QTableWidget {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
            gridline-color: {Colors.BORDER};
        }}
        QTableWidget::item {{
            padding: {UI_RULES.PADDING_SMALL};
        }}
        QTableWidget::item:selected {{
            background-color: {Colors.PRIMARY};
            color: white;
        }}
        QHeaderView::section {{
            background-color: {Colors.SECONDARY};
            color: white;
            padding: {UI_RULES.PADDING_SMALL};
            border: none;
            border-right: 1px solid {Colors.BORDER};
            border-bottom: 1px solid {Colors.BORDER};
        }}
    """
    
    # 스핀박스 스타일
    SPINBOX = f"""
        QSpinBox, QDoubleSpinBox {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
            border-radius: {UI_RULES.BORDER_RADIUS};
            padding: {UI_RULES.PADDING_SMALL};
        }}
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            width: 16px;
            border-left: 1px solid {Colors.BORDER};
            border-bottom: 1px solid {Colors.BORDER};
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            width: 16px;
            border-left: 1px solid {Colors.BORDER};
        }}
        QSpinBox:disabled, QDoubleSpinBox:disabled {{
            background-color: {Colors.DISABLED};
        }}
    """
    
    # 슬라이더 스타일
    SLIDER = f"""
        QSlider::groove:horizontal {{
            border: 1px solid {Colors.BORDER};
            height: 4px;
            background-color: {Colors.BACKGROUND};
            margin: 0px;
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background-color: {Colors.PRIMARY};
            border: none;
            width: 16px;
            height: 16px;
            margin: -6px 0px;
            border-radius: 8px;
        }}
        QSlider::add-page:horizontal {{
            background-color: {Colors.BORDER};
        }}
        QSlider::sub-page:horizontal {{
            background-color: {Colors.PRIMARY};
        }}
    """
    
    # 그룹박스 스타일
    GROUPBOX = f"""
        QGroupBox {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
            border-radius: {UI_RULES.BORDER_RADIUS};
            margin-top: 1em;
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: {UI_RULES.PADDING_NORMAL};
            padding: 0px {UI_RULES.PADDING_SMALL};
        }}
    """
    
    # GROUP_BOX 속성 (GROUPBOX와 동일)
    GROUP_BOX = GROUPBOX
    
    # --- 추가: 툴바 스타일 ---
    TOOLBAR = f"""
        QToolBar {{
            background-color: {Colors.BACKGROUND_LIGHT};
            border-bottom: 1px solid {Colors.BORDER};
            padding: {UI_RULES.PADDING_SMALL};
            spacing: {UI_RULES.MARGIN_SMALL};
        }}
        QToolBarSeparator {{
            background-color: {Colors.BORDER};
            width: 1px;
            margin: {UI_RULES.MARGIN_SMALL} 0;
        }}
    """
    # --- 툴바 스타일 끝 ---
    
    # --- 추가: 툴바 버튼 스타일 ---
    TOOLBAR_BUTTON = f"""
        QPushButton {{
            background-color: transparent;
            border: 1px solid transparent; # 호버 시 테두리 보이도록
            color: {Colors.TEXT};
            padding: 5px 10px; # 메뉴 버튼보다 작게
            font-family: {Fonts.FAMILY};
            font-size: {FONT_SIZES.SMALL}px; # 약간 작게
            min-width: 50px;
        }}
        QPushButton:hover {{
            background-color: {Colors.BACKGROUND_DARKER};
            border: 1px solid {Colors.BORDER_DARK};
        }}
        QPushButton:pressed {{
            background-color: {Colors.PRIMARY};
            color: white;
            border: 1px solid {Colors.PRIMARY_PRESSED};
        }}
        QPushButton:checked {{
            background-color: {Colors.INFO};
            color: white;
            font-weight: bold;
            border: 1px solid {Colors.PRIMARY};
        }}
        QPushButton:disabled {{
            color: {Colors.TEXT_DISABLED};
        }}
    """

    TOOLBAR_BUTTON_DROPDOWN = TOOLBAR_BUTTON + f"""
        QPushButton::menu-indicator {{
            image: url(resources/icons/down_arrow_dark.png); /* 어두운 화살표 아이콘 필요 */
            subcontrol-origin: padding;
            subcontrol-position: right center;
            right: 4px;
        }}
    """ 
    # --- 툴바 버튼 스타일 끝 ---
    
    # 로그아웃 버튼 레이어 스타일
    LOGOUT_LAYER = f"""
        QWidget {{
            background-color: {Colors.BACKGROUND};
            border: 1px solid {Colors.BORDER};
        }}
    """
    
    LOGOUT_BUTTON = f"""
        QPushButton {{
            background-color: {Colors.DANGER};
            color: white;
            border: none;
            border-radius: 3px;
            padding: 8px 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {Colors.HOVER};
        }}
        QPushButton:pressed {{
            background-color: {Colors.DARK};
        }}
        QPushButton:disabled {{
            background-color: {Colors.DISABLED};
            color: gray;
        }}
    """
    
    # 추세 아이콘 스타일 (추가)
    TREND_ICON = f"""
        QLabel {{
            font-size: {FONT_SIZES.NORMAL};
            font-weight: bold;
            padding: 2px;
            border-radius: 3px;
            min-width: 16px;
            text-align: center;
        }}
    """
    
    # 스플리터 스타일 (수정)
    SPLITTER = f"""
        QSplitter::handle {{
            background-color: {Colors.BORDER_LIGHT}; /* 연한 회색으로 변경 */
            border: 1px solid {Colors.BORDER}; /* 테두리 추가 */
            width: 5px; /* 너비 조정 */
            margin: 2px 0; /* 상하 마진 */
            border-radius: 2px;
            /* TODO: 점 3개 이미지 추가 필요 */
            /* image: url(resources/icons/splitter_handle.png); */ 
        }}
        QSplitter::handle:horizontal {{
            height: 5px; /* 수평 핸들 높이 */
            margin: 0 2px; /* 좌우 마진 */
        }}
        QSplitter::handle:hover {{
            background-color: {Colors.PRIMARY_HOVER}; /* 호버 색상 변경 */
            border: 1px solid {Colors.PRIMARY};
        }}
    """
    
    # 검색 컨테이너 스타일
    SEARCH_CONTAINER = f"""
        QFrame {{
            background-color: {Colors.BACKGROUND};
            border-radius: {UI_RULES.BORDER_RADIUS};
            border: 1px solid transparent;
            padding: 2px;
        }}
    """
    
    # 결과 컨테이너 스타일 (테두리 있음)
    RESULT_CONTAINER = f"""
        QFrame {{
            background-color: {Colors.BACKGROUND};
            border-radius: {UI_RULES.BORDER_RADIUS};
            border: 1px solid {Colors.BORDER};
            padding: 0px;
        }}
    """
    
    # 결과 타이틀 스타일
    RESULT_TITLE = f"""
        QLabel {{
            color: {Colors.TEXT};
            font-size: {FONT_SIZES.LARGE};
            font-weight: {Fonts.WEIGHT_BOLD};
            padding: 0px;
            background-color: transparent;
            border: none;
        }}
    """
    
    # 서브 타이틀 스타일 (추가)
    SUBTITLE = f"""
        QLabel {{
            color: {Colors.TEXT};
            font-size: {FONT_SIZES.SUBTITLE};
            font-weight: {Fonts.WEIGHT_BOLD};
            padding: 0px;
            background-color: transparent;
            border: none;
        }}
    """
    
    # 검색 타이틀 스타일
    SEARCH_TITLE = f"""
        QLabel {{
            color: {Colors.TEXT};
            font-size: {FONT_SIZES.NORMAL};
            font-weight: {Fonts.WEIGHT_BOLD};
            padding: 0px;
            min-width: 60px;
            max-width: 80px;
            background-color: transparent;
            border: none;
        }}
    """
    
    # 검색 입력 필드 스타일
    SEARCH_INPUT = f"""
        QLineEdit {{
            background-color: {Colors.BACKGROUND};
            color: {Colors.TEXT};
            border: 1px solid {Colors.BORDER};
            border-radius: 2px;
            padding: 4px 8px;
            font-size: {FONT_SIZES.NORMAL};
        }}
        QLineEdit:focus {{
            background-color: #F5F9FF;
            border: 1px solid {Colors.PRIMARY};
        }}
    """
    
    # 검색 버튼 스타일
    SEARCH_BUTTON = f"""
        QPushButton {{
            background-color: {Colors.PRIMARY};
            color: white;
            border: none;
            border-radius: {UI_RULES.BORDER_RADIUS};
            padding: 4px 12px;
            font-weight: {Fonts.WEIGHT_BOLD};
            min-width: 60px;
            font-size: {FONT_SIZES.NORMAL};
        }}
        QPushButton:hover {{
            background-color: {Colors.INFO};
        }}
        QPushButton:pressed {{
            background-color: {Colors.SECONDARY};
        }}
    """
    
    # 관심그룹 리스트 아이템 스타일 (중복 정의 제거 필요 확인)
    # WATCHLIST_ITEM = f""" ... """
    
    # 상황메뉴 스타일 (중복 정의 제거 필요 확인)
    # CONTEXT_MENU = f""" ... """
    
    # 관심그룹 삭제 버튼 스타일 (중복 정의 제거 필요 확인)
    # GROUP_DELETE_BUTTON = f""" ... """
    
    # PRIMARY_BUTTON -> BUTTON_PRIMARY 이름 변경 (중복 정의 제거 필요 확인)
    # BUTTON_PRIMARY = f""" ... """
    
    # 작은 버튼 스타일 정의 추가 (중복 정의 제거 필요 확인)
    # BUTTON_SECONDARY_SMALL = f""" ... """
    # BUTTON_DANGER_SMALL = f""" ... """
    # ----- 작은 버튼 스타일 끝 -----
    
    # SECONDARY_BUTTON -> BUTTON_SECONDARY 이름 변경 (중복 정의 제거 필요 확인)
    # BUTTON_SECONDARY = f""" ... """
    
    # GROUP_ADD_BUTTON (중복 정의 제거 필요 확인)
    # GROUP_ADD_BUTTON = f""" ... """
    
    # 카드 스타일 (중복 정의 제거 필요 확인)
    # CARD_DEFAULT = f""" ... """
    # CARD_HOVER = f""" ... """

    # 아코디언 아이템 스타일 (중복 정의 제거 필요 확인)
    # ACCORDION_ITEM_DEFAULT = f""" ... """
    # ACCORDION_ITEM_EXPANDED = f""" ... """
    
    # 활성 차트 기간 버튼 스타일 (기본 버튼 기반) (중복 정의 제거 필요 확인)
    # CHART_PERIOD_BUTTON_ACTIVE = f""" ... """
    
    # 메뉴 버튼 스타일 (중복 정의 제거 필요 확인)
    # MENU_BUTTON = f""" ... """ 