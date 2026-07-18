# core/keyboard_hook.py
"""
全局键盘钩子 - 使用低级键盘钩子 (WH_KEYBOARD_LL)

相比 RegisterHotKey 的优势：
- 不独占按键：按键事件会继续传递给当前焦点窗口，用户在浏览器/聊天框等地方
  仍可正常使用 +、-、[、] 等字符
- 支持任意按键组合
"""
import ctypes
import threading
from ctypes import wintypes
from PySide6.QtCore import QObject, Signal

# Windows 常量
WH_KEYBOARD_LL = 13
HC_ACTION = 0
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_QUIT = 0x0012

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


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('vkCode', wintypes.DWORD),
        ('scanCode', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_void_p),
    ]


# 低级钩子回调函数签名
HOOKPROC = ctypes.CFUNCTYPE(
    ctypes.c_long,    # LRESULT
    ctypes.c_int,     # int code
    wintypes.WPARAM,  # wParam
    wintypes.LPARAM,  # lParam
)

# 预先设置 API 参数类型，避免 ctypes 默认转换导致的溢出
_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

_user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD
]
_user32.SetWindowsHookExW.restype = wintypes.HHOOK

_user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
_user32.UnhookWindowsHookEx.restype = wintypes.BOOL

_user32.CallNextHookEx.argtypes = [
    wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
]
_user32.CallNextHookEx.restype = ctypes.c_long  # LRESULT

_user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
_user32.GetAsyncKeyState.restype = ctypes.c_short

_user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT
]
_user32.GetMessageW.restype = wintypes.BOOL

_user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
_user32.TranslateMessage.restype = wintypes.BOOL

_user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
_user32.DispatchMessageW.restype = ctypes.c_long

_user32.PostThreadMessageW.argtypes = [
    wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
]
_user32.PostThreadMessageW.restype = wintypes.BOOL

_kernel32.GetCurrentThreadId.argtypes = []
_kernel32.GetCurrentThreadId.restype = wintypes.DWORD


class KeyboardHook(QObject):
    """全局键盘钩子（非阻塞）

    用法：
        hook = KeyboardHook(parent)
        hook.hotkey_triggered.connect(handler)  # handler 接收 hotkey_id 参数
        hook.register_hotkey(vk, mod_code, hotkey_id)
        hook.start()
        # ...
        hook.stop()
    """

    # 触发热键时发出，参数为注册时提供的 hotkey_id
    hotkey_triggered = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hook = None
        self._hook_proc = None  # 保持回调引用防止被 GC
        self._thread = None
        self._thread_id = 0
        self._running = threading.Event()
        self._lock = threading.Lock()
        # {(vk, mod_mask): hotkey_id}
        self._hotkeys = {}
        # 防止按键长按重复触发（记录已按下的键）
        self._pressed = set()

    def register_hotkey(self, vk, mod_code, hotkey_id):
        """注册一个热键

        :param vk: 虚拟键码
        :param mod_code: 修饰键代码（与 RegisterHotKey 的 MOD_* 一致）
        :param hotkey_id: 热键 ID，会通过 hotkey_triggered 信号传回
        """
        with self._lock:
            self._hotkeys[(vk, mod_code)] = hotkey_id

    def unregister_all(self):
        """清空所有已注册的热键"""
        with self._lock:
            self._hotkeys.clear()
            self._pressed.clear()

    def start(self):
        """启动钩子线程"""
        if self._thread and self._thread.is_alive():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """停止钩子线程"""
        self._running.clear()
        if self._thread_id:
            # 向钩子线程发送 WM_QUIT 唤醒 GetMessage
            _user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(timeout=2)
        self._thread = None
        self._thread_id = 0

    def _run(self):
        """钩子线程主函数"""
        self._thread_id = _kernel32.GetCurrentThreadId()

        def low_level_handler(code, wParam, lParam):
            if code == HC_ACTION and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                vk = kb.vkCode

                # 获取当前修饰键状态
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

                # 查找匹配的热键
                with self._lock:
                    hotkey_id = self._hotkeys.get((vk, mod_mask))
                    # 防止长按重复触发
                    key_sig = (vk, mod_mask)
                    if hotkey_id is not None and key_sig not in self._pressed:
                        self._pressed.add(key_sig)
                        # 通过信号通知主线程
                        try:
                            self.hotkey_triggered.emit(hotkey_id)
                        except RuntimeError:
                            # 信号已断开（如窗口已销毁）
                            pass

            elif code == HC_ACTION and wParam in (0x0101, 0x0105):  # WM_KEYUP / WM_SYSKEYUP
                # 释放按键时清除按下标记
                kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                vk = kb.vkCode
                with self._lock:
                    # 清除该 vk 对应的所有按下标记
                    self._pressed = {k for k in self._pressed if k[0] != vk}

            # 调用下一个钩子（不拦截按键，让事件继续传递）
            # 显式构造 WPARAM/LPARAM 确保类型正确
            return _user32.CallNextHookEx(
                wintypes.HHOOK(self._hook),
                ctypes.c_int(code),
                wintypes.WPARAM(wParam),
                wintypes.LPARAM(lParam),
            )

        # 保存回调引用，防止被 GC
        self._hook_proc = HOOKPROC(low_level_handler)
        self._hook = _user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._hook_proc, None, 0
        )

        if not self._hook:
            return

        # 消息循环（必须，否则钩子不会工作）
        msg = wintypes.MSG()
        while self._running.is_set():
            ret = _user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:  # 0=WM_QUIT, -1=错误
                break
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))

        _user32.UnhookWindowsHookEx(self._hook)
        self._hook = None
