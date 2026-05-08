"""
ROI框选工具 - 独立测试版本
使用纯Win32 API获取鼠标坐标，避免Qt DPI缩放问题
"""
import sys
import ctypes

# 设置DPI感知（必须在导入Qt之前）
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    print("✅ 已设置DPI感知: Per Monitor V2")
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        print("✅ 已设置DPI感知: System DPI Aware")
    except:
        print("⚠️ 无法设置DPI感知")

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QPixmap


class ROISelector(QWidget):
    """ROI框选窗口 - 使用物理像素坐标"""
    
    def __init__(self):
        super().__init__()
        
        # 全屏无边框置顶
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setCursor(Qt.CrossCursor)
        
        # 截取全屏背景
        screen = QApplication.primaryScreen()
        self.screen_geometry = screen.geometry()
        self.pixmap = screen.grabWindow(0)
        self.setGeometry(self.screen_geometry)
        
        # 框选状态（使用物理像素）
        self.is_selecting = False
        self.start_x = 0
        self.start_y = 0
        self.current_x = 0
        self.current_y = 0
        
        print(f"📐 屏幕尺寸(逻辑): {self.screen_geometry.width()}x{self.screen_geometry.height()}")
    
    def _get_mouse_pos(self):
        """使用Win32 API获取鼠标物理像素坐标"""
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景截图
        painter.drawPixmap(0, 0, self.pixmap)
        
        # 半透明遮罩
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))
        
        if self.is_selecting:
            # 计算矩形（确保正确的顺序）
            x1 = min(self.start_x, self.current_x)
            y1 = min(self.start_y, self.current_y)
            x2 = max(self.start_x, self.current_x)
            y2 = max(self.start_y, self.current_y)
            
            rect_width = x2 - x1
            rect_height = y2 - y1
            
            if rect_width > 0 and rect_height > 0:
                rect = QRect(x1, y1, rect_width, rect_height)
                
                # 清除框选区域的遮罩（显示原图）
                painter.setCompositionMode(QPainter.CompositionMode_Clear)
                painter.fillRect(rect, Qt.transparent)
                painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                
                # 绘制边框
                pen = QPen(QColor(0, 150, 255), 2)
                painter.setPen(pen)
                painter.drawRect(rect)
                
                # 填充半透明蓝色
                brush = QBrush(QColor(0, 150, 255, 30))
                painter.setBrush(brush)
                painter.drawRect(rect)
                
                # 显示尺寸信息
                size_text = f"{rect_width} x {rect_height}"
                painter.setPen(QPen(QColor(255, 255, 255)))
                font = painter.font()
                font.setBold(True)
                font.setPointSize(12)
                painter.setFont(font)
                
                # 在框选区域上方显示尺寸
                text_rect = painter.boundingRect(rect.adjusted(0, -30, 0, 0), Qt.AlignCenter, size_text)
                painter.fillRect(text_rect.adjusted(-5, -2, 5, 2), QColor(0, 0, 0, 180))
                painter.drawText(rect.adjusted(0, -30, 0, 0), Qt.AlignCenter, size_text)
    
    def mousePressEvent(self, event):
        """鼠标按下"""
        if event.button() == Qt.LeftButton:
            self.is_selecting = True
            self.start_x, self.start_y = self._get_mouse_pos()
            self.current_x, self.current_y = self.start_x, self.start_y
            print(f"\n🐭 鼠标按下(物理像素): ({self.start_x}, {self.start_y})")
            self.update()
        elif event.button() == Qt.RightButton:
            self.close()
    
    def mouseMoveEvent(self, event):
        """鼠标移动"""
        if self.is_selecting:
            self.current_x, self.current_y = self._get_mouse_pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            
            # 计算框选区域
            x1 = min(self.start_x, self.current_x)
            y1 = min(self.start_y, self.current_y)
            x2 = max(self.start_x, self.current_x)
            y2 = max(self.start_y, self.current_y)
            
            w = x2 - x1
            h = y2 - y1
            
            if w > 10 and h > 10:
                # 输出结果（物理像素坐标）
                print(f"\n{'='*50}")
                print(f"框选区域(物理像素):")
                print(f"  左上角: ({x1}, {y1})")
                print(f"  宽高: {w} x {h}")
                print(f"  ROI元组: ({x1}, {y1}, {w}, {h})")
                print(f"{'='*50}\n")
                
                # 复制到剪贴板
                clipboard = QApplication.clipboard()
                roi_str = f"({x1}, {y1}, {w}, {h})"
                clipboard.setText(roi_str)
                print(f"已复制到剪贴板: {roi_str}")
                
                self.close()
            else:
                print("框选区域太小，请重新选择")
                self.update()
    
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key_Escape:
            self.close()


def main():
    app = QApplication(sys.argv)
    
    print("=" * 50)
    print("ROI框选工具（物理像素版本）")
    print("=" * 50)
    print("使用说明:")
    print("  1. 左键拖动框选区域")
    print("  2. 释放左键确认选择")
    print("  3. 右键或ESC取消")
    print("  4. 结果会自动复制到剪贴板")
    print("=" * 50)
    print("\n启动框选工具...")
    
    selector = ROISelector()
    selector.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
