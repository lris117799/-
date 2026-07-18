import cv2
import math
import numpy as np
import os
import sys
import time
import pickle
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


def _log_map_debug(msg):
    """将地图加载诊断信息写入日志文件（exe 无控制台时用此排查）

    日志生成位置：image/map/map_debug.log
    """
    try:
        if getattr(sys, 'frozen', False):
            # 打包环境：在 exe 同级的 _internal/image/map/ 下生成
            base_dir = os.path.dirname(sys.executable)
            if hasattr(sys, '_MEIPASS'):
                # 优先写到 _internal/image/map/（用户可访问）
                log_dir = os.path.join(sys._MEIPASS, "image", "map")
                if not os.path.exists(log_dir):
                    log_dir = os.path.join(base_dir, "image", "map")
            else:
                log_dir = os.path.join(base_dir, "image", "map")
        else:
            # 开发环境：项目根目录/image/map/
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "image", "map")
        # 确保目录存在
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "map_debug.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass
    print(msg)


def load_map_full_hq_pixmap():
    """加载 map_full_hq.png 的 QPixmap

    优先使用嵌入到 exe 内部的数据（core._map_data），
    其次从外部文件 image/map_full_hq.png 加载。
    即使 _internal/image/map_full_hq.png 被删除，仍可正常显示。

    返回: QPixmap 对象（加载失败时为空 pixmap）
    """
    from PySide6.QtGui import QPixmap

    _log_map_debug("[Map] === 开始加载地图 ===")

    # 1. 优先尝试嵌入数据
    try:
        _log_map_debug("[Map] 尝试导入 core._map_data ...")
        from core._map_data import get_map_bytes
        _log_map_debug("[Map] 导入成功，开始解码 ...")
        data = get_map_bytes()
        _log_map_debug(f"[Map] 嵌入数据解码完成，大小: {len(data)} bytes ({len(data) / 1024 / 1024:.1f} MB)")
        _log_map_debug(f"[Map] PNG 头: {data[:8]}")
        pix = QPixmap()
        if pix.loadFromData(data):
            _log_map_debug(f"[Map] QPixmap 加载成功: {pix.width()}x{pix.height()}")
            return pix
        else:
            _log_map_debug("[Map] 警告: loadFromData 返回 False，数据可能损坏")
    except Exception as e:
        _log_map_debug(f"[Map] 嵌入数据加载失败: {type(e).__name__}: {e}")
        import traceback
        _log_map_debug(traceback.format_exc())

    # 2. 回退到外部文件
    map_path = _get_resource_path(os.path.join("image", "map_full_hq.png"))
    _log_map_debug(f"[Map] 回退到外部文件: {map_path}, exists={os.path.exists(map_path)}")
    if os.path.exists(map_path):
        return QPixmap(map_path)

    _log_map_debug("[Map] 错误: 嵌入数据和外部文件均不可用")
    return QPixmap()


def get_map_full_hq_bytes():
    """返回 map_full_hq.png 的原始字节（优先嵌入数据，其次读文件）

    返回: bytes 或 None
    """
    # 1. 优先嵌入数据
    try:
        from core._map_data import get_map_bytes
        return get_map_bytes()
    except Exception:
        pass

    # 2. 回退到外部文件
    map_path = _get_resource_path(os.path.join("image", "map_full_hq.png"))
    if os.path.exists(map_path):
        with open(map_path, "rb") as f:
            return f.read()

    return None


