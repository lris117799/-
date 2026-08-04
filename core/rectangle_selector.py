"""
矩形框选工具 - 全屏透明覆盖层框选游戏区域
基于 CircleSelector 改造，圆形改为方形
"""
import sys
import ctypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    print("DPI awareness set: Per Monitor V2")
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        print("DPI awareness set: System DPI Aware")
    except:
        print("Could not set DPI awareness")

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QRect, QRectF, QPoint, Signal
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QFont


class RectangleSelector(QWidget):
    """全屏透明覆盖层,用于鼠标框选矩形区域"""

    region_selected = Signal(int, int, int, int)
    selection_cancelled = Signal()

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Window
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self._setup_fullscreen_geometry()

        self.rect_start = QPoint()
        self.rect_end = QPoint()
        self.is_dragging = False
        self.is_moving = False
        self.drag_start_pos = QPoint()

        self.confirm_button_rect = None
        self.cancel_button_rect = None

        self.rect_size = 0

        print("矩形框选工具已启动,点击并拖动创建矩形区域 (按ESC取消)")

    def _setup_fullscreen_geometry(self):
        """设置全屏几何信息，覆盖所有屏幕，支持多屏幕和DPI缩放"""
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

    def _get_rect(self):
        if self.rect_start.isNull() or self.rect_end.isNull():
            return None
        return QRect(self.rect_start, self.rect_end).normalized()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))

        rect = self._get_rect()

        if rect and rect.width() > 0 and rect.height() > 0:
            path = QPainterPath()
            path.addRect(QRectF(rect))
            painter.setClipPath(path, Qt.IntersectClip)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(self.rect(), Qt.transparent)
            painter.setClipping(False)

            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            painter.setPen(QPen(QColor(30, 64, 175), 6))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect.adjusted(-1, -1, 1, 1))

            painter.setPen(QPen(QColor(59, 130, 246), 4))
            painter.drawRect(rect)

            painter.setPen(QPen(Qt.white, 1))
            painter.drawRect(rect.adjusted(1, 1, -1, -1))

            bar_height = 60
            bar_width = 300
            bar_x = rect.center().x() - bar_width // 2
            bar_y = rect.bottom() + 20

            screen = QApplication.primaryScreen().geometry()
            if bar_y + bar_height > screen.bottom():
                bar_y = screen.bottom() - bar_height - 10
            if bar_x < 10:
                bar_x = 10
            if bar_x + bar_width > screen.right():
                bar_x = screen.right() - bar_width - 10

            bar_rect = QRect(bar_x, bar_y, bar_width, bar_height)
            painter.setPen(QPen(QColor(200, 200, 200), 2))
            painter.setBrush(QColor(255, 255, 255, 240))
            painter.drawRoundedRect(bar_rect, 10, 10)

            button_size = 40
            button_margin = 10

            cancel_x = bar_x + button_margin
            cancel_y = bar_y + (bar_height - button_size) // 2
            cancel_rect = QRect(cancel_x, cancel_y, button_size, button_size)

            painter.setBrush(QColor(239, 68, 68, 220))
            painter.setPen(QPen(QColor(239, 68, 68), 2))
            painter.drawRoundedRect(cancel_rect, 8, 8)

            painter.setPen(QPen(Qt.white, 3))
            painter.drawLine(cancel_rect.left() + 12, cancel_rect.top() + 12,
                           cancel_rect.right() - 12, cancel_rect.bottom() - 12)
            painter.drawLine(cancel_rect.left() + 12, cancel_rect.bottom() - 12,
                           cancel_rect.right() - 12, cancel_rect.top() + 12)

            size_ctrl_width = 90
            size_ctrl_height = 30
            size_ctrl_x = bar_x + (bar_width - size_ctrl_width) // 2
            size_ctrl_y = bar_y + (bar_height - size_ctrl_height) // 2

            minus_btn_rect = QRect(size_ctrl_x, size_ctrl_y, 28, size_ctrl_height)
            painter.setBrush(QColor(100, 100, 100, 220))
            painter.setPen(QPen(QColor(80, 80, 80), 1))
            painter.drawRoundedRect(minus_btn_rect, 5, 5)
            painter.setPen(QPen(Qt.white, 2))
            painter.drawLine(minus_btn_rect.left() + 8, minus_btn_rect.center().y(),
                           minus_btn_rect.right() - 8, minus_btn_rect.center().y())

            display_rect = QRect(size_ctrl_x + 28, size_ctrl_y, 34, size_ctrl_height)
            painter.setBrush(QColor(240, 240, 240, 220))
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.drawRoundedRect(display_rect, 5, 5)

            painter.setPen(QColor(60, 60, 60))
            font = painter.font()
            font.setPointSize(11)
            font.setBold(True)
            painter.setFont(font)
            size_text = f"{rect.width()}x{rect.height()}"
            painter.drawText(display_rect, Qt.AlignCenter, size_text)

            plus_btn_rect = QRect(size_ctrl_x + 62, size_ctrl_y, 28, size_ctrl_height)
            painter.setBrush(QColor(59, 130, 246, 220))
            painter.setPen(QPen(QColor(40, 100, 200), 1))
            painter.drawRoundedRect(plus_btn_rect, 5, 5)
            painter.setPen(QPen(Qt.white, 2))
            painter.drawLine(plus_btn_rect.left() + 8, plus_btn_rect.center().y(),
                           plus_btn_rect.right() - 8, plus_btn_rect.center().y())
            painter.drawLine(plus_btn_rect.center().x(), plus_btn_rect.top() + 8,
                           plus_btn_rect.center().x(), plus_btn_rect.bottom() - 8)

            confirm_x = bar_x + bar_width - button_margin - button_size
            confirm_y = bar_y + (bar_height - button_size) // 2
            confirm_rect = QRect(confirm_x, confirm_y, button_size, button_size)

            painter.setBrush(QColor(34, 197, 94, 220))
            painter.setPen(QPen(QColor(34, 197, 94), 2))
            painter.drawRoundedRect(confirm_rect, 8, 8)

            painter.setPen(QPen(Qt.white, 3))
            check_path = QPainterPath()
            check_path.moveTo(confirm_rect.left() + 10, confirm_rect.center().y())
            check_path.lineTo(confirm_rect.center().x() - 3, confirm_rect.bottom() - 12)
            check_path.lineTo(confirm_rect.right() - 10, confirm_rect.top() + 12)
            painter.drawPath(check_path)

            self.confirm_button_rect = confirm_rect
            self.cancel_button_rect = cancel_rect
            self.minus_button_rect = minus_btn_rect
            self.plus_button_rect = plus_btn_rect

            painter.setPen(QColor(255, 255, 255))
            font = painter.font()
            font.setPointSize(11)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignHCenter,
                           "拖动矩形边框移动 | 点击外部重新框选")
        else:
            painter.setPen(QColor(255, 255, 255))
            font = painter.font()
            font.setPointSize(14)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, "点击并拖动创建矩形框选区域")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.confirm_button_rect is not None and self.confirm_button_rect.contains(event.pos()):
                rect = self._get_rect()
                if rect:
                    global_x = self.screen_geometry.x() + rect.x()
                    global_y = self.screen_geometry.y() + rect.y()
                    print(f"框选完成: ({global_x}, {global_y}, {rect.width()}, {rect.height()})")
                    self.region_selected.emit(global_x, global_y, rect.width(), rect.height())
                    self.close()
                return

            if self.cancel_button_rect is not None and self.cancel_button_rect.contains(event.pos()):
                print("框选已取消")
                self.selection_cancelled.emit()
                self.close()
                return

            if getattr(self, 'minus_button_rect', None) is not None and self.minus_button_rect.contains(event.pos()):
                rect = self._get_rect()
                if rect:
                    new_rect = rect.adjusted(10, 10, -10, -10)
                    if new_rect.width() > 20 and new_rect.height() > 20:
                        self.rect_start = new_rect.topLeft()
                        self.rect_end = new_rect.bottomRight()
                        print(f"缩小矩形: {new_rect.width()}x{new_rect.height()}")
                        self.update()
                return

            if getattr(self, 'plus_button_rect', None) is not None and self.plus_button_rect.contains(event.pos()):
                rect = self._get_rect()
                if rect:
                    new_rect = rect.adjusted(-10, -10, 10, 10)
                    self.rect_start = new_rect.topLeft()
                    self.rect_end = new_rect.bottomRight()
                    print(f"放大矩形: {new_rect.width()}x{new_rect.height()}")
                    self.update()
                return

            rect = self._get_rect()
            if rect and rect.width() > 0 and rect.height() > 0:
                margin = 15
                on_border = (
                    abs(event.pos().x() - rect.left()) < margin or
                    abs(event.pos().x() - rect.right()) < margin or
                    abs(event.pos().y() - rect.top()) < margin or
                    abs(event.pos().y() - rect.bottom()) < margin
                )
                if on_border:
                    self.is_moving = True
                    self.is_dragging = False
                    self.drag_start_pos = event.pos()
                    self.setCursor(Qt.SizeAllCursor)
                    return

            self.rect_start = event.pos()
            self.rect_end = event.pos()
            self.is_dragging = True
            self.is_moving = False
            self.confirm_button_rect = None
            self.cancel_button_rect = None
            self.minus_button_rect = None
            self.plus_button_rect = None
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self.rect_end = event.pos()
            self.update()
        elif self.is_moving:
            delta = event.pos() - self.drag_start_pos
            self.rect_start += delta
            self.rect_end += delta
            self.drag_start_pos = event.pos()
            self.update()
        else:
            rect = self._get_rect()
            if rect and rect.width() > 0 and rect.height() > 0:
                margin = 15
                on_border = (
                    abs(event.pos().x() - rect.left()) < margin or
                    abs(event.pos().x() - rect.right()) < margin or
                    abs(event.pos().y() - rect.top()) < margin or
                    abs(event.pos().y() - rect.bottom()) < margin
                )
                if on_border:
                    self.setCursor(Qt.SizeAllCursor)
                else:
                    self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.is_moving = False
            self.setCursor(Qt.ArrowCursor)
            self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            print("框选已取消")
            self.selection_cancelled.emit()
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    selector = RectangleSelector()

    def on_region_selected(x, y, w, h):
        print(f"框选完成 (屏幕坐标): ({x}, {y}, {w}, {h})")
        QApplication.quit()

    def on_cancelled():
        print("框选已取消")
        QApplication.quit()

    selector.region_selected.connect(on_region_selected)
    selector.selection_cancelled.connect(on_cancelled)
    selector.show()

    sys.exit(app.exec())