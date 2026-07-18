from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QGraphicsDropShadowEffect, QScrollArea, QComboBox,
    QFileDialog, QSizePolicy, QLineEdit
)
from PySide6.QtCore import Qt, QPoint, QPointF, Signal, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QPixmap, QPen, QWheelEvent, QImage
import os
import sys
import json
import math
import ctypes
from ctypes import windll

# 导入自定义模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.map_navigation import MapNavigationThread
from core.screen_selector import ScreenSelector
from core.settings_manager import SettingsManager


def get_resource_path(relative_path):
    """获取资源文件的正确路径，支持打包后运行，优先使用内部打包资源"""
    if getattr(sys, 'frozen', False):
        # 打包环境：优先使用内部打包资源
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(sys.executable)
        return os.path.join(base_path, relative_path)
    else:
        # 开发环境
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, relative_path)


class MapLabel(QLabel):
    """支持绘制资源图标、指针和路线的地图标签"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.resource_data = []  # 存储需要绘制的资源信息
        self.pointer_position = None  # 指针位置 (x, y)
        self.pointer_visible = False  # 指针是否可见
        self.pointer_angle = 0.0  # 指针Qt旋转角度（度），0°=朝上
        self._target_angle = 0.0   # 目标角度（模型原始角度，未转换）
        self.map_scale = 1.0  # 地图缩放比例

        # 指针图标（zz.png，支持旋转渲染）
        zz_path = get_resource_path(os.path.join("image", "zz.png"))
        self.ptr_pixmap = QPixmap(zz_path) if os.path.exists(zz_path) else QPixmap()
        self.ptr_size = 32  # 指针渲染尺寸（缩放后）

        # 路线相关
        self.route_points = []  # 路线点列表：[(x, y, is_checkpoint), ...]
        self.route_visible = True  # 是否显示路线
        self.route_color = QColor(34, 197, 94, 255)  # 路线颜色
        self.checkpoint_color = QColor(255, 165, 0, 255)  # 检查点颜色
        
        # 指针模式
        self.use_real_pointer = True  # True=使用游戏指针(zz.png)，False=使用绿色方向指针
        
    def set_resource_data(self, data):
        """设置资源数据"""
        self.resource_data = data
        self.update()
        
    def set_pointer_position(self, x, y, visible=True):
        """设置指针位置"""
        self.pointer_position = (x, y)
        self.pointer_visible = visible
        self.update()
        
    def set_map_scale(self, scale):
        """设置地图缩放比例"""
        self.map_scale = scale
        self.update()
        
    def set_pointer_angle(self, angle):
        """设置指针角度

        模型角度约定：0°=UP, 90°=LEFT, 180°=DOWN, 270°=RIGHT（逆时针递增）
        zz.png 在 rotate(0°) 时指向 UP

        Qt painter.rotate(qt) = 顺时针旋转 qt 度
        转换：qt = (360 - model_angle) % 360
        """
        self._target_angle = angle
        # 模型角度 → Qt旋转角度
        qt_angle = (360 - angle) % 360

        # 最短路径插值：计算有符号角度差 [-180, 180]
        diff = (qt_angle - self.pointer_angle + 180) % 360 - 180

        # 翻转（角度差>90°）时直接跳转，不插值
        if abs(diff) > 90:
            self.pointer_angle = qt_angle
        else:
            # 小角度变化用平滑插值
            self.pointer_angle += diff * 0.5
            self.pointer_angle %= 360

        self.update()
        
    def set_route_points(self, points):
        """设置路线点"""
        self.route_points = points
        self.update()
        
    def add_route_point(self, x, y, is_checkpoint=False):
        """添加路线点"""
        self.route_points.append((x, y, is_checkpoint))
        self.update()
        
    def clear_route(self):
        """清除路线"""
        self.route_points = []
        self.update()
        
    def set_route_visible(self, visible):
        """设置路线可见性"""
        self.route_visible = visible
        self.update()
        
    def paintEvent(self, event):
        """绘制事件 - 先绘制父类内容，再绘制资源图标、路线和指针"""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # 绘制资源图标
        for item in self.resource_data:
            icon = item['icon']
            x = item['x']
            y = item['y']
            size = item['size']
            
            if icon and not icon.isNull():
                # 绘制图标
                scaled_icon = icon.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(int(x - size/2), int(y - size/2), scaled_icon)
        
        # 绘制路线（支持多段路线）
        if self.route_visible and len(self.route_points) >= 2:
            # 绘制路线线段（按段绘制，遇到 None 断开）
            painter.setPen(QPen(self.route_color, 3, Qt.SolidLine))
            painter.setBrush(Qt.NoBrush)
            
            # 当前段的起点
            segment_start = 0
            
            # 遍历路线点，按段绘制
            for i in range(len(self.route_points)):
                if self.route_points[i] is None or i == len(self.route_points) - 1:
                    # 到达段末尾或遇到 None（段分隔符）
                    segment_end = i if self.route_points[i] is None else i + 1
                    
                    # 绘制当前段的线段
                    if segment_end - segment_start >= 2:
                        for j in range(segment_start, segment_end - 1):
                            if self.route_points[j] is not None and self.route_points[j + 1] is not None:
                                x1, y1, _ = self.route_points[j]
                                x2, y2, _ = self.route_points[j + 1]
                                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
                    
                    segment_start = i + 1
            
            # 绘制路线点和检查点
            checkpoint_count = 0
            for i, point in enumerate(self.route_points):
                if point is None:
                    continue  # 跳过段分隔符
                
                x, y, is_checkpoint = point
                point_radius = 6
                
                if is_checkpoint:
                    # 检查点：更大的圆，不同的颜色
                    checkpoint_count += 1
                    point_radius = 10
                    painter.setPen(QPen(self.checkpoint_color, 2, Qt.SolidLine))
                    painter.setBrush(QBrush(self.checkpoint_color))
                    painter.drawEllipse(QRectF(x - point_radius, y - point_radius, 
                                              point_radius * 2, point_radius * 2))
                    
                    # 绘制检查点标签（序号）
                    painter.setPen(Qt.white)
                    font = painter.font()
                    font.setBold(True)
                    font.setPointSize(10)
                    painter.setFont(font)
                    text_rect = QRectF(x - 8, y - 8, 16, 16)
                    painter.drawText(text_rect, Qt.AlignCenter, str(checkpoint_count))
                else:
                    # 普通路线点
                    painter.setPen(QPen(self.route_color, 2, Qt.SolidLine))
                    painter.setBrush(QBrush(self.route_color))
                    painter.drawEllipse(QRectF(x - point_radius, y - point_radius, 
                                              point_radius * 2, point_radius * 2))
        
        # 绘制指针
        if self.pointer_visible and self.pointer_position:
            px, py = self.pointer_position

            if self.use_real_pointer and not self.ptr_pixmap.isNull():
                # ── 模式A：游戏真实指针（zz.png，支持旋转） ──
                painter.save()
                painter.translate(px, py)
                painter.rotate(self.pointer_angle)
                scaled = self.ptr_pixmap.scaled(
                    self.ptr_size, self.ptr_size,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                painter.drawPixmap(
                    -scaled.width() // 2, -scaled.height() // 2,
                    scaled
                )
                painter.restore()
            else:
                # ── 模式B：绿色方向指针（三角形箭头，朝当前方向） ──
                scale_factor = max(0.7, min(self.map_scale * 1.1, 1.5))
                arrow_size = int(15 * scale_factor)

                painter.save()
                painter.translate(px, py)
                painter.rotate(self.pointer_angle)

                # 箭头主体 - 三角形（QPainter 绘制，支持旋转）
                arrow_body = [
                    QPoint(0, -arrow_size),
                    QPoint(-int(arrow_size * 0.55), int(arrow_size * 0.35)),
                    QPoint(0, int(arrow_size * 0.2)),
                    QPoint(int(arrow_size * 0.55), int(arrow_size * 0.35)),
                ]
                painter.setPen(QPen(QColor(34, 197, 94), max(1, int(2 * scale_factor))))
                painter.setBrush(QBrush(QColor(34, 197, 94, 220)))
                painter.drawPolygon(arrow_body)

                # 箭头中心白色圆点
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(255, 255, 255)))
                painter.drawEllipse(QPoint(0, 0), int(arrow_size * 0.2), int(arrow_size * 0.2))

                painter.restore()
        
        painter.end()

class MapFloatingWindow(QWidget):
    """地图悬浮窗 - 显示简化版地图和导航信息"""
    
    WORLD_WIDTH = 8192
    WORLD_HEIGHT = 8192

    def __init__(self, parent=None, game_capture=None):
        # 不使用 parent，避免跟随主窗口最小化
        super().__init__(None)
        
        # 设置DPI感知
        try:
            windll.shcore.SetProcessDpiAwareness(2)  # Per Monitor V2
        except:
            try:
                windll.shcore.SetProcessDpiAwareness(1)  # Per Monitor
            except:
                pass
        
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 保存父窗口引用（用于获取 circle_roi）
        self._main_window = parent
        
        # 拖拽相关
        self.drag_pos = None
        self.is_locked = False  # 是否锁定位置
        self.pin_mode = False  # 图钉模式：True=拖动地图，False=拖动窗口
        
        # 地图缩放和平移
        self.map_scale = 1.0  # 默认缩放，update_map_display 时会自动 fit-to-view
        self.map_offset_x = 0
        self.map_offset_y = 0
        self.is_dragging_map = False
        self.drag_start_pos = None
        
        # 窗口缩放比例（调整整个悬浮窗大小）
        self.window_scale = 1.0  # 默认1.0倍
        self.base_window_width = 400
        self.base_window_height = 300
        self.base_map_width = 360
        self.base_map_height = 200
        
        # 上次有效位置（用于检测异常跳变）
        self.last_valid_position = None
        self._last_angle_pos = None  # 上次更新角度时的位置，用于累积位移判断
        self.position_update_count = 0
        
        # 传送检测：连续3次相同的大跳变位置才确认为传送
        self.pending_teleport_position = None
        self.teleport_confirm_count = 0
        
        # 资源数据
        self.collect_data = {}
        self.selected_resource = "全部显示"
        self.resource_markers = []  # 存储资源标记
        
        # 眠枭之星和宝箱数据
        self.owl_stars_data = {}
        self.selected_owl_stars = set()  # 选中的眠枭之星和宝箱集合
        self.owl_star_markers = []  # 存储标记
        self.chests_loaded = False  # 宝箱是否已加载
        
        # 路线编辑模式
        self.route_edit_mode = False  # 是否在路线编辑模式
        self.is_placing_checkpoint = False  # 是否正在放置检查点
        self.route_segments = []  # 路线段列表，支持多段路线：[[(x,y,cp), ...], [(x,y,cp), ...], ...]
        self.route_history = []  # 路线历史，用于撤回
        
        # 路线管理数据结构
        self.saved_routes = []  # 保存的路线列表: [{"name": str, "segments": list, "color": str}, ...]
        self._current_route_name = "未命名路线"  # 当前路线名称
        self.route_color = QColor(34, 197, 94, 255)  # 路线颜色
        
        # 鼠标穿透
        self.mouse_enabled = True  # 鼠标是否可选中
        
        # 透明度
        self.window_opacity = 1.0  # 窗口透明度
        
        # DPI缩放
        self.dpi_scale = self._get_dpi_scale()  # 获取系统DPI缩放因子
        
        # 导航相关
        self.game_capture = game_capture
        self.navigation_thread = None
        self.is_navigating = False
        self.minimap_roi = None  # 小地图区域 (x, y, width, height)
        self.minimap_to_map_scale = 1.0  # 小地图到完整地图的缩放比例
        self.minimap_to_map_offset = (0, 0)  # 小地图到完整地图的偏移

        # 渲染优化
        self._cached_scaled_pixmap = None  # 缓存的缩放地图
        self._cached_scale = 0  # 缓存时的缩放值
        self._pixmap_needs_update = True  # 地图需要重新缩放
        self._markers_needs_update = True  # 标记需要重建
        self._render_timer = QTimer(self)  # 定时器用于批量延迟渲染
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._do_deferred_render)
        self._last_pointer_x = 0
        self._last_pointer_y = 0
        self._pending_center = False  # 待处理的地图居中请求
        self._pending_center_x = 0
        self._pending_center_y = 0
        
        if self._main_window and hasattr(self._main_window, 'circle_roi'):
            self.minimap_roi = self._main_window.circle_roi
        
        # 加载图标
        sc_dir = get_resource_path(os.path.join("image", "sc"))
        self.ks_icon = QPixmap(os.path.join(sc_dir, 'ks.png')) if os.path.exists(os.path.join(sc_dir, 'ks.png')) else QPixmap()
        self.hua_icon = QPixmap(os.path.join(sc_dir, 'hua.png')) if os.path.exists(os.path.join(sc_dir, 'hua.png')) else QPixmap()
        self._resource_icon_cache = {}  # 资源个体图标缓存

        # 眠枭之星和宝箱图标缓存（避免每次从磁盘重载）
        self._jx_icon = QPixmap(os.path.join(sc_dir, 'jx.png')) if os.path.exists(os.path.join(sc_dir, 'jx.png')) else QPixmap()
        self._lx_icon = QPixmap(os.path.join(sc_dir, 'lx.png')) if os.path.exists(os.path.join(sc_dir, 'lx.png')) else QPixmap()
        self._xz_icon = QPixmap(os.path.join(sc_dir, 'xz.png')) if os.path.exists(os.path.join(sc_dir, 'xz.png')) else QPixmap()
        self._yp_icon = QPixmap(os.path.join(sc_dir, 'yp.png')) if os.path.exists(os.path.join(sc_dir, 'yp.png')) else QPixmap()
        
        # 初始化UI
        self._init_ui()
        
    def showEvent(self, event):
        """窗口显示时注册热键"""
        super().showEvent(event)
        # 使用低级键盘钩子注册全局快捷键 Alt+M（不阻塞按键传递）
        self._register_hotkey()

    def _register_hotkey(self):
        """注册全局快捷键 Alt+M（使用低级键盘钩子，不阻塞按键传递）"""
        try:
            from core.settings_manager import SettingsManager
            from core.keyboard_hook import KeyboardHook

            settings = SettingsManager()
            hotkeys = settings.get("hotkeys", {})
            cfg = hotkeys.get("map_toggle_passthrough", {"mod_code": 0x0001, "vk": 0x4D})

            # 销毁旧的钩子
            self._unregister_hotkeys()

            self.hotkey_id = 2
            self._keyboard_hook = KeyboardHook(parent=self)
            self._keyboard_hook.hotkey_triggered.connect(self._on_hotkey_triggered)
            self._keyboard_hook.register_hotkey(
                cfg.get("vk", 0x4D),
                cfg.get("mod_code", 0x0001),
                self.hotkey_id
            )
            self._keyboard_hook.start()
            display = cfg.get("display", "Alt+M")
            print(f"✓ 地图全局快捷键 {display} 已注册")
        except Exception as e:
            pass

    def _unregister_hotkeys(self):
        """注销所有已注册的全局快捷键"""
        try:
            if hasattr(self, '_keyboard_hook') and self._keyboard_hook is not None:
                self._keyboard_hook.stop()
                self._keyboard_hook.deleteLater()
                self._keyboard_hook = None
        except Exception as e:
            pass

    def _on_hotkey_triggered(self, hk_id):
        """键盘钩子触发热键时的处理（主线程）"""
        if hk_id == self.hotkey_id:
            self._toggle_mouse_interaction()

    def nativeEvent(self, eventType, message):
        """处理Windows原生消息（热键现在通过 KeyboardHook 处理，保留以兼容）"""
        return super().nativeEvent(eventType, message)
        
    def _init_ui(self):
        """初始化地图悬浮窗UI"""
        # 设置窗口大小
        self.resize(400, 300)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # 顶部栏
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)
        
        # 标题
        title_label = QLabel("地图导航")
        title_label.setStyleSheet("color: #f8f0ff; font-weight: bold; font-size: 16px;")
        top_bar.addWidget(title_label)
        top_bar.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton()
        close_btn.setFixedSize(28, 28)
        close_btn.setToolTip("关闭悬浮窗")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.15);
                border: 1.5px solid rgba(239, 68, 68, 0.6);
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.3);
                border: 1.5px solid #ef4444;
            }
        """)
        # 使用 QLabel 绘制红色 X
        close_icon = QLabel("✕", close_btn)
        close_icon.setStyleSheet("color: #ef4444; font-size: 16px; font-weight: bold;")
        close_icon.setAlignment(Qt.AlignCenter)
        close_icon.setGeometry(0, 0, 28, 28)
        close_btn.clicked.connect(self.close)
        top_bar.addWidget(close_btn)
        
        # 鼠标穿透按钮（穿透时为紫色，不穿透时为绿色）
        self.penetrate_btn = QPushButton()
        self.penetrate_btn.setFixedSize(28, 28)
        self.penetrate_btn.setToolTip("鼠标穿透 (Alt+M)\n绿色=可交互，紫色=穿透\n点击也可切换")
        self.penetrate_btn.setCheckable(True)
        self.penetrate_btn.setChecked(False)
        self.penetrate_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 197, 94, 0.2);
                border: 1.5px solid #22c55e;
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(34, 197, 94, 0.3);
                border: 1.5px solid #16a34a;
            }
            QPushButton:checked {
                background-color: rgba(168, 85, 247, 0.2);
                border: 1.5px solid #a855f7;
            }
        """)
        penetrate_icon = QLabel("👆", self.penetrate_btn)
        penetrate_icon.setStyleSheet("color: #22c55e; font-size: 16px;")
        penetrate_icon.setAlignment(Qt.AlignCenter)
        penetrate_icon.setGeometry(0, 0, 28, 28)
        self.penetrate_btn.clicked.connect(self._toggle_mouse_interaction)
        top_bar.addWidget(self.penetrate_btn)
        
        # 撤回按钮（改为红色）
        self.undo_btn = QPushButton()
        self.undo_btn.setFixedSize(28, 28)
        self.undo_btn.setToolTip("撤回上一个路径点")
        self.undo_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.15);
                border: 1.5px solid rgba(239, 68, 68, 0.5);
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.25);
                border: 1.5px solid #ef4444;
            }
        """)
        undo_icon = QLabel("↩", self.undo_btn)
        undo_icon.setStyleSheet("color: #ef4444; font-size: 16px; font-weight: bold;")
        undo_icon.setAlignment(Qt.AlignCenter)
        undo_icon.setGeometry(0, 0, 28, 28)
        self.undo_btn.clicked.connect(self._undo_last_point)
        top_bar.addWidget(self.undo_btn)
        
        # 锁定按钮（改进样式）
        self.pin_btn = QPushButton()
        self.pin_btn.setFixedSize(28, 28)
        self.pin_btn.setToolTip("锁定窗口，拖动地图")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setChecked(False)
        self.pin_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(199, 125, 255, 0.15);
                border: 1.5px solid rgba(199, 125, 255, 0.5);
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(199, 125, 255, 0.25);
                border: 1.5px solid #c77dff;
            }
            QPushButton:checked {
                background-color: rgba(34, 197, 94, 0.2);
                border: 1.5px solid #22c55e;
            }
        """)
        # 使用更直观的图标
        self.pin_icon_label = QLabel("🔒", self.pin_btn)
        self.pin_icon_label.setStyleSheet("color: #c77dff; font-size: 14px;")
        self.pin_icon_label.setAlignment(Qt.AlignCenter)
        self.pin_icon_label.setGeometry(0, 0, 28, 28)
        self.pin_btn.clicked.connect(self._toggle_pin_mode)
        top_bar.addWidget(self.pin_btn)
        
        # 缩小按钮（缩小窗口）
        self.shrink_btn = QPushButton()
        self.shrink_btn.setFixedSize(28, 28)
        self.shrink_btn.setToolTip("缩小悬浮窗 (Ctrl+-)")
        self.shrink_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(124, 58, 237, 0.15);
                border: 1.5px solid rgba(124, 58, 237, 0.5);
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(124, 58, 237, 0.25);
                border: 1.5px solid #8b5cf6;
            }
        """)
        shrink_icon = QLabel("−", self.shrink_btn)
        shrink_icon.setStyleSheet("color: #a78bfa; font-size: 18px; font-weight: bold;")
        shrink_icon.setAlignment(Qt.AlignCenter)
        shrink_icon.setGeometry(0, 0, 28, 28)
        self.shrink_btn.clicked.connect(self._shrink_window)
        top_bar.addWidget(self.shrink_btn)
        
        # 放大按钮（放大窗口）
        self.expand_btn = QPushButton()
        self.expand_btn.setFixedSize(28, 28)
        self.expand_btn.setToolTip("放大悬浮窗 (Ctrl++)")
        self.expand_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(124, 58, 237, 0.15);
                border: 1.5px solid rgba(124, 58, 237, 0.5);
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(124, 58, 237, 0.25);
                border: 1.5px solid #8b5cf6;
            }
        """)
        expand_icon = QLabel("+", self.expand_btn)
        expand_icon.setStyleSheet("color: #a78bfa; font-size: 18px; font-weight: bold;")
        expand_icon.setAlignment(Qt.AlignCenter)
        expand_icon.setGeometry(0, 0, 28, 28)
        self.expand_btn.clicked.connect(self._expand_window)
        top_bar.addWidget(self.expand_btn)
        
        # 折叠按钮
        self.collapse_btn = QPushButton()
        self.collapse_btn.setFixedSize(28, 28)
        self.collapse_btn.setToolTip("折叠/展开悬浮窗")
        self.collapse_btn.setCheckable(True)
        self.collapse_btn.setChecked(False)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(251, 191, 36, 0.15);
                border: 1.5px solid rgba(251, 191, 36, 0.5);
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(251, 191, 36, 0.25);
                border: 1.5px solid #fbbf24;
            }
        """)
        self.collapse_icon_label = QLabel("▼", self.collapse_btn)
        self.collapse_icon_label.setStyleSheet("color: #fbbf24; font-size: 14px; font-weight: bold;")
        self.collapse_icon_label.setAlignment(Qt.AlignCenter)
        self.collapse_icon_label.setGeometry(0, 0, 28, 28)
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        top_bar.addWidget(self.collapse_btn)
        
        main_layout.addLayout(top_bar)
        
        # 地图容器（固定大小）
        self.map_container = QWidget()
        self.map_container.setFixedSize(360, 200)  # 固定地图显示区域大小
        self.map_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 8px;
            }
        """)
        self.map_container.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.map_label = MapLabel(self.map_container)
        self.map_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.map_label.setMouseTracking(True)
        
        main_layout.addWidget(self.map_container)
        
        # 可折叠内容容器
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setSpacing(12)
        
        # 资源筛选（多选）
        resource_layout = QHBoxLayout()
        resource_label = QLabel("资源：")
        resource_label.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        resource_layout.addWidget(resource_label)
        
        # 创建多选下拉框按钮
        self.resource_btn = QPushButton("全部显示")
        self.resource_btn.setFixedWidth(120)
        self.resource_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(39, 39, 42, 0.8);
                color: #e4e4e7;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                text-align: left;
            }
            QPushButton:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
        """)
        self.resource_btn.clicked.connect(self._toggle_resource_menu)
        resource_layout.addWidget(self.resource_btn)
        
        # 创建资源选择菜单
        from PySide6.QtWidgets import QMenu
        self.resource_menu = QMenu()
        self.resource_menu.setStyleSheet("""
            QMenu {
                background-color: rgba(30, 30, 38, 0.95);
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 6px;
                padding: 8px;
            }
            QMenu::item {
                padding: 6px 20px;
                color: #e4e4e7;
            }
            QMenu::item:selected {
                background-color: rgba(124, 58, 237, 0.3);
            }
        """)
        
        # 添加全选/全不选选项
        self.action_show_all = self.resource_menu.addAction("✓ 全部显示")
        self.action_hide_all = self.resource_menu.addAction("✗ 全部隐藏")
        self.resource_menu.addSeparator()
        
        self.action_show_all.triggered.connect(lambda: self._set_all_resources(True))
        self.action_hide_all.triggered.connect(lambda: self._set_all_resources(False))
        resource_layout.addStretch()
        
        self.content_layout.addLayout(resource_layout)
        
        # 眠枭之星显示按钮（多选下拉框）
        owl_stars_layout = QHBoxLayout()
        owl_stars_label = QLabel("其余：")
        owl_stars_label.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        owl_stars_layout.addWidget(owl_stars_label)
        
        self.owl_stars_btn = QPushButton("全部隐藏")
        self.owl_stars_btn.setFixedWidth(100)
        self.owl_stars_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(39, 39, 42, 0.8);
                color: #e4e4e7;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                text-align: left;
            }
            QPushButton:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
        """)
        self.owl_stars_btn.clicked.connect(self._toggle_owl_stars_menu)
        owl_stars_layout.addWidget(self.owl_stars_btn)
        
        # 创建眠枭之星选择菜单
        from PySide6.QtWidgets import QMenu
        self.owl_stars_menu = QMenu()
        self.owl_stars_menu.setStyleSheet("""
            QMenu {
                background-color: rgba(30, 30, 38, 0.95);
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 6px;
                padding: 8px;
            }
            QMenu::item {
                padding: 6px 20px;
                color: #e4e4e7;
            }
            QMenu::item:selected {
                background-color: rgba(124, 58, 237, 0.3);
            }
        """)
        
        # 添加全选/全不选选项
        self.action_owl_show_all = self.owl_stars_menu.addAction("✓ 全部显示")
        self.action_owl_hide_all = self.owl_stars_menu.addAction("✗ 全部隐藏")
        self.owl_stars_menu.addSeparator()
        
        self.action_owl_show_all.triggered.connect(lambda: self._set_all_owl_stars(True))
        self.action_owl_hide_all.triggered.connect(lambda: self._set_all_owl_stars(False))
        
        # 初始化眠枭之星和宝箱复选框
        self.owl_stars_checkboxes = {}
        self.selected_owl_stars = set()
        
        owl_stars_layout.addStretch()
        self.content_layout.addLayout(owl_stars_layout)
        
        # 路线编辑按钮区域
        route_layout = QHBoxLayout()
        
        # 绘制路线按钮
        self.draw_route_btn = QPushButton("绘制路线")
        self.draw_route_btn.setFixedHeight(28)
        self.draw_route_btn.setCheckable(True)
        self.draw_route_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 197, 94, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(34, 197, 94, 0.5);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(34, 197, 94, 0.5);
            }
            QPushButton:checked {
                background-color: rgba(34, 197, 94, 0.7);
                border-color: #22c55e;
            }
        """)
        self.draw_route_btn.clicked.connect(self._toggle_route_edit_mode)
        route_layout.addWidget(self.draw_route_btn)
        
        # 放置检查点按钮
        self.add_checkpoint_btn = QPushButton("检查点")
        self.add_checkpoint_btn.setFixedHeight(28)
        self.add_checkpoint_btn.setCheckable(True)
        self.add_checkpoint_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 165, 0, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(255, 165, 0, 0.5);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 165, 0, 0.5);
            }
            QPushButton:checked {
                background-color: rgba(255, 165, 0, 0.7);
                border-color: #ffa500;
            }
        """)
        self.add_checkpoint_btn.clicked.connect(self._toggle_checkpoint_mode)
        route_layout.addWidget(self.add_checkpoint_btn)
        
        # 清除路线按钮
        self.clear_route_btn = QPushButton("清除")
        self.clear_route_btn.setFixedHeight(28)
        self.clear_route_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(239, 68, 68, 0.5);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.5);
            }
        """)
        self.clear_route_btn.clicked.connect(self._clear_route)
        route_layout.addWidget(self.clear_route_btn)
        
        # 断开路线按钮（用于传送点分段）
        self.break_route_btn = QPushButton("断开")
        self.break_route_btn.setFixedHeight(28)
        self.break_route_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(251, 146, 60, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(251, 146, 60, 0.5);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(251, 146, 60, 0.5);
            }
        """)
        self.break_route_btn.clicked.connect(self._break_route)
        route_layout.addWidget(self.break_route_btn)
        
        route_layout.addStretch()
        
        # 导入导出按钮
        self.export_route_btn = QPushButton("导出")
        self.export_route_btn.setFixedHeight(28)
        self.export_route_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(157, 78, 221, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(157, 78, 221, 0.5);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(157, 78, 221, 0.5);
            }
        """)
        self.export_route_btn.clicked.connect(self._export_route)
        route_layout.addWidget(self.export_route_btn)
        
        self.import_route_btn = QPushButton("导入")
        self.import_route_btn.setFixedHeight(28)
        self.import_route_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(157, 78, 221, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(157, 78, 221, 0.5);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(157, 78, 221, 0.5);
            }
        """)
        self.import_route_btn.clicked.connect(self._import_route)
        route_layout.addWidget(self.import_route_btn)
        
        self.content_layout.addLayout(route_layout)
        
        # 路线名称和路径列表
        route_name_layout = QHBoxLayout()
        
        self.route_name_label = QLineEdit(self._current_route_name)
        self.route_name_label.setStyleSheet("""
            QLineEdit {
                background-color: rgba(39, 39, 42, 0.8);
                color: #e4e4e7;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QLineEdit:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
        """)
        self.route_name_label.editingFinished.connect(self._on_route_name_changed)
        route_name_layout.addWidget(self.route_name_label)
        
        self.route_list_btn = QPushButton("▼")
        self.route_list_btn.setFixedHeight(28)
        self.route_list_btn.setFixedWidth(28)
        self.route_list_btn.setToolTip("路径列表")
        self.route_list_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(124, 58, 237, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(124, 58, 237, 0.5);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(124, 58, 237, 0.5);
            }
        """)
        self.route_list_btn.clicked.connect(self._show_route_list_menu)
        route_name_layout.addWidget(self.route_list_btn)
        
        # 颜色选择器
        self.color_btn = QPushButton("▼")
        self.color_btn.setFixedHeight(28)
        self.color_btn.setFixedWidth(28)
        self.color_btn.setToolTip("选择颜色")
        self.color_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 197, 94, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(34, 197, 94, 0.5);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(34, 197, 94, 0.5);
            }
        """)
        self.color_btn.clicked.connect(self._show_color_menu)
        route_name_layout.addWidget(self.color_btn)
        
        self.content_layout.addLayout(route_name_layout)
        
        # 透明度滑条
        opacity_layout = QHBoxLayout()
        
        opacity_label = QLabel("透明度:")
        opacity_label.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        opacity_layout.addWidget(opacity_label)
        
        from PySide6.QtWidgets import QSlider
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setMinimum(30)
        self.opacity_slider.setMaximum(100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setFixedWidth(100)
        self.opacity_slider.valueChanged.connect(self._change_opacity)
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_value_label = QLabel("100%")
        self.opacity_value_label.setStyleSheet("color: #c084fc; font-size: 11px;")
        opacity_layout.addWidget(self.opacity_value_label)
        
        opacity_layout.addStretch()
        self.content_layout.addLayout(opacity_layout)
        
        # 坐标信息显示
        coord_layout = QHBoxLayout()
        
        self.current_pos_label = QLabel("当前位置: --")
        self.current_pos_label.setStyleSheet("color: #e0aaff; font-size: 12px;")
        coord_layout.addWidget(self.current_pos_label)
        
        coord_layout.addStretch()
        
        self.target_pos_label = QLabel("目标位置: --")
        self.target_pos_label.setStyleSheet("color: #c084fc; font-size: 12px;")
        coord_layout.addWidget(self.target_pos_label)
        
        self.content_layout.addLayout(coord_layout)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        # 导航按钮
        self.nav_btn = QPushButton("开始导航")
        self.nav_btn.setFixedHeight(32)
        self.nav_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 197, 94, 0.6);
                color: white;
                border: 1px solid rgba(74, 222, 128, 0.8);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(34, 197, 94, 0.8);
            }
        """)
        self.nav_btn.clicked.connect(self._toggle_navigation)
        btn_layout.addWidget(self.nav_btn)
        
        # 快捷键状态提示栏
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 4, 0, 0)
        
        self.hotkey_status_label = QLabel("Alt+M: 鼠标穿透 | 绿色=可交互 紫色=穿透")
        self.hotkey_status_label.setStyleSheet("color: #c084fc; font-size: 10px;")
        status_layout.addWidget(self.hotkey_status_label)
        
        status_layout.addStretch()
        self.content_layout.addLayout(status_layout)
        
        self.content_layout.addLayout(btn_layout)
        
        # 将可折叠容器添加到主布局
        main_layout.addWidget(self.content_container)
        # 设置内容容器的大小策略，确保可以被正确隐藏
        self.content_container.setSizePolicy(
            self.content_container.sizePolicy().horizontalPolicy(),
            QSizePolicy.Fixed
        )
    
    def _set_target_position(self):
        """设置目标位置"""
        pass  # 这里可以添加设置目标位置的逻辑
    
    def _toggle_navigation(self):
        """切换导航状态"""
        if not self.game_capture:
            return
        
        if self.is_navigating:
            self._stop_navigation()
        else:
            self._start_navigation()
    
    def _start_navigation(self):
        """开始导航"""
        # 从父窗口获取已框选的区域
        if hasattr(self.parent(), 'circle_roi') and self.parent().circle_roi:
            self.minimap_roi = self.parent().circle_roi
        elif hasattr(self.parent(), '_circle_selector') and self.parent()._circle_selector:
            # 如果正在框选，获取当前选择的区域
            selector = self.parent()._circle_selector
            if selector.center_pos and selector.radius > 0:
                x = selector.screen_geometry.x() + selector.center_pos.x() - selector.radius
                y = selector.screen_geometry.y() + selector.center_pos.y() - selector.radius
                w = selector.radius * 2
                h = selector.radius * 2
                self.minimap_roi = (x, y, w, h)
        
        if not self.minimap_roi:
            self.current_pos_label.setText("请先框选小地图区域")
            return
        
        # 导出调试截图
        self._export_debug_screenshot()
        
        # 获取完整地图路径（使用打包资源）
        full_map_path = get_resource_path(os.path.join("image", "map_full_hq.png"))
        
        # 创建导航线程（传入完整地图路径用于 SIFT 定位）
        self.navigation_thread = MapNavigationThread(self.game_capture, self.minimap_roi, full_map_path)
        
        # 从设置读取地图更新帧间隔
        settings = SettingsManager()
        frame_interval = settings.get("map_update_interval", 3)
        use_real_ptr = settings.get("use_real_pointer", True)
        self.navigation_thread.set_frame_interval(frame_interval)
        self.map_label.use_real_pointer = use_real_ptr
        
        # 连接信号
        self.navigation_thread.position_updated.connect(self._on_position_updated)
        self.navigation_thread.navigation_status.connect(self._on_navigation_status)

        # 重置位置更新计数和上次有效位置，确保首次定位时应用导航默认缩放
        self.position_update_count = 0
        self.last_valid_position = None

        # 启动线程
        self.navigation_thread.start()
        self.is_navigating = True
    
    def _calculate_mapping(self):
        """计算小地图到悬浮窗地图的映射参数"""
        # 默认使用1:1映射（假设小地图和悬浮窗地图使用相同的坐标系统）
        # 实际使用时可能需要根据游戏坐标进行调整
        self.minimap_to_map_scale = 1.0
        self.minimap_to_map_offset = (0, 0)
    
    def _export_debug_screenshot(self):
        """导出调试截图（固定文件名，覆盖旧文件）"""
        try:
            import cv2
            import numpy as np
            
            # OpenCV Unicode 路径支持
            def _imwrite(path, img):
                cv2.imencode(os.path.splitext(path)[1] or '.png', img)[1].tofile(path)

            # 截取小地图区域
            debug_image = self.game_capture.capture_window(self.minimap_roi)
            
            if debug_image is not None:
                # 创建保存目录
                image_dir = os.path.join(os.path.dirname(__file__), '..', 'image')
                os.makedirs(image_dir, exist_ok=True)
                
                # 使用固定文件名，覆盖旧文件
                filename = "minimap_current.png"
                filepath = os.path.join(image_dir, filename)
                
                # 保存截图
                _imwrite(filepath, debug_image)
            else:
                pass  # 截图失败
        except Exception as e:
            pass  # 忽略错误
        
        # 更新UI
        self.nav_btn.setText("停止导航")
        self.nav_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.6);
                color: white;
                border: 1px solid rgba(248, 113, 113, 0.8);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.8);
            }
        """)
    
    def _stop_navigation(self):
        """停止导航"""
        if self.navigation_thread:
            self.navigation_thread.stop()
            self.navigation_thread = None
        
        self.is_navigating = False
        
        # 更新UI
        self.nav_btn.setText("开始导航")
        self.nav_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 197, 94, 0.6);
                color: white;
                border: 1px solid rgba(74, 222, 128, 0.8);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(34, 197, 94, 0.8);
            }
        """)
        
        # 隐藏指针
        self.map_label.set_pointer_position(0, 0, visible=False)
    
    def _on_position_updated(self, x, y, confidence, map_position):
        """位置更新回调 - 轻量版：仅更新指针和坐标，延迟批处理重渲染"""
        if confidence > 0 and map_position:
            # map_position = (world_x, world_y, ptr_angle)
            if len(map_position) >= 3:
                map_x, map_y, ptr_angle = map_position[0], map_position[1], map_position[2]
            else:
                map_x, map_y = map_position
                ptr_angle = 0.0

            self.last_valid_position = (map_x, map_y)
            self.position_update_count += 1

            # 指针角度：直接使用识别到的真实旋转角度
            self.map_label.set_pointer_angle(ptr_angle)

            self._last_pointer_x = map_x
            self._last_pointer_y = map_y

            self._update_pointer_position(map_x, map_y)
            self.current_pos_label.setText(f"当前位置: ({int(map_x)}, {int(map_y)})")

            if self.position_update_count == 1:
                # 首次定位：应用导航默认缩放（比 fit_scale 大，便于看清图标位置）
                self._apply_navigation_default_zoom()
                self._pending_center = True
                self._pending_center_x = map_x
                self._pending_center_y = map_y
                self._markers_needs_update = True
            else:
                pointer_screen_x = self.map_offset_x + map_x * self._screen_scale_x()
                pointer_screen_y = self.map_offset_y + map_y * self._screen_scale_y()
                container_width = self.map_container.width()
                container_height = self.map_container.height()
                margin = 50
                if (pointer_screen_x < margin or pointer_screen_x > container_width - margin or
                    pointer_screen_y < margin or pointer_screen_y > container_height - margin):
                    self._pending_center = True
                    self._pending_center_x = map_x
                    self._pending_center_y = map_y
                    self._markers_needs_update = True

            if not self._render_timer.isActive():
                self._render_timer.start(16)
        else:
            if self.last_valid_position is not None:
                pass
            else:
                self.map_label.set_pointer_position(0, 0, visible=False)
                self.current_pos_label.setText("当前位置: (未检测到)")
    
    def _on_navigation_status(self, status):
        """导航状态更新"""
        if hasattr(self, 'current_pos_label'):
            self.current_pos_label.setText(status)
    def _do_deferred_render(self):
        """渲染更新：合并多个位置更新请求，只执行一次重渲染"""
        if self._pending_center:
            self._center_map_on_position(self._pending_center_x, self._pending_center_y)
            self._pending_center = False
            self._markers_needs_update = False
        elif self._pixmap_needs_update or self._markers_needs_update:
            self._update_map_render()
        else:
            # 即使不需要全量渲染，也要确保指针位置刷新
            if self.last_valid_position is not None:
                mx, my = self.last_valid_position
                self._update_pointer_position(mx, my)

    def _apply_navigation_default_zoom(self):
        """应用导航默认缩放。

        默认 fit_scale 会让整张地图铺满容器，图标挤在一起看不清。
        导航开始时放大到 3 倍 fit_scale，便于看清图标在地图上的具体位置。
        """
        if not hasattr(self, 'original_pixmap') or self.original_pixmap.isNull():
            return
        if not hasattr(self, 'map_container'):
            return
        cw = max(1, self.map_container.width())
        ch = max(1, self.map_container.height())
        # fit_scale = 地图刚好铺满容器（无黑边）
        fit_scale = max(cw / self.original_pixmap.width(),
                        ch / self.original_pixmap.height())
        # 导航默认：3 倍 fit_scale，图标在地图上分散开便于辨识
        nav_default_scale = fit_scale * 3.0
        # 限制在合理范围内（不小于 fit_scale，不大于 10 倍）
        self.map_scale = max(fit_scale, min(nav_default_scale, 10.0))

    def _center_map_on_position(self, map_x, map_y):
        """将地图居中显示在指定位置"""
        container_width = self.map_container.width()
        container_height = self.map_container.height()

        scaled_map_x = map_x * self._screen_scale_x()
        scaled_map_y = map_y * self._screen_scale_y()

        self.map_offset_x = (container_width / 2) - scaled_map_x
        self.map_offset_y = (container_height / 2) - scaled_map_y

        self._markers_needs_update = True
        self._update_map_render()

    def _compute_icon_size(self, base_icon_size=16, max_size=32):
        """计算图标大小，基于当前缩放相对于 fit_scale 的比例。

        旧公式 base_icon_size * map_scale 由于 map_scale 是很小的数（约 0.04），
        结果几乎总是 0，被钳到最小值，无法随缩放变化。
        新公式以 fit_scale 为基准，zoom_factor = map_scale / fit_scale，
        在 fit_scale 时图标为 base_icon_size，放大时按比例增大。
        """
        if not hasattr(self, 'original_pixmap') or self.original_pixmap.isNull():
            return max(10, base_icon_size)
        if not hasattr(self, 'map_container'):
            return max(10, base_icon_size)
        cw = max(1, self.map_container.width())
        ch = max(1, self.map_container.height())
        fit_scale = max(cw / self.original_pixmap.width(),
                        ch / self.original_pixmap.height())
        if fit_scale <= 0:
            return max(10, base_icon_size)
        zoom_factor = self.map_scale / fit_scale
        # 最小 10 像素（项目规范），最大 max_size 像素
        return max(10, min(int(base_icon_size * zoom_factor), max_size))
        
    def _screen_scale_x(self):
        """世界X坐标 → 屏幕像素的精确比例"""
        if hasattr(self, 'original_pixmap') and not self.original_pixmap.isNull():
            return float(self.original_pixmap.width() * self.map_scale) / self.WORLD_WIDTH
        return self.map_scale

    def _screen_scale_y(self):
        """世界Y坐标 → 屏幕像素的精确比例"""
        if hasattr(self, 'original_pixmap') and not self.original_pixmap.isNull():
            return float(self.original_pixmap.height() * self.map_scale) / self.WORLD_HEIGHT
        return self.map_scale

    def _update_pointer_position(self, map_x, map_y):
        """根据地图坐标更新指针在屏幕上的位置（保留浮点精度）"""
        # 使用精确的X/Y比例尺（地图宽高比 ≠ 世界宽高比）
        label_x = float(map_x) * self._screen_scale_x()
        label_y = float(map_y) * self._screen_scale_y()
        
        # 设置指针位置（使用浮点坐标，由paintEvent处理取整）
        self.map_label.set_pointer_position(label_x, label_y, visible=True)
    
    def _set_pointer_at_center(self):
        """在地图中心设置指针（延迟调用以确保地图已渲染）"""
        
        if not hasattr(self, 'map_label'):
            return
        
        pixmap = self.map_label.pixmap()
        if pixmap is None or pixmap.isNull():
            return
        
        label_width = self.map_label.width()
        label_height = self.map_label.height()
        
        
        if label_width > 0 and label_height > 0:
            center_x = label_width / 2
            center_y = label_height / 2
            self.map_label.set_pointer_position(center_x, center_y, visible=True)
        else:
            pass  # 标签尺寸无效
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        self._stop_navigation()
        # 清理键盘钩子
        if hasattr(self, '_unregister_hotkeys'):
            self._unregister_hotkeys()
        super().closeEvent(event)
    
    def _shrink_window(self):
        """缩小悬浮窗"""
        if self.window_scale > 0.5:  # 最小缩小到50%
            self.window_scale -= 0.25
            self._apply_window_scale()
    
    def _expand_window(self):
        """放大悬浮窗"""
        if self.window_scale < 2.0:  # 最大放大到200%
            self.window_scale += 0.25
            self._apply_window_scale()
    
    def _toggle_collapse(self):
        """切换折叠/展开状态"""
        if self.collapse_btn.isChecked():
            # 折叠状态：隐藏内容区域，只显示地图
            self.content_container.hide()
            self.collapse_icon_label.setText("▲")
            # 先清空布局约束，然后设置精确大小
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            # 设置只显示地图的窗口大小（标题栏约30px + 地图200px + 边距）
            self.resize(400, 230)
            # 强制刷新
            self.show()
            self.raise_()
        else:
            # 展开状态：显示所有内容
            self.content_container.show()
            self.collapse_icon_label.setText("▼")
            # 设置展开后的窗口大小
            self.resize(400, 530)
            # 强制刷新
            self.show()
            self.raise_()
    
    def _apply_window_scale(self):
        """应用窗口缩放"""
        # 计算新的窗口和地图尺寸
        new_width = int(self.base_window_width * self.window_scale)
        new_height = int(self.base_window_height * self.window_scale)
        new_map_width = int(self.base_map_width * self.window_scale)
        new_map_height = int(self.base_map_height * self.window_scale)
        
        # 应用窗口大小
        self.resize(new_width, new_height)
        
        # 应用地图容器大小
        self.map_container.setFixedSize(new_map_width, new_map_height)
        
        # 更新地图显示（重新计算偏移）
        self._recalculate_map_offset()
        
    
    def _recalculate_map_offset(self):
        """重新计算地图偏移以保持中心位置（窗口缩放后调用）"""
        if hasattr(self, 'original_pixmap') and not self.original_pixmap.isNull():
            # 获取容器尺寸
            container_width = max(1, self.map_container.width())
            container_height = max(1, self.map_container.height())

            # 重新计算 fit_scale，确保地图铺满容器（无黑边）
            fit_scale = max(
                container_width / self.original_pixmap.width(),
                container_height / self.original_pixmap.height()
            )
            self.map_scale = max(0.01, fit_scale)

            # 计算缩放后的地图尺寸
            scaled_width = int(self.original_pixmap.width() * self.map_scale)
            scaled_height = int(self.original_pixmap.height() * self.map_scale)

            # 居中显示（地图 >= 容器时 offset 为负数，地图中心对齐容器中心）
            self.map_offset_x = (container_width - scaled_width) // 2
            self.map_offset_y = (container_height - scaled_height) // 2
            self._clamp_map_offset()

            # 注意：此处不再调用 setFixedSize 锁定 map_label 大小。
            # 否则后续 Ctrl+滚轮缩放地图时，setGeometry 受固定大小约束无法放大 map_label，
            # 会导致 map_label 不能覆盖整个容器，露出容器外的黑色背景（黑边越缩放越多）。
            # 大小由 update_map_display -> _update_map_render 中的 setGeometry 动态设置。
            self.update_map_display()
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        # Ctrl++ 放大窗口
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Plus:
            self._expand_window()
            event.accept()
        # Ctrl+- 缩小窗口
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Minus:
            self._shrink_window()
            event.accept()
        # Ctrl+0 重置窗口大小
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_0:
            self.window_scale = 1.0
            self._apply_window_scale()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def update_map_display(self, map_image_path=None, collect_data=None, map_pixmap=None):
        """更新地图显示

        Args:
            map_image_path: 地图文件路径（可选，当 map_pixmap 为空时使用）
            collect_data: 资源采集点数据
            map_pixmap: 已加载的 QPixmap（优先使用，支持从嵌入数据加载）
        """
        # 加载资源数据
        if collect_data:
            self.collect_data = collect_data
            self.selected_resources = set()  # 选中的资源集合
            
            # 填充资源菜单（多选复选框）
            self.resource_checkboxes = {}
            for resource_name in sorted(self.collect_data.keys()):
                action = self.resource_menu.addAction(resource_name)
                action.setCheckable(True)
                action.setChecked(True)  # 默认全选
                action.triggered.connect(lambda checked, name=resource_name: self._on_resource_toggled(name, checked))
                self.resource_checkboxes[resource_name] = action
                self.selected_resources.add(resource_name)
            
            # 预加载资源个体图标到缓存
            self._resource_icon_cache = {}
            sc_dir = get_resource_path(os.path.join("image", "sc"))
            for rname, rinfo in self.collect_data.items():
                icon_file = rinfo.get('icon', '')
                if icon_file:
                    icon_path = os.path.join(sc_dir, icon_file)
                    if os.path.exists(icon_path):
                        pix = QPixmap(icon_path)
                        if not pix.isNull():
                            self._resource_icon_cache[rname] = pix
            
            # 初始化按钮文本
            self._update_resource_button_text()
        
        # 加载眠枭之星数据
        if not self.owl_stars_data:
            self._load_owl_stars_data()
            
            # 填充眠枭之星菜单（多选复选框）
            for star_name in sorted(self.owl_stars_data.keys()):
                action = self.owl_stars_menu.addAction(star_name)
                action.setCheckable(True)
                action.setChecked(False)  # 默认不选中
                action.triggered.connect(lambda checked, name=star_name: self._on_owl_star_toggled(name, checked))
                self.owl_stars_checkboxes[star_name] = action
        
        # 加载宝箱数据并合并到owl_stars_data
        if not self.chests_loaded:
            self._load_chests_data_and_merge()
        
        if map_pixmap is not None and not map_pixmap.isNull():
            # 优先使用已加载的 pixmap（来自嵌入数据）
            self.original_pixmap = map_pixmap
        elif map_image_path and os.path.exists(map_image_path):
            # 回退：从文件路径加载
            self.original_pixmap = QPixmap(map_image_path)
        else:
            # 两者都不可用，显示默认文本
            self.map_label.setText("地图加载中...")
            return

        if not self.original_pixmap.isNull():
            # 自动适配：用 max 比例保证地图铺满容器（无黑色边框），看到地图中心
            container_width = max(1, self.map_container.width())
            container_height = max(1, self.map_container.height())
            if not self.original_pixmap.isNull() and self.original_pixmap.width() > 0:
                fit_scale = max(
                    container_width / self.original_pixmap.width(),
                    container_height / self.original_pixmap.height()
                )
                self.map_scale = max(0.01, fit_scale)
            scaled_width = int(self.original_pixmap.width() * self.map_scale)
            scaled_height = int(self.original_pixmap.height() * self.map_scale)

            # 居中显示（地图大于容器时 offset 为负，地图中心对齐容器中心）
            self.map_offset_x = (container_width - scaled_width) // 2
            self.map_offset_y = (container_height - scaled_height) // 2
            self._clamp_map_offset()

            self._update_map_render()
        else:
            self.map_label.setText("地图加载失败")
    
    def _on_resource_changed(self, resource_name):
        """资源筛选变化（旧方法，保留兼容）"""
        self.selected_resource = resource_name
        self._update_resource_markers()
    
    def _toggle_resource_menu(self):
        """显示/隐藏资源选择菜单"""
        pos = self.resource_btn.mapToGlobal(QPoint(0, self.resource_btn.height()))
        self.resource_menu.exec(pos)
    
    def _on_resource_toggled(self, resource_name, checked):
        """资源复选框状态变化"""
        if checked:
            self.selected_resources.add(resource_name)
        else:
            self.selected_resources.discard(resource_name)
        
        # 更新按钮文本
        self._update_resource_button_text()
        
        # 触发地图重绘
        self._update_resource_markers()
    
    def _set_all_resources(self, show_all):
        """全选/全不选"""
        for name, action in self.resource_checkboxes.items():
            action.setChecked(show_all)
        
        if show_all:
            self.selected_resources = set(self.collect_data.keys())
        else:
            self.selected_resources.clear()
        
        # 更新按钮文本
        self._update_resource_button_text()
        
        # 触发地图重绘
        self._update_resource_markers()
    
    def _update_resource_button_text(self):
        """更新资源按钮显示的文本"""
        total = len(self.collect_data)
        selected = len(self.selected_resources)
        
        if selected == 0:
            self.resource_btn.setText("全部隐藏")
        elif selected == total:
            self.resource_btn.setText("全部显示")
        else:
            self.resource_btn.setText(f"已选 {selected}/{total}")
    
    def _update_resource_markers(self):
        """更新资源标记显示 - 池化QLabel复用，使用个体资源图标"""
        # 计算需要显示的标记列表
        draw_data = []
        need_markers = []

        if self.collect_data and getattr(self, 'selected_resources', set()):
            base_icon_size = 16
            icon_size = self._compute_icon_size(base_icon_size)
            container_rect = self.map_container.rect()
            label_pos = self.map_label.pos()
            icon_cache = getattr(self, '_resource_icon_cache', {})

            for resource_name in list(self.selected_resources):
                resource_info = self.collect_data.get(resource_name, {})
                points = resource_info.get('points', [])
                # 使用个体资源图标
                icon = icon_cache.get(resource_name)
                if not icon or icon.isNull():
                    # 回退到 hua/ks 图标
                    special_resources = {'黄石榴石', '蓝晶碧玺', '黑晶琉璃', '紫莲刚玉'}
                    use_ks = any(special in resource_name for special in special_resources)
                    icon = self.ks_icon if use_ks and not self.ks_icon.isNull() else self.hua_icon

                for point in points:
                    map_x, map_y = self._game_to_map_coords(point.get('lat', 0), point.get('lng', 0))
                    screen_x = self.map_offset_x + (map_x * self.map_scale)
                    screen_y = self.map_offset_y + (map_y * self.map_scale)
                    if (screen_x < -icon_size or screen_x > container_rect.width() + icon_size or
                        screen_y < -icon_size or screen_y > container_rect.height() + icon_size):
                        continue
                    relative_x = screen_x - label_pos.x()
                    relative_y = screen_y - label_pos.y()
                    draw_data.append({'icon': icon, 'x': relative_x, 'y': relative_y, 'size': icon_size})
                    need_markers.append((int(screen_x - icon_size/2), int(screen_y - icon_size/2), icon_size, resource_name))

        # 池化复用QLabel
        old_count = len(self.resource_markers)
        new_count = len(need_markers)
        reuse = min(old_count, new_count)

        for i in range(reuse):
            m = self.resource_markers[i]
            x, y, s, tip = need_markers[i]
            m.setGeometry(x, y, s, s)
            m.setToolTip(tip)
            m.show()

        if new_count > old_count:
            for i in range(old_count, new_count):
                x, y, s, tip = need_markers[i]
                marker = QLabel(self.map_container)
                marker.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                marker.setFixedSize(s, s)
                marker.setGeometry(x, y, s, s)
                marker.setToolTip(tip)
                marker.setStyleSheet("background: transparent; border: none;")
                marker.show()
                self.resource_markers.append(marker)
        elif new_count < old_count:
            for i in range(new_count, old_count):
                m = self.resource_markers[i]
                m.setParent(None)
                m.deleteLater()
            self.resource_markers = self.resource_markers[:new_count]

        self.map_label.set_resource_data(draw_data)
    
    def _load_owl_stars_data(self):
        """加载眠枭之星数据"""
        try:
            base_dir = os.path.join(os.path.dirname(__file__), '..')
            owl_stars_file = os.path.join(base_dir, 'owl_stars.json')
            if os.path.exists(owl_stars_file):
                with open(owl_stars_file, 'r', encoding='utf-8') as f:
                    self.owl_stars_data = json.load(f)
        except Exception as e:
            pass  # 静默失败
    
    def _load_chests_data_and_merge(self):
        """加载宝箱数据并合并到owl_stars_data"""
        try:
            base_dir = os.path.join(os.path.dirname(__file__), '..')
            chests_file = os.path.join(base_dir, 'chests.json')
            if os.path.exists(chests_file):
                with open(chests_file, 'r', encoding='utf-8') as f:
                    chests_data = json.load(f)
                    # 将宝箱数据合并到owl_stars_data中
                    self.owl_stars_data.update(chests_data)
                    
                    # 填充宝箱菜单（多选复选框）
                    for chest_name in sorted(chests_data.keys()):
                        action = self.owl_stars_menu.addAction(chest_name)
                        action.setCheckable(True)
                        action.setChecked(False)  # 默认不选中
                        action.triggered.connect(lambda checked, name=chest_name: self._on_owl_star_toggled(name, checked))
                        self.owl_stars_checkboxes[chest_name] = action
                    
                    self.chests_loaded = True
        except Exception as e:
            pass  # 静默失败
    
    def _toggle_owl_stars_menu(self):
        """显示/隐藏眠枭之星选择菜单"""
        pos = self.owl_stars_btn.mapToGlobal(QPoint(0, self.owl_stars_btn.height()))
        self.owl_stars_menu.exec(pos)
    
    def _on_owl_star_toggled(self, star_name, checked):
        """眠枭之星复选框状态变化"""
        if checked:
            self.selected_owl_stars.add(star_name)
        else:
            self.selected_owl_stars.discard(star_name)
        
        # 更新按钮文本
        self._update_owl_stars_button_text()
        
        # 触发地图重绘
        self._update_owl_star_markers()
    
    def _set_all_owl_stars(self, show_all):
        """全选/全不选眠枭之星"""
        for name, action in self.owl_stars_checkboxes.items():
            action.setChecked(show_all)
        
        if show_all:
            self.selected_owl_stars = set(self.owl_stars_data.keys())
        else:
            self.selected_owl_stars.clear()
        
        # 更新按钮文本
        self._update_owl_stars_button_text()
        
        # 触发地图重绘
        self._update_owl_star_markers()
    
    def _update_owl_stars_button_text(self):
        """更新眠枭之星按钮显示的文本"""
        total = len(self.owl_stars_data)
        selected = len(self.selected_owl_stars)
        
        if selected == 0:
            self.owl_stars_btn.setText("全部隐藏")
        elif selected == total:
            self.owl_stars_btn.setText("全部显示")
        else:
            self.owl_stars_btn.setText(f"已选 {selected}/{total}")
    
    def _game_to_map_coords(self, lat, lng):
        """将中心原点坐标转换为地图像素坐标（新地图 8192x8192）
        
        Args:
            lat: 中心原点 Y 坐标（-4096 ~ +4096，与 ResourceExporter.java 输出一致）
            lng: 中心原点 X 坐标（-4096 ~ +4096，与 ResourceExporter.java 输出一致）
            
        Returns:
            (x, y): 显示地图像素坐标（0 ~ map_width/height）
        """
        scale = self.original_pixmap.width() / 8192.0 if hasattr(self, 'original_pixmap') and not self.original_pixmap.isNull() else 0.5
        # 中心原点 → 左上角原点：X 平移 +4096，Y 反转后平移 +4096
        x = (lng + 4096) * scale
        y = (4096 - lat) * scale
        return x, y
    
    def _update_owl_star_markers(self):
        """更新眠枭之星和宝箱标记显示 - 池化复用+图标缓存"""
        need_markers = []

        if self.owl_stars_data:
            base_icon_size = 16
            icon_size = self._compute_icon_size(base_icon_size)
            container_rect = self.map_container.rect()

            for item_name in self.selected_owl_stars:
                if item_name not in self.owl_stars_data:
                    continue
                items = self.owl_stars_data[item_name].get('points', [])

                if '金' in item_name:
                    current_pixmap = self._jx_icon
                elif '蓝' in item_name:
                    current_pixmap = self._lx_icon
                elif '宝箱' in item_name:
                    current_pixmap = self._xz_icon
                elif '乐谱' in item_name:
                    current_pixmap = self._yp_icon
                else:
                    current_pixmap = None

                if not current_pixmap or current_pixmap.isNull():
                    continue

                for item in items:
                    map_x, map_y = self._game_to_map_coords(item.get('lat', 0), item.get('lng', 0))
                    screen_x = self.map_offset_x + (map_x * self.map_scale)
                    screen_y = self.map_offset_y + (map_y * self.map_scale)

                    item_icon_size = self._compute_icon_size(24, 40) if '乐谱' in item_name else icon_size

                    if (screen_x < -item_icon_size or screen_x > container_rect.width() + item_icon_size or
                        screen_y < -item_icon_size or screen_y > container_rect.height() + item_icon_size):
                        continue

                    need_markers.append((int(screen_x - item_icon_size/2), int(screen_y - item_icon_size/2),
                                         item_icon_size, current_pixmap, item_name))

        old_count = len(self.owl_star_markers)
        new_count = len(need_markers)
        reuse = min(old_count, new_count)

        for i in range(reuse):
            m = self.owl_star_markers[i]
            x, y, s, pix, tip = need_markers[i]
            scaled = pix.scaled(s, s, Qt.KeepAspectRatio, Qt.FastTransformation)
            m.setPixmap(scaled)
            m.setGeometry(x, y, s, s)
            m.setToolTip(tip)
            m.show()

        if new_count > old_count:
            for i in range(old_count, new_count):
                x, y, s, pix, tip = need_markers[i]
                scaled = pix.scaled(s, s, Qt.KeepAspectRatio, Qt.FastTransformation)
                marker = QLabel(self.map_container)
                marker.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                marker.setPixmap(scaled)
                marker.setGeometry(x, y, s, s)
                marker.setToolTip(tip)
                marker.setStyleSheet("background: transparent; border: none;")
                marker.show()
                self.owl_star_markers.append(marker)
        elif new_count < old_count:
            for i in range(new_count, old_count):
                m = self.owl_star_markers[i]
                m.setParent(None)
                m.deleteLater()
            self.owl_star_markers = self.owl_star_markers[:new_count]
    
    def _shift_markers(self, dx, dy):
        """拖拽时快速平移所有标记（不重建控件）"""
        for m in self.resource_markers:
            g = m.geometry()
            m.setGeometry(g.x() + dx, g.y() + dy, g.width(), g.height())
        for m in self.owl_star_markers:
            g = m.geometry()
            m.setGeometry(g.x() + dx, g.y() + dy, g.width(), g.height())

    def _update_map_render(self):
        """更新地图渲染（带缓存：仅在缩放值改变时重新缩放）"""
        if not hasattr(self, 'original_pixmap') or self.original_pixmap.isNull():
            return

        scale_changed = abs(self.map_scale - self._cached_scale) > 0.01

        if scale_changed or self._cached_scaled_pixmap is None:
            scaled_width = max(1, int(self.original_pixmap.width() * self.map_scale))
            scaled_height = max(1, int(self.original_pixmap.height() * self.map_scale))

            self._cached_scaled_pixmap = self.original_pixmap.scaled(
                scaled_width,
                scaled_height,
                Qt.KeepAspectRatio,
                Qt.FastTransformation
            )
            self._cached_scale = self.map_scale
            self.map_label.setPixmap(self._cached_scaled_pixmap)

        self.map_label.setGeometry(
            int(self.map_offset_x),
            int(self.map_offset_y),
            self._cached_scaled_pixmap.width(),
            self._cached_scaled_pixmap.height()
        )

        self.map_label.set_map_scale(self.map_scale)
        self._pixmap_needs_update = False

        if self._markers_needs_update:
            self._update_resource_markers()
            self._update_owl_star_markers()
            self._update_route_display()
            self._markers_needs_update = False
    
    def update_position(self, current_lat, current_lng, target_lat=None, target_lng=None):
        """更新位置信息"""
        self.current_pos_label.setText(f"当前位置: ({current_lat}, {current_lng})")
        if target_lat is not None and target_lng is not None:
            self.target_pos_label.setText(f"目标位置: ({target_lat}, {target_lng})")
    
    def toggle_lock(self):
        """切换锁定状态"""
        self.is_locked = not self.is_locked
    
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
        
        painter.end()
    
    def mouseMoveEvent(self, event):
        """鼠标移动实现拖拽"""
        # 地图拖拽平移
        if self.is_dragging_map and self.drag_start_pos:
            delta = event.pos() - self.drag_start_pos
            self.map_offset_x = self.drag_start_offset_x + delta.x()
            self.map_offset_y = self.drag_start_offset_y + delta.y()
            self._clamp_map_offset()
            self._pixmap_needs_update = False
            self.map_label.setGeometry(
                int(self.map_offset_x),
                int(self.map_offset_y),
                self._cached_scaled_pixmap.width(),
                self._cached_scaled_pixmap.height()
            )
            self._shift_markers(int(delta.x()), int(delta.y()))
            self.map_label.update()
            event.accept()
            return
        
        # 窗口拖拽
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None and not self.is_locked:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        self.is_dragging_map = False
        self.drag_start_pos = None
        self.drag_pos = None
        event.accept()
    
    def wheelEvent(self, event):
        """滚轮缩放"""
        # 检查是否在地图区域内
        if hasattr(self, 'map_label') and self.map_label.underMouse():
            # Ctrl + 滚轮缩放
            if event.modifiers() & Qt.ControlModifier:
                delta = event.angleDelta().y()
                
                # 记录缩放前的偏移和缩放比例
                old_scale = self.map_scale
                mouse_pos = event.position().toPoint()
                
                # 计算鼠标在地图上的相对位置（相对于当前偏移）
                mouse_map_x = mouse_pos.x() - self.map_offset_x
                mouse_map_y = mouse_pos.y() - self.map_offset_y
                
                # 执行缩放
                if delta > 0:
                    self.map_scale *= 1.2  # 放大
                else:
                    self.map_scale *= 0.8  # 缩小

                # 限制缩放范围：最小缩放 = 地图铺满容器（无黑边），最大 10 倍
                if hasattr(self, 'original_pixmap') and not self.original_pixmap.isNull():
                    cw = self.map_container.width() if hasattr(self, 'map_container') else 360
                    ch = self.map_container.height() if hasattr(self, 'map_container') else 200
                    min_scale = max(cw / self.original_pixmap.width(),
                                    ch / self.original_pixmap.height())
                    self.map_scale = max(min_scale, min(self.map_scale, 10.0))
                
                # 计算新的偏移，使鼠标位置保持不变
                self.map_offset_x = mouse_pos.x() - (mouse_map_x * self.map_scale / old_scale)
                self.map_offset_y = mouse_pos.y() - (mouse_map_y * self.map_scale / old_scale)

                self._clamp_map_offset()
                self._pixmap_needs_update = True
                self._markers_needs_update = True
                self._do_deferred_render()
                event.accept()
                return
        
        super().wheelEvent(event)

    def _clamp_map_offset(self):
        """限制地图偏移：到地图边缘时直接拉不动（不露出地图外的黑色区域）
        核心策略：保证地图始终 >= 容器，offset 限制在 [container-scaled, 0]。
        """
        if not hasattr(self, 'map_container') or not hasattr(self, 'map_label'):
            return
        if not hasattr(self, 'original_pixmap') or self.original_pixmap.isNull():
            return
        cw = max(1, self.map_container.width())
        ch = max(1, self.map_container.height())
        if cw <= 1 or ch <= 1:
            return
        scale = self.map_scale if self.map_scale > 0 else 1.0
        lw = self.original_pixmap.width() * scale
        lh = self.original_pixmap.height() * scale
        # 关键：如果地图比容器小，强制增大 scale 让地图填满容器
        if lw < cw:
            scale = cw / self.original_pixmap.width()
            self.map_scale = scale
            lw = self.original_pixmap.width() * scale
        if lh < ch:
            scale = max(scale, ch / self.original_pixmap.height())
            self.map_scale = scale
            lh = self.original_pixmap.height() * scale
        # offset 限制在 [container-scaled, 0]：到边缘时拉不动
        self.map_offset_x = max(cw - lw, min(0, self.map_offset_x))
        self.map_offset_y = max(ch - lh, min(0, self.map_offset_y))
    
    def _get_dpi_scale(self):
        """获取系统DPI缩放因子"""
        try:
            # 方法1: 使用 GetDeviceCaps (系统默认 DPI)
            dc = windll.user32.GetDC(0)
            dpi_x = windll.gdi32.GetDeviceCaps(dc, 88)  # LOGPIXELSX
            dpi_y = windll.gdi32.GetDeviceCaps(dc, 90)  # LOGPIXELSY
            windll.user32.ReleaseDC(0, dc)
            scale = max(dpi_x, dpi_y) / 96.0
            return scale
        except Exception as e:
            return 1.0
    
    def _toggle_route_edit_mode(self):
        """切换路线编辑模式"""
        self.route_edit_mode = self.draw_route_btn.isChecked()
        if self.route_edit_mode:
            # 自动取消检查点模式
            self.is_placing_checkpoint = False
            self.add_checkpoint_btn.setChecked(False)
        else:
            pass  # 退出路线编辑模式
    
    def _toggle_checkpoint_mode(self):
        """切换检查点放置模式"""
        self.is_placing_checkpoint = self.add_checkpoint_btn.isChecked()
        if self.is_placing_checkpoint:
            # 自动启用路线编辑模式
            self.route_edit_mode = True
            self.draw_route_btn.setChecked(True)
        else:
            pass  # 退出检查点模式
    
    def _clear_route(self):
        """清除路线"""
        self.route_history.append([seg.copy() for seg in self.route_segments])  # 保存当前状态用于撤回
        self.route_segments = []
        if hasattr(self, 'map_label'):
            self.map_label.clear_route()
    
    def _break_route(self):
        """断开路线 - 开始新的路线段（用于传送点分段）"""
        # 如果当前有路线段，保存状态到历史
        if self.route_segments:
            self.route_history.append([seg.copy() for seg in self.route_segments])
        # 添加一个空的新路线段
        if not self.route_segments or len(self.route_segments[-1]) > 0:
            self.route_segments.append([])
    
    def _update_route_display(self):
        """更新路线显示（将原始坐标转换为显示坐标）"""
        if not hasattr(self, 'map_label'):
            return
        
        # 同步路线颜色到 MapLabel
        if hasattr(self, 'route_color'):
            self.map_label.route_color = self.route_color
        
        # 将多段路线合并为单个点列表（保持段之间不连接）
        # 通过在段之间插入 None 来标记断开
        display_points = []
        for seg_idx, segment in enumerate(self.route_segments):
            for (x, y, is_checkpoint) in segment:
                display_x = x * self.map_scale
                display_y = y * self.map_scale
                display_points.append((display_x, display_y, is_checkpoint))
            # 在段之间插入 None 标记断开（最后一段不插入）
            if seg_idx < len(self.route_segments) - 1:
                display_points.append(None)
        
        self.map_label.set_route_points(display_points)
    
    def _export_route(self):
        """导出路线到文件"""
        # 检查是否有路线
        has_route = any(len(seg) > 0 for seg in self.route_segments)
        if not has_route:
            return
        
        # 打开文件保存对话框
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出路线",
            "",
            "JSON文件 (*.json);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                # 准备路线数据（保存多段路线）
                route_data = {
                    "version": "2.1",
                    "name": self._current_route_name,
                    "color": self._get_color_name(self.route_color),
                    "segments": [
                        [{"x": float(p[0]), "y": float(p[1]), "checkpoint": p[2]} for p in seg]
                        for seg in self.route_segments
                    ]
                }
                
                # 保存到文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(route_data, f, ensure_ascii=False, indent=2)
                
            except Exception as e:
                pass  # 忽略导出错误
    
    def _import_route(self):
        """从文件导入路线"""
        # 打开文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入路线",
            "",
            "JSON文件 (*.json);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                # 读取并解析文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    route_data = json.load(f)
                
                # 保存当前路线到 saved_routes（如果有内容）
                self._save_current_route()
                
                # 保存当前状态到历史
                self.route_history.append([seg.copy() for seg in self.route_segments])
                
                # 提取路线点（支持多段路线格式）
                self.route_segments = []
                
                # 尝试读取新版本（多段路线）
                if "segments" in route_data:
                    for seg_data in route_data.get("segments", []):
                        segment = []
                        for p in seg_data:
                            x = p.get("x", 0)
                            y = p.get("y", 0)
                            is_checkpoint = p.get("checkpoint", False)
                            segment.append((x, y, is_checkpoint))
                        if segment:
                            self.route_segments.append(segment)
                else:
                    # 兼容旧版本（单段路线）
                    segment = []
                    for p in route_data.get("points", []):
                        x = p.get("x", 0)
                        y = p.get("y", 0)
                        is_checkpoint = p.get("checkpoint", False)
                        segment.append((x, y, is_checkpoint))
                    if segment:
                        self.route_segments.append(segment)
                
                # 读取路线颜色
                route_color_name = route_data.get("color", "green")
                self._apply_route_color(route_color_name)
                
                # 读取路线名称
                route_name = route_data.get("name", "")
                if not route_name:
                    route_name = os.path.splitext(os.path.basename(file_path))[0]
                self._current_route_name = route_name
                if hasattr(self, 'route_name_label'):
                    self.route_name_label.setText(route_name)
                
                # 添加到已保存路线列表
                self._add_route_to_saved(route_name)
                
                # 更新显示
                self._update_route_display()
                
            except Exception as e:
                pass  # 忽略导入错误
    
    # ============ 路线管理功能 ============
    def _save_current_route(self):
        """保存当前路线到 saved_routes"""
        has_route = any(len(seg) > 0 for seg in self.route_segments)
        if not has_route:
            return
        color_name = self._get_color_name(self.route_color)
        for route in self.saved_routes:
            if route["name"] == self._current_route_name:
                route["segments"] = [seg.copy() for seg in self.route_segments]
                route["color"] = color_name
                return
        self.saved_routes.append({
            "name": self._current_route_name,
            "segments": [seg.copy() for seg in self.route_segments],
            "color": color_name
        })
    
    def _add_route_to_saved(self, route_name):
        """添加当前路线到已保存列表"""
        has_route = any(len(seg) > 0 for seg in self.route_segments)
        if not has_route:
            return
        color_name = self._get_color_name(self.route_color)
        for route in self.saved_routes:
            if route["name"] == route_name:
                route["segments"] = [seg.copy() for seg in self.route_segments]
                route["color"] = color_name
                return
        self.saved_routes.append({
            "name": route_name,
            "segments": [seg.copy() for seg in self.route_segments],
            "color": color_name
        })
    
    def _get_color_name(self, color):
        """获取颜色对应的名称"""
        color_map = {
            (34, 197, 94): "green",
            (239, 68, 68): "red",
            (59, 130, 246): "blue",
            (0, 0, 0): "black",
            (124, 58, 237): "purple",
            (255, 165, 0): "orange",
            (255, 255, 255): "white",
        }
        r = color.red()
        g = color.green()
        b = color.blue()
        for (cr, cg, cb), name in color_map.items():
            if abs(r - cr) <= 5 and abs(g - cg) <= 5 and abs(b - cb) <= 5:
                return name
        return "green"
    
    def _apply_route_color(self, color_name):
        """根据颜色名称应用路线颜色"""
        color_map = {
            "green": QColor(34, 197, 94, 255),
            "red": QColor(239, 68, 68, 255),
            "blue": QColor(59, 130, 246, 255),
            "black": QColor(0, 0, 0, 255),
            "purple": QColor(124, 58, 237, 255),
            "orange": QColor(255, 165, 0, 255),
            "white": QColor(255, 255, 255, 255),
        }
        self.route_color = color_map.get(color_name, QColor(34, 197, 94, 255))
        if hasattr(self, 'map_label'):
            self.map_label.route_color = self.route_color
    
    def _show_route_list_menu(self):
        """显示路线列表菜单"""
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(30, 30, 38, 0.95);
                border: 1px solid rgba(124, 58, 237, 0.5);
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
                color: #e4e4e7;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: rgba(124, 58, 237, 0.3);
            }
        """)
        
        if not self.saved_routes:
            empty_action = menu.addAction("（暂无保存的路线）")
            empty_action.setEnabled(False)
        else:
            for idx, route in enumerate(self.saved_routes):
                route_name = route["name"]
                color_name = route.get("color", "green")
                color_display = self._get_color_display_name(color_name)
                display_text = f"{route_name}  [{color_display}]"
                
                action = menu.addAction(display_text)
                action.setData(idx)
                action.triggered.connect(lambda checked, i=idx: self._switch_to_route(i))
                
                sub_menu = QMenu()
                sub_menu.setStyleSheet("""
                    QMenu {
                        background-color: rgba(30, 30, 38, 0.95);
                        border: 1px solid rgba(239, 68, 68, 0.5);
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QMenu::item {
                        padding: 6px 16px;
                        color: #ef4444;
                        font-size: 11px;
                    }
                    QMenu::item:selected {
                        background-color: rgba(239, 68, 68, 0.3);
                    }
                """)
                delete_action = sub_menu.addAction("删除")
                delete_action.triggered.connect(lambda checked, i=idx: self._delete_route(i))
                action.setMenu(sub_menu)
        
        pos = self.route_list_btn.mapToGlobal(QPoint(0, self.route_list_btn.height()))
        menu.exec(pos)
    
    def _show_color_menu(self):
        """显示颜色选择菜单"""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QPixmap, QPainter, QIcon
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(30, 30, 38, 0.95);
                border: 1px solid rgba(124, 58, 237, 0.5);
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
                color: #e4e4e7;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: rgba(124, 58, 237, 0.3);
            }
        """)
        
        color_options = [
            ("默认", "green", QColor(34, 197, 94)),
            ("红色", "red", QColor(239, 68, 68)),
            ("深蓝色", "blue", QColor(59, 130, 246)),
            ("黑色", "black", QColor(0, 0, 0)),
            ("深紫色", "purple", QColor(124, 58, 237)),
            ("橙色", "orange", QColor(255, 165, 0)),
            ("白色", "white", QColor(255, 255, 255)),
        ]
        
        for display_name, color_name, color in color_options:
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1))
            painter.drawRoundedRect(0, 0, 16, 16, 3, 3)
            painter.end()
            
            action = menu.addAction(QIcon(pixmap), display_name)
            action.triggered.connect(lambda checked, cn=color_name: self._on_color_selected(cn))
        
        pos = self.color_btn.mapToGlobal(QPoint(0, self.color_btn.height()))
        menu.exec(pos)
    
    def _on_color_selected(self, color_name):
        """颜色选择回调"""
        self._apply_route_color(color_name)
        color_map = {
            "green": (34, 197, 94),
            "red": (239, 68, 68),
            "blue": (59, 130, 246),
            "black": (0, 0, 0),
            "purple": (124, 58, 237),
            "orange": (255, 165, 0),
            "white": (255, 255, 255),
        }
        rgb = color_map.get(color_name, (34, 197, 94))
        r, g, b = rgb
        text_color = "#1a1a2e" if color_name == "white" else "#e4e4e7"
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba({r}, {g}, {b}, 0.3);
                color: {text_color};
                border: 1px solid rgba({r}, {g}, {b}, 0.5);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba({r}, {g}, {b}, 0.5);
            }}
        """)
        self._update_route_display()
    
    def _on_route_name_changed(self):
        """路线名称编辑完成回调"""
        new_name = self.route_name_label.text().strip()
        if not new_name:
            new_name = "未命名路线"
            self.route_name_label.setText(new_name)
        self._current_route_name = new_name
        self._save_current_route()
    
    def _switch_to_route(self, route_index):
        """切换到指定路线"""
        if route_index < 0 or route_index >= len(self.saved_routes):
            return
        self._save_current_route()
        route = self.saved_routes[route_index]
        self.route_history.append([seg.copy() for seg in self.route_segments])
        self.route_segments = [seg.copy() for seg in route.get("segments", [])]
        self._current_route_name = route["name"]
        if hasattr(self, 'route_name_label'):
            self.route_name_label.setText(route["name"])
        color_name = route.get("color", "green")
        self._apply_route_color(color_name)
        self._update_route_display()
    
    def _delete_route(self, route_index):
        """删除指定路线"""
        if route_index < 0 or route_index >= len(self.saved_routes):
            return
        del self.saved_routes[route_index]
        if not self.saved_routes:
            self._current_route_name = "未命名路线"
            if hasattr(self, 'route_name_label'):
                self.route_name_label.setText("未命名路线")
    
    def _get_color_display_name(self, color_name):
        """获取颜色显示名称"""
        color_map = {
            "green": "默认",
            "red": "红色",
            "blue": "深蓝色",
            "black": "黑色",
            "purple": "深紫色",
            "orange": "橙色",
            "white": "白色",
        }
        return color_map.get(color_name, "默认")
    
    # ============ 路线管理功能结束 ============
    
    def _toggle_mouse_interaction(self):
        """切换鼠标交互（穿透）状态"""
        self.mouse_enabled = not self.mouse_enabled
        
        # 更新按钮状态
        self.penetrate_btn.setChecked(not self.mouse_enabled)
        
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
            except Exception as e:
                pass
            
            # 更新按钮样式和图标（绿色=可交互）
            self.penetrate_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(34, 197, 94, 0.2);
                    border: 1.5px solid #22c55e;
                    border-radius: 14px;
                }
                QPushButton:hover {
                    background-color: rgba(34, 197, 94, 0.3);
                    border: 1.5px solid #16a34a;
                }
                QPushButton:checked {
                    background-color: rgba(168, 85, 247, 0.2);
                    border: 1.5px solid #a855f7;
                }
            """)
            self.penetrate_btn.findChild(QLabel).setStyleSheet("color: #22c55e; font-size: 16px;")
            self.penetrate_btn.setToolTip("鼠标穿透 (Alt+M)\n绿色=可交互，紫色=穿透")
            
            # 更新状态标签（绿色=可交互）
            self.hotkey_status_label.setText("✓ 可交互状态 | Alt+M 切换")
            self.hotkey_status_label.setStyleSheet("color: #22c55e; font-size: 10px;")
            
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
            except Exception as e:
                pass
            
            # 更新按钮样式和图标（紫色=穿透）
            self.penetrate_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(168, 85, 247, 0.2);
                    border: 1.5px solid #a855f7;
                    border-radius: 14px;
                }
                QPushButton:hover {
                    background-color: rgba(168, 85, 247, 0.3);
                    border: 1.5px solid #9333ea;
                }
                QPushButton:checked {
                    background-color: rgba(34, 197, 94, 0.2);
                    border: 1.5px solid #22c55e;
                }
            """)
            self.penetrate_btn.findChild(QLabel).setStyleSheet("color: #a855f7; font-size: 16px;")
            self.penetrate_btn.setToolTip("鼠标穿透 (Alt+M)\n绿色=可交互，紫色=穿透")
            
            # 更新状态标签（紫色=穿透）
            self.hotkey_status_label.setText("✓ 穿透状态 | Alt+M 切换")
            self.hotkey_status_label.setStyleSheet("color: #a855f7; font-size: 10px;")
            
    
    def _undo_last_point(self):
        """撤回上一个路线点"""
        if len(self.route_history) > 0:
            last_state = self.route_history.pop()
            self.route_segments = last_state
            self._update_route_display()
        else:
            pass  # 没有可撤回的操作
    
    def _change_opacity(self, value):
        """改变窗口透明度"""
        self.window_opacity = value / 100.0
        self.setWindowOpacity(self.window_opacity)
        self.opacity_value_label.setText(f"{value}%")
    
    def _toggle_pin_mode(self):
        """切换图钉模式（改进图标）"""
        self.pin_mode = self.pin_btn.isChecked()
        
        # 更新图标
        if self.pin_mode:
            self.pin_icon_label.setText("🔓")  # 锁定状态时显示解锁（表示可以拖动地图）
            self.pin_btn.setToolTip("窗口已锁定，拖动地图")
        else:
            self.pin_icon_label.setText("🔒")  # 非锁定状态显示锁（表示可以拖动窗口）
            self.pin_btn.setToolTip("锁定窗口，拖动地图")
        
        if self.pin_mode:
            pass  # 图钉模式已激活
        else:
            pass  # 非图钉模式
    
    def mousePressEvent(self, event):
        """鼠标按下 - 点击窗口任意位置激活交互模式"""
        # 如果当前是穿透模式，点击窗口任意位置都切换为可交互模式
        if not self.mouse_enabled and event.button() == Qt.LeftButton:
            self._toggle_mouse_interaction()
            event.accept()
            return
        
        # 检查是否在路线编辑模式且点击在地图上
        if self.route_edit_mode and hasattr(self, 'map_label'):
            # 检查鼠标是否在map_label区域内
            if self.map_label.geometry().contains(event.pos()):
                if event.button() == Qt.LeftButton:
                    # 计算点击在地图上的坐标（转换为原始地图坐标）
                    label_pos = self.map_label.pos()
                    # 获取点击相对于map_label的坐标
                    relative_x = event.pos().x() - label_pos.x()
                    relative_y = event.pos().y() - label_pos.y()
                    
                    # 调试信息
                    
                    # 关键！正确的反向转换（和资源标记的正向转换保持一致）
                    # 资源标记的正向转换是：
                    # screen_x = map_offset_x + (map_x * map_scale)
                    # screen_y = map_offset_y + (map_y * map_scale)
                    # 其中 screen_x 是相对于 map_container 的坐标
                    
                    # 但是 event.pos() 是相对于窗口的坐标，我们需要先找到相对于 map_container 的坐标
                    # 让我们找到 map_container 在窗口中的位置
                    container_pos = self.map_container.pos()
                    
                    # 计算点击相对于 map_container 的坐标
                    click_container_x = event.pos().x() - container_pos.x()
                    click_container_y = event.pos().y() - container_pos.y()
                    
                    
                    # 现在逆向计算：map_x = (click_container_x - map_offset_x) / map_scale
                    original_x = (click_container_x - self.map_offset_x) / self._screen_scale_x()
                    original_y = (click_container_y - self.map_offset_y) / self._screen_scale_y()
                    
                    
                    # 打印前3个资源标记的位置
                    if self.collect_data:
                        count = 0
                        for resource_name, info in self.collect_data.items():
                            for point in info.get('points', []):
                                if count >= 3:
                                    break
                                lat, lng = point.get('lat', 0), point.get('lng', 0)
                                map_x, map_y = self._game_to_map_coords(lat, lng)
                                count += 1
                            if count >= 3:
                                break
                    
                    # 添加路线点到当前路线段（保存原始坐标）
                    self.route_history.append([seg.copy() for seg in self.route_segments])  # 保存当前状态用于撤回
                    
                    # 如果没有路线段，创建一个新的
                    if not self.route_segments:
                        self.route_segments.append([])
                    
                    # 添加到最后一个路线段
                    self.route_segments[-1].append((original_x, original_y, self.is_placing_checkpoint))
                    
                    # 更新显示
                    self._update_route_display()
                    
                    point_type = "检查点" if self.is_placing_checkpoint else "路线点"
                    
                    event.accept()
                    return
        
        # 检查是否在地图容器区域内（平移地图）
        if hasattr(self, 'map_label') and self.map_label.underMouse():
            if event.button() == Qt.LeftButton and not self.route_edit_mode:
                # 在地图上进行拖拽平移
                self.is_dragging_map = True
                self.drag_start_pos = event.pos()
                self.drag_start_offset_x = self.map_offset_x
                self.drag_start_offset_y = self.map_offset_y
                event.accept()
                return
        
        # 窗口拖拽（仅在非图钉模式下）
        if event.button() == Qt.LeftButton and not self.is_locked and not self.pin_mode:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()