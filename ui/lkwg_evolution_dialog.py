# ui/lkwg_evolution_dialog.py
"""进化链配置对话框"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFrame, QWidget, QMessageBox,
                               QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QColor
import os
from ui.pokedex_view import SCROLL_BAR_STYLE


class EvolutionChainDialog(QDialog):
    """进化链配置对话框（动态增减模式）"""
    
    def __init__(self, selected_pokemon, all_pokemons, parent=None):
        super().__init__(parent)
        self.selected_pokemon = selected_pokemon
        self.all_pokemons = all_pokemons
        # 进化链：[退化..., 当前, 进化...]
        self.evolution_chain = [selected_pokemon]
        
        self.setWindowTitle("配置进化链")
        self.setFixedSize(700, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
            }
            QLabel {
                color: #f8f0ff;
            }
            QPushButton {
                background-color: #7c3aed;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #6d28d9;
            }
            QPushButton:disabled {
                background-color: #4b5563;
                color: #9ca3af;
            }
        """)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title = QLabel("配置进化链")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #e0aaff;")
        layout.addWidget(title)
        
        # 操作按钮行
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(20)
        
        # 左侧：添加上一阶段
        btn_prev = QPushButton("← 添加上一阶段")
        btn_prev.setFixedHeight(40)
        btn_prev.clicked.connect(lambda: self._add_stage('prev'))
        btn_layout.addWidget(btn_prev)
        
        # 中间：当前精灵（只读）
        current_label = QLabel(f"{self.selected_pokemon['name']}")
        current_label.setAlignment(Qt.AlignCenter)
        current_label.setStyleSheet("color: #f8f0ff; font-size: 16px; font-weight: bold;")
        btn_layout.addWidget(current_label, stretch=1)
        
        # 右侧：添加下一阶段
        btn_next = QPushButton("添加下一阶段 →")
        btn_next.setFixedHeight(40)
        btn_next.clicked.connect(lambda: self._add_stage('next'))
        btn_layout.addWidget(btn_next)
        
        layout.addWidget(btn_row)
        
        # 进化链展示区（滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(SCROLL_BAR_STYLE)
        
        self.chain_container = QWidget()
        self.chain_layout = QVBoxLayout(self.chain_container)
        self.chain_layout.setContentsMargins(10, 10, 10, 10)
        self.chain_layout.setSpacing(10)
        
        scroll.setWidget(self.chain_container)
        scroll.setFixedHeight(250)
        layout.addWidget(scroll)
        
        # 说明文字
        hint = QLabel("提示：点击左右按钮添加节点，×删除节点（基础精灵不可删），最多3个阶段")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color: #a78bfa; font-size: 12px;")
        layout.addWidget(hint)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedWidth(100)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_confirm = QPushButton("确认添加")
        btn_confirm.setFixedWidth(100)
        btn_confirm.setObjectName("confirmBtn")
        btn_confirm.clicked.connect(self._on_confirm)
        btn_layout.addWidget(btn_confirm)
        
        layout.addLayout(btn_layout)
        
        # 初始渲染
        self._render_chain()
    
    def _render_chain(self):
        """渲染进化链列表"""
        # 清空现有内容
        for i in reversed(range(self.chain_layout.count())):
            widget = self.chain_layout.takeAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 渲染每个节点
        for idx, pokemon in enumerate(self.evolution_chain):
            is_base = (idx == 0 and len([p for p in self.evolution_chain if p['name'] == self.selected_pokemon['name']]) == 1)
            # 更准确的判断：是否是初始选中的那个
            is_base = (pokemon['name'] == self.selected_pokemon['name'] and 
                      self.evolution_chain.index(pokemon) == 0 and
                      len([p for p in self.evolution_chain[:1] if p['name'] == pokemon['name']]) == 1)
            
            card = self._create_chain_card(pokemon, idx, is_base)
            self.chain_layout.addWidget(card)
        
        self.chain_layout.addStretch()
    
    def _create_chain_card(self, pokemon, index, is_base):
        """创建进化链节点卡片"""
        card = QFrame()
        card.setFixedHeight(80)
        card.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border: 2px solid #7c3aed;
                border-radius: 10px;
            }
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)
        
        # 序号标签
        stage_num = QLabel(f"第{index + 1}阶段")
        stage_num.setFixedWidth(70)
        stage_num.setStyleSheet("color: #c084fc; font-size: 13px; font-weight: 600;")
        layout.addWidget(stage_num)
        
        # 图标
        icon_label = QLabel()
        icon_label.setFixedSize(60, 60)
        self._load_pokemon_icon(icon_label, pokemon)
        layout.addWidget(icon_label)
        
        # 名称
        name_label = QLabel(pokemon['name'])
        name_label.setStyleSheet("color: #f8f0ff; font-size: 15px; font-weight: 600;")
        layout.addWidget(name_label, stretch=1)
        
        # 删除按钮（基础精灵不显示）
        if not is_base:
            btn_delete = QPushButton("删除")
            btn_delete.setFixedWidth(70)
            btn_delete.setFixedHeight(30)
            btn_delete.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 12px;
                    padding: 0 8px;
                }
                QPushButton:hover {
                    background-color: #dc2626;
                }
            """)
            btn_delete.clicked.connect(lambda: self._remove_stage(index))
            layout.addWidget(btn_delete)
        else:
            # 基础精灵显示锁定图标
            lock_label = QLabel("🔒")
            lock_label.setFixedSize(30, 30)
            lock_label.setAlignment(Qt.AlignCenter)
            lock_label.setStyleSheet("font-size: 16px;")
            layout.addWidget(lock_label)
        
        return card
    
    def _load_pokemon_icon(self, icon_label, pokemon):
        """加载精灵图标"""
        pokemon_id = pokemon.get('id', 0)
        image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "tj", "images")
        image_path = os.path.join(image_dir, f"{pokemon_id:03d}.png")
        
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                rounded_pixmap = QPixmap(60, 60)
                rounded_pixmap.fill(Qt.transparent)
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, 60, 60)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.end()
                icon_label.setPixmap(rounded_pixmap)
                icon_label.setStyleSheet("")
                return
        
        icon_label.setText("🐾")
        icon_label.setStyleSheet("font-size: 30px; color: #a78bfa;")
    
    def _add_stage(self, position):
        """添加进化阶段"""
        # 检查是否已达上限
        if len(self.evolution_chain) >= 3:
            QMessageBox.warning(self, "警告", "最多支持3个阶段！")
            return
        
        from ui.lkwg_pokedex_selector import LkwgPokedexSelector
        
        selector = LkwgPokedexSelector(self.all_pokemons, self)
        if selector.exec():
            selected = selector.get_selected()
            
            # 检查是否重复
            if any(p['name'] == selected['name'] for p in self.evolution_chain):
                QMessageBox.warning(self, "警告", f"{selected['name']}已在进化链中！")
                return
            
            if position == 'prev':
                # 添加到头部
                self.evolution_chain.insert(0, selected)
            else:
                # 添加到尾部
                self.evolution_chain.append(selected)
            
            # 重新渲染
            self._render_chain()
    
    def _remove_stage(self, index):
        """删除进化阶段"""
        if index < 0 or index >= len(self.evolution_chain):
            return
        
        # 不能删除基础精灵（第一个）
        if index == 0:
            return
        
        del self.evolution_chain[index]
        self._render_chain()
    
    def _on_confirm(self):
        """确认配置"""
        if len(self.evolution_chain) < 1:
            QMessageBox.warning(self, "警告", "进化链不能为空")
            return
        
        self.accept()
    
    def get_evolution_chain(self):
        """获取进化链（返回名称列表）"""
        return [p['name'] for p in self.evolution_chain]
