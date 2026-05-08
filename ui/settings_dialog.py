from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QWidget, QScrollArea, QGroupBox, QCheckBox, QSpinBox, 
    QDoubleSpinBox, QFormLayout, QTabWidget, QLineEdit
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QPalette, QColor


class SettingsDialog(QDialog):
    """设置对话框 - 现代美观风格"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("助手设置")
        self.setModal(True)
        self.setFixedSize(700, 600)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 主容器
        main_container = QWidget()
        main_container.setStyleSheet("""
            QWidget {
                background-color: #121212;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            }
        """)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(main_container)
        
        # 内部布局
        inner_layout = QVBoxLayout(main_container)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)
        
        # 对话框头部
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #1a1a22;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                border-bottom: 1px solid rgba(124, 58, 237, 0.2);
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(30, 20, 30, 20)
        
        title = QLabel("助手设置")
        title.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: 0.5px;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet("""
            QPushButton {
                color: #94a3b8;
                background: transparent;
                border: none;
                font-size: 24px;
                border-radius: 16px;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            QPushButton:hover {
                color: #ffffff;
                background-color: rgba(239, 68, 68, 0.1);
                transform: scale(1.05);
            }
            QPushButton:pressed {
                background-color: rgba(239, 68, 68, 0.2);
                transform: scale(0.95);
            }
        """)
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)
        
        inner_layout.addWidget(header)
        
        # 标签页容器
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget {
                background-color: #121212;
            }
            QTabBar {
                background-color: #121212;
                padding: 0 30px;
                height: 50px;
            }
            QTabBar::tab {
                color: #94a3b8;
                background: transparent;
                padding: 0 24px;
                margin-right: 8px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            QTabBar::tab:hover {
                color: #e2e8f0;
                background-color: rgba(124, 58, 237, 0.1);
            }
            QTabBar::tab:selected {
                color: #ffffff;
                background-color: rgba(124, 58, 237, 0.2);
            }
            QTabWidget::pane {
                border: none;
                background-color: #121212;
            }
        """)
        
        # 通用设置标签
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_layout.setContentsMargins(30, 30, 30, 30)
        general_layout.setSpacing(24)
        
        # 通用设置分组
        general_group = self._create_settings_group("通用设置")
        general_group_layout = QVBoxLayout()
        general_group_layout.setSpacing(16)
        
        # 开机自启
        auto_start_check = QCheckBox("开机自动启动")
        auto_start_check.setStyleSheet(self._get_checkbox_style())
        general_group_layout.addWidget(auto_start_check)
        
        # 最小化到托盘
        minimize_to_tray = QCheckBox("关闭时最小化到系统托盘")
        minimize_to_tray.setStyleSheet(self._get_checkbox_style())
        general_group_layout.addWidget(minimize_to_tray)
        
        general_group.setLayout(general_group_layout)
        general_layout.addWidget(general_group)
        
        # 外观设置分组
        appearance_group = self._create_settings_group("外观设置")
        appearance_layout = QVBoxLayout()
        appearance_layout.setSpacing(16)
        
        # 深色模式
        dark_mode_check = QCheckBox("使用深色模式")
        dark_mode_check.setChecked(True)
        dark_mode_check.setStyleSheet(self._get_checkbox_style())
        appearance_layout.addWidget(dark_mode_check)
        
        appearance_group.setLayout(appearance_layout)
        general_layout.addWidget(appearance_group)
        
        general_layout.addStretch()
        tab_widget.addTab(general_tab, "通用")
        
        # 识别设置标签
        ocr_tab = QWidget()
        ocr_layout = QVBoxLayout(ocr_tab)
        ocr_layout.setContentsMargins(30, 30, 30, 30)
        ocr_layout.setSpacing(24)
        
        # 图像识别设置分组
        ocr_group = self._create_settings_group("图像识别设置")
        ocr_group_layout = QFormLayout()
        ocr_group_layout.setSpacing(20)
        ocr_group_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        # 识别间隔
        interval_spin = QSpinBox()
        interval_spin.setRange(100, 5000)
        interval_spin.setValue(500)
        interval_spin.setSuffix(" ms")
        interval_spin.setStyleSheet(self._get_spinbox_style())
        ocr_group_layout.addRow("识别间隔：", interval_spin)
        
        # 置信度阈值
        confidence_spin = QDoubleSpinBox()
        confidence_spin.setRange(0.5, 1.0)
        confidence_spin.setValue(0.7)
        confidence_spin.setSingleStep(0.05)
        confidence_spin.setStyleSheet(self._get_spinbox_style())
        ocr_group_layout.addRow("识别置信度：", confidence_spin)
        
        ocr_group.setLayout(ocr_group_layout)
        ocr_layout.addWidget(ocr_group)
        
        ocr_layout.addStretch()
        tab_widget.addTab(ocr_tab, "识别")
        
        # 计数器设置标签
        counter_tab = QWidget()
        counter_layout = QVBoxLayout(counter_tab)
        counter_layout.setContentsMargins(30, 30, 30, 30)
        counter_layout.setSpacing(24)
        
        # 计数器默认设置分组
        counter_group = self._create_settings_group("计数器默认设置")
        counter_group_layout = QFormLayout()
        counter_group_layout.setSpacing(20)
        counter_group_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        # 默认保底次数
        default_target = QSpinBox()
        default_target.setRange(10, 999)
        default_target.setValue(80)
        default_target.setStyleSheet(self._get_spinbox_style())
        counter_group_layout.addRow("默认保底次数：", default_target)
        
        # 基础概率
        base_prob = QDoubleSpinBox()
        base_prob.setRange(0.1, 10.0)
        base_prob.setValue(1.8)
        base_prob.setSingleStep(0.1)
        base_prob.setSuffix(" %")
        base_prob.setStyleSheet(self._get_spinbox_style())
        counter_group_layout.addRow("基础异色概率：", base_prob)
        
        counter_group.setLayout(counter_group_layout)
        counter_layout.addWidget(counter_group)
        
        counter_layout.addStretch()
        tab_widget.addTab(counter_tab, "计数器")
        
        # 框选设置标签
        roi_tab = QWidget()
        roi_layout = QVBoxLayout(roi_tab)
        roi_layout.setContentsMargins(30, 30, 30, 30)
        roi_layout.setSpacing(24)
        
        # 框选区域设置分组
        roi_group = self._create_settings_group("识别区域设置")
        roi_group_layout = QVBoxLayout()
        roi_group_layout.setSpacing(16)
        
        # 说明文字
        info_label = QLabel("通过框选指定识别区域，可解决不同分辨率下的识别问题")
        info_label.setStyleSheet("color: #94a3b8; font-size: 13px; padding: 8px 0;")
        info_label.setWordWrap(True)
        roi_group_layout.addWidget(info_label)
        
        # 框选按钮
        roi_select_btn = QPushButton("📸 开始框选识别区域")
        roi_select_btn.setFixedHeight(50)
        roi_select_btn.setCursor(Qt.PointingHandCursor)
        roi_select_btn.setStyleSheet("""
            QPushButton {
                background-color: #7c3aed;
                color: #ffffff;
                border: 2px solid #a855f7;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 600;
                padding: 0 24px;
            }
            QPushButton:hover {
                background-color: #6d28d9;
                border-color: #c084fc;
            }
            QPushButton:pressed {
                background-color: #5b21b6;
            }
        """)
        roi_select_btn.clicked.connect(self.on_roi_select)
        roi_group_layout.addWidget(roi_select_btn)
        
        # 当前框选区域显示
        current_roi_label = QLabel("当前未设置框选区域")
        current_roi_label.setStyleSheet("color: #e2e8f0; font-size: 13px; padding: 12px; background-color: #252530; border-radius: 6px;")
        roi_group_layout.addWidget(current_roi_label)
        
        roi_group.setLayout(roi_group_layout)
        roi_layout.addWidget(roi_group)
        
        roi_layout.addStretch()
        tab_widget.addTab(roi_tab, "框选")
        
        inner_layout.addWidget(tab_widget)
        
        # 底部按钮
        footer = QWidget()
        footer.setStyleSheet("""
            QWidget {
                background-color: #1a1a22;
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
                border-top: 1px solid rgba(124, 58, 237, 0.2);
            }
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(30, 24, 30, 24)
        footer_layout.setSpacing(16)
        footer_layout.addStretch()
        
        reset_btn = QPushButton("恢复默认")
        reset_btn.setObjectName("secondaryButton")
        reset_btn.setFixedHeight(44)
        reset_btn.setMinimumWidth(120)
        reset_btn.setStyleSheet(self._get_secondary_button_style())
        footer_layout.addWidget(reset_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryButton")
        cancel_btn.setFixedHeight(44)
        cancel_btn.setMinimumWidth(120)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(self._get_secondary_button_style())
        footer_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存设置")
        save_btn.setObjectName("primaryButton")
        save_btn.setFixedHeight(44)
        save_btn.setMinimumWidth(120)
        save_btn.setStyleSheet(self._get_primary_button_style())
        save_btn.clicked.connect(self.accept)
        footer_layout.addWidget(save_btn)
        
        # 框选识别按钮
        pollution_btn = QPushButton("框选识别")
        pollution_btn.setObjectName("pollutionButton")
        pollution_btn.setFixedHeight(44)
        pollution_btn.setMinimumWidth(120)
        pollution_btn.setStyleSheet("""
            QPushButton#pollutionButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #059669, stop:1 #10b981);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 24px;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3);
            }
            QPushButton#pollutionButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #047857, stop:1 #059669);
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(5, 150, 105, 0.4);
            }
            QPushButton#pollutionButton:pressed {
                transform: translateY(0);
                box-shadow: 0 3px 8px rgba(5, 150, 105, 0.5);
            }
        """)
        pollution_btn.clicked.connect(self.on_pollution_select)
        footer_layout.addWidget(pollution_btn)
        
        inner_layout.addWidget(footer)
        
        # 添加动画效果
        self._add_animations()
    
    def _create_settings_group(self, title):
        """创建设置分组"""
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                background-color: #1e1e26;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 12px;
                margin-top: 8px;
                padding: 24px 28px;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            QGroupBox:hover {
                border-color: rgba(124, 58, 237, 0.4);
                box-shadow: 0 6px 20px rgba(124, 58, 237, 0.1);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                top: -10px;
                padding: 0 16px;
                color: #a78bfa;
                font-size: 14px;
                font-weight: 600;
                background-color: #1e1e26;
                border-radius: 6px;
            }
        """)
        return group
    
    def _get_checkbox_style(self):
        """获取复选框样式"""
        return """
            QCheckBox {
                color: #e2e8f0;
                font-size: 14px;
                spacing: 12px;
                padding: 8px 0;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid rgba(124, 58, 237, 0.4);
                border-radius: 5px;
                background-color: #252530;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            QCheckBox::indicator:hover {
                border-color: rgba(124, 58, 237, 0.7);
                transform: scale(1.05);
            }
            QCheckBox::indicator:checked {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c3aed, stop:1 #a855f7);
                border-color: #7c3aed;
            }
            QCheckBox::indicator:checked:hover {
                transform: scale(1.1);
            }
        """
    
    def _get_spinbox_style(self):
        """获取 spinbox 样式"""
        return """
            QSpinBox, QDoubleSpinBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 8px;
                padding: 10px 16px;
                color: #e2e8f0;
                font-size: 14px;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            QSpinBox:hover, QDoubleSpinBox:hover {
                border-color: rgba(124, 58, 237, 0.6);
                background-color: #2a2a35;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #7c3aed;
                background-color: #2a2a35;
                box-shadow: 0 0 0 4px rgba(124, 58, 237, 0.15);
            }
            QSpinBox::up-button,
            QSpinBox::down-button,
            QDoubleSpinBox::up-button,
            QDoubleSpinBox::down-button {
                width: 24px;
                background-color: rgba(124, 58, 237, 0.1);
                border-radius: 4px;
                transition: all 0.2s ease;
            }
            QSpinBox::up-button:hover,
            QSpinBox::down-button:hover,
            QDoubleSpinBox::up-button:hover,
            QDoubleSpinBox::down-button:hover {
                background-color: rgba(124, 58, 237, 0.2);
            }
        """
    
    def _get_primary_button_style(self):
        """获取主要按钮样式"""
        return """
            QPushButton#primaryButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c3aed, stop:1 #a855f7);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 24px;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
            }
            QPushButton#primaryButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9333ea, stop:1 #c084fc);
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(124, 58, 237, 0.4);
            }
            QPushButton#primaryButton:pressed {
                transform: translateY(0);
                box-shadow: 0 3px 8px rgba(124, 58, 237, 0.5);
            }
        """
    
    def _get_secondary_button_style(self):
        """获取次要按钮样式"""
        return """
            QPushButton#secondaryButton {
                background-color: #252530;
                color: #e2e8f0;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 10px;
                font-size: 14px;
                font-weight: 500;
                padding: 0 24px;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            QPushButton#secondaryButton:hover {
                background-color: #2a2a35;
                border-color: rgba(124, 58, 237, 0.6);
                transform: translateY(-2px);
            }
            QPushButton#secondaryButton:pressed {
                transform: translateY(0);
            }
        """
    
    def _add_animations(self):
        """添加动画效果"""
        # 窗口显示动画
        self.setWindowOpacity(0)
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于拖动窗口"""
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 用于拖动窗口"""
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()
    
    def on_roi_select(self):
        """框选识别区域"""
        from core.screen_selector import ScreenSelector
        from PySide6.QtWidgets import QApplication
        
        self.hide()
        
        app = QApplication.instance()
        selector = ScreenSelector()
        
        def on_region_selected(x, y, w, h):
            print(f"✅ 已保存框选区域: x={x}, y={y}, w={w}, h={h}")
        
        def on_cancelled():
            print("❌ 框选已取消")
        
        selector.region_selected.connect(on_region_selected)
        selector.selection_cancelled.connect(on_cancelled)
        selector.show()
        
        while selector.isVisible():
            app.processEvents()
        
        self.show()
    
    def on_pollution_select(self):
        """框选识别污染区域"""
        from core.pollution_recognition import PollutionSelector
        from PySide6.QtWidgets import QApplication
        
        self.hide()
        
        app = QApplication.instance()
        selector = PollutionSelector()
        
        def on_roi_selected(x, y, w, h):
            from core.pollution_recognition import PollutionRecognitionWorker
            
            worker = PollutionRecognitionWorker()
            worker.set_roi(x, y, w, h)
            
            def on_result(result):
                print(f"污染识别结果: {result}")
            
            def on_status(status):
                print(f"状态: {status}")
            
            worker.recognition_result.connect(on_result)
            worker.status_changed.connect(on_status)
            worker.start()
        
        def on_cancelled():
            print("框选已取消")
        
        selector.roi_selected.connect(on_roi_selected)
        selector.selection_cancelled.connect(on_cancelled)
        selector.showFullScreen()
        
        while selector.isVisible():
            app.processEvents()
        
        self.show()