# core/keyboard_hook.py
"""
全局热键检测 - 使用 GetAsyncKeyState 轮询

相比其他方案的优势：
- 不阻塞按键传递：按键事件正常传递给当前焦点窗口
- 不需要管理员权限：不受 UIPI（用户界面特权隔离）限制
  （低级键盘钩子 WH_KEYBOARD_LL 在其他程序以管理员权限运行时会失效）
- 实现简单稳定：无需独立线程和消息循环

用法：
    hook = KeyboardHook(parent)
    hook.hotkey_triggered.connect(handler)  # handler 接收 hotkey_id 参数
    hook.register_hotkey(vk, mod_code, hotkey_id)
    hook.start()
    # ...
    hook.stop()
"""
import ctypes
from PySide6.QtCore import QObject, Signal, QTimer

# 修饰键虚拟键码
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_LWIN = 0x5B
VK_RWIN = 0x5C

# 修饰键掩码（与 RegisterHotKey 的 MOD_* 定义一致）
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

_user32 = ctypes.windll.user32
_user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
_user32.GetAsyncKeyState.restype = ctypes.c_short


class KeyboardHook(QObject):
    """全局热键检测（轮询方式，非阻塞，无需管理员权限）"""

    # 触发热键时发出，参数为注册时提供的 hotkey_id
    hotkey_triggered = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lock = None  # 单线程运行无需锁
        # {(vk, mod_mask): hotkey_id}
        self._hotkeys = {}
        # 已按下的键签名（防止长按重复触发）
        self._pressed = set()
        # 轮询定时器（30ms ≈ 33fps，足够灵敏捕捉用户按键）
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._poll)

    def register_hotkey(self, vk, mod_code, hotkey_id):
        """注册一个热键

        :param vk: 虚拟键码
        :param mod_code: 修饰键代码（与 RegisterHotKey 的 MOD_* 一致）
        :param hotkey_id: 热键 ID，会通过 hotkey_triggered 信号传回
        """
        self._hotkeys[(vk, mod_code)] = hotkey_id

    def unregister_all(self):
        """清空所有已注册的热键"""
        self._hotkeys.clear()
        self._pressed.clear()

    def start(self):
        """开始轮询按键"""
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        """停止轮询"""
        self._timer.stop()
        self._pressed.clear()

    def _poll(self):
        """轮询按键状态，检测热键按下边沿"""
        # 获取当前修饰键状态（高位为 1 表示按下）
        mod_mask = 0
        if _user32.GetAsyncKeyState(VK_MENU) & 0x8000:
            mod_mask |= MOD_ALT
        if _user32.GetAsyncKeyState(VK_CONTROL) & 0x8000:
            mod_mask |= MOD_CONTROL
        if _user32.GetAsyncKeyState(VK_SHIFT) & 0x8000:
            mod_mask |= MOD_SHIFT
        if (_user32.GetAsyncKeyState(VK_LWIN) & 0x8000) or \
           (_user32.GetAsyncKeyState(VK_RWIN) & 0x8000):
            mod_mask |= MOD_WIN

        # 检查每个注册的热键
        for (vk, registered_mod), hotkey_id in list(self._hotkeys.items()):
            key_down = bool(_user32.GetAsyncKeyState(vk) & 0x8000)
            key_sig = (vk, mod_mask)

            if key_down and registered_mod == mod_mask:
                # 按键按下且修饰键匹配，且本周期内未触发过
                if key_sig not in self._pressed:
                    self._pressed.add(key_sig)
                    try:
                        self.hotkey_triggered.emit(hotkey_id)
                    except RuntimeError:
                        # 信号已断开（如窗口已销毁）
                        pass
            elif not key_down:
                # 按键释放，清除按下标记（允许下次按下再次触发）
                self._pressed.discard(key_sig)
