"""
UI 모듈
"""

# 주의: 여기서 MainWindow 임포트하면 순환 참조 발생
# (원인: main_window.py가 core.ui.styles를 임포트하고,
#       styles를 임포트할 때 이 파일이 먼저 실행되기 때문)

__all__ = ["MainWindow"]

# 사용처에서 MainWindow를 임포트할 때는 아래와 같이 사용해야 함:
# from core.ui.main_window import MainWindow 