class KalmanFilter2D:
    def __init__(self):
        self.kf = cv2.KalmanFilter(4, 2)
        self.kf.transitionMatrix = np.array([
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], np.float32)
        self.kf.measurementMatrix = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], np.float32)
        # ─── 噪声协方差 ───
        self.kf.processNoiseCov = np.array([
            [0.1, 0, 0, 0],
            [0, 0.1, 0, 0],
            [0, 0, 0.5, 0],
            [0, 0, 0, 0.5]
        ], dtype=np.float32)
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 0.5
        self.kf.errorCovPost = np.eye(4, dtype=np.float32) * 0.5
        self.kf.statePost = np.zeros((4, 1), np.float32)
        self.init = False
        self._last_meas_x = 0.0   # 上一帧原始测量值（稳定锚点）
        self._last_meas_y = 0.0
        self._deadband = 3.0      # 静止判定阈值

    def update(self, x, y):
        """统一 predict+correct，无死区切换，基于原始测量判定静止"""
        if not self.init:
            self.kf.statePost[0, 0] = x
            self.kf.statePost[1, 0] = y
            self._last_meas_x = x
            self._last_meas_y = y
            self.init = True
            return x, y

        # ─── 静止判定：基于原始测量值的帧间变化（稳定锚点，不漂移） ───
        stationary = (abs(x - self._last_meas_x) < self._deadband and
                      abs(y - self._last_meas_y) < self._deadband)
        self._last_meas_x = x
        self._last_meas_y = y

        # ─── 始终运行 predict + correct（消除模式切换震荡） ───
        self.kf.predict()
        m = np.array([[x], [y]], np.float32)
        self.kf.correct(m)

        # ─── 速度阻尼：静止时强制衰减速度防漂移，运动中保持 ───
        if stationary:
            self.kf.statePost[2, 0] *= 0.2   # 静止：速度衰减80%
            self.kf.statePost[3, 0] *= 0.2

        return float(self.kf.statePost[0, 0]), float(self.kf.statePost[1, 0])

    def reset(self, x=0, y=0):
        self.kf.statePost = np.zeros((4, 1), np.float32)
        self.kf.statePost[0, 0] = x
        self.kf.statePost[1, 0] = y
        self.kf.errorCovPost = np.eye(4, dtype=np.float32) * 0.5
        self._last_meas_x = x
        self._last_meas_y = y
        self.init = True


def _load_onnx_model():
    """加载 CNN 指针角度检测模型（ONNX）"""
    model_path = os.path.join(os.path.dirname(__file__), '..', 'model', 'pointer_cnn.onnx')
    if not os.path.exists(model_path):
        print(f"[Nav] ONNX模型未找到: {model_path}")
        return None
    try:
        import onnxruntime as ort
        sess = ort.InferenceSession(model_path)
        print(f"[Nav] ONNX指针角度模型加载成功")
        return sess
    except Exception as e:
        print(f"[Nav] ONNX加载失败: {e}")
        return None

_ONNX_SESSION = _load_onnx_model()


def detect_pointer_angle(scene_bgr):
    """CNN模型检测指针角度

    输入: BGR图像（任意大小，取64x64中心裁剪）
    输出: (ok, angle_degrees)
        成功时 ok=True, angle 范围 0-360°
        角度遵循标准数学坐标：0°=右, 90°=下, 180°=左, 270°=上（屏幕坐标）
    """
    global _ONNX_SESSION
    if _ONNX_SESSION is None:
        return False, 0.0

    try:
        h, w = scene_bgr.shape[:2]
        cx, cy = w // 2, h // 2
        crop = scene_bgr[cy-32:cy+32, cx-32:cx+32]

        # BGR → RGB → float32 → CHW → batch
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        inp = np.transpose(rgb, (2, 0, 1))[np.newaxis, :, :, :]

        # ONNX推理
        out = _ONNX_SESSION.run(None, {'input': inp})[0][0]

        # (sin, cos) → angle
        sin_v, cos_v = out[0], out[1]
        angle = math.degrees(math.atan2(sin_v, cos_v)) % 360
        return True, angle

    except Exception as e:
        print(f"[Nav] CNN角度检测异常: {e}")
        return False, 0.0


# ─── 常量 ───
# 世界坐标边界（与新地图 8192x8192 一致）
MAP_BOUNDS = (0, 0, 8192, 8192)

