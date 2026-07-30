#!/usr/bin/env python
# -*- coding: utf-8 -*-

import warnings
warnings.filterwarnings("ignore", message="iCCP: known incorrect sRGB profile")

import json
import os
import re
import math
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QScrollArea, QLineEdit,
    QFrame, QGroupBox, QCheckBox, QSpinBox, QListWidget, QListWidgetItem,
    QSlider, QDialog
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QPixmap

from ui.pokedex_view import (
    PALETTE, ParchmentWidget, RoundedFrame,
    _load_icon, _get_attr_icon, _skill_icon, _skill_type_icon,
    _make_attr_pill, _make_skill_type_badge,
    _type_bg, SCROLL_BAR_STYLE, _get_dpr, _scale_hdpi,
    _SKILL_TYPE_COLORS,
)

_SC_SC_DIR = os.path.join(os.path.dirname(__file__), "..", "image", "sc", "sc")
_SC_DIR = os.path.join(os.path.dirname(__file__), "..", "image", "sc")
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "image", "tj")
_ENRICHED_FILE = os.path.join(_DATA_DIR, "lkwg_enriched_data.json")
_POKEMON_DATA_FILE = os.path.join(_DATA_DIR, "pokemon_data.json")
_STAR_GRAY = os.path.join(_SC_DIR, "xx.png")
_STAR_GOLD = os.path.join(_SC_DIR, "hx.png")

def _input_style():
    return f"""
        QSpinBox, QComboBox, QLineEdit {{
            background-color: {PALETTE['bg_inset']};
            border: 1px solid {PALETTE['border']};
            border-radius: 5px;
            padding: 0 8px;
            color: {PALETTE['text']};
            font-size: 12px;
            outline: none;
        }}
        QSpinBox:focus, QComboBox:focus, QLineEdit:focus {{
            border: 1px solid {PALETTE['gold_deep']};
            background-color: {PALETTE['bg_hover']};
        }}
        QSpinBox:disabled {{
            background-color: rgba(200, 185, 150, 0.25);
            color: {PALETTE['text_mute']};
        }}
        QComboBox::drop-down {{ border: none; width: 18px; }}
        QComboBox QAbstractItemView {{
            background-color: {PALETTE['bg_card']};
            color: {PALETTE['text']};
            selection-background-color: {PALETTE['gold_light']};
            selection-color: {PALETTE['text_on_gold']};
            border: 1px solid {PALETTE['border']};
            outline: none;
        }}
    """

def _group_style():
    return f"""
        QGroupBox {{
            color: {PALETTE['text']};
            font-size: 13px;
            font-weight: bold;
            background-color: rgba(255, 250, 240, 0.45);
            border: 1px solid {PALETTE['border']};
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: {PALETTE['gold_deep']};
        }}
    """

def _label_style(color=None, size=12, bold=False):
    c = color or PALETTE['text']
    fw = 'bold' if bold else 'normal'
    return (f"color: {c}; font-size: {size}px; font-weight: {fw};"
            f" background: transparent; border: none;")

