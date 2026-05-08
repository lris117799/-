#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
精灵图鉴视图 - Material Design风格
"""

import warnings
warnings.filterwarnings("ignore", message="iCCP: known incorrect sRGB profile")

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QScrollArea, QFrame, QComboBox, QPushButton
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPixmap, QFont, QPainter, QPainterPath, QPen, QColor, QBrush
import json
import os

# 统一的滚动条样式
SCROLL_BAR_STYLE = """
    QScrollArea {
        border: none;
        background-color: transparent;
        padding-right: 10px;
    }
    QScrollBar:vertical {
        background: rgba(255, 255, 255, 0.05);
        width: 8px;
        border-radius: 4px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: rgba(167, 139, 250, 0.5);
        border-radius: 4px;
        min-height: 30px;
    }
    QScrollBar::handle:vertical:hover {
        background: rgba(167, 139, 250, 0.7);
    }
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {
        background: none;
    }
"""


class RoundedFrame(QFrame):
    """自定义圆角Frame，禁用默认边框绘制"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setAttribute(Qt.WA_StyledBackground, True)


class PokemonCard(QFrame):
    """精灵卡片 - Material Design风格"""
    
    def __init__(self, pokemon, parent=None):
        super().__init__(parent)
        self.pokemon = pokemon
        self.setFixedSize(180, 240)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setup_ui()
        
    def mousePressEvent(self, event):
        """点击卡片进入详情页"""
        if event.button() == Qt.LeftButton:
            # 向上查找PokedexWidget
            parent = self.parent()
            while parent:
                if hasattr(parent, 'show_detail'):
                    parent.show_detail(self.pokemon)
                    return
                parent = parent.parent()
        
        # 不调用父类方法，避免产生pressed状态
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 图片区域（上半部分）
        image_frame = RoundedFrame()
        image_frame.setFixedHeight(160)
        image_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 0px;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }
        """)
        image_layout = QVBoxLayout(image_frame)
        image_layout.setContentsMargins(20, 20, 20, 20)
        image_layout.setAlignment(Qt.AlignCenter)
        
        pid = self.pokemon.get('id', 0)
        image_label = QLabel()
        image_label.setFixedSize(120, 120)
        image_label.setAlignment(Qt.AlignCenter)
        
        image_path = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "images", f"{pid:03d}.png")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(110, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image_label.setPixmap(scaled)
        
        image_layout.addWidget(image_label)
        main_layout.addWidget(image_frame)
        
        # 信息区域（下半部分）
        info_frame = RoundedFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 60, 0.95);
                border: 0px;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 10, 12, 12)
        info_layout.setSpacing(6)
        
        # 编号和名称（固定宽度）
        header_layout = QHBoxLayout()
        
        id_label = QLabel(f"#{pid:03d}")
        id_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        id_label.setFixedWidth(40)
        header_layout.addWidget(id_label)
        
        name = self.pokemon.get('name', '未知')
        name_label = QLabel(name)
        name_label.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
        name_label.setFixedWidth(100)
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        info_layout.addLayout(header_layout)
        
        # 属性标签
        attr = self.pokemon.get('attribute', '')
        if attr:
            if '/' in attr:
                parts = attr.split('/')
                attr_layout = QHBoxLayout()
                attr_layout.setSpacing(4)
                
                for part in parts:
                    tag = QLabel(part)
                    tag.setStyleSheet("""
                        background-color: rgba(139, 92, 246, 0.2);
                        color: #a78bfa;
                        padding: 2px 8px;
                        border-radius: 4px;
                        font-size: 10px;
                    """)
                    tag.setAlignment(Qt.AlignCenter)
                    attr_layout.addWidget(tag)
                
                attr_layout.addStretch()
                info_layout.addLayout(attr_layout)
            else:
                attr_tag = QLabel(attr)
                attr_tag.setStyleSheet("""
                    background-color: rgba(139, 92, 246, 0.2);
                    color: #a78bfa;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 10px;
                """)
                attr_tag.setAlignment(Qt.AlignCenter)
                info_layout.addWidget(attr_tag, alignment=Qt.AlignLeft)
        
        main_layout.addWidget(info_frame)
        
        # 卡片样式
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
            QFrame:hover {
                background-color: rgba(139, 92, 246, 0.1);
            }
        """)