# 地图像素尺寸（新地图 8192x8192）
MAP_PIXEL_W = 8192
MAP_PIXEL_H = 8192

# 独立X/Y缩放因子：世界坐标 / 像素坐标
SCALE_X = MAP_BOUNDS[2] / MAP_PIXEL_W  # 8192/8192 = 1.0
SCALE_Y = MAP_BOUNDS[3] / MAP_PIXEL_H  # 8192/8192 = 1.0

# 匹配参数
MATCH_RATIO = 0.55          # 严格比值：更高质量匹配对
MIN_INLIERS = 10            # 最小内点数
RANSAC_TH = 5.0             # RANSAC阈值
SEARCH_RADIUS = 600          # 空间过滤搜索半径（局部FLANN覆盖范围）

# 回退匹配参数（标准匹配失败时使用空间先验）
FALLBACK_RADIUS = 300        # 回退搜索半径（小半径过滤虚假匹配）
FALLBACK_RATIO = 0.75        # 放松比率测试（应对重复纹理）
FALLBACK_RANSAC_TH = 3.0     # 更严格RANSAC阈值
FALLBACK_MIN_INLIERS = 6     # 回退最小内点数（已有空间先验，可降低）
FALLBACK_MAX_JUMP = 450      # 回退允许的最大位置跳跃（半径1.5倍）

CACHE_MS = 10               # 仅同帧复用（防同一帧多次调用），不跨帧缓存
QUICK_MATCH_INTERVAL = 3      # 每3帧全匹配1次（约10Hz匹配频率）
FRAME_INTERVAL = 2            # 默认每2帧更新一次（30fps处理）

# SIFT参数（运行时与预计算完全一致）
# 预计算: nfeatures=0, contrastThreshold=0.001, edgeThreshold=50.0, sigma=1.6
# 运行时必须完全一致！之前设3000导致特征选择不一致
RUNTIME_SIFT_FEATURES = 0   # 无限制（匹配预计算）
SIFT_CONTRAST_TH = 0.001
SIFT_EDGE_TH = 50.0
SIFT_SIGMA = 1.6

# FLANN搜索参数（checks=8 经测试匹配数与24相近，但速度快40%）
FLANN_CHECKS = 8

# 失败恢复参数
MAX_CONSECUTIVE_FAILS = 5


