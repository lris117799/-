from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QScrollArea, QGroupBox, QCheckBox, QSpinBox,
    QDoubleSpinBox, QFormLayout, QTabWidget, QLineEdit, QComboBox,
    QMessageBox
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QThread, Signal
from PySide6.QtGui import QIcon, QPalette, QColor


class _CheckUpdateWorker(QThread):
    """后台检查更新线程"""
    finished_signal = Signal(object)  # update_info dict or None

    def run(self):
        try:
            from core.update_manager import check_for_update
            info = check_for_update(timeout=15)
        except Exception:
            info = None
        self.finished_signal.emit(info)


class _ShowUpdateDialog(QThread):
    """延迟显示更新弹窗（避免在设置对话框关闭前弹出）"""
    show_signal = Signal(dict)

    def __init__(self, info: dict, delay_ms: int = 200):
        super().__init__()
        self._info = info
        self._delay = delay_ms

    def run(self):
        from PySide6.QtCore import QThread as _QThread
        _QThread.msleep(self._delay)
        self.show_signal.emit(self._info)


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
            }
            QPushButton:hover {
                color: #ffffff;
                background-color: rgba(239, 68, 68, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(239, 68, 68, 0.2);
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
        ocr_group_layout.addRow("nl识别置信度：", confidence_spin)

        # 识别比例模式
        scale_mode_combo = QComboBox()
        scale_mode_combo.addItems(["自动检测", "手动设置"])
        scale_mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 8px;
                padding: 10px 16px;
                color: #e2e8f0;
                font-size: 14px;
            }
            QComboBox:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #94a3b8;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.3);
                color: #e2e8f0;
                selection-background-color: rgba(124, 58, 237, 0.3);
                padding: 8px;
            }
        """)
        ocr_group_layout.addRow("识别比例模式：", scale_mode_combo)

        # 识别比例（手动设置时启用）
        recognition_scale_combo = QComboBox()
        recognition_scale_combo.addItems(["100%", "125%", "150%"])
        recognition_scale_combo.setCurrentText("125%")
        recognition_scale_combo.setStyleSheet("""
            QComboBox {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 8px;
                padding: 10px 16px;
                color: #e2e8f0;
                font-size: 14px;
            }
            QComboBox:hover {
                border-color: rgba(124, 58, 237, 0.6);
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #94a3b8;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #252530;
                border: 1px solid rgba(124, 58, 237, 0.3);
                color: #e2e8f0;
                selection-background-color: rgba(124, 58, 237, 0.3);
                padding: 8px;
            }
        """)
        ocr_group_layout.addRow("识别比例：", recognition_scale_combo)

        # 地图更新间隔
        self.map_update_interval_spin = QSpinBox()
        self.map_update_interval_spin.setRange(1, 10)
        self.map_update_interval_spin.setValue(3)
        self.map_update_interval_spin.setSuffix(" 帧")
        self.map_update_interval_spin.setStyleSheet(self._get_spinbox_style())
        ocr_group_layout.addRow("地图更新间隔：", self.map_update_interval_spin)

        # 资源点大小
        self.resource_icon_size_spin = QSpinBox()
        self.resource_icon_size_spin.setRange(8, 64)
        self.resource_icon_size_spin.setValue(24)
        self.resource_icon_size_spin.setSingleStep(2)
        self.resource_icon_size_spin.setSuffix(" px")
        self.resource_icon_size_spin.setStyleSheet(self._get_spinbox_style())
        ocr_group_layout.addRow("资源点大小：", self.resource_icon_size_spin)

        # 真实指针开关
        self.use_real_pointer_check = QCheckBox("启用游戏真实指针（关闭后使用绿色方向指针）")
        self.use_real_pointer_check.setChecked(True)
        self.use_real_pointer_check.setStyleSheet(self._get_checkbox_style())
        ocr_group_layout.addRow("", self.use_real_pointer_check)
        
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

        # 版本信息区
        version_bar = QWidget()
        version_bar.setStyleSheet("""
            QWidget {
                background-color: #1a1a22;
                border-top: 1px solid rgba(124, 58, 237, 0.15);
            }
        """)
        vb_layout = QHBoxLayout(version_bar)
        vb_layout.setContentsMargins(30, 12, 30, 12)
        vb_layout.setSpacing(10)

        # 当前版本号
        try:
            from core.update_manager import CURRENT_VERSION
        except Exception:
            CURRENT_VERSION = "4.6.12"
        version_label = QLabel(f"当前版本：v{CURRENT_VERSION}")
        version_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        vb_layout.addWidget(version_label)

        vb_layout.addStretch()

        # 最新版本号（点击检查更新后显示）
        self.latest_version_label = QLabel("")
        self.latest_version_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        vb_layout.addWidget(self.latest_version_label)

        # 检查更新按钮
        check_update_btn = QPushButton("检查更新")
        check_update_btn.setObjectName("checkUpdateButton")
        check_update_btn.setFixedHeight(32)
        check_update_btn.setMinimumWidth(100)
        check_update_btn.setCursor(Qt.PointingHandCursor)
        check_update_btn.setStyleSheet("""
            QPushButton#checkUpdateButton {
                background-color: #252530;
                color: #e2e8f0;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 8px;
                font-size: 12px;
                font-weight: 500;
                padding: 0 16px;
            }
            QPushButton#checkUpdateButton:hover {
                background-color: #2a2a35;
                border-color: rgba(124, 58, 237, 0.6);
            }
            QPushButton#checkUpdateButton:disabled {
                color: #64748b;
                background-color: #1e1e26;
            }
        """)
        check_update_btn.clicked.connect(self._on_check_update)
        vb_layout.addWidget(check_update_btn)
        self._check_update_btn = check_update_btn

        inner_layout.addWidget(version_bar)

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
            }
            QPushButton#pollutionButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #047857, stop:1 #059669);
            }
            QPushButton#pollutionButton:pressed {
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
            }
            QGroupBox:hover {
                border-color: rgba(124, 58, 237, 0.4);
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
            }
            QCheckBox::indicator:hover {
                border-color: rgba(124, 58, 237, 0.7);
            }
            QCheckBox::indicator:checked {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c3aed, stop:1 #a855f7);
                border-color: #7c3aed;
            }
            QCheckBox::indicator:checked:hover {
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
            }
            QSpinBox:hover, QDoubleSpinBox:hover {
                border-color: rgba(124, 58, 237, 0.6);
                background-color: #2a2a35;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #7c3aed;
                background-color: #2a2a35;
            }
            QSpinBox::up-button,
            QSpinBox::down-button,
            QDoubleSpinBox::up-button,
            QDoubleSpinBox::down-button {
                width: 24px;
                background-color: rgba(124, 58, 237, 0.1);
                border-radius: 4px;
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
            }
            QPushButton#primaryButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9333ea, stop:1 #c084fc);
            }
            QPushButton#primaryButton:pressed {
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
            }
            QPushButton#secondaryButton:hover {
                background-color: #2a2a35;
                border-color: rgba(124, 58, 237, 0.6);
            }
            QPushButton#secondaryButton:pressed {
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
    
    def _on_check_update(self):
        """检查更新"""
        # 禁用按钮，显示检查中
        self._check_update_btn.setEnabled(False)
        self._check_update_btn.setText("检查中...")
        self.latest_version_label.setText("正在检查更新...")
        self.latest_version_label.setStyleSheet("color: #94a3b8; font-size: 12px;")

        # 启动后台检查线程
        self._check_worker = _CheckUpdateWorker()
        self._check_worker.finished_signal.connect(self._on_check_update_done)
        self._check_worker.start()

    def _on_check_update_done(self, info):
        """检查更新完成"""
        self._check_update_btn.setEnabled(True)
        self._check_update_btn.setText("检查更新")

        if info is None:
            # 无新版本或检查失败
            try:
                from core.update_manager import CURRENT_VERSION
            except Exception:
                CURRENT_VERSION = "4.6.12"
            self.latest_version_label.setText(f"已是最新版本 v{CURRENT_VERSION}")
            self.latest_version_label.setStyleSheet("color: #10b981; font-size: 12px;")
            return

        # 有新版本，显示最新版本号
        latest = info.get("latest_version", "")
        self.latest_version_label.setText(f"检测到新版本：v{latest}")
        self.latest_version_label.setStyleSheet("color: #f59e0b; font-size: 12px;")

        # 弹出更新对话框（关闭设置对话框后弹出，避免层级冲突）
        self._pending_update_info = info
        self.accept()  # 关闭设置对话框
        # 用延迟线程在主窗口上显示更新弹窗
        from PySide6.QtWidgets import QApplication
        parent_window = QApplication.activeWindow()
        # 保存到属性，等待关闭后再弹
        QTimer = None
        try:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(250, lambda: self._show_update_dialog(parent_window, info))
        except Exception:
            self._show_update_dialog(parent_window, info)

    def _show_update_dialog(self, parent_window, info):
        """显示更新弹窗"""
        try:
            from ui.update_dialog import UpdateDialog
            dlg = UpdateDialog(info, parent=parent_window)
            dlg.exec()
        except Exception as e:
            html_url = info.get("html_url", "") if info else ""
            latest = info.get("latest_version", "") if info else ""
            QMessageBox.warning(
                parent_window, "更新",
                f"检测到新版本 v{latest}，但更新弹窗加载失败：\n{e}\n\n"
                f"请前往 GitHub 手动下载：\n{html_url}\n"
                f"或加 QQ 群 1105048691 获取下载"
            )

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