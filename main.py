# main.py
import sys
import os

# 重定向 stderr 过滤 libpng 警告 (必须在导入 Qt 之前)
class LibpngWarningFilter:
    def __init__(self, original_stderr):
        self.original_stderr = original_stderr
    
    def write(self, text):
        if 'libpng warning: iCCP' not in text:
            self.original_stderr.write(text)
    
    def flush(self):
        self.original_stderr.flush()

sys.stderr = LibpngWarningFilter(sys.stderr)

import warnings
warnings.filterwarnings("ignore", message="iCCP: known incorrect sRGB profile")

# 抑制 libpng iCCP 警告
os.environ['QT_LOGGING_RULES'] = 'qt.imageformats.png=false'

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def get_resource_path(relative_path):
    """获取资源文件的绝对路径（支持打包后运行）"""
    if getattr(sys, 'frozen', False):
        # 打包后的路径
        base_path = sys._MEIPASS
    else:
        # 开发环境的路径
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

def main():
    app = QApplication(sys.argv)

    try:
        qss_path = get_resource_path("ui/styles.qss")
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("样式表未找到，继续运行")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
