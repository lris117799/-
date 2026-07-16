#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
家园系统 - 蛋组浏览界面
暖白卡片风格，蛋组分类展示精灵基础形态
"""

import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QScrollArea, QFrame, QPushButton,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QColor, QFont

from ui.breeding_query import BreedingQueryDialog


# ── 颜色常量 ──
BG_PAGE = "#FFF8E7"          # 米白色底色
CARD_WHITE = "#ffffff"        # 卡片白色
ACCENT = "#f97316"            # 暖橙主色
ACCENT_HOVER = "#ea580c"      # 暖橙深色(悬停)
ACCENT_LIGHT = "#fff7ed"      # 暖橙极浅底
TEXT_DARK = "#292524"         # 深棕文字
TEXT_MED = "#78716c"          # 中灰文字
TEXT_LIGHT = "#a8a29e"        # 浅灰文字
BORDER = "#e7e5e4"            # 浅边框
BORDER_HOVER = "#fdba74"      # 暖橙浅描边(悬停)
TAG_INACTIVE_BG = "#f5f5f4"   # 未选中标签底色
TAG_INACTIVE_TEXT = "#78716c" # 未选中标签文字


class HomeView(QWidget):
    """家园系统主界面 - 蛋组浏览"""
    
    pokemon_clicked = Signal(object)  # 精灵卡片被点击时发射 pokemon dict
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_pokemon = []
        self.egg_group_map = {}
        self.egg_group_names = []
        self.current_egg_group = None
        
        self._load_data()
        self._init_ui()
    
    # ────────────────────── 数据加载 ──────────────────────
    
    def _load_data(self):
        """加载并分析精灵数据"""
        data_file = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "pokemon_data.json")
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                self.all_pokemon = json.load(f)
        except Exception as e:
            print(f"加载精灵数据失败: {e}")
            return
        
        group_map = {}
        for p in self.all_pokemon:
            if p.get('is_leader_form', False):
                continue
            if not self._is_base_form(p):
                continue
            egg_groups = p.get('egg_groups', [])
            if not egg_groups:
                continue
            for eg in egg_groups:
                group_map.setdefault(eg, []).append(p)
        
        self.egg_group_map = group_map
        self.egg_group_names = sorted(group_map.keys(), key=lambda g: -len(group_map[g]))
    
    def _is_base_form(self, pokemon):
        """判断是否为可显示的基础形态（一阶或无法进化）"""
        name = pokemon.get('name', '')
        chain = pokemon.get('evolution_chain', [])
        if chain:
            return chain[0].get('name', '') == name
        evolution = pokemon.get('evolution', [])
        if evolution == ['无法进化']:
            return True
        if not chain and not evolution:
            return True
        if evolution and name not in evolution:
            return False
        return False
    
    # ────────────────────── 界面初始化 ──────────────────────
    
    def _init_ui(self):
        self.setStyleSheet(f"background-color: {BG_PAGE};")
        
        # 整体垂直布局
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        
        # 顶部白色区域（标题 + 标签栏）
        top_block = QWidget()
        top_block.setStyleSheet(f"background-color: {CARD_WHITE};")
        top_layout = QVBoxLayout(top_block)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        top_layout.addWidget(self._create_header())
        # 装饰线
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {BORDER}; margin: 0 32px;")
        top_layout.addWidget(line)
        top_layout.addWidget(self._create_tab_bar())
        root.addWidget(top_block)
        
        # 精灵展示区
        self.content_area = QScrollArea()
        self.content_area.setWidgetResizable(True)
        self.content_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_area.setStyleSheet(f"""
            QScrollArea {{ border: none; background-color: {BG_PAGE}; }}
            QScrollBar:vertical {{
                background: transparent; width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: #d6d3d1; border-radius: 3px; min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(f"background-color: {BG_PAGE};")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(32, 28, 32, 40)
        self.content_layout.setSpacing(0)
        
        self.content_area.setWidget(self.content_widget)
        root.addWidget(self.content_area, stretch=1)
        
        # 默认选中第一个蛋组
        if self.egg_group_names:
            self._select_egg_group(self.egg_group_names[0])
    
    def _create_header(self):
        """顶部标题行"""
        hdr = QWidget()
        hdr.setFixedHeight(80)
        hdr.setStyleSheet(f"background-color: {CARD_WHITE};")
        
        lo = QHBoxLayout(hdr)
        lo.setContentsMargins(32, 0, 32, 0)
        
        title = QLabel("家园 · 蛋组")
        title.setStyleSheet(f"""
            font-size: 22px; font-weight: 700;
            color: {TEXT_DARK}; background: transparent;
        """)
        lo.addWidget(title)
        
        total_groups = len(self.egg_group_names)
        total_pokemon = sum(len(v) for v in self.egg_group_map.values())
        sub = QLabel(f"{total_groups} 个蛋组 · {total_pokemon} 只精灵")
        sub.setStyleSheet(f"""
            font-size: 13px; color: {TEXT_LIGHT};
            background: transparent; padding-top: 4px;
        """)
        lo.addWidget(sub)
        lo.addStretch()
        
        # 孵蛋查询按钮
        breed_btn = QPushButton("🥚 孵蛋查询")
        breed_btn.setCursor(Qt.PointingHandCursor)
        breed_btn.setFixedHeight(34)
        breed_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}; color: white; border: none;
                border-radius: 17px; padding: 0 20px;
                font-size: 13px; font-weight: 600;
            }}
            QPushButton:hover {{
                background: {ACCENT_HOVER};
            }}
        """)
        breed_btn.clicked.connect(self._open_breeding_query)
        lo.addWidget(breed_btn)
        
        return hdr
    
    def _open_breeding_query(self):
        """打开孵蛋查询窗口"""
        dialog = BreedingQueryDialog(self)
        dialog.exec()
    
    # ────────────────────── 蛋组标签栏 ──────────────────────
    
    def _create_tab_bar(self):
        """两排蛋组标签"""
        container = QWidget()
        container.setStyleSheet(f"background-color: {CARD_WHITE};")
        
        main_lo = QVBoxLayout(container)
        main_lo.setContentsMargins(32, 10, 32, 14)
        main_lo.setSpacing(8)
        
        self.tab_buttons = []
        total = len(self.egg_group_names)
        mid = (total + 1) // 2
        
        for row_idx in range(2):
            row_lo = QHBoxLayout()
            row_lo.setContentsMargins(0, 0, 0, 0)
            row_lo.setSpacing(8)
            
            start = 0 if row_idx == 0 else mid
            end = mid if row_idx == 0 else total
            
            for i in range(start, end):
                eg_name = self.egg_group_names[i]
                count = len(self.egg_group_map[eg_name])
                btn = EggGroupChip(eg_name, count)
                btn.clicked.connect(lambda checked, name=eg_name: self._select_egg_group(name))
                row_lo.addWidget(btn)
                self.tab_buttons.append(btn)
            
            row_lo.addStretch()
            main_lo.addLayout(row_lo)
        
        return container
    
    def _select_egg_group(self, egg_group_name):
        """选中蛋组，展示精灵"""
        self.current_egg_group = egg_group_name
        
        for btn in self.tab_buttons:
            btn.set_active(btn.group_name == egg_group_name)
        
        self._rebuild_content(egg_group_name)
    
    # ────────────────────── 精灵展示区 ──────────────────────
    
    def _rebuild_content(self, egg_group_name):
        """清空并重建精灵网格"""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        pokemon_list = self.egg_group_map.get(egg_group_name, [])
        pokemon_list.sort(key=lambda p: p.get('id', 0))
        
        if not pokemon_list:
            empty = QLabel("该蛋组暂无精灵数据")
            empty.setStyleSheet(f"color: {TEXT_LIGHT}; font-size: 15px; background: transparent;")
            empty.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(empty)
            self.content_layout.addStretch()
            return
        
        # 分组标题 + 计数
        title = QLabel(f"{egg_group_name}  ·  {len(pokemon_list)} 只")
        title.setStyleSheet(f"""
            font-size: 17px; font-weight: 600;
            color: {TEXT_DARK}; background: transparent;
            padding-bottom: 18px;
        """)
        self.content_layout.addWidget(title)
        
        # 网格
        cols = 8
        grid_widget = QWidget()
        grid_widget.setStyleSheet(f"background-color: {BG_PAGE};")
        grid = QGridLayout(grid_widget)
        grid.setSpacing(14)
        grid.setContentsMargins(0, 0, 0, 0)
        
        for idx, p in enumerate(pokemon_list):
            row, col = divmod(idx, cols)
            card = PokemonMiniCard(p)
            card.clicked.connect(self.pokemon_clicked.emit)
            grid.addWidget(card, row, col)
        
        # 末行空位占位
        remainder = len(pokemon_list) % cols
        if remainder:
            last_row = len(pokemon_list) // cols
            for i in range(remainder, cols):
                ph = QWidget()
                ph.setStyleSheet("background-color: transparent;")
                grid.addWidget(ph, last_row, i)
        
        self.content_layout.addWidget(grid_widget)
        self.content_layout.addStretch()


# ═══════════════════════════════════════════════════════
#  蛋组标签 Chip
# ═══════════════════════════════════════════════════════

class EggGroupChip(QPushButton):
    """蛋组标签 - 圆角胶囊风格"""
    
    def __init__(self, group_name, count, parent=None):
        super().__init__(parent)
        self.group_name = group_name
        self._active = False
        self.setText(f"{group_name}  {count}")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(34)
        self.setMinimumWidth(80)
        # 计算合适宽度
        text_w = len(f"{group_name}  {count}") * 13 + 36
        self.setMinimumWidth(max(80, text_w))
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self._update_style()
    
    def _update_style(self):
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 {ACCENT}, stop:1 {ACCENT_HOVER});
                    color: white; border: none;
                    border-radius: 17px;
                    padding: 0 20px;
                    font-size: 13px; font-weight: 600;
                    outline: none;
                }}
                QPushButton:hover {{
                    background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                        stop:0 {ACCENT_HOVER}, stop:1 #d95600);
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {TAG_INACTIVE_BG};
                    color: {TAG_INACTIVE_TEXT}; border: none;
                    border-radius: 17px;
                    padding: 0 20px;
                    font-size: 13px; font-weight: 500;
                    outline: none;
                }}
                QPushButton:hover {{
                    background-color: {ACCENT_LIGHT};
                    color: {ACCENT};
                }}
            """)
    
    def set_active(self, active):
        self._active = active
        self._update_style()


