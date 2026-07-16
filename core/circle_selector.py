"""
圆形框选工具 - 全屏透明覆盖层框选游戏区域
"""
import sys
import ctypes

# 设置DPI感知（必须在导入Qt之前）
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
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QFont


class CircleSelector(QWidget):
    """全屏透明覆盖层,用于鼠标框选圆形区域"""

    # 信号: 框选完成,返回区域坐标(x, y, width, height)
    region_selected = Signal(int, int, int, int)
    selection_cancelled = Signal()

    def __init__(self):
        super().__init__()

        # 设置为全屏、无边框、置顶
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Window
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # 设置全屏大小
        self._setup_fullscreen_geometry()

        # 框选状态
        self.center_pos = QPoint()
        self.radius = 0
        self.is_dragging = False
        self.is_moving = False
        self.drag_start_pos = QPoint()
        
        # 按钮区域
        self.confirm_button_rect = None
        self.cancel_button_rect = None

        print("🔵 圆形框选工具已启动,点击并拖动创建圆形区域 (按ESC取消)")

    def _setup_fullscreen_geometry(self):
        """设置全屏几何信息，覆盖所有屏幕"""
        app = QApplication.instance()
        screen = app.primaryScreen()
        self.screen_geometry = screen.geometry()
        self.setGeometry(self.screen_geometry)
        print(f"📐 屏幕几何信息: {self.screen_geometry}")
    
    def paintEvent(self, event):
        """绘制半透明遮罩、圆形选框和操作按钮"""
        print(f"🔵 paintEvent called - radius: {self.radius}, center: {self.center_pos}")
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制半透明遮罩
        painter.fillRect(self.rect(), QColor(0, 0, 0, 150))
        
        # 如果有圆形，绘制选框
        if self.radius > 0:
            # 创建圆形路径
            path = QPainterPath()
            path.addEllipse(self.center_pos, self.radius, self.radius)
            
            # 使用路径进行镂空（显示原始画面）
            painter.setClipPath(path, Qt.IntersectClip)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(self.rect(), Qt.transparent)
            painter.setClipping(False)
            
            # 恢复正常绘制模式
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            
            # 绘制蓝色边框（三层效果）
            # 外层阴影
            painter.setPen(QPen(QColor(30, 64, 175), 6))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(self.center_pos, self.radius + 1, self.radius + 1)
            # 主边框（蓝色）
            painter.setPen(QPen(QColor(59, 130, 246), 4))
            painter.drawEllipse(self.center_pos, self.radius, self.radius)
            # 内层高光
            painter.setPen(QPen(Qt.white, 1))
            painter.drawEllipse(self.center_pos, self.radius - 1, self.radius - 1)
            
            # 绘制底部白色操作栏
            bar_height = 60
            bar_width = 300
            bar_x = self.center_pos.x() - bar_width // 2
            bar_y = self.center_pos.y() + self.radius + 20
            
            # 确保操作栏不超出屏幕
            screen = QApplication.primaryScreen().geometry()
            if bar_y + bar_height > screen.bottom():
                bar_y = screen.bottom() - bar_height - 10
            if bar_x < 10:
                bar_x = 10
            if bar_x + bar_width > screen.right():
                bar_x = screen.right() - bar_width - 10
            
            # 绘制白色背景栏
            bar_rect = QRect(bar_x, bar_y, bar_width, bar_height)
            painter.setPen(QPen(QColor(200, 200, 200), 2))
            painter.setBrush(QColor(255, 255, 255, 240))
            painter.drawRoundedRect(bar_rect, 10, 10)
            
            # 绘制红色X按钮（左侧）
            button_size = 40
            button_margin = 10
            cancel_x = bar_x + button_margin
            cancel_y = bar_y + (bar_height - button_size) // 2
            cancel_rect = QRect(cancel_x, cancel_y, button_size, button_size)
            
            painter.setBrush(QColor(239, 68, 68, 220))
            painter.setPen(QPen(QColor(239, 68, 68), 2))
            painter.drawRoundedRect(cancel_rect, 8, 8)
            
            # 绘制X符号
            painter.setPen(QPen(Qt.white, 3))
            painter.drawLine(cancel_rect.left() + 12, cancel_rect.top() + 12,
                           cancel_rect.right() - 12, cancel_rect.bottom() - 12)
            painter.drawLine(cancel_rect.left() + 12, cancel_rect.bottom() - 12,
                           cancel_rect.right() - 12, cancel_rect.top() + 12)
            
            # 绘制大小调整控件（中间）
            size_ctrl_width = 90
            size_ctrl_height = 30
            size_ctrl_x = bar_x + (bar_width - size_ctrl_width) // 2
            size_ctrl_y = bar_y + (bar_height - size_ctrl_height) // 2
            
            # 减小按钮
            minus_btn_rect = QRect(size_ctrl_x, size_ctrl_y, 28, size_ctrl_height)
            painter.setBrush(QColor(100, 100, 100, 220))
            painter.setPen(QPen(QColor(80, 80, 80), 1))
            painter.drawRoundedRect(minus_btn_rect, 5, 5)
            painter.setPen(QPen(Qt.white, 2))
            painter.drawLine(minus_btn_rect.left() + 8, minus_btn_rect.center().y(),
                           minus_btn_rect.right() - 8, minus_btn_rect.center().y())
            
            # 大小显示区域
            display_rect = QRect(size_ctrl_x + 28, size_ctrl_y, 34, size_ctrl_height)
            painter.setBrush(QColor(240, 240, 240, 220))
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.drawRoundedRect(display_rect, 5, 5)
            
            # 显示当前大小
            painter.setPen(QColor(60, 60, 60))
            font = painter.font()
            font.setPointSize(11)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(display_rect, Qt.AlignCenter, str(self.radius))
            
            # 增大按钮
            plus_btn_rect = QRect(size_ctrl_x + 62, size_ctrl_y, 28, size_ctrl_height)
            painter.setBrush(QColor(59, 130, 246, 220))
            painter.setPen(QPen(QColor(40, 100, 200), 1))
            painter.drawRoundedRect(plus_btn_rect, 5, 5)
            painter.setPen(QPen(Qt.white, 2))
            painter.drawLine(plus_btn_rect.left() + 8, plus_btn_rect.center().y(),
                           plus_btn_rect.right() - 8, plus_btn_rect.center().y())
            painter.drawLine(plus_btn_rect.center().x(), plus_btn_rect.top() + 8,
                           plus_btn_rect.center().x(), plus_btn_rect.bottom() - 8)
            
            # 绘制绿色勾按钮（右侧）
            confirm_x = bar_x + bar_width - button_margin - button_size
            confirm_y = bar_y + (bar_height - button_size) // 2
            confirm_rect = QRect(confirm_x, confirm_y, button_size, button_size)
            
            painter.setBrush(QColor(34, 197, 94, 220))
            painter.setPen(QPen(QColor(34, 197, 94), 2))
            painter.drawRoundedRect(confirm_rect, 8, 8)
            
            # 绘制勾符号
            painter.setPen(QPen(Qt.white, 3))
            check_path = QPainterPath()
            check_path.moveTo(confirm_rect.left() + 10, confirm_rect.center().y())
            check_path.lineTo(confirm_rect.center().x() - 3, confirm_rect.bottom() - 12)
            check_path.lineTo(confirm_rect.right() - 10, confirm_rect.top() + 12)
            painter.drawPath(check_path)
            
            # 保存按钮位置用于点击检测
            self.confirm_button_rect = confirm_rect
            self.cancel_button_rect = cancel_rect
            self.minus_button_rect = minus_btn_rect
            self.plus_button_rect = plus_btn_rect
            
            # 绘制提示文字
            painter.setPen(QColor(255, 255, 255))
            font = painter.font()
            font.setPointSize(11)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignHCenter, 
                           "拖动圆形边框移动 | 点击外部重新框选")
        else:
            # 没有圆形时，显示初始提示
            painter.setPen(QColor(255, 255, 255))
            font = painter.font()
            font.setPointSize(14)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, "点击并拖动创建圆形框选区域")
            print("🔵 Drew initial hint text")
    
    def mousePressEvent(self, event):
        print(f"🔵 mousePressEvent - pos: {event.pos()}, button: {event.button()}")
        
        if event.button() == Qt.LeftButton:
            # 检查是否点击了确认按钮
            if self.confirm_button_rect is not None and self.confirm_button_rect.contains(event.pos()):
                rect = QRect(
                    self.center_pos.x() - self.radius,
                    self.center_pos.y() - self.radius,
                    self.radius * 2,
                    self.radius * 2
                )
                global_x = self.screen_geometry.x() + rect.x()
                global_y = self.screen_geometry.y() + rect.y()
                print(f"[OK] Selection: ({global_x}, {global_y}, {rect.width()}, {rect.height()})")
                self.region_selected.emit(global_x, global_y, rect.width(), rect.height())
                self.close()
                return
            
            # 检查是否点击了取消按钮
            if self.cancel_button_rect is not None and self.cancel_button_rect.contains(event.pos()):
                print("❌ 框选已取消")
                self.selection_cancelled.emit()
                self.close()
                return
            
            # 检查是否点击了减小按钮
            if getattr(self, 'minus_button_rect', None) is not None and self.minus_button_rect.contains(event.pos()):
                self.radius = max(10, self.radius - 20)
                print(f"🔵 减小半径: {self.radius}")
                self.update()
                return
            
            # 检查是否点击了增大按钮
            if getattr(self, 'plus_button_rect', None) is not None and self.plus_button_rect.contains(event.pos()):
                self.radius = min(500, self.radius + 20)
                print(f"🔵 增大半径: {self.radius}")
                self.update()
                return
            
            # 检查是否点击在圆形边框上（用于移动）
            if self.radius > 0:
                dx = event.pos().x() - self.center_pos.x()
                dy = event.pos().y() - self.center_pos.y()
                distance = (dx**2 + dy**2)**0.5
                # 检查是否在边框附近（15像素范围内）
                if abs(distance - self.radius) < 15:
                    self.is_moving = True
                    self.is_dragging = False
                    self.drag_start_pos = event.pos()
                    self.setCursor(Qt.SizeAllCursor)
                    return
            
            # 开始新的框选
            self.center_pos = event.pos()
            self.radius = 0
            self.is_dragging = True
            self.is_moving = False
            self.confirm_button_rect = None
            self.cancel_button_rect = None
            self.minus_button_rect = None
            self.plus_button_rect = None
            self.update()
    
    def mouseMoveEvent(self, event):
        if self.is_dragging:
            # 计算半径
            dx = event.pos().x() - self.center_pos.x()
            dy = event.pos().y() - self.center_pos.y()
            self.radius = int((dx**2 + dy**2)**0.5)
            print(f"🔵 Dragging - new radius: {self.radius}")
            self.update()
        elif self.is_moving:
            # 移动圆形
            delta = event.pos() - self.drag_start_pos
            self.center_pos += delta
            self.drag_start_pos = event.pos()
            print(f"🔵 Moving - new center: {self.center_pos}")
            self.update()
        else:
            # 检查鼠标是否在边框上
            if self.radius > 0:
                dx = event.pos().x() - self.center_pos.x()
                dy = event.pos().y() - self.center_pos.y()
                distance = (dx**2 + dy**2)**0.5
                if abs(distance - self.radius) < 15:
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
        """按键事件 - ESC取消"""
        if event.key() == Qt.Key_Escape:
            print("❌ 框选已取消")
            self.selection_cancelled.emit()
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    selector = CircleSelector()
    
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