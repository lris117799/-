#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
精灵图鉴视图 - 童话风专业设计
- 暖色羊皮纸基底 + 柔金点缀
- 属性色徽章 + 圆角卡片 + 柔和阴影
- 学习自 bwiki 精灵图鉴排版，并优化细节
"""

import warnings
warnings.filterwarnings("ignore", message="iCCP: known incorrect sRGB profile")

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QScrollArea, QFrame, QComboBox, QPushButton
)
from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import (
    QPixmap, QFont, QPainter, QPen, QColor, QBrush,
    QRadialGradient, QLinearGradient
)
import json
import os

# ────────────────────────────────────────────────────────────────
# 童话风调色板
# ────────────────────────────────────────────────────────────────
PALETTE = {
    # 背景层
    'bg_top':       '#f7eed8',   # 暖羊皮纸顶
    'bg_bottom':    '#ece0c2',   # 暖羊皮纸底
    'bg_card':      '#fffaf0',   # 象牙白卡片
    'bg_card_alt':  '#fbf3e3',   # 备用卡片色
    'bg_inset':     '#f0e4cc',   # 内嵌区
    'bg_hover':     '#fff5dc',   # 悬浮高亮
    # 边框
    'border':       '#d8c19a',   # 柔金边框
    'border_dark':  '#b89a6e',   # 深金边框
    'border_soft':  '#e6d4b0',   # 浅金边框
    # 文字
    'text':         '#3d2f1f',   # 深棕主文
    'text_sub':     '#7a6650',   # 灰棕副文
    'text_mute':    '#a08d75',   # 静音文字
    'text_on_gold': '#5a4216',   # 金底文字
    # 强调色
    'gold':         '#c9a96e',   # 主金
    'gold_deep':    '#a8853d',   # 深金
    'gold_light':   '#e6c98a',   # 浅金
    'leader':       '#b8860b',   # 首领金
    'leader_deep':  '#7e6012',   # 首领深金
    # 装饰
    'shadow':       QColor(120, 90, 40, 40),     # 卡片阴影
    'shadow_hover': QColor(180, 130, 50, 70),    # 悬浮阴影
    'glow':         QColor(212, 178, 110, 100),  # 金色辉光
}

# 属性色（RGB 元组），用于徽章背景与光环
TYPE_COLORS_RGB = {
    "火":   (220, 80, 60),
    "水":   (60, 130, 220),
    "草":   (90, 175, 90),
    "电":   (220, 180, 40),
    "冰":   (110, 195, 215),
    "武":   (190, 70, 70),
    "毒":   (160, 70, 200),
    "翼":   (110, 180, 225),
    "萌":   (220, 120, 175),
    "虫":   (140, 190, 60),
    "地":   (180, 140, 70),
    "幽灵": (115, 60, 200),
    "龙":   (90, 70, 230),
    "恶":   (110, 100, 120),
    "机械": (155, 165, 180),
    "光":   (215, 180, 40),
    "幻":   (170, 145, 215),
    "普通": (155, 155, 155),
}

def _type_rgb(type_name):
    """从属性名取 RGB（兼容"火系"和"火"两种写法）"""
    if not type_name:
        return (155, 155, 155)
    short = type_name.replace('系', '').strip()
    return TYPE_COLORS_RGB.get(short, (155, 155, 155))

def _type_bg(type_name):
    """属性徽章背景色（带透明度）"""
    r, g, b = _type_rgb(type_name)
    return f'rgba({r}, {g}, {b}, 0.92)'

def _type_border(type_name):
    """属性徽章边框色"""
    r, g, b = _type_rgb(type_name)
    return f'rgba({max(r-30,0)}, {max(g-30,0)}, {max(b-30,0)}, 1.0)'

def _type_halo(type_name):
    """属性光环色（径向渐变用）"""
    r, g, b = _type_rgb(type_name)
    return QColor(r, g, b, 60), QColor(r, g, b, 0)


# ── 图标加载辅助 ──
_SC_SC_DIR = os.path.join(os.path.dirname(__file__), "..", "image", "sc", "sc")
_SKILL_ATTR_DIR = os.path.join(os.path.dirname(__file__), "..", "image", "sc", "skill", "技能")
_SKILL_ABILITY_DIR = os.path.join(os.path.dirname(__file__), "..", "image", "sc", "skill", "特性")

# 技能分类 → 图标文件名映射（中文命名）
_SKILL_TYPE_ICON_MAP = {
    '物攻': '物攻.png',
    '魔攻': '魔攻.png',
    '状态': '状态.png',
    '防御': '防御.png',
}

_icon_cache = {}

def _get_dpr():
    """获取当前屏幕 devicePixelRatio，用于 HiDPI 清晰渲染"""
    try:
        from PySide6.QtGui import QGuiApplication
        app = QGuiApplication.instance()
        if app:
            screen = QGuiApplication.primaryScreen()
            if screen:
                return max(screen.devicePixelRatio(), 1.0)
    except Exception:
        pass
    return 1.0

def _scale_hdpi(pm, size):
    """将 pixmap 缩放到逻辑 size，自动处理 HiDPI"""
    if pm is None or pm.isNull() or not size:
        return pm
    dpr = _get_dpr()
    target = int(size * dpr)
    scaled = pm.scaled(target, target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    scaled.setDevicePixelRatio(dpr)
    return scaled

def _load_icon(path, size=None):
    """加载图标 pixmap，带缓存。失败返回 None"""
    if not path or not os.path.exists(path):
        return None
    dpr = _get_dpr()
    key = (path, size, dpr)
    if key in _icon_cache:
        return _icon_cache[key]
    pm = QPixmap(path)
    if pm.isNull():
        _icon_cache[key] = None
        return None
    if size:
        pm = _scale_hdpi(pm, size)
    _icon_cache[key] = pm
    return pm

def _skill_type_icon(skill_type, size=18):
    """获取技能分类图标（物攻/魔攻/状态/防御）"""
    fname = _SKILL_TYPE_ICON_MAP.get(skill_type)
    if not fname:
        return None
    return _load_icon(os.path.join(_SC_SC_DIR, fname), size)

def _ability_icon(ability_name, size=28):
    """获取特性图标"""
    if not ability_name:
        return None
    return _load_icon(os.path.join(_SKILL_ABILITY_DIR, f"{ability_name}.png"), size)

def _skill_icon(skill_name, size=32):
    """获取技能图标（按技能名加载，如 超导/潮涌/光球）"""
    if not skill_name:
        return None
    return _load_icon(os.path.join(_SKILL_ATTR_DIR, f"{skill_name}.png"), size)

# 属性图标别名（数据中的属性名 -> 图标文件名）
_ATTR_ICON_ALIASES = {
    '翼': '飞行',
    '幽灵': '幽',
}
_attr_icon_cache = {}

def _get_attr_icon(attr_name, size=14):
    """获取属性图标 QPixmap（已缩放，带缓存）。无图标返回 None。
    从 sc/sc/ 加载：先试 {short}系.png，再试 {alias}.png。"""
    if not attr_name:
        return None
    short = attr_name.replace('系', '').strip()
    dpr = _get_dpr()
    key = (short, size, dpr)
    if key in _attr_icon_cache:
        return _attr_icon_cache[key]
    pm = None
    alias = _ATTR_ICON_ALIASES.get(short, short)
    for fname in [f"{short}系.png", f"{alias}.png"]:
        path = os.path.join(_SC_SC_DIR, fname)
        if os.path.exists(path):
            raw = QPixmap(path)
            if not raw.isNull():
                pm = _scale_hdpi(raw, size)
                break
    _attr_icon_cache[key] = pm
    return pm

def _make_attr_pill(attr_name, font_size=11, icon_size=14,
                    pad_h=10, pad_v=2, radius=9):
    """构造属性徽章：文字 + 右侧属性图标（带属性色背景）。"""
    pill = QFrame()
    pill.setFrameShape(QFrame.NoFrame)
    pill.setAttribute(Qt.WA_StyledBackground, True)
    pill.setStyleSheet(f"""
        QFrame {{
            background-color: {_type_bg(attr_name)};
            border: none;
            border-radius: {radius}px;
        }}
    """)
    lay = QHBoxLayout(pill)
    lay.setContentsMargins(pad_h, pad_v, pad_h, pad_v)
    lay.setSpacing(4)

    text_lbl = QLabel(attr_name.replace('系', ''))
    text_lbl.setStyleSheet(
        f"color: white; font-size: {font_size}px; font-weight: bold;"
        f" background: transparent; border: none;"
    )
    lay.addWidget(text_lbl)

    icon_pm = _get_attr_icon(attr_name, size=icon_size)
    if icon_pm and not icon_pm.isNull():
        icon_lbl = QLabel()
        icon_lbl.setPixmap(icon_pm)
        icon_lbl.setFixedSize(icon_size, icon_size)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(icon_lbl)
    return pill


# 技能分类色
_SKILL_TYPE_COLORS = {
    '物攻': '#c8463c', '魔攻': '#3c82c8',
    '状态': '#5aa05a', '防御': '#c89a3c',
}

def _make_skill_type_badge(skill_type, icon_size=18, pad=2, radius=10,
                           show_text=False, font_size=11):
    """构造技能分类徽章：默认仅图标（物攻/魔攻/状态/防御），无底纹。
    无图标时回退到带底纹的文字。show_text=True 时同时显示图标+文字。"""
    icon_pm = _skill_type_icon(skill_type, icon_size)

    # 有图标时：纯图标显示，无底纹
    if icon_pm and not icon_pm.isNull() and not show_text:
        lbl = QLabel()
        lbl.setPixmap(icon_pm)
        lbl.setFixedSize(icon_size, icon_size)
        lbl.setStyleSheet("background: transparent; border: none;")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setToolTip(skill_type)
        return lbl

    # 无图标：回退到带底纹的文字徽章
    tc = _SKILL_TYPE_COLORS.get(skill_type, '#777777')
    badge = QFrame()
    badge.setFrameShape(QFrame.NoFrame)
    badge.setAttribute(Qt.WA_StyledBackground, True)
    badge.setStyleSheet(f"""
        QFrame {{
            background-color: {tc};
            border-radius: {radius}px;
        }}
    """)
    lay = QHBoxLayout(badge)
    lay.setContentsMargins(pad, pad, pad, pad)
    lay.setSpacing(3)

    if icon_pm and not icon_pm.isNull():
        lbl = QLabel()
        lbl.setPixmap(icon_pm)
        lbl.setFixedSize(icon_size, icon_size)
        lbl.setStyleSheet("background: transparent; border: none;")
        lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl)
        badge.setToolTip(skill_type)

    text_lbl = QLabel(skill_type)
    text_lbl.setStyleSheet(
        f"color: white; font-size: {font_size}px; font-weight: bold;"
        f" background: transparent; border: none;"
    )
    lay.addWidget(text_lbl)
    return badge

# 统一滚动条样式（童话风）
SCROLL_BAR_STYLE = """
    QScrollArea {
        border: none;
        background-color: transparent;
        padding-right: 10px;
    }
    QScrollBar:vertical {
        background: rgba(180, 150, 100, 0.10);
        width: 10px;
        border-radius: 5px;
        margin: 2px;
    }
    QScrollBar::handle:vertical {
        background: rgba(255, 252, 245, 0.85);
        border: 1px solid rgba(180, 140, 70, 0.35);
        border-radius: 5px;
        min-height: 30px;
    }
    QScrollBar::handle:vertical:hover {
        background: rgba(255, 255, 255, 0.95);
        border: 1px solid rgba(180, 140, 70, 0.5);
    }
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical { height: 0px; }
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical { background: none; }
"""

from PySide6.QtWidgets import QDialog


# ────────────────────────────────────────────────────────────────
# 共享背景绘制：羊皮纸渐变 + 装饰光斑
# ────────────────────────────────────────────────────────────────
def paint_parchment_background(widget, ev):
    """为widget绘制童话风羊皮纸背景"""
    p = QPainter(widget)
    p.setRenderHint(QPainter.Antialiasing, True)
    rect = widget.rect()

    # 主体垂直渐变
    grad = QLinearGradient(0, 0, 0, rect.height())
    grad.setColorAt(0.0, QColor(PALETTE['bg_top']))
    grad.setColorAt(1.0, QColor(PALETTE['bg_bottom']))
    p.fillRect(rect, QBrush(grad))

    # 顶部柔光
    halo = QRadialGradient(rect.width() * 0.5, -rect.height() * 0.2,
                           rect.width() * 0.8)
    halo.setColorAt(0, QColor(255, 245, 215, 110))
    halo.setColorAt(1, QColor(255, 245, 215, 0))
    p.fillRect(rect, QBrush(halo))

    # 角落点缀（四个角落的淡金色斑）
    for cx, cy in [(0, 0), (rect.width(), 0),
                   (0, rect.height()), (rect.width(), rect.height())]:
        blob = QRadialGradient(cx, cy, 220)
        blob.setColorAt(0, QColor(201, 169, 110, 45))
        blob.setColorAt(1, QColor(201, 169, 110, 0))
        p.fillRect(rect, QBrush(blob))

    p.end()


class ParchmentWidget(QWidget):
    """自带羊皮纸背景的基类widget"""
    def paintEvent(self, ev):
        paint_parchment_background(self, ev)
        super().paintEvent(ev)


class SkillDetailDialog(QDialog):
    """技能详情对话框 - 童话风"""

    def __init__(self, skill, all_pokemons, parent=None):
        super().__init__(parent)
        self.skill = skill
        self.all_pokemons = all_pokemons
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"技能详情 - {self.skill.get('name', '未知技能')}")
        self.setFixedSize(720, 760)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)

        # 整体羊皮纸背景
        self.setStyleSheet(f"""
            QDialog {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {PALETTE['bg_top']}, stop:1 {PALETTE['bg_bottom']});
                border: 1px solid {PALETTE['border_dark']};
                border-radius: 14px;
                outline: none;
            }}
        """)

        outer_layout = QVBoxLayout(self)
        outer_layout.setSpacing(10)
        outer_layout.setContentsMargins(14, 14, 14, 14)

        # 顶部技能头图卡（带属性色光环）
        header_card = QFrame()
        header_card.setStyleSheet(f"""
            QFrame {{
                background-color: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 12px;
                outline: none;
            }}
        """)
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(18, 14, 18, 14)
        header_layout.setSpacing(8)

        # 技能图标 + 技能名
        skill_name = self.skill.get('name', '未知技能')
        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        title_row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        skill_pm = _skill_icon(skill_name, size=48)
        if skill_pm and not skill_pm.isNull():
            skill_icon_lbl = QLabel()
            skill_icon_lbl.setPixmap(skill_pm)
            skill_icon_lbl.setFixedSize(48, 48)
            skill_icon_lbl.setStyleSheet("background: transparent; border: none;")
            skill_icon_lbl.setAlignment(Qt.AlignCenter)
            title_row.addWidget(skill_icon_lbl, alignment=Qt.AlignVCenter)

        name_label = QLabel(skill_name)
        name_label.setStyleSheet(f"""
            color: {PALETTE['text']};
            font-size: 22px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        title_row.addWidget(name_label)
        title_row.addStretch()
        header_layout.addLayout(title_row)

        # 属性 + 类型 行
        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)

        attr = self.skill.get('attribute', '')
        if attr:
            attr_pm = _get_attr_icon(attr, size=22)
            if attr_pm and not attr_pm.isNull():
                attr_lbl = QLabel()
                attr_lbl.setPixmap(attr_pm)
                attr_lbl.setFixedSize(22, 22)
                attr_lbl.setStyleSheet("background: transparent; border: none;")
                attr_lbl.setAlignment(Qt.AlignCenter)
                attr_lbl.setToolTip(attr.replace('系', ''))
                meta_row.addWidget(attr_lbl, alignment=Qt.AlignVCenter)
            else:
                attr_tag = _make_attr_pill(attr, font_size=12, icon_size=14,
                                           pad_h=12, pad_v=3, radius=10)
                meta_row.addWidget(attr_tag, alignment=Qt.AlignVCenter)

        skill_type = self.skill.get('type', '')
        if skill_type:
            type_tag = _make_skill_type_badge(skill_type, icon_size=22)
            meta_row.addWidget(type_tag, alignment=Qt.AlignVCenter)

        meta_row.addStretch()

        power = self.skill.get('power', '')
        cost = self.skill.get('cost', '')
        if cost and str(cost) != '0':
            cost_pm = _load_icon(os.path.join(_SC_SC_DIR, "能耗.png"), size=20)
            if cost_pm and not cost_pm.isNull():
                cost_icon_lbl = QLabel()
                cost_icon_lbl.setPixmap(cost_pm)
                cost_icon_lbl.setFixedSize(20, 20)
                cost_icon_lbl.setStyleSheet("background: transparent; border: none;")
                cost_icon_lbl.setAlignment(Qt.AlignCenter)
                meta_row.addWidget(cost_icon_lbl, alignment=Qt.AlignVCenter)
            c_tag = QLabel(str(cost))
            c_tag.setStyleSheet(f"color: #3c82c8; font-size: 15px; font-weight: bold; background: transparent; border: none;")
            meta_row.addWidget(c_tag, alignment=Qt.AlignVCenter)
        if power and str(power) != '0':
            meta_row.addSpacing(16)
            p_tag = QLabel(str(power))
            p_tag.setStyleSheet(f"color: #c8463c; font-size: 16px; font-weight: bold; background: transparent; border: none;")
            p_tag.setToolTip("威力")
            meta_row.addWidget(p_tag, alignment=Qt.AlignVCenter)

        header_layout.addLayout(meta_row)

        desc = self.skill.get('description', '')
        if desc:
            desc_label = QLabel(f"✦ {desc}")
            desc_label.setStyleSheet(f"""
                color: {PALETTE['text_sub']};
                font-size: 13px;
                background: transparent;
                border: none;
                line-height: 1.5;
            """)
            desc_label.setWordWrap(True)
            header_layout.addWidget(desc_label)

        outer_layout.addWidget(header_card)

        # 能学会此技能的精灵
        skill_name_str = self.skill.get('name', '')
        self.learners = self._find_learners(skill_name_str)
        self.selected_pokemon = None  # 点击精灵后存储，供父窗口导航

        learners_title = QLabel(f"✦ 能学会此技能的精灵  ({len(self.learners)}只)")
        learners_title.setStyleSheet(f"""
            color: {PALETTE['text']};
            font-size: 15px;
            font-weight: bold;
            background: transparent;
        """)
        outer_layout.addWidget(learners_title)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLL_BAR_STYLE)

        grid_container = QWidget()
        grid_container.setStyleSheet("background: transparent; border: none;")
        grid_layout = QGridLayout(grid_container)
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(4, 4, 4, 4)
        grid_layout.setAlignment(Qt.AlignTop)

        if self.learners:
            for idx, learner in enumerate(self.learners):
                card = self._make_learner_card(learner)
                row = idx // 5
                col = idx % 5
                grid_layout.addWidget(card, row, col)
        else:
            no_l = QLabel("暂无数据")
            no_l.setStyleSheet(f"color: {PALETTE['text_mute']}; font-size: 13px; background: transparent; border: none;")
            grid_layout.addWidget(no_l, 0, 0)

        scroll.setWidget(grid_container)
        outer_layout.addWidget(scroll, stretch=1)

        # 关闭按钮
        close_btn = QPushButton("关 闭")
        close_btn.setFixedHeight(38)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PALETTE['gold_light']}, stop:1 {PALETTE['gold']});
                color: {PALETTE['text_on_gold']};
                border: 1px solid {PALETTE['gold_deep']};
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                outline: none;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PALETTE['gold']}, stop:1 {PALETTE['gold_deep']});
                color: white;
            }}
        """)
        close_btn.clicked.connect(self.close)
        outer_layout.addWidget(close_btn)

    def _find_learners(self, skill_name):
        """查找能学会此技能的精灵，返回 [{name, id, level, source}] 列表"""
        learners = []
        seen_names = set()
        enriched_file = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "lkwg_enriched_data.json")
        # 同时从 pokemon_data.json 加载（作为补充数据源）
        data_file = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "pokemon_data.json")

        def _scan(pokemon_list, is_enriched=True):
            for pokemon in pokemon_list:
                pname = pokemon.get('name', '')
                if not pname or pname in seen_names:
                    continue
                pid = pokemon.get('id', 0)
                skills = pokemon.get('skills', {})
                found = None
                source = None
                for sk in skills.get('normal_skills', []):
                    if sk.get('name', '') == skill_name:
                        found = sk; source = 'default'; break
                if not found:
                    for sk in skills.get('bloodline_skills', []):
                        if sk.get('name', '') == skill_name:
                            found = sk; source = 'bloodline'; break
                if not found:
                    for sk in skills.get('stone_skills', []):
                        if sk.get('name', '') == skill_name:
                            found = sk; source = 'stone'; break
                if found:
                    seen_names.add(pname)
                    learners.append({
                        'name': pname,
                        'id': pid,
                        'level': found.get('level', found.get('unlock', '')),
                        'source': source,
                    })

        try:
            if os.path.exists(enriched_file):
                with open(enriched_file, 'r', encoding='utf-8') as f:
                    _scan(json.load(f), is_enriched=True)
            if os.path.exists(data_file):
                with open(data_file, 'r', encoding='utf-8') as f:
                    _scan(json.load(f), is_enriched=False)
        except Exception as e:
            print(f"加载技能数据失败: {e}")

        # 按 id 排序
        learners.sort(key=lambda x: x.get('id', 0))
        return learners

    def _make_learner_card(self, learner):
        """构造单个学习精灵卡片（图标+文字，可点击跳转）"""
        pid = learner.get('id', 0)
        name = learner.get('name', '')
        level = learner.get('level', '')
        source = learner.get('source', 'default')

        card = QFrame()
        card.setFixedSize(120, 160)
        card.setCursor(Qt.PointingHandCursor)
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 10px;
                outline: none;
            }}
            QFrame:hover {{
                border: 1px solid {PALETTE['gold']};
                background-color: {PALETTE['bg_hover']};
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignCenter)

        # 精灵图片
        image_path = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "images", f"{pid:03d}.png")
        if os.path.exists(image_path):
            pm = QPixmap(image_path)
            if not pm.isNull():
                scaled = pm.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_lbl = QLabel()
                img_lbl.setPixmap(scaled)
                img_lbl.setFixedSize(64, 64)
                img_lbl.setAlignment(Qt.AlignCenter)
                img_lbl.setStyleSheet("background: transparent; border: none;")
                layout.addWidget(img_lbl, alignment=Qt.AlignCenter)

        # 编号
        id_lbl = QLabel(f"NO.{pid:03d}")
        id_lbl.setStyleSheet(f"color: {PALETTE['text_mute']}; font-size: 10px; font-weight: 600; background: transparent; border: none;")
        id_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(id_lbl)

        # 名称
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color: {PALETTE['text']}; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setWordWrap(True)
        layout.addWidget(name_lbl)

        # 等级 + 来源 徽章
        source_labels = {'default': '默认', 'bloodline': '血脉', 'stone': '技能石'}
        source_colors = {'default': '#5aa05a', 'bloodline': '#b84a7d', 'stone': '#2a8a6a'}

        if level or source:
            badge_row = QHBoxLayout()
            badge_row.setSpacing(3)
            badge_row.setAlignment(Qt.AlignCenter)

            # 等级
            level_str = str(level) if level else ''
            if level_str:
                if not level_str.lower().startswith('lv'):
                    level_str = f"Lv.{level_str}"
                lv_lbl = QLabel(level_str)
                lv_lbl.setStyleSheet(f"""
                    background-color: {PALETTE['gold_light']};
                    color: {PALETTE['text_on_gold']};
                    padding: 1px 6px;
                    border-radius: 6px;
                    font-size: 9px;
                    font-weight: bold;
                """)
                badge_row.addWidget(lv_lbl)

            # 来源
            src_color = source_colors.get(source, '#777777')
            src_text = source_labels.get(source, source)
            src_lbl = QLabel(src_text)
            src_lbl.setStyleSheet(f"""
                background-color: {src_color};
                color: white;
                padding: 1px 6px;
                border-radius: 6px;
                font-size: 9px;
                font-weight: bold;
            """)
            badge_row.addWidget(src_lbl)
            layout.addLayout(badge_row)

        # 点击跳转
        def _on_click(event):
            for p in self.all_pokemons:
                if p.get('name') == name or p.get('id') == pid:
                    self.selected_pokemon = p
                    self.accept()
                    return

        card.mousePressEvent = _on_click
        return card


class RoundedFrame(QFrame):
    """自定义圆角Frame，禁用默认边框绘制"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setFocusPolicy(Qt.NoFocus)


