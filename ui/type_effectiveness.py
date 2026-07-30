"""
属性克制表界面 — 童话风重绘
图标+属性名称显示克制关系
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QScrollArea, QFrame, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
import os
import re

# ── 调色板（与精灵图鉴一致）──
PALETTE = {
    'bg_top':       '#f7eed8',
    'bg_bottom':    '#ece0c2',
    'bg_card':      '#fffaf0',
    'bg_card_alt':  '#fbf3e3',
    'bg_inset':     '#f0e4cc',
    'bg_hover':     '#fff5dc',
    'border':       '#d8c19a',
    'border_dark':  '#b89a6e',
    'border_soft':  '#e6d4b0',
    'text':         '#3d2f1f',
    'text_sub':     '#7a6650',
    'text_mute':    '#a08d75',
    'text_on_gold': '#5a4216',
    'gold':         '#c9a96e',
    'gold_deep':    '#a8853d',
    'gold_light':   '#e6c98a',
}

# 属性颜色（用于图标背景圆圈）
ATTR_COLORS = {
    '草系':   '#5ac85a',
    '火系':   '#e85a3c',
    '水系':   '#3c9ae8',
    '光系':   '#e8c83c',
    '地系':   '#c89856',
    '冰系':   '#6cc8e8',
    '龙系':   '#a86ce8',
    '电系':   '#f0d040',
    '毒系':   '#a85ac8',
    '虫系':   '#a8c85a',
    '武系':   '#e8783c',
    '翼系':   '#9aa8e8',
    '萌系':   '#e88ac8',
    '幽系':   '#7a5ac8',
    '恶系':   '#5a3c5a',
    '普系':   '#a89878',
    '幻系':   '#c86ce8',
    '机械系': '#9aa8b8',
}

# 图标文件名别名
_ATTR_ICON_ALIASES = {
    '翼': '飞行',
    '普': '普通',
}

_SC_SC_DIR = os.path.join(os.path.dirname(__file__), "..", "image", "sc", "sc")
_icon_cache = {}


def _load_attr_icon(attr_name, size=20):
    """加载属性图标 QPixmap"""
    if not attr_name:
        return None
    short = attr_name.replace('系', '').strip()
    alias = _ATTR_ICON_ALIASES.get(short, short)
    key = (short, size)
    if key in _icon_cache:
        return _icon_cache[key]
    pm = None
    # 尝试多种文件名：短名、带系后缀、别名
    for fname in [f"{short}.png", f"{short}系.png", f"{alias}.png", f"{alias}系.png"]:
        path = os.path.join(_SC_SC_DIR, fname)
        if os.path.exists(path):
            raw = QPixmap(path)
            if not raw.isNull():
                pm = raw.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                break
    _icon_cache[key] = pm
    return pm


def _attr_short(attr_name):
    """获取属性简称（去'系'后缀）"""
    return attr_name.replace('系', '').strip()


class AttrPill(QFrame):
    """属性胶囊：图标+名称"""
    def __init__(self, attr_name, icon_size=18, font_size=12, parent=None):
        super().__init__(parent)
        self.attr_name = attr_name
        short = _attr_short(attr_name)
        color = ATTR_COLORS.get(attr_name, '#888888')

        self.setFrameShape(QFrame.NoFrame)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 14px;
                outline: none;
            }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 10, 4)
        lay.setSpacing(5)

        # 图标
        pm = _load_attr_icon(attr_name, icon_size)
        if pm and not pm.isNull():
            icon_lbl = QLabel()
            icon_lbl.setPixmap(pm)
            icon_lbl.setFixedSize(icon_size, icon_size)
            icon_lbl.setStyleSheet("background: transparent; border: none;")
            icon_lbl.setAlignment(Qt.AlignCenter)
            lay.addWidget(icon_lbl)

        # 名称
        name_lbl = QLabel(attr_name)
        name_lbl.setStyleSheet(
            f"color: white; font-size: {font_size}px; font-weight: bold;"
            f" background: transparent; border: none;"
        )
        lay.addWidget(name_lbl)


class AttrCard(QFrame):
    """属性卡片：大图标+名称+倍率，用于克制关系展示"""
    def __init__(self, attr_name, multiplier=None, icon_size=36, parent=None):
        super().__init__(parent)
        self.attr_name = attr_name
        color = ATTR_COLORS.get(attr_name, '#888888')

        self.setFixedSize(90, 100)
        self.setFrameShape(QFrame.NoFrame)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-top: 3px solid {color};
                border-radius: 10px;
                outline: none;
            }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 8, 6, 6)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignCenter)

        # 图标（带属性色背景圆）
        icon_bg = QFrame()
        icon_bg.setFixedSize(icon_size + 8, icon_size + 8)
        icon_bg.setFrameShape(QFrame.NoFrame)
        icon_bg.setAttribute(Qt.WA_StyledBackground, True)
        icon_bg.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: {(icon_size + 8) // 2}px;
            }}
        """)
        icon_lay = QHBoxLayout(icon_bg)
        icon_lay.setContentsMargins(0, 0, 0, 0)
        icon_lay.setAlignment(Qt.AlignCenter)

        pm = _load_attr_icon(attr_name, icon_size)
        if pm and not pm.isNull():
            icon_lbl = QLabel()
            icon_lbl.setPixmap(pm)
            icon_lbl.setFixedSize(icon_size, icon_size)
            icon_lbl.setStyleSheet("background: transparent; border: none;")
            icon_lbl.setAlignment(Qt.AlignCenter)
            icon_lay.addWidget(icon_lbl)
        lay.addWidget(icon_bg, alignment=Qt.AlignCenter)

        # 名称
        name_lbl = QLabel(attr_name)
        name_lbl.setStyleSheet(f"""
            color: {PALETTE['text']};
            font-size: 12px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        name_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(name_lbl)

        # 倍率
        if multiplier:
            mult_color = '#c8463c' if multiplier >= 2 else '#3c9a5a'
            mult_lbl = QLabel(f"×{multiplier:.1f}" if multiplier != 3.0 else "×3.0")
            mult_lbl.setStyleSheet(f"""
                color: white;
                background-color: {mult_color};
                padding: 1px 8px;
                border-radius: 8px;
                font-size: 10px;
                font-weight: bold;
            """)
            mult_lbl.setAlignment(Qt.AlignCenter)
            lay.addWidget(mult_lbl, alignment=Qt.AlignCenter)


class AttrButton(QPushButton):
    """属性选择按钮：图标+名称"""
    def __init__(self, attr_name, icon_size=28, parent=None):
        super().__init__(parent)
        self.attr_name = attr_name
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(90, 70)

        short = _attr_short(attr_name)
        color = ATTR_COLORS.get(attr_name, '#888888')

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(5)
        lay.setAlignment(Qt.AlignCenter)

        # 图标
        pm = _load_attr_icon(attr_name, icon_size)
        if pm and not pm.isNull():
            icon_lbl = QLabel()
            icon_lbl.setPixmap(pm)
            icon_lbl.setFixedSize(icon_size, icon_size)
            icon_lbl.setStyleSheet("background: transparent; border: none;")
            icon_lbl.setAlignment(Qt.AlignCenter)
            lay.addWidget(icon_lbl)

        # 名称
        name_lbl = QLabel(attr_name)
        name_lbl.setStyleSheet(
            f"color: {PALETTE['text']}; font-size: 12px; font-weight: 600;"
            f" background: transparent; border: none;"
        )
        lay.addWidget(name_lbl)

        self._color = color
        self._update_style(False)

    def _update_style(self, selected):
        if selected:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self._color};
                    border: 2px solid {PALETTE['gold_deep']};
                    border-radius: 12px;
                    outline: none;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PALETTE['bg_card']};
                    border: 1px solid {PALETTE['border']};
                    border-radius: 12px;
                    outline: none;
                }}
                QPushButton:hover {{
                    border: 2px solid {self._color};
                    background-color: {PALETTE['bg_hover']};
                }}
            """)

    def set_selected(self, selected):
        self.setChecked(selected)
        self._update_style(selected)