def _gold_btn_style():
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {PALETTE['gold_light']}, stop:1 {PALETTE['gold']});
            color: {PALETTE['text_on_gold']};
            border: 1px solid {PALETTE['gold_deep']};
            border-radius: 8px;
            font-size: 13px;
            font-weight: bold;
            outline: none;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {PALETTE['gold']}, stop:1 {PALETTE['gold_deep']});
            color: white;
        }}
        QPushButton:pressed {{
            background: {PALETTE['gold_deep']};
        }}
    """

def _sub_btn_style():
    return f"""
        QPushButton {{
            background-color: {PALETTE['bg_inset']};
            color: {PALETTE['text_sub']};
            border: 1px solid {PALETTE['border']};
            border-radius: 7px;
            font-size: 12px;
            outline: none;
        }}
        QPushButton:hover {{
            background-color: {PALETTE['bg_hover']};
            color: {PALETTE['text']};
            border: 1px solid {PALETTE['gold']};
        }}
    """

def _slider_style():
    return f"""
        QSlider::groove:horizontal {{
            border: 1px solid {PALETTE['border']};
            height: 6px;
            background-color: {PALETTE['bg_inset']};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background-color: {PALETTE['gold']};
            border: 2px solid {PALETTE['gold_deep']};
            width: 16px;
            margin-top: -6px;
            margin-bottom: -6px;
            border-radius: 9px;
        }}
        QSlider::handle:horizontal:hover {{
            background-color: {PALETTE['gold_deep']};
        }}
    """

def _check_style():
    return f"""
        QCheckBox {{
            color: {PALETTE['text']};
            font-size: 12px;
            spacing: 6px;
            background: transparent;
        }}
        QCheckBox::indicator {{
            width: 16px; height: 16px;
            border-radius: 3px;
            background-color: {PALETTE['bg_inset']};
            border: 1.5px solid {PALETTE['border_dark']};
        }}
        QCheckBox::indicator:hover {{
            border: 1.5px solid {PALETTE['gold_deep']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {PALETTE['gold']};
            border: 1.5px solid {PALETTE['gold_deep']};
        }}
        QCheckBox::indicator:disabled {{
            opacity: 0.3;
        }}
    """


_SKILL_POOL_CACHE = None

def build_skill_pool():
    """扫描所有精灵数据，构建全技能池（按 name 去重）。"""
    global _SKILL_POOL_CACHE
    if _SKILL_POOL_CACHE is not None:
        return _SKILL_POOL_CACHE
    pool = {}
    for fpath in (_ENRICHED_FILE, _POKEMON_DATA_FILE):
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            continue
        for poke in data:
            skills = poke.get('skills', {})
            for key in ('normal_skills', 'bloodline_skills', 'stone_skills'):
                for sk in skills.get(key, []):
                    name = sk.get('name', '')
                    if not name or name in pool:
                        continue
                    pool[name] = dict(sk)
    _SKILL_POOL_CACHE = dict(sorted(pool.items()))
    return _SKILL_POOL_CACHE


class SpriteSearchBox(QWidget):
    sprite_selected = Signal(object)  # 选中精灵后发出

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sprite_list = []
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入精灵名字...")
        self.search_input.setFixedHeight(32)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {PALETTE['bg_inset']};
                border: 1px solid {PALETTE['border']};
                border-radius: 6px;
                padding: 0 12px;
                color: {PALETTE['text']};
                font-size: 13px;
            }}
            QLineEdit:focus {{ border: 1px solid {PALETTE['gold_deep']}; }}
        """)
        self.search_input.textChanged.connect(self.on_search)
        layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(240)
        self.list_widget.setMaximumHeight(320)
        self.list_widget.setVisible(False)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border_dark']};
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 7px 12px;
                border-radius: 4px;
                margin: 1px 0;
                color: {PALETTE['text']};
                font-size: 13px;
            }}
            QListWidget::item:hover {{
                background-color: {PALETTE['bg_hover']};
            }}
            QListWidget::item:selected {{
                background-color: {PALETTE['gold_light']};
                color: {PALETTE['text_on_gold']};
            }}
        """)
        self.list_widget.itemClicked.connect(self.on_item_selected)
        layout.addWidget(self.list_widget)

    def load_data(self):
        if os.path.exists(_ENRICHED_FILE):
            try:
                with open(_ENRICHED_FILE, 'r', encoding='utf-8') as f:
                    self.sprite_list = json.load(f)
            except Exception:
                self.sprite_list = []

    def on_search(self, text):
        if not text:
            self.list_widget.setVisible(False)
            return
        self.list_widget.clear()
        t = text.lower().strip()
        for sprite in self.sprite_list:
            name = sprite.get('name', '')
            if t in name.lower():
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, sprite)
                self.list_widget.addItem(item)
        self.list_widget.setVisible(self.list_widget.count() > 0)

    def on_item_selected(self, item):
        sprite = item.data(Qt.UserRole)
        self.search_input.setText(sprite.get('name', ''))
        self.list_widget.setVisible(False)
        self.sprite_selected.emit(sprite)

    def clear_text(self):
        self.search_input.clear()
        self.list_widget.setVisible(False)


class SkillSelectionDialog(QDialog):
    """选择技能弹窗 - 羊皮纸主题"""

    def __init__(self, learnable_skills, parent=None):
        super().__init__(parent)
        self.learnable_skills = learnable_skills or []  # 该精灵可学技能列表
        self.selected_skill = None
        self.all_pool = build_skill_pool()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("选择技能")
        self.setFixedSize(560, 720)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        self.setStyleSheet(f"""
            QDialog {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {PALETTE['bg_top']}, stop:1 {PALETTE['bg_bottom']});
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(10)

        title = QLabel("✦ 选择技能")
        title.setStyleSheet(_label_style(PALETTE['gold_deep'], 18, True))
        outer.addWidget(title)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索技能名...")
        self.search_input.setFixedHeight(30)
        self.search_input.setStyleSheet(_input_style().replace(
            "QSpinBox, QComboBox, QLineEdit", "QLineEdit"))
        self.search_input.textChanged.connect(self._refresh_list)
        filter_row.addWidget(self.search_input, 1)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("可学技能", 'learnable')
        self.filter_combo.addItem("全部技能池", 'all')
        self.filter_combo.setFixedHeight(30)
        self.filter_combo.setStyleSheet(_input_style().replace(
            "QSpinBox, QComboBox, QLineEdit", "QComboBox"))
        self.filter_combo.currentIndexChanged.connect(self._refresh_list)
        filter_row.addWidget(self.filter_combo, 0)
        outer.addLayout(filter_row)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: rgba(255, 250, 240, 0.55);
                border: 1px solid {PALETTE['border']};
                border-radius: 8px;
                padding: 6px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 0px;
                margin: 3px 0;
                border: none;
            }}
        """)
        self.list_widget.setSelectionMode(QListWidget.NoSelection)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        outer.addWidget(self.list_widget, 1)

        close_btn = QPushButton("关 闭")
        close_btn.setFixedHeight(34)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(_sub_btn_style())
        close_btn.clicked.connect(self.reject)
        outer.addWidget(close_btn)

        self._refresh_list()

    def _current_source_list(self):
        if self.filter_combo.currentData() == 'learnable':
            return self.learnable_skills
        return list(self.all_pool.values())

    def _refresh_list(self, *_):
        text = self.search_input.text().lower().strip()
        self.list_widget.clear()
        for sk in self._current_source_list():
            name = sk.get('name', '')
            if text and text not in name.lower():
                continue
            item = QListWidgetItem()
            item.setData(Qt.UserRole, sk)
            item.setSizeHint(QSize(0, 76))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, self._make_skill_row(sk))

    def _make_skill_row(self, sk):
        row = QFrame()
        row.setFixedHeight(70)
        row.setCursor(Qt.PointingHandCursor)
        row.setStyleSheet(f"""
            QFrame {{
                background-color: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border: 1px solid {PALETTE['gold']};
                background-color: {PALETTE['bg_hover']};
            }}
        """)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(8, 6, 10, 6)
        lay.setSpacing(8)

        name = sk.get('name', '')
        pm = _skill_icon(name, size=44)
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(44, 44)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        if pm and not pm.isNull():
            icon_lbl.setPixmap(pm)
        lay.addWidget(icon_lbl)

        mid = QVBoxLayout()
        mid.setSpacing(2)
        mid.setContentsMargins(0, 0, 0, 0)
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(_label_style(PALETTE['text'], 14, True))
        mid.addWidget(name_lbl)

        meta = QHBoxLayout()
        meta.setSpacing(6)
        attr = sk.get('attribute', '')
        if attr:
            attr_pill = _make_attr_pill(attr, font_size=10, icon_size=12,
                                        pad_h=7, pad_v=1, radius=8)
            meta.addWidget(attr_pill)
        stype = sk.get('type', '')
        if stype:
            tb = _make_skill_type_badge(stype, icon_size=16)
            meta.addWidget(tb)
        power = sk.get('power', '')
        if power and str(power) not in ('0', '-'):
            pw = QLabel(f"威力 {power}")
            pw.setStyleSheet(_label_style('#c8463c', 11, True))
            meta.addWidget(pw)
        cost = sk.get('cost', '')
        if cost and str(cost) not in ('0', '-'):
            ct = QLabel(f"能耗 {cost}")
            ct.setStyleSheet(_label_style('#3c82c8', 11, True))
            meta.addWidget(ct)
        meta.addStretch()
        mid.addLayout(meta)
        lay.addLayout(mid, 1)
        return row

    def _on_item_clicked(self, item):
        self.selected_skill = item.data(Qt.UserRole)
        self.accept()


class SkillSlotWidget(QFrame):
    """单个技能栏位，可点击选中。"""
    clicked = Signal(int)  # 发出栏位索引

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.skill = None
        self._selected = False
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(86)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 10, 6)
        lay.setSpacing(8)

        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(48, 48)
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(self.icon_lbl)

        mid = QVBoxLayout()
        mid.setSpacing(2)
        mid.setContentsMargins(0, 0, 0, 0)

        self.name_lbl = QLabel("（空）")
        self.name_lbl.setStyleSheet(_label_style(PALETTE['text_mute'], 13, True))
        mid.addWidget(self.name_lbl)

        self.meta_row = QHBoxLayout()
        self.meta_row.setSpacing(5)
        self.meta_row.setContentsMargins(0, 0, 0, 0)
        self._meta_widget = QWidget()
        self._meta_widget.setStyleSheet("background: transparent; border: none;")
        self._meta_widget.setLayout(self.meta_row)
        mid.addWidget(self._meta_widget)

        self.desc_lbl = QLabel("")
        self.desc_lbl.setStyleSheet(_label_style(PALETTE['text_sub'], 10))
        self.desc_lbl.setWordWrap(False)
        mid.addWidget(self.desc_lbl)

        lay.addLayout(mid, 1)

        right = QVBoxLayout()
        right.setSpacing(0)
        right.setContentsMargins(0, 0, 0, 0)
        self.display_power_lbl = QLabel("—")
        self.display_power_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.display_power_lbl.setStyleSheet(
            _label_style(PALETTE['gold_deep'], 16, True))
        right.addWidget(self.display_power_lbl)

        self.dp_caption = QLabel("显示威力")
        self.dp_caption.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.dp_caption.setStyleSheet(_label_style(PALETTE['text_mute'], 9))
        right.addWidget(self.dp_caption)

        self.damage_lbl = QLabel("—")
        self.damage_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.damage_lbl.setStyleSheet(_label_style('#c8463c', 12, True))
        right.addWidget(self.damage_lbl)

        lay.addLayout(right)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _apply_style(self):
        if self._selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {PALETTE['bg_hover']};
                    border: 2px solid {PALETTE['gold_deep']};
                    border-radius: 10px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {PALETTE['bg_card']};
                    border: 1px solid {PALETTE['border']};
                    border-radius: 10px;
                }}
                QFrame:hover {{
                    border: 1px solid {PALETTE['gold']};
                }}
            """)

    def set_selected(self, sel):
        self._selected = sel
        self._apply_style()

    def set_skill(self, skill):
        self.skill = skill
        self._clear_layout(self.meta_row)
        if not skill:
            self.icon_lbl.clear()
            self.name_lbl.setText("（空）")
            self.name_lbl.setStyleSheet(_label_style(PALETTE['text_mute'], 13, True))
            self.desc_lbl.setText("点击选择技能按钮选择技能")
            self.display_power_lbl.setText("—")
            self.damage_lbl.setText("—")
            return

        name = skill.get('name', '')
        self.name_lbl.setText(name)
        self.name_lbl.setStyleSheet(_label_style(PALETTE['text'], 13, True))

        pm = _skill_icon(name, size=48)
        if pm and not pm.isNull():
            self.icon_lbl.setPixmap(pm)
        else:
            self.icon_lbl.clear()

        attr = skill.get('attribute', '')
        if attr:
            self.meta_row.addWidget(_make_attr_pill(attr, font_size=10, icon_size=12,
                                                    pad_h=6, pad_v=1, radius=8))
        stype = skill.get('type', '')
        if stype:
            self.meta_row.addWidget(_make_skill_type_badge(stype, icon_size=14))
        power = skill.get('power', '')
        if power and str(power) not in ('0', '-'):
            pw = QLabel(f"威力 {power}")
            pw.setStyleSheet(_label_style('#c8463c', 11, True))
            self.meta_row.addWidget(pw)
        cost = skill.get('cost', '')
        if cost and str(cost) not in ('0', '-'):
            ct = QLabel(f"能耗 {cost}")
            ct.setStyleSheet(_label_style('#3c82c8', 11, True))
            self.meta_row.addWidget(ct)
        self.meta_row.addStretch()

        desc = skill.get('description', '')
        if desc:
            self.desc_lbl.setText(desc.replace('✦', '').strip()[:32])

    def set_power_and_damage(self, display_power, damage, pct, type_mult):
        """更新显示威力与伤害。type_mult 决定颜色。"""
        if display_power is None:
            self.display_power_lbl.setText("—")
        else:
            self.display_power_lbl.setText(str(display_power))
            if type_mult > 1.0:
                self.display_power_lbl.setStyleSheet(_label_style('#5aa05a', 16, True))
            elif type_mult < 1.0:
                self.display_power_lbl.setStyleSheet(_label_style('#c8463c', 16, True))
            else:
                self.display_power_lbl.setStyleSheet(_label_style(PALETTE['gold_deep'], 16, True))

        if damage is None:
            self.damage_lbl.setText("—")
        else:
            self.damage_lbl.setText(f"{damage}  ({pct:.0f}%)")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.index)


