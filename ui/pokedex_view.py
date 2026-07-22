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
from PySide6.QtCore import Qt, QRectF, QTimer
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

from PySide6.QtWidgets import (
    QDialog, QTextBrowser
)


class SkillDetailDialog(QDialog):
    """技能详情对话框"""
    
    def __init__(self, skill, all_pokemons, parent=None):
        super().__init__(parent)
        self.skill = skill
        self.all_pokemons = all_pokemons
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"技能详情 - {self.skill.get('name', '未知技能')}")
        self.setFixedSize(520, 620)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        
        # 设置背景
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(15, 15, 25, 0.95);
                border: 1px solid #5a4a9a;
                border-radius: 12px;
                outline: none;
            }
        """)
        
        # 外层布局：滚动区域 + 关闭按钮
        outer_layout = QVBoxLayout(self)
        outer_layout.setSpacing(8)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        
        # 滚动区域（包含标题、技能信息、精灵列表）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: rgba(30, 30, 45, 0.6);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(139, 92, 246, 0.4);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # 滚动区域内容容器
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        # 技能标题
        title_label = QLabel(self.skill.get('name', '未知技能'))
        title_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title_label)
        
        # 技能基本信息
        info_widget = QWidget()
        info_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(139, 92, 246, 0.1);
                border: 1px solid #3d2d6e;
                border-radius: 8px;
                padding: 15px;
                outline: none;
            }
        """)
        info_layout = QGridLayout(info_widget)
        info_layout.setSpacing(10)
        
        row = 0
        
        # 属性
        attr = self.skill.get('attribute', '')
        if attr:
            info_layout.addWidget(QLabel("属性:"), row, 0)
            attr_label = QLabel(attr)
            attr_label.setStyleSheet("color: #a78bfa; font-weight: bold;")
            info_layout.addWidget(attr_label, row, 1)
            row += 1
        
        # 类型
        skill_type = self.skill.get('type', '')
        if skill_type:
            info_layout.addWidget(QLabel("类型:"), row, 0)
            type_colors = {
                '物攻': '#f87171',
                '魔攻': '#60a5fa',
                '状态': '#34d399',
                '防御': '#fbbf24'
            }
            type_color = type_colors.get(skill_type, '#9ca3af')
            type_label = QLabel(f'<span style="color: {type_color};">{skill_type}</span>')
            info_layout.addWidget(type_label, row, 1)
            row += 1
        
        # 威力
        power = self.skill.get('power', '')
        if power and power != '0':
            info_layout.addWidget(QLabel("威力:"), row, 0)
            power_label = QLabel(f'<span style="color: #fbbf24;">{power}</span>')
            info_layout.addWidget(power_label, row, 1)
            row += 1
        
        # 能耗
        cost = self.skill.get('cost', '')
        if cost and cost != '0':
            info_layout.addWidget(QLabel("能耗:"), row, 0)
            cost_label = QLabel(f'<span style="color: #60a5fa;">{cost}</span>')
            info_layout.addWidget(cost_label, row, 1)
            row += 1
        
        # 技能描述
        desc = self.skill.get('description', '')
        if desc:
            info_layout.addWidget(QLabel("描述:"), row, 0)
            row += 1
            info_layout.addWidget(QLabel(desc), row, 0, 1, 2)
        
        main_layout.addWidget(info_widget)
        
        # 能学会此技能的精灵
        learners_label = QLabel("能学会此技能的精灵:")
        learners_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        main_layout.addWidget(learners_label)
        
        # 查找能学会此技能的精灵
        skill_name = self.skill.get('name', '')
        self.learners = self._find_learners(skill_name)
        self._learners_expanded = False
        
        if self.learners:
            learners_widget = QWidget()
            learners_widget.setStyleSheet("""
                QWidget {
                    background-color: rgba(52, 211, 153, 0.1);
                    border: 1px solid #1a694b;
                    border-radius: 8px;
                    outline: none;
                }
            """)
            learners_layout = QVBoxLayout(learners_widget)
            learners_layout.setSpacing(5)
            learners_layout.setContentsMargins(12, 12, 12, 12)
            
            self._learners_content = QLabel()
            self._learners_content.setStyleSheet("color: #34d399; font-size: 13px;")
            self._learners_content.setWordWrap(True)
            self._update_learners_text()
            learners_layout.addWidget(self._learners_content)
            
            # 展开/收起按钮（仅当精灵数超过20时显示）
            if len(self.learners) > 20:
                self._expand_btn = QPushButton(f"展开全部 ({len(self.learners)}只)")
                self._expand_btn.setFixedHeight(28)
                self._expand_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(52, 211, 153, 0.2);
                        color: #34d399;
                        border: 1px solid #1a694b;
                        border-radius: 4px;
                        font-size: 12px;
                        outline: none;
                    }
                    QPushButton:hover {
                        background-color: rgba(52, 211, 153, 0.35);
                    }
                """)
                self._expand_btn.clicked.connect(self._toggle_learners)
                learners_layout.addWidget(self._expand_btn)
            else:
                self._expand_btn = None
            
            main_layout.addWidget(learners_widget)
        else:
            no_learners = QLabel("暂无数据")
            no_learners.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 13px;")
            main_layout.addWidget(no_learners)
        
        # 底部弹簧，将内容推到顶部
        main_layout.addStretch()
        
        scroll.setWidget(content_widget)
        outer_layout.addWidget(scroll)
        
        # 关闭按钮（固定在底部，不跟随滚动）
        close_btn = QPushButton("关闭")
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(139, 92, 246, 0.3);
                color: white;
                border: 1px solid #5a4a9a;
                border-radius: 6px;
                font-size: 14px;
                outline: none;
            }
            QPushButton:hover {
                background-color: rgba(139, 92, 246, 0.5);
            }
        """)
        close_btn.clicked.connect(self.close)
        outer_layout.addWidget(close_btn)
    
    def _find_learners(self, skill_name):
        """查找能学会此技能的精灵"""
        learners = []
        
        # 尝试从增强数据文件加载
        enriched_file = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "lkwg_enriched_data.json")
        
        try:
            if os.path.exists(enriched_file):
                with open(enriched_file, 'r', encoding='utf-8') as f:
                    enriched_list = json.load(f)
                    
                    for pokemon in enriched_list:
                        # 检查普通技能
                        skills = pokemon.get('skills', {})
                        normal_skills = skills.get('normal_skills', [])
                        for skill in normal_skills:
                            if skill.get('name', '') == skill_name:
                                learners.append(pokemon.get('name', ''))
                                break
                        
                        # 检查血脉技能
                        bloodline_skills = skills.get('bloodline_skills', [])
                        for skill in bloodline_skills:
                            if skill.get('name', '') == skill_name:
                                if pokemon.get('name', '') not in learners:
                                    learners.append(pokemon.get('name', ''))
                                break
                        
                        # 检查技能石
                        stone_skills = skills.get('stone_skills', [])
                        for skill in stone_skills:
                            if skill.get('name', '') == skill_name:
                                if pokemon.get('name', '') not in learners:
                                    learners.append(pokemon.get('name', ''))
                                break
        
        except Exception as e:
            print(f"加载技能数据失败: {e}")
        
        return learners  # 保持 enriched 数据中的顺序（即图鉴编号顺序）

    def _update_learners_text(self):
        """更新精灵列表文本"""
        if self._learners_expanded:
            text = ", ".join(self.learners)
        else:
            text = ", ".join(self.learners[:20])
            if len(self.learners) > 20:
                text += f" ... 等{len(self.learners)}只"
        self._learners_content.setText(text)
    
    def _toggle_learners(self):
        """切换展开/收起精灵列表"""
        self._learners_expanded = not self._learners_expanded
        self._update_learners_text()
        if self._learners_expanded:
            self._expand_btn.setText(f"收起 ({len(self.learners)}只)")
        else:
            self._expand_btn.setText(f"展开全部 ({len(self.learners)}只)")


