#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
孵蛋查询子窗口
- 输入父亲/母亲，显示可搭配的同蛋组异性精灵
- 输入想生的精灵，推荐搭配方案
"""

import json
import os
import re

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QScrollArea,
    QWidget, QListWidget, QListWidgetItem, QSizePolicy,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QColor, QFont


# ── 颜色常量（与家园页面统一） ──
BG_PAGE = "#FFF8E7"
CARD_WHITE = "#ffffff"
ACCENT = "#f97316"
ACCENT_HOVER = "#ea580c"
ACCENT_LIGHT = "#fff7ed"
TEXT_DARK = "#292524"
TEXT_MED = "#78716c"
TEXT_LIGHT = "#a8a29e"
BORDER = "#e7e5e4"
BORDER_HOVER = "#fdba74"
TAG_INACTIVE_BG = "#f5f5f4"
GREEN = "#22c55e"
GREEN_LIGHT = "#f0fdf4"


# ────────────────────── 工具函数 ──────────────────────

def _load_all_pokemon():
    """加载全部精灵数据"""
    path = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "pokemon_data.json")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _parse_gender(gender_ratio):
    """解析性别比例，返回 (可雄, 可雌)"""
    if not gender_ratio:
        return False, False
    m = re.search(r'雄性\s*(\d+)%', gender_ratio)
    f = re.search(r'雌性\s*(\d+)%', gender_ratio)
    male_pct = int(m.group(1)) if m else 0
    female_pct = int(f.group(1)) if f else 0
    return male_pct > 0, female_pct > 0


def _can_be_male(pokemon):
    """是否可能为雄性"""
    return _parse_gender(pokemon.get('gender_ratio', ''))[0]


def _can_be_female(pokemon):
    """是否可能为雌性"""
    return _parse_gender(pokemon.get('gender_ratio', ''))[1]


def _get_base_form(pokemon, all_data):
    """获取精灵的基础形态（进化链第一个）"""
    chain = pokemon.get('evolution_chain', [])
    if chain:
        base_name = chain[0].get('name', '')
        # 在全部数据中找这个基础形态的完整数据
        for p in all_data:
            if p.get('name') == base_name:
                return p
    return pokemon


def _get_display_name(name):
    """获取显示名（去掉括号内的形态描述）"""
    return name.split('（')[0].split('(')[0].strip()


def _share_egg_group(p1, p2):
    """判断两只精灵是否有共同蛋组"""
    eg1 = p1.get('egg_groups', [])
    eg2 = p2.get('egg_groups', [])
    return bool(set(eg1) & set(eg2))


# ═══════════════════════════════════════════════════════
#  孵蛋查询对话框
# ═══════════════════════════════════════════════════════

class BreedingQueryDialog(QDialog):
    """孵蛋查询子窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_pokemon = _load_all_pokemon()
        self.setWindowTitle("孵蛋查询")
        self.setFixedSize(780, 620)
        self.setStyleSheet(f"background-color: {BG_PAGE};")
        
        self._selected_father = None
        self._selected_mother = None
        
        # 懒加载分页
        self._all_schemes = []
        self._loaded_count = 0
        self._scheme_title = None  # "推荐 N 种方案" 标签
        
        self._init_ui()
        
        # 事件绑定
        self.father_input.textChanged.connect(self._on_father_changed)
        self.mother_input.textChanged.connect(self._on_mother_changed)
        self.father_list.itemClicked.connect(self._on_father_selected)
        self.mother_list.itemClicked.connect(self._on_mother_selected)
    
    # ────────────────────── 界面 ──────────────────────
    
    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)
        
        # ── 标题 ──
        title = QLabel("🥚 孵蛋查询")
        title.setStyleSheet(f"""
            font-size: 20px; font-weight: 700;
            color: {TEXT_DARK}; background: transparent;
        """)
        root.addWidget(title)
        
        desc = QLabel("只有同蛋组的异性精灵才能生蛋。子代 = 母方的基础形态")
        desc.setStyleSheet(f"font-size: 13px; color: {TEXT_MED}; background: transparent;")
        root.addWidget(desc)
        
        # ── 父母输入行 ──
        parents_row = QHBoxLayout()
        parents_row.setSpacing(12)
        
        # 父亲栏
        father_group = self._create_parent_group("父亲（雄性）", ACCENT)
        self.father_input = father_group["input"]
        self.father_list = father_group["list"]
        self.father_result = father_group["result"]
        parents_row.addWidget(father_group["widget"], stretch=1)
        
        # 子代显示（中间区域）
        self.offspring_widget, self.offspring_label, self.offspring_sub = self._create_offspring_display()
        parents_row.addWidget(self.offspring_widget, stretch=0)
        
        # 母亲栏
        mother_group = self._create_parent_group("母亲（雌性）", "#ec4899")
        self.mother_input = mother_group["input"]
        self.mother_list = mother_group["list"]
        self.mother_result = mother_group["result"]
        parents_row.addWidget(mother_group["widget"], stretch=1)
        
        root.addLayout(parents_row)
        
        # ── 分隔线 ──
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {BORDER};")
        root.addWidget(line)
        
        # ── 想生的精灵 ──
        target_row = QHBoxLayout()
        target_row.setSpacing(12)
        
        target_label = QLabel("想生的精灵：")
        target_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {TEXT_DARK}; background: transparent;")
        target_row.addWidget(target_label)
        
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("输入目标精灵名称…")
        self.target_input.setFixedHeight(36)
        self.target_input.setStyleSheet(f"""
            QLineEdit {{
                border: 2px solid {BORDER}; border-radius: 8px;
                padding: 0 14px; font-size: 13px; color: {TEXT_DARK};
                background: {CARD_WHITE};
            }}
            QLineEdit:focus {{ border-color: {ACCENT}; }}
        """)
        self.target_input.textChanged.connect(self._on_target_changed)
        target_row.addWidget(self.target_input, stretch=1)
        
        root.addLayout(target_row)
        
        # ── 推荐方案展示区 ──
        self.recommend_area = QScrollArea()
        self.recommend_area.setWidgetResizable(True)
        self.recommend_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.recommend_area.setStyleSheet(f"""
            QScrollArea {{ border: 1px solid {BORDER}; border-radius: 10px;
                background: {CARD_WHITE}; }}
            QScrollBar:vertical {{ background: transparent; width: 5px; }}
            QScrollBar::handle:vertical {{ background: #d6d3d1; border-radius: 2px; min-height: 20px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        
        self.recommend_widget = QWidget()
        self.recommend_widget.setStyleSheet(f"background: transparent;")
        self.recommend_layout = QVBoxLayout(self.recommend_widget)
        self.recommend_layout.setContentsMargins(16, 12, 16, 12)
        self.recommend_layout.setSpacing(0)
        
        self.recommend_area.setWidget(self.recommend_widget)
        root.addWidget(self.recommend_area, stretch=1)
        
        # 滚动到底部时自动加载更多
        self.recommend_area.verticalScrollBar().valueChanged.connect(self._on_scroll)
        
        # 初始化推荐区域提示
        self._show_recommend_hint("输入目标精灵名称后，将显示推荐孵化方案")
    
    def _create_parent_group(self, label_text, color):
        """创建父亲/母亲输入组"""
        container = QWidget()
        container.setStyleSheet(f"background: transparent;")
        lo = QVBoxLayout(container)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(6)
        
        # 标题
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {TEXT_DARK}; background: transparent;")
        lo.addWidget(lbl)
        
        # 输入框
        inp = QLineEdit()
        inp.setPlaceholderText("输入名称搜索…")
        inp.setFixedHeight(36)
        inp.setStyleSheet(f"""
            QLineEdit {{
                border: 2px solid {color}; border-radius: 8px;
                padding: 0 14px; font-size: 13px; color: {TEXT_DARK};
                background: {CARD_WHITE};
            }}
        """)
        lo.addWidget(inp)
        
        # 候选列表
        lst = QListWidget()
        lst.setFixedHeight(100)
        lst.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {BORDER}; border-radius: 6px;
                background: {CARD_WHITE}; padding: 4px;
                font-size: 12px; color: {TEXT_DARK};
                outline: none;
            }}
            QListWidget::item {{
                padding: 4px 8px; border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background: {ACCENT_LIGHT}; color: {ACCENT};
            }}
            QListWidget::item:hover {{
                background: {TAG_INACTIVE_BG};
            }}
        """)
        lst.hide()
        lo.addWidget(lst)
        
        # 结果提示
        result = QLabel("")
        result.setStyleSheet(f"font-size: 12px; color: {TEXT_LIGHT}; background: transparent; padding: 4px 0;")
        result.setWordWrap(True)
        lo.addWidget(result)
        
        return {"widget": container, "input": inp, "list": lst, "result": result}
    
    def _create_offspring_display(self):
        """创建中间的子代显示区域（纯文字，无框）"""
        container = QWidget()
        container.setFixedWidth(100)
        container.setStyleSheet("background: transparent;")
        
        lo = QVBoxLayout(container)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(2)
        lo.setAlignment(Qt.AlignCenter)
        
        label = QLabel("子代 = ?")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"""
            font-size: 15px; font-weight: 700;
            color: {TEXT_DARK}; background: transparent;
        """)
        lo.addWidget(label, alignment=Qt.AlignCenter)
        
        sub = QLabel("选择母亲后显示")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"font-size: 11px; color: {TEXT_LIGHT}; background: transparent;")
        lo.addWidget(sub, alignment=Qt.AlignCenter)
        
        return container, label, sub
    
    def _update_offspring_display(self, mother=None, father=None):
        """更新子代显示区域，检查父母是否可生蛋"""
        # 父母都选了但不同蛋组 → 警告
        if mother and father and not _share_egg_group(mother, father):
            self.offspring_label.setText("⚠️ 无法生蛋")
            self.offspring_label.setStyleSheet(f"""
                font-size: 15px; font-weight: 700;
                color: #ef4444; background: transparent;
            """)
            self.offspring_sub.setText("非同蛋组，不能孵蛋")
            self.offspring_sub.setStyleSheet(f"font-size: 11px; color: #ef4444; background: transparent;")
            return
        
        if mother:
            offspring = self._get_offspring(mother)
            oname = _get_display_name(offspring.get('name', ''))
            self.offspring_label.setText(f"子代 = {oname}")
            self.offspring_label.setStyleSheet(f"""
                font-size: 15px; font-weight: 700;
                color: #16a34a; background: transparent;
            """)
            self.offspring_sub.setText("母方基础形态")
            self.offspring_sub.setStyleSheet(f"font-size: 11px; color: #16a34a; background: transparent;")
        else:
            self.offspring_label.setText("子代 = ?")
            self.offspring_label.setStyleSheet(f"""
                font-size: 15px; font-weight: 700;
                color: {TEXT_DARK}; background: transparent;
            """)
            self.offspring_sub.setText("选择母亲后显示")
            self.offspring_sub.setStyleSheet(f"font-size: 11px; color: {TEXT_LIGHT}; background: transparent;")
    
    # ────────────────────── 事件绑定 ──────────────────────
    
    def _on_father_changed(self, text):
        """父亲输入变化"""
        self._update_suggestions(text, self.father_input, self.father_list, is_father=True)
    
    def _on_mother_changed(self, text):
        """母亲输入变化"""
        self._update_suggestions(text, self.mother_input, self.mother_list, is_father=False)
    
    def _update_suggestions(self, text, inp, lst, is_father):
        """更新候选列表"""
        if not text:
            lst.hide()
            return
        
        # 搜索匹配的精灵
        text_lower = text.lower()
        matches = []
        for p in self.all_pokemon:
            name = p.get('name', '')
            if text_lower in name.lower():
                matches.append(p)
        
        # 按性别过滤
        if is_father:
            matches = [p for p in matches if _can_be_male(p)]
        else:
            matches = [p for p in matches if _can_be_female(p)]
        
        # 过滤首领化
        matches = [p for p in matches if not p.get('is_leader_form', False)]
        
        matches = matches[:20]  # 最多20个
        
        if not matches:
            lst.hide()
            return
        
        lst.clear()
        for p in matches:
            name = p.get('name', '')
            gender = p.get('gender_ratio', '')
            display = f"{name}  [{gender}]"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, p.get('name', ''))
            lst.addItem(item)
        
        lst.show()
    
    # ────────────────────── 查询逻辑 ──────────────────────
    
    def _find_compatible(self, pokemon, want_male):
        """查找与指定精灵同蛋组的异性精灵"""
        egg_groups = set(pokemon.get('egg_groups', []))
        if not egg_groups:
            return []
        
        results = []
        seen = set()
        for p in self.all_pokemon:
            pname = p.get('name', '')
            if pname in seen:
                continue
            p_eggs = set(p.get('egg_groups', []))
            if not egg_groups & p_eggs:
                continue
            # 性别检查
            if want_male and not _can_be_male(p):
                continue
            if not want_male and not _can_be_female(p):
                continue
            if p.get('name') == pokemon.get('name'):
                continue
            # 过滤首领化
            if p.get('is_leader_form', False):
                continue
            seen.add(pname)
            results.append(p)
        
        return results
    
    def _get_offspring(self, mother):
        """获取母方产出的子代（母方的基础形态）"""
        base = _get_base_form(mother, self.all_pokemon)
        return base
    
    def _find_target_parents(self, target_name):
        """查找能生出目标精灵的父母方案"""
        results = []
        seen_pairs = set()
        processed_mothers = set()  # 记录已处理过的母亲基础形态（避免进化链重复）
        
        for mother in self.all_pokemon:
            if not _can_be_female(mother):
                continue
            if mother.get('is_leader_form', False):
                continue
            base = _get_base_form(mother, self.all_pokemon)
            if base.get('name') != target_name:
                continue
            
            # 关键修复：同一个基础形态只处理一次（避免进化链上的不同形态重复贡献方案）
            base_name = base.get('name', '')
            if base_name in processed_mothers:
                continue
            processed_mothers.add(base_name)
            
            # 找到能与母亲配对的雄性
            mother_eggs = set(mother.get('egg_groups', []))
            if not mother_eggs:
                continue
            
            for father in self.all_pokemon:
                if not _can_be_male(father):
                    continue
                if father.get('is_leader_form', False):
                    continue
                father_eggs = set(father.get('egg_groups', []))
                if not mother_eggs & father_eggs:
                    continue
                if father.get('name') == mother.get('name'):
                    continue
                
                pair_key = (father.get('name', ''), mother.get('name', ''))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                
                results.append({
                    'father': father,
                    'mother': mother,
                    'offspring': base
                })
        
        # 调试：检查是否有重复的方案
        result_names = [f"{r['father']['name']} + {r['mother']['name']}" for r in results]
        unique_count = len(set(result_names))
        if len(results) != unique_count:
            print(f"[孵蛋查询] ⚠️ 发现重复方案! 总数:{len(results)}, 去重后:{unique_count}")
            # 找出重复的
            from collections import Counter
            counter = Counter(result_names)
            duplicates = [k for k, v in counter.items() if v > 1]
            print(f"[孵蛋查询] 重复的方案: {duplicates[:5]}")
        
        return results

    # ────────────────────── 选中与展示 ──────────────────────

    def _show_recommend_hint(self, text):
        """显示提示信息"""
        while self.recommend_layout.count():
            item = self.recommend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        hint = QLabel(text)
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"font-size: 13px; color: {TEXT_LIGHT}; background: transparent; padding: 40px 0;")
        self.recommend_layout.addWidget(hint)

    def _on_father_selected(self, item):
        """选中父亲"""
        name = item.data(Qt.UserRole)
        self.father_input.setText(name)
        self.father_list.hide()
        for p in self.all_pokemon:
            if p.get('name') == name:
                self._selected_father = p
                break
        self._update_father_result()
        # 如果母亲已选，更新兼容性
        if self._selected_mother:
            self._update_mother_result()

    def _on_mother_selected(self, item):
        """选中母亲"""
        name = item.data(Qt.UserRole)
        self.mother_input.setText(name)
        self.mother_list.hide()
        for p in self.all_pokemon:
            if p.get('name') == name:
                self._selected_mother = p
                break
        self._update_mother_result()

    def _update_father_result(self):
        """更新父亲的搭配结果"""
        if not self._selected_father:
            self.father_result.setText("")
            return
        compatible = self._find_compatible(self._selected_father, want_male=False)
        if compatible:
            self.father_result.setText(f"可搭配 {len(compatible)} 只雌性精灵")
            self.father_result.setStyleSheet(f"font-size: 12px; color: {GREEN}; background: transparent; padding: 4px 0;")
        else:
            self.father_result.setText("未找到可搭配的雌性精灵")
            self.father_result.setStyleSheet(f"font-size: 12px; color: {ACCENT}; background: transparent; padding: 4px 0;")
        # 父母兼容性检查
        self._check_pair_compatibility()

    def _update_mother_result(self):
        """更新母亲的搭配结果"""
        if not self._selected_mother:
            self.mother_result.setText("")
            self._update_offspring_display(None, self._selected_father)
            return
        compatible = self._find_compatible(self._selected_mother, want_male=True)
        # 更新子代显示区域（传入父母双方）
        self._update_offspring_display(self._selected_mother, self._selected_father)
        if compatible:
            self.mother_result.setText(f"可搭配 {len(compatible)} 只雄性精灵")
            self.mother_result.setStyleSheet(f"font-size: 12px; color: {GREEN}; background: transparent; padding: 4px 0;")
        else:
            self.mother_result.setText("未找到可搭配的雄性精灵")
            self.mother_result.setStyleSheet(f"font-size: 12px; color: {ACCENT}; background: transparent; padding: 4px 0;")
        # 父母兼容性检查
        self._check_pair_compatibility()
    
    def _check_pair_compatibility(self):
        """检查已选的父母是否可生蛋，给两边结果加提示"""
        if not self._selected_father or not self._selected_mother:
            return
        if not _share_egg_group(self._selected_father, self._selected_mother):
            msg = "⚠️ 与该精灵不同蛋组"
            self.father_result.setText(msg)
            self.father_result.setStyleSheet(f"font-size: 12px; color: #ef4444; background: transparent; padding: 4px 0;")
            self.mother_result.setText(msg)
            self.mother_result.setStyleSheet(f"font-size: 12px; color: #ef4444; background: transparent; padding: 4px 0;")

    def _on_target_changed(self, text):
        """目标精灵输入变化"""
        QTimer.singleShot(300, lambda: self._update_recommendations(text))

    def _update_recommendations(self, text):
        """更新推荐方案"""
        if not text or text != self.target_input.text():
            return

        # 清空
        while self.recommend_layout.count():
            item = self.recommend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 在全部数据中搜索目标
        target_pokemon = None
        for p in self.all_pokemon:
            if p.get('name') == text:
                target_pokemon = p
                break

        if not target_pokemon:
            # 尝试模糊搜索
            matches = [p for p in self.all_pokemon if text in p.get('name', '')]
            if not matches:
                hint = QLabel("未找到该精灵，请输入完整名称")
                hint.setAlignment(Qt.AlignCenter)
                hint.setStyleSheet(f"font-size: 13px; color: {TEXT_LIGHT}; background: transparent; padding: 40px 0;")
                self.recommend_layout.addWidget(hint)
                return

            # 显示候选
            matches = matches[:10]
            hint = QLabel("您要找的是不是：")
            hint.setStyleSheet(f"font-size: 13px; color: {TEXT_MED}; background: transparent; padding: 4px 0;")
            self.recommend_layout.addWidget(hint)

            for p in matches:
                btn = QPushButton(p.get('name', ''))
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        text-align: left; border: 1px solid {BORDER};
                        border-radius: 6px; padding: 8px 14px;
                        font-size: 13px; color: {TEXT_DARK};
                        background: {CARD_WHITE};
                    }}
                    QPushButton:hover {{ border-color: {ACCENT}; background: {ACCENT_LIGHT}; }}
                """)
                pname = p.get('name', '')
                btn.clicked.connect(lambda checked, n=pname: self.target_input.setText(n))
                self.recommend_layout.addWidget(btn)

            self.recommend_layout.addStretch()
            return

        target_name = target_pokemon.get('name', '')

        # 查找能产出目标精灵的父母方案
        parents_list = self._find_target_parents(target_name)

        if not parents_list:
            hint = QLabel("未找到能孵化出该精灵的搭配方案")
            hint.setAlignment(Qt.AlignCenter)
            hint.setStyleSheet(f"font-size: 13px; color: {TEXT_LIGHT}; background: transparent; padding: 40px 0;")
            self.recommend_layout.addWidget(hint)
            return

        # 全部方案 + 懒加载分页
        self._all_schemes = parents_list
        self._loaded_count = 0

        # 清空并显示标题
        self._show_recommend_title(len(parents_list))
        self._load_more_schemes()
        self.recommend_layout.addStretch()

    # ─── 懒加载分页 ───────────────────────────────

    def _show_recommend_title(self, total):
        """显示标题并清空推荐区"""
        while self.recommend_layout.count():
            item = self.recommend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._scheme_title = QLabel(f"推荐 {total} 种孵化方案")
        self._scheme_title.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {TEXT_DARK}; background: transparent; padding: 4px 0 12px 0;"
        )
        self.recommend_layout.addWidget(self._scheme_title)

    def _load_more_schemes(self):
        """加载下一批方案（每次 30 个）"""
        remaining = len(self._all_schemes) - self._loaded_count
        if remaining <= 0:
            return
        batch = self._all_schemes[self._loaded_count:self._loaded_count + 30]
        for scheme in batch:
            row = self._create_scheme_row(scheme)
            self.recommend_layout.addWidget(row)
        self._loaded_count += len(batch)

    def _on_scroll(self, value):
        """滚动检测：到底部时加载更多"""
        scrollbar = self.recommend_area.verticalScrollBar()
        if value >= scrollbar.maximum() - 20:  # 接近底部时触发
            self._load_more_schemes()

    def _create_scheme_row(self, scheme):
        """创建方案行"""
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background: {CARD_WHITE};
                border: 1px solid {BORDER};
                border-radius: 10px;
                margin: 4px 0;
            }}
            QFrame:hover {{ border-color: {ACCENT}; }}
        """)

        lo = QHBoxLayout(container)
        lo.setContentsMargins(12, 8, 12, 8)
        lo.setSpacing(12)
        lo.setAlignment(Qt.AlignLeft)

        father = scheme['father']
        mother = scheme['mother']
        offspring = scheme['offspring']

        # 父亲卡
        f_card = BreedingMiniCard(father, "父")
        lo.addWidget(f_card)

        # + 号
        plus = QLabel("+")
        plus.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {TEXT_MED}; background: transparent;")
        lo.addWidget(plus)

        # 母亲卡
        m_card = BreedingMiniCard(mother, "母")
        lo.addWidget(m_card)

        # 箭头
        arrow = QLabel("→")
        arrow.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {ACCENT}; background: transparent;")
        lo.addWidget(arrow)

        # 子代卡
        o_card = BreedingMiniCard(offspring, "蛋")
        lo.addWidget(o_card)

        lo.addStretch()

        # 蛋组标签
        common_eggs = set(father.get('egg_groups', [])) & set(mother.get('egg_groups', []))
        if common_eggs:
            tag = QLabel(f"{'/'.join(common_eggs)}")
            tag.setStyleSheet(f"""
                font-size: 11px; color: {TEXT_LIGHT};
                background: {GREEN_LIGHT}; border-radius: 10px;
                padding: 2px 12px;
            """)
            lo.addWidget(tag)
        else:
            # 非同蛋组警告
            warn = QLabel("⚠️ 非同蛋组")
            warn.setStyleSheet(f"""
                font-size: 11px; font-weight: 600; color: white;
                background: #ef4444; border-radius: 10px;
                padding: 2px 12px;
            """)
            lo.addWidget(warn)

        return container