class PokemonDetailWidget(QWidget):
    """精灵详情页"""
    
    def __init__(self, pokemon, parent=None):
        super().__init__(parent)
        self.pokemon = pokemon
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # 返回按钮
        back_btn = QPushButton("← 返回")
        back_btn.setFixedWidth(80)
        back_btn.setFixedHeight(36)
        back_btn.setAttribute(Qt.WA_MacShowFocusRect, False)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(139, 92, 246, 0.2);
                color: #a78bfa;
                border: 1px solid rgba(139, 92, 246, 0.5);
                border-radius: 8px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(139, 92, 246, 0.3);
            }
            QPushButton:focus {
                background-color: rgba(139, 92, 246, 0.3);
                border: 1px solid rgba(139, 92, 246, 0.7);
            }
        """)
        back_btn.clicked.connect(self.go_back)
        main_layout.addWidget(back_btn, alignment=Qt.AlignLeft)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(SCROLL_BAR_STYLE)
        
        # 主要内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(25)
        content_layout.setContentsMargins(0, 0, 40, 0)  # 右侧增加40px边距,让主滚动条远离内容
        
        # 顶部：头像 + 基本信息
        top_layout = QHBoxLayout()
        top_layout.setSpacing(30)
        
        # 左侧：头像
        image_frame = RoundedFrame()
        image_frame.setFixedSize(200, 200)
        image_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 2px solid rgba(167, 139, 250, 0.3);
                border-radius: 100px;
            }
        """)
        image_layout = QVBoxLayout(image_frame)
        image_layout.setContentsMargins(20, 20, 20, 20)
        image_layout.setAlignment(Qt.AlignCenter)
        
        pid = self.pokemon.get('id', 0)
        image_label = QLabel()
        image_label.setFixedSize(160, 160)
        image_label.setAlignment(Qt.AlignCenter)
        
        image_path = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "images", f"{pid:03d}.png")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image_label.setPixmap(scaled)
        
        image_layout.addWidget(image_label)
        top_layout.addWidget(image_frame, alignment=Qt.AlignCenter)
        
        # 右侧：基本信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(15)
        
        # 编号和名称
        id_label = QLabel(f"NO.{pid:03d}")
        id_label.setStyleSheet("color: #6b7280; font-size: 14px;")
        info_layout.addWidget(id_label)
        
        name = self.pokemon.get('name', '未知')
        name_label = QLabel(name)
        name_label.setStyleSheet("color: white; font-size: 28px; font-weight: bold;")
        info_layout.addWidget(name_label)
        
        # 属性
        attr = self.pokemon.get('attribute', '')
        if attr:
            attr_container = QWidget()
            attr_box_layout = QHBoxLayout(attr_container)
            attr_box_layout.setContentsMargins(0, 0, 0, 0)
            attr_box_layout.setSpacing(8)
            
            if '/' in attr:
                parts = attr.split('/')
                for part in parts:
                    tag = QLabel(part)
                    tag.setStyleSheet("""
                        QLabel {
                            background-color: rgba(139, 92, 246, 0.3);
                            color: #a78bfa;
                            padding: 6px 16px;
                            border: none;
                            border-radius: 8px;
                            font-size: 14px;
                            font-weight: bold;
                        }
                    """)
                    tag.setAlignment(Qt.AlignCenter)
                    attr_box_layout.addWidget(tag)
            else:
                tag = QLabel(attr)
                tag.setStyleSheet("""
                    QLabel {
                        background-color: rgba(139, 92, 246, 0.3);
                        color: #a78bfa;
                        padding: 6px 16px;
                        border: none;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
                tag.setAlignment(Qt.AlignCenter)
                attr_box_layout.addWidget(tag)
            
            attr_box_layout.addStretch()
            info_layout.addWidget(attr_container)
        
        # 身高体重
        height = self.pokemon.get('height', '')
        weight = self.pokemon.get('weight', '')
        if height or weight:
            hw_layout = QHBoxLayout()
            hw_layout.setSpacing(20)
            
            if height:
                h_label = QLabel(f"身高: {height}m")
                h_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 13px;")
                hw_layout.addWidget(h_label)
            
            if weight:
                w_label = QLabel(f"体重: {weight}kg")
                w_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 13px;")
                hw_layout.addWidget(w_label)
            
            hw_layout.addStretch()
            info_layout.addLayout(hw_layout)
        
        info_layout.addStretch()
        top_layout.addLayout(info_layout, stretch=1)
        
        content_layout.addLayout(top_layout)
        
        # 种族值区域
        stats = self.pokemon.get('stats', {})
        if stats:
            stats_title = QLabel("种族值")
            stats_title.setStyleSheet("color: #a78bfa; font-size: 18px; font-weight: bold;")
            content_layout.addWidget(stats_title)
            
            stats_widget = QWidget()
            stats_main_layout = QHBoxLayout(stats_widget)
            stats_main_layout.setSpacing(30)
            
            # 左侧：6项具体种族值
            stats_list_layout = QVBoxLayout()
            stats_list_layout.setSpacing(10)
            
            stat_items = [
                ('HP', stats.get('hp', 0)),
                ('攻击', stats.get('attack', 0)),
                ('防御', stats.get('defense', 0)),
                ('特攻', stats.get('magic_attack', 0)),
                ('特防', stats.get('magic_defense', 0)),
                ('速度', stats.get('speed', 0)),
            ]
            
            for label, value in stat_items:
                item_layout = QHBoxLayout()
                
                name_lbl = QLabel(f"{label}:")
                name_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 13px;")
                name_lbl.setFixedWidth(50)
                item_layout.addWidget(name_lbl)
                
                # 进度条背景
                bar_bg = RoundedFrame()
                bar_bg.setFixedHeight(20)
                bar_bg.setStyleSheet("""
                    QFrame {
                        background-color: rgba(255, 255, 255, 0.1);
                        border: 0px;
                        border-radius: 10px;
                    }
                """)
                bar_layout = QHBoxLayout(bar_bg)
                bar_layout.setContentsMargins(2, 2, 2, 2)
                
                # 进度条填充
                bar_fill = RoundedFrame()
                percent = min(value / 200, 1.0)
                bar_fill.setMinimumWidth(int(200 * percent))
                bar_fill.setStyleSheet("""
                    QFrame {
                        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #8b5cf6, stop:1 #a78bfa);
                        border: 0px;
                        border-radius: 8px;
                    }
                """)
                bar_layout.addWidget(bar_fill)
                bar_layout.addStretch()
                
                item_layout.addWidget(bar_bg, stretch=1)
                
                # 数值
                value_lbl = QLabel(str(value))
                value_lbl.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
                value_lbl.setFixedWidth(40)
                value_lbl.setAlignment(Qt.AlignRight)
                item_layout.addWidget(value_lbl)
                
                stats_list_layout.addLayout(item_layout)
            
            stats_main_layout.addLayout(stats_list_layout, stretch=1)
            
            # 右侧：总种族值
            total_frame = RoundedFrame()
            total_frame.setFixedSize(150, 150)
            total_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(139, 92, 246, 0.15);
                    border: 2px solid rgba(139, 92, 246, 0.4);
                    border-radius: 75px;
                }
            """)
            total_layout = QVBoxLayout(total_frame)
            total_layout.setAlignment(Qt.AlignCenter)
            total_layout.setSpacing(5)
            
            total_label = QLabel("总和")
            total_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 14px;")
            total_label.setAlignment(Qt.AlignCenter)
            total_layout.addWidget(total_label)
            
            total_value = QLabel(str(stats.get('total', 0)))
            total_value.setStyleSheet("color: #fbbf24; font-size: 36px; font-weight: bold;")
            total_value.setAlignment(Qt.AlignCenter)
            total_layout.addWidget(total_value)
            
            stats_main_layout.addWidget(total_frame, alignment=Qt.AlignCenter)
            
            content_layout.addWidget(stats_widget)
        
        # 进化链区域
        evolution = self.pokemon.get('evolution', [])
        current_name = self.pokemon.get('name', '')
        
        if evolution and evolution != ['无法进化']:
            evo_title = QLabel("进化链")
            evo_title.setStyleSheet("color: #a78bfa; font-size: 18px; font-weight: bold;")
            content_layout.addWidget(evo_title)
            
            # 构建完整进化链，确保包含当前精灵并正确排序
            full_evolution = []
            
            if current_name not in evolution:
                # 当前精灵不在进化链中，需要推断位置
                # 尝试通过ID判断：ID小的在前，大的在后
                all_evo_names = evolution + [current_name]
                
                # 从数据文件中获取所有相关精灵的ID
                try:
                    data_file = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "pokemon_data.json")
                    if os.path.exists(data_file):
                        with open(data_file, 'r', encoding='utf-8') as f:
                            all_pokemons = json.load(f)
                            
                            # 创建名称到ID的映射
                            name_to_id = {p['name']: p['id'] for p in all_pokemons}
                            
                            # 按ID排序
                            full_evolution = sorted(all_evo_names, key=lambda x: name_to_id.get(x, 999))
                    else:
                        # 如果找不到数据文件，简单追加到末尾
                        full_evolution = evolution + [current_name]
                except:
                    full_evolution = evolution + [current_name]
            else:
                # 当前精灵已在进化链中，直接使用
                full_evolution = evolution.copy()
            
            # 检测是否有带括号的形态描述
            has_form = any('(' in name or '（' in name for name in full_evolution)
            
            evo_container = QWidget()
            evo_layout = QHBoxLayout(evo_container)
            evo_layout.setSpacing(15)
            
            for i, evo_name in enumerate(full_evolution):
                # 解析名称和形态
                if '(' in evo_name:
                    base_name = evo_name.split('(')[0].strip()
                    form_desc = '(' + evo_name.split('(')[1]
                elif '（' in evo_name:
                    base_name = evo_name.split('（')[0].strip()
                    form_desc = '（' + evo_name.split('（')[1]
                else:
                    base_name = evo_name
                    form_desc = None
                
                # 创建精灵卡片容器
                card_container = QWidget()
                card_layout = QVBoxLayout(card_container)
                card_layout.setContentsMargins(0, 0, 0, 0)
                card_layout.setSpacing(2)
                
                # 高亮显示当前精灵
                if evo_name == current_name:
                    name_label = QLabel(f"● {base_name}")
                    name_label.setStyleSheet("""
                        QLabel {
                            background-color: rgba(251, 191, 36, 0.3);
                            color: #fbbf24;
                            padding: 8px 16px;
                            border-radius: 8px;
                            font-size: 14px;
                            font-weight: bold;
                            border: 2px solid rgba(251, 191, 36, 0.6);
                        }
                    """)
                    
                    if form_desc:
                        form_label = QLabel(form_desc)
                        form_label.setStyleSheet("""
                            QLabel {
                                color: rgba(251, 191, 36, 0.8);
                                padding: 2px 16px 8px 16px;
                                font-size: 12px;
                            }
                        """)
                        card_layout.addWidget(name_label)
                        card_layout.addWidget(form_label)
                    else:
                        card_layout.addWidget(name_label)
                else:
                    name_label = QLabel(base_name)
                    name_label.setStyleSheet("""
                        QLabel {
                            background-color: rgba(139, 92, 246, 0.2);
                            color: #c4b5fd;
                            padding: 8px 16px;
                            border-radius: 8px;
                            font-size: 13px;
                        }
                    """)
                    
                    if form_desc:
                        form_label = QLabel(form_desc)
                        form_label.setStyleSheet("""
                            QLabel {
                                color: rgba(196, 181, 253, 0.7);
                                padding: 2px 16px 8px 16px;
                                font-size: 12px;
                            }
                        """)
                        card_layout.addWidget(name_label)
                        card_layout.addWidget(form_label)
                    else:
                        card_layout.addWidget(name_label)
                
                evo_layout.addWidget(card_container)
                
                # 添加箭头（最后一个不加）
                if i < len(full_evolution) - 1:
                    arrow_label = QLabel("→")
                    arrow_label.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 16px;")
                    evo_layout.addWidget(arrow_label)
            
            evo_layout.addStretch()
            content_layout.addWidget(evo_container)
        elif evolution == ['无法进化']:
            evo_title = QLabel("进化链")
            evo_title.setStyleSheet("color: #a78bfa; font-size: 18px; font-weight: bold;")
            content_layout.addWidget(evo_title)
            
            no_evo_label = QLabel("无法进化")
            no_evo_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 13px;")
            content_layout.addWidget(no_evo_label)
        
        # 特性区域
        abilities = self.pokemon.get('abilities', [])
        if abilities:
            ability_title = QLabel("特性")
            ability_title.setStyleSheet("color: #a78bfa; font-size: 18px; font-weight: bold;")
            content_layout.addWidget(ability_title)
            
            for ability in abilities:
                ability_box = RoundedFrame()
                ability_box.setStyleSheet("""
                    QFrame {
                        background-color: rgba(139, 92, 246, 0.08);
                        border: 1px solid rgba(139, 92, 246, 0.25);
                        border-radius: 6px;
                        padding: 12px;
                    }
                """)
                ability_layout = QVBoxLayout(ability_box)
                ability_layout.setContentsMargins(12, 12, 12, 12)
                ability_layout.setSpacing(10)
                
                # 支持新旧两种格式：字典{name, effect}或字符串
                if isinstance(ability, dict):
                    ability_name = ability.get('name', '')
                    ability_effect = ability.get('effect', '')
                else:
                    # 旧格式：字符串，直接使用
                    ability_name = ''
                    ability_effect = str(ability)
                
                # 显示特性名称（如果有）
                if ability_name:
                    name_label = QLabel(f"特性：{ability_name}")
                    name_label.setStyleSheet("""
                        color: #fbbf24;
                        font-size: 14px;
                        font-weight: bold;
                    """)
                    ability_layout.addWidget(name_label)
                
                # 显示效果描述
                if ability_effect:
                    desc_label = QLabel(ability_effect)
                    desc_label.setStyleSheet("""
                        color: rgba(255, 255, 255, 0.85);
                        font-size: 13px;
                    """)
                    desc_label.setWordWrap(True)
                    ability_layout.addWidget(desc_label)
                
                content_layout.addWidget(ability_box)
        
        # 技能区域
        skills = self.pokemon.get('skills', {})
        normal_skills = skills.get('normal_skills', [])
        bloodline_skills = skills.get('bloodline_skills', [])
        stone_skills = skills.get('stone_skills', [])
        
        # 技能Tab切换
        skill_tab_layout = QHBoxLayout()
        skill_tab_layout.setSpacing(8)
        
        normal_tab_btn = QPushButton(f"精灵技能 ({len(normal_skills)})")
        bloodline_tab_btn = QPushButton(f"血脉技能 ({len(bloodline_skills)})")
        stone_tab_btn = QPushButton(f"可学技能石 ({len(stone_skills)})")
        
        tab_style = """
            QPushButton {
                background-color: rgba(139, 92, 246, 0.15);
                color: #a78bfa;
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(139, 92, 246, 0.25);
            }
            QPushButton:checked {
                background-color: rgba(139, 92, 246, 0.4);
                border: 2px solid rgba(139, 92, 246, 0.6);
            }
        """
        
        normal_tab_btn.setStyleSheet(tab_style)
        bloodline_tab_btn.setStyleSheet(tab_style)
        stone_tab_btn.setStyleSheet(tab_style)
        
        normal_tab_btn.setCheckable(True)
        bloodline_tab_btn.setCheckable(True)
        stone_tab_btn.setCheckable(True)
        
        skill_tab_layout.addWidget(normal_tab_btn)
        skill_tab_layout.addWidget(bloodline_tab_btn)
        skill_tab_layout.addWidget(stone_tab_btn)
        skill_tab_layout.addStretch()
        
        content_layout.addLayout(skill_tab_layout)
        
        # 创建三个技能显示区域
        skill_stack = QWidget()
        skill_stack_layout = QVBoxLayout(skill_stack)
        skill_stack_layout.setContentsMargins(0, 0, 0, 0)
        
        # 精灵技能区域
        normal_scroll = QScrollArea()
        normal_scroll.setWidgetResizable(True)
        normal_scroll.setMaximumHeight(400)
        normal_scroll.setStyleSheet(SCROLL_BAR_STYLE)
        
        normal_skills_widget = QWidget()
        normal_skills_layout = QGridLayout(normal_skills_widget)
        normal_skills_layout.setSpacing(8)
        normal_skills_layout.setContentsMargins(10, 10, 10, 10)
        
        # 两列布局
        for i, skill in enumerate(normal_skills):
            skill_box = self.create_skill_box(skill)
            row = i // 2
            col = i % 2
            normal_skills_layout.addWidget(skill_box, row, col)
        
        normal_skills_layout.setColumnStretch(0, 1)
        normal_skills_layout.setColumnStretch(1, 1)
        normal_scroll.setWidget(normal_skills_widget)
        
        # 血脉技能区域
        bloodline_scroll = QScrollArea()
        bloodline_scroll.setWidgetResizable(True)
        bloodline_scroll.setMaximumHeight(400)
        bloodline_scroll.setStyleSheet(SCROLL_BAR_STYLE)
        
        bloodline_skills_widget = QWidget()
        bloodline_skills_layout = QGridLayout(bloodline_skills_widget)
        bloodline_skills_layout.setSpacing(8)
        bloodline_skills_layout.setContentsMargins(10, 10, 10, 10)
        
        for i, skill in enumerate(bloodline_skills):
            skill_box = self.create_skill_box(skill, is_bloodline=True)
            row = i // 2
            col = i % 2
            bloodline_skills_layout.addWidget(skill_box, row, col)
        
        bloodline_skills_layout.setColumnStretch(0, 1)
        bloodline_skills_layout.setColumnStretch(1, 1)
        bloodline_scroll.setWidget(bloodline_skills_widget)
        
        # 可学技能石区域
        stone_scroll = QScrollArea()
        stone_scroll.setWidgetResizable(True)
        stone_scroll.setMaximumHeight(400)
        stone_scroll.setStyleSheet(SCROLL_BAR_STYLE)
        
        stone_skills_widget = QWidget()
        stone_skills_layout = QGridLayout(stone_skills_widget)
        stone_skills_layout.setSpacing(8)
        stone_skills_layout.setContentsMargins(10, 10, 10, 10)
        
        for i, skill in enumerate(stone_skills):
            skill_box = self.create_skill_box(skill, is_stone=True)
            row = i // 2
            col = i % 2
            stone_skills_layout.addWidget(skill_box, row, col)
        
        stone_skills_layout.setColumnStretch(0, 1)
        stone_skills_layout.setColumnStretch(1, 1)
        stone_scroll.setWidget(stone_skills_widget)
        
        # 添加到stack
        skill_stack_layout.addWidget(normal_scroll)
        skill_stack_layout.addWidget(bloodline_scroll)
        skill_stack_layout.addWidget(stone_scroll)
        
        # 默认只显示第一个有内容的Tab
        if normal_skills:
            normal_scroll.setVisible(True)
            bloodline_scroll.setVisible(False)
            stone_scroll.setVisible(False)
            normal_tab_btn.setChecked(True)
        elif bloodline_skills:
            normal_scroll.setVisible(False)
            bloodline_scroll.setVisible(True)
            stone_scroll.setVisible(False)
            bloodline_tab_btn.setChecked(True)
        else:
            normal_scroll.setVisible(False)
            bloodline_scroll.setVisible(False)
            stone_scroll.setVisible(True)
            stone_tab_btn.setChecked(True)
        
        # Tab切换逻辑
        def switch_to_normal():
            normal_scroll.setVisible(True)
            bloodline_scroll.setVisible(False)
            stone_scroll.setVisible(False)
            normal_tab_btn.setChecked(True)
            bloodline_tab_btn.setChecked(False)
            stone_tab_btn.setChecked(False)
        
        def switch_to_bloodline():
            normal_scroll.setVisible(False)
            bloodline_scroll.setVisible(True)
            stone_scroll.setVisible(False)
            normal_tab_btn.setChecked(False)
            bloodline_tab_btn.setChecked(True)
            stone_tab_btn.setChecked(False)
        
        def switch_to_stone():
            normal_scroll.setVisible(False)
            bloodline_scroll.setVisible(False)
            stone_scroll.setVisible(True)
            normal_tab_btn.setChecked(False)
            bloodline_tab_btn.setChecked(False)
            stone_tab_btn.setChecked(True)
        
        normal_tab_btn.clicked.connect(switch_to_normal)
        bloodline_tab_btn.clicked.connect(switch_to_bloodline)
        stone_tab_btn.clicked.connect(switch_to_stone)
        
        content_layout.addWidget(skill_stack)
        
        content_layout.addStretch()
        
        # 将内容widget放入滚动区域
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
    def go_back(self):
        """返回图鉴列表"""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'show_list'):
                parent.show_list()
                return
            parent = parent.parent()
    
    def create_skill_box(self, skill, is_bloodline=False, is_stone=False):
        """创建技能信息框"""
        skill_box = RoundedFrame()
        
        # 根据技能类型设置不同的边框颜色
        if is_bloodline:
            border_color = "rgba(244, 114, 182, 0.3)"
            bg_color = "rgba(244, 114, 182, 0.05)"
        elif is_stone:
            border_color = "rgba(52, 211, 153, 0.3)"
            bg_color = "rgba(52, 211, 153, 0.05)"
        else:
            border_color = "rgba(139, 92, 246, 0.3)"
            bg_color = "rgba(139, 92, 246, 0.05)"
        
        skill_box.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        
        skill_layout = QVBoxLayout(skill_box)
        skill_layout.setSpacing(6)
        skill_layout.setContentsMargins(12, 8, 12, 8)
        
        # 第一行：技能名称 + 属性 + 类型
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # 技能名称
        skill_name = skill.get('name', '')
        name_label = QLabel(skill_name)
        name_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        header_layout.addWidget(name_label)
        
        # 属性标签
        attr = skill.get('attribute', '')
        if attr:
            attr_tag = QLabel(attr.replace('系', ''))
            attr_tag.setStyleSheet("""
                QLabel {
                    background-color: rgba(139, 92, 246, 0.2);
                    color: #a78bfa;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                }
            """)
            header_layout.addWidget(attr_tag)
        
        # 类型标签（物攻/魔攻/状态/防御）
        skill_type = skill.get('type', '')
        if skill_type:
            type_color = {
                '物攻': '#f87171',
                '魔攻': '#60a5fa',
                '状态': '#34d399',
                '防御': '#fbbf24'
            }.get(skill_type, '#9ca3af')
            
            type_tag = QLabel(skill_type)
            type_tag.setStyleSheet(f"""
                QLabel {{
                    background-color: rgba({int(type_color[1:3], 16)}, {int(type_color[3:5], 16)}, {int(type_color[5:7], 16)}, 0.2);
                    color: {type_color};
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                }}
            """)
            header_layout.addWidget(type_tag)
        
        header_layout.addStretch()
        skill_layout.addLayout(header_layout)
        
        # 第二行：威力 + 能耗
        info_layout = QHBoxLayout()
        info_layout.setSpacing(15)
        
        power = skill.get('power', '')
        if power and power != '0':
            power_label = QLabel(f"威力: {power}")
            power_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 12px;")
            info_layout.addWidget(power_label)
        
        cost = skill.get('cost', '')
        if cost and cost != '0':
            cost_label = QLabel(f"能耗: {cost}")
            cost_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 12px;")
            info_layout.addWidget(cost_label)
        
        info_layout.addStretch()
        skill_layout.addLayout(info_layout)
        
        # 第三行：技能描述
        desc = skill.get('description', '')
        if desc:
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 12px; line-height: 1.4;")
            desc_label.setWordWrap(True)
            skill_layout.addWidget(desc_label)
        
        return skill_box


