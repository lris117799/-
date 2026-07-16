"""
桌宠模块 - 可丽希亚公主 桌面宠物
- 待机动画 (dj.gif)：循环播放
- 点击动画 (tink.gif)：点击触发，或 5% 概率随机触发
- 扔球动画 (rq.gif)：15% 概率随机触发
- 可拖拽移动，右键菜单关闭
- 触碰互动台词（戳头/脸/肚子/连续戳/疯狂戳）
- 随机待机台词 + 2小时休息提醒
- 精灵信息查询对话框
- 穿透模式（右键菜单切换，透传时右键仍可唤出菜单）
- 鼠标悬停显示游戏时长
- 每日签到提醒
- 随机精灵冷知识
"""

import os
import random
import time
import sys
import json
import ctypes
from ctypes import wintypes
from datetime import date
import warnings
warnings.filterwarnings("ignore", message="iCCP: known incorrect sRGB profile")
warnings.filterwarnings("ignore", message="libpng warning")

from PySide6.QtWidgets import (QLabel, QMenu, QApplication, QDialog,
                                QVBoxLayout, QLineEdit, QTextEdit, QPushButton, QHBoxLayout)
from PySide6.QtCore import Qt, QTimer, QSize, QPoint, QAbstractNativeEventFilter
from PySide6.QtGui import QMovie, QAction, QCursor, QImageReader, QPainter, QFont, QColor, QPixmap, QPen, QBrush

# 确保项目根目录在 sys.path 中，以便导入 core 模块
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# ═══════════════════════════════════════════════════════════
# Windows 原生消息结构（用于穿透模式右键拦截）
# ═══════════════════════════════════════════════════════════

class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", _POINT),
    ]

WM_RBUTTONDOWN = 0x0204

# ═══════════════════════════════════════════════════════════
# 持久化数据
# ═══════════════════════════════════════════════════════════

PET_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pet_data.json")


