# main.py
import sys
import os
import ctypes

# 设置 stdout/stderr 为 UTF-8，避免 emoji 等字符在 GBK 终端报错
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# 设置 DPI 感知（必须在导入 Qt 之前，最优先！）
try:
    # 尝试设置 Per Monitor V2 (Windows 10 1803+)
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    print("[OK] DPI Awareness: Per Monitor V2")
except Exception as e1:
    try:
        # 降级到 Per Monitor
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        print("[OK] DPI Awareness: Per Monitor")
    except Exception as e2:
        try:
            # 降级到 System DPI Aware
            ctypes.windll.user32.SetProcessDPIAware()
            print("[OK] DPI Awareness: System DPI Aware")
        except Exception as e3:
            print("[WARN] Failed to set DPI awareness")

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
    """获取资源文件的正确路径，支持打包后运行"""
    if getattr(sys, 'frozen', False):
        # 打包环境
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(sys.executable)
        return os.path.join(base_path, relative_path)
    else:
        # 开发环境
        base_path = os.path.dirname(__file__)
        return os.path.join(base_path, relative_path)

def main():
    app = QApplication(sys.argv)

    try:
        qss_path = get_resource_path("ui/styles.qss")
        with open(qss_path, "r", encoding="utf-8") as f:
            qss_content = f.read()
        
        no_focus_style = """
            QPushButton:focus,
            QListWidget:focus,
            QComboBox:focus,
            QLineEdit:focus,
            QSpinBox:focus,
            QDoubleSpinBox:focus,
            QCheckBox:focus,
            QLabel:focus {
                outline: none;
            }
        """
        
        app.setStyleSheet(qss_content + no_focus_style)
    except FileNotFoundError:
        print("样式表未找到，继续运行")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
