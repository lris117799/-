# ui/lkwg_manual_dialog.py
"""手动新建自定义精灵对话框"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget, 
                                QLabel, QLineEdit, QPushButton, QComboBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
import os
import re


class LkwgManualDialog(QDialog):
    """手动新建自定义精灵"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("手动新建自定义精灵")
        self.setModal(True)
        self.setFixedSize(800, 700)
        
        self.selected_icon_path = ""
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 头部
        header = self._create_header()
        main_layout.addWidget(header)
        
        # 主体
        body = self._create_body()
        main_layout.addWidget(body)
        
        # 底部
        footer = self._create_footer()
        main_layout.addWidget(footer)
    
    def _create_header(self):
        """创建头部"""
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #1a1a22;
                border-bottom: 1px solid rgba(124, 58, 237, 0.1);
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 16)
        
        title = QLabel("手动新建自定义精灵")
        title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 600;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                color: #71717a;
                background: transparent;
                border: none;
                font-size: 20px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)
        
        return header
    
    def _create_body(self):
        """创建主体"""
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(32, 28, 32, 28)
        body_layout.setSpacing(18)
        
        # 精灵名称
        name_group = self._create_input_field("精灵名称", "请输入精灵名称", "name_edit")
        body_layout.addWidget(name_group)
        
        # 属性
        type_group = self._create_type_selection()
        body_layout.addWidget(type_group)
        
        # 默认保底次数
        target_group = self._create_input_field("默认保底次数", "80", "target_edit", is_number=True)
        body_layout.addWidget(target_group)
        
        # 精灵图标
        icon_group = self._create_icon_selection()
        body_layout.addWidget(icon_group)
        
        body_layout.addStretch()
        
        return body
    
    def _create_input_field(self, label_text, placeholder, attr_name, is_number=False):
        """创建输入字段"""
        group = QWidget()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        label = QLabel(label_text)
        label.setStyleSheet("color: #71717a; font-size: 12px;")
        layout.addWidget(label)
        
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMinimumHeight(40)
        if is_number:
            edit.setText(placeholder)
        edit.setStyleSheet("""
            QLineEdit {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 15px;
            }
            QLineEdit:focus {
                border: 1px solid #7c3aed;
            }
        """)
        
        setattr(self, attr_name, edit)
        layout.addWidget(edit)
        
        return group
    
    def _create_type_selection(self):
        """创建属性选择"""
        group = QWidget()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        label = QLabel("属性")
        label.setStyleSheet("color: #71717a; font-size: 12px;")
        layout.addWidget(label)
        
        type_row = QWidget()
        type_layout = QHBoxLayout(type_row)
        type_layout.setContentsMargins(0, 4, 0, 0)
        type_layout.setSpacing(8)
        
        from core.pokemon_types import get_all_types
        
        self.type_combo_1 = QComboBox()
        self.type_combo_1.addItems(["请选择"] + get_all_types())
        self.type_combo_1.setMinimumHeight(40)
        self.type_combo_1.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 15px;
            }
        """)
        type_layout.addWidget(self.type_combo_1)
        
        self.type_combo_2 = QComboBox()
        self.type_combo_2.addItems(["无"] + get_all_types())
        self.type_combo_2.setMinimumHeight(40)
        self.type_combo_2.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 15px;
            }
        """)
        type_layout.addWidget(self.type_combo_2)
        
        layout.addWidget(type_row)
        
        return group
    
    def _create_evolution_field(self):
        """创建进化链输入"""
        group = QWidget()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        label = QLabel("进化链（选填，用 → 分隔，如：雪娃娃 → 冰封怨灵 → 雪灵）")
        label.setStyleSheet("color: #71717a; font-size: 12px;")
        layout.addWidget(label)
        
        self.evolution_edit = QLineEdit()
        self.evolution_edit.setPlaceholderText("例如：雪娃娃 → 冰封怨灵 → 雪灵")
        self.evolution_edit.setMinimumHeight(40)
        self.evolution_edit.setStyleSheet("""
            QLineEdit {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e4e4e7;
                font-size: 15px;
            }
            QLineEdit:focus {
                border: 1px solid #7c3aed;
            }
        """)
        layout.addWidget(self.evolution_edit)
        
        return group
    
    def _create_icon_selection(self):
        """创建图标选择"""
        group = QWidget()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        label = QLabel("精灵图标")
        label.setStyleSheet("color: #71717a; font-size: 12px;")
        layout.addWidget(label)
        
        icon_row = QWidget()
        icon_layout = QHBoxLayout(icon_row)
        icon_layout.setContentsMargins(0, 4, 0, 0)
        icon_layout.setSpacing(12)
        
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(60, 60)
        self.icon_preview.setAlignment(Qt.AlignCenter)
        self.icon_preview.setText("无图片")
        self.icon_preview.setStyleSheet("""
            QLabel {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                color: #71717a;
                font-size: 12px;
            }
        """)
        icon_layout.addWidget(self.icon_preview)
        
        select_btn = QPushButton("📁 选择图片")
        select_btn.setFixedHeight(40)
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 10px 16px;
                color: #e4e4e7;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(124, 58, 237, 0.1);
                border: 1px solid #7c3aed;
            }
        """)
        select_btn.clicked.connect(self._select_icon_image)
        icon_layout.addWidget(select_btn, stretch=1)
        
        layout.addWidget(icon_row)
        
        return group
    
    def _select_icon_image(self):
        """选择本地图片"""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择精灵图标",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            self.selected_icon_path = file_path
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.icon_preview.setPixmap(scaled)
                self.icon_preview.setText("")
    
    def _create_footer(self):
        """创建底部按钮"""
        footer = QWidget()
        footer.setStyleSheet("""
            QWidget {
                background-color: #1a1a22;
                border-top: 1px solid rgba(124, 58, 237, 0.1);
            }
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(32, 20, 32, 20)
        footer_layout.setSpacing(12)
        footer_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("customPokemonBtn")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)
        
        confirm_btn = QPushButton("确认添加")
        confirm_btn.setObjectName("customPokemonBtn")
        confirm_btn.setFixedHeight(40)
        confirm_btn.setMinimumWidth(100)
        confirm_btn.setStyleSheet("""
            QPushButton#customPokemonBtn {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c3aed, stop:1 #a855f7);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton#customPokemonBtn:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9333ea, stop:1 #c084fc);
            }
        """)
        confirm_btn.clicked.connect(self.accept)
        footer_layout.addWidget(confirm_btn)
        
        return footer
    
    def get_data(self):
        """获取表单数据"""
        name = self.name_edit.text().strip()
        
        # 获取属性
        type1 = self.type_combo_1.currentText()
        type2 = self.type_combo_2.currentText()
        types = []
        if type1 != "请选择":
            types.append(type1)
        if type2 != "无" and type2 != "请选择":
            types.append(type2)
        type_str = "、".join(types) if types else ""
        
        # 获取保底次数
        try:
            target = int(self.target_edit.text())
        except:
            target = 80
        
        # 手动新建无进化链
        evolution_chain = []
        
        return (name, type_str, str(target), self.selected_icon_path, evolution_chain)
