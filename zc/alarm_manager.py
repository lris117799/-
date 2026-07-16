"""
闹钟与日程管理模块
- 闹钟：指定时间 + 可选星期重复，到点冒泡 + 播放音乐
- 定时器：时分秒倒计时，支持多个同时运行、重置、编辑
- 日程：文字记录，可选星期，可关联闹钟/定时器
"""

import os
import json
import math
import time
import uuid
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QPushButton, QLabel, QMessageBox, QScrollArea, QFrame,
    QLineEdit, QTimeEdit, QSpinBox, QCheckBox, QFormLayout,
    QDialogButtonBox, QComboBox
)
from PySide6.QtCore import Qt, QTimer, QUrl, QTime, QRect
from PySide6.QtGui import QPainter, QColor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PET_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pet_data.json")
SOUND_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image", "yp", "ls", "ls.mp3")

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 全局播放器引用
_players = []


def _load_data():
    if os.path.exists(PET_DATA_FILE):
        try:
            with open(PET_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_data(data):
    try:
        with open(PET_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def play_alarm_sound():
    if not os.path.exists(SOUND_PATH):
        print(f"[闹钟] 音频文件不存在: {SOUND_PATH}")
        return
    
    print(f"[闹钟] 尝试播放音频: {SOUND_PATH}")
    
    # 方法1: QMediaPlayer（优先，FFmpeg支持更好）
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
        from PySide6.QtCore import QUrl
        
        app = QApplication.instance()
        if app is None:
            print("[闹钟] 警告: 没有 QApplication 实例，尝试创建...")
            app = QApplication([])
        
        player = QMediaPlayer()
        audio = QAudioOutput()
        audio.setVolume(1.0)
        player.setAudioOutput(audio)
        
        def on_error(err, s):
            print(f"[闹钟] QMediaPlayer 错误: {err}, {s}")
        
        def on_status_changed(status):
            status_names = {
                0: "UnknownMediaStatus", 1: "NoMedia", 2: "LoadingMedia",
                3: "LoadedMedia", 4: "StalledMedia", 5: "BufferingMedia",
                6: "BufferedMedia", 7: "EndOfMedia", 8: "InvalidMedia"
            }
            print(f"[闹钟] 媒体状态: {status_names.get(status, status)}")
        
        player.errorOccurred.connect(on_error)
        player.mediaStatusChanged.connect(on_status_changed)
        
        player.setSource(QUrl.fromLocalFile(SOUND_PATH))
        player.play()
        # 关键：同时保持 player 和 audio 的引用，防止被垃圾回收
        _players.append((player, audio))
        player.mediaStatusChanged.connect(lambda status, p=player: _cleanup_player(p, status))
        print("[闹钟] QMediaPlayer 播放已启动")
        return
    except Exception as e:
        print(f"[闹钟] QMediaPlayer 播放失败: {e}")
    
    # 方法2: Windows MCI 回退
    try:
        import ctypes
        ctypes.windll.winmm.mciSendStringW('close lkwg_alarm', None, 0, 0)
        ret = ctypes.windll.winmm.mciSendStringW(
            f'open "{SOUND_PATH}" alias lkwg_alarm', None, 0, 0)
        if ret == 0:
            ctypes.windll.winmm.mciSendStringW('play lkwg_alarm', None, 0, 0)
            print("[闹钟] MCI 播放已启动")
            return
        else:
            print(f"[闹钟] MCI 打开失败，返回值: {ret}")
    except Exception as e:
        print(f"[闹钟] MCI 播放失败: {e}")
    
    # 方法3: 使用 winsound 发出提示音（备用方案）
    try:
        import winsound
        winsound.Beep(1000, 500)
        print("[闹钟] 使用 winsound 发出提示音")
        return
    except Exception as e:
        print(f"[闹钟] winsound 失败: {e}")


def _cleanup_player(player, status):
    if status == QMediaPlayer.EndOfMedia:
        for item in _players[:]:
            p = item[0] if isinstance(item, tuple) else item
            if p is player:
                _players.remove(item)
                break
        player.deleteLater()


def check_alarms_and_timers(on_fire):
    data = _load_data()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_ts = time.time()
    wday = now.weekday()  # 0=周一 ... 6=周日
    changed = False

    for alarm in data.get("alarms", []):
        if not alarm.get("enabled", True):
            continue
        if alarm.get("last_fired_date") == today_str:
            continue
        if alarm.get("hour") != now.hour or alarm.get("minute") != now.minute:
            continue
        # 检查星期
        weekdays = alarm.get("weekdays", [])
        if weekdays and wday not in weekdays:
            continue
        on_fire(alarm.get("name", "闹钟"), "alarm")
        alarm["last_fired_date"] = today_str
        changed = True

    for timer in data.get("timers", []):
        if not timer.get("enabled", True):
            continue
        if timer.get("fired", False):
            continue
        if current_ts >= timer.get("end_time", 0):
            on_fire(timer.get("name", "定时器"), "timer")
            timer["fired"] = True
            changed = True

    if changed:
        _save_data(data)
    return changed


# ═══════════════════════════════════════════════════════════
# 开关组件
# ═══════════════════════════════════════════════════════════

class ToggleSwitch(QPushButton):
    """iOS风格开关 - 带滑块和平移动画"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.PointingHandCursor)

        self._offset = 2
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(16)
        self._animation_timer.timeout.connect(self._update_animation)

        self._is_checked = False

    def isChecked(self):
        return self._is_checked

    def setChecked(self, checked):
        self._is_checked = checked
        super().setChecked(checked)  # 同步 QPushButton 内部状态
        self._start_animation()

    def _start_animation(self):
        if not self._animation_timer.isActive():
            self._animation_timer.start()

    def _update_animation(self):
        target = self.width() - self.height() + 2 if self.isChecked() else 2
        diff = target - self._offset
        if abs(diff) < 0.5:
            self._offset = target
            self._animation_timer.stop()
        else:
            self._offset += diff * 0.2
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = rect.height() / 2

        bg_color = QColor(34, 197, 94) if self.isChecked() else QColor(63, 63, 70)
        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, radius, radius)

        slider_rect = QRect(int(self._offset), 2, self.height() - 4, self.height() - 4)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(slider_rect)


# ═══════════════════════════════════════════════════════════
# 样式
# ═══════════════════════════════════════════════════════════

COMMON_STYLE = """
    QDialog {
        background-color: #1e1e2e;
        border: 2px solid rgba(124, 58, 237, 0.4);
        border-radius: 12px;
        color: #e2e8f0;
    }
    QScrollArea {
        border: none;
        background: transparent;
    }
    QPushButton {
        background-color: rgba(124, 58, 237, 0.3);
        border: 1px solid rgba(124, 58, 237, 0.5);
        border-radius: 6px;
        padding: 5px 12px;
        color: #e2e8f0;
        font-size: 12px;
        font-family: "Microsoft YaHei";
    }
    QPushButton:hover {
        background-color: rgba(124, 58, 237, 0.5);
    }
    QPushButton#btn_danger {
        background-color: rgba(220, 38, 38, 0.3);
        border-color: rgba(220, 38, 38, 0.5);
    }
    QPushButton#btn_danger:hover {
        background-color: rgba(220, 38, 38, 0.5);
    }
    QPushButton#btn_reset {
        background-color: rgba(34, 197, 94, 0.3);
        border-color: rgba(34, 197, 94, 0.5);
    }
    QPushButton#btn_reset:hover {
        background-color: rgba(34, 197, 94, 0.5);
    }
    QPushButton#btn_add {
        background-color: rgba(124, 58, 237, 0.4);
        padding: 8px 20px;
        font-size: 13px;
        font-weight: bold;
    }
    QLineEdit, QTimeEdit, QSpinBox, QComboBox {
        background-color: #2a2a3a;
        border: 1px solid rgba(124, 58, 237, 0.3);
        border-radius: 6px;
        padding: 6px 10px;
        color: #e2e8f0;
        font-size: 13px;
        font-family: "Microsoft YaHei";
    }
    QTabWidget::pane {
        border: 1px solid rgba(124, 58, 237, 0.2);
        border-radius: 8px;
        background-color: #1e1e2e;
    }
    QTabBar::tab {
        background-color: #2a2a3a;
        border: 1px solid rgba(124, 58, 237, 0.2);
        border-radius: 6px;
        padding: 8px 20px;
        margin: 2px;
        color: #aab;
        font-size: 13px;
        font-family: "Microsoft YaHei";
    }
    QTabBar::tab:selected {
        background-color: rgba(124, 58, 237, 0.3);
        color: #e2e8f0;
    }
    QLabel {
        color: #e2e8f0;
        font-size: 13px;
        font-family: "Microsoft YaHei";
    }
    QCheckBox {
        color: #e2e8f0;
        font-size: 12px;
        font-family: "Microsoft YaHei";
    }
    QFrame#item_row {
        background-color: rgba(42, 42, 58, 0.6);
        border: 1px solid rgba(124, 58, 237, 0.15);
        border-radius: 8px;
        padding: 2px;
    }
    QFrame#item_row:hover {
        border-color: rgba(124, 58, 237, 0.35);
    }
