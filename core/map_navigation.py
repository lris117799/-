import cv2
import math
import numpy as np
import os
import time
import pickle
from PySide6.QtCore import QThread, Signal


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
# 世界坐标边界
MAP_BOUNDS = (0, 0, 4500, 2500)

# 地图像素尺寸（map_G.png 6144x4608）
MAP_PIXEL_W = 6144
MAP_PIXEL_H = 4608

# 独立X/Y缩放因子：世界坐标 / 像素坐标
SCALE_X = MAP_BOUNDS[2] / MAP_PIXEL_W  # 4500/6144 = 0.73242
SCALE_Y = MAP_BOUNDS[3] / MAP_PIXEL_H  # 2500/4608 = 0.54253

# 匹配参数
MATCH_RATIO = 0.55          # 严格比值：更高质量的匹配对
MIN_INLIERS = 10            # 最小内点数
RANSAC_TH = 5.0             # RANSAC阈值
SEARCH_RADIUS = 500         # 搜索半径

CACHE_MS = 10               # 仅同帧复用（防同一帧多次调用），不跨帧缓存
QUICK_MATCH_INTERVAL = 5      # 每5帧全匹配1次（约2-5Hz匹配频率）
FRAME_INTERVAL = 3            # 默认每3帧更新一次地图识别

# SIFT参数（运行时与预计算完全一致）
# 预计算: nfeatures=0, contrastThreshold=0.001, edgeThreshold=50.0, sigma=1.6
# 运行时必须完全一致！之前设3000导致特征选择不一致
RUNTIME_SIFT_FEATURES = 0   # 无限制（匹配预计算）
SIFT_CONTRAST_TH = 0.001
SIFT_EDGE_TH = 50.0
SIFT_SIGMA = 1.6

# FLANN搜索参数
FLANN_CHECKS = 24

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
        cache_path = os.path.join(
            os.path.dirname(__file__), '..',
            "image", "global_sift_features.pkl"
        )

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

            # ─── 全局FLANN（单次调用效率最高，经实测64ms vs 瓦片207ms） ───
            self._global_flann = cv2.FlannBasedMatcher(flann_params, search_params)
            self._global_flann.add([des])
            self._global_flann.train()

            print(f"[Nav] 全局FLANN加载完成 ({time.time()-t0:.1f}s)")

            # 保存全局数据
            kp = cache['kp']
            self._global_pts = np.array(kp[:, :2], dtype=np.float32) if len(kp) > 0 else np.zeros((0, 2), dtype=np.float32)
            self._global_des = des
            self._total_features = cache.get('total_features', len(kp))
            self._tile_grid = cache.get('tile_grid', None)

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

            # ─── 快速模式：帧间homography复用（4/5帧走此路径，~0.1ms，零图像转换） ───
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

            # ─── 全路径：SIFT提取 + 全局FLANN匹配（1/5帧走此路径） ───
            kpm, dm = self._sift.detectAndCompute(gray, None)
            if dm is None or len(kpm) < MIN_INLIERS:
                return False, 0, 0, 1.0

            # 全局FLANN匹配（单次调用，64ms @ 227K特征）
            ms = self._global_flann.knnMatch(dm, k=2)
            if not ms:
                return False, 0, 0, 1.0

            # 比率测试
            good = [m for m, n in ms if m.distance < MATCH_RATIO * n.distance]
            if len(good) < MIN_INLIERS:
                return False, 0, 0, 1.0

            # 构建匹配点
            src_pts = np.float32([kpm[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = self._global_pts[[m.trainIdx for m in good]].reshape(-1, 1, 2)

            # RANSAC
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.USAC_MAGSAC, RANSAC_TH)
            if M is None:
                return False, 0, 0, 1.0

            inliers = mask.sum() if mask is not None else 0
            if inliers < MIN_INLIERS:
                return False, 0, 0, 1.0

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
                return False, 0, 0, 1.0

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
                        print(f"[Nav] 传送恢复: 重置KF到({sx:.1f},{sy:.1f})")
                    else:
                        sx, sy = self.kf.update(mx, my)

                    self._sx, self._sy = sx, sy
                    combined_conf = mconf
                    self.position_updated.emit(px, py, combined_conf, (sx, sy, angle))
                else:
                    self._fail_count += 1

                    if self._fail_count == 1:
                        print(f"[Nav] 进入恢复模式")
                        self._lpos_pixel = None
                        self._last_good_conf = 0.0
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