# ═══════════════════════════════════════════════════════
#  精灵迷你卡片（方案展示用）
# ═══════════════════════════════════════════════════════

class BreedingMiniCard(QFrame):
    """方案中的小卡片"""
    
    def __init__(self, pokemon, label="", parent=None):
        super().__init__(parent)
        self.setFixedSize(86, 110)
        self.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border: none;
                border-radius: 0px;
            }}
        """)
        
        lo = QVBoxLayout(self)
        lo.setContentsMargins(4, 4, 4, 4)
        lo.setSpacing(0)
        lo.setAlignment(Qt.AlignCenter)
        
        # 图片
        img = QLabel()
        img.setFixedSize(48, 48)
        img.setAlignment(Qt.AlignCenter)
        pid = pokemon.get('id', 0)
        img_path = os.path.join(os.path.dirname(__file__), "..", "image", "tj", "images", f"{pid:03d}.png")
        if os.path.exists(img_path):
            pm = QPixmap(img_path)
            if not pm.isNull():
                s = pm.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img.setPixmap(s)
        lo.addWidget(img, alignment=Qt.AlignCenter)
        
        # 名字（增加顶部间距）
        raw = pokemon.get('name', '')
        display = _get_display_name(raw)
        if len(display) > 5:
            display = display[:4] + '…'
        name_lbl = QLabel(display)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet(f"""
            font-size: 10px; font-weight: 500; color: {TEXT_DARK};
            background: transparent; padding-top: 6px;
        """)
        lo.addWidget(name_lbl, alignment=Qt.AlignCenter)
        
        # 标签
        if label:
            tag = QLabel(label)
            tag.setAlignment(Qt.AlignCenter)
            tag.setFixedHeight(18)
            c = ACCENT if label == "父" else ("#ec4899" if label == "母" else GREEN)
            tag.setStyleSheet(f"""
                font-size: 9px; font-weight: 600; color: white;
                background-color: {c}; border-radius: 9px;
                padding: 0 8px;
            """)
            lo.addWidget(tag, alignment=Qt.AlignCenter)