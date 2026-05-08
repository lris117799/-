# ui/lkwg_pokedex_selector.py
"""洛克王国图鉴选择器"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget,
                                QLabel, QLineEdit, QPushButton, QScrollArea,
                                QFrame, QMessageBox, QSizePolicy)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
import os
from ui.pokedex_view import SCROLL_BAR_STYLE


class LkwgPokedexSelector(QDialog):
    """从图鉴中选择精灵的对话框"""
    
    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.setWindowTitle("从图鉴选择精灵")
        self.setModal(True)
        self.setFixedSize(900, 700)
        
        self.database = database or []
        self.selected_data = None
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # 头部
        header = self._create_header()
        main_layout.addWidget(header)
        
        # 搜索框
        search_box = self._create_search_box()
        main_layout.addWidget(search_box)
        
        # 精灵网格
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(SCROLL_BAR_STYLE)
        
        self.grid_container = QWidget()
        self.grid_layout = self._create_grid_layout()
        scroll.setWidget(self.grid_container)
        
        main_layout.addWidget(scroll, stretch=1)
        
        # 底部按钮
        footer = self._create_footer()
        main_layout.addWidget(footer)
        
        # 初始加载
        self._refresh_grid()
    
    def _create_header(self):
        """创建头部"""
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("从图鉴选择精灵")
        title.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
        header_layout.addWidget(title)
        
        subtitle = QLabel("选择后将自动继承属性和图标")
        subtitle.setStyleSheet("color: #a78bfa; font-size: 13px; margin-left: 12px;")
        header_layout.addWidget(subtitle)
        header_layout.addStretch()
        
        return header
    
    def _create_search_box(self):
        """创建搜索框"""
        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 搜索精灵名称...")
        self.search_edit.setMinimumHeight(40)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #7c3aed;
            }
        """)
        self.search_edit.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_edit)
        
        return search_widget
    
    def _on_search_changed(self, text):
        """搜索文本变化"""
        self._refresh_grid(text)
    
    def _create_grid_layout(self):
        """创建网格布局"""
        layout = QVBoxLayout(self.grid_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        return layout
    
    def _create_grid(self):
        """创建网格容器"""
        grid = QWidget()
        grid_layout = self._create_grid_layout()
        return grid, grid_layout
    
    def _refresh_grid(self, search_text=""):
        """刷新精灵网格"""
        # 清空现有内容
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.takeAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 过滤精灵
        filtered = []
        for pokemon in self.database:
            name = pokemon.get('name', '')
            if search_text and search_text.lower() not in name.lower():
                continue
            filtered.append(pokemon)
        
        if not filtered:
            no_result = QLabel("未找到匹配的精灵")
            no_result.setAlignment(Qt.AlignCenter)
            no_result.setStyleSheet("color: #71717a; font-size: 14px; padding: 40px;")
            self.grid_layout.addWidget(no_result)
            return
        
        # 创建网格（3列）
        grid_widget = QWidget()
        grid = self._create_actual_grid(grid_widget, filtered)
        self.grid_layout.addWidget(grid_widget)
    
    def _create_actual_grid(self, container, pokemons):
        """创建实际网格"""
        grid_layout = QVBoxLayout(container)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(12)
        
        # 每行3个
        row_count = (len(pokemons) + 2) // 3
        
        for row in range(row_count):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)
            
            for col in range(3):
                idx = row * 3 + col
                if idx < len(pokemons):
                    card = self._create_pokemon_card(pokemons[idx])
                    row_layout.addWidget(card, stretch=1)
                else:
                    spacer = QWidget()
                    spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                    row_layout.addWidget(spacer, stretch=1)
            
            grid_layout.addWidget(row_widget)
        
        grid_layout.addStretch()
        
        return container
    
    def _create_pokemon_card(self, pokemon):
        """创建精灵卡片（参考异色图鉴样式）"""
        card = QFrame()
        card.setObjectName("pokedexItem")
        card.setFixedWidth(180)
        card.setFixedHeight(220)
        card.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)
        
        # 圆形头像
        avatar = QLabel()
        avatar.setFixedSize(80, 80)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("background: transparent;")
        
        pokemon_name = pokemon.get('name', '')
        pokemon_id = pokemon.get('id', 0)
        image_loaded = False
        
        # 从tj/images文件夹按ID加载图片
        image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "tj", "images")
        if pokemon_id > 0 and os.path.exists(image_dir):
            image_filename = f"{pokemon_id:03d}.png"
            image_path = os.path.join(image_dir, image_filename)
            
            if os.path.exists(image_path):
                from PySide6.QtGui import QPainter, QPainterPath
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    rounded_pixmap = QPixmap(80, 80)
                    rounded_pixmap.fill(Qt.transparent)
                    painter = QPainter(rounded_pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform)
                    path = QPainterPath()
                    path.addEllipse(0, 0, 80, 80)
                    painter.setClipPath(path)
                    painter.drawPixmap(0, 0, scaled_pixmap)
                    painter.end()
                    avatar.setPixmap(rounded_pixmap)
                    image_loaded = True
        
        # 如果图片未加载，使用默认样式
        if not image_loaded:
            avatar.setText(pokemon_name[0] if pokemon_name else '?')
            avatar.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #c77dff, stop:1 #9d4edd);
                    border-radius: 40px;
                    color: white;
                    font-size: 36px;
                    font-weight: bold;
                }
            """)
        
        layout.addWidget(avatar, 0, Qt.AlignHCenter)
        
        # 名称
        name_label = QLabel(pokemon_name)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 600;")
        layout.addWidget(name_label)
        
        # 属性标签
        attribute = pokemon.get('attribute', '')
        if attribute:
            # 添加“系”后缀（如“光”→“光系”）
            type_str = attribute + "系" if not attribute.endswith("系") else attribute
        else:
            type_str = "未知"
        
        type_label = QLabel(type_str)
        type_label.setAlignment(Qt.AlignCenter)
        type_label.setStyleSheet("""
            QLabel {
                background-color: rgba(124, 58, 237, 0.2);
                color: #a78bfa;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        layout.addWidget(type_label, 0, Qt.AlignHCenter)
        
        # 描述
        desc_label = QLabel("图鉴精灵")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #71717a; font-size: 12px;")
        layout.addWidget(desc_label)
        
        # 点击事件
        def on_click(event, p=pokemon, c=card):
            if event.button() == Qt.LeftButton:
                self._on_card_clicked(p, c)
        
        card.mousePressEvent = on_click
        
        # 悬停效果
        def enter_event(event):
            if card.property("selected"):
                return
            card.setStyleSheet("""
                QFrame#pokedexItem {
                    background-color: #2a184a;
                    border: 1px solid rgba(199, 125, 255, 0.6);
                }
            """)
        
        def leave_event(event):
            if card.property("selected"):
                return
            card.setStyleSheet("")
        
        card.enterEvent = enter_event
        card.leaveEvent = leave_event
        
        return card
    
    def _on_card_clicked(self, pokemon, card_widget):
        """卡片点击"""
        # 清除之前的选中状态
        for child in self.findChildren(QFrame):
            if child.objectName() == "pokedexItem":
                child.setProperty("selected", False)
                child.setStyleSheet("")
        
        # 设置当前选中状态
        card_widget.setProperty("selected", True)
        card_widget.setStyleSheet("""
            QFrame#pokedexItem {
                background-color: #2a184a;
                border: 2px solid #7c3aed;
            }
        """)
        
        self.selected_data = pokemon
    
    def _create_footer(self):
        """创建底部按钮"""
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(12)
        footer_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 16px;
                color: #e4e4e7;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2a2a35;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)
        
        confirm_btn = QPushButton("确认选择")
        confirm_btn.setFixedHeight(40)
        confirm_btn.setMinimumWidth(100)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #7c3aed;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #8b5cf6;
            }
        """)
        confirm_btn.clicked.connect(self._on_confirm)
        footer_layout.addWidget(confirm_btn)
        
        return footer
    
    def _on_confirm(self):
        """确认选择"""
        if not self.selected_data:
            QMessageBox.warning(self, "提示", "请先选择一个精灵！")
            return
        self.accept()
    
    def get_selected(self):
        """获取选中的精灵数据"""
        return self.selected_data