class TypeEffectivenessWidget(QWidget):
    """属性克制表界面 — 童话风"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.effectiveness_data = {}
        self.selected_attrs = []  # 最多2个
        self.attr_buttons = {}    # attr_name -> AttrButton
        self.load_type_data()
        self.setup_ui()

    # ── 数据加载（保持原有逻辑）──

    def load_type_data(self):
        """加载属性克制数据"""
        base_dir = os.path.join(os.path.dirname(__file__), '..')
        type_file = os.path.join(base_dir, '克制.txt')
        with open(type_file, 'r', encoding='utf-8') as f:
            content = f.read()

        all_types = ['草', '火', '水', '光', '地', '冰', '龙', '电', '毒',
                     '虫', '武', '翼', '萌', '幽', '恶', '普', '幻', '机械']

        for attr in all_types:
            self.effectiveness_data[attr + '系'] = {
                'attack_2x': [], 'attack_0.5x': [],
                'defense_2x': [], 'defense_0.5x': []
            }

        current_attr = None
        section = None
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            attr_match = re.match(r'Step\d+：(\w+)系', line)
            if attr_match:
                current_attr = attr_match.group(1) + '系'
                section = None
                continue
            if '作为攻击方' in line:
                section = 'attack'
                continue
            elif '作为被攻击方' in line:
                section = 'defense'
                continue
            if current_attr and section:
                if section == 'attack' and '0.5倍' in line:
                    match = re.search(r'对(.+?)系造成0\.5倍伤害', line)
                    if match:
                        attrs = [a.strip() + '系' for a in match.group(1).split('/')]
                        self.effectiveness_data[current_attr]['attack_0.5x'] = attrs
                elif section == 'attack' and '2倍' in line:
                    match = re.search(r'对(.+?)系造成2倍伤害', line)
                    if match:
                        attrs = [a.strip() + '系' for a in match.group(1).split('/')]
                        self.effectiveness_data[current_attr]['attack_2x'] = attrs
                elif section == 'defense' and '0.5倍' in line:
                    match = re.search(r'受到(.+?)系的0\.5倍伤害', line)
                    if match:
                        attrs = [a.strip() + '系' for a in match.group(1).split('/')]
                        self.effectiveness_data[current_attr]['defense_0.5x'] = attrs
                elif section == 'defense' and '2倍' in line:
                    match = re.search(r'受到(.+?)系的2倍伤害', line)
                    if match:
                        attrs = [a.strip() + '系' for a in match.group(1).split('/')]
                        self.effectiveness_data[current_attr]['defense_2x'] = attrs

    # ── UI 构建 ──

    def setup_ui(self):
        """初始化UI"""
        # 羊皮纸渐变背景
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {PALETTE['bg_top']},
                    stop:1 {PALETTE['bg_bottom']}
                );
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 24, 30, 24)
        main_layout.setSpacing(16)

        # ── 标题区 ──
        title = QLabel("属 性 克 制 表")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"""
            color: {PALETTE['gold_deep']};
            font-size: 26px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        main_layout.addWidget(title)

        subtitle = QLabel("点击属性图标查看克制关系  ·  可选择1~2个属性")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"""
            color: {PALETTE['text_mute']};
            font-size: 12px;
            background: transparent;
            border: none;
        """)
        main_layout.addWidget(subtitle)

        # ── 属性选择网格 ──
        select_card = QFrame()
        select_card.setFrameShape(QFrame.NoFrame)
        select_card.setAttribute(Qt.WA_StyledBackground, True)
        select_card.setStyleSheet(f"""
            QFrame {{
                background-color: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 14px;
            }}
        """)
        select_lay = QVBoxLayout(select_card)
        select_lay.setContentsMargins(16, 14, 16, 14)
        select_lay.setSpacing(10)

        select_title = QLabel("选择属性")
        select_title.setStyleSheet(f"""
            color: {PALETTE['text']};
            font-size: 14px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        select_lay.addWidget(select_title)

        grid = QGridLayout()
        grid.setSpacing(8)
        all_attrs = sorted(self.effectiveness_data.keys())
        for i, attr in enumerate(all_attrs):
            btn = AttrButton(attr, icon_size=24)
            btn.clicked.connect(lambda checked, a=attr: self._on_attr_clicked(a))
            self.attr_buttons[attr] = btn
            grid.addWidget(btn, i // 6, i % 6)
        select_lay.addLayout(grid)

        main_layout.addWidget(select_card)

        # ── 已选属性栏 ──
        self.selected_bar = QFrame()
        self.selected_bar.setFrameShape(QFrame.NoFrame)
        self.selected_bar.setAttribute(Qt.WA_StyledBackground, True)
        self.selected_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {PALETTE['bg_inset']};
                border: 1px solid {PALETTE['border_soft']};
                border-radius: 10px;
            }}
        """)
        self.selected_bar_lay = QHBoxLayout(self.selected_bar)
        self.selected_bar_lay.setContentsMargins(16, 8, 16, 8)
        self.selected_bar_lay.setSpacing(10)

        sel_label = QLabel("已选：")
        sel_label.setStyleSheet(f"color: {PALETTE['text_sub']}; font-size: 13px; font-weight: 600; background: transparent; border: none;")
        self.selected_bar_lay.addWidget(sel_label)

        self.selected_display = QLabel("（请点击上方属性）")
        self.selected_display.setStyleSheet(f"color: {PALETTE['text_mute']}; font-size: 13px; background: transparent; border: none;")
        self.selected_bar_lay.addWidget(self.selected_display)
        self.selected_bar_lay.addStretch()

        self.clear_btn = QPushButton("清除选择")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setFixedHeight(28)
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PALETTE['bg_card']};
                color: {PALETTE['text_sub']};
                border: 1px solid {PALETTE['border']};
                border-radius: 8px;
                font-size: 12px;
                padding: 0 12px;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {PALETTE['gold_light']};
                color: {PALETTE['text_on_gold']};
            }}
        """)
        self.clear_btn.clicked.connect(self._clear_selection)
        self.selected_bar_lay.addWidget(self.clear_btn)

        main_layout.addWidget(self.selected_bar)

        # ── 结果区域（滚动）──
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: rgba(180, 150, 100, 0.10);
                width: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 252, 245, 0.85);
                border: 1px solid rgba(180, 140, 70, 0.35);
                border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(180, 140, 70, 0.5);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self.result_container = QWidget()
        self.result_container.setStyleSheet("background: transparent; border: none;")
        self.result_layout = QVBoxLayout(self.result_container)
        self.result_layout.setContentsMargins(0, 4, 0, 4)
        self.result_layout.setSpacing(14)

        self.scroll.setWidget(self.result_container)
        main_layout.addWidget(self.scroll, 1)

        self._show_placeholder()

    # ── 交互逻辑 ──

    def _on_attr_clicked(self, attr):
        """属性按钮点击：最多选2个"""
        if attr in self.selected_attrs:
            # 取消选择
            self.selected_attrs.remove(attr)
            self.attr_buttons[attr].set_selected(False)
        else:
            if len(self.selected_attrs) >= 2:
                # 替换第一个
                old = self.selected_attrs.pop(0)
                self.attr_buttons[old].set_selected(False)
            self.selected_attrs.append(attr)
            self.attr_buttons[attr].set_selected(True)
        self._update_display()

    def _clear_selection(self):
        for attr in self.selected_attrs:
            self.attr_buttons[attr].set_selected(False)
        self.selected_attrs.clear()
        self._update_display()

    def _update_display(self):
        """更新已选栏和结果区"""
        # 更新已选栏
        if not self.selected_attrs:
            self.selected_display.setText("（请点击上方属性）")
            self.selected_display.setStyleSheet(f"color: {PALETTE['text_mute']}; font-size: 13px; background: transparent; border: none;")
        else:
            pills_text = "  +  ".join(self.selected_attrs)
            self.selected_display.setText(pills_text)
            self.selected_display.setStyleSheet(f"color: {PALETTE['text']}; font-size: 14px; font-weight: bold; background: transparent; border: none;")

        # 更新结果
        self._clear_result()
        if not self.selected_attrs:
            self._show_placeholder()
            return

        if len(self.selected_attrs) == 1:
            self._show_single(self.selected_attrs[0])
        else:
            self._show_dual(self.selected_attrs[0], self.selected_attrs[1])

        self.result_layout.addStretch()

    def _show_placeholder(self):
        placeholder = QLabel("点击上方属性图标，查看克制关系")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet(f"""
            color: {PALETTE['text_mute']};
            font-size: 15px;
            padding: 50px;
            background: transparent;
            border: none;
        """)
        self.result_layout.addWidget(placeholder)

    def _clear_result(self):
        while self.result_layout.count():
            item = self.result_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ── 结果展示 ──

    def _make_section(self, icon, title, desc, attr_mult_pairs, bg_color, border_color, text_color):
        """创建一个克制关系区块
        attr_mult_pairs: [(attr_name, multiplier), ...]
        """
        if not attr_mult_pairs:
            return None

        card = QFrame()
        card.setFrameShape(QFrame.NoFrame)
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-left: 4px solid {border_color};
                border-radius: 10px;
            }}
        """)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        # 标题行
        header = QHBoxLayout()
        header.setSpacing(8)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size: 20px; background: transparent; border: none;")
        header.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"""
            color: {text_color};
            font-size: 15px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        header.addWidget(title_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"color: {PALETTE['text_mute']}; font-size: 11px; background: transparent; border: none;")
        header.addWidget(desc_lbl)
        header.addStretch()

        count_lbl = QLabel(f"{len(attr_mult_pairs)}个")
        count_lbl.setStyleSheet(f"""
            color: white;
            background-color: {bg_color};
            padding: 2px 8px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: bold;
        """)
        header.addWidget(count_lbl)

        lay.addLayout(header)

        # 属性卡片网格
        card_grid = QGridLayout()
        card_grid.setSpacing(8)
        for i, (attr, mult) in enumerate(attr_mult_pairs):
            ac = AttrCard(attr, multiplier=mult, icon_size=32)
            card_grid.addWidget(ac, i // 6, i % 6)
        lay.addLayout(card_grid)

        return card

    def _show_single(self, attr):
        """单属性克制"""
        data = self.effectiveness_data.get(attr, {})

        # 选中属性标题
        header_card = self._make_selected_header([attr])
        self.result_layout.addWidget(header_card)

        sections = [
            ("⚔  →", "攻击克制", "对以下属性造成2倍伤害",
             [(a, 2.0) for a in data.get('attack_2x', [])],
             '#c8463c', '#c8463c', '#c8463c'),
            ("🛡  →", "攻击抵抗", "对以下属性仅造成0.5倍伤害",
             [(a, 0.5) for a in data.get('attack_0.5x', [])],
             '#c89a3c', '#c89a3c', '#a8753d'),
            ("⚠  ←", "被克制", "受到以下属性2倍伤害",
             [(a, 2.0) for a in data.get('defense_2x', [])],
             '#c8463c', '#c8463c', '#c8463c'),
            ("✦  ←", "抵抗", "受到以下属性0.5倍伤害",
             [(a, 0.5) for a in data.get('defense_0.5x', [])],
             '#3c9a5a', '#3c9a5a', '#2a7a4a'),
        ]

        for icon, title, desc, pairs, bg, border, text in sections:
            card = self._make_section(icon, title, desc, pairs, bg, border, text)
            if card:
                self.result_layout.addWidget(card)
            else:
                empty = QLabel(f"  {icon} {title}：无")
                empty.setStyleSheet(f"color: {PALETTE['text_mute']}; font-size: 13px; background: transparent; border: none; padding: 4px 16px;")
                self.result_layout.addWidget(empty)

    def _show_dual(self, type1, type2):
        """双属性综合克制"""
        data1 = self.effectiveness_data.get(type1, {})
        data2 = self.effectiveness_data.get(type2, {})

        # 选中属性标题
        header_card = self._make_selected_header([type1, type2])
        self.result_layout.addWidget(header_card)

        # 计算综合被攻击效果（带倍率）
        defense_pairs = []  # [(attr, multiplier), ...]
        all_attackers = set()
        for key in ['defense_2x', 'defense_0.5x']:
            all_attackers.update(data1.get(key, []))
            all_attackers.update(data2.get(key, []))

        for attacker in sorted(all_attackers):
            mult1 = 2.0 if attacker in data1.get('defense_2x', []) else (0.5 if attacker in data1.get('defense_0.5x', []) else 1.0)
            mult2 = 2.0 if attacker in data2.get('defense_2x', []) else (0.5 if attacker in data2.get('defense_0.5x', []) else 1.0)
            final = mult1 * mult2
            if mult1 == 2.0 and mult2 == 2.0:
                final = 3.0
            if final >= 2.0 or final < 1.0:
                defense_pairs.append((attacker, final))

        defense_2x_pairs = [(a, m) for a, m in defense_pairs if m >= 2.0]
        defense_half_pairs = [(a, m) for a, m in defense_pairs if m < 1.0]

        # 计算综合攻击效果（带倍率）
        attack_pairs = []
        all_defenders = set()
        for key in ['attack_2x', 'attack_0.5x']:
            all_defenders.update(data1.get(key, []))
            all_defenders.update(data2.get(key, []))

        for defender in sorted(all_defenders):
            mult1 = 2.0 if defender in data1.get('attack_2x', []) else (0.5 if defender in data1.get('attack_0.5x', []) else 1.0)
            mult2 = 2.0 if defender in data2.get('attack_2x', []) else (0.5 if defender in data2.get('attack_0.5x', []) else 1.0)
            final = max(mult1, mult2)
            if final >= 2.0:
                attack_pairs.append((defender, final))
            elif mult1 < 1.0 and mult2 < 1.0:
                attack_pairs.append((defender, 0.25))

        attack_2x_pairs = [(a, m) for a, m in attack_pairs if m >= 2.0]
        attack_half_pairs = [(a, m) for a, m in attack_pairs if m < 1.0]

        sections = [
            ("⚔  →", "攻击克制", "对以下属性造成2倍+伤害",
             attack_2x_pairs, '#c8463c', '#c8463c', '#c8463c'),
            ("🛡  →", "攻击抵抗", "对以下属性仅造成0.5倍伤害",
             attack_half_pairs, '#c89a3c', '#c89a3c', '#a8753d'),
            ("⚠  ←", "被克制", "受到以下属性2倍+伤害",
             defense_2x_pairs, '#c8463c', '#c8463c', '#c8463c'),
            ("✦  ←", "抵抗", "受到以下属性0.5倍伤害",
             defense_half_pairs, '#3c9a5a', '#3c9a5a', '#2a7a4a'),
        ]

        for icon, title, desc, pairs, bg, border, text in sections:
            card = self._make_section(icon, title, desc, pairs, bg, border, text)
            if card:
                self.result_layout.addWidget(card)
            else:
                empty = QLabel(f"  {icon} {title}：无")
                empty.setStyleSheet(f"color: {PALETTE['text_mute']}; font-size: 13px; background: transparent; border: none; padding: 4px 16px;")
                self.result_layout.addWidget(empty)

    def _make_selected_header(self, attrs):
        """已选属性标题卡"""
        card = QFrame()
        card.setFrameShape(QFrame.NoFrame)
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {PALETTE['bg_card_alt']};
                border: 1px solid {PALETTE['gold']};
                border-radius: 12px;
            }}
        """)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(12)
        lay.setAlignment(Qt.AlignCenter)

        for i, attr in enumerate(attrs):
            if i > 0:
                plus = QLabel("+")
                plus.setStyleSheet(f"color: {PALETTE['gold_deep']}; font-size: 20px; font-weight: bold; background: transparent; border: none;")
                lay.addWidget(plus)

            # 大图标+名称
            pill = AttrPill(attr, icon_size=28, font_size=16)
            lay.addWidget(pill)

        return card