# ────────────────────────────────────────────────────────────────
# 精灵卡片 - 童话风
# ────────────────────────────────────────────────────────────────
class PokemonCard(QFrame):
    """精灵卡片 - 童话风专业设计"""

    _shared_icons = None
    _pokemon_pixmaps = {}

    @classmethod
    def _load_shared_icons(cls):
        if cls._shared_icons is not None:
            return cls._shared_icons
        xg_path = r"d:\game\lkwg\image\sc\sc\xg.png"
        jb_path = r"d:\game\lkwg\image\sc\sc\jb.png"
        sl_path = r"d:\game\lkwg\image\sc\sc\sl.png"

        def _load(path, w, h):
            if not os.path.exists(path):
                return None
            pm = QPixmap(path)
            if pm.isNull():
                return None
            return _scale_hdpi(pm, max(w, h))

        cls._shared_icons = {
            'xg':    _load(xg_path, 14, 14),
            'jb':    _load(jb_path, 14, 14),
            'sl_28': _load(sl_path, 28, 28),
            'sl_22': _load(sl_path, 22, 22),
        }
        return cls._shared_icons

    @classmethod
    def _get_pokemon_pixmap(cls, pid, size=120):
        dpr = _get_dpr()
        cache_key = (pid, size, dpr)
        if cache_key in cls._pokemon_pixmaps:
            return cls._pokemon_pixmaps[cache_key]
        image_path = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "images", f"{pid:03d}.png")
        pm = None
        if os.path.exists(image_path):
            raw = QPixmap(image_path)
            if not raw.isNull():
                pm = _scale_hdpi(raw, size)
        cls._pokemon_pixmaps[cache_key] = pm
        return pm

    def __init__(self, pokemon, show_extra=False, parent=None):
        super().__init__(parent)
        self.pokemon = pokemon
        self.show_extra = show_extra
        self.setFixedSize(200, 260)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setFocusPolicy(Qt.NoFocus)
        self._hovered = False
        self.setup_ui()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            parent = self.parent()
            while parent:
                if hasattr(parent, 'show_detail'):
                    parent.show_detail(self.pokemon)
                    return
                parent = parent.parent()

    def enterEvent(self, ev):
        self._hovered = True
        self.update()
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        self._hovered = False
        self.update()
        super().leaveEvent(ev)

    def paintEvent(self, ev):
        """自绘卡片背景：象牙白底 + 柔金边框 + 悬浮辉光"""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        radius = 14.0

        # 悬浮辉光（外层）
        if self._hovered:
            glow = QRectF(0, 0, self.width(), self.height())
            p.setBrush(QBrush(PALETTE['glow']))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(glow.adjusted(0, 0, 0, -2), radius + 2, radius + 2)

        # 卡片阴影
        shadow_rect = r.translated(0, 3 if self._hovered else 2)
        p.setBrush(QBrush(PALETTE['shadow_hover'] if self._hovered else PALETTE['shadow']))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(shadow_rect, radius, radius)

        # 卡片主体
        if self._hovered:
            p.setBrush(QBrush(QColor(PALETTE['bg_hover'])))
        else:
            p.setBrush(QBrush(QColor(PALETTE['bg_card'])))
        border_color = PALETTE['gold_deep'] if self._hovered else PALETTE['border']
        p.setPen(QPen(QColor(border_color), 1.4 if self._hovered else 1.0))
        p.drawRoundedRect(r, radius, radius)

        p.end()

    def setup_ui(self):
        is_leader = self.pokemon.get('is_leader_form', False)
        shared_icons = self._load_shared_icons()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 顶部行：编号 + 阶段徽章 ──
        header_wrap = QWidget()
        header_wrap.setFixedHeight(28)
        header_wrap.setStyleSheet("background: transparent; border: none;")
        header_layout = QHBoxLayout(header_wrap)
        header_layout.setContentsMargins(10, 6, 10, 0)
        header_layout.setSpacing(4)

        pid = self.pokemon.get('id', 0)
        id_label = QLabel(f"NO.{pid:03d}")
        id_label.setStyleSheet(f"""
            color: {PALETTE['text_mute']};
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1px;
            background: transparent;
            border: none;
        """)
        header_layout.addWidget(id_label)
        header_layout.addStretch()

        # 阶段徽章（颜色：一阶绿/二阶蓝/三阶紫/首领金）
        stage = self._get_stage_text()
        if stage:
            stage_colors = {
                '一阶':   '#5aa05a',
                '二阶':   '#3c82c8',
                '三阶':   '#9c5dc8',
                '首领':   '#c89a3c',
                '最终':   '#c8783c',
                '无进':   '#8a8a8a',
            }
            sc = stage_colors.get(stage, '#8a8a8a')
            stage_tag = QLabel(stage)
            stage_tag.setStyleSheet(f"""
                QLabel {{
                    background-color: {sc};
                    color: white;
                    padding: 1px 8px;
                    border-radius: 8px;
                    font-size: 10px;
                    font-weight: bold;
                }}
            """)
            stage_tag.setAlignment(Qt.AlignCenter)
            header_layout.addWidget(stage_tag)

        main_layout.addWidget(header_wrap)

        # ── 图片区（带属性色光环） ──
        image_wrap = QWidget()
        image_wrap.setFixedHeight(140)
        image_wrap.setStyleSheet("background: transparent; border: none;")
        image_layout = QVBoxLayout(image_wrap)
        image_layout.setContentsMargins(0, 4, 0, 4)
        image_layout.setAlignment(Qt.AlignCenter)

        image_label = QLabel()
        image_label.setFixedSize(120, 120)
        image_label.setAlignment(Qt.AlignCenter)

        cached_pm = self._get_pokemon_pixmap(pid)
        if cached_pm is not None:
            # 合成：底层属性光环 + 精灵图（HiDPI）
            attr = self.pokemon.get('attribute', '')
            primary_type = attr.split('/')[0] if '/' in attr else attr
            halo_inner, halo_outer = _type_halo(primary_type)
            dpr = _get_dpr()
            phys = int(120 * dpr)
            composited = QPixmap(phys, phys)
            composited.fill(Qt.transparent)
            painter = QPainter(composited)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.scale(dpr, dpr)
            # 径向光环
            halo_grad = QRadialGradient(60, 60, 60)
            halo_grad.setColorAt(0, halo_inner)
            halo_grad.setColorAt(1, halo_outer)
            painter.setBrush(QBrush(halo_grad))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, 120, 120)
            # 精灵图
            painter.drawPixmap(0, 0, cached_pm)
            painter.end()
            composited.setDevicePixelRatio(dpr)
            image_label.setPixmap(composited)

        image_layout.addWidget(image_label)
        main_layout.addWidget(image_wrap)

        # ── 名称区 ──
        name_wrap = QWidget()
        name_wrap.setStyleSheet("background: transparent; border: none;")
        name_layout = QVBoxLayout(name_wrap)
        name_layout.setContentsMargins(10, 0, 10, 0)
        name_layout.setSpacing(4)

        name = self.pokemon.get('name', '未知')
        name_label = QLabel(name)
        name_label.setStyleSheet(f"""
            color: {PALETTE['leader'] if is_leader else PALETTE['text']};
            font-size: 14px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        name_layout.addWidget(name_label)

        # 首领化小标签（在名称下方）
        if is_leader:
            leader_mini = QLabel("★ 首领形态")
            leader_mini.setStyleSheet(f"""
                color: {PALETTE['leader']};
                font-size: 10px;
                font-weight: 600;
                background: transparent;
                border: none;
            """)
            leader_mini.setAlignment(Qt.AlignCenter)
            name_layout.addWidget(leader_mini)

        main_layout.addWidget(name_wrap)

        # ── 属性徽章行 ──
        attr_wrap = QWidget()
        attr_wrap.setFixedHeight(28)
        attr_wrap.setStyleSheet("background: transparent; border: none;")
        attr_layout = QHBoxLayout(attr_wrap)
        attr_layout.setContentsMargins(10, 0, 10, 8)
        attr_layout.setSpacing(4)
        attr_layout.addStretch()

        attr = self.pokemon.get('attribute', '')
        if attr:
            parts = attr.split('/') if '/' in attr else [attr]
            for part in parts:
                tag = _make_attr_pill(part, font_size=11, icon_size=14,
                                      pad_h=10, pad_v=2, radius=9)
                attr_layout.addWidget(tag)

        # 额外信息（星光值/洛克贝）- 显示在属性行右侧
        if self.show_extra:
            starlight = self.pokemon.get('starlight', '')
            review_cost = self.pokemon.get('review_cost', '')
            xg_pm = shared_icons['xg']
            jb_pm = shared_icons['jb']

            if starlight and xg_pm and not xg_pm.isNull():
                s_icon = QLabel()
                s_icon.setPixmap(xg_pm)
                s_icon.setFixedSize(14, 14)
                s_icon.setStyleSheet("background: transparent; border: none;")
                attr_layout.addWidget(s_icon)
                s_val = QLabel(str(starlight))
                s_val.setStyleSheet(f"color: {PALETTE['gold_deep']}; font-size: 10px; font-weight: bold; background: transparent; border: none;")
                attr_layout.addWidget(s_val)

            if review_cost and jb_pm and not jb_pm.isNull():
                c_icon = QLabel()
                c_icon.setPixmap(jb_pm)
                c_icon.setFixedSize(14, 14)
                c_icon.setStyleSheet("background: transparent; border: none;")
                attr_layout.addWidget(c_icon)
                c_val = QLabel(str(review_cost))
                c_val.setStyleSheet(f"color: #8a6a30; font-size: 10px; font-weight: bold; background: transparent; border: none;")
                attr_layout.addWidget(c_val)

        attr_layout.addStretch()
        main_layout.addWidget(attr_wrap)

        # 底部装饰金条（仅首领化）
        if is_leader:
            deco = QWidget()
            deco.setFixedHeight(3)
            deco.setStyleSheet(f"background: transparent; border: none;")
            deco_layout = QHBoxLayout(deco)
            deco_layout.setContentsMargins(20, 0, 20, 6)
            bar = QWidget()
            bar.setFixedHeight(3)
            bar.setStyleSheet(f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent,
                    stop:0.3 {PALETTE['leader']},
                    stop:0.7 {PALETTE['leader']},
                    stop:1 transparent);
                border: none;
                border-radius: 1px;
            """)
            deco_layout.addWidget(bar)
            main_layout.addWidget(deco)

    def _get_stage_text(self):
        """从 pokemon 数据推断阶段短文本"""
        if self.pokemon.get('is_leader_form'):
            return '首领'
        chain = self.pokemon.get('evolution_chain', [])
        evolution = self.pokemon.get('evolution', [])
        name = self.pokemon.get('name', '')

        if chain:
            non_leader = [e for e in chain if not e.get('is_leader')]
            if not non_leader:
                return '无进'
            if len(non_leader) <= 1:
                return '无进' if non_leader[0].get('name') == name else '无进'
            for i, e in enumerate(non_leader):
                if e.get('name') == name:
                    remaining = non_leader[i+1:]
                    if remaining and all(PokedexWidget._is_leader_related(r) for r in remaining):
                        return '最终'
                    stage = i + 1
                    if stage >= 3:
                        return '三阶'
                    return {1: '一阶', 2: '二阶'}.get(stage, '一阶')
            # 在 chain 但找不到自己 - 可能是首领形态已经在前面过滤掉了
            return '一阶'

        if evolution and evolution != ['无法进化']:
            if len(evolution) == 1 and evolution[0] == name:
                return '无进'
            return '一阶'
        return '无进'


