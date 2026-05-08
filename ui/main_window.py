from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QStackedWidget,
    QProgressBar, QFrame, QScrollArea, QLineEdit, QDialog, QFormLayout,
    QDialogButtonBox, QMessageBox, QInputDialog, QMenu, QGraphicsDropShadowEffect, QComboBox, QGroupBox, QCheckBox, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal, QPoint, QSize, QRect, QTimer
from PySide6.QtGui import QFont, QIcon, QPainter, QColor, QLinearGradient, QPen, QBrush, QPainterPath, QPolygon, QPixmap
import os
import cv2

from core.pokemon_data import POKEMON_LIST, get_all_pokemon, save_custom_pokemon, load_custom_pokemon
from core.counter_manager import CounterManager, Counter
from core.game_capture import GameCapture
from core.evolution_manager import EvolutionManager
from core.settings_manager import SettingsManager
from core.pokemon_types import get_all_types
from core.logger import logger
from ui.floating_window import FloatingWindow
from ui.settings_dialog import SettingsDialog
from ui.debug_window import DebugWindow
from ui.pokedex_view import PokedexWidget, SCROLL_BAR_STYLE
from ui.damage_calculator import DamageCalculatorWidget
from ui.type_effectiveness import TypeEffectivenessWidget


class FoldButton(QPushButton):
    """折叠按钮 - 三角形图标（参考HTML设计）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_folded = False
        self.setFixedSize(28, 28)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制三角形
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#a78bfa"))
        
        size = self.size()
        center_x = size.width() / 2
        center_y = size.height() / 2
        
        # 根据折叠状态旋转三角形
        if self.is_folded:
            # 向右的三角形 ▶
            points = [
                QPoint(int(center_x - 4), int(center_y - 6)),
                QPoint(int(center_x - 4), int(center_y + 6)),
                QPoint(int(center_x + 4), int(center_y))
            ]
        else:
            # 向下的三角形 ▼
            points = [
                QPoint(int(center_x - 6), int(center_y - 4)),
                QPoint(int(center_x + 6), int(center_y - 4)),
                QPoint(int(center_x), int(center_y + 4))
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
        
        # 绘制滑轨背景
        if self.isChecked():
            painter.setBrush(QColor(124, 58, 237))  # 紫色
        else:
            painter.setBrush(QColor(63, 63, 70))  # 深灰
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), self.height() / 2, self.height() / 2)
        
        # 绘制滑块
        slider_size = self.height() - 4
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            int(self._offset),
            2,
            slider_size,
            slider_size
        )

class CustomPokemonDialog(QDialog):
    """自定义精灵对话框（完全参考HTML设计）"""
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


class MainWindow(QMainWindow):
    # 自定义信号：当计数器数据变化时发射，让悬浮窗同步
    counter_changed = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("可丽希亚助手")
        self.resize(1280, 750)
        
        # 设置窗口图标（任务栏图标）
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "tb", "klxy.png")
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
        
        # 联动识别状态
        self.last_recognized_lkwg = None  # 上次识别到的洛克王国精灵
        self.xt_icon_detected = False  # 是否检测到xt图标
        self.xt100_detected = False  # 是否检测到xt100
        self.current_battle_lkwg = None  # 当前战斗中的洛克王国精灵名
        self._breakthrough_counted_for_current_battle = False  # 当前战斗是否已计数(防重复)
        
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
        self.content_stack.addWidget(self.select_view)   # 0
        self.content_stack.addWidget(self.detail_view)   # 1
        self.content_stack.addWidget(self.pokedex_view)  # 2
        self.content_stack.addWidget(self.pokemon_pokedex)  # 3 - 精灵图鉴
        self.content_stack.addWidget(self.egg_prediction_view)  # 4 - 孵蛋预测
        self.content_stack.addWidget(self.ball_calculator_view)  # 5 - 咕噜球计算
        self.content_stack.addWidget(self.settings_view) # 6
        self.content_stack.addWidget(self.damage_calculator_view)  # 7 - 伤害计算器
        self.content_stack.addWidget(self.type_effectiveness_view)  # 8 - 属性克制表
        body_layout.addWidget(self.content_stack, stretch=1)

        # 右侧面板
        self.right_panel = self._create_right_panel()
        body_layout.addWidget(self.right_panel)

        main_layout.addWidget(body, stretch=1)

        # 初始加载数据
        self._load_initial_data()
        self._refresh_all()
        
        # 加载设置到UI
        self.load_settings_to_ui()
        
        # 创建悬浮窗实例
        self.floating_window = FloatingWindow(self)
        self.floating_window.count_changed.connect(self.modify_count)
        
        # 应用悬浮窗大小设置
        size_key = self.settings_manager.get("floating_window_size", "medium")
        self.floating_window.set_size(size_key)
        
        # 启动自动识别联动
        self.start_auto_recognition()
    
    def enter_floating_mode(self):
        """进入抓宠模式（显示悬浮窗）"""
        active = self.manager.get_active()
        if not active:
            QMessageBox.warning(self, "警告", "请先选择一个计数器")
            return
        
        # 查找对应的自定义精灵数据，获取icon_id
        custom_pokemons = self.manager.get_custom_pokemons()
        icon_id = 0
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
    
    def closeEvent(self, event):
        """窗口关闭时保存数据"""
        try:
            # 停止自动识别
            if hasattr(self, 'recognition_timer'):
                self.recognition_timer.stop()
            if hasattr(self, 'screenshot_worker'):
                self.screenshot_worker.stop()
            if hasattr(self, 'nightmare_worker'):
                self.nightmare_worker.stop()
            
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
            
            # 主识别定时器：500ms
            self.recognition_timer = QTimer(self)
            self.recognition_timer.timeout.connect(self._request_screenshot)
            self.recognition_timer.start(500)
        
        print("✓ 自动识别联动已启动")
    
    def _request_screenshot(self):
        """请求截图和识别（非阻塞）"""
        self.screenshot_worker.capture_async()
    
    def _on_roi_status_changed(self, status):
        """接收ROI识别状态变化"""
        logger.log(status)
    
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
                            icon_id = active_counter.pokemon.get('icon', '') if hasattr(active_counter, 'pokemon') else ''
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
    
    def _on_recognition_result(self, result):
        """接收子线程的识别结果（在主线程执行）"""
        try:
            xt_detected = result['xt_detected']
            recognized_names = result['recognized_names']
            xt10_detected = result['xt10_detected']
            
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
            
            # 输出详细的状态日志
            logger.log(f"📸 识别结果: xt={xt_detected}, OCR={len(recognized_names)}, xt10={xt10_detected}")
            
            if recognized_names:
                logger.log(f"📝 OCR识别到: {', '.join(recognized_names)}")
            
            # 处理识别结果
            if recognized_names:
                for base_name in recognized_names:
                    if base_name in self.game_capture.evolution_manager.evolution_chains:
                        # 进入战斗或保持战斗状态
                        old_battle = self.current_battle_lkwg
                        self.current_battle_lkwg = base_name
                        self._update_floating_current_lkwg(base_name)
                        
                        # 同步状态到子线程
                        if hasattr(self, 'screenshot_worker'):
                            self.screenshot_worker.current_battle_lkwg = base_name
                        
                        # 同步状态到ROI worker
                        if hasattr(self, 'roi_worker') and self.roi_worker is not None:
                            self.roi_worker.set_current_battle(base_name)
                        
                        if old_battle != base_name:
                            logger.log(f"✅ 设置当前精灵: {base_name}")
                        break
            else:
                # 没有识别到名字时,检查是否需要清空状态
                if self.current_battle_lkwg:
                    # 战斗持续阶段:即使OCR失败,只要xt10还在就不清空
                    if not xt10_detected:
                        logger.log(f"⚠️ 精灵名消失且xt10未检测到,清空状态")
                        self.current_battle_lkwg = None
                        self._update_floating_current_lkwg(None)
                        
                        # 同步状态到子线程
                        if hasattr(self, 'screenshot_worker'):
                            self.screenshot_worker.current_battle_lkwg = None
                        
                        # 同步状态到ROI worker
                        if hasattr(self, 'roi_worker') and self.roi_worker is not None:
                            self.roi_worker.set_current_battle(None)
                        
                        # 重置防重复计数标记(战斗结束)
                        self._breakthrough_counted_for_current_battle = False
            
            # 输出战斗状态日志
            if self.current_battle_lkwg:
                xt_status = "✅" if xt_detected else "❌"
                xt10_status = "✅" if xt10_detected else "❌"
                log_msg = f"🎯 当前精灵: {self.current_battle_lkwg} | xt: {xt_status} | xt10: {xt10_status}"
                
                # 如果触发污染击破,添加标记
                if self.current_battle_lkwg and xt10_detected:
                    active_counter = self.manager.get_active()
                    if active_counter and active_counter.pokemon_name == self.current_battle_lkwg:
                        if recognized_names and self.current_battle_lkwg in recognized_names:
                            log_msg += " 💥 污染击破!"
                
                logger.log(log_msg)
            
            # 污染击破判定
            if self.current_battle_lkwg and xt10_detected:
                active_counter = self.manager.get_active()
                if active_counter and active_counter.pokemon_name == self.current_battle_lkwg:
                    if recognized_names and self.current_battle_lkwg in recognized_names:
                        # 防重复计数：只有当前战斗未计数时才触发
                        if not self._breakthrough_counted_for_current_battle:
                            self._trigger_lkwg_breakthrough(active_counter)
                            self._breakthrough_counted_for_current_battle = True
                            logger.log(f"✓ 污染击破: {self.current_battle_lkwg} | 计数: {active_counter.count}/{active_counter.target}")
                        else:
                            logger.log(f"⏭️ 跳过重复计数: {self.current_battle_lkwg}")
                elif self.settings_manager.get("enable_global_tracking", True):
                    if recognized_names and self.current_battle_lkwg in recognized_names:
                        self.manager.add_global_breakthrough(self.current_battle_lkwg)
                        self.manager.save_counters()
                        self._refresh_all()
                        logger.log(f"○ 全局追踪: {self.current_battle_lkwg} +1 (未创建快捷计数器)")
            
        except Exception as e:
            print(f"❌ 处理识别结果错误: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_floating_current_lkwg(self, lkwg_name):
        """更新悬浮窗当前洛克王国精灵显示"""
        if hasattr(self, 'floating_window'):
            self.floating_window.update_current_lkwg(lkwg_name)
    
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
    
    def _find_counter_by_lkwg(self, lkwg_name):
        """根据洛克王国精灵名称查找对应的计数器"""
        for counter in self.manager.counters:
            if counter.pokemon_name == lkwg_name:
                return counter
        return None
    
    def _trigger_lkwg_breakthrough(self, counter):
        """触发洛克王国精灵污染击破"""
        counter.count += 1  # 污染击破次数+1
        
        # 检查是否需要自动保存（基于时间间隔）
        auto_save_interval = self.settings_manager.get("auto_save_interval", 5)
        if self.settings_manager.get("auto_save_progress", True):
            if self.manager.should_auto_save(counter.id, auto_save_interval):
                self.manager.save_counters()
                self.manager.update_save_time(counter.id)
        
        # 检查是否达到保底，发送通知
        if counter.count >= 80:  # 默认保底80次
            if self.settings_manager.get("breakthrough_notification", True):
                self._show_breakthrough_notification(counter)
        
        # 保存数据并刷新界面
        self.counter_changed.emit()
        self._refresh_all()
        
        # 同步更新悬浮窗
        if hasattr(self, 'floating_window') and self.floating_window.isVisible():
            icon_id = counter.pokemon.get('icon', 0) if hasattr(counter, 'pokemon') else 0
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
            image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image")
            os.makedirs(image_dir, exist_ok=True)
            screenshot_path = os.path.join(image_dir, "startup_screenshot.png")
            cv2.imwrite(screenshot_path, image)
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
        image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "tb")
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

        # 主导航菜单（参考HTML设计）
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
        nav_home.clicked.connect(lambda: self.show_coming_soon("家园"))
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
        """根据精灵列表动态生成卡片"""
        # 清空网格
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.takeAt(i).widget()
            if widget:
                widget.deleteLater()

        columns = 3
        row = 0
        col = 0
        for idx, pokemon in enumerate(POKEMON_LIST):
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
            image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "tj", "images")
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
        
        # 如果icon_id未加载，尝试从ys文件夹加载
        if not image_loaded:
            image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "ys")
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
        
        # 进度填充
        progress_fill = QFrame()
        max_count = 80
        if max_count > 0:
            progress_percentage = min(100, (count / max_count) * 100)
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

    # ================= 计数器详情视图 =================
    def _create_detail_view(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
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

        mode_tag = QLabel("污染计数模式")
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
        info_layout.setSpacing(24)  # 增加图标与文字的间距

        # 大图标 - 使用ys文件夹中的图片
        self.big_icon = QLabel()  # 保存为实例变量以便后续更新
        self.big_icon.setFixedSize(100, 100)
        self.big_icon.setAlignment(Qt.AlignCenter)
        self.big_icon.setStyleSheet("background: transparent;")  # 设置透明背景
        info_layout.addWidget(self.big_icon)

        # 文字信息 - 垂直居中对齐
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

        # 计数器名称行 - 横向排列
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

        # 污染击破次数(wai)
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

        stat1_label = QLabel("污染击破次数")
        stat1_label.setStyleSheet("color: #c084fc; font-size: 11px;")
        stat1_layout.addWidget(stat1_label)

        self.detail_count = QLabel("0")
        self.detail_count.setStyleSheet("color: #f8f0ff; font-size: 28px; font-weight: bold;")
        stat1_layout.addWidget(self.detail_count)

        stats_layout.addWidget(stat1, 0, 0)

        # 保底剩余
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

        # 重置按钮和锁定复选框
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)
        
        # 重置按钮
        btn_reset = QPushButton("🔄 重置计数器")
        btn_reset.setObjectName("resetBtn")
        btn_reset.setFixedHeight(40)
        btn_reset.setStyleSheet("""
            QPushButton#resetBtn {
                background-color: rgba(239, 68, 68, 0.2);
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 8px;
                color: #ef4444;
                font-size: 14px;
                font-weight: 600;
                padding: 0 20px;
                transition: all 0.2s ease;
            }
            QPushButton#resetBtn:hover {
                background-color: rgba(239, 68, 68, 0.3);
                border: 1px solid rgba(239, 68, 68, 0.6);
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2);
            }
            QPushButton#resetBtn:pressed {
                background-color: rgba(220, 38, 38, 0.4);
                transform: translateY(0);
                box-shadow: 0 2px 6px rgba(220, 38, 38, 0.3);
            }
        """)
        btn_reset.clicked.connect(self.on_reset_counter)
        btn_layout.addWidget(btn_reset)
        
        btn_layout.addStretch()
        
        # 锁定计数区域
        lock_container = QWidget()
        lock_layout = QHBoxLayout(lock_container)
        lock_layout.setContentsMargins(0, 0, 0, 0)
        lock_layout.setSpacing(10)
        
        # 自定义复选框（放在左边）
        self.lock_checkbox = CustomCheckBox()
        self.lock_checkbox.setFixedSize(24, 24)
        self.lock_checkbox.clicked.connect(self.on_toggle_lock)
        lock_layout.addWidget(self.lock_checkbox)
        
        # 锁定文字和状态
        lock_text_container = QWidget()
        lock_text_layout = QVBoxLayout(lock_text_container)
        lock_text_layout.setContentsMargins(0, 0, 0, 0)
        lock_text_layout.setSpacing(2)
        
        # 主文字
        lock_label = QLabel("锁定计数")
        lock_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 500;")
        lock_text_layout.addWidget(lock_label)
        
        # 状态提示
        self.lock_status_label = QLabel("未锁定")
        self.lock_status_label.setStyleSheet("color: #71717a; font-size: 11px;")
        lock_text_layout.addWidget(self.lock_status_label)
        
        lock_layout.addWidget(lock_text_container, stretch=1)
        
        btn_layout.addWidget(lock_container)

        card_layout.addWidget(btn_row)

        layout.addWidget(card)
        layout.addStretch()
        return widget

    # ================= 右侧面板（参考HTML设计）=================
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
        
        # 污染击破次数输入框
        wai_group = QWidget()
        wai_layout = QVBoxLayout(wai_group)
        wai_layout.setContentsMargins(0, 0, 0, 0)
        wai_layout.setSpacing(4)
        
        wai_label = QLabel("污染击破次数")
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
        
        # 删除按钮
        btn_delete = QPushButton("删除计数器")
        btn_delete.setObjectName("settingsBtn")
        btn_delete.setFixedHeight(40)
        btn_delete.clicked.connect(self.on_delete_current_counter)
        settings_layout.addWidget(btn_delete)
        
        layout.addWidget(settings_section)
        
        # 第二部分：出闪记录
        record_section = QWidget()
        record_layout = QVBoxLayout(record_section)
        record_layout.setContentsMargins(0, 0, 0, 0)
        record_layout.setSpacing(16)
        
        record_title = QLabel("出闪记录")
        record_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 600;")
        record_layout.addWidget(record_title)
        
        btn_record = QPushButton("✅ 记录本次出闪")
        btn_record.setObjectName("customPokemonBtn")
        btn_record.setFixedHeight(40)
        btn_record.clicked.connect(self.on_record_shiny)
        record_layout.addWidget(btn_record)
        
        layout.addWidget(record_section)
        
        # 第三部分：快捷操作
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
            image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "tj", "images")
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
        
        # 如果icon_id未加载，尝试从ys文件夹加载
        if not image_loaded:
            image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "ys")
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
        
        # 进度填充
        progress_fill = QFrame()
        # 进度条显示 count/80 的进度
        max_count = 80
        if max_count > 0:
            progress_percentage = min(100, (counter.count / max_count) * 100)
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
            
            # 查找对应的自定义精灵数据，获取icon_id
            custom_pokemons = self.manager.get_custom_pokemons()
            icon_id = 0
            for cp in custom_pokemons:
                if cp['name'] == pokemon_name:
                    icon_id = cp.get('icon_id', 0)
                    break
            
            # 优先尝试使用icon_id从tj/images加载
            if icon_id > 0:
                image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "tj", "images")
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
            
            # 如果icon_id未加载，尝试从ys文件夹加载
            if not image_loaded:
                image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "ys")
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
            
            # 污染击破次数显示 count
            self.detail_count.setText(str(active.count))
            # 保底剩余显示 target - count
            remaining = active.target - active.count
            self.detail_remaining.setText(str(remaining))
            # 进度条显示 count/80 的进度
            max_val = 80
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
        self.counter_changed.emit()

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
        # 切换到污染计数模式(详情页)
        self.content_stack.setCurrentIndex(1)
        self._refresh_all()
    
    def on_counter_selected(self, row):
        """点击计数器列表项时切换页面(保留兼容)"""
        if row >= 0:
            counter_id = self.counter_list_widget.item(row).data(Qt.UserRole)
            self.manager.set_active(counter_id)
            self.manager.save_counters()  # 切换计数器后保存
            # 切换到污染计数模式(详情页)
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
        action = menu.exec(self.counter_list_widget.mapToGlobal(pos))
        if action == rename_action:
            self.rename_counter(counter_id)
        elif action == delete_action:
            self.delete_counter(counter_id)
        elif action == pin_action:
            self.toggle_pin(counter_id)

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
        self._refresh_all()

    def toggle_pin(self, counter_id):
        self.manager.toggle_pin(counter_id)
        self.manager.save_counters()  # 置顶后立即保存
        self._refresh_all()

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
            f"确定要记录【{active.pokemon_name}】出闪吗？\n当前计数{active.count}次，记录后将自动重置计数器",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 这里可以添加出闪记录逻辑
            self.manager.modify_count(-active.count)  # 重置计数
            QMessageBox.information(self, "恭喜", "出闪记录已保存！")
    
    def on_reset_counter(self):
        """重置当前计数器"""
        active = self.manager.get_active()
        if not active:
            QMessageBox.warning(self, "警告", "请先选择一个计数器")
            return
        
        reply = QMessageBox.question(
            self,
            "确认重置",
            f"确定要重置【{active.pokemon_name}】的计数器吗？\n当前计数将清零。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            active.count = 0
            self.manager.save_counters()
            self._refresh_all()
            QMessageBox.information(self, "成功", "计数器已重置！")
    
    def on_toggle_lock(self):
        """切换锁定状态"""
        active = self.manager.get_active()
        if not active:
            QMessageBox.warning(self, "警告", "请先选择一个计数器")
            return
        
        active.is_locked = not active.is_locked
        self.manager.save_counters()
        self._refresh_all()
    
    def load_settings_to_ui(self):
        """从设置管理器加载设置到UI"""
        # 通用设置
        self.minimize_tray_switch.setChecked(self.settings_manager.get("minimize_to_tray", False))
        
        # 识别设置
        self.recognition_interval_spin.setValue(self.settings_manager.get("recognition_interval", 500))
        self.recognition_confidence_spin.setValue(self.settings_manager.get("recognition_confidence", 0.8))
        
        # 计数器设置
        self.default_target_spin.setValue(self.settings_manager.get("default_target", 80))
        self.auto_save_interval_spin.setValue(self.settings_manager.get("auto_save_interval", 5))
        self.auto_save_switch.setChecked(self.settings_manager.get("auto_save_progress", True))
        self.breakthrough_notification_switch.setChecked(self.settings_manager.get("breakthrough_notification", True))
        
        # 高级设置
        self.detailed_log_switch.toggled.connect(self.on_debug_toggled)
        self.performance_monitor_switch.setChecked(self.settings_manager.get("show_performance_monitor", False))
        
        # 悬浮窗设置
        size_map = {"small": "小尺寸", "medium": "中尺寸", "large": "大尺寸"}
        current_size_key = self.settings_manager.get("floating_window_size", "medium")
        current_size_text = size_map.get(current_size_key, "中尺寸")
        if hasattr(self, 'floating_size_combo'):
            self.floating_size_combo.setCurrentText(current_size_text)
        
        # 全局追踪设置
        if hasattr(self, 'global_tracking_switch'):
            self.global_tracking_switch.setChecked(self.settings_manager.get("enable_global_tracking", True))
        
        # 坐标识别设置
        if hasattr(self, 'roi_recognition_switch'):
            self.roi_recognition_switch.setChecked(self.settings_manager.get("enable_roi_recognition", False))
    
    def save_ui_to_settings(self):
        """从UI保存设置到设置管理器"""
        # 通用设置
        self.settings_manager.set("minimize_to_tray", self.minimize_tray_switch.isChecked())
        
        # 识别设置
        self.settings_manager.set("recognition_interval", self.recognition_interval_spin.value())
        self.settings_manager.set("recognition_confidence", self.recognition_confidence_spin.value())
        
        # 计数器设置
        self.settings_manager.set("default_target", self.default_target_spin.value())
        self.settings_manager.set("auto_save_interval", self.auto_save_interval_spin.value())
        self.settings_manager.set("auto_save_progress", self.auto_save_switch.isChecked())
        self.settings_manager.set("breakthrough_notification", self.breakthrough_notification_switch.isChecked())
        
        # 高级设置（不需要保存，只用于触发调试窗口）
        self.settings_manager.set("show_performance_monitor", self.performance_monitor_switch.isChecked())
        
        # 悬浮窗设置
        size_map_reverse = {"小尺寸": "small", "中尺寸": "medium", "大尺寸": "large"}
        if hasattr(self, 'floating_size_combo'):
            size_text = self.floating_size_combo.currentText()
            size_key = size_map_reverse.get(size_text, "medium")
            self.settings_manager.set("floating_window_size", size_key)
        
        # 全局追踪设置
        if hasattr(self, 'global_tracking_switch'):
            self.settings_manager.set("enable_global_tracking", self.global_tracking_switch.isChecked())
        
        # 坐标识别设置
        if hasattr(self, 'roi_recognition_switch'):
            self.settings_manager.set("enable_roi_recognition", self.roi_recognition_switch.isChecked())
    
    def on_save_settings(self):
        """保存设置"""
        # 检查识别模式是否改变
        old_roi_mode = self.settings_manager.get("enable_roi_recognition", False)
        
        self.save_ui_to_settings()
        if self.settings_manager.save_settings():
            # 应用悬浮窗大小设置
            size_key = self.settings_manager.get("floating_window_size", "medium")
            if hasattr(self, 'floating_window') and self.floating_window.isVisible():
                self.floating_window.set_size(size_key)
            
            # 检查识别模式是否改变，如果改变则重启识别
            new_roi_mode = self.settings_manager.get("enable_roi_recognition", False)
            if old_roi_mode != new_roi_mode:
                print(f"🔄 识别模式已更改: {old_roi_mode} -> {new_roi_mode}")
                self._restart_recognition()
            
            QMessageBox.information(self, "成功", "✅ 设置已保存！\n部分设置需重启后生效。")
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
            self.load_settings_to_ui()
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
        info_text = "📊 全局污染击破统计\n\n"
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
        from core.screen_selector import ScreenSelector
        from PySide6.QtWidgets import QApplication
        
        self.hide()
        
        app = QApplication.instance()
        selector = ScreenSelector()
        
        finished = False
        
        def on_region_selected(x, y, w, h):
            nonlocal finished
            print(f"✅ 已保存框选区域: x={x}, y={y}, w={w}, h={h}")
            self.settings_manager.set("recognition_roi", {"x": x, "y": y, "width": w, "height": h})
            self.settings_manager.save_settings()
            print("✅ 框选区域已保存")
            finished = True
            
        def on_cancelled():
            nonlocal finished
            print("❌ 框选已取消")
            finished = True
        
        selector.region_selected.connect(on_region_selected)
        selector.selection_cancelled.connect(on_cancelled)
        selector.showFullScreen()
        
        # 等待框选完成
        while not finished and selector.isVisible():
            app.processEvents()
        
        self.show()
    
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
        
        # 检查是否有全局追踪数据
        global_count = self.manager.get_global_breakthrough(name)
        
        if global_count > 0:
            # 有全局追踪数据，询问是否同步
            reply = QMessageBox.question(
                self,
                "同步数据",
                f"检测到【{name}】已有 {global_count} 次污染击破记录。\n\n"
                f"是否将这些记录同步到新创建的计数器？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply != QMessageBox.Yes:
                # 选择"否"：不清零数据，不创建计数器，直接返回
                return
            
            # 选择"是"：创建计数器并同步数据
            default_target = self.settings_manager.get("default_target", 80)
            counter = self.manager.add_counter(name, f"{name}计数器", type_)
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
            counter = self.manager.add_counter(name, counter_name, type_)
            if counter:
                counter.target = default_target
        
        self.manager.save_counters()  # 添加后立即保存
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
            "国王球", "棱镜球", "织梦棱镜球"
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
        
        general_section = self._create_clean_section(
            "🎯 通用设置",
            [
                ("关闭时最小化到托盘", "点击关闭按钮时隐藏到系统托盘", self.minimize_tray_switch)
            ]
        )
        content_layout.addWidget(general_section)
        
        # 识别设置
        self.recognition_interval_spin = self._create_spin_input(100, 5000, 500, " ms")
        self.recognition_confidence_spin = self._create_spin_input(0.5, 1.0, 0.7, "", 0.05, True)
        
        ocr_section = self._create_clean_section(
            "🔍 图像识别设置",
            [
                ("识别间隔 ⚠️", "两次识别之间的时间间隔（实验性功能，修改需重启）", self.recognition_interval_spin),
                ("识别置信度 ⚠️", "匹配置信度阈值，越高越准确（实验性功能，暂未生效）", self.recognition_confidence_spin)
            ]
        )
        content_layout.addWidget(ocr_section)
        
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
        
        advanced_section = self._create_clean_section(
            "⚡ 高级设置",
            [
                ("调试输出", "打开调试窗口查看实时日志", self.detailed_log_switch),
                ("显示性能监控", "在悬浮窗显示帧率和内存占用", self.performance_monitor_switch)
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
        
        floating_section = self._create_clean_section(
            "🪟 悬浮窗设置",
            [
                ("悬浮窗大小", "选择悬浮窗的显示尺寸", self.floating_size_combo)
            ]
        )
        content_layout.addWidget(floating_section)
        
        # 全局追踪设置
        self.global_tracking_switch = ToggleSwitch()
        self.global_tracking_switch.setChecked(self.settings_manager.get("enable_global_tracking", True))
        
        tracking_section = self._create_clean_section(
            "📊 全局追踪设置",
            [
                ("启用全局污染追踪", 
                 "记录所有检测到的污染击破，即使未创建对应计数器", 
                 self.global_tracking_switch)
            ]
        )
        content_layout.addWidget(tracking_section)
        
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
                ("启用坐标识别", "启用后使用框选坐标识别方式", self.roi_recognition_switch),
                ("", "", roi_select_btn)
            ]
        )
        content_layout.addWidget(roi_section)
        
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
            data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "tj", "pokemon_data.json")
            with open(data_file, 'r', encoding='utf-8') as f:
                pokemons = json.load(f)
            
            # 加载基础形态列表（只有这些精灵可以从蛋中孵化）
            base_form_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "base_form_pokemons.txt")
            base_forms = set()
            if os.path.exists(base_form_file):
                with open(base_form_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            base_forms.add(line)
            
            # 计算匹配度并筛选
            results = []
            for pokemon in pokemons:
                name = pokemon['name']
                
                # 只保留基础形态
                if base_forms and name not in base_forms:
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
        image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "tj", "images")
        
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
            QComboBox::drop-down {
                border: none;
                width: 24px;
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
        
        prob_desc = QLabel("用于计算污染击破概率的基础值（百分比）")
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

    def modify_count(self, delta):
        self.manager.modify_count(delta)
        self._refresh_all()
    
    def on_reset_counter(self):
        """重置当前计数器"""
        active = self.manager.get_active()
        if not active:
            QMessageBox.warning(self, "警告", "请先选择一个计数器")
            return
        
        reply = QMessageBox.question(
            self,
            "确认重置",
            f"确定要重置【{active.pokemon_name}】的计数吗？\n当前计数{active.count}次将清零。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            active.count = 0
            self.manager.save_counters()  # 重置后保存
            self._refresh_all()
            QMessageBox.information(self, "成功", "计数器已重置！")
    
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
            self.floating_window.update_data(
                active.pokemon_name,
                active.type,
                active.count,
                active.target,
                active.is_locked,
                active.nightmare_count
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
        
        # 筛选器（参考HTML设计）
        filter_bar = QWidget()
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setContentsMargins(0, 8, 0, 8)
        filter_layout.setSpacing(16)
        
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
        # 清空现有网格
        for i in reversed(range(self.pokemon_grid_layout.count())):
            widget = self.pokemon_grid_layout.takeAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 获取筛选条件
        type_filter = self.filter_type_combo.currentText()
        display_filter = self.filter_display_combo.currentText()
        
        # 从数据库加载所有精灵
        from core.pokemon_data import load_pokemon_database
        database_pokemons = load_pokemon_database()
        
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
        
        # 添加"新增自定义精灵"卡片（参考HTML设计）
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
            image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "tj", "images")
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
        
        # 如果都未加载，尝试从ys文件夹加载
        if not image_loaded:
            image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "ys")
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
            image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "ys")
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
        """创建新增自定义精灵卡片（参考HTML虚线设计）"""
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
        self.manager.add_counter(name, counter_name, type_)
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
            self.content_stack.setCurrentIndex(1)
            self._refresh_all()
    
    def _load_evolution_chain(self, pokemon_name):
        """从 lkwg_names.txt 加载精灵的进化链"""
        import os
        
        names_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "lkwg_names.txt")
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
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "tj", "pokemon_data.json")
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