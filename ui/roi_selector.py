"""
ROI框选工具 - 覆盖游戏窗口客户区
使用Qt事件坐标获取逻辑像素，然后转换为物理像素
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
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QBrush


class ROISelector(QWidget):
    """ROI框选窗口 - 覆盖游戏窗口，返回物理像素坐标"""
    
    region_selected = Signal(int, int, int, int)
    selection_cancelled = Signal()
    
    def __init__(self, target_window_title="洛克王国：世界"):
        super().__init__()
        
        self.target_window_title = target_window_title
        self.hwnd = None
        self.main_hwnd = None
        self.client_info = None
        self.dpi_scale = 1.0
        
        # 设置窗口属性 - 透明覆盖层
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        # 框选状态（使用逻辑像素）
        self.is_selecting = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        
        # 查找目标窗口并设置窗口位置和大小
        self.find_window()
        
        print(f"📸 框选工具已启动，请在游戏窗口内拖动鼠标选择区域 (按ESC取消)")
    
    def _get_dpi_scale(self, hwnd):
        """获取DPI缩放因子"""
        try:
            dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
            return dpi / 96.0
        except:
            pass
        
        try:
            scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0)
            return scale_factor / 100.0
        except:
            pass
        
        return 1.0
    
    def find_window(self):
        """查找游戏窗口"""
        import win32gui
        import win32process
        import psutil
        import win32con
        
        try:
            # 通过进程名找到PID
            target_pid = None
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] == 'NRC-Win64-Shipping.exe':
                        target_pid = proc.info['pid']
                        print(f"✅ 找到游戏进程: PID={target_pid}")
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not target_pid:
                print(f"❌ 未找到NRC-Win64-Shipping.exe进程")
                return
            
            # 查找窗口
            self.main_hwnd = win32gui.FindWindow(None, self.target_window_title)
            
            if self.main_hwnd == 0:
                def callback(hwnd, extra):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if self.target_window_title in title:
                            try:
                                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                                if pid == target_pid:
                                    extra.append(hwnd)
                                    return False
                            except:
                                pass
                    return True
                
                matched_hwnds = []
                win32gui.EnumWindows(callback, matched_hwnds)
                if matched_hwnds:
                    self.main_hwnd = matched_hwnds[0]
            
            if self.main_hwnd != 0:
                print(f"✅ 找到游戏窗口: HWND={self.main_hwnd}")
                
                # 查找子窗口（游戏主渲染窗口）
                def find_child(hwnd, extra):
                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                    if style & win32con.WS_CHILD:
                        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                        width = right - left
                        height = bottom - top
                        if width > 100 and height > 100:
                            extra.append(hwnd)
                    return True
                
                child_windows = []
                win32gui.EnumChildWindows(self.main_hwnd, find_child, child_windows)
                
                if child_windows:
                    child_windows.sort(
                        key=lambda h: (lambda r: (r[2]-r[0])*(r[3]-r[1]))(win32gui.GetWindowRect(h)),
                        reverse=True
                    )
                    print(f"🔍 找到 {len(child_windows)} 个子窗口，使用最大的")
                    self.hwnd = child_windows[0]
                else:
                    self.hwnd = self.main_hwnd
            else:
                print(f"❌ 未找到游戏窗口")
                
        except Exception as e:
            print(f"❌ 查找窗口失败: {e}")
            import traceback
            traceback.print_exc()
        
        if self.main_hwnd != 0:
            self._update_client_info()
    
    def _update_client_info(self):
        """更新窗口信息（使用窗口矩形）"""
        import win32gui

        try:
            # 获取窗口矩形（物理像素）
            win_left, win_top, win_right, win_bottom = win32gui.GetWindowRect(self.main_hwnd)
            physical_width = win_right - win_left
            physical_height = win_bottom - win_top

            # 获取DPI缩放因子
            self.dpi_scale = self._get_dpi_scale(self.main_hwnd)

            # 转换为逻辑像素
            logical_left = int(win_left / self.dpi_scale)
            logical_top = int(win_top / self.dpi_scale)
            logical_width = int(physical_width / self.dpi_scale)
            logical_height = int(physical_height / self.dpi_scale)

            # 保存窗口信息
            self.client_info = {
                'left_physical': win_left,
                'top_physical': win_top,
                'left_logical': logical_left,
                'top_logical': logical_top,
                'width_physical': physical_width,
                'height_physical': physical_height,
                'width_logical': logical_width,
                'height_logical': logical_height,
                'dpi_scale': self.dpi_scale
            }

            # 设置窗口位置和大小为窗口矩形（逻辑像素）
            self.setGeometry(logical_left, logical_top, logical_width, logical_height)

            print(f"\n📐 游戏窗口信息:")
            print(f"   DPI缩放: {self.dpi_scale:.2f}x")
            print(f"   物理位置: ({win_left}, {win_top})")
            print(f"   物理尺寸: {physical_width}x{physical_height}")
            print(f"   逻辑位置: ({logical_left}, {logical_top})")
            print(f"   逻辑尺寸: {logical_width}x{logical_height}")

        except Exception as e:
            print(f"⚠️ 更新窗口信息失败: {e}")
            import traceback
            traceback.print_exc()
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        
        # 绘制半透明黑色遮罩
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        # 绘制选择框
        if self.is_selecting and not self.start_point.isNull() and not self.end_point.isNull():
            rect = QRect(self.start_point, self.end_point).normalized()
            
            if rect.width() > 0 and rect.height() > 0:
                painter.setBrush(QBrush(QColor(0, 120, 215, 50)))
                painter.setPen(QPen(QColor(0, 120, 215), 2))
                painter.drawRect(rect)
                
                size_text = f"{rect.width()} x {rect.height()}"
                text_rect = painter.boundingRect(rect.adjusted(5, 5, 0, 0), Qt.AlignLeft, size_text)
                
                painter.fillRect(text_rect.adjusted(-3, -2, 3, 2), QColor(0, 0, 0, 160))
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.drawText(text_rect, Qt.AlignLeft, size_text)
    
    def mousePressEvent(self, event):
        """鼠标按下"""
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.end_point = self.start_point
            self.is_selecting = True
            self.update()
        elif event.button() == Qt.RightButton:
            self.close()
    
    def mouseMoveEvent(self, event):
        """鼠标移动"""
        if self.is_selecting:
            self.end_point = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False

            x1, y1 = self.start_point.x(), self.start_point.y()
            x2, y2 = self.end_point.x(), self.end_point.y()

            rx = min(x1, x2)
            ry = min(y1, y2)
            rw = abs(x2 - x1)
            rh = abs(y2 - y1)

            if rw > 10 and rh > 10:
                # 转换为物理像素坐标（与截图匹配）
                if self.client_info:
                    dpi_scale = self.client_info['dpi_scale']

                    # 鼠标坐标是窗口内逻辑坐标
                    # 先转换为窗口内物理像素，再加上窗口的物理偏移量
                    inner_physical_x = int(rx * dpi_scale)
                    inner_physical_y = int(ry * dpi_scale)
                    inner_physical_w = int(rw * dpi_scale)
                    inner_physical_h = int(rh * dpi_scale)

                    # 加上窗口的物理偏移量得到屏幕物理坐标
                    client_x = self.client_info['left_physical'] + inner_physical_x
                    client_y = self.client_info['top_physical'] + inner_physical_y
                    client_w = inner_physical_w
                    client_h = inner_physical_h

                    print(f"\n✅ 框选完成(屏幕物理像素): ({client_x}, {client_y}, {client_w}, {client_h})")
                    print(f"   窗口内逻辑坐标: ({rx}, {ry}, {rw}, {rh})")
                    print(f"   窗口物理偏移: ({self.client_info['left_physical']}, {self.client_info['top_physical']})")
                    print(f"   DPI缩放: {dpi_scale:.2f}x")

                    self.region_selected.emit(client_x, client_y, client_w, client_h)
                else:
                    print(f"\n⚠️ 无法获取窗口信息，使用逻辑坐标: ({rx}, {ry}, {rw}, {rh})")
                    self.region_selected.emit(rx, ry, rw, rh)
            else:
                print("⚠️ 选择区域太小")
                self.selection_cancelled.emit()

            self.close()
    
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key_Escape:
            print("❌ 框选已取消")
            self.selection_cancelled.emit()
            self.close()


def main():
    app = QApplication(sys.argv)
    
    print("=" * 50)
    print("ROI框选工具（覆盖游戏窗口版本）")
    print("=" * 50)
    print("使用说明:")
    print("  1. 左键拖动框选区域")
    print("  2. 释放左键确认选择")
    print("  3. 右键或ESC取消")
    print("=" * 50)
    print("\n启动框选工具...")
    
    selector = ROISelector()
    
    def on_region_selected(x, y, w, h):
        print(f"\n框选完成: ({x}, {y}, {w}, {h})")
        QApplication.quit()
    
    def on_cancelled():
        print("\n框选已取消")
        QApplication.quit()
    
    selector.region_selected.connect(on_region_selected)
    selector.selection_cancelled.connect(on_cancelled)
    selector.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