class MapNavigationThread(QThread):
  
    position_updated = Signal(int, int, float, object)
    navigation_status = Signal(str)
    debug_info = Signal(str)

    def __init__(self, gc, roi=None, fmp=None):
        super().__init__()
        self.gc = gc
        self.roi = roi
        self._run = False

        # ─── SIFT（参数与预计算完全一致） ───
        self._sift = cv2.SIFT_create(
            nfeatures=RUNTIME_SIFT_FEATURES,
            contrastThreshold=SIFT_CONTRAST_TH,
            edgeThreshold=SIFT_EDGE_TH,
            sigma=SIFT_SIGMA
        )

        # ─── 全局FLANN索引（从缓存加载） ───
        self._global_flann = None
        self._global_pts = None     # Nx2 特征点坐标
        self._global_des = None     # Nx128 描述子
        self._total_features = 0
        self._tile_grid = None
        self._ready = False

        # 缓存
        self._lH = None
        self._lmt = 0
        self._lpos_pixel = None     # 上次位置（像素坐标）
        self._homography_angle = 0.0  # 从homography提取的小地图旋转角（度）

        # 卡尔曼滤波
        self.kf = KalmanFilter2D()
        self._lupd = 0
        self._sx = self._sy = None
        self._last_good_conf = 0.0

        # 更新间隔（基于帧计数）
        self._frame_interval = FRAME_INTERVAL
        self._fail_count = 0
        self._frame_count = 0       # 帧计数器（QUICK_MATCH_INTERVAL 机制用）

    def _load_global_features(self):
        cache_path = _get_resource_path(os.path.join("image", "global_sift_features.pkl"))

        if not os.path.exists(cache_path):
            print("[Nav] 未找到全局特征缓存文件")
            self._ready = True
            return

        try:
            t0 = time.time()
            with open(cache_path, 'rb') as f:
                cache = pickle.load(f)

            des = cache['des']
            flann_params = cache.get('flann_params', dict(algorithm=1, trees=4))
            search_params = cache.get('search_params', dict(checks=FLANN_CHECKS))

            # ─── 全局FLANN（首次匹配或传送恢复时使用） ───
            self._global_flann = cv2.FlannBasedMatcher(flann_params, search_params)
            self._global_flann.add([des])
            self._global_flann.train()

            # ─── 空间KD-tree（用于局部特征过滤） ───
            from scipy.spatial import cKDTree
            kp = cache['kp']
            self._global_pts = np.array(kp[:, :2], dtype=np.float32) if len(kp) > 0 else np.zeros((0, 2), dtype=np.float32)
            self._global_des = des
            self._spatial_kdtree = cKDTree(self._global_pts) if len(self._global_pts) > 0 else None

            print(f"[Nav] 全局FLANN+KDTree加载完成 ({time.time()-t0:.1f}s, {cache.get('total_features', 0)} 特征)")

            self._total_features = cache.get('total_features', len(kp))
            self._tile_grid = cache.get('tile_grid', None)

            # 局部FLANN缓存（仅在位置变化时重建）
            self._local_flann = None
            self._local_pts = None
            self._local_des = None
            self._local_center = None  # 上次局部FLANN的中心位置
            self._local_flann_params = flann_params

            # ─── SIFT预热 ───
            try:
                warmup = np.zeros((100, 100), dtype=np.uint8)
                self._sift.detectAndCompute(warmup, None)
            except:
                pass

            self._ready = True

        except Exception as e:
            print(f"[Nav] 特征加载失败: {e}")
            import traceback
            traceback.print_exc()
            self._ready = True

    def _rebuild_local_flann(self, center_x, center_y, radius=SEARCH_RADIUS):
        """重建局部FLANN索引（仅包含指定位置附近的特征）"""
        if self._spatial_kdtree is None:
            return False

        try:
            # 查询半径内的所有特征索引
            indices = self._spatial_kdtree.query_ball_point([center_x, center_y], radius)
            if len(indices) < MIN_INLIERS * 2:
                return False

            indices = np.array(indices, dtype=np.int32)
            local_des = self._global_des[indices]
            local_pts = self._global_pts[indices]

            # 构建局部FLANN
            self._local_flann = cv2.FlannBasedMatcher(
                self._local_flann_params,
                dict(checks=FLANN_CHECKS)
            )
            self._local_flann.add([local_des])
            self._local_flann.train()

            self._local_pts = local_pts
            self._local_des = local_des
            self._local_center = (center_x, center_y)

            return True
        except Exception as e:
            print(f"[Nav] 局部FLANN重建失败: {e}")
            return False

    def _locate_fallback(self, gray, kpm, dm):
        """空间先验回退匹配：标准匹配失败时，使用上次位置做小半径空间过滤

        应对重复纹理区域：全局/局部FLANN因虚假匹配导致RANSAC失败时，
        通过更小的搜索半径（300px）过滤掉远处的相似纹理，仅保留附近特征。

        策略：
        1. 用KD-tree过滤全局特征到_last_known_position附近的小半径(300px)
        2. 放松比率测试到0.75（获取更多候选匹配）
        3. 用更严格的RANSAC阈值(3.0)剔除虚假匹配
        4. 接受较低的inliers(6)，因为已有空间先验降低误检风险
        5. 限制最大位置跳跃，防止异常漂移
        """
        if self._lpos_pixel is None or self._spatial_kdtree is None:
            return False, 0, 0, 1.0

        lx, ly = self._lpos_pixel
        if not (MAP_BOUNDS[0] <= lx <= MAP_BOUNDS[2] and
                MAP_BOUNDS[1] <= ly <= MAP_BOUNDS[3]):
            return False, 0, 0, 1.0

        try:
            # ─── 1. 空间过滤：仅保留上次位置附近的特征 ───
            indices = self._spatial_kdtree.query_ball_point([lx, ly], FALLBACK_RADIUS)
            if len(indices) < FALLBACK_MIN_INLIERS * 2:
                return False, 0, 0, 1.0

            indices = np.array(indices, dtype=np.int32)
            local_des = self._global_des[indices]
            local_pts = self._global_pts[indices]

            # ─── 2. BFMatcher + 放松比率测试 ───
            bf = cv2.BFMatcher(cv2.NORM_L2)
            ms = bf.knnMatch(dm, local_des, k=2)
            if not ms:
                return False, 0, 0, 1.0

            good = [m for m, n in ms if m.distance < FALLBACK_RATIO * n.distance]
            if len(good) < FALLBACK_MIN_INLIERS:
                return False, 0, 0, 1.0

            # ─── 3. RANSAC（更严格阈值） ───
            h, w = gray.shape[:2]
            px, py = w // 2, h // 2
            src_pts = np.float32([kpm[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = local_pts[[m.trainIdx for m in good]].reshape(-1, 1, 2)
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.USAC_MAGSAC, FALLBACK_RANSAC_TH)
            if M is None:
                return False, 0, 0, 1.0

            inliers = int(mask.sum()) if mask is not None else 0
            if inliers < FALLBACK_MIN_INLIERS:
                return False, 0, 0, 1.0

            # ─── 4. 世界坐标 + 跳跃检查 ───
            ptr_pt = np.float32([[[px, py]]])
            global_pixel = cv2.perspectiveTransform(ptr_pt, M)[0, 0]
            wx = float(global_pixel[0] * SCALE_X)
            wy = float(global_pixel[1] * SCALE_Y)

            if not (MAP_BOUNDS[0] <= wx <= MAP_BOUNDS[2] and
                    MAP_BOUNDS[1] <= wy <= MAP_BOUNDS[3]):
                return False, 0, 0, 1.0

            # 跳跃检查：防止异常位置漂移
            dist = ((wx - lx) ** 2 + (wy - ly) ** 2) ** 0.5
            if dist > FALLBACK_MAX_JUMP:
                return False, 0, 0, 1.0

            # ─── 5. 缓存 + 返回（置信度上限0.8，标识为回退路径） ───
            self._lH = M
            self._homography_angle = math.degrees(math.atan2(M[1, 0], M[0, 0]))
            self._lmt = time.time() * 1000
            self._lpos_pixel = (float(global_pixel[0]), float(global_pixel[1]))
            conf = min(0.8, inliers / 20.0)
            self._last_good_conf = conf

            return True, wx, wy, conf
        except Exception as e:
            print(f"[Nav] _locate_fallback异常: {e}")
            return False, 0, 0, 1.0

    def _get_match_flann(self, last_pos):
        """获取用于匹配的FLANN：优先使用局部FLANN，否则使用全局"""
        if last_pos is None:
            # 无上次位置（首次或传送恢复）：使用全局FLANN
            self._local_flann = None
            return self._global_flann, self._global_pts

        lx, ly = last_pos
        # 检查是否需要重建局部FLANN
        need_rebuild = False
        if self._local_flann is None:
            need_rebuild = True
        elif self._local_center is not None:
            cx, cy = self._local_center
            dist = ((lx - cx) ** 2 + (ly - cy) ** 2) ** 0.5
            # 位置移动超过搜索半径的80%时重建（最大化局部FLANN复用）
            if dist > SEARCH_RADIUS * 0.8:
                need_rebuild = True
        else:
            need_rebuild = True

        if need_rebuild:
            if not self._rebuild_local_flann(lx, ly):
                # 重建失败，回退到全局
                return self._global_flann, self._global_pts

        if self._local_flann is not None:
            return self._local_flann, self._local_pts
        return self._global_flann, self._global_pts

    def set_minimap_roi(self, r):
        self.roi = r

    def set_frame_interval(self, frames):
        """设置帧间隔（每N帧更新一次）"""
        self._frame_interval = max(1, min(10, frames))

    def _locate(self, img, gray=None, force=False):
        try:
            if not self._ready:
                return False, 0, 0, 1.0

            h, w = img.shape[:2]
            px, py = w // 2, h // 2

            # ─── 快速模式：帧间homography复用（~0.1ms，零图像转换） ───
            if not force and self._lH is not None:
                if self._frame_count % QUICK_MATCH_INTERVAL != 0:
                    try:
                        p = cv2.perspectiveTransform(
                            np.float32([[[px, py]]]), self._lH)[0, 0]
                        wx = float(p[0] * SCALE_X)
                        wy = float(p[1] * SCALE_Y)
                        if MAP_BOUNDS[0] <= wx <= MAP_BOUNDS[2] and MAP_BOUNDS[1] <= wy <= MAP_BOUNDS[3]:
                            return True, wx, wy, 0.95
                    except:
                        pass

            # ─── 全路径：需要gray时才转换 ───
            if gray is None:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # ─── SIFT提取 ───
            kpm, dm = self._sift.detectAndCompute(gray, None)
            if dm is None or len(kpm) < FALLBACK_MIN_INLIERS:
                # 特征数过少（连回退阈值都达不到），直接失败
                return False, 0, 0, 1.0
            if len(kpm) < MIN_INLIERS:
                # 特征数不足以做标准匹配，尝试回退
                return self._locate_fallback(gray, kpm, dm)

            # ─── 空间过滤FLANN匹配：优先使用局部FLANN（仅附近特征） ───
            flann, match_pts = self._get_match_flann(self._lpos_pixel)
            ms = flann.knnMatch(dm, k=2)
            if not ms:
                return self._locate_fallback(gray, kpm, dm)

            # 比率测试
            good = [m for m, n in ms if m.distance < MATCH_RATIO * n.distance]
            if len(good) < MIN_INLIERS:
                # 局部FLANN匹配不足时尝试全局回退
                if flann is not self._global_flann:
                    ms = self._global_flann.knnMatch(dm, k=2)
                    good = [m for m, n in ms if m.distance < MATCH_RATIO * n.distance]
                    match_pts = self._global_pts
                    if len(good) < MIN_INLIERS:
                        return self._locate_fallback(gray, kpm, dm)
                else:
                    return self._locate_fallback(gray, kpm, dm)

            # 构建匹配点
            src_pts = np.float32([kpm[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = match_pts[[m.trainIdx for m in good]].reshape(-1, 1, 2)

            # RANSAC
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.USAC_MAGSAC, RANSAC_TH)
            if M is None:
                return self._locate_fallback(gray, kpm, dm)

            inliers = mask.sum() if mask is not None else 0
            if inliers < MIN_INLIERS:
                return self._locate_fallback(gray, kpm, dm)

            # Homography精化（仅用内点做最小二乘）
            inlier_mask = mask.ravel().astype(bool)
            if inlier_mask.sum() >= MIN_INLIERS and inlier_mask.sum() < len(src_pts):
                refined, _ = cv2.findHomography(
                    src_pts[inlier_mask], dst_pts[inlier_mask], 0)
                if refined is not None:
                    check = cv2.perspectiveTransform(
                        src_pts[inlier_mask][:1], refined)[0, 0]
                    if 0 <= check[0] <= MAP_PIXEL_W and 0 <= check[1] <= MAP_PIXEL_H:
                        M = refined

            # 世界坐标
            ptr_pt = np.float32([[[px, py]]])
            global_pixel = cv2.perspectiveTransform(ptr_pt, M)[0, 0]
            wx = float(global_pixel[0] * SCALE_X)
            wy = float(global_pixel[1] * SCALE_Y)

            if not (MAP_BOUNDS[0] <= wx <= MAP_BOUNDS[2] and
                    MAP_BOUNDS[1] <= wy <= MAP_BOUNDS[3]):
                return self._locate_fallback(gray, kpm, dm)

            # 缓存
            self._lH = M
            self._homography_angle = math.degrees(math.atan2(M[1, 0], M[0, 0]))
            self._lmt = time.time() * 1000
            self._lpos_pixel = (float(global_pixel[0]), float(global_pixel[1]))
            conf = min(1.0, inliers / 30.0)
            self._last_good_conf = conf

            return True, wx, wy, conf

        except Exception as e:
            print(f"[Nav] _locate异常: {e}")
            import traceback
            traceback.print_exc()
            return False, 0, 0, 1.0

    def run(self):
        self._run = True
        self._load_global_features()
        self.navigation_status.emit("导航已启动")

        # 缓存：已无需要缓存的变量（指针位置用中心点，角度从homography提取）

        while self._run:
            try:
                if not self.roi:
                    self.msleep(10)
                    continue

                # 帧间隔控制（每 N 帧处理一次）
                self._frame_count += 1
                if self._frame_count % self._frame_interval != 0:
                    self.msleep(10)
                    continue

                now = time.time() * 1000

                # 截图
                img = self.gc.capture_window(self.roi)
                if img is None:
                    self.position_updated.emit(0, 0, 0.0, None)
                    self._lupd = now
                    continue

                h, w = img.shape[:2]

                need_full_match = (self._frame_count % QUICK_MATCH_INTERVAL == 0)

                # ─── 1. 定位（全匹配帧做SIFT+FLANN，其余帧复用homography） ───
                if need_full_match:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                else:
                    gray = None

                mok, mx, my, mconf = self._locate(img, gray=gray)

                # ─── 2. 指针角度识别（径向扫描，~5ms） ───
                px, py = w // 2, h // 2
                ok, angle = detect_pointer_angle(img)
                if not ok:
                    angle = 0.0

                if mok:
                    had_failures = self._fail_count > 0
                    self._fail_count = 0

                    if had_failures:
                        # 从失败中恢复（可能是传送）：直接重置KF到新位置
                        self.kf.reset(mx, my)
                        sx, sy = mx, my
                        print(f"[Nav] 恢复定位: 重置KF到({sx:.1f},{sy:.1f})")
                    else:
                        sx, sy = self.kf.update(mx, my)

                    self._sx, self._sy = sx, sy
                    combined_conf = mconf
                    self.position_updated.emit(px, py, combined_conf, (sx, sy, angle))
                else:
                    self._fail_count += 1

                    if self._fail_count == 1:
                        # 首次失败：保留_lpos_pixel作为空间先验，供回退匹配使用
                        print(f"[Nav] 进入恢复模式（保留空间先验）")
                        self._last_good_conf = 0.0
                        self.position_updated.emit(px, py, 0.0, None)
                    elif self._fail_count == 3:
                        # 连续3次失败：可能是传送，清除空间先验让全局FLANN接管
                        print(f"[Nav] 连续3次失败，重置空间先验（疑似传送）")
                        self._lpos_pixel = None
                        self._lH = None
                        self.kf.reset(0, 0)
                        self.position_updated.emit(px, py, 0.0, None)
                    elif self._fail_count >= MAX_CONSECUTIVE_FAILS:
                        print(f"[Nav] 连续{self._fail_count}次失败")
                        self.position_updated.emit(px, py, 0.0, None)
                    else:
                        self.position_updated.emit(px, py, 0.0, None)

                self._lupd = now

            except Exception as e:
                print(f"[Nav] 异常: {e}")
                self.msleep(10)

    def stop(self):
        self._run = False
        self.navigation_status.emit("导航已停止")
        self.wait()