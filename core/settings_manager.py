# core/settings_manager.py
import json
import os

class SettingsManager:
    def __init__(self):
        self.settings_file = os.path.join(os.path.dirname(__file__), "settings.json")
        self.default_settings = {
            # 通用设置
            "auto_start": False,
            "minimize_to_tray": False,
            "show_main_on_startup": True,
            
            # 识别设置
            "recognition_interval": 500,
            "recognition_confidence": 0.7,
            "enable_background_recognition": True,
            
            # 计数器设置
            "default_target": 80,
            "auto_save_interval": 5,  # 自动保存间隔（分钟）
            "auto_save_progress": True,
            "breakthrough_notification": True,  # 保底通知提醒
            
            # 高级设置
            "enable_detailed_log": False,
            "show_performance_monitor": False,
            
            # 悬浮窗设置
            "floating_window_size": "medium",  # small, medium, large
            
            # 全局追踪设置
            "enable_global_tracking": True,  # 默认开启全局污染追踪
            
            # 咕噜球计算数据
            "ball_calculator_data": {},  # 存储咕噜球计算数据 {球名: {before: x, after: y}}
            
            # 框选识别区域
            "recognition_roi": None  # 框选区域 (x, y, width, height)，None表示全屏识别
        }
        self.settings = self.load_settings()
    
    def load_settings(self):
        """加载设置"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                # 合并默认设置，确保新字段存在
                settings = self.default_settings.copy()
                settings.update(loaded)
                return settings
            except Exception as e:
                print(f"加载设置失败: {e}，使用默认设置")
                return self.default_settings.copy()
        return self.default_settings.copy()
    
    def save_settings(self):
        """保存设置"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存设置失败: {e}")
            return False
    
    def get(self, key, default=None):
        """获取设置值"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """设置值"""
        self.settings[key] = value
    
    def reset_to_default(self):
        """恢复默认设置"""
        self.settings = self.default_settings.copy()
        self.save_settings()