"""


# ═══════════════════════════════════════════════════════════
# 编辑对话框
# ═══════════════════════════════════════════════════════════

class _AlarmEditDialog(QDialog):
    """闹钟编辑对话框 — 名称 + 时间选择器（输入+滚动双模式）+ 星期 + 距离现在的剩余时间"""

    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("编辑闹钟" if data else "添加闹钟")
        self.setMinimumWidth(400)
        self.setStyleSheet(COMMON_STYLE)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("如：取蛋 浇水")
        self._name_edit.setContextMenuPolicy(Qt.NoContextMenu)
        layout.addRow("名称：", self._name_edit)

        # ── 方式一：直接输入 ──
        self._time_edit = QTimeEdit()
        self._time_edit.setDisplayFormat("HH : mm")
        self._time_edit.setTime(QTime(8, 0))
        self._time_edit.setMinimumHeight(32)
        self._time_edit.setContextMenuPolicy(Qt.NoContextMenu)
        self._time_edit.timeChanged.connect(self._on_timeedit_changed)
        layout.addRow("时间输入：", self._time_edit)

        # ── 距离现在的剩余时间 ──
        self._time_until_label = QLabel()
        self._time_until_label.setStyleSheet("color: #7dd3fc; font-size: 13px; font-weight: bold;")
        layout.addRow("", self._time_until_label)

        # ── 方式二：滚动选择（手机闹钟风格）──
        scroll_label = QLabel("快速滚动：")
        scroll_layout = QHBoxLayout()
        scroll_layout.setSpacing(8)

        self._hour_combo = QComboBox()
        self._hour_combo.setContextMenuPolicy(Qt.NoContextMenu)
        for h in range(24):
            self._hour_combo.addItem(f"{h:02d} 时", h)
        self._hour_combo.setCurrentIndex(8)
        self._hour_combo.setMinimumWidth(80)
        self._hour_combo.currentIndexChanged.connect(self._on_combo_changed)

        self._min_combo = QComboBox()
        self._min_combo.setContextMenuPolicy(Qt.NoContextMenu)
        for m in range(60):
            self._min_combo.addItem(f"{m:02d} 分", m)
        self._min_combo.setCurrentIndex(0)
        self._min_combo.setMinimumWidth(80)
        self._min_combo.currentIndexChanged.connect(self._on_combo_changed)

        scroll_layout.addWidget(self._hour_combo)
        scroll_layout.addWidget(self._min_combo)
        scroll_layout.addStretch()
        layout.addRow(scroll_label, scroll_layout)

        self._syncing = False  # 防止双向同步时死循环

        # 星期选择
        wday_label = QLabel("重复：")
        wday_layout = QHBoxLayout()
        wday_layout.setSpacing(4)
        self._wday_checks = []
        for i, name in enumerate(WEEKDAY_NAMES):
            cb = QCheckBox(name)
            cb.setChecked(True)  # 默认每天
            wday_layout.addWidget(cb)
            self._wday_checks.append(cb)
        wday_layout.addStretch()
        layout.addRow(wday_label, wday_layout)

        # 快捷按钮
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(6)
        btn_all = QPushButton("每天")
        btn_all.clicked.connect(lambda: self._set_weekdays(range(7)))
        btn_workday = QPushButton("工作日")
        btn_workday.clicked.connect(lambda: self._set_weekdays(range(5)))
        btn_weekend = QPushButton("周末")
        btn_weekend.clicked.connect(lambda: self._set_weekdays([5, 6]))
        quick_layout.addWidget(btn_all)
        quick_layout.addWidget(btn_workday)
        quick_layout.addWidget(btn_weekend)
        quick_layout.addStretch()
        layout.addRow("", quick_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        if data:
            self._name_edit.setText(data.get("name", ""))
            h = data.get("hour", 8)
            m = data.get("minute", 0)
            self._time_edit.setTime(QTime(h, m))
            self._syncing = True
            self._hour_combo.setCurrentIndex(h)
            self._min_combo.setCurrentIndex(m)
            self._syncing = False
            wdays = set(data.get("weekdays", list(range(7))))
            for i, cb in enumerate(self._wday_checks):
                cb.setChecked(i in wdays)

        self._update_time_until()

    def _update_time_until(self):
        """更新距离闹钟时间的剩余时间显示"""
        h = self._hour_combo.currentIndex()
        m = self._min_combo.currentIndex()
        now = datetime.now()
        alarm_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if alarm_time <= now:
            alarm_time = alarm_time.replace(day=now.day + 1)
        diff = alarm_time - now
        total_seconds = int(diff.total_seconds())
        total_minutes = math.ceil(total_seconds / 60)  # 向上取整，26:30→27:00 显示1分钟
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if hours > 0:
            self._time_until_label.setText(f"\u23f0 还有 {hours} 小时 {minutes} 分钟后响铃")
        else:
            self._time_until_label.setText(f"\u23f0 还有 {minutes} 分钟后响铃")

    def _on_timeedit_changed(self, t):
        """QTimeEdit 变化 → 同步到滚动选择器"""
        if self._syncing:
            return
        self._syncing = True
        self._hour_combo.setCurrentIndex(t.hour())
        self._min_combo.setCurrentIndex(t.minute())
        self._syncing = False
        self._update_time_until()

    def _on_combo_changed(self):
        """滚动选择器变化 → 同步到 QTimeEdit"""
        if self._syncing:
            return
        self._syncing = True
        self._time_edit.setTime(QTime(self._hour_combo.currentIndex(), self._min_combo.currentIndex()))
        self._syncing = False
        self._update_time_until()

    def _set_weekdays(self, days):
        for i, cb in enumerate(self._wday_checks):
            cb.setChecked(i in days)

    def get_data(self):
        return {
            "name": self._name_edit.text().strip(),
            "hour": self._hour_combo.currentIndex(),
            "minute": self._min_combo.currentIndex(),
            "weekdays": [i for i, cb in enumerate(self._wday_checks) if cb.isChecked()],
        }


class _TimerEditDialog(QDialog):
    """定时器编辑对话框 — 名称 + 时/分/秒"""

    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("编辑定时器" if data else "添加定时器")
        self.setMinimumWidth(380)
        self.setStyleSheet(COMMON_STYLE)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("如：取蛋 浇水")
        self._name_edit.setContextMenuPolicy(Qt.NoContextMenu)
        layout.addRow("名称：", self._name_edit)

        time_layout = QHBoxLayout()
        time_layout.setSpacing(6)
        self._hour_spin = QSpinBox()
        self._hour_spin.setRange(0, 23)
        self._hour_spin.setSuffix(" 时")
        self._hour_spin.setContextMenuPolicy(Qt.NoContextMenu)
        self._min_spin = QSpinBox()
        self._min_spin.setRange(0, 59)
        self._min_spin.setSuffix(" 分")
        self._min_spin.setContextMenuPolicy(Qt.NoContextMenu)
        self._sec_spin = QSpinBox()
        self._sec_spin.setRange(0, 59)
        self._sec_spin.setSuffix(" 秒")
        self._sec_spin.setContextMenuPolicy(Qt.NoContextMenu)
        time_layout.addWidget(self._hour_spin)
        time_layout.addWidget(self._min_spin)
        time_layout.addWidget(self._sec_spin)
        time_layout.addStretch()
        layout.addRow("时长：", time_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        if data:
            self._name_edit.setText(data.get("name", ""))
            total = data.get("duration_seconds", 600)
            self._hour_spin.setValue(total // 3600)
            self._min_spin.setValue((total % 3600) // 60)
            self._sec_spin.setValue(total % 60)

    def get_data(self):
        total = (self._hour_spin.value() * 3600 +
                 self._min_spin.value() * 60 +
                 self._sec_spin.value())
        if total <= 0:
            total = 1
        return {
            "name": self._name_edit.text().strip(),
            "duration_seconds": total,
        }


class _ScheduleEditDialog(QDialog):
    """日程编辑对话框 — 内容 + 星期 + 关联选择"""

    def __init__(self, parent=None, data=None, alarm_choices=None, timer_choices=None):
        super().__init__(parent)
        self.setWindowTitle("编辑日程" if data else "添加日程")
        self.setMinimumWidth(420)
        self.setStyleSheet(COMMON_STYLE)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        self._alarm_map = alarm_choices or {}
        self._timer_map = timer_choices or {}

        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        self._text_edit = QLineEdit()
        self._text_edit.setPlaceholderText("如：取蛋 浇水")
        self._text_edit.setContextMenuPolicy(Qt.NoContextMenu)
        layout.addRow("内容：", self._text_edit)

        # 星期
        wday_label = QLabel("星期：")
        wday_layout = QHBoxLayout()
        wday_layout.setSpacing(4)
        self._wday_checks = []
        for name in WEEKDAY_NAMES:
            cb = QCheckBox(name)
            wday_layout.addWidget(cb)
            self._wday_checks.append(cb)
        wday_layout.addStretch()
        layout.addRow(wday_label, wday_layout)

        # 关联闹钟
        self._alarm_combo = QComboBox()
        self._alarm_combo.addItem("（无）", None)
        for aid, label in self._alarm_map.items():
            self._alarm_combo.addItem(label, aid)
        layout.addRow("关联闹钟：", self._alarm_combo)

        # 关联定时器
        self._timer_combo = QComboBox()
        self._timer_combo.addItem("（无）", None)
        for tid, label in self._timer_map.items():
            self._timer_combo.addItem(label, tid)
        layout.addRow("关联定时器：", self._timer_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        if data:
            self._text_edit.setText(data.get("text", ""))
            wdays = set(data.get("weekdays", []))
            for i, cb in enumerate(self._wday_checks):
                cb.setChecked(i in wdays)
            # 选中关联
            aid = data.get("linked_alarm_id")
            tid = data.get("linked_timer_id")
            for j in range(self._alarm_combo.count()):
                if self._alarm_combo.itemData(j) == aid:
                    self._alarm_combo.setCurrentIndex(j)
                    break
            for j in range(self._timer_combo.count()):
                if self._timer_combo.itemData(j) == tid:
                    self._timer_combo.setCurrentIndex(j)
                    break

    def get_data(self):
        wdays = [i for i, cb in enumerate(self._wday_checks) if cb.isChecked()]
        return {
            "text": self._text_edit.text().strip(),
            "weekdays": wdays,
            "linked_alarm_id": self._alarm_combo.currentData(),
            "linked_timer_id": self._timer_combo.currentData(),
        }


# ═══════════════════════════════════════════════════════════
# 主管理对话框
# ═══════════════════════════════════════════════════════════

class AlarmManagerDialog(QDialog):
    """闹钟、定时器、日程 管理对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("闹钟与日程")
        self.setMinimumSize(600, 480)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(COMMON_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._create_alarm_tab(), "闹钟")
        self._tabs.addTab(self._create_timer_tab(), "定时器")
        self._tabs.addTab(self._create_schedule_tab(), "日程")
        layout.addWidget(self._tabs)

        self._timer_row_widgets = {}  # timer_id -> (row, label)

        self._refresh_all()

        # 定时刷新定时器剩余时间（不重建 UI，只更新文字）
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_timer_labels)
        self._refresh_timer.start(1000)

    # ─── 闹钟标签页 ──────────────────────────────

    def _create_alarm_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._alarm_container = QWidget()
        self._alarm_layout = QVBoxLayout(self._alarm_container)
        self._alarm_layout.setContentsMargins(4, 4, 4, 4)
        self._alarm_layout.setSpacing(4)
        scroll.setWidget(self._alarm_container)
        layout.addWidget(scroll)

        btn = QPushButton("＋ 添加闹钟")
        btn.setObjectName("btn_add")
        btn.setMinimumHeight(36)
        btn.clicked.connect(self._add_alarm)
        layout.addWidget(btn)

        return w

    def _refresh_alarms(self):
        _clear_layout(self._alarm_layout)
        data = _load_data()
        for alarm in data.get("alarms", []):
            row = _make_row()
            aid = alarm.get("id")
            name = alarm.get("name", "未命名")
            t = f"{alarm.get('hour', 0):02d}:{alarm.get('minute', 0):02d}"
            wdays = alarm.get("weekdays", [])
            if len(wdays) == 7 or not wdays:
                day_str = "每天"
            else:
                day_str = " ".join(WEEKDAY_NAMES[d] for d in sorted(wdays))

            enabled = alarm.get("enabled", True)
            status_color = "" if enabled else "color:#888; text-decoration:line-through;"
            label = QLabel(f"<span style='{status_color}'>{name}　{t}　<span style='color:#888'>{day_str}</span></span>")
            label.setMinimumWidth(180)
            row.layout().addWidget(label)
            row.layout().addStretch()

            # 启用/禁用开关
            toggle = ToggleSwitch()
            toggle.setChecked(enabled)
            toggle.setToolTip("开启/关闭闹钟")
            toggle.clicked.connect(lambda checked, a=alarm: self._toggle_alarm(a, checked))
            row.layout().addWidget(toggle)

            btn_edit = QPushButton("编辑")
            btn_edit.clicked.connect(lambda checked, a=alarm: self._edit_alarm(a))
            btn_del = QPushButton("删除")
            btn_del.setObjectName("btn_danger")
            btn_del.clicked.connect(lambda checked, a=alarm: self._delete_alarm(a))
            row.layout().addWidget(btn_edit)
            row.layout().addWidget(btn_del)
            self._alarm_layout.addWidget(row)
        self._alarm_layout.addStretch()

    def _toggle_alarm(self, alarm, enabled):
        """切换闹钟启用/禁用状态"""
        data = _load_data()
        for a in data.get("alarms", []):
            if a["id"] == alarm["id"]:
                a["enabled"] = enabled
                a["last_fired_date"] = ""  # 切换状态时重置，允许当天再次触发
                break
        _save_data(data)
        self._refresh_alarms()

    def _add_alarm(self):
        dlg = _AlarmEditDialog(self)
        if dlg.exec():
            info = dlg.get_data()
            if not info["name"]:
                return
            data = _load_data()
            data.setdefault("alarms", []).append({
                "id": str(uuid.uuid4())[:8],
                "name": info["name"],
                "hour": info["hour"],
                "minute": info["minute"],
                "weekdays": info["weekdays"],
                "enabled": True,
                "last_fired_date": "",
            })
            _save_data(data)
            self._refresh_alarms()

    def _edit_alarm(self, alarm):
        dlg = _AlarmEditDialog(self, data=alarm)
        if dlg.exec():
            info = dlg.get_data()
            if not info["name"]:
                return
            data = _load_data()
            for a in data.get("alarms", []):
                if a["id"] == alarm["id"]:
                    # 如果时间或星期变了，重置 last_fired_date 允许当天再次触发
                    if (a.get("hour") != info["hour"] or a.get("minute") != info["minute"]
                            or a.get("weekdays") != info["weekdays"]):
                        a["last_fired_date"] = ""
                    a["name"] = info["name"]
                    a["hour"] = info["hour"]
                    a["minute"] = info["minute"]
                    a["weekdays"] = info["weekdays"]
                    break
            _save_data(data)
            self._refresh_alarms()

    def _delete_alarm(self, alarm):
        if QMessageBox.question(self, "确认", f"删除闹钟「{alarm.get('name', '')}」？") != QMessageBox.Yes:
            return
        data = _load_data()
        data["alarms"] = [a for a in data.get("alarms", []) if a["id"] != alarm["id"]]
        for s in data.get("schedules", []):
            if s.get("linked_alarm_id") == alarm["id"]:
                s["linked_alarm_id"] = None
        _save_data(data)
        self._refresh_alarms()
        self._refresh_schedules()

    # ─── 定时器标签页 ────────────────────────────

    def _create_timer_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._timer_container = QWidget()
        self._timer_layout = QVBoxLayout(self._timer_container)
        self._timer_layout.setContentsMargins(4, 4, 4, 4)
        self._timer_layout.setSpacing(4)
        scroll.setWidget(self._timer_container)
        layout.addWidget(scroll)

        btn = QPushButton("＋ 添加定时器")
        btn.setObjectName("btn_add")
        btn.setMinimumHeight(36)
        btn.clicked.connect(self._add_timer)
        layout.addWidget(btn)

        return w

    def _refresh_timers(self):
        """完全重建定时器列表"""
        _clear_layout(self._timer_layout)
        self._timer_row_widgets.clear()
        data = _load_data()
        now = time.time()

        for timer in data.get("timers", []):
            row = _make_row()
            tid = timer.get("id")
            name = timer.get("name", "未命名")

            label = QLabel()
            label.setMinimumWidth(200)
            row.layout().addWidget(label)
            row.layout().addStretch()

            # 重置按钮
            btn_reset = QPushButton("重置")
            btn_reset.setObjectName("btn_reset")
            btn_reset.clicked.connect(lambda checked, t=timer: self._reset_timer(t))
            row.layout().addWidget(btn_reset)

            btn_edit = QPushButton("编辑")
            btn_edit.clicked.connect(lambda checked, t=timer: self._edit_timer(t))
            btn_del = QPushButton("删除")
            btn_del.setObjectName("btn_danger")
            btn_del.clicked.connect(lambda checked, t=timer: self._delete_timer(t))
            row.layout().addWidget(btn_edit)
            row.layout().addWidget(btn_del)
            self._timer_layout.addWidget(row)

            self._timer_row_widgets[tid] = (row, label)

        self._timer_layout.addStretch()
        self._refresh_timer_labels()

    def _refresh_timer_labels(self):
        """仅更新定时器文字，不重建 UI"""
        data = _load_data()
        now = time.time()
        for timer in data.get("timers", []):
            tid = timer.get("id")
            if tid not in self._timer_row_widgets:
                continue
            _, label = self._timer_row_widgets[tid]
            name = timer.get("name", "未命名")
            if timer.get("fired", False):
                status = "已触发"
                color = "#4ade80"
            elif not timer.get("enabled", True):
                status = "已暂停"
                color = "#fbbf24"
            else:
                remaining = max(0, int(timer.get("end_time", 0) - now))
                h = remaining // 3600
                m = (remaining % 3600) // 60
                s = remaining % 60
                if h > 0:
                    status = f"剩余 {h}:{m:02d}:{s:02d}"
                else:
                    status = f"剩余 {m}:{s:02d}"
                color = "#e2e8f0" if remaining > 60 else "#f87171"
            label.setText(f"<span style='color:{color}'>{name}　{status}</span>")

    def _add_timer(self):
        dlg = _TimerEditDialog(self)
        if dlg.exec():
            info = dlg.get_data()
            if not info["name"]:
                return
            data = _load_data()
            data.setdefault("timers", []).append({
                "id": str(uuid.uuid4())[:8],
                "name": info["name"],
                "duration_seconds": info["duration_seconds"],
                "end_time": time.time() + info["duration_seconds"],
                "enabled": True,
                "fired": False,
            })
            _save_data(data)
            self._refresh_timers()

    def _edit_timer(self, timer):
        dlg = _TimerEditDialog(self, data=timer)
        if dlg.exec():
            info = dlg.get_data()
            if not info["name"]:
                return
            data = _load_data()
            for t in data.get("timers", []):
                if t["id"] == timer["id"]:
                    t["name"] = info["name"]
                    t["duration_seconds"] = info["duration_seconds"]
                    t["end_time"] = time.time() + info["duration_seconds"]
                    t["fired"] = False
                    break
            _save_data(data)
            self._refresh_timers()

    def _reset_timer(self, timer):
        """重置定时器：重新开始计时"""
        data = _load_data()
        for t in data.get("timers", []):
            if t["id"] == timer["id"]:
                t["end_time"] = time.time() + t.get("duration_seconds", 600)
                t["fired"] = False
                t["enabled"] = True
                break
        _save_data(data)
        self._refresh_timer_labels()

    def _delete_timer(self, timer):
        if QMessageBox.question(self, "确认", f"删除定时器「{timer.get('name', '')}」？") != QMessageBox.Yes:
            return
        data = _load_data()
        data["timers"] = [t for t in data.get("timers", []) if t["id"] != timer["id"]]
        for s in data.get("schedules", []):
            if s.get("linked_timer_id") == timer["id"]:
                s["linked_timer_id"] = None
        _save_data(data)
        self._refresh_timers()
        self._refresh_schedules()

    # ─── 日程标签页 ──────────────────────────────

    def _create_schedule_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._schedule_container = QWidget()
        self._schedule_layout = QVBoxLayout(self._schedule_container)
        self._schedule_layout.setContentsMargins(4, 4, 4, 4)
        self._schedule_layout.setSpacing(4)
        scroll.setWidget(self._schedule_container)
        layout.addWidget(scroll)

        btn = QPushButton("＋ 添加日程")
        btn.setObjectName("btn_add")
        btn.setMinimumHeight(36)
        btn.clicked.connect(self._add_schedule)
        layout.addWidget(btn)

        return w

    def _refresh_schedules(self):
        _clear_layout(self._schedule_layout)
        data = _load_data()
        alarms = {a["id"]: a for a in data.get("alarms", [])}
        timers = {t["id"]: t for t in data.get("timers", [])}

        for s in data.get("schedules", []):
            row = _make_row()
            text = s.get("text", "")

            # 星期
            wdays = s.get("weekdays", [])
            if wdays:
                day_str = " ".join(WEEKDAY_NAMES[d] for d in sorted(wdays))
            else:
                day_str = ""

            # 关联信息
            linked = ""
            aid = s.get("linked_alarm_id")
            tid = s.get("linked_timer_id")
            if aid and aid in alarms:
                a = alarms[aid]
                linked = f"闹钟:{a.get('name','')}"
            elif tid and tid in timers:
                t = timers[tid]
                linked = f"定时:{t.get('name','')}"
            else:
                linked = "未关联"

            label_text = text
            if day_str:
                label_text += f"  <span style='color:#7dd3fc'>{day_str}</span>"
            label_text += f"  <span style='color:#888'>[{linked}]</span>"

            label = QLabel(label_text)
            label.setMinimumWidth(200)
            row.layout().addWidget(label)
            row.layout().addStretch()

            btn_edit = QPushButton("编辑")
            btn_edit.clicked.connect(lambda checked, sc=s: self._edit_schedule(sc))
            btn_del = QPushButton("删除")
            btn_del.setObjectName("btn_danger")
            btn_del.clicked.connect(lambda checked, sc=s: self._delete_schedule(sc))
            row.layout().addWidget(btn_edit)
            row.layout().addWidget(btn_del)
            self._schedule_layout.addWidget(row)
        self._schedule_layout.addStretch()

    def _add_schedule(self):
        data = _load_data()
        alarm_choices = {
            a["id"]: f"{a.get('name','')} ({a.get('hour',0):02d}:{a.get('minute',0):02d})"
            for a in data.get("alarms", [])
        }
        timer_choices = {
            t["id"]: f"{t.get('name','')} ({t.get('duration_seconds',0)//60}分)"
            for t in data.get("timers", [])
        }
        dlg = _ScheduleEditDialog(self, alarm_choices=alarm_choices, timer_choices=timer_choices)
        if dlg.exec():
            info = dlg.get_data()
            if not info["text"]:
                return
            data = _load_data()
            data.setdefault("schedules", []).append({
                "id": str(uuid.uuid4())[:8],
                "text": info["text"],
                "weekdays": info["weekdays"],
                "linked_alarm_id": info["linked_alarm_id"],
                "linked_timer_id": info["linked_timer_id"],
            })
            _save_data(data)
            self._refresh_schedules()

    def _edit_schedule(self, schedule):
        data = _load_data()
        alarm_choices = {
            a["id"]: f"{a.get('name','')} ({a.get('hour',0):02d}:{a.get('minute',0):02d})"
            for a in data.get("alarms", [])
        }
        timer_choices = {
            t["id"]: f"{t.get('name','')} ({t.get('duration_seconds',0)//60}分)"
            for t in data.get("timers", [])
        }
        dlg = _ScheduleEditDialog(self, data=schedule, alarm_choices=alarm_choices, timer_choices=timer_choices)
        if dlg.exec():
            info = dlg.get_data()
            if not info["text"]:
                return
            data = _load_data()
            for s in data.get("schedules", []):
                if s["id"] == schedule["id"]:
                    s["text"] = info["text"]
                    s["weekdays"] = info["weekdays"]
                    s["linked_alarm_id"] = info["linked_alarm_id"]
                    s["linked_timer_id"] = info["linked_timer_id"]
                    break
            _save_data(data)
            self._refresh_schedules()

    def _delete_schedule(self, schedule):
        if QMessageBox.question(self, "确认", f"删除日程「{schedule.get('text', '')}」？") != QMessageBox.Yes:
            return
        data = _load_data()
        data["schedules"] = [s for s in data.get("schedules", []) if s["id"] != schedule["id"]]
        _save_data(data)
        self._refresh_schedules()

    # ─── 全量刷新 ────────────────────────────────

    def _refresh_all(self):
        self._refresh_alarms()
        self._refresh_timers()
        self._refresh_schedules()

    def closeEvent(self, event):
        self._refresh_timer.stop()
        super().closeEvent(event)


# ═══════════════════════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════════════════════

def _make_row():
    """创建一个统一的列表行 QFrame"""
    row = QFrame()
    row.setObjectName("item_row")
    row_layout = QHBoxLayout(row)
    row_layout.setContentsMargins(8, 6, 8, 6)
    row_layout.setSpacing(8)
    return row


def _clear_layout(layout):
    """清空布局中的所有 widget"""
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear_layout(item.layout())