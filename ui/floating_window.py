from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QPoint, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QBrush, QPixmap
import ctypes
from ctypes import wintypes
import os

class FloatingWindow(QWidget):
    """悬浮窗 - 模仿HTML的半透明毛玻璃效果"""
    
    # 信号：当计数变化时通知主窗口
    count_changed = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 拖拽相关
        self.drag_pos = None
        self.is_locked = False  # 是否锁定位置
        
        # 交互模式控制
        self.interactive_mode = False  # 是否处于交互模式
        self.mouse_enabled = True  # 鼠标是否可选中
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.setInterval(2000)  # 悬停2秒后激活
        self.hover_timer.timeout.connect(self._activate_interactive_mode)
        
        # 注册全局快捷键 Ctrl+N
        self._register_hotkey()
        
        # 悬浮窗尺寸配置
        self.size_configs = {
            "small": {"size": (260, 150), "margins": (12, 12, 12, 12), "spacing": 8},
            "medium": {"size": (320, 180), "margins": (16, 16, 16, 16), "spacing": 10},
            "large": {"size": (400, 220), "margins": (20, 20, 20, 20), "spacing": 12}
        }
        self.current_size = "medium"
        
        # 初始化UI
        self._init_ui()
        
        # 设置初始状态为穿透模式
        self._set_transparent_mode()
        
    def _init_ui(self):
        """初始化悬浮窗UI"""
        # 根据当前尺寸配置设置窗口
        config = self.size_configs[self.current_size]
        width, height = config["size"]
        margins = config["margins"]
        spacing = config["spacing"]
        
        self.resize(width, height)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(*margins)
        main_layout.setSpacing(spacing)
        
        # 顶部栏
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)
        
        # 精灵名称
        name_section = QHBoxLayout()
        name_section.setSpacing(6)
        name_section.setContentsMargins(0, 8, 0, 0)  # 增加顶部留白
        
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("background: transparent;")
        name_section.addWidget(self.icon_label)
        
        self.poke_name_label = QLabel("异色帕尔")
        self.poke_name_label.setStyleSheet("color: #f8f0ff; font-weight: bold; font-size: 14px;")
        name_section.addWidget(self.poke_name_label)
        name_section.addStretch()
        
        top_bar.addLayout(name_section)
        
        # 展开按钮（Windows风格最大化图标）
        btn_expand = QPushButton("□")
        btn_expand.setFixedSize(32, 32)
        btn_expand.setToolTip("返回主窗口")
        btn_expand.setStyleSheet("""
            QPushButton {
                color: #c77dff;
                background: rgba(199, 125, 255, 0.1);
                border: 1px solid rgba(199, 125, 255, 0.4);
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #f8f0ff;
                background: rgba(199, 125, 255, 0.2);
                border: 1px solid #c77dff;
            }
        """)
        btn_expand.clicked.connect(self.expand_to_main)
        top_bar.addWidget(btn_expand)
        
        # 固定按钮（图钉图标）
        self.btn_lock = QPushButton("📍")
        self.btn_lock.setFixedSize(32, 32)
        self.btn_lock.setMinimumWidth(32)
        self.btn_lock.setToolTip("锁定/解锁位置")
        self.btn_lock.setStyleSheet("""
            QPushButton {
                color: #ffffff;
                background: transparent;
                border: none;
                font-size: 18px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                color: #f8f0ff;
                background: rgba(199, 125, 255, 0.2);
                border-radius: 4px;
            }
        """)
        self.btn_lock.clicked.connect(self.toggle_lock)
        top_bar.addWidget(self.btn_lock)
        
        main_layout.addLayout(top_bar)
        
        # 信息行
        info_bar = QHBoxLayout()
        info_bar.setContentsMargins(0, 12, 0, 0)  # 增加顶部留白,与名字拉开更大距离
        
        left_info = QLabel("污染击破")
        left_info.setStyleSheet("color: #e0aaff; font-size: 12px;")
        info_bar.addWidget(left_info)
        
        info_bar.addStretch()
        
        self.lock_label = QLabel("锁定：幽系")
        self.lock_label.setStyleSheet("color: #c084fc; font-size: 12px;")
        info_bar.addWidget(self.lock_label)
        
        main_layout.addLayout(info_bar)
        
        # 当前洛克王国精灵显示
        self.current_lkwg_label = QLabel("当前精灵：")
        self.current_lkwg_label.setStyleSheet("color: #ffffff; font-size: 13px; margin-top: 4px;")
        self.current_lkwg_label.setVisible(True)
        main_layout.addWidget(self.current_lkwg_label)
        
        # 大数字计数
        self.count_label = QLabel("32/80")
        self.count_label.setStyleSheet("""
            color: #f8f0ff;
            font-size: 36px;
            font-weight: bold;
        """)
        main_layout.addWidget(self.count_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(80)
        self.progress_bar.setValue(32)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(26, 15, 48, 0.8);
                border: none;
                border-radius: 4px;
                height: 8px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #c77dff, stop:1 #9d4edd);
                border-radius: 4px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # 底部栏
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 0, 0, 0)
        
        self.remaining_label = QLabel("保底剩余 48")
        self.remaining_label.setStyleSheet("color: #c084fc; font-size: 12px;")
        bottom_bar.addWidget(self.remaining_label)
        
        bottom_bar.addStretch()
        
        # 污染提示数
        self.nightmare_label = QLabel("污染提示: 0")
        self.nightmare_label.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold;")
        bottom_bar.addWidget(self.nightmare_label)
        
        main_layout.addLayout(bottom_bar)
        
        # 快捷键状态提示栏
        status_bar = QHBoxLayout()
        status_bar.setContentsMargins(0, 4, 0, 0)
        
        self.status_label = QLabel("Ctrl+N: 鼠标穿透 ✓")
        self.status_label.setStyleSheet("color: #a78bfa; font-size: 10px;")
        status_bar.addWidget(self.status_label)
        
        status_bar.addStretch()
        
        main_layout.addLayout(status_bar)
    
    def _register_hotkey(self):
        """注册全局快捷键 Ctrl+N"""
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            # MOD_CONTROL = 0x0002, VK_N = 0x4E
            self.hotkey_id = 1
            registered = user32.RegisterHotKey(
                int(self.winId()),
                self.hotkey_id,
                0x0002,  # MOD_CONTROL
                0x4E     # VK_N
            )
            if registered:
                print("✓ 全局快捷键 Ctrl+N 已注册")
            else:
                print("✗ 全局快捷键注册失败")
        except Exception as e:
            print(f"✗ 注册快捷键异常: {e}")
    
    def nativeEvent(self, eventType, message):
        """处理Windows原生消息 - 捕获全局快捷键"""
        if eventType == b'windows_generic_MSG':
            msg = ctypes.wintypes.MSG.from_address(message.__int__())
            WM_HOTKEY = 0x0312
            if msg.message == WM_HOTKEY and msg.wParam == self.hotkey_id:
                self._toggle_mouse_interaction()
                return True, 0
        return super().nativeEvent(eventType, message)
    
    def _toggle_mouse_interaction(self):
        """切换鼠标交互状态"""
        self.mouse_enabled = not self.mouse_enabled
        if self.mouse_enabled:
            # 启用鼠标交互：移除透明属性
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            
            # 移除WS_EX_TRANSPARENT扩展样式
            try:
                import win32gui
                import win32con
                hwnd = int(self.winId())
                ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                ex_style &= ~win32con.WS_EX_TRANSPARENT  # 清除TRANSPARENT标志
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
                print("✓ 悬浮窗已启用鼠标交互")
            except ImportError:
                print("⚠️ 未安装pywin32，使用基础模式")
            
            # 更新状态显示
            self.status_label.setText("Ctrl+N: 可交互 ✗")
            self.status_label.setStyleSheet("color: #10b981; font-size: 10px;")
        else:
            # 禁用鼠标交互：设置透明穿透
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            
            # 使用Windows API设置WS_EX_TRANSPARENT扩展样式
            try:
                import win32gui
                import win32con
                hwnd = int(self.winId())
                ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                ex_style |= win32con.WS_EX_TRANSPARENT
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
                print("✓ 悬浮窗已禁用鼠标交互（完全穿透）")
            except ImportError:
                print("⚠️ 未安装pywin32，使用基础穿透模式")
            
            # 更新状态显示
            self.status_label.setText("Ctrl+N: 鼠标穿透 ✓")
            self.status_label.setStyleSheet("color: #a78bfa; font-size: 10px;")
    
    def _set_transparent_mode(self):
        """设置为透明穿透模式"""
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setWindowOpacity(0.7)  # 降低透明度，减少视觉干扰
        
    def _activate_interactive_mode(self):
        """激活交互模式"""
        if not self.interactive_mode:
            self.interactive_mode = True
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.setWindowOpacity(1.0)
            
    def _deactivate_interactive_mode(self):
        """取消交互模式，恢复穿透"""
        if self.interactive_mode:
            self.interactive_mode = False
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.setWindowOpacity(0.7)
            self.hover_timer.stop()
    
    def enterEvent(self, event):
        """鼠标进入悬浮窗区域"""
        if not self.is_locked:
            self.hover_timer.start()  # 启动定时器
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开悬浮窗区域"""
        self.hover_timer.stop()  # 停止定时器
        self._deactivate_interactive_mode()  # 立即恢复穿透
        super().leaveEvent(event)
        
    def update_data(self, pokemon_name, type_, count, target, is_locked=False, nightmare_count=0, icon_id=0):
        """更新悬浮窗数据"""
        self.poke_name_label.setText(pokemon_name)
        lock_status = "🔒 锁定" if is_locked else f"锁定：{type_}"
        self.lock_label.setText(lock_status)
        self.count_label.setText(f"{count}/{target}")
        self.progress_bar.setMaximum(target)
        self.progress_bar.setValue(count)
        remaining = target - count
        self.remaining_label.setText(f"保底剩余 {remaining}")
        self.nightmare_label.setText(f"污染提示: {nightmare_count}")
        
        # 加载精灵图标
        self._load_pokemon_icon(pokemon_name, icon_id)
    
    def update_current_lkwg(self, lkwg_name):
        """更新当前洛克王国精灵显示"""
        if lkwg_name:
            text = f"当前精灵：【{lkwg_name}】"
            self.current_lkwg_label.setText(text)
            print(f"✅ 设置文本: {text}")
        else:
            # OCR识别不到时，清空精灵名字，但保留“当前精灵：”
            self.current_lkwg_label.setText("当前精灵：")
            print("❌ OCR未识别到精灵，重置标签")
    
    def _load_pokemon_icon(self, pokemon_name, icon_id=0):
        """加载精灵图标"""
        image_loaded = False
        
        # 优先尝试使用icon_id从tj/images加载
        if icon_id > 0:
            image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "tj", "images")
            image_path = os.path.join(image_dir, f"{icon_id:03d}.png")
            
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.icon_label.setPixmap(scaled_pixmap)
                    image_loaded = True
        
        # 如果icon_id未加载，尝试从ys文件夹加载
        if not image_loaded:
            image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "ys")
            image_path = os.path.join(image_dir, f"{pokemon_name}.png")
            
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.icon_label.setPixmap(scaled_pixmap)
                    image_loaded = True
        
        # 如果都未加载，使用默认emoji
        if not image_loaded:
            self.icon_label.setText("🐾")
            self.icon_label.setStyleSheet("font-size: 16px; background: transparent;")
    
    def update_nightmare_count(self, count):
        """更新污染提示数"""
        self.nightmare_label.setText(f"污染提示: {count}")
    
    def set_size(self, size_name):
        """设置悬浮窗大小
        
        Args:
            size_name: 'small', 'medium', 或 'large'
        """
        if size_name not in self.size_configs:
            return
        
        self.current_size = size_name
        config = self.size_configs[size_name]
        
        # 调整窗口大小
        width, height = config["size"]
        self.resize(width, height)
        
        # 调整布局间距
        self.layout().setContentsMargins(*config["margins"])
        self.layout().setSpacing(config["spacing"])
        
        # 根据尺寸调整字体大小
        self._adjust_font_sizes(size_name)
    
    def _adjust_font_sizes(self, size_name):
        """根据尺寸调整字体大小"""
        font_sizes = {
            "small": {
                "icon": 14,
                "name": 12,
                "info": 10,
                "current_lkwg": 11,
                "count": 28,
                "remaining": 10,
                "nightmare": 10
            },
            "medium": {
                "icon": 16,
                "name": 14,
                "info": 12,
                "current_lkwg": 13,
                "count": 36,
                "remaining": 12,
                "nightmare": 12
            },
            "large": {
                "icon": 18,
                "name": 16,
                "info": 14,
                "current_lkwg": 15,
                "count": 44,
                "remaining": 14,
                "nightmare": 14
            }
        }
        
        sizes = font_sizes[size_name]
        
        # 更新各个元素的样式
        # 这里需要通过遍历子组件来找到对应的标签并更新
        # 由于PySide6的限制，我们需要重新应用样式
        
    def toggle_lock(self):
        """切换锁定状态"""
        self.is_locked = not self.is_locked
        if self.is_locked:
            self.btn_lock.setText("🔒")
            self.btn_lock.setToolTip("已锁定，点击解锁")
        else:
            self.btn_lock.setText("📍")
            self.btn_lock.setToolTip("锁定/解锁位置")
    
    def expand_to_main(self):
        """切换回主窗口"""
        if self.parent():
            self.hide()
            self.parent().show()
    
    def paintEvent(self, event):
        """绘制半透明背景和毛玻璃效果"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 半透明背景 + 边框（一次性绘制）
        bg_color = QColor(18, 8, 34, 235)  # rgba(18, 8, 34, 0.92)
        border_color = QColor(157, 78, 221, 128)  # rgba(157, 78, 221, 0.5)
        
        # 设置画笔宽度为2像素
        pen = painter.pen()
        pen.setWidth(2)
        pen.setColor(border_color)
        painter.setPen(pen)
        painter.setBrush(QBrush(bg_color))
        
        # 绘制圆角矩形（向内偏移1像素避免边框被裁剪）
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 16, 16)
    
    def mousePressEvent(self, event):
        """鼠标按下开始拖拽"""
        if event.button() == Qt.LeftButton and not self.is_locked:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动实现拖拽"""
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None and not self.is_locked:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        self.drag_pos = None
        event.accept()
