"""
屏幕框选工具 - 类似QQ截图的透明覆盖层框选
"""
import sys
import ctypes
from ctypes import windll

# 设置DPI感知（必须在导入Qt之前）
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    print("[DPI] Per Monitor V2")
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        print("[DPI] System DPI Aware")
    except:
        print("[DPI] Failed to set DPI awareness")

from PySide6.QtWidgets import QApplication, QWidget, QRubberBand
from PySide6.QtCore import Qt, QRect, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap, QScreen


class ScreenSelector(QWidget):
    """全屏透明覆盖层,用于鼠标框选区域"""

    # 信号: 框选完成,返回区域坐标(x, y, width, height)
    region_selected = Signal(int, int, int, int)
    selection_cancelled = Signal()

    def __init__(self):
        super().__init__()

        # 设置为全屏、无边框、置顶
        # 使用 Qt.Window 而不是 Qt.Tool，确保全屏覆盖
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Window
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # 获取所有屏幕的几何信息（物理像素）
        self._setup_fullscreen_geometry()

        # 框选状态
        self.is_selecting = False
        self.start_point = None
        self.current_rect = None

        # 半透明黑色背景
        self.mask_color = QColor(0, 0, 0, 120)  # RGBA

        # 红色边框
        self.border_pen = QPen(QColor(255, 0, 0), 2)

        print("📸 框选工具已启动,请拖动鼠标选择区域 (按ESC取消)")

    def _setup_fullscreen_geometry(self):
        """设置全屏几何信息，覆盖所有屏幕"""
        # 获取系统DPI缩放因子
        try:
            user32 = ctypes.windll.user32
            dpi = user32.GetDpiForSystem()
            dpi_scale = dpi / 96.0
        except:
            dpi_scale = 1.0

        # 获取所有屏幕
        app = QApplication.instance()
        screens = app.screens()

        if not screens:
            # 降级到主屏幕
            screen = QApplication.primaryScreen()
            self.screen_geometry = screen.geometry()
            self.setGeometry(self.screen_geometry)
            return

        # 计算所有屏幕的联合边界（物理像素）
        if len(screens) == 1:
            # 单屏幕直接使用
            self.screen_geometry = screens[0].geometry()
        else:
            # 多屏幕：计算所有屏幕的联合边界
            min_x = float('inf')
            min_y = float('inf')
            max_x = float('-inf')
            max_y = float('-inf')

            for screen in screens:
                geo = screen.geometry()
                min_x = min(min_x, geo.x())
                min_y = min(min_y, geo.y())
                max_x = max(max_x, geo.x() + geo.width())
                max_y = max(max_y, geo.y() + geo.height())

            self.screen_geometry = QRect(int(min_x), int(min_y),
                                        int(max_x - min_x), int(max_y - min_y))

        # 设置窗口几何信息（全屏覆盖）
        self.setGeometry(self.screen_geometry)
        print(f"📐 屏幕几何信息(物理像素): {self.screen_geometry}")
        print(f"   DPI缩放因子: {dpi_scale:.2f}")
        print(f"   屏幕数量: {len(screens)}")
    
    def paintEvent(self, event):
        """绘制半透明遮罩和选择框"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制半透明遮罩
        painter.fillRect(self.rect(), self.mask_color)
        
        # 如果正在选择,绘制选择框
        if self.current_rect and not self.current_rect.isNull():
            # 清除选择框内的遮罩(显示原始内容)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(self.current_rect, Qt.transparent)
            
            # 绘制红色边框
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setPen(self.border_pen)
            painter.drawRect(self.current_rect)
    
    def mousePressEvent(self, event):
        """鼠标按下 - 开始框选"""
        if event.button() == Qt.LeftButton:
            self.is_selecting = True
            self.start_point = event.position().toPoint()
            self.current_rect = QRect(self.start_point, self.start_point)
            self.update()
    
    def mouseMoveEvent(self, event):
        """鼠标移动 - 更新选择框"""
        if self.is_selecting:
            self.current_rect = QRect(self.start_point, event.position().toPoint()).normalized()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放 - 完成框选"""
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False

            if self.current_rect and not self.current_rect.isNull():
                # 确保区域有效
                rect = self.current_rect.normalized()
                if rect.width() > 10 and rect.height() > 10:  # 最小尺寸限制
                    # 注意：返回的是相对于窗口的坐标（屏幕坐标）
                    # 窗口位置是 screen_geometry 的左上角
                    global_x = self.screen_geometry.x() + rect.x()
                    global_y = self.screen_geometry.y() + rect.y()
                    print(f"[OK] Selection: x={global_x}, y={global_y}, w={rect.width()}, h={rect.height()}")
                    print(f"   窗口几何: {self.screen_geometry}")
                    self.region_selected.emit(global_x, global_y, rect.width(), rect.height())
                else:
                    print("[WARN] Selection too small, cancelled")
                    self.selection_cancelled.emit()
            else:
                self.selection_cancelled.emit()

            self.close()
    
    def keyPressEvent(self, event):
        """按键事件 - ESC取消"""
        if event.key() == Qt.Key_Escape:
            print("❌ 框选已取消")
            self.selection_cancelled.emit()
            self.close()


def capture_screen_region(x, y, width, height):
    """截取指定区域的屏幕截图"""
    app = QApplication.instance() or QApplication(sys.argv)
    screen = QApplication.primaryScreen()
    
    # 截取整个屏幕
    pixmap = screen.grabWindow(0, x, y, width, height)
    
    if pixmap.isNull():
        print("❌ 截图失败")
        return None
    
    # 转换为OpenCV格式
    image = pixmap.toImage()
    w = image.width()
    h = image.height()
    
    # 转换为numpy数组
    ptr = image.bits()
    arr = np.frombuffer(ptr, np.uint8).reshape((h, w, 4))
    
    # BGRA -> BGR
    bgr_image = arr[:, :, :3].copy()
    
    print(f"[OK] Screenshot: {w}x{h}")
    return bgr_image


if __name__ == "__main__":
    import numpy as np
    
    app = QApplication(sys.argv)
    selector = ScreenSelector()
    
    def on_region_selected(x, y, w, h):
        print(f"框选完成: ({x}, {y}, {w}, {h})")
        # 截取区域
        screenshot = capture_screen_region(x, y, w, h)
        if screenshot is not None:
            print(f"截图形状: {screenshot.shape}")
        QApplication.quit()
    
    def on_cancelled():
        print("框选已取消")
        QApplication.quit()
    
    selector.region_selected.connect(on_region_selected)
    selector.selection_cancelled.connect(on_cancelled)
    selector.show()
    
    sys.exit(app.exec())