class PokedexWidget(QWidget):
    """精灵图鉴主界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pokemon_data = []
        self.filtered_data = []
        self.current_view = 'list'
        self.init_ui()
        self.load_data()
    
    def focusOutEvent(self, event):
        """失去焦点时清除所有卡片焦点"""
        super().focusOutEvent(event)
        # 清除所有卡片的焦点
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                item.widget().clearFocus()
        
    def init_ui(self):
        """初始化UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 全局禁用焦点框
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        # 创建列表视图容器
        self.list_container = QWidget()
        list_layout = QVBoxLayout(self.list_container)
        list_layout.setContentsMargins(20, 20, 20, 20)
        list_layout.setSpacing(15)
        
        # 标题栏
        title_layout = QHBoxLayout()
        
        title = QLabel("精灵图鉴")
        title.setFont(QFont("Microsoft YaHei", 22, QFont.Bold))
        title.setStyleSheet("color: #a78bfa;")
        title_layout.addWidget(title)
        
        title_layout.addStretch()
        list_layout.addLayout(title_layout)
        
        # 数据来源说明
        source_label = QLabel("本页面数据来源于《洛克王国:世界》 bwiki (https://wiki.biligame.com/rocom/) 作者为BWIKI全体贡献者。")
        source_label.setStyleSheet("color: #6b7280; font-size: 11px; padding: 4px 0 8px 0;")
        source_label.setWordWrap(True)
        list_layout.addWidget(source_label)
        
        # 搜索栏
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索精灵...")
        self.search_input.setFixedHeight(36)
        self.search_input.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(167, 139, 250, 0.3);
                border-radius: 18px;
                padding: 8px 16px;
                color: white;
                font-size: 13px;
            }
            QLineEdit:focus {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid #a78bfa;
            }
            QLineEdit:hover {
                background-color: rgba(255, 255, 255, 0.12);
            }
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_input, stretch=2)
        
        self.type_filter = QComboBox()
        self.type_filter.addItem("全部")
        self.type_filter.setFixedHeight(36)
        self.type_filter.setFixedWidth(100)
        self.type_filter.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.type_filter.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(167, 139, 250, 0.3);
                border-radius: 18px;
                padding: 6px 12px;
                color: white;
                font-size: 13px;
            }
            QComboBox:focus {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid #a78bfa;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e2e;
                color: white;
                border: none;
            }
        """)
        self.type_filter.currentTextChanged.connect(self.on_filter_changed)
        search_layout.addWidget(self.type_filter)
        
        list_layout.addLayout(search_layout)
        
        # 统计信息
        self.stats_label = QLabel("加载中...")
        self.stats_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        list_layout.addWidget(self.stats_label)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.05);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(167, 139, 250, 0.5);
                border-radius: 3px;
            }
        """)
        
        self.content_widget = QWidget()
        self.grid_layout = QGridLayout(self.content_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        
        scroll.setWidget(self.content_widget)
        list_layout.addWidget(scroll)
        
        self.main_layout.addWidget(self.list_container)
        
    def show_list(self):
        """显示列表视图"""
        # 清空当前布局中的所有widget
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)  # 解除父子关系，不删除
                widget.hide()
        
        # 重新添加列表容器
        self.main_layout.addWidget(self.list_container)
        self.list_container.show()
        
        # 清除所有卡片的焦点
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                item.widget().clearFocus()
        
        # 清除父窗口中所有导航按钮的active状态
        parent = self.parent()
        while parent:
            if hasattr(parent, 'sidebar'):
                sidebar = parent.sidebar
                for i in range(sidebar.layout().count()):
                    item = sidebar.layout().itemAt(i)
                    if item and item.widget():
                        widget = item.widget()
                        if isinstance(widget, QWidget):
                            for child in widget.findChildren(QPushButton):
                                if child.objectName() == "navItem":
                                    child.setProperty("active", False)
                                    child.style().unpolish(child)
                                    child.style().polish(child)
                break
            parent = parent.parent()
        
        self.current_view = 'list'
        
    def show_detail(self, pokemon):
        """显示详情视图"""
        # 清空当前布局
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.hide()
        
        # 尝试从增强数据文件中获取完整信息
        enriched_pokemon = self.get_enriched_data(pokemon)
        
        # 创建新的详情页
        detail_widget = PokemonDetailWidget(enriched_pokemon)
        self.main_layout.addWidget(detail_widget)
        self.current_view = 'detail'
    
    def get_enriched_data(self, basic_pokemon):
        """获取增强数据（包含进化链、特性、技能）"""
        pid = basic_pokemon.get('id', 0)
        name = basic_pokemon.get('name', '')
        
        # 尝试加载增强数据文件
        enriched_file = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "lkwg_enriched_data.json")
        
        try:
            if os.path.exists(enriched_file):
                with open(enriched_file, 'r', encoding='utf-8') as f:
                    enriched_list = json.load(f)
                    
                    # 查找匹配的精灵
                    for p in enriched_list:
                        if p.get('id') == pid or p.get('name') == name:
                            # 合并基础数据和增强数据
                            merged = dict(basic_pokemon)
                            merged.update(p)  # 增强数据覆盖基础数据
                            return merged
        except Exception as e:
            print(f"加载增强数据失败: {e}")
        
        # 如果找不到增强数据，返回基础数据
        return basic_pokemon
        
    def load_data(self):
        """加载数据"""
        data_file = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "pokemon_data.json")
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                self.pokemon_data = json.load(f)
            
            types = set()
            for pokemon in self.pokemon_data:
                attr = pokemon.get('attribute', '')
                if attr:
                    if '/' in attr:
                        types.update(attr.split('/'))
                    else:
                        types.add(attr)
            
            for t in sorted(types):
                self.type_filter.addItem(t)
            
            self.filtered_data = self.pokemon_data.copy()
            self.refresh_display()
            
        except Exception as e:
            self.stats_label.setText(f"加载失败: {str(e)}")
            
    def on_search_changed(self, text):
        self.apply_filters()
        
    def on_filter_changed(self, text):
        self.apply_filters()
        
    def apply_filters(self):
        search_text = self.search_input.text().lower()
        type_filter = self.type_filter.currentText()
        
        filtered = []
        for pokemon in self.pokemon_data:
            name = pokemon.get('name', '').lower()
            pid = str(pokemon.get('id', ''))
            
            if search_text and search_text not in name and search_text not in pid:
                continue
            
            if type_filter != "全部":
                attr = pokemon.get('attribute', '')
                if type_filter not in attr:
                    continue
            
            filtered.append(pokemon)
        
        self.filtered_data = filtered
        self.refresh_display()
        
    def refresh_display(self):
        """刷新显示"""
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        total = len(self.pokemon_data)
        shown = len(self.filtered_data)
        self.stats_label.setText(f"共 {total} 个 | 显示 {shown} 个")
        
        # 固定3列布局
        columns = 3
        
        for idx, pokemon in enumerate(self.filtered_data):
            row = idx // columns
            col = idx % columns
            
            card = PokemonCard(pokemon)
            self.grid_layout.addWidget(card, row, col)
        
        self.grid_layout.setRowStretch(self.grid_layout.rowCount(), 1)
