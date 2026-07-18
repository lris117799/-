# core/settings_manager.py
import json
import os

class SettingsManager:
    def __init__(self):
        self.settings_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "settings.json")
        self.default_settings = {
            # 设置版本号（用于设置迁移）
        "settings_version": 2,

            # 通用设置
            "auto_start": False,
            "minimize_to_tray": False,
            "show_main_on_startup": True,
            "desktop_pet_enabled": False,  # 桌宠开关
            
            # 识别设置
        "recognition_interval": 500,
        "recognition_confidence": 0.7,  # nl 和其他识别用的置信度
        "confidence_pollution": 0.75,  # 童话事件用的置信度
        "ocr_confidence": 0.5,  # OCR文字识别置信度阈值
        "enable_background_recognition": True,
            
            # 界面设置
            "ui_scale": "large",  # small: 1280x750, medium: 1450x850, large: 1600x950
            
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
            "floating_window_opacity": 0.7,  # 悬浮窗透明度 (0.1~1.0)
            
            # 全局追踪设置
            "enable_global_tracking": True,  # 默认开启全局污染追踪
            
            # 咕噜球计算数据
            "ball_calculator_data": {},  # 存储咕噜球计算数据 {球名: {before: x, after: y}}
            
            # 框选识别区域
            "recognition_roi": None,  # 框选区域 (x, y, width, height)，None表示全屏识别

            # 血脉识别设置
            "enable_bloodline_recognition": True,  # 血脉识别开关（默认开启）
            "bloodline_roi": None,  # 血脉识别框选区域 (x, y, width, height)，None表示未设置
            
            # 导航地图设置
            "map_update_interval": 3,  # 地图更新间隔（每N帧更新一次）
            "use_real_pointer": True,  # 使用游戏真实指针（否则使用绿色方向指针）
            "resource_icon_size": 24,  # 资源点图标大小（基准像素，随地图缩放变化）
            
            # 多窗口设置
            "selected_window_index": 0,  # 多游戏窗口时，选择使用第几个窗口(从0开始)

            # 热键设置
            "hotkeys": {
                "toggle_passthrough": {"mod": "Ctrl", "key": "N", "vk": 0x4E, "mod_code": 0x0002, "display": "Ctrl+N"},
                "map_toggle_passthrough": {"mod": "Alt", "key": "M", "vk": 0x4D, "mod_code": 0x0001, "display": "Alt+M"},
                "count_plus": {"mod": "", "key": "+", "vk": 0xBB, "mod_code": 0, "display": "+"},
                "count_minus": {"mod": "", "key": "-", "vk": 0xBD, "mod_code": 0, "display": "-"},
                "counter_prev": {"mod": "", "key": "[", "vk": 0xDB, "mod_code": 0, "display": "["},
                "counter_next": {"mod": "", "key": "]", "vk": 0xDD, "mod_code": 0, "display": "]"},
                "nightmare_plus": {"mod": "", "key": "》", "vk": 0xBE, "mod_code": 0, "display": "》"},
                "nightmare_minus": {"mod": "", "key": "《", "vk": 0xBC, "mod_code": 0, "display": "《"},
            },
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
                # 深度合并热键：确保新增的热键默认值不会被旧设置覆盖
                if "hotkeys" in loaded and "hotkeys" in settings:
                    default_hotkeys = settings["hotkeys"]
                    for key, value in default_hotkeys.items():
                        if key not in loaded["hotkeys"]:
                            loaded["hotkeys"][key] = value
                # 版本迁移：旧版血脉识别默认为False，强制升级为True
                # 通过 settings_version 标记，仅在首次升级时强制覆盖
                old_version = loaded.get("settings_version", 0)
                if old_version < 1:
                    # 强制使用新默认值（用户后续可手动关闭）
                    loaded["enable_bloodline_recognition"] = True
                    loaded["settings_version"] = 1
                if old_version < 2:
                    # 童话事件置信度阈值从 0.6 提升到 0.75（减少误识别）
                    loaded["confidence_pollution"] = 0.75
                    loaded["settings_version"] = 2
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