# ═══════════════════════════════════════════════════════
#  精灵迷你卡片
# ═══════════════════════════════════════════════════════

class PokemonMiniCard(QFrame):
    """精灵迷你卡片 - 白底圆角 + 阴影 + 悬停上浮"""
    
    clicked = Signal(object)
    
    def __init__(self, pokemon, parent=None):
        super().__init__(parent)
        self.pokemon = pokemon
        self.setFixedSize(118, 148)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        
        self._setup_ui()
        self._add_shadow()
    
    def _add_shadow(self):
        """投影阴影"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 18))
        self.setGraphicsEffect(shadow)
    
    def _setup_ui(self):
        lo = QVBoxLayout(self)
        lo.setContentsMargins(6, 10, 6, 8)
        lo.setSpacing(6)
        lo.setAlignment(Qt.AlignCenter)
        
        # ── 精灵图片 ──
        img_label = QLabel()
        img_label.setFixedSize(78, 78)
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setStyleSheet("""
            background: transparent;
            border: none;
            outline: none;
        """)
        
        pid = self.pokemon.get('id', 0)
        img_path = os.path.join(
            os.path.dirname(__file__), "..", "image", "tj", "images", f"{pid:03d}.png"
        )
        if os.path.exists(img_path):
            pm = QPixmap(img_path)
            if not pm.isNull():
                s = pm.scaled(74, 74, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_label.setPixmap(s)
        
        lo.addWidget(img_label, alignment=Qt.AlignCenter)
        
        # ── 名字 ──
        raw = self.pokemon.get('name', '未知')
        display = raw.split('（')[0].split('(')[0].strip()
        if len(display) > 5:
            display = display[:4] + '…'
        
        name_lbl = QLabel(display)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setMaximumWidth(106)
        name_lbl.setStyleSheet(f"""
            color: {TEXT_DARK};
            font-size: 12px; font-weight: 500;
            background: transparent;
        """)
        lo.addWidget(name_lbl, alignment=Qt.AlignCenter)
        
        # ── 基础卡片样式 ──
        self._apply_base_style()
    
    def _apply_base_style(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD_WHITE};
                border: 1px solid {BORDER};
                border-radius: 11px;
            }}
            QFrame:hover {{
                border: 1.5px solid {ACCENT};
                background-color: #fffcf7;
            }}
        """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.pokemon)