class DamageCalculatorWidget(ParchmentWidget):
    """伤害计算器主界面 - 羊皮纸主题"""

    IV_RANGES = [
        (7, 10), (14, 20), (21, 30), (28, 40), (35, 50), (42, 60)
    ]
    STAT_NAMES = ["生命", "物攻", "物防", "魔攻", "魔防", "速度"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sprite1_data = None
        self.sprite2_data = None
        self.natures = self._load_natures()
        self.effectiveness = self._load_effectiveness()
        self._build_skill_pool_for_pokemon = {}  # sprite name -> learnable list
        self.setup_ui()

    def _load_natures(self):
        natures = {}
        nature_file = os.path.join(os.path.dirname(__file__), '..', "性格.txt")
        if os.path.exists(nature_file):
            try:
                with open(nature_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        m = re.match(r'(\S+)\s+([\u4e00-\u9fa5]+)\s*\+\s*(\d+)%，([\u4e00-\u9fa5]+)\s*-\s*(\d+)%', line)
                        if m:
                            natures[m.group(1)] = {
                                'boost': (m.group(2), int(m.group(3))),
                                'reduce': (m.group(4), int(m.group(5))),
                            }
            except Exception:
                pass
        return natures

    def _load_effectiveness(self):
        effectiveness = {}
        type_file = os.path.join(os.path.dirname(__file__), '..', "克制.txt")
        if not os.path.exists(type_file):
            return effectiveness

        all_types = ['草', '火', '水', '光', '地', '冰', '龙', '电', '毒', '虫',
                     '武', '翼', '萌', '幽', '恶', '普', '幻', '机械']
        for attr in all_types:
            effectiveness[attr + '系'] = {
                'attack_2x': [], 'attack_0.5x': [],
                'defense_2x': [], 'defense_0.5x': []
            }

        current_attr = None
        section = None
        try:
            with open(type_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    m = re.match(r'Step\d+：(\w+)系', line)
                    if m:
                        current_attr = m.group(1) + '系'
                        continue
                    if '作为攻击方' in line:
                        section = 'attack'; continue
                    elif '作为被攻击方' in line:
                        section = 'defense'; continue
                    if current_attr and section:
                        hm = re.search(r'对(.+?)系造成0\.5倍伤害', line)
                        if hm and section == 'attack':
                            effectiveness[current_attr]['attack_0.5x'] = [
                                a.strip() + '系' for a in hm.group(1).split('/')]
                            continue
                        hm = re.search(r'受到(.+?)系的0\.5倍伤害', line)
                        if hm and section == 'defense':
                            effectiveness[current_attr]['defense_0.5x'] = [
                                a.strip() + '系' for a in hm.group(1).split('/')]
                            continue
                        dm = re.search(r'对(.+?)系造成2倍伤害', line)
                        if dm and section == 'attack':
                            effectiveness[current_attr]['attack_2x'] = [
                                a.strip() + '系' for a in dm.group(1).split('/')]
                            continue
                        dm = re.search(r'受到(.+?)系的2倍伤害', line)
                        if dm and section == 'defense':
                            effectiveness[current_attr]['defense_2x'] = [
                                a.strip() + '系' for a in dm.group(1).split('/')]
                            continue
        except Exception:
            pass
        return effectiveness

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QLabel("✦  伤害计算器")
        header.setAlignment(Qt.AlignCenter)
        header.setFixedHeight(40)
        header.setStyleSheet(f"""
            QLabel {{
                color: {PALETTE['text_on_gold']};
                font-size: 18px;
                font-weight: bold;
                letter-spacing: 2px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PALETTE['gold']}, stop:0.5 {PALETTE['gold_deep']}, stop:1 {PALETTE['gold']});
                border-bottom: 2px solid {PALETTE['gold_deep']};
            }}
        """)
        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(SCROLL_BAR_STYLE)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        main_layout = QHBoxLayout(content)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(14)

        left = self._create_sprite_panel("精灵1", "sprite1")
        right = self._create_sprite_panel("精灵2", "sprite2")
        main_layout.addWidget(left, 1)
        main_layout.addWidget(right, 1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    def _create_sprite_panel(self, title, side):
        panel = RoundedFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 250, 240, 0.78);
                border: 1px solid {PALETTE['border_dark']};
                border-radius: 14px;
            }}
        """)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(8)

        t_lbl = QLabel(title)
        t_lbl.setAlignment(Qt.AlignCenter)
        t_lbl.setStyleSheet(f"""
            QLabel {{
                color: {PALETTE['text_on_gold']};
                font-size: 16px;
                font-weight: bold;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PALETTE['gold_light']}, stop:1 {PALETTE['gold']});
                border: 1px solid {PALETTE['gold_deep']};
                border-radius: 8px;
                padding: 4px;
            }}
        """)
        lay.addWidget(t_lbl)

        lay.addWidget(self._section_label("精灵"))
        search_box = SpriteSearchBox()
        search_box.sprite_selected.connect(lambda sp, s=side: self.on_sprite_selected(sp, s))
        setattr(self, f"{side}_search_box", search_box)
        lay.addWidget(search_box)

        lay.addWidget(self._section_label("属性"))
        attr_row = QHBoxLayout()
        attr_row.setSpacing(6)
        attr1 = self._make_attr_placeholder()
        attr2 = self._make_attr_placeholder()
        attr_row.addWidget(attr1, 1)
        attr_row.addWidget(attr2, 1)
        setattr(self, f"{side}_attr1", attr1)
        setattr(self, f"{side}_attr2", attr2)
        lay.addLayout(attr_row)

        lay.addWidget(self._section_label("等级"))
        level_row = QHBoxLayout()
        level_row.setSpacing(8)
        level_label = QLabel("60")
        level_label.setFixedWidth(28)
        level_label.setAlignment(Qt.AlignCenter)
        level_label.setStyleSheet(_label_style(PALETTE['gold_deep'], 14, True))
        level_slider = QSlider(Qt.Horizontal)
        level_slider.setRange(1, 60)
        level_slider.setValue(60)
        level_slider.setStyleSheet(_slider_style())
        level_slider.valueChanged.connect(
            lambda v, s=side, lbl=level_label: self.on_level_changed(v, s, lbl))
        level_row.addWidget(level_slider, 1)
        level_row.addWidget(level_label)
        setattr(self, f"{side}_level_slider", level_slider)
        setattr(self, f"{side}_level_value", 60)
        setattr(self, f"{side}_level_value_label", level_label)
        lay.addLayout(level_row)

        stats_group = QGroupBox("当前属性")
        stats_group.setStyleSheet(_group_style())
        sg = QGridLayout(stats_group)
        sg.setSpacing(6)
        stat_labels = {}
        for i, name in enumerate(self.STAT_NAMES):
            lbl = QLabel(f"{name}: -")
            lbl.setStyleSheet(_label_style(PALETTE['text'], 12))
            sg.addWidget(lbl, i // 2, i % 2 * 2)
            stat_labels[name] = lbl
        setattr(self, f"{side}_stat_labels", stat_labels)
        setattr(self, f"{side}_computed_stats", {})
        lay.addWidget(stats_group)

        lay.addWidget(self._section_label("星级评定"))
        star_row = QHBoxLayout()
        star_row.setSpacing(6)
        star_row.addStretch()
        star_btns = []
        for i in range(5):
            btn = QPushButton()
            btn.setFixedSize(30, 30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("QPushButton { border: none; background: transparent; }")
            btn.clicked.connect(lambda _, idx=i, s=side: self.on_star_clicked(idx, s))
            star_row.addWidget(btn)
            star_btns.append(btn)
        star_row.addStretch()
        setattr(self, f"{side}_stars", star_btns)
        setattr(self, f"{side}_star_count", 0)
        star_container = QWidget()
        star_container.setStyleSheet("background: transparent; border: none;")
        star_container.setLayout(star_row)
        lay.addWidget(star_container)
        self._update_star_display(side)

        full_iv = QCheckBox("满资质（5星·个体60）")
        full_iv.setStyleSheet(_check_style())
        full_iv.stateChanged.connect(lambda _: self.on_full_iv_changed(side))
        setattr(self, f"{side}_full_iv", full_iv)
        lay.addWidget(full_iv)

        iv_group = QGroupBox("能力值配置")
        iv_group.setStyleSheet(_group_style())
        iv_grid = QGridLayout(iv_group)
        iv_grid.setSpacing(5)
        race_inputs, iv_inputs, iv_checks = {}, {}, {}
        for col, txt in enumerate(["属性", "种族", "个体?", "个体值"]):
            h = QLabel(txt)
            h.setStyleSheet(_label_style(PALETTE['gold_deep'], 11, True))
            h.setAlignment(Qt.AlignCenter)
            iv_grid.addWidget(h, 0, col)
        for i, name in enumerate(self.STAT_NAMES):
            r = i + 1
            iv_grid.addWidget(self._plain_label(name), r, 0)
            race_spin = QSpinBox()
            race_spin.setRange(0, 9999)
            race_spin.setFixedHeight(26)
            race_spin.setFixedWidth(70)
            race_spin.setStyleSheet(_input_style())
            race_spin.valueChanged.connect(lambda _, s=side: self.calculate_stats(s))
            iv_grid.addWidget(race_spin, r, 1)
            race_inputs[name] = race_spin

            iv_check = QCheckBox()
            iv_check.setStyleSheet(_check_style())
            iv_grid.addWidget(iv_check, r, 2, alignment=Qt.AlignCenter)
            iv_checks[name] = iv_check

            iv_spin = QSpinBox()
            iv_spin.setRange(0, 60)
            iv_spin.setFixedHeight(26)
            iv_spin.setFixedWidth(70)
            iv_spin.setStyleSheet(_input_style())
            iv_spin.setEnabled(False)
            iv_spin.valueChanged.connect(lambda _, s=side: self.calculate_stats(s))
            iv_grid.addWidget(iv_spin, r, 3)
            iv_inputs[name] = iv_spin

            def _on_check(checked, sp=iv_spin, ck=iv_check, s=side):
                if checked:
                    sc = getattr(self, f"{s}_star_count", 0)
                    lo, hi = self.IV_RANGES[sc]
                    sp.setEnabled(True)
                    sp.setRange(lo, hi)
                    sp.setValue(lo)
                else:
                    sp.setRange(0, 60)
                    sp.setValue(0)
                    sp.setEnabled(False)
                self._limit_iv_count(s)
                self.calculate_stats(s)

            iv_check.stateChanged.connect(_on_check)
        setattr(self, f"{side}_race_inputs", race_inputs)
        setattr(self, f"{side}_iv_inputs", iv_inputs)
        setattr(self, f"{side}_iv_checks", iv_checks)
        lay.addWidget(iv_group)

        lay.addWidget(self._section_label("性格"))
        nature_combo = QComboBox()
        nature_combo.addItem("无性格加成")
        for n in self.natures.keys():
            nature_combo.addItem(n, n)
        nature_combo.setFixedHeight(30)
        nature_combo.setStyleSheet(_input_style().replace(
            "QSpinBox, QComboBox, QLineEdit", "QComboBox"))
        nature_combo.currentIndexChanged.connect(lambda _: self.calculate_stats(side))
        setattr(self, f"{side}_nature", nature_combo)
        self._update_nature_display(side)
        lay.addWidget(nature_combo)

        lay.addWidget(self._section_label("技能栏位（点击选中）"))
        slot_vbox = QVBoxLayout()
        slot_vbox.setSpacing(5)
        slots = []
        for i in range(4):
            slot = SkillSlotWidget(i)
            slot.clicked.connect(lambda idx, s=side: self.on_slot_selected(idx, s))
            slot_vbox.addWidget(slot)
            slots.append(slot)
        slots_container = QWidget()
        slots_container.setStyleSheet("background: transparent; border: none;")
        slots_container.setLayout(slot_vbox)
        setattr(self, f"{side}_skill_slots", slots)
        setattr(self, f"{side}_skills", [None, None, None, None])  # skill data
        setattr(self, f"{side}_selected_slot", 0)
        lay.addWidget(slots_container)

        skill_btn_row = QHBoxLayout()
        skill_btn_row.setSpacing(6)
        pick_btn = QPushButton("选择技能")
        pick_btn.setFixedHeight(30)
        pick_btn.setCursor(Qt.PointingHandCursor)
        pick_btn.setStyleSheet(_gold_btn_style())
        pick_btn.clicked.connect(lambda _, s=side: self.on_pick_skill(s))
        skill_btn_row.addWidget(pick_btn, 1)

        clear_btn = QPushButton("清除")
        clear_btn.setFixedHeight(30)
        clear_btn.setFixedWidth(60)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(_sub_btn_style())
        clear_btn.clicked.connect(lambda _, s=side: self.on_clear_skill(s))
        skill_btn_row.addWidget(clear_btn)
        lay.addLayout(skill_btn_row)

        bonus_group = QGroupBox("战斗加成（攻防等级）")
        bonus_group.setStyleSheet(_group_style())
        bg = QGridLayout(bonus_group)
        bg.setSpacing(5)
        bonus_inputs = {}
        bonus_items = [("攻击提升", "物攻/魔攻 提升 %"), ("攻击下降", "物攻/魔攻 下降 %"),
                       ("防御提升", "物防/魔防 提升 %"), ("防御下降", "物防/魔防 下降 %")]
        for i, (key, desc) in enumerate(bonus_items):
            r = i // 2
            c = (i % 2) * 2
            bg.addWidget(self._plain_label(key), r, c)
            sp = QSpinBox()
            sp.setRange(0, 500)
            sp.setSuffix("%")
            sp.setFixedHeight(26)
            sp.setFixedWidth(80)
            sp.setStyleSheet(_input_style())
            sp.valueChanged.connect(lambda _, s=side: self.refresh_all_damage(s))
            bg.addWidget(sp, r, c + 1)
            bonus_inputs[key] = sp
        setattr(self, f"{side}_bonus", bonus_inputs)
        lay.addWidget(bonus_group)

        skill_adj_group = QGroupBox("技能威力调整")
        skill_adj_group.setStyleSheet(_group_style())
        sg2 = QGridLayout(skill_adj_group)
        sg2.setSpacing(5)
        skill_adj = {}
        adj_items = [("技能威力", "基础威力+固定值", 0, 200),
                     ("本次技能威力", "本次技能威力 %", 0, 500),
                     ("威力加成", "其他威力乘区 %", 0, 500),
                     ("连击数", "本技能连击次数", 1, 10),
                     ("条件伤害", "最终伤害 %", 0, 500),
                     ("印记层数", "星陨印记·额外幻伤", 0, 30)]
        suffix_map = {"技能威力": "", "本次技能威力": "%", "威力加成": "%",
                      "连击数": " 击", "条件伤害": "%", "印记层数": " 层"}
        for i, (key, desc, lo, hi) in enumerate(adj_items):
            sg2.addWidget(self._plain_label(key), i, 0)
            sp = QSpinBox()
            sp.setRange(lo, hi)
            sp.setSuffix(suffix_map.get(key, ""))
            sp.setFixedHeight(26)
            sp.setFixedWidth(90)
            sp.setStyleSheet(_input_style())
            sp.valueChanged.connect(lambda _, s=side: self.refresh_all_damage(s))
            sg2.addWidget(sp, i, 1)
            sg2.addWidget(self._plain_label(desc, mute=True, size=10), i, 2)
            skill_adj[key] = sp
        setattr(self, f"{side}_skill_adj", skill_adj)
        lay.addWidget(skill_adj_group)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        calc_btn = QPushButton("伤害计算")
        calc_btn.setFixedHeight(36)
        calc_btn.setCursor(Qt.PointingHandCursor)
        calc_btn.setStyleSheet(_gold_btn_style())
        calc_btn.clicked.connect(lambda _, s=side: self.on_calculate(s))
        btn_row.addWidget(calc_btn, 1)
        reset_btn = QPushButton("重置")
        reset_btn.setFixedHeight(36)
        reset_btn.setFixedWidth(70)
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setStyleSheet(_sub_btn_style())
        reset_btn.clicked.connect(lambda _, s=side: self.on_reset(s))
        btn_row.addWidget(reset_btn)
        lay.addLayout(btn_row)

        result_box = QGroupBox("计算结果（选中技能）")
        result_box.setStyleSheet(_group_style())
        rl = QVBoxLayout(result_box)
        rl.setSpacing(4)
        result_label = QLabel("选中技能后点击“伤害计算”查看详细分解。")
        result_label.setWordWrap(True)
        result_label.setStyleSheet(_label_style(PALETTE['text_sub'], 12))
        result_label.setTextFormat(Qt.RichText)
        rl.addWidget(result_label)
        setattr(self, f"{side}_result_label", result_label)
        lay.addWidget(result_box)

        hp_container = QWidget()
        hp_container.setVisible(False)
        hp_v = QVBoxLayout(hp_container)
        hp_v.setSpacing(4)
        dmg_lbl = QLabel("")
        dmg_lbl.setAlignment(Qt.AlignCenter)
        dmg_lbl.setStyleSheet(_label_style('#c8463c', 14, True))
        hp_v.addWidget(dmg_lbl)
        hp_bar = QWidget()
        hp_bar.setFixedHeight(22)
        hp_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {PALETTE['bg_inset']};
                border: 1.5px solid {PALETTE['border_dark']};
                border-radius: 5px;
            }}
        """)
        hp_inner = QHBoxLayout(hp_bar)
        hp_inner.setContentsMargins(2, 2, 2, 2)
        hp_inner.setSpacing(0)
        hp_fill = QWidget()
        hp_fill.setStyleSheet("background-color: #5aa05a; border-radius: 3px;")
        hp_inner.addWidget(hp_fill)
        hp_inner.addStretch()
        hp_v.addWidget(hp_bar)
        hp_text = QLabel("")
        hp_text.setAlignment(Qt.AlignCenter)
        hp_text.setStyleSheet(_label_style(PALETTE['text'], 11))
        hp_v.addWidget(hp_text)
        setattr(self, f"{side}_hp_container", hp_container)
        setattr(self, f"{side}_hp_fill", hp_fill)
        setattr(self, f"{side}_damage_label", dmg_lbl)
        setattr(self, f"{side}_hp_text", hp_text)
        lay.addWidget(hp_container)

        lay.addStretch()
        return panel

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"""
            color: {PALETTE['gold_deep']};
            font-size: 12px;
            font-weight: bold;
            background: transparent;
            border: none;
            padding-top: 2px;
        """)
        return lbl

    def _plain_label(self, text, mute=False, size=12):
        c = PALETTE['text_sub'] if mute else PALETTE['text']
        lbl = QLabel(text)
        lbl.setStyleSheet(_label_style(c, size))
        return lbl

    def _make_attr_placeholder(self):
        lbl = QLabel("—")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {PALETTE['bg_inset']};
                color: {PALETTE['text_mute']};
                padding: 6px 10px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid {PALETTE['border_soft']};
            }}
        """)
        return lbl

    def on_sprite_selected(self, sprite, side):
        if side == "sprite1":
            self.sprite1_data = sprite
        else:
            self.sprite2_data = sprite

        attr = sprite.get('attribute', '未知')
        attrs = attr.split('/')
        a1 = getattr(self, f"{side}_attr1")
        a2 = getattr(self, f"{side}_attr2")
        self._set_attr_label(a1, attrs[0] if attrs else '—')
        self._set_attr_label(a2, attrs[1] if len(attrs) > 1 else '—')

        stats = sprite.get('stats', {})
        race = getattr(self, f"{side}_race_inputs")
        race["生命"].setValue(stats.get('hp', 0))
        race["物攻"].setValue(stats.get('attack', 0))
        race["物防"].setValue(stats.get('defense', 0))
        race["魔攻"].setValue(stats.get('magic_attack', 0))
        race["魔防"].setValue(stats.get('magic_defense', 0))
        race["速度"].setValue(stats.get('speed', 0))

        self._build_learnable(sprite, side)

        self.calculate_stats(side)
        self.refresh_all_damage("sprite1")
        self.refresh_all_damage("sprite2")

    def _set_attr_label(self, label, attr_text):
        if not attr_text or attr_text == '—':
            label.setText("—")
            label.setStyleSheet(f"""
                QLabel {{
                    background-color: {PALETTE['bg_inset']};
                    color: {PALETTE['text_mute']};
                    padding: 6px 10px; border-radius: 6px;
                    font-size: 12px; font-weight: bold;
                    border: 1px solid {PALETTE['border_soft']};
                }}
            """)
            return
        short = attr_text.replace('系', '').strip()
        label.setText(short)
        label.setStyleSheet(f"""
            QLabel {{
                background-color: {_type_bg(attr_text)};
                color: white;
                padding: 6px 10px; border-radius: 6px;
                font-size: 12px; font-weight: bold;
            }}
        """)

    def _build_learnable(self, sprite, side):
        skills = sprite.get('skills', {})
        learnable = []
        for sk in skills.get('normal_skills', []):
            learnable.append(dict(sk, _source='默认'))
        for sk in skills.get('bloodline_skills', []):
            learnable.append(dict(sk, _source='血脉'))
        for sk in skills.get('stone_skills', []):
            learnable.append(dict(sk, _source='技能石'))
        self._build_skill_pool_for_pokemon[sprite.get('name', side)] = learnable

    def _get_learnable(self, side):
        sprite = self.sprite1_data if side == "sprite1" else self.sprite2_data
        if not sprite:
            return []
        return self._build_skill_pool_for_pokemon.get(sprite.get('name', side), [])

    def on_pick_skill(self, side):
        idx = getattr(self, f"{side}_selected_slot")
        dlg = SkillSelectionDialog(self._get_learnable(side), self)
        if dlg.exec() == QDialog.Accepted and dlg.selected_skill:
            skill = dlg.selected_skill
            skills = getattr(self, f"{side}_skills")
            slots = getattr(self, f"{side}_skill_slots")
            skills[idx] = skill
            slots[idx].set_skill(skill)
            self.on_slot_selected(idx, side)
            self.refresh_all_damage(side)

    def on_clear_skill(self, side):
        idx = getattr(self, f"{side}_selected_slot")
        skills = getattr(self, f"{side}_skills")
        slots = getattr(self, f"{side}_skill_slots")
        skills[idx] = None
        slots[idx].set_skill(None)
        slots[idx].set_power_and_damage(None, None, 0, 1.0)
        self.refresh_all_damage(side)
        self._update_hp_bar(side, 0, 1)

    def on_slot_selected(self, idx, side):
        setattr(self, f"{side}_selected_slot", idx)
        slots = getattr(self, f"{side}_skill_slots")
        for i, s in enumerate(slots):
            s.set_selected(i == idx)

    def on_level_changed(self, value, side, label):
        setattr(self, f"{side}_level_value", value)
        label.setText(str(value))
        self.calculate_stats(side)
        self.refresh_all_damage(side)

    def on_star_clicked(self, star_index, side):
        cur = getattr(self, f"{side}_star_count")
        new_count = star_index if star_index < cur else star_index + 1
        setattr(self, f"{side}_star_count", new_count)
        self._update_star_display(side)
        self._update_iv_range(side, new_count)
        self._update_nature_display(side)
        self.calculate_stats(side)

    def _update_star_display(self, side):
        count = getattr(self, f"{side}_star_count")
        btns = getattr(self, f"{side}_stars")
        for i, btn in enumerate(btns):
            path = _STAR_GOLD if i < count else _STAR_GRAY
            pm = QPixmap(path)
            if not pm.isNull():
                scaled = _scale_hdpi(pm, 28)
                btn.setIcon(scaled)
                btn.setIconSize(scaled.size())

    def _update_iv_range(self, side, star_count):
        iv_inputs = getattr(self, f"{side}_iv_inputs")
        iv_checks = getattr(self, f"{side}_iv_checks")
        lo, hi = self.IV_RANGES[star_count]
        for name, sp in iv_inputs.items():
            if iv_checks[name].isChecked():
                sp.setRange(lo, hi)
                sp.setValue(lo)
            else:
                sp.setRange(0, 60)
                sp.setValue(0)

    def _limit_iv_count(self, side):
        iv_checks = getattr(self, f"{side}_iv_checks")
        full_iv = getattr(self, f"{side}_full_iv")
        if full_iv.isChecked():
            return
        checked = sum(1 for c in iv_checks.values() if c.isChecked())
        for c in iv_checks.values():
            if c.isChecked():
                c.setEnabled(True)
            else:
                c.setEnabled(checked < 3)

    def on_full_iv_changed(self, side):
        full_iv = getattr(self, f"{side}_full_iv")
        iv_inputs = getattr(self, f"{side}_iv_inputs")
        iv_checks = getattr(self, f"{side}_iv_checks")
        if full_iv.isChecked():
            setattr(self, f"{side}_star_count", 5)
            self._update_star_display(side)
            for name in iv_checks.keys():
                iv_inputs[name].setRange(0, 60)
                if iv_checks[name].isChecked():
                    iv_inputs[name].setValue(60)
                    iv_inputs[name].setEnabled(False)
                else:
                    iv_checks[name].setEnabled(False)
                    iv_inputs[name].setEnabled(False)
        else:
            setattr(self, f"{side}_star_count", 0)
            self._update_star_display(side)
            for name in iv_checks.keys():
                iv_checks[name].setEnabled(True)
            for name, sp in iv_inputs.items():
                if iv_checks[name].isChecked():
                    sp.setValue(7)
                    sp.setEnabled(True)
                else:
                    sp.setValue(0)
                    sp.setEnabled(False)
            self._limit_iv_count(side)
        self._update_nature_display(side)
        self.calculate_stats(side)

    def _update_nature_display(self, side):
        combo = getattr(self, f"{side}_nature")
        star = getattr(self, f"{side}_star_count")
        cur = combo.currentIndex()
        combo.clear()
        combo.addItem("无性格加成")
        for n in self.natures.keys():
            info = self.natures[n]
            bs, bv = info['boost']
            rs, rv = info['reduce']
            actual_bv = bv + star * 2
            combo.addItem(f"{n} ({bs}+{actual_bv}%, {rs}-{rv}%)", n)
        if cur > 0 and cur < combo.count():
            combo.setCurrentIndex(cur)

    def calculate_stats(self, side):
        sprite = self.sprite1_data if side == "sprite1" else self.sprite2_data
        if not sprite:
            return
        level = getattr(self, f"{side}_level_value")
        star = getattr(self, f"{side}_star_count")
        race = getattr(self, f"{side}_race_inputs")
        iv_inputs = getattr(self, f"{side}_iv_inputs")
        iv_checks = getattr(self, f"{side}_iv_checks")
        nature_combo = getattr(self, f"{side}_nature")
        full_iv = getattr(self, f"{side}_full_iv")

        b_hp = race["生命"].value()
        b_atk = race["物攻"].value()
        b_def = race["物防"].value()
        b_matk = race["魔攻"].value()
        b_mdef = race["魔防"].value()
        b_spd = race["速度"].value()

        effort_hp = star * 20
        effort_other = star * 10

        def get_iv(name):
            if iv_checks[name].isChecked():
                return iv_inputs[name].value()
            return 0

        iv_hp = get_iv("生命")
        iv_atk = get_iv("物攻")
        iv_def = get_iv("物防")
        iv_matk = get_iv("魔攻")
        iv_mdef = get_iv("魔防")
        iv_spd = get_iv("速度")

        if full_iv.isChecked():
            if iv_checks["生命"].isChecked(): iv_hp = 60
            if iv_checks["物攻"].isChecked(): iv_atk = 60
            if iv_checks["物防"].isChecked(): iv_def = 60
            if iv_checks["魔攻"].isChecked(): iv_matk = 60
            if iv_checks["魔防"].isChecked(): iv_mdef = 60
            if iv_checks["速度"].isChecked(): iv_spd = 60

        eff_hp = b_hp + iv_hp / 2
        eff_atk = b_atk + iv_atk / 2
        eff_def = b_def + iv_def / 2
        eff_matk = b_matk + iv_matk / 2
        eff_mdef = b_mdef + iv_mdef / 2
        eff_spd = b_spd + iv_spd / 2

        nb_stat, nb_val = None, 0
        nr_stat, nr_val = None, 0
        ni = nature_combo.currentIndex()
        if ni > 0:
            nname = nature_combo.itemData(ni)
            if nname and nname in self.natures:
                info = self.natures[nname]
                nb_stat, base_bv = info['boost']
                nr_stat, nr_val = info['reduce']
                nb_val = base_bv + star * 2

        def nmult(name):
            if nb_stat == name:
                return 1 + nb_val / 100
            if nr_stat == name:
                return 1 - nr_val / 100
            return 1.0

        hp_base = round(eff_hp * (2 * level + 50) / 100) + level + 10
        hp_final = round(hp_base * nmult("生命")) + effort_hp

        def calc_non(eff, effort, name):
            base = round(eff * (level + 50) / 100) + 10
            return round(base * nmult(name)) + effort

        atk = calc_non(eff_atk, effort_other, "物攻")
        df = calc_non(eff_def, effort_other, "物防")
        matk = calc_non(eff_matk, effort_other, "魔攻")
        mdf = calc_non(eff_mdef, effort_other, "魔防")
        spd = calc_non(eff_spd, effort_other, "速度")

        computed = {'生命': hp_final, '物攻': atk, '物防': df,
                    '魔攻': matk, '魔防': mdf, '速度': spd}
        setattr(self, f"{side}_computed_stats", computed)

        labels = getattr(self, f"{side}_stat_labels", {})
        if labels:
            for k, v in computed.items():
                labels[k].setText(f"{k}: {v}")

    def get_type_multiplier(self, skill_attr, target_sprite):
        if not skill_attr or not target_sprite:
            return 1.0
        skill_short = skill_attr.replace('系', '').strip()
        target_attr = target_sprite.get('attribute', '')
        target_attrs = [a.strip().replace('系', '') for a in target_attr.split('/')]
        weak = 0
        resist = 0
        for t in target_attrs:
            t_with = t + '系'
            s_with = skill_short + '系'
            if s_with in self.effectiveness.get(t_with, {}).get('defense_2x', []):
                weak += 1
            elif s_with in self.effectiveness.get(t_with, {}).get('defense_0.5x', []):
                resist += 1
        if weak == 0 and resist == 0:
            return 1.0
        if weak == 1 and resist == 0:
            return 2.0
        if weak == 2 and resist == 0:
            return 3.0
        if weak == 0 and resist >= 1:
            return 0.5
        if weak == 1 and resist == 1:
            return 1.0
        return 1.0

    def _compute_breakdown(self, attacker_side, skill):
        """返回完整分解 dict，无法计算时返回 None。"""
        defender_side = "sprite2" if attacker_side == "sprite1" else "sprite1"
        attacker = self.sprite1_data if attacker_side == "sprite1" else self.sprite2_data
        defender = self.sprite2_data if defender_side == "sprite2" else self.sprite1_data
        if not attacker or not defender or not skill:
            return None

        raw_power = skill.get('power', 0)
        try:
            base_power = int(raw_power)
        except (ValueError, TypeError):
            base_power = 0
        if base_power <= 0:
            return None  # 状态/防御技不造成伤害

        adj = getattr(self, f"{attacker_side}_skill_adj")
        fixed_bonus = adj["技能威力"].value()
        skill_power_pct = adj["本次技能威力"].value() / 100.0
        effective_power = (base_power + fixed_bonus) * (1 + skill_power_pct)

        skill_attr = skill.get('attribute', '')
        atk_attr = attacker.get('attribute', '')
        atk_attrs = [a.strip().replace('系', '') for a in atk_attr.split('/')]
        same_type = 1.25 if skill_attr.replace('系', '').strip() in atk_attrs else 1.0

        type_mult = self.get_type_multiplier(skill_attr, defender)

        bonus = getattr(self, f"{attacker_side}_bonus")
        def_bonus = getattr(self, f"{defender_side}_bonus")
        atk_up = bonus["攻击提升"].value() / 100.0
        atk_down = bonus["攻击下降"].value() / 100.0
        def_up = def_bonus["防御提升"].value() / 100.0
        def_down = def_bonus["防御下降"].value() / 100.0
        numerator = 1 + atk_up + def_down
        denominator = 1 + atk_down + def_up
        atk_def_level = numerator / denominator if denominator > 0 else numerator

        other_mult = 1 + adj["威力加成"].value() / 100.0

        display_power = round(effective_power * same_type * type_mult
                              * atk_def_level * other_mult)

        dmg_type = skill.get('type', '')
        atk_stats = getattr(self, f"{attacker_side}_computed_stats", {})
        def_stats = getattr(self, f"{defender_side}_computed_stats", {})
        if not atk_stats or not def_stats:
            return None
        if dmg_type == '物攻':
            attack_val = atk_stats.get('物攻', 0)
            defense_val = def_stats.get('物防', 0)
        elif dmg_type == '魔攻':
            attack_val = atk_stats.get('魔攻', 0)
            defense_val = def_stats.get('魔防', 0)
        else:
            return None  # 状态/防御技能
        if defense_val <= 0:
            return None

        level = getattr(self, f"{attacker_side}_level_value")
        level_coeff = (level * 45 / 100 + 10) / 41.0

        final_mult = 1 + adj["条件伤害"].value() / 100.0
        combo = adj["连击数"].value()

        raw = round(attack_val * display_power * level_coeff)
        main_damage = math.floor(raw / defense_val) * final_mult * combo
        main_damage = int(main_damage)

        mark_layers = adj["印记层数"].value()
        mark_extra = 0
        mark_type_mult = 1.0
        if mark_layers > 0:
            atk_phys = atk_stats.get('物攻', 0)
            atk_mag = atk_stats.get('魔攻', 0)
            if atk_phys >= atk_mag:
                mark_atk, mark_def = atk_phys, def_stats.get('物防', 0)
            else:
                mark_atk, mark_def = atk_mag, def_stats.get('魔防', 0)
            mark_type_mult = self.get_type_multiplier('幻系', defender)
            mark_display = round(mark_layers * 30 * mark_type_mult)
            if mark_def > 0:
                mark_raw = round(mark_atk * mark_display * level_coeff)
                mark_extra = math.floor(mark_raw / mark_def)
        damage = main_damage + mark_extra

        max_hp = def_stats.get('生命', 0)
        pct = (damage / max_hp * 100) if max_hp > 0 else 0.0

        return {
            'base_power': base_power, 'fixed_bonus': fixed_bonus,
            'skill_power_pct': skill_power_pct, 'effective_power': effective_power,
            'same_type': same_type, 'type_mult': type_mult,
            'atk_def_level': atk_def_level, 'other_mult': other_mult,
            'display_power': display_power, 'dmg_type': dmg_type,
            'attack_val': attack_val, 'defense_val': defense_val,
            'level': level, 'level_coeff': level_coeff,
            'final_mult': final_mult, 'combo': combo,
            'main_damage': main_damage, 'mark_layers': mark_layers,
            'mark_extra': mark_extra, 'mark_type_mult': mark_type_mult,
            'damage': damage, 'max_hp': max_hp, 'pct': pct,
            'defender_side': defender_side,
        }

    def refresh_all_damage(self, side):
        """刷新某侧四个栏位的伤害显示（不影响对方血条）。"""
        slots = getattr(self, f"{side}_skill_slots", [])
        skills = getattr(self, f"{side}_skills", [])
        defender_side = "sprite2" if side == "sprite1" else "sprite1"
        defender = self.sprite2_data if defender_side == "sprite2" else self.sprite1_data
        for i, slot in enumerate(slots):
            sk = skills[i] if i < len(skills) else None
            if not sk or not defender:
                slot.set_power_and_damage(None, None, 0, 1.0)
                continue
            br = self._compute_breakdown(side, sk)
            if not br:
                slot.set_power_and_damage(None, None, 0, 1.0)
                continue
            slot.set_power_and_damage(br['display_power'], br['damage'],
                                      br['pct'], br['type_mult'])

    def on_calculate(self, side):
        idx = getattr(self, f"{side}_selected_slot")
        skills = getattr(self, f"{side}_skills", [])
        sk = skills[idx] if idx < len(skills) else None
        result_label = getattr(self, f"{side}_result_label")
        if not sk:
            result_label.setText("请先选择技能再计算。")
            return
        br = self._compute_breakdown(side, sk)
        if not br:
            result_label.setText("该技能不造成伤害（状态/防御类），或双方信息不完整。")
            return

        kill = "斩杀 ✓" if br['damage'] >= br['max_hp'] else "未斩杀"
        kill_color = '#c8463c' if br['damage'] >= br['max_hp'] else PALETTE['text_sub']
        mark_line = ""
        if br.get('mark_layers', 0) > 0:
            mark_line = (f"<span style='color:{PALETTE['text_sub']}'>星陨印记：</span>"
                         f"{br['mark_layers']}层 × 30威力 × 幻系克制{br['mark_type_mult']}"
                         f" → 额外幻伤 <b style='color:#7a5ad6;'>+{br['mark_extra']}</b><br>")
        combo_txt = f" × {br['combo']}" if br.get('combo', 1) > 1 else ""
        html = f"""
        <div style='color:{PALETTE['text']}; font-size:12px; line-height:1.6;'>
          <b style='color:{PALETTE['gold_deep']}; font-size:13px;'>{sk.get('name','')} → {br['dmg_type']}技能</b><br>
          <span style='color:{PALETTE['text_sub']}'>基础威力区：</span>
            ({br['base_power']} + {br['fixed_bonus']}) × (1 + {br['skill_power_pct']*100:.0f}%)
            = <b>{br['effective_power']:.1f}</b> <span style='color:{PALETTE['text_mute']}'>有效威力</span><br>
          <span style='color:{PALETTE['text_sub']}'>显示威力区：</span>
            {br['effective_power']:.1f} × 本系{br['same_type']} × 克制{br['type_mult']}
            × 攻防等级{br['atk_def_level']:.3f} × 威力加成{br['other_mult']:.2f}
            = <b style='color:{PALETTE['gold_deep']}'>{br['display_power']}</b><br>
          <span style='color:{PALETTE['text_sub']}'>攻防数值：</span>
            攻击 {br['attack_val']} / 防御 {br['defense_val']}（{br['dmg_type']}通道）<br>
          <span style='color:{PALETTE['text_sub']}'>等级系数：</span>
            ({br['level']}×45/100+10)/41 ≈ <b>{br['level_coeff']:.4f}</b><br>
          <span style='color:{PALETTE['text_sub']}'>技能伤害：</span>
            floor(round({br['attack_val']}×{br['display_power']}×{br['level_coeff']:.4f})÷{br['defense_val']})
            × {br['final_mult']}{combo_txt} = <b style='color:#c8463c;'>{br['main_damage']}</b><br>
          {mark_line}
          <span style='color:{PALETTE['text_sub']}'>预计总伤害：</span>
            <b style='color:#c8463c; font-size:15px;'>{br['damage']}</b>
            <span style='color:{PALETTE['text_mute']};font-size:10px;'>(技能{br['main_damage']}+印记{br['mark_extra']})</span><br>
          <span style='color:{PALETTE['text_sub']}'>占敌方生命：</span>
            <b style='color:#c8463c;'>{br['pct']:.1f}%</b>
            <span style='color:{kill_color};'>({kill})</span>
        </div>
        """
        result_label.setText(html)

        self._update_hp_bar(br['defender_side'], br['damage'], br['max_hp'])

    def _update_hp_bar(self, side, damage, max_hp):
        container = getattr(self, f"{side}_hp_container", None)
        if container is None:
            return
        if max_hp <= 0:
            container.setVisible(False)
            return
        container.setVisible(True)
        fill = getattr(self, f"{side}_hp_fill")
        dmg_lbl = getattr(self, f"{side}_damage_label")
        hp_text = getattr(self, f"{side}_hp_text")
        remaining = max(0, max_hp - damage)
        pct = remaining / max_hp * 100 if max_hp > 0 else 0
        dmg_lbl.setText(f"受到 {damage} 点伤害（{damage/max_hp*100 if max_hp>0 else 0:.1f}%）")
        hp_text.setText(f"剩余 {remaining} / {max_hp}（{pct:.1f}%）")
        if pct > 50:
            color = '#5aa05a'
        elif pct > 20:
            color = '#e0b341'
        else:
            color = '#c8463c'
        fill.setStyleSheet(f"background-color: {color}; border-radius: 3px;")
        QTimer.singleShot(0, lambda: self._resize_hp_fill(fill, pct))

    def _resize_hp_fill(self, fill, pct):
        parent = fill.parentWidget()
        if parent is None:
            return
        total = parent.width() - 4
        fill.setFixedWidth(max(int(total * pct / 100), 0))

    def on_reset(self, side):
        if side == "sprite1":
            self.sprite1_data = None
        else:
            self.sprite2_data = None
        sb = getattr(self, f"{side}_search_box")
        sb.clear_text()
        self._set_attr_label(getattr(self, f"{side}_attr1"), '—')
        self._set_attr_label(getattr(self, f"{side}_attr2"), '—')
        getattr(self, f"{side}_level_slider").setValue(60)
        getattr(self, f"{side}_level_value_label").setText("60")
        setattr(self, f"{side}_level_value", 60)
        setattr(self, f"{side}_star_count", 0)
        self._update_star_display(side)
        getattr(self, f"{side}_full_iv").setChecked(False)
        iv_checks = getattr(self, f"{side}_iv_checks")
        iv_inputs = getattr(self, f"{side}_iv_inputs")
        for name in iv_checks.keys():
            iv_checks[name].setChecked(False)
            iv_checks[name].setEnabled(True)
            iv_inputs[name].setValue(0)
            iv_inputs[name].setEnabled(False)
            iv_inputs[name].setRange(0, 60)
        for sp in getattr(self, f"{side}_race_inputs").values():
            sp.setValue(0)
        getattr(self, f"{side}_nature").setCurrentIndex(0)
        self._update_nature_display(side)
        skills = getattr(self, f"{side}_skills")
        slots = getattr(self, f"{side}_skill_slots")
        for i in range(4):
            skills[i] = None
            slots[i].set_skill(None)
            slots[i].set_power_and_damage(None, None, 0, 1.0)
            slots[i].set_selected(i == 0)
        setattr(self, f"{side}_selected_slot", 0)
        for sp in getattr(self, f"{side}_bonus").values():
            sp.setValue(0)
        for sp in getattr(self, f"{side}_skill_adj").values():
            sp.setValue(0)
        for lbl in getattr(self, f"{side}_stat_labels", {}).values():
            lbl.setText(f"{lbl.text().split(':')[0]}: -")
        setattr(self, f"{side}_computed_stats", {})
        getattr(self, f"{side}_result_label").setText(
            "选中技能后点击“伤害计算”查看详细分解。")
        getattr(self, f"{side}_hp_container").setVisible(False)
        self.refresh_all_damage("sprite1")
        self.refresh_all_damage("sprite2")
