# core/logger.py
import sys
from datetime import datetime
from collections import deque

class Logger:
    """日志管理器 - 内存缓冲模式"""
    
    _instance = None
    _enabled = False
    _callbacks = []  # 日志回调列表
    _max_buffer = 1000  # 最大缓冲行数
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._buffer = deque(maxlen=cls._max_buffer)
        return cls._instance
    
    def set_enabled(self, enabled):
        """启用/禁用日志"""
        self._enabled = enabled
        if enabled:
            self._buffer.clear()
            self.log("=== 调试日志开始 ===")
            self.log(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.log(f"打包状态: {'是' if getattr(sys, 'frozen', False) else '否'}")
    
    def register_callback(self, callback):
        """注册日志回调函数"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def unregister_callback(self, callback):
        """注销日志回调函数"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def log(self, message):
        """记录日志"""
        if not self._enabled:
            return
        
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_line = f"[{timestamp}] {message}"
        
        # 保存到缓冲区
        self._buffer.append(log_line)
        
        # 通知所有回调(只在主线程调用,避免跨线程崩溃)
        import threading
        main_thread = threading.main_thread()
        if threading.current_thread() == main_thread:
            for callback in self._callbacks:
                try:
                    callback(log_line)
                except:
                    pass
    
    def get_buffer(self):
        """获取日志缓冲区内容"""
        return list(self._buffer)
    
    def clear_buffer(self):
        """清空缓冲区"""
        self._buffer.clear()


# 全局日志实例
logger = Logger()
