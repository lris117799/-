    # core/game_capture.py
import cv2
import numpy as np
import win32gui
import win32ui
import win32con
import win32process
from rapidocr_onnxruntime import RapidOCR
import os
from ctypes import windll
from .evolution_manager import EvolutionManager
from .logger import logger
from PySide6.QtCore import QThread, Signal

class GameCapture:
    def __init__(self, window_title="洛克王国：世界"):
        self.window_title = window_title
        self.hwnd = None
        self.ocr_engine = None
        self.evolution_manager = EvolutionManager()
        self.pokemon_names = self._load_pokemon_names()
        
        # 污染提示检测状态
        self.nightmare_detected_count = 0
        self.last_nightmare_time = 0
        self.nightmare_cooldown = 6  # 6秒冷却
        
        # xt10检测状态（防重复计数）
        self.xt10_was_detected = False  # 上一帧是否检测到xt10
        
        # 缓存模板图片（避免重复加载）
        self.xt_template = None
        self.xt10_template = None
        self.nightmare_template = None
        self.templates_loaded = False  # 标记模板是否已加载
        self.last_dpi_scale = None  # 记录上次加载时的DPI
        
        # 智能缓存最佳缩放比例
        self.xt_best_scale = None  # xt.png最佳缩放比例
        self.xt10_best_scale = None  # xt10.png最佳缩放比例
        self.nightmare_best_scale = None  # nightmare_template最佳缩放比例
        self.scale_probe_count = 0  # 探测计数器
        
        # 预保存缩放后的模板(避免每次resize)
        self.xt_cached_template = None  # xt.png缩放后模板
        self.xt10_cached_template = None  # xt10.png缩放后模板
        self.nightmare_cached_template = None  # nightmare_template缩放后模板
    
    def _load_pokemon_names(self):
        """加载宠物名称词库（从进化链中提取所有形态）"""
        return list(self.evolution_manager.evolution_chains.keys())
    
    def _load_templates(self):
        """加载并缓存模板图片(根据DPI自动缩放)"""
        image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image")
            
        # 获取DPI缩放因子(防止为0)
        dpi_scale = self._get_dpi_scale()
        if dpi_scale <= 0:
            logger.log(f"⚠️ DPI缩放因子异常({dpi_scale}),使用默认值1.0")
            dpi_scale = 1.0
            
        # 加载xt.png
        xt_path = os.path.join(image_dir, "xt.png")
        if os.path.exists(xt_path):
            self.xt_template = cv2.imread(xt_path, cv2.IMREAD_COLOR)
            if self.xt_template is not None:
                # 根据DPI缩放模板
                if dpi_scale != 1.0:
                    h, w = self.xt_template.shape[:2]
                    new_w = int(w / dpi_scale)
                    new_h = int(h / dpi_scale)
                    if new_w > 0 and new_h > 0:  # 确保尺寸有效
                        self.xt_template = cv2.resize(self.xt_template, (new_w, new_h))
                        logger.log(f"✅ 已缓存xt.png模板 (DPI缩放: {dpi_scale}x, 尺寸: {new_w}x{new_h})")
                    else:
                        logger.log(f"⚠️ xt.png缩放后尺寸无效,使用原始模板")
                else:
                    logger.log(f"✅ 已缓存xt.png模板")
            
        # 加载xt10.png
        xt10_path = os.path.join(image_dir, "xt10.png")
        if os.path.exists(xt10_path):
            self.xt10_template = cv2.imread(xt10_path, cv2.IMREAD_COLOR)
            if self.xt10_template is not None:
                # 根据DPI缩放模板
                if dpi_scale != 1.0:
                    h, w = self.xt10_template.shape[:2]
                    new_w = int(w / dpi_scale)
                    new_h = int(h / dpi_scale)
                    if new_w > 0 and new_h > 0:
                        self.xt10_template = cv2.resize(self.xt10_template, (new_w, new_h))
                        logger.log(f"✅ 已缓存xt10.png模板 (DPI缩放: {dpi_scale}x, 尺寸: {new_w}x{new_h})")
                    else:
                        logger.log(f"⚠️ xt10.png缩放后尺寸无效,使用原始模板")
                else:
                    logger.log(f"✅ 已缓存xt10.png模板")
            
        # 加载nightmare_template.png
        nightmare_path = os.path.join(image_dir, "nightmare_template.png")
        if os.path.exists(nightmare_path):
            self.nightmare_template = cv2.imread(nightmare_path)
            if self.nightmare_template is not None:
                # 根据DPI缩放模板
                if dpi_scale != 1.0:
                    h, w = self.nightmare_template.shape[:2]
                    new_w = int(w / dpi_scale)
                    new_h = int(h / dpi_scale)
                    if new_w > 0 and new_h > 0:
                        self.nightmare_template = cv2.resize(self.nightmare_template, (new_w, new_h))
                        logger.log(f"✅ 已缓存nightmare_template.png模板 (DPI缩放: {dpi_scale}x, 尺寸: {new_w}x{new_h})")
                    else:
                        logger.log(f"⚠️ nightmare_template缩放后尺寸无效,使用原始模板")
                else:
                    logger.log(f"✅ 已缓存nightmare_template.png模板")
    
    def reload_templates(self):
        """重新加载所有模板图片（用于更换图片后不重启程序）"""
        logger.log("🔄 重新加载模板图片...")
        self._load_templates()
        logger.log("✅ 模板重新加载完成")
    
    def _get_dpi_scale(self):
        """获取DPI缩放因子"""
        try:
            # 方法1: 使用GetDpiForWindow (Windows 10+)
            dpi = windll.user32.GetDpiForWindow(self.hwnd)
            scale = dpi / 96.0
            return scale
        except:
            pass
        
        try:
            # 方法2: 使用GetScaleFactorForDevice
            scale_factor = windll.shcore.GetScaleFactorForDevice(0)
            scale = scale_factor / 100.0
            return scale
        except:
            pass
        
        # 默认返回1.0（无缩放）
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
            # 通过进程名找到PID
            target_pid = None
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] == 'NRC-Win64-Shipping.exe':
                        target_pid = proc.info['pid']
                        logger.log(f"✅ 找到游戏进程: PID={target_pid}")
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not target_pid:
                logger.log(f"❌ 未找到NRC-Win64-Shipping.exe进程")
                self.hwnd = 0
                return False
            
            # 直接通过标题查找窗口(已确定是游戏进程,不会误匹配)
            self.hwnd = win32gui.FindWindow(None, self.window_title)
            
            if self.hwnd == 0:
                # 尝试模糊匹配
                def callback(hwnd, extra):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if self.window_title in title:
                            # 验证是否属于目标进程
                            try:
                                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                                if pid == target_pid:
                                    extra.append(hwnd)
                                    return False
                            except:
                                pass
                    return True
                
                matched_hwnds = []
                win32gui.EnumWindows(callback, matched_hwnds)
                if matched_hwnds:
                    self.hwnd = matched_hwnds[0]
            
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
    
    def capture_window(self, roi=None):
        """捕获游戏窗口画面（支持后台）
        :param roi: 框选区域 (x, y, width, height)，如果为None则全屏截图
        :return: BGR格式的numpy数组
        """
        if not self.hwnd:
            if not self.find_window():
                logger.log("❌ 未找到游戏窗口")
                return None
        
        # 获取窗口位置和大小（使用GetClientRect获取客户区，避免边框影响）
        try:
            # 获取客户区尺寸（不包含边框、标题栏）
            left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
            
            # 将客户区坐标转换为屏幕坐标
            point = (left, top)
            screen_point = win32gui.ClientToScreen(self.hwnd, point)
            
            client_left = screen_point[0]
            client_top = screen_point[1]
            client_right = client_left + (right - left)
            client_bottom = client_top + (bottom - top)
            
            # GetClientRect返回的是逻辑像素，PrintWindow需要使用逻辑像素尺寸
            logical_width = right - left
            logical_height = bottom - top
            
            # 获取DPI缩放因子用于后续处理
            dpi_scale = self._get_dpi_scale()
            if dpi_scale != 1.0:
                logger.log(f"📐 DPI缩放: {dpi_scale}x, 逻辑尺寸: {logical_width}x{logical_height}")

        except Exception as e:
            # 降级到GetWindowRect
            logger.log(f"⚠️ GetClientRect失败，使用GetWindowRect: {e}")
            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            client_left, client_top, client_right, client_bottom = left, top, right, bottom
            
            logical_width = right - left
            logical_height = bottom - top
            dpi_scale = self._get_dpi_scale()
        

        
        try:
            # 方法1：尝试PrintWindow参数2（完整内容）
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
            
            # 检查是否截到有效数据（非全黑/全白）
            img_temp = np.frombuffer(bmpstr, dtype=np.uint8).reshape((logical_height, logical_width, 4))
            mean_val = np.mean(img_temp[:, :, :3])  # 计算RGB平均值
            
            # 如果平均亮度接近0或255，说明截图失败，降级到BitBlt
            if mean_val < 10 or mean_val > 245:

                save_dc.DeleteDC()
                mfc_dc.DeleteDC()
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
                mfc_screen.DeleteDC()
                win32gui.ReleaseDC(0, screen_dc)
            else:
                # PrintWindow成功
                win32gui.DeleteObject(bitmap.GetHandle())
                save_dc.DeleteDC()
                mfc_dc.DeleteDC()
                win32gui.ReleaseDC(self.hwnd, hwnd_dc)
            
            img = img_temp
            
            # BGRA -> BGR
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            # 如果指定了roi，裁剪图像
            if roi:
                x, y, w, h = roi
                # 确保roi在图像范围内
                h_img, w_img = img.shape[:2]
                x = max(0, min(x, w_img - 1))
                y = max(0, min(y, h_img - 1))
                w = min(w, w_img - x)
                h = min(h, h_img - y)
                if w > 0 and h > 0:
                    img = img[y:y+h, x:x+w]
                    logger.log(f"✂️ 已裁剪ROI: ({x}, {y}, {w}, {h})")
            
            return img
        except Exception as e:
            logger.log(f"❌ 截图失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def init_ocr(self):
        """初始化OCR引擎"""
        if self.ocr_engine is None:
            import sys
            
            # 获取模型文件路径（支持打包后运行）
            if getattr(sys, 'frozen', False):
                # 打包后的路径
                base_path = sys._MEIPASS
                det_model_path = os.path.join(base_path, 'rapidocr_onnxruntime', 'models', 'ch_PP-OCRv4_det_infer.onnx')
                rec_model_path = os.path.join(base_path, 'rapidocr_onnxruntime', 'models', 'ch_PP-OCRv4_rec_infer.onnx')
                cls_model_path = os.path.join(base_path, 'rapidocr_onnxruntime', 'models', 'ch_ppocr_mobile_v2.0_cls_infer.onnx')
            else:
                # 开发环境的路径
                import rapidocr_onnxruntime
                model_dir = os.path.join(os.path.dirname(rapidocr_onnxruntime.__file__), 'models')
                det_model_path = os.path.join(model_dir, 'ch_PP-OCRv4_det_infer.onnx')
                rec_model_path = os.path.join(model_dir, 'ch_PP-OCRv4_rec_infer.onnx')
                cls_model_path = os.path.join(model_dir, 'ch_ppocr_mobile_v2.0_cls_infer.onnx')
            
            logger.log(f"🔍 OCR模型路径: det={det_model_path}")
            
            # 配置RapidOCR参数
            ocr_config = {
                'use_angle_cls': False,  # 不使用角度分类，提升速度
                'rec_batch_num': 6,      # 批量识别数量
                'rec_img_shape': [3, 48, 320],  # 识别图像尺寸
                'det_db_score_mode': 'slow',  # 检测评分模式
                'det_db_unclip_ratio': 1.6,   # 文本框扩展比例
                'det_db_box_thresh': 0.5,     # 文本框置信度阈值
                'det_db_thresh': 0.3,         # 二值化阈值
                'det_model_path': det_model_path,
                'rec_model_path': rec_model_path,
                'cls_model_path': cls_model_path,
            }
            self.ocr_engine = RapidOCR(params=ocr_config)
            logger.log("✅ OCR引擎初始化成功")
    
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
            roi_x = int(w * 0.4)
            roi_y = 0
            roi_w = int(w * 0.6)
            roi_h = int(h * 0.15)
            roi = (roi_x, roi_y, roi_w, roi_h)
            
            # 默认识别模式：首次调用时保存调试图
            if not hasattr(self, '_default_roi_debug_saved'):
                import cv2
                debug_image = image.copy()
                cv2.rectangle(debug_image, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (0, 0, 255), 3)
                debug_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "image", "debug_roi.png")
                cv2.imwrite(debug_path, debug_image)
                logger.log(f"📸 ROI调试图已保存: {debug_path} (尺寸:{w}x{h}, ROI:{roi})")
                self._default_roi_debug_saved = True
            
            # 裁剪图像
            image = image[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]
        
        # 初始化OCR
        self.init_ocr()
        
        # 执行OCR识别
        result, elapse = self.ocr_engine(image)
        
        if result:
            # 提取所有文本（调试用）
            all_texts = [item[1] for item in result]
            logger.log(f"🔍 OCR识别到 {len(all_texts)} 个文本: {', '.join(all_texts[:5])}")
            
            # 过滤并匹配宠物名称
            matched = self._match_pokemon_names(all_texts)
            if matched:
                logger.log(f"✅ 匹配到精灵: {', '.join(matched)}")
            else:
                logger.log(f"❌ 未匹配到已知精灵")
            return matched
        else:
            logger.log(f"❌ OCR未识别到任何文本")
        
        return []
    
    def _match_pokemon_names(self, texts):
        """匹配宠物名称并返回基础精灵名"""
        matched = []
        for text in texts:
            text_clean = text.strip()
            
            # 1. 精确匹配
            base_pokemon = self.evolution_manager.get_base_pokemon(text_clean)
            if base_pokemon:
                matched.append(base_pokemon)
                continue
            
            # 2. 模糊匹配：检查是否包含宠物名称
            for form_name, base_name in self.evolution_manager.evolution_chains.items():
                if form_name in text_clean or text_clean in form_name:
                    matched.append(base_name)
                    break
        
        return list(set(matched))  # 去重
    
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
    
    def detect_xt_icon(self, image=None, roi=None):
        """
        检测是否出现xt.png图标(智能缓存最佳缩放比例)
        :return: True/False
        """
        if image is None:
            image = self.capture_window()
        
        if image is None:
            return False
        
        # 标记是否是用户传入的roi(坐标识别模式)
        user_provided_roi = roi is not None
        
        # 如果没有指定ROI,使用默认区域(右上角,与精灵名字同一区域)
        if roi is None:
            h, w = image.shape[:2]
            roi_x = int(w * 0.4)
            roi_y = 0
            roi_w = int(w * 0.6)
            roi_h = int(h * 0.15)
            roi = (roi_x, roi_y, roi_w, roi_h)
        
        if roi:
            x, y, w, h = roi
            image = image[y:y+h, x:x+w]
        
        # 使用缓存的模板
        if self.xt_template is None:
            logger.log(f"⚠️ xt模板未加载")
            return False
        
        threshold = 0.7
        
        # 如果已有缓存的缩放模板，直接使用
        if self.xt_cached_template is not None:
            result = cv2.matchTemplate(image, self.xt_cached_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                logger.log(f"✅ xt.png匹配成功(缓存): 相似度={max_val:.3f}")
                
                # 关键：xt缓存命中后，也要清除xt10缓存，确保xt10重新探测以适配可能的分辨率变化
                if self.xt10_cached_template is not None:
                    logger.log(f"🔄 xt缓存命中，清除xt10缓存以保持一致")
                    self.xt10_best_scale = None
                    self.xt10_cached_template = None
                
                return True
            else:
                # 坐标识别模式：不使用缩放，直接返回失败
                if user_provided_roi:
                    logger.log(f"❌ xt.png未匹配(坐标识别模式，不缩放)")
                    return False
                # 默认识别模式：匹配失败，清空缓存重新探测
                logger.log(f"⚠️ xt缓存模板失效，重新探测")
                self.xt_best_scale = None
                self.xt_cached_template = None
        
        # 坐标识别模式：按DPI缩放模板
        if user_provided_roi:
            # 获取DPI缩放因子
            dpi_scale = self._get_dpi_scale()
            h, w = self.xt_template.shape[:2]
            new_w = int(w * dpi_scale)
            new_h = int(h * dpi_scale)
            scaled_template = cv2.resize(self.xt_template, (new_w, new_h))
            
            result = cv2.matchTemplate(image, scaled_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            print(f"📊 xt DPI缩放={dpi_scale:.2f}x, 模板尺寸={new_w}x{new_h}, 相似度={max_val:.4f}")
            
            if max_val >= threshold:
                print(f"✅ xt.png匹配成功(坐标识别+DPI): 相似度={max_val:.3f}")
                return True
            else:
                print(f"❌ xt.png未匹配(坐标识别+DPI): 相似度={max_val:.3f}")
                return False
        
        # 多尺度探测：尝试多个缩放比例
        scales = [0.8, 0.9, 1.0, 1.1, 1.2]
        best_score = 0
        best_scale = 1.0
        
        for scale in scales:
            h, w = self.xt_template.shape[:2]
            new_w = int(w * scale)
            new_h = int(h * scale)
            if new_w < 10 or new_h < 10:
                continue
            scaled_template = cv2.resize(self.xt_template, (new_w, new_h))
            
            result = cv2.matchTemplate(image, scaled_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val > best_score:
                best_score = max_val
                best_scale = scale
            
            if max_val >= threshold:
                # 找到匹配，缓存最佳比例和缩放后的模板
                self.xt_best_scale = scale
                self.xt_cached_template = scaled_template.copy()  # 保存副本
                self.scale_probe_count += 1
                logger.log(f"✅ xt.png匹配成功: 缩放={scale}x, 相似度={max_val:.3f}")
                
                # 关键：xt重新探测成功后，强制清除xt10缓存，让xt10使用新的缩放比例
                if self.xt10_cached_template is not None:
                    logger.log(f"🔄 xt缩放比例更新，清除xt10缓存以适配新分辨率")
                    self.xt10_best_scale = None
                    self.xt10_cached_template = None
                
                return True
        
        # 所有尺度都未匹配
        logger.log(f"❌ xt.png未匹配: 最高相似度={best_score:.3f}, 阈值={threshold}")
        
        # 如果探测多次都失败，重置缓存
        if self.xt_best_scale is not None:
            self.scale_probe_count += 1
            if self.scale_probe_count >= 3:  # 连续3次失败
                logger.log(f"⚠️ xt连续探测失败，重置缓存")
                self.xt_best_scale = None
                self.scale_probe_count = 0
        
        return False
    
    def detect_xt10(self, image=None, roi=None):
        """
        检测是否出现xt10.png图标（带防重复计数，跟随xt的缩放比例）
        :return: True/False (仅当从“未检测到”变为“检测到”时返回True)
        """
        if image is None:
            image = self.capture_window()
        
        if image is None:
            return False
        
        # 标记是否是用户传入的roi(坐标识别模式)
        user_provided_roi = roi is not None
        
        # 如果没有指定ROI,使用默认区域(右上角,与精灵名字同一区域)
        if roi is None:
            h, w = image.shape[:2]
            roi_x = int(w * 0.4)
            roi_y = 0
            roi_w = int(w * 0.6)
            roi_h = int(h * 0.15)
            roi = (roi_x, roi_y, roi_w, roi_h)
        
        if roi:
            x, y, w, h = roi
            image = image[y:y+h, x:x+w]
        
        # 使用缓存的模板
        if self.xt10_template is None:
            logger.log(f"⚠️ xt10模板未加载")
            return False
        
        threshold = 0.65
        currently_detected = False
        
        # 如果已有缓存的缩放模板，直接使用
        if self.xt10_cached_template is not None:
            result = cv2.matchTemplate(image, self.xt10_cached_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                currently_detected = True
            else:
                # 坐标识别模式：不使用缩放，直接返回
                if user_provided_roi:
                    logger.log(f"❌ xt10.png未匹配(坐标识别模式，不缩放)")
                    return False
                # 默认识别模式：匹配失败，清空缓存重新探测
                self.xt10_best_scale = None
                self.xt10_cached_template = None
        
        # 坐标识别模式：按DPI缩放模板
        if user_provided_roi:
            dpi_scale = self._get_dpi_scale()
            h, w = self.xt10_template.shape[:2]
            new_w = int(w * dpi_scale)
            new_h = int(h * dpi_scale)
            scaled_template = cv2.resize(self.xt10_template, (new_w, new_h))
            
            result = cv2.matchTemplate(image, scaled_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            print(f"📊 xt10 DPI缩放={dpi_scale:.2f}x, 模板尺寸={new_w}x{new_h}, 相似度={max_val:.4f}")
            
            if max_val >= 0.65:  # threshold
                currently_detected = True
                print(f"✅ xt10.png匹配成功(坐标识别+DPI): 相似度={max_val:.3f}")
            else:
                print(f"❌ xt10.png未匹配(坐标识别+DPI): 相似度={max_val:.3f}")
        
        # 默认识别模式：多尺度探测
        if not currently_detected and not user_provided_roi:
            # 使用完整的缩放比例范围
            scales = [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
            best_score = 0
            best_scale = 1.0
            
            for scale in scales:
                h, w = self.xt10_template.shape[:2]
                new_w = int(w * scale)
                new_h = int(h * scale)
                if new_w < 10 or new_h < 10:
                    continue
                scaled_template = cv2.resize(self.xt10_template, (new_w, new_h))
                
                result = cv2.matchTemplate(image, scaled_template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                if max_val > best_score:
                    best_score = max_val
                    best_scale = scale
                
                if max_val >= threshold:
                    currently_detected = True
                    self.xt10_best_scale = scale
                    self.xt10_cached_template = scaled_template.copy()  # 保存副本
                    break
            
            if not currently_detected:
                logger.log(f"❌ xt10.png未匹配: 最高相似度={best_score:.3f}, 阈值={threshold}")
        else:
            # 缓存命中,输出日志
            logger.log(f"✅ xt10.png匹配成功(缓存)")
        
        # 防重复计数逻辑：只在状态变化时返回True
        if currently_detected and not self.xt10_was_detected:
            # 首次检测到xt10
            self.xt10_was_detected = True
            logger.log(f"✅ 检测到xt10.png（首次）")
            return True
        elif not currently_detected and self.xt10_was_detected:
            # xt10消失，重置状态
            self.xt10_was_detected = False
            logger.log(f"🔄 xt10.png消失，重置状态")
        
        return False
    
    def detect_nightmare_template(self, image=None):
        """
        检测nightmare_template图片，带6秒冷却(智能缓存最佳缩放比例)
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
        
        threshold = 0.7
        
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
                    logger.log(f"✅ 检测到nightmare_template(缓存)，污染提示数: {self.nightmare_detected_count}")
                else:
                    remaining = self.nightmare_cooldown - (current_time - self.last_nightmare_time)
                    logger.log(f"⏳ nightmare_template在冷却中，剩余{remaining:.1f}秒")
                return True, self.nightmare_detected_count
            else:
                # 匹配失败，可能分辨率变化，清空缓存重新探测
                logger.log(f"⚠️ nightmare缓存模板失效，重新探测")
                self.nightmare_best_scale = None
                self.nightmare_cached_template = None
        
        # 多尺度探测：尝试多个缩放比例
        scales = [0.8, 0.9, 1.0, 1.1, 1.2]
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
                    logger.log(f"✅ 检测到nightmare_template: 缩放={scale}x, 污染提示数: {self.nightmare_detected_count}")
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
    
    def run(self):
        """线程主循环"""
        while self._running:
            if self._capture_requested:
                self._capture_requested = False
                self._do_recognition()
            self.msleep(10)  # 避免空转
    
    def _do_recognition(self):
        """执行识别逻辑（在子线程）"""
        import time
        start_time = time.time()
        
        try:
            # 默认识别模式不使用框选ROI,直接使用默认区域
            roi = None
            
            # 截图
            current_image = self.game_capture.capture_window(roi)
            if current_image is None:
                return
            
            # 检测xt.png
            xt_detected = self.game_capture.detect_xt_icon(image=current_image)
            
            # OCR识别
            recognized_names = []
            # 战斗持续阶段:有战斗状态或xt存在时都要OCR
            should_ocr = xt_detected or self.current_battle_lkwg
            if should_ocr:
                # 传递roi参数，让recognize_pokemon_name知道使用的是已裁剪的图像
                recognized_names = self.game_capture.recognize_pokemon_name(image=current_image, roi=roi, debug=True)
            
            # 检测xt10(如果OCR识别到名字)
            xt10_detected = False
            if recognized_names:
                xt10_detected = self.game_capture.detect_xt10(image=current_image)
            
            # 发送结果到主线程(不包含nightmare,nighmare由独立线程处理)
            result = {
                'xt_detected': xt_detected,
                'recognized_names': recognized_names,
                'xt10_detected': xt10_detected
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
        self.wait()
