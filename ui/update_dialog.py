# -*- coding: utf-8 -*-
"""
更新弹窗 UI

显示：
- 标题：检测到更新
- 当前版本 → 最新版本
- 更新日志（中央 QTextEdit，只读）
- 底部两个按钮：更新 / 下次再说
- 下载进度条（点击"更新"后显示）
"""
import os
import sys
import tempfile

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QProgressBar, QTextEdit, QFrame
)
from PySide6.QtGui import QPropertyAnimation, QEasingCurve


class _DownloadWorker(QThread):
    """后台下载线程"""
    progress = Signal(int, int)   # downloaded, total
    finished_signal = Signal(bool, str)  # success, msg

    def __init__(self, url: str, dest_path: str):
        super().__init__()
        self._url = url
        self._dest = dest_path

    def run(self):
        try:
            from core.update_manager import download_file
            ok = download_file(self._url, self._dest, progress_callback=self._on_progress)
            if ok:
                self.finished_signal.emit(True, self._dest)
            else:
                self.finished_signal.emit(False, "下载失败，请检查网络后重试")
        except Exception as e:
            self.finished_signal.emit(False, f"下载失败: {e}")

    def _on_progress(self, downloaded: int, total: int):
        self.progress.emit(downloaded, total)


class UpdateDialog(QDialog):
    """更新弹窗"""

    def __init__(self, update_info: dict, parent=None):
        """
        Args:
            update_info: check_for_update() 返回的 dict
        """
        super().__init__(parent)
        self._info = update_info
        self._download_worker = None
        self._downloaded_zip = ""

        self.setWindowTitle("检测到更新")
        self.setModal(True)
        self.setFixedSize(560, 520)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._build_ui()
        self._add_animation()

    # ────────── UI 构建 ──────────
    def _build_ui(self):
        # 主容器
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #121212;
                border-radius: 16px;
            }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 头部 ──
        header = QWidget()
        header.setStyleSheet("""
            QWidget {
                background-color: #1a1a22;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                border-bottom: 1px solid rgba(124, 58, 237, 0.2);
            }
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(28, 20, 28, 20)

        title = QLabel("✨ 检测到新版本")
        title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 700; letter-spacing: 0.5px;")
        h_layout.addWidget(title)
        h_layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                color: #94a3b8;
                background: transparent;
                border: none;
                font-size: 22px;
                border-radius: 15px;
            }
            QPushButton:hover {
                color: #ffffff;
                background-color: rgba(239, 68, 68, 0.15);
            }
        """)
        close_btn.clicked.connect(self.reject)
        h_layout.addWidget(close_btn)

        root.addWidget(header)

        # ── 内容区 ──
        body = QWidget()
        body.setStyleSheet("background-color: #121212;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(28, 24, 28, 16)
        body_layout.setSpacing(14)

        # 版本信息
        cur = self._info.get("current_version", "")
        latest = self._info.get("latest_version", "")

        ver_label = QLabel(f'<span style="color:#94a3b8;">当前版本：</span>'
                           f'<span style="color:#e2e8f0; font-weight:600;">v{cur}</span>'
                           f'   <span style="color:#7c3aed;">→</span>   '
                           f'<span style="color:#94a3b8;">最新版本：</span>'
                           f'<span style="color:#10b981; font-weight:700;">v{latest}</span>')
        ver_label.setTextFormat(Qt.RichText)
        ver_label.setStyleSheet("font-size: 14px; padding: 4px 0;")
        body_layout.addWidget(ver_label)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: rgba(124, 58, 237, 0.15); max-height: 1px;")
        body_layout.addWidget(sep)

        # 更新日志标题
        log_title = QLabel("更新日志")
        log_title.setStyleSheet("color: #a78bfa; font-size: 14px; font-weight: 600;")
        body_layout.addWidget(log_title)

        # 更新日志正文
        changelog = self._info.get("changelog", "") or "暂无更新日志"
        log_edit = QTextEdit()
        log_edit.setReadOnly(True)
        log_edit.setPlainText(changelog)
        log_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e26;
                border: 1px solid rgba(124, 58, 237, 0.2);
                border-radius: 10px;
                padding: 12px;
                color: #e2e8f0;
                font-size: 13px;
                line-height: 1.6;
            }
        """)
        body_layout.addWidget(log_edit, 1)

        # 进度条（默认隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e1e26;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 8px;
                height: 24px;
                color: #e2e8f0;
                font-size: 12px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c3aed, stop:1 #a855f7);
                border-radius: 7px;
            }
        """)
        body_layout.addWidget(self.progress_bar)

        # 状态文本
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        body_layout.addWidget(self.status_label)

        root.addWidget(body, 1)

        # ── 底部按钮 ──
        footer = QWidget()
        footer.setStyleSheet("""
            QWidget {
                background-color: #1a1a22;
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
                border-top: 1px solid rgba(124, 58, 237, 0.2);
            }
        """)
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(28, 16, 28, 20)
        f_layout.setSpacing(12)
        f_layout.addStretch()

        # 下次再说
        later_btn = QPushButton("下次再说")
        later_btn.setFixedHeight(40)
        later_btn.setMinimumWidth(110)
        later_btn.setCursor(Qt.PointingHandCursor)
        later_btn.setStyleSheet("""
            QPushButton {
                background-color: #252530;
                color: #e2e8f0;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 10px;
                font-size: 13px;
                font-weight: 500;
                padding: 0 22px;
            }
            QPushButton:hover {
                background-color: #2a2a35;
                border-color: rgba(124, 58, 237, 0.6);
            }
        """)
        later_btn.clicked.connect(self.reject)
        f_layout.addWidget(later_btn)

        # 立即更新
        self.update_btn = QPushButton("立即更新")
        self.update_btn.setFixedHeight(40)
        self.update_btn.setMinimumWidth(110)
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c3aed, stop:1 #a855f7);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 22px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9333ea, stop:1 #c084fc);
            }
            QPushButton:disabled {
                background-color: #4c4c5a;
                color: #94a3b8;
            }
        """)
        self.update_btn.clicked.connect(self._on_update_clicked)
        f_layout.addWidget(self.update_btn)

        root.addWidget(footer)

    def _add_animation(self):
        self.setWindowOpacity(0)
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(280)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        self._anim = anim  # 保持引用

    # ────────── 更新流程 ──────────
    def _on_update_clicked(self):
        url = self._info.get("download_url", "")
        if not url:
            # 没有可下载的 zip，提示用户手动下载
            html_url = self._info.get("html_url", "")
            self.status_label.setText(
                f"未找到可下载的更新包，请前往 GitHub 手动下载：{html_url}"
            )
            self.status_label.setStyleSheet("color: #f59e0b; font-size: 12px;")
            return

        # 切换为下载中状态
        self.update_btn.setEnabled(False)
        self.update_btn.setText("更新中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("准备下载...")
        self.status_label.setText("正在下载更新包，请稍候...")
        self.status_label.setStyleSheet("color: #94a3b8; font-size: 12px;")

        # 准备临时下载路径
        if not self._downloaded_zip:
            self._downloaded_zip = os.path.join(
                tempfile.gettempdir(), "klxy_update.zip"
            )
            # 删除旧文件
            try:
                if os.path.exists(self._downloaded_zip):
                    os.remove(self._downloaded_zip)
            except Exception:
                pass

        # 启动下载线程
        self._download_worker = _DownloadWorker(url, self._downloaded_zip)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.finished_signal.connect(self._on_download_finished)
        self._download_worker.start()

    def _on_download_progress(self, downloaded: int, total: int):
        if total <= 0:
            self.progress_bar.setFormat(f"已下载 {downloaded / 1024 / 1024:.1f} MB")
            self.progress_bar.setValue(0)
        else:
            pct = int(downloaded * 100 / total) if total else 0
            self.progress_bar.setValue(pct)
            mb_d = downloaded / 1024 / 1024
            mb_t = total / 1024 / 1024
            self.progress_bar.setFormat(f"{pct}%  ({mb_d:.1f} / {mb_t:.1f} MB)")

    def _on_download_finished(self, success: bool, msg: str):
        if not success:
            self.update_btn.setEnabled(True)
            self.update_btn.setText("立即更新")
            self.progress_bar.setFormat("下载失败")
            self.status_label.setText(msg)
            self.status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
            return

        # 下载完成，应用更新
        self.progress_bar.setFormat("正在应用更新...")
        self.status_label.setText("更新包已下载，正在应用更新...")
        self.status_label.setStyleSheet("color: #10b981; font-size: 12px;")

        try:
            from core.update_manager import apply_update
            ok = apply_update(self._downloaded_zip, restart=True)
        except Exception as e:
            ok = False
            msg = str(e)

        if ok:
            self.status_label.setText("更新已启动，程序即将退出...")
            # 等待 1.2 秒后退出程序
            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QApplication
            QTimer.singleShot(1200, lambda: QApplication.quit())
        else:
            self.update_btn.setEnabled(True)
            self.update_btn.setText("立即更新")
            self.progress_bar.setFormat("应用更新失败")
            self.status_label.setText(f"应用更新失败：{msg}")
            self.status_label.setStyleSheet("color: #ef4444; font-size: 12px;")

    # ────────── 窗口拖动 ──────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
