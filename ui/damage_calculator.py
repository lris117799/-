#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
伤害计算器 - 左右分栏布局
左侧：精灵1配置 | 右侧：精灵2配置
"""

import warnings
warnings.filterwarnings("ignore", message="iCCP: known incorrect sRGB profile")

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QScrollArea, QLineEdit,
    QFrame, QGroupBox, QCheckBox, QSpinBox, QListWidget, QListWidgetItem, QSlider
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

import json
import os
import re
import sys

SCROLL_BAR_STYLE = """
QScrollBar:vertical {
    border: none;
    background: rgba(255, 255, 255, 0.05);
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: rgba(139, 92, 246, 0.5);
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(139, 92, 246, 0.7);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""


class SpriteSearchBox(QWidget):
    """精灵搜索框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sprite_list = []
        self.selected_sprite = None
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入精灵名字...")

        self.search_input.setFixedHeight(36)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 5px;
                padding: 0 12px;
                color: white;
                font-size: 13px;
            }
        """)
        self.search_input.textChanged.connect(self.on_search)
        layout.addWidget(self.search_input)
        
        # 下拉列表（嵌入显示）
        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(250)
        self.list_widget.setMinimumHeight(300)
        self.list_widget.setMaximumHeight(600)
        self.list_widget.setVisible(False)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: rgba(22, 33, 62, 0.98);
                border: 1px solid rgba(139, 92, 246, 0.4);
                border-radius: 5px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-radius: 4px;
                margin: 2px 0;
                color: white;
                font-size: 13px;
            }
            QListWidget::item:hover {
                background-color: rgba(139, 92, 246, 0.3);
            }
            QListWidget::item:selected {
                background-color: rgba(139, 92, 246, 0.5);
            }
        """)
        self.list_widget.itemClicked.connect(self.on_item_selected)
        layout.addWidget(self.list_widget)
        
    def load_data(self):
        data_file = os.path.join(os.path.dirname(__file__), '..', "image", "tj", "lkwg_enriched_data.json")
        if os.path.exists(data_file):
            with open(data_file, 'r', encoding='utf-8') as f:
                self.sprite_list = json.load(f)
    
    def on_search(self, text):
        if not text:
            self.list_widget.setVisible(False)
            return
        
        self.list_widget.clear()
        text_lower = text.lower()
        
        for sprite in self.sprite_list:
            name = sprite.get('name', '')
            
            if text_lower in name.lower():
                item_text = name
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, sprite)
                self.list_widget.addItem(item)
        
        if self.list_widget.count() > 0:
            self.list_widget.setVisible(True)
        else:
            self.list_widget.setVisible(False)
    
    def on_item_selected(self, item):
        sprite = item.data(Qt.UserRole)
        self.selected_sprite = sprite
        self.search_input.setText(sprite.get('name', ''))
        self.list_widget.setVisible(False)
        
        if hasattr(self.parent(), 'on_sprite_selected'):
            self.parent().on_sprite_selected(sprite, self.objectName())


class RoundedBox(QFrame):
    """圆角卡片"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("roundedBox")