def _load_pet_data():
    if os.path.exists(PET_DATA_FILE):
        try:
            with open(PET_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_pet_data(data):
    try:
        with open(PET_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# 外观配置
# ═══════════════════════════════════════════════════════════
MAX_HEIGHT = 300                              # 缩放后最大高度
GIF_SPEED = 70                                # GIF 播放速度（100=原速，越小越慢）
DEFAULT_SIZE = QSize(MAX_HEIGHT, MAX_HEIGHT)

# ═══════════════════════════════════════════════════════════
# 触碰台词 — 随机从池中选取
# ═══════════════════════════════════════════════════════════
POKE_LINES = [
    "无礼！本公主的头岂是你能随便乱摸的？",
    "哼，就算你说我可爱，我也不会高兴的……",
    "大胆刁民！我可是高贵的可丽希亚公主！",
]
POKE_SPAM_LINES = [
    "住手！本公主的发型都被你弄乱了！",
]
POKE_CRAZY_LINES = [
    "救——命——啊！有人要谋害公主啦！菲尔特！快来救我！",
]

# ═══════════════════════════════════════════════════════════
# 随机待机台词
# ═══════════════════════════════════════════════════════════
IDLE_LINES = [
    "菲尔特那个胆小鬼，没有本公主照着，被欺负了怎么办。",
    "怎样才能让王国里的每一个人，都过上幸福的生活呢？",
    "这不是迪莫嘛，来，让本公主抱抱！……哎呀别跑！",
    "哼！不要得意，本公主下次一定会赢的！",
    "要不要来场对战检验一下我的训练成果呢？",
    "作为公主，我要更优雅一点……",
    "作为王国的公主，我要变得更强！",
    "嗯？你也是本公主的粉丝吗？",
]

# ═══════════════════════════════════════════════════════════
# 休息提醒台词
# ═══════════════════════════════════════════════════════════
REST_LINES = [
    "已经玩了很久了哦，要不要休息一下？",
    "本公主都累了……你还不去歇会儿吗？",
    "注意休息呀！眼睛会累的~",
    "劳逸结合才能变得更强！先休息吧！",
    "本公主命令你：现在就去休息！",
]

# ═══════════════════════════════════════════════════════════
# 每日签到台词
# ═══════════════════════════════════════════════════════════
DAILY_GREETINGS = [
    "早安！今天别忘了每日任务！",
    "新的一天又开始啦！今天也要加油哦~",
    "早上好！今天的日常任务在等着你呢！",
    "欢迎回来！今天也要元气满满地冒险哦！",
]

# ═══════════════════════════════════════════════════════════
# 冷知识模板
# ═══════════════════════════════════════════════════════════
TRIVIA_TEMPLATES = [
    "冷知识：{name} 是 {attr} 系精灵，种族值 {total} 哦！",
    "你知道 {name} 吗？它是 {attr} 系的，种族值高达 {total}！",
    "悄悄告诉你，{name}（{attr}系）的种族值是 {total}~",
    "科普时间！{name} 属于 {attr} 系，种族值合计 {total}！",
]


# ═══════════════════════════════════════════════════════════
# 桌宠诊断日志系统
# ═══════════════════════════════════════════════════════════

_PET_LOG_DIR = os.path.dirname(os.path.abspath(__file__))

class PetDiagnosticLogger:
    """桌宠运行诊断日志 - 记录全部运行情况到txt文件"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._buffer = []
        self._start_time = time.time()

        # 生成日志文件名（带时间戳，避免重复启动覆盖）
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(self._start_time))
        self._log_file = os.path.join(_PET_LOG_DIR, f"pet_diagnostic_{timestamp}.txt")

        # 写入文件头
        self._write(f"{'='*60}\n")
        self._write(f" 桌宠诊断日志\n")
        self._write(f" 启动时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self._start_time))}\n")
        self._write(f" Python: {sys.version}\n")
        self._write(f" 打包环境: {'是 (frozen)' if getattr(sys, 'frozen', False) else '否 (开发环境)'}\n")
        self._write(f" 可执行路径: {sys.executable}\n")
        self._write(f" __file__: {__file__}\n")
        if hasattr(sys, '_MEIPASS'):
            self._write(f" _MEIPASS: {sys._MEIPASS}\n")
        self._write(f" 素材目录: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'image', 'dj')}\n")
        self._write(f" 日志文件: {self._log_file}\n")
        self._write(f"{'='*60}\n")
        print(f"[桌宠诊断] 日志文件: {self._log_file}")

    def _write(self, text):
        try:
            with open(self._log_file, 'a', encoding='utf-8') as f:
                f.write(text)
        except Exception:
            pass  # 日志写入失败不应影响桌宠运行

    def _fmt(self, msg):
        elapsed = time.time() - self._start_time
        ts = time.strftime("%H:%M:%S", time.localtime())
        return f"[{ts}][{elapsed:7.1f}s] {msg}\n"

    def log(self, event_type: str, detail: str = "", error: str = ""):
        """记录一条日志
        Args:
            event_type: 事件类型 (如 STATE_SWITCH, CLICK, ERROR, TIMER, CLOSE)
            detail: 事件详情
            error: 错误信息（如果有）
        """
        msg = f"[{event_type}] {detail}"
        if error:
            msg += f" | 错误: {error}"
        formatted = self._fmt(msg)
        self._buffer.append(formatted)
        self._write(formatted)
        # 同时在控制台输出
        print(f"[桌宠诊断] {msg}")

    def log_error(self, method: str, error_info: str):
        """专门记录错误"""
        import traceback
        tb = traceback.format_exc()
        msg = self._fmt(f"[ERROR] 发生在 {method}: {error_info}\n{tb}")
        self._buffer.append(msg)
        self._write(msg)
        print(f"[桌宠诊断] ❌ 错误: {method} - {error_info}")

    def get_report(self) -> str:
        """获取当前完整报告"""
        lines = [
            f"{'='*60}",
            f" 桌宠运行报告",
            f"{'='*60}",
            f" 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f" 运行时长: {time.time() - self._start_time:.1f} 秒",
            f" 打包环境: {'是' if getattr(sys, 'frozen', False) else '否'}",
            f" 日志条目: {len(self._buffer)}",
            f"{'='*60}",
        ]
        lines.extend(self._buffer)
        lines.append(f"{'='*60}")
        lines.append(f" 日志文件: {self._log_file}")
        lines.append(f"{'='*60}")
        return "\n".join(lines)

    def save_report(self, filepath: str = None):
        """保存完整报告到指定文件"""
        if filepath is None:
            base = os.path.splitext(self._log_file)[0]
            filepath = f"{base}_report.txt"
        try:
            report = self.get_report()
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"[桌宠诊断] 报告已保存: {filepath}")
            return filepath
        except Exception as e:
            print(f"[桌宠诊断] 保存报告失败: {e}")
            return None


# ═══════════════════════════════════════════════════════════
# 穿透模式原生事件过滤器
# ═══════════════════════════════════════════════════════════

class PetNativeFilter(QAbstractNativeEventFilter):
    """穿透模式下拦截 Windows 右键消息，实现右键穿透时仍可唤出菜单"""

    def __init__(self, pet):
        super().__init__()
        self.pet = pet

    def nativeEventFilter(self, eventType, message):
        if not self.pet._penetration_mode:
            return False, 0
        try:
            msg = ctypes.cast(message, ctypes.POINTER(_MSG)).contents
            if msg.message == WM_RBUTTONDOWN:
                cursor_pos = QCursor.pos()
                if self.pet.frameGeometry().contains(cursor_pos):
                    QTimer.singleShot(0, lambda: self.pet._show_context_menu_at(cursor_pos))
                    return True, 0
        except Exception:
            pass
        return False, 0


# ═══════════════════════════════════════════════════════════
# 对话气泡
# ═══════════════════════════════════════════════════════════

class SpeechBubble(QLabel):
    """漂浮在桌宠上方的漫画风格对话气泡"""

    def __init__(self, parent, text: str, duration_ms: int = 4000):
        super().__init__(parent)
        self._parent_pet = parent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)

        font = QFont("Microsoft YaHei", 11)
        font.setBold(True)
        self.setFont(font)
        self.setStyleSheet("""
            QLabel {
                color: #000000;
                padding: 8px 14px;
                background: transparent;
            }
        """)
        self.setText(text)
        self.setWordWrap(True)
        self.setMaximumWidth(400)
        self.adjustSize()

        self._reposition()
        QTimer.singleShot(duration_ms, self._fade_out)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 白色填充 + 黑色描边
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 8, 8)
        super().paintEvent(event)

    def _reposition(self):
        """将气泡定位到宠物上方中央"""
        if self._parent_pet and self._parent_pet.isVisible():
            pet_geo = self._parent_pet.frameGeometry()
            x = pet_geo.center().x() - self.width() // 2
            y = pet_geo.top() - self.height() - 8
            self.move(max(0, x), max(0, y))

    def show(self):
        self._reposition()
        super().show()

    def _fade_out(self):
        try:
            self.hide()
            self.deleteLater()
        except RuntimeError:
            pass  # C++ object already deleted


# ═══════════════════════════════════════════════════════════
# 精灵查询对话框
# ═══════════════════════════════════════════════════════════

class SpiritSearchDialog(QDialog):
    """精灵信息查询对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("精灵查询")
        self.setMinimumSize(450, 420)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                border: 2px solid rgba(124, 58, 237, 0.4);
                border-radius: 12px;
                color: #e2e8f0;
            }
            QLineEdit {
                background-color: #2a2a3a;
                border: 2px solid rgba(124, 58, 237, 0.3);
                border-radius: 8px;
                padding: 10px 14px;
                color: #e2e8f0;
                font-size: 15px;
                font-family: "Microsoft YaHei";
            }
            QLineEdit:focus {
                border-color: rgba(124, 58, 237, 0.7);
            }
            QLineEdit::placeholder {
                color: #666;
            }
            QPushButton {
                background-color: rgba(124, 58, 237, 0.3);
                border: 1px solid rgba(124, 58, 237, 0.5);
                border-radius: 8px;
                padding: 10px 24px;
                color: #e2e8f0;
                font-size: 14px;
                font-family: "Microsoft YaHei";
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(124, 58, 237, 0.5);
            }
            QTextEdit {
                background-color: #2a2a3a;
                border: 2px solid rgba(124, 58, 237, 0.3);
                border-radius: 8px;
                padding: 10px;
                color: #c9d1d9;
                font-size: 14px;
                font-family: "Microsoft YaHei";
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入精灵名字，如：迪莫、水蓝蓝、火花……")
        self.search_input.returnPressed.connect(self._do_search)
        layout.addWidget(self.search_input)

        # 按钮
        btn_layout = QHBoxLayout()
        self.search_btn = QPushButton("查询")
        self.search_btn.clicked.connect(self._do_search)
        btn_layout.addStretch()
        btn_layout.addWidget(self.search_btn)
        layout.addLayout(btn_layout)

        # 结果区：立绘 + 文字
        result_layout = QHBoxLayout()
        result_layout.setSpacing(14)

        # 立绘
        self.image_label = QLabel()
        self.image_label.setFixedSize(130, 130)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            background-color: rgba(30, 30, 40, 0.5);
            border: 1px solid rgba(124, 58, 237, 0.2);
            border-radius: 8px;
        """)
        result_layout.addWidget(self.image_label)

        # 文字信息
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setPlaceholderText("查询结果将显示在这里……")
        result_layout.addWidget(self.result_area, 1)

        layout.addLayout(result_layout, 1)

    def _do_search(self):
        name = self.search_input.text().strip()
        if not name:
            self.result_area.setText("请输入精灵名字后再查询~")
            self.image_label.clear()
            return

        result = _lookup_spirit(name)
        if isinstance(result, str):
            self.result_area.setText(result)
            self.image_label.clear()
            return

        mon = result[0]  # 取第一个匹配
        stats = mon.get("stats", {})
        info = (
            f"【{mon.get('name', '未知')}】\n"
            f"属性：{mon.get('attribute', '未知')}\n"
            f"身高：{mon.get('height', '') or '未知'} m\n"
            f"体重：{mon.get('weight', '') or '未知'} kg\n"
            f"星光值：{mon.get('starlight', '?')}\n"
            f"金币回顾：{mon.get('review_cost', '?')}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"HP　　：{stats.get('hp', '?')}\n"
            f"攻击　：{stats.get('attack', '?')}\n"
            f"魔攻　：{stats.get('magic_attack', '?')}\n"
            f"防御　：{stats.get('defense', '?')}\n"
            f"魔防　：{stats.get('magic_defense', '?')}\n"
            f"速度　：{stats.get('speed', '?')}\n"
            f"种族值：{stats.get('total', '?')}\n"
        )
        self.result_area.setText(info)

        # 加载本地立绘
        pid = mon.get("id", 0)
        self._load_local_image(pid)

    def _load_local_image(self, pid: int):
        """加载本地缓存的立绘图片 image/tj/images/{pid:03d}.png"""
        path = os.path.join(_project_root, "image", "tj", "images", f"{pid:03d}.png")
        if os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                return
        self.image_label.setText("暂无\n立绘")
        self.image_label.setStyleSheet(self.image_label.styleSheet() + "color: #555; font-size: 13px;")


# ═══════════════════════════════════════════════════════════
# 精灵查询逻辑
# ═══════════════════════════════════════════════════════════

_enriched_map = None


def _load_enriched_data():
    """加载 enriched 数据库，提取 name -> {height, weight} 映射"""
    global _enriched_map
    if _enriched_map is not None:
        return _enriched_map

    _enriched_map = {}
    enriched_file = os.path.join(_project_root, "image", "tj", "lkwg_enriched_data.json")
    try:
        if os.path.exists(enriched_file):
            with open(enriched_file, 'r', encoding='utf-8') as f:
                enriched_db = json.load(f)
            for mon in enriched_db:
                name = mon.get("name", "")
                if name:
                    _enriched_map[name] = {
                        "height": mon.get("height", ""),
                        "weight": mon.get("weight", ""),
                    }
    except Exception as e:
        print(f"[桌宠] 加载 enriched 数据失败: {e}")
    return _enriched_map


def _lookup_spirit(name: str):
    """
    精灵查询逻辑 — 从 pokemon_data.json 查询，enriched 数据补充身高体重
    返回 list[dict] 或错误字符串
    """
    data_file = os.path.join(_project_root, "image", "tj", "pokemon_data.json")
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            db = json.load(f)
    except Exception as e:
        return f"无法加载精灵数据库：{e}"

    if not name:
        return "请输入精灵名字后再查询~"

    name_lower = name.lower()
    matches = []
    for mon in db:
        mon_name = mon.get("name", "")
        if name_lower in mon_name.lower() or mon_name.lower() in name_lower:
            matches.append(mon)

    if not matches:
        return f"抱歉，暂时没有找到关于「{name}」的信息。\n\n试试输入其他精灵名字？"

    if len(matches) > 1:
        exact = [m for m in matches if m.get("name", "") == name]
        if exact:
            matches = exact

    # 从 enriched 数据补充身高体重
    enriched = _load_enriched_data()
    for mon in matches:
        if not mon.get("height") and not mon.get("weight"):
            extra = enriched.get(mon.get("name", ""), {})
            if extra.get("height"):
                mon["height"] = extra["height"]
            if extra.get("weight"):
                mon["weight"] = extra["weight"]

    return matches[:5]


# ═══════════════════════════════════════════════════════════
# 桌面宠物主体
# ═══════════════════════════════════════════════════════════

class DesktopPet(QLabel):
    """桌面宠物 — 无边框、置顶、透明背景的动画窗口"""

    STATE_IDLE = "idle"
    STATE_TINK = "tink"
    STATE_THROW = "throw"
    STATE_BB = "bb"
    STATE_SQ = "sq"
    STATE_XL = "xl"

    SPAM_THRESHOLD = 3    # 连续点击次数阈值
    CRAZY_THRESHOLD = 6   # 疯狂乱戳阈值
    SPAM_WINDOW_MS = 2000 # 连续点击时间窗口

    def __init__(self, parent=None):
        super().__init__(parent)

        # 诊断日志
        self._diag = PetDiagnosticLogger()
        self._diag.log("INIT", "桌宠开始初始化")

        # 素材路径
        self._base_dir = os.path.dirname(os.path.abspath(__file__))
        self._image_dir = os.path.join(self._base_dir, "image", "dj")
        self._diag.log("INIT", f"素材目录: {self._image_dir}")

        # 加载 GIF 素材信息（不预创建 QMovie，每次 _switch_state 创建全新的）
        self._movies = {}        # name → (path, size)
        self._movie_sizes = {}   # name → QSize
        for name, filename in [(self.STATE_IDLE, "dj.gif"),
                               (self.STATE_TINK, "tink.gif"),
                               (self.STATE_THROW, "rq.gif"),
                               (self.STATE_BB, "bb.gif"),
                               (self.STATE_SQ, "sq.gif"),
                               (self.STATE_XL, "xl.gif")]:
            path, size = self._load_movie(filename)
            self._movies[name] = (path, size)
            self._movie_sizes[name] = size
            if path:
                self._diag.log("INIT", f"  ✅ 素材就绪: {filename} ({size.width()}x{size.height()})")
            else:
                self._diag.log("INIT", f"  ⚠️ 素材不存在: {filename}")

        self._current_state = None
        self._current_movie = None
        self._prev_frame = -1   # 帧轮询用的前一帧编号

        # 窗口设置
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.NoFocus)

        self.setFixedSize(DEFAULT_SIZE)

        # 拖拽
        self._drag_pos = None

        # 互动点击计数
        self._poke_count = 0
        self._poke_last_time = 0
        self._poke_reset_timer = QTimer(self)
        self._poke_reset_timer.setSingleShot(True)
        self._poke_reset_timer.timeout.connect(self._reset_poke_count)

        # 当前是否正在显示气泡
        self._active_bubble = None

        # 随机动画定时器（每 5 秒检查一次）
        self._random_timer = QTimer(self)
        self._random_timer.timeout.connect(self._try_random_animation)
        self._random_timer.start(5000)

        # 随机台词定时器（每 15-30 秒随机说一句话）
        self._idle_talk_timer = QTimer(self)
        self._idle_talk_timer.timeout.connect(self._try_idle_talk)
        self._schedule_next_idle_talk()

        # 2 小时休息提醒
        self._rest_timer = QTimer(self)
        self._rest_timer.setSingleShot(True)
        self._rest_timer.timeout.connect(self._show_rest_reminder)
        self._rest_timer.start(2 * 60 * 60 * 1000)  # 2小时
        self._rest_reminded = False

        # ── 穿透模式 ────────────────────────────
        self._penetration_mode = False
        self._native_filter = None

        # ── 游戏时长（从桌宠启动算起）───────────
        self._pet_start_time = time.time()
        self._hover_bubble = None

        # ── 动画安全超时（打包环境帧检测可能失效）──
        self._animation_timeout = QTimer(self)
        self._animation_timeout.setSingleShot(True)
        self._animation_timeout.timeout.connect(self._on_animation_timeout)

        # ── 帧轮询定时器（替代 setMovie + QMovie 信号，避免打包环境 C++ 崩溃）──
        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._on_frame_tick)
        self._frame_timer.start(33)  # ~30fps 轮询帧状态 + 触发重绘

        # ── 每日签到 ────────────────────────────
        self._check_daily_greeting()

        # ── 随机精灵冷知识 ──────────────────────
        self._trivia_timer = QTimer(self)
        self._trivia_timer.timeout.connect(self._show_trivia)
        self._schedule_next_trivia()

        # ── 闹钟/定时器检查（每秒一次）──────────
        self._alarm_check_timer = QTimer(self)
        self._alarm_check_timer.timeout.connect(self._check_alarms)
        self._alarm_check_timer.start(1000)

        # 设置鼠标追踪（悬停气泡需要）
        self.setMouseTracking(True)

        # 右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # 初始位置：屏幕右下角
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            self.move(geom.right() - 180, geom.bottom() - 200)

        # 开始待机
        self._switch_state(self.STATE_IDLE)
        self._diag.log("INIT", "桌宠初始化完成")

    # ─── 资源加载 ─────────────────────────────────

    def _load_movie(self, filename):
        path = os.path.join(self._image_dir, filename)
        if not os.path.exists(path):
            print(f"[桌宠] 素材未找到: {path}")
            return None, QSize(0, 0)
        # 仅验证文件存在并获取尺寸，不创建 QMovie（每次 _switch_state 时创建全新的）
        orig_size = QImageReader(path).size()
        print(f"[桌宠] 素材已加载: {filename}  ({orig_size.width()}x{orig_size.height()})")
        return path, orig_size

    # ─── 清晰缩放 — 重写 paintEvent ─────────────

    def paintEvent(self, event):
        """自定义绘制：用 SmoothTransformation 缩放，避免模糊"""
        if self._current_movie:
            try:
                pix = self._current_movie.currentPixmap()
            except RuntimeError:
                pix = QPixmap()
            if not pix.isNull():
                painter = QPainter(self)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                painter.setRenderHint(QPainter.Antialiasing, True)
                scaled = pix.scaled(
                    self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                x = (self.width() - scaled.width()) // 2
                y = (self.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
                return
        super().paintEvent(event)

    # ─── 缩放计算 ─────────────────────────────────

    def _scaled_size(self, state):
        orig = self._movie_sizes.get(state, QSize(MAX_HEIGHT, MAX_HEIGHT))
        if orig.width() <= 0 or orig.height() <= 0:
            return QSize(MAX_HEIGHT, MAX_HEIGHT)
        ratio = MAX_HEIGHT / orig.height()
        return QSize(int(orig.width() * ratio), MAX_HEIGHT)

    # ─── 状态切换 ─────────────────────────────────

    def _switch_state(self, state):
        entry = self._movies.get(state)
        if entry is None:
            self._diag.log("STATE_SWITCH", f"'{state}' 素材缺失，跳过")
            return

        path, size = entry
        state_name = {self.STATE_IDLE: "待机", self.STATE_TINK: "点击", self.STATE_THROW: "扔球",
                      self.STATE_BB: "变扁", self.STATE_SQ: "生气", self.STATE_XL: "训练"}.get(state, state)
        self._diag.log("STATE_SWITCH", f"切换到 → {state_name}")

        # 销毁旧 QMovie（不调用 setMovie，直接释放）
        if self._current_movie:
            try:
                self._current_movie.stop()
                self._diag.log("STATE_SWITCH", f"已停止旧动画: {self._current_state}")
            except Exception:
                pass
            self._current_movie = None

        # ═══ 每次都创建全新的 QMovie（避免复用导致 C++ 状态损坏）═══
        try:
            movie = QMovie(path)
            movie.setCacheMode(QMovie.CacheAll)
            movie.setSpeed(GIF_SPEED)
        except Exception as e:
            self._diag.log_error("STATE_SWITCH", f"QMovie创建失败: {path}: {e}")
            return

        self._current_movie = movie
        self._current_state = state
        self._prev_frame = -1  # 重置帧检测

        # 调整窗口大小
        self.setFixedSize(self._scaled_size(state))

        # 非待机动画：开启 5 秒超时兜底
        if state != self.STATE_IDLE:
            self._animation_timeout.start(5000)
        else:
            self._animation_timeout.stop()

        # 开始播放（try/except 兜底 C++ 异常）
        try:
            movie.jumpToFrame(0)
            movie.start()
            self._diag.log("STATE_SWITCH", f"✅ QMovie播放成功: {state_name}")
        except Exception as e:
            self._diag.log_error("movie.start", f"状态={state}: {e}")

    def _on_frame_tick(self):
        """帧轮询回调（~30fps）：检测动画循环 + 触发重绘"""
        if self._current_movie is None:
            return

        # 先触发 paintEvent 绘制当前帧
        self.update()

        # 获取当前帧编号
        try:
            current_frame = self._current_movie.currentFrameNumber()
        except RuntimeError:
            # QMovie 的 C++ 对象已销毁
            self._diag.log("ANIM", "QMovie C++ 对象已销毁，释放引用")
            self._current_movie = None
            self._current_state = None
            return
        except Exception:
            return

        # 检测动画循环：帧从高编号回到 0
        if self._prev_frame > 0 and current_frame == 0:
            if self._current_state == self.STATE_IDLE:
                # idle 循环结束，重新播放
                self._diag.log("ANIM", "idle动画循环，重新播放")
                try:
                    self._current_movie.jumpToFrame(0)
                    self._current_movie.start()
                except Exception as e:
                    self._diag.log_error("idle重播", str(e))
            else:
                # 非 idle 动画播放完成，切回待机
                self._diag.log("ANIM", f"单次动画 '{self._current_state}' 播放完成")
                self._switch_state(self.STATE_IDLE)
                return  # _switch_state 会重置 _prev_frame

        self._prev_frame = current_frame

    def _on_animation_timeout(self):
        """动画超时兜底：如果单次动画未正常回到待机，强制切换"""
        if self._current_state and self._current_state != self.STATE_IDLE:
            self._diag.log("ANIM", f"⏱️ 动画 '{self._current_state}' 超时(5s)，强制回到待机")
            self._switch_state(self.STATE_IDLE)

    # ─── 随机动画 ─────────────────────────────────

    def _try_random_animation(self):
        if self._current_state != self.STATE_IDLE:
            return
        roll = random.random()
        if roll < 0.05:
            self._diag.log("TIMER", f"随机动画触发: 点击 (roll={roll:.3f})")
            self._switch_state(self.STATE_TINK)
        elif roll < 0.10:
            self._diag.log("TIMER", f"随机动画触发: 变扁 (roll={roll:.3f})")
            self._switch_state(self.STATE_BB)
        elif roll < 0.15:
            self._diag.log("TIMER", f"随机动画触发: 生气 (roll={roll:.3f})")
            self._switch_state(self.STATE_SQ)
        elif roll < 0.20:
            self._diag.log("TIMER", f"随机动画触发: 训练 (roll={roll:.3f})")
            self._switch_state(self.STATE_XL)
        elif roll < 0.25:
            self._diag.log("TIMER", f"随机动画触发: 扔球 (roll={roll:.3f})")
            self._switch_state(self.STATE_THROW)

    # ─── 随机台词 ─────────────────────────────────

    def _schedule_next_idle_talk(self):
        """随机 15-30 秒后说一句话"""
        delay = random.randint(15000, 30000)
        self._idle_talk_timer.start(delay)

    def _try_idle_talk(self):
        """在待机状态下随机冒泡"""
        if self._current_state != self.STATE_IDLE:
            return
        if self._active_bubble is not None:
            self._schedule_next_idle_talk()
            return
        line = random.choice(IDLE_LINES)
        self._show_bubble(line)
        self._schedule_next_idle_talk()

    # ─── 休息提醒 ─────────────────────────────────

    def _show_rest_reminder(self):
        """2小时休息提醒"""
        self._rest_reminded = True
        line = random.choice(REST_LINES)
        self._show_bubble(line, duration_ms=6000)
        # 之后每 30 分钟再提醒一次
        self._rest_timer.start(30 * 60 * 1000)

    # ─── 对话气泡 ─────────────────────────────────

    def _show_bubble(self, text: str, duration_ms: int = 4000):
        """显示对话气泡（点击触发）"""
        if self._active_bubble is not None:
            try:
                self._active_bubble._fade_out()
            except RuntimeError:
                pass
            self._active_bubble = None
        bubble = SpeechBubble(self, text, duration_ms)
        self._active_bubble = bubble
        bubble.show()
        self._reposition_bubbles()
        QTimer.singleShot(duration_ms + 100, lambda: setattr(self, '_active_bubble', None)
                          if self._active_bubble is bubble else None)

    def _reposition_bubbles(self):
        """将两个气泡上下分层：hover 在上，active 在下"""
        pet_geo = self.frameGeometry()
        hover = self._hover_bubble
        active = self._active_bubble

        if hover and active:
            # 两个都存在：hover 在上，active 在下
            hx = pet_geo.center().x() - hover.width() // 2
            hy = pet_geo.top() - active.height() - hover.height() - 16
            hover.move(max(0, hx), max(0, hy))
            ax = pet_geo.center().x() - active.width() // 2
            ay = pet_geo.top() - active.height() - 10
            active.move(max(0, ax), max(0, ay))
        elif hover:
            hx = pet_geo.center().x() - hover.width() // 2
            hy = pet_geo.top() - hover.height() - 10
            hover.move(max(0, hx), max(0, hy))
        elif active:
            ax = pet_geo.center().x() - active.width() // 2
            ay = pet_geo.top() - active.height() - 10
            active.move(max(0, ax), max(0, ay))

    # ─── 互动：触碰检测 ──────────────────────────

    def _handle_poke(self):
        """
        处理戳碰：
        - 单次/1-2次：随机从触碰池选台词
        - 连续（3-5次）：连续戳台词
        - 疯狂（6+次）：疯狂戳台词
        """
        now = time.time() * 1000

        if now - self._poke_last_time > self.SPAM_WINDOW_MS:
            self._poke_count = 0

        self._poke_count += 1
        self._poke_last_time = now

        self._poke_reset_timer.stop()
        self._poke_reset_timer.start(self.SPAM_WINDOW_MS)

        if self._poke_count >= self.CRAZY_THRESHOLD:
            line = random.choice(POKE_CRAZY_LINES)
            self._diag.log("CLICK", f"疯狂戳! 第{self._poke_count}次: {line}")
        elif self._poke_count >= self.SPAM_THRESHOLD:
            line = random.choice(POKE_SPAM_LINES)
            self._diag.log("CLICK", f"连续戳 第{self._poke_count}次: {line}")
        else:
            line = random.choice(POKE_LINES)
            self._diag.log("CLICK", f"点击 第{self._poke_count}次: {line}")

        self._show_bubble(line)

    def _reset_poke_count(self):
        self._poke_count = 0

    # ─── 每日签到 ─────────────────────────────────

    def _check_daily_greeting(self):
        """检查是否需要显示每日签到提醒"""
        data = _load_pet_data()
        today = date.today().isoformat()
        last_date = data.get("last_greeting_date", "")
        if last_date != today:
            QTimer.singleShot(3000, lambda: self._show_bubble(
                random.choice(DAILY_GREETINGS), duration_ms=5000
            ))
            data["last_greeting_date"] = today
            _save_pet_data(data)

    # ─── 随机冷知识 ───────────────────────────────

    def _schedule_next_trivia(self):
        """随机 60-120 秒后显示冷知识"""
        delay = random.randint(60000, 120000)
        self._trivia_timer.start(delay)

    def _show_trivia(self):
        """显示随机精灵冷知识"""
        if self._current_state != self.STATE_IDLE:
            self._schedule_next_trivia()
            return
        if self._active_bubble is not None:
            self._schedule_next_trivia()
            return
        try:
            data_file = os.path.join(_project_root, "image", "tj", "pokemon_data.json")
            with open(data_file, 'r', encoding='utf-8') as f:
                db = json.load(f)
            if db:
                mon = random.choice(db)
                name = mon.get("name", "未知")
                attr = mon.get("attribute", "未知")
                stats = mon.get("stats", {})
                total = stats.get("total", "?")
                template = random.choice(TRIVIA_TEMPLATES)
                self._show_bubble(
                    template.format(name=name, attr=attr, total=total),
                    duration_ms=5000
                )
        except Exception:
            pass
        self._schedule_next_trivia()

    # ─── 闹钟检查 ─────────────────────────────────

    def _check_alarms(self):
        """每秒检查闹钟和定时器是否触发"""
        try:
            from zc.alarm_manager import check_alarms_and_timers, play_alarm_sound
            def on_fire(name, _type):
                self._show_bubble(f"「{name}」时间到了！", duration_ms=6000)
                play_alarm_sound()
            check_alarms_and_timers(on_fire)
        except Exception:
            pass

    def _open_alarm_manager(self):
        """打开闹钟管理对话框"""
        try:
            from zc.alarm_manager import AlarmManagerDialog
            dialog = AlarmManagerDialog()
            dialog.exec()
        except Exception as e:
            print(f"[桌宠] 打开闹钟管理器失败: {e}")

    # ─── 悬停气泡 ─────────────────────────────────

    def enterEvent(self, event):
        """鼠标悬停时显示游戏时长"""
        if self._penetration_mode:
            return
        elapsed = time.time() - self._pet_start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        if hours > 0:
            text = f"今天已经玩了 {hours} 小时 {minutes} 分钟"
        else:
            text = f"今天已经玩了 {minutes} 分钟"
        self._diag.log("EVENT", f"鼠标进入 (运行时长: {hours}h{minutes}m)")
        self._show_hover_bubble(text)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开时隐藏时长气泡"""
        self._diag.log("EVENT", "鼠标离开")
        if self._hover_bubble:
            try:
                self._hover_bubble._fade_out()
            except RuntimeError:
                pass
            self._hover_bubble = None
        super().leaveEvent(event)

    def _show_hover_bubble(self, text):
        """显示悬停时长气泡，如果已有对话气泡则显示在上方"""
        if self._hover_bubble:
            try:
                self._hover_bubble._fade_out()
            except RuntimeError:
                pass
            self._hover_bubble = None
        bubble = SpeechBubble(self, text, duration_ms=3000)
        self._hover_bubble = bubble
        bubble.show()
        self._reposition_bubbles()
        QTimer.singleShot(3100, lambda: setattr(self, '_hover_bubble', None)
                          if self._hover_bubble is bubble else None)

    # ─── 穿透模式 ─────────────────────────────────

    def _toggle_penetration(self):
        """切换穿透模式"""
        self._penetration_mode = not self._penetration_mode
        if self._penetration_mode:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            if self._native_filter is None:
                self._native_filter = PetNativeFilter(self)
                QApplication.instance().installNativeEventFilter(self._native_filter)
            self._show_bubble("穿透模式已开启\n右键我依然可以打开菜单哦~", duration_ms=2500)
        else:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            if self._native_filter:
                try:
                    QApplication.instance().removeNativeEventFilter(self._native_filter)
                except Exception:
                    pass
                self._native_filter = None
            self._show_bubble("穿透模式已关闭", duration_ms=2000)

    def _show_context_menu_at(self, pos):
        """在指定全局坐标显示右键菜单"""
        self._show_context_menu(self.mapFromGlobal(pos))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._drag_pos is not None:
                drag_distance = (event.globalPosition().toPoint() -
                                 (self.frameGeometry().topLeft() + self._drag_pos))
                if drag_distance.manhattanLength() < 5:
                    # 是点击不是拖拽
                    self._diag.log("CLICK", f"左键点击 (当前状态={self._current_state})")
                    if self._current_state == self.STATE_IDLE:
                        self._switch_state(self.STATE_TINK)
                    # 触碰台词
                    self._handle_poke()
                else:
                    self._diag.log("CLICK", f"拖拽释放 (距离={drag_distance.manhattanLength()})")
            self._drag_pos = None
            event.accept()

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e26;
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 8px;
                padding: 4px;
                color: #e2e8f0;
                font-size: 13px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(124, 58, 237, 0.2);
            }
        """)

        search_action = QAction("精灵查询", menu)
        search_action.triggered.connect(self._open_spirit_search)
        menu.addAction(search_action)

        menu.addSeparator()

        alarm_action = QAction("闹钟与日程", menu)
        alarm_action.triggered.connect(self._open_alarm_manager)
        menu.addAction(alarm_action)

        menu.addSeparator()

        pen_text = "关闭穿透模式" if self._penetration_mode else "开启穿透模式"
        pen_action = QAction(pen_text, menu)
        pen_action.triggered.connect(self._toggle_penetration)
        menu.addAction(pen_action)

        menu.addSeparator()

        close_action = QAction("关闭桌宠", menu)
        close_action.triggered.connect(self.close_pet)
        menu.addAction(close_action)

        menu.exec(QCursor.pos())

    def _open_spirit_search(self):
        dialog = SpiritSearchDialog()
        dialog.exec()

    def close_pet(self):
        global _pet_instance
        self._diag.log("CLOSE", "开始关闭桌宠")
        if self._current_movie:
            try:
                self._current_movie.stop()
                self._diag.log("CLOSE", "当前动画已停止")
            except Exception as e:
                self._diag.log("CLOSE", "停止当前动画异常", error=str(e))
            self._current_movie = None
        self._random_timer.stop()
        self._idle_talk_timer.stop()
        self._rest_timer.stop()
        self._poke_reset_timer.stop()
        self._trivia_timer.stop()
        self._alarm_check_timer.stop()
        self._animation_timeout.stop()  # 修复：遗漏的定时器
        self._frame_timer.stop()
        self._diag.log("CLOSE", "所有定时器已停止")
        if self._active_bubble:
            try:
                self._active_bubble._fade_out()
            except RuntimeError:
                pass
            self._active_bubble = None
        if self._hover_bubble:
            try:
                self._hover_bubble._fade_out()
            except RuntimeError:
                pass
            self._hover_bubble = None
        if self._native_filter:
            try:
                QApplication.instance().removeNativeEventFilter(self._native_filter)
            except Exception:
                pass
            self._native_filter = None
        self.hide()
        self.deleteLater()
        _pet_instance = None
        self._diag.log("CLOSE", "桌宠已关闭")
        # 生成最终报告
        report_path = self._diag.save_report()
        if report_path:
            print(f"[桌宠诊断] 关闭报告: {report_path}")

    def showEvent(self, event):
        super().showEvent(event)
        if self._current_movie:
            try:
                if self._current_movie.state() == QMovie.NotRunning:
                    self._diag.log("EVENT", "showEvent触发，启动暂停的动画")
                    self._current_movie.start()
            except RuntimeError:
                pass  # C++ 对象已销毁


# ═══════════════════════════════════════════════════════════
# 全局单例管理
# ═══════════════════════════════════════════════════════════

_pet_instance = None
_pet_diag = None  # 模块级诊断日志引用


def is_pet_running():
    global _pet_instance
    return _pet_instance is not None and _pet_instance.isVisible()


def start_pet():
    global _pet_instance, _pet_diag
    if _pet_instance is not None:
        try:
            if _pet_instance.isVisible():
                print("[桌宠] 已在运行，跳过")
                return
        except RuntimeError:
            pass
        _pet_instance = None

    # 初始化诊断日志（在 DesktopPet 之前，记录启动全过程）
    _pet_diag = PetDiagnosticLogger()
    _pet_diag.log("LIFECYCLE", "start_pet() 被调用")

    print("[桌宠] 正在启动...")
    _pet_diag.log("LIFECYCLE", "创建 DesktopPet 实例...")
    _pet_instance = DesktopPet()
    _pet_diag.log("LIFECYCLE", "DesktopPet 实例已创建，调用 show()...")
    _pet_instance.show()
    print("[桌宠] 已启动")
    _pet_diag.log("LIFECYCLE", "桌宠已显示")
    return _pet_instance


def stop_pet():
    global _pet_instance, _pet_diag
    if _pet_instance is not None:
        print("[桌宠] 正在关闭...")
        if _pet_diag:
            _pet_diag.log("LIFECYCLE", "stop_pet() 被调用")
        _pet_instance.close_pet()
        _pet_instance = None


def toggle_pet(enabled: bool):
    global _pet_diag
    if _pet_diag:
        _pet_diag.log("LIFECYCLE", f"toggle_pet({enabled})")
    if enabled:
        start_pet()
    else:
        stop_pet()