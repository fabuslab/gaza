from core.ui.stylesheets import StyleSheets
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel

class JournalWindow(QMainWindow):
    def __init__(self, kiwoom_api):
        super().__init__()
        self.kiwoom_api = kiwoom_api
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("매매일지")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(StyleSheets.WIDGET) 