class DamageCalculatorWidget(QWidget):
    """伤害计算器主界面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sprite1_data = None
        self.sprite2_data = None
        self.natures = self.load_natures()
        self.effectiveness = self.load_effectiveness()
        self.setup_ui()
        
    def load_natures(self):
        """加载性格数据"""
        natures = {}
        nature_file = os.path.join(os.path.dirname(__file__), '..', "性格.txt")
        if os.path.exists(nature_file):
            with open(nature_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # 解析格式: 固执	物攻 + 10%，魔攻 - 10%
                    match = re.match(r'(\S+)\s+([\u4e00-\u9fa5]+)\s*\+\s*(\d+)%，([\u4e00-\u9fa5]+)\s*-\s*(\d+)%', line)
                    if match:
                        name = match.group(1)
                        boost_stat = match.group(2)
                        boost_val = int(match.group(3))
                        reduce_stat = match.group(4)
                        reduce_val = int(match.group(5))
                        natures[name] = {
                            'boost': (boost_stat, boost_val),
                            'reduce': (reduce_stat, reduce_val)
                        }
        return natures
    
    def load_effectiveness(self):
        """加载属性克制数据"""
        effectiveness = {}
        type_file = os.path.join(os.path.dirname(__file__), '..', "克制.txt")
        if not os.path.exists(type_file):
            return effectiveness
        
        all_types = ['草', '火', '水', '光', '地', '冰', '龙', '电', '毒', '虫', '武', '翼', '萌', '幽', '恶', '普', '幻', '机械']
        
        # 统一使用带“系”后缀的key
        for attr in all_types:
            attr_with_suffix = attr + '系'
            effectiveness[attr_with_suffix] = {
                'attack_2x': [],
                'attack_0.5x': [],
                'defense_2x': [],
                'defense_0.5x': []
            }
        
        current_attr = None
        section = None
        
        with open(type_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # 检测属性标题
                attr_match = re.match(r'Step\d+：(\w+)系', line)
                if attr_match:
                    current_attr = attr_match.group(1) + '系'  # 统一带“系”后缀
                    continue
                
                # 检测章节
                if '作为攻击方' in line:
                    section = 'attack'
                    continue
                elif '作为被攻击方' in line:
                    section = 'defense'
                    continue
                
                # 解析克制关系
                if current_attr and section:
                    # 0.5倍伤害
                    half_match = re.search(r'对(.+?)系造成0\.5倍伤害', line)
                    if half_match and section == 'attack':
                        text = half_match.group(1)
                        attrs = [a.strip() + '系' for a in text.split('/')]
                        effectiveness[current_attr]['attack_0.5x'] = attrs
                        continue
                    
                    half_match = re.search(r'受到(.+?)系的0\.5倍伤害', line)
                    if half_match and section == 'defense':
                        text = half_match.group(1)
                        attrs = [a.strip() + '系' for a in text.split('/')]
                        effectiveness[current_attr]['defense_0.5x'] = attrs
                        continue
                    
                    # 2倍伤害
                    double_match = re.search(r'对(.+?)系造成2倍伤害', line)
                    if double_match and section == 'attack':
                        text = double_match.group(1)
                        attrs = [a.strip() + '系' for a in text.split('/')]
                        effectiveness[current_attr]['attack_2x'] = attrs
                        continue
                    
                    double_match = re.search(r'受到(.+?)系的2倍伤害', line)
                    if double_match and section == 'defense':
                        text = double_match.group(1)
                        attrs = [a.strip() + '系' for a in text.split('/')]
                        effectiveness[current_attr]['defense_2x'] = attrs
                        continue
        
        return effectiveness
    
    def setup_ui(self):
        # 主滚动区域
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        main_scroll.setStyleSheet(SCROLL_BAR_STYLE)
        
        # 内容容器
        content = QWidget()
        main_layout = QHBoxLayout(content)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # 左侧：精灵1
        sprite1_panel = self.create_sprite_panel("精灵1", "sprite1")
        sprite1_panel.setMaximumWidth(450)
        main_layout.addWidget(sprite1_panel, 1)
        
        # 右侧：精灵2
        sprite2_panel = self.create_sprite_panel("精灵2", "sprite2")
        sprite2_panel.setMaximumWidth(450)
        main_layout.addWidget(sprite2_panel, 1)
        
        main_scroll.setWidget(content)
        
        # 主布局
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(main_scroll)
    
    def create_sprite_panel(self, title, side):
        """创建精灵配置面板"""
        panel = RoundedBox()
        panel.setStyleSheet("""
            QFrame#roundedBox {
                background-color: rgba(15, 15, 35, 0.9);
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 10px;
                padding: 16px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #a78bfa; font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 1. 精灵选择
        layout.addWidget(QLabel("精灵"))
        search_box = SpriteSearchBox()
        search_box.setObjectName(side)
        # 设置父组件引用以触发回调
        search_box.setParent(panel)
        panel.on_sprite_selected = lambda sprite, s=side: self.on_sprite_selected(sprite, s)
        setattr(self, f"{side}_search_box", search_box)
        layout.addWidget(search_box)
        
        # 2. 属性显示（双属性，只读）
        layout.addWidget(QLabel("属性"))
        attr_layout = QHBoxLayout()
        attr_layout.setSpacing(6)
        
        attr1_label = QLabel("-")
        attr1_label.setStyleSheet("""
            QLabel {
                background-color: rgba(139, 92, 246, 0.15);
                color: #a78bfa;
                padding: 8px 12px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        attr_layout.addWidget(attr1_label, 1)
        
        attr2_label = QLabel("-")
        attr2_label.setStyleSheet("""
            QLabel {
                background-color: rgba(139, 92, 246, 0.15);
                color: #a78bfa;
                padding: 8px 12px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        attr_layout.addWidget(attr2_label, 1)
        
        setattr(self, f"{side}_attr1", attr1_label)
        setattr(self, f"{side}_attr2", attr2_label)
        layout.addLayout(attr_layout)
        
        # 3. 等级拖动条
        level_layout = QVBoxLayout()
        level_layout.setSpacing(4)
        
        level_header = QHBoxLayout()
        level_label = QLabel("等级")
        level_label.setStyleSheet("color: rgba(255, 255, 255, 0.85); font-size: 12px;")
        level_header.addWidget(level_label)
        level_header.addStretch()
        
        level_value_label = QLabel("60")
        level_value_label.setStyleSheet("color: #a78bfa; font-size: 14px; font-weight: bold;")
        level_value_label.setFixedWidth(30)
        level_header.addWidget(level_value_label)
        
        level_layout.addLayout(level_header)
        
        level_slider = QSlider(Qt.Horizontal)
        level_slider.setRange(1, 60)
        level_slider.setValue(60)
        level_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid rgba(139, 92, 246, 0.3);
                height: 6px;
                background-color: rgba(22, 33, 62, 0.8);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background-color: #8b5cf6;
                border: 2px solid #a78bfa;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background-color: #a78bfa;
            }
        """)
        level_slider.valueChanged.connect(lambda value: self.on_level_changed(value, side, level_value_label))
        level_layout.addWidget(level_slider)
        
        setattr(self, f"{side}_level_slider", level_slider)
        setattr(self, f"{side}_level_value", 60)
        setattr(self, f"{side}_level_value_label", level_value_label)
        
        level_container = QWidget()
        level_container.setLayout(level_layout)
        layout.addWidget(level_container)
        
        # 3.5. 当前属性显示
        stats_display_group = QGroupBox("当前属性")
        stats_display_group.setStyleSheet(self.group_style())
        stats_display_layout = QGridLayout(stats_display_group)
        stats_display_layout.setSpacing(6)
        
        stat_labels = {}
        for i, stat_name in enumerate(["生命", "物攻", "物防", "魔攻", "魔防", "速度"]):
            label = QLabel(f"{stat_name}: -")
            label.setStyleSheet("color: rgba(255, 255, 255, 0.85); font-size: 12px;")
            stats_display_layout.addWidget(label, i // 2, i % 2 * 2)
            stat_labels[stat_name] = label
        
        setattr(self, f"{side}_stat_labels", stat_labels)
        layout.addWidget(stats_display_group)
        
        # 4. 星级评定（属性下面，满资质上面）
        star_layout = QHBoxLayout()
        star_layout.setSpacing(8)
        star_layout.addStretch()
        
        self.star_buttons = []
        for i in range(5):
            star_btn = QPushButton()
            star_btn.setFixedSize(32, 32)
            star_btn.setCursor(Qt.PointingHandCursor)
            star_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                }
            """)
            # 默认灰色
            pixmap = QPixmap('D:/game/lkwg/image/sc/xx.png')
            if not pixmap.isNull():
                scaled = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                star_btn.setIcon(scaled)
                star_btn.setIconSize(scaled.size())
            star_btn.setProperty('star_index', i)
            star_btn.clicked.connect(lambda checked, idx=i, s=side: self.on_star_clicked(idx, s))
            star_layout.addWidget(star_btn)
            self.star_buttons.append(star_btn)
        
        star_layout.addStretch()
        setattr(self, f"{side}_stars", self.star_buttons)
        setattr(self, f"{side}_star_count", 0)  # 当前星数
        
        star_container = QWidget()
        star_container.setLayout(star_layout)
        layout.addWidget(star_container)
        
        # 5. 满资质勾选
        full_iv_check = QCheckBox("满资质")
        full_iv_check.setStyleSheet("""
            QCheckBox {
                color: rgba(255, 255, 255, 0.85);
                font-size: 12px;
            }
        """)
        full_iv_check.stateChanged.connect(lambda: self.on_full_iv_changed(side))
        setattr(self, f"{side}_full_iv", full_iv_check)
        layout.addWidget(full_iv_check)
        
        # 5. 能力值配置
        stats_group = QGroupBox("能力值配置")
        stats_group.setStyleSheet(self.group_style())
        stats_layout = QGridLayout(stats_group)
        stats_layout.setSpacing(6)
        
        stat_names = ["生命", "物攻", "物防", "魔攻", "魔防", "速度"]
        iv_inputs = {}
        race_inputs = {}
        iv_checks = {}  # 个体值复选框
        
        for i, stat_name in enumerate(stat_names):
            row = i
            
            # 种族值输入
            race_spin = QSpinBox()
            race_spin.setRange(0, 9999)
            race_spin.setValue(0)
            race_spin.setFixedHeight(28)
            race_spin.setFixedWidth(80)
            race_spin.setStyleSheet(self.input_style())
            stats_layout.addWidget(QLabel(stat_name), row, 0)
            stats_layout.addWidget(race_spin, row, 1)
            race_inputs[stat_name] = race_spin
            
            # 个体值复选框（放在种族值和个体值输入之间）
            iv_check = QCheckBox("")
            iv_check.setStyleSheet("""
                QCheckBox {
                    color: rgba(255, 255, 255, 0.85);
                    font-size: 11px;
                    spacing: 4px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 3px;
                    background-color: rgba(30, 30, 60, 0.9);
                    border: 2px solid rgba(139, 92, 246, 0.5);
                }
                QCheckBox::indicator:hover {
                    border: 2px solid #a78bfa;
                    background-color: rgba(139, 92, 246, 0.1);
                }
                QCheckBox::indicator:checked {
                    background-color: #8b5cf6;
                    border: 2px solid #a78bfa;
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgNEw0LjUgNy41TDExIDEiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMi41IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz48L3N2Zz4=);
                }
                QCheckBox::indicator:disabled {
                    opacity: 0.15;
                    background-color: rgba(20, 20, 40, 0.5);
                    border: 2px solid rgba(100, 100, 100, 0.3);
                }
            """)
            stats_layout.addWidget(iv_check, row, 2)
            iv_checks[stat_name] = iv_check
            
            # 个体值输入（默认禁用，值为0）
            iv_spin = QSpinBox()
            iv_spin.setRange(0, 60)
            iv_spin.setValue(0)
            iv_spin.setFixedHeight(28)
            iv_spin.setFixedWidth(80)
            iv_spin.setStyleSheet(self.input_style())
            iv_spin.setEnabled(False)
            stats_layout.addWidget(iv_spin, row, 3)
            iv_inputs[stat_name] = iv_spin
            
            # 监听个体值变化，实时更新属性
            iv_spin.valueChanged.connect(lambda value, s=side: self.calculate_stats(s))
            
            # 复选框状态变化时启用/禁用个体值输入
            def on_check_changed(checked, spin=iv_spin, stat=stat_name):
                if checked:
                    # 勾选后，根据当前星级设置初始值
                    star_count = getattr(self, f"{side}_star_count", 0)
                    iv_ranges = [
                        (7, 10),   # 0星
                        (14, 20),  # 1星
                        (21, 30),  # 2星
                        (28, 40),  # 3星
                        (35, 50),  # 4星
                        (42, 60)   # 5星
                    ]
                    iv_min, iv_max = iv_ranges[star_count]
                    spin.setEnabled(True)
                    spin.setValue(iv_min)
                else:
                    # 取消勾选后，先重置范围再归0，避免范围限制导致无法归0
                    spin.setRange(0, 60)
                    spin.setValue(0)
                    spin.setEnabled(False)
                # 无论勾选还是取消，都重新检查限制
                self.limit_iv_count(side)
                # 重新计算属性
                self.calculate_stats(side)
            
            iv_check.stateChanged.connect(on_check_changed)
        
        setattr(self, f"{side}_race_inputs", race_inputs)
        setattr(self, f"{side}_iv_inputs", iv_inputs)
        setattr(self, f"{side}_iv_checks", iv_checks)
        
        layout.addWidget(stats_group)
        
        layout.addWidget(QLabel("性格"))
        nature_combo = QComboBox()
        nature_combo.addItem("无性格加成")
        for nature_name in self.natures.keys():
            nature_info = self.natures[nature_name]
            boost_stat, boost_val = nature_info['boost']
            reduce_stat, reduce_val = nature_info['reduce']
            display_text = f"{nature_name} ({boost_stat}+{boost_val}%, {reduce_stat}-{reduce_val}%)"
            nature_combo.addItem(display_text, nature_name)
        nature_combo.setFixedHeight(32)
        nature_combo.setStyleSheet(self.combo_style())
        setattr(self, f"{side}_nature", nature_combo)
        # 监听性格变化，实时更新属性
        nature_combo.currentIndexChanged.connect(lambda: self.calculate_stats(side))
        layout.addWidget(nature_combo)
        skills_group = QGroupBox("技能")
        skills_group.setStyleSheet(self.group_style())
        skills_layout = QVBoxLayout(skills_group)
        skills_layout.setSpacing(6)
        
        skill_widgets = []
        for i in range(4):
            skill_row = QWidget()
            skill_row_layout = QHBoxLayout(skill_row)
            skill_row_layout.setContentsMargins(0, 0, 0, 0)
            skill_row_layout.setSpacing(4)
            
            # 技能名称
            skill_combo = QComboBox()
            skill_combo.addItem("选择技能")
            skill_combo.setFixedHeight(28)
            skill_combo.setStyleSheet(self.combo_style())
            skill_row_layout.addWidget(skill_combo, 2)
            
            # 属性
            attr_label = QLabel("-")
            attr_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 12px; padding: 4px 8px;")
            attr_label.setFixedWidth(55)
            skill_row_layout.addWidget(attr_label)
            
            # 威力
            power_label = QLabel("-")
            power_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 12px; padding: 4px 8px;")
            power_label.setFixedWidth(45)
            skill_row_layout.addWidget(power_label)
            
            # 伤害类型
            type_label = QLabel("-")
            type_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 12px; padding: 4px 8px;")
            type_label.setFixedWidth(60)
            skill_row_layout.addWidget(type_label)
            
            # 显示威力
            display_power_label = QLabel("-")
            display_power_label.setStyleSheet("color: #a78bfa; font-size: 12px; font-weight: bold; padding: 4px 8px;")
            display_power_label.setFixedWidth(60)
            skill_row_layout.addWidget(display_power_label)
            
            skill_row_layout.addStretch()
            skills_layout.addWidget(skill_row)
            
            skill_widgets.append({
                'combo': skill_combo,
                'attr': attr_label,
                'power': power_label,
                'type': type_label,
                'display_power': display_power_label
            })
        
        setattr(self, f"{side}_skills", skill_widgets)
        layout.addWidget(skills_group)
        
        # 10. 伤害计算按钮
        calc_button = QPushButton("伤害计算")
        calc_button.setFixedHeight(36)
        calc_button.setCursor(Qt.PointingHandCursor)
        calc_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(139, 92, 246, 0.8);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(139, 92, 246, 1.0);
            }
            QPushButton:pressed {
                background-color: rgba(109, 72, 226, 0.9);
            }
        """)
        calc_button.clicked.connect(lambda checked=False, s=side: self.on_calculate_damage(s))
        layout.addWidget(calc_button)
        
        # 重置按钮
        reset_button = QPushButton("重置")
        reset_button.setFixedHeight(32)
        reset_button.setCursor(Qt.PointingHandCursor)
        reset_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(100, 100, 100, 0.6);
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(100, 100, 100, 0.8);
            }
            QPushButton:pressed {
                background-color: rgba(80, 80, 80, 0.7);
            }
        """)
        reset_button.clicked.connect(lambda checked=False, s=side: self.on_reset_side(s))
        layout.addWidget(reset_button)
        
        # 11. 血条显示区域
        hp_bar_container = QWidget()
        hp_bar_container.setVisible(False)  # 默认隐藏
        hp_bar_layout = QVBoxLayout(hp_bar_container)
        hp_bar_layout.setSpacing(4)
        
        # 伤害数值标签
        damage_label = QLabel("")
        damage_label.setAlignment(Qt.AlignCenter)
        damage_label.setStyleSheet("color: #fbbf24; font-size: 14px; font-weight: bold;")
        hp_bar_layout.addWidget(damage_label)
        
        # 血条容器
        hp_bar_widget = QWidget()
        hp_bar_widget.setFixedHeight(24)
        hp_bar_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 60, 0.9);
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
            }
        """)
        hp_bar_inner_layout = QHBoxLayout(hp_bar_widget)
        hp_bar_inner_layout.setContentsMargins(2, 2, 2, 2)
        hp_bar_inner_layout.setSpacing(0)
        
        # 绿色血条
        hp_bar_fill = QWidget()
        hp_bar_fill.setStyleSheet("""
            QWidget {
                background-color: #4ade80;
                border-radius: 2px;
            }
        """)
        hp_bar_inner_layout.addWidget(hp_bar_fill)
        hp_bar_inner_layout.addStretch()
        
        hp_bar_layout.addWidget(hp_bar_widget)
        
        # 血量文本
        hp_text_label = QLabel("")
        hp_text_label.setAlignment(Qt.AlignCenter)
        hp_text_label.setStyleSheet("color: white; font-size: 12px;")
        hp_bar_layout.addWidget(hp_text_label)
        
        setattr(self, f"{side}_hp_bar_container", hp_bar_container)
        setattr(self, f"{side}_hp_bar_fill", hp_bar_fill)
        setattr(self, f"{side}_damage_label", damage_label)
        setattr(self, f"{side}_hp_text_label", hp_text_label)
        
        layout.addWidget(hp_bar_container)
        
        # 9. 加成配置
        bonus_group = QGroupBox("战斗加成")
        bonus_group.setStyleSheet(self.group_style())
        bonus_layout = QGridLayout(bonus_group)
        bonus_layout.setSpacing(6)
        
        bonus_inputs = {}
        bonus_stats = ["物攻", "魔攻", "物防", "魔防"]
        for i, stat in enumerate(bonus_stats):
            bonus_layout.addWidget(QLabel(stat), i, 0)
            bonus_spin = QSpinBox()
            bonus_spin.setRange(0, 1000)
            bonus_spin.setValue(0)
            bonus_spin.setSuffix("%")
            bonus_spin.setFixedHeight(28)
            bonus_spin.setFixedWidth(70)
            bonus_spin.setStyleSheet(self.input_style())
            bonus_layout.addWidget(bonus_spin, i, 1)
            bonus_inputs[stat] = bonus_spin
        
        setattr(self, f"{side}_bonus", bonus_inputs)
        layout.addWidget(bonus_group)
        
        layout.addStretch()
        return panel
    
    def on_sprite_selected(self, sprite, side):
        """精灵选择回调"""
        if side == "sprite1":
            self.sprite1_data = sprite
        elif side == "sprite2":
            self.sprite2_data = sprite
            
        # 更新属性显示（双属性）
        attr = sprite.get('attribute', '未知')
        attr1_label = getattr(self, f"{side}_attr1")
        attr2_label = getattr(self, f"{side}_attr2")
            
        # 解析属性，支持双属性如“火/水”
        attrs = attr.split('/')
        attr1_label.setText(attrs[0] if attrs else '-')
        attr2_label.setText(attrs[1] if len(attrs) > 1 else '-')
            
        # 更新种族值输入框
        stats = sprite.get('stats', {})
        race_inputs = getattr(self, f"{side}_race_inputs")
        race_inputs["生命"].setValue(stats.get('hp', 0))
        race_inputs["物攻"].setValue(stats.get('attack', 0))
        race_inputs["物防"].setValue(stats.get('defense', 0))
        race_inputs["魔攻"].setValue(stats.get('magic_attack', 0))
        race_inputs["魔防"].setValue(stats.get('magic_defense', 0))
        race_inputs["速度"].setValue(stats.get('speed', 0))
            
        # 更新技能列表
        self.update_skills(sprite, side)
            
        # 重新计算属性
        self.calculate_stats(side)
    
    def update_skills(self, sprite, side):
        """更新技能列表"""
        skills = sprite.get('skills', {})
        normal_skills = skills.get('normal_skills', [])
        bloodline_skills = skills.get('bloodline_skills', [])
        stone_skills = skills.get('stone_skills', [])
        
        all_skills = normal_skills + bloodline_skills + stone_skills
        
        skill_widgets = getattr(self, f"{side}_skills")
        for widget_dict in skill_widgets:
            combo = widget_dict['combo']
            attr_label = widget_dict['attr']
            power_label = widget_dict['power']
            type_label = widget_dict['type']
            display_power_label = widget_dict['display_power']
            
            combo.clear()
            combo.addItem("选择技能")
            
            for skill in all_skills:
                skill_name = skill.get('name', '')
                combo.addItem(skill_name, skill)
            
            # 连接信号，选择技能后显示属性、威力和类型
            combo.currentIndexChanged.connect(
                lambda idx, c=combo, a=attr_label, p=power_label, t=type_label, dp=display_power_label, s=side: self.on_skill_selected(c, a, p, t, dp, s)
            )
    
    def on_skill_selected(self, combo, attr_label, power_label, type_label, display_power_label, side):
        """技能选择回调"""
        if combo.currentIndex() <= 0:
            attr_label.setText("-")
            power_label.setText("-")
            type_label.setText("-")
            display_power_label.setText("-")
            return
        
        skill = combo.currentData()
        if skill:
            attr = skill.get('attribute', '-')
            base_power = skill.get('power', 0)
            damage_type = skill.get('type', '-')
            attr_label.setText(attr)
            power_label.setText(str(base_power))
            type_label.setText(damage_type)
            
            # 计算显示威力
            display_power = self.calculate_display_power(skill, side)
            display_power_label.setText(str(display_power))
            
            # 根据属性克制设置颜色
            type_multiplier = self.get_type_multiplier_for_color(skill, side)
            if type_multiplier > 1.0:
                # 克制：绿色
                display_power_label.setStyleSheet("color: #4ade80; font-size: 12px; font-weight: bold; padding: 4px 8px;")
            elif type_multiplier < 1.0:
                # 抵抗：红色
                display_power_label.setStyleSheet("color: #f87171; font-size: 12px; font-weight: bold; padding: 4px 8px;")
            else:
                # 正常：紫色
                display_power_label.setStyleSheet("color: #a78bfa; font-size: 12px; font-weight: bold; padding: 4px 8px;")
    
    def calculate_display_power(self, skill, side):
        """计算显示威力 = 基础威力 x 本系加成(1.25) x 属性克制 x 增减益"""
        sprite = self.sprite1_data if side == "sprite1" else self.sprite2_data
        if not sprite:
            return skill.get('power', 0)
        
        base_power = skill.get('power', 0)
        if not base_power or base_power == '-':
            return 0
        
        try:
            base_power = int(base_power)
        except:
            return 0
        
        # 1. 本系加成：技能属性与精灵属性匹配时x1.25
        same_type_bonus = 1.0
        skill_attr = skill.get('attribute', '')
        sprite_attr = sprite.get('attribute', '')
        # 支持双属性，如“火/水”
        # 统一格式：都去掉“系”后缀进行比较
        skill_attr_clean = skill_attr.replace('系', '')
        sprite_attrs = [a.strip().replace('系', '') for a in sprite_attr.split('/')]
        if skill_attr_clean in sprite_attrs:
            same_type_bonus = 1.25
        
        # 2. 属性克制：需要知道目标精灵的属性
        # 这里假设是sprite1对sprite2，或者sprite2对sprite1
        target_side = "sprite2" if side == "sprite1" else "sprite1"
        target_sprite = self.sprite2_data if target_side == "sprite2" else self.sprite1_data
        
        type_multiplier = 1.0
        if target_sprite:
            type_multiplier = self.get_type_multiplier(skill_attr, target_sprite)
        
        # 3. 增减益：从战斗加成中获取
        bonus_inputs = getattr(self, f"{side}_bonus", {})
        bonus_multiplier = 1.0
        
        # 根据技能伤害类型获取对应的加成
        damage_type = skill.get('type', '')
        if damage_type == '物攻' or damage_type == '物理':
            bonus_pct = bonus_inputs.get('物攻', None)
            if bonus_pct:
                bonus_multiplier = 1 + bonus_pct.value() / 100
        elif damage_type == '魔攻' or damage_type == '特殊':
            bonus_pct = bonus_inputs.get('魔攻', None)
            if bonus_pct:
                bonus_multiplier = 1 + bonus_pct.value() / 100
        
        # 计算最终显示威力（向下取整）
        import math
        display_power = base_power * same_type_bonus * type_multiplier * bonus_multiplier
        return math.floor(display_power)
    
    def get_type_multiplier_for_color(self, skill, side):
        """获取属性克制倍数用于颜色判断"""
        sprite = self.sprite1_data if side == "sprite1" else self.sprite2_data
        if not sprite:
            return 1.0
        
        skill_attr = skill.get('attribute', '')
        
        # 属性克制：需要知道目标精灵的属性
        target_side = "sprite2" if side == "sprite1" else "sprite1"
        target_sprite = self.sprite2_data if target_side == "sprite2" else self.sprite1_data
        
        if target_sprite:
            return self.get_type_multiplier(skill_attr, target_sprite)
        
        return 1.0
    
    def on_calculate_damage(self, side):
        """伤害计算按钮点击事件"""
        # 获取攻击方和目标方
        attacker_side = side
        defender_side = "sprite2" if side == "sprite1" else "sprite1"
        
        attacker_sprite = self.sprite1_data if attacker_side == "sprite1" else self.sprite2_data
        defender_sprite = self.sprite2_data if defender_side == "sprite2" else self.sprite1_data
        
        if not attacker_sprite or not defender_sprite:
            return
        
        # 获取第一个选择的技能
        skill_widgets = getattr(self, f"{attacker_side}_skills")
        selected_skill = None
        for widget_dict in skill_widgets:
            combo = widget_dict['combo']
            if combo.currentIndex() > 0:
                selected_skill = combo.currentData()
                break
        
        if not selected_skill:
            return
        
        # 计算显示威力
        display_power = self.calculate_display_power(selected_skill, attacker_side)
        
        # 获取攻击能力值和防御能力值
        attacker_stat_labels = getattr(self, f"{attacker_side}_stat_labels", {})
        defender_stat_labels = getattr(self, f"{defender_side}_stat_labels", {})
        
        damage_type = selected_skill.get('type', '-')
        if damage_type == '物攻':
            attack_stat = int(attacker_stat_labels.get('物攻', QLabel('0')).text().split(': ')[1])
            defense_stat = int(defender_stat_labels.get('物防', QLabel('0')).text().split(': ')[1])
        elif damage_type == '魔攻':
            attack_stat = int(attacker_stat_labels.get('魔攻', QLabel('0')).text().split(': ')[1])
            defense_stat = int(defender_stat_labels.get('魔防', QLabel('0')).text().split(': ')[1])
        else:
            return
        
        # 连击数（默认为1）
        hit_count = 1
        
        # 获取战斗加成
        attacker_bonus_inputs = getattr(self, f"{attacker_side}_bonus", {})
        defender_bonus_inputs = getattr(self, f"{defender_side}_bonus", {})
        
        if damage_type == '物攻':
            attacker_bonus_pct = attacker_bonus_inputs.get('物攻', None)
            defender_bonus_pct = defender_bonus_inputs.get('物防', None)
        else:  # 魔攻
            attacker_bonus_pct = attacker_bonus_inputs.get('魔攻', None)
            defender_bonus_pct = defender_bonus_inputs.get('魔防', None)
        
        # 检查是否有战斗加成
        has_bonus = False
        if attacker_bonus_pct and attacker_bonus_pct.value() != 0:
            has_bonus = True
        if defender_bonus_pct and defender_bonus_pct.value() != 0:
            has_bonus = True
        
        # 计算战斗伤害
        import math
        if has_bonus:
            # 使用带战斗加成的公式
            attacker_bonus_val = attacker_bonus_pct.value() / 100 if attacker_bonus_pct else 0
            defender_bonus_val = defender_bonus_pct.value() / 100 if defender_bonus_pct else 0
            
            actual_attack = attack_stat * (1 + attacker_bonus_val)
            actual_defense = defense_stat * (1 + defender_bonus_val)
            
            final_damage = math.ceil(0.9 * display_power * (actual_attack / actual_defense) * hit_count)
        else:
            # 使用原公式（默认）
            final_damage = math.ceil(0.9 * display_power * (attack_stat / defense_stat) * hit_count)
        
        # 获取目标最大HP
        max_hp = int(defender_stat_labels.get('生命', QLabel('0')).text().split(': ')[1])
        
        # 更新血条显示
        self.update_hp_bar(defender_side, final_damage, max_hp)
    
    def update_hp_bar(self, side, damage, max_hp):
        """更新血条显示"""
        hp_bar_container = getattr(self, f"{side}_hp_bar_container")
        hp_bar_fill = getattr(self, f"{side}_hp_bar_fill")
        damage_label = getattr(self, f"{side}_damage_label")
        hp_text_label = getattr(self, f"{side}_hp_text_label")
        
        # 显示血条容器
        hp_bar_container.setVisible(True)
        
        # 计算剩余血量
        remaining_hp = max(0, max_hp - damage)
        hp_percentage = (remaining_hp / max_hp * 100) if max_hp > 0 else 0
        
        # 更新伤害数值标签
        damage_label.setText(f"这一击造成 {damage} 点伤害")
        
        # 更新血条宽度
        total_width = hp_bar_fill.parentWidget().width() - 4  # 减去边距
        fill_width = int(total_width * (remaining_hp / max_hp)) if max_hp > 0 else 0
        hp_bar_fill.setFixedWidth(max(fill_width, 0))
        
        # 更新血量文本
        hp_text_label.setText(f"{remaining_hp} / {max_hp} ({hp_percentage:.1f}%)")
    
    def on_reset_side(self, side):
        """重置单侧配置"""
        # 清空精灵数据
        if side == "sprite1":
            self.sprite1_data = None
        else:
            self.sprite2_data = None
        
        # 清空精灵搜索框
        search_box = getattr(self, f"{side}_search_box", None)
        if search_box and hasattr(search_box, 'search_input'):
            search_box.search_input.clear()
        
        # 重置属性显示为"-"
        attr1_label = getattr(self, f"{side}_attr1")
        attr2_label = getattr(self, f"{side}_attr2")
        attr1_label.setText("-")
        attr2_label.setText("-")
        
        # 重置等级为60
        level_slider = getattr(self, f"{side}_level_slider")
        level_value_label = getattr(self, f"{side}_level_value_label")
        level_slider.setValue(60)
        level_value_label.setText("60")
        
        # 重置星级为0
        setattr(self, f"{side}_star_count", 0)
        self.update_star_display(side)
        
        # 重置满资质
        full_iv_check = getattr(self, f"{side}_full_iv")
        full_iv_check.setChecked(False)
        
        # 重置个体值
        iv_inputs = getattr(self, f"{side}_iv_inputs")
        iv_checks = getattr(self, f"{side}_iv_checks")
        for stat in iv_checks.keys():
            iv_checks[stat].setChecked(False)
            iv_checks[stat].setEnabled(True)
            iv_inputs[stat].setValue(0)
            iv_inputs[stat].setEnabled(False)
            iv_inputs[stat].setRange(0, 60)
        
        # 重置性格
        nature_combo = getattr(self, f"{side}_nature")
        nature_combo.setCurrentIndex(0)
        self.update_nature_display(side)
        
        # 重置技能
        skill_widgets = getattr(self, f"{side}_skills")
        for widget_dict in skill_widgets:
            combo = widget_dict['combo']
            combo.setCurrentIndex(0)
            widget_dict['attr'].setText("-")
            widget_dict['power'].setText("-")
            widget_dict['type'].setText("-")
            widget_dict['display_power'].setText("-")
            widget_dict['display_power'].setStyleSheet("color: #a78bfa; font-size: 12px; font-weight: bold; padding: 4px 8px;")
        
        # 重置战斗加成
        bonus_inputs = getattr(self, f"{side}_bonus")
        for spin in bonus_inputs.values():
            spin.setValue(0)
        
        # 重置种族值为0
        race_inputs = getattr(self, f"{side}_race_inputs")
        for spin in race_inputs.values():
            spin.setValue(0)
        
        # 重置当前属性显示为"-"
        stat_labels = getattr(self, f"{side}_stat_labels", {})
        for label in stat_labels.values():
            label.setText(f"{label.text().split(':')[0]}: -")
        
        # 隐藏血条
        hp_bar_container = getattr(self, f"{side}_hp_bar_container")
        hp_bar_container.setVisible(False)
    
    def get_type_multiplier(self, skill_attr, target_sprite):
        """计算属性克制倍数"""
        if not skill_attr or not target_sprite:
            return 1.0
        
        # 统一格式：去掉“系”后缀
        skill_attr_clean = skill_attr.replace('系', '')
        
        # 获取目标精灵的属性
        target_attr = target_sprite.get('attribute', '')
        target_attrs = [a.strip().replace('系', '') for a in target_attr.split('/')]
        
        weak_count = 0
        resist_count = 0
        
        for t_attr in target_attrs:
            # 克制数据中带“系”后缀，所以比较时要加上
            t_attr_with_suffix = t_attr + '系'
            skill_attr_with_suffix = skill_attr_clean + '系'
            # 检查技能属性是否克制目标属性
            if skill_attr_with_suffix in self.effectiveness.get(t_attr_with_suffix, {}).get('defense_2x', []):
                weak_count += 1
            elif skill_attr_with_suffix in self.effectiveness.get(t_attr_with_suffix, {}).get('defense_0.5x', []):
                resist_count += 1
        
        # 根据规则计算最终倍率
        if weak_count == 0 and resist_count == 0:
            return 1.0
        elif weak_count == 1 and resist_count == 0:
            return 2.0
        elif weak_count == 2 and resist_count == 0:
            return 3.0  # 双属性都被克制，3倍而非4倍
        elif weak_count == 0 and resist_count == 1:
            return 0.5
        elif weak_count == 0 and resist_count == 2:
            return 0.5  # 双属性都抵抗，仍为0.5倍
        elif weak_count == 1 and resist_count == 1:
            return 1.0  # 一克一抗，抵消
        
        return 1.0
    
    def on_star_clicked(self, star_index, side):
        """星星点击事件"""
        current_count = getattr(self, f"{side}_star_count")
        star_buttons = getattr(self, f"{side}_stars")
        
        # 点击的星是当前星数，则取消这颗及之后的星
        if star_index < current_count:
            new_count = star_index
        else:
            # 否则点亮到这颗
            new_count = star_index + 1
        
        setattr(self, f"{side}_star_count", new_count)
        self.update_star_display(side)
        
        # 更新个体值范围限制
        self.update_iv_range(side, new_count)
        
        # 更新性格显示
        self.update_nature_display(side)
        
        # 重新计算属性（星级影响努力值和个体值）
        self.calculate_stats(side)
    
    def update_star_display(self, side):
        """更新星星显示"""
        star_count = getattr(self, f"{side}_star_count")
        star_buttons = getattr(self, f"{side}_stars")
        
        for i, btn in enumerate(star_buttons):
            if i < star_count:
                # 点亮的黄色星星
                pixmap = QPixmap('D:/game/lkwg/image/sc/hx.png')
            else:
                # 灰色的星星
                pixmap = QPixmap('D:/game/lkwg/image/sc/xx.png')
            
            if not pixmap.isNull():
                scaled = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                btn.setIcon(scaled)
                btn.setIconSize(scaled.size())
    
    def update_iv_range(self, side, star_count):
        """根据星级更新个体值范围"""
        iv_inputs = getattr(self, f"{side}_iv_inputs")
        iv_checks = getattr(self, f"{side}_iv_checks")
        
        # 个体值范围：0星7-10, 1星14-20, 2星21-30, 3星28-40, 4星35-50, 5星42-60
        iv_ranges = [
            (7, 10),   # 0星
            (14, 20),  # 1星
            (21, 30),  # 2星
            (28, 40),  # 3星
            (35, 50),  # 4星
            (42, 60)   # 5星
        ]
        iv_min, iv_max = iv_ranges[star_count]
        
        # 更新所有个体值输入框的范围和当前值
        for stat_name, iv_spin in iv_inputs.items():
            if iv_checks[stat_name].isChecked():
                # 勾选的：更新范围并调整值到新范围的最小值
                iv_spin.setRange(iv_min, iv_max)
                iv_spin.setValue(iv_min)
            else:
                # 未勾选的：确保值为0，范围设为0-60（防止无法修改）
                iv_spin.setValue(0)
                iv_spin.setRange(0, 60)
    
    def on_level_changed(self, value, side, level_value_label):
        """等级变化回调"""
        setattr(self, f"{side}_level_value", value)
        level_value_label.setText(str(value))
        
        # 重新计算属性
        self.calculate_stats(side)
    
    def calculate_stats(self, side):
        """根据公式计算精灵属性"""
        sprite = self.sprite1_data if side == "sprite1" else self.sprite2_data
        if not sprite:
            return
        
        level = getattr(self, f"{side}_level_value")
        star_count = getattr(self, f"{side}_star_count")
        race_inputs = getattr(self, f"{side}_race_inputs")
        iv_inputs = getattr(self, f"{side}_iv_inputs")
        iv_checks = getattr(self, f"{side}_iv_checks")
        nature_combo = getattr(self, f"{side}_nature")
        full_iv_check = getattr(self, f"{side}_full_iv")
        
        # 获取种族值
        base_hp = race_inputs["生命"].value()
        base_atk = race_inputs["物攻"].value()
        base_def = race_inputs["物防"].value()
        base_matk = race_inputs["魔攻"].value()
        base_mdef = race_inputs["魔防"].value()
        base_spd = race_inputs["速度"].value()
        
        # 计算努力值（星级影响）
        # 1星: 生命+20, 其他+10; 5星: 生命+100, 其他+50
        effort_hp = star_count * 20
        effort_other = star_count * 10
        
        # 计算个体值范围（星级影响）
        # 0星: 7-10, 1星: 14-20, 2星: 21-30, 3星: 28-40, 4星: 35-50, 5星: 42-60
        iv_ranges = [
            (7, 10),   # 0星
            (14, 20),  # 1星
            (21, 30),  # 2星
            (28, 40),  # 3星
            (35, 50),  # 4星
            (42, 60)   # 5星
        ]
        iv_min, iv_max = iv_ranges[star_count]
        
        # 获取当前个体值（如果勾选了则使用输入值，否则用0）
        def get_iv(stat_name):
            if iv_checks[stat_name].isChecked():
                return iv_inputs[stat_name].value()
            else:
                return 0
        
        iv_hp = get_iv("生命")
        iv_atk = get_iv("物攻")
        iv_def = get_iv("物防")
        iv_matk = get_iv("魔攻")
        iv_mdef = get_iv("魔防")
        iv_spd = get_iv("速度")
        
        # 满资质时，已勾选的个体值强制为60
        if full_iv_check.isChecked():
            if iv_checks["生命"].isChecked():
                iv_hp = 60
            if iv_checks["物攻"].isChecked():
                iv_atk = 60
            if iv_checks["物防"].isChecked():
                iv_def = 60
            if iv_checks["魔攻"].isChecked():
                iv_matk = 60
            if iv_checks["魔防"].isChecked():
                iv_mdef = 60
            if iv_checks["速度"].isChecked():
                iv_spd = 60
        
        # 计算有效种族值 = 基础种族值 + 个体值 / 2
        effective_hp = base_hp + iv_hp / 2
        effective_atk = base_atk + iv_atk / 2
        effective_def = base_def + iv_def / 2
        effective_matk = base_matk + iv_matk / 2
        effective_mdef = base_mdef + iv_mdef / 2
        effective_spd = base_spd + iv_spd / 2
        
        # 获取性格加成
        nature_index = nature_combo.currentIndex()
        nature_boost_stat = None
        nature_reduce_stat = None
        nature_boost_val = 0
        nature_reduce_val = 0
        
        if nature_index > 0:
            nature_name = nature_combo.itemData(nature_index)
            if nature_name and nature_name in self.natures:
                nature_info = self.natures[nature_name]
                nature_boost_stat, base_boost_val = nature_info['boost']
                nature_reduce_stat, nature_reduce_val = nature_info['reduce']
                
                # 根据星级计算加成：0星+10%, 1星+12%, 2星+14%, 3星+16%, 4星+18%, 5星+20%
                nature_boost_val = base_boost_val + star_count * 2
        
        # 计算性格系数
        def get_nature_multiplier(stat_name):
            if nature_boost_stat == stat_name:
                return 1 + nature_boost_val / 100
            elif nature_reduce_stat == stat_name:
                return 1 - nature_reduce_val / 100
            return 1.0
        
        # 计算生命值
        # 生命值 = [ 有效生命种族 × (2 × 等级 + 50) ÷ 100 ]四舍五入 + 等级 + 10
        hp_base = round(effective_hp * (2 * level + 50) / 100) + level + 10
        hp_nature_mult = get_nature_multiplier("生命")
        hp_final = round(hp_base * hp_nature_mult) + effort_hp
        
        # 计算非生命属性
        # 属性值 = [ [有效种族 × (等级 + 50) ÷ 100]四舍五入 + 10 ] × 性格系数，结果四舍五入，最后 + 努力值
        def calc_non_hp_stat(effective_race, effort, stat_name):
            base = round(effective_race * (level + 50) / 100) + 10
            nature_mult = get_nature_multiplier(stat_name)
            return round(base * nature_mult) + effort
        
        atk_final = calc_non_hp_stat(effective_atk, effort_other, "物攻")
        def_final = calc_non_hp_stat(effective_def, effort_other, "物防")
        matk_final = calc_non_hp_stat(effective_matk, effort_other, "魔攻")
        mdef_final = calc_non_hp_stat(effective_mdef, effort_other, "魔防")
        spd_final = calc_non_hp_stat(effective_spd, effort_other, "速度")
        
        # 更新UI显示
        stat_labels = getattr(self, f"{side}_stat_labels", {})
        if stat_labels:
            stat_labels["生命"].setText(f"生命: {hp_final}")
            stat_labels["物攻"].setText(f"物攻: {atk_final}")
            stat_labels["物防"].setText(f"物防: {def_final}")
            stat_labels["魔攻"].setText(f"魔攻: {matk_final}")
            stat_labels["魔防"].setText(f"魔防: {mdef_final}")
            stat_labels["速度"].setText(f"速度: {spd_final}")
    
    def limit_iv_count(self, side):
        """限制个体值最多只能勾选3项"""
        iv_checks = getattr(self, f"{side}_iv_checks")
        full_iv_check = getattr(self, f"{side}_full_iv")
        
        # 满资质时不限制
        if full_iv_check.isChecked():
            return
        
        # 统计当前勾选的数量
        checked_count = sum(1 for check in iv_checks.values() if check.isChecked())
        
        # 更新所有复选框的启用状态
        for stat, check in iv_checks.items():
            if check.isChecked():
                # 已勾选的始终可以取消
                check.setEnabled(True)
            else:
                # 未勾选的：如果已选3个则禁用，否则启用
                check.setEnabled(checked_count < 3)
    
    def on_full_iv_changed(self, side):
        """满资质状态变化"""
        full_iv_check = getattr(self, f"{side}_full_iv")
        iv_inputs = getattr(self, f"{side}_iv_inputs")
        iv_checks = getattr(self, f"{side}_iv_checks")
        nature_combo = getattr(self, f"{side}_nature")
        
        is_full = full_iv_check.isChecked()
        
        if is_full:
            # 满资质：点亮5颗星
            setattr(self, f"{side}_star_count", 5)
            self.update_star_display(side)
            
            # 只将已勾选的项设为60
            for stat in iv_checks.keys():
                if iv_checks[stat].isChecked():
                    iv_inputs[stat].setValue(60)
                    iv_inputs[stat].setEnabled(False)
                else:
                    # 未勾选的禁用复选框和输入框
                    iv_checks[stat].setEnabled(False)
                    iv_inputs[stat].setEnabled(False)
            
            # 更新性格显示为20%-10%
            self.update_nature_display(side, is_full=True)
        else:
            # 非满资质：重置星星为0
            setattr(self, f"{side}_star_count", 0)
            self.update_star_display(side)
            
            # 恢复所有复选框，重置个体值
            for stat in iv_checks.keys():
                iv_checks[stat].setEnabled(True)
            for stat, spin in iv_inputs.items():
                if iv_checks[stat].isChecked():
                    spin.setValue(7)  # 勾选的重置为7
                    spin.setEnabled(True)
                else:
                    spin.setValue(0)  # 未勾选的重置为0
                    spin.setEnabled(False)
            
            # 重新检查限制（修复满资质切换Bug）
            self.limit_iv_count(side)
            
            # 恢复性格显示为10%-10%
            self.update_nature_display(side, is_full=False)
        
        # 重新计算属性
        self.calculate_stats(side)
    
    def update_nature_display(self, side, is_full=False):
        """更新性格显示"""
        nature_combo = getattr(self, f"{side}_nature")
        star_count = getattr(self, f"{side}_star_count")
        current_index = nature_combo.currentIndex()
        
        # 清空并重新填充
        nature_combo.clear()
        nature_combo.addItem("无性格加成")
        
        for nature_name in self.natures.keys():
            nature_info = self.natures[nature_name]
            boost_stat, base_boost_val = nature_info['boost']
            reduce_stat, reduce_val = nature_info['reduce']
            
            # 根据星级计算加成：0星+10%, 1星+12%, 2星+14%, 3星+16%, 4星+18%, 5星+20%
            actual_boost_val = base_boost_val + star_count * 2
            
            display_text = f"{nature_name} ({boost_stat}+{actual_boost_val}%, {reduce_stat}-{reduce_val}%)"
            nature_combo.addItem(display_text, nature_name)
        
        # 恢复之前的选择
        if current_index > 0:
            nature_combo.setCurrentIndex(current_index)
    
    def input_style(self):
        return """
            QSpinBox {
                background-color: rgba(22, 33, 62, 0.8);
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 4px;
                padding: 0 8px;
                color: white;
                font-size: 11px;
                outline: none;
            }
            QSpinBox:focus {
                outline: none;
                border: 1px solid rgba(139, 92, 246, 0.5);
            }
            QSpinBox:disabled {
                background-color: rgba(20, 20, 40, 0.5);
                border: 1px solid rgba(80, 80, 80, 0.3);
                color: rgba(150, 150, 150, 0.5);
            }
        """
    
    def combo_style(self):
        return """
            QComboBox {
                background-color: rgba(22, 33, 62, 0.8);
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 4px;
                padding: 0 8px;
                color: white;
                font-size: 11px;
                outline: none;
            }
            QComboBox:focus {
                outline: none;
                border: 1px solid rgba(139, 92, 246, 0.5);
            }
            QComboBox::drop-down {
                border: none;
                width: 16px;
            }
            QComboBox QAbstractItemView {
                background-color: #16213e;
                color: white;
                selection-background-color: rgba(139, 92, 246, 0.4);
            }
        """
    
    def group_style(self):
        return """
            QGroupBox {
                color: #a78bfa;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 8px;
            }
        """
