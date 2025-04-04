"""
관심 그룹 패널 컴포넌트
"""

import logging
from typing import List, Dict, Optional, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QListWidget, QListWidgetItem, 
    QInputDialog, QMessageBox, QMenu,
    QFrame, QSplitter
)
from PySide6.QtCore import Qt, Signal as pyqtSignal, QSize, QPoint
from PySide6.QtGui import QFont, QColor, QCursor, QAction

from core.ui.constants.colors import Colors
from core.ui.constants.fonts import FONT_SIZES
from core.ui.constants.rules import UI_RULES
from core.ui.stylesheets import StyleSheets
from core.modules.watchlist import WatchlistModule

logger = logging.getLogger(__name__)

class GroupItem(QListWidgetItem):
    """관심 그룹 항목"""
    
    def __init__(self, group_id: int, name: str):
        """
        Args:
            group_id: 그룹 ID
            name: 그룹 이름
        """
        super().__init__(name)
        self.group_id = group_id
        self.setData(Qt.UserRole, group_id)
        self.setToolTip(name)

class WatchlistGroupPanel(QWidget):
    """관심 그룹 패널 컴포넌트"""
    
    # 시그널 정의
    group_selected = pyqtSignal(int, str)  # group_id, group_name
    
    def __init__(self, watchlist_module: WatchlistModule):
        """
        Args:
            watchlist_module: 관심목록 모듈
        """
        super().__init__()
        logger.info("관심 그룹 패널 초기화 시작")
        
        self.watchlist_module = watchlist_module
        self.selected_group_id = 1  # 기본 그룹 ID (1)
        
        # 시그널 연결
        self.watchlist_module.watchlist_group_updated.connect(self._on_groups_updated)
        self.watchlist_module.error_occurred.connect(self._show_error)
        
        self._init_ui()
        self._load_groups()
        
        logger.info("관심 그룹 패널 초기화 완료")
        
    def _init_ui(self):
        """UI 초기화"""
        try:
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(10)
            
            # 제목 영역
            title_frame = QFrame()
            title_frame.setStyleSheet(StyleSheets.FRAME)
            title_layout = QHBoxLayout(title_frame)
            
            title_label = QLabel("관심 그룹")
            title_label.setStyleSheet(f"""
                color: {Colors.TEXT};
                font-size: {FONT_SIZES.LARGE};
                font-weight: bold;
                background-color: transparent;
                border: none;
            """)
            title_layout.addWidget(title_label)
            
            # 그룹 추가 버튼
            add_button = QPushButton("+")
            add_button.setStyleSheet(StyleSheets.BUTTON)
            add_button.setFixedSize(30, 30)
            add_button.setToolTip("관심 그룹 추가")
            add_button.clicked.connect(self._add_group)
            title_layout.addWidget(add_button)
            
            layout.addWidget(title_frame)
            
            # 그룹 목록
            self.group_list = QListWidget()
            self.group_list.setStyleSheet(f"""
                QListWidget {{
                    background-color: {Colors.BACKGROUND};
                    border: none;
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
            """)
            self.group_list.setSelectionMode(QListWidget.SingleSelection)
            self.group_list.itemClicked.connect(self._on_group_selected)
            self.group_list.setContextMenuPolicy(Qt.CustomContextMenu)
            self.group_list.customContextMenuRequested.connect(self._show_context_menu)
            
            layout.addWidget(self.group_list)
            
            self.setLayout(layout)
            self.setMinimumWidth(100)
            self.setMaximumWidth(300)
            
        except Exception as e:
            logger.error(f"관심 그룹 패널 UI 초기화 중 오류 발생: {e}", exc_info=True)
            
    def _load_groups(self):
        """관심 그룹 목록 로드"""
        try:
            groups = self.watchlist_module.get_watchlists()
            self._update_group_list(groups)
            logger.debug(f"관심 그룹 목록 로드 완료: {len(groups)}개")
        except Exception as e:
            logger.error(f"관심 그룹 목록 로드 실패: {e}", exc_info=True)
            
    def _update_group_list(self, groups: List[Dict]):
        """그룹 목록 업데이트
        
        Args:
            groups: 그룹 목록
        """
        try:
            self.group_list.clear()
            
            for group in groups:
                item = GroupItem(group["id"], group["name"])
                self.group_list.addItem(item)
                
                # 현재 선택된 그룹이면 선택 상태 유지
                if group["id"] == self.selected_group_id:
                    self.group_list.setCurrentItem(item)
                    
            # 선택된 항목이 없으면 첫 번째 항목 선택
            if self.group_list.currentItem() is None and self.group_list.count() > 0:
                self.group_list.setCurrentRow(0)
                item = self.group_list.currentItem()
                group_id = item.data(Qt.UserRole)
                self.selected_group_id = group_id
                self.group_selected.emit(group_id, item.text())
                
            logger.debug(f"그룹 목록 업데이트 완료: {len(groups)}개")
        except Exception as e:
            logger.error(f"그룹 목록 업데이트 실패: {e}", exc_info=True)
            
    def _on_groups_updated(self, groups: List[Dict]):
        """그룹 목록 업데이트 시그널 수신
        
        Args:
            groups: 그룹 목록
        """
        logger.debug(f"그룹 목록 업데이트 시그널 수신: {len(groups)}개")
        self._update_group_list(groups)
        
    def _on_group_selected(self, item: GroupItem):
        """그룹 선택 시
        
        Args:
            item: 선택된 그룹 항목
        """
        try:
            group_id = item.data(Qt.UserRole)
            self.selected_group_id = group_id
            logger.debug(f"그룹 선택: {group_id} ({item.text()})")
            self.group_selected.emit(group_id, item.text())
        except Exception as e:
            logger.error(f"그룹 선택 처리 실패: {e}", exc_info=True)
            
    def _add_group(self):
        """관심 그룹 추가"""
        try:
            name, ok = QInputDialog.getText(
                self, "관심 그룹 추가", "그룹 이름을 입력하세요:"
            )
            
            if ok and name:
                logger.debug(f"관심 그룹 추가 시도: {name}")
                
                # 이름이 비어있는 경우
                if not name.strip():
                    QMessageBox.warning(
                        self, "추가 실패", "그룹 이름을 입력해야 합니다."
                    )
                    return
                    
                # 관심 그룹 생성
                result = self.watchlist_module.create_watchlist(name)
                
                if not result:
                    # 기존 그룹 목록 가져오기
                    existing_groups = self.watchlist_module.get_watchlists()
                    exists = any(group["name"].lower() == name.lower() for group in existing_groups)
                    
                    if exists:
                        QMessageBox.warning(
                            self, "추가 실패", f"'{name}' 그룹은 이미 존재합니다. 다른 이름을 사용해주세요."
                        )
                    else:
                        QMessageBox.warning(
                            self, "추가 실패", f"'{name}' 그룹 추가에 실패했습니다."
                        )
        except Exception as e:
            logger.error(f"관심 그룹 추가 실패: {e}", exc_info=True)
            self._show_error(f"관심 그룹 추가 실패: {str(e)}")
            
    def _rename_group(self, item: GroupItem):
        """관심 그룹 이름 변경
        
        Args:
            item: 그룹 항목
        """
        try:
            group_id = item.data(Qt.UserRole)
            old_name = item.text()
            
            # 기본 그룹(ID=1)은 이름 변경 불가
            if group_id == 1:
                QMessageBox.information(
                    self, "이름 변경 불가", "기본 그룹의 이름은 변경할 수 없습니다."
                )
                return
                
            name, ok = QInputDialog.getText(
                self, "관심 그룹 이름 변경", "새 이름을 입력하세요:",
                text=old_name
            )
            
            if ok and name and name != old_name:
                logger.debug(f"관심 그룹 이름 변경 시도: {group_id} ({old_name} -> {name})")
                result = self.watchlist_module.rename_watchlist(group_id, name)
                
                if not result:
                    QMessageBox.warning(
                        self, "변경 실패", f"'{old_name}'에서 '{name}'으로 이름 변경에 실패했습니다."
                    )
        except Exception as e:
            logger.error(f"관심 그룹 이름 변경 실패: {e}", exc_info=True)
            self._show_error(f"관심 그룹 이름 변경 실패: {str(e)}")
            
    def _delete_group(self, item: GroupItem):
        """관심 그룹 삭제
        
        Args:
            item: 그룹 항목
        """
        try:
            group_id = item.data(Qt.UserRole)
            name = item.text()
            
            # 기본 그룹(ID=1)은 삭제 불가
            if group_id == 1:
                QMessageBox.information(
                    self, "삭제 불가", "기본 그룹은 삭제할 수 없습니다."
                )
                return
                
            reply = QMessageBox.question(
                self, "관심 그룹 삭제",
                f"'{name}' 그룹을 삭제하시겠습니까?\n이 그룹에 있는 모든 종목이 함께 삭제됩니다.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                logger.debug(f"관심 그룹 삭제 시도: {group_id} ({name})")
                result = self.watchlist_module.delete_watchlist(group_id)
                
                if not result:
                    QMessageBox.warning(
                        self, "삭제 실패", f"'{name}' 그룹 삭제에 실패했습니다."
                    )
        except Exception as e:
            logger.error(f"관심 그룹 삭제 실패: {e}", exc_info=True)
            self._show_error(f"관심 그룹 삭제 실패: {str(e)}")
            
    def _show_context_menu(self, pos: QPoint):
        """컨텍스트 메뉴 표시
        
        Args:
            pos: 마우스 위치
        """
        try:
            item = self.group_list.itemAt(pos)
            if not item:
                return
                
            group_id = item.data(Qt.UserRole)
            
            menu = QMenu(self)
            
            # 관심 그룹 이름 변경 메뉴
            rename_action = QAction("이름 변경", self)
            rename_action.triggered.connect(lambda: self._rename_group(item))
            menu.addAction(rename_action)
            
            # 관심 그룹 삭제 메뉴
            delete_action = QAction("삭제", self)
            delete_action.triggered.connect(lambda: self._delete_group(item))
            menu.addAction(delete_action)
            
            # 기본 그룹(ID=1)은 이름 변경/삭제 불가
            if group_id == 1:
                rename_action.setEnabled(False)
                delete_action.setEnabled(False)
                
            menu.exec_(self.group_list.mapToGlobal(pos))
        except Exception as e:
            logger.error(f"컨텍스트 메뉴 표시 실패: {e}", exc_info=True)
            
    def _show_error(self, message: str):
        """오류 메시지 표시
        
        Args:
            message: 오류 메시지
        """
        logger.error(f"오류 발생: {message}")
        QMessageBox.critical(self, "오류", message) 