# ────────────────────────────────────────────────────────────────
# 详情页 - 童话风
# ────────────────────────────────────────────────────────────────
class PokemonDetailWidget(ParchmentWidget):
    """精灵详情页 - 童话风专业设计"""

    def __init__(self, pokemon, parent=None):
        super().__init__(parent)
        self.pokemon = pokemon
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 22, 28, 22)
        main_layout.setSpacing(18)

        # ── 顶部导航行 ──
        nav_row = QHBoxLayout()
        nav_row.setContentsMargins(0, 0, 0, 0)

        back_btn = QPushButton("← 返回图鉴")
        back_btn.setFixedHeight(34)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setAttribute(Qt.WA_MacShowFocusRect, False)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {PALETTE['bg_card']};
                color: {PALETTE['text']};
                border: 1px solid {PALETTE['border']};
                border-radius: 10px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: 600;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {PALETTE['gold_light']};
                color: {PALETTE['text_on_gold']};
                border: 1px solid {PALETTE['gold_deep']};
            }}
        """)
        back_btn.clicked.connect(self.go_back)
        nav_row.addWidget(back_btn)
        nav_row.addStretch()
        main_layout.addLayout(nav_row)

        # ── 滚动区 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(SCROLL_BAR_STYLE)

        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent; border: none;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(0, 0, 40, 0)

        # ── 英雄区：图像 + 基本信息 ──
        hero_card = RoundedFrame()
        hero_card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 250, 240, 0.85);
                border: 1px solid {PALETTE['border']};
                border-radius: 16px;
                outline: none;
            }}
        """)
        hero_layout = QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(24, 20, 24, 20)
        hero_layout.setSpacing(28)

        # 左：图像（属性色光环背景）
        image_frame = QFrame()
        image_frame.setFixedSize(220, 220)
        image_frame.setStyleSheet("background: transparent; border: none;")
        image_grid = QGridLayout(image_frame)
        image_grid.setContentsMargins(0, 0, 0, 0)

        # 合成图：属性色径向 + glq装饰底 + 精灵图（HiDPI）
        glq_path = r"d:\game\lkwg\image\sc\sc\glq.png"
        dpr = _get_dpr()
        phys220 = int(220 * dpr)
        composited = QPixmap(phys220, phys220)
        composited.fill(Qt.transparent)
        painter = QPainter(composited)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.scale(dpr, dpr)

        # 底层：属性色径向光环
        attr = self.pokemon.get('attribute', '')
        primary_type = attr.split('/')[0] if '/' in attr else attr
        halo_inner, halo_outer = _type_halo(primary_type)
        halo_grad = QRadialGradient(110, 110, 110)
        halo_grad.setColorAt(0, halo_inner)
        halo_grad.setColorAt(1, halo_outer)
        painter.setBrush(QBrush(halo_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 220, 220)

        # glq 装饰底
        if os.path.exists(glq_path):
            glq_pm = QPixmap(glq_path)
            if not glq_pm.isNull():
                glq_scaled = _scale_hdpi(glq_pm, 200)
                painter.drawPixmap(10, 10, glq_scaled)

        # 精灵图
        pid = self.pokemon.get('id', 0)
        image_path = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "images", f"{pid:03d}.png")
        if os.path.exists(image_path):
            pm = QPixmap(image_path)
            if not pm.isNull():
                pokemon_scaled = _scale_hdpi(pm, 150)
                x = (220 - pokemon_scaled.width() / dpr) // 2
                y = (220 - pokemon_scaled.height() / dpr) // 2
                painter.drawPixmap(x, y, pokemon_scaled)

        # 圆形边框
        painter.setPen(QPen(QColor(PALETTE['gold_deep']), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(1, 1, 218, 218)

        painter.end()
        composited.setDevicePixelRatio(dpr)

        img_label = QLabel()
        img_label.setPixmap(composited)
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setStyleSheet("background: transparent; border: none; padding: 0; margin: 0;")
        image_grid.addWidget(img_label, 0, 0, alignment=Qt.AlignCenter)

        # 首领化徽章（图像右上角）
        if self.pokemon.get('is_leader_form'):
            shared_icons = PokemonCard._load_shared_icons()
            if shared_icons['sl_28']:
                badge = QLabel()
                badge.setPixmap(shared_icons['sl_28'])
                badge.setStyleSheet(f"""
                    background-color: rgba(255, 250, 230, 0.95);
                    border: 2px solid {PALETTE['leader']};
                    border-radius: 16px;
                    padding: 2px;
                """)
                badge.setAlignment(Qt.AlignCenter)
                badge.setFixedSize(34, 34)
                image_grid.addWidget(badge, 0, 0, alignment=Qt.AlignTop | Qt.AlignRight)

        hero_layout.addWidget(image_frame, alignment=Qt.AlignCenter)

        # 右：信息栏
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)

        # 编号
        id_label = QLabel(f"NO.{pid:03d}")
        id_label.setStyleSheet(f"""
            color: {PALETTE['gold_deep']};
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 2px;
            background: transparent;
            border: none;
        """)
        info_layout.addWidget(id_label)

        # 名称
        name = self.pokemon.get('name', '未知')
        name_label = QLabel(name)
        name_label.setStyleSheet(f"""
            color: {PALETTE['text']};
            font-size: 30px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        info_layout.addWidget(name_label)

        # 属性徽章行
        if attr:
            attr_container = QWidget()
            attr_container.setStyleSheet("background: transparent; border: none;")
            attr_box = QHBoxLayout(attr_container)
            attr_box.setContentsMargins(0, 4, 0, 4)
            attr_box.setSpacing(8)
            parts = attr.split('/') if '/' in attr else [attr]
            for part in parts:
                tag = _make_attr_pill(part, font_size=14, icon_size=18,
                                      pad_h=18, pad_v=5, radius=12)
                attr_box.addWidget(tag)
            attr_box.addStretch()
            info_layout.addWidget(attr_container)

        # 身高体重
        height = self.pokemon.get('height', '')
        weight = self.pokemon.get('weight', '')
        if height or weight:
            hw = QHBoxLayout()
            hw.setSpacing(20)
            if height:
                h_label = QLabel(f"📏 身高  {height} m")
                h_label.setStyleSheet(f"color: {PALETTE['text_sub']}; font-size: 13px; background: transparent; border: none;")
                hw.addWidget(h_label)
            if weight:
                w_label = QLabel(f"⚖ 体重  {weight} kg")
                w_label.setStyleSheet(f"color: {PALETTE['text_sub']}; font-size: 13px; background: transparent; border: none;")
                hw.addWidget(w_label)
            hw.addStretch()
            info_layout.addLayout(hw)

        info_layout.addStretch()
        hero_layout.addLayout(info_layout, stretch=1)

        content_layout.addWidget(hero_card)

        # ── 描述（卷轴风） ──
        description = self.pokemon.get('description', '')
        if description:
            desc_card = RoundedFrame()
            desc_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {PALETTE['bg_inset']};
                    border: 1px solid {PALETTE['border']};
                    border-radius: 12px;
                    outline: none;
                }}
            """)
            desc_layout = QHBoxLayout(desc_card)
            desc_layout.setContentsMargins(20, 14, 20, 14)

            # 左侧装饰条
            deco_bar = QWidget()
            deco_bar.setFixedWidth(4)
            deco_bar.setStyleSheet(f"background-color: {PALETTE['gold']}; border: none; border-radius: 2px;")
            desc_layout.addWidget(deco_bar)

            desc_text = QLabel(f"「{description}」")
            desc_text.setStyleSheet(f"""
                color: {PALETTE['text']};
                font-size: 14px;
                font-style: italic;
                line-height: 1.6;
                background: transparent;
                border: none;
            """)
            desc_text.setWordWrap(True)
            desc_layout.addWidget(desc_text, stretch=1)

            content_layout.addWidget(desc_card)

        # ── 基本信息卡片行 ──
        starlight = self.pokemon.get('starlight', '')
        review_cost = self.pokemon.get('review_cost', '')
        gender_ratio = self.pokemon.get('gender_ratio', '')
        egg_groups = self.pokemon.get('egg_groups', [])

        if starlight or review_cost or gender_ratio or egg_groups:
            section_title = self._make_section_title("基本信息")
            content_layout.addWidget(section_title)

            info_row = QHBoxLayout()
            info_row.setSpacing(12)

            if starlight:
                info_row.addWidget(self._make_icon_card("星光值", str(starlight),
                    r"d:\game\lkwg\image\sc\sc\xg.png", PALETTE['gold_deep']))
            if review_cost:
                info_row.addWidget(self._make_icon_card("洛克贝", str(review_cost),
                    r"d:\game\lkwg\image\sc\sc\jb.png", "#8a6a30"))
            if gender_ratio:
                info_row.addWidget(self._make_gender_card(gender_ratio))
            if egg_groups:
                egg_text = " / ".join(egg_groups)
                info_row.addWidget(self._make_text_card("蛋组", egg_text, "#5aa05a"))

            info_row.addStretch()
            content_layout.addLayout(info_row)

        # ── 种族值 ──
        stats = self.pokemon.get('stats', {})
        if stats:
            section_title = self._make_section_title("种族值")
            content_layout.addWidget(section_title)

            stats_card = RoundedFrame()
            stats_card.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(255, 250, 240, 0.85);
                    border: 1px solid {PALETTE['border']};
                    border-radius: 14px;
                    outline: none;
                }}
            """)
            stats_main = QHBoxLayout(stats_card)
            stats_main.setContentsMargins(24, 18, 24, 18)
            stats_main.setSpacing(28)

            # 左：6项
            stats_left = QVBoxLayout()
            stats_left.setSpacing(10)

            stat_items = [
                ('HP',  stats.get('hp', 0),            '#c8463c'),
                ('攻击', stats.get('attack', 0),        '#c8783c'),
                ('防御', stats.get('defense', 0),       '#3c82c8'),
                ('特攻', stats.get('magic_attack', 0),  '#9c5dc8'),
                ('特防', stats.get('magic_defense', 0), '#5aa05a'),
                ('速度', stats.get('speed', 0),         '#c89a3c'),
            ]
            # 取最大值用于条宽计算
            max_val = max((v for _, v, _ in stat_items), default=200)
            max_val = max(max_val, 200)  # 至少200作为标尺

            for label, value, color in stat_items:
                row = QHBoxLayout()
                row.setSpacing(10)

                name_lbl = QLabel(label)
                name_lbl.setStyleSheet(f"color: {PALETTE['text']}; font-size: 12px; font-weight: 600; background: transparent; border: none;")
                name_lbl.setFixedWidth(38)
                row.addWidget(name_lbl)

                # 进度条
                bar_bg = RoundedFrame()
                bar_bg.setFixedHeight(14)
                bar_bg.setStyleSheet(f"""
                    QFrame {{
                        background-color: {PALETTE['bg_inset']};
                        border: 1px solid {PALETTE['border_soft']};
                        border-radius: 7px;
                    }}
                """)
                bar_inner = QHBoxLayout(bar_bg)
                bar_inner.setContentsMargins(1, 1, 1, 1)
                bar_inner.setSpacing(0)

                fill = RoundedFrame()
                fill.setFixedHeight(12)
                percent = min(value / max_val, 1.0)
                fill.setMinimumWidth(int(200 * percent))
                fill.setStyleSheet(f"""
                    QFrame {{
                        background-color: {color};
                        border: none;
                        border-radius: 6px;
                    }}
                """)
                bar_inner.addWidget(fill)
                bar_inner.addStretch()
                row.addWidget(bar_bg, stretch=1)

                val_lbl = QLabel(str(value))
                val_lbl.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold; background: transparent; border: none;")
                val_lbl.setFixedWidth(36)
                val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                row.addWidget(val_lbl)

                stats_left.addLayout(row)

            stats_main.addLayout(stats_left, stretch=1)

            # 右：总和圆环
            total_frame = QFrame()
            total_frame.setFixedSize(140, 140)
            total_frame.setStyleSheet("background: transparent; border: none;")
            total_grid = QGridLayout(total_frame)
            total_grid.setContentsMargins(0, 0, 0, 0)

            # 自绘总和圆（HiDPI）
            total_circle = QLabel()
            dpr_total = _get_dpr()
            phys140 = int(140 * dpr_total)
            total_pm = QPixmap(phys140, phys140)
            total_pm.fill(Qt.transparent)
            tp = QPainter(total_pm)
            tp.setRenderHint(QPainter.Antialiasing, True)
            tp.scale(dpr_total, dpr_total)
            # 外圈金色
            tp.setBrush(QBrush(QColor(PALETTE['gold'])))
            tp.setPen(QPen(QColor(PALETTE['gold_deep']), 2))
            tp.drawEllipse(8, 8, 124, 124)
            # 内圈象牙白
            tp.setBrush(QBrush(QColor(PALETTE['bg_card'])))
            tp.setPen(Qt.NoPen)
            tp.drawEllipse(16, 16, 108, 108)
            tp.end()
            total_pm.setDevicePixelRatio(dpr_total)
            total_circle.setPixmap(total_pm)
            total_grid.addWidget(total_circle, 0, 0, alignment=Qt.AlignCenter)

            # 总和数字叠加
            overlay = QFrame()
            overlay.setStyleSheet("background: transparent; border: none;")
            overlay_grid = QGridLayout(overlay)
            overlay_grid.setContentsMargins(0, 0, 0, 0)

            t_lbl = QLabel("总和")
            t_lbl.setStyleSheet(f"color: {PALETTE['text_sub']}; font-size: 12px; background: transparent; border: none;")
            t_lbl.setAlignment(Qt.AlignCenter)
            overlay_grid.addWidget(t_lbl, 0, 0)

            t_val = QLabel(str(stats.get('total', 0)))
            t_val.setStyleSheet(f"color: {PALETTE['gold_deep']}; font-size: 28px; font-weight: bold; background: transparent; border: none;")
            t_val.setAlignment(Qt.AlignCenter)
            overlay_grid.addWidget(t_val, 1, 0)

            total_grid.addWidget(overlay, 0, 0, alignment=Qt.AlignCenter)

            stats_main.addWidget(total_frame, alignment=Qt.AlignCenter)

            content_layout.addWidget(stats_card)

        # ── 进化链 ──
        evolution_chain = self.pokemon.get('evolution_chain', [])
        current_name = self.pokemon.get('name', '')
        old_evolution = self.pokemon.get('evolution', [])

        if evolution_chain:
            content_layout.addWidget(self._make_section_title("进化链"))
            content_layout.addWidget(self._build_evolution_chain_widget(
                [(e.get('name', ''), e.get('evo_level'), e.get('is_leader', False)) for e in evolution_chain],
                current_name))

        elif old_evolution and old_evolution != ['无法进化']:
            full_evolution = []
            if current_name not in old_evolution:
                all_evo_names = old_evolution + [current_name]
                try:
                    data_file = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "pokemon_data.json")
                    if os.path.exists(data_file):
                        with open(data_file, 'r', encoding='utf-8') as f:
                            all_pokemons = json.load(f)
                            name_to_id = {p['name']: p['id'] for p in all_pokemons}
                            full_evolution = sorted(all_evo_names, key=lambda x: name_to_id.get(x, 999))
                    else:
                        full_evolution = old_evolution + [current_name]
                except Exception:
                    full_evolution = old_evolution + [current_name]
            else:
                full_evolution = old_evolution.copy()

            chain_data = []
            for n in full_evolution:
                base_name = n.split('（')[0].split('(')[0].strip() if n else n
                chain_data.append((base_name, None, False))
            content_layout.addWidget(self._make_section_title("进化链"))
            content_layout.addWidget(self._build_evolution_chain_widget(chain_data, current_name))

        elif old_evolution == ['无法进化']:
            content_layout.addWidget(self._make_section_title("进化链"))
            no_evo = QLabel("— 此精灵无法进化 —")
            no_evo.setStyleSheet(f"color: {PALETTE['text_mute']}; font-size: 13px; background: transparent; border: none;")
            no_evo.setAlignment(Qt.AlignCenter)
            content_layout.addWidget(no_evo)

        # ── 特性 ──
        ability_name = self.pokemon.get('ability_name', '')
        ability_desc = self.pokemon.get('ability_desc', '')
        abilities = self.pokemon.get('abilities', [])

        if ability_name or ability_desc:
            content_layout.addWidget(self._make_section_title("特性"))
            content_layout.addWidget(self._build_ability_box(ability_name, ability_desc))
        elif abilities:
            content_layout.addWidget(self._make_section_title("特性"))
            for ability in abilities:
                if isinstance(ability, dict):
                    content_layout.addWidget(self._build_ability_box(
                        ability.get('name', ''), ability.get('effect', '')))
                else:
                    content_layout.addWidget(self._build_ability_box('', str(ability)))

        # ── 技能 ──
        skills = self.pokemon.get('skills', {})
        normal_skills = skills.get('normal_skills', [])
        bloodline_skills = skills.get('bloodline_skills', [])
        stone_skills = skills.get('stone_skills', [])

        content_layout.addWidget(self._make_section_title("技能"))

        # Tab 切换
        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)

        normal_tab_btn = QPushButton(f"精灵技能 ({len(normal_skills)})")
        bloodline_tab_btn = QPushButton(f"血脉技能 ({len(bloodline_skills)})")
        stone_tab_btn = QPushButton(f"技能石 ({len(stone_skills)})")

        tab_style_default = f"""
            QPushButton {{
                background-color: {PALETTE['bg_card']};
                color: {PALETTE['text_sub']};
                border: 1px solid {PALETTE['border']};
                border-radius: 14px;
                padding: 6px 18px;
                font-size: 13px;
                font-weight: 600;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {PALETTE['bg_hover']};
                color: {PALETTE['text']};
            }}
        """
        tab_style_active = f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PALETTE['gold']}, stop:1 {PALETTE['gold_deep']});
                color: white;
                border: 1px solid {PALETTE['gold_deep']};
                border-radius: 14px;
                padding: 6px 18px;
                font-size: 13px;
                font-weight: bold;
                outline: none;
            }}
        """
        for btn in (normal_tab_btn, bloodline_tab_btn, stone_tab_btn):
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setAttribute(Qt.WA_MacShowFocusRect, False)
            btn.setStyleSheet(tab_style_default)
            tab_row.addWidget(btn)
        tab_row.addStretch()
        content_layout.addLayout(tab_row)

        # 三个滚动区
        normal_scroll = self._make_skill_scroll(normal_skills)
        bloodline_scroll = self._make_skill_scroll(bloodline_skills, kind='bloodline')
        stone_scroll = self._make_skill_scroll(stone_skills, kind='stone')

        if normal_skills:
            normal_scroll.setVisible(True); bloodline_scroll.setVisible(False); stone_scroll.setVisible(False)
            normal_tab_btn.setChecked(True)
            normal_tab_btn.setStyleSheet(tab_style_active)
        elif bloodline_skills:
            normal_scroll.setVisible(False); bloodline_scroll.setVisible(True); stone_scroll.setVisible(False)
            bloodline_tab_btn.setChecked(True)
            bloodline_tab_btn.setStyleSheet(tab_style_active)
        else:
            normal_scroll.setVisible(False); bloodline_scroll.setVisible(False); stone_scroll.setVisible(True)
            stone_tab_btn.setChecked(True)
            stone_tab_btn.setStyleSheet(tab_style_active)

        def _activate(btn):
            for b in (normal_tab_btn, bloodline_tab_btn, stone_tab_btn):
                if b is btn:
                    b.setStyleSheet(tab_style_active)
                else:
                    b.setStyleSheet(tab_style_default)

        normal_tab_btn.clicked.connect(lambda: (
            normal_scroll.setVisible(True), bloodline_scroll.setVisible(False), stone_scroll.setVisible(False),
            _activate(normal_tab_btn)))
        bloodline_tab_btn.clicked.connect(lambda: (
            normal_scroll.setVisible(False), bloodline_scroll.setVisible(True), stone_scroll.setVisible(False),
            _activate(bloodline_tab_btn)))
        stone_tab_btn.clicked.connect(lambda: (
            normal_scroll.setVisible(False), bloodline_scroll.setVisible(False), stone_scroll.setVisible(True),
            _activate(stone_tab_btn)))

        content_layout.addWidget(normal_scroll)
        content_layout.addWidget(bloodline_scroll)
        content_layout.addWidget(stone_scroll)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    # ─── 辅助构造函数 ───

    def _make_section_title(self, text):
        """章节标题：金色短线 + 文字"""
        wrap = QWidget()
        wrap.setStyleSheet("background: transparent; border: none;")
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        # 左短金线
        line1 = QWidget()
        line1.setFixedHeight(2)
        line1.setFixedWidth(18)
        line1.setStyleSheet(f"background-color: {PALETTE['gold_deep']}; border: none; border-radius: 1px;")
        lay.addWidget(line1)

        title = QLabel(text)
        title.setStyleSheet(f"""
            color: {PALETTE['text']};
            font-size: 18px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        lay.addWidget(title)

        # 右延伸淡金线
        line2 = QWidget()
        line2.setFixedHeight(1)
        line2.setStyleSheet(f"""
            background-color: {PALETTE['border']};
            border: none;
        """)
        lay.addWidget(line2, stretch=1)

        return wrap

    def _make_icon_card(self, title, value, icon_path, color):
        card = RoundedFrame()
        card.setFixedHeight(80)
        card.setMinimumWidth(110)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 12px;
                outline: none;
            }}
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 8, 10, 8)
        cl.setSpacing(2)
        cl.setAlignment(Qt.AlignCenter)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {PALETTE['text_sub']}; font-size: 11px; background: transparent; border: none;")
        title_lbl.setAlignment(Qt.AlignCenter)
        cl.addWidget(title_lbl)

        # 图标 + 数值 横排
        row = QHBoxLayout()
        row.setSpacing(4)
        row.setAlignment(Qt.AlignCenter)

        if os.path.exists(icon_path):
            icon_lbl = QLabel()
            ipm = QPixmap(icon_path)
            if not ipm.isNull():
                icon_lbl.setPixmap(ipm.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            icon_lbl.setAlignment(Qt.AlignCenter)
            icon_lbl.setStyleSheet("background: transparent; border: none;")
            row.addWidget(icon_lbl)

        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"color: {color}; font-size: 17px; font-weight: bold; background: transparent; border: none;")
        val_lbl.setAlignment(Qt.AlignCenter)
        row.addWidget(val_lbl)

        cl.addLayout(row)
        return card

    def _make_text_card(self, title, value, color):
        card = RoundedFrame()
        card.setFixedHeight(80)
        card.setMinimumWidth(110)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 12px;
                outline: none;
            }}
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(10, 8, 10, 8)
        cl.setSpacing(2)
        cl.setAlignment(Qt.AlignCenter)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {PALETTE['text_sub']}; font-size: 11px; background: transparent; border: none;")
        title_lbl.setAlignment(Qt.AlignCenter)
        cl.addWidget(title_lbl)

        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        val_lbl.setAlignment(Qt.AlignCenter)
        val_lbl.setWordWrap(True)
        cl.addWidget(val_lbl)
        return card

    def _make_gender_card(self, gender_text):
        card = RoundedFrame()
        card.setFixedHeight(80)
        card.setMinimumWidth(140)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 12px;
                outline: none;
            }}
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(8, 8, 8, 8)
        cl.setSpacing(2)
        cl.setAlignment(Qt.AlignCenter)

        title_lbl = QLabel("性别比例")
        title_lbl.setStyleSheet(f"color: {PALETTE['text_sub']}; font-size: 11px; background: transparent; border: none;")
        title_lbl.setAlignment(Qt.AlignCenter)
        cl.addWidget(title_lbl)

        text_str = str(gender_text) if gender_text is not None else ""
        male_pct = female_pct = ""
        if " / " in text_str:
            for part in text_str.split(" / "):
                p = part.strip()
                if p.startswith("雄"):
                    male_pct = p.replace("雄性 ", "")
                elif p.startswith("雌"):
                    female_pct = p.replace("雌性 ", "")
        elif text_str.startswith("雄"):
            male_pct = text_str.replace("雄性 ", "")
        elif text_str.startswith("雌"):
            female_pct = text_str.replace("雌性 ", "")

        row = QHBoxLayout()
        row.setSpacing(10)
        if male_pct:
            row.addWidget(self._make_gender_side("♂", "雄", male_pct, "#3c82c8"))
        if female_pct:
            row.addWidget(self._make_gender_side("♀", "雌", female_pct, "#d8609c"))
        cl.addLayout(row)
        return card

    def _make_gender_side(self, symbol, label, pct, color):
        w = QWidget()
        w.setStyleSheet("background: transparent; border: none;")
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(1)
        l.setAlignment(Qt.AlignCenter)

        top = QLabel(f"{symbol} {label}")
        top.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        top.setAlignment(Qt.AlignCenter)
        l.addWidget(top)

        bot = QLabel(pct)
        bot.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        bot.setAlignment(Qt.AlignCenter)
        l.addWidget(bot)
        return w

    def _build_name_lookup(self):
        """加载 pokemon_data.json 构建 name -> pokemon data 的查找表（带缓存）"""
        if hasattr(self.__class__, '_name_lookup_cache') and self.__class__._name_lookup_cache:
            return self.__class__._name_lookup_cache
        lookup = {}
        data_file = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "pokemon_data.json")
        try:
            if os.path.exists(data_file):
                with open(data_file, 'r', encoding='utf-8') as f:
                    for p in json.load(f):
                        n = p.get('name', '')
                        if n:
                            lookup[n] = p
        except Exception:
            pass
        self.__class__._name_lookup_cache = lookup
        return lookup

    def _build_evolution_chain_widget(self, chain_data, current_name):
        """chain_data: [(name, level, is_leader), ...]"""
        wrap = RoundedFrame()
        wrap.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 250, 240, 0.7);
                border: 1px solid {PALETTE['border']};
                border-radius: 12px;
                outline: none;
            }}
        """)
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        name_to_data = self._build_name_lookup()

        for i, (evo_name, evo_level, is_leader) in enumerate(chain_data):
            card = self._make_evo_card(
                evo_name, evo_level, is_leader,
                is_current=(evo_name == current_name),
                name_to_data=name_to_data)
            layout.addWidget(card, alignment=Qt.AlignVCenter | Qt.AlignHCenter)

            if i < len(chain_data) - 1:
                arrow = QLabel("→")
                arrow.setStyleSheet(
                    f"color: {PALETTE['gold_deep']}; font-size: 24px;"
                    f" font-weight: bold; background: transparent; border: none;")
                arrow.setAlignment(Qt.AlignCenter)
                layout.addWidget(arrow, alignment=Qt.AlignVCenter | Qt.AlignHCenter)

        layout.addStretch()
        return wrap

    def _make_evo_card(self, name, level, is_leader, is_current, name_to_data):
        """单个进化卡片：等级徽章 + 精灵图（属性光环）+ 名字 + 首领标"""
        card = QWidget()
        card.setFixedWidth(108)
        card.setStyleSheet("background: transparent; border: none;")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignCenter)

        # 等级徽章（保持高度一致：无等级时占位）
        if level is not None:
            lv = QLabel(f"Lv.{level}")
            lv.setStyleSheet(f"""
                background-color: {PALETTE['gold_light']};
                color: {PALETTE['text_on_gold']};
                padding: 2px 10px;
                border-radius: 8px;
                font-size: 11px;
                font-weight: bold;
            """)
            lv.setAlignment(Qt.AlignCenter)
            lv.setFixedHeight(18)
            lay.addWidget(lv, alignment=Qt.AlignCenter)
        else:
            lay.addSpacing(18)

        # 精灵图（带属性色光环 + 圆形边框）
        poke_data = name_to_data.get(name, {})
        pid = poke_data.get('id', 0)
        attr = poke_data.get('attribute', '')

        img_label = QLabel()
        img_label.setFixedSize(78, 78)
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setStyleSheet("background: transparent; border: none;")

        dpr = _get_dpr()
        phys78 = int(78 * dpr)
        composited = QPixmap(phys78, phys78)
        composited.fill(Qt.transparent)
        painter = QPainter(composited)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.scale(dpr, dpr)

        # 属性色径向光环
        if attr:
            primary = attr.split('/')[0] if '/' in attr else attr
            halo_inner, halo_outer = _type_halo(primary)
            halo_grad = QRadialGradient(39, 39, 39)
            halo_grad.setColorAt(0, halo_inner)
            halo_grad.setColorAt(1, halo_outer)
            painter.setBrush(QBrush(halo_grad))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, 78, 78)

        # 精灵图
        pm = PokemonCard._get_pokemon_pixmap(pid, size=70) if pid else None
        if pm and not pm.isNull():
            scaled = _scale_hdpi(pm, 58)
            x = (78 - scaled.width() / dpr) // 2
            y = (78 - scaled.height() / dpr) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            # 无图占位：显示名字首字
            font = painter.font()
            font.setPointSize(20)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(QColor(PALETTE['text_mute'])))
            painter.drawText(QRectF(0, 0, 78, 78), Qt.AlignCenter, name[:1] if name else '?')

        # 圆形边框（当前形态高亮）
        border_color = PALETTE['gold_deep'] if is_current else PALETTE['border']
        border_w = 2.0 if is_current else 1.2
        painter.setPen(QPen(QColor(border_color), border_w))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(0.6, 0.6, 76.8, 76.8))

        painter.end()
        composited.setDevicePixelRatio(dpr)
        img_label.setPixmap(composited)
        lay.addWidget(img_label, alignment=Qt.AlignCenter)

        # 名字
        name_text = f"● {name}" if is_current else name
        name_label = QLabel(name_text)
        if is_current:
            name_label.setStyleSheet(f"""
                color: {PALETTE['gold_deep']};
                font-size: 13px;
                font-weight: bold;
                background-color: {PALETTE['gold_light']};
                padding: 3px 10px;
                border-radius: 8px;
                border: 1px solid {PALETTE['gold']};
            """)
        else:
            name_label.setStyleSheet(f"""
                color: {PALETTE['text']};
                font-size: 12px;
                font-weight: 600;
                background-color: {PALETTE['bg_card']};
                padding: 3px 10px;
                border-radius: 8px;
                border: 1px solid {PALETTE['border_soft']};
            """)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(False)
        lay.addWidget(name_label, alignment=Qt.AlignCenter)

        # 首领标
        if is_leader:
            lt = QLabel("★ 首领")
            lt.setStyleSheet(f"""
                color: {PALETTE['leader']};
                font-size: 10px;
                font-weight: bold;
                background: transparent;
                border: none;
            """)
            lt.setAlignment(Qt.AlignCenter)
            lt.setFixedHeight(14)
            lay.addWidget(lt, alignment=Qt.AlignCenter)
        else:
            lay.addSpacing(14)

        return card

    def _build_ability_box(self, name, desc):
        box = RoundedFrame()
        box.setStyleSheet(f"""
            QFrame {{
                background-color: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-left: 4px solid {PALETTE['gold_deep']};
                border-radius: 12px;
                outline: none;
            }}
        """)
        bl = QVBoxLayout(box)
        bl.setContentsMargins(18, 14, 18, 14)
        bl.setSpacing(8)

        if name:
            # 特性图标 + 名称 横排
            name_row = QHBoxLayout()
            name_row.setSpacing(10)
            name_row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            ability_pm = _ability_icon(name, size=48)
            if ability_pm and not ability_pm.isNull():
                icon_lbl = QLabel()
                icon_lbl.setPixmap(ability_pm)
                icon_lbl.setFixedSize(48, 48)
                icon_lbl.setStyleSheet(
                    f"background-color: {PALETTE['bg_inset']};"
                    f" border: 1px solid {PALETTE['border']};"
                    f" border-radius: 6px;"
                )
                icon_lbl.setAlignment(Qt.AlignCenter)
                name_row.addWidget(icon_lbl, alignment=Qt.AlignVCenter)

            nl = QLabel(name)
            nl.setStyleSheet(f"""
                color: {PALETTE['gold_deep']};
                font-size: 16px;
                font-weight: bold;
                background: transparent;
                border: none;
            """)
            name_row.addWidget(nl)
            name_row.addStretch()
            bl.addLayout(name_row)
        if desc:
            dl = QLabel(desc)
            dl.setStyleSheet(f"""
                color: {PALETTE['text']};
                font-size: 13px;
                line-height: 1.5;
                background: transparent;
                border: none;
            """)
            dl.setWordWrap(True)
            bl.addWidget(dl)
        return box

    def _make_skill_scroll(self, skills, kind='normal'):
        """创建技能滚动区"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(420)
        scroll.setStyleSheet(SCROLL_BAR_STYLE)

        content = QWidget()
        content.setStyleSheet("background: transparent; border: none;")
        grid = QGridLayout(content)
        grid.setSpacing(10)
        grid.setContentsMargins(8, 8, 8, 8)

        for i, skill in enumerate(skills):
            box = self._make_skill_box(skill, kind=kind)
            row = i // 2
            col = i % 2
            grid.addWidget(box, row, col)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        scroll.setWidget(content)
        return scroll

    def _make_skill_box(self, skill, kind='normal'):
        box = RoundedFrame()
        box.setCursor(Qt.PointingHandCursor)

        side_colors = {
            'normal':    PALETTE['gold_deep'],
            'bloodline': '#b84a7d',
            'stone':     '#2a8a6a',
        }
        side_color = side_colors.get(kind, PALETTE['gold_deep'])

        box.setStyleSheet(f"""
            QFrame {{
                background-color: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-left: 4px solid {side_color};
                border-radius: 10px;
                outline: none;
            }}
            QFrame:hover {{
                background-color: {PALETTE['bg_hover']};
                border: 1px solid {PALETTE['gold']};
                border-left: 4px solid {side_color};
            }}
        """)

        outer = QHBoxLayout(box)
        outer.setSpacing(8)
        outer.setContentsMargins(10, 8, 12, 8)

        skill_name = skill.get('name', '')

        skill_pm = _skill_icon(skill_name, size=48)
        if skill_pm and not skill_pm.isNull():
            skill_icon_lbl = QLabel()
            skill_icon_lbl.setPixmap(skill_pm)
            skill_icon_lbl.setFixedSize(48, 48)
            skill_icon_lbl.setStyleSheet("background: transparent; border: none;")
            skill_icon_lbl.setAlignment(Qt.AlignCenter)
            outer.addWidget(skill_icon_lbl, alignment=Qt.AlignVCenter)

        content = QWidget()
        content.setStyleSheet("background: transparent; border: none;")
        content_lay = QVBoxLayout(content)
        content_lay.setSpacing(3)
        content_lay.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.setSpacing(6)

        attr = skill.get('attribute', '')
        if attr:
            attr_pm = _get_attr_icon(attr, size=18)
            if attr_pm and not attr_pm.isNull():
                attr_lbl = QLabel()
                attr_lbl.setPixmap(attr_pm)
                attr_lbl.setFixedSize(18, 18)
                attr_lbl.setStyleSheet("background: transparent; border: none;")
                attr_lbl.setAlignment(Qt.AlignCenter)
                attr_lbl.setToolTip(attr.replace('系', ''))
                header.addWidget(attr_lbl, alignment=Qt.AlignVCenter)
            else:
                attr_tag = _make_attr_pill(attr, font_size=10, icon_size=12,
                                           pad_h=6, pad_v=1, radius=6)
                header.addWidget(attr_tag, alignment=Qt.AlignVCenter)

        name_lbl = QLabel(skill_name)
        name_lbl.setStyleSheet(f"color: {PALETTE['text']}; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        header.addWidget(name_lbl, alignment=Qt.AlignVCenter)

        header.addStretch()

        cost = skill.get('cost', '')
        energy_slot = QWidget()
        energy_slot.setFixedWidth(44)
        energy_slot.setStyleSheet("background: transparent; border: none;")
        energy_lay = QHBoxLayout(energy_slot)
        energy_lay.setContentsMargins(0, 0, 0, 0)
        energy_lay.setSpacing(2)
        energy_lay.setAlignment(Qt.AlignCenter)
        if cost and str(cost) != '0':
            cost_pm = _load_icon(os.path.join(_SC_SC_DIR, "能耗.png"), size=16)
            if cost_pm and not cost_pm.isNull():
                cost_icon_lbl = QLabel()
                cost_icon_lbl.setPixmap(cost_pm)
                cost_icon_lbl.setFixedSize(16, 16)
                cost_icon_lbl.setStyleSheet("background: transparent; border: none;")
                cost_icon_lbl.setAlignment(Qt.AlignCenter)
                energy_lay.addWidget(cost_icon_lbl, alignment=Qt.AlignVCenter)
            c_lbl = QLabel(str(cost))
            c_lbl.setStyleSheet(f"color: #3c82c8; font-size: 13px; font-weight: bold; background: transparent; border: none;")
            energy_lay.addWidget(c_lbl, alignment=Qt.AlignVCenter)
        header.addWidget(energy_slot, alignment=Qt.AlignVCenter)

        header.addSpacing(28)

        skill_type = skill.get('type', '')
        type_slot = QWidget()
        type_slot.setFixedWidth(22)
        type_slot.setStyleSheet("background: transparent; border: none;")
        type_lay = QHBoxLayout(type_slot)
        type_lay.setContentsMargins(0, 0, 0, 0)
        type_lay.setAlignment(Qt.AlignCenter)
        if skill_type:
            type_tag = _make_skill_type_badge(skill_type, icon_size=18)
            type_lay.addWidget(type_tag, alignment=Qt.AlignVCenter)
        header.addWidget(type_slot, alignment=Qt.AlignVCenter)

        power = skill.get('power', '')
        power_slot = QWidget()
        power_slot.setFixedWidth(34)
        power_slot.setStyleSheet("background: transparent; border: none;")
        power_lay = QHBoxLayout(power_slot)
        power_lay.setContentsMargins(0, 0, 0, 0)
        power_lay.setAlignment(Qt.AlignCenter)
        if power and str(power) != '0':
            p_lbl = QLabel(str(power))
            p_lbl.setStyleSheet(f"color: #c8463c; font-size: 14px; font-weight: bold; background: transparent; border: none;")
            p_lbl.setToolTip("威力")
            power_lay.addWidget(p_lbl, alignment=Qt.AlignVCenter)
        header.addWidget(power_slot, alignment=Qt.AlignVCenter)

        content_lay.addLayout(header)

        desc = skill.get('description', '')
        if desc:
            dl = QLabel(f"✦ {desc}")
            dl.setStyleSheet(f"color: {PALETTE['text_sub']}; font-size: 11px; background: transparent; border: none;")
            dl.setWordWrap(True)
            content_lay.addWidget(dl)

        outer.addWidget(content, 1)

        def on_clicked(event):
            parent = box.parent()
            while parent:
                if hasattr(parent, 'show_skill_detail'):
                    parent.show_skill_detail(skill)
                    return
                parent = parent.parent()

        box.mousePressEvent = on_clicked
        return box

    def go_back(self):
        parent = self.parent()
        while parent:
            if hasattr(parent, 'show_list'):
                parent.show_list()
                return
            parent = parent.parent()


# ────────────────────────────────────────────────────────────────
# 主视图 - 童话风
# ────────────────────────────────────────────────────────────────
class PokedexWidget(ParchmentWidget):
    """精灵图鉴主界面 - 童话风"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pokemon_data = []
        self.filtered_data = []
        self.show_extra_info = False
        self.sort_ascending = True
        self.current_view = 'list'
        self._search_debounce_timer = QTimer(self)
        self._search_debounce_timer.setSingleShot(True)
        self._search_debounce_timer.setInterval(250)
        self._search_debounce_timer.timeout.connect(self.apply_filters)
        self.init_ui()
        self.load_data()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                item.widget().clearFocus()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 列表视图容器
        self.list_container = ParchmentWidget()
        list_layout = QVBoxLayout(self.list_container)
        list_layout.setContentsMargins(28, 22, 28, 18)
        list_layout.setSpacing(14)

        # ── 标题区 ──
        title_wrap = QWidget()
        title_wrap.setStyleSheet("background: transparent; border: none;")
        title_grid = QVBoxLayout(title_wrap)
        title_grid.setContentsMargins(0, 0, 0, 0)
        title_grid.setSpacing(4)

        title = QLabel("✦  精 灵 图 鉴  ✦")
        title.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))
        title.setStyleSheet(f"color: {PALETTE['text']}; background: transparent; border: none;")
        title.setAlignment(Qt.AlignCenter)
        title_grid.addWidget(title)

        # 数据来源说明
        source_label = QLabel("数据来源：BWIKI 全体贡献者 · https://wiki.biligame.com/rocom/")
        source_label.setStyleSheet(f"color: {PALETTE['text_mute']}; font-size: 10px; background: transparent; border: none;")
        source_label.setAlignment(Qt.AlignCenter)
        title_grid.addWidget(source_label)

        list_layout.addWidget(title_wrap)

        # ── 搜索栏 ──
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  搜索精灵名 / 编号 ...")
        self.search_input.setFixedHeight(40)
        self.search_input.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 20px;
                padding: 8px 18px;
                color: {PALETTE['text']};
                font-size: 13px;
                outline: none;
            }}
            QLineEdit:focus {{
                border: 2px solid {PALETTE['gold_deep']};
                background-color: white;
                padding: 7px 17px;
            }}
            QLineEdit:hover {{
                border: 1px solid {PALETTE['gold']};
            }}
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        search_row.addWidget(self.search_input, stretch=2)

        # 属性筛选
        self.type_filter = QComboBox()
        self.type_filter.addItem("全部属性")
        self.type_filter.setFixedHeight(40)
        self.type_filter.setFixedWidth(120)
        self.type_filter.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.type_filter.setStyleSheet(self._combo_style())
        self.type_filter.currentTextChanged.connect(self.on_filter_changed)
        search_row.addWidget(self.type_filter)

        list_layout.addLayout(search_row)

        # ── 统计信息 ──
        self.stats_label = QLabel("加载中...")
        self.stats_label.setStyleSheet(f"""
            color: {PALETTE['text_sub']};
            font-size: 12px;
            background: transparent;
            border: none;
            padding: 2px 4px;
        """)
        list_layout.addWidget(self.stats_label)

        # ── 工具栏 ──
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 250, 240, 0.7);
                border: 1px solid {PALETTE['border']};
                border-radius: 14px;
                outline: none;
            }}
        """)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(14, 8, 14, 8)
        tb_layout.setSpacing(10)

        # 额外信息开关
        self.extra_toggle = QPushButton()
        self.extra_toggle.setCheckable(True)
        self.extra_toggle.setChecked(False)
        self.extra_toggle.setFixedHeight(32)
        self.extra_toggle.setCursor(Qt.PointingHandCursor)
        self.extra_toggle.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.extra_toggle.toggled.connect(self._on_extra_toggled)
        self._update_toggle_style()
        tb_layout.addWidget(self.extra_toggle)

        tb_layout.addWidget(self._make_sep())

        # 蛋组
        eg_label = QLabel("蛋组")
        eg_label.setStyleSheet(f"color: {PALETTE['text_sub']}; font-size: 12px; background: transparent; border: none;")
        tb_layout.addWidget(eg_label)

        self.egg_group_combo = QComboBox()
        self.egg_group_combo.addItem("全部")
        self.egg_group_combo.setFixedHeight(32)
        self.egg_group_combo.setMinimumWidth(95)
        self.egg_group_combo.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.egg_group_combo.setStyleSheet(self._combo_style())
        self.egg_group_combo.currentTextChanged.connect(self._on_filter_or_sort_changed)
        tb_layout.addWidget(self.egg_group_combo)

        tb_layout.addWidget(self._make_sep())

        # 排序
        sort_label = QLabel("排序")
        sort_label.setStyleSheet(f"color: {PALETTE['text_sub']}; font-size: 12px; background: transparent; border: none;")
        tb_layout.addWidget(sort_label)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["编号", "名称", "星光值", "洛克贝", "种族值"])
        self.sort_combo.setCurrentIndex(0)
        self.sort_combo.setFixedHeight(32)
        self.sort_combo.setMinimumWidth(85)
        self.sort_combo.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.sort_combo.setStyleSheet(self._combo_style())
        self.sort_combo.currentTextChanged.connect(self._on_filter_or_sort_changed)
        tb_layout.addWidget(self.sort_combo)

        # 升降序
        self.order_btn = QPushButton("↑ 升序")
        self.order_btn.setCheckable(True)
        self.order_btn.setChecked(True)
        self.order_btn.setFixedHeight(32)
        self.order_btn.setFixedWidth(80)
        self.order_btn.setCursor(Qt.PointingHandCursor)
        self.order_btn.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.order_btn.setStyleSheet(self._order_btn_style(True))
        self.order_btn.clicked.connect(self._on_order_toggle)
        tb_layout.addWidget(self.order_btn)

        tb_layout.addWidget(self._make_sep())

        # 进化阶段
        stage_label = QLabel("阶段")
        stage_label.setStyleSheet(f"color: {PALETTE['text_sub']}; font-size: 12px; background: transparent; border: none;")
        tb_layout.addWidget(stage_label)

        self.stage_combo = QComboBox()
        self.stage_combo.addItems(["全部", "1阶", "2阶", "3阶", "最终形态", "无法进化"])
        self.stage_combo.setFixedHeight(32)
        self.stage_combo.setMinimumWidth(75)
        self.stage_combo.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.stage_combo.setStyleSheet(self._combo_style())
        self.stage_combo.currentTextChanged.connect(self._on_filter_or_sort_changed)
        tb_layout.addWidget(self.stage_combo)

        tb_layout.addStretch()
        list_layout.addWidget(toolbar)

        # ── 网格滚动区 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(SCROLL_BAR_STYLE)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent; border: none;")
        self.grid_layout = QGridLayout(self.content_widget)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setContentsMargins(6, 6, 6, 6)

        scroll.setWidget(self.content_widget)
        list_layout.addWidget(scroll)

        self.main_layout.addWidget(self.list_container)

    def _make_sep(self):
        sep = QLabel("|")
        sep.setStyleSheet(f"color: {PALETTE['border_dark']}; font-size: 14px; background: transparent; border: none; padding: 0 2px;")
        return sep

    def _combo_style(self):
        import os as _os
        _arrow_path = _os.path.join(_os.path.dirname(__file__), "assets", "down_arrow.svg").replace('\\', '/')
        return f"""
            QComboBox {{
                background-color: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 16px;
                padding: 4px 14px;
                color: {PALETTE['text']};
                font-size: 12px;
                outline: none;
            }}
            QComboBox:hover {{
                border: 1px solid {PALETTE['gold']};
                background-color: {PALETTE['bg_hover']};
            }}
            QComboBox:focus {{
                border: 2px solid {PALETTE['gold_deep']};
                padding: 3px 13px;
            }}
            QComboBox::drop-down {{ border: none; width: 16px; }}
            QComboBox::down-arrow {{
                image: url({_arrow_path});
                width: 10px;
                height: 6px;
                margin-right: 4px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {PALETTE['bg_card']};
                color: {PALETTE['text']};
                border: 1px solid {PALETTE['border_dark']};
                border-radius: 8px;
                selection-background-color: {PALETTE['gold_light']};
                selection-color: {PALETTE['text_on_gold']};
                padding: 4px;
                outline: none;
            }}
        """

    def _order_btn_style(self, asc):
        if asc:
            return f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {PALETTE['gold']}, stop:1 {PALETTE['gold_deep']});
                    color: white;
                    border: 1px solid {PALETTE['gold_deep']};
                    border-radius: 16px;
                    font-size: 12px;
                    font-weight: bold;
                    outline: none;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {PALETTE['gold_light']}, stop:1 {PALETTE['gold']});
                }}
            """
        return f"""
            QPushButton {{
                background-color: {PALETTE['bg_card']};
                color: {PALETTE['text_sub']};
                border: 1px solid {PALETTE['border']};
                border-radius: 16px;
                font-size: 12px;
                font-weight: 600;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {PALETTE['bg_hover']};
                border: 1px solid {PALETTE['gold']};
            }}
        """

    # ─── 视图切换 ───

    def show_list(self):
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.hide()

        self.main_layout.addWidget(self.list_container)
        self.list_container.show()

        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                item.widget().clearFocus()

        # 清除父窗口导航按钮active状态
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
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.hide()

        enriched_pokemon = self.get_enriched_data(pokemon)
        detail_widget = PokemonDetailWidget(enriched_pokemon)
        self.main_layout.addWidget(detail_widget)
        self.current_view = 'detail'

    def get_enriched_data(self, basic_pokemon):
        pid = basic_pokemon.get('id', 0)
        name = basic_pokemon.get('name', '')
        is_leader = basic_pokemon.get('is_leader_form', False)
        source_form = basic_pokemon.get('source_final_form', '')

        enriched_file = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "lkwg_enriched_data.json")
        try:
            if os.path.exists(enriched_file):
                with open(enriched_file, 'r', encoding='utf-8') as f:
                    enriched_list = json.load(f)

                    for p in enriched_list:
                        if p.get('id') == pid or p.get('name') == name:
                            merged = dict(basic_pokemon)
                            for k, v in p.items():
                                if v is not None:
                                    merged[k] = v
                            if not merged.get('description') and basic_pokemon.get('description'):
                                merged['description'] = basic_pokemon['description']
                            if is_leader and source_form:
                                leader_skills = self._inherit_skills_from_source(
                                    enriched_list, source_form, merged.get('skills', {}))
                                if leader_skills:
                                    merged['skills'] = leader_skills
                            return merged

                    if is_leader and source_form:
                        merged = dict(basic_pokemon)
                        leader_skills = self._inherit_skills_from_source(
                            enriched_list, source_form, {})
                        if leader_skills:
                            merged['skills'] = leader_skills
                        return merged
        except Exception as e:
            print(f"加载增强数据失败: {e}")
        return basic_pokemon

    def _inherit_skills_from_source(self, enriched_list, source_name, current_skills):
        for p in enriched_list:
            if p.get('name') == source_name:
                source_skills = p.get('skills', {})
                if source_skills:
                    return {
                        "normal_skills": source_skills.get('normal_skills', []),
                        "bloodline_skills": source_skills.get('bloodline_skills', []),
                        "stone_skills": source_skills.get('stone_skills', []),
                    }
        return current_skills

    def show_skill_detail(self, skill):
        dialog = SkillDetailDialog(skill, self.pokemon_data, self)
        dialog.exec()
        # 如果用户点击了某个学习精灵，跳转到该精灵详情
        if dialog.selected_pokemon:
            self.show_detail(dialog.selected_pokemon)

    def load_data(self):
        data_file = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "pokemon_data.json")
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                self.pokemon_data = json.load(f)

            enriched_file = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "lkwg_enriched_data.json")
            try:
                if os.path.exists(enriched_file):
                    with open(enriched_file, 'r', encoding='utf-8') as f:
                        enriched_list = json.load(f)
                    evo_lookup = {}
                    for ep in enriched_list:
                        ename = ep.get('name', '')
                        evo = ep.get('evolution')
                        if ename and evo is not None:
                            evo_lookup[ename] = evo
                    for pokemon in self.pokemon_data:
                        pname = pokemon.get('name', '')
                        if pname in evo_lookup:
                            enriched_evo = evo_lookup[pname]
                            if not pokemon.get('evolution'):
                                pokemon['evolution'] = enriched_evo
            except Exception:
                pass

            types = set()
            egg_groups = set()
            for pokemon in self.pokemon_data:
                attr = pokemon.get('attribute', '')
                if attr:
                    if '/' in attr:
                        types.update(attr.split('/'))
                    else:
                        types.add(attr)
                eg = pokemon.get('egg_groups', [])
                for e in eg:
                    egg_groups.add(e)

            for t in sorted(types):
                self.type_filter.addItem(t)
            for eg in sorted(egg_groups):
                self.egg_group_combo.addItem(eg)

            self.filtered_data = self.pokemon_data.copy()
            self.refresh_display()

        except Exception as e:
            self.stats_label.setText(f"加载失败: {str(e)}")

    def on_search_changed(self, text):
        self._search_debounce_timer.start()

    def on_filter_changed(self, text):
        self.apply_filters()

    def _update_toggle_style(self):
        if self.extra_toggle.isChecked():
            self.extra_toggle.setText("✦ 详 ON")
            self.extra_toggle.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {PALETTE['gold']}, stop:1 {PALETTE['gold_deep']});
                    color: white;
                    border: 1px solid {PALETTE['gold_deep']};
                    border-radius: 16px;
                    padding: 0 14px;
                    font-size: 12px;
                    font-weight: bold;
                    outline: none;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {PALETTE['gold_light']}, stop:1 {PALETTE['gold']});
                }}
            """)
        else:
            self.extra_toggle.setText("✦ 详 OFF")
            self.extra_toggle.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PALETTE['bg_card']};
                    color: {PALETTE['text_sub']};
                    border: 1px solid {PALETTE['border']};
                    border-radius: 16px;
                    padding: 0 14px;
                    font-size: 12px;
                    font-weight: 600;
                    outline: none;
                }}
                QPushButton:hover {{
                    background-color: {PALETTE['bg_hover']};
                    border: 1px solid {PALETTE['gold']};
                }}
            """)

    def _on_extra_toggled(self, checked):
        self.show_extra_info = checked
        self._update_toggle_style()
        self._card_pool = []
        self.refresh_display()

    def _on_filter_or_sort_changed(self, text):
        self.apply_filters()

    def _on_order_toggle(self):
        self.sort_ascending = self.order_btn.isChecked()
        self.order_btn.setText("↑ 升序" if self.sort_ascending else "↓ 降序")
        self.order_btn.setStyleSheet(self._order_btn_style(self.sort_ascending))
        self.apply_filters()

    @staticmethod
    def _is_leader_related(entry):
        if entry.get('is_leader'):
            return True
        name = entry.get('name', '')
        return '国王' in name or '首领' in name

    @staticmethod
    def _get_stage(pokemon):
        if pokemon.get('is_leader_form'):
            return None
        name = pokemon.get('name', '')
        chain = pokemon.get('evolution_chain', [])
        evolution = pokemon.get('evolution', [])

        if chain:
            non_leader = [e for e in chain if not e.get('is_leader')]
            if not non_leader:
                if evolution == ['无法进化'] or not evolution:
                    return '无法进化'
                return None
            if len(non_leader) <= 1:
                if non_leader[0].get('name') != name:
                    return None
                if evolution and evolution != ['无法进化']:
                    if len(evolution) == 1 and evolution[0] == name:
                        return '无法进化'
                    return '1阶'
                return '无法进化'
            for i, e in enumerate(non_leader):
                if e.get('name') == name:
                    remaining = non_leader[i+1:]
                    if remaining and all(PokedexWidget._is_leader_related(r) for r in remaining):
                        return '无法进化'
                    stage = i + 1
                    if stage >= 3:
                        return '3阶'
                    return f'{stage}阶'
            return None

        if evolution and evolution != ['无法进化']:
            if len(evolution) == 1 and evolution[0] == name:
                return '无法进化'
            return '1阶'
        return '无法进化'

    @staticmethod
    def _is_final_form(pokemon):
        if pokemon.get('is_leader_form'):
            return False
        name = pokemon.get('name', '')
        chain = pokemon.get('evolution_chain', [])
        if chain:
            non_leader = [e for e in chain if not e.get('is_leader')]
            if not non_leader:
                return False
            return non_leader[-1].get('name') == name
        evolution = pokemon.get('evolution', [])
        if not evolution or evolution == ['无法进化']:
            return True
        if len(evolution) == 1 and evolution[0] == name:
            return True
        return False

    def apply_filters(self):
        search_text = self.search_input.text().lower()
        type_filter = self.type_filter.currentText()
        egg_group_filter = self.egg_group_combo.currentText()
        sort_text = self.sort_combo.currentText()

        old_keys = {id(p) for p in self.filtered_data} if self.filtered_data else None

        raw_order = {id(p): i for i, p in enumerate(self.pokemon_data)}
        sort_key_map = {
            "编号": lambda p: raw_order.get(id(p), 0),
            "名称": lambda p: p.get('name', ''),
            "星光值": lambda p: int(p.get('starlight', 0) or 0),
            "洛克贝": lambda p: int(p.get('review_cost', 0) or 0),
            "种族值": lambda p: int(p.get('stats', {}).get('total', 0) or 0),
        }
        sort_fn = sort_key_map.get(sort_text, sort_key_map["编号"])

        filtered = []
        for pokemon in self.pokemon_data:
            name = pokemon.get('name', '').lower()
            pid = str(pokemon.get('id', ''))

            if search_text and search_text not in name and search_text not in pid:
                continue
            if type_filter != "全部属性":
                attr = pokemon.get('attribute', '')
                if type_filter not in attr:
                    continue
            if egg_group_filter != "全部":
                eg_list = pokemon.get('egg_groups', [])
                if egg_group_filter not in eg_list:
                    continue

            stage_filter = self.stage_combo.currentText()
            if stage_filter != "全部":
                if stage_filter == "最终形态":
                    if not self._is_final_form(pokemon):
                        continue
                else:
                    pokemon_stage = self._get_stage(pokemon)
                    if pokemon_stage != stage_filter:
                        continue

            filtered.append(pokemon)

        filtered.sort(key=sort_fn, reverse=not self.sort_ascending)

        new_keys = {id(p) for p in filtered}
        if old_keys is not None and old_keys == new_keys:
            pass
        else:
            self._card_pool = []

        self.filtered_data = filtered
        self.refresh_display()

    def refresh_display(self):
        columns = 3
        total = len(self.pokemon_data)
        shown = len(self.filtered_data)
        self.stats_label.setText("")

        pool = getattr(self, '_card_pool', [])
        if pool:
            pool_keys = [id(p) for p, _ in pool]
            filtered_keys = [id(p) for p in self.filtered_data]

            if len(pool_keys) == len(filtered_keys) and set(pool_keys) == set(filtered_keys):
                id_to_card = {id(p): card for p, card in pool}

                while self.grid_layout.count():
                    item = self.grid_layout.takeAt(0)
                    if item.widget():
                        item.widget().setParent(None)

                for idx, pokemon in enumerate(self.filtered_data):
                    row, col = divmod(idx, columns)
                    self.grid_layout.addWidget(id_to_card[id(pokemon)], row, col)

                self.grid_layout.setRowStretch(self.grid_layout.rowCount(), 1)
                return

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._card_pool = []

        for idx, pokemon in enumerate(self.filtered_data):
            row = idx // columns
            col = idx % columns

            card = PokemonCard(pokemon, show_extra=self.show_extra_info)
            self._card_pool.append((pokemon, card))
            self.grid_layout.addWidget(card, row, col)

        self.grid_layout.setRowStretch(self.grid_layout.rowCount(), 1)
