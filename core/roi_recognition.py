# core/roi_recognition.py
"""
坐标识别模块 - 独立线程运行
使用用户框选的固定坐标区域进行识别,与默认ROI完全隔离
"""
import time
import threading
import cv2
import numpy as np
from PySide6.QtCore import Signal, QObject
from core.game_capture import GameCapture
from core.settings_manager import SettingsManager


class RoiRecognitionWorker(QObject):
    """坐标识别工作线程"""
    
    # 信号定义 - 与ScreenshotWorker保持一致
    recognition_result = Signal(dict)  # {xt_detected, recognized_names, xt10_detected}
    error_occurred = Signal(str)  # 错误信息
    status_changed = Signal(str)  # 状态变化
    
    def __init__(self):
        super().__init__()
        self.capture = GameCapture()
        self.settings = SettingsManager()
        self.is_running = False
        self.thread = None
        self.current_battle_lkwg = None  # 当前战斗中的精灵名（由主窗口同步）
        self.debug_image_saved = False  # 标记调试图是否已保存
    
    def set_current_battle(self, battle_name):
        """设置当前战斗状态（与ScreenshotWorker保持一致）"""
        self.current_battle_lkwg = battle_name
        
    def start(self):
        """启动识别线程"""
        if self.is_running:
            return
        
        # 检查是否启用坐标识别
        if not self.settings.get("enable_roi_recognition", False):
            self.status_changed.emit("❌ 未启用坐标识别模式")
            return
        
        # 检查是否有框选坐标
        roi = self.settings.get("recognition_roi")
        if not roi:
            self.status_changed.emit("❌ 未设置框选区域,请先在设置中框选")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.status_changed.emit("✅ 坐标识别已启动")
        
    def stop(self):
        """停止识别线程"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        self.status_changed.emit("⏹️ 坐标识别已停止")
        
    def _run_loop(self):
        """识别主循环 - 直接调用OpenCV匹配,不使用多尺度探测"""
        interval = self.settings.get("recognition_interval", 500) / 1000.0
        
        # 打印启动信息
        roi_config = self.settings.get("recognition_roi")
        print(f"🎯 [坐标识别] 线程启动, ROI配置: {roi_config}")
        
        while self.is_running:
            try:
                # 获取框选区域配置
                roi_config = self.settings.get("recognition_roi")
                if not roi_config:
                    time.sleep(interval)
                    continue
                
                x = roi_config["x"]
                y = roi_config["y"]
                w = roi_config["width"]
                h = roi_config["height"]
                
                # 判断是比例坐标还是绝对坐标
                # 比例坐标: x, y 都小于1.0（范围0-1）
                # 绝对坐标: x 或 y >= 1.0，表示物理像素
                is_ratio = (x < 1.0 and y < 1.0)
                
                if is_ratio:
                    # 比例坐标: 使用capture_window截图(支持后台)
                    screenshot = self.capture.capture_window()
                    if screenshot is None:
                        time.sleep(interval)
                        continue
                    
                    img_h, img_w = screenshot.shape[:2]
                    pixel_x = int(x * img_w)
                    pixel_y = int(y * img_h)
                    pixel_w = int(w * img_w)
                    pixel_h = int(h * img_h)
                    
                    print(f"📐 比例坐标转换: ({x},{y},{w},{h}) -> ({pixel_x},{pixel_y},{pixel_w},{pixel_h})")
                else:
                    # 客户区相对坐标(物理像素): 使用capture_window截图(支持后台)
                    # ScreenSelector返回的是客户区相对坐标，不是屏幕绝对坐标
                    screenshot = self.capture.capture_window()
                    if screenshot is None:
                        time.sleep(interval)
                        continue
                    
                    # 直接使用物理像素坐标（ScreenSelector已处理DPI缩放）
                    pixel_x = int(x)
                    pixel_y = int(y)
                    pixel_w = int(w)
                    pixel_h = int(h)
                    
                    # 验证坐标是否在截图范围内
                    img_h, img_w = screenshot.shape[:2]
                    if pixel_x < 0 or pixel_y < 0 or pixel_x + pixel_w > img_w or pixel_y + pixel_h > img_h:
                        print(f"⚠️ ROI坐标超出截图范围! 截图尺寸: {img_w}x{img_h}, ROI: ({pixel_x},{pixel_y},{pixel_w},{pixel_h})")
                        time.sleep(interval)
                        continue
                
                # 保存全图+ROI红框调试(仅首次)
                if not self.debug_image_saved:
                    import os
                    debug_full = screenshot.copy()
                    cv2.rectangle(debug_full, (pixel_x, pixel_y), (pixel_x+pixel_w, pixel_y+pixel_h), (0, 0, 255), 3)
                    debug_full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "debug_full_with_roi.png")
                    cv2.imwrite(debug_full_path, debug_full)
                    print(f"📸 全图+ROI红框已保存: {debug_full_path}, 尺寸: {screenshot.shape}, ROI: ({pixel_x},{pixel_y},{pixel_w},{pixel_h})")
                    self.debug_image_saved = True
                
                # 关键简化：直接使用已有的 detect_xt_icon 和 detect_xt10，传入 roi 参数！
                roi = (pixel_x, pixel_y, pixel_w, pixel_h)
                
                # 识别逻辑与默认识别完全一致:
                # 1. 先检测xt图标 - 传入roi参数，只在指定区域搜索
                xt_detected = self.capture.detect_xt_icon(image=screenshot, roi=roi)
                print(f"🔍 xt检测结果: {xt_detected}")
                
                # 2. 战斗持续阶段：有战斗状态或xt存在时都要OCR
                recognized_names = []
                should_ocr = xt_detected or (self.current_battle_lkwg is not None)
                if should_ocr:
                    # OCR识别时也传入roi参数
                    pokemon_names = self.capture.recognize_pokemon_name(image=screenshot, roi=roi)
                    if pokemon_names:
                        recognized_names.extend(pokemon_names)
                
                # 3. 检测xt10（只有OCR识别到名字才检测）- 也传入roi参数
                xt10_detected = False
                if recognized_names:
                    xt10_detected = self.capture.detect_xt10(image=screenshot, roi=roi)
                
                # 发射结果(与ScreenshotWorker完全一致的结构)
                result = {
                    'xt_detected': xt_detected,
                    'recognized_names': recognized_names,
                    'xt10_detected': xt10_detected
                }
                self.recognition_result.emit(result)
                
                time.sleep(interval)
                
            except Exception as e:
                self.error_occurred.emit(f"坐标识别错误: {str(e)}")
                import traceback
                traceback.print_exc()
                time.sleep(interval)
    
    def _match_xt_direct(self, image):
        """直接匹配xt图标,不使用多尺度探测（保留用于兼容性）"""
        if self.capture.xt_template is None:
            return False
        
        threshold = 0.7
        result = cv2.matchTemplate(image, self.capture.xt_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            return True
        return False
    
    def _match_xt10_direct(self, image):
        """直接匹配xt10图标,不使用多尺度探测（保留用于兼容性）"""
        if self.capture.xt10_template is None:
            return False
        
        threshold = 0.65
        result = cv2.matchTemplate(image, self.capture.xt10_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        currently_detected = max_val >= threshold
        
        # 防重复计数逻辑
        if currently_detected and not self.capture.xt10_was_detected:
            self.capture.xt10_was_detected = True
            return True
        elif not currently_detected and self.capture.xt10_was_detected:
            self.capture.xt10_was_detected = False
        
        return False
