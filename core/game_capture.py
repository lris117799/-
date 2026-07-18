    # core/game_capture.py
import cv2
import numpy as np

# ── OpenCV Unicode 路径支持 ──
def _cv2_imread(path, flags=cv2.IMREAD_COLOR):
    """支持中文路径的 cv2.imread"""
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), flags)

def _cv2_imwrite(path, img, params=None):
    """支持中文路径的 cv2.imwrite"""
    ext = os.path.splitext(path)[1].lower()
    ext = ext if ext else '.png'
    cv2.imencode(ext, img, params or [])[1].tofile(path)

import win32gui
import win32ui
import win32con
import win32process
from rapidocr_onnxruntime import RapidOCR
import os
import sys
import threading
from ctypes import windll
from .evolution_manager import EvolutionManager
from .logger import logger
from PySide6.QtCore import QThread, Signal


def _get_resource_path(relative_path):
    """获取资源文件的正确路径，支持打包后运行"""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(sys.executable)
        return os.path.join(base_path, relative_path)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, relative_path)

class GameCapture:
    # 血脉类型关键字（OCR识别用）
    BLOODLINE_TYPES = ["奇异", "污染", "混乱", "异色"]

    def __init__(self, window_title="洛克王国：世界"):
        self.window_title = window_title
        self.hwnd = None
        self.ocr_engine = None
        self.evolution_manager = EvolutionManager()
        self.pokemon_names = self._load_pokemon_names()
        
        # 童话事件检测状态
        self.nightmare_detected_count = 0
        self.last_nightmare_time = 0
        self.nightmare_cooldown = 6  # 6秒冷却

        # 窗口捕获缓存（避免每次重复 GDI 调用）
        self._capture_cache = {'valid': False}
        self._capture_lock = threading.Lock()  # 防止多线程同时调用 GDI 导致死锁

        # OCR优化参数
        self.ocr_last_hash = None
        self.ocr_prewarmed = False
        
        # OCR启停控制状态
        self.ocr_enabled = False  # OCR是否启用
        self.battle_start_time = 0  # 战斗开始时间（用于6秒计时）
        self.nl_trigger_time = 0  # nl触发时间（用于2秒计时）
        self.last_valid_recognition_time = 0  # 最后一次识别到有效文本的时间
        self.ocr_timeout = 6.0  # 6秒超时（战斗进行中）
        self.nl_trigger_timeout = 2.0  # 2秒触发超时（nl检测到后等待四叶草铅绘）
        self.nl_was_detected = False  # nl是否曾经被检测到（用于防止重复触发）
        self.nl_detection_failed = False  # nl触发是否失败（2秒内未检测到四叶草铅绘）
        self.battle_started = False  # 战斗是否已正式开始（检测到四叶草铅绘后）
        
        # 缓存模板图片（避免重复加载）
        self.nightmare_template = None  # nightmare_template模板
        self.nl_template = None  # nl.png 触发模板
        self.templates_loaded = False  # 标记模板是否已加载
        
        # 原始模板副本（用于多尺度探测）
        self.nightmare_template_original = None
        self.nl_template_original = None
        
        # 智能缓存最佳缩放比例
        self.nightmare_best_scale = None  # nightmare_template最佳缩放比例
        self.nl_best_scale = None  # nl.png最佳缩放比例
        self.scale_probe_count = 0  # 探测计数器

        # 预保存缩放后的模板(避免每次resize)
        self.nightmare_cached_template = None  # nightmare_template缩放后模板
        self.nl_cached_template = None  # nl.png缩放后模板
        
        # OCR：精灵名称匹配缓存
        self._name_match_cache = {}  # {识别文本: 匹配结果}
        self._cache_hit_count = 0
        self._cache_miss_count = 0
        
        # 立即加载模板（支持打包后运行）
        logger.log("🔄 初始化加载模板...")
        self._load_templates()
    
    def _load_pokemon_names(self):
        """加载宠物名称词库（从进化链中提取所有形态）"""
        return list(self.evolution_manager.evolution_chains.keys())
    
    def _load_templates(self):
        """加载并缓存模板图片(保持原始尺寸)"""
        import sys

        # 获取资源目录（支持打包环境）
        image_dir = _get_resource_path("image")

        logger.log(f"🔍 模板目录路径: {image_dir}")
        logger.log(f"🔍 frozen={getattr(sys, 'frozen', False)}, MEIPASS={getattr(sys, '_MEIPASS', 'N/A')}")
            
        # 加载nightmare_template.png - 保持原始尺寸
        nightmare_path = os.path.join(image_dir, "nightmare_template.png")
        if os.path.exists(nightmare_path):
            self.nightmare_template_original = _cv2_imread(nightmare_path)
            if self.nightmare_template_original is not None:
                h, w = self.nightmare_template_original.shape[:2]
                self.nightmare_template = self.nightmare_template_original.copy()
                logger.log(f"✅ 已缓存nightmare_template.png模板 (原始尺寸: {w}x{h})")
        
        # 加载nl.png - 童话事件触发模板
        nl_path = os.path.join(image_dir, "nl.png")
        if os.path.exists(nl_path):
            self.nl_template_original = _cv2_imread(nl_path, cv2.IMREAD_COLOR)
            if self.nl_template_original is not None:
                h, w = self.nl_template_original.shape[:2]
                self.nl_template = self.nl_template_original.copy()
                logger.log(f"✅ 已缓存nl.png模板 (原始尺寸: {w}x{h})")
            else:
                logger.log(f"⚠️ nl.png加载失败")
        else:
            logger.log(f"⚠️ nl.png不存在")

        # 初始化完成后标记模板已加载
        self.templates_loaded = True

    def reload_templates(self):
        """重新加载所有模板图片（用于更换图片后不重启程序）"""
        logger.log("🔄 重新加载模板图片...")
        self._load_templates()
        logger.log("✅ 模板重新加载完成")
    
    def _get_dpi_scale(self):
        """获取DPI缩放因子"""
        # 尝试多种方式获取 DPI，并输出调试信息
        debug_info = []
        scale = 1.0
        
        # 方法1: 使用 GetDpiForWindow (需要窗口句柄，最准确)
        if self.hwnd != 0:
            try:
                dpi = windll.user32.GetDpiForWindow(self.hwnd)
                scale = dpi / 96.0
                debug_info.append(f"✅ GetDpiForWindow({self.hwnd})= {scale:.2f}x")
                logger.log(f"🔍 {debug_info[-1]}")
                return scale
            except Exception as e:
                debug_info.append(f"❌ GetDpiForWindow 失败: {e}")
                logger.log(f"⚠️ {debug_info[-1]}")
        else:
            debug_info.append(f"⏭️ GetDpiForWindow 跳过（self.hwnd=0）")
        
        # 方法2: 使用 GetDeviceCaps (系统默认 DPI)
        try:
            dc = windll.user32.GetDC(0)
            dpi_x = windll.gdi32.GetDeviceCaps(dc, 88)  # LOGPIXELSX
            dpi_y = windll.gdi32.GetDeviceCaps(dc, 90)  # LOGPIXELSY
            windll.user32.ReleaseDC(0, dc)
            scale = max(dpi_x, dpi_y) / 96.0
            debug_info.append(f"✅ GetDeviceCaps: {dpi_x}x{dpi_y} DPI = {scale:.2f}x")
            logger.log(f"🔍 {debug_info[-1]}")
            return scale
        except Exception as e:
            debug_info.append(f"❌ GetDeviceCaps 失败: {e}")
            logger.log(f"⚠️ {debug_info[-1]}")
        
        # 方法3: 使用 GetScaleFactorForDevice
        try:
            scale_factor = windll.shcore.GetScaleFactorForDevice(0)
            scale = scale_factor / 100.0
            debug_info.append(f"✅ GetScaleFactorForDevice: {scale_factor}% = {scale:.2f}x")
            logger.log(f"🔍 {debug_info[-1]}")
            return scale
        except Exception as e:
            debug_info.append(f"❌ GetScaleFactorForDevice 失败: {e}")
            logger.log(f"⚠️ {debug_info[-1]}")
        
        # 默认返回 1.0
        debug_info.append(f"⚠️ 所有方法失败，返回默认值 1.0x")
        logger.log(f"⚠️ {debug_info[-1]}")
        logger.log(f"📋 DPI 获取调试信息: {' | '.join(debug_info)}")
        return 1.0

    def find_window(self):
        """查找游戏窗口(通过进程名过滤,只匹配NRC-Win64-Shipping.exe)"""
        import psutil
        
        # 如果已有窗口句柄且窗口仍然有效,直接返回
        if self.hwnd != 0:
            try:
                if win32gui.IsWindow(self.hwnd) and win32gui.IsWindowVisible(self.hwnd):
                    return True
            except:
                pass
            # 窗口无效,需要重新查找
            logger.log(f"⚠️ 窗口句柄失效,重新查找")
            self.hwnd = 0
        
        try:
            # 收集所有匹配进程的PID（支持双开）
            target_pids = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] == 'NRC-Win64-Shipping.exe':
                        target_pids.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not target_pids:
                logger.log(f"❌ 未找到NRC-Win64-Shipping.exe进程")
                self.hwnd = 0
                return False
            
            logger.log(f"✅ 共找到 {len(target_pids)} 个游戏进程: PID={target_pids}")
            # 使用第一个PID作为主PID（用于后续标题精确匹配）
            target_pid = target_pids[0]
            
            # 直接通过标题查找窗口
            self.hwnd = win32gui.FindWindow(None, self.window_title)
            
            # 验证找到的窗口是否属于任一匹配进程
            if self.hwnd != 0:
                try:
                    _, found_pid = win32process.GetWindowThreadProcessId(self.hwnd)
                    if found_pid not in target_pids:
                        logger.log(f"⚠️ 窗口不属于目标进程 (期望PID={target_pids}, 实际PID={found_pid})")
                        self.hwnd = 0  # 重置，进入模糊匹配流程
                except:
                    self.hwnd = 0
            
            if self.hwnd == 0:
                # 尝试模糊匹配（收集所有符合条件的窗口，属于任一目标进程）
                def callback(hwnd, extra):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if self.window_title in title:
                            # 验证是否属于任一游戏进程
                            try:
                                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                                if pid in target_pids:
                                    extra.append(hwnd)
                            except:
                                pass
                    return True
                
                matched_hwnds = []
                win32gui.EnumWindows(callback, matched_hwnds)
                if matched_hwnds:
                    selected_index = self.settings_manager.get("selected_window_index", 0) if hasattr(self, 'settings_manager') else 0
                    if selected_index >= len(matched_hwnds):
                        selected_index = 0
                        if hasattr(self, 'settings_manager'):
                            self.settings_manager.set("selected_window_index", 0)
                    self.hwnd = matched_hwnds[selected_index]
                    logger.log(f"✅ 找到 {len(matched_hwnds)} 个游戏窗口，使用第 {selected_index + 1} 个 (共{len(matched_hwnds)}个)")
            
            if self.hwnd != 0:
                logger.log(f"✅ 找到游戏窗口: HWND={self.hwnd}")
                
                # 如果找到的是父窗口，尝试查找子窗口（游戏主渲染窗口）
                def find_child(hwnd, extra):
                    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                    if style & win32con.WS_CHILD:
                        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                        width = right - left
                        height = bottom - top
                        if width > 100 and height > 100:
                            extra.append(hwnd)
                    return True
                
                child_windows = []
                win32gui.EnumChildWindows(self.hwnd, find_child, child_windows)
                
                if child_windows:
                    child_windows.sort(
                        key=lambda h: (lambda r: (r[2]-r[0])*(r[3]-r[1]))(win32gui.GetWindowRect(h)),
                        reverse=True
                    )
                    logger.log(f"🔍 找到 {len(child_windows)} 个子窗口，使用最大的")
                    self.hwnd = child_windows[0]
            else:
                logger.log(f"❌ 未找到游戏窗口")
                self.hwnd = 0
        except Exception as e:
            logger.log(f"❌ 查找窗口失败: {e}")
            import traceback
            traceback.print_exc()
            self.hwnd = 0
        
        # 找到窗口后加载模板
        if self.hwnd != 0:
            current_dpi = self._get_dpi_scale()
            if not self.templates_loaded or abs(current_dpi - (self.last_dpi_scale or 0)) > 0.01:
                logger.log(f"🔄 DPI变化: {self.last_dpi_scale} -> {current_dpi}, 重新加载模板")
                self._load_templates()
                self.templates_loaded = True
                self.last_dpi_scale = current_dpi
        
        return self.hwnd != 0
    
    def get_available_windows(self):
        """获取所有可用的游戏窗口列表
        :return: [(index, hwnd, title), ...]
        """
        import psutil

        # 收集所有匹配进程的PID（支持双开）
        target_pids = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == 'NRC-Win64-Shipping.exe':
                    target_pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not target_pids:
            return []

        windows = []
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if self.window_title in title:
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        if pid in target_pids:
                            extra.append(hwnd)
                    except:
                        pass
            return True

        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        for i, hwnd in enumerate(hwnds):
            title = win32gui.GetWindowText(hwnd)
            windows.append((i, hwnd, title))
        return windows

    def capture_window(self, roi=None, return_raw=False):
        """捕获游戏窗口画面（支持后台）
        :param roi: 框选区域 (x, y, width, height)，如果为None则全屏截图
        :param return_raw: True=返回BGRA原始格式（跳过颜色转换，约省15-30ms）
        :return: BGR或BGRA格式的numpy数组
        """
        # 验证窗口句柄是否仍然有效
        if self.hwnd != 0:
            try:
                if not win32gui.IsWindow(self.hwnd) or not win32gui.IsWindowVisible(self.hwnd):
                    logger.log("⚠️ 窗口已关闭或不可见，重置句柄")
                    self.hwnd = 0
            except:
                self.hwnd = 0
        
        if not self.hwnd:
            if not self.find_window():
                logger.log("❌ 未找到游戏窗口")
                return None
        
        # 缓存窗口尺寸，避免每次重复调用 GDI 函数
        cache = self._capture_cache
        try:
            if not cache['valid']:
                left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
                point = (left, top)
                screen_point = win32gui.ClientToScreen(self.hwnd, point)
                cache['client_left'] = screen_point[0]
                cache['client_top'] = screen_point[1]
                cache['logical_width'] = right - left
                cache['logical_height'] = bottom - top
                cache['dpi_scale'] = self._get_dpi_scale()
                cache['valid'] = True
                if cache['dpi_scale'] != 1.0:
                    logger.log(f"📐 DPI缩放: {cache['dpi_scale']:.2f}x, 尺寸: {cache['logical_width']}x{cache['logical_height']}")
                logger.log(f"📍 窗口坐标缓存: ({cache['client_left']}, {cache['client_top']}), {cache['logical_width']}x{cache['logical_height']}")
            
            client_left = cache['client_left']
            client_top = cache['client_top']
            logical_width = cache['logical_width']
            logical_height = cache['logical_height']

        except Exception as e:
            cache['valid'] = False
            logger.log(f"⚠️ GetClientRect失败，使用GetWindowRect: {e}")
            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            client_left, client_top, client_right, client_bottom = left, top, right, bottom
            logical_width = right - left
            logical_height = bottom - top
            logger.log(f"📍 窗口屏幕坐标: ({client_left}, {client_top}), 尺寸: {logical_width}x{logical_height}")
        

        
        try:
            # GDI 截图（加锁：非线程安全，多线程同时调用 GetWindowDC 会死锁）
            with self._capture_lock:
                hwnd_dc = win32gui.GetWindowDC(self.hwnd)
                mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
                save_dc = mfc_dc.CreateCompatibleDC()

                bitmap = win32ui.CreateBitmap()
                # PrintWindow需要使用逻辑像素尺寸
                bitmap.CreateCompatibleBitmap(mfc_dc, logical_width, logical_height)
                save_dc.SelectObject(bitmap)

                # 先尝试参数2（PW_RENDERFULLCONTENT）
                result = windll.user32.PrintWindow(self.hwnd, save_dc.GetSafeHdc(), 2)

                if result == 0:
                    # 失败则尝试参数0
                    result = windll.user32.PrintWindow(self.hwnd, save_dc.GetSafeHdc(), 0)

                bmpstr = bitmap.GetBitmapBits(True)

                # 快速检查是否截到有效数据
                img_temp = np.frombuffer(bmpstr, dtype=np.uint8).reshape((logical_height, logical_width, 4))
                cy, cx = logical_height // 2, logical_width // 2
                sample = img_temp[cy-2:cy+3, cx-2:cx+3, :3] if logical_height > 4 and logical_width > 4 else img_temp[:, :, :3]
                mean_val = np.mean(sample)

                # 如果平均亮度接近0或255，说明截图失败，降级到BitBlt
                if mean_val < 10 or mean_val > 245:

                    save_dc.DeleteDC()
                    win32gui.ReleaseDC(self.hwnd, hwnd_dc)
                    win32gui.DeleteObject(bitmap.GetHandle())

                    # 降级方案：使用BitBlt（需要窗口在前台）
                    screen_dc = win32gui.GetDC(0)
                    mfc_screen = win32ui.CreateDCFromHandle(screen_dc)
                    save_dc = mfc_screen.CreateCompatibleDC()

                    bitmap2 = win32ui.CreateBitmap()
                    bitmap2.CreateCompatibleBitmap(mfc_screen, logical_width, logical_height)
                    save_dc.SelectObject(bitmap2)
                    save_dc.BitBlt((0, 0), (logical_width, logical_height), mfc_screen, (client_left, client_top), win32con.SRCCOPY)

                    bmpstr = bitmap2.GetBitmapBits(True)
                    img_temp = np.frombuffer(bmpstr, dtype=np.uint8).reshape((logical_height, logical_width, 4))

                    win32gui.DeleteObject(bitmap2.GetHandle())
                    save_dc.DeleteDC()
                    win32gui.ReleaseDC(0, screen_dc)
                else:
                    # PrintWindow成功
                    save_dc.DeleteDC()
                    win32gui.ReleaseDC(self.hwnd, hwnd_dc)
                    win32gui.DeleteObject(bitmap.GetHandle())
            
            img = img_temp
            
            if not return_raw:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # 如果指定了roi，裁剪图像
            if roi:
                x, y, w, h = roi

                relative_x = x - client_left
                relative_y = y - client_top

                dpi_scale = self._capture_cache.get('dpi_scale', 1.0)
                h_img, w_img = img.shape[:2]

                if dpi_scale != 1.0:
                    physical_relative_x = int(relative_x * dpi_scale)
                    physical_relative_y = int(relative_y * dpi_scale)
                    physical_w = int(w * dpi_scale)
                    physical_h = int(h * dpi_scale)

                    relative_x = max(0, min(physical_relative_x, w_img - 1))
                    relative_y = max(0, min(physical_relative_y, h_img - 1))
                    w = min(physical_w, w_img - relative_x)
                    h = min(physical_h, h_img - relative_y)
                else:
                    relative_x = max(0, min(relative_x, w_img - 1))
                    relative_y = max(0, min(relative_y, h_img - 1))
                    w = min(w, w_img - relative_x)
                    h = min(h, h_img - relative_y)

                if w > 0 and h > 0:
                    img = img[relative_y:relative_y+h, relative_x:relative_x+w]
                else:
                    logger.log(f"❌ ROI超出图像范围!")
            
            return img
        except Exception as e:
            logger.log(f"❌ 截图失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def init_ocr(self):
        """初始化OCR引擎（极速优化版）"""
        if self.ocr_engine is None:
            import sys
            
            cpu_nums = os.cpu_count() or 4
            
            ocr_config = {
                'use_angle_cls': False,
                'rec_batch_num': 1,
                'rec_img_shape': [3, 32, 320],
                'det_db_score_mode': 'fast',
                'det_db_unclip_ratio': 1.5,
                'det_db_box_thresh': 0.6,
                'det_db_thresh': 0.35,
                'det_limit_side_len': 160,
                'intra_op_num_threads': min(2, cpu_nums),
                'inter_op_num_threads': 1,
            }
            self.ocr_engine = RapidOCR(**ocr_config)
            self.ocr_prewarmed = False
            logger.log("✅ OCR引擎初始化成功（极速版）")

    def prewarm_ocr(self):
        """预热OCR引擎（启动时调用，避免运行时首卡顿）"""
        if self.ocr_engine is None:
            self.init_ocr()
        if self.ocr_prewarmed:
            return
        try:
            dummy = np.zeros((100, 400, 3), dtype=np.uint8)
            self.ocr_engine(dummy)
            self.ocr_prewarmed = True
            logger.log("✅ OCR引擎预热完成")
        except Exception as e:
            logger.log(f"⚠️ OCR预热失败: {e}")
    
    def recognize_pokemon_name(self, image=None, roi=None, debug=False):
        """
        识别精灵名称
        :param image: 截图图像,如果为None则自动捕获
        :param roi: 感兴趣区域 (x, y, w, h),如果为None则使用配置的框选区域或默认区域
        :param debug: 是否保存调试图片（绘制ROI红框）
        :return: 识别到的文本列表
        """
        if image is None:
            # 如果没有指定roi，尝试从配置中加载
            if roi is None and hasattr(self, 'settings_manager'):
                saved_roi = self.settings_manager.get("recognition_roi")
                if saved_roi:
                    roi = (saved_roi['x'], saved_roi['y'], saved_roi['width'], saved_roi['height'])
                    logger.log(f"📍 使用配置的框选区域: {roi}")
            
            image = self.capture_window(roi)
            
        if image is None:
            return []
        
        # 如果传入了roi参数，需要裁剪图像
        if roi is not None:
            roi_x, roi_y, roi_w, roi_h = roi
            image = image[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]
        elif roi is None:
            # 只有当image由capture_window截取且roi为None时,才应用默认ROI
            h, w = image.shape[:2]
            # 右上角区域: 从右侧60%开始到右侧,顶部15%高度
            roi_x = int(w * 0.4) + 100
            roi_y = 0
            roi_w = int(w * 0.6) - 100
            roi_h = int(h * 0.15)
            roi = (roi_x, roi_y, roi_w, roi_h)
            
            # 默认识别模式：首次调用时保存调试图
            if not hasattr(self, '_default_roi_debug_saved'):
                import cv2
                debug_image = image.copy()
                cv2.rectangle(debug_image, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (0, 0, 255), 3)
                debug_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "debug_roi.png")
                _cv2_imwrite(debug_path, debug_image)
                logger.log(f"📸 ROI调试图已保存: {debug_path} (尺寸:{w}x{h}, ROI:{roi})")
                self._default_roi_debug_saved = True
            
            # 裁剪图像
            image = image[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]
        
        # 初始化OCR
        self.init_ocr()

        # 跳过未变化的帧：用简单哈希检测画面是否有变化
        import struct
        simple_hash = hash(image[::8, ::8].tobytes())
        if simple_hash == self.ocr_last_hash and self.ocr_last_hash is not None:
            return []
        self.ocr_last_hash = simple_hash

        # 执行OCR识别（det_limit_side_len=160内部处理缩放）
        result, elapse = self.ocr_engine(image)

        if result:
            ocr_confidence = self.settings_manager.get("ocr_confidence", 0.5) if hasattr(self, 'settings_manager') else 0.5

            high_confidence_texts = [item[1] for item in result if item[2] >= ocr_confidence]
            all_texts = [item[1] for item in result]

            matched = self._match_pokemon_names(high_confidence_texts)
            if matched and all_texts:
                elapse_ms = elapse if isinstance(elapse, (int, float)) else (elapse[0] if isinstance(elapse, (list, tuple)) and len(elapse) > 0 else 0)
                logger.log(f"📝 OCR: {', '.join(all_texts[:3])} → {', '.join(matched)} ({elapse_ms*1000:.0f}ms)")
            return matched
        else:
            self.ocr_last_hash = None

        return []

    def recognize_bloodline(self, image=None, roi=None):
        """
        识别血脉类型（OCR识别框选区域内的文字）
        :param image: 截图图像（游戏窗口客户区截图），如果为None则自动捕获
        :param roi: 血脉识别区域 (x, y, w, h)，客户区相对物理像素坐标
        :return: (bloodline_type, has_text)
            - bloodline_type: 识别到的血脉类型（奇异/污染/混乱/异色），未识别到返回None
            - has_text: 是否识别到任何文字（用于判断是否停止OCR）
        """
        if image is None:
            if roi is not None:
                image = self.capture_window()
            else:
                image = self.capture_window(roi)

        if image is None:
            return None, False

        # 如果传入了roi参数，裁剪图像
        if roi is not None:
            roi_x, roi_y, roi_w, roi_h = roi
            img_h, img_w = image.shape[:2]
            # 边界保护
            if roi_x < 0 or roi_y < 0 or roi_x + roi_w > img_w or roi_y + roi_h > img_h:
                return None, False
            image = image[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]

        # 初始化OCR
        self.init_ocr()

        # 执行OCR识别
        result, elapse = self.ocr_engine(image)

        if not result:
            return None, False

        # 收集所有识别到的文字
        all_texts = [item[1] for item in result]
        has_text = len(all_texts) > 0

        # 检查是否包含血脉类型关键字
        for text in all_texts:
            for bloodline in self.BLOODLINE_TYPES:
                if bloodline in text:
                    logger.log(f"🩸 识别到血脉: {bloodline}")
                    return bloodline, True

        return None, has_text

    def _match_pokemon_names(self, texts):
        """匹配宠物名称并返回基础精灵名（带缓存）"""
        matched = []
        for text in texts:
            text_clean = text.strip()
            text_len = len(text_clean)
            
            # 更严格的跳过规则：2个字符以下直接跳过，防止"港"、"F1"等单字/短文本误匹配
            if text_len < 2:
                continue
            
            # 特殊处理："四叶草铅绘"直接通过，不经过进化链匹配
            if text_clean == "四叶草铅绘":
                matched.append("四叶草铅绘")
                continue
            
            # 优先检查缓存
            if text_clean in self._name_match_cache:
                cached_result = self._name_match_cache[text_clean]
                self._cache_hit_count += 1
                if cached_result:
                    matched.append(cached_result)
                continue
            
            # 缓存未命中，执行匹配逻辑
            self._cache_miss_count += 1
            result = None
            
            # 1. 精确匹配（最高优先级）
            base_pokemon = self.evolution_manager.get_base_pokemon(text_clean)
            if base_pokemon:
                result = base_pokemon
                matched.append(result)
                self._name_match_cache[text_clean] = result
                continue
            
            # 2. 编辑距离匹配（防止"灵狐"被识别为"水滴蛇"等错误）
            best_match = None
            min_distance = float('inf')
            evolution_chains = self.evolution_manager.evolution_chains
            
            for form_name, base_name in evolution_chains.items():
                if len(form_name) < 2:
                    continue
                
                # 快速过滤：长度差异太大的直接跳过
                len_diff = abs(text_len - len(form_name))
                if len_diff > 1:
                    continue
                
                # 严格要求：短文本必须和精灵名有足够多的字符重叠
                if text_len <= 3 and len_diff == 1:
                    # 对于2-3个字符的文本，必须有至少2个字符相同
                    overlap = len(set(text_clean) & set(form_name))
                    if overlap < 2:
                        continue
                
                # 计算编辑距离（Levenshtein距离）
                distance = self._levenshtein_distance(text_clean, form_name)
                
                # 更严格的编辑距离要求
                max_distance = 1 if text_len <= 3 else 2
                if distance <= max_distance and distance < min_distance:
                    min_distance = distance
                    best_match = base_name
            
            if best_match:
                result = best_match
                matched.append(result)
                self._name_match_cache[text_clean] = result
                continue
            
            # 3. 严格包含匹配（只有当文本长度差异不大时）
            for form_name, base_name in evolution_chains.items():
                if len(form_name) < 2:
                    continue
                
                # 快速过滤
                if form_name in text_clean or text_clean in form_name:
                    # 更严格的重叠要求
                    overlap = len(set(text_clean) & set(form_name))
                    min_overlap = max(2, len(form_name) // 2)
                    # 对于短文本，要求更高的重叠比例
                    if text_len <= 3:
                        min_overlap = max(2, len(text_clean) - 0)
                    if overlap >= min_overlap:
                        result = base_name
                        matched.append(result)
                        self._name_match_cache[text_clean] = result
                        break
        
        # 定期清理缓存（防止内存泄漏）
        if len(self._name_match_cache) > 1000:
            self._name_match_cache = {}
            logger.log(f"🧹 清理名称匹配缓存，命中率: {self._cache_hit_count}/{self._cache_hit_count + self._cache_miss_count:.1%}")
            self._cache_hit_count = 0
            self._cache_miss_count = 0
        
        return list(set(matched))  # 去重
    
    def _levenshtein_distance(self, s1, s2):
        """计算两个字符串的编辑距离（Levenshtein距离）"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        # len(s1) >= len(s2)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

    def recognize_with_confidence(self, image=None, roi=None, min_confidence=0.7):
        """
        带置信度的OCR识别
        :param min_confidence: 最小置信度阈值
        :return: [(文本, 置信度), ...]
        """
        if image is None:
            image = self.capture_window()
        
        if image is None:
            return []
        
        if roi:
            x, y, w, h = roi
            image = image[y:y+h, x:x+w]
        
        self.init_ocr()
        result, elapse = self.ocr_engine(image)
        
        if result:
            # 过滤低置信度结果
            filtered = [(item[1], item[2]) for item in result if item[2] >= min_confidence]
            return filtered
        
        return []
    
    def detect_nightmare_template(self, image=None):
        """
        检测nightmare_template图片，带6秒冷却(智能缓存最佳缩放比例+DPI感知)
        :return: (是否检测到, 当前计数)
        """
        import time
        
        if image is None:
            image = self.capture_window()
        
        if image is None:
            return False, self.nightmare_detected_count
        
        # 使用缓存的模板
        if self.nightmare_template is None:
            logger.log(f"⚠️ nightmare_template模板未加载")
            return False, self.nightmare_detected_count
        
        threshold = self.settings_manager.get("confidence_pollution", 0.75) if hasattr(self, 'settings_manager') else 0.75
        
        # 如果已有缓存的缩放模板，直接使用
        if self.nightmare_cached_template is not None:
            result = cv2.matchTemplate(image, self.nightmare_cached_template, cv2.TM_CCOEFF_NORMED)
            loc = np.where(result >= threshold)
            detected = len(loc[0]) > 0
            
            if detected:
                current_time = time.time()
                if current_time - self.last_nightmare_time >= self.nightmare_cooldown:
                    self.nightmare_detected_count += 1
                    self.last_nightmare_time = current_time
                    logger.log(f"✅ 检测到nightmare_template(缓存)，童话事件数: {self.nightmare_detected_count}")
                else:
                    remaining = self.nightmare_cooldown - (current_time - self.last_nightmare_time)
                    logger.log(f"⏳ nightmare_template在冷却中，剩余{remaining:.1f}秒")
                return True, self.nightmare_detected_count
            else:
                # 匹配失败，可能分辨率变化，清空缓存重新探测
                logger.log(f"⚠️ nightmare缓存模板失效，重新探测")
                self.nightmare_best_scale = None
                self.nightmare_cached_template = None
        
        # 获取DPI缩放比例（如果有）
        dpi_scale = 1.0
        if hasattr(self, 'get_dpi_scale'):
            try:
                dpi_scale = self.get_dpi_scale()
            except:
                dpi_scale = 1.0
        
        # 多尺度探测：尝试多个缩放比例（包含DPI缩放）
        base_scales = [0.8, 0.9, 1.0, 1.1, 1.2]
        # 根据DPI调整基础缩放范围
        if dpi_scale != 1.0:
            # 以DPI缩放为中心，生成更密集的探测点
            scales = sorted(set([
                max(0.5, dpi_scale * s) for s in [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
            ] + base_scales))
        else:
            scales = base_scales
        
        best_score = 0
        best_scale = 1.0
        detected = False
        
        for scale in scales:
            h, w = self.nightmare_template.shape[:2]
            new_w = int(w * scale)
            new_h = int(h * scale)
            if new_w < 10 or new_h < 10:
                continue
            scaled_template = cv2.resize(self.nightmare_template, (new_w, new_h))
            
            result = cv2.matchTemplate(image, scaled_template, cv2.TM_CCOEFF_NORMED)
            loc = np.where(result >= threshold)
            
            if len(loc[0]) > 0:
                # 找到匹配，缓存最佳比例和缩放后的模板
                self.nightmare_best_scale = scale
                self.nightmare_cached_template = scaled_template.copy()
                detected = True
                
                current_time = time.time()
                if current_time - self.last_nightmare_time >= self.nightmare_cooldown:
                    self.nightmare_detected_count += 1
                    self.last_nightmare_time = current_time
                    logger.log(f"✅ 检测到nightmare_template: 缩放={scale}x, 童话事件数: {self.nightmare_detected_count}")
                # 冷却中不输出日志,避免刷屏
                break
            
            # 记录最高分数
            if len(loc[0]) == 0:
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                if max_val > best_score:
                    best_score = max_val
                    best_scale = scale
        
        if not detected:
            # 未匹配时不输出日志,避免刷屏
            pass
        
        return detected, self.nightmare_detected_count

    def reset_nightmare_count(self):
        """重置童话事件提示计数"""
        self.nightmare_detected_count = 0
        logger.log(f"🔄 童话事件提示计数已重置为 0")
    
    def set_nightmare_count(self, count):
        """设置童话事件提示计数"""
        self.nightmare_detected_count = max(0, count)
        logger.log(f"🔄 童话事件提示计数已设置为 {self.nightmare_detected_count}")
    
    def detect_nl_trigger(self, image=None):
        """
        检测是否出现nl.png模板（童话事件触发标志，带多尺度缩放和智能缓存）
        :param image: 截图图像，如果为None则自动捕获
        :return: True/False
        """
        if image is None:
            image = self.capture_window()
        
        if image is None or self.nl_template is None:
            return False
        
        # 使用默认ROI区域（右上角）
        h, w = image.shape[:2]
        roi_x = int(w * 0.4) + 100
        roi_y = 0
        roi_w = int(w * 0.6) - 100
        roi_h = int(h * 0.15)
        roi_image = image[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]
        
        # 使用设置中的置信度
        threshold = self.settings_manager.get("recognition_confidence", 0.7) if hasattr(self, 'settings_manager') else 0.7
        
        # 如果已有缓存的缩放模板，直接使用
        if self.nl_cached_template is not None:
            result = cv2.matchTemplate(roi_image, self.nl_cached_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                logger.log(f"✅ nl.png匹配成功(缓存): 相似度={max_val:.3f}")
                return True
            else:
                # 匹配失败，清空缓存重新探测
                logger.log(f"⚠️ nl缓存模板失效，重新探测")
                self.nl_best_scale = None
                self.nl_cached_template = None
        
        # 多尺度探测，最少5个尺度，覆盖常见分辨率
        scales = [0.5, 0.67, 0.8, 1.0, 1.25, 1.5, 1.75, 2.0]
        best_score = 0
        best_scale = 1.0
        
        for scale in scales:
            h_tpl, w_tpl = self.nl_template_original.shape[:2]
            new_w = int(w_tpl / scale)
            new_h = int(h_tpl / scale)
            if new_w < 10 or new_h < 10:
                continue
            scaled_template = cv2.resize(self.nl_template_original, (new_w, new_h))
            
            result = cv2.matchTemplate(roi_image, scaled_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val > best_score:
                best_score = max_val
                best_scale = scale
            
            if max_val >= threshold:
                # 找到匹配，缓存最佳比例和缩放后的模板
                self.nl_best_scale = scale
                self.nl_cached_template = scaled_template.copy()
                self.scale_probe_count += 1
                logger.log(f"✅ nl.png匹配成功: 缩放=1/{scale:.2f}x, 相似度={max_val:.3f}")
                return True
        
        # 所有尺度都未匹配
        logger.log(f"❌ nl.png未匹配: 最高相似度={best_score:.3f}, 阈值={threshold}")
        
        # 如果探测多次都失败，重置缓存
        if self.nl_best_scale is not None:
            self.scale_probe_count += 1
            if self.scale_probe_count >= 3:
                logger.log(f"⚠️ nl连续探测失败，重置缓存")
                self.nl_best_scale = None
                self.scale_probe_count = 0
        
        return False
    
    def should_enable_ocr(self, image=None):
        """
        判断是否应该启用OCR（基于nl检测和战斗状态）
        :param image: 截图图像
        :return: (should_ocr, reason) - 是否应该OCR及原因
        """
        import time
        current_time = time.time()
        
        if self.ocr_enabled:
            # OCR已启用，检查是否需要关闭
            elapsed_since_last_valid = current_time - self.last_valid_recognition_time
            
            if self.last_valid_recognition_time > 0 and elapsed_since_last_valid > self.ocr_timeout:
                # 超过6秒没有识别到有效文本，关闭OCR
                self.ocr_enabled = False
                self.battle_start_time = 0
                self.last_valid_recognition_time = 0
                self.nl_was_detected = False  # 重置nl触发状态，允许下次触发
                logger.log(f"⏱️ OCR超时关闭：{elapsed_since_last_valid:.1f}秒无有效识别")
                return False, "timeout"
            else:
                # 继续OCR
                return True, "battle_active"
        else:
            # OCR未启用，检查是否应该启动
            # 如果之前nl触发失败，需要先检测nl是否消失
            if self.nl_detection_failed:
                # 添加超时保护：如果nl_detection_failed状态持续超过30秒，强制重置
                if not hasattr(self, '_nl_fail_time'):
                    self._nl_fail_time = current_time
                    logger.log(f"⏳ nl触发失败，等待nl消失或30秒超时自动恢复")
                
                elapsed_fail = current_time - self._nl_fail_time
                if elapsed_fail > 30:
                    logger.log(f"🔄 nl_detection_failed超时30秒({elapsed_fail:.0f}s)，强制恢复OCR状态")
                    self.nl_was_detected = False
                    self.nl_detection_failed = False
                    self.battle_start_time = 0
                    self._nl_fail_time = 0
                else:
                    nl_currently_detected = self.detect_nl_trigger(image)
                    if not nl_currently_detected:
                        # nl已消失，重置状态，允许下次触发
                        logger.log("✅ nl已消失，重置触发状态")
                        self.nl_was_detected = False
                        self.nl_detection_failed = False
                        self.battle_start_time = 0
                        self._nl_fail_time = 0
                    # nl仍存在，不允许再次触发
                    return False, "nl_still_present"
            
            # 检测nl模板
            nl_detected = self.detect_nl_trigger(image)
            if nl_detected:
                if not self.nl_was_detected:
                    # 首次检测到nl，启动OCR
                    self.nl_was_detected = True
                    self.ocr_enabled = True
                    self.nl_trigger_time = current_time  # 记录nl触发时间
                    self.last_valid_recognition_time = current_time  # 设置初始时间，用于超时判断
                    self.battle_started = False  # 战斗尚未开始
                    self.nl_detection_failed = False
                    logger.log("🚀 检测到nl模板，启动OCR，等待2秒内检测四叶草铅绘")
                    return True, "nl_triggered"
                else:
                    # nl已被检测过但尚未消失，不再重复触发
                    return False, "nl_already_detected"
            else:
                # 未检测到nl
                return False, "waiting_nl"
    
    def update_ocr_state(self, has_valid_recognition, recognized_names=None):
        """
        更新OCR状态（在主线程调用）
        :param has_valid_recognition: 是否有有效识别结果
        :param recognized_names: 识别到的名称列表
        """
        import time
        current_time = time.time()
        
        if self.ocr_enabled:
            # 阶段1：nl触发后2秒内必须检测到“四叶草铅绘”
            if not self.battle_started and self.nl_trigger_time > 0:
                elapsed_since_nl = current_time - self.nl_trigger_time
                
                # 检查是否已经检测到四叶草铅绘
                has_lucky_box = recognized_names and "四叶草铅绘" in recognized_names
                
                if has_lucky_box:
                    # 检测到四叶草铅绘，战斗正式开始
                    logger.log("✅ nl触发后检测到四叶草铅绘，战斗开始")
                    self.battle_started = True
                    self.battle_start_time = current_time  # 重置计时器，用于6秒超时
                    self.last_valid_recognition_time = current_time
                elif elapsed_since_nl > self.nl_trigger_timeout:
                    # 2秒内未检测到四叶草铅绘，关闭OCR并标记失败
                    self.ocr_enabled = False
                    self.nl_trigger_time = 0
                    self.battle_start_time = 0
                    self.last_valid_recognition_time = 0
                    self.nl_detection_failed = True  # 标记为失败，直到nl消失才重置
                    self.nl_was_detected = False  # 重置nl触发状态，允许下次触发
                    logger.log(f"⏱️ nl触发后{elapsed_since_nl:.1f}秒内未检测到四叶草铅绘，关闭OCR，等待nl消失")
            
            # 阶段2：战斗已正式开始，使用6秒超时判定
            elif self.battle_started:
                if has_valid_recognition:
                    self.last_valid_recognition_time = current_time


class ScreenshotWorker(QThread):
    """异步截图+识别工作线程"""
    screenshot_ready = Signal(object)  # 发送截图结果
    recognition_result = Signal(dict)  # 发送识别结果
    
    def __init__(self, game_capture, main_window):
        super().__init__()
        self.game_capture = game_capture
        self.main_window = main_window
        self._running = True
        self._capture_requested = False
        self.current_battle_lkwg = None  # 同步主线程的战斗状态
        self.idle_count = 0  # 空闲计数，用于动态调整频率
        # 血脉识别状态（由主线程同步）
        self.bloodline_check_active = False  # 是否应该执行血脉OCR
    
    def run(self):
        """线程主循环"""
        while self._running:
            try:
                if self._capture_requested:
                    self._capture_requested = False
                    self._do_recognition()
                    self.idle_count = 0
                else:
                    self.idle_count += 1
                    # 智能休眠：空闲时增加休眠时间，减少CPU占用
                    if self.idle_count > 100:
                        self.msleep(100)  # 空闲时休眠100ms
                    elif self.idle_count > 50:
                        self.msleep(50)   # 中度空闲
                    else:
                        self.msleep(10)   # 活跃时快速响应
            except Exception as e:
                print(f"❌ ScreenshotWorker线程异常: {e}")
                import traceback
                traceback.print_exc()
                self.msleep(1000)  # 发生异常后等待1秒再继续，避免死循环
    
    def _do_recognition(self):
        """执行识别逻辑（在子线程）"""
        try:
            # 默认识别模式不使用框选ROI,直接使用默认区域
            roi = None

            # 截图
            current_image = self.game_capture.capture_window(roi)
            if current_image is None:
                result = {
                    'recognized_names': [],
                    'should_ocr': False,
                    'ocr_reason': 'capture_failed'
                }
                self.recognition_result.emit(result)
                return

            # 判断是否应该启用OCR
            should_ocr, ocr_reason = self.game_capture.should_enable_ocr(image=current_image)

            recognized_names = []
            if should_ocr:
                h, w = current_image.shape[:2]
                roi_x = int(w * 0.4) + 100
                roi_y = 0
                roi_w = int(w * 0.6) - 100
                roi_h = int(h * 0.15)
                roi_image = current_image[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]
                recognized_names = self.game_capture.recognize_pokemon_name(image=roi_image, roi=(0, 0, roi_w, roi_h))

            # 血脉识别：当四叶草铅绘未识别到且血脉检查处于激活状态时，顺便OCR血脉框选区域
            bloodline_result = None
            bloodline_has_text = False
            bloodline_checked = False  # 是否实际执行了血脉OCR
            if (should_ocr and
                    self.bloodline_check_active and
                    "四叶草铅绘" not in recognized_names and
                    hasattr(self.game_capture, 'settings_manager') and
                    self.game_capture.settings_manager):
                bl_enabled = self.game_capture.settings_manager.get("enable_bloodline_recognition", False)
                bl_roi = self.game_capture.settings_manager.get("bloodline_roi")
                if bl_enabled and bl_roi:
                    bl_roi_tuple = (bl_roi['x'], bl_roi['y'], bl_roi['width'], bl_roi['height'])
                    bloodline_result, bloodline_has_text = self.game_capture.recognize_bloodline(
                        image=current_image, roi=bl_roi_tuple
                    )
                    bloodline_checked = True  # 标记实际执行了血脉OCR

            result = {
                'recognized_names': recognized_names,
                'should_ocr': should_ocr,
                'ocr_reason': ocr_reason,
                'bloodline': bloodline_result,
                'bloodline_has_text': bloodline_has_text,
                'bloodline_checked': bloodline_checked
            }
            self.recognition_result.emit(result)

        except Exception as e:
            print(f"❌ 子线程识别错误: {e}")
            import traceback
            traceback.print_exc()
    
    def capture_async(self):
        """请求截图和识别"""
        self._capture_requested = True
    
    def stop(self):
        """停止线程"""
        self._running = False
        self.wait()


class NightmareWorker(QThread):
    """Nightmare独立检测工作线程(低频)"""
    nightmare_result = Signal(dict)  # 发送nightmare检测结果
    
    def __init__(self, game_capture, main_window):
        super().__init__()
        self.game_capture = game_capture
        self.main_window = main_window
        self._running = True
    
    def run(self):
        """线程主循环 - 每2秒检测一次nightmare"""
        while self._running:
            try:
                # 截图
                current_image = self.game_capture.capture_window()
                if current_image is not None:
                    # 检测nightmare
                    nightmare_detected, nightmare_count = self.game_capture.detect_nightmare_template(image=current_image)
                    
                    # 发送结果到主线程
                    result = {
                        'nightmare_detected': nightmare_detected,
                        'nightmare_count': nightmare_count
                    }
                    self.nightmare_result.emit(result)
            except Exception as e:
                print(f"❌ Nightmare检测错误: {e}")
            
            # 每2秒检测一次
            self.msleep(2000)
    
    def stop(self):
        """停止线程"""
        self._running = False
        self.wait(3000)
