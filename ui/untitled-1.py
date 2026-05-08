from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QWidget, QScrollArea, QGroupBox, QCheckBox, QSpinBox, 
    QDoubleSpinBox, QFormLayout, QTabWidget
)
from PySide6.QtCore import Qt


class SettingsDialog(QDialog):
    """设置对话框 - 专业标签页风格"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("助手设置")
        self.setModal(True)
        self.setFixedSize(700, 600)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 对话框头部
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #1a1a22;
                border-bottom: 1px solid rgba(124, 58, 237, 0.1);
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 16)
        
        title = QLabel("助手设置")
        title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 600;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton {
                color: #71717a;
                background: transparent;
                border: none;
                font-size: 20px;
                border-radius: 14px;
                transition: all 0.2s ease;
            }
            QPushButton:hover {
                color: #ffffff;
                background-color: rgba(124, 58, 237, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(124, 58, 237, 0.2);
            }
        """)
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)
        
        main_layout.addWidget(header)
        
        # 标签页容器
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget {
                background-color: #121212;
            }
            QTabBar {
                background-color: #1a1a22;
                border-bottom: 1px solid rgba(124, 58, 237, 0.1);
                padding: 0;
            }
            QTabBar::tab {
                background-color: transparent;
                color: #71717a;
                padding: 12px 24px;
                margin: 0;
                border-bottom: 2px solid transparent;
                font-size: 14px;
                font-weight: 500;
                transition: all 0.2s ease;
            }
            QTabBar::tab:hover {
                color: #a1a1aa;
                background-color: rgba(124, 58, 237, 0.05);
            }
            QTabBar::tab:selected {
                color: #a78bfa;
                border-bottom-color: #a78bfa;
                background-color: rgba(124, 58, 237, 0.08);
            }
            QTabWidget::pane {
                border: none;
                background-color: #121212;
            }
        """)
        
        # 通用设置标签
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_layout.setContentsMargins(32, 24, 32, 24)
        general_layout.setSpacing(24)
        
        # 通用设置组
        general_group = self._create_settings_group("基础设置")
        general_group_layout = QVBoxLayout()
        general_group_layout.setSpacing(16)
        
        # 开机自启
        auto_start_check = QCheckBox("开机自动启动")
        auto_start_check.setStyleSheet("""
            QCheckBox {
                color: #e4e4e7;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid rgba(124, 58, 237, 0.3);
                border-radius: 4px;
                background-color: #252530;
                transition: all 0.2s ease;
            }
            QCheckBox::indicator:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
            QCheckBox::indicator:checked {
                background-color: #7c3aed;
                border-color: #7c3aed;
            }
        """)
        general_group_layout.addWidget(auto_start_check)
        
        # 最小化到托盘
        minimize_to_tray = QCheckBox("关闭时最小化到系统托盘")
        minimize_to_tray.setStyleSheet("""
            QCheckBox {
                color: #e4e4e7;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid rgba(124, 58, 237, 0.3);
                border-radius: 4px;
                background-color: #252530;
                transition: all 0.2s ease;
            }
            QCheckBox::indicator:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
            QCheckBox::indicator:checked {
                background-color: #7c3aed;
                border-color: #7c3aed;
            }
        """)
        general_group_layout.addWidget(minimize_to_tray)
        
        general_group.setLayout(general_group_layout)
        general_layout.addWidget(general_group)
        
        # 外观设置组
        appearance_group = self._create_settings_group("外观设置")
        appearance_layout = QVBoxLayout()
        appearance_layout.setSpacing(16)
        
        # 深色模式
        dark_mode_check = QCheckBox("使用深色模式")
        dark_mode_check.setChecked(True)
        dark_mode_check.setStyleSheet("""
            QCheckBox {
                color: #e4e4e7;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid rgba(124, 58, 237, 0.3);
                border-radius: 4px;
                background-color: #252530;
                transition: all 0.2s ease;
            }
            QCheckBox::indicator:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
            QCheckBox::indicator:checked {
                background-color: #7c3aed;
                border-color: #7c3aed;
            }
        """)
        appearance_layout.addWidget(dark_mode_check)
        
        # 显示动画
        animation_check = QCheckBox("启用界面动画效果")
        animation_check.setChecked(True)
        animation_check.setStyleSheet("""
            QCheckBox {
                color: #e4e4e7;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid rgba(124, 58, 237, 0.3);
                border-radius: 4px;
                background-color: #252530;
                transition: all 0.2s ease;
            }
            QCheckBox::indicator:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
            QCheckBox::indicator:checked {
                background-color: #7c3aed;
                border-color: #7c3aed;
            }
        """)
        appearance_layout.addWidget(animation_check)
        
        appearance_group.setLayout(appearance_layout)
        general_layout.addWidget(appearance_group)
        
        general_layout.addStretch()
        tab_widget.addTab(general_tab, "通用设置")
        
        # 识别设置标签
        ocr_tab = QWidget()
        ocr_layout = QVBoxLayout(ocr_tab)
        ocr_layout.setContentsMargins(32, 24, 32, 24)
        ocr_layout.setSpacing(24)
        
        # 图像识别设置组
        ocr_group = self._create_settings_group("图像识别")
        ocr_group_layout = QFormLayout()
        ocr_group_layout.setSpacing(16)
        ocr_group_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        # 识别间隔
        interval_spin = QSpinBox()
        interval_spin.setRange(100, 5000)
        interval_spin.setValue(500)
        interval_spin.setSuffix(" ms")
        interval_spin.setStyleSheet("""
            QSpinBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 8px 12px;
                color: #e4e4e7;
                font-size: 13px;
                transition: all 0.2s ease;
            }
            QSpinBox:hover {
                border-color: rgba(124, 58, 237, 0.5);
            }
            QSpinBox:focus {
                border-color: #7c3aed;
                box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
            }
            QSpinBox::up-button,
            QSpinBox::down-button {
                width: 20px;
                background-color: rgba(124, 58, 237, 0.1);
                border-radius: 4px;
            }
        """)
        ocr_group_layout.addRow("识别间隔：", interval_spin)
        
        # 置信度阈值
        confidence_spin = QDoubleSpinBox()
        confidence_spin.setRange(0.5, 1.0)
        confidence_spin.setValue(0.8)
        confidence_spin.setSingleStep(0.05)
        confidence_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 8px 12px;
                color: #e4e4e7;
                font-size: 13px;
                transition: all 0.2s ease;
            }
            QDoubleSpinBox:hover {
                border-color: rgba(124, 58, 237, 0.5);
            }
            QDoubleSpinBox:focus {
                border-color: #7c3aed;
                box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
            }
            QDoubleSpinBox::up-button,
            QDoubleSpinBox::down-button {
                width: 20px;
                background-color: rgba(124, 58, 237, 0.1);
                border-radius: 4px;
            }
        """)
        ocr_group_layout.addRow("识别置信度：", confidence_spin)
        
        ocr_group.setLayout(ocr_group_layout)
        ocr_layout.addWidget(ocr_group)
        
        # 高级识别设置组
        advanced_ocr_group = self._create_settings_group("高级识别")
        advanced_ocr_layout = QVBoxLayout()
        advanced_ocr_layout.setSpacing(16)
        
        # 区域识别
        area_check = QCheckBox("使用区域识别模式")
        area_check.setStyleSheet("""
            QCheckBox {
                color: #e4e4e7;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid rgba(124, 58, 237, 0.3);
                border-radius: 4px;
                background-color: #252530;
                transition: all 0.2s ease;
            }
            QCheckBox::indicator:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
            QCheckBox::indicator:checked {
                background-color: #7c3aed;
                border-color: #7c3aed;
            }
        """)
        advanced_ocr_layout.addWidget(area_check)
        
        # 自动调整
        auto_adjust_check = QCheckBox("自动调整识别区域")
        auto_adjust_check.setStyleSheet("""
            QCheckBox {
                color: #e4e4e7;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid rgba(124, 58, 237, 0.3);
                border-radius: 4px;
                background-color: #252530;
                transition: all 0.2s ease;
            }
            QCheckBox::indicator:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
            QCheckBox::indicator:checked {
                background-color: #7c3aed;
                border-color: #7c3aed;
            }
        """)
        advanced_ocr_layout.addWidget(auto_adjust_check)
        
        advanced_ocr_group.setLayout(advanced_ocr_layout)
        ocr_layout.addWidget(advanced_ocr_group)
        
        ocr_layout.addStretch()
        tab_widget.addTab(ocr_tab, "识别设置")
        
        # 计数器设置标签
        counter_tab = QWidget()
        counter_layout = QVBoxLayout(counter_tab)
        counter_layout.setContentsMargins(32, 24, 32, 24)
        counter_layout.setSpacing(24)
        
        # 计数器默认设置组
        counter_group = self._create_settings_group("默认设置")
        counter_group_layout = QFormLayout()
        counter_group_layout.setSpacing(16)
        counter_group_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        # 默认保底次数
        default_target = QSpinBox()
        default_target.setRange(10, 999)
        default_target.setValue(80)
        default_target.setStyleSheet("""
            QSpinBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 8px 12px;
                color: #e4e4e7;
                font-size: 13px;
                transition: all 0.2s ease;
            }
            QSpinBox:hover {
                border-color: rgba(124, 58, 237, 0.5);
            }
            QSpinBox:focus {
                border-color: #7c3aed;
                box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
            }
            QSpinBox::up-button,
            QSpinBox::down-button {
                width: 20px;
                background-color: rgba(124, 58, 237, 0.1);
                border-radius: 4px;
            }
        """)
        counter_group_layout.addRow("默认保底次数：", default_target)
        
        # 基础概率
        base_prob = QDoubleSpinBox()
        base_prob.setRange(0.1, 10.0)
        base_prob.setValue(1.8)
        base_prob.setSingleStep(0.1)
        base_prob.setSuffix(" %")
        base_prob.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 8px;
                padding: 8px 12px;
                color: #e4e4e7;
                font-size: 13px;
                transition: all 0.2s ease;
            }
            QDoubleSpinBox:hover {
                border-color: rgba(124, 58, 237, 0.5);
            }
            QDoubleSpinBox:focus {
                border-color: #7c3aed;
                box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
            }
            QDoubleSpinBox::up-button,
            QDoubleSpinBox::down-button {
                width: 20px;
                background-color: rgba(124, 58, 237, 0.1);
                border-radius: 4px;
            }
        """)
        counter_group_layout.addRow("基础异色概率：", base_prob)
        
        counter_group.setLayout(counter_group_layout)
        counter_layout.addWidget(counter_group)
        
        # 计数设置组
        counting_group = self._create_settings_group("计数设置")
        counting_layout = QVBoxLayout()
        counting_layout.setSpacing(16)
        
        # 自动计数
        auto_count_check = QCheckBox("启用自动计数功能")
        auto_count_check.setChecked(True)
        auto_count_check.setStyleSheet("""
            QCheckBox {
                color: #e4e4e7;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid rgba(124, 58, 237, 0.3);
                border-radius: 4px;
                background-color: #252530;
                transition: all 0.2s ease;
            }
            QCheckBox::indicator:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
            QCheckBox::indicator:checked {
                background-color: #7c3aed;
                border-color: #7c3aed;
            }
        """)
        counting_layout.addWidget(auto_count_check)
        
        # 声音提示
        sound_check = QCheckBox("出闪时播放提示音")
        sound_check.setStyleSheet("""
            QCheckBox {
                color: #e4e4e7;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid rgba(124, 58, 237, 0.3);
                border-radius: 4px;
                background-color: #252530;
                transition: all 0.2s ease;
            }
            QCheckBox::indicator:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
            QCheckBox::indicator:checked {
                background-color: #7c3aed;
                border-color: #7c3aed;
            }
        """)
        counting_layout.addWidget(sound_check)
        
        counting_group.setLayout(counting_layout)
        counter_layout.addWidget(counting_group)
        
        counter_layout.addStretch()
        tab_widget.addTab(counter_tab, "计数器设置")
        
        main_layout.addWidget(tab_widget)
        
        # 底部按钮
        footer = QWidget()
        footer.setStyleSheet("""
            QWidget {
                background-color: #1a1a22;
                border-top: 1px solid rgba(124, 58, 237, 0.1);
                box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.2);
            }
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(32, 20, 32, 20)
        footer_layout.setSpacing(16)
        footer_layout.addStretch()
        
        reset_btn = QPushButton("恢复默认")
        reset_btn.setObjectName("customPokemonBtn")
        reset_btn.setFixedHeight(40)
        reset_btn.setMinimumWidth(110)
        reset_btn.setStyleSheet("""
            QPushButton#customPokemonBtn {
                background-color: #252530;
                color: #e4e4e7;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 8px;
                font-size: 14px;
                padding: 0 20px;
                transition: all 0.2s ease;
            }
            QPushButton#customPokemonBtn:hover {
                background-color: #2a2a35;
                border: 1px solid rgba(124, 58, 237, 0.5);
                transform: translateY(-1px);
            }
            QPushButton#customPokemonBtn:pressed {
                transform: translateY(0);
            }
        """)
        footer_layout.addWidget(reset_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("customPokemonBtn")
        cancel_btn.setFixedHeight(40)
        cancel_btn.setMinimumWidth(110)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton#customPokemonBtn {
                background-color: #252530;
                color: #e4e4e7;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 8px;
                font-size: 14px;
                padding: 0 20px;
                transition: all 0.2s ease;
            }
            QPushButton#customPokemonBtn:hover {
                background-color: #2a2a35;
                border: 1px solid rgba(124, 58, 237, 0.5);
                transform: translateY(-1px);
            }
            QPushButton#customPokemonBtn:pressed {
                transform: translateY(0);
            }
        """)
        footer_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存设置")
        save_btn.setObjectName("customPokemonBtn")
        save_btn.setFixedHeight(40)
        save_btn.setMinimumWidth(110)
        save_btn.setStyleSheet("""
            QPushButton#customPokemonBtn {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c3aed, stop:1 #a855f7);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 20px;
                transition: all 0.2s ease;
            }
            QPushButton#customPokemonBtn:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9333ea, stop:1 #c084fc);
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
            }
            QPushButton#customPokemonBtn:pressed {
                transform: translateY(0);
                box-shadow: 0 2px 6px rgba(124, 58, 237, 0.4);
            }
        """)
        save_btn.clicked.connect(self.accept)
        footer_layout.addWidget(save_btn)
        
        main_layout.addWidget(footer)
    
    def _create_settings_group(self, title):
        """创建设置分组"""
        group = QGroupBox()
        group.setStyleSheet("""
            QGroupBox {
                background-color: #1e1e26;
                border: 1px solid rgba(124, 58, 237, 0.15);
                border-radius: 10px;
                margin-top: 16px;
                padding: 20px 24px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 12px;
                color: #a78bfa;
                font-size: 14px;
                font-weight: 600;
                background-color: #1e1e26;
                border-radius: 4px;
            }
        """)
        return group