class RoundedFrame(QFrame):
    """自定义圆角Frame，禁用默认边框绘制"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setFocusPolicy(Qt.NoFocus)


class PokemonCard(QFrame):
    """精灵卡片 - Material Design风格"""

    # ── 类级共享缓存：所有卡片实例共用，避免每张卡片都重新读磁盘 ──
    _shared_icons = None        # 共享小图标 (xg.png / jb.png / sl.png 缩放后)
    _pokemon_pixmaps = {}       # 精灵图按 pid 缓存 {pid: QPixmap}

    @classmethod
    def _load_shared_icons(cls):
        """首次访问时加载共享图标（线程安全由 GDB 保证，UI 单线程足够）"""
        if cls._shared_icons is not None:
            return cls._shared_icons
        xg_path = r"d:\game\lkwg\image\sc\sc\xg.png"
        jb_path = r"d:\game\lkwg\image\sc\sc\jb.png"
        sl_path = r"d:\game\lkwg\image\sc\sc\sl.png"

        xg_pm = QPixmap(xg_path).scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation) if os.path.exists(xg_path) else None
        if xg_pm is not None and xg_pm.isNull():
            xg_pm = None
        jb_pm = QPixmap(jb_path).scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation) if os.path.exists(jb_path) else None
        if jb_pm is not None and jb_pm.isNull():
            jb_pm = None
        # sl.png 在卡片中用到两种尺寸：28x28(右上角) 和 22x22(信息行)，都缓存
        sl_28 = None
        sl_22 = None
        if os.path.exists(sl_path):
            sl_orig = QPixmap(sl_path)
            if not sl_orig.isNull():
                sl_28 = sl_orig.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                sl_22 = sl_orig.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        cls._shared_icons = {
            'xg': xg_pm,
            'jb': jb_pm,
            'sl_28': sl_28,
            'sl_22': sl_22,
        }
        return cls._shared_icons

    @classmethod
    def _get_pokemon_pixmap(cls, pid):
        """按 pid 取精灵图（缓存命中直接返回，未命中才读磁盘）"""
        if pid in cls._pokemon_pixmaps:
            return cls._pokemon_pixmaps[pid]
        image_path = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "images", f"{pid:03d}.png")
        pm = None
        if os.path.exists(image_path):
            raw = QPixmap(image_path)
            if not raw.isNull():
                pm = raw.scaled(110, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        cls._pokemon_pixmaps[pid] = pm  # 即使为 None 也缓存，避免反复探测
        return pm

    def __init__(self, pokemon, show_extra=False, parent=None):
        super().__init__(parent)
        self.pokemon = pokemon
        self.show_extra = show_extra
        self.setFixedSize(180, 240)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.setFocusPolicy(Qt.NoFocus)
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
        is_leader = self.pokemon.get('is_leader_form', False)

        # 预加载共享图标缓存（首次调用才真正读磁盘，后续直接返回缓存）
        shared_icons = self._load_shared_icons()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 图片区域（上半部分）
        image_frame = RoundedFrame()
        image_frame.setFixedHeight(160)
        
        if is_leader:
            # 首领化：金色边框 + 流光效果
            image_frame.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(251, 191, 36, 0.12),
                        stop:0.5 rgba(251, 191, 36, 0.05),
                        stop:1 rgba(251, 191, 36, 0.12));
                    border: 2px solid #7e6012;
                    border-top-left-radius: 12px;
                    border-top-right-radius: 12px;
                    outline: none;
                }
            """)
        else:
            image_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 0px;
                    border-top-left-radius: 12px;
                    border-top-right-radius: 12px;
                    outline: none;
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
        # 使用类级缓存：命中则直接复用，未命中才读磁盘
        cached_pm = self._get_pokemon_pixmap(pid)
        if cached_pm is not None:
            image_label.setPixmap(cached_pm)

        image_layout.addWidget(image_label)

        # 首领化标签 sl.png 素材（在图片右上方）
        if is_leader:
            sl_label = QLabel()
            if shared_icons['sl_28'] is not None:
                sl_label.setPixmap(shared_icons['sl_28'])
            sl_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(251, 191, 36, 0.2);
                    border-radius: 14px;
                    padding: 2px;
                    outline: none;
                }
            """)
            sl_label.setAlignment(Qt.AlignCenter)
            sl_label.setFixedSize(32, 32)
            # 放在右上角
            crown_layout = QHBoxLayout()
            crown_layout.setContentsMargins(0, 0, 8, 0)
            crown_layout.addStretch()
            crown_layout.addWidget(sl_label)
            image_layout.addLayout(crown_layout)
        
        main_layout.addWidget(image_frame)
        
        # 信息区域（下半部分）
        info_frame = RoundedFrame()
        if is_leader:
            info_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(251, 191, 36, 0.08);
                    border: 0px;
                    border-bottom-left-radius: 12px;
                    border-bottom-right-radius: 12px;
                    outline: none;
                }
            """)
        else:
            info_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(40, 40, 60, 0.95);
                    border: 0px;
                    border-bottom-left-radius: 12px;
                    border-bottom-right-radius: 12px;
                    outline: none;
                }
            """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 10, 12, 12)
        info_layout.setSpacing(6)
        
        # 编号和名称
        header_layout = QHBoxLayout()
        
        if not is_leader:
            # 普通精灵显示编号
            id_label = QLabel(f"#{pid:03d}")
            id_label.setStyleSheet("color: #6b7280; font-size: 11px;")
            id_label.setFixedWidth(40)
            header_layout.addWidget(id_label)
        
        name = self.pokemon.get('name', '未知')
        name_label = QLabel(name)
        if is_leader:
            name_label.setStyleSheet("color: #fbbf24; font-size: 13px; font-weight: bold;")
            name_label.setFixedWidth(120)
        else:
            name_label.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
            name_label.setFixedWidth(80)
        name_label.setWordWrap(True)
        header_layout.addWidget(name_label)
        
        # 蛋组标签（仅在显示额外信息时显示）
        if self.show_extra:
            egg_groups = self.pokemon.get('egg_groups', [])
            if egg_groups:
                egg_text = '/'.join(egg_groups) if isinstance(egg_groups, list) else str(egg_groups)
                # 去掉末尾的"组"字节省空间
                egg_text = egg_text.replace('组', '')
                egg_tag = QLabel(egg_text)
                egg_tag.setStyleSheet("""
                    background-color: rgba(34, 197, 94, 0.2);
                    color: #22c55e;
                    padding: 1px 4px;
                    border-radius: 3px;
                    font-size: 8px;
                """)
                egg_tag.setAlignment(Qt.AlignCenter)
                header_layout.addWidget(egg_tag)
        
        # 首领标签（使用 sl.png 素材）
        if is_leader:
            sl_22 = shared_icons['sl_22']
            if sl_22 is not None:
                sl_label = QLabel()
                sl_label.setPixmap(sl_22)
                sl_label.setAlignment(Qt.AlignCenter)
                header_layout.addWidget(sl_label)
            else:
                # fallback
                leader_tag = QLabel("首领")
                leader_tag.setStyleSheet("""
                    background-color: rgba(251, 191, 36, 0.3);
                    color: #fbbf24;
                    padding: 1px 6px;
                    border-radius: 4px;
                    font-size: 9px;
                    font-weight: bold;
                """)
                leader_tag.setAlignment(Qt.AlignCenter)
                header_layout.addWidget(leader_tag)

        header_layout.addStretch()
        info_layout.addLayout(header_layout)

        # 属性标签 + 额外信息（星光值/洛克贝）混合行
        attr = self.pokemon.get('attribute', '')
        extra_shown = False

        # 使用共享图标缓存（xg.png / jb.png 全局只加载一次）
        xg_pm = shared_icons['xg']
        jb_pm = shared_icons['jb']
        
        if attr or self.show_extra:
            attr_row = QHBoxLayout()
            attr_row.setSpacing(6)
            
            # 属性标签
            if '/' in attr:
                for part in attr.split('/'):
                    tag = QLabel(part)
                    tag.setStyleSheet("""
                        background-color: rgba(139, 92, 246, 0.2);
                        color: #a78bfa;
                        padding: 2px 8px;
                        border-radius: 4px;
                        font-size: 10px;
                    """)
                    tag.setAlignment(Qt.AlignCenter)
                    attr_row.addWidget(tag)
            elif attr:
                tag = QLabel(attr)
                tag.setStyleSheet("""
                    background-color: rgba(139, 92, 246, 0.2);
                    color: #a78bfa;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 10px;
                """)
                tag.setAlignment(Qt.AlignCenter)
                attr_row.addWidget(tag)
            
            # 额外信息（星光值 + 洛克贝）- 放在属性右边
            if self.show_extra:
                starlight = self.pokemon.get('starlight', '')
                review_cost = self.pokemon.get('review_cost', '')
                
                if starlight or review_cost:
                    # 间距
                    attr_row.addSpacing(6)
                
                if starlight and xg_pm and not xg_pm.isNull():
                    star_icon = QLabel()
                    star_icon.setPixmap(xg_pm)
                    star_icon.setFixedSize(14, 14)
                    star_icon.setStyleSheet("background: transparent; border: none;")
                    attr_row.addWidget(star_icon)
                    
                    star_val = QLabel(str(starlight))
                    star_val.setStyleSheet("color: #fbbf24; font-size: 10px; font-weight: 600; background: transparent;")
                    attr_row.addWidget(star_val)
                    extra_shown = True
                elif starlight:
                    star_label = QLabel(f"✦ {starlight}")
                    star_label.setStyleSheet("color: #fbbf24; font-size: 10px; font-weight: 600; background: transparent;")
                    attr_row.addWidget(star_label)
                    extra_shown = True
                
                if review_cost and jb_pm and not jb_pm.isNull():
                    if starlight:
                        attr_row.addSpacing(4)
                    coin_icon = QLabel()
                    coin_icon.setPixmap(jb_pm)
                    coin_icon.setFixedSize(14, 14)
                    coin_icon.setStyleSheet("background: transparent; border: none;")
                    attr_row.addWidget(coin_icon)
                    
                    coin_val = QLabel(str(review_cost))
                    coin_val.setStyleSheet("color: #34d399; font-size: 10px; font-weight: 600; background: transparent;")
                    attr_row.addWidget(coin_val)
                    extra_shown = True
                elif review_cost:
                    if starlight:
                        attr_row.addSpacing(4)
                    coin_label = QLabel(f"💰 {review_cost}")
                    coin_label.setStyleSheet("color: #34d399; font-size: 10px; font-weight: 600; background: transparent;")
                    attr_row.addWidget(coin_label)
                    extra_shown = True
            
            attr_row.addStretch()
            info_layout.addLayout(attr_row)
        
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
                border: 1px solid #5a4a9a;
                border-radius: 8px;
                font-size: 13px;
                outline: none;
            }
            QPushButton:hover {
                background-color: rgba(139, 92, 246, 0.3);
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
        
        # 左侧：头像（glq素材做背景，圆形边框）
        image_frame = RoundedFrame()
        image_frame.setFixedSize(240, 240)
        image_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 2px solid #4a3a8a;
                border-radius: 120px;
                outline: none;
            }
        """)
        
        # 使用QGridLayout叠加：底层glq素材，上层精灵图片
        image_layout = QGridLayout(image_frame)
        image_layout.setContentsMargins(2, 2, 2, 2)
        
        # 合成一张图：glq背景 + 精灵图片居中，彻底消灭重叠控件矩形框
        glq_path = r"d:\game\lkwg\image\sc\sc\glq.png"
        composited = QPixmap(232, 232)
        composited.fill(Qt.transparent)
        
        painter = QPainter(composited)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # 先画glq背景铺满232x232
        if os.path.exists(glq_path):
            glq_pm = QPixmap(glq_path)
            if not glq_pm.isNull():
                glq_scaled = glq_pm.scaled(232, 232, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                painter.drawPixmap(0, 0, glq_scaled)
        
        # 再画精灵图片居中
        pid = self.pokemon.get('id', 0)
        image_path = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "images", f"{pid:03d}.png")
        if os.path.exists(image_path):
            pm = QPixmap(image_path)
            if not pm.isNull():
                pokemon_scaled = pm.scaled(140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                x = (232 - pokemon_scaled.width()) // 2
                y = (232 - pokemon_scaled.height()) // 2
                painter.drawPixmap(x, y, pokemon_scaled)
        
        painter.end()
        
        combined_label = QLabel()
        combined_label.setPixmap(composited)
        combined_label.setAlignment(Qt.AlignCenter)
        combined_label.setStyleSheet("background: transparent; border: none; outline: none; padding: 0px; margin: 0px;")
        
        image_layout.addWidget(combined_label, 0, 0, alignment=Qt.AlignCenter)
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
        
        # ─── 描述区域（紧凑型） ───
        description = self.pokemon.get('description', '')
        if description:
            desc_label = QLabel(f"「{description}」")
            desc_label.setStyleSheet("""
                color: rgba(255, 255, 255, 0.65);
                font-size: 13px;
                font-style: italic;
                padding: 6px 12px;
                background-color: rgba(139, 92, 246, 0.04);
                border: 1px solid #3d2d6e;
                border-radius: 6px;
                outline: none;
            """)
            desc_label.setWordWrap(True)
            content_layout.addWidget(desc_label)
        
        # ─── 额外信息卡片（星光值、回顾、性别比例、蛋组） ───
        starlight = self.pokemon.get('starlight', '')
        review_cost = self.pokemon.get('review_cost', '')
        gender_ratio = self.pokemon.get('gender_ratio', '')
        egg_groups = self.pokemon.get('egg_groups', [])
        
        if starlight or review_cost or gender_ratio or egg_groups:
            extra_title = QLabel("基本信息")
            extra_title.setStyleSheet("color: #a78bfa; font-size: 18px; font-weight: bold;")
            content_layout.addWidget(extra_title)
            
            extra_grid = QWidget()
            extra_grid.setStyleSheet("background: transparent; border: none; outline: none;")
            grid_layout = QHBoxLayout(extra_grid)
            grid_layout.setSpacing(12)
            grid_layout.setContentsMargins(0, 0, 0, 0)
            
            # 星光值（使用素材图标）
            if starlight:
                star_card = self._create_icon_card("星光值", str(starlight), 
                    r"d:\game\lkwg\image\sc\sc\xg.png", "#fbbf24")
                grid_layout.addWidget(star_card)
            
            # 回顾金币（使用素材图标）
            if review_cost:
                review_card = self._create_icon_card("洛克贝", str(review_cost),
                    r"d:\game\lkwg\image\sc\sc\jb.png", "#f59e0b")
                grid_layout.addWidget(review_card)
            
            # 性别比例（雄性蓝色/雌性粉色）
            if gender_ratio:
                gender_card = self._create_gender_card(gender_ratio)
                grid_layout.addWidget(gender_card)
            
            # 蛋组
            if egg_groups:
                egg_text = " / ".join(egg_groups)
                egg_card = self._create_info_card("蛋组", egg_text, "#34d399")
                grid_layout.addWidget(egg_card)
            
            grid_layout.addStretch()
            content_layout.addWidget(extra_grid)
        
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
                    border: 2px solid #523b93;
                    border-radius: 75px;
                    outline: none;
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
        
        # ─── 进化链区域 ───
        evolution_chain = self.pokemon.get('evolution_chain', [])
        current_name = self.pokemon.get('name', '')
        
        # 兼容旧格式：evolution 是纯字符串列表
        old_evolution = self.pokemon.get('evolution', [])
        
        if evolution_chain:
            # 新格式：列表 of dict
            evo_title = QLabel("进化链")
            evo_title.setStyleSheet("color: #a78bfa; font-size: 18px; font-weight: bold;")
            content_layout.addWidget(evo_title)
            
            evo_container = QWidget()
            evo_layout = QHBoxLayout(evo_container)
            evo_layout.setSpacing(15)
            
            for i, entry in enumerate(evolution_chain):
                evo_name = entry.get('name', '')
                evo_level = entry.get('evo_level')
                is_leader = entry.get('is_leader', False)
                
                # 创建精灵卡片容器
                card_container = QWidget()
                card_layout = QVBoxLayout(card_container)
                card_layout.setContentsMargins(0, 0, 0, 0)
                card_layout.setSpacing(4)
                card_layout.setAlignment(Qt.AlignCenter)
                
                # 进化等级标签（如果有）
                if evo_level is not None:
                    lv_badge = QLabel(f"Lv.{evo_level}")
                    lv_badge.setStyleSheet("""
                        QLabel {
                            background-color: rgba(251, 191, 36, 0.2);
                            color: #fbbf24;
                            padding: 2px 10px;
                            border-radius: 4px;
                            font-size: 11px;
                            font-weight: bold;
                        }
                    """)
                    lv_badge.setAlignment(Qt.AlignCenter)
                    card_layout.addWidget(lv_badge)
                
                # 高亮显示当前精灵
                if evo_name == current_name:
                    if is_leader:
                        name_label = QLabel(f"★ {evo_name}")
                        name_label.setStyleSheet("""
                            QLabel {
                                background-color: rgba(251, 191, 36, 0.3);
                                color: #fbbf24;
                                padding: 8px 16px;
                                border-radius: 8px;
                                font-size: 14px;
                                font-weight: bold;
                                border: 2px solid #b8860b;
                                outline: none;
                            }
                        """)
                    else:
                        name_label = QLabel(f"● {evo_name}")
                        name_label.setStyleSheet("""
                            QLabel {
                                background-color: rgba(251, 191, 36, 0.3);
                                color: #fbbf24;
                                padding: 8px 16px;
                                border-radius: 8px;
                                font-size: 14px;
                                font-weight: bold;
                                border: 2px solid #b8860b;
                                outline: none;
                            }
                        """)
                else:
                    name_label = QLabel(evo_name)
                    name_label.setStyleSheet("""
                        QLabel {
                            background-color: rgba(139, 92, 246, 0.2);
                            color: #c4b5fd;
                            padding: 8px 16px;
                            border-radius: 8px;
                            font-size: 13px;
                        }
                    """)
                
                name_label.setAlignment(Qt.AlignCenter)
                card_layout.addWidget(name_label)
                
                # 首领化标签
                if is_leader:
                    leader_tag = QLabel("👑 首领化")
                    leader_tag.setStyleSheet("""
                        QLabel {
                            background-color: rgba(244, 114, 182, 0.25);
                            color: #f472b6;
                            padding: 2px 10px;
                            border-radius: 4px;
                            font-size: 10px;
                            font-weight: bold;
                        }
                    """)
                    leader_tag.setAlignment(Qt.AlignCenter)
                    card_layout.addWidget(leader_tag)
                
                evo_layout.addWidget(card_container)
                
                # 添加箭头（最后一个不加）
                if i < len(evolution_chain) - 1:
                    arrow_label = QLabel("→")
                    arrow_label.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 16px;")
                    evo_layout.addWidget(arrow_label)
            
            evo_layout.addStretch()
            content_layout.addWidget(evo_container)
        
        elif old_evolution and old_evolution != ['无法进化']:
            # 旧格式兼容：纯字符串列表
            evo_title = QLabel("进化链")
            evo_title.setStyleSheet("color: #a78bfa; font-size: 18px; font-weight: bold;")
            content_layout.addWidget(evo_title)
            
            # 构建完整进化链
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
                except:
                    full_evolution = old_evolution + [current_name]
            else:
                full_evolution = old_evolution.copy()
            
            evo_container = QWidget()
            evo_layout = QHBoxLayout(evo_container)
            evo_layout.setSpacing(15)
            
            for i, evo_name in enumerate(full_evolution):
                if '（' in evo_name:
                    base_name = evo_name.split('（')[0].strip()
                elif '(' in evo_name:
                    base_name = evo_name.split('(')[0].strip()
                else:
                    base_name = evo_name
                
                card_container = QWidget()
                card_layout = QVBoxLayout(card_container)
                card_layout.setContentsMargins(0, 0, 0, 0)
                card_layout.setSpacing(2)
                card_layout.setAlignment(Qt.AlignCenter)
                
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
                            border: 2px solid #b8860b;
                            outline: none;
                        }
                    """)
                else:
                    name_label = QLabel(base_name)
                    name_label.setStyleSheet("""
                        QLabel {
                            background-color: rgba(139, 92, 246, 0.2);
                            color: #c4b5fd;
                            padding: 8px 16px;
                            border-radius: 8px;
                            font-size: 13px;
                            outline: none;
                        }
                    """)
                
                name_label.setAlignment(Qt.AlignCenter)
                card_layout.addWidget(name_label)
                evo_layout.addWidget(card_container)
                
                if i < len(full_evolution) - 1:
                    arrow_label = QLabel("→")
                    arrow_label.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 16px;")
                    evo_layout.addWidget(arrow_label)
            
            evo_layout.addStretch()
            content_layout.addWidget(evo_container)
        
        elif old_evolution == ['无法进化']:
            evo_title = QLabel("进化链")
            evo_title.setStyleSheet("color: #a78bfa; font-size: 18px; font-weight: bold;")
            content_layout.addWidget(evo_title)
            no_evo_label = QLabel("无法进化")
            no_evo_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 13px;")
            content_layout.addWidget(no_evo_label)
        
        # ─── 特性区域（支持新旧格式） ───
        ability_name = self.pokemon.get('ability_name', '')
        ability_desc = self.pokemon.get('ability_desc', '')
        abilities = self.pokemon.get('abilities', [])
        
        if ability_name or ability_desc:
            ability_title = QLabel("特性")
            ability_title.setStyleSheet("color: #a78bfa; font-size: 18px; font-weight: bold;")
            content_layout.addWidget(ability_title)
            
            ability_box = RoundedFrame()
            ability_box.setStyleSheet("""
                QFrame {
                    background-color: rgba(139, 92, 246, 0.08);
                    border: 1px solid #3d2d6e;
                    border-radius: 10px;
                    padding: 16px;
                    outline: none;
                }
            """)
            ab_layout = QVBoxLayout(ability_box)
            ab_layout.setContentsMargins(16, 16, 16, 16)
            ab_layout.setSpacing(10)
            
            if ability_name:
                ab_name_label = QLabel(ability_name)
                ab_name_label.setStyleSheet("""
                    color: #fbbf24;
                    font-size: 16px;
                    font-weight: bold;
                """)
                ab_layout.addWidget(ab_name_label)
            
            if ability_desc:
                ab_desc_label = QLabel(ability_desc)
                ab_desc_label.setStyleSheet("""
                    color: rgba(255, 255, 255, 0.85);
                    font-size: 13px;
                    line-height: 1.5;
                """)
                ab_desc_label.setWordWrap(True)
                ab_layout.addWidget(ab_desc_label)
            
            content_layout.addWidget(ability_box)
        
        elif abilities:
            # 旧格式兼容：abilities 列表
            ability_title = QLabel("特性")
            ability_title.setStyleSheet("color: #a78bfa; font-size: 18px; font-weight: bold;")
            content_layout.addWidget(ability_title)
            
            for ability in abilities:
                ability_box = RoundedFrame()
                ability_box.setStyleSheet("""
                    QFrame {
                        background-color: rgba(139, 92, 246, 0.08);
                        border: 1px solid #3d2d6e;
                        border-radius: 10px;
                        padding: 16px;
                        outline: none;
                    }
                """)
                ab_layout = QVBoxLayout(ability_box)
                ab_layout.setContentsMargins(16, 16, 16, 16)
                ab_layout.setSpacing(10)
                
                if isinstance(ability, dict):
                    ab_name = ability.get('name', '')
                    ab_effect = ability.get('effect', '')
                else:
                    ab_name = ''
                    ab_effect = str(ability)
                
                if ab_name:
                    name_label = QLabel(ab_name)
                    name_label.setStyleSheet("color: #fbbf24; font-size: 14px; font-weight: bold;")
                    ab_layout.addWidget(name_label)
                if ab_effect:
                    desc_label = QLabel(ab_effect)
                    desc_label.setStyleSheet("color: rgba(255, 255, 255, 0.85); font-size: 13px;")
                    desc_label.setWordWrap(True)
                    ab_layout.addWidget(desc_label)
                
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
                border: 1px solid #4a3a8a;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
                outline: none;
            }
            QPushButton:hover {
                background-color: rgba(139, 92, 246, 0.25);
            }
            QPushButton:checked {
                background-color: rgba(139, 92, 246, 0.4);
                border: 2px solid #6a4aba;
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
    
    def _create_info_card(self, title, value, color):
        """创建纯文本信息卡片"""
        card = RoundedFrame()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(4)
        card_layout.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px; background: transparent; outline: none;")
        title_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold; background: transparent; outline: none;")
        value_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(value_label)
        
        return card
    
    def _create_icon_card(self, title, value, icon_path, color):
        """创建带图标的数值信息卡片（星光值、金币用素材图）"""
        card = RoundedFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                border-radius: 0px;
                padding: 0px;
                outline: none;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 6, 8, 6)
        card_layout.setSpacing(2)
        card_layout.setAlignment(Qt.AlignCenter)
        
        # 标题文字（在上方，小字）
        title_label = QLabel(title)
        title_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 9px; background: transparent; outline: none;")
        title_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title_label)
        
        # 图标（在中间）
        if os.path.exists(icon_path):
            icon_label = QLabel()
            icon_pixmap = QPixmap(icon_path)
            if not icon_pixmap.isNull():
                icon_label.setPixmap(icon_pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet("background: transparent; outline: none;")
            card_layout.addWidget(icon_label)
        
        # 数值（在底部）
        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold; background: transparent; outline: none;")
        value_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(value_label)
        
        return card
    
    def _create_gender_card(self, gender_text):
        """创建性别卡片 - 雌雄分开显示，带性别文字"""
        card = RoundedFrame()
        card.setStyleSheet("""
            QFrame {
                background: transparent;
                border: none;
                outline: none;
            }
        """)
        card_layout = QVBoxLayout(card)
        # 与其他卡片的 _create_icon_card 一致 (8,6,8,6)
        card_layout.setContentsMargins(8, 6, 8, 6)
        card_layout.setSpacing(4)
        card_layout.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel("性别比例")
        title_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px; background: transparent; outline: none;")
        title_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title_label)
        
        # 解析性别文本
        gender_text_str = str(gender_text) if gender_text is not None else ""
        
        # 提取雌雄比例
        male_pct = ""
        female_pct = ""
        if " / " in gender_text_str:
            parts = gender_text_str.split(" / ")
            for part in parts:
                p = part.strip()
                if p.startswith("雄"):
                    male_pct = p.replace("雄性 ", "")
                elif p.startswith("雌"):
                    female_pct = p.replace("雌性 ", "")
        else:
            if gender_text_str.startswith("雄"):
                male_pct = gender_text_str.replace("雄性 ", "")
            elif gender_text_str.startswith("雌"):
                female_pct = gender_text_str.replace("雌性 ", "")
        
        # 水平布局：雌雄两栏
        gender_row = QHBoxLayout()
        gender_row.setSpacing(6)
        gender_row.setContentsMargins(0, 0, 0, 0)
        
        has_male = bool(male_pct)
        has_female = bool(female_pct)
        
        if has_male:
            male_widget = self._create_gender_side("♂", "雄性", male_pct, "#3b82f6")
            gender_row.addWidget(male_widget)
        
        if has_female:
            female_widget = self._create_gender_side("♀", "雌性", female_pct, "#ec4899")
            gender_row.addWidget(female_widget)
        
        # 如果只有一种性别，加空白占位保持居中
        if has_male and not has_female:
            placeholder = QLabel("")
            placeholder.setFixedWidth(50)
            placeholder.setStyleSheet("background: transparent;")
            gender_row.addWidget(placeholder)
        elif has_female and not has_male:
            placeholder = QLabel("")
            placeholder.setFixedWidth(50)
            placeholder.setStyleSheet("background: transparent;")
            gender_row.insertWidget(0, placeholder)
        
        card_layout.addLayout(gender_row)
        
        return card
    
    def _create_gender_side(self, symbol, label_text, percent, color):
        """创建性别单侧显示（符号+性别名称+百分比）"""
        widget = QWidget()
        widget.setStyleSheet("background: transparent; outline: none;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)
        
        # 符号 + 性别名合成一个QLabel，确保对齐
        top_label = QLabel(f"{symbol} {label_text}")
        top_label.setStyleSheet(f"""
            color: {color};
            font-size: 13px;
            font-weight: bold;
            background: transparent;
            outline: none;
        """)
        top_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(top_label)
        
        # 百分比
        pct_label = QLabel(percent)
        pct_label.setStyleSheet(f"""
            color: {color};
            font-size: 13px;
            font-weight: bold;
            background: transparent;
            outline: none;
        """)
        pct_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(pct_label)
        
        return widget
    
    def create_skill_box(self, skill, is_bloodline=False, is_stone=False):
        """创建技能信息框（可点击查看详情）"""
        skill_box = RoundedFrame()
        skill_box.setCursor(Qt.PointingHandCursor)
        
        # 根据技能类型设置不同的边框颜色（不透明色防止渲染小点）
        if is_bloodline:
            border_color = "#b84a7d"
            bg_color = "#2a1a2e"
            hover_color = "#3a2a3e"
            border_hover = "#d46a9d"
        elif is_stone:
            border_color = "#2a8a6a"
            bg_color = "#1a2a22"
            hover_color = "#2a3a32"
            border_hover = "#4aaa8a"
        else:
            border_color = "#6a4aba"
            bg_color = "#1e1830"
            hover_color = "#2e2840"
            border_hover = "#8a6ada"
        
        skill_box.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 10px;
                padding: 12px;
                outline: none;
            }}
            QFrame:hover {{
                background-color: {hover_color};
                border: 2px solid {border_hover};
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
        
        # 点击事件：打开技能详情
        def on_skill_clicked(event):
            # 向上查找 PokedexWidget
            parent = skill_box.parent()
            while parent:
                if hasattr(parent, 'show_skill_detail'):
                    parent.show_skill_detail(skill)
                    return
                parent = parent.parent()
        
        skill_box.mousePressEvent = on_skill_clicked
        
        return skill_box


class PokedexWidget(QWidget):
    """精灵图鉴主界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pokemon_data = []
        self.filtered_data = []
        self.show_extra_info = False     # 是否显示星光值/洛克贝
        self.sort_ascending = True       # 升序/降序
        self.current_view = 'list'
        # 搜索防抖定时器：用户连续输入时只在停顿 250ms 后才真正过滤
        self._search_debounce_timer = QTimer(self)
        self._search_debounce_timer.setSingleShot(True)
        self._search_debounce_timer.setInterval(250)
        self._search_debounce_timer.timeout.connect(self.apply_filters)
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
                outline: none;
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
                outline: none;
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
        
        # ─── 工具栏：开关 + 筛选 + 排序 ───
        toolbar = QWidget()
        toolbar.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(167, 139, 250, 0.15);
            border-radius: 10px;
            padding: 4px;
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 6, 12, 6)
        toolbar_layout.setSpacing(10)
        
        # 显示额外信息开关
        self.extra_toggle = QPushButton()
        self.extra_toggle.setCheckable(True)
        self.extra_toggle.setChecked(False)
        self.extra_toggle.setFixedHeight(30)
        self.extra_toggle.setCursor(Qt.PointingHandCursor)
        self.extra_toggle.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.extra_toggle.toggled.connect(self._on_extra_toggled)
        self._update_toggle_style()
        toolbar_layout.addWidget(self.extra_toggle)
        
        # 分隔
        sep1 = QLabel("|")
        sep1.setStyleSheet("color: rgba(255,255,255,0.15); font-size: 14px; background: transparent; padding: 0 2px;")
        toolbar_layout.addWidget(sep1)
        
        # 蛋组筛选
        eg_label = QLabel("蛋组")
        eg_label.setStyleSheet("color: #9ca3af; font-size: 12px; background: transparent;")
        toolbar_layout.addWidget(eg_label)
        
        self.egg_group_combo = QComboBox()
        self.egg_group_combo.addItem("全部")
        self.egg_group_combo.setFixedHeight(30)
        self.egg_group_combo.setMinimumWidth(90)
        self.egg_group_combo.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.egg_group_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(167, 139, 250, 0.25);
                border-radius: 15px;
                padding: 4px 12px;
                color: #e5e7eb;
                font-size: 12px;
                outline: none;
            }
            QComboBox:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid #a78bfa;
            }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { width: 0; }
            QComboBox QAbstractItemView {
                background-color: #1e1e2e;
                color: #e5e7eb;
                border: 1px solid #a78bfa;
                border-radius: 6px;
                selection-background-color: rgba(167, 139, 250, 0.3);
                outline: none;
            }
        """)
        self.egg_group_combo.currentTextChanged.connect(self._on_filter_or_sort_changed)
        toolbar_layout.addWidget(self.egg_group_combo)
        
        # 分隔
        sep2 = QLabel("|")
        sep2.setStyleSheet("color: rgba(255,255,255,0.15); font-size: 14px; background: transparent; padding: 0 2px;")
        toolbar_layout.addWidget(sep2)
        
        # 排序依据
        sort_label = QLabel("排序")
        sort_label.setStyleSheet("color: #9ca3af; font-size: 12px; background: transparent;")
        toolbar_layout.addWidget(sort_label)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["编号", "名称", "星光值", "洛克贝", "种族值"])
        self.sort_combo.setCurrentIndex(0)
        self.sort_combo.setFixedHeight(30)
        self.sort_combo.setMinimumWidth(80)
        self.sort_combo.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.sort_combo.setStyleSheet(self.egg_group_combo.styleSheet())
        self.sort_combo.currentTextChanged.connect(self._on_filter_or_sort_changed)
        toolbar_layout.addWidget(self.sort_combo)
        
        # 升降序切换
        self.order_btn = QPushButton("↑ 升序")
        self.order_btn.setCheckable(True)
        self.order_btn.setChecked(True)
        self.order_btn.setFixedHeight(30)
        self.order_btn.setFixedWidth(80)
        self.order_btn.setCursor(Qt.PointingHandCursor)
        self.order_btn.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.order_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(167, 139, 250, 0.15);
                color: #c4b5fd;
                border: 1px solid rgba(167, 139, 250, 0.3);
                border-radius: 15px;
                font-size: 12px;
                font-weight: 600;
                outline: none;
            }
            QPushButton:hover {
                background-color: rgba(167, 139, 250, 0.25);
                border: 1px solid #a78bfa;
            }
            QPushButton:checked {
                background-color: rgba(167, 139, 250, 0.25);
                border: 1px solid #a78bfa;
            }
        """)
        self.order_btn.clicked.connect(self._on_order_toggle)
        toolbar_layout.addWidget(self.order_btn)
        
        # 分隔
        sep3 = QLabel("|")
        sep3.setStyleSheet("color: rgba(255,255,255,0.15); font-size: 14px; background: transparent; padding: 0 2px;")
        toolbar_layout.addWidget(sep3)
        
        # 进化阶段筛选
        stage_label = QLabel("阶段")
        stage_label.setStyleSheet("color: #9ca3af; font-size: 12px; background: transparent;")
        toolbar_layout.addWidget(stage_label)
        
        self.stage_combo = QComboBox()
        self.stage_combo.addItems(["全部", "1阶", "2阶", "3阶", "最终形态", "无法进化"])
        self.stage_combo.setFixedHeight(30)
        self.stage_combo.setMinimumWidth(70)
        self.stage_combo.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.stage_combo.setStyleSheet(self.egg_group_combo.styleSheet())
        self.stage_combo.currentTextChanged.connect(self._on_filter_or_sort_changed)
        toolbar_layout.addWidget(self.stage_combo)
        
        toolbar_layout.addStretch()
        list_layout.addWidget(toolbar)
        
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
        """获取增强数据（包含进化链、特性、技能）
        首领化精灵会自动继承来源最终形态的技能池
        """
        pid = basic_pokemon.get('id', 0)
        name = basic_pokemon.get('name', '')
        is_leader = basic_pokemon.get('is_leader_form', False)
        source_form = basic_pokemon.get('source_final_form', '')
        
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
                            # 只覆盖非None值，防止增强数据空值抹掉基本数据
                            for k, v in p.items():
                                if v is not None:
                                    merged[k] = v
                            
                            # 修复：增强数据的空description不覆盖基本数据
                            if not merged.get('description') and basic_pokemon.get('description'):
                                merged['description'] = basic_pokemon['description']
                            
                            # 如果是首领化精灵，从来源形态继承技能池
                            if is_leader and source_form:
                                leader_skills = self._inherit_skills_from_source(
                                    enriched_list, source_form, merged.get('skills', {}))
                                if leader_skills:
                                    merged['skills'] = leader_skills
                            
                            return merged
                    
                    # 如果没找到匹配ID/名字（首领化可能ID不匹配）
                    if is_leader and source_form:
                        # 直接用基础数据，但尝试从来源继承技能
                        merged = dict(basic_pokemon)
                        leader_skills = self._inherit_skills_from_source(
                            enriched_list, source_form, {})
                        if leader_skills:
                            merged['skills'] = leader_skills
                        return merged
        except Exception as e:
            print(f"加载增强数据失败: {e}")
        
        # 如果找不到增强数据，返回基础数据
        return basic_pokemon
    
    def _inherit_skills_from_source(self, enriched_list, source_name, current_skills):
        """从来源最终形态继承技能池"""
        for p in enriched_list:
            if p.get('name') == source_name:
                source_skills = p.get('skills', {})
                if source_skills:
                    # 复制技能，标记来源
                    inherited = {
                        "normal_skills": source_skills.get('normal_skills', []),
                        "bloodline_skills": source_skills.get('bloodline_skills', []),
                        "stone_skills": source_skills.get('stone_skills', []),
                    }
                    return inherited
        return current_skills
    
    def show_skill_detail(self, skill):
        """显示技能详情"""
        # 创建技能详情对话框
        dialog = SkillDetailDialog(skill, self.pokemon_data, self)
        dialog.exec()
        
    def load_data(self):
        """加载数据"""
        data_file = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "pokemon_data.json")
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                self.pokemon_data = json.load(f)
            
            # 加载增强数据，合并evolution字段到基本数据
            enriched_file = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "lkwg_enriched_data.json")
            try:
                if os.path.exists(enriched_file):
                    with open(enriched_file, 'r', encoding='utf-8') as f:
                        enriched_list = json.load(f)
                    # 按名称建立evolution查找表
                    evo_lookup = {}
                    for ep in enriched_list:
                        ename = ep.get('name', '')
                        evo = ep.get('evolution')
                        if ename and evo is not None:
                            evo_lookup[ename] = evo
                    # 合并到基本数据
                    for pokemon in self.pokemon_data:
                        pname = pokemon.get('name', '')
                        if pname in evo_lookup:
                            enriched_evo = evo_lookup[pname]
                            # 只有基本数据没有evolution字段时才合并
                            if not pokemon.get('evolution'):
                                pokemon['evolution'] = enriched_evo
            except Exception:
                pass  # 增强数据非必需，静默失败
            
            types = set()
            egg_groups = set()
            for pokemon in self.pokemon_data:
                attr = pokemon.get('attribute', '')
                if attr:
                    if '/' in attr:
                        types.update(attr.split('/'))
                    else:
                        types.add(attr)
                # 收集蛋组
                eg = pokemon.get('egg_groups', [])
                for e in eg:
                    egg_groups.add(e)
            
            for t in sorted(types):
                self.type_filter.addItem(t)
            
            # 填充蛋组下拉
            for eg in sorted(egg_groups):
                self.egg_group_combo.addItem(eg)
            
            self.filtered_data = self.pokemon_data.copy()
            self.refresh_display()
            
        except Exception as e:
            self.stats_label.setText(f"加载失败: {str(e)}")
            
    def on_search_changed(self, text):
        # 防抖：连续输入时只触发一次过滤，避免每个字符都重建卡片
        self._search_debounce_timer.start()
        
    def on_filter_changed(self, text):
        self.apply_filters()
    
    # ── 工具按钮回调 ──
    
    def _update_toggle_style(self):
        """更新开关按钮样式"""
        if self.extra_toggle.isChecked():
            self.extra_toggle.setText("✦ 值 ON")
            self.extra_toggle.setStyleSheet("""
                QPushButton {
                    background-color: rgba(167, 139, 250, 0.25);
                    color: #c4b5fd;
                    border: 1px solid #a78bfa;
                    border-radius: 15px;
                    padding: 0 14px;
                    font-size: 12px;
                    font-weight: 600;
                    outline: none;
                }
                QPushButton:hover {
                    background-color: rgba(167, 139, 250, 0.35);
                }
            """)
        else:
            self.extra_toggle.setText("✦ 值 OFF")
            self.extra_toggle.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.06);
                    color: #9ca3af;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 15px;
                    padding: 0 14px;
                    font-size: 12px;
                    font-weight: 500;
                    outline: none;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.10);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
            """)
    
    def _on_extra_toggled(self, checked):
        """额外信息开关切换"""
        self.show_extra_info = checked
        self._update_toggle_style()
        # 卡片内容变了，清缓存强制重建
        self._card_pool = []
        self.refresh_display()
    
    def _on_filter_or_sort_changed(self, text):
        """筛选/排序变更"""
        self.apply_filters()
    
    def _on_order_toggle(self):
        """升降序切换"""
        self.sort_ascending = self.order_btn.isChecked()
        self.order_btn.setText("↑ 升序" if self.sort_ascending else "↓ 降序")
        self.apply_filters()
    
    @staticmethod
    def _is_leader_related(entry):
        """判断是否是首领相关形态（首领化不算进化）"""
        if entry.get('is_leader'):
            return True
        name = entry.get('name', '')
        return '国王' in name or '首领' in name
    
    @staticmethod
    def _get_stage(pokemon):
        """判断精灵进化阶段
        返回: '1阶', '2阶', '3阶', '无法进化', None(首领或无法判断)
        """
        if pokemon.get('is_leader_form'):
            return None
        
        name = pokemon.get('name', '')
        chain = pokemon.get('evolution_chain', [])
        evolution = pokemon.get('evolution', [])
        
        # 优先用evolution_chain判断
        if chain:
            # 过滤掉首领形态
            non_leader = [e for e in chain if not e.get('is_leader')]
            
            if not non_leader:
                # 全是首领形态
                if evolution == ['无法进化'] or not evolution:
                    return '无法进化'
                return None
            
            # 只有自己
            if len(non_leader) <= 1:
                if non_leader[0].get('name') != name:
                    return None
                if evolution and evolution != ['无法进化']:
                    if len(evolution) == 1 and evolution[0] == name:
                        return '无法进化'
                    return '1阶'
                return '无法进化'
            
            # 多阶进化链，找自己在链中的位置
            for i, e in enumerate(non_leader):
                if e.get('name') == name:
                    # 检查后续形态是否都是首领相关（首领化不算进化）
                    remaining = non_leader[i+1:]
                    if remaining and all(PokedexWidget._is_leader_related(r) for r in remaining):
                        return '无法进化'
                    stage = i + 1
                    if stage >= 3:
                        return '3阶'
                    return f'{stage}阶'
            return None
        
        # 没有evolution_chain，用evolution字段判断（从增强数据合并而来）
        if evolution and evolution != ['无法进化']:
            if len(evolution) == 1 and evolution[0] == name:
                return '无法进化'
            return '1阶'
        return '无法进化'
    
    @staticmethod
    def _is_final_form(pokemon):
        """判断是否为最终形态（进化链最后一个非首领形态）"""
        if pokemon.get('is_leader_form'):
            return False
        
        name = pokemon.get('name', '')
        chain = pokemon.get('evolution_chain', [])
        
        if chain:
            non_leader = [e for e in chain if not e.get('is_leader')]
            if not non_leader:
                return False
            return non_leader[-1].get('name') == name
        
        # 没有evolution_chain，用evolution字段
        evolution = pokemon.get('evolution', [])
        if not evolution or evolution == ['无法进化']:
            return True
        if len(evolution) == 1 and evolution[0] == name:
            return True
        return False
    
    def apply_filters(self):
        """应用搜索/筛选/排序"""
        search_text = self.search_input.text().lower()
        type_filter = self.type_filter.currentText()
        egg_group_filter = self.egg_group_combo.currentText()
        sort_text = self.sort_combo.currentText()
        
        # 筛选前记录旧对象身份集合，判断是否纯排序变化
        # 用 id() 而非 p.get('id')，避免不同精灵共用同一 id 时误判为"未变化"
        old_keys = {id(p) for p in self.filtered_data} if self.filtered_data else None
        
        # 排序键映射
        # "编号"默认保持原始顺序（不排序），避免首领精灵被排到最后
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
            
            # 搜索过滤
            if search_text and search_text not in name and search_text not in pid:
                continue
            
            # 属性过滤
            if type_filter != "全部":
                attr = pokemon.get('attribute', '')
                if type_filter not in attr:
                    continue
            
            # 蛋组过滤
            if egg_group_filter != "全部":
                eg_list = pokemon.get('egg_groups', [])
                if egg_group_filter not in eg_list:
                    continue
            
            # 进化阶段过滤
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
        
        # 排序
        filtered.sort(key=sort_fn, reverse=not self.sort_ascending)
        
        # 判断是否纯排序变化（对象身份集合相同说明内容没变）
        new_keys = {id(p) for p in filtered}
        if old_keys is not None and old_keys == new_keys:
            pass  # 纯排序变化，保留现有缓存
        else:
            # 筛选条件变了，清缓存
            self._card_pool = []
        
        self.filtered_data = filtered
        self.refresh_display()
        
    def refresh_display(self):
        """刷新显示，尽量复用已有卡片"""
        columns = 3
        total = len(self.pokemon_data)
        shown = len(self.filtered_data)
        self.stats_label.setText(f"共 {total} 个 | 显示 {shown} 个")
        
        # ── 尝试复用缓存的卡片（纯排序变化不重建） ──
        pool = getattr(self, '_card_pool', [])
        if pool:
            # 用对象身份(id())做 key，避免不同精灵共用同一 id 时字典塌成一条
            pool_keys = [id(p) for p, _ in pool]
            filtered_keys = [id(p) for p in self.filtered_data]

            if len(pool_keys) == len(filtered_keys) and set(pool_keys) == set(filtered_keys):
                # 纯排序/同批数据 - 只需重新排列
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
        
        # ── 需要重建所有卡片 ──
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
