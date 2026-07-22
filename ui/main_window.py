from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QStackedWidget,
    QProgressBar, QFrame, QScrollArea, QLineEdit, QDialog, QFormLayout,
    QDialogButtonBox, QMessageBox, QInputDialog, QMenu, QGraphicsDropShadowEffect, QComboBox, QGroupBox, QCheckBox, QSpinBox, QDoubleSpinBox, QGraphicsView, QSizePolicy, QSlider, QSystemTrayIcon
)
from PySide6.QtCore import Qt, Signal, QPoint, QSize, QRect, QTimer, QEvent, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, Property, QObject
from PySide6.QtGui import QFont, QIcon, QPainter, QColor, QLinearGradient, QPen, QBrush, QPainterPath, QPolygon, QPixmap, QFontMetrics, QImage
import os
import sys
import time
import math
import cv2

# ── OpenCV Unicode 路径支持 ──
def _imwrite(path, img, params=None):
    cv2.imencode(os.path.splitext(path)[1] or '.png', img, params or [])[1].tofile(path)

from core.pokemon_data import POKEMON_LIST, get_all_pokemon, save_custom_pokemon, load_custom_pokemon, load_pokemon_database
from core.counter_manager import CounterManager, Counter
from core.game_capture import GameCapture
from core.evolution_manager import EvolutionManager
from core.settings_manager import SettingsManager
from core.pokemon_types import get_all_types, get_type_color
from core.logger import logger
from ui.floating_window import FloatingWindow
from ui.settings_dialog import SettingsDialog
from zc.desktop_pet import toggle_pet, is_pet_running
from ui.debug_window import DebugWindow
from ui.pokedex_view import PokedexWidget, SCROLL_BAR_STYLE
from ui.home_view import HomeView
from ui.damage_calculator import DamageCalculatorWidget
from ui.type_effectiveness import TypeEffectivenessWidget

def get_resource_path(relative_path):
    """获取资源文件的正确路径，支持打包后运行"""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(sys.executable)
        return os.path.join(base_path, relative_path)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, relative_path)


# 全局样式：禁用焦点虚线框
NO_FOCUS_STYLE = """
    QPushButton:focus,
    QListWidget:focus,
    QComboBox:focus,
    QLineEdit:focus,
    QSpinBox:focus,
    QDoubleSpinBox:focus,
    QCheckBox:focus {
        outline: none;
    }
"""


class FoldButton(QPushButton):
    """折叠按钮 - 三角形图标"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_folded = False
        self.setFixedSize(28, 28)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制三角形
        painter.setPen(QPen(QColor("#a78bfa"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(QColor("#a78bfa"))
        
        size = self.size()
        center_x = size.width() / 2
        center_y = size.height() / 2
        
        # 根据折叠状态旋转三角形
        if self.is_folded:
            # 向右的三角形 ▶
            points = [
                QPoint(int(center_x - 4), int(center_y - 8)),
                QPoint(int(center_x - 4), int(center_y + 8)),
                QPoint(int(center_x + 6), int(center_y))
            ]
        else:
            # 向下的三角形 ▼
            points = [
                QPoint(int(center_x - 8), int(center_y - 4)),
                QPoint(int(center_x + 8), int(center_y - 4)),
                QPoint(int(center_x), int(center_y + 6))
            ]
        
        painter.drawPolygon(points)


class AddButton(QPushButton):
    """新建按钮 - 圆形+十字镂空图标"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        size = self.size()
        center_x = size.width() / 2
        center_y = size.height() / 2
        
        # 绘制十字镂空（白色）
        painter.setPen(QPen(QColor("#ffffff"), 2.5, Qt.SolidLine, Qt.RoundCap))
        
        # 竖线
        painter.drawLine(
            QPoint(int(center_x), int(center_y - 7)),
            QPoint(int(center_x), int(center_y + 7))
        )
        
        # 横线
        painter.drawLine(
            QPoint(int(center_x - 7), int(center_y)),
            QPoint(int(center_x + 7), int(center_y))
        )


class TriangleComboBox(QComboBox):
    """带三角形箭头的下拉框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        # 在右侧绘制紫色三角形
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#a78bfa"))
        
        rect = self.rect()
        arrow_size = 5
        cx = rect.right() - 14  # 距离右边14px
        cy = rect.center().y()
        
        # 向下三角形 ▼
        points = [
            QPoint(cx - arrow_size, cy - arrow_size // 2),
            QPoint(cx + arrow_size, cy - arrow_size // 2),
            QPoint(cx, cy + arrow_size)
        ]
        painter.drawPolygon(points)


class CustomCheckBox(QPushButton):
    """自定义复选框 - 白色方框+绿色对勾"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.setCheckable(True)
        self.setChecked(False)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        if self.isChecked():
            # 选中状态：绿色背景
            painter.setBrush(QColor(34, 197, 94, 50))  # rgba(34, 197, 94, 0.2)
            painter.setPen(QPen(QColor(34, 197, 94), 2))
        else:
            # 未选中状态：白色边框
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
        
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 4, 4)
        
        # 绘制对勾
        if self.isChecked():
            painter.setPen(QPen(QColor(34, 197, 94), 2.5, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(6, 12, 10, 16)
            painter.drawLine(10, 16, 18, 8)


class ToggleSwitch(QPushButton):
    """iOS风格开关 - 带滑块和平移动画"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(44, 24)
        self.setCursor(Qt.PointingHandCursor)
        
        # 动画属性
        self._offset = 2
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(16)  # 60fps
        self._animation_timer.timeout.connect(self._update_animation)
        
        # 设置初始状态(不触发动画)
        self._is_checked = False
        
    def isChecked(self):
        return self._is_checked
        
    def setChecked(self, checked):
        self._is_checked = checked
        self._start_animation()
        
    def mousePressEvent(self, event):
        self.setChecked(not self._is_checked)
        super().mousePressEvent(event)
        
    def _start_animation(self):
        if not self._animation_timer.isActive():
            self._animation_timer.start()
            
    def _update_animation(self):
        target = self.width() - self.height() + 2 if self.isChecked() else 2
        diff = target - self._offset
        
        if abs(diff) < 0.5:
            self._offset = target
            self._animation_timer.stop()
        else:
            self._offset += diff * 0.2
            
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = rect.height() / 2
        
        # 背景颜色
        bg_color = QColor(34, 197, 94) if self.isChecked() else QColor(63, 63, 70)
        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, radius, radius)
        
        # 滑块
        slider_rect = QRect(int(self._offset), 2, self.height() - 4, self.height() - 4)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(slider_rect)


class ZoomableGraphicsView(QGraphicsView):
    """支持滚轮缩放的 QGraphicsView"""
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setMouseTracking(True)  # 启用鼠标跟踪
        
    def mouseMoveEvent(self, event):
        """处理鼠标移动事件，显示坐标"""
        # 获取场景坐标
        scene_pos = self.mapToScene(event.pos())
        map_x = scene_pos.x()
        map_y = scene_pos.y()
        
        # 获取父窗口并更新坐标显示
        main_window = self.window()
        if hasattr(main_window, '_update_coordinate_display'):
            main_window._update_coordinate_display(map_x, map_y)
        
        super().mouseMoveEvent(event)


class MapLabel(QLabel):
    """支持拖拽和缩放的地图标签 - 使用渲染而非重绘"""
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setMouseTracking(True)
        self.is_dragging = False
        self.drag_start_pos = None
        self.drag_start_offset_x = 0  # 拖动开始时的offset
        self.drag_start_offset_y = 0  # 拖动开始时的offset
        
        # 圆形框选相关
        self.is_selecting = False  # 是否在框选模式
        self.is_dragging_circle = False  # 是否在拖拽圆形
        self.circle_center = None  # 圆形中心坐标
        self.circle_radius = 100  # 圆形半径
        self.is_resizing_circle = False  # 是否在调整圆形大小
        self.hovering_resize_handle = False  # 是否悬停在调整手柄上

        # 路径绘制相关
        self.route_preview_point = None  # 当前绘制中的起点（地图坐标），None=未开始绘制
        self.route_preview_mouse = None  # 鼠标当前位置（屏幕坐标），用于绘制预览线
        self.route_snapped = False  # 鼠标是否吸附到资源点
        self.selected_route_point = None  # 选中的路径点（单选时的主点，用于改名）(seg_idx, pt_idx)
        # 多选支持：Shift+点击 可多选路径点或整条路径段
        self.selected_route_points = set()  # 多选的路径点集合 {(seg_idx, pt_idx), ...}
        self.selected_route_segments = set()  # 多选的整条路径段集合 {seg_idx, ...}
        # 长按拖动支持
        self.route_press_start_time = 0  # 鼠标按下时间戳（用于长按判定）
        self.route_press_pos = None  # 鼠标按下位置（用于判定是否拖动）
        self.route_dragging_point = None  # 正在拖动的路径点 (seg_idx, pt_idx)，None=未拖动
        self.route_drag_moved = False  # 拖动是否产生实际位移
        # 连接模式
        self.route_connect_mode = False  # 是否在连接模式
        self.route_connect_source = None  # 连接源点 (seg_idx, pt_idx)

        # 关键：设置这些属性确保鼠标事件正常工作
        self.setAttribute(Qt.WA_Hover, True)
        # 启用双缓冲，减少闪烁
        self.setAttribute(Qt.WA_PaintOnScreen, False)
        self.setAutoFillBackground(False)
        
    def mousePressEvent(self, event):
        from PySide6.QtCore import QPointF
        import time
        # 路线自由变换模式：优先处理
        if getattr(self.main_window, 'route_transform_active', False):
            return self._handle_route_transform_press(event)
        route_edit_mode = getattr(self.main_window, 'route_edit_mode', False)

        if event.button() == Qt.LeftButton:
            # 如果在框选模式
            if self.is_selecting:
                # 先检测是否点击调整手柄
                if self.circle_center:
                    circle_screen_x = self.main_window.map_offset_x + (self.circle_center.x() * self.main_window.map_scale)
                    circle_screen_y = self.main_window.map_offset_y + (self.circle_center.y() * self.main_window.map_scale)
                    circle_screen_radius = self.circle_radius * self.main_window.map_scale

                    handle_size = 12
                    handle_x = circle_screen_x + circle_screen_radius
                    handle_y = circle_screen_y

                    dx = event.pos().x() - handle_x
                    dy = event.pos().y() - handle_y
                    distance = (dx**2 + dy**2) ** 0.5

                    if distance <= handle_size:
                        self.is_resizing_circle = True
                        event.accept()
                        return

                    dx = event.pos().x() - circle_screen_x
                    dy = event.pos().y() - circle_screen_y
                    distance = (dx**2 + dy**2) ** 0.5

                    if distance <= circle_screen_radius:
                        self.is_dragging_circle = True
                        self.drag_start_pos = event.pos()
                        self.drag_start_circle_x = self.circle_center.x()
                        self.drag_start_circle_y = self.circle_center.y()
                        event.accept()
                        return

                map_x = (event.pos().x() - self.main_window.map_offset_x) / self.main_window.map_scale
                map_y = (event.pos().y() - self.main_window.map_offset_y) / self.main_window.map_scale
                self.circle_center = QPointF(map_x, map_y)
                event.accept()
                return

            # 连接模式：左键点击另一个路径点完成连接
            if self.route_connect_mode:
                target_pt = self._detect_clicked_route_point(event.pos())
                if target_pt and target_pt != self.route_connect_source:
                    self._bridge_two_points(self.route_connect_source, target_pt)
                # 退出连接模式
                self.route_connect_mode = False
                self.route_connect_source = None
                self.setCursor(Qt.ArrowCursor)
                self.update()
                event.accept()
                return

            # 路线绘制模式
            if route_edit_mode:
                pos = event.pos()
                # 检查是否吸附到资源点
                snapped = self._check_resource_snap(pos)
                if snapped:
                    original_x, original_y = snapped
                else:
                    original_x = (pos.x() - self.main_window.map_offset_x) / self.main_window.map_scale
                    original_y = (pos.y() - self.main_window.map_offset_y) / self.main_window.map_scale

                route_segments = self.main_window.route_segments
                route_history = self.main_window.route_history
                is_cp = getattr(self.main_window, 'is_placing_checkpoint', False)

                # 保存历史用于撤回
                route_history.append([seg.copy() for seg in route_segments])

                if self.route_preview_point is None:
                    # 第一次点击 = 原点，开始新段
                    if not route_segments or len(route_segments[-1]) > 0:
                        route_segments.append([])
                    route_segments[-1].append((original_x, original_y, is_cp))
                    self.route_preview_point = (original_x, original_y)
                else:
                    # 后续点击 = 确认线段，添加新路径点
                    route_segments[-1].append((original_x, original_y, is_cp))
                    self.route_preview_point = (original_x, original_y)

                self.main_window._update_map_display()
                event.accept()
                return

            # 检测是否点击到已有路径点（用于选中或拖动）
            clicked_pt = self._detect_clicked_route_point(event.pos())

            # 检测是否点击到路径线
            clicked_line_seg = None
            if not clicked_pt:
                clicked_line_seg = self._detect_clicked_route_line(event.pos())

            # Shift 多选
            shift_pressed = bool(event.modifiers() & Qt.ShiftModifier)

            if clicked_pt:
                if shift_pressed:
                    # Shift+点击路径点：添加到/移出多选集合
                    if clicked_pt in self.selected_route_points:
                        self.selected_route_points.discard(clicked_pt)
                    else:
                        self.selected_route_points.add(clicked_pt)
                    # 主选中点设为最新点击的
                    self.selected_route_point = clicked_pt
                else:
                    # 普通点击：设为唯一选中
                    self.selected_route_points.clear()
                    self.selected_route_segments.clear()
                    self.selected_route_point = clicked_pt

                # 记录按下时间和位置，用于长按拖动判定
                self.route_press_start_time = time.time()
                self.route_press_pos = event.pos()
                self.route_dragging_point = None
                self.route_drag_moved = False
                self.update()
                event.accept()
                return

            elif clicked_line_seg is not None:
                # 点击路径线（clicked_line_seg 为 (seg_idx, start_pt, end_pt) 子段标识）
                if shift_pressed:
                    # Shift+点击路径线：添加到/移出多选集合
                    if clicked_line_seg in self.selected_route_segments:
                        self.selected_route_segments.discard(clicked_line_seg)
                    else:
                        self.selected_route_segments.add(clicked_line_seg)
                else:
                    # 普通点击：选中该子段
                    self.selected_route_points.clear()
                    self.selected_route_segments.clear()
                    self.selected_route_segments.add(clicked_line_seg)
                    # 主选中点设为该子段起点
                    seg_idx, start_pt, _ = clicked_line_seg
                    self.selected_route_point = (seg_idx, start_pt)
                self.update()
                event.accept()
                return

            else:
                # 点击空白：清空选中
                if self.selected_route_point or self.selected_route_points or self.selected_route_segments:
                    self.selected_route_point = None
                    self.selected_route_points.clear()
                    self.selected_route_segments.clear()
                    self.update()

            # 正常点击：拖动地图或检测资源
            self.press_pos = event.pos()
            clicked_resource = self._detect_clicked_resource(event.pos())

            if clicked_resource:
                self.pending_resource_to_show = clicked_resource
            else:
                self.is_dragging = True
                self.pending_resource_to_show = None

            self.drag_start_pos = event.pos()
            self.drag_start_offset_x = self.main_window.map_offset_x
            self.drag_start_offset_y = self.main_window.map_offset_y
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()

        elif event.button() == Qt.RightButton:
            if route_edit_mode:
                # 右键取消当前绘制（预览线消失，已绘制的保留）
                self.route_preview_point = None
                self.route_preview_mouse = None
                self.route_snapped = False
                self.update()
                event.accept()
                return
            elif self.route_connect_mode:
                # 右键取消连接模式
                self.route_connect_mode = False
                self.route_connect_source = None
                self.setCursor(Qt.ArrowCursor)
                self.update()
                event.accept()
                return
            else:
                # 区分点击路径点/路径线/空白
                clicked_pt = self._detect_clicked_route_point(event.pos())
                if clicked_pt:
                    # 右键路径点 = 显示菜单（删除/改名/连接/桥接）
                    self.selected_route_point = clicked_pt
                    self.update()
                    self._show_route_point_menu(event.globalPosition().toPoint())
                    event.accept()
                    return

                clicked_line_seg = self._detect_clicked_route_line(event.pos())
                if clicked_line_seg is not None:
                    # 右键路径线 = 显示菜单（删除此段/添加路径点）
                    self._show_route_line_menu(event.globalPosition().toPoint(), clicked_line_seg, event.pos())
                    event.accept()
                    return

                # 右键空白 = 显示菜单（添加路径点）
                self._show_route_blank_menu(event.globalPosition().toPoint(), event.pos())
                event.accept()
                return
            super().mousePressEvent(event)

        else:
            super().mousePressEvent(event)

    def _bridge_two_points(self, source_pt, target_pt):
        """连接/桥接两个路径点：在两点之间创建新段"""
        s1, p1 = source_pt
        s2, p2 = target_pt
        route_segments = self.main_window.route_segments

        if s1 >= len(route_segments) or s2 >= len(route_segments):
            return
        if p1 >= len(route_segments[s1]) or p2 >= len(route_segments[s2]):
            return

        x1, y1, cp1 = route_segments[s1][p1]
        x2, y2, cp2 = route_segments[s2][p2]

        # 保存历史
        self.main_window.route_history.append([seg.copy() for seg in route_segments])
        # 创建新段，包含这两个点
        route_segments.append([(x1, y1, cp1), (x2, y2, cp2)])
        # 清空选中状态
        self.selected_route_points.clear()
        self.selected_route_segments.clear()
        self.selected_route_point = None
        self.main_window._update_map_display()

    def _check_resource_snap(self, screen_pos):
        """检查鼠标是否在资源点附近，返回资源点的地图坐标 (map_x, map_y) 或 None"""
        if not hasattr(self.main_window, 'collect_data') or not self.main_window.collect_data:
            return None

        click_x = screen_pos.x()
        click_y = screen_pos.y()

        # 吸附范围
        snap_radius = max(20, int(20 * self.main_window.map_scale))

        selected_resources = getattr(self.main_window, 'selected_resources', set())
        if not selected_resources:
            return None

        for resource_name in selected_resources:
            resource_info = self.main_window.collect_data.get(resource_name, {})
            points = resource_info.get('points', [])

            for point in points:
                lat = point.get('lat', 0)
                lng = point.get('lng', 0)

                x, y = self.main_window._game_to_map_coords(lat, lng)
                screen_x = self.main_window.map_offset_x + (x * self.main_window.map_scale)
                screen_y = self.main_window.map_offset_y + (y * self.main_window.map_scale)

                distance = ((click_x - screen_x) ** 2 + (click_y - screen_y) ** 2) ** 0.5

                if distance <= snap_radius:
                    # 返回资源点的地图坐标（用于吸附）
                    return (x, y)

        return None

    def _detect_clicked_route_point(self, screen_pos):
        """检测点击是否在某个路径点上，返回 (seg_idx, pt_idx) 或 None"""
        route_segments = getattr(self.main_window, 'route_segments', [])
        if not route_segments:
            return None

        click_x = screen_pos.x()
        click_y = screen_pos.y()

        # 路径点检测范围
        detect_radius = max(12, int(12 * self.main_window.map_scale))

        for seg_idx, segment in enumerate(route_segments):
            for pt_idx, (map_x, map_y, is_cp) in enumerate(segment):
                screen_x = self.main_window.map_offset_x + (map_x * self.main_window.map_scale)
                screen_y = self.main_window.map_offset_y + (map_y * self.main_window.map_scale)

                distance = ((click_x - screen_x) ** 2 + (click_y - screen_y) ** 2) ** 0.5

                if distance <= detect_radius:
                    return (seg_idx, pt_idx)

        return None

    def _detect_clicked_route_line(self, screen_pos):
        """检测点击是否在某条路径线段上，按检测点为分割标准返回子段
        返回 (seg_idx, start_pt_idx, end_pt_idx) 或 None
        start_pt_idx 和 end_pt_idx 是子段在 segment 中的起止点索引（含）
        """
        route_segments = getattr(self.main_window, 'route_segments', [])
        if not route_segments:
            return None

        click_x = screen_pos.x()
        click_y = screen_pos.y()

        # 线段检测阈值（点到线段的距离）
        threshold = max(6, int(6 * self.main_window.map_scale))

        for seg_idx, segment in enumerate(route_segments):
            if len(segment) < 2:
                continue
            for i in range(len(segment) - 1):
                x1, y1, _ = segment[i]
                x2, y2, _ = segment[i + 1]
                sx1 = self.main_window.map_offset_x + (x1 * self.main_window.map_scale)
                sy1 = self.main_window.map_offset_y + (y1 * self.main_window.map_scale)
                sx2 = self.main_window.map_offset_x + (x2 * self.main_window.map_scale)
                sy2 = self.main_window.map_offset_y + (y2 * self.main_window.map_scale)
                dist = self._point_to_segment_distance(click_x, click_y, sx1, sy1, sx2, sy2)
                if dist <= threshold:
                    # 以检测点为分割标准：向前找到第一个检测点（含起点 0）
                    start = i
                    while start > 0 and not segment[start][2]:
                        start -= 1
                    # 向后找到下一个检测点（含终点 len-1）
                    end = i + 1
                    while end < len(segment) - 1 and not segment[end][2]:
                        end += 1
                    return (seg_idx, start, end)
        return None

    @staticmethod
    def _point_to_segment_distance(px, py, x1, y1, x2, y2):
        """计算点到线段的距离"""
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5

    def _show_route_point_menu(self, global_pos):
        """显示路径点右键菜单（删除/改名/连接/桥接）"""
        from PySide6.QtWidgets import QMenu, QInputDialog
        from PySide6.QtGui import QAction

        if self.selected_route_point is None:
            return

        seg_idx, pt_idx = self.selected_route_point
        route_segments = self.main_window.route_segments

        if seg_idx >= len(route_segments) or pt_idx >= len(route_segments[seg_idx]):
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(30, 30, 38, 0.98);
                color: #e4e4e7;
                border: 1px solid rgba(124, 58, 237, 0.4);
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(124, 58, 237, 0.3);
            }
        """)

        # 删除
        action_delete = menu.addAction("删除")
        # 改名
        action_rename = menu.addAction("改名")
        # 连接：进入连接模式，点击另一个点后在两点之间创建新段
        action_connect = menu.addAction("连接")

        # 桥接：仅当多选了 2 个路径点时显示
        action_bridge = None
        if len(self.selected_route_points) == 2:
            action_bridge = menu.addAction("桥接")

        action = menu.exec(global_pos)

        if action == action_delete:
            # 保存历史
            self.main_window.route_history.append([seg.copy() for seg in route_segments])
            # 删除路径点
            del route_segments[seg_idx][pt_idx]
            # 如果段空了，删除段
            if len(route_segments[seg_idx]) == 0:
                del route_segments[seg_idx]
            # 更新名称字典
            names = self.main_window.route_point_names
            # 删除该点名称，并重新编号后续点
            new_names = {}
            for (s, p), name in names.items():
                if s == seg_idx:
                    if p < pt_idx:
                        new_names[(s, p)] = name
                    elif p > pt_idx:
                        new_names[(s, p - 1)] = name
                elif s > seg_idx and len(route_segments) < len(names):
                    new_names[(s - 1, p)] = name
                else:
                    new_names[(s, p)] = name
            self.main_window.route_point_names = new_names
            self.selected_route_point = None
            self.selected_route_points.clear()
            self.selected_route_segments.clear()
            self.main_window._update_map_display()

        elif action == action_rename:
            names = self.main_window.route_point_names
            current_name = names.get((seg_idx, pt_idx), str(pt_idx + 1))
            new_name, ok = QInputDialog.getText(
                self, "改名", "路径点名称:", text=current_name
            )
            if ok and new_name:
                names[(seg_idx, pt_idx)] = new_name
                self.update()

        elif action == action_connect:
            # 进入连接模式：下次左键点击另一个路径点时创建新段
            self.route_connect_mode = True
            self.route_connect_source = (seg_idx, pt_idx)
            # 退出绘制模式以避免冲突
            if getattr(self.main_window, 'route_edit_mode', False):
                self.main_window.draw_route_btn.setChecked(False)
                self.main_window._toggle_route_edit_mode()
            self.setCursor(Qt.CrossCursor)
            self.update()

        elif action_bridge is not None and action == action_bridge:
            self._bridge_selected_points()

    def _bridge_selected_points(self):
        """桥接：在两个多选的路径点之间创建新段"""
        if len(self.selected_route_points) != 2:
            return
        pts = list(self.selected_route_points)
        (s1, p1), (s2, p2) = pts
        route_segments = self.main_window.route_segments

        if s1 >= len(route_segments) or s2 >= len(route_segments):
            return
        if p1 >= len(route_segments[s1]) or p2 >= len(route_segments[s2]):
            return

        # 取两个点的坐标
        x1, y1, cp1 = route_segments[s1][p1]
        x2, y2, cp2 = route_segments[s2][p2]

        # 保存历史
        self.main_window.route_history.append([seg.copy() for seg in route_segments])
        # 创建新段，包含这两个点
        route_segments.append([(x1, y1, cp1), (x2, y2, cp2)])
        # 清空选中状态
        self.selected_route_points.clear()
        self.selected_route_segments.clear()
        self.selected_route_point = None
        self.main_window._update_map_display()

    def _show_route_line_menu(self, global_pos, sub_segment, click_pos):
        """显示路径线右键菜单（删除此子段/添加检测点）
        sub_segment = (seg_idx, start_pt_idx, end_pt_idx) 子段标识
        """
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction

        seg_idx, start_pt, end_pt = sub_segment
        route_segments = self.main_window.route_segments
        if seg_idx >= len(route_segments):
            return
        segment = route_segments[seg_idx]
        if start_pt >= len(segment) or end_pt >= len(segment):
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(30, 30, 38, 0.98);
                color: #e4e4e7;
                border: 1px solid rgba(124, 58, 237, 0.4);
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(124, 58, 237, 0.3);
            }
        """)

        action_delete_seg = menu.addAction("删除此路径线")
        action_add_point = menu.addAction("在此处添加检测点")

        action = menu.exec(global_pos)

        if action == action_delete_seg:
            # 保存历史
            self.main_window.route_history.append([seg.copy() for seg in route_segments])
            # 仅删除被点击的那条线（i 和 i+1 之间），保留所有点
            # 在子段 [start_pt, end_pt] 范围内找到点击位置最近的线段 i
            click_x = click_pos.x()
            click_y = click_pos.y()
            best_i = start_pt
            best_dist = float('inf')
            for i in range(start_pt, end_pt):
                x1, y1, _ = segment[i]
                x2, y2, _ = segment[i + 1]
                sx1 = self.main_window.map_offset_x + (x1 * self.main_window.map_scale)
                sy1 = self.main_window.map_offset_y + (y1 * self.main_window.map_scale)
                sx2 = self.main_window.map_offset_x + (x2 * self.main_window.map_scale)
                sy2 = self.main_window.map_offset_y + (y2 * self.main_window.map_scale)
                dist = self._point_to_segment_distance(click_x, click_y, sx1, sy1, sx2, sy2)
                if dist < best_dist:
                    best_dist = dist
                    best_i = i

            # 在 best_i 和 best_i+1 之间断开 segment（保留所有点，只是不连线）
            front_part = segment[:best_i + 1]   # [0..best_i]，含点 best_i
            back_part = segment[best_i + 1:]    # [best_i+1..]，含点 best_i+1

            # 构建替换段列表（保留非空段）
            new_segs = []
            if front_part:
                new_segs.append(front_part)
            if back_part:
                new_segs.append(back_part)

            if new_segs:
                # 用 new_segs[0] 替换原 segment，剩余的作为新 segment 插入
                route_segments[seg_idx] = new_segs[0]
                for i, ns in enumerate(new_segs[1:], 1):
                    route_segments.insert(seg_idx + i, ns)
                inserted_count = len(new_segs) - 1  # 插入的新 segment 数
                seg_idx_delta = inserted_count  # 后续 segment 索引偏移
            else:
                # 两段都空，删除当前 segment
                del route_segments[seg_idx]
                seg_idx_delta = -1

            # 更新名称字典（保留所有点的名称）
            names = self.main_window.route_point_names
            new_names = {}
            has_front = bool(front_part)
            has_back = bool(back_part)
            for (s, p), name in names.items():
                if s == seg_idx:
                    if p <= best_i and has_front:
                        # 前段保留（seg_idx 不变，pt_idx 不变）
                        new_names[(s, p)] = name
                    elif p > best_i and has_back:
                        # 后段：seg_idx + (1 if has_front else 0)，pt_idx = p - (best_i + 1)
                        new_seg_idx = s + (1 if has_front else 0)
                        new_names[(new_seg_idx, p - (best_i + 1))] = name
                elif s > seg_idx:
                    # 后续 segment 索引偏移
                    new_names[(s + seg_idx_delta, p)] = name
                else:
                    new_names[(s, p)] = name
            self.main_window.route_point_names = new_names
            # 清空选中状态
            self.selected_route_point = None
            self.selected_route_points.clear()
            self.selected_route_segments.discard(sub_segment)
            self.main_window._update_map_display()

        elif action == action_add_point:
            # 计算点击位置的地图坐标
            map_x = (click_pos.x() - self.main_window.map_offset_x) / self.main_window.map_scale
            map_y = (click_pos.y() - self.main_window.map_offset_y) / self.main_window.map_scale
            # 检查吸附
            snapped = self._check_resource_snap(click_pos)
            if snapped:
                map_x, map_y = snapped
            # 保存历史
            self.main_window.route_history.append([seg.copy() for seg in route_segments])
            # 在路线上添加检测点：找到点击位置在哪两个相邻点之间，insert 到该位置
            # Bug 2: 使用检测点（is_cp=True）而非普通点
            # Bug 3: 使用 insert 到正确位置而非 append 到末尾
            insert_idx = self._find_insert_index_in_segment(segment, click_pos, start_pt, end_pt)
            segment.insert(insert_idx, (map_x, map_y, True))
            # 更新名称字典：seg_idx 内 pt_idx >= insert_idx 的点 pt_idx+1
            names = self.main_window.route_point_names
            new_names = {}
            for (s, p), name in names.items():
                if s == seg_idx and p >= insert_idx:
                    new_names[(s, p + 1)] = name
                else:
                    new_names[(s, p)] = name
            self.main_window.route_point_names = new_names
            self.main_window._update_map_display()

    def _find_insert_index_in_segment(self, segment, click_pos, start_pt, end_pt):
        """找到点击位置在 segment 的子段 [start_pt, end_pt] 中的最佳插入位置
        返回 insert_idx（0-based）：插入后新点位于该索引
        """
        click_x = click_pos.x()
        click_y = click_pos.y()

        # 遍历子段中所有相邻点对，找到点击位置距哪一对最近
        best_idx = start_pt + 1  # 默认插在子段第二个点之前
        best_dist = float('inf')

        for i in range(start_pt, end_pt):
            x1, y1, _ = segment[i]
            x2, y2, _ = segment[i + 1]
            sx1 = self.main_window.map_offset_x + (x1 * self.main_window.map_scale)
            sy1 = self.main_window.map_offset_y + (y1 * self.main_window.map_scale)
            sx2 = self.main_window.map_offset_x + (x2 * self.main_window.map_scale)
            sy2 = self.main_window.map_offset_y + (y2 * self.main_window.map_scale)
            dist = self._point_to_segment_distance(click_x, click_y, sx1, sy1, sx2, sy2)
            if dist < best_dist:
                best_dist = dist
                best_idx = i + 1  # 插入到点 i 和 i+1 之间，即新点索引为 i+1

        return best_idx

    def _show_route_blank_menu(self, global_pos, click_pos):
        """显示空白处右键菜单（添加路径点）"""
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(30, 30, 38, 0.98);
                color: #e4e4e7;
                border: 1px solid rgba(124, 58, 237, 0.4);
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(124, 58, 237, 0.3);
            }
        """)

        action_add_point = menu.addAction("在此处添加路径点")

        action = menu.exec(global_pos)

        if action == action_add_point:
            # 在空白处创建新段，并添加路径点
            map_x = (click_pos.x() - self.main_window.map_offset_x) / self.main_window.map_scale
            map_y = (click_pos.y() - self.main_window.map_offset_y) / self.main_window.map_scale
            # 检查吸附
            snapped = self._check_resource_snap(click_pos)
            if snapped:
                map_x, map_y = snapped
            # 保存历史
            route_segments = self.main_window.route_segments
            self.main_window.route_history.append([seg.copy() for seg in route_segments])
            is_cp = getattr(self.main_window, 'is_placing_checkpoint', False)
            # 新段包含这个点
            route_segments.append([(map_x, map_y, is_cp)])
            self.main_window._update_map_display()

    def _detect_clicked_resource(self, pos):
        """检测点击位置是否在某个资源标记上（包括资源一栏和其余一栏）"""
        click_x = pos.x()
        click_y = pos.y()

        detection_radius = max(12 * self.main_window.map_scale, 10)

        # 优先检测"资源"一栏（材料）
        selected_resources = getattr(self.main_window, 'selected_resources', set())
        collect_data = getattr(self.main_window, 'collect_data', {})
        for resource_name in selected_resources:
            resource_info = collect_data.get(resource_name, {})
            points = resource_info.get('points', [])

            for point in points:
                lat = point.get('lat', 0)
                lng = point.get('lng', 0)

                x, y = self.main_window._game_to_map_coords(lat, lng)
                screen_x = self.main_window.map_offset_x + (x * self.main_window.map_scale)
                screen_y = self.main_window.map_offset_y + (y * self.main_window.map_scale)

                distance = ((click_x - screen_x) ** 2 + (click_y - screen_y) ** 2) ** 0.5

                if distance <= detection_radius:
                    return resource_name

        # 再检测"其余"一栏（宝箱 + 眠枭之星）
        selected_owl_stars = getattr(self.main_window, 'selected_owl_stars', set())
        owl_stars_data = getattr(self.main_window, 'owl_stars_data', {})
        for item_name in selected_owl_stars:
            item_info = owl_stars_data.get(item_name, {})
            points = item_info.get('points', [])

            for point in points:
                lat = point.get('lat', 0)
                lng = point.get('lng', 0)

                x, y = self.main_window._game_to_map_coords(lat, lng)
                screen_x = self.main_window.map_offset_x + (x * self.main_window.map_scale)
                screen_y = self.main_window.map_offset_y + (y * self.main_window.map_scale)

                distance = ((click_x - screen_x) ** 2 + (click_y - screen_y) ** 2) ** 0.5

                if distance <= detection_radius:
                    return item_name

        return None

    def _show_resource_tooltip(self, resource_name, global_pos):
        """显示资源名称提示"""
        from PySide6.QtWidgets import QToolTip
        from PySide6.QtGui import QPalette, QColor

        tooltip_text = f"<div style='background-color: rgba(0, 0, 0, 0.85); color: white; padding: 8px 12px; border-radius: 4px; font-size: 13px;'>{resource_name}</div>"

        QToolTip.showText(global_pos, tooltip_text, self)

        if hasattr(self.main_window, 'coord_label'):
            self.main_window.coord_label.setText(f"选中: {resource_name}")

    def mouseMoveEvent(self, event):
        from PySide6.QtCore import QPointF
        import time
        current_time = time.time()

        # 路线自由变换模式：拖拽中则优先处理
        if getattr(self.main_window, 'route_transform_active', False) and self.main_window.route_transform_action is not None:
            return self._handle_route_transform_move(event)

        # 路线绘制模式：更新预览线和吸附
        route_edit_mode = getattr(self.main_window, 'route_edit_mode', False)
        if route_edit_mode and self.route_preview_point is not None:
            pos = event.pos()
            # 检查吸附
            snapped = self._check_resource_snap(pos)
            if snapped:
                self.route_snapped = True
                map_x, map_y = snapped
                # 存储屏幕坐标用于绘制预览线
                self.route_preview_mouse = (
                    self.main_window.map_offset_x + map_x * self.main_window.map_scale,
                    self.main_window.map_offset_y + map_y * self.main_window.map_scale
                )
            else:
                self.route_snapped = False
                self.route_preview_mouse = (pos.x(), pos.y())

            # 更新坐标显示
            if hasattr(self.main_window, 'coord_label'):
                map_x = (pos.x() - self.main_window.map_offset_x) / self.main_window.map_scale
                map_y = (pos.y() - self.main_window.map_offset_y) / self.main_window.map_scale
                self.main_window._update_coordinate_display(map_x, map_y)

            self.update()
            event.accept()
            return

        # 长按拖动路径点
        if (self.route_press_start_time > 0 and self.route_press_pos is not None
                and self.selected_route_point is not None
                and self.route_connect_mode is False):
            # 判断是否进入拖动模式：超过 400ms 且未移动太远（避免误触）
            elapsed = current_time - self.route_press_start_time
            dx = event.pos().x() - self.route_press_pos.x()
            dy = event.pos().y() - self.route_press_pos.y()
            move_dist = (dx * dx + dy * dy) ** 0.5

            if self.route_dragging_point is None:
                # 未进入拖动：超过 400ms 后开始拖动
                if elapsed >= 0.4 and move_dist <= 8:
                    seg_idx, pt_idx = self.selected_route_point
                    route_segments = self.main_window.route_segments
                    if seg_idx < len(route_segments) and pt_idx < len(route_segments[seg_idx]):
                        # 保存历史用于撤回
                        self.main_window.route_history.append([seg.copy() for seg in route_segments])
                        self.route_dragging_point = self.selected_route_point
                        self.route_drag_moved = False
                        self.setCursor(Qt.SizeAllCursor)
            else:
                # 已在拖动：更新路径点位置
                seg_idx, pt_idx = self.route_dragging_point
                route_segments = self.main_window.route_segments
                if seg_idx < len(route_segments) and pt_idx < len(route_segments[seg_idx]):
                    # 检查吸附
                    snapped = self._check_resource_snap(event.pos())
                    if snapped:
                        new_map_x, new_map_y = snapped
                    else:
                        new_map_x = (event.pos().x() - self.main_window.map_offset_x) / self.main_window.map_scale
                        new_map_y = (event.pos().y() - self.main_window.map_offset_y) / self.main_window.map_scale
                    # 保留原 is_checkpoint
                    _, _, is_cp = route_segments[seg_idx][pt_idx]
                    route_segments[seg_idx][pt_idx] = (new_map_x, new_map_y, is_cp)
                    self.route_drag_moved = True
                    self.main_window._update_map_display()
                event.accept()
                return

        if self.is_selecting:
            if self.circle_center:
                circle_screen_x = self.main_window.map_offset_x + (self.circle_center.x() * self.main_window.map_scale)
                circle_screen_y = self.main_window.map_offset_y + (self.circle_center.y() * self.main_window.map_scale)
                circle_screen_radius = self.circle_radius * self.main_window.map_scale

                handle_size = 12
                handle_x = circle_screen_x + circle_screen_radius
                handle_y = circle_screen_y

                dx = event.pos().x() - handle_x
                dy = event.pos().y() - handle_y
                distance = (dx**2 + dy**2) ** 0.5

                if distance <= handle_size:
                    self.hovering_resize_handle = True
                    self.setCursor(Qt.SizeHorCursor)
                else:
                    self.hovering_resize_handle = False

                if not self.is_dragging_circle and not self.is_resizing_circle and not self.hovering_resize_handle:
                    self.setCursor(Qt.ArrowCursor)

            if self.is_resizing_circle and self.circle_center:
                circle_screen_x = self.main_window.map_offset_x + (self.circle_center.x() * self.main_window.map_scale)
                circle_screen_y = self.main_window.map_offset_y + (self.circle_center.y() * self.main_window.map_scale)

                dx = event.pos().x() - circle_screen_x
                dy = event.pos().y() - circle_screen_y
                screen_distance = (dx**2 + dy**2) ** 0.5

                self.circle_radius = screen_distance / self.main_window.map_scale
                self.update()
                event.accept()
                return

            if self.is_dragging_circle:
                delta = event.pos() - self.drag_start_pos

                map_delta_x = delta.x() / self.main_window.map_scale
                map_delta_y = delta.y() / self.main_window.map_scale

                self.circle_center = QPointF(self.drag_start_circle_x + map_delta_x,
                                              self.drag_start_circle_y + map_delta_y)
                self.update()
                event.accept()
                return

        if hasattr(self.main_window, 'coord_label') and not self.is_dragging and not self.is_selecting:
            if current_time - self.main_window._last_coord_update_time > 0.1:
                pos = event.pos()
                map_x = (pos.x() - self.main_window.map_offset_x) / self.main_window.map_scale
                map_y = (pos.y() - self.main_window.map_offset_y) / self.main_window.map_scale
                self.main_window._update_coordinate_display(map_x, map_y)
                self.main_window._last_coord_update_time = current_time

        if not self.is_selecting and self.drag_start_pos:
            delta = event.pos() - self.drag_start_pos
            if abs(delta.x()) > 5 or abs(delta.y()) > 5:
                self.pending_resource_to_show = None

                self.main_window.map_offset_x = self.drag_start_offset_x + delta.x()
                self.main_window.map_offset_y = self.drag_start_offset_y + delta.y()

                if not self.is_dragging:
                    self.is_dragging = True

                self.main_window._update_map_display()
            elif self.is_dragging:
                delta = event.pos() - self.drag_start_pos
                self.main_window.map_offset_x = self.drag_start_offset_x + delta.x()
                self.main_window.map_offset_y = self.drag_start_offset_y + delta.y()
                self.main_window._update_map_display()

        event.accept()

    def mouseReleaseEvent(self, event):
        # 路线自由变换模式：释放结束本次拖拽
        if getattr(self.main_window, 'route_transform_active', False) and self.main_window.route_transform_action is not None:
            self.main_window.route_transform_action = None
            self.main_window.route_transform_press_pos = None
            self.main_window.route_transform_start_segments = None
            self.setCursor(Qt.ArrowCursor)
            self.update()
            event.accept()
            return
        if event.button() == Qt.LeftButton:
            if self.is_selecting:
                self.is_resizing_circle = False
                self.is_dragging_circle = False
                self.update()
                event.accept()
                return

            # 结束长按拖动
            if self.route_dragging_point is not None:
                # 如果没有实际移动（短按），保持选中状态（不撤销）
                if not self.route_drag_moved:
                    # 撤回刚才保存的历史（因为没移动）
                    if self.main_window.route_history:
                        self.main_window.route_history.pop()
                self.route_dragging_point = None
                self.route_drag_moved = False
                self.route_press_start_time = 0
                self.route_press_pos = None
                self.setCursor(Qt.ArrowCursor)
                event.accept()
                return

            # 清除长按记录
            self.route_press_start_time = 0
            self.route_press_pos = None

            if self.pending_resource_to_show and not self.is_dragging:
                self._show_resource_tooltip(self.pending_resource_to_show, event.globalPosition().toPoint())

            self.is_dragging = False
            self.drag_start_pos = None
            self.press_pos = None
            self.pending_resource_to_show = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _handle_route_transform_press(self, event):
        """自由变换模式：鼠标按下"""
        if event.button() != Qt.LeftButton:
            event.accept()
            return
        pos = event.pos()
        mw = self.main_window
        bbox = mw.route_transform_bbox
        if not bbox:
            event.accept()
            return
        min_x, min_y, max_x, max_y = bbox
        scale = mw.map_scale
        ox = mw.map_offset_x
        oy = mw.map_offset_y
        sx1 = ox + min_x * scale
        sy1 = oy + min_y * scale
        sx2 = ox + max_x * scale
        sy2 = oy + max_y * scale
        handle_size = 10
        hit_tol = 8  # 手柄命中容差
        mid_x = (sx1 + sx2) / 2
        mid_y = (sy1 + sy2) / 2

        # 1. 检测是否点击 4 角手柄 → 等比例缩放
        corners = [(sx1, sy1), (sx2, sy1), (sx2, sy2), (sx1, sy2)]
        for cx, cy in corners:
            if abs(pos.x() - cx) <= handle_size/2 + hit_tol and abs(pos.y() - cy) <= handle_size/2 + hit_tol:
                mw.route_transform_action = 'scale'
                mw.route_transform_press_pos = pos
                mw.route_transform_start_segments = [seg.copy() for seg in mw.route_segments]
                # 记录锚点 = 对角点（地图世界坐标）
                anchor_screen_x = sx1 + sx2 - cx
                anchor_screen_y = sy1 + sy2 - cy
                mw._route_transform_anchor = (
                    (anchor_screen_x - ox) / scale,
                    (anchor_screen_y - oy) / scale
                )
                self.setCursor(Qt.SizeFDiagCursor)
                event.accept()
                return

        # 2. 检测是否点击上下边中点手柄 → 垂直缩放（scale_y）
        for cx, cy in [(mid_x, sy1), (mid_x, sy2)]:
            if abs(pos.x() - cx) <= handle_size/2 + hit_tol and abs(pos.y() - cy) <= handle_size/2 + hit_tol:
                mw.route_transform_action = 'scale_y'
                mw.route_transform_press_pos = pos
                mw.route_transform_start_segments = [seg.copy() for seg in mw.route_segments]
                # 锚点 = 对边中点（地图世界坐标）
                anchor_screen_y = sy1 + sy2 - cy
                mw._route_transform_anchor = (
                    (cx - ox) / scale,
                    (anchor_screen_y - oy) / scale
                )
                self.setCursor(Qt.SizeVerCursor)
                event.accept()
                return

        # 3. 检测是否点击左右边中点手柄 → 水平缩放（scale_x）
        for cx, cy in [(sx1, mid_y), (sx2, mid_y)]:
            if abs(pos.x() - cx) <= handle_size/2 + hit_tol and abs(pos.y() - cy) <= handle_size/2 + hit_tol:
                mw.route_transform_action = 'scale_x'
                mw.route_transform_press_pos = pos
                mw.route_transform_start_segments = [seg.copy() for seg in mw.route_segments]
                # 锚点 = 对边中点（地图世界坐标）
                anchor_screen_x = sx1 + sx2 - cx
                mw._route_transform_anchor = (
                    (anchor_screen_x - ox) / scale,
                    (cy - oy) / scale
                )
                self.setCursor(Qt.SizeHorCursor)
                event.accept()
                return

        # 2. 检测是否点击框内 → 移动
        if sx1 - hit_tol <= pos.x() <= sx2 + hit_tol and sy1 - hit_tol <= pos.y() <= sy2 + hit_tol:
            mw.route_transform_action = 'move'
            mw.route_transform_press_pos = pos
            mw.route_transform_start_segments = [seg.copy() for seg in mw.route_segments]
            self.setCursor(Qt.SizeAllCursor)
            event.accept()
            return

        # 3. 检测是否点击框外边缘（用于旋转）→ 鼠标在框外但距离框边不超过 30 像素
        margin = 30
        near_box = (
            sx1 - margin <= pos.x() <= sx2 + margin and
            sy1 - margin <= pos.y() <= sy2 + margin and
            not (sx1 <= pos.x() <= sx2 and sy1 <= pos.y() <= sy2)
        )
        if near_box:
            mw.route_transform_action = 'rotate'
            mw.route_transform_press_pos = pos
            mw.route_transform_start_segments = [seg.copy() for seg in mw.route_segments]
            # 计算初始角度（鼠标相对中心的角度）
            center_screen_x = (sx1 + sx2) / 2
            center_screen_y = (sy1 + sy2) / 2
            mw._route_transform_initial_angle = math.degrees(math.atan2(
                pos.y() - center_screen_y,
                pos.x() - center_screen_x
            ))
            self.setCursor(Qt.CrossCursor)
            event.accept()
            return

        # 4. 点击其他位置：不做处理（保持变换模式）
        event.accept()

    def _handle_route_transform_move(self, event):
        """自由变换模式：鼠标移动"""
        pos = event.pos()
        mw = self.main_window
        if mw.route_transform_action is None or mw.route_transform_press_pos is None:
            return
        if mw.route_transform_start_segments is None:
            return

        start_pos = mw.route_transform_press_pos
        start_segs = mw.route_transform_start_segments
        scale = mw.map_scale

        if mw.route_transform_action == 'move':
            # 平移：dx/dy 转换到地图世界坐标
            dx = (pos.x() - start_pos.x()) / scale
            dy = (pos.y() - start_pos.y()) / scale
            new_segs = [
                [((p[0] + dx), (p[1] + dy), p[2]) for p in seg]
                for seg in start_segs
            ]
            mw.route_segments = new_segs
            mw._update_route_transform_bbox()
            mw._update_map_display()

        elif mw.route_transform_action == 'scale':
            # 等比例缩放：以对角点为锚点
            anchor_x, anchor_y = getattr(mw, '_route_transform_anchor', (0, 0))
            ox = mw.map_offset_x
            oy = mw.map_offset_y
            anchor_screen_x = ox + anchor_x * scale
            anchor_screen_y = oy + anchor_y * scale
            start_dist = ((start_pos.x() - anchor_screen_x)**2 + (start_pos.y() - anchor_screen_y)**2) ** 0.5
            curr_dist = ((pos.x() - anchor_screen_x)**2 + (pos.y() - anchor_screen_y)**2) ** 0.5
            if start_dist > 5:
                factor = curr_dist / start_dist
                factor = max(0.05, min(factor, 20.0))  # 限制范围
            else:
                factor = 1.0
            new_segs = [
                [((anchor_x + (p[0] - anchor_x) * factor), (anchor_y + (p[1] - anchor_y) * factor), p[2]) for p in seg]
                for seg in start_segs
            ]
            mw.route_segments = new_segs
            mw._update_route_transform_bbox()
            mw._update_map_display()

        elif mw.route_transform_action == 'scale_x':
            # 水平缩放：以对边中点为锚点，只缩放 x
            anchor_x, anchor_y = getattr(mw, '_route_transform_anchor', (0, 0))
            ox = mw.map_offset_x
            anchor_screen_x = ox + anchor_x * scale
            start_dx = start_pos.x() - anchor_screen_x
            curr_dx = pos.x() - anchor_screen_x
            if abs(start_dx) > 5:
                factor = curr_dx / start_dx
                factor = max(0.05, min(factor, 20.0))
            else:
                factor = 1.0
            new_segs = [
                [((anchor_x + (p[0] - anchor_x) * factor), p[1], p[2]) for p in seg]
                for seg in start_segs
            ]
            mw.route_segments = new_segs
            mw._update_route_transform_bbox()
            mw._update_map_display()

        elif mw.route_transform_action == 'scale_y':
            # 垂直缩放：以对边中点为锚点，只缩放 y
            anchor_x, anchor_y = getattr(mw, '_route_transform_anchor', (0, 0))
            oy = mw.map_offset_y
            anchor_screen_y = oy + anchor_y * scale
            start_dy = start_pos.y() - anchor_screen_y
            curr_dy = pos.y() - anchor_screen_y
            if abs(start_dy) > 5:
                factor = curr_dy / start_dy
                factor = max(0.05, min(factor, 20.0))
            else:
                factor = 1.0
            new_segs = [
                [(p[0], (anchor_y + (p[1] - anchor_y) * factor), p[2]) for p in seg]
                for seg in start_segs
            ]
            mw.route_segments = new_segs
            mw._update_route_transform_bbox()
            mw._update_map_display()

        elif mw.route_transform_action == 'rotate':
            # 旋转：以包围盒中心为锚点
            all_pts = [(p[0], p[1]) for seg in start_segs for p in seg]
            if not all_pts:
                return
            cx = sum(p[0] for p in all_pts) / len(all_pts)
            cy = sum(p[1] for p in all_pts) / len(all_pts)
            # 屏幕坐标的中心
            ox = mw.map_offset_x
            oy = mw.map_offset_y
            center_screen_x = ox + cx * scale
            center_screen_y = oy + cy * scale
            curr_angle = math.degrees(math.atan2(
                pos.y() - center_screen_y,
                pos.x() - center_screen_x
            ))
            delta_angle = curr_angle - mw._route_transform_initial_angle
            rad = math.radians(delta_angle)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            new_segs = []
            for seg in start_segs:
                new_seg = []
                for (x, y, cp) in seg:
                    dx = x - cx
                    dy = y - cy
                    new_x = cx + dx * cos_a - dy * sin_a
                    new_y = cy + dx * sin_a + dy * cos_a
                    new_seg.append((new_x, new_y, cp))
                new_segs.append(new_seg)
            mw.route_segments = new_segs
            mw._update_route_transform_bbox()
            mw._update_map_display()

        event.accept()

    def keyPressEvent(self, event):
        """处理 Enter/ESC 退出变换模式"""
        if getattr(self.main_window, 'route_transform_active', False):
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                self.main_window._exit_route_transform_mode(apply_changes=True)
                event.accept()
                return
            elif event.key() == Qt.Key_Escape:
                self.main_window._exit_route_transform_mode(apply_changes=False)
                event.accept()
                return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        main_window = self.window()
        if hasattr(main_window, '_zoom_map'):
            if event.modifiers() & Qt.ControlModifier:
                mouse_pos = event.position()
                if event.angleDelta().y() > 0:
                    main_window._zoom_map(1.1, mouse_pos)
                else:
                    main_window._zoom_map(0.9, mouse_pos)
                event.accept()
                return

        super().wheelEvent(event)

    def paintEvent(self, event):
        """自定义绘制事件 - 地图始终填满 widget，用 source_rect 控制显示区域（无黑边）"""
        from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPixmap
        from PySide6.QtCore import QRectF
        import os

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # 不再用黑色填充背景——地图会绘制到整个 widget

        pixmap_to_draw = None
        if hasattr(self.main_window, 'map_pixmap') and not self.main_window.map_pixmap.isNull():
            pixmap_to_draw = self.main_window.map_pixmap

        sc_dir = os.path.join(os.path.dirname(__file__), '..', 'image', 'sc')
        jx_icon_path = os.path.join(sc_dir, 'jx.png')
        lx_icon_path = os.path.join(sc_dir, 'lx.png')
        xz_icon_path = os.path.join(sc_dir, 'xz.png')
        yp_icon_path = os.path.join(sc_dir, 'yp.png')
        zx_icon_path = os.path.join(sc_dir, 'zx.png')

        jx_pixmap = QPixmap(jx_icon_path) if os.path.exists(jx_icon_path) else None
        lx_pixmap = QPixmap(lx_icon_path) if os.path.exists(lx_icon_path) else None
        xz_pixmap = QPixmap(xz_icon_path) if os.path.exists(xz_icon_path) else None
        yp_pixmap = QPixmap(yp_icon_path) if os.path.exists(yp_icon_path) else None
        zx_pixmap = QPixmap(zx_icon_path) if os.path.exists(zx_icon_path) else None

        if pixmap_to_draw:
            # 地图绘制：到边缘拉不动，无黑边，不拉伸
            w = max(1, self.width())
            h = max(1, self.height())
            scale = self.main_window.map_scale if self.main_window.map_scale > 0 else 1.0
            map_w = max(1, self.main_window.map_width)
            map_h = max(1, self.main_window.map_height)

            # 在 paintEvent 中直接 clamp，保证用同一个 w/h 计算
            # 1. 强制地图 >= 视口（避免黑边）
            scaled_w = map_w * scale
            scaled_h = map_h * scale
            if scaled_w < w:
                scale = w / map_w
                self.main_window.map_scale = scale
                scaled_w = map_w * scale
            if scaled_h < h:
                scale = max(scale, h / map_h)
                self.main_window.map_scale = scale
                scaled_h = map_h * scale
            # 2. offset 限制在 [w-scaled_w, 0]（到边缘拉不动，不露出地图外）
            self.main_window.map_offset_x = max(w - scaled_w, min(0, self.main_window.map_offset_x))
            self.main_window.map_offset_y = max(h - scaled_h, min(0, self.main_window.map_offset_y))

            # 3. 计算 source（offset 被 clamp 后，source 保证不超出地图范围）
            src_x = max(0.0, -self.main_window.map_offset_x / scale)
            src_y = max(0.0, -self.main_window.map_offset_y / scale)
            src_w = w / scale
            src_h = h / scale

            # target = widget（无黑边），source 不超出（不拉伸）
            source_rect = QRectF(src_x, src_y, src_w, src_h)
            target_rect = QRectF(0, 0, w, h)
            painter.drawPixmap(target_rect, pixmap_to_draw, source_rect)

            if self.is_selecting and self.circle_center:
                circle_screen_x = self.main_window.map_offset_x + (self.circle_center.x() * self.main_window.map_scale)
                circle_screen_y = self.main_window.map_offset_y + (self.circle_center.y() * self.main_window.map_scale)
                circle_screen_radius = self.circle_radius * self.main_window.map_scale

                from PySide6.QtGui import QPainterPath
                mask_path = QPainterPath()
                mask_path.addRect(self.rect())

                circle_path = QPainterPath()
                circle_path.addEllipse(circle_screen_x - circle_screen_radius,
                                       circle_screen_y - circle_screen_radius,
                                       circle_screen_radius * 2,
                                       circle_screen_radius * 2)

                painter.setBrush(QBrush(QColor(0, 0, 0, 128)))
                painter.setPen(Qt.NoPen)

                mask_path = mask_path.subtracted(circle_path)
                painter.drawPath(mask_path)

                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor(124, 58, 237), 3))
                painter.drawEllipse(circle_screen_x - circle_screen_radius,
                                    circle_screen_y - circle_screen_radius,
                                    circle_screen_radius * 2,
                                    circle_screen_radius * 2)

                handle_size = 12
                handle_x = circle_screen_x + circle_screen_radius
                handle_y = circle_screen_y

                painter.setBrush(QBrush(QColor(124, 58, 237, 200)))
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.drawEllipse(handle_x - handle_size/2,
                                   handle_y - handle_size/2,
                                   handle_size, handle_size)

            if hasattr(self.main_window, 'collect_data') and self.main_window.collect_data:
                selected_resources = getattr(self.main_window, 'selected_resources', set())

                if not selected_resources:
                    resources_to_show = []
                else:
                    resources_to_show = list(selected_resources)

                # 资源图标缓存（从 main_window._resource_icon_cache 获取）
                icon_cache = getattr(self.main_window, '_resource_icon_cache', {})

                for resource_name in resources_to_show:
                    resource_info = self.main_window.collect_data.get(resource_name, {})
                    points = resource_info.get('points', [])

                    if not points:
                        continue

                    # 使用每个资源对应的图标
                    current_pixmap = icon_cache.get(resource_name)

                    if not current_pixmap or current_pixmap.isNull():
                        color_hash = hash(resource_name) % 360
                        marker_color = QColor.fromHsl(color_hash, 255, 150, 255)

                    for point in points:
                        lat = point.get('lat', 0)
                        lng = point.get('lng', 0)

                        x, y = self.main_window._game_to_map_coords(lat, lng)

                        screen_x = self.main_window.map_offset_x + (x * self.main_window.map_scale)
                        screen_y = self.main_window.map_offset_y + (y * self.main_window.map_scale)

                        if current_pixmap and not current_pixmap.isNull():
                            # 资源点大小：从设置读取基准值（默认24），随地图缩放等比放大，最小20像素保证可见
                            base_size = 24
                            try:
                                if hasattr(self.main_window, 'settings_manager'):
                                    base_size = self.main_window.settings_manager.get("resource_icon_size", 24)
                            except Exception:
                                pass
                            icon_size = max(20, int(base_size * self.main_window.map_scale))
                            scaled_icon = current_pixmap.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            painter.drawPixmap(int(screen_x - icon_size/2), int(screen_y - icon_size/2), scaled_icon)
                        else:
                            marker_size = max(12, 14 * self.main_window.map_scale)
                            painter.setPen(QPen(marker_color, max(2, int(3 * self.main_window.map_scale))))
                            painter.setBrush(QBrush(marker_color))
                            painter.drawEllipse(int(screen_x - marker_size/2), int(screen_y - marker_size/2),
                                              int(marker_size), int(marker_size))

        if hasattr(self.main_window, 'owl_stars_data') and self.main_window.owl_stars_data:
            selected_items = getattr(self.main_window, 'selected_owl_stars', set())

            for item_name in selected_items:
                if item_name not in self.main_window.owl_stars_data:
                    continue

                items = self.main_window.owl_stars_data[item_name].get('points', [])

                if '金' in item_name or '黄' in item_name:
                    current_pixmap = jx_pixmap
                elif '紫' in item_name:
                    current_pixmap = zx_pixmap
                elif '蓝' in item_name:
                    current_pixmap = lx_pixmap
                elif '宝箱' in item_name:
                    current_pixmap = xz_pixmap
                elif '乐谱' in item_name:
                    current_pixmap = yp_pixmap
                else:
                    current_pixmap = None

                if not current_pixmap or current_pixmap.isNull():
                    continue

                for item in items:
                    lat = item.get('lat', 0)
                    lng = item.get('lng', 0)

                    x, y = self.main_window._game_to_map_coords(lat, lng)
                    screen_x = self.main_window.map_offset_x + (x * self.main_window.map_scale)
                    screen_y = self.main_window.map_offset_y + (y * self.main_window.map_scale)

                    # 与"资源"栏图标大小一致：从设置读取基准值（默认24），随地图缩放等比放大
                    base_size = 24
                    try:
                        if hasattr(self.main_window, 'settings_manager'):
                            base_size = self.main_window.settings_manager.get("resource_icon_size", 24)
                    except Exception:
                        pass
                    icon_size = max(20, int(base_size * self.main_window.map_scale))
                    scaled_icon = current_pixmap.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    painter.drawPixmap(int(screen_x - icon_size/2), int(screen_y - icon_size/2), scaled_icon)

        if hasattr(self.main_window, 'route_visible') and self.main_window.route_visible:
            route_segments = getattr(self.main_window, 'route_segments', [])
            route_names = getattr(self.main_window, 'route_point_names', {})
            selected_pt = self.selected_route_point
            # 多选集合
            selected_pts_set = getattr(self, 'selected_route_points', set())
            selected_segs_set = getattr(self, 'selected_route_segments', set())

            if route_segments:
                display_points = []
                for seg_idx, segment in enumerate(route_segments):
                    for pt_idx, (x, y, is_checkpoint) in enumerate(segment):
                        display_x = self.main_window.map_offset_x + (x * self.main_window.map_scale)
                        display_y = self.main_window.map_offset_y + (y * self.main_window.map_scale)
                        display_points.append((display_x, display_y, is_checkpoint, seg_idx, pt_idx))
                    if seg_idx < len(route_segments) - 1:
                        display_points.append(None)

                # 绘制线段
                if len(display_points) >= 2:
                    route_line_color = getattr(self.main_window, 'route_color', QColor(34, 197, 94, 255))
                    selected_line_color = QColor(255, 255, 0, 255)  # 选中段用黄色高亮
                    painter.setBrush(Qt.NoBrush)

                    segment_start = 0
                    for i in range(len(display_points)):
                        if display_points[i] is None or i == len(display_points) - 1:
                            segment_end = i if display_points[i] is None else i + 1

                            # 当前 segment 在 route_segments 中的 seg_idx
                            seg_idx_cur = display_points[segment_start][3] if display_points[segment_start] is not None else -1

                            # 按检测点拆分该 segment 为子段，分别判断是否被选中
                            sub_start = segment_start
                            while sub_start < segment_end - 1:
                                # 子段起点：sub_start
                                # 子段终点：下一个检测点 或 segment_end-1
                                sub_end = sub_start + 1
                                while sub_end < segment_end - 1:
                                    # display_points[sub_end] 是子段中间点
                                    # 检查是否为检测点（即作为下一段的起点）
                                    if display_points[sub_end][2]:  # is_checkpoint
                                        break
                                    sub_end += 1
                                # sub_end 是子段最后一个点的索引（含），且 sub_end < segment_end
                                # 判断该子段是否被选中：selected_segs_set 中存的是 (seg_idx, start_pt, end_pt)
                                is_sub_selected = False
                                for sel_seg_idx, sel_start, sel_end in selected_segs_set:
                                    if sel_seg_idx == seg_idx_cur:
                                        # 把 display_points 索引转回 pt_idx
                                        sub_start_pt = display_points[sub_start][4]
                                        sub_end_pt = display_points[sub_end][4]
                                        if sel_start == sub_start_pt and sel_end == sub_end_pt:
                                            is_sub_selected = True
                                            break

                                line_color = selected_line_color if is_sub_selected else route_line_color
                                line_width = max(4, int(4 * self.main_window.map_scale)) if is_sub_selected else max(3, int(3 * self.main_window.map_scale))
                                painter.setPen(QPen(line_color, line_width, Qt.SolidLine))
                                # 画子段内的所有相邻线段（j 从 sub_start 到 sub_end-1）
                                for j in range(sub_start, sub_end):
                                    # 双重保险：确保 j+1 不越界
                                    if j + 1 >= segment_end:
                                        break
                                    if display_points[j] is not None and display_points[j + 1] is not None:
                                        x1, y1, _, _, _ = display_points[j]
                                        x2, y2, _, _, _ = display_points[j + 1]
                                        painter.drawLine(int(x1), int(y1), int(x2), int(y2))

                                # 下一个子段从当前 sub_end 开始（检测点同时是子段终点和下一段起点）
                                # 若 sub_end == sub_start 则说明没前进，强制 +1 避免死循环
                                if sub_end == sub_start:
                                    sub_start = sub_end + 1
                                else:
                                    sub_start = sub_end

                            segment_start = i + 1

                # 绘制路径点和名称
                point_counter = 0  # 全局路径点编号
                for point in display_points:
                    if point is None:
                        continue

                    x, y, is_checkpoint, seg_idx, pt_idx = point
                    point_counter += 1

                    # 判断是否选中（单选或属于多选集合）
                    is_selected = (selected_pt == (seg_idx, pt_idx) or
                                   (seg_idx, pt_idx) in selected_pts_set)
                    # 判断该点是否在被选中的子段范围内
                    if not is_selected:
                        for sel_seg_idx, sel_start, sel_end in selected_segs_set:
                            if sel_seg_idx == seg_idx and sel_start <= pt_idx <= sel_end:
                                is_selected = True
                                break

                    if is_checkpoint:
                        point_radius = max(10, int(10 * self.main_window.map_scale))
                        point_color = QColor(255, 165, 0, 255)
                    else:
                        point_radius = max(7, int(7 * self.main_window.map_scale))
                        point_color = getattr(self.main_window, 'route_color', QColor(34, 197, 94, 255))

                    # 选中的点：外圈高亮
                    if is_selected:
                        highlight_radius = point_radius + 6
                        painter.setPen(QPen(QColor(255, 255, 0, 200), 2, Qt.DashLine))
                        painter.setBrush(Qt.NoBrush)
                        painter.drawEllipse(int(x - highlight_radius), int(y - highlight_radius),
                                          int(highlight_radius * 2), int(highlight_radius * 2))

                    # 绘制点
                    painter.setPen(QPen(point_color, max(2, int(2 * self.main_window.map_scale)), Qt.SolidLine))
                    painter.setBrush(QBrush(point_color))
                    painter.drawEllipse(int(x - point_radius), int(y - point_radius),
                                      int(point_radius * 2), int(point_radius * 2))

                    # 绘制名称/编号
                    name = route_names.get((seg_idx, pt_idx), str(point_counter))
                    painter.setPen(QColor(255, 255, 255, 255))
                    font = painter.font()
                    font.setBold(True)
                    font.setPointSize(max(9, int(9 * self.main_window.map_scale)))
                    painter.setFont(font)
                    label_offset = point_radius + 4
                    painter.drawText(QRectF(x + label_offset, y - 10, 100, 20), Qt.AlignLeft | Qt.AlignVCenter, name)

            # 绘制预览线（路线绘制模式中）
            route_edit_mode = getattr(self.main_window, 'route_edit_mode', False)
            if route_edit_mode and self.route_preview_point is not None and self.route_preview_mouse is not None:
                # 起点（屏幕坐标）
                start_x = self.main_window.map_offset_x + (self.route_preview_point[0] * self.main_window.map_scale)
                start_y = self.main_window.map_offset_y + (self.route_preview_point[1] * self.main_window.map_scale)
                # 终点（屏幕坐标，已存储）
                end_x, end_y = self.route_preview_mouse

                # 虚线预览
                preview_color = QColor(255, 255, 0, 200) if self.route_snapped else QColor(
                    getattr(self.main_window, 'route_color', QColor(34, 197, 94, 255)).red(),
                    getattr(self.main_window, 'route_color', QColor(34, 197, 94, 255)).green(),
                    getattr(self.main_window, 'route_color', QColor(34, 197, 94, 255)).blue(),
                    180)
                painter.setPen(QPen(preview_color, max(2, int(2 * self.main_window.map_scale)), Qt.DashLine))
                painter.setBrush(Qt.NoBrush)
                painter.drawLine(int(start_x), int(start_y), int(end_x), int(end_y))

                # 预览终点小圆
                end_radius = max(5, int(5 * self.main_window.map_scale))
                painter.setBrush(QBrush(preview_color))
                painter.drawEllipse(int(end_x - end_radius), int(end_y - end_radius),
                                  int(end_radius * 2), int(end_radius * 2))

        # 绘制路线变换框
        if getattr(self.main_window, 'route_transform_active', False):
            bbox = self.main_window.route_transform_bbox
            if bbox:
                min_x, min_y, max_x, max_y = bbox
                t_scale = self.main_window.map_scale
                ox = self.main_window.map_offset_x
                oy = self.main_window.map_offset_y
                sx1 = ox + min_x * t_scale
                sy1 = oy + min_y * t_scale
                sx2 = ox + max_x * t_scale
                sy2 = oy + max_y * t_scale
                # 虚线框
                pen = QPen(QColor(124, 58, 237, 220), 2, Qt.DashLine)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(QRectF(sx1, sy1, sx2 - sx1, sy2 - sy1))
                # 8 个手柄（4 角 + 4 边中点，白色边框，紫色填充）
                handle_size = 10
                mid_x = (sx1 + sx2) / 2
                mid_y = (sy1 + sy2) / 2
                painter.setBrush(QBrush(QColor(124, 58, 237, 230)))
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                handles = [
                    (sx1, sy1), (sx2, sy1), (sx2, sy2), (sx1, sy2),  # 4 角
                    (mid_x, sy1), (mid_x, sy2),  # 上中、下中
                    (sx1, mid_y), (sx2, mid_y),  # 左中、右中
                ]
                for cxh, cyh in handles:
                    painter.drawRect(QRectF(cxh - handle_size/2, cyh - handle_size/2, handle_size, handle_size))
                # 提示文字
                painter.setPen(QPen(QColor(255, 255, 255, 220)))
                t_font = painter.font()
                t_font.setPointSize(9)
                painter.setFont(t_font)
                painter.drawText(QRectF(sx1, sy2 + 6, sx2 - sx1, 20), Qt.AlignCenter,
                                 "Enter 确认 / ESC 取消")

        painter.end()


# ================= 动画进度条组件 =================
class PokemonProgressBar(QWidget):
    """单条精灵进度条 - 带增长动画，数据在进度条右侧"""
    def __init__(self, pokemon_name, count, total, max_count, parent=None):
        super().__init__(parent)
        self.pokemon_name = pokemon_name
        self.count = count
        self.total = total
        self.max_count = max_count
        self._anim_progress = 0.0
        self.setFixedHeight(36)
        self.setMinimumWidth(200)

    def animate_in(self, delay=0):
        self._anim_progress = 0.0
        self.anim = QPropertyAnimation(self, b"anim_progress")
        self.anim.setDuration(600)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        if delay > 0:
            self.anim.setLoopCount(1)
            QTimer.singleShot(delay, self.anim.start)
        else:
            self.anim.start()

    def get_anim_progress(self):
        return self._anim_progress

    def set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    anim_progress = Property(float, get_anim_progress, set_anim_progress)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        bar_h = 24
        bar_y = (h - bar_h) // 2

        # 数据在右侧预留空间，进度条只画在左边区域
        data_area_w = 155
        track_w = max(60, min(220, w - data_area_w - 10))

        ratio = self.count / self.max_count if self.max_count > 0 else 0
        bar_w = int((track_w - 10) * ratio * self._anim_progress)
        pct = (self.count / self.total * 100) if self.total > 0 else 0

        # 背景轨道 — 宽度与填充进度一致
        bg_w = max(bar_w, 4)
        path = QPainterPath()
        path.addRoundedRect(0, bar_y, bg_w, bar_h, 6, 6)
        p.fillPath(path, QColor(30, 30, 45))

        # 前景进度条 - 亮色渐变
        if bar_w > 4:
            grad = QLinearGradient(0, 0, bar_w, 0)
            grad.setColorAt(0.0, QColor(147, 75, 250, 248))
            grad.setColorAt(1.0, QColor(196, 120, 252, 248))
            bar_path = QPainterPath()
            bar_path.addRoundedRect(2, bar_y + 2, max(bar_w - 4, 4), bar_h - 4, 4, 4)
            p.fillPath(bar_path, grad)
            p.setPen(QPen(QColor(167, 139, 250), 1.2))
            p.drawPath(bar_path)

        # 精灵名画在进度条内部
        p.setPen(QColor(248, 240, 255))
        font = p.font()
        font.setPointSize(11)
        font.setBold(True)
        p.setFont(font)
        p.drawText(12, bar_y + bar_h // 2 + 5, self.pokemon_name)

        # 次数+占比数据画在进度条右侧，紧挨进度条但不重叠
        font.setPointSize(10)
        font.setBold(False)
        p.setFont(font)
        p.setPen(QColor(196, 139, 252))
        count_text = f"{self.count} 次 ({pct:.1f}%)"
        p.drawText(track_w + 10, bar_y + bar_h // 2 + 5, count_text)

        p.end()


class TypeProgressBar(QWidget):
    """属性进度条 - 较小尺寸，带描边，数据在右侧"""

    def __init__(self, type_name, count, total, max_count, parent=None):
        super().__init__(parent)
        self.type_name = type_name
        self.count = count
        self.total = total
        self.max_count = max_count
        self._anim_progress = 0.0
        self.setFixedHeight(26)
        self.setMinimumWidth(200)

    def animate_in(self, delay=0):
        self._anim_progress = 0.0
        self.anim = QPropertyAnimation(self, b"anim_progress")
        self.anim.setDuration(500)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        if delay > 0:
            QTimer.singleShot(delay, self.anim.start)
        else:
            self.anim.start()

    def get_anim_progress(self):
        return self._anim_progress

    def set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    anim_progress = Property(float, get_anim_progress, set_anim_progress)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        bar_h = 16
        bar_y = (h - bar_h) // 2

        # 数据在右侧预留空间，进度条只画在左边区域
        data_area_w = 155
        track_w = max(60, min(220, w - data_area_w - 10))

        ratio = self.count / self.max_count if self.max_count > 0 else 0
        bar_w = int((track_w - 8) * ratio * self._anim_progress)
        pct = (self.count / self.total * 100) if self.total > 0 else 0

        # 统一属性进度条颜色（淡灰色）
        r, g, b = 150, 150, 150

        # 背景轨道 — 宽度与填充进度一致
        bg_w = max(bar_w, 4)
        path = QPainterPath()
        path.addRoundedRect(0, bar_y, bg_w, bar_h, 4, 4)
        p.fillPath(path, QColor(40, 40, 50))

        # 前景带描边 - 亮色
        if bar_w > 4:
            pen_color = QColor(min(r+100, 255), min(g+100, 255), min(b+100, 255))
            p.setPen(QPen(pen_color, 1.5))
            fill_color = QColor(r, g, b, 245)
            bar_path = QPainterPath()
            bar_path.addRoundedRect(2, bar_y + 1, max(bar_w - 4, 4), bar_h - 2, 3, 3)
            p.fillPath(bar_path, fill_color)
            p.drawPath(bar_path)

        # 属性名画在进度条内部
        font = p.font()
        font.setPointSize(9)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(240, 240, 255))
        p.drawText(10, bar_y + bar_h // 2 + 4, self.type_name)

        # 次数+占比数据画在进度条右侧
        font.setPointSize(8)
        font.setBold(False)
        p.setFont(font)
        p.setPen(QColor(200, 200, 220))
        count_text = f"{self.count} ({pct:.1f}%)"
        p.drawText(track_w + 10, bar_y + bar_h // 2 + 3, count_text)

        p.end()


# ================= 柱状图组件 =================

def _resolve_color(color_key):
    """将颜色键转换为RGB元组，支持字符串（属性名）和元组（RGB）"""
    if isinstance(color_key, (tuple, list)):
        r, g, b = color_key[:3]
        return int(r), int(g), int(b)
    return get_type_color(color_key)


class BarChartWidget(QWidget):
    """柱状图 - 带生长动画"""
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data  # [(label, count, type_or_color), ...]
        self._anim_progress = 0.0
        self.setMinimumHeight(260)

    def animate_in(self):
        self._anim_progress = 0.0
        self.anim = QPropertyAnimation(self, b"anim_progress")
        self.anim.setDuration(800)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()

    def get_anim_progress(self):
        return self._anim_progress

    def set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    anim_progress = Property(float, get_anim_progress, set_anim_progress)

    def paintEvent(self, event):
        if not self.data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        max_val = max(d[1] for d in self.data) if self.data else 1
        n = len(self.data)
        bar_w = min(60, max(20, (w - 60) // n - 6))

        if n <= 12 and bar_w >= 14:
            self.setMinimumHeight(260)
            self._draw_vertical_bars(p, w, h, n, bar_w, max_val)
        else:
            self._draw_horizontal_bars(p, w, n, max_val)

        p.end()

    def _draw_vertical_bars(self, p, w, h, n, bar_w, max_val):
        # Y轴标签区域宽度
        left_margin = 38
        total_w = n * (bar_w + 6)
        # 柱状图起始X（在Y轴右侧）
        start_x = left_margin + max(0, (w - left_margin - total_w) // 2)
        chart_top = 30
        chart_bottom = h - 30
        chart_height = chart_bottom - chart_top

        # 绘制Y轴刻度线和数值
        font = p.font()
        font.setPointSize(7)
        p.setFont(font)
        fm = QFontMetrics(font)
        
        y_axis_x = left_margin - 6
        
        # 计算刻度间隔
        if max_val <= 5:
            tick_interval = 1
        elif max_val <= 15:
            tick_interval = max(1, int(max_val / 5))
        elif max_val <= 50:
            tick_interval = 5
        else:
            tick_interval = 10
        
        # 生成刻度值列表（0 到 max_val，含 max_val）
        ticks = list(range(0, max_val + tick_interval, tick_interval))
        if ticks[-1] < max_val:
            ticks.append(max_val)
        
        for tick_val in ticks:
            if tick_val > max_val and tick_val == ticks[-1]:
                tick_val = max_val
            ratio = tick_val / max_val if max_val > 0 else 0
            tick_y = int(chart_bottom - ratio * chart_height)
            
            # 刻度线
            p.setPen(QColor(80, 80, 100))
            p.drawLine(y_axis_x - 3, tick_y, y_axis_x, tick_y)
            # 水平网格线（淡色）
            p.setPen(QColor(50, 50, 65))
            p.drawLine(y_axis_x, tick_y, start_x + total_w + 4, tick_y)
            
            # 刻度数值
            p.setPen(QColor(180, 180, 200))
            tick_text = str(tick_val)
            tw = fm.horizontalAdvance(tick_text)
            p.drawText(y_axis_x - 8 - tw, tick_y + 4, tick_text)
        
        # Y轴线和X轴基线
        p.setPen(QPen(QColor(100, 100, 130), 1))
        p.drawLine(y_axis_x, chart_top, y_axis_x, chart_bottom)
        p.drawLine(y_axis_x, chart_bottom, start_x + total_w + 4, chart_bottom)

        for i, (label, val, color_key) in enumerate(self.data):
            r, g, b = _resolve_color(color_key)
            bar_h = int((val / max_val) * chart_height * self._anim_progress) if max_val > 0 else 0
            x = start_x + i * (bar_w + 6)
            y = chart_bottom - bar_h

            grad = QLinearGradient(x, y, x, chart_bottom)
            grad.setColorAt(0.0, QColor(r, g, b, 240))
            grad.setColorAt(1.0, QColor(r//2 + 40, g//2 + 40, b//2 + 40, 200))
            p.fillRect(x, y, bar_w, max(bar_h, 1), grad)

            p.setPen(QPen(QColor(min(r+40,255), min(g+40,255), min(b+40,255)), 1))
            p.drawRect(x, y, bar_w, max(bar_h, 1))

            font.setPointSize(8)
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor(248, 240, 255))
            fm2 = QFontMetrics(font)
            val_text = str(val)
            val_w = fm2.horizontalAdvance(val_text)
            p.drawText(x + (bar_w - val_w)//2, y - 4, val_text)

            font.setPointSize(7)
            font.setBold(False)
            p.setFont(font)
            p.setPen(QColor(200, 200, 220))
            fm2 = QFontMetrics(font)
            label_w = fm2.horizontalAdvance(label)
            if label_w > bar_w + 4:
                label = label[:max(2, int(len(label) * (bar_w+4) / label_w))] + ".."
            p.drawText(x + (bar_w - fm2.horizontalAdvance(label))//2, h - 10, label)

    def _draw_horizontal_bars(self, p, w, n, max_val):
        bar_h = 28
        gap = 4
        total_h = n * (bar_h + gap)
        self.setMinimumHeight(max(260, total_h + 50))

        start_y = 10
        label_w = 80
        bar_area_w = w - label_w - 60

        for i, (label, val, color_key) in enumerate(self.data):
            r, g, b = _resolve_color(color_key)
            y = start_y + i * (bar_h + gap)
            bar_w = int((val / max_val) * bar_area_w * self._anim_progress)

            font = p.font()
            font.setPointSize(8)
            font.setBold(False)
            p.setFont(font)
            p.setPen(QColor(200, 200, 220))
            display_label = label if len(label) <= 6 else label[:5] + "."
            p.drawText(2, y + bar_h // 2 + 3, display_label)

            grad = QLinearGradient(label_w + 10, y, label_w + 10 + bar_w, y)
            grad.setColorAt(0.0, QColor(r, g, b, 240))
            grad.setColorAt(1.0, QColor(r//2 + 40, g//2 + 40, b//2 + 40, 200))
            p.fillRect(label_w + 10, y, max(bar_w, 1), bar_h, grad)

            p.setPen(QPen(QColor(min(r+40,255), min(g+40,255), min(b+40,255)), 1))
            p.drawRect(label_w + 10, y, max(bar_w, 1), bar_h)

            font.setPointSize(8)
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor(248, 240, 255))
            val_text = str(val)
            p.drawText(label_w + 16 + bar_w, y + bar_h // 2 + 3, val_text)


# ================= 饼图组件 =================
class PieChartWidget(QWidget):
    """饼图 - 带旋转进场动画"""
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data  # [(label, count, type_or_color), ...]
        self._anim_progress = 0.0
        self.setMinimumHeight(200)

    def animate_in(self):
        self._anim_progress = 0.0
        self.anim = QPropertyAnimation(self, b"anim_progress")
        self.anim.setDuration(1000)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()

    def get_anim_progress(self):
        return self._anim_progress

    def set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    anim_progress = Property(float, get_anim_progress, set_anim_progress)

    def paintEvent(self, event):
        if not self.data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        total = sum(d[1] for d in self.data)
        if total == 0:
            p.end()
            return

        n = len(self.data)
        legend_item_h = 22
        col1_count = (n + 1) // 2
        col2_count = n - col1_count
        max_col_count = max(col1_count, col2_count)
        legend_total_h = max_col_count * legend_item_h + 10

        cx, cy = w // 2 - 80, max(h // 2, 100)
        radius = min(w // 2 - 100, h // 2 - 20, 90)

        rotation_angle = -360.0 * (1.0 - self._anim_progress)
        p.save()
        p.translate(cx, cy)
        p.rotate(rotation_angle)
        p.translate(-cx, -cy)

        start_angle = 90 * 16
        for label, val, color_key in self.data:
            r, g, b = _resolve_color(color_key)
            span = int(val / total * 360 * 16)
            if span < 1:
                span = 1

            p.setPen(QPen(QColor(min(r+60,255), min(g+60,255), min(b+60,255)), 1.5))
            p.setBrush(QColor(r, g, b, 230))
            p.drawPie(cx - radius, cy - radius, radius * 2, radius * 2, start_angle, span)
            start_angle += span

        p.restore()

        legend_x = cx + radius + 20
        col_w = min(185, max(120, (w - legend_x - 20) // 2))
        font = p.font()
        font.setPointSize(8)
        p.setFont(font)

        col1_y = cy - legend_total_h // 2
        col2_x = legend_x + col_w + 10
        col2_y = col1_y

        for idx, (label, val, color_key) in enumerate(self.data):
            r, g, b = _resolve_color(color_key)
            pct = val / total * 100

            if idx < col1_count:
                lx = legend_x
                ly = col1_y + idx * legend_item_h
            else:
                lx = col2_x
                ly = col2_y + (idx - col1_count) * legend_item_h

            p.fillRect(lx, ly, 10, 10, QColor(r, g, b))
            p.setPen(QPen(QColor(min(r+40,255), min(g+40,255), min(b+40,255)), 1))
            p.drawRect(lx, ly, 10, 10)
            p.setPen(QColor(230, 230, 240))
            
            # 根据名字长度调整显示文本，避免溢出
            label_text = f"{label} {val} ({pct:.1f}%)"
            fm = QFontMetrics(font)
            # 截断过长文本
            max_label_w = col_w - 20
            if fm.horizontalAdvance(label_text) > max_label_w:
                # 缩短：去掉百分比的小数部分
                label_text = f"{label} {val} ({int(pct)}%)"
                if fm.horizontalAdvance(label_text) > max_label_w:
                    # 进一步截断精灵名
                    short_label = label[:3]
                    label_text = f"{short_label} {val} ({int(pct)}%)"
            p.drawText(lx + 16, ly + 9, label_text)

        need_h = max(h, cy + radius + 20, legend_total_h + 40)
        self.setMinimumHeight(max(200, need_h))

        p.end()


class CustomPokemonDialog(QDialog):
    """自定义精灵对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新增自定义精灵")
        self.setModal(True)
        self.setFixedSize(800, 620)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 对话框头部
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #1a1a22;
                border-bottom: 1px solid rgba(124, 58, 237, 0.1);
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 16)
        
        title = QLabel("新增自定义精灵")
        title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 600;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                color: #71717a;
                background: transparent;
                border: none;
                font-size: 20px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)
        
        main_layout.addWidget(header)
        
        # 对话框主体
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(32, 28, 32, 28)
        body_layout.setSpacing(18)
        
        # 精灵名称
        name_group = QWidget()
        name_vlayout = QVBoxLayout(name_group)
        name_vlayout.setContentsMargins(0, 0, 0, 0)
        name_vlayout.setSpacing(4)
        
        name_label = QLabel("精灵名称")
        name_label.setStyleSheet("color: #71717a; font-size: 12px;")
        name_vlayout.addWidget(name_label)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入精灵名称")
        self.name_edit.setMinimumHeight(40)
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 15px;
            }
            QLineEdit:focus {
                border: 1px solid #7c3aed;
            }
        """)
        name_vlayout.addWidget(self.name_edit)
        body_layout.addWidget(name_group)
        
        # 属性
        type_group = QWidget()
        type_vlayout = QVBoxLayout(type_group)
        type_vlayout.setContentsMargins(0, 0, 0, 0)
        type_vlayout.setSpacing(4)
        
        type_label = QLabel("属性")
        type_label.setStyleSheet("color: #71717a; font-size: 12px;")
        type_vlayout.addWidget(type_label)
        
        # 属性多选容器（支持1-2个属性）
        self.type_selection_widget = QWidget()
        type_selection_layout = QHBoxLayout(self.type_selection_widget)
        type_selection_layout.setContentsMargins(0, 4, 0, 0)
        type_selection_layout.setSpacing(8)
        
        # 第一个属性选择
        self.type_combo_1 = TriangleComboBox()
        self.type_combo_1.addItems(["请选择"] + get_all_types())
        self.type_combo_1.setMinimumHeight(40)
        self.type_combo_1.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 15px;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)
        type_selection_layout.addWidget(self.type_combo_1)
        
        # 第二个属性选择
        self.type_combo_2 = TriangleComboBox()
        self.type_combo_2.addItems(["无"] + get_all_types())
        self.type_combo_2.setMinimumHeight(40)
        self.type_combo_2.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 15px;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)
        type_selection_layout.addWidget(self.type_combo_2)
        
        type_vlayout.addWidget(self.type_selection_widget)
        body_layout.addWidget(type_group)
        
        # 默认保底次数
        target_group = QWidget()
        target_vlayout = QVBoxLayout(target_group)
        target_vlayout.setContentsMargins(0, 0, 0, 0)
        target_vlayout.setSpacing(4)
        
        target_label = QLabel("默认保底次数")
        target_label.setStyleSheet("color: #71717a; font-size: 12px;")
        target_vlayout.addWidget(target_label)
        
        self.target_edit = QLineEdit()
        self.target_edit.setText("80")
        self.target_edit.setMinimumHeight(40)
        self.target_edit.setStyleSheet("""
            QLineEdit {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 15px;
            }
            QLineEdit:focus {
                border: 1px solid #7c3aed;
            }
        """)
        target_vlayout.addWidget(self.target_edit)
        body_layout.addWidget(target_group)
        
        # 进化链
        evolution_group = QWidget()
        evolution_vlayout = QVBoxLayout(evolution_group)
        evolution_vlayout.setContentsMargins(0, 0, 0, 0)
        evolution_vlayout.setSpacing(4)
        
        evolution_label = QLabel("进化链（选填，用 → 分隔，如：雪娃娃 → 冰封怨灵 → 雪灵）")
        evolution_label.setStyleSheet("color: #71717a; font-size: 12px;")
        evolution_vlayout.addWidget(evolution_label)
        
        self.evolution_edit = QLineEdit()
        self.evolution_edit.setPlaceholderText("例如：雪娃娃 → 冰封怨灵 → 雪灵")
        self.evolution_edit.setMinimumHeight(40)
        self.evolution_edit.setStyleSheet("""
            QLineEdit {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 15px;
            }
            QLineEdit:focus {
                border: 1px solid #7c3aed;
            }
        """)
        evolution_vlayout.addWidget(self.evolution_edit)
        body_layout.addWidget(evolution_group)
        
        # 精灵图标（本地图片）
        icon_group = QWidget()
        icon_vlayout = QVBoxLayout(icon_group)
        icon_vlayout.setContentsMargins(0, 0, 0, 0)
        icon_vlayout.setSpacing(4)
        
        icon_label = QLabel("精灵图标")
        icon_label.setStyleSheet("color: #71717a; font-size: 12px;")
        icon_vlayout.addWidget(icon_label)
        
        # 图片预览和选择按钮
        icon_select_widget = QWidget()
        icon_select_layout = QHBoxLayout(icon_select_widget)
        icon_select_layout.setContentsMargins(0, 4, 0, 0)
        icon_select_layout.setSpacing(12)
        
        # 图片预览
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(60, 60)
        self.icon_preview.setAlignment(Qt.AlignCenter)
        self.icon_preview.setText("无图片")
        self.icon_preview.setStyleSheet("""
            QLabel {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                color: #71717a;
                font-size: 12px;
            }
        """)
        icon_select_layout.addWidget(self.icon_preview)
        
        # 选择按钮
        select_btn = QPushButton("📁 选择图片")
        select_btn.setFixedHeight(40)
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 16px;
                color: #e4e4e7;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(124, 58, 237, 0.1);
                border: 1px solid #7c3aed;
            }
        """)
        select_btn.clicked.connect(self.select_icon_image)
        icon_select_layout.addWidget(select_btn, stretch=1)
        
        icon_vlayout.addWidget(icon_select_widget)
        body_layout.addWidget(icon_group)
        
        # 保存当前选择的图片路径
        self.selected_icon_path = ""
        
        main_layout.addWidget(body)
        
        # 对话框底部
        footer = QWidget()
        footer.setStyleSheet("""
            QWidget {
                background-color: #1a1a22;
                border-top: 1px solid rgba(124, 58, 237, 0.1);
            }
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(32, 20, 32, 20)
        footer_layout.setSpacing(12)
        footer_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("customPokemonBtn")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)
        
        confirm_btn = QPushButton("确认添加")
        confirm_btn.setObjectName("customPokemonBtn")
        confirm_btn.setFixedHeight(40)
        confirm_btn.setMinimumWidth(100)
        confirm_btn.setStyleSheet("""
            QPushButton#customPokemonBtn {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c3aed, stop:1 #a855f7);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton#customPokemonBtn:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9333ea, stop:1 #c084fc);
            }
            QPushButton#customPokemonBtn:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6d28d9, stop:1 #9333ea);
            }
        """)
        confirm_btn.clicked.connect(self.accept)
        footer_layout.addWidget(confirm_btn)
        
        main_layout.addWidget(footer)
    
    def select_icon_image(self):
        """选择本地图片文件"""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择精灵图标",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            self.selected_icon_path = file_path
            # 更新预览
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.icon_preview.setPixmap(scaled_pixmap)
                self.icon_preview.setText("")
                self.icon_preview.setStyleSheet("""
                    QLabel {
                        background-color: #252530;
                        border: 1px solid rgba(124, 58, 237, 0.2);
                        border-radius: 8px;
                    }
                """)
    
    def get_data(self):
        # 获取选中的属性
        type1 = self.type_combo_1.currentText()
        type2 = self.type_combo_2.currentText()
        
        # 组合属性（过滤掉“请选择”和“无”）
        types = []
        if type1 != "请选择":
            types.append(type1)
        if type2 != "无" and type2 != "请选择":
            types.append(type2)
        
        type_str = "、".join(types) if types else ""
        
        # 解析进化链
        evolution_text = self.evolution_edit.text().strip()
        evolution_chain = []
        if evolution_text:
            # 支持多种分隔符：→、-、>
            import re
            parts = re.split(r'[→\->]+', evolution_text)
            evolution_chain = [p.strip() for p in parts if p.strip()]
        
        return (
            self.name_edit.text().strip(),
            type_str,
            self.target_edit.text(),
            self.selected_icon_path,  # 返回图片路径
            evolution_chain  # 返回进化链
        )


class EditPokemonDialog(QDialog):
    """编辑自定义精灵对话框"""
    def __init__(self, pokemon, parent=None):
        super().__init__(parent)
        self.original_name = pokemon["name"]
        self.setWindowTitle("修改自定义精灵")
        self.setModal(True)
        self.setFixedSize(800, 620)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 对话框头部
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #1a1a22;
                border-bottom: 1px solid rgba(124, 58, 237, 0.1);
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 16)
        
        title = QLabel("修改自定义精灵")
        title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 600;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                color: #71717a;
                background: transparent;
                border: none;
                font-size: 20px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)
        
        main_layout.addWidget(header)
        
        # 对话框主体
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(32, 28, 32, 28)
        body_layout.setSpacing(18)
        
        # 精灵名称
        name_group = QWidget()
        name_vlayout = QVBoxLayout(name_group)
        name_vlayout.setContentsMargins(0, 0, 0, 0)
        name_vlayout.setSpacing(4)
        
        name_label = QLabel("精灵名称")
        name_label.setStyleSheet("color: #71717a; font-size: 12px;")
        name_vlayout.addWidget(name_label)
        
        self.name_edit = QLineEdit()
        self.name_edit.setText(pokemon["name"])
        self.name_edit.setMinimumHeight(40)
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 15px;
            }
            QLineEdit:focus {
                border: 1px solid #7c3aed;
            }
        """)
        name_vlayout.addWidget(self.name_edit)
        body_layout.addWidget(name_group)
        
        # 属性
        type_group = QWidget()
        type_vlayout = QVBoxLayout(type_group)
        type_vlayout.setContentsMargins(0, 0, 0, 0)
        type_vlayout.setSpacing(4)
        
        type_label = QLabel("属性")
        type_label.setStyleSheet("color: #71717a; font-size: 12px;")
        type_vlayout.addWidget(type_label)
        
        # 解析当前属性
        current_types = pokemon.get("types", [])
        if not current_types:
            # 兼容旧版type字段
            type_str_old = pokemon.get("type", "")
            if type_str_old:
                current_types = [t.strip() for t in type_str_old.split("、") if t.strip()]
        
        if isinstance(current_types, str):
            current_types = [t.strip() for t in current_types.split("、") if t.strip()]
        
        # 属性多选容器
        self.type_selection_widget = QWidget()
        type_selection_layout = QHBoxLayout(self.type_selection_widget)
        type_selection_layout.setContentsMargins(0, 4, 0, 0)
        type_selection_layout.setSpacing(8)
        
        # 第一个属性选择
        self.type_combo_1 = TriangleComboBox()
        self.type_combo_1.addItems(["请选择"] + get_all_types())
        if len(current_types) > 0:
            self.type_combo_1.setCurrentText(current_types[0])
        self.type_combo_1.setMinimumHeight(40)
        self.type_combo_1.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 15px;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)
        type_selection_layout.addWidget(self.type_combo_1)
        
        # 第二个属性选择
        self.type_combo_2 = TriangleComboBox()
        self.type_combo_2.addItems(["无"] + get_all_types())
        if len(current_types) > 1:
            self.type_combo_2.setCurrentText(current_types[1])
        self.type_combo_2.setMinimumHeight(40)
        self.type_combo_2.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 15px;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)
        type_selection_layout.addWidget(self.type_combo_2)
        
        type_vlayout.addWidget(self.type_selection_widget)
        body_layout.addWidget(type_group)
        
        # 图标（本地图片）
        icon_group = QWidget()
        icon_vlayout = QVBoxLayout(icon_group)
        icon_vlayout.setContentsMargins(0, 0, 0, 0)
        icon_vlayout.setSpacing(4)
        
        icon_label = QLabel("精灵图标")
        icon_label.setStyleSheet("color: #71717a; font-size: 12px;")
        icon_vlayout.addWidget(icon_label)
        
        # 图片预览和选择按钮
        icon_select_widget = QWidget()
        icon_select_layout = QHBoxLayout(icon_select_widget)
        icon_select_layout.setContentsMargins(0, 4, 0, 0)
        icon_select_layout.setSpacing(12)
        
        # 图片预览
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(60, 60)
        self.icon_preview.setAlignment(Qt.AlignCenter)
        self.icon_preview.setStyleSheet("""
            QLabel {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
            }
        """)
        
        # 加载当前图片
        current_icon = pokemon.get("icon", "")
        if current_icon and os.path.exists(current_icon):
            pixmap = QPixmap(current_icon)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.icon_preview.setPixmap(scaled_pixmap)
        else:
            self.icon_preview.setText("无图片")
            self.icon_preview.setStyleSheet("""
                QLabel {
                    background-color: #252530;
                    border: 1px solid rgba(124, 58, 237, 0.2);
                    border-radius: 8px;
                    color: #71717a;
                    font-size: 12px;
                }
            """)
        
        icon_select_layout.addWidget(self.icon_preview)
        
        # 选择按钮
        select_btn = QPushButton("📁 选择图片")
        select_btn.setFixedHeight(40)
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 16px;
                color: #e4e4e7;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(124, 58, 237, 0.1);
                border: 1px solid #7c3aed;
            }
        """)
        select_btn.clicked.connect(self.select_icon_image)
        icon_select_layout.addWidget(select_btn, stretch=1)
        
        icon_vlayout.addWidget(icon_select_widget)
        body_layout.addWidget(icon_group)
        
        # 保存当前选择的图片路径
        self.selected_icon_path = current_icon if current_icon and os.path.exists(current_icon) else ""
        
        main_layout.addWidget(body, stretch=1)
        
        # 底部按钮
        footer = QWidget()
        footer.setStyleSheet("""
            QWidget {
                background-color: #1a1a22;
                border-top: 1px solid rgba(124, 58, 237, 0.1);
            }
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 16, 24, 16)
        footer_layout.setSpacing(12)
        
        # 删除按钮
        delete_btn = QPushButton("🗑️ 删除")
        delete_btn.setFixedHeight(40)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.1);
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 8px;
                padding: 10px 20px;
                color: #ef4444;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
            }
        """)
        delete_btn.clicked.connect(self.delete_and_close)
        footer_layout.addWidget(delete_btn)
        
        footer_layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setFixedWidth(100)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 20px;
                color: #e4e4e7;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(124, 58, 237, 0.1);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)
        
        # 保存按钮
        save_btn = QPushButton("💾 保存")
        save_btn.setFixedHeight(40)
        save_btn.setFixedWidth(100)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #7c3aed;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                color: white;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #6d28d9;
            }
        """)
        save_btn.clicked.connect(self.accept)
        footer_layout.addWidget(save_btn)
        
        main_layout.addWidget(footer)
    
    def delete_and_close(self):
        """删除并关闭"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除自定义精灵【{self.original_name}】吗？\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.done(2)  # 特殊返回值2表示删除（避免与Accepted=1冲突）
    
    def select_icon_image(self):
        """选择本地图片文件"""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择精灵图标",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            self.selected_icon_path = file_path
            # 更新预览
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.icon_preview.setPixmap(scaled_pixmap)
                self.icon_preview.setText("")
                self.icon_preview.setStyleSheet("""
                    QLabel {
                        background-color: #252530;
                        border: 1px solid rgba(124, 58, 237, 0.2);
                        border-radius: 8px;
                    }
                """)
    
    def get_data(self):
        """获取编辑后的数据"""
        type1 = self.type_combo_1.currentText()
        type2 = self.type_combo_2.currentText()
        
        # 组合属性（过滤掉“请选择”和“无”）
        types = []
        if type1 != "请选择":
            types.append(type1)
        if type2 != "无" and type2 != "请选择":
            types.append(type2)
        
        type_str = "、".join(types) if types else ""
        
        return (
            self.name_edit.text().strip(),
            type_str,
            self.selected_icon_path  # 返回图片路径
        )


class KeyCaptureDialog(QDialog):
    """热键捕获对话框 - 按下目标组合键完成绑定"""
    key_captured = Signal(dict)

    VK_NAMES = {
        0x4E: "N", 0x4D: "M", 0xBB: "+", 0xBD: "-", 0xDB: "[", 0xDD: "]",
        0xBC: ",", 0xBE: ".", 0xBF: "/", 0xBA: ";", 0xDC: "\\",
        0xC0: "`", 0xDE: "'", 0xBD: "-", 0xBB: "=",
        0x30: "0", 0x31: "1", 0x32: "2", 0x33: "3", 0x34: "4",
        0x35: "5", 0x36: "6", 0x37: "7", 0x38: "8", 0x39: "9",
        0x41: "A", 0x42: "B", 0x43: "C", 0x44: "D", 0x45: "E",
        0x46: "F", 0x47: "G", 0x48: "H", 0x49: "I", 0x4A: "J",
        0x4B: "K", 0x4C: "L", 0x4F: "O", 0x50: "P",
        0x51: "Q", 0x52: "R", 0x53: "S", 0x54: "T", 0x55: "U",
        0x56: "V", 0x57: "W", 0x58: "X", 0x59: "Y", 0x5A: "Z",
        0x70: "F1", 0x71: "F2", 0x72: "F3", 0x73: "F4",
        0x74: "F5", 0x75: "F6", 0x76: "F7", 0x77: "F8",
        0x78: "F9", 0x79: "F10", 0x7A: "F11", 0x7B: "F12",
    }

    ALPHA_VK = set(range(0x41, 0x5B))  # A-Z
    DIGIT_VK = set(range(0x30, 0x3A))  # 0-9

    MODIFIER_KEYS = {Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta}

    MOD_KEY_MAP = {
        Qt.Key_Control: ("Ctrl", 0x0002),
        Qt.Key_Shift: ("Shift", 0x0004),
        Qt.Key_Alt: ("Alt", 0x0001),
        Qt.Key_Meta: ("Meta", 0x0008),
    }

    MOD_QT_FLAGS = {
        "Ctrl": 0x04000000,   # Qt.ControlModifier
        "Shift": 0x02000000,  # Qt.ShiftModifier
        "Alt": 0x08000000,    # Qt.AltModifier
    }

    def __init__(self, current_label, parent=None):
        super().__init__(parent)
        self.setWindowTitle("绑定热键")
        self.setFixedSize(360, 200)
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet("background-color: #1e1e26; border: 1px solid #7c3aed; border-radius: 10px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        self.info_label = QLabel(f"当前: {current_label}\n请按下新的组合键...")
        self.info_label.setStyleSheet("color: #e2e8f0; font-size: 14px; border: none;")
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)

        hint = QLabel("支持 Ctrl / Shift / Alt + 任意键，Esc 取消")
        hint.setStyleSheet("color: #71717a; font-size: 12px; border: none;")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        self._cancel_btn = QPushButton("取消")
        self._cancel_btn.setFixedHeight(34)
        self._cancel_btn.setCursor(Qt.PointingHandCursor)
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #252530; color: #94a3b8;
                border: 1px solid #3f3f46; border-radius: 6px; font-size: 13px;
            }
            QPushButton:hover { background-color: #2a2a35; }
        """)
        self._cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self._cancel_btn)

        self._captured = None
        self._held_mods = set()

    def showEvent(self, event):
        super().showEvent(event)
        self.grabKeyboard()
        self.setFocus()

    def _mods_to_modcode(self):
        """将当前按住的修饰符集合转换为 mod_code 位掩码"""
        code = 0
        for mod_name in self._held_mods:
            if mod_name == "Ctrl":
                code |= 0x0002
            elif mod_name == "Shift":
                code |= 0x0004
            elif mod_name == "Alt":
                code |= 0x0001
        return code

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.reject()
            return

        if key in self.MODIFIER_KEYS:
            mod_name, _ = self.MOD_KEY_MAP[key]
            self._held_mods.add(mod_name)
            mod_code = self._mods_to_modcode()
            mod_display = "+".join(sorted(self._held_mods))
            if mod_code == 0:
                self.info_label.setText(f"按住修饰符后按下目标键...\n当前: {mod_display}")
            else:
                self.info_label.setText(f"按住 {mod_display} 后按下目标键...")
            return

        # 读取当前修饰符状态（通过 Qt 事件修饰符）
        modifiers = int(event.modifiers().value)
        mod_code = 0
        held_names = set()
        if modifiers & 0x04000000:  # Qt.ControlModifier
            mod_code |= 0x0002
            held_names.add("Ctrl")
        if modifiers & 0x02000000:  # Qt.ShiftModifier
            mod_code |= 0x0004
            held_names.add("Shift")
        if modifiers & 0x08000000:  # Qt.AltModifier
            mod_code |= 0x0001
            held_names.add("Alt")

        mod_name = ""
        mod_list = []
        if mod_code & 0x0002:
            mod_list.append("Ctrl")
        if mod_code & 0x0004:
            mod_list.append("Shift")
        if mod_code & 0x0001:
            mod_list.append("Alt")
        mod_name = "+".join(mod_list)
        if mod_name:
            mod_name += "+"

        vk = self._qt_key_to_vk(key)
        key_name = self.VK_NAMES.get(vk, "")
        if not key_name:
            raw = Qt.Key(key).name
            if isinstance(raw, bytes):
                raw = raw.decode()
            if raw.startswith("Key_"):
                raw = raw[4:]
            key_name = raw

        if mod_code == 0 and (vk in self.ALPHA_VK or vk in self.DIGIT_VK):
            msg = QMessageBox(self)
            msg.setWindowTitle("⚠️ 键盘冲突警告")
            msg.setText(f"你正在把热键绑定为单独的「{key_name}」键。\n\n"
                        f"这会导致所有程序中按 {key_name} 都无法正常输入！")
            msg.setInformativeText("建议添加 Ctrl / Shift / Alt 修饰符。\n确定要继续吗？")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            msg.setStyleSheet("background-color: #1e1e26; color: #e2e8f0;")
            if msg.exec() == QMessageBox.No:
                return

        display_name = mod_name + key_name
        result = {"mod": mod_name.rstrip("+"), "key": key_name, "vk": vk, "mod_code": mod_code, "display": display_name}
        self._captured = result
        self.accept()

    def keyReleaseEvent(self, event):
        key = event.key()
        if key in self.MODIFIER_KEYS:
            mod_name, _ = self.MOD_KEY_MAP[key]
            self._held_mods.discard(mod_name)
            remaining = "+".join(sorted(self._held_mods))
            if remaining:
                self.info_label.setText(f"按住 {remaining} 后按下目标键...")

    def _qt_key_to_vk(self, qt_key):
        map_qt = {
            Qt.Key_N: 0x4E, Qt.Key_M: 0x4D,
            Qt.Key_Plus: 0xBB, Qt.Key_Minus: 0xBD,
            Qt.Key_BracketLeft: 0xDB, Qt.Key_BracketRight: 0xDD,
            Qt.Key_Comma: 0xBC, Qt.Key_Period: 0xBE,
            Qt.Key_Slash: 0xBF, Qt.Key_Semicolon: 0xBA,
            Qt.Key_Backslash: 0xDC, Qt.Key_QuoteLeft: 0xC0,
            Qt.Key_Apostrophe: 0xDE, Qt.Key_Equal: 0xBB,
            Qt.Key_A: 0x41, Qt.Key_B: 0x42, Qt.Key_C: 0x43,
            Qt.Key_D: 0x44, Qt.Key_E: 0x45, Qt.Key_F: 0x46,
            Qt.Key_G: 0x47, Qt.Key_H: 0x48, Qt.Key_I: 0x49,
            Qt.Key_J: 0x4A, Qt.Key_K: 0x4B, Qt.Key_L: 0x4C,
            Qt.Key_O: 0x4F, Qt.Key_P: 0x50,
            Qt.Key_Q: 0x51, Qt.Key_R: 0x52, Qt.Key_S: 0x53,
            Qt.Key_T: 0x54, Qt.Key_U: 0x55, Qt.Key_V: 0x56,
            Qt.Key_W: 0x57, Qt.Key_X: 0x58, Qt.Key_Y: 0x59,
            Qt.Key_Z: 0x5A,
            Qt.Key_0: 0x30, Qt.Key_1: 0x31, Qt.Key_2: 0x32,
            Qt.Key_3: 0x33, Qt.Key_4: 0x34, Qt.Key_5: 0x35,
            Qt.Key_6: 0x36, Qt.Key_7: 0x37, Qt.Key_8: 0x38,
            Qt.Key_9: 0x39,
            Qt.Key_F1: 0x70, Qt.Key_F2: 0x71, Qt.Key_F3: 0x72,
            Qt.Key_F4: 0x73, Qt.Key_F5: 0x74, Qt.Key_F6: 0x75,
            Qt.Key_F7: 0x76, Qt.Key_F8: 0x77, Qt.Key_F9: 0x78,
            Qt.Key_F10: 0x79, Qt.Key_F11: 0x7A, Qt.Key_F12: 0x7B,
        }
        return map_qt.get(qt_key, 0)


# 精灵类型查找缓存
_POKEMON_TYPE_CACHE = None

def _build_pokemon_type_cache():
    """构建精灵名称到属性列表的缓存映射"""
    global _POKEMON_TYPE_CACHE
    if _POKEMON_TYPE_CACHE is not None:
        return _POKEMON_TYPE_CACHE
    _POKEMON_TYPE_CACHE = {}
    db = load_pokemon_database("第一赛季")
    for entry in db:
        name = entry.get("name", "")
        types = entry.get("types", [])
        if name:
            _POKEMON_TYPE_CACHE[name] = types
    db2 = load_pokemon_database("第二赛季")
    for entry in db2:
        name = entry.get("name", "")
        types = entry.get("types", [])
        if name and name not in _POKEMON_TYPE_CACHE:
            _POKEMON_TYPE_CACHE[name] = types
    db3 = load_pokemon_database("第三赛季")
    for entry in db3:
        name = entry.get("name", "")
        types = entry.get("types", [])
        if name and name not in _POKEMON_TYPE_CACHE:
            _POKEMON_TYPE_CACHE[name] = types
    custom = load_custom_pokemon()
    for entry in custom:
        name = entry.get("name", "")
        t = entry.get("type", "")
        if name and name not in _POKEMON_TYPE_CACHE:
            _POKEMON_TYPE_CACHE[name] = [t] if t else []
    return _POKEMON_TYPE_CACHE

def get_pokemon_types(name):
    """获取精灵的属性列表，返回如 ['火系', '萌系'] 的列表"""
    cache = _build_pokemon_type_cache()
    return cache.get(name, [])


# 宝箱分类合并：将 A1/A2/A2-2 等版本的宝箱统一为单一分类
_CHEST_ELEMENTS = ['幽系', '草系', '火系', '水系', '光系', '地系', '冰系', '电系',
                   '毒系', '虫系', '武系', '翼系', '恶系', '机械系', '龙系', '萌系', '幻系']

def _merge_chest_name(name):
    """根据宝箱名称合并分类（按优先级匹配）"""
    if '隐藏' in name:
        return '隐藏宝箱'
    if '华丽' in name:
        return '华丽宝箱'
    if '贵重' in name or '珍贵' in name:
        return '贵重宝箱'
    for elem in _CHEST_ELEMENTS:
        if elem in name:
            return f'{elem}宝箱'
    if '高级' in name:
        return '高级宝箱'
    if '中级' in name:
        return '中级宝箱'
    if '初级' in name or '普通' in name:
        return '普通宝箱'
    return '其他宝箱'


class MainWindow(QMainWindow):
    # 自定义信号：当计数器数据变化时发射，让悬浮窗同步
    counter_changed = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("可丽希亚助手")
        self.resize(1800, 950)
        
        # 获取基础目录
        self._base_dir = os.path.join(os.path.dirname(__file__), '..')
        
        # 设置窗口图标（任务栏图标）
        icon_path = os.path.join(self._base_dir, "image", "tb", "klxy.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # 去掉标题栏和顶部留白
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # 核心数据管理器
        self.manager = CounterManager()
        
        # 设置管理器
        self.settings_manager = SettingsManager()
        
        # 初始化进化链管理器
        self.evolution_manager = EvolutionManager()
        
        # 将evolution_manager注入到CounterManager
        self.manager.evolution_manager = self.evolution_manager
        
        # 初始化OCR和游戏捕获
        self.game_capture = GameCapture()
        self.game_capture.settings_manager = self.settings_manager
        # 将evolution_manager注入到GameCapture
        self.game_capture.evolution_manager = self.evolution_manager
        
        # 预热OCR引擎（启动1秒后后台加载，避免运行时首卡顿）
        QTimer.singleShot(1000, lambda: self.game_capture.prewarm_ocr())
        
        # 联动识别状态
        self.last_recognized_lkwg = None  # 上次识别到的洛克王国精灵
        self.xt_icon_detected = False  # 是否检测到xt图标
        self.xt100_detected = False  # 是否检测到xt100
        self.current_battle_lkwg = None  # 当前战斗中的洛克王国精灵名
        self._breakthrough_counted_for_current_battle = False  # 当前战斗是否已计数(防重复)
        # 血脉识别状态：检测到四叶草铅绘后激活，2秒内识别到血脉关键字则显示对应颜色，否则显示"普通"
        self._bloodline_check_active = False
        self._bloodline_check_start_time = 0  # 血脉检查开始时间（time.time()）
        self._bloodline_check_timeout = 2.0  # 血脉检查2秒超时
        self._prev_battle_lkwg_for_bloodline = None  # 上一帧的战斗状态（用于检测战斗结束过渡）
        
        
        # 启动时截图
        self._capture_startup_screenshot()

        # 中心部件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部导航栏
        self.header = self._create_header()
        main_layout.addWidget(self.header)

        # 主体内容区（横向布局）
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 左侧边栏
        self.sidebar = self._create_sidebar()
        body_layout.addWidget(self.sidebar)

        # 中间堆栈（增加异色图鉴、精灵图鉴、孵蛋预测和设置视图）
        self.content_stack = QStackedWidget()
        self.select_view = self._create_select_view()
        self.detail_view = self._create_detail_view()
        self.pokedex_view = self._create_pokedex_view()  # 异色图鉴
        self.pokemon_pokedex = PokedexWidget()  # 精灵图鉴
        self.egg_prediction_view = self._create_egg_prediction_view()  # 孵蛋预测
        self.ball_calculator_view = self._create_ball_calculator_view()  # 咕噜球计算
        self.settings_view = self._create_settings_view()  # 设置页面
        self.damage_calculator_view = DamageCalculatorWidget()  # 伤害计算器
        self.type_effectiveness_view = TypeEffectivenessWidget()  # 属性克制表
        # 路线相关属性（需要在 _create_map_view 之前初始化）
        self.route_color = QColor(34, 197, 94, 255)  # 路线颜色
        self.saved_routes = []  # 保存的路线列表: [{"name": str, "segments": list, "color": str}, ...]
        self._current_route_name = "未命名路线"  # 当前路线名称
        # 路线自由变换模式
        self.route_transform_active = False
        self.route_transform_route_index = -1
        self.route_transform_original = None  # 变换前原始 segments（ESC 恢复用）
        self.route_transform_action = None  # 'move' / 'scale' / 'rotate' / None
        self.route_transform_press_pos = None  # 鼠标按下位置（屏幕坐标）
        self.route_transform_start_segments = None  # 本次变换开始时的 segments
        self.route_transform_bbox = None  # 包围盒 (min_x, min_y, max_x, max_y) 地图世界坐标
        self.route_transform_panel = None  # 右侧参数面板 QFrame
        self.map_view = self._create_map_view()  # 地图
        self.shiny_records_view = self._create_shiny_records_view()  # 出闪记录
        self.home_view = HomeView()  # 家园系统
        self.content_stack.addWidget(self.select_view)   # 0
        self.content_stack.addWidget(self.detail_view)   # 1
        self.content_stack.addWidget(self.pokedex_view)  # 2
        self.content_stack.addWidget(self.pokemon_pokedex)  # 3 - 精灵图鉴
        self.content_stack.addWidget(self.egg_prediction_view)  # 4 - 孵蛋预测
        self.content_stack.addWidget(self.ball_calculator_view)  # 5 - 咕噜球计算
        self.content_stack.addWidget(self.settings_view) # 6
        self.content_stack.addWidget(self.damage_calculator_view)  # 7 - 伤害计算器
        self.content_stack.addWidget(self.type_effectiveness_view)  # 8 - 属性克制表
        self.content_stack.addWidget(self.map_view)  # 9 - 地图
        self.content_stack.addWidget(self.shiny_records_view)  # 10 - 出闪记录
        self.content_stack.addWidget(self.home_view)  # 11 - 家园系统
        
        # 家园系统点击精灵 → 跳转到精灵图鉴详情
        self.home_view.pokemon_clicked.connect(self._on_home_pokemon_clicked)
        body_layout.addWidget(self.content_stack, stretch=1)

        # 右侧面板
        self.right_panel = self._create_right_panel()
        body_layout.addWidget(self.right_panel)

        main_layout.addWidget(body, stretch=1)

        # 初始加载数据
        self._load_initial_data()
        
        # 同步童话事件提示计数
        active_counter = self.manager.get_active()
        if hasattr(self, 'game_capture') and self.game_capture and active_counter:
            self.game_capture.set_nightmare_count(active_counter.nightmare_count)
        
        self._refresh_all()
        
        # 加载设置到UI
        self.load_settings_to_ui()
        
        # 启动桌宠（延后到事件循环启动后，避免 QMovie 在 exec() 前初始化异常）
        if self.settings_manager.get("desktop_pet_enabled", False):
            QTimer.singleShot(0, lambda: toggle_pet(True))
        
        # 应用UI缩放
        self.apply_ui_scale()
        
        # 创建悬浮窗实例
        self.floating_window = FloatingWindow(self)
        self.floating_window.count_changed.connect(self.modify_count)
        self.floating_window.nightmare_count_changed.connect(self._on_floating_nightmare_adjust)
        self.floating_window.breakthrough_count_changed.connect(self._on_floating_breakthrough_adjust)
        self.floating_window.counter_navigate.connect(self._on_counter_navigate)
        
        # 应用悬浮窗大小设置
        size_key = self.settings_manager.get("floating_window_size", "medium")
        self.floating_window.set_size(size_key)
        
        # 应用悬浮窗透明度设置
        opacity = self.settings_manager.get("floating_window_opacity", 0.7)
        self.floating_window.normal_opacity = opacity
        self.floating_window.setWindowOpacity(opacity)
        
        # 初始化性能监控面板显示状态
        self.floating_window.set_performance_monitor_visible(
            self.settings_manager.get("show_performance_monitor", False)
        )
        self.floating_window.set_performance_charts_visible(
            self.settings_manager.get("show_performance_charts", True)
        )
        
        # 启动自动识别联动
        self.start_auto_recognition()

        # 初始化系统托盘（用于关闭时最小化到托盘）
        self._init_tray_icon()

        # 启动 3 秒后静默检查更新（不弹"无更新"提示，仅在有新版本时弹窗）
        QTimer.singleShot(3000, self._silent_check_update)

    # ─── 系统托盘 ────────────────────────────────────────

    def _init_tray_icon(self):
        """初始化系统托盘图标"""
        self._tray_icon = QSystemTrayIcon(self)
        icon_path = os.path.join(self._base_dir, "image", "tb", "klxy.png")
        if os.path.exists(icon_path):
            self._tray_icon.setIcon(QIcon(icon_path))
        else:
            self._tray_icon.setIcon(QIcon.fromTheme("application-exit"))
        self._tray_icon.setToolTip("可丽希亚助手")

        # 托盘右键菜单
        tray_menu = QMenu(self)
        show_action = tray_menu.addAction("显示窗口")
        show_action.triggered.connect(self._show_from_tray)
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self._quit_app)
        self._tray_icon.setContextMenu(tray_menu)

        # 双击托盘图标显示窗口
        self._tray_icon.activated.connect(self._on_tray_activated)

    def _show_from_tray(self):
        """从托盘恢复窗口"""
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        """托盘图标点击事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_from_tray()

    def _quit_app(self):
        """从托盘退出程序（真正退出）"""
        self._tray_icon.hide()
        self.settings_manager.set("minimize_to_tray", False)  # 临时禁用，让 closeEvent 真正关闭
        self.close()

    def apply_ui_scale(self):
        """应用UI缩放设置"""
        scale_key = self.settings_manager.get("ui_scale", "large")
        scale_sizes = {
            "small": (1280, 750),
            "medium": (1550, 850),
            "large": (1800, 950)
        }
        width, height = scale_sizes.get(scale_key, (1800, 950))
        self.setMinimumSize(800, 600)  # 确保可以缩小的最小尺寸
        self.resize(width, height)
        self.update()  # 强制刷新窗口
    
    def enter_floating_mode(self):
        """进入抓宠模式（显示悬浮窗）"""
        active = self.manager.get_active()
        if not active:
            QMessageBox.warning(self, "警告", "请先选择一个计数器")
            return
        
        # 查找对应的自定义精灵数据，获取icon_id
        custom_pokemons = self.manager.get_custom_pokemons()
        # 优先使用计数器自带的icon_id
        icon_id = active.icon_id if hasattr(active, 'icon_id') else 0
        
        # 如果icon_id为0，尝试从custom_pokemons中查找
        if icon_id == 0:
            custom_pokemons = self.manager.get_custom_pokemons()
            for cp in custom_pokemons:
                if cp['name'] == active.pokemon_name:
                    icon_id = cp.get('icon_id', 0)
                    break
        
        # 隐藏主窗口，显示悬浮窗
        self.hide()
        self.floating_window.update_data(
            active.pokemon_name,
            active.type,
            active.count,
            active.target,
            active.is_locked,
            active.nightmare_count,
            icon_id
        )
        self.floating_window.show()
    
    def toggle_recognition(self):
        """切换识别开关"""
        if self._recognition_enabled:
            # 关闭识别
            self._stop_recognition()
            self.recognition_toggle_btn.setText("▶️ 开启识别")
            self.recognition_toggle_btn.setStyleSheet("""
                QPushButton#floatingModeBtn {
                    background-color: rgba(34, 197, 94, 0.2);
                    border: 1px solid rgba(34, 197, 94, 0.4);
                    border-radius: 8px;
                    color: #22c55e;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 0 12px;
                }
                QPushButton#floatingModeBtn:hover {
                    background-color: rgba(34, 197, 94, 0.3);
                    border: 1px solid rgba(34, 197, 94, 0.6);
                }
            """)
            logger.log("⏸️ 已暂停自动识别")
        else:
            # 开启识别
            self._start_recognition()
            self.recognition_toggle_btn.setText("⏸️ 暂停识别")
            self.recognition_toggle_btn.setStyleSheet("""
                QPushButton#floatingModeBtn {
                    background-color: rgba(239, 68, 68, 0.2);
                    border: 1px solid rgba(239, 68, 68, 0.4);
                    border-radius: 8px;
                    color: #ef4444;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 0 12px;
                }
                QPushButton#floatingModeBtn:hover {
                    background-color: rgba(239, 68, 68, 0.3);
                    border: 1px solid rgba(239, 68, 68, 0.6);
                }
            """)
            logger.log("▶️ 已开启自动识别")
        
        self._recognition_enabled = not self._recognition_enabled
    
    def _stop_recognition(self):
        """停止识别"""
        # 停止定时器
        if hasattr(self, 'recognition_timer') and self.recognition_timer is not None:
            self.recognition_timer.stop()
        
        # 停止截图工作线程
        if hasattr(self, 'screenshot_worker') and self.screenshot_worker is not None:
            self.screenshot_worker.stop()
            self.screenshot_worker = None
        
        # 停止ROI工作线程
        if hasattr(self, 'roi_worker') and self.roi_worker is not None:
            self.roi_worker.is_running = False
            self.roi_worker = None
        
        # 停止nightmare工作线程
        if hasattr(self, 'nightmare_worker') and self.nightmare_worker is not None:
            self.nightmare_worker.stop()
            self.nightmare_worker = None
        
        
    
    def _start_recognition(self):
        """启动识别"""
        # 重新启动识别系统
        self.start_auto_recognition()
    
    def closeEvent(self, event):
        """窗口关闭时：若开启最小化到托盘则隐藏，否则真正退出"""
        # 检查是否开启最小化到托盘
        if self.settings_manager.get("minimize_to_tray", False):
            # 最小化到托盘（不真正关闭）
            self.hide()
            self._tray_icon.show()
            # 先保存数据
            try:
                self.manager.save_counters()
            except Exception as e:
                print(f"❌ 保存数据失败: {e}")
            event.ignore()
            print("⇲ 已最小化到系统托盘")
            return

        # 真正退出：清理资源
        self._tray_icon.hide()
        try:
            # 先关闭悬浮窗（清理 QProcess，避免 Destroyed while running 警告）
            if hasattr(self, 'floating_window') and self.floating_window is not None:
                self.floating_window.close()
                self.floating_window = None
            
            # 关闭桌宠
            from zc.desktop_pet import stop_pet
            stop_pet()
            
            # 停止自动识别
            if hasattr(self, 'recognition_timer'):
                self.recognition_timer.stop()
            if hasattr(self, 'screenshot_worker') and self.screenshot_worker is not None:
                self.screenshot_worker.stop()
            if hasattr(self, 'nightmare_worker') and self.nightmare_worker is not None:
                self.nightmare_worker.stop()
            # 停止游戏窗口预览定时器
            if hasattr(self, 'window_preview_timer'):
                self.window_preview_timer.stop()
            
            
            self.manager.save_counters()
            print("✓ 数据已保存")
        except Exception as e:
            print(f"❌ 保存数据失败: {e}")
        event.accept()
    
    def start_auto_recognition(self):
        """启动自动识别联动"""
        # 检查是否启用坐标识别模式
        use_roi = self.settings_manager.get("enable_roi_recognition", False)
        
        if use_roi:
            # 使用坐标识别模式
            from core.roi_recognition import RoiRecognitionWorker
            print("🎯 启动坐标识别模式")
            
            self.roi_worker = RoiRecognitionWorker()
            self.roi_worker.recognition_result.connect(self._on_recognition_result)
            self.roi_worker.status_changed.connect(self._on_roi_status_changed)
            self.roi_worker.start()
            
            # 初始化nightmare独立检测线程(低频2秒一次)
            from core.game_capture import NightmareWorker
            self.nightmare_worker = NightmareWorker(self.game_capture, self)
            self.nightmare_worker.nightmare_result.connect(self._on_nightmare_result)
            self.nightmare_worker.start()
        else:
            # 使用默认ROI识别模式
            from core.game_capture import ScreenshotWorker, NightmareWorker
            print("🔍 启动默认识别模式")
            
            self.screenshot_worker = ScreenshotWorker(self.game_capture, self)
            self.screenshot_worker.recognition_result.connect(self._on_recognition_result)
            self.screenshot_worker.start()
            
            # 初始化nightmare独立检测线程(低频2秒一次)
            self.nightmare_worker = NightmareWorker(self.game_capture, self)
            self.nightmare_worker.nightmare_result.connect(self._on_nightmare_result)
            self.nightmare_worker.start()
            
            
            
            # 主识别定时器：使用设置中的间隔
            self.recognition_timer = QTimer(self)
            self.recognition_timer.timeout.connect(self._request_screenshot)
            interval = self.settings_manager.get("recognition_interval", 500)
            self.recognition_timer.start(interval)
        
        print("✓ 自动识别联动已启动")
    
    def _request_screenshot(self):
        """请求截图和识别（非阻塞）"""
        self.screenshot_worker.capture_async()
    
    def _on_roi_status_changed(self, status):
        """接收ROI识别状态变化"""
        logger.log(status)

    def _on_opacity_changed(self, value):
        """悬浮窗透明度滑条变化时实时更新悬浮窗"""
        opacity = value / 100.0
        if hasattr(self, 'floating_window') and self.floating_window is not None:
            self.floating_window.normal_opacity = opacity
            if not self.floating_window.interactive_mode:
                self.floating_window.setWindowOpacity(opacity)
        self.settings_manager.set("floating_window_opacity", opacity)

    def _on_change_hotkey(self, hk_id):
        """打开热键捕获对话框，更改指定热键"""
        current_hotkeys = self.settings_manager.get("hotkeys", {})
        current_config = current_hotkeys.get(hk_id, {})
        current_label = current_config.get("display", hk_id)

        dialog = KeyCaptureDialog(current_label, self)
        if dialog.exec() == QDialog.Accepted and dialog._captured:
            new_config = dialog._captured
            current_hotkeys[hk_id] = new_config
            self.settings_manager.set("hotkeys", current_hotkeys)
            self.settings_manager.save_settings()

            if hk_id in self.hotkey_labels:
                self.hotkey_labels[hk_id].setText(new_config["display"])

            if hasattr(self, 'floating_window') and self.floating_window is not None:
                self.floating_window._unregister_hotkeys()
                self.floating_window._register_hotkey()
                logger.log(f"⌨️ 热键已更新: {hk_id} → {new_config['display']}")
            if hasattr(self, '_map_floating_window') and self._map_floating_window is not None:
                self._map_floating_window._unregister_hotkeys()
                self._map_floating_window._register_hotkey()
    
    def _on_nightmare_result(self, result):
        """接收nightmare检测结果（在主线程执行）"""
        try:
            nightmare_detected = result['nightmare_detected']
            nightmare_count = result['nightmare_count']
            
            if nightmare_detected:
                active_counter = self.manager.get_active()
                if active_counter:
                    old_count = active_counter.nightmare_count
                    active_counter.nightmare_count = nightmare_count
                    
                    # 只在计数变化时保存和更新
                    if old_count != nightmare_count:
                        self.manager.save_counters()
                        
                        # 同步更新悬浮窗(使用update_data完整更新)
                        if hasattr(self, 'floating_window') and self.floating_window.isVisible():
                            icon_id = active_counter.icon_id if hasattr(active_counter, 'icon_id') else 0
                            try:
                                icon_id = int(icon_id)
                            except (ValueError, TypeError):
                                icon_id = 0
                            self.floating_window.update_data(
                                active_counter.pokemon_name,
                                active_counter.type,
                                active_counter.count,
                                active_counter.target,
                                active_counter.is_locked,
                                active_counter.nightmare_count,
                                icon_id
                            )
        except Exception as e:
            print(f"❌ 处理nightmare结果错误: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_floating_nightmare_adjust(self, delta):
        """处理悬浮窗快捷键调整的童话事件提示计数"""
        try:
            active_counter = self.manager.get_active()
            if not active_counter:
                return

            # 调整计数
            old_count = active_counter.nightmare_count
            active_counter.nightmare_count = max(0, old_count + delta)

            # 同步更新 game_capture 的 nightmare_detected_count
            # 防止下次自动检测时用旧值+1覆盖用户手动调整的值
            if hasattr(self, 'game_capture') and self.game_capture:
                self.game_capture.set_nightmare_count(active_counter.nightmare_count)

            # 保存并更新
            self.manager.save_counters()

            # 同步更新悬浮窗
            if hasattr(self, 'floating_window') and self.floating_window.isVisible():
                icon_id = active_counter.icon_id if hasattr(active_counter, 'icon_id') else 0
                try:
                    icon_id = int(icon_id)
                except (ValueError, TypeError):
                    icon_id = 0
                self.floating_window.update_data(
                    active_counter.pokemon_name,
                    active_counter.type,
                    active_counter.count,
                    active_counter.target,
                    active_counter.is_locked,
                    active_counter.nightmare_count,
                    icon_id
                )

            logger.log(f"🔧 手动调整童话事件提示: {old_count} -> {active_counter.nightmare_count} ({'+' if delta > 0 else ''}{delta})")
        except Exception as e:
            print(f"❌ 处理悬浮窗计数调整错误: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_floating_breakthrough_adjust(self, delta):
        """处理悬浮窗快捷键调整的童话事件计数（四叶草铅绘）"""
        try:
            active_counter = self.manager.get_active()
            if not active_counter:
                return
            
            # 调整计数
            old_count = active_counter.count
            active_counter.count = max(0, min(active_counter.target, old_count + delta))
            
            # 保存并更新
            self.manager.save_counters()
            
            # 同步更新悬浮窗
            if hasattr(self, 'floating_window') and self.floating_window.isVisible():
                icon_id = active_counter.icon_id if hasattr(active_counter, 'icon_id') else 0
                try:
                    icon_id = int(icon_id)
                except (ValueError, TypeError):
                    icon_id = 0
                self.floating_window.update_data(
                    active_counter.pokemon_name,
                    active_counter.type,
                    active_counter.count,
                    active_counter.target,
                    active_counter.is_locked,
                    active_counter.nightmare_count,
                    icon_id
                )
            
            logger.log(f"🔧 手动调整童话事件: {old_count} -> {active_counter.count} ({'+' if delta > 0 else ''}{delta})")
            
            # 同步刷新详情视图（计数模式）
            if self.content_stack.currentIndex() == 1:
                self._refresh_right_panel()
        except Exception as e:
            print(f"❌ 处理悬浮窗童话事件调整错误: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_counter_navigate(self, direction):
        """处理快捷键 [ ] 切换快捷计数器"""
        try:
            new_counter = self.manager.navigate_counter(direction)
            if new_counter and hasattr(self, 'floating_window') and self.floating_window.isVisible():
                icon_id = new_counter.icon_id if hasattr(new_counter, 'icon_id') else 0
                try:
                    icon_id = int(icon_id)
                except (ValueError, TypeError):
                    icon_id = 0
                self.floating_window.update_data(
                    new_counter.pokemon_name,
                    new_counter.type,
                    new_counter.count,
                    new_counter.target,
                    new_counter.is_locked,
                    new_counter.nightmare_count,
                    icon_id
                )
                self.floating_window.update_current_lkwg(self.current_battle_lkwg)
                # 同步童话事件提示计数
                if hasattr(self, 'game_capture') and self.game_capture:
                    self.game_capture.set_nightmare_count(new_counter.nightmare_count)
                self._refresh_all()
                logger.log(f"🔄 快捷键切换计数器: {new_counter.pokemon_name}")
        except Exception as e:
            print(f"❌ 切换计数器错误: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_performance_monitor_toggled(self, enabled):
        """性能监控开关 - 显示/隐藏悬浮窗性能面板"""
        if hasattr(self, 'floating_window') and self.floating_window is not None:
            self.floating_window.set_performance_monitor_visible(enabled)
            # 保存设置
            self.settings_manager.set("show_performance_monitor", enabled)
    
    def _on_performance_charts_toggled(self, enabled):
        """曲线图开关 - 显示/隐藏性能监控的曲线图部分"""
        if hasattr(self, 'floating_window') and self.floating_window is not None:
            self.floating_window.set_performance_charts_visible(enabled)
            self.settings_manager.set("show_performance_charts", enabled)
    
    def _on_recognition_result(self, result):
        """接收子线程的识别结果（在主线程执行）"""
        try:
            recognized_names = result['recognized_names']
            should_ocr = result.get('should_ocr', False)
            ocr_reason = result.get('ocr_reason', 'unknown')
            
            # 更新游戏状态指示器(窗口检测由capture_window负责)
            if hasattr(self, 'game_status_label'):
                current_hwnd = self.game_capture.hwnd != 0
                
                # 只在状态变化时输出日志
                if not hasattr(self, '_last_window_status'):
                    self._last_window_status = None
                
                if current_hwnd != self._last_window_status:
                    if current_hwnd:
                        logger.log(f"✅ 已检测到游戏窗口")
                    else:
                        logger.log(f"⚠️ 未检测到游戏窗口")
                    self._last_window_status = current_hwnd
                
                if current_hwnd:
                    self.game_status_label.setText("● 已检测到游戏")
                    self.game_status_label.setStyleSheet("""
                        QLabel {
                            color: #22c55e;
                            font-size: 13px;
                            font-weight: 500;
                            padding: 0 8px;
                        }
                    """)
                else:
                    self.game_status_label.setText("● 未检测到游戏")
                    self.game_status_label.setStyleSheet("""
                        QLabel {
                            color: #ef4444;
                            font-size: 13px;
                            font-weight: 500;
                            padding: 0 8px;
                        }
                    """)
            
            # 刷新调试日志(从缓冲区读取子线程产生的日志)
            if hasattr(self, 'debug_window') and self.debug_window is not None and self.debug_window.isVisible():
                self._refresh_debug_log()
            
            # 输出OCR状态日志
            if should_ocr:
                logger.log(f"📸 OCR启用 [{ocr_reason}]: 识别到{len(recognized_names)}个名称")
            else:
                logger.log(f"📸 OCR禁用 [{ocr_reason}]")
            
            if recognized_names:
                logger.log(f"📝 OCR识别到: {', '.join(recognized_names)}")
                # 有有效识别，更新OCR状态
                self.game_capture.update_ocr_state(has_valid_recognition=True, recognized_names=recognized_names)
            
            # 处理识别结果 - 新逻辑：基于“四叶草铅绘”和精灵名字的战斗流程
            if "四叶草铅绘" in recognized_names:
                # 检测到四叶草铅绘，标记为进入战斗
                old_battle = self.current_battle_lkwg
                self.current_battle_lkwg = "四叶草铅绘"
                self._update_floating_current_lkwg("四叶草铅绘")

                

                # 同步状态到子线程
                if hasattr(self, 'screenshot_worker') and self.screenshot_worker is not None:
                    self.screenshot_worker.current_battle_lkwg = "四叶草铅绘"
                
                # 同步状态到ROI worker
                if hasattr(self, 'roi_worker') and self.roi_worker is not None:
                    self.roi_worker.set_current_battle("四叶草铅绘")
                
                if old_battle != "四叶草铅绘":
                    logger.log(f"✅ 检测到四叶草铅绘，进入战斗")
                    # 激活血脉识别检查（配合童话事件使用）
                    bl_enabled = self.settings_manager.get("enable_bloodline_recognition", False)
                    bl_roi = self.settings_manager.get("bloodline_roi")
                    if bl_enabled and bl_roi:
                        self._set_bloodline_check_active(True)
                
                # 触发童话事件计数（原污染击破）
                active_counter = self.manager.get_active()
                if active_counter:
                    # 防重复计数：只有当前战斗未计数时才触发
                    if not self._breakthrough_counted_for_current_battle:
                        self._trigger_lkwg_breakthrough(active_counter)
                        self._breakthrough_counted_for_current_battle = True
                        logger.log(f"✓ 童话事件: {active_counter.pokemon_name} | 计数: {active_counter.count}/{active_counter.target}")
                    else:
                        logger.log(f"⏭️ 跳过重复计数: {active_counter.pokemon_name}")
            elif recognized_names:
                # 识别到其他精灵名字（四叶草铅绘消失后）
                for base_name in recognized_names:
                    if base_name in self.game_capture.evolution_manager.evolution_chains and base_name != "四叶草铅绘":
                        # 保持战斗状态，显示精灵名
                        old_battle = self.current_battle_lkwg
                        self.current_battle_lkwg = base_name
                        self._update_floating_current_lkwg(base_name)
                        
                        # 同步状态到子线程
                        if hasattr(self, 'screenshot_worker') and self.screenshot_worker is not None:
                            self.screenshot_worker.current_battle_lkwg = base_name
                        
                        # 同步状态到ROI worker
                        if hasattr(self, 'roi_worker') and self.roi_worker is not None:
                            self.roi_worker.set_current_battle(base_name)
                        
                        # 记录童话事件期间出现的精灵
                        active_counter = self.manager.get_active()
                        if active_counter and self.current_battle_lkwg == "四叶草铅绘" or old_battle == "四叶草铅绘":
                            # 在童话事件期间，记录出现的精灵
                            if base_name not in active_counter.battle_pokemon_stats:
                                active_counter.battle_pokemon_stats[base_name] = 0
                            active_counter.battle_pokemon_stats[base_name] += 1

                        if old_battle != base_name:
                            logger.log(f"✅ 设置当前精灵: {base_name}")
                        break
            else:
                # 没有识别到任何名字时，检查是否需要清空状态
                if self.current_battle_lkwg:
                    # 区分“四叶草铅绘”和“精灵名字”两种情况
                    if self.current_battle_lkwg == "四叶草铅绘":
                        # 四叶草铅绘消失，进入6秒等待期
                        if not should_ocr and ocr_reason == "timeout":
                            logger.log(f"⏱️ OCR超时，四叶草铅绘消失后未检测到精灵，判定战斗结束")
                            self.current_battle_lkwg = None
                            self._update_floating_current_lkwg(None)
                            
                            # 同步状态到子线程
                            if hasattr(self, 'screenshot_worker') and self.screenshot_worker is not None:
                                self.screenshot_worker.current_battle_lkwg = None
                            
                            # 同步状态到ROI worker
                            if hasattr(self, 'roi_worker') and self.roi_worker is not None:
                                self.roi_worker.set_current_battle(None)
                            
                            # 重置防重复计数标记(战斗结束)
                            self._breakthrough_counted_for_current_battle = False
                            
                            # 重置OCR状态（允许下次nl触发）
                            if hasattr(self, 'game_capture'):
                                self.game_capture.ocr_enabled = False  # 立即关闭OCR
                                self.game_capture.battle_started = False
                                self.game_capture.nl_was_detected = False
                                self.game_capture.nl_detection_failed = False
                                self.game_capture.nl_trigger_time = 0
                                self.game_capture.battle_start_time = 0
                                self.game_capture.last_valid_recognition_time = 0
                        else:
                            # OCR仍启用，继续等待精灵名字出现（6秒空窗期）
                            pass
                            
                    else:
                        # 精灵名字消失，立即判定战斗结束（不等待）
                        logger.log(f"✅ 精灵名字消失，立即判定战斗结束: {self.current_battle_lkwg}")
                        self.current_battle_lkwg = None
                        self._update_floating_current_lkwg(None)
                        
                        # 同步状态到子线程
                        if hasattr(self, 'screenshot_worker') and self.screenshot_worker is not None:
                            self.screenshot_worker.current_battle_lkwg = None
                        
                        # 同步状态到ROI worker
                        if hasattr(self, 'roi_worker') and self.roi_worker is not None:
                            self.roi_worker.set_current_battle(None)
                        
                        # 重置防重复计数标记(战斗结束)
                        self._breakthrough_counted_for_current_battle = False
                        
                        # 重置OCR状态（允许下次nl触发）
                        if hasattr(self, 'game_capture'):
                            self.game_capture.ocr_enabled = False  # 立即关闭OCR
                            self.game_capture.battle_started = False
                            self.game_capture.nl_was_detected = False
                            self.game_capture.nl_detection_failed = False
                            self.game_capture.nl_trigger_time = 0
                            self.game_capture.battle_start_time = 0
                            self.game_capture.last_valid_recognition_time = 0

            # 血脉识别结果处理
            # 逻辑：四叶草铅绘检测到时激活检查（但不开始计时）；
            #       四叶草铅绘消失后子线程开始OCR血脉区域，此时开始2秒计时；
            #       2秒内识别到 奇异/污染/混乱/异色 显示对应颜色并立即停止OCR；
            #       2秒超时未识别到关键字，显示"普通"并立即停止OCR；
            #       血脉显示会一直保留在悬浮窗上直到战斗结束。
            if self._bloodline_check_active:
                bl_checked = result.get('bloodline_checked', False)
                bl_type = result.get('bloodline') if bl_checked else None
                if bl_type:
                    # 识别到血脉关键字，显示对应颜色并立即停止OCR
                    if hasattr(self, 'floating_window') and self.floating_window is not None:
                        self.floating_window.update_bloodline(bl_type)
                    self._set_bloodline_check_active(False)
                elif bl_checked:
                    # 子线程执行了血脉OCR但未命中关键字
                    # 首次执行血脉OCR时开始计时
                    if self._bloodline_check_start_time == 0:
                        self._bloodline_check_start_time = time.time()
                        logger.log(f"🩸 四叶草铅绘消失，开始2秒血脉识别计时")
                    elapsed = time.time() - self._bloodline_check_start_time
                    if elapsed >= self._bloodline_check_timeout:
                        # 2秒超时，显示"普通"并立即停止OCR
                        if hasattr(self, 'floating_window') and self.floating_window is not None:
                            self.floating_window.update_bloodline("普通")
                        self._set_bloodline_check_active(False)

            # 战斗结束（current_battle_lkwg从非None变为None）时关闭血脉OCR并清空显示
            if not self.current_battle_lkwg and self._prev_battle_lkwg_for_bloodline is not None:
                if self._bloodline_check_active:
                    self._set_bloodline_check_active(False)
                # 清空悬浮窗血脉显示
                self._clear_bloodline_display()
            # 更新上一帧战斗状态
            self._prev_battle_lkwg_for_bloodline = self.current_battle_lkwg

            # 输出战斗状态日志
            if self.current_battle_lkwg:
                log_msg = f"🎯 当前状态: {self.current_battle_lkwg}"
                logger.log(log_msg)
            
        except Exception as e:
            print(f"❌ 处理识别结果错误: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_floating_current_lkwg(self, lkwg_name):
        """更新悬浮窗当前洛克王国精灵显示"""
        if hasattr(self, 'floating_window'):
            self.floating_window.update_current_lkwg(lkwg_name)

    def _set_bloodline_check_active(self, active):
        """同步血脉识别检查状态到子线程
        注意：关闭检查时不清空悬浮窗显示，血脉会一直显示直到战斗结束
        """
        if self._bloodline_check_active == active:
            return
        self._bloodline_check_active = active
        if active:
            # 激活时重置开始时间（等待四叶草铅绘消失后才开始计时）
            self._bloodline_check_start_time = 0
            # 激活新事件时清空上一次的血脉显示
            if hasattr(self, 'floating_window') and self.floating_window is not None:
                self.floating_window.update_bloodline(None)
        # 同步到ScreenshotWorker
        if hasattr(self, 'screenshot_worker') and self.screenshot_worker is not None:
            self.screenshot_worker.bloodline_check_active = active
        # 同步到RoiRecognitionWorker
        if hasattr(self, 'roi_worker') and self.roi_worker is not None:
            self.roi_worker.set_bloodline_check_active(active)

    def _clear_bloodline_display(self):
        """清空悬浮窗血脉显示（仅在战斗结束时调用）"""
        if hasattr(self, 'floating_window') and self.floating_window is not None:
            self.floating_window.update_bloodline(None)

    
    
    def _refresh_debug_log(self):
        """刷新调试日志(从缓冲区读取子线程产生的日志)"""
        if not hasattr(self, 'debug_window') or not self.debug_window.isVisible():
            return
        
        # 获取所有日志
        history = logger.get_buffer()
        if history:
            current_lines = self.debug_window.log_text.toPlainText().split('\n')
            # 过滤空行
            current_lines = [line for line in current_lines if line.strip()]
            
            # 只在有新日志时追加
            if len(history) > len(current_lines):
                new_logs = history[len(current_lines):]
                for log_entry in new_logs:
                    self.debug_window.log_text.append(log_entry)
                
                # 自动滚动到底部（如果启用）
                if self.debug_window.auto_scroll_enabled:
                    scrollbar = self.debug_window.log_text.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum())
    
    def _restart_recognition(self):
        """重启识别系统（切换识别模式）"""
        print("🔄 正在重启识别系统...")
        
        # 停止当前识别
        if hasattr(self, 'recognition_timer') and self.recognition_timer is not None:
            self.recognition_timer.stop()
            self.recognition_timer = None
        
        if hasattr(self, 'screenshot_worker') and self.screenshot_worker is not None:
            self.screenshot_worker.stop()
            self.screenshot_worker = None
        
        if hasattr(self, 'roi_worker') and self.roi_worker is not None:
            self.roi_worker.is_running = False
            self.roi_worker = None
        
        if hasattr(self, 'nightmare_worker') and self.nightmare_worker is not None:
            self.nightmare_worker.stop()
            self.nightmare_worker = None
        
        # 重新启动识别
        import time
        time.sleep(0.5)  # 等待线程完全停止
        self.start_auto_recognition()
        print("✅ 识别系统已重启")
    
    def _emergency_restart_all(self):
        """异常重启 - 诊断所有模块状态，强制重启全部模块，清除系统缓存"""
        logger.log("=" * 40)
        logger.log("🔴 开始异常重启流程...")
        
        import time
        import gc
        
        # 第一步：诊断所有模块状态
        logger.log("📋 正在诊断模块状态...")
        diagnosis = []
        
        # 诊断识别定时器
        timer_ok = hasattr(self, 'recognition_timer') and self.recognition_timer is not None
        timer_active = timer_ok and self.recognition_timer.isActive()
        diagnosis.append(("识别定时器", "正常" if timer_active else ("停止" if timer_ok else "缺失")))
        
        # 诊断截图工作线程
        worker_ok = hasattr(self, 'screenshot_worker') and self.screenshot_worker is not None
        worker_alive = worker_ok and self.screenshot_worker.isRunning()
        diagnosis.append(("截图工作线程", "存活" if worker_alive else ("已停止" if worker_ok else "缺失")))
        
        # 诊断ROI工作线程
        roi_ok = hasattr(self, 'roi_worker') and self.roi_worker is not None
        diagnosis.append(("ROI识别线程", "存在" if roi_ok else "未创建"))
        
        # 诊断噩梦工作线程
        nightmare_ok = hasattr(self, 'nightmare_worker') and self.nightmare_worker is not None
        diagnosis.append(("噩梦检测线程", "存在" if nightmare_ok else "未创建"))
        
        
        
        # 诊断OCR状态机
        ocr_state = "未知"
        if hasattr(self, 'game_capture'):
            cap = self.game_capture
            ocr_state = f"ocr_enabled={cap.ocr_enabled}, nl_was_detected={cap.nl_was_detected}"
        diagnosis.append(("OCR状态机", ocr_state))
        
        # 输出诊断结果
        for name, status in diagnosis:
            logger.log(f"  - {name}: {status}")
        
        # 第二步：强制停止所有模块
        logger.log("🛑 正在强制停止所有模块...")
        
        if hasattr(self, 'recognition_timer') and self.recognition_timer is not None:
            try:
                self.recognition_timer.stop()
                logger.log("  ✅ 识别定时器已停止")
            except Exception as e:
                logger.log(f"  ⚠️ 识别定时器停止异常: {e}")
            self.recognition_timer = None
        
        if hasattr(self, 'screenshot_worker') and self.screenshot_worker is not None:
            try:
                self.screenshot_worker.stop()
                logger.log("  ✅ 截图工作线程已停止")
            except Exception as e:
                logger.log(f"  ⚠️ 截图工作线程停止异常: {e}")
            self.screenshot_worker = None
        
        if hasattr(self, 'roi_worker') and self.roi_worker is not None:
            try:
                self.roi_worker.is_running = False
                logger.log("  ✅ ROI工作线程已停止")
            except Exception as e:
                logger.log(f"  ⚠️ ROI工作线程停止异常: {e}")
            self.roi_worker = None
        
        if hasattr(self, 'nightmare_worker') and self.nightmare_worker is not None:
            try:
                self.nightmare_worker.stop()
                logger.log("  ✅ 噩梦检测线程已停止")
            except Exception as e:
                logger.log(f"  ⚠️ 噩梦检测线程停止异常: {e}")
                self.nightmare_worker.quit()
                self.nightmare_worker.wait(2000)
            self.nightmare_worker = None
        
        
        
        # 第三步：清除系统缓存
        logger.log("🧹 正在清除系统缓存...")
        try:
            if hasattr(self, 'game_capture') and self.game_capture is not None:
                game_cap = self.game_capture
                game_cap.ocr_enabled = False
                game_cap.nl_was_detected = False
                game_cap.nl_detection_failed = False
                game_cap.battle_started = False
                game_cap.nl_trigger_time = 0
                game_cap.battle_start_time = 0
                game_cap.last_valid_recognition_time = 0
                if hasattr(game_cap, '_nl_fail_time'):
                    game_cap._nl_fail_time = 0
                if hasattr(game_cap, 'template_cache'):
                    game_cap.template_cache.clear()
                if hasattr(game_cap, 'ocr_cache_ref'):
                    game_cap.ocr_cache_ref = None
                logger.log("  ✅ game_capture 状态已重置")
            
            # 清理Python垃圾回收
            gc.collect()
            logger.log("  ✅ Python内存缓存已清理")
        except Exception as e:
            logger.log(f"  ⚠️ 缓存清理异常: {e}")
        
        time.sleep(0.5)
        
        # 第三步半：重启性能监控持久进程（PowerShell / PresentMon）
        try:
            if (hasattr(self, 'floating_window') and self.floating_window is not None
                    and hasattr(self.floating_window, 'performance_monitor')):
                self.floating_window.performance_monitor.restart_all_perf()
                logger.log("  ✅ 性能监控进程已重启")
        except Exception as e:
            logger.log(f"  ⚠️ 性能监控重启异常: {e}")
        
        # 第四步：重新启动识别系统
        logger.log("🚀 正在重新启动所有模块...")
        try:
            self.start_auto_recognition()
            logger.log("  ✅ 识别系统已重新启动")
        except Exception as e:
            logger.log(f"  ❌ 识别系统启动失败: {e}")
        
        logger.log("✅" + "=" * 38)
        logger.log("🔴 异常重启流程已完成")
        logger.log("=" * 40)
    
    def _find_counter_by_lkwg(self, lkwg_name):
        """根据洛克王国精灵名称查找对应的计数器"""
        for counter in self.manager.counters:
            if counter.pokemon_name == lkwg_name:
                return counter
        return None
    
    def _trigger_lkwg_breakthrough(self, counter):
        """触发洛克王国精灵童话事件（原污染击破）"""
        counter.count += 1  # 童话事件次数+1
        
        # 检查是否需要自动保存（基于时间间隔）
        auto_save_interval = self.settings_manager.get("auto_save_interval", 5)
        if self.settings_manager.get("auto_save_progress", True):
            if self.manager.should_auto_save(counter.id, auto_save_interval):
                self.manager.save_counters()
                self.manager.update_save_time(counter.id)
        
        # 检查是否达到保底，发送通知
        # 只有等于保底次数且未通知过时才弹窗
        if counter.count == counter.target and not counter.breakthrough_notified:
            if self.settings_manager.get("breakthrough_notification", True):
                self._show_breakthrough_notification(counter)
                counter.breakthrough_notified = True
        
        # 保存数据并刷新界面
        self.counter_changed.emit()
        self._refresh_all()
        
        # 同步更新悬浮窗
        if hasattr(self, 'floating_window') and self.floating_window.isVisible():
            icon_id = counter.icon_id if hasattr(counter, 'icon_id') else 0
            # 确保icon_id是整数类型
            try:
                icon_id = int(icon_id)
            except (ValueError, TypeError):
                icon_id = 0
            self.floating_window.update_data(
                counter.pokemon_name,
                counter.type,
                counter.count,
                counter.target,
                counter.is_locked,
                counter.nightmare_count,
                icon_id
            )
    
    def _show_breakthrough_notification(self, counter):
        """显示保底通知"""
        try:
            from plyer import notification
            notification.notify(
                title="🎉 保底达成！",
                message=f"【{counter.pokemon_name}】已达到保底次数！\n当前击破：{counter.count}/80",
                app_name="可丽希娅助手",
                timeout=10
            )
        except Exception as e:
            print(f"通知发送失败: {e}")
            # 如果plyer不可用，使用QMessageBox作为备选
            QMessageBox.information(
                self,
                "🎉 保底达成！",
                f"【{counter.pokemon_name}】已达到保底次数！\n当前击破：{counter.count}/80"
            )
    
    def modify_count(self, delta):
        """修改计数器数值(由悬浮窗调用)"""
        active = self.manager.get_active()
        if active and not active.is_locked:
            active.count = max(0, min(active.target, active.count + delta))
            self.manager.save_counters()
            self._refresh_all()
    
    def _capture_startup_screenshot(self):
        """启动时截取游戏画面"""
        try:
            # 延迟1秒确保窗口已完全显示
            QTimer.singleShot(1000, self._do_capture_screenshot)
        except:
            pass
    
    def _do_capture_screenshot(self):
        """执行截图"""
        if not self.game_capture.find_window():
            print("警告：未找到游戏窗口，跳过截图")
            return
        
        image = self.game_capture.capture_window()
        if image is not None:
            image_dir = os.path.join(self._base_dir, "image")
            os.makedirs(image_dir, exist_ok=True)
            screenshot_path = os.path.join(image_dir, "startup_screenshot.png")
            _imwrite(screenshot_path, image)
            print(f"✓ 启动截图已保存: {screenshot_path}")
        else:
            print("警告：截图失败")

    # ================= 顶部导航栏 =================
    def _create_header(self):
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(60)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(0)

        # 左侧区域（Logo + 副标题）
        left_section = QWidget()
        left_layout = QHBoxLayout(left_section)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        logo_icon = QLabel()
        logo_icon.setFixedSize(36, 36)
        logo_icon.setAlignment(Qt.AlignCenter)
        
        # 加载klxy.png图片
        image_dir = os.path.join(self._base_dir, "image", "tb")
        image_path = os.path.join(image_dir, "klxy.png")
        
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo_icon.setPixmap(scaled_pixmap)
                logo_icon.setStyleSheet("background: transparent;")
            else:
                # 图片加载失败，使用默认样式
                logo_icon.setText("💎")
                logo_icon.setStyleSheet("""
                    font-size: 24px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #c77dff, stop:1 #9d4edd);
                    border-radius: 8px;
                    padding: 4px;
                    color: white;
                """)
        else:
            # 图片不存在，使用默认样式
            logo_icon.setText("💎")
            logo_icon.setStyleSheet("""
                font-size: 24px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #c77dff, stop:1 #9d4edd);
                border-radius: 8px;
                padding: 4px;
                color: white;
            """)
        left_layout.addWidget(logo_icon)

        title_section = QWidget()
        title_layout = QVBoxLayout(title_section)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)

        main_title = QLabel("洛克王国世界多模态工具")
        main_title.setStyleSheet("color: #f8f0ff; font-weight: 600; font-size: 14px;")
        title_layout.addWidget(main_title)

        sub_title = QLabel("WEAK WORLD MULTIMODAL TOOL")
        sub_title.setStyleSheet("color: #c084fc; font-size: 9px; opacity: 0.7;")
        title_layout.addWidget(sub_title)

        left_layout.addWidget(title_section)
        left_layout.addStretch()
        
        layout.addWidget(left_section, stretch=1)

        # 中间大标题 - “可丽希亚助手”居中最上面
        center_title = QLabel("可丽希亚助手")
        center_title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #ffffff;
            padding: 5px 15px;
        """)
        center_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(center_title, stretch=1)

        # 右侧按钮组（对称布局）
        right_section = QWidget()
        right_layout = QHBoxLayout(right_section)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        right_layout.addStretch()
        
        # 游戏状态指示器
        self.game_status_label = QLabel("● 未检测到游戏")
        self.game_status_label.setStyleSheet("""
            QLabel {
                color: #ef4444;
                font-size: 13px;
                font-weight: 500;
                padding: 0 8px;
            }
        """)
        right_layout.addWidget(self.game_status_label)

        # 识别开关
        self.recognition_toggle_btn = QPushButton("⏸️ 暂停识别")
        self.recognition_toggle_btn.setObjectName("floatingModeBtn")
        self.recognition_toggle_btn.setFixedHeight(34)
        self.recognition_toggle_btn.setFixedWidth(120)
        self.recognition_toggle_btn.clicked.connect(self.toggle_recognition)
        self._recognition_enabled = True  # 默认开启识别
        right_layout.addWidget(self.recognition_toggle_btn)

        btn_floating = QPushButton("🗖 进入抓宠模式")
        btn_floating.setObjectName("floatingModeBtn")
        btn_floating.setFixedHeight(34)
        btn_floating.clicked.connect(self.enter_floating_mode)
        right_layout.addWidget(btn_floating)

        btn_settings = QPushButton("应用设置 ▾")
        btn_settings.setObjectName("settingsBtn")
        btn_settings.setFixedHeight(34)
        btn_settings.clicked.connect(lambda: self._switch_nav_page(6, None, None))
        right_layout.addWidget(btn_settings)
        
        # 窗口控制按钮（最小化、最大化、关闭）
        window_controls = QWidget()
        window_controls_layout = QHBoxLayout(window_controls)
        window_controls_layout.setContentsMargins(0, 0, 0, 0)
        window_controls_layout.setSpacing(0)
        
        btn_minimize = QPushButton("─")
        btn_minimize.setFixedSize(46, 32)
        btn_minimize.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        btn_minimize.clicked.connect(self.showMinimized)
        window_controls_layout.addWidget(btn_minimize)
        
        btn_maximize = QPushButton("□")
        btn_maximize.setFixedSize(46, 32)
        btn_maximize.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: none;
                font-size: 14px;
                padding-top: 2px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        btn_maximize.clicked.connect(self.toggle_maximize)
        window_controls_layout.addWidget(btn_maximize)
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(46, 32)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e81123;
            }
        """)
        btn_close.clicked.connect(self.close)
        window_controls_layout.addWidget(btn_close)
        
        right_layout.addWidget(window_controls)

        layout.addWidget(right_section, stretch=1)

        return header

    # ================= 侧边栏 =================
    def _create_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(280)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 分隔线（渐变设计）
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent,
                    stop:0.3 rgba(124, 58, 237, 0.3),
                    stop:0.7 rgba(124, 58, 237, 0.3),
                    stop:1 transparent);
                max-height: 2px;
                margin: 0 20px;
            }
        """)
        layout.addWidget(separator1)

        # 主导航菜单
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(12, 8, 12, 8)
        nav_layout.setSpacing(4)
        
        # 计数器导航项
        nav_counter = QPushButton("计数器")
        nav_counter.setObjectName("navItem")
        nav_counter.setProperty("active", True)
        nav_counter.setStyleSheet("""
            QPushButton#navItem {
                background-color: transparent;
                color: #71717a;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton#navItem:hover {
                background-color: rgba(124, 58, 237, 0.1);
                color: #a1a1aa;
            }
            QPushButton#navItem[active="true"] {
                background-color: rgba(124, 58, 237, 0.2);
                color: #a78bfa;
                font-weight: 600;
            }
        """)
        nav_counter.clicked.connect(lambda: self._switch_nav_page(0, nav_counter, None))
        nav_layout.addWidget(nav_counter)
        
        # 异色图鉴导航项
        nav_pokedex = QPushButton("异色图鉴")
        nav_pokedex.setObjectName("navItem")
        nav_pokedex.setProperty("active", False)
        nav_pokedex.setStyleSheet("""
            QPushButton#navItem {
                background-color: transparent;
                color: #71717a;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton#navItem:hover {
                background-color: rgba(124, 58, 237, 0.1);
                color: #a1a1aa;
            }
            QPushButton#navItem[active="true"] {
                background-color: rgba(124, 58, 237, 0.2);
                color: #a78bfa;
                font-weight: 600;
            }
        """)
        nav_pokedex.clicked.connect(lambda: self._switch_nav_page(2, nav_pokedex, None))
        nav_layout.addWidget(nav_pokedex)
        
        # 精灵图鉴导航项
        nav_pokemon_pokedex = QPushButton("精灵图鉴")
        nav_pokemon_pokedex.setObjectName("navItem")
        nav_pokemon_pokedex.setProperty("active", False)
        nav_pokemon_pokedex.setStyleSheet("""
            QPushButton#navItem {
                background-color: transparent;
                color: #71717a;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton#navItem:hover {
                background-color: rgba(124, 58, 237, 0.1);
                color: #a1a1aa;
            }
            QPushButton#navItem[active="true"] {
                background-color: rgba(124, 58, 237, 0.2);
                color: #a78bfa;
                font-weight: 600;
            }
        """)
        nav_pokemon_pokedex.clicked.connect(lambda: self._switch_nav_page(3, nav_pokemon_pokedex, None))
        nav_layout.addWidget(nav_pokemon_pokedex)
        
        # 伤害计算器导航项
        nav_damage = QPushButton("伤害计算器")
        nav_damage.setObjectName("navItem")
        nav_damage.setProperty("active", False)
        nav_damage.setStyleSheet("""
            QPushButton#navItem {
                background-color: transparent;
                color: #71717a;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton#navItem:hover {
                background-color: rgba(124, 58, 237, 0.1);
                color: #a1a1aa;
            }
            QPushButton#navItem[active="true"] {
                background-color: rgba(124, 58, 237, 0.2);
                color: #a78bfa;
                font-weight: 600;
            }
        """)
        nav_damage.clicked.connect(lambda: self._switch_nav_page(7, nav_damage, None, hide_right_panel=True))
        nav_layout.addWidget(nav_damage)
        
        # 属性克制表导航项
        nav_type_effectiveness = QPushButton("属性克制表")
        nav_type_effectiveness.setObjectName("navItem")
        nav_type_effectiveness.setProperty("active", False)
        nav_type_effectiveness.setStyleSheet("""
            QPushButton#navItem {
                background-color: transparent;
                color: #71717a;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton#navItem:hover {
                background-color: rgba(124, 58, 237, 0.1);
                color: #a1a1aa;
            }
            QPushButton#navItem[active="true"] {
                background-color: rgba(124, 58, 237, 0.2);
                color: #a78bfa;
                font-weight: 600;
            }
        """)
        nav_type_effectiveness.clicked.connect(lambda: self._switch_nav_page(8, nav_type_effectiveness, None, hide_right_panel=True))
        nav_layout.addWidget(nav_type_effectiveness)
        
        # 地图导航项
        nav_map = QPushButton("地图")
        nav_map.setObjectName("navItem")
        nav_map.setProperty("active", False)
        nav_map.setStyleSheet("""
            QPushButton#navItem {
                background-color: transparent;
                color: #71717a;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton#navItem:hover {
                background-color: rgba(124, 58, 237, 0.1);
                color: #a1a1aa;
            }
            QPushButton#navItem[active="true"] {
                background-color: rgba(124, 58, 237, 0.2);
                color: #a78bfa;
                font-weight: 600;
            }
        """)
        nav_map.clicked.connect(lambda: self._switch_nav_page(9, nav_map, None, hide_right_panel=True))
        nav_layout.addWidget(nav_map)
        
        # 孵蛋预测导航项
        nav_egg = QPushButton("孵蛋预测")
        nav_egg.setObjectName("navItem")
        nav_egg.setProperty("active", False)
        nav_egg.setStyleSheet("""
            QPushButton#navItem {
                background-color: transparent;
                color: #71717a;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton#navItem:hover {
                background-color: rgba(124, 58, 237, 0.1);
                color: #a1a1aa;
            }
            QPushButton#navItem[active="true"] {
                background-color: rgba(124, 58, 237, 0.2);
                color: #a78bfa;
                font-weight: 600;
            }
        """)
        nav_egg.clicked.connect(lambda: self._switch_nav_page(4, nav_egg, None))
        nav_layout.addWidget(nav_egg)
        
        # 家园导航项
        nav_home = QPushButton("家园")
        nav_home.setObjectName("navItem")
        nav_home.setProperty("active", False)
        nav_home.setStyleSheet("""
            QPushButton#navItem {
                background-color: transparent;
                color: #71717a;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton#navItem:hover {
                background-color: rgba(124, 58, 237, 0.1);
                color: #a1a1aa;
            }
            QPushButton#navItem[active="true"] {
                background-color: rgba(124, 58, 237, 0.2);
                color: #a78bfa;
                font-weight: 600;
            }
        """)
        nav_home.clicked.connect(lambda: self._switch_nav_page(11, nav_home, None, hide_right_panel=True))
        nav_layout.addWidget(nav_home)
        
        # 咕噜球计算导航项
        nav_ball = QPushButton("咕噜球计算")
        nav_ball.setObjectName("navItem")
        nav_ball.setProperty("active", False)
        nav_ball.setStyleSheet("""
            QPushButton#navItem {
                background-color: transparent;
                color: #71717a;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton#navItem:hover {
                background-color: rgba(124, 58, 237, 0.1);
                color: #a1a1aa;
            }
            QPushButton#navItem[active="true"] {
                background-color: rgba(124, 58, 237, 0.2);
                color: #a78bfa;
                font-weight: 600;
            }
        """)
        nav_ball.clicked.connect(lambda: self._switch_nav_page(5, None, None))
        nav_layout.addWidget(nav_ball)
        
        # 出闪记录导航项
        nav_shiny = QPushButton("出闪记录")
        nav_shiny.setObjectName("navItem")
        nav_shiny.setProperty("active", False)
        nav_shiny.setStyleSheet("""
            QPushButton#navItem {
                background-color: transparent;
                color: #71717a;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton#navItem:hover {
                background-color: rgba(124, 58, 237, 0.1);
                color: #a1a1aa;
            }
            QPushButton#navItem[active="true"] {
                background-color: rgba(124, 58, 237, 0.2);
                color: #a78bfa;
                font-weight: 600;
            }
        """)
        nav_shiny.clicked.connect(lambda: self._switch_nav_page(10, nav_shiny, None, hide_right_panel=False))
        nav_layout.addWidget(nav_shiny)
        
        layout.addWidget(nav_container)
        
        # 分隔线
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent,
                    stop:0.3 rgba(124, 58, 237, 0.2),
                    stop:0.7 rgba(124, 58, 237, 0.2),
                    stop:1 transparent);
                max-height: 1px;
                margin: 8px 20px;
            }
        """)
        layout.addWidget(separator2)

        # 标题栏（计数器 + 加号 + 折叠）
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 12, 16, 8)
        title_layout.setSpacing(10)

        title_label = QLabel("计数器")
        title_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # 折叠按钮 - 圆形+三角形
        self.btn_fold = FoldButton()
        self.btn_fold.setFixedSize(28, 28)
        self.btn_fold.setToolTip("折叠/展开列表")
        self.btn_fold.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(139, 92, 246, 0.15);
                border-radius: 14px;
            }
        """)
        self.btn_fold.clicked.connect(self.on_toggle_fold)
        title_layout.addWidget(self.btn_fold)

        # 新建按钮 - 圆形+十字镂空
        btn_add = AddButton()
        btn_add.setFixedSize(32, 32)
        btn_add.setToolTip("新建计数器")
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #8b5cf6, stop:0.5 #a855f7, stop:1 #c084fc);
                border: none;
                border-radius: 16px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #a78bfa, stop:0.5 #c084fc, stop:1 #e9d5ff);
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #7c3aed, stop:0.5 #9333ea, stop:1 #a855f7);
            }
        """)
        btn_add.clicked.connect(self.on_new_counter)
        title_layout.addWidget(btn_add)

        layout.addWidget(title_bar)

        # 计数器列表
        self.counter_list_widget = QListWidget()
        self.counter_list_widget.setObjectName("counterList")
        self.counter_list_widget.itemClicked.connect(self.on_counter_item_clicked)
        self.counter_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.counter_list_widget.customContextMenuRequested.connect(self.on_counter_context_menu)
        layout.addWidget(self.counter_list_widget)

        # 底部设置入口
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: rgba(157, 78, 221, 0.2); margin: 16px 12px 12px 12px;")
        layout.addWidget(separator)

        btn_settings_entry = QPushButton("⚙ 助手设置")
        btn_settings_entry.setObjectName("settingsEntry")
        btn_settings_entry.clicked.connect(lambda: self._switch_nav_page(6, None, None))
        layout.addWidget(btn_settings_entry)

        return sidebar

    # ================= 精灵选择视图 =================
    def _create_select_view(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 禁用水平滚动条
        scroll.setStyleSheet(SCROLL_BAR_STYLE)
        container = QWidget()
        container.setObjectName("mainContent")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 标题
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)

        title = QLabel("选择目标异色精灵")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f8f0ff;")
        title_layout.addWidget(title)

        hint = QLabel("点击精灵创建计数器")
        hint.setStyleSheet("color: #c084fc; font-size: 12px; margin-left: 8px;")
        title_layout.addWidget(hint)
        title_layout.addStretch()
        
        # 赛季选择
        season_label = QLabel("赛季：")
        season_label.setStyleSheet("color: #71717a; font-size: 14px;")
        title_layout.addWidget(season_label)
        
        self.counter_season_combo = TriangleComboBox()
        self.counter_season_combo.addItems(["第一赛季", "第二赛季", "第三赛季"])
        self.counter_season_combo.setCurrentText("第三赛季")
        self.counter_season_combo.setFixedWidth(120)
        self.counter_season_combo.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 6px 10px;
                color: #e4e4e7;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)
        self.counter_season_combo.currentTextChanged.connect(self._populate_pokemon_grid)
        title_layout.addWidget(self.counter_season_combo)

        layout.addWidget(title_bar)

        # 精灵卡片网格
        self.pokemon_grid = QWidget()
        self.grid_layout = QGridLayout(self.pokemon_grid)
        self.grid_layout.setSpacing(16)
        layout.addWidget(self.pokemon_grid, stretch=1)  # 让网格占据剩余空间

        # 自定义精灵按钮 - 放在底部
        btn_custom_container = QWidget()
        btn_custom_layout = QHBoxLayout(btn_custom_container)
        btn_custom_layout.setContentsMargins(0, 16, 0, 0)  # 顶部留白
        btn_custom_layout.setSpacing(12)
        
        btn_pokedex = QPushButton("异色图鉴")
        btn_pokedex.setObjectName("customPokemonBtn")
        btn_pokedex.clicked.connect(lambda: self.content_stack.setCurrentIndex(2))
        btn_custom_layout.addWidget(btn_pokedex)
        
        # 手动新建按钮
        btn_manual = QPushButton("✏️ 手动新建")
        btn_manual.setObjectName("customPokemonBtn")
        btn_manual.clicked.connect(self.on_custom_pokemon)
        btn_custom_layout.addWidget(btn_manual)
        
        layout.addWidget(btn_custom_container)

        scroll.setWidget(container)
        return scroll

    def _populate_pokemon_grid(self):
        """根据精灵列表动态生成卡片（只显示图鉴中的精灵，不显示自定义精灵）"""
        # 更新全局赛季设置
        from core.pokemon_data import set_current_season
        season = self.counter_season_combo.currentText() if hasattr(self, 'counter_season_combo') else "第三赛季"
        set_current_season(season)
        
        # 清空网格
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.takeAt(i).widget()
            if widget:
                widget.deleteLater()

        # 只加载图鉴数据库中的精灵，不加载自定义精灵（按赛季筛选）
        from core.pokemon_data import load_pokemon_database
        database_pokemons = load_pokemon_database(season)

        columns = 3
        row = 0
        col = 0
        for idx, pokemon in enumerate(database_pokemons):
            card = self._create_pokemon_card(pokemon)
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= columns:
                col = 0
                row += 1
        
        # 添加弹性空间
        self.grid_layout.setRowStretch(row + 1, 1)

    def _create_pokemon_card(self, pokemon):
        """单个精灵卡片（带阴影和悬停动效）"""
        card = QFrame()
        card.setObjectName("pokemonCard")
        card.setFixedSize(180, 200)  # 增加高度以容纳进度条
        card.setCursor(Qt.PointingHandCursor)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 80))
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)  # 减小间距

        # 圆形图标（优先使用icon_id从tj/images加载）
        icon_label = QLabel()
        icon_label.setFixedSize(64, 64)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent;")  # 设置透明背景
        
        pokemon_name = pokemon["name"]
        image_loaded = False
        
        # 优先尝试使用icon_id从tj/images加载
        icon_id = pokemon.get('icon_id', 0)
        if icon_id > 0:
            image_dir = os.path.join(self._base_dir, "image", "tj", "images")
            image_path = os.path.join(image_dir, f"{icon_id:03d}.png")
            
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    rounded_pixmap = QPixmap(64, 64)
                    rounded_pixmap.fill(Qt.transparent)
                    painter = QPainter(rounded_pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform)
                    path = QPainterPath()
                    path.addEllipse(0, 0, 64, 64)
                    painter.setClipPath(path)
                    painter.drawPixmap(0, 0, scaled_pixmap)
                    painter.end()
                    icon_label.setPixmap(rounded_pixmap)
                    image_loaded = True
        
        # 如果icon_id未加载，尝试从ys文件夹加载（支持赛季目录）
        if not image_loaded:
            # 获取当前选择的赛季（优先级：计数器界面 > 图鉴界面 > 默认第三赛季）
            season = "第三赛季"
            if hasattr(self, 'counter_season_combo'):
                season = self.counter_season_combo.currentText()
            elif hasattr(self, 'season_combo'):
                season = self.season_combo.currentText()
            
            image_dir = os.path.join(self._base_dir, "image", "ys", season)
            image_path = os.path.join(image_dir, f"{pokemon_name}.png")
            
            # 如果当前赛季没有，尝试从通用目录加载（向后兼容）
            if not os.path.exists(image_path):
                image_dir = os.path.join(self._base_dir, "image", "ys")
                image_path = os.path.join(image_dir, f"{pokemon_name}.png")
            
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    rounded_pixmap = QPixmap(64, 64)
                    rounded_pixmap.fill(Qt.transparent)
                    painter = QPainter(rounded_pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform)
                    path = QPainterPath()
                    path.addEllipse(0, 0, 64, 64)
                    painter.setClipPath(path)
                    painter.drawPixmap(0, 0, scaled_pixmap)
                    painter.end()
                    icon_label.setPixmap(rounded_pixmap)
                    image_loaded = True
        
        # 如果都未加载，使用默认样式
        if not image_loaded:
            self._set_default_icon(icon_label, pokemon.get("icon", "✨"))
        
        layout.addWidget(icon_label, 0, Qt.AlignHCenter)  # 水平居中

        name = QLabel(pokemon["name"])
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet("color: #f8f0ff; font-weight: 600; font-size: 15px;")
        layout.addWidget(name)

        # 处理types字段(可能是列表或字符串)
        types = pokemon.get("types", [])
        if isinstance(types, list):
            type_str = "、".join(types)
        else:
            type_str = str(types)
        
        type_label = QLabel(type_str)
        type_label.setAlignment(Qt.AlignCenter)
        type_label.setStyleSheet("color: #c084fc; font-size: 12px; font-weight: 500;")
        layout.addWidget(type_label)
        
        # 添加进度信息显示（所有精灵都显示）
        pokemon_name = pokemon["name"]
        counter = self._find_counter_by_lkwg(pokemon_name)
        
        if counter:
            # 有正式计数器
            count = counter.count
            target = counter.target
        else:
            # 无正式计数器，使用全局追踪数据
            count = self.manager.get_global_breakthrough(pokemon_name)
            target = 80  # 默认保底
        
        # 显示进度文本
        progress_info = QLabel(f"{count}/{target}")
        progress_info.setAlignment(Qt.AlignCenter)
        if counter:
            progress_info.setStyleSheet("color: #e0aaff; font-size: 11px; font-weight: 600;")
        else:
            progress_info.setStyleSheet("color: #a78bfa; font-size: 11px;")
        layout.addWidget(progress_info)
        
        # 添加小进度条（完全复制左侧计数器样式）
        # 第二行：进度条
        progress_row = QWidget()
        progress_row_layout = QHBoxLayout(progress_row)
        progress_row_layout.setContentsMargins(0, 0, 0, 0)
        progress_row_layout.setSpacing(0)
        
        # 进度条
        progress_bar = QFrame()
        progress_bar.setFixedHeight(3)
        progress_bar.setFixedWidth(100)
        progress_bar.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 15, 19, 0.8);
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 2px;
            }
        """)
        progress_bar_inner = QHBoxLayout(progress_bar)
        progress_bar_inner.setContentsMargins(0, 0, 0, 0)
        progress_bar_inner.setSpacing(0)
        
        # 进度填充 - 使用实际的target值而非硬编码的80
        progress_fill = QFrame()
        if target > 0:
            progress_percentage = min(100, (count / target) * 100)
        else:
            progress_percentage = 0
        fill_width = max(2, int(100 * progress_percentage / 100))
        progress_fill.setFixedWidth(fill_width)
        progress_fill.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8b5cf6, stop:1 #a78bfa);
                border-radius: 2px;
            }
        """)
        progress_bar_inner.addWidget(progress_fill)
        progress_bar_inner.addStretch()
        
        progress_row_layout.addStretch()  # 左边弹性空间
        progress_row_layout.addWidget(progress_bar)
        progress_row_layout.addStretch()  # 右边弹性空间
        layout.addWidget(progress_row)

        # 点击事件
        card.mousePressEvent = lambda event, p=pokemon: self.create_counter_from_pokemon(p)
        
        # 悬停动效
        def enter_event(event):
            card.setStyleSheet("""
                #pokemonCard {
                    background-color: #2a184a;
                    border: 1px solid rgba(199, 125, 255, 0.6);
                }
            """)
            # 轻微放大
            card.setGeometry(card.x() - 2, card.y() - 2, card.width() + 4, card.height() + 4)
            
        def leave_event(event):
            card.setStyleSheet("")
            card.setGeometry(card.x() + 2, card.y() + 2, card.width() - 4, card.height() - 4)
        
        card.enterEvent = enter_event
        card.leaveEvent = leave_event

        return card
    
    def _set_default_icon(self, icon_label, icon_text):
        """设置默认图标样式（渐变背景+文字）"""
        if len(icon_text) > 2:
            icon_text = icon_text[0]
        icon_label.setText(icon_text)
        icon_label.setStyleSheet("""
            font-size: 32px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #c77dff, stop:1 #9d4edd);
            border-radius: 28px;
            padding: 12px;
            color: white;
        """)

    # ================= 计数器详情视图（改造版-带进度条/图表）=================
    def _create_detail_view(self):
        # 外层滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(SCROLL_BAR_STYLE)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 头部返回按钮
        header_bar = QWidget()
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        btn_back = QPushButton("←")
        btn_back.setFixedSize(32, 32)
        btn_back.setStyleSheet("""
            QPushButton {
                color: #c084fc;
                background: transparent;
                border: none;
                font-size: 20px;
            }
            QPushButton:hover {
                color: #f8f0ff;
            }
        """)
        btn_back.clicked.connect(lambda: self.content_stack.setCurrentIndex(0))
        header_layout.addWidget(btn_back)

        self.detail_header = QLabel("")
        self.detail_header.setStyleSheet("font-size: 18px; font-weight: bold; color: #f8f0ff;")
        header_layout.addWidget(self.detail_header)

        mode_tag = QLabel("计数模式")
        mode_tag.setStyleSheet("""
            background-color: #120822;
            color: #c77dff;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
        """)
        header_layout.addWidget(mode_tag)
        header_layout.addStretch()

        layout.addWidget(header_bar)

        # 详情卡片
        card = QFrame()
        card.setObjectName("detailCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        # 精灵信息区域
        info_section = QWidget()
        info_layout = QHBoxLayout(info_section)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(24)

        # 大图标
        self.big_icon = QLabel()
        self.big_icon.setFixedSize(100, 100)
        self.big_icon.setAlignment(Qt.AlignCenter)
        self.big_icon.setStyleSheet("background: transparent;")
        info_layout.addWidget(self.big_icon)

        # 文字信息
        text_section = QWidget()
        text_layout = QVBoxLayout(text_section)
        text_layout.setContentsMargins(0, 8, 0, 0)
        text_layout.setSpacing(6)

        self.detail_name = QLabel("精灵名称")
        self.detail_name.setStyleSheet("color: #f8f0ff; font-size: 26px; font-weight: bold;")
        text_layout.addWidget(self.detail_name)

        self.detail_type = QLabel("幽系 | 异色")
        self.detail_type.setStyleSheet("color: #e0aaff; font-size: 14px; font-weight: 500;")
        text_layout.addWidget(self.detail_type)

        counter_name_row = QWidget()
        counter_name_layout = QHBoxLayout(counter_name_row)
        counter_name_layout.setContentsMargins(0, 4, 0, 0)
        counter_name_layout.setSpacing(6)

        counter_name_label = QLabel("计数器：")
        counter_name_label.setStyleSheet("color: #c084fc; font-size: 12px;")
        counter_name_layout.addWidget(counter_name_label)

        self.detail_counter_name = QLabel("噩梦追迹")
        self.detail_counter_name.setStyleSheet("color: #e0aaff; font-size: 12px;")
        counter_name_layout.addWidget(self.detail_counter_name)
        counter_name_layout.addStretch()

        text_layout.addWidget(counter_name_row)

        info_layout.addWidget(text_section)
        info_layout.addStretch()
        card_layout.addWidget(info_section)

        # 双统计卡片
        stats_grid = QWidget()
        stats_layout = QGridLayout(stats_grid)
        stats_layout.setSpacing(16)

        stat1 = QFrame()
        stat1.setObjectName("statCard")
        stat1.setStyleSheet("""
            QFrame#statCard {
                background-color: rgba(124, 58, 237, 0.15);
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 8px;
            }
        """)
        stat1_layout = QVBoxLayout(stat1)
        stat1_layout.setContentsMargins(12, 12, 12, 12)

        stat1_label = QLabel("童话事件次数")
        stat1_label.setStyleSheet("color: #c084fc; font-size: 11px;")
        stat1_layout.addWidget(stat1_label)

        self.detail_count = QLabel("0")
        self.detail_count.setStyleSheet("color: #f8f0ff; font-size: 28px; font-weight: bold;")
        stat1_layout.addWidget(self.detail_count)
        stats_layout.addWidget(stat1, 0, 0)

        stat2 = QFrame()
        stat2.setObjectName("statCard")
        stat2.setStyleSheet("""
            QFrame#statCard {
                background-color: rgba(124, 58, 237, 0.15);
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 8px;
            }
        """)
        stat2_layout = QVBoxLayout(stat2)
        stat2_layout.setContentsMargins(12, 12, 12, 12)

        stat2_label = QLabel("保底剩余")
        stat2_label.setStyleSheet("color: #c084fc; font-size: 11px;")
        stat2_layout.addWidget(stat2_label)

        self.detail_remaining = QLabel("48")
        self.detail_remaining.setStyleSheet("color: #f8f0ff; font-size: 28px; font-weight: bold;")
        stat2_layout.addWidget(self.detail_remaining)
        stats_layout.addWidget(stat2, 0, 1)

        card_layout.addWidget(stats_grid)

        # 进度条
        self.detail_progress = QProgressBar()
        self.detail_progress.setMaximum(80)
        self.detail_progress.setValue(0)
        card_layout.addWidget(self.detail_progress)

        # 按钮行: 重置 + 锁定
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)

        btn_reset = QPushButton("重置计数器")
        btn_reset.setObjectName("resetCounterBtn")
        btn_reset.setFixedHeight(40)
        btn_reset.setStyleSheet("""
            QPushButton#resetCounterBtn {
                background-color: rgba(239, 68, 68, 0.15);
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 8px;
                color: #ef4444;
                font-size: 14px;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton#resetCounterBtn:hover {
                background-color: rgba(239, 68, 68, 0.25);
                border: 1px solid rgba(239, 68, 68, 0.55);
            }
            QPushButton#resetCounterBtn:pressed {
                background-color: rgba(220, 38, 38, 0.35);
            }
        """)
        btn_reset.clicked.connect(self.on_reset_counter)
        btn_layout.addWidget(btn_reset)

        btn_layout.addStretch()

        lock_container = QWidget()
        lock_layout = QHBoxLayout(lock_container)
        lock_layout.setContentsMargins(0, 0, 0, 0)
        lock_layout.setSpacing(10)

        self.lock_checkbox = CustomCheckBox()
        self.lock_checkbox.setFixedSize(24, 24)
        self.lock_checkbox.clicked.connect(self.on_toggle_lock)
        lock_layout.addWidget(self.lock_checkbox)

        lock_text_container = QWidget()
        lock_text_layout = QVBoxLayout(lock_text_container)
        lock_text_layout.setContentsMargins(0, 0, 0, 0)
        lock_text_layout.setSpacing(2)

        lock_label = QLabel("锁定计数")
        lock_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 500;")
        lock_text_layout.addWidget(lock_label)

        self.lock_status_label = QLabel("未锁定")
        self.lock_status_label.setStyleSheet("color: #71717a; font-size: 11px;")
        lock_text_layout.addWidget(self.lock_status_label)

        lock_layout.addWidget(lock_text_container, stretch=1)
        btn_layout.addWidget(lock_container)

        card_layout.addWidget(btn_row)
        layout.addWidget(card)

        # ================= 视图切换按钮区 =================
        toggle_section = QWidget()
        toggle_layout = QHBoxLayout(toggle_section)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        toggle_layout.setSpacing(10)

        self.btn_progress_view = QPushButton("进度条")
        self.btn_chart_view = QPushButton("统计图")
        for btn in (self.btn_progress_view, self.btn_chart_view):
            btn.setCheckable(True)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(37, 37, 48, 0.8);
                    color: #a1a1aa;
                    border: 1px solid rgba(124, 58, 237, 0.15);
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 500;
                    padding: 0 18px;
                }
                QPushButton:hover {
                    background-color: rgba(124, 58, 237, 0.15);
                    border-color: rgba(124, 58, 237, 0.35);
                    color: #c084fc;
                }
                QPushButton:checked {
                    background: linear-gradient(135deg, rgba(124, 58, 237, 0.35) 0%, rgba(124, 58, 237, 0.15) 100%);
                    color: #a78bfa;
                    border: 1px solid rgba(124, 58, 237, 0.6);
                    font-weight: 600;
                }
            """)

        self.btn_progress_view.setChecked(True)
        toggle_layout.addWidget(self.btn_progress_view)
        toggle_layout.addWidget(self.btn_chart_view)
        toggle_layout.addStretch()

        # 内部分组切换按钮 (仅统计图模式下显示)
        self.btn_bar_chart = QPushButton("柱状图")
        self.btn_pie_chart = QPushButton("饼图")
        for btn in (self.btn_bar_chart, self.btn_pie_chart):
            btn.setCheckable(True)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(37, 37, 48, 0.6);
                    color: #71717a;
                    border: 1px solid rgba(124, 58, 237, 0.1);
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 500;
                    padding: 0 14px;
                }
                QPushButton:hover {
                    background-color: rgba(124, 58, 237, 0.12);
                    color: #a78bfa;
                }
                QPushButton:checked {
                    background-color: rgba(124, 58, 237, 0.25);
                    color: #c084fc;
                    border: 1px solid rgba(124, 58, 237, 0.4);
                    font-weight: 600;
                }
            """)
        self.btn_bar_chart.setChecked(True)
        self.sub_toggle_group = QWidget()
        sub_toggle_layout = QHBoxLayout(self.sub_toggle_group)
        sub_toggle_layout.setContentsMargins(0, 0, 0, 0)
        sub_toggle_layout.setSpacing(8)
        sub_toggle_layout.addWidget(self.btn_bar_chart)
        sub_toggle_layout.addWidget(self.btn_pie_chart)
        self.sub_toggle_group.setVisible(False)
        toggle_layout.addWidget(self.sub_toggle_group)

        layout.addWidget(toggle_section)

        # ================= 进度条 + 图表堆栈 =================
        self.chart_stack = QStackedWidget()
        self.chart_stack.setMinimumHeight(300)

        # 页面0: 进度条视图（带滚动区域）
        self.progress_page = QWidget()
        self.progress_page_layout = QVBoxLayout(self.progress_page)
        self.progress_page_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_page_layout.setSpacing(6)

        # 主进度条标题
        main_progress_header = QLabel("精灵出现统计")
        main_progress_header.setStyleSheet("color: #c084fc; font-size: 14px; font-weight: 600; padding: 4px 0;")
        self.progress_page_layout.addWidget(main_progress_header)

        # 进度条滚动区域
        self.progress_scroll_area = QScrollArea()
        self.progress_scroll_area.setWidgetResizable(True)
        self.progress_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.progress_scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.progress_scroll_area.setFrameShape(QFrame.NoFrame)

        # 进度条容器（精灵+属性组合）
        self.pokemon_progress_container = QWidget()
        self.pokemon_progress_container.setStyleSheet("background: transparent;")
        self.pokemon_progress_layout = QVBoxLayout(self.pokemon_progress_container)
        self.pokemon_progress_layout.setContentsMargins(0, 0, 0, 0)
        self.pokemon_progress_layout.setSpacing(8)

        self.progress_scroll_area.setWidget(self.pokemon_progress_container)
        self.progress_page_layout.addWidget(self.progress_scroll_area, stretch=1)

        self.chart_stack.addWidget(self.progress_page)  # index 0

        # 页面1: 统计图视图 (左右双栏：精灵 + 属性)
        self.chart_page = QWidget()
        self.chart_page_layout = QHBoxLayout(self.chart_page)
        self.chart_page_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_page_layout.setSpacing(16)

        # 左侧：精灵统计（柱状图/饼图堆叠切换）
        self.pokemon_chart_container = QWidget()
        self.pokemon_chart_layout = QVBoxLayout(self.pokemon_chart_container)
        self.pokemon_chart_layout.setContentsMargins(0, 0, 0, 0)
        self.pokemon_chart_layout.setSpacing(8)

        pokemon_header = QLabel("精灵统计")
        pokemon_header.setStyleSheet("color: #c084fc; font-size: 14px; font-weight: 600;")
        self.pokemon_chart_layout.addWidget(pokemon_header)

        self.pokemon_chart_scroll = QScrollArea()
        self.pokemon_chart_scroll.setWidgetResizable(True)
        self.pokemon_chart_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.pokemon_chart_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.pokemon_chart_scroll.setFrameShape(QFrame.NoFrame)
        self.pokemon_chart_stack = QStackedWidget()
        self.pokemon_chart_scroll.setWidget(self.pokemon_chart_stack)
        self.pokemon_chart_layout.addWidget(self.pokemon_chart_scroll, stretch=1)

        self.chart_page_layout.addWidget(self.pokemon_chart_container, stretch=1)

        # 右侧：属性统计（柱状图/饼图堆叠切换）
        self.type_chart_container = QWidget()
        self.type_chart_layout = QVBoxLayout(self.type_chart_container)
        self.type_chart_layout.setContentsMargins(0, 0, 0, 0)
        self.type_chart_layout.setSpacing(8)

        type_header = QLabel("属性统计")
        type_header.setStyleSheet("color: #a78bfa; font-size: 14px; font-weight: 600;")
        self.type_chart_layout.addWidget(type_header)

        self.type_chart_scroll = QScrollArea()
        self.type_chart_scroll.setWidgetResizable(True)
        self.type_chart_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.type_chart_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.type_chart_scroll.setFrameShape(QFrame.NoFrame)
        self.type_chart_stack = QStackedWidget()
        self.type_chart_scroll.setWidget(self.type_chart_stack)
        self.type_chart_layout.addWidget(self.type_chart_scroll, stretch=1)

        self.chart_page_layout.addWidget(self.type_chart_container, stretch=1)

        self.chart_stack.addWidget(self.chart_page)  # index 1

        layout.addWidget(self.chart_stack, stretch=1)

        # ================= 信号连接 =================
        self.btn_progress_view.clicked.connect(lambda: self._switch_chart_view(0))
        self.btn_chart_view.clicked.connect(lambda: self._switch_chart_view(1))
        self.btn_bar_chart.clicked.connect(lambda: self._switch_sub_chart("bar"))
        self.btn_pie_chart.clicked.connect(lambda: self._switch_sub_chart("pie"))

        scroll.setWidget(container)
        return scroll

    # ================= 右侧面板 =================
    def _create_right_panel(self):
        panel = QFrame()
        panel.setObjectName("rightPanel")
        panel.setFixedWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(24)
        
        # 第一部分：计数器设置
        settings_section = QWidget()
        settings_layout = QVBoxLayout(settings_section)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(16)
        
        section_title = QLabel("计数器设置")
        section_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 600;")
        settings_layout.addWidget(section_title)
        
        # 精灵名称输入框
        name_group = QWidget()
        name_layout = QVBoxLayout(name_group)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(4)
        
        name_label = QLabel("精灵名称")
        name_label.setStyleSheet("color: #71717a; font-size: 12px;")
        name_layout.addWidget(name_label)
        
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("请输入精灵名称")
        self.edit_name.setStyleSheet("""
            QLineEdit {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 8px 12px;
                color: #e4e4e7;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #7c3aed;
            }
        """)
        name_layout.addWidget(self.edit_name)
        settings_layout.addWidget(name_group)
        
        # 属性选择框
        type_group = QWidget()
        type_layout = QVBoxLayout(type_group)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(4)
        
        type_label = QLabel("属性")
        type_label.setStyleSheet("color: #71717a; font-size: 12px;")
        type_layout.addWidget(type_label)
        
        # 属性多选容器
        edit_type_widget = QWidget()
        edit_type_layout = QHBoxLayout(edit_type_widget)
        edit_type_layout.setContentsMargins(0, 4, 0, 0)
        edit_type_layout.setSpacing(8)
        
        self.edit_type_1 = TriangleComboBox()
        self.edit_type_1.addItems(["请选择"] + get_all_types())
        self.edit_type_1.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 8px 12px;
                color: #e4e4e7;
                font-size: 14px;
            }
            QComboBox:focus {
                border: 1px solid #7c3aed;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)
        edit_type_layout.addWidget(self.edit_type_1)
        
        self.edit_type_2 = TriangleComboBox()
        self.edit_type_2.addItems(["无"] + get_all_types())
        self.edit_type_2.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 8px 12px;
                color: #e4e4e7;
                font-size: 14px;
            }
            QComboBox:focus {
                border: 1px solid #7c3aed;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)
        edit_type_layout.addWidget(self.edit_type_2)
        
        type_layout.addWidget(edit_type_widget)
        settings_layout.addWidget(type_group)
        
        # 保底次数输入框
        target_group = QWidget()
        target_layout = QVBoxLayout(target_group)
        target_layout.setContentsMargins(0, 0, 0, 0)
        target_layout.setSpacing(4)
        
        target_label = QLabel("保底次数")
        target_label.setStyleSheet("color: #71717a; font-size: 12px;")
        target_layout.addWidget(target_label)
        
        self.edit_target = QLineEdit()
        self.edit_target.setText("80")
        self.edit_target.setStyleSheet("""
            QLineEdit {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 8px 12px;
                color: #e4e4e7;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #7c3aed;
            }
        """)
        target_layout.addWidget(self.edit_target)
        settings_layout.addWidget(target_group)
        
        # 童话事件次数输入框
        wai_group = QWidget()
        wai_layout = QVBoxLayout(wai_group)
        wai_layout.setContentsMargins(0, 0, 0, 0)
        wai_layout.setSpacing(4)
        
        wai_label = QLabel("童话事件次数")
        wai_label.setStyleSheet("color: #71717a; font-size: 12px;")
        wai_layout.addWidget(wai_label)
        
        self.edit_wai = QLineEdit()
        self.edit_wai.setText("0")
        self.edit_wai.setStyleSheet("""
            QLineEdit {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 8px 12px;
                color: #e4e4e7;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #7c3aed;
            }
        """)
        wai_layout.addWidget(self.edit_wai)
        settings_layout.addWidget(wai_group)
        
        # 保存按钮
        btn_save = QPushButton("保存修改")
        btn_save.setObjectName("floatingModeBtn")
        btn_save.setFixedHeight(40)
        btn_save.clicked.connect(self.on_save_counter_edit)
        settings_layout.addWidget(btn_save)
        
        # 本次出闪记录按钮
        btn_shiny_record = QPushButton("本次出闪记录")
        btn_shiny_record.setObjectName("settingsBtn")
        btn_shiny_record.setFixedHeight(40)
        btn_shiny_record.clicked.connect(self.on_record_shiny)
        settings_layout.addWidget(btn_shiny_record)
        
        # 删除按钮
        btn_delete = QPushButton("删除计数器")
        btn_delete.setObjectName("settingsBtn")
        btn_delete.setFixedHeight(40)
        btn_delete.clicked.connect(self.on_delete_current_counter)
        settings_layout.addWidget(btn_delete)
        
        layout.addWidget(settings_section)
        
        # 第二部分：快捷操作
        quick_section = QWidget()
        quick_layout = QVBoxLayout(quick_section)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(8)
        
        quick_title = QLabel("快捷操作")
        quick_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 600;")
        quick_layout.addWidget(quick_title)
        
        btn_export = QPushButton("导出计数器数据")
        btn_export.setObjectName("customPokemonBtn")
        btn_export.setFixedHeight(36)
        btn_export.clicked.connect(self.on_export_counters)
        quick_layout.addWidget(btn_export)
        
        btn_import = QPushButton("导入计数器数据")
        btn_import.setObjectName("customPokemonBtn")
        btn_import.setFixedHeight(36)
        btn_import.clicked.connect(self.on_import_counters)
        quick_layout.addWidget(btn_import)
        
        layout.addWidget(quick_section)
        
        layout.addStretch()
        return panel

    # ================= 核心逻辑 =================
    def _switch_nav_page(self, index, active_btn=None, inactive_btn=None):
        """切换导航页面"""
        self.content_stack.setCurrentIndex(index)
        
        # 清除所有导航按钮的active状态和焦点
        sidebar = self.sidebar
        for i in range(sidebar.layout().count()):
            item = sidebar.layout().itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # 查找nav_container中的QPushButton
                if isinstance(widget, QWidget):
                    for child in widget.findChildren(QPushButton):
                        if child.objectName() == "navItem":
                            child.setProperty("active", False)
                            child.clearFocus()
                            child.style().unpolish(child)
                            child.style().polish(child)
        
        # 设置当前按钮为active
        if active_btn:
            active_btn.setProperty("active", True)
            active_btn.clearFocus()
            active_btn.style().unpolish(active_btn)
            active_btn.style().polish(active_btn)
    
    def _load_initial_data(self):
        """初始不加载任何预设计数器"""
        pass

    def _refresh_all(self):
        self._refresh_counter_list()
        self._refresh_right_panel()
        self._refresh_detail_view()
        self._populate_pokemon_grid()
        self._refresh_pokedex()
        active = self.manager.get_active()
        if active:
            self._update_charts(active)
            self._update_progress_bars(active)  # 确保进度条也刷新
        else:
            # 清空图表
            while self.pokemon_chart_stack.count():
                w = self.pokemon_chart_stack.widget(0)
                self.pokemon_chart_stack.removeWidget(w)
                w.hide()  # 立即隐藏
                w.deleteLater()
            while self.type_chart_stack.count():
                w = self.type_chart_stack.widget(0)
                self.type_chart_stack.removeWidget(w)
                w.hide()  # 立即隐藏
                w.deleteLater()
            # 清空进度条
            while self.pokemon_progress_layout.count():
                item = self.pokemon_progress_layout.takeAt(0)
                if item.widget():
                    w = item.widget()
                    w.hide()  # 立即隐藏
                    w.deleteLater()

    def _refresh_counter_list(self):
        print(f"🔄 刷新计数器列表, 共{len(self.manager.counters)}个计数器")
        self.counter_list_widget.blockSignals(True)
        self.counter_list_widget.clear()
        
        # 如果折叠，不显示任何计数器
        if self.manager.is_folded:
            item = QListWidgetItem("列表已折叠")
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QColor("#6b6f82"))
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled & ~Qt.ItemIsSelectable)  # 禁用交互
            self.counter_list_widget.addItem(item)
            self.counter_list_widget.blockSignals(False)
            return
        
        for counter in self.manager.counters:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, counter.id)
            item.setSizeHint(QSize(260, 80))  # 增加高度以容纳两行
            self.counter_list_widget.addItem(item)

            # 自定义widget作为item - 每次都重新创建以反映最新数据
            item_widget = self._create_counter_list_item(counter)
            self.counter_list_widget.setItemWidget(self.counter_list_widget.item(self.counter_list_widget.count()-1), item_widget)

        # 选中激活的计数器
        active = self.manager.get_active()
        if active:
            for i in range(self.counter_list_widget.count()):
                if self.counter_list_widget.item(i).data(Qt.UserRole) == active.id:
                    self.counter_list_widget.setCurrentRow(i)
                    break
        
        self.counter_list_widget.blockSignals(False)

    def _create_counter_list_item(self, counter):
        """创建计数器列表项widget - 专业设计"""
        widget = QWidget()
        widget.setObjectName("counterItemWidget")
        widget.setStyleSheet("""
            #counterItemWidget {
                background-color: #121212;
                border: 1px solid rgba(139, 92, 246, 0.2);
                border-radius: 8px;
            }
            #counterItemWidget:hover {
                background-color: #1a1a1a;
                border: 1px solid rgba(139, 92, 246, 0.4);
            }
        """)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 10, 10, 10)  # 增加边距
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignVCenter)

        # 左侧：图标 + 信息
        left_section = QWidget()
        left_layout = QVBoxLayout(left_section)  # 垂直布局
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        
        # 第一行：图标、名字、属性、数字全部横向排列在同一水平线
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)
        top_layout.setAlignment(Qt.AlignVCenter)
        
        # 圆形图标（优先使用icon_id从tj/images加载）
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent;")  # 设置透明背景
        
        pokemon_name = counter.pokemon_name
        image_loaded = False
        
        # 查找对应的自定义精灵数据，获取icon_id
        custom_pokemons = self.manager.get_custom_pokemons()
        icon_id = 0
        for cp in custom_pokemons:
            if cp['name'] == pokemon_name:
                icon_id = cp.get('icon_id', 0)
                break
        
        # 优先尝试使用icon_id从tj/images加载
        if icon_id > 0:
            image_dir = os.path.join(self._base_dir, "image", "tj", "images")
            image_path = os.path.join(image_dir, f"{icon_id:03d}.png")
            
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    rounded_pixmap = QPixmap(32, 32)
                    rounded_pixmap.fill(Qt.transparent)
                    painter = QPainter(rounded_pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform)
                    path = QPainterPath()
                    path.addEllipse(0, 0, 32, 32)
                    painter.setClipPath(path)
                    painter.drawPixmap(0, 0, scaled_pixmap)
                    painter.end()
                    icon_label.setPixmap(rounded_pixmap)
                    image_loaded = True
        
        # 如果icon_id未加载，尝试从ys文件夹加载（支持赛季目录）
        if not image_loaded:
            # 获取当前选择的赛季（优先级：计数器界面 > 图鉴界面 > 默认第三赛季）
            season = "第三赛季"
            if hasattr(self, 'counter_season_combo'):
                season = self.counter_season_combo.currentText()
            elif hasattr(self, 'season_combo'):
                season = self.season_combo.currentText()
            
            image_dir = os.path.join(self._base_dir, "image", "ys", season)
            image_path = os.path.join(image_dir, f"{pokemon_name}.png")
            
            # 如果当前赛季没有，尝试从其他赛季目录加载
            if not os.path.exists(image_path):
                for s in ["第一赛季", "第二赛季", "第三赛季"]:
                    if s == season:
                        continue
                    other_dir = os.path.join(self._base_dir, "image", "ys", s)
                    other_path = os.path.join(other_dir, f"{pokemon_name}.png")
                    if os.path.exists(other_path):
                        image_path = other_path
                        break
            
            # 如果赛季目录都没有，尝试从通用目录加载（向后兼容）
            if not os.path.exists(image_path):
                image_dir = os.path.join(self._base_dir, "image", "ys")
                image_path = os.path.join(image_dir, f"{pokemon_name}.png")
            
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    rounded_pixmap = QPixmap(32, 32)
                    rounded_pixmap.fill(Qt.transparent)
                    painter = QPainter(rounded_pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform)
                    path = QPainterPath()
                    path.addEllipse(0, 0, 32, 32)
                    painter.setClipPath(path)
                    painter.drawPixmap(0, 0, scaled_pixmap)
                    painter.end()
                    icon_label.setPixmap(rounded_pixmap)
                    image_loaded = True
        
        # 如果都未加载，使用默认样式
        if not image_loaded:
            icon_label.setText(pokemon_name[0] if pokemon_name else "?")
            icon_label.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6c5ce7, stop:1 #a855f7);
                    border-radius: 16px;
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
        top_layout.addWidget(icon_label)
        
        # 名称
        name_label = QLabel(counter.pokemon_name)
        name_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 600;")
        top_layout.addWidget(name_label)
        
        # 属性
        info_label = QLabel(f"{counter.type}")
        info_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        top_layout.addWidget(info_label)
        
        top_layout.addStretch()  # 弹性空间，把数字推到右边
        
        # 数字（当前击破次数 count）
        progress_info = QLabel(f"{counter.count}")
        progress_info.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: bold;")
        top_layout.addWidget(progress_info)
        
        left_layout.addWidget(top_row)
        
        # 第二行：进度条靠右
        progress_row = QWidget()
        progress_row_layout = QHBoxLayout(progress_row)
        progress_row_layout.setContentsMargins(0, 0, 0, 0)
        progress_row_layout.setSpacing(0)
        progress_row_layout.addStretch()  # 左边弹性空间，把进度条推到右边
        
        # 进度条
        progress_bar = QFrame()
        progress_bar.setFixedHeight(3)
        progress_bar.setFixedWidth(100)
        progress_bar.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 15, 19, 0.8);
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 2px;
            }
        """)
        progress_bar_inner = QHBoxLayout(progress_bar)
        progress_bar_inner.setContentsMargins(0, 0, 0, 0)
        progress_bar_inner.setSpacing(0)
        
        # 进度填充 - 使用实际的target值而非硬编码的80
        progress_fill = QFrame()
        if counter.target > 0:
            progress_percentage = min(100, (counter.count / counter.target) * 100)
        else:
            progress_percentage = 0
        fill_width = max(2, int(100 * progress_percentage / 100))
        progress_fill.setFixedWidth(fill_width)
        progress_fill.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8b5cf6, stop:1 #a78bfa);
                border-radius: 2px;
            }
        """)
        progress_bar_inner.addWidget(progress_fill)
        progress_bar_inner.addStretch()
        
        progress_row_layout.addWidget(progress_bar)
        
        left_layout.addWidget(progress_row)
        
        layout.addWidget(left_section, stretch=1)

        return widget

    def _refresh_right_panel(self):
        """刷新右侧面板表单数据"""
        active = self.manager.get_active()
        if active:
            self.edit_name.setText(active.pokemon_name)
            # 设置属性下拉框（支持双属性）
            if active.type:
                type_list = active.type.split("、")
                if len(type_list) >= 1:
                    self.edit_type_1.setCurrentText(type_list[0])
                else:
                    self.edit_type_1.setCurrentText("请选择")
                if len(type_list) >= 2:
                    self.edit_type_2.setCurrentText(type_list[1])
                else:
                    self.edit_type_2.setCurrentText("无")
            else:
                self.edit_type_1.setCurrentText("请选择")
                self.edit_type_2.setCurrentText("无")
            self.edit_target.setText(str(active.target))
            self.edit_wai.setText(str(active.count))
        else:
            self.edit_name.clear()
            self.edit_type_1.setCurrentText("请选择")
            self.edit_type_2.setCurrentText("无")
            self.edit_target.setText("80")
            self.edit_wai.setText("0")

    def _refresh_detail_view(self):
        active = self.manager.get_active()
        if active:
            self.detail_header.setText(active.pokemon_name)
            self.detail_name.setText(f"{active.pokemon_name}")
            self.detail_type.setText(f"{active.type} | 异色")
            self.detail_counter_name.setText(active.counter_name)
            
            # 更新大图标（优先使用icon_id从tj/images加载）
            pokemon_name = active.pokemon_name
            image_loaded = False
            
            # 优先使用计数器自带的icon_id
            icon_id = active.icon_id if hasattr(active, 'icon_id') else 0
            
            # 如果icon_id为0，尝试从custom_pokemons中查找
            if icon_id == 0:
                custom_pokemons = self.manager.get_custom_pokemons()
                for cp in custom_pokemons:
                    if cp['name'] == pokemon_name:
                        icon_id = cp.get('icon_id', 0)
                        break
            
            # 优先尝试使用icon_id从tj/images加载
            if icon_id > 0:
                image_dir = os.path.join(self._base_dir, "image", "tj", "images")
                image_path = os.path.join(image_dir, f"{icon_id:03d}.png")
                
                if os.path.exists(image_path):
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        rounded_pixmap = QPixmap(100, 100)
                        rounded_pixmap.fill(Qt.transparent)
                        painter = QPainter(rounded_pixmap)
                        painter.setRenderHint(QPainter.Antialiasing)
                        painter.setRenderHint(QPainter.SmoothPixmapTransform)
                        path = QPainterPath()
                        path.addEllipse(0, 0, 100, 100)
                        painter.setClipPath(path)
                        painter.drawPixmap(0, 0, scaled_pixmap)
                        painter.end()
                        self.big_icon.setPixmap(rounded_pixmap)
                        self.big_icon.setText("")
                        self.big_icon.setStyleSheet("background: transparent;")
                        image_loaded = True
            
            # 如果icon_id未加载，尝试从ys文件夹加载（支持赛季目录）
            if not image_loaded:
                # 获取当前选择的赛季（优先级：计数器界面 > 图鉴界面 > 默认第三赛季）
                season = "第三赛季"
                if hasattr(self, 'counter_season_combo'):
                    season = self.counter_season_combo.currentText()
                elif hasattr(self, 'season_combo'):
                    season = self.season_combo.currentText()
                
                image_dir = os.path.join(self._base_dir, "image", "ys", season)
                image_path = os.path.join(image_dir, f"{pokemon_name}.png")
                
                # 如果当前赛季没有，尝试从其他赛季目录加载
                if not os.path.exists(image_path):
                    for s in ["第一赛季", "第二赛季", "第三赛季"]:
                        if s == season:
                            continue
                        other_dir = os.path.join(self._base_dir, "image", "ys", s)
                        other_path = os.path.join(other_dir, f"{pokemon_name}.png")
                        if os.path.exists(other_path):
                            image_path = other_path
                            break
                
                # 如果赛季目录都没有，尝试从通用目录加载（向后兼容）
                if not os.path.exists(image_path):
                    image_dir = os.path.join(self._base_dir, "image", "ys")
                    image_path = os.path.join(image_dir, f"{pokemon_name}.png")
                
                if os.path.exists(image_path):
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        rounded_pixmap = QPixmap(100, 100)
                        rounded_pixmap.fill(Qt.transparent)
                        painter = QPainter(rounded_pixmap)
                        painter.setRenderHint(QPainter.Antialiasing)
                        painter.setRenderHint(QPainter.SmoothPixmapTransform)
                        path = QPainterPath()
                        path.addEllipse(0, 0, 100, 100)
                        painter.setClipPath(path)
                        painter.drawPixmap(0, 0, scaled_pixmap)
                        painter.end()
                        self.big_icon.setPixmap(rounded_pixmap)
                        self.big_icon.setText("")
                        self.big_icon.setStyleSheet("background: transparent;")
                        image_loaded = True
            
            # 如果都未加载，使用默认样式
            if not image_loaded:
                self.big_icon.setPixmap(QPixmap())
                self.big_icon.setText("🐾")
                self.big_icon.setStyleSheet("""
                    font-size: 48px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #c77dff, stop:1 #9d4edd);
                    border-radius: 50px;
                    color: white;
                """)
            
            # 童话事件次数显示 count
            self.detail_count.setText(str(active.count))
            # 保底剩余显示 target - count
            remaining = active.target - active.count
            self.detail_remaining.setText(str(remaining))
            # 进度条显示 count/target 的进度
            max_val = active.target
            progress_val = active.count
            self.detail_progress.setMaximum(max_val)
            self.detail_progress.setValue(progress_val)
            # 更新锁定复选框状态
            if hasattr(self, 'lock_checkbox'):
                self.lock_checkbox.setChecked(active.is_locked)
            # 更新锁定状态提示文字
            if hasattr(self, 'lock_status_label'):
                self.lock_status_label.setText("已锁定" if active.is_locked else "未锁定")
                if active.is_locked:
                    self.lock_status_label.setStyleSheet("color: #22c55e; font-size: 11px; font-weight: 500;")
                else:
                    self.lock_status_label.setStyleSheet("color: #71717a; font-size: 11px;")
            
            # 同步更新悬浮窗
            if hasattr(self, 'floating_window'):
                self.floating_window.update_data(
                    active.pokemon_name,
                    active.type,
                    active.count,
                    active.target,
                    active.is_locked,
                    active.nightmare_count,
                    icon_id
                )
                
            # 更新进度条和图表数据
            self._update_progress_bars(active)
            self._update_charts(active)
        self.counter_changed.emit()

    def _update_progress_bars(self, active):
        """更新精灵进度条和属性进度条（精灵下方紧跟属性）"""
        # 清除旧的进度条
        while self.pokemon_progress_layout.count():
            item = self.pokemon_progress_layout.takeAt(0)
            if item.widget():
                w = item.widget()
                w.hide()  # 立即隐藏
                w.deleteLater()

        stats = getattr(active, 'battle_pokemon_stats', {})
        if not stats:
            no_data = QLabel("暂无精灵出现数据")
            no_data.setStyleSheet("color: #71717a; font-size: 12px; padding: 12px 0;")
            self.pokemon_progress_layout.addWidget(no_data)
            self.pokemon_progress_layout.addStretch()
            return

        total = sum(stats.values())
        max_count = max(stats.values()) if stats else 1

        # 精灵进度条（按次数降序排列），每个精灵下方紧跟其属性
        sorted_pokemon = sorted(stats.items(), key=lambda x: x[1], reverse=True)
        for name, cnt in sorted_pokemon:
            # 每只精灵为一个分组容器
            group = QWidget()
            group_layout = QVBoxLayout(group)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(2)

            bar = PokemonProgressBar(name, cnt, total, max_count)
            group_layout.addWidget(bar)

            types = get_pokemon_types(name)
            if not types:
                types = [active.type.split("、")[0] if active.type else "普通"]
            for t in types:
                t_short = t.replace("系", "")
                tbar = TypeProgressBar(t_short, cnt, total, max_count)
                tbar.setFixedHeight(24)
                group_layout.addWidget(tbar)

            self.pokemon_progress_layout.addWidget(group)

        # 添加弹性空间确保内容从顶部开始排列
        self.pokemon_progress_layout.addStretch()

        # 切换到进度条视图时播放动画
        if hasattr(self, 'chart_stack') and self.chart_stack.currentIndex() == 0:
            self._animate_progress_bars()

    def _update_charts(self, active):
        """更新柱状图和饼图（左右双栏：精灵+属性）"""
        # 无论有没有数据，都先清除旧图表（避免空数据时旧图表残留）
        while self.pokemon_chart_stack.count():
            w = self.pokemon_chart_stack.widget(0)
            self.pokemon_chart_stack.removeWidget(w)
            w.hide()  # 立即隐藏
            w.deleteLater()
        while self.type_chart_stack.count():
            w = self.type_chart_stack.widget(0)
            self.type_chart_stack.removeWidget(w)
            w.hide()  # 立即隐藏
            w.deleteLater()

        stats = getattr(active, 'battle_pokemon_stats', {})
        if not stats:
            return

        total = sum(stats.values())

        # 为每个精灵分配一个唯一的颜色，属性颜色跟随对应精灵的颜色（按出现次数排序）
        sorted_pokemon = sorted(stats.items(), key=lambda x: x[1], reverse=True)
        pokemon_color_map = {}        # 精灵名 → (r,g,b)
        type_color_map = {}           # 属性简称 → (r,g,b)
        _CHART_COLORS = [
            (180, 80, 250), (250, 80, 80), (60, 180, 250), (250, 200, 50),
            (80, 220, 120), (255, 140, 50), (240, 100, 200), (80, 230, 230),
            (180, 160, 100), (200, 120, 80), (160, 100, 220), (100, 200, 160),
            (220, 180, 80), (140, 200, 100), (200, 150, 200), (100, 150, 200),
            (180, 100, 140), (120, 180, 200), (200, 180, 120), (160, 160, 200),
        ]
        for i, (name, cnt) in enumerate(sorted_pokemon):
            c = _CHART_COLORS[i % len(_CHART_COLORS)]
            pokemon_color_map[name] = c
            types = get_pokemon_types(name)
            if not types:
                types = [active.type.split("、")[0] if active.type else "普通"]
            for t in types:
                t_short = t.replace("系", "")
                if t_short not in type_color_map:
                    type_color_map[t_short] = c  # 属性颜色跟随第一个出现该属性的精灵颜色

        # 准备精灵图表数据（每个精灵带上分配好的颜色）
        pokemon_bar_data = [(name, cnt, pokemon_color_map[name]) for name, cnt in sorted_pokemon]

        # 准备属性统计数据
        type_stats = {}
        for name, cnt in stats.items():
            types = get_pokemon_types(name)
            if not types:
                types = [active.type.split("、")[0] if active.type else "普通"]
            for t in types:
                t_short = t.replace("系", "")
                type_stats[t_short] = type_stats.get(t_short, 0) + cnt

        sorted_types = sorted(type_stats.items(), key=lambda x: x[1], reverse=True)
        type_bar_data = [(tname, tcnt, type_color_map.get(tname, (150, 150, 150))) for tname, tcnt in sorted_types]

        # 精灵柱状图 (pokemon stack page 0)
        pokemon_bar = BarChartWidget(pokemon_bar_data)
        self.pokemon_chart_stack.addWidget(pokemon_bar)

        # 精灵饼图 (pokemon stack page 1)
        pokemon_pie = PieChartWidget(pokemon_bar_data)
        self.pokemon_chart_stack.addWidget(pokemon_pie)

        # 属性柱状图 (type stack page 0)
        type_bar = BarChartWidget(type_bar_data)
        self.type_chart_stack.addWidget(type_bar)

        # 属性饼图 (type stack page 1)
        type_pie = PieChartWidget(type_bar_data)
        self.type_chart_stack.addWidget(type_pie)

        # 根据当前子视图模式显示正确页面
        current_mode = "bar" if self.btn_bar_chart.isChecked() else "pie"
        self._switch_sub_chart(current_mode)

        # 如果当前在图表视图，播放动画
        if hasattr(self, 'chart_stack') and self.chart_stack.currentIndex() == 1:
            self._animate_charts()

    def _switch_chart_view(self, index):
        """切换进度条/统计图视图"""
        self.chart_stack.setCurrentIndex(index)
        self.btn_progress_view.setChecked(index == 0)
        self.btn_chart_view.setChecked(index == 1)
        self.sub_toggle_group.setVisible(index == 1)
        if index == 0:
            self._animate_progress_bars()
        else:
            self._animate_charts()

    def _switch_sub_chart(self, mode):
        """切换柱状图/饼图模式（同时切换左右两栏）"""
        self.btn_bar_chart.setChecked(mode == "bar")
        self.btn_pie_chart.setChecked(mode == "pie")

        if mode == "bar":
            self.pokemon_chart_stack.setCurrentIndex(0)
            self.type_chart_stack.setCurrentIndex(0)
            self._animate_bar_chart()
        else:
            self.pokemon_chart_stack.setCurrentIndex(1)
            self.type_chart_stack.setCurrentIndex(1)
            self._animate_pie_chart()

    def _animate_progress_bars(self):
        """启动进度条动画（每组依次延迟）"""
        for i in range(self.pokemon_progress_layout.count()):
            w = self.pokemon_progress_layout.itemAt(i)
            if w and w.widget() and hasattr(w.widget(), 'layout'):
                gl = w.widget().layout()
                if gl is None:
                    continue
                delay = i * 120
                for j in range(gl.count()):
                    child = gl.itemAt(j)
                    if child and child.widget():
                        if isinstance(child.widget(), PokemonProgressBar):
                            QTimer.singleShot(delay, child.widget().animate_in)
                        elif isinstance(child.widget(), TypeProgressBar):
                            QTimer.singleShot(delay + 60, child.widget().animate_in)

    def _animate_charts(self):
        """启动图表动画"""
        current_mode = "bar" if self.btn_bar_chart.isChecked() else "pie"
        if current_mode == "bar":
            self._animate_bar_chart()
        else:
            self._animate_pie_chart()

    def _animate_bar_chart(self):
        """启动柱状图动画（左右两栏同时播放）"""
        for i in range(self.pokemon_chart_stack.count()):
            w = self.pokemon_chart_stack.widget(i)
            if w and isinstance(w, BarChartWidget):
                QTimer.singleShot(100, w.animate_in)
        for i in range(self.type_chart_stack.count()):
            w = self.type_chart_stack.widget(i)
            if w and isinstance(w, BarChartWidget):
                QTimer.singleShot(200, w.animate_in)

    def _animate_pie_chart(self):
        """启动饼图动画（左右两栏同时播放）"""
        for i in range(self.pokemon_chart_stack.count()):
            w = self.pokemon_chart_stack.widget(i)
            if w and isinstance(w, PieChartWidget):
                QTimer.singleShot(100, w.animate_in)
        for i in range(self.type_chart_stack.count()):
            w = self.type_chart_stack.widget(i)
            if w and isinstance(w, PieChartWidget):
                QTimer.singleShot(200, w.animate_in)

    # ================= 槽函数 =================
    def mousePressEvent(self, event):
        """实现无边框窗口拖拽"""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """实现无边框窗口拖拽"""
        if event.buttons() == Qt.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        super().mouseMoveEvent(event)
    
    def toggle_maximize(self):
        """切换最大化/还原"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    
    def on_counter_item_clicked(self, item):
        """点击计数器列表项时切换页面"""
        counter_id = item.data(Qt.UserRole)
        self.manager.set_active(counter_id)
        self.manager.save_counters()  # 切换计数器后保存
        
        # 同步童话事件提示计数
        active_counter = self.manager.get_active()
        if hasattr(self, 'game_capture') and self.game_capture and active_counter:
            self.game_capture.set_nightmare_count(active_counter.nightmare_count)
        
        # 切换到计数模式(详情页)
        self.content_stack.setCurrentIndex(1)
        self._refresh_all()
    
    def on_counter_selected(self, row):
        """点击计数器列表项时切换页面(保留兼容)"""
        if row >= 0:
            counter_id = self.counter_list_widget.item(row).data(Qt.UserRole)
            self.manager.set_active(counter_id)
            self.manager.save_counters()  # 切换计数器后保存
            
            # 同步童话事件提示计数
            active_counter = self.manager.get_active()
            if hasattr(self, 'game_capture') and self.game_capture and active_counter:
                self.game_capture.set_nightmare_count(active_counter.nightmare_count)
            
            # 切换到计数模式(详情页)
            self.content_stack.setCurrentIndex(1)
            self._refresh_all()

    def on_counter_context_menu(self, pos):
        item = self.counter_list_widget.itemAt(pos)
        if not item:
            return
        counter_id = item.data(Qt.UserRole)
        menu = QMenu()
        rename_action = menu.addAction("重命名")
        delete_action = menu.addAction("删除")
        pin_action = menu.addAction("置顶")
        export_action = menu.addAction("导出童话事件统计")
        action = menu.exec(self.counter_list_widget.mapToGlobal(pos))
        if action == rename_action:
            self.rename_counter(counter_id)
        elif action == delete_action:
            self.delete_counter(counter_id)
        elif action == pin_action:
            self.toggle_pin(counter_id)
        elif action == export_action:
            self.export_battle_stats(counter_id)

    def rename_counter(self, counter_id):
        counter = next((c for c in self.manager.counters if c.id == counter_id), None)
        if counter:
            new_name, ok = QInputDialog.getText(self, "重命名", "新名称:", text=counter.counter_name)
            if ok and new_name:
                self.manager.rename_counter(counter_id, new_name)
                self.manager.save_counters()  # 重命名后保存
                self._refresh_all()

    def delete_counter(self, counter_id):
        """删除计数器（带确认对话框）"""
        counter = next((c for c in self.manager.counters if c.id == counter_id), None)
        if not counter:
            return
        
        # 二次确认
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除计数器【{counter.counter_name}】吗？\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        if len(self.manager.counters) <= 1:
            QMessageBox.warning(self, "警告", "至少保留一个计数器！")
            return
        
        self.manager.delete_counter(counter_id)
        self.manager.save_counters()  # 删除后立即保存
        
        # 重置童话事件提示计数
        if hasattr(self, 'game_capture') and self.game_capture:
            self.game_capture.reset_nightmare_count()
        
        self._refresh_all()

    def toggle_pin(self, counter_id):
        self.manager.toggle_pin(counter_id)
        self.manager.save_counters()  # 置顶后立即保存
        self._refresh_all()
    
    def export_battle_stats(self, counter_id):
        """导出童话事件期间精灵统计（支持多种格式）"""
        from PySide6.QtWidgets import (QFileDialog, QDialog, QVBoxLayout, QHBoxLayout, 
                                      QCheckBox, QDialogButtonBox, QLabel, QGroupBox, 
                                      QPushButton)
        import json
        
        counter = next((c for c in self.manager.counters if c.id == counter_id), None)
        if not counter:
            QMessageBox.warning(self, "警告", "未找到计数器")
            return
        
        # 检查是否有统计数据
        if not counter.battle_pokemon_stats:
            QMessageBox.information(self, "提示", "当前没有童话事件期间的精灵统计数据")
            return
        
        # 加载精灵数据库（优先使用完整数据库）
        pokemon_db = {}
        
        # 首先加载完整精灵数据库（包含所有300+只精灵）
        full_db_file = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "pokemon_data.json")
        if os.path.exists(full_db_file):
            try:
                with open(full_db_file, 'r', encoding='utf-8') as f:
                    db_data = json.load(f)
                    for item in db_data:
                        if 'name' in item and item['name'] not in pokemon_db:
                            attr = item.get('attribute', '')
                            if attr:
                                types = [t.strip() + "系" for t in attr.split('/') if t.strip()]
                                pokemon_db[item['name']] = types
                            else:
                                pokemon_db[item['name']] = []
                logger.log(f"已加载完整精灵数据库: {len(pokemon_db)} 只精灵")
            except Exception as e:
                logger.log(f"加载完整精灵数据库失败 {full_db_file}: {e}")
        
        # 然后加载计数器专用数据库（补充或覆盖）
        db_files = [
            os.path.join(os.path.dirname(__file__), "..", "core", "pokemon_database.json"),
            os.path.join(os.path.dirname(__file__), "..", "core", "pokemon_database_s2.json")
        ]
        
        for db_file in db_files:
            try:
                with open(db_file, 'r', encoding='utf-8') as f:
                    db_data = json.load(f)
                    for item in db_data:
                        if item['name'] not in pokemon_db:
                            pokemon_db[item['name']] = item.get('types', [])
            except Exception as e:
                logger.log(f"加载精灵数据库失败 {db_file}: {e}")
        
        # 添加模糊匹配辅助函数
        def find_pokemon_type(pokemon_name, db):
            """查找精灵属性，支持简称匹配全名"""
            # 1. 精确匹配
            if pokemon_name in db:
                return db[pokemon_name]
            
            # 2. 模糊匹配：OCR识别的名称可能是简称或全名的一部分
            for full_name, types in db.items():
                # 检查是否OCR识别的名称是数据库名称的开头或包含关系
                if full_name.startswith(pokemon_name) or pokemon_name.startswith(full_name.replace('（', '(').replace('）', ')')):
                    return types
                # 处理中文括号变体
                full_name_simple = full_name.replace('（', '(').replace('）', ')')
                if full_name_simple.startswith(pokemon_name):
                    return types
            
            # 3. 从计数器列表中查找
            for c in self.manager.counters:
                if c.pokemon_name == pokemon_name:
                    return c.type.split('、') if c.type and c.type != "未知" else []
            
            return None  # 返回None表示未找到
        
        # 创建导出格式选择对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("导出童话事件统计")
        dialog.setFixedSize(500, 320)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 提示文字
        hint_label = QLabel("请选择要导出的格式（可多选）：")
        hint_label.setStyleSheet("color: #e2e8f0; font-size: 14px; padding-bottom: 8px;")
        layout.addWidget(hint_label)
        
        # 导出格式选项
        export_format_group = QGroupBox("导出格式")
        export_format_layout = QVBoxLayout(export_format_group)
        export_format_layout.setSpacing(8)
        export_format_layout.setContentsMargins(15, 8, 15, 8)
        
        export_txt_checkbox = QCheckBox("纯文本报告 (.txt)")
        export_txt_checkbox.setChecked(True)
        export_txt_checkbox.setStyleSheet("color: #e2e8f0; font-size: 13px; padding: 3px 0;")
        export_format_layout.addWidget(export_txt_checkbox)
        
        export_png_checkbox = QCheckBox("PNG图片（四个图表）")
        export_png_checkbox.setStyleSheet("color: #e2e8f0; font-size: 13px; padding: 3px 0;")
        export_format_layout.addWidget(export_png_checkbox)
        
        export_html_checkbox = QCheckBox("HTML图表（可在浏览器中打开）")
        export_html_checkbox.setStyleSheet("color: #e2e8f0; font-size: 13px; padding: 3px 0;")
        export_format_layout.addWidget(export_html_checkbox)
        
        layout.addWidget(export_format_group)
        
        # 全选/取消按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        select_all_btn = QPushButton("全选")
        deselect_all_btn = QPushButton("取消全选")
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        def select_all():
            export_txt_checkbox.setChecked(True)
            export_png_checkbox.setChecked(True)
            export_html_checkbox.setChecked(True)
        
        def deselect_all():
            export_txt_checkbox.setChecked(False)
            export_png_checkbox.setChecked(False)
            export_html_checkbox.setChecked(False)
        
        select_all_btn.clicked.connect(select_all)
        deselect_all_btn.clicked.connect(deselect_all)
        
        # 确定/取消按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() != QDialog.Accepted:
            return
        
        # 检查是否选择了任何导出格式
        if not any([export_txt_checkbox.isChecked(), 
                   export_png_checkbox.isChecked(), 
                   export_html_checkbox.isChecked()]):
            QMessageBox.warning(self, "提示", "请至少选择一种导出格式")
            return
        
        # 选择保存路径（使用QFileDialog实例设置defaultSuffix，避免Win11将输入解释为目录）
        dlg = QFileDialog(self, "选择保存位置", f"{counter.pokemon_name}_童话事件统计")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        dlg.setDefaultSuffix("html")
        dlg.setFileMode(QFileDialog.AnyFile)
        if dlg.exec() != QDialog.Accepted:
            return
        base_path = dlg.selectedFiles()[0]
        if not base_path:
            return
        
        # 移除扩展名（如果有），但保留路径为文件路径
        # 确保即使没有扩展名也被视为文件，避免Qt在某些版本中将其解释为目录
        if '.' in base_path:
            base_path = base_path.rsplit('.', 1)[0]
        # 检查路径是否以目录分隔符结尾（表示Qt将其解释为目录）
        if base_path and (base_path.endswith('/') or base_path.endswith('\\')):
            # 如果被解释为目录，使用默认文件名
            base_path = os.path.join(base_path, f"{counter.pokemon_name}_童话事件统计")
        
        try:
            # 计算总次数
            total_count = sum(counter.battle_pokemon_stats.values())
            
            # 按出现次数排序
            sorted_pokemons = sorted(
                counter.battle_pokemon_stats.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # 获取精灵属性信息
            pokemon_info = []
            for pokemon_name, count in sorted_pokemons:
                percentage = (count / total_count * 100) if total_count > 0 else 0
                
                # 从数据库中查找精灵属性（使用模糊匹配）
                types = find_pokemon_type(pokemon_name, pokemon_db)
                if types:
                    pokemon_type = "、".join(types)
                else:
                    pokemon_type = "未知"
                
                pokemon_info.append({
                    'name': pokemon_name,
                    'count': count,
                    'percentage': percentage,
                    'type': pokemon_type
                })
            
            exported_files = []
            
            # 导出文本报告
            if export_txt_checkbox.isChecked():
                txt_path = self._export_txt_report(pokemon_info, counter, base_path)
                if txt_path:
                    exported_files.append(txt_path)
            
            # 导出PNG图片（四个图表）
            if export_png_checkbox.isChecked():
                png_files = self._export_png_charts(pokemon_info, counter, base_path)
                exported_files.extend(png_files)
            
            # 导出交互式HTML
            if export_html_checkbox.isChecked():
                html_path = self._export_interactive_html(pokemon_info, counter, base_path)
                if html_path:
                    exported_files.append(html_path)
            
            # 显示成功消息
            if exported_files:
                QMessageBox.information(
                    self,
                    "导出成功",
                    f"童话事件统计已导出到:\n{chr(10).join(exported_files)}\n\n共统计 {len(pokemon_info)} 种精灵，{total_count} 次出现"
                )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "导出失败",
                f"导出过程中发生错误:\n{str(e)}"
            )
            import traceback
            traceback.print_exc()
    
    def _get_type_color(self, type_name):
        """根据属性名称获取对应的颜色（RGB元组）- 统一使用pokemon_types.py"""
        return get_type_color(type_name)
    
    def _export_txt_report(self, pokemon_info, counter, base_path):
        """导出纯文本报告"""
        try:
            content = []
            content.append("=" * 60)
            content.append("童话事件统计报告")
            content.append("=" * 60)
            content.append("")
            content.append(f"计数器名称: {counter.counter_name}")
            content.append(f"精灵名称: {counter.pokemon_name}")
            content.append(f"属性: {counter.type}")
            content.append(f"童话事件次数: {counter.count}")
            content.append(f"保底上限: {counter.target}")
            content.append("")
            content.append("-" * 60)
            content.append("战斗期间出现的精灵统计")
            content.append("-" * 60)
            content.append("")
            
            total_count = sum(info['count'] for info in pokemon_info)
            content.append(f"总计识别到 {total_count} 次精灵")
            content.append("")
            
            for idx, info in enumerate(pokemon_info, 1):
                content.append(f"{idx}. {info['name']}")
                content.append(f"   出现次数: {info['count']} 次")
                content.append(f"   占比: {info['percentage']:.2f}%")
                content.append(f"   属性: {info['type']}")
                content.append("")
            
            content.append("")
            content.append("=" * 60)
            content.append("统计结束")
            content.append("=" * 60)
            
            txt_path = f"{base_path}.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            logger.log(f"已导出文本报告: {txt_path}")
            return txt_path
        except Exception as e:
            logger.log(f"导出文本报告失败: {e}")
            return None
    
    def _export_png_charts(self, pokemon_info, counter, base_path):
        """导出PNG图片（四个图表：精灵柱状图、精灵饼图、属性柱状图、属性饼图）"""
        exported_files = []
        
        try:
            from PIL import Image, ImageDraw, ImageFont
            import math
            
            # 颜色配置
            colors = [
                (124, 58, 237), (168, 85, 247), (192, 132, 252), (216, 180, 254), (233, 213, 255),
                (5, 150, 105), (16, 185, 129), (52, 211, 153), (110, 231, 183), (167, 243, 208),
                (245, 158, 11), (239, 68, 68), (59, 130, 246), (139, 92, 246), (236, 72, 153),
                (255, 107, 107), (78, 205, 196), (149, 225, 211), (254, 202, 87), (248, 181, 0)
            ]
            
            # 统计属性占比
            type_stats = {}
            for info in pokemon_info:
                if info['type'] != "未知":
                    for t in info['type'].split('、'):
                        t = t.strip()
                        if t:
                            type_stats[t] = type_stats.get(t, 0) + info['count']
            
            sorted_types = sorted(type_stats.items(), key=lambda x: x[1], reverse=True)
            type_names = [t[0] for t in sorted_types]
            type_counts = [t[1] for t in sorted_types]
            
            # 为精灵柱状图准备属性颜色
            pokemon_colors = []
            for info in pokemon_info:
                type_name = info['type'].split('、')[0].strip() if info['type'] != "未知" else "未知"
                pokemon_colors.append(self._get_type_color(type_name))
            
            # 为属性柱状图准备属性颜色
            type_colors = [self._get_type_color(t) for t in type_names]
            
            # 生成四个图表
            # 1. 精灵柱状图（按属性分配颜色
            bar1_path = f"{base_path}_精灵出现次数统计_柱状图.png"
            self._draw_bar_chart(pokemon_info, counter.pokemon_name, "精灵名称", "出现次数", 
                               bar1_path, pokemon_colors, title="精灵出现次数统计（柱状图）")
            if self._validate_image(bar1_path):
                exported_files.append(bar1_path)
                logger.log(f"已导出精灵柱状图: {bar1_path}")
            
            # 2. 精灵饼图（显示所有精灵）
            pie1_path = f"{base_path}_精灵出现占比_饼图.png"
            self._draw_pie_chart(pokemon_info, counter.pokemon_name, pie1_path, colors, 
                               title="精灵出现占比（饼图）")
            if self._validate_image(pie1_path):
                exported_files.append(pie1_path)
                logger.log(f"已导出精灵饼图: {pie1_path}")
            
            # 3. 属性柱状图（按属性分配颜色
            if type_names:
                bar2_path = f"{base_path}_属性出现次数统计_柱状图.png"
                self._draw_type_bar_chart(type_names, type_counts, counter.pokemon_name, 
                                         bar2_path, type_colors, title="属性出现次数统计（柱状图）")
                if self._validate_image(bar2_path):
                    exported_files.append(bar2_path)
                    logger.log(f"已导出属性柱状图: {bar2_path}")
            
            # 4. 属性饼图
            if type_names:
                pie2_path = f"{base_path}_属性出现占比_饼图.png"
                self._draw_type_pie_chart(type_names, type_counts, counter.pokemon_name, 
                                         pie2_path, colors, title="属性出现占比（饼图）")
                if self._validate_image(pie2_path):
                    exported_files.append(pie2_path)
                    logger.log(f"已导出属性饼图: {pie2_path}")
            
        except Exception as e:
            logger.log(f"导出PNG图片失败: {e}")
            import traceback
            traceback.print_exc()
        
        return exported_files
    
    def _draw_bar_chart(self, data, title_prefix, x_label, y_label, output_path, colors, title):
        """使用PIL绘制柱状图（支持按属性分配颜色）"""
        from PIL import Image, ImageDraw, ImageFont
        
        # 计算图表尺寸
        padding = 60
        bar_width = 40
        max_name_len = max(len(item['name']) for item in data)
        num_items = len(data)
        
        # 根据数据量调整宽度
        chart_width = max(800, num_items * (bar_width + 15) + padding * 2 + max_name_len * 12)
        chart_height = 500
        
        # 创建图片
        img = Image.new('RGB', (chart_width, chart_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # 加载字体
        try:
            font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 12)
            title_font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 16)
        except:
            font = ImageFont.load_default()
            title_font = font
        
        # 获取文本尺寸的辅助函数
        def get_text_size(text, font_obj):
            """获取文本尺寸（兼容新旧版本PIL）"""
            try:
                # PIL 10+ 使用 textlength 和 getmetrics
                width = draw.textlength(text, font=font_obj)
                ascent, descent = font_obj.getmetrics()
                return (width, ascent + descent)
            except AttributeError:
                # 旧版PIL
                return draw.textsize(text, font=font_obj)
        
        # 绘制标题
        title_text = f"{title_prefix} - {title}"
        title_w, title_h = get_text_size(title_text, title_font)
        draw.text(((chart_width - title_w) // 2, 20), title_text, fill=(0, 0, 0), font=title_font)
        
        # 计算数据范围
        max_count = max(item['count'] for item in data) if data else 1
        
        # 绘制坐标轴
        draw.line([(padding, padding + 30), (padding, chart_height - padding)], fill=(100, 100, 100), width=2)
        draw.line([(padding, chart_height - padding), (chart_width - padding, chart_height - padding)], fill=(100, 100, 100), width=2)
        
        # 绘制Y轴刻度
        y_ticks = 5
        for i in range(y_ticks + 1):
            value = int(max_count * (i / y_ticks))
            y = chart_height - padding - (i / y_ticks) * (chart_height - padding * 2 - 30)
            draw.text((padding - 50, y - 8), str(value), fill=(80, 80, 80), font=font)
            draw.line([(padding - 5, y), (padding, y)], fill=(150, 150, 150))
        
        # 绘制柱状图
        start_x = padding + 30
        for i, item in enumerate(data):
            x = start_x + i * (bar_width + 15)
            bar_height = (item['count'] / max_count) * (chart_height - padding * 2 - 30)
            y = chart_height - padding - bar_height
            
            # 获取柱子颜色（根据精灵属性或直接使用颜色数组）
            if isinstance(colors, list):
                color = colors[i % len(colors)]
            else:
                color = colors
            
            # 绘制柱子
            draw.rectangle([(x, y), (x + bar_width, chart_height - padding)], fill=color)
            
            # 绘制数值标签
            num_text = str(item['count'])
            num_w, num_h = get_text_size(num_text, font)
            draw.text((x + (bar_width - num_w) // 2, y - 20), num_text, fill=(50, 50, 50), font=font)
            
            # 绘制X轴标签
            name_text = item['name']
            draw.text((x - 10, chart_height - padding + 10), name_text, fill=(50, 50, 50), font=font)
        
        # 保存图片
        img.save(output_path, 'PNG')
    
    def _draw_pie_chart(self, data, title_prefix, output_path, colors, title):
        """使用PIL绘制饼图（显示所有数据）"""
        from PIL import Image, ImageDraw, ImageFont
        import math
        
        size = 500
        center = size // 2
        radius = 180
        
        img = Image.new('RGB', (size, size), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # 加载字体
        try:
            font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 11)
            title_font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 16)
        except:
            font = ImageFont.load_default()
            title_font = font
        
        # 获取文本尺寸的辅助函数
        def get_text_size(text, font_obj):
            try:
                width = draw.textlength(text, font=font_obj)
                ascent, descent = font_obj.getmetrics()
                return (width, ascent + descent)
            except AttributeError:
                return draw.textsize(text, font=font_obj)
        
        # 绘制标题
        title_text = f"{title_prefix} - {title}"
        title_w, title_h = get_text_size(title_text, title_font)
        draw.text(((size - title_w) // 2, 20), title_text, fill=(0, 0, 0), font=title_font)
        
        # 计算总数
        total = sum(item['count'] for item in data)
        if total == 0:
            draw.text((center - 50, center - 10), "无数据", fill=(150, 150, 150), font=font)
            img.save(output_path, 'PNG')
            return
        
        # 绘制饼图
        start_angle = -90  # 从顶部开始
        legend_y = 350
        legend_x = 50
        
        for i, item in enumerate(data):
            angle = (item['count'] / total) * 360
            end_angle = start_angle + angle
            
            # 转换角度为弧度
            start_rad = math.radians(start_angle)
            end_rad = math.radians(end_angle)
            
            # 计算扇形路径
            x1 = center + radius * math.cos(start_rad)
            y1 = center + radius * math.sin(start_rad)
            x2 = center + radius * math.cos(end_rad)
            y2 = center + radius * math.sin(end_rad)
            
            # 绘制扇形
            color = colors[i % len(colors)]
            draw.pieslice([(center - radius, center - radius), 
                          (center + radius, center + radius)], 
                         start_angle, end_angle, fill=color)
            
            # 绘制图例
            legend_color_box = (legend_x, legend_y + i * 25, legend_x + 20, legend_y + i * 25 + 15)
            draw.rectangle(legend_color_box, fill=color)
            
            # 图例文字：名称 (百分比)
            percentage = (item['count'] / total * 100)
            legend_text = f"{item['name']} ({percentage:.1f}%)"
            draw.text((legend_x + 25, legend_y + i * 25), legend_text, fill=(30, 30, 30), font=font)
            
            start_angle = end_angle
        
        # 保存图片
        img.save(output_path, 'PNG')
    
    def _draw_type_bar_chart(self, names, counts, title_prefix, output_path, colors, title):
        """绘制属性柱状图（支持按属性分配颜色）"""
        from PIL import Image, ImageDraw, ImageFont
        
        padding = 60
        bar_width = 50
        num_items = len(names)
        
        chart_width = max(600, num_items * (bar_width + 20) + padding * 2)
        chart_height = 400
        
        img = Image.new('RGB', (chart_width, chart_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 12)
            title_font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 16)
        except:
            font = ImageFont.load_default()
            title_font = font
        
        # 获取文本尺寸的辅助函数
        def get_text_size(text, font_obj):
            try:
                width = draw.textlength(text, font=font_obj)
                ascent, descent = font_obj.getmetrics()
                return (width, ascent + descent)
            except AttributeError:
                return draw.textsize(text, font=font_obj)
        
        # 绘制标题
        title_text = f"{title_prefix} - {title}"
        title_w, title_h = get_text_size(title_text, title_font)
        draw.text(((chart_width - title_w) // 2, 20), title_text, fill=(0, 0, 0), font=title_font)
        
        max_count = max(counts) if counts else 1
        
        # 绘制坐标轴
        draw.line([(padding, padding + 30), (padding, chart_height - padding)], fill=(100, 100, 100), width=2)
        draw.line([(padding, chart_height - padding), (chart_width - padding, chart_height - padding)], fill=(100, 100, 100), width=2)
        
        # Y轴刻度
        y_ticks = 5
        for i in range(y_ticks + 1):
            value = int(max_count * (i / y_ticks))
            y = chart_height - padding - (i / y_ticks) * (chart_height - padding * 2 - 30)
            draw.text((padding - 40, y - 8), str(value), fill=(80, 80, 80), font=font)
        
        # 绘制柱子
        start_x = padding + 30
        for i, (name, count) in enumerate(zip(names, counts)):
            x = start_x + i * (bar_width + 20)
            bar_height = (count / max_count) * (chart_height - padding * 2 - 30)
            y = chart_height - padding - bar_height
            
            # 获取柱子颜色（按属性或使用颜色数组
            if isinstance(colors, list):
                color = colors[i % len(colors)]
            else:
                color = colors
            
            draw.rectangle([(x, y), (x + bar_width, chart_height - padding)], fill=color)
            
            num_text = str(count)
            num_w, num_h = get_text_size(num_text, font)
            draw.text((x + (bar_width - num_w) // 2, y - 20), num_text, fill=(50, 50, 50), font=font)
            
            name_w, _ = get_text_size(name, font)
            draw.text((x + (bar_width - name_w) // 2, 
                      chart_height - padding + 10), name, fill=(50, 50, 50), font=font)
        
        img.save(output_path, 'PNG')
    
    def _draw_type_pie_chart(self, names, counts, title_prefix, output_path, colors, title):
        """绘制属性饼图"""
        from PIL import Image, ImageDraw, ImageFont
        import math
        
        size = 450
        center = size // 2
        radius = 160
        
        img = Image.new('RGB', (size, size), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 12)
            title_font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 16)
        except:
            font = ImageFont.load_default()
            title_font = font
        
        # 获取文本尺寸的辅助函数
        def get_text_size(text, font_obj):
            try:
                width = draw.textlength(text, font=font_obj)
                ascent, descent = font_obj.getmetrics()
                return (width, ascent + descent)
            except AttributeError:
                return draw.textsize(text, font=font_obj)
        
        title_text = f"{title_prefix} - {title}"
        title_w, title_h = get_text_size(title_text, title_font)
        draw.text(((size - title_w) // 2, 20), title_text, fill=(0, 0, 0), font=title_font)
        
        total = sum(counts)
        if total == 0:
            draw.text((center - 50, center - 10), "无数据", fill=(150, 150, 150), font=font)
            img.save(output_path, 'PNG')
            return
        
        start_angle = -90
        legend_y = 320
        legend_x = 40
        
        for i, (name, count) in enumerate(zip(names, counts)):
            angle = (count / total) * 360
            end_angle = start_angle + angle
            
            start_rad = math.radians(start_angle)
            end_rad = math.radians(end_angle)
            
            color = colors[i % len(colors)]
            draw.pieslice([(center - radius, center - radius), 
                          (center + radius, center + radius)], 
                         start_angle, end_angle, fill=color)
            
            legend_color_box = (legend_x, legend_y + i * 22, legend_x + 18, legend_y + i * 22 + 13)
            draw.rectangle(legend_color_box, fill=color)
            
            percentage = (count / total * 100)
            legend_text = f"{name} ({percentage:.1f}%)"
            draw.text((legend_x + 22, legend_y + i * 22), legend_text, fill=(30, 30, 30), font=font)
            
            start_angle = end_angle
        
        img.save(output_path, 'PNG')
    
    def _export_interactive_html(self, pokemon_info, counter, base_path):
        """导出交互式HTML（支持在浏览器中打开）"""
        try:
            import json
            
            total_count = sum(info['count'] for info in pokemon_info)
            
            # 统计数据
            pokemon_data = []
            for info in pokemon_info:
                pokemon_data.append({
                    'name': info['name'],
                    'count': info['count'],
                    'percentage': round(info['percentage'], 2),
                    'type': info['type']
                })
            
            # 属性统计数据
            type_stats = {}
            for info in pokemon_info:
                if info['type'] != "未知":
                    for t in info['type'].split('、'):
                        t = t.strip()
                        if t:
                            type_stats[t] = type_stats.get(t, 0) + info['count']
            
            type_data = []
            if type_stats:
                sorted_types = sorted(type_stats.items(), key=lambda x: x[1], reverse=True)
                total_type_count = sum(type_stats.values())
                for t_name, t_count in sorted_types:
                    type_data.append({
                        'name': t_name,
                        'count': t_count,
                        'percentage': round((t_count / total_type_count * 100), 2) if total_type_count > 0 else 0
                    })
            
            # 为HTML图表准备颜色
            def rgb_to_hex(rgb):
                """将RGB元组转换为HEX颜色字符串"""
                return f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
            
            # 精灵柱状图颜色
            pokemon_hex_colors = []
            for info in pokemon_info:
                type_name = info['type'].split('、')[0].strip() if info['type'] != "未知" else "未知"
                color_rgb = self._get_type_color(type_name)
                pokemon_hex_colors.append(rgb_to_hex(color_rgb))
            
            # 属性柱状图颜色
            type_hex_colors = []
            for t_data in type_data:
                color_rgb = self._get_type_color(t_data['name'])
                type_hex_colors.append(rgb_to_hex(color_rgb))
            
            # 生成HTML内容
            html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>童话事件统计 - {counter.pokemon_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft YaHei', 'PingFang SC', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 28px;
        }}
        .stats-header {{
            display: flex;
            justify-content: space-around;
            margin-bottom: 30px;
            flex-wrap: wrap;
            gap: 20px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 40px;
            border-radius: 15px;
            text-align: center;
            min-width: 200px;
        }}
        .stat-card h3 {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 10px;
        }}
        .stat-card .value {{
            font-size: 32px;
            font-weight: bold;
        }}
        .charts-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
            margin-top: 30px;
        }}
        .chart-section {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
        }}
        .chart-section h2 {{
            text-align: center;
            color: #333;
            margin-bottom: 20px;
            font-size: 20px;
        }}
        .chart-wrapper {{
            position: relative;
            height: 400px;
        }}
        .table-section {{
            margin-top: 30px;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
        }}
        .table-section h2 {{
            text-align: center;
            color: #333;
            margin-bottom: 20px;
            font-size: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        tr:hover {{
            background: #f0f0f0;
        }}
        .type-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            margin: 2px;
        }}
        .type-fire {{ background: #ff6b6b; color: white; }}
        .type-water {{ background: #4ecdc4; color: white; }}
        .type-grass {{ background: #95e1d3; color: #333; }}
        .type-electric {{ background: #feca57; color: #333; }}
        .type-ice {{ background: #a8e6cf; color: #333; }}
        .type-fighting {{ background: #ff8a5c; color: white; }}
        .type-poison {{ background: #c44569; color: white; }}
        .type-ground {{ background: #d4a373; color: white; }}
        .type-flying {{ background: #a8d8ea; color: #333; }}
        .type-psychic {{ background: #f8b500; color: #333; }}
        .type-bug {{ background: #26de81; color: white; }}
        .type-rock {{ background: #778beb; color: white; }}
        .type-ghost {{ background: #786fa6; color: white; }}
        .type-dragon {{ background: #fd79a8; color: white; }}
        .type-dark {{ background: #2d3436; color: white; }}
        .type-steel {{ background: #b2bec3; color: #333; }}
        .type-fairy {{ background: #fd79a8; color: white; }}
        .type-normal {{ background: #dfe6e9; color: #333; }}
        .type-light {{ background: #ffeaa7; color: #333; }}
        .type-evil {{ background: #636e72; color: white; }}
        .type-mach {{ background: #b2bec3; color: #333; }}
        .type-none {{ background: #ddd; color: #333; }}
        @media (max-width: 768px) {{
            .charts-container {{
                grid-template-columns: 1fr;
            }}
            .stat-card {{
                min-width: 150px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{counter.pokemon_name} - 童话事件统计报告</h1>
        
        <div class="stats-header">
            <div class="stat-card">
                <h3>童话事件次数</h3>
                <div class="value">{counter.count}</div>
            </div>
            <div class="stat-card">
                <h3>识别精灵种类</h3>
                <div class="value">{len(pokemon_data)}</div>
            </div>
            <div class="stat-card">
                <h3>总识别次数</h3>
                <div class="value">{total_count}</div>
            </div>
            <div class="stat-card">
                <h3>保底上限</h3>
                <div class="value">{counter.target}</div>
            </div>
        </div>

        <!-- 精灵统计图表 -->
        <div class="charts-container">
            <div class="chart-section">
                <h2>精灵出现次数统计（柱状图）</h2>
                <div class="chart-wrapper">
                    <canvas id="pokemonBarChart"></canvas>
                </div>
            </div>
            <div class="chart-section">
                <h2>精灵出现占比（饼图）</h2>
                <div class="chart-wrapper">
                    <canvas id="pokemonPieChart"></canvas>
                </div>
            </div>
        </div>

        <!-- 属性统计图表 -->
        <div class="charts-container">
            <div class="chart-section">
                <h2>属性出现次数统计（柱状图）</h2>
                <div class="chart-wrapper">
                    <canvas id="typeBarChart"></canvas>
                </div>
            </div>
            <div class="chart-section">
                <h2>属性出现占比（饼图）</h2>
                <div class="chart-wrapper">
                    <canvas id="typePieChart"></canvas>
                </div>
            </div>
        </div>

        <!-- 详细数据表格 -->
        <div class="table-section">
            <h2>详细统计数据</h2>
            <table>
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>精灵名称</th>
                        <th>出现次数</th>
                        <th>占比</th>
                        <th>属性</th>
                    </tr>
                </thead>
                <tbody>
'''
            
            for idx, info in enumerate(pokemon_data, 1):
                type_badges = ''
                if info['type'] != "未知":
                    for t in info['type'].split('、'):
                        t = t.strip()
                        if t:
                            type_class = self._get_type_css_class(t)
                            type_badges += f'<span class="type-badge {type_class}">{t}</span>'
                else:
                    type_badges = '<span class="type-badge type-none">未知</span>'
                
                html_content += f'''
                    <tr>
                        <td>{idx}</td>
                        <td><strong>{info['name']}</strong></td>
                        <td>{info['count']}</td>
                        <td>{info['percentage']}%</td>
                        <td>{type_badges}</td>
                    </tr>
'''
            
            html_content += '''
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // 精灵数据
        const pokemonData = ''' + json.dumps(pokemon_data, ensure_ascii=False) + ''';
        // 属性数据
        const typeData = ''' + json.dumps(type_data, ensure_ascii=False) + ''';
        // 精灵颜色
        const pokemonColors = ''' + json.dumps(pokemon_hex_colors, ensure_ascii=False) + ''';
        // 属性颜色
        const typeColors = ''' + json.dumps(type_hex_colors, ensure_ascii=False) + ''';
        
        document.addEventListener('DOMContentLoaded', function() {
            // 精灵柱状图
            const pokemonBarCtx = document.getElementById('pokemonBarChart');
            if (pokemonBarCtx) {
                new Chart(pokemonBarCtx, {
                    type: 'bar',
                    data: {
                        labels: pokemonData.map(p => p.name),
                        datasets: [{
                            label: '出现次数',
                            data: pokemonData.map(p => p.count),
                            backgroundColor: pokemonColors,
                            borderRadius: 5,
                            borderSkipped: false
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            x: {
                                ticks: {
                                    maxRotation: 45,
                                    minRotation: 45,
                                    font: { size: 11 }
                                }
                            },
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    stepSize: 1
                                }
                            }
                        }
                    }
                });
            }
            
            // 精灵饼图（显示所有精灵）
            const pokemonPieCtx = document.getElementById('pokemonPieChart');
            if (pokemonPieCtx) {
                new Chart(pokemonPieCtx, {
                    type: 'pie',
                    data: {
                        labels: pokemonData.map(p => p.name),
                        datasets: [{
                            data: pokemonData.map(p => p.count),
                            backgroundColor: pokemonColors,
                            borderWidth: 2,
                            borderColor: '#fff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'right',
                                labels: {
                                    padding: 15,
                                    usePointStyle: true,
                                    font: { size: 11 }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        let value = context.raw;
                                        let total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        let percentage = ((value / total) * 100).toFixed(1);
                                        return `出现 ${value} 次 (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            }
            
            // 属性柱状图
            const typeBarCtx = document.getElementById('typeBarChart');
            if (typeBarCtx && typeData.length > 0) {
                new Chart(typeBarCtx, {
                    type: 'bar',
                    data: {
                        labels: typeData.map(t => t.name),
                        datasets: [{
                            label: '出现次数',
                            data: typeData.map(t => t.count),
                            backgroundColor: typeColors,
                            borderRadius: 5,
                            borderSkipped: false
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            x: {
                                ticks: {
                                    font: { size: 12 }
                                }
                            },
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    stepSize: 1
                                }
                            }
                        }
                    }
                });
            }
            
            // 属性饼图
            const typePieCtx = document.getElementById('typePieChart');
            if (typePieCtx && typeData.length > 0) {
                new Chart(typePieCtx, {
                    type: 'pie',
                    data: {
                        labels: typeData.map(t => t.name),
                        datasets: [{
                            data: typeData.map(t => t.count),
                            backgroundColor: typeColors,
                            borderWidth: 2,
                            borderColor: '#fff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'right',
                                labels: {
                                    padding: 15,
                                    usePointStyle: true,
                                    font: { size: 12 }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        let value = context.raw;
                                        let total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        let percentage = ((value / total) * 100).toFixed(1);
                                        return `出现 ${value} 次 (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            }
        });
    </script>
</body>
</html>'''
            
            html_path = f"{base_path}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.log(f"已导出HTML图表: {html_path}")
            return html_path
            
        except Exception as e:
            logger.log(f"导出HTML图表失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_type_css_class(self, type_name):
        """获取属性对应的CSS类名"""
        type_map = {
            '火系': 'type-fire', '水系': 'type-water', '草系': 'type-grass',
            '电系': 'type-electric', '冰系': 'type-ice', '格斗系': 'type-fighting',
            '毒系': 'type-poison', '地系': 'type-ground', '飞行系': 'type-flying',
            '超能系': 'type-psychic', '虫系': 'type-bug', '岩石系': 'type-rock',
            '幽灵系': 'type-ghost', '龙系': 'type-dragon', '恶系': 'type-dark',
            '机械系': 'type-mach', '光系': 'type-light', '萌系': 'type-normal',
            '普通系': 'type-normal', '幻系': 'type-phantom'
        }
        return type_map.get(type_name, 'type-none')
    
    def _validate_image(self, image_path):
        """验证图片是否正确生成"""
        try:
            if not os.path.exists(image_path):
                logger.log(f"图片验证失败: 文件不存在 {image_path}")
                return False
            
            # 检查文件大小（最小应该大于1KB）
            file_size = os.path.getsize(image_path)
            if file_size < 1024:
                logger.log(f"图片验证失败: 文件过小 {file_size} bytes - {image_path}")
                return False
            
            # 使用PIL验证图片格式和内容
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    # 检查图片格式
                    if img.format != 'PNG':
                        logger.log(f"图片验证失败: 格式不正确 {img.format} - {image_path}")
                        return False
                    
                    # 检查图片尺寸
                    width, height = img.size
                    if width < 100 or height < 100:
                        logger.log(f"图片验证失败: 分辨率过低 {width}x{height} - {image_path}")
                        return False
                    
                    # 检查图片是否为空（全是透明或白色）
                    extrema = img.convert('L').getextrema()
                    if extrema[0] == extrema[1]:
                        logger.log(f"图片验证失败: 图片内容为空 - {image_path}")
                        return False
                
                logger.log(f"图片验证通过: {width}x{height}, {file_size} bytes - {image_path}")
                return True
                
            except ImportError:
                # 如果没有PIL，仅检查文件大小
                logger.log(f"图片验证（基础）: {file_size} bytes - {image_path}")
                return file_size > 1024
            
        except Exception as e:
            logger.log(f"图片验证异常: {e} - {image_path}")
            return False
    
    def on_save_counter_edit(self):
        """保存计数器修改"""
        active = self.manager.get_active()
        if not active:
            QMessageBox.warning(self, "警告", "请先选择一个计数器")
            return
        
        name = self.edit_name.text().strip()
        if not name:
            QMessageBox.warning(self, "警告", "请输入精灵名称")
            return
        
        # 更新数据
        old_name = active.pokemon_name
        active.pokemon_name = name
        # 同步更新计数器名称，保持一致性
        if active.counter_name == f"{old_name}计数器":
            active.counter_name = f"{name}计数器"
        
        # 组合属性（支持双属性）
        type1 = self.edit_type_1.currentText()
        type2 = self.edit_type_2.currentText()
        types = []
        if type1 != "请选择":
            types.append(type1)
        if type2 != "无" and type2 != "请选择":
            types.append(type2)
        active.type = "、".join(types) if types else ""
        
        try:
            active.target = int(self.edit_target.text())
        except:
            active.target = 80
        try:
            active.count = int(self.edit_wai.text())
        except:
            active.count = 0
        
        # 保存数据
        self.manager.save_counters()
        
        self._refresh_all()
        QMessageBox.information(self, "成功", "修改已保存！")
    
    def on_delete_current_counter(self):
        """删除当前计数器"""
        active = self.manager.get_active()
        if not active:
            QMessageBox.warning(self, "警告", "请先选择一个计数器")
            return
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除计数器【{active.pokemon_name}】吗？\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.delete_counter(active.id)
    
    def on_record_shiny(self):
        """记录本次出闪"""
        active = self.manager.get_active()
        if not active:
            QMessageBox.warning(self, "警告", "请先选择一个计数器")
            return
        
        reply = QMessageBox.question(
            self,
            "确认记录",
            f"确定要记录【{active.pokemon_name}】的本次出闪吗？\n当前童话事件计数: {active.count}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.manager.add_shiny_record(active.pokemon_name, active.count, True)
            QMessageBox.information(self, "成功", "出闪记录已保存！")
    
    def on_reset_counter(self):
        """重置当前计数器"""
        active = self.manager.get_active()
        if not active:
            QMessageBox.warning(self, "警告", "请先选择一个计数器")
            return
        
        reply = QMessageBox.question(
            self,
            "确认重置",
            f"确定要重置【{active.pokemon_name}】的计数器吗？\n当前计数和精灵出现数据将清零。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            active.count = 0
            active.nightmare_count = 0  # 清空童话事件提示计数
            active.battle_pokemon_stats = {}  # 清空童话事件精灵统计
            active.breakthrough_notified = False  # 重置保底通知标记
            # 同步重置 game_capture 的 nightmare_detected_count
            if hasattr(self, 'game_capture') and self.game_capture:
                self.game_capture.reset_nightmare_count()
            self.manager.save_counters()
            self._refresh_all()
            QMessageBox.information(self, "成功", "计数器已重置！")
    
    def load_settings_to_ui(self):
        """从设置管理器加载设置到UI"""
        # 通用设置
        self.minimize_tray_switch.setChecked(self.settings_manager.get("minimize_to_tray", False))
        self.desktop_pet_switch.setChecked(self.settings_manager.get("desktop_pet_enabled", False))
        
        # 识别设置
        self.recognition_interval_spin.setValue(self.settings_manager.get("recognition_interval", 500))
        self.confidence_xt_spin.setValue(self.settings_manager.get("recognition_confidence", 0.7))
        self.confidence_pollution_spin.setValue(self.settings_manager.get("confidence_pollution", 0.75))
        self.ocr_confidence_spin.setValue(self.settings_manager.get("ocr_confidence", 0.5))
        
        # 地图设置
        self.map_update_interval_spin.setValue(self.settings_manager.get("map_update_interval", 3))
        self.use_real_pointer_switch.setChecked(self.settings_manager.get("use_real_pointer", True))
        self.resource_icon_size_spin.setValue(self.settings_manager.get("resource_icon_size", 24))
        
        
        
        # 游戏窗口选择
        if hasattr(self, 'window_select_combo'):
            self._refresh_window_list()
        
        # 计数器设置
        self.default_target_spin.setValue(self.settings_manager.get("default_target", 80))
        self.auto_save_interval_spin.setValue(self.settings_manager.get("auto_save_interval", 5))
        self.auto_save_switch.setChecked(self.settings_manager.get("auto_save_progress", True))
        self.breakthrough_notification_switch.setChecked(self.settings_manager.get("breakthrough_notification", True))
        
        # 高级设置
        self.detailed_log_switch.toggled.connect(self.on_debug_toggled)
        self.performance_monitor_switch.setChecked(self.settings_manager.get("show_performance_monitor", False))
        self.performance_monitor_switch.toggled.connect(self._on_performance_monitor_toggled)
        self.performance_charts_switch.setChecked(self.settings_manager.get("show_performance_charts", True))
        self.performance_charts_switch.toggled.connect(self._on_performance_charts_toggled)
        # 立即同步到悬浮窗（如果已创建）
        if hasattr(self, 'floating_window') and self.floating_window is not None:
            self.floating_window.set_performance_monitor_visible(
                self.performance_monitor_switch.isChecked()
            )
            self.floating_window.set_performance_charts_visible(
                self.performance_charts_switch.isChecked()
            )
        
        # 悬浮窗设置
        size_map = {"small": "小尺寸", "medium": "中尺寸", "large": "大尺寸"}
        current_size_key = self.settings_manager.get("floating_window_size", "medium")
        current_size_text = size_map.get(current_size_key, "中尺寸")
        if hasattr(self, 'floating_size_combo'):
            self.floating_size_combo.setCurrentText(current_size_text)
        if hasattr(self, 'floating_opacity_spin'):
            opacity = self.settings_manager.get("floating_window_opacity", 0.7)
            self.floating_opacity_spin.setValue(opacity)
            self.floating_opacity_slider.setValue(int(opacity * 100))
        
        # 界面大小设置
        ui_size_map = {"small": "小", "medium": "中", "large": "大"}
        current_ui_size_key = self.settings_manager.get("ui_scale", "large")
        current_ui_size_text = ui_size_map.get(current_ui_size_key, "大")
        if hasattr(self, 'ui_size_combo'):
            self.ui_size_combo.setCurrentText(current_ui_size_text)
        
        # 全局追踪设置
        if hasattr(self, 'global_tracking_switch'):
            self.global_tracking_switch.setChecked(self.settings_manager.get("enable_global_tracking", True))
        
        # 坐标识别设置
        if hasattr(self, 'roi_recognition_switch'):
            self.roi_recognition_switch.setChecked(self.settings_manager.get("enable_roi_recognition", False))

        # 血脉识别设置
        if hasattr(self, 'bloodline_recognition_switch'):
            self.bloodline_recognition_switch.setChecked(self.settings_manager.get("enable_bloodline_recognition", False))
        if hasattr(self, 'bloodline_roi_label'):
            bl_roi = self.settings_manager.get("bloodline_roi")
            if bl_roi and all(k in bl_roi for k in ("x", "y", "width", "height")):
                self.bloodline_roi_label.setText(
                    f"当前血脉框选区域: x={bl_roi['x']}, y={bl_roi['y']}, w={bl_roi['width']}, h={bl_roi['height']}"
                )
            else:
                self.bloodline_roi_label.setText("当前未设置血脉框选区域")

        # 热键标签刷新
        if hasattr(self, 'hotkey_labels'):
            hotkeys = self.settings_manager.get("hotkeys", {})
            for hk_id, label in self.hotkey_labels.items():
                cfg = hotkeys.get(hk_id, {})
                if cfg.get("display"):
                    label.setText(cfg["display"])

    def save_ui_to_settings(self):
        """从UI保存设置到设置管理器"""
        # 通用设置
        self.settings_manager.set("minimize_to_tray", self.minimize_tray_switch.isChecked())
        self.settings_manager.set("desktop_pet_enabled", self.desktop_pet_switch.isChecked())
        
        # 识别设置
        self.settings_manager.set("recognition_interval", self.recognition_interval_spin.value())
        self.settings_manager.set("recognition_confidence", self.confidence_xt_spin.value())
        self.settings_manager.set("confidence_pollution", self.confidence_pollution_spin.value())
        self.settings_manager.set("ocr_confidence", self.ocr_confidence_spin.value())
        
        # 地图设置
        self.settings_manager.set("map_update_interval", self.map_update_interval_spin.value())
        self.settings_manager.set("use_real_pointer", self.use_real_pointer_switch.isChecked())
        self.settings_manager.set("resource_icon_size", self.resource_icon_size_spin.value())
        
        
        
        # 计数器设置
        self.settings_manager.set("default_target", self.default_target_spin.value())
        self.settings_manager.set("auto_save_interval", self.auto_save_interval_spin.value())
        self.settings_manager.set("auto_save_progress", self.auto_save_switch.isChecked())
        self.settings_manager.set("breakthrough_notification", self.breakthrough_notification_switch.isChecked())
        
        # 高级设置（不需要保存，只用于触发调试窗口）
        self.settings_manager.set("show_performance_monitor", self.performance_monitor_switch.isChecked())
        self.settings_manager.set("show_performance_charts", self.performance_charts_switch.isChecked())
        
        # 悬浮窗设置
        size_map_reverse = {"小尺寸": "small", "中尺寸": "medium", "大尺寸": "large"}
        if hasattr(self, 'floating_size_combo'):
            size_text = self.floating_size_combo.currentText()
            size_key = size_map_reverse.get(size_text, "medium")
            self.settings_manager.set("floating_window_size", size_key)
        if hasattr(self, 'floating_opacity_spin'):
            self.settings_manager.set("floating_window_opacity", self.floating_opacity_spin.value())
        
        # 界面大小设置
        ui_size_map_reverse = {"小": "small", "中": "medium", "大": "large"}
        if hasattr(self, 'ui_size_combo'):
            ui_size_text = self.ui_size_combo.currentText()
            ui_size_key = ui_size_map_reverse.get(ui_size_text, "large")
            self.settings_manager.set("ui_scale", ui_size_key)
        
        # 全局追踪设置
        if hasattr(self, 'global_tracking_switch'):
            self.settings_manager.set("enable_global_tracking", self.global_tracking_switch.isChecked())
        
        # 坐标识别设置
        if hasattr(self, 'roi_recognition_switch'):
            self.settings_manager.set("enable_roi_recognition", self.roi_recognition_switch.isChecked())

        # 血脉识别设置
        if hasattr(self, 'bloodline_recognition_switch'):
            self.settings_manager.set("enable_bloodline_recognition", self.bloodline_recognition_switch.isChecked())
    
    def _on_check_update(self):
        """检查更新"""
        if not hasattr(self, 'check_update_btn'):
            return
        self.check_update_btn.setEnabled(False)
        self.check_update_btn.setText("检查中...")
        self.latest_version_label.setText("正在检查更新...")
        self.latest_version_label.setStyleSheet("color: #71717a; font-size: 13px;")

        # 启动后台检查线程
        from PySide6.QtCore import QThread, Signal
        # 复用 settings_dialog 中的 worker
        try:
            from ui.settings_dialog import _CheckUpdateWorker
        except Exception:
            # 兜底：内联 worker
            class _CheckUpdateWorker(QThread):
                finished_signal = Signal(object)
                def run(self):
                    try:
                        from core.update_manager import check_for_update
                        info = check_for_update(timeout=15)
                    except Exception:
                        info = None
                    self.finished_signal.emit(info)

        self._check_worker = _CheckUpdateWorker()
        self._check_worker.finished_signal.connect(self._on_check_update_done)
        self._check_worker.start()

    def _silent_check_update(self):
        """启动时静默检查更新（不显示"检查中"，仅在有新版本时弹窗）"""
        try:
            from ui.settings_dialog import _CheckUpdateWorker
        except Exception:
            return  # 模块加载失败，跳过

        self._silent_worker = _CheckUpdateWorker()
        self._silent_worker.finished_signal.connect(self._on_silent_check_done)
        self._silent_worker.start()

    def _on_silent_check_done(self, info):
        """静默检查完成（仅在有新版本时弹窗）"""
        if info is None:
            return  # 无新版本或失败，静默忽略
        # 有新版本，更新设置页面的版本标签（如果已显示）
        if hasattr(self, 'latest_version_label'):
            latest = info.get("latest_version", "")
            self.latest_version_label.setText(f"🆕 检测到新版本：v{latest}")
            self.latest_version_label.setStyleSheet("color: #f59e0b; font-size: 13px;")
        # 弹出更新对话框
        try:
            from ui.update_dialog import UpdateDialog
            dlg = UpdateDialog(info, parent=self)
            dlg.exec()
        except Exception as e:
            # 弹窗失败时降级提示，避免静默吞掉异常导致用户不知有新版本
            from PySide6.QtWidgets import QMessageBox
            html_url = info.get("html_url", "")
            latest = info.get("latest_version", "")
            QMessageBox.warning(
                self, "检测到新版本",
                f"检测到新版本 v{latest}，但更新弹窗加载失败：\n{e}\n\n"
                f"请前往 GitHub 手动下载：\n{html_url}\n"
                f"或加 QQ 群 1105048691 获取下载"
            )

    def _on_check_update_done(self, info):
        """检查更新完成"""
        if hasattr(self, 'check_update_btn'):
            self.check_update_btn.setEnabled(True)
            self.check_update_btn.setText("🔍 检查更新")

        if info is None:
            # 无新版本或检查失败
            try:
                from core.update_manager import CURRENT_VERSION
            except Exception:
                CURRENT_VERSION = "4.6.11"
            self.latest_version_label.setText(f"✅ 已是最新版本 v{CURRENT_VERSION}")
            self.latest_version_label.setStyleSheet("color: #10b981; font-size: 13px;")
            return

        # 有新版本
        latest = info.get("latest_version", "")
        self.latest_version_label.setText(f"🆕 检测到新版本：v{latest}")
        self.latest_version_label.setStyleSheet("color: #f59e0b; font-size: 13px;")

        # 弹出更新对话框
        try:
            from ui.update_dialog import UpdateDialog
            dlg = UpdateDialog(info, parent=self)
            dlg.exec()
        except Exception as e:
            html_url = info.get("html_url", "") if info else ""
            latest = info.get("latest_version", "") if info else ""
            QMessageBox.warning(
                self, "更新",
                f"检测到新版本 v{latest}，但更新弹窗加载失败：\n{e}\n\n"
                f"请前往 GitHub 手动下载：\n{html_url}\n"
                f"或加 QQ 群 1105048691 获取下载"
            )

    def on_save_settings(self):
        """保存设置"""
        # 检查识别模式和间隔是否改变
        old_roi_mode = self.settings_manager.get("enable_roi_recognition", False)
        old_interval = self.settings_manager.get("recognition_interval", 500)

        self.save_ui_to_settings()
        if self.settings_manager.save_settings():
            # 应用桌宠开关
            toggle_pet(self.desktop_pet_switch.isChecked())
            
            # 应用UI缩放
            self.apply_ui_scale()
            
            # 应用悬浮窗大小设置
            size_key = self.settings_manager.get("floating_window_size", "medium")
            if hasattr(self, 'floating_window') and self.floating_window.isVisible():
                self.floating_window.set_size(size_key)

            # 检查识别间隔是否改变，如果改变则更新定时器
            new_interval = self.settings_manager.get("recognition_interval", 500)
            if old_interval != new_interval and hasattr(self, 'recognition_timer'):
                print(f"🔄 识别间隔已更改: {old_interval}ms -> {new_interval}ms")
                self.recognition_timer.stop()
                self.recognition_timer.start(new_interval)

            # 检查识别模式是否改变，如果改变则重启识别
            new_roi_mode = self.settings_manager.get("enable_roi_recognition", False)
            if old_roi_mode != new_roi_mode:
                print(f"🔄 识别模式已更改: {old_roi_mode} -> {new_roi_mode}")
                self._restart_recognition()

            QMessageBox.information(self, "成功", "✅ 设置已保存！")
        else:
            QMessageBox.critical(self, "错误", "保存设置失败！")
    
    def on_reset_settings(self):
        """恢复默认设置"""
        reply = QMessageBox.question(
            self,
            "确认恢复",
            "确定要恢复所有设置为默认值吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.settings_manager.reset_to_default()
            self.settings_manager.save_settings()
            self.load_settings_to_ui()
            self.apply_ui_scale()

            if hasattr(self, 'floating_window') and self.floating_window is not None:
                self.floating_window._unregister_hotkeys()
                self.floating_window._register_hotkey()
                logger.log("✅ 抓宠悬浮窗热键已重注册（恢复默认）")
            if hasattr(self, '_map_floating_window') and self._map_floating_window is not None:
                self._map_floating_window._unregister_hotkeys()
                self._map_floating_window._register_hotkey()
                logger.log("✅ 地图悬浮窗热键已重注册（恢复默认）")

            QMessageBox.information(self, "成功", "已恢复默认设置！")
    
    def show_coming_soon(self, feature_name):
        """显示功能未制作完成提示"""
        QMessageBox.information(
            self,
            "功能预告",
            f"【{feature_name}】功能还未制作完成，敬请期待！\n\n我们正在努力开发中..."
        )
    
    def on_view_global_stats(self):
        """查看全局追踪统计数据"""
        stats = self.manager.get_all_global_stats()
        
        if not stats:
            QMessageBox.information(self, "统计数据", "暂无全局追踪数据")
            return
        
        # 构建统计信息文本
        info_text = "📊 全局童话事件统计\n\n"
        total = 0
        for name, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            info_text += f"{name}: {count} 次\n"
            total += count
        
        info_text += f"\n总计: {total} 次"
        
        QMessageBox.information(self, "统计数据", info_text)
    
    def on_clear_global_stats(self):
        """清空所有全局追踪数据"""
        stats = self.manager.get_all_global_stats()
        
        if not stats:
            QMessageBox.information(self, "提示", "暂无追踪数据需要清空")
            return
        
        reply = QMessageBox.question(
            self,
            "确认清空",
            f"确定要清空所有全局追踪数据吗？\n\n当前共有 {len(stats)} 个精灵的追踪记录。\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.manager.clear_global_stats()
            self.manager.save_counters()
            QMessageBox.information(self, "成功", "已清空所有追踪数据")

    def on_roi_select(self):
        """框选识别区域"""
        from ui.roi_selector import ROISelector
        from PySide6.QtWidgets import QApplication

        self.hide()

        app = QApplication.instance()
        selector = ROISelector()

        finished = False

        def on_region_selected(x, y, w, h):
            nonlocal finished
            self.settings_manager.set("recognition_roi", {"x": x, "y": y, "width": w, "height": h})
            self.settings_manager.save_settings()
            finished = True

        def on_cancelled():
            nonlocal finished
            finished = True

        selector.region_selected.connect(on_region_selected)
        selector.selection_cancelled.connect(on_cancelled)
        selector.show()

        # 等待框选完成
        while not finished and selector.isVisible():
            app.processEvents()

        self.show()

    def on_bloodline_select(self):
        """框选血脉识别区域（使用全屏覆盖框选工具，返回屏幕坐标转换为客户区相对坐标）"""
        from core.rectangle_selector import RectangleSelector
        from PySide6.QtWidgets import QApplication
        import win32gui

        self.hide()

        app = QApplication.instance()
        selector = RectangleSelector()

        finished = False

        def on_region_selected(x, y, w, h):
            nonlocal finished
            # RectangleSelector 返回的是屏幕逻辑坐标（Qt坐标系）
            # 需要转换为物理坐标（与capture_window()截图坐标系一致）
            # 先乘以dpi_scale转为物理像素，再减去窗口物理偏移
            client_x, client_y, phys_w, phys_h = x, y, w, h
            conversion_ok = False
            try:
                if hasattr(self, 'game_capture') and self.game_capture and self.game_capture.hwnd:
                    hwnd = self.game_capture.hwnd
                    # 获取DPI缩放因子（与ROISelector相同的方法）
                    import ctypes
                    try:
                        dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
                        dpi_scale = dpi / 96.0
                    except:
                        try:
                            scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0)
                            dpi_scale = scale_factor / 100.0
                        except:
                            dpi_scale = 1.0

                    # 将逻辑坐标转换为物理坐标
                    phys_x = int(x * dpi_scale)
                    phys_y = int(y * dpi_scale)
                    phys_w = int(w * dpi_scale)
                    phys_h = int(h * dpi_scale)

                    # 获取窗口客户区的屏幕物理坐标
                    client_origin = win32gui.ClientToScreen(hwnd, (0, 0))
                    # 转换为窗口客户区相对物理坐标（与截图坐标系一致）
                    client_x = phys_x - client_origin[0]
                    client_y = phys_y - client_origin[1]
                    conversion_ok = True
            except Exception:
                pass

            if not conversion_ok:
                finished = True
                return

            # 保存客户区相对物理坐标到设置
            self.settings_manager.set("bloodline_roi", {"x": client_x, "y": client_y, "width": phys_w, "height": phys_h})
            self.settings_manager.save_settings()
            if hasattr(self, 'bloodline_roi_label'):
                self.bloodline_roi_label.setText(
                    f"当前血脉框选区域: x={client_x}, y={client_y}, w={phys_w}, h={phys_h}"
                )

            # 保存框选区域截图到 image/xm.png（覆盖旧文件）
            try:
                if hasattr(self, 'game_capture') and self.game_capture:
                    full_screenshot = self.game_capture.capture_window()  # 无ROI，返回完整客户区截图
                    if full_screenshot is not None and full_screenshot.size > 0:
                        img_h, img_w = full_screenshot.shape[:2]
                        # 边界保护
                        cx = max(0, min(client_x, img_w - 1))
                        cy = max(0, min(client_y, img_h - 1))
                        cw = min(phys_w, img_w - cx)
                        ch = min(phys_h, img_h - cy)
                        if cw > 0 and ch > 0:
                            roi_image = full_screenshot[cy:cy+ch, cx:cx+cw]
                            image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'image')
                            if not os.path.exists(image_dir):
                                os.makedirs(image_dir)
                            # 保存xm.png（只有框选区域）
                            save_path = os.path.join(image_dir, "xm.png")
                            _imwrite(save_path, roi_image)
            except Exception:
                pass

            finished = True

        def on_cancelled():
            nonlocal finished
            finished = True

        selector.region_selected.connect(on_region_selected)
        selector.selection_cancelled.connect(on_cancelled)
        selector.show()

        # 等待框选完成
        while not finished and selector.isVisible():
            app.processEvents()

        self.show()

    def _refresh_window_list(self):
        """刷新可用的游戏窗口列表到下拉框"""
        if not hasattr(self, 'window_select_combo'):
            return

        self.window_select_combo.blockSignals(True)
        self.window_select_combo.clear()

        if not hasattr(self, 'game_capture') or self.game_capture is None:
            self.window_select_combo.addItem("游戏未初始化")
            self.window_select_combo.blockSignals(False)
            return

        windows = self.game_capture.get_available_windows()
        if not windows:
            self.window_select_combo.addItem("未检测到游戏窗口")
            self.window_select_combo.blockSignals(False)
            return

        for idx, hwnd, title in windows:
            display = f"游戏窗口 {idx + 1}"
            self.window_select_combo.addItem(display, idx)

        saved_index = self.settings_manager.get("selected_window_index", 0)
        if saved_index < self.window_select_combo.count():
            self.window_select_combo.setCurrentIndex(saved_index)

        self.window_select_combo.blockSignals(False)

    def _on_window_selected(self, index):
        """用户选择不同游戏窗口时触发"""
        if index < 0:
            return

        window_index = self.window_select_combo.itemData(index)
        if window_index is None:
            return

        self.settings_manager.set("selected_window_index", window_index)
        self.settings_manager.save_settings()

        if hasattr(self, 'game_capture') and self.game_capture is not None:
            self.game_capture.hwnd = 0
            logger.log(f"🔄 切换游戏窗口索引为 {window_index + 1}，下次识别将使用新窗口")

    def _on_window_preview_toggled(self, checked):
        """预览按钮勾选/取消时触发"""
        if not hasattr(self, 'window_preview_label') or not hasattr(self, 'window_preview_timer'):
            return

        if checked:
            self.window_preview_label.show()
            # 立即捕获一帧
            self._update_window_preview()
            self.window_preview_timer.start()
        else:
            self.window_preview_timer.stop()
            self.window_preview_label.hide()

    def _update_window_preview(self):
        """捕获当前选中游戏窗口画面并更新预览标签"""
        if not hasattr(self, 'window_preview_label'):
            return

        if not hasattr(self, 'game_capture') or self.game_capture is None:
            self.window_preview_label.setText("游戏未初始化")
            return

        # 捕获窗口画面（不复用主识别的截图缓存，避免干扰）
        try:
            image = self.game_capture.capture_window()
        except Exception as e:
            self.window_preview_label.setText(f"截图失败: {e}")
            return

        if image is None:
            self.window_preview_label.setText("未检测到游戏窗口")
            return

        try:
            # BGR -> RGB
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            h, w = img_rgb.shape[:2]

            # 按标签宽度等比缩放
            label_w = max(1, self.window_preview_label.width() - 12)
            label_h = max(1, self.window_preview_label.height() - 12)
            scale = min(label_w / w, label_h / h)
            if scale < 1.0:
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
                img_rgb = cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
            else:
                new_w, new_h = w, h

            qimg = QImage(img_rgb.data, new_w, new_h, img_rgb.strides[0], QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            self.window_preview_label.setText("")
            self.window_preview_label.setPixmap(pixmap)
        except Exception as e:
            self.window_preview_label.setText(f"预览渲染失败: {e}")

    def on_export_counters(self):
        """导出计数器数据到JSON文件"""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出计数器数据",
            "counters_export.json",
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            self.manager.save_counters()  # 先保存到默认位置
            import shutil
            shutil.copy2(self.manager.counters_file, file_path)
            QMessageBox.information(self, "成功", f"计数器数据已导出到:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {e}")
    
    def on_import_counters(self):
        """从JSON文件导入计数器数据"""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入计数器数据",
            "",
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        reply = QMessageBox.question(
            self,
            "确认导入",
            "导入将覆盖当前所有计数器数据，是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            import shutil
            shutil.copy2(file_path, self.manager.counters_file)
            self.manager.load_counters()  # 重新加载
            self._refresh_all()
            QMessageBox.information(self, "成功", "计数器数据已导入！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {e}")
    
    def on_debug_toggled(self, checked):
        """调试输出开关切换 - 打开/关闭调试窗口"""
        if checked:
            # 创建并显示调试窗口
            if not hasattr(self, 'debug_window') or self.debug_window is None:
                self.debug_window = DebugWindow(self)
            
            self.debug_window.show()
            self.debug_window.raise_()
            self.debug_window.activateWindow()
            
            # 启用日志
            logger.set_enabled(True)
            
            # 输出模型加载状态
            if hasattr(self, 'game_capture') and self.game_capture:
                logger.log(self.game_capture.get_model_status())
        else:
            # 关闭调试窗口
            if hasattr(self, 'debug_window') and self.debug_window:
                self.debug_window.close()
                self.debug_window = None
            
            # 禁用日志
            logger.set_enabled(False)

    def on_toggle_fold(self):
        """切换折叠状态"""
        is_folded = self.manager.toggle_fold()
        self.manager.save_counters()  # 切换折叠后保存
        # 更新按钮三角形方向
        self.btn_fold.is_folded = is_folded
        self.btn_fold.update()  # 触发重绘
        self._refresh_counter_list()
    
    def on_new_counter(self):
        """新建计数器 - 从异色图鉴选择"""
        # 如果折叠，先展开
        if self.manager.is_folded:
            self.on_toggle_fold()
        # 切换到异色图鉴视图
        self.content_stack.setCurrentIndex(2)

    def create_counter_from_pokemon(self, pokemon):
        """从精灵卡片创建计数器(带确认对话框)"""
        name = pokemon["name"]
        # 处理types字段(可能是列表或字符串)
        types = pokemon.get("types", [])
        if isinstance(types, list):
            type_ = "、".join(types)
        else:
            type_ = str(types)
        
        # 获取精灵的icon_id
        icon_id = pokemon.get("icon_id", 0)
        try:
            icon_id = int(icon_id)
        except (ValueError, TypeError):
            icon_id = 0
        
        # 检查是否有全局追踪数据
        global_count = self.manager.get_global_breakthrough(name)
        
        if global_count > 0:
            # 有全局追踪数据，询问是否同步
            reply = QMessageBox.question(
                self,
                "同步数据",
                f"检测到【{name}】已有 {global_count} 次童话事件记录。\n\n"
                f"是否将这些记录同步到新创建的计数器？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply != QMessageBox.Yes:
                # 选择"否"：不清零数据，不创建计数器，直接返回
                return
            
            # 选择"是"：创建计数器并同步数据
            default_target = self.settings_manager.get("default_target", 80)
            counter = self.manager.add_counter(name, f"{name}计数器", type_, icon_id=icon_id)
            if counter:
                counter.count = global_count
                counter.target = default_target
        else:
            # 没有全局数据，直接创建
            reply = QMessageBox.question(
                self,
                "确认添加",
                f"确定为【{name}】创建计数器吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply != QMessageBox.Yes:
                return
            
            default_target = self.settings_manager.get("default_target", 80)
            counter_name = f"{name}计数器"
            counter = self.manager.add_counter(name, counter_name, type_, icon_id=icon_id)
            if counter:
                counter.target = default_target
        
        self.manager.save_counters()  # 添加后立即保存
        
        # 重置童话事件提示计数
        if hasattr(self, 'game_capture') and self.game_capture:
            self.game_capture.set_nightmare_count(0)
            if counter:
                counter.nightmare_count = 0
        
        self.content_stack.setCurrentIndex(1)
        self._refresh_all()

    def on_custom_pokemon(self):
        from ui.lkwg_manual_dialog import LkwgManualDialog
        
        dialog = LkwgManualDialog(self)
        if dialog.exec():
            name, type_, target, icon, evolution_chain = dialog.get_data()
            if not name:
                QMessageBox.warning(self, "警告", "请输入精灵名称！")
                return
            
            # 保存到图鉴（包含进化链）
            self.manager.save_custom_pokemon(name, type_, evolution_chain)
            
            # 创建计数器
            try:
                target_val = int(target)
            except:
                target_val = self.settings_manager.get("default_target", 80)
            
            counter = self.manager.add_counter(name, f"{name}计数器", type_, is_custom=True)
            if counter:
                counter.target = target_val
            self.manager.save_counters()  # 添加后立即保存
            
            # 重置童话事件提示计数
            if hasattr(self, 'game_capture') and self.game_capture:
                self.game_capture.set_nightmare_count(0)
                if counter:
                    counter.nightmare_count = 0
            
            self.content_stack.setCurrentIndex(1)
            self._refresh_all()
    
    # ================= 咕噜球计算界面 =================
    def _create_ball_calculator_view(self):
        """创建咕噜球计算界面"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(SCROLL_BAR_STYLE)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        # 标题
        title = QLabel("🔮 咕噜球使用计算器")
        title.setStyleSheet("color: #f8f0ff; font-size: 24px; font-weight: bold;")
        layout.addWidget(title)
        
        subtitle = QLabel("输入使用前后的咕噜球数量，自动计算各类球的使用情况")
        subtitle.setStyleSheet("color: #c084fc; font-size: 13px;")
        layout.addWidget(subtitle)
        
        # 咕噜球种类列表
        ball_types = [
            "普通咕噜球", "高级咕噜球", "光合球", "淘沙球",
            "调温球", "变幻球", "暗星球", "网兜球",
            "绝缘球", "好战球", "美妙球", "捕光球",
            "国王球", "棱镜球", "织梦棱镜球",
            "奇趣球", "狂欢棱镜球", "童话球", "铅绘棱镜球"
        ]
        
        # 创建输入表格
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setSpacing(12)
        
        self.ball_inputs = {}  # 存储每个球的输入框
        
        for ball_name in ball_types:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(15)
            
            # 球名称
            label = QLabel(ball_name)
            label.setStyleSheet("color: #e4e4e7; font-size: 14px; min-width: 120px;")
            row_layout.addWidget(label)
            
            # 使用前数量
            before_label = QLabel("使用前:")
            before_label.setStyleSheet("color: #a1a1aa; font-size: 12px;")
            row_layout.addWidget(before_label)
            
            before_input = QLineEdit()
            before_input.setPlaceholderText("0")
            before_input.setStyleSheet("""
                QLineEdit {
                    background-color: #252530;
                    border: 1px solid rgba(124, 58, 237, 0.2);
                    border-radius: 6px;
                    padding: 6px 10px;
                    color: #e4e4e7;
                    font-size: 13px;
                    min-width: 80px;
                }
                QLineEdit:focus {
                    border: 1px solid #7c3aed;
                }
            """)
            before_input.textChanged.connect(self._on_ball_input_changed)
            row_layout.addWidget(before_input)
            
            # 使用后数量
            after_label = QLabel("使用后:")
            after_label.setStyleSheet("color: #a1a1aa; font-size: 12px;")
            row_layout.addWidget(after_label)
            
            after_input = QLineEdit()
            after_input.setPlaceholderText("0")
            after_input.setStyleSheet("""
                QLineEdit {
                    background-color: #252530;
                    border: 1px solid rgba(124, 58, 237, 0.2);
                    border-radius: 6px;
                    padding: 6px 10px;
                    color: #e4e4e7;
                    font-size: 13px;
                    min-width: 80px;
                }
                QLineEdit:focus {
                    border: 1px solid #7c3aed;
                }
            """)
            after_input.textChanged.connect(self._on_ball_input_changed)
            row_layout.addWidget(after_input)
            
            # 使用数量显示
            used_label = QLabel("使用: 0")
            used_label.setStyleSheet("color: #a78bfa; font-size: 13px; font-weight: 500; min-width: 100px;")
            row_layout.addWidget(used_label)
            
            row_layout.addStretch()
            
            table_layout.addWidget(row)
            self.ball_inputs[ball_name] = {
                'before': before_input,
                'after': after_input,
                'used': used_label
            }
        
        layout.addWidget(table_widget)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        calc_btn = QPushButton("计算使用量")
        calc_btn.setFixedHeight(42)
        calc_btn.setMinimumWidth(150)
        calc_btn.setCursor(Qt.PointingHandCursor)
        calc_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8b5cf6, stop:1 #a855f7);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #a78bfa, stop:1 #c084fc);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c3aed, stop:1 #9333ea);
            }
        """)
        calc_btn.clicked.connect(self._calculate_balls)
        btn_layout.addWidget(calc_btn)
        
        reset_btn = QPushButton("重置")
        reset_btn.setFixedHeight(42)
        reset_btn.setMinimumWidth(120)
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #252530;
                color: #a1a1aa;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                font-size: 14px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #2a2a35;
                border-color: #7c3aed;
                color: #e4e4e7;
            }
        """)
        reset_btn.clicked.connect(self._reset_ball_inputs)
        btn_layout.addWidget(reset_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 结果显示区域
        result_group = QGroupBox("计算结果")
        result_group.setStyleSheet("""
            QGroupBox {
                color: #c084fc;
                font-size: 15px;
                font-weight: 600;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 10px;
                margin-top: 15px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }
        """)
        result_layout = QVBoxLayout(result_group)
        result_layout.setSpacing(8)
        
        self.result_label = QLabel("请输入数据后点击计算")
        self.result_label.setStyleSheet("color: #71717a; font-size: 13px; padding: 10px;")
        self.result_label.setAlignment(Qt.AlignCenter)
        result_layout.addWidget(self.result_label)
        
        layout.addWidget(result_group)
        layout.addStretch()
        
        scroll.setWidget(container)
        
        # 加载保存的数据
        self._load_ball_calculator_data()
        
        return scroll
    
    def _calculate_balls(self):
        """计算咕噜球使用量"""
        results = []
        total_used = 0
        
        for ball_name, inputs in self.ball_inputs.items():
            before_text = inputs['before'].text().strip()
            after_text = inputs['after'].text().strip()
            
            # 如果使用前或使用后任一为空，跳过计算
            if not before_text or not after_text:
                inputs['used'].setText("未输入")
                inputs['used'].setStyleSheet("color: #71717a; font-size: 13px; font-weight: 500; min-width: 100px;")
                continue
            
            try:
                before = int(before_text)
                after = int(after_text)
                used = before - after
                
                if used > 0:
                    results.append(f"{ball_name}: {used} 个")
                    total_used += used
                    inputs['used'].setText(f"使用: {used}")
                    inputs['used'].setStyleSheet("color: #22c55e; font-size: 13px; font-weight: 500; min-width: 100px;")
                elif used < 0:
                    inputs['used'].setText(f"增加: {-used}")
                    inputs['used'].setStyleSheet("color: #ef4444; font-size: 13px; font-weight: 500; min-width: 100px;")
                else:
                    inputs['used'].setText("使用: 0")
                    inputs['used'].setStyleSheet("color: #71717a; font-size: 13px; font-weight: 500; min-width: 100px;")
            except ValueError:
                inputs['used'].setText("无效输入")
                inputs['used'].setStyleSheet("color: #ef4444; font-size: 13px; font-weight: 500; min-width: 100px;")
        
        # 显示结果
        if results:
            result_text = f"总计使用: {total_used} 个咕噜球\n\n详细统计:\n" + "\n".join(results)
            self.result_label.setText(result_text)
            self.result_label.setStyleSheet("color: #e4e4e7; font-size: 13px; padding: 10px;")
            self.result_label.setAlignment(Qt.AlignLeft)
        else:
            self.result_label.setText("没有使用任何咕噜球或数据不完整")
            self.result_label.setStyleSheet("color: #71717a; font-size: 13px; padding: 10px;")
            self.result_label.setAlignment(Qt.AlignCenter)
    
    def _reset_ball_inputs(self):
        """重置所有输入 - 只重置使用后"""
        for inputs in self.ball_inputs.values():
            # 只清空使用后，保留使用前
            inputs['after'].clear()
            inputs['used'].setText("使用: 0")
            inputs['used'].setStyleSheet("color: #71717a; font-size: 13px; font-weight: 500; min-width: 100px;")
        
        self.result_label.setText("请输入数据后点击计算")
        self.result_label.setStyleSheet("color: #71717a; font-size: 13px; padding: 10px;")
        self.result_label.setAlignment(Qt.AlignCenter)
        
        # 清除保存的数据
        self.settings_manager.set("ball_calculator_data", {})
        self.settings_manager.save_settings()
    
    def _on_ball_input_changed(self):
        """输入框内容变化时自动保存"""
        ball_data = {}
        
        for ball_name, inputs in self.ball_inputs.items():
            before_text = inputs['before'].text().strip()
            after_text = inputs['after'].text().strip()
            
            if before_text or after_text:
                ball_data[ball_name] = {
                    'before': before_text,
                    'after': after_text
                }
        
        # 保存到设置
        self.settings_manager.set("ball_calculator_data", ball_data)
        self.settings_manager.save_settings()
    
    def _load_ball_calculator_data(self):
        """加载保存的咕噜球计算数据"""
        ball_data = self.settings_manager.get("ball_calculator_data", {})
        
        if not ball_data:
            return
        
        for ball_name, data in ball_data.items():
            if ball_name in self.ball_inputs:
                inputs = self.ball_inputs[ball_name]
                if 'before' in data:
                    inputs['before'].setText(str(data['before']))
                if 'after' in data:
                    inputs['after'].setText(str(data['after']))
    
    # ================= 出闪记录视图 =================
    def _create_shiny_records_view(self):
        """创建出闪记录界面"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(SCROLL_BAR_STYLE)
        container = QWidget()
        container.setObjectName("mainContent")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(28)
        
        # ================= 标题区 =================
        header_section = QWidget()
        header_layout = QVBoxLayout(header_section)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)
        
        # 主标题
        title_row = QWidget()
        title_row_layout = QHBoxLayout(title_row)
        title_row_layout.setContentsMargins(0, 0, 0, 0)
        title_row_layout.setSpacing(12)
        
        title_icon = QLabel()
        title_icon.setStyleSheet("font-size: 32px;")
        title_row_layout.addWidget(title_icon)
        
        title_text = QLabel("出闪记录")
        title_text.setStyleSheet("color: #f8f0ff; font-size: 28px; font-weight: bold; letter-spacing: 1px;")
        title_row_layout.addWidget(title_text)
        title_row_layout.addStretch()
        
        # 操作按钮组
        action_group = QWidget()
        action_layout = QHBoxLayout(action_group)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(10)
        
        # 清除记录按钮
        clear_btn = QPushButton("清空记录")
        clear_btn.setFixedHeight(40)
        clear_btn.setMinimumWidth(130)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.1);
                color: #ef4444;
                border: 1px solid rgba(239, 68, 68, 0.25);
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
                border-color: rgba(239, 68, 68, 0.45);
            }
            QPushButton:pressed {
                background-color: rgba(220, 38, 38, 0.3);
            }
        """)
        clear_btn.clicked.connect(self.on_clear_shiny_records)
        action_layout.addWidget(clear_btn)
        
        title_row_layout.addWidget(action_group)
        header_layout.addWidget(title_row)
        
        # 副标题
        subtitle_label = QLabel("记录您每一次珍贵的出闪时刻")
        subtitle_label.setStyleSheet("color: #a1a1aa; font-size: 14px; padding-left: 44px;")
        header_layout.addWidget(subtitle_label)
        
        layout.addWidget(header_section)
        
        # ================= 日期筛选区 =================
        filter_card = QFrame()
        filter_card.setStyleSheet("""
            QFrame {
                background: linear-gradient(135deg, rgba(124, 58, 237, 0.08) 0%, rgba(21, 21, 28, 0.95) 100%);
                border: 1px solid rgba(124, 58, 237, 0.25);
                border-radius: 16px;
            }
        """)
        filter_card_layout = QVBoxLayout(filter_card)
        filter_card_layout.setContentsMargins(24, 20, 24, 20)
        filter_card_layout.setSpacing(16)
        
        # 筛选标题
        filter_header = QWidget()
        filter_header_layout = QHBoxLayout(filter_header)
        filter_header_layout.setContentsMargins(0, 0, 0, 0)
        filter_header_layout.setSpacing(10)
        
        filter_icon = QLabel()
        filter_icon.setStyleSheet("font-size: 20px;")
        filter_header_layout.addWidget(filter_icon)
        
        filter_title = QLabel("时间筛选")
        filter_title.setStyleSheet("color: #f8f0ff; font-size: 16px; font-weight: 600;")
        filter_header_layout.addWidget(filter_title)
        filter_header_layout.addStretch()
        
        filter_card_layout.addWidget(filter_header)
        
        # 日期按钮组
        filter_buttons = QWidget()
        filter_buttons_layout = QHBoxLayout(filter_buttons)
        filter_buttons_layout.setContentsMargins(0, 0, 0, 0)
        filter_buttons_layout.setSpacing(10)
        
        # 创建日期筛选按钮
        filter_options = [
            ("今天", "today"),
            ("近3天", "3days"),
            ("近7天", "week"),
            ("近30天", "month"),
            ("全部记录", "all")
        ]
        
        for btn_text, btn_value in filter_options:
            btn = QPushButton(btn_text)
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("filterValue", btn_value)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(37, 37, 48, 0.8);
                    color: #a1a1aa;
                    border: 1px solid rgba(124, 58, 237, 0.15);
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: 500;
                    padding: 0 22px;
                }
                QPushButton:hover {
                    background-color: rgba(124, 58, 237, 0.15);
                    border-color: rgba(124, 58, 237, 0.35);
                    color: #c084fc;
                }
                QPushButton:checked {
                    background: linear-gradient(135deg, rgba(124, 58, 237, 0.35) 0%, rgba(124, 58, 237, 0.15) 100%);
                    color: #a78bfa;
                    border: 1px solid rgba(124, 58, 237, 0.6);
                    font-weight: 600;
                }
            """)
            btn.clicked.connect(lambda checked, v=btn_value: self.filter_shiny_records(v))
            
            if btn_value == "today":
                btn.setChecked(True)
                self.shiny_filter_today = btn
            elif btn_value == "3days":
                self.shiny_filter_3days = btn
            elif btn_value == "week":
                self.shiny_filter_week = btn
            elif btn_value == "month":
                self.shiny_filter_month = btn
            elif btn_value == "all":
                self.shiny_filter_all = btn
            
            filter_buttons_layout.addWidget(btn)
        
        filter_buttons_layout.addStretch()
        filter_card_layout.addWidget(filter_buttons)
        layout.addWidget(filter_card)
        
        # ================= 统计概览区 =================
        stats_overview = QWidget()
        stats_overview_layout = QVBoxLayout(stats_overview)
        stats_overview_layout.setContentsMargins(0, 0, 0, 0)
        stats_overview_layout.setSpacing(16)
        
        # 统计标题
        stats_title_row = QWidget()
        stats_title_layout = QHBoxLayout(stats_title_row)
        stats_title_layout.setContentsMargins(0, 0, 0, 0)
        stats_title_layout.setSpacing(10)
        
        stats_icon = QLabel()
        stats_icon.setStyleSheet("font-size: 20px;")
        stats_title_layout.addWidget(stats_icon)
        
        stats_title = QLabel("统计概览")
        stats_title.setStyleSheet("color: #f8f0ff; font-size: 16px; font-weight: 600;")
        stats_title_layout.addWidget(stats_title)
        stats_title_layout.addStretch()
        
        stats_overview_layout.addWidget(stats_title_row)
        
        # 统计卡片容器
        self.shiny_stats_widget = QWidget()
        self.shiny_stats_layout = QVBoxLayout(self.shiny_stats_widget)
        self.shiny_stats_layout.setContentsMargins(0, 0, 0, 0)
        self.shiny_stats_layout.setSpacing(12)
        
        stats_overview_layout.addWidget(self.shiny_stats_widget)
        layout.addWidget(stats_overview)
        
        # ================= 详细记录区 =================
        records_section = QWidget()
        records_layout = QVBoxLayout(records_section)
        records_layout.setContentsMargins(0, 0, 0, 0)
        records_layout.setSpacing(16)
        
        # 记录标题
        records_title_row = QWidget()
        records_title_layout = QHBoxLayout(records_title_row)
        records_title_layout.setContentsMargins(0, 0, 0, 0)
        records_title_layout.setSpacing(10)
        
        records_icon = QLabel()
        records_icon.setStyleSheet("font-size: 20px;")
        records_title_layout.addWidget(records_icon)
        
        records_title = QLabel("详细记录")
        records_title.setStyleSheet("color: #f8f0ff; font-size: 16px; font-weight: 600;")
        records_title_layout.addWidget(records_title)
        records_title_layout.addStretch()
        
        records_layout.addWidget(records_title_row)
        
        # 记录列表
        self.shiny_records_list = QWidget()
        self.shiny_records_list_layout = QVBoxLayout(self.shiny_records_list)
        self.shiny_records_list_layout.setContentsMargins(0, 0, 0, 0)
        self.shiny_records_list_layout.setSpacing(12)
        
        records_layout.addWidget(self.shiny_records_list)
        layout.addWidget(records_section)
        
        # ================= 底部留白 =================
        layout.addStretch()
        
        scroll.setWidget(container)
        
        # 初始刷新显示
        self.refresh_shiny_records()
        
        return scroll
    
    def filter_shiny_records(self, period):
        """筛选出闪记录"""
        buttons = [
            self.shiny_filter_today, 
            self.shiny_filter_3days, 
            self.shiny_filter_week, 
            self.shiny_filter_month, 
            self.shiny_filter_all
        ]
        for btn in buttons:
            btn.setChecked(btn == self.sender())
        
        self.shiny_current_period = period
        self.refresh_shiny_records()
    
    def refresh_shiny_records(self):
        """刷新显示出闪记录"""
        import datetime
        from datetime import timedelta
        
        # 清除现有显示
        while self.shiny_stats_layout.count():
            item = self.shiny_stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        while self.shiny_records_list_layout.count():
            item = self.shiny_records_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 获取筛选后的记录
        if not hasattr(self, 'shiny_current_period'):
            self.shiny_current_period = "today"
        
        today = datetime.date.today()
        start_date = None
        
        if self.shiny_current_period == "today":
            start_date = today.strftime("%Y-%m-%d")
        elif self.shiny_current_period == "3days":
            start_date = (today - timedelta(days=2)).strftime("%Y-%m-%d")
        elif self.shiny_current_period == "week":
            start_date = (today - timedelta(days=6)).strftime("%Y-%m-%d")
        elif self.shiny_current_period == "month":
            start_date = (today - timedelta(days=29)).strftime("%Y-%m-%d")
        
        # 获取记录并统计
        records = self.manager.get_shiny_records_by_date_range(start_date)
        stats = self.manager.get_shiny_records_statistics(records)
        
        # 显示统计概览（只显示最欧和最非）
        if stats:
            luckiest_pokemon = None
            luckiest_count = float('inf')
            unluckiest_pokemon = None
            unluckiest_count = 0
            
            for pokemon_name, stat in stats.items():
                if stat['max_count'] < luckiest_count:
                    luckiest_count = stat['max_count']
                    luckiest_pokemon = pokemon_name
                if stat['max_count'] > unluckiest_count:
                    unluckiest_count = stat['max_count']
                    unluckiest_pokemon = pokemon_name
            
            # 创建统计卡片
            stat_card = QFrame()
            stat_card.setStyleSheet("""
                QFrame {
                    background: linear-gradient(135deg, rgba(37, 37, 48, 0.9) 0%, rgba(21, 21, 28, 0.9) 100%);
                    border: 1px solid rgba(124, 58, 237, 0.2);
                    border-radius: 12px;
                }
            """)
            stat_card_layout = QVBoxLayout(stat_card)
            stat_card_layout.setContentsMargins(16, 16, 16, 16)
            stat_card_layout.setSpacing(16)
            
            # 主布局：左侧信息 + 右侧评级
            main_layout = QHBoxLayout()
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(16)
            
            # 左侧：最欧和最非信息
            left_widget = QWidget()
            left_layout = QVBoxLayout(left_widget)
            left_layout.setContentsMargins(0, 0, 0, 0)
            left_layout.setSpacing(16)
            
            # 最欧精灵
            lucky_row = QWidget()
            lucky_layout = QHBoxLayout(lucky_row)
            lucky_layout.setContentsMargins(0, 0, 0, 0)
            lucky_layout.setSpacing(12)
            
            lucky_icon = QLabel("🍀")
            lucky_icon.setStyleSheet("font-size: 24px;")
            lucky_layout.addWidget(lucky_icon)
            
            lucky_info = QWidget()
            lucky_info_layout = QVBoxLayout(lucky_info)
            lucky_info_layout.setContentsMargins(0, 0, 0, 0)
            lucky_info_layout.setSpacing(4)
            
            lucky_title = QLabel("最欧精灵")
            lucky_title.setStyleSheet("color: #71717a; font-size: 12px;")
            
            lucky_name = QLabel(f"{luckiest_pokemon}")
            lucky_name.setStyleSheet("color: #22c55e; font-size: 16px; font-weight: bold;")
            
            lucky_count = QLabel(f"{luckiest_count} 只污染")
            lucky_count.setStyleSheet("color: #a1a1aa; font-size: 13px;")
            
            lucky_info_layout.addWidget(lucky_title)
            lucky_info_layout.addWidget(lucky_name)
            lucky_info_layout.addWidget(lucky_count)
            
            lucky_layout.addWidget(lucky_info)
            lucky_layout.addStretch()
            left_layout.addWidget(lucky_row)
            
            # 分隔线
            separator = QFrame()
            separator.setFixedHeight(1)
            separator.setStyleSheet("background-color: rgba(124, 58, 237, 0.2);")
            left_layout.addWidget(separator)
            
            # 最非精灵
            unlucky_row = QWidget()
            unlucky_layout = QHBoxLayout(unlucky_row)
            unlucky_layout.setContentsMargins(0, 0, 0, 0)
            unlucky_layout.setSpacing(12)
            
            unlucky_icon = QLabel("💀")
            unlucky_icon.setStyleSheet("font-size: 24px;")
            unlucky_layout.addWidget(unlucky_icon)
            
            unlucky_info = QWidget()
            unlucky_info_layout = QVBoxLayout(unlucky_info)
            unlucky_info_layout.setContentsMargins(0, 0, 0, 0)
            unlucky_info_layout.setSpacing(4)
            
            unlucky_title = QLabel("最非精灵")
            unlucky_title.setStyleSheet("color: #71717a; font-size: 12px;")
            
            unlucky_name = QLabel(f"{unluckiest_pokemon}")
            unlucky_name.setStyleSheet("color: #ef4444; font-size: 16px; font-weight: bold;")
            
            unlucky_count = QLabel(f"{unluckiest_count} 只污染")
            unlucky_count.setStyleSheet("color: #a1a1aa; font-size: 13px;")
            
            unlucky_info_layout.addWidget(unlucky_title)
            unlucky_info_layout.addWidget(unlucky_name)
            unlucky_info_layout.addWidget(unlucky_count)
            
            unlucky_layout.addWidget(unlucky_info)
            unlucky_layout.addStretch()
            left_layout.addWidget(unlucky_row)
            
            main_layout.addWidget(left_widget, stretch=1)
            
            # 右侧：总体评级（只在全部记录时显示）
            if self.shiny_current_period == "all":
                total_shiny_count = 0
                total_pollution = 0
                
                for record in records:
                    if record['is_shiny']:
                        total_shiny_count += 1
                        total_pollution += record['count']
                
                if total_shiny_count > 0:
                    avg_pollution = total_pollution / total_shiny_count
                else:
                    avg_pollution = 0
                
                # 判断评级
                if avg_pollution <= 15:
                    rating_text = "欧皇"
                    bg_color = "rgba(59, 130, 246, 0.2)"
                    text_color = "#fbbf24"
                    border_color = "rgba(59, 130, 246, 0.5)"
                elif avg_pollution <= 25:
                    rating_text = "欧"
                    bg_color = "rgba(59, 130, 246, 0.2)"
                    text_color = "#fbbf24"
                    border_color = "rgba(59, 130, 246, 0.5)"
                elif avg_pollution <= 35:
                    rating_text = "小欧"
                    bg_color = "rgba(59, 130, 246, 0.2)"
                    text_color = "#fbbf24"
                    border_color = "rgba(59, 130, 246, 0.5)"
                elif avg_pollution <= 50:
                    rating_text = "一般"
                    bg_color = "rgba(59, 130, 246, 0.2)"
                    text_color = "#fbbf24"
                    border_color = "rgba(59, 130, 246, 0.5)"
                elif avg_pollution <= 65:
                    rating_text = "小非"
                    bg_color = "rgba(255, 255, 255, 0.15)"
                    text_color = "#78350f"
                    border_color = "rgba(255, 255, 255, 0.3)"
                elif avg_pollution <= 70:
                    rating_text = "非"
                    bg_color = "rgba(255, 255, 255, 0.15)"
                    text_color = "#78350f"
                    border_color = "rgba(255, 255, 255, 0.3)"
                else:
                    rating_text = "非酋"
                    bg_color = "rgba(255, 255, 255, 0.15)"
                    text_color = "#78350f"
                    border_color = "rgba(255, 255, 255, 0.3)"
                
                rating_label = QLabel(rating_text)
                rating_label.setAlignment(Qt.AlignCenter)
                rating_label.setFixedSize(120, 120)
                rating_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: {bg_color};
                        color: {text_color};
                        border: 3px solid {border_color};
                        border-radius: 60px;
                        font-size: 32px;
                        font-weight: bold;
                        font-style: italic;
                    }}
                """)
                
                main_layout.addWidget(rating_label)
            
            stat_card_layout.addLayout(main_layout)
            self.shiny_stats_layout.addWidget(stat_card)
        else:
            no_data_card = QFrame()
            no_data_card.setStyleSheet("""
                QFrame {
                    background: linear-gradient(135deg, rgba(37, 37, 48, 0.7) 0%, rgba(21, 21, 28, 0.7) 100%);
                    border: 1px dashed rgba(124, 58, 237, 0.3);
                    border-radius: 12px;
                }
            """)
            no_data_layout = QVBoxLayout(no_data_card)
            no_data_layout.setContentsMargins(30, 40, 30, 40)
            no_data_layout.setSpacing(10)
            
            icon_label = QLabel()
            icon_label.setStyleSheet("font-size: 48px;")
            icon_label.setAlignment(Qt.AlignCenter)
            
            text_label = QLabel("暂无出闪记录")
            text_label.setStyleSheet("color: #71717a; font-size: 16px;")
            text_label.setAlignment(Qt.AlignCenter)
            
            hint_label = QLabel("快去抓宠吧，说不定下一次就出闪了！")
            hint_label.setStyleSheet("color: #52525b; font-size: 13px;")
            hint_label.setAlignment(Qt.AlignCenter)
            
            no_data_layout.addWidget(icon_label)
            no_data_layout.addWidget(text_label)
            no_data_layout.addWidget(hint_label)
            
            self.shiny_stats_layout.addWidget(no_data_card)
        
        # 显示详细记录
        if records:
            for record in reversed(records):
                record_card = QFrame()
                record_card.setStyleSheet("""
                    QFrame {
                        background: linear-gradient(90deg, rgba(37, 37, 48, 0.6) 0%, rgba(21, 21, 28, 0.6) 100%);
                        border-radius: 8px;
                    }
                """)
                record_layout = QHBoxLayout(record_card)
                record_layout.setContentsMargins(16, 12, 16, 12)
                record_layout.setSpacing(0)
                
                # 左侧信息（固定宽度）
                left_widget = QWidget()
                left_widget.setFixedWidth(120)
                left_layout = QVBoxLayout(left_widget)
                left_layout.setContentsMargins(0, 0, 0, 0)
                left_layout.setSpacing(6)
                
                name_label = QLabel(f"{record['pokemon_name']}")
                name_label.setStyleSheet("color: #f8f0ff; font-size: 15px; font-weight: 600;")
                
                time_label = QLabel(f"{record['date']}")
                time_label.setStyleSheet("color: #71717a; font-size: 12px;")
                
                left_layout.addWidget(name_label)
                left_layout.addWidget(time_label)
                
                record_layout.addWidget(left_widget)
                
                # 中间：横向柱状图
                bar_container = QFrame()
                bar_container.setFixedHeight(20)
                bar_container.setFixedWidth(350)
                bar_container.setStyleSheet("""
                    QFrame {
                        background-color: rgba(37, 37, 48, 0.5);
                        border-radius: 4px;
                    }
                """)
                bar_container_layout = QHBoxLayout(bar_container)
                bar_container_layout.setContentsMargins(2, 2, 2, 2)
                bar_container_layout.setSpacing(0)
                
                # 根据 count 确定颜色
                count = record['count']
                if 0 <= count < 30:
                    bar_color = '#22c55e'
                elif 30 <= count < 55:
                    bar_color = '#eab308'
                elif 55 <= count <= 80:
                    bar_color = '#78350f'
                else:
                    bar_color = '#a78bfa'
                
                # 柱子宽度根据 count 值计算
                bar_width = max(10, int(340 * count / 80))
                
                bar = QFrame()
                bar.setFixedWidth(bar_width)
                bar.setFixedHeight(16)
                bar.setStyleSheet(f"""
                    QFrame {{
                        background-color: {bar_color};
                        border-radius: 3px;
                    }}
                """)
                
                bar_container_layout.addWidget(bar, alignment=Qt.AlignLeft)
                record_layout.addWidget(bar_container)
                
                # 计数标签
                count_label = QLabel(f"{count}只")
                count_label.setStyleSheet("color: #71717a; font-size: 13px; font-weight: 500; margin-left: 8px;")
                
                # 评级标签
                rating_label = QLabel()
                rating_label.setFixedWidth(50)
                rating_label.setAlignment(Qt.AlignCenter)
                rating_label.setStyleSheet("margin-left: 4px;")
                
                if count >= 70:
                    rating_label.setText("非")
                    rating_label.setStyleSheet("""
                        QLabel {
                            color: #ef4444;
                            font-size: 16px;
                            font-weight: bold;
                            font-style: italic;
                        }
                    """)
                elif 0 <= count < 10:
                    rating_label.setText("欧皇")
                    rating_label.setStyleSheet("""
                        QLabel {
                            color: #22c55e;
                            font-size: 14px;
                            font-weight: bold;
                            font-style: italic;
                        }
                    """)
                elif 10 <= count < 20:
                    rating_label.setText("欧")
                    rating_label.setStyleSheet("""
                        QLabel {
                            color: #22c55e;
                            font-size: 15px;
                            font-weight: bold;
                            font-style: italic;
                        }
                    """)
                elif 20 <= count < 30:
                    rating_label.setText("小欧")
                    rating_label.setStyleSheet("""
                        QLabel {
                            color: #84cc16;
                            font-size: 15px;
                            font-weight: bold;
                            font-style: italic;
                        }
                    """)
                elif 30 <= count < 40:
                    rating_label.setText("一般般")
                    rating_label.setStyleSheet("""
                        QLabel {
                            color: #eab308;
                            font-size: 14px;
                            font-weight: bold;
                            font-style: italic;
                        }
                    """)
                elif 40 <= count < 50:
                    rating_label.setText("一般般")
                    rating_label.setStyleSheet("""
                        QLabel {
                            color: #f59e0b;
                            font-size: 14px;
                            font-weight: bold;
                            font-style: italic;
                        }
                    """)
                elif 50 <= count < 60:
                    rating_label.setText("小非")
                    rating_label.setStyleSheet("""
                        QLabel {
                            color: #f97316;
                            font-size: 15px;
                            font-weight: bold;
                            font-style: italic;
                        }
                    """)
                else:
                    rating_label.setText("")
                
                record_layout.addWidget(count_label)
                record_layout.addWidget(rating_label)
                
                # 结果标签（在最右边）
                record_layout.addStretch()
                
                result_badge = QLabel("出闪" if record['is_shiny'] else "未出闪")
                result_badge.setStyleSheet("""
                    QLabel {
                        background-color: """ + ('rgba(34, 197, 94, 0.15)' if record['is_shiny'] else 'rgba(124, 58, 237, 0.15)') + """;
                        color: """ + ('#22c55e' if record['is_shiny'] else '#a78bfa') + """;
                        border-radius: 2px;
                        padding: 0px 1px;
                        font-size: 11px;
                        font-weight: 600;
                    }
                """)
                
                record_layout.addWidget(result_badge)
                
                self.shiny_records_list_layout.addWidget(record_card)
    
    def on_clear_shiny_records(self):
        """清除所有出闪记录"""
        reply = QMessageBox.question(
            self,
            "确认清除",
            "确定要清除所有出闪记录吗？\n此操作无法撤销！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.manager.clear_all_shiny_records()
            self.refresh_shiny_records()
            QMessageBox.information(self, "成功", "✓ 所有出闪记录已清除！")

    # ================= 自动识别联动 =================
    def _create_settings_view(self):
        """创建设置页面视图 - 极简专业风格"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(SCROLL_BAR_STYLE)
        
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 顶部标题区
        header = QWidget()
        header.setStyleSheet("background-color: #1a1a22; border-bottom: 1px solid rgba(124, 58, 237, 0.1);")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(80, 60, 80, 60)
        header_layout.setSpacing(12)
        
        title = QLabel("⚙️ 助手设置")
        title.setStyleSheet("color: #ffffff; font-size: 32px; font-weight: bold;")
        header_layout.addWidget(title)
        
        subtitle = QLabel("配置助手的各项功能和参数，优化您的使用体验")
        subtitle.setStyleSheet("color: #71717a; font-size: 15px;")
        header_layout.addWidget(subtitle)
        
        main_layout.addWidget(header)
        
        # 内容区
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(80, 40, 80, 40)
        content_layout.setSpacing(32)
        
        # 通用设置
        self.minimize_tray_switch = ToggleSwitch()
        self.desktop_pet_switch = ToggleSwitch()
        
        general_section = self._create_clean_section(
            "🎯 通用设置",
            [
                ("关闭时最小化到托盘", "点击关闭按钮时隐藏到系统托盘", self.minimize_tray_switch),
                ("启用桌面宠物", "在桌面上显示可爱的桌宠精灵", self.desktop_pet_switch)
            ]
        )
        content_layout.addWidget(general_section)
        
        # 识别设置
        self.recognition_interval_spin = self._create_spin_input(100, 5000, 500, " ms")
        self.confidence_xt_spin = self._create_spin_input(0.5, 1.0, 0.7, "", 0.05, True)
        self.confidence_pollution_spin = self._create_spin_input(0.5, 1.0, 0.75, "", 0.05, True)
        self.ocr_confidence_spin = self._create_spin_input(0.3, 1.0, 0.5, "", 0.05, True)
        
        # 识别间隔输入验证
        def validate_interval(value):
            if value < 100:
                self.recognition_interval_spin.setValue(100)
                logger.log(f"⚠️ 识别间隔不能小于100ms，已自动调整")
            elif value > 5000:
                self.recognition_interval_spin.setValue(5000)
                logger.log(f"⚠️ 识别间隔不能大于5000ms，已自动调整")
        
        self.recognition_interval_spin.valueChanged.connect(validate_interval)
        
        ocr_section = self._create_clean_section(
            "🔍 图像识别设置",
            [
                ("识别间隔", "两次识别之间的时间间隔（100-5000ms），间隔越小识别越频繁但CPU占用越高", self.recognition_interval_spin),
                ("nl识别置信度", "nl 图标的识别阈值，越高越准确", self.confidence_xt_spin),
                ("童话事件置信度", "童话事件模板的识别阈值，越高越准确", self.confidence_pollution_spin),
                ("OCR文字置信度", "OCR文字识别的置信度阈值，越高越严格", self.ocr_confidence_spin)
            ]
        )
        content_layout.addWidget(ocr_section)
        
        # 地图设置
        self.map_update_interval_spin = self._create_spin_input(1, 10, 3, " 帧")
        self.use_real_pointer_switch = ToggleSwitch()
        self.use_real_pointer_switch.setChecked(True)
        self.resource_icon_size_spin = self._create_spin_input(8, 64, 24, " px", step=2)

        map_section = self._create_clean_section(
            "🗺️ 地图导航设置",
            [
                ("地图更新间隔", "每N帧更新一次地图识别，帧数越小更新越快但CPU占用越高（范围1-10帧）", self.map_update_interval_spin),
                ("启用真实指针", "开启后使用游戏真实指针图标；关闭后使用绿色方向指针（朝移动方向）", self.use_real_pointer_switch),
                ("资源点大小", "资源栏与其余栏资源图标的基准大小（8-64px，随地图缩放等比放大）", self.resource_icon_size_spin)
            ]
        )
        content_layout.addWidget(map_section)
        
        # 计数器设置
        self.default_target_spin = self._create_spin_input(10, 999, 80, "")
        self.auto_save_interval_spin = self._create_spin_input(1, 60, 5, " 分钟")
        self.auto_save_switch = ToggleSwitch()
        self.breakthrough_notification_switch = ToggleSwitch()
        
        counter_section = self._create_clean_section(
            "📊 计数器默认设置",
            [
                ("默认保底次数", "新建计数器时的默认目标次数", self.default_target_spin),
                ("自动保存间隔", "每隔X分钟自动保存一次数据", self.auto_save_interval_spin),
                ("自动保存进度", "计数变化时自动保存到本地", self.auto_save_switch),
                ("保底通知提醒", "达到保底次数时弹出系统通知", self.breakthrough_notification_switch)
            ]
        )
        content_layout.addWidget(counter_section)
        
        # 高级设置
        self.detailed_log_switch = ToggleSwitch()
        self.performance_monitor_switch = ToggleSwitch()
        self.performance_charts_switch = ToggleSwitch()
        
        advanced_section = self._create_clean_section(
            "⚡ 高级设置",
            [
                ("调试输出", "打开调试窗口查看实时日志", self.detailed_log_switch),
                ("显示性能监控", "在悬浮窗显示帧率和内存占用", self.performance_monitor_switch),
                ("└─ 显示曲线图", "性能监控开启时，数据显示下方显示实时曲线", self.performance_charts_switch)
            ]
        )
        content_layout.addWidget(advanced_section)
        
        # 悬浮窗设置
        size_map = {"small": "小尺寸", "medium": "中尺寸", "large": "大尺寸"}
        current_size_key = self.settings_manager.get("floating_window_size", "medium")
        current_size_text = size_map.get(current_size_key, "中尺寸")
        self.floating_size_combo = self._create_combo_box(
            ["小尺寸", "中尺寸", "大尺寸"],
            current_size_text
        )

        current_opacity = self.settings_manager.get("floating_window_opacity", 0.7)

        opacity_container = QWidget()
        opacity_layout = QHBoxLayout(opacity_container)
        opacity_layout.setContentsMargins(0, 0, 0, 0)
        opacity_layout.setSpacing(8)

        self.floating_opacity_slider = QSlider(Qt.Horizontal)
        self.floating_opacity_slider.setRange(10, 100)
        self.floating_opacity_slider.setValue(int(current_opacity * 100))
        self.floating_opacity_slider.setFixedWidth(160)
        self.floating_opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #252530;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #7c3aed;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #a78bfa;
            }
            QSlider::sub-page:horizontal {
                background: #6d28d9;
                border-radius: 3px;
            }
        """)

        self.floating_opacity_spin = QDoubleSpinBox()
        self.floating_opacity_spin.setRange(0.1, 1.0)
        self.floating_opacity_spin.setSingleStep(0.05)
        self.floating_opacity_spin.setValue(current_opacity)
        self.floating_opacity_spin.setFixedWidth(70)
        self.floating_opacity_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 6px;
                padding: 6px 8px;
                color: #e4e4e7;
                font-size: 13px;
            }
            QDoubleSpinBox:hover {
                border-color: #7c3aed;
            }
        """)

        self.floating_opacity_slider.valueChanged.connect(
            lambda v: self.floating_opacity_spin.setValue(v / 100.0))
        self.floating_opacity_spin.valueChanged.connect(
            lambda v: self.floating_opacity_slider.setValue(int(v * 100)))
        self.floating_opacity_slider.valueChanged.connect(self._on_opacity_changed)

        opacity_layout.addWidget(self.floating_opacity_slider)
        opacity_layout.addWidget(self.floating_opacity_spin)
        opacity_layout.addStretch()

        floating_section = self._create_clean_section(
            "🪟 悬浮窗设置",
            [
                ("悬浮窗大小", "选择悬浮窗的显示尺寸", self.floating_size_combo),
                ("悬浮窗透明度", "拖动滑条调整悬浮窗透明度（0.1=几乎透明, 1.0=完全不透明）", opacity_container)
            ]
        )
        content_layout.addWidget(floating_section)
        
        # 界面大小设置
        ui_size_map = {"small": "小", "medium": "中", "large": "大"}
        current_ui_size_key = self.settings_manager.get("ui_scale", "large")
        current_ui_size_text = ui_size_map.get(current_ui_size_key, "大")
        self.ui_size_combo = self._create_combo_box(
            ["小", "中", "大"],
            current_ui_size_text
        )
        
        ui_size_section = self._create_clean_section(
            "🎨 界面设置",
            [
                ("界面大小", "选择程序界面的显示尺寸\n小：紧凑布局，适合低分辨率\n中：平衡布局\n大：宽松布局，适合高分辨率", self.ui_size_combo)
            ]
        )
        content_layout.addWidget(ui_size_section)
        
        # 全局追踪设置
        self.global_tracking_switch = ToggleSwitch()
        self.global_tracking_switch.setChecked(self.settings_manager.get("enable_global_tracking", True))
        
        tracking_section = self._create_clean_section(
            "📊 全局追踪设置",
            [
                ("启用全局追踪", 
                 "记录所有检测到的童话事件，即使未创建对应计数器", 
                 self.global_tracking_switch)
            ]
        )
        content_layout.addWidget(tracking_section)

        # 多窗口选择设置（独立区域）
        window_select_section = QWidget()
        window_select_section_layout = QVBoxLayout(window_select_section)
        window_select_section_layout.setContentsMargins(0, 0, 0, 0)
        window_select_section_layout.setSpacing(16)

        window_select_title = QLabel("游戏窗口选择")
        window_select_title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 600;")
        window_select_section_layout.addWidget(window_select_title)

        window_select_card = QFrame()
        window_select_card.setStyleSheet("""
            QFrame {
                background-color: #1e1e26;
                border: none;
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #252530;
            }
        """)
        window_select_card_layout = QVBoxLayout(window_select_card)
        window_select_card_layout.setContentsMargins(24, 18, 24, 18)
        window_select_card_layout.setSpacing(10)

        window_select_header = QHBoxLayout()
        window_select_header.setContentsMargins(0, 0, 0, 0)

        window_select_label = QLabel("选择游戏窗口")
        window_select_label.setStyleSheet("color: #e2e8f0; font-size: 14px; font-weight: 500;")
        window_select_header.addWidget(window_select_label)
        window_select_header.addStretch()

        # 预览按钮（可勾选，放在刷新按钮左边）
        self.window_preview_btn = QPushButton("预览")
        self.window_preview_btn.setCheckable(True)
        self.window_preview_btn.setFixedSize(60, 28)
        self.window_preview_btn.setCursor(Qt.PointingHandCursor)
        self.window_preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #252530;
                color: #a78bfa;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2a2a35;
                border-color: #7c3aed;
            }
            QPushButton:checked {
                background-color: #7c3aed;
                color: #ffffff;
                border-color: #a855f7;
            }
        """)
        self.window_preview_btn.toggled.connect(self._on_window_preview_toggled)
        window_select_header.addWidget(self.window_preview_btn)

        self.window_refresh_btn = QPushButton("刷新")
        self.window_refresh_btn.setFixedSize(60, 28)
        self.window_refresh_btn.setCursor(Qt.PointingHandCursor)
        self.window_refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #252530;
                color: #a78bfa;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2a2a35;
                border-color: #7c3aed;
            }
        """)
        self.window_refresh_btn.clicked.connect(self._refresh_window_list)
        window_select_header.addWidget(self.window_refresh_btn)

        window_select_card_layout.addLayout(window_select_header)

        self.window_select_combo = TriangleComboBox()
        self.window_select_combo.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 6px;
                padding: 8px 12px;
                color: #e2e8f0;
                font-size: 13px;
                min-width: 120px;
            }
            QComboBox:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.3);
                color: #e2e8f0;
                selection-background-color: rgba(124, 58, 237, 0.3);
                padding: 4px;
            }
        """)
        self.window_select_combo.currentIndexChanged.connect(self._on_window_selected)
        window_select_card_layout.addWidget(self.window_select_combo)

        window_select_desc = QLabel("当检测到多个游戏窗口时，可选择要识别的目标窗口")
        window_select_desc.setStyleSheet("color: #71717a; font-size: 12px;")
        window_select_desc.setWordWrap(True)
        window_select_card_layout.addWidget(window_select_desc)

        # 游戏窗口预览画面标签（默认隐藏）
        self.window_preview_label = QLabel("暂无预览画面")
        self.window_preview_label.setAlignment(Qt.AlignCenter)
        self.window_preview_label.setFixedHeight(220)
        self.window_preview_label.setStyleSheet("""
            QLabel {
                background-color: #000000;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 6px;
                color: #71717a;
                font-size: 13px;
            }
        """)
        self.window_preview_label.hide()
        window_select_card_layout.addWidget(self.window_preview_label)

        # 预览刷新定时器
        self.window_preview_timer = QTimer(self)
        self.window_preview_timer.setInterval(200)
        self.window_preview_timer.timeout.connect(self._update_window_preview)

        window_select_section_layout.addWidget(window_select_card)
        content_layout.addWidget(window_select_section)

        # 框选识别设置
        roi_select_btn = QPushButton("📸 框选识别区域")
        roi_select_btn.setFixedHeight(44)
        roi_select_btn.setCursor(Qt.PointingHandCursor)
        roi_select_btn.setStyleSheet("""
            QPushButton {
                background-color: #7c3aed;
                color: #ffffff;
                border: 2px solid #a855f7;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #6d28d9;
                border-color: #c084fc;
            }
            QPushButton:pressed {
                background-color: #5b21b6;
            }
        """)
        roi_select_btn.clicked.connect(self.on_roi_select)
        
        roi_info_label = QLabel("通过框选指定识别区域，可解决不同分辨率下的识别问题")
        roi_info_label.setStyleSheet("color: #71717a; font-size: 13px; padding: 8px 0;")
        roi_info_label.setWordWrap(True)
        
        # 启用坐标识别开关
        self.roi_recognition_switch = ToggleSwitch()
        
        roi_section = self._create_clean_section(
            "🎯 框选识别设置",
            [
                ("启用坐标识别", "启用后使用框选坐标识别方式  <span style='color:#ef4444;font-weight:600;'>⚠️ 非极端分辨率请勿开启</span>", self.roi_recognition_switch),
                ("", "", roi_select_btn)
            ]
        )
        content_layout.addWidget(roi_section)

        # 血脉识别设置（配合童话事件使用）
        bloodline_section = QWidget()
        bloodline_section_layout = QVBoxLayout(bloodline_section)
        bloodline_section_layout.setContentsMargins(0, 0, 0, 0)
        bloodline_section_layout.setSpacing(16)

        bloodline_title = QLabel("血脉识别设置")
        bloodline_title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 600;")
        bloodline_section_layout.addWidget(bloodline_title)

        bloodline_card = QFrame()
        bloodline_card.setStyleSheet("""
            QFrame {
                background-color: #1e1e26;
                border: none;
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #252530;
            }
        """)
        bloodline_card_layout = QVBoxLayout(bloodline_card)
        bloodline_card_layout.setContentsMargins(24, 18, 24, 18)
        bloodline_card_layout.setSpacing(12)

        # 血脉识别开关
        bloodline_toggle_row = QHBoxLayout()
        bloodline_toggle_row.setContentsMargins(0, 0, 0, 0)

        bloodline_toggle_title = QLabel("启用血脉识别")
        bloodline_toggle_title.setStyleSheet("color: #e2e8f0; font-size: 14px; font-weight: 500;")
        bloodline_toggle_row.addWidget(bloodline_toggle_title)
        bloodline_toggle_row.addStretch()

        self.bloodline_recognition_switch = ToggleSwitch()
        bloodline_toggle_row.addWidget(self.bloodline_recognition_switch)

        bloodline_card_layout.addLayout(bloodline_toggle_row)

        # 分隔线
        bloodline_separator = QFrame()
        bloodline_separator.setFrameShape(QFrame.HLine)
        bloodline_separator.setStyleSheet("background-color: #2a2a35; max-height: 1px;")
        bloodline_card_layout.addWidget(bloodline_separator)

        # 框选按钮（蓝色）
        bloodline_select_btn = QPushButton("血脉识别框选")
        bloodline_select_btn.setFixedHeight(44)
        bloodline_select_btn.setCursor(Qt.PointingHandCursor)
        bloodline_select_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                border: 2px solid #3b82f6;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
                border-color: #60a5fa;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
        """)
        bloodline_select_btn.clicked.connect(self.on_bloodline_select)

        bloodline_info = QLabel("框选血脉识别区域，配合童话事件自动识别 奇异/污染/混乱/异色 血脉（为了流畅，最好只框选提示区域，而非整个屏幕）")
        bloodline_info.setStyleSheet("color: #71717a; font-size: 13px;")
        bloodline_info.setWordWrap(True)

        # 显示当前血脉框选区域
        self.bloodline_roi_label = QLabel("当前未设置血脉框选区域")
        self.bloodline_roi_label.setStyleSheet("color: #e2e8f0; font-size: 13px; padding: 12px; background-color: #252530; border-radius: 6px;")

        bloodline_card_layout.addWidget(bloodline_info)
        bloodline_card_layout.addWidget(bloodline_select_btn)
        bloodline_card_layout.addWidget(self.bloodline_roi_label)

        bloodline_section_layout.addWidget(bloodline_card)
        content_layout.addWidget(bloodline_section)

        # 热键设置
        hotkey_section = QWidget()
        hotkey_section_layout = QVBoxLayout(hotkey_section)
        hotkey_section_layout.setContentsMargins(0, 0, 0, 0)
        hotkey_section_layout.setSpacing(16)

        hotkey_title = QLabel("热键设置")
        hotkey_title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 600;")
        hotkey_section_layout.addWidget(hotkey_title)

        hotkey_card = QFrame()
        hotkey_card.setStyleSheet("""
            QFrame {
                background-color: #1e1e26;
                border: none;
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #252530;
            }
        """)
        hotkey_card_layout = QVBoxLayout(hotkey_card)
        hotkey_card_layout.setContentsMargins(24, 18, 24, 18)
        hotkey_card_layout.setSpacing(0)

        self.hotkey_labels = {}
        self._hotkey_configs = {}

        hotkey_functions = [
            ("toggle_passthrough", "切换鼠标穿透（抓宠）", "Ctrl + N"),
            ("map_toggle_passthrough", "切换鼠标穿透（地图）", "Alt + M"),
            ("count_plus", "童话事件 +1", "+"),
            ("count_minus", "童话事件 -1", "-"),
            ("counter_prev", "上一个计数器", "["),
            ("counter_next", "下一个计数器", "]"),
            ("nightmare_plus", "童话提示 +1", "》"),
            ("nightmare_minus", "童话提示 -1", "《"),
        ]

        for i, (hk_id, func_name, default_display) in enumerate(hotkey_functions):
            hk_config = self.settings_manager.get("hotkeys", {}).get(hk_id, {})
            display = hk_config.get("display", default_display)

            row = QHBoxLayout()
            row.setContentsMargins(0, 8, 0, 8)
            row.setSpacing(12)

            func_label = QLabel(func_name)
            func_label.setStyleSheet("color: #e2e8f0; font-size: 13px;")
            func_label.setFixedWidth(140)
            row.addWidget(func_label)

            key_label = QLabel(display)
            key_label.setStyleSheet("""
                color: #a78bfa; font-size: 13px; font-weight: 600;
                background-color: #252530; border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 4px; padding: 4px 12px;
            """)
            key_label.setAlignment(Qt.AlignCenter)
            key_label.setFixedWidth(120)
            row.addWidget(key_label)

            self.hotkey_labels[hk_id] = key_label
            self._hotkey_configs[hk_id] = hk_config

            change_btn = QPushButton("更改")
            change_btn.setFixedSize(56, 28)
            change_btn.setCursor(Qt.PointingHandCursor)
            change_btn.setStyleSheet("""
                QPushButton {
                    background-color: #252530;
                    color: #94a3b8;
                    border: 1px solid #3f3f46;
                    border-radius: 4px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #2a2a35;
                    border-color: #7c3aed;
                    color: #a78bfa;
                }
            """)
            change_btn.clicked.connect(lambda checked, h=hk_id: self._on_change_hotkey(h))
            row.addWidget(change_btn)

            row.addStretch()

            hotkey_card_layout.addLayout(row)

            if i < len(hotkey_functions) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                sep.setStyleSheet("background-color: #2a2a35; max-height: 1px;")
                hotkey_card_layout.addWidget(sep)

        hotkey_section_layout.addWidget(hotkey_card)
        content_layout.addWidget(hotkey_section)

        # 数据管理按钮
        data_manage_widget = QWidget()
        data_manage_layout = QHBoxLayout(data_manage_widget)
        data_manage_layout.setContentsMargins(0, 0, 0, 0)
        data_manage_layout.setSpacing(12)
        
        manage_btn = QPushButton("查看统计数据")
        manage_btn.setFixedHeight(36)
        manage_btn.setCursor(Qt.PointingHandCursor)
        manage_btn.setStyleSheet("""
            QPushButton {
                background-color: #252530;
                color: #a78bfa;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 6px;
                font-size: 13px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #2a2a35;
                border-color: #7c3aed;
            }
        """)
        manage_btn.clicked.connect(self.on_view_global_stats)
        data_manage_layout.addWidget(manage_btn)
        
        clear_btn = QPushButton("清空追踪数据")
        clear_btn.setFixedHeight(36)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #252530;
                color: #ef4444;
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 6px;
                font-size: 13px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #2a2a35;
                border-color: #ef4444;
            }
        """)
        clear_btn.clicked.connect(self.on_clear_global_stats)
        data_manage_layout.addWidget(clear_btn)
        data_manage_layout.addStretch()
        
        content_layout.addWidget(data_manage_widget)

        # 版本信息与更新区
        try:
            from core.update_manager import CURRENT_VERSION
        except Exception:
            CURRENT_VERSION = "4.6.12"

        version_section = QWidget()
        version_section_layout = QVBoxLayout(version_section)
        version_section_layout.setContentsMargins(0, 0, 0, 0)
        version_section_layout.setSpacing(12)

        version_title = QLabel("📦 版本信息")
        version_title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 600;")
        version_section_layout.addWidget(version_title)

        version_card = QFrame()
        version_card.setStyleSheet("""
            QFrame {
                background-color: #1e1e26;
                border: none;
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #252530;
            }
        """)
        version_card_layout = QHBoxLayout(version_card)
        version_card_layout.setContentsMargins(24, 18, 24, 18)
        version_card_layout.setSpacing(16)

        cur_version_label = QLabel(f"当前版本：v{CURRENT_VERSION}")
        cur_version_label.setStyleSheet("color: #e2e8f0; font-size: 14px; font-weight: 500;")
        version_card_layout.addWidget(cur_version_label)

        version_card_layout.addStretch()

        # 最新版本号显示（点击检查更新后显示）
        self.latest_version_label = QLabel("")
        self.latest_version_label.setStyleSheet("color: #71717a; font-size: 13px;")
        version_card_layout.addWidget(self.latest_version_label)

        # 检查更新按钮
        self.check_update_btn = QPushButton("🔍 检查更新")
        self.check_update_btn.setFixedHeight(36)
        self.check_update_btn.setMinimumWidth(120)
        self.check_update_btn.setCursor(Qt.PointingHandCursor)
        self.check_update_btn.setStyleSheet("""
            QPushButton {
                background-color: #252530;
                color: #a78bfa;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                padding: 0 18px;
            }
            QPushButton:hover {
                background-color: #2a2a35;
                border-color: #7c3aed;
                color: #c4b5fd;
            }
            QPushButton:disabled {
                color: #64748b;
                background-color: #1e1e26;
            }
        """)
        self.check_update_btn.clicked.connect(self._on_check_update)
        version_card_layout.addWidget(self.check_update_btn)

        version_section_layout.addWidget(version_card)
        content_layout.addWidget(version_section)

        content_layout.addStretch()
        main_layout.addWidget(content_widget)
        
        # 底部操作栏
        footer = QWidget()
        footer.setStyleSheet("background-color: #1a1a22; border-top: 1px solid rgba(124, 58, 237, 0.1);")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(80, 24, 80, 24)
        
        tip_label = QLabel("💡 修改设置后需要重启助手才能完全生效")
        tip_label.setStyleSheet("color: #a78bfa; font-size: 13px;")
        footer_layout.addWidget(tip_label)
        
        footer_layout.addStretch()
        
        # 异常重启按钮（独立不耦合，模板崩溃也可用）
        emergency_btn = QPushButton("🔴 异常重启")
        emergency_btn.setFixedHeight(40)
        emergency_btn.setMinimumWidth(120)
        emergency_btn.setCursor(Qt.PointingHandCursor)
        emergency_btn.setStyleSheet("""
            QPushButton {
                background-color: #7f1d1d;
                color: #fca5a5;
                border: 2px solid #dc2626;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #991b1b;
                border-color: #ef4444;
                color: #fecaca;
            }
            QPushButton:pressed {
                background-color: #450a0a;
            }
        """)
        emergency_btn.clicked.connect(self._emergency_restart_all)
        footer_layout.addWidget(emergency_btn)
        
        reset_btn = QPushButton("恢复默认")
        reset_btn.setFixedHeight(40)
        reset_btn.setMinimumWidth(110)
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #252530;
                color: #a1a1aa;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #2a2a35;
                color: #e4e4e7;
            }
            QPushButton:pressed {
                background-color: #1e1e26;
            }
        """)
        reset_btn.clicked.connect(self.on_reset_settings)
        footer_layout.addWidget(reset_btn)
        
        save_btn = QPushButton("保存设置")
        save_btn.setFixedHeight(40)
        save_btn.setMinimumWidth(110)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #7c3aed;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #8b5cf6;
            }
            QPushButton:pressed {
                background-color: #6d28d9;
            }
        """)
        save_btn.clicked.connect(self.on_save_settings)
        footer_layout.addWidget(save_btn)
        
        main_layout.addWidget(footer)
        
        scroll.setWidget(container)
        return scroll
    
    # ================= 孵蛋预测视图 =================
    def _create_egg_prediction_view(self):
        """创建孵蛋预测界面"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(SCROLL_BAR_STYLE)
        container = QWidget()
        container.setObjectName("mainContent")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(24)
        
        # 标题区
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(12)
        
        icon_label = QLabel("🥚")
        icon_label.setStyleSheet("font-size: 24px;")
        title_layout.addWidget(icon_label)
        
        title = QLabel("孵蛋预测")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #f8f0ff;")
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        layout.addWidget(title_bar)
        
        # 说明文字
        desc_label = QLabel("输入精灵蛋的身高和体重数值，系统将为您预测可能孵化出的精灵")
        desc_label.setStyleSheet("color: #a1a1aa; font-size: 14px; padding-left: 36px;")
        layout.addWidget(desc_label)
        
        # 输入面板
        input_panel = QFrame()
        input_panel.setStyleSheet("""
            QFrame {
                background-color: #1e1e26;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 12px;
                padding: 24px;
            }
        """)
        input_layout = QVBoxLayout(input_panel)
        input_layout.setSpacing(20)
        
        # 身高输入行
        height_row = QWidget()
        height_layout = QHBoxLayout(height_row)
        height_layout.setContentsMargins(0, 0, 0, 0)
        height_layout.setSpacing(16)
        
        height_label = QLabel("蛋身高 (m):")
        height_label.setStyleSheet("color: #e4e4e7; font-size: 14px; font-weight: 500;")
        height_label.setFixedWidth(100)
        height_layout.addWidget(height_label)
        
        self.egg_height_input = QLineEdit()
        self.egg_height_input.setPlaceholderText("例如: 0.18")
        self.egg_height_input.setStyleSheet("""
            QLineEdit {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 6px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #7c3aed;
                background-color: #2a2a35;
            }
        """)
        height_layout.addWidget(self.egg_height_input, stretch=1)
        
        input_layout.addWidget(height_row)
        
        # 体重输入行
        weight_row = QWidget()
        weight_layout = QHBoxLayout(weight_row)
        weight_layout.setContentsMargins(0, 0, 0, 0)
        weight_layout.setSpacing(16)
        
        weight_label = QLabel("蛋体重 (kg):")
        weight_label.setStyleSheet("color: #e4e4e7; font-size: 14px; font-weight: 500;")
        weight_label.setFixedWidth(100)
        weight_layout.addWidget(weight_label)
        
        self.egg_weight_input = QLineEdit()
        self.egg_weight_input.setPlaceholderText("例如: 3.585")
        self.egg_weight_input.setStyleSheet("""
            QLineEdit {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 6px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #7c3aed;
                background-color: #2a2a35;
            }
        """)
        weight_layout.addWidget(self.egg_weight_input, stretch=1)
        
        input_layout.addWidget(weight_row)
        
        # 预测按钮
        predict_btn = QPushButton("🔍 开始预测")
        predict_btn.setFixedHeight(44)
        predict_btn.setCursor(Qt.PointingHandCursor)
        predict_btn.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c3aed, stop:1 #a855f7);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 600;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9333ea, stop:1 #c084fc);
            }
            QPushButton:pressed {
                background-color: #6d28d9;
            }
        """)
        predict_btn.clicked.connect(self._on_predict_eggs)
        input_layout.addWidget(predict_btn)
        
        layout.addWidget(input_panel)
        
        # 结果展示区
        result_section = QWidget()
        result_layout = QVBoxLayout(result_section)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(16)
        
        result_title = QLabel("预测结果")
        result_title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 600;")
        result_layout.addWidget(result_title)
        
        # 结果列表容器
        self.egg_result_container = QFrame()
        self.egg_result_container.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        self.egg_result_layout = QVBoxLayout(self.egg_result_container)
        self.egg_result_layout.setContentsMargins(0, 0, 0, 0)
        self.egg_result_layout.setSpacing(12)
        
        # 初始提示
        empty_hint = QLabel("请输入蛋的身高和体重，然后点击“开始预测”")
        empty_hint.setStyleSheet("color: #71717a; font-size: 14px; padding: 40px 20px;")
        empty_hint.setAlignment(Qt.AlignCenter)
        self.egg_result_layout.addWidget(empty_hint)
        
        result_layout.addWidget(self.egg_result_container)
        layout.addWidget(result_section)
        
        layout.addStretch()
        scroll.setWidget(container)
        return scroll
    
    def _on_predict_eggs(self):
        """执行孵蛋预测"""
        import json
        try:
            # 获取输入值
            height_str = self.egg_height_input.text().strip()
            weight_str = self.egg_weight_input.text().strip()
            
            if not height_str or not weight_str:
                QMessageBox.warning(self, "提示", "请输入蛋的身高和体重")
                return
            
            egg_height = float(height_str)
            egg_weight = float(weight_str)
            
            # 读取精灵数据
            data_file = os.path.join(self._base_dir, "image", "tj", "pokemon_data.json")
            with open(data_file, 'r', encoding='utf-8') as f:
                pokemons = json.load(f)
            
            # 自动从进化链判断基础形态（进化链第一个就是基础形态）
            base_forms = set()
            for pokemon in pokemons:
                chain = pokemon.get('evolution_chain', [])
                if chain and chain[0].get('name') == pokemon.get('name', ''):
                    base_forms.add(pokemon['name'])
            
            # 计算匹配度并筛选
            results = []
            for pokemon in pokemons:
                name = pokemon['name']
                
                # 只保留基础形态（可以从蛋中孵化的精灵）
                if name not in base_forms:
                    continue
                
                height_range = pokemon.get('height', '')
                weight_range = pokemon.get('weight', '')
                
                if not height_range or not weight_range:
                    continue
                
                # 解析身高范围
                height_parts = height_range.split('~')
                hl = float(height_parts[0])
                hu = float(height_parts[1])
                
                # 解析体重范围
                weight_parts = weight_range.split('~')
                vl = float(weight_parts[0])
                vu = float(weight_parts[1])
                
                # 计算理论蛋的身高体重范围
                calc_egg_hl = round(hl * 0.42, 2)
                calc_egg_hu = round(hu * 0.42, 2)
                calc_egg_wl = round(vl * 0.35, 2)
                calc_egg_wu = round(vu * 0.40, 2)
                
                # 特殊精灵的蛋数据调整
                if name == '火红尾':
                    calc_egg_hu = 0.61
                    calc_egg_wu = 15.0
                elif name == '大耳帽兜':
                    calc_egg_hu = 0.20
                
                # 检查是否在范围内
                height_match = calc_egg_hl <= egg_height <= calc_egg_hu
                weight_match = calc_egg_wl <= egg_weight <= calc_egg_wu
                
                if height_match and weight_match:
                    # 计算符合度（距离中心点的距离）
                    height_center = (calc_egg_hl + calc_egg_hu) / 2
                    weight_center = (calc_egg_wl + calc_egg_wu) / 2
                    
                    height_dist = abs(egg_height - height_center) / max(calc_egg_hu - calc_egg_hl, 0.01)
                    weight_dist = abs(egg_weight - weight_center) / max(calc_egg_wu - calc_egg_wl, 0.01)
                    
                    total_dist = height_dist + weight_dist
                    match_score = max(0, 100 - total_dist * 50)  # 转换为百分制
                    
                    results.append({
                        'id': pokemon.get('id', 0),
                        'name': name,
                        'height_range': f"{calc_egg_hl:.2f}~{calc_egg_hu:.2f}",
                        'weight_range': f"{calc_egg_wl:.2f}~{calc_egg_wu:.2f}",
                        'score': match_score,
                        'attribute': pokemon.get('attribute', ''),
                        'image_url': pokemon.get('image_url', '')
                    })
            
            # 按符合度排序
            results.sort(key=lambda x: x['score'], reverse=True)
            
            # 显示结果
            self._display_egg_results(results)
            
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效的数字")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"预测失败: {str(e)}")
    
    def _display_egg_results(self, results):
        """显示预测结果"""
        # 清空现有结果
        while self.egg_result_layout.count():
            item = self.egg_result_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not results:
            no_result = QLabel("未找到匹配的精灵，请尝试调整输入值")
            no_result.setStyleSheet("color: #71717a; font-size: 14px; padding: 40px 20px;")
            no_result.setAlignment(Qt.AlignCenter)
            self.egg_result_layout.addWidget(no_result)
            return
        
        # 显示结果数量
        count_label = QLabel(f"共找到 {len(results)} 个可能的精灵")
        count_label.setStyleSheet("color: #a78bfa; font-size: 13px; margin-bottom: 8px;")
        self.egg_result_layout.addWidget(count_label)
        
        # 显示每个结果
        for i, result in enumerate(results):
            card = self._create_egg_result_card(result, i + 1)
            self.egg_result_layout.addWidget(card)
    
    def _create_egg_result_card(self, result, rank):
        """创建结果卡片"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e1e26;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 10px;
                padding: 16px;
            }
            QFrame:hover {
                background-color: #252530;
                border-color: rgba(124, 58, 237, 0.4);
            }
        """)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(16)
        
        # 排名
        rank_label = QLabel(f"#{rank}")
        rank_label.setStyleSheet("""
            QLabel {
                background-color: rgba(124, 58, 237, 0.2);
                color: #a78bfa;
                border-radius: 12px;
                padding: 6px 10px;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        rank_label.setFixedWidth(50)
        rank_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(rank_label)
        
        # 精灵头像
        icon_label = QLabel()
        icon_label.setFixedSize(56, 56)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                padding: 0px;
                margin: 0px;
            }
        """)
        
        # 尝试加载图片：从tj/images文件夹按ID加载
        pokemon_id = result.get('id', 0)
        image_dir = os.path.join(self._base_dir, "image", "tj", "images")
        
        loaded = False
        if pokemon_id > 0 and os.path.exists(image_dir):
            from PySide6.QtGui import QPixmap
            
            # 按ID查找图片（如 001.png, 002.png）
            image_filename = f"{pokemon_id:03d}.png"
            image_path = os.path.join(image_dir, image_filename)
            
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    target_pixmap = self._create_rounded_pixmap(pixmap, 56)
                    icon_label.setPixmap(target_pixmap)
                    loaded = True
        
        if not loaded:
            # 默认图标
            icon_label.setText(pokemon_name[0] if pokemon_name else "?")
            icon_label.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6c5ce7, stop:1 #a855f7);
                    border-radius: 28px;
                    color: white;
                    font-size: 24px;
                    font-weight: bold;
                    padding: 0px;
                    margin: 0px;
                }
            """)
        card_layout.addWidget(icon_label)
        
        # 信息区
        info_widget = QWidget()
        info_widget.setStyleSheet("background-color: transparent;")
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(6)
        
        # 名称和属性
        name_row = QWidget()
        name_row.setStyleSheet("background-color: transparent;")
        name_layout = QHBoxLayout(name_row)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(10)
        
        name_label = QLabel(result['name'])
        name_label.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 600;")
        name_layout.addWidget(name_label)
        
        if result['attribute']:
            attr_label = QLabel(result['attribute'])
            attr_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(139, 92, 246, 0.15);
                    color: #c4b5fd;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 11px;
                }
            """)
            name_layout.addWidget(attr_label)
        
        name_layout.addStretch()
        info_layout.addWidget(name_row)
        
        # 身高体重范围
        stats_label = QLabel(f"蛋身高: {result['height_range']}m  |  蛋体重: {result['weight_range']}kg")
        stats_label.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        info_layout.addWidget(stats_label)
        
        card_layout.addWidget(info_widget, stretch=1)
        
        # 符合度
        score_widget = QWidget()
        score_widget.setStyleSheet("background-color: transparent;")
        score_layout = QVBoxLayout(score_widget)
        score_layout.setContentsMargins(0, 0, 0, 0)
        score_layout.setSpacing(4)
        score_layout.setAlignment(Qt.AlignCenter)  # 居中对齐
        
        score_label = QLabel(f"{result['score']:.1f}%")
        score_label.setStyleSheet("color: #a78bfa; font-size: 16px; font-weight: bold;")
        score_label.setAlignment(Qt.AlignCenter)  # 文字居中
        score_layout.addWidget(score_label)
        
        score_text = QLabel("符合度")
        score_text.setStyleSheet("color: #71717a; font-size: 11px;")
        score_text.setAlignment(Qt.AlignCenter)  # 文字居中
        score_layout.addWidget(score_text)
        
        score_widget.setFixedWidth(90)  # 固定宽度
        card_layout.addWidget(score_widget)
        
        return card
    
    def _create_rounded_pixmap(self, pixmap, size):
        """创建圆形头像图片"""
        from PySide6.QtGui import QPixmap, QPainter, QPainterPath
        
        target_pixmap = QPixmap(size, size)
        target_pixmap.fill(Qt.transparent)
        
        painter = QPainter(target_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # 创建圆形裁剪路径
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        
        # 直接缩放到填满
        scaled = pixmap.scaled(size, size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(0, 0, scaled)
        painter.end()
        
        return target_pixmap
    
    def _create_clean_section(self, title, items):
        """创建简洁的设置区块"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 600;")
        layout.addWidget(title_label)
        
        # 项目列表
        for item_title, item_desc, control in items:
            card = self._create_setting_item(item_title, item_desc, control)
            layout.addWidget(card)
        
        return section
    
    def _create_setting_item(self, title, description, control):
        """创建设置项卡片"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e1e26;
                border: none;
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #252530;
            }
        """)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(24, 18, 24, 18)
        card_layout.setSpacing(20)
        
        # 左侧信息
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #e4e4e7; font-size: 14px; font-weight: 500; background: transparent;")
        info_layout.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #71717a; font-size: 12px; background: transparent;")
        info_layout.addWidget(desc_label)
        
        card_layout.addWidget(info_widget, stretch=1)
        
        # 右侧控件
        if isinstance(control, QCheckBox):
            # 替换为ToggleSwitch
            toggle = ToggleSwitch()
            toggle.setChecked(control.isChecked())
            control = toggle
        
        card_layout.addWidget(control)
        
        return card
    
    def _create_spin_input(self, min_val, max_val, value, suffix="", step=1, is_double=False):
        """创建数字输入框"""
        if is_double:
            spin = QDoubleSpinBox()
            spin.setSingleStep(step)
        else:
            spin = QSpinBox()
        
        spin.setRange(min_val, max_val)
        spin.setValue(value)
        if suffix:
            spin.setSuffix(suffix)
        spin.setFixedWidth(140)
        spin.setStyleSheet("""
            QSpinBox, QDoubleSpinBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 6px;
                padding: 8px 12px;
                color: #e4e4e7;
                font-size: 14px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #7c3aed;
                background-color: #2a2a35;
            }
        """)
        return spin
    
    def _create_combo_box(self, items, current_value):
        """创建下拉选择框（使用TriangleComboBox）"""
        combo = TriangleComboBox()
        combo.addItems(items)
        combo.setCurrentText(current_value)
        combo.setFixedWidth(140)
        combo.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 15px;
            }
            QComboBox:focus {
                border-color: #7c3aed;
                background-color: #2a2a35;
            }
            QComboBox:disabled {
                background-color: #1a1a1a;
                border: 1px solid rgba(124, 58, 237, 0.1);
                color: #6b6b6b;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow:disabled {
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #6b6b6b;
                margin-right: 10px;
            }
        """)
        return combo
        
        # 计数器设置
        counter_group = self._create_modern_settings_group("📊 计数器默认设置", "新建计数器的初始参数")
        counter_content = QWidget()
        counter_main_layout = QVBoxLayout(counter_content)
        counter_main_layout.setContentsMargins(0, 0, 0, 0)
        counter_main_layout.setSpacing(24)
        
        # 保底次数卡片
        target_card = QWidget()
        target_card_layout = QHBoxLayout(target_card)
        target_card_layout.setContentsMargins(24, 20, 24, 20)
        target_card_layout.setSpacing(20)
        
        target_icon = QLabel("🎲")
        target_icon.setStyleSheet("font-size: 28px;")
        target_card_layout.addWidget(target_icon)
        
        target_info = QWidget()
        target_info_layout = QVBoxLayout(target_info)
        target_info_layout.setContentsMargins(0, 0, 0, 0)
        target_info_layout.setSpacing(4)
        
        target_title = QLabel("默认保底次数")
        target_title.setStyleSheet("color: #e4e4e7; font-size: 16px; font-weight: 600;")
        target_info_layout.addWidget(target_title)
        
        target_desc = QLabel("新建计数器时的默认保底目标次数")
        target_desc.setStyleSheet("color: #71717a; font-size: 13px;")
        target_info_layout.addWidget(target_desc)
        
        target_card_layout.addWidget(target_info, stretch=1)
        
        default_target = QSpinBox()
        default_target.setRange(10, 999)
        default_target.setValue(80)
        default_target.setFixedWidth(160)
        default_target.setStyleSheet("""
            QSpinBox {
                background-color: #252530;
                border: 2px solid rgba(124, 58, 237, 0.3);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 15px;
                font-weight: 500;
            }
            QSpinBox:focus {
                border: 2px solid #7c3aed;
                background-color: #2a2a35;
            }
        """)
        target_card_layout.addWidget(default_target)
        
        counter_main_layout.addWidget(target_card)
        
        # 基础概率卡片
        prob_card = QWidget()
        prob_card_layout = QHBoxLayout(prob_card)
        prob_card_layout.setContentsMargins(24, 20, 24, 20)
        prob_card_layout.setSpacing(20)
        
        prob_icon = QLabel("✨")
        prob_icon.setStyleSheet("font-size: 28px;")
        prob_card_layout.addWidget(prob_icon)
        
        prob_info = QWidget()
        prob_info_layout = QVBoxLayout(prob_info)
        prob_info_layout.setContentsMargins(0, 0, 0, 0)
        prob_info_layout.setSpacing(4)
        
        prob_title = QLabel("基础异色概率")
        prob_title.setStyleSheet("color: #e4e4e7; font-size: 16px; font-weight: 600;")
        prob_info_layout.addWidget(prob_title)
        
        prob_desc = QLabel("用于计算童话事件概率的基础值（百分比）")
        prob_desc.setStyleSheet("color: #71717a; font-size: 13px;")
        prob_info_layout.addWidget(prob_desc)
        
        prob_card_layout.addWidget(prob_info, stretch=1)
        
        base_prob = QDoubleSpinBox()
        base_prob.setRange(0.1, 10.0)
        base_prob.setValue(1.8)
        base_prob.setSingleStep(0.1)
        base_prob.setSuffix(" %")
        base_prob.setFixedWidth(160)
        base_prob.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #252530;
                border: 2px solid rgba(124, 58, 237, 0.3);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 15px;
                font-weight: 500;
            }
            QDoubleSpinBox:focus {
                border: 2px solid #7c3aed;
                background-color: #2a2a35;
            }
        """)
        prob_card_layout.addWidget(base_prob)
        
        counter_main_layout.addWidget(prob_card)
        
        # 自动保存进度
        autosave_card = self._create_setting_card(
            "自动保存进度",
            "计数变化时自动保存到本地文件",
            QCheckBox(),
            True
        )
        counter_main_layout.addWidget(autosave_card)
        
        counter_group.layout().addWidget(counter_content)
        layout.addWidget(counter_group)
        
        # 高级设置
        advanced_group = self._create_modern_settings_group("⚡ 高级设置", "性能和调试选项")
        advanced_content = QWidget()
        advanced_main_layout = QVBoxLayout(advanced_content)
        advanced_main_layout.setContentsMargins(0, 0, 0, 0)
        advanced_main_layout.setSpacing(24)
        
        # 启用日志
        log_card = self._create_setting_card(
            "启用详细日志",
            "记录详细的运行日志用于问题排查",
            QCheckBox(),
            False
        )
        advanced_main_layout.addWidget(log_card)
        
        # 显示FPS
        fps_card = self._create_setting_card(
            "显示性能监控",
            "在悬浮窗显示当前帧率和内存占用",
            QCheckBox(),
            False
        )
        advanced_main_layout.addWidget(fps_card)
        
        advanced_group.layout().addWidget(advanced_content)
        layout.addWidget(advanced_group)
        
        # 底部操作区
        footer_widget = QWidget()
        footer_layout = QVBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 32, 0, 0)
        footer_layout.setSpacing(16)
        
        # 提示文字
        tip_label = QLabel("💡 修改设置后需要重启助手才能完全生效")
        tip_label.setStyleSheet("color: #a78bfa; font-size: 13px;")
        footer_layout.addWidget(tip_label)
        
        # 按钮行
        btn_row = QWidget()
        btn_row_layout = QHBoxLayout(btn_row)
        btn_row_layout.setContentsMargins(0, 0, 0, 0)
        btn_row_layout.setSpacing(16)
        btn_row_layout.addStretch()
        
        reset_btn = QPushButton("↺ 恢复默认")
        reset_btn.setFixedHeight(48)
        reset_btn.setMinimumWidth(140)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #a1a1aa;
                border: 2px solid rgba(124, 58, 237, 0.3);
                border-radius: 10px;
                font-size: 15px;
                font-weight: 500;
                padding: 0 28px;
            }
            QPushButton:hover {
                background-color: rgba(124, 58, 237, 0.1);
                border: 2px solid rgba(124, 58, 237, 0.6);
                color: #e4e4e7;
            }
            QPushButton:pressed {
                background-color: rgba(124, 58, 237, 0.15);
            }
        """)
        reset_btn.clicked.connect(self.on_reset_settings)
        btn_row_layout.addWidget(reset_btn)
        
        save_btn = QPushButton("✓ 保存设置")
        save_btn.setFixedHeight(48)
        save_btn.setMinimumWidth(140)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c3aed, stop:1 #8b5cf6);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 600;
                padding: 0 28px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8b5cf6, stop:1 #a78bfa);
            }
            QPushButton:pressed {
                background-color: #6d28d9;
            }
        """)
        save_btn.clicked.connect(lambda: QMessageBox.information(self, "成功", "✅ 设置已保存！\n\n部分设置需要重启后生效。"))
        btn_row_layout.addWidget(save_btn)
        
        footer_layout.addWidget(btn_row)
        layout.addWidget(footer_widget)
        
        layout.addStretch()
        
        scroll.setWidget(container)
        return scroll
    
    def _create_modern_settings_group(self, title, description):
        """创建现代化设置分组"""
        group = QGroupBox()
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(16)
        
        # 标题区域
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 12)
        header_layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #71717a; font-size: 13px;")
        header_layout.addWidget(desc_label)
        
        group_layout.addWidget(header)
        
        return group
    
    def _create_setting_card(self, title, description, control, checked=False):
        """创建设置卡片"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #1e1e26;
                border: 1px solid rgba(124, 58, 237, 0.1);
                border-radius: 12px;
            }
            QFrame:hover {
                border: 1px solid rgba(124, 58, 237, 0.25);
                background-color: #222229;
            }
        """)
        
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(24, 18, 24, 18)
        card_layout.setSpacing(20)
        
        # 信息区域
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #e4e4e7; font-size: 15px; font-weight: 600;")
        info_layout.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet("color: #71717a; font-size: 13px;")
        info_layout.addWidget(desc_label)
        
        card_layout.addWidget(info_widget, stretch=1)
        
        # 控制控件
        if isinstance(control, QCheckBox):
            control.setChecked(checked)
            control.setStyleSheet("""
                QCheckBox {
                    spacing: 0;
                }
                QCheckBox::indicator {
                    width: 22px;
                    height: 22px;
                    border: 2px solid rgba(124, 58, 237, 0.4);
                    border-radius: 6px;
                    background-color: #252530;
                }
                QCheckBox::indicator:checked {
                    background-color: #7c3aed;
                    border: 2px solid #7c3aed;
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgNEw0LjUgNy41TDExIDEiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+PC9zdmc+);
                }
                QCheckBox::indicator:hover {
                    border: 2px solid rgba(124, 58, 237, 0.7);
                }
            """)
        
        card_layout.addWidget(control)
        
        return card
    
    def _create_settings_group(self, title):
        """创建设置分组"""
        group = QGroupBox()
        group.setStyleSheet("""
            QGroupBox {
                background-color: #1e1e26;
                border: 1px solid rgba(124, 58, 237, 0.15);
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #a78bfa;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        return group

    def on_toggle_lock(self):
        """切换锁定状态"""
        is_locked = self.manager.toggle_lock()
        self.manager.save_counters()  # 切换锁定后保存
        # 更新复选框状态
        if hasattr(self, 'lock_checkbox'):
            self.lock_checkbox.setChecked(is_locked)
        # 更新锁定状态提示文字
        if hasattr(self, 'lock_status_label'):
            self.lock_status_label.setText("已锁定" if is_locked else "未锁定")
            # 更新文字颜色
            if is_locked:
                self.lock_status_label.setStyleSheet("color: #22c55e; font-size: 11px; font-weight: 500;")
            else:
                self.lock_status_label.setStyleSheet("color: #71717a; font-size: 11px;")
        self._refresh_all()

    # ================= 悬浮窗切换 =================
    def enter_floating_mode(self):
        """进入悬浮窗模式，隐藏主窗口"""
        active = self.manager.get_active()
        if active:
            # 优先使用计数器自带的icon_id
            icon_id = active.icon_id if hasattr(active, 'icon_id') else 0
            
            # 如果icon_id为0，尝试从custom_pokemons中查找
            if icon_id == 0:
                custom_pokemons = self.manager.get_custom_pokemons()
                for cp in custom_pokemons:
                    if cp['name'] == active.pokemon_name:
                        icon_id = cp.get('icon_id', 0)
                        break
            
            self.floating_window.update_data(
                active.pokemon_name,
                active.type,
                active.count,
                active.target,
                active.is_locked,
                active.nightmare_count,
                icon_id
            )
        self.floating_window.show()
        self.hide()
    
    # ================= 异色图鉴视图 =================
    def _create_pokedex_view(self):
        """创建异色图鉴选择界面"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 禁用水平滚动条
        scroll.setStyleSheet(SCROLL_BAR_STYLE)
        container = QWidget()
        container.setObjectName("mainContent")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 40, 20)  # 右边距40px补偿滚动条宽度
        layout.setSpacing(16)
        
        # 标题
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)
        
        title = QLabel("异色图鉴")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        title_layout.addWidget(title)
        
        desc = QLabel("查看所有可捕捉异色精灵，点击创建对应计数器")
        desc.setStyleSheet("color: #71717a; font-size: 14px; margin-left: 8px;")
        title_layout.addWidget(desc)
        title_layout.addStretch()
        
        layout.addWidget(title_bar)
        
        # 筛选器
        filter_bar = QWidget()
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setContentsMargins(0, 8, 0, 8)
        filter_layout.setSpacing(16)
        
        # 赛季选择
        season_label = QLabel("赛季：")
        season_label.setStyleSheet("color: #71717a; font-size: 14px;")
        filter_layout.addWidget(season_label)
        
        self.season_combo = TriangleComboBox()
        self.season_combo.addItems(["第一赛季", "第二赛季", "第三赛季"])
        self.season_combo.setCurrentText("第三赛季")
        self.season_combo.setFixedWidth(120)
        self.season_combo.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 6px 10px;
                color: #e4e4e7;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)
        self.season_combo.currentTextChanged.connect(self._refresh_pokedex)
        filter_layout.addWidget(self.season_combo)
        
        # 属性筛选
        filter_type_label = QLabel("属性筛选：")
        filter_type_label.setStyleSheet("color: #71717a; font-size: 14px;")
        filter_layout.addWidget(filter_type_label)
        
        self.filter_type_combo = TriangleComboBox()
        self.filter_type_combo.addItems(["全部属性"] + get_all_types())
        self.filter_type_combo.setFixedWidth(120)
        self.filter_type_combo.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 6px 10px;
                color: #e4e4e7;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)
        self.filter_type_combo.currentTextChanged.connect(self._refresh_pokedex)
        filter_layout.addWidget(self.filter_type_combo)
        
        # 显示筛选
        filter_display_label = QLabel("显示：")
        filter_display_label.setStyleSheet("color: #71717a; font-size: 14px;")
        filter_layout.addWidget(filter_display_label)
        
        self.filter_display_combo = TriangleComboBox()
        self.filter_display_combo.addItems(["全部精灵", "仅自定义"])
        self.filter_display_combo.setFixedWidth(120)
        self.filter_display_combo.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 6px 10px;
                color: #e4e4e7;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
        """)
        self.filter_display_combo.currentTextChanged.connect(self._refresh_pokedex)
        filter_layout.addWidget(self.filter_display_combo)
        
        filter_layout.addStretch()
        
        # 视图切换按钮
        self.view_toggle_btn = QPushButton("☷ 列表")
        self.view_toggle_btn.setFixedWidth(80)
        self.view_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 6px 10px;
                color: #e4e4e7;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(124, 58, 237, 0.2);
            }
        """)
        self.pokedex_view_mode = "grid"  # grid或list
        self.view_toggle_btn.clicked.connect(self._toggle_pokedex_view)
        filter_layout.addWidget(self.view_toggle_btn)
        
        layout.addWidget(filter_bar)
        
        # 精灵网格容器（3列布局，从左到右）
        self.pokemon_grid_container = QWidget()
        self.pokemon_grid_container.setFixedWidth(600)  # 3列*180px + 2*16px间距
        self.pokemon_grid_layout = QGridLayout(self.pokemon_grid_container)
        self.pokemon_grid_layout.setSpacing(16)
        self.pokemon_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.pokemon_grid_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)
        scroll_layout.addWidget(self.pokemon_grid_container, alignment=Qt.AlignHCenter)
        scroll_layout.addStretch()
        
        layout.addWidget(scroll_content, stretch=1)
        
        # 底部按钮区域 - 固定在底部
        btn_custom_container = QWidget()
        btn_custom_layout = QHBoxLayout(btn_custom_container)
        btn_custom_layout.setContentsMargins(0, 16, 0, 0)  # 顶部留白
        btn_custom_layout.setSpacing(12)
        
        # 手动新建按钮
        btn_manual = QPushButton("✏️ 手动新建")
        btn_manual.setObjectName("customPokemonBtn")
        btn_manual.clicked.connect(self.on_custom_pokemon_from_pokedex)
        btn_custom_layout.addWidget(btn_manual)
        
        # 从图鉴选取按钮
        btn_select = QPushButton("从图鉴选取")
        btn_select.setObjectName("customPokemonBtn")
        btn_select.setStyleSheet("""
            QPushButton#customPokemonBtn {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.3);
                color: #a78bfa;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton#customPokemonBtn:hover {
                background-color: rgba(124, 58, 237, 0.1);
                border: 1px solid #7c3aed;
            }
        """)
        btn_select.clicked.connect(self.on_select_from_pokedex)
        btn_custom_layout.addWidget(btn_select)
        
        btn_custom_layout.addStretch()
        
        layout.addWidget(btn_custom_container)
        
        scroll.setWidget(container)
        return scroll
    
    def _refresh_pokedex(self):
        """刷新异色图鉴列表（3列网格+筛选）"""
        # 更新全局赛季设置
        from core.pokemon_data import set_current_season
        season = self.season_combo.currentText()
        set_current_season(season)
        
        # 清空现有网格
        for i in reversed(range(self.pokemon_grid_layout.count())):
            widget = self.pokemon_grid_layout.takeAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 获取筛选条件
        type_filter = self.filter_type_combo.currentText()
        display_filter = self.filter_display_combo.currentText()
        
        # 从数据库加载所有精灵（按赛季筛选）
        from core.pokemon_data import load_pokemon_database
        database_pokemons = load_pokemon_database(season)
        
        # 获取自定义精灵
        custom_pokemons = self.manager.get_custom_pokemons()
        
        # 合并数据库和自定义精灵
        all_pokemons = database_pokemons + custom_pokemons
        
        # 应用筛选
        filtered = []
        for pokemon in all_pokemons:
            # 属性筛选
            if type_filter != "全部属性":
                types = pokemon.get("types", [])
                if isinstance(types, list):
                    type_str = "、".join(types)
                else:
                    type_str = str(types)
                
                # 直接使用完整属性名匹配
                if type_filter not in type_str:
                    continue
            
            # 显示筛选
            if display_filter == "仅自定义":
                if not pokemon.get("is_custom", False):
                    continue
            filtered.append(pokemon)
        
        if not filtered:
            # 如果没有精灵，显示提示
            empty_label = QLabel("暂无精灵，请点击底部“自己新建”添加")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setStyleSheet("color: #6b6f82; font-size: 14px; padding: 40px;")
            self.pokemon_grid_layout.addWidget(empty_label, 0, 0, 1, 3)
            return
        
        # 3列布局
        columns = 3
        for idx, pokemon in enumerate(filtered):
            if self.pokedex_view_mode == "grid":
                row = idx // columns
                col = idx % columns
                item = self._create_pokedex_item(pokemon)
                self.pokemon_grid_layout.addWidget(item, row, col)
            else:
                # 列表模式，单列
                item = self._create_pokedex_list_item(pokemon)
                self.pokemon_grid_layout.addWidget(item, idx, 0, 1, 3)
        
        # 添加"新增自定义精灵"卡片
        total_items = len(filtered)
        if self.pokedex_view_mode == "grid":
            last_row = (total_items + 2) // columns  # 计算最后一行
            add_card = self._create_add_custom_card()
            self.pokemon_grid_layout.addWidget(add_card, last_row, 0, 1, columns)
        else:
            add_card = self._create_add_custom_card()
            add_card.setFixedWidth(660)
            self.pokemon_grid_layout.addWidget(add_card, total_items, 0, 1, 3)
    
    def _create_pokedex_item(self, pokemon):
        """创建图鉴中的单个精灵项（180px卡片）"""
        item = QFrame()
        item.setObjectName("pokedexItem")
        item.setCursor(Qt.PointingHandCursor)
        item.setFixedWidth(180)
        
        layout = QVBoxLayout(item)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)
        
        # 圆形头像（从ys文件夹加载图片或自定义icon）
        avatar = QLabel()
        avatar.setFixedSize(60, 60)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("background: transparent;")  # 设置透明背景
        
        pokemon_name = pokemon["name"]
        image_loaded = False
        
        # 优先尝试使用icon_id从tj/images加载
        icon_id = pokemon.get('icon_id', 0)
        if icon_id > 0:
            image_dir = os.path.join(self._base_dir, "image", "tj", "images")
            image_path = os.path.join(image_dir, f"{icon_id:03d}.png")
            
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    rounded_pixmap = QPixmap(60, 60)
                    rounded_pixmap.fill(Qt.transparent)
                    painter = QPainter(rounded_pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform)
                    path = QPainterPath()
                    path.addEllipse(0, 0, 60, 60)
                    painter.setClipPath(path)
                    painter.drawPixmap(0, 0, scaled_pixmap)
                    painter.end()
                    avatar.setPixmap(rounded_pixmap)
                    image_loaded = True
        
        # 如果icon_id未加载，尝试使用自定义icon（如果是图片路径）
        if not image_loaded:
            custom_icon = pokemon.get("icon", "")
            if custom_icon and os.path.exists(custom_icon):
                pixmap = QPixmap(custom_icon)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    rounded_pixmap = QPixmap(60, 60)
                    rounded_pixmap.fill(Qt.transparent)
                    painter = QPainter(rounded_pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform)
                    path = QPainterPath()
                    path.addEllipse(0, 0, 60, 60)
                    painter.setClipPath(path)
                    painter.drawPixmap(0, 0, scaled_pixmap)
                    painter.end()
                    avatar.setPixmap(rounded_pixmap)
                    image_loaded = True
        
        # 如果都未加载，尝试从ys文件夹加载（按赛季）
        if not image_loaded:
            # 获取当前赛季
            if hasattr(self, 'season_combo'):
                season = self.season_combo.currentText()
                image_dir = os.path.join(self._base_dir, "image", "ys", season)
                image_path = os.path.join(image_dir, f"{pokemon_name}.png")
            else:
                # 计数器界面可能没有season_combo，直接从第三赛季加载
                image_dir = os.path.join(self._base_dir, "image", "ys", "第三赛季")
                image_path = os.path.join(image_dir, f"{pokemon_name}.png")
            
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    rounded_pixmap = QPixmap(60, 60)
                    rounded_pixmap.fill(Qt.transparent)
                    painter = QPainter(rounded_pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform)
                    path = QPainterPath()
                    path.addEllipse(0, 0, 60, 60)
                    painter.setClipPath(path)
                    painter.drawPixmap(0, 0, scaled_pixmap)
                    painter.end()
                    avatar.setPixmap(rounded_pixmap)
                    image_loaded = True
        
        # 如果都未加载，使用默认样式
        if not image_loaded:
            self._set_pokedex_default_avatar(avatar, pokemon_name)
        
        layout.addWidget(avatar, 0, Qt.AlignHCenter)
        
        # 名称
        name_label = QLabel(pokemon["name"])
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 600;")
        layout.addWidget(name_label)
        
        # 属性标签
        types = pokemon.get("types", [])
        if not types:
            # 兼容旧版type字段
            type_str_old = pokemon.get("type", "")
            if type_str_old:
                types = [t.strip() for t in type_str_old.split("、") if t.strip()]
        
        if isinstance(types, list):
            type_str = "、".join(types)
        else:
            type_str = str(types)
        
        type_label = QLabel(type_str)
        type_label.setAlignment(Qt.AlignCenter)
        type_label.setStyleSheet("""
            QLabel {
                background-color: rgba(124, 58, 237, 0.2);
                color: #a78bfa;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        layout.addWidget(type_label, 0, Qt.AlignHCenter)
        
        # 描述
        desc_label = QLabel("自定义精灵" if pokemon.get("is_custom", False) else "图鉴精灵")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #71717a; font-size: 12px;")
        layout.addWidget(desc_label)
        
        # 点击选中（仅左键）
        def on_item_click(event, p=pokemon):
            if event.button() == Qt.LeftButton:
                self.select_pokemon_from_pokedex(p)
            else:
                QFrame.mousePressEvent(item, event)  # 传递其他事件给父类
        
        item.mousePressEvent = on_item_click
        
        # 自定义精灵添加右键菜单
        if pokemon.get("is_custom", False):
            item.setContextMenuPolicy(Qt.CustomContextMenu)
            item.customContextMenuRequested.connect(lambda pos, p=pokemon: self.show_pokemon_context_menu(pos, p, item))
        
        return item
    
    def _set_pokedex_default_avatar(self, avatar, pokemon_name):
        """设置图鉴网格模式默认头像"""
        avatar.setText(pokemon_name[0] if pokemon_name else "?")
        avatar.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7c3aed, stop:1 #a78bfa);
                border-radius: 30px;
                color: white;
                font-size: 24px;
            }
        """)
    
    def show_pokemon_context_menu(self, pos, pokemon, widget):
        """显示自定义精灵的右键菜单"""
        menu = QMenu(self)
        
        edit_action = menu.addAction("✏️ 修改")
        delete_action = menu.addAction("🗑️ 删除")
        
        action = menu.exec_(widget.mapToGlobal(pos))
        
        if action == edit_action:
            self.edit_custom_pokemon(pokemon)
        elif action == delete_action:
            self.delete_custom_pokemon(pokemon)
    
    def edit_custom_pokemon(self, pokemon):
        """编辑自定义精灵"""
        dialog = EditPokemonDialog(pokemon, self)
        result = dialog.exec()
        
        if result == 2:
            # 用户点击了删除按钮
            self.delete_custom_pokemon(pokemon)
            return
        
        if result == QDialog.Accepted:
            new_name, new_type, new_icon = dialog.get_data()
            if not new_name:
                QMessageBox.warning(self, "警告", "请输入精灵名称！")
                return
            
            # 更新图鉴数据
            self.manager.update_custom_pokemon(pokemon["name"], new_name, new_type, new_icon)
            
            # 如果有使用该精灵的计数器，也更新计数器中的名称
            for counter in self.manager.counters:
                if counter.pokemon_name == pokemon["name"] and counter.is_custom:
                    counter.pokemon_name = new_name
                    counter.counter_name = f"{new_name}计数器"
            
            self.manager.save_counters()
            self._refresh_pokedex()
            QMessageBox.information(self, "成功", f"已更新精灵【{new_name}】")
    
    def _set_pokedex_list_default_icon(self, icon_label, pokemon_name):
        """设置图鉴列表模式默认图标"""
        icon_label.setText(pokemon_name[0] if pokemon_name else "?")
        icon_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6c5ce7, stop:1 #a855f7);
                border-radius: 16px;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        icon_label.setAlignment(Qt.AlignCenter)
    
    def _create_pokedex_list_item(self, pokemon):
        """创建图鉴中的列表项（180x80px，计数器样式）"""
        item = QFrame()
        item.setObjectName("pokedexListItem")
        item.setCursor(Qt.PointingHandCursor)
        item.setFixedWidth(600)
        item.setFixedHeight(80)
        item.setStyleSheet("""
            QFrame#pokedexListItem {
                background-color: #121212;
                border: 1px solid rgba(139, 92, 246, 0.2);
                border-radius: 8px;
            }
            QFrame#pokedexListItem:hover {
                background-color: #1a1a1a;
                border: 1px solid rgba(139, 92, 246, 0.4);
            }
        """)
        
        layout = QHBoxLayout(item)
        layout.setContentsMargins(12, 10, 10, 10)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignVCenter)
        
        # 左侧：图标 + 信息
        left_section = QWidget()
        left_layout = QVBoxLayout(left_section)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        
        # 第一行：图标、名字、属性横向排列
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)
        top_layout.setAlignment(Qt.AlignVCenter)
        
        # 圆形图标（从ys文件夹加载图片或自定义icon）
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        icon_label.setStyleSheet("background: transparent;")
        
        pokemon_name = pokemon["name"]
        image_loaded = False
        
        # 优先尝试使用自定义icon（如果是图片路径）
        custom_icon = pokemon.get("icon", "")
        if custom_icon and os.path.exists(custom_icon):
            pixmap = QPixmap(custom_icon)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                rounded_pixmap = QPixmap(32, 32)
                rounded_pixmap.fill(Qt.transparent)
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setRenderHint(QPainter.SmoothPixmapTransform)
                path = QPainterPath()
                path.addEllipse(0, 0, 32, 32)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.end()
                icon_label.setPixmap(rounded_pixmap)
                image_loaded = True
        
        # 如果自定义icon未加载，尝试从ys文件夹加载
        if not image_loaded:
            image_dir = os.path.join(self._base_dir, "image", "ys")
            image_path = os.path.join(image_dir, f"{pokemon_name}.png")
            
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    rounded_pixmap = QPixmap(32, 32)
                    rounded_pixmap.fill(Qt.transparent)
                    painter = QPainter(rounded_pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform)
                    path = QPainterPath()
                    path.addEllipse(0, 0, 32, 32)
                    painter.setClipPath(path)
                    painter.drawPixmap(0, 0, scaled_pixmap)
                    painter.end()
                    icon_label.setPixmap(rounded_pixmap)
                    image_loaded = True
        
        # 如果都未加载，使用默认样式
        if not image_loaded:
            self._set_pokedex_list_default_icon(icon_label, pokemon_name)
        
        top_layout.addWidget(icon_label)
        
        # 名称
        name_label = QLabel(pokemon["name"])
        name_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 600;")
        top_layout.addWidget(name_label)
        
        # 属性
        types = pokemon.get("types", [])
        if not types:
            # 兼容旧版type字段
            type_str_old = pokemon.get("type", "")
            if type_str_old:
                types = [t.strip() for t in type_str_old.split("、") if t.strip()]
        
        if isinstance(types, list):
            type_str = "、".join(types)
        else:
            type_str = str(types)
        info_label = QLabel(type_str)
        info_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
        top_layout.addWidget(info_label)
        
        top_layout.addStretch()
        left_layout.addWidget(top_row)
        
        # 第二行：描述
        desc_row = QWidget()
        desc_layout = QHBoxLayout(desc_row)
        desc_layout.setContentsMargins(0, 0, 0, 0)
        desc_layout.addStretch()
        
        desc_label = QLabel("自定义精灵" if pokemon.get("is_custom", False) else "图鉴精灵")
        desc_label.setStyleSheet("color: #71717a; font-size: 11px;")
        desc_layout.addWidget(desc_label)
        left_layout.addWidget(desc_row)
        
        layout.addWidget(left_section, stretch=1)
        
        # 点击选中（仅左键）
        def on_list_item_click(event, p=pokemon):
            if event.button() == Qt.LeftButton:
                self.select_pokemon_from_pokedex(p)
            else:
                QFrame.mousePressEvent(item, event)  # 传递其他事件给父类
        
        item.mousePressEvent = on_list_item_click
        
        # 自定义精灵添加右键菜单
        if pokemon.get("is_custom", False):
            item.setContextMenuPolicy(Qt.CustomContextMenu)
            item.customContextMenuRequested.connect(lambda pos, p=pokemon: self.show_pokemon_context_menu(pos, p, item))
        
        return item
    
    def _toggle_pokedex_view(self):
        """切换图鉴视图模式"""
        if self.pokedex_view_mode == "grid":
            self.pokedex_view_mode = "list"
            self.view_toggle_btn.setText("☰ 网格")
            self.pokemon_grid_container.setFixedWidth(600)
        else:
            self.pokedex_view_mode = "grid"
            self.view_toggle_btn.setText("☷ 列表")
            self.pokemon_grid_container.setFixedWidth(600)
        self._refresh_pokedex()
    
    def _create_add_custom_card(self):
        """创建新增自定义精灵卡片"""
        card = QFrame()
        card.setObjectName("addCustomCard")
        card.setCursor(Qt.PointingHandCursor)
        if self.pokedex_view_mode == "grid":
            card.setFixedWidth(180)
        else:
            card.setFixedWidth(600)
        card.setStyleSheet("""
            QFrame#addCustomCard {
                border: 2px dashed rgba(124, 58, 237, 0.3);
                border-radius: 12px;
                background-color: transparent;
            }
            QFrame#addCustomCard:hover {
                border-color: #7c3aed;
                background-color: rgba(124, 58, 237, 0.1);
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)
        
        # +号图标
        plus_icon = QLabel("+")
        plus_icon.setFixedSize(48, 48)
        plus_icon.setAlignment(Qt.AlignCenter)
        plus_icon.setStyleSheet("""
            QLabel {
                background-color: rgba(124, 58, 237, 0.1);
                border-radius: 24px;
                color: #a78bfa;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        layout.addWidget(plus_icon, 0, Qt.AlignHCenter)
        
        # 文字
        text_label = QLabel("新增自定义精灵")
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setStyleSheet("color: #71717a; font-size: 14px;")
        layout.addWidget(text_label)
        
        # 点击事件
        card.mousePressEvent = lambda event: self.on_custom_pokemon_from_pokedex()
        
        return card
    
    def select_pokemon_from_pokedex(self, pokemon):
        """从图鉴中选择精灵创建计数器(带确认对话框)"""
        name = pokemon["name"]
        # 处理types字段(可能是列表或字符串)
        types = pokemon.get("types", [])
        if isinstance(types, list):
            type_ = "、".join(types)
        else:
            type_ = str(types)
        
        # 二次确认
        reply = QMessageBox.question(
            self,
            "确认添加",
            f"确定为【{name}】创建计数器吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply != QMessageBox.Yes:
            return
        
        counter_name = f"{name}计数器"
        counter = self.manager.add_counter(name, counter_name, type_)
        # 重置童话事件提示计数
        if hasattr(self, 'game_capture') and self.game_capture:
            self.game_capture.set_nightmare_count(0)
        if counter:
            counter.nightmare_count = 0
        self.content_stack.setCurrentIndex(1)  # 切换到详情
        self._refresh_all()
    
    def delete_custom_pokemon(self, pokemon):
        """删除自定义精灵"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除自定义精灵【{pokemon['name']}】吗？\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.manager.delete_custom_pokemon(pokemon["name"])
            self._refresh_pokedex()
            # 如果有使用该精灵的计数器，也需要保存
            self.manager.save_counters()
    
    def on_custom_pokemon_from_pokedex(self):
        """手动新建自定义精灵"""
        from ui.lkwg_manual_dialog import LkwgManualDialog
        
        dialog = LkwgManualDialog(self)
        if dialog.exec():
            name, type_, target, icon, evolution_chain = dialog.get_data()
            if not name:
                QMessageBox.warning(self, "警告", "请输入精灵名称！")
                return
            
            # 询问是否保存到图鉴
            reply = QMessageBox.question(
                self,
                "保存至图鉴",
                f"是否将【{name}】保存至异色图鉴？\n保存后下次可直接在图鉴中选择。",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Cancel:
                return
            
            if reply == QMessageBox.Yes:
                # 保存到图鉴（使用 manager，包含进化链）
                self.manager.save_custom_pokemon(name, type_, evolution_chain)
                # 刷新图鉴
                self._refresh_pokedex()
            
            # 创建计数器
            try:
                target_val = int(target)
            except:
                target_val = 80
            
            self.manager.add_counter(name, f"{name}计数器", type_, is_custom=True)
            self.manager.save_counters()  # 添加后立即保存
            # 重置童话事件提示计数
            if hasattr(self, 'game_capture') and self.game_capture:
                self.game_capture.set_nightmare_count(0)
            self.content_stack.setCurrentIndex(1)
            self._refresh_all()
    
    def _load_evolution_chain(self, pokemon_name):
        """从 lkwg_names.txt 加载精灵的进化链"""
        import os
        
        names_file = os.path.join(self._base_dir, "core", "lkwg_names.txt")
        if not os.path.exists(names_file):
            return [pokemon_name]
        
        with open(names_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过注释和空行
                if not line or line.startswith('#'):
                    continue
                
                # 解析进化链
                chain = [name.strip() for name in line.split('→')]
                
                # 如果当前精灵在这个进化链中，返回整个链
                if pokemon_name in chain:
                    return chain
        
        # 没有找到进化链，返回单个精灵
        return [pokemon_name]
    
    def on_select_from_pokedex(self):
        """从图鉴选取精灵并配置进化链"""
        from ui.lkwg_pokedex_selector import LkwgPokedexSelector
        import json
        import os
        
        # 加载完整精灵图鉴数据库（352个）
        db_path = os.path.join(self._base_dir, "image", "tj", "pokemon_data.json")
        if os.path.exists(db_path):
            with open(db_path, 'r', encoding='utf-8') as f:
                database = json.load(f)
        else:
            database = []
        
        # 第一步：选择基础精灵
        selector = LkwgPokedexSelector(database, self)
        if not selector.exec():
            return
        
        selected_data = selector.get_selected()
        if not selected_data:
            return
        
        # 第二步：自动从 lkwg_names.txt 读取进化链
        evolution_chain = self._load_evolution_chain(selected_data['name'])
        
        # 第三步：创建自定义精灵并添加到异色图鉴
        name = selected_data.get('name', '')
        attribute = selected_data.get('attribute', '')
        icon_id = selected_data.get('id', 0)
        
        # 处理属性字段
        if attribute and not attribute.endswith("系"):
            type_str = attribute + "系"
        elif attribute:
            type_str = attribute
        else:
            type_str = "未知"
        
        # 保存到异色图鉴（作为自定义精灵）
        self.manager.save_custom_pokemon(name, type_str, evolution_chain, icon_id)
        self._refresh_pokedex()
        
        # 第四步：创建计数器
        self.manager.add_counter(name, f"{name}计数器", type_str, is_custom=True)
        self.manager.save_counters()
        # 重置童话事件提示计数
        if hasattr(self, 'game_capture') and self.game_capture:
            self.game_capture.set_nightmare_count(0)
        self.content_stack.setCurrentIndex(1)
        self._refresh_all()
    
    def _switch_nav_page(self, index, nav_btn=None, callback=None, hide_right_panel=False):
        """切换导航页面"""
        # 切换页面
        self.content_stack.setCurrentIndex(index)
        
        # 隐藏/显示右侧面板
        if hasattr(self, 'right_panel'):
            self.right_panel.setVisible(not hide_right_panel)
        
        # 更新导航按钮状态
        if nav_btn:
            # 查找所有导航按钮并重置
            for i in range(self.sidebar.layout().count()):
                item = self.sidebar.layout().itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    # 找到nav_container
                    if hasattr(widget, 'layout') and widget.layout():
                        for j in range(widget.layout().count()):
                            sub_item = widget.layout().itemAt(j)
                            if sub_item and sub_item.widget():
                                sub_widget = sub_item.widget()
                                if hasattr(sub_widget, 'objectName') and sub_widget.objectName() == "navItem":
                                    sub_widget.setProperty("active", False)
                                    sub_widget.style().unpolish(sub_widget)
                                    sub_widget.style().polish(sub_widget)
            
            # 激活当前按钮
            nav_btn.setProperty("active", True)
            nav_btn.style().unpolish(nav_btn)
            nav_btn.style().polish(nav_btn)
        
        # 执行回调
        if callback:
            callback()
    
    def _on_home_pokemon_clicked(self, pokemon):
        """家园系统点击精灵 → 跳转到精灵图鉴详情"""
        # 切换到精灵图鉴并显示详情
        self.content_stack.setCurrentIndex(3)
        enriched = self.pokemon_pokedex.get_enriched_data(pokemon)
        self.pokemon_pokedex.show_detail(enriched)
    
    def _create_map_view(self):
        """创建地图视图"""
        from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QLabel, QComboBox, QVBoxLayout, QHBoxLayout, QWidget, QScrollArea, QPushButton, QSizePolicy
        from PySide6.QtGui import QPixmap, QPainter, QFont, QColor, QPen, QBrush
        from PySide6.QtCore import Qt
        import json
        import os
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 标题栏
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("地图")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f8f0ff;")
        title_layout.addWidget(title)
        
        # 框选按钮
        self.toggle_select_btn = QPushButton("框选")
        self.toggle_select_btn.setCheckable(True)
        self.toggle_select_btn.setFixedWidth(60)
        self.toggle_select_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 197, 94, 0.6);
                color: white;
                border: 2px solid rgba(74, 222, 128, 0.8);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(34, 197, 94, 0.8);
            }
            QPushButton:pressed {
                background-color: rgba(34, 197, 94, 0.4);
            }
            QPushButton:checked {
                background-color: rgba(124, 58, 237, 0.8);
                border-color: rgba(167, 139, 250, 1);
            }
        """)
        self.toggle_select_btn.clicked.connect(self._toggle_selection_mode)
        title_layout.addWidget(self.toggle_select_btn)
        
        title_layout.addStretch()
        
        # 区域选择下拉框
        region_label = QLabel("区域：")
        region_label.setStyleSheet("color: #a1a1aa; font-size: 14px;")
        title_layout.addWidget(region_label)
        
        self.map_region_combo = QComboBox()
        self.map_region_combo.addItems(["G层（地面）", "B1层（地下1层）", "B2层（地下2层）"])
        self.map_region_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(39, 39, 42, 0.8);
                color: #e4e4e7;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 150px;
            }
            QComboBox:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.map_region_combo.currentIndexChanged.connect(self._on_map_region_changed)
        title_layout.addWidget(self.map_region_combo)
        
        # 资源类型选择（多选）
        resource_label = QLabel("资源：")
        resource_label.setStyleSheet("color: #a1a1aa; font-size: 14px;")
        title_layout.addWidget(resource_label)
        
        # 创建多选下拉框按钮
        self.map_resource_btn = QPushButton("全部显示")
        self.map_resource_btn.setFixedWidth(100)
        self.map_resource_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(39, 39, 42, 0.8);
                color: #e4e4e7;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 6px;
                padding: 6px 12px;
                text-align: left;
            }
            QPushButton:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
        """)
        self.map_resource_btn.clicked.connect(self._toggle_resource_menu)
        title_layout.addWidget(self.map_resource_btn)
        
        # 创建资源选择菜单
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
        
        # 眠枭之星显示按钮（多选下拉框）
        owl_stars_label = QLabel("其余：")
        owl_stars_label.setStyleSheet("color: #a1a1aa; font-size: 14px;")
        title_layout.addWidget(owl_stars_label)
        
        self.owl_stars_btn = QPushButton("全部隐藏")
        self.owl_stars_btn.setFixedWidth(100)
        self.owl_stars_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(39, 39, 42, 0.8);
                color: #e4e4e7;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 6px;
                padding: 6px 12px;
                text-align: left;
            }
            QPushButton:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
        """)
        self.owl_stars_btn.clicked.connect(self._toggle_owl_stars_menu)
        title_layout.addWidget(self.owl_stars_btn)
        
        # 创建眠枭之星选择菜单
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
        
        # 当前路线名称显示
        self.route_name_label = QLineEdit(self._current_route_name)
        self.route_name_label.setFixedWidth(120)
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
        title_layout.addWidget(self.route_name_label)
        
        # 路线列表折叠按钮
        self.route_list_btn = QPushButton("▼")
        self.route_list_btn.setFixedWidth(28)
        self.route_list_btn.setToolTip("路径列表")
        self.route_list_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(124, 58, 237, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(124, 58, 237, 0.5);
                border-radius: 4px;
                padding: 4px 6px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(124, 58, 237, 0.5);
            }
        """)
        self.route_list_btn.clicked.connect(self._show_route_list_menu)
        title_layout.addWidget(self.route_list_btn)
        
        # 导航按钮
        nav_btn = QPushButton("导航")
        nav_btn.setFixedWidth(60)
        nav_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 197, 94, 0.6);
                color: white;
                border: 2px solid rgba(74, 222, 128, 0.8);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(34, 197, 94, 0.8);
            }
            QPushButton:pressed {
                background-color: rgba(34, 197, 94, 0.4);
            }
        """)
        nav_btn.clicked.connect(self._start_navigation)
        title_layout.addWidget(nav_btn)
        
        # 路线编辑按钮区域（与悬浮窗地图一致）
        # 绘制路线按钮
        self.draw_route_btn = QPushButton("绘制路线")
        self.draw_route_btn.setFixedWidth(80)
        self.draw_route_btn.setCheckable(True)
        self.draw_route_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 197, 94, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(34, 197, 94, 0.5);
                border-radius: 4px;
                padding: 6px 8px;
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
        title_layout.addWidget(self.draw_route_btn)
        
        # 颜色选择器折叠按钮
        self.color_btn = QPushButton("▼")
        self.color_btn.setFixedWidth(28)
        self.color_btn.setToolTip("选择颜色")
        self.color_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 197, 94, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(34, 197, 94, 0.5);
                border-radius: 4px;
                padding: 6px 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(34, 197, 94, 0.5);
            }
        """)
        self.color_btn.clicked.connect(self._show_color_menu)
        title_layout.addWidget(self.color_btn)
        
        # 放置检查点按钮
        self.add_checkpoint_btn = QPushButton("检查点")
        self.add_checkpoint_btn.setFixedWidth(60)
        self.add_checkpoint_btn.setCheckable(True)
        self.add_checkpoint_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 165, 0, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(255, 165, 0, 0.5);
                border-radius: 4px;
                padding: 6px 8px;
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
        title_layout.addWidget(self.add_checkpoint_btn)
        
        # 清除路线按钮
        self.clear_route_btn = QPushButton("清除")
        self.clear_route_btn.setFixedWidth(50)
        self.clear_route_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(239, 68, 68, 0.5);
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.5);
            }
        """)
        self.clear_route_btn.clicked.connect(self._clear_route)
        title_layout.addWidget(self.clear_route_btn)
        
        # 断开路线按钮（用于传送点分段）
        self.break_route_btn = QPushButton("断开")
        self.break_route_btn.setFixedWidth(50)
        self.break_route_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(251, 146, 60, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(251, 146, 60, 0.5);
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(251, 146, 60, 0.5);
            }
        """)
        self.break_route_btn.clicked.connect(self._break_route)
        title_layout.addWidget(self.break_route_btn)
        
        # 撤销按钮（撤回上一个路径点）
        self.undo_route_btn = QPushButton("↩")
        self.undo_route_btn.setFixedWidth(40)
        self.undo_route_btn.setToolTip("撤回上一个路径点")
        self.undo_route_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(124, 58, 237, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(124, 58, 237, 0.5);
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(124, 58, 237, 0.5);
            }
        """)
        self.undo_route_btn.clicked.connect(self._undo_last_point)
        title_layout.addWidget(self.undo_route_btn)
        
        # 导出路线按钮
        self.export_route_btn = QPushButton("导出")
        self.export_route_btn.setFixedWidth(50)
        self.export_route_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(59, 130, 246, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(59, 130, 246, 0.5);
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(59, 130, 246, 0.5);
            }
        """)
        self.export_route_btn.clicked.connect(self._export_route)
        title_layout.addWidget(self.export_route_btn)
        
        # 导入路线按钮
        self.import_route_btn = QPushButton("导入")
        self.import_route_btn.setFixedWidth(50)
        self.import_route_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(168, 85, 247, 0.3);
                color: #e4e4e7;
                border: 1px solid rgba(168, 85, 247, 0.5);
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(168, 85, 247, 0.5);
            }
        """)
        self.import_route_btn.clicked.connect(self._import_route)
        title_layout.addWidget(self.import_route_btn)
        
        layout.addWidget(title_bar)
        
        # 版权信息
        copyright_label = QLabel("本页面数据来源于《洛克王国:世界》bwiki (https://wiki.biligame.com/rocom) 作者为BWIKI全体贡献者")
        copyright_label.setStyleSheet("""
            QLabel {
                color: #a1a1aa;
                font-size: 11px;
                padding: 4px 8px;
                background-color: rgba(39, 39, 42, 0.5);
            }
        """)
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)
        
        # 加载采集资源数据（使用 image/map/resource_configs.json）
        # 新版 resource_configs.json 同时包含 材料 / 宝箱 / 眠枭之星 三类数据
        # 材料 → collect_data（资源菜单）；宝箱+眠枭之星 → owl_stars_data（其余菜单）
        self.collect_data = {}
        self.selected_resources = set()  # 选中的资源集合
        self.owl_stars_data = {}
        self.selected_owl_stars = set()  # 选中的眠枭之星和宝箱集合
        collect_file = os.path.join(os.path.dirname(__file__), '..', 'image', 'map', 'resource_configs.json')
        if os.path.exists(collect_file):
            try:
                with open(collect_file, 'r', encoding='utf-8') as f:
                    raw_list = json.load(f)
                    # 转换为数组格式 → {name: {points: [...], markType}}
                    # 仅保留 layer=10003（主世界地图）的点位
                    # 注意：新文件 lat 符号约定与旧文件相反（新 lat = -旧 lat），
                    # 旧坐标转换公式 y=(4096-lat) 是按旧约定设计的，
                    # 因此这里加载时取反 lat，使现有公式继续正确工作
                    tmp_collect = {}   # 材料
                    tmp_owl = {}      # 宝箱 + 眠枭之星
                    for item in raw_list:
                        layer = str(item.get('layer', ''))
                        if layer != '10003':
                            continue
                        name = item.get('markTypeName', '')
                        if not name:
                            continue
                        lat = -item.get('lat', 0)  # 取反，对齐旧坐标系（南为负）
                        lng = item.get('lng', 0)
                        item_type = item.get('type', '')
                        # 宝箱分类合并：A1/A2/A2-2 等版本统一为单一分类
                        if item_type == '宝箱':
                            name = _merge_chest_name(name)
                        target = tmp_owl if item_type in ('宝箱', '眠枭之星') else tmp_collect
                        if name not in target:
                            target[name] = {
                                'points': [],
                                'markType': item.get('markType', 1),
                                'icon': item.get('icon', ''),  # 图标文件名，如 "星霜花.png"
                            }
                        target[name]['points'].append({'lat': lat, 'lng': lng})
                    self.collect_data = tmp_collect
                    self.owl_stars_data = tmp_owl

                    # 预加载资源图标到缓存（从 image/sc/ 目录加载每个资源对应的图标）
                    # 图标缺失映射：资源名在 sc 目录中无对应图标时，回退到指定文件
                    _ICON_FALLBACK = {
                        '蝠蝶兰': '蝴蝶兰.png',  # sc 目录中是"蝴蝶兰.png"而非"蝠蝶兰.png"
                    }
                    self._resource_icon_cache = {}
                    sc_dir = os.path.join(os.path.dirname(__file__), '..', 'image', 'sc')
                    for rname, rinfo in tmp_collect.items():
                        icon_file = rinfo.get('icon', '')
                        if not icon_file:
                            continue
                        icon_path = os.path.join(sc_dir, icon_file)
                        # 缺失则尝试回退映射
                        if not os.path.exists(icon_path) and rname in _ICON_FALLBACK:
                            icon_path = os.path.join(sc_dir, _ICON_FALLBACK[rname])
                        if os.path.exists(icon_path):
                            pix = QPixmap(icon_path)
                            if not pix.isNull():
                                self._resource_icon_cache[rname] = pix

                    # 填充资源菜单（多选复选框）- 仅材料
                    self.resource_checkboxes = {}
                    for resource_name in sorted(self.collect_data.keys()):
                        action = self.resource_menu.addAction(resource_name)
                        action.setCheckable(True)
                        action.setChecked(True)  # 默认全选
                        action.triggered.connect(lambda checked, name=resource_name: self._on_resource_toggled(name, checked))
                        self.resource_checkboxes[resource_name] = action
                        self.selected_resources.add(resource_name)

                    # 填充眠枭之星菜单（多选复选框）- 宝箱 + 眠枭之星
                    self.owl_stars_checkboxes = {}
                    for star_name in sorted(self.owl_stars_data.keys()):
                        action = self.owl_stars_menu.addAction(star_name)
                        action.setCheckable(True)
                        action.setChecked(False)  # 默认不选中
                        action.triggered.connect(lambda checked, name=star_name: self._on_owl_star_toggled(name, checked))
                        self.owl_stars_checkboxes[star_name] = action
            except Exception as e:
                print(f"[资源加载错误] {e}")

        # 创建地图显示标签（使用自定义MapLabel）
        self.map_label = MapLabel(self)
        self.map_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # 左上对齐，避免偏移
        self.map_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
            }
        """)
        
        # 创建滚动区域
        from PySide6.QtWidgets import QScrollArea
        self.map_scroll = QScrollArea()
        self.map_scroll.setWidget(self.map_label)
        self.map_scroll.setWidgetResizable(True)  # 允许自动调整大小
        self.map_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏滚动条
        self.map_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏滚动条
        # 关键：允许手动控制内容位置
        self.map_scroll.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.map_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        # 确保视口透明，不显示黑边
        self.map_scroll.viewport().setAutoFillBackground(False)
        self.map_scroll.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # 初始化缩放和平移
        self.map_scale = 1.0
        self.map_offset_x = 0
        self.map_offset_y = 0
        self.is_dragging = False
        self.drag_start_pos = None
        self._last_scale = 1.0  # 用于跟踪缩放变化
        self._last_coord_update_time = 0  # 用于坐标更新防抖
        
        # 路线编辑模式（与悬浮窗地图一致）
        self.route_edit_mode = False  # 是否在路线编辑模式
        self.is_placing_checkpoint = False  # 是否正在放置检查点
        self.route_segments = []  # 路线段列表，支持多段路线：[[(x,y,cp), ...], [(x,y,cp), ...], ...]
        self.route_history = []  # 路线历史，用于撤回
        self.route_visible = True  # 是否显示路线
        self.route_point_names = {}  # 路径点名称：{(seg_idx, pt_idx): "名称"}
        self.checkpoint_color = QColor(255, 165, 0, 255)  # 检查点颜色
        # route_color, saved_routes, _current_route_name 已在 __init__ 中提前初始化
        
        layout.addWidget(self.map_scroll, stretch=1)
        
        # 创建坐标显示标签（放在标题栏，偏左一点）
        from PySide6.QtWidgets import QLabel
        self.coord_label = QLabel("地图: (0, 0) | 游戏: (0, 0)")
        self.coord_label.setStyleSheet("""
            QLabel {
                color: #e4e4e7;
                padding: 4px 8px;
                font-size: 11px;
                font-family: 'Consolas', monospace;
            }
        """)
        title_layout.insertWidget(1, self.coord_label)  # 插入到第二个位置，让它偏左
        
        # 保存引用供其他方法使用
        self._map_view_widget = self.map_label

        # 初始加载地图
        self.current_region = "full"
        self._load_map_image("full")

        # 窗口显示后再做一次 fit-to-view（首次初始化时 viewport 尺寸可能尚未确定）
        try:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(50, self._fit_map_to_view)
        except Exception:
            pass

        return container
    
    def _on_map_region_changed(self, index):
        """区域切换事件"""
        region_map = {0: "full", 1: "b1", 2: "b2"}
        region = region_map.get(index, "full")
        self.current_region = region
        self._load_map_image(region)
    
    def _toggle_resource_menu(self):
        """显示/隐藏资源选择菜单"""
        # 在按钮下方显示菜单
        pos = self.map_resource_btn.mapToGlobal(QPoint(0, self.map_resource_btn.height()))
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
        if hasattr(self, 'map_label'):
            self.map_label.update()
    
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
        if hasattr(self, 'map_label'):
            self.map_label.update()
    
    def _update_resource_button_text(self):
        """更新资源按钮显示的文本"""
        total = len(self.collect_data)
        selected = len(self.selected_resources)
        
        if selected == 0:
            self.map_resource_btn.setText("全部隐藏")
        elif selected == total:
            self.map_resource_btn.setText("全部显示")
        else:
            self.map_resource_btn.setText(f"已选 {selected}/{total}")
    
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
        if hasattr(self, 'map_label'):
            self.map_label.update()
    
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
        if hasattr(self, 'map_label'):
            self.map_label.update()
    
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
    
    def _on_map_resource_changed(self, index):
        """资源类型切换事件（旧方法，保留兼容）"""
        # 触发地图重绘
        if hasattr(self, 'map_label'):
            self.map_label.update()
    
    def _toggle_selection_mode(self, checked):
        """切换游戏窗口框选模式"""
        if checked:
            # 进入框选模式，使用独立的圆形框选工具
            self._start_circle_selection()
        else:
            # 退出框选模式
            if hasattr(self, '_circle_selector') and self._circle_selector:
                self._circle_selector.close()
                self._circle_selector = None
    
    def _start_circle_selection(self):
        """启动圆形框选工具"""
        from core.circle_selector import CircleSelector
        
        # 创建框选工具
        self._circle_selector = CircleSelector()
        
        # 连接信号
        self._circle_selector.region_selected.connect(self._on_circle_selection_done)
        self._circle_selector.selection_cancelled.connect(self._on_circle_selection_cancelled)
        
        # 显示框选工具
        self._circle_selector.show()
        
        # 最小化主窗口
        self.showMinimized()
    
    def _on_circle_selection_done(self, x, y, width, height):
        """处理圆形框选完成"""
        # 恢复主窗口
        self.showNormal()
        
        # 显示框选结果
        
        # 保存框选区域供导航使用（持久化）
        self.circle_roi = (x, y, width, height)
        
        # 保存到配置文件
        if hasattr(self, 'settings_manager'):
            self.settings_manager.set("minimap_roi", {
                "x": x,
                "y": y,
                "width": width,
                "height": height
            })
            self.settings_manager.save_settings()
        
        # 更新按钮状态
        if hasattr(self, 'toggle_select_btn'):
            self.toggle_select_btn.setChecked(False)
        
        # 如果地图悬浮窗已打开，更新其小地图区域
        if hasattr(self, '_map_floating_window') and self._map_floating_window:
            self._map_floating_window.minimap_roi = self.circle_roi
    
    def _on_circle_selection_cancelled(self):
        """处理圆形框选取消"""
        # 恢复主窗口
        self.showNormal()
        
        # 更新按钮状态
        if hasattr(self, 'toggle_select_btn'):
                    self.toggle_select_btn.setChecked(False)
    
    def _update_coordinate_display(self, map_x, map_y):
        """更新坐标显示"""
        # 将地图坐标转换为中心原点坐标（新地图 8192x8192）
        # 地图像素 (0-8192) → 中心原点 (-4096 ~ +4096)
        lng = map_x - 4096
        lat = 4096 - map_y
        
        # 更新标签
        self.coord_label.setText(f"地图: ({map_x:.0f}, {map_y:.0f}) | 中心原点: (lat={lat:.0f}, lng={lng:.0f})")
    
    def _start_navigation(self):
        """开始导航功能：显示地图悬浮窗"""
        print("=== 开始导航 ===")
        print(f"当前线程: {__import__('threading').current_thread().name}")
        
        # 导入地图悬浮窗
        from ui.map_floating_window import MapFloatingWindow
        
        # 检查是否已有地图悬浮窗
        if hasattr(self, '_map_floating_window') and self._map_floating_window is not None:
            # 如果已存在，则显示它
            self._map_floating_window.show()
            self._map_floating_window.raise_()
            return
        
        # 创建新的地图悬浮窗
        self._map_floating_window = MapFloatingWindow(self, self.game_capture)
        
        # 从配置文件加载框选区域
        if hasattr(self, 'settings_manager'):
            saved_roi = self.settings_manager.get("minimap_roi")
            print(f"🔍 调试: settings_manager存在, saved_roi={saved_roi}")
            if saved_roi:
                self.circle_roi = (saved_roi['x'], saved_roi['y'], saved_roi['width'], saved_roi['height'])
                self._map_floating_window.minimap_roi = self.circle_roi
            else:
                print(f"⚠️ 配置文件中没有 minimap_roi")
        else:
            print(f"⚠️ MainWindow 没有 settings_manager")
        
        # 设置初始地图显示（使用当前加载的地图）
        if hasattr(self, 'current_region'):
            collect_data = getattr(self, 'collect_data', {})
            if self.current_region == 'full':
                # full 层：优先使用嵌入到 exe 的地图数据
                from core.map_navigation import load_map_full_hq_pixmap
                map_pix = load_map_full_hq_pixmap()
                self._map_floating_window.update_map_display(None, collect_data, map_pixmap=map_pix)
            else:
                map_path = get_resource_path(os.path.join("image", f'map_{self.current_region}.png'))
                if os.path.exists(map_path):
                    self._map_floating_window.update_map_display(map_path, collect_data)
        
        # 显示悬浮窗
        self._map_floating_window.show()
        self._map_floating_window.raise_()
        
        # 同步路线数据到悬浮窗
        self._sync_routes_to_floating_window()
    
    def _on_selection_done(self, rect):
        """处理框选完成"""
        print(f"_on_selection_done: {rect}")
        self._process_selection(rect)
    
    def _process_selection(self, rect):
        """处理框选结果"""
        # 这里可以添加图像识别逻辑来识别人物位置
        # 目前先模拟一个位置（眠枭庇护所附近）
        player_lat = 1387
        player_lng = -1457
        
        # 在地图上显示人物位置
        self._show_player_position(player_lat, player_lng)
    
    def _game_to_map_coords(self, lat, lng):
        """将中心原点坐标转换为地图像素坐标（新地图 8192x8192）
        
        Args:
            lat: 中心原点 Y 坐标（-4096 ~ +4096，与 ResourceExporter.java 输出一致）
            lng: 中心原点 X 坐标（-4096 ~ +4096，与 ResourceExporter.java 输出一致）
            
        Returns:
            (x, y): 显示地图像素坐标（0 ~ map_width/height）
        """
        scale = self.map_width / 8192.0
        # 中心原点 → 左上角原点：X 平移 +4096，Y 反转后平移 +4096
        x = (lng + 4096) * scale
        y = (4096 - lat) * scale
        return x, y
    
    def _show_player_position(self, lat, lng):
        """在地图上显示玩家位置"""
        # 清除旧的玩家标记
        if hasattr(self, '_player_marker'):
            self.map_scene.removeItem(self._player_marker)
        
        # 使用统一的坐标转换方法
        x, y = self._game_to_map_coords(lat, lng)
        
        # 加载指针图片
        import os
        pointer_path = os.path.join(os.path.dirname(__file__), '..', 'image', 'zz.png')
        
        from PySide6.QtGui import QPixmap
        if os.path.exists(pointer_path):
            pixmap = QPixmap(pointer_path)
            # 根据缩放级别调整大小
            icon_size = max(24, int(32 * self.current_zoom))
            pixmap = pixmap.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # 创建图片项
            self._player_marker = self.map_scene.addPixmap(pixmap)
            # 设置位置（图片中心对齐到坐标点）
            self._player_marker.setPos(x - pixmap.width()/2, y - pixmap.height()/2)
            
            print(f"玩家位置: (lat={lat}, lng={lng}) -> (x={x:.1f}, y={y:.1f})")
        else:
            # 如果没有图片，用圆形代替
            circle_radius = max(8, int(10 * self.current_zoom))
            circle = self.map_scene.addEllipse(x - circle_radius, y - circle_radius, 
                                               circle_radius * 2, circle_radius * 2)
            circle.setBrush(QBrush(QColor(255, 0, 0)))
            circle.setPen(QPen(QColor(255, 255, 0), max(1, int(2 * self.current_zoom))))
            self._player_marker = circle
            print(f"警告: 未找到指针图片 zz.png，使用红色圆圈标记")
    
    def _load_map_image(self, region):
        """加载指定区域的地图图片"""

        if region == 'full':
            # 使用高清完整地图：优先嵌入到 exe 的数据，其次外部文件
            from core.map_navigation import load_map_full_hq_pixmap
            self.map_pixmap = load_map_full_hq_pixmap()

            if self.map_pixmap.isNull():
                logger.log("⚠️ G层高清地图加载失败（嵌入数据与外部文件均不可用）")
                return

            self.map_width = self.map_pixmap.width()
            self.map_height = self.map_pixmap.height()
        elif region in ['b1', 'b2']:
            # B1/B2 层使用新拼接的地图
            map_path = get_resource_path(os.path.join("image", f'map_full_{region}.png'))
            
            if not os.path.exists(map_path):
                logger.log(f"⚠️ B1/B2地图文件不存在: {map_path}")
                return
            
            from PySide6.QtGui import QPixmap
            self.map_pixmap = QPixmap(map_path)
            
            if self.map_pixmap.isNull():
                logger.log(f"⚠️ B1/B2地图加载失败: {map_path}")
                return
            
            self.map_width = self.map_pixmap.width()
            self.map_height = self.map_pixmap.height()
        else:
            # 其他区域仍使用瓦片拼接（保留旧逻辑）
            tiles_dir = get_resource_path(os.path.join("image", "map_tiles_complete"))
            
            if not os.path.exists(tiles_dir):
                logger.log(f"⚠️ 瓦片目录不存在: {tiles_dir}")
                return
            
            # 找出瓦片的范围
            min_x, max_x = 0, 0
            min_y, max_y = 0, 0
            tile_size = 256
            
            for filename in os.listdir(tiles_dir):
                if filename.startswith('tile_') and filename.endswith('.png'):
                    try:
                        name = filename[5:-4]
                        parts = name.split('_')
                        if len(parts) == 2:
                            tx, ty = int(parts[0]), int(parts[1])
                            min_x = min(min_x, tx)
                            max_x = max(max_x, tx)
                            min_y = min(min_y, ty)
                            max_y = max(max_y, ty)
                    except:
                        pass
            
            
            # 计算总地图尺寸
            map_width = (max_x - min_x + 1) * tile_size
            map_height = (max_y - min_y + 1) * tile_size
            
            # 创建空白图片
            from PySide6.QtGui import QPixmap, QPainter
            combined_pixmap = QPixmap(map_width, map_height)
            combined_pixmap.fill(QColor(255, 255, 255))  # 白色背景
            
            painter = QPainter(combined_pixmap)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            
            # 加载并绘制瓦片
            loaded_count = 0
            for filename in os.listdir(tiles_dir):
                if filename.startswith('tile_') and filename.endswith('.png'):
                    try:
                        name = filename[5:-4]
                        parts = name.split('_')
                        if len(parts) == 2:
                            tx, ty = int(parts[0]), int(parts[1])
                            tile_path = os.path.join(tiles_dir, filename)
                            
                            pixmap = QPixmap(tile_path)
                            if not pixmap.isNull():
                                pos_x = (tx - min_x) * tile_size
                                pos_y = (ty - min_y) * tile_size
                                painter.drawPixmap(pos_x, pos_y, pixmap)
                                loaded_count += 1
                    except Exception as e:
                        pass  # 忽略单个瓦片加载错误
            
            painter.end()
            
            self.map_pixmap = combined_pixmap
            self.map_width = map_width
            self.map_height = map_height
        
        # 设置map_label的大小为地图实际尺寸
        # 注意：不再 setFixedSize，让 QScrollArea 自动调整 widget = viewport 大小
        # 这样 paintEvent 中 target_rect = self.rect() 始终覆盖整个视口（无黑边）

        # 自动适配视图：让整张地图正好填满视口并居中
        self._fit_map_to_view()

        # 更新标记
        self._update_markers()

    def _fit_map_to_view(self):
        """让整张地图正好填满视口并居中显示（首次加载/切换地图时调用）
        策略：用 max() 比例保证地图铺满视口（无黑色边框），看到的是地图中心区域。
        """
        if not hasattr(self, 'map_width') or not hasattr(self, 'map_height'):
            return
        if not hasattr(self, 'map_scroll') or self.map_scroll is None:
            return
        viewport = self.map_scroll.viewport()
        if viewport is None:
            return
        vw = max(1, viewport.width())
        vh = max(1, viewport.height())
        # 用 max 比例：保证地图至少铺满视口（较短边正好填满，较长边超出）
        fit_scale = max(vw / self.map_width, vh / self.map_height)
        fit_scale = max(0.01, min(fit_scale, 5.0))
        self.map_scale = fit_scale
        # 让地图中心对齐视口中心
        scaled_w = self.map_width * self.map_scale
        scaled_h = self.map_height * self.map_scale
        self.map_offset_x = (vw - scaled_w) / 2
        self.map_offset_y = (vh - scaled_h) / 2
        self._clamp_map_offset()
        self._last_scale = self.map_scale
        self.map_label.update()
    
    def _update_markers(self):
        """更新地图上的采集点标记 - 现在只需触发重绘"""
        # 只需触发重绘 - paintEvent 会处理绘制
        self._update_map_display()
    
    def _on_map_mouse_press(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            # 如果在路线编辑模式
            if self.route_edit_mode:
                # 计算点击在地图上的坐标（转换为原始地图坐标）
                pos = event.pos()
                original_x = (pos.x() - self.map_offset_x) / self.map_scale
                original_y = (pos.y() - self.map_offset_y) / self.map_scale
                
                # 添加路线点到当前路线段
                self.route_history.append([seg.copy() for seg in self.route_segments])
                
                # 如果没有路线段，创建一个新的
                if not self.route_segments:
                    self.route_segments.append([])
                
                # 添加到最后一个路线段
                self.route_segments[-1].append((original_x, original_y, self.is_placing_checkpoint))
                
                # 更新显示
                self._update_map_display()
                event.accept()
                return
            
            self.is_dragging = True
            self.drag_start_pos = event.pos()
            self.map_label.setCursor(Qt.ClosedHandCursor)
            self.map_label.grabMouse()  # 捕获鼠标
            event.accept()  # 接受事件，阻止传播
    
    def _on_map_mouse_move(self, event):
        """鼠标移动事件"""
        # 更新坐标显示
        if hasattr(self, 'coord_label'):
            pos = event.pos()
            map_x = (pos.x() - self.map_offset_x) / self.map_scale
            map_y = (pos.y() - self.map_offset_y) / self.map_scale
            self._update_coordinate_display(map_x, map_y)
        
        # 拖拽移动
        if self.is_dragging and self.drag_start_pos:
            delta = event.pos() - self.drag_start_pos
            self.map_offset_x += delta.x()
            self.map_offset_y += delta.y()
            self._clamp_map_offset()
            self.drag_start_pos = event.pos()
            self._update_map_display()
            event.accept()  # 接受事件
    
    def _on_map_mouse_release(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            self.drag_start_pos = None
            self.map_label.setCursor(Qt.ArrowCursor)
            self.map_label.releaseMouse()  # 释放鼠标
            event.accept()
    
    def _on_map_wheel(self, event):
        """滚轮缩放事件"""
        # Ctrl+滚轮缩放
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._zoom_map(1.2)
            else:
                self._zoom_map(0.8)
            event.accept()
        else:
            # 普通滚轮平移
            delta = event.angleDelta().y()
            self.map_offset_y += delta
            self._clamp_map_offset()
            self._update_map_display()
            event.accept()

    def _clamp_map_offset(self):
        """限制地图偏移：到地图边缘时直接拉不动（不露出地图外的黑色区域）
        核心策略：保证地图始终 >= 视口，offset 限制在 [viewport-scaled, 0]。
        这样地图永远填满视口，且 source_rect 不超出地图范围（不拉伸）。
        """
        if not hasattr(self, 'map_scroll') or not hasattr(self, 'map_label'):
            return
        if not hasattr(self, 'map_width') or not hasattr(self, 'map_height'):
            return
        # 用 MapLabel 的实际尺寸（和 paintEvent 一致）
        vw = max(1, self.map_label.width())
        vh = max(1, self.map_label.height())
        if vw <= 1 or vh <= 1:
            # MapLabel 未就绪，尝试 viewport
            viewport = self.map_scroll.viewport()
            if viewport:
                vw = max(1, viewport.width())
                vh = max(1, viewport.height())
        if vw <= 1 or vh <= 1:
            return  # 仍未就绪，跳过
        scale = self.map_scale if self.map_scale > 0 else 1.0
        scaled_w = self.map_width * scale
        scaled_h = self.map_height * scale
        # 关键：如果地图比视口小，强制增大 scale 让地图填满视口
        # 这样 offset 范围始终是 [viewport-scaled, 0]（负数到0）
        if scaled_w < vw:
            scale = vw / self.map_width
            self.map_scale = scale
            scaled_w = self.map_width * scale
        if scaled_h < vh:
            scale = max(scale, vh / self.map_height)
            self.map_scale = scale
            scaled_h = self.map_height * scale
        # offset 限制在 [viewport-scaled, 0]：到边缘时拉不动
        self.map_offset_x = max(vw - scaled_w, min(0, self.map_offset_x))
        self.map_offset_y = max(vh - scaled_h, min(0, self.map_offset_y))
    
    def _update_map_display(self):
        """更新地图显示 - 只触发重绘，不重新生成pixmap"""
        # 直接触发map_label的重绘
        if hasattr(self, 'map_label'):
            self.map_label.update()  # 触发paintEvent
    
    def _zoom_map(self, factor, mouse_pos=None):
        """缩放地图 - 以鼠标位置为中心"""
        old_scale = self.map_scale
        self.map_scale *= factor
        
        # 动态计算最小缩放比例，确保地图始终填满视口
        min_scale = 1.0  # 默认最小值
        if hasattr(self, 'map_width') and hasattr(self, 'map_height') and hasattr(self, 'map_scroll'):
            # 获取视口大小
            viewport_width = self.map_scroll.viewport().width()
            viewport_height = self.map_scroll.viewport().height()
            
            # 计算能让地图填满视口的最小缩放比例
            scale_by_width = viewport_width / self.map_width
            scale_by_height = viewport_height / self.map_height
            min_scale = max(scale_by_width, scale_by_height)
            
            # 设置最小缩放为计算值和 0.1 的较大者，确保能看到完整地图
            min_scale = max(0.1, min_scale)
        
        self.map_scale = max(min_scale, min(self.map_scale, 5.0))  # 限制缩放范围
        
        # 如果提供了鼠标位置，以鼠标位置为中心缩放
        if mouse_pos is not None:
            mouse_x = mouse_pos.x()
            mouse_y = mouse_pos.y()
            
            # 计算鼠标位置在缩放前的地图坐标
            old_map_x = (mouse_x - self.map_offset_x) / old_scale if old_scale != 0 else 0
            old_map_y = (mouse_y - self.map_offset_y) / old_scale if old_scale != 0 else 0
            
            # 计算缩放后鼠标位置应该在的地图坐标
            new_map_x = old_map_x
            new_map_y = old_map_y
            
            # 计算新的offset，使鼠标位置保持不变
            new_offset_x = mouse_x - new_map_x * self.map_scale
            new_offset_y = mouse_y - new_map_y * self.map_scale
            
            # 平滑过渡，避免跳动
            self.map_offset_x = new_offset_x
            self.map_offset_y = new_offset_y
        # 如果没有鼠标位置（按钮缩放），保持当前offset
        
        # 更新map_label的大小以匹配缩放后的图片
        # 注意：不再 setFixedSize，widget 大小 = viewport 大小（由 QScrollArea 自动管理）
        # paintEvent 会根据 map_scale 和 offset 绘制地图的可见部分

        # 限制偏移，确保地图填满视口
        self._clamp_map_offset()
        
        # 触发重绘
        self._update_map_display()
        
        # 更新_last_scale以反映当前缩放级别
        self._last_scale = self.map_scale
    
    def _reset_zoom(self):
        """重置缩放"""
        self.map_scale = 1.0
        self.map_offset_x = 0
        self.map_offset_y = 0
        self._update_map_display()
        
    # ============ 路线编辑功能 ============
    def _toggle_route_edit_mode(self):
        """切换路线编辑模式"""
        self.route_edit_mode = self.draw_route_btn.isChecked()
        if self.route_edit_mode:
            self.is_placing_checkpoint = False
            self.add_checkpoint_btn.setChecked(False)
            self.map_label.route_preview_point = None
            self.map_label.route_preview_mouse = None
            self.map_label.route_snapped = False
            self.map_label.setCursor(Qt.CrossCursor)
        else:
            # 退出绘制模式时清除预览
            self.map_label.route_preview_point = None
            self.map_label.route_preview_mouse = None
            self.map_label.route_snapped = False
            self.map_label.route_connect_mode = False
            self.map_label.route_connect_source = None
            self.map_label.setCursor(Qt.ArrowCursor)
        self.map_label.update()
    
    def _toggle_checkpoint_mode(self):
        """切换检查点模式"""
        self.is_placing_checkpoint = self.add_checkpoint_btn.isChecked()
        if self.is_placing_checkpoint:
            self.route_edit_mode = True
            self.draw_route_btn.setChecked(True)
        else:
            pass
    
    def _clear_route(self):
        """清除路线"""
        self.route_history.append([seg.copy() for seg in self.route_segments])
        self.route_segments = []
        self.route_point_names = {}
        if hasattr(self, 'map_label'):
            self.map_label.selected_route_point = None
            self.map_label.selected_route_points.clear()
            self.map_label.selected_route_segments.clear()
            self.map_label.route_preview_point = None
            self.map_label.route_preview_mouse = None
            self.map_label.route_connect_mode = False
            self.map_label.route_connect_source = None
        self._update_map_display()
    
    def _undo_last_point(self):
        """撤回上一个路线点（与悬浮窗小地图一致）"""
        if len(self.route_history) > 0:
            last_state = self.route_history.pop()
            self.route_segments = last_state
            self._update_map_display()
    
    def _break_route(self):
        """断开路线 - 开始新的路线段（用于传送点分段）"""
        if self.route_segments:
            self.route_history.append([seg.copy() for seg in self.route_segments])
        if not self.route_segments or len(self.route_segments[-1]) > 0:
            self.route_segments.append([])
        self._update_map_display()
    
    def _export_route(self):
        """导出路线到文件"""
        has_route = any(len(seg) > 0 for seg in self.route_segments)
        if not has_route:
            return
        
        from PySide6.QtWidgets import QFileDialog
        import json
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出路线",
            "",
            "JSON文件 (*.json);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                route_data = {
                    "version": "2.1",
                    "name": self._current_route_name,
                    "color": self._get_color_name(self.route_color),
                    "segments": [
                        [{"x": float(p[0]), "y": float(p[1]), "checkpoint": p[2]} for p in seg]
                        for seg in self.route_segments
                    ]
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(route_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                pass
    
    def _import_route(self):
        """从文件导入路线"""
        from PySide6.QtWidgets import QFileDialog
        import json
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入路线",
            "",
            "JSON文件 (*.json);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    route_data = json.load(f)
                
                # 保存当前路线到 saved_routes（如果有内容）
                self._save_current_route()
                
                self.route_history.append([seg.copy() for seg in self.route_segments])
                self.route_segments = []
                
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
                    segment = []
                    for p in route_data.get("points", []):
                        x = p.get("x", 0)
                        y = p.get("y", 0)
                        is_checkpoint = p.get("checkpoint", False)
                        segment.append((x, y, is_checkpoint))
                    if segment:
                        self.route_segments.append(segment)
                
                # 读取路线颜色
                route_color = route_data.get("color", "green")
                self._apply_route_color(route_color)
                
                # 读取路线名称
                route_name = route_data.get("name", "")
                if not route_name:
                    route_name = os.path.splitext(os.path.basename(file_path))[0]
                self._current_route_name = route_name
                if hasattr(self, 'route_name_label'):
                    self.route_name_label.setText(route_name)
                
                # 添加到已保存路线列表
                self._add_route_to_saved(route_name)
                
                self._update_map_display()
            except Exception as e:
                pass
    
    # ============ 路线编辑功能结束 ============
    
    # ============ 路线管理功能 ============
    def _save_current_route(self):
        """保存当前路线到 saved_routes"""
        has_route = any(len(seg) > 0 for seg in self.route_segments)
        if not has_route:
            return
        # 查找是否已有同名路线，有则更新，否则新增
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
        # 检查是否已存在同名路线
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
                
                # 添加操作子菜单（删除 / 修改）
                sub_menu = QMenu()
                sub_menu.setStyleSheet("""
                    QMenu {
                        background-color: rgba(30, 30, 38, 0.95);
                        border: 1px solid rgba(124, 58, 237, 0.5);
                        border-radius: 4px;
                        padding: 4px;
                    }
                    QMenu::item {
                        padding: 6px 16px;
                        color: #e4e4e7;
                        font-size: 11px;
                    }
                    QMenu::item:selected {
                        background-color: rgba(124, 58, 237, 0.3);
                    }
                """)
                # 删除
                delete_action = sub_menu.addAction("🗑  删除")
                delete_action.triggered.connect(lambda checked, i=idx: self._delete_route(i))

                # 修改子菜单（自由变换）
                modify_sub_menu = QMenu()
                modify_sub_menu.setStyleSheet(sub_menu.styleSheet())
                free_transform_action = modify_sub_menu.addAction("自由变换")
                free_transform_action.triggered.connect(lambda checked, i=idx: self._enter_route_transform_mode(i))
                modify_action = sub_menu.addAction("修改")
                modify_action.setMenu(modify_sub_menu)

                action.setMenu(sub_menu)
        
        pos = self.route_list_btn.mapToGlobal(QPoint(0, self.route_list_btn.height()))
        menu.exec(pos)
    
    def _show_color_menu(self):
        """显示颜色选择菜单"""
        from PySide6.QtWidgets import QMenu, QWidgetAction, QWidget, QHBoxLayout
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
            # 创建带颜色方块的图标
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
        # 更新颜色按钮样式
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
                padding: 6px 8px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: rgba({r}, {g}, {b}, 0.5);
            }}
        """)
        self._update_map_display()
    
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
        # 保存当前路线
        self._save_current_route()
        # 加载目标路线
        route = self.saved_routes[route_index]
        self.route_history.append([seg.copy() for seg in self.route_segments])
        self.route_segments = [seg.copy() for seg in route.get("segments", [])]
        self._current_route_name = route["name"]
        if hasattr(self, 'route_name_label'):
            self.route_name_label.setText(route["name"])
        color_name = route.get("color", "green")
        self._apply_route_color(color_name)
        self._update_map_display()
    
    def _delete_route(self, route_index):
        """删除指定路线"""
        if route_index < 0 or route_index >= len(self.saved_routes):
            return
        del self.saved_routes[route_index]
        # 如果列表为空，重置当前路线名称
        if not self.saved_routes:
            self._current_route_name = "未命名路线"
            if hasattr(self, 'route_name_label'):
                self.route_name_label.setText("未命名路线")

    # ============ 路线自由变换模式（PS 风格变换框） ============

    def _enter_route_transform_mode(self, route_index):
        """进入路线自由变换模式"""
        if route_index < 0 or route_index >= len(self.saved_routes):
            return
        # 切换到目标路线
        self._switch_to_route(route_index)
        self.route_transform_route_index = route_index
        # 保存原始 segments（ESC 恢复用）
        self.route_transform_original = [seg.copy() for seg in self.saved_routes[route_index].get("segments", [])]
        self.route_transform_active = True
        self.route_transform_action = None
        self.route_transform_press_pos = None
        self.route_transform_start_segments = None
        self._update_route_transform_bbox()
        self._show_route_transform_panel()
        if hasattr(self, 'map_label'):
            self.map_label.setFocus()
            self.map_label.update()

    def _exit_route_transform_mode(self, apply_changes=True):
        """退出路线自由变换模式"""
        route_index = self.route_transform_route_index
        if not apply_changes:
            # ESC：恢复原始数据
            if 0 <= route_index < len(self.saved_routes) and self.route_transform_original is not None:
                self.saved_routes[route_index]["segments"] = [seg.copy() for seg in self.route_transform_original]
                self.route_segments = [seg.copy() for seg in self.route_transform_original]
                self._update_map_display()
        else:
            # Enter：写回变换后的数据并同步到悬浮窗
            if 0 <= route_index < len(self.saved_routes):
                self.saved_routes[route_index]["segments"] = [seg.copy() for seg in self.route_segments]
            if hasattr(self, '_sync_routes_to_floating_window'):
                self._sync_routes_to_floating_window()
        # 重置状态
        self.route_transform_active = False
        self.route_transform_route_index = -1
        self.route_transform_original = None
        self.route_transform_action = None
        self.route_transform_press_pos = None
        self.route_transform_start_segments = None
        self.route_transform_bbox = None
        self._route_transform_anchor = None
        self._route_transform_initial_angle = None
        self._hide_route_transform_panel()
        if hasattr(self, 'map_label'):
            self.map_label.update()

    def _update_route_transform_bbox(self):
        """计算当前 route_segments 的包围盒（地图世界坐标）"""
        all_pts = [(p[0], p[1]) for seg in self.route_segments for p in seg]
        if not all_pts:
            self.route_transform_bbox = None
            return
        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        self.route_transform_bbox = (min(xs), min(ys), max(xs), max(ys))

    def _apply_transform_param(self, kind, value):
        """参数面板应用变换（在当前 route_segments 基础上累积）"""
        if not self.route_transform_active or not self.route_segments:
            return
        bbox = self.route_transform_bbox
        if not bbox:
            return
        min_x, min_y, max_x, max_y = bbox
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        if kind == 'scale':
            factor = float(value)
            if abs(factor) < 1e-6:
                return
            new_segs = [
                [((cx + (p[0] - cx) * factor), (cy + (p[1] - cy) * factor), p[2]) for p in seg]
                for seg in self.route_segments
            ]
        elif kind == 'rotate':
            angle = float(value)
            rad = math.radians(angle)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            new_segs = []
            for seg in self.route_segments:
                new_seg = []
                for (x, y, cp) in seg:
                    dx = x - cx
                    dy = y - cy
                    new_x = cx + dx * cos_a - dy * sin_a
                    new_y = cy + dx * sin_a + dy * cos_a
                    new_seg.append((new_x, new_y, cp))
                new_segs.append(new_seg)
        elif kind == 'move':
            dx, dy = float(value[0]), float(value[1])
            new_segs = [
                [((p[0] + dx), (p[1] + dy), p[2]) for p in seg]
                for seg in self.route_segments
            ]
        else:
            return
        self.route_segments = new_segs
        self._update_route_transform_bbox()
        self._update_map_display()

    def _show_route_transform_panel(self):
        """显示路线变换参数浮动面板"""
        self._hide_route_transform_panel()
        panel = QFrame(self.map_scroll.viewport())
        panel.setObjectName("routeTransformPanel")
        panel.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 38, 0.95);
                border: 1px solid rgba(124, 58, 237, 0.6);
                border-radius: 8px;
            }
            QLabel { color: #e4e4e7; font-size: 11px; }
            QPushButton {
                background-color: rgba(124, 58, 237, 0.4);
                color: white;
                border: 1px solid rgba(124, 58, 237, 0.8);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: rgba(124, 58, 237, 0.7); }
            QLineEdit, QDoubleSpinBox {
                background-color: rgba(20, 20, 28, 0.9);
                color: #e4e4e7;
                border: 1px solid rgba(124, 58, 237, 0.4);
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 11px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        title = QLabel("变换参数")
        title.setStyleSheet("color: #c4b5fd; font-size: 12px; font-weight: bold;")
        layout.addWidget(title)

        # 缩放
        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("缩放比例:"))
        scale_input = QDoubleSpinBox()
        scale_input.setRange(0.05, 20.0)
        scale_input.setValue(1.0)
        scale_input.setDecimals(2)
        scale_input.setSingleStep(0.1)
        scale_row.addWidget(scale_input)
        scale_btn = QPushButton("应用")
        scale_btn.clicked.connect(lambda checked, w=scale_input: self._apply_transform_param('scale', w.value()))
        scale_row.addWidget(scale_btn)
        layout.addLayout(scale_row)

        # 旋转
        rotate_row = QHBoxLayout()
        rotate_row.addWidget(QLabel("旋转角度:"))
        rotate_input = QDoubleSpinBox()
        rotate_input.setRange(-360.0, 360.0)
        rotate_input.setValue(0.0)
        rotate_input.setDecimals(1)
        rotate_input.setSingleStep(15.0)
        rotate_row.addWidget(rotate_input)
        rotate_btn = QPushButton("应用")
        rotate_btn.clicked.connect(lambda checked, w=rotate_input: self._apply_transform_param('rotate', w.value()))
        rotate_row.addWidget(rotate_btn)
        layout.addLayout(rotate_row)

        # 移动
        move_row = QHBoxLayout()
        move_row.addWidget(QLabel("dx:"))
        dx_input = QDoubleSpinBox()
        dx_input.setRange(-8192.0, 8192.0)
        dx_input.setValue(0.0)
        dx_input.setDecimals(1)
        move_row.addWidget(dx_input)
        move_row.addWidget(QLabel("dy:"))
        dy_input = QDoubleSpinBox()
        dy_input.setRange(-8192.0, 8192.0)
        dy_input.setValue(0.0)
        dy_input.setDecimals(1)
        move_row.addWidget(dy_input)
        move_btn = QPushButton("应用")
        move_btn.clicked.connect(lambda checked, w1=dx_input, w2=dy_input: self._apply_transform_param('move', (w1.value(), w2.value())))
        move_row.addWidget(move_btn)
        layout.addLayout(move_row)

        # 确认/取消
        btn_row = QHBoxLayout()
        ok_btn = QPushButton("确认 (Enter)")
        ok_btn.clicked.connect(lambda: self._exit_route_transform_mode(apply_changes=True))
        btn_row.addWidget(ok_btn)
        cancel_btn = QPushButton("取消 (ESC)")
        cancel_btn.clicked.connect(lambda: self._exit_route_transform_mode(apply_changes=False))
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        panel.adjustSize()
        panel_w = max(panel.sizeHint().width(), 250)
        panel_h = max(panel.sizeHint().height(), 180)
        try:
            vp_w = self.map_scroll.viewport().width()
        except Exception:
            vp_w = 800
        panel.setGeometry(max(0, vp_w - panel_w - 10), 10, panel_w, panel_h)
        # 给面板及所有子控件安装事件过滤器，让 Enter/ESC 能被 MainWindow 捕获
        panel.installEventFilter(self)
        for child in panel.findChildren(QObject):
            child.installEventFilter(self)
        panel.show()
        panel.raise_()
        self.route_transform_panel = panel

    def eventFilter(self, obj, event):
        """事件过滤器：在变换模式下捕获 Enter/ESC 键"""
        if self.route_transform_active and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Return or key == Qt.Key_Enter:
                self._exit_route_transform_mode(apply_changes=True)
                return True
            elif key == Qt.Key_Escape:
                self._exit_route_transform_mode(apply_changes=False)
                return True
        return super().eventFilter(obj, event)

    def _hide_route_transform_panel(self):
        """隐藏并销毁路线变换参数面板"""
        if self.route_transform_panel is not None:
            self.route_transform_panel.setParent(None)
            self.route_transform_panel.deleteLater()
            self.route_transform_panel = None

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
    
    def _sync_routes_to_floating_window(self):
        """同步路线数据到悬浮窗"""
        if hasattr(self, '_map_floating_window') and self._map_floating_window is not None:
            fw = self._map_floating_window
            # 同步已保存的路线列表
            fw.saved_routes = [r.copy() for r in self.saved_routes]
            fw._current_route_name = self._current_route_name
            if hasattr(fw, 'route_name_label'):
                fw.route_name_label.setText(self._current_route_name)
            # 同步当前路线段
            fw.route_segments = [seg.copy() for seg in self.route_segments]
            fw.route_color = QColor(self.route_color)
            if hasattr(fw, 'map_label'):
                fw.map_label.route_color = self.route_color
            if hasattr(fw, '_update_route_display'):
                fw._update_route_display()
    
    # ============ 路线管理功能结束 ============
    
    def _update_markers(self):
        """更新地图上的采集点标记（B1/B2层不显示）"""
        # B1/B2 层不显示资源标记
        if hasattr(self, 'current_region') and self.current_region in ['b1', 'b2']:
            return
        
        # 只需触发重绘 - paintEvent 会处理绘制
        self._update_map_display()

    def _get_pokemon_image_path(self, pokemon_name):
        """获取精灵图片路径（支持赛季目录）"""
        # 先尝试从当前赛季目录加载
        season = self.season_combo.currentText() if hasattr(self, 'season_combo') else "第三赛季"
        season_dir = os.path.join(self._base_dir, "image", "ys", season)
        image_path = os.path.join(season_dir, f"{pokemon_name}.png")
        if os.path.exists(image_path):
            return image_path
        
        # 尝试从通用目录加载（向后兼容）
        ys_dir = os.path.join(self._base_dir, "image", "ys")
        image_path = os.path.join(ys_dir, f"{pokemon_name}.png")
        if os.path.exists(image_path):
            return image_path
        
        return None
