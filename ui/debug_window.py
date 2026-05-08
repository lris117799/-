# ui/debug_window.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTextEdit, QPushButton, 
                                QHBoxLayout, QLabel)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from core.logger import logger


class DebugWindow(QDialog):
    """调试输出窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("调试输出")
        self.setMinimumSize(800, 600)
        
        # 设置窗口标志：保持在最前，独立窗口
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # 标题栏
        header_layout = QHBoxLayout()
        title_label = QLabel("🔍 调试日志")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #60a5fa;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # 清空按钮
        clear_btn = QPushButton("清空")
        clear_btn.setFixedSize(60, 28)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #9ca3af;
                border: 1px solid #4b5563;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4b5563;
                color: #ffffff;
            }
        """)
        clear_btn.clicked.connect(self.clear_log)
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1f2937;
                color: #d1d5db;
                border: 1px solid #374151;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.log_text)
        
        # 状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)
        
        # 注册日志回调
        logger.register_callback(self.on_new_log)
        
        # 自动滚动标志（用户手动滚动时暂停自动滚动）
        self.auto_scroll_enabled = True
        self.user_scrolling = False
        
        # 监听滚动条变化
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.valueChanged.connect(self.on_scroll_changed)
        
        # 加载历史日志
        self.load_history()
    
    def on_new_log(self, log_line):
        """接收新日志"""
        self.log_text.append(log_line)
        self.status_label.setText(f"共 {len(logger.get_buffer())} 条日志")
        
        # 如果启用了自动滚动，则滚动到底部
        if self.auto_scroll_enabled:
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def on_scroll_changed(self, value):
        """滚动条值变化时触发"""
        scrollbar = self.log_text.verticalScrollBar()
        max_value = scrollbar.maximum()
        
        # 如果用户滚动到了底部，恢复自动滚动
        if value >= max_value - 5:  # 允许5像素误差
            self.auto_scroll_enabled = True
            self.user_scrolling = False
        else:
            # 用户向上滚动，暂停自动滚动
            self.auto_scroll_enabled = False
            self.user_scrolling = True
    
    def load_history(self):
        """加载历史日志"""
        history = logger.get_buffer()
        if history:
            self.log_text.setPlainText('\n'.join(history))
    
    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        logger.clear_buffer()
        self.status_label.setText("已清空")
    
    def closeEvent(self, event):
        """关闭窗口时注销回调"""
        logger.unregister_callback(self.on_new_log)
        super().closeEvent(event)
